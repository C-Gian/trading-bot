"""Native bidirectional reference-paper ledger (core contracts sections 10-11).

This adapts the existing LONG-only accounting of `app.backtest` rather than forking it:

- the cost primitives are the same `CostModel` (10 bp fee + 2 bp adverse friction per side, the
  inherited nominal 24 bp round trip) and the same basis-point arithmetic;
- the LONG-only assumptions of `app.backtest.engine.simulate` are made explicit and signed: the
  side sign `s` (+1 LONG, -1 SHORT) replaces the hard-coded LONG direction in the price P&L, the
  adverse-friction direction, stop/objective ordering, gap detection and collision handling;
- for LONG trades the signed ledger reproduces the legacy engine's effective prices and net P&L per
  unit (see `backend/tests/test_g1_ledger.py`), so there is one accounting semantics, not two.

The legacy engine itself is left byte-stable because frozen historical experiments depend on it.

Reference instrument: BTCUSDT USD-M traded-price series for LONG and SHORT. This is a paper
reference model — no margin, liquidation or live-account fidelity is claimed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal

from app.backtest.models import CostModel

from .bars import MINUTE, Bar
from .canonical import content_id
from .records import (
    ClosedTrade,
    FillKind,
    LedgerSnapshot,
    OrderFillEvent,
    Side,
    TradePlan,
)

BPS = Decimal(10000)
COST_CONTRACT_VERSION = "G1_REFERENCE_PAPER_COST_V1_24BP_ROUND_TRIP_PLUS_FUNDING"
# V2 (ADR-0045): the architecture's frozen 1-minute primary operational delay after readiness.
RISK_CONTRACT_VERSION = "G1_RISK_V2_025PCT_1X_1PCT_DAY_5PCT_RUN_ONE_POSITION_1M_PRIMARY_DELAY"
PRIMARY_DELAY_MINUTES = 1
DELAY_STRESS_MINUTES = 5  # later robustness view, relative to the primary delay
QUANTITY_STEP = Decimal("0.000001")
FUNDING_HOURS = (0, 8, 16)


@dataclass(frozen=True)
class RiskPolicy:
    initial_equity: Decimal = Decimal(10000)
    risk_fraction: Decimal = Decimal("0.0025")
    max_gross_notional_multiple: Decimal = Decimal(1)
    daily_loss_stop_fraction: Decimal = Decimal("0.01")
    run_drawdown_stop_fraction: Decimal = Decimal("0.05")
    max_hold_minutes: int = 240
    operational_delay_minutes: int = PRIMARY_DELAY_MINUTES
    version: str = RISK_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not 1 <= self.max_hold_minutes <= 240:
            raise ValueError("G1 maximum hold is at most 4h")
        if self.max_gross_notional_multiple > 1:
            raise ValueError("G1 gross notional is at most 1x virtual equity")


def effective_entry(side: Side, raw: Decimal, costs: CostModel) -> Decimal:
    """Adverse entry friction: LONG pays up, SHORT sells down."""
    return raw * (BPS + side.sign * costs.entry_friction_bps) / BPS


def effective_exit(side: Side, raw: Decimal, costs: CostModel) -> Decimal:
    """Adverse exit friction: LONG sells down, SHORT buys back up."""
    return raw * (BPS - side.sign * costs.exit_friction_bps) / BPS


def size_position(
    side: Side, fill_price: Decimal, stop: Decimal, equity: Decimal, policy: RiskPolicy
) -> tuple[Decimal, Decimal] | None:
    """0.25% planned equity risk, capped at 1x gross notional. None if the stop is not adverse."""
    per_unit_risk = side.sign * (fill_price - stop)
    if per_unit_risk <= 0:
        return None
    risk_amount = equity * policy.risk_fraction
    by_risk = risk_amount / per_unit_risk
    by_notional = equity * policy.max_gross_notional_multiple / fill_price
    quantity = min(by_risk, by_notional).quantize(QUANTITY_STEP, rounding=ROUND_DOWN)
    return (quantity, risk_amount) if quantity > 0 else None


def is_funding_time(moment: datetime) -> bool:
    return moment.minute == 0 and moment.hour in FUNDING_HOURS


@dataclass
class _Pending:
    plan: TradePlan


@dataclass
class _Open:
    plan: TradePlan
    entry_time: datetime
    entry_raw: Decimal
    entry_effective: Decimal
    quantity: Decimal
    risk_amount: Decimal
    entry_fee: Decimal
    entry_friction: Decimal
    funding: Decimal
    expiry: datetime
    gap_pending: bool = False


class ReferenceLedger:
    """Signed one-position paper ledger with G1 risk controls.

    It is driven minute by minute by the core with the completed 1m bar (or `None` for a missing
    minute). It never looks at a bar that has not closed.
    """

    def __init__(self, policy: RiskPolicy | None = None, costs: CostModel | None = None) -> None:
        self.policy = policy or RiskPolicy()
        self.costs = costs or CostModel()
        self.equity = self.policy.initial_equity
        self.peak_equity = self.equity
        self.day_start_equity = self.equity
        self.current_day: datetime | None = None
        self.run_entry_stop = False
        self.pending: _Pending | None = None
        self.position: _Open | None = None
        self.last_mark: Decimal | None = None
        self.events: list[OrderFillEvent] = []
        self.trades: list[ClosedTrade] = []

    # ------------------------------------------------------------------ risk state
    def roll_day(self, moment: datetime) -> None:
        day = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.current_day != day:
            self.current_day = day
            self.day_start_equity = self.equity

    @property
    def occupied(self) -> bool:
        return self.pending is not None or self.position is not None

    @property
    def day_loss_fraction(self) -> Decimal:
        loss = self.day_start_equity - self.equity
        return max(Decimal(0), loss / self.day_start_equity)

    @property
    def drawdown_fraction(self) -> Decimal:
        return max(Decimal(0), (self.peak_equity - self.equity) / self.peak_equity)

    @property
    def daily_entry_stop(self) -> bool:
        return self.day_loss_fraction >= self.policy.daily_loss_stop_fraction

    def entry_blockers(self) -> tuple[str, ...]:
        blockers = []
        if self.occupied:
            blockers.append("POSITION_OCCUPIED")
        if self.daily_entry_stop:
            blockers.append("DAILY_LOSS_ENTRY_STOP")
        if self.run_entry_stop:
            blockers.append("RUN_DRAWDOWN_ENTRY_STOP")
        return tuple(blockers)

    # ------------------------------------------------------------------ plans / fills
    def submit(self, plan: TradePlan) -> None:
        if self.entry_blockers():
            raise ValueError(f"entry refused: {self.entry_blockers()}")
        self.pending = _Pending(plan)

    def _event(
        self,
        plan: TradePlan,
        kind: FillKind,
        when: datetime,
        reason: str,
        raw: Decimal | None = None,
        effective: Decimal | None = None,
        quantity: Decimal | None = None,
        fee: Decimal = Decimal(0),
        friction: Decimal = Decimal(0),
        funding: Decimal = Decimal(0),
        available_at: datetime | None = None,
    ) -> OrderFillEvent:
        payload = (plan.trade_plan_id, kind, when, reason, raw, quantity, funding)
        event = OrderFillEvent(
            content_id("FIL", payload),
            plan.trade_plan_id,
            kind,
            plan.side,
            when,
            available_at or when + MINUTE,
            raw,
            effective,
            quantity,
            fee,
            friction,
            funding,
            reason,
        )
        self.events.append(event)
        return event

    def on_minute(self, minute_open: datetime, bar: Bar | None) -> list[OrderFillEvent]:
        """Process the 1m interval starting at `minute_open`; `bar` is None if it is missing."""
        start = len(self.events)
        self.roll_day(minute_open)
        if self.pending is not None:
            self._try_entry(minute_open, bar)
        if self.position is not None:
            self._manage(minute_open, bar)
        if bar is not None:
            self.last_mark = bar.close
        return self.events[start:]

    def _try_entry(self, minute_open: datetime, bar: Bar | None) -> None:
        assert self.pending is not None
        plan = self.pending.plan
        eligible = plan.readiness_time + timedelta(minutes=plan.operational_delay_minutes)
        if minute_open < eligible:
            return
        self.pending = None
        if minute_open >= plan.entry_expiry:
            self._event(plan, FillKind.ENTRY_REJECTED, minute_open, "ENTRY_EXPIRED")
            return
        if bar is None:
            # The next eligible minute is missing: the entry is rejected, never rolled forward.
            self._event(plan, FillKind.ENTRY_REJECTED, minute_open, "REJECTED_MISSING_MINUTE")
            return
        side = plan.side
        sized = size_position(side, bar.open, plan.stop_price, self.equity, self.policy)
        adverse_objective = side.sign * (plan.objective_price - bar.open) <= 0
        if sized is None or adverse_objective:
            self._event(plan, FillKind.ENTRY_REJECTED, minute_open, "REJECTED_NON_TRADABLE_GAP")
            return
        quantity, risk_amount = sized
        effective = effective_entry(side, bar.open, self.costs)
        fee = effective * quantity * self.costs.entry_fee_bps / BPS
        friction = side.sign * (effective - bar.open) * quantity
        self.position = _Open(
            plan,
            minute_open,
            bar.open,
            effective,
            quantity,
            risk_amount,
            fee,
            friction,
            Decimal(0),
            minute_open + timedelta(minutes=plan.max_hold_minutes),
        )
        self._event(
            plan,
            FillKind.ENTRY,
            minute_open,
            "NEXT_ELIGIBLE_1M_OPEN",
            bar.open,
            effective,
            quantity,
            fee,
            friction,
        )

    def _manage(self, minute_open: datetime, bar: Bar | None) -> None:
        position = self.position
        assert position is not None
        if bar is None:
            position.gap_pending = True
            return
        plan, sign = position.plan, position.plan.side.sign
        stop, objective = plan.stop_price, plan.objective_price
        if position.gap_pending:
            self._close(minute_open, bar.open, "DATA_GAP_EXIT_UNSCORABLE", scorable=False)
            return
        # Adverse gap through the stop: filled at the (worse) open, never at the stop.
        if sign * (bar.open - stop) < 0:
            self._close(minute_open, bar.open, "STOP_GAP")
            return
        if sign * (bar.open - objective) >= 0:
            # A favorable gap is credited only at the objective, never better.
            self._close(minute_open, objective, "OBJECTIVE")
            return
        adverse = bar.low if sign > 0 else bar.high
        favorable = bar.high if sign > 0 else bar.low
        stop_hit = sign * (adverse - stop) <= 0
        objective_hit = sign * (favorable - objective) >= 0
        if stop_hit and objective_hit:
            self._close(minute_open, stop, "STOP_SAME_MINUTE_COLLISION_CONSERVATIVE")
            return
        if stop_hit:
            self._close(minute_open, stop, "STOP")
            return
        if objective_hit:
            self._close(minute_open, objective, "OBJECTIVE")
            return
        if minute_open + MINUTE >= position.expiry:
            self._close(
                minute_open + MINUTE, bar.close, "MAX_HOLD_EXPIRY", event_minute=minute_open
            )

    def _close(
        self,
        when: datetime,
        raw: Decimal,
        reason: str,
        scorable: bool = True,
        event_minute: datetime | None = None,
    ) -> None:
        position = self.position
        assert position is not None
        plan, side = position.plan, position.plan.side
        effective = effective_exit(side, raw, self.costs)
        fee = effective * position.quantity * self.costs.exit_fee_bps / BPS
        friction = side.sign * (raw - effective) * position.quantity
        gross = side.sign * (raw - position.entry_raw) * position.quantity
        net = (
            side.sign * (effective - position.entry_effective) * position.quantity
            - position.entry_fee
            - fee
            + position.funding
        )
        self._event(
            plan,
            FillKind.EXIT,
            when,
            reason,
            raw,
            effective,
            position.quantity,
            fee,
            friction,
            available_at=(event_minute or when) + MINUTE,
        )
        trade = ClosedTrade(
            content_id("TRD", (plan.trade_plan_id, when, reason)),
            plan.trade_plan_id,
            side,
            plan.playbook_id,
            position.entry_time,
            when,
            position.entry_raw,
            raw,
            position.entry_effective,
            effective,
            position.quantity,
            position.entry_raw * position.quantity,
            gross,
            position.entry_fee + fee,
            position.entry_friction + friction,
            position.funding,
            net,
            position.risk_amount,
            net / position.risk_amount,
            reason,
            scorable,
            int((when - position.entry_time).total_seconds() // 60),
        )
        self.trades.append(trade)
        self.position = None
        self.equity += net - position.funding  # funding was already booked when settled
        self.peak_equity = max(self.peak_equity, self.equity)
        if self.drawdown_fraction >= self.policy.run_drawdown_stop_fraction:
            self.run_entry_stop = True

    def finalize(self, moment: datetime) -> None:
        """Unresolved end state: drop a pending entry; close an open position at the last observed
        close as UNSCORABLE (it never counts as scored economics)."""
        if self.pending is not None:
            self._event(
                self.pending.plan, FillKind.ENTRY_REJECTED, moment, "UNRESOLVED_END_OF_WINDOW"
            )
            self.pending = None
        if self.position is not None:
            mark = self.last_mark if self.last_mark is not None else self.position.entry_raw
            self._close(moment, mark, "UNRESOLVED_END_OF_WINDOW_UNSCORABLE", scorable=False)

    def settle_funding(self, moment: datetime, rate: Decimal, mark: Decimal) -> None:
        """Signed funding at a settlement instant for a position held across it.

        A positive rate debits LONG and credits SHORT; a negative rate the reverse.
        """
        position = self.position
        if position is None or position.entry_time >= moment:
            return
        amount = -position.plan.side.sign * rate * mark * position.quantity
        position.funding += amount
        self.equity += amount
        self.peak_equity = max(self.peak_equity, self.equity)
        if self.drawdown_fraction >= self.policy.run_drawdown_stop_fraction:
            self.run_entry_stop = True
        self._event(
            position.plan,
            FillKind.FUNDING,
            moment,
            f"FUNDING_RATE_{rate}",
            mark,
            None,
            position.quantity,
            funding=amount,
            available_at=moment,
        )

    def snapshot(self, as_of: datetime) -> LedgerSnapshot:
        position = self.position
        unrealized = Decimal(0)
        if position is not None and self.last_mark is not None:
            unrealized = (
                position.plan.side.sign
                * (self.last_mark - position.entry_raw)
                * (position.quantity)
            )
        return LedgerSnapshot(
            as_of,
            self.equity,
            self.peak_equity,
            self.drawdown_fraction,
            self.day_start_equity,
            self.day_loss_fraction,
            None if position is None else position.plan.trade_plan_id,
            None if position is None else position.plan.side,
            Decimal(0) if position is None else position.quantity,
            unrealized,
            self.daily_entry_stop,
            self.run_entry_stop,
        )


def with_delay(plan: TradePlan, minutes: int) -> TradePlan:
    """A +delay operational stress view of the same plan (robustness, not a new strategy)."""
    return replace(plan, operational_delay_minutes=plan.operational_delay_minutes + minutes)
