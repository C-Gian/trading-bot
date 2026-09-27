"""Causal 1m substrate and completed-bar aggregation for G2 (contract section 2).

A 1m kline `[t, t+1m)` becomes available only at `t+1m`. Higher-timeframe bars (3m for the 45m
cycle scale, 15m, 1h, 4h, Daily and Weekly UTC) are emitted only once their UTC window has closed.
A window that closed with missing source minutes is emitted as incomplete and must be refused by
every consumer; a window with no source minute at all emits nothing, so the gap is visible as a
discontinuity. No consumer can read an incomplete or future bar.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from app.g1.bars import window_end, window_start

from .contract import MINUTE

HTF = ("3m", "15m", "1h", "4h", "1d", "1w")
STEP = {
    "3m": timedelta(minutes=3),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
    "1w": timedelta(days=7),
}


class FutureObservationError(LookupError):
    """A consumer asked for an observation that is not available at the cursor."""


@dataclass(frozen=True, slots=True)
class Minute:
    """One official USD-M 1m kline (float research representation)."""

    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float | None
    taker_buy_base_volume: float | None

    @property
    def available_at(self) -> datetime:
        return self.open_time + MINUTE


def valid_minute(bar: Minute) -> bool:
    values = (bar.open, bar.high, bar.low, bar.close, bar.volume)
    if not all(math.isfinite(v) for v in values):
        return False
    return 0 < bar.low <= min(bar.open, bar.close) <= max(bar.open, bar.close) <= bar.high


@dataclass(frozen=True, slots=True)
class Bar:
    timeframe: str
    open_time: datetime
    close_time: datetime  # == available_at
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float | None
    taker_buy_base_volume: float | None
    source_minutes: int
    expected_minutes: int

    @property
    def complete(self) -> bool:
        return self.source_minutes == self.expected_minutes

    @property
    def available_at(self) -> datetime:
        return self.close_time


class _Partial:
    __slots__ = (
        "close",
        "count",
        "end",
        "high",
        "low",
        "open",
        "quote",
        "start",
        "taker",
        "tf",
        "volume",
    )

    def __init__(self, tf: str, start: datetime) -> None:
        self.tf = tf
        self.start = start
        self.end = window_end(tf, start)
        self.count = 0
        self.open = self.high = self.low = self.close = 0.0
        self.volume = 0.0
        self.quote: float | None = 0.0
        self.taker: float | None = 0.0

    def add(self, bar: Minute) -> None:
        if self.count == 0:
            self.open, self.high, self.low = bar.open, bar.high, bar.low
        else:
            self.high = max(self.high, bar.high)
            self.low = min(self.low, bar.low)
        self.close = bar.close
        self.volume += bar.volume
        self.quote = (
            None
            if self.quote is None or bar.quote_volume is None
            else self.quote + bar.quote_volume
        )
        self.taker = (
            None
            if self.taker is None or bar.taker_buy_base_volume is None
            else self.taker + bar.taker_buy_base_volume
        )
        self.count += 1

    def build(self) -> Bar:
        expected = int((self.end - self.start).total_seconds() // 60)
        return Bar(
            self.tf,
            self.start,
            self.end,
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
            self.quote,
            self.taker,
            self.count,
            expected,
        )


class Aggregator:
    """Incremental completed-bar aggregation driven by the advancing cursor."""

    def __init__(self, timeframes: tuple[str, ...] = HTF) -> None:
        self.timeframes = timeframes
        self._partial: dict[str, _Partial | None] = dict.fromkeys(timeframes)
        self._last: datetime | None = None

    def add(self, bar: Minute) -> list[Bar]:
        """Ingest one available minute; returns bars whose window closed before it."""
        if self._last is not None and bar.open_time <= self._last:
            raise ValueError("source minutes must arrive in strictly increasing order")
        self._last = bar.open_time
        emitted = self.close_until(bar.open_time)
        for tf in self.timeframes:
            partial = self._partial[tf]
            if partial is None:
                partial = _Partial(tf, window_start(tf, bar.open_time))
                self._partial[tf] = partial
            partial.add(bar)
        return emitted

    def close_until(self, moment: datetime) -> list[Bar]:
        """Emit every partial window whose end is at or before `moment`."""
        closed: list[Bar] = []
        for tf in self.timeframes:
            partial = self._partial[tf]
            if partial is not None and partial.end <= moment:
                closed.append(partial.build())
                self._partial[tf] = None
        return closed


class MinuteTape:
    """Minute-indexed arrays of the ingested 1m source, readable only up to the cursor.

    Missing minutes stay NaN / absent; nothing is forward-filled.
    """

    def __init__(self, start: datetime, minutes: int) -> None:
        self.start = start
        self.size = minutes
        self.open = np.full(minutes, np.nan)
        self.high = np.full(minutes, np.nan)
        self.low = np.full(minutes, np.nan)
        self.close = np.full(minutes, np.nan)
        self.present = np.zeros(minutes, dtype=bool)
        self.available_until = 0  # exclusive index: minutes with close <= cursor

    def index(self, open_time: datetime) -> int:
        return int((open_time - self.start) // MINUTE)

    def put(self, bar: Minute) -> None:
        i = self.index(bar.open_time)
        if not 0 <= i < self.size:
            raise ValueError("minute outside the registered run window")
        self.open[i], self.high[i], self.low[i], self.close[i] = (
            bar.open,
            bar.high,
            bar.low,
            bar.close,
        )
        self.present[i] = True

    def advance(self, cursor: datetime) -> None:
        self.available_until = max(self.available_until, min(self.size, self.index(cursor)))

    def require(self, stop: int) -> None:
        if stop > self.available_until:
            raise FutureObservationError("minute tape read beyond the causal cursor")

    def minute(self, open_time: datetime) -> tuple[float, float, float, float] | None:
        i = self.index(open_time)
        if i < 0 or i >= self.size:
            return None
        self.require(i + 1)
        if not self.present[i]:
            return None
        return float(self.open[i]), float(self.high[i]), float(self.low[i]), float(self.close[i])

    def window(self, first: datetime, last: datetime) -> slice:
        """The index slice of minutes opening in [first, last]; causally checked."""
        i0, i1 = self.index(first), self.index(last) + 1
        if i0 < 0 or i1 > self.size:
            raise ValueError("window outside the registered run")
        self.require(i1)
        return slice(i0, i1)


def completed_bars(minutes: list[Minute], timeframe: str) -> list[Bar]:
    """Batch reference aggregation (tests/parity): every closed window of `timeframe`."""
    aggregator = Aggregator((timeframe,))
    bars: list[Bar] = []
    for bar in minutes:
        bars.extend(aggregator.add(bar))
    if minutes:
        bars.extend(aggregator.close_until(minutes[-1].available_at))
    return bars
