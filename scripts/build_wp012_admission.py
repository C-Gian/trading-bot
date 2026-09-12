"""Regenerate the WP-012 novelty admission, allocation, family and preregistrations.

Deterministic: the admission binds the current implementation hashes, so this must be
re-run after any change to a declared dependency and before any market result exists.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.wp012 import (
    ADMISSION_PATH,
    ALLOCATION_ID,
    ALLOCATION_PATH,
    ARCHITECTURE,
    CONTROL_VARIANT,
    EXPERIMENTS,
    FAMILY_PATH,
    HYPOTHESIS_ID,
    MAXIMUM_EXPERT_FITS,
    PRIMARY_VARIANT,
    ROOT_FAMILY,
    STEMS,
    VARIANTS,
    config_path,
    dependency_manifest,
    novelty_decision,
    preflight,
    sha256,
)

CREATED_AT = "2026-09-12T00:00:00Z"

HYPOTHESES = {
    PRIMARY_VARIANT: (
        "The relationship between the eight frozen internal features and forward net R "
        "differs between financial regimes, so two independently fitted experts selected by "
        "a point-in-time NFCI gate can select BTCUSDT LONG opportunities with robust "
        "positive net expectancy after realistic costs."
    ),
    CONTROL_VARIANT: (
        "A single unconditioned expert fitted on exactly the same eligible rows measures how "
        "much, if anything, the regime conditioning itself contributes."
    ),
}


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
            "work_package": "WP-012",
            "status": "ADMITTED_PENDING_RESULTS",
            "allocation_id": ALLOCATION_ID,
            "admitted_by": ADMISSION_PATH,
            "aliases": [HYPOTHESIS_ID, ARCHITECTURE, *VARIANTS],
            "entry_event_anchors": ["PREDICTED_DEFAULT_NET_R_STRICTLY_ABOVE_ZERO"],
            "information_source": (
                "INTERNAL_PRICE_VOLATILITY_VOLUME_AND_TAKER_FLOW_DESCRIPTORS_CONDITIONED_BY_"
                "POINT_IN_TIME_ALFRED_NFCI_FINANCIAL_CONDITIONS_REGIME"
            ),
            "mechanism": (
                "Financial conditions may change how internal market descriptors map to "
                "forward net R. Two disjoint experts, selected hour by hour by a fixed "
                "zero-threshold point-in-time NFCI gate, may rank default-cost long "
                "opportunity quality better than one global weight vector; predictive, not "
                "causal. No macro value enters an expert feature matrix."
            ),
            "legitimate_revisit": (
                "A new Research Director allocation with explicit accounting. A different "
                "threshold, macro variable, regime count, smoothing, hysteresis, lag variant, "
                "feature set, label, barrier or horizon is not this experiment."
            ),
            "failure_experiment_ids": [],
        },
    )
    write(
        ALLOCATION_PATH,
        {
            "schema_version": 1,
            "allocation_id": ALLOCATION_ID,
            "work_package": "WP-012",
            "authority": "tasks/CURRENT_TASK.md",
            "review_authority": "reports/reviews/WP-011-RESEARCH-DIRECTOR-REVIEW.md",
            "kind": "RESULT_DEPENDENT_NEW_CONDITIONED_MODEL_FAMILY_ALLOCATION",
            "root_family": ROOT_FAMILY,
            "hypothesis_id": HYPOTHESIS_ID,
            "architecture": ARCHITECTURE,
            "primary_variant": PRIMARY_VARIANT,
            "experiment_ids": [EXPERIMENTS[v] for v in VARIANTS],
            "conditionality": (
                "Execution requires committed admission and preregistrations, a passing "
                "point-in-time regime as-of audit, full-rank per-expert fits, purge "
                "containment, truthful abstention wherever a regime expert is infeasible, and "
                "zero sealed access."
            ),
            "new_economic_hypotheses": 1,
            "model_configurations": 2,
            "profiles": ["DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"],
            "profiles_per_configuration": 4,
            "profile_evaluations": 8,
            "maximum_expert_fits": MAXIMUM_EXPERT_FITS,
            "supervised_model_fits": MAXIMUM_EXPERT_FITS,
            "experts_per_fold": {PRIMARY_VARIANT: 2, CONTROL_VARIANT: 1},
            "numeric_parameter_variants": 0,
            "algorithm_variants": 0,
            "hyperparameter_searches": 0,
            "threshold_searches": 0,
            "regime_threshold_variants": 0,
            "regime_count_variants": 0,
            "macro_variable_variants": 0,
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
                "All prior family budgets and dispositions remain unchanged; this root resets "
                "nothing and reopens neither FAM-SUPERVISED-LINEAR nor FAM-ADAPTIVE-EWLS-MACRO."
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
                "hypothesis": HYPOTHESES[variant],
                "rationale": (
                    "WP-008 falsified one fixed global linear weight vector over these eight "
                    "features and WP-011 falsified adding point-in-time macro levels as "
                    "additive predictors. Neither tested conditioning: whether the mapping "
                    "itself differs between financial regimes. This is predictive, not causal."
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
                        "regime_diagnostics",
                        "expert_coefficient_comparison",
                        "infeasible_expert_accounting",
                        "uncovered_hour_accounting",
                        "prediction_diagnostics",
                        "artifact_manifest",
                    ],
                },
                "evaluation_design": (
                    "Six frozen annual folds 2019-2024. Each expert is fitted once per fold on "
                    "every eligible historical row whose signal instant and complete label "
                    "outcome both precede validation start minus 216 hours, partitioned by the "
                    "point-in-time regime of the signal hour. Coefficients are held fixed "
                    "across the validation year. Four fixed execution profiles. An infeasible "
                    "regime expert emits nothing and its hours are counted, never merged."
                ),
                "leakage_controls": [
                    "FEATURES_AVAILABLE_BY_SIGNAL_TIME",
                    "REGIME_CONSERVATIVE_NEXT_CALENDAR_DAY_AVAILABILITY",
                    "REGIME_POINT_IN_TIME_VINTAGE_NO_FUTURE_REVISION",
                    "COMPLETED_CONTIGUOUS_UNQUARANTINED_WINDOWS",
                    "TRAINING_ONLY_DEFAULT_LABELS",
                    "TRAINING_ONLY_PER_EXPERT_SCALING",
                    "TRAINING_SIGNAL_AND_OUTCOME_STRICTLY_BEFORE_VALIDATION_MINUS_216H",
                    "NO_VALIDATION_REFIT_OR_FEATURE_SELECTION",
                    "MISSING_REGIME_INELIGIBLE_NEVER_IMPUTED",
                    "POST_CUTOFF_HARD_FAIL",
                ],
                "cost_execution_reference": (
                    "BACKTEST_ENGINE_V2 / EXECUTION_MODEL_V2 / BTCUSDT_SPOT_COST_V1"
                ),
                "parameter_space": {
                    "allocation_id": ALLOCATION_ID,
                    "root_family": ROOT_FAMILY,
                    "hypothesis_id": HYPOTHESIS_ID,
                    "architecture": ARCHITECTURE,
                    "variant": variant,
                    "feature_count": len(features),
                    "features": features,
                    "experts_per_fold": item["spec"]["train_window_rule"]["conditioning"][
                        "experts_per_fold"
                    ],
                    "regime_version": "FINANCIAL_CONDITIONS_REGIME_V1",
                    "regime_series": "NFCI",
                    "regime_threshold": 0.0,
                    "regime_threshold_variants": 0,
                    "regime_count_variants": 0,
                    "macro_variable_variants": 0,
                    "macro_features_in_expert_matrix": 0,
                    "update_cadence": "ONCE_PER_FOLD_NO_VALIDATION_REFIT",
                    "algorithm_variants": 0,
                    "numeric_parameter_variants": 0,
                    "hyperparameter_searches": 0,
                    "threshold_searches": 0,
                    "feature_subset_searches": 0,
                    "signal_threshold": 0.0,
                    "regime_source_version": "ALFRED_MACRO_CONTEXT_V1",
                    "regime_manifest_id": "ALFRED-MACRO-CONTEXT-DEV-v1",
                    "behavior_hash": item["behavior_hash"],
                    "structural_hash": item["structural_hash"],
                    "executable_spec_hash": item["executable_spec_hash"],
                    "declared_trial_budget": {
                        "configurations": 1,
                        "profiles": 4,
                        "model_fits": 6
                        * item["spec"]["train_window_rule"]["conditioning"]["experts_per_fold"],
                        "seeds": 0,
                        "total_trials": 4,
                    },
                    "dependencies": dependencies,
                },
                "trial_budget": 4,
                "stopping_rule": (
                    "Exactly four frozen profiles for this configuration. No additional "
                    "experiment, threshold, macro variable, regime count, smoothing, "
                    "hysteresis, lag variant, feature subset or refit after observing any "
                    "result."
                ),
                "seeds": [0],
                "code_config_reference": sha256(ROOT / config_path(variant)),
                "status": "PREREGISTERED",
            },
        )

    report = preflight(ROOT)
    print(json.dumps(report, indent=2))
    print("config stems:", json.dumps(STEMS, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
