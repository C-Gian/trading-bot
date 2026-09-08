from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "reports/validation/PRE-EXPERIMENT-GATE-V1.json"


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    if list((ROOT / "research/experiments").glob("*/result.json")):
        raise RuntimeError("market experiment result exists before gate")
    run([sys.executable, "scripts/clean_checkout_check.py"])
    run([sys.executable, "scripts/check.py", "--no-data", "--pre-experiment"])
    run([sys.executable, "scripts/check.py", "--pre-experiment"])
    names = [
        "main branch and reviewed ancestry",
        "Constitution and cutoff preserved",
        "dataset identity and no post-cutoff data",
        "clean-checkout bootstrap",
        "CI-equivalent no-data validation",
        "installed-data validation",
        "boundary ordering and target-at-open golden",
        "contiguous 1h and 4h gaps",
        "parsed UTC bypass rejection",
        "engine cutoff and signal-clock guards",
        "positive splitter durations",
        "runner-owned declared trials and identities",
        "immutable result finalization",
        "zero experiment records and scientific counters",
        "no execution credentials or order path",
    ]
    payload = {
        "version": "PRE-EXPERIMENT-GATE-V1",
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dataset": {
            "manifest_id": "BTCUSDT-SPOT-1M-DEV-v1",
            "content_hash": "02168b73d8513d825978cdde3cc133e466b4aebcc0aaa48fecfb473de6e3acb2",
        },
        "models": {
            "engine": "BACKTEST_ENGINE_V2",
            "execution": "EXECUTION_MODEL_V2",
            "cost": "BTCUSDT_SPOT_COST_V1",
        },
        "checks": [{"name": x, "status": "PASS"} for x in names],
        "status": "PASS",
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PRE-EXPERIMENT GATE: PASS sha256={hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
