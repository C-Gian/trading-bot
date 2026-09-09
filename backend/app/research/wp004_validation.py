"""Post-execution audit of frozen evidence. No market loading or strategy reruns."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from .adaptive import validate_adaptive
from .continuation_lab import DATASET_HASH, DATASET_ID, MANIFEST_SHA256, PROFILES
from .evaluation_protocol import (
    HOUR_US,
    fold_contains,
    load_protocol,
    summarize_trades,
    terminal_classification,
    utc_us,
)
from .records import validate_result
from .runner import deterministic_run_identity, sha256
from .search_memory import load_memory, validate_memory
from .wp004 import (
    BASE,
    DESIGN_COMMIT,
    PROTOCOL_COMMIT,
    ROOT,
    SPEC,
    ancestor,
    dependency_manifest,
    effective_preregistration,
    git,
    immutable_from_first_commit,
    validate_historical_identity,
    validate_identity,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def historical_bytes(commit: str, path: str, root: Path = ROOT) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=root).replace(
        b"\r\n", b"\n"
    )


def validate_trade(trade: dict[str, Any], variant: str, profile: str) -> None:
    """Reconcile saved Decimal accounting and temporal/intent metadata, not fills."""
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
        and record["strategy_reference"] == f"ALIGNED_PARTICIPATION_CONTINUATION_V1:{variant}",
        "record strategy mismatch",
    )
    require(
        record["engine_version"] == "BACKTEST_ENGINE_V2"
        and record["execution_model_version"] == "EXECUTION_MODEL_V2",
        "execution version mismatch",
    )
    require(
        record["data_quality_status"] == trade["status"]
        and record["exit_reason"] == trade["reason"],
        "record status mismatch",
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
        -1 <= features["signed_efficiency"] <= 1 and features["relative_volume"] >= 0,
        "invalid saved feature",
    )
    if variant in {"REGIME_ONLY", "ALIGNED"}:
        require(
            trade["regime"] == "PERSISTENT_UP" and features["signed_efficiency"] >= 1 / 3 - 1e-12,
            "regime gate mismatch",
        )
    if variant in {"PARTICIPATION_ONLY", "ALIGNED"}:
        require(features["relative_volume"] >= 2, "participation gate mismatch")
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
    require(
        record["holding_minutes"] == (exit_us - signal) // 60_000_000, "holding period mismatch"
    )
    available = exit_us if trade["reason"] == "EXPIRY" else exit_us + 60_000_000
    require(trade["position_available_us"] == available, "intrabar exit used before availability")
    if trade["reason"] == "EXPIRY":
        require(exit_us == signal + 24 * HOUR_US, "early expiry")
    scale = 0 if profile == "ZERO" else 2 if profile == "DOUBLE" else 1
    expected_cost = "BTCUSDT_SPOT_COST_V1" + (f"_{profile}" if scale != 1 else "")
    require(record["cost_model_version"] == expected_cost, "cost version mismatch")
    entry, exit_price, stop = (
        Decimal(record[key]) for key in ("entry_raw_price", "exit_raw_price", "stop")
    )
    require(0 < stop < entry < Decimal(record["target"]), "non-tradable entry marked valid")
    if trade["reason"] == "STOP":
        require(exit_price == stop, "stop fill mismatch")
    elif trade["reason"] == "STOP_GAP":
        require(exit_price < stop, "gap stop mismatch")
    elif trade["reason"] == "TARGET":
        require(exit_price == Decimal(record["target"]), "target fill mismatch")
    else:
        require(trade["reason"] == "EXPIRY", "unknown valid exit")
    entry_effective = entry * (Decimal(10000) + 2 * scale) / 10000
    exit_effective = exit_price * (Decimal(10000) - 2 * scale) / 10000
    entry_fee, exit_fee = entry_effective * 10 * scale / 10000, exit_effective * 10 * scale / 10000
    gross, risk = exit_price - entry, entry - stop
    net = exit_effective - entry_effective - entry_fee - exit_fee
    expected = {
        "entry_effective_price": entry_effective,
        "exit_effective_price": exit_effective,
        "entry_fee": entry_fee,
        "exit_fee": exit_fee,
        "entry_execution_friction": entry_effective - entry,
        "exit_execution_friction": exit_price - exit_effective,
        "gross_pnl": gross,
        "net_pnl": net,
        "initial_price_risk": risk,
        "gross_r": gross / risk,
        "net_r": net / risk,
    }
    require(
        all(Decimal(record[key]) == value for key, value in expected.items()),
        "Decimal cost/P&L reconciliation failed",
    )
    require(
        trade["net_r"] == float(net / risk) and trade["gross_r"] == float(gross / risk),
        "numeric R projection mismatch",
    )
    require(
        trade["net_return_bps"] == float(net / entry * 10000)
        and trade["cost_drag_r"] == float(gross / risk - net / risk),
        "economic scale/cost projection mismatch",
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
    counts = Counter(t["fold_id"] for t in trial["trades"])
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


def validate_checkpoint(
    root: Path = ROOT, *, require_committed_results: bool = True
) -> dict[str, Any]:
    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    for commit in (BASE, DESIGN_COMMIT, PROTOCOL_COMMIT):
        require(ancestor(commit, "HEAD", root), "starting/design/protocol ancestry missing")
    count, adaptive = validate_memory(root), validate_adaptive(root)
    require(
        count["global"]
        == {"experiments": 9, "strategy_variants": 9, "trials": 53, "numeric_parameter_variants": 0}
        and count["completed_experiments"] == 9,
        "cumulative search accounting mismatch",
    )
    require(
        adaptive["adaptive_decisions"] == adaptive["result_dependent_forks"] == 1
        and adaptive["wp004_variants_reserved"] == 3
        and adaptive["wp004_profiles_reserved"] == 12,
        "adaptive/family budget mismatch",
    )
    manifest_path = root / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
    manifest = read_json(manifest_path)
    require(
        sha256(manifest_path) == MANIFEST_SHA256
        and manifest["content_hash"]["value"] == DATASET_HASH
        and manifest["symbol"] == "BTCUSDT",
        "dataset identity mismatch",
    )
    require(
        manifest["coverage"]["end"] == protocol["development_cutoff"], "dataset cutoff mismatch"
    )
    registry_path = "research/protocols/WP-004-PREEXECUTION-AMENDMENTS.json"
    registry = read_json(root / registry_path)
    registry_commit = immutable_from_first_commit(registry_path, root)
    require(
        registry["strategy_trials_before_amendment"]
        == registry["additional_profile_trials"]
        == registry["additional_strategy_variants"]
        == 0,
        "amendment attempted to erase trials",
    )
    require(
        sha256(root / registry["abort_record"]) == registry["abort_record_sha256"],
        "abort evidence changed",
    )
    for path in (
        "research/memory/SEARCH_BUDGET.json",
        "research/memory/HYPOTHESIS_FAMILIES.json",
        "research/memory/ADAPTIVE_DECISIONS.json",
        "research/design/ALGORITHM_FAMILY_V1_DESIGN.md",
        "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json",
        registry["abort_record"],
    ):
        immutable_from_first_commit(path, root)
    memory = load_memory(root)
    for entry in memory["entries"]:
        if entry["work_package"] == "WP-003":
            for filename in ("preregistration.json", "trials.json", "result.json"):
                path = f"research/experiments/{entry['experiment_id']}/{filename}"
                require(
                    historical_bytes(BASE, path, root)
                    == (root / path).read_bytes().replace(b"\r\n", b"\n"),
                    "WP-003 negative/history evidence changed",
                )
    for filename in ("SEARCH_LEDGER.jsonl", "OUTCOMES.jsonl"):
        path = f"research/memory/{filename}"
        require(
            (root / path)
            .read_bytes()
            .replace(b"\r\n", b"\n")
            .startswith(historical_bytes("fcd3e8f", path, root)),
            "retrospective memory prefix changed",
        )
    ledger = "research/memory/SEARCH_LEDGER.jsonl"
    require(
        historical_bytes("4023928", ledger, root)
        == (root / ledger).read_bytes().replace(b"\r\n", b"\n"),
        "admissions changed after observation",
    )
    attempt_path = "research/runs/WP-004-ATTEMPT.json"
    attempt = read_json(root / attempt_path)
    require(
        set((root / "research/runs").iterdir()) == {root / attempt_path},
        "undeclared execution attempt",
    )
    require(
        attempt["status"] == "PASS" and attempt["adaptive_accounting"] == adaptive,
        "execution admission mismatch",
    )
    expected_ids = [f"{variant}:{profile}" for variant, _ in SPEC.values() for profile in PROFILES]
    require(attempt["trial_ids"] == expected_ids, "undeclared/repeated strategy trials")
    require(
        attempt["preregistration_commit"] == registry_commit
        and ancestor(registry_commit, attempt["execution_commit"], root),
        "effective preregistration did not precede execution",
    )
    require(
        attempt["dependency_manifest_sha256"]
        == hashlib.sha256(
            json.dumps(dependency_manifest(root), sort_keys=True).encode()
        ).hexdigest(),
        "execution closure mismatch",
    )
    classifications = {}
    results_commits = set()
    for eid, (variant, _) in SPEC.items():
        directory = root / "research/experiments" / eid
        require(
            {p.name for p in directory.iterdir()}
            == {"preregistration.json", "preregistration.v2.json", "trials.json", "result.json"},
            "undeclared experiment artifact",
        )
        old_path = f"research/experiments/{eid}/preregistration.json"
        old_commit = immutable_from_first_commit(old_path, root)
        original = read_json(root / old_path)
        validate_historical_identity(original, root)
        pre_path = effective_preregistration(eid, root)
        pre = read_json(pre_path)
        validate_identity(pre, root)
        validate_historical_identity(pre, root)
        pre_commit = immutable_from_first_commit(pre_path.relative_to(root).as_posix(), root)
        implementation = pre["parameter_space"]["implementation_commit"]
        ordered = [
            git("rev-parse", DESIGN_COMMIT, root=root),
            original["parameter_space"]["implementation_commit"],
            old_commit,
            implementation,
            pre_commit,
        ]
        require(
            len(set(ordered)) == len(ordered)
            and all(ancestor(a, b, root) for a, b in zip(ordered, ordered[1:])),
            "scientific freeze chronology changed",
        )
        require(
            pre_commit == registry_commit
            and pre["experiment_version"] == 2
            and attempt["preregistration_hashes"][eid] == sha256(pre_path),
            "effective preregistration version/hash mismatch",
        )
        require(
            utc_us(pre["created_at_utc"]) <= utc_us(attempt["started_at_utc"]),
            "execution timestamp predates preregistration",
        )
        result = validate_result(directory / "result.json", pre_path)
        require(
            utc_us(attempt["started_at_utc"]) <= utc_us(result["completed_at_utc"]),
            "result predates attempt",
        )
        trials = read_json(directory / "trials.json")
        require(len(trials) == 4, "exact max-three/four-profile budget exceeded")
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
            "terminal classification differs from frozen rule",
        )
        gate = {
            key: value
            for key, value in attempt.items()
            if key not in {"started_at_utc", "trial_ids"}
        }
        require(
            secondary["execution_provenance"]
            == {
                **gate,
                "trial_artifact_sha256": sha256(directory / "trials.json"),
                "feature_version": "CONTINUATION_FEATURES_V2",
                "fold_executions": 24,
                "trial_count": 4,
                "structural_variants": 1,
            },
            "result provenance mismatch",
        )
        require(
            result["run_identity_hash"]
            == deterministic_run_identity(
                pre,
                attempt["execution_commit"],
                {"reference": pre["code_config_reference"]},
                {
                    "engine": "BACKTEST_ENGINE_V2",
                    "execution": "EXECUTION_MODEL_V2",
                    "cost": "BTCUSDT_SPOT_COST_V1",
                },
            ),
            "deterministic run identity mismatch",
        )
        classifications[variant] = classification
        if require_committed_results:
            for name in ("result.json", "trials.json"):
                commit = immutable_from_first_commit(
                    (directory / name).relative_to(root).as_posix(), root
                )
                require(
                    commit != pre_commit and ancestor(pre_commit, commit, root),
                    "result commit did not follow preregistration",
                )
                results_commits.add(commit)
    if require_committed_results:
        results_commits.add(immutable_from_first_commit(attempt_path, root))
        require(len(results_commits) == 1, "WP-004 result evidence was not committed together")
    return {
        "status": "PASS",
        "experiments": 9,
        "wp004_structural_variants": 3,
        "wp004_profile_trials": 12,
        "wp004_fold_components": 72,
        "cumulative_profile_trials": 53,
        "classifications": classifications,
        "selected_family_terminal_classification": classifications["ALIGNED"],
    }
