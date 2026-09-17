"""Point-in-time, staleness and causality proofs for the Stage-2 open-interest source.

Every claim here is hand-computable on a deterministic synthetic 5-minute timeline. Nothing
in this file reads the canonical artifact or any market label.
"""

from __future__ import annotations

import math

import pytest
from app.predictive.open_interest_source import (
    CADENCE_SECONDS,
    FEATURE_COUNT,
    FEATURE_NAMES,
    FORBIDDEN_COLUMNS,
    HOUR_SECONDS,
    LOOKBACK_HOURS,
    MAXIMUM_STATE_AGE_SECONDS,
    NO_PRIOR_OPEN_INTEREST_RECORD,
    NON_POSITIVE_OPEN_INTEREST,
    OPEN_INTEREST_STATE_TOO_STALE,
    RECORDS_PER_DAY,
    REQUIRED_STATES,
    UNAVAILABILITY_TAXONOMY,
    OpenInterestError,
    OpenInterestSource,
    build_open_interest_features,
    feature_source_times,
    hourly_state,
    parse_metrics_csv,
    state_window,
)

DECISION = 200 * HOUR_SECONDS


def grid_source(
    quantity: float = 1000.0, start: int = 0, end: int = 210 * HOUR_SECONDS
) -> OpenInterestSource:
    """A complete 5-minute grid carrying a constant quantity."""
    times = tuple(range(start, end + CADENCE_SECONDS, CADENCE_SECONDS))
    return OpenInterestSource(times=times, quantities=tuple(quantity for _ in times))


def geometric_source(ratio: float = 1.01) -> OpenInterestSource:
    """A complete grid whose quantity grows by a fixed ratio every hour."""
    times = tuple(range(0, 210 * HOUR_SECONDS + CADENCE_SECONDS, CADENCE_SECONDS))
    quantities = tuple(1000.0 * ratio ** (moment / HOUR_SECONDS) for moment in times)
    return OpenInterestSource(times=times, quantities=quantities)


def test_the_frozen_feature_set_is_exactly_six_ordered_names():
    assert FEATURE_COUNT == 6
    assert FEATURE_NAMES == (
        "OI_LOG_CHANGE_1H",
        "OI_LOG_CHANGE_4H",
        "OI_LOG_CHANGE_24H",
        "OI_LOG_LEVEL_Z24",
        "OI_LOG_DIFF_VOL24",
        "OI_LOG_TREND24",
    )
    assert LOOKBACK_HOURS == 24
    assert REQUIRED_STATES == 25
    assert CADENCE_SECONDS == 300
    assert RECORDS_PER_DAY == 288
    assert MAXIMUM_STATE_AGE_SECONDS == 600


def test_the_family_admits_no_price_bearing_or_ratio_field():
    assert "sum_open_interest_value" in FORBIDDEN_COLUMNS
    for name in (
        "count_toptrader_long_short_ratio",
        "sum_toptrader_long_short_ratio",
        "count_long_short_ratio",
        "sum_taker_long_short_vol_ratio",
    ):
        assert name in FORBIDDEN_COLUMNS
    joined = " ".join(FEATURE_NAMES).lower()
    for forbidden in ("price", "value", "notional", "ratio", "funding", "basis"):
        assert forbidden not in joined, forbidden


def test_the_feature_set_shares_nothing_with_the_rejected_families():
    from app.predictive.funding_source import FEATURE_NAMES as FUNDING_FEATURES
    from app.predictive.internal_features import FEATURE_NAMES as STAGE1_FEATURES

    assert not set(FEATURE_NAMES) & set(STAGE1_FEATURES)
    assert not set(FEATURE_NAMES) & set(FUNDING_FEATURES)


def test_a_record_stamped_exactly_at_the_decision_instant_is_unavailable():
    times = (DECISION - CADENCE_SECONDS, DECISION)
    source = OpenInterestSource(times=times, quantities=(900.0, 5000.0))
    value, reason = hourly_state(source, DECISION)
    assert reason is None
    # The record at exactly T is skipped; the state is the one strictly before it.
    assert value == 900.0
    assert feature_source_times(source, DECISION) == ()
    # One second later the boundary record becomes the state.
    assert hourly_state(source, DECISION + 1)[0] == 5000.0


