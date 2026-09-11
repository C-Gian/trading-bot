from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow as pa
import pytest
from app.research.artifacts import ArtifactError, validate_parquet, write_parquet

SCHEMA = pa.schema(
    [
        pa.field("fold", pa.int16(), nullable=False),
        pa.field("timestamp", pa.int64(), nullable=False),
        pa.field("value", pa.float64(), nullable=True),
    ]
)


def test_deterministic_parquet_round_trip(tmp_path: Path) -> None:
    rows: list[dict[str, object]] = [
        {"fold": 2020, "timestamp": 2, "value": None},
        {"fold": 2019, "timestamp": 1, "value": 0.25},
    ]
    first = write_parquet(
        tmp_path / "first.parquet",
        rows,
        schema=SCHEMA,
        sort_key=("fold", "timestamp"),
        root=tmp_path,
    )
    second = write_parquet(
        tmp_path / "second.parquet",
        reversed(rows),
        schema=SCHEMA,
        sort_key=("fold", "timestamp"),
        root=tmp_path,
    )
    assert first["logical_sha256"] == second["logical_sha256"]
    assert first["file_sha256"] == second["file_sha256"]
    assert validate_parquet(first, schema=SCHEMA, root=tmp_path).num_rows == 2


def test_artifacts_reject_nonfinite_and_duplicate_keys(tmp_path: Path) -> None:
    duplicate = [
        {"fold": 2019, "timestamp": 1, "value": 0.0},
        {"fold": 2019, "timestamp": 1, "value": 1.0},
    ]
    with pytest.raises(ArtifactError, match="strictly increasing"):
        write_parquet(
            tmp_path / "duplicate.parquet",
            duplicate,
            schema=SCHEMA,
            sort_key=("fold", "timestamp"),
            root=tmp_path,
        )
    with pytest.raises(ArtifactError, match="non-finite"):
        write_parquet(
            tmp_path / "nan.parquet",
            [{"fold": 2019, "timestamp": 1, "value": float("nan")}],
            schema=SCHEMA,
            sort_key=("fold", "timestamp"),
            root=tmp_path,
        )


def test_logical_hash_canonicalizes_arrow_date_and_timestamp_scalars(tmp_path: Path) -> None:
    schema = pa.schema(
        [
            pa.field("day", pa.date32(), nullable=False),
            pa.field("timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
        ]
    )
    manifest = write_parquet(
        tmp_path / "temporal.parquet",
        [{"day": date(2020, 1, 2), "timestamp": datetime(2020, 1, 2, 3, tzinfo=UTC)}],
        schema=schema,
        sort_key=("timestamp",),
        root=tmp_path,
    )
    assert len(manifest["logical_sha256"]) == 64
    assert validate_parquet(manifest, schema=schema, root=tmp_path).num_rows == 1
