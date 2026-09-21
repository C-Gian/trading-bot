"""Release-state ALFRED snapshots and the frozen 13-feature macro vector, V2 semantics.

The predecessor module `macro_vintage_source` is untouched and remains the record of
`PREDICTIVE-STAGE3-MACRO-VINTAGE-V1`. This module implements the one authorized prospective
remediation described by `docs/contracts/PREDICTIVE_MACRO_RELEASE_STATE_V1.md`.

The point-in-time reconstruction is identical: a decision at `T` sees only records whose
conservative `availability_time` is not later than `T`, so a later vintage can change only
decisions at or after its own availability boundary.

What changes is the meaning of *current*. A low-frequency release describes a period that
closed before it was published, so the gap between `T` and the observation period date says
nothing about whether a newer release exists. The current known level is therefore the value
on the greatest observation date present in the as-of-`T` snapshot, and it persists until a
newer observation date actually becomes available. Nothing is interpolated, forward-dated or
read from a later revision; the persisted number is a real release already seen at `T`.

Historical anchors keep a tolerance, but that tolerance is measured against the intended
historical anchor date, never against `T`.
"""

from __future__ import annotations

import hashlib
import json
import math
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]

SOURCE_VERSION = "ALFRED_MACRO_CONTEXT_V1"
RELEASE_STATE_VERSION = "MACRO_RELEASE_STATE_V1"
FEATURE_SET_VERSION = "PREDICTIVE_MACRO_VINTAGE_FEATURES_V2"
PREDECESSOR_FEATURE_SET_VERSION = "PREDICTIVE_MACRO_VINTAGE_FEATURES_V1"
CONTRACT_PATH = "docs/contracts/PREDICTIVE_MACRO_RELEASE_STATE_V1.md"
PREDECESSOR_CONTRACT_PATH = "docs/contracts/PREDICTIVE_MACRO_VINTAGE_CONTEXT_V1.md"
POINT_IN_TIME_CONTRACT = "docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md"
MANIFEST_PATH = "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json"
CATALOG_PATH = "research/exogenous/ALFRED_SERIES_CATALOG_V1.json"
SUBSTRATE_PATH = "data/derived/ALFRED-macro-context-v1.parquet"

SERIES = ("DFF", "DGS10", "T10Y2Y", "VIXCLS", "NFCI", "WALCL", "CPIAUCSL", "UNRATE")
AVAILABILITY_RULE = "NEXT_CALENDAR_DAY_00_00_UTC_AFTER_VINTAGE_START"
DEVELOPMENT_CEILING = "2024-12-31T23:59:00Z"
DEVELOPMENT_CEILING_SECONDS = 1_735_689_540
HOUR_SECONDS = 3600

FEATURE_NAMES = (
    "DFF_LEVEL",
    "DFF_DELTA_30D",
    "DGS10_LEVEL",
    "DGS10_DELTA_30D",
    "T10Y2Y_LEVEL",
    "T10Y2Y_DELTA_30D",
    "LOG_VIX_LEVEL",
    "VIX_LOG_CHANGE_5D",
    "NFCI_LEVEL",
    "NFCI_DELTA_28D",
    "WALCL_LOG_CHANGE_28D",
    "CPI_YOY_LOG_CHANGE",
    "UNRATE_DELTA_3M",
)
FEATURE_COUNT = len(FEATURE_NAMES)

FREQUENCY = {
    "DFF": "DAILY",
    "DGS10": "DAILY",
    "T10Y2Y": "DAILY",
    "VIXCLS": "DAILY",
    "NFCI": "WEEKLY",
    "WALCL": "WEEKLY",
    "CPIAUCSL": "MONTHLY",
    "UNRATE": "MONTHLY",
}

# Source-integrity limits on the release calendar itself. They are never applied to the gap
# between a decision time and the current observation period date.
SOURCE_CADENCE_LIMIT_DAYS = {"DAILY": 10, "WEEKLY": 21, "MONTHLY": 70}

