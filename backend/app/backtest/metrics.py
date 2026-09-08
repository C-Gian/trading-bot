from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from .models import TradeRecord


@dataclass(frozen=True)
class Metrics:
    trade_count: int
    net_expectancy_r: Decimal | None
    cumulative_net_r: Decimal
    profit_factor: Decimal | None
    maximum_drawdown_r: Decimal
    hit_rate: Decimal | None
    average_win_r: Decimal | None
    average_loss_r: Decimal | None
    gross_to_net_cost_drag_r: Decimal
    unresolved_invalid_count: int


def calculate(records: Iterable[TradeRecord]) -> Metrics:
    all_records = tuple(records)
    valid = [
        r
        for r in all_records
        if r.data_quality_status == "VALID" and r.net_r is not None and r.gross_r is not None
    ]
    net = [r.net_r for r in valid if r.net_r is not None]
    gross = [r.gross_r for r in valid if r.gross_r is not None]
    wins = [x for x in net if x > 0]
    losses = [x for x in net if x < 0]
    cumulative = sum(net, Decimal(0))
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    for value in net:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    gain = sum(wins, Decimal(0))
    loss = -sum(losses, Decimal(0))
    return Metrics(
        len(valid),
        cumulative / len(valid) if valid else None,
        cumulative,
        gain / loss if loss else None,
        max_dd,
        Decimal(len(wins)) / len(valid) if valid else None,
        sum(wins, Decimal(0)) / len(wins) if wins else None,
        sum(losses, Decimal(0)) / len(losses) if losses else None,
        sum(gross, Decimal(0)) - cumulative,
        len(all_records) - len(valid),
    )
