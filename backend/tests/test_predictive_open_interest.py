"""Proofs for the Stage-2 open-interest advancement gate, frozen records and fold selection.

Hand-built gate inputs and synthetic folds. This file never reads market data and never
asserts anything about the committed result; the committed artifacts are guarded separately.
"""

from __future__ import annotations

from typing import Any

import pytest
from app.predictive import ABSTAIN, DOWN, UP
from app.predictive.folds import Fold
from app.predictive.labels import HOUR_SECONDS, Label
from app.predictive.open_interest import (
    ADVANCE,
    CONFIGURATION_ORDER,
    EXPERIMENT_IDS,
    FAMILY_SIZE,
    GATE_NAMES,
    HGBR_MODEL_VERSION,
    HGBR_PARAMETERS,
    HYPOTHESIS_IDS,
    LINEAR_DIRECTION_PARAMETERS,
    LINEAR_MAGNITUDE_PARAMETERS,
    LINEAR_MODEL_VERSION,
    MINIMUM_IMPORTANT_EFFECT,
    NO_ADVANCE,
    PAIRED_SEED,
    _fold_predictions,
    advancement_gate,
    director_decisions,
    required_non_negative_folds,
    specification,
)
from app.predictive.open_interest_audit import (
    CANDIDATE_FOLDS,
    FOLD_COVERAGE_GATE,
    MINIMUM_ADMISSIBLE_FOLDS,
    MINIMUM_ELIGIBLE_TIMESTAMPS,
    MINIMUM_TRAINING_HISTORY_DAYS,
)
from app.predictive.open_interest_source import FEATURE_COUNT

FOLDS = ("2022", "2023", "2024")
PASSING_COVERAGE = dict.fromkeys(FOLDS, 0.99)
PASSING_DELTAS = {"2022": 0.02, "2023": 0.03, "2024": -0.01}


