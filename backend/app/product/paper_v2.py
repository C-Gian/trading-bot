"""Durable-intent-first causal paper lifecycle for the ALIGNED candidate.

V1 remains blocked and unchanged in :mod:`app.product.paper`.  V2 first commits an
unarmed LONG intent, records the authoritative server persistence instant only after
that commit, and then permits only completed minute bars whose open is strictly later.
"""

from __future__ import annotations

import importlib
import json
import os
import tempfile
import threading
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ..backtest import COST_VERSION
from ..backtest.models import Bar, ExitReason
from .analysis import (
    CHAMPION_STATUS,
    MAX_HOLD_MINUTES,
    RESEARCH_STATUS,
    STOP_FRACTION,
    STRATEGY_VERSION,
    TARGET_FRACTION,
    VARIANT,
    analysis_identity,
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

EVIDENCE_VERSION = "FUTURE_PAPER_EVIDENCE_V2"
EVIDENCE_CONTRACT = "docs/contracts/FUTURE_PAPER_EVIDENCE_V2.md"
EVIDENCE_STAGE = "MANUAL_PROSPECTIVE_PAPER"
INITIATION_MODE = "OWNER_MANUAL"
STORE_PATH = "data/paper/PAPER_TRADES_V2.json"
PAPER_ENTRY_STATUS = "AVAILABLE"
PAPER_ENTRY_BLOCK_REASON = ""
ENTRY_EXECUTION = "STRICTLY_FUTURE_1M_OPEN"
DATASET_MANIFEST_ID = "PUBLIC_BTCUSDT_SPOT_LIVE_READ_ONLY"
DATASET_CONTENT_HASH = "NOT_A_FROZEN_DEVELOPMENT_DATASET"
ENTRY_TIMEOUT_OPPORTUNITIES = 5

PERSISTING_INTENT = "PERSISTING_INTENT"
PENDING_ENTRY = "PENDING_ENTRY"
OPEN = "OPEN"
CLOSED_TARGET = "CLOSED_TARGET"
CLOSED_STOP = "CLOSED_STOP"
CLOSED_EXPIRY = "CLOSED_EXPIRY"
INVALIDATED = "INVALIDATED"
INVALIDATED_ENTRY_UNAVAILABLE = "INVALIDATED_ENTRY_UNAVAILABLE"
INVALIDATED_INTENT_PERSISTENCE = "INVALIDATED_INTENT_PERSISTENCE"
STATUSES = (
    PERSISTING_INTENT,
    PENDING_ENTRY,
    OPEN,
    CLOSED_TARGET,
    CLOSED_STOP,
    CLOSED_EXPIRY,
    INVALIDATED,
    INVALIDATED_ENTRY_UNAVAILABLE,
    INVALIDATED_INTENT_PERSISTENCE,
)
ACTIVE_STATUSES = (PERSISTING_INTENT, PENDING_ENTRY, OPEN)
TERMINAL_STATUSES = (
    CLOSED_TARGET,
    CLOSED_STOP,
    CLOSED_EXPIRY,
    INVALIDATED,
    INVALIDATED_ENTRY_UNAVAILABLE,
    INVALIDATED_INTENT_PERSISTENCE,
)

_EXIT_STATUS = {
    ExitReason.TARGET: CLOSED_TARGET,
    ExitReason.STOP: CLOSED_STOP,
    ExitReason.STOP_GAP: CLOSED_STOP,
    ExitReason.EXPIRY: CLOSED_EXPIRY,
}
MINUTE = timedelta(minutes=1)
MINUTE_MS = 60_000

_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[Path, threading.RLock] = {}


class PaperTradeError(RuntimeError):
    """A paper intent cannot be persisted or advanced under the V2 contract."""


def _utc(instant: datetime) -> datetime:
    if instant.tzinfo is None:
        raise PaperTradeError("authoritative timestamps must be timezone-aware")
    return instant.astimezone(UTC)


def _parse(value: Any) -> datetime:
    if not isinstance(value, str):
        raise PaperTradeError("paper trade contains an invalid timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PaperTradeError("paper trade contains an invalid timestamp") from exc
    return _utc(parsed)


def _format(instant: datetime) -> str:
    return _utc(instant).isoformat().replace("+00:00", "Z")


def _decimal(value: Any) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PaperTradeError("paper trade contains an invalid numeric value") from exc
    if not parsed.is_finite():
        raise PaperTradeError("paper trade contains a non-finite numeric value")
    return parsed


def _next_minute_strictly_after(instant: datetime) -> datetime:
    utc = _utc(instant)
    return utc.replace(second=0, microsecond=0) + MINUTE


def _path_lock(path: Path) -> threading.RLock:
    resolved = path.resolve()
    with _LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(resolved, threading.RLock())


@contextmanager
def _interprocess_lock(path: Path):
    """Serialize writers across local backend processes using a one-byte OS lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl = importlib.import_module("fcntl")

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _replace_durably(staging: Path, target: Path) -> None:
    """Atomically replace and flush rename metadata on the supported platform."""
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        move = kernel32.MoveFileExW
        move.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
        move.restype = ctypes.c_int
        replace_existing = 0x1
        write_through = 0x8
        if not move(str(staging), str(target), replace_existing | write_through):
            error = ctypes.get_last_error()
            raise OSError(error, ctypes.FormatError(error), str(target))
        return
    os.replace(staging, target)
    descriptor = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class PaperTradeStore:
    """Atomic V2 JSON persistence with one shared in-process lock per path."""

    evidence_version = EVIDENCE_VERSION

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

    def load(self) -> list[dict[str, Any]]:
        with self.locked():
            if not self.path.is_file():
                return []
            try:
                document = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise PaperTradeError("paper trade store is unreadable") from exc
            expected = {
                "version": EVIDENCE_VERSION,
                "contract": EVIDENCE_CONTRACT,
                "evidence_stage": EVIDENCE_STAGE,
                "initiation_mode": INITIATION_MODE,
                "champion_status": CHAMPION_STATUS,
                "research_status": RESEARCH_STATUS,
                "real_money": False,
            }
            if any(document.get(key) != value for key, value in expected.items()):
                raise PaperTradeError("paper trade store safety metadata mismatch")
            trades = document.get("trades")
            if not isinstance(trades, list):
                raise PaperTradeError("paper trade store has an invalid trade collection")
            for trade in trades:
                self._validate_trade(trade)
            self._validate_collection(trades)
            return trades

    @staticmethod
    def _validate_collection(trades: list[dict[str, Any]]) -> None:
        ids = [trade["trade_id"] for trade in trades]
        analyses = [trade["analysis_id"] for trade in trades]
        if len(ids) != len(set(ids)) or len(analyses) != len(set(analyses)):
            raise PaperTradeError("paper trade store contains duplicate identities")
        if sum(trade["status"] in ACTIVE_STATUSES for trade in trades) > 1:
            raise PaperTradeError("paper trade store contains multiple active intents")

    @staticmethod
    def _validate_trade(trade: Any) -> None:
        if not isinstance(trade, dict):
            raise PaperTradeError("paper trade store contains an unsafe record")
        required = {
            "schema_version",
            "trade_id",
            "analysis_id",
            "status",
            "evidence_version",
            "strategy_version",
            "variant",
            "research_status",
            "champion_status",
            "symbol",
            "execution_model_version",
            "engine_version",
            "cost_model_version",
            "evidence_stage",
            "initiation_mode",
            "signal_timestamp",
            "analysis_completed_at",
            "intent_persisted_at",
            "entry_not_before",
            "entry_search_cursor",
            "entry_opportunities_checked",
            "entry_timeout_opportunities",
            "entry_execution",
            "entry_timing_rule",
            "ambiguous_fill_policy",
            "entry_time",
            "entry_price",
            "entry_minute",
            "entry_observation",
            "stop_price",
            "target_price",
            "expiry_time",
            "exit_time",
            "exit_price",
            "exit_reason",
            "net_r",
            "holding_minutes",
            "stop_fraction",
            "target_fraction",
            "max_hold_minutes",
            "real_money",
            "order_placed",
            "leverage",
            "short",
        }
        if (
            not required.issubset(trade)
            or trade.get("schema_version") != 2
            or trade.get("status") not in STATUSES
            or trade.get("evidence_version") != EVIDENCE_VERSION
            or trade.get("direction") != "LONG"
            or trade.get("strategy_version") != STRATEGY_VERSION
            or trade.get("variant") != VARIANT
            or trade.get("research_status") != RESEARCH_STATUS
            or trade.get("champion_status") != CHAMPION_STATUS
            or trade.get("symbol") != "BTCUSDT"
            or trade.get("execution_model_version") != PAPER_EXECUTION_VERSION
            or trade.get("engine_version") != PAPER_ENGINE_VERSION
            or trade.get("cost_model_version") != COST_VERSION
            or trade.get("evidence_stage") != EVIDENCE_STAGE
            or trade.get("initiation_mode") != INITIATION_MODE
            or trade.get("entry_timeout_opportunities") != ENTRY_TIMEOUT_OPPORTUNITIES
            or trade.get("entry_execution") != ENTRY_EXECUTION
            or trade.get("entry_timing_rule") != ENTRY_TIMING_RULE
            or trade.get("ambiguous_fill_policy") != AMBIGUOUS_FILL_POLICY
            or _decimal(trade.get("stop_fraction")) != Decimal("0.02")
            or _decimal(trade.get("target_fraction")) != Decimal("0.04")
            or trade.get("max_hold_minutes") != MAX_HOLD_MINUTES
            or trade.get("real_money") is not False
            or trade.get("order_placed") is not False
            or trade.get("leverage") is not False
            or trade.get("short") is not False
        ):
            raise PaperTradeError("paper trade store contains an unsafe record")
        unarmed_statuses = {PERSISTING_INTENT, INVALIDATED_INTENT_PERSISTENCE}
        if trade["status"] not in unarmed_statuses:
            persisted = _parse(trade.get("intent_persisted_at"))
            lower_bound = _parse(trade.get("entry_not_before"))
            completed = _parse(trade["analysis_completed_at"])
            if completed > persisted:
                raise PaperTradeError("paper intent predates analysis completion")
            if lower_bound != _next_minute_strictly_after(persisted):
                raise PaperTradeError("paper trade contains an unsafe causal lower bound")
            signal = _parse(trade["signal_timestamp"])
            if trade.get("signal_age_seconds") != (persisted - signal).total_seconds():
                raise PaperTradeError("paper trade contains a forged signal age")
        else:
            if any(
                trade.get(field) is not None
                for field in (
                    "intent_persisted_at",
                    "entry_not_before",
                    "entry_time",
                    "entry_price",
                    "stop_price",
                    "target_price",
                    "expiry_time",
                )
            ):
                raise PaperTradeError("unarmed paper intent contains forged causal fields")
        if trade["status"] == PENDING_ENTRY and any(
            trade.get(field) is not None
            for field in ("entry_time", "entry_price", "stop_price", "target_price", "expiry_time")
        ):
            raise PaperTradeError("pending paper intent contains a forged fill or plan")
        filled_statuses = {OPEN, CLOSED_TARGET, CLOSED_STOP, CLOSED_EXPIRY, INVALIDATED}
        if (trade["status"] in filled_statuses) != (trade.get("entry_time") is not None):
            raise PaperTradeError("paper trade status and fill are inconsistent")
        if trade["status"] not in filled_statuses and any(
            trade.get(field) is not None
            for field in (
                "entry_price",
                "entry_minute",
                "entry_observation",
                "reference_price",
                "stop_price",
                "target_price",
                "expiry_time",
            )
        ):
            raise PaperTradeError("unfilled paper trade contains a forged plan")
        if trade.get("entry_time") is not None:
            entry_time = _parse(trade["entry_time"])
            persisted = _parse(trade["intent_persisted_at"])
            entry_not_before = _parse(trade["entry_not_before"])
            entry_price = _decimal(trade["entry_price"])
            tolerance = Decimal("0.00000001")
            checked = trade.get("entry_opportunities_checked")
            expected_checked = int((entry_time - entry_not_before) / MINUTE) + 1
            if (
                entry_time.second
                or entry_time.microsecond
                or entry_time < entry_not_before
                or entry_time <= persisted
                or trade.get("entry_minute") != trade["entry_time"]
                or checked != expected_checked
                or not 1 <= expected_checked <= ENTRY_TIMEOUT_OPPORTUNITIES
            ):
                raise PaperTradeError("filled paper trade violates its causal lower bound")
            if abs(_decimal(trade["stop_price"]) - entry_price * STOP_FRACTION) > tolerance:
                raise PaperTradeError("filled paper trade contains a forged stop")
            if abs(_decimal(trade["target_price"]) - entry_price * TARGET_FRACTION) > tolerance:
                raise PaperTradeError("filled paper trade contains a forged target")
            if _parse(trade["expiry_time"]) != entry_time + timedelta(minutes=MAX_HOLD_MINUTES):
                raise PaperTradeError("filled paper trade contains a forged expiry")
            observation = trade.get("entry_observation")
            if (
                not isinstance(observation, dict)
                or observation.get("open_time") != trade["entry_time"]
                or _decimal(observation.get("open")) != entry_price
            ):
                raise PaperTradeError("filled paper trade contains a forged entry observation")
            try:
                observed = _bar(observation)
            except (KeyError, TypeError, ValueError) as exc:
                raise PaperTradeError("filled paper trade has a malformed entry bar") from exc
            if not (
                observed.low <= observed.open <= observed.high
                and observed.low <= observed.close <= observed.high
            ):
                raise PaperTradeError("filled paper trade has an impossible entry bar")
        checked = trade.get("entry_opportunities_checked")
        if type(checked) is not int or not 0 <= checked <= ENTRY_TIMEOUT_OPPORTUNITIES:
            raise PaperTradeError("paper trade has invalid entry opportunity accounting")
        if trade["status"] == PENDING_ENTRY:
            cursor = _parse(trade["entry_search_cursor"])
            lower_bound = _parse(trade["entry_not_before"])
            if cursor != lower_bound + checked * MINUTE or checked >= ENTRY_TIMEOUT_OPPORTUNITIES:
                raise PaperTradeError("pending paper trade has an unsafe causal cursor")
        if trade["status"] == INVALIDATED_ENTRY_UNAVAILABLE and (
            checked != ENTRY_TIMEOUT_OPPORTUNITIES
            or trade.get("entry_time") is not None
            or trade.get("entry_search_cursor") is not None
        ):
            raise PaperTradeError("entry timeout record is internally inconsistent")
        exit_fields = ("exit_time", "exit_price", "net_r", "holding_minutes")
        if trade["status"] == OPEN and any(trade.get(field) is not None for field in exit_fields):
            raise PaperTradeError("open paper trade contains a forged terminal result")
        closed_reasons = {
            CLOSED_TARGET: {ExitReason.TARGET.value},
            CLOSED_STOP: {ExitReason.STOP.value, ExitReason.STOP_GAP.value},
            CLOSED_EXPIRY: {ExitReason.EXPIRY.value},
        }
        if trade["status"] in closed_reasons:
            if (
                any(trade.get(field) is None for field in exit_fields)
                or trade.get("exit_reason") not in closed_reasons[trade["status"]]
                or _parse(trade["exit_time"]) < _parse(trade["entry_time"])
                or type(trade["holding_minutes"]) is not int
                or trade["holding_minutes"] < 0
            ):
                raise PaperTradeError("closed paper trade contains an inconsistent result")
        elif trade["status"] != INVALIDATED and trade.get("exit_reason") is not None:
            allowed_invalidations = {
                INVALIDATED_ENTRY_UNAVAILABLE,
                INVALIDATED_INTENT_PERSISTENCE,
            }
            if trade["status"] not in allowed_invalidations:
                raise PaperTradeError("nonterminal paper trade contains a forged exit reason")

    def save(self, trades: list[dict[str, Any]]) -> None:
        with self.locked():
            for trade in trades:
                self._validate_trade(trade)
            self._validate_collection(trades)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": EVIDENCE_VERSION,
                "contract": EVIDENCE_CONTRACT,
                "evidence_stage": EVIDENCE_STAGE,
                "initiation_mode": INITIATION_MODE,
                "champion_status": CHAMPION_STATUS,
                "research_status": RESEARCH_STATUS,
                "real_money": False,
                "trades": trades,
            }
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
                _replace_durably(staging, self.path)
            finally:
                if staging is not None:
                    staging.unlink(missing_ok=True)

    def active(self) -> list[dict[str, Any]]:
        return [trade for trade in self.load() if trade["status"] in ACTIVE_STATUSES]


def _validate_analysis(analysis: dict[str, Any]) -> tuple[datetime, datetime]:
    if analysis.get("decision") != "LONG" or not analysis.get("plan"):
        raise PaperTradeError("analysis is NO_TRADE; no paper trade is created")
    if analysis.get("data_status") != "OK":
        raise PaperTradeError("analysis did not complete on sound market data")
    if (
        analysis.get("strategy_version") != STRATEGY_VERSION
        or analysis.get("variant") != VARIANT
        or analysis.get("research_status") != RESEARCH_STATUS
        or analysis.get("champion_status") != CHAMPION_STATUS
        or analysis.get("symbol") != "BTCUSDT"
        or analysis.get("real_money") is not False
    ):
        raise PaperTradeError("analysis identity or safety classification mismatch")
    plan = analysis["plan"]
    if not isinstance(plan, dict):
        raise PaperTradeError("analysis plan is malformed")
    if (
        plan.get("direction") != "LONG"
        or Decimal(str(plan.get("stop_fraction"))) != Decimal("0.02")
        or Decimal(str(plan.get("target_fraction"))) != Decimal("0.04")
        or plan.get("max_hold_minutes") != MAX_HOLD_MINUTES
        or plan.get("leverage") is not False
        or plan.get("short") is not False
        or plan.get("order_placed") is not False
    ):
        raise PaperTradeError("analysis plan does not match the frozen paper candidate")
    analysis_id = analysis.get("analysis_id")
    if not analysis_id or analysis_id != analysis_identity(analysis):
        raise PaperTradeError("analysis identity mismatch")
    completed = _parse(analysis.get("analysis_time"))
    signal = _parse(analysis.get("signal_time"))
    if signal.second or signal.microsecond or signal.minute:
        raise PaperTradeError("signal timestamp is not an hourly UTC boundary")
    if completed < signal:
        raise PaperTradeError("analysis completed before its signal timestamp")
    return completed, signal


def _unarmed_intent(
    analysis: dict[str, Any], analysis_completed_at: datetime, signal: datetime
) -> dict[str, Any]:
    analysis_id = str(analysis["analysis_id"])
    return {
        "schema_version": 2,
        "trade_id": f"PAPER-V2-{analysis_id[:16]}",
        "evidence_version": EVIDENCE_VERSION,
        "evidence_stage": EVIDENCE_STAGE,
        "initiation_mode": INITIATION_MODE,
        "analysis_id": analysis_id,
        "strategy_version": STRATEGY_VERSION,
        "variant": VARIANT,
        "research_status": RESEARCH_STATUS,
        "champion_status": CHAMPION_STATUS,
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "status": PERSISTING_INTENT,
        "created_at": _format(analysis_completed_at),
        "analysis_completed_at": _format(analysis_completed_at),
        "intent_persisted_at": None,
        "signal_timestamp": _format(signal),
        "signal_time": _format(signal),
        "signal_age_seconds": None,
        "entry_not_before": None,
        "entry_search_cursor": None,
        "entry_opportunities_checked": 0,
        "entry_timeout_opportunities": ENTRY_TIMEOUT_OPPORTUNITIES,
        "entry_execution": ENTRY_EXECUTION,
        "entry_timing_rule": ENTRY_TIMING_RULE,
        "entry_minute": None,
        "ambiguous_fill_policy": AMBIGUOUS_FILL_POLICY,
        "engine_version": PAPER_ENGINE_VERSION,
        "execution_model_version": PAPER_EXECUTION_VERSION,
        "cost_model_version": COST_VERSION,
        "analysis_reference_price": analysis.get("reference_price"),
        "reference_price": None,
        "stop_fraction": float(Decimal(1) - STOP_FRACTION),
        "target_fraction": float(TARGET_FRACTION - Decimal(1)),
        "stop_price": None,
        "target_price": None,
        "max_hold_minutes": MAX_HOLD_MINUTES,
        "expiry_time": None,
        "entry_time": None,
        "entry_price": None,
        "entry_observation": None,
        "exit_time": None,
        "exit_price": None,
        "exit_reason": None,
        "net_r": None,
        "holding_minutes": None,
        "resolution_detail": "durable intent is being armed; no entry is permitted",
        "last_update_time": _format(analysis_completed_at),
        "leverage": False,
        "short": False,
        "order_placed": False,
        "real_money": False,
    }


def create_from_analysis(
    analysis: dict[str, Any],
    store: PaperTradeStore,
    *,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Commit an unarmed intent, then arm only a strictly future minute."""
    analysis_evaluated_at, signal = _validate_analysis(analysis)
    authoritative_clock = clock or (lambda: datetime.now(UTC))
    analysis_completed_at = _utc(authoritative_clock())
    if analysis_completed_at < analysis_evaluated_at:
        raise PaperTradeError("server clock predates the completed analysis")
    with store.locked():
        trades = store.load()
        if any(trade["status"] in ACTIVE_STATUSES for trade in trades):
            raise PaperTradeError("a paper intent is already PENDING_ENTRY or OPEN")
        if any(trade["analysis_id"] == analysis["analysis_id"] for trade in trades):
            raise PaperTradeError("a paper trade already exists for this analysis")
        intent = _unarmed_intent(analysis, analysis_completed_at, signal)
        store.save([*trades, intent])

        persisted_at = _utc(authoritative_clock())
        if persisted_at < analysis_completed_at:
            raise PaperTradeError("server clock predates analysis completion")
        entry_not_before = _next_minute_strictly_after(persisted_at)
        armed = dict(intent)
        armed.update(
            status=PENDING_ENTRY,
            created_at=_format(persisted_at),
            intent_persisted_at=_format(persisted_at),
            signal_age_seconds=(persisted_at - signal).total_seconds(),
            entry_not_before=_format(entry_not_before),
            entry_search_cursor=_format(entry_not_before),
            resolution_detail="durable LONG intent; awaiting a strictly future completed minute",
            last_update_time=_format(persisted_at),
        )
        store.save([*trades, armed])
        return armed


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


def _fill(trade: dict[str, Any], kline: Kline, opportunities: int) -> dict[str, Any]:
    fill_time = datetime.fromtimestamp(kline.open_ms / 1000, UTC)
    persisted_at = _parse(trade["intent_persisted_at"])
    if fill_time <= persisted_at:
        raise PaperTradeError("market feed attempted a non-causal paper fill")
    price = Decimal(str(kline.open))
    stop = price * STOP_FRACTION
    target = price * TARGET_FRACTION
    updated = dict(trade)
    updated.update(
        status=OPEN,
        entry_opportunities_checked=opportunities,
        entry_search_cursor=None,
        entry_minute=_format(fill_time),
        entry_time=_format(fill_time),
        entry_price=float(price),
        reference_price=float(price),
        stop_price=float(stop),
        target_price=float(target),
        expiry_time=_format(fill_time + timedelta(minutes=MAX_HOLD_MINUTES)),
        entry_observation=_kline_record(kline),
        resolution_detail="filled from the first available legal completed minute",
    )
    return updated


def _attempt_entry(
    trade: dict[str, Any], now: datetime, *, client: Any = None, feed: Any = None
) -> dict[str, Any]:
    cursor = _parse(trade["entry_search_cursor"])
    last_completed = now.replace(second=0, microsecond=0) - MINUTE
    if last_completed < cursor:
        return trade
    checked = int(trade["entry_opportunities_checked"])
    remaining = ENTRY_TIMEOUT_OPPORTUNITIES - checked
    available = int((last_completed - cursor) / MINUTE) + 1
    count = min(remaining, available)
    kwargs: dict[str, Any] = {"now": now}
    if client is not None:
        kwargs["client"] = client
    if feed is not None:
        kwargs["feed"] = feed
    klines = fetch_minutes(int(cursor.timestamp() * 1000), count, **kwargs)
    candidates = [cursor + index * MINUTE for index in range(count)]
    by_open = {kline.open_ms: kline for kline in klines}
    for offset, candidate in enumerate(candidates):
        kline = by_open.get(int(candidate.timestamp() * 1000))
        if kline is not None:
            return _fill(trade, kline, checked + offset + 1)
    total = checked + count
    updated = dict(trade)
    updated["entry_opportunities_checked"] = total
    if total >= ENTRY_TIMEOUT_OPPORTUNITIES:
        updated.update(
            status=INVALIDATED_ENTRY_UNAVAILABLE,
            entry_search_cursor=None,
            exit_reason=INVALIDATED_ENTRY_UNAVAILABLE,
            resolution_detail="five completed legal entry opportunities were unavailable",
        )
    else:
        updated.update(
            entry_search_cursor=_format(cursor + count * MINUTE),
            resolution_detail="completed entry opportunity unavailable; causal cursor advanced",
        )
    return updated


def _paper_path(trade: dict[str, Any], klines: tuple[Kline, ...]) -> tuple[Bar, ...]:
    observed = _bar(trade["entry_observation"])
    rows = {observed.open_time: observed}
    for kline in klines:
        bar = _bar(_kline_record(kline))
        if bar.open_time > observed.open_time:
            rows[bar.open_time] = bar
    return tuple(rows[key] for key in sorted(rows))


def _advance_open(
    trade: dict[str, Any], now: datetime, *, client: Any = None, feed: Any = None
) -> dict[str, Any]:
    entry = _parse(trade["entry_time"])
    kwargs: dict[str, Any] = {"now": now}
    if client is not None:
        kwargs["client"] = client
    if feed is not None:
        kwargs["feed"] = feed
    klines = fetch_minutes(int(entry.timestamp() * 1000), trade["max_hold_minutes"] + 1, **kwargs)
    plan = CausalPaperPlan(
        run_id=trade["trade_id"],
        strategy_reference=f"{STRATEGY_VERSION}:{VARIANT}",
        dataset_manifest_id=DATASET_MANIFEST_ID,
        dataset_content_hash=DATASET_CONTENT_HASH,
        entry_timestamp=entry,
        stop=Decimal(str(trade["stop_price"])),
        target=Decimal(str(trade["target_price"])),
        max_hold_minutes=trade["max_hold_minutes"],
    )
    record = simulate_causal_paper(plan, _paper_path(trade, klines))
    updated = dict(trade)
    if record.data_quality_status == "INVALID":
        updated.update(
            status=INVALIDATED,
            exit_reason=record.exit_reason.value,
            resolution_detail="the V2 execution adapter rejected the filled plan",
        )
    elif record.data_quality_status == "UNRESOLVED":
        updated.update(
            status=OPEN,
            exit_reason=None,
            resolution_detail=f"position unresolved on complete data ({record.exit_reason.value})",
        )
    else:
        assert record.exit_timestamp is not None and record.net_r is not None
        updated.update(
            status=_EXIT_STATUS[record.exit_reason],
            exit_time=_format(record.exit_timestamp),
            exit_price=float(record.exit_raw_price) if record.exit_raw_price else None,
            exit_reason=record.exit_reason.value,
            net_r=float(record.net_r),
            holding_minutes=record.holding_minutes,
            resolution_detail=f"resolved by {PAPER_EXECUTION_VERSION}",
        )
    return updated


def update_lifecycle(
    store: PaperTradeStore,
    *,
    now: datetime | None = None,
    client: Any = None,
    feed: Any = None,
) -> dict[str, Any]:
    """Advance active V2 records; a successful missing-minute check is never revisited."""
    moment = _utc(now or datetime.now(UTC))
    advanced: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    with store.locked():
        trades = store.load()
        changed = False
        for index, trade in enumerate(trades):
            if trade["status"] in TERMINAL_STATUSES:
                continue
            try:
                if trade["status"] == PERSISTING_INTENT:
                    resolved = dict(trade)
                    resolved.update(
                        status=INVALIDATED_INTENT_PERSISTENCE,
                        exit_reason="INTENT_PERSISTENCE_INTERRUPTED",
                        resolution_detail="unarmed intent recovered after interrupted persistence",
                    )
                elif trade["status"] == PENDING_ENTRY:
                    resolved = _attempt_entry(trade, moment, client=client, feed=feed)
                    if resolved["status"] == OPEN:
                        try:
                            resolved = _advance_open(resolved, moment, client=client, feed=feed)
                        except MarketFeedError as exc:
                            errors.append({"trade_id": trade["trade_id"], "error": str(exc)})
                else:
                    resolved = _advance_open(trade, moment, client=client, feed=feed)
            except MarketFeedError as exc:
                errors.append({"trade_id": trade["trade_id"], "error": str(exc)})
                continue
            if resolved != trade:
                resolved = {**resolved, "last_update_time": _format(moment)}
                trades[index] = resolved
                changed = True
                advanced.append(resolved)
        if changed:
            store.save(trades)
    return {
        "evidence_version": EVIDENCE_VERSION,
        "updated": len(advanced),
        "trades": advanced,
        "errors": errors,
        "real_money": False,
    }


def listing(store: PaperTradeStore, *, limit: int = 20) -> dict[str, Any]:
    trades = store.load()
    return {
        "evidence_version": EVIDENCE_VERSION,
        "evidence_stage": EVIDENCE_STAGE,
        "initiation_mode": INITIATION_MODE,
        "contract": EVIDENCE_CONTRACT,
        "research_status": RESEARCH_STATUS,
        "champion_status": CHAMPION_STATUS,
        "strategy_version": STRATEGY_VERSION,
        "execution_model_version": PAPER_EXECUTION_VERSION,
        "entry_timeout_opportunities": ENTRY_TIMEOUT_OPPORTUNITIES,
        "max_hold_minutes": MAX_HOLD_MINUTES,
        "statuses": list(STATUSES),
        "active": [trade for trade in trades if trade["status"] in ACTIVE_STATUSES],
        "recent": trades[-limit:],
        "recorded": len(trades),
        "paper_entry_status": PAPER_ENTRY_STATUS,
        "paper_entry_block_reason": PAPER_ENTRY_BLOCK_REASON,
        "real_money": False,
    }
