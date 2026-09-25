"""SYSTEM-G1-CYCLE-METHOD-V1: causal multi-scale Autocorrelation Periodogram cycle state.

Implementation of the frozen method family (research/protocols/SYSTEM-G1-CYCLE-METHOD-V1.md),
following Ehlers' Autocorrelation Periodogram (Cycle Analytics for Traders, 2013; TASC Sept. 2016
Traders' Tips companions):

1. two-pole causal high-pass with cutoff `period2` (the search upper bound);
2. SuperSmoother low-pass with cutoff `period1` (the search lower bound);
3. Pearson autocorrelation over the past `AVERAGING_LENGTH = 3` filtered values, lags 0..period2;
4. DFT-style cosine/sine projection of lags `AVERAGING_LENGTH..period2` for each integer period
   `period1..period2`;
5. recursive smoothing `R = 0.2 * SqSum**2 + 0.8 * R_prev`;
6. normalization by the current maximum of `R` across the band;
7. dominant period = centre of gravity over periods with normalized power `>= 0.5`.

Everything is strictly recursive over completed past bars; no centred, forward/backward or
full-series operation exists here. The same class runs in live-style and replay adapters.

Quality labels (frozen by ADR-0045 / SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1, not chosen here):

- UNAVAILABLE: warm-up incomplete, active gap re-warm, no dominant period or no causal projection;
- USABLE: otherwise available and `explained_fraction >= 0.90` on the current completed input bar
  and on each of the two immediately preceding completed input bars, with no gap/reset inside that
  three-bar window (the persistence history is cleared on every reset);
- WEAK: available but not USABLE.

No other metric participates.

Activation (ADR-0046): the family is an ACTIVE timing/corroboration component. The only value the
decision path reads is the timing qualifier:

- `CYCLE_SUPPORTS_LONG` iff at least one FAST (45m, 3h) scale is USABLE, every USABLE FAST scale is
  RISING, and no USABLE INTERMEDIATE (1d, 4d) scale has most recent confirmed turn
  `CONFIRMED_DOWN_TURN`;
- `CYCLE_SUPPORTS_SHORT` symmetrically;
- otherwise `CYCLE_MIXED_OR_WEAK`.

SLOW (1w, 4w) disagreement is recorded, never a veto. The qualifier can only satisfy a playbook's
predeclared cycle-corroboration role; it cannot create a setup or a trade by itself.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta

from .bars import FIXED_MINUTES, Bar
from .canonical import content_id, digest
from .records import CycleScaleState, CycleState, SignalRole, TurnEvent

METHOD_VERSION = "SYSTEM-G1-CYCLE-METHOD-V1-ACP-IMPL-2-QUALITY-GATE-V1"
AVERAGING_LENGTH = 3
SMOOTHING = 0.2
POWER_FLOOR = 0.5
CYCLE_DECISION_ACTIVATION = True  # ADR-0046
METHOD_STATUS = "ACTIVE_COMPONENT_ADR_0046"
QUALITY_RULE_ID = "SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1:EXPLAINED_FRACTION_GE_0.90_FOR_3_BARS"
USABLE_EXPLAINED_FRACTION = 0.90  # frozen (ADR-0045); never tuned
USABLE_PERSISTENCE_BARS = 3  # current bar + two immediately preceding bars (ADR-0045)
UNAVAILABLE, WEAK, USABLE = "UNAVAILABLE", "WEAK", "USABLE"
NOT_READY_QUALIFIER = "CYCLE_METHOD_NOT_READY"
SUPPORTS_LONG = "CYCLE_SUPPORTS_LONG"
SUPPORTS_SHORT = "CYCLE_SUPPORTS_SHORT"
MIXED_OR_WEAK = "CYCLE_MIXED_OR_WEAK"


@dataclass(frozen=True)
class Scale:
    nominal: str
    resolution: str
    nominal_samples: int
    period1: int
    period2: int
    group: str

    @property
    def warmup_bars(self) -> int:
        return max(4 * self.period2, 128)

    @property
    def bar_minutes(self) -> int:
        return FIXED_MINUTES[self.resolution]


# Frozen by the cycle method contract: six nominal scales, input resolutions and ACP ranges.
SCALES = (
    Scale("45m", "3m", 15, 10, 22, "FAST"),
    Scale("3h", "15m", 12, 10, 18, "FAST"),
    Scale("1d", "1h", 24, 16, 36, "INTERMEDIATE"),
    Scale("4d", "4h", 24, 16, 36, "INTERMEDIATE"),
    Scale("1w", "4h", 42, 28, 48, "SLOW"),
    Scale("4w", "1d", 28, 19, 42, "SLOW"),
)


def highpass_coefficients(period2: int) -> tuple[float, float, float]:
    angle = 0.707 * 2 * math.pi / period2
    alpha = (math.cos(angle) + math.sin(angle) - 1) / math.cos(angle)
    return (1 - alpha / 2) ** 2, 2 * (1 - alpha), (1 - alpha) ** 2


def supersmoother_coefficients(period1: int) -> tuple[float, float, float]:
    a1 = math.exp(-1.414 * math.pi / period1)
    b1 = 2 * a1 * math.cos(1.414 * math.pi / period1)
    c2, c3 = b1, -a1 * a1
    return 1 - c2 - c3, c2, c3


@dataclass(frozen=True)
class AcpOutput:
    filtered: float
    dominant_period: float | None
    power: tuple[float, ...]


class AutocorrelationPeriodogram:
    """Streaming ACP for one scale. `update(value)` consumes one completed input bar."""

    def __init__(self, period1: int, period2: int) -> None:
        self.period1, self.period2 = period1, period2
        self.hp_a, self.hp_b, self.hp_c = highpass_coefficients(period2)
        self.ss_c1, self.ss_c2, self.ss_c3 = supersmoother_coefficients(period1)
        self.closes: deque[float] = deque(maxlen=3)
        self.hp: deque[float] = deque([0.0, 0.0], maxlen=2)  # hp[-1] is the latest
        self.filt: deque[float] = deque(maxlen=period2 + AVERAGING_LENGTH + 1)
        self.r = [0.0] * (period2 + 1)
        periods = range(period1, period2 + 1)
        lags = range(AVERAGING_LENGTH, period2 + 1)
        self._cos = {p: [math.cos(2 * math.pi * n / p) for n in lags] for p in periods}
        self._sin = {p: [math.sin(2 * math.pi * n / p) for n in lags] for p in periods}

    def update(self, value: float) -> AcpOutput:
        self.closes.append(value)
        if len(self.closes) == 3:
            c0, c1, c2 = self.closes[2], self.closes[1], self.closes[0]
            hp = self.hp_a * (c0 - 2 * c1 + c2) + self.hp_b * self.hp[1] - self.hp_c * self.hp[0]
        else:
            hp = 0.0
        previous_hp = self.hp[1]
        self.hp.append(hp)
        f1 = self.filt[-1] if len(self.filt) >= 1 else 0.0
        f2 = self.filt[-2] if len(self.filt) >= 2 else 0.0
        filtered = self.ss_c1 * (hp + previous_hp) / 2 + self.ss_c2 * f1 + self.ss_c3 * f2
        self.filt.append(filtered)
        if len(self.filt) < self.period2 + AVERAGING_LENGTH:
            return AcpOutput(filtered, None, ())
        # filt_back[k] is the value k bars ago (k=0 current), exactly Ehlers' Filt[k].
        back = list(reversed(self.filt))
        corr = [0.0] * (self.period2 + 1)
        m = AVERAGING_LENGTH
        for lag in range(self.period2 + 1):
            sx = sy = sxx = syy = sxy = 0.0
            for count in range(m):
                x, y = back[count], back[lag + count]
                sx += x
                sy += y
                sxx += x * x
                syy += y * y
                sxy += x * y
            denominator = (m * sxx - sx * sx) * (m * syy - sy * sy)
            if denominator > 0:
                corr[lag] = (m * sxy - sx * sy) / math.sqrt(denominator)
        for period in range(self.period1, self.period2 + 1):
            cosine = sum(
                c * k for c, k in zip(corr[AVERAGING_LENGTH:], self._cos[period], strict=True)
            )
            sine = sum(
                c * k for c, k in zip(corr[AVERAGING_LENGTH:], self._sin[period], strict=True)
            )
            sq_sum = cosine * cosine + sine * sine
            self.r[period] = SMOOTHING * sq_sum * sq_sum + (1 - SMOOTHING) * self.r[period]
        band = self.r[self.period1 : self.period2 + 1]
        max_power = max(band)
        if max_power <= 0:
            return AcpOutput(filtered, None, tuple(0.0 for _ in band))
        power = tuple(r / max_power for r in band)
        spx = sp = 0.0
        for offset, pwr in enumerate(power):
            if pwr >= POWER_FLOOR:
                spx += (self.period1 + offset) * pwr
                sp += pwr
        return AcpOutput(filtered, spx / sp if sp else None, power)

    def trailing_filtered(self, length: int) -> list[float]:
        """The last `length` filtered values, most recent first."""
        return list(reversed(self.filt))[:length]


def project(trailing: list[float], period: float) -> tuple[float, float, float] | None:
    """Causal trailing projection at the dominant period.

    Returns (coordinate, phase_estimate_degrees, explained_fraction) or None when numerically
    unstable. `trailing[0]` is the current value. With x[t-k] ~ A cos(theta_t - w k), the sums
    re = sum x cos(w k), im = sum x sin(w k) give theta_t = atan2(im, re); the coordinate is
    cos(theta_t) in [-1, 1] (+1 = projected cycle peak).
    """
    length = round(period)
    if length < 2 or len(trailing) < length:
        return None
    window = trailing[:length]
    omega = 2 * math.pi / length
    re = sum(x * math.cos(omega * k) for k, x in enumerate(window))
    im = sum(x * math.sin(omega * k) for k, x in enumerate(window))
    energy = sum(x * x for x in window)
    if energy <= 1e-24 or re * re + im * im <= 1e-24:
        return None
    theta = math.atan2(im, re)
    explained = min(1.0, (2.0 / length) * (re * re + im * im) / energy)
    return math.cos(theta), math.degrees(theta) % 360.0, explained


def _sign(value: float | None) -> int:
    if value is None or abs(value) <= 1e-12:
        return 0
    return 1 if value > 0 else -1


class ScaleTracker:
    """One frozen scale: ACP, projection, slope, causal turn confirmation and gap/re-warm state."""

    def __init__(self, scale: Scale) -> None:
        self.scale = scale
        self._reset()
        self.gap_state = "NO_GAP"
        self.market_time: datetime | None = None
        self.available_at: datetime | None = None

    def _reset(self) -> None:
        self.acp = AutocorrelationPeriodogram(self.scale.period1, self.scale.period2)
        self.bars_seen = 0
        self.dominant: float | None = None
        self.power: tuple[float, ...] = ()
        self.coordinate: float | None = None
        self.phase: float | None = None
        self.explained: float | None = None
        self.previous_dominant: float | None = None
        self.slope: float | None = None
        self.slope_history: deque[tuple[int, datetime, datetime]] = deque(maxlen=3)
        self.pending_turn: tuple[str, datetime] | None = None
        self.last_turn: TurnEvent | None = None
        self.last_open: datetime | None = None
        # explained_fraction of the most recent completed input bars since the last reset.
        self.explained_history: deque[float | None] = deque(maxlen=USABLE_PERSISTENCE_BARS)

    @property
    def ready(self) -> bool:
        return self.bars_seen >= self.scale.warmup_bars

    def update(
        self, open_time: datetime, close_time: datetime, value: float, complete: bool
    ) -> None:
        step = timedelta(minutes=self.scale.bar_minutes)
        if not complete or (self.last_open is not None and open_time != self.last_open + step):
            # A gap or incomplete input bar invalidates the recursive state: re-warm from zero.
            self._reset()
            self.gap_state = "REWARMING_AFTER_GAP"
            if not complete:
                self.market_time, self.available_at = open_time, close_time
                return
        self.last_open = open_time
        self.market_time, self.available_at = open_time, close_time
        self.bars_seen += 1
        output = self.acp.update(value)
        self.previous_dominant = self.dominant
        self.dominant, self.power = output.dominant_period, output.power
        previous = self.coordinate
        projected = (
            project(self.acp.trailing_filtered(self.scale.period2), self.dominant)
            if self.dominant is not None
            else None
        )
        if projected is None:
            self.coordinate = self.phase = self.explained = None
            self.slope = None
        else:
            self.coordinate, self.phase, self.explained = projected
            self.slope = None if previous is None else self.coordinate - previous
        self.explained_history.append(self.explained)
        self._track_turn(open_time, close_time)
        if self.ready and self.gap_state == "REWARMING_AFTER_GAP":
            self.gap_state = "NO_GAP"

    def _track_turn(self, open_time: datetime, close_time: datetime) -> None:
        sign = _sign(self.slope)
        history = self.slope_history
        if self.pending_turn is not None:
            kind, estimated = self.pending_turn
            expected = 1 if kind == "CONFIRMED_UP_TURN" else -1
            if sign == expected:
                self.last_turn = TurnEvent(kind, estimated, close_time)
            self.pending_turn = None
        if history and sign != 0 and history[-1][0] != 0 and sign != history[-1][0]:
            kind = "CONFIRMED_UP_TURN" if sign > 0 else "CONFIRMED_DOWN_TURN"
            # The extremum is estimated at the previous bar; it is recorded only once a
            # subsequent completed bar does not reverse the new slope sign.
            self.pending_turn = (kind, history[-1][2])
        history.append((sign, open_time, close_time))

    def quality_label(self) -> str:
        """The frozen three-way label; only `explained_fraction` persistence participates."""
        if (
            not self.ready
            or self.gap_state == "REWARMING_AFTER_GAP"
            or self.dominant is None
            or self.coordinate is None
            or self.explained is None
        ):
            return UNAVAILABLE
        history = self.explained_history
        if len(history) == USABLE_PERSISTENCE_BARS and all(
            value is not None and value >= USABLE_EXPLAINED_FRACTION for value in history
        ):
            return USABLE
        return WEAK

    def quality_metrics(self) -> tuple[tuple[str, float | str | None], ...]:
        if not self.power:
            return (
                ("explained_fraction", None),
                ("mean_normalized_power", None),
                ("peak_band_fraction", None),
                ("period_change", None),
            )
        mean_power = sum(self.power) / len(self.power)
        peak_fraction = sum(p >= POWER_FLOOR for p in self.power) / len(self.power)
        change = (
            None
            if self.dominant is None or self.previous_dominant is None
            else abs(self.dominant - self.previous_dominant)
        )
        return (
            ("explained_fraction", self.explained),
            ("mean_normalized_power", mean_power),
            ("peak_band_fraction", peak_fraction),
            ("period_change", change),
        )

    def state(self) -> CycleScaleState:
        scale = self.scale
        ready = self.ready
        slope = _sign(self.slope)
        dominant = self.dominant if ready else None
        return CycleScaleState(
            scale.nominal,
            scale.resolution,
            scale.period1,
            scale.period2,
            self.bars_seen,
            scale.warmup_bars,
            ready,
            self.gap_state,
            dominant,
            None if dominant is None else dominant * scale.bar_minutes,
            digest([round(p, 9) for p in self.power])[:16] if ready and self.power else None,
            self.quality_metrics() if ready else (),
            self.quality_label(),
            self.coordinate if ready else None,
            self.phase if ready else None,
            ("RISING" if slope > 0 else "FALLING" if slope < 0 else "FLAT")
            if ready
            else "UNAVAILABLE",
            self.last_turn if ready else None,
            METHOD_VERSION,
            (
                "PHASE_ESTIMATE_DIAGNOSTIC_ONLY",
                "QUALITY_LABEL_ONLY_VIA_ADR_0046_TIMING_QUALIFIER",
                "NOT_A_PROBABILITY_OR_TURN_FORECAST",
            ),
        )


class CycleEngine:
    """The six-scale hierarchical family. Input bars must be completed UTC bars."""

    def __init__(self) -> None:
        self.trackers = tuple(ScaleTracker(scale) for scale in SCALES)

    def on_bar(self, bar: Bar) -> None:
        for tracker in self.trackers:
            if tracker.scale.resolution == bar.timeframe:
                tracker.update(bar.open_time, bar.close_time, float(bar.close), bar.complete)

    def snapshot(self, run_id: str, decision_time: datetime) -> CycleState:
        scales = tuple(tracker.state() for tracker in self.trackers)
        groups: list[tuple[str, str | float | None]] = []
        for group in ("FAST", "INTERMEDIATE", "SLOW"):
            members = [
                s for s, t in zip(scales, self.trackers, strict=True) if t.scale.group == group
            ]
            # Individual scale disagreement stays in `scales`; SLOW is recorded, never a veto.
            usable = [s for s in members if s.quality_label == USABLE]
            ready = [s.nominal_scale for s in members if s.warmup_ready]
            groups.append((group, group_direction(usable)))
            groups.append(
                (f"{group}_usable_scales", ",".join(s.nominal_scale for s in usable) or None)
            )
            groups.append((f"{group}_warm_scales", ",".join(ready) or None))
        payload = (run_id, decision_time, METHOD_VERSION, scales)
        return CycleState(
            content_id("CYC", payload),
            run_id,
            decision_time,
            decision_time,
            METHOD_VERSION,
            METHOD_STATUS,
            SignalRole.ACTIVE,
            timing_qualifier(scales),
            tuple(groups),
            scales,
        )


def group_direction(usable: list[CycleScaleState]) -> str:
    """Descriptive direction of one group's USABLE scales (display/record only)."""
    if not usable:
        return "UNKNOWN_NO_USABLE_SCALE"
    slopes = {s.slope_direction for s in usable}
    if slopes == {"RISING"}:
        return "RISING"
    if slopes == {"FALLING"}:
        return "FALLING"
    return "DISAGREE"


