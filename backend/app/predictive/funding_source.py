"""Strictly-prior settled BTCUSDT USD-M funding, and the five frozen Stage-2 features.

The canonical artifact, its manifest, its integrity check and its credential-free
acquisition provenance are reused unchanged from the superseded generation's tooling. Only
`funding_time` and `funding_rate` are read. Nothing here touches mark price, premium, basis,
open interest, position ratios, or any field absent from the canonical artifact.

Availability is strict and fail-closed. At decision instant `T` a settlement counts only when
`funding_time < T` exactly; a settlement stamped exactly `T` is unavailable. The last nine
strictly-prior settlements must all exist, and every consecutive gap inside those nine
records must be at most eight hours plus sixty seconds. Otherwise the vector is unavailable
and the timestamp becomes a counted abstention. Nothing is interpolated or forward filled.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

FEATURE_SET_VERSION = "PREDICTIVE_SETTLED_FUNDING_FEATURES_V1"
CONTRACT_PATH = "docs/contracts/PREDICTIVE_SETTLED_FUNDING_STRUCTURE_V1.md"
MANIFEST_PATH = "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json"
CANONICAL_PATH = "data/derived/BTCUSDT-USDM-settled-funding-v1.parquet"
SOURCE_NAME = "BINANCE_USDM_FUTURES_PUBLIC_MARKET_DATA"

FEATURE_NAMES = (
    "LATEST_SETTLED_RATE",
    "MEAN_LAST_3_SETTLEMENTS",
    "MEAN_LAST_9_SETTLEMENTS",
    "DELTA_LATEST_PREVIOUS",
    "STD_LAST_9_SETTLEMENTS",
)
FEATURE_COUNT = len(FEATURE_NAMES)

REQUIRED_SETTLEMENTS = 9
# The natural funding cadence is eight hours; sixty seconds of tolerance absorbs exchange
# stamping jitter without ever bridging a missed settlement.
MAX_SETTLEMENT_GAP_SECONDS = 8 * 60 * 60 + 60
MICROSECONDS = 1_000_000

# Ordered, mutually exclusive: the first rule that fires owns the instant.
INSUFFICIENT_PRIOR_SETTLEMENTS = "INSUFFICIENT_PRIOR_SETTLEMENTS"
SETTLEMENT_GAP_TOO_LARGE = "SETTLEMENT_GAP_TOO_LARGE"
NON_FINITE_FUNDING_FEATURE = "NON_FINITE_FUNDING_FEATURE"

UNAVAILABILITY_TAXONOMY = (
    INSUFFICIENT_PRIOR_SETTLEMENTS,
    SETTLEMENT_GAP_TOO_LARGE,
    NON_FINITE_FUNDING_FEATURE,
)

# Explicitly forbidden here, so the guard is a list rather than a promise.
FORBIDDEN_SOURCE_FIELDS = (
    "markPrice",
    "indexPrice",
    "premium",
    "basis",
    "openInterest",
    "longShortRatio",
    "predictedFundingRate",
)


class FundingFeatureError(RuntimeError):
    """The settled-funding substrate is not usable as the frozen contract specifies."""


@dataclass(frozen=True)
class SettledFundingSource:
    """A strictly increasing settled-funding timeline in epoch microseconds."""

    times_us: tuple[int, ...]
    rates: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.times_us or len(self.times_us) != len(self.rates):
            raise FundingFeatureError("the funding timeline needs aligned, non-empty records")
        if any(later <= earlier for earlier, later in zip(self.times_us, self.times_us[1:])):
            raise FundingFeatureError("the funding timeline is not strictly increasing")

    def strictly_prior_window(
        self, instant: int, count: int = REQUIRED_SETTLEMENTS
    ) -> tuple[tuple[int, ...], tuple[float, ...]] | None:
        """The last `count` settlements with `funding_time < instant`, oldest first.

        `bisect_left` on the exact decision instant is what makes a settlement stamped
        exactly at `T` unavailable: it lands at that record, and the window ends before it.
        """
        cutoff = instant * MICROSECONDS
        end = bisect.bisect_left(self.times_us, cutoff)
        if end < count:
            return None
        start = end - count
        return self.times_us[start:end], self.rates[start:end]

    def first_time_us(self) -> int:
        return self.times_us[0]

    def last_time_us(self) -> int:
        return self.times_us[-1]


def _population_std(values: Sequence[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def build_funding_features(
    source: SettledFundingSource, instant: int
) -> tuple[tuple[float, ...] | None, str | None]:
    """Build the five frozen features at `instant`, or say exactly why they are unavailable.

    Returns `(values, None)` when available and `(None, reason)` when not. An unavailable
    evaluation instant becomes a counted abstention; an unavailable training instant is
    excluded from fitting and counted. Neither is ever imputed.
    """
    window = source.strictly_prior_window(instant)
    if window is None:
        return None, INSUFFICIENT_PRIOR_SETTLEMENTS
    times, rates = window
    limit = MAX_SETTLEMENT_GAP_SECONDS * MICROSECONDS
    for earlier, later in zip(times, times[1:]):
        if later - earlier > limit:
            return None, SETTLEMENT_GAP_TOO_LARGE

    values = (
        rates[-1],
        sum(rates[-3:]) / 3,
        sum(rates) / REQUIRED_SETTLEMENTS,
        rates[-1] - rates[-2],
        _population_std(rates),
    )
    if len(values) != FEATURE_COUNT:
        raise FundingFeatureError("the frozen funding feature vector changed width")
    if any(not math.isfinite(value) for value in values):
        return None, NON_FINITE_FUNDING_FEATURE
    return values, None


def feature_source_times(source: SettledFundingSource, instant: int) -> tuple[int, ...]:
    """Exactly the settlement timestamps a vector at `instant` may read, oldest first.

    The whole causal surface of the feature set, so a look-ahead guard can be asserted
    against this tuple rather than against a comment claiming causality.
    """
    window = source.strictly_prior_window(instant)
    return () if window is None else window[0]


def load_settled_funding(root: Path = ROOT) -> SettledFundingSource:
    """Load the canonical artifact through the existing integrity tooling, unchanged.

    `load_funding_context` verifies the manifest hash, the column set and the development
    cutoff. Reusing it means this checkpoint cannot silently read a different artifact than
    the one the manifest admits.
    """
    import sys

    if str(root / "backend") not in sys.path:
        sys.path.insert(0, str(root / "backend"))
    from app.research.funding import load_funding_context

    context = load_funding_context(root)
    return SettledFundingSource(times_us=tuple(context.times_us), rates=tuple(context.rates))


def source_identity(root: Path = ROOT) -> dict[str, Any]:
    """The admitted source identity, copied from the manifest rather than restated."""
    import json

    manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    canonical = manifest["canonical"]
    return {
        "manifest": MANIFEST_PATH,
        "manifest_id": manifest["manifest_id"],
        "historical_contract": manifest["contract"],
        "predictive_contract": CONTRACT_PATH,
        "canonical_artifact": canonical["path"],
        "canonical_file_sha256": canonical["file_sha256"],
        "canonical_logical_sha256": canonical["logical_sha256"],
        "records": manifest["records"],
        "first_funding_time": manifest["first_funding_time"],
        "last_funding_time": manifest["last_funding_time"],
        "source": manifest["source"]["name"],
        "credential_free": manifest["source"]["credential_free"],
        "fields_read": ["funding_time", "funding_rate"],
        "forbidden_fields": list(FORBIDDEN_SOURCE_FIELDS),
        "availability_rule": "FUNDING_TIME_STRICTLY_BEFORE_DECISION_INSTANT",
        "interpolation": False,
        "forward_fill": False,
        "post_cutoff_records": 0,
    }


__all__ = [
    "CANONICAL_PATH",
    "CONTRACT_PATH",
    "FEATURE_COUNT",
    "FEATURE_NAMES",
    "FEATURE_SET_VERSION",
    "FORBIDDEN_SOURCE_FIELDS",
    "INSUFFICIENT_PRIOR_SETTLEMENTS",
    "MANIFEST_PATH",
    "MAX_SETTLEMENT_GAP_SECONDS",
    "MICROSECONDS",
    "NON_FINITE_FUNDING_FEATURE",
    "REQUIRED_SETTLEMENTS",
    "SETTLEMENT_GAP_TOO_LARGE",
    "SOURCE_NAME",
    "UNAVAILABILITY_TAXONOMY",
    "FundingFeatureError",
    "SettledFundingSource",
    "build_funding_features",
    "feature_source_times",
    "load_settled_funding",
    "source_identity",
]
