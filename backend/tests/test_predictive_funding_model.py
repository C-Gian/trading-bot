"""Proofs for the two frozen Stage-2 settled-funding dual-head configurations.

Synthetic data only. Determinism under the fixed seed, training-only calibration separation,
fail-closed behaviour on a one-class split side, and the fact that both configurations share
one procedure apart from their estimators.
"""

from __future__ import annotations

import pytest
from app.predictive import DOWN, UP
from app.predictive.funding_model import (
    HGBR_MAGNITUDE_LOSS,
    HGBR_MODEL_VERSION,
    HGBR_PARAMETERS,
    LINEAR_DIRECTION_PARAMETERS,
    LINEAR_MAGNITUDE_PARAMETERS,
    LINEAR_MODEL_VERSION,
    fit_direction_head,
    fit_magnitude_head,
    specification,
)
from app.predictive.funding_source import FEATURE_COUNT
from app.predictive.internal_model import (
    CALIBRATION_EMBARGO_HOURS,
    ModelError,
    calibration_split,
    declared_direction,
    declared_probability,
)
from app.predictive.labels import HOUR_SECONDS

CONFIGURATIONS = (LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION)


def synthetic_rows(count: int, seed: int = 11):
    """Deterministic, deliberately non-separable rows on the five-feature width."""
    import numpy as np

    generator = np.random.default_rng(seed)
    matrix = generator.normal(size=(count, FEATURE_COUNT))
    signal = matrix[:, 0] + 0.5 * matrix[:, 1] * matrix[:, 2]
    noisy = signal + 1.2 * generator.normal(size=count)
    open_times = [index * HOUR_SECONDS for index in range(count)]
    directions = [UP if value > 0 else DOWN for value in noisy]
    returns = [float(0.02 * value) for value in signal]
    return open_times, [tuple(float(x) for x in row) for row in matrix], directions, returns


def test_the_frozen_parameters_are_what_the_design_declares():
    assert LINEAR_DIRECTION_PARAMETERS == {
        "penalty": "l2",
        "C": 1.0,
        "solver": "lbfgs",
        "fit_intercept": True,
        "max_iter": 2000,
        "tol": 1e-8,
        "class_weight": None,
    }
    assert LINEAR_MAGNITUDE_PARAMETERS == {"alpha": 1.0, "fit_intercept": True}
    assert HGBR_PARAMETERS == {
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 15,
        "min_samples_leaf": 50,
        "l2_regularization": 1.0,
        "max_bins": 255,
        "early_stopping": False,
        "random_state": 20260916,
    }
    assert HGBR_MAGNITUDE_LOSS == "squared_error"


def test_both_configurations_share_one_procedure_apart_from_their_estimators():
    linear, boosted = specification(LINEAR_MODEL_VERSION), specification(HGBR_MODEL_VERSION)
    for shared in (
        "family",
        "calibration_estimator",
        "calibration_parameters",
        "calibration_input",
        "calibration_split_fraction",
        "calibration_embargo_hours",
        "magnitude_target",
        "magnitude_target_clipping",
        "decision_rule",
        "probability_rule",
        "strength_rule",
        "probability_threshold_searched",
        "hyperparameter_search",
        "selective_abstention_beyond_source_availability",
    ):
        assert linear[shared] == boosted[shared], shared
    assert linear["direction_base_estimator"] == "LogisticRegression"
    assert boosted["direction_base_estimator"] == "HistGradientBoostingClassifier"
    assert linear["magnitude_estimator"] == "Ridge"
    assert boosted["magnitude_estimator"] == "HistGradientBoostingRegressor"
    assert linear["direction_input_scaling"].startswith("STANDARD_SCALER")
    assert boosted["direction_input_scaling"] == "NONE_NOT_REQUIRED"


def test_an_unknown_configuration_is_refused():
    with pytest.raises(ModelError, match="unknown Stage-2 configuration"):
        specification("FUNDING_SOMETHING_ELSE_V1")


@pytest.mark.parametrize("model_version", CONFIGURATIONS)
def test_the_direction_head_fails_closed_when_a_side_lacks_both_classes(model_version):
    open_times, matrix, directions, _ = synthetic_rows(400)
    one_sided = list(directions)
    boundary = calibration_split(open_times).boundary_index
    for index in range(boundary, len(one_sided)):
        one_sided[index] = UP
    with pytest.raises(ModelError, match="both directional classes"):
        fit_direction_head(model_version, open_times, matrix, one_sided)


@pytest.mark.parametrize("model_version", CONFIGURATIONS)
def test_the_direction_head_rejects_a_non_directional_training_label(model_version):
    open_times, matrix, directions, _ = synthetic_rows(400)
    broken = list(directions)
    broken[0] = "NEUTRAL"
    with pytest.raises(ModelError, match="non-directional"):
        fit_direction_head(model_version, open_times, matrix, broken)


