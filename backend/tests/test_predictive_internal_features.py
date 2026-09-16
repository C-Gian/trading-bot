"""Causality and edge-rule proofs for the frozen internal feature set.

Every claim here is hand-computable on a deterministic synthetic series. Nothing in this
file touches market data.
"""

from __future__ import annotations

import math

import pytest
from app.predictive.internal_features import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    LOOKBACK_BAR_INCOMPLETE,
    LOOKBACK_BAR_MISSING,
    MAX_LOOKBACK_HOURS,
    NEGATIVE_VOLUME,
    NON_FINITE_FEATURE,
    NON_POSITIVE_CLOSE,
    NON_POSITIVE_MEAN_VOLUME,
    REQUIRED_BARS,
    CausalView,
    OhlcvBar,
    assert_feature_causality,
    build_feature_vector,
    feature_source_open_times,
    index_ohlcv,
)
from app.predictive.labels import HOUR_SECONDS, LabelError

DECISION = MAX_LOOKBACK_HOURS * HOUR_SECONDS
GROWTH = 1.01
STEP = math.log(GROWTH)


def geometric_bars(extra: int = 0) -> list[OhlcvBar]:
    """A strictly geometric series: every hourly return is exactly `log(1.01)`."""
    bars = []
    for index in range(REQUIRED_BARS + extra):
        close = 100.0 * GROWTH**index
        bars.append(
            OhlcvBar(
                open_time=index * HOUR_SECONDS,
                high=close,
                low=close * 0.99,
                close=close,
                volume=50.0,
                complete=True,
            )
        )
    return bars


def flat_bars(close: float = 100.0, volume: float = 50.0) -> list[OhlcvBar]:
    return [
        OhlcvBar(
            open_time=index * HOUR_SECONDS,
            high=close,
            low=close,
            close=close,
            volume=volume,
            complete=True,
        )
        for index in range(REQUIRED_BARS)
    ]


def vector(bars):
    values, reason = build_feature_vector(index_ohlcv(bars), DECISION)
    return values, reason


def test_the_frozen_feature_set_is_exactly_eighteen_ordered_names():
    assert FEATURE_COUNT == 18
    assert FEATURE_NAMES[0] == "logret_1h"
    assert FEATURE_NAMES[-1] == "log_volume_regime_24_168h"
    assert len(set(FEATURE_NAMES)) == FEATURE_COUNT


def test_every_value_is_hand_computable_on_a_geometric_series():
    values, reason = vector(geometric_bars())
    assert reason is None and values is not None
    named = dict(zip(FEATURE_NAMES, values, strict=True))
    for hours in (1, 6, 24, 72, 168):
        assert named[f"logret_{hours}h"] == pytest.approx(hours * STEP, abs=1e-12)
    for hours in (6, 24, 72, 168):
        assert named[f"rv_{hours}h"] == pytest.approx(math.sqrt(hours) * STEP, abs=1e-12)
    for hours in (24, 72, 168):
        # A perfectly efficient path: the signed move equals the distance travelled.
        assert named[f"signed_efficiency_{hours}h"] == pytest.approx(1.0, abs=1e-12)
    assert named["up_fraction_24h"] == 1.0
    assert named["up_fraction_168h"] == 1.0
    # The close is the running high, so it sits at the top of both rolling ranges.
    assert named["close_position_24h"] == pytest.approx(1.0, abs=1e-12)
    assert named["close_position_168h"] == pytest.approx(1.0, abs=1e-12)
    assert named["log_volume_relative_24h"] == pytest.approx(0.0, abs=1e-12)
    assert named["log_volume_regime_24_168h"] == pytest.approx(0.0, abs=1e-12)


def test_the_causal_surface_is_exactly_the_169_bars_up_to_the_decision_instant():
    sources = feature_source_open_times(DECISION)
    assert len(sources) == REQUIRED_BARS == MAX_LOOKBACK_HOURS + 1
    assert sources[-1] == DECISION
    assert sources[0] == DECISION - MAX_LOOKBACK_HOURS * HOUR_SECONDS
    assert max(sources) <= DECISION


