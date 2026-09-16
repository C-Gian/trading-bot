"""Tamper-evident logical audit chain for prospective shadow evidence.

The JSON snapshot stays the convenient current-state view.  Alongside it, every scientific
transition appends one immutable event whose hash binds all of its own fields and the hash
of its predecessor, so deletion, reordering, duplication, or silent payload edits stop the
chain from recomputing.

This is corruption and tamper *evidence*, not authentication: there is deliberately no
secret key, and anyone able to rewrite the whole file could recompute a consistent chain.
What it guarantees is that a partial or careless edit cannot pass validation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

AUDIT_CHAIN_VERSION = "SHADOW_EVIDENCE_AUDIT_CHAIN_V1"
GENESIS_PREVIOUS_HASH = "GENESIS"

DECISION_PERSISTING = "PROSPECTIVE_DECISION_PERSISTING"
DECISION_OBSERVED = "PROSPECTIVE_DECISION_OBSERVED"
DECISION_MISSED = "PROSPECTIVE_DECISION_MISSED"
LONG_SUPPRESSED = "LONG_SIGNAL_SUPPRESSED"
INTENT_PERSISTING = "SHADOW_INTENT_PERSISTING"
INTENT_PERSISTED = "SHADOW_INTENT_PERSISTED"
ENTRY_ESTABLISHED = "SHADOW_ENTRY_ESTABLISHED"
TRADE_RECONCILED = "SHADOW_TRADE_RECONCILED"
TRADE_CLOSED = "SHADOW_TRADE_CLOSED"
TRADE_DATA_QUALITY_FAILED = "SHADOW_TRADE_DATA_QUALITY_FAILED"

EVENT_TYPES = frozenset(
    {
        DECISION_PERSISTING,
        DECISION_OBSERVED,
        DECISION_MISSED,
        LONG_SUPPRESSED,
        INTENT_PERSISTING,
        INTENT_PERSISTED,
        ENTRY_ESTABLISHED,
        TRADE_RECONCILED,
        TRADE_CLOSED,
        TRADE_DATA_QUALITY_FAILED,
    }
)

_EVENT_FIELDS = (
    "sequence",
    "event_type",
    "entity_kind",
    "entity_id",
    "event_time",
    "payload_digest",
    "previous_event_hash",
)


class AuditChainError(RuntimeError):
    """The evidence audit chain is broken, reordered, or inconsistent."""


def canonical_json(payload: Any) -> str:
    """One deterministic byte representation for any governed payload."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def payload_digest(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def event_hash(event: dict[str, Any]) -> str:
    """Bind every preceding field and the predecessor hash into this event's identity."""
    try:
        bound = "|".join(f"{field}={event[field]}" for field in _EVENT_FIELDS)
    except KeyError as exc:
        raise AuditChainError(f"audit event is missing {exc.args[0]}") from exc
    return hashlib.sha256(f"{AUDIT_CHAIN_VERSION}|{bound}".encode()).hexdigest()


def append_event(
    chain: list[dict[str, Any]],
    *,
    event_type: str,
    entity_kind: str,
    entity_id: str,
    event_time: str,
    payload: Any,
) -> dict[str, Any]:
    """Append one immutable event to the chain and return it."""
    if event_type not in EVENT_TYPES:
        raise AuditChainError(f"unknown audit event type: {event_type}")
    previous = chain[-1]["event_hash"] if chain else GENESIS_PREVIOUS_HASH
    event = {
        "sequence": len(chain) + 1,
        "event_type": event_type,
        "entity_kind": entity_kind,
        "entity_id": entity_id,
        "event_time": event_time,
        "payload_digest": payload_digest(payload),
        "previous_event_hash": previous,
    }
    event["event_hash"] = event_hash(event)
    chain.append(event)
    return event


def latest_event_for(chain: list[dict[str, Any]], entity_id: str) -> dict[str, Any] | None:
    for event in reversed(chain):
        if event.get("entity_id") == entity_id:
            return event
    return None


def has_event_type(chain: list[dict[str, Any]], entity_id: str, event_type: str) -> bool:
    return any(
        event.get("entity_id") == entity_id and event.get("event_type") == event_type
        for event in chain
    )


def validate_chain(chain: Any) -> None:
    """Reject a missing, duplicated, reordered, relinked, or edited chain."""
    if not isinstance(chain, list):
        raise AuditChainError("audit chain must be a list")
    previous = GENESIS_PREVIOUS_HASH
    for index, event in enumerate(chain, start=1):
        if not isinstance(event, dict):
            raise AuditChainError("audit event must be an object")
        for field in (*_EVENT_FIELDS, "event_hash"):
            if field not in event:
                raise AuditChainError(f"audit event {index} is missing {field}")
        if event["sequence"] != index:
            raise AuditChainError(
                f"audit chain sequence break at position {index}: {event['sequence']!r}"
            )
        if event["event_type"] not in EVENT_TYPES:
            raise AuditChainError(f"audit event {index} has an unknown type")
        if event["previous_event_hash"] != previous:
            raise AuditChainError(f"audit chain link is broken at event {index}")
        if event_hash(event) != event["event_hash"]:
            raise AuditChainError(f"audit event {index} does not match its own hash")
        previous = event["event_hash"]


__all__ = [
    "AUDIT_CHAIN_VERSION",
    "DECISION_MISSED",
    "DECISION_OBSERVED",
    "DECISION_PERSISTING",
    "ENTRY_ESTABLISHED",
    "EVENT_TYPES",
    "GENESIS_PREVIOUS_HASH",
    "INTENT_PERSISTED",
    "INTENT_PERSISTING",
    "LONG_SUPPRESSED",
    "TRADE_CLOSED",
    "TRADE_DATA_QUALITY_FAILED",
    "TRADE_RECONCILED",
    "AuditChainError",
    "append_event",
    "canonical_json",
    "event_hash",
    "has_event_type",
    "latest_event_for",
    "payload_digest",
    "validate_chain",
]
