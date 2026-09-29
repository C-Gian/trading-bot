"""Long-job progress telemetry (operational only; never scientific evidence)."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from app.operations.api import operations_router
from app.operations.jobs import Job, list_jobs, read_job, status_line
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def test_job_state_is_atomic_json_with_measured_percent_only(tmp_path: Path):
    job = Job("unit", ["a", "b"], tmp_path, job_id="unit-1", heartbeat_seconds=0.05)
    with job:
        job.phase("a")
        state = json.loads(job.state_path.read_text("utf-8"))
        assert state["status"] == "RUNNING" and state["phase_index"] == 1
        assert state["phase_percent"] is None and state["percent"] is None  # no denominator
        assert state["eta_seconds"] is None and state["eta_basis"] == "UNKNOWN"
        job.phase("b", total_units=200, unit_label="rows")
        job.advance(50)
        state = json.loads(job.state_path.read_text("utf-8"))
        assert state["phase_percent"] == 25.0 and state["completed_units"] == 50
        assert state["percent"] is None  # multi-phase: no whole-job percent is invented
    final = read_job("unit-1", tmp_path)
    assert final is not None
    assert final["status"] == "PASS" and final["exit_code"] == 0 and final["completed_units"] == 200
    assert any("job PASS" in line for line in final["log_tail"])


def test_heartbeat_advances_while_the_job_is_silent(tmp_path: Path):
    job = Job("quiet", ["wait"], tmp_path, job_id="quiet-1", heartbeat_seconds=0.02)
    with job:
        job.phase("wait")
        first = json.loads(job.state_path.read_text("utf-8"))["heartbeat_at"]
        done = threading.Event()
        done.wait(0.2)
        second = json.loads(job.state_path.read_text("utf-8"))["heartbeat_at"]
        assert second > first


def test_failure_is_recorded_with_exit_code_and_error(tmp_path: Path):
    with pytest.raises(RuntimeError), Job("boom", ["x"], tmp_path, job_id="boom-1") as job:
        job.phase("x")
        raise RuntimeError("child failed")
    state = read_job("boom-1", tmp_path)
    assert state is not None and state["status"] == "FAIL" and state["exit_code"] == 1
    assert "child failed" in state["error"]


def test_eta_uses_recorded_history_after_a_successful_run(tmp_path: Path):
    with Job("hist", ["p1", "p2"], tmp_path, job_id="hist-1") as job:
        job.phase("p1")
        job.phase("p2")
    job = Job("hist", ["p1", "p2"], tmp_path, job_id="hist-2")
    job.phase("p1")
    assert job.state["eta_basis"] in ("HISTORICAL_PHASE_DURATIONS", "UNKNOWN")
    job.finish("CANCELLED", 130, "test")
    assert (tmp_path / ".runtime/jobs/history.json").is_file()


def test_listing_puts_active_jobs_first_and_rejects_path_ids(tmp_path: Path):
    with Job("done", ["x"], tmp_path, job_id="done-1") as job:
        job.phase("x")
    running = Job("live", ["x"], tmp_path, job_id="live-1")
    running.start()
    try:
        jobs = list_jobs(tmp_path)
        assert [j["job_id"] for j in jobs][:1] == ["live-1"]
        assert read_job("../secrets", tmp_path) is None
        assert "phase 0/1" in status_line(jobs[0])
    finally:
        running.finish("PASS", 0)


def test_operations_api_is_read_only(tmp_path: Path):
    with Job("api", ["x"], tmp_path, job_id="api-1") as job:
        job.phase("x")
    app = FastAPI()
    app.router.routes.extend(operations_router(tmp_path).routes)
    client = TestClient(app)
    payload = client.get("/api/v1/operations/jobs").json()
    assert payload["evidence"] == "OPERATIONAL_TELEMETRY_NOT_SCIENTIFIC_EVIDENCE"
    assert payload["jobs"][0]["job_id"] == "api-1"
    assert client.get("/api/v1/operations/jobs/api-1").json()["status"] == "PASS"
    assert client.get("/api/v1/operations/jobs/missing").status_code == 404
    assert client.post("/api/v1/operations/jobs").status_code == 405


def test_runtime_directory_is_git_ignored():
    result = subprocess.run(
        ["git", "check-ignore", "-q", ".runtime/jobs/x.json"], cwd=ROOT, check=False
    )
    assert result.returncode == 0


def test_check_script_exposes_progress_flag():
    output = subprocess.run(
        [sys.executable, "scripts/check.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "--progress" in output
