"""`PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1` — strict-vintage U.S. macro release state.

Two preregistered configurations, `MACRO_RELEASE_STATE_LINEAR_V1` and
`MACRO_RELEASE_STATE_HGBR_V1`, both executed in this work package regardless of the first
result, on the thirteen frozen macro quantities of `PREDICTIVE_MACRO_VINTAGE_FEATURES_V2`.

This is the one prospective source-semantics remediation authorized for the ALFRED macro
family inside `PREDICTIVE_RESEARCH_GENERATION_V1`. The predecessor,
`PREDICTIVE-STAGE3-MACRO-VINTAGE-V1`, remains immutable and source-blocked; nothing here
reclassifies it, and its records are hash-pinned by the admission artifact below.

Direction and calibrated probability only. Magnitude is deliberately not declared: no source
family has earned directional admission yet.

The target, labels, folds, scorer, reliability bins, controls and dependence-aware bootstrap
are those of `PREDICTIVE_EVALUATION_CONTRACT_V1` Amendment A1 and `PREDICTIVE-BASELINES-V1`.
The evaluation fold set is not chosen here: it is whatever the pre-result source audit
declared source-admissible from source availability alone.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import ABSTAIN, DOWN, HORIZON_HOURS, NEUTRAL, UP
from .baselines import (
    ALWAYS_UP,
    PREVIOUS_24H_SIGN_PERSISTENCE,
    TRAINING_UP_BASE_RATE,
    always_up_predictions,
    fit_training_up_base_rate,
    previous_24h_sign_predictions,
    training_up_base_rate_predictions,
)
from .evaluation import RELIABILITY_BIN_EDGES, Outcome, Prediction, score
from .folds import FOLD_BOUNDARIES, FOLD_DESIGN, PURGE_EMBARGO_HOURS, Fold, build_folds
from .folds import assert_no_boundary_leak as assert_no_fold_leak
from .internal_model import (
    CALIBRATION_EMBARGO_HOURS,
    CALIBRATION_SPLIT_FRACTION,
    declared_direction,
    declared_probability,
)
from .internal_structure import ExperimentError, canonical_bytes, content_hash, payload_hash
from .labels import Bar, Label, build_labels, index_bars, load_hourly_bars
from .macro_release_state_audit import (
    AUDIT_PATH,
    COVERAGE_BLOCKED,
    INTEGRITY_BLOCKED,
    MINIMUM_ADMISSIBLE_FOLDS,
    MINIMUM_TRAINING_HISTORY_DAYS,
    PARKED,
    PASS,
    SEMANTICS_BLOCKED,
)
from .macro_release_state_audit import (
    FOLD_COVERAGE_GATE as SOURCE_FOLD_COVERAGE_GATE,
)
from .macro_release_state_audit import (
    POOLED_COVERAGE_GATE as SOURCE_POOLED_COVERAGE_GATE,
)
from .macro_release_state_source import (
    CONTRACT_PATH,
    EXACT_MONTH_ANCHORS,
    FEATURE_COUNT,
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    HISTORICAL_ANCHORS,
    MANIFEST_PATH,
    PREDECESSOR_CONTRACT_PATH,
    PREDECESSOR_FEATURE_SET_VERSION,
    RELEASE_STATE_VERSION,
    SERIES,
    SOURCE_CADENCE_LIMIT_DAYS,
    UNAVAILABILITY_TAXONOMY,
    MacroReleaseStateSource,
    availability_map,
    load_release_state_source,
    source_identity,
)
from .paired_inference import (
    PAIRED_ALPHA,
    PAIRED_BLOCK_LENGTH_HOURS,
    PAIRED_METHOD,
    PAIRED_REPLICATES,
    REPLICATE_CHUNK,
    PairedRecord,
    build_paired_fold,
    paired_delta_interval,
)

ROOT = Path(__file__).resolve().parents[3]

CHECKPOINT = "PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1"
FAMILY = "PREDICTIVE_STAGE3_MACRO_RELEASE_STATE_FAMILY_V1"
RESEARCH_GENERATION = "PREDICTIVE_RESEARCH_GENERATION_V1"
EVALUATION_CONTRACT = "docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md"
EVALUATION_CONTRACT_AMENDMENT = "A1"
BASELINE_PROTOCOL_PATH = "research/protocols/PREDICTIVE-BASELINES-V1.json"
SOURCE_ROADMAP_STAGE = "STAGE_3_CROSS_ASSET_AND_MACRO_CONTEXT"
ROADMAP_FAMILY = "MACRO_AND_FINANCIAL_CONDITIONS_CONTEXT"
INFORMATION_FAMILY = "ALFRED_STRICT_VINTAGE_US_MACRO_RELEASE_STATE"

PREDECESSOR_CHECKPOINT = "PREDICTIVE-STAGE3-MACRO-VINTAGE-V1"
PREDECESSOR_DISPOSITION = "BLOCKED_MACRO_SOURCE_COVERAGE_V1"
PREDECESSOR_FAMILY = "PREDICTIVE_STAGE3_MACRO_VINTAGE_FAMILY_V1"

LINEAR_MODEL_VERSION = "MACRO_RELEASE_STATE_LINEAR_V1"
HGBR_MODEL_VERSION = "MACRO_RELEASE_STATE_HGBR_V1"
CONFIGURATION_ORDER = (LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION)

ROOT_HYPOTHESIS_ID = "H-PRED-MACRO-003"
EXPERIMENT_IDS = {
    LINEAR_MODEL_VERSION: "EXP-PRED-009-MACRO-RELEASE-STATE-LINEAR",
    HGBR_MODEL_VERSION: "EXP-PRED-010-MACRO-RELEASE-STATE-HGBR",
}
HYPOTHESIS_IDS = {
    LINEAR_MODEL_VERSION: "H-PRED-MACRO-003",
    HGBR_MODEL_VERSION: "H-PRED-MACRO-004",
}

SEARCH_PLAN_PATH = "research/protocols/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-SEARCH-PLAN-V1.json"
ADMISSION_PATH = "reports/validation/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1-ADMISSION.json"
REPORT_JSON_PATH = "reports/research/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1.json"
REPORT_MARKDOWN_PATH = "reports/research/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1.md"
CHECKPOINT_REPORT_PATH = "reports/checkpoints/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1.md"

CREATED_AT = "2026-09-21T00:00:00Z"

MINIMUM_IMPORTANT_EFFECT = 0.015
FAMILYWISE_ALPHA = 0.05
CANDIDATE_ALPHA = 0.025
POOLED_COVERAGE_GATE = 0.95
FOLD_COVERAGE_GATE = 0.90
FAMILY_SIZE = 2
PAIRED_SEED = 20260921

LINEAR_DIRECTION_PARAMETERS: dict[str, Any] = {
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
    "random_state": 20260921,
}

# The primary effect is measured against the information-free control; the absolute reference
# is a separate, non-rescuable condition of the gate.
MATCHED_CONTROL = TRAINING_UP_BASE_RATE
ABSOLUTE_REFERENCE = ALWAYS_UP

GATE_NAMES = (
    "POOLED_COVERAGE_AT_LEAST_0_95",
    "EVERY_INCLUDED_FOLD_COVERAGE_AT_LEAST_0_90",
    "POOLED_DELTA_VERSUS_MATCHED_TRAINING_BASE_RATE_AT_LEAST_MESI",
    "PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO",
    "WIN_RATE_AT_LEAST_MATCHED_ALWAYS_UP",
    "BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER",
    "AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE",
)

ADVANCE = {
    LINEAR_MODEL_VERSION: "ADVANCE_MACRO_RELEASE_STATE_LINEAR_V1",
    HGBR_MODEL_VERSION: "ADVANCE_MACRO_RELEASE_STATE_HGBR_V1",
}
NO_ADVANCE = {
    LINEAR_MODEL_VERSION: "NO_ADVANCE_MACRO_RELEASE_STATE_LINEAR_V1",
    HGBR_MODEL_VERSION: "NO_ADVANCE_MACRO_RELEASE_STATE_HGBR_V1",
}

FAMILY_REJECTED = "REJECTED_DEVELOPMENT_NO_SEALED"
FAMILY_SIGNAL = "ADVANCE_TO_RESEARCH_DIRECTOR_REVIEW"
NOT_ELIGIBLE = "NOT_ELIGIBLE_REJECTED_DEVELOPMENT"
REVIEW_ELIGIBLE = "ELIGIBLE_FOR_RESEARCH_DIRECTOR_SEALED_REVIEW"

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
# The predecessor's frozen records. The admission hashes them so this checkpoint cannot
# silently edit, weaken or reclassify the source block it descends from.
PREDECESSOR_RECORDS = (
    "research/protocols/PREDICTIVE-STAGE3-MACRO-VINTAGE-SEARCH-PLAN-V1.json",
    "reports/validation/PREDICTIVE-STAGE3-MACRO-VINTAGE-V1-SOURCE-AUDIT.json",
    "reports/validation/PREDICTIVE-STAGE3-MACRO-VINTAGE-V1-ADMISSION.json",
    "research/experiments/EXP-PRED-007-MACRO-VINTAGE-LINEAR/preregistration.json",
    "research/experiments/EXP-PRED-008-MACRO-VINTAGE-HGBR/preregistration.json",
    "reports/checkpoints/PREDICTIVE-STAGE3-MACRO-VINTAGE-V1.md",
    "docs/contracts/PREDICTIVE_MACRO_VINTAGE_CONTEXT_V1.md",
)

IMPLEMENTATION_FILES = (
    "backend/app/predictive/__init__.py",
    "backend/app/predictive/baselines.py",
    "backend/app/predictive/evaluation.py",
    "backend/app/predictive/folds.py",
    "backend/app/predictive/internal_model.py",
    "backend/app/predictive/labels.py",
    "backend/app/predictive/macro_release_state.py",
    "backend/app/predictive/macro_release_state_audit.py",
    "backend/app/predictive/macro_release_state_source.py",
    "backend/app/predictive/paired_inference.py",
    "scripts/run_predictive_macro_release_state.py",
)


@dataclass(frozen=True)
class DirectionHead:
    """A frozen optional scaler, a frozen base model and a training-only Platt map.

    Defined here rather than imported: the width check must be this family's own feature
    count, and a head borrowed from another family would validate against the wrong width.
    """

    scaler: Any
    base: Any
    platt: Any
    split: Any

    def _design(self, features: Sequence[Sequence[float]]) -> Any:
        import numpy as np

        from .internal_model import ModelError

        matrix = np.asarray(features, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[1] != FEATURE_COUNT:
            raise ModelError("the direction head was given the wrong feature width")
        return matrix if self.scaler is None else self.scaler.transform(matrix)

    def probability_up(self, features: Sequence[Sequence[float]]) -> list[float]:
        """Calibrated P(UP). The only route from features to an exposed probability."""
        raw = self.base.decision_function(self._design(features)).reshape(-1, 1)
        return [float(value) for value in self.platt.predict_proba(raw)[:, 1]]


def director_decisions() -> dict[str, Any]:
    """The decisions frozen before any target-bearing fit or outer prediction."""
    return {
        "decision_id": "PREDICTIVE_STAGE3_MACRO_RELEASE_STATE_ADMISSION_V1",
        "decided_by": "RESEARCH_DIRECTOR",
        "generation": RESEARCH_GENERATION,
        "generation_continues": True,
        "target_or_horizon_changed": False,
        "target": "BTCUSDT_SPOT_24H_TERMINAL_DIRECTION",
        "labels_folds_scorer_mesi_or_advancement_changed": False,
        "magnitude_declared": False,
        "magnitude_disposition": "DEFERRED_UNTIL_A_FAMILY_EARNS_DIRECTIONAL_ADMISSION",
        "basis_disposition": "DEFERRED",
        "stage1_substrate_disposition": "DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH",
        "prior_executed_configurations": 8,
        "prior_executed_configurations_unchanged": True,
        "prior_results_changed": False,
        "predecessor_checkpoint": PREDECESSOR_CHECKPOINT,
        "predecessor_disposition": PREDECESSOR_DISPOSITION,
        "predecessor_reclassified_as_market_evidence": False,
        "predecessor_records_modified": False,
        "source_semantics_remediations_authorized": 1,
        "source_semantics_remediation_consumed": 1,
        "third_macro_source_redesign_authorized": False,
        "current_revised_fred_substitution": False,
        "interpolation_or_future_vintage": False,
        "feature_search": False,
        "threshold_search": False,
        "sealed_btc_access": False,
        "admitted_family": FAMILY,
        "admitted_source": INFORMATION_FAMILY,
        "admission_rationale": (
            "The predecessor never produced a market result: it stopped on a source-design "
            "defect in which one freshness concept was applied to every release frequency, so "
            "a legitimate latest-known monthly release was judged stale between publications. "
            "Correcting the release-state semantics tests the same orthogonal macro channel "
            "on the same hash-pinned substrate, without touching the frozen scientific design."
        ),
        "rejected_families_unchanged": [
            "PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1",
            "PREDICTIVE_STAGE2_SETTLED_FUNDING_FAMILY_V1",
            "PREDICTIVE_STAGE2_OPEN_INTEREST_MODEL_FAMILY_V1",
            "PREDICTIVE_STAGE3_CROSS_ASSET_BREADTH_FAMILY_V1",
        ],
        "rejected_families_disposition": FAMILY_REJECTED,
        "rejected_family_features_combined": False,
        "incremental_control_omitted": True,
        "incremental_control_rationale": (
            "No predictive family has been admitted, so an incremental control over an "
            "admitted feature set would be information-free."
        ),
    }


def specification(model_version: str) -> dict[str, Any]:
    """The executed configuration, exactly as preregistered."""
    if model_version not in EXPERIMENT_IDS:
        raise ExperimentError(f"unknown macro release-state configuration: {model_version}")
    linear = model_version == LINEAR_MODEL_VERSION
    return {
        "model_version": model_version,
        "family": FAMILY,
        "sklearn_version": "1.7.2",
        "declares_direction": True,
        "declares_probability": True,
        "declares_magnitude": False,
        "direction_base_estimator": (
            "LogisticRegression" if linear else "HistGradientBoostingClassifier"
        ),
        "direction_base_parameters": dict(
            LINEAR_DIRECTION_PARAMETERS if linear else HGBR_PARAMETERS
        ),
        "direction_input_scaling": (
            "STANDARD_SCALER_FITTED_ON_BASE_FIT_ROWS_ONLY" if linear else "NONE_NOT_REQUIRED"
        ),
        "calibration_estimator": "LogisticRegression",
        "calibration_input": "BASE_MODEL_RAW_DECISION_FUNCTION_SCORE",
        "calibration_penalty": None,
        "calibration_split_fraction": CALIBRATION_SPLIT_FRACTION,
        "calibration_embargo_hours": CALIBRATION_EMBARGO_HOURS,
        "calibration_rows": "TRAINING_ONLY",
        "decision_rule": "DECLARE_UP_WHEN_CALIBRATED_P_UP_GREATER_OR_EQUAL_0_5_TIES_UP",
        "probability_rule": "EXPOSE_P_DECLARED_DIRECTION_CORRECT",
        "probability_threshold_searched": False,
        "hyperparameter_search": False,
        "magnitude_estimator": None,
        "abstention_only_on_source_or_feature_validity": True,
    }


def search_plan() -> dict[str, Any]:
    """The Stage-3 macro release-state family, frozen before any candidate result."""
    return {
        "schema_version": 1,
        "version": "PREDICTIVE_STAGE3_MACRO_RELEASE_STATE_SEARCH_PLAN_V1",
        "status": "FROZEN_BEFORE_OBSERVATION",
        "checkpoint": CHECKPOINT,
        "research_generation": RESEARCH_GENERATION,
        "family": FAMILY,
        "root_hypothesis_id": ROOT_HYPOTHESIS_ID,
        "source_roadmap_stage": SOURCE_ROADMAP_STAGE,
        "source_roadmap_family": ROADMAP_FAMILY,
        "information_family": INFORMATION_FAMILY,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "baseline_protocol": BASELINE_PROTOCOL_PATH,
        "predictive_source_contract": CONTRACT_PATH,
        "predecessor_source_contract": PREDECESSOR_CONTRACT_PATH,
        "director_decisions": director_decisions(),
        "purpose": (
            "Freeze the complete Stage-3 macro release-state model family before either "
            "configuration is executed, so neither can be influenced by the other's result."
        ),
        "source_semantics": {
            "version": FEATURE_SET_VERSION,
            "release_state_version": RELEASE_STATE_VERSION,
            "supersedes": PREDECESSOR_FEATURE_SET_VERSION,
            "current_state_rule": "GREATEST_OBSERVATION_DATE_IN_THE_AS_OF_T_SNAPSHOT",
            "current_state_expiry_relative_to_decision_time": False,
            "state_persistence_is_not_interpolation": True,
            "interpolation_or_backfill": False,
            "historical_anchor_offset_days": {
                f"{series}_{label}": offset for series, label, offset, _ in HISTORICAL_ANCHORS
            },
            "historical_anchor_tolerance_days": {
                f"{series}_{label}": tolerance for series, label, _, tolerance in HISTORICAL_ANCHORS
            },
            "exact_month_anchors": {
                f"{series}_{label}": months for series, label, months in EXACT_MONTH_ANCHORS
            },
            "source_cadence_limit_days": dict(SOURCE_CADENCE_LIMIT_DAYS),
        },
        "feature_set": {
            "version": FEATURE_SET_VERSION,
            "count": FEATURE_COUNT,
            "ordered_names": list(FEATURE_NAMES),
            "series": list(SERIES),
            "identical_quantities_and_order_to_v1": True,
        },
        "family_size": FAMILY_SIZE,
        "both_configurations_executed_in_one_work_package": True,
        "result_dependent_early_stop": False,
        "declares": {"direction": True, "probability": True, "magnitude": False},
        "configurations": [
            {
                "order": index + 1,
                "model_version": model_version,
                "experiment_id": EXPERIMENT_IDS[model_version],
                "hypothesis_id": HYPOTHESIS_IDS[model_version],
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
        "primary_effect": "CANDIDATE_WIN_RATE_MINUS_MATCHED_TRAINING_UP_BASE_RATE_WIN_RATE",
        "mesi": MINIMUM_IMPORTANT_EFFECT,
        "inference": {
            "method": PAIRED_METHOD,
            "block_length_hours": PAIRED_BLOCK_LENGTH_HOURS,
            "replicates": PAIRED_REPLICATES,
            "seed": PAIRED_SEED,
            "seed_is_new_for_this_family": True,
            "replicate_chunk": REPLICATE_CHUNK,
        },
        "source_gate": {
            "fold_coverage": SOURCE_FOLD_COVERAGE_GATE,
            "minimum_history_days": MINIMUM_TRAINING_HISTORY_DAYS,
            "minimum_admissible_folds": MINIMUM_ADMISSIBLE_FOLDS,
            "pooled_coverage": SOURCE_POOLED_COVERAGE_GATE,
            "semantics_failure_classification": SEMANTICS_BLOCKED,
            "integrity_failure_classification": INTEGRITY_BLOCKED,
            "coverage_failure_classification": COVERAGE_BLOCKED,
            "family_disposition_if_blocked": PARKED,
        },
        "budget": {
            "planned_model_configurations": FAMILY_SIZE,
            "consumed_by_this_checkpoint": FAMILY_SIZE,
            "remaining_after_this_checkpoint": 0,
            "source_semantics_versions_authorized": 1,
            "source_semantics_versions_consumed": 1,
        },
        "forbidden": [
            "EDITING_OR_RECLASSIFYING_THE_PREDECESSOR_SOURCE_BLOCK",
            "LOWERING_A_COVERAGE_GATE_AFTER_SEEING_IT",
            "A_THIRD_MACRO_SOURCE_REDESIGN_IN_GENERATION_V1",
            "FEATURE_PRUNING_OR_SEARCH_AFTER_A_SOURCE_OR_MARKET_RESULT",
            "MIXING_REJECTED_FEATURE_FAMILIES",
            "BREADTH_INVERSION_NEGATION_OR_THRESHOLD_RESCUE",
            "TARGET_OR_HORIZON_CHANGE",
            "MAGNITUDE_HEAD",
            "BASIS",
            "STAGE1_SUBSTRATE_GAP_REPAIR",
            "CURRENT_REVISED_MACRO_DATA",
            "INTERPOLATION_OR_FUTURE_VINTAGE",
            "SEALED_OR_POST_CUTOFF_BTC_ACCESS",
            "REAL_MONEY",
        ],
        "boundaries": {
            "additional_information_family": False,
            "post_cutoff_market_data": False,
            "predecessor_records_modified": False,
            "sealed_queries": 0,
            "champion_created": False,
            "real_money": False,
        },
    }


def preregistration_path(model_version: str) -> str:
    return f"research/experiments/{EXPERIMENT_IDS[model_version]}/preregistration.json"


def result_path(model_version: str) -> str:
    return f"research/experiments/{EXPERIMENT_IDS[model_version]}/result.json"


def trials_path(model_version: str) -> str:
    return f"research/experiments/{EXPERIMENT_IDS[model_version]}/trials.json"


def _audit(root: Path) -> dict[str, Any]:
    record = json.loads((root / AUDIT_PATH).read_text(encoding="utf-8"))
    if record["status"] != PASS:
        raise ExperimentError(f"the source audit blocked this checkpoint: {record['status']}")
    if record["target_bearing_model_fitted"]:
        raise ExperimentError("the source audit claims a model fit it must precede")
    if record["predecessor_reclassified"]:
        raise ExperimentError("the source audit reclassified the predecessor source block")
    return record


def included_folds(root: Path = ROOT) -> list[str]:
    """The source-admissible folds, read from the pre-result audit, never chosen here."""
    return list(_audit(root)["coverage"]["admissible_folds"])


def required_non_negative_folds(fold_count: int) -> int:
    return math.ceil(2 / 3 * fold_count)


def preregistration(model_version: str, root: Path = ROOT) -> dict[str, Any]:
    """The frozen hypothesis, design, inference plan and advancement gate for one candidate."""
    if model_version not in EXPERIMENT_IDS:
        raise ExperimentError(f"unknown macro release-state configuration: {model_version}")
    audit = _audit(root)
    folds = list(audit["coverage"]["admissible_folds"])
    return {
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
        "root_hypothesis_id": ROOT_HYPOTHESIS_ID,
        "hypothesis_id": HYPOTHESIS_IDS[model_version],
        "hypothesis": (
            "Strict point-in-time U.S. macro and financial-condition release state, read with "
            "persistent current-release semantics and available at the BTC hourly decision "
            "instant, contains out-of-sample information about the frozen BTCUSDT spot 24h "
            "terminal direction beyond an information-free chronological base-rate control."
        ),
        "hypothesis_class": "MATERIAL_PREDICTIVE_HYPOTHESIS",
        "model_version": model_version,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "baseline_protocol": BASELINE_PROTOCOL_PATH,
        "source_roadmap_stage": SOURCE_ROADMAP_STAGE,
        "source_roadmap_family": ROADMAP_FAMILY,
        "director_decisions": director_decisions(),
        "predecessor": {
            "checkpoint": PREDECESSOR_CHECKPOINT,
            "family": PREDECESSOR_FAMILY,
            "disposition": PREDECESSOR_DISPOSITION,
            "reclassified": False,
            "records_modified": False,
            "model_fits": 0,
            "outer_predictions": 0,
            "configurations_consumed": 0,
        },
        "target": {
            "symbol": "BTCUSDT",
            "market": "crypto_spot",
            "canonical_resolution": "1m",
            "decision_cadence": "1h",
            "horizon_hours": HORIZON_HOURS,
            "label": "r_24h = log(close[T + 24h] / close[T])",
            "path_dependent": False,
            "target_or_horizon_changed": False,
        },
        "source": {
            "manifest": MANIFEST_PATH,
            "predictive_contract": CONTRACT_PATH,
            "predecessor_predictive_contract": PREDECESSOR_CONTRACT_PATH,
            "source_audit": AUDIT_PATH,
            "source_audit_status": audit["status"],
            "information_family": INFORMATION_FAMILY,
            "series": list(SERIES),
            "current_state_rule": "GREATEST_OBSERVATION_DATE_IN_THE_AS_OF_T_SNAPSHOT",
            "current_state_expiry_relative_to_decision_time": False,
            "current_revised_substitution": False,
            "post_2024_vintages": 0,
            "interpolation": False,
            "nearest_future_substitution": False,
            "source_cadence_limit_days": dict(SOURCE_CADENCE_LIMIT_DAYS),
            "source_cadence_integrity_passed": audit["source_cadence_integrity"]["passed"],
        },
        "features": {
            "version": FEATURE_SET_VERSION,
            "supersedes": PREDECESSOR_FEATURE_SET_VERSION,
            "count": FEATURE_COUNT,
            "ordered_names": list(FEATURE_NAMES),
            "identical_quantities_and_order_to_v1": True,
            "unavailability_taxonomy": list(UNAVAILABILITY_TAXONOMY),
            "unavailable_evaluation_row": "NEUTRAL_UNCERTAIN_ABSTENTION_COUNTED",
            "unavailable_training_row": "EXCLUDED_FROM_FITTING_COUNTED",
            "rejected_family_features_combined": False,
            "btc_price_or_return_feature_present": False,
            "clipping_winsorization_or_rank_transform": False,
            "feature_selection": False,
        },
        "model": specification(model_version),
        "evaluation_design": {
            "design": FOLD_DESIGN,
            "random_k_fold": False,
            "included_folds": folds,
            "included_fold_count": len(folds),
            "fold_selection": "PRE_RESULT_SOURCE_AUDIT_DETERMINISTIC",
            "fold_selection_used_return_values": False,
            "fold_boundaries": [
                {"fold": name, "start": start, "end": end}
                for name, start, end in FOLD_BOUNDARIES
                if name in folds
            ],
            "purge_embargo_hours": PURGE_EMBARGO_HOURS,
            "training": "EXPANDING_CHRONOLOGICAL_STRICTLY_BEFORE_THE_FOLD",
            "folds_recut": False,
            "outer_evaluation_used_in_fitting": False,
            "source_gate": {
                "fold_coverage": SOURCE_FOLD_COVERAGE_GATE,
                "minimum_training_history_days": MINIMUM_TRAINING_HISTORY_DAYS,
                "minimum_admissible_folds": MINIMUM_ADMISSIBLE_FOLDS,
                "pooled_coverage": SOURCE_POOLED_COVERAGE_GATE,
            },
        },
        "controls": {
            "primary": MATCHED_CONTROL,
            "primary_semantics": "AMENDMENT_A1_TRAINING_ONLY_REFIT_PER_FOLD",
            "absolute_reference": ABSOLUTE_REFERENCE,
            "descriptive": [PREVIOUS_24H_SIGN_PERSISTENCE],
            "scored_on": "IDENTICAL_CANDIDATE_ACTIONABLE_NON_NEUTRAL_TIMESTAMPS",
            "persistence_inverted": False,
            "beating_0_5_or_a_weak_control_is_not_usefulness": True,
        },
        "primary_effect": {
            "definition": (
                "candidate actionable directional win rate - matched TRAINING_UP_BASE_RATE "
                "win rate on the exact candidate-actionable timestamps"
            ),
            "matched_control": MATCHED_CONTROL,
            "minimum_important_effect": MINIMUM_IMPORTANT_EFFECT,
            "minimum_important_effect_units": "ABSOLUTE_WIN_RATE_POINTS",
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
            "blocks_cross_fold_boundaries": False,
            "abstentions_compressed_into_adjacency": False,
        },
        "mandatory_reporting": [
            "DIRECTIONAL_WIN_RATE_WITH_SAMPLE_SIZE_AND_COVERAGE",
            "BRIER_SCORE_AND_FIXED_BIN_RELIABILITY_TABLE",
            "CHRONOLOGICAL_PER_FOLD_RESULTS",
            "MATCHED_AND_CANONICAL_BASELINE_COMPARISONS",
            "TYPED_SOURCE_UNAVAILABILITY_ACCOUNTING",
        ],
        "reliability_bin_edges": list(RELIABILITY_BIN_EDGES),
        "advancement_gate": {
            "all_must_hold": True,
            "conditions": [
                {"name": GATE_NAMES[0], "threshold": POOLED_COVERAGE_GATE},
                {"name": GATE_NAMES[1], "threshold": FOLD_COVERAGE_GATE},
                {"name": GATE_NAMES[2], "threshold": MINIMUM_IMPORTANT_EFFECT},
                {"name": GATE_NAMES[3], "threshold": 0.0},
                {"name": GATE_NAMES[4], "threshold": "MATCHED_ALWAYS_UP_WIN_RATE"},
                {"name": GATE_NAMES[5], "threshold": "MATCHED_TRAINING_BASE_RATE_BRIER"},
                {"name": GATE_NAMES[6], "threshold": required_non_negative_folds(len(folds))},
            ],
            "pass_classification": ADVANCE[model_version],
            "fail_classification": NO_ADVANCE[model_version],
            "pass_meaning": REVIEW_ELIGIBLE,
            "sealed_query_authorized_on_pass": False,
            "secondary_metric_may_rescue_primary_gate": False,
            "post_result_tuning_authorized": False,
        },
        "budget": {
            "family_configurations_planned": FAMILY_SIZE,
            "family_configurations_consumed_by_this_experiment": 1,
            "executed_regardless_of_the_other_result": True,
            "hyperparameter_search": False,
            "threshold_search": False,
            "feature_search": False,
            "source_semantics_versions_consumed": 1,
        },
        "boundaries": {
            "additional_information_family": False,
            "combined_with_rejected_families": False,
            "stage1_substrate_repair": False,
            "post_cutoff_market_data": False,
            "predecessor_records_modified": False,
            "sealed_queries": 0,
            "champion_created": False,
            "real_money": False,
            "historical_results_changed": False,
            "previous_24h_sign_persistence_inverted": False,
            "post_hoc_winner_selection": False,
        },
    }


def admission(root: Path = ROOT) -> dict[str, Any]:
    """Prove the frozen records, the audited source and the implementation precede results."""
    plan_path = root / SEARCH_PLAN_PATH
    if not plan_path.is_file():
        raise ExperimentError("the frozen search plan must exist before the admission gate")
    if json.loads(plan_path.read_text(encoding="utf-8")) != search_plan():
        raise ExperimentError("the committed search plan is not what the code declares")
    audit_path = root / AUDIT_PATH
    if not audit_path.is_file():
        raise ExperimentError("the source audit must exist before the admission gate")
    audit = _audit(root)
    preregistrations: dict[str, str] = {}
    for model_version in CONFIGURATION_ORDER:
        relative = preregistration_path(model_version)
        path = root / relative
        if not path.is_file():
            raise ExperimentError(f"missing preregistration: {relative}")
        if json.loads(path.read_text(encoding="utf-8")) != preregistration(model_version, root):
            raise ExperimentError(f"the committed preregistration drifted: {relative}")
        preregistrations[EXPERIMENT_IDS[model_version]] = content_hash(path)
    if not (root / CONTRACT_PATH).is_file():
        raise ExperimentError("the release-state contract must exist before execution")
    missing = [name for name in IMPLEMENTATION_FILES if not (root / name).is_file()]
    if missing:
        raise ExperimentError(f"the implementation is incomplete: {missing}")
    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_PRE_EXECUTION_ADMISSION_V1",
        "checkpoint": CHECKPOINT,
        "family": FAMILY,
        "status": "PASS",
        "execution_authorized": True,
        "search_plan": SEARCH_PLAN_PATH,
        "search_plan_sha256": content_hash(plan_path),
        "preregistration_sha256": preregistrations,
        "predictive_contract": CONTRACT_PATH,
        "predictive_contract_sha256": content_hash(root / CONTRACT_PATH),
        "source_audit": AUDIT_PATH,
        "source_audit_sha256": content_hash(audit_path),
        "source_audit_status": audit["status"],
        "source_semantics_version": FEATURE_SET_VERSION,
        "included_folds": list(audit["coverage"]["admissible_folds"]),
        "source": source_identity(root),
        "implementation_sha256": {name: content_hash(root / name) for name in IMPLEMENTATION_FILES},
        "prior_experiment_result_sha256": {
            path: content_hash(root / path) for path in PRIOR_EXPERIMENT_RESULTS
        },
        "predecessor_record_sha256": {
            path: content_hash(root / path) for path in PREDECESSOR_RECORDS
        },
        "director_decisions": director_decisions(),
        "feature_set_version": FEATURE_SET_VERSION,
        "feature_count": FEATURE_COUNT,
        "paired_bootstrap_seed": PAIRED_SEED,
        "family_configurations_planned": FAMILY_SIZE,
        "family_configurations_consumed_before_this_run": 0,
        "source_semantics_versions_authorized": 1,
        "source_semantics_versions_consumed": 1,
        "market_results_observed": 0,
        "model_fits_executed": 0,
        "post_cutoff_access": 0,
        "sealed_queries": 0,
        "champion_status": "NONE",
        "real_money": False,
    }


def admission_identity(root: Path = ROOT) -> str:
    record = admission(root)
    return payload_hash(
        {
            "search_plan_sha256": record["search_plan_sha256"],
            "preregistration_sha256": record["preregistration_sha256"],
            "predictive_contract_sha256": record["predictive_contract_sha256"],
            "source_audit_sha256": record["source_audit_sha256"],
            "substrate_file_sha256": record["source"]["substrate_file_sha256"],
            "implementation_sha256": record["implementation_sha256"],
            "prior_experiment_result_sha256": record["prior_experiment_result_sha256"],
            "predecessor_record_sha256": record["predecessor_record_sha256"],
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


def _fit_direction(
    model_version: str,
    open_times: Sequence[int],
    features: Sequence[Sequence[float]],
    directions: Sequence[str],
) -> DirectionHead:
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    from .internal_model import PLATT_PARAMETERS, ModelError, calibration_split
    from .labels import HOUR_SECONDS

    if any(value not in {UP, DOWN} for value in directions):
        raise ModelError("a training row carries a non-directional label")
    split = calibration_split(open_times)
    embargo = CALIBRATION_EMBARGO_HOURS * HOUR_SECONDS
    boundary = split.boundary_open_time
    matrix = np.asarray(features, dtype=np.float64)
    truth = np.asarray([1 if value == UP else 0 for value in directions], dtype=np.int64)
    moments = np.asarray(open_times, dtype=np.int64)
    base_mask = moments + embargo <= boundary
    calibration_mask = moments >= boundary
    if len(np.unique(truth[base_mask])) < 2 or len(np.unique(truth[calibration_mask])) < 2:
        raise ModelError("a frozen split side lacks both directional classes")

    linear = model_version == LINEAR_MODEL_VERSION
    scaler = StandardScaler().fit(matrix[base_mask]) if linear else None
    design = matrix[base_mask] if scaler is None else scaler.transform(matrix[base_mask])
    base = (
        LogisticRegression(**LINEAR_DIRECTION_PARAMETERS)
        if linear
        else HistGradientBoostingClassifier(**HGBR_PARAMETERS)
    )
    base.fit(design, truth[base_mask])
    calibration_design = (
        matrix[calibration_mask] if scaler is None else scaler.transform(matrix[calibration_mask])
    )
    raw = base.decision_function(calibration_design).reshape(-1, 1)
    platt = LogisticRegression(**PLATT_PARAMETERS)
    platt.fit(raw, truth[calibration_mask])
    if list(platt.classes_) != [0, 1]:
        raise ModelError("the Platt map did not see both directional classes")
    return DirectionHead(scaler=scaler, base=base, platt=platt, split=split)


def _fold_predictions(
    model_version: str, fold: Fold, cache: Mapping[int, tuple[float, ...]]
) -> tuple[dict[str, Any], list[Prediction]]:
    training = [label for label in fold.training if label.open_time in cache]
    if not training:
        raise ExperimentError(f"{fold.name}: no source-eligible training row")
    directional = [label for label in training if label.direction in {UP, DOWN}]
    excluded_neutral = len(training) - len(directional)

    head = _fit_direction(
        model_version,
        [label.open_time for label in directional],
        [cache[label.open_time] for label in directional],
        [label.direction for label in directional],
    )

    available = [label for label in fold.evaluation if label.open_time in cache]
    matrix = [cache[label.open_time] for label in available]
    probabilities = head.probability_up(matrix) if matrix else []
    by_time = dict(zip([label.open_time for label in available], probabilities, strict=True))

    predictions: list[Prediction] = []
    for label in fold.evaluation:
        probability_up = by_time.get(label.open_time)
        if probability_up is None:
            predictions.append(Prediction(open_time=label.open_time, direction=ABSTAIN))
            continue
        predictions.append(
            Prediction(
                open_time=label.open_time,
                direction=declared_direction(probability_up),
                probability=declared_probability(probability_up),
            )
        )

    split = head.split
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
        "evaluation_rows_source_eligible": len(available),
        "evaluation_rows_source_unavailable": len(fold.evaluation) - len(available),
        "model_fits": {"direction_base": 1, "direction_calibration": 1},
    }
    return fit_record, predictions


def _actionable(predictions: Sequence[Prediction], labels: Sequence[Label]) -> list[Label]:
    declared = {item.open_time for item in predictions if item.direction in {UP, DOWN}}
    return [label for label in labels if label.open_time in declared and label.direction != NEUTRAL]


def _controls(
    matched_labels: Sequence[Label], base_rate_fit: Any, bars_by_open: Mapping[int, Bar]
) -> dict[str, Any]:
    outcomes = _outcomes(matched_labels)
    base_rate = score(
        training_up_base_rate_predictions(base_rate_fit, matched_labels),
        outcomes,
        declares_direction=True,
        declares_probability=True,
        declares_magnitude=False,
    )
    base_rate["fit"] = base_rate_fit.as_record()
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
    return {
        MATCHED_CONTROL: base_rate,
        ABSOLUTE_REFERENCE: always_up,
        PREVIOUS_24H_SIGN_PERSISTENCE: persistence,
    }


def _paired_records(
    predictions: Sequence[Prediction], matched_labels: Sequence[Label], base_rate_fit: Any
) -> list[PairedRecord]:
    truth = {label.open_time: label for label in matched_labels}
    candidate = {item.open_time: item.direction for item in predictions}
    return [
        PairedRecord(
            open_time=moment,
            candidate_correct=candidate[moment] == truth[moment].direction,
            baseline_correct=base_rate_fit.direction == truth[moment].direction,
        )
        for moment in sorted(truth)
    ]


def advancement_gate(
    model_version: str,
    pooled_coverage: float,
    fold_coverage: Mapping[str, float],
    pooled_delta: float,
    interval: Sequence[float],
    candidate_win_rate: float,
    always_up_win_rate: float,
    candidate_brier: float,
    base_rate_brier: float,
    fold_deltas: Mapping[str, float],
) -> dict[str, Any]:
    """The seven predeclared conditions. All must hold; no secondary metric ever rescues."""
    non_negative = sum(1 for value in fold_deltas.values() if value >= 0.0)
    required = required_non_negative_folds(len(fold_deltas))
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
            "observed": pooled_delta,
            "passed": pooled_delta >= MINIMUM_IMPORTANT_EFFECT,
        },
        GATE_NAMES[3]: {
            "threshold": 0.0,
            "observed": float(interval[0]),
            "passed": float(interval[0]) > 0.0,
        },
        GATE_NAMES[4]: {
            "threshold": always_up_win_rate,
            "observed": candidate_win_rate,
            "passed": candidate_win_rate >= always_up_win_rate,
        },
        GATE_NAMES[5]: {
            "threshold": base_rate_brier,
            "observed": candidate_brier,
            "passed": candidate_brier <= base_rate_brier,
        },
        GATE_NAMES[6]: {
            "threshold": required,
            "observed": non_negative,
            "passed": non_negative >= required,
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
        "secondary_metric_used_to_rescue": False,
        "required_non_negative_folds": required,
        "included_fold_count": len(fold_deltas),
    }


def baseline_context(root: Path = ROOT) -> dict[str, Any]:
    report = json.loads(
        (root / "reports/research/PREDICTIVE-BASELINES-V1.json").read_text(encoding="utf-8")
    )
    return {
        "source": "reports/research/PREDICTIVE-BASELINES-V1.json",
        "classification": report["classification"],
        "pooled": {
            name: {
                "win_rate": record["pooled"]["win_rate"],
                "coverage": record["pooled"]["coverage"],
            }
            for name, record in report["baselines"].items()
        },
        "reference_bar": report["baselines"][ALWAYS_UP]["pooled"]["win_rate"],
        "note": "SIX_FOLD_FULL_UNIVERSE_NOT_THE_MACRO_ADMISSIBLE_UNIVERSE",
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
    pooled_labels: list[Label] = []
    pooled_matched: list[Label] = []
    pooled_base_rate: list[Prediction] = []
    paired_folds = []
    fold_coverage: dict[str, float] = {}
    fold_deltas: dict[str, float] = {}
    fits = {"direction_base": 0, "direction_calibration": 0}

    for fold in folds:
        fit_record, directional = _fold_predictions(model_version, fold, cache)
        for key in fits:
            fits[key] += fit_record["model_fits"][key]
        trials.append(fit_record)
        directional_score = score(
            directional,
            _outcomes(fold.evaluation),
            declares_direction=True,
            declares_probability=True,
            declares_magnitude=False,
        )
        matched_labels = _actionable(directional, fold.evaluation)
        controls = _controls(matched_labels, base_rate_fits[fold.name], bars_by_open)
        paired_folds.append(
            build_paired_fold(
                fold.name,
                [label.open_time for label in fold.evaluation],
                _paired_records(directional, matched_labels, base_rate_fits[fold.name]),
            )
        )
        coverage = directional_score["coverage"]
        candidate_rate = directional_score["win_rate"]
        if coverage is None or candidate_rate is None:
            raise ExperimentError(f"{fold.name}: the fold produced no scorable prediction")
        fold_coverage[fold.name] = float(coverage)
        fold_deltas[fold.name] = float(candidate_rate) - float(
            controls[MATCHED_CONTROL]["win_rate"]
        )
        by_fold[fold.name] = {
            "fit": fit_record,
            "directional": directional_score,
            "matched_universe": {
                "records": len(matched_labels),
                "share_of_eligible": len(matched_labels) / len(fold.evaluation),
            },
            "controls": controls,
            "delta_versus_training_base_rate": fold_deltas[fold.name],
            "delta_versus_always_up": float(candidate_rate)
            - float(controls[ABSOLUTE_REFERENCE]["win_rate"]),
        }
        pooled_directional.extend(directional)
        pooled_labels.extend(fold.evaluation)
        pooled_matched.extend(matched_labels)
        pooled_base_rate.extend(
            training_up_base_rate_predictions(base_rate_fits[fold.name], matched_labels)
        )

    pooled_directional_score = score(
        pooled_directional,
        _outcomes(pooled_labels),
        declares_direction=True,
        declares_probability=True,
        declares_magnitude=False,
    )
    pooled_outcomes = _outcomes(pooled_matched)
    pooled_controls = {
        MATCHED_CONTROL: score(
            pooled_base_rate,
            pooled_outcomes,
            declares_direction=True,
            declares_probability=True,
            declares_magnitude=False,
        ),
        ABSOLUTE_REFERENCE: score(
            always_up_predictions(pooled_matched),
            pooled_outcomes,
            declares_direction=True,
            declares_probability=False,
            declares_magnitude=False,
        ),
        PREVIOUS_24H_SIGN_PERSISTENCE: score(
            previous_24h_sign_predictions(pooled_matched, bars_by_open),
            pooled_outcomes,
            declares_direction=True,
            declares_probability=False,
            declares_magnitude=False,
        ),
    }
    paired = paired_delta_interval(paired_folds, seed=PAIRED_SEED)
    pooled_coverage = float(pooled_directional_score["coverage"])
    candidate_rate = float(pooled_directional_score["win_rate"])
    base_rate_rate = float(pooled_controls[MATCHED_CONTROL]["win_rate"])
    always_up_rate = float(pooled_controls[ABSOLUTE_REFERENCE]["win_rate"])
    candidate_brier = float(pooled_directional_score["brier_score"])
    base_rate_brier = float(pooled_controls[MATCHED_CONTROL]["brier_score"])
    gate = advancement_gate(
        model_version,
        pooled_coverage,
        fold_coverage,
        candidate_rate - base_rate_rate,
        paired["interval"],
        candidate_rate,
        always_up_rate,
        candidate_brier,
        base_rate_brier,
        fold_deltas,
    )

    return {
        "experiment_id": EXPERIMENT_IDS[model_version],
        "hypothesis_id": HYPOTHESIS_IDS[model_version],
        "model_version": model_version,
        "model": specification(model_version),
        "model_fits": {**fits, "total": sum(fits.values())},
        "trials": trials,
        "candidate": {
            "pooled_directional": pooled_directional_score,
            "by_fold": by_fold,
        },
        "matched_universe": {
            "records": len(pooled_matched),
            "share_of_eligible": len(pooled_matched) / len(pooled_labels),
            "definition": "CANDIDATE_ACTIONABLE_NON_NEUTRAL_TIMESTAMPS",
        },
        "controls": pooled_controls,
        "primary_comparison": {
            "definition": (
                "candidate actionable directional win rate - matched TRAINING_UP_BASE_RATE "
                "win rate on candidate-actionable, non-NEUTRAL timestamps"
            ),
            "matched_control": MATCHED_CONTROL,
            "candidate_win_rate": candidate_rate,
            "matched_base_rate_win_rate": base_rate_rate,
            "pooled_delta": candidate_rate - base_rate_rate,
            "minimum_important_effect": MINIMUM_IMPORTANT_EFFECT,
            "fold_deltas": fold_deltas,
            "fold_coverage": fold_coverage,
            "paired_interval": paired,
        },
        "absolute_reference_comparison": {
            "control": ABSOLUTE_REFERENCE,
            "matched_win_rate": always_up_rate,
            "candidate_at_least_reference": candidate_rate >= always_up_rate,
            "delta_versus_always_up": candidate_rate - always_up_rate,
            "note": "AN_ABSOLUTE_FLOOR_NOT_THE_PRIMARY_EFFECT",
        },
        "calibration_comparison": {
            "control": MATCHED_CONTROL,
            "matched_brier_score": base_rate_brier,
            "candidate_brier_score": candidate_brier,
            "candidate_brier_at_most_control": candidate_brier <= base_rate_brier,
        },
        "advancement_gate": gate,
        "terminal_classification": gate["terminal_classification"],
    }


def release_state_accounting(
    source: MacroReleaseStateSource, folds: Sequence[Fold]
) -> dict[str, Any]:
    """How long the current known level of each series persists over the included folds.

    This is source accounting, never a feature. It is what distinguishes state persistence
    from interpolation: every number below is a real release, and the audit's cadence gate
    has already proved the release calendar itself is not frozen.
    """
    instants = [label.open_time for fold in folds for label in fold.evaluation]
    by_series: dict[str, Any] = {}
    for series in SERIES:
        ages = []
        for instant in instants:
            current = source.current_release(series, instant)
            if current is None:
                continue
            from datetime import UTC, datetime

            ages.append((datetime.fromtimestamp(instant, UTC).date() - current[0]).days)
        ordered = sorted(ages)
        middle = len(ordered) // 2
        median = (
            0
            if not ordered
            else (
                ordered[middle]
                if len(ordered) % 2
                else (ordered[middle - 1] + ordered[middle]) // 2
            )
        )
        by_series[series] = {
            "measured_timestamps": len(ordered),
            "minimum_current_release_age_days": min(ordered, default=0),
            "median_current_release_age_days": median,
            "maximum_current_release_age_days": max(ordered, default=0),
        }
    return {
        "definition": "DECISION_DATE_MINUS_CURRENT_KNOWN_OBSERVATION_DATE",
        "by_series": by_series,
        "current_release_age_is_a_model_feature": False,
        "predecessor_rejected_a_current_level_on_this_age": True,
        "this_contract_rejects_a_current_level_on_this_age": False,
    }


def run_experiment(root: Path = ROOT) -> dict[str, Any]:
    """Execute both frozen configurations once and emit the complete contract report."""
    audit = _audit(root)
    names = list(audit["coverage"]["admissible_folds"])
    bars = load_hourly_bars(root)
    bars_by_open = index_bars(bars)
    label_set = build_labels(bars, horizon_hours=HORIZON_HOURS)
    fold_set = build_folds(
        label_set.labels, horizon_hours=HORIZON_HOURS, purge_embargo_hours=PURGE_EMBARGO_HOURS
    )
    assert_no_fold_leak(fold_set)
    folds = [fold for fold in fold_set.folds if fold.name in names]
    if [fold.name for fold in folds] != names:
        raise ExperimentError("the included folds are not the audited source-admissible set")

    source = load_release_state_source(root)
    cache, unavailability = availability_map(
        source, [label.open_time for label in label_set.labels]
    )

    base_rate_fits: dict[str, Any] = {}
    for fold in folds:
        eligible_training = [label for label in fold.training if label.open_time in cache]
        if not eligible_training:
            raise ExperimentError(f"{fold.name}: the base-rate control has no training row")
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
    disposition = FAMILY_SIGNAL if advanced else FAMILY_REJECTED
    eligible_total = sum(len(fold.evaluation) for fold in folds)

    return {
        "version": CHECKPOINT,
        "classification": "PREDICTIVE_EXPERIMENT_RESULT",
        "family": FAMILY,
        "research_generation": RESEARCH_GENERATION,
        "root_hypothesis_id": ROOT_HYPOTHESIS_ID,
        "information_family": INFORMATION_FAMILY,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "search_plan": SEARCH_PLAN_PATH,
        "admission": ADMISSION_PATH,
        "source_audit": AUDIT_PATH,
        "source_audit_status": audit["status"],
        "source_cadence_integrity": audit["source_cadence_integrity"],
        "predecessor": {
            "checkpoint": PREDECESSOR_CHECKPOINT,
            "family": PREDECESSOR_FAMILY,
            "disposition": PREDECESSOR_DISPOSITION,
            "reclassified": False,
            "records_modified": False,
            "model_fits": 0,
            "outer_predictions": 0,
            "configurations_consumed": 0,
        },
        "director_decisions": director_decisions(),
        "source": source_identity(root),
        "labels": label_set.accounting(),
        "folds": {
            "design": FOLD_DESIGN,
            "random_k_fold": False,
            "purge_embargo_hours": PURGE_EMBARGO_HOURS,
            "included_folds": names,
            "included_fold_count": len(names),
            "excluded_candidate_folds": [
                name for name in audit["coverage"]["candidate_folds"] if name not in names
            ],
            "fold_selection": "PRE_RESULT_SOURCE_AUDIT_DETERMINISTIC",
            "fold_selection_used_return_values": False,
            "eligible_decision_timestamps": eligible_total,
            "canonical_six_fold_eligible_total": fold_set.eligible_total(),
            "recut": False,
        },
        "features": {
            "version": FEATURE_SET_VERSION,
            "supersedes": PREDECESSOR_FEATURE_SET_VERSION,
            "count": FEATURE_COUNT,
            "ordered_names": list(FEATURE_NAMES),
            "identical_quantities_and_order_to_v1": True,
            "available_vectors": len(cache),
            "unavailable_vectors": sum(unavailability.values()),
            "unavailability_by_reason": unavailability,
            "btc_price_or_return_feature_present": False,
            "combined_with_rejected_families": False,
            "clipping_winsorization_or_rank_transform": False,
            "feature_selection": False,
        },
        "release_state_accounting": release_state_accounting(source, folds),
        "base_rate_control_fits": {
            "control": MATCHED_CONTROL,
            "fits": len(base_rate_fits),
            "classification": "COUNTED_TRAINING_BASE_RATE_NOT_A_MODEL_FIT",
            "by_fold": {name: fit.as_record() for name, fit in base_rate_fits.items()},
        },
        "configurations": configurations,
        "baseline_context": baseline_context(root),
        "family_disposition": {
            "family": FAMILY,
            "disposition": disposition,
            "advancing_configurations": [ADVANCE[name] for name in advanced],
            "configurations_executed": list(CONFIGURATION_ORDER),
            "post_hoc_winner_selected": False,
            "sealed_eligibility": {
                EXPERIMENT_IDS[name]: (REVIEW_ELIGIBLE if name in advanced else NOT_ELIGIBLE)
                for name in CONFIGURATION_ORDER
            },
            "sealed_queried": False,
            "champion_created": False,
            "prospective_observer_created": False,
            "descendant_tuned": False,
            "macro_source_design_closed": True,
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
            "source_semantics_versions_authorized": 1,
            "source_semantics_versions_consumed": 1,
            "source_semantics_versions_remaining": 0,
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
            "magnitude_declared": False,
        },
        "boundaries": {
            "additional_information_family": False,
            "combined_with_rejected_families": False,
            "predecessor_records_modified": False,
            "predecessor_reclassified": False,
            "third_macro_source_redesign": False,
            "coverage_gate_lowered_after_observation": False,
            "stage1_substrate_repair": False,
            "current_revised_macro_data": False,
            "interpolation_or_future_vintage": False,
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
    "ABSOLUTE_REFERENCE",
    "ADMISSION_PATH",
    "ADVANCE",
    "CANDIDATE_ALPHA",
    "CHECKPOINT",
    "CHECKPOINT_REPORT_PATH",
    "CONFIGURATION_ORDER",
    "EXPERIMENT_IDS",
    "FAMILY",
    "FAMILY_REJECTED",
    "FAMILY_SIGNAL",
    "FAMILY_SIZE",
    "GATE_NAMES",
    "HGBR_MODEL_VERSION",
    "HGBR_PARAMETERS",
    "HYPOTHESIS_IDS",
    "IMPLEMENTATION_FILES",
    "INFORMATION_FAMILY",
    "LINEAR_DIRECTION_PARAMETERS",
    "LINEAR_MODEL_VERSION",
    "MATCHED_CONTROL",
    "MINIMUM_IMPORTANT_EFFECT",
    "NOT_ELIGIBLE",
    "NO_ADVANCE",
    "PAIRED_SEED",
    "PREDECESSOR_CHECKPOINT",
    "PREDECESSOR_DISPOSITION",
    "PREDECESSOR_RECORDS",
    "PRIOR_EXPERIMENT_RESULTS",
    "REPORT_JSON_PATH",
    "REPORT_MARKDOWN_PATH",
    "REVIEW_ELIGIBLE",
    "ROOT_HYPOTHESIS_ID",
    "SEARCH_PLAN_PATH",
    "admission",
    "admission_identity",
    "advancement_gate",
    "baseline_context",
    "canonical_bytes",
    "director_decisions",
    "included_folds",
    "preregistration",
    "preregistration_path",
    "release_state_accounting",
    "required_non_negative_folds",
    "result_path",
    "run_experiment",
    "search_plan",
    "specification",
    "trials_path",
]
