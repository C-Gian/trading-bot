"""Regenerate the WP-011 novelty admission, allocation, family and preregistrations.

Deterministic: the admission binds the current implementation hashes, so this must be
re-run after any change to a declared dependency and before any market result exists.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.wp011 import (
    ADMISSION_PATH,
    ALLOCATION_ID,
    ALLOCATION_PATH,
    EXPERIMENTS,
    FAMILY_PATH,
    HYPOTHESIS_ID,
    PRIMARY_VARIANT,
    ROOT_FAMILY,
    VARIANTS,
    dependency_manifest,
    novelty_decision,
    preflight,
    sha256,
)

CREATED_AT = "2026-09-12T00:00:00Z"


def write(relative: str, payload: object) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def prior_accounting() -> dict[str, int]:
    """Accounting as it stands without this allocation, so nothing double-counts."""
    path = ROOT / ALLOCATION_PATH
    saved = path.read_text(encoding="utf-8") if path.is_file() else None
    if saved is not None:
        path.unlink()
    try:
        from app.research.registry import cumulative_accounting

        return cumulative_accounting(ROOT)
    finally:
        if saved is not None:
            path.write_text(saved, encoding="utf-8", newline="\n")


def main() -> int:
    prior = prior_accounting()
    write(ADMISSION_PATH, novelty_decision(ROOT))
    write(
        FAMILY_PATH,
        {
            "schema_version": 1,
            "family_id": ROOT_FAMILY,
            "parent_family_id": None,
            "work_package": "WP-011",
            "status": "ADMITTED_PENDING_RESULTS",
            "allocation_id": ALLOCATION_ID,
            "admitted_by": ADMISSION_PATH,
            "aliases": [HYPOTHESIS_ID, *VARIANTS],
            "entry_event_anchors": ["PREDICTED_DEFAULT_NET_R_STRICTLY_ABOVE_ZERO"],
            "information_source": (
                "INTERNAL_PRICE_VOLATILITY_VOLUME_AND_TAKER_FLOW_DESCRIPTORS_PLUS_"
                "POINT_IN_TIME_ALFRED_MACRO_FINANCIAL_CONTEXT"
            ),
            "mechanism": (
                "A recency-weighted linear combination refitted at the first UTC hour of each "
                "calendar month may let feature importance drift through time and may rank "
                "default-cost long opportunity quality; predictive, not causal."
            ),
            "legitimate_revisit": (
                "A new Research Director allocation with explicit accounting. Half-life, "
                "feature set, label, threshold, regularization, cadence, barrier or horizon "
                "drift is not this experiment."
            ),
            "failure_experiment_ids": [],
        },
    )
    write(
        ALLOCATION_PATH,
        {
            "schema_version": 1,
            "allocation_id": ALLOCATION_ID,
            "work_package": "WP-011",
            "authority": "tasks/CURRENT_TASK.md",
            "review_authority": "reports/reviews/WP-008-RESEARCH-DIRECTOR-REVIEW.md",
            "kind": "RESULT_DEPENDENT_NEW_ADAPTIVE_MODEL_FAMILY_ALLOCATION",
            "root_family": ROOT_FAMILY,
            "hypothesis_id": HYPOTHESIS_ID,
            "primary_variant": PRIMARY_VARIANT,
            "experiment_ids": [EXPERIMENTS[v] for v in VARIANTS],
            "conditionality": (
                "Execution requires committed admission and preregistrations, verified ALFRED "
                "point-in-time integrity, full-rank weighted fits, purge containment, and zero "
                "sealed access."
            ),
            "new_economic_hypotheses": 1,
            "model_configurations": 2,
            "profiles": ["DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"],
            "profiles_per_configuration": 4,
            "profile_evaluations": 8,
            "supervised_model_fits": 144,
            "monthly_models_per_configuration": 72,
            "numeric_parameter_variants": 0,
            "algorithm_variants": 0,
            "hyperparameter_searches": 0,
            "threshold_searches": 0,
            "half_life_variants": 0,
            "feature_subset_searches": 0,
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
            "prior_family_budget_policy": (
                "All prior family budgets and dispositions remain unchanged; this adaptive "
                "root resets nothing and does not reopen FAM-SUPERVISED-LINEAR."
            ),
        },
    )

    admission = json.loads((ROOT / ADMISSION_PATH).read_text(encoding="utf-8"))
    dependencies = dependency_manifest(ROOT)
    for variant, item in zip(VARIANTS, admission["variants"], strict=True):
        features = [entry["name"] for entry in item["spec"]["features"]]
        write(
            f"research/experiments/{EXPERIMENTS[variant]}/preregistration.json",
            {
                "schema_version": 2,
                "experiment_id": EXPERIMENTS[variant],
                "experiment_version": 1,
                "created_at_utc": CREATED_AT,
                "hypothesis": (
                    "A prospectively fixed recency-weighted linear combination of internal "
                    "market features and point-in-time macro context, refitted monthly, can "
                    "adapt feature importance through time sufficiently to select BTCUSDT LONG "
                    "opportunities with robust positive net expectancy after realistic costs."
                    if variant == PRIMARY_VARIANT
                    else "The same adaptive architecture restricted to the eight internal "
                    "features measures whether point-in-time macro information adds anything."
                ),
                "rationale": (
                    "WP-008 falsified only fixed global linear weights over eight internal "
                    "features. Time-varying weights, macro information and recency weighting "
                    "were never tested. This is predictive, not causal."
                ),
                "research_scope": "DEVELOPMENT_WALK_FORWARD_NO_SEALED_ACCESS_NO_PAPER_EVIDENCE",
                "dataset": {
                    "manifest_id": "BTCUSDT-SPOT-1M-DEV-v1",
                    "content_hash": item["spec"]["dataset"]["content_hash"],
                    "maximum_timestamp": "2024-12-31T23:59:00Z",
                },
                "metrics": {
                    "primary": "POOLED_VALID_RESOLVED_DEFAULT_NET_R",
                    "secondary": [
                        "profiles",
                        "terminal_classification",
                        "monthly_models",
                        "coefficient_trajectories",
                        "grouped_contribution_stability",
                        "prediction_diagnostics",
                        "macro_incremental_comparison",
                        "artifact_manifest",
                    ],
                },
                "evaluation_design": (
                    "Six frozen annual folds 2019-2024. One exponentially weighted least "
                    "squares model becomes effective at the first UTC hour of each calendar "
                    "month and is held fixed until the next. Training uses every eligible "
                    "historical row whose signal instant and complete label outcome both "
                    "precede effective-216h, weighted by a frozen 180-day half-life. Four "
                    "fixed execution profiles."
                ),
                "leakage_controls": [
                    "FEATURES_AVAILABLE_BY_SIGNAL_TIME",
                    "MACRO_CONSERVATIVE_NEXT_CALENDAR_DAY_AVAILABILITY",
                    "MACRO_POINT_IN_TIME_VINTAGE_NO_FUTURE_REVISION",
                    "COMPLETED_CONTIGUOUS_UNQUARANTINED_WINDOWS",
                    "TRAINING_ONLY_DEFAULT_LABELS",
                    "TRAINING_ONLY_WEIGHTED_SCALING",
                    "TRAINING_SIGNAL_AND_OUTCOME_STRICTLY_BEFORE_EFFECTIVE_MINUS_216H",
                    "NO_VALIDATION_REFIT_OR_FEATURE_SELECTION",
                    "POST_CUTOFF_HARD_FAIL",
                ],
                "cost_execution_reference": (
                    "BACKTEST_ENGINE_V2 / EXECUTION_MODEL_V2 / BTCUSDT_SPOT_COST_V1"
                ),
                "parameter_space": {
                    "allocation_id": ALLOCATION_ID,
                    "root_family": ROOT_FAMILY,
                    "hypothesis_id": HYPOTHESIS_ID,
                    "variant": variant,
                    "feature_count": len(features),
                    "features": features,
                    "half_life_days": 180,
                    "half_life_variants": 0,
                    "update_cadence": "FIRST_UTC_HOUR_OF_EACH_CALENDAR_MONTH",
                    "algorithm_variants": 0,
                    "numeric_parameter_variants": 0,
                    "hyperparameter_searches": 0,
                    "threshold_searches": 0,
                    "feature_subset_searches": 0,
                    "signal_threshold": 0.0,
                    "macro_source_version": "ALFRED_MACRO_CONTEXT_V1",
                    "macro_manifest_id": "ALFRED-MACRO-CONTEXT-DEV-v1",
                    "behavior_hash": item["behavior_hash"],
                    "structural_hash": item["structural_hash"],
                    "executable_spec_hash": item["executable_spec_hash"],
                    "declared_trial_budget": {
                        "configurations": 1,
                        "profiles": 4,
                        "model_fits": 72,
                        "seeds": 0,
                        "total_trials": 4,
                    },
                    "dependencies": dependencies,
                },
                "trial_budget": 4,
                "stopping_rule": (
                    "Exactly four frozen profiles for this configuration. No additional "
                    "experiment, half-life, feature subset, threshold or refit after observing "
                    "any result."
                ),
                "seeds": [0],
                "code_config_reference": sha256(
                    ROOT / f"research/configs/wp011/{variant.lower()}.json"
                ),
                "status": "PREREGISTERED",
            },
        )

    report = preflight(ROOT)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
