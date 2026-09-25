"""System G1 Development V1: ADR-0046 cycle qualifier and frozen shared indicators."""

from __future__ import annotations

import dataclasses
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.g1.bars import Bar, minute_bar
from app.g1.cycle import (
    CYCLE_DECISION_ACTIVATION,
    MIXED_OR_WEAK,
    SCALES,
    SUPPORTS_LONG,
    SUPPORTS_SHORT,
    CycleEngine,
    decision_timing_qualifier,
    timing_qualifier,
)
from app.g1.indicators import (
    BEARISH,
    BULLISH,
    DAILY_BEAR,
    DAILY_BULL,
    DAILY_NEUTRAL,
    NEUTRAL,
    RANGE,
    TRANSITION,
    TREND_BEAR,
    TREND_BULL,
    UNAVAILABLE,
    DailyContext,
    Ema,
    HourStructure,
    Participation,
    SessionVwap,
    WilderAdx,
    WilderAtr,
    regime,
)
from app.g1.records import SignalRole, TurnEvent

D = Decimal
T0 = datetime(2001, 3, 5, tzinfo=UTC)


def scale_states(labels, slopes, turns=None):
    base = CycleEngine().snapshot("RUN-x", T0).scales
    turns = turns or [None] * 6
    out = []
    for state, label, slope, turn in zip(base, labels, slopes, turns, strict=True):
        event = None if turn is None else TurnEvent(turn, T0, T0 + timedelta(hours=1))
        out.append(
            dataclasses.replace(
                state, quality_label=label, slope_direction=slope, last_confirmed_turn=event
            )
        )
    return tuple(out)


U, W, X = "USABLE", "WEAK", "UNAVAILABLE"


@pytest.mark.parametrize(
    ("labels", "slopes", "turns", "expected"),
    [
        ([U, W, W, W, W, W], ["RISING"] + ["FLAT"] * 5, None, SUPPORTS_LONG),
        ([U, U, W, W, W, W], ["RISING", "RISING"] + ["FLAT"] * 4, None, SUPPORTS_LONG),
        ([U, U, W, W, W, W], ["RISING", "FALLING"] + ["FLAT"] * 4, None, MIXED_OR_WEAK),
        ([W, W, U, U, U, U], ["RISING"] * 6, None, MIXED_OR_WEAK),  # no USABLE FAST
        (
            [U, X, U, W, W, W],
            ["RISING"] * 6,
            [None, None, "CONFIRMED_DOWN_TURN", None, None, None],
            MIXED_OR_WEAK,
        ),
        (
            [U, X, W, W, W, W],
            ["RISING"] * 6,
            [None, None, "CONFIRMED_DOWN_TURN", None, None, None],
            SUPPORTS_LONG,
        ),  # WEAK INTERMEDIATE ignored
        (
            [U, X, U, W, W, W],
            ["RISING"] * 6,
            [None, None, "CONFIRMED_UP_TURN", None, None, None],
            SUPPORTS_LONG,
        ),
        (
            [U, W, W, W, U, U],
            ["RISING", "FLAT", "FLAT", "FLAT", "FALLING", "FALLING"],
            None,
            SUPPORTS_LONG,
        ),  # SLOW never vetoes
        ([U, W, W, W, W, W], ["FALLING"] + ["FLAT"] * 5, None, SUPPORTS_SHORT),
        (
            [U, W, W, U, W, W],
            ["FALLING"] + ["FLAT"] * 5,
            [None, None, None, "CONFIRMED_UP_TURN", None, None],
            MIXED_OR_WEAK,
        ),
        ([U, W, W, W, W, W], ["FLAT"] * 6, None, MIXED_OR_WEAK),
    ],
)
def test_adr_0046_timing_qualifier(labels, slopes, turns, expected) -> None:
    assert timing_qualifier(scale_states(labels, slopes, turns)) == expected


def test_cycle_is_an_active_component_that_only_reports_the_qualifier() -> None:
    assert CYCLE_DECISION_ACTIVATION is True
    state = CycleEngine().snapshot("RUN-x", T0)
    assert state.decision_role is SignalRole.ACTIVE
    assert decision_timing_qualifier(state) == state.timing_qualifier == MIXED_OR_WEAK
    assert [s.group for s in SCALES] == [
        "FAST",
        "FAST",
        "INTERMEDIATE",
        "INTERMEDIATE",
        "SLOW",
        "SLOW",
    ]
    assert (
        decision_timing_qualifier(
            dataclasses.replace(state, decision_role=SignalRole.METHOD_NOT_READY)
        )
        == "CYCLE_METHOD_NOT_READY"
    )


