"""`PROSPECTIVE_PAPER_FEATURES_V1`: the ALIGNED gates on real forward timestamps.

The frozen research `FeatureSource` (`CONTINUATION_FEATURES_V2`) is hash-frozen by the
committed novelty admission and correctly refuses clocks after the development cutoff,
so WP-010A translated post-cutoff instants onto an in-development anchor. This adapter
removes that last workaround from the product path by reproducing the frozen feature
and gate semantics exactly while working on real current instants.

Nothing here changes a parameter or loosens a gate. The lookback widths (25 completed
hourly bars, 43 completed four-hour bars), the contiguity and completeness quarantine,
the breakout, persistence and participation definitions and the two-clock requirement
of `decision` are identical. `backend/tests/test_prospective_features.py` pins that by
running both implementations over identical pre-cutoff fixtures.

The frozen research implementation is untouched, stays cutoff-protected, and no
research or backtest module may import this adapter.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from math import fsum, isfinite

from ..research.continuation import FEATURE_VERSION, VARIANTS, FeatureBar, IneligibleSignal

PROSPECTIVE_FEATURES_VERSION = "PROSPECTIVE_PAPER_FEATURES_V1"
FROZEN_FEATURE_VERSION = FEATURE_VERSION
HOUR_US = 3_600_000_000
CONTEXT_US = 4 * HOUR_US
HOURLY_LOOKBACK = 25
CONTEXT_LOOKBACK = 43
BREAKOUT_HOURS = 24
VOLUME_BASELINE_HOURS = 24
VOLUME_MULTIPLIER = 2
UP_TO_DOWN_RATIO = 2


@dataclass(frozen=True)
class ProspectiveFeatures:
    """Same fields as the frozen `Features`, carrying a real forward instant."""

    asof_us: int
    reference: float
    breakout: bool
    persistent_up: bool
    participation: bool
    signed_efficiency: float | None
    relative_volume: float | None


class ProspectiveFeatureSource:
    """Derived signal/context bars on real instants; never the execution path."""

    def __init__(self, hourly: Sequence[FeatureBar], context: Sequence[FeatureBar]):
        self.hourly, self.context = tuple(hourly), tuple(context)
        self.hour_times = tuple(bar.open_us for bar in self.hourly)
        self.context_times = tuple(bar.open_us for bar in self.context)
        self._cache: dict[int, ProspectiveFeatures] = {}
        for bars, width in ((self.hourly, HOUR_US), (self.context, CONTEXT_US)):
            previous = -1
            for bar in bars:
                if bar.open_us <= previous or bar.open_us % width:
                    raise ValueError("derived bars must be unique aligned instants")
                if (
                    not all(isfinite(value) for value in (bar.high, bar.close, bar.volume))
                    or bar.high < bar.close
                    or bar.close <= 0
                    or bar.volume < 0
                ):
                    raise ValueError("invalid derived observation")
                previous = bar.open_us

    @staticmethod
    def _window(
        bars: tuple[FeatureBar, ...],
        times: tuple[int, ...],
        signal_us: int,
        width: int,
        count: int,
    ) -> tuple[FeatureBar, ...]:
        expected_open = signal_us // width * width - width
        end = bisect_right(times, expected_open)
        selected = bars[max(0, end - count) : end]
        if len(selected) != count or any(
            not bar.complete or bar.open_us != expected_open - (count - 1 - index) * width
            for index, bar in enumerate(selected)
        ):
            raise IneligibleSignal("completed contiguous lookback unavailable")
        return selected

    def at(self, signal_us: int) -> ProspectiveFeatures:
        if signal_us % HOUR_US:
            raise ValueError("signal clock is not on an hourly boundary")
        if signal_us in self._cache:
            return self._cache[signal_us]
        hours = self._window(self.hourly, self.hour_times, signal_us, HOUR_US, HOURLY_LOOKBACK)
        context = self._window(
            self.context, self.context_times, signal_us, CONTEXT_US, CONTEXT_LOOKBACK
        )
        changes = [context[i].close - context[i - 1].close for i in range(1, CONTEXT_LOOKBACK)]
        up = fsum(max(change, 0.0) for change in changes)
        down = fsum(max(-change, 0.0) for change in changes)
        volume_mean = fsum(bar.volume for bar in hours[:-1]) / VOLUME_BASELINE_HOURS
        result = ProspectiveFeatures(
            signal_us,
            hours[-1].close,
            hours[-1].close > max(bar.high for bar in hours[:-1]),
            up + down > 0 and up >= UP_TO_DOWN_RATIO * down,
            volume_mean > 0 and hours[-1].volume >= VOLUME_MULTIPLIER * volume_mean,
            (up - down) / (up + down) if up + down else None,
            hours[-1].volume / volume_mean if volume_mean else None,
        )
        self._cache[signal_us] = result
        return result

    def decision(
        self, signal_us: int, variant: str, delay_hours: int = 0
    ) -> tuple[bool, ProspectiveFeatures, float]:
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
