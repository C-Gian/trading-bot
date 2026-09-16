"""`PREDICTIVE-INTERNAL-NONLINEAR-V1` — the reserved Stage-1 configuration.

`EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD` executes `INTERNAL_HGBR_DUAL_HEAD_V1` exactly as it
was frozen in commit `54dc831`, before the linear result existed. It consumes Stage-1
configuration 2 of 2 and closes `PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1`.

Every model-agnostic step — labels, folds, the feature cache, the frozen scorer, the matched
control and the paired inference — is imported from the executed linear checkpoint rather
than reimplemented, so the two configurations are provably scored by one procedure. The
imported names include a few module-private helpers; that is deliberate. Their bytes are
hashed by the executed `PREDICTIVE-INTERNAL-STRUCTURE-V1` admission artifact and cannot
change, so importing them is the strongest available guarantee that nothing was re-tuned
between the two configurations.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import ABSTAIN, DOWN, HORIZON_HOURS, UP
from .baselines import ALWAYS_UP
from .evaluation import RELIABILITY_BIN_EDGES, Prediction, score
from .folds import FOLD_BOUNDARIES, FOLD_DESIGN, PURGE_EMBARGO_HOURS, Fold, build_folds
from .folds import assert_no_boundary_leak as assert_no_fold_leak
from .internal_features import (
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    MAX_LOOKBACK_HOURS,
    REQUIRED_BARS,
    UNAVAILABILITY_TAXONOMY,
    OhlcvBar,
    index_ohlcv,
    load_hourly_ohlcv,
)
from .internal_model import (
    CALIBRATION_EMBARGO_HOURS,
    CALIBRATION_SPLIT_FRACTION,
    LINEAR_MODEL_VERSION,
    MODEL_FAMILY,
    SKLEARN_VERSION,
    declared_direction,
    declared_probability,
    reserved_hgbr_specification,
)
from .internal_nonlinear_model import (
    MODEL_VERSION,
    fit_direction_head,
    fit_magnitude_head,
    nonlinear_specification,
)
from .internal_structure import (
    CANDIDATE_ALPHA,
    FAMILYWISE_ALPHA,
    FOLD_COVERAGE_GATE,
    GATE_NAMES,
    MINIMUM_IMPORTANT_EFFECT,
    MINIMUM_NON_NEGATIVE_FOLDS,
    OUTER_FOLDS,
    POOLED_COVERAGE_GATE,
    SEARCH_PLAN_PATH,
    STAGE1_FAMILY_SIZE,
    ExperimentError,
    _feature_cache,
    _label_bars,
    _matched_records,
    _matched_summary,
    _outcomes,
    advancement_gate,
    baseline_context,
    canonical_bytes,
    content_hash,
    payload_hash,
)
from .internal_structure import (
    EXPERIMENT_ID as LINEAR_EXPERIMENT_ID,
)
from .internal_structure import (
    RESULT_PATH as LINEAR_RESULT_PATH,
)
from .labels import Label, build_labels
from .paired_inference import (
    PAIRED_ALPHA,
    PAIRED_BLOCK_LENGTH_HOURS,
    PAIRED_METHOD,
    PAIRED_REPLICATES,
    PAIRED_SEED,
    REPLICATE_CHUNK,
    build_paired_fold,
    paired_delta_interval,
)

ROOT = Path(__file__).resolve().parents[3]

CHECKPOINT = "PREDICTIVE-INTERNAL-NONLINEAR-V1"
EXPERIMENT_ID = "EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD"
HYPOTHESIS_ID = "H-PRED-INT-002"
RESEARCH_GENERATION = "PREDICTIVE_RESEARCH_GENERATION_V1"
EVALUATION_CONTRACT = "docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md"
EVALUATION_CONTRACT_AMENDMENT = "A1"
SOURCE_ROADMAP_STAGE = "STAGE_1_INTERNAL_MARKET_STRUCTURE"

PREREGISTRATION_PATH = f"research/experiments/{EXPERIMENT_ID}/preregistration.json"
RESULT_PATH = f"research/experiments/{EXPERIMENT_ID}/result.json"
ADMISSION_PATH = "reports/validation/PREDICTIVE-INTERNAL-NONLINEAR-V1-ADMISSION.json"
REPORT_JSON_PATH = "reports/research/PREDICTIVE-INTERNAL-NONLINEAR-V1.json"
REPORT_MARKDOWN_PATH = "reports/research/PREDICTIVE-INTERNAL-NONLINEAR-V1.md"
BASELINE_PROTOCOL_PATH = "research/protocols/PREDICTIVE-BASELINES-V1.json"

CREATED_AT = "2026-09-16T00:00:00Z"

ADVANCE = "ADVANCE_INTERNAL_HGBR_V1"
NO_ADVANCE = "NO_ADVANCE_INTERNAL_HGBR_V1"

STAGE1_FAMILY_CLOSED = "CLOSED_BOTH_PREDECLARED_CONFIGURATIONS_EXECUTED"

# Every file whose bytes define this execution. The linear implementation files are listed
# because this checkpoint runs on them unmodified; if any of them changed, the two Stage-1
# configurations would no longer share one procedure and the admission gate must fail.
IMPLEMENTATION_FILES = (
    "backend/app/predictive/__init__.py",
    "backend/app/predictive/evaluation.py",
    "backend/app/predictive/folds.py",
    "backend/app/predictive/internal_features.py",
    "backend/app/predictive/internal_model.py",
    "backend/app/predictive/internal_nonlinear.py",
    "backend/app/predictive/internal_nonlinear_model.py",
    "backend/app/predictive/internal_structure.py",
    "backend/app/predictive/labels.py",
    "backend/app/predictive/paired_inference.py",
    "scripts/run_predictive_internal_nonlinear.py",
)


def coverage_policy_decision() -> dict[str, Any]:
    """The Research Director's pre-execution coverage ruling, recorded before any number.

    The linear checkpoint established that the two coverage conditions cannot pass on this
    substrate: a single missing or incomplete canonical hourly bar invalidates the next 169
    decision instants, and the reserved configuration abstains on exactly the same
    timestamps because it inherits the feature-validity rules unchanged.

    The ruling does not weaken anything. The gates stay, they stay all-must-hold, and a
    directional result therefore cannot produce formal advancement while coverage fails.
    """
    return {
        "decision_id": "PREDICTIVE_STAGE1_COVERAGE_POLICY_V1",
        "decided_by": "RESEARCH_DIRECTOR",
        "decided_before_any_hgbr_outer_evaluation_number": True,
        "option_taken": "OPTION_1_EXECUTE_UNCHANGED",
        "options_offered": [
            "OPTION_1_EXECUTE_UNCHANGED",
            "OPTION_2_PREREGISTERED_COVERAGE_POLICY_AMENDMENT",
            "OPTION_3_REDESIGN_REQUIRED",
        ],
        "reserved_configuration_executed_exactly_as_frozen": True,
        "feature_set_identical_to_linear": True,
        "feature_validity_rules_identical_to_linear": True,
        "coverage_thresholds_changed": False,
        "coverage_gates_known_unpassable_before_execution": True,
        "reason_coverage_gates_cannot_pass": (
            "The candidate abstains on exactly the timestamps where the frozen 169-bar "
            "causal window cannot be constructed, which are the same timestamps the linear "
            "configuration abstained on."
        ),
        "gates_waived": False,
        "gates_reinterpreted": False,
        "gates_removed": False,
        "all_advancement_conditions_all_must_hold": True,
        "directional_result_may_rescue_formal_advancement": False,
        "informative_despite_formal_failure": [
            "DIRECTIONAL_DELTA_VERSUS_MATCHED_ALWAYS_UP",
            "CALIBRATION",
            "MAGNITUDE_ERROR",
        ],
        "informative_scope": "FEATURE_AVAILABLE_SUBSET_ONLY",
        "window_rule_rescue_authorized": False,
        "gap_policy_rescue_authorized": False,
        "threshold_rescue_authorized": False,
        "feature_rescue_authorized": False,
        "parameter_rescue_authorized": False,
    }


def preregistration() -> dict[str, Any]:
    """The frozen hypothesis, design, inference plan, gate and coverage ruling."""
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
        "search_plan_configuration_order": 2,
        "family": MODEL_FAMILY,
        "hypothesis_id": HYPOTHESIS_ID,
        "hypothesis": (
            "A fixed, causal, low-complexity nonlinear predictor using only BTCUSDT's own "
            "price, volume and volatility history contains directional information about "
            "the frozen 24h terminal target beyond the ALWAYS_UP baseline, and beyond what "
            "the linear configuration of the same family extracted from the same features."
        ),
        "hypothesis_class": "MATERIAL_PREDICTIVE_HYPOTHESIS",
        "model_version": MODEL_VERSION,
        "predecessor_configuration": LINEAR_MODEL_VERSION,
        "predecessor_experiment_id": LINEAR_EXPERIMENT_ID,
        "scheduled_regardless_of_predecessor_result": True,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "baseline_protocol": BASELINE_PROTOCOL_PATH,
        "source_roadmap_stage": SOURCE_ROADMAP_STAGE,
        "coverage_policy_decision": coverage_policy_decision(),
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
            "identical_to": LINEAR_MODEL_VERSION,
            "redesigned": False,
            "edge_rules_changed": False,
            "unavailability_taxonomy": list(UNAVAILABILITY_TAXONOMY),
            "unavailable_evaluation_row": "NEUTRAL_UNCERTAIN_ABSTENTION_COUNTED",
            "unavailable_training_row": "EXCLUDED_FROM_FITTING_COUNTED",
            "causality": "NO_BAR_WITH_OPEN_TIME_AFTER_T_MAY_ENTER_A_FEATURE",
        },
        "model": nonlinear_specification(),
        "reserved_specification_as_frozen": reserved_hgbr_specification(),
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
        "linear_comparison": {
            "classification": "DESCRIPTIVE_NOT_A_PREREGISTERED_TEST",
            "reason": (
                "The Stage-1 family allocates its alpha to two candidate-versus-baseline "
                "comparisons. A candidate-versus-candidate interval was never preregistered "
                "and would consume multiplicity the family does not have, so the comparison "
                "is reported descriptively and cannot support an advancement claim."
            ),
            "linear_configuration_replayed_for_comparison": True,
            "replay_consumes_stage1_budget": False,
            "replay_must_reconcile_with_committed_linear_result": True,
            "reported": [
                "POOLED_WIN_RATE_AND_COVERAGE_BOTH_CONFIGURATIONS",
                "POOLED_MATCHED_DELTA_BOTH_CONFIGURATIONS",
                "PER_FOLD_MATCHED_DELTA_BOTH_CONFIGURATIONS",
                "DIRECTIONAL_AGREEMENT_RATE_ON_SHARED_ACTIONABLE_TIMESTAMPS",
                "BRIER_AND_MAGNITUDE_ERROR_BOTH_CONFIGURATIONS",
            ],
        },
        "mandatory_reporting": [
            "DIRECTIONAL_WIN_RATE_WITH_SAMPLE_SIZE_AND_COVERAGE",
            "BRIER_SCORE_AND_FIXED_BIN_RELIABILITY_TABLE",
            "SIGNED_RETURN_MAE_AND_MEDIAN_ABSOLUTE_ERROR",
            "SIGNED_MAGNITUDE_MATCH_DIAGNOSTIC_WITH_EXCLUSION_COUNTS",
            "CHRONOLOGICAL_PER_FOLD_RESULTS",
            "BASELINE_COMPARISONS",
            "LINEAR_CONFIGURATION_COMPARISON",
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
            "coverage_gates_known_unpassable_before_execution": True,
            "post_result_tuning_authorized": False,
        },
        "budget": {
            "stage1_configurations_planned": STAGE1_FAMILY_SIZE,
            "stage1_configurations_consumed_before_this_experiment": 1,
            "stage1_configurations_consumed_by_this_experiment": 1,
            "stage1_configurations_remaining_after_this_experiment": 0,
            "closes_stage1_family": True,
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
            "internal_structure_v1_results_changed": False,
            "historical_terminal_classifications_changed": False,
            "previous_24h_sign_persistence_inverted": False,
            "linear_configuration_tuned_descendant": False,
            "third_stage1_model_family": False,
        },
    }


def admission(root: Path = ROOT) -> dict[str, Any]:
    """Prove the frozen records and the implementation exist before any market result."""
    plan_path, prereg_path = root / SEARCH_PLAN_PATH, root / PREREGISTRATION_PATH
    if not plan_path.is_file() or not prereg_path.is_file():
        raise ExperimentError("the frozen records must exist before the admission gate")
    if json.loads(prereg_path.read_text(encoding="utf-8")) != preregistration():
        raise ExperimentError("the committed preregistration is not what the code declares")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    reserved = plan["configurations"][1]
    if reserved["experiment_id"] != EXPERIMENT_ID:
        raise ExperimentError("the reserved configuration is not the one being executed")
    if reserved["specification"] != reserved_hgbr_specification():
        raise ExperimentError("the reserved specification drifted from the frozen plan")
    missing = [name for name in IMPLEMENTATION_FILES if not (root / name).is_file()]
    if missing:
        raise ExperimentError(f"the implementation is incomplete: {missing}")
    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_PRE_EXECUTION_ADMISSION_V1",
        "checkpoint": CHECKPOINT,
        "experiment_id": EXPERIMENT_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "model_version": MODEL_VERSION,
        "status": "PASS",
        "search_plan": SEARCH_PLAN_PATH,
        "search_plan_sha256": content_hash(plan_path),
        "preregistration": PREREGISTRATION_PATH,
        "preregistration_sha256": content_hash(prereg_path),
        "implementation_sha256": {name: content_hash(root / name) for name in IMPLEMENTATION_FILES},
        "coverage_policy_decision": coverage_policy_decision(),
        "feature_set_version": FEATURE_SET_VERSION,
        "feature_count": len(FEATURE_NAMES),
        "sklearn_version": SKLEARN_VERSION,
        "stage1_configurations_planned": STAGE1_FAMILY_SIZE,
        "stage1_configurations_consumed_before_this_run": 1,
        "predecessor_configuration": LINEAR_MODEL_VERSION,
        "predecessor_implementation_unchanged": True,
        "market_results_observed": 0,
        "model_fits_executed": 0,
        "post_cutoff_access": 0,
        "sealed_queries": 0,
        "champion_status": "NONE",
        "real_money": False,
    }


def admission_identity(root: Path = ROOT) -> str:
    """One hash binding the frozen records, the ruling and the implementation together."""
    record = admission(root)
    return payload_hash(
        {
            "search_plan_sha256": record["search_plan_sha256"],
            "preregistration_sha256": record["preregistration_sha256"],
            "implementation_sha256": record["implementation_sha256"],
            "coverage_policy_decision": record["coverage_policy_decision"],
        }
    )


def _fold_predictions(
    fold: Fold, cache: Mapping[int, tuple[float, ...]]
) -> tuple[dict[str, Any], list[Prediction], list[Prediction]]:
    """Fit the reserved heads on this fold's training portion and predict its evaluation."""
    training = [label for label in fold.training if label.open_time in cache]
    if not training:
        raise ExperimentError(f"{fold.name}: no feature-valid training row")
    directional = [label for label in training if label.direction in {UP, DOWN}]
    excluded_neutral = len(training) - len(directional)

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


