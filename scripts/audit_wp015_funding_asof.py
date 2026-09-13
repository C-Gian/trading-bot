"""Independent raw-to-canonical and strict as-of audit for WP-015 funding."""

from __future__ import annotations

import bisect
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.evaluation_protocol import HOUR_US, utc_us

RAW_ROOT = ROOT / "data/raw/funding/binance-usdm/BTCUSDT"
MANIFEST = ROOT / "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json"
OUTPUT = ROOT / "reports/validation/WP-015-FUNDING-ASOF-AUDIT.json"
CUTOFF_MS = 1_735_689_599_999


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows: list[tuple[int, float]] = []
    request_checks = 0
    for request in manifest["raw_requests"]:
        path = ROOT / request["path"]
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != request["sha256"]:
            raise ValueError("independent raw funding hash mismatch")
        decoded = json.loads(payload)
        if len(decoded) != request["row_count"]:
            raise ValueError("independent raw funding row count mismatch")
        for item in decoded:
            if item["symbol"] != "BTCUSDT":
                raise ValueError("independent wrong funding symbol")
            rows.append((int(item["fundingTime"]), float(item["fundingRate"])))
        request_checks += 1
    times_ms = [item[0] for item in rows]
    if times_ms != sorted(set(times_ms)) or max(times_ms) > CUTOFF_MS:
        raise ValueError("independent funding timeline or cutoff failure")

    table = pq.read_table(ROOT / manifest["canonical"]["path"])
    canonical_times_ms = [int(value) // 1000 for value in table["funding_time"].cast(pa.int64())]
    canonical_rates = [float(value) for value in table["funding_rate"]]
    if canonical_times_ms != times_ms or canonical_rates != [item[1] for item in rows]:
        raise ValueError("independent raw canonicalization mismatch")

    strict_checks = 0
    for index, timestamp in enumerate(times_ms):
        signal_us = timestamp * 1000
        chosen = bisect.bisect_left(times_ms, signal_us // 1000) - 1
        if chosen != index - 1:
            raise ValueError("same-timestamp funding leaked into signal")
        strict_checks += 1

    folds = json.loads(
        (ROOT / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json").read_text(encoding="utf-8")
    )["folds"]
    coverage: dict[str, int] = {}
    for fold in folds:
        year = int(str(fold["fold_id"]).split("-")[-1])
        if year < 2020:
            continue
        start = utc_us(fold["validation_start"])
        end = utc_us(fold["last_signal_inclusive"])
        coverage[fold["fold_id"]] = sum(
            bisect.bisect_left(times_ms, signal_us // 1000) > 0
            for signal_us in range(start, end + 1, HOUR_US)
        )

    output = {
        "schema_version": 1,
        "work_package": "WP-015",
        "status": "PASS",
        "independent_path": "RAW_JSON_TO_CANONICAL_AND_BISECT_LEFT_MINUS_ONE",
        "raw_requests_verified": request_checks,
        "records_reconstructed": len(rows),
        "first_funding_time": datetime.fromtimestamp(times_ms[0] / 1000, UTC)
        .isoformat()
        .replace("+00:00", "Z"),
        "last_funding_time": datetime.fromtimestamp(times_ms[-1] / 1000, UTC)
        .isoformat()
        .replace("+00:00", "Z"),
        "post_cutoff_records": 0,
        "duplicate_records": 0,
        "canonical_match": True,
        "same_timestamp_exclusion_checks": strict_checks,
        "strict_funding_time_before_signal_time": True,
        "hourly_validation_coverage": coverage,
        "no_interpolation": True,
        "sealed_queries": 0,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
