"""Deterministic UTC completed-bar aggregation with explicit availability (contract section 1).

A completed bar with interval `[t0, t1)` is available no earlier than `t1`. Higher-timeframe bars
are built incrementally from 1m source events and become visible only once their UTC window has
closed. A window that closed with missing source minutes is emitted as `INCOMPLETE`, never as a
complete bar, so consumers can refuse it.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import islice

MINUTE = timedelta(minutes=1)
TIMEFRAMES = ("1m", "3m", "15m", "1h", "4h", "1d", "1w", "1M")
FIXED_MINUTES = {"1m": 1, "3m": 3, "15m": 15, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
EPOCH_MONDAY = datetime(1970, 1, 5, tzinfo=UTC)
RETENTION = 4096


class FutureObservationError(LookupError):
    """A consumer asked for an observation that is not yet available at the replay cursor."""


@dataclass(frozen=True)
class Bar:
    timeframe: str
    open_time: datetime
    close_time: datetime
    available_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    source_minutes: int
    expected_minutes: int
    quality: str
    # Exchange-reported kline fields (None when a constituent minute lacks them; never imputed).
    quote_volume: Decimal | None = None
    taker_buy_base_volume: Decimal | None = None

    @property
    def complete(self) -> bool:
        return self.quality == "COMPLETE"


def minute_bar(
    open_time: datetime,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal = Decimal(1),
    quote_volume: Decimal | None = None,
    taker_buy_base_volume: Decimal | None = None,
) -> Bar:
    if open_time.tzinfo is None or open_time.second or open_time.microsecond:
        raise ValueError("1m source events must be UTC minute boundaries")
    if not low <= min(open_, close) <= max(open_, close) <= high:
        raise ValueError("inconsistent OHLC")
    close_time = open_time + MINUTE
    return Bar(
        "1m",
        open_time,
        close_time,
        close_time,
        open_,
        high,
        low,
        close,
        volume,
        1,
        1,
        "COMPLETE",
        quote_volume,
        taker_buy_base_volume,
    )


def window_start(timeframe: str, moment: datetime) -> datetime:
    """The UTC start of the window containing `moment`."""
    moment = moment.astimezone(UTC)
    if timeframe == "1M":
        return moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if timeframe == "1w":
        days = (moment - EPOCH_MONDAY).days
        return EPOCH_MONDAY + timedelta(days=days - days % 7)
    minutes = FIXED_MINUTES[timeframe]
    day = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    offset = int((moment - day).total_seconds() // 60)
    return day + timedelta(minutes=offset - offset % minutes)


def window_end(timeframe: str, start: datetime) -> datetime:
    if timeframe == "1M":
        year, month = (start.year + 1, 1) if start.month == 12 else (start.year, start.month + 1)
        return start.replace(year=year, month=month)
    return start + timedelta(minutes=FIXED_MINUTES[timeframe])


class _Partial:
    """Incremental OHLCV accumulation for one open window (O(1) memory per timeframe)."""

    def __init__(self, timeframe: str, start: datetime) -> None:
        self.timeframe = timeframe
        self.start = start
        self.end = window_end(timeframe, start)
        self.count = 0
        self.open = self.high = self.low = self.close = Decimal(0)
        self.volume = Decimal(0)
        self.quote: Decimal | None = Decimal(0)
        self.taker: Decimal | None = Decimal(0)

    def add(self, bar: Bar) -> None:
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
            else (self.quote + bar.quote_volume)
        )
        self.taker = (
            None
            if self.taker is None or bar.taker_buy_base_volume is None
            else (self.taker + bar.taker_buy_base_volume)
        )
        self.count += 1

    def build(self) -> Bar:
        expected = int((self.end - self.start).total_seconds() // 60)
        return Bar(
            self.timeframe,
            self.start,
            self.end,
            self.end,
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
            self.count,
            expected,
            "COMPLETE" if self.count == expected else "INCOMPLETE",
            self.quote,
            self.taker,
        )


class Aggregator:
    """Incremental completed-bar aggregation driven only by the advancing cursor.

    `advance(cursor, new_minutes)` ingests 1m bars whose availability is `<= cursor` and returns
    every higher-timeframe bar whose window has closed at or before the cursor. A window with no
    source minute at all produces no bar (the gap is visible as a missing bar).
    """

    def __init__(self, timeframes: tuple[str, ...] = TIMEFRAMES) -> None:
        self.timeframes = tuple(tf for tf in timeframes if tf != "1m")
        self._partial: dict[str, _Partial | None] = dict.fromkeys(self.timeframes)
        self._last_minute: datetime | None = None

    def advance(self, cursor: datetime, new_minutes: tuple[Bar, ...] = ()) -> list[Bar]:
        emitted: list[Bar] = []
        for bar in new_minutes:
            if bar.available_at > cursor:
                raise FutureObservationError("a source minute is not yet available")
            if self._last_minute is not None and bar.open_time <= self._last_minute:
                raise ValueError("source minutes must arrive in strictly increasing order")
            self._last_minute = bar.open_time
            emitted.extend(self._close_before(bar.open_time))
            emitted.append(bar)
            for timeframe in self.timeframes:
                partial = self._partial[timeframe]
                if partial is None:
                    partial = _Partial(timeframe, window_start(timeframe, bar.open_time))
                    self._partial[timeframe] = partial
                partial.add(bar)
        emitted.extend(self._close_before(cursor))
        return emitted

    def _close_before(self, moment: datetime) -> list[Bar]:
        closed: list[Bar] = []
        for timeframe in self.timeframes:
            partial = self._partial[timeframe]
            if partial is not None and partial.end <= moment:
                closed.append(partial.build())
                self._partial[timeframe] = None
        return closed


class CausalView:
    """Everything an algorithm may see at the cursor: bars with `available_at <= cursor`."""

    def __init__(self, retention: int = RETENTION) -> None:
        # Bounded causal history per timeframe: long historical runs keep O(1) memory. Every
        # consumer reads at most the trailing window it needs (the longest is one UTC day of 1m).
        self.cursor: datetime | None = None
        self._bars: dict[str, deque[Bar]] = {
            tf: deque(maxlen=max(retention, 2 * 1440) if tf == "1m" else retention)
            for tf in TIMEFRAMES
        }

    def move_to(self, cursor: datetime, new_bars: list[Bar]) -> None:
        if self.cursor is not None and cursor < self.cursor:
            raise ValueError("the virtual cursor never moves backwards")
        for bar in new_bars:
            if bar.available_at > cursor:
                raise FutureObservationError(f"{bar.timeframe} bar at {bar.open_time} is future")
            self._bars[bar.timeframe].append(bar)
        self.cursor = cursor

    def _require(self, moment: datetime) -> None:
        if self.cursor is None or moment > self.cursor:
            raise FutureObservationError(f"{moment} is after the replay cursor {self.cursor}")

    def bars(self, timeframe: str, count: int | None = None) -> tuple[Bar, ...]:
        rows = self._bars[timeframe]
        if count is None or count >= len(rows):
            return tuple(rows)
        return tuple(islice(rows, len(rows) - count, None))

    def last(self, timeframe: str) -> Bar | None:
        rows = self._bars[timeframe]
        return rows[-1] if rows else None

    def bar_closing_at(self, timeframe: str, close_time: datetime) -> Bar | None:
        """The bar of `timeframe` ending exactly at `close_time`; future requests are refused."""
        self._require(close_time)
        for bar in reversed(self._bars[timeframe]):
            if bar.close_time == close_time:
                return bar
            if bar.close_time < close_time:
                return None
        return None

    def minute_at(self, open_time: datetime) -> Bar | None:
        return self.bar_closing_at("1m", open_time + MINUTE)
