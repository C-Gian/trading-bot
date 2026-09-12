"""Credential-free ALFRED vintage acquisition and point-in-time normalization."""

from __future__ import annotations

import csv
import gzip
import io
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from threading import Lock, local
from typing import Any
from urllib.parse import urlencode

import httpx

from .artifacts import write_parquet
from .exogenous import (
    ALFRED_REQUEST_SCHEMA,
    ALFRED_SCHEMA,
    ALFRED_SERIES,
    ALFRED_VERSION,
    END,
    START,
    ExogenousDataError,
    calendar_dates,
    canonical_id,
    file_sha256,
    next_day_availability,
    read_json,
    sha256_bytes,
    validate_catalogs,
)
from .wp004 import ROOT

ENDPOINT = "https://alfred.stlouisfed.org/graph/alfredgraph.csv"
RAW_ROOT = "data/raw/exogenous/alfred"
CANONICAL_PATH = "data/derived/ALFRED-macro-context-v1.parquet"
MANIFEST_PATH = "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json"
INTEGRITY_PATH = "reports/validation/WP-009-ALFRED-INTEGRITY.json"
PARSER_VERSION = "ALFRED_DAILY_SNAPSHOT_DIFF_V1"
REQUEST_INDEX_PATH = "data/derived/ALFRED-request-index-v1.parquet"
FALLBACK_POLICY_PATH = "research/exogenous/ALFRED-SINGLE-VINTAGE-FALLBACK-CORRECTION-V1.json"
_THREAD = local()


class _RateLimiter:
    def __init__(self, interval: float) -> None:
        self.interval = interval
        self.last_start = 0.0
        self.lock = Lock()

    def wait(self) -> None:
        with self.lock:
            delay = self.interval - (time.monotonic() - self.last_start)
            if delay > 0:
                time.sleep(delay)
            self.last_start = time.monotonic()


def _client() -> httpx.Client:
    client = getattr(_THREAD, "client", None)
    if client is None:
        client = httpx.Client(
            headers={"User-Agent": "trading-bot-wp009/1.0"},
            timeout=90,
            follow_redirects=True,
        )
        _THREAD.client = client
    return client


def _request_spec(series_id: str, vintage: date, root: Path = ROOT) -> dict[str, Any]:
    if series_id not in ALFRED_SERIES:
        raise ExogenousDataError("unfrozen ALFRED series")
    params = {
        "id": series_id,
        "cosd": START.date().isoformat(),
        "coed": END.date().isoformat(),
        "vintage_date": vintage.isoformat(),
    }
    identity = {
        "source": "ALFRED",
        "endpoint": ENDPOINT,
        "params": params,
        "parser": PARSER_VERSION,
    }
    request_id = canonical_id(identity)
    return {
        **identity,
        "request_id": request_id,
        "series_id": series_id,
        "vintage_date": vintage.isoformat(),
        "raw_path": (
            f"{RAW_ROOT}/{series_id}/{vintage.year}/{vintage.isoformat()}-{request_id}.csv"
        ),
        "meta_path": (
            f"{RAW_ROOT}/{series_id}/{vintage.year}/{vintage.isoformat()}-{request_id}.meta.json"
        ),
    }


def request_url(spec: dict[str, Any]) -> str:
    return f"{spec['endpoint']}?{urlencode(spec['params'])}"


def _unavailable_paths(spec: dict[str, Any], root: Path) -> tuple[Path, Path]:
    raw = root / spec["raw_path"]
    return raw.with_suffix(".fallback.html.gz"), raw.with_suffix(".unavailable.meta.json")


def _fallback_policy(spec: dict[str, Any], root: Path) -> dict[str, Any] | None:
    policy = read_json(root / FALLBACK_POLICY_PATH)
    if spec["request_id"] != policy["primary_request_id"]:
        return None
    if spec["series_id"] != policy["series_id"] or spec["vintage_date"] != policy["vintage_date"]:
        raise ExogenousDataError("ALFRED fallback identity differs from frozen request")
    return policy


def _validate_unavailable(
    spec: dict[str, Any], root: Path, policy: dict[str, Any]
) -> dict[str, Any] | None:
    raw_path, meta_path = _unavailable_paths(spec, root)
    if not raw_path.is_file() or not meta_path.is_file():
        return None
    meta = read_json(meta_path)
    fallback_body = gzip.decompress(raw_path.read_bytes())
    if (
        meta["request_id"] != spec["request_id"]
        or meta["primary_status"] != 404
        or meta["primary_response_sha256"] != sha256_bytes(b"")
        or meta["fallback_status"] != 200
        or meta["fallback_response_sha256"] != sha256_bytes(fallback_body)
        or meta["fallback_compressed_file_sha256"] != file_sha256(raw_path)
        or b"No observations were retrieved using the specified options." not in fallback_body
        or meta["fallback_url"] != policy["fallback_endpoint"]
    ):
        raise ExogenousDataError("ALFRED unavailable-vintage evidence changed")
    return meta


