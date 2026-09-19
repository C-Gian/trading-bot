"""Proofs for the Stage-3 cross-asset advancement gate, frozen records and fold selection.

Hand-built gate inputs and synthetic folds. This file never reads market data and never
asserts anything about the committed result; the committed artifacts are guarded separately.
"""

from __future__ import annotations

from typing import Any

import pytest
from app.predictive import ABSTAIN, DOWN, UP
from app.predictive.cross_asset import (
    ABSOLUTE_REFERENCE,
    ADVANCE,
    CONFIGURATION_ORDER,
    EXPERIMENT_IDS,
    FAMILY_SIZE,
    GATE_NAMES,
    HGBR_MODEL_VERSION,
    HGBR_PARAMETERS,
    HYPOTHESIS_IDS,
    LINEAR_DIRECTION_PARAMETERS,
    LINEAR_MODEL_VERSION,
    MATCHED_CONTROL,
    MINIMUM_IMPORTANT_EFFECT,
    NO_ADVANCE,
    PAIRED_SEED,
    ROOT_HYPOTHESIS_ID,
    _fold_predictions,
    advancement_gate,
    director_decisions,
    required_non_negative_folds,
    specification,
)
from app.predictive.cross_asset_audit import (
    CANDIDATE_FOLDS,
    FOLD_COVERAGE_GATE,
    MINIMUM_ADMISSIBLE_FOLDS,
    MINIMUM_ELIGIBLE_TIMESTAMPS,
    MINIMUM_TRAINING_HISTORY_DAYS,
)
from app.predictive.cross_asset_source import FEATURE_COUNT
from app.predictive.folds import Fold
from app.predictive.labels import HOUR_SECONDS, Label

FOLDS = ("2020", "2021", "2022", "2023", "2024")
PASSING_COVERAGE = dict.fromkeys(FOLDS, 0.99)
PASSING_DELTAS = {"2020": 0.02, "2021": 0.03, "2022": 0.02, "2023": 0.01, "2024": -0.01}


def gate(model_version: str = LINEAR_MODEL_VERSION, **overrides):
    arguments: dict[str, Any] = {
        "pooled_coverage": 0.99,
        "fold_coverage": PASSING_COVERAGE,
        "pooled_delta": 0.02,
        "interval": [0.005, 0.035],
        "candidate_win_rate": 0.55,
        "always_up_win_rate": 0.52,
        "candidate_brier": 0.24,
        "base_rate_brier": 0.25,
        "fold_deltas": PASSING_DELTAS,
    }
    arguments.update(overrides)
    return advancement_gate(model_version, **arguments)


def test_the_frozen_thresholds_and_seed_are_what_the_design_declares():
    assert MINIMUM_IMPORTANT_EFFECT == 0.015
    assert len(GATE_NAMES) == 7
    assert FAMILY_SIZE == 2
    assert PAIRED_SEED == 20260919
    assert HGBR_PARAMETERS["random_state"] == 20260917
    assert FOLD_COVERAGE_GATE == 0.95
    assert MINIMUM_TRAINING_HISTORY_DAYS == 180
    assert MINIMUM_ADMISSIBLE_FOLDS == 5
    assert MINIMUM_ELIGIBLE_TIMESTAMPS == 40_000
    assert CANDIDATE_FOLDS == ("2019", "2020", "2021", "2022", "2023", "2024")


def test_the_primary_effect_is_measured_against_the_information_free_control():
    assert MATCHED_CONTROL == "TRAINING_UP_BASE_RATE"
    assert ABSOLUTE_REFERENCE == "ALWAYS_UP"
    assert GATE_NAMES[2] == "POOLED_DELTA_VERSUS_MATCHED_TRAINING_BASE_RATE_AT_LEAST_MESI"
    assert GATE_NAMES[4] == "WIN_RATE_AT_LEAST_MATCHED_ALWAYS_UP"
    assert GATE_NAMES[5] == "BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER"


def test_the_two_thirds_fold_rule_is_hand_computable():
    assert required_non_negative_folds(3) == 2
    assert required_non_negative_folds(5) == 4
    assert required_non_negative_folds(6) == 4


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_all_seven_conditions_must_hold_to_advance(model_version):
    record = gate(model_version)
    assert record["failed_conditions"] == []
    assert record["terminal_classification"] == ADVANCE[model_version]
    assert set(record["conditions"]) == set(GATE_NAMES)
    assert record["all_must_hold"] is True
    assert record["secondary_metric_used_to_rescue"] is False
    assert record["required_non_negative_folds"] == 4
    assert record["included_fold_count"] == 5


