"""Run or replay the single frozen Candidate #1 admission calculation.

Specification: `research/protocols/CANDIDATE-1-FROZEN-ADMISSION-V1.md` (Director-frozen).
Budget: exactly one support calculation; `--check` is a deterministic replay, not a new one.

Usage:
    python scripts/audit_candidate_1_frozen_admission.py          # the one calculation
    python scripts/audit_candidate_1_frozen_admission.py --check  # replay and compare
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.open_interest_source import load_open_interest
from app.predictive.taker_flow_source import (
    MANIFEST_PATH as KLINE_MANIFEST_PATH,
)
from app.predictive.taker_flow_source import (
    SPOT,
    USDM,
    VALID,
    WINDOW_START_MS,
    load_minute_books,
)
from app.research import candidate_1_admission as frozen

OI_MANIFEST_PATH = "data/manifests/BTCUSDT-USDM-OPEN-INTEREST-DEV-v1.json"
MODULE_PATH = "backend/app/research/candidate_1_admission.py"
SCRIPT_PATH = "scripts/audit_candidate_1_frozen_admission.py"


def canonical_text_sha256(path: Path) -> str:
    text = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(text).hexdigest()


def hourly(book: Any) -> np.ndarray:
    hours = book.status.shape[0] // 60
    index = np.arange(1, hours + 1) * 60 - 1
    return np.where(book.status[index] == VALID, book.close[index], np.nan)


def build() -> dict[str, Any]:
    books, _ = load_minute_books(ROOT)
    source = load_open_interest(ROOT)
    spot, perp = hourly(books[SPOT]), hourly(books[USDM])
    start = WINDOW_START_MS // 1000
    instants = start + np.arange(1, spot.shape[0] + 1, dtype=np.int64) * frozen.HOUR
    inputs = frozen.HourlyInputs(
        instants=instants,
        spot_close=spot,
        perp_close=perp,
        oi_times=np.asarray(source.times, dtype=np.int64),
        oi_quantity=np.asarray(source.quantities, dtype=np.float64),
    )
    record = frozen.admission(inputs)
    record["identity"] = {
        path: canonical_text_sha256(ROOT / path)
        for path in (
            frozen.PROTOCOL_PATH,
            MODULE_PATH,
            SCRIPT_PATH,
            KLINE_MANIFEST_PATH,
            OI_MANIFEST_PATH,
        )
    }
    return record


def canonical(record: dict[str, Any]) -> str:
    return json.dumps(record, indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    path = ROOT / frozen.RECORD_PATH
    if not options.check and path.exists():
        raise SystemExit("the single frozen admission calculation has already been recorded")
    text = canonical(build())
    if options.check:
        stored = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if stored != text:
            raise SystemExit("candidate #1 frozen admission record does not replay")
        print("candidate #1 frozen admission replay: PASS")
        return
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {frozen.RECORD_PATH}")


if __name__ == "__main__":
    main()
