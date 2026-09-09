"""Deterministic structural validation for the completed WP-006 checkpoint.

No market loading, no strategy rerun. Every claim is reconciled against immutable
artifacts, Git ancestry and the frozen evaluation rule.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from .continuation_lab import DATASET_HASH, DATASET_ID, PROFILES
from .evaluation_protocol import (
    HOUR_US,
    fold_contains,
    load_protocol,
    summarize_trades,
    terminal_classification,
    utc_us,
)
from .records import validate_result
from .report_guard import declared_base, validate_report_bases
from .runner import deterministic_run_identity, sha256
from .sealed_eligibility import build_eligibility_table
from .wp004 import ancestor, first_commit, immutable_from_first_commit
from .wp006 import (
    ADMISSION_PATH,
    ALLOCATION_ID,
    ATTEMPT_PATH,
    BASE,
    HYPOTHESIS_ID,
    LEDGER_PATH,
    OUTCOMES_PATH,
    PRIMARY_VARIANT,
    ROOT,
    ROOT_FAMILY,
    SPEC,
    SPEC_DEPENDENCY_PATHS,
    dependency_manifest,
    effective_preregistration,
    read_json,
    validate_admission,
    validate_allocation,
    validate_identity,
    validate_ledger,
    validate_registry,
)
from .wp006_views import build_wp006_comparison, wp006_accounting_snapshot

COMPARISON_PATH = "reports/research/WP-006-COMPARISON.json"
ELIGIBILITY_PATH = "research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json"
SEALED_BUDGET_PATH = "research/sealed/SEALED_QUERY_BUDGET.json"
FORBIDDEN_YEARS = tuple(str(year) for year in range(2025, 2100))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_trade(trade: dict[str, Any], variant: str, profile: str) -> None:
    """Reconcile the saved recovery decision, barriers, costs and occupancy."""
    record = trade["record"]
    signal = trade["signal_us"]
    require(
        trade["feature_asof_us"] == signal - (HOUR_US if profile == "DELAY_1H" else 0),
        "feature availability/timing mismatch",
    )
    require(utc_us(record["signal_timestamp"]) == signal, "record signal mismatch")
    require(
        record["dataset_content_hash"] == DATASET_HASH
        and record["dataset_manifest_id"] == DATASET_ID,
        "record dataset mismatch",
    )
    require(
        record["run_id"] == f"{variant}:{profile}"
        and record["strategy_reference"] == f"{HYPOTHESIS_ID}:{variant}",
        "record strategy mismatch",
    )
    require(
        record["engine_version"] == "BACKTEST_ENGINE_V2"
        and record["execution_model_version"] == "EXECUTION_MODEL_V2",
        "execution version mismatch",
    )
    reference = Decimal(str(trade["reference"]))
    require(
        Decimal(record["stop"]) == reference * Decimal("0.98")
        and Decimal(record["target"]) == reference * Decimal("1.04"),
        "frozen barriers changed",
    )
    require(record["target_exit_rule"] == "FIXED_TARGET_OR_STOP_OR_24H", "exit rule changed")
    features = trade["feature_values"]
    require(
        set(features)
        == {
            "sma24",
            "sma24_previous",
            "previous_close",
            "previous_high",
            "exceeds_previous_high",
        },
        "an undeclared feature was recorded with a trade",
    )
    require(trade["regime"] == "PERSISTENT_UP", "the 4h persistence gate was not enforced")
    require(
        features["previous_close"] <= features["sma24_previous"],
        "the pullback precondition was not enforced",
    )
    if profile != "DELAY_1H":
        # Undelayed profiles decide on the recorded reference close, so the recovery
        # transition is fully checkable here. The delayed profile decides on the
        # previous clock's close, which the trade record does not carry; its pullback
        # precondition and persistence gate above are still verified.
        require(float(reference) > features["sma24"], "the recovery condition was not enforced")
    if variant == "RECOVERY_CONFIRM":
        require(features["exceeds_previous_high"], "the confirmation gate was not enforced")
    if trade["status"] != "VALID":
        require(
            all(record[key] is None for key in ("gross_pnl", "net_pnl", "gross_r", "net_r")),
            "unresolved/invalid P&L fabricated",
        )
        expected = signal + 24 * HOUR_US if trade["status"] == "UNRESOLVED" else signal
        require(trade["position_available_us"] == expected, "unresolved occupancy mismatch")
        return
    require(
        utc_us(record["entry_timestamp"]) == signal
        and utc_us(record["expiry_timestamp"]) == signal + 24 * HOUR_US,
        "next-open/horizon mismatch",
    )
    exit_us = utc_us(record["exit_timestamp"])
    require(
        exit_us == trade["exit_us"] and signal <= exit_us <= signal + 24 * HOUR_US,
        "exit timing mismatch",
    )
    available = exit_us if trade["reason"] == "EXPIRY" else exit_us + 60_000_000
    require(trade["position_available_us"] == available, "intrabar exit used before availability")
    scale = 0 if profile == "ZERO" else 2 if profile == "DOUBLE" else 1
    expected_cost = "BTCUSDT_SPOT_COST_V1" + (f"_{profile}" if scale != 1 else "")
    require(record["cost_model_version"] == expected_cost, "cost version mismatch")
    entry, exit_price, stop = (
        Decimal(record[key]) for key in ("entry_raw_price", "exit_raw_price", "stop")
    )
    require(0 < stop < entry < Decimal(record["target"]), "non-tradable entry marked valid")
    entry_effective = entry * (Decimal(10000) + 2 * scale) / 10000
    exit_effective = exit_price * (Decimal(10000) - 2 * scale) / 10000
    entry_fee, exit_fee = entry_effective * 10 * scale / 10000, exit_effective * 10 * scale / 10000
    gross, risk = exit_price - entry, entry - stop
    net = exit_effective - entry_effective - entry_fee - exit_fee
    require(
        Decimal(record["net_pnl"]) == net and Decimal(record["gross_pnl"]) == gross,
        "Decimal cost/P&L reconciliation failed",
    )
    require(
        trade["net_r"] == float(net / risk) and trade["gross_r"] == float(gross / risk),
        "numeric R projection mismatch",
    )


def validate_trial(
    trial: dict[str, Any], variant: str, profile: str, protocol: dict[str, Any]
) -> None:
    require(
        trial["status"] == "COMPLETED"
        and trial["variant"] == variant
        and trial["profile"] == profile
        and trial["trial_id"] == f"{variant}:{profile}",
        "undeclared/failed profile",
    )
    require(
        trial["summary"] == summarize_trades(trial["trades"], protocol),
        "summary differs from immutable trade evidence",
    )
    require(
        trial["summary"]["excluded_outside_validation_attempt_count"] == 0,
        "strategy executed outside frozen validation",
    )
    require(len(trial["clock_diagnostics"]) == 6, "fold budget mismatch")
    counts = Counter(item["fold_id"] for item in trial["trades"])
    for fold, clocks in zip(protocol["folds"], trial["clock_diagnostics"], strict=True):
        require(clocks["fold_id"] == fold["fold_id"], "fold identity mismatch")
        expected = (
            utc_us(fold["last_signal_inclusive"]) - utc_us(fold["validation_start"])
        ) // HOUR_US + 1
        require(
            clocks["eligible_clocks"] + clocks["ineligible_clocks"] == expected,
            "signal clock accounting mismatch",
        )
        require(
            0
            <= clocks["suppressed_conditions"]
            <= clocks["conditions_emitted"]
            <= clocks["eligible_clocks"],
            "invalid condition accounting",
        )
        require(
            counts[fold["fold_id"]]
            == clocks["conditions_emitted"] - clocks["suppressed_conditions"],
            "attempt accounting mismatch",
        )
        available = -1
        for trade in (t for t in trial["trades"] if t["fold_id"] == fold["fold_id"]):
            require(
                fold_contains(fold, trade["signal_us"]) and trade["signal_us"] >= available,
                "overlap or fold mismatch",
            )
            validate_trade(trade, variant, profile)
            available = trade["position_available_us"]


def validate_sealed_state(root: Path) -> dict[str, Any]:
    """No reserved data, no authorized query, no consumed query, no eligible candidate."""
    budget = read_json(root / SEALED_BUDGET_PATH)
    scope = budget["scopes"]["BTCUSDT_POST_CUTOFF"]
    require(
        scope["authorized_queries"] == 0
        and scope["consumed_queries"] == 0
        and scope["status"] == "LOCKED_NO_AUTHORIZED_QUERY"
        and scope["authorization_record"] is None
        and scope["dataset_state"] == "RESERVED_NOT_ACQUIRED",
        "the BTC sealed scope is not locked at zero",
    )
    ledger = root / scope["consumption_ledger"]
    require(ledger.is_file() and not ledger.read_text(encoding="utf-8").strip(), "sealed ledger")
    results = root / scope["result_directory"]
    require(
        not [item for item in results.glob("*.json")],
        "a sealed result exists although no query was authorized",
    )
    require(not (root / "data/sealed").exists(), "a reserved sealed dataset was materialized")
    for directory in ("data/raw", "data/canonical", "data/derived"):
        for path in (root / directory).rglob("*"):
            require(
                path.is_dir() or not any(f"-{year}-" in path.name for year in FORBIDDEN_YEARS),
                f"a post-cutoff market file exists: {path.name}",
            )
    table = read_json(root / ELIGIBILITY_PATH)
    require(table == build_eligibility_table(root), "eligibility table is not reproducible")
    require(table["sealed_queries_executed"] == 0, "a sealed query was executed")
    rows = {item["experiment_id"]: item for item in table["candidates"]}
    require(
        rows["EXP-ALG-009-ALIGNED"]["sealed_eligibility"] == "NOT_ELIGIBLE_INCONCLUSIVE",
        "ALIGNED is not correctly recorded as ineligible",
    )
    eligible = [
        item
        for item in table["candidates"]
        if item["sealed_eligibility"].startswith("DEVELOPMENT_ELIGIBLE")
    ]
    require(all(item["sealed_allocation"] is None for item in table["candidates"]), "allocation")
    return {"candidates": len(rows), "seal_eligible": len(eligible)}


def validate_wp006(root: Path = ROOT) -> dict[str, Any]:
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=root, text=True, encoding="utf-8"
    ).strip()
    require(
        branch == "main" or (not branch and os.environ.get("CLEAN_CHECKOUT") == "1"), "not main"
    )
    require(ancestor(BASE, "HEAD", root), "required WP-006 starting HEAD missing")
    require(declared_base("WP-006", root) == BASE, "declared WP-006 base differs from the module")
    guard = validate_report_bases(root, repo=root)

    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    allocation = validate_allocation(root)
    validate_registry(root)
    admission = validate_admission(root)
    counts = validate_ledger(root)
    require(
        counts
        == {
            "experiments": 2,
            "strategy_variants": 2,
            "trials": 8,
            "numeric_parameter_variants": 0,
            "material_economic_hypotheses": 1,
            "strategy_descendants": 1,
        },
        "WP-006 admission accounting differs from the allocation",
    )

    admission_commit = immutable_from_first_commit(ADMISSION_PATH, root)
    for dependency in SPEC_DEPENDENCY_PATHS:
        commit = first_commit(dependency, root)
        require(
            commit != admission_commit and ancestor(commit, admission_commit, root),
            "executable behaviour was not committed before admission",
        )
    for path in (
        ADMISSION_PATH,
        LEDGER_PATH,
        "research/memory/WP006-PULLBACK-RECOVERY-ALLOCATION.json",
        "research/memory/FAMILY_REGISTRY_V2.json",
        "research/memory/SEARCH_BUDGET_V2.json",
        "research/protocols/WP-006-PREEXECUTION-AMENDMENTS.json",
        "research/design/PULLBACK_RECOVERY_V1_DESIGN.md",
        COMPARISON_PATH,
    ):
        immutable_from_first_commit(path, root)

    attempt = read_json(root / ATTEMPT_PATH)
    require(
        attempt["status"] == "PASS"
        and attempt["family_classification"] == "NEW_FAMILY"
        and attempt["admission_commit"] == admission_commit
        and attempt["root_family"] == ROOT_FAMILY,
        "execution admission mismatch",
    )
    expected_ids = [f"{variant}:{profile}" for variant in SPEC.values() for profile in PROFILES]
    require(attempt["trial_ids"] == expected_ids, "undeclared or repeated strategy trials")
    require(
        attempt["dependency_manifest_sha256"]
        == hashlib.sha256(
            json.dumps(dependency_manifest(root), sort_keys=True).encode()
        ).hexdigest(),
        "execution closure mismatch",
    )

    classifications: dict[str, str] = {}
    result_commits: set[str] = set()
    for experiment_id, variant in SPEC.items():
        directory = root / "research/experiments" / experiment_id
        require(
            {path.name for path in directory.iterdir()}
            == {"preregistration.json", "preregistration.v2.json", "trials.json", "result.json"},
            "undeclared experiment artifact",
        )
        original = f"research/experiments/{experiment_id}/preregistration.json"
        original_commit = immutable_from_first_commit(original, root)
        effective = effective_preregistration(experiment_id, root)
        prereg = read_json(effective)
        validate_identity(prereg, root)
        require(prereg["experiment_version"] == 2, "effective preregistration version mismatch")
        pre_commit = immutable_from_first_commit(effective.relative_to(root).as_posix(), root)
        ordered = [admission_commit, original_commit, pre_commit]
        require(
            len(set(ordered)) == len(ordered)
            and all(ancestor(a, b, root) for a, b in zip(ordered, ordered[1:], strict=False)),
            "scientific freeze chronology changed",
        )
        require(
            attempt["preregistration_hashes"][experiment_id] == sha256(effective),
            "effective preregistration hash mismatch",
        )
        require(
            utc_us(prereg["created_at_utc"]) <= utc_us(attempt["started_at_utc"]),
            "execution timestamp predates preregistration",
        )
        result = validate_result(directory / "result.json", effective)
        require(
            utc_us(attempt["started_at_utc"]) <= utc_us(result["completed_at_utc"]),
            "result predates attempt",
        )
        trials = read_json(directory / "trials.json")
        require(len(trials) == 4, "exact four-profile budget exceeded")
        for trial, profile in zip(trials, PROFILES, strict=True):
            validate_trial(trial, variant, profile, protocol)
        summaries = {trial["profile"]: trial["summary"] for trial in trials}
        secondary = result["secondary_results"]
        require(
            secondary["profiles"] == summaries
            and result["primary_result"] == summaries["DEFAULT"]["metrics"]["net_expectancy_r"],
            "result summary linkage mismatch",
        )
        classification = terminal_classification(
            summaries["DEFAULT"], summaries["ZERO"], summaries["DOUBLE"], protocol
        )
        require(
            secondary["terminal_classification"] == classification,
            "terminal classification differs from the frozen rule",
        )
        require(
            result["run_identity_hash"]
            == deterministic_run_identity(
                prereg,
                attempt["execution_commit"],
                {"reference": prereg["code_config_reference"]},
                {
                    "engine": "BACKTEST_ENGINE_V2",
                    "execution": "EXECUTION_MODEL_V2",
                    "cost": "BTCUSDT_SPOT_COST_V1",
                },
            ),
            "deterministic run identity mismatch",
        )
        classifications[variant] = classification
        for name in ("result.json", "trials.json"):
            commit = immutable_from_first_commit(
                (directory / name).relative_to(root).as_posix(), root
            )
            require(
                commit != pre_commit and ancestor(pre_commit, commit, root),
                "result commit did not follow preregistration",
            )
            result_commits.add(commit)
    result_commits.add(immutable_from_first_commit(ATTEMPT_PATH, root))
    require(len(result_commits) == 1, "WP-006 result evidence was not committed together")
    outcomes = [
        json.loads(line)
        for line in (root / OUTCOMES_PATH).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    require(
        [item["experiment_id"] for item in outcomes] == list(SPEC),
        "V2 outcomes do not match the admitted experiments",
    )
    for outcome in outcomes:
        result_path = root / outcome["result_path"]
        require(sha256(result_path) == outcome["result_sha256"], "outcome result hash mismatch")
        require(
            outcome["terminal_classification"]
            == read_json(result_path)["secondary_results"]["terminal_classification"],
            "outcome classification differs from its immutable result",
        )

    require(
        read_json(root / COMPARISON_PATH) == json.loads(json.dumps(build_wp006_comparison(root))),
        "WP-006 comparison is not reproducible from immutable evidence",
    )
    lessons = read_json(root / "research/memory/WP-006-LESSONS.json")
    require(
        lessons["family_terminal_classification"] == classifications[PRIMARY_VARIANT],
        "the family conclusion does not follow the preselected primary variant",
    )
    require(lessons["new_trial_allocation"] == 0, "the lessons record allocates new trials")

    sealed = validate_sealed_state(root)
    state = read_json(root / "state/current_state.json")
    wp006_accounting = wp006_accounting_snapshot(root)
    require(
        all(
            state["adaptive_search"].get(key, -1) >= value
            for key, value in wp006_accounting.items()
        ),
        "current state understates the deterministic WP-006 accounting snapshot",
    )
    require(
        state["experiments_completed"] >= 11
        and state["sealed_evaluations_completed"] == 0
        and state["paper_trades_completed"] == 0
        and state["champion_status"] == "NONE"
        and state["forward_evidence"] == "NONE"
        and not state["real_money_authorized"],
        "WP-006 state counters are not truthful",
    )
    require(
        state["latest_family"]["terminal_classification"] == classifications[PRIMARY_VARIANT]
        and state["latest_family"]["novelty_classification"] == "NEW_FAMILY"
        and state["selected_family"]["name"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
        and state["selected_family"]["terminal_classification"] == "INCONCLUSIVE",
        "state family identity changed",
    )
    require(
        state["sealed_evaluation"]["authorized_btc_queries"] == 0
        and state["sealed_evaluation"]["consumed_btc_queries"] == 0
        and state["sealed_evaluation"]["seal_eligible_candidates"] == sealed["seal_eligible"],
        "state sealed counters are not truthful",
    )
    return {
        "status": "PASS",
        "root_family": ROOT_FAMILY,
        "allocation_id": ALLOCATION_ID,
        "novelty_classification": admission["family_classification"],
        "variants": len(SPEC),
        "profile_trials": counts["trials"],
        "numeric_parameter_variants": 0,
        "classifications": classifications,
        "family_terminal_classification": classifications[PRIMARY_VARIANT],
        "sealed": sealed,
        "report_base_guard": guard["base_guard_enforced"],
        "cumulative": wp006_accounting,
        "allocation_cumulative_forks": allocation["cumulative_result_dependent_forks"],
    }
