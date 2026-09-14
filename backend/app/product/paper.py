"""Paper-trade persistence and lifecycle for the WP-010A ALIGNED analysis flow.

`FUTURE_PAPER_EVIDENCE_V1`. These are prospective paper-research records for a
`PAPER_RESEARCH_CANDIDATE`, kept strictly apart from development experiment evidence.
Nothing here changes strategy logic, places an order, or touches real money.

Entry and exit are resolved by `PROSPECTIVE_PAPER_EXECUTION_V1` on real timestamps.
That adapter reproduces `EXECUTION_MODEL_V2` exactly - pinned field for field against
the frozen engine over pre-cutoff fixtures in
`backend/tests/test_prospective_execution.py` - so forward paper evidence no longer
depends on translating post-cutoff instants onto a historical anchor. The frozen
historical engine is untouched and stays cutoff-protected.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from ..backtest import COST_VERSION, EVENT_SEQUENCE
from ..backtest.models import Bar, ExitReason
from .analysis import (
    CHAMPION_STATUS,
    MAX_HOLD_MINUTES,
    RESEARCH_STATUS,
    STRATEGY_VERSION,
    VARIANT,
)
from .execution import (
    PROSPECTIVE_ENGINE_VERSION,
    PROSPECTIVE_EXECUTION_VERSION,
    ProspectiveIntent,
    simulate_prospective,
)
from .market_feed import Kline, MarketFeedError, fetch_minutes

EVIDENCE_VERSION = "FUTURE_PAPER_EVIDENCE_V1"
EVIDENCE_CONTRACT = "docs/contracts/FUTURE_PAPER_EVIDENCE_V1.md"
EVIDENCE_STAGE = "PROSPECTIVE_PAPER_RESEARCH_NOT_DEVELOPMENT_EVIDENCE"
STORE_PATH = "data/paper/PAPER_TRADES_V1.json"
ENTRY_EXECUTION = EVENT_SEQUENCE[-1]  # NEXT_1M_OPEN_EXECUTION
ENTRY_TIMING_RULE = "NEXT_1M_OPEN"
AMBIGUOUS_FILL_POLICY = "STOP_FIRST_V1"
PROSPECTIVE_EXECUTION = PROSPECTIVE_EXECUTION_VERSION
DATASET_MANIFEST_ID = "PUBLIC_BTCUSDT_SPOT_LIVE_READ_ONLY"
DATASET_CONTENT_HASH = "NOT_A_FROZEN_DEVELOPMENT_DATASET"
PAPER_ENTRY_STATUS = "BLOCKED_CAUSAL_ENTRY_TIMING_V1"
PAPER_ENTRY_BLOCK_REASON = (
    "Paper entry is disabled: an analysis requested after the hourly boundary cannot "
    "prospectively enter at that already-observed minute open."
)

PENDING_ENTRY = "PENDING_ENTRY"
OPEN = "OPEN"
CLOSED_TARGET = "CLOSED_TARGET"
CLOSED_STOP = "CLOSED_STOP"
CLOSED_EXPIRY = "CLOSED_EXPIRY"
INVALIDATED = "INVALIDATED"
STATUSES = (PENDING_ENTRY, OPEN, CLOSED_TARGET, CLOSED_STOP, CLOSED_EXPIRY, INVALIDATED)
ACTIVE_STATUSES = (PENDING_ENTRY, OPEN)
TERMINAL_STATUSES = (CLOSED_TARGET, CLOSED_STOP, CLOSED_EXPIRY, INVALIDATED)

_EXIT_STATUS = {
    ExitReason.TARGET: CLOSED_TARGET,
    ExitReason.STOP: CLOSED_STOP,
    ExitReason.STOP_GAP: CLOSED_STOP,
    ExitReason.EXPIRY: CLOSED_EXPIRY,
}
_INVALID_REASONS = {ExitReason.INVALID_MISSING_ENTRY_BAR, ExitReason.INVALID_NON_TRADABLE}
MINUTE = timedelta(minutes=1)
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class PaperTradeError(RuntimeError):
    """A paper trade could not be created or advanced under the frozen rules."""


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def _format(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat().replace("+00:00", "Z")


class PaperTradeStore:
    """Simple local JSON persistence; the path is injected so tests stay isolated."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._mutex = threading.RLock()

    @contextmanager
    def locked(self):
        """Serialize a complete read-modify-write operation for this store instance."""
        with self._mutex:
            yield

    def load(self) -> list[dict[str, Any]]:
        with self._mutex:
            if not self.path.is_file():
                return []
            document = json.loads(self.path.read_text(encoding="utf-8"))
            expected = {
                "version": EVIDENCE_VERSION,
                "contract": EVIDENCE_CONTRACT,
                "evidence_stage": EVIDENCE_STAGE,
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
                if (
                    not isinstance(trade, dict)
                    or trade.get("status") not in STATUSES
                    or trade.get("direction") != "LONG"
                    or trade.get("real_money") is not False
                    or trade.get("order_placed") is not False
                    or trade.get("leverage") is not False
                    or trade.get("short") is not False
                ):
                    raise PaperTradeError("paper trade store contains an unsafe record")
            return trades

    def save(self, trades: list[dict[str, Any]]) -> None:
        with self._mutex:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": EVIDENCE_VERSION,
                "contract": EVIDENCE_CONTRACT,
                "evidence_stage": EVIDENCE_STAGE,
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
                    staging = Path(handle.name)
                os.replace(staging, self.path)
            finally:
                if staging is not None:
                    staging.unlink(missing_ok=True)

    def active(self) -> list[dict[str, Any]]:
        return [trade for trade in self.load() if trade["status"] in ACTIVE_STATUSES]


def create_from_analysis(analysis: dict[str, Any], store: PaperTradeStore) -> dict[str, Any]:
    """Persist exactly one paper trade for a LONG analysis, or refuse with a reason."""
    if analysis.get("decision") != "LONG" or not analysis.get("plan"):
        raise PaperTradeError("analysis is NO_TRADE; no paper trade is created")
    if analysis.get("data_status") != "OK":
        raise PaperTradeError("analysis did not complete on sound market data")
    analysis_id = analysis.get("analysis_id")
    if not analysis_id:
        raise PaperTradeError("analysis carries no identity")

    raise PaperTradeError(PAPER_ENTRY_BLOCK_REASON)


def _build_trade_from_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Build a synthetic lifecycle fixture; production creation is fail-closed above."""
    analysis_id = str(analysis["analysis_id"])
    plan = analysis["plan"]
    signal_time = _parse(analysis["signal_time"])
    return {
        "trade_id": f"PAPER-{analysis_id[:16]}",
        "evidence_version": EVIDENCE_VERSION,
        "evidence_stage": EVIDENCE_STAGE,
        "analysis_id": analysis_id,
        "strategy_version": STRATEGY_VERSION,
        "variant": VARIANT,
        "research_status": RESEARCH_STATUS,
        "champion_status": CHAMPION_STATUS,
        "symbol": analysis["symbol"],
        "direction": "LONG",
        "status": PENDING_ENTRY,
        "created_at": analysis["analysis_time"],
        "signal_time": analysis["signal_time"],
        "entry_execution": ENTRY_EXECUTION,
        "entry_timing_rule": ENTRY_TIMING_RULE,
        "entry_minute": _format(signal_time),
        "ambiguous_fill_policy": AMBIGUOUS_FILL_POLICY,
        "engine_version": PROSPECTIVE_ENGINE_VERSION,
        "execution_model_version": PROSPECTIVE_EXECUTION_VERSION,
        "cost_model_version": COST_VERSION,
        "reference_price": plan["reference_price"],
        "stop_price": plan["stop_price"],
        "target_price": plan["target_price"],
        "max_hold_minutes": plan["max_hold_minutes"],
        "expiry_time": plan["expiry_time"],
        "entry_time": None,
        "entry_price": None,
        "exit_time": None,
        "exit_price": None,
        "exit_reason": None,
        "net_r": None,
        "holding_minutes": None,
        "resolution_detail": "synthetic lifecycle fixture awaiting entry",
        "last_update_time": analysis["analysis_time"],
        "leverage": False,
        "short": False,
        "order_placed": False,
        "real_money": False,
    }


def _intent(trade: dict[str, Any]) -> ProspectiveIntent:
    return ProspectiveIntent(
        run_id=trade["trade_id"],
        strategy_reference=f"{STRATEGY_VERSION}:{VARIANT}",
        dataset_manifest_id=DATASET_MANIFEST_ID,
        dataset_content_hash=DATASET_CONTENT_HASH,
        signal_timestamp=_parse(trade["entry_minute"]),
        direction="LONG",
        entry_timing_rule=ENTRY_TIMING_RULE,
        stop=Decimal(str(trade["stop_price"])),
        target=Decimal(str(trade["target_price"])),
        target_exit_rule="FIXED_TARGET_OR_STOP_OR_24H",
        max_hold_minutes=trade["max_hold_minutes"],
    )


def _path(klines: tuple[Kline, ...], entry_ms: int) -> tuple[Bar, ...]:
    """Bars from the entry minute onward, on their real UTC instants."""
    return tuple(
        Bar(
            datetime.fromtimestamp(kline.open_ms / 1000, UTC),
            Decimal(str(kline.open)),
            Decimal(str(kline.high)),
            Decimal(str(kline.low)),
            Decimal(str(kline.close)),
        )
        for kline in klines
        if kline.open_ms >= entry_ms
    )


def _resolve(trade: dict[str, Any], klines: tuple[Kline, ...], now: datetime) -> dict[str, Any]:
    """Advance one trade. Missing or gapped minutes never manufacture an outcome."""
    updated = dict(trade)
    updated["last_update_time"] = _format(now)
    entry_minute = _parse(trade["entry_minute"])
    entry_ms = int(entry_minute.timestamp() * 1000)
    path = _path(klines, entry_ms)

    if not path or path[0].open_time != entry_minute:
        if now < entry_minute + MINUTE:
            updated["resolution_detail"] = "entry minute has not closed yet"
            return updated
        updated["status"] = INVALIDATED
        updated["exit_reason"] = ExitReason.INVALID_MISSING_ENTRY_BAR.value
        updated["resolution_detail"] = "the entry minute is missing from public market data"
        return updated

    record = simulate_prospective(_intent(trade), path)
    updated["entry_time"] = _format(record.entry_timestamp) if record.entry_timestamp else None
    updated["entry_price"] = float(record.entry_raw_price) if record.entry_raw_price else None

    if record.data_quality_status == "INVALID":
        updated["status"] = INVALIDATED
        updated["exit_reason"] = record.exit_reason.value
        updated["resolution_detail"] = "the execution adapter rejected this intent as non-tradable"
        return updated
    if record.data_quality_status == "UNRESOLVED":
        updated["status"] = OPEN
        updated["exit_reason"] = None
        updated["resolution_detail"] = (
            f"public minute data is incomplete; no outcome is inferred ({record.exit_reason.value})"
        )
        return updated

    assert record.exit_timestamp is not None and record.net_r is not None
    updated["status"] = _EXIT_STATUS[record.exit_reason]
    updated["exit_time"] = _format(record.exit_timestamp)
    updated["exit_price"] = float(record.exit_raw_price) if record.exit_raw_price else None
    updated["exit_reason"] = record.exit_reason.value
    updated["net_r"] = float(record.net_r)
    updated["holding_minutes"] = record.holding_minutes
    updated["resolution_detail"] = "resolved by PROSPECTIVE_PAPER_EXECUTION_V1"
    return updated


def update_lifecycle(
    store: PaperTradeStore,
    *,
    now: datetime | None = None,
    client: Any = None,
    feed: Any = None,
) -> dict[str, Any]:
    """Explicitly advance every active trade. Deterministic and idempotent."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    with store.locked():
        trades = store.load()
        advanced, errors = [], []
        changed = False
        for index, trade in enumerate(trades):
            if trade["status"] in TERMINAL_STATUSES:
                continue
            entry_ms = int(_parse(trade["entry_minute"]).timestamp() * 1000)
            try:
                klines = fetch_minutes(
                    entry_ms,
                    trade["max_hold_minutes"] + 1,
                    now=now,
                    client=client,
                    feed=feed,
                )
            except MarketFeedError as exc:
                errors.append({"trade_id": trade["trade_id"], "error": str(exc)})
                continue
            resolved = _resolve(trade, klines, now)
            if resolved != trade:
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
        "contract": EVIDENCE_CONTRACT,
        "research_status": RESEARCH_STATUS,
        "champion_status": CHAMPION_STATUS,
        "strategy_version": STRATEGY_VERSION,
        "max_hold_minutes": MAX_HOLD_MINUTES,
        "statuses": list(STATUSES),
        "active": [trade for trade in trades if trade["status"] in ACTIVE_STATUSES],
        "recent": trades[-limit:],
        "recorded": len(trades),
        "paper_entry_status": PAPER_ENTRY_STATUS,
        "paper_entry_block_reason": PAPER_ENTRY_BLOCK_REASON,
        "real_money": False,
    }
