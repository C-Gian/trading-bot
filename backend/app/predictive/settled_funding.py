"""`PREDICTIVE-STAGE2-SETTLED-FUNDING-V1` — the first Stage-2 information family.

Two preregistered configurations, `FUNDING_LINEAR_DUAL_HEAD_V1` and
`FUNDING_HGBR_DUAL_HEAD_V1`, both executed in this work package regardless of the first
result, on five causal features derived only from strictly-prior settled BTCUSDT USD-M
perpetual funding.

The frozen target, labels, NEUTRAL handling, scorer, reliability bins and dependence-aware
bootstrap are those of `PREDICTIVE_EVALUATION_CONTRACT_V1` Amendment A1 and
`PREDICTIVE-BASELINES-V1`, narrowed only where §4 of the work package narrows them for source
availability. The label, fold and scoring modules are imported unchanged; their bytes are
hashed by two executed admissions and may not move.

This family deliberately does not inherit the Stage-1 169-bar contiguity rule, so the Stage-1
substrate defect is neither repaired nor carried forward.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import ABSTAIN, DOWN, HORIZON_HOURS, NEUTRAL, UP
from .baselines import (
    ALWAYS_UP,
    PREVIOUS_24H_SIGN_PERSISTENCE,
    ZERO_RETURN_MAGNITUDE,
    always_up_predictions,
    fit_training_up_base_rate,
    previous_24h_sign_predictions,
    training_up_base_rate_predictions,
    zero_return_magnitude_predictions,
)
from .evaluation import RELIABILITY_BIN_EDGES, Outcome, Prediction, score
from .folds import FOLD_BOUNDARIES, FOLD_DESIGN, PURGE_EMBARGO_HOURS, Fold, build_folds
from .folds import assert_no_boundary_leak as assert_no_fold_leak
from .funding_model import (
    FAMILY,
    HGBR_MODEL_VERSION,
    LINEAR_MODEL_VERSION,
    fit_direction_head,
    fit_magnitude_head,
    specification,
)
from .funding_source import (
    CONTRACT_PATH,
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    MANIFEST_PATH,
    MAX_SETTLEMENT_GAP_SECONDS,
    REQUIRED_SETTLEMENTS,
    UNAVAILABILITY_TAXONOMY,
    SettledFundingSource,
    build_funding_features,
    load_settled_funding,
    source_identity,
)
from .internal_model import (
    CALIBRATION_EMBARGO_HOURS,
    CALIBRATION_SPLIT_FRACTION,
    declared_direction,
    declared_probability,
)
from .internal_structure import ExperimentError, canonical_bytes, content_hash, payload_hash
from .labels import Bar, Label, build_labels, index_bars, load_hourly_bars
from .paired_inference import (
    PAIRED_ALPHA,
    PAIRED_BLOCK_LENGTH_HOURS,
    PAIRED_METHOD,
    PAIRED_REPLICATES,
    PAIRED_SEED,
    REPLICATE_CHUNK,
    PairedRecord,
    build_paired_fold,
    paired_delta_interval,
)

ROOT = Path(__file__).resolve().parents[3]

CHECKPOINT = "PREDICTIVE-STAGE2-SETTLED-FUNDING-V1"
RESEARCH_GENERATION = "PREDICTIVE_RESEARCH_GENERATION_V1"
HYPOTHESIS_ID = "H-PRED-FUND-001"
HYPOTHESIS_NAME = "CAUSAL_SETTLED_FUNDING_STRUCTURE_ADDS_24H_DIRECTIONAL_INFORMATION"
EVALUATION_CONTRACT = "docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md"
EVALUATION_CONTRACT_AMENDMENT = "A1"
BASELINE_PROTOCOL_PATH = "research/protocols/PREDICTIVE-BASELINES-V1.json"
SOURCE_ROADMAP_STAGE = "STAGE_2_DERIVATIVES_AND_POSITIONING"

LINEAR_EXPERIMENT_ID = "EXP-PRED-003-FUNDING-LINEAR-DUAL-HEAD"
HGBR_EXPERIMENT_ID = "EXP-PRED-004-FUNDING-HGBR-DUAL-HEAD"
EXPERIMENT_IDS = {
    LINEAR_MODEL_VERSION: LINEAR_EXPERIMENT_ID,
    HGBR_MODEL_VERSION: HGBR_EXPERIMENT_ID,
}
CONFIGURATION_ORDER = (LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION)

SEARCH_PLAN_PATH = "research/protocols/PREDICTIVE-STAGE2-SETTLED-FUNDING-SEARCH-PLAN-V1.json"
ADMISSION_PATH = "reports/validation/PREDICTIVE-STAGE2-SETTLED-FUNDING-V1-ADMISSION.json"
REPORT_JSON_PATH = "reports/research/PREDICTIVE-STAGE2-SETTLED-FUNDING-V1.json"
REPORT_MARKDOWN_PATH = "reports/research/PREDICTIVE-STAGE2-SETTLED-FUNDING-V1.md"

CREATED_AT = "2026-09-17T00:00:00Z"

# Evaluation folds for this family: the source begins in September 2019, so the frozen 2019
# fold is training/warmup only and is never scored.
EVALUATION_FOLDS = ("2020", "2021", "2022", "2023", "2024")
WARMUP_FOLD = "2019"

MINIMUM_IMPORTANT_EFFECT = 0.015
FAMILYWISE_ALPHA = 0.05
CANDIDATE_ALPHA = 0.025
POOLED_COVERAGE_GATE = 0.95
FOLD_COVERAGE_GATE = 0.90
MINIMUM_NON_NEGATIVE_FOLDS = 4
FAMILY_SIZE = 2

MATCHED_CONTROL = "MATCHED_TRAINING_UP_BASE_RATE"

GATE_NAMES = (
    "POOLED_SOURCE_COVERAGE_AT_LEAST_0_95",
    "EVERY_FOLD_COVERAGE_AT_LEAST_0_90",
    "POOLED_PRIMARY_DELTA_AT_LEAST_MESI",
    "PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO",
    "POOLED_DELTA_VERSUS_MATCHED_ALWAYS_UP_ABOVE_ZERO",
    "AT_LEAST_4_OF_5_FOLD_PRIMARY_DELTAS_NON_NEGATIVE",
    "POOLED_BRIER_AT_MOST_MATCHED_CONTROL_BRIER",
)

ADVANCE = {
    LINEAR_MODEL_VERSION: "ADVANCE_FUNDING_LINEAR_V1",
    HGBR_MODEL_VERSION: "ADVANCE_FUNDING_HGBR_V1",
}
NO_ADVANCE = {
    LINEAR_MODEL_VERSION: "NO_ADVANCE_FUNDING_LINEAR_V1",
    HGBR_MODEL_VERSION: "NO_ADVANCE_FUNDING_HGBR_V1",
}

FAMILY_REJECTED = "REJECTED_DEVELOPMENT_NO_SEALED"
FAMILY_SIGNAL = "DEVELOPMENT_SIGNAL_REQUIRES_RESEARCH_DIRECTOR_REVIEW"
NOT_ELIGIBLE = "NOT_ELIGIBLE_REJECTED_DEVELOPMENT"

IMPLEMENTATION_FILES = (
    "backend/app/predictive/__init__.py",
    "backend/app/predictive/baselines.py",
    "backend/app/predictive/evaluation.py",
    "backend/app/predictive/folds.py",
    "backend/app/predictive/funding_model.py",
    "backend/app/predictive/funding_source.py",
    "backend/app/predictive/internal_model.py",
    "backend/app/predictive/labels.py",
    "backend/app/predictive/paired_inference.py",
    "backend/app/predictive/settled_funding.py",
    "scripts/run_predictive_settled_funding.py",
)


def stage1_disposition() -> dict[str, Any]:
    """The Research Director's Stage-1 closure decisions, recorded with this checkpoint."""
    return {
        "decision_id": "PREDICTIVE_STAGE1_CLOSURE_V1",
        "decided_by": "RESEARCH_DIRECTOR",
        "family": "PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1",
        "family_disposition": FAMILY_REJECTED,
        "review_verdict": "ACCEPTED",
        "linear_experiment_id": "EXP-PRED-001-INTERNAL-LINEAR-DUAL-HEAD",
        "linear_sealed_eligibility": NOT_ELIGIBLE,
        "hgbr_experiment_id": "EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD",
        "hgbr_sealed_eligibility": NOT_ELIGIBLE,
        "rationale": (
            "Both frozen configurations were materially worse than their matched ALWAYS_UP "
            "control and both multiplicity-adjusted paired intervals lay entirely below zero."
        ),
        "scope": (
            "This rejects the defined two-configuration Stage-1 family only. It does not "
            "claim that all possible internal BTCUSDT information is useless."
        ),
        "canonical_hourly_gap_repaired": False,
        "contiguity_rule_relaxed": False,
        "substrate_disposition": "DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH",
        "substrate_revisit_rule": (
            "A future independent protocol may revisit the gap and contiguity rule only if "
            "scientifically justified on its own terms, never as a rescue of either "
            "Stage-1 result."
        ),
        "stage1_results_changed": False,
        "stage2_opened": True,
        "stage2_first_family": FAMILY,
    }


