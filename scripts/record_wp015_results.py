"""Record immutable WP-015 outcomes after independent reconciliation passes."""

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
from app.research.wp015 import (
    ADMISSION_PATH,
    ALLOCATION_ID,
    CONTROL_VARIANT,
    EXPERIMENTS,
    FAMILY_PATH,
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

COMPARISON_PATH = "reports/research/WP-015-COMPARISON.json"
DIAGNOSTICS_PATH = "reports/research/WP-015-FUNDING-DIAGNOSTICS.json"
HISTORICAL_PATH = "reports/research/WP-015-HISTORICAL-COMPARISON.json"
QUESTIONS_PATH = "reports/research/WP-015-SCIENTIFIC-QUESTIONS.json"
RESEARCH_REPORT_PATH = "reports/research/WP-015-PERPETUAL-FUNDING.md"
RECONCILIATION_PATH = "reports/validation/WP-015-MODEL-RECONCILIATION.json"
CHECKPOINT_PATH = "reports/checkpoints/WP-015.md"
COMPLETED_AT = "2026-09-13T14:30:00Z"
PRIORS = {
    "WP-014 SHALLOW_INTERNAL_HGBR": "EXP-ML-022-SHALLOW-INTERNAL-HGBR",
    "WP-014 INTERNAL_LINEAR_MATCHED": "EXP-ML-023-INTERNAL-LINEAR-MATCHED",
    "WP-013 NFCI_CONTEXT_INTERACTIONS": "EXP-ML-020-NFCI-CONTEXT-INTERACTIONS",
    "WP-012 REGIME_TWO_EXPERTS": "EXP-ML-018-REGIME-TWO-EXPERTS",
    "WP-011 EWLS_INTERNAL_ONLY": "EXP-ML-017-EWLS-INTERNAL-ONLY",
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
        "work_package": "WP-015",
        "comparison_basis": "DESCRIPTIVE_ONLY_EXCEPT_WITHIN_WP015_MATCHED_UNIVERSE",
        "caveat": (
            "WP-015 uses matched 2020-2024 funding coverage. Prior 2019-2024 experiments "
            "and differing executed trade sets are not paired comparisons."
        ),
        "wp015": {
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


def scientific_questions(comparison: dict[str, Any], diagnostics: dict[str, Any]) -> dict[str, Any]:
    primary = comparison["configurations"][PRIMARY_VARIANT]
    control = comparison["configurations"][CONTROL_VARIANT]
    default = profile(primary, "DEFAULT")
    difference = comparison["primary_vs_control"]["default_net_expectancy_difference_r"]
    primary_corr = primary["prediction_diagnostics"]["pooled_prediction_label_pearson"]
    control_corr = control["prediction_diagnostics"]["pooled_prediction_label_pearson"]
    signs = diagnostics["default_trade_outcomes_by_funding_sign"]
    return {
        "schema_version": 1,
        "work_package": "WP-015",
        "answers": {
            "1_funding_improves_matched_hgbr": {
                "answer": difference > 0,
                "default_expectancy_difference_r": difference,
            },
            "2_primary_default_positive": {
                "answer": primary["primary_result"] > 0,
                "net_expectancy_r": primary["primary_result"],
            },
            "3_improvement_broad_2020_2024": {
                "answer": default["stability"]["nonnegative_fold_count"] >= 4,
                "nonnegative_folds": default["stability"]["nonnegative_fold_count"],
            },
            "4_double_survives": {
                "answer": profile(primary, "DOUBLE")["metrics"]["net_expectancy_r"] >= 0,
                "net_expectancy_r": profile(primary, "DOUBLE")["metrics"]["net_expectancy_r"],
            },
            "5_delay_preserves": {
                "answer": profile(primary, "DELAY_1H")["metrics"]["net_expectancy_r"] > 0,
                "net_expectancy_r": profile(primary, "DELAY_1H")["metrics"]["net_expectancy_r"],
            },
            "6_oos_correlation_improves_materially": {
                "answer": "NOT_ESTABLISHED",
                "primary": primary_corr,
                "control": control_corr,
                "difference": primary_corr - control_corr,
                "reason": "No prospective materiality threshold was declared.",
            },
            "7_incremental_value_consistent_with_funding_sign": {
                "answer": "DESCRIPTIVE_SIGN_ASSOCIATION_NOT_ROBUST_INCREMENTAL_VALUE",
                "negative_funding_mean_net_r": signs["NEGATIVE"]["mean_net_r"],
                "positive_funding_mean_net_r": signs["POSITIVE"]["mean_net_r"],
                "zero_group_trades": signs["ZERO"]["valid_resolved_trades"],
            },
            "8_useful_information_or_noisy_variable": {
                "answer": "NO_ROBUST_USEFUL_INCREMENTAL_POSITIONING_INFORMATION",
                "reason": "Relative improvement did not produce positive DEFAULT expectancy or any nonnegative fold.",
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
        raise RuntimeError("refusing to record unreconciled WP-015 results")
    safe_commit = git("rev-parse", "HEAD")
    if any(
        git("ls-files", f"research/experiments/{experiment}/result.json")
        for experiment in EXPERIMENTS.values()
    ):
        raise RuntimeError("WP-015 committed results already exist")
    history = historical(comparison)
    write_json(HISTORICAL_PATH, history)
    questions = scientific_questions(comparison, diagnostics)
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
                "profiles": {
                    name: {
                        "net_expectancy_r": profile(config, name)["metrics"]["net_expectancy_r"],
                        "cumulative_net_r": profile(config, name)["metrics"]["cumulative_net_r"],
                        "trade_count": profile(config, name)["metrics"]["trade_count"],
                    }
                    for name in ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")
                },
                "annual_folds": {
                    "terminal_classification": config["terminal_classification"],
                    "folds": default["folds"],
                    "trade_count": default["metrics"]["trade_count"],
                    "cumulative_net_r": default["metrics"]["cumulative_net_r"],
                    "nonnegative_fold_count": default["stability"]["nonnegative_fold_count"],
                    "minimum_fold_trade_count": default["diagnostics"]["minimum_fold_trades"],
                    "trade_ess": default["diagnostics"]["trade_ess"],
                    "model_fits": config["model_fits"],
                },
                "trade_ess_and_concentration": {
                    "trade_ess": default["diagnostics"]["trade_ess"],
                    "active_week_kish_count": default["diagnostics"]["active_week_kish_count"],
                    "max_fold_trade_share": default["stability"]["max_fold_trade_share"],
                },
                "prediction_positive_hours": {
                    "total": config["prediction_diagnostics"]["prediction_positive_hours"],
                    "per_fold": {
                        fold: record["prediction_positive_hours"]
                        for fold, record in config["prediction_diagnostics"]["per_fold"].items()
                    },
                },
                "oos_prediction_label_pearson": {
                    "pooled": config["prediction_diagnostics"]["pooled_prediction_label_pearson"],
                    "per_fold": {
                        fold: record["pearson"]
                        for fold, record in config["prediction_diagnostics"]["per_fold"].items()
                    },
                },
                "funding_distribution_and_sign_diagnostics": (
                    diagnostics
                    if variant == PRIMARY_VARIANT
                    else {
                        "matched_funding_eligible_universe": True,
                        "known_control_mechanism": "EXP-ML-022-SHALLOW-INTERNAL-HGBR",
                    }
                ),
                "independent_reconciliation": "PASS",
            },
            "artifacts": [
                COMPARISON_PATH,
                DIAGNOSTICS_PATH,
                HISTORICAL_PATH,
                QUESTIONS_PATH,
                f"research/experiments/{experiment}/fold-models.json",
                RECONCILIATION_PATH,
                "reports/validation/WP-015-PREFLIGHT.json",
            ],
            "validation_outcome": "PASS",
            "interpretation": (
                "EXPOSED DEVELOPMENT RESEARCH, PREDICTIVE NOT CAUSAL. Settled perpetual "
                "funding is information only; traded instrument remains BTCUSDT spot LONG."
            ),
            "trial_accounting": {"declared_budget": 4, "executed_trials": 4},
            "run_identity_hash": hashlib.sha256(
                json.dumps(
                    {
                        "variant": variant,
                        "behavior_hash": admitted["behavior_hash"],
                        "trials": comparison["trials_artifact"]["logical_sha256"],
                        "predictions": comparison["predictions_artifact"]["logical_sha256"],
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
                "work_package": "WP-015",
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
                    "Strictly prior settled perpetual funding may add positioning information."
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
                    "New-information family primary."
                    if variant == PRIMARY_VARIANT
                    else "Known internal HGBR on the matched funding-available universe."
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
                    f"Frozen WP-015 walk-forward: {classification}; no Champion, product "
                    "change, sealed query, futures action, or paper action."
                ),
                "falsified": (
                    "The preregistered robust after-cost expectancy claim failed."
                    if classification.startswith("REJECT")
                    else "No predeclared hurdle was falsified."
                ),
                "not_falsified": (
                    "No causal sentiment claim was tested; no tuning of exposed funding is authorized."
                ),
                "evidence_facts": [
                    {"json_pointer": "/primary_result", "expected_value": result["primary_result"]},
                    {
                        "json_pointer": "/secondary_results/annual_folds/terminal_classification",
                        "expected_value": classification,
                    },
                ],
                "failure_modes": [classification] if classification.startswith("REJECT") else [],
                "legitimate_revisit": (
                    "Only a new explicit Research Director allocation; no transformation rescue."
                ),
            }
        )
    write_lines(LEDGER_PATH, ledger)
    write_lines(OUTCOMES_PATH, outcomes)
    eligibility_path = write_eligibility_table(ROOT)
    eligibility = json.loads(eligibility_path.read_text(encoding="utf-8"))
    family = read_json(FAMILY_PATH)
    family["status"] = "PARKED_PENDING_RESEARCH_DIRECTOR_REVIEW"
    family["failure_experiment_ids"] = [EXPERIMENTS[PRIMARY_VARIANT]]
    write_json(FAMILY_PATH, family)

    primary = comparison["configurations"][PRIMARY_VARIANT]
    control = comparison["configurations"][CONTROL_VARIANT]
    default = profile(primary, "DEFAULT")
    report = f"""# WP-015 perpetual funding sentiment / positioning context

WP-015 tested one new raw informational variable, the latest settled BTCUSDT USD-M
perpetual funding rate strictly earlier than each hourly signal, against a matched
internal-only HGBR control on the exact same 2020-2024 eligible universe. BTCUSDT spot
LONG remained the only traded instrument.

Primary DEFAULT expectancy was {primary["primary_result"]:+.10f} R/trade over
{default["metrics"]["trade_count"]} trades, with
{default["stability"]["nonnegative_fold_count"]}/5 nonnegative folds and minimum fold
count {default["diagnostics"]["minimum_fold_trades"]}. ZERO was
{profile(primary, "ZERO")["metrics"]["net_expectancy_r"]:+.10f}, DOUBLE was
{profile(primary, "DOUBLE")["metrics"]["net_expectancy_r"]:+.10f}, and DELAY_1H was
{profile(primary, "DELAY_1H")["metrics"]["net_expectancy_r"]:+.10f} R/trade.

Matched control DEFAULT was {control["primary_result"]:+.10f}; primary minus control was
{comparison["primary_vs_control"]["default_net_expectancy_difference_r"]:+.10f} R/trade.
This relative improvement did not yield positive DEFAULT expectancy or any nonnegative
fold. Classification: **{primary["terminal_classification"]}**. Reconciliation passed
with maximum prediction difference {reconciliation["maximum_prediction_absolute_difference"]}.

Funding-sign diagnostics are descriptive only. No transformation, sign threshold, model
variant, or result-dependent rescue was performed. Champion remains NONE, ALIGNED remains
the paper research candidate, sealed queries and paper trades remain zero, and real money
remains false.
"""
    (ROOT / RESEARCH_REPORT_PATH).write_text(report, encoding="utf-8", newline="\n")

    accounting = cumulative_accounting(ROOT)
    state = read_json("state/current_state.json")
    state["status"] = "EXECUTOR_COMPLETE_PENDING_REVIEW"
    state["experiments_completed"] = len(
        list((ROOT / "research/experiments").glob("*/result.json"))
    )
    state["latest_reviewed_checkpoint"] = "WP-014"
    state["latest_executor_checkpoint"] = "WP-015"
    state["next_recommended_work_package"] = "RESEARCH_DIRECTOR_REVIEW_WP_015"
    state["search_memory"] = {
        "version": "SEARCH_MEMORY_V2",
        "status": "VALIDATED",
        "families_tracked": len(all_families(ROOT)),
    }
    state["adaptive_search"] = accounting
    state["latest_family"] = {
        "name": "PERPETUAL_FUNDING_CONTEXT_V1",
        "root_family": ROOT_FAMILY,
        "primary_experiment_id": EXPERIMENTS[PRIMARY_VARIANT],
        "novelty_classification": "NEW_FAMILY",
        "terminal_classification": primary["terminal_classification"],
    }
    state["funding_context_challenger"] = {
        "version": "PERPETUAL_FUNDING_CONTEXT_V1",
        "status": "VALIDATED",
        "root_family": ROOT_FAMILY,
        "primary": PRIMARY_VARIANT,
        "control": CONTROL_VARIANT,
        "funding_source": "BINANCE_USDM_FUTURES_PUBLIC_MARKET_DATA",
        "funding_records": diagnostics["funding_observations_acquired"],
        "validation_folds": 5,
        "reserved_model_fits": 10,
        "actual_model_fits": 10,
        "terminal_classification": primary["terminal_classification"],
        "model_reconciliation": "PASS",
        "sealed_eligibility": sealed_status(primary["terminal_classification"]),
        "safe_phase_1_commit": safe_commit,
        "futures_execution": False,
    }
    state["remote_ci"]["work_packages"]["WP-014"] = {
        "status": "SUCCESS",
        "head": "478f2fcab10569f20a81136bca1b5cff6b66d601",
        "run_id": 34757514686,
        "evidence": "reports/reviews/WP-014-CI-EVIDENCE.json",
    }
    state["sealed_evaluation"]["candidates_assessed"] = len(eligibility["candidates"])
    state["sealed_evaluation"]["seal_eligible_candidates"] = sum(
        item["sealed_eligibility"].startswith("DEVELOPMENT_ELIGIBLE")
        for item in eligibility["candidates"]
    )
    write_json("state/current_state.json", state)

    checkpoint = f"""# WP-015 checkpoint

WP-015 completed with PASS execution integrity and primary disposition
**{primary["terminal_classification"]}**. The safe Phase-1 commit `{safe_commit}` froze
one raw settled-funding feature, exact F1-F8, the WP-014 HGBR, five annual folds, strict
as-of availability, 216h purge, four profiles, and zero search variants before results.

Primary DEFAULT was {primary["primary_result"]:+.10f} R/trade; matched control DEFAULT was
{control["primary_result"]:+.10f}; difference
{comparison["primary_vs_control"]["default_net_expectancy_difference_r"]:+.10f}.
Independent reconciliation passed with zero mismatches at tolerance
{reconciliation["prediction_tolerance"]}.

Accounting is {state["experiments_completed"]} experiments,
{accounting["material_economic_hypotheses"]} hypotheses,
{accounting["configuration_variants"]} configurations, {accounting["profile_trials"]}
profiles, and {accounting["supervised_model_fits"]} model fits. Sealed queries and paper
trades remain zero; Champion is NONE; ALIGNED is unchanged; real money is false.
"""
    (ROOT / CHECKPOINT_PATH).write_text(checkpoint, encoding="utf-8", newline="\n")
    task = ROOT / "tasks/CURRENT_TASK.md"
    completed = task.read_text(encoding="utf-8").replace(
        "## STATUS\nACTIVE", "## STATUS\nCOMPLETED", 1
    )
    task.write_text(completed, encoding="utf-8", newline="\n")
    archive = ROOT / "tasks/archive/WP-015.md"
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_text(completed, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "classification": primary["terminal_classification"],
                "experiments": state["experiments_completed"],
                "safe_phase_1_commit": safe_commit,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
