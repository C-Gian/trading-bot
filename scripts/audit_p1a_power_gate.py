"""Generate or verify the deterministic P1A prospective power-gate artifacts.

`--generate` needs the local development dataset and rebuilds the committed placebo null
distribution. `--check` needs no market data: it re-derives the gate from the committed
null distribution and fails on any drift, so continuous integration can audit the gate
without ever touching BTCUSDT bars.

Neither mode computes the unshifted 120h ALIGNED statistic.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.signal_persistence import (
    assert_no_result_leakage,
    evaluate_power_gate,
    render_power_gate_markdown,
)
from app.research.statistical_governance import json_bytes

NULL_PATH = ROOT / "reports/power/P1A-ALIGNED-SIGNAL-PERSISTENCE-NULL-DISTRIBUTION-V1.json"
GATE_JSON = ROOT / "reports/power/P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-V1.json"
GATE_MD = ROOT / "reports/power/P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-V1.md"


def load_null(path: Path = NULL_PATH) -> dict[str, Any]:
    null = json.loads(path.read_text(encoding="utf-8"))
    assert_no_result_leakage(null)
    return null


def gate_outputs(null: dict[str, Any]) -> dict[Path, bytes]:
    gate = evaluate_power_gate(null)
    assert_no_result_leakage(gate)
    return {
        GATE_JSON: json_bytes(gate),
        GATE_MD: render_power_gate_markdown(gate).encode("utf-8"),
    }


def generate() -> int:
    from app.research.signal_persistence import build_null_distribution
    from app.research.signal_persistence_lab import load_fold_series

    null = build_null_distribution(load_fold_series(ROOT))
    assert_no_result_leakage(null)
    outputs = {NULL_PATH: json_bytes(null), **gate_outputs(null)}
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print("P1A power-gate artifacts generated")
    return 0


def check() -> int:
    expected = gate_outputs(load_null())
    drift = [
        path
        for path, content in expected.items()
        if not path.is_file() or path.read_bytes() != content
    ]
    if drift:
        for path in drift:
            print(f"::error file={path.relative_to(ROOT).as_posix()}::P1A power-gate drift")
        raise SystemExit("P1A power-gate drift: " + ", ".join(str(path) for path in drift))
    print("P1A power gate: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify committed artifacts")
    parser.add_argument("--generate", action="store_true", help="rebuild from local market data")
    args = parser.parse_args()
    if args.generate == args.check:
        raise SystemExit("choose exactly one of --generate or --check")
    return generate() if args.generate else check()


if __name__ == "__main__":
    raise SystemExit(main())
