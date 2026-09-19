"""Official Binance spot USDT cross-section, and the eight frozen Stage-3 breadth features.

The only admitted source class is the official Binance public data archive
(`data.binance.vision`, `data/spot/monthly/klines`, `1h`), already acquired, hashed and
governed by `BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1`. Nothing here downloads anything, and
no historical cross-sectional research result enters this family.

`BTCUSDT` is the prediction target and is removed from the cross-section entirely: the
features describe the rest of the market, never the asset being predicted. Leveraged tokens
are already excluded by the manifest's frozen symbol rule and the exclusion is re-applied
here so the admitted panel cannot drift from it.

Point-in-time membership is the whole design. At a decision instant `T` an asset is usable
only when the four required endpoint bars `T`, `T-1h`, `T-24h` and `T-168h` have all actually
been observed for that asset. There is no interpolation, no forward fill, no nearest-bar
substitution, no reconstruction, and above all **no future-survival filter**: nothing about
an asset's eventual sample length, its eventual liquidity or its total row count over the
complete sample may decide whether it participates at `T`. The retired 504-row participation
idea is not revived here in any form. The universe is therefore recomputed at every instant
and may grow or shrink causally.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]

SOURCE_VERSION = "BINANCE_SPOT_USDT_1H_CROSSSECTION_V1"
FEATURE_SET_VERSION = "PREDICTIVE_CROSS_ASSET_BREADTH_FEATURES_V1"
CONTRACT_PATH = "docs/contracts/PREDICTIVE_CROSS_ASSET_BREADTH_CONTEXT_V1.md"
MANIFEST_PATH = "data/manifests/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.json"
SUBSTRATE_PATH = "data/derived/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.parquet"

SOURCE_NAME = "BINANCE_SPOT_OFFICIAL_PUBLIC_DATA_ARCHIVE"
ARCHIVE_HOST = "https://data.binance.vision"
ARCHIVE_PREFIX = "data/spot/monthly/klines"
KLINE_INTERVAL = "1h"
QUOTE_ASSET = "USDT"
TARGET_SYMBOL = "BTCUSDT"
LEVERAGED_TOKEN_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")

ADMITTED_COLUMNS = ("symbol", "open_time", "close")
FORBIDDEN_COLUMNS = ("open", "high", "low", "volume", "quote_volume")

HOUR_SECONDS = 3600
SHORT_LOOKBACK_HOURS = 1
MEDIUM_LOOKBACK_HOURS = 24
LONG_LOOKBACK_HOURS = 168
# Ordered oldest-first in the window; every one of the four must exist for the same asset.
ENDPOINT_OFFSET_HOURS = (LONG_LOOKBACK_HOURS, MEDIUM_LOOKBACK_HOURS, SHORT_LOOKBACK_HOURS, 0)
REQUIRED_ENDPOINT_BARS = len(ENDPOINT_OFFSET_HOURS)

MINIMUM_POINT_IN_TIME_UNIVERSE = 30

DEVELOPMENT_CEILING = "2024-12-31T23:59:00Z"
DEVELOPMENT_CEILING_SECONDS = 1_735_689_540

FEATURE_NAMES = (
    "BREADTH_UP_SHARE_1H",
    "BREADTH_UP_SHARE_24H",
    "BREADTH_UP_SHARE_168H",
    "CROSS_MEDIAN_RETURN_1H",
    "CROSS_MEDIAN_RETURN_24H",
    "CROSS_MEDIAN_RETURN_168H",
    "CROSS_MAD_RETURN_24H",
    "CROSS_MAD_RETURN_168H",
)
FEATURE_COUNT = len(FEATURE_NAMES)

CROSS_SECTIONAL_WEIGHTING = "EQUAL_WEIGHTED"

# Ordered, mutually exclusive: the first rule that fires owns the instant.
DECISION_INSTANT_OUTSIDE_SOURCE_SPAN = "DECISION_INSTANT_OUTSIDE_SOURCE_SPAN"
INSUFFICIENT_POINT_IN_TIME_UNIVERSE = "INSUFFICIENT_POINT_IN_TIME_UNIVERSE"
NON_FINITE_CROSS_ASSET_FEATURE = "NON_FINITE_CROSS_ASSET_FEATURE"

UNAVAILABILITY_TAXONOMY = (
    DECISION_INSTANT_OUTSIDE_SOURCE_SPAN,
    INSUFFICIENT_POINT_IN_TIME_UNIVERSE,
    NON_FINITE_CROSS_ASSET_FEATURE,
)


class CrossAssetError(RuntimeError):
    """The cross-asset substrate is not usable as the frozen contract specifies."""


def is_leveraged_token(symbol: str) -> bool:
    """The manifest's frozen mechanical rule, re-applied to the admitted panel.

    Literal and non-discretionary: a leveraged suffix immediately preceding the quote asset.
    No judgement about individual assets can enter the universe through this function.
    """
    if not symbol.endswith(QUOTE_ASSET):
        return False
    base = symbol[: -len(QUOTE_ASSET)]
    return any(base.endswith(suffix) for suffix in LEVERAGED_TOKEN_SUFFIXES)


def is_admitted_symbol(symbol: str) -> bool:
    """USDT-quoted, not leveraged, and not the prediction target itself."""
    return (
        symbol.endswith(QUOTE_ASSET)
        and len(symbol) > len(QUOTE_ASSET)
        and symbol != TARGET_SYMBOL
        and not is_leveraged_token(symbol)
    )


@dataclass(frozen=True)
class CrossSectionPanel:
    """Log closes of every admitted non-BTC asset on the hourly grid, `NaN` where unobserved.

    A `NaN` means the bar was never observed for that asset, and it stays `NaN`: there is no
    fill of any kind. The panel is a pure restatement of the governed substrate, so the
    causal content of a decision instant is exactly the rows at or before it.
    """

    symbols: tuple[str, ...]
    first_open_time: int
    log_close: Any

    def __post_init__(self) -> None:
        matrix = self.log_close
        if matrix.ndim != 2 or matrix.shape[1] != len(self.symbols):
            raise CrossAssetError("the cross-section panel does not match its symbol list")
        if self.first_open_time % HOUR_SECONDS:
            raise CrossAssetError("the cross-section panel is not aligned to an hour boundary")
        if len(set(self.symbols)) != len(self.symbols):
            raise CrossAssetError("the cross-section panel carries a duplicate symbol")
        if any(not is_admitted_symbol(symbol) for symbol in self.symbols):
            raise CrossAssetError("the cross-section panel carries an inadmissible symbol")

    @property
    def rows(self) -> int:
        return int(self.log_close.shape[0])

    @property
    def last_open_time(self) -> int:
        return self.first_open_time + (self.rows - 1) * HOUR_SECONDS

    def row_index(self, instant: int) -> int:
        if instant % HOUR_SECONDS:
            raise CrossAssetError("a decision instant is not aligned to an hour boundary")
        return (instant - self.first_open_time) // HOUR_SECONDS


def panel_from_series(series: Mapping[str, Mapping[int, float]]) -> CrossSectionPanel:
    """Build a panel from explicit per-symbol `{open_time: close}` series.

    Used by the deterministic tests and by the loader, so both travel the same code path.
    Only strictly positive, finite closes become observations; anything else stays `NaN`.
    """
    observed = [moment for values in series.values() for moment in values]
    if not observed:
        raise CrossAssetError("the cross-section panel has no observation at all")
    first, last = min(observed), max(observed)
    if first % HOUR_SECONDS or last % HOUR_SECONDS:
        raise CrossAssetError("a cross-section bar is not aligned to an hour boundary")
    symbols = tuple(sorted(series))
    rows = (last - first) // HOUR_SECONDS + 1
    matrix = np.full((rows, len(symbols)), np.nan, dtype=np.float64)
    for column, symbol in enumerate(symbols):
        for moment, close in series[symbol].items():
            if moment % HOUR_SECONDS:
                raise CrossAssetError("a cross-section bar is not aligned to an hour boundary")
            if math.isfinite(close) and close > 0.0:
                matrix[(moment - first) // HOUR_SECONDS, column] = math.log(close)
    return CrossSectionPanel(symbols=symbols, first_open_time=first, log_close=matrix)


def endpoint_mask(panel: CrossSectionPanel, instant: int) -> tuple[Any | None, str | None]:
    """Which assets carry all four required endpoint bars at `instant`, or why none can.

    This is the whole point-in-time universe rule. Membership depends only on bars the asset
    has actually been observed to have at or before `instant`; nothing about its later life
    is consulted, so an asset that is delisted tomorrow is a full member today and an asset
    that lists tomorrow is absent today.
    """
    index = panel.row_index(instant)
    if index >= panel.rows or index - LONG_LOOKBACK_HOURS < 0:
        return None, DECISION_INSTANT_OUTSIDE_SOURCE_SPAN
    matrix = panel.log_close
    mask = np.ones(matrix.shape[1], dtype=bool)
    for offset in ENDPOINT_OFFSET_HOURS:
        mask &= ~np.isnan(matrix[index - offset])
    return mask, None


def point_in_time_universe(panel: CrossSectionPanel, instant: int) -> tuple[str, ...]:
    """The admitted assets usable at `instant`, in the panel's frozen symbol order."""
    mask, _ = endpoint_mask(panel, instant)
    if mask is None:
        return ()
    return tuple(symbol for symbol, usable in zip(panel.symbols, mask, strict=True) if usable)


