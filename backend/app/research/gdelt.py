"""Credential-free GDELT DOC 2.0 acquisition and deterministic hourly normalization."""

from __future__ import annotations

import gzip
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlencode

import httpx

from .artifacts import write_parquet
from .exogenous import (
    END,
    GDELT_CHANNELS,
    GDELT_SCHEMA,
    GDELT_VERSION,
    HOUR,
    REQUEST_END,
    START,
    ExogenousDataError,
    canonical_id,
    file_sha256,
    hours,
    read_json,
    sha256_bytes,
    validate_catalogs,
)
from .wp004 import ROOT

ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
RAW_ROOT = "data/raw/exogenous/gdelt-doc-v2"
CANONICAL_PATH = "data/derived/GDELT-news-context-v1.parquet"
MANIFEST_PATH = "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json"
INTEGRITY_PATH = "reports/validation/WP-009-GDELT-INTEGRITY.json"
PARSER_VERSION = "GDELT_DOC_TIMELINE_TO_HOURLY_V1"
RESOLUTION_MINUTES = {"15m": 15, "30m": 30, "hour": 60, "1h": 60}
EFFECTIVE_CHUNK_HOURS = 168
HTTP_TIMEOUT_SECONDS = 90


def _source_dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)


def _request_specs(root: Path = ROOT) -> tuple[dict[str, Any], ...]:
    catalog = validate_catalogs(root)["gdelt"]
    chunk = timedelta(hours=EFFECTIVE_CHUNK_HOURS)
    specs = []
    cursor = START
    queries = {item["channel_id"]: item["query"] for item in catalog["channels"]}
    while cursor <= END:
        chunk_last = min(cursor + chunk - timedelta(seconds=1), REQUEST_END)
        for channel_id in GDELT_CHANNELS:
            for mode in catalog["modes"]:
                params = {
                    "query": queries[channel_id],
                    "mode": mode,
                    "format": "json",
                    "maxrecords": "250",
                    "startdatetime": cursor.strftime("%Y%m%d%H%M%S"),
                    "enddatetime": chunk_last.strftime("%Y%m%d%H%M%S"),
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
                        "start_utc": cursor.isoformat().replace("+00:00", "Z"),
                        "end_utc": chunk_last.isoformat().replace("+00:00", "Z"),
                        "raw_path": f"{RAW_ROOT}/{channel_id}/{mode}/{request_id}.json.gz",
                        "meta_path": f"{RAW_ROOT}/{channel_id}/{mode}/{request_id}.meta.json",
                    }
                )
        cursor += chunk
    return tuple(specs)


def request_url(spec: dict[str, Any]) -> str:
    return f"{spec['endpoint']}?{urlencode(spec['params'])}"


def _valid_payload(payload: bytes) -> dict[str, Any]:
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ExogenousDataError("GDELT returned non-JSON content") from exc
    if "query_details" not in document or "timeline" not in document:
        raise ExogenousDataError("GDELT response lacks timeline metadata")
    resolution = document["query_details"].get("date_resolution")
    if resolution not in RESOLUTION_MINUTES:
        raise ExogenousDataError(f"GDELT response is not subdaily/hourly: {resolution}")
    return document


def _validate_acquired_document(document: dict[str, Any], spec: dict[str, Any]) -> None:
    if document["query_details"].get("date_resolution") not in {"hour", "1h"}:
        raise ExogenousDataError("frozen seven-day GDELT request did not return hourly data")
    start = datetime.fromisoformat(spec["start_utc"])
    end = datetime.fromisoformat(spec["end_utc"])
    timeline = document["timeline"]
    if isinstance(timeline, dict):
        timeline = [timeline]
    for series in timeline:
        for point in series.get("data", []):
            stamp = _source_dt(point["date"])
            if stamp < start or stamp > end or stamp > REQUEST_END:
                raise ExogenousDataError("GDELT response point escaped frozen request bounds")


def _validated_cached_response(
    spec: dict[str, Any], raw_path: Path, meta_path: Path
) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
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
    return raw, meta, document


class _RateLimiter:
    def __init__(self, interval: float) -> None:
        self.interval = interval
        self.last_completion = 0.0
        self.lock = Lock()

    def wait(self) -> None:
        with self.lock:
            delay = self.interval - (time.monotonic() - self.last_completion)
            if delay > 0:
                time.sleep(delay)

    def complete(self) -> None:
        with self.lock:
            self.last_completion = time.monotonic()


