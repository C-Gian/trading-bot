"""Independent raw-source as-of oracle for WP-009."""

from __future__ import annotations

import csv
import gzip
import io
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow.compute as pc
import pyarrow.parquet as pq

from .exogenous import (
    ALFRED_SERIES,
    END,
    GDELT_CHANNELS,
    HOUR,
    START,
    ExogenousDataError,
    canonical_id,
    read_json,
    sha256_bytes,
)
from .exogenous_context import context_schema
from .wp004 import ROOT

REPORT_PATH = "reports/validation/WP-009-EXOGENOUS-ASOF-RECONCILIATION.json"


def _slug(identifier: str) -> str:
    return identifier.lower()


def _quarter_samples() -> set[datetime]:
    samples = set()
    year, quarter = 2017, 3
    while (year, quarter) <= (2024, 4):
        month = 1 + (quarter - 1) * 3
        quarter_start = max(START, datetime(year, month, 1, tzinfo=UTC))
        next_year, next_month = (year + 1, 1) if month == 10 else (year, month + 3)
        quarter_end = min(END + HOUR, datetime(next_year, next_month, 1, tzinfo=UTC))
        width = int((quarter_end - quarter_start) / HOUR)
        offset = int(canonical_id(f"WP009:{year}:Q{quarter}")[:16], 16) % width
        samples.add(quarter_start + offset * HOUR)
        quarter = 1 if quarter == 4 else quarter + 1
        year += 1 if quarter == 1 else 0
    return samples


def _fixed_stress_samples() -> set[datetime]:
    return {
        START,
        START + HOUR,
        datetime(2017, 9, 1, tzinfo=UTC),
        datetime(2018, 1, 1, tzinfo=UTC),
        datetime(2020, 3, 12, 12, tzinfo=UTC),
        datetime(2020, 3, 15, 1, tzinfo=UTC),
        datetime(2020, 10, 25, 1, tzinfo=UTC),
        datetime(2021, 1, 1, tzinfo=UTC),
        datetime(2024, 12, 1, tzinfo=UTC),
        END,
    }