@pytest.mark.parametrize(
    ("overrides", "failed"),
    [
        ({"pooled_coverage": 0.9499}, GATE_NAMES[0]),
        ({"fold_coverage": {**PASSING_COVERAGE, "2023": 0.8999}}, GATE_NAMES[1]),
        ({"pooled_delta": 0.0149}, GATE_NAMES[2]),
        ({"interval": [0.0, 0.04]}, GATE_NAMES[3]),
        ({"candidate_win_rate": 0.5199, "always_up_win_rate": 0.52}, GATE_NAMES[4]),
        ({"candidate_brier": 0.2500001}, GATE_NAMES[5]),
        (
            {
                "fold_deltas": {
                    "2020": -0.01,
                    "2021": -0.02,
                    "2022": 0.03,
                    "2023": 0.02,
                    "2024": 0.01,
                }
            },
            GATE_NAMES[6],
        ),
    ],
)
def test_each_condition_can_fail_the_candidate_on_its_own(overrides, failed):
    record = gate(**overrides)
    assert record["failed_conditions"] == [failed]
    assert record["terminal_classification"] == NO_ADVANCE[LINEAR_MODEL_VERSION]


def test_a_high_win_rate_with_low_coverage_cannot_advance():
    """Trivial abstention is never predictive success, however large the delta."""
    record = gate(
        pooled_coverage=0.20,
        fold_coverage=dict.fromkeys(FOLDS, 0.20),
        pooled_delta=0.30,
        interval=[0.25, 0.35],
        candidate_win_rate=0.80,
    )
    assert GATE_NAMES[0] in record["failed_conditions"]
    assert GATE_NAMES[1] in record["failed_conditions"]
    assert record["terminal_classification"] == NO_ADVANCE[LINEAR_MODEL_VERSION]
    assert record["conditions"][GATE_NAMES[2]]["passed"] is True
    assert record["conditions"][GATE_NAMES[3]]["passed"] is True


def test_beating_a_weak_information_free_control_alone_cannot_advance():
    """Clearing the base rate while missing the absolute ALWAYS_UP floor cannot advance."""
    record = gate(
        pooled_delta=0.10,
        interval=[0.05, 0.15],
        candidate_win_rate=0.50,
        always_up_win_rate=0.52,
    )
    assert record["failed_conditions"] == [GATE_NAMES[4]]
    assert record["conditions"][GATE_NAMES[2]]["passed"] is True
    assert record["terminal_classification"] == NO_ADVANCE[LINEAR_MODEL_VERSION]


def test_a_worse_brier_than_the_training_base_rate_cannot_advance():
    record = gate(candidate_brier=0.26, base_rate_brier=0.25)
    assert record["failed_conditions"] == [GATE_NAMES[5]]
    assert record["conditions"][GATE_NAMES[5]]["threshold"] == 0.25
    assert record["terminal_classification"] == NO_ADVANCE[LINEAR_MODEL_VERSION]


def test_the_gate_boundaries_are_inclusive_exactly_where_declared():
    assert gate(pooled_coverage=0.95)["failed_conditions"] == []
    assert gate(pooled_delta=MINIMUM_IMPORTANT_EFFECT)["failed_conditions"] == []
    assert gate(candidate_win_rate=0.52, always_up_win_rate=0.52)["failed_conditions"] == []
    assert gate(candidate_brier=0.25, base_rate_brier=0.25)["failed_conditions"] == []
    # Strict where declared strict.
    assert gate(interval=[0.0, 0.04])["failed_conditions"] == [GATE_NAMES[3]]
    # A fold delta of exactly zero counts as non-negative.
    assert (
        gate(
            fold_deltas={
                "2020": 0.0,
                "2021": 0.0,
                "2022": 0.0,
                "2023": 0.0,
                "2024": -0.5,
            }
        )["failed_conditions"]
        == []
    )


def test_the_director_decisions_are_recorded_without_rescuing_anything():
    decisions = director_decisions()
    assert decisions["generation_continues"] is True
    assert decisions["target_or_horizon_changed"] is False
    assert decisions["canonical_hourly_gap_repaired"] is False
    assert decisions["contiguity_rule_relaxed"] is False
    assert decisions["stage1_substrate_disposition"] == (
        "DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH"
    )
    assert decisions["basis_authorized"] is False
    assert decisions["basis_disposition"] == "DEFERRED_NOT_REJECTED"
    assert decisions["rejected_family_results_immutable"] is True
    assert decisions["rejected_family_sealed_eligibility"] is False
    assert decisions["admitted_source"] == "BINANCE_SPOT_USDT_CROSS_SECTIONAL_BREADTH"
    assert decisions["magnitude_declared"] is False
    assert decisions["product_target_unchanged"] == "BTCUSDT"
    assert decisions["cross_assets_are_context_only"] is True
    assert decisions["incremental_control_omitted"] is True
    assert len(decisions["rejected_families_unchanged"]) == 3


