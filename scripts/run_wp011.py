"""Execute the WP-011 adaptive walk-forward and write every governed artifact.

Preflight must pass before a single validation hour is evaluated. Nothing here reacts to
an intermediate result: both configurations and all four profiles are fixed in advance.
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
from app.research.macro import load_macro_source
from app.research.supervised import load_feature_source
from app.research.wp011 import (
    ABLATION_VARIANT,
    EXPERIMENTS,
    PRIMARY_VARIANT,
    VARIANTS,
    load_protocol,
    preflight,
)
from app.research.wp011_lab import TRIAL_SCHEMA, AdaptiveEwlsLab, parquet_rows

TRIALS_PATH = "data/derived/WP-011-adaptive-trials.parquet"
PREFLIGHT_PATH = "reports/validation/WP-011-PREFLIGHT.json"
COMPARISON_PATH = "reports/research/WP-011-COMPARISON.json"
COEFFICIENTS_PATH = "reports/research/WP-011-COEFFICIENT-TRAJECTORIES.json"


def write_json(relative: str, payload: Any) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def group_contributions(protocol: dict[str, Any], record: dict[str, Any]) -> dict[str, float]:
    """Absolute standardized coefficient mass per information family."""
    order = record["feature_order"]
    coefficients = dict(zip(order, record["coefficients"], strict=True))
    total = sum(abs(value) for value in coefficients.values()) or 1.0
    shares = {}
    for group, names in protocol["feature_groups"].items():
        present = [abs(coefficients[name]) for name in names if name in coefficients]
        shares[group] = float(sum(present) / total)
    return shares


def coefficient_trajectory(protocol: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Monthly coefficient evolution, sign stability and grouped contribution drift."""
    models = result["monthly_models"]
    order = models[0]["model"]["feature_order"]
    series = {name: [] for name in order}
    groups: dict[str, list[float]] = {group: [] for group in protocol["feature_groups"]}
    rows = []
    for item in models:
        record = item["model"]
        for name, value in zip(record["feature_order"], record["coefficients"], strict=True):
            series[name].append(float(value))
        shares = group_contributions(protocol, record)
        for group, value in shares.items():
            groups[group].append(value)
        rows.append(
            {
                "effective_utc": item["training_manifest"]["effective_utc"],
                "fit_rows": item["training_manifest"]["fit_rows"],
                "effective_sample_size": record["effective_sample_size"],
                "condition_number": record["condition_number"],
                "intercept": record["intercept"],
                "coefficients": dict(
                    zip(record["feature_order"], record["coefficients"], strict=True)
                ),
                "group_contribution_share": shares,
            }
        )
    stability = {}
    for name, values in series.items():
        array = np.asarray(values, dtype=np.float64)
        positive = int(np.count_nonzero(array > 0))
        stability[name] = {
            "mean": float(array.mean()),
            "std": float(array.std(ddof=0)),
            "min": float(array.min()),
            "max": float(array.max()),
            "positive_months": positive,
            "negative_months": int(len(array) - positive),
            "sign_stability": float(max(positive, len(array) - positive) / len(array)),
        }
    group_summary = {
        group: {
            "mean_share": float(np.mean(values)),
            "min_share": float(np.min(values)),
            "max_share": float(np.max(values)),
            "std_share": float(np.std(values, ddof=0)),
        }
        for group, values in groups.items()
    }
    return {
        "variant": result["variant"],
        "monthly_models": len(models),
        "coefficient_sign_stability": stability,
        "grouped_contribution": group_summary,
        "monthly": rows,
    }


def profile_summary(result: dict[str, Any], profile: str) -> dict[str, Any]:
    summary = result["profiles"][profile]["summary"]
    metrics = summary["metrics"]
    stability = summary["stability"]
    diagnostics = summary["diagnostics"]
    return {
        "profile": profile,
        "trade_count": metrics["trade_count"],
        "net_expectancy_r": metrics["net_expectancy_r"],
        "cumulative_net_r": metrics["cumulative_net_r"],
        "gross_expectancy_r": metrics.get("gross_expectancy_r"),
        "nonnegative_fold_count": stability["nonnegative_fold_count"],
        "minimum_fold_trade_count": diagnostics["minimum_fold_trades"],
        "worst_fold": stability["worst_fold"],
        "best_fold": stability["best_fold"],
        "max_positive_fold_profit_share": stability["max_positive_fold_profit_share"],
        "trade_ess": diagnostics.get("trade_ess"),
        "folds": [
            {
                "fold_id": fold["fold_id"],
                "trade_count": fold["metrics"]["trade_count"],
                "net_expectancy_r": fold["metrics"]["net_expectancy_r"],
                "cumulative_net_r": fold["metrics"]["cumulative_net_r"],
            }
            for fold in summary["folds"]
        ],
    }


