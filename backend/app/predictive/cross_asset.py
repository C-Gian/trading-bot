"""`PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1` — contemporaneous crypto-market breadth.

Two preregistered configurations, `CROSS_ASSET_BREADTH_LINEAR_V1` and
`CROSS_ASSET_BREADTH_HGBR_V1`, both executed in this work package regardless of the first
result, on eight equal-weighted cross-sectional statistics of the non-BTC Binance spot USDT
universe, read strictly point-in-time.

Direction and calibrated probability only. Magnitude is deliberately not declared: the
generation has not yet established directional information from any source family, so
fitting another magnitude head would spend computation without answering the admission
question this checkpoint exists to answer.

The frozen target, labels, folds, scorer, reliability bins and dependence-aware bootstrap
are those of `PREDICTIVE_EVALUATION_CONTRACT_V1` Amendment A1 and `PREDICTIVE-BASELINES-V1`.
The evaluation fold set is not chosen here: it is whatever the pre-result source audit
declared source-admissible from source availability alone.

The label, fold, scoring and paired-inference modules are imported unchanged; their bytes are
hashed by five executed admissions and may not move.
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
from .cross_asset_audit import (
    AUDIT_PATH,
    MINIMUM_ADMISSIBLE_FOLDS,
    MINIMUM_ELIGIBLE_TIMESTAMPS,
    MINIMUM_TRAINING_HISTORY_DAYS,
    PASS,
)
from .cross_asset_audit import (
    FOLD_COVERAGE_GATE as SOURCE_FOLD_COVERAGE_GATE,
)
from .cross_asset_source import (
    CONTRACT_PATH,
    CROSS_SECTIONAL_WEIGHTING,
    ENDPOINT_OFFSET_HOURS,
    FEATURE_COUNT,
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    MANIFEST_PATH,
    MINIMUM_POINT_IN_TIME_UNIVERSE,
    REQUIRED_ENDPOINT_BARS,
    TARGET_SYMBOL,
    UNAVAILABILITY_TAXONOMY,
    CrossSectionPanel,
    availability_map,
    load_cross_section,
    source_identity,
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

CHECKPOINT = "PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1"
FAMILY = "PREDICTIVE_STAGE3_CROSS_ASSET_BREADTH_FAMILY_V1"
RESEARCH_GENERATION = "PREDICTIVE_RESEARCH_GENERATION_V1"
EVALUATION_CONTRACT = "docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md"
EVALUATION_CONTRACT_AMENDMENT = "A1"
BASELINE_PROTOCOL_PATH = "research/protocols/PREDICTIVE-BASELINES-V1.json"
SOURCE_ROADMAP_STAGE = "STAGE_3_CROSS_ASSET_AND_MACRO_CONTEXT"
ROADMAP_FAMILY = "CROSS_ASSET_CONTEXT"

LINEAR_MODEL_VERSION = "CROSS_ASSET_BREADTH_LINEAR_V1"
HGBR_MODEL_VERSION = "CROSS_ASSET_BREADTH_HGBR_V1"
CONFIGURATION_ORDER = (LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION)

ROOT_HYPOTHESIS_ID = "H-PRED-XB-001"
EXPERIMENT_IDS = {
    LINEAR_MODEL_VERSION: "EXP-PRED-007-CROSS-ASSET-BREADTH-LINEAR",
    HGBR_MODEL_VERSION: "EXP-PRED-008-CROSS-ASSET-BREADTH-HGBR",
}
HYPOTHESIS_IDS = {
    LINEAR_MODEL_VERSION: "H-PRED-XB-001",
    HGBR_MODEL_VERSION: "H-PRED-XB-002",
}

SEARCH_PLAN_PATH = "research/protocols/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-SEARCH-PLAN-V1.json"
ADMISSION_PATH = "reports/validation/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1-ADMISSION.json"
REPORT_JSON_PATH = "reports/research/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1.json"
REPORT_MARKDOWN_PATH = "reports/research/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1.md"

CREATED_AT = "2026-09-19T00:00:00Z"

MINIMUM_IMPORTANT_EFFECT = 0.015
FAMILYWISE_ALPHA = 0.05
CANDIDATE_ALPHA = 0.025
POOLED_COVERAGE_GATE = 0.95
FOLD_COVERAGE_GATE = 0.90
FAMILY_SIZE = 2
PAIRED_SEED = 20260919

LINEAR_DIRECTION_PARAMETERS: dict[str, Any] = {
    "penalty": "l2",
    "C": 1.0,
    "solver": "lbfgs",
    "fit_intercept": True,
    "max_iter": 2000,
    "tol": 1e-8,
    "class_weight": None,
}
HGBR_PARAMETERS: dict[str, Any] = {
    "learning_rate": 0.05,
    "max_iter": 200,
    "max_leaf_nodes": 15,
    "min_samples_leaf": 50,
    "l2_regularization": 1.0,
    "max_bins": 255,
    "early_stopping": False,
    "random_state": 20260917,
}

# The primary effect is measured against the information-free control, and the absolute
# reference is a separate, non-rescuable condition of the gate.
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
    LINEAR_MODEL_VERSION: "ADVANCE_CROSS_ASSET_BREADTH_LINEAR_V1",
    HGBR_MODEL_VERSION: "ADVANCE_CROSS_ASSET_BREADTH_HGBR_V1",
}
NO_ADVANCE = {
    LINEAR_MODEL_VERSION: "NO_ADVANCE_CROSS_ASSET_BREADTH_LINEAR_V1",
    HGBR_MODEL_VERSION: "NO_ADVANCE_CROSS_ASSET_BREADTH_HGBR_V1",
}

FAMILY_REJECTED = "REJECTED_DEVELOPMENT_NO_SEALED"
FAMILY_SIGNAL = "ADVANCE_TO_RESEARCH_DIRECTOR_REVIEW"
NOT_ELIGIBLE = "NOT_ELIGIBLE_REJECTED_DEVELOPMENT"
REVIEW_ELIGIBLE = "REQUIRES_RESEARCH_DIRECTOR_REVIEW"

IMPLEMENTATION_FILES = (
    "backend/app/predictive/__init__.py",
    "backend/app/predictive/baselines.py",
    "backend/app/predictive/cross_asset.py",
    "backend/app/predictive/cross_asset_audit.py",
    "backend/app/predictive/cross_asset_source.py",
    "backend/app/predictive/evaluation.py",
    "backend/app/predictive/folds.py",
    "backend/app/predictive/internal_model.py",
    "backend/app/predictive/labels.py",
    "backend/app/predictive/paired_inference.py",
    "scripts/run_predictive_cross_asset.py",
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
    """The Research Director's post-open-interest decisions, recorded before execution."""
    return {
        "decision_id": "PREDICTIVE_STAGE3_CROSS_ASSET_BREADTH_ADMISSION_V1",
        "decided_by": "RESEARCH_DIRECTOR",
        "generation_continues": True,
        "generation": RESEARCH_GENERATION,
        "target_or_horizon_changed": False,
        "target_change_disposition": "DEFERRED_WOULD_OPEN_A_NEW_RESEARCH_GENERATION",
        "rejected_configurations_before_this_family": 6,
        "stage1_substrate_disposition": "DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH",
        "canonical_hourly_gap_repaired": False,
        "contiguity_rule_relaxed": False,
        "basis_authorized": False,
        "basis_disposition": "DEFERRED_NOT_REJECTED",
        "basis_rationale": (
            "After null results from settled funding (a carry/price channel) and open "
            "interest (a positioning-quantity channel), the expected incremental "
            "information from a third derivatives/carry series is lower than the value of "
            "testing an orthogonal cross-asset channel."
        ),
        "admitted_family": FAMILY,
        "admitted_source": "BINANCE_SPOT_USDT_CROSS_SECTIONAL_BREADTH",
        "admission_rationale": (
            "Crypto-market breadth is orthogonal to everything already tested: it is neither "
            "BTC's own structure, nor its derivatives carry, nor its positioning quantity, "
            "and it is available at the BTC decision instant from an already-governed "
            "official source."
        ),
        "magnitude_declared": False,
        "magnitude_disposition": (
            "REINTRODUCED_ONLY_AFTER_A_SOURCE_FAMILY_EARNS_DIRECTIONAL_ADMISSION"
        ),
        "product_target_unchanged": "BTCUSDT",
        "cross_assets_are_context_only": True,
        "rejected_families_unchanged": [
            "PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1",
            "PREDICTIVE_STAGE2_SETTLED_FUNDING_FAMILY_V1",
            "PREDICTIVE_STAGE2_OPEN_INTEREST_MODEL_FAMILY_V1",
        ],
        "rejected_families_disposition": FAMILY_REJECTED,
        "rejected_family_results_immutable": True,
        "rejected_family_sealed_eligibility": False,
        "incremental_control_omitted": True,
        "incremental_control_rationale": (
            "No predictive family has been admitted, so an incremental control over an "
            "admitted feature set would be information-free."
        ),
    }