def search_plan() -> dict[str, Any]:
    """The Stage-2 model family, frozen before any Stage-2 result is observed."""
    return {
        "version": "PREDICTIVE_STAGE2_SETTLED_FUNDING_SEARCH_PLAN_V1",
        "status": "FROZEN_BEFORE_OBSERVATION",
        "checkpoint": CHECKPOINT,
        "research_generation": RESEARCH_GENERATION,
        "family": FAMILY,
        "source_roadmap_stage": SOURCE_ROADMAP_STAGE,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "baseline_protocol": BASELINE_PROTOCOL_PATH,
        "predictive_source_contract": CONTRACT_PATH,
        "purpose": (
            "Freeze the complete Stage-2 settled-funding model family before either "
            "configuration is executed, so neither can be influenced by the other's result."
        ),
        "family_size": FAMILY_SIZE,
        "both_configurations_executed_in_one_work_package": True,
        "result_dependent_early_stop": False,
        "configurations": [
            {
                "model_version": model_version,
                "experiment_id": EXPERIMENT_IDS[model_version],
                "order": index + 1,
                "specification": specification(model_version),
            }
            for index, model_version in enumerate(CONFIGURATION_ORDER)
        ],
        "multiplicity": {
            "familywise_alpha": FAMILYWISE_ALPHA,
            "correction": "BONFERRONI",
            "per_configuration_alpha": CANDIDATE_ALPHA,
            "interval_mass_per_configuration": 1.0 - CANDIDATE_ALPHA,
        },
        "budget": {
            "planned_model_configurations": FAMILY_SIZE,
            "consumed_by_this_checkpoint": FAMILY_SIZE,
            "remaining_after_this_checkpoint": 0,
        },
        "forbidden": [
            "THIRD_STAGE2_FUNDING_MODEL",
            "HYPERPARAMETER_SEARCH",
            "THRESHOLD_SEARCH",
            "FEATURE_SEARCH",
            "POST_HOC_WINNER_SELECTION_BETWEEN_A_AND_B",
            "STAGE1_RESCUE_OR_REDESIGN",
            "CANONICAL_HOURLY_GAP_REPAIR",
            "OPEN_INTEREST_BASIS_POSITION_RATIO_CFTC_MACRO_NEWS_ONCHAIN_ADMISSION",
            "INVERSION_OR_NEGATION_OF_PREVIOUS_24H_SIGN_PERSISTENCE",
        ],
        "boundaries": {
            "external_information_family_beyond_settled_funding": False,
            "post_cutoff_market_data": False,
            "sealed_queries": 0,
            "champion_created": False,
            "real_money": False,
        },
    }


