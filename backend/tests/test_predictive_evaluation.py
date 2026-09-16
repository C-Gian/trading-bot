"""Evaluation-correctness proofs on synthetic fixtures with hand-computable answers.

Every obligation in `tasks/CURRENT_TASK.md` §3 is proven here before the scorer is allowed
near market data, together with the Amendment A1 applicability rules.
"""

from __future__ import annotations

import math

import pytest
from app.predictive import ABSTAIN, DOWN, NEUTRAL, UP
from app.predictive.evaluation import (
    ABSTAINED_MAGNITUDE,
    DIRECTION_NOT_DECLARED,
    MAGNITUDE_EPSILON,
    NEAR_ZERO_BOTH,
    NEUTRAL_REALIZED,
    PROBABILITY_NOT_DECLARED,
    RELIABILITY_BIN_EDGES,
    EvaluationError,
    Outcome,
    Prediction,
    magnitude_match,
    magnitude_match_class,
    moving_block_bootstrap,
    reliability_table,
    score,
    wilson_interval,
)
from app.predictive.labels import HOUR_SECONDS

HOUR = HOUR_SECONDS


def _outcomes(returns) -> list[Outcome]:
    return [
        Outcome(
            open_time=index * HOUR,
            r_24h=value,
            direction=UP if value > 0 else DOWN if value < 0 else NEUTRAL,
        )
        for index, value in enumerate(returns)
    ]


