"""Run the fixed WP-008 SEARCH_MEMORY_V2 admission before any market result."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.registry import signatures
from app.research.wp004 import git
from app.research.wp008 import (
    ADMISSION_PATH,
    ALLOCATION_ID,
    ALLOCATION_PATH,
    FAMILY_PATH,
    HYPOTHESIS_ID,
    PRIMARY_VARIANT,
    REJECTION_PATH,
    ROOT_FAMILY,
    SPEC,
    NoveltyRejected,
    novelty_decisions,
)


def write_json(relative: str, payload: dict) -> None:
    path = ROOT / relative
    if path.exists():
        raise FileExistsError(f"immutable admission artifact already exists: {relative}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n")


def main() -> None:
    if git("branch", "--show-current", root=ROOT) != "main" or git(
        "status", "--porcelain", root=ROOT
    ):
        raise RuntimeError("WP-008 admission requires a clean local main")
    if any(
        (ROOT / "research/experiments" / experiment_id / "result.json").exists()
        for experiment_id in SPEC
    ):
        raise RuntimeError("market-derived WP-008 results already exist; chronology audit required")
    reference_count = len(signatures(ROOT))
    try:
        decisions = novelty_decisions(ROOT)
    except NoveltyRejected as exc:
        write_json(
            REJECTION_PATH,
            {
                "schema_version": 1,
                "version": "SEARCH_MEMORY_V2",
                "work_package": "WP-008",
                "proposed_root_family": ROOT_FAMILY,
                "proposed_hypothesis_id": HYPOTHESIS_ID,
                "admitted": False,
                "reason": str(exc),
                "market_results_observed_at_rejection": 0,
                "renamed_or_weakened": False,
            },
        )
        raise
    admission = {
        "schema_version": 1,
        "version": "SEARCH_MEMORY_V2",
        "work_package": "WP-008",
        "gate": "GOVERNED_MODEL_NOVELTY_ADMISSION_BEFORE_ANY_VALIDATION_RESULT",
        "proposed_root_family": ROOT_FAMILY,
        "proposed_hypothesis_id": HYPOTHESIS_ID,
        "family_classification": decisions[0]["classification"],
        "admitted": True,
        "market_results_observed_at_admission": 0,
        "classifier_modified": False,
        "renamed_to_force_novelty": False,
        "conditions_added_to_force_novelty": False,
        "reference_signatures": reference_count,
        "model_fingerprint_fields": [
            "algorithm",
            "label",
            "features",
            "train_window_rule",
            "scaling",
            "regularization",
            "hyperparameters",
            "signal_rule",
            "execution_geometry",
            "dataset",
            "cost_model_reference",
            "execution_model_reference",
        ],
        "variants": decisions,
    }
    allocation = {
        "schema_version": 1,
        "allocation_id": ALLOCATION_ID,
        "work_package": "WP-008",
        "kind": "RESULT_DEPENDENT_NEW_MODEL_FAMILY_ALLOCATION",
        "authority": "tasks/CURRENT_TASK.md",
        "review_authority": "reports/reviews/WP-007-RESEARCH-DIRECTOR-REVIEW.md",
        "root_family": ROOT_FAMILY,
        "hypothesis_id": HYPOTHESIS_ID,
        "primary_variant": PRIMARY_VARIANT,
        "experiment_ids": list(SPEC),
        "new_economic_hypotheses": 1,
        "model_configurations": 2,
        "numeric_parameter_variants": 0,
        "algorithm_variants": 0,
        "hyperparameter_searches": 0,
        "threshold_searches": 0,
        "profiles_per_configuration": 4,
        "profiles": ["DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"],
        "profile_evaluations": 8,
        "supervised_model_fits": 12,
        "family_limits": {
            "experiments": 2,
            "strategy_variants": 2,
            "trials": 8,
            "numeric_parameter_variants": 0,
        },
        "adaptive_decision_increment": 1,
        "result_dependent_fork_increment": 1,
        "prior_adaptive_decisions": 4,
        "prior_result_dependent_forks": 4,
        "cumulative_adaptive_decisions": 5,
        "cumulative_result_dependent_forks": 5,
        "sealed_queries": 0,
        "paper_observations": 0,
        "prior_family_budget_policy": "All prior family budgets and dispositions remain unchanged; this predictive model root resets nothing.",
        "conditionality": "Execution requires committed admission and preregistrations, leakage-safe fold containment, full-rank OLS fits, and zero sealed access.",
    }
    family = {
        "schema_version": 1,
        "family_id": ROOT_FAMILY,
        "aliases": [HYPOTHESIS_ID, "LINEAR_FULL", "LINEAR_NO_FLOW"],
        "entry_event_anchors": ["PREDICTED_DEFAULT_NET_R_STRICTLY_ABOVE_ZERO"],
        "parent_family_id": None,
        "admitted_by": ADMISSION_PATH,
        "allocation_id": ALLOCATION_ID,
        "work_package": "WP-008",
        "information_source": "FIXED_LOW_DIMENSIONAL_PRICE_VOLATILITY_VOLUME_REGIME_AND_TAKER_FLOW_DESCRIPTORS",
        "mechanism": "A fixed historical OLS combination may rank default-cost long opportunity quality; predictive, not causal.",
        "status": "ADMITTED_PENDING_RESULTS",
        "failure_experiment_ids": [],
        "legitimate_revisit": "A new Research Director allocation with explicit accounting; feature, label, threshold, regularization, algorithm, barrier, or horizon drift is not this experiment.",
    }
    write_json(ADMISSION_PATH, admission)
    write_json(ALLOCATION_PATH, allocation)
    write_json(FAMILY_PATH, family)
    print("LINEAR_FULL admitted NEW_FAMILY; LINEAR_NO_FLOW admitted structural ablation.")


if __name__ == "__main__":
    main()