def _shared_design() -> dict[str, Any]:
    return {
        "target": {
            "symbol": "BTCUSDT",
            "market": "crypto_spot",
            "canonical_resolution": "1m",
            "decision_cadence": "1h",
            "horizon_hours": HORIZON_HOURS,
            "label": "r_24h = log(close[T + 24h] / close[T])",
            "path_dependent": False,
        },
        "source": {
            "family": FAMILY,
            "manifest": MANIFEST_PATH,
            "predictive_contract": CONTRACT_PATH,
            "availability_rule": "FUNDING_TIME_STRICTLY_BEFORE_T",
            "record_at_exactly_T_available": False,
            "required_strictly_prior_settlements": REQUIRED_SETTLEMENTS,
            "maximum_gap_seconds_inside_the_chain": MAX_SETTLEMENT_GAP_SECONDS,
            "interpolation": False,
            "forward_fill": False,
            "fields_read": ["funding_time", "funding_rate"],
            "predicted_funding_used": False,
            "mark_price_premium_basis_open_interest_used": False,
        },
        "features": {
            "version": FEATURE_SET_VERSION,
            "count": len(FEATURE_NAMES),
            "ordered_names": list(FEATURE_NAMES),
            "stage1_internal_price_features_present": False,
            "stage1_contiguity_rule_inherited": False,
            "unavailability_taxonomy": list(UNAVAILABILITY_TAXONOMY),
            "unavailable_evaluation_row": "NEUTRAL_UNCERTAIN_ABSTENTION_COUNTED",
            "unavailable_training_row": "EXCLUDED_FROM_FITTING_COUNTED",
            "additional_transform_authorized": False,
        },
        "evaluation_design": {
            "design": FOLD_DESIGN,
            "random_k_fold": False,
            "outer_folds": len(EVALUATION_FOLDS),
            "evaluation_folds": list(EVALUATION_FOLDS),
            "warmup_only_fold": WARMUP_FOLD,
            "warmup_reason": "THE_SETTLED_FUNDING_SOURCE_BEGINS_IN_SEPTEMBER_2019",
            "fold_boundaries": [
                {"fold": name, "start": start, "end": end}
                for name, start, end in FOLD_BOUNDARIES
                if name in EVALUATION_FOLDS
            ],
            "purge_embargo_hours": PURGE_EMBARGO_HOURS,
            "training": "EXPANDING_CHRONOLOGICAL_STRICTLY_BEFORE_THE_FOLD",
            "folds_recut": False,
            "outer_evaluation_used_in_fitting": False,
            "source_eligibility_redefined_after_result": False,
        },
        "matched_controls": {
            "primary": MATCHED_CONTROL,
            "primary_semantics": "AMENDMENT_A1_TRAINING_UP_BASE_RATE_REFIT_PER_FOLD",
            "primary_training_universe": "SOURCE_ELIGIBLE_TRAINING_ROWS_OF_THAT_FOLD",
            "also_scored": [ALWAYS_UP, PREVIOUS_24H_SIGN_PERSISTENCE, ZERO_RETURN_MAGNITUDE],
            "scored_on": "IDENTICAL_CANDIDATE_ACTIONABLE_NON_NEUTRAL_TIMESTAMPS",
            "persistence_inverted": False,
        },
        "primary_effect": {
            "definition": (
                "candidate directional win rate - matched MATCHED_TRAINING_UP_BASE_RATE "
                "win rate, on the exact timestamps where the candidate is actionable"
            ),
            "matched_control": MATCHED_CONTROL,
            "minimum_important_effect": MINIMUM_IMPORTANT_EFFECT,
            "minimum_important_effect_units": "ABSOLUTE_WIN_RATE_POINTS",
        },
        "secondary_effect": {
            "definition": "candidate directional win rate - matched ALWAYS_UP win rate",
            "role": "ABSOLUTE_REFERENCE",
            "interval_claimed": False,
        },
        "inference": {
            "method": PAIRED_METHOD,
            "block_length_hours": PAIRED_BLOCK_LENGTH_HOURS,
            "replicates": PAIRED_REPLICATES,
            "seed": PAIRED_SEED,
            "replicate_chunk": REPLICATE_CHUNK,
            "familywise_alpha": FAMILYWISE_ALPHA,
            "multiplicity_correction": "BONFERRONI",
            "alpha": CANDIDATE_ALPHA,
            "interval": "CENTRAL_97_5_PERCENT_PERCENTILE",
            "resample_unit": "CONTIGUOUS_HOURLY_BLOCK_ON_THE_ORIGINAL_EVALUATION_TIMELINE",
            "blocks_cross_fold_boundaries": False,
            "abstentions_compressed_into_adjacency": False,
        },
        "mandatory_reporting": [
            "DIRECTIONAL_WIN_RATE_WITH_SAMPLE_SIZE_AND_COVERAGE",
            "BRIER_SCORE_AND_FIXED_BIN_RELIABILITY_TABLE",
            "SIGNED_RETURN_MAE_AND_MEDIAN_ABSOLUTE_ERROR",
            "SIGNED_MAGNITUDE_MATCH_DIAGNOSTIC_WITH_EXCLUSION_COUNTS",
            "CHRONOLOGICAL_PER_FOLD_RESULTS",
            "MATCHED_AND_CANONICAL_BASELINE_COMPARISONS",
        ],
        "reliability_bin_edges": list(RELIABILITY_BIN_EDGES),
    }


