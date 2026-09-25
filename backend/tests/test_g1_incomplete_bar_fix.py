"""ADR-0047: incomplete 15m/1h/4h/1d bars reset recursive indicator state and are never consumed.

For ATR, hourly EMA structure, ADX/DI and daily EMA context separately: two histories identical
before an incomplete bar whose OHLC differs radically must publish UNAVAILABLE at that bar, produce
identical later state, match a fresh indicator fed only the later complete bars, and show no READY
reading before the frozen warm-up is satisfied again. An integration run proves the same for P1/P2
decisions.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from app.g1 import dev_fixtures
from app.g1.bars import MINUTE, Bar, minute_bar
from app.g1.development import DevelopmentEngine, development_manifest, drive, primary_book
from app.g1.indicators import UNAVAILABLE, DailyContext, HourStructure, WilderAdx, WilderAtr

T0 = datetime(2001, 3, 5, tzinfo=UTC)
K = 60  # index of the incomplete bar
AFTER = 60  # complete bars after it


def bar(tf: str, minutes: int, index: int, price: float, complete: bool = True) -> Bar:
    step = timedelta(minutes=minutes)
    opened = T0 + index * step
    wiggle = 2 + (index * 7) % 5
    o, c = price, price + (1 if index % 3 else -1.5)
    return Bar(
        tf,
        opened,
        opened + step,
        opened + step,
        Decimal(repr(o)),
        Decimal(repr(max(o, c) + wiggle)),
        Decimal(repr(min(o, c) - wiggle)),
        Decimal(repr(c)),
        Decimal(10),
        minutes if complete else minutes - 1,
        minutes,
        "COMPLETE" if complete else "INCOMPLETE",
    )


def history(tf: str, minutes: int, poison: float) -> list[Bar]:
    rows = [bar(tf, minutes, i, 100 + 0.8 * i) for i in range(K)]
    rows.append(bar(tf, minutes, K, poison, complete=False))
    rows += [
        bar(tf, minutes, K + 1 + i, 100 + 0.8 * (K + 1 + i) - 3 * (i % 4)) for i in range(AFTER)
    ]
    return rows


def snapshot(reading: Any) -> tuple:
    return (reading.state, reading.available_at, reading.values)


# (name, timeframe, minutes, factory, reader, frozen warm-up in complete bars after the reset)
CASES: list[tuple[str, str, int, Callable[[], Any], Callable[[Any, Bar], Any], int]] = [
    ("atr_15m", "15m", 15, WilderAtr, lambda ind, b: ind.update(b), 14),
    ("ema_1h", "1h", 60, HourStructure, lambda ind, b: ind.update(b), 50),
    ("adx_4h", "4h", 240, WilderAdx, lambda ind, b: ind.update(b), 28),
]


@pytest.mark.parametrize(
    ("name", "tf", "minutes", "factory", "read", "warmup"), CASES, ids=[c[0] for c in CASES]
)
def test_incomplete_bar_resets_and_never_contaminates(
    name, tf, minutes, factory, read, warmup
) -> None:
    runs = []
    for poison in (100 + 0.8 * K, 1e6):  # radically different partial OHLC
        indicator = factory()
        runs.append([snapshot(read(indicator, b)) for b in history(tf, minutes, poison)])
    first, second = runs
    assert first[:K] == second[:K]
    assert first[K][0] == second[K][0] == UNAVAILABLE
    assert first[K + 1 :] == second[K + 1 :]
    fresh = factory()
    tail = history(tf, minutes, 0)[K + 1 :]
    assert [snapshot(read(fresh, b)) for b in tail] == first[K + 1 :]
    after = [state for state, _, _ in first[K + 1 :]]
    assert all(state == UNAVAILABLE for state in after[: warmup - 1])
    assert after[warmup - 1] != UNAVAILABLE
    assert first[K - 1][0] != UNAVAILABLE  # it was READY before the incomplete bar


def test_daily_context_incomplete_day_resets_ema_and_boundary() -> None:
    runs = []
    for poison in (100 + 0.8 * K, 1e6):
        daily = DailyContext()
        rows = []
        for b in history("1d", 1440, poison):
            daily.update(b)
            rows.append(
                (
                    snapshot(daily.direction),
                    snapshot(daily.boundary),
                    tuple(daily.history),
                    daily.ema.value,
                )
            )
        runs.append(rows)
    first, second = runs
    assert first[:K] == second[:K] and first[K + 1 :] == second[K + 1 :]
    direction, boundary, lookback, ema = first[K]
    assert direction[0] == boundary[0] == UNAVAILABLE and lookback == () and ema is None
    assert first[K + 1][1][0] == "READY"  # next complete day's own boundary is known
    states = [row[0][0] for row in first[K + 1 :]]
    assert all(state == UNAVAILABLE for state in states[:22]) and states[22] != UNAVAILABLE
    fresh = DailyContext()
    for b in history("1d", 1440, 0)[K + 1 :]:
        fresh.update(b)
    assert (fresh.ema.value, tuple(fresh.history)) == (first[-1][3], first[-1][2])
    assert first[K - 1][0][0] != UNAVAILABLE


@pytest.mark.parametrize(
    ("tf", "minutes", "factory"),
    [("15m", 15, WilderAtr), ("1h", 60, HourStructure), ("4h", 240, WilderAdx)],
)
def test_whole_bar_gap_still_resets(tf, minutes, factory) -> None:
    rows = [bar(tf, minutes, i, 100 + 0.8 * i) for i in range(K)]
    later = [bar(tf, minutes, K + 5 + i, 150 + 0.5 * i) for i in range(AFTER)]
    gapped, fresh = factory(), factory()
    for b in rows:
        gapped.update(b)
    assert [snapshot(gapped.update(b)) for b in later] == [snapshot(fresh.update(b)) for b in later]


# ------------------------------------------------------------------ integration
WINDOW = datetime(2000, 12, 2, 13, 0, tzinfo=UTC)  # a 15m window inside the synthetic path
REMOVED = {0, 3, 6, 9, 14}  # one minute per 3m sub-bar, including the terminal minute


def variant(bars: tuple[Bar, ...], poison: bool) -> tuple[Bar, ...]:
    out = []
    for b in bars:
        offset = int((b.open_time - WINDOW) / MINUTE)
        if 0 <= offset < 15:
            if offset in REMOVED:
                continue
            if poison:
                scale = Decimal("1.5") if offset % 2 else Decimal("0.55")
                o, c = b.open * scale, b.close * scale
                b = minute_bar(
                    b.open_time,
                    o,
                    max(o, c) * Decimal("1.01"),
                    min(o, c) * Decimal("0.99"),
                    c,
                    b.volume * 50,
                    (b.quote_volume or Decimal(0)) * 50,
                    b.volume * 49,
                )
        out.append(b)
    return tuple(out)


def run(bars: tuple[Bar, ...]) -> DevelopmentEngine:
    start, end = dev_fixtures.START, dev_fixtures.END
    books = (primary_book("S0", start, end), primary_book("S_FULL", start, end))
    manifest = development_manifest(
        (("synthetic", "incomplete-bar-fix"),),
        start,
        end,
        books,
        "SYNTHETIC_FIXTURE_NOT_MARKET_EVIDENCE",
        "t",
    )
    engine = DevelopmentEngine(
        manifest, books, dev_fixtures.synthetic_funding(), display_book="S0:PRIMARY"
    )
    return drive(engine, bars)


def test_incomplete_higher_timeframe_bars_cannot_change_later_p1_p2_decisions() -> None:
    base = dev_fixtures.synthetic_path()
    clean, poisoned = run(variant(base, False)), run(variant(base, True))
    s0 = clean.books["S0:PRIMARY"].ledger.trades
    assert not any(t.entry_time <= WINDOW + 15 * MINUTE and t.exit_time >= WINDOW for t in s0)
    later = [t for t in s0 if t.entry_time > WINDOW + timedelta(days=24)]
    assert later, "the fixture must contain trades after every indicator has re-warmed"
    for book in clean.books:
        assert clean.books[book].ledger.trades == poisoned.books[book].ledger.trades
        assert clean.books[book].ledger.events == poisoned.books[book].ledger.events
    assert clean.forecasts == poisoned.forecasts
    from app.g1.records import DecisionSnapshot, MarketState

    assert clean.store.of_type(DecisionSnapshot) == poisoned.store.of_type(DecisionSnapshot)
    assert clean.store.of_type(MarketState) == poisoned.store.of_type(MarketState)
