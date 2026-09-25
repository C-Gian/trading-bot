"""Build (or `--check` replay) the frozen System G1 cycle synthetic quality gate artifact.

Synthetic method validation only (ADR-0045): no market data is read, and no threshold, quality
feature, band, ACP parameter or method is searched. `--check` re-executes the whole frozen gate
and requires a byte-identical artifact.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.g1.cycle_quality_gate import ARTIFACT_PATH, build_gate

DIGITS = 9


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
    content = artifact_bytes(options.workers)
    disposition = json.loads(content)["disposition"]
    if options.check:
        if path.read_bytes().replace(b"\r\n", b"\n") != content:
            raise SystemExit("the cycle quality gate does not replay byte-identically")
        print(f"System G1 cycle quality gate replay: PASS (byte-identical; {disposition})")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    print(f"wrote {ARTIFACT_PATH}: {disposition}")


if __name__ == "__main__":
    main()
