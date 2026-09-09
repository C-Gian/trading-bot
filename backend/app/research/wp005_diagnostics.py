"""Frozen matched-parent, matched-random-gate, and coverage diagnostics for WP-005."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections import Counter
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.backtest.engine import simulate
from app.backtest.models import ExitReason, Intent

from .continuation_lab import DATASET_HASH, DATASET_ID, MINUTE_US, ResearchInputs, costs
from .evaluation_protocol import EPOCH, HOUR_US, load_protocol, summarize_trades, utc_us
from .search_memory import text_sha256
from .wp005_integrity import OracleBars, canonical_hash, normalized_file_hash

ALIGNED_EXPECTANCY = 0.1373934676
PROFILES = ("DEFAULT", "ZERO", "DOUBLE")
SEED_PREFIX = "WP005_MATCHED_RANDOM_GATE_SEED"
RANK_PREFIX = "WP005_MATCHED_RANDOM_GATE_V1"


def random_gate_seed(index: int) -> int:
    if not 0 <= index < 32:
        raise ValueError("random-gate seed index is outside frozen range")
    digest = hashlib.sha256(f"{SEED_PREFIX}:{index}".encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def random_gate_rank(seed: int, timestamp_us: int) -> bytes:
    return hashlib.sha256(f"{RANK_PREFIX}:{seed}:{timestamp_us}".encode("ascii")).digest()


def quantile_type7(values: list[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise ValueError("invalid deterministic quantile input")
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    value = ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])
    return round(value, 10)


def _trade(
    inputs: ResearchInputs,
    signal_us: int,
    reference: float,
    profile: str,
    run_id: str,
) -> tuple[dict[str, Any], int]:
    instant = EPOCH + timedelta(microseconds=signal_us)
    price = Decimal(str(reference))
    intent = Intent(
        run_id,
        "WP005_FROZEN_24H_BREAKOUT_MATCHED_DIAGNOSTIC",
        DATASET_ID,
        DATASET_HASH,
        instant,
        "LONG",
        "NEXT_1M_OPEN",
        price * Decimal("0.98"),
        price * Decimal("1.04"),
        "FIXED_TARGET_OR_STOP_OR_24H",
        1440,
    )
    record = simulate(intent, inputs.path(signal_us), costs(profile))
    trade: dict[str, Any] = {
        "signal_us": signal_us,
        "year": instant.year,
        "status": record.data_quality_status,
        "reason": str(record.exit_reason),
        "record": record.deterministic_dict(),
        "reference": reference,
    }
    if record.data_quality_status == "VALID":
        assert record.exit_timestamp is not None
        assert record.net_r is not None and record.gross_r is not None
        assert record.net_pnl is not None and record.entry_raw_price is not None
        exit_us = utc_us(record.exit_timestamp)
        trade.update(
            exit_us=exit_us,
            net_r=float(record.net_r),
            gross_r=float(record.gross_r),
            cost_drag_r=float(record.gross_r - record.net_r),
            net_return_bps=float(record.net_pnl / record.entry_raw_price * 10000),
        )
        available = exit_us if record.exit_reason == ExitReason.EXPIRY else exit_us + MINUTE_US
    elif record.data_quality_status == "UNRESOLVED":
        available = signal_us + 1440 * MINUTE_US
    else:
        available = signal_us
    trade["position_available_us"] = available
    return trade, available


def _candidate_universe(root: Path) -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    oracle = OracleBars(root)
    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    folds: dict[str, Any] = {}
    features: dict[int, dict[str, Any]] = {}
    for fold in protocol["folds"]:
        fold_id = fold["fold_id"]
        total = eligible = persistent_eligible = 0
        parent: list[int] = []
        persistence: list[int] = []
        participation: list[int] = []
        aligned: list[int] = []
        for signal in range(
            utc_us(fold["validation_start"]),
            utc_us(fold["last_signal_inclusive"]) + 1,
            HOUR_US,
        ):
            total += 1
            current = oracle.features(signal)
            previous = oracle.features(signal - HOUR_US)
            if current is None or previous is None:
                continue
            eligible += 1
            persistent_eligible += int(current["persistent_up"])
            features[signal] = current
            if not current["breakout"]:
                continue
            parent.append(signal)
            if current["persistent_up"]:
                persistence.append(signal)
            if current["participation"]:
                participation.append(signal)
            if current["persistent_up"] and current["participation"]:
                aligned.append(signal)
        folds[fold_id] = {
            "total": total,
            "eligible": eligible,
            "persistent_eligible": persistent_eligible,
            "parent": parent,
            "persistence": persistence,
            "participation": participation,
            "aligned": aligned,
        }
    return folds, features


def _execute(
    inputs: ResearchInputs,
    protocol: dict[str, Any],
    selected: dict[str, list[int]],
    features: dict[int, dict[str, Any]],
    profile: str,
    run_id: str,
) -> dict[str, Any]:
    trades = []
    diagnostics = []
    for fold in protocol["folds"]:
        fold_id = fold["fold_id"]
        blocked_until = -1
        suppressed = 0
        for signal in selected[fold_id]:
            if signal < blocked_until:
                suppressed += 1
                continue
            trade, blocked_until = _trade(
                inputs, signal, features[signal]["reference"], profile, run_id
            )
            trade.update(
                fold_id=fold_id,
                regime="PERSISTENT_UP" if features[signal]["persistent_up"] else "OTHER",
            )
            trades.append(trade)
        diagnostics.append(
            {
                "fold_id": fold_id,
                "selected_before_occupancy": len(selected[fold_id]),
                "suppressed_by_active_position": suppressed,
                "attempted_while_flat": len(selected[fold_id]) - suppressed,
            }
        )
    return {
        "profile": profile,
        "trades": trades,
        "occupancy_diagnostics": diagnostics,
        "summary": summarize_trades(trades, protocol),
    }


def _preconditions(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    required = {
        "source": root / "reports/validation/WP-005-SOURCE-PROVENANCE.json",
        "features": root / "research/diagnostics/WP-005/feature-result-reconciliation.json",
        "replay": root / "research/diagnostics/WP-005/wp004-integrity-replay.json",
    }
    statuses = {
        name: json.loads(path.read_text(encoding="utf-8"))["status"]
        for name, path in required.items()
    }
    if any(value != "PASS" for value in statuses.values()):
        raise ValueError("integrity prerequisite failed")
    if [random_gate_seed(index) for index in range(32)] != protocol["matched_random_gate"]["seeds"]:
        raise ValueError("frozen seed derivation mismatch")
    protocol_path = "research/protocols/WP-005-MATCHED-CONTROLS-V1.json"
    commits = subprocess.check_output(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", protocol_path],
        cwd=root,
        text=True,
        encoding="utf-8",
    ).splitlines()
    if not commits:
        raise ValueError("matched-control protocol is not committed")
    allocation = json.loads(
        (root / "research/memory/WP-005-DIAGNOSTIC-ALLOCATION.json").read_text(encoding="utf-8")
    )
    if (
        allocation["new_economic_hypotheses"] != 0
        or allocation["new_strategy_variants"] != 0
        or allocation["numeric_parameter_variants"] != 0
        or allocation["diagnostic_evaluations"] != 35
    ):
        raise ValueError("diagnostic allocation changed")
    aligned_prereg = json.loads(
        (root / "research/experiments/EXP-ALG-009-ALIGNED/preregistration.v2.json").read_text(
            encoding="utf-8"
        )
    )
    for dependency in aligned_prereg["parameter_space"]["dependencies"]:
        if normalized_file_hash(root / dependency["path"]) != dependency["sha256"]:
            raise ValueError(f"WP-004 executable/config dependency changed: {dependency['path']}")
    return {
        "source_provenance": "PASS",
        "independent_feature_reconciliation": "PASS",
        "exact_wp004_replay": "PASS",
        "strategy_config_unchanged": True,
        "protocol_first_commit": commits[-1],
        "protocol_sha256": text_sha256(root / protocol_path),
        "all_32_seeds_preserved": True,
        "undeclared_evaluations": 0,
    }


def build_diagnostics(root: Path) -> dict[str, dict[str, Any]]:
    protocol_path = root / "research/protocols/WP-005-MATCHED-CONTROLS-V1.json"
    declaration = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    prerequisites = _preconditions(root, declaration)
    universe, features = _candidate_universe(root)
    aligned_k = {fold: len(value["aligned"]) for fold, value in universe.items()}
    if aligned_k != declaration["matched_random_gate"]["k_by_fold"]:
        raise ValueError("raw ALIGNED K differs from frozen protocol")
    inputs = ResearchInputs.load(root)

    parent_selected = {fold: value["parent"] for fold, value in universe.items()}
    parent_trials = [
        _execute(
            inputs,
            protocol,
            parent_selected,
            features,
            profile,
            f"WP005:MATCHED_PARENT:{profile}",
        )
        for profile in PROFILES
    ]
    parent = {
        "schema_version": 1,
        "diagnostic_id": "WP005-MATCHED-PARENT-BREAKOUT",
        "status": "PASS",
        "kind": "SAME_MECHANISM_DIAGNOSTIC_NOT_STRATEGY_VARIANT",
        "rule": declaration["matched_parent"]["rule"],
        "shared_universe": declaration["shared_universe"],
        "profiles": parent_trials,
        "diagnostic_evaluations": len(parent_trials),
        "new_economic_hypotheses": 0,
        "new_strategy_variants": 0,
        "post_cutoff_bytes_read": False,
    }

    random_evaluations = []
    for index in range(32):
        seed = random_gate_seed(index)
        selected = {
            fold: sorted(
                sorted(value["parent"], key=lambda signal: random_gate_rank(seed, signal))[
                    : len(value["aligned"])
                ]
            )
            for fold, value in universe.items()
        }
        if any(len(selected[fold]) != aligned_k[fold] for fold in selected):
            raise ValueError("random gate did not preserve exact per-fold K")
        execution = _execute(
            inputs,
            protocol,
            selected,
            features,
            "DEFAULT",
            f"WP005:MATCHED_RANDOM_GATE:{index}",
        )
        random_evaluations.append(
            {
                "seed_index": index,
                "seed": seed,
                "selected_timestamps": selected,
                "selected_timestamps_sha256": canonical_hash(selected),
                **execution,
            }
        )
    expectancies = [item["summary"]["metrics"]["net_expectancy_r"] for item in random_evaluations]
    cumulative = [item["summary"]["metrics"]["cumulative_net_r"] for item in random_evaluations]
    trade_counts = [item["summary"]["metrics"]["trade_count"] for item in random_evaluations]
    positive_folds = [
        sum(fold["metrics"]["net_expectancy_r"] > 0 for fold in item["summary"]["folds"])
        for item in random_evaluations
    ]
    random_gate = {
        "schema_version": 1,
        "diagnostic_id": "WP005-MATCHED-RANDOM-GATE",
        "status": "PASS",
        "kind": "CONTROL_DIAGNOSTIC_NOT_FORMAL_INDEPENDENT_P_VALUE",
        "seed_derivation": declaration["matched_random_gate"]["seed_derivation"],
        "rank_rule": declaration["matched_random_gate"]["rank_rule"],
        "rank_timestamp_encoding": declaration["matched_random_gate"]["rank_timestamp_encoding"],
        "quantile_convention": declaration["matched_random_gate"]["quantile_convention"],
        "k_by_fold": aligned_k,
        "evaluations": random_evaluations,
        "distribution": {
            "mean_expectancy_r": round(math.fsum(expectancies) / len(expectancies), 10),
            "median_expectancy_r": quantile_type7(expectancies, 0.5),
            "minimum_expectancy_r": min(expectancies),
            "maximum_expectancy_r": max(expectancies),
            "q10_expectancy_r": quantile_type7(expectancies, 0.1),
            "q90_expectancy_r": quantile_type7(expectancies, 0.9),
            "trade_count": {
                "minimum": min(trade_counts),
                "maximum": max(trade_counts),
                "values": trade_counts,
            },
            "positive_fold_count": {
                "minimum": min(positive_folds),
                "maximum": max(positive_folds),
                "values": positive_folds,
            },
            "cumulative_net_r": {
                "mean": round(math.fsum(cumulative) / len(cumulative), 10),
                "median": quantile_type7(cumulative, 0.5),
                "minimum": min(cumulative),
                "maximum": max(cumulative),
                "q10": quantile_type7(cumulative, 0.1),
                "q90": quantile_type7(cumulative, 0.9),
            },
        },
        "seed_count": len(random_evaluations),
        "selection_policy": "ALL_32_FIXED_SEEDS_NO_SELECTION_OR_REPLACEMENT",
        "new_economic_hypotheses": 0,
        "new_strategy_variants": 0,
        "post_cutoff_bytes_read": False,
    }

    aligned_default = next(
        item
        for item in json.loads(
            (root / "research/experiments/EXP-ALG-009-ALIGNED/trials.json").read_text(
                encoding="utf-8"
            )
        )
        if item["profile"] == "DEFAULT"
    )
    aligned_by_fold = {
        fold["fold_id"]: {
            "trades": [
                trade for trade in aligned_default["trades"] if trade["fold_id"] == fold["fold_id"]
            ]
        }
        for fold in protocol["folds"]
    }
    funnel = []
    monthly: Counter[str] = Counter()
    for fold_id, value in universe.items():
        trades = aligned_by_fold[fold_id]["trades"]
        resolved = sum(trade["status"] == "VALID" for trade in trades)
        invalid = sum(trade["status"] == "INVALID" for trade in trades)
        unresolved = sum(trade["status"] == "UNRESOLVED" for trade in trades)
        emitted = len(trades)
        suppressed = len(value["aligned"]) - emitted
        for signal in value["aligned"]:
            instant = EPOCH + timedelta(microseconds=signal)
            monthly[f"{instant.year:04d}-{instant.month:02d}"] += 1
        funnel.append(
            {
                "fold_id": fold_id,
                "total_hourly_boundaries": value["total"],
                "common_quality_eligible_boundaries": value["eligible"],
                "raw_parent_breakout_candidates": len(value["parent"]),
                "persistent_up_pass_among_breakouts": len(value["persistence"]),
                "participation_pass_among_breakouts": len(value["participation"]),
                "aligned_pass_among_breakouts": len(value["aligned"]),
                "emitted_signals_while_flat": emitted,
                "suppressed_by_active_position": suppressed,
                "invalid_attempts": invalid,
                "unresolved_trades": unresolved,
                "resolved_trades": resolved,
                "persistent_up_coverage_eligible": round(
                    value["persistent_eligible"] / value["eligible"], 10
                ),
                "persistent_up_coverage_breakouts": round(
                    len(value["persistence"]) / len(value["parent"]), 10
                ),
                "participation_coverage_breakouts": round(
                    len(value["participation"]) / len(value["parent"]), 10
                ),
                "aligned_coverage_breakouts": round(
                    len(value["aligned"]) / len(value["parent"]), 10
                ),
                "active_position_suppression_rate": round(suppressed / len(value["aligned"]), 10),
            }
        )

    def total(key: str) -> int:
        return sum(
            len(value[key]) if isinstance(value[key], list) else int(value[key])
            for value in universe.values()
        )

    total_aligned = total("aligned")
    total_parent = total("parent")
    total_eligible = total("eligible")
    total_suppressed = total_aligned - len(aligned_default["trades"])
    coverage = {
        "schema_version": 1,
        "diagnostic_id": "WP005-COVERAGE-FUNNEL",
        "status": "PASS",
        "purpose": "DESCRIBE_SPARSITY_WITHOUT_RULE_OR_THRESHOLD_SEARCH",
        "per_fold": funnel,
        "overall": {
            "total_hourly_boundaries": total("total"),
            "common_quality_eligible_boundaries": total_eligible,
            "raw_parent_breakout_candidates": total_parent,
            "persistent_up_pass_among_breakouts": total("persistence"),
            "participation_pass_among_breakouts": total("participation"),
            "aligned_pass_among_breakouts": total_aligned,
            "emitted_signals_while_flat": len(aligned_default["trades"]),
            "suppressed_by_active_position": total_suppressed,
            "invalid_attempts": sum(
                trade["status"] == "INVALID" for trade in aligned_default["trades"]
            ),
            "unresolved_trades": sum(
                trade["status"] == "UNRESOLVED" for trade in aligned_default["trades"]
            ),
            "resolved_trades": sum(
                trade["status"] == "VALID" for trade in aligned_default["trades"]
            ),
            "persistent_up_coverage_eligible": round(
                total("persistent_eligible") / total_eligible, 10
            ),
            "persistent_up_coverage_breakouts": round(total("persistence") / total_parent, 10),
            "participation_coverage_breakouts": round(total("participation") / total_parent, 10),
            "aligned_coverage_breakouts": round(total_aligned / total_parent, 10),
            "active_position_suppression_rate": round(total_suppressed / total_aligned, 10),
        },
        "monthly_aligned_raw_candidate_distribution": dict(sorted(monthly.items())),
        "threshold_changes": 0,
        "alternate_regime_definitions": 0,
        "outcome_conditioned_search": False,
        "post_cutoff_bytes_read": False,
    }

    parent_expectancy = parent_trials[0]["summary"]["metrics"]["net_expectancy_r"]
    delta = round(ALIGNED_EXPECTANCY - parent_expectancy, 10)
    q90 = random_gate["distribution"]["q90_expectancy_r"]
    parent_pass = delta >= 0.12
    random_pass = ALIGNED_EXPECTANCY > q90
    classification = (
        "ALIGNED_DIAGNOSTIC_SUPPORTED_BUT_INCONCLUSIVE"
        if parent_pass and random_pass
        else "ALIGNED_DIAGNOSTIC_WEAKENED"
    )
    final = {
        "schema_version": 1,
        "diagnostic_id": "WP005-FINAL-COMPARABILITY-CLASSIFICATION",
        "status": "PASS",
        "hard_prerequisites": prerequisites,
        "aligned_default_expectancy_r": ALIGNED_EXPECTANCY,
        "matched_parent_default_expectancy_r": parent_expectancy,
        "delta_parent_r": delta,
        "parent_hurdle_r": 0.12,
        "parent_hurdle_pass": parent_pass,
        "matched_random_gate_q90_expectancy_r": q90,
        "sparse_selection_hurdle_pass": random_pass,
        "classification": classification,
        "underlying_wp004_classification": "INCONCLUSIVE",
        "champion": "NONE",
        "interpretation": "Diagnostic allocation rule on exposed development evidence; not a formal p-value or independent strategy approval.",
        "artifact_content_hashes": {
            "matched_parent": canonical_hash(parent),
            "matched_random_gate": canonical_hash(random_gate),
            "coverage": canonical_hash(coverage),
        },
    }
    return {
        "matched-parent.json": parent,
        "matched-random-gate.json": random_gate,
        "coverage-funnel.json": coverage,
        "final-classification.json": final,
    }
