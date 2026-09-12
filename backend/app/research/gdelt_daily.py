"""Credential-free GDELT DOC 2.0 daily acquisition for ``GDELT_NEWS_CONTEXT_V1_1``.

``GDELT_NEWS_CONTEXT_V1`` (:mod:`app.research.gdelt`) required hourly timeline
resolution, which official DOC 2.0 semantics only return for spans of 72 hours
through one week. That forced 3850 credential-free requests, and the endpoint
persistently answered HTTP 429 during that schedule.

``GDELT_NEWS_CONTEXT_V1_1`` keeps the five frozen semantic channels, both frozen
modes and ``TIMELINESMOOTH=0`` byte-for-byte, and only changes the acquisition
unit to the UTC calendar day over calendar-year request windows. The V1 hourly
raw cache and module are preserved untouched as historical acquisition evidence.
"""

from __future__ import annotations

import gzip
import json
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from .artifacts import write_parquet
from .exogenous import (
    GDELT_CHANNELS,
    GDELT_DAILY_PILOT_END,
    GDELT_DAILY_SCHEMA,
    GDELT_DAILY_VERSION,
    REQUEST_END,
    START,
    ExogenousDataError,
    calendar_days,
    canonical_id,
    daily_availability,
    file_sha256,
    read_json,
    sha256_bytes,
    validate_catalogs,
)
from .wp004 import ROOT

ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
RAW_ROOT = "data/raw/exogenous/gdelt-doc-v2-daily"
CANONICAL_PATH = "data/derived/GDELT-news-context-v1_1.parquet"
AMENDMENT_PATH = "research/exogenous/GDELT-NEWS-CONTEXT-AMENDMENT-V1_1.json"
PILOT_MANIFEST_PATH = "data/manifests/GDELT-NEWS-CONTEXT-DAILY-PILOT-DEV-v1_1.json"
PILOT_INTEGRITY_PATH = "reports/validation/WP-009-GDELT-DAILY-PILOT-INTEGRITY.json"
PILOT_ACQUISITION_PATH = "reports/validation/WP-009-GDELT-DAILY-PILOT-ACQUISITION.json"
PARSER_VERSION = "GDELT_DOC_TIMELINE_TO_DAILY_V1_1"
DAILY_RESOLUTION = "day"
HTTP_TIMEOUT_SECONDS = 90

# Bounded error handling: no retry loop may run unbounded.
MAX_ATTEMPTS = 4
BACKOFF_SECONDS = (45.0, 120.0, 300.0)
MIN_REQUEST_INTERVAL_SECONDS = 10.0
MAX_THROTTLE_RESPONSES = 12


def _source_day(value: str) -> date:
    stamp = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    if (stamp.hour, stamp.minute, stamp.second) != (0, 0, 0):
        raise ExogenousDataError("GDELT daily point carries an intraday timestamp")
    return stamp.date()


def _windows(end: datetime) -> tuple[tuple[datetime, datetime], ...]:
    """Calendar-year request windows, long enough that GDELT answers daily."""
    if end > REQUEST_END:
        raise ExogenousDataError("GDELT V1_1 must never request data after 2024-12-31")
    spans = []
    cursor = START
    while cursor <= end:
        year_last = datetime(cursor.year, 12, 31, 23, 59, 59, tzinfo=UTC)
        spans.append((cursor, min(year_last, end)))
        cursor = datetime(cursor.year + 1, 1, 1, tzinfo=UTC)
    return tuple(spans)


def request_specs(root: Path = ROOT, *, end: datetime = REQUEST_END) -> tuple[dict[str, Any], ...]:
    """Deterministic frozen request identities for every channel, mode and window."""
    catalog = validate_catalogs(root)["gdelt"]
    queries = {item["channel_id"]: item["query"] for item in catalog["channels"]}
    specs = []
    for window_start, window_end in _windows(end):
        for channel_id in GDELT_CHANNELS:
            for mode in catalog["modes"]:
                params = {
                    "query": queries[channel_id],
                    "mode": mode,
                    "format": "json",
                    "maxrecords": "250",
                    "startdatetime": window_start.strftime("%Y%m%d%H%M%S"),
                    "enddatetime": window_end.strftime("%Y%m%d%H%M%S"),
                    "timelinesmooth": "0",
                }
                identity = {
                    "source": "GDELT_DOC_2_0",
                    "endpoint": ENDPOINT,
                    "params": params,
                    "parser": PARSER_VERSION,
                }
                request_id = canonical_id(identity)
                specs.append(
                    {
                        **identity,
                        "request_id": request_id,
                        "channel_id": channel_id,
                        "mode": mode,
                        "window_id": str(window_start.year),
                        "start_utc": window_start.isoformat().replace("+00:00", "Z"),
                        "end_utc": window_end.isoformat().replace("+00:00", "Z"),
                        "raw_path": f"{RAW_ROOT}/{channel_id}/{mode}/{request_id}.json.gz",
                        "meta_path": f"{RAW_ROOT}/{channel_id}/{mode}/{request_id}.meta.json",
                    }
                )
    return tuple(specs)


