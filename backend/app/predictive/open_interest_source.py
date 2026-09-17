"""Official Binance USD-M historical open interest, and the six frozen Stage-2 OI features.

The only admitted source class is the official Binance public data archive
(`data.binance.vision`), `futures/um/daily/metrics/BTCUSDT`, credential-free, development
interval only. Every daily object is verified against the archive's own `.CHECKSUM` file, so
a silently substituted or truncated download cannot enter the canonical artifact.

Only two fields are admitted: the record timestamp and the aggregate perpetual open-interest
**quantity**. `sum_open_interest_value` is deliberately excluded because it mechanically
embeds BTC price, which would stop the family being interpretable as positioning quantity.
The long/short, top-trader and taker ratio columns are not admitted by this experiment.

Availability is strict and fail-closed. At decision instant `T` the OI state is the latest
record with `create_time < T` exactly — a record stamped exactly `T` is unavailable — and
that record must be no older than ten minutes at `T`. There is no interpolation and no
forward fill beyond that as-of rule.
"""

from __future__ import annotations

import bisect
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

SOURCE_VERSION = "BINANCE_USDM_OPEN_INTEREST_METRICS_V1"
FEATURE_SET_VERSION = "PREDICTIVE_OPEN_INTEREST_FEATURES_V1"
CONTRACT_PATH = "docs/contracts/PREDICTIVE_OPEN_INTEREST_STRUCTURE_V1.md"
MANIFEST_PATH = "data/manifests/BTCUSDT-USDM-OPEN-INTEREST-DEV-v1.json"
CANONICAL_PATH = "data/derived/BTCUSDT-USDM-open-interest-5m-v1.parquet"
RAW_ROOT = "data/raw/open-interest/binance-um-metrics/BTCUSDT"

SOURCE_NAME = "BINANCE_USDM_FUTURES_OFFICIAL_PUBLIC_DATA_ARCHIVE"
ARCHIVE_HOST = "https://data.binance.vision"
ARCHIVE_PREFIX = "data/futures/um/daily/metrics/BTCUSDT"
SYMBOL = "BTCUSDT"

# The archive's own column order. Only the first and third are admitted.
ARCHIVE_COLUMNS = (
    "create_time",
    "symbol",
    "sum_open_interest",
    "sum_open_interest_value",
    "count_toptrader_long_short_ratio",
    "sum_toptrader_long_short_ratio",
    "count_long_short_ratio",
    "sum_taker_long_short_vol_ratio",
)
ADMITTED_COLUMNS = ("create_time", "sum_open_interest")
FORBIDDEN_COLUMNS = tuple(
    name for name in ARCHIVE_COLUMNS if name not in {*ADMITTED_COLUMNS, "symbol"}
)

CADENCE_SECONDS = 300
RECORDS_PER_DAY = 86_400 // CADENCE_SECONDS
MAXIMUM_STATE_AGE_SECONDS = 600
DEVELOPMENT_CEILING = "2024-12-31T23:59:59.999Z"
DEVELOPMENT_CEILING_SECONDS = 1_735_689_599

# Every hour in `T-24h .. T` must carry a valid state, so a vector reads 25 hourly states.
LOOKBACK_HOURS = 24
REQUIRED_STATES = LOOKBACK_HOURS + 1
HOUR_SECONDS = 3600

FEATURE_NAMES = (
    "OI_LOG_CHANGE_1H",
    "OI_LOG_CHANGE_4H",
    "OI_LOG_CHANGE_24H",
    "OI_LOG_LEVEL_Z24",
    "OI_LOG_DIFF_VOL24",
    "OI_LOG_TREND24",
)
FEATURE_COUNT = len(FEATURE_NAMES)

ZERO_DISPERSION_Z_VALUE = 0.0

# Ordered, mutually exclusive: the first rule that fires owns the instant.
NO_PRIOR_OPEN_INTEREST_RECORD = "NO_PRIOR_OPEN_INTEREST_RECORD"
OPEN_INTEREST_STATE_TOO_STALE = "OPEN_INTEREST_STATE_TOO_STALE"
NON_POSITIVE_OPEN_INTEREST = "NON_POSITIVE_OPEN_INTEREST"
NON_FINITE_OPEN_INTEREST_FEATURE = "NON_FINITE_OPEN_INTEREST_FEATURE"

UNAVAILABILITY_TAXONOMY = (
    NO_PRIOR_OPEN_INTEREST_RECORD,
    OPEN_INTEREST_STATE_TOO_STALE,
    NON_POSITIVE_OPEN_INTEREST,
    NON_FINITE_OPEN_INTEREST_FEATURE,
)


class OpenInterestError(RuntimeError):
    """The open-interest substrate is not usable as the frozen contract specifies."""


