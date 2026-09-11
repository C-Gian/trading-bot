"""Deterministic compact research artifacts for WP-008 and later."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

ARTIFACT_STORAGE_VERSION = "RESEARCH_ARTIFACT_STORAGE_V1"
PARQUET_SCHEMA_VERSION = 1
WRITER_SETTINGS = {
    "compression": "zstd",
    "compression_level": 9,
    "data_page_version": "1.0",
    "use_dictionary": False,
    "version": "2.6",
    "write_statistics": True,
}


class ArtifactError(ValueError):
    """A compact artifact violated its declared deterministic contract."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_scalar(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ArtifactError("non-finite values are forbidden in research artifacts")
        if value == 0.0:
            return 0.0
    return value


def logical_hash(table: pa.Table) -> str:
    """Encoding-independent SHA-256 over schema and row content."""
    table = table.combine_chunks()
    payload = {
        "schema": [(field.name, str(field.type), field.nullable) for field in table.schema],
        "rows": [
            {name: _canonical_scalar(row[name]) for name in table.column_names}
            for row in table.to_pylist()
        ],
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sorted_table(
    rows: Iterable[Mapping[str, Any]], schema: pa.Schema, sort_key: Sequence[str]
) -> pa.Table:
    records = list(rows)
    expected = set(schema.names)
    if any(set(record) != expected for record in records):
        raise ArtifactError("artifact rows must match the fixed schema exactly")
    if not sort_key or not set(sort_key) <= expected:
        raise ArtifactError("artifact sort key is empty or outside the schema")
    records.sort(key=lambda row: tuple(row[name] for name in sort_key))
    table = pa.Table.from_pylist(records, schema=schema)
    if table.num_rows > 1:
        keys = [tuple(row[name] for name in sort_key) for row in table.to_pylist()]
        if any(left >= right for left, right in zip(keys, keys[1:], strict=False)):
            raise ArtifactError("artifact sort key must be strictly increasing")
    return table


def write_parquet(
    path: Path,
    rows: Iterable[Mapping[str, Any]],
    *,
    schema: pa.Schema,
    sort_key: Sequence[str],
    root: Path,
) -> dict[str, Any]:
    """Write a deterministic ZSTD Parquet artifact and return its compact manifest."""
    resolved_root, resolved_path = root.resolve(), path.resolve()
    if resolved_root not in resolved_path.parents:
        raise ArtifactError("artifact path must stay inside the repository")
    table = sorted_table(rows, schema, sort_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, **WRITER_SETTINGS)
    return {
        "artifact_storage_version": ARTIFACT_STORAGE_VERSION,
        "schema_version": PARQUET_SCHEMA_VERSION,
        "path": path.relative_to(root).as_posix(),
        "format": "PARQUET_ZSTD",
        "rows": table.num_rows,
        "columns": [
            {"name": field.name, "type": str(field.type), "nullable": field.nullable}
            for field in schema
        ],
        "sort_key": list(sort_key),
        "file_sha256": file_sha256(path),
        "logical_sha256": logical_hash(table),
        "writer": {**WRITER_SETTINGS, "pyarrow_version": pa.__version__},
    }


def validate_parquet(manifest: Mapping[str, Any], *, schema: pa.Schema, root: Path) -> pa.Table:
    if manifest["artifact_storage_version"] != ARTIFACT_STORAGE_VERSION:
        raise ArtifactError("artifact storage version changed")
    path = root / manifest["path"]
    if file_sha256(path) != manifest["file_sha256"]:
        raise ArtifactError("Parquet file hash mismatch")
    table = pq.read_table(path)
    if not table.schema.equals(schema):
        raise ArtifactError("Parquet schema mismatch")
    if table.num_rows != manifest["rows"]:
        raise ArtifactError("Parquet row count mismatch")
    expected = sorted_table(table.to_pylist(), schema, manifest["sort_key"])
    if table.to_pylist() != expected.to_pylist():
        raise ArtifactError("Parquet rows are not deterministically sorted")
    if logical_hash(table) != manifest["logical_sha256"]:
        raise ArtifactError("Parquet logical hash mismatch")
    return table
