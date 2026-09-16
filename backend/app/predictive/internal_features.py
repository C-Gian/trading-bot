"""The frozen causal internal feature set of `PREDICTIVE-INTERNAL-STRUCTURE-V1`.

Eighteen features built only from completed canonical BTCUSDT hourly OHLCV bars at or
before the decision instant `T`. The bar `[T, T+1h)` is completed at `T` and may be used;
no bar with an open time after `T` may enter a feature. The horizon bar is the label and is
never readable here.

Availability is deterministic and fail-closed. Every hourly bar in the maximum 168h lookback
must exist and be complete; the two named degenerate cases (a zero efficiency denominator, a
zero rolling range) have fixed values; anything else invalid or non-finite makes the whole
vector unavailable. Nothing is interpolated, forward filled, backward filled or substituted.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .labels import HOUR_SECONDS, LabelError

ROOT = Path(__file__).resolve().parents[3]
HOURLY_ARTIFACT = "data/derived/BTCUSDT-1h.parquet"

FEATURE_SET_VERSION = "PREDICTIVE_INTERNAL_CAUSAL_FEATURES_V1"

# The maximum lookback. `logret_168h` reads `c_{T-168h}` and `rv_168h` reads the 168 hourly
# returns ending at T, so the complete contiguous requirement is the 169 bars T-168h .. T.
MAX_LOOKBACK_HOURS = 168
REQUIRED_BARS = MAX_LOOKBACK_HOURS + 1

FEATURE_NAMES = (
    "logret_1h",
    "logret_6h",
    "logret_24h",
    "logret_72h",
    "logret_168h",
    "rv_6h",
    "rv_24h",
    "rv_72h",
    "rv_168h",
    "signed_efficiency_24h",
    "signed_efficiency_72h",
    "signed_efficiency_168h",
    "up_fraction_24h",
    "up_fraction_168h",
    "close_position_24h",
    "close_position_168h",
    "log_volume_relative_24h",
    "log_volume_regime_24_168h",
)
FEATURE_COUNT = len(FEATURE_NAMES)

ZERO_EFFICIENCY_DENOMINATOR_VALUE = 0.0
ZERO_RANGE_CLOSE_POSITION_VALUE = 0.5

# Ordered, mutually exclusive: the first rule that fires owns the instant.
LOOKBACK_BAR_MISSING = "LOOKBACK_BAR_MISSING"
LOOKBACK_BAR_INCOMPLETE = "LOOKBACK_BAR_INCOMPLETE"
NON_POSITIVE_CLOSE = "NON_POSITIVE_CLOSE"
NEGATIVE_VOLUME = "NEGATIVE_VOLUME"
NON_POSITIVE_MEAN_VOLUME = "NON_POSITIVE_MEAN_VOLUME"
NON_FINITE_FEATURE = "NON_FINITE_FEATURE"

UNAVAILABILITY_TAXONOMY = (
    LOOKBACK_BAR_MISSING,
    LOOKBACK_BAR_INCOMPLETE,
    NON_POSITIVE_CLOSE,
    NEGATIVE_VOLUME,
    NON_POSITIVE_MEAN_VOLUME,
    NON_FINITE_FEATURE,
)


@dataclass(frozen=True)
class OhlcvBar:
    """One canonical hourly OHLCV bar. `open_time` is UTC seconds since the epoch."""

    open_time: int
    high: float
    low: float
    close: float
    volume: float
    complete: bool


@dataclass(frozen=True)
class FeatureVector:
    """One available causal feature vector at decision instant `open_time`."""

    open_time: int
    values: tuple[float, ...]


def feature_source_open_times(instant: int) -> tuple[int, ...]:
    """Exactly the bars a feature vector at `instant` may read, oldest first.

    This is the whole causal surface of the feature set, so a look-ahead guard can be
    asserted against this tuple rather than against a comment claiming causality.
    """
    first = instant - MAX_LOOKBACK_HOURS * HOUR_SECONDS
    return tuple(range(first, instant + HOUR_SECONDS, HOUR_SECONDS))


def _tail(bars: Sequence[OhlcvBar], hours: int) -> Sequence[OhlcvBar]:
    """The last `hours` bars ending at the decision bar, inclusive of it."""
    return bars[REQUIRED_BARS - hours :]


def _hourly_returns(closes: Sequence[float]) -> list[float]:
    return [math.log(closes[index] / closes[index - 1]) for index in range(1, len(closes))]


def build_feature_vector(
    bars_by_open: Mapping[int, OhlcvBar], instant: int
) -> tuple[tuple[float, ...] | None, str | None]:
    """Build the frozen vector at `instant`, or say exactly why it is unavailable.

    Returns `(values, None)` when available and `(None, reason)` when not. An unavailable
    evaluation instant becomes a counted `NEUTRAL_UNCERTAIN` abstention; an unavailable
    training instant is excluded from fitting and counted. Neither is ever imputed.
    """
    window: list[OhlcvBar] = []
    for open_time in feature_source_open_times(instant):
        bar = bars_by_open.get(open_time)
        if bar is None:
            return None, LOOKBACK_BAR_MISSING
        if not bar.complete:
            return None, LOOKBACK_BAR_INCOMPLETE
        window.append(bar)

    closes = [bar.close for bar in window]
    volumes = [bar.volume for bar in window]
    if any(not math.isfinite(close) or close <= 0.0 for close in closes):
        return None, NON_POSITIVE_CLOSE
    if any(not math.isfinite(volume) or volume < 0.0 for volume in volumes):
        return None, NEGATIVE_VOLUME

    decision_close = closes[-1]
    # `returns[-n:]` are exactly the last n hourly returns ending at the decision bar.
    returns = _hourly_returns(closes)

    def logret(hours: int) -> float:
        return math.log(decision_close / closes[REQUIRED_BARS - 1 - hours])

    def realized_volatility(hours: int) -> float:
        return math.sqrt(sum(value * value for value in returns[-hours:]))

    def travelled_path(hours: int) -> float:
        return sum(abs(value) for value in returns[-hours:])

    def signed_efficiency(hours: int) -> float:
        travelled = travelled_path(hours)
        if travelled == 0.0:
            return ZERO_EFFICIENCY_DENOMINATOR_VALUE
        return logret(hours) / travelled

    def up_fraction(hours: int) -> float:
        recent = returns[-hours:]
        return sum(1 for value in recent if value > 0.0) / len(recent)

    def close_position(hours: int) -> float:
        recent = _tail(window, hours)
        highest = max(bar.high for bar in recent)
        lowest = min(bar.low for bar in recent)
        span = highest - lowest
        if span == 0.0:
            return ZERO_RANGE_CLOSE_POSITION_VALUE
        return (decision_close - lowest) / span

    def mean_volume(hours: int) -> float:
        recent = _tail(window, hours)
        return sum(bar.volume for bar in recent) / len(recent)

    mean_volume_24 = mean_volume(24)
    mean_volume_168 = mean_volume(168)
    if mean_volume_24 <= 0.0 or mean_volume_168 <= 0.0:
        return None, NON_POSITIVE_MEAN_VOLUME
    if volumes[-1] <= 0.0:
        return None, NON_FINITE_FEATURE

    values = (
        returns[-1],
        logret(6),
        logret(24),
        logret(72),
        logret(168),
        realized_volatility(6),
        realized_volatility(24),
        realized_volatility(72),
        realized_volatility(168),
        signed_efficiency(24),
        signed_efficiency(72),
        signed_efficiency(168),
        up_fraction(24),
        up_fraction(168),
        close_position(24),
        close_position(168),
        math.log(volumes[-1] / mean_volume_24),
        math.log(mean_volume_24 / mean_volume_168),
    )
    if len(values) != FEATURE_COUNT:
        raise LabelError("the frozen feature vector changed width")
    if any(not math.isfinite(value) for value in values):
        return None, NON_FINITE_FEATURE
    return values, None


class CausalView(dict):
    """A bar index that refuses any read after the decision instant it guards."""

    def __init__(self, source: Mapping[int, OhlcvBar], instant: int) -> None:
        super().__init__(source)
        self._instant = instant

    def get(self, key: Any, default: Any = None) -> Any:
        if isinstance(key, int) and key > self._instant:
            raise LabelError(f"look-ahead: a feature at {self._instant} read a bar at {key}")
        return dict.get(self, key, default)


def assert_feature_causality(bars_by_open: Mapping[int, OhlcvBar], instant: int) -> None:
    """Prove the vector at `instant` cannot read a bar after `instant`.

    Rebuilds the vector against a view that raises the moment a later bar is requested, so
    the guard exercises the code path instead of restating an intention.
    """
    build_feature_vector(CausalView(bars_by_open, instant), instant)


def index_ohlcv(bars: Iterable[OhlcvBar]) -> dict[int, OhlcvBar]:
    return {bar.open_time: bar for bar in bars}


def load_hourly_ohlcv(root: Path = ROOT) -> tuple[OhlcvBar, ...]:
    """Read the governed hourly artifact. Never touches post-cutoff or sealed data."""
    import pyarrow.parquet as pq

    path = root / HOURLY_ARTIFACT
    if not path.is_file():
        raise LabelError(f"the canonical hourly artifact is not installed: {HOURLY_ARTIFACT}")
    table = pq.read_table(path, columns=["open_time", "high", "low", "close", "volume", "complete"])
    open_times = table["open_time"].to_numpy().astype("datetime64[s]").astype("int64")
    highs = table["high"].to_numpy()
    lows = table["low"].to_numpy()
    closes = table["close"].to_numpy()
    volumes = table["volume"].to_numpy()
    complete = table["complete"].to_numpy(zero_copy_only=False)
    return tuple(
        OhlcvBar(
            open_time=int(moment),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=float(volume),
            complete=bool(flag),
        )
        for moment, high, low, close, volume, flag in zip(
            open_times, highs, lows, closes, volumes, complete, strict=True
        )
    )


__all__ = [
    "FEATURE_COUNT",
    "FEATURE_NAMES",
    "FEATURE_SET_VERSION",
    "HOURLY_ARTIFACT",
    "LOOKBACK_BAR_INCOMPLETE",
    "LOOKBACK_BAR_MISSING",
    "MAX_LOOKBACK_HOURS",
    "NEGATIVE_VOLUME",
    "NON_FINITE_FEATURE",
    "NON_POSITIVE_CLOSE",
    "NON_POSITIVE_MEAN_VOLUME",
    "REQUIRED_BARS",
    "UNAVAILABILITY_TAXONOMY",
    "ZERO_EFFICIENCY_DENOMINATOR_VALUE",
    "ZERO_RANGE_CLOSE_POSITION_VALUE",
    "CausalView",
    "FeatureVector",
    "OhlcvBar",
    "assert_feature_causality",
    "build_feature_vector",
    "feature_source_open_times",
    "index_ohlcv",
    "load_hourly_ohlcv",
]
