"""`PREDICTIVE-INTERNAL-STRUCTURE-V1` — the first result-bearing predictive experiment.

One preregistered candidate, `INTERNAL_LINEAR_DUAL_HEAD_V1`, fitted only on the
chronological training portion of each frozen outer fold and scored by
`PREDICTIVE_EVALUATION_CONTRACT_V1` (Amendment A1) against the matched `ALWAYS_UP` control.

The scientific design is frozen by the Research Director and is not reinterpreted here.
This module implements it, proves the no-peek ordering with content hashes, and emits the
result. It searches nothing, tunes nothing and promotes nothing.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import ABSTAIN, DOWN, HORIZON_HOURS, NEUTRAL, UP
from .baselines import ALWAYS_UP
from .evaluation import (
    BLOCK_LENGTH_HOURS,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    RELIABILITY_BIN_EDGES,
    Outcome,
    Prediction,
    score,
)
from .folds import FOLD_BOUNDARIES, FOLD_DESIGN, PURGE_EMBARGO_HOURS, Fold, build_folds
from .folds import assert_no_boundary_leak as assert_no_fold_leak
from .internal_features import (
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    MAX_LOOKBACK_HOURS,
    REQUIRED_BARS,
    UNAVAILABILITY_TAXONOMY,
    ZERO_EFFICIENCY_DENOMINATOR_VALUE,
    ZERO_RANGE_CLOSE_POSITION_VALUE,
    OhlcvBar,
    build_feature_vector,
    index_ohlcv,
    load_hourly_ohlcv,
)
from .internal_model import (
    HGBR_MODEL_VERSION,
    LINEAR_MODEL_VERSION,
    MODEL_FAMILY,
    SKLEARN_VERSION,
    declared_direction,
    declared_probability,
    fit_direction_head,
    fit_magnitude_head,
    linear_specification,
    reserved_hgbr_specification,
)
from .labels import Bar, Label, build_labels
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

CHECKPOINT = "PREDICTIVE-INTERNAL-STRUCTURE-V1"
EXPERIMENT_ID = "EXP-PRED-001-INTERNAL-LINEAR-DUAL-HEAD"
RESERVED_EXPERIMENT_ID = "EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD"
HYPOTHESIS_ID = "H-PRED-INT-001"
RESEARCH_GENERATION = "PREDICTIVE_RESEARCH_GENERATION_V1"
EVALUATION_CONTRACT = "docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md"
EVALUATION_CONTRACT_AMENDMENT = "A1"
SOURCE_ROADMAP_STAGE = "STAGE_1_INTERNAL_MARKET_STRUCTURE"

SEARCH_PLAN_PATH = "research/protocols/PREDICTIVE-STAGE1-INTERNAL-SEARCH-PLAN-V1.json"
PREREGISTRATION_PATH = f"research/experiments/{EXPERIMENT_ID}/preregistration.json"
RESULT_PATH = f"research/experiments/{EXPERIMENT_ID}/result.json"
ADMISSION_PATH = "reports/validation/PREDICTIVE-INTERNAL-STRUCTURE-V1-ADMISSION.json"
REPORT_JSON_PATH = "reports/research/PREDICTIVE-INTERNAL-STRUCTURE-V1.json"
REPORT_MARKDOWN_PATH = "reports/research/PREDICTIVE-INTERNAL-STRUCTURE-V1.md"
BASELINE_REPORT_PATH = "reports/research/PREDICTIVE-BASELINES-V1.json"
BASELINE_PROTOCOL_PATH = "research/protocols/PREDICTIVE-BASELINES-V1.json"

CREATED_AT = "2026-09-16T00:00:00Z"

MINIMUM_IMPORTANT_EFFECT = 0.015
FAMILYWISE_ALPHA = 0.05
CANDIDATE_ALPHA = 0.025
POOLED_COVERAGE_GATE = 0.95
FOLD_COVERAGE_GATE = 0.90
MINIMUM_NON_NEGATIVE_FOLDS = 4
OUTER_FOLDS = len(FOLD_BOUNDARIES)

STAGE1_FAMILY_SIZE = 2
STAGE1_CONFIGURATIONS = (LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION)

ADVANCE = "ADVANCE_INTERNAL_LINEAR_V1"
NO_ADVANCE = "NO_ADVANCE_INTERNAL_LINEAR_V1"

# Every file whose bytes define the executed procedure. The admission artifact freezes
# these hashes before the first outer-evaluation number exists.
IMPLEMENTATION_FILES = (
    "backend/app/predictive/__init__.py",
    "backend/app/predictive/evaluation.py",
    "backend/app/predictive/folds.py",
    "backend/app/predictive/internal_features.py",
    "backend/app/predictive/internal_model.py",
    "backend/app/predictive/internal_structure.py",
    "backend/app/predictive/labels.py",
    "backend/app/predictive/paired_inference.py",
    "scripts/run_predictive_internal_structure.py",
)

GATE_NAMES = (
    "POOLED_COVERAGE_AT_LEAST_0_95",
    "EVERY_FOLD_COVERAGE_AT_LEAST_0_90",
    "POOLED_MATCHED_DELTA_AT_LEAST_MESI",
    "PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO",
    "AT_LEAST_4_OF_6_FOLD_DELTAS_NON_NEGATIVE",
)


class ExperimentError(RuntimeError):
    """The frozen experiment cannot be executed or replayed as preregistered."""


def content_hash(path: Path) -> str:
    """Line-ending-insensitive content hash, so a checkout on Windows agrees with CI."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def payload_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


