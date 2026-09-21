"""Strict point-in-time ALFRED snapshots and the frozen 13-feature macro vector.

Every lookup first reconstructs the complete state whose conservative
``availability_time`` is not later than the BTC decision timestamp.  Anchor lookups are
then performed inside that state.  A later vintage can therefore change only decisions at
or after its own availability boundary; current-revised FRED data is never consulted.
"""

from __future__ import annotations

import hashlib
import json
import math
from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]

SOURCE_VERSION = "ALFRED_MACRO_CONTEXT_V1"
FEATURE_SET_VERSION = "PREDICTIVE_MACRO_VINTAGE_FEATURES_V1"
CONTRACT_PATH = "docs/contracts/PREDICTIVE_MACRO_VINTAGE_CONTEXT_V1.md"
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

MAX_AGE_DAYS = {"DAILY": 7, "WEEKLY": 14, "MONTHLY": 45}
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

ANCHORS = (
    ("DFF", "CURRENT"),
    ("DFF", "30D"),
    ("DGS10", "CURRENT"),
    ("DGS10", "30D"),
    ("T10Y2Y", "CURRENT"),
    ("T10Y2Y", "30D"),
    ("VIXCLS", "CURRENT"),
    ("VIXCLS", "5D"),
    ("NFCI", "CURRENT"),
    ("NFCI", "28D"),
    ("WALCL", "CURRENT"),
    ("WALCL", "28D"),
    ("CPIAUCSL", "CURRENT"),
    ("CPIAUCSL", "12M_EXACT"),
    ("UNRATE", "CURRENT"),
    ("UNRATE", "3M_EXACT"),
)
UNAVAILABILITY_TAXONOMY = tuple(
    f"{series}_{anchor}_ANCHOR_UNAVAILABLE_OR_STALE" for series, anchor in ANCHORS
) + (
    "VIXCLS_NON_POSITIVE_LEVEL",
    "WALCL_NON_POSITIVE_LEVEL",
    "CPIAUCSL_NON_POSITIVE_LEVEL",
    "NON_FINITE_MACRO_FEATURE",
)


class MacroVintageError(RuntimeError):
    """The admitted ALFRED source cannot satisfy the frozen predictive contract."""


@dataclass(frozen=True)
class VintageRecord:
    available: int
    observation: date
    value: float


def _months_earlier(value: date, months: int) -> date:
    year = value.year
    month = value.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, value.day)


