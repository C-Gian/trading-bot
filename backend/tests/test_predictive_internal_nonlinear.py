"""Proofs for the reserved configuration's experiment mechanics and frozen records.

Synthetic folds and hand-built gate inputs. This file never reads market data and never
asserts anything about the committed result; the committed artifacts are guarded separately.
"""

from __future__ import annotations

import pytest
from app.predictive import ABSTAIN, DOWN, UP
from app.predictive.folds import Fold
from app.predictive.internal_features import FEATURE_COUNT, FEATURE_NAMES
from app.predictive.internal_model import LINEAR_MODEL_VERSION
from app.predictive.internal_nonlinear import (
    ADVANCE,
    EXPERIMENT_ID,
    HYPOTHESIS_ID,
    IMPLEMENTATION_FILES,
    NO_ADVANCE,
    STAGE1_FAMILY_CLOSED,
    _directional_agreement,
    _fold_predictions,
    coverage_policy_decision,
    nonlinear_advancement_gate,
    preregistration,
)
from app.predictive.internal_nonlinear_model import MODEL_VERSION
from app.predictive.internal_structure import (
    CANDIDATE_ALPHA,
    GATE_NAMES,
    MINIMUM_IMPORTANT_EFFECT,
)
from app.predictive.labels import HOUR_SECONDS, Label

PASSING_FOLD_COVERAGE = {name: 0.99 for name in ("2019", "2020", "2021", "2022", "2023", "2024")}
PASSING_FOLD_DELTAS = {
    "2019": 0.02,
    "2020": 0.03,
    "2021": -0.01,
    "2022": 0.01,
    "2023": 0.02,
    "2024": -0.02,
}


def gate(**overrides):
    arguments = {
        "pooled_coverage": 0.99,
        "fold_coverage": PASSING_FOLD_COVERAGE,
        "pooled_delta": 0.02,
        "interval": [0.005, 0.035],
        "fold_deltas": PASSING_FOLD_DELTAS,
    }
    arguments.update(overrides)
    return nonlinear_advancement_gate(**arguments)


def test_the_gate_reuses_the_frozen_thresholds_with_this_configurations_labels():
    record = gate()
    assert record["failed_conditions"] == []
    assert record["terminal_classification"] == ADVANCE == "ADVANCE_INTERNAL_HGBR_V1"
    assert set(record["conditions"]) == set(GATE_NAMES)
    assert record["coverage_gates_known_unpassable_before_execution"] is True


@pytest.mark.parametrize(
    ("overrides", "failed"),
    [
        ({"pooled_coverage": 0.9499}, GATE_NAMES[0]),
        ({"fold_coverage": {**PASSING_FOLD_COVERAGE, "2021": 0.8999}}, GATE_NAMES[1]),
        ({"pooled_delta": 0.0149}, GATE_NAMES[2]),
        ({"interval": [0.0, 0.04]}, GATE_NAMES[3]),
        ({"fold_deltas": {**PASSING_FOLD_DELTAS, "2022": -0.01, "2023": -0.01}}, GATE_NAMES[4]),
    ],
)
def test_each_condition_can_fail_the_candidate_on_its_own(overrides, failed):
    record = gate(**overrides)
    assert record["failed_conditions"] == [failed]
    assert record["terminal_classification"] == NO_ADVANCE
    assert record["secondary_metrics_used_to_rescue"] is False


def test_a_failed_coverage_gate_cannot_be_rescued_by_a_strong_directional_result():
    """The whole point of the Research Director's ruling: the gates still bind."""
    record = gate(pooled_coverage=0.80, pooled_delta=0.25, interval=[0.20, 0.30])
    assert GATE_NAMES[0] in record["failed_conditions"]
    assert record["terminal_classification"] == NO_ADVANCE
    assert record["conditions"][GATE_NAMES[2]]["passed"] is True
    assert record["conditions"][GATE_NAMES[3]]["passed"] is True


def test_the_coverage_ruling_records_a_decision_and_weakens_nothing():
    ruling = coverage_policy_decision()
    assert ruling["option_taken"] == "OPTION_1_EXECUTE_UNCHANGED"
    assert ruling["decided_by"] == "RESEARCH_DIRECTOR"
    assert ruling["decided_before_any_hgbr_outer_evaluation_number"] is True
    assert ruling["reserved_configuration_executed_exactly_as_frozen"] is True
    assert ruling["feature_set_identical_to_linear"] is True
    assert ruling["feature_validity_rules_identical_to_linear"] is True
    assert ruling["coverage_thresholds_changed"] is False
    assert ruling["coverage_gates_known_unpassable_before_execution"] is True
    assert ruling["gates_waived"] is False
    assert ruling["gates_reinterpreted"] is False
    assert ruling["gates_removed"] is False
    assert ruling["all_advancement_conditions_all_must_hold"] is True
    assert ruling["directional_result_may_rescue_formal_advancement"] is False
    for rescue in (
        "window_rule_rescue_authorized",
        "gap_policy_rescue_authorized",
        "threshold_rescue_authorized",
        "feature_rescue_authorized",
        "parameter_rescue_authorized",
    ):
        assert ruling[rescue] is False