@pytest.mark.parametrize("model_version", CONFIGURATIONS)
def test_the_fit_is_deterministic_under_the_fixed_seed(model_version):
    open_times, matrix, directions, returns = synthetic_rows(600)
    probe = [tuple(0.1 * index for index in range(FEATURE_COUNT))]
    first = fit_direction_head(model_version, open_times, matrix, directions)
    second = fit_direction_head(model_version, open_times, matrix, directions)
    assert first.probability_up(probe) == second.probability_up(probe)
    assert fit_magnitude_head(model_version, matrix, returns).expected_return(probe) == (
        fit_magnitude_head(model_version, matrix, returns).expected_return(probe)
    )


@pytest.mark.parametrize("model_version", CONFIGURATIONS)
def test_only_base_fit_rows_can_move_the_base_model(model_version):
    """Rows on the calibration side of the split must never refit the base model."""
    open_times, matrix, directions, _ = synthetic_rows(600)
    split = calibration_split(open_times)
    boundary = split.boundary_open_time
    embargo = CALIBRATION_EMBARGO_HOURS * HOUR_SECONDS
    head = fit_direction_head(model_version, open_times, matrix, directions)
    probe = [tuple(0.1 * index for index in range(FEATURE_COUNT))]
    design = head._design(probe)
    baseline = head.base.decision_function(design)[0]

    perturbed = [
        tuple(value + 25.0 for value in row) if moment + embargo > boundary else row
        for moment, row in zip(open_times, matrix, strict=True)
    ]
    moved = fit_direction_head(model_version, open_times, perturbed, directions)
    assert moved.base.decision_function(moved._design(probe))[0] == baseline
    assert head.split == moved.split
    # The calibration map is allowed to see exactly those rows, and does.
    assert list(head.platt.coef_[0]) != list(moved.platt.coef_[0])


@pytest.mark.parametrize("model_version", CONFIGURATIONS)
def test_embargoed_rows_reach_neither_side_of_the_direction_head(model_version):
    open_times, matrix, directions, _ = synthetic_rows(600)
    split = calibration_split(open_times)
    boundary = split.boundary_open_time
    embargo = CALIBRATION_EMBARGO_HOURS * HOUR_SECONDS
    head = fit_direction_head(model_version, open_times, matrix, directions)
    probe = [tuple(0.1 * index for index in range(FEATURE_COUNT))]
    perturbed = [
        tuple(value + 25.0 for value in row) if moment + embargo > boundary > moment else row
        for moment, row in zip(open_times, matrix, strict=True)
    ]
    moved = fit_direction_head(model_version, open_times, perturbed, directions)
    assert (
        moved.base.decision_function(moved._design(probe))[0]
        == (head.base.decision_function(head._design(probe))[0])
    )
    assert list(head.platt.coef_[0]) == list(moved.platt.coef_[0])
    assert split.dropped_to_embargo > 0


@pytest.mark.parametrize("model_version", CONFIGURATIONS)
def test_the_calibrated_probability_is_a_probability_of_the_declared_direction(model_version):
    open_times, matrix, directions, _ = synthetic_rows(1200)
    head = fit_direction_head(model_version, open_times, matrix, directions)
    probabilities = head.probability_up(matrix[:300])
    assert all(0.0 <= value <= 1.0 for value in probabilities)
    assert min(probabilities) < 0.5 < max(probabilities)
    for value in probabilities:
        assert declared_probability(value) >= 0.5
        assert declared_direction(value) in {UP, DOWN}


@pytest.mark.parametrize("model_version", CONFIGURATIONS)
def test_strength_is_an_inclusive_training_only_percentile_rank(model_version):
    matrix = [tuple(float(index % 3) for _ in range(FEATURE_COUNT)) for index in range(4)]
    head = fit_magnitude_head(model_version, matrix, [0.01, -0.02, 0.03, -0.04])
    assert head.strength([0.0])[0] == 0.0
    assert head.strength([0.01])[0] == 25.0
    assert head.strength([-0.03])[0] == 75.0
    assert head.strength([1.0])[0] == 100.0
    assert head.strength([0.02])[0] == head.strength([-0.02])[0] == 50.0


@pytest.mark.parametrize("model_version", CONFIGURATIONS)
def test_the_heads_reject_the_wrong_feature_width(model_version):
    open_times, matrix, directions, returns = synthetic_rows(400)
    head = fit_direction_head(model_version, open_times, matrix, directions)
    magnitude = fit_magnitude_head(model_version, matrix, returns)
    with pytest.raises(ModelError, match="feature width"):
        head.probability_up([(0.0, 0.0)])
    with pytest.raises(ModelError, match="feature width"):
        magnitude.expected_return([(0.0, 0.0)])
