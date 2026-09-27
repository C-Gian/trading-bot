"""Exact G2-V0 eight-column state (contract sections 3, 4, 11 and 20).

Every recursion consumes completed bars only. An incomplete bar or a discontinuity (a missing
window) invalidates the dependent recursive state, which then re-warms from the next valid bar; no
value is backfilled or forward-filled. A column whose inputs are missing is UNAVAILABLE — it never
becomes zero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from .bars import STEP, Bar
from .contract import (
    ATR_PERIOD,
    COLUMNS,
    CONTEXT_FAST_HL,
    CONTEXT_SLOW_HL,
    EPS,
    LOCAL_FAST_HL,
    LOCAL_SLOW_HL,
    PARTICIPATION_HL,
    VOL_FAST_HL,
    VOL_SLOW_HL,
    WARMUP_MULTIPLE,
)
from .records import Reason

AVAILABLE = "AVAILABLE"
WARMUP = "WARMUP"
MISSING = "MISSING_DATA"
INVALID = "INVALID"


def ewm_lambda(half_life: float) -> float:
    return float(2.0 ** (-1.0 / half_life))


class Ewm:
    """EWM_t = lambda * EWM_(t-1) + (1 - lambda) * x_t; the first observation initializes it."""

    __slots__ = ("count", "lam", "value")

    def __init__(self, half_life: float) -> None:
        self.lam = ewm_lambda(half_life)
        self.value: float | None = None
        self.count = 0

    def update(self, x: float) -> None:
        self.value = x if self.value is None else self.lam * self.value + (1 - self.lam) * x
        self.count += 1

    def reset(self) -> None:
        self.value = None
        self.count = 0


def eligible(ewm: Ewm, longest_half_life: int) -> bool:
    return ewm.value is not None and ewm.count >= WARMUP_MULTIPLE * longest_half_life


class Atr:
    """Wilder ATR14 on completed 1h bars: seed = mean of the first 14 TR, then recursion."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.prev_close: float | None = None
        self.seed: list[float] = []
        self.value: float | None = None

    def update(self, bar: Bar) -> None:
        if self.prev_close is not None:
            tr = max(
                bar.high - bar.low,
                abs(bar.high - self.prev_close),
                abs(bar.low - self.prev_close),
            )
            if self.value is None:
                self.seed.append(tr)
                if len(self.seed) == ATR_PERIOD:
                    self.value = sum(self.seed) / ATR_PERIOD
            else:
                self.value = ((ATR_PERIOD - 1) * self.value + tr) / ATR_PERIOD
        self.prev_close = bar.close


@dataclass(frozen=True)
class StateSnapshot:
    """The causal state at one decision instant (numbers only; records are built by the core)."""

    decision_time: datetime
    max_source_time: datetime | None
    price: float | None
    raw: tuple[float | None, ...]
    term_status: tuple[str, ...]
    price_response: float | None
    sigma_4h: float | None
    atr14: float | None
    ewm: tuple[tuple[str, float | None], ...]
    daily: tuple[tuple[str, float | str | None], ...]
    weekly: tuple[tuple[str, float | str | None], ...]
    reason: Reason | None  # None when every term and SIGMA_4H are available

    @property
    def available(self) -> bool:
        return self.reason is None


def _floor(moment: datetime, timeframe: str) -> datetime:
    from app.g1.bars import window_start

    return window_start(timeframe, moment)


def _display(bar: Bar | None) -> tuple[tuple[str, float | str | None], ...]:
    if bar is None:
        return (("status", "UNAVAILABLE"),)
    return (
        ("open_time", bar.open_time.isoformat().replace("+00:00", "Z")),
        ("complete", "COMPLETE" if bar.complete else "INCOMPLETE"),
        ("return", bar.close / bar.open - 1.0 if bar.open > 0 else None),
        ("high_low_range", bar.high - bar.low),
        ("range_fraction", (bar.high - bar.low) / bar.open if bar.open > 0 else None),
        ("close", bar.close),
    )


