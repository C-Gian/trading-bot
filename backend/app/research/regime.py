"""`FINANCIAL_CONDITIONS_REGIME_V1`: a point-in-time NFCI gate, not a predictor.

WP-011 established direct negative evidence for treating macro variables as additive
predictive features. This module uses exactly one macro series, and only to partition
hours into two regimes:

- ``NORMAL_OR_LOOSE`` when the latest conservatively available NFCI is at or below 0.0
- ``TIGHT`` when it is above 0.0

The threshold is exactly 0.0 and is not fitted or searched. NFCI is standardized around
zero, so zero carries an intrinsic reading of roughly average financial conditions.

NFCI never enters an expert's feature matrix. It only selects which expert speaks.

Availability follows the frozen ALFRED point-in-time semantics already validated in
WP-009 and WP-011: historical vintage states only, conservative next-calendar-day
availability, no future revision visible before its own publication, no interpolation and
nothing after the development cutoff. An hour with no conservatively available NFCI is
ineligible and counted, never imputed.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, date
from pathlib import Path
from typing import Any

from .evaluation_protocol import HOUR_US, utc_us
from .macro import CUTOFF_US, MacroDataError, verified_records
from .wp004 import ROOT

REGIME_VERSION = "FINANCIAL_CONDITIONS_REGIME_V1"
REGIME_SERIES = "NFCI"
REGIME_THRESHOLD = 0.0
NORMAL_OR_LOOSE = "NORMAL_OR_LOOSE"
TIGHT = "TIGHT"
REGIMES = (NORMAL_OR_LOOSE, TIGHT)


class RegimeError(MacroDataError):
    """The frozen regime definition or its point-in-time availability was violated."""


@dataclass(frozen=True)
class RegimeReading:
    """What the regime gate saw at one signal instant."""

    signal_us: int
    regime: str
    nfci: float
    observation: date


def classify(nfci: float) -> str:
    """The entire frozen rule: zero is the boundary, and nothing else is tested."""
    return TIGHT if nfci > REGIME_THRESHOLD else NORMAL_OR_LOOSE


class RegimeSource:
    """Latest conservatively available NFCI per instant, resolved by bisect."""

    def __init__(self, steps: list[tuple[int, date, float]]):
        if not steps:
            raise RegimeError("no NFCI vintage history is available")
        ordered = sorted(steps, key=lambda item: (item[0], item[1]))
        state: dict[date, float] = {}
        self.available: list[int] = []
        self.latest: list[tuple[date, float]] = []
        for index, (available_us, observation, value) in enumerate(ordered):
            state[observation] = value
            if index + 1 < len(ordered) and ordered[index + 1][0] == available_us:
                continue  # collapse simultaneous publications into one visible step
            newest = max(state)
            self.available.append(available_us)
            self.latest.append((newest, state[newest]))
        self._cache: dict[int, RegimeReading | None] = {}

    def at(self, signal_us: int) -> RegimeReading | None:
        """The regime at ``signal_us``, or ``None`` when NFCI is not yet available."""
        if signal_us % HOUR_US or signal_us > CUTOFF_US:
            raise RegimeError("regime signal is misaligned or post-cutoff")
        if signal_us in self._cache:
            return self._cache[signal_us]
        position = bisect_right(self.available, signal_us) - 1
        if position < 0:
            self._cache[signal_us] = None
            return None
        observation, value = self.latest[position]
        reading = RegimeReading(signal_us, classify(value), float(value), observation)
        self._cache[signal_us] = reading
        return reading


def load_regime_source(root: Path = ROOT) -> RegimeSource:
    """Build the gate from the accepted ALFRED artifact, NFCI only."""
    steps = []
    for record in verified_records(root):
        if record["series_id"] != REGIME_SERIES:
            continue
        available = record["availability_time"]
        if available.tzinfo is None:
            raise RegimeError("ALFRED availability time must be explicit UTC")
        observation = record["observation_date"]
        if observation > date(2024, 12, 31):
            raise RegimeError("post-cutoff NFCI observation")
        steps.append((utc_us(available.astimezone(UTC)), observation, float(record["value"])))
    return RegimeSource(steps)


def independent_regime(records: list[dict[str, Any]], signal_us: int) -> RegimeReading | None:
    """Naive full-rescan regime used only by the audit, never by the runner."""
    from datetime import timedelta

    from .evaluation_protocol import EPOCH

    instant = EPOCH + timedelta(microseconds=signal_us)
    state: dict[date, tuple[Any, float]] = {}
    for record in records:
        if record["series_id"] != REGIME_SERIES:
            continue
        available = record["availability_time"].astimezone(UTC)
        if available > instant:
            continue
        observation = record["observation_date"]
        previous = state.get(observation)
        if previous is None or available >= previous[0]:
            state[observation] = (available, float(record["value"]))
    if not state:
        return None
    observation = max(state)
    value = state[observation][1]
    return RegimeReading(signal_us, classify(value), value, observation)


__all__ = [
    "NORMAL_OR_LOOSE",
    "REGIMES",
    "REGIME_SERIES",
    "REGIME_THRESHOLD",
    "REGIME_VERSION",
    "TIGHT",
    "RegimeError",
    "RegimeReading",
    "RegimeSource",
    "classify",
    "independent_regime",
    "load_regime_source",
]
