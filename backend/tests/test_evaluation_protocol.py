from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from app.research.evaluation_protocol import (
    HOUR_US,
    dependence_diagnostics,
    fold_contains,
    load_protocol,
    protocol_hash,
    summarize_trades,
    terminal_classification,
    utc_us,
    validate_protocol,
    validation_fold,
)


@pytest.fixture
def protocol():
    return load_protocol()


def trade(year=2019, offset=0, net=0.5, regime="PERSISTENT_UP", status="VALID"):
    result = {
        "signal_us": utc_us(datetime(year, 1, 2, tzinfo=UTC) + timedelta(days=offset)),
        "status": status,
        "regime": regime,
    }
    if status == "VALID":
        result.update(net_r=net, gross_r=net + 0.12, year=year)
    return result


def balanced_trades(net=0.5):
    return [trade(year, index, net) for year in range(2019, 2025) for index in range(20)]


def summaries(protocol, default=0.5, zero=0.62, double=0.38):
    return [summarize_trades(balanced_trades(value), protocol) for value in (default, zero, double)]


def test_exact_six_calendar_folds_and_cutoff_fence(protocol):
    validate_protocol(protocol)
    assert [fold["fold_id"] for fold in protocol["folds"]] == [
        f"DEV-{year}" for year in range(2019, 2025)
    ]
    for fold in protocol["folds"]:
        start = utc_us(fold["validation_start"])
        last = utc_us(fold["last_signal_inclusive"])
        end = utc_us(fold["validation_end_exclusive"])
        assert start - utc_us(fold["train_end_exclusive"]) == 216 * HOUR_US
        assert end - last == 24 * HOUR_US
        assert fold_contains(fold, start) and fold_contains(fold, last)
        assert not fold_contains(fold, start - HOUR_US)
        assert not fold_contains(fold, last + HOUR_US)
        assert not fold_contains(fold, end)
    assert validation_fold(protocol, utc_us("2025-01-01T00:00:00Z")) is None
    assert utc_us(protocol["folds"][-1]["validation_end_exclusive"]) - 60_000_000 == utc_us(
        protocol["development_cutoff"]
    )


@pytest.mark.parametrize(
    ("key", "value"),
    [("purge_hours", 192), ("embargo_hours", 0), ("max_hold_minutes", 60), ("folds", [])],
)
def test_protocol_rejects_material_redefinitions(protocol, key, value):
    protocol[key] = value
    with pytest.raises(ValueError, match="frozen"):
        validate_protocol(protocol)


def test_protocol_hash_order_independent_but_threshold_sensitive(protocol):
    reordered = dict(reversed(list(protocol.items())))
    assert protocol_hash(protocol) == protocol_hash(reordered)
    changed = deepcopy(protocol)
    changed["diagnostics"]["minimum_total_trades"] = 1
    assert protocol_hash(protocol) != protocol_hash(changed)
    with pytest.raises(ValueError):
        validate_protocol(changed)


def test_utc_integer_conversion_rejects_naive_and_keeps_microseconds():
    assert utc_us("2020-01-01T01:00:00+01:00") == utc_us("2020-01-01T00:00:00Z")
    assert utc_us("1970-01-01T00:00:00.000001Z") == 1
    with pytest.raises(ValueError, match="timezone-aware"):
        utc_us("2020-01-01T00:00:00")


def test_pooled_metric_weights_trades_and_keeps_empty_folds(protocol):
    inputs = [trade(2019, 0, 2), trade(2020, 0, -1), trade(2020, 1, -1)]
    summary = summarize_trades(reversed(inputs), protocol)
    assert summary["metrics"]["trade_count"] == 3
    assert summary["metrics"]["net_expectancy_r"] == 0
    assert summary["stability"]["equal_fold_mean"] == 0.5
    assert summary["stability"]["empty_fold_count"] == 4
    assert summary["stability"]["positive_fold_fraction"] == pytest.approx(1 / 6)
    assert summary["stability"]["max_absolute_fold_pnl_share"] == 0.5
    assert summary["stability"]["max_fold_trade_share"] == pytest.approx(2 / 3)
    assert summary["stability"]["leave_one_fold_out_expectancy"]["DEV-2019"] == -1
    assert summary["diagnostics"]["minimum_fold_trades"] == 0
    assert inputs[0]["net_r"] == 2


