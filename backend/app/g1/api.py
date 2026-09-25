"""Thin HTTP boundary for the System G1 synthetic replay slice (`/api/v1/g1`).

Routes only translate HTTP to the replay service. No route accepts a scientific parameter,
threshold, price, plan or timestamp: the only inputs are a registered run identity, replay control
verbs, a speed from the fixed pacing list and elapsed UI wall time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .cycle import CYCLE_DECISION_ACTIVATION, METHOD_STATUS
from .service import (
    G1ReplayService,
    RunNotCompleteError,
    UnknownRunError,
    UnknownSessionError,
)


class SessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str


class ControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["start", "pause", "step", "speed"]
    speed: int | None = None
    unit: Literal["1m", "15m"] = "15m"


class TickRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    wall_seconds: float = Field(gt=0, le=5)


def g1_router(service: G1ReplayService, load_state: Callable[[], dict[str, Any]]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/g1")

    @router.get("/status")
    def status():
        current = load_state().get("current_project_status", {})
        return {
            "generation": current.get("active_system_generation"),
            "disposition": current.get("disposition"),
            "validated_strategy": current.get("validated_strategy"),
            "operational_action": "NO_TRADE",
            "historical_market_trial_authorized": current.get("market_trial_authorized"),
            "cycle_method_status": METHOD_STATUS,
            "cycle_active_in_decisions": CYCLE_DECISION_ACTIVATION,
            "registered_runs": [run["manifest"]["run_id"] for run in service.runs()],
            "evidence": "SYNTHETIC_FIXTURE_ONLY",
        }

    @router.get("/runs")
    def runs():
        return {"runs": service.runs()}

    @router.post("/replay/sessions", status_code=201)
    def create_session(request: SessionRequest):
        try:
            return service.create_session(request.run_id)
        except UnknownRunError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.get("/replay/sessions/{session_id}")
    def session(session_id: str):
        try:
            return service.cursor_view(session_id)
        except UnknownSessionError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.post("/replay/sessions/{session_id}/control")
    def control(session_id: str, request: ControlRequest):
        try:
            return service.control(session_id, request.action, request.speed, request.unit)
        except UnknownSessionError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/replay/sessions/{session_id}/tick")
    def tick(session_id: str, request: TickRequest):
        try:
            return service.tick(session_id, request.wall_seconds)
        except UnknownSessionError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.get("/runs/{run_id}/review")
    def review(run_id: str):
        try:
            return service.review_view(run_id)
        except UnknownRunError as exc:
            raise HTTPException(404, str(exc)) from exc
        except RunNotCompleteError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/runs/{run_id}/post-analysis")
    def post_analysis(run_id: str):
        try:
            return service.post_analysis(run_id)
        except UnknownRunError as exc:
            raise HTTPException(404, str(exc)) from exc

    return router
