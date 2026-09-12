"""`PAPER_STATISTICS_V1`: deterministic counts over genuine persisted paper trades.

FUTURE PAPER EVIDENCE — NOT BACKTEST PERFORMANCE.

Every number here is computed from the local paper-trade store and nothing else. No
development research metric of any kind may appear in this surface, and a paper record
never becomes development evidence.

Only terminal trades contribute to realized-return metrics. `PENDING_ENTRY` and `OPEN`
trades are counted as active and are excluded from every realized figure, and an
`INVALIDATED` trade carries no return at all. With no contributing trades the realized
metrics are explicitly `None` rather than a misleading zero.
"""

from __future__ import annotations

from typing import Any

from .paper import (
    ACTIVE_STATUSES,
    CLOSED_EXPIRY,
    CLOSED_STOP,
    CLOSED_TARGET,
    EVIDENCE_STAGE,
    EVIDENCE_VERSION,
    INVALIDATED,
    TERMINAL_STATUSES,
    PaperTradeStore,
)

STATISTICS_VERSION = "PAPER_STATISTICS_V1"
STATISTICS_LABEL = "FUTURE PAPER EVIDENCE — NOT BACKTEST PERFORMANCE"
REALIZED_STATUSES = (CLOSED_TARGET, CLOSED_STOP, CLOSED_EXPIRY)


def _drawdown(returns: list[float]) -> float | None:
    """Maximum peak-to-trough decline of the cumulative realized R curve."""
    if not returns:
        return None
    peak = 0.0
    equity = 0.0
    worst = 0.0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return worst


def statistics(store: PaperTradeStore) -> dict[str, Any]:
    """Counts and realized-return metrics over genuine persisted paper trades only."""
    trades = store.load()
    active = [trade for trade in trades if trade["status"] in ACTIVE_STATUSES]
    closed = [trade for trade in trades if trade["status"] in TERMINAL_STATUSES]
    realized = [
        trade
        for trade in trades
        if trade["status"] in REALIZED_STATUSES and trade["net_r"] is not None
    ]
    returns = [float(trade["net_r"]) for trade in realized]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    breakeven = [value for value in returns if value == 0]
    contributing = len(returns)
    total_r = sum(returns) if returns else None
    return {
        "statistics_version": STATISTICS_VERSION,
        "evidence_version": EVIDENCE_VERSION,
        "evidence_stage": EVIDENCE_STAGE,
        "label": STATISTICS_LABEL,
        "development_backtest_metrics_included": False,
        "total_paper_trades": len(trades),
        "pending_entry": sum(1 for trade in trades if trade["status"] == "PENDING_ENTRY"),
        "open": sum(1 for trade in trades if trade["status"] == "OPEN"),
        "active": len(active),
        "closed": len(closed),
        "invalidated": sum(1 for trade in trades if trade["status"] == INVALIDATED),
        "closed_target": sum(1 for trade in trades if trade["status"] == CLOSED_TARGET),
        "closed_stop": sum(1 for trade in trades if trade["status"] == CLOSED_STOP),
        "expiries": sum(1 for trade in trades if trade["status"] == CLOSED_EXPIRY),
        "realized_trades": contributing,
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(breakeven),
        "win_rate": (len(wins) / contributing) if contributing else None,
        "mean_realized_r": (total_r / contributing)
        if contributing and total_r is not None
        else None,
        "cumulative_realized_r": total_r,
        "expectancy_r_per_trade": (
            (total_r / contributing) if contributing and total_r is not None else None
        ),
        "max_drawdown_r": _drawdown(returns),
        "best_realized_r": max(returns) if returns else None,
        "worst_realized_r": min(returns) if returns else None,
        "empty": contributing == 0,
        "empty_detail": (
            "No terminal paper trade has produced a realized return yet."
            if contributing == 0
            else None
        ),
        "champion_status": "NONE",
        "real_money": False,
    }
