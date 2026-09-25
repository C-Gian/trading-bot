"""System G1 Checkpoint 1: the native bidirectional reference-paper ledger on synthetic paths."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.backtest.engine import simulate
from app.backtest.models import Bar as LegacyBar
from app.backtest.models import CostModel, ExitReason, Intent
from app.g1.bars import MINUTE, minute_bar
from app.g1.ledger import (
    ReferenceLedger,
    RiskPolicy,
    effective_entry,
    effective_exit,
    size_position,
)
from app.g1.records import Conviction, FillKind, Playbook, Side, TradePlan

D = Decimal
T0 = datetime(2001, 3, 5, 6, tzinfo=UTC)


def plan(
    side: Side,
    stop: str,
    objective: str,
    readiness: datetime = T0,
    delay: int = 0,
    max_hold: int = 240,
    name: str = "p",
) -> TradePlan:
    return TradePlan(
        f"PLN-{name}",
        "RUN-test",
        f"DEC-{name}",
        side,
        Playbook.P1.value,
        "TEST",
        readiness,
        readiness,
        delay,
        "NEXT_ELIGIBLE_1M_OPEN_AFTER_READINESS_PLUS_DELAY",
        readiness + timedelta(minutes=delay + 15),
        D("100"),
        D(stop),
        D(objective),
        max_hold,
        D("2"),
        "TEST",
        "TEST",
        D("10000"),
        D("25"),
        D("10000"),
        "TEST",
        Conviction.HIGH,
        (),
        (),
        "TEST",
    )


def bar(offset: int, o: str, h: str, low: str, c: str, start: datetime = T0):
    return minute_bar(start + offset * MINUTE, D(o), D(h), D(low), D(c))


def drive(ledger: ReferenceLedger, path, start: datetime = T0, minutes: int | None = None):
    by_time = {b.open_time: b for b in path}
    count = minutes if minutes is not None else len(path)
    for index in range(count):
        moment = start + index * MINUTE
        ledger.on_minute(moment, by_time.get(moment))
    return ledger


def flat(count: int, price: str = "100", start: datetime = T0):
    return [bar(i, price, price, price, price, start) for i in range(count)]


def test_long_and_short_signed_pnl_and_adverse_costs() -> None:
    zero = CostModel(
        entry_fee_bps=D(0), exit_fee_bps=D(0), entry_friction_bps=D(0), exit_friction_bps=D(0)
    )
    for side, exit_price, expected_sign in (
        (Side.LONG, "102", 1),
        (Side.LONG, "98", -1),
        (Side.SHORT, "98", 1),
        (Side.SHORT, "102", -1),
    ):
        ledger = ReferenceLedger(costs=zero)
        ledger.submit(
            plan(
                side,
                "90" if side is Side.LONG else "110",
                "150" if side is Side.LONG else "50",
                max_hold=2,
            )
        )
        drive(ledger, [bar(0, "100", "100", "100", "100"), bar(1, "100", "102", "98", exit_price)])
        trade = ledger.trades[0]
        assert trade.exit_reason == "MAX_HOLD_EXPIRY"
        assert (trade.net_pnl > 0) == (expected_sign > 0) and trade.net_pnl == trade.gross_price_pnl
        assert trade.gross_price_pnl == side.sign * (D(exit_price) - D(100)) * trade.quantity
    costs = CostModel()
    assert (
        effective_entry(Side.LONG, D(100), costs)
        > D(100)
        > effective_entry(Side.SHORT, D(100), costs)
    )
    assert (
        effective_exit(Side.LONG, D(100), costs)
        < D(100)
        < effective_exit(Side.SHORT, D(100), costs)
    )
    for side in Side:
        ledger = ReferenceLedger()
        stop, objective = ("90", "150") if side is Side.LONG else ("110", "50")
        ledger.submit(plan(side, stop, objective, max_hold=2))
        drive(ledger, flat(2))
        trade = ledger.trades[0]
        # A flat path loses exactly fees plus adverse friction, whatever the side.
        assert trade.gross_price_pnl == 0 and trade.net_pnl < 0
        assert trade.fees > 0 and trade.friction_cost > 0
        assert trade.net_pnl == -(trade.fees + trade.friction_cost)
        assert ledger.equity == D("10000") + trade.net_pnl


def test_quantity_notional_equity_and_sizing_caps() -> None:
    policy = RiskPolicy()
    quantity, risk = size_position(Side.LONG, D(100), D(99), D(10000), policy)  # type: ignore[misc]
    assert risk == D(25) and quantity * D(100) <= D(10000)
    assert quantity == D(25)  # 0.25% risk: 25 / 1 per unit
    capped, _ = size_position(Side.SHORT, D(100), D("100.01"), D(10000), policy)  # type: ignore[misc]
    assert capped == D(100)  # risk sizing would need 2500 units; notional cap is 1x equity
    assert size_position(Side.LONG, D(100), D(101), D(10000), policy) is None
    assert size_position(Side.SHORT, D(100), D(99), D(10000), policy) is None
    with pytest.raises(ValueError):
        RiskPolicy(max_gross_notional_multiple=D(2))
    with pytest.raises(ValueError):
        RiskPolicy(max_hold_minutes=241)


def test_funding_credit_and_debit_are_signed() -> None:
    settle = T0 + timedelta(minutes=2)
    for side, rate, sign in (
        (Side.LONG, "0.0001", -1),
        (Side.SHORT, "0.0001", 1),
        (Side.LONG, "-0.0001", 1),
        (Side.SHORT, "-0.0001", -1),
    ):
        ledger = ReferenceLedger()
        stop, objective = ("90", "150") if side is Side.LONG else ("110", "50")
        ledger.submit(plan(side, stop, objective, max_hold=5))
        drive(ledger, flat(2))
        before = ledger.equity
        ledger.settle_funding(settle, D(rate), D(100))
        funding = ledger.events[-1]
        assert funding.kind is FillKind.FUNDING
        assert (funding.funding_amount > 0) == (sign > 0)
        assert ledger.equity - before == funding.funding_amount
        drive(ledger, flat(5), T0 + 2 * MINUTE)
        trade = ledger.trades[0]
        assert trade.funding == funding.funding_amount
        assert trade.net_pnl == -(trade.fees + trade.friction_cost) + trade.funding
        assert ledger.equity == D("10000") + trade.net_pnl
    idle = ReferenceLedger()
    idle.settle_funding(settle, D("0.0001"), D(100))
    assert idle.events == [] and idle.equity == D("10000")


def test_fill_is_next_eligible_minute_after_readiness_and_delay() -> None:
    ledger = ReferenceLedger()
    ledger.submit(plan(Side.LONG, "90", "150", readiness=T0 + 3 * MINUTE, delay=5))
    drive(
        ledger, [bar(i, str(100 + i), str(100 + i), str(100 + i), str(100 + i)) for i in range(12)]
    )
    entry = next(e for e in ledger.events if e.kind is FillKind.ENTRY)
    assert entry.event_time == T0 + 8 * MINUTE and entry.raw_price == D(108)
    assert entry.available_at == entry.event_time + MINUTE


def test_missing_eligible_minute_rejects_entry_without_rolling_forward() -> None:
    ledger = ReferenceLedger()
    ledger.submit(plan(Side.SHORT, "110", "50"))
    drive(ledger, flat(5)[1:], minutes=5)
    assert [e.kind for e in ledger.events] == [FillKind.ENTRY_REJECTED]
    assert ledger.events[0].reason == "REJECTED_MISSING_MINUTE"
    assert ledger.position is None and ledger.pending is None and not ledger.trades


def test_missing_minute_while_open_is_unscorable() -> None:
    ledger = ReferenceLedger()
    ledger.submit(plan(Side.LONG, "90", "150"))
    path = [b for b in flat(6) if b.open_time != T0 + 2 * MINUTE]
    drive(ledger, path, minutes=6)
    trade = ledger.trades[0]
    assert trade.exit_reason == "DATA_GAP_EXIT_UNSCORABLE" and trade.scorable is False
    assert trade.exit_time == T0 + 3 * MINUTE


@pytest.mark.parametrize("side", list(Side))
def test_adverse_gap_fills_at_the_worse_open(side: Side) -> None:
    ledger = ReferenceLedger()
    stop, objective = ("99", "105") if side is Side.LONG else ("101", "95")
    gap_open = "97" if side is Side.LONG else "103"
    ledger.submit(plan(side, stop, objective))
    drive(
        ledger, [bar(0, "100", "100", "100", "100"), bar(1, gap_open, gap_open, gap_open, gap_open)]
    )
    trade = ledger.trades[0]
    assert trade.exit_reason == "STOP_GAP" and trade.exit_raw_price == D(gap_open)
    assert side.sign * (trade.exit_raw_price - D(stop)) < 0


@pytest.mark.parametrize("side", list(Side))
def test_favorable_gap_is_credited_only_at_the_objective(side: Side) -> None:
    ledger = ReferenceLedger()
    stop, objective = ("99", "102") if side is Side.LONG else ("101", "98")
    gap_open = "105" if side is Side.LONG else "95"
    ledger.submit(plan(side, stop, objective))
    drive(
        ledger, [bar(0, "100", "100", "100", "100"), bar(1, gap_open, gap_open, gap_open, gap_open)]
    )
    assert ledger.trades[0].exit_reason == "OBJECTIVE"
    assert ledger.trades[0].exit_raw_price == D(objective)


@pytest.mark.parametrize("side", list(Side))
def test_same_minute_stop_objective_collision_resolves_to_stop(side: Side) -> None:
    ledger = ReferenceLedger()
    stop, objective = ("99", "101") if side is Side.LONG else ("101", "99")
    ledger.submit(plan(side, stop, objective))
    drive(ledger, [bar(0, "100", "100", "100", "100"), bar(1, "100", "102", "98", "100")])
    trade = ledger.trades[0]
    assert trade.exit_reason == "STOP_SAME_MINUTE_COLLISION_CONSERVATIVE"
    assert trade.exit_raw_price == D(stop) and trade.net_pnl < 0


def test_maximum_hold_expiry() -> None:
    ledger = ReferenceLedger()
    ledger.submit(plan(Side.SHORT, "110", "50", max_hold=240))
    drive(ledger, flat(300))
    trade = ledger.trades[0]
    assert trade.exit_reason == "MAX_HOLD_EXPIRY" and trade.holding_minutes == 240
    assert trade.exit_time == T0 + timedelta(minutes=240)


def test_one_position_no_pyramiding_or_hedging() -> None:
    ledger = ReferenceLedger()
    ledger.submit(plan(Side.LONG, "90", "150"))
    assert ledger.entry_blockers() == ("POSITION_OCCUPIED",)
    for side in Side:
        with pytest.raises(ValueError):
            ledger.submit(
                plan(
                    side,
                    "90" if side is Side.LONG else "110",
                    "150" if side is Side.LONG else "50",
                    name="second",
                )
            )
    drive(ledger, flat(3))
    assert ledger.position is not None and ledger.entry_blockers() == ("POSITION_OCCUPIED",)


def _lose(ledger: ReferenceLedger, start: datetime, name: str) -> None:
    ledger.submit(plan(Side.LONG, "99", "150", readiness=start, name=name))
    drive(
        ledger,
        [bar(0, "100", "100", "100", "100", start), bar(1, "100", "100", "98", "98", start)],
        start,
    )


def test_daily_entry_stop_after_one_percent_loss_resets_next_utc_day() -> None:
    ledger = ReferenceLedger()
    losses = 0
    while not ledger.daily_entry_stop:
        _lose(ledger, T0 + timedelta(minutes=10 * losses), f"loss{losses}")
        losses += 1
    assert losses == 4  # ~0.31% per stopped trade: 0.25% risk + fees and friction
    assert "DAILY_LOSS_ENTRY_STOP" in ledger.entry_blockers()
    assert ledger.day_loss_fraction >= D("0.01")
    ledger.roll_day(T0 + timedelta(days=1))
    assert not ledger.daily_entry_stop and ledger.entry_blockers() == ()


def test_run_drawdown_entry_stop_after_five_percent() -> None:
    ledger = ReferenceLedger()
    day = 0
    while not ledger.run_entry_stop:
        start = T0 + timedelta(days=day)
        ledger.roll_day(start)
        _lose(ledger, start, f"dd{day}")
        day += 1
    assert ledger.drawdown_fraction >= D("0.05") and day >= 12
    ledger.roll_day(T0 + timedelta(days=day + 1))
    assert "RUN_DRAWDOWN_ENTRY_STOP" in ledger.entry_blockers()


def test_long_accounting_reconciles_with_the_legacy_long_only_engine() -> None:
    """One accounting semantics: the signed ledger reproduces the legacy LONG engine per unit."""
    start = datetime(2020, 3, 2, 12, tzinfo=UTC)
    prices = ["100", "100.5", "101", "100.2", "102.5", "103"]
    path = []
    for i, p in enumerate(prices):
        close = prices[min(i + 1, 5)]
        high, low = max(D(p), D(close)) + D("0.3"), min(D(p), D(close)) - D("0.3")
        path.append(bar(i, p, str(high), str(low), close, start))
    legacy_path = [LegacyBar(b.open_time, b.open, b.high, b.low, b.close) for b in path]
    intent = Intent("r", "s", "m", "h", start, "LONG", "NEXT_1M_OPEN", D("98"), D("102"), None, 240)
    legacy = simulate(intent, legacy_path)
    assert legacy.exit_reason is ExitReason.TARGET
    ledger = ReferenceLedger()
    ledger.submit(plan(Side.LONG, "98", "102", readiness=start))
    drive(ledger, path, start)
    trade = ledger.trades[0]
    assert trade.exit_reason == "OBJECTIVE" and trade.exit_time == legacy.exit_timestamp
    assert trade.entry_effective_price == legacy.entry_effective_price
    assert trade.exit_effective_price == legacy.exit_effective_price
    per_unit = trade.net_pnl / trade.quantity
    assert abs(per_unit - legacy.net_pnl) < D("1e-18")  # type: ignore[operator]
