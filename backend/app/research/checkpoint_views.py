"""Read-only, deterministic projections of existing evidence; no market execution."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any

from .evaluation_protocol import load_protocol, protocol_hash, summarize_trades
from .runner import sha256
from .search_memory import accounting, load_memory, render_failure_memory, render_research_map
from .wp004 import ROOT, SPEC

LABEL = "DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE"
CONTROL_IDS = (
    "EXP-CTRL-002-RANDOM",
    "EXP-BASE-003-TREND",
    "EXP-BASE-004-BREAKOUT",
    "EXP-CTRL-005-TREND-DELAY-1H",
    "EXP-CTRL-006-NO-TRADE",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_comparison(root: Path = ROOT) -> dict[str, Any]:
    """Apply the predeclared windows to old saved trades, preserving every seed."""
    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    controls: dict[str, Any] = {}
    for eid in CONTROL_IDS:
        path = root / "research/experiments" / eid / "trials.json"
        trials = read_json(path)
        controls[eid] = {
            "source_path": path.relative_to(root).as_posix(),
            "source_sha256": sha256(path),
            "trials": [
                {
                    "trial_id": t["trial_id"],
                    "seed": t["seed"],
                    "profile": t["profile"],
                    "summary": summarize_trades(
                        t["trades"], protocol, allow_unclassified_regime=True
                    ),
                }
                for t in trials
            ],
        }
    random = controls["EXP-CTRL-002-RANDOM"]["trials"]
    values = [t["summary"]["metrics"]["net_expectancy_r"] for t in random]
    counts = [t["summary"]["metrics"]["trade_count"] for t in random]
    variants: dict[str, Any] = {}
    for eid, (variant, _) in SPEC.items():
        path = root / "research/experiments" / eid / "result.json"
        result = read_json(path)
        variants[variant] = {
            "experiment_id": eid,
            "source_path": path.relative_to(root).as_posix(),
            "source_sha256": sha256(path),
            "terminal_classification": result["secondary_results"]["terminal_classification"],
            "profiles": result["secondary_results"]["profiles"],
        }
    return {
        "schema_version": 1,
        "label": LABEL,
        "protocol_sha256": protocol_hash(protocol),
        "method": "DESCRIPTIVE_SLICING_OF_IMMUTABLE_TRADES_NO_RESIMULATION",
        "new_strategy_trials": 0,
        "buy_hold_excluded": True,
        "limitations": [
            "All history is previously exposed development data, not fresh out-of-sample or sealed evidence.",
            "Same annual signal windows and full 24h containment; old control paths retain pre-window occupancy.",
            "WP-003 uses 169h eligibility and can reenter at an intrabar exit's open; WP-004 requires contiguous 4h context and waits through that minute's close.",
            "Off-grid source intervals in 2017/2018 limit full-history WP-003 interpretation; those intervals precede these validation windows and warm-up.",
            "Random timing, regime exposure, frequency and occupancy are not matched to the new gates. Seeds share one price history and are not independent evidence.",
            "Differences are descriptive, not a paired significance test, causal attribution, or validated improvement in deployable returns.",
            "Summed R/bps are trade accounting, not a funded/equal-capital compounded portfolio return.",
        ],
        "controls": controls,
        "random_seed_distribution": {
            "seed_count": len(random),
            "selection_policy": "ALL_32_FIXED_SEEDS_NO_SELECTION",
            "minimum_net_expectancy_r": min(values),
            "median_net_expectancy_r": round(median(values), 10),
            "maximum_net_expectancy_r": max(values),
            "positive_seed_count": sum(v > 0 for v in values),
            "minimum_trade_count": min(counts),
            "median_trade_count": median(counts),
            "maximum_trade_count": max(counts),
            "fold_median_net_expectancy_r": {
                fold["fold_id"]: round(
                    median(t["summary"]["folds"][i]["metrics"]["net_expectancy_r"] for t in random),
                    10,
                )
                for i, fold in enumerate(protocol["folds"])
            },
        },
        "variants": variants,
        "primary_variant": "ALIGNED",
        "selected_family_terminal_classification": variants["ALIGNED"]["terminal_classification"],
    }


def experiment_view(root: Path = ROOT, *, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state if state is not None else read_json(root / "state/current_state.json")
    historical = read_json(root / "reports/research/WP-003-BASELINES.json")
    experiments = [
        {**item, "evidence_window": "WP-003 full development history (2017–2024)"}
        for item in historical["experiments"]
    ]
    for eid in SPEC:
        path = root / "research/experiments" / eid / "result.json"
        if not path.is_file():
            continue
        result = read_json(path)
        experiments.append(
            {
                "experiment_id": eid,
                "classification": result["secondary_results"]["terminal_classification"],
                "primary_metric": "Default-cost validation net expectancy R",
                "primary_result": result["primary_result"],
                "trade_count": result["secondary_results"]["profiles"]["DEFAULT"]["metrics"][
                    "trade_count"
                ],
                "validation_status": result["validation_outcome"],
                "evidence_window": "WP-004 exposed annual validation (2019–2024)",
            }
        )
    return {
        "label": LABEL,
        "evidence_stage": "EXPOSED DEVELOPMENT / CONTROLS — NO STRATEGY APPROVAL",
        "experiments": experiments,
        "latest_checkpoint": state["latest_executor_checkpoint"],
        "next_checkpoint": state["next_recommended_work_package"],
    }


def budget_view(root: Path = ROOT) -> list[dict[str, Any]]:
    memory = load_memory(root)
    counts = accounting(memory)
    return [
        {
            "family_id": family,
            "experiments_consumed": counts["families"][family]["experiments"],
            "experiments_limit": limit["experiments"],
            "trials_consumed": counts["families"][family]["trials"],
            "trials_limit": limit["trials"],
        }
        for family, limit in memory["budget"]["family_limits"].items()
    ]


def memory_views(root: Path = ROOT) -> dict[str, str]:
    memory = load_memory(root)
    lessons = read_json(root / "research/memory/WP-004-LESSONS.json")
    rows = [
        "",
        "## WP-004 evidence and current research dispositions",
        "",
        "Generated from WP-004-LESSONS.json and immutable results. Earlier family revisit text above is",
        "historical admission rationale, not a fresh allocation; the WP-003 clue has now been consumed.",
        "",
        "| Experiment | Default net expectancy R | Resolved trades | Key lesson |",
        "|---|---:|---:|---|",
    ]
    for eid, item in lessons["experiments"].items():
        result = read_json(root / item["result_path"])
        metrics = result["secondary_results"]["profiles"]["DEFAULT"]["metrics"]
        rows.append(
            f"| {eid} | {result['primary_result']:+.10f} | {metrics['trade_count']} | {item['key_lesson']} |"
        )
    rows.extend(
        [
            "",
            "Current family disposition: " + lessons["family_disposition"],
            "",
            "Legitimate next direction: " + lessons["legitimate_next_direction"],
            "",
            "Blocked repeats: " + "; ".join(lessons["blocked_directions"]) + ".",
            "",
        ]
    )
    failures = [
        "",
        "## WP-004 interpretive limits and retirement",
        "",
        "Generated from WP-004-LESSONS.json; the original outcomes above are not amended.",
        "",
    ]
    for eid, item in lessons["experiments"].items():
        failures.extend([f"- {eid}: {item['key_lesson']} {item['not_established']}"])
    failures.extend(
        ["", lessons["family_disposition"], "", lessons["legitimate_next_direction"], ""]
    )
    return {
        "RESEARCH_MAP.md": render_research_map(memory) + "\n".join(rows),
        "FAILURE_MEMORY.md": render_failure_memory(memory) + "\n".join(failures),
    }