def point_in_time_universe_size(panel: CrossSectionPanel, instant: int) -> int:
    """Source accounting only. The universe size is never a model feature."""
    mask, _ = endpoint_mask(panel, instant)
    return 0 if mask is None else int(mask.sum())


def endpoint_returns(
    panel: CrossSectionPanel, instant: int
) -> tuple[tuple[Any, Any, Any] | None, str | None]:
    """The three trailing log returns of every point-in-time-eligible asset at `instant`."""
    mask, reason = endpoint_mask(panel, instant)
    if mask is None:
        return None, reason
    if int(mask.sum()) < MINIMUM_POINT_IN_TIME_UNIVERSE:
        return None, INSUFFICIENT_POINT_IN_TIME_UNIVERSE
    index = panel.row_index(instant)
    matrix = panel.log_close
    now = matrix[index][mask]
    return (
        now - matrix[index - SHORT_LOOKBACK_HOURS][mask],
        now - matrix[index - MEDIUM_LOOKBACK_HOURS][mask],
        now - matrix[index - LONG_LOOKBACK_HOURS][mask],
    ), None


def build_cross_asset_features(
    panel: CrossSectionPanel, instant: int
) -> tuple[tuple[float, ...] | None, str | None]:
    """Build the eight frozen features at `instant`, or say why they are unavailable.

    Returns `(values, None)` when available and `(None, reason)` when not. An unavailable
    evaluation instant becomes a counted abstention; an unavailable training instant is
    excluded from fitting and counted. Neither is ever imputed.

    Every statistic is equal-weighted across the same point-in-time asset set. No market
    capitalisation, future volume or survivorship weight exists anywhere in this function.
    """
    returns, reason = endpoint_returns(panel, instant)
    if returns is None:
        return None, reason
    short, medium, long = returns
    median_medium = float(np.median(medium))
    median_long = float(np.median(long))
    values = (
        float(np.count_nonzero(short > 0.0) / short.shape[0]),
        float(np.count_nonzero(medium > 0.0) / medium.shape[0]),
        float(np.count_nonzero(long > 0.0) / long.shape[0]),
        float(np.median(short)),
        median_medium,
        median_long,
        float(np.median(np.abs(medium - median_medium))),
        float(np.median(np.abs(long - median_long))),
    )
    if len(values) != FEATURE_COUNT:
        raise CrossAssetError("the frozen cross-asset feature vector changed width")
    if any(not math.isfinite(value) for value in values):
        return None, NON_FINITE_CROSS_ASSET_FEATURE
    return values, None