class FeatureEngine:
    """Consumes completed bars in close-time order; `snapshot(T)` reads the state at T."""

    def __init__(self) -> None:
        self.local_fast, self.local_slow = Ewm(LOCAL_FAST_HL), Ewm(LOCAL_SLOW_HL)
        self.context_fast, self.context_slow = Ewm(CONTEXT_FAST_HL), Ewm(CONTEXT_SLOW_HL)
        self.participation = Ewm(PARTICIPATION_HL)
        self.vol_fast, self.vol_slow = Ewm(VOL_FAST_HL), Ewm(VOL_SLOW_HL)
        self.atr = Atr()
        self.last: dict[str, Bar | None] = dict.fromkeys(("15m", "1h", "4h", "1d", "1w"))
        self._valid_close: dict[str, float | None] = dict.fromkeys(("15m", "1h", "4h"))
        self._last_open: dict[str, datetime | None] = dict.fromkeys(("15m", "1h", "4h"))
        # Values tied to the most recent completed 15m bar.
        self.r15: float | None = None
        self.baseline_pre: float | None = None
        self.baseline_pre_count = 0
        self.lq: float | None = None

    # ------------------------------------------------------------------ ingestion
    def on_bar(self, bar: Bar) -> None:
        tf = bar.timeframe
        if tf in ("1d", "1w"):
            self.last[tf] = bar
            return
        if tf not in ("15m", "1h", "4h"):
            return
        self.last[tf] = bar
        previous_open = self._last_open[tf]
        contiguous = previous_open is not None and bar.open_time == previous_open + STEP[tf]
        self._last_open[tf] = bar.open_time
        if not bar.complete:
            self._reset(tf)
            self._last_open[tf] = None
            return
        if not contiguous:
            self._reset(tf)
        getattr(self, f"_on_{tf}")(bar)

    def _reset(self, tf: str) -> None:
        self._valid_close[tf] = None
        if tf == "15m":
            self.participation.reset()
            self.vol_fast.reset()
            self.vol_slow.reset()
            self.r15 = self.baseline_pre = self.lq = None
            self.baseline_pre_count = 0
        elif tf == "1h":
            self.local_fast.reset()
            self.local_slow.reset()
            self.atr.reset()
        else:
            self.context_fast.reset()
            self.context_slow.reset()

    def _on_15m(self, bar: Bar) -> None:
        previous = self._valid_close["15m"]
        self.r15 = math.log(bar.close / previous) if previous is not None else None
        if self.r15 is not None:
            squared = self.r15 * self.r15
            self.vol_fast.update(squared)
            self.vol_slow.update(squared)
        self.baseline_pre = self.participation.value
        self.baseline_pre_count = self.participation.count
        if bar.quote_volume is not None and math.isfinite(bar.quote_volume):
            self.lq = math.log1p(bar.quote_volume)
            self.participation.update(self.lq)
        else:
            # Missing quote volume breaks the participation recursion (critical field).
            self.lq = None
            self.participation.reset()
        self._valid_close["15m"] = bar.close

    def _on_1h(self, bar: Bar) -> None:
        value = math.log(bar.close)
        self.local_fast.update(value)
        self.local_slow.update(value)
        self.atr.update(bar)
        self._valid_close["1h"] = bar.close

    def _on_4h(self, bar: Bar) -> None:
        value = math.log(bar.close)
        self.context_fast.update(value)
        self.context_slow.update(value)
        self._valid_close["4h"] = bar.close

    # ------------------------------------------------------------------ snapshot
    def _current(self, tf: str, decision: datetime) -> Bar | None:
        """The completed `tf` bar that must be the latest at `decision`, or None if stale."""
        bar = self.last[tf]
        expected_close = _floor(decision, tf)
        if bar is None or bar.close_time != expected_close:
            return None
        return bar

    def snapshot(self, decision: datetime) -> StateSnapshot:
        bar15, bar1h, bar4h = (self._current(tf, decision) for tf in ("15m", "1h", "4h"))
        consumed = [b.close_time for b in (bar15, bar1h, bar4h) if b is not None]
        for tf in ("1d", "1w"):
            display_bar = self.last[tf]
            if display_bar is not None:
                consumed.append(display_bar.close_time)
        max_source = max(consumed) if consumed else None
        if max_source is not None and max_source > decision:
            raise AssertionError("a state consumed a source later than its decision instant")

        status: dict[str, str] = {}
        raw: dict[str, float | None] = dict.fromkeys(COLUMNS)
        price: float | None = None
        decision_ok = bar15 is not None and bar15.complete
        if decision_ok:
            assert bar15 is not None
            price = bar15.close

        # 1h local structure and extension.
        h1_ok = bar1h is not None and bar1h.complete and self._valid_close["1h"] is not None
        local_ok = h1_ok and eligible(self.local_slow, LOCAL_SLOW_HL)
        local = (
            self.local_fast.value - self.local_slow.value  # type: ignore[operator]
            if local_ok
            else None
        )
        status["LOCAL_STRUCTURE"] = AVAILABLE if local_ok else (WARMUP if h1_ok else MISSING)
        raw["LOCAL_STRUCTURE"] = local
        extension_ok = h1_ok and decision_ok and eligible(self.local_fast, LOCAL_FAST_HL)
        raw["PRICE_EXTENSION"] = (
            math.log(price) - self.local_fast.value  # type: ignore[arg-type,operator]
            if extension_ok
            else None
        )
        status["PRICE_EXTENSION"] = (
            AVAILABLE if extension_ok else (WARMUP if h1_ok and decision_ok else MISSING)
        )

        # 4h context.
        h4_ok = bar4h is not None and bar4h.complete and self._valid_close["4h"] is not None
        context_ok = h4_ok and eligible(self.context_slow, CONTEXT_SLOW_HL)
        raw["CONTEXT_STRUCTURE"] = (
            self.context_fast.value - self.context_slow.value  # type: ignore[operator]
            if context_ok
            else None
        )
        status["CONTEXT_STRUCTURE"] = AVAILABLE if context_ok else (WARMUP if h4_ok else MISSING)

        # 15m participation, taker imbalance, volatility.
        participation_ok = (
            decision_ok
            and self.lq is not None
            and self.baseline_pre is not None
            and self.baseline_pre_count >= WARMUP_MULTIPLE * PARTICIPATION_HL
        )
        raw["RELATIVE_PARTICIPATION"] = (
            self.lq - self.baseline_pre  # type: ignore[operator]
            if participation_ok
            else None
        )
        status["RELATIVE_PARTICIPATION"] = (
            AVAILABLE
            if participation_ok
            else (WARMUP if decision_ok and self.lq is not None else MISSING)
        )
        taker: float | None = None
        if decision_ok:
            assert bar15 is not None
            buy, volume = bar15.taker_buy_base_volume, bar15.volume
            if buy is not None and math.isfinite(buy) and volume > 0 and math.isfinite(volume):
                taker = (2.0 * buy - volume) / volume
        raw["TAKER_IMBALANCE"] = taker
        status["TAKER_IMBALANCE"] = AVAILABLE if taker is not None else MISSING

        vol_ok = decision_ok and self.r15 is not None and eligible(self.vol_slow, VOL_SLOW_HL)
        sigma: float | None = None
        response: float | None = None
        if vol_ok:
            v_fast, v_slow = self.vol_fast.value, self.vol_slow.value
            assert v_fast is not None and v_slow is not None and self.r15 is not None
            raw["VOLATILITY_STATE"] = 0.5 * math.log(max(v_fast, EPS) / max(v_slow, EPS))
            status["VOLATILITY_STATE"] = AVAILABLE
            candidate = math.sqrt(16.0 * v_slow) if v_slow >= 0 else float("nan")
            sigma = candidate if math.isfinite(candidate) and candidate > 0 else None
            response = self.r15 / math.sqrt(max(v_slow, EPS))
        else:
            status["VOLATILITY_STATE"] = WARMUP if decision_ok else MISSING

        i1_parts = (raw["LOCAL_STRUCTURE"], raw["RELATIVE_PARTICIPATION"])
        raw["LOCAL_STRUCTURE_X_PARTICIPATION"] = (
            i1_parts[0] * i1_parts[1] if None not in i1_parts else None  # type: ignore[operator]
        )
        status["LOCAL_STRUCTURE_X_PARTICIPATION"] = _combine(
            status["LOCAL_STRUCTURE"], status["RELATIVE_PARTICIPATION"]
        )
        raw["IMBALANCE_X_PRICE_RESPONSE"] = (
            taker * response if taker is not None and response is not None else None
        )
        status["IMBALANCE_X_PRICE_RESPONSE"] = _combine(
            status["TAKER_IMBALANCE"],
            AVAILABLE if response is not None else status["VOLATILITY_STATE"],
        )

        term_status = tuple(status[c] for c in COLUMNS)
        if MISSING in term_status or not decision_ok:
            reason: Reason | None = Reason.FORECAST_UNAVAILABLE_MISSING_DATA
        elif WARMUP in term_status:
            reason = Reason.FORECAST_UNAVAILABLE_WARMUP
        elif sigma is None:
            reason = Reason.FORECAST_UNAVAILABLE_INVALID_SIGMA
        else:
            reason = None
        atr = self.atr.value if h1_ok else None
        ewm = (
            ("LOCAL_FAST", self.local_fast.value),
            ("LOCAL_SLOW", self.local_slow.value),
            ("CONTEXT_FAST", self.context_fast.value),
            ("CONTEXT_SLOW", self.context_slow.value),
            ("PARTICIPATION_BASELINE_PRE_T", self.baseline_pre),
            ("V_FAST", self.vol_fast.value),
            ("V_SLOW", self.vol_slow.value),
            ("R15_CURRENT", self.r15),
        )
        return StateSnapshot(
            decision,
            max_source,
            price,
            tuple(raw[c] for c in COLUMNS),
            term_status,
            response,
            sigma,
            atr,
            ewm,
            _display(self.last["1d"]),
            _display(self.last["1w"]),
            reason,
        )


def _combine(*states: str) -> str:
    if MISSING in states:
        return MISSING
    if WARMUP in states:
        return WARMUP
    return AVAILABLE
