"""The registered synthetic System G1 fixture: a tiny deterministic 1m path and a scenario script.

Nothing here is market data. Timestamps sit in 2001 — before BTC existed — so a synthetic record
can never be mistaken for a BTC observation. Prices are a piecewise-linear path with a small
deterministic wiggle. The scenario script supplies fixture-controlled forecast/conviction/playbook
values that exercise the System G1 *contract* (no-trade, risk-blocked, LONG, SHORT, conflicting
playbooks, unavailable data); it is not a statistical model and not a P1/P2 construction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from .bars import Bar, minute_bar
from .canonical import digest
from .records import Bias, Conviction, Direction, Playbook, Side, StructuralMode

FIXTURE_ID = "G1-SYNTHETIC-VERTICAL-SLICE-FIXTURE-V1"
START = datetime(2001, 1, 30, tzinfo=UTC)
DAYS = 3
END = START + timedelta(days=DAYS)
CENT = Decimal("0.01")


def _at(day: int, hhmm: str) -> int:
    hours, minutes = (int(part) for part in hhmm.split(":"))
    return day * 1440 + hours * 60 + minutes


# (minute offset, anchor price). Designed so the fixture's plans reach objective, stop, expiry.
ANCHORS = (
    (_at(0, "00:00"), 30000.0),
    (_at(0, "06:00"), 30100.0),
    (_at(0, "08:30"), 30360.0),
    (_at(0, "12:00"), 30210.0),
    (_at(0, "14:00"), 29990.0),
    (_at(0, "16:00"), 30010.0),
    (_at(0, "17:30"), 30180.0),
    (_at(1, "00:00"), 30150.0),
    (_at(1, "02:00"), 30160.0),
    (_at(1, "03:00"), 29980.0),
    (_at(1, "04:00"), 30000.0),
    (_at(1, "05:00"), 30190.0),
    (_at(1, "06:00"), 30170.0),
    (_at(1, "07:00"), 29990.0),
    (_at(1, "12:00"), 30050.0),
    (_at(1, "18:00"), 30000.0),
    (_at(2, "00:00"), 30020.0),
    (_at(2, "04:00"), 30030.0),
    (_at(2, "08:00"), 30010.0),
    (_at(2, "16:00"), 29900.0),
    (_at(2, "20:00"), 29700.0),
    (_at(3, "00:00"), 29800.0),
)

# Missing 1m source events exercised by the fixture (data-quality handling).
MISSING_MINUTES = frozenset({_at(1, "10:07"), _at(1, "10:08"), _at(1, "10:09"), _at(2, "11:46")})

# Synthetic funding rates at settlement instants (per 8h), fixture-controlled.
FUNDING_RATES = {
    START + timedelta(minutes=offset): Decimal(rate)
    for offset, rate in (
        (_at(0, "08:00"), "0.0001"),
        (_at(0, "16:00"), "0.0001"),
        (_at(1, "00:00"), "-0.0002"),
        (_at(1, "08:00"), "0.0001"),
        (_at(1, "16:00"), "0.0001"),
        (_at(2, "00:00"), "0.0001"),
        (_at(2, "08:00"), "0.0003"),
        (_at(2, "16:00"), "0.0001"),
    )
}


def _price(offset: float) -> float:
    for (t0, p0), (t1, p1) in zip(ANCHORS, ANCHORS[1:], strict=False):
        if t0 <= offset <= t1:
            base = p0 + (p1 - p0) * (offset - t0) / (t1 - t0)
            break
    else:
        base = ANCHORS[-1][1]
    return base + 3.0 * math.sin(2 * math.pi * offset / 37.0)


def minute_path() -> tuple[Bar, ...]:
    bars = []
    for offset in range(DAYS * 1440):
        if offset in MISSING_MINUTES:
            continue
        open_ = Decimal(str(_price(offset))).quantize(CENT)
        close = Decimal(str(_price(offset + 1))).quantize(CENT)
        wick = Decimal(str(1.0 + (offset * 7919 % 13) / 10)).quantize(CENT)
        bars.append(
            minute_bar(
                START + timedelta(minutes=offset),
                open_,
                max(open_, close) + wick,
                min(open_, close) - wick,
                close,
                Decimal(10 + offset * 104729 % 17),
            )
        )
    return tuple(bars)


def dataset_hash(bars: tuple[Bar, ...]) -> str:
    return digest([(b.open_time, b.open, b.high, b.low, b.close, b.volume) for b in bars])


@dataclass(frozen=True)
class ScenarioStep:
    label: str
    bias: Bias
    mode: StructuralMode
    conviction: Conviction
    direction: Direction
    probability_up: float
    mean_return: float
    median_return: float
    lower_return: float
    upper_return: float
    prior_risk_scale: float
    proposals: tuple[tuple[Playbook, Side], ...] = ()
    stop_fraction: float = 0.004
    objective_fraction: float = 0.008
    supporting: tuple[str, ...] = ()
    opposing: tuple[str, ...] = ()


def _weak(index: int) -> ScenarioStep:
    """Background candles: weak, low/medium-conviction forecasts that never trade."""
    pattern = index % 6
    direction = (Direction.UP, Direction.NEUTRAL, Direction.DOWN)[pattern % 3]
    conviction = Conviction.MEDIUM if pattern in (3, 5) else Conviction.LOW
    sign = {Direction.UP: 1, Direction.DOWN: -1, Direction.NEUTRAL: 0}[direction]
    return ScenarioStep(
        "WEAK_PREDICTION_NO_TRADE",
        Bias.NEUTRAL if sign == 0 else (Bias.BULLISH if sign > 0 else Bias.BEARISH),
        StructuralMode.TRANSITION,
        conviction,
        direction,
        0.5 + 0.04 * sign,
        0.0004 * sign,
        0.0003 * sign,
        -0.006 + 0.0004 * sign,
        0.006 + 0.0004 * sign,
        0.004,
        supporting=("FIXTURE_WEAK_CONTEXT",),
        opposing=("FIXTURE_NO_COMPLETE_SETUP",),
    )


def _high(
    label: str,
    side: Side,
    proposals: tuple[tuple[Playbook, Side], ...],
    mode: StructuralMode,
    stop: float = 0.004,
    objective: float = 0.008,
) -> ScenarioStep:
    sign = side.sign
    return ScenarioStep(
        label,
        Bias.BULLISH if sign > 0 else Bias.BEARISH,
        mode,
        Conviction.HIGH,
        Direction.UP if sign > 0 else Direction.DOWN,
        0.5 + 0.12 * sign,
        0.003 * sign,
        0.0025 * sign,
        -0.004 + 0.003 * sign,
        0.004 + 0.003 * sign,
        0.004,
        proposals,
        stop,
        objective,
        supporting=("FIXTURE_COMPLETE_PATTERN",),
        opposing=(),
    )


P1_LONG = ((Playbook.P1, Side.LONG),)
P1_SHORT = ((Playbook.P1, Side.SHORT),)
P2_LONG = ((Playbook.P2, Side.LONG),)
P2_SHORT = ((Playbook.P2, Side.SHORT),)
TREND, RANGE = StructuralMode.TREND, StructuralMode.RANGE

EVENTS: dict[int, ScenarioStep] = {
    _at(0, "06:00"): _high("LONG_PLAN", Side.LONG, P1_LONG, TREND),
    _at(0, "06:30"): _high("HIGH_CONVICTION_RISK_BLOCKED_OCCUPIED", Side.SHORT, P2_SHORT, RANGE),
    _at(0, "12:00"): _high("SHORT_PLAN", Side.SHORT, P2_SHORT, RANGE, 0.004, 0.006),
    _at(0, "14:30"): _high("CONFLICTING_PLAYBOOKS_NO_TRADE", Side.LONG, P1_LONG + P2_SHORT, TREND),
    _at(0, "16:00"): _high("SHORT_PLAN_STOPPED", Side.SHORT, P1_SHORT, TREND, 0.003, 0.008),
    _at(1, "02:00"): _high("LONG_PLAN_STOPPED", Side.LONG, P2_LONG, RANGE, 0.003, 0.008),
    _at(1, "04:00"): _high("SHORT_PLAN_STOPPED", Side.SHORT, P2_SHORT, RANGE, 0.003, 0.008),
    _at(1, "06:00"): _high("LONG_PLAN_STOPPED", Side.LONG, P1_LONG, TREND, 0.003, 0.008),
    _at(1, "08:00"): _high("HIGH_CONVICTION_RISK_BLOCKED_DAILY_STOP", Side.LONG, P1_LONG, TREND),
    _at(1, "10:15"): _high("DATA_UNAVAILABLE_NO_TRADE", Side.LONG, P1_LONG, TREND),
    _at(2, "04:00"): _high("LONG_PLAN_MAX_HOLD_EXPIRY", Side.LONG, P2_LONG, RANGE, 0.02, 0.02),
    _at(2, "11:45"): _high("ENTRY_REJECTED_MISSING_MINUTE", Side.SHORT, P1_SHORT, TREND),
    _at(2, "15:00"): _high("SHORT_PLAN_FUNDING_CREDIT", Side.SHORT, P1_SHORT, TREND, 0.004, 0.009),
}


def scenario_step(decision_time: datetime) -> ScenarioStep:
    offset = int((decision_time - START).total_seconds() // 60)
    return EVENTS.get(offset) or _weak(offset // 15)


def scenario_digest() -> str:
    return digest(sorted((offset, step) for offset, step in EVENTS.items()))
