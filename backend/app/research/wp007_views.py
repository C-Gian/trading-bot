"""Read-only projections of immutable WP-007 results and preserved references."""

from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any

from .checkpoint_views import build_comparison, read_json
from .runner import sha256
from .wp004 import ROOT

CORE_ID = "EXP-ALG-012-ORDERFLOW-CORE"
PRICE_ID = "EXP-ALG-013-ORDERFLOW-PRICE-RESPONSE"


def variant_view(root: Path, experiment_id: str) -> dict[str, Any]:
    result_path = root / "research/experiments" / experiment_id / "result.json"
    result = read_json(result_path)
    profiles = result["secondary_results"]["profiles"]
    default = profiles["DEFAULT"]
    return {
        "experiment_id": experiment_id,
        "result_path": result_path.relative_to(root).as_posix(),
        "result_sha256": sha256(result_path),
        "terminal_classification": result["secondary_results"]["terminal_classification"],
        "default_net_expectancy_r": default["metrics"]["net_expectancy_r"],
        "zero_cost_net_expectancy_r": profiles["ZERO"]["metrics"]["net_expectancy_r"],
        "double_cost_net_expectancy_r": profiles["DOUBLE"]["metrics"]["net_expectancy_r"],
        "delay_net_expectancy_r": profiles["DELAY_1H"]["metrics"]["net_expectancy_r"],
        "trade_count": default["metrics"]["trade_count"],
        "delay_trade_count": profiles["DELAY_1H"]["metrics"]["trade_count"],
        "attempted_setups": default["metrics"]["attempted_setups"],
        "invalid_attempts": default["metrics"]["invalid_attempts"],
        "unresolved_trades": default["metrics"]["unresolved_trades"],
        "unresolved_rate": default["metrics"]["unresolved_rate"],
        "cost_drag_r": default["metrics"]["cost_drag_r"],
        "nonnegative_fold_count": default["stability"]["nonnegative_fold_count"],
        "minimum_fold_trades": default["diagnostics"]["minimum_fold_trades"],
        "trade_ess": default["diagnostics"]["trade_ess"],
        "active_week_kish_count": default["diagnostics"]["active_week_kish_count"],
        "max_positive_fold_profit_share": default["stability"]["max_positive_fold_profit_share"],
        "folds": [
            {
                "fold_id": fold["fold_id"],
                "trade_count": fold["metrics"]["trade_count"],
                "net_expectancy_r": fold["metrics"]["net_expectancy_r"],
            }
            for fold in default["folds"]
        ],
    }


def build_wp007_comparison(root: Path = ROOT) -> dict[str, Any]:
    prior = build_comparison(root)
    wp006 = read_json(root / "reports/research/WP-006-COMPARISON.json")
    random_trials = prior["controls"]["EXP-CTRL-002-RANDOM"]["trials"]
    references = {
        "random_control_mean": round(
            mean(item["summary"]["metrics"]["net_expectancy_r"] for item in random_trials), 10
        ),
        "sma_trend": next(
            item
            for item in prior["controls"]["EXP-BASE-003-TREND"]["trials"]
            if item["profile"] == "DEFAULT"
        )["summary"]["metrics"]["net_expectancy_r"],
        "breakout": next(
            item
            for item in prior["controls"]["EXP-BASE-004-BREAKOUT"]["trials"]
            if item["profile"] == "DEFAULT"
        )["summary"]["metrics"]["net_expectancy_r"],
        "aligned": prior["variants"]["ALIGNED"]["profiles"]["DEFAULT"]["metrics"][
            "net_expectancy_r"
        ],
        "pullback_recovery_core": wp006["variants"]["RECOVERY_CORE"]["default_net_expectancy_r"],
        "no_trade": None,
    }
    variants = {
        "FLOW_CORE": variant_view(root, CORE_ID),
        "FLOW_PRICE_RESPONSE": variant_view(root, PRICE_ID),
    }
    core = variants["FLOW_CORE"]
    return {
        "schema_version": 1,
        "work_package": "WP-007",
        "label": "DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE",
        "method": "DESCRIPTIVE_COMPARISON_OF_IMMUTABLE_RESULTS_NO_NEW_TRIAL",
        "paired_comparison": False,
        "new_strategy_trials": 0,
        "primary_variant": "FLOW_CORE",
        "family_terminal_classification": core["terminal_classification"],
        "variants": variants,
        "references": references,
        "core_deltas": {
            key: None if value is None else round(core["default_net_expectancy_r"] - value, 10)
            for key, value in references.items()
        },
        "interpretation": {
            "zero_cost_signal_positive": core["zero_cost_net_expectancy_r"] > 0,
            "default_friction_consumes_signal": core["default_net_expectancy_r"] < 0,
            "double_cost_survives": core["double_cost_net_expectancy_r"] >= 0,
            "delay_weakens_expectancy": (
                core["delay_net_expectancy_r"] < core["default_net_expectancy_r"]
            ),
            "price_response_improves_default_expectancy": (
                variants["FLOW_PRICE_RESPONSE"]["default_net_expectancy_r"]
                > core["default_net_expectancy_r"]
            ),
            "price_response_reduces_coverage": (
                variants["FLOW_PRICE_RESPONSE"]["trade_count"] < core["trade_count"]
            ),
        },
        "limitations": [
            "All folds are exposed development history, not sealed or prospective evidence.",
            "Reference families retain different eligibility and occupancy semantics; deltas are not paired causal estimates.",
            "Binance taker-buy base share is a venue-level aggressive-participation proxy, not market-wide signed demand or investor intent.",
            "Distinct inputs and entry logic establish structural novelty, not causality or profitable mechanism validation.",
        ],
    }