class MacroVintageSource:
    """Availability-indexed immutable snapshots for all eight admitted series."""

    def __init__(self, records: dict[str, list[VintageRecord]]):
        missing = [name for name in SERIES if not records.get(name)]
        if missing:
            raise MacroVintageError(f"missing ALFRED series: {missing}")
        self.available: dict[str, list[int]] = {}
        self.snapshots: dict[str, list[dict[date, float]]] = {}
        for series in SERIES:
            ordered = sorted(records[series], key=lambda row: (row.available, row.observation))
            state: dict[date, float] = {}
            times: list[int] = []
            snapshots: list[dict[date, float]] = []
            for index, row in enumerate(ordered):
                state[row.observation] = row.value
                if index + 1 < len(ordered) and ordered[index + 1].available == row.available:
                    continue
                times.append(row.available)
                snapshots.append(dict(state))
            self.available[series] = times
            self.snapshots[series] = snapshots
        self._cache: dict[int, tuple[tuple[float, ...] | None, str | None]] = {}
        self._dates_cache: dict[int, tuple[date, ...]] = {}

    def state(self, series: str, instant: int) -> dict[date, float]:
        index = bisect_right(self.available[series], instant) - 1
        return {} if index < 0 else self.snapshots[series][index]

    def lookup(
        self, state: dict[date, float], anchor: date, maximum_age_days: int
    ) -> tuple[date, float] | None:
        identity = id(state)
        ordered = self._dates_cache.get(identity)
        if ordered is None:
            ordered = tuple(sorted(state))
            self._dates_cache[identity] = ordered
        index = bisect_right(ordered, anchor) - 1
        if index < 0:
            return None
        observed = ordered[index]
        if (anchor - observed).days > maximum_age_days:
            return None
        return observed, float(state[observed])

    def _anchor(
        self, series: str, state: dict[date, float], anchor: date, label: str
    ) -> tuple[date, float] | tuple[None, str]:
        found = self.lookup(state, anchor, MAX_AGE_DAYS[FREQUENCY[series]])
        if found is None:
            return None, f"{series}_{label}_ANCHOR_UNAVAILABLE_OR_STALE"
        return found

    def at(self, instant: int) -> tuple[tuple[float, ...] | None, str | None]:
        if instant % HOUR_SECONDS or instant > DEVELOPMENT_CEILING_SECONDS:
            raise MacroVintageError("macro decision timestamp is misaligned or post-cutoff")
        if instant not in self._cache:
            self._cache[instant] = self._build(instant)
        return self._cache[instant]

    def _build(self, instant: int) -> tuple[tuple[float, ...] | None, str | None]:
        anchor = datetime.fromtimestamp(instant, UTC).date()
        states = {series: self.state(series, instant) for series in SERIES}

        def pair(series: str, days: int, label: str) -> tuple[float, float] | tuple[None, str]:
            current = self._anchor(series, states[series], anchor, "CURRENT")
            if current[0] is None:
                return current
            earlier = self._anchor(series, states[series], anchor - timedelta(days=days), label)
            if earlier[0] is None:
                return earlier
            return float(current[1]), float(earlier[1])

        dff = pair("DFF", 30, "30D")
        if dff[0] is None:
            return dff
        dgs10 = pair("DGS10", 30, "30D")
        if dgs10[0] is None:
            return dgs10
        spread = pair("T10Y2Y", 30, "30D")
        if spread[0] is None:
            return spread
        vix = pair("VIXCLS", 5, "5D")
        if vix[0] is None:
            return vix
        nfci = pair("NFCI", 28, "28D")
        if nfci[0] is None:
            return nfci
        walcl = pair("WALCL", 28, "28D")
        if walcl[0] is None:
            return walcl

        cpi_current = self._anchor("CPIAUCSL", states["CPIAUCSL"], anchor, "CURRENT")
        if cpi_current[0] is None:
            return cpi_current
        cpi_target = _months_earlier(cpi_current[0], 12)
        cpi_prior = states["CPIAUCSL"].get(cpi_target)
        if cpi_prior is None:
            return None, "CPIAUCSL_12M_EXACT_ANCHOR_UNAVAILABLE_OR_STALE"

        unrate_current = self._anchor("UNRATE", states["UNRATE"], anchor, "CURRENT")
        if unrate_current[0] is None:
            return unrate_current
        unrate_target = _months_earlier(unrate_current[0], 3)
        unrate_prior = states["UNRATE"].get(unrate_target)
        if unrate_prior is None:
            return None, "UNRATE_3M_EXACT_ANCHOR_UNAVAILABLE_OR_STALE"

        if vix[0] <= 0 or vix[1] <= 0:
            return None, "VIXCLS_NON_POSITIVE_LEVEL"
        if walcl[0] <= 0 or walcl[1] <= 0:
            return None, "WALCL_NON_POSITIVE_LEVEL"
        if cpi_current[1] <= 0 or cpi_prior <= 0:
            return None, "CPIAUCSL_NON_POSITIVE_LEVEL"

        values = (
            dff[0],
            dff[0] - dff[1],
            dgs10[0],
            dgs10[0] - dgs10[1],
            spread[0],
            spread[0] - spread[1],
            math.log(vix[0]),
            math.log(vix[0] / vix[1]),
            nfci[0],
            nfci[0] - nfci[1],
            math.log(walcl[0] / walcl[1]),
            math.log(float(cpi_current[1]) / float(cpi_prior)),
            float(unrate_current[1]) - float(unrate_prior),
        )
        if len(values) != FEATURE_COUNT:
            raise MacroVintageError("the frozen macro feature width changed")
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
    manifest = manifest_record(root)
    catalog = catalog_record(root)
    if (
        manifest["version"] != SOURCE_VERSION
        or manifest["manifest_id"] != "ALFRED-MACRO-CONTEXT-DEV-v1"
    ):
        raise MacroVintageError("ALFRED manifest identity changed")
    if tuple(manifest["series"]) != SERIES:
        raise MacroVintageError("ALFRED manifest series changed")
    if tuple(row["series_id"] for row in catalog["series"]) != SERIES:
        raise MacroVintageError("ALFRED catalog series changed")
    if _sha256(root / CATALOG_PATH) != manifest["series_catalog_sha256"]:
        raise MacroVintageError("ALFRED catalog hash mismatch")
    if manifest["availability_rule"] != AVAILABILITY_RULE:
        raise MacroVintageError("ALFRED availability rule changed")
    if manifest["current_revised_substitution"] or manifest["post_2024_vintages"] != 0:
        raise MacroVintageError("inadmissible ALFRED revision or post-cutoff state")
    artifact = manifest["file"]
    path = root / artifact["path"]
    if path != root / SUBSTRATE_PATH or _sha256(path) != artifact["file_sha256"]:
        raise MacroVintageError("ALFRED canonical artifact identity mismatch")
    records = pq.read_table(path).to_pylist()
    for row in records:
        available = row["availability_time"]
        expected = datetime.combine(
            row["vintage_start"] + timedelta(days=1), datetime.min.time(), UTC
        )
        if available.astimezone(UTC) != expected:
            raise MacroVintageError("an ALFRED record violates next-day availability")
        # A 2024-12-31 vintage becomes conservatively available on 2025-01-01 and is
        # retained for audit identity, but can never enter a development timestamp.
        if row["vintage_start"] > date(2024, 12, 31):
            raise MacroVintageError("an ALFRED vintage is post-cutoff")
    return records


