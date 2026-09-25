"""Registered synthetic run, replay sessions and the two API view modes.

- causal cursor view: only records with `available_at <= cursor` (realized scores only after
  target maturity, fills only after they happen);
- completed-run review view: the whole run, available only once a run has completed.
"""

from __future__ import annotations

import itertools
from datetime import timedelta
from typing import Any

from . import fixtures
from .bars import CausalView
from .canonical import to_plain
from .clock import SPEEDS, ReplayController, ReplayStatus
from .core import G1Core, run_manifest, run_to_end
from .ledger import RiskPolicy
from .post_analysis import PostAnalysisStore, create_hot_windows, create_report
from .records import (
    ClosedTrade,
    CycleState,
    DecisionSnapshot,
    OrderFillEvent,
    PredictionRealization,
    PredictionSnapshot,
    RunManifest,
    TradePlan,
)
from .stats import LABEL, running_stats

MAX_SESSIONS = 8
CANDLE_WINDOW = 96


class UnknownRunError(LookupError):
    pass


class UnknownSessionError(LookupError):
    pass


class RunNotCompleteError(RuntimeError):
    pass


class G1ReplayService:
    def __init__(self) -> None:
        self.bars = fixtures.minute_path()
        self.policy = RiskPolicy()
        self.manifest: RunManifest = run_manifest(
            self.bars, fixtures.START, fixtures.END, self.policy
        )
        self.sessions: dict[str, ReplayController] = {}
        self._ids = itertools.count(1)
        self._completed: G1Core | None = None
        self._post = PostAnalysisStore()

    # ---------------------------------------------------------------- registry
    def new_core(self) -> G1Core:
        return G1Core(self.manifest, fixtures.scenario_step, fixtures.FUNDING_RATES, self.policy)

    def runs(self) -> list[dict[str, Any]]:
        return [
            {
                "manifest": to_plain(self.manifest),
                "fixture_id": fixtures.FIXTURE_ID,
                "label": LABEL,
                "registered": True,
            }
        ]

    def _require_run(self, run_id: str) -> None:
        if run_id != self.manifest.run_id:
            raise UnknownRunError(f"unknown run {run_id}")

    # ---------------------------------------------------------------- sessions
    def create_session(self, run_id: str) -> dict[str, Any]:
        self._require_run(run_id)
        if len(self.sessions) >= MAX_SESSIONS:
            self.sessions.pop(next(iter(self.sessions)))
        session_id = f"G1-REPLAY-{next(self._ids)}"
        self.sessions[session_id] = ReplayController(self.new_core(), self.bars)
        return self.cursor_view(session_id)

    def controller(self, session_id: str) -> ReplayController:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise UnknownSessionError(f"unknown session {session_id}") from exc

    def control(self, session_id: str, action: str, speed: int | None, unit: str) -> dict[str, Any]:
        controller = self.controller(session_id)
        if action == "start":
            controller.start()
        elif action == "pause":
            controller.pause()
        elif action == "step":
            controller.step(unit)
        elif action == "speed":
            if speed is None:
                raise ValueError("speed is required")
            controller.set_speed(speed)
        else:
            raise ValueError(f"unknown control action {action}")
        return self.cursor_view(session_id)

    def tick(self, session_id: str, wall_seconds: float) -> dict[str, Any]:
        self.controller(session_id).tick(wall_seconds)
        return self.cursor_view(session_id)

    # ---------------------------------------------------------------- views
    def cursor_view(self, session_id: str) -> dict[str, Any]:
        controller = self.controller(session_id)
        core = controller.core
        cursor = core.cursor
        store = core.store
        candles = [bar for bar in _visible_bars(core.view, "15m") if bar.available_at <= cursor][
            -CANDLE_WINDOW:
        ]
        first = candles[0].open_time if candles else cursor
        in_window = [
            p
            for p in store.visible(PredictionSnapshot, cursor)
            if p.issue_time - timedelta(minutes=15) >= first
        ]
        prediction_ids = {p.prediction_id for p in in_window}
        realizations = [
            r
            for r in store.of_type(PredictionRealization)
            if r.available_at <= cursor and r.prediction_id in prediction_ids
        ]
        decisions = [
            d for d in store.visible(DecisionSnapshot, cursor) if d.prediction_id in prediction_ids
        ]
        plans = [p for p in store.of_type(TradePlan) if p.readiness_time <= cursor]
        fills = [
            f
            for f in store.of_type(OrderFillEvent)
            if f.available_at <= cursor and f.event_time >= first
        ]
        latest = core.latest
        return to_plain(
            {
                "mode": "CAUSAL_CURSOR",
                "label": LABEL,
                "session_id": session_id,
                "run_id": core.run_id,
                "status": controller.status.value,
                "speed": controller.speed,
                "speeds": list(SPEEDS),
                "cursor": cursor,
                "dataset_start": core.manifest.dataset_start,
                "dataset_end": core.manifest.dataset_end,
                "candles": [
                    {
                        "open_time": bar.open_time,
                        "available_at": bar.available_at,
                        "open": float(bar.open),
                        "high": float(bar.high),
                        "low": float(bar.low),
                        "close": float(bar.close),
                        "quality": bar.quality,
                    }
                    for bar in candles
                ],
                "predictions": in_window,
                "realizations": realizations,
                "decisions": decisions,
                "trade_plans": plans,
                "fills": fills,
                "current": {
                    "signals": latest.get("signals", ()),
                    "cycle": _cycle_panel(core.latest_cycle()),
                    "market_state": latest.get("market_state"),
                    "prediction": latest.get("prediction"),
                    "decision": latest.get("decision"),
                    "ledger": core.ledger.snapshot(cursor),
                },
                "stats": running_stats(store, cursor),
                "production_action": "NO_TRADE",
                "validated_strategy": None,
            }
        )

    def completed_core(self) -> G1Core:
        if self._completed is None:
            self._completed = run_to_end(self.new_core(), self.bars)
        return self._completed

    def review_view(self, run_id: str) -> dict[str, Any]:
        self._require_run(run_id)
        core = self.completed_core()
        if not core.complete:
            raise RunNotCompleteError("the run has not completed")
        store = core.store
        return to_plain(
            {
                "mode": "COMPLETED_RUN_REVIEW",
                "label": LABEL,
                "manifest": core.manifest,
                "fingerprint": core.fingerprint(),
                "record_count": len(store),
                "predictions": store.of_type(PredictionSnapshot),
                "realizations": store.of_type(PredictionRealization),
                "decisions": store.of_type(DecisionSnapshot),
                "trade_plans": store.of_type(TradePlan),
                "fills": store.of_type(OrderFillEvent),
                "trades": store.of_type(ClosedTrade),
                "stats": running_stats(store, core.cursor),
                "exposure": core.exposure_record(),
            }
        )

    def post_analysis(self, run_id: str) -> dict[str, Any]:
        self._require_run(run_id)
        core = self.completed_core()
        before = core.fingerprint()
        windows = create_hot_windows(core, self._post)
        report = create_report(core, self._post, windows)
        assert core.fingerprint() == before
        return to_plain({"hot_windows": windows, "report": report, "run_fingerprint": before})


def _visible_bars(view: CausalView, timeframe: str) -> tuple[Any, ...]:
    return view.bars(timeframe)


def _cycle_panel(cycle: CycleState | None) -> dict[str, Any] | None:
    if cycle is None:
        return None
    return {
        "cycle_state_id": cycle.cycle_state_id,
        "method_status": cycle.method_status,
        "decision_role": cycle.decision_role,
        "timing_qualifier": cycle.timing_qualifier,
        "scales": [
            {
                "nominal_scale": s.nominal_scale,
                "input_resolution": s.input_resolution,
                "warmup": f"{s.bars_seen}/{s.warmup_bars}",
                "ready": s.warmup_ready,
                "quality_label": s.quality_label,
                "dominant_period_minutes": s.dominant_period_minutes,
                "slope_direction": s.slope_direction,
            }
            for s in cycle.scales
        ],
    }


__all__ = ["G1ReplayService", "ReplayStatus"]
