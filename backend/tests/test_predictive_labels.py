"""Causality proofs for the 24h label substrate.

Every obligation in `tasks/CURRENT_TASK.md` §2 is proven here on synthetic bars with known
answers, not asserted in prose.
"""

from __future__ import annotations

import math

import pytest
from app.predictive import DOWN, HORIZON_HOURS, NEUTRAL, UP
from app.predictive.labels import (
    DECISION_BAR_INCOMPLETE,
    DECISION_BAR_MISSING,
    EXCLUSION_TAXONOMY,
    HORIZON_BAR_BEYOND_COVERAGE,
    HORIZON_BAR_INCOMPLETE,
    HORIZON_BAR_MISSING,
    HOUR_SECONDS,
    NON_POSITIVE_PRICE,
    Bar,
    LabelError,
    assert_causal,
    build_labels,
    direction_of,
    index_bars,
    trailing_return,
)

HOURS = HORIZON_HOURS


def _bars(closes, start: int = 0, complete=None) -> list[Bar]:
    return [
        Bar(
            open_time=start + index * HOUR_SECONDS,
            close=float(close),
            complete=True if complete is None else complete[index],
        )
        for index, close in enumerate(closes)
    ]


def _flat(count: int, price: float = 100.0, start: int = 0) -> list[Bar]:
    return _bars([price] * count, start=start)


# --- the label reads exactly two bars, and they are the right two -------------------


def test_the_label_is_exactly_the_terminal_24h_log_return() -> None:
    closes = [100.0] * (HOURS + 1)
    closes[HOURS] = 110.0
    label_set = build_labels(_bars(closes))
    assert label_set.admissible == 1
    label = label_set.labels[0]
    assert label.open_time == 0
    assert label.decision_close == 100.0
    assert label.horizon_close == 110.0
    assert label.r_24h == pytest.approx(math.log(1.1))
    assert label.direction == UP


def test_no_bar_between_the_decision_and_the_horizon_can_change_the_label() -> None:
    """Only close[T] and close[T+24h] may enter; the intra-horizon path may not."""
    closes = [100.0] * (HOURS + 1)
    closes[HOURS] = 105.0
    baseline = build_labels(_bars(closes)).labels[0]
    perturbed_closes = list(closes)
    for index in range(1, HOURS):
        perturbed_closes[index] = 1_000_000.0 if index % 2 else 0.01
    perturbed = build_labels(_bars(perturbed_closes)).labels[0]
    assert perturbed.r_24h == baseline.r_24h
    assert perturbed.direction == baseline.direction


def test_a_bar_before_the_decision_cannot_change_the_label() -> None:
    closes = [50.0, 60.0, 70.0] + [100.0] * HOURS + [120.0]
    label_set = build_labels(_bars(closes))
    target = next(label for label in label_set.labels if label.open_time == 3 * HOUR_SECONDS)
    assert target.decision_close == 100.0
    assert target.r_24h == pytest.approx(math.log(1.2))


# --- shifting the series -------------------------------------------------------------


def test_shifting_the_series_forward_shifts_every_label_by_the_same_amount() -> None:
    closes = [100.0] * HOURS + [130.0]
    original = build_labels(_bars(closes, start=0))
    shifted = build_labels(_bars(closes, start=7 * HOUR_SECONDS))
    assert [label.open_time for label in original.labels] == [0]
    assert [label.open_time for label in shifted.labels] == [7 * HOUR_SECONDS]
    assert original.labels[0].r_24h == shifted.labels[0].r_24h


def test_shifting_the_price_series_backward_against_time_is_detected() -> None:
    """A one-hour backward shift of prices must change the labels, not silently agree."""
    closes = [100.0 + index for index in range(HOURS + 4)]
    honest = build_labels(_bars(closes))
    leaked = build_labels(_bars(closes[1:]))
    assert [label.r_24h for label in honest.labels] != [label.r_24h for label in leaked.labels]


def test_unordered_or_unaligned_bars_are_rejected() -> None:
    bars = _flat(3)
    with pytest.raises(LabelError, match="strictly increasing"):
        build_labels([bars[1], bars[0], bars[2]])
    with pytest.raises(LabelError, match="hour boundary"):
        build_labels([Bar(open_time=90, close=1.0, complete=True)])


# --- the explicit look-ahead guard ---------------------------------------------------


