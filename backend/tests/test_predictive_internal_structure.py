"""Proofs for the frozen experiment mechanics of `PREDICTIVE-INTERNAL-STRUCTURE-V1`.

Synthetic folds and hand-built gate inputs. This file never reads market data and never
asserts anything about the committed result; the committed artifacts are guarded separately.
"""

from __future__ import annotations

import pytest
from app.predictive import ABSTAIN, DOWN, NEUTRAL, UP
from app.predictive.folds import Fold
from app.predictive.internal_features import FEATURE_COUNT, FEATURE_NAMES
from app.predictive.internal_model import HGBR_MODEL_VERSION, LINEAR_MODEL_VERSION
from app.predictive.internal_structure import (
    ADVANCE,
    CANDIDATE_ALPHA,
    EXPERIMENT_ID,
    FAMILYWISE_ALPHA,
    FOLD_COVERAGE_GATE,
    GATE_NAMES,
    MINIMUM_IMPORTANT_EFFECT,
    MINIMUM_NON_NEGATIVE_FOLDS,
    NO_ADVANCE,
    POOLED_COVERAGE_GATE,
    STAGE1_FAMILY_SIZE,
    _fold_predictions,
    _matched_records,
    _matched_summary,
    advancement_gate,
    preregistration,
    search_plan,
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
    return advancement_gate(**arguments)


def test_the_frozen_gate_thresholds_are_what_the_design_declares():
    assert MINIMUM_IMPORTANT_EFFECT == 0.015
    assert POOLED_COVERAGE_GATE == 0.95
    assert FOLD_COVERAGE_GATE == 0.90
    assert MINIMUM_NON_NEGATIVE_FOLDS == 4
    assert FAMILYWISE_ALPHA == 0.05
    assert CANDIDATE_ALPHA == 0.025
    assert STAGE1_FAMILY_SIZE == 2


def test_all_five_conditions_must_hold_for_the_candidate_to_advance():
    record = gate()
    assert record["failed_conditions"] == []
    assert record["terminal_classification"] == ADVANCE
    assert set(record["conditions"]) == set(GATE_NAMES)


@pytest.mark.parametrize(
    ("overrides", "failed"),
    [
        ({"pooled_coverage": 0.9499}, GATE_NAMES[0]),
        ({"fold_coverage": {**PASSING_FOLD_COVERAGE, "2021": 0.8999}}, GATE_NAMES[1]),
        ({"pooled_delta": 0.0149}, GATE_NAMES[2]),
        ({"interval": [0.0, 0.04]}, GATE_NAMES[3]),
        (
            {
                "fold_deltas": {
                    **PASSING_FOLD_DELTAS,
                    "2022": -0.01,
                    "2023": -0.01,
                }
            },
            GATE_NAMES[4],
        ),
    ],
)
def test_each_condition_can_fail_the_candidate_on_its_own(overrides, failed):
    record = gate(**overrides)
    assert record["failed_conditions"] == [failed]
    assert record["terminal_classification"] == NO_ADVANCE
    assert record["secondary_metrics_used_to_rescue"] is False


def test_the_gate_boundaries_are_inclusive_exactly_where_declared():
    assert gate(pooled_coverage=POOLED_COVERAGE_GATE)["failed_conditions"] == []
    assert gate(pooled_delta=MINIMUM_IMPORTANT_EFFECT)["failed_conditions"] == []
    # The interval bound is strict: touching zero is not clearing zero.
    assert gate(interval=[0.0, 0.04])["failed_conditions"] == [GATE_NAMES[3]]
    # A fold delta of exactly zero counts as non-negative.
    zeroed = {**PASSING_FOLD_DELTAS, "2022": 0.0, "2024": 0.0}
    assert gate(fold_deltas=zeroed)["failed_conditions"] == []


def test_matched_records_pair_only_actionable_non_neutral_timestamps():
    from app.predictive.evaluation import Prediction

    labels = [
        Label(HOUR_SECONDS * 0, 100.0, 101.0, 0.01, UP),
        Label(HOUR_SECONDS * 1, 100.0, 99.0, -0.01, DOWN),
        Label(HOUR_SECONDS * 2, 100.0, 100.0, 0.0, NEUTRAL),
        Label(HOUR_SECONDS * 3, 100.0, 101.0, 0.01, UP),
    ]
    predictions = [
        Prediction(HOUR_SECONDS * 0, UP, 0.6),
        Prediction(HOUR_SECONDS * 1, UP, 0.6),
        Prediction(HOUR_SECONDS * 2, UP, 0.6),
        Prediction(HOUR_SECONDS * 3, ABSTAIN),
    ]
    records = _matched_records(predictions, labels)
    # The NEUTRAL truth and the abstention are both dropped from the paired comparison.
    assert [record.open_time for record in records] == [0, HOUR_SECONDS]
    assert [record.candidate_correct for record in records] == [True, False]
    # The matched control is ALWAYS_UP on exactly those same two timestamps.
    assert [record.baseline_correct for record in records] == [True, False]
    summary = _matched_summary(records, eligible=4)
    assert summary["paired_records"] == 2
    assert summary["delta"] == 0.0
    assert summary["matched_universe_share_of_eligible"] == 0.5


def synthetic_fold(training_rows: int = 600, evaluation_rows: int = 120, missing: int = 5):
    """A fold whose labels are directionally driven by the first feature, with a few gaps."""
    import numpy as np

    generator = np.random.default_rng(31)
    total = training_rows + evaluation_rows
    matrix = generator.normal(size=(total, FEATURE_COUNT))
    signal = matrix[:, 0]
    noisy = signal + 1.2 * generator.normal(size=total)
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
        # The last `missing` evaluation instants have no causal feature vector at all.
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
    abstentions = [item for item in directional if item.direction == ABSTAIN]
    assert len(abstentions) == 5
    assert record["evaluation_rows_feature_unavailable"] == 5
    assert record["evaluation_rows_feature_valid"] == len(fold.evaluation) - 5
    # A declared side always carries a probability; an abstention never invents one.
    for item in directional:
        if item.direction == ABSTAIN:
            assert item.probability is None
        else:
            assert item.probability is not None and item.probability >= 0.5
    # Magnitude is declared only where the feature vector exists, and is never imputed.
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
    assert record["training_labels"] == len(fold.training)
    assert record["training_rows_feature_valid"] == len(fold.training)
    assert record["training_rows_feature_unavailable"] == 0
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
    assert {item.direction for item in directional} == {UP, DOWN}


def test_the_frozen_records_carry_the_design_without_drift():
    plan, prereg = search_plan(), preregistration()
    assert plan["status"] == "FROZEN_BEFORE_OBSERVATION"
    assert plan["family_size"] == 2
    versions = [item["model_version"] for item in plan["configurations"]]
    assert versions == [LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION]
    assert plan["configurations"][1]["executed_in_checkpoint"] is None
    assert plan["multiplicity"] == {
        "familywise_alpha": 0.05,
        "correction": "BONFERRONI",
        "per_configuration_alpha": 0.025,
        "interval_mass_per_configuration": 0.975,
    }
    assert plan["budget"]["consumed_by_this_checkpoint"] == 1
    assert "INVERSION_OR_NEGATION_OF_PREVIOUS_24H_SIGN_PERSISTENCE" in plan["forbidden"]

    assert prereg["experiment_id"] == EXPERIMENT_ID
    assert prereg["status"] == "PREREGISTERED"
    assert prereg["features"]["ordered_names"] == list(FEATURE_NAMES)
    assert prereg["features"]["count"] == FEATURE_COUNT == 18
    assert prereg["primary_effect"]["minimum_important_effect"] == MINIMUM_IMPORTANT_EFFECT
    assert prereg["inference"]["alpha"] == CANDIDATE_ALPHA
    assert prereg["inference"]["interval"] == "CENTRAL_97_5_PERCENT_PERCENTILE"
    assert prereg["advancement_gate"]["pass_classification"] == ADVANCE
    assert prereg["advancement_gate"]["fail_classification"] == NO_ADVANCE
    assert prereg["advancement_gate"]["secondary_metrics_may_rescue_primary_gate"] is False
    assert prereg["budget"]["hyperparameter_search"] is False
    assert prereg["boundaries"]["sealed_queries"] == 0
    assert prereg["boundaries"]["previous_24h_sign_persistence_inverted"] is False
    assert prereg["evaluation_design"]["folds_recut"] is False
    assert prereg["model"]["probability_threshold_searched"] is False
