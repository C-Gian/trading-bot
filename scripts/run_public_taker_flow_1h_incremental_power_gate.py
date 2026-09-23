"""Run the frozen EXP-PRED-V2-006 pre-execution power gate exactly once, or replay it.

Needs the pinned official source (`scripts/acquire_public_taker_flow.py`). It replays the
exposed EXP-PRED-V2-005 1h proxy with the frozen foundation code, verifies that replay
against the committed result, computes the analog power gate and writes:

- `reports/validation/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1.json`;
- `reports/validation/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1.md`.

It never fits or scores an EXP-PRED-V2-006 control or candidate. Written outputs are never
rewritten; ``--check`` recomputes and compares them by canonical text (ADR-0034).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.taker_flow_power_gate import (
    GATE_JSON_PATH,
    GATE_MARKDOWN_PATH,
    GATE_PATHS,
    MDE_STATEMENT,
    PowerGateError,
    canonical_json_bytes,
    markdown_bytes,
    run_power_gate,
    validate_record,
)
from app.research.text_provenance import canonical_text_bytes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="replay and compare with the written outputs"
    )
    options = parser.parse_args()

    existing = [path for path in GATE_PATHS if (ROOT / path).exists()]
    if not options.check and existing:
        raise PowerGateError(
            f"power-gate outputs already exist and are never rewritten: {existing}"
        )
    if options.check and len(existing) != len(GATE_PATHS):
        raise PowerGateError("--check needs both written power-gate outputs")

    record = run_power_gate(ROOT)
    validate_record(record, ROOT)
    outputs = {
        GATE_JSON_PATH: canonical_json_bytes(record),
        GATE_MARKDOWN_PATH: markdown_bytes(record),
    }

    if options.check:
        mismatched = [
            path
            for path, payload in outputs.items()
            if canonical_text_bytes((ROOT / path).read_bytes()) != payload
        ]
        if mismatched:
            raise PowerGateError(f"power-gate replay does not reproduce: {mismatched}")
        print(f"power gate replay: PASS classification={record['classification']}")
        return

    for path, payload in outputs.items():
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    print(MDE_STATEMENT)
    print(f"power gate written: classification={record['classification']}")
    analysis = record["analysis"]
    if analysis is not None:
        mde = analysis["mde"]
        mde_text = f"{mde['mde']:.7f}" if mde["reached"] else "NOT_REACHED"
        print(f"  power_at_mesi={analysis['power_at_mesi']:.4f} mde={mde_text}")
    for path in outputs:
        print(f"  wrote {path}")


if __name__ == "__main__":
    main()
