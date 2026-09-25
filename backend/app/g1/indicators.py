"""Frozen System G1 Development V1 shared technical state (protocol sections 4-5).

Deterministic streaming implementations of exactly the protocol definitions — no alternative
period, threshold or fallback:

- 4h Wilder ADX/+DI/-DI(14): TREND_BULL (ADX >= 25, +DI > -DI), TREND_BEAR (ADX >= 25,
  -DI > +DI), RANGE (ADX <= 20), otherwise TRANSITION;
- 1h EMA20/EMA50 structure: BULLISH (EMA20 > EMA50 and close > EMA20), BEARISH (symmetric),
  otherwise NEUTRAL;
- 15m Wilder ATR(14);
- current UTC-session VWAP = cumulative quote volume / cumulative base volume;
- previous completed UTC-day high/low;
- daily EMA20 corroboration: DAILY_BULL (close > EMA20 and EMA20 > EMA20 three completed days
  earlier), DAILY_BEAR (symmetric), otherwise DAILY_NEUTRAL;
- 15m RVOL = base volume / median(base volume of the previous 20 completed 15m candles),
  support iff RVOL >= 1.20, trigger candle excluded from the baseline;
- taker imbalance = (2 * taker-buy base - base) / base; LONG needs > 0, SHORT needs < 0.

Missing-data semantics (implementation of "readiness and missing-data semantics"):

- every indicator consumes completed UTC bars only; each output carries the bar's `available_at`;
- a whole missing bar (time gap) resets that recursive indicator, which then re-warms normally;
- an INCOMPLETE bar (some constituent minutes missing) also resets that recursive indicator
  (15m ATR, 1h EMA20/EMA50, 4h ADX/DI, daily EMA20 + lookback), is never consumed (its partial
  OHLC/close cannot contaminate later state) and publishes UNAVAILABLE; subsequent complete bars
  re-warm normally (ADR-0047);
- session VWAP is unavailable if any minute of the current UTC session is missing, lacks quote
  volume, or the cumulative base volume is not positive;
- previous-day boundaries are unavailable unless the previous UTC day bar is COMPLETE;
- RVOL requires the trigger candle and the previous 20 contiguous candles to be COMPLETE, and a
  positive median; taker imbalance requires the exchange field and positive base volume.

EMA seeding: the first value is the simple mean of the first `n` closes (standard recursive EMA
with alpha = 2 / (n + 1) thereafter). Wilder smoothing: first TR/DM sums over 14 bars, first ADX is
the mean of the first 14 DX values.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import median

from .bars import FIXED_MINUTES, Bar

ADX_PERIOD = 14
ADX_TREND = 25.0
ADX_RANGE = 20.0
EMA_FAST = 20
EMA_SLOW = 50
ATR_PERIOD = 14
DAILY_EMA = 20
DAILY_LOOKBACK = 3
RVOL_BASELINE = 20
RVOL_MIN = 1.20

TREND_BULL, TREND_BEAR, RANGE, TRANSITION = "TREND_BULL", "TREND_BEAR", "RANGE", "TRANSITION"
BULLISH, BEARISH, NEUTRAL = "BULLISH", "BEARISH", "NEUTRAL"
DAILY_BULL, DAILY_BEAR, DAILY_NEUTRAL = "DAILY_BULL", "DAILY_BEAR", "DAILY_NEUTRAL"
UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class Reading:
    """One indicator output with its causal availability."""

    state: str
    available_at: datetime | None
    values: tuple[tuple[str, float | None], ...] = ()

    def value(self, name: str) -> float | None:
        return dict(self.values).get(name)


class _Contiguous:
    """Shared gap/incomplete detection for one timeframe."""

    def __init__(self, timeframe: str) -> None:
        self.step = timedelta(minutes=FIXED_MINUTES[timeframe])
        self.last_open: datetime | None = None

    def breaks(self, bar: Bar) -> bool:
        """True when at least one whole bar is missing before `bar` (a time gap)."""
        broken = self.last_open is not None and bar.open_time != self.last_open + self.step
        self.last_open = bar.open_time
        return broken


class Ema:
    def __init__(self, period: int) -> None:
        self.period = period
        self.reset()

    def reset(self) -> None:
        self.seed: list[float] = []
        self.value: float | None = None

    def update(self, x: float) -> float | None:
        if self.value is None:
            self.seed.append(x)
            if len(self.seed) == self.period:
                self.value = sum(self.seed) / self.period
            return self.value
        alpha = 2.0 / (self.period + 1)
        self.value = alpha * x + (1 - alpha) * self.value
        return self.value


class WilderAdx:
    """Wilder ADX/+DI/-DI(14) on completed 4h bars."""

    def __init__(self) -> None:
        self.gap = _Contiguous("4h")
        self.reset()
        self.reading = Reading(UNAVAILABLE, None)

    def reset(self) -> None:
        self.previous: Bar | None = None
        self.samples: list[tuple[float, float, float]] = []
        self.tr = self.pdm = self.mdm = 0.0
        self.smoothed = False
        self.dx: list[float] = []
        self.adx: float | None = None

    def update(self, bar: Bar) -> Reading:
        if self.gap.breaks(bar) or not bar.complete:
            self.reset()
        if not bar.complete:
            self.reading = Reading(UNAVAILABLE, bar.available_at)
            return self.reading
        high, low = float(bar.high), float(bar.low)
        previous = self.previous
        self.previous = bar
        if previous is None:
            self.reading = Reading(UNAVAILABLE, bar.available_at)
            return self.reading
        p_high, p_low, p_close = float(previous.high), float(previous.low), float(previous.close)
        tr = max(high - low, abs(high - p_close), abs(low - p_close))
        up, down = high - p_high, p_low - low
        pdm = up if up > down and up > 0 else 0.0
        mdm = down if down > up and down > 0 else 0.0
        n = ADX_PERIOD
        if not self.smoothed:
            self.samples.append((tr, pdm, mdm))
            if len(self.samples) < n:
                self.reading = Reading(UNAVAILABLE, bar.available_at)
                return self.reading
            self.tr = sum(s[0] for s in self.samples)
            self.pdm = sum(s[1] for s in self.samples)
            self.mdm = sum(s[2] for s in self.samples)
            self.smoothed = True
        else:
            self.tr = self.tr - self.tr / n + tr
            self.pdm = self.pdm - self.pdm / n + pdm
            self.mdm = self.mdm - self.mdm / n + mdm
        plus = 100 * self.pdm / self.tr if self.tr > 0 else 0.0
        minus = 100 * self.mdm / self.tr if self.tr > 0 else 0.0
        total = plus + minus
        dx = 100 * abs(plus - minus) / total if total > 0 else 0.0
        if self.adx is None:
            self.dx.append(dx)
            if len(self.dx) < n:
                self.reading = Reading(UNAVAILABLE, bar.available_at)
                return self.reading
            self.adx = sum(self.dx) / n
        else:
            self.adx = (self.adx * (n - 1) + dx) / n
        values = (("adx", self.adx), ("plus_di", plus), ("minus_di", minus))
        self.reading = Reading(regime(self.adx, plus, minus), bar.available_at, values)
        return self.reading


def regime(adx: float, plus: float, minus: float) -> str:
    if adx >= ADX_TREND and plus > minus:
        return TREND_BULL
    if adx >= ADX_TREND and minus > plus:
        return TREND_BEAR
    if adx <= ADX_RANGE:
        return RANGE
    return TRANSITION


class HourStructure:
    """1h EMA20/EMA50 structure on completed 1h closes."""

    def __init__(self) -> None:
        self.gap = _Contiguous("1h")
        self.fast, self.slow = Ema(EMA_FAST), Ema(EMA_SLOW)
        self.reading = Reading(UNAVAILABLE, None)

    def update(self, bar: Bar) -> Reading:
        if self.gap.breaks(bar) or not bar.complete:
            self.fast.reset()
            self.slow.reset()
        if not bar.complete:
            self.reading = Reading(UNAVAILABLE, bar.available_at)
            return self.reading
        close = float(bar.close)
        fast, slow = self.fast.update(close), self.slow.update(close)
        if fast is None or slow is None:
            values = (("ema20", fast), ("ema50", slow), ("close", close))
            self.reading = Reading(UNAVAILABLE, bar.available_at, values)
            return self.reading
        if fast > slow and close > fast:
            state = BULLISH
        elif fast < slow and close < fast:
            state = BEARISH
        else:
            state = NEUTRAL
        self.reading = Reading(
            state, bar.available_at, (("ema20", fast), ("ema50", slow), ("close", close))
        )
        return self.reading

    @property
    def ema20(self) -> float | None:
        return self.fast.value


class WilderAtr:
    """Wilder ATR(14) on completed 15m bars."""

    def __init__(self) -> None:
        self.gap = _Contiguous("15m")
        self.reset()
        self.reading = Reading(UNAVAILABLE, None)

    def reset(self) -> None:
        self.previous_close: float | None = None
        self.samples: list[float] = []
        self.atr: float | None = None

    def update(self, bar: Bar) -> Reading:
        if self.gap.breaks(bar) or not bar.complete:
            self.reset()
        if not bar.complete:
            self.reading = Reading(UNAVAILABLE, bar.available_at, (("atr", None),))
            return self.reading
        high, low, close = float(bar.high), float(bar.low), float(bar.close)
        if self.previous_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - self.previous_close), abs(low - self.previous_close))
        self.previous_close = close
        if self.atr is None:
            self.samples.append(tr)
            if len(self.samples) == ATR_PERIOD:
                self.atr = sum(self.samples) / ATR_PERIOD
        else:
            self.atr = (self.atr * (ATR_PERIOD - 1) + tr) / ATR_PERIOD
        valid = self.atr is not None and math.isfinite(self.atr) and self.atr > 0
        self.reading = Reading(
            "READY" if valid else UNAVAILABLE,
            bar.available_at,
            (("atr", self.atr if valid else None),),
        )
        return self.reading


class SessionVwap:
    """Current UTC-session VWAP from completed 1m bars (quote / base cumulative)."""

    def __init__(self) -> None:
        self.day: datetime | None = None
        self.quote = Decimal(0)
        self.base = Decimal(0)
        self.expected_next: datetime | None = None
        self.broken = False
        self.available_at: datetime | None = None

    def on_minute_boundary(self, minute_open: datetime, bar: Bar | None) -> None:
        """Called once per minute boundary, with `bar=None` for a missing minute."""
        day = minute_open.replace(hour=0, minute=0, second=0, microsecond=0)
        if day != self.day:
            self.day, self.quote, self.base, self.broken = day, Decimal(0), Decimal(0), False
        self.available_at = minute_open + timedelta(minutes=1)
        if bar is None or bar.quote_volume is None:
            self.broken = True
            return
        self.quote += bar.quote_volume
        self.base += bar.volume

    def reading(self) -> Reading:
        if self.day is None or self.broken or self.base <= 0:
            return Reading(UNAVAILABLE, self.available_at, (("vwap", None),))
        return Reading("READY", self.available_at, (("vwap", float(self.quote / self.base)),))


class DailyContext:
    """Previous completed UTC-day boundaries and daily EMA20 corroboration."""

    def __init__(self) -> None:
        self.gap = _Contiguous("1d")
        self.ema = Ema(DAILY_EMA)
        self.history: deque[float] = deque(maxlen=DAILY_LOOKBACK + 1)
        self.boundary = Reading(UNAVAILABLE, None)
        self.direction = Reading(UNAVAILABLE, None)

    def update(self, bar: Bar) -> None:
        if self.gap.breaks(bar) or not bar.complete:
            self.ema.reset()
            self.history.clear()
        if not bar.complete:
            self.boundary = Reading(UNAVAILABLE, bar.available_at)
            self.direction = Reading(UNAVAILABLE, bar.available_at)
            return
        close = float(bar.close)
        value = self.ema.update(close)
        if value is not None:
            self.history.append(value)
        self.boundary = Reading(
            "READY", bar.available_at, (("high", float(bar.high)), ("low", float(bar.low)))
        )
        if value is None or len(self.history) <= DAILY_LOOKBACK:
            self.direction = Reading(UNAVAILABLE, bar.available_at, (("ema20", value),))
            return
        earlier = self.history[0]
        if close > value > earlier:
            state = DAILY_BULL
        elif close < value < earlier:
            state = DAILY_BEAR
        else:
            state = DAILY_NEUTRAL
        self.direction = Reading(
            state,
            bar.available_at,
            (("ema20", value), ("ema20_3d_earlier", earlier), ("close", close)),
        )

    def boundary_for(self, decision_time: datetime) -> Reading:
        """Only the day that ended at the current UTC session start counts as 'previous day'."""
        session = (decision_time - timedelta(minutes=1)).replace(hour=0, minute=0)
        if self.boundary.available_at != session:
            return Reading(UNAVAILABLE, self.boundary.available_at)
        return self.boundary


class Participation:
    """RVOL and taker imbalance of the completed 15m trigger candle."""

    def __init__(self) -> None:
        self.gap = _Contiguous("15m")
        self.volumes: deque[tuple[float, bool]] = deque(maxlen=RVOL_BASELINE)
        self.reading = Reading(UNAVAILABLE, None)

    def update(self, bar: Bar) -> Reading:
        if self.gap.breaks(bar):
            self.volumes.clear()
        rvol = imbalance = None
        if (
            bar.complete
            and len(self.volumes) == RVOL_BASELINE
            and all(complete for _, complete in self.volumes)
        ):
            baseline = median(volume for volume, _ in self.volumes)
            if baseline > 0:
                rvol = float(bar.volume) / baseline
        if bar.complete and bar.taker_buy_base_volume is not None and bar.volume > 0:
            imbalance = float((2 * bar.taker_buy_base_volume - bar.volume) / bar.volume)
        self.volumes.append((float(bar.volume), bar.complete))
        values = (("rvol", rvol), ("imbalance", imbalance))
        self.reading = Reading(
            "READY" if rvol is not None and imbalance is not None else UNAVAILABLE,
            bar.available_at,
            values,
        )
        return self.reading

    def supports(self, side_sign: int) -> bool:
        rvol, imbalance = self.reading.value("rvol"), self.reading.value("imbalance")
        if rvol is None or imbalance is None:
            return False
        return rvol >= RVOL_MIN and side_sign * imbalance > 0


def log_return(end: Decimal, start: Decimal) -> float:
    return math.log(float(end) / float(start))
