"""Create WP-014 SEARCH_MEMORY records and preregistrations before results."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.continuation_lab import PROFILES
from app.research.model_search_memory import bind_model_spec, model_fingerprint
from app.research.registry import cumulative_accounting
from app.research.wp014 import (
    ADMISSION_PATH,
    ALLOCATION_ID,
    ALLOCATION_PATH,
    CONTROL_VARIANT,
    EXPERIMENTS,
    FAMILY_PATH,
    HYPOTHESIS_ID,
    MAXIMUM_MODEL_FITS,
    PREDICTION_TOLERANCE,
    PRIMARY_VARIANT,
    ROOT_FAMILY,
    VARIANTS,
    config_path,
    dependency_manifest,
    executable_spec,
    novelty_decision,
    preflight,
    sha256,
)
from app.research.wp014_model import HGBR_PARAMETERS, MODEL_VERSION, SKLEARN_VERSION

CREATED_AT = "2026-09-13T08:00:00Z"
PREFLIGHT_PATH = "reports/validation/WP-014-PREFLIGHT.json"


def write(relative: str, payload: Any) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    if any(
        (ROOT / f"research/experiments/{experiment}/result.json").exists()
        for experiment in EXPERIMENTS.values()
    ):
        raise RuntimeError("refusing to regenerate admission after WP-014 result")
    prior = cumulative_accounting(ROOT)
    admission = novelty_decision(ROOT)
    write(ADMISSION_PATH, admission)
    write(
        FAMILY_PATH,
        {
            "schema_version": 1,
            "work_package": "WP-014",
            "family_id": ROOT_FAMILY,
            "parent_family_id": None,
            "allocation_id": ALLOCATION_ID,
            "admitted_by": ADMISSION_PATH,
            "status": "ADMITTED_PENDING_RESULTS",
            "aliases": [HYPOTHESIS_ID, MODEL_VERSION, PRIMARY_VARIANT],
            "entry_event_anchors": ["PREDICTED_DEFAULT_NET_R_STRICTLY_ABOVE_ZERO"],
            "information_source": "FROZEN_INTERNAL_MARKET_AND_ORDER_FLOW_FEATURES_F1_F8",
            "mechanism": (
                "A fixed shallow histogram gradient-boosted regressor may capture bounded "
                "threshold and intersection relationships among raw internal F1-F8."
            ),
            "matched_control": {
                "variant": CONTROL_VARIANT,
                "classification": "DUPLICATE_MATCHED_CONTROL_REPLICATION",
                "duplicate_of": "EXP-ML-014-LINEAR-NET-R-FULL",
                "novelty_claimed": False,
            },
            "failure_experiment_ids": [],
            "legitimate_revisit": (
                "Only a new explicit Research Director allocation; no exposed-result tuning."
            ),
        },
    )
    write(
        ALLOCATION_PATH,
        {
            "schema_version": 1,
            "work_package": "WP-014",
            "allocation_id": ALLOCATION_ID,
            "authority": "Owner WP-014 instruction",
            "review_authority": "reports/reviews/WP-013-RESEARCH-DIRECTOR-REVIEW.md",
            "kind": "RESULT_DEPENDENT_NEW_SHALLOW_NONLINEAR_FAMILY_ALLOCATION",
            "root_family": ROOT_FAMILY,
            "hypothesis_id": HYPOTHESIS_ID,
            "architecture": MODEL_VERSION,
            "experiment_ids": [EXPERIMENTS[variant] for variant in VARIANTS],
            "primary_variant": PRIMARY_VARIANT,
            "matched_control_variant": CONTROL_VARIANT,
            "matched_control_duplicate_of": "EXP-ML-014-LINEAR-NET-R-FULL",
            "new_economic_hypotheses": 1,
            "model_configurations": 2,
            "profiles": list(PROFILES),
            "profiles_per_configuration": 4,
            "profile_evaluations": 8,
            "supervised_model_fits": MAXIMUM_MODEL_FITS,
            "numeric_parameter_variants": 0,
            "hyperparameter_variants": 0,
            "feature_variants": 0,
            "threshold_variants": 0,
            "architecture_variants": 0,
            "model_selection_forks": 0,
            "sealed_queries": 0,
            "paper_observations": 0,
            "adaptive_decision_increment": 1,
            "result_dependent_fork_increment": 1,
            "prior_adaptive_decisions": prior["adaptive_decisions"],
            "prior_result_dependent_forks": prior["result_dependent_forks"],
            "cumulative_adaptive_decisions": prior["adaptive_decisions"] + 1,
            "cumulative_result_dependent_forks": prior["result_dependent_forks"] + 1,
            "family_limits": {
                "experiments": 2,
                "strategy_variants": 2,
                "trials": 8,
                "numeric_parameter_variants": 0,
            },
            "conditionality": (
                "Execution requires a committed admission and preregistration, exact F1-F8, "
                "fixed HGBR parameters, matched eligibility, 216h purge and complete outcomes."
            ),
        },
    )
    dependencies = dependency_manifest(ROOT)
    for decision in admission["variants"]:
        variant = decision["variant"]
        experiment = EXPERIMENTS[variant]
        primary = variant == PRIMARY_VARIANT
        spec = executable_spec(variant, ROOT)
        binding = bind_model_spec(spec)
        parameter_space = {
            "allocation_id": ALLOCATION_ID,
            "root_family": ROOT_FAMILY,
            "hypothesis_id": HYPOTHESIS_ID,
            "variant": variant,
            "features": [spec.to_dict()["features"][index]["name"] for index in range(8)],
            "feature_count": 8,
            "input_scaling": (
                "NONE_RAW_GOVERNED_VALUES" if primary else "TRAINING_ONLY_MEAN_STD_DDOF_0"
            ),
            "hgbr_parameters": dict(HGBR_PARAMETERS) if primary else {},
            "sklearn_version": SKLEARN_VERSION if primary else None,
            "numeric_parameter_variants": 0,
            "hyperparameter_variants": 0,
            "feature_variants": 0,
            "threshold_variants": 0,
            "architecture_variants": 0,
            "model_selection_forks": 0,
            "signal_threshold": 0.0,
            "update_cadence": "ONCE_PER_FOLD_NO_VALIDATION_REFIT",
            "prediction_tolerance": PREDICTION_TOLERANCE,
            "matched_control_duplicate_of": (
                "EXP-ML-014-LINEAR-NET-R-FULL" if not primary else None
            ),
            "declared_trial_budget": {
                "configurations": 1,
                "profiles": 4,
                "model_fits": 6,
                "seeds": 0,
                "total_trials": 4,
            },
            "behavior_hash": binding.behavior_hash,
            "structural_hash": binding.structural_hash,
            "executable_spec_hash": binding.executable_spec_hash,
            "dependency_hash": binding.dependency_hash,
            "model_fingerprint": model_fingerprint(spec),
            "executable_model_spec": spec.to_dict(),
            "dependencies": dependencies,
        }
        write(
            f"research/experiments/{experiment}/preregistration.json",
            {
                "schema_version": 2,
                "experiment_id": experiment,
                "experiment_version": 1,
                "created_at_utc": CREATED_AT,
                "status": "PREREGISTERED",
                "hypothesis": (
                    "A fixed low-capacity nonlinear model may capture threshold/intersection "
                    "relationships among eight frozen internal BTC signals that linear models "
                    "cannot represent, producing more robust after-cost LONG expectancy."
                    if primary
                    else "The frozen WP-008 F1-F8 OLS behavior is repeated on the identical "
                    "WP-014 universe as a matched control; no novelty is claimed."
                ),
                "rationale": (
                    "One rigid nonlinear architecture versus one disclosed duplicate linear "
                    "control; predictive, not causal, with no model search."
                ),
                "research_scope": (
                    "BTCUSDT_SPOT_LONG_ONLY_EXPOSED_DEVELOPMENT_NO_SEALED_OR_PAPER_ACTION"
                ),
                "dataset": {
                    "manifest_id": "BTCUSDT-SPOT-1M-DEV-v1",
                    "content_hash": spec.dataset["content_hash"],
                    "maximum_timestamp": "2024-12-31T23:59:00Z",
                },
                "metrics": {
                    "primary": "POOLED_VALID_RESOLVED_DEFAULT_NET_R",
                    "secondary": [
                        "profiles",
                        "annual_folds",
                        "trade_ess_and_concentration",
                        "prediction_positive_hours",
                        "oos_prediction_label_pearson",
                        "fold_model_identity_and_serialization_hashes",
                        "independent_reconciliation",
                    ],
                },
                "evaluation_design": (
                    "Six annual expanding folds 2019-2024; one fit per fold; training signals "
                    "and complete label outcomes strictly before validation_start-216h; four "
                    "fixed profiles and identical eligibility across configurations."
                ),
                "leakage_controls": [
                    "EXACT_FROZEN_F1_F8_AVAILABLE_AT_SIGNAL_TIME",
                    "NO_MACRO_NFCI_EXOGENOUS_OR_ALIGNED_FEATURE_ACCESS",
                    "TRAINING_SIGNAL_AND_COMPLETE_OUTCOME_STRICTLY_BEFORE_PURGE_BOUNDARY",
                    "NO_VALIDATION_REFIT_SELECTION_OR_STANDARDIZATION_FOR_HGBR",
                    "OLS_TRAINING_ONLY_SCALING_DDOF_0",
                    "NO_POST_CUTOFF_OR_SEALED_ACCESS",
                ],
                "parameter_space": parameter_space,
                "code_config_reference": sha256(ROOT / config_path(variant)),
                "cost_execution_reference": (
                    "BACKTEST_ENGINE_V2 / EXECUTION_MODEL_V2 / BTCUSDT_SPOT_COST_V1"
                ),
                "seeds": [0],
                "trial_budget": 4,
                "stopping_rule": (
                    "Execute all four declared profiles once; no hyperparameter, feature, "
                    "threshold, architecture, model-selection, or post-result variant."
                ),
            },
        )
    write(PREFLIGHT_PATH, preflight(ROOT))
    print(
        json.dumps(
            {
                "family": admission["family_classification"],
                "control": admission["variants"][1]["classification"],
                "experiments": list(EXPERIMENTS.values()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
