"""`--check` replay of the accepted System G1 cycle synthetic quality gate (ADR-0045/ADR-0046).

Synthetic method validation only: no market data is read, and no threshold, quality feature, band,
ACP parameter or method is searched. The accepted artifact is preserved immutably (canonical
SHA-256 pin). ADR-0046 later activated the cycle component, which changed `cycle.py` source text
(activation and timing qualifier) but not the cycle math or labels, so `--check` re-executes the
whole frozen gate and requires every result to be identical except the recorded code identities and
the activation flag.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.g1.cycle_quality_gate import ARTIFACT_PATH, build_gate

DIGITS = 9
PRESERVED_SHA256 = "68124a8b199cecde15eccfd16e435a53389f2c4bcd2ae5d5dc931c61737ba6d3"
POST_ACTIVATION_FIELDS = ("code_canonical_sha256", "cycle_active_in_decisions")


def rounded(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, DIGITS)
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [rounded(item) for item in value]
    return value


def artifact_bytes(workers: int) -> bytes:
    payload = rounded(build_gate(workers))
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--workers", type=int, default=min(6, os.cpu_count() or 1))
    options = parser.parse_args()
    path = ROOT / ARTIFACT_PATH
    if not options.check:
        raise SystemExit("the accepted gate artifact is preserved; only --check replay is allowed")
    preserved = path.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(preserved).hexdigest() != PRESERVED_SHA256:
        raise SystemExit("the accepted cycle quality gate artifact was modified")
    replay = json.loads(artifact_bytes(options.workers))
    original = json.loads(preserved)
    for field in POST_ACTIVATION_FIELDS:
        replay.pop(field)
        original.pop(field)
    if replay != original:
        raise SystemExit("the cycle quality gate no longer replays identically")
    print(f"System G1 cycle quality gate replay: PASS (identical; {replay['disposition']})")


if __name__ == "__main__":
    main()
