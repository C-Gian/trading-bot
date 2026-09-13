"""Create WP-015 SEARCH_MEMORY records and preregistrations before model results."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.continuation_lab import DATASET_HASH, PROFILES
from app.research.funding import FEATURE, MANIFEST_PATH
from app.research.funding import VERSION as FUNDING_VERSION
from app.research.model_search_memory import bind_model_spec, model_fingerprint
from app.research.registry import cumulative_accounting
from app.research.wp014_model import HGBR_PARAMETERS, MODEL_VERSION, SKLEARN_VERSION
from app.research.wp015 import (
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
    features_for,
    novelty_decision,
    preflight,
    sha256,
)

CREATED_AT = "2026-09-13T13:10:00Z"
PREFLIGHT_PATH = "reports/validation/WP-015-PREFLIGHT.json"


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
        raise RuntimeError("refusing to regenerate WP-015 admission after results")
    prior = cumulative_accounting(ROOT)
    funding = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    combined_content_hash = hashlib.sha256(
        f"{DATASET_HASH}:{funding['canonical']['logical_sha256']}".encode()
    ).hexdigest()
    admission = novelty_decision(ROOT)
    write(ADMISSION_PATH, admission)
    write(
        FAMILY_PATH,
        {
            "schema_version": 1,
            "work_package": "WP-015",
            "family_id": ROOT_FAMILY,
            "parent_family_id": None,
            "allocation_id": ALLOCATION_ID,
            "admitted_by": ADMISSION_PATH,
            "status": "ADMITTED_PENDING_RESULTS",
            "aliases": [HYPOTHESIS_ID, FUNDING_VERSION, PRIMARY_VARIANT],
            "entry_event_anchors": ["PREDICTED_DEFAULT_NET_R_STRICTLY_ABOVE_ZERO"],
            "information_source": "STRICTLY_PRIOR_SETTLED_BTCUSDT_USDM_PERPETUAL_FUNDING",
            "mechanism": "One raw settled derivatives positioning value is added to frozen spot F1-F8.",
            "matched_control": {
                "variant": CONTROL_VARIANT,
                "classification": "KNOWN_INTERNAL_HGBR_MATCHED_CONTROL",
                "related_to": "EXP-ML-022-SHALLOW-INTERNAL-HGBR",
                "novelty_claimed": False,
            },
            "failure_experiment_ids": [],
            "legitimate_revisit": "Only a new explicit Research Director allocation; no exposed-result tuning.",
        },
    )
    write(
        ALLOCATION_PATH,
        {
            "schema_version": 1,
            "work_package": "WP-015",
            "allocation_id": ALLOCATION_ID,
            "authority": "Owner WP-015 instruction",
            "review_authority": "reports/reviews/WP-014-RESEARCH-DIRECTOR-REVIEW.md",
            "kind": "DELIBERATE_NEW_INFORMATION_FAMILY_ALLOCATION",
            "root_family": ROOT_FAMILY,
            "hypothesis_id": HYPOTHESIS_ID,
            "architecture": MODEL_VERSION,
            "experiment_ids": [EXPERIMENTS[variant] for variant in VARIANTS],
            "primary_variant": PRIMARY_VARIANT,
            "matched_control_variant": CONTROL_VARIANT,
            "new_economic_hypotheses": 1,
            "model_configurations": 2,
            "profiles": list(PROFILES),
            "profiles_per_configuration": 4,
            "profile_evaluations": 8,
            "supervised_model_fits": MAXIMUM_MODEL_FITS,
            "funding_transformations": 0,
            "funding_thresholds": 0,
            "feature_subsets": 0,
            "algorithm_variants": 0,
            "hyperparameter_variants": 0,
            "threshold_variants": 0,
            "architecture_variants": 0,
            "model_selection_forks": 0,
            "sealed_queries": 0,
            "paper_observations": 0,
            "adaptive_decision_increment": 1,
            "result_dependent_fork_increment": 0,
            "prior_adaptive_decisions": prior["adaptive_decisions"],
            "prior_result_dependent_forks": prior["result_dependent_forks"],
            "cumulative_adaptive_decisions": prior["adaptive_decisions"] + 1,
            "cumulative_result_dependent_forks": prior["result_dependent_forks"],
            "family_limits": {
                "experiments": 2,
                "strategy_variants": 2,
                "trials": 8,
                "numeric_parameter_variants": 0,
            },
            "conditionality": "Official funding integrity and strict as-of audit, fixed HGBR, matched funding availability, 216h purge, and complete outcomes.",
        },
    )
    dependencies = dependency_manifest(ROOT)
    for decision in admission["variants"]:
        variant = decision["variant"]
        experiment = EXPERIMENTS[variant]
        spec = executable_spec(variant, ROOT)
        binding = bind_model_spec(spec)
        names = list(features_for(variant))
        parameter_space = {
            "allocation_id": ALLOCATION_ID,
            "root_family": ROOT_FAMILY,
            "hypothesis_id": HYPOTHESIS_ID,
            "variant": variant,
            "features": names,
            "feature_count": len(names),
            "only_new_feature": FEATURE if variant == PRIMARY_VARIANT else None,
            "funding_manifest_id": funding["manifest_id"],
            "funding_logical_sha256": funding["canonical"]["logical_sha256"],
            "funding_availability": "FUNDING_TIME_STRICTLY_EARLIER_THAN_SIGNAL_TIME",
            "matched_funding_eligible_universe": True,
            "input_scaling": "NONE_RAW_GOVERNED_VALUES",
            "hgbr_parameters": dict(HGBR_PARAMETERS),
            "sklearn_version": SKLEARN_VERSION,
            "validation_years": list(range(2020, 2025)),
            "model_fits": 5,
            "funding_transformations": 0,
            "funding_thresholds": 0,
            "feature_subsets": 0,
            "algorithm_variants": 0,
            "hyperparameter_variants": 0,
            "feature_variants": 0,
            "threshold_variants": 0,
            "architecture_variants": 0,
            "model_selection_forks": 0,
            "signal_threshold": 0.0,
            "update_cadence": "ONCE_PER_FOLD_NO_VALIDATION_REFIT",
            "prediction_tolerance": PREDICTION_TOLERANCE,
            "known_control_mechanism": (
                "EXP-ML-022-SHALLOW-INTERNAL-HGBR" if variant == CONTROL_VARIANT else None
            ),
            "declared_trial_budget": {
                "configurations": 1,
                "profiles": 4,
                "model_fits": 5,
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
                    "The latest legally available settled BTCUSDT perpetual funding rate may add positioning information absent from frozen spot F1-F8 and improve after-cost SPOT LONG expectancy."
                    if variant == PRIMARY_VARIANT
                    else "The exact WP-014 internal HGBR is repeated on the identical funding-available universe as a matched known-mechanism control."
                ),
                "rationale": "One new raw information variable versus a matched known HGBR control; predictive, not causal, with no model search.",
                "research_scope": "BTCUSDT_SPOT_LONG_ONLY_FUNDING_INFORMATIONAL_NO_FUTURES_EXECUTION_NO_SEALED",
                "dataset": {
                    "manifest_id": "BTCUSDT-SPOT-1M-DEV-v1 + BTCUSDT-USDM-FUNDING-DEV-v1",
                    "content_hash": combined_content_hash,
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
                        "funding_distribution_and_sign_diagnostics",
                        "independent_reconciliation",
                    ],
                },
                "evaluation_design": "Five annual expanding folds 2020-2024; strict prior funding availability; identical primary/control universe; complete outcomes before validation_start-216h; four fixed profiles.",
                "leakage_controls": [
                    "EXACT_FROZEN_F1_F8_AVAILABLE_AT_SIGNAL_TIME",
                    "LATEST_FUNDING_TIME_STRICTLY_BEFORE_SIGNAL_TIME",
                    "PRIMARY_AND_CONTROL_REQUIRE_IDENTICAL_FUNDING_AVAILABILITY",
                    "TRAINING_SIGNAL_AND_COMPLETE_OUTCOME_STRICTLY_BEFORE_PURGE_BOUNDARY",
                    "NO_VALIDATION_REFIT_SELECTION_SCALING_OR_EARLY_STOPPING",
                    "NO_POST_CUTOFF_OR_SEALED_ACCESS",
                ],
                "parameter_space": parameter_space,
                "code_config_reference": sha256(ROOT / config_path(variant)),
                "cost_execution_reference": "BACKTEST_ENGINE_V2 / EXECUTION_MODEL_V2 / BTCUSDT_SPOT_COST_V1",
                "seeds": [0],
                "trial_budget": 4,
                "stopping_rule": "Execute four profiles once; no funding transform/threshold, subset, algorithm, hyperparameter, signal threshold, or post-result fork.",
            },
        )
    write(PREFLIGHT_PATH, preflight(ROOT))
    print(
        json.dumps(
            {
                "family": admission["family_classification"],
                "experiments": list(EXPERIMENTS.values()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
