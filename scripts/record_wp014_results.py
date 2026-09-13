"""Record immutable WP-014 outcomes after independent reconciliation passes."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.registry import all_families, cumulative_accounting
from app.research.sealed_eligibility import write_eligibility_table
from app.research.wp014 import (
    ADMISSION_PATH,
    ALLOCATION_ID,
    CONTROL_VARIANT,
    EXPERIMENTS,
    HYPOTHESIS_ID,
    LEDGER_PATH,
    OUTCOMES_PATH,
    PRIMARY_VARIANT,
    ROLES,
    ROOT_FAMILY,
    VARIANTS,
    load_protocol,
    sha256,
)

COMPARISON_PATH = "reports/research/WP-014-COMPARISON.json"
DIAGNOSTICS_PATH = "reports/research/WP-014-NONLINEAR-DIAGNOSTICS.json"
HISTORICAL_PATH = "reports/research/WP-014-HISTORICAL-COMPARISON.json"
QUESTIONS_PATH = "reports/research/WP-014-SCIENTIFIC-QUESTIONS.json"
RESEARCH_REPORT_PATH = "reports/research/WP-014-SHALLOW-NONLINEAR.md"
RECONCILIATION_PATH = "reports/validation/WP-014-MODEL-RECONCILIATION.json"
CHECKPOINT_PATH = "reports/checkpoints/WP-014.md"
COMPLETED_AT = "2026-09-13T10:00:00Z"
PRIORS = {
    "WP-008 LINEAR_FULL": "EXP-ML-014-LINEAR-NET-R-FULL",
    "WP-011 EWLS_INTERNAL_ONLY": "EXP-ML-017-EWLS-INTERNAL-ONLY",
    "WP-012 GLOBAL_SINGLE_EXPERT_MATCHED": "EXP-ML-019-GLOBAL-MATCHED-CONTROL",
    "WP-013 INTERNAL_ONLY_MATCHED_NFCI": "EXP-ML-021-INTERNAL-NFCI-MATCHED",
    "ALIGNED": "EXP-ALG-009-ALIGNED",
    "breakout": "EXP-BASE-004-BREAKOUT",
    "no-trade": "EXP-CTRL-006-NO-TRADE",
}


def read_json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


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


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def profile(config: dict[str, Any], name: str) -> dict[str, Any]:
    return config["profiles"][name]


def historical(comparison: dict[str, Any]) -> dict[str, Any]:
    records = []
    for label, experiment in PRIORS.items():
        result = read_json(f"research/experiments/{experiment}/result.json")
        secondary = result.get("secondary_results") or {}
        records.append(
            {
                "label": label,
                "experiment_id": experiment,
                "primary_result": result.get("primary_result"),
                "terminal_classification": secondary.get("terminal_classification"),
                "trade_count": secondary.get("trade_count")
                or secondary.get("annual_folds", {}).get("trade_count"),
            }
        )
    return {
        "schema_version": 1,
        "work_package": "WP-014",
        "comparison_basis": "DESCRIPTIVE_ONLY_EXCEPT_WITHIN_WP014_MATCHED_ELIGIBLE_UNIVERSE",
        "caveat": (
            "Historical families and executed trade sets differ; no paired claim is made. "
            "WP-014 configurations share eligible hours but predictions and occupancy differ."
        ),
        "wp014": {
            variant: {
                "experiment_id": EXPERIMENTS[variant],
                "primary_result": comparison["configurations"][variant]["primary_result"],
                "terminal_classification": comparison["configurations"][variant][
                    "terminal_classification"
                ],
                "trade_count": profile(comparison["configurations"][variant], "DEFAULT")["metrics"][
                    "trade_count"
                ],
            }
            for variant in VARIANTS
        },
        "primary_vs_control": comparison["primary_vs_control"],
        "historical": records,
    }


def scientific_questions(comparison: dict[str, Any], history: dict[str, Any]) -> dict[str, Any]:
    primary = comparison["configurations"][PRIMARY_VARIANT]
    control = comparison["configurations"][CONTROL_VARIANT]
    default = profile(primary, "DEFAULT")
    difference = comparison["primary_vs_control"]["default_net_expectancy_difference_r"]
    primary_corr = primary["prediction_diagnostics"]["pooled_prediction_label_pearson"]
    control_corr = control["prediction_diagnostics"]["pooled_prediction_label_pearson"]
    broad = default["stability"]["nonnegative_fold_count"] >= 4
    useful = difference > 0 and primary["primary_result"] > 0 and broad
    aligned = next(item for item in history["historical"] if item["label"] == "ALIGNED")
    return {
        "schema_version": 1,
        "work_package": "WP-014",
        "answers": {
            "1_hgbr_beats_internal_linear_matched": {
                "answer": difference > 0,
                "default_expectancy_difference_r": difference,
            },
            "2_default_expectancy_positive": {
                "answer": primary["primary_result"] > 0,
                "net_expectancy_r": primary["primary_result"],
            },
            "3_improvement_broad_across_folds": {
                "answer": broad,
                "nonnegative_folds": default["stability"]["nonnegative_fold_count"],
            },
            "4_double_viable": {
                "answer": profile(primary, "DOUBLE")["metrics"]["net_expectancy_r"] >= 0,
                "net_expectancy_r": profile(primary, "DOUBLE")["metrics"]["net_expectancy_r"],
            },
            "5_delay_preserves_result": {
                "answer": profile(primary, "DELAY_1H")["metrics"]["net_expectancy_r"] > 0,
                "net_expectancy_r": profile(primary, "DELAY_1H")["metrics"]["net_expectancy_r"],
            },
            "6_oos_correlation_materially_improves": {
                "answer": primary_corr is not None
                and control_corr is not None
                and primary_corr > control_corr,
                "hgbr": primary_corr,
                "control": control_corr,
                "difference": primary_corr - control_corr,
            },
            "7_conditional_structure_or_degrees_of_freedom": {
                "answer": (
                    "USEFUL_CONDITIONAL_STRUCTURE_SUPPORTED"
                    if useful
                    else "NO_ROBUST_USEFUL_NONLINEARITY; ADDED_DEGREES_DID_NOT_CLEAR_HURDLES"
                ),
                "diagnostics_not_used_for_adaptation": True,
            },
            "8_descriptive_comparison_to_aligned": {
                "hgbr_default_net_expectancy_r": primary["primary_result"],
                "aligned_primary_result": aligned["primary_result"],
                "paired": False,
            },
        },
    }


def sealed_status(classification: str) -> str:
    if classification == "PROMISING_DEVELOPMENT_ONLY":
        return "DEVELOPMENT_ELIGIBLE_PENDING_RESEARCH_DIRECTOR_REVIEW"
    if classification == "INCONCLUSIVE":
        return "NOT_ELIGIBLE_INCONCLUSIVE"
    return "NOT_ELIGIBLE_REJECTED"


def main() -> int:
    load_protocol(ROOT)
    comparison = read_json(COMPARISON_PATH)
    diagnostics = read_json(DIAGNOSTICS_PATH)
    reconciliation = read_json(RECONCILIATION_PATH)
    if reconciliation["status"] != "PASS":
        raise RuntimeError("refusing to record unreconciled WP-014 results")
    safe_commit = git("rev-parse", "HEAD")
    if any(
        (ROOT / f"research/experiments/{experiment}/result.json").exists()
        for experiment in EXPERIMENTS.values()
    ):
        raise RuntimeError("WP-014 results already recorded")
    history = historical(comparison)
    write_json(HISTORICAL_PATH, history)
    questions = scientific_questions(comparison, history)
    write_json(QUESTIONS_PATH, questions)
    admission = read_json(ADMISSION_PATH)
    ledger: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    for admitted in admission["variants"]:
        variant = admitted["variant"]
        experiment = EXPERIMENTS[variant]
        config = comparison["configurations"][variant]
        default = profile(config, "DEFAULT")
        prereg_path = f"research/experiments/{experiment}/preregistration.json"
        preregistration = read_json(prereg_path)
        result = {
            "schema_version": 2,
            "experiment_id": experiment,
            "experiment_version": 1,
            "preregistration_reference": experiment,
            "preregistration_created_at_utc": preregistration["created_at_utc"],
            "completed_at_utc": COMPLETED_AT,
            "status": "COMPLETED",
            "code_config_reference": preregistration["code_config_reference"],
            "dataset": {
                "manifest_id": preregistration["dataset"]["manifest_id"],
                "content_hash": preregistration["dataset"]["content_hash"],
            },
            "seed_reference": [0],
            "primary_result": config["primary_result"],
            "secondary_results": {
                "terminal_classification": config["terminal_classification"],
                "profiles": {
                    name: {
                        "net_expectancy_r": profile(config, name)["metrics"]["net_expectancy_r"],
                        "cumulative_net_r": profile(config, name)["metrics"]["cumulative_net_r"],
                        "trade_count": profile(config, name)["metrics"]["trade_count"],
                    }
                    for name in ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")
                },
                "annual_folds": {
                    "folds": default["folds"],
                    "trade_count": default["metrics"]["trade_count"],
                    "cumulative_net_r": default["metrics"]["cumulative_net_r"],
                    "nonnegative_fold_count": default["stability"]["nonnegative_fold_count"],
                    "minimum_fold_trade_count": default["diagnostics"]["minimum_fold_trades"],
                    "trade_ess": default["diagnostics"]["trade_ess"],
                    "model_fits": config["model_fits"],
                },
                "prediction_diagnostics": config["prediction_diagnostics"],
                "nonlinear_fold_diagnostics": (
                    diagnostics["configurations"][variant]["folds"]
                    if variant == PRIMARY_VARIANT
                    else []
                ),
                "matched_control_duplicate_of": (
                    "EXP-ML-014-LINEAR-NET-R-FULL" if variant == CONTROL_VARIANT else None
                ),
                "independent_reconciliation": reconciliation["status"],
            },
            "artifacts": [
                COMPARISON_PATH,
                DIAGNOSTICS_PATH,
                HISTORICAL_PATH,
                QUESTIONS_PATH,
                f"research/experiments/{experiment}/fold-models.json",
                RECONCILIATION_PATH,
                "reports/validation/WP-014-PREFLIGHT.json",
            ],
            "validation_outcome": "PASS",
            "interpretation": (
                "EXPOSED DEVELOPMENT RESEARCH, PREDICTIVE NOT CAUSAL. One fixed shallow "
                "HGBR and one disclosed duplicate matched OLS control; no tuning or sealed access."
            ),
            "trial_accounting": {"declared_budget": 4, "executed_trials": 4},
            "run_identity_hash": hashlib.sha256(
                json.dumps(
                    {
                        "variant": variant,
                        "behavior_hash": admitted["behavior_hash"],
                        "artifact": comparison["artifact"]["logical_sha256"],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
        }
        result_path = f"research/experiments/{experiment}/result.json"
        result_hash = write_json(result_path, result)
        ledger.append(
            {
                "schema_version": 2,
                "experiment_id": experiment,
                "work_package": "WP-014",
                "record_kind": (
                    "PREREGISTERED_ADMISSION"
                    if variant == PRIMARY_VARIANT
                    else "PREREGISTERED_MATCHED_DUPLICATE_CONTROL"
                ),
                "strategy_label": variant,
                "root_family": ROOT_FAMILY,
                "hypothesis_id": HYPOTHESIS_ID,
                "hypothesis_role": ROLES[variant],
                "claimed_market_mechanism": (
                    "Fixed shallow HGBR may capture conditional/intersection structure among F1-F8."
                ),
                "allocation_id": ALLOCATION_ID,
                "classification": admitted["classification"],
                "matched_experiment_ids": admitted["matched_experiment_ids"],
                "behavior_hash": admitted["behavior_hash"],
                "structural_hash": admitted["structural_hash"],
                "executable_spec_hash": admitted["executable_spec_hash"],
                "dependency_hash": admitted["dependency_hash"],
                "parent_experiment_ids": (
                    [] if variant == PRIMARY_VARIANT else [EXPERIMENTS[PRIMARY_VARIANT]]
                ),
                "novelty": admitted["classification"],
                "scientific_reason": (
                    "Family primary fixed nonlinear mechanism."
                    if variant == PRIMARY_VARIANT
                    else "Matched duplicate OLS control; no novelty claim."
                ),
                "budget_units": {
                    "experiments": 1,
                    "strategy_variants": 1,
                    "trials": 4,
                    "numeric_parameter_variants": 0,
                },
                "preregistration_path": prereg_path,
                "preregistration_sha256": sha256(ROOT / prereg_path),
                "result_path": result_path,
                "outcome_reference": experiment,
            }
        )
        classification = config["terminal_classification"]
        outcomes.append(
            {
                "schema_version": 1,
                "experiment_id": experiment,
                "result_path": result_path,
                "result_sha256": result_hash,
                "terminal_classification": classification,
                "conclusion": (
                    f"Frozen WP-014 walk-forward: {classification}; no Champion, product change, "
                    "sealed query, or paper action."
                ),
                "falsified": (
                    "The preregistered robust after-cost expectancy claim failed."
                    if classification.startswith("REJECT")
                    else "No predeclared hurdle was falsified."
                ),
                "not_falsified": (
                    "Other prospectively allocated mechanisms remain untested; no tuning of this "
                    "exposed model is authorized."
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
                    "Only a new explicit cumulative Research Director allocation; no tuning."
                ),
            }
        )
    write_lines(LEDGER_PATH, ledger)
    write_lines(OUTCOMES_PATH, outcomes)
    eligibility_path = write_eligibility_table(ROOT)
    eligibility = read_json(str(eligibility_path.relative_to(ROOT)).replace("\\", "/"))

    primary = comparison["configurations"][PRIMARY_VARIANT]
    control = comparison["configurations"][CONTROL_VARIANT]
    default = profile(primary, "DEFAULT")
    report = f"""# WP-014 shallow nonlinear internal-signal challenger

