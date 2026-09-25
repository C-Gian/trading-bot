"""Frozen System G1 Development V1 playbooks, conviction, configurations and conflict rules.

Implements protocol sections 7-10 and 12 exactly:

- P1 `SYSTEM-G1-P1-DIRECTIONAL-CONTINUATION` — one causal state machine per direction;
- P2 `SYSTEM-G1-P2-FAILED-AUCTION-REENTRY` — one completed-15m excursion/re-entry detector;
- conviction under S-full evidence (LOW / MEDIUM / HIGH), independent of the configuration;
- the seven frozen configurations, differing only in their declared component/playbook;
- conflict resolution: opposite proposals -> NO_TRADE / PLAYBOOK_CONFLICT; same direction ->
  larger planned reward/risk; exact tie -> P1.

Order of evaluation for a configuration (implementation of "vetoes after setup recognition"):

1. base recognition (P1 trigger, P2 excursion + re-entry) — configuration-independent;
2. the configuration's required corroborations (daily for P1, participation, cycle);
3. playbook plan validity (ATR/VWAP availability, P2 objective side and >= 1.50R) — a failed plan is
   a recognized base trigger that does not become a proposal;
4. conflict / same-direction choice among proposals;
5. risk / occupancy vetoes (applied by the engine's ledger).

Cycle support only satisfies a playbook's cycle-corroboration role: without a base trigger no
proposal can exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .bars import Bar
from .cycle import SUPPORTS_LONG, SUPPORTS_SHORT
from .indicators import (
    BEARISH,
    BULLISH,
    DAILY_BEAR,
    DAILY_BULL,
    RANGE,
    TREND_BEAR,
    TREND_BULL,
    UNAVAILABLE,
)
from .records import Conviction, Playbook, Side

P1_ARMING_CANDLES = 4
P1_OBJECTIVE_R = 2.0
STOP_ATR_BUFFER = 0.25
P2_EXCURSION_ATR = 0.25
P2_MIN_REWARD_RISK = 1.50
PLAYBOOK_VERSION = "SYSTEM-G1-DEVELOPMENT-V1"
CONFIGURATIONS = (
    "S0",
    "S_FULL",
    "S_MINUS_CYCLE",
    "S_MINUS_PARTICIPATION",
    "S_MINUS_DAILY_HTF",
    "S_P1_ONLY",
    "S_P2_ONLY",
)


@dataclass(frozen=True)
class Configuration:
    config_id: str
    p1_enabled: bool = True
    p2_enabled: bool = True
    participation: bool = True
    cycle: bool = True
    p1_daily_veto: bool = True
    removed: str = "NONE"


CONFIGS: dict[str, Configuration] = {
    "S0": Configuration(
        "S0",
        participation=False,
        cycle=False,
        p1_daily_veto=False,
        removed="PARTICIPATION+CYCLE+P1_DAILY_VETO",
    ),
    "S_FULL": Configuration("S_FULL"),
    "S_MINUS_CYCLE": Configuration("S_MINUS_CYCLE", cycle=False, removed="CYCLE"),
    "S_MINUS_PARTICIPATION": Configuration(
        "S_MINUS_PARTICIPATION", participation=False, removed="PARTICIPATION"
    ),
    "S_MINUS_DAILY_HTF": Configuration(
        "S_MINUS_DAILY_HTF", p1_daily_veto=False, removed="P1_DAILY_VETO"
    ),
    "S_P1_ONLY": Configuration("S_P1_ONLY", p2_enabled=False, removed="PLAYBOOK_P2"),
    "S_P2_ONLY": Configuration("S_P2_ONLY", p1_enabled=False, removed="PLAYBOOK_P1"),
}
assert tuple(CONFIGS) == CONFIGURATIONS


@dataclass(frozen=True)
class DecisionContext:
    """Everything the playbooks may read at one completed 15m decision candle."""

    decision_time: datetime
    candle: Bar | None
    previous: Bar | None
    regime: str
    structure: str
    ema20_1h: float | None
    atr: float | None
    previous_day_high: float | None
    previous_day_low: float | None
    vwap: float | None
    daily: str
    participation_long: bool
    participation_short: bool
    cycle: str

    @property
    def market_state_available(self) -> bool:
        return (
            self.candle is not None
            and self.candle.complete
            and self.regime != UNAVAILABLE
            and self.structure != UNAVAILABLE
        )

    def participation(self, side: Side) -> bool:
        return self.participation_long if side is Side.LONG else self.participation_short

    def cycle_supports(self, side: Side) -> bool:
        return self.cycle == (SUPPORTS_LONG if side is Side.LONG else SUPPORTS_SHORT)

    def daily_not_opposing(self, side: Side) -> bool:
        """P1 HTF rule: daily supports or is neutral; UNAVAILABLE cannot be verified (fails)."""
        if self.daily == UNAVAILABLE:
            return False
        return self.daily != (DAILY_BEAR if side is Side.LONG else DAILY_BULL)


@dataclass(frozen=True)
class Setup:
    """One recognized base trigger and its plan (plan fields None under a data veto)."""

    playbook: Playbook
    side: Side
    reference: float
    stop: float | None
    objective: float | None
    reward_risk: float | None
    plan_veto: str | None
    reasons: tuple[str, ...]

    @property
    def plan_valid(self) -> bool:
        return self.plan_veto is None


@dataclass
class _Armed:
    count: int
    lows: list[float] = field(default_factory=list)
    highs: list[float] = field(default_factory=list)


class P1Machine:
    """P1 directional continuation after pullback — one arming state per direction."""

    def __init__(self) -> None:
        self.armed: dict[Side, _Armed | None] = {Side.LONG: None, Side.SHORT: None}

    @staticmethod
    def context_valid(ctx: DecisionContext, side: Side) -> bool:
        if ctx.candle is None or not ctx.candle.complete or ctx.ema20_1h is None:
            return False
        if side is Side.LONG:
            return ctx.regime == TREND_BULL and ctx.structure == BULLISH
        return ctx.regime == TREND_BEAR and ctx.structure == BEARISH

    def step(self, ctx: DecisionContext) -> tuple[list[Setup], list[str]]:
        setups: list[Setup] = []
        events: list[str] = []
        for side in (Side.LONG, Side.SHORT):
            tag = f"P1_{side.value}"
            valid = self.context_valid(ctx, side)
            armed = self.armed[side]
            if armed is not None and not valid:
                self.armed[side], armed = None, None
                events.append(f"{tag}_EXPIRED_CONTEXT_INVALID")
            if armed is not None and armed.count >= P1_ARMING_CANDLES:
                self.armed[side], armed = None, None
                events.append(f"{tag}_EXPIRED_FOUR_CANDLES")
            if not valid:
                continue
            candle, ema = ctx.candle, ctx.ema20_1h
            assert candle is not None and ema is not None
            low, high, close = float(candle.low), float(candle.high), float(candle.close)
            touched = low <= ema if side is Side.LONG else high >= ema
            if armed is None and touched:
                armed = _Armed(0)
                self.armed[side] = armed
                events.append(f"{tag}_ARMED")
            if armed is None:
                continue
            armed.count += 1
            armed.lows.append(low)
            armed.highs.append(high)
            previous = ctx.previous
            if previous is None or not previous.complete:
                continue
            if side is Side.LONG:
                triggered = close > ema and close > float(previous.high)
            else:
                triggered = close < ema and close < float(previous.low)
            if not triggered:
                continue
            self.armed[side] = None
            events.append(f"{tag}_TRIGGERED")
            setups.append(self._plan(ctx, side, armed, close))
        return setups, events

    @staticmethod
    def _plan(ctx: DecisionContext, side: Side, armed: _Armed, reference: float) -> Setup:
        reasons = ("P1_TREND_CONTEXT", "P1_EMA20_PULLBACK", "P1_RECLAIM_TRIGGER")
        if ctx.atr is None:
            return Setup(
                Playbook.P1, side, reference, None, None, None, "P1_ATR_UNAVAILABLE", reasons
            )
        if side is Side.LONG:
            stop = min(armed.lows) - STOP_ATR_BUFFER * ctx.atr
        else:
            stop = max(armed.highs) + STOP_ATR_BUFFER * ctx.atr
        risk = side.sign * (reference - stop)
        objective = reference + side.sign * P1_OBJECTIVE_R * risk
        return Setup(Playbook.P1, side, reference, stop, objective, P1_OBJECTIVE_R, None, reasons)


def p2_setups(ctx: DecisionContext) -> tuple[list[Setup], list[str]]:
    """P2 failed-auction re-entry on the completed 15m trigger candle."""
    events: list[str] = []
    candle = ctx.candle
    if ctx.regime != RANGE or candle is None or not candle.complete:
        return [], events
    if ctx.previous_day_high is None or ctx.previous_day_low is None:
        events.append("P2_BOUNDARY_UNAVAILABLE")
        return [], events
    if ctx.atr is None:
        events.append("P2_ATR_UNAVAILABLE")
        return [], events
    low, high, close = float(candle.low), float(candle.high), float(candle.close)
    buffer = P2_EXCURSION_ATR * ctx.atr
    setups = []
    for side in (Side.LONG, Side.SHORT):
        if side is Side.LONG:
            excursion = low <= ctx.previous_day_low - buffer
            reentry = close >= ctx.previous_day_low
            stop = low - STOP_ATR_BUFFER * ctx.atr
        else:
            excursion = high >= ctx.previous_day_high + buffer
            reentry = close <= ctx.previous_day_high
            stop = high + STOP_ATR_BUFFER * ctx.atr
        tag = f"P2_{side.value}"
        if not excursion:
            continue
        if not reentry:
            events.append(f"{tag}_EXCURSION_WITHOUT_REENTRY")
            continue
        events.append(f"{tag}_FAILED_AUCTION_REENTRY")
        reasons = ("P2_RANGE_REGIME", "P2_PREVIOUS_DAY_BOUNDARY", "P2_EXCURSION_REENTRY")
        if ctx.vwap is None:
            setups.append(
                Setup(Playbook.P2, side, close, stop, None, None, "P2_VWAP_UNAVAILABLE", reasons)
            )
            continue
        reward = side.sign * (ctx.vwap - close)
        risk = side.sign * (close - stop)
        if reward <= 0:
            setups.append(
                Setup(
                    Playbook.P2,
                    side,
                    close,
                    stop,
                    ctx.vwap,
                    None,
                    "P2_OBJECTIVE_NOT_PROFITABLE_SIDE",
                    reasons,
                )
            )
            continue
        ratio = reward / risk
        veto = None if ratio >= P2_MIN_REWARD_RISK else "P2_REWARD_RISK_BELOW_1_50"
        setups.append(Setup(Playbook.P2, side, close, stop, ctx.vwap, ratio, veto, reasons))
    return setups, events


def corroborated(setup: Setup, ctx: DecisionContext, config: Configuration) -> list[str]:
    """Missing corroborations of `setup` under `config` (empty list = satisfied)."""
    missing = []
    if (
        setup.playbook is Playbook.P1
        and config.p1_daily_veto
        and not ctx.daily_not_opposing(setup.side)
    ):
        missing.append("P1_DAILY_OPPOSES_OR_UNAVAILABLE")
    if config.participation and not ctx.participation(setup.side):
        missing.append("PARTICIPATION_NOT_SUPPORTING")
    if config.cycle and not ctx.cycle_supports(setup.side):
        missing.append("CYCLE_NOT_SUPPORTING")
    return missing


def conviction(setups: list[Setup], ctx: DecisionContext) -> Conviction:
    """S-full evidence conviction; plan/risk/data vetoes never lower it."""
    if not ctx.market_state_available or not setups:
        return Conviction.LOW
    full = CONFIGS["S_FULL"]
    complete = {(s.playbook, s.side) for s in setups if not corroborated(s, ctx, full)}
    return Conviction.HIGH if len(complete) == 1 else Conviction.MEDIUM


@dataclass(frozen=True)
class ConfigDecision:
    config_id: str
    chosen: Setup | None
    blockers: tuple[str, ...]


def decide(setups: list[Setup], ctx: DecisionContext, config: Configuration) -> ConfigDecision:
    """Configuration filter, plan validity and conflict resolution (before risk/occupancy)."""
    blockers: list[str] = []
    if not ctx.market_state_available:
        blockers.append("MARKET_STATE_UNAVAILABLE")
    enabled = [
        s
        for s in setups
        if (s.playbook is Playbook.P1 and config.p1_enabled)
        or (s.playbook is Playbook.P2 and config.p2_enabled)
    ]
    if not enabled:
        blockers.append("NO_BASE_TRIGGER")
        return ConfigDecision(config.config_id, None, tuple(blockers))
    proposals = []
    for setup in enabled:
        missing = corroborated(setup, ctx, config)
        if missing:
            blockers.extend(f"{setup.playbook.name}_{setup.side.value}_{m}" for m in missing)
        elif not setup.plan_valid:
            blockers.append(str(setup.plan_veto))
        else:
            proposals.append(setup)
    if not proposals:
        return ConfigDecision(config.config_id, None, tuple(blockers))
    if len({p.side for p in proposals}) > 1:
        return ConfigDecision(config.config_id, None, (*blockers, "PLAYBOOK_CONFLICT"))
    # Same direction: larger planned reward/risk; exact tie -> P1 (frozen precedence).
    chosen = max(
        proposals,
        key=lambda p: (p.reward_risk or 0.0, 1 if p.playbook is Playbook.P1 else 0),
    )
    return ConfigDecision(config.config_id, chosen, ())


def directional_bias(ctx: DecisionContext) -> str:
    """Forecaster cell bias: BULLISH iff 4h TREND_BULL and 1h BULLISH; BEARISH symmetric."""
    if ctx.regime == TREND_BULL and ctx.structure == BULLISH:
        return "BULLISH"
    if ctx.regime == TREND_BEAR and ctx.structure == BEARISH:
        return "BEARISH"
    return "NEUTRAL"