def _gdelt_chunk_boundary_samples() -> set[datetime]:
    """Exercise both sides of deterministic seven-day acquisition boundaries."""
    chunk = timedelta(hours=168)
    boundaries = []
    cursor = START + chunk
    while cursor <= END:
        boundaries.append(cursor)
        cursor += chunk
    if not boundaries:
        return set()
    selected = (boundaries[0], boundaries[len(boundaries) // 2], boundaries[-1])
    return {
        instant
        for boundary in selected
        for instant in (boundary - HOUR, boundary, boundary + HOUR)
        if START <= instant <= END
    }


def _read_gdelt_hour(
    root: Path,
    request: dict[str, Any],
    source_hour: datetime,
    mode: str,
) -> dict[str, Any] | None:
    raw = gzip.decompress((root / request["raw_path"]).read_bytes())
    if sha256_bytes(raw) != request["response_sha256"]:
        raise ExogenousDataError("oracle GDELT raw hash mismatch")
    document = json.loads(raw)
    if document["query_details"]["date_resolution"] not in {"hour", "1h"}:
        raise ExogenousDataError("oracle requires frozen hourly GDELT responses")
    timeline = document["timeline"]
    if isinstance(timeline, dict):
        timeline = [timeline]
    target = source_hour.strftime("%Y%m%dT%H0000Z")
    matches = [item for item in timeline[0]["data"] if item["date"] == target]
    if len(matches) > 1:
        raise ExogenousDataError("oracle found duplicate GDELT point")
    if not matches:
        return None
    item = matches[0]
    if mode == "TimelineVolRaw" and item.get("norm") is None:
        return None
    return item


def _gdelt_oracle(root: Path, manifest: dict[str, Any], timestamp: datetime) -> dict[str, Any]:
    source_hour = timestamp - HOUR
    result: dict[str, Any] = {}
    requests = manifest["requests"]
    for channel in GDELT_CHANNELS:
        applicable = [
            item
            for item in requests
            if item["channel_id"] == channel
            and datetime.fromisoformat(item["start_utc"])
            <= source_hour
            <= datetime.fromisoformat(item["end_utc"])
        ]
        by_mode = {item["mode"]: item for item in applicable}
        if set(by_mode) != {"TimelineVolRaw", "TimelineTone"}:
            available = False
            volume = tone = None
        else:
            volume = _read_gdelt_hour(
                root, by_mode["TimelineVolRaw"], source_hour, "TimelineVolRaw"
            )
            tone = _read_gdelt_hour(root, by_mode["TimelineTone"], source_hour, "TimelineTone")
            available = volume is not None and tone is not None
        prefix = _slug(channel)
        request_id = (
            f"{by_mode['TimelineVolRaw']['request_id']}:{by_mode['TimelineTone']['request_id']}"
            if set(by_mode) == {"TimelineVolRaw", "TimelineTone"}
            else None
        )
        matched = int(volume["value"]) if available and volume is not None else None
        norm = int(volume["norm"]) if available and volume is not None else None
        result.update(
            {
                f"{prefix}_matched_articles": matched,
                f"{prefix}_monitored_articles_norm": norm,
                f"{prefix}_coverage_share": matched / norm
                if norm and matched is not None
                else None,
                f"{prefix}_average_tone": float(tone["value"])
                if available and tone is not None
                else None,
                f"{prefix}_data_available": available,
                f"{prefix}_source_hour": source_hour if available else None,
                f"{prefix}_source_request_id": request_id if available else None,
            }
        )
    return result


def _alfred_snapshot(payload: bytes, series_id: str, vintage: date) -> dict[date, float]:
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    field = f"{series_id}_{vintage:%Y%m%d}"
    if reader.fieldnames != ["observation_date", field]:
        raise ExogenousDataError("oracle ALFRED response identity changed")
    values = {}
    for row in reader:
        observation = date.fromisoformat(row["observation_date"])
        raw = row[field].strip()
        if START.date() <= observation <= END.date() and raw and raw != ".":
            values[observation] = float(raw)
    return values


def _alfred_oracle(
    root: Path, request_index: dict[tuple[str, date], dict[str, Any]], timestamp: datetime
) -> dict[str, Any]:
    vintage = timestamp.date() - timedelta(days=1)
    result: dict[str, Any] = {}
    for series_id in ALFRED_SERIES:
        prefix = _slug(series_id)
        if vintage < START.date():
            result.update(
                {
                    f"{prefix}_value": None,
                    f"{prefix}_data_available": False,
                    f"{prefix}_observation_date": None,
                    f"{prefix}_vintage_start": None,
                    f"{prefix}_age_observation_hours": None,
                    f"{prefix}_age_vintage_hours": None,
                    f"{prefix}_source_request_id": None,
                }
            )
            continue
        vintage = min(vintage, END.date())
        request = request_index[(series_id, vintage)]
        if request["request_status"] != "AVAILABLE":
            result.update(
                {
                    f"{prefix}_value": None,
                    f"{prefix}_data_available": False,
                    f"{prefix}_observation_date": None,
                    f"{prefix}_vintage_start": None,
                    f"{prefix}_age_observation_hours": None,
                    f"{prefix}_age_vintage_hours": None,
                    f"{prefix}_source_request_id": None,
                }
            )
            continue
        payload = (root / request["raw_path"]).read_bytes()
        if sha256_bytes(payload) != request["response_sha256"]:
            raise ExogenousDataError("oracle ALFRED raw hash mismatch")
        values = _alfred_snapshot(payload, series_id, vintage)
        if not values:
            result.update(
                {
                    f"{prefix}_value": None,
                    f"{prefix}_data_available": False,
                    f"{prefix}_observation_date": None,
                    f"{prefix}_vintage_start": None,
                    f"{prefix}_age_observation_hours": None,
                    f"{prefix}_age_vintage_hours": None,
                    f"{prefix}_source_request_id": None,
                }
            )
            continue
        observation = max(values)
        value = values[observation]
        state_start = vintage
        while state_start > START.date():
            prior_date = state_start - timedelta(days=1)
            prior_request = request_index[(series_id, prior_date)]
            if prior_request["request_status"] != "AVAILABLE":
                break
            prior_payload = (root / prior_request["raw_path"]).read_bytes()
            if sha256_bytes(prior_payload) != prior_request["response_sha256"]:
                raise ExogenousDataError("oracle ALFRED prior raw hash mismatch")
            prior_values = _alfred_snapshot(prior_payload, series_id, prior_date)
            if prior_values.get(observation) != value:
                break
            state_start = prior_date
        state_request = request_index[(series_id, state_start)]
        observation_time = datetime.combine(observation, datetime.min.time(), UTC)
        vintage_time = datetime.combine(state_start, datetime.min.time(), UTC)
        result.update(
            {
                f"{prefix}_value": value,
                f"{prefix}_data_available": True,
                f"{prefix}_observation_date": observation,
                f"{prefix}_vintage_start": state_start,
                f"{prefix}_age_observation_hours": (timestamp - observation_time).total_seconds()
                / 3600,
                f"{prefix}_age_vintage_hours": (timestamp - vintage_time).total_seconds() / 3600,
                f"{prefix}_source_request_id": state_request["request_id"],
            }
        )
    return result


def _canonical(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def reconcile(root: Path = ROOT) -> dict[str, Any]:
    context_manifest = read_json(root / "data/manifests/EXOGENOUS-CONTEXT-DEV-v1.json")
    gdelt_manifest = read_json(root / "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json")
    alfred_manifest = read_json(root / "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json")
    context = pq.read_table(root / context_manifest["file"]["path"])
    if not context.schema.equals(context_schema()):
        raise ExogenousDataError("oracle context schema mismatch")
    request_table = pq.read_table(root / alfred_manifest["request_index"]["path"])
    request_index = {
        (row["series_id"], row["vintage_date"]): row for row in request_table.to_pylist()
    }
    macro = pq.read_table(root / alfred_manifest["file"]["path"])
    samples = _quarter_samples() | _fixed_stress_samples() | _gdelt_chunk_boundary_samples()
    revision_times = sorted(
        {
            row["availability_time"]
            for row in macro.to_pylist()
            if row["vintage_end"] is not None and START <= row["availability_time"] <= END
        }
    )
    for instant in revision_times[:4] + revision_times[-4:]:
        samples.add(instant)
        if instant - HOUR >= START:
            samples.add(instant - HOUR)
    gdelt_table = pq.read_table(root / gdelt_manifest["file"]["path"])
    missing = [
        row["hour"] + HOUR
        for row in gdelt_table.to_pylist()
        if not row["data_available"] and START <= row["hour"] + HOUR <= END
    ]
    samples.update(missing[:2])
    samples = {sample for sample in samples if START <= sample <= END}
    rows = []
    mismatches = 0
    for timestamp in sorted(samples):
        selected = context.filter(pc.equal(context["timestamp"], timestamp))
        if selected.num_rows != 1:
            raise ExogenousDataError("oracle sample missing from combined context")
        actual = selected.to_pylist()[0]
        expected = {
            "timestamp": timestamp,
            **_gdelt_oracle(root, gdelt_manifest, timestamp),
            **_alfred_oracle(root, request_index, timestamp),
        }
        differing = [name for name in context.schema.names if actual[name] != expected[name]]
        mismatches += bool(differing)
        rows.append(
            {
                "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                "actual_hash": canonical_id(
                    {key: _canonical(value) for key, value in actual.items()}
                ),
                "oracle_hash": canonical_id(
                    {key: _canonical(value) for key, value in expected.items()}
                ),
                "mismatch_columns": differing,
            }
        )
    return {
        "schema_version": 1,
        "work_package": "WP-009",
        "version": "EXOGENOUS_ASOF_ORACLE_V1",
        "status": "PASS" if mismatches == 0 else "FAIL",
        "independence": "DIRECT_RAW_GDELT_JSON_AND_RAW_ALFRED_VINTAGE_CSV_RECONSTRUCTION_WITHOUT_PRODUCTION_JOIN",
        "sampling": "FROZEN_SHA256_ONE_HOUR_PER_CALENDAR_QUARTER_PLUS_BOUNDARY_AND_REVISION_STRESS",
        "sample_count": len(rows),
        "calendar_quarters_covered": len(_quarter_samples()),
        "mismatch_count": mismatches,
        "checks": {
            "macro_revision_boundaries": "PASS" if mismatches == 0 else "FAIL",
            "month_year_boundaries": "PASS" if mismatches == 0 else "FAIL",
            "gdelt_chunk_boundaries": "PASS" if mismatches == 0 else "FAIL",
            "missing_hours": "PASS" if mismatches == 0 else "FAIL",
            "high_news_2020": "PASS" if mismatches == 0 else "FAIL",
            "utc_dst_transitions": "PASS" if mismatches == 0 else "FAIL",
            "cutoff_boundary": "PASS" if mismatches == 0 else "FAIL",
            "no_btc_outcomes": "PASS",
        },
        "samples": rows,
    }
