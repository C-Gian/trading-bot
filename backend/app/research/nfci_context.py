"""Raw point-in-time NFCI context for WP-013.

The source exposes the latest historical NFCI vintage conservatively available at an
hourly signal instant.  It deliberately contains no regime classification, threshold,
centering, clipping, smoothing, interpolation, or transformation.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, date, timedelta
from pathlib import Path
from typing import Any

from .evaluation_protocol import EPOCH, HOUR_US, utc_us
from .macro import CUTOFF_US, MacroDataError, verified_records
from .wp004 import ROOT

CONTEXT_VERSION = "NFCI_CONTEXT_V1"
CONTEXT_SERIES = "NFCI"


class NFCIContextError(MacroDataError):
    """The frozen raw NFCI context contract was violated."""


@dataclass(frozen=True)
class NFCIReading:
    signal_us: int
    value: float
    observation: date


class NFCIContextSource:
    """Availability-ordered raw NFCI vintages queried strictly as of signal time."""

    def __init__(self, steps: list[tuple[int, date, float]]):
        if not steps:
            raise NFCIContextError("no NFCI vintage history is available")
        ordered = sorted(steps, key=lambda item: (item[0], item[1]))
        state: dict[date, float] = {}
        self.available: list[int] = []
        self.latest: list[tuple[date, float]] = []
        for index, (available_us, observation, value) in enumerate(ordered):
            state[observation] = value
            if index + 1 < len(ordered) and ordered[index + 1][0] == available_us:
                continue
            newest = max(state)
            self.available.append(available_us)
            self.latest.append((newest, state[newest]))
        self._cache: dict[int, NFCIReading | None] = {}

    def at(self, signal_us: int) -> NFCIReading | None:
        if signal_us % HOUR_US or signal_us > CUTOFF_US:
            raise NFCIContextError("NFCI context signal is misaligned or post-cutoff")
        if signal_us in self._cache:
            return self._cache[signal_us]
        position = bisect_right(self.available, signal_us) - 1
        if position < 0:
            self._cache[signal_us] = None
            return None
        observation, value = self.latest[position]
        reading = NFCIReading(signal_us, float(value), observation)
        self._cache[signal_us] = reading
        return reading


def load_nfci_context(root: Path = ROOT) -> NFCIContextSource:
    steps: list[tuple[int, date, float]] = []
    for record in verified_records(root):
        if record["series_id"] != CONTEXT_SERIES:
            continue
        available = record["availability_time"]
        if available.tzinfo is None:
            raise NFCIContextError("ALFRED availability time must be explicit UTC")
        observation = record["observation_date"]
        if observation > date(2024, 12, 31):
            raise NFCIContextError("post-cutoff NFCI observation")
        steps.append((utc_us(available.astimezone(UTC)), observation, float(record["value"])))
    return NFCIContextSource(steps)


def independent_nfci(records: list[dict[str, Any]], signal_us: int) -> NFCIReading | None:
    """Naive full rescan used by audits/reconciliation, never by the primary runner."""
    instant = EPOCH + timedelta(microseconds=signal_us)
    state: dict[date, tuple[Any, float]] = {}
    for record in records:
        if record["series_id"] != CONTEXT_SERIES:
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
    return NFCIReading(signal_us, state[observation][1], observation)


__all__ = [
    "CONTEXT_SERIES",
    "CONTEXT_VERSION",
    "NFCIContextError",
    "NFCIContextSource",
    "NFCIReading",
    "independent_nfci",
    "load_nfci_context",
]