def test_a_state_older_than_ten_minutes_is_unavailable():
    fresh = OpenInterestSource(times=(DECISION - MAXIMUM_STATE_AGE_SECONDS,), quantities=(1000.0,))
    assert hourly_state(fresh, DECISION) == (1000.0, None)
    stale = OpenInterestSource(
        times=(DECISION - MAXIMUM_STATE_AGE_SECONDS - 1,), quantities=(1000.0,)
    )
    assert hourly_state(stale, DECISION) == (None, OPEN_INTEREST_STATE_TOO_STALE)
    assert OPEN_INTEREST_STATE_TOO_STALE in UNAVAILABILITY_TAXONOMY


def test_no_record_at_or_after_the_decision_instant_can_move_a_feature():
    source = geometric_source()
    baseline, reason = build_open_interest_features(source, DECISION)
    assert reason is None and baseline is not None
    mutated = OpenInterestSource(
        times=source.times,
        quantities=tuple(
            quantity if moment < DECISION else quantity * 50.0
            for moment, quantity in zip(source.times, source.quantities, strict=True)
        ),
    )
    assert build_open_interest_features(mutated, DECISION)[0] == baseline


def test_every_feature_reads_only_states_inside_the_twenty_four_hour_window():
    source = geometric_source()
    stamps = feature_source_times(source, DECISION)
    assert len(stamps) == REQUIRED_STATES
    assert max(stamps) < DECISION
    assert min(stamps) >= DECISION - LOOKBACK_HOURS * HOUR_SECONDS - MAXIMUM_STATE_AGE_SECONDS
    # A record older than the window cannot move anything.
    baseline, _ = build_open_interest_features(source, DECISION)
    older = DECISION - (LOOKBACK_HOURS + 1) * HOUR_SECONDS
    mutated = OpenInterestSource(
        times=source.times,
        quantities=tuple(
            quantity * 50.0 if moment <= older else quantity
            for moment, quantity in zip(source.times, source.quantities, strict=True)
        ),
    )
    assert build_open_interest_features(mutated, DECISION)[0] == baseline


def test_the_six_features_reproduce_hand_computed_fixtures():
    ratio = 1.01
    source = geometric_source(ratio)
    values, reason = build_open_interest_features(source, DECISION)
    assert reason is None and values is not None
    named = dict(zip(FEATURE_NAMES, values, strict=True))
    # The as-of state at each hour is stamped five minutes earlier, so every hourly log
    # difference is exactly one hour of growth.
    step = math.log(ratio)
    assert named["OI_LOG_CHANGE_1H"] == pytest.approx(step)
    assert named["OI_LOG_CHANGE_4H"] == pytest.approx(4 * step)
    assert named["OI_LOG_CHANGE_24H"] == pytest.approx(24 * step)
    # log(O) is an exact arithmetic progression over the 25 states.
    assert named["OI_LOG_DIFF_VOL24"] == pytest.approx(0.0, abs=1e-12)
    assert named["OI_LOG_TREND24"] == pytest.approx(step)
    # The z-score of the last point of an evenly spaced run of 25.
    spread = math.sqrt(sum((index - 12) ** 2 for index in range(25)) / 25)
    assert named["OI_LOG_LEVEL_Z24"] == pytest.approx(12 / spread)


def test_a_flat_series_gives_zero_change_and_the_declared_zero_dispersion_value():
    values, reason = build_open_interest_features(grid_source(), DECISION)
    assert reason is None and values is not None
    named = dict(zip(FEATURE_NAMES, values, strict=True))
    assert named["OI_LOG_CHANGE_1H"] == 0.0
    assert named["OI_LOG_CHANGE_4H"] == 0.0
    assert named["OI_LOG_CHANGE_24H"] == 0.0
    # A zero population standard deviation emits the declared 0.0 rather than dividing.
    assert named["OI_LOG_LEVEL_Z24"] == 0.0
    assert named["OI_LOG_DIFF_VOL24"] == 0.0
    assert named["OI_LOG_TREND24"] == 0.0


