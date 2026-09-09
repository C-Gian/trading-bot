"""Frozen development schedule and descriptive diagnostics; never loads market data."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from numbers import Integral
from pathlib import Path
from typing import Any

import numpy as np

from app.data.policy import CUTOFF, parse_utc_instant

from .baselines import calculate_metrics

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json"
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
HOUR_US = 3_600_000_000
REGIMES = ("PERSISTENT_UP", "OTHER")
DIAGNOSTICS = {
    "minimum_total_trades": 120,
    "minimum_fold_trades": 15,
    "minimum_trade_ess": 60,
    "maximum_unresolved_rate": 0.01,
    "ess_lags": 5,
    "minimum_nonnegative_folds": 4,
    "maximum_positive_fold_profit_share": 0.5,
    "minimum_double_cost_expectancy": 0,
}


def utc_us(value: str | datetime) -> int:
    """Convert an aware instant to integer UTC microseconds without float rounding."""
    delta = parse_utc_instant(value) - EPOCH
    return (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds


def protocol_hash(protocol: dict[str, Any]) -> str:
    """Canonical content hash; Git ancestry must independently establish the freeze."""
    return hashlib.sha256(
        json.dumps(protocol, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def validate_protocol(protocol: dict[str, Any]) -> None:
    """Fail closed if any declared V1 schedule, threshold, or metadata changes."""
    expected_folds = []
    for year in range(2019, 2025):
        expected_folds.append(
            {
                "fold_id": f"DEV-{year}",
                "train_start": "2017-08-17T04:00:00Z",
                "train_end_exclusive": f"{year - 1}-12-24T00:00:00Z",
                "validation_start": f"{year}-01-02T00:00:00Z",
                "validation_end_exclusive": f"{year + 1}-01-01T00:00:00Z",
                "last_signal_inclusive": f"{year}-12-31T00:00:00Z",
            }
        )
    expected = {
        "schema_version": 1,
        "protocol_id": "DEVELOPMENT_WALK_FORWARD_V1",
        "development_cutoff": "2024-12-31T23:59:00Z",
        "evidence_stage": "EXPOSED_DEVELOPMENT_WALK_FORWARD",
        "purge_hours": 216,
        "embargo_hours": 24,
        "max_hold_minutes": 1440,
        "fit_policy": "NO_FITTING_NO_FOLD_SELECTION",
        "primary_aggregation": "POOLED_VALID_RESOLVED_NET_R",
        "diagnostics": DIAGNOSTICS,
        "folds": expected_folds,
    }
    if protocol != expected:
        raise ValueError("protocol differs from frozen DEVELOPMENT_WALK_FORWARD_V1")
    for fold in protocol["folds"]:
        start = utc_us(fold["validation_start"])
        end = utc_us(fold["validation_end_exclusive"])
        if start - utc_us(fold["train_end_exclusive"]) != 216 * HOUR_US:
            raise ValueError("invalid purge")
        if end - utc_us(fold["last_signal_inclusive"]) != 24 * HOUR_US:
            raise ValueError("invalid full-horizon containment")
        if end - 60_000_000 > utc_us(CUTOFF):
            raise ValueError("validation would access a post-cutoff minute")


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    validate_protocol(protocol)
    return protocol


def fold_contains(fold: dict[str, Any], signal_us: int) -> bool:
    """Signals include end minus 24h; the outcome fence itself is exclusive for opens."""
    return utc_us(fold["validation_start"]) <= signal_us <= utc_us(fold["last_signal_inclusive"])


def validation_fold(protocol: dict[str, Any], signal_us: int) -> dict[str, Any] | None:
    return next((fold for fold in protocol["folds"] if fold_contains(fold, signal_us)), None)


def _rounded(value: float | None) -> float | None:
    return round(value, 10) if value is not None else None


def _metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    invalid = sum(trade["status"] == "INVALID" for trade in trades)
    unresolved = sum(trade["status"] == "UNRESOLVED" for trade in trades)
    metrics = calculate_metrics(trades, len(trades), invalid, unresolved)
    metrics["invalid_rate"] = _rounded(invalid / len(trades)) if trades else 0.0
    resolved = [trade for trade in trades if trade["status"] == "VALID"]
    bps = [float(trade["net_return_bps"]) for trade in resolved if "net_return_bps" in trade]
    metrics["net_return_bps_observation_count"] = len(bps)
    complete_bps = bool(resolved) and len(bps) == len(resolved)
    metrics["net_expectancy_bps"] = _rounded(math.fsum(bps) / len(bps)) if complete_bps else None
    metrics["cumulative_net_bps"] = _rounded(math.fsum(bps)) if complete_bps else None
    return metrics


def dependence_diagnostics(trades: list[dict[str, Any]], lags: int = 5) -> dict[str, Any]:
    """Positive sample-ACF penalty and weekly concentration, not a significance test."""
    if lags < 1:
        raise ValueError("ESS lag count must be positive")
    resolved = sorted(
        (trade for trade in trades if trade["status"] == "VALID"),
        key=lambda trade: trade["signal_us"],
    )
    values = np.asarray([trade["net_r"] for trade in resolved], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("non-finite trade return")
    count = len(values)
    # Shifting first avoids a rounded mean manufacturing variance for a constant
    # decimal-valued series (for example 120 identical float representations of 0.1).
    shifted = values - values[0] if count else values
    centered = shifted - float(shifted.mean()) if count else shifted
    variance_sum = float(np.dot(centered, centered))
    correlations = []
    for lag in range(1, lags + 1):
        correlation = (
            float(np.dot(centered[:-lag], centered[lag:])) / variance_sum
            if count > lag and variance_sum > 0
            else 0.0
        )
        correlations.append(min(1.0, max(0.0, correlation)))
    ess = min(float(count), count / (1 + 2 * math.fsum(correlations)))
    weeks = Counter(
        (EPOCH + timedelta(microseconds=int(trade["signal_us"]))).isocalendar()[:2]
        for trade in resolved
    )
    weekly_square_sum = sum(number * number for number in weeks.values())
    return {
        "trade_ess": _rounded(ess),
        "positive_autocorrelations": [_rounded(value) for value in correlations],
        "constant_return_series": count > 0 and variance_sum == 0,
        "active_week_count": len(weeks),
        "active_week_kish_count": _rounded(count * count / weekly_square_sum)
        if weekly_square_sum
        else 0.0,
        "interpretation": "DEPENDENCE_AND_CONCENTRATION_DIAGNOSTICS_NOT_INDEPENDENT_EVIDENCE",
    }


def _concentration(values: list[float], *, positive_only: bool = False) -> float | None:
    magnitudes = [max(0.0, value) if positive_only else abs(value) for value in values]
    total = math.fsum(magnitudes)
    return _rounded(max(magnitudes) / total) if total else None


def summarize_trades(
    trades: Iterable[dict[str, Any]],
    protocol: dict[str, Any],
    *,
    allow_unclassified_regime: bool = False,
) -> dict[str, Any]:
    """Slice immutable paths or summarize supplied fold runs; never resimulates entries.

    The caller owns flat-at-fold-start simulation. Slicing existing controls cannot
    retroactively remove their earlier position occupancy. Every supplied signal
    is checked against the development cutoff before interval filtering.
    """
    validate_protocol(protocol)
    selected = []
    supplied_count = 0
    for source in trades:
        supplied_count += 1
        signal = source.get("signal_us")
        if isinstance(signal, bool) or not isinstance(signal, Integral):
            raise TypeError("trade signal_us must be an integer UTC microsecond instant")
        signal = int(signal)
        if signal % HOUR_US or signal > utc_us(CUTOFF):
            raise ValueError("trade signal is misaligned or post-cutoff")
        fold = validation_fold(protocol, signal)
        if fold is None:
            continue
        trade = dict(source)
        trade["signal_us"] = signal
        if trade.get("status") not in {"VALID", "INVALID", "UNRESOLVED"}:
            raise ValueError("unknown trade status")
        exit_us = trade.get("exit_us")
        if exit_us is not None:
            if isinstance(exit_us, bool) or not isinstance(exit_us, Integral):
                raise TypeError("exit_us must be an integer UTC microsecond instant")
            if not signal <= exit_us <= signal + 24 * HOUR_US or exit_us > utc_us(
                fold["validation_end_exclusive"]
            ):
                raise ValueError("trade exit exceeds its holding horizon or validation fence")
        if trade["status"] == "VALID":
            if not all(
                key in trade and math.isfinite(float(trade[key])) for key in ("net_r", "gross_r")
            ):
                raise ValueError("valid trade requires finite net and gross R")
            if "net_return_bps" in trade and not math.isfinite(float(trade["net_return_bps"])):
                raise ValueError("non-finite net return bps")
        elif any(trade.get(key) is not None for key in ("net_r", "gross_r", "net_return_bps")):
            raise ValueError("invalid/unresolved trade cannot contain invented numeric P&L")
        year = (EPOCH + timedelta(microseconds=signal)).year
        if "year" in trade and trade["year"] != year:
            raise ValueError("trade year disagrees with signal timestamp")
        trade["year"] = year
        regime = trade.get("regime", "UNCLASSIFIED")
        if regime not in REGIMES and not (allow_unclassified_regime and regime == "UNCLASSIFIED"):
            raise ValueError("regime must be observed PERSISTENT_UP/OTHER, not inferred from P&L")
        trade["regime"] = regime
        selected.append(trade)
    selected.sort(key=lambda trade: trade["signal_us"])
    if len({trade["signal_us"] for trade in selected}) != len(selected):
        raise ValueError("duplicate signals in a single strategy path")
    metrics = _metrics(selected)
    folds = []
    for fold in protocol["folds"]:
        contained = [trade for trade in selected if fold_contains(fold, trade["signal_us"])]
        folds.append({"fold_id": fold["fold_id"], "metrics": _metrics(contained)})
    populated = [fold for fold in folds if fold["metrics"]["trade_count"]]
    means = [fold["metrics"]["net_expectancy_r"] for fold in populated]
    pnls = [fold["metrics"]["cumulative_net_r"] or 0.0 for fold in folds]
    counts = [fold["metrics"]["trade_count"] for fold in folds]
    total_count = metrics["trade_count"]
    total_pnl = metrics["cumulative_net_r"] or 0.0
    loo = {
        fold["fold_id"]: _rounded((total_pnl - pnl) / (total_count - count))
        if total_count > count
        else None
        for fold, pnl, count in zip(folds, pnls, counts, strict=True)
    }
    nonnegative = sum(value >= 0 for value in means)

    def extreme(best: bool) -> dict[str, Any] | None:
        if not populated:
            return None
        choose = max if best else min
        fold = choose(populated, key=lambda item: item["metrics"]["net_expectancy_r"])
        return {
            "fold_id": fold["fold_id"],
            "net_expectancy_r": fold["metrics"]["net_expectancy_r"],
        }

    diagnostics = dependence_diagnostics(selected, protocol["diagnostics"]["ess_lags"])
    diagnostics["minimum_fold_trades"] = min(counts)
    regime_names = (*REGIMES, "UNCLASSIFIED") if allow_unclassified_regime else REGIMES
    regime_metrics = {
        regime: _metrics([trade for trade in selected if trade["regime"] == regime])
        for regime in regime_names
    }
    regime_pnls = [value["cumulative_net_r"] or 0.0 for value in regime_metrics.values()]
    regime_counts = [value["trade_count"] for value in regime_metrics.values()]
    return {
        "validation_outcome": "PASS",
        "evidence_stage": protocol["evidence_stage"],
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol_hash(protocol),
        "supplied_attempt_count": supplied_count,
        "excluded_outside_validation_attempt_count": supplied_count - len(selected),
        "metrics": metrics,
        "folds": folds,
        "diagnostics": diagnostics,
        "stability": {
            "nonnegative_fold_count": nonnegative,
            "positive_fold_fraction": _rounded(sum(value > 0 for value in means) / len(folds)),
            "nonnegative_fold_fraction": _rounded(nonnegative / len(folds)),
            "populated_fold_count": len(populated),
            "empty_fold_count": len(folds) - len(populated),
            "equal_fold_mean": _rounded(math.fsum(means) / len(means)) if means else None,
            "equal_fold_mean_policy": "NONEMPTY_FOLDS_ONLY_EMPTY_FOLDS_RETAINED_IN_DIAGNOSTICS",
            "worst_fold": extreme(False),
            "best_fold": extreme(True),
            "max_absolute_fold_pnl_share": _concentration(pnls),
            "max_positive_fold_profit_share": _concentration(pnls, positive_only=True),
            "max_fold_trade_share": _concentration(counts),
            "leave_one_fold_out_expectancy": loo,
        },
        "regime_metrics": regime_metrics,
        "regime_stability": {
            "max_absolute_regime_pnl_share": _concentration(regime_pnls),
            "max_positive_regime_profit_share": _concentration(regime_pnls, positive_only=True),
            "max_regime_trade_share": _concentration(regime_counts),
        },
    }


def terminal_classification(
    default_summary: dict[str, Any],
    zero_summary: dict[str, Any],
    double_summary: dict[str, Any],
    protocol: dict[str, Any],
) -> str:
    """Apply the frozen research rule; poor profitability never fails validation."""
    validate_protocol(protocol)
    for summary in (default_summary, zero_summary, double_summary):
        if summary.get("validation_outcome") != "PASS":
            raise ValueError("structural invalidity blocks terminal classification")
        if summary.get("protocol_sha256") != protocol_hash(protocol):
            raise ValueError("summary is not linked to the frozen protocol")
    diagnostic = protocol["diagnostics"]
    metrics = default_summary["metrics"]
    if (
        metrics["trade_count"] < diagnostic["minimum_total_trades"]
        or default_summary["diagnostics"]["minimum_fold_trades"] < diagnostic["minimum_fold_trades"]
        or default_summary["diagnostics"]["trade_ess"] < diagnostic["minimum_trade_ess"]
        or metrics["unresolved_rate"] > diagnostic["maximum_unresolved_rate"]
    ):
        return "INCONCLUSIVE"
    expectancy = metrics["net_expectancy_r"]
    gross = zero_summary["metrics"]["net_expectancy_r"]
    doubled = double_summary["metrics"]["net_expectancy_r"]
    if any(value is None or not math.isfinite(value) for value in (expectancy, gross, doubled)):
        raise ValueError("sufficient trade diagnostics require finite cost-profile expectancies")
    if expectancy <= 0:
        return "REJECT_COST_DOMINATED" if gross > 0 else "REJECT"
    if doubled < diagnostic["minimum_double_cost_expectancy"]:
        return "REJECT_COST_DOMINATED"
    stability = default_summary["stability"]
    if (
        stability["nonnegative_fold_count"] < diagnostic["minimum_nonnegative_folds"]
        or any(
            value is None or value <= 0
            for value in stability["leave_one_fold_out_expectancy"].values()
        )
        or stability["max_positive_fold_profit_share"]
        > diagnostic["maximum_positive_fold_profit_share"]
    ):
        return "REJECT_UNSTABLE"
    return "PROMISING_DEVELOPMENT_ONLY"