def main() -> int:
    report = preflight(ROOT)
    write_json(PREFLIGHT_PATH, report)
    if report["status"] != "PASS":
        print("preflight failed; no validation hour evaluated")
        return 1
    print("preflight PASS — admission and preregistrations precede every result", flush=True)

    protocol = load_protocol(ROOT)
    walk_forward = load_walk_forward()
    inputs = ResearchInputs.load(ROOT)
    lab = AdaptiveEwlsLab(
        inputs, load_feature_source(ROOT), load_macro_source(ROOT), protocol, walk_forward
    )
    print("substrate loaded", flush=True)

    results = {}
    for variant in VARIANTS:
        print(f"running {variant} …", flush=True)
        results[variant] = lab.run_configuration(variant)
        counts = {
            profile: results[variant]["profiles"][profile]["summary"]["metrics"]["trade_count"]
            for profile in PROFILES
        }
        print(f"  {variant} trades: {counts}", flush=True)

    rows = [
        row
        for variant in VARIANTS
        for profile in PROFILES
        for row in parquet_rows(results[variant]["profiles"][profile])
    ]
    artifact = write_parquet(
        ROOT / TRIALS_PATH,
        rows,
        schema=TRIAL_SCHEMA,
        sort_key=["variant", "profile", "signal_us"],
        root=ROOT,
    )

    comparison: dict[str, Any] = {
        "schema_version": 1,
        "work_package": "WP-011",
        "protocol_id": protocol["protocol_id"],
        "root_family": "FAM-ADAPTIVE-EWLS-MACRO",
        "hypothesis_id": protocol["hypothesis_id"],
        "primary_variant": PRIMARY_VARIANT,
        "model_version": protocol["model"]["version"],
        "half_life_days": protocol["training"]["half_life_days"],
        "update_cadence": protocol["model"]["update_cadence"],
        "sealed_queries": 0,
        "paper_evidence_used": False,
        "configurations": {},
        "artifact": artifact,
    }

    for variant in VARIANTS:
        result = results[variant]
        summaries = {profile: profile_summary(result, profile) for profile in PROFILES}
        classification = terminal_classification(
            result["profiles"]["DEFAULT"]["summary"],
            result["profiles"]["ZERO"]["summary"],
            result["profiles"]["DOUBLE"]["summary"],
            walk_forward,
        )
        comparison["configurations"][variant] = {
            "experiment_id": EXPERIMENTS[variant],
            "feature_count": len(protocol["features"][variant]),
            "monthly_models": len(result["monthly_models"]),
            "terminal_classification": classification,
            "profiles": summaries,
            "validation_diagnostics": result["validation_diagnostics"],
            "admissible_monthly_models": len(result["monthly_models"]),
            "inadmissible_monthly_models": result["inadmissible_monthly_models"],
        }
        write_json(
            COEFFICIENTS_PATH.replace(".json", f"-{variant}.json"),
            coefficient_trajectory(protocol, result),
        )

    primary = comparison["configurations"][PRIMARY_VARIANT]
    ablation = comparison["configurations"][ABLATION_VARIANT]
    comparison["family_disposition"] = primary["terminal_classification"]
    comparison["preexecution_correction"] = "reports/validation/WP-011-PREEXECUTION-CORRECTION.json"
    comparison["reserved_model_fits"] = 144
    comparison["admissible_model_fits"] = sum(
        comparison["configurations"][v]["admissible_monthly_models"] for v in VARIANTS
    )
    comparison["macro_incremental"] = {
        "default_expectancy_delta_r": (
            primary["profiles"]["DEFAULT"]["net_expectancy_r"]
            - ablation["profiles"]["DEFAULT"]["net_expectancy_r"]
            if primary["profiles"]["DEFAULT"]["net_expectancy_r"] is not None
            and ablation["profiles"]["DEFAULT"]["net_expectancy_r"] is not None
            else None
        ),
        "primary_default_expectancy_r": primary["profiles"]["DEFAULT"]["net_expectancy_r"],
        "ablation_default_expectancy_r": ablation["profiles"]["DEFAULT"]["net_expectancy_r"],
        "primary_nonnegative_folds": primary["profiles"]["DEFAULT"]["nonnegative_fold_count"],
        "ablation_nonnegative_folds": ablation["profiles"]["DEFAULT"]["nonnegative_fold_count"],
        "primary_double_expectancy_r": primary["profiles"]["DOUBLE"]["net_expectancy_r"],
        "ablation_double_expectancy_r": ablation["profiles"]["DOUBLE"]["net_expectancy_r"],
        "primary_pooled_correlation": primary["validation_diagnostics"][
            "pooled_prediction_label_pearson"
        ],
        "ablation_pooled_correlation": ablation["validation_diagnostics"][
            "pooled_prediction_label_pearson"
        ],
    }
    write_json(COMPARISON_PATH, comparison)

    for variant in VARIANTS:
        write_json(
            f"research/experiments/{EXPERIMENTS[variant]}/monthly-models.json",
            {
                "experiment_id": EXPERIMENTS[variant],
                "monthly_models": [
                    {
                        "effective_utc": item["training_manifest"]["effective_utc"],
                        "model_hash": item["model"]["model_hash"],
                        "fit_rows": item["training_manifest"]["fit_rows"],
                        "effective_sample_size": item["model"]["effective_sample_size"],
                        "condition_number": item["model"]["condition_number"],
                        "rank": item["model"]["rank"],
                        "training_matrix_logical_sha256": item["training_manifest"][
                            "training_matrix_logical_sha256"
                        ],
                        "training_label_logical_sha256": item["training_manifest"][
                            "training_label_logical_sha256"
                        ],
                        "purge_boundary_exclusive_us": item["training_manifest"][
                            "purge_boundary_exclusive_us"
                        ],
                        "max_training_label_outcome_us": item["training_manifest"][
                            "max_training_label_outcome_us"
                        ],
                    }
                    for item in results[variant]["monthly_models"]
                ],
            },
        )

    print(json.dumps(comparison["macro_incremental"], indent=2))
    print("family disposition:", comparison["family_disposition"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
