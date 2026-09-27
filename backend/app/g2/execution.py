"""Market-only historical execution: shadow geometry, stops, expiry, friction, funding.

Sections 12-15 and 18 of the frozen contract. Every price is read through the causal minute tape;
the exact entry/expiry 1m bars are required. A stop is a trigger, not a guaranteed price: a bar
that opens through the stop fills at that worse open. Friction is adverse on every executed side.
Settled funding is usable only at its settlement instant and only for an open position.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from .bars import MinuteTape
from .contract import BASE_LATENCY, FUNDING_INTERVAL, HORIZON, MINUTE
from .records import Reason

SIDE_SIGN = {"LONG": 1, "SHORT": -1}


class FundingBook:
    """Settled funding records keyed by settlement minute (never backfilled earlier)."""

    def __init__(self, rates: Iterable[tuple[datetime, float]]) -> None:
        self.rates: dict[datetime, float] = {}
        for moment, rate in rates:
            if not math.isfinite(rate):
                continue
            self.rates[moment.replace(second=0, microsecond=0)] = rate
        self._times = sorted(self.rates)

    def settlements(
        self, after: datetime, through: datetime
    ) -> list[tuple[datetime, float | None]]:
        """Every settlement in (after, through]: recorded ones plus expected 8h boundaries.

        An expected boundary without a record is returned with rate None (structurally invalid).
        """
        lo = bisect.bisect_right(self._times, after)
        hi = bisect.bisect_right(self._times, through)
        moments = set(self._times[lo:hi])
        moment = after.replace(hour=0, minute=0, second=0, microsecond=0)
        while moment <= after:
            moment += FUNDING_INTERVAL
        while moment <= through:
            moments.add(moment)
            moment += FUNDING_INTERVAL
        return [(m, self.rates.get(m)) for m in sorted(moments)]


def accounting_price(raw: float, side: str, entry: bool, friction: float) -> float:
    """LONG buy/SHORT cover pay raw*(1+f); LONG sell/SHORT open receive raw*(1-f)."""
    buying = (side == "LONG") == entry
    return raw * (1 + friction) if buying else raw * (1 - friction)


def _proxy(tape: MinuteTape, moment: datetime) -> float | None:
    bar = tape.minute(moment - MINUTE)
    return None if bar is None else bar[3]


@dataclass(frozen=True)
class ShadowOutcome:
    status: str
    reasons: tuple[Reason, ...]
    raw_entry: float | None = None
    stop_price: float | None = None
    raw_exit: float | None = None
    exit_kind: str | None = None
    exit_time: datetime | None = None
    gross: float | None = None
    friction: float | None = None
    funding: float | None = None
    settlements: int = 0
    net: float | None = None
    net_r: float | None = None


def unavailable(*reasons: Reason) -> ShadowOutcome:
    return ShadowOutcome("UNAVAILABLE", tuple(reasons))


def shadow_label(
    tape: MinuteTape,
    funding: FundingBook,
    decision_time: datetime,
    side: str,
    stop_distance: float | None,
    friction: float,
) -> ShadowOutcome:
    """The standardized counterfactual payoff of one side at decision T (section 12/15)."""
    if stop_distance is None or not math.isfinite(stop_distance) or stop_distance <= 0:
        return unavailable(Reason.SOURCE_STALE_OR_INVALID)
    sign = SIDE_SIGN[side]
    entry_time = decision_time + BASE_LATENCY
    expiry_time = decision_time + HORIZON
    entry_bar = tape.minute(entry_time)
    if entry_bar is None:
        return unavailable(Reason.EXECUTION_ENTRY_DATA_MISSING)
    raw_entry = entry_bar[0]
    stop = raw_entry - sign * stop_distance
    path = tape.window(entry_time, expiry_time - MINUTE)
    tape.require(tape.index(expiry_time) + 1)
    present = tape.present[path]
    opens, highs, lows = tape.open[path], tape.high[path], tape.low[path]
    if sign > 0:
        gap, touch = opens <= stop, lows <= stop
    else:
        gap, touch = opens >= stop, highs >= stop
    hit = np.flatnonzero(present & (gap | touch))
    first_missing = np.flatnonzero(~present)
    if hit.size and (not first_missing.size or first_missing[0] > hit[0]):
        k = int(hit[0])
        exit_time = entry_time + k * MINUTE
        if gap[k]:
            raw_exit, kind = float(opens[k]), "STOP_GAP"
        else:
            raw_exit, kind = stop, "STOP"
    elif first_missing.size:
        return unavailable(Reason.SOURCE_STALE_OR_INVALID)
    else:
        expiry_bar = tape.minute(expiry_time)
        if expiry_bar is None:
            return unavailable(Reason.EXECUTION_EXIT_DATA_MISSING)
        raw_exit, kind, exit_time = expiry_bar[0], "EXPIRY", expiry_time
    funding_total = 0.0
    settlements = funding.settlements(entry_time, exit_time)
    for moment, rate in settlements:
        proxy = _proxy(tape, moment)
        if rate is None or proxy is None:
            return unavailable(Reason.FUNDING_DATA_INVALID)
        funding_total += -sign * rate * proxy
    gross = sign * (raw_exit - raw_entry)
    net_price = sign * (
        accounting_price(raw_exit, side, False, friction)
        - accounting_price(raw_entry, side, True, friction)
    )
    net = net_price + funding_total
    return ShadowOutcome(
        "AVAILABLE",
        (),
        raw_entry,
        stop,
        raw_exit,
        kind,
        exit_time,
        gross,
        gross - net_price,
        funding_total,
        len(settlements),
        net,
        net / stop_distance,
    )


@dataclass
class OpenTrade:
    """A simulated economic position (at most one exists)."""

    trade_id: str
    intent_id: str
    decision_id: str
    side: str
    decision_reference: float
    intended_entry_time: datetime
    intended_expiry_time: datetime
    entry_time: datetime
    raw_entry: float
    accounting_entry: float
    stop_price: float
    stop_distance: float
    quantity: float
    friction: float
    funding_pnl: float = 0.0
    funding_ids: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)

    @property
    def sign(self) -> int:
        return SIDE_SIGN[self.side]

    @property
    def entry_cost(self) -> float:
        return self.quantity * self.raw_entry * self.friction

    def exit_check(
        self, open_time: datetime, bar: tuple[float, float, float, float]
    ) -> tuple[str, float, float | None] | None:
        """(kind, raw exit, trigger) if this available bar closes the position."""
        o, h, low, _ = bar
        if open_time >= self.intended_expiry_time:
            if open_time == self.intended_expiry_time:
                return "EXPIRY", o, None
            return "EXPIRY_LATE_EXIT_DATA_MISSING", o, None
        through_open = (self.sign > 0 and o <= self.stop_price) or (
            self.sign < 0 and o >= self.stop_price
        )
        if open_time > self.entry_time and through_open:
            return "STOP_GAP", o, self.stop_price
        if (self.sign > 0 and low <= self.stop_price) or (self.sign < 0 and h >= self.stop_price):
            return "STOP", self.stop_price, self.stop_price
        return None

    def mark(self, equity: float, close: float) -> float:
        return equity + self.sign * self.quantity * (close - self.raw_entry)