# (series, label, offset days, tolerance days) measured against the intended historical anchor.
HISTORICAL_ANCHORS = (
    ("DFF", "30D", 30, 7),
    ("DGS10", "30D", 30, 7),
    ("T10Y2Y", "30D", 30, 7),
    ("VIXCLS", "5D", 5, 7),
    ("NFCI", "28D", 28, 14),
    ("WALCL", "28D", 28, 14),
)
EXACT_MONTH_ANCHORS = (("CPIAUCSL", "12M_EXACT", 12), ("UNRATE", "3M_EXACT", 3))

UNAVAILABILITY_TAXONOMY = (
    tuple(f"{series}_CURRENT_RELEASE_STATE_UNAVAILABLE" for series in SERIES)
    + tuple(f"{series}_{label}_HISTORICAL_ANCHOR_UNAVAILABLE" for series, label, _, _ in HISTORICAL_ANCHORS)
    + tuple(f"{series}_{label}_ANCHOR_UNAVAILABLE" for series, label, _ in EXACT_MONTH_ANCHORS)
    + (
        "VIXCLS_NON_POSITIVE_LEVEL",
        "WALCL_NON_POSITIVE_LEVEL",
        "CPIAUCSL_NON_POSITIVE_LEVEL",
        "NON_FINITE_MACRO_FEATURE",
    )
)


class MacroReleaseStateError(RuntimeError):
    """The admitted ALFRED source cannot satisfy the frozen release-state contract."""


@dataclass(frozen=True)
class VintageRecord:
    available: int
    observation: date
    value: float


@dataclass(frozen=True)
class Snapshot:
    """One immutable as-of-`T` state of a single series."""

    values: dict[date, float]
    observations: tuple[date, ...]


def months_earlier(value: date, months: int) -> date:
    year = value.year
    month = value.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, value.day)