def preregistration(model_version: str) -> dict[str, Any]:
    """The frozen hypothesis, design, inference plan and advancement gate for one candidate."""
    if model_version not in EXPERIMENT_IDS:
        raise ExperimentError(f"unknown Stage-2 configuration: {model_version}")
    record = {
        "schema_version": 1,
        "record_type": "PREDICTIVE_EXPERIMENT_PREREGISTRATION_V1",
        "experiment_id": EXPERIMENT_IDS[model_version],
        "experiment_version": 1,
        "created_at_utc": CREATED_AT,
        "status": "PREREGISTERED",
        "checkpoint": CHECKPOINT,
        "research_generation": RESEARCH_GENERATION,
        "search_plan": SEARCH_PLAN_PATH,
        "search_plan_configuration_order": CONFIGURATION_ORDER.index(model_version) + 1,
        "family": FAMILY,
        "hypothesis_id": HYPOTHESIS_ID,
        "hypothesis_name": HYPOTHESIS_NAME,
        "hypothesis": (
            "Strictly prior, already-settled BTCUSDT USD-M perpetual funding history "
            "contains credible out-of-sample information about the frozen BTCUSDT spot 24h "
            "terminal direction, relative to an information-free chronological control and "
            "the canonical ALWAYS_UP baseline."
        ),
        "hypothesis_class": "MATERIAL_PREDICTIVE_HYPOTHESIS",
        "model_version": model_version,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "baseline_protocol": BASELINE_PROTOCOL_PATH,
        "source_roadmap_stage": SOURCE_ROADMAP_STAGE,
        "stage1_disposition": stage1_disposition(),
        "historical_wp015_results_used_as_evidence": False,
        "historical_wp015_reuse": "SOURCE_INTEGRITY_TOOLING_AND_CANONICAL_DATA_ONLY",
        "model": specification(model_version),
        "advancement_gate": {
            "all_must_hold": True,
            "conditions": [
                {"name": GATE_NAMES[0], "threshold": POOLED_COVERAGE_GATE},
                {"name": GATE_NAMES[1], "threshold": FOLD_COVERAGE_GATE},
                {"name": GATE_NAMES[2], "threshold": MINIMUM_IMPORTANT_EFFECT},
                {"name": GATE_NAMES[3], "threshold": 0.0},
                {"name": GATE_NAMES[4], "threshold": 0.0},
                {"name": GATE_NAMES[5], "threshold": MINIMUM_NON_NEGATIVE_FOLDS},
                {"name": GATE_NAMES[6], "threshold": "MATCHED_CONTROL_BRIER"},
            ],
            "pass_classification": ADVANCE[model_version],
            "fail_classification": NO_ADVANCE[model_version],
            "magnitude_may_rescue_primary_gate": False,
            "post_result_tuning_authorized": False,
        },
        "budget": {
            "family_configurations_planned": FAMILY_SIZE,
            "family_configurations_consumed_by_this_experiment": 1,
            "executed_regardless_of_the_other_result": True,
            "hyperparameter_search": False,
            "threshold_search": False,
            "feature_search": False,
        },
        "boundaries": {
            "stage1_rescue_or_redesign": False,
            "canonical_hourly_gap_repair": False,
            "additional_information_family": False,
            "post_cutoff_market_data": False,
            "sealed_queries": 0,
            "champion_created": False,
            "real_money": False,
            "historical_results_changed": False,
            "previous_24h_sign_persistence_inverted": False,
            "post_hoc_winner_selection": False,
        },
    }
    record.update(_shared_design())
    return record


def admission(root: Path = ROOT) -> dict[str, Any]:
    """Prove the frozen records, the source identity and the implementation precede results."""
    plan_path = root / SEARCH_PLAN_PATH
    if not plan_path.is_file():
        raise ExperimentError("the frozen search plan must exist before the admission gate")
    if json.loads(plan_path.read_text(encoding="utf-8")) != search_plan():
        raise ExperimentError("the committed search plan is not what the code declares")
    preregistrations: dict[str, str] = {}
    for model_version in CONFIGURATION_ORDER:
        relative = preregistration_path(model_version)
        path = root / relative
        if not path.is_file():
            raise ExperimentError(f"missing preregistration: {relative}")
        if json.loads(path.read_text(encoding="utf-8")) != preregistration(model_version):
            raise ExperimentError(f"the committed preregistration drifted: {relative}")
        preregistrations[EXPERIMENT_IDS[model_version]] = content_hash(path)
    if not (root / CONTRACT_PATH).is_file():
        raise ExperimentError("the predictive funding contract must exist before execution")
    missing = [name for name in IMPLEMENTATION_FILES if not (root / name).is_file()]
    if missing:
        raise ExperimentError(f"the implementation is incomplete: {missing}")
    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_PRE_EXECUTION_ADMISSION_V1",
        "checkpoint": CHECKPOINT,
        "family": FAMILY,
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "PASS",
        "search_plan": SEARCH_PLAN_PATH,
        "search_plan_sha256": content_hash(plan_path),
        "preregistration_sha256": preregistrations,
        "predictive_contract": CONTRACT_PATH,
        "predictive_contract_sha256": content_hash(root / CONTRACT_PATH),
        "source": source_identity(root),
        "implementation_sha256": {name: content_hash(root / name) for name in IMPLEMENTATION_FILES},
        "stage1_disposition": stage1_disposition(),
        "feature_set_version": FEATURE_SET_VERSION,
        "feature_count": len(FEATURE_NAMES),
        "family_configurations_planned": FAMILY_SIZE,
        "family_configurations_consumed_before_this_run": 0,
        "market_results_observed": 0,
        "model_fits_executed": 0,
        "post_cutoff_access": 0,
        "sealed_queries": 0,
        "champion_status": "NONE",
        "real_money": False,
    }


def preregistration_path(model_version: str) -> str:
    return f"research/experiments/{EXPERIMENT_IDS[model_version]}/preregistration.json"


def result_path(model_version: str) -> str:
    return f"research/experiments/{EXPERIMENT_IDS[model_version]}/result.json"


def trials_path(model_version: str) -> str:
    return f"research/experiments/{EXPERIMENT_IDS[model_version]}/trials.json"


def admission_identity(root: Path = ROOT) -> str:
    """One hash binding the frozen records, the source and the implementation together."""
    record = admission(root)
    return payload_hash(
        {
            "search_plan_sha256": record["search_plan_sha256"],
            "preregistration_sha256": record["preregistration_sha256"],
            "predictive_contract_sha256": record["predictive_contract_sha256"],
            "canonical_file_sha256": record["source"]["canonical_file_sha256"],
            "implementation_sha256": record["implementation_sha256"],
        }
    )


# --------------------------------------------------------------------------------------
# Execution.
# --------------------------------------------------------------------------------------


def _outcomes(labels: Sequence[Label]) -> list[Outcome]:
    return [
        Outcome(open_time=label.open_time, r_24h=label.r_24h, direction=label.direction)
        for label in labels
    ]