def test_mutating_bars_after_the_decision_instant_cannot_change_the_vector():
    bars = geometric_bars(extra=48)
    baseline, _ = vector(bars)
    mutated = [
        bar
        if bar.open_time <= DECISION
        else OhlcvBar(
            open_time=bar.open_time,
            high=bar.high * 7.0,
            low=bar.low / 7.0,
            close=bar.close * 7.0,
            volume=bar.volume * 7.0,
            complete=bar.complete,
        )
        for bar in bars
    ]
    assert vector(mutated)[0] == baseline


def test_the_look_ahead_guard_rejects_a_read_after_the_instant_it_guards():
    bars = geometric_bars(extra=24)
    # The real feature build passes its own guard at its own decision instant.
    assert_feature_causality(index_ohlcv(bars), DECISION)
    # Guarding one hour earlier makes the decision bar itself a forward read, and the
    # guard fires on the real code path rather than on a restated intention.
    guarded = CausalView(index_ohlcv(bars), DECISION - HOUR_SECONDS)
    with pytest.raises(LabelError, match="look-ahead"):
        build_feature_vector(guarded, DECISION)


@pytest.mark.parametrize("hours", [1, 6, 24, 72, 168])
def test_each_signed_lookback_reads_exactly_its_own_origin_close(hours):
    """`logret_h` reads `c_T` and `c_{T-h}` and nothing else, so only it moves."""
    bars = geometric_bars()
    target = DECISION - hours * HOUR_SECONDS
    perturbed = [
        OhlcvBar(
            open_time=bar.open_time,
            high=bar.high,
            low=bar.low,
            close=bar.close * 1.05 if bar.open_time == target else bar.close,
            volume=bar.volume,
            complete=bar.complete,
        )
        for bar in bars
    ]
    before = dict(zip(FEATURE_NAMES, vector(bars)[0], strict=True))
    after = dict(zip(FEATURE_NAMES, vector(perturbed)[0], strict=True))
    for other in (1, 6, 24, 72, 168):
        name = f"logret_{other}h"
        if other == hours:
            assert before[name] != after[name]
        else:
            assert before[name] == after[name]


@pytest.mark.parametrize(
    ("offset", "spanned"),
    [(3, (6, 24, 72, 168)), (12, (24, 72, 168)), (48, (72, 168)), (100, (168,))],
)
def test_each_window_family_spans_exactly_the_hours_it_claims(offset, spanned):
    """Perturbing `c_{T-k}` moves every rolling window whose lookback reaches k, and no other."""
    bars = geometric_bars()
    target = DECISION - offset * HOUR_SECONDS
    perturbed = [
        OhlcvBar(
            open_time=bar.open_time,
            high=bar.high,
            low=bar.low,
            close=bar.close * 1.05 if bar.open_time == target else bar.close,
            volume=bar.volume,
            complete=bar.complete,
        )
        for bar in bars
    ]
    before = dict(zip(FEATURE_NAMES, vector(bars)[0], strict=True))
    after = dict(zip(FEATURE_NAMES, vector(perturbed)[0], strict=True))
    for hours in (6, 24, 72, 168):
        name = f"rv_{hours}h"
        if hours in spanned:
            assert before[name] != after[name], name
        else:
            assert before[name] == after[name], name


def test_a_bar_before_the_maximum_lookback_cannot_move_anything():
    bars = geometric_bars()
    outside = DECISION - (MAX_LOOKBACK_HOURS + 1) * HOUR_SECONDS
    extended = [
        OhlcvBar(
            open_time=outside,
            high=1e9,
            low=1e-9,
            close=1e9,
            volume=1e9,
            complete=True,
        ),
        *bars,
    ]
    assert vector(extended)[0] == vector(bars)[0]


@pytest.mark.parametrize("offset", [0, 1, 84, MAX_LOOKBACK_HOURS])
def test_a_missing_lookback_bar_makes_the_whole_vector_unavailable(offset):
    bars = [bar for bar in geometric_bars() if bar.open_time != DECISION - offset * HOUR_SECONDS]
    values, reason = vector(bars)
    assert values is None and reason == LOOKBACK_BAR_MISSING


