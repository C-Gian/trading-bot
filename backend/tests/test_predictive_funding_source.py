"""Point-in-time and causality proofs for the Stage-2 settled-funding source.

Every claim here is hand-computable on a deterministic synthetic timeline. Nothing in this
file reads the canonical artifact.
"""

from __future__ import annotations

import math

import pytest
from app.predictive.funding_source import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    FORBIDDEN_SOURCE_FIELDS,
    INSUFFICIENT_PRIOR_SETTLEMENTS,
    MAX_SETTLEMENT_GAP_SECONDS,
    MICROSECONDS,
    NON_FINITE_FUNDING_FEATURE,
    REQUIRED_SETTLEMENTS,
    SETTLEMENT_GAP_TOO_LARGE,
    UNAVAILABILITY_TAXONOMY,
    FundingFeatureError,
    SettledFundingSource,
    build_funding_features,
    feature_source_times,
)

EIGHT_HOURS = 8 * 60 * 60


def source_from(hours: list[int], rates: list[float]) -> SettledFundingSource:
    return SettledFundingSource(
        times_us=tuple(hour * 3600 * MICROSECONDS for hour in hours),
        rates=tuple(rates),
    )


def regular_source(count: int = 10) -> SettledFundingSource:
    """Settlements every eight hours with rates 1e-4, 2e-4, … in order."""
    hours = [index * 8 for index in range(count)]
    rates = [(index + 1) * 1e-4 for index in range(count)]
    return source_from(hours, rates)


def test_the_frozen_feature_set_is_exactly_five_ordered_names():
    assert FEATURE_COUNT == 5
    assert FEATURE_NAMES == (
        "LATEST_SETTLED_RATE",
        "MEAN_LAST_3_SETTLEMENTS",
        "MEAN_LAST_9_SETTLEMENTS",
        "DELTA_LATEST_PREVIOUS",
        "STD_LAST_9_SETTLEMENTS",
    )
    assert REQUIRED_SETTLEMENTS == 9
    assert MAX_SETTLEMENT_GAP_SECONDS == EIGHT_HOURS + 60


def test_the_feature_set_carries_no_stage_one_internal_price_feature():
    """The Stage-1 family is rejected; none of its features may reappear here."""
    from app.predictive.internal_features import FEATURE_NAMES as STAGE1_FEATURES

    assert not set(FEATURE_NAMES) & set(STAGE1_FEATURES)
    joined = " ".join(FEATURE_NAMES).lower()
    for forbidden in ("logret", "close", "volume", "rv_", "efficiency", "up_fraction"):
        assert forbidden not in joined, forbidden
    for field in FORBIDDEN_SOURCE_FIELDS:
        assert field not in joined


def test_a_settlement_stamped_exactly_at_the_decision_instant_is_unavailable():
    source = regular_source(10)
    decision = 72 * 3600  # exactly the timestamp of the tenth settlement
    values, reason = build_funding_features(source, decision)
    assert reason is None and values is not None
    # The window is the nine settlements strictly before it: rates 1e-4 … 9e-4.
    assert values[0] == pytest.approx(9e-4)
    assert feature_source_times(source, decision)[-1] == (64 * 3600) * MICROSECONDS

    # One second later the settlement at the boundary becomes available and shifts the window.
    later, later_reason = build_funding_features(source, decision + 1)
    assert later_reason is None and later is not None
    assert later[0] == pytest.approx(10e-4)


def test_the_five_features_reproduce_hand_computed_fixtures():
    source = regular_source(10)
    values, reason = build_funding_features(source, 72 * 3600)
    assert reason is None and values is not None
    named = dict(zip(FEATURE_NAMES, values, strict=True))
    # Window rates are 1e-4 … 9e-4.
    assert named["LATEST_SETTLED_RATE"] == pytest.approx(9e-4)
    assert named["MEAN_LAST_3_SETTLEMENTS"] == pytest.approx(8e-4)
    assert named["MEAN_LAST_9_SETTLEMENTS"] == pytest.approx(5e-4)
    assert named["DELTA_LATEST_PREVIOUS"] == pytest.approx(1e-4)
    # Population variance of 1..9 about 5 is 60/9.
    assert named["STD_LAST_9_SETTLEMENTS"] == pytest.approx(math.sqrt(60 / 9) * 1e-4)


def test_no_settlement_after_the_decision_instant_can_move_a_feature():
    source = regular_source(20)
    decision = 72 * 3600
    baseline, _ = build_funding_features(source, decision)
    mutated = SettledFundingSource(
        times_us=source.times_us,
        rates=tuple(
            rate if time_us < decision * MICROSECONDS else rate * 500.0
            for time_us, rate in zip(source.times_us, source.rates, strict=True)
        ),
    )
    assert build_funding_features(mutated, decision)[0] == baseline


