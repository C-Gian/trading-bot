"""Deterministic G2-02 scorecards (development protocol sections 12-13; contract section 24).

Forecast scoring uses the exact empirical predictive distribution each forecast was issued with:
the atoms are `(mu_z + e) * SIGMA_4H` for the residual set `e` the core used at issue time (the
prequential window of the forecast residual archive, or the fit's training-target baseline). The
window is reconstructed from the archive exactly as `ResidualArchive.window` selects it, and the
reconstruction is verified against the issued q10/q50/q90 (bit-identical) before any score is used.

CRPS of an empirical distribution with atoms x_1..x_n at observation y:
    CRPS = mean_i |x_i - y| - (1 / (2 n^2)) * sum_i sum_j |x_i - x_j|.
It is evaluated in z-space and rescaled by SIGMA_4H (exact: every atom shares the scale). Sliding
prequential windows use Fenwick trees over the globally ranked residuals so every decision is
scored exactly in O(log n).

Nothing here is a probability claim: p_positive is the issued empirical-distribution frequency and
is labelled uncalibrated by its source status.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..contract import MAX_RESIDUAL_AGE, MINUTE, QUANTILES
from .runner import scored_mask

DAY_MINUTES = 1440
WEEKDAY_OF_ORIGIN = 2  # 2020-01-01 was a Wednesday (Monday = 0)
SEED = 2026092702
REPLICATES = 5000
PERCENTILES = (10, 50, 90)
STRATA_STRENGTH = (("WEAK", 0.0, 0.25), ("MODERATE", 0.25, 0.75), ("STRONG", 0.75, math.inf))
SOURCE_NAMES = {1: "TRAINING_TARGET_BASELINE_UNVALIDATED", 2: "PREQUENTIAL_CDF_UNCALIBRATED"}
MAX_AGE_MINUTES = int(MAX_RESIDUAL_AGE // MINUTE)


# ---------------------------------------------------------------------- CRPS machinery
class _Fenwick:
    __slots__ = ("count", "size", "total")

    def __init__(self, size: int) -> None:
        self.size = size
        self.count = [0] * (size + 1)
        self.total = [0.0] * (size + 1)

    def add(self, rank: int, count: int, value: float) -> None:
        i = rank + 1
        while i <= self.size:
            self.count[i] += count
            self.total[i] += value
            i += i & -i

    def prefix(self, rank_exclusive: int) -> tuple[int, float]:
        """(count, sum) of members with global rank < rank_exclusive."""
        i = rank_exclusive
        c, s = 0, 0.0
        while i > 0:
            c += self.count[i]
            s += self.total[i]
            i -= i & -i
        return c, s


class SlidingCrps:
    """Exact CRPS against a sliding contiguous window [lo, hi) of an append-only residual log."""

    def __init__(self, values: np.ndarray) -> None:
        self.values = np.asarray(values, dtype=float)
        order = np.argsort(self.values, kind="stable")
        self.rank = np.empty(len(order), dtype=np.int64)
        self.rank[order] = np.arange(len(order))
        self.sorted = self.values[order]
        self.tree = _Fenwick(len(order))
        self.lo = self.hi = 0
        self.n = 0
        self.sum = 0.0
        self.pair = 0.0  # sum over ordered pairs |e_i - e_j|

    def _distance_sum(self, value: float, rank: int) -> float:
        below_count, below_sum = self.tree.prefix(rank)
        above_count = self.n - below_count
        above_sum = self.sum - below_sum
        return value * below_count - below_sum + above_sum - value * above_count

    def _insert(self, index: int) -> None:
        value, rank = float(self.values[index]), int(self.rank[index])
        self.pair += 2.0 * self._distance_sum(value, rank)
        self.tree.add(rank, 1, value)
        self.n += 1
        self.sum += value

    def _remove(self, index: int) -> None:
        value, rank = float(self.values[index]), int(self.rank[index])
        self.tree.add(rank, -1, -value)
        self.n -= 1
        self.sum -= value
        self.pair -= 2.0 * self._distance_sum(value, rank)

    def move(self, lo: int, hi: int) -> None:
        if lo < self.lo or hi < self.hi:
            raise ValueError("sliding windows only move forward")
        while self.hi < hi:
            self._insert(self.hi)
            self.hi += 1
        while self.lo < lo:
            self._remove(self.lo)
            self.lo += 1

    def crps_z(self, mu: float, y: float) -> float:
        """CRPS of atoms mu + e (current window) at observation y (z-space)."""
        target = y - mu
        k = int(np.searchsorted(self.sorted, target, side="right"))
        below_count, below_sum = self.tree.prefix(k)
        above_count = self.n - below_count
        above_sum = self.sum - below_sum
        mean_abs = (target * below_count - below_sum + above_sum - target * above_count) / self.n
        return mean_abs - self.pair / (2.0 * self.n * self.n)


class FixedAtoms:
    """Exact CRPS for a fixed atom set (training-target baseline distribution)."""

    def __init__(self, atoms: np.ndarray) -> None:
        self.sorted = np.sort(np.asarray(atoms, dtype=float))
        self.n = len(self.sorted)
        self.prefix = np.concatenate([[0.0], np.cumsum(self.sorted)])
        weights = 2.0 * np.arange(self.n) - self.n + 1.0
        self.spread = float(np.dot(weights, self.sorted)) / (self.n * self.n)

    def crps_z(self, mu: float, y: float) -> float:
        target = y - mu
        k = int(np.searchsorted(self.sorted, target, side="right"))
        below = self.prefix[k]
        above = self.prefix[-1] - below
        mean_abs = (target * k - below + above - target * (self.n - k)) / self.n
        return float(mean_abs - self.spread)


def crps_bruteforce(atoms: np.ndarray, y: float) -> float:
    atoms = np.asarray(atoms, dtype=float)
    return float(
        np.mean(np.abs(atoms - y)) - 0.5 * np.mean(np.abs(atoms[:, None] - atoms[None, :]))
    )


def windows(arrays: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """[lo, hi) archive window of every decision, exactly as `ResidualArchive.window(t)`."""
    t = arrays["t"]
    matured = arrays["archive_matured"]
    times = arrays["archive_times"]
    hi = np.searchsorted(matured, t, side="right")
    # `times` is sorted, so searching the full log and clamping at hi equals searching times[:hi].
    lo = np.minimum(np.searchsorted(times, t - MAX_AGE_MINUTES, side="left"), hi)
    return lo.astype(np.int64), hi.astype(np.int64)


def verify_reconstruction(
    arrays: dict[str, np.ndarray], lo: np.ndarray, hi: np.ndarray, rows: np.ndarray
) -> dict[str, Any]:
    """Recompute issued quantiles from the reconstructed residual set; must be bit-identical."""
    values = arrays["archive_values"]
    checked = mismatched = 0
    for i in rows:
        source = int(arrays["residual_source"][i])
        if source == 2:
            residuals = values[lo[i] : hi[i]]
        else:
            residuals = arrays[f"atoms_{int(arrays['fit'][i])}"]
        if len(residuals) != int(arrays["residual_count"][i]):
            mismatched += 1
            checked += 1
            continue
        returns = (arrays["mu_z"][i] + residuals) * arrays["sigma"][i]
        q = np.quantile(returns, list(QUANTILES), method="linear")
        issued = (arrays["q10"][i], arrays["q50"][i], arrays["q90"][i])
        checked += 1
        if tuple(float(v) for v in q) != tuple(float(v) for v in issued):
            mismatched += 1
    return {"checked": checked, "mismatched": mismatched, "bit_identical": mismatched == 0}


def forecast_contributions(arrays: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Per-decision forecast score contributions (NaN where not scoreable)."""
    n = len(arrays["t"])
    scored = scored_mask(arrays["t"])
    usable = scored & arrays["forecast_available"] & (arrays["outcome_status"] == 1)
    lo, hi = windows(arrays)
    crps = np.full(n, np.nan)
    sliding = SlidingCrps(arrays["archive_values"])
    fixed: dict[int, FixedAtoms] = {}
    for i in np.flatnonzero(arrays["forecast_available"]):
        if not usable[i]:
            continue
        sigma, mu = float(arrays["sigma"][i]), float(arrays["mu_z"][i])
        yz = float(arrays["realized"][i]) / sigma
        if int(arrays["residual_source"][i]) == 2:
            sliding.move(int(lo[i]), int(hi[i]))
            crps[i] = sigma * sliding.crps_z(mu, yz)
        else:
            j = int(arrays["fit"][i])
            if j not in fixed:
                fixed[j] = FixedAtoms(arrays[f"atoms_{j}"])
            crps[i] = sigma * fixed[j].crps_z(mu, yz)
    realized: np.ndarray = np.where(usable, arrays["realized"], np.nan)

    def pinball(q: np.ndarray, tau: float) -> np.ndarray:
        return np.where(usable, (realized - q) * (tau - (realized < q)), np.nan)

    positive = (realized > 0).astype(float)
    median = arrays["median"]
    hit = np.where(
        usable & (median != 0) & (realized != 0),
        (np.sign(median) == np.sign(realized)).astype(float),
        np.nan,
    )
    step = max(1, int(usable.sum()) // 499)
    sample = np.flatnonzero(usable)[::step]
    return {
        "usable": usable,
        "crps": crps,
        "pinball_q10": pinball(arrays["q10"], 0.10),
        "pinball_q50": pinball(arrays["q50"], 0.50),
        "pinball_q90": pinball(arrays["q90"], 0.90),
        "brier": np.where(usable, (arrays["p_positive"] - positive) ** 2, np.nan),
        "covered": np.where(
            usable,
            ((realized >= arrays["q10"]) & (realized <= arrays["q90"])).astype(float),
            np.nan,
        ),
        "abs_error_median": np.where(usable, np.abs(realized - median), np.nan),
        "direction_hit": hit,
        "_verification": verify_reconstruction(arrays, lo, hi, sample),  # type: ignore[dict-item]
    }


def strength_stratum(view: np.ndarray) -> np.ndarray:
    labels = np.full(len(view), "UNAVAILABLE", dtype=object)
    for name, low, high in STRATA_STRENGTH:
        labels[(view >= low) & (view < high)] = name
    return labels


def _mean(values: np.ndarray, mask: np.ndarray) -> float | None:
    selected = values[mask & np.isfinite(values)]
    return None if selected.size == 0 else float(selected.mean())


FORECAST_METRICS = (
    "crps",
    "pinball_q10",
    "pinball_q50",
    "pinball_q90",
    "brier",
    "covered",
    "abs_error_median",
    "direction_hit",
)


def forecast_scorecard(arrays: dict[str, np.ndarray], c: dict[str, Any]) -> dict[str, Any]:
    scored = scored_mask(arrays["t"])
    usable = c["usable"]
    available = arrays["forecast_available"]
    out: dict[str, Any] = {
        "support": {
            "scored_decisions": int(scored.sum()),
            "forecast_available": int((scored & available).sum()),
            "forecast_unavailable": int((scored & ~available).sum()),
            "matured_scoreable": int(usable.sum()),
            "available_not_matured_at_observation_ceiling": int(
                (scored & available & (arrays["outcome_status"] != 1)).sum()
            ),
            "availability_fraction": float((scored & available).sum() / max(1, scored.sum())),
            "residual_source_counts": {
                SOURCE_NAMES.get(k, "NONE"): int((scored & (arrays["residual_source"] == k)).sum())
                for k in (0, 1, 2)
            },
        },
        "metrics": {name: _mean(c[name], usable) for name in FORECAST_METRICS},
        "metric_definitions": {
            "crps": "mean CRPS of the issued empirical predictive distribution (return units)",
            "pinball_q10": "mean pinball loss of q10 (tau 0.10)",
            "pinball_q50": "mean pinball loss of q50 (tau 0.50)",
            "pinball_q90": "mean pinball loss of q90 (tau 0.90)",
            "brier": "mean (p_positive - 1{r4h > 0})^2; p_positive is uncalibrated",
            "covered": "fraction of r4h inside [q10, q90] (nominal central 80%)",
            "abs_error_median": "mean |r4h - median forecast|",
            "direction_hit": "descriptive only: sign(median) == sign(r4h), zeros excluded",
        },
        "reconstruction_verification": c["_verification"],
    }
    strata = strength_stratum(arrays["view"])
    table = []
    for source in (1, 2):
        for name, _, _ in STRATA_STRENGTH:
            mask = usable & (strata == name) & (arrays["residual_source"] == source)
            table.append(
                {
                    "view_strength": name,
                    "evidence": SOURCE_NAMES[source],
                    "count": int(mask.sum()),
                    **{metric: _mean(c[metric], mask) for metric in FORECAST_METRICS},
                }
            )
    out["strata"] = table
    years = year_of(arrays["t"])
    out["by_year"] = [
        {
            "year": int(year),
            "count": int((usable & (years == year)).sum()),
            **{
                metric: _mean(c[metric], usable & (years == year))
                for metric in ("crps", "brier", "covered")
            },
        }
        for year in range(2021, 2025)
    ]
    return out


def year_of(t_minutes: np.ndarray) -> np.ndarray:
    days = (t_minutes // DAY_MINUTES).astype("timedelta64[D]") + np.datetime64("2020-01-01")
    return days.astype("datetime64[Y]").astype(int) + 1970


# ---------------------------------------------------------------------- weekly blocks
def week_index(t_minutes: np.ndarray) -> np.ndarray:
    """Contiguous UTC calendar week (Monday 00:00) of each timestamp."""
    return (t_minutes // DAY_MINUTES + WEEKDAY_OF_ORIGIN) // 7


class WeeklyBootstrap:
    """One common complete-week resampling matrix shared by every comparison (seed 2026092702)."""

    def __init__(self, weeks: np.ndarray) -> None:
        self.weeks = np.unique(weeks)
        rng = np.random.default_rng(SEED)
        self.draws = rng.integers(0, len(self.weeks), size=(REPLICATES, len(self.weeks)))

    def block_sums(self, values: np.ndarray, weeks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        mask = np.isfinite(values)
        position = np.searchsorted(self.weeks, weeks[mask])
        sums = np.bincount(position, weights=values[mask], minlength=len(self.weeks))
        counts = np.bincount(position, minlength=len(self.weeks)).astype(float)
        return sums, counts

    def mean_distribution(self, values: np.ndarray, weeks: np.ndarray) -> dict[str, Any]:
        sums, counts = self.block_sums(values, weeks)
        total = counts[self.draws].sum(axis=1)
        replicate = sums[self.draws].sum(axis=1) / np.where(total > 0, total, np.nan)
        point = float(sums.sum() / counts.sum()) if counts.sum() else None
        finite = replicate[np.isfinite(replicate)]
        return {
            "point": point,
            "count": int(counts.sum()),
            "weeks_with_data": int((counts > 0).sum()),
            **{
                f"p{p}": float(np.percentile(finite, p)) if finite.size else None
                for p in PERCENTILES
            },
            "replicates": REPLICATES,
            "seed": SEED,
            "fraction_replicates_above_zero": float((finite > 0).mean()) if finite.size else None,
        }

    def max_drawdown_distribution(self, returns: np.ndarray, weeks: np.ndarray) -> dict[str, Any]:
        """Path metric: resample complete weeks, chain their returns, report max drawdown."""
        position = np.searchsorted(self.weeks, weeks)
        groups = [np.log1p(returns[position == k]) for k in range(len(self.weeks))]
        values = []
        for row in self.draws:
            path = np.concatenate([groups[k] for k in row])
            curve = np.cumsum(path)
            peak = np.maximum.accumulate(np.concatenate([[0.0], curve]))[1:]
            values.append(float(1.0 - np.exp((curve - peak).min())) if path.size else 0.0)
        array = np.asarray(values)
        return {f"p{p}": float(np.percentile(array, p)) for p in PERCENTILES} | {
            "replicates": REPLICATES,
            "seed": SEED,
        }


# ---------------------------------------------------------------------- policy
def equity_path(arrays: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Marked equity on the 15m grid from 2021-01-01 00:00 through 2025-01-01 00:00 inclusive."""
    from .runner import ECONOMIC_START, INITIALIZATION_START, OBSERVATION_END

    lo = int((ECONOMIC_START - INITIALIZATION_START) // MINUTE)
    hi = int((OBSERVATION_END - INITIALIZATION_START) // MINUTE)
    t = arrays["t"]
    mask = (t >= lo) & (t <= hi)
    return t[mask], arrays["marked"][mask]


def interval_returns(t: np.ndarray, marked: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(interval start times, simple returns) of consecutive grid marks."""
    return t[:-1], marked[1:] / marked[:-1] - 1.0


def drawdown_stats(t: np.ndarray, marked: np.ndarray) -> dict[str, Any]:
    peak = np.maximum.accumulate(marked)
    drawdown = 1.0 - marked / peak
    under = drawdown > 1e-12
    longest = current = 0
    start_of_longest = None
    run_start = 0
    for k, flag in enumerate(under):
        if flag:
            if current == 0:
                run_start = k
            current += 1
            if current > longest:
                longest, start_of_longest = current, run_start
        else:
            current = 0
    worst = int(np.argmax(drawdown))
    return {
        "max_drawdown": float(drawdown.max()),
        "max_drawdown_at_index": worst,
        "time_under_water_fraction": float(under.mean()),
        "longest_under_water_days": longest * 15 / DAY_MINUTES,
        "longest_under_water_start_index": start_of_longest,
    }


def policy_scorecard(
    system: str,
    arrays: dict[str, np.ndarray] | None,
    events: dict[str, Any] | None,
    reason_sets: list[str] | None,
) -> dict[str, Any]:
    """Common-timeline portfolio + trade scorecard. `arrays is None` means CASH_REFERENCE."""
    from .variants import CASH_SYSTEM

    if arrays is None or events is None:
        assert system == CASH_SYSTEM
        return {"system": system, "definition": "zero exposure; equity constant at 10,000 USDT"}
    t, marked = equity_path(arrays)
    _starts, returns = interval_returns(t, marked)
    trades = events["trades"]
    years = sorted({trade["entry_time"][:4] for trade in trades})
    net = np.array([trade["net_pnl"] for trade in trades], dtype=float)
    gross = np.array([trade["gross_pnl"] for trade in trades], dtype=float)
    friction = np.array([trade["friction_cost"] for trade in trades], dtype=float)
    funding = np.array([trade["funding_pnl"] for trade in trades], dtype=float)
    net_r = np.array([trade["realized_net_r"] for trade in trades], dtype=float)
    sides = np.array([trade["side"] for trade in trades])
    notional = sum(trade["quantity"] * (trade["raw_entry"] + trade["raw_exit"]) for trade in trades)
    held_minutes = sum(_span_minutes(trade["entry_time"], trade["exit_time"]) for trade in trades)
    window_minutes = int(t[-1] - t[0])
    years_span = window_minutes / (365.25 * DAY_MINUTES)
    ordered = np.sort(net)[::-1]
    total_net = float(net.sum()) if net.size else 0.0
    lock = [e for e in events["risk_events"] if e["kind"] == "DRAWDOWN_STOP_TRIGGERED"]
    scored = scored_mask(arrays["t"])
    no_trade = scored & (arrays["action"] == 0)
    primary = primary_no_trade_reasons(arrays, reason_sets or [], no_trade)
    all_codes: dict[str, int] = {}
    for index in arrays["reasons"][scored]:
        for code in (reason_sets or [])[int(index)].split("|"):
            if code:
                all_codes[code] = all_codes.get(code, 0) + 1
    return {
        "system": system,
        "primary": {
            "definition": "mean simple return per 15m interval of marked equity on the common "
            "2021-01-01..2025-01-01 UTC grid, relative to CASH_REFERENCE (return 0)",
            "mean_15m_return_relative_cash": float(returns.mean()),
            "intervals": int(returns.size),
        },
        "total_net_return": float(marked[-1] / marked[0] - 1.0),
        "start_equity": float(marked[0]),
        "end_marked_equity": float(marked[-1]),
        "cagr": float((marked[-1] / marked[0]) ** (1.0 / years_span) - 1.0),
        **drawdown_stats(t, marked),
        "drawdown_stop_triggered_at": lock[0]["event_time"] if lock else None,
        "trade_count": len(trades),
        "mean_realized_net_r": float(net_r.mean()) if net_r.size else None,
        "median_realized_net_r": float(np.median(net_r)) if net_r.size else None,
        "win_fraction_descriptive": float((net > 0).mean()) if net.size else None,
        "total_net_pnl": total_net,
        "total_gross_pnl": float(gross.sum()),
        "total_friction": float(friction.sum()),
        "total_funding_pnl": float(funding.sum()),
        "friction_share_of_abs_gross": float(friction.sum() / max(1e-12, np.abs(gross).sum())),
        "funding_share_of_abs_gross": float(
            np.abs(funding).sum() / max(1e-12, np.abs(gross).sum())
        ),
        "turnover_per_year": float(notional / float(np.mean(marked)) / years_span),
        "occupancy_fraction": float(held_minutes / max(1, window_minutes)),
        "long_short_mix": {
            side: {
                "count": int((sides == side).sum()),
                "net_pnl": float(net[sides == side].sum()),
                "mean_net_r": float(net_r[sides == side].mean()) if (sides == side).any() else None,
            }
            for side in ("LONG", "SHORT")
        },
        "trades_by_year": {
            year: sum(t_["entry_time"][:4] == year for t_ in trades) for year in years
        },
        "net_pnl_by_year": {
            year: float(sum(t_["net_pnl"] for t_ in trades if t_["entry_time"][:4] == year))
            for year in years
        },
        "trades_by_quarter": _by_quarter(trades),
        "concentration": {
            "top5_trades_share_of_total_net": (
                float(ordered[:5].sum() / total_net) if trades and total_net != 0 else None
            ),
            "total_net_excluding_top5_trades": float(ordered[5:].sum()) if trades else 0.0,
        },
        "no_trade_primary_reasons": primary,
        "all_reason_code_counts_scored": dict(sorted(all_codes.items())),
        "decision_counts_scored": {
            "decisions": int(scored.sum()),
            "long_actions": int((scored & (arrays["action"] == 1)).sum()),
            "short_actions": int((scored & (arrays["action"] == -1)).sum()),
            "no_trade": int(no_trade.sum()),
            "policy_long_selections": int((scored & (arrays["selection"] == 1)).sum()),
            "policy_short_selections": int((scored & (arrays["selection"] == -1)).sum()),
        },
        "shadow_payoffs": shadow_distributions(arrays),
        "open_trade_at_observation_ceiling": events["open_trade_at_end"],
    }


NO_TRADE_PRECEDENCE = (
    "FORECAST_UNAVAILABLE_MISSING_DATA",
    "FORECAST_UNAVAILABLE_WARMUP",
    "FORECAST_UNAVAILABLE_INVALID_SIGMA",
    "FORECAST_UNAVAILABLE_NO_MODEL",
    "INSUFFICIENT_POLICY_EVIDENCE",
    "TREND_REFERENCE_FORECAST_UNAVAILABLE",
    "FORECAST_REFERENCE_NO_POLICY",
    "UTILITY_MARGIN_NOT_POSITIVE",
    "UTILITY_MARGIN_TIE",
    "TREND_REFERENCE_QUANTILES_NOT_DIRECTIONAL",
    "PATH_DRAWDOWN_STOP_ACTIVE",
    "POSITION_ALREADY_OPEN",
    "CONTRACT_FILTER_NOT_MET",
    "SOURCE_STALE_OR_INVALID",
)


def primary_reason(codes: set[str]) -> str:
    for code in NO_TRADE_PRECEDENCE:
        if code in codes:
            return code
    return "OTHER"


def primary_no_trade_reasons(
    arrays: dict[str, np.ndarray], reason_sets: list[str], mask: np.ndarray
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for index in arrays["reasons"][mask]:
        code = primary_reason(set(reason_sets[int(index)].split("|")))
        counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))


def _span_minutes(start: str, end: str) -> int:
    from datetime import datetime

    a = datetime.fromisoformat(start)
    b = datetime.fromisoformat(end)
    return int((b - a).total_seconds() // 60)


def _by_quarter(trades: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for trade in trades:
        year, month = trade["entry_time"][:4], int(trade["entry_time"][5:7])
        key = f"{year}Q{(month - 1) // 3 + 1}"
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def _distribution(values: np.ndarray) -> dict[str, Any]:
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"count": 0}
    q = np.percentile(values, [5, 10, 25, 50, 75, 90, 95])
    return {
        "count": int(values.size),
        "mean": float(values.mean()),
        "fraction_positive": float((values > 0).mean()),
        **{f"p{p}": float(v) for p, v in zip((5, 10, 25, 50, 75, 90, 95), q, strict=True)},
    }


def shadow_distributions(arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    """Standardized LONG/SHORT shadow NET_R (research labels, not booked P&L)."""
    scored = scored_mask(arrays["t"])
    long_r, short_r = arrays["shadow_long_net_r"], arrays["shadow_short_net_r"]
    selection = arrays["selection"]
    selected = np.where(selection == 1, long_r, np.where(selection == -1, short_r, np.nan))
    return {
        "note": "overlapping 15m labels; descriptive distributions, not independent samples",
        "all_eligible_long": _distribution(long_r[scored]),
        "all_eligible_short": _distribution(short_r[scored]),
        "policy_selected_side": _distribution(selected[scored & (selection != 0)]),
        "policy_selected_long": _distribution(long_r[scored & (selection == 1)]),
        "policy_selected_short": _distribution(short_r[scored & (selection == -1)]),
        "executed_decisions_selected_side": _distribution(
            selected[scored & (arrays["action"] != 0)]
        ),
        "unavailable_labels_scored": {
            "LONG": int((scored & (arrays["shadow_long_status"] != 1)).sum()),
            "SHORT": int((scored & (arrays["shadow_short_status"] != 1)).sum()),
        },
    }


# ---------------------------------------------------------------------- execution
def execution_scorecard(system: str, events: dict[str, Any] | None) -> dict[str, Any]:
    if events is None:
        return {"system": system, "definition": "no executions (zero exposure)"}
    fills = events["fills"]
    entries = [f for f in fills if f["kind"] == "ENTRY"]
    exits = [f for f in fills if f["kind"] == "EXIT"]
    rejected = [f for f in fills if f["kind"] == "ENTRY_REJECTED"]
    trades = events["trades"]
    delays = [
        _span_minutes(trade["intended_entry_time"], trade["entry_time"]) + 1 for trade in trades
    ]
    decision_delay = sorted(set(delays))
    friction_bps = [
        abs(f["accounting_price"] - f["raw_price"]) / f["raw_price"] * 1e4
        for f in entries + exits
        if f["raw_price"]
    ]
    shortfall = [
        (1 if trade["side"] == "LONG" else -1)
        * trade["entry_shortfall"]
        / (trade["raw_entry"] - trade["entry_shortfall"])
        * 1e4
        for trade in trades
    ]
    exit_kinds: dict[str, int] = {}
    for trade in trades:
        exit_kinds[trade["exit_kind"]] = exit_kinds.get(trade["exit_kind"], 0) + 1
    rejected_reasons: dict[str, int] = {}
    for fill in rejected:
        for code in fill["reason_codes"]:
            rejected_reasons[code] = rejected_reasons.get(code, 0) + 1
    funding = [f["amount"] for f in events["funding"]]
    return {
        "system": system,
        "decision_to_fill_delay_minutes": {
            "distinct_values": decision_delay,
            "definition": "entry price instant (open of the T+1m bar) minus decision instant T",
        },
        "entries_filled": len(entries),
        "exits_filled": len(exits),
        "entries_rejected": len(rejected),
        "entry_rejection_reasons": rejected_reasons,
        "raw_vs_accounting_friction_bps_per_side": {
            "min": min(friction_bps) if friction_bps else None,
            "max": max(friction_bps) if friction_bps else None,
            "convention": "historical 12bp all-in adverse haircut per executed side",
        },
        "friction_paid": float(sum(trade["friction_cost"] for trade in trades)),
        "funding_paid": float(-sum(a for a in funding if a < 0)),
        "funding_received": float(sum(a for a in funding if a > 0)),
        "funding_events": len(funding),
        "funding_invalid_events": sum(1 for f in events["funding"] if f["status"] != "SETTLED"),
        "exit_kinds": dict(sorted(exit_kinds.items())),
        "gap_stop_exits": exit_kinds.get("STOP_GAP", 0),
        "late_exit_data_missing": exit_kinds.get("EXPIRY_LATE_EXIT_DATA_MISSING", 0),
        "ambiguous_fills": {
            "count": 0,
            "basis": "no take-profit exists; same-bar ordering cannot create a favourable "
            "ambiguity; stops fill at the worse of open-through or stop price",
        },
        "trades_with_violation_flags": sum(1 for trade in trades if trade["violation_flags"]),
        "entry_implementation_shortfall_bps": _distribution(np.asarray(shortfall, dtype=float)),
        "implementation_shortfall_definition": "side-signed (raw T+1m open - decision close) in "
        "bp of the decision close; no historical quotes exist, so no bid/ask shortfall",
        "invalid_minutes_ingested": events["invalid_minutes"],
    }
