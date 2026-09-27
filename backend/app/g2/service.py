"""G2 replay/product boundary: registered engineering runs, causal cursor sessions, review.

Every view is a projection of the records the authoritative `G2Core` issued. The causal cursor
view returns only records whose `available_at` is at or before the cursor (a prediction's outcome,
a fill or a label is invisible until its own availability instant). The completed-run review is
available only after a replay session of that run has reached completion. Nothing here computes a
forecast, a decision, a fill or an accounting value.
"""

from __future__ import annotations

import bisect
import itertools
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from . import runs
from .bars import Bar, completed_bars
from .contract import DECISION_MINUTES, MINUTE
from .core import G2Core
from .records import (
    ClosedTrade,
    CycleShadowState,
    Decision,
    FitManifest,
    FundingEvent,
    MarketState,
    OrderIntent,
    Prediction,
    PredictionOutcome,
    RiskStateEvent,
    ShadowLabel,
    SimulatedFill,
    SourceAuditEvent,
    StopExpiryEvent,
)
from .store import plain

SPEEDS = (900, 3600, 14400, 86400)  # virtual seconds per wall second (pacing only)
DEFAULT_SPEED = 3600
CANDLES = 192
MAX_SESSIONS = 8
STEP_UNITS = {"15m": timedelta(minutes=15), "1h": timedelta(hours=1), "1d": timedelta(days=1)}
LABEL = runs.NOT_PERFORMANCE_EVIDENCE


class UnknownRunError(LookupError):
    pass


class UnknownSessionError(LookupError):
    pass


class RunNotCompleteError(RuntimeError):
    pass


class UnknownRecordError(LookupError):
    pass


@dataclass
class ComputedRun:
    built: runs.BuiltRun
    core: G2Core
    candles: list[Bar]
    candle_close: list[datetime]
    fingerprint: str


@dataclass
class Session:
    session_id: str
    run_key: str
    cursor: datetime
    status: str = "READY"
    speed: int = DEFAULT_SPEED
    carry: float = 0.0
    history: list[str] = field(default_factory=list)


def _engineering_data_present(root: Path) -> bool:
    start, _ = runs.ENGINEERING_WINDOW
    path = root / f"data/raw/public-taker-flow/um/BTCUSDT-1m-{start:%Y-%m}.zip"
    return path.is_file()


