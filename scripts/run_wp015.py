"""Execute the frozen WP-015 walk-forward after its committed safe gate."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.artifacts import write_parquet
from app.research.continuation_lab import PROFILES, ResearchInputs
from app.research.evaluation_protocol import terminal_classification
from app.research.funding import MANIFEST_PATH, load_funding_context
from app.research.supervised import load_feature_source
from app.research.wp015 import (
    CONTROL_VARIANT,
    EXPERIMENTS,
    PRIMARY_VARIANT,
    VARIANTS,
    dependency_manifest,
    load_protocol,
    load_walk_forward,
    preflight,
)
from app.research.wp015_lab import (
    PREDICTION_SCHEMA,
    TRIAL_SCHEMA,
    FundingContextLab,
    parquet_rows,
)

TRIALS_PATH = "data/derived/WP-015-funding-trials.parquet"
PREDICTIONS_PATH = "data/derived/WP-015-funding-predictions.parquet"
COMPARISON_PATH = "reports/research/WP-015-COMPARISON.json"
DIAGNOSTICS_PATH = "reports/research/WP-015-FUNDING-DIAGNOSTICS.json"


def write_json(relative: str, payload: Any) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "median": None, "max": None, "mean": None}
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": len(values),
        "min": float(array.min()),
        "median": float(np.median(array)),
        "max": float(array.max()),
        "mean": float(array.mean()),
    }


def sign_label(value: float) -> str:
    return "NEGATIVE" if value < 0 else "POSITIVE" if value > 0 else "ZERO"


def funding_diagnostics(results: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    records = results[PRIMARY_VARIANT]["prediction_records"]
    by_fold: dict[str, list[float]] = defaultdict(list)
    for row in records:
        by_fold[row["fold_id"]].append(row["funding_rate"])
    all_rates = [row["funding_rate"] for row in records]
    sign_counts = {
        name: sum(sign_label(value) == name for value in all_rates)
        for name in (
            "NEGATIVE",
            "ZERO",
            "POSITIVE",
        )
    }
    default_trades = results[PRIMARY_VARIANT]["profiles"]["DEFAULT"]["trades"]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trade in default_trades:
        groups[sign_label(trade["funding_rate"])].append(trade)
    trade_groups: dict[str, Any] = {}
    for name in ("NEGATIVE", "ZERO", "POSITIVE"):
        trades = groups[name]
        valid = [trade for trade in trades if trade["status"] == "VALID"]
        net = [trade["net_r"] for trade in valid]
        trade_groups[name] = {
            "executed_attempts": len(trades),
            "valid_resolved_trades": len(valid),
            "mean_net_r": float(np.mean(net)) if net else None,
            "cumulative_net_r": float(np.sum(net)) if net else 0.0,
        }
    return {
        "schema_version": 1,
        "work_package": "WP-015",
        "diagnostic_only": True,
        "used_to_adapt_experiment": False,
        "funding_observations_acquired": manifest["records"],
        "first_funding_time": manifest["first_funding_time"],
        "last_funding_time": manifest["last_funding_time"],
        "hourly_eligible_coverage": len(records),
        "funding_distribution": distribution(all_rates),
        "funding_distribution_by_fold": {
            fold: distribution(values) for fold, values in sorted(by_fold.items())
        },
        "sign_distribution": {
            name: {
                "count": count,
                "fraction": count / len(all_rates),
            }
            for name, count in sign_counts.items()
        },
        "prediction_groups": results[PRIMARY_VARIANT]["funding_prediction_diagnostics"],
        "mean_funding_executed_trades": (
            float(np.mean([trade["funding_rate"] for trade in default_trades]))
            if default_trades
            else None
        ),
        "default_trade_outcomes_by_funding_sign": trade_groups,
    }


def main() -> int:
    if preflight(ROOT)["status"] != "PASS":
        raise RuntimeError("WP-015 pre-result gate failed")
    if any(
        (ROOT / f"research/experiments/{experiment}/result.json").exists()
        for experiment in EXPERIMENTS.values()
    ):
        raise RuntimeError("WP-015 results already exist; refusing rerun")
    protocol = load_protocol(ROOT)
    walk_forward = load_walk_forward(ROOT)
    lab = FundingContextLab(
        ResearchInputs.load(ROOT),
        load_feature_source(ROOT),
        load_funding_context(ROOT),
        walk_forward,
    )
    lab.dependencies = dependency_manifest(ROOT)
    results: dict[str, Any] = {}
    trial_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    for variant in VARIANTS:
        print(f"running {variant}", flush=True)
        result = lab.run_configuration(variant)
        results[variant] = result
        prediction_rows.extend(result["prediction_records"])
        for profile in PROFILES:
            trial_rows.extend(parquet_rows(result["profiles"][profile]))
        write_json(
            f"research/experiments/{EXPERIMENTS[variant]}/fold-models.json",
            {
                "schema_version": 1,
                "work_package": "WP-015",
                "experiment_id": EXPERIMENTS[variant],
                "variant": variant,
                "architecture": "sklearn.ensemble.HistGradientBoostingRegressor",
                "fold_models": result["folds"],
                "model_fits": result["model_fits"],
            },
        )
    trials_artifact = write_parquet(
        ROOT / TRIALS_PATH,
        trial_rows,
        schema=TRIAL_SCHEMA,
        sort_key=["variant", "profile", "signal_us"],
        root=ROOT,
    )
    prediction_artifact = write_parquet(
        ROOT / PREDICTIONS_PATH,
        prediction_rows,
        schema=PREDICTION_SCHEMA,
        sort_key=["variant", "fold_id", "signal_us"],
        root=ROOT,
    )
    comparison: dict[str, Any] = {
        "schema_version": 1,
        "work_package": "WP-015",
        "protocol_id": protocol["protocol_id"],
        "model_version": protocol["model_version"],
        "primary_variant": PRIMARY_VARIANT,
        "control_variant": CONTROL_VARIANT,
        "trials_artifact": trials_artifact,
        "predictions_artifact": prediction_artifact,
        "configurations": {},
    }
    for variant in VARIANTS:
        summaries = {
            profile: results[variant]["profiles"][profile]["summary"] for profile in PROFILES
        }
        comparison["configurations"][variant] = {
            "experiment_id": EXPERIMENTS[variant],
            "primary_result": summaries["DEFAULT"]["metrics"]["net_expectancy_r"],
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
            "prediction_diagnostics": results[variant]["prediction_diagnostics"],
            "model_fits": results[variant]["model_fits"],
        }
    primary = comparison["configurations"][PRIMARY_VARIANT]
    control = comparison["configurations"][CONTROL_VARIANT]
    comparison["primary_vs_control"] = {
        "default_net_expectancy_difference_r": primary["primary_result"]
        - control["primary_result"],
        "default_trade_count_difference": (
            primary["profiles"]["DEFAULT"]["metrics"]["trade_count"]
            - control["profiles"]["DEFAULT"]["metrics"]["trade_count"]
        ),
        "eligible_universe_matched": True,
        "executed_trade_sets_paired": False,
        "control_classification": "KNOWN_INTERNAL_HGBR_MATCHED_CONTROL",
        "control_known_mechanism": "EXP-ML-022-SHALLOW-INTERNAL-HGBR",
    }
    write_json(COMPARISON_PATH, comparison)
    manifest = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    write_json(DIAGNOSTICS_PATH, funding_diagnostics(results, manifest))
    print(json.dumps(comparison["primary_vs_control"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
