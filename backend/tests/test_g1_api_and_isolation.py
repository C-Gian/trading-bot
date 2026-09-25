"""System G1 Checkpoint 1: replay API modes and HotWindow/PostAnalysisReport isolation."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from app.g1 import fixtures
from app.g1.core import G1Core, run_manifest
from app.g1.ledger import RiskPolicy
from app.g1.post_analysis import (
    PostAnalysisStore,
    RunNotCompleteError,
    create_hot_windows,
    create_report,
)
from app.g1.service import G1ReplayService
from app.main import create_app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
G1 = ROOT / "backend/app/g1"
DECISION_PATH_MODULES = (
    "bars.py",
    "signals.py",
    "cycle.py",
    "pipeline.py",
    "core.py",
    "ledger.py",
    "fixtures.py",
    "clock.py",
    "stats.py",
)
SERVICE = G1ReplayService()


def _never() -> dict:
    raise AssertionError("the historical analyser must not run")


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(analyser=_never, g1_service=SERVICE))


def _session(client: TestClient) -> tuple[str, str]:
    run_id = client.get("/api/v1/g1/runs").json()["runs"][0]["manifest"]["run_id"]
    body = client.post("/api/v1/g1/replay/sessions", json={"run_id": run_id}).json()
    return run_id, body["session_id"]


def test_status_reports_fail_closed_synthetic_only(client) -> None:
    status = client.get("/api/v1/g1/status").json()
    assert status["validated_strategy"] is None and status["operational_action"] == "NO_TRADE"
    assert status["cycle_active_in_decisions"] is False
    assert status["historical_market_trial_authorized"] is False
    assert status["evidence"] == "SYNTHETIC_FIXTURE_ONLY"
    # The production action surface stays fail-closed alongside the G1 replay slice.
    assert client.post("/api/v1/product/analysis").json()["decision"] == "NO_TRADE"


def test_causal_cursor_view_exposes_only_available_information(client) -> None:
    _, session = _session(client)
    for _ in range(40):  # 10 decision candles past the 4h warm-up... then some
        view = client.post(
            f"/api/v1/g1/replay/sessions/{session}/control", json={"action": "step"}
        ).json()
    assert view["mode"] == "CAUSAL_CURSOR" and view["cursor"] == "2001-01-30T10:00:00Z"
    cursor = view["cursor"]
    assert all(c["available_at"] <= cursor for c in view["candles"])
    assert all(p["available_at"] <= cursor for p in view["predictions"])
    assert all(d["available_at"] <= cursor for d in view["decisions"])
    assert all(f["available_at"] <= cursor for f in view["fills"])
    assert all(r["available_at"] <= cursor for r in view["realizations"])
    issued = {p["prediction_id"]: p for p in view["predictions"]}
    for realization in view["realizations"]:
        assert issued[realization["prediction_id"]]["target_end"] <= cursor
    assert len(view["realizations"]) < len(view["predictions"])  # later ones not yet matured
    assert view["current"]["decision"]["decision_time"] == cursor
    assert view["current"]["cycle"]["decision_role"] == "METHOD_NOT_READY"
    assert view["stats"]["matured"] == len(view["realizations"])
    assert view["production_action"] == "NO_TRADE" and view["validated_strategy"] is None
    assert any(f["kind"] == "ENTRY" and f["side"] == "LONG" for f in view["fills"])


def test_replay_controls_and_no_free_parameter_knobs(client) -> None:
    _, session = _session(client)
    base = f"/api/v1/g1/replay/sessions/{session}"
    assert (
        client.post(f"{base}/control", json={"action": "speed", "speed": 3600}).json()["speed"]
        == 3600
    )
    assert client.post(f"{base}/control", json={"action": "speed", "speed": 7}).status_code == 409
    started = client.post(f"{base}/control", json={"action": "start"}).json()
    assert started["status"] == "RUNNING"
    ticked = client.post(f"{base}/tick", json={"wall_seconds": 1}).json()
    assert ticked["cursor"] == "2001-01-30T01:00:00Z"
    assert client.post(f"{base}/control", json={"action": "step"}).status_code == 409
    assert client.post(f"{base}/control", json={"action": "pause"}).json()["status"] == "PAUSED"
    for forbidden in (
        {"action": "start", "threshold": 0.7},
        {"action": "start", "stop_fraction": 0.01},
        {"action": "optimize"},
    ):
        assert client.post(f"{base}/control", json=forbidden).status_code == 422
    assert client.post(f"{base}/tick", json={"wall_seconds": 60}).status_code == 422
    assert client.post("/api/v1/g1/replay/sessions", json={"run_id": "RUN-x"}).status_code == 404
    assert client.get("/api/v1/g1/replay/sessions/unknown").status_code == 404


def test_completed_run_review_is_a_distinct_mode(client) -> None:
    run_id, _ = _session(client)
    review = client.get(f"/api/v1/g1/runs/{run_id}/review").json()
    assert review["mode"] == "COMPLETED_RUN_REVIEW"
    assert len(review["predictions"]) == len(review["decisions"]) == 288
    assert review["exposure"]["market_outcomes_inspected"] is False
    assert review["exposure"]["real_market_data_read"] is False
    assert review["exposure"]["sealed_queries"] == 0
    assert review["stats"]["label"].startswith("SYNTHETIC FIXTURE")


def test_post_analysis_runs_only_after_completion_and_never_mutates_the_run(client) -> None:
    policy = RiskPolicy()
    bars = fixtures.minute_path()
    manifest = run_manifest(bars, fixtures.START, fixtures.END, policy)
    incomplete = G1Core(manifest, fixtures.scenario_step, fixtures.FUNDING_RATES, policy)
    store = PostAnalysisStore()
    with pytest.raises(RunNotCompleteError):
        create_hot_windows(incomplete, store)
    with pytest.raises(RunNotCompleteError):
        create_report(incomplete, store, ())
    run_id, _ = _session(client)
    before = client.get(f"/api/v1/g1/runs/{run_id}/review").json()["fingerprint"]
    body = client.post(f"/api/v1/g1/runs/{run_id}/post-analysis").json()
    assert body["hot_windows"] and body["report"]["decision_graph_input"] is False
    assert body["report"]["status"] == "PLACEHOLDER_NO_NEWS_OR_EVENT_SOURCE_FETCHED"
    assert all(w["created_after_run_completion"] for w in body["hot_windows"])
    assert body["run_fingerprint"] == before
    assert client.get(f"/api/v1/g1/runs/{run_id}/review").json()["fingerprint"] == before
    ids = {type(r).__name__ for r in SERVICE.completed_core().store}
    assert "HotWindow" not in ids and "PostAnalysisReport" not in ids


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_decision_path_cannot_consume_post_analysis_entities() -> None:
    for module in DECISION_PATH_MODULES:
        path = G1 / module
        imported = _imports(path)
        assert not any("post_analysis" in name for name in imported), module
        source = path.read_text(encoding="utf-8")
        assert "HotWindow" not in source and "PostAnalysisReport" not in source, module