def search_plan() -> dict[str, Any]:
    """The Stage-3 cross-asset breadth model family, frozen before any candidate result."""
    return {
        "version": "PREDICTIVE_STAGE3_CROSS_ASSET_BREADTH_SEARCH_PLAN_V1",
        "status": "FROZEN_BEFORE_OBSERVATION",
        "checkpoint": CHECKPOINT,
        "research_generation": RESEARCH_GENERATION,
        "family": FAMILY,
        "root_hypothesis_id": ROOT_HYPOTHESIS_ID,
        "source_roadmap_stage": SOURCE_ROADMAP_STAGE,
        "source_roadmap_family": ROADMAP_FAMILY,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "baseline_protocol": BASELINE_PROTOCOL_PATH,
        "predictive_source_contract": CONTRACT_PATH,
        "director_decisions": director_decisions(),
        "purpose": (
            "Freeze the complete Stage-3 cross-asset breadth model family before either "
            "configuration is executed, so neither can be influenced by the other's result."
        ),
        "family_size": FAMILY_SIZE,
        "both_configurations_executed_in_one_work_package": True,
        "result_dependent_early_stop": False,
        "declares": {"direction": True, "probability": True, "magnitude": False},
        "configurations": [
            {
                "model_version": model_version,
                "experiment_id": EXPERIMENT_IDS[model_version],
                "hypothesis_id": HYPOTHESIS_IDS[model_version],
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
        "inference": {
            "method": PAIRED_METHOD,
            "block_length_hours": PAIRED_BLOCK_LENGTH_HOURS,
            "replicates": PAIRED_REPLICATES,
            "seed": PAIRED_SEED,
            "seed_is_new_for_this_family": True,
            "replicate_chunk": REPLICATE_CHUNK,
        },
        "budget": {
            "planned_model_configurations": FAMILY_SIZE,
            "consumed_by_this_checkpoint": FAMILY_SIZE,
            "remaining_after_this_checkpoint": 0,
        },
        "forbidden": [
            "THIRD_STAGE3_CROSS_ASSET_MODEL",
            "HYPERPARAMETER_SEARCH",
            "THRESHOLD_SEARCH",
            "FEATURE_SEARCH",
            "FEATURE_REDESIGN",
            "RESULT_DEPENDENT_EARLY_STOP",
            "POST_HOC_WINNER_SELECTION",
            "COMBINING_BREADTH_WITH_REJECTED_STAGE1_FUNDING_OR_OPEN_INTEREST_FEATURES",
            "IMPORTING_HISTORICAL_CROSS_SECTION_RESEARCH_RESULTS",
            "BASIS_CFTC_MACRO_CALENDAR_NEWS_SENTIMENT_ONCHAIN_ADMISSION",
            "STAGE1_SUBSTRATE_REPAIR",
            "ASSET_UNIVERSE_EXPANSION_OF_THE_PREDICTION_TARGET",
            "FUTURE_SURVIVAL_FILTER_OR_WHOLE_SAMPLE_PARTICIPATION_THRESHOLD",
            "INVERSION_OR_NEGATION_OF_PREVIOUS_24H_SIGN_PERSISTENCE",
        ],
        "boundaries": {
            "additional_information_family": False,
            "post_cutoff_market_data": False,
            "sealed_queries": 0,
            "champion_created": False,
            "real_money": False,
        },
    }


def specification(model_version: str) -> dict[str, Any]:
    """The executed configuration, exactly as preregistered."""
    if model_version not in EXPERIMENT_IDS:
        raise ExperimentError(f"unknown Stage-3 cross-asset configuration: {model_version}")
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
        "calibration_split_fraction": CALIBRATION_SPLIT_FRACTION,
        "calibration_embargo_hours": CALIBRATION_EMBARGO_HOURS,
        "calibration_rows": "TRAINING_ONLY",
        "decision_rule": "DECLARE_UP_WHEN_CALIBRATED_P_UP_GREATER_OR_EQUAL_0_5_TIES_UP",
        "probability_rule": "EXPOSE_P_DECLARED_DIRECTION_CORRECT",
        "probability_threshold_searched": False,
        "hyperparameter_search": False,
        "abstention_only_on_source_or_feature_validity": True,
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
    return record


def included_folds(root: Path = ROOT) -> list[str]:
    """The source-admissible folds, read from the pre-result audit, never chosen here."""
    return list(_audit(root)["coverage"]["admissible_folds"])


def required_non_negative_folds(fold_count: int) -> int:
    return math.ceil(2 / 3 * fold_count)


def preregistration(model_version: str, root: Path = ROOT) -> dict[str, Any]:
    """The frozen hypothesis, design, inference plan and advancement gate for one candidate."""
    if model_version not in EXPERIMENT_IDS:
        raise ExperimentError(f"unknown Stage-3 cross-asset configuration: {model_version}")
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
            "Contemporaneous, point-in-time crypto-market breadth available at the BTC "
            "hourly decision instant contains out-of-sample information about the frozen "
            "BTCUSDT spot 24h terminal direction beyond an information-free chronological "
            "base-rate control."
        ),
        "hypothesis_class": "MATERIAL_PREDICTIVE_HYPOTHESIS",
        "model_version": model_version,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "baseline_protocol": BASELINE_PROTOCOL_PATH,
        "source_roadmap_stage": SOURCE_ROADMAP_STAGE,
        "source_roadmap_family": ROADMAP_FAMILY,
        "director_decisions": director_decisions(),
        "target": {
            "symbol": TARGET_SYMBOL,
            "market": "crypto_spot",
            "canonical_resolution": "1m",
            "decision_cadence": "1h",
            "horizon_hours": HORIZON_HOURS,
            "label": "r_24h = log(close[T + 24h] / close[T])",
            "path_dependent": False,
            "cross_assets_are_context_only": True,
            "additional_prediction_target_created": False,
        },
        "source": {
            "manifest": MANIFEST_PATH,
            "predictive_contract": CONTRACT_PATH,
            "source_audit": AUDIT_PATH,
            "source_audit_status": audit["status"],
            "target_symbol_excluded_from_cross_section": True,
            "required_endpoint_bars": REQUIRED_ENDPOINT_BARS,
            "endpoint_offsets_hours": list(ENDPOINT_OFFSET_HOURS),
            "minimum_point_in_time_universe": MINIMUM_POINT_IN_TIME_UNIVERSE,
            "universe_recomputed_point_in_time": True,
            "future_survival_filter": False,
            "whole_sample_participation_threshold": False,
            "retired_504_row_participation_rule_revived": False,
            "cross_sectional_weighting": CROSS_SECTIONAL_WEIGHTING,
            "interpolation": False,
            "forward_fill": False,
            "nearest_bar_substitution": False,
            "historical_cross_section_results_imported": False,
        },
        "features": {
            "version": FEATURE_SET_VERSION,
            "count": FEATURE_COUNT,
            "ordered_names": list(FEATURE_NAMES),
            "unavailability_taxonomy": list(UNAVAILABILITY_TAXONOMY),
            "unavailable_evaluation_row": "NEUTRAL_UNCERTAIN_ABSTENTION_COUNTED",
            "unavailable_training_row": "EXCLUDED_FROM_FITTING_COUNTED",
            "rejected_family_features_combined": False,
            "btc_price_or_return_feature_present": False,
            "universe_size_is_a_feature": False,
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
                "minimum_eligible_timestamps": MINIMUM_ELIGIBLE_TIMESTAMPS,
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
            "POINT_IN_TIME_UNIVERSE_ACCOUNTING",
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
        },
        "boundaries": {
            "prediction_target_universe_expanded": False,
            "additional_information_family": False,
            "combined_with_rejected_families": False,
            "stage1_substrate_repair": False,
            "post_cutoff_market_data": False,
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
        raise ExperimentError("the predictive cross-asset contract must exist before execution")
    missing = [name for name in IMPLEMENTATION_FILES if not (root / name).is_file()]
    if missing:
        raise ExperimentError(f"the implementation is incomplete: {missing}")
    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_PRE_EXECUTION_ADMISSION_V1",
        "checkpoint": CHECKPOINT,
        "family": FAMILY,
        "status": "PASS",
        "search_plan": SEARCH_PLAN_PATH,
        "search_plan_sha256": content_hash(plan_path),
        "preregistration_sha256": preregistrations,
        "predictive_contract": CONTRACT_PATH,
        "predictive_contract_sha256": content_hash(root / CONTRACT_PATH),
        "source_audit": AUDIT_PATH,
        "source_audit_sha256": content_hash(audit_path),
        "source_audit_status": audit["status"],
        "included_folds": list(audit["coverage"]["admissible_folds"]),
        "source": source_identity(root),
        "implementation_sha256": {name: content_hash(root / name) for name in IMPLEMENTATION_FILES},
        "director_decisions": director_decisions(),
        "feature_set_version": FEATURE_SET_VERSION,
        "feature_count": FEATURE_COUNT,
        "paired_bootstrap_seed": PAIRED_SEED,
        "family_configurations_planned": FAMILY_SIZE,
        "family_configurations_consumed_before_this_run": 0,
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
    panel: CrossSectionPanel, labels: Sequence[Label]
) -> tuple[dict[int, tuple[float, ...]], dict[str, int]]:
    return availability_map(panel, [label.open_time for label in labels])


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
    by_time = dict(
        zip(
            [label.open_time for label in available],
            probabilities,
            strict=True,
        )
    )

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
        "note": "SIX_FOLD_FULL_UNIVERSE_NOT_THE_CROSS_ASSET_ADMISSIBLE_UNIVERSE",
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


def universe_accounting(panel: CrossSectionPanel, folds: Sequence[Fold]) -> dict[str, Any]:
    """Point-in-time universe sizes over the included evaluation timestamps. Never a feature."""
    from .cross_asset_source import point_in_time_universe_size

    sizes = [
        point_in_time_universe_size(panel, label.open_time)
        for fold in folds
        for label in fold.evaluation
    ]
    ordered = sorted(sizes)
    middle = len(ordered) // 2
    median = (
        0
        if not ordered
        else (ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) // 2)
    )
    return {
        "panel_symbols": len(panel.symbols),
        "evaluation_timestamps_measured": len(ordered),
        "minimum_point_in_time_universe_observed": min(ordered, default=0),
        "median_point_in_time_universe": median,
        "maximum_point_in_time_universe_observed": max(ordered, default=0),
        "minimum_required": MINIMUM_POINT_IN_TIME_UNIVERSE,
        "universe_size_is_a_model_feature": False,
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

    panel = load_cross_section(root)
    cache, unavailability = _feature_cache(panel, label_set.labels)

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
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "search_plan": SEARCH_PLAN_PATH,
        "admission": ADMISSION_PATH,
        "source_audit": AUDIT_PATH,
        "source_audit_status": audit["status"],
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
            "count": FEATURE_COUNT,
            "ordered_names": list(FEATURE_NAMES),
            "available_vectors": len(cache),
            "unavailable_vectors": sum(unavailability.values()),
            "unavailability_by_reason": unavailability,
            "btc_price_or_return_feature_present": False,
            "combined_with_rejected_families": False,
            "universe_size_is_a_feature": False,
            "clipping_winsorization_or_rank_transform": False,
            "feature_selection": False,
        },
        "point_in_time_universe": universe_accounting(panel, folds),
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
            "magnitude_declared": False,
        },
        "boundaries": {
            "prediction_target_universe_expanded": False,
            "additional_information_family": False,
            "combined_with_rejected_families": False,
            "historical_cross_section_results_imported": False,
            "future_survival_filter": False,
            "whole_sample_participation_threshold": False,
            "stage1_substrate_repair": False,
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
    "LINEAR_DIRECTION_PARAMETERS",
    "LINEAR_MODEL_VERSION",
    "MATCHED_CONTROL",
    "MINIMUM_IMPORTANT_EFFECT",
    "NOT_ELIGIBLE",
    "NO_ADVANCE",
    "PAIRED_SEED",
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
    "required_non_negative_folds",
    "result_path",
    "run_experiment",
    "search_plan",
    "specification",
    "trials_path",
    "universe_accounting",
]
