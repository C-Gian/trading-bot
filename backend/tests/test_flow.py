"""Synthetic tests for the frozen order-flow rules. No market data is loaded."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.research.evaluation_protocol import HOUR_US, utc_us
from app.research.flow import (
    BALANCE,
    CONTEXT_US,
    STRATEGY_VERSION,
    VARIANTS,
    FlowSource,
    IneligibleFlowSignal,
    context_open,
)
from app.research.flow_lab import config_path, validate_config
from app.research.order_flow import FlowBucket

ROOT = Path(__file__).resolve().parents[2]
START = utc_us("2020-01-06T00:00:00Z")
SIGNAL = START + 40 * HOUR_US


def _bucket(open_us: int, share: float | None, *, close=101.0, open_price=100.0, eligible=True):
    volume = 100.0
    return FlowBucket(
        open_us=open_us,
        source_minutes=60 if open_us % CONTEXT_US or True else 240,
        complete=eligible,
        quarantined=False,
        eligible=eligible and share is not None,
        open=open_price,
        close=close,
        volume=volume,
        quote_volume=volume * 100.0,
        taker_base=volume * (share or 0.0),
        taker_quote=volume * (share or 0.0) * 100.0,
        share=share,
    )


def _source(
    *,
    current: float = 0.7,
    previous: float = 0.4,
    context: float = 0.6,
    current_close: float = 101.0,
    current_open: float = 100.0,
    baseline: float = 0.4,
    hourly_overrides: dict[int, FlowBucket] | None = None,
    context_overrides: dict[int, FlowBucket] | None = None,
) -> FlowSource:
    """A synthetic substrate where only the decision buckets differ from the baseline."""
    hourly = {
        START + index * HOUR_US: _bucket(START + index * HOUR_US, baseline) for index in range(60)
    }
    hourly[SIGNAL - HOUR_US] = _bucket(
        SIGNAL - HOUR_US, current, close=current_close, open_price=current_open
    )
    hourly[SIGNAL - 2 * HOUR_US] = _bucket(SIGNAL - 2 * HOUR_US, previous)
    fours = {
        START + index * CONTEXT_US: _bucket(START + index * CONTEXT_US, baseline)
        for index in range(20)
    }
    fours[context_open(SIGNAL)] = _bucket(context_open(SIGNAL), context)
    hourly.update(hourly_overrides or {})
    fours.update(context_overrides or {})
    return FlowSource(tuple(hourly.values()), tuple(fours.values()))


def test_context_bucket_never_contains_the_current_signal_bar():
    for hours in range(24):
        signal = START + hours * HOUR_US
        opened = context_open(signal)
        closed = opened + CONTEXT_US
        assert closed <= signal - HOUR_US, "context must close at or before the signal hour opens"
        assert opened % CONTEXT_US == 0, "context must stay UTC aligned"
        staleness = signal - closed
        assert HOUR_US <= staleness <= 4 * HOUR_US


def test_flow_core_requires_transition_and_dominant_context():
    emits, feature, reference = _source().decision(SIGNAL, "FLOW_CORE")
    assert emits and feature.transition and feature.context_dominant
    assert feature.previous_non_dominant and feature.current_dominant
    assert reference == 101.0
    # Already dominant beforehand: no transition.
    emits, feature, _ = _source(previous=0.6).decision(SIGNAL, "FLOW_CORE")
    assert not emits and not feature.previous_non_dominant
    # Still not dominant now: the transition has not happened.
    emits, feature, _ = _source(current=0.5).decision(SIGNAL, "FLOW_CORE")
    assert not emits and not feature.current_dominant
    # A non-dominant slower context suppresses the same transition.
    emits, feature, _ = _source(context=0.5).decision(SIGNAL, "FLOW_CORE")
    assert not emits and not feature.context_dominant


def test_the_balance_point_is_a_strict_inequality_at_exactly_one_half():
    assert BALANCE == 0.5
    # Exactly 0.5 counts as non-dominant on both clocks.
    assert not _source(current=0.5).decision(SIGNAL, "FLOW_CORE")[0]
    assert _source(previous=0.5).decision(SIGNAL, "FLOW_CORE")[0]
    assert not _source(context=0.5).decision(SIGNAL, "FLOW_CORE")[0]
    # The smallest representable step above the balance point already qualifies.
    import math

    assert _source(current=math.nextafter(0.5, 1.0)).decision(SIGNAL, "FLOW_CORE")[0]


def test_price_response_variant_adds_only_close_above_open():
    up = _source(current_close=101.0, current_open=100.0)
    down = _source(current_close=99.0, current_open=100.0)
    flat = _source(current_close=100.0, current_open=100.0)
    assert up.decision(SIGNAL, "FLOW_CORE")[0]
    assert down.decision(SIGNAL, "FLOW_CORE")[0]
    assert flat.decision(SIGNAL, "FLOW_CORE")[0]
    assert up.decision(SIGNAL, "FLOW_PRICE_RESPONSE")[0]
    assert not down.decision(SIGNAL, "FLOW_PRICE_RESPONSE")[0]
    assert not flat.decision(SIGNAL, "FLOW_PRICE_RESPONSE")[0]


def test_core_has_no_price_condition_at_all():
    """A collapsing price must not stop the core rule; only flow decides."""
    crashing = _source(current_close=1.0, current_open=100_000.0)
    emits, feature, reference = crashing.decision(SIGNAL, "FLOW_CORE")
    assert emits and not feature.price_response
    assert reference == 1.0, "the reference is still the current completed close"


def test_delay_control_shifts_the_condition_but_not_the_reference():
    delayed_current = _bucket(SIGNAL - 2 * HOUR_US, 0.7)
    delayed_previous = _bucket(SIGNAL - 3 * HOUR_US, 0.4)
    engine = _source(
        current=0.45,
        previous=0.7,
        hourly_overrides={
            SIGNAL - 2 * HOUR_US: delayed_current,
            SIGNAL - 3 * HOUR_US: delayed_previous,
        },
        context_overrides={
            context_open(SIGNAL - HOUR_US): _bucket(context_open(SIGNAL - HOUR_US), 0.6)
        },
    )
    immediate, _, _ = engine.decision(SIGNAL, "FLOW_CORE")
    delayed, feature, reference = engine.decision(SIGNAL, "FLOW_CORE", 1)
    assert not immediate and delayed
    assert feature.asof_us == SIGNAL - HOUR_US
    assert reference == engine.at(SIGNAL).reference


def test_an_ineligible_or_missing_bucket_produces_no_signal():
    quarantined = _bucket(SIGNAL - HOUR_US, 0.7)
    quarantined = FlowBucket(**{**quarantined.__dict__, "quarantined": True, "eligible": False})
    with pytest.raises(IneligibleFlowSignal):
        _source(hourly_overrides={SIGNAL - HOUR_US: quarantined}).at(SIGNAL)
    untraded = _bucket(SIGNAL - 2 * HOUR_US, None)
    with pytest.raises(IneligibleFlowSignal):
        _source(hourly_overrides={SIGNAL - 2 * HOUR_US: untraded}).at(SIGNAL)
    context = context_open(SIGNAL)
    stale = FlowBucket(**{**_bucket(context, 0.6).__dict__, "complete": False, "eligible": False})
    with pytest.raises(IneligibleFlowSignal):
        _source(context_overrides={context: stale}).at(SIGNAL)


def test_post_cutoff_and_misaligned_clocks_are_refused():
    engine = _source()
    with pytest.raises(ValueError, match="hourly development boundary"):
        engine.at(utc_us("2025-01-02T00:00:00Z"))
    with pytest.raises(ValueError, match="hourly development boundary"):
        engine.at(SIGNAL + 60_000_000)


def test_undeclared_variant_or_perturbation_is_refused():
    engine = _source()
    with pytest.raises(ValueError, match="undeclared strategy variant"):
        engine.decision(SIGNAL, "FLOW_ALTERNATE")
    with pytest.raises(ValueError, match="undeclared strategy variant"):
        engine.decision(SIGNAL, "FLOW_CORE", 2)


def test_committed_configs_are_exactly_the_two_frozen_variants():
    directory = ROOT / "research/configs/wp007"
    files = sorted(path.name for path in directory.glob("*.json"))
    assert files == ["flow_core.json", "flow_price_response.json"]
    variants = set()
    for name in files:
        config = json.loads((directory / name).read_text(encoding="utf-8"))
        validate_config(config)
        variants.add(config["variant"])
        assert config["strategy_version"] == STRATEGY_VERSION
        assert config_path(config["variant"]).endswith(name)
    assert variants == set(VARIANTS)


@pytest.mark.parametrize(
    "field,value",
    [
        ("balance_threshold", 0.55),
        ("balance_threshold", 0.51),
        ("context_timeframe_minutes", 60),
        ("stop_fraction", 0.03),
        ("target_fraction", 0.05),
        ("max_hold_minutes", 720),
    ],
)
def test_any_numeric_drift_in_a_config_is_refused(field, value):
    config = json.loads(
        (ROOT / "research/configs/wp007/flow_core.json").read_text(encoding="utf-8")
    )
    config[field] = value
    with pytest.raises(ValueError, match="frozen structural variant"):
        validate_config(config)


def test_extra_profile_or_gate_in_a_config_is_refused():
    config = json.loads(
        (ROOT / "research/configs/wp007/flow_core.json").read_text(encoding="utf-8")
    )
    with pytest.raises(ValueError, match="frozen structural variant"):
        validate_config({**config, "profiles": [*config["profiles"], "TRIPLE"]})
    for gate in ("breakout_hours", "sma_hours", "up_to_down_ratio", "volume_multiplier"):
        with pytest.raises(ValueError, match="frozen structural variant"):
            validate_config({**config, gate: 24})
