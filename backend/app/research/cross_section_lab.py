"""Build the 1h cross-sectional research substrate and the frozen-ALIGNED signal panel.

Nothing in this module evaluates the true cross-sectional ALIGNED effect. It produces
bars, causal eligibility, raw signal events and forward outcomes; the pooled estimator
lives in `cross_section_power` and is structurally barred from the zero alignment.
"""

from __future__ import annotations

import json
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .continuation import FeatureBar, FeatureSource, IneligibleSignal
from .cross_section import (
    DAY_US,
    DEVELOPMENT_END_US,
    DEVELOPMENT_START_US,
    LIQUIDITY_LOOKBACK_DAYS,
    MINIMUM_HISTORY_DAYS,
    MINIMUM_MEDIAN_DAILY_QUOTE_VOLUME_USDT,
    OUTCOME_HORIZON_HOURS,
)
from .cross_section_archive import RAW_ROOT
from .evaluation_protocol import EPOCH, HOUR_US

SUBSTRATE_PATH = "data/derived/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.parquet"
PANEL_PATH = "data/derived/BINANCE-SPOT-USDT-CROSSSECTION-PANEL-DEV-v1.parquet"
FOUR_HOUR_US = 4 * HOUR_US
KLINE_OPEN, KLINE_HIGH, KLINE_LOW, KLINE_CLOSE = 0, 2, 3, 4
KLINE_VOLUME, KLINE_QUOTE_VOLUME = 5, 7

SUBSTRATE_SCHEMA = pa.schema(
    [
        ("symbol", pa.string()),
        ("open_time", pa.int64()),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.float64()),
        ("quote_volume", pa.float64()),
    ]
)


def _rows(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"unexpected archive layout: {path.name}")
        text = archive.read(names[0]).decode("utf-8")
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.split(",")
        if fields[0].strip().lower().startswith("open_time"):
            continue
        out.append(fields)
    return out


@dataclass
class SymbolBars:
    """One symbol's in-window, on-grid, deduplicated hourly series."""

    symbol: str
    open_time: np.ndarray
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    quote_volume: np.ndarray
    off_grid_rows: int
    duplicate_rows: int
    out_of_window_rows: int
    invalid_rows: int

    def __len__(self) -> int:
        return len(self.open_time)


def load_symbol(root: Path, symbol: str) -> SymbolBars:
    """Read every preserved monthly object for one symbol under the frozen window rules."""
    directory = root / RAW_ROOT / symbol
    collected: dict[int, tuple[float, float, float, float, float, float]] = {}
    off_grid = duplicates = outside = invalid = 0
    for path in sorted(directory.glob(f"{symbol}-1h-*.zip")):
        for fields in _rows(path):
            raw = int(fields[KLINE_OPEN])
            open_us = raw * 1000 if raw < 10_000_000_000_000 else raw
            if open_us % HOUR_US:
                off_grid += 1
                continue
            if not DEVELOPMENT_START_US <= open_us <= DEVELOPMENT_END_US:
                outside += 1
                continue
            values = tuple(
                float(fields[index])
                for index in (
                    1,
                    KLINE_HIGH,
                    KLINE_LOW,
                    KLINE_CLOSE,
                    KLINE_VOLUME,
                    KLINE_QUOTE_VOLUME,
                )
            )
            opn, high, low, close, volume, quote = values
            if (
                not all(np.isfinite(values))
                or close <= 0
                or opn <= 0
                or high < max(opn, close)
                or low > min(opn, close)
                or low <= 0
                or volume < 0
                or quote < 0
            ):
                invalid += 1
                continue
            if open_us in collected:
                duplicates += 1
                continue
            collected[open_us] = values
    times = np.array(sorted(collected), dtype=np.int64)
    stacked = np.array([collected[int(t)] for t in times], dtype=np.float64).reshape(len(times), 6)
    return SymbolBars(
        symbol,
        times,
        stacked[:, 0],
        stacked[:, 1],
        stacked[:, 2],
        stacked[:, 3],
        stacked[:, 4],
        stacked[:, 5],
        off_grid,
        duplicates,
        outside,
        invalid,
    )


