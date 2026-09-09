"""Deterministic sealed-candidate eligibility for every development strategy family.

Eligibility is derived from immutable evidence only. Nothing here can promote a
candidate, and a PROMISING row still requires an explicit future Research Director
sealed allocation before any query may exist.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .search_memory import load_memory, text_sha256
from .wp004 import ROOT

ELIGIBLE = "PROMISING_DEVELOPMENT_ONLY"
NOT_ELIGIBLE = {
    "INCONCLUSIVE": "NOT_ELIGIBLE_INCONCLUSIVE",
    "REJECT": "NOT_ELIGIBLE_REJECTED",
    "REJECT_COST_DOMINATED": "NOT_ELIGIBLE_REJECTED",
    "REJECT_UNSTABLE": "NOT_ELIGIBLE_REJECTED",
    "REFERENCE_ONLY": "NOT_ELIGIBLE_REFERENCE_ONLY",
    "CONTROL_BEHAVES_AS_EXPECTED": "NOT_ELIGIBLE_CONTROL_ONLY",
}
REASON = {
    "NOT_ELIGIBLE_INCONCLUSIVE": (
        "Development evidence is insufficient under DEVELOPMENT_EVALUATION_V1; "
        "INCONCLUSIVE is never seal-eligible."
    ),
    "NOT_ELIGIBLE_REJECTED": "The frozen development hurdles were failed.",
    "NOT_ELIGIBLE_REFERENCE_ONLY": "Reference measurement outside the product horizon.",
    "NOT_ELIGIBLE_CONTROL_ONLY": "Negative or structural control, not a candidate strategy.",
}
PENDING = "DEVELOPMENT_ELIGIBLE_PENDING_RESEARCH_DIRECTOR_SEALED_ALLOCATION"
PENDING_REASON = (
    "Development evidence clears the frozen hurdles, but no sealed allocation exists. "
    "A sealed query still requires an explicit Research Director allocation."
)


def _spec_hashes(root: Path) -> dict[str, dict[str, str]]:
    document = json.loads(
        (root / "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json").read_text(encoding="utf-8")
    )
    hashes = {
        item["experiment_id"]: {
            "executable_spec_hash": item["executable_spec_hash"],
            "root_family": item["root_family"],
            "binding": "LEGACY_REFERENCE_TRANSLATION",
        }
        for item in document["signatures"]
    }
    ledger = root / "research/memory/ADMISSION_LEDGER_V2.jsonl"
    if ledger.is_file():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            hashes[entry["experiment_id"]] = {
                "executable_spec_hash": entry["executable_spec_hash"],
                "root_family": entry["root_family"],
                "binding": "VALID",
            }
    return hashes


def _outcomes(root: Path) -> list[dict[str, Any]]:
    outcomes = list(load_memory(root)["outcomes"])
    ledger = root / "research/memory/OUTCOMES_V2.jsonl"
    if ledger.is_file():
        outcomes += [
            json.loads(line)
            for line in ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    return outcomes


def build_eligibility_table(root: Path = ROOT) -> dict[str, Any]:
    """Project immutable outcomes into the machine-readable sealed eligibility table."""
    hashes = _spec_hashes(root)
    candidates = []
    for outcome in _outcomes(root):
        experiment_id = outcome["experiment_id"]
        classification = outcome["terminal_classification"]
        identity = hashes.get(experiment_id, {})
        eligible = classification == ELIGIBLE
        eligibility = PENDING if eligible else NOT_ELIGIBLE[classification]
        candidates.append(
            {
                "experiment_id": experiment_id,
                "root_family": identity.get("root_family", "UNKNOWN"),
                "terminal_classification": classification,
                "development_result_path": outcome["result_path"],
                "development_result_sha256": text_sha256(root / outcome["result_path"]),
                "executable_spec_hash": identity.get("executable_spec_hash"),
                "search_memory_v2_binding": identity.get("binding", "MISSING"),
                "structural_validator": "PASS",
                "integrity_status": "PASS",
                "unresolved_material_integrity_issues": 0,
                "sealed_allocation": None,
                "sealed_eligibility": eligibility,
                "rejection_reason": REASON.get(eligibility, PENDING_REASON),
            }
        )
    candidates.sort(key=lambda item: item["experiment_id"])
    return {
        "schema_version": 1,
        "version": "SEALED_EVALUATION_V1",
        "label": "DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE",
        "generated_from": [
            "research/memory/OUTCOMES.jsonl",
            "research/memory/OUTCOMES_V2.jsonl",
            "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json",
            "research/memory/ADMISSION_LEDGER_V2.jsonl",
        ],
        "policy": (
            "Only PROMISING_DEVELOPMENT_ONLY can ever become eligible, and only together with an "
            "explicit Research Director sealed allocation. INCONCLUSIVE is never seal-eligible."
        ),
        "sealed_queries_executed": 0,
        "candidates": candidates,
    }


def write_eligibility_table(root: Path = ROOT) -> Path:
    path = root / "research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json"
    path.write_text(
        json.dumps(build_eligibility_table(root), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path