class MacroReleaseStateSource:
    """Availability-indexed immutable snapshots with persistent current release state."""

    def __init__(self, records: dict[str, list[VintageRecord]]):
        missing = [name for name in SERIES if not records.get(name)]
        if missing:
            raise MacroReleaseStateError(f"missing ALFRED series: {missing}")
        self.available: dict[str, list[int]] = {}
        self.snapshots: dict[str, list[Snapshot]] = {}
        self.observation_dates: dict[str, tuple[date, ...]] = {}
        for series in SERIES:
            ordered = sorted(records[series], key=lambda row: (row.available, row.observation))
            state: dict[date, float] = {}
            times: list[int] = []
            snapshots: list[Snapshot] = []
            for index, row in enumerate(ordered):
                state[row.observation] = row.value
                if index + 1 < len(ordered) and ordered[index + 1].available == row.available:
                    continue
                times.append(row.available)
                snapshots.append(Snapshot(values=dict(state), observations=tuple(sorted(state))))
            self.available[series] = times
            self.snapshots[series] = snapshots
            self.observation_dates[series] = tuple(sorted({row.observation for row in ordered}))
        self._cache: dict[int, tuple[tuple[float, ...] | None, str | None]] = {}

    def snapshot(self, series: str, instant: int) -> Snapshot:
        """Everything this series had published and available at `instant`, and nothing else."""
        index = bisect_right(self.available[series], instant) - 1
        if index < 0:
            return Snapshot(values={}, observations=())
        return self.snapshots[series][index]

    def current_release(self, series: str, instant: int) -> tuple[date, float] | None:
        """The greatest observation date in the as-of-`T` snapshot, and its value.

        This is the market's current known state. It is never rejected for being older than
        some number of days relative to the decision time: until a newer release becomes
        available, this really is the latest published value.
        """
        state = self.snapshot(series, instant)
        if not state.observations:
            return None
        observation = state.observations[-1]
        return observation, float(state.values[observation])

    def historical_anchor(
        self, state: Snapshot, anchor: date, tolerance_days: int
    ) -> tuple[date, float] | None:
        """The latest observation on or before an intended historical anchor date."""
        index = bisect_right(state.observations, anchor) - 1
        if index < 0:
            return None
        observed = state.observations[index]
        if (anchor - observed).days > tolerance_days:
            return None
        return observed, float(state.values[observed])

    def at(self, instant: int) -> tuple[tuple[float, ...] | None, str | None]:
        if instant % HOUR_SECONDS or instant > DEVELOPMENT_CEILING_SECONDS:
            raise MacroReleaseStateError("macro decision timestamp is misaligned or post-cutoff")
        if instant not in self._cache:
            self._cache[instant] = self._build(instant)
        return self._cache[instant]

    def _build(self, instant: int) -> tuple[tuple[float, ...] | None, str | None]:
        decision_date = datetime.fromtimestamp(instant, UTC).date()
        states = {series: self.snapshot(series, instant) for series in SERIES}

        current: dict[str, tuple[date, float]] = {}
        for series in SERIES:
            found = self.current_release(series, instant)
            if found is None:
                return None, f"{series}_CURRENT_RELEASE_STATE_UNAVAILABLE"
            current[series] = found

        earlier: dict[str, float] = {}
        for series, label, offset, tolerance in HISTORICAL_ANCHORS:
            anchor = self.historical_anchor(
                states[series], decision_date - timedelta(days=offset), tolerance
            )
            if anchor is None:
                return None, f"{series}_{label}_HISTORICAL_ANCHOR_UNAVAILABLE"
            earlier[series] = anchor[1]

        exact: dict[str, float] = {}
        for series, label, months in EXACT_MONTH_ANCHORS:
            target = months_earlier(current[series][0], months)
            value = states[series].values.get(target)
            if value is None:
                return None, f"{series}_{label}_ANCHOR_UNAVAILABLE"
            exact[series] = float(value)

        if current["VIXCLS"][1] <= 0 or earlier["VIXCLS"] <= 0:
            return None, "VIXCLS_NON_POSITIVE_LEVEL"
        if current["WALCL"][1] <= 0 or earlier["WALCL"] <= 0:
            return None, "WALCL_NON_POSITIVE_LEVEL"
        if current["CPIAUCSL"][1] <= 0 or exact["CPIAUCSL"] <= 0:
            return None, "CPIAUCSL_NON_POSITIVE_LEVEL"

        values = (
            current["DFF"][1],
            current["DFF"][1] - earlier["DFF"],
            current["DGS10"][1],
            current["DGS10"][1] - earlier["DGS10"],
            current["T10Y2Y"][1],
            current["T10Y2Y"][1] - earlier["T10Y2Y"],
            math.log(current["VIXCLS"][1]),
            math.log(current["VIXCLS"][1] / earlier["VIXCLS"]),
            current["NFCI"][1],
            current["NFCI"][1] - earlier["NFCI"],
            math.log(current["WALCL"][1] / earlier["WALCL"]),
            math.log(current["CPIAUCSL"][1] / exact["CPIAUCSL"]),
            current["UNRATE"][1] - exact["UNRATE"],
        )
        if len(values) != FEATURE_COUNT:
            raise MacroReleaseStateError("the frozen macro feature width changed")
        if not all(math.isfinite(value) for value in values):
            return None, "NON_FINITE_MACRO_FEATURE"
        return tuple(float(value) for value in values), None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest_record(root: Path = ROOT) -> dict[str, Any]:
    return json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))


def catalog_record(root: Path = ROOT) -> dict[str, Any]:
    return json.loads((root / CATALOG_PATH).read_text(encoding="utf-8"))


