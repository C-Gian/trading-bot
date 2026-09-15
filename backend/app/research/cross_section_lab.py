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
    off_grid_rows: int = 0
    duplicate_rows: int = 0
    out_of_window_rows: int = 0
    invalid_rows: int = 0

    def __len__(self) -> int:
        return len(self.open_time)


def load_symbol(root: Path, symbol: str) -> SymbolBars:
    """Read every preserved monthly object for one symbol under the frozen window rules."""
    directory = root / RAW_ROOT / symbol
    collected: dict[int, tuple[float, ...]] = {}
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
        values = [
            columns[key][start:end][inner]
            for key in ("open", "high", "low", "close", "volume", "quote_volume")
        ]
        out[name] = SymbolBars(
            name,
            columns["open_time"][start:end][inner].astype(np.int64),
            values[0],
            values[1],
            values[2],
            values[3],
            values[4],
            values[5],
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
    """Completed UTC-day quote turnover on a contiguous calendar axis.

    The axis is contiguous so an archive gap cannot be skipped over: absent days and
    partial days both carry `nan` and therefore block the trailing liquidity window until
    thirty consecutive complete days exist again. Nothing is interpolated.
    """
    if len(bars) == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64)
    days = bars.open_time // DAY_US
    first, last = int(days[0]), int(days[-1])
    axis = np.arange(first, last + 1, dtype=np.int64)
    offset = (days - first).astype(np.int64)
    totals = np.bincount(offset, weights=bars.quote_volume, minlength=len(axis))
    hours = np.bincount(offset, minlength=len(axis))
    return axis, np.where(hours == 24, totals, np.nan)


