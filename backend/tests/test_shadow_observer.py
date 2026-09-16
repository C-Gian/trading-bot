"""Synthetic-clock/feed tests for FUTURE_SHADOW_PAPER_EVIDENCE_V1."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from app.main import create_app
from app.product.market_feed import Kline
from app.product.paper_v2 import EVIDENCE_VERSION as MANUAL_EVIDENCE_VERSION
from app.product.paper_v2 import STORE_PATH as MANUAL_STORE_PATH
from app.product.shadow_observer import (
    CLOSED_EXPIRY,
    CLOSED_STOP,
    CLOSED_TARGET,
    DATA_QUALITY_ERROR,
    EVIDENCE_STAGE,
    EVIDENCE_STORE_PATH,
    EVIDENCE_VERSION,
    HEALTH_STORE_PATH,
    MISSED_DECISION,
    OBSERVER_VERSION,
    OPEN,
    SUPPRESSED,
    ProspectiveShadowObserver,
    ShadowEvidenceStore,
    ShadowHealthStore,
    ShadowObserverError,
    default_observer,
)
from app.research.local_runner import default_runner
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
HOUR = timedelta(hours=1)
MINUTE = timedelta(minutes=1)


class Clock:
    def __init__(self, value: datetime):
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class SyntheticAnalysis:
    def __init__(self, decisions: dict[datetime, str] | None = None):
        self.decisions = decisions or {}
        self.calls: list[datetime] = []

    def __call__(self, *, now: datetime) -> dict[str, Any]:
        boundary = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        self.calls.append(boundary)
        decision = self.decisions.get(boundary, "NO_TRADE")
        gates = decision == "LONG"
        return {
            "strategy_version": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
            "champion_status": "NONE",
            "research_status": "PAPER_RESEARCH_CANDIDATE",
            "real_money": False,
            "data_status": "OK",
            "decision": decision,
            "signal_time": boundary.isoformat().replace("+00:00", "Z"),
            "analysis_time": now.isoformat().replace("+00:00", "Z"),
            "analysis_id": f"analysis-{int(boundary.timestamp())}",
            "reference_price": 100.0,
            "features": {
                "persistent_up": gates,
                "breakout": gates,
                "participation": gates,
            },
        }


class SyntheticMinuteFeed:
    def __init__(self, rows: list[Kline] | None = None):
        self.rows = rows or []
        self.calls: list[tuple[int, int, datetime]] = []

    def __call__(self, start_ms: int, count: int, *, now: datetime) -> tuple[Kline, ...]:
        self.calls.append((start_ms, count, now))
        completed = int(now.timestamp() * 1000) - 60_000
        rows = [row for row in self.rows if start_ms <= row.open_ms <= completed]
        return tuple(rows[:count])


def minute(
    instant: datetime,
    *,
    opened: float = 100.0,
    high: float = 100.5,
    low: float = 99.5,
    close: float = 100.0,
) -> Kline:
    return Kline(int(instant.timestamp() * 1000), high, low, close, 1.0, opened)


def service(
    tmp_path: Path,
    clock: Clock,
    analysis: SyntheticAnalysis | None = None,
    feed: SyntheticMinuteFeed | None = None,
) -> ProspectiveShadowObserver:
    return ProspectiveShadowObserver(
        ShadowEvidenceStore(tmp_path / "shadow" / "evidence.json"),
        ShadowHealthStore(tmp_path / "shadow" / "health.json"),
        analyser=analysis or SyntheticAnalysis(),
        minute_feed=feed or SyntheticMinuteFeed(),
        clock=clock,
        build_identity="synthetic-build",
        heartbeat_seconds=1,
    )


def activate_at(observer: ProspectiveShadowObserver, instant: datetime) -> None:
    observer.activate(now=instant)


def observe(
    observer: ProspectiveShadowObserver,
    clock: Clock,
    boundary: datetime,
    *,
    seconds_after: int = 30,
) -> None:
    evaluated = boundary + timedelta(seconds=seconds_after)
    clock.value = evaluated + timedelta(seconds=1)
    observer.tick(now=evaluated)


def test_first_boundary_is_strictly_after_durable_activation(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)
    clock = Clock(activation)
    observer = service(tmp_path, clock)
    activate_at(observer, activation)
    health = observer.health_store.load()
    assert health is not None
    assert health["observer_activation"] == "2026-09-16T10:00:00Z"
    assert health["next_expected_boundary"] == "2026-09-16T11:00:00Z"
    assert observer.evidence_store.load()["decisions"] == []


def test_no_trade_is_durable_prospective_evidence(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 23, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    clock = Clock(activation)
    analysis = SyntheticAnalysis({boundary: "NO_TRADE"})
    observer = service(tmp_path, clock, analysis)
    activate_at(observer, activation)
    observe(observer, clock, boundary)

    evidence = observer.evidence_store.load()
    assert len(evidence["decisions"]) == 1
    decision = evidence["decisions"][0]
    assert decision["decision"] == "NO_TRADE"
    assert decision["durable_persistence_time"] == "2026-09-16T11:00:31Z"
    assert evidence["trades"] == []
    assert observer.overview()["prospective_counters"]["prospective_observation_hours"] == 1


def test_latency_beyond_five_minutes_is_missed_and_never_analysed(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    clock = Clock(activation)
    analysis = SyntheticAnalysis({boundary: "LONG"})
    observer = service(tmp_path, clock, analysis)
    activate_at(observer, activation)
    observer.tick(now=boundary + timedelta(minutes=5, seconds=1))

    decision = observer.evidence_store.load()["decisions"][0]
    assert decision["status"] == MISSED_DECISION
    assert decision["decision"] is None
    assert analysis.calls == []
    assert observer.evidence_store.load()["trades"] == []


def test_decision_that_cannot_persist_within_five_minutes_fails_closed(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    clock = Clock(activation)
    observer = service(tmp_path, clock, SyntheticAnalysis({boundary: "LONG"}))
    activate_at(observer, activation)
    clock.value = boundary + timedelta(minutes=5, seconds=1)
    observer.tick(now=boundary + timedelta(seconds=30))

    evidence = observer.evidence_store.load()
    assert evidence["decisions"][0]["status"] == MISSED_DECISION
    assert evidence["decisions"][0]["decision"] is None
    assert evidence["trades"][0]["status"] == DATA_QUALITY_ERROR
    assert evidence["trades"][0]["entry_time"] is None


def test_long_intent_precedes_strictly_future_entry_and_boundary_open_is_forbidden(
    tmp_path: Path,
) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    entry = boundary + MINUTE
    clock = Clock(activation)
    analysis = SyntheticAnalysis({boundary: "LONG"})
    feed = SyntheticMinuteFeed([minute(boundary, opened=90), minute(entry, opened=100)])
    observer = service(tmp_path, clock, analysis, feed)
    activate_at(observer, activation)
    observe(observer, clock, boundary)

    pending = observer.evidence_store.load()["trades"][0]
    assert pending["intent_persisted_at"] == "2026-09-16T11:00:31Z"
    assert pending["entry_not_before"] == "2026-09-16T11:01:00Z"
    assert pending["entry_time"] is None

    clock.value = boundary + timedelta(minutes=2)
    observer.tick(now=clock.value)
    trade = observer.evidence_store.load()["trades"][0]
    assert trade["status"] == OPEN
    assert trade["entry_time"] == "2026-09-16T11:01:00Z"
    assert trade["entry_price"] == 100.0
    assert trade["entry_time"] > trade["intent_persisted_at"]
    assert trade["stop_price"] == 98.0
    assert trade["target_price"] == 104.0


def test_second_long_is_recorded_but_suppressed_while_position_is_active(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    first = datetime(2026, 9, 16, 11, tzinfo=UTC)
    second = first + HOUR
    entry = first + MINUTE
    clock = Clock(activation)
    analysis = SyntheticAnalysis({first: "LONG", second: "LONG"})
    feed = SyntheticMinuteFeed([minute(entry)])
    observer = service(tmp_path, clock, analysis, feed)
    activate_at(observer, activation)
    observe(observer, clock, first)
    clock.value = first + timedelta(minutes=2)
    observer.tick(now=clock.value)
    observe(observer, clock, second)

    evidence = observer.evidence_store.load()
    assert [item["decision"] for item in evidence["decisions"]] == ["LONG", "LONG"]
    assert evidence["decisions"][1]["status"] == SUPPRESSED
    assert len(evidence["trades"]) == 1
    overview = observer.overview()
    assert overview["raw_prospective_long_signals"] == 2
    assert overview["suppressed_long_signals"] == 1


@pytest.mark.parametrize(
    ("resolution_bar", "expected_status", "expected_reason"),
    (
        ({"high": 105.0, "low": 99.0, "close": 104.0}, CLOSED_TARGET, "TARGET"),
        ({"high": 105.0, "low": 97.0, "close": 100.0}, CLOSED_STOP, "STOP"),
    ),
)
def test_stop_target_and_stop_first_match_frozen_geometry(
    tmp_path: Path,
    resolution_bar: dict[str, float],
    expected_status: str,
    expected_reason: str,
) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    entry = boundary + MINUTE
    resolution = entry + MINUTE
    clock = Clock(activation)
    feed = SyntheticMinuteFeed([minute(entry), minute(resolution, opened=100.0, **resolution_bar)])
    observer = service(tmp_path, clock, SyntheticAnalysis({boundary: "LONG"}), feed)
    activate_at(observer, activation)
    observe(observer, clock, boundary)
    clock.value = resolution + MINUTE
    observer.tick(now=clock.value)

    trade = observer.evidence_store.load()["trades"][0]
    assert trade["status"] == expected_status
    assert trade["exit_reason"] == expected_reason
    assert trade["cost_model_version"] == "BTCUSDT_SPOT_COST_V1"
    assert trade["gross_return"] is not None and trade["net_return"] is not None
    assert trade["r_multiple"] is not None


def test_expiry_uses_1440_minutes_and_governed_costs(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    entry = boundary + MINUTE
    rows = [minute(entry + index * MINUTE) for index in range(1440)]
    clock = Clock(activation)
    observer = service(
        tmp_path,
        clock,
        SyntheticAnalysis({boundary: "LONG"}),
        SyntheticMinuteFeed(rows),
    )
    activate_at(observer, activation)
    observe(observer, clock, boundary)
    clock.value = entry + timedelta(minutes=1440)
    fetched, errors = observer._reconcile_open_trades(clock.value, after_restart=False)

    trade = observer.evidence_store.load()["trades"][0]
    assert fetched and errors == []
    assert trade["status"] == CLOSED_EXPIRY
    assert trade["holding_minutes"] == 1440
    assert trade["cost_model_version"] == "BTCUSDT_SPOT_COST_V1"
    assert trade["net_return"] < trade["gross_return"]


def test_restart_marks_signal_downtime_missed_without_backfill(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    clock = Clock(activation)
    first_analysis = SyntheticAnalysis()
    first = service(tmp_path, clock, first_analysis)
    activate_at(first, activation)
    first.stop()

    restart = datetime(2026, 9, 16, 12, 2, tzinfo=UTC)
    clock.value = restart
    restarted_analysis = SyntheticAnalysis(
        {
            datetime(2026, 9, 16, 11, tzinfo=UTC): "LONG",
            datetime(2026, 9, 16, 12, tzinfo=UTC): "LONG",
        }
    )
    restarted = service(tmp_path, clock, restarted_analysis)
    activate_at(restarted, restart)

    decisions = restarted.evidence_store.load()["decisions"]
    assert [item["status"] for item in decisions] == [MISSED_DECISION, MISSED_DECISION]
    assert all(item["decision"] is None for item in decisions)
    assert restarted_analysis.calls == []
    assert restarted.evidence_store.load()["trades"] == []
    health = restarted.health_store.load()
    assert health is not None
    assert health["next_expected_boundary"] == "2026-09-16T13:00:00Z"


def test_already_open_trade_reconciles_after_restart_but_original_times_do_not_change(
    tmp_path: Path,
) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    entry = boundary + MINUTE
    target = entry + MINUTE
    clock = Clock(activation)
    initial_feed = SyntheticMinuteFeed([minute(entry)])
    first = service(tmp_path, clock, SyntheticAnalysis({boundary: "LONG"}), initial_feed)
    activate_at(first, activation)
    observe(first, clock, boundary)
    clock.value = boundary + timedelta(minutes=2)
    first.tick(now=clock.value)
    original = dict(first.evidence_store.load()["trades"][0])
    first.stop()

    restart = boundary + timedelta(minutes=4)
    clock.value = restart
    restart_feed = SyntheticMinuteFeed(
        [minute(entry), minute(target, high=105.0, low=99.0, close=104.0)]
    )
    restarted = service(tmp_path, clock, SyntheticAnalysis(), restart_feed)
    activate_at(restarted, restart)
    trade = restarted.evidence_store.load()["trades"][0]
    assert trade["status"] == CLOSED_TARGET
    assert trade["reconciled_after_restart"] is True
    assert trade["intent_persisted_at"] == original["intent_persisted_at"]
    assert trade["entry_time"] == original["entry_time"]


def test_pending_entry_is_not_reconstructed_after_restart(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    clock = Clock(activation)
    first = service(tmp_path, clock, SyntheticAnalysis({boundary: "LONG"}))
    activate_at(first, activation)
    observe(first, clock, boundary)
    first.stop()

    clock.value = boundary + timedelta(minutes=2)
    restarted = service(
        tmp_path,
        clock,
        SyntheticAnalysis(),
        SyntheticMinuteFeed([minute(boundary + MINUTE)]),
    )
    activate_at(restarted, clock.value)
    trade = restarted.evidence_store.load()["trades"][0]
    assert trade["status"] == DATA_QUALITY_ERROR
    assert trade["data_quality_status"] == "DOWNTIME_BEFORE_ENTRY"
    assert trade["entry_time"] is None


def test_unavailable_entry_bars_fail_closed_without_manufacturing_a_fill(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    clock = Clock(activation)
    observer = service(tmp_path, clock, SyntheticAnalysis({boundary: "LONG"}))
    activate_at(observer, activation)
    observe(observer, clock, boundary)
    clock.value = boundary + timedelta(minutes=6)
    observer.tick(now=clock.value)

    trade = observer.evidence_store.load()["trades"][0]
    assert trade["status"] == DATA_QUALITY_ERROR
    assert trade["data_quality_status"] == "ENTRY_BARS_UNAVAILABLE"
    assert trade["entry_time"] is trade["entry_price"] is None


def test_observer_api_is_read_only_and_stores_are_separate(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    clock = Clock(activation)
    observer = service(tmp_path, clock)
    activate_at(observer, activation)
    client = TestClient(create_app(shadow_observer=observer))
    payload = client.get("/api/v1/product/prospective-observer").json()

    assert payload["evidence_version"] == EVIDENCE_VERSION
    assert payload["evidence_stage"] == EVIDENCE_STAGE
    assert payload["observer_version"] == OBSERVER_VERSION
    assert payload["manual_evidence_included"] is False
    assert payload["real_money"] is False
    assert MANUAL_EVIDENCE_VERSION == "FUTURE_PAPER_EVIDENCE_V2"
    assert MANUAL_STORE_PATH == "data/paper/PAPER_TRADES_V2.json"
    assert observer.evidence_store.path.name != Path(MANUAL_STORE_PATH).name


def test_local_backend_lifespan_starts_and_stops_exactly_one_observer() -> None:
    class LifecycleProbe:
        starts = 0
        stops = 0

        def start(self) -> None:
            self.starts += 1

        def stop(self) -> None:
            self.stops += 1

        def overview(self) -> dict[str, Any]:
            return {"status": "ACTIVE", "real_money": False}

    probe = LifecycleProbe()
    with TestClient(create_app(shadow_observer=probe)) as client:
        assert client.get("/api/v1/product/prospective-observer").json()["status"] == "ACTIVE"
        assert probe.starts == 1 and probe.stops == 0
    assert probe.starts == probe.stops == 1


def test_no_real_order_or_credential_surface_exists() -> None:
    app = create_app()
    paths = {str(getattr(route, "path", "")).lower() for route in app.routes}
    observer_paths = {path for path in paths if "prospective-observer" in path}
    assert observer_paths == {"/api/v1/product/prospective-observer"}
    source = (ROOT / "backend/app/product/shadow_observer.py").read_text(encoding="utf-8").lower()
    for forbidden in ("api_key", "apikey", "hmac", "withdraw", "create_order", "place_order"):
        assert forbidden not in source
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert state["experiments_completed"] == 26
    assert state["champion_status"] == "NONE"
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["real_money_authorized"] is False


def test_historical_aligned_family_is_final_and_no_descendant_is_runnable() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    closure = state["aligned_development_closure"]
    assert closure == {
        "version": "ALIGNED_DEVELOPMENT_FINAL_CLOSURE_V1",
        "research_director_accepted": True,
        "aligned_development_family_status": "PARKED_DEVELOPMENT_SEARCH_EXHAUSTED",
        "causal_panel_correction_status": "PASS",
        "frozen_calendar_randomization_support_status": "FAIL",
        "accepted_randomization_vectors": 0,
        "requested_randomization_vectors": 1024,
        "empirical_power_executed": False,
        "real_gate_intensity_beta_observed": False,
        "real_sparse_cross_section_beta_observed": False,
        "historical_descendant_search_authorized": False,
        "market_performance_rejected": False,
    }
    assert state["primary_research_phase"] == "PROSPECTIVE_EVIDENCE_COLLECTION"
    assert state["historical_discovery_status"] == "PAUSED"
    candidates = default_runner().overview()["candidates"]
    assert not any(
        candidate["runnable"]
        and any(token in candidate["candidate_id"] for token in ("ALIGNED", "GATE_INTENSITY"))
        for candidate in candidates
    )


def test_test_startup_cannot_write_the_production_prospective_store() -> None:
    """The real wiring activates on backend start; a test run must never record evidence."""
    observer = default_observer()
    assert observer.evidence_store.path == ROOT / EVIDENCE_STORE_PATH
    assert observer.health_store.path == ROOT / HEALTH_STORE_PATH

    with pytest.raises(ShadowObserverError, match="production prospective evidence store"):
        observer.activate(now=datetime(2026, 9, 16, 10, 30, tzinfo=UTC))

    with (
        pytest.raises(ShadowObserverError, match="production prospective evidence store"),
        TestClient(create_app(shadow_observer=default_observer())),
    ):
        pass

    assert not (ROOT / EVIDENCE_STORE_PATH).exists()
    assert not (ROOT / HEALTH_STORE_PATH).exists()
