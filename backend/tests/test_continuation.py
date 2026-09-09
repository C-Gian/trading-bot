import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from app.research.continuation import FeatureBar, FeatureSource, IneligibleSignal
from app.research.continuation_lab import ResearchInputs, trade_at, validate_config
from app.research.evaluation_protocol import HOUR_US, utc_us

T = utc_us("2020-01-10T00:00:00Z")
MINUTE = 60_000_000


def source(current_volume=20.0, context_step=1.0):
    hours = tuple(FeatureBar(T - (60 - i) * HOUR_US, 100.0, 99.0, 10.0) for i in range(60))
    hours = (*hours[:-1], replace(hours[-1], high=102.0, close=101.0, volume=current_volume))
    context = tuple(
        FeatureBar(T - (50 - i) * 4 * HOUR_US, 300.0, 150 + i * context_step, 1.0)
        for i in range(50)
    )
    return FeatureSource(hours, context)


def test_exact_gate_threshold_and_prior_volume_excludes_current():
    features = source().at(T)
    assert features.breakout and features.persistent_up and features.participation
    assert features.relative_volume == 2.0
    assert source(current_volume=19.999).at(T).participation is False
    assert source().decision(T, "ALIGNED")[0]


def test_structural_ablations_isolate_each_gate():
    low_activity = source(current_volume=10)
    assert low_activity.decision(T, "REGIME_ONLY")[0]
    assert not low_activity.decision(T, "PARTICIPATION_ONLY")[0]
    assert not low_activity.decision(T, "ALIGNED")[0]
    declining = source(context_step=-1)
    assert declining.decision(T, "PARTICIPATION_ONLY")[0]
    assert not declining.decision(T, "REGIME_ONLY")[0]


def test_unsigned_volume_does_not_invent_direction_or_trade_when_flat():
    flat = source(context_step=0)
    assert flat.at(T).signed_efficiency is None
    assert not flat.at(T).persistent_up
    original = source()
    zero = FeatureSource(tuple(replace(bar, volume=0) for bar in original.hourly), original.context)
    assert zero.at(T).relative_volume is None and not zero.at(T).participation


def test_efficiency_equality_has_exact_two_to_one_price_travel():
    original = source()
    # Last 42 increments alternate +2,-1: U=42,D=21.
    prices = [100.0]
    for i in range(49):
        prices.append(prices[-1] + (2 if i % 2 else -1))
    context = tuple(replace(bar, close=price) for bar, price in zip(original.context, prices))
    features = FeatureSource(original.hourly, context).at(T)
    assert features.persistent_up and features.signed_efficiency == pytest.approx(1 / 3)


@pytest.mark.parametrize("offset", [0, 1, 2, 3, 4])
def test_context_availability_and_future_suffix_invariance(offset):
    original = source()
    future_hours = tuple(FeatureBar(T + i * HOUR_US, 10000.0, 9000.0, 1e8) for i in range(8))
    future_context = tuple(FeatureBar(T + i * 4 * HOUR_US, 10000.0, 9000.0, 1e8) for i in range(3))
    extended = FeatureSource(
        (*original.hourly, *future_hours), (*original.context, *future_context)
    )
    assert extended.at(T) == original.at(T)
    instant = T + offset * HOUR_US
    prefix = FeatureSource(
        tuple(bar for bar in extended.hourly if bar.open_us + HOUR_US <= instant),
        tuple(bar for bar in extended.context if bar.open_us + 4 * HOUR_US <= instant),
    )
    assert extended.at(instant) == prefix.at(instant)
    if offset < 4:
        assert extended.at(instant).signed_efficiency == original.at(T).signed_efficiency


@pytest.mark.parametrize(
    "resolution,missing",
    [("hourly", True), ("hourly", False), ("context", True), ("context", False)],
)
def test_missing_and_partial_bars_reset_eligibility(resolution, missing):
    original = source()
    hours, context = original.hourly, original.context
    bars = list(getattr(original, resolution))
    if missing:
        del bars[-10]
    else:
        bars[-10] = replace(bars[-10], complete=False)
    changed = FeatureSource(
        tuple(bars) if resolution == "hourly" else hours,
        tuple(bars) if resolution == "context" else context,
    )
    with pytest.raises(IneligibleSignal):
        changed.decision(T, "ALIGNED")


def test_timing_delay_uses_old_condition_and_current_reference():
    original = source()
    assert original.decision(T, "ALIGNED")[0]
    emits, feature, reference = original.decision(T, "ALIGNED", 1)
    assert not emits and feature.asof_us == T - HOUR_US and reference == 101.0
    with pytest.raises(ValueError, match="undeclared"):
        original.decision(T, "ALIGNED", 2)


def inputs(count=1440):
    return ResearchInputs(
        source(),
        T + np.arange(count) * MINUTE,
        np.full(count, 100.0),
        np.full(count, 101.0),
        np.full(count, 99.0),
        np.full(count, 100.0),
    )


def test_intraminute_exit_cannot_release_same_open_entry():
    data = inputs()
    data.minute_high[0], data.minute_low[0] = 105, 97
    result, available = trade_at(data, T, 100, "ALIGNED", "DEFAULT", "SYNTHETIC")
    assert result["reason"] == "STOP"
    assert result["exit_us"] == T < available == T + MINUTE
    assert result["net_r"] < result["gross_r"] == -1


