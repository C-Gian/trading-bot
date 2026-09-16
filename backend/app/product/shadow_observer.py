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
from .platform_file_io import platform_file_operations

ROOT = Path(__file__).resolve().parents[3]

OBSERVER_VERSION = "PROSPECTIVE_SHADOW_PAPER_OBSERVER_V1"
EVIDENCE_VERSION = "FUTURE_SHADOW_PAPER_EVIDENCE_V1"
EVIDENCE_CONTRACT = "docs/contracts/FUTURE_SHADOW_PAPER_EVIDENCE_V1.md"
EVIDENCE_STAGE = "AUTOMATED_PROSPECTIVE_SHADOW_PAPER"
INITIATION_MODE = "AUTOMATED_RESEARCH_OBSERVER"
EVIDENCE_STORE_PATH = "data/paper/FUTURE_SHADOW_PAPER_EVIDENCE_V1.json"
HEALTH_STORE_PATH = "data/paper/PROSPECTIVE_SHADOW_OBSERVER_HEALTH_V1.json"
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


class ShadowEvidenceStore(_DurableJsonStore):
    """Append-only decision and trade evidence, physically separate from manual V2."""

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
            "real_money": False,
            "decisions": [],
            "trades": [],
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
        for field in (
            "backend_start",
            "observer_activation",
            "last_heartbeat",
            "next_expected_boundary",
        ):
            _parse(document.get(field))


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
    ):
        self.evidence_store = evidence_store
        self.health_store = health_store
        self.analyser = analyser
        self.minute_feed = minute_feed
        self.clock = clock or (lambda: datetime.now(UTC))
        self.build_identity = build_identity or default_build_identity()
        self.heartbeat_seconds = heartbeat_seconds
        self._service_lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._active = False

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
                    "real_money": False,
                }
            )
            self.evidence_store.save(document)
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
                self.evidence_store.save(document)
            return changed

    def activate(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Durably activate and account for downtime without evaluating past signals."""
        moment = _utc(now or self.clock())
        with self._service_lock:
            prior = self.health_store.load()
            if prior is None:
                health = self._new_health(moment)
            else:
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
            self.health_store.save(health)
            self._active = True
            self._reconcile_open_trades(moment, after_restart=prior is not None)
            return self.overview()

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
                health.update(status="STOPPED", last_heartbeat=_format(now))
                self.health_store.save(health)
            self._active = False

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
        self, analysis: dict[str, Any], boundary: datetime, now: datetime
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
        self, analysis: dict[str, Any], boundary: datetime, evaluated_at: datetime
    ) -> dict[str, Any]:
        with self.evidence_store.locked():
            document = self.evidence_store.load()
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
            decision = self._pending_decision(analysis, boundary, evaluated_at)
            active = any(trade["status"] in ACTIVE_TRADE_STATUSES for trade in document["trades"])
            trade: dict[str, Any] | None = None
            if decision["decision"] == "LONG" and not active:
                trade = self._unarmed_trade(decision, analysis, evaluated_at)
                document["trades"].append(trade)
            document["decisions"].append(decision)
            self.evidence_store.save(document)

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
            self.evidence_store.save(document)
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

            next_boundary = _parse(health["next_expected_boundary"])
            while next_boundary <= _last_completed_hour(moment):
                if moment > next_boundary + MAX_DECISION_LATENCY:
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
                decision = self._persist_analysis(analysis, next_boundary, moment)
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
                self.evidence_store.save(document)
        return fetched, errors

    def overview(self) -> dict[str, Any]:
        document = self.evidence_store.load()
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
    )


__all__ = [
    "CLOSED_EXPIRY",
    "CLOSED_STOP",
    "CLOSED_TARGET",
    "DATA_QUALITY_ERROR",
    "EVIDENCE_STAGE",
    "EVIDENCE_STORE_PATH",
    "EVIDENCE_VERSION",
    "HEALTH_STORE_PATH",
    "INITIATION_MODE",
    "MISSED_DECISION",
    "OBSERVER_VERSION",
    "OPEN",
    "PENDING_ENTRY",
    "SUPPRESSED",
    "ProspectiveShadowObserver",
    "ShadowEvidenceStore",
    "ShadowHealthStore",
    "ShadowObserverError",
    "default_observer",
]
