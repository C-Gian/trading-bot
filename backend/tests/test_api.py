import json
from datetime import UTC, datetime

import pytest
from app.data.policy import require_allowed
from app.main import app, create_app
from app.state import StateRepository
from fastapi.testclient import TestClient


def fixture_state(tmp_path, **changes):
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    state = json.loads((root / "state/current_state.json").read_text())
    state.update(changes)
    path = tmp_path / "state.json"
    path.write_text(json.dumps(state))
    return path


def test_api_reads_authoritative_fixture_state(tmp_path):
    path = fixture_state(tmp_path, project_phase="BASELINE_RESEARCH", status="REVIEWED")
    client = TestClient(create_app(path, lambda: False))
    health = client.get("/api/v1/system/health").json()
    assert health["project_phase"] == "BASELINE_RESEARCH" and health["status"] == "REVIEWED"
    assert health["development_data_available"] is False
    assert client.get("/api/v1/state").json()["latest_reviewed_checkpoint"] == "WP-001"


def test_research_api_uses_fixture_counters(tmp_path):
    path = fixture_state(tmp_path, experiments_completed=7, champion_status="FIXTURE_ONLY")
    payload = TestClient(create_app(path)).get("/api/v1/research/status").json()
    assert payload["experiments_completed"] == 7 and payload["champion"] == "FIXTURE_ONLY"


def test_cutoff_guards(tmp_path):
    with pytest.raises(ValueError):
        require_allowed("BTCUSDT", datetime(2025, 1, 1, tzinfo=UTC))
    client = TestClient(create_app(fixture_state(tmp_path)))
    response = client.get(
        "/api/v1/market/candles",
        params={"start": "2024-12-31T00:00:00Z", "end": "2025-01-01T00:00:00Z"},
    )
    assert response.status_code == 400


def test_substrate_versions_come_from_state(tmp_path):
    state_path = fixture_state(tmp_path)
    payload = TestClient(create_app(state_path)).get("/api/v1/backtest/substrate").json()
    assert payload["engine_version"] == "BACKTEST_ENGINE_V1"


def test_repository_state_and_default_api_are_consistent():
    state = StateRepository().load()
    client = TestClient(app)
    health = client.get("/api/v1/system/health").json()
    research = client.get("/api/v1/research/status").json()
    assert (
        health["project_phase"] == state["project_phase"]
        and health["real_money_authorized"] == state["real_money_authorized"]
    )
    assert (
        research["experiments_completed"] == state["experiments_completed"]
        and research["champion"] == state["champion_status"]
    )
