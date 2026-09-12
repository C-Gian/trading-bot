"""Shared point-in-time exogenous data primitives for WP-009."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa

from .wp004 import ROOT

CONTRACT_VERSION = "POINT_IN_TIME_EXOGENOUS_DATA_V1"
GDELT_VERSION = "GDELT_NEWS_CONTEXT_V1"
GDELT_DAILY_VERSION = "GDELT_NEWS_CONTEXT_V1_1"
ALFRED_VERSION = "ALFRED_MACRO_CONTEXT_V1"
CONTEXT_VERSION = "EXOGENOUS_CONTEXT_V1"
START = datetime(2017, 8, 17, tzinfo=UTC)
END = datetime(2024, 12, 31, 23, tzinfo=UTC)
REQUEST_END = datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
GDELT_DAILY_PILOT_END = datetime(2017, 12, 31, 23, 59, 59, tzinfo=UTC)

GDELT_CHANNELS = (
    "Q1_CRYPTO_CORE",
    "Q2_CRYPTO_POLICY",
    "Q3_CENTRAL_BANK_POLICY",
    "Q4_GEOPOLITICAL_STRESS",
    "Q5_SOCIAL_STRESS",
)
ALFRED_SERIES = ("DFF", "DGS10", "T10Y2Y", "VIXCLS", "NFCI", "WALCL", "CPIAUCSL", "UNRATE")

GDELT_SCHEMA = pa.schema(
    [
        ("channel_id", pa.string(), False),
        ("hour", pa.timestamp("us", tz="UTC"), False),
        ("availability_time", pa.timestamp("us", tz="UTC"), False),
        ("matched_articles", pa.int64()),
        ("monitored_articles_norm", pa.int64()),
        ("coverage_share", pa.float64()),
        ("average_tone", pa.float64()),
        ("data_available", pa.bool_(), False),
        ("source_request_id", pa.string(), False),
    ]
)

GDELT_DAILY_SCHEMA = pa.schema(
    [
        ("channel_id", pa.string(), False),
        ("day", pa.date32(), False),
        ("availability_time", pa.timestamp("us", tz="UTC"), False),
        ("matched_articles", pa.int64()),
        ("monitored_articles_norm", pa.int64()),
        ("coverage_share", pa.float64()),
        ("average_tone", pa.float64()),
        ("data_available", pa.bool_(), False),
        ("source_request_id", pa.string(), False),
    ]
)

ALFRED_SCHEMA = pa.schema(
    [
        ("series_id", pa.string(), False),
        ("observation_date", pa.date32(), False),
        ("value", pa.float64(), False),
        ("vintage_start", pa.date32(), False),
        ("vintage_end", pa.date32()),
        ("availability_time", pa.timestamp("us", tz="UTC"), False),
        ("source_request_id", pa.string(), False),
    ]
)

ALFRED_REQUEST_SCHEMA = pa.schema(
    [
        ("series_id", pa.string(), False),
        ("vintage_date", pa.date32(), False),
        ("request_id", pa.string(), False),
        ("request_status", pa.string(), False),
        ("http_status", pa.int32(), False),
        ("retrieval_time", pa.timestamp("us", tz="UTC"), False),
        ("raw_path", pa.string()),
        ("response_sha256", pa.string()),
        ("file_sha256", pa.string()),
    ]
)


class ExogenousDataError(ValueError):
    """A source, timestamp, or point-in-time identity violated WP-009."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_id(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return sha256_bytes(encoded)


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ExogenousDataError("timestamp must be explicit UTC")
    return parsed.astimezone(UTC)


def hours() -> tuple[datetime, ...]:
    count = int((END - START) / HOUR) + 1
    return tuple(START + index * HOUR for index in range(count))


def calendar_dates() -> tuple[date, ...]:
    count = (END.date() - START.date()).days + 1
    return tuple(START.date() + timedelta(days=index) for index in range(count))


def calendar_days(start: datetime, end: datetime) -> tuple[date, ...]:
    """Every UTC calendar day fully inside ``[start, end]``."""
    count = (end.date() - start.date()).days + 1
    return tuple(start.date() + timedelta(days=index) for index in range(count))


def daily_availability(day: date) -> datetime:
    """A complete UTC day becomes available only at ``D+1 00:00:00 UTC``."""
    return datetime.combine(day + timedelta(days=1), datetime.min.time(), UTC)


def next_day_availability(vintage_start: date) -> datetime:
    return datetime.combine(vintage_start + timedelta(days=1), datetime.min.time(), UTC)


def validate_catalogs(root: Path = ROOT) -> dict[str, Any]:
    source = read_json(root / "research/exogenous/SOURCE_CATALOG_V1.json")
    gdelt = read_json(root / "research/exogenous/GDELT_QUERY_CATALOG_V1.json")
    alfred = read_json(root / "research/exogenous/ALFRED_SERIES_CATALOG_V1.json")
    if (
        source["authorized_source_family_count"] != 2
        or [item["source_family"] for item in source["source_families"]]
        != ["GDELT_DOC_2_0", "ALFRED"]
        or source["btc_outcomes_consulted"]
    ):
        raise ExogenousDataError("source catalog differs from its exact authority")
    if (
        tuple(item["channel_id"] for item in gdelt["channels"]) != GDELT_CHANNELS
        or gdelt["modes"] != ["TimelineVolRaw", "TimelineTone"]
        or gdelt["timeline_smooth"] != 0
        or gdelt["selection_uses_btc_outcomes"]
        or parse_utc(gdelt["coverage_start_utc"]) != START
        or parse_utc(gdelt["coverage_end_utc"]) != REQUEST_END
    ):
        raise ExogenousDataError("GDELT query catalog changed")
    expected_queries = (
        "(bitcoin OR cryptocurrency)",
        "(bitcoin OR cryptocurrency) (regulation OR regulator OR regulatory OR law OR ban)",
        '("Federal Reserve" OR "European Central Bank" OR "Bank of England" OR "Bank of Japan")',
        "(war OR conflict OR sanctions OR invasion OR missile)",
        "(protest OR riot OR unrest OR strike)",
    )
    if tuple(item["query"] for item in gdelt["channels"]) != expected_queries:
        raise ExogenousDataError("GDELT vocabulary drifted")
    if (
        tuple(item["series_id"] for item in alfred["series"]) != ALFRED_SERIES
        or alfred["credential_required"]
        or alfred["current_revised_fred_substitution"]
        or alfred["availability_rule"] != "NEXT_CALENDAR_DAY_00_00_UTC_AFTER_VINTAGE_START"
        or alfred["selection_uses_btc_outcomes"]
    ):
        raise ExogenousDataError("ALFRED series catalog changed")
    return {"source": source, "gdelt": gdelt, "alfred": alfred}