WP-014 executed one fixed `SHALLOW_INTERNAL_HGBR_V1` configuration and one disclosed
duplicate matched OLS control over the exact frozen F1-F8 universe. No hyperparameter,
feature, threshold, architecture, or model-selection search occurred.

Primary DEFAULT expectancy was {primary["primary_result"]:+.10f} R/trade over
{default["metrics"]["trade_count"]} trades, with
{default["stability"]["nonnegative_fold_count"]}/6 nonnegative folds and minimum fold
count {default["diagnostics"]["minimum_fold_trades"]}. ZERO was
{profile(primary, "ZERO")["metrics"]["net_expectancy_r"]:+.10f}, DOUBLE was
{profile(primary, "DOUBLE")["metrics"]["net_expectancy_r"]:+.10f}, and DELAY_1H was
{profile(primary, "DELAY_1H")["metrics"]["net_expectancy_r"]:+.10f} R/trade. Pooled OOS
prediction/label Pearson correlation was
{primary["prediction_diagnostics"]["pooled_prediction_label_pearson"]:+.10f}.

The matched OLS DEFAULT expectancy was {control["primary_result"]:+.10f}; HGBR minus
control was {comparison["primary_vs_control"]["default_net_expectancy_difference_r"]:+.10f}
R/trade. Eligible hours were matched, but executed trade sets were not paired.