# --------------------------------------------------------------------------------------
# Frozen records: the Stage-1 search plan and the experiment preregistration.
# --------------------------------------------------------------------------------------


def search_plan() -> dict[str, Any]:
    """The Stage-1 model family, frozen before any candidate result is observed."""
    return {
        "version": "PREDICTIVE_STAGE1_INTERNAL_SEARCH_PLAN_V1",
        "status": "FROZEN_BEFORE_OBSERVATION",
        "checkpoint": CHECKPOINT,
        "research_generation": RESEARCH_GENERATION,
        "family": MODEL_FAMILY,
        "source_roadmap_stage": SOURCE_ROADMAP_STAGE,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "baseline_protocol": BASELINE_PROTOCOL_PATH,
        "purpose": (
            "Freeze the complete Stage-1 internal model family before the first "
            "configuration is executed, so neither configuration can be influenced by the "
            "other's result."
        ),
        "family_size": STAGE1_FAMILY_SIZE,
        "configurations": [
            {
                "model_version": LINEAR_MODEL_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "order": 1,
                "executed_in_checkpoint": CHECKPOINT,
                "specification": linear_specification(),
            },
            {
                "model_version": HGBR_MODEL_VERSION,
                "experiment_id": RESERVED_EXPERIMENT_ID,
                "order": 2,
                "executed_in_checkpoint": None,
                "scheduling_rule": (
                    "Scheduled for the next checkpoint and executed regardless of the "
                    "linear result, unless an integrity or software defect blocks it."
                ),
                "specification": reserved_hgbr_specification(),
            },
        ],
        "multiplicity": {
            "familywise_alpha": FAMILYWISE_ALPHA,
            "correction": "BONFERRONI",
            "per_configuration_alpha": CANDIDATE_ALPHA,
            "interval_mass_per_configuration": 1.0 - CANDIDATE_ALPHA,
        },
        "budget": {
            "planned_model_configurations": STAGE1_FAMILY_SIZE,
            "consumed_by_this_checkpoint": 1,
            "remaining_after_this_checkpoint": 1,
        },
        "forbidden": [
            "THIRD_STAGE1_MODEL_FAMILY",
            "PARAMETER_RESCUE",
            "THRESHOLD_RESCUE",
            "FEATURE_REDESIGN",
            "POST_RESULT_DESCENDANT_OF_A_FAILED_CONFIGURATION",
            "INVERSION_OR_NEGATION_OF_PREVIOUS_24H_SIGN_PERSISTENCE",
        ],
        "boundaries": {
            "external_information_family": False,
            "post_cutoff_market_data": False,
            "sealed_queries": 0,
            "champion_created": False,
            "real_money": False,
        },
    }


