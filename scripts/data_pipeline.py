"""Acquire official Binance monthly BTCUSDT 1m archives through the fixed cutoff."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import time
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.data.policy import CUTOFF, require_allowed

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m"
START = (2017, 8)
END = (2024, 12)
COLS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_base",
    "taker_quote",
    "ignore",
]


def months():
    y, m = START
    while (y, m) <= END:
        yield y, m
        m += 1
        y, m = (y + 1, 1) if m == 13 else (y, m)


def download(url: str, path: Path):
    if path.exists():
        return
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = r.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2**attempt)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def main():
    require_allowed("BTCUSDT", CUTOFF)
    raw = ROOT / "data/raw/binance/BTCUSDT/1m"
    rows = []
    sources = []
    for y, m in months():
        name = f"BTCUSDT-1m-{y}-{m:02d}.zip"
        p = raw / name
        url = f"{BASE}/{name}"
        download(url, p)
        sources.append(
            {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "url": url, "sha256": sha(p)}
        )
        with zipfile.ZipFile(p) as z, z.open(z.namelist()[0]) as f:
            for r in csv.reader(io.TextIOWrapper(f)):
                if not r or not r[0].isdigit():
                    continue
                ms = int(r[0])
                dt = datetime.fromtimestamp(ms / 1000, UTC)
                if dt <= CUTOFF:
                    rows.append(
                        (
                            dt,
                            *map(float, r[1:6]),
                            int(r[6]),
                            float(r[7]),
                            int(r[8]),
                            float(r[9]),
                            float(r[10]),
                        )
                    )
    rows.sort(key=lambda x: x[0])
    dup = len(rows) - len({r[0] for r in rows})
    invalid = sum(
        not (r[2] >= max(r[1], r[4]) and r[3] <= min(r[1], r[4]) and r[5] >= 0) for r in rows
    )
    gaps = sum(
        int((b[0] - a[0]).total_seconds() / 60) - 1
        for a, b in zip(rows, rows[1:])
        if (b[0] - a[0]).total_seconds() > 60
    )
    schema = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "taker_base",
        "taker_quote",
    ]
    table = pa.Table.from_pylist([dict(zip(schema, r)) for r in rows])
    cp = ROOT / "data/canonical/BTCUSDT-1m.parquet"
    cp.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, cp, compression="zstd")
    counts = {}
    incomplete = {}
    files = {"canonical": {"path": "data/canonical/BTCUSDT-1m.parquet", "sha256": sha(cp)}}
    for tf, mins in [("1h", 60), ("4h", 240)]:
        import pyarrow.compute as pc

        epoch_us = pc.cast(table["open_time"], pa.int64())
        width_us = mins * 60 * 1_000_000
        bucket_index = pc.cast(pc.floor(pc.divide(epoch_us, width_us)), pa.int64())
        bucket_us = pc.multiply(bucket_index, width_us)
        bucket = pc.cast(bucket_us, pa.timestamp("us", tz="UTC"))
        t = table.append_column("bucket", bucket)
        out = (
            t.group_by("bucket", use_threads=False)
            .aggregate(
                [
                    ("open", "first"),
                    ("high", "max"),
                    ("low", "min"),
                    ("close", "last"),
                    ("volume", "sum"),
                    ("open_time", "count"),
                ]
            )
            .rename_columns(
                ["open_time", "open", "high", "low", "close", "volume", "source_minutes"]
            )
        )
        out = out.append_column("complete", pc.equal(out["source_minutes"], mins)).sort_by(
            "open_time"
        )
        p = ROOT / f"data/derived/BTCUSDT-{tf}.parquet"
        pq.write_table(out, p, compression="zstd")
        counts[tf] = len(out)
        incomplete[tf] = pc.sum(pc.invert(out["complete"])).as_py()
        files[tf] = {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(p)}
    logical = hashlib.sha256()
    [logical.update((",".join(map(str, r)) + "\n").encode()) for r in rows]
    manifest = {
        "manifest_id": "BTCUSDT-SPOT-1M-DEV-v1",
        "dataset_version": 1,
        "source": {"provider": "Binance", "archive_base": BASE, "raw_objects": sources},
        "symbol": "BTCUSDT",
        "market_type": "spot",
        "canonical_resolution": "1m",
        "coverage": {
            "start": rows[0][0].isoformat().replace("+00:00", "Z"),
            "end": rows[-1][0].isoformat().replace("+00:00", "Z"),
        },
        "row_counts": {"1m": len(rows), **counts},
        "files": files,
        "content_hash": {"algorithm": "sha256-canonical-csv-v1", "value": logical.hexdigest()},
        "schema_version": 1,
        "integrity": {
            "duplicates": dup,
            "missing_minutes": gaps,
            "invalid_ohlcv": invalid,
            "incomplete_windows": incomplete,
        },
        "derivation": {
            "1h": "UTC aligned from 1m; incomplete flagged",
            "4h": "UTC aligned from 1m; incomplete flagged",
        },
        "code_reference": "work/wp-001-foundation-data",
    }
    mp = ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
    mp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (ROOT / "data/reports/WP-001-INTEGRITY.md").write_text(
        f"# Dataset integrity\n\nStatus: {'PASS' if dup == invalid == 0 else 'FAIL'}\n\n- coverage: {manifest['coverage']['start']} to {manifest['coverage']['end']}\n- rows: {len(rows)}\n- duplicates: {dup}\n- missing minutes: {gaps}\n- invalid OHLCV: {invalid}\n- 1h rows: {counts['1h']}\n- 4h rows: {counts['4h']}\n- incomplete 1h/4h windows: {incomplete['1h']} / {incomplete['4h']}\n- manifest: {manifest['manifest_id']}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
