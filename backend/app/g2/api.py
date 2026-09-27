"""Thin HTTP boundary for G2 engineering replay (`/api/v1/g2`).

Routes translate HTTP to the replay service only. No route accepts a scientific parameter,
threshold, price, plan or timestamp: the inputs are a registered run key, replay verbs, a speed
from the fixed pacing list, a step unit and elapsed UI wall time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .contract import IMPLEMENTATION_VERSION, SYSTEM_VERSION
from .cycle import RUNTIME_ROLE
from .service import (
    G2ReplayService,
    RunNotCompleteError,
    UnknownRecordError,
    UnknownRunError,
    UnknownSessionError,
)


class SessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_key: str


class ControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["start", "pause", "step", "speed"]
    speed: int | None = None
    unit: Literal["15m", "1h", "1d"] = "15m"


class TickRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    wall_seconds: float = Field(gt=0, le=5)


def g2_router(service: G2ReplayService, load_state: Callable[[], dict[str, Any]]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/g2")

    @router.get("/status")
    def status():
        current = load_state().get("current_project_status", {})
        return {
            "generation": current.get("active_system_generation"),
            "system_version": SYSTEM_VERSION,
            "implementation": IMPLEMENTATION_VERSION,
            "validated_strategy": current.get("validated_strategy"),
            "operational_action": "NO_TRADE",
            "market_trial_authorized": current.get("market_trial_authorized"),
            "cycle_runtime_role": RUNTIME_ROLE,
            "registered_runs": [run["run_key"] for run in service.runs()],
            "evidence": "ENGINEERING_ONLY_NOT_PERFORMANCE_EVIDENCE",
        }

    @router.get("/runs")
    def runs():
        return {"runs": service.runs()}

    @router.get("/runs/{run_name}/latest")
    def latest(run_name: str):
        try:
            return service.latest(run_name)
        except UnknownRunError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.get("/runs/{run_name}/review")
    def review(run_name: str):
        try:
            return service.review(run_name)
        except UnknownRunError as exc:
            raise HTTPException(404, str(exc)) from exc
        except RunNotCompleteError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/replay/sessions", status_code=201)
    def create_session(request: SessionRequest):
        try:
            return service.create_session(request.run_key)
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

    @router.get("/replay/sessions/{session_id}/lineage/{decision_id}")
    def lineage(session_id: str, decision_id: str):
        try:
            return service.lineage(session_id, decision_id)
        except UnknownSessionError as exc:
            raise HTTPException(404, str(exc)) from exc
        except UnknownRecordError as exc:
            raise HTTPException(404, str(exc)) from exc

    return router
