"""Record the WP-011 outcome: experiment results, ledger, outcomes and comparisons.

Runs only after the walk-forward produced its comparison artifact. Nothing here alters
the experiment; it transcribes what was measured, including a negative result.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.wp011 import (
    ABLATION_VARIANT,
    ALLOCATION_ID,
    EXPERIMENTS,
    HYPOTHESIS_ID,
    LEDGER_PATH,
    OUTCOMES_PATH,
    PRIMARY_VARIANT,
    ROOT_FAMILY,
    VARIANTS,
    load_protocol,
    sha256,
)

COMPARISON_PATH = "reports/research/WP-011-COMPARISON.json"
HISTORICAL_PATH = "reports/research/WP-011-HISTORICAL-COMPARISON.json"
COMPLETED_AT = "2026-09-12T00:00:00Z"
ROLES = {
    PRIMARY_VARIANT: "ECONOMIC_CORE",
    ABLATION_VARIANT: "STRUCTURAL_ABLATION_VARIANT",
}
MECHANISM = (
    "A recency-weighted linear combination refitted monthly over internal market features "
    "and point-in-time macro context may rank default-cost long opportunity quality; "
    "predictive, not causal."
)


def write_json(relative: str, payload: Any) -> str:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return sha256(path)


def write_lines(relative: str, records: list[dict[str, Any]]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
            for record in records
        ),
        encoding="utf-8",
        newline="\n",
    )


def historical_comparison(comparison: dict[str, Any]) -> dict[str, Any]:
    """Descriptive only. Trade sets are not paired and are never presented as if they were."""
    priors = []
    for experiment_id in (
        "EXP-CTRL-006-NO-TRADE",
        "EXP-CTRL-002-RANDOM",
        "EXP-BASE-003-TREND",
        "EXP-BASE-004-BREAKOUT",
        "EXP-ALG-009-ALIGNED",
        "EXP-ALG-010-PULLBACK-RECOVERY-CORE",
        "EXP-ALG-012-ORDERFLOW-CORE",
        "EXP-ML-014-LINEAR-NET-R-FULL",
    ):
        path = ROOT / f"research/experiments/{experiment_id}/result.json"
        if not path.is_file():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        secondary = record.get("secondary_results") or {}
        priors.append(
            {
                "experiment_id": experiment_id,
                "primary_result": record.get("primary_result"),
                "terminal_classification": secondary.get("terminal_classification"),
                "trade_count": secondary.get("trade_count"),
            }
        )
    primary = comparison["configurations"][PRIMARY_VARIANT]["profiles"]["DEFAULT"]
    return {
        "schema_version": 1,
        "work_package": "WP-011",
        "comparison_basis": "DESCRIPTIVE_ONLY_TRADE_SETS_ARE_NOT_PAIRED",
        "caveat": (
            "Eligibility universes, entry events and trade counts differ across families. "
            "These numbers are not a matched-control comparison and no significance claim "
            "is made."
        ),
        "wp011_primary": {
            "experiment_id": EXPERIMENTS[PRIMARY_VARIANT],
            "primary_result": primary["net_expectancy_r"],
            "terminal_classification": comparison["configurations"][PRIMARY_VARIANT][
                "terminal_classification"
            ],
            "trade_count": primary["trade_count"],
        },
        "wp011_ablation": {
            "experiment_id": EXPERIMENTS[ABLATION_VARIANT],
            "primary_result": comparison["configurations"][ABLATION_VARIANT]["profiles"]["DEFAULT"][
                "net_expectancy_r"
            ],
            "terminal_classification": comparison["configurations"][ABLATION_VARIANT][
                "terminal_classification"
            ],
            "trade_count": comparison["configurations"][ABLATION_VARIANT]["profiles"]["DEFAULT"][
                "trade_count"
            ],
        },
        "historical": priors,
    }


def main() -> int:
    protocol = load_protocol(ROOT)
    comparison = json.loads((ROOT / COMPARISON_PATH).read_text(encoding="utf-8"))
    reconciliation = json.loads(
        (ROOT / "reports/validation/WP-011-MODEL-RECONCILIATION.json").read_text(encoding="utf-8")
    )

    ledger: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    admission = json.loads(
        (ROOT / "research/memory/registry/admissions/WP011-NOVELTY-ADMISSION.json").read_text(
            encoding="utf-8"
        )
    )

    for variant, item in zip(VARIANTS, admission["variants"], strict=True):
        experiment_id = EXPERIMENTS[variant]
        config = comparison["configurations"][variant]
        default = config["profiles"]["DEFAULT"]
        prereg_relative = f"research/experiments/{experiment_id}/preregistration.json"
        prereg = json.loads((ROOT / prereg_relative).read_text(encoding="utf-8"))
        result = {
            "schema_version": 2,
            "experiment_id": experiment_id,
            "experiment_version": 1,
            "preregistration_reference": prereg_relative,
            "preregistration_created_at_utc": prereg["created_at_utc"],
            "completed_at_utc": COMPLETED_AT,
            "status": "COMPLETED",
            "code_config_reference": prereg["code_config_reference"],
            "dataset": prereg["dataset"],
            "seed_reference": 0,
            "primary_result": default["net_expectancy_r"],
            "secondary_results": {
                "terminal_classification": config["terminal_classification"],
                "trade_count": default["trade_count"],
                "cumulative_net_r": default["cumulative_net_r"],
                "nonnegative_fold_count": default["nonnegative_fold_count"],
                "minimum_fold_trade_count": default["minimum_fold_trade_count"],
                "profiles": {
                    profile: config["profiles"][profile]["net_expectancy_r"]
                    for profile in ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")
                },
                "monthly_models": config["monthly_models"],
                "pooled_prediction_label_pearson": config["validation_diagnostics"][
                    "pooled_prediction_label_pearson"
                ],
                "feature_count": config["feature_count"],
                "half_life_days": protocol["training"]["half_life_days"],
                "update_cadence": protocol["model"]["update_cadence"],
                "independent_reconciliation": reconciliation["status"],
                "sealed_queries": 0,
            },
            "artifacts": [
                COMPARISON_PATH,
                f"research/experiments/{experiment_id}/monthly-models.json",
                f"reports/research/WP-011-COEFFICIENT-TRAJECTORIES-{variant}.json",
                "reports/validation/WP-011-MODEL-RECONCILIATION.json",
                "reports/validation/WP-011-MACRO-ASOF-AUDIT.json",
            ],
            "validation_outcome": "PASS" if reconciliation["status"] == "PASS" else "FAIL",
            "interpretation": (
                "EXPOSED DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE. "
                "Monthly recency-weighted least squares with training-only weighted scaling "
                "and labels; no tuning, no half-life search and no validation refit."
            ),
            "trial_accounting": {"declared_budget": 4, "executed_trials": 4},
            "run_identity_hash": hashlib.sha256(
                json.dumps(
                    {
                        "variant": variant,
                        "behavior_hash": item["behavior_hash"],
                        "artifact": comparison["artifact"]["logical_sha256"],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
        }
        result_relative = f"research/experiments/{experiment_id}/result.json"
        result_hash = write_json(result_relative, result)

        ledger.append(
            {
                "schema_version": 2,
                "experiment_id": experiment_id,
                "work_package": "WP-011",
                "record_kind": "PREREGISTERED_ADMISSION",
                "strategy_label": variant,
                "root_family": ROOT_FAMILY,
                "hypothesis_id": HYPOTHESIS_ID,
                "hypothesis_role": ROLES[variant],
                "claimed_market_mechanism": MECHANISM,
                "allocation_id": ALLOCATION_ID,
                "classification": item["classification"],
                "matched_experiment_ids": item["matched_experiment_ids"],
                "behavior_hash": item["behavior_hash"],
                "structural_hash": item["structural_hash"],
                "executable_spec_hash": item["executable_spec_hash"],
                "dependency_hash": item["dependency_hash"],
                "parent_experiment_ids": (
                    [] if variant == PRIMARY_VARIANT else [EXPERIMENTS[PRIMARY_VARIANT]]
                ),
                "novelty": item["classification"],
                "scientific_reason": (
                    "The sixteen-feature adaptive configuration is the family primary."
                    if variant == PRIMARY_VARIANT
                    else "The internal-only configuration isolates the macro contribution."
                ),
                "budget_units": {
                    "experiments": 1,
                    "strategy_variants": 1,
                    "trials": 4,
                    "numeric_parameter_variants": 0,
                },
                "preregistration_path": prereg_relative,
                "preregistration_sha256": sha256(ROOT / prereg_relative),
                "result_path": result_relative,
                "outcome_reference": experiment_id,
            }
        )
        classification = config["terminal_classification"]
        outcomes.append(
            {
                "schema_version": 1,
                "experiment_id": experiment_id,
                "result_path": result_relative,
                "result_sha256": result_hash,
                "terminal_classification": classification,
                "conclusion": (
                    "Frozen leakage-safe adaptive walk-forward with monthly recency-weighted "
                    f"refits: {classification}; no sealed query, Champion, or paper action."
                ),
                "falsified": (
                    "The time-varying internal-plus-macro net-profitability/stability claim "
                    "failed its predeclared hurdles."
                    if classification.startswith("REJECT")
                    else "No predeclared hurdle was falsified by this configuration."
                ),
                "not_falsified": (
                    "Other half-lives, cadences, feature families, non-linear models, labels, "
                    "thresholds, exits, horizons, assets and prospective evidence remain "
                    "untested."
                ),
                "evidence_facts": [
                    {"json_pointer": "/primary_result", "expected_value": result["primary_result"]},
                    {
                        "json_pointer": "/secondary_results/terminal_classification",
                        "expected_value": classification,
                    },
                ],
                "failure_modes": [classification] if classification.startswith("REJECT") else [],
                "legitimate_revisit": (
                    "Only under a new explicit cumulative Research Director allocation; do not "
                    "tune this exposed family after results."
                ),
            }
        )

    write_lines(LEDGER_PATH, ledger)
    write_lines(OUTCOMES_PATH, outcomes)
    write_json(HISTORICAL_PATH, historical_comparison(comparison))
    print("family disposition:", comparison["family_disposition"])
    print("reconciliation:", reconciliation["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
