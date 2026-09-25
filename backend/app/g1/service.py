"""Registered synthetic run, replay sessions and the two API view modes.

- causal cursor view: only records with `available_at <= cursor` (realized scores only after
  target maturity, fills only after they happen);
- completed-run review view: the whole run, available only once a run has completed.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from . import dev_fixtures, fixtures
from .bars import CausalView
from .canonical import to_plain
from .clock import SPEEDS, ReplayController, ReplayStatus
from .core import G1Core, run_manifest, run_to_end
from .development import DevelopmentEngine, development_manifest, drive, primary_book
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


@dataclass
class RegisteredRun:
    kind: str
    fixture_id: str
    description: str
    manifest: RunManifest
    bars: tuple[Any, ...]
    factory: Callable[[], Any]


class G1ReplayService:
    """Synthetic registered runs only: the Checkpoint-1 contract fixture and the frozen
    Development V1 engine on a synthetic path (displaying S_FULL or S0)."""

    def __init__(self) -> None:
        self.bars = fixtures.minute_path()
        self.policy = RiskPolicy()
        self.manifest: RunManifest = run_manifest(
            self.bars, fixtures.START, fixtures.END, self.policy
        )
        self.registry: dict[str, RegisteredRun] = {
            self.manifest.run_id: RegisteredRun(
                "CHECKPOINT_1_CONTRACT_FIXTURE",
                fixtures.FIXTURE_ID,
                "Checkpoint-1 scripted contract fixture",
                self.manifest,
                self.bars,
                self.new_core,
            )
        }
        self._dev_bars: tuple[Any, ...] | None = None
        for config_id in ("S_FULL", "S0"):
            self._register_development(config_id)
        self.sessions: dict[str, ReplayController] = {}
        self._ids = itertools.count(1)
        self._completed: dict[str, Any] = {}
        self._post = PostAnalysisStore()

    # ---------------------------------------------------------------- registry
    def new_core(self) -> G1Core:
        return G1Core(self.manifest, fixtures.scenario_step, fixtures.FUNDING_RATES, self.policy)

    def development_bars(self) -> tuple[Any, ...]:
        if self._dev_bars is None:
            self._dev_bars = dev_fixtures.synthetic_path()
        return self._dev_bars

    def _register_development(self, config_id: str) -> None:
        book = primary_book(config_id, dev_fixtures.START, dev_fixtures.END)
        manifest = development_manifest(
            (
                (dev_fixtures.FIXTURE_ID, f"seed={dev_fixtures.SEED}"),
                ("display_configuration", config_id),
            ),
            dev_fixtures.START,
            dev_fixtures.END,
            (book,),
            "SYNTHETIC_FIXTURE_NOT_MARKET_EVIDENCE",
            "SYNTHETIC_REPLAY_REGISTRATION",
        )

        def factory() -> DevelopmentEngine:
            return DevelopmentEngine(manifest, (book,), dev_fixtures.synthetic_funding())

        self.registry[manifest.run_id] = RegisteredRun(
            "SYSTEM_G1_DEVELOPMENT_V1_ENGINE",
            dev_fixtures.FIXTURE_ID,
            f"Frozen G1 Development V1 engine, configuration {config_id}, synthetic path",
            manifest,
            (),
            factory,
        )

    def runs(self) -> list[dict[str, Any]]:
        return [
            {
                "manifest": to_plain(run.manifest),
                "kind": run.kind,
                "fixture_id": run.fixture_id,
                "description": run.description,
                "label": LABEL,
                "registered": True,
            }
            for run in self.registry.values()
        ]

    def _require_run(self, run_id: str) -> RegisteredRun:
        if run_id not in self.registry:
            raise UnknownRunError(f"unknown run {run_id}")
        return self.registry[run_id]

    def _bars_for(self, run: RegisteredRun) -> tuple[Any, ...]:
        return run.bars or self.development_bars()

    # ---------------------------------------------------------------- sessions
    def create_session(self, run_id: str) -> dict[str, Any]:
        run = self._require_run(run_id)
        if len(self.sessions) >= MAX_SESSIONS:
            self.sessions.pop(next(iter(self.sessions)))
        session_id = f"G1-REPLAY-{next(self._ids)}"
        self.sessions[session_id] = ReplayController(run.factory(), self._bars_for(run))
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
                    "setups": [_setup_panel(x) for x in latest.get("setups", ())],
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

    def completed_core(self, run_id: str | None = None) -> Any:
        run = self._require_run(run_id or self.manifest.run_id)
        key = run.manifest.run_id
        if key not in self._completed:
            if run.kind == "CHECKPOINT_1_CONTRACT_FIXTURE":
                self._completed[key] = run_to_end(run.factory(), run.bars)
            else:
                engine = drive(run.factory(), self._bars_for(run))
                engine.finish()
                self._completed[key] = engine
        return self._completed[key]

    def review_view(self, run_id: str) -> dict[str, Any]:
        self._require_run(run_id)
        core = self.completed_core(run_id)
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
        core = self.completed_core(run_id)
        before = core.fingerprint()
        windows = create_hot_windows(core, self._post)
        report = create_report(core, self._post, windows)
        assert core.fingerprint() == before
        return to_plain({"hot_windows": windows, "report": report, "run_fingerprint": before})


def _visible_bars(view: CausalView, timeframe: str) -> tuple[Any, ...]:
    return view.bars(timeframe)


def _setup_panel(setup: Any) -> dict[str, Any]:
    return {
        "playbook": setup.playbook.value,
        "side": setup.side.value,
        "reference": setup.reference,
        "stop": setup.stop,
        "objective": setup.objective,
        "reward_risk": setup.reward_risk,
        "plan_veto": setup.plan_veto,
        "reasons": list(setup.reasons),
    }


def _cycle_panel(cycle: CycleState | None) -> dict[str, Any] | None:
    if cycle is None:
        return None
    return {
        "cycle_state_id": cycle.cycle_state_id,
        "method_status": cycle.method_status,
        "decision_role": cycle.decision_role,
        "timing_qualifier": cycle.timing_qualifier,
        "groups": [[name, value] for name, value in cycle.group_summary],
        "scales": [
            {
                "nominal_scale": s.nominal_scale,
                "input_resolution": s.input_resolution,
                "warmup": f"{s.bars_seen}/{s.warmup_bars}",
                "ready": s.warmup_ready,
                "quality_label": s.quality_label,
                "dominant_period_minutes": s.dominant_period_minutes,
                "slope_direction": s.slope_direction,
                "last_confirmed_turn": None
                if s.last_confirmed_turn is None
                else s.last_confirmed_turn.kind,
            }
            for s in cycle.scales
        ],
    }


__all__ = ["G1ReplayService", "ReplayStatus"]