class G2ReplayService:
    def __init__(self, root: Path | None = None, include_engineering_window: bool = True) -> None:
        from .sources import ROOT

        self.root = root or ROOT
        self.specs: dict[str, runs.RunSpec] = {}
        synthetic = runs.synthetic_spec()
        self.specs[synthetic.key] = synthetic
        if include_engineering_window and _engineering_data_present(self.root):
            window = runs.engineering_window_spec(self.root)
            self.specs[window.key] = window
        self._computed: dict[str, ComputedRun] = {}
        self._completed: set[str] = set()
        self._lock = threading.Lock()
        self.sessions: dict[str, Session] = {}
        self._ids = itertools.count(1)

    # ------------------------------------------------------------ registry
    def runs(self) -> list[dict[str, Any]]:
        out = []
        for key, spec in self.specs.items():
            computed = self._computed.get(key)
            out.append(
                {
                    "run_key": key,
                    "label": spec.label,
                    "evidence_class": spec.evidence_class,
                    "evidence_label": LABEL,
                    "description": spec.description,
                    "dataset_start": plain(spec.start),
                    "dataset_end": plain(spec.end),
                    "computed": computed is not None,
                    "run_id": None if computed is None else computed.built.manifest.run_id,
                    "review_available": key in self._completed,
                }
            )
        return out

    def computed(self, key: str) -> ComputedRun:
        spec = self.specs.get(key)
        if spec is None:
            raise UnknownRunError(f"unknown G2 run {key}")
        with self._lock:
            existing = self._computed.get(key)
            if existing is not None:
                return existing
            built = runs.build(spec)
            core = runs.run_batch(built)
            candles = completed_bars(built.minutes, "15m")
            result = ComputedRun(
                built, core, candles, [c.close_time for c in candles], core.store.fingerprint()
            )
            self._computed[key] = result
            return result

    # ------------------------------------------------------------ sessions
    def create_session(self, key: str) -> dict[str, Any]:
        run = self.computed(key)
        if len(self.sessions) >= MAX_SESSIONS:
            self.sessions.pop(next(iter(self.sessions)))
        session = Session(f"G2SES-{next(self._ids):04d}", key, run.built.manifest.dataset_start)
        self.sessions[session.session_id] = session
        return self.cursor_view(session.session_id)

    def _session(self, session_id: str) -> Session:
        session = self.sessions.get(session_id)
        if session is None:
            raise UnknownSessionError(f"unknown G2 session {session_id}")
        return session

    def _move(self, session: Session, target: datetime) -> None:
        end = self._computed[session.run_key].built.manifest.dataset_end
        session.cursor = min(max(target, session.cursor), end)
        if session.cursor >= end:
            session.status = "COMPLETE"
            self._completed.add(session.run_key)

    def control(
        self, session_id: str, action: str, speed: int | None = None, unit: str = "15m"
    ) -> dict[str, Any]:
        session = self._session(session_id)
        if action == "start":
            if session.status != "COMPLETE":
                session.status = "RUNNING"
        elif action == "pause":
            if session.status == "RUNNING":
                session.status = "PAUSED"
        elif action == "speed":
            if speed not in SPEEDS:
                raise ValueError(f"speed must be one of {SPEEDS}")
            session.speed = speed
        elif action == "step":
            if session.status == "RUNNING":
                raise ValueError("pause before single-stepping")
            if unit not in STEP_UNITS:
                raise ValueError(f"step unit must be one of {tuple(STEP_UNITS)}")
            if session.status != "COMPLETE":
                step = STEP_UNITS[unit]
                cursor = session.cursor + MINUTE
                while (cursor - session.cursor) < step or cursor.minute % DECISION_MINUTES:
                    cursor += MINUTE
                self._move(session, cursor)
                if session.status == "READY":
                    session.status = "PAUSED"
        else:
            raise ValueError(f"unknown control {action}")
        session.history.append(action)
        return self.cursor_view(session_id)

    def tick(self, session_id: str, wall_seconds: float) -> dict[str, Any]:
        session = self._session(session_id)
        if not 0 < wall_seconds <= 5:
            raise ValueError("wall_seconds must be in (0, 5]")
        if session.status == "RUNNING":
            session.carry += session.speed * wall_seconds
            minutes = max(1, int(session.carry // 60))
            session.carry = max(0.0, session.carry - minutes * 60)
            self._move(session, session.cursor + minutes * MINUTE)
        return self.cursor_view(session_id)

    # ------------------------------------------------------------ views
    def cursor_view(self, session_id: str) -> dict[str, Any]:
        session = self._session(session_id)
        run = self._computed[session.run_key]
        return {
            "mode": "CAUSAL_CURSOR",
            "session_id": session.session_id,
            "status": session.status,
            "speed": session.speed,
            "speeds": list(SPEEDS),
            "step_units": list(STEP_UNITS),
            **self._frame(run, session.cursor),
        }

    def _frame(self, run: ComputedRun, cursor: datetime) -> dict[str, Any]:
        store = run.core.store
        manifest = run.built.manifest
        hi = bisect.bisect_right(run.candle_close, cursor)
        candles = run.candles[max(0, hi - CANDLES) : hi]
        window_start = candles[0].open_time if candles else manifest.dataset_start

        def recent(kind: type) -> list[Any]:
            return [r for r in store.visible(kind, cursor) if r.available_at >= window_start]

        def latest(kind: type) -> Any:
            rows = store.visible(kind, cursor)
            return rows[-1] if rows else None

        predictions = recent(Prediction)
        decisions = recent(Decision)
        fills = recent(SimulatedFill)
        trades = store.visible(ClosedTrade, cursor)
        entries = {f.trade_id: f for f in store.visible(SimulatedFill, cursor) if f.kind == "ENTRY"}
        closed_ids = {t.trade_id for t in trades}
        open_trade = next((plain(f) for tid, f in entries.items() if tid not in closed_ids), None)
        current_prediction = latest(Prediction)
        return {
            "label": LABEL,
            "run_key": run.built.spec.key,
            "run_id": manifest.run_id,
            "evidence_class": manifest.evidence_class,
            "cursor": plain(cursor),
            "dataset_start": plain(manifest.dataset_start),
            "dataset_end": plain(manifest.dataset_end),
            "candles": [
                {
                    "open_time": plain(c.open_time),
                    "available_at": plain(c.close_time),
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "complete": c.complete,
                }
                for c in candles
            ],
            "prediction_markers": [
                {
                    "prediction_id": p.prediction_id,
                    "decision_time": plain(p.decision_time),
                    "direction": p.direction,
                    "median_return": p.median_return,
                    "status": p.calibration_status,
                }
                for p in predictions
            ],
            "decision_markers": [
                {
                    "decision_id": d.decision_id,
                    "decision_time": plain(d.decision_time),
                    "action": str(d.action),
                    "policy_selection": d.policy_selection,
                    "reason_codes": list(d.reason_codes),
                }
                for d in decisions
                if d.action != "NO_TRADE" or d.policy_selection != "NONE"
            ],
            "fills": [plain(f) for f in fills],
            "closed_trades": [plain(t) for t in trades[-20:]],
            "current": {
                "state": plain(latest(MarketState)),
                "prediction": plain(current_prediction),
                "decision": plain(latest(Decision)),
                "cycle": plain(latest(CycleShadowState)),
                "risk": plain(latest(RiskStateEvent)),
                "open_position": open_trade,
                "fit": [plain(f) for f in store.visible(FitManifest, cursor)[-3:]],
            },
            "visible_counts": {
                kind.__name__: len(store.visible(kind, cursor))
                for kind in (
                    Prediction,
                    PredictionOutcome,
                    Decision,
                    ShadowLabel,
                    OrderIntent,
                    SimulatedFill,
                    ClosedTrade,
                )
            },
            "production_action": "NO_TRADE",
            "validated_strategy": None,
            "cycle_role": "SHADOW",
        }

    def lineage(self, session_id: str, decision_id: str) -> dict[str, Any]:
        session = self._session(session_id)
        return self._lineage(self._computed[session.run_key], decision_id, session.cursor)

    def _lineage(self, run: ComputedRun, decision_id: str, cursor: datetime) -> dict[str, Any]:
        store = run.core.store
        decision = store.get(decision_id)
        if not isinstance(decision, Decision) or decision.available_at > cursor:
            raise UnknownRecordError(f"decision {decision_id} is not visible at the cursor")

        def visible(record: Any) -> Any:
            return None if record is None or record.available_at > cursor else plain(record)

        t = decision.decision_time
        prediction = store.get(decision.prediction_id)
        intents = [i for i in store.visible(OrderIntent, cursor) if i.decision_id == decision_id]
        intent_ids = {i.intent_id for i in intents}
        fills = [f for f in store.visible(SimulatedFill, cursor) if f.intent_id in intent_ids]
        trade_ids = {f.trade_id for f in fills}
        return {
            "label": LABEL,
            "cursor": plain(cursor),
            "decision": plain(decision),
            "prediction": visible(prediction),
            "state": visible(store.get(prediction.state_id)) if prediction else None,
            "cycle": visible(
                next(
                    (c for c in store.visible(CycleShadowState, cursor) if c.decision_time == t),
                    None,
                )
            ),
            "prediction_outcome": next(
                (
                    plain(o)
                    for o in store.visible(PredictionOutcome, cursor)
                    if o.prediction_id == decision.prediction_id
                ),
                None,
            ),
            "shadow_labels": [
                plain(label)
                for label in store.visible(ShadowLabel, cursor)
                if label.decision_time == t
            ],
            "order_intents": [plain(i) for i in intents],
            "fills": [plain(f) for f in fills],
            "funding": [
                plain(f) for f in store.visible(FundingEvent, cursor) if f.trade_id in trade_ids
            ],
            "stop_expiry": [
                plain(e) for e in store.visible(StopExpiryEvent, cursor) if e.trade_id in trade_ids
            ],
            "closed_trade": [
                plain(c) for c in store.visible(ClosedTrade, cursor) if c.trade_id in trade_ids
            ],
        }

    def review(self, key: str) -> dict[str, Any]:
        if key not in self.specs:
            raise UnknownRunError(f"unknown G2 run {key}")
        if key not in self._completed:
            raise RunNotCompleteError("the completed-run review is available only after completion")
        run = self._computed[key]
        store = run.core.store
        decisions = store.of_type(Decision)
        reasons: dict[str, int] = {}
        for decision in decisions:
            for code in decision.reason_codes:
                reasons[code] = reasons.get(code, 0) + 1
        return {
            "mode": "COMPLETED_RUN_REVIEW",
            "label": LABEL,
            "run_key": key,
            "manifest": plain(run.built.manifest),
            "fingerprint": run.fingerprint,
            "record_counts": store.counts(),
            "decision_reason_counts": dict(sorted(reasons.items())),
            "fits": [plain(f) for f in store.of_type(FitManifest)],
            "source_audit": [plain(a) for a in store.of_type(SourceAuditEvent)],
            "closed_trades": [plain(t) for t in store.of_type(ClosedTrade)],
            "economic_summary": "NOT_COMPUTED_G2_01_ENGINEERING_ONLY",
        }

    def latest(self, key: str) -> dict[str, Any]:
        """The latest G2 state of a registered run at its end (Home surface)."""
        run = self.computed(key)
        end = run.built.manifest.dataset_end
        frame = self._frame(run, end)
        return {
            "mode": "REGISTERED_RUN_LATEST_STATE",
            "label": LABEL,
            "run_key": key,
            "run_id": frame["run_id"],
            "evidence_class": frame["evidence_class"],
            "cursor": frame["cursor"],
            "current": frame["current"],
            "production_action": "NO_TRADE",
            "validated_strategy": None,
        }
