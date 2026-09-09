"""Independent order-flow oracle.

This path shares no aggregation code with the production builder. The builder computes
bucket boundaries by integer arithmetic over whole sorted numpy columns; the oracle
streams Parquet record batches, detects bucket changes as it goes, and marks quarantine
per row. Both use ``math.fsum``, which is exactly rounded, so agreement is bit-for-bit
rather than approximate.
"""

from __future__ import annotations

import hashlib
import json
from math import fsum
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .evaluation_protocol import HOUR_US
from .order_flow import (
    BALANCE,
    SUM_FIELDS,
    FlowBucket,
    OrderFlowError,
    content_hash,
    read_buckets,
)
from .wp004 import ROOT

MINUTE_US = 60_000_000
WIDTHS = {"1h": HOUR_US, "4h": 4 * HOUR_US}
SOURCE_MANIFEST_PATH = "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"


def _stream(root: Path) -> Any:
    """Yield one record batch at a time as plain Python lists, timestamps as integers."""
    manifest = json.loads((root / SOURCE_MANIFEST_PATH).read_text(encoding="utf-8"))
    path = root / manifest["files"]["canonical"]["path"]
    reader = pq.ParquetFile(path)
    for batch in reader.iter_batches(
        batch_size=131072, columns=["open_time", "open", "close", *SUM_FIELDS]
    ):
        stamps = batch.column("open_time").cast(pa.int64()).to_pylist()
        payload = {name: batch.column(name).to_pylist() for name in ("open", "close", *SUM_FIELDS)}
        yield stamps, payload


