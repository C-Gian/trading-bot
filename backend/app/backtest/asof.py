from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .models import Bar


def _contiguous_suffix(
    bars: tuple[Bar, ...], signal_time: datetime, width: timedelta
) -> tuple[Bar, ...]:
    ordered = tuple(sorted(bars, key=lambda bar: bar.open_time))
    if len({bar.open_time for bar in ordered}) != len(ordered):
        raise ValueError("duplicate bar timestamp")
    minutes = int(width.total_seconds() / 60)
    for bar in ordered:
        if (
            bar.open_time.tzinfo is None
            or bar.open_time.astimezone(UTC) != bar.open_time
            or bar.open_time.second
            or bar.open_time.microsecond
        ):
            raise ValueError("bars must use aligned UTC timestamps")
        if (minutes < 60 and bar.open_time.minute % minutes) or (
            minutes >= 60 and bar.open_time.minute
        ):
            raise ValueError("bar is not timeframe aligned")
        if minutes >= 60 and bar.open_time.hour % (minutes // 60):
            raise ValueError("bar is not timeframe aligned")
    eligible = tuple(bar for bar in ordered if bar.open_time + width <= signal_time)
    suffix = []
    expected = None
    for bar in reversed(eligible):
        if not bar.complete or (expected is not None and bar.open_time + width != expected):
            break
        suffix.append(bar)
        expected = bar.open_time
    return tuple(reversed(suffix))


@dataclass(frozen=True)
class AsOfView:
    signal_time: datetime
    signal_bars_1h: tuple[Bar, ...]
    context_bars_4h: tuple[Bar, ...]

    @classmethod
    def build(
        cls,
        signal_time: datetime,
        bars_1h: tuple[Bar, ...],
        bars_4h: tuple[Bar, ...],
    ):
        if signal_time.tzinfo is None:
            raise ValueError("signal time must be timezone-aware")
        instant = signal_time.astimezone(UTC)
        return cls(
            instant,
            _contiguous_suffix(bars_1h, instant, timedelta(hours=1)),
            _contiguous_suffix(bars_4h, instant, timedelta(hours=4)),
        )

    def require_1h(self, count: int) -> tuple[Bar, ...]:
        if (
            count <= 0
            or len(self.signal_bars_1h) < count
            or self.signal_bars_1h[-1].open_time + timedelta(hours=1) != self.signal_time
        ):
            raise ValueError("contiguous 1h lookback unavailable")
        return self.signal_bars_1h[-count:]

    def require_4h(self, count: int) -> tuple[Bar, ...]:
        age = (
            self.signal_time - (self.context_bars_4h[-1].open_time + timedelta(hours=4))
            if self.context_bars_4h
            else None
        )
        if (
            count <= 0
            or len(self.context_bars_4h) < count
            or age is None
            or not timedelta(0) <= age < timedelta(hours=4)
        ):
            raise ValueError("contiguous 4h context unavailable")
        return self.context_bars_4h[-count:]
