"""G2-V0 cycle state: SHADOW ONLY adapter around the preserved causal ACP (checkpoint V1).

The dominant period, phase, projection coordinate, explained fraction, quality label and turn
confirmation are produced by the unchanged G1 `ScaleTracker` (the frozen ACP lineage). G2 adds two
descriptive fields that do not alter those semantics:

- PROJECTION_AMPLITUDE = 2 * sqrt(re^2 + im^2) / L at the dominant period (section 10);
- PERIOD_STABILITY = |P_t - P_(t-1)| / max(P_(t-1), 1e-12), null if either is unavailable (s. 11).

G2-V0 role: zero forecast coefficients, zero utility coefficients, no veto (CYCLE_SHADOW_ONLY).
"""

from __future__ import annotations

import math
from datetime import datetime

from app.g1.cycle import METHOD_VERSION as ACP_METHOD_VERSION
from app.g1.cycle import SCALES, UNAVAILABLE, USABLE, ScaleTracker

from .bars import Bar
from .records import CycleScaleShadow, CycleShadowState, Reason, record_key

METHOD_VERSION = f"G2-CYCLE-SHADOW-V1/{ACP_METHOD_VERSION}"
RUNTIME_ROLE = "SHADOW_ONLY"
FORECAST_COEFFICIENTS = 0
POLICY_COEFFICIENTS = 0
VETO_AUTHORITY = "NONE"
RESOLUTIONS = tuple(sorted({scale.resolution for scale in SCALES}))


def projection_amplitude(trailing: list[float], period: float) -> float | None:
    """2*sqrt(re^2+im^2)/L over the same trailing window the G1 projection uses."""
    length = round(period)
    if length < 2 or len(trailing) < length:
        return None
    window = trailing[:length]
    omega = 2 * math.pi / length
    re = sum(x * math.cos(omega * k) for k, x in enumerate(window))
    im = sum(x * math.sin(omega * k) for k, x in enumerate(window))
    return 2.0 * math.sqrt(re * re + im * im) / length


def period_stability(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return abs(current - previous) / max(previous, 1e-12)


class ShadowScale:
    """One frozen scale: the G1 tracker plus the two G2 descriptive fields."""

    def __init__(self, scale_index: int) -> None:
        self.scale = SCALES[scale_index]
        self.tracker = ScaleTracker(self.scale)
        self.amplitude: float | None = None
        self.stability: float | None = None

    def update(
        self, open_time: datetime, close_time: datetime, value: float, complete: bool
    ) -> None:
        tracker = self.tracker
        tracker.update(open_time, close_time, value, complete)
        ready = tracker.ready
        if tracker.coordinate is None or tracker.dominant is None:
            self.amplitude = None
        else:
            self.amplitude = projection_amplitude(
                tracker.acp.trailing_filtered(self.scale.period2), tracker.dominant
            )
        # Both periods must be available (ready) numeric estimates; a reset clears the previous.
        self.stability = (
            period_stability(tracker.dominant, tracker.previous_dominant) if ready else None
        )

    def state(self) -> CycleScaleShadow:
        g1 = self.tracker.state()
        label = g1.quality_label
        reason = (
            Reason.CYCLE_UNAVAILABLE
            if label == UNAVAILABLE
            else (None if label == USABLE else Reason.CYCLE_UNRELIABLE)
        )
        turn = g1.last_confirmed_turn
        explained = (
            dict(g1.quality_metrics).get("explained_fraction") if g1.quality_metrics else None
        )
        return CycleScaleShadow(
            g1.nominal_scale,
            g1.input_resolution,
            g1.warmup_ready,
            g1.gap_state,
            label,
            g1.dominant_period_bars,
            g1.dominant_period_minutes,
            g1.phase_estimate_diagnostic,
            g1.coordinate,
            self.amplitude if g1.warmup_ready else None,
            explained if isinstance(explained, float) else None,
            self.stability,
            g1.slope_direction,
            None if turn is None else turn.kind,
            None if turn is None else turn.estimated_turn_time,
            None if turn is None else turn.confirmation_time,
            None if reason is None else str(reason),
        )


class CycleShadow:
    """Six-scale shadow family fed with completed bars of its input resolutions."""

    def __init__(self) -> None:
        self.scales = tuple(ShadowScale(i) for i in range(len(SCALES)))

    def on_bar(self, bar: Bar) -> None:
        for scale in self.scales:
            if scale.scale.resolution == bar.timeframe:
                scale.update(bar.open_time, bar.close_time, bar.close, bar.complete)

    def snapshot(self, run_id: str, decision_time: datetime) -> CycleShadowState:
        states = tuple(scale.state() for scale in self.scales)
        reasons = {str(Reason.CYCLE_SHADOW_ONLY)}
        reasons.update(s.reason_code for s in states if s.reason_code is not None)
        return CycleShadowState(
            record_key("G2C", run_id, decision_time),
            run_id,
            decision_time,
            decision_time,
            METHOD_VERSION,
            RUNTIME_ROLE,
            FORECAST_COEFFICIENTS,
            POLICY_COEFFICIENTS,
            VETO_AUTHORITY,
            tuple(sorted(reasons)),
            states,
        )
