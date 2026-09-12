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
    path = fixture_state(
        tmp_path,
        project_phase="BASELINE_RESEARCH",
        status="REVIEWED",
        latest_reviewed_checkpoint="WP-002",
    )
    client = TestClient(create_app(path, lambda: False))
    health = client.get("/api/v1/system/health").json()
    assert health["project_phase"] == "BASELINE_RESEARCH" and health["status"] == "REVIEWED"
    assert health["development_data_available"] is False
    assert client.get("/api/v1/state").json()["latest_reviewed_checkpoint"] == "WP-002"


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
    assert payload["engine_version"] == "BACKTEST_ENGINE_V2"


def test_research_experiment_summary_is_read_only_and_labeled(tmp_path):
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "evidence_stage": "DEVELOPMENT BACKTEST / CONTROLS",
                "experiments": [{"experiment_id": "FIXTURE", "classification": "NEGATIVE_CONTROL"}],
            }
        )
    )
    payload = (
        TestClient(create_app(fixture_state(tmp_path), research_summary_path=summary))
        .get("/api/v1/research/experiments")
        .json()
    )
    assert payload["evidence_stage"] == "DEVELOPMENT BACKTEST / CONTROLS"
    assert payload["experiments"][0]["classification"] == "NEGATIVE_CONTROL"


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
        and research["wp005_integrity"] == state.get("wp005_integrity")
        and research["exogenous_foundation"] == state.get("exogenous_foundation")
    )


def test_memory_inspection_is_read_only_and_counters_come_from_state(tmp_path):
    memory = {"version": "SEARCH_MEMORY_V1", "status": "VALIDATED", "families_tracked": 5}
    selected = {
        "name": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
        "primary_experiment_id": "EXP-ALG-009-ALIGNED",
        "terminal_classification": "INCONCLUSIVE",
    }
    path = fixture_state(tmp_path, search_memory=memory, selected_family=selected)
    client = TestClient(create_app(path))
    payload = client.get("/api/v1/research/status").json()
    assert payload["search_memory"] == memory and payload["selected_family"] == selected
    breakout = next(x for x in payload["family_budgets"] if x["family_id"] == "FAM-BREAKOUT")
    assert breakout["experiments_consumed"] == breakout["experiments_limit"] == 4
    assert breakout["trials_consumed"] == breakout["trials_limit"] == 15
    assert client.post("/api/v1/research/status", json={"champion": "APPROVED"}).status_code == 405
    assert client.post("/api/v1/analyze").status_code == 404


def test_all_experiments_have_explicit_evidence_windows():
    payload = TestClient(app).get("/api/v1/research/experiments").json()
    assert payload["label"] == "DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE"
    assert len(payload["experiments"]) == 19
    recovery = next(
        x for x in payload["experiments"] if x["experiment_id"].endswith("RECOVERY-CORE")
    )
    assert recovery["classification"] == "INCONCLUSIVE"
    assert recovery["evidence_window"].startswith("WP-006")
    assert all(item["evidence_window"] for item in payload["experiments"])
    flow = next(x for x in payload["experiments"] if x["experiment_id"].endswith("ORDERFLOW-CORE"))
    assert flow["classification"] == "REJECT_COST_DOMINATED"
    assert flow["evidence_window"].startswith("WP-007")
    adaptive = next(
        x for x in payload["experiments"] if x["experiment_id"] == "EXP-ML-016-EWLS-INTERNAL-MACRO"
    )
    assert adaptive["classification"] == "REJECT_COST_DOMINATED"
    assert adaptive["evidence_window"].startswith("WP-011")
    ablation = next(
        x for x in payload["experiments"] if x["experiment_id"] == "EXP-ML-017-EWLS-INTERNAL-ONLY"
    )
    assert ablation["classification"] == "INCONCLUSIVE"
    aligned = next(x for x in payload["experiments"] if x["experiment_id"] == "EXP-ALG-009-ALIGNED")
    assert aligned["classification"] == "INCONCLUSIVE" and aligned["trade_count"] == 125
