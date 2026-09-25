"""System G1 Development V1: P1/P2 causal fixtures, conviction, configurations and conflicts."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from app.g1.bars import Bar
from app.g1.cycle import MIXED_OR_WEAK, SUPPORTS_LONG, SUPPORTS_SHORT
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
)
from app.g1.playbooks import (
    CONFIGS,
    CONFIGURATIONS,
    Configuration,
    DecisionContext,
    P1Machine,
    Setup,
    conviction,
    decide,
    directional_bias,
    p2_setups,
)
from app.g1.records import Conviction, Playbook, Side

T0 = datetime(2001, 3, 5, 12, tzinfo=UTC)
Q = timedelta(minutes=15)


def candle(index: int, o, h, low, c, complete: bool = True) -> Bar:
    opened = T0 + index * Q
    return Bar(
        "15m",
        opened,
        opened + Q,
        opened + Q,
        Decimal(str(o)),
        Decimal(str(h)),
        Decimal(str(low)),
        Decimal(str(c)),
        Decimal(10),
        15 if complete else 14,
        15,
        "COMPLETE" if complete else "INCOMPLETE",
    )


def ctx(index: int, bar: Bar | None, previous: Bar | None = None, **overrides) -> DecisionContext:
    base: dict[str, Any] = {
        "decision_time": T0 + (index + 1) * Q,
        "candle": bar,
        "previous": previous,
        "regime": TREND_BULL,
        "structure": BULLISH,
        "ema20_1h": 100.0,
        "atr": 2.0,
        "previous_day_high": 120.0,
        "previous_day_low": 80.0,
        "vwap": 100.0,
        "daily": DAILY_BULL,
        "participation_long": True,
        "participation_short": True,
        "cycle": SUPPORTS_LONG,
    }
    base.update(overrides)
    return DecisionContext(**base)


def run_p1(bars, **overrides):
    machine = P1Machine()
    out = []
    previous = None
    for index, bar in enumerate(bars):
        setups, events = machine.step(ctx(index, bar, previous, **overrides))
        out.append((setups, events))
        previous = bar
    return out


# ------------------------------------------------------------------ P1
def test_p1_bullish_pullback_arming_trigger_stop_and_2r_objective() -> None:
    bars = [
        candle(0, 103, 104, 102, 103),
        candle(1, 103, 103.5, 99.5, 100.5),  # touches EMA20 (low <= 100): armed
        candle(2, 100.5, 101.5, 99, 101),  # close > EMA20 but not > previous high 103.5
        candle(3, 101, 104.2, 100.8, 104),  # close > EMA20 and > previous high 101.5: trigger
    ]
    out = run_p1(bars)
    assert "P1_LONG_ARMED" in out[1][1] and out[1][0] == [] and out[2][0] == []
    [setup] = out[3][0]
    assert setup.playbook is Playbook.P1 and setup.side is Side.LONG
    assert setup.reference == 104
    assert setup.stop == pytest.approx(99 - 0.25 * 2.0)  # window low 99 minus 0.25 ATR
    assert setup.objective == pytest.approx(104 + 2 * (104 - 98.5))
    assert setup.reward_risk == 2.0 and setup.plan_valid


def test_p1_bearish_mirror() -> None:
    bars = [
        candle(0, 97, 98, 96, 97),
        candle(1, 97, 100.5, 96.5, 99.5),  # high >= EMA20: armed
        candle(2, 99.5, 100.2, 95.5, 95.8),  # close < EMA20 and < previous low 96.5
    ]
    out = run_p1(bars, regime=TREND_BEAR, structure=BEARISH, daily=DAILY_BEAR, cycle=SUPPORTS_SHORT)
    [setup] = out[2][0]
    assert setup.side is Side.SHORT
    assert setup.stop == pytest.approx(100.5 + 0.5)
    assert setup.objective == pytest.approx(95.8 - 2 * (101.0 - 95.8))


def test_p1_can_trigger_on_the_arming_candle() -> None:
    bars = [candle(0, 100.5, 100.6, 100.2, 100.4), candle(1, 100.4, 101, 99.8, 100.8)]
    out = run_p1(bars, ema20_1h=100.0)
    assert out[1][0] and "P1_LONG_ARMED" in out[1][1]


def test_p1_expires_after_four_candles_including_the_arming_candle() -> None:
    bars = [candle(0, 103, 104, 102, 103), candle(1, 103, 103, 99, 100)]
    bars += [candle(i, 100.5, 101, 100.2, 100.4) for i in range(2, 5)]  # armed window 1..4
    bars.append(candle(5, 100.5, 106, 100.4, 105))  # would trigger, but the window expired
    out = run_p1(bars)
    assert "P1_LONG_EXPIRED_FOUR_CANDLES" in out[5][1] and out[5][0] == []
    bars[4] = candle(4, 100.5, 106, 100.4, 105)  # same trigger on the 4th armed candle
    assert run_p1(bars[:5])[4][0]


def test_p1_invalidation_expires_the_setup() -> None:
    machine = P1Machine()
    b0, b1, b2 = (
        candle(0, 103, 104, 102, 103),
        candle(1, 103, 103, 99, 100),
        candle(2, 100, 106, 100, 105),
    )
    machine.step(ctx(0, b0))
    machine.step(ctx(1, b1, b0))
    setups, events = machine.step(ctx(2, b2, b1, structure=NEUTRAL))
    assert setups == [] and "P1_LONG_EXPIRED_CONTEXT_INVALID" in events


def test_p1_unavailable_inputs_never_trigger_and_atr_is_a_plan_veto() -> None:
    bars = [
        candle(0, 103, 104, 102, 103),
        candle(1, 103, 103.5, 99.5, 100.5),
        candle(2, 101, 104.2, 100.8, 104),
    ]
    assert all(not s for s, _ in run_p1(bars, ema20_1h=None))
    assert all(not s for s, _ in run_p1(bars, regime=UNAVAILABLE))
    bars_incomplete = bars[:2] + [candle(2, 101, 104.2, 100.8, 104, complete=False)]
    assert all(not s for s, _ in run_p1(bars_incomplete))
    [setup] = run_p1(bars, atr=None)[2][0]
    assert setup.plan_veto == "P1_ATR_UNAVAILABLE" and not setup.plan_valid


def test_p1_is_causal_no_future_candle_changes_past_outputs() -> None:
    bars = [
        candle(0, 103, 104, 102, 103),
        candle(1, 103, 103.5, 99.5, 100.5),
        candle(2, 101, 104.2, 100.8, 104),
    ]
    base = run_p1(bars)
    extended = run_p1([*bars, candle(3, 104, 110, 90, 95), candle(4, 95, 96, 80, 81)])
    assert extended[:3] == base


# ------------------------------------------------------------------ P2
def p2(bar: Bar, **overrides):
    return p2_setups(ctx(0, bar, **{"regime": RANGE, "structure": NEUTRAL, **overrides}))


def test_p2_long_failed_auction_reentry_vwap_objective() -> None:
    [setup], events = p2(candle(0, 81, 82, 79.4, 80.5), vwap=90.0)
    assert "P2_LONG_FAILED_AUCTION_REENTRY" in events
    assert setup.side is Side.LONG and setup.stop == pytest.approx(79.4 - 0.5)
    assert setup.objective == 90.0
    assert setup.reward_risk == pytest.approx((90 - 80.5) / (80.5 - 78.9)) and setup.plan_valid


def test_p2_short_mirror() -> None:
    [setup], _ = p2(candle(0, 119, 120.6, 118, 119.5), vwap=110.0)
    assert setup.side is Side.SHORT and setup.stop == pytest.approx(121.1)
    assert setup.reward_risk == pytest.approx((119.5 - 110) / (121.1 - 119.5))


def test_p2_insufficient_excursion_and_failed_reentry() -> None:
    assert p2(candle(0, 81, 82, 79.6, 80.5)) == ([], [])  # 79.6 > 80 - 0.5
    setups, events = p2(candle(0, 81, 82, 79, 79.9))  # close < previous-day low
    assert setups == [] and events == ["P2_LONG_EXCURSION_WITHOUT_REENTRY"]


def test_p2_reward_risk_objective_side_and_unavailable_inputs() -> None:
    [low_rr], _ = p2(candle(0, 81, 82, 79.4, 80.5), vwap=82.0)
    assert low_rr.plan_veto == "P2_REWARD_RISK_BELOW_1_50"
    [wrong_side], _ = p2(candle(0, 81, 82, 79.4, 80.5), vwap=80.0)
    assert wrong_side.plan_veto == "P2_OBJECTIVE_NOT_PROFITABLE_SIDE"
    [no_vwap], _ = p2(candle(0, 81, 82, 79.4, 80.5), vwap=None)
    assert no_vwap.plan_veto == "P2_VWAP_UNAVAILABLE"
    assert p2(candle(0, 81, 82, 79.4, 80.5), previous_day_low=None) == (
        [],
        ["P2_BOUNDARY_UNAVAILABLE"],
    )
    assert p2(candle(0, 81, 82, 79.4, 80.5), atr=None) == ([], ["P2_ATR_UNAVAILABLE"])
    assert p2(candle(0, 81, 82, 79.4, 80.5), regime=TRANSITION) == ([], [])
    assert p2(candle(0, 81, 82, 79.4, 80.5, complete=False)) == ([], [])


def test_p2_uses_only_the_trigger_candle() -> None:
    bar = candle(0, 81, 82, 79.4, 80.5)
    first = p2(bar, vwap=90.0)
    assert p2(bar, vwap=90.0, previous=candle(-1, 50, 200, 10, 60)) == first


# ------------------------------------------------------------------ conviction / configs / conflicts
def setup(playbook, side, rr=2.0, veto=None) -> Setup:
    return Setup(playbook, side, 100.0, 99.0, 102.0, rr, veto, ("X",))


def test_conviction_is_s_full_evidence_and_ignores_plan_vetoes() -> None:
    full = ctx(0, candle(0, 100, 101, 99, 100))
    assert conviction([], full) is Conviction.LOW
    assert (
        conviction([setup(Playbook.P1, Side.LONG)], dataclasses.replace(full, regime=UNAVAILABLE))
        is Conviction.LOW
    )
    assert conviction([setup(Playbook.P1, Side.LONG)], full) is Conviction.HIGH
    assert (
        conviction([setup(Playbook.P1, Side.LONG, veto="P1_ATR_UNAVAILABLE")], full)
        is Conviction.HIGH
    )
    assert (
        conviction([setup(Playbook.P1, Side.LONG)], dataclasses.replace(full, cycle=MIXED_OR_WEAK))
        is Conviction.MEDIUM
    )
    assert (
        conviction(
            [setup(Playbook.P1, Side.LONG)], dataclasses.replace(full, participation_long=False)
        )
        is Conviction.MEDIUM
    )
    assert (
        conviction([setup(Playbook.P1, Side.LONG)], dataclasses.replace(full, daily=DAILY_BEAR))
        is Conviction.MEDIUM
    )
    assert (
        conviction([setup(Playbook.P2, Side.LONG)], dataclasses.replace(full, daily=DAILY_BEAR))
        is Conviction.HIGH
    )
    both = [setup(Playbook.P1, Side.LONG), setup(Playbook.P2, Side.SHORT)]
    assert (
        conviction(both, dataclasses.replace(full, cycle=SUPPORTS_LONG)) is Conviction.HIGH
    )  # only one complete
    two_complete = [setup(Playbook.P1, Side.LONG), setup(Playbook.P2, Side.LONG)]
    assert conviction(two_complete, full) is Conviction.MEDIUM


def test_seven_configurations_remove_only_their_declared_component() -> None:
    assert CONFIGURATIONS == (
        "S0",
        "S_FULL",
        "S_MINUS_CYCLE",
        "S_MINUS_PARTICIPATION",
        "S_MINUS_DAILY_HTF",
        "S_P1_ONLY",
        "S_P2_ONLY",
    )
    full = dataclasses.asdict(CONFIGS["S_FULL"])
    expected = {
        "S0": {"participation": False, "cycle": False, "p1_daily_veto": False},
        "S_FULL": {},
        "S_MINUS_CYCLE": {"cycle": False},
        "S_MINUS_PARTICIPATION": {"participation": False},
        "S_MINUS_DAILY_HTF": {"p1_daily_veto": False},
        "S_P1_ONLY": {"p2_enabled": False},
        "S_P2_ONLY": {"p1_enabled": False},
    }
    for config_id, changes in expected.items():
        config = dataclasses.asdict(CONFIGS[config_id])
        diff = {
            k: v for k, v in config.items() if k not in ("config_id", "removed") and full[k] != v
        }
        assert diff == changes, config_id


@pytest.mark.parametrize(
    ("overrides", "allowed"),
    [
        (
            {},
            {
                "S0",
                "S_FULL",
                "S_MINUS_CYCLE",
                "S_MINUS_PARTICIPATION",
                "S_MINUS_DAILY_HTF",
                "S_P1_ONLY",
            },
        ),
        ({"cycle": MIXED_OR_WEAK}, {"S0", "S_MINUS_CYCLE"}),
        ({"participation_long": False}, {"S0", "S_MINUS_PARTICIPATION"}),
        ({"daily": DAILY_BEAR}, {"S0", "S_MINUS_DAILY_HTF"}),
        (
            {"daily": DAILY_NEUTRAL},
            {
                "S0",
                "S_FULL",
                "S_MINUS_CYCLE",
                "S_MINUS_PARTICIPATION",
                "S_MINUS_DAILY_HTF",
                "S_P1_ONLY",
            },
        ),
    ],
)
def test_configuration_filters_for_a_p1_long(overrides, allowed) -> None:
    c = dataclasses.replace(ctx(0, candle(0, 100, 101, 99, 100)), **overrides)
    chosen = {
        cid
        for cid in CONFIGURATIONS
        if decide([setup(Playbook.P1, Side.LONG)], c, CONFIGS[cid]).chosen
    }
    assert chosen == allowed


def test_cycle_alone_never_creates_a_setup_or_trade() -> None:
    c = ctx(0, candle(0, 100, 101, 99, 100), cycle=SUPPORTS_LONG)
    for config_id in CONFIGURATIONS:
        decision = decide([], c, CONFIGS[config_id])
        assert decision.chosen is None and "NO_BASE_TRIGGER" in decision.blockers
    assert conviction([], c) is Conviction.LOW


def test_conflict_same_direction_choice_and_p1_tie() -> None:
    c = ctx(0, candle(0, 100, 101, 99, 100), cycle=SUPPORTS_LONG, participation_short=True)
    s0 = CONFIGS["S0"]
    conflict = decide([setup(Playbook.P1, Side.LONG), setup(Playbook.P2, Side.SHORT)], c, s0)
    assert conflict.chosen is None and "PLAYBOOK_CONFLICT" in conflict.blockers
    larger = decide([setup(Playbook.P1, Side.LONG, 2.0), setup(Playbook.P2, Side.LONG, 2.5)], c, s0)
    assert larger.chosen is not None and larger.chosen.playbook is Playbook.P2
    tie = decide([setup(Playbook.P1, Side.LONG, 2.0), setup(Playbook.P2, Side.LONG, 2.0)], c, s0)
    assert tie.chosen is not None and tie.chosen.playbook is Playbook.P1
    vetoed = decide(
        [
            setup(Playbook.P1, Side.LONG),
            setup(Playbook.P2, Side.SHORT, 1.2, "P2_REWARD_RISK_BELOW_1_50"),
        ],
        c,
        s0,
    )
    assert (
        vetoed.chosen is not None and vetoed.chosen.side is Side.LONG
    )  # failed P2 plan never proposes
    only_p2 = decide([setup(Playbook.P1, Side.LONG)], c, CONFIGS["S_P2_ONLY"])
    assert only_p2.chosen is None


def test_directional_bias_cells() -> None:
    c = ctx(0, None)
    assert directional_bias(c) == "BULLISH"
    assert (
        directional_bias(dataclasses.replace(c, regime=TREND_BEAR, structure=BEARISH)) == "BEARISH"
    )
    assert directional_bias(dataclasses.replace(c, structure=BEARISH)) == "NEUTRAL"
    assert directional_bias(dataclasses.replace(c, regime=RANGE)) == "NEUTRAL"


def test_configuration_type_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        CONFIGS["S_FULL"].cycle = False  # type: ignore[misc]
    assert isinstance(CONFIGS["S0"], Configuration) and len(CONFIGS) == 7
