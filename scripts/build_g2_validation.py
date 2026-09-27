"""Build or `--check` the G2-01 engineering validation artifact (NOT performance evidence).

Write mode executes the full deterministic validation (synthetic end-to-end run twice, replay-speed
identity, prefix invariance, the thirteen cycle-checkpoint tests at full size and, when the local
exposed data is present, the declared <=2024 engineering window) and writes the canonical JSON
artifact plus a verbose log. `--check` re-executes the same validation and requires the result to be
byte-identical to the committed artifact (the engineering-window section is compared only when the
local data is present). No economic market run, tuning or protected-data access is possible here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.g2.service import _engineering_data_present
from app.g2.validation import ARTIFACT_PATH, artifact_bytes, build

LOG_PATH = "reports/validation/G2-01-ENGINEERING-VALIDATION-V1.log"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    options = parser.parse_args()
    data = _engineering_data_present(ROOT)
    started = time.time()
    payload = build(ROOT, options.workers, data)
    produced = artifact_bytes(payload)
    path = ROOT / ARTIFACT_PATH
    if options.check:
        recorded = json.loads(path.read_bytes().replace(b"\r\n", b"\n"))
        replay = json.loads(produced)
        if not data:
            replay.pop("engineering_window")
            recorded.pop("engineering_window")
        if replay != recorded:
            differing = sorted(
                k for k in set(replay) | set(recorded) if replay.get(k) != recorded.get(k)
            )
            raise SystemExit(f"G2-01 validation replay differs from the artifact: {differing}")
        print(f"G2-01 engineering validation replay: PASS (identical; data={data})")
        return
    if not data:
        raise SystemExit("write mode requires the local exposed-window data to record its parity")
    path.write_bytes(produced)
    lines = [
        f"G2-01 engineering validation build ({time.time() - started:.1f}s, workers={options.workers})",
        f"synthetic run_id={payload['synthetic_run']['run_id']}",
        f"synthetic fingerprint={payload['synthetic_run']['fingerprint']}",
        f"determinism={json.dumps(payload['determinism'], sort_keys=True)}",
        f"cycle checkpoint all_pass={payload['cycle_checkpoint']['all_pass']}",
    ]
    for name, test in payload["cycle_checkpoint"]["tests"].items():
        lines.append(f"  cycle {name}: pass={test['pass']}")
    window = payload["engineering_window"]
    lines.append(
        f"engineering window status={window['status']} ledger={window.get('ledger_record')}"
    )
    lines.append(json.dumps(window, sort_keys=True, default=str))
    (ROOT / LOG_PATH).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:5]))


if __name__ == "__main__":
    main()
