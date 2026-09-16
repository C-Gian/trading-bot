"""Proofs for the reserved HGBR dual-head configuration.

Synthetic data only. The claims checked here are the ones the task requires of the new
heads — determinism under the fixed random_state, the same training-only calibration
separation proven for the linear head, and the same fail-closed behaviour when a split side
lacks both directional classes — plus the structural claim that the executed specification
is the one frozen in the search plan rather than a new choice.
"""

from __future__ import annotations

import pytest
from app.predictive import DOWN, UP
from app.predictive.internal_features import FEATURE_COUNT
from app.predictive.internal_model import (
    CALIBRATION_EMBARGO_HOURS,
    RESERVED_HGBR_PARAMETERS,
    ModelError,
    calibration_split,
    declared_direction,
    declared_probability,
    reserved_hgbr_specification,
)
from app.predictive.internal_nonlinear_model import (
    MAGNITUDE_LOSS,
    MODEL_VERSION,
    fit_direction_head,
    fit_magnitude_head,
    nonlinear_specification,
)
from app.predictive.labels import HOUR_SECONDS


def synthetic_rows(count: int, seed: int = 7):
    """A deterministic training set with a nonlinear, non-separable directional signal."""
    import numpy as np

    generator = np.random.default_rng(seed)
    matrix = generator.normal(size=(count, FEATURE_COUNT))
    # An interaction a linear head cannot represent, so the tree head has something to find.
    signal = matrix[:, 0] * matrix[:, 1] + 0.5 * np.abs(matrix[:, 2])
    noisy = signal + 1.2 * generator.normal(size=count)
    open_times = [index * HOUR_SECONDS for index in range(count)]
    directions = [UP if value > 0 else DOWN for value in noisy]
    returns = [float(0.03 * value) for value in signal]
    return open_times, [tuple(float(x) for x in row) for row in matrix], directions, returns


def test_the_executed_specification_is_the_one_frozen_in_the_search_plan():
    reserved = reserved_hgbr_specification()
    executed = nonlinear_specification()
    assert executed["model_version"] == reserved["model_version"] == MODEL_VERSION
    assert executed["direction_base_estimator"] == reserved["direction_estimator"]
    assert executed["magnitude_estimator"] == reserved["magnitude_estimator"]
    assert executed["magnitude_loss"] == reserved["magnitude_loss"] == MAGNITUDE_LOSS
    assert executed["direction_base_parameters"] == RESERVED_HGBR_PARAMETERS
    assert executed["magnitude_parameters"] == RESERVED_HGBR_PARAMETERS
    assert executed["hyperparameter_search"] is False
    assert executed["probability_threshold_searched"] is False
    assert RESERVED_HGBR_PARAMETERS["random_state"] == 20260916
    assert RESERVED_HGBR_PARAMETERS["early_stopping"] is False


def test_the_calibration_split_is_the_linear_one_unchanged():
    open_times = [index * HOUR_SECONDS for index in range(100)]
    split = calibration_split(open_times)
    assert split.boundary_index == 80
    assert split.base_fit_rows == 33
    assert split.calibration_rows == 20
    assert split.dropped_to_embargo == 47
    executed = nonlinear_specification()
    assert executed["calibration_split_fraction"] == 0.80
    assert executed["calibration_embargo_hours"] == CALIBRATION_EMBARGO_HOURS == 48
    assert executed["calibration_input"] == "BASE_MODEL_RAW_DECISION_FUNCTION_SCORE"


def test_the_direction_head_fails_closed_when_a_side_lacks_both_classes():
    open_times, matrix, directions, _ = synthetic_rows(300)
    one_sided = list(directions)
    boundary = calibration_split(open_times).boundary_index
    for index in range(boundary, len(one_sided)):
        one_sided[index] = UP
    with pytest.raises(ModelError, match="both directional classes"):
        fit_direction_head(open_times, matrix, one_sided)


def test_the_direction_head_rejects_a_non_directional_training_label():
    open_times, matrix, directions, _ = synthetic_rows(300)
    broken = list(directions)
    broken[0] = "NEUTRAL"
    with pytest.raises(ModelError, match="non-directional"):
        fit_direction_head(open_times, matrix, broken)


def test_the_fit_is_deterministic_under_the_fixed_random_state():
    open_times, matrix, directions, returns = synthetic_rows(600)
    probe = [tuple(0.1 * index for index in range(FEATURE_COUNT))]
    first = fit_direction_head(open_times, matrix, directions)
    second = fit_direction_head(open_times, matrix, directions)
    assert first.probability_up(probe) == second.probability_up(probe)
    assert fit_magnitude_head(matrix, returns).expected_return(probe) == (
        fit_magnitude_head(matrix, returns).expected_return(probe)
    )


