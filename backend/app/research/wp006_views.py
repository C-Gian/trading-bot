"""Deterministic WP-006 projections: descriptive comparison and cumulative accounting.

Everything here reads immutable retained artifacts. Nothing reruns a strategy, loads a
market table, selects a profile, or creates a new evaluation trial.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .checkpoint_views import LABEL, build_comparison, read_json
from .evaluation_protocol import load_protocol, protocol_hash
from .runner import sha256
from .search_memory import accounting as v1_accounting
from .search_memory import load_memory
from .wp006 import ROOT, SPEC
from .wp006 import accounting as v2_accounting

DIAGNOSTIC_DIR = "research/diagnostics/WP-005"
ALIGNED_ID = "EXP-ALG-009-ALIGNED"
PRIMARY_ID = "EXP-ALG-010-PULLBACK-RECOVERY-CORE"
CONFIRM_ID = "EXP-ALG-011-PULLBACK-RECOVERY-CONFIRM"


def _round(value: float | None) -> float | None:
    return round(value, 10) if value is not None else None


def _signals(trades: list[dict[str, Any]]) -> set[int]:
    return {int(trade["signal_us"]) for trade in trades}


def _default_trades(root: Path, experiment_id: str) -> list[dict[str, Any]]:
    trials = read_json(root / "research/experiments" / experiment_id / "trials.json")
    return next(trial for trial in trials if trial["profile"] == "DEFAULT")["trades"]


def _overlap(left: set[int], right: set[int]) -> dict[str, Any]:
    union = left | right
    return {
        "left_signals": len(left),
        "right_signals": len(right),
        "shared_signals": len(left & right),
        "jaccard": _round(len(left & right) / len(union)) if union else None,
        "left_share_shared": _round(len(left & right) / len(left)) if left else None,
    }


def variant_view(root: Path, experiment_id: str) -> dict[str, Any]:
    result = read_json(root / "research/experiments" / experiment_id / "result.json")
    profiles = result["secondary_results"]["profiles"]
    default = profiles["DEFAULT"]
    metrics, stability, diagnostics = (
        default["metrics"],
        default["stability"],
        default["diagnostics"],
    )
    return {
        "experiment_id": experiment_id,
        "source_path": f"research/experiments/{experiment_id}/result.json",
        "source_sha256": sha256(root / "research/experiments" / experiment_id / "result.json"),
        "terminal_classification": result["secondary_results"]["terminal_classification"],
        "default_net_expectancy_r": metrics["net_expectancy_r"],
        "zero_cost_net_expectancy_r": profiles["ZERO"]["metrics"]["net_expectancy_r"],
        "double_cost_net_expectancy_r": profiles["DOUBLE"]["metrics"]["net_expectancy_r"],
        "delay_net_expectancy_r": profiles["DELAY_1H"]["metrics"]["net_expectancy_r"],
        "trade_count": metrics["trade_count"],
        "delay_trade_count": profiles["DELAY_1H"]["metrics"]["trade_count"],
        "unresolved_rate": metrics["unresolved_rate"],
        "nonnegative_fold_count": stability["nonnegative_fold_count"],
        "minimum_fold_trades": diagnostics["minimum_fold_trades"],
        "trade_ess": diagnostics["trade_ess"],
        "max_positive_fold_profit_share": stability["max_positive_fold_profit_share"],
        "active_week_kish_count": diagnostics["active_week_kish_count"],
        "fold_trade_counts": {
            fold["fold_id"]: fold["metrics"]["trade_count"] for fold in default["folds"]
        },
        "fold_net_expectancy_r": {
            fold["fold_id"]: fold["metrics"]["net_expectancy_r"] for fold in default["folds"]
        },
    }


def build_wp006_comparison(root: Path = ROOT) -> dict[str, Any]:
    """Descriptive comparison against every preserved reference. No new trial is run."""
    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    prior = build_comparison(root)
    random_trials = prior["controls"]["EXP-CTRL-002-RANDOM"]["trials"]
    random_values = [item["summary"]["metrics"]["net_expectancy_r"] for item in random_trials]
    variants = {
        "RECOVERY_CORE": variant_view(root, PRIMARY_ID),
        "RECOVERY_CONFIRM": variant_view(root, CONFIRM_ID),
    }
    core = variants["RECOVERY_CORE"]
    confirm = variants["RECOVERY_CONFIRM"]
    core_signals = _signals(_default_trades(root, PRIMARY_ID))
    aligned_signals = _signals(_default_trades(root, ALIGNED_ID))
    parent = read_json(root / DIAGNOSTIC_DIR / "matched-parent.json")
    parent_default = next(item for item in parent["profiles"] if item["profile"] == "DEFAULT")
    parent_signals = _signals(parent_default["trades"])
    breakout_summary = next(
        item
        for item in prior["controls"]["EXP-BASE-004-BREAKOUT"]["trials"]
        if item["profile"] == "DEFAULT"
    )["summary"]
    trend_summary = next(
        item
        for item in prior["controls"]["EXP-BASE-003-TREND"]["trials"]
        if item["profile"] == "DEFAULT"
    )["summary"]
    delay_summary = prior["controls"]["EXP-CTRL-005-TREND-DELAY-1H"]["trials"][0]["summary"]
    no_trade = prior["controls"]["EXP-CTRL-006-NO-TRADE"]["trials"][0]["summary"]
    aligned = prior["variants"]["ALIGNED"]
    aligned_default = aligned["profiles"]["DEFAULT"]["metrics"]["net_expectancy_r"]
    return {
        "schema_version": 1,
        "label": LABEL,
        "protocol_sha256": protocol_hash(protocol),
        "method": "DESCRIPTIVE_SLICING_OF_IMMUTABLE_TRADES_NO_RESIMULATION",
        "new_strategy_trials": 0,
        "diagnostic_evaluations": 0,
        "buy_hold_excluded": True,
        "primary_variant": "RECOVERY_CORE",
        "variants": variants,
        "references": {
            "random_control": {
                "experiment_id": "EXP-CTRL-002-RANDOM",
                "seed_count": len(random_values),
                "selection_policy": "ALL_32_FIXED_SEEDS_NO_SELECTION",
                "minimum_net_expectancy_r": min(random_values),
                "median_net_expectancy_r": _round(
                    sorted(random_values)[len(random_values) // 2 - 1] / 2
                    + sorted(random_values)[len(random_values) // 2] / 2
                ),
                "maximum_net_expectancy_r": max(random_values),
                "mean_net_expectancy_r": _round(math.fsum(random_values) / len(random_values)),
            },
            "sma_trend": {
                "experiment_id": "EXP-BASE-003-TREND",
                "default_net_expectancy_r": trend_summary["metrics"]["net_expectancy_r"],
                "trade_count": trend_summary["metrics"]["trade_count"],
            },
            "sma_trend_delay_1h": {
                "experiment_id": "EXP-CTRL-005-TREND-DELAY-1H",
                "default_net_expectancy_r": delay_summary["metrics"]["net_expectancy_r"],
                "trade_count": delay_summary["metrics"]["trade_count"],
            },
            "breakout": {
                "experiment_id": "EXP-BASE-004-BREAKOUT",
                "default_net_expectancy_r": breakout_summary["metrics"]["net_expectancy_r"],
                "trade_count": breakout_summary["metrics"]["trade_count"],
            },
            "matched_parent_breakout": {
                "source_path": f"{DIAGNOSTIC_DIR}/matched-parent.json",
                "default_net_expectancy_r": parent_default["summary"]["metrics"][
                    "net_expectancy_r"
                ],
                "trade_count": parent_default["summary"]["metrics"]["trade_count"],
            },
            "aligned": {
                "experiment_id": ALIGNED_ID,
                "terminal_classification": aligned["terminal_classification"],
                "default_net_expectancy_r": aligned_default,
                "trade_count": aligned["profiles"]["DEFAULT"]["metrics"]["trade_count"],
            },
            "no_trade": {
                "experiment_id": "EXP-CTRL-006-NO-TRADE",
                "trade_count": no_trade["metrics"]["trade_count"],
            },
        },
        "deltas": {
            "core_minus_matched_parent_r": _round(
                core["default_net_expectancy_r"]
                - parent_default["summary"]["metrics"]["net_expectancy_r"]
            ),
            "core_minus_breakout_r": _round(
                core["default_net_expectancy_r"] - breakout_summary["metrics"]["net_expectancy_r"]
            ),
            "core_minus_trend_r": _round(
                core["default_net_expectancy_r"] - trend_summary["metrics"]["net_expectancy_r"]
            ),
            "core_minus_aligned_r": _round(core["default_net_expectancy_r"] - aligned_default),
            "core_minus_random_mean_r": _round(
                core["default_net_expectancy_r"] - math.fsum(random_values) / len(random_values)
            ),
        },
        "interpretation": {
            "gross_margin_r": core["zero_cost_net_expectancy_r"],
            "default_cost_survival": core["default_net_expectancy_r"] > 0,
            "cost_drag_r": _round(
                core["zero_cost_net_expectancy_r"] - core["default_net_expectancy_r"]
            ),
            "double_cost_survival": core["double_cost_net_expectancy_r"] > 0,
            "double_cost_sensitivity_r": _round(
                core["default_net_expectancy_r"] - core["double_cost_net_expectancy_r"]
            ),
            "fold_coverage": {
                "populated_folds": sum(1 for count in core["fold_trade_counts"].values() if count),
                "minimum_fold_trades": core["minimum_fold_trades"],
                "required_minimum_fold_trades": protocol["diagnostics"]["minimum_fold_trades"],
                "total_trades": core["trade_count"],
                "required_total_trades": protocol["diagnostics"]["minimum_total_trades"],
            },
            "concentration": {
                "max_positive_fold_profit_share": core["max_positive_fold_profit_share"],
                "limit": protocol["diagnostics"]["maximum_positive_fold_profit_share"],
                "active_week_kish_count": core["active_week_kish_count"],
            },
            "confirmation_effect": {
                "trades_removed": core["trade_count"] - confirm["trade_count"],
                "expectancy_change_r": _round(
                    confirm["default_net_expectancy_r"] - core["default_net_expectancy_r"]
                ),
                "minimum_fold_trades_change": confirm["minimum_fold_trades"]
                - core["minimum_fold_trades"],
            },
            "timing_delay_sensitivity": {
                "core_expectancy_change_r": _round(
                    core["delay_net_expectancy_r"] - core["default_net_expectancy_r"]
                ),
                "core_trade_count_change": core["delay_trade_count"] - core["trade_count"],
            },
            "distinction_from_breakout": {
                "method": "EXECUTED_SIGNAL_TIMESTAMP_OVERLAP_ON_IMMUTABLE_RETAINED_TRADES_AFTER_OCCUPANCY_SUPPRESSION",
                "vs_matched_parent_breakout": _overlap(core_signals, parent_signals),
                "vs_aligned": _overlap(core_signals, aligned_signals),
            },
        },
        "limitations": [
            "All history here is previously exposed development data, not fresh out-of-sample or sealed evidence.",
            "The WP-003 controls keep their own eligibility, occupancy and execution semantics; differences are not paired causal estimates.",
            "Random seeds share one price history and are not independent evidence.",
            "Overlap is measured on executed signals after occupancy suppression, not on raw conditions; it describes when the rules fired, not why, and low overlap is not proof of an independent economic mechanism.",
            "Summed R is trade accounting, not a funded, equal-capital compounded portfolio return.",
            "Neither variant met its preregistered sufficiency diagnostics, so none of these differences is decision-grade.",
        ],
    }


def cumulative_accounting(root: Path = ROOT) -> dict[str, int]:
    """One total search burden across the frozen V1 layer and the additive V2 layer."""
    memory = load_memory(root)
    first = v1_accounting(memory)
    second = v2_accounting(root)
    allocation = read_json(root / "research/memory/WP006-PULLBACK-RECOVERY-ALLOCATION.json")
    return {
        "material_economic_hypotheses": first["material_economic_hypotheses"]
        + second["material_economic_hypotheses"],
        "configuration_variants": first["global"]["strategy_variants"]
        + second["strategy_variants"],
        "profile_trials": first["global"]["trials"] + second["trials"],
        "numeric_parameter_variants": first["global"]["numeric_parameter_variants"]
        + second["numeric_parameter_variants"],
        "adaptive_decisions": allocation["cumulative_adaptive_decisions"],
        "result_dependent_forks": allocation["cumulative_result_dependent_forks"],
        "strategy_descendants": first["strategy_descendants"] + second["strategy_descendants"],
        "wp004_variants_reserved": 3,
        "wp004_profiles_reserved": 12,
        "wp006_variants_reserved": second["strategy_variants"],
        "wp006_profiles_reserved": second["trials"],
        "integrity_replay_profiles": 12,
        "diagnostic_evaluations": 35,
        "diagnostic_execution_attempts": 2,
        "sealed_queries": 0,
    }


def v2_budget_view(root: Path = ROOT) -> list[dict[str, Any]]:
    budget = read_json(root / "research/memory/SEARCH_BUDGET_V2.json")
    counts = v2_accounting(root)
    return [
        {
            "family_id": family,
            "experiments_consumed": counts["experiments"],
            "experiments_limit": limit["experiments"],
            "trials_consumed": counts["trials"],
            "trials_limit": limit["trials"],
        }
        for family, limit in budget["family_limits"].items()
    ]


def wp006_experiment_rows(root: Path = ROOT) -> list[dict[str, Any]]:
    rows = []
    for experiment_id in SPEC:
        path = root / "research/experiments" / experiment_id / "result.json"
        if not path.is_file():
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "experiment_id": experiment_id,
                "classification": result["secondary_results"]["terminal_classification"],
                "primary_metric": "Default-cost validation net expectancy R",
                "primary_result": result["primary_result"],
                "trade_count": result["secondary_results"]["profiles"]["DEFAULT"]["metrics"][
                    "trade_count"
                ],
                "validation_status": result["validation_outcome"],
                "evidence_window": "WP-006 exposed annual validation (2019–2024)",
            }
        )
    return rows
