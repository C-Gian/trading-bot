"""Append-only storage policy for issued System G1 records."""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from .canonical import canonical_bytes, digest


class ImmutableRecordError(RuntimeError):
    """An attempt to overwrite, re-issue or delete an issued record."""


def record_id(record: Any) -> str:
    first = dataclasses.fields(record)[0]
    value = getattr(record, first.name)
    if not first.name.endswith("_id") or not isinstance(value, str):
        raise TypeError(f"{type(record).__name__} has no leading identity field")
    return value


class EventStore:
    """An append-only, insertion-ordered record log.

    There is no update or delete operation. Appending an identity that already exists is accepted
    only if the content is byte-identical (idempotent replay); otherwise it is refused.
    """

    def __init__(self) -> None:
        self._records: list[Any] = []
        self._by_id: dict[str, bytes] = {}

    def append(self, record: Any) -> Any:
        params = getattr(type(record), "__dataclass_params__", None)
        if not dataclasses.is_dataclass(record) or params is None or not params.frozen:
            raise ImmutableRecordError("only frozen records may be issued")
        identity = record_id(record)
        content = canonical_bytes(record)
        existing = self._by_id.get(identity)
        if existing is not None:
            if existing != content:
                raise ImmutableRecordError(f"record {identity} was already issued differently")
            return record
        self._by_id[identity] = content
        self._records.append(record)
        return record

    def __iter__(self) -> Iterator[Any]:
        return iter(tuple(self._records))

    def __len__(self) -> int:
        return len(self._records)

    def of_type(self, kind: type) -> tuple[Any, ...]:
        return tuple(record for record in self._records if isinstance(record, kind))

    def visible(self, kind: type, cursor: datetime) -> tuple[Any, ...]:
        """Records of one type whose `available_at` is not after the cursor."""
        records: tuple[Any, ...] = self.of_type(kind)
        return tuple(record for record in records if record.available_at <= cursor)

    def fingerprint(self) -> str:
        return digest([canonical_bytes(record).decode("ascii") for record in self._records])
