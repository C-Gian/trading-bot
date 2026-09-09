"""Deterministic structural validation for the completed WP-005 checkpoint."""

from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

import jsonschema

from .evaluation_protocol import load_protocol, summarize_trades
from .search_memory import accounting, load_memory, text_sha256
from .search_memory_v2 import validate_search_memory_v2
from .wp004 import ROOT, ancestor, immutable_from_first_commit
from .wp005_diagnostics import (
    ALIGNED_EXPECTANCY,
    _candidate_universe,
    quantile_type7,
    random_gate_rank,
    random_gate_seed,
)
from .wp005_integrity import (
    canonical_hash,
    feature_and_result_reconciliation,
    source_provenance,
)

WP005_BASE = "3fdeffe5de59ebf3d80dcb70e26fe8dff8a28153"
WP004_REVIEWED = "2b40aa03cfc05ac7f57d269f596f1ebacdc9d356"
DIAGNOSTIC_DIR = Path("research/diagnostics/WP-005")
# The nine strategy experiments that existed at the WP-005 checkpoint. Later work
# packages may add experiments; none of these may ever disappear or be renamed.
WP005_EXPERIMENTS = frozenset(
    {
        "EXP-BASE-001-BUYHOLD",
        "EXP-CTRL-002-RANDOM",
        "EXP-BASE-003-TREND",
        "EXP-BASE-004-BREAKOUT",
        "EXP-CTRL-005-TREND-DELAY-1H",
        "EXP-CTRL-006-NO-TRADE",
        "EXP-ALG-007-REGIME",
        "EXP-ALG-008-PARTICIPATION",
        "EXP-ALG-009-ALIGNED",
    }
)


def _read(root: Path, relative: str | Path) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _first_commit(root: Path, relative: str) -> str:
    commits = subprocess.check_output(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", relative],
        cwd=root,
        text=True,
        encoding="utf-8",
    ).splitlines()
    if not commits:
        raise ValueError(f"uncommitted scientific artifact: {relative}")
    return commits[-1]