@dataclass(frozen=True)
class OpenInterestSource:
    """A strictly increasing 5-minute open-interest timeline in epoch seconds."""

    times: tuple[int, ...]
    quantities: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.times or len(self.times) != len(self.quantities):
            raise OpenInterestError("the open-interest timeline needs aligned, non-empty records")
        if any(later <= earlier for earlier, later in zip(self.times, self.times[1:])):
            raise OpenInterestError("the open-interest timeline is not strictly increasing")

    def state_at(self, instant: int) -> tuple[int, float] | None:
        """The latest record strictly before `instant`, or None when there is none.

        `bisect_left` on the exact decision instant is what makes a record stamped exactly at
        `T` unavailable: it lands on that record, and the state is taken before it.
        """
        index = bisect.bisect_left(self.times, instant) - 1
        if index < 0:
            return None
        return self.times[index], self.quantities[index]


def hourly_state(source: OpenInterestSource, instant: int) -> tuple[float | None, str | None]:
    """The as-of open-interest state at one hourly instant, or why it is unavailable."""
    record = source.state_at(instant)
    if record is None:
        return None, NO_PRIOR_OPEN_INTEREST_RECORD
    stamped, quantity = record
    if instant - stamped > MAXIMUM_STATE_AGE_SECONDS:
        return None, OPEN_INTEREST_STATE_TOO_STALE
    if not math.isfinite(quantity) or quantity <= 0.0:
        return None, NON_POSITIVE_OPEN_INTEREST
    return quantity, None


def state_window(
    source: OpenInterestSource, instant: int
) -> tuple[tuple[float, ...] | None, str | None]:
    """The 25 hourly states `T-24h .. T`, oldest first, or why the window is unavailable."""
    states: list[float] = []
    for offset in range(LOOKBACK_HOURS, -1, -1):
        value, reason = hourly_state(source, instant - offset * HOUR_SECONDS)
        if value is None:
            return None, reason
        states.append(value)
    return tuple(states), None


