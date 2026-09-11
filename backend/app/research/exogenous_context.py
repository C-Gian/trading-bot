"""Timestamp-only construction of EXOGENOUS_CONTEXT_V1; no market data is loaded."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .artifacts import write_parquet
from .exogenous import (
    ALFRED_SCHEMA,
    ALFRED_SERIES,
    CONTEXT_VERSION,
    END,
    GDELT_CHANNELS,
    GDELT_SCHEMA,
    HOUR,
    START,
    ExogenousDataError,
    file_sha256,
    hours,
    read_json,
)
from .wp004 import ROOT

CANONICAL_PATH = "data/derived/EXOGENOUS-context-v1.parquet"
MANIFEST_PATH = "data/manifests/EXOGENOUS-CONTEXT-DEV-v1.json"


def _slug(identifier: str) -> str:
    return identifier.lower()


def context_schema() -> pa.Schema:
    fields = [pa.field("timestamp", pa.timestamp("us", tz="UTC"), nullable=False)]
    for channel in GDELT_CHANNELS:
        prefix = _slug(channel)
        fields.extend(
            [
                pa.field(f"{prefix}_matched_articles", pa.int64()),
                pa.field(f"{prefix}_monitored_articles_norm", pa.int64()),
                pa.field(f"{prefix}_coverage_share", pa.float64()),
                pa.field(f"{prefix}_average_tone", pa.float64()),
                pa.field(f"{prefix}_data_available", pa.bool_(), nullable=False),
                pa.field(f"{prefix}_source_hour", pa.timestamp("us", tz="UTC")),
                pa.field(f"{prefix}_source_request_id", pa.string()),
            ]
        )
    for series_id in ALFRED_SERIES:
        prefix = _slug(series_id)
        fields.extend(
            [
                pa.field(f"{prefix}_value", pa.float64()),
                pa.field(f"{prefix}_data_available", pa.bool_(), nullable=False),
                pa.field(f"{prefix}_observation_date", pa.date32()),
                pa.field(f"{prefix}_vintage_start", pa.date32()),
                pa.field(f"{prefix}_age_observation_hours", pa.float64()),
                pa.field(f"{prefix}_age_vintage_hours", pa.float64()),
                pa.field(f"{prefix}_source_request_id", pa.string()),
            ]
        )
    return pa.schema(fields)


def _verified_table(root: Path, manifest_path: str, expected_schema: pa.Schema) -> pa.Table:
    manifest = read_json(root / manifest_path)
    artifact = manifest["file"]
    path = root / artifact["path"]
    if file_sha256(path) != artifact["file_sha256"]:
        raise ExogenousDataError("exogenous source Parquet hash mismatch")
    table = pq.read_table(path)
    if not table.schema.equals(expected_schema):
        raise ExogenousDataError("exogenous source Parquet schema mismatch")
    return table


def build_rows(root: Path = ROOT) -> list[dict[str, Any]]:
    news_table = _verified_table(
        root, "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json", GDELT_SCHEMA
    )
    macro_table = _verified_table(
        root, "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json", ALFRED_SCHEMA
    )
    macro_manifest = read_json(root / "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json")
    unavailable_vintages = {
        (item["series_id"], date.fromisoformat(item["vintage_date"]))
        for item in macro_manifest["source_unavailable_requests"]
    }
    news = {(row["channel_id"], row["hour"]): row for row in news_table.to_pylist()}
    revisions = sorted(
        macro_table.to_pylist(),
        key=lambda item: (
            item["availability_time"],
            item["series_id"],
            item["observation_date"],
        ),
    )
    states: dict[str, dict[date, dict[str, Any]]] = defaultdict(dict)
    latest: dict[str, dict[str, Any]] = {}
    revision_index = 0
    rows = []
    for timestamp in hours():
        while (
            revision_index < len(revisions)
            and revisions[revision_index]["availability_time"] <= timestamp
        ):
            record = revisions[revision_index]
            series_id, observation = record["series_id"], record["observation_date"]
            states[series_id][observation] = record
            if series_id not in latest or observation >= latest[series_id]["observation_date"]:
                latest[series_id] = record
            revision_index += 1
        row: dict[str, Any] = {"timestamp": timestamp}
        source_hour = timestamp - HOUR
        for channel in GDELT_CHANNELS:
            prefix = _slug(channel)
            item = news.get((channel, source_hour))
            available = bool(item and item["data_available"])
            source = item if available and item is not None else {}
            row.update(
                {
                    f"{prefix}_matched_articles": source.get("matched_articles"),
                    f"{prefix}_monitored_articles_norm": source.get("monitored_articles_norm"),
                    f"{prefix}_coverage_share": source.get("coverage_share"),
                    f"{prefix}_average_tone": source.get("average_tone"),
                    f"{prefix}_data_available": available,
                    f"{prefix}_source_hour": source.get("hour"),
                    f"{prefix}_source_request_id": source.get("source_request_id"),
                }
            )
        for series_id in ALFRED_SERIES:
            prefix = _slug(series_id)
            item = latest.get(series_id)
            source_vintage = timestamp.date() - timedelta(days=1)
            available = bool(
                item
                and item["availability_time"] <= timestamp
                and (series_id, source_vintage) not in unavailable_vintages
            )
            source = item if available and item is not None else {}
            observation_time = (
                datetime.combine(source["observation_date"], datetime.min.time(), UTC)
                if available
                else None
            )
            vintage_time = (
                datetime.combine(source["vintage_start"], datetime.min.time(), UTC)
                if available
                else None
            )
            row.update(
                {
                    f"{prefix}_value": source.get("value"),
                    f"{prefix}_data_available": available,
                    f"{prefix}_observation_date": source.get("observation_date"),
                    f"{prefix}_vintage_start": source.get("vintage_start"),
                    f"{prefix}_age_observation_hours": (
                        (timestamp - observation_time).total_seconds() / 3600
                        if observation_time
                        else None
                    ),
                    f"{prefix}_age_vintage_hours": (
                        (timestamp - vintage_time).total_seconds() / 3600 if vintage_time else None
                    ),
                    f"{prefix}_source_request_id": source.get("source_request_id"),
                }
            )
        rows.append(row)
    return rows


def build(root: Path = ROOT) -> dict[str, Any]:
    rows = build_rows(root)
    artifact = write_parquet(
        root / CANONICAL_PATH,
        rows,
        schema=context_schema(),
        sort_key=["timestamp"],
        root=root,
    )
    availability = {
        **{
            channel: sum(row[f"{_slug(channel)}_data_available"] for row in rows)
            for channel in GDELT_CHANNELS
        },
        **{
            series_id: sum(row[f"{_slug(series_id)}_data_available"] for row in rows)
            for series_id in ALFRED_SERIES
        },
    }
    return {
        "schema_version": 1,
        "manifest_id": "EXOGENOUS-CONTEXT-DEV-v1",
        "version": CONTEXT_VERSION,
        "contract": "docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md",
        "coverage": {"start": START.isoformat(), "end": END.isoformat()},
        "grid_source": "TIMESTAMP_GENERATION_ONLY",
        "btc_price_return_or_outcome_columns_loaded": False,
        "availability_rule": "SOURCE_AVAILABILITY_TIME_LE_TIMESTAMP",
        "full_history_standardization": False,
        "interpolation": False,
        "trading_score": False,
        "rows": len(rows),
        "source_available_rows": availability,
        "source_manifests": {
            "gdelt": {
                "path": "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json",
                "sha256": file_sha256(root / "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json"),
            },
            "alfred": {
                "path": "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json",
                "sha256": file_sha256(root / "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json"),
            },
        },
        "file": artifact,
        "post_2024_rows": 0,
    }


def validate(root: Path = ROOT) -> dict[str, Any]:
    manifest = read_json(root / MANIFEST_PATH)
    rebuilt = build(root)
    if manifest != rebuilt:
        raise ExogenousDataError("combined exogenous manifest differs from deterministic rebuild")
    return manifest
