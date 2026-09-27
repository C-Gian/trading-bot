"""Append-only, immutable G2 record store with deterministic canonical hashing.

There is no update or delete. Re-appending an identity is accepted only for byte-identical content
(idempotent replay); any different content under an issued identity is refused. Consumers read
per-type, availability-ordered views; the causal view never returns a record whose `available_at`
is after the cursor.
"""

from __future__ import annotations

import bisect
import dataclasses
import hashlib
import json
import math
from collections.abc import Iterator
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.g1.store import ImmutableRecordError, record_id

__all__ = ["G2Store", "ImmutableRecordError"]


class G2Store:
    def __init__(self) -> None:
        self._records: list[Any] = []
        self._by_id: dict[str, Any] = {}
        self._by_type: dict[type, list[Any]] = {}
        self._available: dict[type, list[datetime]] = {}

    def append(self, record: Any) -> Any:
        params = getattr(type(record), "__dataclass_params__", None)
        if not dataclasses.is_dataclass(record) or params is None or not params.frozen:
            raise ImmutableRecordError("only frozen records may be issued")
        identity = record_id(record)
        existing = self._by_id.get(identity)
        if existing is not None:
            if canonical_bytes(existing) != canonical_bytes(record):
                raise ImmutableRecordError(f"record {identity} was already issued differently")
            return existing
        kind = type(record)
        available: datetime = getattr(record, "available_at")  # noqa: B009
        times = self._available.setdefault(kind, [])
        if times and available < times[-1]:
            raise ImmutableRecordError("records of one type are appended in availability order")
        self._by_id[identity] = record
        self._records.append(record)
        self._by_type.setdefault(kind, []).append(record)
        times.append(available)
        return record

    def get(self, identity: str) -> Any | None:
        return self._by_id.get(identity)

    def __iter__(self) -> Iterator[Any]:
        return iter(tuple(self._records))

    def __len__(self) -> int:
        return len(self._records)

    def of_type(self, kind: type) -> list[Any]:
        return list(self._by_type.get(kind, ()))

    def visible(self, kind: type, cursor: datetime) -> list[Any]:
        """Records of one type with `available_at <= cursor` (a causal prefix)."""
        rows = self._by_type.get(kind, [])
        hi = bisect.bisect_right(self._available.get(kind, []), cursor)
        return rows[:hi]

    def counts(self) -> dict[str, int]:
        return {
            kind.__name__: len(rows)
            for kind, rows in sorted(self._by_type.items(), key=lambda item: item[0].__name__)
        }

    def fingerprint(self) -> str:
        """SHA-256 over the canonical bytes of every record in issue order."""
        digest = hashlib.sha256()
        for record in self._records:
            digest.update(canonical_bytes(record))
            digest.update(b"\n")
        return digest.hexdigest()


_FIELDS: dict[type, tuple[str, ...]] = {}


def plain(value: Any) -> Any:
    """JSON-ready primitives; identical semantics to `app.g1.canonical.to_plain`."""
    kind = type(value)
    if value is None or kind is str or kind is int or kind is bool:
        return value
    if kind is float:
        if not math.isfinite(value):
            raise ValueError("non-finite floats are not canonical")
        return float(repr(round(value, 12)))
    if kind is tuple or kind is list:
        return [plain(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if kind is datetime:
        if value.tzinfo is None:
            raise ValueError("G2 timestamps must be timezone-aware UTC")
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    names = _FIELDS.get(kind)
    if names is None and dataclasses.is_dataclass(value) and not isinstance(value, type):
        names = _FIELDS[kind] = tuple(field.name for field in dataclasses.fields(value))
    if names is not None:
        return {name: plain(getattr(value, name)) for name in names}
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in sorted(value.items())}
    if isinstance(value, float):
        return plain(float(value))
    return value


def canonical_bytes(record: Any) -> bytes:
    return json.dumps(
        plain(record), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
