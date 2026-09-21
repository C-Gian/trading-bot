"""Frozen records for `PREDICTIVE-STAGE3-MACRO-VINTAGE-V1`.

The source gate failed before any target-bearing fit.  This module therefore freezes the
planned two-configuration family and records the fail-closed admission without exposing an
execution path that could bypass the gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .folds import FOLD_BOUNDARIES, FOLD_DESIGN, PURGE_EMBARGO_HOURS
from .internal_model import CALIBRATION_EMBARGO_HOURS, CALIBRATION_SPLIT_FRACTION
from .internal_structure import ExperimentError, content_hash, payload_hash
from .macro_vintage_audit import (
    AUDIT_PATH,
    BLOCKED,
    FOLD_COVERAGE_GATE,
    MINIMUM_ADMISSIBLE_FOLDS,
    MINIMUM_TRAINING_HISTORY_DAYS,
    POOLED_COVERAGE_GATE,
)
from .macro_vintage_source import (
    CONTRACT_PATH,
    FEATURE_COUNT,
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    MANIFEST_PATH,
    SERIES,
    UNAVAILABILITY_TAXONOMY,
    source_identity,
)
from .paired_inference import PAIRED_BLOCK_LENGTH_HOURS, PAIRED_METHOD, PAIRED_REPLICATES

ROOT = Path(__file__).resolve().parents[3]

CHECKPOINT = "PREDICTIVE-STAGE3-MACRO-VINTAGE-V1"
FAMILY = "PREDICTIVE_STAGE3_MACRO_VINTAGE_FAMILY_V1"
RESEARCH_GENERATION = "PREDICTIVE_RESEARCH_GENERATION_V1"
LINEAR_MODEL_VERSION = "MACRO_VINTAGE_LINEAR_V1"
HGBR_MODEL_VERSION = "MACRO_VINTAGE_HGBR_V1"
CONFIGURATION_ORDER = (LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION)
EXPERIMENT_IDS = {
    LINEAR_MODEL_VERSION: "EXP-PRED-007-MACRO-VINTAGE-LINEAR",
    HGBR_MODEL_VERSION: "EXP-PRED-008-MACRO-VINTAGE-HGBR",
}
HYPOTHESIS_IDS = {
    LINEAR_MODEL_VERSION: "H-PRED-MACRO-001",
    HGBR_MODEL_VERSION: "H-PRED-MACRO-002",
}
SEARCH_PLAN_PATH = "research/protocols/PREDICTIVE-STAGE3-MACRO-VINTAGE-SEARCH-PLAN-V1.json"
ADMISSION_PATH = "reports/validation/PREDICTIVE-STAGE3-MACRO-VINTAGE-V1-ADMISSION.json"
CHECKPOINT_REPORT_PATH = "reports/checkpoints/PREDICTIVE-STAGE3-MACRO-VINTAGE-V1.md"
CREATED_AT = "2026-09-21T00:00:00Z"

FAMILY_SIZE = 2
FAMILYWISE_ALPHA = 0.05
CANDIDATE_ALPHA = 0.025
MINIMUM_IMPORTANT_EFFECT = 0.015
PAIRED_SEED = 20260919

LINEAR_PARAMETERS: dict[str, Any] = {
    "penalty": "l2",
    "C": 1.0,
    "class_weight": None,
    "fit_intercept": True,
    "solver": "lbfgs",
    "max_iter": 2000,
    "tol": 1e-8,
}
HGBR_PARAMETERS: dict[str, Any] = {
    "learning_rate": 0.05,
    "max_iter": 200,
    "max_leaf_nodes": 15,
    "min_samples_leaf": 50,
    "l2_regularization": 1.0,
    "max_bins": 255,
    "early_stopping": False,
    "random_state": 20260919,
}
PLATT_PARAMETERS: dict[str, Any] = {
    "penalty": None,
    "fit_intercept": True,
    "solver": "lbfgs",
    "max_iter": 2000,
    "tol": 1e-8,
}

PRIOR_EXPERIMENT_RESULTS = (
    "research/experiments/EXP-PRED-001-INTERNAL-LINEAR-DUAL-HEAD/result.json",
    "research/experiments/EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD/result.json",
    "research/experiments/EXP-PRED-003-FUNDING-LINEAR-DUAL-HEAD/result.json",
    "research/experiments/EXP-PRED-004-FUNDING-HGBR-DUAL-HEAD/result.json",
    "research/experiments/EXP-PRED-005-OPEN-INTEREST-LINEAR-DUAL-HEAD/result.json",
    "research/experiments/EXP-PRED-006-OPEN-INTEREST-HGBR-DUAL-HEAD/result.json",
    "research/experiments/EXP-PRED-007-CROSS-ASSET-BREADTH-LINEAR/result.json",
    "research/experiments/EXP-PRED-008-CROSS-ASSET-BREADTH-HGBR/result.json",
)

IMPLEMENTATION_FILES = (
    "backend/app/predictive/macro_vintage.py",
    "backend/app/predictive/macro_vintage_audit.py",
    "backend/app/predictive/macro_vintage_source.py",
    "scripts/audit_predictive_macro_vintage.py",
    "scripts/preregister_predictive_macro_vintage.py",
)


def director_decisions() -> dict[str, Any]:
    return {
        "decision_id": "PREDICTIVE_STAGE3_MACRO_VINTAGE_ADMISSION_V1",
        "decided_by": "RESEARCH_DIRECTOR",
        "generation": RESEARCH_GENERATION,
        "generation_continues": True,
        "prior_negative_configurations": 8,
        "prior_results_changed": False,
        "breadth_inversion_or_rescue_authorized": False,
        "basis_tested": False,
        "basis_disposition": "DEFERRED",
        "stage1_substrate_disposition": "DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH",
        "target_or_horizon_changed": False,
        "target": "BTCUSDT_SPOT_24H_TERMINAL_DIRECTION",
        "magnitude_declared": False,
        "magnitude_disposition": "DEFERRED_UNTIL_DIRECTIONAL_ADMISSION",
        "admitted_family": FAMILY,
        "admission_rationale": (
            "Strict-vintage U.S. macro and financial-condition information is orthogonal "
            "to price structure, derivatives carry and positioning, and crypto breadth; "
            "the existing ALFRED foundation is hash-pinned."
        ),
    }


def specification(model_version: str) -> dict[str, Any]:
    if model_version not in EXPERIMENT_IDS:
        raise ExperimentError(f"unknown macro-vintage configuration: {model_version}")
    linear = model_version == LINEAR_MODEL_VERSION
    return {
        "model_version": model_version,
        "direction_estimator": (
            "StandardScaler+LogisticRegression" if linear else "HistGradientBoostingClassifier"
        ),
        "parameters": dict(LINEAR_PARAMETERS if linear else HGBR_PARAMETERS),
        "probability_calibration": "TRAINING_ONLY_PLATT_ON_RAW_DECISION_SCORE",
        "platt_parameters": dict(PLATT_PARAMETERS),
        "calibration_split_fraction": CALIBRATION_SPLIT_FRACTION,
        "calibration_embargo_hours": CALIBRATION_EMBARGO_HOURS,
        "decision_rule": "UP_IF_CALIBRATED_P_UP_GREATER_OR_EQUAL_0_5_ELSE_DOWN_TIES_UP",
        "threshold_search": False,
        "hyperparameter_search": False,
        "magnitude_estimator": None,
    }


def search_plan() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "version": "PREDICTIVE_STAGE3_MACRO_VINTAGE_SEARCH_PLAN_V1",
        "status": "FROZEN_BEFORE_OBSERVATION_SOURCE_BLOCKED_BEFORE_EXECUTION",
        "checkpoint": CHECKPOINT,
        "research_generation": RESEARCH_GENERATION,
        "family": FAMILY,
        "director_decisions": director_decisions(),
        "source": source_identity(ROOT),
        "feature_set": {
            "version": FEATURE_SET_VERSION,
            "count": FEATURE_COUNT,
            "ordered_names": list(FEATURE_NAMES),
            "series": list(SERIES),
        },
        "configurations": [
            {
                "order": index + 1,
                "experiment_id": EXPERIMENT_IDS[model_version],
                "hypothesis_id": HYPOTHESIS_IDS[model_version],
                "specification": specification(model_version),
            }
            for index, model_version in enumerate(CONFIGURATION_ORDER)
        ],
        "family_size": FAMILY_SIZE,
        "multiplicity": {
            "familywise_alpha": FAMILYWISE_ALPHA,
            "correction": "BONFERRONI",
            "per_configuration_alpha": CANDIDATE_ALPHA,
            "interval_mass": 0.975,
        },
        "primary_effect": "CANDIDATE_WIN_RATE_MINUS_MATCHED_TRAINING_UP_BASE_RATE_WIN_RATE",
        "mesi": MINIMUM_IMPORTANT_EFFECT,
        "inference": {
            "method": PAIRED_METHOD,
            "block_length_hours": PAIRED_BLOCK_LENGTH_HOURS,
            "replicates": PAIRED_REPLICATES,
            "seed": PAIRED_SEED,
        },
        "source_gate": {
            "fold_coverage": FOLD_COVERAGE_GATE,
            "minimum_history_days": MINIMUM_TRAINING_HISTORY_DAYS,
            "minimum_admissible_folds": MINIMUM_ADMISSIBLE_FOLDS,
            "pooled_coverage": POOLED_COVERAGE_GATE,
            "failure_classification": BLOCKED,
        },
        "budget": {
            "configurations_reserved": FAMILY_SIZE,
            "configurations_consumed": 0,
            "reason_unconsumed": BLOCKED,
        },
        "forbidden": [
            "SOURCE_GATE_WEAKENING",
            "CURRENT_REVISED_FRED_SUBSTITUTION",
            "POST_2024_VINTAGES",
            "INTERPOLATION_OR_NEAREST_FUTURE_SUBSTITUTION",
            "FEATURE_OR_THRESHOLD_SEARCH",
            "BREADTH_INVERSION_NEGATION_THRESHOLDING_OR_FOLD_TRIMMING",
            "BASIS_OR_STAGE1_SUBSTRATE_RESCUE",
            "TARGET_HORIZON_OR_MAGNITUDE_CHANGE",
            "SEALED_OR_POST_CUTOFF_BTC_ACCESS",
            "REAL_MONEY",
        ],
    }


def preregistration_path(model_version: str) -> str:
    return f"research/experiments/{EXPERIMENT_IDS[model_version]}/preregistration.json"


def preregistration(model_version: str, root: Path = ROOT) -> dict[str, Any]:
    audit = json.loads((root / AUDIT_PATH).read_text(encoding="utf-8"))
    if audit["status"] != BLOCKED:
        raise ExperimentError("this frozen record represents the fail-closed source gate")
    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_EXPERIMENT_PREREGISTRATION_V1",
        "experiment_id": EXPERIMENT_IDS[model_version],
        "experiment_version": 1,
        "created_at_utc": CREATED_AT,
        "status": "PREREGISTERED_NOT_EXECUTED_SOURCE_BLOCKED",
        "checkpoint": CHECKPOINT,
        "research_generation": RESEARCH_GENERATION,
        "family": FAMILY,
        "hypothesis_id": HYPOTHESIS_IDS[model_version],
        "hypothesis": (
            "Strict point-in-time U.S. macro and financial-condition information contains "
            "24h BTCUSDT directional information beyond the training-only UP base rate."
        ),
        "hypothesis_class": "MATERIAL_PREDICTIVE_HYPOTHESIS",
        "source_manifest": MANIFEST_PATH,
        "source_contract": CONTRACT_PATH,
        "source_audit": AUDIT_PATH,
        "source_audit_status": audit["status"],
        "included_folds": [],
        "candidate_folds": [name for name, _, _ in FOLD_BOUNDARIES],
        "evaluation_design": FOLD_DESIGN,
        "purge_embargo_hours": PURGE_EMBARGO_HOURS,
        "features": {
            "version": FEATURE_SET_VERSION,
            "count": FEATURE_COUNT,
            "ordered_names": list(FEATURE_NAMES),
            "unavailability_taxonomy": list(UNAVAILABILITY_TAXONOMY),
        },
        "model": specification(model_version),
        "controls": {
            "primary": "TRAINING_UP_BASE_RATE",
            "absolute_reference": "ALWAYS_UP",
            "descriptive": "PREVIOUS_24H_SIGN_PERSISTENCE_NEVER_INVERTED",
        },
        "primary_effect": {
            "definition": "CANDIDATE_WIN_RATE_MINUS_MATCHED_TRAINING_UP_BASE_RATE_WIN_RATE",
            "mesi": MINIMUM_IMPORTANT_EFFECT,
        },
        "inference": search_plan()["inference"],
        "multiplicity": search_plan()["multiplicity"],
        "advancement_gate": {
            "conditions": 7,
            "all_must_hold": True,
            "not_evaluated_reason": BLOCKED,
        },
        "model_fits": 0,
        "outer_predictions": 0,
        "configuration_consumed": False,
        "sealed_queries": 0,
        "champion_created": False,
        "real_money": False,
    }


def admission(root: Path = ROOT) -> dict[str, Any]:
    plan_path = root / SEARCH_PLAN_PATH
    audit_path = root / AUDIT_PATH
    if json.loads(plan_path.read_text(encoding="utf-8")) != search_plan():
        raise ExperimentError("macro-vintage search plan drifted")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit["status"] != BLOCKED or audit["target_bearing_model_fitted"]:
        raise ExperimentError("macro-vintage source-block identity changed")
    prereg_hashes: dict[str, str] = {}
    for model_version in CONFIGURATION_ORDER:
        path = root / preregistration_path(model_version)
        if json.loads(path.read_text(encoding="utf-8")) != preregistration(model_version, root):
            raise ExperimentError("macro-vintage preregistration drifted")
        prereg_hashes[EXPERIMENT_IDS[model_version]] = content_hash(path)
    prior = {path: content_hash(root / path) for path in PRIOR_EXPERIMENT_RESULTS}
    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_PRE_EXECUTION_ADMISSION_V1",
        "checkpoint": CHECKPOINT,
        "family": FAMILY,
        "status": BLOCKED,
        "execution_authorized": False,
        "search_plan": SEARCH_PLAN_PATH,
        "search_plan_sha256": content_hash(plan_path),
        "source_audit": AUDIT_PATH,
        "source_audit_sha256": content_hash(audit_path),
        "source": source_identity(root),
        "preregistration_sha256": prereg_hashes,
        "implementation_sha256": {path: content_hash(root / path) for path in IMPLEMENTATION_FILES},
        "prior_experiment_result_sha256": prior,
        "included_folds": [],
        "model_fits_executed": 0,
        "outer_predictions_observed": 0,
        "configurations_reserved": FAMILY_SIZE,
        "configurations_consumed": 0,
        "sealed_queries": 0,
        "champion_status": "NONE",
        "real_money": False,
    }


def admission_identity(root: Path = ROOT) -> str:
    record = admission(root)
    return payload_hash(
        {
            "search_plan_sha256": record["search_plan_sha256"],
            "source_audit_sha256": record["source_audit_sha256"],
            "preregistration_sha256": record["preregistration_sha256"],
            "implementation_sha256": record["implementation_sha256"],
            "prior_experiment_result_sha256": record["prior_experiment_result_sha256"],
        }
    )


__all__ = [
    "ADMISSION_PATH",
    "CHECKPOINT",
    "CHECKPOINT_REPORT_PATH",
    "CONFIGURATION_ORDER",
    "EXPERIMENT_IDS",
    "FAMILY",
    "FAMILY_SIZE",
    "HGBR_MODEL_VERSION",
    "HYPOTHESIS_IDS",
    "IMPLEMENTATION_FILES",
    "LINEAR_MODEL_VERSION",
    "PAIRED_SEED",
    "PRIOR_EXPERIMENT_RESULTS",
    "SEARCH_PLAN_PATH",
    "admission",
    "admission_identity",
    "director_decisions",
    "preregistration",
    "preregistration_path",
    "search_plan",
    "specification",
]
