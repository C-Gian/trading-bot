"""Proofs for the frozen dual-head fitting and calibration procedure.

Synthetic data only. Every structural claim — where the calibration boundary falls, that the
embargo really drops rows, that a one-class side fails closed, that outer-evaluation rows
cannot move a coefficient, that strength is an inclusive training-only percentile — is
checked directly rather than assumed from the parameter dictionary.
"""

from __future__ import annotations

import math

import pytest
from app.predictive import DOWN, UP
from app.predictive.internal_features import FEATURE_COUNT
from app.predictive.internal_model import (
    CALIBRATION_EMBARGO_HOURS,
    CALIBRATION_SPLIT_FRACTION,
    DIRECTION_BASE_PARAMETERS,
    HGBR_MODEL_VERSION,
    LINEAR_MODEL_VERSION,
    MAGNITUDE_PARAMETERS,
    PLATT_PARAMETERS,
    RESERVED_HGBR_PARAMETERS,
    ModelError,
    calibration_split,
    declared_direction,
    declared_probability,
    fit_direction_head,
    fit_magnitude_head,
    linear_specification,
    reserved_hgbr_specification,
)
from app.predictive.labels import HOUR_SECONDS


def synthetic_rows(count: int, seed: int = 7):
    """A deterministic training set whose first feature carries most of the direction."""
    import numpy as np

    generator = np.random.default_rng(seed)
    matrix = generator.normal(size=(count, FEATURE_COUNT))
    signal = matrix[:, 0] + 0.25 * matrix[:, 1]
    # Deliberately not separable: a separable toy would saturate every calibrated
    # probability at 0 or 1 and prove nothing about the calibration map.
    noisy = signal + 1.5 * generator.normal(size=count)
    open_times = [index * HOUR_SECONDS for index in range(count)]
    directions = [UP if value > 0 else DOWN for value in noisy]
    returns = [float(0.03 * value) for value in signal]
    return open_times, [tuple(float(x) for x in row) for row in matrix], directions, returns


def test_the_frozen_parameters_are_exactly_what_the_design_declares():
    assert DIRECTION_BASE_PARAMETERS == {
        "penalty": "l2",
        "C": 1.0,
        "solver": "lbfgs",
        "fit_intercept": True,
        "max_iter": 2000,
        "tol": 1e-8,
        "class_weight": None,
    }
    assert PLATT_PARAMETERS == {
        "penalty": None,
        "solver": "lbfgs",
        "fit_intercept": True,
        "max_iter": 2000,
        "tol": 1e-8,
    }
    assert MAGNITUDE_PARAMETERS == {"alpha": 1.0, "fit_intercept": True}
    assert CALIBRATION_SPLIT_FRACTION == 0.80
    assert CALIBRATION_EMBARGO_HOURS == 48


def test_the_reserved_configuration_is_frozen_and_not_executed_here():
    reserved = reserved_hgbr_specification()
    assert reserved["model_version"] == HGBR_MODEL_VERSION
    assert reserved["executed_in_this_checkpoint"] is False
    assert reserved["hyperparameter_search"] is False
    assert RESERVED_HGBR_PARAMETERS == {
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 15,
        "min_samples_leaf": 50,
        "l2_regularization": 1.0,
        "max_bins": 255,
        "early_stopping": False,
        "random_state": 20260916,
    }
    assert linear_specification()["model_version"] == LINEAR_MODEL_VERSION
    assert linear_specification()["hyperparameter_search"] is False


def test_the_calibration_boundary_and_embargo_are_hand_computable():
    open_times = [index * HOUR_SECONDS for index in range(100)]
    split = calibration_split(open_times)
    # floor(0.80 * 100) = 80, so the boundary is the timestamp at index 80.
    assert split.boundary_index == 80
    assert split.boundary_open_time == 80 * HOUR_SECONDS
    # Base-fit rows satisfy T + 48h <= S, i.e. indices 0..32.
    assert split.base_fit_rows == 33
    # Calibration rows satisfy T >= S, i.e. indices 80..99.
    assert split.calibration_rows == 20
    # The 47 rows in between are dropped by the embargo and counted, never used twice.
    assert split.dropped_to_embargo == 47
    assert split.base_fit_rows + split.calibration_rows + split.dropped_to_embargo == 100


def test_the_split_refuses_a_non_chronological_or_unusable_training_portion():
    with pytest.raises(ModelError, match="chronological"):
        calibration_split([0, 2 * HOUR_SECONDS, HOUR_SECONDS])
    with pytest.raises(ModelError, match="too small"):
        calibration_split([0])
    # Every row inside one embargo window leaves the base-fit side empty.
    with pytest.raises(ModelError, match="unusable side"):
        calibration_split([index * HOUR_SECONDS for index in range(4)])


def test_the_direction_head_fails_closed_when_a_side_lacks_both_classes():
    open_times, matrix, directions, _ = synthetic_rows(300)
    one_sided = list(directions)
    boundary = calibration_split(open_times).boundary_index
    for index in range(boundary, len(one_sided)):
        one_sided[index] = UP
    with pytest.raises(ModelError, match="both directional classes"):
        fit_direction_head(open_times, matrix, one_sided)


