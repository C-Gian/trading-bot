"""Checkpoint-1 signal-board plumbing: causal descriptive measurements only.

These snapshots prove that signals are read from the causal view with explicit `market_time` /
`available_at`, quality and role. Every one is `DIAGNOSTIC`: none is a frozen G1 construction
(the Research Director freezes the P1/P2 structure, location, trigger and corroboration
definitions later) and none feeds the decision path.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from .bars import Bar, CausalView
from .canonical import content_id
from .records import SignalRole, SignalSnapshot

SIGNAL_VERSION = "G1-CP1-PLUMBING-V1"
PLUMBING_REASON = "PLUMBING_MEASUREMENT_NOT_A_FROZEN_G1_CONSTRUCTION"


def _snapshot(
    run_id: str,
    family: str,
    name: str,
    timeframe: str,
    market_time: datetime,
    available_at: datetime,
    values: tuple[tuple[str, float | str | None], ...],
    state: str,
    quality: str,
    refs: tuple[str, ...] = (),
) -> SignalSnapshot:
    payload = (run_id, family, name, SIGNAL_VERSION, market_time, available_at, values, state)
    return SignalSnapshot(
        content_id("SIG", payload),
        run_id,
        family,
        name,
        SIGNAL_VERSION,
        market_time,
        available_at,
        timeframe,
        values,
        state,
        quality,
        SignalRole.DIAGNOSTIC,
        PLUMBING_REASON,
        "Causal descriptive measurement for the board; not a decision input.",
        refs,
    )


def _direction(bar: Bar | None) -> str:
    if bar is None:
        return "UNAVAILABLE"
    if bar.close > bar.open:
        return "UP"
    return "DOWN" if bar.close < bar.open else "FLAT"


def _return(bar: Bar | None) -> float | None:
    return None if bar is None else float(bar.close / bar.open - 1)


def board(run_id: str, view: CausalView, decision_time: datetime) -> tuple[SignalSnapshot, ...]:
    signals = []
    for family, timeframe in (
        ("MOMENTUM_VOLATILITY", "15m"),
        ("STRUCTURE_TREND", "1h"),
        ("STRUCTURE_TREND", "4h"),
    ):
        bar = view.last(timeframe)
        signals.append(
            _snapshot(
                run_id,
                family,
                f"last_completed_{timeframe}_move",
                timeframe,
                decision_time if bar is None else bar.open_time,
                decision_time if bar is None else bar.available_at,
                (("return", _return(bar)),),
                _direction(bar),
                "UNAVAILABLE" if bar is None else bar.quality,
            )
        )
    day = view.last("1d")
    signals.append(
        _snapshot(
            run_id,
            "PRICE_LOCATION_VALUE",
            "prior_completed_utc_day_range",
            "1d",
            decision_time if day is None else day.open_time,
            decision_time if day is None else day.available_at,
            (
                ("high", None if day is None else float(day.high)),
                ("low", None if day is None else float(day.low)),
            ),
            "UNAVAILABLE" if day is None else "KNOWN",
            "UNAVAILABLE" if day is None else day.quality,
        )
    )
    # The UTC session containing the last completed minute.
    session_start = (decision_time - timedelta(minutes=1)).replace(hour=0, minute=0)
    minutes = [b for b in view.bars("1m", 1440) if b.open_time >= session_start]
    volume = sum((b.volume for b in minutes), Decimal(0))
    vwap = (
        None
        if not minutes or volume == 0
        else float(sum((b.close * b.volume for b in minutes), Decimal(0)) / volume)
    )
    signals.append(
        _snapshot(
            run_id,
            "PRICE_LOCATION_VALUE",
            "utc_session_vwap_completed_1m",
            "1m",
            session_start,
            decision_time,
            (("vwap", vwap), ("minutes", float(len(minutes)))),
            "UNAVAILABLE" if vwap is None else "KNOWN",
            "COMPLETE"
            if len(minutes) == int((decision_time - session_start).total_seconds() // 60)
            else "INCOMPLETE",
        )
    )
    decision_bar = view.bar_closing_at("15m", decision_time)
    signals.append(
        _snapshot(
            run_id,
            "EXECUTION_DATA_QUALITY",
            "decision_bar_completeness",
            "15m",
            decision_time - timedelta(minutes=15),
            decision_time,
            (
                (
                    "source_minutes",
                    None if decision_bar is None else float(decision_bar.source_minutes),
                ),
            ),
            "READY" if decision_bar is not None and decision_bar.complete else "NOT_READY",
            "COMPLETE" if decision_bar is not None and decision_bar.complete else "INCOMPLETE",
        )
    )
    return tuple(signals)


def data_ready(view: CausalView, decision_time: datetime) -> tuple[bool, str | None]:
    """Mandatory data: a complete 15m decision bar and a completed 4h context bar."""
    decision_bar = view.bar_closing_at("15m", decision_time)
    if decision_bar is None or not decision_bar.complete:
        return False, "DECISION_BAR_INCOMPLETE_OR_MISSING"
    if view.last("4h") is None:
        return False, "WARMUP_4H_CONTEXT_UNAVAILABLE"
    return True, None
