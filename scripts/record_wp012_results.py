"""Record the WP-012 outcome: experiment results, ledger, outcomes and comparisons.

Runs only after the walk-forward produced its comparison artifact. Nothing here alters
the experiment; it transcribes what was measured, including a negative or inert result.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.sealed_eligibility import write_eligibility_table
from app.research.wp012 import (
    ALLOCATION_ID,
    ARCHITECTURE,
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

COMPARISON_PATH = "reports/research/WP-012-COMPARISON.json"
HISTORICAL_PATH = "reports/research/WP-012-HISTORICAL-COMPARISON.json"
RECONCILIATION_PATH = "reports/validation/WP-012-MODEL-RECONCILIATION.json"
DIAGNOSTICS_PATH = "reports/research/WP-012-REGIME-DIAGNOSTICS.json"
COEFFICIENTS_PATH = "reports/research/WP-012-EXPERT-COEFFICIENTS.json"
STABILITY_PATH = "reports/research/WP-012-EXPERT-STABILITY.json"
COMPLETED_AT = "2026-09-12T00:00:00Z"
MECHANISM = (
    "Two independently fitted linear experts over the frozen eight internal features, "
    "selected hour by hour by a fixed zero-threshold point-in-time NFCI regime gate, may "
    "rank default-cost long opportunity quality better than one global weight vector; "
    "predictive, not causal."
)
PRIORS = (
    "EXP-CTRL-006-NO-TRADE",
    "EXP-CTRL-002-RANDOM",
    "EXP-BASE-003-TREND",
    "EXP-BASE-004-BREAKOUT",
    "EXP-ALG-009-ALIGNED",
    "EXP-ALG-010-PULLBACK-RECOVERY-CORE",
    "EXP-ALG-012-ORDERFLOW-CORE",
    "EXP-ML-014-LINEAR-NET-R-FULL",
    "EXP-ML-016-EWLS-INTERNAL-MACRO",
    "EXP-ML-017-EWLS-INTERNAL-ONLY",
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
    for experiment_id in PRIORS:
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
    return {
        "schema_version": 1,
        "work_package": "WP-012",
        "comparison_basis": "DESCRIPTIVE_ONLY_TRADE_SETS_ARE_NOT_PAIRED",
        "caveat": (
            "Eligibility universes, entry events and trade counts differ across families. "
            "These numbers are not a matched-control comparison and no significance claim "
            "is made. Within WP-012 the two configurations share an eligible universe but "
            "not an executed trade set, because the primary abstains wherever its regime "
            "expert is infeasible."
        ),
        "wp012": {
            variant: {
                "experiment_id": EXPERIMENTS[variant],
                "primary_result": comparison["configurations"][variant]["primary_result"],
                "terminal_classification": comparison["configurations"][variant][
                    "terminal_classification"
                ],
                "trade_count": comparison["configurations"][variant]["profiles"]["DEFAULT"][
                    "metrics"
                ]["trade_count"],
                "hours_without_a_feasible_expert": comparison["configurations"][variant][
                    "coverage"
                ]["total_uncovered_hours"],
            }
            for variant in VARIANTS
        },
        "conditioning_effect": comparison["conditioning_effect"],
        "historical": priors,
    }


def family_disposition(comparison: dict[str, Any]) -> str:
    """One disposition for the root family, from the primary configuration's own rule."""
    classification = comparison["configurations"][PRIMARY_VARIANT]["terminal_classification"]
    return "REJECTED" if classification.startswith("REJECT") else "PENDING_RESEARCH_DIRECTOR_REVIEW"


