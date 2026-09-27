"""G2-01 policy, risk and execution acceptance tests (contract s.12-18)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.g2 import runs
from app.g2.bars import MinuteTape
from app.g2.contract import FRICTION_SCENARIOS
from app.g2.core import G2Core, policy, select_side
from app.g2.execution import FundingBook, OpenTrade, accounting_price, shadow_label
from app.g2.records import (
    Action,
    ClosedTrade,
    Decision,
    FundingEvent,
    OrderIntent,
    Reason,
    RiskStateEvent,
    SimulatedFill,
    StopExpiryEvent,
    UtilityView,
    record_key,
)
from app.g2.risk import (
    ExchangeFilters,
    Governor,
    filtered_quantity,
    round_quantity,
    round_stop,
    size,
)
from g2_support import full_run, minute

F = FRICTION_SCENARIOS["BASE"]
START = datetime(2001, 3, 1, tzinfo=UTC)
T = START + timedelta(hours=6)  # decision instant; funding settles at 08:00 inside the hold
M = timedelta(minutes=1)
FILTERS = ExchangeFilters("TEST_FAKE", "0.1", "0.001", "0.001", "1000", "5")


def path(
    overrides: dict[int, tuple[float, float, float, float]] | None = None,
    missing: tuple[int, ...] = (),
    hours: int = 12,
    price: float = 100.0,
):
    """Flat 1m path from START; overrides/missing keyed by minutes after T."""
    out = []
    for i in range(hours * 60):
        t = START + i * M
        k = int((t - T) // M)
        if k in missing:
            continue
        o, h, low, c = (overrides or {}).get(k, (price, price, price, price))
        out.append(minute(t, o, h, low, c))
    return out


def make_core(
    minutes, funding=((START + timedelta(hours=8), 0.0001),), filters=FILTERS, hours: int = 12
) -> G2Core:
    spec = runs.RunSpec(
        "TEST",
        "test",
        runs.SYNTHETIC,
        START,
        START + timedelta(hours=hours),
        lambda: minutes,
        lambda: list(funding),
        filters,
        lambda run_id: (),
        "",
    )
    built = runs.build(spec)
    return built.new_core(), built  # type: ignore[return-value]


def drive(core: G2Core, built, until: datetime | None = None) -> None:
    for m in built.minutes:
        if until is not None and m.available_at > until:
            break
        core.advance_to(m.open_time)
        core.ingest(m)
    core.advance_to(until or built.manifest.dataset_end)


def inject_intent(core: G2Core, side: str = "LONG", stop_distance: float = 2.0) -> OrderIntent:
    core.advance_to(T)
    intent = OrderIntent(
        record_key("G2I", core.run_id, T),
        core.run_id,
        record_key("G2D", core.run_id, T),
        side,
        T,
        T + M,
        T + timedelta(minutes=15),
        T + timedelta(hours=4),
        stop_distance,
        100.0,
        12.5,
        "MARKET_HISTORICAL_BAR_SIMULATION",
    )
    core.intent = intent
    core.governor.pending_intent = intent.intent_id
    return intent


def run_with_intent(minutes, side="LONG", **kwargs):
    core, built = make_core(minutes, **kwargs)
    early = [m for m in built.minutes if m.available_at <= T]
    for m in early:
        core.advance_to(m.open_time)
        core.ingest(m)
    inject_intent(core, side)
    for m in built.minutes:
        if m.available_at <= T:
            continue
        core.advance_to(m.open_time)
        core.ingest(m)
    core.advance_to(built.manifest.dataset_end)
    return core


# ---------------------------------------------------------------- shadow geometry


def tape_of(minutes) -> MinuteTape:
    tape = MinuteTape(START, 12 * 60)
    for m in minutes:
        tape.put(m)
    tape.advance(START + timedelta(hours=12))
    return tape


def test_shadow_long_and_short_expiry_geometry_is_exact():
    minutes = path(
        {1: (100, 100, 100, 100), 240: (101, 101, 101, 101), 119: (99.5, 99.9, 99.5, 99.9)}
    )
    funding = FundingBook([(START + timedelta(hours=8), 0.0001)])
    tape = tape_of(minutes)
    long = shadow_label(tape, funding, T, "LONG", 2.0, F)
    proxy = 99.9  # 1m close of the bar ending at the 08:00 settlement
    assert long.exit_kind == "EXPIRY" and long.exit_time == T + timedelta(hours=4)
    assert long.raw_entry == 100 and long.stop_price == 98 and long.raw_exit == 101
    net_price = 101 * (1 - F) - 100 * (1 + F)
    assert long.funding == pytest.approx(-0.0001 * proxy)
    assert long.net == pytest.approx(net_price - 0.0001 * proxy)
    assert long.net_r == pytest.approx((net_price - 0.0001 * proxy) / 2.0)
    assert long.gross == 1.0 and long.settlements == 1
    short = shadow_label(tape, funding, T, "SHORT", 2.0, F)
    assert short.stop_price == 102
    assert short.net == pytest.approx(100 * (1 - F) - 101 * (1 + F) + 0.0001 * proxy)


def test_shadow_stop_touch_gap_and_entry_bar_eligibility():
    funding = FundingBook([(START + timedelta(hours=8), 0.0001)])
    touch = shadow_label(tape_of(path({30: (99, 99, 97.5, 98.5)})), funding, T, "LONG", 2.0, F)
    assert touch.exit_kind == "STOP" and touch.raw_exit == 98 and touch.exit_time == T + 30 * M
    gap = shadow_label(tape_of(path({30: (95, 96, 94, 95)})), funding, T, "LONG", 2.0, F)
    assert gap.exit_kind == "STOP_GAP" and gap.raw_exit == 95  # worse open, not the stop
    entry_bar = shadow_label(tape_of(path({1: (100, 100, 97, 99)})), funding, T, "LONG", 2.0, F)
    assert entry_bar.exit_kind == "STOP" and entry_bar.exit_time == T + M
    short_gap = shadow_label(tape_of(path({30: (104, 105, 103, 104)})), funding, T, "SHORT", 2.0, F)
    assert short_gap.exit_kind == "STOP_GAP" and short_gap.raw_exit == 104


def test_shadow_requires_exact_entry_and_expiry_bars_and_valid_funding():
    funding = FundingBook([(START + timedelta(hours=8), 0.0001)])
    no_entry = shadow_label(tape_of(path(missing=(1,))), funding, T, "LONG", 2.0, F)
    assert no_entry.status == "UNAVAILABLE"
    assert no_entry.reasons == (Reason.EXECUTION_ENTRY_DATA_MISSING,)
    no_exit = shadow_label(tape_of(path(missing=(240,))), funding, T, "LONG", 2.0, F)
    assert no_exit.reasons == (Reason.EXECUTION_EXIT_DATA_MISSING,)
    hole = shadow_label(tape_of(path(missing=(50,))), funding, T, "LONG", 2.0, F)
    assert hole.reasons == (Reason.SOURCE_STALE_OR_INVALID,)
    no_rate = shadow_label(tape_of(path()), FundingBook([]), T, "LONG", 2.0, F)
    assert no_rate.reasons == (Reason.FUNDING_DATA_INVALID,)
    no_atr = shadow_label(tape_of(path()), funding, T, "LONG", None, F)
    assert no_atr.status == "UNAVAILABLE"


def test_funding_settlements_are_only_at_settlement_time_and_boundaries():
    book = FundingBook([(START + timedelta(hours=8, microseconds=1000), 0.0002)])
    assert book.settlements(START + timedelta(hours=7), START + timedelta(hours=8)) == [
        (START + timedelta(hours=8), 0.0002)
    ]
    assert book.settlements(START + timedelta(hours=8), START + timedelta(hours=9)) == []
    assert book.settlements(START, START + timedelta(hours=16)) == [
        (START + timedelta(hours=8), 0.0002),
        (START + timedelta(hours=16), None),  # expected boundary without a record
    ]


# ---------------------------------------------------------------- policy


def view(margin: float | None, ready: bool = True) -> UtilityView:
    status = "PREQUENTIAL_READY" if ready else "INSUFFICIENT"
    return UtilityView("X", "fit", 0.1, -0.1 if ready else None, 2000, 31.0, status, margin)


@pytest.mark.parametrize(
    ("long", "short", "expected"),
    [
        (-0.1, -0.2, ("NONE", "UTILITY_MARGIN_NOT_POSITIVE")),
        (0.0, 0.0, ("NONE", "UTILITY_MARGIN_NOT_POSITIVE")),
        (0.3, -0.1, ("LONG", "LONG_SELECTED")),
        (-0.3, 0.1, ("SHORT", "SHORT_SELECTED")),
        (0.3, 0.1, ("LONG", "LONG_SELECTED")),
        (0.1, 0.3, ("SHORT", "SHORT_SELECTED")),
        (0.3, 0.3 + 1e-6, ("NONE", "UTILITY_MARGIN_TIE")),
        (0.3, 0.3 + 2e-6, ("SHORT", "SHORT_SELECTED")),
    ],
)
def test_prudential_margin_cases(long, short, expected):
    assert select_side(long, short) == expected


def test_insufficient_evidence_and_terminal_view_override():
    assert policy(True, view(None, False), view(0.5), "UP") == (
        "NONE",
        ["INSUFFICIENT_POLICY_EVIDENCE"],
    )
    assert policy(False, view(0.5), view(-1.0), "UP")[1] == ["INSUFFICIENT_POLICY_EVIDENCE"]
    assert policy(True, view(0.5), view(-1.0), "DOWN") == (
        "LONG",
        ["LONG_SELECTED", "PATH_UTILITY_OVERRIDES_TERMINAL_VIEW"],
    )
    assert (
        policy(True, view(-0.5), view(1.0), "UP")[1][-1] == "PATH_UTILITY_OVERRIDES_TERMINAL_VIEW"
    )
    assert policy(True, view(0.5), view(-1.0), "UP") == ("LONG", ["LONG_SELECTED"])
    assert policy(True, view(0.5), view(-1.0), "NEUTRAL") == ("LONG", ["LONG_SELECTED"])


def test_full_run_actions_follow_utility_evidence_only():
    decisions = full_run().core.store.of_type(Decision)
    traded = [d for d in decisions if d.action is not Action.NO_TRADE]
    assert traded, "the synthetic path must exercise LONG/SHORT actions"
    for d in decisions:
        if d.action is not Action.NO_TRADE:
            assert d.policy_selection == f"{d.action}_SELECTED"
            assert d.long_utility.evidence_status == "PREQUENTIAL_READY"
            assert d.short_utility.evidence_status == "PREQUENTIAL_READY"
            margin = (
                d.long_utility if d.action is Action.LONG else d.short_utility
            ).prudential_margin
            assert margin is not None and margin > 0
            assert d.position_state == "FLAT" and not d.risk.drawdown_stop_active
            if (d.action is Action.LONG and d.forecast_direction == "DOWN") or (
                d.action is Action.SHORT and d.forecast_direction == "UP"
            ):
                assert "PATH_UTILITY_OVERRIDES_TERMINAL_VIEW" in d.reason_codes
        if "INSUFFICIENT_POLICY_EVIDENCE" in d.reason_codes:
            assert d.action is Action.NO_TRADE
        assert "CYCLE_SHADOW_ONLY" in d.reason_codes
    first_ready = next(
        d for d in decisions if d.long_utility.evidence_status == "PREQUENTIAL_READY"
    )
    earlier = [d for d in decisions if d.decision_time < first_ready.decision_time]
    assert all("INSUFFICIENT_POLICY_EVIDENCE" in d.reason_codes for d in earlier)


def test_full_run_one_position_no_overlap_and_blocked_while_open():
    store = full_run().core.store
    trades = store.of_type(ClosedTrade)
    for previous, current in zip(trades, trades[1:], strict=False):
        assert current.entry_time > previous.exit_time
    decisions = store.of_type(Decision)
    for trade in trades:
        held = [d for d in decisions if trade.entry_time <= d.decision_time <= trade.exit_time]
        assert held and all(d.action is Action.NO_TRADE for d in held)
        assert all("POSITION_ALREADY_OPEN" in d.reason_codes for d in held)
        # the decision at the expiry instant is still blocked (no same-candle flip/re-entry)
        assert any(d.decision_time == trade.intended_expiry_time for d in held)


# ---------------------------------------------------------------- risk


def test_risk_sizing_and_notional_cap():
    assert size(10_000.0, 2.0, 100.0) == 12.5  # 0.25% * 10000 / 2
    assert size(10_000.0, 0.01, 100.0) == 100.0  # capped at 1.0x equity / price
    assert round_quantity(0.0129, FILTERS) == 0.012
    assert round_stop(97.96, "LONG", FILTERS) == 98.0  # toward entry: risk never exceeds plan
    assert round_stop(102.04, "SHORT", FILTERS) == 102.0
    assert filtered_quantity(10_000.0, 2.0, 100.0, FILTERS) == 12.5
    tight = ExchangeFilters("TEST_FAKE", "0.1", "0.001", "0.001", "1000", "5000")
    assert filtered_quantity(10_000.0, 2.0, 100.0, tight) is None  # 1250 notional < 5000
    coarse = ExchangeFilters("TEST_FAKE", "0.1", "100", "100", "1000", "5")
    assert filtered_quantity(10_000.0, 2.0, 100.0, coarse) is None  # rounds to 0 < min qty


def test_drawdown_lock_governor():
    governor = Governor()
    assert not governor.mark_to(10_400.0)
    assert not governor.mark_to(9_881.0)  # 4.99%
    assert governor.mark_to(9_880.0)  # exactly 5% from the 10,400 peak
    assert governor.locked and not governor.mark_to(20_000.0)
    assert governor.locked  # never reset or widened


@pytest.mark.parametrize(
    ("side", "entry", "expected"),
    [
        ("LONG", True, 100 * (1 + F)),
        ("LONG", False, 100 * (1 - F)),
        ("SHORT", True, 100 * (1 - F)),
        ("SHORT", False, 100 * (1 + F)),
    ],
)
def test_adverse_friction_by_side(side, entry, expected):
    assert accounting_price(100.0, side, entry, F) == expected


def test_gap_stop_fills_at_the_worse_open():
    trade = OpenTrade(
        "t",
        "i",
        "d",
        "LONG",
        100,
        T + M,
        T + timedelta(hours=4),
        T + M,
        100,
        100 * (1 + F),
        98,
        2,
        1,
        F,
    )
    assert trade.exit_check(T + 5 * M, (95, 96, 94, 95)) == ("STOP_GAP", 95, 98)
    assert trade.exit_check(T + 5 * M, (99, 99, 97, 98)) == ("STOP", 98, 98)
    assert trade.exit_check(T + 5 * M, (99, 100, 98.5, 99)) is None
    assert trade.exit_check(T + timedelta(hours=4), (90, 91, 89, 90))[0] == "EXPIRY"


# ---------------------------------------------------------------- core execution paths


def test_core_fill_funding_expiry_and_accounting():
    core = run_with_intent(path({119: (100, 100.5, 100, 100.5), 240: (101, 101, 101, 101)}))
    store = core.store
    entry, exit_fill = store.of_type(SimulatedFill)
    assert entry.kind == "ENTRY" and entry.event_time == T + M and entry.available_at == T + 2 * M
    assert entry.raw_price == 100 and entry.quantity == 12.5
    (funding,) = store.of_type(FundingEvent)
    assert funding.funding_time == START + timedelta(hours=8) and funding.status == "SETTLED"
    assert funding.amount == pytest.approx(-0.0001 * 12.5 * 100.5)
    (event,) = store.of_type(StopExpiryEvent)
    assert event.kind == "EXPIRY" and exit_fill.raw_price == 101
    (trade,) = store.of_type(ClosedTrade)
    friction = 12.5 * F * (100 + 101)
    assert trade.friction_cost == pytest.approx(friction)
    assert trade.net_pnl == pytest.approx(12.5 * 1 - friction + funding.amount)
    assert trade.realized_net_r == pytest.approx(trade.net_pnl / (12.5 * 2.0))
    assert core.governor.equity == pytest.approx(10_000 + trade.net_pnl)
    assert trade.violation_flags == ()
    blocked = [d for d in store.of_type(Decision) if T < d.decision_time <= T + timedelta(hours=4)]
    assert blocked and all("POSITION_ALREADY_OPEN" in d.reason_codes for d in blocked)


def test_core_entry_missing_and_filter_veto_fail_closed():
    core = run_with_intent(path(missing=(1,)))
    (rejected,) = core.store.of_type(SimulatedFill)
    assert rejected.kind == "ENTRY_REJECTED"
    assert rejected.reason_codes == ("EXECUTION_ENTRY_DATA_MISSING",)
    assert not core.store.of_type(ClosedTrade) and core.governor.flat
    tight = ExchangeFilters("TEST_FAKE", "0.1", "0.001", "0.001", "1000", "1000000")
    core = run_with_intent(path(), filters=tight)
    (rejected,) = core.store.of_type(SimulatedFill)
    assert rejected.reason_codes == ("CONTRACT_FILTER_NOT_MET",)


def test_core_missing_expiry_bar_and_invalid_funding_are_flagged():
    core = run_with_intent(path(missing=(240,)), funding=())
    (trade,) = core.store.of_type(ClosedTrade)
    assert trade.exit_kind == "EXPIRY_LATE_EXIT_DATA_MISSING"
    assert trade.exit_time == T + timedelta(hours=4, minutes=1)
    assert "EXECUTION_EXIT_DATA_MISSING" in trade.violation_flags
    assert "FUNDING_DATA_INVALID" in trade.violation_flags
    (funding,) = core.store.of_type(FundingEvent)
    assert funding.status == "FUNDING_DATA_INVALID" and funding.amount == 0.0


def test_core_gap_stop_and_drawdown_lock():
    core = run_with_intent(path({30: (40, 41, 39, 40)}))
    (trade,) = core.store.of_type(ClosedTrade)
    assert trade.exit_kind == "STOP_GAP" and trade.raw_exit == 40
    kinds = [e.kind for e in core.store.of_type(RiskStateEvent)]
    assert "DRAWDOWN_STOP_TRIGGERED" in kinds and core.governor.locked
    later = [d for d in core.store.of_type(Decision) if d.decision_time > T + 31 * M]
    assert later and all("PATH_DRAWDOWN_STOP_ACTIVE" in d.reason_codes for d in later)
    assert all(d.action is Action.NO_TRADE for d in later)


# ---------------------------------------------------------------- Gate-B corrections (B-01/B-02)


def risk_events(core: G2Core) -> dict[str, RiskStateEvent]:
    return {e.kind: e for e in core.store.of_type(RiskStateEvent)}


def test_entry_exit_and_funding_risk_events_are_post_event_and_fresh():
    core = run_with_intent(path({119: (100, 100.5, 100, 100.5), 240: (101, 101, 101, 101)}))
    events = risk_events(core)
    entry, funding, exit_ = events["ENTRY"], events["FUNDING"], events["EXIT"]
    entry_cost = 12.5 * 100 * F
    assert entry.equity == pytest.approx(10_000 - entry_cost)  # post-entry friction
    assert (
        entry.marked_equity == pytest.approx(entry.equity)
        and entry.mark_basis == "ENTRY_FILL_PRICE"
    )
    assert entry.drawdown == pytest.approx(1 - entry.marked_equity / entry.peak_equity)
    assert entry.position_open and entry.available_at == T + 2 * M
    (settlement,) = core.store.of_type(FundingEvent)
    assert funding.equity == pytest.approx(entry.equity + settlement.amount)
    assert funding.marked_equity == pytest.approx(funding.equity + 12.5 * (100.5 - 100))
    assert funding.mark_basis == "FUNDING_PRICE_PROXY" and funding.position_open
    (trade,) = core.store.of_type(ClosedTrade)
    assert not exit_.position_open and exit_.mark_basis == "FLAT_AFTER_EXIT"
    assert exit_.equity == pytest.approx(10_000 + trade.net_pnl)  # includes the exit friction
    assert exit_.marked_equity == pytest.approx(exit_.equity)
    assert exit_.drawdown == pytest.approx(max(0.0, 1 - exit_.marked_equity / exit_.peak_equity))


def test_funding_that_crosses_the_drawdown_threshold_locks_at_the_same_instant():
    settlement = START + timedelta(hours=8)
    core = run_with_intent(path(), funding=((settlement, 0.45),))  # 562.5 USDT: > 5% alone
    events = {e.kind: e for e in core.store.of_type(RiskStateEvent)}
    lock, funding = events["DRAWDOWN_STOP_TRIGGERED"], events["FUNDING"]
    assert lock.available_at == funding.available_at == settlement
    assert funding.drawdown_stop_active and funding.drawdown >= 0.05
    at_settlement = next(d for d in core.store.of_type(Decision) if d.decision_time == settlement)
    assert "PATH_DRAWDOWN_STOP_ACTIVE" in at_settlement.reason_codes
    assert at_settlement.risk.drawdown_stop_active
    before = next(
        d
        for d in core.store.of_type(Decision)
        if d.decision_time == settlement - timedelta(minutes=15)
    )
    assert not before.risk.drawdown_stop_active


def test_decision_position_open_means_an_actual_open_trade_only():
    core, built = make_core(path())
    for m in built.minutes:
        if m.available_at > T:
            break
        core.advance_to(m.open_time)
        core.ingest(m)
    core.advance_to(T)
    entry = T + timedelta(minutes=16)
    intent = OrderIntent(
        record_key("G2I", core.run_id, T),
        core.run_id,
        record_key("G2D", core.run_id, T),
        "LONG",
        T,
        entry,
        entry + timedelta(minutes=14),
        entry + timedelta(hours=4) - M,
        2.0,
        100.0,
        12.5,
        "MARKET_HISTORICAL_BAR_SIMULATION",
    )
    core.intent = intent
    core.governor.pending_intent = intent.intent_id
    drive_rest = [m for m in built.minutes if m.available_at > T]
    for m in drive_rest:
        core.advance_to(m.open_time)
        core.ingest(m)
    core.advance_to(built.manifest.dataset_end)
    decisions = {d.decision_time: d for d in core.store.of_type(Decision)}
    pending = decisions[T + timedelta(minutes=15)]
    assert pending.position_state == "ENTRY_PENDING"
    assert pending.risk.position_open is False and pending.risk.open_trade_id is None
    assert "POSITION_ALREADY_OPEN" in pending.reason_codes  # still blocked from a new entry
    held = decisions[T + timedelta(minutes=30)]
    assert held.position_state == "OPEN" and held.risk.position_open is True