def oracle_buckets(timeframe: str, root: Path = ROOT) -> tuple[FlowBucket, ...]:
    """Rebuild one timeframe by streaming, without the builder's index arithmetic."""
    if timeframe not in WIDTHS:
        raise OrderFlowError("unsupported order-flow timeframe")
    width = WIDTHS[timeframe]
    expected = width // MINUTE_US
    buckets: list[FlowBucket] = []
    unsafe: set[int] = set()
    current: int | None = None
    pending: dict[str, list[float]] = {name: [] for name in SUM_FIELDS}
    first_open = last_close = 0.0
    minutes = 0
    previous = None

    def finalize() -> None:
        nonlocal minutes
        if current is None:
            return
        sums = {name: fsum(pending[name]) for name in SUM_FIELDS}
        share = sums["taker_base"] / sums["volume"] if sums["volume"] > 0 else None
        buckets.append(
            FlowBucket(
                open_us=current,
                source_minutes=minutes,
                complete=minutes == expected,
                quarantined=False,
                eligible=False,
                open=first_open,
                close=last_close,
                volume=sums["volume"],
                quote_volume=sums["quote_volume"],
                taker_base=sums["taker_base"],
                taker_quote=sums["taker_quote"],
                share=share,
            )
        )

    for stamps, payload in _stream(root):
        for index, open_us in enumerate(stamps):
            if previous is not None and open_us <= previous:
                raise OrderFlowError("canonical stream is not strictly increasing")
            previous = open_us
            if open_us % MINUTE_US:
                # An off-grid minute contaminates every bucket its interval touches.
                unsafe.add(open_us // width * width)
                unsafe.add((open_us + MINUTE_US - 1) // width * width)
            identifier = open_us // width * width
            if identifier != current:
                finalize()
                current = identifier
                minutes = 0
                first_open = float(payload["open"][index])
                pending = {name: [] for name in SUM_FIELDS}
            minutes += 1
            last_close = float(payload["close"][index])
            for name in SUM_FIELDS:
                pending[name].append(float(payload[name][index]))
    finalize()
    return tuple(
        FlowBucket(
            open_us=bucket.open_us,
            source_minutes=bucket.source_minutes,
            complete=bucket.complete,
            quarantined=bucket.open_us in unsafe,
            eligible=bucket.complete and bucket.open_us not in unsafe and bucket.share is not None,
            open=bucket.open,
            close=bucket.close,
            volume=bucket.volume,
            quote_volume=bucket.quote_volume,
            taker_base=bucket.taker_base,
            taker_quote=bucket.taker_quote,
            share=bucket.share,
        )
        for bucket in buckets
    )


def accepted_1h_cross_check(
    production: dict[str, tuple[FlowBucket, ...]], root: Path = ROOT
) -> dict[str, Any]:
    """The new bucketing must agree with the derived 1h file accepted back in WP-001.

    ``open``, ``close``, ``source_minutes`` and ``complete`` involve no float arithmetic,
    so they must match exactly. ``volume`` is compared numerically because the accepted
    file used a pairwise sum while this substrate uses an exactly rounded fsum.
    """
    manifest = json.loads((root / SOURCE_MANIFEST_PATH).read_text(encoding="utf-8"))
    record = manifest["files"]["1h"]
    table = pq.read_table(root / record["path"])
    times = table["open_time"].cast(pa.int64()).to_pylist()
    accepted = {
        int(open_us): values
        for open_us, *values in zip(
            times,
            table["open"].to_pylist(),
            table["close"].to_pylist(),
            table["volume"].to_pylist(),
            table["source_minutes"].to_pylist(),
            table["complete"].to_pylist(),
            strict=True,
        )
    }
    exact = 0
    price_mismatches = 0
    structure_mismatches = 0
    worst_volume_difference = 0.0
    missing = 0
    for bucket in production["1h"]:
        values = accepted.get(bucket.open_us)
        if values is None:
            missing += 1
            continue
        open_price, close_price, volume, minutes, complete = values
        if bucket.open != open_price or bucket.close != close_price:
            price_mismatches += 1
        elif bucket.source_minutes != minutes or bucket.complete != bool(complete):
            structure_mismatches += 1
        else:
            exact += 1
        worst_volume_difference = max(worst_volume_difference, abs(bucket.volume - float(volume)))
    return {
        "accepted_file": record["path"],
        "accepted_sha256": record["sha256"],
        "accepted_buckets": len(accepted),
        "compared_buckets": len(production["1h"]),
        "buckets_absent_from_accepted_file": missing,
        "exact_open_close_structure_matches": exact,
        "price_mismatches": price_mismatches,
        "structure_mismatches": structure_mismatches,
        "maximum_absolute_volume_difference": worst_volume_difference,
        "status": "PASS"
        if missing == price_mismatches == structure_mismatches == 0
        and worst_volume_difference < 1e-6
        else "FAIL",
    }


def _sample_indices(count: int, wanted: int = 64) -> list[int]:
    """Deterministic, identity-only sample positions used for the reconciliation record."""
    if count == 0:
        return []
    picks = {0, count - 1}
    for step in range(wanted):
        seed = f"WP007-ORDER-FLOW-RECONCILIATION|{count}|{step}".encode()
        picks.add(int(hashlib.sha256(seed).hexdigest(), 16) % count)
    return sorted(picks)


def reconcile(root: Path = ROOT, *, from_disk: bool = True) -> dict[str, Any]:
    """Reconcile the production substrate against the independent oracle, bit-for-bit."""
    from .order_flow import build_substrate

    production = (
        {timeframe: read_buckets(timeframe, root) for timeframe in WIDTHS}
        if from_disk
        else build_substrate(root)
    )
    oracle = {timeframe: oracle_buckets(timeframe, root) for timeframe in WIDTHS}
    timeframes = {}
    for timeframe in sorted(WIDTHS):
        left, right = production[timeframe], oracle[timeframe]
        mismatches = [
            index
            for index, (a, b) in enumerate(zip(left, right, strict=False))
            if a.as_record() != b.as_record()
        ]
        indices = _sample_indices(min(len(left), len(right)))
        edges = [0, len(left) - 1] if left else []
        anomaly = [index for index, bucket in enumerate(left) if bucket.quarantined][:8]
        timeframes[timeframe] = {
            "production_buckets": len(left),
            "oracle_buckets": len(right),
            "bucket_count_match": len(left) == len(right),
            "production_eligible": sum(bucket.eligible for bucket in left),
            "oracle_eligible": sum(bucket.eligible for bucket in right),
            "eligible_count_match": sum(bucket.eligible for bucket in left)
            == sum(bucket.eligible for bucket in right),
            "record_mismatches": len(mismatches),
            "first_mismatch_index": mismatches[0] if mismatches else None,
            "sampled_indices": indices,
            "sampled_values_match": all(
                left[index].as_record() == right[index].as_record() for index in indices
            ),
            "edge_indices": edges,
            "edge_values_match": all(
                left[index].as_record() == right[index].as_record() for index in edges
            ),
            "anomaly_bucket_indices": anomaly,
            "anomaly_values_match": all(
                left[index].as_record() == right[index].as_record() for index in anomaly
            ),
            "buy_dominant_eligible": sum(
                bucket.eligible and bucket.share is not None and bucket.share > BALANCE
                for bucket in left
            ),
        }
    production_hash = content_hash(production)
    oracle_hash = content_hash(oracle)
    cross_check = accepted_1h_cross_check(production, root)
    status = (
        "PASS"
        if production_hash == oracle_hash
        and cross_check["status"] == "PASS"
        and all(
            item["bucket_count_match"]
            and item["eligible_count_match"]
            and item["record_mismatches"] == 0
            and item["sampled_values_match"]
            and item["edge_values_match"]
            and item["anomaly_values_match"]
            for item in timeframes.values()
        )
        else "FAIL"
    )
    return {
        "version": "ORDER_FLOW_RECONCILIATION_V1",
        "status": status,
        "method": "INDEPENDENT_STREAMING_ORACLE_SHARES_NO_AGGREGATION_CODE",
        "arithmetic": "EXACTLY_ROUNDED_FSUM_SO_AGREEMENT_IS_BIT_FOR_BIT_NOT_TOLERANCE_BASED",
        "production_content_hash": production_hash,
        "oracle_content_hash": oracle_hash,
        "content_hash_match": production_hash == oracle_hash,
        "accepted_1h_cross_check": cross_check,
        "timeframes": timeframes,
    }