def test_expiry_is_available_at_next_boundary_and_cost_profiles_monotone():
    results = [
        trade_at(inputs(), T, 100, "ALIGNED", profile, "SYNTHETIC")
        for profile in ("ZERO", "DEFAULT", "DOUBLE")
    ]
    assert all(available == T + 24 * HOUR_US for _, available in results)
    assert all(result["reason"] == "EXPIRY" for result, _ in results)
    assert results[0][0]["net_r"] == 0 > results[1][0]["net_r"] > results[2][0]["net_r"]


def test_gap_unresolved_quarantines_original_horizon_without_pnl():
    data = inputs()
    for key in ("minute_times", "minute_open", "minute_high", "minute_low", "minute_close"):
        setattr(data, key, np.delete(getattr(data, key), 10))
    result, available = trade_at(data, T, 100, "ALIGNED", "DEFAULT", "SYNTHETIC")
    assert result["status"] == "UNRESOLVED" and result["reason"] == "UNRESOLVED_DATA_GAP"
    assert "net_r" not in result and available == T + 24 * HOUR_US


def test_missing_entry_is_invalid_and_post_cutoff_source_rejected():
    data = inputs()
    data.minute_times = data.minute_times + MINUTE
    result, _ = trade_at(data, T, 100, "ALIGNED", "DEFAULT", "SYNTHETIC")
    assert result["status"] == "INVALID"
    with pytest.raises(ValueError, match="development"):
        FeatureSource((FeatureBar(utc_us("2025-01-01T00:00:00Z"), 1, 1, 1),), ())


def test_configuration_rejects_parameter_tuning_and_fourth_variant():
    root = Path(__file__).resolve().parents[2]
    config = json.loads((root / "research/configs/wp004/aligned.json").read_text())
    validate_config(config)
    config["volume_multiplier"] = 2.1
    with pytest.raises(ValueError, match="frozen"):
        validate_config(config)
    config["volume_multiplier"] = 2
    config["variant"] = "ALIGNED_WITH_NEW_GATE"
    with pytest.raises(ValueError, match="frozen"):
        validate_config(config)


def test_delayed_emission_uses_previous_features_but_latest_barriers():
    original = source()
    extended = FeatureSource((*original.hourly, FeatureBar(T, 103, 102, 10)), original.context)
    emits, feature, reference = extended.decision(T + HOUR_US, "ALIGNED", 1)
    assert emits and feature.asof_us == T and reference == 102
    data = inputs()
    result, _ = trade_at(data, T, reference, "ALIGNED", "DELAY_1H", "SYNTHETIC")
    assert result["record"]["stop"] == "99.96"


def test_previous_clock_only_missing_observation_blocks_all_profiles():
    original = source()
    hours = original.hourly[-25:]  # Current feature exists, prior-clock feature does not.
    limited = FeatureSource(hours, original.context)
    assert limited.at(T).breakout
    for variant in ("ALIGNED", "REGIME_ONLY", "PARTICIPATION_ONLY"):
        for delay in (0, 1):
            with pytest.raises(IneligibleSignal):
                limited.decision(T, variant, delay)


def test_mutated_manifest_rejected_before_parquet_inspection(tmp_path, monkeypatch):
    import app.research.continuation_lab as module

    manifest = tmp_path / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"symbol":"BTCUSDT"}')
    monkeypatch.setattr(module.pq, "read_table", lambda *_: pytest.fail("unverified table read"))
    with pytest.raises(ValueError, match="manifest bytes"):
        ResearchInputs.load(tmp_path)


def test_protocol_mutation_rejected_before_features_or_path_access():
    from app.research.continuation_lab import ContinuationLab
    from app.research.evaluation_protocol import load_protocol

    protocol = load_protocol()
    protocol["purge_hours"] = 1
    with pytest.raises(ValueError, match="frozen"):
        ContinuationLab(None, protocol)


@pytest.mark.parametrize("intrabar,expected", [(True, 6), (False, 12)])
def test_lab_orchestration_respects_position_availability(monkeypatch, intrabar, expected):
    from types import SimpleNamespace

    import app.research.continuation_lab as module
    from app.research.continuation import Features
    from app.research.evaluation_protocol import load_protocol

    monkeypatch.setattr(
        module, "range", lambda start, _end, step: [start, start + step], raising=False
    )
    fake_features = SimpleNamespace(
        decision=lambda t, _v, _d: (True, Features(t, 100, True, True, True, 1, 2), 100)
    )

    def synthetic_execution(_inputs, signal, _reference, _variant, _profile, _run):
        exit_us = signal + HOUR_US
        available = exit_us + MINUTE if intrabar else exit_us
        return {
            "signal_us": signal,
            "status": "VALID",
            "exit_us": exit_us,
            "net_r": 0.1,
            "gross_r": 0.2,
        }, available

    monkeypatch.setattr(module, "trade_at", synthetic_execution)
    lab = module.ContinuationLab(SimpleNamespace(features=fake_features), load_protocol())
    root = Path(__file__).resolve().parents[2]
    config = json.loads((root / "research/configs/wp004/aligned.json").read_text())
    trial = lab.run_trial(config, "ALIGNED:DEFAULT")
    assert trial["summary"]["metrics"]["trade_count"] == expected
    assert sum(row["suppressed_conditions"] for row in trial["clock_diagnostics"]) == 12 - expected