def _population_std(values: Sequence[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _ols_slope(values: Sequence[float]) -> float:
    """Slope of `values` on the integer index 0..n-1. The index mean/variance are exact."""
    count = len(values)
    index_mean = (count - 1) / 2
    value_mean = sum(values) / count
    covariance = sum(
        (index - index_mean) * (value - value_mean) for index, value in enumerate(values)
    )
    variance = sum((index - index_mean) ** 2 for index in range(count))
    return covariance / variance


def build_open_interest_features(
    source: OpenInterestSource, instant: int
) -> tuple[tuple[float, ...] | None, str | None]:
    """Build the six frozen features at `instant`, or say exactly why they are unavailable.

    Returns `(values, None)` when available and `(None, reason)` when not. An unavailable
    evaluation instant becomes a counted abstention; an unavailable training instant is
    excluded from fitting and counted. Neither is ever imputed.
    """
    states, reason = state_window(source, instant)
    if states is None:
        return None, reason
    logs = [math.log(value) for value in states]
    latest = logs[-1]
    differences = [later - earlier for earlier, later in zip(logs, logs[1:])]
    dispersion = _population_std(logs)

    values = (
        latest - logs[-2],
        latest - logs[-5],
        latest - logs[0],
        ZERO_DISPERSION_Z_VALUE
        if dispersion == 0.0
        else (latest - sum(logs) / len(logs)) / dispersion,
        _population_std(differences),
        _ols_slope(logs),
    )
    if len(values) != FEATURE_COUNT:
        raise OpenInterestError("the frozen open-interest feature vector changed width")
    if any(not math.isfinite(value) for value in values):
        return None, NON_FINITE_OPEN_INTEREST_FEATURE
    return values, None


def feature_source_times(source: OpenInterestSource, instant: int) -> tuple[int, ...]:
    """Exactly the record timestamps a vector at `instant` may read, oldest first."""
    stamps: list[int] = []
    for offset in range(LOOKBACK_HOURS, -1, -1):
        record = source.state_at(instant - offset * HOUR_SECONDS)
        if record is None:
            return ()
        stamps.append(record[0])
    return tuple(stamps)


def parse_metrics_csv(text: str) -> list[tuple[int, float]]:
    """Parse one official daily metrics CSV into admitted `(epoch_seconds, quantity)` rows.

    The header must be the archive's exact column order, so a schema change upstream fails
    the parse instead of silently shifting a column into the admitted field.
    """
    from datetime import UTC, datetime

    lines = [line for line in text.replace("\r\n", "\n").split("\n") if line]
    if not lines:
        raise OpenInterestError("an official metrics file is empty")
    header = tuple(name.strip() for name in lines[0].split(","))
    if header != ARCHIVE_COLUMNS:
        raise OpenInterestError(f"the official metrics schema drifted: {header}")
    rows: list[tuple[int, float]] = []
    for line in lines[1:]:
        fields = line.split(",")
        if len(fields) != len(ARCHIVE_COLUMNS):
            raise OpenInterestError("an official metrics row has the wrong field count")
        if fields[1] != SYMBOL:
            raise OpenInterestError(f"an official metrics row is not {SYMBOL}")
        stamped = datetime.strptime(fields[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        rows.append((int(stamped.timestamp()), float(fields[2])))
    return rows


def load_open_interest(root: Path = ROOT) -> OpenInterestSource:
    """Read the canonical artifact, verifying the manifest hash and the development ceiling."""
    import hashlib

    import pyarrow.parquet as pq

    manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    path = root / manifest["canonical"]["path"]
    if not path.is_file():
        raise OpenInterestError(f"the canonical open-interest artifact is not installed: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != manifest["canonical"]["file_sha256"]:
        raise OpenInterestError("canonical open-interest artifact hash mismatch")
    table = pq.read_table(path)
    if table.column_names != list(ADMITTED_COLUMNS):
        raise OpenInterestError("canonical open-interest columns drifted")
    times = [int(value) for value in table["create_time"].to_pylist()]
    quantities = [float(value) for value in table["sum_open_interest"].to_pylist()]
    if times and max(times) > DEVELOPMENT_CEILING_SECONDS:
        raise OpenInterestError("the canonical artifact contains a post-cutoff record")
    return OpenInterestSource(times=tuple(times), quantities=tuple(quantities))


def source_identity(root: Path = ROOT) -> dict[str, Any]:
    """The admitted source identity, copied from the manifest rather than restated."""
    manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    canonical = manifest["canonical"]
    return {
        "version": manifest["version"],
        "manifest": MANIFEST_PATH,
        "manifest_id": manifest["manifest_id"],
        "predictive_contract": CONTRACT_PATH,
        "canonical_artifact": canonical["path"],
        "canonical_file_sha256": canonical["file_sha256"],
        "records": manifest["records"],
        "first_record": manifest["first_record"],
        "last_record": manifest["last_record"],
        "source": manifest["source"]["name"],
        "source_class": manifest["source"]["class"],
        "credential_free": manifest["source"]["credential_free"],
        "archive_days": manifest["archive"]["days"],
        "archive_index_sha256": manifest["archive"]["index_sha256"],
        "official_checksums_verified": manifest["archive"]["official_checksums_verified"],
        "cadence_seconds": manifest["cadence"]["seconds"],
        "fields_read": list(ADMITTED_COLUMNS),
        "forbidden_fields": list(FORBIDDEN_COLUMNS),
        "open_interest_value_admitted": False,
        "availability_rule": "CREATE_TIME_STRICTLY_BEFORE_DECISION_INSTANT",
        "maximum_state_age_seconds": MAXIMUM_STATE_AGE_SECONDS,
        "interpolation": False,
        "forward_fill": False,
        "development_ceiling": DEVELOPMENT_CEILING,
        "post_cutoff_records": manifest["integrity"]["post_cutoff_records"],
        "third_party_vendor_used": False,
        "rest_snapshot_history_used": False,
        "reconstructed_or_backfilled": False,
    }


def manifest_record(root: Path = ROOT) -> Mapping[str, Any]:
    return json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))


__all__ = [
    "ADMITTED_COLUMNS",
    "ARCHIVE_COLUMNS",
    "ARCHIVE_HOST",
    "ARCHIVE_PREFIX",
    "CADENCE_SECONDS",
    "CANONICAL_PATH",
    "CONTRACT_PATH",
    "DEVELOPMENT_CEILING",
    "DEVELOPMENT_CEILING_SECONDS",
    "FEATURE_COUNT",
    "FEATURE_NAMES",
    "FEATURE_SET_VERSION",
    "FORBIDDEN_COLUMNS",
    "LOOKBACK_HOURS",
    "MANIFEST_PATH",
    "MAXIMUM_STATE_AGE_SECONDS",
    "NON_FINITE_OPEN_INTEREST_FEATURE",
    "NON_POSITIVE_OPEN_INTEREST",
    "NO_PRIOR_OPEN_INTEREST_RECORD",
    "OPEN_INTEREST_STATE_TOO_STALE",
    "RAW_ROOT",
    "RECORDS_PER_DAY",
    "REQUIRED_STATES",
    "SOURCE_NAME",
    "SOURCE_VERSION",
    "SYMBOL",
    "UNAVAILABILITY_TAXONOMY",
    "OpenInterestError",
    "OpenInterestSource",
    "build_open_interest_features",
    "feature_source_times",
    "hourly_state",
    "load_open_interest",
    "manifest_record",
    "parse_metrics_csv",
    "source_identity",
    "state_window",
]
