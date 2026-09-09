"""Deterministic integrity audit of the accepted canonical Binance taker fields.

Nothing here modifies canonical data. The audit reads every canonical 1m row, then
independently re-verifies the four flow fields against the immutable raw Binance
archives for a sample whose selection rule is frozen before inspection and uses only
timestamp/label/count identity — never a value.

A ratio outside its accounting range is counted and reported, never clamped.
"""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .evaluation_protocol import utc_us
from .source_grid import grid_audit
from .wp004 import ROOT

AUDIT_VERSION = "ORDER_FLOW_INTEGRITY_V1"
SAMPLE_RULE_ID = "WP007-ORDER-FLOW-SAMPLE-V1"
MANIFEST_PATH = "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
GRID_PATH = "reports/validation/WP-004-SOURCE-GRID.json"
CUTOFF_US = utc_us("2024-12-31T23:59:00Z")
MINUTE_US = 60_000_000
FLOW_FIELDS = ("volume", "quote_volume", "taker_base", "taker_quote")
RAW_INDEX = {"open_time": 0, "volume": 5, "quote_volume": 7, "taker_base": 9, "taker_quote": 10}
# Float-parity tolerance for the containment identities. Both sides are independent
# decimal strings parsed by the acquisition script's float(); correct rounding is
# monotone, so an exact violation would indicate a real source or pipeline defect.
ABSOLUTE_TOLERANCE = 1e-9
RELATIVE_TOLERANCE = 1e-12
ANOMALY_MONTHS = ("2017-12", "2018-02")


class OrderFlowAuditError(ValueError):
    """The canonical taker substrate failed a deterministic integrity gate."""


def _instant(value: int) -> str:
    return (
        (datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=int(value)))
        .isoformat()
        .replace("+00:00", "Z")
    )


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _selector(*parts: str) -> int:
    """Deterministic index from identity only; no market value can influence it."""
    return int(hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest(), 16)


def _quarter(month: str) -> str:
    year, number = month.split("-")
    return f"{year}Q{(int(number) - 1) // 3 + 1}"


def _month_of(path: str) -> str:
    return path.rsplit("-", 2)[-2] + "-" + path.rsplit("-", 1)[-1].removesuffix(".zip")


def sample_plan(root: Path = ROOT) -> dict[str, Any]:
    """Freeze which minutes will be re-verified, using only archive labels and row counts."""
    manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    months: dict[str, list[dict[str, str]]] = {}
    for item in manifest["source"]["raw_objects"]:
        months.setdefault(_quarter(_month_of(item["path"])), []).append(item)
    quarters = []
    for quarter in sorted(months):
        available = sorted(months[quarter], key=lambda item: item["path"])
        chosen = available[_selector(SAMPLE_RULE_ID, quarter) % len(available)]
        quarters.append(
            {
                "quarter": quarter,
                "months_available": len(available),
                "selected_path": chosen["path"],
                "selected_sha256": chosen["sha256"],
            }
        )
    return {
        "rule_id": SAMPLE_RULE_ID,
        "selection_inputs": "ARCHIVE_LABEL_AND_ROW_COUNT_ONLY_NO_MARKET_VALUE",
        "outcome_conditioned_selection": False,
        "quarters": quarters,
        "anomaly_months": list(ANOMALY_MONTHS),
        "anomaly_policy": "EVERY_OFF_GRID_ROW_IN_BOTH_KNOWN_ANOMALY_ARCHIVES_IS_REVERIFIED",
        "plan_sha256": canonical_hash(
            [
                SAMPLE_RULE_ID,
                [[item["quarter"], item["selected_path"]] for item in quarters],
                list(ANOMALY_MONTHS),
            ]
        ),
    }