def gate(model_version: str = LINEAR_MODEL_VERSION, **overrides):
    arguments: dict[str, Any] = {
        "pooled_coverage": 0.99,
        "fold_coverage": PASSING_COVERAGE,
        "pooled_delta": 0.02,
        "interval": [0.005, 0.035],
        "candidate_win_rate": 0.55,
        "base_rate_win_rate": 0.52,
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
    assert PAIRED_SEED == 20260917
    assert HGBR_PARAMETERS["random_state"] == 20260917
    assert FOLD_COVERAGE_GATE == 0.95
    assert MINIMUM_TRAINING_HISTORY_DAYS == 180
    assert MINIMUM_ADMISSIBLE_FOLDS == 3
    assert MINIMUM_ELIGIBLE_TIMESTAMPS == 20_000
    assert CANDIDATE_FOLDS == ("2020", "2021", "2022", "2023", "2024")


def test_the_two_thirds_fold_rule_is_hand_computable():
    assert required_non_negative_folds(3) == 2
    assert required_non_negative_folds(4) == 3
    assert required_non_negative_folds(5) == 4


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_all_seven_conditions_must_hold_to_advance(model_version):
    record = gate(model_version)
    assert record["failed_conditions"] == []
    assert record["terminal_classification"] == ADVANCE[model_version]
    assert set(record["conditions"]) == set(GATE_NAMES)
    assert record["all_must_hold"] is True
    assert record["magnitude_used_to_rescue"] is False
    assert record["required_non_negative_folds"] == 2
    assert record["included_fold_count"] == 3


@pytest.mark.parametrize(
    ("overrides", "failed"),
    [
        ({"pooled_coverage": 0.9499}, GATE_NAMES[0]),
        ({"fold_coverage": {**PASSING_COVERAGE, "2023": 0.8999}}, GATE_NAMES[1]),
        ({"pooled_delta": 0.0149}, GATE_NAMES[2]),
        ({"interval": [0.0, 0.04]}, GATE_NAMES[3]),
        ({"candidate_win_rate": 0.5199, "base_rate_win_rate": 0.52}, GATE_NAMES[4]),
        ({"candidate_brier": 0.2500001}, GATE_NAMES[5]),
        ({"fold_deltas": {"2022": -0.01, "2023": -0.02, "2024": 0.03}}, GATE_NAMES[6]),
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


def test_beating_a_weak_training_majority_control_alone_cannot_advance():
    """The candidate must clear matched ALWAYS_UP, not merely a temporarily weak control."""
    record = gate(
        pooled_delta=0.001,
        interval=[-0.01, 0.02],
        candidate_win_rate=0.55,
        base_rate_win_rate=0.40,
    )
    assert GATE_NAMES[2] in record["failed_conditions"]
    assert GATE_NAMES[3] in record["failed_conditions"]
    assert record["conditions"][GATE_NAMES[4]]["passed"] is True
    assert record["terminal_classification"] == NO_ADVANCE[LINEAR_MODEL_VERSION]


def test_a_worse_brier_than_the_training_base_rate_cannot_advance():
    record = gate(candidate_brier=0.26, base_rate_brier=0.25)
    assert record["failed_conditions"] == [GATE_NAMES[5]]
    assert record["conditions"][GATE_NAMES[5]]["threshold"] == 0.25
    assert record["terminal_classification"] == NO_ADVANCE[LINEAR_MODEL_VERSION]


def test_the_gate_boundaries_are_inclusive_exactly_where_declared():
    assert gate(pooled_coverage=0.95)["failed_conditions"] == []
    assert gate(pooled_delta=MINIMUM_IMPORTANT_EFFECT)["failed_conditions"] == []
    assert gate(candidate_win_rate=0.52, base_rate_win_rate=0.52)["failed_conditions"] == []
    assert gate(candidate_brier=0.25, base_rate_brier=0.25)["failed_conditions"] == []
    # Strict where declared strict.
    assert gate(interval=[0.0, 0.04])["failed_conditions"] == [GATE_NAMES[3]]
    # A fold delta of exactly zero counts as non-negative.
    assert gate(fold_deltas={"2022": 0.0, "2023": 0.0, "2024": -0.5})["failed_conditions"] == []


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
    assert decisions["rejected_family_results_immutable"] is True
    assert decisions["rejected_family_sealed_eligibility"] is False
    assert decisions["admitted_source"] == "BTCUSDT_USDM_PERPETUAL_OPEN_INTEREST"


def test_both_configurations_occupy_exactly_two_family_slots():
    assert len(CONFIGURATION_ORDER) == FAMILY_SIZE == 2
    assert set(EXPERIMENT_IDS) == {LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION}
    assert len(set(EXPERIMENT_IDS.values())) == 2
    assert set(HYPOTHESIS_IDS.values()) == {"H-PRED-OI-001", "H-PRED-OI-002"}


def test_both_configurations_share_one_procedure_apart_from_their_estimators():
    linear, boosted = specification(LINEAR_MODEL_VERSION), specification(HGBR_MODEL_VERSION)
    for shared in (
        "family",
        "calibration_estimator",
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
        "abstention_only_on_source_or_feature_validity",
    ):
        assert linear[shared] == boosted[shared], shared
    assert linear["direction_base_parameters"] == LINEAR_DIRECTION_PARAMETERS
    assert linear["magnitude_parameters"] == LINEAR_MAGNITUDE_PARAMETERS
    assert boosted["direction_base_parameters"] == HGBR_PARAMETERS
    assert boosted["magnitude_loss"] == "squared_error"


def synthetic_fold(training_rows: int = 700, evaluation_rows: int = 150, missing: int = 6):
    """A fold whose labels follow the OI features, with a few source-unavailable rows."""
    import numpy as np

    generator = np.random.default_rng(29)
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
    record, directional, magnitude = _fold_predictions(model_version, fold, cache)
    assert sum(1 for item in directional if item.direction == ABSTAIN) == 6
    assert record["evaluation_rows_source_unavailable"] == 6
    for item in directional:
        if item.direction == ABSTAIN:
            assert item.probability is None
        else:
            assert item.probability is not None and item.probability >= 0.5
    assert len(magnitude) == len(fold.evaluation) - 6
    assert all(item.expected_return is not None for item in magnitude)


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_the_fold_fit_accounting_closes_and_keeps_evaluation_out_of_the_fit(model_version):
    fold, cache = synthetic_fold()
    record, directional, _ = _fold_predictions(model_version, fold, cache)
    assert record["model_fits"] == {
        "direction_base": 1,
        "direction_calibration": 1,
        "magnitude": 1,
    }
    assert (
        record["direction_base_fit_rows"]
        + record["direction_calibration_rows"]
        + record["direction_rows_dropped_to_calibration_embargo"]
        == record["training_rows_source_eligible"]
    )
    assert record["magnitude_training_rows"] == record["training_rows_source_eligible"]
    assert record["training_rows_source_eligible"] <= len(fold.training)
    assert len(directional) == len(fold.evaluation)


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_both_model_families_are_deterministic_under_frozen_settings(model_version):
    fold, cache = synthetic_fold()
    first = _fold_predictions(model_version, fold, cache)
    second = _fold_predictions(model_version, fold, cache)
    assert [item.direction for item in first[1]] == [item.direction for item in second[1]]
    assert [item.probability for item in first[1]] == [item.probability for item in second[1]]
    assert [item.expected_return for item in first[2]] == [
        item.expected_return for item in second[2]
    ]