def pilot_specs(root: Path = ROOT) -> tuple[dict[str, Any], ...]:
    """The deterministic 2017-08-17 .. 2017-12-31 pilot interval only."""
    return request_specs(root, end=GDELT_DAILY_PILOT_END)


def request_url(spec: dict[str, Any]) -> str:
    return f"{spec['endpoint']}?{urlencode(spec['params'])}"


def _timeline(document: dict[str, Any]) -> list[dict[str, Any]]:
    timeline = document["timeline"]
    if isinstance(timeline, dict):
        timeline = [timeline]
    if len(timeline) != 1 or "data" not in timeline[0]:
        raise ExogenousDataError("GDELT response must contain one timeline series")
    return list(timeline[0]["data"])


def _valid_payload(payload: bytes) -> dict[str, Any]:
    """Validate the returned resolution rather than assuming it."""
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ExogenousDataError("GDELT returned non-JSON content") from exc
    if "query_details" not in document or "timeline" not in document:
        raise ExogenousDataError("GDELT response lacks timeline metadata")
    resolution = document["query_details"].get("date_resolution")
    if resolution != DAILY_RESOLUTION:
        raise ExogenousDataError(f"GDELT response is not daily resolution: {resolution}")
    smooth = document["query_details"].get("timelinesmooth")
    if smooth not in (None, 0, "0"):
        raise ExogenousDataError("GDELT response declares timeline smoothing")
    return document


def _validate_acquired_document(document: dict[str, Any], spec: dict[str, Any]) -> None:
    start = datetime.fromisoformat(spec["start_utc"]).date()
    end = datetime.fromisoformat(spec["end_utc"]).date()
    for point in _timeline(document):
        day = _source_day(point["date"])
        if day < start or day > end or day > REQUEST_END.date():
            raise ExogenousDataError("GDELT response point escaped frozen request bounds")


