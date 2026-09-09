"""Read-only WP-008 projections from immutable results."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from .registry import cumulative_accounting as registry_accounting
from .runner import sha256
from .wp004 import ROOT
from .wp008 import SPEC


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def cumulative_accounting(root: Path = ROOT) -> dict[str, int]:
    return registry_accounting(root)


def variant_view(root: Path, experiment_id: str, variant: str) -> dict[str, Any]:
    path = root / "research/experiments" / experiment_id / "result.json"
    result = read_json(path)
    secondary = result["secondary_results"]
    profiles = secondary["profiles"]
    default = profiles["DEFAULT"]["summary"]
    signs = {
        feature: [
            1 if value > 0 else -1 if value < 0 else 0
            for value in [model["coefficients"][index] for model in secondary["fold_models"]]
        ]
        for index, feature in enumerate(secondary["fold_models"][0]["feature_order"])
    }
    diagnostics = secondary["prediction_diagnostics"]
    eligible = sum(item["validation_eligible_count"] for item in diagnostics)
    positives = sum(item["prediction_positive_count"] for item in diagnostics)
    correlations = [item["prediction_label_pearson"] for item in diagnostics]
    return {
        "experiment_id": experiment_id,
        "variant": variant,
        "result_path": path.relative_to(root).as_posix(),
        "result_sha256": sha256(path),
        "terminal_classification": secondary["terminal_classification"],
        "default_net_expectancy_r": default["metrics"]["net_expectancy_r"],
        "zero_cost_net_expectancy_r": profiles["ZERO"]["summary"]["metrics"]["net_expectancy_r"],
        "double_cost_net_expectancy_r": profiles["DOUBLE"]["summary"]["metrics"][
            "net_expectancy_r"
        ],
        "delay_net_expectancy_r": profiles["DELAY_1H"]["summary"]["metrics"]["net_expectancy_r"],
        "trade_count": default["metrics"]["trade_count"],
        "delay_trade_count": profiles["DELAY_1H"]["summary"]["metrics"]["trade_count"],
        "nonnegative_fold_count": default["stability"]["nonnegative_fold_count"],
        "minimum_fold_trades": default["diagnostics"]["minimum_fold_trades"],
        "trade_ess": default["diagnostics"]["trade_ess"],
        "max_positive_fold_profit_share": default["stability"]["max_positive_fold_profit_share"],
        "max_absolute_fold_pnl_share": default["stability"]["max_absolute_fold_pnl_share"],
        "validation_eligible_count": eligible,
        "prediction_positive_count": positives,
        "prediction_positive_fraction": round(positives / eligible, 10),
        "prediction_label_pearson_min": min(correlations),
        "prediction_label_pearson_mean": mean(correlations),
        "prediction_label_pearson_max": max(correlations),
        "coefficient_signs_by_fold": signs,
        "coefficient_sign_consistent_features": sum(
            len(set(values)) == 1 for values in signs.values()
        ),
        "condition_number_min": min(item["condition_number"] for item in secondary["fold_models"]),
        "condition_number_max": max(item["condition_number"] for item in secondary["fold_models"]),
        "folds": [
            {
                "fold_id": fold["fold_id"],
                "trade_count": fold["metrics"]["trade_count"],
                "net_expectancy_r": fold["metrics"]["net_expectancy_r"],
                "cumulative_net_r": fold["metrics"]["cumulative_net_r"],
            }
            for fold in default["folds"]
        ],
        "artifact_manifest": secondary["artifact_manifest"],
    }


def build_wp008_comparison(root: Path = ROOT) -> dict[str, Any]:
    prior = read_json(root / "reports/research/WP-007-COMPARISON.json")
    variants = {
        variant: variant_view(root, experiment_id, variant)
        for experiment_id, variant in SPEC.items()
    }
    full = variants["LINEAR_FULL"]
    references = prior["references"] | {
        "order_flow_core": prior["variants"]["FLOW_CORE"]["default_net_expectancy_r"]
    }
    return {
        "schema_version": 1,
        "work_package": "WP-008",
        "label": "DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE",
        "method": "DESCRIPTIVE_COMPARISON_OF_IMMUTABLE_RESULTS_NO_NEW_TRIAL",
        "paired_comparison": False,
        "new_strategy_trials": 0,
        "primary_variant": "LINEAR_FULL",
        "family_terminal_classification": full["terminal_classification"],
        "variants": variants,
        "references": references,
        "full_deltas": {
            key: None if value is None else round(full["default_net_expectancy_r"] - value, 10)
            for key, value in references.items()
        },
        "interpretation": {
            "zero_cost_signal_positive": full["zero_cost_net_expectancy_r"] > 0,
            "default_friction_consumes_signal": full["default_net_expectancy_r"] < 0,
            "double_cost_survives": full["double_cost_net_expectancy_r"] >= 0,
            "delay_materially_changes_disposition": full["delay_net_expectancy_r"] >= 0,
            "no_flow_materially_improves_disposition": variants["LINEAR_NO_FLOW"][
                "terminal_classification"
            ]
            != full["terminal_classification"],
            "broad_long_drift_only": full["prediction_positive_fraction"] >= 0.5,
            "one_positive_year_only": full["nonnegative_fold_count"] == 1,
        },
        "limitations": [
            "All folds are exposed development history, not sealed or prospective evidence.",
            "Reference families have different eligibility and occupancy; deltas are descriptive, not causal or paired.",
            "OLS coefficients are fold outputs, not independently tested hypotheses.",
            "No post-result feature, threshold, model, regularization, interaction, or execution change is authorized.",
        ],
    }
