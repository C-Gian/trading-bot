"""Check the preserved Checkpoint-1 System G1 cycle synthetic diagnostic artifact.

The V1 artifact was produced by cycle implementation IMPL-1 (labels pending thresholds). ADR-0045
froze the quality labels (IMPL-2), so the V1 artifact no longer regenerates from current code; it
is preserved immutably and `--check` verifies its canonical SHA-256. The current gate is
`scripts/build_g1_cycle_quality_gate.py`. Synthetic only: no market data is read.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = "reports/research/SYSTEM-G1-CYCLE-SYNTHETIC-DIAGNOSTICS-V1.json"
PRESERVED_V1_SHA256 = "e9b7e655c6ef0e03b444dd88c3c67a7e9fa5e36ff29069a392b0651e5a010c9a"


def preserved_sha256() -> str:
    return hashlib.sha256((ROOT / ARTIFACT_PATH).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    if not options.check:
        raise SystemExit("V1 diagnostics are preserved history; build the V1 quality gate instead")
    if preserved_sha256() != PRESERVED_V1_SHA256:
        raise SystemExit("the preserved Checkpoint-1 cycle diagnostics were modified")
    print("System G1 cycle synthetic diagnostics V1: PASS (preserved artifact unchanged)")


if __name__ == "__main__":
    main()