def sign_stability(values: list[float]) -> dict[str, Any]:
    """Dominant coefficient-sign share, retaining exact zeros as their own category."""
    counts = {
        "negative": sum(value < 0.0 for value in values),
        "zero": sum(value == 0.0 for value in values),
        "positive": sum(value > 0.0 for value in values),
    }
    return {
        "fits": len(values),
        "counts": counts,
        "dominant_sign_fraction": max(counts.values()) / len(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def coefficient_stability() -> dict[str, Any]:
    """Derive declared sign and condition diagnostics from the immutable fold records."""
    coefficients = json.loads((ROOT / COEFFICIENTS_PATH).read_text(encoding="utf-8"))
    configurations: dict[str, Any] = {}
    for variant, configuration in coefficients["configurations"].items():
        by_expert: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for fold in configuration["folds"]:
            for expert, model in fold["experts"].items():
                by_expert[expert].append(model)
        experts = {}
        for expert, models in sorted(by_expert.items()):
            features = models[0]["coefficients"]
            experts[expert] = {
                "fits": len(models),
                "unique_model_hashes": len({model["model_hash"] for model in models}),
                "fit_rows": [model["fit_rows"] for model in models],
                "condition_number": {
                    "minimum": min(model["condition_number"] for model in models),
                    "maximum": max(model["condition_number"] for model in models),
                },
                "coefficient_sign_stability": {
                    feature: sign_stability(
                        [float(model["coefficients"][feature]) for model in models]
                    )
                    for feature in features
                },
            }
        contrasts = configuration["regime_contrasts"]
        contrast_features = contrasts[0]["difference_tight_minus_normal"] if contrasts else {}
        configurations[variant] = {
            "experts": experts,
            "regime_contrast": {
                "comparable_folds": len(contrasts),
                "difference_sign_stability": {
                    feature: sign_stability(
                        [
                            float(item["difference_tight_minus_normal"][feature])
                            for item in contrasts
                        ]
                    )
                    for feature in contrast_features
                },
                "sign_disagreement_count_by_fold": {
                    item["fold_id"]: item["sign_disagreement_count"] for item in contrasts
                },
                "mean_absolute_difference_range": (
                    {
                        "minimum": min(item["mean_absolute_difference"] for item in contrasts),
                        "maximum": max(item["mean_absolute_difference"] for item in contrasts),
                    }
                    if contrasts
                    else None
                ),
            },
        }
    return {
        "schema_version": 1,
        "work_package": "WP-012",
        "definition": "DOMINANT_EXACT_SIGN_FRACTION_ACROSS_RECORDED_FOLD_FITS",
        "configurations": configurations,
        "interpretation_guard": (
            "The four recorded TIGHT fits are one identical 336-row model repeated because "
            "no later TIGHT rows exist. Its apparent sign stability and the corresponding "
            "contrast stability are therefore not four independent temporal confirmations. "
            "The TIGHT expert is never feasible and selected in the same validation fold."
        ),
    }


def main() -> int:
    protocol = load_protocol(ROOT)
    comparison = json.loads((ROOT / COMPARISON_PATH).read_text(encoding="utf-8"))
    reconciliation = json.loads((ROOT / RECONCILIATION_PATH).read_text(encoding="utf-8"))
    diagnostics = json.loads((ROOT / DIAGNOSTICS_PATH).read_text(encoding="utf-8"))
    admission = json.loads(
        (ROOT / "research/memory/registry/admissions/WP012-NOVELTY-ADMISSION.json").read_text(
            encoding="utf-8"
        )
    )
    write_json(STABILITY_PATH, coefficient_stability())

    ledger: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
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
            "primary_result": config["primary_result"],
            "secondary_results": {
                "terminal_classification": config["terminal_classification"],
                "trade_count": default["metrics"]["trade_count"],
                "cumulative_net_r": default["metrics"]["cumulative_net_r"],
                "nonnegative_fold_count": default["stability"]["nonnegative_fold_count"],
                "minimum_fold_trade_count": default["diagnostics"]["minimum_fold_trades"],
                "profiles": {
                    profile: config["profiles"][profile]["metrics"]["net_expectancy_r"]
                    for profile in ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")
                },
                "architecture": ARCHITECTURE,
                "regime_version": protocol["regime"]["version"],
                "regime_threshold": protocol["regime"]["threshold"],
                "regime_threshold_variants": 0,
                "macro_features_in_expert_matrix": 0,
                "expert_fits": config["coverage"]["expert_fits"],
                "infeasible_expert_count": config["coverage"]["infeasible_expert_count"],
                "hours_without_a_feasible_expert": config["coverage"]["total_uncovered_hours"],
                "pooled_prediction_label_pearson": diagnostics["configurations"][variant][
                    "pooled_prediction_label_pearson"
                ],
                "per_regime": {
                    regime: {
                        "executed_trades": values["executed_trades"],
                        "mean_net_r": values["mean_net_r"],
                        "eligible_validation_hours": values["eligible_validation_hours"],
                    }
                    for regime, values in diagnostics["configurations"][variant][
                        "per_regime"
                    ].items()
                },
                "independent_reconciliation": reconciliation["status"],
                "sealed_queries": 0,
            },
            "artifacts": [
                COMPARISON_PATH,
                DIAGNOSTICS_PATH,
                COEFFICIENTS_PATH,
                STABILITY_PATH,
                f"research/experiments/{experiment_id}/fold-experts.json",
                RECONCILIATION_PATH,
                "reports/validation/WP-012-REGIME-ASOF-AUDIT.json",
                "reports/validation/WP-012-PREEXECUTION-STRUCTURAL-FINDING.json",
            ],
            "validation_outcome": "PASS" if reconciliation["status"] == "PASS" else "FAIL",
            "interpretation": (
                "EXPOSED DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE. "
                "Per-fold ordinary least squares with training-only per-expert scaling and "
                "labels, gated by point-in-time NFCI at a fixed zero threshold; no tuning, "
                "no threshold search and no validation refit. Hours with no feasible expert "
                "are counted, never merged into another regime."
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
                "work_package": "WP-012",
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
                    "The two-expert regime-conditioned configuration is the family primary."
                    if variant == PRIMARY_VARIANT
                    else "The single-expert configuration on the same eligible universe "
                    "isolates the contribution of regime conditioning itself."
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
        uncovered = config["coverage"]["total_uncovered_hours"]
        outcomes.append(
            {
                "schema_version": 1,
                "experiment_id": experiment_id,
                "result_path": result_relative,
                "result_sha256": result_hash,
                "terminal_classification": classification,
                "conclusion": (
                    "Frozen leakage-safe regime-conditioned walk-forward with per-fold "
                    f"per-regime refits: {classification}; {uncovered} validation hours had "
                    "no feasible expert and emitted nothing; no sealed query, Champion, or "
                    "paper action."
                ),
                "falsified": (
                    "The regime-conditioned net-profitability/stability claim failed its "
                    "predeclared hurdles."
                    if classification.startswith("REJECT")
                    else "No predeclared hurdle was falsified by this configuration."
                ),
                "not_falsified": (
                    "Other thresholds, macro series, regime counts, smoothing rules, lag "
                    "variants, feature families, non-linear models, labels, exits, horizons, "
                    "assets and prospective evidence remain untested. On this history NFCI "
                    "exceeds zero in a single fortnight, so the TIGHT expert was never both "
                    "feasible and used; that is a property of the sample, not evidence "
                    "against regime conditioning in general."
                ),
                "evidence_facts": [
                    {"json_pointer": "/primary_result", "expected_value": result["primary_result"]},
                    {
                        "json_pointer": "/secondary_results/terminal_classification",
                        "expected_value": classification,
                    },
                    {
                        "json_pointer": "/secondary_results/hours_without_a_feasible_expert",
                        "expected_value": uncovered,
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
    write_eligibility_table(ROOT)
    disposition = family_disposition(comparison)
    print("family disposition:", disposition)
    print("reconciliation:", reconciliation["status"])
    for variant in VARIANTS:
        config = comparison["configurations"][variant]
        print(
            f"{variant}: {config['terminal_classification']} "
            f"expectancy={config['primary_result']} "
            f"trades={config['profiles']['DEFAULT']['metrics']['trade_count']} "
            f"uncovered={config['coverage']['total_uncovered_hours']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