def test_only_base_fit_rows_can_move_the_boosted_base_model():
    """Perturbing rows on the calibration side must not refit the base model."""
    open_times, matrix, directions, _ = synthetic_rows(600)
    split = calibration_split(open_times)
    boundary = split.boundary_open_time
    embargo = CALIBRATION_EMBARGO_HOURS * HOUR_SECONDS
    head = fit_direction_head(open_times, matrix, directions)
    probe = [tuple(0.1 * index for index in range(FEATURE_COUNT))]
    baseline = head.base.decision_function(head.scaler.transform(probe))[0]

    perturbed = [
        tuple(value + 25.0 for value in row) if moment + embargo > boundary else row
        for moment, row in zip(open_times, matrix, strict=True)
    ]
    moved = fit_direction_head(open_times, perturbed, directions)
    assert moved.base.decision_function(moved.scaler.transform(probe))[0] == baseline
    assert head.split == moved.split
    # The calibration map, by contrast, is allowed to see exactly those rows.
    assert list(head.platt.coef_[0]) != list(moved.platt.coef_[0])


def test_embargoed_rows_reach_neither_side_of_the_direction_head():
    open_times, matrix, directions, _ = synthetic_rows(600)
    split = calibration_split(open_times)
    boundary = split.boundary_open_time
    embargo = CALIBRATION_EMBARGO_HOURS * HOUR_SECONDS
    head = fit_direction_head(open_times, matrix, directions)
    probe = [tuple(0.1 * index for index in range(FEATURE_COUNT))]
    perturbed = [
        tuple(value + 25.0 for value in row) if moment + embargo > boundary > moment else row
        for moment, row in zip(open_times, matrix, strict=True)
    ]
    moved = fit_direction_head(open_times, perturbed, directions)
    assert (
        moved.base.decision_function(moved.scaler.transform(probe))[0]
        == (head.base.decision_function(head.scaler.transform(probe))[0])
    )
    assert list(head.platt.coef_[0]) == list(moved.platt.coef_[0])
    assert split.dropped_to_embargo > 0


def test_the_calibrated_probability_tracks_the_signal_and_stays_inside_the_unit_interval():
    open_times, matrix, directions, _ = synthetic_rows(1200)
    head = fit_direction_head(open_times, matrix, directions)
    probabilities = head.probability_up(matrix[:200])
    assert all(0.0 <= value <= 1.0 for value in probabilities)
    assert min(probabilities) < 0.5 < max(probabilities)
    for value in probabilities:
        assert declared_probability(value) >= 0.5
        assert declared_direction(value) in {UP, DOWN}


def test_the_magnitude_head_recovers_the_interaction_a_linear_head_cannot():
    from app.predictive.internal_model import fit_magnitude_head as fit_linear_magnitude

    _, matrix, _, returns = synthetic_rows(1500)
    boosted = fit_magnitude_head(matrix, returns)
    linear = fit_linear_magnitude(matrix, returns)
    predicted_boosted = boosted.expected_return(matrix)
    predicted_linear = linear.expected_return(matrix)
    error_boosted = sum(abs(p - a) for p, a in zip(predicted_boosted, returns, strict=True)) / len(
        returns
    )
    error_linear = sum(abs(p - a) for p, a in zip(predicted_linear, returns, strict=True)) / len(
        returns
    )
    # In-sample on a deliberately nonlinear target: the tree head must fit it better, or the
    # reserved configuration would have no mechanism to test.
    assert error_boosted < error_linear
    assert boosted.training_rows == 1500


def test_strength_is_an_inclusive_training_only_percentile_rank():
    matrix = [tuple(float(index % 3) for _ in range(FEATURE_COUNT)) for index in range(4)]
    head = fit_magnitude_head(matrix, [0.01, -0.02, 0.03, -0.04])
    assert head.strength([0.0])[0] == 0.0
    assert head.strength([0.01])[0] == 25.0
    assert head.strength([-0.03])[0] == 75.0
    assert head.strength([1.0])[0] == 100.0
    assert head.strength([0.02])[0] == head.strength([-0.02])[0] == 50.0


def test_the_heads_reject_the_wrong_feature_width():
    open_times, matrix, directions, returns = synthetic_rows(300)
    head = fit_direction_head(open_times, matrix, directions)
    magnitude = fit_magnitude_head(matrix, returns)
    with pytest.raises(ModelError, match="feature width"):
        head.probability_up([(0.0, 0.0)])
    with pytest.raises(ModelError, match="feature width"):
        magnitude.expected_return([(0.0, 0.0)])