def _feature_cache(
    source: SettledFundingSource, labels: Sequence[Label]
) -> tuple[dict[int, tuple[float, ...]], dict[str, int]]:
    """Build every funding vector once. Unavailability is typed and counted, never filled."""
    available: dict[int, tuple[float, ...]] = {}
    reasons = dict.fromkeys(UNAVAILABILITY_TAXONOMY, 0)
    for label in labels:
        values, reason = build_funding_features(source, label.open_time)
        if values is None:
            reasons[str(reason)] += 1
            continue
        available[label.open_time] = values
    return available, reasons


def _fold_predictions(
    model_version: str, fold: Fold, cache: Mapping[int, tuple[float, ...]]
) -> tuple[dict[str, Any], list[Prediction], list[Prediction]]:
    """Fit both heads on this fold's source-eligible training portion and predict it."""
    training = [label for label in fold.training if label.open_time in cache]
    if not training:
        raise ExperimentError(f"{fold.name}: no source-eligible training row")
    directional = [label for label in training if label.direction in {UP, DOWN}]
    excluded_neutral = len(training) - len(directional)

    direction_head = fit_direction_head(
        model_version,
        [label.open_time for label in directional],
        [cache[label.open_time] for label in directional],
        [label.direction for label in directional],
    )
    magnitude_head = fit_magnitude_head(
        model_version,
        [cache[label.open_time] for label in training],
        [label.r_24h for label in training],
    )

    available = [label for label in fold.evaluation if label.open_time in cache]
    matrix = [cache[label.open_time] for label in available]
    probabilities = direction_head.probability_up(matrix) if matrix else []
    expected = magnitude_head.expected_return(matrix) if matrix else []
    strengths = magnitude_head.strength(expected) if matrix else []
    by_time = {
        label.open_time: (probability, predicted, strength)
        for label, probability, predicted, strength in zip(
            available, probabilities, expected, strengths, strict=True
        )
    }

    directional_predictions: list[Prediction] = []
    magnitude_predictions: list[Prediction] = []
    for label in fold.evaluation:
        record = by_time.get(label.open_time)
        if record is None:
            directional_predictions.append(Prediction(open_time=label.open_time, direction=ABSTAIN))
            continue
        probability_up, predicted_return, _ = record
        directional_predictions.append(
            Prediction(
                open_time=label.open_time,
                direction=declared_direction(probability_up),
                probability=declared_probability(probability_up),
            )
        )
        magnitude_predictions.append(
            Prediction(
                open_time=label.open_time, direction=ABSTAIN, expected_return=predicted_return
            )
        )

    split = direction_head.split
    fit_record = {
        "fold": fold.name,
        "model_version": model_version,
        "training_labels": len(fold.training),
        "training_rows_source_eligible": len(training),
        "training_rows_source_unavailable": len(fold.training) - len(training),
        "training_rows_neutral_excluded_from_direction": excluded_neutral,
        "direction_base_fit_rows": split.base_fit_rows,
        "direction_calibration_rows": split.calibration_rows,
        "direction_rows_dropped_to_calibration_embargo": split.dropped_to_embargo,
        "calibration_boundary_open_time": split.boundary_open_time,
        "calibration_boundary_index": split.boundary_index,
        "magnitude_training_rows": magnitude_head.training_rows,
        "strength_reference_rows": magnitude_head.training_rows,
        "evaluation_rows_source_eligible": len(available),
        "evaluation_rows_source_unavailable": len(fold.evaluation) - len(available),
        "model_fits": {"direction_base": 1, "direction_calibration": 1, "magnitude": 1},
    }
    return fit_record, directional_predictions, magnitude_predictions


def _actionable(predictions: Sequence[Prediction], labels: Sequence[Label]) -> list[Label]:
    """The candidate-actionable, non-NEUTRAL labels: the matched scoring universe."""
    declared = {item.open_time for item in predictions if item.direction in {UP, DOWN}}
    return [label for label in labels if label.open_time in declared and label.direction != NEUTRAL]


def _matched_controls(
    fold: Fold,
    matched_labels: Sequence[Label],
    base_rate_fit: Any,
    bars_by_open: Mapping[int, Bar],
) -> dict[str, Any]:
    """Score every declared control on the identical matched universe."""
    del fold
    outcomes = _outcomes(matched_labels)
    control = score(
        training_up_base_rate_predictions(base_rate_fit, matched_labels),
        outcomes,
        declares_direction=True,
        declares_probability=True,
        declares_magnitude=False,
    )
    control["fit"] = base_rate_fit.as_record()
    always_up = score(
        always_up_predictions(matched_labels),
        outcomes,
        declares_direction=True,
        declares_probability=False,
        declares_magnitude=False,
    )
    persistence = score(
        previous_24h_sign_predictions(matched_labels, bars_by_open),
        outcomes,
        declares_direction=True,
        declares_probability=False,
        declares_magnitude=False,
    )
    zero_magnitude = score(
        zero_return_magnitude_predictions(matched_labels),
        outcomes,
        declares_direction=False,
        declares_probability=False,
        declares_magnitude=True,
    )
    return {
        MATCHED_CONTROL: control,
        ALWAYS_UP: always_up,
        PREVIOUS_24H_SIGN_PERSISTENCE: persistence,
        ZERO_RETURN_MAGNITUDE: zero_magnitude,
    }


def _paired_records(
    predictions: Sequence[Prediction],
    control: Sequence[Prediction],
    matched_labels: Sequence[Label],
) -> list[PairedRecord]:
    truth = {label.open_time: label for label in matched_labels}
    candidate = {item.open_time: item.direction for item in predictions}
    baseline = {item.open_time: item.direction for item in control}
    records: list[PairedRecord] = []
    for moment in sorted(truth):
        outcome = truth[moment]
        records.append(
            PairedRecord(
                open_time=moment,
                candidate_correct=candidate[moment] == outcome.direction,
                baseline_correct=baseline[moment] == outcome.direction,
            )
        )
    return records


