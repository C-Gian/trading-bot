"""Execute the WP-012 regime-conditioned walk-forward and write every governed artifact.

Preflight must pass before a single validation hour is evaluated. Nothing here reacts to
an intermediate result: both configurations and all four profiles are fixed in advance,
and a regime expert that is infeasible for a fold stays infeasible.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np
from app.research.artifacts import write_parquet
from app.research.continuation_lab import PROFILES, ResearchInputs
from app.research.evaluation_protocol import load_protocol as load_walk_forward
from app.research.evaluation_protocol import terminal_classification
from app.research.regime import REGIMES, load_regime_source
from app.research.supervised import FULL_FEATURES, load_feature_source
from app.research.wp012 import (
    CONTROL_VARIANT,
    EXPERIMENTS,
    GLOBAL_KEY,
    PRIMARY_VARIANT,
    VARIANTS,
    load_protocol,
    preflight,
)
from app.research.wp012_lab import TRIAL_SCHEMA, RegimeExpertLab, parquet_rows

TRIALS_PATH = "data/derived/WP-012-regime-trials.parquet"
PREFLIGHT_PATH = "reports/validation/WP-012-PREFLIGHT.json"
COMPARISON_PATH = "reports/research/WP-012-COMPARISON.json"
DIAGNOSTICS_PATH = "reports/research/WP-012-REGIME-DIAGNOSTICS.json"
COEFFICIENTS_PATH = "reports/research/WP-012-EXPERT-COEFFICIENTS.json"


def write_json(relative: str, payload: Any) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def expert_coefficients(result: dict[str, Any]) -> dict[str, Any]:
    """Standardized coefficients per fold and expert, with the regime contrast."""
    folds = []
    contrasts = []
    for fold in result["folds"]:
        experts = {
            key: dict(
                zip(model["feature_order"], (float(v) for v in model["coefficients"]), strict=True)
            )
            for key, model in fold["experts"].items()
        }
        folds.append(
            {
                "fold_id": fold["fold_id"],
                "experts": {
                    key: {
                        "coefficients": experts[key],
                        "intercept": fold["experts"][key]["intercept"],
                        "condition_number": fold["experts"][key]["condition_number"],
                        "fit_rows": fold["training_manifests"][key]["fit_rows"],
                        "model_hash": fold["experts"][key]["model_hash"],
                    }
                    for key in sorted(experts)
                },
                "infeasible_experts": fold["infeasible_experts"],
            }
        )
        if set(REGIMES) <= set(experts):
            differences = {
                name: experts[REGIMES[1]][name] - experts[REGIMES[0]][name]
                for name in FULL_FEATURES
            }
            magnitudes = [abs(value) for value in differences.values()]
            contrasts.append(
                {
                    "fold_id": fold["fold_id"],
                    "difference_tight_minus_normal": differences,
                    "max_absolute_difference": max(magnitudes),
                    "mean_absolute_difference": float(np.mean(magnitudes)),
                    "sign_disagreement_count": sum(
                        (experts[REGIMES[0]][name] > 0) != (experts[REGIMES[1]][name] > 0)
                        for name in FULL_FEATURES
                    ),
                }
            )
    return {
        "variant": result["variant"],
        "folds": folds,
        "regime_contrasts": contrasts,
        "comparable_fold_count": len(contrasts),
        "comparison_note": (
            "A contrast exists only where both experts were feasible. Where the TIGHT "
            "expert was refused there is nothing to compare and nothing is imputed."
        ),
    }


def coverage(result: dict[str, Any]) -> dict[str, Any]:
    """Every validation hour the configuration could not speak for, by cause."""
    per_fold = {}
    for profile in PROFILES:
        for item in result["profiles"][profile]["fold_diagnostics"]:
            if profile != "DEFAULT":
                continue
            per_fold[item["fold_id"]] = {
                "validation_eligible_count": item["validation_eligible_count"],
                "uncovered_hour_count": item["uncovered_hour_count"],
                "prediction_positive_count": item["prediction_positive_count"],
                "suppressed_positive_count": item["suppressed_positive_count"],
                "emitted_trade_count": item["emitted_trade_count"],
            }
    return {
        "variant": result["variant"],
        "per_fold": per_fold,
        "uncovered_hours_by_expert": result["uncovered_hours"],
        "total_uncovered_hours": sum(result["uncovered_hours"].values()),
        "infeasible_expert_count": result["infeasible_expert_count"],
        "expert_fits": result["expert_fits"],
        "policy": "EMIT_NO_MODEL_COUNT_AFFECTED_HOURS_NEVER_MERGE_REGIMES",
    }


def main() -> int:
    report = preflight(ROOT)
    if report["status"] != "PASS":
        print(json.dumps(report, indent=2))
        return 1
    write_json(PREFLIGHT_PATH, report)
    protocol = load_protocol(ROOT)
    walk_forward = load_walk_forward()

    lab = RegimeExpertLab(
        ResearchInputs.load(ROOT),
        load_feature_source(ROOT),
        load_regime_source(ROOT),
        walk_forward,
    )

    results = {}
    rows: list[dict[str, Any]] = []
    for variant in VARIANTS:
        print(f"running {variant}", flush=True)
        result = lab.run_configuration(variant)
        results[variant] = result
        for profile in PROFILES:
            rows.extend(parquet_rows(result["profiles"][profile]))
        print(
            f"  experts={result['expert_fits']} infeasible={result['infeasible_expert_count']} "
            f"uncovered={sum(result['uncovered_hours'].values())}",
            flush=True,
        )

    for variant in VARIANTS:
        result = results[variant]
        write_json(
            f"research/experiments/{EXPERIMENTS[variant]}/fold-experts.json",
            {
                "schema_version": 1,
                "experiment_id": EXPERIMENTS[variant],
                "variant": variant,
                "architecture": protocol["architecture"],
                "fold_experts": [
                    {
                        "fold_id": fold["fold_id"],
                        "experts": fold["experts"],
                        "training_manifests": fold["training_manifests"],
                        "infeasible_experts": fold["infeasible_experts"],
                    }
                    for fold in result["folds"]
                ],
                "expert_fits": result["expert_fits"],
                "infeasible_expert_count": result["infeasible_expert_count"],
                "uncovered_hours": result["uncovered_hours"],
            },
        )

    manifest = write_parquet(
        ROOT / TRIALS_PATH,
        rows,
        schema=TRIAL_SCHEMA,
        sort_key=["variant", "profile", "signal_us"],
        root=ROOT,
    )

    comparison: dict[str, Any] = {
        "schema_version": 1,
        "work_package": "WP-012",
        "protocol_id": protocol["protocol_id"],
        "architecture": protocol["architecture"],
        "primary_variant": PRIMARY_VARIANT,
        "control_variant": CONTROL_VARIANT,
        "regime": {
            "version": protocol["regime"]["version"],
            "series": protocol["regime"]["series"],
            "threshold": protocol["regime"]["threshold"],
            "threshold_variants": 0,
        },
        "artifact": manifest,
        "configurations": {},
    }
    for variant in VARIANTS:
        result = results[variant]
        summaries = {profile: result["profiles"][profile]["summary"] for profile in PROFILES}
        default = summaries["DEFAULT"]
        comparison["configurations"][variant] = {
            "experiment_id": EXPERIMENTS[variant],
            "primary_result": default["metrics"]["net_expectancy_r"],
            "terminal_classification": terminal_classification(
                summaries["DEFAULT"], summaries["ZERO"], summaries["DOUBLE"], walk_forward
            ),
            "profiles": {
                profile: {
                    "metrics": summaries[profile]["metrics"],
                    "stability": summaries[profile]["stability"],
                    "diagnostics": summaries[profile]["diagnostics"],
                    "folds": summaries[profile]["folds"],
                }
                for profile in PROFILES
            },
            "coverage": coverage(result),
        }

    primary = comparison["configurations"][PRIMARY_VARIANT]
    control = comparison["configurations"][CONTROL_VARIANT]
    comparison["conditioning_effect"] = {
        "primary_minus_control_default_net_expectancy_r": (
            None
            if primary["primary_result"] is None or control["primary_result"] is None
            else primary["primary_result"] - control["primary_result"]
        ),
        "primary_default_trade_count": primary["profiles"]["DEFAULT"]["metrics"]["trade_count"],
        "control_default_trade_count": control["profiles"]["DEFAULT"]["metrics"]["trade_count"],
        "hours_the_primary_could_not_speak_for": primary["coverage"]["total_uncovered_hours"],
        "paired": False,
        "interpretation_guard": (
            "The two configurations do not share an identical executed trade set, so this "
            "difference is a summary contrast, not a paired test."
        ),
    }
    write_json(COMPARISON_PATH, comparison)
    write_json(
        DIAGNOSTICS_PATH,
        {
            "schema_version": 1,
            "work_package": "WP-012",
            "regime_version": protocol["regime"]["version"],
            "eligibility_exclusions": dict(sorted(lab.exclusions.items())),
            "configurations": {
                variant: results[variant]["regime_diagnostics"] for variant in VARIANTS
            },
        },
    )
    write_json(
        COEFFICIENTS_PATH,
        {
            "schema_version": 1,
            "work_package": "WP-012",
            "configurations": {
                variant: expert_coefficients(results[variant]) for variant in VARIANTS
            },
            "global_expert_key": GLOBAL_KEY,
        },
    )
    print(json.dumps(comparison["conditioning_effect"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
