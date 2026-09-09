"""PERSISTENT_TREND_PULLBACK_RECOVERY_V1: causal recovery features and two frozen variants.

The event is a recovery transition: the previous hourly close sat at or below its
one-day mean and the current completed close is back above it, inside an already
persistent multi-day uptrend. There is no prior-high breakout requirement, no
SMA24/SMA168 membership rule, no volume condition, and no pullback-depth threshold.

Bar eligibility, quarantine and cutoff semantics are inherited unchanged from
CONTINUATION_FEATURES_V2 so both families share one data-quality universe.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from math import fsum, isfinite

from .continuation import CUTOFF_US, FeatureBar, IneligibleSignal
from .evaluation_protocol import HOUR_US

FEATURE_VERSION = "PULLBACK_RECOVERY_FEATURES_V1"
STRATEGY_VERSION = "PERSISTENT_TREND_PULLBACK_RECOVERY_V1"
VARIANTS = ("RECOVERY_CORE", "RECOVERY_CONFIRM")
SMA_HOURS = 24
HOURLY_BARS = SMA_HOURS + 1
CONTEXT_BARS = 43
CONTEXT_INCREMENTS = CONTEXT_BARS - 1
UP_TO_DOWN_RATIO = 2


@dataclass(frozen=True)
class RecoveryFeatures:
    """Everything the two frozen rules may consult, observed at the decision boundary."""

    asof_us: int
    reference: float
    sma24: float
    sma24_previous: float
    previous_close: float
    previous_high: float
    below_mean_before: bool
    recovered_above_mean: bool
    recovery_event: bool
    persistent_up: bool
    exceeds_previous_high: bool


class RecoveryFeatureSource:
    """Holds only completed signal/context bars, never any part of the execution path."""

    def __init__(self, hourly: tuple[FeatureBar, ...], context: tuple[FeatureBar, ...]):
        self.hourly, self.context = hourly, context
        self.hour_times = tuple(bar.open_us for bar in hourly)
        self.context_times = tuple(bar.open_us for bar in context)
        self._cache: dict[int, RecoveryFeatures] = {}
        for bars, width in ((hourly, HOUR_US), (context, 4 * HOUR_US)):
            previous = -1
            for bar in bars:
                if bar.open_us <= previous or bar.open_us % width or bar.open_us > CUTOFF_US:
                    raise ValueError("derived bars must be unique aligned development instants")
                if (
                    not all(isfinite(value) for value in (bar.high, bar.close, bar.volume))
                    or bar.high < bar.close
                    or bar.close <= 0
                    or bar.volume < 0
                ):
                    raise ValueError("invalid derived observation")
                previous = bar.open_us

    @staticmethod
    def _window(bars, times, signal_us: int, width: int, count: int) -> tuple[FeatureBar, ...]:
        """Exactly ``count`` completed contiguous bars ending with the last closed one."""
        expected_open = signal_us // width * width - width
        end = bisect_right(times, expected_open)
        selected = bars[max(0, end - count) : end]
        if len(selected) != count or any(
            not bar.complete or bar.open_us != expected_open - (count - 1 - index) * width
            for index, bar in enumerate(selected)
        ):
            raise IneligibleSignal("completed contiguous lookback unavailable")
        return selected

    def at(self, signal_us: int) -> RecoveryFeatures:
        if signal_us % HOUR_US or signal_us > CUTOFF_US:
            raise ValueError("signal clock outside hourly development boundary")
        if signal_us in self._cache:
            return self._cache[signal_us]
        hours = self._window(self.hourly, self.hour_times, signal_us, HOUR_US, HOURLY_BARS)
        context = self._window(
            self.context, self.context_times, signal_us, 4 * HOUR_US, CONTEXT_BARS
        )
        changes = [
            context[index].close - context[index - 1].close for index in range(1, CONTEXT_BARS)
        ]
        up = fsum(max(change, 0.0) for change in changes)
        down = fsum(max(-change, 0.0) for change in changes)
        closes = [bar.close for bar in hours]
        # The current bar is the just-closed hour; the mean windows differ by one hour.
        sma24 = fsum(closes[1:]) / SMA_HOURS
        sma24_previous = fsum(closes[:-1]) / SMA_HOURS
        current, previous = hours[-1], hours[-2]
        below_before = previous.close <= sma24_previous
        recovered = current.close > sma24
        result = RecoveryFeatures(
            asof_us=signal_us,
            reference=current.close,
            sma24=sma24,
            sma24_previous=sma24_previous,
            previous_close=previous.close,
            previous_high=previous.high,
            below_mean_before=below_before,
            recovered_above_mean=recovered,
            recovery_event=below_before and recovered,
            persistent_up=up + down > 0 and up >= UP_TO_DOWN_RATIO * down,
            exceeds_previous_high=current.close > previous.high,
        )
        self._cache[signal_us] = result
        return result

    def decision(
        self, signal_us: int, variant: str, delay_hours: int = 0
    ) -> tuple[bool, RecoveryFeatures, float]:
        """Emit the frozen rule; the delay control shifts the condition, never the barriers."""
        if variant not in VARIANTS or delay_hours not in (0, 1):
            raise ValueError("undeclared strategy variant or timing perturbation")
        # Both feature clocks are required for every profile: the same quality universe.
        current = self.at(signal_us)
        previous = self.at(signal_us - HOUR_US)
        feature = previous if delay_hours else current
        emits = feature.recovery_event and feature.persistent_up
        if variant == "RECOVERY_CONFIRM":
            emits = emits and feature.exceeds_previous_high
        return emits, feature, current.reference
