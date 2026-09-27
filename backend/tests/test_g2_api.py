"""G2-01 product/API acceptance: causal cursor, completed review, parity with the core."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app.g2 import runs
from app.g2.records import ClosedTrade, Decision, SimulatedFill
from app.g2.store import plain
from app.main import create_app
from fastapi.testclient import TestClient
from g2_support import full_run, shared_service

KEY = runs.synthetic_spec().key


@pytest.fixture(scope="module")
def client():
    full_run()  # computed once for the whole test session
    return TestClient(create_app(g2_service=shared_service()))


def parse(text: str) -> datetime:
    return datetime.fromisoformat(text)


def test_status_and_registered_runs_are_labelled_not_performance_evidence(client):
    status = client.get("/api/v1/g2/status").json()
    assert status["operational_action"] == "NO_TRADE" and status["validated_strategy"] is None
    assert status["cycle_runtime_role"] == "SHADOW_ONLY"
    assert status["evidence"] == "ENGINEERING_ONLY_NOT_PERFORMANCE_EVIDENCE"
    (run,) = [r for r in client.get("/api/v1/g2/runs").json()["runs"] if r["run_key"] == KEY]
    assert run["evidence_label"] == "NOT PERFORMANCE EVIDENCE"
    assert run["evidence_class"] == runs.SYNTHETIC
    assert client.get("/api/v1/g1/status").status_code == 200  # the existing app stays usable


def test_causal_cursor_never_exposes_future_records(client):
    service = shared_service()
    view = client.post("/api/v1/g2/replay/sessions", json={"run_key": KEY}).json()
    session_id = view["session_id"]
    assert view["mode"] == "CAUSAL_CURSOR" and view["label"] == "NOT PERFORMANCE EVIDENCE"
    trade = full_run().core.store.of_type(ClosedTrade)[0]
    cursor = trade.entry_time + timedelta(hours=1)  # inside the holding period
    service._move(service.sessions[session_id], cursor)
    view = client.get(f"/api/v1/g2/replay/sessions/{session_id}").json()
    assert parse(view["cursor"]) == cursor
    for candle in view["candles"]:
        assert parse(candle["available_at"]) <= cursor
    for marker in view["prediction_markers"] + view["decision_markers"]:
        assert parse(marker["decision_time"]) <= cursor
    for fill in view["fills"]:
        assert parse(fill["available_at"]) <= cursor
    assert all(parse(t["available_at"]) <= cursor for t in view["closed_trades"])
    assert view["current"]["open_position"]["trade_id"] == trade.trade_id
    assert not any(f["kind"] == "EXIT" and f["trade_id"] == trade.trade_id for f in view["fills"])
    lineage = client.get(
        f"/api/v1/g2/replay/sessions/{session_id}/lineage/{trade.decision_id}"
    ).json()
    assert [f["kind"] for f in lineage["fills"]] == ["ENTRY"]
    assert lineage["closed_trade"] == [] and lineage["stop_expiry"] == []
    assert lineage["prediction_outcome"] is None and lineage["shadow_labels"] == []
    future = next(d for d in full_run().core.store.of_type(Decision) if d.decision_time > cursor)
    assert (
        client.get(
            f"/api/v1/g2/replay/sessions/{session_id}/lineage/{future.decision_id}"
        ).status_code
        == 404
    )


def test_api_output_matches_the_authoritative_core(client):
    service = shared_service()
    session_id = client.post("/api/v1/g2/replay/sessions", json={"run_key": KEY}).json()[
        "session_id"
    ]
    store = full_run().core.store
    decision = next(d for d in store.of_type(Decision) if str(d.action) != "NO_TRADE")
    service._move(service.sessions[session_id], decision.decision_time)
    view = client.get(f"/api/v1/g2/replay/sessions/{session_id}").json()
    assert view["current"]["decision"] == plain(decision)
    assert view["current"]["prediction"] == plain(store.get(decision.prediction_id))
    assert view["current"]["decision"]["action"] in ("LONG", "SHORT")


def test_replay_controls_and_completed_review_gate(client):
    fresh_service = type(shared_service())(include_engineering_window=False)
    fresh_service._computed = shared_service()._computed  # reuse the computed immutable run
    local = TestClient(create_app(g2_service=fresh_service))
    view = local.post("/api/v1/g2/replay/sessions", json={"run_key": KEY}).json()
    session_id = view["session_id"]
    assert local.get(f"/api/v1/g2/runs/{KEY}/review").status_code == 409
    stepped = local.post(
        f"/api/v1/g2/replay/sessions/{session_id}/control", json={"action": "step", "unit": "1h"}
    ).json()
    assert parse(stepped["cursor"]) - parse(view["cursor"]) == timedelta(hours=1)
    assert stepped["status"] == "PAUSED"
    assert (
        local.post(
            f"/api/v1/g2/replay/sessions/{session_id}/control", json={"action": "speed", "speed": 7}
        ).status_code
        == 409
    )
    local.post(
        f"/api/v1/g2/replay/sessions/{session_id}/control", json={"action": "speed", "speed": 86400}
    )
    local.post(f"/api/v1/g2/replay/sessions/{session_id}/control", json={"action": "start"})
    ticked = local.post(
        f"/api/v1/g2/replay/sessions/{session_id}/tick", json={"wall_seconds": 1}
    ).json()
    assert parse(ticked["cursor"]) - parse(stepped["cursor"]) == timedelta(days=1)
    fresh_service._move(fresh_service.sessions[session_id], parse(ticked["dataset_end"]))
    review = local.get(f"/api/v1/g2/runs/{KEY}/review").json()
    assert review["mode"] == "COMPLETED_RUN_REVIEW"
    assert review["fingerprint"] == full_run().core.store.fingerprint()
    assert review["economic_summary"] == "NOT_COMPUTED_G2_01_ENGINEERING_ONLY"
    assert review["record_counts"]["Decision"] == len(full_run().core.store.of_type(Decision))


def test_full_lineage_reconstruction_after_completion(client):
    service = shared_service()
    session_id = client.post("/api/v1/g2/replay/sessions", json={"run_key": KEY}).json()[
        "session_id"
    ]
    service._move(service.sessions[session_id], full_run().built.manifest.dataset_end)
    trade = full_run().core.store.of_type(ClosedTrade)[0]
    lineage = client.get(
        f"/api/v1/g2/replay/sessions/{session_id}/lineage/{trade.decision_id}"
    ).json()
    assert lineage["decision"]["decision_id"] == trade.decision_id
    assert lineage["prediction"]["decision_id"] == trade.decision_id
    assert lineage["state"]["state_id"] == lineage["prediction"]["state_id"]
    assert lineage["cycle"]["runtime_role"] == "SHADOW_ONLY"
    assert lineage["prediction_outcome"]["prediction_id"] == lineage["prediction"]["prediction_id"]
    assert sorted(label["side"] for label in lineage["shadow_labels"]) == ["LONG", "SHORT"]
    assert [i["decision_id"] for i in lineage["order_intents"]] == [trade.decision_id]
    assert [f["kind"] for f in lineage["fills"]] == ["ENTRY", "EXIT"]
    assert (
        len(lineage["stop_expiry"]) == 1
        and lineage["closed_trade"][0]["trade_id"] == trade.trade_id
    )
    fills = [
        f for f in full_run().core.store.of_type(SimulatedFill) if f.trade_id == trade.trade_id
    ]
    assert [plain(f) for f in fills] == lineage["fills"]


def test_latest_state_surface_for_home(client):
    latest = client.get(f"/api/v1/g2/runs/{KEY}/latest").json()
    assert (
        latest["label"] == "NOT PERFORMANCE EVIDENCE" and latest["production_action"] == "NO_TRADE"
    )
    assert (
        latest["current"]["decision"]["decision_id"]
        == plain(full_run().core.store.of_type(Decision)[-1])["decision_id"]
    )
    assert latest["current"]["cycle"]["runtime_role"] == "SHADOW_ONLY"