def test_empty_summary_has_no_manufactured_metrics_and_is_inconclusive(protocol):
    summary = summarize_trades([], protocol)
    assert summary["metrics"]["net_expectancy_r"] is None
    assert len(summary["folds"]) == 6
    assert summary["stability"]["positive_fold_fraction"] == 0
    assert summary["stability"]["worst_fold"] is None
    assert summary["diagnostics"]["trade_ess"] == 0
    assert terminal_classification(summary, summary, summary, protocol) == "INCONCLUSIVE"


def test_filter_uses_declared_maximum_outcome_not_actual_early_exit(protocol):
    before = trade()
    before["signal_us"] = utc_us("2019-01-01T23:00:00Z")
    last = trade(offset=1)
    last["signal_us"] = utc_us("2019-12-31T00:00:00Z")
    too_late = trade(offset=2)
    too_late["signal_us"] = utc_us("2019-12-31T01:00:00Z")
    too_late["exit_us"] = too_late["signal_us"] + 60_000_000
    summary = summarize_trades([before, last, too_late], protocol)
    assert summary["metrics"]["trade_count"] == 1
    assert summary["excluded_outside_validation_attempt_count"] == 2


def test_recorded_exit_fence_allows_final_close_but_never_later(protocol):
    last = trade(2024)
    last["signal_us"] = utc_us("2024-12-31T00:00:00Z")
    last["exit_us"] = utc_us("2025-01-01T00:00:00Z")
    # This timestamp labels the close of the last permitted minute, not a new
    # post-cutoff opening bar. No market data is loaded by this test.
    assert summarize_trades([last], protocol)["metrics"]["trade_count"] == 1
    last["exit_us"] += 60_000_000
    with pytest.raises(ValueError, match="horizon or validation fence"):
        summarize_trades([last], protocol)
    last["exit_us"] = last["signal_us"] - 60_000_000
    with pytest.raises(ValueError, match="horizon or validation fence"):
        summarize_trades([last], protocol)


def test_summary_rejects_post_cutoff_before_filtering_and_bad_pnl(protocol):
    post = trade(2024)
    post["signal_us"] = utc_us("2025-01-01T00:00:00Z")
    with pytest.raises(ValueError, match="post-cutoff"):
        summarize_trades([post], protocol)
    invalid = trade(status="UNRESOLVED")
    invalid["net_r"] = -1
    with pytest.raises(ValueError, match="invented"):
        summarize_trades([invalid], protocol)
    broken = trade(net=float("nan"))
    with pytest.raises(ValueError, match="finite"):
        summarize_trades([broken], protocol)
    with pytest.raises(ValueError, match="duplicate signals"):
        summarize_trades([trade(), trade()], protocol)


def test_invalid_unresolved_diagnostics_and_observed_regimes(protocol):
    rows = [
        trade(net=2),
        trade(offset=1, net=-1, regime="OTHER"),
        trade(offset=2, status="INVALID"),
        trade(offset=3, status="UNRESOLVED", regime="OTHER"),
    ]
    summary = summarize_trades(rows, protocol)
    assert summary["metrics"]["trade_count"] == 2
    assert summary["metrics"]["unresolved_rate"] == 0.25
    assert summary["metrics"]["invalid_rate"] == 0.25
    assert summary["regime_metrics"]["PERSISTENT_UP"]["net_expectancy_r"] == 2
    assert summary["regime_metrics"]["OTHER"]["net_expectancy_r"] == -1
    assert summary["regime_stability"]["max_absolute_regime_pnl_share"] == pytest.approx(2 / 3)
    missing = trade()
    del missing["regime"]
    with pytest.raises(ValueError, match="observed"):
        summarize_trades([missing], protocol)
    imported = summarize_trades([missing], protocol, allow_unclassified_regime=True)
    assert imported["regime_metrics"]["UNCLASSIFIED"]["trade_count"] == 1


