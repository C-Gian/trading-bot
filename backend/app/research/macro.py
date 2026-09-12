"""`MACRO_FEATURES_V1`: eight point-in-time macro features from ALFRED vintages.

At an hourly signal instant ``t`` only ALFRED information whose conservative
``availability_time <= t`` may be read, and only the vintage state that was current at
``t``. A later revision of the same observation is invisible until its own availability
time, so no revision can leak backward.

Nothing is interpolated and no missing history is imputed: a signal hour that lacks any
required macro input is ineligible and is counted, never filled.

The eight features are frozen by `research/protocols/WP-011-ADAPTIVE-EWLS-MACRO-V1.json`
and are never selected, searched, or conditioned on any result.
"""

from __future__ import annotations

import bisect
import math
from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from .alfred import CANONICAL_PATH, MANIFEST_PATH
from .evaluation_protocol import EPOCH, utc_us
from .exogenous import ALFRED_SERIES, read_json
from .wp004 import ROOT

FEATURE_VERSION = "MACRO_FEATURES_V1"
MACRO_FEATURES = (
    "DFF_LEVEL",
    "DGS10_LEVEL",
    "T10Y2Y_LEVEL",
    "VIX_LEVEL",
    "NFCI_LEVEL",
    "WALCL_LOG_CHANGE_28D",
    "CPI_YOY",
    "UNRATE_LEVEL",
)
LEVEL_SOURCE = {
    "DFF_LEVEL": "DFF",
    "DGS10_LEVEL": "DGS10",
    "T10Y2Y_LEVEL": "T10Y2Y",
    "VIX_LEVEL": "VIXCLS",
    "NFCI_LEVEL": "NFCI",
    "UNRATE_LEVEL": "UNRATE",
}
WALCL_LOOKBACK_DAYS = 28
CPI_LOOKBACK_MONTHS = 12
CUTOFF_US = utc_us("2024-12-31T23:59:00Z")


class MacroDataError(ValueError):
    """Point-in-time macro availability or frozen-specification validation failed."""


@dataclass(frozen=True)
class MacroRow:
    signal_us: int
    values: tuple[float, ...]
    observation_dates: tuple[date, ...]


@dataclass(frozen=True)
class _Vintage:
    """One observation value that became usable at ``available_us``."""

    available_us: int
    observation: date
    value: float


class MacroFeatureSource:
    """Vintage states per series, queried strictly as of a signal instant.

    Each series is collapsed once into an availability-ordered timeline so a lookup is a
    bisect rather than a rescan. The semantics are unchanged: only vintage states already
    published at the signal instant are visible, and a later revision of an observation
    becomes visible only from its own availability time.
    """

    def __init__(self, vintages: dict[str, list[_Vintage]]):
        missing = [series for series in ALFRED_SERIES if not vintages.get(series)]
        if missing:
            raise MacroDataError(f"missing ALFRED series history: {missing}")
        self.available: dict[str, list[int]] = {}
        self.latest: dict[str, list[tuple[date, float]]] = {}
        self.snapshots: dict[str, list[dict[date, float]]] = {}
        for series, items in vintages.items():
            ordered = sorted(items, key=lambda item: (item.available_us, item.observation))
            state: dict[date, float] = {}
            times: list[int] = []
            latest: list[tuple[date, float]] = []
            snapshots: list[dict[date, float]] = []
            keep_snapshots = series in {"WALCL", "CPIAUCSL"}
            for index, item in enumerate(ordered):
                state[item.observation] = item.value
                if (
                    index + 1 < len(ordered)
                    and ordered[index + 1].available_us == item.available_us
                ):
                    continue  # collapse simultaneous publications into one visible step
                newest = max(state)
                times.append(item.available_us)
                latest.append((newest, state[newest]))
                if keep_snapshots:
                    snapshots.append(dict(state))
            self.available[series] = times
            self.latest[series] = latest
            self.snapshots[series] = snapshots
        self._cache: dict[int, MacroRow | None] = {}

    def _index(self, series: str, signal_us: int) -> int:
        """Position of the newest vintage step published at or before the instant."""
        return bisect_right(self.available[series], signal_us) - 1

    def _latest(self, series: str, signal_us: int) -> tuple[date, float] | None:
        position = self._index(series, signal_us)
        return None if position < 0 else self.latest[series][position]

    def _state(self, series: str, signal_us: int) -> dict[date, float]:
        position = self._index(series, signal_us)
        if position < 0:
            return {}
        if not self.snapshots[series]:
            raise MacroDataError(f"no retained vintage snapshots for {series}")
        return self.snapshots[series][position]

    @staticmethod
    def _at_or_before(state: dict[date, float], limit: date) -> tuple[date, float] | None:
        """Point-in-time value for the newest observation not after ``limit``."""
        candidates = [observation for observation in state if observation <= limit]
        if not candidates:
            return None
        observation = max(candidates)
        return observation, state[observation]

    def at(self, signal_us: int) -> MacroRow | None:
        """The eight macro features, or ``None`` when required history is unavailable."""
        if signal_us % 3_600_000_000 or signal_us > CUTOFF_US:
            raise MacroDataError("macro signal is misaligned or post-cutoff")
        if signal_us in self._cache:
            return self._cache[signal_us]
        row = self._build(signal_us)
        self._cache[signal_us] = row
        return row

    def _build(self, signal_us: int) -> MacroRow | None:
        values: list[float] = []
        observations: list[date] = []
        latest: dict[str, tuple[date, float]] = {}
        for series in ALFRED_SERIES:
            found = self._latest(series, signal_us)
            if found is None:
                return None
            latest[series] = found

        for name in MACRO_FEATURES:
            if name in LEVEL_SOURCE:
                observation, value = latest[LEVEL_SOURCE[name]]
                values.append(float(value))
                observations.append(observation)
                continue
            if name == "WALCL_LOG_CHANGE_28D":
                observation, current = latest["WALCL"]
                earlier = self._at_or_before(
                    self._state("WALCL", signal_us),
                    observation - timedelta(days=WALCL_LOOKBACK_DAYS),
                )
                if earlier is None or current <= 0 or earlier[1] <= 0:
                    return None
                values.append(math.log(current / earlier[1]))
                observations.append(observation)
                continue
            if name == "CPI_YOY":
                observation, current = latest["CPIAUCSL"]
                target = _months_earlier(observation, CPI_LOOKBACK_MONTHS)
                earlier = self._at_or_before(self._state("CPIAUCSL", signal_us), target)
                if earlier is None or earlier[0] > target or current <= 0 or earlier[1] <= 0:
                    return None
                values.append(100.0 * (current / earlier[1] - 1.0))
                observations.append(observation)
                continue
            raise MacroDataError(f"undeclared macro feature {name}")

        if not all(math.isfinite(value) for value in values):
            return None
        return MacroRow(signal_us, tuple(values), tuple(observations))