def verified_records(root: Path = ROOT) -> list[dict[str, Any]]:
    """Re-verify the hash-pinned ALFRED substrate on every load; never trust the file alone."""
    manifest = manifest_record(root)
    catalog = catalog_record(root)
    if (
        manifest["version"] != SOURCE_VERSION
        or manifest["manifest_id"] != "ALFRED-MACRO-CONTEXT-DEV-v1"
    ):
        raise MacroReleaseStateError("ALFRED manifest identity changed")
    if tuple(manifest["series"]) != SERIES:
        raise MacroReleaseStateError("ALFRED manifest series changed")
    if tuple(row["series_id"] for row in catalog["series"]) != SERIES:
        raise MacroReleaseStateError("ALFRED catalog series changed")
    if _sha256(root / CATALOG_PATH) != manifest["series_catalog_sha256"]:
        raise MacroReleaseStateError("ALFRED catalog hash mismatch")
    if manifest["availability_rule"] != AVAILABILITY_RULE:
        raise MacroReleaseStateError("ALFRED availability rule changed")
    if manifest["current_revised_substitution"] or manifest["post_2024_vintages"] != 0:
        raise MacroReleaseStateError("inadmissible ALFRED revision or post-cutoff state")
    artifact = manifest["file"]
    path = root / artifact["path"]
    if path != root / SUBSTRATE_PATH or _sha256(path) != artifact["file_sha256"]:
        raise MacroReleaseStateError("ALFRED canonical artifact identity mismatch")
    records = pq.read_table(path).to_pylist()
    for row in records:
        available = row["availability_time"]
        expected = datetime.combine(
            row["vintage_start"] + timedelta(days=1), datetime.min.time(), UTC
        )
        if available.astimezone(UTC) != expected:
            raise MacroReleaseStateError("an ALFRED record violates next-day availability")
        # A 2024-12-31 vintage becomes conservatively available on 2025-01-01 and is retained
        # for audit identity, but can never enter a development timestamp.
        if row["vintage_start"] > date(2024, 12, 31):
            raise MacroReleaseStateError("an ALFRED vintage is post-cutoff")
    return records


def group_records(records: Sequence[dict[str, Any]]) -> dict[str, list[VintageRecord]]:
    grouped: dict[str, list[VintageRecord]] = {series: [] for series in SERIES}
    for row in records:
        grouped[row["series_id"]].append(
            VintageRecord(
                available=int(row["availability_time"].timestamp()),
                observation=row["observation_date"],
                value=float(row["value"]),
            )
        )
    return grouped


def load_release_state_source(root: Path = ROOT) -> MacroReleaseStateSource:
    return MacroReleaseStateSource(group_records(verified_records(root)))


def cadence_findings(source: MacroReleaseStateSource) -> dict[str, Any]:
    """Prove the admitted release calendar is not silently frozen or truncated."""
    by_series: dict[str, Any] = {}
    for series in SERIES:
        observations = source.observation_dates[series]
        gaps = [
            (observations[index + 1] - observations[index]).days
            for index in range(len(observations) - 1)
        ]
        limit = SOURCE_CADENCE_LIMIT_DAYS[FREQUENCY[series]]
        largest = max(gaps) if gaps else 0
        by_series[series] = {
            "frequency": FREQUENCY[series],
            "observation_dates": len(observations),
            "first_observation_date": observations[0].isoformat() if observations else None,
            "last_observation_date": observations[-1].isoformat() if observations else None,
            "maximum_observation_gap_days": largest,
            "maximum_allowed_gap_days": limit,
            "passed": bool(observations) and largest <= limit,
        }
    return {
        "passed": all(record["passed"] for record in by_series.values()),
        "limits": dict(SOURCE_CADENCE_LIMIT_DAYS),
        "by_series": by_series,
        "semantics": "SOURCE_RELEASE_CALENDAR_INTEGRITY_NOT_A_PER_DECISION_EXPIRY_RULE",
    }