def _persistent_series(runs: int, run_length: int) -> list[bool]:
    """Alternating runs: a deterministic series with strong positive autocorrelation."""
    return [bool((index // run_length) % 2) for index in range(runs * run_length)]


def _directional(directions, probabilities=None) -> list[Prediction]:
    return [
        Prediction(
            open_time=index * HOUR,
            direction=direction,
            probability=None if probabilities is None else probabilities[index],
        )
        for index, direction in enumerate(directions)
    ]


def _score(predictions, outcomes, **declares):
    return score(
        predictions,
        outcomes,
        declares_direction=declares.get("direction", True),
        declares_probability=declares.get("probability", False),
        declares_magnitude=declares.get("magnitude", False),
        replicates=200,
    )


# --- win rate and coverage extremes ---------------------------------------------------


def test_a_perfect_predictor_scores_one_with_full_coverage() -> None:
    outcomes = _outcomes([0.01, -0.02, 0.03, -0.04])
    predictions = _directional([UP, DOWN, UP, DOWN])
    report = _score(predictions, outcomes)
    assert report["win_rate"] == 1.0
    assert report["coverage"] == 1.0
    assert report["actionable_directional_predictions"] == 4
    assert report["correct_directional_predictions"] == 4


def test_an_always_wrong_predictor_scores_zero() -> None:
    outcomes = _outcomes([0.01, -0.02, 0.03, -0.04])
    report = _score(_directional([DOWN, UP, DOWN, UP]), outcomes)
    assert report["win_rate"] == 0.0
    assert report["coverage"] == 1.0


def test_abstaining_everywhere_but_one_correct_call_is_visible_as_tiny_coverage() -> None:
    outcomes = _outcomes([0.01] + [-0.01] * 99)
    predictions = _directional([UP] + [ABSTAIN] * 99)
    report = _score(predictions, outcomes)
    assert report["win_rate"] == 1.0
    assert report["coverage"] == pytest.approx(0.01)
    assert report["actionable_directional_predictions"] == 1
    assert report["abstentions"] == 99
    assert report["eligible_decision_timestamps"] == 100


def test_the_directional_sample_accounting_always_closes() -> None:
    outcomes = _outcomes([0.01, 0.0, -0.02, 0.0, 0.03])
    predictions = _directional([UP, UP, ABSTAIN, ABSTAIN, DOWN])
    report = _score(predictions, outcomes)
    assert report["actionable_directional_predictions"] == 2
    assert report["declared_side_on_neutral_truth"] == 1
    assert report["abstentions"] == 2
    assert report["neutral_truths"] == 2
    total = (
        report["actionable_directional_predictions"]
        + report["declared_side_on_neutral_truth"]
        + report["abstentions"]
    )
    assert total == report["eligible_decision_timestamps"] == 5


def test_a_neutral_truth_is_never_a_win_and_never_silently_dropped() -> None:
    outcomes = _outcomes([0.0, 0.0, 0.01])
    report = _score(_directional([UP, DOWN, UP]), outcomes)
    assert report["win_rate"] == 1.0, "only the one decidable label counts"
    assert report["actionable_directional_predictions"] == 1
    assert report["neutral_truths"] == 2
    assert report["declared_side_on_neutral_truth"] == 2


def test_scoring_a_different_universe_is_refused() -> None:
    outcomes = _outcomes([0.01, -0.01])
    with pytest.raises(EvaluationError, match="not the same set"):
        _score(_directional([UP]), outcomes)


def test_an_unknown_direction_token_is_refused() -> None:
    outcomes = _outcomes([0.01])
    with pytest.raises(EvaluationError, match="unknown declared direction"):
        _score([Prediction(open_time=0, direction="SIDEWAYS")], outcomes)


# --- calibration ----------------------------------------------------------------------


def test_brier_and_reliability_reproduce_hand_computed_values() -> None:
    outcomes = _outcomes([0.01, -0.01, 0.01, -0.01])
    # Declared UP everywhere at p = 0.75; correct on records 0 and 2.
    predictions = _directional([UP] * 4, probabilities=[0.75] * 4)
    report = _score(predictions, outcomes, probability=True)
    assert report["win_rate"] == 0.5
    # ((0.75-1)^2 + (0.75-0)^2 + (0.75-1)^2 + (0.75-0)^2) / 4 = (0.0625+0.5625)*2/4
    assert report["brier_score"] == pytest.approx(0.3125)
    rows = {row["bin"]: row for row in report["reliability_table"]}
    populated = rows["[0.7,0.8)"]
    assert populated["count"] == 4
    assert populated["mean_predicted_probability"] == pytest.approx(0.75)
    assert populated["empirical_frequency_correct"] == pytest.approx(0.5)
    assert sum(row["count"] for row in report["reliability_table"]) == 4


def test_the_reliability_bins_are_the_frozen_ones_and_the_last_is_closed() -> None:
    assert RELIABILITY_BIN_EDGES == (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
    rows = reliability_table([0.0, 0.1, 0.95, 1.0], [True, False, True, True])
    names = [row["bin"] for row in rows]
    assert names[0] == "[0.0,0.1)"
    assert names[-1] == "[0.9,1.0]"
    counts = {row["bin"]: row["count"] for row in rows}
    assert counts["[0.0,0.1)"] == 1
    assert counts["[0.1,0.2)"] == 1
    assert counts["[0.9,1.0]"] == 2, "1.0 belongs to the closed final bin"
    assert sum(counts.values()) == 4


def test_an_empty_bin_is_reported_rather_than_merged_away() -> None:
    rows = reliability_table([0.55], [True])
    empty = [row for row in rows if row["count"] == 0]
    assert len(rows) == 10 and len(empty) == 9
    assert all(row["mean_predicted_probability"] is None for row in empty)


# --- Amendment A1: metric applicability ----------------------------------------------


def test_a_deterministic_baseline_gets_no_brier_and_no_reliability_table() -> None:
    outcomes = _outcomes([0.01, -0.01])
    report = _score(_directional([UP, UP]), outcomes)
    assert report["probability_flag"] == PROBABILITY_NOT_DECLARED
    assert report["brier_score"] is None
    assert report["reliability_table"] is None
    assert report["win_rate"] == 0.5, "it is still scored for direction"


def test_a_probabilistic_predictor_may_not_omit_a_probability() -> None:
    outcomes = _outcomes([0.01, -0.01])
    predictions = _directional([UP, UP], probabilities=[0.6, None])
    with pytest.raises(EvaluationError, match="omitted a probability"):
        _score(predictions, outcomes, probability=True)


def test_a_probability_outside_the_unit_interval_is_refused() -> None:
    outcomes = _outcomes([0.01])
    predictions = _directional([UP], probabilities=[1.5])
    with pytest.raises(EvaluationError, match="outside"):
        _score(predictions, outcomes, probability=True)


def test_a_probability_without_a_direction_has_no_meaning() -> None:
    outcomes = _outcomes([0.01])
    with pytest.raises(EvaluationError, match="no meaning"):
        score(
            _directional([UP], probabilities=[0.6]),
            outcomes,
            declares_direction=False,
            declares_probability=True,
            declares_magnitude=False,
        )


def test_a_magnitude_only_predictor_has_no_win_rate_and_no_coverage() -> None:
    outcomes = _outcomes([0.01, -0.02])
    predictions = [
        Prediction(open_time=0, direction=ABSTAIN, expected_return=0.0),
        Prediction(open_time=HOUR, direction=ABSTAIN, expected_return=0.0),
    ]
    report = _score(predictions, outcomes, direction=False, magnitude=True)
    assert report["direction_flag"] == DIRECTION_NOT_DECLARED
    assert report["win_rate"] is None and report["coverage"] is None
    assert report["magnitude_mae_percentage_points"] == pytest.approx(1.5)


def test_a_directional_predictor_reports_no_magnitude_error() -> None:
    outcomes = _outcomes([0.01])
    report = _score(_directional([UP]), outcomes)
    assert report["magnitude_flag"] == "MAGNITUDE_NOT_DECLARED"
    assert report["magnitude_mae_percentage_points"] is None


# --- magnitude error and the signed magnitude-match diagnostic -------------------------


def test_magnitude_mae_is_reported_in_both_units() -> None:
    outcomes = _outcomes([0.02, -0.02])
    predictions = [
        Prediction(open_time=0, direction=ABSTAIN, expected_return=0.01),
        Prediction(open_time=HOUR, direction=ABSTAIN, expected_return=0.01),
    ]
    report = _score(predictions, outcomes, direction=False, magnitude=True)
    # errors are 0.01 and 0.03 -> mean 0.02
    assert report["magnitude_mae_percentage_points"] == pytest.approx(2.0)
    assert report["magnitude_mae_basis_points"] == pytest.approx(200.0)
    assert report["magnitude_median_absolute_error_percentage_points"] == pytest.approx(2.0)


@pytest.mark.parametrize(
    ("predicted", "actual", "expected"),
    [
        (0.02, 0.02, 100.0),
        (-0.02, -0.02, 100.0),
        (0.002, 0.02, 10.0),
        (0.02, 0.002, 10.0),
        (-0.02, 0.02, -100.0),
        (-0.002, 0.02, -10.0),
        (0.02, -0.002, -10.0),
    ],
)
def test_the_magnitude_match_diagnostic_matches_its_declared_properties(
    predicted: float, actual: float, expected: float
) -> None:
    assert magnitude_match(predicted, actual) == pytest.approx(expected)


def test_the_magnitude_match_diagnostic_is_symmetric_and_bounded() -> None:
    for predicted, actual in ((0.013, 0.047), (-0.004, -0.2), (0.3, -0.05)):
        assert magnitude_match(predicted, actual) == pytest.approx(
            magnitude_match(actual, predicted)
        )
        assert -100.0 <= magnitude_match(predicted, actual) <= 100.0


def test_each_near_zero_class_is_excluded_and_counted() -> None:
    tiny = MAGNITUDE_EPSILON / 10
    assert magnitude_match_class(tiny, tiny) == NEAR_ZERO_BOTH
    assert magnitude_match_class(0.02, 0.0) == NEUTRAL_REALIZED
    assert magnitude_match_class(tiny, 0.02) == ABSTAINED_MAGNITUDE
    assert magnitude_match_class(0.02, 0.02) is None

    outcomes = _outcomes([tiny, 0.0, 0.02, 0.02])
    predictions = [
        Prediction(open_time=0, direction=ABSTAIN, expected_return=tiny),
        Prediction(open_time=HOUR, direction=ABSTAIN, expected_return=0.02),
        Prediction(open_time=2 * HOUR, direction=ABSTAIN, expected_return=tiny),
        Prediction(open_time=3 * HOUR, direction=ABSTAIN, expected_return=0.02),
    ]
    report = _score(predictions, outcomes, direction=False, magnitude=True)
    assert report["magnitude_match_exclusions"] == {
        NEAR_ZERO_BOTH: 1,
        NEUTRAL_REALIZED: 1,
        ABSTAINED_MAGNITUDE: 1,
    }
    assert report["magnitude_match_included"] == 1
    assert report["magnitude_match_mean"] == pytest.approx(100.0)


def test_a_zero_magnitude_predictor_excludes_every_record_by_construction() -> None:
    outcomes = _outcomes([0.01, -0.02, 0.03])
    predictions = [
        Prediction(open_time=index * HOUR, direction=ABSTAIN, expected_return=0.0)
        for index in range(3)
    ]
    report = _score(predictions, outcomes, direction=False, magnitude=True)
    assert report["magnitude_match_included"] == 0
    assert report["magnitude_match_mean"] is None
    assert report["magnitude_match_exclusions"][ABSTAINED_MAGNITUDE] == 3
    assert sum(report["magnitude_match_exclusions"].values()) == 3


# --- uncertainty ------------------------------------------------------------------------


def test_the_moving_block_interval_is_wider_than_naive_wilson_on_overlapping_labels() -> None:
    """Overlapping labels are not independent; the naive interval is optimistic.

    Runs of 100 are longer than the 48-hour block, so most blocks fall inside a single run
    and the resampled win rate varies far more than a binomial of the same size would.
    """
    correct = _persistent_series(runs=20, run_length=100)
    assert sum(correct) * 2 == len(correct)
    block = moving_block_bootstrap(correct, block_length=48, replicates=2000, seed=11)
    naive = wilson_interval(sum(correct), len(correct))
    assert block[1] - block[0] > naive[1] - naive[0]


def test_the_naive_interval_understates_dependence_by_a_wide_margin() -> None:
    correct = _persistent_series(runs=20, run_length=100)
    block = moving_block_bootstrap(correct, block_length=48, replicates=2000, seed=11)
    naive = wilson_interval(sum(correct), len(correct))
    assert (block[1] - block[0]) > 3 * (naive[1] - naive[0])


def test_the_bootstrap_is_deterministic_under_the_frozen_seed() -> None:
    correct = _persistent_series(runs=10, run_length=100)
    first = moving_block_bootstrap(correct, replicates=500, seed=7)
    second = moving_block_bootstrap(correct, replicates=500, seed=7)
    assert first == second
    assert moving_block_bootstrap(correct, replicates=500, seed=8) != first


def test_the_bootstrap_brackets_a_degenerate_series_exactly() -> None:
    assert moving_block_bootstrap([True] * 200, replicates=200, seed=3) == [1.0, 1.0]
    assert moving_block_bootstrap([False] * 200, replicates=200, seed=3) == [0.0, 0.0]


def test_the_wilson_reference_is_only_available_at_the_frozen_alpha() -> None:
    assert wilson_interval(50, 100)[0] < 0.5 < wilson_interval(50, 100)[1]
    with pytest.raises(EvaluationError, match="alpha 0.05"):
        wilson_interval(50, 100, alpha=0.1)


def test_a_report_carries_both_intervals_and_names_the_primary_method() -> None:
    outcomes = _outcomes([0.01, -0.01, 0.01, -0.01])
    report = _score(_directional([UP, DOWN, UP, UP]), outcomes)
    assert report["win_rate_interval_method"] == "MOVING_BLOCK_BOOTSTRAP"
    assert report["win_rate_interval_block_length_hours"] == 48
    assert len(report["win_rate_interval_moving_block"]) == 2
    assert len(report["win_rate_interval_naive_wilson_optimistic_reference"]) == 2


def test_win_rate_matches_a_hand_computed_fraction() -> None:
    outcomes = _outcomes([math.log(1.01), math.log(0.99), math.log(1.02)])
    report = _score(_directional([UP, UP, UP]), outcomes)
    assert report["win_rate"] == pytest.approx(2 / 3)