def canonical_audit(root: Path = ROOT) -> dict[str, Any]:
    """Audit every canonical 1m row for flow-field validity. No value is repaired."""
    manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    record = manifest["files"]["canonical"]
    path = root / record["path"]
    if _file_hash(path) != record["sha256"]:
        raise OrderFlowAuditError("canonical byte hash differs from the accepted manifest")
    table = pq.read_table(path, columns=["open_time", *FLOW_FIELDS])
    times = table["open_time"].cast(pa.int64()).to_numpy()
    volume = table["volume"].to_numpy()
    quote_volume = table["quote_volume"].to_numpy()
    taker_base = table["taker_base"].to_numpy()
    taker_quote = table["taker_quote"].to_numpy()
    if len(times) != manifest["row_counts"]["1m"]:
        raise OrderFlowAuditError("canonical row count differs from the accepted manifest")
    ordered = bool(np.all(np.diff(times) > 0))
    finite = {
        name: bool(np.isfinite(values).all())
        for name, values in zip(FLOW_FIELDS, (volume, quote_volume, taker_base, taker_quote))
    }
    negative = {
        name: int((values < 0).sum())
        for name, values in zip(FLOW_FIELDS, (volume, quote_volume, taker_base, taker_quote))
    }
    base_excess = taker_base - volume
    quote_excess = taker_quote - quote_volume
    base_tolerance = ABSOLUTE_TOLERANCE + RELATIVE_TOLERANCE * np.abs(volume)
    quote_tolerance = ABSOLUTE_TOLERANCE + RELATIVE_TOLERANCE * np.abs(quote_volume)
    traded = volume > 0
    quoted = quote_volume > 0
    ratio = np.divide(taker_base, volume, out=np.zeros_like(volume), where=traded)
    invalid_ratio = int(np.count_nonzero(traded & ((ratio < 0.0) | (ratio > 1.0))))
    # Count missing minutes exactly as the accepted manifest does: only intervals wider
    # than one minute contribute. One sub-minute interval exists inside the known
    # off-grid anomaly and is quarantined rather than treated as a negative gap.
    deltas = np.diff(times)
    wide = deltas[deltas > MINUTE_US]
    gaps = len(wide)
    missing = int(np.sum(wide // MINUTE_US - 1))
    sub_minute = int(np.count_nonzero(deltas < MINUTE_US))
    grid = grid_audit(times)
    expected_grid = json.loads((root / GRID_PATH).read_text(encoding="utf-8"))
    return {
        "audit_version": AUDIT_VERSION,
        "dataset": {
            "manifest_id": manifest["manifest_id"],
            "content_hash": manifest["content_hash"]["value"],
            "canonical_sha256": record["sha256"],
            "rows": len(times),
        },
        "cutoff": {
            "development_cutoff": "2024-12-31T23:59:00Z",
            "maximum_open_time": _instant(int(times[-1])),
            "post_cutoff_rows": int(np.count_nonzero(times > CUTOFF_US)),
            "post_cutoff_bytes_read": False,
        },
        "timestamps": {
            "strictly_increasing_and_unique": ordered,
            "gap_intervals": gaps,
            "missing_minutes": missing,
            "manifest_missing_minutes": manifest["integrity"]["missing_minutes"],
            "missing_minutes_match_manifest": missing == manifest["integrity"]["missing_minutes"],
            "sub_minute_intervals": sub_minute,
            "missing_minutes_filled": False,
        },
        "finite": finite,
        "negative_values": negative,
        "containment": {
            "policy": "COUNT_AND_REPORT_NEVER_CLAMP",
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "relative_tolerance": RELATIVE_TOLERANCE,
            "taker_base_exceeds_volume_exact": int(np.count_nonzero(base_excess > 0)),
            "taker_base_exceeds_volume_beyond_tolerance": int(
                np.count_nonzero(base_excess > base_tolerance)
            ),
            "taker_quote_exceeds_quote_volume_exact": int(np.count_nonzero(quote_excess > 0)),
            "taker_quote_exceeds_quote_volume_beyond_tolerance": int(
                np.count_nonzero(quote_excess > quote_tolerance)
            ),
            "maximum_base_excess": float(base_excess.max()),
            "maximum_quote_excess": float(quote_excess.max()),
        },
        "counts": {
            "zero_volume_rows": int(np.count_nonzero(volume == 0)),
            "zero_quote_volume_rows": int(np.count_nonzero(quote_volume == 0)),
            "zero_volume_with_nonzero_taker_base": int(
                np.count_nonzero((volume == 0) & (taker_base != 0))
            ),
            "zero_quote_volume_with_nonzero_taker_quote": int(
                np.count_nonzero((quote_volume == 0) & (taker_quote != 0))
            ),
            "tradable_rows": int(np.count_nonzero(traded)),
            "quoted_rows": int(np.count_nonzero(quoted)),
            "invalid_taker_ratio_rows": invalid_ratio,
            "clamped_ratios": 0,
        },
        "quarantine": {
            "policy": grid["policy"],
            "off_grid_rows": grid["off_grid_rows"],
            "quarantined_1h_buckets": grid["quarantined_1h_buckets"],
            "quarantined_4h_buckets": grid["quarantined_4h_buckets"],
            "repairs_or_fills": grid["repairs_or_fills"],
            "matches_accepted_wp004_audit": grid == expected_grid,
        },
    }


def _archive_rows(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != 1 or not names[0].endswith(".csv"):
            raise OrderFlowAuditError("unexpected official archive layout")
        with archive.open(names[0]) as handle:
            rows = [
                row
                for row in csv.reader(line.decode("utf-8") for line in handle)
                if row and row[0].isdigit()
            ]
    if any(len(row) < 11 for row in rows):
        raise OrderFlowAuditError("raw Binance column layout is incomplete")
    return rows


def _compare(
    rows: list[list[str]],
    indices: list[int],
    times: np.ndarray,
    columns: dict[str, np.ndarray],
    mismatches: Counter[str],
) -> int:
    compared = 0
    for index in indices:
        row = rows[index]
        raw_us = int(row[RAW_INDEX["open_time"]]) * 1000
        position = int(np.searchsorted(times, raw_us))
        if position >= len(times) or int(times[position]) != raw_us:
            mismatches["open_time"] += 1
            continue
        for name in FLOW_FIELDS:
            # Identical parsing semantics to the acquisition script: float(text).
            if float(columns[name][position]) != float(row[RAW_INDEX[name]]):
                mismatches[name] += 1
        compared += 1
    return compared


def source_provenance_sample(root: Path = ROOT) -> dict[str, Any]:
    """Re-verify the flow fields against immutable raw archives on the frozen sample."""
    manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    plan = sample_plan(root)
    accepted = {item["path"]: item for item in manifest["source"]["raw_objects"]}
    canonical_path = root / manifest["files"]["canonical"]["path"]
    table = pq.read_table(canonical_path, columns=["open_time", *FLOW_FIELDS])
    times = table["open_time"].cast(pa.int64()).to_numpy()
    columns = {name: table[name].to_numpy() for name in FLOW_FIELDS}
    mismatches: Counter[str] = Counter()
    archives = []
    samples = []
    quarter_rows = 0
    for item in plan["quarters"]:
        relative = item["selected_path"]
        path = root / relative
        digest = _file_hash(path)
        if digest != accepted[relative]["sha256"]:
            raise OrderFlowAuditError(f"raw archive hash mismatch: {relative}")
        rows = _archive_rows(path)
        index = _selector(SAMPLE_RULE_ID, item["quarter"], relative) % len(rows)
        quarter_rows += _compare(rows, [index], times, columns, mismatches)
        row = rows[index]
        samples.append(
            {
                "quarter": item["quarter"],
                "archive": relative,
                "archive_sha256": digest,
                "row_index": index,
                "rows_in_archive": len(rows),
                "open_time": _instant(int(row[RAW_INDEX["open_time"]]) * 1000),
                "raw": {name: row[RAW_INDEX[name]] for name in FLOW_FIELDS},
            }
        )
        archives.append(
            {
                "path": relative,
                "accepted_sha256": accepted[relative]["sha256"],
                "observed_sha256": digest,
                "rows": len(rows),
                "role": "QUARTERLY_SAMPLE",
            }
        )
    anomaly_rows = 0
    for month in ANOMALY_MONTHS:
        relative = next(name for name in accepted if name.endswith(f"{month}.zip"))
        path = root / relative
        digest = _file_hash(path)
        if digest != accepted[relative]["sha256"]:
            raise OrderFlowAuditError(f"raw archive hash mismatch: {relative}")
        rows = _archive_rows(path)
        indices = [
            index for index, row in enumerate(rows) if int(row[RAW_INDEX["open_time"]]) % 60_000
        ]
        anomaly_rows += _compare(rows, indices, times, columns, mismatches)
        archives.append(
            {
                "path": relative,
                "accepted_sha256": accepted[relative]["sha256"],
                "observed_sha256": digest,
                "rows": len(rows),
                "role": "OFF_GRID_ANOMALY_INTERVAL",
            }
        )
    return {
        "audit_version": AUDIT_VERSION,
        "sample_plan": plan,
        "parsing_semantics": "PYTHON_FLOAT_OF_RAW_CSV_TEXT_IDENTICAL_TO_ACQUISITION",
        "third_party_data_used": False,
        "archives": archives,
        "quarterly_rows_compared": quarter_rows,
        "anomaly_rows_compared": anomaly_rows,
        "total_rows_compared": quarter_rows + anomaly_rows,
        "field_mismatches": dict(sorted(mismatches.items())),
        "samples": samples,
        "status": "PASS" if not mismatches else "FAIL",
    }


def order_flow_integrity(root: Path = ROOT) -> dict[str, Any]:
    """Combine the full-column audit and the frozen raw sample into one verdict."""
    audit = canonical_audit(root)
    provenance = source_provenance_sample(root)
    containment = audit["containment"]
    counts = audit["counts"]
    violations = {
        "negative_values": sum(audit["negative_values"].values()),
        "non_finite_fields": sum(not value for value in audit["finite"].values()),
        "taker_base_exceeds_volume": containment["taker_base_exceeds_volume_beyond_tolerance"],
        "taker_quote_exceeds_quote_volume": containment[
            "taker_quote_exceeds_quote_volume_beyond_tolerance"
        ],
        "invalid_taker_ratio_rows": counts["invalid_taker_ratio_rows"],
        "zero_volume_with_nonzero_taker_base": counts["zero_volume_with_nonzero_taker_base"],
        "post_cutoff_rows": audit["cutoff"]["post_cutoff_rows"],
        "provenance_field_mismatches": sum(provenance["field_mismatches"].values()),
    }
    blocking = sum(violations.values())
    structural = (
        audit["timestamps"]["strictly_increasing_and_unique"]
        and audit["timestamps"]["missing_minutes_match_manifest"]
        and audit["quarantine"]["matches_accepted_wp004_audit"]
        and provenance["status"] == "PASS"
    )
    status = "PASS" if blocking == 0 and structural else "FAIL"
    return {
        "audit_version": AUDIT_VERSION,
        "status": status,
        "material_violations": blocking,
        "violations": violations,
        "canonical_audit": audit,
        "source_provenance_sample": provenance,
        "canonical_data_modified": False,
        "interpretation": (
            "Exchange-reported taker buy volume on Binance Spot. It is a venue-level proxy for "
            "aggressive buy-side participation, not market-wide order flow, investor intent, "
            "signed cross-venue demand, or evidence of causality."
        ),
    }