def test_bps_require_complete_observation_coverage(protocol):
    rows = [trade(), trade(offset=1)]
    rows[0]["net_return_bps"] = 10
    partial = summarize_trades(rows, protocol)["metrics"]
    assert partial["net_expectancy_bps"] is None
    assert partial["net_return_bps_observation_count"] == 1
    rows[1]["net_return_bps"] = -4
    complete = summarize_trades(rows, protocol)["metrics"]
    assert complete["net_expectancy_bps"] == 3
    assert complete["cumulative_net_bps"] == 6


def test_positive_acf_reduces_ess_and_negative_acf_is_clipped():
    increasing = [trade(offset=index, net=index) for index in range(20)]
    serial = dependence_diagnostics(increasing, lags=1)
    assert 0 < serial["trade_ess"] < 20
    alternating = [trade(offset=index, net=(-1) ** index) for index in range(20)]
    negative = dependence_diagnostics(alternating, lags=1)
    assert negative["positive_autocorrelations"] == [0]
    assert negative["trade_ess"] == 20
    for value in (1, 0.1, -0.1):
        constant = dependence_diagnostics([trade(offset=index, net=value) for index in range(120)])
        assert constant["trade_ess"] == 120 and constant["constant_return_series"]


def test_active_week_kish_penalizes_concentration_and_uses_iso_week():
    rows = [trade(offset=0), trade(offset=1), trade(offset=7)]
    diagnostic = dependence_diagnostics(rows)
    assert diagnostic["active_week_count"] == 2
    assert diagnostic["active_week_kish_count"] == 9 / 5


@pytest.mark.parametrize(
    ("default", "zero", "double", "classification"),
    [
        (-0.1, 0.02, -0.22, "REJECT_COST_DOMINATED"),
        (-0.1, -0.01, -0.22, "REJECT"),
        (0.1, 0.22, -0.02, "REJECT_COST_DOMINATED"),
        (0.1, 0.22, 0, "PROMISING_DEVELOPMENT_ONLY"),
    ],
)
def test_terminal_classification_and_negative_profitability_validation_pass(
    protocol, default, zero, double, classification
):
    outputs = summaries(protocol, default, zero, double)
    assert all(output["validation_outcome"] == "PASS" for output in outputs)
    assert terminal_classification(*outputs, protocol) == classification


@pytest.mark.parametrize("diagnostic", ["trade_count", "minimum_fold_trades", "trade_ess", "gap"])
def test_diagnostic_insufficiency_precedes_cost_rejection(protocol, diagnostic):
    outputs = summaries(protocol, -0.1, 0.02, -0.22)
    if diagnostic == "trade_count":
        outputs[0]["metrics"]["trade_count"] = 119
    elif diagnostic == "gap":
        outputs[0]["metrics"]["unresolved_rate"] = 0.01001
    else:
        outputs[0]["diagnostics"][diagnostic] = 0
    assert terminal_classification(*outputs, protocol) == "INCONCLUSIVE"


@pytest.mark.parametrize("condition", ["fold_count", "loo", "profit_concentration"])
def test_positive_but_concentrated_or_unstable_is_rejected(protocol, condition):
    outputs = summaries(protocol)
    stability = outputs[0]["stability"]
    if condition == "fold_count":
        stability["nonnegative_fold_count"] = 3
    elif condition == "loo":
        stability["leave_one_fold_out_expectancy"]["DEV-2019"] = 0
    else:
        stability["max_positive_fold_profit_share"] = 0.50001
    assert terminal_classification(*outputs, protocol) == "REJECT_UNSTABLE"


def test_structural_failure_or_different_protocol_blocks_classification(protocol):
    outputs = summaries(protocol)
    outputs[1]["validation_outcome"] = "FAIL"
    with pytest.raises(ValueError, match="structural"):
        terminal_classification(*outputs, protocol)
    outputs[1]["validation_outcome"] = "PASS"
    outputs[1]["protocol_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="frozen protocol"):
        terminal_classification(*outputs, protocol)