def _months_earlier(observation: date, months: int) -> date:
    """Observation-month semantics: the same day-of-month ``months`` earlier."""
    year, month = observation.year, observation.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, observation.day)


def verified_records(root: Path = ROOT) -> list[dict[str, Any]]:
    """Read the accepted ALFRED artifact, refusing any byte or bound drift."""
    manifest = read_json(root / MANIFEST_PATH)
    if manifest["version"] != "ALFRED_MACRO_CONTEXT_V1":
        raise MacroDataError("ALFRED macro context version changed")
    if tuple(manifest["series"]) != ALFRED_SERIES:
        raise MacroDataError("ALFRED series set changed")
    if manifest["coverage"]["vintage_end"] != "2024-12-31":
        raise MacroDataError("ALFRED vintage coverage extends past the development cutoff")
    if manifest["current_revised_substitution"]:
        raise MacroDataError("current revised macro substitution detected")
    if manifest["post_2024_vintages"] != 0:
        raise MacroDataError("post-cutoff ALFRED vintages detected")

    artifact = manifest["file"]
    path = root / artifact["path"]
    import hashlib

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != artifact["file_sha256"]:
        raise MacroDataError("ALFRED artifact bytes differ from the accepted manifest")
    if str(path) != str(root / CANONICAL_PATH):
        raise MacroDataError("ALFRED artifact path changed")
    return pq.read_table(path).to_pylist()


def load_macro_source(root: Path = ROOT) -> MacroFeatureSource:
    vintages: dict[str, list[_Vintage]] = {series: [] for series in ALFRED_SERIES}
    for record in verified_records(root):
        series = record["series_id"]
        if series not in vintages:
            raise MacroDataError("unfrozen ALFRED series in the accepted artifact")
        available: datetime = record["availability_time"]
        if available.tzinfo is None:
            raise MacroDataError("ALFRED availability time must be explicit UTC")
        observation: date = record["observation_date"]
        if observation > date(2024, 12, 31):
            raise MacroDataError("post-cutoff ALFRED observation")
        vintages[series].append(
            _Vintage(utc_us(available.astimezone(UTC)), observation, float(record["value"]))
        )
    return MacroFeatureSource(vintages)


def availability_boundary(records: list[dict[str, Any]], series: str) -> int:
    """First instant at which any value of ``series`` is conservatively usable."""
    times = sorted(
        utc_us(record["availability_time"].astimezone(UTC))
        for record in records
        if record["series_id"] == series
    )
    if not times:
        raise MacroDataError(f"no availability history for {series}")
    return times[0]


def independent_asof(
    records: list[dict[str, Any]], series: str, signal_us: int
) -> tuple[date, float] | None:
    """Deliberately naive as-of lookup used only by the audit, never by the runner."""
    instant = EPOCH + timedelta(microseconds=signal_us)
    state: dict[date, tuple[datetime, float]] = {}
    for record in records:
        if record["series_id"] != series:
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
    return observation, state[observation][1]


def monthly_effective_instants(start_us: int, end_us: int) -> tuple[int, ...]:
    """First UTC hour of each calendar month from the month containing ``start_us``.

    The boundary of the starting month is included so the first validation month is
    already covered by an effective model.
    """
    first = EPOCH + timedelta(microseconds=start_us)
    cursor = datetime(first.year, first.month, 1, tzinfo=UTC)
    instants: list[int] = []
    while True:
        stamp = utc_us(cursor)
        if stamp > end_us:
            break
        instants.append(stamp)
        cursor = datetime(
            cursor.year + (cursor.month == 12), (cursor.month % 12) + 1, 1, tzinfo=UTC
        )
    return tuple(instants)


def effective_model_index(effective: tuple[int, ...], signal_us: int) -> int:
    """Index of the most recent monthly model already effective at ``signal_us``."""
    position = bisect.bisect_right(effective, signal_us) - 1
    if position < 0:
        raise MacroDataError("no monthly model is effective at this signal hour")
    return position


__all__ = [
    "CUTOFF_US",
    "FEATURE_VERSION",
    "MACRO_FEATURES",
    "MacroDataError",
    "MacroFeatureSource",
    "MacroRow",
    "availability_boundary",
    "effective_model_index",
    "independent_asof",
    "load_macro_source",
    "monthly_effective_instants",
    "verified_records",
]
