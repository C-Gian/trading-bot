"""Frozen System G1 Development V1 scoring, selection and adjudication (protocol sections 14-16).

Pure functions over closed trades, equity paths and compact forecast rows. No gate beyond the
protocol is implemented. Calendar attribution: a trade's net P&L belongs to the UTC year of its
exit; funding is already inside each trade's net P&L. Equity return for a period is the period's
net P&L divided by the equity at the period start (initial virtual equity 10,000 at the phase
start). Maximum drawdown is the peak-to-trough decline of the realized equity path.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from .development import ForecastRow
from .records import ClosedTrade, Side

INITIAL_EQUITY = Decimal(10000)

INVALID_EXECUTION = "INVALID_EXECUTION"
INCONCLUSIVE = "SYSTEM_G1_INCONCLUSIVE_OR_BLOCKED_NO_PROMOTION"
REJECTED_SELECTION = "SYSTEM_G1_DEVELOPMENT_REJECTED_SELECTION_STAGE"
REJECTED_EVALUATION = "SYSTEM_G1_DEVELOPMENT_REJECTED_EVALUATION_STAGE"
PROMOTION_ELIGIBLE = "SYSTEM_G1_PROMOTION_ELIGIBLE_PENDING_ASTRA"
DISPOSITION_ORDER = (
    INVALID_EXECUTION,
    INCONCLUSIVE,
    REJECTED_SELECTION,
    REJECTED_EVALUATION,
    PROMOTION_ELIGIBLE,
)

SELECTION_YEARS = (2021, 2022)
EVALUATION_YEARS = (2023, 2024)


@dataclass(frozen=True)
class BookResult:
    """Everything the gates need from one book (configuration x execution assumption)."""

    book_id: str
    config_id: str
    trades: tuple[ClosedTrade, ...]
    closed_trades: int
    run_drawdown_stop_triggered: bool
    equity_path: tuple[tuple[datetime, Decimal], ...] = ()


def _scorable(trades: Iterable[ClosedTrade]) -> list[ClosedTrade]:
    return [t for t in trades if t.scorable]


def net_pnl(trades: Iterable[ClosedTrade]) -> Decimal:
    return sum((t.net_pnl for t in trades), Decimal(0))


def by_year(trades: Iterable[ClosedTrade], year: int) -> list[ClosedTrade]:
    return [t for t in trades if t.exit_time.year == year]


def equity_returns(trades: Sequence[ClosedTrade], years: Sequence[int]) -> dict[str, Decimal]:
    """Per-year and cumulative net equity return from the phase-start equity."""
    equity = INITIAL_EQUITY
    result: dict[str, Decimal] = {}
    for year in years:
        pnl = net_pnl(by_year(trades, year))
        result[str(year)] = pnl / equity
        equity += pnl
    result["cumulative"] = (equity - INITIAL_EQUITY) / INITIAL_EQUITY
    return result


def profit_factor(trades: Sequence[ClosedTrade]) -> Decimal | None:
    wins = sum((t.net_pnl for t in trades if t.net_pnl > 0), Decimal(0))
    losses = -sum((t.net_pnl for t in trades if t.net_pnl < 0), Decimal(0))
    if losses == 0:
        return None if wins == 0 else Decimal("Infinity")
    return wins / losses


def top_winners_removed(trades: Sequence[ClosedTrade], count: int = 3) -> Decimal:
    winners = sorted((t.net_pnl for t in trades if t.net_pnl > 0), reverse=True)[:count]
    return net_pnl(trades) - sum(winners, Decimal(0))


def max_drawdown(trades: Sequence[ClosedTrade]) -> Decimal:
    """Peak-to-trough fraction of the realized equity path (exit-time ordered)."""
    equity = peak = INITIAL_EQUITY
    worst = Decimal(0)
    for trade in sorted(trades, key=lambda t: (t.exit_time, t.trade_id)):
        equity += trade.net_pnl
        peak = max(peak, equity)
        worst = max(worst, (peak - equity) / peak)
    return worst


def trade_metrics(result: BookResult, years: Sequence[int]) -> dict[str, Any]:
    scorable = _scorable(result.trades)
    coverage = (
        Decimal(len(scorable)) / Decimal(result.closed_trades) if result.closed_trades else None
    )
    returns = equity_returns(scorable, years)
    mean_r = sum((t.net_r for t in scorable), Decimal(0)) / len(scorable) if scorable else None
    return {
        "book_id": result.book_id,
        "config_id": result.config_id,
        "closed_trades": result.closed_trades,
        "scorable_trades": len(scorable),
        "scorable_by_year": {str(y): len(by_year(scorable, y)) for y in years},
        "scorable_coverage": coverage,
        "net_pnl_by_year": {str(y): net_pnl(by_year(scorable, y)) for y in years},
        "net_pnl": net_pnl(scorable),
        "equity_return": returns,
        "mean_net_r": mean_r,
        "profit_factor": profit_factor(scorable),
        "long_net_pnl": net_pnl(t for t in scorable if t.side is Side.LONG),
        "short_net_pnl": net_pnl(t for t in scorable if t.side is Side.SHORT),
        "long_trades": sum(1 for t in scorable if t.side is Side.LONG),
        "short_trades": sum(1 for t in scorable if t.side is Side.SHORT),
        "net_pnl_without_top3_winners": top_winners_removed(scorable),
        "max_drawdown": max_drawdown(scorable),
        "run_drawdown_stop_triggered": result.run_drawdown_stop_triggered,
    }


# ------------------------------------------------------------------ phase A (selection)
def selection_eligibility(
    metrics: dict[str, Any], years: Sequence[int] = SELECTION_YEARS
) -> dict[str, bool]:
    coverage = metrics["scorable_coverage"]
    gates = {"scorable_trades_ge_40": metrics["scorable_trades"] >= 40}
    for year in years:
        gates[f"scorable_{year}_ge_15"] = metrics["scorable_by_year"][str(year)] >= 15
    gates["scorable_coverage_ge_95pct"] = coverage is not None and coverage >= Decimal("0.95")
    for year in years:
        gates[f"net_pnl_{year}_positive"] = metrics["net_pnl_by_year"][str(year)] > 0
    gates["run_drawdown_stop_never_triggered"] = not metrics["run_drawdown_stop_triggered"]
    return gates


def select(table: dict[str, dict[str, Any]]) -> str | None:
    """Automatic selection: greatest cumulative net equity return among eligible; tie -> min ID."""
    eligible = [
        (config_id, row["equity_return"]["cumulative"])
        for config_id, row in table.items()
        if all(row["eligibility"].values())
    ]
    if not eligible:
        return None
    best = max(value for _, value in eligible)
    return min(config_id for config_id, value in eligible if value == best)


def phase_a_table(
    results: Sequence[BookResult], years: Sequence[int] = SELECTION_YEARS
) -> dict[str, dict[str, Any]]:
    table = {}
    for result in results:
        metrics = trade_metrics(result, years)
        metrics["eligibility"] = selection_eligibility(metrics, years)
        table[result.config_id] = metrics
    return table


# ------------------------------------------------------------------ phase B (evaluation)
def forecast_metrics(rows: Sequence[ForecastRow], years: Sequence[int]) -> dict[str, Any]:
    in_window = [r for r in rows if r.issue_time.year in years]
    by_conviction: dict[str, Any] = {}
    for conviction in ("LOW", "MEDIUM", "HIGH", "ALL"):
        valid = [
            r
            for r in in_window
            if r.valid
            and r.probability_up is not None
            and r.training_up_rate is not None
            and r.mean_return is not None
            and r.realized_return is not None
            and (conviction == "ALL" or r.conviction == conviction)
        ]
        n = len(valid)
        if not n:
            by_conviction[conviction] = {"valid": 0}
            continue

        cells = [
            (
                float(r.probability_up or 0),
                float(r.training_up_rate or 0),
                float(r.mean_return or 0),
                float(r.realized_return or 0),
            )
            for r in valid
        ]
        brier = sum((p - (1.0 if y > 0 else 0.0)) ** 2 for p, _, _, y in cells) / n
        baseline = sum((u - (1.0 if y > 0 else 0.0)) ** 2 for _, u, _, y in cells) / n
        mae = sum(abs(m - y) for _, _, m, y in cells) / n
        zero = sum(abs(y) for _, _, _, y in cells) / n
        by_conviction[conviction] = {
            "valid": n,
            "brier": brier,
            "brier_training_up_rate_baseline": baseline,
            "mae": mae,
            "mae_zero_return_baseline": zero,
        }
    issued = len(in_window)
    available = sum(1 for r in in_window if r.available)
    return {
        "eligible_issues": issued,
        "available_issues": available,
        "issue_coverage": available / issued if issued else None,
        "by_conviction": by_conviction,
    }


def evaluation_gates(
    primary: dict[str, Any],
    cost_stress: dict[str, Any],
    delay_stress: dict[str, Any],
    forecasts: dict[str, Any],
    identities_pass: bool,
    violations: bool,
    years: Sequence[int] = EVALUATION_YEARS,
) -> dict[str, dict[str, bool]]:
    coverage = primary["scorable_coverage"]
    support = {
        "identities_pass": identities_pass,
        "prediction_issue_coverage_ge_95pct": (forecasts["issue_coverage"] or 0) >= 0.95,
        "scorable_coverage_ge_95pct": coverage is not None and coverage >= Decimal("0.95"),
        "scorable_trades_ge_60": primary["scorable_trades"] >= 60,
        **{f"scorable_{y}_ge_20": primary["scorable_by_year"][str(y)] >= 20 for y in years},
        "long_ge_10_and_short_ge_10": primary["long_trades"] >= 10
        and primary["short_trades"] >= 10,
        "no_causal_data_provenance_violation": not violations,
        "run_drawdown_stop_never_triggered": not primary["run_drawdown_stop_triggered"],
    }
    returns = primary["equity_return"]
    pf = primary["profit_factor"]
    economic = {
        **{f"equity_return_{y}_positive": returns[str(y)] > 0 for y in years},
        "mean_net_r_ge_0_10": primary["mean_net_r"] is not None
        and primary["mean_net_r"] >= Decimal("0.10"),
        "cumulative_equity_return_ge_5pct": returns["cumulative"] >= Decimal("0.05"),
        "profit_factor_ge_1_15": pf is not None and pf >= Decimal("1.15"),
        "long_net_pnl_nonnegative": primary["long_net_pnl"] >= 0,
        "short_net_pnl_nonnegative": primary["short_net_pnl"] >= 0,
        "net_pnl_without_top3_winners_positive": primary["net_pnl_without_top3_winners"] > 0,
        "max_drawdown_below_5pct": primary["max_drawdown"] < Decimal("0.05"),
    }
    robustness = {
        "cost_48bp_net_pnl_positive": cost_stress["net_pnl"] > 0,
        "delay_plus_5m_net_pnl_positive": delay_stress["net_pnl"] > 0,
    }
    high = forecasts["by_conviction"]["HIGH"]
    prediction = {
        "high_valid_ge_100": high["valid"] >= 100,
        "high_brier_better_than_up_rate": high["valid"] > 0
        and high["brier"] < high["brier_training_up_rate_baseline"],
        "high_mae_better_than_zero_return": high["valid"] > 0
        and high["mae"] < high["mae_zero_return_baseline"],
    }
    return {
        "support": support,
        "economic": economic,
        "robustness": robustness,
        "prediction": prediction,
    }


def disposition(
    invalid_execution: bool,
    selected: str | None,
    gates: dict[str, dict[str, bool]] | None,
) -> str:
    """Frozen terminal ordering (protocol section 16)."""
    if invalid_execution:
        return INVALID_EXECUTION
    if selected is None:
        return REJECTED_SELECTION
    if gates is None:
        raise ValueError("a selected configuration requires evaluation gates")
    if not all(gates["support"].values()):
        return INCONCLUSIVE
    if not all(all(gates[group].values()) for group in ("economic", "robustness", "prediction")):
        return REJECTED_EVALUATION
    return PROMOTION_ELIGIBLE
