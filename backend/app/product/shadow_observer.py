"""Automated prospective shadow-paper observation for the frozen ALIGNED candidate.

This module owns a new evidence class and durable store.  It never imports the manual
paper store, development data, sealed evaluation code, credentials, or an order API.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import threading
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from .. import __version__
from ..backtest import COST_VERSION
from ..backtest.models import Bar, CostModel, ExitReason
from . import audit_chain, provenance
from .analysis import (
    CHAMPION_STATUS,
    MAX_HOLD_MINUTES,
    PROSPECTIVE_FEATURES,
    RESEARCH_STATUS,
    STOP_FRACTION,
    STRATEGY_VERSION,
    TARGET_FRACTION,
    VARIANT,
    analyse,
)
from .execution_v2 import (
    AMBIGUOUS_FILL_POLICY,
    ENTRY_TIMING_RULE,
    PAPER_ENGINE_VERSION,
    PAPER_EXECUTION_VERSION,
    CausalPaperPlan,
    simulate_causal_paper,
)
from .market_feed import Kline, MarketFeedError, fetch_minutes
from .observer_lease import CONTENDED_ERROR, ObserverLease
from .platform_file_io import platform_file_operations

ROOT = Path(__file__).resolve().parents[3]

OBSERVER_VERSION = "PROSPECTIVE_SHADOW_PAPER_OBSERVER_V1_1"
EVIDENCE_VERSION = "FUTURE_SHADOW_PAPER_EVIDENCE_V1_1"
EVIDENCE_CONTRACT = "docs/contracts/FUTURE_SHADOW_PAPER_EVIDENCE_V1_1.md"
EVIDENCE_STAGE = "AUTOMATED_PROSPECTIVE_SHADOW_PAPER"
INITIATION_MODE = "AUTOMATED_RESEARCH_OBSERVER"
EVIDENCE_STORE_PATH = "data/paper/FUTURE_SHADOW_PAPER_EVIDENCE_V1_1.json"
HEALTH_STORE_PATH = "data/paper/PROSPECTIVE_SHADOW_OBSERVER_HEALTH_V1_1.json"
LEASE_PATH = "data/paper/PROSPECTIVE_SHADOW_OBSERVER_V1_1.lease"

# The superseded V1 implementation never recorded a genuine observation; its contract and
# artifacts remain in the repository purely as implementation history.
SUPERSEDED_EVIDENCE_VERSION = "FUTURE_SHADOW_PAPER_EVIDENCE_V1"
SUPERSEDED_EVIDENCE_STATUS = "IMPLEMENTED_SUPERSEDED_BEFORE_FIRST_REAL_OBSERVATION"

UNVERIFIED_BUILD = provenance.UNVERIFIED_REASON
INTEGRITY_ERROR = "EVIDENCE_INTEGRITY_VALIDATION_FAILED"
SYMBOL = "BTCUSDT"
MAX_DECISION_LATENCY = timedelta(minutes=5)
MAX_DECISION_LATENCY_SECONDS = 300
ENTRY_TIMEOUT_OPPORTUNITIES = 5
FIRST_REVIEW_COMPLETED_TRADES = 20
HEARTBEAT_SECONDS = 15
MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)

OBSERVED = "OBSERVED_PROSPECTIVE_DECISION"
PERSISTING_DECISION = "PERSISTING_PROSPECTIVE_DECISION"
MISSED_DECISION = "MISSED_PROSPECTIVE_DECISION"
SUPPRESSED = "LONG_SIGNAL_SUPPRESSED_ACTIVE_SHADOW_POSITION"

PERSISTING_INTENT = "PERSISTING_INTENT"
PENDING_ENTRY = "PENDING_ENTRY"
OPEN = "OPEN"
CLOSED_TARGET = "CLOSED_TARGET"
CLOSED_STOP = "CLOSED_STOP"
CLOSED_EXPIRY = "CLOSED_EXPIRY"
DATA_QUALITY_ERROR = "DATA_QUALITY_ERROR"

ACTIVE_TRADE_STATUSES = frozenset({PERSISTING_INTENT, PENDING_ENTRY, OPEN})
COMPLETED_TRADE_STATUSES = frozenset({CLOSED_TARGET, CLOSED_STOP, CLOSED_EXPIRY})
TERMINAL_TRADE_STATUSES = COMPLETED_TRADE_STATUSES | {DATA_QUALITY_ERROR}
DECISION_STATUSES = frozenset({OBSERVED, PERSISTING_DECISION, MISSED_DECISION, SUPPRESSED})
TRADE_STATUSES = ACTIVE_TRADE_STATUSES | TERMINAL_TRADE_STATUSES

_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[Path, threading.RLock] = {}


class ShadowObserverError(RuntimeError):
    """The prospective observer cannot safely advance."""


def _utc(instant: datetime) -> datetime:
    if instant.tzinfo is None:
        raise ShadowObserverError("observer timestamps must be timezone-aware")
    return instant.astimezone(UTC)


def _format(instant: datetime) -> str:
    return _utc(instant).isoformat().replace("+00:00", "Z")


def _parse(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ShadowObserverError("observer store contains an invalid timestamp")
    try:
        return _utc(datetime.fromisoformat(value))
    except ValueError as exc:
        raise ShadowObserverError("observer store contains an invalid timestamp") from exc


def _next_hour_strictly_after(instant: datetime) -> datetime:
    utc = _utc(instant)
    return utc.replace(minute=0, second=0, microsecond=0) + HOUR


def _last_completed_hour(now: datetime) -> datetime:
    return _utc(now).replace(minute=0, second=0, microsecond=0)


def _next_minute_strictly_after(instant: datetime) -> datetime:
    utc = _utc(instant)
    return utc.replace(second=0, microsecond=0) + MINUTE


def _forbid_production_write_under_test(path: Path) -> None:
    """A test run may never fabricate a record in the real prospective evidence store.

    The observer activates with the local backend, so an ordinary ``TestClient`` lifespan
    would otherwise write genuine-looking evidence.  Guarding the single durable write
    seam makes that structurally impossible rather than merely conventional.
    """
    if "PYTEST_CURRENT_TEST" not in os.environ:
        return
    if path.resolve().parent == (ROOT / "data" / "paper").resolve():
        raise ShadowObserverError(
            "a test run may never write the production prospective evidence store"
        )


def _path_lock(path: Path) -> threading.RLock:
    resolved = path.resolve()
    with _LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(resolved, threading.RLock())


@contextmanager
def _interprocess_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        operations = platform_file_operations()
        operations.lock(handle.fileno())
        try:
            yield
        finally:
            handle.seek(0)
            operations.unlock(handle.fileno())


class _DurableJsonStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(f"{self.path.suffix}.lock")
        self._mutex = _path_lock(self.path)
        self._local = threading.local()

    @contextmanager
    def locked(self):
        with self._mutex:
            depth = int(getattr(self._local, "depth", 0))
            self._local.depth = depth + 1
            try:
                if depth:
                    yield
                else:
                    with _interprocess_lock(self.lock_path):
                        yield
            finally:
                self._local.depth = depth

    def _read(self) -> dict[str, Any] | None:
        if not self.path.is_file():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ShadowObserverError("observer store is unreadable") from exc
        if not isinstance(payload, dict):
            raise ShadowObserverError("observer store root must be an object")
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        _forbid_production_write_under_test(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        staging: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="\n",
                dir=self.path.parent,
                delete=False,
                suffix=".staging",
            ) as handle:
                json.dump(payload, handle, sort_keys=True, indent=2, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
                staging = Path(handle.name)
            platform_file_operations().replace_durably(staging, self.path)
        finally:
            if staging is not None:
                staging.unlink(missing_ok=True)


# Scientifically material fields only.  Bookkeeping such as reconciliation counters and
# heartbeat stamps is deliberately excluded so that an audit event is appended when the
# governed meaning of a record changes, and not merely because a tick touched it.
_DECISION_GOVERNED_FIELDS = (
    "decision_id",
    "status",
    "evidence_version",
    "observer_version",
    "strategy_version",
    "feature_version",
    "symbol",
    "decision_boundary",
    "observer_evaluation_time",
    "durable_persistence_time",
    "data_completeness_status",
    "decision",
    "direction_pass",
    "breakout_pass",
    "participation_pass",
    "analysis_id",
    "miss_reason",
    "research_status",
    "champion_status",
    "build_provenance_sha256",
    "real_money",
)

_TRADE_GOVERNED_FIELDS = (
    "trade_id",
    "decision_id",
    "status",
    "evidence_version",
    "observer_version",
    "strategy_version",
    "symbol",
    "direction",
    "decision_boundary",
    "intent_persisted_at",
    "entry_not_before",
    "entry_time",
    "entry_price",
    "stop_price",
    "target_price",
    "expiry_time",
    "exit_time",
    "exit_price",
    "exit_reason",
    "gross_return",
    "net_return",
    "r_multiple",
    "holding_minutes",
    "stop_fraction",
    "target_fraction",
    "max_hold_minutes",
    "ambiguous_fill_policy",
    "execution_model_version",
    "cost_model_version",
    "data_quality_status",
    "reconciled_after_restart",
    "build_provenance_sha256",
    "real_money",
)

_DECISION_EVENT_TYPES = {
    PERSISTING_DECISION: audit_chain.DECISION_PERSISTING,
    OBSERVED: audit_chain.DECISION_OBSERVED,
    MISSED_DECISION: audit_chain.DECISION_MISSED,
    SUPPRESSED: audit_chain.LONG_SUPPRESSED,
}

_TRADE_EVENT_TYPES = {
    PERSISTING_INTENT: audit_chain.INTENT_PERSISTING,
    PENDING_ENTRY: audit_chain.INTENT_PERSISTED,
    CLOSED_TARGET: audit_chain.TRADE_CLOSED,
    CLOSED_STOP: audit_chain.TRADE_CLOSED,
    CLOSED_EXPIRY: audit_chain.TRADE_CLOSED,
    DATA_QUALITY_ERROR: audit_chain.TRADE_DATA_QUALITY_FAILED,
}


def _projection(record: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: record.get(field) for field in fields}


def decision_projection(decision: dict[str, Any]) -> dict[str, Any]:
    return _projection(decision, _DECISION_GOVERNED_FIELDS)


def trade_projection(trade: dict[str, Any]) -> dict[str, Any]:
    return _projection(trade, _TRADE_GOVERNED_FIELDS)


def _trade_event_type(chain: list[dict[str, Any]], trade: dict[str, Any]) -> str:
    status = trade["status"]
    if status == OPEN:
        # The first time a trade is open it was entered; later governed changes while it
        # remains open can only come from reconciling it against public bars.
        if audit_chain.has_event_type(chain, trade["trade_id"], audit_chain.ENTRY_ESTABLISHED):
            return audit_chain.TRADE_RECONCILED
        return audit_chain.ENTRY_ESTABLISHED
    return _TRADE_EVENT_TYPES[status]


def synchronise_audit_chain(document: dict[str, Any], event_time: str) -> int:
    """Append one immutable event for every governed state change in the snapshot."""
    chain = document["audit_chain"]
    appended = 0
    for kind, records, project, event_type in (
        (
            "decision",
            document["decisions"],
            decision_projection,
            lambda chain, record: _DECISION_EVENT_TYPES[record["status"]],
        ),
        ("trade", document["trades"], trade_projection, _trade_event_type),
    ):
        for record in records:
            entity_id = record["decision_id"] if kind == "decision" else record["trade_id"]
            payload = project(record)
            latest = audit_chain.latest_event_for(chain, entity_id)
            if latest is not None and latest["payload_digest"] == audit_chain.payload_digest(
                payload
            ):
                continue
            audit_chain.append_event(
                chain,
                event_type=event_type(chain, record),
                entity_kind=kind,
                entity_id=entity_id,
                event_time=event_time,
                payload=payload,
            )
            appended += 1
    return appended


def _validate_audit_integrity(document: dict[str, Any]) -> None:
    """Validate the chain itself and that the snapshot agrees with its latest events."""
    chain = document.get("audit_chain")
    try:
        audit_chain.validate_chain(chain)
    except audit_chain.AuditChainError as exc:
        raise ShadowObserverError(f"{INTEGRITY_ERROR}: {exc}") from exc
    assert isinstance(chain, list)

    governed: list[tuple[str, str, dict[str, Any]]] = [
        *(
            ("decision", decision["decision_id"], decision_projection(decision))
            for decision in document["decisions"]
        ),
        *(("trade", trade["trade_id"], trade_projection(trade)) for trade in document["trades"]),
    ]
    entity_ids = {entity_id for _, entity_id, _ in governed}
    for kind, entity_id, payload in governed:
        latest = audit_chain.latest_event_for(chain, entity_id)
        if latest is None:
            raise ShadowObserverError(
                f"{INTEGRITY_ERROR}: {kind} {entity_id} has no governed audit event"
            )
        if latest["payload_digest"] != audit_chain.payload_digest(payload):
            raise ShadowObserverError(
                f"{INTEGRITY_ERROR}: {kind} {entity_id} disagrees with its latest audit event"
            )
    for event in chain:
        if event["entity_id"] not in entity_ids:
            raise ShadowObserverError(
                f"{INTEGRITY_ERROR}: audit event {event['sequence']} describes a deleted record"
            )


class ShadowEvidenceStore(_DurableJsonStore):
    """Append-only decision and trade evidence, physically separate from manual V2.

    The snapshot and its audit chain live in one document so a single durable replace
    keeps them consistent; a crash can never leave the chain describing one state while
    the snapshot describes another.
    """

    def _empty(self) -> dict[str, Any]:
        return {
            "version": EVIDENCE_VERSION,
            "contract": EVIDENCE_CONTRACT,
            "evidence_stage": EVIDENCE_STAGE,
            "initiation_mode": INITIATION_MODE,
            "observer_version": OBSERVER_VERSION,
            "strategy_version": STRATEGY_VERSION,
            "feature_version": PROSPECTIVE_FEATURES,
            "research_status": RESEARCH_STATUS,
            "champion_status": CHAMPION_STATUS,
            "audit_chain_version": audit_chain.AUDIT_CHAIN_VERSION,
            "supersedes": SUPERSEDED_EVIDENCE_VERSION,
            "supersedes_status": SUPERSEDED_EVIDENCE_STATUS,
            "real_money": False,
            "build_provenance": [],
            "decisions": [],
            "trades": [],
            "audit_chain": [],
        }

    def load(self) -> dict[str, Any]:
        with self.locked():
            document = self._read() or self._empty()
            self.validate(document)
            return document

    def save(self, document: dict[str, Any]) -> None:
        with self.locked():
            self.validate(document)
            self._write(document)

    def commit(self, document: dict[str, Any], event_time: datetime) -> None:
        """Append an audit event for every governed change, then durably replace once."""
        with self.locked():
            synchronise_audit_chain(document, _format(event_time))
            self.validate(document)
            self._write(document)

    @staticmethod
    def validate(document: dict[str, Any]) -> None:
        expected = {
            "version": EVIDENCE_VERSION,
            "contract": EVIDENCE_CONTRACT,
            "evidence_stage": EVIDENCE_STAGE,
            "initiation_mode": INITIATION_MODE,
            "observer_version": OBSERVER_VERSION,
            "strategy_version": STRATEGY_VERSION,
            "feature_version": PROSPECTIVE_FEATURES,
            "research_status": RESEARCH_STATUS,
            "champion_status": CHAMPION_STATUS,
            "audit_chain_version": audit_chain.AUDIT_CHAIN_VERSION,
            "supersedes": SUPERSEDED_EVIDENCE_VERSION,
            "supersedes_status": SUPERSEDED_EVIDENCE_STATUS,
            "real_money": False,
        }
        if any(document.get(key) != value for key, value in expected.items()):
            raise ShadowObserverError("shadow evidence safety metadata mismatch")
        decisions = document.get("decisions")
        trades = document.get("trades")
        if not isinstance(decisions, list) or not isinstance(trades, list):
            raise ShadowObserverError("shadow evidence collections are invalid")
        boundaries: list[str] = []
        decision_ids: list[str] = []
        for decision in decisions:
            if not isinstance(decision, dict):
                raise ShadowObserverError("shadow decision is invalid")
            status = decision.get("status")
            boundary = decision.get("decision_boundary")
            if (
                status not in DECISION_STATUSES
                or decision.get("observer_version") != OBSERVER_VERSION
                or decision.get("strategy_version") != STRATEGY_VERSION
                or decision.get("symbol") != SYMBOL
                or decision.get("champion_status") != CHAMPION_STATUS
                or decision.get("real_money") is not False
                or not isinstance(boundary, str)
                or _parse(boundary).minute
                or _parse(boundary).second
                or _parse(boundary).microsecond
            ):
                raise ShadowObserverError("shadow decision violates its contract")
            boundaries.append(boundary)
            decision_ids.append(str(decision.get("decision_id")))
            if status == MISSED_DECISION:
                if decision.get("decision") is not None or decision.get("analysis_id") is not None:
                    raise ShadowObserverError(
                        "missed decisions cannot contain a reconstructed signal"
                    )
            elif status != PERSISTING_DECISION and (
                decision.get("decision") not in {"LONG", "NO_TRADE"}
                or decision.get("data_completeness_status") != "OK"
                or not isinstance(decision.get("durable_persistence_time"), str)
                or any(
                    type(decision.get(name)) is not bool
                    for name in ("direction_pass", "breakout_pass", "participation_pass")
                )
            ):
                raise ShadowObserverError("observed decision is incomplete")
        if len(boundaries) != len(set(boundaries)) or len(decision_ids) != len(set(decision_ids)):
            raise ShadowObserverError("shadow decisions contain duplicate identities")

        trade_ids: list[str] = []
        active = 0
        for trade in trades:
            if not isinstance(trade, dict):
                raise ShadowObserverError("shadow trade is invalid")
            status = trade.get("status")
            if (
                status not in TRADE_STATUSES
                or trade.get("evidence_version") != EVIDENCE_VERSION
                or trade.get("evidence_stage") != EVIDENCE_STAGE
                or trade.get("initiation_mode") != INITIATION_MODE
                or trade.get("strategy_version") != STRATEGY_VERSION
                or trade.get("symbol") != SYMBOL
                or trade.get("direction") != "LONG"
                or trade.get("cost_model_version") != COST_VERSION
                or trade.get("ambiguous_fill_policy") != AMBIGUOUS_FILL_POLICY
                or trade.get("stop_fraction") != 0.02
                or trade.get("target_fraction") != 0.04
                or trade.get("max_hold_minutes") != MAX_HOLD_MINUTES
                or trade.get("champion_status") != CHAMPION_STATUS
                or trade.get("real_money") is not False
                or trade.get("order_placed") is not False
                or trade.get("leverage") is not False
                or trade.get("short") is not False
            ):
                raise ShadowObserverError("shadow trade violates its safety contract")
            trade_ids.append(str(trade.get("trade_id")))
            active += int(status in ACTIVE_TRADE_STATUSES)
            if status in {PENDING_ENTRY, OPEN} | COMPLETED_TRADE_STATUSES:
                persisted = _parse(trade.get("intent_persisted_at"))
                lower_bound = _parse(trade.get("entry_not_before"))
                if lower_bound != _next_minute_strictly_after(persisted):
                    raise ShadowObserverError("shadow entry lower bound is not causal")
            if status in {OPEN} | COMPLETED_TRADE_STATUSES:
                entry = _parse(trade.get("entry_time"))
                if (
                    entry <= _parse(trade.get("intent_persisted_at"))
                    or entry.second
                    or entry.microsecond
                ):
                    raise ShadowObserverError("shadow entry is not strictly after its intent")
            elif status != DATA_QUALITY_ERROR and trade.get("entry_time") is not None:
                raise ShadowObserverError("unfilled shadow intent contains an entry")
            if status in COMPLETED_TRADE_STATUSES and any(
                trade.get(field) is None
                for field in (
                    "exit_time",
                    "exit_price",
                    "gross_return",
                    "net_return",
                    "r_multiple",
                    "holding_minutes",
                )
            ):
                raise ShadowObserverError("completed shadow trade is missing its result")
        if len(trade_ids) != len(set(trade_ids)) or active > 1:
            raise ShadowObserverError("shadow ledger violates the one-position rule")
        if not isinstance(document.get("build_provenance"), list):
            raise ShadowObserverError("shadow evidence is missing its build provenance history")
        _validate_audit_integrity(document)


class ShadowHealthStore(_DurableJsonStore):
    """Operational health; never treated as prospective market evidence."""

    def load(self) -> dict[str, Any] | None:
        with self.locked():
            document = self._read()
            if document is not None:
                self.validate(document)
            return document

    def save(self, document: dict[str, Any]) -> None:
        with self.locked():
            self.validate(document)
            self._write(document)

    @staticmethod
    def validate(document: dict[str, Any]) -> None:
        if (
            document.get("version") != OBSERVER_VERSION
            or document.get("evidence_version") != EVIDENCE_VERSION
            or document.get("status") not in {"ACTIVE", "STOPPED", "DEGRADED"}
            or document.get("real_money") is not False
            or not isinstance(document.get("activation_history"), list)
            or not isinstance(document.get("missed_boundaries"), int)
        ):
            raise ShadowObserverError("observer health store is invalid")
        for field in ("backend_start", "last_heartbeat"):
            _parse(document.get(field))
        # An observer that never activated — because a peer held the lease, or because its
        # evidence failed integrity validation — records no activation instant and no next
        # boundary, so those stay null rather than implying uptime that never happened.
        activated = document.get("observer_activation") is not None
        for field in ("observer_activation", "next_expected_boundary"):
            if activated:
                _parse(document.get(field))
            elif document.get(field) is not None:
                raise ShadowObserverError("inactive observer health cannot claim a boundary")


def default_build_identity() -> str:
    configured = os.environ.get("TRADING_BOT_BUILD_ID")
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return f"trading-bot-{__version__}"


def _default_provenance() -> dict[str, Any]:
    """The live repository build identity for this observer and evidence version."""
    return provenance.repository_provenance(
        observer_version=OBSERVER_VERSION,
        evidence_version=EVIDENCE_VERSION,
        contract_path=EVIDENCE_CONTRACT,
    )


def _decision_id(boundary: datetime) -> str:
    payload = f"{EVIDENCE_VERSION}|{STRATEGY_VERSION}|{SYMBOL}|{_format(boundary)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _kline_record(kline: Kline) -> dict[str, Any]:
    return {
        "open_time": _format(datetime.fromtimestamp(kline.open_ms / 1000, UTC)),
        "open": kline.open,
        "high": kline.high,
        "low": kline.low,
        "close": kline.close,
    }


def _bar(record: dict[str, Any]) -> Bar:
    return Bar(
        _parse(record["open_time"]),
        Decimal(str(record["open"])),
        Decimal(str(record["high"])),
        Decimal(str(record["low"])),
        Decimal(str(record["close"])),
    )


def _default_minute_feed(start_ms: int, count: int, *, now: datetime) -> tuple[Kline, ...]:
    return fetch_minutes(start_ms, count, now=now)


class ProspectiveShadowObserver:
    """Single durable observer with a deterministic ``tick`` seam for synthetic tests."""

    def __init__(
        self,
        evidence_store: ShadowEvidenceStore,
        health_store: ShadowHealthStore,
        *,
        analyser: Callable[..., dict[str, Any]] = analyse,
        minute_feed: Callable[..., tuple[Kline, ...]] = _default_minute_feed,
        clock: Callable[[], datetime] | None = None,
        build_identity: str | None = None,
        heartbeat_seconds: int = HEARTBEAT_SECONDS,
        provenance_provider: Callable[[], dict[str, Any]] | None = None,
        lease: ObserverLease | None = None,
    ):
        self.evidence_store = evidence_store
        self.health_store = health_store
        self.analyser = analyser
        self.minute_feed = minute_feed
        self.clock = clock or (lambda: datetime.now(UTC))
        self.build_identity = build_identity or default_build_identity()
        self.heartbeat_seconds = heartbeat_seconds
        self.provenance_provider = provenance_provider or _default_provenance
        self.lease = lease
        self._service_lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._active = False

    def build_provenance(self) -> dict[str, Any]:
        """The current scientific build identity, never cached across a tick."""
        return self.provenance_provider()

    def _verified_provenance(self) -> dict[str, Any]:
        """Return a usable build identity or fail closed with the governed reason."""
        current = self.build_provenance()
        try:
            provenance.validate(current)
        except provenance.ProvenanceError as exc:
            raise ShadowObserverError(f"{UNVERIFIED_BUILD}: {exc}") from exc
        return current

    def _require_lease(self) -> None:
        """Only the process owning the scientific lease may observe or record."""
        if self.lease is None:
            return
        if not self.lease.acquire():
            raise ShadowObserverError(CONTENDED_ERROR)

    def _record_provenance(self, document: dict[str, Any], current: dict[str, Any]) -> str:
        """Persist the manifest and aggregate SHA once per distinct build identity."""
        identity = provenance.provenance_identity(current)
        history = document["build_provenance"]
        if not any(item.get("semantic_manifest_sha256") == identity for item in history):
            history.append(current)
        return identity

    def _new_health(self, now: datetime) -> dict[str, Any]:
        stamp = _format(now)
        return {
            "version": OBSERVER_VERSION,
            "evidence_version": EVIDENCE_VERSION,
            "status": "ACTIVE",
            "backend_start": stamp,
            "observer_activation": stamp,
            "initial_activation": stamp,
            "activation_history": [stamp],
            "last_heartbeat": stamp,
            "last_successful_market_fetch": None,
            "last_evaluated_boundary": None,
            "last_missed_boundary": None,
            "next_expected_boundary": _format(_next_hour_strictly_after(now)),
            "missed_boundaries": 0,
            "current_error": None,
            "build_provenance_verified": None,
            "build_provenance_sha256": None,
            "observer_lease_held": None,
            "real_money": False,
        }

    def _mark_missed(self, boundary: datetime, reason: str, recorded_at: datetime) -> bool:
        with self.evidence_store.locked():
            document = self.evidence_store.load()
            boundary_text = _format(boundary)
            if any(item["decision_boundary"] == boundary_text for item in document["decisions"]):
                return False
            document["decisions"].append(
                {
                    "decision_id": _decision_id(boundary),
                    "status": MISSED_DECISION,
                    "observer_version": OBSERVER_VERSION,
                    "evidence_version": EVIDENCE_VERSION,
                    "evidence_stage": EVIDENCE_STAGE,
                    "initiation_mode": INITIATION_MODE,
                    "strategy_version": STRATEGY_VERSION,
                    "feature_version": PROSPECTIVE_FEATURES,
                    "code_build_identity": self.build_identity,
                    "symbol": SYMBOL,
                    "decision_boundary": boundary_text,
                    "observer_evaluation_time": None,
                    "durable_persistence_time": _format(recorded_at),
                    "data_completeness_status": "NOT_OBSERVED",
                    "decision": None,
                    "direction_pass": None,
                    "breakout_pass": None,
                    "participation_pass": None,
                    "analysis_id": None,
                    "research_status": RESEARCH_STATUS,
                    "champion_status": CHAMPION_STATUS,
                    "miss_reason": reason,
                    "build_provenance_sha256": None,
                    "real_money": False,
                }
            )
            self.evidence_store.commit(document, recorded_at)
            return True

    def _close_unentered_after_restart(self, now: datetime) -> int:
        with self.evidence_store.locked():
            document = self.evidence_store.load()
            changed = 0
            for trade in document["trades"]:
                if trade["status"] in {PERSISTING_INTENT, PENDING_ENTRY}:
                    trade.update(
                        status=DATA_QUALITY_ERROR,
                        data_quality_status="DOWNTIME_BEFORE_ENTRY",
                        resolution_detail=(
                            "restart cannot reconstruct an entry that was not observed prospectively"
                        ),
                        last_update_time=_format(now),
                    )
                    changed += 1
            if changed:
                self.evidence_store.commit(document, now)
            return changed

    def activate(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Durably activate and account for downtime without evaluating past signals.

        Scientific activation requires exclusive ownership of the observer lease and
        evidence whose audit chain still validates.  Either failure leaves the observer
        degraded and inactive rather than quietly starting a second writer or continuing
        on top of evidence that can no longer be trusted.
        """
        moment = _utc(now or self.clock())
        with self._service_lock:
            try:
                self._require_lease()
                self.evidence_store.load()
            except ShadowObserverError as exc:
                self._degrade_without_activating(moment, str(exc))
                return self.overview()
            prior = self.health_store.load()
            # A health record left behind by a failed activation attempt records no
            # activation instant, so it must not be treated as a restart with downtime.
            previously_activated = (
                prior is not None and prior.get("observer_activation") is not None
            )
            if not previously_activated:
                health = self._new_health(moment)
            else:
                assert prior is not None
                health = dict(prior)
                next_boundary = _parse(health["next_expected_boundary"])
                while next_boundary <= _last_completed_hour(moment):
                    if self._mark_missed(next_boundary, "BACKEND_DOWNTIME", moment):
                        health["missed_boundaries"] += 1
                    health["last_missed_boundary"] = _format(next_boundary)
                    next_boundary += HOUR
                health.update(
                    status="ACTIVE",
                    backend_start=_format(moment),
                    observer_activation=_format(moment),
                    last_heartbeat=_format(moment),
                    next_expected_boundary=_format(next_boundary),
                    current_error=None,
                )
                health["activation_history"] = [*health["activation_history"], _format(moment)]
                self._close_unentered_after_restart(moment)
            current = self.build_provenance()
            health["build_provenance_verified"] = bool(current.get("verified"))
            health["build_provenance_sha256"] = current.get("semantic_manifest_sha256")
            health["observer_lease_held"] = self.lease is None or self.lease.held
            if not health["build_provenance_verified"]:
                health.update(status="DEGRADED", current_error=UNVERIFIED_BUILD)
            self.health_store.save(health)
            self._active = True
            self._reconcile_open_trades(moment, after_restart=previously_activated)
            return self.overview()

    def _degrade_without_activating(self, now: datetime, detail: str) -> None:
        """Fail closed: never activate, and never rewrite evidence to make it validate."""
        self._active = False
        prior = self.health_store.load()
        if prior is None:
            # Nothing has ever activated here, so record the attempt without inventing an
            # activation instant or any uptime that did not happen.
            health = self._new_health(now)
            health.update(
                observer_activation=None,
                initial_activation=None,
                activation_history=[],
                next_expected_boundary=None,
            )
        else:
            health = dict(prior)
        health.update(
            status="DEGRADED",
            backend_start=_format(now),
            last_heartbeat=_format(now),
            current_error=detail,
            observer_lease_held=self.lease is None or self.lease.held,
        )
        self.health_store.save(health)

    def start(self) -> None:
        with self._service_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            if not self._active:
                self.activate()
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="prospective-shadow-observer-v1",
                daemon=True,
            )
            self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.heartbeat_seconds):
            try:
                self.tick()
            except Exception as exc:  # fail closed while keeping the local backend alive
                self._record_health_error(str(exc))

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(2, self.heartbeat_seconds + 1))
        with self._service_lock:
            health = self.health_store.load()
            if health is not None:
                now = _utc(self.clock())
                health.update(
                    status="STOPPED", last_heartbeat=_format(now), observer_lease_held=False
                )
                self.health_store.save(health)
            self._active = False
            if self.lease is not None:
                self.lease.release()

    def _record_health_error(self, detail: str) -> None:
        with self._service_lock:
            health = self.health_store.load()
            if health is None:
                return
            health.update(
                status="DEGRADED",
                last_heartbeat=_format(_utc(self.clock())),
                current_error=detail,
            )
            self.health_store.save(health)

    def _pending_decision(
        self,
        analysis: dict[str, Any],
        boundary: datetime,
        now: datetime,
        provenance_sha: str,
    ) -> dict[str, Any]:
        features = analysis.get("features")
        if not isinstance(features, dict):
            raise ShadowObserverError("sound observer analysis omitted frozen ALIGNED gates")
        return {
            "decision_id": _decision_id(boundary),
            "status": PERSISTING_DECISION,
            "observer_version": OBSERVER_VERSION,
            "evidence_version": EVIDENCE_VERSION,
            "evidence_stage": EVIDENCE_STAGE,
            "initiation_mode": INITIATION_MODE,
            "strategy_version": STRATEGY_VERSION,
            "feature_version": PROSPECTIVE_FEATURES,
            "code_build_identity": self.build_identity,
            "symbol": SYMBOL,
            "decision_boundary": _format(boundary),
            "observer_evaluation_time": _format(now),
            "durable_persistence_time": None,
            "data_completeness_status": analysis.get("data_status"),
            "decision": analysis.get("decision"),
            "direction_pass": bool(features.get("persistent_up")),
            "breakout_pass": bool(features.get("breakout")),
            "participation_pass": bool(features.get("participation")),
            "analysis_id": analysis.get("analysis_id"),
            "research_status": RESEARCH_STATUS,
            "champion_status": CHAMPION_STATUS,
            "miss_reason": None,
            "build_provenance_sha256": provenance_sha,
            "real_money": False,
        }

    def _unarmed_trade(
        self, decision: dict[str, Any], analysis: dict[str, Any], now: datetime
    ) -> dict[str, Any]:
        trade_id = f"SHADOW-V1-{decision['decision_id'][:16]}"
        return {
            "trade_id": trade_id,
            "decision_id": decision["decision_id"],
            "analysis_id": decision["analysis_id"],
            "status": PERSISTING_INTENT,
            "observer_version": OBSERVER_VERSION,
            "evidence_version": EVIDENCE_VERSION,
            "evidence_stage": EVIDENCE_STAGE,
            "initiation_mode": INITIATION_MODE,
            "strategy_version": STRATEGY_VERSION,
            "feature_version": PROSPECTIVE_FEATURES,
            "code_build_identity": self.build_identity,
            "research_status": RESEARCH_STATUS,
            "champion_status": CHAMPION_STATUS,
            "build_provenance_sha256": decision["build_provenance_sha256"],
            "symbol": SYMBOL,
            "direction": "LONG",
            "decision_boundary": decision["decision_boundary"],
            "observer_evaluation_time": decision["observer_evaluation_time"],
            "intent_persisted_at": None,
            "entry_not_before": None,
            "entry_search_cursor": None,
            "entry_opportunities_checked": 0,
            "entry_timeout_opportunities": ENTRY_TIMEOUT_OPPORTUNITIES,
            "entry_timing_rule": ENTRY_TIMING_RULE,
            "ambiguous_fill_policy": AMBIGUOUS_FILL_POLICY,
            "execution_model_version": PAPER_EXECUTION_VERSION,
            "engine_version": PAPER_ENGINE_VERSION,
            "cost_model_version": COST_VERSION,
            "cost_components_bps": {
                "entry_fee": 10.0,
                "exit_fee": 10.0,
                "entry_friction": 2.0,
                "exit_friction": 2.0,
            },
            "stop_fraction": 0.02,
            "target_fraction": 0.04,
            "max_hold_minutes": MAX_HOLD_MINUTES,
            "entry_time": None,
            "entry_price": None,
            "entry_observation": None,
            "stop_price": None,
            "target_price": None,
            "expiry_time": None,
            "exit_time": None,
            "exit_price": None,
            "exit_reason": None,
            "gross_return": None,
            "net_return": None,
            "r_multiple": None,
            "holding_minutes": None,
            "entry_effective_price": None,
            "exit_effective_price": None,
            "entry_fee": None,
            "exit_fee": None,
            "entry_execution_friction": None,
            "exit_execution_friction": None,
            "data_quality_status": "PENDING_DURABLE_INTENT",
            "resolution_detail": "unarmed automated shadow intent is durably persisting",
            "reconciliation_count": 0,
            "reconciled_after_restart": False,
            "last_reconciled_at": None,
            "last_update_time": _format(now),
            "order_placed": False,
            "leverage": False,
            "short": False,
            "real_money": False,
            "analysis_reference_price": analysis.get("reference_price"),
        }

    def _persist_analysis(
        self,
        analysis: dict[str, Any],
        boundary: datetime,
        evaluated_at: datetime,
        current: dict[str, Any],
    ) -> dict[str, Any]:
        with self.evidence_store.locked():
            document = self.evidence_store.load()
            provenance_sha = self._record_provenance(document, current)
            boundary_text = _format(boundary)
            existing = next(
                (
                    item
                    for item in document["decisions"]
                    if item["decision_boundary"] == boundary_text
                ),
                None,
            )
            if existing is not None:
                return existing
            decision = self._pending_decision(analysis, boundary, evaluated_at, provenance_sha)
            active = any(trade["status"] in ACTIVE_TRADE_STATUSES for trade in document["trades"])
            trade: dict[str, Any] | None = None
            if decision["decision"] == "LONG" and not active:
                trade = self._unarmed_trade(decision, analysis, evaluated_at)
                document["trades"].append(trade)
            document["decisions"].append(decision)
            self.evidence_store.commit(document, evaluated_at)

            persisted_at = _utc(self.clock())
            if persisted_at > boundary + MAX_DECISION_LATENCY:
                decision.update(
                    status=MISSED_DECISION,
                    durable_persistence_time=_format(persisted_at),
                    data_completeness_status="LATE_DURABLE_PERSISTENCE",
                    decision=None,
                    direction_pass=None,
                    breakout_pass=None,
                    participation_pass=None,
                    analysis_id=None,
                    miss_reason="DECISION_DURABLE_PERSISTENCE_EXCEEDED_5_MINUTES",
                )
                if trade is not None:
                    trade.update(
                        status=DATA_QUALITY_ERROR,
                        data_quality_status="LATE_DECISION_PERSISTENCE",
                        resolution_detail="intent was never armed because the decision missed its window",
                        last_update_time=_format(persisted_at),
                    )
            else:
                decision.update(
                    status=SUPPRESSED if decision["decision"] == "LONG" and active else OBSERVED,
                    durable_persistence_time=_format(persisted_at),
                )
                if trade is not None:
                    lower_bound = _next_minute_strictly_after(persisted_at)
                    trade.update(
                        status=PENDING_ENTRY,
                        intent_persisted_at=_format(persisted_at),
                        entry_not_before=_format(lower_bound),
                        entry_search_cursor=_format(lower_bound),
                        data_quality_status="OK",
                        resolution_detail=(
                            "durable automated shadow intent; awaiting a strictly future minute"
                        ),
                        last_update_time=_format(persisted_at),
                    )
            self.evidence_store.commit(document, persisted_at)
            return decision

    @staticmethod
    def _analysis_is_for_boundary(analysis: dict[str, Any], boundary: datetime) -> bool:
        if analysis.get("data_status") != "OK":
            return False
        if analysis.get("decision") not in {"LONG", "NO_TRADE"}:
            return False
        if analysis.get("strategy_version") != STRATEGY_VERSION:
            return False
        if analysis.get("champion_status") != CHAMPION_STATUS:
            return False
        if analysis.get("real_money") is not False:
            return False
        try:
            return _parse(analysis.get("signal_time")) == boundary
        except ShadowObserverError:
            return False

    def tick(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Advance health, open trades, and at most one due prospective boundary."""
        moment = _utc(now or self.clock())
        with self._service_lock:
            health = self.health_store.load()
            if health is None or not self._active:
                raise ShadowObserverError("observer is not activated")
            health["last_heartbeat"] = _format(moment)
            fetched, trade_errors = self._reconcile_open_trades(moment, after_restart=False)
            if fetched:
                health["last_successful_market_fetch"] = _format(moment)
            if trade_errors:
                health.update(status="DEGRADED", current_error="; ".join(trade_errors))

            # Verify the build and the lease once, before looking at the market at all, so
            # an unusable build can never evaluate a signal that is relabelled afterwards.
            gate_error: str | None = None
            try:
                self._require_lease()
                current = self._verified_provenance()
            except ShadowObserverError as exc:
                gate_error = str(exc)
                health.update(
                    status="DEGRADED",
                    current_error=gate_error,
                    build_provenance_verified=False,
                    observer_lease_held=self.lease is None or self.lease.held,
                )
            else:
                health.update(
                    build_provenance_verified=True,
                    build_provenance_sha256=provenance.provenance_identity(current),
                    observer_lease_held=True,
                )

            next_boundary = _parse(health["next_expected_boundary"])
            while next_boundary <= _last_completed_hour(moment):
                expired = moment > next_boundary + MAX_DECISION_LATENCY
                if gate_error is not None:
                    # The condition may still be repaired inside the five-minute window;
                    # once it closes the boundary is permanently missed, typed by cause.
                    if not expired:
                        break
                    reason = CONTENDED_ERROR if CONTENDED_ERROR in gate_error else UNVERIFIED_BUILD
                    if self._mark_missed(next_boundary, reason, moment):
                        health["missed_boundaries"] += 1
                    health["last_missed_boundary"] = _format(next_boundary)
                    next_boundary += HOUR
                    health["next_expected_boundary"] = _format(next_boundary)
                    continue
                if expired:
                    if self._mark_missed(next_boundary, "DECISION_LATENCY_EXCEEDED", moment):
                        health["missed_boundaries"] += 1
                    health["last_missed_boundary"] = _format(next_boundary)
                    next_boundary += HOUR
                    health["next_expected_boundary"] = _format(next_boundary)
                    continue

                try:
                    analysis = self.analyser(now=moment)
                except Exception as exc:
                    health.update(status="DEGRADED", current_error=f"analysis failed: {exc}")
                    break
                if not self._analysis_is_for_boundary(analysis, next_boundary):
                    health.update(
                        status="DEGRADED",
                        current_error=(
                            "current public bars do not yet support the expected completed boundary"
                        ),
                    )
                    break
                decision = self._persist_analysis(analysis, next_boundary, moment, current)
                if decision["status"] == MISSED_DECISION:
                    health["missed_boundaries"] += 1
                    health["last_missed_boundary"] = _format(next_boundary)
                else:
                    health["last_evaluated_boundary"] = _format(next_boundary)
                    health["last_successful_market_fetch"] = _format(moment)
                next_boundary += HOUR
                health["next_expected_boundary"] = _format(next_boundary)
                health.update(status="ACTIVE", current_error=None)
                self._reconcile_open_trades(moment, after_restart=False)
                break
            self.health_store.save(health)
            return self.overview()

    def _attempt_entry(self, trade: dict[str, Any], now: datetime) -> tuple[dict[str, Any], bool]:
        cursor = _parse(trade["entry_search_cursor"])
        last_completed = now.replace(second=0, microsecond=0) - MINUTE
        if last_completed < cursor:
            return trade, False
        checked = int(trade["entry_opportunities_checked"])
        count = min(
            ENTRY_TIMEOUT_OPPORTUNITIES - checked,
            int((last_completed - cursor) / MINUTE) + 1,
        )
        klines = self.minute_feed(int(cursor.timestamp() * 1000), count, now=now)
        by_open = {item.open_ms: item for item in klines}
        for offset in range(count):
            candidate = cursor + offset * MINUTE
            kline = by_open.get(int(candidate.timestamp() * 1000))
            if kline is None:
                continue
            fill_time = datetime.fromtimestamp(kline.open_ms / 1000, UTC)
            if fill_time <= _parse(trade["intent_persisted_at"]):
                raise ShadowObserverError("market feed attempted a non-causal shadow fill")
            price = Decimal(str(kline.open))
            updated = dict(trade)
            updated.update(
                status=OPEN,
                entry_opportunities_checked=checked + offset + 1,
                entry_search_cursor=None,
                entry_time=_format(fill_time),
                entry_price=float(price),
                entry_observation=_kline_record(kline),
                stop_price=float(price * STOP_FRACTION),
                target_price=float(price * TARGET_FRACTION),
                expiry_time=_format(fill_time + timedelta(minutes=MAX_HOLD_MINUTES)),
                data_quality_status="OK",
                resolution_detail="filled from the first available legal completed minute",
                last_update_time=_format(now),
            )
            return updated, True
        total = checked + count
        updated = dict(trade)
        updated["entry_opportunities_checked"] = total
        if total >= ENTRY_TIMEOUT_OPPORTUNITIES:
            updated.update(
                status=DATA_QUALITY_ERROR,
                entry_search_cursor=None,
                data_quality_status="ENTRY_BARS_UNAVAILABLE",
                resolution_detail="five completed legal entry opportunities were unavailable",
                last_update_time=_format(now),
            )
        else:
            updated.update(
                entry_search_cursor=_format(cursor + count * MINUTE),
                resolution_detail="completed entry opportunity unavailable; causal cursor advanced",
                last_update_time=_format(now),
            )
        return updated, True

    @staticmethod
    def _paper_path(trade: dict[str, Any], klines: tuple[Kline, ...]) -> tuple[Bar, ...]:
        observed = _bar(trade["entry_observation"])
        rows = {observed.open_time: observed}
        for kline in klines:
            bar = _bar(_kline_record(kline))
            if bar.open_time > observed.open_time:
                rows[bar.open_time] = bar
        return tuple(rows[key] for key in sorted(rows))

    def _advance_open(
        self, trade: dict[str, Any], now: datetime, *, after_restart: bool
    ) -> tuple[dict[str, Any], bool]:
        entry = _parse(trade["entry_time"])
        klines = self.minute_feed(
            int(entry.timestamp() * 1000), trade["max_hold_minutes"] + 1, now=now
        )
        plan = CausalPaperPlan(
            run_id=trade["trade_id"],
            strategy_reference=f"{STRATEGY_VERSION}:{VARIANT}",
            dataset_manifest_id="PUBLIC_BTCUSDT_SPOT_LIVE_READ_ONLY",
            dataset_content_hash="PROSPECTIVE_PUBLIC_OBSERVATIONS",
            entry_timestamp=entry,
            stop=Decimal(str(trade["stop_price"])),
            target=Decimal(str(trade["target_price"])),
            max_hold_minutes=trade["max_hold_minutes"],
        )
        record = simulate_causal_paper(plan, self._paper_path(trade, klines), CostModel())
        updated = dict(trade)
        updated.update(
            reconciliation_count=int(trade["reconciliation_count"]) + 1,
            reconciled_after_restart=bool(trade["reconciled_after_restart"] or after_restart),
            last_reconciled_at=_format(now),
            last_update_time=_format(now),
        )
        if record.exit_reason == ExitReason.UNRESOLVED_DATA_GAP:
            updated.update(
                status=DATA_QUALITY_ERROR,
                data_quality_status="UNRESOLVED_DATA_GAP",
                resolution_detail="required public bars contain a gap; trade failed closed",
            )
        elif record.data_quality_status == "INVALID":
            updated.update(
                status=DATA_QUALITY_ERROR,
                data_quality_status=record.exit_reason.value,
                resolution_detail="frozen execution engine rejected the shadow path",
            )
        elif record.data_quality_status == "UNRESOLVED":
            updated.update(
                status=OPEN,
                data_quality_status="OK",
                resolution_detail=f"position unresolved ({record.exit_reason.value})",
            )
        else:
            assert (
                record.entry_raw_price is not None
                and record.entry_effective_price is not None
                and record.exit_timestamp is not None
                and record.exit_raw_price is not None
                and record.exit_effective_price is not None
                and record.entry_fee is not None
                and record.exit_fee is not None
                and record.entry_execution_friction is not None
                and record.exit_execution_friction is not None
                and record.gross_pnl is not None
                and record.net_pnl is not None
                and record.net_r is not None
            )
            status = {
                ExitReason.TARGET: CLOSED_TARGET,
                ExitReason.STOP: CLOSED_STOP,
                ExitReason.STOP_GAP: CLOSED_STOP,
                ExitReason.EXPIRY: CLOSED_EXPIRY,
            }[record.exit_reason]
            updated.update(
                status=status,
                exit_time=_format(record.exit_timestamp),
                exit_price=float(record.exit_raw_price),
                exit_reason=record.exit_reason.value,
                gross_return=float(record.gross_pnl / record.entry_raw_price),
                net_return=float(record.net_pnl / record.entry_raw_price),
                r_multiple=float(record.net_r),
                holding_minutes=record.holding_minutes,
                entry_effective_price=float(record.entry_effective_price),
                exit_effective_price=float(record.exit_effective_price),
                entry_fee=float(record.entry_fee),
                exit_fee=float(record.exit_fee),
                entry_execution_friction=float(record.entry_execution_friction),
                exit_execution_friction=float(record.exit_execution_friction),
                data_quality_status="VALID",
                resolution_detail=f"resolved by {PAPER_EXECUTION_VERSION}",
            )
        return updated, True

    def _reconcile_open_trades(
        self, now: datetime, *, after_restart: bool
    ) -> tuple[bool, list[str]]:
        fetched = False
        errors: list[str] = []
        with self.evidence_store.locked():
            document = self.evidence_store.load()
            changed = False
            for index, trade in enumerate(document["trades"]):
                if trade["status"] in TERMINAL_TRADE_STATUSES:
                    continue
                if after_restart and trade["status"] in {PERSISTING_INTENT, PENDING_ENTRY}:
                    continue
                try:
                    if trade["status"] == PENDING_ENTRY:
                        resolved, did_fetch = self._attempt_entry(trade, now)
                        fetched = fetched or did_fetch
                        if resolved["status"] == OPEN:
                            # Entry is its own scientific fact: commit it before computing
                            # any resolution, so the audit chain records the established
                            # entry even when the same pass also closes the trade.
                            document["trades"][index] = resolved
                            self.evidence_store.commit(document, now)
                            resolved, did_fetch = self._advance_open(
                                resolved, now, after_restart=after_restart
                            )
                            fetched = fetched or did_fetch
                    elif trade["status"] == OPEN:
                        resolved, did_fetch = self._advance_open(
                            trade, now, after_restart=after_restart
                        )
                        fetched = fetched or did_fetch
                    else:
                        resolved = dict(trade)
                        resolved.update(
                            status=DATA_QUALITY_ERROR,
                            data_quality_status="INTENT_PERSISTENCE_INTERRUPTED",
                            resolution_detail="unarmed intent recovered and failed closed",
                            last_update_time=_format(now),
                        )
                except (MarketFeedError, ShadowObserverError) as exc:
                    errors.append(f"{trade['trade_id']}: {exc}")
                    continue
                if resolved != trade:
                    document["trades"][index] = resolved
                    changed = True
            if changed:
                self.evidence_store.commit(document, now)
        return fetched, errors

    def overview(self) -> dict[str, Any]:
        try:
            document = self.evidence_store.load()
        except ShadowObserverError as exc:
            # Evidence that no longer validates is never rewritten to make it readable;
            # the surface reports the failure instead of presenting untrusted numbers.
            return self._degraded_overview(str(exc))
        health = self.health_store.load()
        decisions = document["decisions"]
        trades = document["trades"]
        long_signals = [item for item in decisions if item.get("decision") == "LONG"]
        suppressed = [item for item in decisions if item["status"] == SUPPRESSED]
        completed = [item for item in trades if item["status"] in COMPLETED_TRADE_STATUSES]
        open_trades = [item for item in trades if item["status"] in ACTIVE_TRADE_STATUSES]
        missed = [item for item in decisions if item["status"] == MISSED_DECISION]
        status = health["status"] if health is not None else "STOPPED"
        return {
            "status": status,
            "label": "AUTOMATED PAPER RESEARCH — NO REAL MONEY",
            "observer_version": OBSERVER_VERSION,
            "evidence_version": EVIDENCE_VERSION,
            "evidence_stage": EVIDENCE_STAGE,
            "initiation_mode": INITIATION_MODE,
            "strategy_version": STRATEGY_VERSION,
            "feature_version": PROSPECTIVE_FEATURES,
            "research_status": RESEARCH_STATUS,
            "champion_status": CHAMPION_STATUS,
            "max_decision_latency_seconds": MAX_DECISION_LATENCY_SECONDS,
            "first_scientific_review_completed_trades": FIRST_REVIEW_COMPLETED_TRADES,
            "last_evaluated_hourly_boundary": (
                health.get("last_evaluated_boundary") if health is not None else None
            ),
            "last_heartbeat": health.get("last_heartbeat") if health is not None else None,
            "next_expected_boundary": (
                health.get("next_expected_boundary") if health is not None else None
            ),
            "last_successful_market_fetch": (
                health.get("last_successful_market_fetch") if health is not None else None
            ),
            "current_error": health.get("current_error") if health is not None else None,
            "missed_prospective_decisions": len(missed),
            "raw_prospective_long_signals": len(long_signals),
            "suppressed_long_signals": len(suppressed),
            "open_shadow_trade": open_trades[0] if open_trades else None,
            "completed_shadow_trades": len(completed),
            "prospective_counters": {
                "prospective_observation_hours": sum(
                    item["status"] in {OBSERVED, SUPPRESSED} for item in decisions
                ),
                "prospective_long_signals": len(long_signals),
                "prospective_suppressed_signals": len(suppressed),
                "prospective_shadow_trades_open": len(open_trades),
                "prospective_shadow_trades_completed": len(completed),
            },
            "audit_chain_version": audit_chain.AUDIT_CHAIN_VERSION,
            "audit_events": len(document["audit_chain"]),
            "evidence_integrity": "VALID",
            "supersedes": SUPERSEDED_EVIDENCE_VERSION,
            "supersedes_status": SUPERSEDED_EVIDENCE_STATUS,
            "build_provenance_verified": (
                health.get("build_provenance_verified") if health is not None else None
            ),
            "build_provenance_sha256": (
                health.get("build_provenance_sha256") if health is not None else None
            ),
            "observer_lease_held": (
                health.get("observer_lease_held") if health is not None else None
            ),
            "manual_evidence_included": False,
            "historical_experiment_counted": False,
            "order_placement": False,
            "credentials": False,
            "real_money": False,
        }

    def _degraded_overview(self, detail: str) -> dict[str, Any]:
        """Report an unreadable or untrusted ledger without inventing scientific counts."""
        health = None
        try:
            health = self.health_store.load()
        except ShadowObserverError:
            health = None
        return {
            "status": "DEGRADED",
            "label": "AUTOMATED PAPER RESEARCH — NO REAL MONEY",
            "observer_version": OBSERVER_VERSION,
            "evidence_version": EVIDENCE_VERSION,
            "evidence_stage": EVIDENCE_STAGE,
            "initiation_mode": INITIATION_MODE,
            "strategy_version": STRATEGY_VERSION,
            "feature_version": PROSPECTIVE_FEATURES,
            "research_status": RESEARCH_STATUS,
            "champion_status": CHAMPION_STATUS,
            "max_decision_latency_seconds": MAX_DECISION_LATENCY_SECONDS,
            "first_scientific_review_completed_trades": FIRST_REVIEW_COMPLETED_TRADES,
            "last_evaluated_hourly_boundary": None,
            "last_heartbeat": health.get("last_heartbeat") if health is not None else None,
            "next_expected_boundary": None,
            "last_successful_market_fetch": None,
            "current_error": detail,
            "missed_prospective_decisions": None,
            "raw_prospective_long_signals": None,
            "suppressed_long_signals": None,
            "open_shadow_trade": None,
            "completed_shadow_trades": None,
            "prospective_counters": None,
            "audit_chain_version": audit_chain.AUDIT_CHAIN_VERSION,
            "audit_events": None,
            "evidence_integrity": "INVALID",
            "supersedes": SUPERSEDED_EVIDENCE_VERSION,
            "supersedes_status": SUPERSEDED_EVIDENCE_STATUS,
            "build_provenance_verified": (
                health.get("build_provenance_verified") if health is not None else None
            ),
            "build_provenance_sha256": (
                health.get("build_provenance_sha256") if health is not None else None
            ),
            "observer_lease_held": (
                health.get("observer_lease_held") if health is not None else None
            ),
            "manual_evidence_included": False,
            "historical_experiment_counted": False,
            "order_placement": False,
            "credentials": False,
            "real_money": False,
        }


def default_observer() -> ProspectiveShadowObserver:
    return ProspectiveShadowObserver(
        ShadowEvidenceStore(ROOT / EVIDENCE_STORE_PATH),
        ShadowHealthStore(ROOT / HEALTH_STORE_PATH),
        lease=ObserverLease(ROOT / LEASE_PATH),
    )


__all__ = [
    "CLOSED_EXPIRY",
    "CLOSED_STOP",
    "CLOSED_TARGET",
    "CONTENDED_ERROR",
    "DATA_QUALITY_ERROR",
    "EVIDENCE_STAGE",
    "EVIDENCE_STORE_PATH",
    "EVIDENCE_VERSION",
    "HEALTH_STORE_PATH",
    "INITIATION_MODE",
    "INTEGRITY_ERROR",
    "LEASE_PATH",
    "MISSED_DECISION",
    "OBSERVER_VERSION",
    "OPEN",
    "PENDING_ENTRY",
    "SUPERSEDED_EVIDENCE_STATUS",
    "SUPERSEDED_EVIDENCE_VERSION",
    "SUPPRESSED",
    "UNVERIFIED_BUILD",
    "ObserverLease",
    "ProspectiveShadowObserver",
    "ShadowEvidenceStore",
    "ShadowHealthStore",
    "ShadowObserverError",
    "decision_projection",
    "default_observer",
    "synchronise_audit_chain",
    "trade_projection",
]