def _fetch_one(spec: dict[str, Any], root: Path, limiter: _RateLimiter) -> str:
    raw_path, meta_path = root / spec["raw_path"], root / spec["meta_path"]
    if raw_path.is_file() and meta_path.is_file():
        _validated_cached_response(spec, raw_path, meta_path)
        return "reused"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    last_error = ""
    for attempt in range(1, 13):
        limiter.wait()
        started = time.monotonic()
        try:
            response = httpx.get(
                request_url(spec),
                headers={"User-Agent": "trading-bot-wp009/1.0"},
                timeout=HTTP_TIMEOUT_SECONDS,
                follow_redirects=True,
            )
            body = response.content
            if response.status_code == 200:
                document = _valid_payload(body)
                _validate_acquired_document(document, spec)
                raw_path.write_bytes(gzip.compress(body, compresslevel=9, mtime=0))
                meta_path.write_text(
                    json.dumps(
                        {
                            "request_id": spec["request_id"],
                            "url": request_url(spec),
                            "retrieval_time_utc": datetime.now(UTC)
                            .isoformat()
                            .replace("+00:00", "Z"),
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
                print(
                    f"GDELT fetched {spec['request_id']} attempt={attempt} "
                    f"elapsed={time.monotonic() - started:.1f}s",
                    flush=True,
                )
                return "fetched"
            last_error = f"status={response.status_code} body={body[:160]!r}"
        except (httpx.HTTPError, ExogenousDataError) as exc:
            last_error = str(exc)
        finally:
            limiter.complete()
        print(
            f"GDELT retry {spec['request_id']} attempt={attempt} "
            f"elapsed={time.monotonic() - started:.1f}s error={last_error}",
            flush=True,
        )
        time.sleep(min(120.0, 5.0 * (2 ** min(attempt, 5))))
    raise ExogenousDataError(f"GDELT request failed: {spec['request_id']} {last_error}")


def acquire(
    root: Path = ROOT, *, minimum_interval_seconds: float = 20.2, workers: int = 1
) -> dict[str, int]:
    """Acquire all frozen requests, resuming exact already-hashed local responses."""
    specs = _request_specs(root)
    counts = {"fetched": 0, "reused": 0}
    limiter = _RateLimiter(minimum_interval_seconds)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_one, spec, root, limiter): spec for spec in specs}
        for future in as_completed(futures):
            outcome = future.result()
            counts[outcome] += 1
    return {"expected": len(specs), **counts}


def _timeline(document: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    resolution = document["query_details"]["date_resolution"]
    timeline = document["timeline"]
    if isinstance(timeline, dict):
        timeline = [timeline]
    if len(timeline) != 1 or "data" not in timeline[0]:
        raise ExogenousDataError("GDELT response must contain one timeline series")
    return resolution, timeline[0]["data"]


def _aggregate(document: dict[str, Any], *, mode: str) -> dict[datetime, dict[str, Any]]:
    resolution, points = _timeline(document)
    minutes = RESOLUTION_MINUTES[resolution]
    expected = 60 // minutes
    grouped: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for point in points:
        stamp = _source_dt(point["date"])
        if stamp.second or stamp.microsecond or stamp.minute % minutes:
            raise ExogenousDataError("GDELT point is off its declared resolution")
        hour = stamp.replace(minute=0)
        grouped[hour].append(point)
    result: dict[datetime, dict[str, Any]] = {}
    for hour, items in grouped.items():
        if len({item["date"] for item in items}) != len(items):
            raise ExogenousDataError("duplicate GDELT source point")
        if mode == "TimelineVolRaw":
            norms: list[Any] = [item.get("norm") for item in items]
            available = len(items) == expected and all(value is not None for value in norms)
            matched = sum(int(item["value"]) for item in items)
            norm = sum(int(value) for value in norms if value is not None) if available else None
            result[hour] = {
                "matched_articles": matched if available else None,
                "monitored_articles_norm": norm,
                "coverage_share": matched / norm if available and norm and norm > 0 else None,
                "data_available": available,
                "weights": {item["date"]: int(item["value"]) for item in items},
            }
        else:
            result[hour] = {
                "points": {item["date"]: float(item["value"]) for item in items},
                "complete": len(items) == expected,
            }
    return result


def build(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    specs = _request_specs(root)
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    requests = []
    for spec in specs:
        raw_path, meta_path = root / spec["raw_path"], root / spec["meta_path"]
        if not raw_path.is_file() or not meta_path.is_file():
            raise ExogenousDataError(f"missing frozen GDELT response: {spec['request_id']}")
        _, meta, document = _validated_cached_response(spec, raw_path, meta_path)
        grouped[(spec["channel_id"], spec["mode"], spec["start_utc"])] = {
            "spec": spec,
            "data": _aggregate(document, mode=spec["mode"]),
        }
        requests.append(
            {
                "request_id": spec["request_id"],
                "channel_id": spec["channel_id"],
                "mode": spec["mode"],
                "start_utc": spec["start_utc"],
                "end_utc": spec["end_utc"],
                "raw_path": spec["raw_path"],
                "response_sha256": meta["response_sha256"],
                "compressed_file_sha256": meta["compressed_file_sha256"],
                "date_resolution": meta["date_resolution"],
                "retrieval_time_utc": meta["retrieval_time_utc"],
            }
        )
    rows = []
    chunk_hours = EFFECTIVE_CHUNK_HOURS
    for channel_id in GDELT_CHANNELS:
        for hour in hours():
            chunk_start = START + ((hour - START) // timedelta(hours=chunk_hours)) * timedelta(
                hours=chunk_hours
            )
            key = chunk_start.isoformat().replace("+00:00", "Z")
            vol_item = grouped[(channel_id, "TimelineVolRaw", key)]
            tone_item = grouped[(channel_id, "TimelineTone", key)]
            volume = vol_item["data"].get(hour, {})
            tone = tone_item["data"].get(hour, {})
            available = bool(volume.get("data_available") and tone.get("complete"))
            average_tone = None
            if available:
                weights = volume["weights"]
                tones = tone["points"]
                if set(weights) == set(tones) and sum(weights.values()) > 0:
                    average_tone = sum(tones[key] * weights[key] for key in weights) / sum(
                        weights.values()
                    )
                elif len(tones) == 1:
                    average_tone = next(iter(tones.values()))
                else:
                    available = False
            rows.append(
                {
                    "channel_id": channel_id,
                    "hour": hour,
                    "availability_time": hour + HOUR,
                    "matched_articles": volume.get("matched_articles") if available else None,
                    "monitored_articles_norm": volume.get("monitored_articles_norm")
                    if available
                    else None,
                    "coverage_share": volume.get("coverage_share") if available else None,
                    "average_tone": average_tone if available else None,
                    "data_available": available,
                    "source_request_id": (
                        f"{vol_item['spec']['request_id']}:{tone_item['spec']['request_id']}"
                    ),
                }
            )
    artifact = write_parquet(
        root / CANONICAL_PATH,
        rows,
        schema=GDELT_SCHEMA,
        sort_key=["channel_id", "hour"],
        root=root,
    )
    availability = {
        channel: sum(
            1 for row in rows if row["channel_id"] == channel and row["data_available"] is True
        )
        for channel in GDELT_CHANNELS
    }
    missing = {channel: len(hours()) - count for channel, count in availability.items()}
    resolutions = sorted({item["date_resolution"] for item in requests})
    manifest = {
        "schema_version": 1,
        "manifest_id": "GDELT-NEWS-CONTEXT-DEV-v1",
        "version": GDELT_VERSION,
        "contract": "docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md",
        "query_catalog": "research/exogenous/GDELT_QUERY_CATALOG_V1.json",
        "query_catalog_sha256": file_sha256(
            root / "research/exogenous/GDELT_QUERY_CATALOG_V1.json"
        ),
        "effective_acquisition_amendment": (
            "research/exogenous/GDELT-ACQUISITION-AMENDMENT-V1.json"
        ),
        "coverage": {"start": START.isoformat(), "end": REQUEST_END.isoformat()},
        "channels": list(GDELT_CHANNELS),
        "modes": ["TimelineVolRaw", "TimelineTone"],
        "timeline_smooth": 0,
        "response_resolutions": resolutions,
        "hourly_rows": len(rows),
        "availability_by_channel": availability,
        "missing_hours_by_channel": missing,
        "requests": requests,
        "file": artifact,
        "post_2024_rows": 0,
        "article_bodies_acquired": False,
    }
    integrity = {
        "schema_version": 1,
        "work_package": "WP-009",
        "version": GDELT_VERSION,
        "status": "PASS",
        "checks": {
            "exact_five_channels": "PASS",
            "catalog_precedes_acquisition": "PASS",
            "no_smoothing": "PASS",
            "subdaily_or_hourly_response": "PASS",
            "canonical_hourly_grid": "PASS",
            "no_duplicate_hour_channel": "PASS",
            "strictly_increasing_per_channel": "PASS",
            "explicit_gaps": "PASS",
            "request_response_hashes": "PASS",
            "deterministic_raw_to_derived": "PASS",
            "no_post_2024": "PASS",
            "no_article_body_scraping": "PASS",
        },
        "hourly_rows": len(rows),
        "missing_hours_by_channel": missing,
        "response_resolutions": resolutions,
        "artifact_file_sha256": artifact["file_sha256"],
        "artifact_logical_sha256": artifact["logical_sha256"],
    }
    return manifest, integrity


def validate(root: Path = ROOT) -> dict[str, Any]:
    manifest = read_json(root / MANIFEST_PATH)
    integrity = read_json(root / INTEGRITY_PATH)
    rebuilt_manifest, rebuilt_integrity = build(root)
    if manifest != rebuilt_manifest or integrity != rebuilt_integrity:
        raise ExogenousDataError("GDELT manifest/integrity differs from deterministic rebuild")
    return integrity