def availability_map(
    source: MacroReleaseStateSource, instants: Sequence[int]
) -> tuple[dict[int, tuple[float, ...]], dict[str, int]]:
    cache: dict[int, tuple[float, ...]] = {}
    reasons = dict.fromkeys(UNAVAILABILITY_TAXONOMY, 0)
    for instant in instants:
        values, reason = source.at(instant)
        if values is None:
            reasons[str(reason)] += 1
        else:
            cache[instant] = values
    return cache, reasons


def first_available_instant(
    source: MacroReleaseStateSource, start: int, end: int
) -> int | None:
    for instant in range(start, end + HOUR_SECONDS, HOUR_SECONDS):
        if source.at(instant)[0] is not None:
            return instant
    return None


def source_identity(root: Path = ROOT) -> dict[str, Any]:
    manifest = manifest_record(root)
    return {
        "version": SOURCE_VERSION,
        "release_state_version": RELEASE_STATE_VERSION,
        "source_family": "ALFRED",
        "manifest": MANIFEST_PATH,
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": _sha256(root / MANIFEST_PATH),
        "catalog": CATALOG_PATH,
        "catalog_id": catalog_record(root)["catalog_id"],
        "catalog_sha256": manifest["series_catalog_sha256"],
        "substrate_artifact": manifest["file"]["path"],
        "substrate_file_sha256": manifest["file"]["file_sha256"],
        "substrate_logical_sha256": manifest["file"]["logical_sha256"],
        "substrate_rows": manifest["file"]["rows"],
        "series": list(SERIES),
        "availability_rule": AVAILABILITY_RULE,
        "predictive_contract": CONTRACT_PATH,
        "predecessor_predictive_contract": PREDECESSOR_CONTRACT_PATH,
        "point_in_time_contract": POINT_IN_TIME_CONTRACT,
        "current_revised_substitution": False,
        "post_2024_vintages": 0,
        "interpolation": False,
        "nearest_future_substitution": False,
        "forward_filled_observation_dates": False,
        "current_state_rule": "GREATEST_OBSERVATION_DATE_IN_THE_AS_OF_T_SNAPSHOT",
        "current_state_expiry_relative_to_decision_time": False,
        "historical_anchor_tolerance_days": {
            f"{series}_{label}": tolerance for series, label, _, tolerance in HISTORICAL_ANCHORS
        },
        "historical_anchor_offset_days": {
            f"{series}_{label}": offset for series, label, offset, _ in HISTORICAL_ANCHORS
        },
        "exact_month_anchors": {
            f"{series}_{label}": months for series, label, months in EXACT_MONTH_ANCHORS
        },
        "source_cadence_limit_days": dict(SOURCE_CADENCE_LIMIT_DAYS),
        "development_ceiling": DEVELOPMENT_CEILING,
    }


__all__ = [
    "AVAILABILITY_RULE",
    "CATALOG_PATH",
    "CONTRACT_PATH",
    "DEVELOPMENT_CEILING",
    "DEVELOPMENT_CEILING_SECONDS",
    "EXACT_MONTH_ANCHORS",
    "FEATURE_COUNT",
    "FEATURE_NAMES",
    "FEATURE_SET_VERSION",
    "FREQUENCY",
    "HISTORICAL_ANCHORS",
    "HOUR_SECONDS",
    "MANIFEST_PATH",
    "POINT_IN_TIME_CONTRACT",
    "PREDECESSOR_CONTRACT_PATH",
    "PREDECESSOR_FEATURE_SET_VERSION",
    "RELEASE_STATE_VERSION",
    "SERIES",
    "SOURCE_CADENCE_LIMIT_DAYS",
    "SOURCE_VERSION",
    "SUBSTRATE_PATH",
    "MacroReleaseStateError",
    "MacroReleaseStateSource",
    "Snapshot",
    "VintageRecord",
    "availability_map",
    "cadence_findings",
    "catalog_record",
    "first_available_instant",
    "group_records",
    "load_release_state_source",
    "manifest_record",
    "months_earlier",
    "source_identity",
    "verified_records",
]
