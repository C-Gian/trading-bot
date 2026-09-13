"""Official Wikimedia daily Bitcoin pageviews and conservative as-of feature."""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .artifacts import file_sha256, write_parquet
from .evaluation_protocol import HOUR_US
from .wp004 import ROOT

VERSION = "WIKIPEDIA_ATTENTION_CONTEXT_V1"
FEATURE = "BITCOIN_WIKIPEDIA_ATTENTION_SHOCK_V1"
PROJECT = "en.wikipedia"
ARTICLE = "Bitcoin"
ACCESS = "all-access"
AGENT = "user"
GRANULARITY = "daily"
API_ORIGIN = "https://wikimedia.org"
ENDPOINT = "/api/rest_v1/metrics/pageviews/per-article"
SOURCE_START = date(2015, 7, 1)
CUTOFF_DATE = date(2024, 12, 31)
CUTOFF_US = int(datetime(2024, 12, 31, 23, 59, tzinfo=UTC).timestamp() * 1_000_000)
DAY_US = 86_400_000_000
AVAILABILITY_LAG_US = 2 * DAY_US
TRAILING_OBSERVATIONS = 28
RAW_ROOT = "data/raw/wikimedia/en.wikipedia/Bitcoin/daily"
CANONICAL_PATH = "data/derived/WIKIMEDIA-enwiki-Bitcoin-pageviews-daily-v1.parquet"
MANIFEST_PATH = "data/manifests/WIKIMEDIA-BITCOIN-PAGEVIEWS-DEV-v1.json"
USER_AGENT = "TradingBotResearch/1.0 (owner-initiated local scientific research)"
CANONICAL_SCHEMA = pa.schema(
    [
        ("observation_date", pa.timestamp("us", tz="UTC"), False),
        ("availability_time", pa.timestamp("us", tz="UTC"), False),
        ("pageviews", pa.int64(), False),
    ]
)


class WikimediaDataError(ValueError):
    """Official-source identity, chronology, or point-in-time semantics failed."""


@dataclass(frozen=True)
class AttentionValue:
    observation_us: int
    availability_us: int
    pageviews: int
    trailing_median: float
    shock: float


def _day_us(value: date) -> int:
    return int(datetime(value.year, value.month, value.day, tzinfo=UTC).timestamp() * 1_000_000)


def _api_stamp(value: date) -> str:
    return value.strftime("%Y%m%d00")


def request_url(start: date, end: date) -> str:
    if start < SOURCE_START or end > CUTOFF_DATE or end < start:
        raise WikimediaDataError("Wikimedia request exceeds the frozen development window")
    return (
        f"{API_ORIGIN}{ENDPOINT}/{PROJECT}/{ACCESS}/{AGENT}/{ARTICLE}/{GRANULARITY}/"
        f"{_api_stamp(start)}/{_api_stamp(end)}"
    )


def request_windows() -> tuple[tuple[date, date], ...]:
    windows = []
    for year in range(SOURCE_START.year, CUTOFF_DATE.year + 1):
        start = max(SOURCE_START, date(year, 1, 1))
        end = min(CUTOFF_DATE, date(year, 12, 31))
        windows.append((start, end))
    return tuple(windows)


def raw_path(root: Path, start: date, end: date) -> Path:
    return root / RAW_ROOT / f"{start.isoformat()}_{end.isoformat()}.json"


