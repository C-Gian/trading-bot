"""One-position risk governor, stop-risk sizing and pinned contract filters (section 18).

Filters come from a pinned exchangeInfo snapshot (synthetic fixtures use explicit fake filters);
tick/step are never derived from precision fields. Rounding uses decimal arithmetic.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from .contract import INITIAL_EQUITY, MAX_GROSS_NOTIONAL, PATH_DRAWDOWN_STOP, RISK_FRACTION


@dataclass(frozen=True)
class ExchangeFilters:
    """BTCUSDT PERPETUAL/TRADING PRICE_FILTER, LOT_SIZE/MARKET_LOT_SIZE and MIN_NOTIONAL."""

    source: str
    tick_size: str
    step_size: str
    min_qty: str
    max_qty: str
    min_notional: str

    def as_pairs(self) -> tuple[tuple[str, float], ...]:
        return tuple(
            (name, float(getattr(self, name)))
            for name in ("tick_size", "step_size", "min_qty", "max_qty", "min_notional")
        )

    def sha256(self) -> str:
        payload = json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("ascii")).hexdigest()


def round_quantity(quantity: float, filters: ExchangeFilters) -> float:
    """Round down to the step size (never enlarge planned risk/notional)."""
    step = Decimal(filters.step_size)
    steps = (Decimal(repr(quantity)) / step).to_integral_value(rounding=ROUND_FLOOR)
    return float(steps * step)


def round_stop(stop: float, side: str, filters: ExchangeFilters) -> float:
    """Round the stop to the tick toward the entry, so realized risk never exceeds the plan."""
    tick = Decimal(filters.tick_size)
    rounding = ROUND_CEILING if side == "LONG" else ROUND_FLOOR
    return float((Decimal(repr(stop)) / tick).to_integral_value(rounding=rounding) * tick)


def size(equity: float, stop_distance: float, raw_entry: float) -> float:
    """min(risk_budget / D, current_equity * max_gross / raw_entry) before venue rounding."""
    risk_budget = RISK_FRACTION * equity
    return min(risk_budget / stop_distance, MAX_GROSS_NOTIONAL * equity / raw_entry)


def filtered_quantity(
    equity: float, stop_distance: float, price: float, filters: ExchangeFilters
) -> float | None:
    """The rounded order quantity, or None when the pinned minimums/maximum are not met."""
    if not (stop_distance > 0 and price > 0 and equity > 0):
        return None
    quantity = round_quantity(size(equity, stop_distance, price), filters)
    if quantity < float(filters.min_qty) or quantity > float(filters.max_qty):
        return None
    if quantity * price < float(filters.min_notional):
        return None
    return quantity


class Governor:
    """Equity path, peak, 5% path-drawdown lock and the one-position rule."""

    def __init__(self) -> None:
        self.equity = INITIAL_EQUITY  # realized equity
        self.mark = INITIAL_EQUITY  # marked-to-market equity
        self.peak = INITIAL_EQUITY
        self.locked = False
        self.open_trade: str | None = None
        self.pending_intent: str | None = None

    @property
    def drawdown(self) -> float:
        return 0.0 if self.peak <= 0 else max(0.0, 1.0 - self.mark / self.peak)

    def mark_to(self, mark: float) -> bool:
        """Update the marked path; returns True exactly when the lock triggers now."""
        self.mark = mark
        self.peak = max(self.peak, mark)
        if not self.locked and self.drawdown >= PATH_DRAWDOWN_STOP:
            self.locked = True
            return True
        return False

    @property
    def flat(self) -> bool:
        return self.open_trade is None and self.pending_intent is None