def preregistration() -> dict[str, Any]:
    """The frozen hypothesis, design, inference plan and advancement gate."""
    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_EXPERIMENT_PREREGISTRATION_V1",
        "experiment_id": EXPERIMENT_ID,
        "experiment_version": 1,
        "created_at_utc": CREATED_AT,
        "status": "PREREGISTERED",
        "checkpoint": CHECKPOINT,
        "research_generation": RESEARCH_GENERATION,
        "search_plan": SEARCH_PLAN_PATH,
        "family": MODEL_FAMILY,
        "hypothesis_id": HYPOTHESIS_ID,
        "hypothesis": (
            "A fixed, causal, low-complexity predictor using only BTCUSDT's own price, "
            "volume and volatility history contains directional information about the "
            "frozen 24h terminal target beyond the ALWAYS_UP baseline."
        ),
        "hypothesis_class": "MATERIAL_PREDICTIVE_HYPOTHESIS",
        "model_version": LINEAR_MODEL_VERSION,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "baseline_protocol": BASELINE_PROTOCOL_PATH,
        "source_roadmap_stage": SOURCE_ROADMAP_STAGE,
        "target": {
            "symbol": "BTCUSDT",
            "market": "crypto_spot",
            "canonical_resolution": "1m",
            "decision_cadence": "1h",
            "horizon_hours": HORIZON_HOURS,
            "label": "r_24h = log(close[T + 24h] / close[T])",
            "path_dependent": False,
        },
        "features": {
            "version": FEATURE_SET_VERSION,
            "count": len(FEATURE_NAMES),
            "ordered_names": list(FEATURE_NAMES),
            "information_family": "INTERNAL_BTCUSDT_PRICE_VOLUME_VOLATILITY_ONLY",
            "maximum_lookback_hours": MAX_LOOKBACK_HOURS,
            "required_contiguous_complete_bars": REQUIRED_BARS,
            "window_convention": (
                "The last N hourly returns ending at T are x_{T-N+1h}..x_T, so they read "
                "the closes c_{T-N}..c_T. The last N hours of bars are the bars "
                "T-(N-1)h..T inclusive of the decision bar."
            ),
            "edge_rules": {
                "zero_efficiency_denominator_value": ZERO_EFFICIENCY_DENOMINATOR_VALUE,
                "zero_rolling_range_close_position_value": ZERO_RANGE_CLOSE_POSITION_VALUE,
                "unavailability_taxonomy": list(UNAVAILABILITY_TAXONOMY),
                "interpolation": False,
                "forward_fill": False,
                "backward_fill": False,
                "median_fill": False,
                "nearest_bar_substitution": False,
            },
            "unavailable_evaluation_row": "NEUTRAL_UNCERTAIN_ABSTENTION_COUNTED",
            "unavailable_training_row": "EXCLUDED_FROM_FITTING_COUNTED",
            "causality": "NO_BAR_WITH_OPEN_TIME_AFTER_T_MAY_ENTER_A_FEATURE",
        },
        "model": linear_specification(),
        "reserved_configuration": reserved_hgbr_specification(),
        "evaluation_design": {
            "design": FOLD_DESIGN,
            "random_k_fold": False,
            "outer_folds": OUTER_FOLDS,
            "fold_boundaries": [
                {"fold": name, "start": start, "end": end} for name, start, end in FOLD_BOUNDARIES
            ],
            "purge_embargo_hours": PURGE_EMBARGO_HOURS,
            "folds_recut": False,
            "eligible_universe": "UNCHANGED_FROM_PREDICTIVE_BASELINES_V1",
            "coverage_policy": (
                "Candidate feature unavailability is represented as a counted abstention. "
                "Eligible timestamps are never deleted from a denominator."
            ),
            "outer_evaluation_used_in_fitting": False,
        },
        "primary_effect": {
            "definition": (
                "candidate actionable directional win rate - matched ALWAYS_UP win rate, "
                "on the exact timestamps where the candidate makes an actionable "
                "directional prediction"
            ),
            "matched_control": ALWAYS_UP,
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
            "BASELINE_COMPARISONS",
        ],
        "reliability_bin_edges": list(RELIABILITY_BIN_EDGES),
        "advancement_gate": {
            "all_must_hold": True,
            "conditions": [
                {"name": GATE_NAMES[0], "threshold": POOLED_COVERAGE_GATE},
                {"name": GATE_NAMES[1], "threshold": FOLD_COVERAGE_GATE},
                {"name": GATE_NAMES[2], "threshold": MINIMUM_IMPORTANT_EFFECT},
                {"name": GATE_NAMES[3], "threshold": 0.0},
                {"name": GATE_NAMES[4], "threshold": MINIMUM_NON_NEGATIVE_FOLDS},
            ],
            "pass_classification": ADVANCE,
            "fail_classification": NO_ADVANCE,
            "secondary_metrics_may_rescue_primary_gate": False,
            "post_result_tuning_authorized": False,
        },
        "budget": {
            "stage1_configurations_planned": STAGE1_FAMILY_SIZE,
            "stage1_configurations_consumed_by_this_experiment": 1,
            "hyperparameter_search": False,
            "threshold_search": False,
            "feature_search": False,
        },
        "boundaries": {
            "external_information_family": False,
            "post_cutoff_market_data": False,
            "sealed_queries": 0,
            "champion_created": False,
            "real_money": False,
            "baselines_v1_results_changed": False,
            "historical_terminal_classifications_changed": False,
            "previous_24h_sign_persistence_inverted": False,
        },
    }


