"""Build the P1A decision grids, 120h forward outcomes and raw ALIGNED event positions.

Data access lives here so that `signal_persistence` stays a pure, market-data-free
design module. Nothing in this file aggregates outcomes: it only assembles the series
that the guarded placebo aggregator consumes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .continuation import IneligibleSignal
from .continuation_lab import ResearchInputs
from .evaluation_protocol import HOUR_US, load_protocol, utc_us
from .signal_persistence import (
    HORIZON_MINUTES,
    MINUTE_US,
    PRIMARY_HORIZON_HOURS,
    VARIANT,
    FoldSignalSeries,
)

ROOT = Path(__file__).resolve().parents[3]
TERMINAL_OFFSET_MINUTES = HORIZON_MINUTES - 1


def fold_decision_span(fold: dict[str, Any]) -> tuple[int, int]:
    """First and last hourly decision instant whose 120h outcome stays inside the fold."""
    start = utc_us(fold["validation_start"])
    last = utc_us(fold["validation_end_exclusive"]) - PRIMARY_HORIZON_HOURS * HOUR_US
    if last < start:
        raise ValueError("fold is too short to contain a complete 120h outcome")
    return start, last


def collect_fold_series(
    inputs: ResearchInputs, protocol: dict[str, Any]
) -> tuple[FoldSignalSeries, ...]:
    """One series per fixed annual validation fold, in frozen protocol order."""
    minute_times = inputs.minute_times
    minute_open = inputs.minute_open
    minute_close = inputs.minute_close
    last_index = len(minute_times) - 1
    series: list[FoldSignalSeries] = []
    for fold in protocol["folds"]:
        start, last = fold_decision_span(fold)
        span = int((last - start) // HOUR_US) + 1
        grid = start + np.arange(span, dtype=np.int64) * HOUR_US
        entry = np.searchsorted(minute_times, grid)
        clamped_entry = np.minimum(entry, last_index)
        terminal = entry + TERMINAL_OFFSET_MINUTES
        clamped_terminal = np.minimum(terminal, last_index)
        # A contiguous minute path exists exactly when both endpoints land on their own
        # instant; a missing minute between them shifts the terminal index backwards.
        contained = (
            (minute_times[clamped_entry] == grid)
            & (terminal <= last_index)
            & (minute_times[clamped_terminal] == grid + TERMINAL_OFFSET_MINUTES * MINUTE_US)
        )
        eligible = np.nonzero(contained)[0]
        entry_price = minute_open[entry[eligible]]
        terminal_price = minute_close[terminal[eligible]]
        if not np.all(entry_price > 0) or not np.all(np.isfinite(terminal_price)):
            raise ValueError("non-tradable price on an eligible 120h decision instant")
        forward = (terminal_price - entry_price) / entry_price * 10000.0
        times = grid[eligible]
        positions: list[int] = []
        feature_ineligible = 0
        emitted_on_span = 0
        for position, instant in enumerate(times):
            try:
                emits, _, _ = inputs.features.decision(int(instant), VARIANT, 0)
            except IneligibleSignal:
                feature_ineligible += 1
                continue
            if emits:
                positions.append(position)
        for instant in grid:
            try:
                emits, _, _ = inputs.features.decision(int(instant), VARIANT, 0)
            except IneligibleSignal:
                continue
            if emits:
                emitted_on_span += 1
        series.append(
            FoldSignalSeries(
                fold_id=fold["fold_id"],
                decision_times_us=tuple(int(value) for value in times),
                forward_bps=tuple(float(value) for value in forward),
                signal_positions=tuple(positions),
                grid_span_hours=span,
                feature_ineligible_clocks=feature_ineligible,
                outcome_ineligible_clocks=span - len(eligible),
                emitted_conditions_on_span=emitted_on_span,
            )
        )
    return tuple(series)


def load_fold_series(root: Path = ROOT) -> tuple[FoldSignalSeries, ...]:
    return collect_fold_series(ResearchInputs.load(root), load_protocol())
