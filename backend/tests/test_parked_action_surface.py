"""ADR-0042: while alpha research is parked, every action surface fails closed to NO_TRADE."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import PARKED_DISPOSITION, create_app, parked
from fastapi.testclient import TestClient
from state_fixtures import unparked_state_path

ROOT = Path(__file__).resolve().parents[2]
STATE = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))


def _never() -> dict:
    raise AssertionError("the strategy analyser must not run while parked")


def test_live_state_is_parked_with_explicit_precedence() -> None:
    current = STATE["current_project_status"]
    assert parked(STATE) and current["disposition"] == PARKED_DISPOSITION
    assert current["operational_action_output"] == "NO_TRADE"
    assert current["active_alpha_allocation"] == 0 and current["active_candidate"] is None
    assert current["candidate_2"] == "UNALLOCATED"
    assert current["market_trial_authorized"] is current["confirmation_authorized"] is False
    assert current["automatic_next_research_package"] is None
    assert current["active_project_internal_alpha_schedules"] == []
    assert {"selected_family", "product_analysis", "project_phase"} <= set(
        current["historical_top_level_fields"]
    )


def test_parked_analysis_is_no_trade_without_evaluating_a_strategy() -> None:
    client = TestClient(create_app(analyser=_never))
    body = client.post("/api/v1/product/analysis").json()
    assert body["decision"] == "NO_TRADE" and body["plan"] is None
    assert body["data_status"] == "RESEARCH_PARKED"
    assert body["research_status"] == "PARKED_NO_VALIDATED_STRATEGY"
    assert body["champion_status"] == "NONE" and body["real_money"] is False
    capability = client.get("/api/v1/product/analysis/capability").json()
    assert capability["surface"] == "PARKED_NO_TRADE"
    assert capability["paper_trade_persistence"] is False


def test_parked_state_refuses_paper_trades_and_research_runs() -> None:
    client = TestClient(create_app(analyser=_never))
    assert client.post("/api/v1/product/paper-trades").status_code == 409
    response = client.post(
        "/api/v1/research/runner/runs", json={"candidate_id": "WP015_REPRODUCTION_V1"}
    )
    assert response.status_code == 409


def test_unparked_copy_keeps_the_preserved_mechanics_reachable() -> None:
    state = json.loads(unparked_state_path().read_text(encoding="utf-8"))
    assert not parked(state)