def admission(root: Path = ROOT) -> dict[str, Any]:
    """Prove the frozen records and the implementation exist before any market result."""
    plan_path, prereg_path = root / SEARCH_PLAN_PATH, root / PREREGISTRATION_PATH
    if not plan_path.is_file() or not prereg_path.is_file():
        raise ExperimentError("the frozen records must exist before the admission gate")
    if json.loads(plan_path.read_text(encoding="utf-8")) != search_plan():
        raise ExperimentError("the committed search plan is not what the code declares")
    if json.loads(prereg_path.read_text(encoding="utf-8")) != preregistration():
        raise ExperimentError("the committed preregistration is not what the code declares")
    missing = [name for name in IMPLEMENTATION_FILES if not (root / name).is_file()]
    if missing:
        raise ExperimentError(f"the implementation is incomplete: {missing}")
    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_PRE_EXECUTION_ADMISSION_V1",
        "checkpoint": CHECKPOINT,
        "experiment_id": EXPERIMENT_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "model_version": LINEAR_MODEL_VERSION,
        "status": "PASS",
        "search_plan": SEARCH_PLAN_PATH,
        "search_plan_sha256": content_hash(plan_path),
        "preregistration": PREREGISTRATION_PATH,
        "preregistration_sha256": content_hash(prereg_path),
        "implementation_sha256": {name: content_hash(root / name) for name in IMPLEMENTATION_FILES},
        "feature_set_version": FEATURE_SET_VERSION,
        "feature_count": len(FEATURE_NAMES),
        "sklearn_version": SKLEARN_VERSION,
        "stage1_configurations_planned": STAGE1_FAMILY_SIZE,
        "stage1_configurations_consumed_before_this_run": 0,
        "reserved_configuration": HGBR_MODEL_VERSION,
        "reserved_configuration_executed": False,
        "market_results_observed": 0,
        "model_fits_executed": 0,
        "post_cutoff_access": 0,
        "sealed_queries": 0,
        "champion_status": "NONE",
        "real_money": False,
    }


