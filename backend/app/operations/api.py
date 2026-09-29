"""Read-only operations API (`/api/v1/operations`): long-job progress for the local app.

GET only. No route starts, stops or reconfigures a job, and nothing here can change a scientific
parameter. The payload is runtime telemetry, never scientific evidence.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from .jobs import ROOT, list_jobs, read_job


def operations_router(root: Path = ROOT) -> APIRouter:
    router = APIRouter(prefix="/api/v1/operations")

    @router.get("/jobs")
    def jobs():
        return {
            "evidence": "OPERATIONAL_TELEMETRY_NOT_SCIENTIFIC_EVIDENCE",
            "jobs": list_jobs(root),
        }

    @router.get("/jobs/{job_id}")
    def job(job_id: str):
        view = read_job(job_id, root)
        if view is None:
            raise HTTPException(status_code=404, detail="unknown job")
        return view

    return router