def load_macro_source(root: Path = ROOT) -> MacroVintageSource:
    grouped: dict[str, list[VintageRecord]] = {series: [] for series in SERIES}
    for row in verified_records(root):
        grouped[row["series_id"]].append(
            VintageRecord(
                available=int(row["availability_time"].timestamp()),
                observation=row["observation_date"],
                value=float(row["value"]),
            )
        )
    return MacroVintageSource(grouped)


def availability_map(
    source: MacroVintageSource, instants: list[int] | tuple[int, ...]
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


def first_available_instant(source: MacroVintageSource, start: int, end: int) -> int | None:
    for instant in range(start, end + HOUR_SECONDS, HOUR_SECONDS):
        if source.at(instant)[0] is not None:
            return instant
    return None


def source_identity(root: Path = ROOT) -> dict[str, Any]:
    manifest = manifest_record(root)
    return {
        "version": SOURCE_VERSION,
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
        "point_in_time_contract": POINT_IN_TIME_CONTRACT,
        "current_revised_substitution": False,
        "post_2024_vintages": 0,
        "interpolation": False,
        "nearest_future_substitution": False,
        "maximum_age_days": dict(MAX_AGE_DAYS),
        "development_ceiling": DEVELOPMENT_CEILING,
    }


__all__ = [
    "AVAILABILITY_RULE",
    "CATALOG_PATH",
    "CONTRACT_PATH",
    "DEVELOPMENT_CEILING",
    "DEVELOPMENT_CEILING_SECONDS",
    "FEATURE_COUNT",
    "FEATURE_NAMES",
    "FEATURE_SET_VERSION",
    "FREQUENCY",
    "HOUR_SECONDS",
    "MANIFEST_PATH",
    "MAX_AGE_DAYS",
    "POINT_IN_TIME_CONTRACT",
    "SERIES",
    "SOURCE_VERSION",
    "SUBSTRATE_PATH",
    "UNAVAILABILITY_TAXONOMY",
    "MacroVintageError",
    "MacroVintageSource",
    "VintageRecord",
    "availability_map",
    "catalog_record",
    "first_available_instant",
    "load_macro_source",
    "manifest_record",
    "source_identity",
    "verified_records",
]