def meta_path(raw: Path) -> Path:
    return raw.with_suffix(".meta.json")


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False, suffix=".staging") as f:
        f.write(payload)
        staging = Path(f.name)
    os.replace(staging, path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    content = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    _atomic_bytes(path, content)


def _fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise WikimediaDataError(f"official Wikimedia API returned HTTP {response.status}")
        return response.read()


def parse_response(payload: bytes, start: date, end: date) -> list[dict[str, Any]]:
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WikimediaDataError("Wikimedia response is not valid JSON") from exc
    if not isinstance(document, dict) or not isinstance(document.get("items"), list):
        raise WikimediaDataError("Wikimedia response has no items array")
    rows: list[dict[str, Any]] = []
    previous: date | None = None
    for item in document["items"]:
        if not isinstance(item, dict):
            raise WikimediaDataError("Wikimedia item is not an object")
        identity = {
            "project": item.get("project"),
            "article": item.get("article"),
            "access": item.get("access"),
            "agent": item.get("agent"),
            "granularity": item.get("granularity"),
        }
        expected = {
            "project": PROJECT,
            "article": ARTICLE,
            "access": ACCESS,
            "agent": AGENT,
            "granularity": GRANULARITY,
        }
        if identity != expected:
            raise WikimediaDataError("Wikimedia source selectors drifted")
        timestamp = item.get("timestamp")
        try:
            observed = datetime.strptime(str(timestamp), "%Y%m%d00").replace(tzinfo=UTC).date()
        except ValueError as exc:
            raise WikimediaDataError("Wikimedia daily timestamp is invalid") from exc
        views = item.get("views")
        if not isinstance(views, int) or isinstance(views, bool) or views < 0:
            raise WikimediaDataError("Wikimedia pageviews must be a nonnegative integer")
        if observed < start or observed > end or observed > CUTOFF_DATE:
            raise WikimediaDataError("Wikimedia observation is outside its request window")
        if previous is not None and observed <= previous:
            raise WikimediaDataError("duplicate or backward Wikimedia daily timestamp")
        rows.append({"date": observed, "pageviews": views})
        previous = observed
    return rows


def acquire(root: Path = ROOT, fetch: Callable[[str], bytes] = _fetch) -> dict[str, int]:
    fetched = 0
    reused = 0
    for start, end in request_windows():
        url = request_url(start, end)
        target = raw_path(root, start, end)
        metadata = meta_path(target)
        if target.is_file() and metadata.is_file():
            meta = json.loads(metadata.read_text(encoding="utf-8"))
            if meta.get("request_url") != url or meta.get("response_sha256") != file_sha256(target):
                raise WikimediaDataError("cached Wikimedia request identity differs")
            parse_response(target.read_bytes(), start, end)
            reused += 1
            continue
        payload = fetch(url)
        rows = parse_response(payload, start, end)
        _atomic_bytes(target, payload)
        _atomic_json(
            metadata,
            {
                "source": "WIKIMEDIA_REST_PAGEVIEWS_API",
                "request_url": url,
                "request_window": {"start": start.isoformat(), "end": end.isoformat()},
                "retrieved_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "response_sha256": hashlib.sha256(payload).hexdigest(),
                "rows": len(rows),
                "credentials_used": False,
            },
        )
        fetched += 1
    return {"windows": len(request_windows()), "fetched": fetched, "reused": reused}


def raw_records(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    for start, end in request_windows():
        target = raw_path(root, start, end)
        metadata = meta_path(target)
        if not target.is_file() or not metadata.is_file():
            raise WikimediaDataError("official Wikimedia raw window is unavailable")
        meta = json.loads(metadata.read_text(encoding="utf-8"))
        url = request_url(start, end)
        digest = file_sha256(target)
        if meta.get("request_url") != url or meta.get("response_sha256") != digest:
            raise WikimediaDataError("Wikimedia raw bytes or request identity changed")
        chunk = parse_response(target.read_bytes(), start, end)
        records.extend(chunk)
        requests.append(
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "url": url,
                "path": target.relative_to(root).as_posix(),
                "metadata_path": metadata.relative_to(root).as_posix(),
                "sha256": digest,
                "rows": len(chunk),
            }
        )
    return records, requests


def build(root: Path = ROOT) -> dict[str, Any]:
    source, requests = raw_records(root)
    days = [row["date"] for row in source]
    duplicates = len(days) - len(set(days))
    expected_days = [
        SOURCE_START + timedelta(days=offset)
        for offset in range((CUTOFF_DATE - SOURCE_START).days + 1)
    ]
    missing = [value.isoformat() for value in expected_days if value not in set(days)]
    if duplicates or missing or days != expected_days:
        raise WikimediaDataError("Wikimedia daily sequence is incomplete or duplicated")
    canonical = [
        {
            "observation_date": datetime(day.year, day.month, day.day, tzinfo=UTC),
            "availability_time": datetime(day.year, day.month, day.day, tzinfo=UTC)
            + timedelta(days=2),
            "pageviews": row["pageviews"],
        }
        for day, row in zip(days, source, strict=True)
    ]
    artifact = write_parquet(
        root / CANONICAL_PATH,
        canonical,
        schema=CANONICAL_SCHEMA,
        sort_key=["observation_date"],
        root=root,
    )
    manifest = {
        "schema_version": 1,
        "manifest_id": "WIKIMEDIA-BITCOIN-PAGEVIEWS-DEV-v1",
        "version": VERSION,
        "source": {
            "provider": "Wikimedia Foundation",
            "api": "Wikimedia REST Pageviews API",
            "origin": API_ORIGIN,
            "endpoint": ENDPOINT,
            "project": PROJECT,
            "article": ARTICLE,
            "access": ACCESS,
            "agent": AGENT,
            "granularity": GRANULARITY,
            "official_only": True,
            "credentials": False,
        },
        "development_cutoff": "2024-12-31T23:59:00Z",
        "coverage": {"start": days[0].isoformat(), "end": days[-1].isoformat()},
        "records": len(days),
        "integrity": {
            "duplicates": duplicates,
            "missing_days": len(missing),
            "missing_day_values": missing,
            "strictly_increasing": True,
            "post_cutoff_rows": 0,
        },
        "availability": {
            "rule": "UTC_DAY_END_PLUS_24H_FIRST_HOURLY_USE_AT_DAY_START_PLUS_48H",
            "lag_hours_from_observation_day_start": 48,
            "same_day_use": False,
        },
        "feature": {
            "name": FEATURE,
            "previous_observations": TRAILING_OBSERVATIONS,
            "current_observation_excluded_from_median": True,
            "transform": "LOG((PAGEVIEWS_D+1)/(MEDIAN(PREVIOUS_28_PAGEVIEWS)+1))",
            "variants": 0,
        },
        "raw_requests": requests,
        "canonical": artifact,
    }
    _atomic_json(root / MANIFEST_PATH, manifest)
    return manifest


class AttentionContextSource:
    def __init__(self, observation_us: list[int], pageviews: list[int]):
        if not observation_us or len(observation_us) != len(pageviews):
            raise WikimediaDataError("attention context needs aligned nonempty observations")
        if any(b <= a for a, b in zip(observation_us, observation_us[1:], strict=False)):
            raise WikimediaDataError("attention observations must be strictly increasing")
        if any(value % DAY_US for value in observation_us) or any(value < 0 for value in pageviews):
            raise WikimediaDataError("attention observations must be UTC days with valid views")
        if max(observation_us) > _day_us(CUTOFF_DATE):
            raise WikimediaDataError("post-cutoff attention observation is forbidden")
        self.observation_us = tuple(observation_us)
        self.availability_us = tuple(value + AVAILABILITY_LAG_US for value in observation_us)
        self.pageviews = tuple(int(value) for value in pageviews)

    def at(self, signal_us: int) -> AttentionValue:
        if signal_us % HOUR_US or signal_us > CUTOFF_US:
            raise WikimediaDataError("attention signal is misaligned or post-cutoff")
        index = bisect.bisect_right(self.availability_us, signal_us) - 1
        if index < TRAILING_OBSERVATIONS:
            raise WikimediaDataError("full 28-observation attention history is unavailable")
        window = self.observation_us[index - TRAILING_OBSERVATIONS : index + 1]
        if any(b - a != DAY_US for a, b in zip(window, window[1:], strict=False)):
            raise WikimediaDataError("missing daily observation makes attention unavailable")
        history = self.pageviews[index - TRAILING_OBSERVATIONS : index]
        median = float(np.median(np.asarray(history, dtype=np.int64)))
        views = self.pageviews[index]
        return AttentionValue(
            self.observation_us[index],
            self.availability_us[index],
            views,
            median,
            math.log((views + 1.0) / (median + 1.0)),
        )


def load_attention_context(root: Path = ROOT) -> AttentionContextSource:
    manifest_path = root / MANIFEST_PATH
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["source"] != {
        "provider": "Wikimedia Foundation",
        "api": "Wikimedia REST Pageviews API",
        "origin": API_ORIGIN,
        "endpoint": ENDPOINT,
        "project": PROJECT,
        "article": ARTICLE,
        "access": ACCESS,
        "agent": AGENT,
        "granularity": GRANULARITY,
        "official_only": True,
        "credentials": False,
    }:
        raise WikimediaDataError("Wikimedia manifest source identity changed")
    canonical = manifest["canonical"]
    path = root / canonical["path"]
    if file_sha256(path) != canonical["file_sha256"]:
        raise WikimediaDataError("canonical Wikimedia artifact hash mismatch")
    table = pq.read_table(path)
    if table.schema != CANONICAL_SCHEMA:
        raise WikimediaDataError("canonical Wikimedia schema changed")
    observations = [int(value) for value in table["observation_date"].cast(pa.int64()).to_pylist()]
    availability = [int(value) for value in table["availability_time"].cast(pa.int64()).to_pylist()]
    views = [int(value) for value in table["pageviews"].to_pylist()]
    if availability != [value + AVAILABILITY_LAG_US for value in observations]:
        raise WikimediaDataError("canonical Wikimedia availability drifted")
    return AttentionContextSource(observations, views)


__all__ = [
    "ACCESS",
    "AGENT",
    "ARTICLE",
    "CANONICAL_PATH",
    "CUTOFF_DATE",
    "FEATURE",
    "GRANULARITY",
    "MANIFEST_PATH",
    "PROJECT",
    "SOURCE_START",
    "TRAILING_OBSERVATIONS",
    "VERSION",
    "AttentionContextSource",
    "AttentionValue",
    "WikimediaDataError",
    "acquire",
    "build",
    "load_attention_context",
    "parse_response",
    "raw_records",
    "request_url",
    "request_windows",
]
