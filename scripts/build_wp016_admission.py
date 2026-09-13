"""Create WP-016 SEARCH_MEMORY admission and preregistration before results."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.continuation_lab import DATASET_HASH, PROFILES
from app.research.funding import MANIFEST_PATH as FUNDING_MANIFEST_PATH
from app.research.model_search_memory import bind_model_spec, model_fingerprint
from app.research.registry import cumulative_accounting
from app.research.wikimedia import FEATURE as ATTENTION_FEATURE
from app.research.wikimedia import MANIFEST_PATH as ATTENTION_MANIFEST_PATH
from app.research.wp014_model import HGBR_PARAMETERS, MODEL_VERSION, SKLEARN_VERSION
from app.research.wp016 import (
    ADMISSION_PATH,
    ALLOCATION_ID,
    ALLOCATION_PATH,
    CONTROL_VARIANT,
    EXPERIMENTS,
    FAMILY_PATH,
    HYPOTHESIS_ID,
    LEDGER_PATH,
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

CREATED_AT = "2026-09-13T18:00:00Z"
PREFLIGHT_PATH = "reports/validation/WP-016-PREFLIGHT.json"


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
        raise RuntimeError("refusing to regenerate WP-016 admission after results")
    prior = cumulative_accounting(ROOT)
    funding = json.loads((ROOT / FUNDING_MANIFEST_PATH).read_text(encoding="utf-8"))
    attention = json.loads((ROOT / ATTENTION_MANIFEST_PATH).read_text(encoding="utf-8"))
    combined_hash = hashlib.sha256(
        f"{DATASET_HASH}:{funding['canonical']['logical_sha256']}:{attention['canonical']['logical_sha256']}".encode()
    ).hexdigest()
    admission = novelty_decision(ROOT)
    write(ADMISSION_PATH, admission)
    write(
        FAMILY_PATH,
        {
            "schema_version": 1,
            "work_package": "WP-016",
            "family_id": ROOT_FAMILY,
            "parent_family_id": None,
            "allocation_id": ALLOCATION_ID,
            "admitted_by": ADMISSION_PATH,
            "status": "ADMITTED_PREREGISTERED_PENDING_OWNER_EXECUTION",
            "aliases": [HYPOTHESIS_ID, ATTENTION_FEATURE, PRIMARY_VARIANT],
            "entry_event_anchors": ["PREDICTED_DEFAULT_NET_R_STRICTLY_ABOVE_ZERO"],
            "information_source": "OFFICIAL_ENWIKIPEDIA_BITCOIN_DAILY_USER_PAGEVIEWS",
            "mechanism": "One conservative point-in-time relative public-attention shock is added to frozen spot and settled-funding inputs.",
            "matched_control": {
                "variant": CONTROL_VARIANT,
                "classification": "KNOWN_FUNDING_HGBR_MATCHED_CONTROL",
                "related_to": "EXP-ML-024-INTERNAL-PLUS-FUNDING-HGBR",
                "novelty_claimed": False,
            },
            "failure_experiment_ids": [],
            "legitimate_revisit": "Only a new explicit Research Director allocation; no exposed-result tuning.",
        },
    )
    allocation = {
        "schema_version": 1,
        "work_package": "WP-016",
        "allocation_id": ALLOCATION_ID,
        "authority": "Owner WP-016 preparation instruction",
        "review_authority": "reports/reviews/RESEARCH-RUNNER-V1-RESEARCH-DIRECTOR-REVIEW.md",
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
        "attention_windows": 0,
        "article_variants": 0,
        "attention_transformations": 0,
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
        "conditionality": "Official Wikimedia integrity, 48h conservative daily availability, trailing 28 excluding current, exact WP-015 inputs/model, matched attention availability, 216h purge, and complete outcomes.",
    }
    write(ALLOCATION_PATH, allocation)
    dependencies = dependency_manifest(ROOT)
    preregistrations: dict[str, dict[str, Any]] = {}
    for decision in admission["variants"]:
        variant = decision["variant"]
        experiment = EXPERIMENTS[variant]
        spec = executable_spec(variant, ROOT)
        binding = bind_model_spec(spec)
        features = list(features_for(variant))
        parameter_space = {
            "allocation_id": ALLOCATION_ID,
            "root_family": ROOT_FAMILY,
            "hypothesis_id": HYPOTHESIS_ID,
            "variant": variant,
            "features": features,
            "feature_count": len(features),
            "only_new_feature": ATTENTION_FEATURE if variant == PRIMARY_VARIANT else None,
            "attention_manifest_id": attention["manifest_id"],
            "attention_logical_sha256": attention["canonical"]["logical_sha256"],
            "attention_availability": "UTC_DAY_END_PLUS_24H_FIRST_HOURLY_USE_AT_DAY_START_PLUS_48H",
            "attention_transform": "LOG((PAGEVIEWS_D+1)/(MEDIAN(PREVIOUS_28_EXCLUDING_D)+1))",
            "matched_attention_eligible_universe": True,
            "funding_manifest_id": funding["manifest_id"],
            "funding_logical_sha256": funding["canonical"]["logical_sha256"],
            "funding_availability": "FUNDING_TIME_STRICTLY_EARLIER_THAN_SIGNAL_TIME",
            "input_scaling": "NONE_RAW_GOVERNED_VALUES",
            "hgbr_parameters": dict(HGBR_PARAMETERS),
            "sklearn_version": SKLEARN_VERSION,
            "validation_years": list(range(2020, 2025)),
            "model_fits": 5,
            "attention_windows": 0,
            "article_variants": 0,
            "attention_transformations": 0,
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
            "known_control_mechanism": "EXP-ML-024-INTERNAL-PLUS-FUNDING-HGBR"
            if variant == CONTROL_VARIANT
            else None,
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
        preregistrations[variant] = {
            "schema_version": 2,
            "experiment_id": experiment,
            "experiment_version": 1,
            "created_at_utc": CREATED_AT,
            "status": "PREREGISTERED",
            "hypothesis": "Unusual public attention to Bitcoin measured with point-in-time-safe daily Wikimedia pageviews may add information absent from frozen spot and funding inputs and improve after-cost SPOT LONG expectancy."
            if variant == PRIMARY_VARIANT
            else "The exact WP-015 funding HGBR is repeated on the identical attention-available universe as a matched known-mechanism control.",
            "rationale": "One frozen relative-attention-shock variable versus a matched known HGBR control; predictive, not causal, with no model search.",
            "research_scope": "BTCUSDT_SPOT_LONG_ONLY_WIKIMEDIA_INFORMATIONAL_NO_SEALED_NO_LIVE_TRADING",
            "dataset": {
                "manifest_id": "BTCUSDT-SPOT-1M-DEV-v1 + BTCUSDT-USDM-FUNDING-DEV-v1 + WIKIMEDIA-BITCOIN-PAGEVIEWS-DEV-v1",
                "content_hash": combined_hash,
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
                    "attention_sign_diagnostics",
                    "independent_reconciliation",
                ],
            },
            "evaluation_design": "Five complete annual expanding folds 2020-2024; conservative daily attention availability; strict prior funding; identical primary/control universe; complete outcomes before validation_start-216h; four fixed profiles.",
            "leakage_controls": [
                "EXACT_FROZEN_F1_F8_AND_FUNDING_SEMANTICS",
                "OBSERVATION_D_AVAILABLE_ONLY_AT_DAY_START_D_PLUS_48H",
                "TRAILING_28_MEDIAN_EXCLUDES_D",
                "PRIMARY_AND_CONTROL_REQUIRE_IDENTICAL_ATTENTION_AVAILABILITY",
                "TRAINING_SIGNAL_AND_COMPLETE_OUTCOME_STRICTLY_BEFORE_PURGE_BOUNDARY",
                "NO_VALIDATION_REFIT_SELECTION_SCALING_OR_EARLY_STOPPING",
                "NO_POST_CUTOFF_OR_SEALED_ACCESS",
            ],
            "parameter_space": parameter_space,
            "code_config_reference": sha256(ROOT / config_path(variant)),
            "cost_execution_reference": "BACKTEST_ENGINE_V2 / EXECUTION_MODEL_V2 / BTCUSDT_SPOT_COST_V1",
            "seeds": [0],
            "trial_budget": 4,
            "stopping_rule": "Owner executes four profiles once through the allowlisted runner; no attention window/article/transform, subset, algorithm, hyperparameter, signal threshold, or result-dependent fork.",
        }
        write(f"research/experiments/{experiment}/preregistration.json", preregistrations[variant])
    ledger = []
    for decision in admission["variants"]:
        variant = decision["variant"]
        experiment = EXPERIMENTS[variant]
        prereg_path = f"research/experiments/{experiment}/preregistration.json"
        ledger.append(
            {
                "schema_version": 2,
                "work_package": "WP-016",
                "record_kind": "PREREGISTERED_ADMISSION"
                if variant == PRIMARY_VARIANT
                else "PREREGISTERED_MATCHED_DUPLICATE_CONTROL",
                "experiment_id": experiment,
                "strategy_label": variant,
                "root_family": ROOT_FAMILY,
                "allocation_id": ALLOCATION_ID,
                "hypothesis_id": HYPOTHESIS_ID,
                "hypothesis_role": decision["hypothesis_role"],
                "classification": decision["classification"],
                "novelty": decision["classification"],
                "behavior_hash": decision["behavior_hash"],
                "structural_hash": decision["structural_hash"],
                "executable_spec_hash": decision["executable_spec_hash"],
                "dependency_hash": decision["dependency_hash"],
                "matched_experiment_ids": decision["matched_experiment_ids"],
                "parent_experiment_ids": []
                if variant == PRIMARY_VARIANT
                else [EXPERIMENTS[PRIMARY_VARIANT]],
                "claimed_market_mechanism": "Conservatively available relative Wikipedia attention shock may add public-attention information.",
                "scientific_reason": "New-information family primary."
                if variant == PRIMARY_VARIANT
                else "Known funding HGBR on the matched attention-available universe.",
                "preregistration_path": prereg_path,
                "preregistration_sha256": sha256(ROOT / prereg_path),
                "result_path": f"research/experiments/{experiment}/result.json",
                "outcome_reference": experiment,
                "budget_units": {
                    "experiments": 1,
                    "strategy_variants": 1,
                    "trials": 4,
                    "numeric_parameter_variants": 0,
                },
            }
        )
    (ROOT / LEDGER_PATH).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / LEDGER_PATH).write_text(
        "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in ledger),
        encoding="utf-8",
        newline="\n",
    )
    write(PREFLIGHT_PATH, preflight(ROOT))
    print(
        json.dumps(
            {
                "family": admission["family_classification"],
                "experiments": list(EXPERIMENTS.values()),
                "results_observed": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