def admission_identity(root: Path = ROOT) -> str:
    """One hash binding the frozen records and the implementation into a single identity."""
    record = admission(root)
    return payload_hash(
        {
            "search_plan_sha256": record["search_plan_sha256"],
            "preregistration_sha256": record["preregistration_sha256"],
            "implementation_sha256": record["implementation_sha256"],
        }
    )


# --------------------------------------------------------------------------------------
# Execution.
# --------------------------------------------------------------------------------------


def _label_bars(bars: Sequence[OhlcvBar]) -> tuple[Bar, ...]:
    return tuple(
        Bar(open_time=bar.open_time, close=bar.close, complete=bar.complete) for bar in bars
    )


def _feature_cache(
    bars_by_open: Mapping[int, OhlcvBar], labels: Sequence[Label]
) -> tuple[dict[int, tuple[float, ...]], dict[str, int]]:
    """Build every causal vector once. Unavailability is typed and counted, never filled."""
    available: dict[int, tuple[float, ...]] = {}
    reasons = dict.fromkeys(UNAVAILABILITY_TAXONOMY, 0)
    for label in labels:
        values, reason = build_feature_vector(bars_by_open, label.open_time)
        if values is None:
            reasons[str(reason)] += 1
            continue
        available[label.open_time] = values
    return available, reasons


def _outcomes(labels: Sequence[Label]) -> list[Outcome]:
    return [
        Outcome(open_time=label.open_time, r_24h=label.r_24h, direction=label.direction)
        for label in labels
    ]


def _fold_predictions(
    fold: Fold, cache: Mapping[int, tuple[float, ...]]
) -> tuple[dict[str, Any], list[Prediction], list[Prediction]]:
    """Fit the frozen heads on this fold's training portion and predict its evaluation.

    Returns the fit record, the directional predictions over the whole eligible universe,
    and the magnitude predictions over the feature-available subset of it.
    """
    training = [label for label in fold.training if label.open_time in cache]
    if not training:
        raise ExperimentError(f"{fold.name}: no feature-valid training row")
    directional = [label for label in training if label.direction in {UP, DOWN}]
    if len(directional) != len(training):
        excluded_neutral = len(training) - len(directional)
    else:
        excluded_neutral = 0

    direction_head = fit_direction_head(
        [label.open_time for label in directional],
        [cache[label.open_time] for label in directional],
        [label.direction for label in directional],
    )
    magnitude_head = fit_magnitude_head(
        [cache[label.open_time] for label in training],
        [label.r_24h for label in training],
    )

    evaluation_available = [label for label in fold.evaluation if label.open_time in cache]
    matrix = [cache[label.open_time] for label in evaluation_available]
    probabilities = direction_head.probability_up(matrix) if matrix else []
    expected = magnitude_head.expected_return(matrix) if matrix else []
    strengths = magnitude_head.strength(expected) if matrix else []

    by_time = {
        label.open_time: (probability, predicted, strength)
        for label, probability, predicted, strength in zip(
            evaluation_available, probabilities, expected, strengths, strict=True
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
                open_time=label.open_time,
                direction=ABSTAIN,
                expected_return=predicted_return,
            )
        )

    split = direction_head.split
    fit_record = {
        "training_labels": len(fold.training),
        "training_rows_feature_valid": len(training),
        "training_rows_feature_unavailable": len(fold.training) - len(training),
        "training_rows_neutral_excluded_from_direction": excluded_neutral,
        "direction_base_fit_rows": split.base_fit_rows,
        "direction_calibration_rows": split.calibration_rows,
        "direction_rows_dropped_to_calibration_embargo": split.dropped_to_embargo,
        "calibration_boundary_open_time": split.boundary_open_time,
        "calibration_boundary_index": split.boundary_index,
        "magnitude_training_rows": magnitude_head.training_rows,
        "strength_reference_rows": magnitude_head.training_rows,
        "evaluation_rows_feature_valid": len(evaluation_available),
        "evaluation_rows_feature_unavailable": len(fold.evaluation) - len(evaluation_available),
        "model_fits": {"direction_base": 1, "direction_calibration": 1, "magnitude": 1},
    }
    return fit_record, directional_predictions, magnitude_predictions