Primary classification: **{primary["terminal_classification"]}**. Independent
reconciliation passed at tolerance {reconciliation["prediction_tolerance"]} with zero
unexplained mismatches. Champion remains NONE, sealed queries remain zero, the ALIGNED
paper candidate is unchanged, and real money remains false.
"""
    (ROOT / RESEARCH_REPORT_PATH).write_text(report, encoding="utf-8", newline="\n")

    accounting = cumulative_accounting(ROOT)
    state = read_json("state/current_state.json")
    state["status"] = "EXECUTOR_COMPLETE_PENDING_REVIEW"
    state["experiments_completed"] = len(
        list((ROOT / "research/experiments").glob("*/result.json"))
    )
    state["latest_reviewed_checkpoint"] = "WP-013"
    state["latest_executor_checkpoint"] = "WP-014"
    state["next_recommended_work_package"] = "RESEARCH_DIRECTOR_REVIEW_WP_014"
    state["search_memory"] = {
        "version": "SEARCH_MEMORY_V2",
        "status": "VALIDATED",
        "families_tracked": len(all_families(ROOT)),
    }
    state["adaptive_search"] = accounting
    state["latest_family"] = {
        "name": "SHALLOW_INTERNAL_HGBR_V1",
        "root_family": ROOT_FAMILY,
        "primary_experiment_id": EXPERIMENTS[PRIMARY_VARIANT],
        "novelty_classification": "NEW_FAMILY",
        "terminal_classification": primary["terminal_classification"],
    }
    state["shallow_nonlinear_challenger"] = {
        "version": "SHALLOW_INTERNAL_HGBR_V1",
        "status": "VALIDATED",
        "root_family": ROOT_FAMILY,
        "primary": PRIMARY_VARIANT,
        "control": CONTROL_VARIANT,
        "control_novelty": "DUPLICATE_MATCHED_CONTROL_REPLICATION",
        "sklearn_version": "1.7.2",
        "reserved_model_fits": 12,
        "actual_model_fits": 12,
        "terminal_classification": primary["terminal_classification"],
        "model_reconciliation": "PASS",
        "sealed_eligibility": sealed_status(primary["terminal_classification"]),
        "safe_phase_1_commit": safe_commit,
    }
    state["remote_ci"]["work_packages"]["WP-013"] = {
        "status": "SUCCESS",
        "head": "e59318268099d428df0c108144aca739f5504b40",
        "run_id": 34745601715,
        "evidence": "reports/reviews/WP-013-CI-EVIDENCE.json",
    }
    state["sealed_evaluation"]["candidates_assessed"] = len(eligibility["candidates"])
    state["sealed_evaluation"]["seal_eligible_candidates"] = sum(
        item["sealed_eligibility"].startswith("DEVELOPMENT_ELIGIBLE")
        for item in eligibility["candidates"]
    )
    write_json("state/current_state.json", state)

    checkpoint = f"""# WP-014 checkpoint

