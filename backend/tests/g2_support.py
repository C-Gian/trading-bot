"""Shared deterministic helpers for the G2-01 acceptance tests (synthetic only)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import cache

from app.g2 import fixtures, runs
from app.g2.bars import Bar, Minute
from app.g2.service import ComputedRun, G2ReplayService

T0 = datetime(2001, 1, 1, tzinfo=UTC)
MINUTE = timedelta(minutes=1)


def minute(
    t: datetime,
    o: float,
    h: float,
    low: float,
    c: float,
    v: float = 10.0,
    taker: float | None = 5.0,
    quote: float | None = None,
) -> Minute:
    return Minute(t, o, h, low, c, v, v * c if quote is None else quote, taker)


def flat_minutes(start: datetime, count: int, price: float = 100.0) -> list[Minute]:
    return [minute(start + i * MINUTE, price, price, price, price) for i in range(count)]


def bar(
    tf: str,
    open_time: datetime,
    o: float,
    h: float,
    low: float,
    c: float,
    volume: float = 10.0,
    quote: float | None = 1000.0,
    taker: float | None = 5.0,
    complete: bool = True,
) -> Bar:
    from app.g2.bars import STEP

    expected = int(STEP[tf].total_seconds() // 60)
    return Bar(
        tf,
        open_time,
        open_time + STEP[tf],
        o,
        h,
        low,
        c,
        volume,
        quote,
        taker,
        expected if complete else expected - 1,
        expected,
    )


def short_spec(days: int = 21) -> runs.RunSpec:
    """A short synthetic path (no model can fit): causality/replay/prefix checks."""
    end = fixtures.START + timedelta(days=days)
    return runs.RunSpec(
        f"G2-SYN-SHORT-{days}D",
        "Short synthetic path — NOT PERFORMANCE EVIDENCE",
        runs.SYNTHETIC,
        fixtures.START,
        end,
        lambda: fixtures.synthetic_minutes(days=days),
        lambda: fixtures.synthetic_funding(days=days),
        fixtures.SYNTHETIC_FILTERS,
        lambda run_id: (),
        "short synthetic",
    )


@cache
def short_built(days: int = 21) -> runs.BuiltRun:
    return runs.build(short_spec(days))


@cache
def shared_service() -> G2ReplayService:
    """One process-wide service, so the full synthetic run is computed once per test session."""
    return G2ReplayService(include_engineering_window=False)


def full_run() -> ComputedRun:
    return shared_service().computed(runs.synthetic_spec().key)
