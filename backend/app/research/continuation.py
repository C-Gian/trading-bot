"""ALIGNED_PARTICIPATION_CONTINUATION_V1: causal features and three frozen gates."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from math import fsum, isfinite

from .evaluation_protocol import HOUR_US, utc_us

FEATURE_VERSION = "CONTINUATION_FEATURES_V1"
VARIANTS = ("REGIME_ONLY", "PARTICIPATION_ONLY", "ALIGNED")
CUTOFF_US = utc_us("2024-12-31T23:59:00Z")


class IneligibleSignal(ValueError):
    """Required completed contiguous observations are unavailable."""


@dataclass(frozen=True)
class FeatureBar:
    open_us: int
    high: float
    close: float
    volume: float
    complete: bool = True


@dataclass(frozen=True)
class Features:
    asof_us: int
    reference: float
    breakout: bool
    persistent_up: bool
    participation: bool
    signed_efficiency: float | None
    relative_volume: float | None


class FeatureSource:
    """Contains only derived signal/context bars, never the future execution path."""

    def __init__(self, hourly: tuple[FeatureBar, ...], context: tuple[FeatureBar, ...]):
        self.hourly, self.context = hourly, context
        self.hour_times = tuple(bar.open_us for bar in hourly)
        self.context_times = tuple(bar.open_us for bar in context)
        self._cache: dict[int, Features] = {}
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
        expected_open = signal_us // width * width - width
        end = bisect_right(times, expected_open)
        selected = bars[max(0, end - count) : end]
        if len(selected) != count or any(
            not bar.complete or bar.open_us != expected_open - (count - 1 - index) * width
            for index, bar in enumerate(selected)
        ):
            raise IneligibleSignal("completed contiguous lookback unavailable")
        return selected

    def at(self, signal_us: int) -> Features:
        if signal_us % HOUR_US or signal_us > CUTOFF_US:
            raise ValueError("signal clock outside hourly development boundary")
        if signal_us in self._cache:
            return self._cache[signal_us]
        hours = self._window(self.hourly, self.hour_times, signal_us, HOUR_US, 25)
        context = self._window(self.context, self.context_times, signal_us, 4 * HOUR_US, 43)
        changes = [context[i].close - context[i - 1].close for i in range(1, 43)]
        up = fsum(max(change, 0.0) for change in changes)
        down = fsum(max(-change, 0.0) for change in changes)
        volume_mean = fsum(bar.volume for bar in hours[:-1]) / 24
        result = Features(
            signal_us,
            hours[-1].close,
            hours[-1].close > max(bar.high for bar in hours[:-1]),
            up + down > 0 and up >= 2 * down,
            volume_mean > 0 and hours[-1].volume >= 2 * volume_mean,
            (up - down) / (up + down) if up + down else None,
            hours[-1].volume / volume_mean if volume_mean else None,
        )
        self._cache[signal_us] = result
        return result

    def decision(
        self, signal_us: int, variant: str, delay_hours: int = 0
    ) -> tuple[bool, Features, float]:
        if variant not in VARIANTS or delay_hours not in (0, 1):
            raise ValueError("undeclared strategy variant or timing perturbation")
        # Both feature clocks are required for every profile: the same quality universe.
        current = self.at(signal_us)
        previous = self.at(signal_us - HOUR_US)
        feature = previous if delay_hours else current
        emits = (
            feature.breakout
            and (variant == "PARTICIPATION_ONLY" or feature.persistent_up)
            and (variant == "REGIME_ONLY" or feature.participation)
        )
        return emits, feature, current.reference
