"""Deterministic 24h terminal labels on the canonical BTCUSDT hourly decision grid.

The grid is every hourly instant between the first and last canonical hourly bar. `T`
indexes the closed bar `[T, T+1h)`: the decision is taken at that bar's close, the decision
price is `close[T]`, and the label is `r_24h = log(close[T+24h] / close[T])`.

Information available at `T` is exactly the bars with open time `<= T`. Nothing here reads a
later bar except the horizon bar, which is the label and never a feature.

Every excluded instant carries a typed reason and is counted. Canonical gaps are never
interpolated and no nearest-bar substitution exists.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import DOWN, HORIZON_HOURS, NEUTRAL, UP

ROOT = Path(__file__).resolve().parents[3]
HOURLY_ARTIFACT = "data/derived/BTCUSDT-1h.parquet"
HOUR_SECONDS = 3600

DECISION_BAR_MISSING = "DECISION_BAR_MISSING"
DECISION_BAR_INCOMPLETE = "DECISION_BAR_INCOMPLETE"
HORIZON_BAR_BEYOND_COVERAGE = "HORIZON_BAR_BEYOND_COVERAGE"
HORIZON_BAR_MISSING = "HORIZON_BAR_MISSING"
HORIZON_BAR_INCOMPLETE = "HORIZON_BAR_INCOMPLETE"
NON_POSITIVE_PRICE = "NON_POSITIVE_PRICE"

# Ordered, mutually exclusive: the first rule that fires owns the instant.
EXCLUSION_TAXONOMY = (
    DECISION_BAR_MISSING,
    DECISION_BAR_INCOMPLETE,
    HORIZON_BAR_BEYOND_COVERAGE,
    HORIZON_BAR_MISSING,
    HORIZON_BAR_INCOMPLETE,
    NON_POSITIVE_PRICE,
)


class LabelError(RuntimeError):
    """The label substrate is not usable as specified."""


@dataclass(frozen=True)
class Bar:
    """One canonical hourly bar. `open_time` is UTC seconds since the epoch."""

    open_time: int
    close: float
    complete: bool


@dataclass(frozen=True)
class Label:
    """One admissible 24h terminal label at decision instant `open_time`."""

    open_time: int
    decision_close: float
    horizon_close: float
    r_24h: float
    direction: str


@dataclass(frozen=True)
class LabelSet:
    """Admissible labels plus the complete, typed accounting of everything excluded."""

    labels: tuple[Label, ...]
    grid_size: int
    exclusions: Mapping[str, int]
    first_open_time: int
    last_open_time: int

    @property
    def admissible(self) -> int:
        return len(self.labels)

    def direction_counts(self) -> dict[str, int]:
        counts = {UP: 0, DOWN: 0, NEUTRAL: 0}
        for label in self.labels:
            counts[label.direction] += 1
        return counts

    def accounting(self) -> dict[str, Any]:
        excluded = sum(self.exclusions.values())
        if excluded + self.admissible != self.grid_size:
            raise LabelError("label accounting does not close")
        return {
            "grid_decision_instants": self.grid_size,
            "admissible_labels": self.admissible,
            "excluded_total": excluded,
            "exclusions": {reason: self.exclusions[reason] for reason in EXCLUSION_TAXONOMY},
            "direction_counts": self.direction_counts(),
            "first_grid_instant": self.first_open_time,
            "last_grid_instant": self.last_open_time,
        }


def direction_of(r_24h: float) -> str:
    """Direction truth. Exact zero is NEUTRAL and is never resolved to a side."""
    if r_24h > 0:
        return UP
    if r_24h < 0:
        return DOWN
    return NEUTRAL


def build_labels(bars: Sequence[Bar], horizon_hours: int = HORIZON_HOURS) -> LabelSet:
    """Label every hourly instant in coverage, or record exactly why it cannot be labelled.

    The grid is the full hourly span, not the rows that happen to exist, so a canonical gap
    becomes a counted exclusion instead of silently disappearing from the denominator.
    """
    if horizon_hours <= 0:
        raise LabelError("the horizon must be strictly positive")
    if not bars:
        raise LabelError("no canonical hourly bars were supplied")
    by_open: dict[int, Bar] = {}
    previous = None
    for bar in bars:
        if previous is not None and bar.open_time <= previous:
            raise LabelError("canonical hourly bars must be strictly increasing in time")
        previous = bar.open_time
        if bar.open_time % HOUR_SECONDS:
            raise LabelError("a canonical hourly bar is not aligned to an hour boundary")
        by_open[bar.open_time] = bar

    first, last = bars[0].open_time, bars[-1].open_time
    horizon = horizon_hours * HOUR_SECONDS
    exclusions = dict.fromkeys(EXCLUSION_TAXONOMY, 0)
    labels: list[Label] = []
    grid_size = 0

    for instant in range(first, last + HOUR_SECONDS, HOUR_SECONDS):
        grid_size += 1
        reason = None
        decision = by_open.get(instant)
        target = by_open.get(instant + horizon)
        if decision is None:
            reason = DECISION_BAR_MISSING
        elif not decision.complete:
            reason = DECISION_BAR_INCOMPLETE
        elif instant + horizon > last:
            reason = HORIZON_BAR_BEYOND_COVERAGE
        elif target is None:
            reason = HORIZON_BAR_MISSING
        elif not target.complete:
            reason = HORIZON_BAR_INCOMPLETE
        elif not (decision.close > 0 and target.close > 0):
            reason = NON_POSITIVE_PRICE
        if reason is not None:
            exclusions[reason] += 1
            continue
        assert decision is not None and target is not None  # narrowed by the branches above
        r_24h = math.log(target.close / decision.close)
        labels.append(
            Label(
                open_time=instant,
                decision_close=decision.close,
                horizon_close=target.close,
                r_24h=r_24h,
                direction=direction_of(r_24h),
            )
        )

    return LabelSet(
        labels=tuple(labels),
        grid_size=grid_size,
        exclusions=exclusions,
        first_open_time=first,
        last_open_time=last,
    )


def trailing_return(
    bars_by_open: Mapping[int, Bar], instant: int, hours: int = HORIZON_HOURS
) -> float | None:
    """Realized trailing return ending at `instant`, or None when it is not observable.

    Uses only bars at or before `instant`, so it is admissible as a decision-time feature.
    """
    decision = bars_by_open.get(instant)
    origin = bars_by_open.get(instant - hours * HOUR_SECONDS)
    if decision is None or origin is None:
        return None
    if not decision.complete or not origin.complete:
        return None
    if not (decision.close > 0 and origin.close > 0):
        return None
    return math.log(decision.close / origin.close)


def index_bars(bars: Iterable[Bar]) -> dict[int, Bar]:
    return {bar.open_time: bar for bar in bars}


def assert_causal(bars: Sequence[Bar], instant: int, used_open_times: Iterable[int]) -> None:
    """Explicit look-ahead guard for anything claiming to be a decision-time feature.

    A feature at `T` may read bars with open time `<= T` and nothing else. The horizon bar
    is the label, not a feature, and is therefore rejected here by design.
    """
    del bars
    for open_time in used_open_times:
        if open_time > instant:
            raise LabelError(
                f"look-ahead: a decision-time feature at {instant} read a bar at {open_time}"
            )


def load_hourly_bars(root: Path = ROOT) -> tuple[Bar, ...]:
    """Read the governed hourly artifact. Never touches post-cutoff or sealed data."""
    import pyarrow.parquet as pq

    path = root / HOURLY_ARTIFACT
    if not path.is_file():
        raise LabelError(f"the canonical hourly artifact is not installed: {HOURLY_ARTIFACT}")
    table = pq.read_table(path, columns=["open_time", "close", "complete"])
    open_times = table["open_time"].to_numpy().astype("datetime64[s]").astype("int64")
    closes = table["close"].to_numpy()
    complete = table["complete"].to_numpy(zero_copy_only=False)
    return tuple(
        Bar(open_time=int(o), close=float(c), complete=bool(k))
        for o, c, k in zip(open_times, closes, complete, strict=True)
    )


__all__ = [
    "DECISION_BAR_INCOMPLETE",
    "DECISION_BAR_MISSING",
    "EXCLUSION_TAXONOMY",
    "HORIZON_BAR_BEYOND_COVERAGE",
    "HORIZON_BAR_INCOMPLETE",
    "HORIZON_BAR_MISSING",
    "HOURLY_ARTIFACT",
    "HOUR_SECONDS",
    "NON_POSITIVE_PRICE",
    "Bar",
    "Label",
    "LabelError",
    "LabelSet",
    "assert_causal",
    "build_labels",
    "direction_of",
    "index_bars",
    "load_hourly_bars",
    "trailing_return",
]
