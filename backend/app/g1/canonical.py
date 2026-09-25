"""Canonical serialization and content-derived identities for System G1 records.

Identities are SHA-256 digests of canonical JSON of the record content. They never include the
current wall-clock time, so the same sources, versions and configuration always reproduce the same
identities regardless of replay speed or adapter.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


def to_plain(value: Any) -> Any:
    """Convert records to JSON-ready primitives deterministically."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_plain(getattr(value, field.name)) for field in dataclasses.fields(value)
        }
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("System G1 timestamps must be timezone-aware UTC")
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are not canonical")
        return float(repr(round(value, 12)))
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [to_plain(item) for item in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        to_plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def content_id(prefix: str, payload: Any) -> str:
    """A deterministic record identity: `<prefix>-<first 24 hex of the content digest>`."""
    return f"{prefix}-{digest(payload)[:24]}"


def iso(value: datetime | None) -> str | None:
    return None if value is None else to_plain(value)
