"""First Generation V2 family: frozen deterministic UTC calendar prediction.

This module owns preregistration, admission hashing and execution for exactly two declared
configurations.  The outer fold truth is unavailable to fitting, calibration, feature
construction and action selection; it enters only the frozen selective-LONG scorer.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import DOWN, HORIZON_HOURS, NEUTRAL, UP
from .calendar_features import (
    FEATURE_COUNT,
    FEATURE_SET_VERSION,
    calendar_feature_vector_from_epoch,
    feature_contract,
)
from .calendar_model import (
    HGBR_MODEL_VERSION,
    INFERENCE_SEED,
    LINEAR_MODEL_VERSION,
    fit_probability_head,
    model_specification,
)
from .folds import (
    FOLD_BOUNDARIES,
    FOLD_DESIGN,
    PURGE_EMBARGO_HOURS,
    Fold,
    assert_no_boundary_leak,
    build_folds,
)
from .labels import Bar, Label, build_labels, load_hourly_bars
from .selective_long import (
    ACTION_THRESHOLD,
    EVALUATION_CONTRACT,
    MAGNITUDE_STATUS,
    SELECTIVE_BLOCK_LENGTH_HOURS,
    SELECTIVE_FAMILYWISE_ALPHA,
    SELECTIVE_REPLICATES,
    SelectiveRecord,
    advancement_gate,
    build_selective_fold,
    enrichment_interval,
    frozen_semantics,
    pooled_summary,
)

ROOT = Path(__file__).resolve().parents[3]

CHECKPOINT = "PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1"
FAMILY = "PREDICTIVE_V2_DETERMINISTIC_CALENDAR_FAMILY_V1"
GENERATION = "PREDICTIVE_RESEARCH_GENERATION_V2"
SOURCE_ROADMAP_STAGE = "STAGE_3_CALENDAR_AND_CYCLE"
CREATED_AT = "2026-09-21T00:00:00Z"
FAMILY_SIZE = 2
FAMILYWISE_ALPHA = SELECTIVE_FAMILYWISE_ALPHA
PER_CONFIGURATION_ALPHA = FAMILYWISE_ALPHA / FAMILY_SIZE
INTERVAL_MASS = 1.0 - PER_CONFIGURATION_ALPHA

CONFIGURATION_ORDER = (LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION)
EXPERIMENT_IDS = {
    LINEAR_MODEL_VERSION: "EXP-PRED-V2-001-CALENDAR-LINEAR",
    HGBR_MODEL_VERSION: "EXP-PRED-V2-002-CALENDAR-HGBR",
}
HYPOTHESIS_IDS = {
    LINEAR_MODEL_VERSION: "H-PRED-V2-CALENDAR-001",
    HGBR_MODEL_VERSION: "H-PRED-V2-CALENDAR-002",
}
TERMINAL_CLASSIFICATIONS = {
    LINEAR_MODEL_VERSION: (
        "ADVANCE_V2_CALENDAR_LINEAR_V1",
        "NO_ADVANCE_V2_CALENDAR_LINEAR_V1",
    ),
    HGBR_MODEL_VERSION: (
        "ADVANCE_V2_CALENDAR_HGBR_V1",
        "NO_ADVANCE_V2_CALENDAR_HGBR_V1",
    ),
}

SEARCH_PLAN_PATH = "research/protocols/PREDICTIVE-V2-DETERMINISTIC-CALENDAR-SEARCH-PLAN-V1.json"
ADMISSION_PATH = "reports/validation/PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1-ADMISSION.json"
FEATURE_PROOF_PATH = (
    "reports/validation/PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1-FEATURE-PROOFS.json"
)
REPORT_JSON_PATH = "reports/research/PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1.json"
REPORT_MARKDOWN_PATH = "reports/research/PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1.md"
FEATURE_CONTRACT_PATH = "docs/contracts/PREDICTIVE_V2_DETERMINISTIC_CALENDAR_FEATURES_V1.md"
DECISION_RECORD_PATH = "decisions/ADR-0029-PREDICTIVE-V2-DETERMINISTIC-CALENDAR.md"

PREREGISTRATION_PATHS = {
    model: f"research/experiments/{experiment}/preregistration.json"
    for model, experiment in EXPERIMENT_IDS.items()
}
RESULT_PATHS = {
    model: f"research/experiments/{experiment}/result.json"
    for model, experiment in EXPERIMENT_IDS.items()
}
TRIAL_PATHS = {
    model: f"research/experiments/{experiment}/trials.json"
    for model, experiment in EXPERIMENT_IDS.items()
}

V1_RESULT_PATHS = tuple(
    f"research/experiments/{experiment}/result.json"
    for experiment in (
        "EXP-PRED-001-INTERNAL-LINEAR-DUAL-HEAD",
        "EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD",
        "EXP-PRED-003-FUNDING-LINEAR-DUAL-HEAD",
        "EXP-PRED-004-FUNDING-HGBR-DUAL-HEAD",
        "EXP-PRED-005-OPEN-INTEREST-LINEAR-DUAL-HEAD",
        "EXP-PRED-006-OPEN-INTEREST-HGBR-DUAL-HEAD",
        "EXP-PRED-007-CROSS-ASSET-BREADTH-LINEAR",
        "EXP-PRED-008-CROSS-ASSET-BREADTH-HGBR",
        "EXP-PRED-009-MACRO-RELEASE-STATE-LINEAR",
        "EXP-PRED-010-MACRO-RELEASE-STATE-HGBR",
    )
)
MACRO_SOURCE_BLOCK_PATHS = (
    "research/protocols/PREDICTIVE-STAGE3-MACRO-VINTAGE-SEARCH-PLAN-V1.json",
    "research/experiments/EXP-PRED-007-MACRO-VINTAGE-LINEAR/preregistration.json",
    "research/experiments/EXP-PRED-008-MACRO-VINTAGE-HGBR/preregistration.json",
    "reports/validation/PREDICTIVE-STAGE3-MACRO-VINTAGE-V1-ADMISSION.json",
    "reports/validation/PREDICTIVE-STAGE3-MACRO-VINTAGE-V1-SOURCE-AUDIT.json",
    "reports/checkpoints/PREDICTIVE-STAGE3-MACRO-VINTAGE-V1.md",
)
MACRO_RESIDUAL_PATH = (
    "reports/validation/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1-RESIDUAL-SOURCE-FINDING.json"
)

IMPLEMENTATION_FILES = (
    "backend/app/predictive/calendar_features.py",
    "backend/app/predictive/calendar_model.py",
    "backend/app/predictive/calendar.py",
    "backend/app/predictive/calendar_report.py",
    "backend/app/predictive/selective_long.py",
    "scripts/preregister_predictive_calendar.py",
    "scripts/run_predictive_calendar.py",
    "scripts/audit_predictive_calendar_features.py",
)
PROOF_TEST_FILES = ("backend/tests/test_predictive_calendar.py",)


class CalendarExperimentError(RuntimeError):
    """The frozen family cannot be admitted or executed as declared."""


def content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def payload_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _hash_paths(root: Path, paths: Sequence[str]) -> dict[str, str]:
    missing = [path for path in paths if not (root / path).is_file()]
    if missing:
        raise CalendarExperimentError(f"missing frozen files: {missing}")
    return {path: content_hash(root / path) for path in paths}


def search_plan() -> dict[str, Any]:
    return {
        "version": "PREDICTIVE_V2_DETERMINISTIC_CALENDAR_SEARCH_PLAN_V1",
        "status": "FROZEN_BEFORE_FIRST_OUTER_PREDICTION",
        "created_at": CREATED_AT,
        "generation": GENERATION,
        "family": FAMILY,
        "family_size": FAMILY_SIZE,
        "configuration_order": list(CONFIGURATION_ORDER),
        "experiment_ids": dict(EXPERIMENT_IDS),
        "hypothesis_ids": dict(HYPOTHESIS_IDS),
        "feature_set": feature_contract(),
        "models": {model: model_specification(model) for model in CONFIGURATION_ORDER},
        "target": frozen_semantics()["prediction_target"],
        "folds": {
            "design": FOLD_DESIGN,
            "included": [name for name, _, _ in FOLD_BOUNDARIES],
            "purge_embargo_hours": PURGE_EMBARGO_HOURS,
            "calibration_split": "CHRONOLOGICAL_80_PERCENT_BASE_20_PERCENT_CALIBRATION",
            "calibration_embargo_hours": 48,
            "random_k_fold": False,
        },
        "action_threshold": ACTION_THRESHOLD,
        "threshold_search": False,
        "feature_search": False,
        "hyperparameter_search": False,
        "magnitude_estimator": None,
        "magnitude_status": MAGNITUDE_STATUS,
        "controls": {
            "primary": "FULL_FOLD_UP_RATE",
            "secondary": [
                "FEATURE_VALID_FOLD_UP_RATE",
                "TRAINING_UP_BASE_RATE",
                "ALWAYS_UP",
                "PREVIOUS_24H_SIGN_PERSISTENCE_DESCRIPTIVE_ONLY_NEVER_INVERTED",
            ],
            "primary_visible_to_fitting_calibration_or_selection": False,
        },
        "inference": {
            "method": "FOLD_STRATIFIED_MOVING_BLOCK_BOOTSTRAP_PAIRED_ENRICHMENT",
            "block_length_hours": SELECTIVE_BLOCK_LENGTH_HOURS,
            "replicates": SELECTIVE_REPLICATES,
            "seed": INFERENCE_SEED,
            "familywise_alpha": FAMILYWISE_ALPHA,
            "per_configuration_alpha": PER_CONFIGURATION_ALPHA,
            "interval_mass": INTERVAL_MASS,
            "multiplicity_correction": "BONFERRONI_OVER_TWO_CONFIGURATIONS",
            "blocks_cross_fold_boundaries": False,
        },
        "advancement": frozen_semantics()["thresholds"],
        "all_ten_conditions_must_hold": True,
        "execution_rule": "EXECUTE_BOTH_UNLESS_INTEGRITY_OR_SOFTWARE_DEFECT_BLOCKS_THE_FAMILY",
        "search_budget": {
            "configurations_reserved": FAMILY_SIZE,
            "configurations_planned": FAMILY_SIZE,
            "result_dependent_forks": 0,
        },
        "boundaries": {
            "v1_results_rescored_or_used_for_family_selection": False,
            "old_cycle_or_cross_section_result_imported_as_evidence": False,
            "ciclica_evoluta_or_analisi_evoluta_claim": False,
            "post_cutoff_or_sealed_market_data": False,
            "short": False,
            "champion": False,
            "real_money": False,
        },
    }


def preregistration(model_version: str) -> dict[str, Any]:
    if model_version not in CONFIGURATION_ORDER:
        raise CalendarExperimentError(f"unknown configuration: {model_version}")
    advance, no_advance = TERMINAL_CLASSIFICATIONS[model_version]
    return {
        "version": f"{model_version}_PREREGISTRATION_V1",
        "status": "PREREGISTERED_BEFORE_FIRST_OUTER_PREDICTION",
        "created_at": CREATED_AT,
        "experiment_id": EXPERIMENT_IDS[model_version],
        "hypothesis_id": HYPOTHESIS_IDS[model_version],
        "hypothesis": (
            "DETERMINISTIC_UTC_CALENDAR_STATE_IDENTIFIES_SELECTIVE_LONG_OPPORTUNITIES_"
            "WITH_WIN_RATE_AT_LEAST_0_60_AND_ENRICHMENT_AT_LEAST_0_05_OVER_FULL_FOLD_UP_RATE"
        ),
        "generation": GENERATION,
        "family": FAMILY,
        "family_size": FAMILY_SIZE,
        "configuration": model_specification(model_version),
        "feature_set": feature_contract(),
        "primary_metric": "SELECTIVE_LONG_WIN_RATE_MINUS_FULL_FOLD_UP_RATE",
        "minimum_important_effect": 0.05,
        "evaluation_design": search_plan()["folds"],
        "action_rule": "LONG_IFF_CALIBRATED_P_UP_AT_LEAST_0_60_ELSE_NO_TRADE",
        "action_threshold": ACTION_THRESHOLD,
        "inference": search_plan()["inference"],
        "advancement": search_plan()["advancement"],
        "all_ten_conditions_must_hold": True,
        "pass_classification": advance,
        "fail_classification": no_advance,
        "sealed_eligibility_if_pass": "ELIGIBLE_FOR_RESEARCH_DIRECTOR_SEALED_REVIEW",
        "sealed_query_authorized": False,
        "trial_budget": 1,
        "model_fit_budget": {"outer_folds": 6, "base_classifier": 6, "platt_calibrator": 6},
        "parameter_search": False,
        "threshold_search": False,
        "feature_search": False,
        "post_result_tuning": False,
        "magnitude_declared": False,
        "magnitude_status": MAGNITUDE_STATUS,
        "real_money": False,
    }


def admission(root: Path = ROOT) -> dict[str, Any]:
    design_paths = (
        SEARCH_PLAN_PATH,
        FEATURE_CONTRACT_PATH,
        DECISION_RECORD_PATH,
        FEATURE_PROOF_PATH,
        *(PREREGISTRATION_PATHS[model] for model in CONFIGURATION_ORDER),
    )
    v1_results = _hash_paths(root, V1_RESULT_PATHS)
    macro_source_block = _hash_paths(root, MACRO_SOURCE_BLOCK_PATHS)
    macro_residual = _hash_paths(root, (MACRO_RESIDUAL_PATH,))
    return {
        "version": "PREDICTIVE_V2_DETERMINISTIC_CALENDAR_ADMISSION_V1",
        "status": "FROZEN_BEFORE_FIRST_OUTER_PREDICTION",
        "created_at": CREATED_AT,
        "checkpoint": CHECKPOINT,
        "generation": GENERATION,
        "family": FAMILY,
        "feature_set": FEATURE_SET_VERSION,
        "feature_count": FEATURE_COUNT,
        "action_threshold": ACTION_THRESHOLD,
        "advancement_condition_count": 10,
        "primary_control": "FULL_FOLD_UP_RATE",
        "magnitude_status": MAGNITUDE_STATUS,
        "family_size": FAMILY_SIZE,
        "inference_seed": INFERENCE_SEED,
        "design_sha256": _hash_paths(root, design_paths),
        "implementation_sha256": _hash_paths(root, IMPLEMENTATION_FILES),
        "proof_tests_sha256": _hash_paths(root, PROOF_TEST_FILES),
        "v1_result_sha256": v1_results,
        "v1_result_count": len(v1_results),
        "macro_source_block_sha256": macro_source_block,
        "macro_residual_sha256": macro_residual,
        "generation_v1_disposition": "CLOSED_NO_DIRECTIONAL_ADMISSION_NO_SEALED",
        "v1_scores_or_tails_used": False,
        "cross_asset_inversion_forbidden": True,
        "stage1_substrate_debt": "DEFERRED",
        "basis": "DEFERRED",
        "macro_source_redesign_budget": "EXHAUSTED",
        "sealed_queries": 0,
        "champion": "NONE",
        "real_money": False,
    }


def admission_identity(root: Path = ROOT) -> str:
    return payload_hash(admission(root))


def _training_base_rate(labels: Sequence[Label]) -> tuple[float, dict[str, int]]:
    directional = [label for label in labels if label.direction in {UP, DOWN}]
    if not directional:
        raise CalendarExperimentError("a fold has no directional training label")
    up = sum(label.direction == UP for label in directional)
    down = len(directional) - up
    if up == 0 or down == 0:
        raise CalendarExperimentError("a fold training universe lacks both directional classes")
    return up / len(directional), {
        "training_labels": len(labels),
        "training_directional_labels": len(directional),
        "training_up_labels": up,
        "training_down_labels": down,
        "training_neutral_labels_excluded": len(labels) - len(directional),
    }


def _fit_fold(
    fold: Fold,
    model_version: str,
    feature_cache: Mapping[int, tuple[float, ...]],
) -> tuple[dict[str, Any], Any, float]:
    directional = [label for label in fold.training if label.direction in {UP, DOWN}]
    if len(directional) != sum(
        label.direction in {UP, DOWN, NEUTRAL} for label in fold.training
    ) - sum(label.direction == NEUTRAL for label in fold.training):
        raise CalendarExperimentError(f"{fold.name}: unknown direction in training labels")
    training_p_up, base_accounting = _training_base_rate(fold.training)
    head = fit_probability_head(
        model_version,
        [label.open_time for label in directional],
        [feature_cache[label.open_time] for label in directional],
        [label.direction for label in directional],
    )
    split = head.split
    fit_record = {
        "fold": fold.name,
        "model_version": model_version,
        **base_accounting,
        "training_rows_feature_valid": len(fold.training),
        "training_rows_feature_invalid": 0,
        "direction_base_fit_rows": split.base_fit_rows,
        "direction_calibration_rows": split.calibration_rows,
        "direction_rows_dropped_to_calibration_embargo": split.dropped_to_embargo,
        "calibration_boundary_open_time": split.boundary_open_time,
        "calibration_boundary_index": split.boundary_index,
        "evaluation_rows_feature_valid": len(fold.evaluation),
        "evaluation_rows_feature_invalid": 0,
        "training_up_base_rate": training_p_up,
        "model_fits": {"base_classifier": 1, "platt_calibrator": 1, "total": 2},
    }
    return fit_record, head, training_p_up


def _execute_configuration(
    model_version: str,
    folds: Sequence[Fold],
    feature_cache: Mapping[int, tuple[float, ...]],
    label_accounting: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    selective_folds = []
    training_rates: dict[str, float] = {}
    trials: list[dict[str, Any]] = []
    for fold in folds:
        fit_record, head, training_p_up = _fit_fold(fold, model_version, feature_cache)
        probabilities = head.probability_up(
            [feature_cache[label.open_time] for label in fold.evaluation]
        )
        records = [
            SelectiveRecord(
                open_time=label.open_time,
                truth=label.direction,
                p_up=probability,
            )
            for label, probability in zip(fold.evaluation, probabilities, strict=True)
        ]
        selective_folds.append(
            build_selective_fold(
                fold.name,
                [label.open_time for label in fold.evaluation],
                records,
            )
        )
        training_rates[fold.name] = training_p_up
        trials.append(fit_record)

    summary = pooled_summary(selective_folds, training_rates)
    interval = enrichment_interval(
        selective_folds,
        seed=INFERENCE_SEED,
        alpha=PER_CONFIGURATION_ALPHA,
        block_length=SELECTIVE_BLOCK_LENGTH_HOURS,
        replicates=SELECTIVE_REPLICATES,
    )
    gate = advancement_gate(summary, interval)
    advance, no_advance = TERMINAL_CLASSIFICATIONS[model_version]
    terminal = advance if gate["advances"] else no_advance
    sealed = (
        "ELIGIBLE_FOR_RESEARCH_DIRECTOR_SEALED_REVIEW"
        if gate["advances"]
        else "NOT_ELIGIBLE_REJECTED_DEVELOPMENT"
    )
    result = {
        "version": f"{model_version}_RESULT_V1",
        "classification": "PREDICTIVE_V2_SELECTIVE_LONG_EXPERIMENT_RESULT",
        "checkpoint": CHECKPOINT,
        "experiment_id": EXPERIMENT_IDS[model_version],
        "hypothesis_id": HYPOTHESIS_IDS[model_version],
        "model_version": model_version,
        "research_generation": GENERATION,
        "family": FAMILY,
        "evaluation_contract": EVALUATION_CONTRACT,
        "search_plan": SEARCH_PLAN_PATH,
        "preregistration": PREREGISTRATION_PATHS[model_version],
        "admission": ADMISSION_PATH,
        "feature_contract": FEATURE_CONTRACT_PATH,
        "labels": dict(label_accounting),
        "folds": {
            "design": FOLD_DESIGN,
            "included_folds": [fold.name for fold in folds],
            "included_fold_count": len(folds),
            "purge_embargo_hours": PURGE_EMBARGO_HOURS,
            "random_k_fold": False,
            "recut": False,
        },
        "features": {
            **feature_contract(),
            "validity": 1.0,
            "eligible_vectors": sum(len(fold.evaluation) for fold in folds),
            "invalid_vectors": 0,
            "causality_proofs": "PASS",
        },
        "model": model_specification(model_version),
        "model_fit_accounting": {
            "base_classifier": len(folds),
            "platt_calibrator": len(folds),
            "total": 2 * len(folds),
            "training_base_rate_calculations": len(folds),
            "hyperparameter_fits": 0,
        },
        "candidate": summary,
        "primary_inference": interval,
        "advancement_gate": gate,
        "terminal_classification": terminal,
        "sealed_eligibility": sealed,
        "search_budget": {
            "family_size": FAMILY_SIZE,
            "configuration_trial_budget": 1,
            "configuration_consumed": True,
            "hyperparameter_search": False,
            "threshold_search": False,
            "feature_search": False,
            "result_dependent_forks": 0,
        },
        "integrity": {
            "admission_identity_sha256": None,
            "v1_results_modified": False,
            "v1_scores_or_tails_used": False,
            "full_fold_control_visible_to_fitting_or_calibration": False,
            "old_cycle_or_cross_section_result_imported_as_evidence": False,
        },
        "boundaries": {
            "magnitude_declared": False,
            "magnitude_status": MAGNITUDE_STATUS,
            "short_authorized": False,
            "post_cutoff_market_data": False,
            "sealed_queries": 0,
            "champion_created": False,
            "real_money": False,
            "post_result_tuning": False,
        },
    }
    return result, trials


def run_family(
    root: Path = ROOT, bars: Sequence[Bar] | None = None
) -> dict[str, tuple[dict[str, Any], list[dict[str, Any]]]]:
    """Execute both configurations, regardless of the first outcome."""
    resolved = tuple(bars) if bars is not None else load_hourly_bars(root)
    label_set = build_labels(resolved, horizon_hours=HORIZON_HOURS)
    fold_set = build_folds(
        label_set.labels,
        horizon_hours=HORIZON_HOURS,
        purge_embargo_hours=PURGE_EMBARGO_HOURS,
    )
    assert_no_boundary_leak(fold_set)
    if [fold.name for fold in fold_set.folds] != [name for name, _, _ in FOLD_BOUNDARIES]:
        raise CalendarExperimentError("the complete frozen six-fold set was not built")
    feature_cache = {
        label.open_time: calendar_feature_vector_from_epoch(label.open_time)
        for label in label_set.labels
    }
    if len(feature_cache) != len(label_set.labels):
        raise CalendarExperimentError("calendar feature validity is not 1.0")
    for vector in feature_cache.values():
        if len(vector) != FEATURE_COUNT:
            raise CalendarExperimentError("a calendar feature vector has the wrong width")
    identity = admission_identity(root)
    outputs: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    for model_version in CONFIGURATION_ORDER:
        result, trials = _execute_configuration(
            model_version,
            fold_set.folds,
            feature_cache,
            label_set.accounting(),
        )
        result["integrity"]["admission_identity_sha256"] = identity
        outputs[model_version] = result, trials
    return outputs


def family_summary(results: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if tuple(results) != CONFIGURATION_ORDER:
        raise CalendarExperimentError("the family result does not contain both configurations")
    advancing = [
        model for model in CONFIGURATION_ORDER if results[model]["advancement_gate"]["advances"]
    ]
    return {
        "version": CHECKPOINT,
        "classification": "PREDICTIVE_V2_FAMILY_RESULT",
        "family": FAMILY,
        "generation": GENERATION,
        "configuration_order": list(CONFIGURATION_ORDER),
        "experiment_ids": dict(EXPERIMENT_IDS),
        "feature_set": feature_contract(),
        "causality_proofs": "PASS",
        "folds": [name for name, _, _ in FOLD_BOUNDARIES],
        "configuration_results": {
            model: {
                "experiment_id": results[model]["experiment_id"],
                "result": RESULT_PATHS[model],
                "trials": TRIAL_PATHS[model],
                "model_fits": results[model]["model_fit_accounting"],
                "candidate": results[model]["candidate"],
                "primary_inference": results[model]["primary_inference"],
                "advancement_gate": results[model]["advancement_gate"],
                "terminal_classification": results[model]["terminal_classification"],
                "sealed_eligibility": results[model]["sealed_eligibility"],
            }
            for model in CONFIGURATION_ORDER
        },
        "advancing_configurations": advancing,
        "family_disposition": (
            "ADVANCE_TO_RESEARCH_DIRECTOR_SEALED_REVIEW"
            if advancing
            else "REJECTED_DEVELOPMENT_NO_SEALED"
        ),
        "search_budget": {
            "configurations_planned": FAMILY_SIZE,
            "configurations_consumed": FAMILY_SIZE,
            "configurations_remaining": 0,
            "result_dependent_forks": 0,
        },
        "model_fits": sum(
            results[model]["model_fit_accounting"]["total"] for model in CONFIGURATION_ORDER
        ),
        "outer_predictions": sum(
            results[model]["candidate"]["feature_valid_timestamps"] for model in CONFIGURATION_ORDER
        ),
        "admission_identity_sha256": results[LINEAR_MODEL_VERSION]["integrity"][
            "admission_identity_sha256"
        ],
        "v1_integrity": "PASS_BYTE_IDENTICAL",
        "magnitude_status": MAGNITUDE_STATUS,
        "sealed_queries": 0,
        "champion": "NONE",
        "real_money": False,
    }


__all__ = [
    "ADMISSION_PATH",
    "CHECKPOINT",
    "CONFIGURATION_ORDER",
    "DECISION_RECORD_PATH",
    "EXPERIMENT_IDS",
    "FAMILY",
    "FAMILY_SIZE",
    "FEATURE_CONTRACT_PATH",
    "FEATURE_PROOF_PATH",
    "GENERATION",
    "HYPOTHESIS_IDS",
    "INTERVAL_MASS",
    "MACRO_RESIDUAL_PATH",
    "MACRO_SOURCE_BLOCK_PATHS",
    "PER_CONFIGURATION_ALPHA",
    "PREREGISTRATION_PATHS",
    "REPORT_JSON_PATH",
    "REPORT_MARKDOWN_PATH",
    "RESULT_PATHS",
    "SEARCH_PLAN_PATH",
    "TERMINAL_CLASSIFICATIONS",
    "TRIAL_PATHS",
    "V1_RESULT_PATHS",
    "CalendarExperimentError",
    "admission",
    "admission_identity",
    "canonical_bytes",
    "content_hash",
    "family_summary",
    "payload_hash",
    "preregistration",
    "run_family",
    "search_plan",
]
