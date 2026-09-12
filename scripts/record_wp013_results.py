"""Record immutable WP-013 outcomes after independent reconciliation passes."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.sealed_eligibility import write_eligibility_table
from app.research.wp013 import (
    ALLOCATION_ID,
    EXPERIMENTS,
    HYPOTHESIS_ID,
    INTERACTION_FEATURES,
    LEDGER_PATH,
    OUTCOMES_PATH,
    PRIMARY_VARIANT,
    ROLES,
    ROOT_FAMILY,
    VARIANTS,
    load_protocol,
    sha256,
)

COMPARISON_PATH = "reports/research/WP-013-COMPARISON.json"
DIAGNOSTICS_PATH = "reports/research/WP-013-INTERACTION-DIAGNOSTICS.json"
STABILITY_PATH = "reports/research/WP-013-INTERACTION-STABILITY.json"
HISTORICAL_PATH = "reports/research/WP-013-HISTORICAL-COMPARISON.json"
RECONCILIATION_PATH = "reports/validation/WP-013-MODEL-RECONCILIATION.json"
COMPLETED_AT = "2026-09-12T21:00:00Z"

PRIORS = (
    "EXP-CTRL-006-NO-TRADE",
    "EXP-BASE-004-BREAKOUT",
    "EXP-ALG-009-ALIGNED",
    "EXP-ML-014-LINEAR-NET-R-FULL",
    "EXP-ML-016-EWLS-INTERNAL-MACRO",
    "EXP-ML-017-EWLS-INTERNAL-ONLY",
    "EXP-ML-018-REGIME-TWO-EXPERTS",
    "EXP-ML-019-GLOBAL-MATCHED-CONTROL",
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


def sign_record(values: list[float]) -> dict[str, Any]:
    counts = {
        "negative": sum(v < 0 for v in values),
        "zero": sum(v == 0 for v in values),
        "positive": sum(v > 0 for v in values),
    }
    return {
        "fits": len(values),
        "counts": counts,
        "dominant_sign_fraction": max(counts.values()) / len(values),
        "exact_sign_stable": max(counts.values()) == len(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def stability(diagnostics: dict[str, Any]) -> dict[str, Any]:
    folds = diagnostics["configurations"][PRIMARY_VARIANT]["folds"]
    sign_stability = {}
    effective = {}
    for interaction in INTERACTION_FEATURES:
        values = [float(fold["standardized_coefficients"][interaction]) for fold in folds]
        sign_stability[interaction] = sign_record(values)
    for base in folds[0]["effective_raw_feature_slopes"]:
        records = [fold["effective_raw_feature_slopes"][base] for fold in folds]
        effective[base] = {
            "folds": len(records),
            "mean_raw_slope_at_nfci_minus1": sum(r["NFCI_-1"] for r in records) / len(records),
            "mean_raw_slope_at_nfci_zero": sum(r["NFCI_0"] for r in records) / len(records),
            "mean_raw_slope_at_nfci_plus1": sum(r["NFCI_+1"] for r in records) / len(records),
            "mean_absolute_minus1_to_plus1_change": sum(
                abs(r["NFCI_+1"] - r["NFCI_-1"]) for r in records
            )
            / len(records),
            "context_endpoint_sign_reversals": sum(
                (r["NFCI_-1"] > 0) != (r["NFCI_+1"] > 0) for r in records
            ),
        }
    stable = sum(item["exact_sign_stable"] for item in sign_stability.values())
    return {
        "schema_version": 1,
        "work_package": "WP-013",
        "definition": "EXACT_STANDARDIZED_INTERACTION_COEFFICIENT_SIGN_ACROSS_ALL_SIX_EXPANDING_FOLDS",
        "stable_interaction_signs": stable,
        "interaction_count": 8,
        "interaction_sign_stability": sign_stability,
        "effective_raw_feature_slopes": effective,
        "condition_numbers": [fold["condition_number"] for fold in folds],
        "interpretation_guard": "NFCI -1/0/+1 slopes are fixed diagnostics of a predictive model, not causal effects or tuning points.",
    }


def historical(comparison: dict[str, Any]) -> dict[str, Any]:
    records = []
    for experiment in PRIORS:
        path = ROOT / f"research/experiments/{experiment}/result.json"
        if not path.exists():
            continue
        item = json.loads(path.read_text(encoding="utf-8"))
        secondary = item.get("secondary_results") or {}
        records.append(
            {
                "experiment_id": experiment,
                "primary_result": item.get("primary_result"),
                "terminal_classification": secondary.get("terminal_classification"),
                "trade_count": secondary.get("trade_count"),
            }
        )
    return {
        "schema_version": 1,
        "work_package": "WP-013",
        "comparison_basis": "DESCRIPTIVE_ONLY_UNLESS_EXPLICITLY_MATCHED_WITHIN_WP013",
        "caveat": "Historical families and executed trade sets differ; no paired claim is made. WP-013 configurations share eligible hours but not signals or occupancy.",
        "wp013": {
            variant: {
                "experiment_id": EXPERIMENTS[variant],
                "primary_result": comparison["configurations"][variant]["primary_result"],
                "terminal_classification": comparison["configurations"][variant][
                    "terminal_classification"
                ],
                "trade_count": comparison["configurations"][variant]["profiles"]["DEFAULT"][
                    "metrics"
                ]["trade_count"],
            }
            for variant in VARIANTS
        },
        "interaction_effect": comparison["interaction_effect"],
        "historical": records,
    }


def main() -> int:
    load_protocol(ROOT)
    comparison = json.loads((ROOT / COMPARISON_PATH).read_text(encoding="utf-8"))
    diagnostics = json.loads((ROOT / DIAGNOSTICS_PATH).read_text(encoding="utf-8"))
    reconciliation = json.loads((ROOT / RECONCILIATION_PATH).read_text(encoding="utf-8"))
    if reconciliation["status"] != "PASS":
        raise RuntimeError("refusing to record unreconciled WP-013 results")
    write_json(STABILITY_PATH, stability(diagnostics))
    write_json(HISTORICAL_PATH, historical(comparison))
    stability_record = json.loads((ROOT / STABILITY_PATH).read_text(encoding="utf-8"))
    admission = json.loads(
        (ROOT / "research/memory/registry/admissions/WP013-NOVELTY-ADMISSION.json").read_text()
    )
    ledger, outcomes = [], []
    for variant, admitted in zip(VARIANTS, admission["variants"], strict=True):
        experiment = EXPERIMENTS[variant]
        config = comparison["configurations"][variant]
        default = config["profiles"]["DEFAULT"]
        prereg_path = f"research/experiments/{experiment}/preregistration.json"
        prereg = json.loads((ROOT / prereg_path).read_text())
        result = {
            "schema_version": 2,
            "experiment_id": experiment,
            "experiment_version": 1,
            "preregistration_reference": experiment,
            "preregistration_created_at_utc": prereg["created_at_utc"],
            "completed_at_utc": COMPLETED_AT,
            "status": "COMPLETED",
            "code_config_reference": prereg["code_config_reference"],
            "dataset": {
                "manifest_id": prereg["dataset"]["manifest_id"],
                "content_hash": prereg["dataset"]["content_hash"],
            },
            "seed_reference": [0],
            "primary_result": config["primary_result"],
            "secondary_results": {
                "terminal_classification": config["terminal_classification"],
                "profiles": {
                    p: {
                        "net_expectancy_r": config["profiles"][p]["metrics"]["net_expectancy_r"],
                        "cumulative_net_r": config["profiles"][p]["metrics"]["cumulative_net_r"],
                        "trade_count": config["profiles"][p]["metrics"]["trade_count"],
                    }
                    for p in ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")
                },
                "annual_folds": {
                    "folds": default["folds"],
                    "trade_count": default["metrics"]["trade_count"],
                    "cumulative_net_r": default["metrics"]["cumulative_net_r"],
                    "nonnegative_fold_count": default["stability"]["nonnegative_fold_count"],
                    "minimum_fold_trade_count": default["diagnostics"]["minimum_fold_trades"],
                    "model_fits": config["model_fits"],
                },
                "condition_numbers": [
                    fold["condition_number"]
                    for fold in diagnostics["configurations"][variant]["folds"]
                ],
                "coefficient_sign_stability": (
                    stability_record["interaction_sign_stability"]
                    if variant == PRIMARY_VARIANT
                    else {}
                ),
                "effective_slopes_at_nfci_minus1_zero_plus1": (
                    stability_record["effective_raw_feature_slopes"]
                    if variant == PRIMARY_VARIANT
                    else {}
                ),
                "prediction_diagnostics": config["prediction_diagnostics"],
                "independent_reconciliation": reconciliation["status"],
            },
            "artifacts": [
                COMPARISON_PATH,
                DIAGNOSTICS_PATH,
                STABILITY_PATH,
                HISTORICAL_PATH,
                f"research/experiments/{experiment}/fold-models.json",
                RECONCILIATION_PATH,
                "reports/validation/WP-013-NFCI-ASOF-AUDIT.json",
            ],
            "validation_outcome": "PASS",
            "interpretation": "EXPOSED DEVELOPMENT RESEARCH, PREDICTIVE NOT CAUSAL. Raw point-in-time NFCI enters only through eight fixed interactions; no tuning or sealed access.",
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
                "work_package": "WP-013",
                "record_kind": "PREREGISTERED_ADMISSION",
                "strategy_label": variant,
                "root_family": ROOT_FAMILY,
                "hypothesis_id": HYPOTHESIS_ID,
                "hypothesis_role": ROLES[variant],
                "claimed_market_mechanism": "Raw point-in-time NFCI may continuously modify internal-feature predictive slopes through eight fixed interactions.",
                "allocation_id": ALLOCATION_ID,
                "classification": admitted["classification"],
                "matched_experiment_ids": admitted["matched_experiment_ids"],
                "behavior_hash": admitted["behavior_hash"],
                "structural_hash": admitted["structural_hash"],
                "executable_spec_hash": admitted["executable_spec_hash"],
                "dependency_hash": admitted["dependency_hash"],
                "parent_experiment_ids": []
                if variant == PRIMARY_VARIANT
                else [EXPERIMENTS[PRIMARY_VARIANT]],
                "novelty": admitted["classification"],
                "scientific_reason": "Family primary contextual interaction mechanism."
                if variant == PRIMARY_VARIANT
                else "Matched internal-only control on identical eligible hours.",
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
                "conclusion": f"Frozen contextual NFCI interaction walk-forward: {classification}; no sealed query, Champion, or paper action.",
                "falsified": "The preregistered robust after-cost expectancy claim failed."
                if classification.startswith("REJECT")
                else "No predeclared hurdle was falsified.",
                "not_falsified": "Other prospectively allocated mechanisms remain untested; no tuning of this exposed model is authorized.",
                "evidence_facts": [
                    {"json_pointer": "/primary_result", "expected_value": result["primary_result"]},
                    {
                        "json_pointer": "/secondary_results/terminal_classification",
                        "expected_value": classification,
                    },
                ],
                "failure_modes": [classification] if classification.startswith("REJECT") else [],
                "legitimate_revisit": "Only a new explicit cumulative Research Director allocation; no exposed-result tuning.",
            }
        )
    write_lines(LEDGER_PATH, ledger)
    write_lines(OUTCOMES_PATH, outcomes)
    write_eligibility_table(ROOT)
    print("recorded WP-013 outcomes; reconciliation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
