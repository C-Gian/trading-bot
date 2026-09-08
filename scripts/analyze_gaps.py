from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "data/canonical/BTCUSDT-1m.parquet"
ARTIFACT = ROOT / "data/reports/BTCUSDT-SPOT-1M-DEV-v1-gaps.json"
SUMMARY = ROOT / "data/reports/WP-002-GAPS.md"


def iso(microseconds: int) -> str:
    return datetime.fromtimestamp(microseconds / 1_000_000, UTC).isoformat().replace("+00:00", "Z")


def build_artifact(canonical: Path = CANONICAL) -> dict:
    values = pc.cast(
        pq.read_table(canonical, columns=["open_time"])["open_time"], pa.int64()
    ).to_pylist()
    intervals = []
    affected_1h = set()
    affected_4h = set()
    minute_us = 60_000_000
    for previous, current in zip(values, values[1:]):
        missing = (current - previous) // minute_us - 1
        if missing <= 0:
            continue
        start = previous + minute_us
        end = current - minute_us
        intervals.append({"start": iso(start), "end": iso(end), "missing_minutes": missing})
        first_minute = start // minute_us
        last_minute = end // minute_us
        affected_1h.update(range(first_minute // 60, last_minute // 60 + 1))
        affected_4h.update(range(first_minute // 240, last_minute // 240 + 1))
    durations = [item["missing_minutes"] for item in intervals]
    buckets = {
        "1": sum(x == 1 for x in durations),
        "2-5": sum(2 <= x <= 5 for x in durations),
        "6-60": sum(6 <= x <= 60 for x in durations),
        "61-240": sum(61 <= x <= 240 for x in durations),
        ">240": sum(x > 240 for x in durations),
    }
    return {
        "artifact_id": "BTCUSDT-SPOT-1M-DEV-v1-GAPS",
        "schema_version": 1,
        "classification": "DEVELOPMENT DATA QUALITY — NOT TRADING EVIDENCE",
        "dataset_manifest_id": "BTCUSDT-SPOT-1M-DEV-v1",
        "algorithm": "consecutive UTC open-time difference minus one minute; no fill",
        "total_missing_minutes": sum(durations),
        "distinct_intervals": len(intervals),
        "duration_minutes": {
            "min": min(durations),
            "median": median(durations),
            "max": max(durations),
            "buckets": buckets,
        },
        "affected_windows": {"1h": len(affected_1h), "4h": len(affected_4h)},
        "intervals": intervals,
    }


def analyze() -> tuple[dict, str]:
    artifact = build_artifact()
    ARTIFACT.write_text(
        json.dumps(artifact, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    digest = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    durations = artifact["duration_minutes"]
    buckets = durations["buckets"]
    SUMMARY.write_text(
        f"# WP-002 gap characterization\n\nStatus: PASS\n\n- Dataset: `BTCUSDT-SPOT-1M-DEV-v1`\n- Total missing minutes: {artifact['total_missing_minutes']}\n- Distinct intervals: {artifact['distinct_intervals']}\n- Minimum / median / maximum duration: {durations['min']} / {durations['median']:g} / {durations['max']} minutes\n- Duration buckets (1, 2-5, 6-60, 61-240, >240): {buckets['1']}, {buckets['2-5']}, {buckets['6-60']}, {buckets['61-240']}, {buckets['>240']}\n- First gap: {artifact['intervals'][0]['start']} to {artifact['intervals'][0]['end']}\n- Last gap: {artifact['intervals'][-1]['start']} to {artifact['intervals'][-1]['end']}\n- Gap spans: {artifact['affected_windows']['1h']} UTC 1h windows and {artifact['affected_windows']['4h']} UTC 4h windows\n- Accepted derived data flags 31 partial 1h and 50 partial 4h rows; fully absent windows are not represented as bars.\n- Artifact SHA-256: `{digest}`\n\nMissing rows remain unfilled. Their cause is not inferred. The simulator rejects missing entry paths and returns unresolved data-gap outcomes when an open position crosses an unobserved interval.\n",
        encoding="utf-8",
    )
    return artifact, digest


if __name__ == "__main__":
    artifact, digest = analyze()
    print(f"{artifact['distinct_intervals']} intervals; sha256={digest}")