def advancement_gate(
    model_version: str,
    pooled_coverage: float,
    fold_coverage: Mapping[str, float],
    pooled_primary_delta: float,
    interval: Sequence[float],
    pooled_always_up_delta: float,
    fold_primary_deltas: Mapping[str, float],
    candidate_brier: float,
    control_brier: float,
) -> dict[str, Any]:
    """The seven predeclared conditions. All must hold; magnitude never rescues."""
    non_negative = sum(1 for value in fold_primary_deltas.values() if value >= 0.0)
    conditions: dict[str, dict[str, Any]] = {
        GATE_NAMES[0]: {
            "threshold": POOLED_COVERAGE_GATE,
            "observed": pooled_coverage,
            "passed": pooled_coverage >= POOLED_COVERAGE_GATE,
        },
        GATE_NAMES[1]: {
            "threshold": FOLD_COVERAGE_GATE,
            "observed": min(fold_coverage.values()),
            "passed": all(value >= FOLD_COVERAGE_GATE for value in fold_coverage.values()),
        },
        GATE_NAMES[2]: {
            "threshold": MINIMUM_IMPORTANT_EFFECT,
            "observed": pooled_primary_delta,
            "passed": pooled_primary_delta >= MINIMUM_IMPORTANT_EFFECT,
        },
        GATE_NAMES[3]: {
            "threshold": 0.0,
            "observed": float(interval[0]),
            "passed": float(interval[0]) > 0.0,
        },
        GATE_NAMES[4]: {
            "threshold": 0.0,
            "observed": pooled_always_up_delta,
            "passed": pooled_always_up_delta > 0.0,
        },
        GATE_NAMES[5]: {
            "threshold": MINIMUM_NON_NEGATIVE_FOLDS,
            "observed": non_negative,
            "passed": non_negative >= MINIMUM_NON_NEGATIVE_FOLDS,
        },
        GATE_NAMES[6]: {
            "threshold": control_brier,
            "observed": candidate_brier,
            "passed": candidate_brier <= control_brier,
        },
    }
    failed = [name for name, record in conditions.items() if not record["passed"]]
    return {
        "all_must_hold": True,
        "conditions": conditions,
        "failed_conditions": failed,
        "terminal_classification": (
            NO_ADVANCE[model_version] if failed else ADVANCE[model_version]
        ),
        "magnitude_used_to_rescue": False,
    }


def baseline_context(root: Path = ROOT) -> dict[str, Any]:
    """The canonical full-universe baselines from PREDICTIVE-BASELINES-V1, unchanged."""
    report = json.loads(
        (root / "reports/research/PREDICTIVE-BASELINES-V1.json").read_text(encoding="utf-8")
    )
    return {
        "source": "reports/research/PREDICTIVE-BASELINES-V1.json",
        "classification": report["classification"],
        "eligible_decision_timestamps": report["folds"]["eligible_decision_timestamps"],
        "pooled": {
            name: {
                "win_rate": record["pooled"]["win_rate"],
                "coverage": record["pooled"]["coverage"],
            }
            for name, record in report["baselines"].items()
        },
        "reference_bar": report["baselines"][ALWAYS_UP]["pooled"]["win_rate"],
        "note": "SIX_FOLD_FULL_UNIVERSE_NOT_THE_STAGE_2_SOURCE_UNIVERSE",
        "results_changed": False,
    }


