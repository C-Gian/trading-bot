"""Append-only research registry over the frozen V1 and WP-006 records.

The V1 ledger, budget, family registry and outcomes are byte-frozen by the WP-004 audit,
and the WP-006 V2 registry and budget are byte-frozen by the WP-006 audit. Rather than
adding one bespoke layer per work package, every later work package writes **new files**
into ``research/memory/registry/`` and never edits an existing one.

Accounting sums every layer, so a reader sees one cumulative search burden and no
counter is ever reset by introducing a new file or a new name.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .search_memory import accounting as v1_accounting
from .search_memory import load_memory
from .wp004 import ROOT

REGISTRY = Path("research/memory/registry")
FAMILIES = REGISTRY / "families"
ALLOCATIONS = REGISTRY / "allocations"
ADMISSIONS = REGISTRY / "admissions"
LEDGER = REGISTRY / "ledger"
OUTCOMES = REGISTRY / "outcomes"
V2_FAMILIES = "research/memory/FAMILY_REGISTRY_V2.json"
V2_BUDGET = "research/memory/SEARCH_BUDGET_V2.json"
V2_LEDGER = "research/memory/ADMISSION_LEDGER_V2.jsonl"
V2_OUTCOMES = "research/memory/OUTCOMES_V2.jsonl"
WP006_ALLOCATION = "research/memory/WP006-PULLBACK-RECOVERY-ALLOCATION.json"
DIAGNOSTICS_V2 = "research/memory/ADAPTIVE_DIAGNOSTICS_V2.json"
LEGACY_SIGNATURES = "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _lines(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _directory(root: Path, relative: Path) -> list[dict[str, Any]]:
    directory = root / relative
    if not directory.is_dir():
        return []
    return [read_json(path) for path in sorted(directory.glob("*.json"))]


def registry_ledger(root: Path = ROOT) -> list[dict[str, Any]]:
    directory = root / LEDGER
    if not directory.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.jsonl")):
        entries.extend(_lines(path))
    return entries


def registry_outcomes(root: Path = ROOT) -> list[dict[str, Any]]:
    directory = root / OUTCOMES
    if not directory.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.jsonl")):
        entries.extend(_lines(path))
    return entries


def admission_ledger(root: Path = ROOT) -> list[dict[str, Any]]:
    """Every SEARCH_MEMORY_V2-era admission, oldest layer first."""
    return [*_lines(root / V2_LEDGER), *registry_ledger(root)]


def all_outcomes(root: Path = ROOT) -> list[dict[str, Any]]:
    return [
        *load_memory(root)["outcomes"],
        *_lines(root / V2_OUTCOMES),
        *registry_outcomes(root),
    ]


def all_families(root: Path = ROOT) -> list[dict[str, Any]]:
    families = list(load_memory(root)["families"]["families"])
    families.extend(read_json(root / V2_FAMILIES)["families"])
    families.extend(_directory(root, FAMILIES))
    return families


def alias_map(root: Path = ROOT, *, exclude: str | None = None) -> dict[str, str]:
    """Every registered family id, alias and entry-event anchor across all layers."""
    aliases: dict[str, str] = {}
    for family in all_families(root):
        if family["family_id"] == exclude:
            continue
        for alias in [family["family_id"], *family["aliases"], *family["entry_event_anchors"]]:
            aliases[alias] = family["family_id"]
    return aliases


def signatures(
    root: Path = ROOT, *, exclude_experiment_ids: set[str] | None = None
) -> list[dict[str, Any]]:
    """Frozen V1 reference translations plus every V2-era admitted behaviour."""
    excluded = exclude_experiment_ids or set()
    document = read_json(root / LEGACY_SIGNATURES)
    entries = [
        {
            "experiment_id": item["experiment_id"],
            "root_family": item["root_family"],
            "behavior_hash": item["behavior_hash"],
            "structural_hash": item["structural_hash"],
        }
        for item in document["signatures"]
        if item["experiment_id"] not in excluded
    ]
    entries.extend(
        {
            "experiment_id": item["experiment_id"],
            "root_family": item["root_family"],
            "behavior_hash": item["behavior_hash"],
            "structural_hash": item["structural_hash"],
        }
        for item in admission_ledger(root)
        if item["experiment_id"] not in excluded
    )
    return entries


def family_limits(root: Path = ROOT) -> dict[str, dict[str, int]]:
    limits = dict(load_memory(root)["budget"]["family_limits"])
    limits.update(read_json(root / V2_BUDGET)["family_limits"])
    for allocation in _directory(root, ALLOCATIONS):
        limits[allocation["root_family"]] = allocation["family_limits"]
    return limits


def allocations(root: Path = ROOT) -> list[dict[str, Any]]:
    """Every result-dependent strategy allocation after the frozen V1 decision."""
    return [read_json(root / WP006_ALLOCATION), *_directory(root, ALLOCATIONS)]


def v2_accounting(root: Path = ROOT) -> dict[str, int]:
    entries = admission_ledger(root)
    return {
        "experiments": len(entries),
        "strategy_variants": sum(item["budget_units"]["strategy_variants"] for item in entries),
        "trials": sum(item["budget_units"]["trials"] for item in entries),
        "numeric_parameter_variants": sum(
            item["budget_units"]["numeric_parameter_variants"] for item in entries
        ),
        "material_economic_hypotheses": len(
            {
                item["hypothesis_id"]
                for item in entries
                if item["hypothesis_role"] == "ECONOMIC_CORE"
            }
        ),
        "strategy_descendants": sum(bool(item["parent_experiment_ids"]) for item in entries),
    }


def family_accounting(root: Path = ROOT) -> dict[str, dict[str, int]]:
    """Consumed units per root family across every layer."""
    memory = load_memory(root)
    consumed = {family: dict(units) for family, units in v1_accounting(memory)["families"].items()}
    for entry in admission_ledger(root):
        units = consumed.setdefault(
            entry["root_family"],
            {
                "experiments": 0,
                "strategy_variants": 0,
                "trials": 0,
                "numeric_parameter_variants": 0,
            },
        )
        units["experiments"] += entry["budget_units"]["experiments"]
        units["strategy_variants"] += entry["budget_units"]["strategy_variants"]
        units["trials"] += entry["budget_units"]["trials"]
        units["numeric_parameter_variants"] += entry["budget_units"]["numeric_parameter_variants"]
    return consumed


def cumulative_accounting(root: Path = ROOT) -> dict[str, int]:
    """One total search burden across the frozen V1 layer and every additive layer."""
    memory = load_memory(root)
    first = v1_accounting(memory)
    later = v2_accounting(root)
    diagnostics = read_json(root / DIAGNOSTICS_V2)
    decisions = diagnostics["cumulative_adaptive_decisions"]
    forks = diagnostics["cumulative_result_dependent_forks"]
    reserved: dict[str, dict[str, int]] = {}
    for allocation in allocations(root):
        decisions += allocation["adaptive_decision_increment"]
        forks += allocation["result_dependent_fork_increment"]
        reserved[allocation["work_package"]] = {
            "variants": allocation.get(
                "strategy_variants", allocation.get("model_configurations", 0)
            ),
            "profiles": allocation["profile_evaluations"],
        }
    totals = {
        "material_economic_hypotheses": first["material_economic_hypotheses"]
        + later["material_economic_hypotheses"],
        "configuration_variants": first["global"]["strategy_variants"] + later["strategy_variants"],
        "profile_trials": first["global"]["trials"] + later["trials"],
        "numeric_parameter_variants": first["global"]["numeric_parameter_variants"]
        + later["numeric_parameter_variants"],
        "adaptive_decisions": decisions,
        "result_dependent_forks": forks,
        "strategy_descendants": first["strategy_descendants"] + later["strategy_descendants"],
        "wp004_variants_reserved": 3,
        "wp004_profiles_reserved": 12,
    }
    for work_package, units in sorted(reserved.items()):
        key = work_package.replace("-", "").lower()
        totals[f"{key}_variants_reserved"] = units["variants"]
        totals[f"{key}_profiles_reserved"] = units["profiles"]
    totals.update(
        integrity_replay_profiles=12,
        diagnostic_evaluations=35,
        diagnostic_execution_attempts=2,
        supervised_model_fits=sum(
            allocation.get("supervised_model_fits", 0) for allocation in allocations(root)
        ),
        sealed_queries=0,
    )
    return totals


def budget_view(root: Path = ROOT) -> list[dict[str, Any]]:
    """Consumed against limit for every root family in every layer."""
    consumed = family_accounting(root)
    return [
        {
            "family_id": family,
            "experiments_consumed": consumed.get(family, {}).get("experiments", 0),
            "experiments_limit": limits["experiments"],
            "trials_consumed": consumed.get(family, {}).get("trials", 0),
            "trials_limit": limits["trials"],
        }
        for family, limits in family_limits(root).items()
    ]


def validate_budgets(root: Path = ROOT) -> dict[str, dict[str, int]]:
    """No family may exceed its allocation, and no layer may reset a consumed budget."""
    limits = family_limits(root)
    consumed = family_accounting(root)
    for family, units in consumed.items():
        allowed = limits.get(family)
        if allowed is None:
            raise ValueError(f"family lacks an explicit budget allocation: {family}")
        for field, value in units.items():
            if value > allowed[field]:
                raise ValueError(f"family {family} {field} budget exceeded")
    return consumed