def bar(
    tf: str, index: int, o, h, low, c, minutes: int, volume="10", complete=True, taker=None
) -> Bar:
    step = timedelta(minutes=minutes)
    opened = T0 + index * step
    return Bar(
        tf,
        opened,
        opened + step,
        opened + step,
        D(str(o)),
        D(str(h)),
        D(str(low)),
        D(str(c)),
        D(volume),
        minutes if complete else minutes - 1,
        minutes,
        "COMPLETE" if complete else "INCOMPLETE",
        None,
        None if taker is None else D(taker),
    )


def test_regime_boundaries_are_the_frozen_25_20_rule() -> None:
    assert regime(25.0, 30, 10) == TREND_BULL and regime(25.0, 10, 30) == TREND_BEAR
    assert regime(20.0, 30, 10) == RANGE and regime(24.9, 30, 10) == TRANSITION
    assert regime(30.0, 20, 20) == TRANSITION


def test_wilder_adx_matches_an_independent_textbook_computation() -> None:
    rows = [(100 + 2 * math.sin(i / 3) + 0.3 * i, 0.5 + 0.1 * (i % 3)) for i in range(60)]
    bars = [bar("4h", i, c, c + w, c - w - 0.2, c + 0.1, 240) for i, (c, w) in enumerate(rows)]
    adx = WilderAdx()
    readings = [adx.update(b) for b in bars]
    assert all(r.state == UNAVAILABLE for r in readings[:27]) and readings[27].state != UNAVAILABLE
    # textbook reference
    hi = [float(b.high) for b in bars]
    lo = [float(b.low) for b in bars]
    cl = [float(b.close) for b in bars]
    tr, pdm, mdm = [], [], []
    for i in range(1, 60):
        tr.append(max(hi[i] - lo[i], abs(hi[i] - cl[i - 1]), abs(lo[i] - cl[i - 1])))
        up, dn = hi[i] - hi[i - 1], lo[i - 1] - lo[i]
        pdm.append(up if up > dn and up > 0 else 0.0)
        mdm.append(dn if dn > up and dn > 0 else 0.0)
    s_tr, s_p, s_m = sum(tr[:14]), sum(pdm[:14]), sum(mdm[:14])
    dxs, adx_ref = [], None
    for i in range(13, 59):
        if i > 13:
            s_tr, s_p, s_m = (
                s_tr - s_tr / 14 + tr[i],
                s_p - s_p / 14 + pdm[i],
                s_m - s_m / 14 + mdm[i],
            )
        p, m = 100 * s_p / s_tr, 100 * s_m / s_tr
        dx = 100 * abs(p - m) / (p + m)
        if adx_ref is None:
            dxs.append(dx)
            if len(dxs) == 14:
                adx_ref = sum(dxs) / 14
        else:
            adx_ref = (adx_ref * 13 + dx) / 14
    assert readings[-1].value("adx") == pytest.approx(adx_ref, rel=1e-12)


def test_ema_structure_and_incomplete_bar_semantics() -> None:
    ema = Ema(3)
    assert [ema.update(x) for x in (1, 2, 3, 4)] == [None, None, 2.0, 3.0]
    structure = HourStructure()
    rising = [bar("1h", i, 100 + i, 101 + i, 99 + i, 100.5 + i, 60) for i in range(55)]
    readings = [structure.update(b) for b in rising]
    assert readings[48].state == UNAVAILABLE and readings[49].state == BULLISH
    incomplete = bar("1h", 55, 155, 156, 154, 155.5, 60, complete=False)
    assert structure.update(incomplete).state == UNAVAILABLE
    assert structure.update(bar("1h", 56, 156, 157, 155, 156.5, 60)).state == BULLISH
    gapped = structure.update(bar("1h", 60, 150, 151, 149, 150.5, 60))  # whole bars missing
    assert gapped.state == UNAVAILABLE and structure.ema20 is None  # reset, re-warm
    falling = HourStructure()
    states = [
        falling.update(bar("1h", i, 200 - i, 201 - i, 199 - i, 199.5 - i, 60)).state
        for i in range(55)
    ]
    assert states[-1] == BEARISH
    flat = HourStructure()
    assert [flat.update(bar("1h", i, 100, 101, 99, 100, 60)).state for i in range(51)][
        -1
    ] == NEUTRAL