def feature_source_instants(panel: CrossSectionPanel, instant: int) -> tuple[int, ...]:
    """Exactly the grid instants a vector at `instant` may read, oldest first."""
    mask, _ = endpoint_mask(panel, instant)
    if mask is None:
        return ()
    return tuple(instant - offset * HOUR_SECONDS for offset in ENDPOINT_OFFSET_HOURS)


def first_available_instant(panel: CrossSectionPanel) -> int | None:
    """The earliest grid instant whose feature vector is available, or None if there is none."""
    for index in range(LONG_LOOKBACK_HOURS, panel.rows):
        instant = panel.first_open_time + index * HOUR_SECONDS
        if build_cross_asset_features(panel, instant)[0] is not None:
            return instant
    return None


def availability_map(
    panel: CrossSectionPanel, instants: Sequence[int]
) -> tuple[dict[int, tuple[float, ...]], dict[str, int]]:
    """Feature vectors for every supplied instant, plus the typed unavailability counts."""
    available: dict[int, tuple[float, ...]] = {}
    reasons = dict.fromkeys(UNAVAILABILITY_TAXONOMY, 0)
    for instant in instants:
        values, reason = build_cross_asset_features(panel, instant)
        if values is None:
            reasons[str(reason)] += 1
            continue
        available[instant] = values
    return available, reasons


