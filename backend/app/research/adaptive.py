"""Cumulative adaptive decisions are explicit allocations, not evidence resets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runner import sha256
from .search_memory import accounting, load_memory

ROOT = Path(__file__).resolve().parents[3]
WP004_IDS = {"EXP-ALG-007-REGIME", "EXP-ALG-008-PARTICIPATION", "EXP-ALG-009-ALIGNED"}


def validate_adaptive(root: Path = ROOT) -> dict[str, Any]:
    document = json.loads((root / "research/memory/ADAPTIVE_DECISIONS.json").read_text())
    if document["schema_version"] != 1 or document["version"] != "ADAPTIVE_RESEARCH_GOVERNANCE_V1":
        raise ValueError("unknown adaptive governance version")
    decisions = document["decisions"]
    if len(decisions) != 1 or document["prior_adaptive_decisions"] != 0:
        raise ValueError("WP-004 authorizes exactly one adaptive allocation")
    decision = decisions[0]
    required = {
        "decision_id": "WP004-ADAPT-001",
        "work_package": "WP-004",
        "kind": "ADAPTIVE_FOLLOW_UP",
        "hypothesis_id": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
        "family_id": "FAM-BREAKOUT",
        "primary_experiment_id": "EXP-ALG-009-ALIGNED",
        "result_dependent_forks": 1,
        "parameter_searches": 0,
        "allocated_core_hypotheses": 1,
        "allocated_structural_variants": 3,
        "allocated_profile_trials": 12,
        "allocated_fold_executions": 72,
        "sealed_queries": 0,
        "paper_observations": 0,
    }
    if any(decision.get(key) != value for key, value in required.items()):
        raise ValueError("adaptive allocation differs from frozen WP-004 budget")
    if (
        set(decision["descendant_experiment_ids"]) != WP004_IDS
        or len(decision["descendant_experiment_ids"]) != 3
        or document["prior_result_dependent_forks"] != 0
    ):
        raise ValueError("adaptive fork identities differ")
    source = root / decision["source_path"]
    if sha256(source) != decision["source_result_sha256"]:
        raise ValueError("adaptive source identity differs")
    result = json.loads(source.read_text())
    if result["experiment_id"] != decision["source_experiment_id"]:
        raise ValueError("adaptive source experiment differs")
    if not (root / decision["authority"]).is_file():
        raise ValueError("adaptive allocation lacks decision authority")
    memory = load_memory(root)
    entries = [entry for entry in memory["entries"] if entry["work_package"] == "WP-004"]
    if not {entry["experiment_id"] for entry in entries} <= WP004_IDS:
        raise ValueError("unallocated WP-004 descendant")
    if any(
        entry["family_id"] != decision["family_id"]
        or entry["hypothesis_id"] != decision["hypothesis_id"]
        or entry["budget_units"]["trials"] != 4
        for entry in entries
    ):
        raise ValueError("WP-004 ledger does not preserve adaptive family allocation")
    counts = accounting(memory)
    return {
        "material_economic_hypotheses": counts["material_economic_hypotheses"],
        "configuration_variants": counts["global"]["strategy_variants"],
        "profile_trials": counts["global"]["trials"],
        "adaptive_decisions": len(decisions),
        "result_dependent_forks": sum(item["result_dependent_forks"] for item in decisions),
        "strategy_descendants": counts["strategy_descendants"],
        "wp004_variants_reserved": len(entries),
        "wp004_profiles_reserved": sum(entry["budget_units"]["trials"] for entry in entries),
        "sealed_queries": 0,
    }