def test_an_incomplete_lookback_bar_makes_the_whole_vector_unavailable():
    bars = [
        OhlcvBar(
            open_time=bar.open_time,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            complete=bar.open_time != DECISION - 5 * HOUR_SECONDS,
        )
        for bar in geometric_bars()
    ]
    values, reason = vector(bars)
    assert values is None and reason == LOOKBACK_BAR_INCOMPLETE


def test_a_non_positive_close_and_a_negative_volume_are_typed_and_fail_closed():
    bars = flat_bars()
    broken = list(bars)
    broken[10] = OhlcvBar(
        open_time=broken[10].open_time,
        high=100.0,
        low=100.0,
        close=0.0,
        volume=50.0,
        complete=True,
    )
    assert vector(broken) == (None, NON_POSITIVE_CLOSE)

    negative = list(bars)
    negative[10] = OhlcvBar(
        open_time=negative[10].open_time,
        high=100.0,
        low=100.0,
        close=100.0,
        volume=-1.0,
        complete=True,
    )
    assert vector(negative) == (None, NEGATIVE_VOLUME)


def test_a_zero_mean_volume_denominator_fails_closed_instead_of_dividing():
    bars = flat_bars(volume=0.0)
    assert vector(bars) == (None, NON_POSITIVE_MEAN_VOLUME)


def test_a_zero_decision_volume_fails_closed_rather_than_taking_log_of_zero():
    bars = flat_bars()
    bars[-1] = OhlcvBar(
        open_time=bars[-1].open_time,
        high=100.0,
        low=100.0,
        close=100.0,
        volume=0.0,
        complete=True,
    )
    assert vector(bars) == (None, NON_FINITE_FEATURE)


def test_the_two_named_degenerate_cases_have_frozen_values_rather_than_abstaining():
    values, reason = vector(flat_bars())
    assert reason is None and values is not None
    named = dict(zip(FEATURE_NAMES, values, strict=True))
    # A perfectly flat window travels no distance and has no range.
    for hours in (24, 72, 168):
        assert named[f"signed_efficiency_{hours}h"] == 0.0
    for hours in (24, 168):
        assert named[f"close_position_{hours}h"] == 0.5
    for hours in (6, 24, 72, 168):
        assert named[f"rv_{hours}h"] == 0.0
    assert named["up_fraction_24h"] == 0.0


def test_close_position_places_the_close_inside_a_hand_built_range():
    bars = flat_bars()
    # One bar in the last 24 hours printed a high of 120; the close is still 100.
    bars[-5] = OhlcvBar(
        open_time=bars[-5].open_time,
        high=120.0,
        low=80.0,
        close=100.0,
        volume=50.0,
        complete=True,
    )
    named = dict(zip(FEATURE_NAMES, vector(bars)[0], strict=True))
    assert named["close_position_24h"] == pytest.approx((100.0 - 80.0) / (120.0 - 80.0))
    assert named["close_position_168h"] == pytest.approx(0.5)


def test_relative_volume_is_hand_computable():
    bars = flat_bars()
    bars[-1] = OhlcvBar(
        open_time=bars[-1].open_time,
        high=100.0,
        low=100.0,
        close=100.0,
        volume=100.0,
        complete=True,
    )
    named = dict(zip(FEATURE_NAMES, vector(bars)[0], strict=True))
    mean_24 = (23 * 50.0 + 100.0) / 24
    mean_168 = (167 * 50.0 + 100.0) / 168
    assert named["log_volume_relative_24h"] == pytest.approx(math.log(100.0 / mean_24))
    assert named["log_volume_regime_24_168h"] == pytest.approx(math.log(mean_24 / mean_168))


def test_the_vector_is_unavailable_before_enough_history_exists():
    bars = geometric_bars()
    values, reason = build_feature_vector(index_ohlcv(bars), DECISION - HOUR_SECONDS)
    assert values is None and reason == LOOKBACK_BAR_MISSING