def _matched_records(
    predictions: Sequence[Prediction], labels: Sequence[Label]
) -> list[PairedRecord]:
    """Candidate-actionable, non-NEUTRAL records scored both ways on identical timestamps."""
    truth = {label.open_time: label for label in labels}
    records: list[PairedRecord] = []
    for prediction in sorted(predictions, key=lambda item: item.open_time):
        outcome = truth[prediction.open_time]
        if prediction.direction not in {UP, DOWN} or outcome.direction == NEUTRAL:
            continue
        records.append(
            PairedRecord(
                open_time=prediction.open_time,
                candidate_correct=prediction.direction == outcome.direction,
                baseline_correct=outcome.direction == UP,
            )
        )
    return records


def _matched_summary(records: Sequence[PairedRecord], eligible: int) -> dict[str, Any]:
    total = len(records)
    candidate = sum(1 for record in records if record.candidate_correct)
    baseline = sum(1 for record in records if record.baseline_correct)
    return {
        "matched_control": ALWAYS_UP,
        "paired_records": total,
        "candidate_win_rate": (candidate / total) if total else None,
        "matched_always_up_win_rate": (baseline / total) if total else None,
        "delta": ((candidate - baseline) / total) if total else None,
        "matched_universe_share_of_eligible": (total / eligible) if eligible else None,
    }


def advancement_gate(
    pooled_coverage: float,
    fold_coverage: Mapping[str, float],
    pooled_delta: float,
    interval: Sequence[float],
    fold_deltas: Mapping[str, float],
) -> dict[str, Any]:
    """The five predeclared conditions. All must hold; none may be rescued by a companion."""
    non_negative = sum(1 for value in fold_deltas.values() if value >= 0.0)
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
            "threshold": MINIMUM_NON_NEGATIVE_FOLDS,
            "observed": non_negative,
            "passed": non_negative >= MINIMUM_NON_NEGATIVE_FOLDS,
        },
    }
    failed = [name for name, record in conditions.items() if not record["passed"]]
    return {
        "all_must_hold": True,
        "conditions": conditions,
        "failed_conditions": failed,
        "terminal_classification": NO_ADVANCE if failed else ADVANCE,
        "secondary_metrics_used_to_rescue": False,
    }


def baseline_context(root: Path = ROOT) -> dict[str, Any]:
    """The canonical full-universe baselines from PREDICTIVE-BASELINES-V1, unchanged."""
    report = json.loads((root / BASELINE_REPORT_PATH).read_text(encoding="utf-8"))
    baselines = report["baselines"]
    return {
        "source": BASELINE_REPORT_PATH,
        "classification": report["classification"],
        "eligible_decision_timestamps": report["folds"]["eligible_decision_timestamps"],
        "pooled": {
            name: {
                "win_rate": record["pooled"]["win_rate"],
                "coverage": record["pooled"]["coverage"],
            }
            for name, record in baselines.items()
        },
        "always_up_by_fold": {
            name: {"win_rate": record["win_rate"], "coverage": record["coverage"]}
            for name, record in baselines[ALWAYS_UP]["by_fold"].items()
        },
        "reference_bar": baselines[ALWAYS_UP]["pooled"]["win_rate"],
        "results_changed": False,
    }