def timing_qualifier(scales: tuple[CycleScaleState, ...]) -> str:
    """ADR-0046 frozen timing qualifier from the six scale states."""
    by_group = {
        group: [s for s, scale in zip(scales, SCALES, strict=True) if scale.group == group]
        for group in ("FAST", "INTERMEDIATE")
    }
    fast = [s for s in by_group["FAST"] if s.quality_label == USABLE]
    intermediate = [s for s in by_group["INTERMEDIATE"] if s.quality_label == USABLE]

    def last_turn(state: CycleScaleState) -> str | None:
        return None if state.last_confirmed_turn is None else state.last_confirmed_turn.kind

    if (
        fast
        and all(s.slope_direction == "RISING" for s in fast)
        and not any(last_turn(s) == "CONFIRMED_DOWN_TURN" for s in intermediate)
    ):
        return SUPPORTS_LONG
    if (
        fast
        and all(s.slope_direction == "FALLING" for s in fast)
        and not any(last_turn(s) == "CONFIRMED_UP_TURN" for s in intermediate)
    ):
        return SUPPORTS_SHORT
    return MIXED_OR_WEAK


def decision_timing_qualifier(state: CycleState) -> str:
    """The only cycle value the decision path may read (ADR-0046 active component)."""
    if not CYCLE_DECISION_ACTIVATION or state.decision_role is not SignalRole.ACTIVE:
        return NOT_READY_QUALIFIER
    return state.timing_qualifier