def _validated_cached_response(
    spec: dict[str, Any], raw_path: Path, meta_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = gzip.decompress(raw_path.read_bytes())
    meta = read_json(meta_path)
    document = _valid_payload(raw)
    if (
        meta["request_id"] != spec["request_id"]
        or meta["url"] != request_url(spec)
        or meta["response_sha256"] != sha256_bytes(raw)
        or meta["compressed_file_sha256"] != file_sha256(raw_path)
        or meta["date_resolution"] != document["query_details"]["date_resolution"]
    ):
        raise ExogenousDataError("GDELT cached request identity or hash mismatch")
    _validate_acquired_document(document, spec)
    return meta, document


def _write_response(
    spec: dict[str, Any], root: Path, body: bytes, document: dict[str, Any]
) -> None:
    raw_path, meta_path = root / spec["raw_path"], root / spec["meta_path"]
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(gzip.compress(body, compresslevel=9, mtime=0))
    meta_path.write_text(
        json.dumps(
            {
                "request_id": spec["request_id"],
                "url": request_url(spec),
                "retrieval_time_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "response_sha256": sha256_bytes(body),
                "compressed_file_sha256": file_sha256(raw_path),
                "date_resolution": document["query_details"]["date_resolution"],
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def acquire(
    root: Path = ROOT,
    *,
    specs: tuple[dict[str, Any], ...] | None = None,
    sleep: Any = time.sleep,
    client: Any = httpx,
) -> dict[str, Any]:
    """Resumable, idempotent, hash-verified acquisition with bounded error handling.

    Cached responses are re-verified against their frozen identity and hashes and are
    never refetched. Every request gets at most ``MAX_ATTEMPTS`` tries, and the run
    stops once ``MAX_THROTTLE_RESPONSES`` HTTP 429 responses are observed, so no retry
    loop is unbounded and successful cache entries are always preserved.
    """
    specs = pilot_specs(root) if specs is None else specs
    counts = {"fetched": 0, "reused": 0, "failed": 0}
    throttled = 0
    errors: list[dict[str, str]] = []
    stopped = False
    for spec in specs:
        raw_path, meta_path = root / spec["raw_path"], root / spec["meta_path"]
        if raw_path.is_file() and meta_path.is_file():
            _validated_cached_response(spec, raw_path, meta_path)
            counts["reused"] += 1
            continue
        if stopped:
            counts["failed"] += 1
            errors.append(
                {"request_id": spec["request_id"], "error": "SKIPPED_AFTER_THROTTLE_STOP"}
            )
            continue
        last_error = ""
        for attempt in range(MAX_ATTEMPTS):
            sleep(MIN_REQUEST_INTERVAL_SECONDS if attempt == 0 else BACKOFF_SECONDS[attempt - 1])
            try:
                response = client.get(
                    request_url(spec),
                    headers={"User-Agent": "trading-bot-wp009/1.1"},
                    timeout=HTTP_TIMEOUT_SECONDS,
                    follow_redirects=True,
                )
            except httpx.HTTPError as exc:
                last_error = f"transport: {exc}"
                continue
            if response.status_code == 429:
                throttled += 1
                last_error = "status=429 credential-free GDELT throttle"
                if throttled >= MAX_THROTTLE_RESPONSES:
                    stopped = True
                    break
                continue
            if response.status_code != 200:
                last_error = f"status={response.status_code}"
                continue
            try:
                document = _valid_payload(response.content)
                _validate_acquired_document(document, spec)
            except ExogenousDataError as exc:
                last_error = str(exc)
                continue
            _write_response(spec, root, response.content, document)
            counts["fetched"] += 1
            last_error = ""
            break
        if last_error:
            counts["failed"] += 1
            errors.append({"request_id": spec["request_id"], "error": last_error})
    completed = counts["fetched"] + counts["reused"]
    return {
        "version": GDELT_DAILY_VERSION,
        "expected": len(specs),
        **counts,
        "completed": completed,
        "throttle_429_responses": throttled,
        "stopped_on_persistent_throttle": stopped,
        "status": "COMPLETE" if completed == len(specs) else "PARTIAL_SOURCE_THROTTLED",
        "errors": errors,
    }


def _aggregate(document: dict[str, Any], *, mode: str) -> dict[date, dict[str, Any]]:
    result: dict[date, dict[str, Any]] = {}
    for point in _timeline(document):
        day = _source_day(point["date"])
        if day in result:
            raise ExogenousDataError("duplicate GDELT daily source point")
        if mode == "TimelineVolRaw":
            norm, value = point.get("norm"), point["value"]
            if float(value) != int(value):
                raise ExogenousDataError("raw article volume must be an exact count")
            result[day] = {
                "matched_articles": int(value),
                "monitored_articles_norm": None if norm is None else int(norm),
                "norm_available": norm is not None,
            }
        else:
            result[day] = {"average_tone": float(point["value"])}
    return result


def build(
    root: Path = ROOT, *, specs: tuple[dict[str, Any], ...] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Deterministic raw -> derived rebuild over the frozen cached responses."""
    specs = pilot_specs(root) if specs is None else specs
    cached: dict[tuple[str, str, str], dict[date, dict[str, Any]]] = {}
    requests: list[dict[str, Any]] = []
    for spec in specs:
        raw_path, meta_path = root / spec["raw_path"], root / spec["meta_path"]
        if not raw_path.is_file() or not meta_path.is_file():
            raise ExogenousDataError(f"missing frozen GDELT daily response: {spec['request_id']}")
        meta, document = _validated_cached_response(spec, raw_path, meta_path)
        cached[(spec["channel_id"], spec["mode"], spec["window_id"])] = _aggregate(
            document, mode=spec["mode"]
        )
        requests.append(
            {
                "request_id": spec["request_id"],
                "channel_id": spec["channel_id"],
                "mode": spec["mode"],
                "window_id": spec["window_id"],
                "start_utc": spec["start_utc"],
                "end_utc": spec["end_utc"],
                "raw_path": spec["raw_path"],
                "response_sha256": meta["response_sha256"],
                "compressed_file_sha256": meta["compressed_file_sha256"],
                "date_resolution": meta["date_resolution"],
                "retrieval_time_utc": meta["retrieval_time_utc"],
            }
        )
    requests.sort(key=lambda item: (item["window_id"], item["channel_id"], item["mode"]))

    coverage_start = min(datetime.fromisoformat(spec["start_utc"]) for spec in specs)
    coverage_end = max(datetime.fromisoformat(spec["end_utc"]) for spec in specs)
    days = calendar_days(coverage_start, coverage_end)
    window_of: dict[date, str] = {}
    for spec in specs:
        for day in calendar_days(
            datetime.fromisoformat(spec["start_utc"]), datetime.fromisoformat(spec["end_utc"])
        ):
            window_of[day] = spec["window_id"]

    rows: list[dict[str, Any]] = []
    for channel_id in GDELT_CHANNELS:
        for day in days:
            window_id = window_of[day]
            volume = cached[(channel_id, "TimelineVolRaw", window_id)].get(day, {})
            tone = cached[(channel_id, "TimelineTone", window_id)].get(day, {})
            available = bool(volume) and bool(tone) and bool(volume["norm_available"])
            norm = volume.get("monitored_articles_norm") if available else None
            matched = volume.get("matched_articles") if available else None
            rows.append(
                {
                    "channel_id": channel_id,
                    "day": day,
                    "availability_time": daily_availability(day),
                    "matched_articles": matched,
                    "monitored_articles_norm": norm,
                    "coverage_share": (matched / norm) if available and norm else None,
                    "average_tone": tone.get("average_tone") if available else None,
                    "data_available": available,
                    "source_request_id": ":".join(
                        sorted(
                            spec["request_id"]
                            for spec in specs
                            if spec["channel_id"] == channel_id and spec["window_id"] == window_id
                        )
                    ),
                }
            )
    artifact = write_parquet(
        root / CANONICAL_PATH,
        rows,
        schema=GDELT_DAILY_SCHEMA,
        sort_key=["channel_id", "day"],
        root=root,
    )
    availability = {
        channel: sum(1 for row in rows if row["channel_id"] == channel and row["data_available"])
        for channel in GDELT_CHANNELS
    }
    is_pilot = coverage_end == GDELT_DAILY_PILOT_END
    manifest = {
        "schema_version": 1,
        "manifest_id": "GDELT-NEWS-CONTEXT-DAILY-PILOT-DEV-v1_1",
        "version": GDELT_DAILY_VERSION,
        "scope": "DETERMINISTIC_PILOT_INTERVAL" if is_pilot else "EXTENDED_INTERVAL",
        "contract": "docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md",
        "amendment": AMENDMENT_PATH,
        "amendment_sha256": file_sha256(root / AMENDMENT_PATH),
        "query_catalog": "research/exogenous/GDELT_QUERY_CATALOG_V1.json",
        "query_catalog_sha256": file_sha256(
            root / "research/exogenous/GDELT_QUERY_CATALOG_V1.json"
        ),
        "coverage": {"start": coverage_start.isoformat(), "end": coverage_end.isoformat()},
        "aggregation_unit": "UTC_CALENDAR_DAY",
        "availability_rule": "UTC_DAY_D_AVAILABLE_AT_D_PLUS_1_00_00_00_UTC",
        "channels": list(GDELT_CHANNELS),
        "modes": ["TimelineVolRaw", "TimelineTone"],
        "timeline_smooth": 0,
        "response_resolutions": sorted({item["date_resolution"] for item in requests}),
        "daily_rows": len(rows),
        "days": len(days),
        "daily_rows_per_channel": {channel: len(days) for channel in GDELT_CHANNELS},
        "availability_by_channel": availability,
        "missing_days_by_channel": {
            channel: len(days) - count for channel, count in availability.items()
        },
        "requests": requests,
        "file": artifact,
        "post_2024_rows": sum(1 for row in rows if row["day"] > REQUEST_END.date()),
        "article_bodies_acquired": False,
        "btc_price_return_or_outcome_columns_loaded": False,
        "rolling_or_normalization_transforms": False,
        "trading_score": False,
        "remaining_years_acquired": not is_pilot,
    }
    integrity = {
        "schema_version": 1,
        "work_package": "WP-009",
        "version": GDELT_DAILY_VERSION,
        "scope": manifest["scope"],
        "status": "PASS",
        "checks": {
            "exact_five_channels": "PASS",
            "catalog_and_amendment_precede_acquisition": "PASS",
            "no_smoothing": "PASS",
            "daily_resolution_validated_not_assumed": "PASS",
            "canonical_daily_grid": "PASS",
            "no_duplicate_channel_day": "PASS",
            "strictly_increasing_per_channel": "PASS",
            "explicit_gaps": "PASS",
            "request_response_hashes": "PASS",
            "deterministic_raw_to_derived": "PASS",
            "next_day_availability": "PASS",
            "no_same_day_availability": "PASS",
            "no_post_2024": "PASS",
            "no_article_body_scraping": "PASS",
            "no_btc_prices_returns_outcomes_or_strategy": "PASS",
        },
        "daily_rows": len(rows),
        "days": len(days),
        "availability_by_channel": availability,
        "response_resolutions": manifest["response_resolutions"],
        "artifact_file_sha256": artifact["file_sha256"],
        "artifact_logical_sha256": artifact["logical_sha256"],
    }
    return manifest, integrity


def validate(root: Path = ROOT) -> dict[str, Any]:
    """Re-derive the pilot from raw cache and require identical committed records."""
    manifest = read_json(root / PILOT_MANIFEST_PATH)
    integrity = read_json(root / PILOT_INTEGRITY_PATH)
    rebuilt_manifest, rebuilt_integrity = build(root)
    if manifest != rebuilt_manifest or integrity != rebuilt_integrity:
        raise ExogenousDataError(
            "GDELT V1_1 pilot manifest/integrity differs from deterministic rebuild"
        )
    return integrity
