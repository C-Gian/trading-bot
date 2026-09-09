"""Production order-flow feature substrate: BTCUSDT-SPOT-ORDERFLOW-DEV-v1.

Canonical data is read, never written. Buckets are UTC-aligned and aggregate the
canonical 1m rows they contain. A bucket's share is the ratio of summed taker volume
to summed total volume, never the mean of minute ratios.

Sums use ``math.fsum``, which is exactly rounded and therefore independent of addition
order. That is what lets a genuinely independent oracle reconcile bit-for-bit rather
than within a tolerance.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import fsum
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .evaluation_protocol import HOUR_US, utc_us
from .source_grid import unsafe_buckets
from .wp004 import ROOT

FEATURE_VERSION = "ORDER_FLOW_FEATURES_V1"
DATASET_ID = "BTCUSDT-SPOT-ORDERFLOW-DEV-v1"
MANIFEST_PATH = "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json"
SOURCE_MANIFEST_PATH = "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
CUTOFF_US = utc_us("2024-12-31T23:59:00Z")
MINUTE_US = 60_000_000
WIDTHS = {"1h": HOUR_US, "4h": 4 * HOUR_US}
FILES = {
    "1h": "data/derived/BTCUSDT-1h-orderflow-v1.parquet",
    "4h": "data/derived/BTCUSDT-4h-orderflow-v1.parquet",
}
SUM_FIELDS = ("volume", "quote_volume", "taker_base", "taker_quote")
COLUMNS = (
    "open_time",
    "source_minutes",
    "complete",
    "quarantined",
    "eligible",
    "open",
    "close",
    *SUM_FIELDS,
    "taker_buy_base_share",
)
BALANCE = 0.5
AGGREGATION = "EXACT_ROUNDED_FSUM_OF_CANONICAL_MINUTES_RATIO_OF_SUMS_NOT_MEAN_OF_RATIOS"


class OrderFlowError(ValueError):
    """The order-flow substrate failed a deterministic identity or eligibility gate."""


@dataclass(frozen=True)
class FlowBucket:
    """One completed UTC-aligned bucket. ``share`` is None when nothing traded."""

    open_us: int
    source_minutes: int
    complete: bool
    quarantined: bool
    eligible: bool
    open: float
    close: float
    volume: float
    quote_volume: float
    taker_base: float
    taker_quote: float
    share: float | None

    def as_record(self) -> dict[str, Any]:
        return {
            "open_time": self.open_us,
            "source_minutes": self.source_minutes,
            "complete": self.complete,
            "quarantined": self.quarantined,
            "eligible": self.eligible,
            "open": self.open,
            "close": self.close,
            "volume": self.volume,
            "quote_volume": self.quote_volume,
            "taker_base": self.taker_base,
            "taker_quote": self.taker_quote,
            "taker_buy_base_share": self.share,
        }


def content_hash(buckets: dict[str, tuple[FlowBucket, ...]]) -> str:
    """Encoding-independent identity: hash the records, not the Parquet bytes."""
    payload = {
        timeframe: [bucket.as_record() for bucket in series]
        for timeframe, series in sorted(buckets.items())
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _canonical_columns(root: Path) -> dict[str, Any]:
    manifest = json.loads((root / SOURCE_MANIFEST_PATH).read_text(encoding="utf-8"))
    path = root / manifest["files"]["canonical"]["path"]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != manifest["files"]["canonical"]["sha256"]:
        raise OrderFlowError("canonical bytes differ from the accepted manifest")
    table = pq.read_table(path, columns=["open_time", "open", "close", *SUM_FIELDS])
    times = table["open_time"].cast(pa.int64()).to_numpy()
    if np.any(times > CUTOFF_US) or np.any(np.diff(times) <= 0):
        raise OrderFlowError("invalid canonical timestamps")
    return {
        "manifest": manifest,
        "times": times,
        "columns": {name: table[name].to_numpy() for name in ("open", "close", *SUM_FIELDS)},
    }


def build_buckets(timeframe: str, source: dict[str, Any]) -> tuple[FlowBucket, ...]:
    """Aggregate canonical minutes into completed UTC-aligned buckets. Nothing is filled."""
    if timeframe not in WIDTHS:
        raise OrderFlowError("unsupported order-flow timeframe")
    width = WIDTHS[timeframe]
    times, columns = source["times"], source["columns"]
    identifiers = times // width * width
    starts = np.flatnonzero(np.concatenate(([True], identifiers[1:] != identifiers[:-1])))
    ends = np.append(starts[1:], len(identifiers))
    quarantined = unsafe_buckets(times, width)
    expected = width // MINUTE_US
    buckets = []
    for start, end in zip(starts.tolist(), ends.tolist(), strict=True):
        open_us = int(identifiers[start])
        minutes = end - start
        sums = {name: fsum(columns[name][start:end].tolist()) for name in SUM_FIELDS}
        complete = minutes == expected
        unsafe = open_us in quarantined
        # Ratio of summed taker volume to summed total volume; undefined when nothing traded.
        share = sums["taker_base"] / sums["volume"] if sums["volume"] > 0 else None
        buckets.append(
            FlowBucket(
                open_us=open_us,
                source_minutes=minutes,
                complete=complete,
                quarantined=unsafe,
                eligible=complete and not unsafe and share is not None,
                open=float(columns["open"][start]),
                close=float(columns["close"][end - 1]),
                volume=sums["volume"],
                quote_volume=sums["quote_volume"],
                taker_base=sums["taker_base"],
                taker_quote=sums["taker_quote"],
                share=share,
            )
        )
    return tuple(buckets)


def build_substrate(root: Path = ROOT) -> dict[str, tuple[FlowBucket, ...]]:
    source = _canonical_columns(root)
    return {timeframe: build_buckets(timeframe, source) for timeframe in WIDTHS}


def to_table(buckets: tuple[FlowBucket, ...]) -> pa.Table:
    records = [bucket.as_record() for bucket in buckets]
    schema = pa.schema(
        [
            ("open_time", pa.timestamp("us", tz="UTC")),
            ("source_minutes", pa.int64()),
            ("complete", pa.bool_()),
            ("quarantined", pa.bool_()),
            ("eligible", pa.bool_()),
            ("open", pa.float64()),
            ("close", pa.float64()),
            ("volume", pa.float64()),
            ("quote_volume", pa.float64()),
            ("taker_base", pa.float64()),
            ("taker_quote", pa.float64()),
            ("taker_buy_base_share", pa.float64()),
        ]
    )
    return pa.Table.from_pydict(
        {
            name: (
                pa.array([record["open_time"] for record in records], pa.int64()).cast(
                    pa.timestamp("us", tz="UTC")
                )
                if name == "open_time"
                else [record[name] for record in records]
            )
            for name in COLUMNS
        },
        schema=schema,
    )


def read_buckets(timeframe: str, root: Path = ROOT) -> tuple[FlowBucket, ...]:
    """Load a verified substrate table; the manifest hash is checked before any use."""
    manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    record = manifest["files"][timeframe]
    path = root / record["path"]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != record["sha256"]:
        raise OrderFlowError(f"order-flow substrate bytes differ from its manifest: {timeframe}")
    table = pq.read_table(path)
    if table.column_names != list(COLUMNS):
        raise OrderFlowError("order-flow substrate schema changed")
    times = table["open_time"].cast(pa.int64()).to_numpy()
    shares = table["taker_buy_base_share"].to_pylist()
    values = {name: table[name].to_pylist() for name in COLUMNS if name != "open_time"}
    return tuple(
        FlowBucket(
            open_us=int(times[index]),
            source_minutes=int(values["source_minutes"][index]),
            complete=bool(values["complete"][index]),
            quarantined=bool(values["quarantined"][index]),
            eligible=bool(values["eligible"][index]),
            open=float(values["open"][index]),
            close=float(values["close"][index]),
            volume=float(values["volume"][index]),
            quote_volume=float(values["quote_volume"][index]),
            taker_base=float(values["taker_base"][index]),
            taker_quote=float(values["taker_quote"][index]),
            share=None if shares[index] is None else float(shares[index]),
        )
        for index in range(len(times))
    )


def substrate_summary(buckets: dict[str, tuple[FlowBucket, ...]]) -> dict[str, Any]:
    summary = {}
    for timeframe, series in sorted(buckets.items()):
        summary[timeframe] = {
            "buckets": len(series),
            "complete": sum(bucket.complete for bucket in series),
            "quarantined": sum(bucket.quarantined for bucket in series),
            "eligible": sum(bucket.eligible for bucket in series),
            "null_share": sum(bucket.share is None for bucket in series),
            "buy_dominant_eligible": sum(
                bucket.eligible and bucket.share is not None and bucket.share > BALANCE
                for bucket in series
            ),
        }
    return summary