def _configuration_result(
    model_version: str,
    folds: Sequence[Fold],
    cache: Mapping[int, tuple[float, ...]],
    base_rate_fits: Mapping[str, Any],
    bars_by_open: Mapping[int, Bar],
) -> dict[str, Any]:
    by_fold: dict[str, Any] = {}
    trials: list[dict[str, Any]] = []
    pooled_directional: list[Prediction] = []
    pooled_magnitude: list[Prediction] = []
    pooled_labels: list[Label] = []
    pooled_magnitude_labels: list[Label] = []
    pooled_matched_labels: list[Label] = []
    pooled_control: list[Prediction] = []
    paired_folds = []
    fold_coverage: dict[str, float] = {}
    fold_primary_deltas: dict[str, float] = {}
    fold_always_up_deltas: dict[str, float] = {}
    fits = {"direction_base": 0, "direction_calibration": 0, "magnitude": 0}

    for fold in folds:
        fit_record, directional, magnitude = _fold_predictions(model_version, fold, cache)
        for key in fits:
            fits[key] += fit_record["model_fits"][key]
        trials.append(fit_record)
        magnitude_times = {item.open_time for item in magnitude}
        magnitude_labels = [
            label for label in fold.evaluation if label.open_time in magnitude_times
        ]
        directional_score = score(
            directional,
            _outcomes(fold.evaluation),
            declares_direction=True,
            declares_probability=True,
            declares_magnitude=False,
        )
        magnitude_score = score(
            magnitude,
            _outcomes(magnitude_labels),
            declares_direction=False,
            declares_probability=False,
            declares_magnitude=True,
        )
        matched_labels = _actionable(directional, fold.evaluation)
        controls = _matched_controls(fold, matched_labels, base_rate_fits[fold.name], bars_by_open)
        control_predictions = training_up_base_rate_predictions(
            base_rate_fits[fold.name], matched_labels
        )
        records = _paired_records(directional, control_predictions, matched_labels)
        paired_folds.append(
            build_paired_fold(fold.name, [label.open_time for label in fold.evaluation], records)
        )
        coverage = directional_score["coverage"]
        candidate_rate = directional_score["win_rate"]
        if coverage is None or candidate_rate is None:
            raise ExperimentError(f"{fold.name}: the fold produced no scorable prediction")
        control_rate = controls[MATCHED_CONTROL]["win_rate"]
        always_up_rate = controls[ALWAYS_UP]["win_rate"]
        fold_coverage[fold.name] = float(coverage)
        fold_primary_deltas[fold.name] = float(candidate_rate) - float(control_rate)
        fold_always_up_deltas[fold.name] = float(candidate_rate) - float(always_up_rate)
        by_fold[fold.name] = {
            "fit": fit_record,
            "directional": directional_score,
            "magnitude": magnitude_score,
            "magnitude_universe": {
                "eligible_decision_timestamps": len(fold.evaluation),
                "source_eligible_rows_scored": len(magnitude_labels),
                "abstained_rows_excluded_and_counted": len(fold.evaluation) - len(magnitude_labels),
            },
            "matched_universe": {
                "records": len(matched_labels),
                "share_of_eligible": len(matched_labels) / len(fold.evaluation),
            },
            "matched_controls": controls,
            "primary_delta": fold_primary_deltas[fold.name],
            "always_up_delta": fold_always_up_deltas[fold.name],
        }
        pooled_directional.extend(directional)
        pooled_magnitude.extend(magnitude)
        pooled_labels.extend(fold.evaluation)
        pooled_magnitude_labels.extend(magnitude_labels)
        pooled_matched_labels.extend(matched_labels)
        pooled_control.extend(control_predictions)

    pooled_directional_score = score(
        pooled_directional,
        _outcomes(pooled_labels),
        declares_direction=True,
        declares_probability=True,
        declares_magnitude=False,
    )
    pooled_magnitude_score = score(
        pooled_magnitude,
        _outcomes(pooled_magnitude_labels),
        declares_direction=False,
        declares_probability=False,
        declares_magnitude=True,
    )
    pooled_outcomes = _outcomes(pooled_matched_labels)
    pooled_controls = {
        MATCHED_CONTROL: score(
            pooled_control,
            pooled_outcomes,
            declares_direction=True,
            declares_probability=True,
            declares_magnitude=False,
        ),
        ALWAYS_UP: score(
            always_up_predictions(pooled_matched_labels),
            pooled_outcomes,
            declares_direction=True,
            declares_probability=False,
            declares_magnitude=False,
        ),
        PREVIOUS_24H_SIGN_PERSISTENCE: score(
            previous_24h_sign_predictions(pooled_matched_labels, bars_by_open),
            pooled_outcomes,
            declares_direction=True,
            declares_probability=False,
            declares_magnitude=False,
        ),
        ZERO_RETURN_MAGNITUDE: score(
            zero_return_magnitude_predictions(pooled_matched_labels),
            pooled_outcomes,
            declares_direction=False,
            declares_probability=False,
            declares_magnitude=True,
        ),
    }
    paired = paired_delta_interval(paired_folds)
    pooled_coverage = float(pooled_directional_score["coverage"])
    candidate_rate = float(pooled_directional_score["win_rate"])
    control_rate = float(pooled_controls[MATCHED_CONTROL]["win_rate"])
    always_up_rate = float(pooled_controls[ALWAYS_UP]["win_rate"])
    candidate_brier = float(pooled_directional_score["brier_score"])
    control_brier = float(pooled_controls[MATCHED_CONTROL]["brier_score"])
    gate = advancement_gate(
        model_version,
        pooled_coverage,
        fold_coverage,
        candidate_rate - control_rate,
        paired["interval"],
        candidate_rate - always_up_rate,
        fold_primary_deltas,
        candidate_brier,
        control_brier,
    )

    return {
        "experiment_id": EXPERIMENT_IDS[model_version],
        "model_version": model_version,
        "model": specification(model_version),
        "model_fits": {**fits, "total": sum(fits.values())},
        "trials": trials,
        "candidate": {
            "pooled_directional": pooled_directional_score,
            "pooled_magnitude": pooled_magnitude_score,
            "pooled_magnitude_universe": {
                "eligible_decision_timestamps": len(pooled_labels),
                "source_eligible_rows_scored": len(pooled_magnitude_labels),
                "abstained_rows_excluded_and_counted": len(pooled_labels)
                - len(pooled_magnitude_labels),
            },
            "by_fold": by_fold,
        },
        "matched_universe": {
            "records": len(pooled_matched_labels),
            "share_of_eligible": len(pooled_matched_labels) / len(pooled_labels),
            "definition": "CANDIDATE_ACTIONABLE_NON_NEUTRAL_TIMESTAMPS",
        },
        "matched_controls": pooled_controls,
        "primary_comparison": {
            "definition": (
                "candidate directional win rate - matched MATCHED_TRAINING_UP_BASE_RATE "
                "win rate on candidate-actionable, non-NEUTRAL timestamps"
            ),
            "matched_control": MATCHED_CONTROL,
            "candidate_win_rate": candidate_rate,
            "matched_control_win_rate": control_rate,
            "pooled_delta": candidate_rate - control_rate,
            "minimum_important_effect": MINIMUM_IMPORTANT_EFFECT,
            "fold_deltas": fold_primary_deltas,
            "fold_coverage": fold_coverage,
            "paired_interval": paired,
        },
        "secondary_comparison": {
            "definition": "candidate directional win rate - matched ALWAYS_UP win rate",
            "role": "ABSOLUTE_REFERENCE",
            "matched_always_up_win_rate": always_up_rate,
            "pooled_delta": candidate_rate - always_up_rate,
            "fold_deltas": fold_always_up_deltas,
            "interval_claimed": False,
        },
        "calibration_comparison": {
            "candidate_brier_score": candidate_brier,
            "matched_control_brier_score": control_brier,
            "candidate_at_most_control": candidate_brier <= control_brier,
        },
        "advancement_gate": gate,
        "terminal_classification": gate["terminal_classification"],
    }