def validate_wp005(root: Path = ROOT, *, data_available: bool = False) -> dict[str, Any]:
    _require(ancestor(WP005_BASE, "HEAD", root), "required WP-005 starting HEAD missing")
    _require(ancestor(WP004_REVIEWED, WP005_BASE, root), "reviewed predecessor ancestry missing")
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=root, text=True, encoding="utf-8"
    ).strip()
    _require(
        branch == "main" or (not branch and os.environ.get("CLEAN_CHECKOUT") == "1"), "not main"
    )

    source = _read(root, "reports/validation/WP-005-SOURCE-PROVENANCE.json")
    _require(
        source["status"] == "PASS"
        and source["classification"] == "SOURCE_ARCHIVE_OFF_GRID_CONFIRMED"
        and source["off_grid_rows"] == source["raw_anomaly_rows"] == 21602
        and source["raw_to_canonical_timestamp_mismatches"] == 0
        and source["raw_to_canonical_payload_mismatches"] == {}
        and source["quarantine"]["quarantined_1h_buckets"] == 363
        and source["quarantine"]["quarantined_4h_buckets"] == 92
        and source["quarantine"]["repairs_or_fills"] == 0
        and source["validation_required_bucket_intersections"] == {"1h": 0, "4h": 0}
        and not source["post_cutoff_bytes_read"],
        "source provenance gate failed",
    )
    expected_archives = {
        "3d41da2da488a69a21e9223221863c3a8ed6ccb9263d30cf1d3a012a48cfffc1",
        "131667f0d4ff73685852d84a406e07f8a3fdf7037798b1bdb0519e7e987e19ad",
    }
    _require(
        {item["observed_sha256"] for item in source["archives"]} == expected_archives
        and all(item["accepted_sha256"] == item["observed_sha256"] for item in source["archives"]),
        "raw archive provenance changed",
    )

    reconciliation = _read(root, DIAGNOSTIC_DIR / "feature-result-reconciliation.json")
    _require(
        reconciliation["status"] == "PASS"
        and reconciliation["feature_mismatches"] == 0
        and reconciliation[
            "resolved_count_cumulative_net_expectancy_profit_factor_drawdown_cost_drag"
        ]
        == "EXACT_MATCH"
        and reconciliation["fold_metrics"] == "EXACT_MATCH"
        and all(
            item["status"] == "EXACT_MATCH"
            for item in reconciliation["candidate_reconciliation"].values()
        ),
        "independent reconciliation gate failed",
    )
    _require(
        reconciliation["candidate_reconciliation"]["ALIGNED"]["per_fold"]
        == {
            "DEV-2019": 45,
            "DEV-2020": 40,
            "DEV-2021": 15,
            "DEV-2022": 7,
            "DEV-2023": 45,
            "DEV-2024": 43,
        },
        "ALIGNED candidate identity changed",
    )

    replay = _read(root, DIAGNOSTIC_DIR / "wp004-integrity-replay.json")
    _require(
        replay["status"] == "PASS"
        and replay["profiles_replayed"] == 12
        and replay["fold_components_replayed"] == 72
        and replay["new_experiment_result_ids"] == 0
        and all(
            item["status"] == "EXACT_MATCH"
            and item["canonical_content_sha256"] == item["finalized_canonical_content_sha256"]
            for item in replay["trials"]
        ),
        "WP-004 replay did not reconcile exactly",
    )

    search = validate_search_memory_v2(root)
    signatures = _read(root, "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json")
    schema = _read(root, "contracts/executable_strategy_spec_v2.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    for item in signatures["signatures"]:
        validator.validate(item["spec"])
    _require(search["breakout_strategy_budget"] == "EXHAUSTED", "breakout budget reopened")

    memory = load_memory(root)
    counts = accounting(memory)
    _require(
        counts["global"]
        == {"experiments": 9, "strategy_variants": 9, "trials": 53, "numeric_parameter_variants": 0}
        and counts["families"]["FAM-BREAKOUT"] == memory["budget"]["family_limits"]["FAM-BREAKOUT"],
        "strategy search accounting changed",
    )

    allocation = _read(root, "research/memory/WP-005-DIAGNOSTIC-ALLOCATION.json")
    _require(
        allocation["allocation_id"] == "WP005-INTEGRITY-COMPARABILITY-ALLOCATION"
        and allocation["new_economic_hypotheses"] == 0
        and allocation["new_strategy_variants"] == 0
        and allocation["numeric_parameter_variants"] == 0
        and allocation["integrity_replay"]["wp004_profiles"] == 12
        and allocation["matched_parent_control"]["diagnostic_evaluations"] == 3
        and allocation["matched_random_gate_control"]["diagnostic_evaluations"] == 32
        and allocation["diagnostic_evaluations"] == 35,
        "diagnostic allocation changed",
    )
    adaptive = _read(root, "research/memory/ADAPTIVE_DIAGNOSTICS_V2.json")
    _require(
        adaptive["cumulative_adaptive_decisions"] == 2
        and adaptive["cumulative_result_dependent_forks"] == 2
        and adaptive["diagnostic_decisions"][0]["unique_diagnostic_evaluations"] == 35,
        "adaptive diagnostic burden changed",
    )

    declaration_path = "research/protocols/WP-005-MATCHED-CONTROLS-V1.json"
    declaration = _read(root, declaration_path)
    seeds = [random_gate_seed(index) for index in range(32)]
    _require(
        declaration["matched_parent"]["profiles"] == ["DEFAULT", "ZERO", "DOUBLE"]
        and declaration["matched_parent"]["rule"]
        == "current completed 1h close > max(previous 24 completed 1h highs)"
        and declaration["matched_random_gate"]["seed_indices"] == list(range(32))
        and declaration["matched_random_gate"]["seeds"] == seeds
        and declaration["matched_random_gate"]["seed_count"] == 32
        and declaration["coverage"]["threshold_searches"] == 0,
        "matched-control declaration changed",
    )
    protocol_commit = _first_commit(root, declaration_path)

    parent_path = (DIAGNOSTIC_DIR / "matched-parent.json").as_posix()
    random_path = (DIAGNOSTIC_DIR / "matched-random-gate.json").as_posix()
    coverage_path = (DIAGNOSTIC_DIR / "coverage-funnel.json").as_posix()
    final_path = (DIAGNOSTIC_DIR / "final-classification.json").as_posix()
    for path in (parent_path, random_path, coverage_path, final_path):
        result_commit = _first_commit(root, path)
        _require(
            result_commit != protocol_commit and ancestor(protocol_commit, result_commit, root),
            "matched-control result predates protocol",
        )
        immutable_from_first_commit(path, root)

    development_protocol = load_protocol(
        root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json"
    )
    parent = _read(root, parent_path)
    _require(
        parent["status"] == "PASS"
        and parent["rule"] == declaration["matched_parent"]["rule"]
        and parent["shared_universe"] == declaration["shared_universe"]
        and [item["profile"] for item in parent["profiles"]] == ["DEFAULT", "ZERO", "DOUBLE"]
        and parent["diagnostic_evaluations"] == 3
        and parent["new_economic_hypotheses"] == parent["new_strategy_variants"] == 0,
        "matched parent identity changed",
    )
    for trial in parent["profiles"]:
        _require(
            trial["summary"] == summarize_trades(trial["trades"], development_protocol),
            "matched parent summary differs from retained trades",
        )

    random = _read(root, random_path)
    _require(
        random["status"] == "PASS"
        and random["seed_count"] == len(random["evaluations"]) == 32
        and random["k_by_fold"] == declaration["matched_random_gate"]["k_by_fold"]
        and random["selection_policy"] == "ALL_32_FIXED_SEEDS_NO_SELECTION_OR_REPLACEMENT",
        "matched random-gate allocation changed",
    )
    for index, evaluation in enumerate(random["evaluations"]):
        selected = evaluation["selected_timestamps"]
        _require(
            evaluation["seed_index"] == index
            and evaluation["seed"] == seeds[index]
            and evaluation["selected_timestamps_sha256"] == canonical_hash(selected)
            and {fold: len(values) for fold, values in selected.items()} == random["k_by_fold"]
            and evaluation["summary"]
            == summarize_trades(evaluation["trades"], development_protocol),
            "random-gate seed/K/trade identity changed",
        )
    expectancies = [
        item["summary"]["metrics"]["net_expectancy_r"] for item in random["evaluations"]
    ]
    distribution = random["distribution"]
    _require(
        distribution["median_expectancy_r"] == quantile_type7(expectancies, 0.5)
        and distribution["q10_expectancy_r"] == quantile_type7(expectancies, 0.1)
        and distribution["q90_expectancy_r"] == quantile_type7(expectancies, 0.9)
        and distribution["mean_expectancy_r"]
        == round(math.fsum(expectancies) / len(expectancies), 10),
        "random-gate distribution/quantile convention changed",
    )

    coverage = _read(root, coverage_path)
    overall = coverage["overall"]
    _require(
        coverage["status"] == "PASS"
        and coverage["threshold_changes"] == 0
        and coverage["alternate_regime_definitions"] == 0
        and not coverage["outcome_conditioned_search"]
        and overall["raw_parent_breakout_candidates"] == 1875
        and overall["aligned_pass_among_breakouts"] == 195
        and overall["emitted_signals_while_flat"] == 125
        and overall["suppressed_by_active_position"] == 70
        and overall["resolved_trades"] == 125,
        "coverage funnel changed",
    )

    final = _read(root, final_path)
    parent_expectancy = parent["profiles"][0]["summary"]["metrics"]["net_expectancy_r"]
    delta = round(ALIGNED_EXPECTANCY - parent_expectancy, 10)
    q90 = distribution["q90_expectancy_r"]
    expected_classification = (
        "ALIGNED_DIAGNOSTIC_SUPPORTED_BUT_INCONCLUSIVE"
        if delta >= 0.12 and ALIGNED_EXPECTANCY > q90
        else "ALIGNED_DIAGNOSTIC_WEAKENED"
    )
    _require(
        final["status"] == "PASS"
        and final["classification"] == expected_classification
        and final["delta_parent_r"] == delta
        and final["matched_random_gate_q90_expectancy_r"] == q90
        and final["underlying_wp004_classification"] == "INCONCLUSIVE"
        and final["champion"] == "NONE"
        and final["artifact_content_hashes"]
        == {
            "matched_parent": canonical_hash(parent),
            "matched_random_gate": canonical_hash(random),
            "coverage": canonical_hash(coverage),
        },
        "comparability classification changed",
    )

    failure = _read(root, DIAGNOSTIC_DIR / "matched-controls-attempt-001-failure.json")
    _require(
        failure["result_artifacts_finalized"] == 0
        and failure["result_values_reported_or_used_for_adaptation"] == 0
        and failure["declared_unique_diagnostic_evaluations_invoked"] == 35,
        "failed diagnostic attempt was not preserved truthfully",
    )
    hash_index = _read(root, DIAGNOSTIC_DIR / "ARTIFACT-HASHES.json")
    _require(
        hash_index["hash_algorithm"] == "sha256-lf-normalized-text-v1"
        and len(hash_index["artifacts"]) == 14
        and all(
            text_sha256(root / item["path"]) == item["sha256"] for item in hash_index["artifacts"]
        ),
        "WP-005 material artifact hash index changed",
    )

    experiments = {path.name for path in (root / "research/experiments").iterdir() if path.is_dir()}
    _require(
        WP005_EXPERIMENTS <= experiments,
        "a strategy experiment present at WP-005 has disappeared",
    )
    _require(
        len(WP005_EXPERIMENTS) == 9,
        "WP-005 material strategy experiment identities changed",
    )

    if data_available:
        observed_source = json.loads(json.dumps(source_provenance(root)))
        _require(
            observed_source == source, "source provenance does not reproduce from installed data"
        )
        observed_reconciliation = json.loads(json.dumps(feature_and_result_reconciliation(root)))
        _require(
            observed_reconciliation == reconciliation,
            "independent feature/result reconciliation does not reproduce",
        )
        universe, _ = _candidate_universe(root)
        for evaluation in random["evaluations"]:
            seed = evaluation["seed"]
            expected = {
                fold: sorted(
                    sorted(values["parent"], key=lambda signal: random_gate_rank(seed, signal))[
                        : len(values["aligned"])
                    ]
                )
                for fold, values in universe.items()
            }
            _require(
                evaluation["selected_timestamps"] == expected,
                "random-gate selection differs from outcome-free SHA-256 ranking",
            )

    return {
        "status": "PASS",
        "source_provenance": source["classification"],
        "independent_reconciliation": "PASS",
        "integrity_replay_profiles": 12,
        "search_memory": search["version"],
        "diagnostic_evaluations": 35,
        "diagnostic_execution_attempts": 2,
        "matched_parent_default_expectancy_r": parent_expectancy,
        "matched_random_gate_q90_expectancy_r": q90,
        "classification": expected_classification,
        "experiments": 9,
        "sealed": 0,
    }
