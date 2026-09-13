"""Official Binance USD-M settled-funding acquisition and strict point-in-time lookup."""

from __future__ import annotations

import bisect
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

from .artifacts import write_parquet
from .wp004 import ROOT

VERSION = "PERPETUAL_FUNDING_CONTEXT_V1"
FEATURE = "LATEST_SETTLED_FUNDING_RATE"
SOURCE = "BINANCE_USDM_FUTURES_PUBLIC_MARKET_DATA"
ENDPOINT = "https://fapi.binance.com/fapi/v1/fundingRate"
SYMBOL = "BTCUSDT"
LIMIT = 1000
START_MS = 1_546_300_800_000
CUTOFF_MS = 1_735_689_599_999
CUTOFF_ISO = "2024-12-31T23:59:59.999Z"
RAW_ROOT = "data/raw/funding/binance-usdm/BTCUSDT"
CANONICAL_PATH = "data/derived/BTCUSDT-USDM-settled-funding-v1.parquet"
REQUEST_INDEX_PATH = "data/derived/BTCUSDT-USDM-funding-request-index-v1.parquet"
MANIFEST_PATH = "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json"
INTEGRITY_PATH = "reports/validation/WP-015-FUNDING-INTEGRITY.json"
PARSER_VERSION = "BINANCE_USDM_SETTLED_FUNDING_V1"
MAX_NATURAL_GAP_MS = 8 * 60 * 60 * 1000 + 60_000

FUNDING_SCHEMA = pa.schema(
    [
        ("funding_time", pa.timestamp("us", tz="UTC"), False),
        ("funding_rate", pa.float64(), False),
    ]
)
REQUEST_SCHEMA = pa.schema(
    [
        ("page", pa.int32(), False),
        ("start_time_ms", pa.int64(), False),
        ("end_time_ms", pa.int64(), False),
        ("limit", pa.int32(), False),
        ("row_count", pa.int32(), False),
        ("first_funding_time_ms", pa.int64()),
        ("last_funding_time_ms", pa.int64()),
        ("request_url", pa.string(), False),
        ("raw_path", pa.string(), False),
        ("response_sha256", pa.string(), False),
        ("retrieval_time", pa.timestamp("us", tz="UTC"), False),
    ]
)


