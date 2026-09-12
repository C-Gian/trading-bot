"""Create WP-013 SEARCH_MEMORY admission, allocation and preregistrations pre-result."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.continuation_lab import PROFILES
from app.research.registry import cumulative_accounting
from app.research.wp013 import (
    ADMISSION_PATH,
    ALLOCATION_ID,
    ALLOCATION_PATH,
    ARCHITECTURE,
    EXPERIMENTS,
    FAMILY_PATH,
    FEATURES,
    HYPOTHESIS_ID,
    MAXIMUM_MODEL_FITS,
    PRIMARY_VARIANT,
    ROOT_FAMILY,
    VARIANTS,
    config_path,
    dependency_manifest,
    novelty_decision,
    sha256,
)

CREATED_AT = "2026-09-12T20:00:00Z"


def write(relative: str, payload: object) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def main() -> int:
    if any((ROOT / f"research/experiments/{experiment}/result.json").exists()
           for experiment in EXPERIMENTS.values()):
        raise RuntimeError("refusing to regenerate admission after WP-013 result")
    admission = novelty_decision(ROOT)
    write(ADMISSION_PATH, admission)
    prior = cumulative_accounting(ROOT)
    write(FAMILY_PATH, {
        "schema_version": 1, "work_package": "WP-013", "family_id": ROOT_FAMILY,
        "parent_family_id": None, "allocation_id": ALLOCATION_ID,
        "admitted_by": ADMISSION_PATH, "status": "ADMITTED_PENDING_RESULTS",
        "aliases": [HYPOTHESIS_ID, ARCHITECTURE, *VARIANTS],
        "entry_event_anchors": ["PREDICTED_DEFAULT_NET_R_STRICTLY_ABOVE_ZERO"],
        "information_source": "FROZEN_INTERNAL_MARKET_AND_ORDER_FLOW_FEATURES_CONTEXTUALIZED_BY_RAW_POINT_IN_TIME_ALFRED_NFCI",
        "mechanism": (
            "Financial conditions may continuously modify internal BTC signal slopes. "
            "Raw NFCI appears only in eight fixed feature products, never as a direct predictor."
        ),
        "failure_experiment_ids": [],
        "legitimate_revisit": "Only a new explicit Research Director allocation; no exposed-result tuning.",
    })
    write(ALLOCATION_PATH, {
        "schema_version": 1, "work_package": "WP-013", "allocation_id": ALLOCATION_ID,
        "authority": "Owner WP-013 instruction", "review_authority": "reports/reviews/WP-012-RESEARCH-DIRECTOR-REVIEW.md",
        "kind": "RESULT_DEPENDENT_NEW_CONTEXTUAL_INTERACTION_FAMILY_ALLOCATION",
        "root_family": ROOT_FAMILY, "hypothesis_id": HYPOTHESIS_ID,
        "architecture": ARCHITECTURE, "experiment_ids": [EXPERIMENTS[v] for v in VARIANTS],
        "primary_variant": PRIMARY_VARIANT, "new_economic_hypotheses": 1,
        "model_configurations": 2, "profiles": list(PROFILES),
        "profiles_per_configuration": 4, "profile_evaluations": 8,
        "supervised_model_fits": MAXIMUM_MODEL_FITS, "numeric_parameter_variants": 0,
        "interaction_subsets_searched": 0, "context_transforms_searched": 0,
        "threshold_searches": 0, "algorithm_variants": 0, "feature_subset_searches": 0,
        "sealed_queries": 0, "paper_observations": 0,
        "adaptive_decision_increment": 1, "result_dependent_fork_increment": 1,
        "prior_adaptive_decisions": prior["adaptive_decisions"],
        "prior_result_dependent_forks": prior["result_dependent_forks"],
        "cumulative_adaptive_decisions": prior["adaptive_decisions"] + 1,
        "cumulative_result_dependent_forks": prior["result_dependent_forks"] + 1,
        "family_limits": {"experiments": 2, "strategy_variants": 2, "trials": 8,
                          "numeric_parameter_variants": 0},
        "conditionality": "Committed admission/preregistration and passing structural/as-of audit before results.",
    })
    dependencies = dependency_manifest(ROOT)
    for variant, decision in zip(VARIANTS, admission["variants"], strict=True):
        experiment = EXPERIMENTS[variant]
        primary = variant == PRIMARY_VARIANT
        write(f"research/experiments/{experiment}/preregistration.json", {
            "schema_version": 2, "experiment_id": experiment, "experiment_version": 1,
            "created_at_utc": CREATED_AT, "status": "PREREGISTERED",
            "hypothesis": (
                "Point-in-time financial conditions may continuously modify the predictive relationship between internal BTC market/order-flow signals and net LONG opportunity; fixed NFCI-signal interaction terms may improve robust after-cost expectancy over a matched internal-only linear model."
                if primary else
                "On the identical NFCI-available universe, the frozen internal-only OLS provides the matched control for the contextual interaction mechanism."
            ),
            "rationale": "A distinct continuous interaction mechanism; not a rescue of additive macro EWLS or binary regime experts. Predictive, not causal.",
            "research_scope": "DEVELOPMENT_WALK_FORWARD_NO_SEALED_ACCESS_NO_PAPER_EVIDENCE",
            "dataset": {"manifest_id": "BTCUSDT-SPOT-1M-DEV-v1",
                        "content_hash": decision["spec"]["dataset"]["content_hash"],
                        "maximum_timestamp": "2024-12-31T23:59:00Z"},
            "metrics": {"primary": "POOLED_VALID_RESOLVED_DEFAULT_NET_R",
                        "secondary": ["profiles", "terminal_classification", "annual_folds",
                                      "condition_numbers", "coefficient_sign_stability",
                                      "effective_slopes_at_nfci_minus1_zero_plus1",
                                      "prediction_diagnostics", "independent_reconciliation"]},
            "evaluation_design": "Six annual expanding folds 2019-2024; one OLS per fold; 216h purge; complete label outcomes before boundary; four frozen profiles; matched NFCI-available universe.",
            "leakage_controls": ["FEATURES_AVAILABLE_BY_SIGNAL_TIME",
                                 "NFCI_CONSERVATIVE_NEXT_CALENDAR_DAY_AVAILABILITY",
                                 "NFCI_POINT_IN_TIME_VINTAGE_NO_FUTURE_REVISION",
                                 "RAW_INTERACTIONS_BEFORE_TRAINING_ONLY_SCALING",
                                 "TRAINING_SIGNAL_AND_OUTCOME_STRICTLY_BEFORE_VALIDATION_MINUS_216H",
                                 "NO_VALIDATION_REFIT_SELECTION_OR_POST_CUTOFF_ACCESS"],
            "parameter_space": {
                "allocation_id": ALLOCATION_ID, "architecture": ARCHITECTURE,
                "root_family": ROOT_FAMILY, "hypothesis_id": HYPOTHESIS_ID,
                "variant": variant, "features": list(FEATURES[variant]),
                "feature_count": len(FEATURES[variant]), "nfci_direct_feature": False,
                "interaction_count": 8 if primary else 0, "interaction_subsets_searched": 0,
                "context_transforms_searched": 0, "numeric_parameter_variants": 0,
                "threshold_searches": 0, "signal_threshold": 0.0,
                "update_cadence": "ONCE_PER_FOLD_NO_VALIDATION_REFIT",
                "declared_trial_budget": {"configurations": 1, "profiles": 4,
                                          "model_fits": 6, "seeds": 0, "total_trials": 4},
                "behavior_hash": decision["behavior_hash"],
                "structural_hash": decision["structural_hash"],
                "executable_spec_hash": decision["executable_spec_hash"],
                "dependencies": dependencies,
            },
            "code_config_reference": sha256(ROOT / config_path(variant)),
            "cost_execution_reference": "BACKTEST_ENGINE_V2 / EXECUTION_MODEL_V2 / BTCUSDT_SPOT_COST_V1",
            "seeds": [0], "trial_budget": 4,
            "stopping_rule": "Exactly four frozen profiles; no context transform, interaction subset, threshold, feature, model, or post-result variant.",
        })
    print(json.dumps({"admission": admission["family_classification"],
                      "experiments": list(EXPERIMENTS.values())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
