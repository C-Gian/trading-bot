"""Proofs for the Stage-2 advancement gate, the frozen records and the family accounting.

Hand-built gate inputs and synthetic folds. This file never reads market data and never
asserts anything about the committed result; the committed artifacts are guarded separately.
"""

from __future__ import annotations

from typing import Any

import pytest
from app.predictive import ABSTAIN, DOWN, UP
from app.predictive.folds import Fold
from app.predictive.funding_model import HGBR_MODEL_VERSION, LINEAR_MODEL_VERSION
from app.predictive.funding_source import FEATURE_COUNT, FEATURE_NAMES
from app.predictive.labels import HOUR_SECONDS, Label
from app.predictive.settled_funding import (
    ADVANCE,
    CONFIGURATION_ORDER,
    EVALUATION_FOLDS,
    EXPERIMENT_IDS,
    FAMILY,
    FAMILY_REJECTED,
    FAMILY_SIZE,
    GATE_NAMES,
    MATCHED_CONTROL,
    MINIMUM_IMPORTANT_EFFECT,
    NO_ADVANCE,
    NOT_ELIGIBLE,
    WARMUP_FOLD,
    _fold_predictions,
    advancement_gate,
    preregistration,
    search_plan,
    stage1_disposition,
)

PASSING_COVERAGE = {name: 0.99 for name in EVALUATION_FOLDS}
PASSING_DELTAS = {"2020": 0.02, "2021": 0.03, "2022": -0.01, "2023": 0.02, "2024": 0.02}


def gate(model_version: str = LINEAR_MODEL_VERSION, **overrides):
    arguments: dict[str, Any] = {
        "pooled_coverage": 0.99,
        "fold_coverage": PASSING_COVERAGE,
        "pooled_primary_delta": 0.02,
        "interval": [0.005, 0.035],
        "pooled_always_up_delta": 0.01,
        "fold_primary_deltas": PASSING_DELTAS,
        "candidate_brier": 0.24,
        "control_brier": 0.25,
    }
    arguments.update(overrides)
    return advancement_gate(model_version, **arguments)


def test_the_frozen_gate_thresholds_are_what_the_design_declares():
    assert MINIMUM_IMPORTANT_EFFECT == 0.015
    assert len(GATE_NAMES) == 7
    assert FAMILY_SIZE == 2
    assert EVALUATION_FOLDS == ("2020", "2021", "2022", "2023", "2024")
    assert WARMUP_FOLD == "2019"


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_all_seven_conditions_must_hold_to_advance(model_version):
    record = gate(model_version)
    assert record["failed_conditions"] == []
    assert record["terminal_classification"] == ADVANCE[model_version]
    assert set(record["conditions"]) == set(GATE_NAMES)
    assert record["all_must_hold"] is True
    assert record["magnitude_used_to_rescue"] is False