def test_the_direction_head_returns_calibrated_probabilities_that_track_the_signal():
    open_times, matrix, directions, _ = synthetic_rows(600)
    head = fit_direction_head(open_times, matrix, directions)
    strong_up = [(2.0,) + tuple(0.0 for _ in range(FEATURE_COUNT - 1))]
    strong_down = [(-2.0,) + tuple(0.0 for _ in range(FEATURE_COUNT - 1))]
    probability_up = head.probability_up(strong_up)[0]
    probability_down = head.probability_up(strong_down)[0]
    assert 0.0 < probability_down < 0.5 < probability_up < 1.0
    assert declared_direction(probability_up) == UP
    assert declared_direction(probability_down) == DOWN
    # `probability` is always P(declared direction correct), so it never drops below 0.5.
    assert declared_probability(probability_up) == pytest.approx(probability_up)
    assert declared_probability(probability_down) == pytest.approx(1.0 - probability_down)
    assert declared_probability(probability_down) >= 0.5


def test_an_exact_tie_declares_up_and_there_is_no_abstention_threshold():
    assert declared_direction(0.5) == UP
    assert declared_probability(0.5) == 0.5
    assert declared_direction(0.5 - 1e-12) == DOWN


def test_only_base_fit_rows_can_move_the_base_coefficients():
    """Perturbing rows on the calibration side, or inside the embargo, must not refit the base."""
    open_times, matrix, directions, _ = synthetic_rows(400)
    split = calibration_split(open_times)
    boundary = split.boundary_open_time
    embargo = CALIBRATION_EMBARGO_HOURS * HOUR_SECONDS
    head = fit_direction_head(open_times, matrix, directions)

    perturbed = [
        tuple(value + 25.0 for value in row) if moment + embargo > boundary else row
        for moment, row in zip(open_times, matrix, strict=True)
    ]
    moved = fit_direction_head(open_times, perturbed, directions)
    assert list(head.base.coef_[0]) == list(moved.base.coef_[0])
    assert head.base.intercept_[0] == moved.base.intercept_[0]
    assert head.split == moved.split
    # The calibration map, by contrast, is allowed to see exactly those rows.
    assert list(head.platt.coef_[0]) != list(moved.platt.coef_[0])


def test_embargoed_rows_reach_neither_side_of_the_direction_head():
    open_times, matrix, directions, _ = synthetic_rows(400)
    split = calibration_split(open_times)
    boundary = split.boundary_open_time
    embargo = CALIBRATION_EMBARGO_HOURS * HOUR_SECONDS
    head = fit_direction_head(open_times, matrix, directions)
    perturbed = [
        tuple(value + 25.0 for value in row) if moment + embargo > boundary > moment else row
        for moment, row in zip(open_times, matrix, strict=True)
    ]
    moved = fit_direction_head(open_times, perturbed, directions)
    assert list(head.base.coef_[0]) == list(moved.base.coef_[0])
    assert list(head.platt.coef_[0]) == list(moved.platt.coef_[0])
    assert split.dropped_to_embargo > 0


def test_the_magnitude_head_recovers_a_linear_signal_and_keeps_its_sign():
    _, matrix, _, returns = synthetic_rows(500)
    head = fit_magnitude_head(matrix, returns)
    up_row = [(2.0,) + tuple(0.0 for _ in range(FEATURE_COUNT - 1))]
    down_row = [(-2.0,) + tuple(0.0 for _ in range(FEATURE_COUNT - 1))]
    assert head.expected_return(up_row)[0] > 0.0
    assert head.expected_return(down_row)[0] < 0.0
    assert head.training_rows == 500


def test_strength_is_an_inclusive_training_only_percentile_rank():
    matrix = [tuple(0.0 for _ in range(FEATURE_COUNT)) for _ in range(4)]
    head = fit_magnitude_head(matrix, [0.01, -0.02, 0.03, -0.04])
    # Training absolute moves sorted: 0.01, 0.02, 0.03, 0.04.
    assert head.strength([0.0])[0] == 0.0
    assert head.strength([0.01])[0] == 25.0
    assert head.strength([-0.03])[0] == 75.0
    assert head.strength([1.0])[0] == 100.0
    # Ties are inclusive, and the sign of the prediction never enters the rank.
    assert head.strength([0.02])[0] == head.strength([-0.02])[0] == 50.0


def test_the_heads_reject_the_wrong_feature_width():
    _, matrix, directions, returns = synthetic_rows(300)
    open_times = [index * HOUR_SECONDS for index in range(300)]
    head = fit_direction_head(open_times, matrix, directions)
    magnitude = fit_magnitude_head(matrix, returns)
    with pytest.raises(ModelError, match="feature width"):
        head.probability_up([(0.0, 0.0)])
    with pytest.raises(ModelError, match="feature width"):
        magnitude.expected_return([(0.0, 0.0)])


def test_the_direction_head_rejects_a_non_directional_training_label():
    open_times, matrix, directions, _ = synthetic_rows(300)
    broken = list(directions)
    broken[0] = "NEUTRAL"
    with pytest.raises(ModelError, match="non-directional"):
        fit_direction_head(open_times, matrix, broken)


def test_the_fit_is_deterministic_under_the_frozen_procedure():
    open_times, matrix, directions, returns = synthetic_rows(350)
    first = fit_direction_head(open_times, matrix, directions)
    second = fit_direction_head(open_times, matrix, directions)
    probe = [tuple(0.1 * index for index in range(FEATURE_COUNT))]
    assert first.probability_up(probe) == second.probability_up(probe)
    assert fit_magnitude_head(matrix, returns).expected_return(probe) == (
        fit_magnitude_head(matrix, returns).expected_return(probe)
    )
    assert math.isfinite(first.probability_up(probe)[0])