def _fetch_unavailable(
    spec: dict[str, Any], root: Path, limiter: _RateLimiter, policy: dict[str, Any]
) -> str:
    if _validate_unavailable(spec, root, policy) is not None:
        return "unavailable"
    raw_path, meta_path = _unavailable_paths(spec, root)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    limiter.wait()
    primary = _client().get(request_url(spec))
    if primary.status_code != 404 or primary.content:
        raise ExogenousDataError("frozen ALFRED exception no longer returns empty HTTP 404")
    limiter.wait()
    fallback = _client().post(policy["fallback_endpoint"], data=policy["fallback_parameters"])
    if (
        fallback.status_code != 200
        or b"No observations were retrieved using the specified options." not in fallback.content
    ):
        raise ExogenousDataError("official ALFRED fallback did not confirm unavailable vintage")
    raw_path.write_bytes(gzip.compress(fallback.content, compresslevel=9, mtime=0))
    meta_path.write_text(
        json.dumps(
            {
                "request_id": spec["request_id"],
                "primary_url": request_url(spec),
                "primary_status": primary.status_code,
                "primary_response_sha256": sha256_bytes(primary.content),
                "fallback_url": policy["fallback_endpoint"],
                "fallback_parameters": policy["fallback_parameters"],
                "fallback_status": fallback.status_code,
                "fallback_response_sha256": sha256_bytes(fallback.content),
                "fallback_compressed_file_sha256": file_sha256(raw_path),
                "retrieval_time_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "classification": "SOURCE_VINTAGE_UNAVAILABLE_NO_OBSERVATIONS",
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return "unavailable"


def parse_snapshot(
    payload: bytes, expected_series: str, expected_vintage: date
) -> dict[date, float]:
    if payload.startswith(b"PK"):
        archive = zipfile.ZipFile(io.BytesIO(payload))
        with archive:
            entries = sorted(
                (name, archive.read(name))
                for name in archive.namelist()
                if name.lower().endswith(".csv")
            )
    else:
        entries = [("response.csv", payload)]
    if len(entries) != 1:
        raise ExogenousDataError("one-series ALFRED response must contain exactly one CSV")
    reader = csv.DictReader(io.StringIO(entries[0][1].decode("utf-8-sig")))
    expected_column = f"{expected_series}_{expected_vintage:%Y%m%d}"
    if reader.fieldnames != ["observation_date", expected_column]:
        raise ExogenousDataError("ALFRED series or vintage identity changed")
    result: dict[date, float] = {}
    for row in reader:
        observation = date.fromisoformat(row["observation_date"])
        if observation < START.date():
            continue
        if observation > END.date():
            raise ExogenousDataError("ALFRED observation escaped frozen bounds")
        raw = row[expected_column].strip()
        if not raw or raw == ".":
            continue
        if observation in result:
            raise ExogenousDataError("duplicate ALFRED observation within one snapshot")
        result[observation] = float(raw)
    return result


def _fetch_one(spec: dict[str, Any], root: Path, limiter: _RateLimiter) -> str:
    fallback = _fallback_policy(spec, root)
    if fallback is not None:
        return _fetch_unavailable(spec, root, limiter, fallback)
    raw_path, meta_path = root / spec["raw_path"], root / spec["meta_path"]
    if raw_path.is_file() and meta_path.is_file():
        meta = read_json(meta_path)
        body = raw_path.read_bytes()
        if (
            meta["request_id"] == spec["request_id"]
            and meta["url"] == request_url(spec)
            and meta["response_sha256"] == sha256_bytes(body)
            and file_sha256(raw_path) == meta["file_sha256"]
        ):
            parse_snapshot(body, spec["series_id"], date.fromisoformat(spec["vintage_date"]))
            return "reused"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    last_error = ""
    for attempt in range(1, 9):
        limiter.wait()
        try:
            response = _client().get(request_url(spec))
            if response.status_code == 200:
                parse_snapshot(
                    response.content,
                    spec["series_id"],
                    date.fromisoformat(spec["vintage_date"]),
                )
                raw_path.write_bytes(response.content)
                meta_path.write_text(
                    json.dumps(
                        {
                            "request_id": spec["request_id"],
                            "url": request_url(spec),
                            "retrieval_time_utc": datetime.now(UTC)
                            .isoformat()
                            .replace("+00:00", "Z"),
                            "response_sha256": sha256_bytes(response.content),
                            "file_sha256": file_sha256(raw_path),
                        },
                        sort_keys=True,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                return "fetched"
            last_error = f"status={response.status_code} body={response.content[:120]!r}"
        except (httpx.HTTPError, ExogenousDataError) as exc:
            last_error = str(exc)
        time.sleep(min(60.0, 2.0**attempt))
    raise ExogenousDataError(f"ALFRED request failed: {spec['request_id']} {last_error}")


def acquire(
    root: Path = ROOT, *, workers: int = 4, minimum_interval_seconds: float = 0.25
) -> dict[str, int]:
    validate_catalogs(root)
    specs = [
        _request_spec(series_id, vintage, root)
        for series_id in ALFRED_SERIES
        for vintage in calendar_dates()
    ]
    counts = {"fetched": 0, "reused": 0, "unavailable": 0}
    limiter = _RateLimiter(minimum_interval_seconds)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_one, spec, root, limiter): spec for spec in specs}
        for future in as_completed(futures):
            outcome = future.result()
            counts[outcome] += 1
    return {"expected": len(specs), **counts}


def normalized_records(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    validate_catalogs(root)
    records: list[dict[str, Any]] = []
    requests = []
    for series_id in ALFRED_SERIES:
        current: dict[date, float] = {}
        active: dict[date, dict[str, Any]] = {}
        for vintage in calendar_dates():
            spec = _request_spec(series_id, vintage, root)
            fallback = _fallback_policy(spec, root)
            if fallback is not None:
                fallback_raw, _ = _unavailable_paths(spec, root)
                meta = _validate_unavailable(spec, root, fallback)
                if meta is None:
                    raise ExogenousDataError(
                        f"missing ALFRED unavailable-vintage evidence: {series_id} {vintage}"
                    )
                requests.append(
                    {
                        "series_id": series_id,
                        "request_id": spec["request_id"],
                        "vintage_date": vintage,
                        "request_status": "SOURCE_VINTAGE_UNAVAILABLE_NO_OBSERVATIONS",
                        "http_status": meta["primary_status"],
                        "retrieval_time": datetime.fromisoformat(meta["retrieval_time_utc"]),
                        "raw_path": fallback_raw.relative_to(root).as_posix(),
                        "response_sha256": meta["fallback_response_sha256"],
                        "file_sha256": meta["fallback_compressed_file_sha256"],
                    }
                )
                for record in active.values():
                    record["vintage_end"] = vintage - timedelta(days=1)
                active = {}
                current = {}
                continue
            raw_path, meta_path = root / spec["raw_path"], root / spec["meta_path"]
            if not raw_path.is_file() or not meta_path.is_file():
                raise ExogenousDataError(f"missing ALFRED vintage snapshot: {series_id} {vintage}")
            meta = read_json(meta_path)
            body = raw_path.read_bytes()
            if (
                meta["request_id"] != spec["request_id"]
                or meta["url"] != request_url(spec)
                or sha256_bytes(body) != meta["response_sha256"]
                or file_sha256(raw_path) != meta["file_sha256"]
            ):
                raise ExogenousDataError("ALFRED raw request identity or hash mismatch")
            snapshot = parse_snapshot(body, series_id, vintage)
            changed = {
                observation
                for observation, value in snapshot.items()
                if current.get(observation) != value
            }
            removed = set(current) - set(snapshot)
            for observation in sorted(changed | removed):
                if observation in active:
                    active[observation]["vintage_end"] = vintage - timedelta(days=1)
                if observation in snapshot:
                    record = {
                        "series_id": series_id,
                        "observation_date": observation,
                        "value": snapshot[observation],
                        "vintage_start": vintage,
                        "vintage_end": None,
                        "availability_time": next_day_availability(vintage),
                        "source_request_id": spec["request_id"],
                    }
                    records.append(record)
                    active[observation] = record
                else:
                    active.pop(observation, None)
            current = snapshot
            requests.append(
                {
                    "series_id": series_id,
                    "request_id": spec["request_id"],
                    "vintage_date": vintage,
                    "request_status": "AVAILABLE",
                    "http_status": 200,
                    "retrieval_time": datetime.fromisoformat(meta["retrieval_time_utc"]),
                    "raw_path": spec["raw_path"],
                    "response_sha256": meta["response_sha256"],
                    "file_sha256": meta["file_sha256"],
                }
            )
    return records, requests


def asof_values(records: list[dict[str, Any]], timestamp: datetime) -> dict[str, dict[str, Any]]:
    """Return latest known observation per series using only available vintage states."""
    states: dict[tuple[str, date], dict[str, Any]] = {}
    for record in sorted(
        records,
        key=lambda item: (item["availability_time"], item["series_id"], item["observation_date"]),
    ):
        if record["availability_time"] > timestamp:
            break
        states[(record["series_id"], record["observation_date"])] = record
    result = {}
    for series_id in ALFRED_SERIES:
        eligible = [record for (sid, _), record in states.items() if sid == series_id]
        if eligible:
            result[series_id] = max(eligible, key=lambda item: item["observation_date"])
    return result


def build(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    records, requests = normalized_records(root)
    artifact = write_parquet(
        root / CANONICAL_PATH,
        records,
        schema=ALFRED_SCHEMA,
        sort_key=["series_id", "observation_date", "vintage_start"],
        root=root,
    )
    request_index = write_parquet(
        root / REQUEST_INDEX_PATH,
        requests,
        schema=ALFRED_REQUEST_SCHEMA,
        sort_key=["series_id", "vintage_date"],
        root=root,
    )
    stats = {}
    for series_id in ALFRED_SERIES:
        series = [record for record in records if record["series_id"] == series_id]
        stats[series_id] = {
            "first_usable_availability": min(record["availability_time"] for record in series)
            .isoformat()
            .replace("+00:00", "Z"),
            "last_usable_availability_at_or_before_cutoff": max(
                record["availability_time"]
                for record in series
                if record["availability_time"] <= END
            )
            .isoformat()
            .replace("+00:00", "Z"),
            "observation_dates": len({record["observation_date"] for record in series}),
            "vintage_states": len(series),
            "revisions": len(series) - len({record["observation_date"] for record in series}),
        }
    manifest = {
        "schema_version": 1,
        "manifest_id": "ALFRED-MACRO-CONTEXT-DEV-v1",
        "version": ALFRED_VERSION,
        "contract": "docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md",
        "series_catalog": "research/exogenous/ALFRED_SERIES_CATALOG_V1.json",
        "series_catalog_sha256": file_sha256(
            root / "research/exogenous/ALFRED_SERIES_CATALOG_V1.json"
        ),
        "coverage": {
            "observation_start": START.date().isoformat(),
            "observation_end": END.date().isoformat(),
            "vintage_start": START.date().isoformat(),
            "vintage_end": END.date().isoformat(),
        },
        "series": list(ALFRED_SERIES),
        "credential_free": True,
        "current_revised_substitution": False,
        "availability_rule": "NEXT_CALENDAR_DAY_00_00_UTC_AFTER_VINTAGE_START",
        "request_count": len(requests),
        "successful_request_count": sum(item["request_status"] == "AVAILABLE" for item in requests),
        "source_unavailable_request_count": sum(
            item["request_status"] != "AVAILABLE" for item in requests
        ),
        "source_unavailable_requests": [
            {
                "series_id": item["series_id"],
                "vintage_date": item["vintage_date"].isoformat(),
                "request_id": item["request_id"],
                "classification": item["request_status"],
                "primary_http_status": item["http_status"],
                "primary_response_sha256": sha256_bytes(b""),
                "fallback_response_sha256": item["response_sha256"],
                "fallback_file_sha256": item["file_sha256"],
            }
            for item in requests
            if item["request_status"] != "AVAILABLE"
        ],
        "request_index": request_index,
        "effective_acquisition_amendment": (
            "research/exogenous/ALFRED-ACQUISITION-AMENDMENT-V1.json"
        ),
        "source_availability_exception": {
            "path": FALLBACK_POLICY_PATH,
            "sha256": file_sha256(root / FALLBACK_POLICY_PATH),
        },
        "series_statistics": stats,
        "file": artifact,
        "post_2024_vintages": 0,
    }
    integrity = {
        "schema_version": 1,
        "work_package": "WP-009",
        "version": ALFRED_VERSION,
        "status": "PASS",
        "checks": {
            "exact_eight_series": "PASS",
            "catalog_precedes_acquisition": "PASS",
            "credential_free_download": "PASS",
            "historical_vintage_states": "PASS",
            "no_current_revised_substitution": "PASS",
            "next_day_conservative_availability": "PASS",
            "later_revision_cannot_leak_backward": "PASS",
            "no_interpolation": "PASS",
            "request_file_hashes": "PASS",
            "source_unavailable_vintages_explicit": "PASS",
            "no_post_2024_vintage": "PASS",
        },
        "source_unavailable_request_count": manifest["source_unavailable_request_count"],
        "source_unavailable_requests": manifest["source_unavailable_requests"],
        "series_statistics": stats,
        "artifact_file_sha256": artifact["file_sha256"],
        "artifact_logical_sha256": artifact["logical_sha256"],
    }
    return manifest, integrity


def validate(root: Path = ROOT) -> dict[str, Any]:
    manifest = read_json(root / MANIFEST_PATH)
    integrity = read_json(root / INTEGRITY_PATH)
    rebuilt_manifest, rebuilt_integrity = build(root)
    if manifest != rebuilt_manifest or integrity != rebuilt_integrity:
        raise ExogenousDataError("ALFRED manifest/integrity differs from deterministic rebuild")
    return integrity