def test_a_feature_reading_a_future_bar_is_caught_by_the_look_ahead_guard() -> None:
    bars = _flat(HOURS + 1)
    instant = 0
    assert_causal(bars, instant, [instant, instant - HOUR_SECONDS])
    with pytest.raises(LabelError, match="look-ahead"):
        assert_causal(bars, instant, [instant + HOUR_SECONDS])
    with pytest.raises(LabelError, match="look-ahead"):
        assert_causal(bars, instant, [instant + HOURS * HOUR_SECONDS])


def test_the_trailing_feature_never_reads_past_the_decision_instant() -> None:
    closes = [100.0] * (HOURS + 1)
    closes[HOURS] = 200.0
    index = index_bars(_bars(closes))
    instant = HOURS * HOUR_SECONDS
    assert trailing_return(index, instant) == pytest.approx(math.log(2.0))
    # At the first instant the trailing window predates coverage, so it is unobservable.
    assert trailing_return(index, 0) is None


# --- coverage boundary ---------------------------------------------------------------


def test_the_last_admissible_decision_is_exactly_one_horizon_before_coverage_ends() -> None:
    bars = _flat(HOURS + 5)
    label_set = build_labels(bars)
    last_open = bars[-1].open_time
    assert label_set.labels[-1].open_time == last_open - HOURS * HOUR_SECONDS
    assert label_set.exclusions[HORIZON_BAR_BEYOND_COVERAGE] == HOURS


def test_instants_past_the_horizon_boundary_are_excluded_and_counted() -> None:
    label_set = build_labels(_flat(HOURS + 1))
    accounting = label_set.accounting()
    assert accounting["admissible_labels"] == 1
    assert accounting["exclusions"][HORIZON_BAR_BEYOND_COVERAGE] == HOURS
    assert (
        accounting["excluded_total"] + accounting["admissible_labels"]
        == (accounting["grid_decision_instants"])
    )


# --- gaps are never interpolated -----------------------------------------------------


def test_a_canonical_gap_produces_inadmissible_labels_not_interpolated_ones() -> None:
    bars = _flat(2 * HOURS + 2)
    removed = bars.pop(HOURS)  # the horizon bar of the very first decision
    label_set = build_labels(bars)
    labelled = {label.open_time for label in label_set.labels}
    assert removed.open_time not in labelled, "the missing bar must not be labelled"
    assert 0 not in labelled, "no nearest-bar substitution may rescue the first decision"
    assert label_set.exclusions[HORIZON_BAR_MISSING] == 1
    assert label_set.exclusions[DECISION_BAR_MISSING] == 1


def test_an_incomplete_bar_is_excluded_on_either_side_and_typed() -> None:
    size = HOURS + 2
    flags = [True] * size
    flags[0] = False
    decision_incomplete = build_labels(_bars([100.0] * size, complete=flags))
    assert decision_incomplete.exclusions[DECISION_BAR_INCOMPLETE] == 1
    flags = [True] * size
    flags[HOURS] = False
    horizon_incomplete = build_labels(_bars([100.0] * size, complete=flags))
    assert horizon_incomplete.exclusions[HORIZON_BAR_INCOMPLETE] == 1


def test_a_non_positive_close_is_excluded_and_typed() -> None:
    closes = [100.0] * (HOURS + 1)
    closes[HOURS] = 0.0
    label_set = build_labels(_bars(closes))
    assert label_set.exclusions[NON_POSITIVE_PRICE] == 1
    assert label_set.admissible == 0


def test_every_exclusion_reason_is_in_the_frozen_taxonomy_and_counted() -> None:
    label_set = build_labels(_flat(HOURS + 3))
    accounting = label_set.accounting()
    assert set(accounting["exclusions"]) == set(EXCLUSION_TAXONOMY)
    assert sum(accounting["exclusions"].values()) == accounting["excluded_total"]


# --- NEUTRAL truth -------------------------------------------------------------------


def test_direction_truth_is_exact_and_zero_is_neutral() -> None:
    assert direction_of(1e-18) == UP
    assert direction_of(-1e-18) == DOWN
    assert direction_of(0.0) == NEUTRAL


def test_a_flat_horizon_is_neutral_and_is_counted_not_dropped() -> None:
    label_set = build_labels(_flat(HOURS + 1))
    assert label_set.admissible == 1
    assert label_set.labels[0].direction == NEUTRAL
    counts = label_set.direction_counts()
    assert counts == {UP: 0, DOWN: 0, NEUTRAL: 1}
    assert sum(counts.values()) == label_set.admissible