def test_both_configurations_occupy_exactly_two_family_slots():
    assert len(CONFIGURATION_ORDER) == FAMILY_SIZE == 2
    assert set(EXPERIMENT_IDS) == {LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION}
    assert set(EXPERIMENT_IDS.values()) == {
        "EXP-PRED-007-CROSS-ASSET-BREADTH-LINEAR",
        "EXP-PRED-008-CROSS-ASSET-BREADTH-HGBR",
    }
    assert set(HYPOTHESIS_IDS.values()) == {"H-PRED-XB-001", "H-PRED-XB-002"}
    assert ROOT_HYPOTHESIS_ID == "H-PRED-XB-001"


def test_neither_configuration_declares_a_magnitude():
    for model_version in CONFIGURATION_ORDER:
        record = specification(model_version)
        assert record["declares_direction"] is True
        assert record["declares_probability"] is True
        assert record["declares_magnitude"] is False
        assert "magnitude_estimator" not in record


def test_both_configurations_share_one_procedure_apart_from_their_estimators():
    linear, boosted = specification(LINEAR_MODEL_VERSION), specification(HGBR_MODEL_VERSION)
    for shared in (
        "family",
        "calibration_estimator",
        "calibration_input",
        "calibration_split_fraction",
        "calibration_embargo_hours",
        "calibration_rows",
        "decision_rule",
        "probability_rule",
        "probability_threshold_searched",
        "hyperparameter_search",
        "abstention_only_on_source_or_feature_validity",
    ):
        assert linear[shared] == boosted[shared], shared
    assert linear["direction_base_parameters"] == LINEAR_DIRECTION_PARAMETERS
    assert boosted["direction_base_parameters"] == HGBR_PARAMETERS
    assert linear["direction_input_scaling"].startswith("STANDARD_SCALER")
    assert boosted["direction_input_scaling"] == "NONE_NOT_REQUIRED"


def synthetic_fold(training_rows: int = 700, evaluation_rows: int = 150, missing: int = 6):
    """A fold whose labels follow the breadth features, with a few unavailable rows."""
    import numpy as np

    generator = np.random.default_rng(31)
    total = training_rows + evaluation_rows
    matrix = generator.normal(size=(total, FEATURE_COUNT))
    noisy = matrix[:, 0] + 1.0 * generator.normal(size=total)
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


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_a_source_unavailable_timestamp_becomes_a_counted_abstention(model_version):
    fold, cache = synthetic_fold()
    record, directional = _fold_predictions(model_version, fold, cache)
    assert sum(1 for item in directional if item.direction == ABSTAIN) == 6
    assert record["evaluation_rows_source_unavailable"] == 6
    for item in directional:
        if item.direction == ABSTAIN:
            assert item.probability is None
        else:
            assert item.probability is not None and item.probability >= 0.5
            assert item.expected_return is None


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_the_fold_fit_accounting_closes_and_keeps_evaluation_out_of_the_fit(model_version):
    fold, cache = synthetic_fold()
    record, directional = _fold_predictions(model_version, fold, cache)
    assert record["model_fits"] == {"direction_base": 1, "direction_calibration": 1}
    assert (
        record["direction_base_fit_rows"]
        + record["direction_calibration_rows"]
        + record["direction_rows_dropped_to_calibration_embargo"]
        == record["training_rows_source_eligible"]
    )
    assert record["training_rows_source_eligible"] <= len(fold.training)
    assert len(directional) == len(fold.evaluation)


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_both_model_families_are_deterministic_under_frozen_settings(model_version):
    fold, cache = synthetic_fold()
    first = _fold_predictions(model_version, fold, cache)
    second = _fold_predictions(model_version, fold, cache)
    assert [item.direction for item in first[1]] == [item.direction for item in second[1]]
    assert [item.probability for item in first[1]] == [item.probability for item in second[1]]


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_a_head_built_for_another_family_width_is_refused(model_version):
    """The width guard is this family's own eight, not another family's five or six."""
    from app.predictive.internal_model import ModelError

    fold, cache = synthetic_fold()
    narrowed = {moment: values[:-1] for moment, values in cache.items()}
    with pytest.raises((ModelError, ValueError)):
        _fold_predictions(model_version, fold, narrowed)