def test_the_causal_surface_is_exactly_the_nine_strictly_prior_settlements():
    source = regular_source(20)
    decision = 72 * 3600
    times = feature_source_times(source, decision)
    assert len(times) == REQUIRED_SETTLEMENTS
    assert max(times) < decision * MICROSECONDS


def test_fewer_than_nine_prior_settlements_abstains_and_is_typed():
    source = regular_source(10)
    # Eight strictly-prior settlements at the ninth settlement's timestamp.
    values, reason = build_funding_features(source, 64 * 3600)
    assert values is None and reason == INSUFFICIENT_PRIOR_SETTLEMENTS
    assert build_funding_features(source, 0)[1] == INSUFFICIENT_PRIOR_SETTLEMENTS
    assert INSUFFICIENT_PRIOR_SETTLEMENTS in UNAVAILABILITY_TAXONOMY


def test_a_disallowed_gap_inside_the_nine_record_chain_abstains_and_is_typed():
    # One missed settlement leaves a sixteen-hour hole inside the window.
    hours = [0, 8, 16, 24, 32, 48, 56, 64, 72, 80]
    rates = [(index + 1) * 1e-4 for index in range(len(hours))]
    source = source_from(hours, rates)
    values, reason = build_funding_features(source, 80 * 3600 + 1)
    assert values is None and reason == SETTLEMENT_GAP_TOO_LARGE
    assert SETTLEMENT_GAP_TOO_LARGE in UNAVAILABILITY_TAXONOMY


def test_the_gap_tolerance_is_exactly_eight_hours_plus_sixty_seconds():
    def source_with_gap(extra_seconds: int) -> SettledFundingSource:
        times = [0]
        for index in range(1, 10):
            step = EIGHT_HOURS + (extra_seconds if index == 5 else 0)
            times.append(times[-1] + step)
        return SettledFundingSource(
            times_us=tuple(value * MICROSECONDS for value in times),
            rates=tuple((index + 1) * 1e-4 for index in range(10)),
        )

    inside = source_with_gap(60)
    decision = inside.times_us[-1] // MICROSECONDS + 1
    assert build_funding_features(inside, decision)[1] is None

    outside = source_with_gap(61)
    decision = outside.times_us[-1] // MICROSECONDS + 1
    assert build_funding_features(outside, decision)[1] == SETTLEMENT_GAP_TOO_LARGE


def test_a_gap_before_the_window_never_invalidates_it():
    """Only gaps *inside* the nine records matter, exactly as the contract states."""
    hours = [0, 200, 208, 216, 224, 232, 240, 248, 256, 264]
    rates = [(index + 1) * 1e-4 for index in range(len(hours))]
    source = source_from(hours, rates)
    values, reason = build_funding_features(source, 264 * 3600 + 1)
    assert reason is None and values is not None


def test_a_non_finite_rate_fails_closed_rather_than_propagating():
    source = SettledFundingSource(
        times_us=tuple(index * 8 * 3600 * MICROSECONDS for index in range(10)),
        rates=(*(1e-4 for _ in range(9)), math.inf),
    )
    values, reason = build_funding_features(source, 80 * 3600)
    assert values is None and reason == NON_FINITE_FUNDING_FEATURE


def test_the_timeline_must_be_strictly_increasing_and_aligned():
    with pytest.raises(FundingFeatureError, match="strictly increasing"):
        SettledFundingSource(times_us=(0, 0), rates=(1e-4, 1e-4))
    with pytest.raises(FundingFeatureError, match="aligned"):
        SettledFundingSource(times_us=(0, 1), rates=(1e-4,))


def test_a_flat_funding_history_is_available_with_zero_dispersion():
    source = SettledFundingSource(
        times_us=tuple(index * 8 * 3600 * MICROSECONDS for index in range(10)),
        rates=tuple(1e-4 for _ in range(10)),
    )
    values, reason = build_funding_features(source, 80 * 3600)
    assert reason is None and values is not None
    named = dict(zip(FEATURE_NAMES, values, strict=True))
    assert named["DELTA_LATEST_PREVIOUS"] == 0.0
    # Float residue, not dispersion: identical inputs leave a sub-1e-18 remainder.
    assert named["STD_LAST_9_SETTLEMENTS"] == pytest.approx(0.0, abs=1e-18)
    assert named["MEAN_LAST_9_SETTLEMENTS"] == pytest.approx(1e-4)