class FundingDataError(ValueError):
    """Funding source or point-in-time invariants were violated."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def request_params(start_ms: int) -> dict[str, int | str]:
    if start_ms < 0 or start_ms > CUTOFF_MS + 1:
        raise FundingDataError("funding request start escaped frozen bounds")
    return {
        "symbol": SYMBOL,
        "startTime": start_ms,
        "endTime": CUTOFF_MS,
        "limit": LIMIT,
    }


def request_url(start_ms: int) -> str:
    return f"{ENDPOINT}?{urlencode(request_params(start_ms))}"


def parse_response(payload: bytes) -> list[dict[str, Any]]:
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FundingDataError("funding response is not JSON") from error
    if not isinstance(decoded, list):
        raise FundingDataError(f"funding endpoint did not return records: {decoded!r}")
    records: list[dict[str, Any]] = []
    previous = -1
    for item in decoded:
        if not isinstance(item, dict) or item.get("symbol") != SYMBOL:
            raise FundingDataError("funding response contains wrong symbol or shape")
        if "fundingTime" not in item or "fundingRate" not in item:
            raise FundingDataError("funding response lacks settled time/rate")
        timestamp = int(item["fundingTime"])
        if timestamp <= previous:
            raise FundingDataError("duplicate or backward funding timestamp in response")
        if timestamp > CUTOFF_MS:
            raise FundingDataError("post-cutoff funding record returned")
        try:
            rate = Decimal(str(item["fundingRate"]))
        except InvalidOperation as error:
            raise FundingDataError("invalid funding rate") from error
        if not rate.is_finite():
            raise FundingDataError("non-finite funding rate")
        records.append(
            {"funding_time_ms": timestamp, "funding_rate_text": str(item["fundingRate"])}
        )
        previous = timestamp
    return records


def acquire(root: Path = ROOT) -> dict[str, Any]:
    raw_root = root / RAW_ROOT
    raw_root.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(
        headers={"User-Agent": "trading-bot-wp015/1.0"},
        timeout=90,
        follow_redirects=True,
    )
    cursor = START_MS
    page = total = reused = fetched = 0
    while cursor <= CUTOFF_MS:
        page += 1
        identity = sha256_bytes(
            json.dumps(request_params(cursor), sort_keys=True, separators=(",", ":")).encode()
        )[:16]
        raw_path = raw_root / f"page-{page:04d}-{identity}.json"
        meta_path = raw_root / f"page-{page:04d}-{identity}.meta.json"
        if raw_path.is_file() and meta_path.is_file():
            payload = raw_path.read_bytes()
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta["request_url"] != request_url(cursor) or meta[
                "response_sha256"
            ] != sha256_bytes(payload):
                raise FundingDataError("cached funding request identity mismatch")
            reused += 1
        else:
            response = client.get(request_url(cursor))
            if response.status_code != 200:
                raise FundingDataError(
                    f"official Binance funding source failed: HTTP {response.status_code}"
                )
            payload = response.content
            raw_path.write_bytes(payload)
            meta_path.write_text(
                json.dumps(
                    {
                        "endpoint": ENDPOINT,
                        "request_url": request_url(cursor),
                        "params": request_params(cursor),
                        "response_sha256": sha256_bytes(payload),
                        "retrieval_time_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            fetched += 1
        records = parse_response(payload)
        total += len(records)
        if len(records) > LIMIT:
            raise FundingDataError("funding endpoint exceeded page limit")
        if not records:
            break
        next_cursor = records[-1]["funding_time_ms"] + 1
        if next_cursor <= cursor:
            raise FundingDataError("funding pagination did not advance")
        cursor = next_cursor
    client.close()
    return {"pages": page, "records": total, "fetched": fetched, "reused": reused}


def raw_records(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_root = root / RAW_ROOT
    raw_files = sorted(
        path for path in raw_root.glob("page-*.json") if not path.name.endswith(".meta.json")
    )
    if not raw_files:
        raise FundingDataError("no official funding responses are installed")
    records: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    expected_start = START_MS
    for page, raw_path in enumerate(raw_files, 1):
        meta_path = raw_path.with_name(raw_path.stem + ".meta.json")
        if not meta_path.is_file():
            raise FundingDataError("funding response lacks request metadata")
        payload = raw_path.read_bytes()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta["params"] != request_params(expected_start):
            raise FundingDataError("funding pagination parameters are not deterministic")
        if meta["request_url"] != request_url(expected_start):
            raise FundingDataError("funding request URL drifted")
        if meta["response_sha256"] != sha256_bytes(payload):
            raise FundingDataError("funding raw response hash mismatch")
        chunk = parse_response(payload)
        if records and chunk and chunk[0]["funding_time_ms"] <= records[-1]["funding_time_ms"]:
            raise FundingDataError("duplicate or backward timestamp across funding pages")
        retrieval = datetime.fromisoformat(meta["retrieval_time_utc"])
        requests.append(
            {
                "page": page,
                "start_time_ms": expected_start,
                "end_time_ms": CUTOFF_MS,
                "limit": LIMIT,
                "row_count": len(chunk),
                "first_funding_time_ms": chunk[0]["funding_time_ms"] if chunk else None,
                "last_funding_time_ms": chunk[-1]["funding_time_ms"] if chunk else None,
                "request_url": meta["request_url"],
                "raw_path": raw_path.relative_to(root).as_posix(),
                "response_sha256": meta["response_sha256"],
                "retrieval_time": retrieval,
            }
        )
        records.extend(chunk)
        if not chunk:
            if page != len(raw_files):
                raise FundingDataError("funding cache continues after terminal page")
            break
        expected_start = chunk[-1]["funding_time_ms"] + 1
    times = [record["funding_time_ms"] for record in records]
    if len(times) != len(set(times)):
        raise FundingDataError("duplicate funding settlement record")
    gaps = [b - a for a, b in zip(times, times[1:], strict=False) if b - a > MAX_NATURAL_GAP_MS]
    if gaps:
        raise FundingDataError(f"unexplained funding settlement gaps: {gaps[:5]}")
    return records, requests


def build(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    source, requests = raw_records(root)
    canonical = [
        {
            "funding_time": datetime.fromtimestamp(row["funding_time_ms"] / 1000, UTC),
            "funding_rate": float(Decimal(row["funding_rate_text"])),
        }
        for row in source
    ]
    artifact = write_parquet(
        root / CANONICAL_PATH,
        canonical,
        schema=FUNDING_SCHEMA,
        sort_key=["funding_time"],
        root=root,
    )
    request_index = write_parquet(
        root / REQUEST_INDEX_PATH,
        requests,
        schema=REQUEST_SCHEMA,
        sort_key=["page"],
        root=root,
    )
    times = [row["funding_time_ms"] for row in source]
    intervals = [b - a for a, b in zip(times, times[1:], strict=False)]
    raw_manifest = [
        {
            "page": item["page"],
            "path": item["raw_path"],
            "sha256": file_sha256(root / item["raw_path"]),
            "response_sha256": item["response_sha256"],
            "row_count": item["row_count"],
            "start_time_ms": item["start_time_ms"],
            "end_time_ms": item["end_time_ms"],
            "first_funding_time_ms": item["first_funding_time_ms"],
            "last_funding_time_ms": item["last_funding_time_ms"],
        }
        for item in requests
    ]
    manifest = {
        "schema_version": 1,
        "manifest_id": "BTCUSDT-USDM-FUNDING-DEV-v1",
        "version": VERSION,
        "contract": "docs/contracts/PERPETUAL_FUNDING_CONTEXT_V1.md",
        "source": {
            "name": SOURCE,
            "endpoint": ENDPOINT,
            "method": "GET",
            "credential_free": True,
        },
        "symbol": SYMBOL,
        "informational_only": True,
        "traded_instrument": "BTCUSDT_SPOT",
        "request_ceiling": CUTOFF_ISO,
        "pagination": "ASCENDING_LIMIT_1000_NEXT_START_LAST_FUNDING_TIME_PLUS_1MS",
        "parser_version": PARSER_VERSION,
        "feature_columns": [FEATURE],
        "excluded_source_fields": ["markPrice"],
        "records": len(source),
        "first_funding_time": datetime.fromtimestamp(times[0] / 1000, UTC)
        .isoformat()
        .replace("+00:00", "Z"),
        "last_funding_time": datetime.fromtimestamp(times[-1] / 1000, UTC)
        .isoformat()
        .replace("+00:00", "Z"),
        "raw_requests": raw_manifest,
        "canonical": artifact,
        "request_index": request_index,
    }
    integrity = {
        "schema_version": 1,
        "work_package": "WP-015",
        "status": "PASS",
        "source": SOURCE,
        "endpoint": ENDPOINT,
        "records": len(source),
        "pages": len(requests),
        "first_funding_time_ms": times[0],
        "last_funding_time_ms": times[-1],
        "post_cutoff_records": sum(value > CUTOFF_MS for value in times),
        "duplicates": len(times) - len(set(times)),
        "backward_timestamps": sum(b <= a for a, b in zip(times, times[1:], strict=False)),
        "unexplained_gaps_over_8h_plus_60s": sum(delta > MAX_NATURAL_GAP_MS for delta in intervals),
        "observed_settlement_cadence_hours_rounded": sorted(
            {round(delta / 3_600_000) for delta in intervals}
        ),
        "deterministic_pagination": True,
        "silent_fill": False,
        "canonical_columns": ["funding_time", "funding_rate"],
        "mark_price_feature": False,
        "predicted_funding": False,
        "premium_basis_oi_ratio": False,
        "raw_request_hashes_verified": True,
    }
    return manifest, integrity


class FundingContextSource:
    """Strictly-prior latest-settlement lookup over a deterministic timeline."""

    def __init__(self, times_us: list[int], rates: list[float]):
        if not times_us or len(times_us) != len(rates):
            raise FundingDataError("funding context needs aligned nonempty records")
        if any(b <= a for a, b in zip(times_us, times_us[1:], strict=False)):
            raise FundingDataError("funding timeline is not strictly increasing")
        self.times_us = tuple(times_us)
        self.rates = tuple(float(value) for value in rates)

    def at(self, signal_us: int) -> tuple[int, float]:
        index = bisect.bisect_left(self.times_us, signal_us) - 1
        if index < 0:
            raise FundingDataError("no strictly prior settled funding observation")
        return self.times_us[index], self.rates[index]


def load_funding_context(root: Path = ROOT) -> FundingContextSource:
    manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    path = root / manifest["canonical"]["path"]
    if file_sha256(path) != manifest["canonical"]["file_sha256"]:
        raise FundingDataError("canonical funding artifact hash mismatch")
    table = pq.read_table(path)
    if table.column_names != ["funding_time", "funding_rate"]:
        raise FundingDataError("canonical funding columns drifted")
    times = table["funding_time"].cast(pa.int64()).to_pylist()
    rates = table["funding_rate"].to_pylist()
    if max(times) // 1000 > CUTOFF_MS:
        raise FundingDataError("canonical funding contains a post-cutoff record")
    return FundingContextSource([int(value) for value in times], [float(value) for value in rates])


__all__ = [name for name in globals() if name.isupper()] + [
    "FundingContextSource",
    "FundingDataError",
    "acquire",
    "build",
    "load_funding_context",
    "parse_response",
    "raw_records",
    "request_params",
    "request_url",
]