def test_the_preregistration_carries_the_design_and_the_ruling_without_drift():
    prereg = preregistration()
    assert prereg["experiment_id"] == EXPERIMENT_ID
    assert prereg["hypothesis_id"] == HYPOTHESIS_ID
    assert prereg["status"] == "PREREGISTERED"
    assert prereg["model_version"] == MODEL_VERSION
    assert prereg["predecessor_configuration"] == LINEAR_MODEL_VERSION
    assert prereg["scheduled_regardless_of_predecessor_result"] is True
    assert prereg["coverage_policy_decision"] == coverage_policy_decision()
    assert prereg["features"]["ordered_names"] == list(FEATURE_NAMES)
    assert prereg["features"]["count"] == FEATURE_COUNT == 18
    assert prereg["features"]["redesigned"] is False
    assert prereg["features"]["edge_rules_changed"] is False
    assert prereg["primary_effect"]["minimum_important_effect"] == MINIMUM_IMPORTANT_EFFECT
    assert prereg["inference"]["alpha"] == CANDIDATE_ALPHA == 0.025
    assert prereg["inference"]["interval"] == "CENTRAL_97_5_PERCENT_PERCENTILE"
    assert prereg["advancement_gate"]["pass_classification"] == ADVANCE
    assert prereg["advancement_gate"]["fail_classification"] == NO_ADVANCE
    assert prereg["advancement_gate"]["secondary_metrics_may_rescue_primary_gate"] is False
    assert prereg["budget"]["stage1_configurations_remaining_after_this_experiment"] == 0
    assert prereg["budget"]["closes_stage1_family"] is True
    assert prereg["budget"]["hyperparameter_search"] is False
    assert prereg["boundaries"]["third_stage1_model_family"] is False
    assert prereg["boundaries"]["linear_configuration_tuned_descendant"] is False
    assert prereg["linear_comparison"]["classification"] == "DESCRIPTIVE_NOT_A_PREREGISTERED_TEST"
    assert prereg["linear_comparison"]["replay_consumes_stage1_budget"] is False


def test_the_admitted_implementation_covers_both_configurations():
    """The linear files are hashed too: if they changed, the comparison would be invalid."""
    assert "backend/app/predictive/internal_structure.py" in IMPLEMENTATION_FILES
    assert "backend/app/predictive/internal_model.py" in IMPLEMENTATION_FILES
    assert "backend/app/predictive/internal_nonlinear.py" in IMPLEMENTATION_FILES
    assert "backend/app/predictive/internal_nonlinear_model.py" in IMPLEMENTATION_FILES
    assert "backend/app/predictive/internal_features.py" in IMPLEMENTATION_FILES
    assert "scripts/run_predictive_internal_nonlinear.py" in IMPLEMENTATION_FILES
    assert len(set(IMPLEMENTATION_FILES)) == len(IMPLEMENTATION_FILES)
    assert STAGE1_FAMILY_CLOSED == "CLOSED_BOTH_PREDECLARED_CONFIGURATIONS_EXECUTED"


def test_directional_agreement_is_hand_computable():
    linear = {0: UP, 3600: DOWN, 7200: UP}
    nonlinear = {0: UP, 3600: UP, 7200: UP}
    agreement = _directional_agreement(linear, nonlinear)
    assert agreement["shared_declared_timestamps"] == 3
    assert agreement["same_side"] == 2
    assert agreement["agreement_rate"] == pytest.approx(2 / 3)
    assert agreement["declared_sets_identical"] is True
    partial = _directional_agreement(linear, {0: UP})
    assert partial["shared_declared_timestamps"] == 1
    assert partial["declared_sets_identical"] is False


def synthetic_fold(training_rows: int = 700, evaluation_rows: int = 150, missing: int = 5):
    """A fold whose labels are driven by a feature interaction, with a few feature gaps."""
    import numpy as np

    generator = np.random.default_rng(31)
    total = training_rows + evaluation_rows
    matrix = generator.normal(size=(total, FEATURE_COUNT))
    signal = matrix[:, 0] * matrix[:, 1]
    noisy = signal + 1.0 * generator.normal(size=total)
    labels = []
    cache = {}
    for index in range(total):
        moment = index * HOUR_SECONDS
        value = float(0.02 * noisy[index])
        labels.append(
            Label(
                open_time=moment,
                decision_close=100.0,
                horizon_close=100.0 * (1.0 + value),
                r_24h=value,
                direction=UP if value > 0 else DOWN,
            )
        )
        if index < total - missing:
            cache[moment] = tuple(float(x) for x in matrix[index])
    fold = Fold(
        name="SYNTHETIC",
        start=training_rows * HOUR_SECONDS,
        end=total * HOUR_SECONDS,
        training=tuple(labels[:training_rows]),
        evaluation=tuple(labels[training_rows:]),
    )
    return fold, cache


def test_an_unavailable_feature_vector_becomes_a_counted_abstention():
    fold, cache = synthetic_fold()
    record, directional, magnitude = _fold_predictions(fold, cache)
    assert sum(1 for item in directional if item.direction == ABSTAIN) == 5
    assert record["evaluation_rows_feature_unavailable"] == 5
    assert record["evaluation_rows_feature_valid"] == len(fold.evaluation) - 5
    for item in directional:
        if item.direction == ABSTAIN:
            assert item.probability is None
        else:
            assert item.probability is not None and item.probability >= 0.5
    assert len(magnitude) == len(fold.evaluation) - 5
    assert all(item.expected_return is not None for item in magnitude)


def test_the_fold_fit_accounting_closes_and_counts_three_fits():
    fold, cache = synthetic_fold()
    record, directional, _ = _fold_predictions(fold, cache)
    assert record["model_fits"] == {
        "direction_base": 1,
        "direction_calibration": 1,
        "magnitude": 1,
    }
    assert (
        record["direction_base_fit_rows"]
        + record["direction_calibration_rows"]
        + record["direction_rows_dropped_to_calibration_embargo"]
        == record["training_rows_feature_valid"]
    )
    assert record["magnitude_training_rows"] == record["training_rows_feature_valid"]
    assert len(directional) == len(fold.evaluation)


def test_the_candidate_never_abstains_when_its_features_exist():
    fold, cache = synthetic_fold(missing=0)
    _, directional, _ = _fold_predictions(fold, cache)
    assert all(item.direction in {UP, DOWN} for item in directional)
