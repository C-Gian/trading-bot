"""Causal invariants for PAPER_EXECUTION_V2_CAUSAL_NEXT_MINUTE."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import pytest
from app.main import create_app
from app.product.analysis import analysis_identity
from app.product.market_feed import Kline, MarketFeedError
from app.product.paper_v2 import (
    CLOSED_STOP,
    ENTRY_TIMEOUT_OPPORTUNITIES,
    EVIDENCE_STAGE,
    INITIATION_MODE,
    INVALIDATED_ENTRY_UNAVAILABLE,
    INVALIDATED_INTENT_PERSISTENCE,
    OPEN,
    PAPER_EXECUTION_VERSION,
    PENDING_ENTRY,
    PaperTradeError,
    PaperTradeStore,
    create_from_analysis,
    update_lifecycle,
)
from fastapi.testclient import TestClient
from state_fixtures import preserved_mechanics

ROOT = Path(__file__).resolve().parents[2]
SIGNAL = datetime(2026, 9, 14, 10, tzinfo=UTC)
ANALYSIS_DONE = datetime(2026, 9, 14, 10, 23, 16, tzinfo=UTC)
PERSISTED = datetime(2026, 9, 14, 10, 23, 17, 500_000, tzinfo=UTC)
MINUTE_MS = 60_000


def _analysis(decision: str = "LONG") -> dict[str, Any]:
    result: dict[str, Any] = {
        "analysis_version": "PAPER_RESEARCH_ANALYSIS_V1",
        "classification": "EXPERIMENTAL PAPER RESEARCH — NOT AN APPROVED LIVE STRATEGY",
        "symbol": "BTCUSDT",
        "strategy_version": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
        "variant": "ALIGNED",
        "feature_version": "CONTINUATION_FEATURES_V2",
        "research_status": "PAPER_RESEARCH_CANDIDATE",
        "champion_status": "NONE",
        "analysis_time": ANALYSIS_DONE.isoformat().replace("+00:00", "Z"),
        "signal_time": SIGNAL.isoformat().replace("+00:00", "Z"),
        "data_status": "OK",
        "data_detail": "synthetic complete data",
        "decision": decision,
        "plan": None,
        "paper_trade_persisted": False,
        "real_money": False,
    }
    if decision == "LONG":
        result["reference_price"] = 50_000.0
        result["plan"] = {
            "direction": "LONG",
            "entry_rule": "STRICTLY_AFTER_DURABLE_INTENT_NEXT_1M_OPEN",
            "entry_semantics": "strictly future minute",
            "execution_model": "EXECUTION_MODEL_V2",
            "exit_policy": "FIXED_TARGET_OR_STOP_OR_24H",
            "reference_price": 50_000.0,
            "stop_price": 49_000.0,
            "target_price": 52_000.0,
            "stop_fraction": 0.02,
            "target_fraction": 0.04,
            "max_hold_minutes": 1440,
            "expiry_time": "2026-09-15T10:00:00Z",
            "leverage": False,
            "short": False,
            "order_placed": False,
        }
    result["analysis_id"] = analysis_identity(result)
    return result


def _store(tmp_path: Path) -> PaperTradeStore:
    return PaperTradeStore(tmp_path / "paper" / "PAPER_TRADES_V2.json")


def _create(
    tmp_path: Path, *, persisted: datetime = PERSISTED
) -> tuple[PaperTradeStore, dict[str, Any]]:
    store = _store(tmp_path)
    return store, create_from_analysis(_analysis(), store, clock=lambda: persisted)


def _minute(instant: datetime, opened: float = 51_000.0) -> Kline:
    return Kline(
        int(instant.timestamp() * 1000),
        opened + 100,
        opened - 100,
        opened,
        1.0,
        opened,
    )


def _feed(klines: list[Kline], calls: list[int] | None = None):
    def feed(interval: str, limit: int, *, now, client=None, start_ms=None):
        assert interval == "1m"
        if calls is not None:
            calls.append(int(start_ms))
        rows = [row for row in klines if start_ms is None or row.open_ms >= start_ms]
        return tuple(rows[:limit])

    return feed


def _reconcile_in_process(path: str, gate: Any, outcomes: Any) -> None:
    gate.wait()
    fill = datetime(2026, 9, 14, 10, 24, tzinfo=UTC)
    result = update_lifecycle(
        PaperTradeStore(Path(path)),
        now=fill + timedelta(minutes=1),
        feed=_feed([_minute(fill)]),
    )
    outcomes.put(result["updated"])


def test_persistence_at_102317_fills_no_earlier_than_1024(tmp_path: Path) -> None:
    store, intent = _create(tmp_path)
    assert intent["entry_not_before"] == "2026-09-14T10:24:00Z"
    assert intent["entry_price"] is intent["stop_price"] is intent["target_price"] is None
    update_lifecycle(
        store,
        now=datetime(2026, 9, 14, 10, 25, tzinfo=UTC),
        feed=_feed([_minute(datetime(2026, 9, 14, 10, 24, tzinfo=UTC))]),
    )
    assert store.load()[0]["entry_time"] == "2026-09-14T10:24:00Z"


def test_intent_is_durable_and_unarmed_before_persistence_clock_is_taken(tmp_path: Path) -> None:
    store = _store(tmp_path)
    calls = 0

    def after_first_commit() -> datetime:
        nonlocal calls
        calls += 1
        if calls == 1:
            return PERSISTED - timedelta(milliseconds=1)
        durable = store.load()[0]
        assert durable["status"] == "PERSISTING_INTENT"
        assert durable["intent_persisted_at"] is None
        assert durable["entry_price"] is durable["stop_price"] is durable["target_price"] is None
        return PERSISTED

    armed = create_from_analysis(_analysis(), store, clock=after_first_commit)
    assert armed["status"] == PENDING_ENTRY
    assert armed["analysis_completed_at"] == "2026-09-14T10:23:17.499000Z"


def test_interrupted_second_commit_can_only_invalidate_the_unarmed_intent(
    tmp_path: Path,
) -> None:
    class InterruptedStore(PaperTradeStore):
        saves = 0

        def save(self, trades: list[dict[str, Any]]) -> None:
            self.saves += 1
            if self.saves == 2:
                raise OSError("synthetic interruption")
            super().save(trades)

    store = InterruptedStore(tmp_path / "paper" / "PAPER_TRADES_V2.json")
    with pytest.raises(OSError, match="synthetic interruption"):
        create_from_analysis(_analysis(), store, clock=lambda: PERSISTED)
    unarmed = store.load()[0]
    assert unarmed["status"] == "PERSISTING_INTENT" and unarmed["entry_price"] is None

    restarted = PaperTradeStore(store.path)
    update_lifecycle(restarted, now=PERSISTED + timedelta(minutes=10), feed=_feed([]))
    recovered = restarted.load()[0]
    assert recovered["status"] == INVALIDATED_INTENT_PERSISTENCE
    assert recovered["entry_price"] is None


def test_exact_boundary_forbids_that_boundary_and_uses_next_minute(tmp_path: Path) -> None:
    boundary = datetime(2026, 9, 14, 10, 24, tzinfo=UTC)
    store, intent = _create(tmp_path, persisted=boundary)
    assert intent["entry_not_before"] == "2026-09-14T10:25:00Z"
    update_lifecycle(
        store,
        now=datetime(2026, 9, 14, 10, 26, tzinfo=UTC),
        feed=_feed([_minute(boundary), _minute(boundary + timedelta(minutes=1))]),
    )
    assert store.load()[0]["entry_time"] == "2026-09-14T10:25:00Z"


def test_unavailable_not_yet_completed_entry_bar_remains_pending(tmp_path: Path) -> None:
    store, _ = _create(tmp_path)
    calls: list[int] = []
    result = update_lifecycle(
        store,
        now=datetime(2026, 9, 14, 10, 24, 59, tzinfo=UTC),
        feed=_feed([], calls),
    )
    assert result["updated"] == 0 and calls == []
    assert store.load()[0]["status"] == PENDING_ENTRY


def test_missed_earlier_minute_cannot_appear_later_and_retroactively_fill(tmp_path: Path) -> None:
    store, _ = _create(tmp_path)
    first = datetime(2026, 9, 14, 10, 24, tzinfo=UTC)
    update_lifecycle(store, now=first + timedelta(minutes=1), feed=_feed([]))
    assert store.load()[0]["entry_search_cursor"] == "2026-09-14T10:25:00Z"
    update_lifecycle(
        store,
        now=first + timedelta(minutes=2),
        feed=_feed([_minute(first), _minute(first + timedelta(minutes=1), 51_500)]),
    )
    trade = store.load()[0]
    assert trade["entry_time"] == "2026-09-14T10:25:00Z"
    assert trade["entry_price"] == 51_500.0


def test_backend_restart_preserves_the_causal_lower_bound(tmp_path: Path) -> None:
    first_store, intent = _create(tmp_path)
    restarted = PaperTradeStore(first_store.path)
    update_lifecycle(
        restarted,
        now=datetime(2026, 9, 14, 10, 25, tzinfo=UTC),
        feed=_feed([_minute(datetime(2026, 9, 14, 10, 24, tzinfo=UTC))]),
    )
    trade = restarted.load()[0]
    assert trade["intent_persisted_at"] == intent["intent_persisted_at"]
    assert trade["entry_time"] > trade["intent_persisted_at"]


def test_duplicated_reconciliation_is_idempotent(tmp_path: Path) -> None:
    store, _ = _create(tmp_path)
    now = datetime(2026, 9, 14, 10, 25, tzinfo=UTC)
    feed = _feed([_minute(datetime(2026, 9, 14, 10, 24, tzinfo=UTC))])
    assert update_lifecycle(store, now=now, feed=feed)["updated"] == 1
    after = store.path.read_bytes()
    assert update_lifecycle(store, now=now, feed=feed)["updated"] == 0
    assert store.path.read_bytes() == after


def test_concurrent_reconciliation_cannot_double_fill(tmp_path: Path) -> None:
    store, _ = _create(tmp_path)
    second_instance = PaperTradeStore(store.path)
    now = datetime(2026, 9, 14, 10, 25, tzinfo=UTC)
    feed = _feed([_minute(datetime(2026, 9, 14, 10, 24, tzinfo=UTC))])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda item: update_lifecycle(
                    store if item == 0 else second_instance, now=now, feed=feed
                ),
                range(2),
            )
        )
    assert sorted(result["updated"] for result in results) == [0, 1]
    assert len(store.load()) == 1 and store.load()[0]["status"] == OPEN


def test_concurrent_backend_processes_cannot_double_fill(tmp_path: Path) -> None:
    store, _ = _create(tmp_path)
    context = get_context("spawn")
    gate = context.Event()
    outcomes = context.Queue()
    processes = [
        context.Process(
            target=_reconcile_in_process,
            args=(str(store.path), gate, outcomes),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    gate.set()
    for process in processes:
        process.join(timeout=15)
        assert process.exitcode == 0
    assert sorted(outcomes.get(timeout=2) for _ in processes) == [0, 1]
    assert len(store.load()) == 1 and store.load()[0]["status"] == OPEN


def test_client_body_cannot_forge_server_owned_plan_or_timestamps(tmp_path: Path) -> None:
    store = _store(tmp_path)
    server_analysis = _analysis()
    server_analysis["analysis_time"] = "2026-09-13T10:23:16Z"
    server_analysis["signal_time"] = "2026-09-13T10:00:00Z"
    server_analysis["analysis_id"] = analysis_identity(server_analysis)
    app = create_app(**preserved_mechanics(), analyser=lambda: server_analysis, paper_store=store)
    response = TestClient(app).post(
        "/api/v1/product/paper-trades",
        json={
            "decision": "LONG",
            "entry_price": 1,
            "stop_price": 0,
            "target_price": 999_999,
            "intent_persisted_at": "2000-01-01T00:00:00Z",
            "strategy_version": "FORGED",
        },
    )
    assert response.status_code == 422
    assert store.load() == []

    accepted = TestClient(app).post("/api/v1/product/paper-trades")
    assert accepted.status_code == 200
    trade = accepted.json()["trade"]
    assert trade["strategy_version"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    assert trade["entry_price"] is trade["stop_price"] is trade["target_price"] is None


def test_actual_fill_anchors_stop_target_and_expiry(tmp_path: Path) -> None:
    store, _ = _create(tmp_path)
    fill = datetime(2026, 9, 14, 10, 24, tzinfo=UTC)
    update_lifecycle(store, now=fill + timedelta(minutes=1), feed=_feed([_minute(fill, 51_000)]))
    trade = store.load()[0]
    assert trade["entry_price"] == 51_000.0
    assert trade["stop_price"] == 49_980.0
    assert trade["target_price"] == 53_040.0
    assert trade["expiry_time"] == "2026-09-15T10:24:00Z"


def test_tampered_causal_metadata_fails_closed(tmp_path: Path) -> None:
    store, _ = _create(tmp_path)
    document = json.loads(store.path.read_text(encoding="utf-8"))
    document["trades"][0]["entry_not_before"] = "2026-09-14T10:23:00Z"
    store.path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PaperTradeError, match="causal lower bound"):
        store.load()


@pytest.mark.parametrize(
    "forged_entry",
    (
        "2026-09-14T10:23:00Z",
        "2026-09-14T10:24:30Z",
    ),
)
def test_store_rejects_preintent_or_noncanonical_fill(tmp_path: Path, forged_entry: str) -> None:
    store, _ = _create(tmp_path)
    fill = datetime(2026, 9, 14, 10, 24, tzinfo=UTC)
    update_lifecycle(store, now=fill + timedelta(minutes=1), feed=_feed([_minute(fill)]))
    document = json.loads(store.path.read_text(encoding="utf-8"))
    trade = document["trades"][0]
    trade["entry_time"] = forged_entry
    trade["entry_minute"] = forged_entry
    trade["entry_observation"]["open_time"] = forged_entry
    forged_instant = datetime.fromisoformat(forged_entry)
    trade["expiry_time"] = (
        (forged_instant + timedelta(minutes=1440)).isoformat().replace("+00:00", "Z")
    )
    store.path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PaperTradeError, match="causal lower bound"):
        store.load()


def test_five_completed_missing_opportunities_invalidate_without_a_fill(tmp_path: Path) -> None:
    store, _ = _create(tmp_path)
    update_lifecycle(
        store,
        now=datetime(2026, 9, 14, 10, 29, tzinfo=UTC),
        feed=_feed([]),
    )
    trade = store.load()[0]
    assert ENTRY_TIMEOUT_OPPORTUNITIES == 5
    assert trade["status"] == INVALIDATED_ENTRY_UNAVAILABLE
    assert trade["entry_price"] is None


def test_no_trade_creates_no_file(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(PaperTradeError, match="NO_TRADE"):
        create_from_analysis(_analysis("NO_TRADE"), store, clock=lambda: PERSISTED)
    assert store.load() == [] and not store.path.exists()


def test_terminal_record_is_immutable(tmp_path: Path) -> None:
    store, _ = _create(tmp_path)
    fill = datetime(2026, 9, 14, 10, 24, tzinfo=UTC)
    stopped = Kline(int(fill.timestamp() * 1000), 51_100, 49_000, 49_500, 1.0, 51_000)
    update_lifecycle(store, now=fill + timedelta(minutes=1), feed=_feed([stopped]))
    assert store.load()[0]["status"] == CLOSED_STOP
    before = store.path.read_bytes()
    update_lifecycle(store, now=fill + timedelta(days=2), feed=_feed([]))
    assert store.path.read_bytes() == before


def test_temporary_market_failure_keeps_pending_cursor_unchanged(tmp_path: Path) -> None:
    store, before = _create(tmp_path)

    def unavailable(*args, **kwargs):
        raise MarketFeedError("temporary failure")

    result = update_lifecycle(
        store,
        now=datetime(2026, 9, 14, 10, 25, tzinfo=UTC),
        feed=unavailable,
    )
    assert result["updated"] == 0 and result["errors"]
    assert store.load()[0] == before


def test_fill_is_durable_even_if_followup_position_fetch_fails(tmp_path: Path) -> None:
    store, _ = _create(tmp_path)
    fill = datetime(2026, 9, 14, 10, 24, tzinfo=UTC)
    calls = 0

    def fails_after_fill(interval: str, limit: int, *, now, client=None, start_ms=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            return (_minute(fill),)
        raise MarketFeedError("position history temporarily unavailable")

    result = update_lifecycle(
        store,
        now=fill + timedelta(minutes=1),
        feed=fails_after_fill,
    )
    trade = store.load()[0]
    assert result["errors"] and trade["status"] == OPEN
    assert trade["entry_time"] == "2026-09-14T10:24:00Z"
    assert trade["entry_price"] == 51_000.0


def test_manual_classification_and_counter_discipline_persist(tmp_path: Path) -> None:
    _, trade = _create(tmp_path)
    assert trade["evidence_stage"] == EVIDENCE_STAGE == "MANUAL_PROSPECTIVE_PAPER"
    assert trade["initiation_mode"] == INITIATION_MODE == "OWNER_MANUAL"
    assert trade["execution_model_version"] == PAPER_EXECUTION_VERSION
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert state["experiments_completed"] == 26
    assert state["paper_trades_completed"] == 0
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0


def test_v2_has_no_real_money_order_or_credential_path(tmp_path: Path) -> None:
    app = create_app(**preserved_mechanics(), analyser=_analysis, paper_store=_store(tmp_path))
    paths = {str(getattr(route, "path", "")).lower() for route in app.routes}
    assert not any(
        word in path
        for path in paths
        for word in ("order", "account", "balance", "credential", "withdraw", "live")
    )
    sources = "".join(
        (ROOT / relative).read_text(encoding="utf-8").lower()
        for relative in (
            "backend/app/product/paper_v2.py",
            "backend/app/product/execution_v2.py",
        )
    )
    for forbidden in ("api_key", "apikey", "secret", "hmac", "withdraw", "margin"):
        assert forbidden not in sources