@pytest.mark.parametrize(
    ("overrides", "failed"),
    [
        ({"pooled_coverage": 0.9499}, GATE_NAMES[0]),
        ({"fold_coverage": {**PASSING_COVERAGE, "2022": 0.8999}}, GATE_NAMES[1]),
        ({"pooled_primary_delta": 0.0149}, GATE_NAMES[2]),
        ({"interval": [0.0, 0.04]}, GATE_NAMES[3]),
        ({"pooled_always_up_delta": 0.0}, GATE_NAMES[4]),
        (
            {"fold_primary_deltas": {**PASSING_DELTAS, "2023": -0.01, "2024": -0.01}},
            GATE_NAMES[5],
        ),
        ({"candidate_brier": 0.2500001}, GATE_NAMES[6]),
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
        fold_coverage={name: 0.20 for name in EVALUATION_FOLDS},
        pooled_primary_delta=0.30,
        interval=[0.25, 0.35],
        pooled_always_up_delta=0.28,
    )
    assert GATE_NAMES[0] in record["failed_conditions"]
    assert GATE_NAMES[1] in record["failed_conditions"]
    assert record["terminal_classification"] == NO_ADVANCE[LINEAR_MODEL_VERSION]
    # The directional conditions passed and still could not carry it.
    assert record["conditions"][GATE_NAMES[2]]["passed"] is True
    assert record["conditions"][GATE_NAMES[3]]["passed"] is True


def test_beating_the_training_base_rate_but_not_always_up_cannot_advance():
    record = gate(pooled_always_up_delta=-0.004)
    assert record["failed_conditions"] == [GATE_NAMES[4]]
    assert record["conditions"][GATE_NAMES[2]]["passed"] is True
    assert record["terminal_classification"] == NO_ADVANCE[LINEAR_MODEL_VERSION]


def test_a_worse_brier_than_the_matched_control_cannot_advance():
    record = gate(candidate_brier=0.26, control_brier=0.25)
    assert record["failed_conditions"] == [GATE_NAMES[6]]
    assert record["conditions"][GATE_NAMES[6]]["threshold"] == 0.25
    assert record["conditions"][GATE_NAMES[6]]["observed"] == 0.26
    assert record["terminal_classification"] == NO_ADVANCE[LINEAR_MODEL_VERSION]


def test_the_gate_boundaries_are_inclusive_exactly_where_declared():
    assert gate(pooled_coverage=0.95)["failed_conditions"] == []
    assert gate(pooled_primary_delta=MINIMUM_IMPORTANT_EFFECT)["failed_conditions"] == []
    assert gate(candidate_brier=0.25, control_brier=0.25)["failed_conditions"] == []
    # Strict where declared strict: touching zero is not clearing zero.
    assert gate(interval=[0.0, 0.04])["failed_conditions"] == [GATE_NAMES[3]]
    assert gate(pooled_always_up_delta=0.0)["failed_conditions"] == [GATE_NAMES[4]]
    # A fold delta of exactly zero counts as non-negative.
    assert gate(fold_primary_deltas={**PASSING_DELTAS, "2022": 0.0})["failed_conditions"] == []


def test_the_search_plan_freezes_exactly_two_configurations_with_no_early_stop():
    plan = search_plan()
    assert plan["status"] == "FROZEN_BEFORE_OBSERVATION"
    assert plan["family"] == FAMILY
    assert plan["family_size"] == FAMILY_SIZE == 2
    assert [item["model_version"] for item in plan["configurations"]] == list(CONFIGURATION_ORDER)
    assert [item["experiment_id"] for item in plan["configurations"]] == [
        EXPERIMENT_IDS[name] for name in CONFIGURATION_ORDER
    ]
    assert plan["both_configurations_executed_in_one_work_package"] is True
    assert plan["result_dependent_early_stop"] is False
    assert plan["multiplicity"] == {
        "familywise_alpha": 0.05,
        "correction": "BONFERRONI",
        "per_configuration_alpha": 0.025,
        "interval_mass_per_configuration": 0.975,
    }
    assert plan["budget"]["consumed_by_this_checkpoint"] == 2
    assert plan["budget"]["remaining_after_this_checkpoint"] == 0
    for forbidden in (
        "THIRD_STAGE2_FUNDING_MODEL",
        "POST_HOC_WINNER_SELECTION_BETWEEN_A_AND_B",
        "STAGE1_RESCUE_OR_REDESIGN",
        "CANONICAL_HOURLY_GAP_REPAIR",
        "OPEN_INTEREST_BASIS_POSITION_RATIO_CFTC_MACRO_NEWS_ONCHAIN_ADMISSION",
    ):
        assert forbidden in plan["forbidden"], forbidden


def test_the_stage1_disposition_records_the_closure_without_rewriting_it():
    disposition = stage1_disposition()
    assert disposition["family_disposition"] == FAMILY_REJECTED
    assert disposition["linear_sealed_eligibility"] == NOT_ELIGIBLE
    assert disposition["hgbr_sealed_eligibility"] == NOT_ELIGIBLE
    assert disposition["canonical_hourly_gap_repaired"] is False
    assert disposition["contiguity_rule_relaxed"] is False
    assert disposition["substrate_disposition"] == "DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH"
    assert disposition["stage1_results_changed"] is False
    assert disposition["stage2_opened"] is True
    assert "not claim that all possible internal" in disposition["scope"]


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_each_preregistration_carries_the_frozen_design(model_version):
    prereg = preregistration(model_version)
    assert prereg["experiment_id"] == EXPERIMENT_IDS[model_version]
    assert prereg["status"] == "PREREGISTERED"
    assert prereg["family"] == FAMILY
    assert prereg["features"]["ordered_names"] == list(FEATURE_NAMES)
    assert prereg["features"]["count"] == FEATURE_COUNT == 5
    assert prereg["features"]["stage1_contiguity_rule_inherited"] is False
    assert prereg["features"]["stage1_internal_price_features_present"] is False
    assert prereg["source"]["record_at_exactly_T_available"] is False
    assert prereg["source"]["interpolation"] is False
    assert prereg["source"]["forward_fill"] is False
    assert prereg["source"]["mark_price_premium_basis_open_interest_used"] is False
    assert prereg["evaluation_design"]["evaluation_folds"] == list(EVALUATION_FOLDS)
    assert prereg["evaluation_design"]["warmup_only_fold"] == WARMUP_FOLD
    assert prereg["matched_controls"]["primary"] == MATCHED_CONTROL
    assert prereg["matched_controls"]["persistence_inverted"] is False
    assert prereg["primary_effect"]["minimum_important_effect"] == MINIMUM_IMPORTANT_EFFECT
    assert prereg["inference"]["alpha"] == 0.025
    assert prereg["secondary_effect"]["interval_claimed"] is False
    assert prereg["advancement_gate"]["pass_classification"] == ADVANCE[model_version]
    assert prereg["advancement_gate"]["fail_classification"] == NO_ADVANCE[model_version]
    assert prereg["advancement_gate"]["magnitude_may_rescue_primary_gate"] is False
    assert len(prereg["advancement_gate"]["conditions"]) == 7
    assert prereg["budget"]["executed_regardless_of_the_other_result"] is True
    assert prereg["historical_wp015_results_used_as_evidence"] is False
    assert prereg["stage1_disposition"] == stage1_disposition()
    assert prereg["boundaries"]["post_hoc_winner_selection"] is False


def test_both_configurations_occupy_exactly_two_family_slots():
    assert len(CONFIGURATION_ORDER) == FAMILY_SIZE == 2
    assert set(EXPERIMENT_IDS) == {LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION}
    assert len(set(EXPERIMENT_IDS.values())) == 2
    orders = [
        preregistration(name)["search_plan_configuration_order"] for name in CONFIGURATION_ORDER
    ]
    assert orders == [1, 2]


def synthetic_fold(training_rows: int = 700, evaluation_rows: int = 150, missing: int = 4):
    """A fold whose labels follow the funding features, with a few source-unavailable rows."""
    import numpy as np

    generator = np.random.default_rng(23)
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
    assert sum(1 for item in directional if item.direction == ABSTAIN) == 4
    assert record["evaluation_rows_source_unavailable"] == 4
    assert record["evaluation_rows_source_eligible"] == len(fold.evaluation) - 4
    for item in directional:
        if item.direction == ABSTAIN:
            assert item.probability is None
        else:
            assert item.probability is not None and item.probability >= 0.5
    assert len(magnitude) == len(fold.evaluation) - 4
    assert all(item.expected_return is not None for item in magnitude)


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_the_fold_fit_accounting_closes_and_counts_three_fits(model_version):
    fold, cache = synthetic_fold()
    record, directional, _ = _fold_predictions(model_version, fold, cache)
    assert record["model_fits"] == {
        "direction_base": 1,
        "direction_calibration": 1,
        "magnitude": 1,
    }
    assert record["model_version"] == model_version
    assert (
        record["direction_base_fit_rows"]
        + record["direction_calibration_rows"]
        + record["direction_rows_dropped_to_calibration_embargo"]
        == record["training_rows_source_eligible"]
    )
    assert record["magnitude_training_rows"] == record["training_rows_source_eligible"]
    assert len(directional) == len(fold.evaluation)


@pytest.mark.parametrize("model_version", CONFIGURATION_ORDER)
def test_the_candidate_never_abstains_when_its_source_is_available(model_version):
    fold, cache = synthetic_fold(missing=0)
    _, directional, _ = _fold_predictions(model_version, fold, cache)
    assert all(item.direction in {UP, DOWN} for item in directional)