WP-014 completed with **PASS** execution integrity and primary disposition
**{primary["terminal_classification"]}**.

The safe Phase-1 commit `{safe_commit}` froze exact F1-F8 inputs, the scikit-learn 1.7.2
HGBR parameters, raw tree inputs, matched OLS control, six annual folds, 216h purge,
complete label containment, four profiles, and zero search variants before results.
SEARCH_MEMORY admitted the nonlinear primary as NEW_FAMILY and truthfully disclosed the
OLS control as a duplicate replication of EXP-ML-014.

Primary DEFAULT was {primary["primary_result"]:+.10f} R/trade; matched OLS DEFAULT was
{control["primary_result"]:+.10f}; the difference was
{comparison["primary_vs_control"]["default_net_expectancy_difference_r"]:+.10f}. Independent
reconciliation passed with zero mismatches.

Accounting is {state["experiments_completed"]} experiments,
{accounting["material_economic_hypotheses"]} hypotheses,
{accounting["configuration_variants"]} configurations,
{accounting["profile_trials"]} profiles, {accounting["supervised_model_fits"]} reserved
supervised fits, and zero numeric variants or sealed queries. Champion remains NONE,
paper trades remain {state["paper_trades_completed"]}, ALIGNED is unchanged, and real
money remains false.

Next: Research Director review; no automatic tuning, product replacement, or sealed query.
"""
    (ROOT / CHECKPOINT_PATH).write_text(checkpoint, encoding="utf-8", newline="\n")
    task_path = ROOT / "tasks/CURRENT_TASK.md"
    completed_task = task_path.read_text(encoding="utf-8").replace(
        "## STATUS\nACTIVE", "## STATUS\nCOMPLETED", 1
    )
    task_path.write_text(completed_task, encoding="utf-8", newline="\n")
    archive = ROOT / "tasks/archive/WP-014.md"
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_text(completed_task, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "classification": primary["terminal_classification"],
                "experiments": state["experiments_completed"],
                "reconciliation": reconciliation["status"],
                "safe_phase_1_commit": safe_commit,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