def manifest_record(root: Path = ROOT) -> Mapping[str, Any]:
    return json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))


def load_cross_section(root: Path = ROOT) -> CrossSectionPanel:
    """Read the governed substrate, verifying the manifest hash and the development ceiling."""
    import hashlib

    import pyarrow.parquet as pq

    manifest = manifest_record(root)
    path = root / manifest["substrate"]["path"]
    if not path.is_file():
        raise CrossAssetError(f"the cross-section substrate is not installed: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != manifest["substrate"]["sha256"]:
        raise CrossAssetError("cross-section substrate hash mismatch")

    table = pq.read_table(path, columns=list(ADMITTED_COLUMNS))
    symbols = table["symbol"].to_numpy(zero_copy_only=False)
    micros = table["open_time"].to_numpy()
    closes = table["close"].to_numpy()
    seconds = (micros // 1_000_000).astype(np.int64)
    if seconds.size == 0:
        raise CrossAssetError("the cross-section substrate is empty")
    if int(seconds.max()) > DEVELOPMENT_CEILING_SECONDS:
        raise CrossAssetError("the cross-section substrate contains a post-cutoff bar")
    if np.any(seconds % HOUR_SECONDS):
        raise CrossAssetError("a cross-section bar is not aligned to an hour boundary")

    admitted = np.array(
        [is_admitted_symbol(str(symbol)) for symbol in symbols.tolist()], dtype=bool
    )
    symbols, seconds, closes = symbols[admitted], seconds[admitted], closes[admitted]
    names = tuple(sorted({str(symbol) for symbol in symbols.tolist()}))
    if TARGET_SYMBOL in names:
        raise CrossAssetError("the prediction target may not enter the cross-section")
    column_of = {name: index for index, name in enumerate(names)}
    first, last = int(seconds.min()), int(seconds.max())
    rows = (last - first) // HOUR_SECONDS + 1
    matrix = np.full((rows, len(names)), np.nan, dtype=np.float64)
    valid = np.isfinite(closes) & (closes > 0.0)
    row_index = ((seconds[valid] - first) // HOUR_SECONDS).astype(np.int64)
    column_index = np.array(
        [column_of[str(symbol)] for symbol in symbols[valid].tolist()], dtype=np.int64
    )
    matrix[row_index, column_index] = np.log(closes[valid])
    return CrossSectionPanel(symbols=names, first_open_time=first, log_close=matrix)


def source_identity(root: Path = ROOT) -> dict[str, Any]:
    """The admitted source identity, copied from the manifest rather than restated."""
    manifest = manifest_record(root)
    substrate = manifest["substrate"]
    return {
        "version": SOURCE_VERSION,
        "manifest": MANIFEST_PATH,
        "manifest_id": manifest["inventory_id"],
        "predictive_contract": CONTRACT_PATH,
        "substrate_artifact": substrate["path"],
        "substrate_file_sha256": substrate["sha256"],
        "substrate_hourly_rows": substrate["hourly_rows"],
        "substrate_symbols_with_rows": substrate["symbols_with_rows"],
        "source": SOURCE_NAME,
        "provider": manifest["source"]["provider"],
        "archive_base": manifest["source"]["archive_base"],
        "archive_prefix": manifest["source"]["prefix"],
        "market_type": manifest["source"]["market_type"],
        "interval": manifest["source"]["interval"],
        "credential_free": manifest["source"]["credentials_used"] is False,
        "monthly_objects": manifest["object_count"],
        "objects_sha256": manifest["objects_sha256"],
        "quote_asset": manifest["object_quote_asset"],
        "universe_derivation": manifest["universe_derivation"],
        "leveraged_tokens_excluded": manifest["leveraged_token_excluded_count"],
        "target_symbol_excluded_from_cross_section": True,
        "fields_read": list(ADMITTED_COLUMNS),
        "forbidden_fields": list(FORBIDDEN_COLUMNS),
        "endpoint_offsets_hours": list(ENDPOINT_OFFSET_HOURS),
        "required_endpoint_bars": REQUIRED_ENDPOINT_BARS,
        "minimum_point_in_time_universe": MINIMUM_POINT_IN_TIME_UNIVERSE,
        "cross_sectional_weighting": CROSS_SECTIONAL_WEIGHTING,
        "universe_recomputed_point_in_time": True,
        "future_survival_filter": False,
        "whole_sample_participation_threshold": False,
        "retired_504_row_participation_rule_revived": False,
        "interpolation": False,
        "forward_fill": False,
        "nearest_bar_substitution": False,
        "reconstructed_or_backfilled": False,
        "third_party_vendor_used": False,
        "historical_cross_section_results_imported": False,
        "development_ceiling": DEVELOPMENT_CEILING,
    }


__all__ = [
    "ADMITTED_COLUMNS",
    "ARCHIVE_HOST",
    "ARCHIVE_PREFIX",
    "CONTRACT_PATH",
    "CROSS_SECTIONAL_WEIGHTING",
    "DECISION_INSTANT_OUTSIDE_SOURCE_SPAN",
    "DEVELOPMENT_CEILING",
    "DEVELOPMENT_CEILING_SECONDS",
    "ENDPOINT_OFFSET_HOURS",
    "FEATURE_COUNT",
    "FEATURE_NAMES",
    "FEATURE_SET_VERSION",
    "FORBIDDEN_COLUMNS",
    "HOUR_SECONDS",
    "INSUFFICIENT_POINT_IN_TIME_UNIVERSE",
    "KLINE_INTERVAL",
    "LONG_LOOKBACK_HOURS",
    "MANIFEST_PATH",
    "MEDIUM_LOOKBACK_HOURS",
    "MINIMUM_POINT_IN_TIME_UNIVERSE",
    "NON_FINITE_CROSS_ASSET_FEATURE",
    "QUOTE_ASSET",
    "REQUIRED_ENDPOINT_BARS",
    "SHORT_LOOKBACK_HOURS",
    "SOURCE_NAME",
    "SOURCE_VERSION",
    "SUBSTRATE_PATH",
    "TARGET_SYMBOL",
    "UNAVAILABILITY_TAXONOMY",
    "CrossAssetError",
    "CrossSectionPanel",
    "availability_map",
    "build_cross_asset_features",
    "endpoint_mask",
    "endpoint_returns",
    "feature_source_instants",
    "first_available_instant",
    "is_admitted_symbol",
    "is_leveraged_token",
    "load_cross_section",
    "manifest_record",
    "panel_from_series",
    "point_in_time_universe",
    "point_in_time_universe_size",
    "source_identity",
]