def build_substrate(root: Path, symbols: list[str]) -> dict[str, Any]:
    """Write one consolidated on-grid hourly parquet and report per-symbol integrity."""
    target = root / SUBSTRATE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    total = 0
    with pq.ParquetWriter(target, SUBSTRATE_SCHEMA, compression="zstd") as writer:
        for symbol in symbols:
            bars = load_symbol(root, symbol)
            if not len(bars):
                records.append({"symbol": symbol, "rows": 0, "status": "NO_IN_WINDOW_ROWS"})
                continue
            writer.write_table(
                pa.Table.from_arrays(
                    [
                        pa.array([symbol] * len(bars), pa.string()),
                        pa.array(bars.open_time, pa.int64()),
                        pa.array(bars.open, pa.float64()),
                        pa.array(bars.high, pa.float64()),
                        pa.array(bars.low, pa.float64()),
                        pa.array(bars.close, pa.float64()),
                        pa.array(bars.volume, pa.float64()),
                        pa.array(bars.quote_volume, pa.float64()),
                    ],
                    schema=SUBSTRATE_SCHEMA,
                )
            )
            total += len(bars)
            records.append(
                {
                    "symbol": symbol,
                    "rows": len(bars),
                    "first_open_us": int(bars.open_time[0]),
                    "last_open_us": int(bars.open_time[-1]),
                    "off_grid_rows": bars.off_grid_rows,
                    "duplicate_rows": bars.duplicate_rows,
                    "out_of_window_rows": bars.out_of_window_rows,
                    "invalid_rows": bars.invalid_rows,
                    "status": "IN_WINDOW",
                }
            )
    return {
        "path": SUBSTRATE_PATH,
        "symbols_with_rows": sum(1 for item in records if item["rows"]),
        "hourly_rows": total,
        "symbols": records,
        "interpolation_policy": "CANONICAL_GAPS_NEVER_INTERPOLATED",
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }


def read_substrate(root: Path) -> dict[str, SymbolBars]:
    table = pq.read_table(root / SUBSTRATE_PATH)
    symbols = table["symbol"].to_numpy(zero_copy_only=False)
    order = np.argsort(symbols, kind="stable")
    columns = {
        name: table[name].to_numpy(zero_copy_only=False)[order]
        for name in ("open_time", "open", "high", "low", "close", "volume", "quote_volume")
    }
    symbols = symbols[order]
    out: dict[str, SymbolBars] = {}
    boundaries = np.flatnonzero(np.concatenate(([True], symbols[1:] != symbols[:-1], [True])))
    for start, end in zip(boundaries[:-1], boundaries[1:], strict=True):
        name = str(symbols[start])
        inner = np.argsort(columns["open_time"][start:end], kind="stable")
        out[name] = SymbolBars(
            name,
            columns["open_time"][start:end][inner].astype(np.int64),
            *(
                columns[key][start:end][inner]
                for key in ("open", "high", "low", "close", "volume", "quote_volume")
            ),
            0,
            0,
            0,
            0,
        )
    return out