def eligible_hours(bars: SymbolBars) -> np.ndarray:
    """Hours at which the frozen causal eligibility rules are satisfied using past data only.

    An hour t is eligible when, from information completed strictly before t, the symbol
    has at least `MINIMUM_HISTORY_DAYS` of archive history and its trailing median
    completed-day quote turnover over `LIQUIDITY_LOOKBACK_DAYS` clears the frozen floor.
    """
    if len(bars) == 0:
        return np.zeros(0, dtype=np.int64)
    days, totals = daily_quote_volume(bars)
    first_us = int(bars.open_time[0])
    eligible = []
    for index in range(LIQUIDITY_LOOKBACK_DAYS, len(days)):
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
    end_index = int(np.searchsorted(times, horizon_end, side="left")) - 1
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
    series = [
        np.array([archive[key][index] for key in ordered], dtype=np.float64) for index in range(5)
    ]
    archive_bars = SymbolBars(
        "BTCUSDT",
        np.array(ordered, dtype=np.int64),
        series[0],
        series[1],
        series[2],
        series[3],
        series[4],
        np.zeros(len(ordered), dtype=np.float64),
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
        canonical_decision = decide(canonical_source, hour)
        archive_decision = decide(archive_source, hour)
        if canonical_decision is not None and archive_decision is not None:
            both += 1
            identical += canonical_decision == archive_decision
        elif canonical_decision is not None:
            canonical_only += 1
        elif archive_decision is not None:
            archive_only += 1
        canonical_signals += bool(canonical_decision and canonical_decision[0])
        archive_signals += bool(archive_decision and archive_decision[0])

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


# --- vectorized frozen-ALIGNED evaluation (equivalent to FeatureSource.decision) -----
BREAKOUT_HOURS = 24
HOURLY_WINDOW = BREAKOUT_HOURS + 1
CONTEXT_BARS = 43
CONTEXT_INCREMENTS = CONTEXT_BARS - 1
VOLUME_MULTIPLIER = 2.0
UP_TO_DOWN_RATIO = 2.0


def _rolling_sum(values: np.ndarray, window: int) -> np.ndarray:
    """Inclusive rolling sum; element k holds the sum of values[k - window + 1 .. k]."""
    cumulative = np.concatenate(([0.0], np.cumsum(values, dtype=np.float64)))
    out = np.full(len(values), np.nan, dtype=np.float64)
    if len(values) >= window:
        out[window - 1 :] = cumulative[window:] - cumulative[:-window]
    return out


def _rolling_max(values: np.ndarray, window: int) -> np.ndarray:
    out = np.full(len(values), -np.inf, dtype=np.float64)
    if len(values) >= window:
        view = np.lib.stride_tricks.sliding_window_view(values, window)
        out[window - 1 :] = view.max(axis=1)
    return out


def aligned_grid(bars: SymbolBars) -> tuple[np.ndarray, np.ndarray]:
    """Vectorized frozen ALIGNED gates.

    Returns the decision hours where the frozen lookback is computable and the matching
    emission flags. Bars are placed on a contiguous hourly grid; a missing hour or an
    incomplete 4h bucket breaks the required contiguity exactly as `FeatureSource` does,
    and nothing is ever interpolated.
    """
    if len(bars) == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=bool)
    first, last = int(bars.open_time[0]), int(bars.open_time[-1])
    size = (last - first) // HOUR_US + 1
    position = (bars.open_time - first) // HOUR_US
    present = np.zeros(size, dtype=np.float64)
    high = np.zeros(size, dtype=np.float64)
    close = np.zeros(size, dtype=np.float64)
    volume = np.zeros(size, dtype=np.float64)
    present[position] = 1.0
    high[position] = bars.high
    close[position] = bars.close
    volume[position] = bars.volume
    masked_high = np.where(present > 0, high, -np.inf)

    # Hourly window: the 25 bars opening at k-25 .. k-1 relative to decision position k.
    presence_25 = _rolling_sum(present, HOURLY_WINDOW)
    breakout_max = _rolling_max(masked_high, BREAKOUT_HOURS)
    volume_24 = _rolling_sum(volume, BREAKOUT_HOURS)

    hours = np.arange(size, dtype=np.int64)
    latest = hours - 1  # position of the latest completed hourly bar
    baseline_end = hours - 2  # last position of the 24-bar breakout/volume baseline
    valid_hourly = (latest >= 0) & (baseline_end >= BREAKOUT_HOURS - 1)
    valid_hourly &= np.where(
        latest >= 0, presence_25[np.clip(latest, 0, size - 1)] == HOURLY_WINDOW, False
    )

    reference = np.where(latest >= 0, close[np.clip(latest, 0, size - 1)], np.nan)
    latest_volume = np.where(latest >= 0, volume[np.clip(latest, 0, size - 1)], np.nan)
    prior_high = np.where(
        baseline_end >= 0, breakout_max[np.clip(baseline_end, 0, size - 1)], np.inf
    )
    baseline_volume = np.where(
        baseline_end >= 0, volume_24[np.clip(baseline_end, 0, size - 1)], np.nan
    )
    volume_mean = baseline_volume / BREAKOUT_HOURS
    breakout = valid_hourly & (reference > prior_high)
    participation = (
        valid_hourly & (volume_mean > 0) & (latest_volume >= VOLUME_MULTIPLIER * volume_mean)
    )

    # 4h context: the 43 completed buckets ending at the last bucket before the decision.
    grid_times = first + hours * HOUR_US
    bucket_of = grid_times // FOUR_HOUR_US
    first_bucket = int(bucket_of[0])
    bucket_count = int(bucket_of[-1]) - first_bucket + 1
    bucket_index = (bucket_of - first_bucket).astype(np.int64)
    hours_in_bucket = np.bincount(bucket_index, weights=present, minlength=bucket_count)
    complete = (hours_in_bucket == 4).astype(np.float64)
    last_close = np.zeros(bucket_count, dtype=np.float64)
    last_close[bucket_index[present > 0]] = close[present > 0]
    increments = np.diff(last_close, prepend=last_close[0])
    up_increment = np.maximum(increments, 0.0)
    down_increment = np.maximum(-increments, 0.0)
    complete_run = _rolling_sum(complete, CONTEXT_BARS)
    up_sum = _rolling_sum(up_increment, CONTEXT_INCREMENTS)
    down_sum = _rolling_sum(down_increment, CONTEXT_INCREMENTS)

    last_bucket = bucket_index - 1
    valid_context = last_bucket >= CONTEXT_BARS - 1
    safe_bucket = np.clip(last_bucket, 0, bucket_count - 1)
    valid_context &= complete_run[safe_bucket] == CONTEXT_BARS
    up_total = up_sum[safe_bucket]
    down_total = down_sum[safe_bucket]
    persistent = valid_context & (up_total + down_total > 0)
    persistent &= up_total >= UP_TO_DOWN_RATIO * down_total

    computable = valid_hourly & valid_context
    # `FeatureSource.decision` also evaluates the previous hour: the same quality universe.
    previous = np.concatenate(([False], computable[:-1]))
    decidable = computable & previous
    emits = decidable & breakout & persistent & participation
    selected = np.flatnonzero(decidable)
    return grid_times[selected], emits[selected]


def verify_aligned_equivalence(bars: SymbolBars, hours: np.ndarray) -> dict[str, Any]:
    """Confirm the vectorized gates equal the frozen engine bar-for-bar on real data."""
    source = feature_source(bars)
    grid_hours, grid_emits = aligned_grid(bars)
    lookup = dict(zip(grid_hours.tolist(), grid_emits.tolist(), strict=True))
    checked = agree = engine_decidable = 0
    engine_signals = grid_signals = 0
    for hour in hours.tolist():
        try:
            emits, _, _ = source.decision(int(hour), "ALIGNED")
        except (IneligibleSignal, ValueError):
            if hour in lookup:
                return {"symbol": bars.symbol, "equivalent": False, "reason": "VECTOR_EXTRA"}
            continue
        engine_decidable += 1
        engine_signals += bool(emits)
        if hour not in lookup:
            return {"symbol": bars.symbol, "equivalent": False, "reason": "VECTOR_MISSING"}
        checked += 1
        agree += lookup[hour] == emits
        grid_signals += bool(lookup[hour])
    return {
        "symbol": bars.symbol,
        "engine_decidable": engine_decidable,
        "compared": checked,
        "identical": agree,
        "engine_signals": engine_signals,
        "vector_signals": grid_signals,
        "equivalent": checked == agree and engine_signals == grid_signals,
    }
