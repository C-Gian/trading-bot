"""Preserve the genuine ALIGNED prospective evidence and record its final disposition.

The Owner's prediction-first pivot suspends automated ALIGNED prospective collection.
Genuine observations already existed when the pivot was authorized, so this tool copies
the runtime evidence and health stores verbatim into the tracked audit trail and derives
one deterministic disposition record from them.

Nothing is backfilled, reconstructed or reinterpreted. ``--check`` re-derives the
disposition from the preserved artifacts alone, so a clean checkout that has never run an
observer can still verify the record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.product import audit_chain
from app.product.shadow_observer import (
    EVIDENCE_STORE_PATH,
    EVIDENCE_VERSION,
    FIRST_REVIEW_COMPLETED_TRADES,
    HEALTH_STORE_PATH,
    MISSED_DECISION,
    OBSERVED,
    SUPPRESSED,
)

SUSPENSION_VERSION = "PROSPECTIVE_ALIGNED_OBSERVER_SUSPENSION_V1"
DISPOSITION = "SUSPENDED_BY_OWNER_OBJECTIVE_PIVOT"
PRESERVED_EVIDENCE = "research/prospective/PROSPECTIVE-ALIGNED-SHADOW-EVIDENCE-FINAL-V1_1.json"
PRESERVED_HEALTH = "research/prospective/PROSPECTIVE-ALIGNED-OBSERVER-HEALTH-FINAL-V1_1.json"
DISPOSITION_RECORD = "research/prospective/PROSPECTIVE-ALIGNED-OBSERVER-FINAL-DISPOSITION-V1.json"


def normalized_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def normalized_sha256(path: Path) -> str:
    return hashlib.sha256(normalized_bytes(path)).hexdigest()


def load_evidence(path: Path) -> dict[str, Any]:
    """Read one prospective evidence document and prove its audit chain still validates."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if document["version"] != EVIDENCE_VERSION:
        raise SystemExit(f"unexpected evidence version: {document['version']}")
    audit_chain.validate_chain(document["audit_chain"])
    return document


def derive(evidence: dict[str, Any], health: dict[str, Any], root: Path) -> dict[str, Any]:
    """Derive the final accounting from preserved evidence only, never from a summary."""
    decisions = evidence["decisions"]
    trades = evidence["trades"]
    statuses = Counter(item["status"] for item in decisions)
    observed = [item for item in decisions if item["status"] == OBSERVED]
    missed = [item for item in decisions if item["status"] == MISSED_DECISION]
    outcomes = Counter(item["decision"] for item in observed)
    provenance = evidence["build_provenance"][-1]
    return {
        "version": SUSPENSION_VERSION,
        "disposition": DISPOSITION,
        "reason": "OWNER_AUTHORIZED_PREDICTION_FIRST_OBJECTIVE",
        "adr": "decisions/ADR-0026-PREDICTION-FIRST-RESEARCH-OBJECTIVE.md",
        "observer_version": evidence["observer_version"],
        "evidence_version": evidence["version"],
        "evidence_stage": evidence["evidence_stage"],
        "strategy_version": evidence["strategy_version"],
        "audit_chain_version": evidence["audit_chain_version"],
        "audit_chain_integrity": "VALID",
        "audit_chain_events": len(evidence["audit_chain"]),
        "preserved_evidence": {
            "path": PRESERVED_EVIDENCE,
            "sha256": normalized_sha256(root / PRESERVED_EVIDENCE),
            "runtime_source": EVIDENCE_STORE_PATH,
        },
        "preserved_health": {
            "path": PRESERVED_HEALTH,
            "sha256": normalized_sha256(root / PRESERVED_HEALTH),
            "runtime_source": HEALTH_STORE_PATH,
        },
        "decision_records": len(decisions),
        "genuine_observations": len(observed),
        "observed_decisions": len(observed),
        "missed_decisions": len(missed),
        "suppressed_decisions": statuses.get(SUPPRESSED, 0),
        "prospective_observation_hours": statuses.get(OBSERVED, 0) + statuses.get(SUPPRESSED, 0),
        "observed_decision_outcomes": {
            "LONG": outcomes.get("LONG", 0),
            "NO_TRADE": outcomes.get("NO_TRADE", 0),
        },
        "raw_prospective_long_signals": outcomes.get("LONG", 0),
        "shadow_trades_open": 0,
        "shadow_trades_completed": len(trades),
        "observed_boundaries": sorted(item["decision_boundary"] for item in observed),
        "missed_boundaries": sorted(item["decision_boundary"] for item in missed),
        "miss_reasons": sorted({item["miss_reason"] for item in missed}),
        "first_activation_utc": health["initial_activation"],
        "final_activation_utc": health["observer_activation"],
        "final_heartbeat_utc": health["last_heartbeat"],
        "final_observer_status": health["status"],
        "build_provenance_version": provenance["provenance_version"],
        "build_provenance_verified": provenance["verified"],
        "code_build_identity": provenance["git_head"],
        "evidence_backfilled": False,
        "evidence_rewritten": False,
        "runtime_store_deleted": False,
        "implementation_deleted": False,
        "automatic_collection_on_main": False,
        "review_boundary_completed_shadow_trades": FIRST_REVIEW_COMPLETED_TRADES,
        "review_boundary_reached": False,
        "scientific_conclusion": "INSUFFICIENT_PROSPECTIVE_EVIDENCE_NO_CONCLUSION",
        "champion_status": "NONE",
        "real_money": False,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def preserve(root: Path) -> dict[str, Any]:
    """Copy the runtime stores verbatim, then derive the disposition from the copies."""
    runtime_evidence, runtime_health = root / EVIDENCE_STORE_PATH, root / HEALTH_STORE_PATH
    if not runtime_evidence.is_file() or not runtime_health.is_file():
        raise SystemExit("no runtime prospective evidence and health store pair to preserve")
    preserved = root / PRESERVED_EVIDENCE
    preserved.parent.mkdir(parents=True, exist_ok=True)
    preserved.write_bytes(normalized_bytes(runtime_evidence))
    (root / PRESERVED_HEALTH).write_bytes(normalized_bytes(runtime_health))
    evidence = load_evidence(preserved)
    health = json.loads((root / PRESERVED_HEALTH).read_text(encoding="utf-8"))
    record = derive(evidence, health, root)
    write_json(root / DISPOSITION_RECORD, record)
    return record


def verify(root: Path) -> dict[str, Any]:
    """Re-derive the disposition from the preserved artifacts and compare it exactly."""
    evidence = load_evidence(root / PRESERVED_EVIDENCE)
    health = json.loads((root / PRESERVED_HEALTH).read_text(encoding="utf-8"))
    expected = derive(evidence, health, root)
    recorded = json.loads((root / DISPOSITION_RECORD).read_text(encoding="utf-8"))
    if recorded != expected:
        raise SystemExit("the recorded prospective disposition no longer matches its evidence")
    runtime = root / EVIDENCE_STORE_PATH
    if runtime.is_file() and normalized_bytes(runtime) != normalized_bytes(
        root / PRESERVED_EVIDENCE
    ):
        raise SystemExit("the runtime evidence store diverged from the preserved copy")
    return recorded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    record = verify(ROOT) if options.check else preserve(ROOT)
    observations = record["genuine_observations"]
    print(
        f"prospective ALIGNED observer {record['disposition']}: "
        f"observations={observations} missed={record['missed_decisions']} "
        f"shadow_trades={record['shadow_trades_completed']}"
    )


if __name__ == "__main__":
    main()
