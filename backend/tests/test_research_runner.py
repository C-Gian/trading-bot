from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from app.main import create_app
from app.research.local_runner import (
    CandidateDefinition,
    CandidateRegistry,
    LocalResearchRunner,
    RunConflictError,
    RunContext,
    RunStore,
    build_review_bundle,
    wp015_registry,
)
from fastapi.testclient import TestClient

EVIDENCE = "REPRODUCTION_OF_ALREADY_EXPOSED_DEVELOPMENT_RESULT"
STAGES = (
    "READY",
    "PREPARING_DATA",
    "VALIDATING_INPUTS",
    "FOLD_2020",
    "COST_STRESS",
    "RECONCILIATION",
    "FINALIZING",
    "COMPLETED",
    "FAILED",
    "INTERRUPTED",
)


def result(context: RunContext) -> dict[str, Any]:
    return {
        "candidate_id": context.candidate.candidate_id,
        "run_id": context.run_id,
        "status": "COMPLETED",
        "classification": "REJECT_COST_DOMINATED",
        "verdict": "RIPRODUZIONE CONCILIATA",
        "default_expectancy_r": -0.08,
        "zero_cost_expectancy_r": 0.04,
        "double_cost_expectancy_r": -0.20,
        "delay_expectancy_r": -0.09,
        "trade_count": 10,
        "nonnegative_folds": 1,
        "fold_count": 5,
        "minimum_fold_trades": 1,
        "control_default_expectancy_r": -0.12,
        "primary_minus_control_r": 0.04,
        "oos_correlation": 0.01,
        "reconciliation_status": "PASS",
        "scientific_evidence_type": EVIDENCE,
        "code_head": "abc123",
        "dataset_identities": {"fixture": "sha256"},
        "fold_summary": [{"fold_id": "DEV-2020", "expectancy_r": -0.08, "trades": 10}],
        "cost_stress": {"DEFAULT": -0.08, "DOUBLE": -0.20},
        "warnings": ["NOT A NEW EXPERIMENT"],
    }


def fixture_candidate(adapter: Any) -> CandidateDefinition:
    return CandidateDefinition(
        candidate_id="FIXED_REPRODUCTION",
        display_name="Fixture",
        purpose="Synthetic lifecycle fixture",
        run_type="REPRODUCTION_ONLY",
        status="AVAILABLE",
        expected_stages=STAGES,
        required_local_datasets=("fixture.dat",),
        fixed_runner_adapter="tests.fixture",
        scientific_warning="NOT A NEW EXPERIMENT",
        scientific_evidence_type=EVIDENCE,
        execution_counts_as_new_evidence=False,
        preregistration_sha256=(),
        adapter=adapter,
    )


def runner(tmp_path: Path, adapter: Any) -> LocalResearchRunner:
    (tmp_path / "fixture.dat").write_text("synthetic", encoding="utf-8")
    registry = CandidateRegistry((fixture_candidate(adapter),))
    return LocalResearchRunner(registry, tmp_path, RunStore(tmp_path / "runs"))


def wait_terminal(service: LocalResearchRunner, run_id: str) -> dict[str, Any]:
    for _ in range(100):
        record = service.read(run_id)
        if record["status"] in {"COMPLETED", "FAILED"}:
            return record
        time.sleep(0.01)
    raise AssertionError("synthetic run did not reach a terminal state")


def test_registry_is_exactly_two_fixed_allowlisted_candidates() -> None:
    registry = wp015_registry()
    assert len(registry) == 2
    attention = registry.get("WP016_WIKIPEDIA_ATTENTION_V1")
    assert attention.run_type == "NEW_EXPERIMENT"
    assert attention.execution_counts_as_new_evidence is True
    assert attention.preregistration_ready(Path(__file__).resolve().parents[2]) is True
    assert "NEW PREREGISTERED DEVELOPMENT EXPERIMENT" in attention.scientific_warning
    candidate = registry.get("WP015_REPRODUCTION_V1")
    assert candidate.run_type == "REPRODUCTION_ONLY"
    assert candidate.execution_counts_as_new_evidence is False
    assert candidate.scientific_evidence_type == EVIDENCE
    assert "NOT A NEW EXPERIMENT" in candidate.scientific_warning
    with pytest.raises(Exception, match="fixed allowlist"):
        registry.get("../../scripts/run_anything.py")


def test_required_data_readiness_is_explicit_and_blocks_start(tmp_path: Path) -> None:
    service = LocalResearchRunner(
        CandidateRegistry((fixture_candidate(lambda context: result(context)),)),
        tmp_path,
        RunStore(tmp_path / "runs"),
    )
    candidate = service.overview()["candidates"][0]
    assert candidate["required_data"] == {
        "ready": False,
        "files": {"fixture.dat": False},
    }
    with pytest.raises(Exception, match="required local datasets"):
        service.start("FIXED_REPRODUCTION")


