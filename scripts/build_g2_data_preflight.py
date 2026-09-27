"""Build or `--check` the G2-02 exposed-data integrity preflight (non-economic, <=2024 only).

Write mode audits the canonical BTCUSDT USD-M 1m objects and settled-funding artifact through the
phase-bounded loader and writes the canonical JSON artifact. `--check` recomputes it and requires a
byte-identical result when the local exposed data is present; without data it validates only the
committed artifact's structure and negative claims.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.g2.preflight import ARTIFACT_PATH, build
from app.g2.service import _engineering_data_present
from app.g2.validation import artifact_bytes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    path = ROOT / ARTIFACT_PATH
    if options.check:
        recorded = json.loads(path.read_bytes().replace(b"\r\n", b"\n"))
        assert recorded["protected_objects_opened"] is False
        assert not any(recorded["claims"].values())
        if not _engineering_data_present(ROOT):
            print("G2-02 data preflight: artifact claims PASS (no local data; replay skipped)")
            return
        if json.loads(artifact_bytes(build(ROOT))) != recorded:
            raise SystemExit("G2-02 data preflight replay differs from the committed artifact")
        print(f"G2-02 data preflight replay: PASS (identical; status={recorded['status']})")
        return
    payload = build(ROOT)
    path.write_bytes(artifact_bytes(payload))
    print(f"G2-02 data preflight: {payload['status']}")


if __name__ == "__main__":
    main()