def aggregate_context(bars: SymbolBars) -> tuple[FeatureBar, ...]:
    """4h context bars built from completed hours; a bucket is complete with four hours."""
    buckets: dict[int, list[int]] = defaultdict(list)
    for index, open_us in enumerate(bars.open_time):
        buckets[int(open_us) // FOUR_HOUR_US * FOUR_HOUR_US].append(index)
    out = []
    for start in sorted(buckets):
        members = buckets[start]
        out.append(
            FeatureBar(
                start,
                float(bars.high[members].max()),
                float(bars.close[members[-1]]),
                float(bars.volume[members].sum()),
                len(members) == 4,
            )
        )
    return tuple(out)


def feature_source(bars: SymbolBars) -> FeatureSource:
    hourly = tuple(
        FeatureBar(int(t), float(h), float(c), float(v), True)
        for t, h, c, v in zip(bars.open_time, bars.high, bars.close, bars.volume, strict=True)
    )
    return FeatureSource(hourly, aggregate_context(bars))


def daily_quote_volume(bars: SymbolBars) -> tuple[np.ndarray, np.ndarray]:
    """Completed UTC-day quote turnover, used only for trailing capacity eligibility."""
    days = bars.open_time // DAY_US
    unique, inverse = np.unique(days, return_inverse=True)
    totals = np.zeros(len(unique), dtype=np.float64)
    np.add.at(totals, inverse, bars.quote_volume)
    hours = np.zeros(len(unique), dtype=np.int64)
    np.add.at(hours, inverse, 1)
    return unique, np.where(hours == 24, totals, np.nan)


def eligible_hours(bars: SymbolBars) -> np.ndarray:
    """Hours at which the frozen causal eligibility rules are satisfied using past data only.

    An hour t is eligible when, from information completed strictly before t, the symbol
    has at least `MINIMUM_HISTORY_DAYS` of archive history and its trailing median
    completed-day quote turnover over `LIQUIDITY_LOOKBACK_DAYS` clears the frozen floor.
    """
    days, totals = daily_quote_volume(bars)
    if len(bars) == 0:
        return np.zeros(0, dtype=np.int64)
    first_us = int(bars.open_time[0])
    eligible = []
    for index in range(len(days)):
        if index < LIQUIDITY_LOOKBACK_DAYS:
            continue
        window = totals[index - LIQUIDITY_LOOKBACK_DAYS : index]
        if np.isnan(window).any():
            continue
        if float(np.median(window)) < MINIMUM_MEDIAN_DAILY_QUOTE_VOLUME_USDT:
            continue
        day_start = int(days[index]) * DAY_US
        if day_start - first_us < MINIMUM_HISTORY_DAYS * DAY_US:
            continue
        eligible.append(day_start)
    if not eligible:
        return np.zeros(0, dtype=np.int64)
    starts = np.array(eligible, dtype=np.int64)
    hours = (starts[:, None] + np.arange(24, dtype=np.int64)[None, :] * HOUR_US).reshape(-1)
    return hours[(hours >= DEVELOPMENT_START_US) & (hours <= DEVELOPMENT_END_US)]


def raw_signals(bars: SymbolBars, hours: np.ndarray) -> np.ndarray:
    """Frozen ALIGNED gates on eligible hours, with no occupancy suppression at all."""
    source = feature_source(bars)
    emitted = []
    for hour in hours:
        try:
            emits, _, _ = source.decision(int(hour), "ALIGNED")
        except (IneligibleSignal, ValueError):
            continue
        if emits:
            emitted.append(int(hour))
    return np.array(emitted, dtype=np.int64)


def decidable_hours(bars: SymbolBars, hours: np.ndarray) -> np.ndarray:
    """Eligible hours where the frozen ALIGNED lookback is actually computable."""
    source = feature_source(bars)
    out = []
    for hour in hours:
        try:
            source.decision(int(hour), "ALIGNED")
        except (IneligibleSignal, ValueError):
            continue
        out.append(int(hour))
    return np.array(out, dtype=np.int64)


def forward_outcome(bars: SymbolBars, decision_us: int) -> dict[str, Any] | None:
    """Frozen 24h forward log return in bps; never interpolates a missing terminal price."""
    times = bars.open_time
    start_index = int(np.searchsorted(times, decision_us, side="left"))
    if start_index >= len(times):
        return None
    entry_us = int(times[start_index])
    horizon_end = decision_us + OUTCOME_HORIZON_HOURS * HOUR_US
    if entry_us > horizon_end:
        return None
    end_index = int(np.searchsorted(times, horizon_end, side="right")) - 1
    if end_index <= start_index:
        return None
    entry = float(bars.open[start_index])
    terminal = float(bars.close[end_index])
    if entry <= 0 or terminal <= 0:
        return None
    terminal_us = int(times[end_index])
    return {
        "entry_open_us": entry_us,
        "terminal_us": terminal_us,
        "truncated": terminal_us + HOUR_US < horizon_end,
        "return_bps": float(np.log(terminal / entry) * 10_000.0),
    }


def iso(open_us: int) -> str:
    return (EPOCH + timedelta(microseconds=int(open_us))).isoformat().replace("+00:00", "Z")


def utc_week(open_us: int) -> str:
    moment = datetime.fromtimestamp(int(open_us) / 1_000_000, UTC)
    year, week, _ = moment.isocalendar()
    return f"{year:04d}-W{week:02d}"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


# --- BTCUSDT direct-1h vs canonical-1m equivalence (section D) ----------------------
BTC_EQUIVALENCE_PATH = "reports/cross_section/CROSS-SECTION-BTC-1H-EQUIVALENCE-V1.json"
BTC_EQUIVALENCE_TOLERANCE = 1e-9


def _btc_archive_hours(root: Path) -> tuple[dict[int, tuple[float, ...]], int, int]:
    """Read the official BTCUSDT 1h archive and quarantine off-grid source rows."""
    collected: dict[int, tuple[float, ...]] = {}
    off_grid = off_grid_in_window = 0
    for path in sorted((root / RAW_ROOT / "BTCUSDT").glob("BTCUSDT-1h-*.zip")):
        for fields in _rows(path):
            raw = int(fields[KLINE_OPEN])
            open_us = raw * 1000 if raw < 10_000_000_000_000 else raw
            if open_us % HOUR_US:
                off_grid += 1
                off_grid_in_window += open_us >= DEVELOPMENT_START_US
                continue
            collected[open_us] = (
                float(fields[1]),
                float(fields[KLINE_HIGH]),
                float(fields[KLINE_LOW]),
                float(fields[KLINE_CLOSE]),
                float(fields[KLINE_VOLUME]),
            )
    return collected, off_grid, off_grid_in_window


def btc_equivalence_report(root: Path) -> dict[str, Any]:
    """Prove the frozen ALIGNED semantics survive the 1m to direct-1h source change."""
    from .source_grid import unsafe_buckets

    archive, off_grid, off_grid_in_window = _btc_archive_hours(root)
    hourly = pq.read_table(root / "data/derived/BTCUSDT-1h.parquet")
    context = pq.read_table(root / "data/derived/BTCUSDT-4h.parquet")
    minutes = pq.read_table(root / "data/canonical/BTCUSDT-1m.parquet")
    minute_times = minutes["open_time"].cast(pa.int64()).to_numpy()
    unsafe_1h = unsafe_buckets(minute_times, HOUR_US)
    unsafe_4h = unsafe_buckets(minute_times, FOUR_HOUR_US)

    canonical = {
        int(t): (float(o), float(h), float(low), float(c), float(v), bool(k))
        for t, o, h, low, c, v, k in zip(
            hourly["open_time"].cast(pa.int64()).to_numpy(),
            hourly["open"].to_numpy(),
            hourly["high"].to_numpy(),
            hourly["low"].to_numpy(),
            hourly["close"].to_numpy(),
            hourly["volume"].to_numpy(),
            hourly["complete"].to_numpy(),
            strict=True,
        )
    }
    in_window_canonical = {t for t in canonical if DEVELOPMENT_START_US <= t <= DEVELOPMENT_END_US}
    in_window_archive = {t for t in archive if DEVELOPMENT_START_US <= t <= DEVELOPMENT_END_US}

    fields = ("open", "high", "low", "close", "volume")
    mismatches = dict.fromkeys(fields, 0)
    worst = dict.fromkeys(fields, 0.0)
    compared = 0
    discrepant: list[dict[str, Any]] = []
    for open_us in sorted(in_window_canonical & in_window_archive):
        c_open, c_high, c_low, c_close, c_volume, complete = canonical[open_us]
        if not complete or open_us in unsafe_1h:
            continue
        a_open, a_high, a_low, a_close, a_volume = archive[open_us]
        compared += 1
        for name, left, right in zip(
            fields,
            (c_open, c_high, c_low, c_close, c_volume),
            (a_open, a_high, a_low, a_close, a_volume),
            strict=True,
        ):
            relative = abs(left - right) / max(abs(left), 1e-12)
            worst[name] = max(worst[name], relative)
            if relative > BTC_EQUIVALENCE_TOLERANCE:
                mismatches[name] += 1
                discrepant.append(
                    {
                        "open_time": iso(open_us),
                        "field": name,
                        "canonical": left,
                        "archive": right,
                        "relative_deviation": relative,
                    }
                )

    ordered = sorted(archive)
    archive_bars = SymbolBars(
        "BTCUSDT",
        np.array(ordered, dtype=np.int64),
        *(np.array([archive[t][index] for t in ordered], dtype=np.float64) for index in range(5)),
        np.zeros(len(ordered), dtype=np.float64),
        0,
        0,
        0,
        0,
    )
    archive_source = feature_source(archive_bars)
    canonical_source = FeatureSource(
        tuple(
            FeatureBar(int(t), float(h), float(c), float(v), bool(k) and int(t) not in unsafe_1h)
            for t, h, c, v, k in zip(
                hourly["open_time"].cast(pa.int64()).to_numpy(),
                hourly["high"].to_numpy(),
                hourly["close"].to_numpy(),
                hourly["volume"].to_numpy(),
                hourly["complete"].to_numpy(),
                strict=True,
            )
        ),
        tuple(
            FeatureBar(int(t), float(h), float(c), float(v), bool(k) and int(t) not in unsafe_4h)
            for t, h, c, v, k in zip(
                context["open_time"].cast(pa.int64()).to_numpy(),
                context["high"].to_numpy(),
                context["close"].to_numpy(),
                context["volume"].to_numpy(),
                context["complete"].to_numpy(),
                strict=True,
            )
        ),
    )

    def decide(source: FeatureSource, hour: int) -> tuple[bool, bool, bool, bool] | None:
        try:
            emits, feature, _ = source.decision(hour, "ALIGNED")
        except (IneligibleSignal, ValueError):
            return None
        return (emits, feature.breakout, feature.persistent_up, feature.participation)

    both = identical = canonical_only = archive_only = 0
    canonical_signals = archive_signals = 0
    for hour in range(DEVELOPMENT_START_US, DEVELOPMENT_END_US + 1, HOUR_US):
        left, right = decide(canonical_source, hour), decide(archive_source, hour)
        if left is not None and right is not None:
            both += 1
            identical += left == right
        elif left is not None:
            canonical_only += 1
        elif right is not None:
            archive_only += 1
        canonical_signals += bool(left and left[0])
        archive_signals += bool(right and right[0])

    decisions_match = (
        identical == both
        and canonical_only == 0
        and canonical_signals == archive_signals
        and in_window_canonical == in_window_archive
    )
    return {
        "report_id": "CROSS-SECTION-BTC-1H-EQUIVALENCE-V1",
        "symbol": "BTCUSDT",
        "window": {"start_us": DEVELOPMENT_START_US, "end_us": DEVELOPMENT_END_US},
        "archive_off_grid_rows_total": off_grid,
        "archive_off_grid_rows_in_window": off_grid_in_window,
        "in_window_hours_canonical": len(in_window_canonical),
        "in_window_hours_archive": len(in_window_archive),
        "identical_hour_key_set": in_window_canonical == in_window_archive,
        "bars_compared": compared,
        "bar_fields_compared": compared * len(fields),
        "bar_field_mismatches": mismatches,
        "bar_field_mismatch_total": sum(mismatches.values()),
        "worst_relative_deviation": worst,
        "source_discrepancies": discrepant,
        "source_discrepancy_interpretation": (
            "UPSTREAM_BINANCE_1M_VS_1H_SERIALIZATION_DIFFERENCE_NOT_AGGREGATION_ERROR"
        ),
        "decision_hours_scanned": (DEVELOPMENT_END_US - DEVELOPMENT_START_US) // HOUR_US + 1,
        "both_decidable": both,
        "identical_decisions": identical,
        "canonical_only_decidable": canonical_only,
        "archive_only_decidable": archive_only,
        "canonical_aligned_signals": canonical_signals,
        "archive_aligned_signals": archive_signals,
        "aligned_decisions_match": decisions_match,
        "DATA_SOURCE_STATUS": "PASS" if decisions_match else "REDESIGN_REQUIRED",
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