def test_a_missing_hour_inside_the_window_abstains_and_is_typed():
    source = grid_source()
    hole = DECISION - 5 * HOUR_SECONDS
    kept = [
        (moment, quantity)
        for moment, quantity in zip(source.times, source.quantities, strict=True)
        if not hole - 3 * CADENCE_SECONDS < moment <= hole
    ]
    punctured = OpenInterestSource(
        times=tuple(moment for moment, _ in kept),
        quantities=tuple(quantity for _, quantity in kept),
    )
    values, reason = build_open_interest_features(punctured, DECISION)
    assert values is None and reason == OPEN_INTEREST_STATE_TOO_STALE


def test_a_non_positive_state_abstains_rather_than_taking_a_logarithm():
    source = grid_source()
    target = DECISION - 3 * HOUR_SECONDS - CADENCE_SECONDS
    punctured = OpenInterestSource(
        times=source.times,
        quantities=tuple(
            0.0 if moment == target else quantity
            for moment, quantity in zip(source.times, source.quantities, strict=True)
        ),
    )
    values, reason = build_open_interest_features(punctured, DECISION)
    assert values is None and reason == NON_POSITIVE_OPEN_INTEREST
    assert NON_POSITIVE_OPEN_INTEREST in UNAVAILABILITY_TAXONOMY


def test_an_instant_before_the_source_begins_abstains_and_is_typed():
    source = grid_source(start=100 * HOUR_SECONDS)
    values, reason = build_open_interest_features(source, 50 * HOUR_SECONDS)
    assert values is None and reason == NO_PRIOR_OPEN_INTEREST_RECORD
    assert NO_PRIOR_OPEN_INTEREST_RECORD in UNAVAILABILITY_TAXONOMY
    # The very first usable decision instant needs a full 24h of prior states.
    window, window_reason = state_window(source, 101 * HOUR_SECONDS + LOOKBACK_HOURS * HOUR_SECONDS)
    assert window_reason is None and window is not None and len(window) == REQUIRED_STATES


def test_availability_never_depends_on_a_future_return():
    """Source validity is a property of the source timeline alone."""
    source = grid_source()
    first = build_open_interest_features(source, DECISION)
    second = build_open_interest_features(source, DECISION)
    assert first == second
    # Nothing in the signature or the call path can see a label.
    import inspect

    signature = inspect.signature(build_open_interest_features)
    assert list(signature.parameters) == ["source", "instant"]


def test_the_timeline_must_be_strictly_increasing_and_aligned():
    with pytest.raises(OpenInterestError, match="strictly increasing"):
        OpenInterestSource(times=(0, 0), quantities=(1.0, 1.0))
    with pytest.raises(OpenInterestError, match="aligned"):
        OpenInterestSource(times=(0, 300), quantities=(1.0,))


def test_the_official_schema_is_enforced_when_parsing():
    header = (
        "create_time,symbol,sum_open_interest,sum_open_interest_value,"
        "count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,"
        "count_long_short_ratio,sum_taker_long_short_vol_ratio"
    )
    body = "2021-06-15 00:00:00,BTCUSDT,49644.99300000,2010191510.02,1.1,1.1,1.09,0.71"
    rows = parse_metrics_csv(f"{header}\n{body}\n")
    assert rows == [(1623715200, 49644.993)]

    with pytest.raises(OpenInterestError, match="schema drifted"):
        parse_metrics_csv("create_time,symbol,sum_open_interest\n2021-06-15 00:00:00,BTCUSDT,1\n")
    with pytest.raises(OpenInterestError, match="not BTCUSDT"):
        parse_metrics_csv(f"{header}\n{body.replace('BTCUSDT', 'ETHUSDT')}\n")


def test_the_parser_admits_only_the_timestamp_and_the_quantity():
    header = (
        "create_time,symbol,sum_open_interest,sum_open_interest_value,"
        "count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,"
        "count_long_short_ratio,sum_taker_long_short_vol_ratio"
    )
    body = "2021-06-15 00:00:00,BTCUSDT,49644.99300000,2010191510.02,1.1,1.1,1.09,0.71"
    rows = parse_metrics_csv(f"{header}\n{body}\n")
    assert len(rows[0]) == 2
    # The notional column is never carried through, so it cannot embed BTC price.
    assert 2010191510.02 not in rows[0]