def test_progress_result_and_review_bundle_are_persisted(tmp_path: Path) -> None:
    def adapter(context: RunContext) -> dict[str, Any]:
        context.progress("VALIDATING_INPUTS", 10, "synthetic inputs")
        context.progress("FOLD_2020", 50, "synthetic fold")
        context.progress("RECONCILIATION", 90, "synthetic reconciliation")
        return result(context)

    service = runner(tmp_path, adapter)
    started = service.start("FIXED_REPRODUCTION")
    assert started["status"] == "QUEUED"
    final = wait_terminal(service, started["run_id"])
    assert final["status"] == "COMPLETED" and final["progress"] == 100
    assert final["result"]["scientific_evidence_type"] == EVIDENCE
    bundle = json.loads(final["review_bundle"])
    assert bundle["candidate"] == "FIXED_REPRODUCTION"
    assert bundle["new_experiment"] is False
    assert bundle["reconciliation_status"] == "PASS"
    refreshed = LocalResearchRunner(service.registry, tmp_path, RunStore(tmp_path / "runs")).read(
        started["run_id"]
    )
    assert refreshed["result"] == final["result"]


def test_one_active_run_lock_rejects_duplicate_start(tmp_path: Path) -> None:
    release = threading.Event()

    def adapter(context: RunContext) -> dict[str, Any]:
        context.progress("FOLD_2020", 50, "waiting fixture")
        assert release.wait(timeout=3)
        return result(context)

    service = runner(tmp_path, adapter)
    first = service.start("FIXED_REPRODUCTION")
    with pytest.raises(RunConflictError):
        service.start("FIXED_REPRODUCTION")
    release.set()
    assert wait_terminal(service, first["run_id"])["status"] == "COMPLETED"


def test_adapter_failure_is_useful_and_releases_lock(tmp_path: Path) -> None:
    def failing(_context: RunContext) -> dict[str, Any]:
        raise ValueError("synthetic failure")

    service = runner(tmp_path, failing)
    first = service.start("FIXED_REPRODUCTION")
    failed = wait_terminal(service, first["run_id"])
    assert failed["stage"] == "FAILED"
    assert failed["error"] == "ValueError: synthetic failure"
    second = service.start("FIXED_REPRODUCTION")
    assert wait_terminal(service, second["run_id"])["status"] == "FAILED"


def test_backend_restart_marks_unfinished_record_interrupted(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs")
    record = {
        "run_id": "a" * 32,
        "candidate_id": "FIXED_REPRODUCTION",
        "status": "RUNNING",
        "stage": "FOLD_2020",
        "progress": 30,
        "started_at": "2026-09-13T10:00:00Z",
        "finished_at": None,
    }
    store.write(record)
    run_id = str(record["run_id"])
    store.acquire(run_id)
    store.recover_interrupted()
    recovered = store.read(run_id)
    assert recovered["status"] == "FAILED"
    assert recovered["stage"] == "INTERRUPTED"
    assert "restarted" in recovered["error"]
    assert not store.lock_path.exists()


def test_api_accepts_only_candidate_id_and_returns_persisted_run(tmp_path: Path) -> None:
    def adapter(context: RunContext) -> dict[str, Any]:
        return result(context)

    service = runner(tmp_path, adapter)
    state_root = Path(__file__).resolve().parents[2]
    state_path = tmp_path / "state.json"
    state_path.write_bytes((state_root / "state/current_state.json").read_bytes())
    client = TestClient(create_app(state_path=state_path, research_runner=service))
    overview = client.get("/api/v1/research/runner").json()
    assert overview["runner_status"] == "IDLE"
    assert overview["arbitrary_execution"] is False
    assert len(overview["candidates"]) == 1
    rejected = client.post(
        "/api/v1/research/runner/runs",
        json={"candidate_id": "FIXED_REPRODUCTION", "command": "anything"},
    )
    assert rejected.status_code == 422
    assert (
        client.post("/api/v1/research/runner/runs", json={"candidate_id": "UNKNOWN"}).status_code
        == 404
    )
    started = client.post(
        "/api/v1/research/runner/runs", json={"candidate_id": "FIXED_REPRODUCTION"}
    )
    assert started.status_code == 202
    run_id = started.json()["run_id"]
    final = wait_terminal(service, run_id)
    response = client.get(f"/api/v1/research/runner/runs/{run_id}")
    assert response.status_code == 200
    assert response.json()["result"] == final["result"]
    assert client.get("/api/v1/research/runner/runs/not-a-run").status_code == 404


def test_review_bundle_omits_logs_and_declares_reproduction(tmp_path: Path) -> None:
    candidate = fixture_candidate(lambda context: result(context))
    context = RunContext(tmp_path, tmp_path, "b" * 32, candidate, lambda *_: None)
    payload = result(context)
    payload["giant_logs"] = "do not copy"
    bundle = build_review_bundle(payload)
    assert "giant_logs" not in bundle
    assert "REPRODUCTION_OF_ALREADY_EXPOSED_DEVELOPMENT_RESULT" in bundle
    assert '"new_experiment": false' in bundle


def test_review_bundle_declares_a_new_experiment_when_adapter_does(tmp_path: Path) -> None:
    candidate = fixture_candidate(lambda context: result(context))
    context = RunContext(tmp_path, tmp_path, "c" * 32, candidate, lambda *_: None)
    payload = result(context)
    payload["new_experiment"] = True
    assert json.loads(build_review_bundle(payload))["new_experiment"] is True


def test_synthetic_runner_never_mutates_scientific_state(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text('{"experiments_completed":25,"sealed_queries":0}', encoding="utf-8")
    before = state.read_bytes()
    service = runner(tmp_path, lambda context: result(context))
    started = service.start("FIXED_REPRODUCTION")
    assert wait_terminal(service, started["run_id"])["status"] == "COMPLETED"
    assert state.read_bytes() == before
    assert not (tmp_path / "data/sealed").exists()
    assert not (tmp_path / "data/paper").exists()
