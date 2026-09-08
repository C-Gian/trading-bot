import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest
from app.backtest.asof import AsOfView
from app.backtest.engine import content_hash, simulate
from app.backtest.metrics import calculate
from app.backtest.models import Bar, CostModel, ExitReason, Intent

T = datetime(2020, 1, 1, 1, tzinfo=UTC)


def bar(minute=0, o="100", h="105", l="95", c="101", complete=True):
    return Bar(T + timedelta(minutes=minute), D(o), D(h), D(l), D(c), complete)


def intent(**changes):
    values = {
        "run_id": "SYNTHETIC-RUN",
        "strategy_reference": "SYNTHETIC_ADAPTER_V1",
        "dataset_manifest_id": "SYNTHETIC-DATA",
        "dataset_content_hash": "a" * 64,
        "signal_timestamp": T,
        "direction": "LONG",
        "entry_timing_rule": "NEXT_1M_OPEN",
        "stop": D(90),
        "target": D(110),
        "target_exit_rule": "LIMIT_AT_TARGET",
        "max_hold_minutes": 60,
    }
    values.update(changes)
    return Intent(**values)


def test_next_bar_entry_and_plain_target():
    result = simulate(intent(), [bar(h="111")])
    assert result.entry_timestamp == T
    assert result.exit_reason == ExitReason.TARGET and result.exit_raw_price == D(110)


def test_plain_stop_and_ambiguous_stop_first():
    assert simulate(intent(), [bar(l="89")]).exit_reason == ExitReason.STOP
    assert simulate(intent(), [bar(h="111", l="89")]).exit_reason == ExitReason.STOP


def test_gap_below_stop_and_open_beyond_target_conservative():
    stopped = simulate(intent(), [bar(), bar(1, o="85", h="86", l="80", c="82")])
    assert stopped.exit_reason == ExitReason.STOP_GAP and stopped.exit_raw_price == D(85)
    targeted = simulate(intent(), [bar(), bar(1, o="112", h="115", l="111", c="114")])
    assert targeted.exit_raw_price == D(110)


def test_expiry_and_end_of_data():
    exp = simulate(intent(max_hold_minutes=2, target=None), [bar(), bar(1, c="103")])
    assert exp.exit_reason == ExitReason.EXPIRY and exp.exit_timestamp == T + timedelta(minutes=2)
    unresolved = simulate(intent(max_hold_minutes=2, target=None), [bar()])
    assert unresolved.exit_reason == ExitReason.UNRESOLVED_END_OF_DATA and unresolved.net_r is None


def test_missing_entry_and_path_gap_are_not_filled():
    assert simulate(intent(), [bar(1)]).exit_reason == ExitReason.INVALID_MISSING_ENTRY_BAR
    result = simulate(intent(target=None), [bar(), bar(2)])
    assert result.exit_reason == ExitReason.UNRESOLVED_DATA_GAP and result.exit_raw_price is None


def test_overlap_is_suppressed():
    result = simulate(
        intent(), [bar(), bar(1), bar(2, h="111")], overlapping_signals=[T + timedelta(minutes=1)]
    )
    assert result.suppressed_signal_count == 1


def test_scope_horizon_risk_and_cutoff_rejections():
    with pytest.raises(ValueError):
        intent(direction="SHORT")
    with pytest.raises(ValueError):
        intent(max_hold_minutes=1441)
    assert simulate(intent(stop=D(100)), [bar()]).exit_reason == ExitReason.INVALID_NON_TRADABLE
    with pytest.raises(ValueError):
        intent(signal_timestamp=datetime(2025, 1, 1, tzinfo=UTC))


def test_cost_arithmetic_and_golden_oracle():
    result = simulate(intent(), [bar(h="111")])
    expected = json.loads(
        (
            Path(__file__).parents[2] / "research/fixtures/synthetic_execution_golden.json"
        ).read_text()
    )["expected"]
    for name, value in expected.items():
        assert format(getattr(result, name), "f") == value
    assert result.entry_execution_friction == D("0.02") and result.exit_execution_friction == D(
        "0.022"
    )


def test_cost_increase_cannot_improve_net_and_repeat_is_identical():
    base = simulate(intent(), [bar(h="111")])
    stressed = simulate(
        intent(),
        [bar(h="111")],
        CostModel(
            entry_fee_bps=D(20),
            exit_fee_bps=D(20),
            entry_friction_bps=D(5),
            exit_friction_bps=D(5),
            profile="SYNTHETIC_STRESS",
        ),
    )
    assert stressed.net_pnl < base.net_pnl
    assert content_hash(base) == content_hash(simulate(intent(), [bar(h="111")]))


def test_metrics_separate_invalid_records():
    valid = simulate(intent(), [bar(h="111")])
    invalid = simulate(intent(), [])
    metrics = calculate([valid, invalid])
    assert (
        metrics.trade_count == 1
        and metrics.unresolved_invalid_count == 1
        and metrics.cumulative_net_r == valid.net_r
    )


def test_asof_view_excludes_future_and_incomplete_bars():
    one_hour = (
        Bar(T - timedelta(hours=1), D(1), D(1), D(1), D(1), True),
        Bar(T, D(1), D(1), D(1), D(1), True),
    )
    four_hour = (
        Bar(T - timedelta(hours=5), D(1), D(1), D(1), D(1), True),
        Bar(T - timedelta(hours=9), D(1), D(1), D(1), D(1), False),
    )
    view = AsOfView.build(T, one_hour, four_hour)
    assert len(view.signal_bars_1h) == 1 and len(view.context_bars_4h) == 1
    assert all(b.open_time < T for b in view.signal_bars_1h)


def test_incomplete_signal_bar_rejected_and_context_excluded():
    view = AsOfView.build(T, (Bar(T - timedelta(hours=1), D(1), D(1), D(1), D(1), False),), ())
    with pytest.raises(ValueError):
        view.require_1h(1)