def run_experiment(root: Path = ROOT) -> dict[str, Any]:
    """Execute both frozen configurations once and emit the complete contract report."""
    bars = load_hourly_bars(root)
    bars_by_open = index_bars(bars)
    label_set = build_labels(bars, horizon_hours=HORIZON_HOURS)
    fold_set = build_folds(
        label_set.labels, horizon_hours=HORIZON_HOURS, purge_embargo_hours=PURGE_EMBARGO_HOURS
    )
    assert_no_fold_leak(fold_set)
    folds = [fold for fold in fold_set.folds if fold.name in EVALUATION_FOLDS]
    if [fold.name for fold in folds] != list(EVALUATION_FOLDS):
        raise ExperimentError("the Stage-2 evaluation folds are not the frozen five")
    warmup = next(fold for fold in fold_set.folds if fold.name == WARMUP_FOLD)

    source = load_settled_funding(root)
    cache, unavailability = _feature_cache(source, label_set.labels)

    base_rate_fits: dict[str, Any] = {}
    for fold in folds:
        eligible_training = [label for label in fold.training if label.open_time in cache]
        if not eligible_training:
            raise ExperimentError(f"{fold.name}: the matched control has no training row")
        base_rate_fits[fold.name] = fit_training_up_base_rate(eligible_training)

    configurations = {
        model_version: _configuration_result(
            model_version, folds, cache, base_rate_fits, bars_by_open
        )
        for model_version in CONFIGURATION_ORDER
    }

    advanced = [
        model_version
        for model_version in CONFIGURATION_ORDER
        if not configurations[model_version]["advancement_gate"]["failed_conditions"]
    ]
    family_disposition = FAMILY_SIGNAL if advanced else FAMILY_REJECTED
    eligible_total = sum(len(fold.evaluation) for fold in folds)

    return {
        "version": CHECKPOINT,
        "classification": "PREDICTIVE_EXPERIMENT_RESULT",
        "family": FAMILY,
        "hypothesis_id": HYPOTHESIS_ID,
        "hypothesis_name": HYPOTHESIS_NAME,
        "research_generation": RESEARCH_GENERATION,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "search_plan": SEARCH_PLAN_PATH,
        "admission": ADMISSION_PATH,
        "stage1_disposition": stage1_disposition(),
        "source": source_identity(root),
        "labels": label_set.accounting(),
        "folds": {
            "design": FOLD_DESIGN,
            "random_k_fold": False,
            "purge_embargo_hours": PURGE_EMBARGO_HOURS,
            "evaluation_folds": list(EVALUATION_FOLDS),
            "warmup_only_fold": WARMUP_FOLD,
            "warmup_fold_eligible_labels_excluded": len(warmup.evaluation),
            "eligible_decision_timestamps": eligible_total,
            "canonical_six_fold_eligible_total": fold_set.eligible_total(),
            "recut": False,
        },
        "features": {
            "version": FEATURE_SET_VERSION,
            "count": len(FEATURE_NAMES),
            "ordered_names": list(FEATURE_NAMES),
            "available_vectors": len(cache),
            "unavailable_vectors": sum(unavailability.values()),
            "unavailability_by_reason": unavailability,
            "stage1_internal_price_features_present": False,
        },
        "matched_control_fits": {
            "control": MATCHED_CONTROL,
            "fits": len(base_rate_fits),
            "classification": "COUNTED_TRAINING_BASE_RATE_NOT_A_MODEL_FIT",
            "by_fold": {name: fit.as_record() for name, fit in base_rate_fits.items()},
        },
        "configurations": configurations,
        "baseline_context": baseline_context(root),
        "family_disposition": {
            "family": FAMILY,
            "disposition": family_disposition,
            "advancing_configurations": [ADVANCE[name] for name in advanced],
            "configurations_executed": list(CONFIGURATION_ORDER),
            "post_hoc_winner_selected": False,
            "sealed_eligibility": {
                EXPERIMENT_IDS[name]: (
                    "REQUIRES_RESEARCH_DIRECTOR_REVIEW" if name in advanced else NOT_ELIGIBLE
                )
                for name in CONFIGURATION_ORDER
            },
            "sealed_queried": False,
            "champion_created": False,
            "prospective_observer_created": False,
            "descendant_tuned": False,
        },
        "search_budget": {
            "family": FAMILY,
            "configurations_planned": FAMILY_SIZE,
            "configurations_consumed": FAMILY_SIZE,
            "configurations_remaining": 0,
            "configurations_executed": list(CONFIGURATION_ORDER),
            "result_dependent_early_stop": False,
            "hyperparameter_search": False,
            "threshold_search": False,
            "feature_search": False,
            "result_dependent_forks": 0,
        },
        "scoring": {
            "reliability_bin_edges": list(RELIABILITY_BIN_EDGES),
            "paired_interval": {
                "method": PAIRED_METHOD,
                "block_length_hours": PAIRED_BLOCK_LENGTH_HOURS,
                "replicates": PAIRED_REPLICATES,
                "seed": PAIRED_SEED,
                "alpha": PAIRED_ALPHA,
            },
            "calibration_split_fraction": CALIBRATION_SPLIT_FRACTION,
            "calibration_embargo_hours": CALIBRATION_EMBARGO_HOURS,
        },
        "boundaries": {
            "stage1_rescue_or_redesign": False,
            "canonical_hourly_gap_repair": False,
            "additional_information_family": False,
            "post_cutoff_market_data": False,
            "sealed_queries": 0,
            "champion_created": False,
            "real_money": False,
            "historical_results_changed": False,
            "baselines_v1_results_changed": False,
            "previous_24h_sign_persistence_inverted": False,
            "outer_evaluation_used_in_fitting": False,
            "post_result_tuning": False,
            "post_hoc_winner_selection": False,
        },
    }


__all__ = [
    "ADMISSION_PATH",
    "ADVANCE",
    "CANDIDATE_ALPHA",
    "CHECKPOINT",
    "CONFIGURATION_ORDER",
    "EVALUATION_FOLDS",
    "EXPERIMENT_IDS",
    "FAMILY",
    "FAMILY_REJECTED",
    "FAMILY_SIGNAL",
    "FAMILY_SIZE",
    "GATE_NAMES",
    "HGBR_EXPERIMENT_ID",
    "HYPOTHESIS_ID",
    "IMPLEMENTATION_FILES",
    "LINEAR_EXPERIMENT_ID",
    "MATCHED_CONTROL",
    "MINIMUM_IMPORTANT_EFFECT",
    "NOT_ELIGIBLE",
    "NO_ADVANCE",
    "REPORT_JSON_PATH",
    "REPORT_MARKDOWN_PATH",
    "SEARCH_PLAN_PATH",
    "WARMUP_FOLD",
    "admission",
    "admission_identity",
    "advancement_gate",
    "baseline_context",
    "canonical_bytes",
    "preregistration",
    "preregistration_path",
    "result_path",
    "run_experiment",
    "search_plan",
    "stage1_disposition",
    "trials_path",
]