def run_experiment(root: Path = ROOT, bars: Sequence[OhlcvBar] | None = None) -> dict[str, Any]:
    """Execute the frozen experiment once and emit the complete contract report."""
    resolved = tuple(bars) if bars is not None else load_hourly_ohlcv(root)
    bars_by_open = index_ohlcv(resolved)
    label_set = build_labels(_label_bars(resolved), horizon_hours=HORIZON_HOURS)
    fold_set = build_folds(
        label_set.labels, horizon_hours=HORIZON_HOURS, purge_embargo_hours=PURGE_EMBARGO_HOURS
    )
    assert_no_fold_leak(fold_set)
    cache, unavailability = _feature_cache(bars_by_open, label_set.labels)

    by_fold: dict[str, Any] = {}
    pooled_directional: list[Prediction] = []
    pooled_magnitude: list[Prediction] = []
    pooled_labels: list[Label] = []
    pooled_magnitude_labels: list[Label] = []
    paired_folds = []
    fold_coverage: dict[str, float] = {}
    fold_deltas: dict[str, float] = {}
    fits = {"direction_base": 0, "direction_calibration": 0, "magnitude": 0}

    for fold in fold_set.folds:
        fit_record, directional, magnitude = _fold_predictions(fold, cache)
        for key in fits:
            fits[key] += fit_record["model_fits"][key]
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
        records = _matched_records(directional, fold.evaluation)
        matched = _matched_summary(records, len(fold.evaluation))
        paired_folds.append(
            build_paired_fold(fold.name, [label.open_time for label in fold.evaluation], records)
        )
        coverage = directional_score["coverage"]
        if coverage is None or matched["delta"] is None:
            raise ExperimentError(f"{fold.name}: the fold produced no scorable prediction")
        fold_coverage[fold.name] = float(coverage)
        fold_deltas[fold.name] = float(matched["delta"])
        by_fold[fold.name] = {
            "fit": fit_record,
            "directional": directional_score,
            "magnitude": magnitude_score,
            "magnitude_universe": {
                "eligible_decision_timestamps": len(fold.evaluation),
                "feature_available_rows_scored": len(magnitude_labels),
                "abstained_rows_excluded_and_counted": len(fold.evaluation) - len(magnitude_labels),
            },
            "matched_baseline": matched,
        }
        pooled_directional.extend(directional)
        pooled_magnitude.extend(magnitude)
        pooled_labels.extend(fold.evaluation)
        pooled_magnitude_labels.extend(magnitude_labels)

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
    pooled_records = [record for fold in paired_folds for record in fold.records]
    pooled_matched = _matched_summary(pooled_records, len(pooled_labels))
    paired = paired_delta_interval(paired_folds)
    pooled_coverage = float(pooled_directional_score["coverage"])
    gate = advancement_gate(
        pooled_coverage,
        fold_coverage,
        float(pooled_matched["delta"]),
        paired["interval"],
        fold_deltas,
    )

    return {
        "version": CHECKPOINT,
        "classification": "PREDICTIVE_EXPERIMENT_RESULT",
        "experiment_id": EXPERIMENT_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "model_version": LINEAR_MODEL_VERSION,
        "research_generation": RESEARCH_GENERATION,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "preregistration": PREREGISTRATION_PATH,
        "search_plan": SEARCH_PLAN_PATH,
        "admission": ADMISSION_PATH,
        "labels": label_set.accounting(),
        "folds": {
            "design": FOLD_DESIGN,
            "random_k_fold": False,
            "purge_embargo_hours": PURGE_EMBARGO_HOURS,
            "eligible_decision_timestamps": fold_set.eligible_total(),
            "admissible_not_assigned": fold_set.unassigned,
            "recut": False,
        },
        "features": {
            "version": FEATURE_SET_VERSION,
            "count": len(FEATURE_NAMES),
            "ordered_names": list(FEATURE_NAMES),
            "available_vectors": len(cache),
            "unavailable_vectors": sum(unavailability.values()),
            "unavailability_by_reason": unavailability,
        },
        "model": linear_specification(),
        "reserved_configuration": reserved_hgbr_specification(),
        "model_fits": {**fits, "total": sum(fits.values())},
        "candidate": {
            "pooled_directional": pooled_directional_score,
            "pooled_magnitude": pooled_magnitude_score,
            "pooled_magnitude_universe": {
                "eligible_decision_timestamps": len(pooled_labels),
                "feature_available_rows_scored": len(pooled_magnitude_labels),
                "abstained_rows_excluded_and_counted": len(pooled_labels)
                - len(pooled_magnitude_labels),
            },
            "by_fold": by_fold,
        },
        "primary_comparison": {
            "definition": (
                "candidate actionable directional win rate - matched ALWAYS_UP win rate "
                "on candidate-actionable, non-NEUTRAL timestamps"
            ),
            "pooled": pooled_matched,
            "by_fold": {name: by_fold[name]["matched_baseline"] for name in by_fold},
            "fold_deltas": fold_deltas,
            "fold_coverage": fold_coverage,
            "minimum_important_effect": MINIMUM_IMPORTANT_EFFECT,
            "paired_interval": paired,
        },
        "baseline_context": baseline_context(root),
        "advancement_gate": gate,
        "terminal_classification": gate["terminal_classification"],
        "search_budget": {
            "family": MODEL_FAMILY,
            "stage1_configurations_planned": STAGE1_FAMILY_SIZE,
            "stage1_configurations_consumed": 1,
            "stage1_configurations_remaining": STAGE1_FAMILY_SIZE - 1,
            "configurations_executed": [LINEAR_MODEL_VERSION],
            "configurations_reserved": [HGBR_MODEL_VERSION],
            "hyperparameter_search": False,
            "threshold_search": False,
            "feature_search": False,
            "result_dependent_forks": 0,
        },
        "scoring": {
            "reliability_bin_edges": list(RELIABILITY_BIN_EDGES),
            "win_rate_interval": {
                "method": "MOVING_BLOCK_BOOTSTRAP",
                "block_length_hours": BLOCK_LENGTH_HOURS,
                "replicates": BOOTSTRAP_REPLICATES,
                "seed": BOOTSTRAP_SEED,
            },
            "paired_interval": {
                "method": PAIRED_METHOD,
                "block_length_hours": PAIRED_BLOCK_LENGTH_HOURS,
                "replicates": PAIRED_REPLICATES,
                "seed": PAIRED_SEED,
                "alpha": PAIRED_ALPHA,
            },
        },
        "boundaries": {
            "external_information_family": False,
            "post_cutoff_market_data": False,
            "sealed_queries": 0,
            "champion_created": False,
            "real_money": False,
            "baselines_v1_results_changed": False,
            "historical_terminal_classifications_changed": False,
            "previous_24h_sign_persistence_inverted": False,
            "outer_evaluation_used_in_fitting": False,
            "post_result_tuning": False,
        },
    }


__all__ = [
    "ADMISSION_PATH",
    "ADVANCE",
    "CANDIDATE_ALPHA",
    "CHECKPOINT",
    "EXPERIMENT_ID",
    "FAMILYWISE_ALPHA",
    "FOLD_COVERAGE_GATE",
    "GATE_NAMES",
    "HYPOTHESIS_ID",
    "IMPLEMENTATION_FILES",
    "MINIMUM_IMPORTANT_EFFECT",
    "MINIMUM_NON_NEGATIVE_FOLDS",
    "NO_ADVANCE",
    "POOLED_COVERAGE_GATE",
    "PREREGISTRATION_PATH",
    "REPORT_JSON_PATH",
    "REPORT_MARKDOWN_PATH",
    "RESERVED_EXPERIMENT_ID",
    "RESULT_PATH",
    "SEARCH_PLAN_PATH",
    "STAGE1_CONFIGURATIONS",
    "STAGE1_FAMILY_SIZE",
    "ExperimentError",
    "admission",
    "admission_identity",
    "advancement_gate",
    "baseline_context",
    "canonical_bytes",
    "content_hash",
    "payload_hash",
    "preregistration",
    "run_experiment",
    "search_plan",
]