def nonlinear_advancement_gate(
    pooled_coverage: float,
    fold_coverage: Mapping[str, float],
    pooled_delta: float,
    interval: Sequence[float],
    fold_deltas: Mapping[str, float],
) -> dict[str, Any]:
    """The same five frozen conditions, labelled with this configuration's classifications.

    The thresholds and the pass/fail logic come from the executed linear checkpoint's
    hash-frozen implementation; only the two classification strings differ.
    """
    record = advancement_gate(pooled_coverage, fold_coverage, pooled_delta, interval, fold_deltas)
    record["terminal_classification"] = NO_ADVANCE if record["failed_conditions"] else ADVANCE
    record["coverage_gates_known_unpassable_before_execution"] = True
    return record


def _linear_replay(fold_set: Any, cache: Mapping[int, tuple[float, ...]]) -> dict[str, Any]:
    """Re-run the executed linear configuration on the same cache, for comparison only.

    These fits replay a configuration whose budget was already consumed by
    `PREDICTIVE-INTERNAL-STRUCTURE-V1`. They are counted separately from this experiment's
    fits and consume no Stage-1 budget. The replay also reconciles against the committed
    linear result: if the imported linear code no longer reproduces its own committed win
    rate, the comparison is not trustworthy and the run fails closed.
    """
    from .internal_structure import _fold_predictions as linear_fold_predictions

    sides: dict[int, str] = {}
    predictions: list[Prediction] = []
    labels: list[Label] = []
    fits = 0
    for fold in fold_set.folds:
        _, directional, _ = linear_fold_predictions(fold, cache)
        fits += 3
        for item in directional:
            if item.direction != ABSTAIN:
                sides[item.open_time] = item.direction
        predictions.extend(directional)
        labels.extend(fold.evaluation)
    scored = score(
        predictions,
        _outcomes(labels),
        declares_direction=True,
        declares_probability=True,
        declares_magnitude=False,
    )
    return {"sides": sides, "scored": scored, "replay_fits": fits}


