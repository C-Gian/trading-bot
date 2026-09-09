"""Synthetic tests for the frozen pullback-recovery rules. No market data is loaded."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.research.continuation import FeatureBar, IneligibleSignal
from app.research.evaluation_protocol import HOUR_US, utc_us
from app.research.pullback import (
    CONTEXT_BARS,
    HOURLY_BARS,
    SMA_HOURS,
    VARIANTS,
    RecoveryFeatureSource,
)
from app.research.pullback_lab import config_path, validate_config

ROOT = Path(__file__).resolve().parents[2]
START = utc_us("2020-01-01T00:00:00Z")
SIGNAL = START + 200 * HOUR_US


def hourly(closes: dict[int, float], highs: dict[int, float] | None = None, count: int = 260):
    """Hourly bars ending well before the signal, with per-offset overrides."""
    highs = highs or {}
    return tuple(
        FeatureBar(
            START + index * HOUR_US,
            highs.get(index, max(closes.get(index, 100.0), 100.0) + 5.0),
            closes.get(index, 100.0),
            1000.0,
        )
        for index in range(count)
    )


def context(*, persistent: bool, count: int = 60):
    """Rising or oscillating 4h closes; the descriptor is the inherited WP-004 primitive."""
    values = []
    price = 100.0
    for index in range(count):
        price += 1.0 if persistent else (1.0 if index % 2 == 0 else -1.0)
        values.append(price)
    return tuple(
        FeatureBar(START + index * 4 * HOUR_US, value + 5.0, value, 1000.0)
        for index, value in enumerate(values)
    )


def source(closes, highs=None, *, persistent=True):
    return RecoveryFeatureSource(hourly(closes, highs), context(persistent=persistent))


def recovery_closes(*, previous: float, current: float, base: float = 100.0):
    """Flat history so SMA24 is the base level; only the two decision bars vary."""
    current_index = SIGNAL // HOUR_US - START // HOUR_US - 1
    return {index: base for index in range(300)} | {
        current_index - 1: previous,
        current_index: current,
    }


def test_windows_and_means_use_only_completed_contiguous_bars():
    features = source(recovery_closes(previous=99.0, current=101.0)).at(SIGNAL)
    assert features.asof_us == SIGNAL and features.reference == 101.0
    # SMA24_t spans the 24 closes ending with the current bar, so it holds both
    # decision closes; SMA24_prev ends one hour earlier and holds only the previous one.
    assert features.sma24 == pytest.approx((100.0 * 22 + 99.0 + 101.0) / SMA_HOURS)
    assert features.sma24_previous == pytest.approx((100.0 * 23 + 99.0) / SMA_HOURS)
    assert features.previous_close == 99.0 and features.recovery_event
    assert HOURLY_BARS == SMA_HOURS + 1 and CONTEXT_BARS == 43


def test_recovery_core_requires_below_then_above_and_persistence():
    below_then_above = recovery_closes(previous=99.0, current=101.0)
    emits, features, reference = source(below_then_above).decision(SIGNAL, "RECOVERY_CORE")
    assert emits and features.recovery_event and features.persistent_up
    assert features.below_mean_before and features.recovered_above_mean
    assert reference == 101.0
    # Already above the mean beforehand: no recovery transition.
    emits, features, _ = source(recovery_closes(previous=105.0, current=106.0)).decision(
        SIGNAL, "RECOVERY_CORE"
    )
    assert not emits and not features.below_mean_before
    # Still at or below the mean now: the recovery has not happened.
    emits, features, _ = source(recovery_closes(previous=99.0, current=99.5)).decision(
        SIGNAL, "RECOVERY_CORE"
    )
    assert not emits and not features.recovered_above_mean
    # Exactly at the mean counts as "at or below", and only "above" recovers.
    emits, _, _ = source(recovery_closes(previous=100.0, current=100.0)).decision(
        SIGNAL, "RECOVERY_CORE"
    )
    assert not emits
    # Without a persistent 4h uptrend the same recovery is suppressed.
    emits, features, _ = source(below_then_above, persistent=False).decision(
        SIGNAL, "RECOVERY_CORE"
    )
    assert not emits and not features.persistent_up


def test_recovery_confirm_adds_only_the_previous_hourly_high():
    closes = recovery_closes(previous=99.0, current=101.0)
    current_index = SIGNAL // HOUR_US - START // HOUR_US - 1
    low_high = source(closes, {current_index - 1: 100.5})
    high_high = source(closes, {current_index - 1: 130.0})
    assert low_high.decision(SIGNAL, "RECOVERY_CORE")[0]
    assert high_high.decision(SIGNAL, "RECOVERY_CORE")[0]
    assert low_high.decision(SIGNAL, "RECOVERY_CONFIRM")[0]
    assert not high_high.decision(SIGNAL, "RECOVERY_CONFIRM")[0]


def test_no_breakout_no_sma168_and_no_volume_condition():
    """A 24h-high breakout is neither required nor sufficient; volume is never read."""
    current_index = SIGNAL // HOUR_US - START // HOUR_US - 1
    closes = recovery_closes(previous=99.0, current=101.0)
    # Every prior high is far above the current close, so no breakout exists at all.
    highs = {index: 500.0 for index in range(300)} | {current_index: 101.0}
    emits, _, _ = source(closes, highs).decision(SIGNAL, "RECOVERY_CORE")
    assert emits
    # A fresh high with no preceding weakness still emits nothing.
    extended = {index: 100.0 for index in range(300)} | {
        current_index - 1: 120.0,
        current_index: 130.0,
    }
    assert not source(extended).decision(SIGNAL, "RECOVERY_CORE")[0]
    quiet = RecoveryFeatureSource(
        tuple(
            FeatureBar(bar.open_us, bar.high, bar.close, 0.0)
            for bar in hourly(recovery_closes(previous=99.0, current=101.0))
        ),
        context(persistent=True),
    )
    assert quiet.decision(SIGNAL, "RECOVERY_CORE")[0]


def test_delay_control_shifts_the_condition_but_not_the_reference():
    current_index = SIGNAL // HOUR_US - START // HOUR_US - 1
    closes = {index: 100.0 for index in range(300)} | {
        current_index - 2: 99.0,
        current_index - 1: 101.0,
        current_index: 100.5,
    }
    engine = source(closes)
    immediate, _, _ = engine.decision(SIGNAL, "RECOVERY_CORE")
    delayed, features, reference = engine.decision(SIGNAL, "RECOVERY_CORE", 1)
    assert not immediate and delayed
    assert features.asof_us == SIGNAL - HOUR_US
    assert reference == 100.5


def test_incomplete_or_missing_lookback_is_ineligible():
    closes = recovery_closes(previous=99.0, current=101.0)
    bars = list(hourly(closes))
    quarantined = tuple(
        FeatureBar(bar.open_us, bar.high, bar.close, bar.volume, index != 190)
        for index, bar in enumerate(bars)
    )
    engine = RecoveryFeatureSource(quarantined, context(persistent=True))
    with pytest.raises(IneligibleSignal):
        engine.at(SIGNAL)
    gapped = RecoveryFeatureSource(
        tuple(bar for index, bar in enumerate(bars) if index != 185), context(persistent=True)
    )
    with pytest.raises(IneligibleSignal):
        gapped.at(SIGNAL)


def test_post_cutoff_and_misaligned_clocks_are_refused():
    engine = source(recovery_closes(previous=99.0, current=101.0))
    with pytest.raises(ValueError, match="hourly development boundary"):
        engine.at(utc_us("2025-01-02T00:00:00Z"))
    with pytest.raises(ValueError, match="hourly development boundary"):
        engine.at(SIGNAL + 60_000_000)


def test_undeclared_variant_or_perturbation_is_refused():
    engine = source(recovery_closes(previous=99.0, current=101.0))
    with pytest.raises(ValueError, match="undeclared strategy variant"):
        engine.decision(SIGNAL, "RECOVERY_ALTERNATE")
    with pytest.raises(ValueError, match="undeclared strategy variant"):
        engine.decision(SIGNAL, "RECOVERY_CORE", 2)


def test_committed_configs_are_exactly_the_two_frozen_variants():
    directory = ROOT / "research/configs/wp006"
    files = sorted(path.name for path in directory.glob("*.json"))
    assert files == ["recovery_confirm.json", "recovery_core.json"]
    variants = set()
    for name in files:
        config = json.loads((directory / name).read_text(encoding="utf-8"))
        validate_config(config)
        variants.add(config["variant"])
        assert config_path(config["variant"]).endswith(name)
    assert variants == set(VARIANTS)


@pytest.mark.parametrize(
    "field,value",
    [
        ("sma_hours", 20),
        ("up_to_down_ratio", 3),
        ("stop_fraction", 0.03),
        ("target_fraction", 0.05),
        ("max_hold_minutes", 720),
        ("context_increments", 30),
    ],
)
def test_any_numeric_drift_in_a_config_is_refused(field, value):
    config = json.loads(
        (ROOT / "research/configs/wp006/recovery_core.json").read_text(encoding="utf-8")
    )
    config[field] = value
    with pytest.raises(ValueError, match="frozen structural variant"):
        validate_config(config)


def test_extra_profile_or_gate_in_a_config_is_refused():
    config = json.loads(
        (ROOT / "research/configs/wp006/recovery_core.json").read_text(encoding="utf-8")
    )
    with pytest.raises(ValueError, match="frozen structural variant"):
        validate_config({**config, "profiles": [*config["profiles"], "TRIPLE"]})
    with pytest.raises(ValueError, match="frozen structural variant"):
        validate_config({**config, "volume_multiplier": 2})
