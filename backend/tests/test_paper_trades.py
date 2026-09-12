"""WP-010B1: paper-trade persistence and lifecycle over the frozen execution model."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.main import create_app
from app.product.market_feed import Kline, MarketFeedError
from app.product.paper import (
    ACTIVE_STATUSES,
    CLOSED_EXPIRY,
    CLOSED_STOP,
    CLOSED_TARGET,
    ENTRY_EXECUTION,
    INVALIDATED,
    OPEN,
    PENDING_ENTRY,
    STATUSES,
    PaperTradeError,
    PaperTradeStore,
    create_from_analysis,
    listing,
    update_lifecycle,
)
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SIGNAL = datetime(2026, 3, 5, 12, tzinfo=UTC)
NOW = datetime(2026, 3, 6, 13, tzinfo=UTC)
SIGNAL_MS = int(SIGNAL.timestamp() * 1000)
MINUTE_MS = 60_000
REFERENCE = 50_000.0
STOP = REFERENCE * 0.98
TARGET = REFERENCE * 1.04


def _analysis(decision: str = "LONG", *, analysis_id: str = "a" * 64) -> dict:
    result = {
        "analysis_version": "PAPER_RESEARCH_ANALYSIS_V1",
        "classification": "EXPERIMENTAL PAPER RESEARCH — NOT AN APPROVED LIVE STRATEGY",
        "symbol": "BTCUSDT",
        "strategy_version": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
        "variant": "ALIGNED",
        "feature_version": "CONTINUATION_FEATURES_V2",
        "research_status": "PAPER_RESEARCH_CANDIDATE",
        "champion_status": "NONE",
        "analysis_time": "2026-03-05T12:30:00Z",
        "signal_time": "2026-03-05T12:00:00Z",
        "data_status": "OK",
        "data_detail": "completed contiguous lookback available",
        "decision": decision,
        "plan": None,
        "analysis_id": analysis_id,
        "paper_trade_persisted": False,
        "real_money": False,
    }
    if decision == "LONG":
        result["reference_price"] = REFERENCE
        result["plan"] = {
            "direction": "LONG",
            "entry_rule": "NEXT_1M_OPEN",
            "entry_semantics": "next completed 1m open",
            "execution_model": "EXECUTION_MODEL_V2",
            "exit_policy": "FIXED_TARGET_OR_STOP_OR_24H",
            "reference_price": REFERENCE,
            "stop_price": STOP,
            "target_price": TARGET,
            "stop_fraction": 0.02,
            "target_fraction": 0.04,
            "max_hold_minutes": 1440,
            "expiry_time": "2026-03-06T12:00:00Z",
            "leverage": False,
            "short": False,
            "order_placed": False,
        }
    return result


def _minute(index: int, *, high: float, low: float, close: float, opened: float) -> Kline:
    return Kline(SIGNAL_MS + index * MINUTE_MS, high, low, close, 1.0, opened)


def _flat(count: int) -> list[Kline]:
    return [_minute(i, high=50_100, low=49_900, close=50_000, opened=50_000) for i in range(count)]


def _feed(klines: list[Kline]):
    """Stands in for the public 1m endpoint; returns only what it is given."""

    def feed(interval: str, limit: int, *, now, client=None, start_ms=None):
        assert interval == "1m"
        rows = [k for k in klines if start_ms is None or k.open_ms >= start_ms]
        return tuple(rows[:limit])

    return feed


def _store(tmp_path: Path) -> PaperTradeStore:
    return PaperTradeStore(tmp_path / "paper" / "PAPER_TRADES_V1.json")


def _created(tmp_path: Path) -> tuple[PaperTradeStore, dict]:
    store = _store(tmp_path)
    return store, create_from_analysis(_analysis(), store)


# --- creation --------------------------------------------------------------------


def test_no_trade_analysis_creates_nothing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(PaperTradeError, match="NO_TRADE"):
        create_from_analysis(_analysis("NO_TRADE"), store)
    assert store.load() == []
    assert not store.path.exists()


def test_long_analysis_creates_one_pending_trade(tmp_path: Path) -> None:
    store, trade = _created(tmp_path)
    assert trade["status"] == PENDING_ENTRY
    assert trade["direction"] == "LONG"
    assert trade["symbol"] == "BTCUSDT"
    assert trade["strategy_version"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    assert trade["research_status"] == "PAPER_RESEARCH_CANDIDATE"
    assert trade["champion_status"] == "NONE"
    assert trade["entry_execution"] == ENTRY_EXECUTION == "NEXT_1M_OPEN_EXECUTION"
    assert trade["ambiguous_fill_policy"] == "STOP_FIRST_V1"
    assert (trade["stop_price"], trade["target_price"]) == (STOP, TARGET)
    assert trade["max_hold_minutes"] == 1440
    assert trade["entry_time"] is None and trade["exit_time"] is None
    assert trade["real_money"] is False and trade["order_placed"] is False
    assert len(store.load()) == 1
    document = json.loads(store.path.read_text(encoding="utf-8"))
    assert document["version"] == "FUTURE_PAPER_EVIDENCE_V1"
    assert document["real_money"] is False


def test_incomplete_analysis_cannot_create_a_trade(tmp_path: Path) -> None:
    store = _store(tmp_path)
    analysis = _analysis()
    analysis["data_status"] = "INCOMPLETE_MARKET_DATA"
    with pytest.raises(PaperTradeError, match="sound market data"):
        create_from_analysis(analysis, store)
    assert store.load() == []


def test_the_same_analysis_cannot_create_two_trades(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    with pytest.raises(PaperTradeError, match="already exists for this analysis"):
        create_from_analysis(_analysis(), store)
    assert len(store.load()) == 1


def test_a_second_analysis_is_blocked_while_one_trade_is_active(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    with pytest.raises(PaperTradeError, match="already PENDING_ENTRY or OPEN"):
        create_from_analysis(_analysis(analysis_id="b" * 64), store)
    assert len(store.load()) == 1


def test_a_new_trade_is_allowed_once_the_previous_one_closed(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    update_lifecycle(store, now=NOW, feed=_feed(_flat(1441)))
    assert store.load()[0]["status"] == CLOSED_EXPIRY
    second = create_from_analysis(_analysis(analysis_id="b" * 64), store)
    assert second["status"] == PENDING_ENTRY
    assert len(store.load()) == 2


# --- lifecycle -------------------------------------------------------------------


def test_entry_uses_the_next_1m_open_after_the_signal_hour(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    klines = _flat(10)
    klines[0] = _minute(0, high=50_100, low=49_900, close=50_050, opened=49_950)
    update_lifecycle(store, now=SIGNAL + timedelta(minutes=10), feed=_feed(klines))
    trade = store.load()[0]
    assert trade["status"] == OPEN
    assert trade["entry_time"] == "2026-03-05T12:00:00Z"
    assert trade["entry_price"] == 49_950.0


def test_target_touch_closes_at_the_target(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    klines = _flat(10)
    klines[3] = _minute(3, high=TARGET + 500, low=49_900, close=TARGET, opened=50_000)
    update_lifecycle(store, now=NOW, feed=_feed(klines))
    trade = store.load()[0]
    assert trade["status"] == CLOSED_TARGET
    assert trade["exit_price"] == TARGET
    assert trade["exit_time"] == "2026-03-05T12:03:00Z"
    assert trade["holding_minutes"] == 3
    assert trade["net_r"] is not None


def test_stop_touch_closes_at_the_stop(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    klines = _flat(10)
    klines[2] = _minute(2, high=50_100, low=STOP - 100, close=STOP, opened=50_000)
    update_lifecycle(store, now=NOW, feed=_feed(klines))
    trade = store.load()[0]
    assert trade["status"] == CLOSED_STOP
    assert trade["exit_price"] == STOP
    assert trade["net_r"] is not None and trade["net_r"] < 0


def test_expiry_closes_at_the_maximum_holding_horizon(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    update_lifecycle(store, now=NOW, feed=_feed(_flat(1441)))
    trade = store.load()[0]
    assert trade["status"] == CLOSED_EXPIRY
    assert trade["holding_minutes"] == 1440
    assert trade["exit_time"] == "2026-03-06T12:00:00Z"


def test_a_bar_touching_both_stop_and_target_resolves_stop_first(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    klines = _flat(10)
    klines[4] = _minute(4, high=TARGET + 10, low=STOP - 10, close=50_000, opened=50_000)
    update_lifecycle(store, now=NOW, feed=_feed(klines))
    trade = store.load()[0]
    assert trade["status"] == CLOSED_STOP
    assert trade["exit_price"] == STOP
    assert trade["ambiguous_fill_policy"] == "STOP_FIRST_V1"


def test_an_open_below_the_stop_exits_at_that_adverse_open(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    klines = _flat(10)
    klines[2] = _minute(2, high=49_500, low=48_000, close=48_500, opened=48_900)
    update_lifecycle(store, now=NOW, feed=_feed(klines))
    trade = store.load()[0]
    assert trade["status"] == CLOSED_STOP
    assert trade["exit_price"] == 48_900.0
    assert trade["exit_reason"] == "STOP_GAP"


# --- incomplete data never fabricates an outcome ---------------------------------


def test_a_gapped_minute_path_leaves_the_trade_open_without_an_outcome(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    klines = _flat(10)
    del klines[4]
    update_lifecycle(store, now=NOW, feed=_feed(klines))
    trade = store.load()[0]
    assert trade["status"] == OPEN
    assert trade["exit_time"] is None and trade["exit_price"] is None
    assert trade["net_r"] is None
    assert "UNRESOLVED_DATA_GAP" in trade["resolution_detail"]


def test_an_unfinished_path_leaves_the_trade_open(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    update_lifecycle(store, now=SIGNAL + timedelta(hours=2), feed=_feed(_flat(120)))
    trade = store.load()[0]
    assert trade["status"] == OPEN
    assert trade["exit_reason"] is None and trade["net_r"] is None


def test_a_pending_trade_stays_pending_before_its_entry_minute_closes(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    update_lifecycle(store, now=SIGNAL, feed=_feed([]))
    trade = store.load()[0]
    assert trade["status"] == PENDING_ENTRY
    assert trade["entry_time"] is None


def test_a_definitively_missing_entry_minute_invalidates(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    update_lifecycle(store, now=NOW, feed=_feed(_flat(10)[3:]))
    trade = store.load()[0]
    assert trade["status"] == INVALIDATED
    assert trade["exit_reason"] == "INVALID_MISSING_ENTRY_BAR"
    assert trade["net_r"] is None


def test_a_market_feed_failure_reports_an_error_and_changes_nothing(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)

    def failing(*_: object, **__: object):
        raise MarketFeedError("market feed transport failure: offline")

    before = store.load()
    result = update_lifecycle(store, now=NOW, feed=failing)
    assert result["errors"][0]["error"].startswith("market feed transport failure")
    assert result["updated"] == 0
    assert store.load() == before


# --- determinism and idempotency -------------------------------------------------


def test_lifecycle_update_is_deterministic_and_idempotent(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    klines = _flat(10)
    klines[3] = _minute(3, high=TARGET + 500, low=49_900, close=TARGET, opened=50_000)
    first = update_lifecycle(store, now=NOW, feed=_feed(klines))
    after_first = store.path.read_bytes()
    second = update_lifecycle(store, now=NOW, feed=_feed(klines))
    assert first["trades"][0] == store.load()[0]
    assert second["updated"] == 0
    assert store.path.read_bytes() == after_first


def test_a_terminal_trade_is_never_reopened_by_later_data(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    stop_path = _flat(10)
    stop_path[2] = _minute(2, high=50_100, low=STOP - 100, close=STOP, opened=50_000)
    update_lifecycle(store, now=NOW, feed=_feed(stop_path))
    closed = store.load()[0]
    assert closed["status"] == CLOSED_STOP
    target_path = _flat(10)
    target_path[3] = _minute(3, high=TARGET + 500, low=49_900, close=TARGET, opened=50_000)
    update_lifecycle(store, now=NOW, feed=_feed(target_path))
    assert store.load()[0] == closed


def test_statuses_are_exactly_the_declared_lifecycle() -> None:
    assert STATUSES == (
        "PENDING_ENTRY",
        "OPEN",
        "CLOSED_TARGET",
        "CLOSED_STOP",
        "CLOSED_EXPIRY",
        "INVALIDATED",
    )
    assert ACTIVE_STATUSES == ("PENDING_ENTRY", "OPEN")


# --- endpoints and safety --------------------------------------------------------


def _app(tmp_path: Path, decision: str = "LONG"):
    store = _store(tmp_path)
    klines = _flat(10)
    klines[3] = _minute(3, high=TARGET + 500, low=49_900, close=TARGET, opened=50_000)
    return store, create_app(
        analyser=lambda: _analysis(decision),
        paper_store=store,
        lifecycle=lambda s: update_lifecycle(s, now=NOW, feed=_feed(klines)),
    )


def test_endpoints_create_read_and_advance(tmp_path: Path) -> None:
    store, app = _app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/v1/product/paper-trades")
    assert created.status_code == 200
    assert created.json()["trade"]["status"] == PENDING_ENTRY

    read = client.get("/api/v1/product/paper-trades").json()
    assert read["evidence_version"] == "FUTURE_PAPER_EVIDENCE_V1"
    assert read["champion_status"] == "NONE"
    assert read["research_status"] == "PAPER_RESEARCH_CANDIDATE"
    assert len(read["active"]) == 1 and read["recorded"] == 1

    advanced = client.post("/api/v1/product/paper-trades/lifecycle").json()
    assert advanced["trades"][0]["status"] == CLOSED_TARGET
    assert client.get("/api/v1/product/paper-trades").json()["active"] == []
    assert store.load()[0]["status"] == CLOSED_TARGET


def test_endpoint_refuses_to_create_from_a_no_trade_analysis(tmp_path: Path) -> None:
    store, app = _app(tmp_path, "NO_TRADE")
    response = TestClient(app).post("/api/v1/product/paper-trades")
    assert response.status_code == 409
    assert "NO_TRADE" in response.json()["detail"]
    assert store.load() == []


def test_endpoint_blocks_duplicate_and_concurrent_creation(tmp_path: Path) -> None:
    store, app = _app(tmp_path)
    client = TestClient(app)
    assert client.post("/api/v1/product/paper-trades").status_code == 200
    second = client.post("/api/v1/product/paper-trades")
    assert second.status_code == 409
    assert len(store.load()) == 1


def test_nothing_advances_without_an_explicit_lifecycle_call(tmp_path: Path) -> None:
    store = _store(tmp_path)
    calls: list[int] = []
    app = create_app(
        analyser=lambda: _analysis(),
        paper_store=store,
        lifecycle=lambda s: (calls.append(1), update_lifecycle(s, now=NOW, feed=_feed(_flat(10))))[
            1
        ],
    )
    with TestClient(app) as client:
        assert calls == []
        client.post("/api/v1/product/paper-trades")
        client.get("/api/v1/product/paper-trades")
        client.get("/api/v1/system/health")
        assert calls == []
        assert store.load()[0]["status"] == PENDING_ENTRY
        client.post("/api/v1/product/paper-trades/lifecycle")
        assert calls == [1]


def test_no_order_balance_credential_or_real_money_surface(tmp_path: Path) -> None:
    _, app = _app(tmp_path)
    client = TestClient(app)
    paths = {route.path for route in app.routes}
    assert not [
        path
        for path in paths
        if any(
            word in path.lower()
            for word in ("order", "balance", "account", "key", "credential", "withdraw", "live")
        )
    ]
    for path in ("/api/v1/product/paper-trades/order", "/api/v1/account", "/api/v1/balance"):
        assert client.post(path).status_code == 404
    body = client.get("/api/v1/product/paper-trades").json()
    assert body["real_money"] is False


def test_the_paper_module_carries_no_credential_leverage_or_short_surface() -> None:
    source = (ROOT / "backend/app/product/paper.py").read_text(encoding="utf-8").lower()
    for forbidden in ("api_key", "apikey", "secret", "hmac", "withdraw", "margin", "leverage=true"):
        assert forbidden not in source
    assert '"short": False'.lower() in source
    assert '"leverage": False'.lower() in source


# --- scientific separation -------------------------------------------------------


def test_scientific_paper_trade_counter_is_untouched() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert state["paper_trades_completed"] == 0
    assert state["champion_status"] == "NONE"
    assert state["forward_evidence"] == "NONE"
    assert state["real_money_authorized"] is False
    assert state["experiments_completed"] == 17
    assert state["sealed_evaluations_completed"] == 0
    # WP-011 advanced the search burden; the paper counters below must still be zero.
    assert state["adaptive_search"]["adaptive_decisions"] == 7
    assert state["adaptive_search"]["profile_trials"] == 85
    assert state["adaptive_search"]["configuration_variants"] == 17


def test_state_declares_the_paper_surface_truthfully() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    paper = state["paper_trading"]
    assert paper["surface"] == "AVAILABLE"
    assert paper["persistence_version"] == "FUTURE_PAPER_EVIDENCE_V1"
    assert paper["prospective_execution_version"] == "PROSPECTIVE_PAPER_EXECUTION_V1"
    assert paper["prospective_features_version"] == "PROSPECTIVE_PAPER_FEATURES_V1"
    assert paper["feature_equivalence"] == paper["execution_equivalence"] == "PASS"
    assert paper["historical_research_code_modified"] is False
    assert paper["statistics_surface"] == paper["chart_dashboard_surface"] == "AVAILABLE"
    assert paper["statistics_version"] == "PAPER_STATISTICS_V1"
    assert paper["product_stage"] == "V1_PAPER_ALPHA"
    assert paper["scientifically_approved"] is False
    assert paper["lifecycle_trigger"] == "EXPLICIT_USER_ACTION_ONLY"
    assert paper["strategy_version"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    assert paper["research_status"] == "PAPER_RESEARCH_CANDIDATE"
    assert paper["champion_status"] == "NONE"
    assert paper["genuine_paper_trades_completed"] == 0
    assert paper["historical_engine_modified"] is False
    assert paper["timestamp_translation_used"] is False
    assert paper["equivalence_validation"] == "PASS"
    assert paper["order_placement"] is False
    assert paper["credentials"] is False
    assert paper["leverage_or_short"] is False
    assert paper["real_money"] is False


def test_state_still_records_wp009_as_paused() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    pause = state["exogenous_acquisition_pause"]
    assert pause["status"] == "PARTIAL"
    assert pause["pause_reason"] == "PAUSED_FOR_PRODUCT_PRIORITY"
    assert pause["wp009_finalized"] is False


def test_future_paper_evidence_contract_declares_the_separation() -> None:
    record = json.loads(
        (ROOT / "research/paper/FUTURE_PAPER_EVIDENCE_V1.json").read_text(encoding="utf-8")
    )
    assert (ROOT / "docs/contracts/FUTURE_PAPER_EVIDENCE_V1.md").is_file()
    assert record["champion_status"] == "NONE"
    assert record["research_status"] == "PAPER_RESEARCH_CANDIDATE"
    assert record["strategy_logic_changed"] is False
    assert record["counter_discipline"]["incremented_by_this_work_package"] is False
    assert record["counter_discipline"]["incremented_by_tests_or_fixtures"] is False
    execution = record["execution"]
    assert execution["historical_engine_modified"] is False
    assert execution["historical_cutoff_weakened"] is False
    assert execution["real_timestamps"] is True
    assert execution["timestamp_translation_used"] is False
    assert execution["prospective_execution_version"] == "PROSPECTIVE_PAPER_EXECUTION_V1"
    assert execution["equivalence_validation"]["status"] == "PASS"
    assert record["execution"]["entry_execution"] == "NEXT_1M_OPEN_EXECUTION"
    assert record["execution"]["ambiguous_fill_policy"] == "STOP_FIRST_V1"
    assert record["execution"]["missing_or_gapped_minutes_manufacture_outcome"] is False
    assert record["lifecycle"]["background_or_startup_execution"] is False
    assert record["lifecycle"]["max_active_trades"] == 1
    separation = record["separation_from_development_research"]
    assert not any(value for key, value in separation.items() if key.startswith("paper_records"))
    assert all(value is False for value in record["safety"].values())


def test_paper_execution_uses_real_timestamps_without_translation() -> None:
    source = (ROOT / "backend/app/product/paper.py").read_text(encoding="utf-8")
    assert "clock_shift_us" not in source
    assert "shift" not in source
    assert "simulate_prospective" in source


def test_stored_trades_carry_the_prospective_execution_version(tmp_path: Path) -> None:
    store, trade = _created(tmp_path)
    assert trade["execution_model_version"] == "PROSPECTIVE_PAPER_EXECUTION_V1"
    assert trade["engine_version"] == "PROSPECTIVE_PAPER_ENGINE_V1"
    klines = _flat(10)
    klines[3] = _minute(3, high=TARGET + 500, low=49_900, close=TARGET, opened=50_000)
    update_lifecycle(store, now=NOW, feed=_feed(klines))
    closed = store.load()[0]
    # Real post-cutoff instants, never an in-development anchor.
    assert closed["entry_time"] == "2026-03-05T12:00:00Z"
    assert closed["exit_time"] == "2026-03-05T12:03:00Z"
    assert closed["signal_time"] == "2026-03-05T12:00:00Z"
    assert "PROSPECTIVE_PAPER_EXECUTION_V1" in closed["resolution_detail"]


def test_the_frozen_execution_engine_is_used_unmodified() -> None:
    import subprocess

    changed = subprocess.check_output(
        ["git", "diff", "--name-only", "2f963676b26dbbc2c33bdef8120fdb37221d121a", "HEAD"],
        cwd=ROOT,
        text=True,
    ).split()
    for frozen in (
        "backend/app/backtest/engine.py",
        "backend/app/backtest/models.py",
        "backend/app/data/policy.py",
        "backend/app/research/continuation.py",
    ):
        assert frozen not in changed


def test_listing_reports_the_declared_contract(tmp_path: Path) -> None:
    store, _ = _created(tmp_path)
    body = listing(store)
    assert body["contract"] == "docs/contracts/FUTURE_PAPER_EVIDENCE_V1.md"
    assert body["evidence_stage"] == "PROSPECTIVE_PAPER_RESEARCH_NOT_DEVELOPMENT_EVIDENCE"
    assert body["max_hold_minutes"] == 1440