def _directional_agreement(
    linear_sides: Mapping[int, str], nonlinear_sides: Mapping[int, str]
) -> dict[str, Any]:
    """How often the two configurations declared the same side on the same timestamp."""
    shared = sorted(set(linear_sides) & set(nonlinear_sides))
    agreed = sum(1 for moment in shared if linear_sides[moment] == nonlinear_sides[moment])
    return {
        "shared_declared_timestamps": len(shared),
        "linear_declared_timestamps": len(linear_sides),
        "nonlinear_declared_timestamps": len(nonlinear_sides),
        "declared_sets_identical": set(linear_sides) == set(nonlinear_sides),
        "same_side": agreed,
        "agreement_rate": (agreed / len(shared)) if shared else None,
    }


def linear_comparison(
    root: Path,
    replay: Mapping[str, Any],
    nonlinear_sides: Mapping[int, str],
    pooled_directional: Mapping[str, Any],
    pooled_magnitude: Mapping[str, Any],
    pooled_matched: Mapping[str, Any],
    fold_deltas: Mapping[str, float],
    fold_coverage: Mapping[str, float],
) -> dict[str, Any]:
    """Descriptive comparison against the executed linear configuration. Not a test."""
    linear = json.loads((root / LINEAR_RESULT_PATH).read_text(encoding="utf-8"))
    linear_pooled = linear["candidate"]["pooled_directional"]
    linear_comparison_block = linear["primary_comparison"]
    replayed = replay["scored"]
    reconciled = (
        replayed["win_rate"] == linear_pooled["win_rate"]
        and replayed["coverage"] == linear_pooled["coverage"]
        and replayed["brier_score"] == linear_pooled["brier_score"]
    )
    if not reconciled:
        raise ExperimentError(
            "the linear replay does not reproduce the committed linear result, so the "
            "comparison between the two Stage-1 configurations is not trustworthy"
        )
    return {
        "independent_reconciliation": "PASS",
        "replay_model_fits": replay["replay_fits"],
        "replay_consumes_stage1_budget": False,
        "replay_classification": "REPLAY_OF_AN_ALREADY_CONSUMED_CONFIGURATION",
        "classification": "DESCRIPTIVE_NOT_A_PREREGISTERED_TEST",
        "linear_experiment_id": linear["experiment_id"],
        "linear_terminal_classification": linear["terminal_classification"],
        "linear_results_changed": False,
        "pooled": {
            "linear_win_rate": linear_pooled["win_rate"],
            "nonlinear_win_rate": pooled_directional["win_rate"],
            "linear_coverage": linear_pooled["coverage"],
            "nonlinear_coverage": pooled_directional["coverage"],
            "linear_matched_delta": linear_comparison_block["pooled"]["delta"],
            "nonlinear_matched_delta": pooled_matched["delta"],
            "linear_brier_score": linear_pooled["brier_score"],
            "nonlinear_brier_score": pooled_directional["brier_score"],
            "linear_magnitude_mae_percentage_points": (
                linear["candidate"]["pooled_magnitude"]["magnitude_mae_percentage_points"]
            ),
            "nonlinear_magnitude_mae_percentage_points": (
                pooled_magnitude["magnitude_mae_percentage_points"]
            ),
        },
        "by_fold": {
            name: {
                "linear_matched_delta": linear_comparison_block["fold_deltas"][name],
                "nonlinear_matched_delta": fold_deltas[name],
                "linear_coverage": linear_comparison_block["fold_coverage"][name],
                "nonlinear_coverage": fold_coverage[name],
            }
            for name in fold_deltas
        },
        "abstention_sets_identical": (
            linear_pooled["abstentions"] == pooled_directional["abstentions"]
        ),
        "directional_agreement": _directional_agreement(replay["sides"], nonlinear_sides),
    }


