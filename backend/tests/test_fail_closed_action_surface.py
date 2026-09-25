"""System G1 Checkpoint 1 Stage 0: the action surface fails closed on `validated_strategy`.

The guard no longer depends on the ADR-0042 PARKED disposition value. While
`current_project_status.validated_strategy` is null, no historical strategy (ALIGNED or any
predictive family) is evaluated, the output is NO_TRADE, paper trades are refused and the legacy
research runner cannot start — whatever the strategic disposition says.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from app.main import (
    FAIL_CLOSED_DATA_STATUS,
    FAIL_CLOSED_RESEARCH_STATUS,
    PARKED_DISPOSITION,
    create_app,
    fail_closed,
    legacy_runner_authorized,
)
from fastapi.testclient import TestClient
from state_fixtures import FIXTURE_STRATEGY, fixture_schema_path, unparked_state_path

ROOT = Path(__file__).resolve().parents[2]
STATE = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
G1_DISPOSITION = (
    "PROFESSIONAL_MULTISIGNAL_PAPER_SYSTEM_DEVELOPMENT_ARCHITECTURE_ADOPTED_PROTOCOLS_PENDING"
)
DISPOSITIONS = (PARKED_DISPOSITION, "ACTIVE_ALLOCATION", G1_DISPOSITION)


def _never() -> dict:
    raise AssertionError("the historical strategy analyser must not run without validation")


def _state_with(tmp_path: Path, disposition: str) -> Path:
    state = copy.deepcopy(STATE)
    state["current_project_status"]["disposition"] = disposition
    path = tmp_path / f"state-{disposition}.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


def test_live_state_has_no_validated_strategy_and_g1_disposition() -> None:
    current = STATE["current_project_status"]
    assert fail_closed(STATE) and current["validated_strategy"] is None
    assert current["disposition"] == current["strategic_disposition"] == G1_DISPOSITION
    assert "operational_compatibility_note" not in current
    assert current["operational_action_output"] == "NO_TRADE"
    assert current["active_candidate"] is None and current["candidate_2"] == "UNALLOCATED"
    assert current["market_trial_authorized"] is current["confirmation_authorized"] is False
    assert current["prospective_collection_authorized"] is False
    assert current["active_system_generation"] == "SYSTEM_G1"
    assert current["active_project_internal_alpha_schedules"] == []
    assert not legacy_runner_authorized(STATE)
    assert {"selected_family", "product_analysis", "project_phase"} <= set(
        current["historical_top_level_fields"]
    )


@pytest.mark.parametrize("disposition", DISPOSITIONS)
def test_every_disposition_without_validation_fails_closed(tmp_path, disposition) -> None:
    client = TestClient(create_app(_state_with(tmp_path, disposition), analyser=_never))
    body = client.post("/api/v1/product/analysis").json()
    assert body["decision"] == "NO_TRADE" and body["plan"] is None
    assert body["data_status"] == FAIL_CLOSED_DATA_STATUS
    assert body["research_status"] == FAIL_CLOSED_RESEARCH_STATUS
    assert body["strategy_version"] == "NONE" and body["variant"] == "NONE"
    assert body["champion_status"] == "NONE" and body["real_money"] is False
    capability = client.get("/api/v1/product/analysis/capability").json()
    assert capability["surface"] == "FAIL_CLOSED_NO_TRADE"
    assert capability["paper_trade_persistence"] is False
    assert client.post("/api/v1/product/paper-trades").status_code == 409
    run = client.post(
        "/api/v1/research/runner/runs", json={"candidate_id": "WP015_REPRODUCTION_V1"}
    )
    assert run.status_code == 409


def test_live_app_never_calls_the_old_analyser() -> None:
    client = TestClient(create_app(analyser=_never))
    assert client.post("/api/v1/product/analysis").json()["decision"] == "NO_TRADE"
    assert client.post("/api/v1/product/paper-trades").status_code == 409


def test_missing_status_block_is_never_treated_as_validated() -> None:
    assert fail_closed({}) and fail_closed({"current_project_status": {}})
    assert not legacy_runner_authorized({"current_project_status": {"validated_strategy": "X"}})


def test_canonical_schema_rejects_a_validated_strategy(tmp_path) -> None:
    state = copy.deepcopy(STATE)
    state["current_project_status"]["validated_strategy"] = "ALIGNED"
    path = tmp_path / "state.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    client = TestClient(create_app(path, analyser=_never), raise_server_exceptions=False)
    assert client.post("/api/v1/product/analysis").status_code == 500


def test_explicit_fixture_validation_keeps_preserved_mechanics_reachable() -> None:
    state = json.loads(unparked_state_path().read_text(encoding="utf-8"))
    assert not fail_closed(state) and legacy_runner_authorized(state)
    assert state["current_project_status"]["validated_strategy"] == FIXTURE_STRATEGY
    calls: list[int] = []

    def analyser() -> dict:
        calls.append(1)
        return {"decision": "NO_TRADE", "plan": None, "analysis_id": "fixture"}

    client = TestClient(
        create_app(
            state_path=unparked_state_path(),
            state_schema_path=fixture_schema_path(),
            analyser=analyser,
        )
    )
    client.post("/api/v1/product/analysis")
    assert calls == [1]