def test_wilder_atr_and_readiness() -> None:
    atr = WilderAtr()
    readings = [atr.update(bar("15m", i, 100, 102, 99, 101, 15)) for i in range(16)]
    assert readings[12].state == UNAVAILABLE and readings[13].state == "READY"
    assert readings[13].value("atr") == pytest.approx(3.0)
    assert readings[13].available_at == T0 + 14 * timedelta(minutes=15)


def test_session_vwap_is_quote_over_base_and_fails_on_missing_minutes() -> None:
    vwap = SessionVwap()
    day = datetime(2001, 3, 5, tzinfo=UTC)
    for i in range(3):
        m = minute_bar(
            day + timedelta(minutes=i), D(100), D(101), D(99), D(100), D(2), D(200 + 2 * i), D(1)
        )
        vwap.on_minute_boundary(m.open_time, m)
    assert vwap.reading().value("vwap") == pytest.approx((200 + 202 + 204) / 6)
    vwap.on_minute_boundary(day + timedelta(minutes=3), None)
    assert vwap.reading().state == UNAVAILABLE
    next_day = day + timedelta(days=1)
    m = minute_bar(next_day, D(100), D(101), D(99), D(100), D(1), D(150), D(1))
    vwap.on_minute_boundary(next_day, m)
    assert vwap.reading().value("vwap") == 150  # new UTC session resets
    no_quote = SessionVwap()
    no_quote.on_minute_boundary(day, minute_bar(day, D(1), D(1), D(1), D(1), D(1)))
    assert no_quote.reading().state == UNAVAILABLE


def test_daily_boundaries_and_ema20_corroboration() -> None:
    daily = DailyContext()
    for i in range(24):
        daily.update(bar("1d", i, 100 + i, 102 + i, 99 + i, 101 + i, 1440))
    assert daily.direction.state == DAILY_BULL
    decision = T0 + timedelta(days=24, minutes=15)
    boundary = daily.boundary_for(decision)
    assert boundary.value("high") == 125 and boundary.value("low") == 122
    assert daily.boundary_for(decision + timedelta(days=1)).state == UNAVAILABLE  # stale
    falling = DailyContext()
    for i in range(24):
        falling.update(bar("1d", i, 200 - i, 202 - i, 199 - i, 199 - i, 1440))
    assert falling.direction.state == DAILY_BEAR
    flat = DailyContext()
    for i in range(24):
        flat.update(bar("1d", i, 100, 101, 99, 100, 1440))
    assert flat.direction.state == DAILY_NEUTRAL
    short = DailyContext()
    for i in range(22):
        short.update(bar("1d", i, 100 + i, 102 + i, 99 + i, 101 + i, 1440))
    assert short.direction.state == UNAVAILABLE  # EMA20 plus three earlier days needed
    daily.update(bar("1d", 24, 130, 131, 129, 130, 1440, complete=False))
    assert daily.boundary.state == UNAVAILABLE


def test_participation_rvol_excludes_trigger_and_needs_positive_imbalance() -> None:
    flow = Participation()
    for i in range(20):
        flow.update(bar("15m", i, 100, 101, 99, 100, 15, volume=str(10 + i), taker="5"))
    trigger = flow.update(bar("15m", 20, 100, 101, 99, 100, 15, volume="18", taker="12"))
    assert trigger.value("rvol") == pytest.approx(18 / 19.5)  # median of 10..29
    assert not flow.supports(1)  # RVOL < 1.20
    strong = flow.update(bar("15m", 21, 100, 101, 99, 100, 15, volume="40", taker="30"))
    assert strong.value("imbalance") == pytest.approx(0.5)
    assert flow.supports(1) and not flow.supports(-1)
    missing = flow.update(bar("15m", 22, 100, 101, 99, 100, 15, volume="60"))
    assert missing.state == UNAVAILABLE and not flow.supports(1) and not flow.supports(-1)
    fresh = Participation()
    for i in range(19):
        fresh.update(bar("15m", i, 100, 101, 99, 100, 15, taker="5"))
    fresh.update(bar("15m", 19, 100, 101, 99, 100, 15, complete=False, taker="5"))
    assert (
        fresh.update(bar("15m", 20, 100, 101, 99, 100, 15, volume="50", taker="40")).value("rvol")
        is None
    )