def run_experiment(root: Path = ROOT, bars: Sequence[OhlcvBar] | None = None) -> dict[str, Any]:
    """Execute the reserved configuration once and emit the complete contract report."""
    resolved = tuple(bars) if bars is not None else load_hourly_ohlcv(root)
    bars_by_open = index_ohlcv(resolved)
    label_set = build_labels(_label_bars(resolved), horizon_hours=HORIZON_HOURS)
    fold_set = build_folds(
        label_set.labels, horizon_hours=HORIZON_HOURS, purge_embargo_hours=PURGE_EMBARGO_HOURS
    )
    assert_no_fold_leak(fold_set)
    cache, unavailability = _feature_cache(bars_by_open, label_set.labels)

    by_fold: dict[str, Any] = {}
    pooled_directional_predictions: list[Prediction] = []
    pooled_magnitude_predictions: list[Prediction] = []
    pooled_labels: list[Label] = []
    pooled_magnitude_labels: list[Label] = []
    paired_folds = []
    fold_coverage: dict[str, float] = {}
    fold_deltas: dict[str, float] = {}
    fits = {"direction_base": 0, "direction_calibration": 0, "magnitude": 0}
    declared_sides: dict[int, str] = {}

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
        for item in directional:
            if item.direction != ABSTAIN:
                declared_sides[item.open_time] = item.direction
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
        pooled_directional_predictions.extend(directional)
        pooled_magnitude_predictions.extend(magnitude)
        pooled_labels.extend(fold.evaluation)
        pooled_magnitude_labels.extend(magnitude_labels)

    pooled_directional = score(
        pooled_directional_predictions,
        _outcomes(pooled_labels),
        declares_direction=True,
        declares_probability=True,
        declares_magnitude=False,
    )
    pooled_magnitude = score(
        pooled_magnitude_predictions,
        _outcomes(pooled_magnitude_labels),
        declares_direction=False,
        declares_probability=False,
        declares_magnitude=True,
    )
    pooled_records = [record for fold in paired_folds for record in fold.records]
    pooled_matched = _matched_summary(pooled_records, len(pooled_labels))
    paired = paired_delta_interval(paired_folds)
    replay = _linear_replay(fold_set, cache)
    pooled_coverage = float(pooled_directional["coverage"])
    gate = nonlinear_advancement_gate(
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
        "model_version": MODEL_VERSION,
        "research_generation": RESEARCH_GENERATION,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "preregistration": PREREGISTRATION_PATH,
        "search_plan": SEARCH_PLAN_PATH,
        "admission": ADMISSION_PATH,
        "coverage_policy_decision": coverage_policy_decision(),
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
            "identical_to_linear_configuration": True,
        },
        "model": nonlinear_specification(),
        "model_fits": {**fits, "total": sum(fits.values())},
        "candidate": {
            "pooled_directional": pooled_directional,
            "pooled_magnitude": pooled_magnitude,
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
        "linear_comparison": linear_comparison(
            root,
            replay,
            declared_sides,
            pooled_directional,
            pooled_magnitude,
            pooled_matched,
            fold_deltas,
            fold_coverage,
        ),
        "advancement_gate": gate,
        "terminal_classification": gate["terminal_classification"],
        "search_budget": {
            "family": MODEL_FAMILY,
            "stage1_configurations_planned": STAGE1_FAMILY_SIZE,
            "stage1_configurations_consumed": STAGE1_FAMILY_SIZE,
            "stage1_configurations_remaining": 0,
            "configurations_executed": [LINEAR_MODEL_VERSION, MODEL_VERSION],
            "configurations_reserved": [],
            "family_status": STAGE1_FAMILY_CLOSED,
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
            "external_information_family": False,
            "post_cutoff_market_data": False,
            "sealed_queries": 0,
            "champion_created": False,
            "real_money": False,
            "baselines_v1_results_changed": False,
            "internal_structure_v1_results_changed": False,
            "historical_terminal_classifications_changed": False,
            "previous_24h_sign_persistence_inverted": False,
            "outer_evaluation_used_in_fitting": False,
            "post_result_tuning": False,
            "linear_configuration_tuned_descendant": False,
            "third_stage1_model_family": False,
        },
    }


__all__ = [
    "ADMISSION_PATH",
    "ADVANCE",
    "CHECKPOINT",
    "EXPERIMENT_ID",
    "HYPOTHESIS_ID",
    "IMPLEMENTATION_FILES",
    "NO_ADVANCE",
    "PREREGISTRATION_PATH",
    "REPORT_JSON_PATH",
    "REPORT_MARKDOWN_PATH",
    "RESULT_PATH",
    "STAGE1_FAMILY_CLOSED",
    "admission",
    "admission_identity",
    "canonical_bytes",
    "coverage_policy_decision",
    "nonlinear_advancement_gate",
    "preregistration",
    "run_experiment",
]
