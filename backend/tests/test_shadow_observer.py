"""Synthetic-clock/feed tests for FUTURE_SHADOW_PAPER_EVIDENCE_V1_1."""

from __future__ import annotations

import contextlib
import hashlib
import json
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from app.main import create_app
from app.product import audit_chain
from app.product.market_feed import Kline
from app.product.observer_lease import CONTENDED_ERROR, ObserverLease
from app.product.paper_v2 import EVIDENCE_VERSION as MANUAL_EVIDENCE_VERSION
from app.product.paper_v2 import STORE_PATH as MANUAL_STORE_PATH
from app.product.provenance import (
    PROVENANCE_VERSION,
    SUPERSEDED_PROVENANCE_STATUS,
    SUPERSEDED_PROVENANCE_VERSION,
    UNVERIFIED_REASON,
    ProvenanceError,
    aggregate_sha256,
    is_governed_runtime_artifact,
    manifest_members,
    repository_provenance,
    semantic_changes,
    semantic_manifest,
)
from app.product.provenance import validate as provenance_validate
from app.product.shadow_observer import (
    CLOSED_EXPIRY,
    CLOSED_STOP,
    CLOSED_TARGET,
    DATA_QUALITY_ERROR,
    EVIDENCE_CONTRACT,
    EVIDENCE_STAGE,
    EVIDENCE_STORE_PATH,
    EVIDENCE_VERSION,
    HEALTH_STORE_PATH,
    INTEGRITY_ERROR,
    LEASE_PATH,
    MISSED_DECISION,
    OBSERVER_VERSION,
    OPEN,
    RUNTIME_ARTIFACTS,
    SUPPRESSED,
    ProspectiveShadowObserver,
    ShadowEvidenceStore,
    ShadowHealthStore,
    ShadowObserverError,
    default_observer,
    trade_projection,
)
from app.research.local_runner import default_runner
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def _runtime_snapshot(path: Path) -> bytes | None:
    """Exact bytes of a production runtime store, or None when it does not exist."""
    return path.read_bytes() if path.is_file() else None


def _git_ignores(path: str) -> bool:
    return (
        subprocess.run(
            ["git", "check-ignore", "-q", path], cwd=ROOT, capture_output=True, check=False
        ).returncode
        == 0
    )


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


SYNTHETIC_MANIFEST = {
    "backend/app/product/shadow_observer.py": "11" * 32,
    "backend/app/product/analysis.py": "22" * 32,
    "backend/app/research/continuation.py": "33" * 32,
    "backend/app/product/execution_v2.py": "44" * 32,
    "backend/app/backtest/models.py": "55" * 32,
    "backend/app/backtest/__init__.py": "66" * 32,
    "docs/contracts/FUTURE_SHADOW_PAPER_EVIDENCE_V1_1.md": "77" * 32,
}


def synthetic_provenance(**overrides: Any) -> dict[str, Any]:
    """A deterministic verified build identity; tests never shell out to git."""
    manifest = dict(overrides.pop("semantic_manifest", SYNTHETIC_MANIFEST))
    record = {
        "provenance_version": PROVENANCE_VERSION,
        "verified": True,
        "unverified_reason": None,
        "git_head": "a" * 40,
        "git_branch": "main",
        "worktree_clean": True,
        "application_version": "synthetic",
        "observer_version": OBSERVER_VERSION,
        "evidence_version": EVIDENCE_VERSION,
        "strategy_version": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
        "execution_version": "PAPER_EXECUTION_V2",
        "cost_model_version": "BTCUSDT_SPOT_COST_V1",
        "semantic_manifest": manifest,
        "semantic_manifest_sha256": aggregate_sha256(manifest),
    }
    record.update(overrides)
    return record


def service(
    tmp_path: Path,
    clock: Clock,
    analysis: SyntheticAnalysis | None = None,
    feed: SyntheticMinuteFeed | None = None,
    *,
    provenance_provider: Callable[[], dict[str, Any]] | None = None,
    lease: ObserverLease | None = None,
) -> ProspectiveShadowObserver:
    return ProspectiveShadowObserver(
        ShadowEvidenceStore(tmp_path / "shadow" / "evidence.json"),
        ShadowHealthStore(tmp_path / "shadow" / "health.json"),
        analyser=analysis or SyntheticAnalysis(),
        minute_feed=feed or SyntheticMinuteFeed(),
        clock=clock,
        build_identity="synthetic-build",
        heartbeat_seconds=1,
        provenance_provider=provenance_provider or synthetic_provenance,
        lease=lease,
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


def test_tests_cannot_write_the_production_v1_1_evidence_store() -> None:
    store = ShadowEvidenceStore(ROOT / EVIDENCE_STORE_PATH)
    assert store.path == ROOT / EVIDENCE_STORE_PATH
    document = store.load()
    with pytest.raises(ShadowObserverError, match="production prospective evidence store"):
        store.save(document)
    assert not (ROOT / EVIDENCE_STORE_PATH).exists()


def test_tests_cannot_write_the_production_observer_health_store() -> None:
    store = ShadowHealthStore(ROOT / HEALTH_STORE_PATH)
    health: dict[str, Any] = {
        "version": OBSERVER_VERSION,
        "evidence_version": EVIDENCE_VERSION,
        "status": "DEGRADED",
        "backend_start": "2026-09-16T10:30:00Z",
        "observer_activation": None,
        "last_heartbeat": "2026-09-16T10:30:00Z",
        "next_expected_boundary": None,
        "activation_history": [],
        "missed_boundaries": 0,
        "real_money": False,
    }
    before = _runtime_snapshot(ROOT / HEALTH_STORE_PATH)
    with pytest.raises(ShadowObserverError, match="production prospective evidence store"):
        store.save(health)
    assert _runtime_snapshot(ROOT / HEALTH_STORE_PATH) == before


def test_synthetic_stores_outside_the_production_path_remain_usable(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    clock = Clock(activation)
    observer = service(tmp_path, clock, SyntheticAnalysis({boundary: "NO_TRADE"}))
    activate_at(observer, activation)
    observe(observer, clock, boundary)
    assert observer.evidence_store.path.is_file()
    assert observer.health_store.path.is_file()
    assert len(observer.evidence_store.load()["decisions"]) == 1


def test_testclient_lifespan_cannot_create_production_scientific_evidence() -> None:
    """The real wiring activates on backend start; a test run must never record evidence."""
    observer = default_observer()
    assert observer.evidence_store.path == ROOT / EVIDENCE_STORE_PATH
    assert observer.health_store.path == ROOT / HEALTH_STORE_PATH
    assert observer.lease is not None and observer.lease.path == ROOT / LEASE_PATH

    health_before = _runtime_snapshot(ROOT / HEALTH_STORE_PATH)
    try:
        with TestClient(create_app(shadow_observer=observer)):
            pass
    except ShadowObserverError as exc:  # the guard may surface through the lifespan
        assert "production prospective evidence store" in str(exc)
    finally:
        # Stopping also writes health, so the same guard fires there; release the
        # scientific lease directly so a real local backend is never locked out.
        with contextlib.suppress(ShadowObserverError):
            observer.stop()
        if observer.lease is not None:
            observer.lease.release()

    # No genuine observation exists, and operational state a real run left behind is
    # never touched by a test.
    assert not (ROOT / EVIDENCE_STORE_PATH).exists()
    assert _runtime_snapshot(ROOT / HEALTH_STORE_PATH) == health_before


# --- BUILD_PROVENANCE_V1 ----------------------------------------------------------


def test_dirty_worktree_cannot_emit_a_scientific_decision(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    clock = Clock(activation)
    analysis = SyntheticAnalysis({boundary: "LONG"})
    dirty = synthetic_provenance(worktree_clean=False)
    observer = service(tmp_path, clock, analysis, provenance_provider=lambda: dirty)
    activate_at(observer, activation)
    observe(observer, clock, boundary)

    assert analysis.calls == []
    assert observer.evidence_store.load()["decisions"] == []
    health = observer.health_store.load()
    assert health is not None
    assert health["status"] == "DEGRADED"
    assert UNVERIFIED_REASON in health["current_error"]
    assert health["build_provenance_verified"] is False


def test_unverified_build_cannot_emit_a_scientific_decision(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    clock = Clock(activation)
    analysis = SyntheticAnalysis({boundary: "LONG"})
    unverified = synthetic_provenance(verified=False, unverified_reason=UNVERIFIED_REASON)
    observer = service(tmp_path, clock, analysis, provenance_provider=lambda: unverified)
    activate_at(observer, activation)
    observe(observer, clock, boundary)

    assert analysis.calls == []
    assert observer.evidence_store.load()["decisions"] == []
    assert observer.overview()["status"] == "DEGRADED"


def test_unrepaired_unverified_build_becomes_a_typed_missed_decision(tmp_path: Path) -> None:
    """The signal is never evaluated first and relabelled once the window closes."""
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    clock = Clock(activation)
    analysis = SyntheticAnalysis({boundary: "LONG"})
    dirty = synthetic_provenance(worktree_clean=False)
    observer = service(tmp_path, clock, analysis, provenance_provider=lambda: dirty)
    activate_at(observer, activation)

    observe(observer, clock, boundary, seconds_after=60)
    assert observer.evidence_store.load()["decisions"] == []

    clock.value = boundary + timedelta(minutes=6)
    observer.tick(now=clock.value)
    decisions = observer.evidence_store.load()["decisions"]
    assert [item["status"] for item in decisions] == [MISSED_DECISION]
    assert decisions[0]["miss_reason"] == UNVERIFIED_REASON
    assert decisions[0]["decision"] is None
    assert analysis.calls == []


def test_clean_verified_build_records_and_persists_its_provenance(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    clock = Clock(activation)
    observer = service(tmp_path, clock, SyntheticAnalysis({boundary: "NO_TRADE"}))
    activate_at(observer, activation)
    observe(observer, clock, boundary)

    document = observer.evidence_store.load()
    decision = document["decisions"][0]
    assert decision["status"] != MISSED_DECISION
    assert decision["decision"] == "NO_TRADE"

    history = document["build_provenance"]
    assert len(history) == 1
    assert history[0]["verified"] is True
    assert history[0]["git_head"] == "a" * 40
    assert history[0]["worktree_clean"] is True
    assert history[0]["semantic_manifest"] == SYNTHETIC_MANIFEST
    assert decision["build_provenance_sha256"] == history[0]["semantic_manifest_sha256"]
    assert observer.overview()["build_provenance_sha256"] == decision["build_provenance_sha256"]


def test_semantic_source_change_changes_provenance_identity() -> None:
    contract = "docs/contracts/FUTURE_SHADOW_PAPER_EVIDENCE_V1_1.md"
    members = manifest_members(contract)
    for required in (
        "backend/app/product/shadow_observer.py",
        "backend/app/product/analysis.py",
        "backend/app/research/continuation.py",
        "backend/app/product/execution_v2.py",
        "backend/app/backtest/models.py",
        "backend/app/backtest/__init__.py",
        contract,
    ):
        assert required in members

    manifest = semantic_manifest(contract)
    assert set(manifest) == set(members)
    baseline = aggregate_sha256(manifest)
    assert aggregate_sha256(dict(manifest)) == baseline

    for member in members:
        altered = dict(manifest)
        altered[member] = "00" * 32
        assert aggregate_sha256(altered) != baseline


def test_repository_provenance_reports_the_running_build() -> None:
    record = repository_provenance(
        observer_version=OBSERVER_VERSION,
        evidence_version=EVIDENCE_VERSION,
        contract_path="docs/contracts/FUTURE_SHADOW_PAPER_EVIDENCE_V1_1.md",
    )
    assert record["provenance_version"] == PROVENANCE_VERSION
    assert record["observer_version"] == OBSERVER_VERSION
    assert record["strategy_version"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    assert record["cost_model_version"] == "BTCUSDT_SPOT_COST_V1"
    assert record["semantic_manifest_sha256"] == aggregate_sha256(record["semantic_manifest"])
    # Verification tracks the real tree, so this asserts the rule rather than a fixed value.
    assert record["verified"] is (bool(record["git_head"]) and record["worktree_clean"])


# --- single active observer lease -------------------------------------------------


def test_only_one_process_level_observer_lease_can_be_owned(tmp_path: Path) -> None:
    path = tmp_path / "observer.lease"
    first = ObserverLease(path)
    second = ObserverLease(path)
    assert first.acquire() is True
    assert first.held is True
    assert second.acquire() is False
    assert second.held is False

    first.release()
    assert first.held is False
    assert second.acquire() is True
    second.release()


def test_losing_the_lease_prevents_scientific_activation(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    path = tmp_path / "observer.lease"
    incumbent = ObserverLease(path)
    assert incumbent.acquire() is True

    clock = Clock(activation)
    analysis = SyntheticAnalysis({boundary: "LONG"})
    observer = service(tmp_path, clock, analysis, lease=ObserverLease(path))
    overview = observer.activate(now=activation)

    assert overview["status"] == "DEGRADED"
    assert overview["current_error"] == CONTENDED_ERROR
    health = observer.health_store.load()
    assert health is not None
    # A contended instance never invents an activation instant or any uptime.
    assert health["observer_activation"] is None
    assert health["activation_history"] == []
    assert observer.evidence_store.load()["decisions"] == []

    with pytest.raises(ShadowObserverError, match="not activated"):
        observer.tick(now=boundary + timedelta(seconds=30))
    assert analysis.calls == []
    incumbent.release()


def test_second_observer_does_not_duplicate_evaluation_or_evidence(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    path = tmp_path / "observer.lease"
    clock = Clock(activation)

    primary_analysis = SyntheticAnalysis({boundary: "NO_TRADE"})
    primary = service(tmp_path, clock, primary_analysis, lease=ObserverLease(path))
    activate_at(primary, activation)

    duplicate_analysis = SyntheticAnalysis({boundary: "NO_TRADE"})
    duplicate = service(tmp_path, clock, duplicate_analysis, lease=ObserverLease(path))
    duplicate.activate(now=activation)

    observe(primary, clock, boundary)
    assert len(primary.evidence_store.load()["decisions"]) == 1
    assert duplicate_analysis.calls == []
    primary.stop()


# --- tamper-evident audit chain ---------------------------------------------------


def test_audit_genesis_and_chain_extension_are_valid(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    clock = Clock(activation)
    observer = service(
        tmp_path,
        clock,
        SyntheticAnalysis(
            {
                datetime(2026, 9, 16, 11, tzinfo=UTC): "NO_TRADE",
                datetime(2026, 9, 16, 12, tzinfo=UTC): "NO_TRADE",
            }
        ),
    )
    activate_at(observer, activation)
    assert observer.evidence_store.load()["audit_chain"] == []

    observe(observer, clock, datetime(2026, 9, 16, 11, tzinfo=UTC))
    observe(observer, clock, datetime(2026, 9, 16, 12, tzinfo=UTC))

    chain = observer.evidence_store.load()["audit_chain"]
    assert [event["sequence"] for event in chain] == list(range(1, len(chain) + 1))
    assert chain[0]["previous_event_hash"] == audit_chain.GENESIS_PREVIOUS_HASH
    assert [event["event_type"] for event in chain][-1] == audit_chain.DECISION_OBSERVED
    for earlier, later in zip(chain, chain[1:], strict=False):
        assert later["previous_event_hash"] == earlier["event_hash"]
    audit_chain.validate_chain(chain)


def test_long_lifecycle_appends_each_governed_transition(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    entry = boundary + MINUTE
    resolution = entry + MINUTE
    clock = Clock(activation)
    feed = SyntheticMinuteFeed(
        [minute(entry), minute(resolution, high=110.0, low=99.0, close=105.0)]
    )
    observer = service(tmp_path, clock, SyntheticAnalysis({boundary: "LONG"}), feed)
    activate_at(observer, activation)
    observe(observer, clock, boundary)
    clock.value = resolution + timedelta(minutes=2)
    observer.tick(now=clock.value)

    chain = observer.evidence_store.load()["audit_chain"]
    types = [event["event_type"] for event in chain]
    assert audit_chain.DECISION_OBSERVED in types
    assert audit_chain.INTENT_PERSISTED in types
    assert audit_chain.ENTRY_ESTABLISHED in types
    assert audit_chain.TRADE_CLOSED in types
    assert types.index(audit_chain.INTENT_PERSISTED) < types.index(audit_chain.ENTRY_ESTABLISHED)
    assert types.index(audit_chain.ENTRY_ESTABLISHED) < types.index(audit_chain.TRADE_CLOSED)
    audit_chain.validate_chain(chain)


def _tamper(store: ShadowEvidenceStore, mutate: Callable[[dict[str, Any]], None]) -> None:
    """Edit the durable file directly, exactly as a corrupting external write would."""
    document = json.loads(store.path.read_text(encoding="utf-8"))
    mutate(document)
    store.path.write_text(json.dumps(document, indent=2), encoding="utf-8")


def _observed_store(tmp_path: Path) -> ShadowEvidenceStore:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    clock = Clock(activation)
    observer = service(
        tmp_path,
        clock,
        SyntheticAnalysis(
            {
                datetime(2026, 9, 16, 11, tzinfo=UTC): "NO_TRADE",
                datetime(2026, 9, 16, 12, tzinfo=UTC): "NO_TRADE",
            }
        ),
    )
    activate_at(observer, activation)
    observe(observer, clock, datetime(2026, 9, 16, 11, tzinfo=UTC))
    observe(observer, clock, datetime(2026, 9, 16, 12, tzinfo=UTC))
    return observer.evidence_store


def test_audit_payload_modification_is_detected(tmp_path: Path) -> None:
    store = _observed_store(tmp_path)

    def mutate(document: dict[str, Any]) -> None:
        document["audit_chain"][0]["payload_digest"] = "00" * 32

    _tamper(store, mutate)
    with pytest.raises(ShadowObserverError, match=INTEGRITY_ERROR):
        store.load()


def test_audit_reordering_is_detected(tmp_path: Path) -> None:
    store = _observed_store(tmp_path)

    def mutate(document: dict[str, Any]) -> None:
        chain = document["audit_chain"]
        chain[0], chain[1] = chain[1], chain[0]

    _tamper(store, mutate)
    with pytest.raises(ShadowObserverError, match=INTEGRITY_ERROR):
        store.load()


def test_audit_deletion_is_detected(tmp_path: Path) -> None:
    store = _observed_store(tmp_path)

    def mutate(document: dict[str, Any]) -> None:
        del document["audit_chain"][0]

    _tamper(store, mutate)
    with pytest.raises(ShadowObserverError, match=INTEGRITY_ERROR):
        store.load()


def test_duplicate_audit_sequence_is_detected(tmp_path: Path) -> None:
    store = _observed_store(tmp_path)

    def mutate(document: dict[str, Any]) -> None:
        chain = document["audit_chain"]
        chain.insert(1, dict(chain[0]))

    _tamper(store, mutate)
    with pytest.raises(ShadowObserverError, match=INTEGRITY_ERROR):
        store.load()


def test_snapshot_inconsistent_with_its_latest_event_is_detected(tmp_path: Path) -> None:
    """A silent edit to the snapshot alone can no longer pass as genuine evidence."""
    store = _observed_store(tmp_path)

    def mutate(document: dict[str, Any]) -> None:
        document["decisions"][0]["decision"] = "LONG"

    _tamper(store, mutate)
    with pytest.raises(ShadowObserverError, match=INTEGRITY_ERROR):
        store.load()


def test_deleted_snapshot_record_leaves_an_orphaned_event(tmp_path: Path) -> None:
    store = _observed_store(tmp_path)

    def mutate(document: dict[str, Any]) -> None:
        del document["decisions"][0]

    _tamper(store, mutate)
    with pytest.raises(ShadowObserverError, match=INTEGRITY_ERROR):
        store.load()


def test_integrity_failure_fails_closed_without_rewriting_evidence(tmp_path: Path) -> None:
    store = _observed_store(tmp_path)

    def mutate(document: dict[str, Any]) -> None:
        document["decisions"][0]["decision"] = "LONG"

    _tamper(store, mutate)
    corrupted = store.path.read_bytes()

    clock = Clock(datetime(2026, 9, 16, 13, tzinfo=UTC))
    analysis = SyntheticAnalysis({datetime(2026, 9, 16, 13, tzinfo=UTC): "LONG"})
    observer = service(tmp_path, clock, analysis)
    overview = observer.activate(now=clock.value)

    assert overview["status"] == "DEGRADED"
    assert overview["evidence_integrity"] == "INVALID"
    assert INTEGRITY_ERROR in overview["current_error"]
    assert overview["completed_shadow_trades"] is None
    with pytest.raises(ShadowObserverError, match="not activated"):
        observer.tick(now=clock.value)
    assert analysis.calls == []
    assert store.path.read_bytes() == corrupted


def test_restart_preserves_the_audit_chain(tmp_path: Path) -> None:
    store = _observed_store(tmp_path)
    before = store.load()["audit_chain"]

    restart = datetime(2026, 9, 16, 12, 30, tzinfo=UTC)
    clock = Clock(restart)
    restarted = service(tmp_path, clock)
    activate_at(restarted, restart)

    after = restarted.evidence_store.load()["audit_chain"]
    assert after[: len(before)] == before
    audit_chain.validate_chain(after)


def test_snapshot_and_audit_chain_share_one_atomic_document(tmp_path: Path) -> None:
    """A crash cannot leave the chain describing one state and the snapshot another."""
    store = _observed_store(tmp_path)
    document = json.loads(store.path.read_text(encoding="utf-8"))
    assert {"decisions", "trades", "audit_chain"} <= set(document)
    assert document["audit_chain_version"] == audit_chain.AUDIT_CHAIN_VERSION
    assert not list(store.path.parent.glob("*.staging"))


# --- frozen scientific semantics --------------------------------------------------


def test_v1_1_changes_no_scientific_semantics(tmp_path: Path) -> None:
    activation = datetime(2026, 9, 16, 10, 30, tzinfo=UTC)
    boundary = datetime(2026, 9, 16, 11, tzinfo=UTC)
    entry = boundary + MINUTE
    clock = Clock(activation)
    feed = SyntheticMinuteFeed([minute(entry)])
    observer = service(tmp_path, clock, SyntheticAnalysis({boundary: "LONG"}), feed)
    activate_at(observer, activation)
    observe(observer, clock, boundary)
    clock.value = entry + timedelta(minutes=2)
    observer.tick(now=clock.value)

    trade = observer.evidence_store.load()["trades"][0]
    projection = trade_projection(trade)
    assert projection["stop_fraction"] == 0.02
    assert projection["target_fraction"] == 0.04
    assert projection["max_hold_minutes"] == 1440
    assert projection["ambiguous_fill_policy"] == "STOP_FIRST_V1"
    assert projection["cost_model_version"] == "BTCUSDT_SPOT_COST_V1"
    assert projection["direction"] == "LONG"
    assert trade["entry_price"] == 100.0
    assert trade["stop_price"] == 98.0
    assert trade["target_price"] == 104.0
    assert trade["leverage"] is False and trade["short"] is False
    assert trade["order_placed"] is False and trade["real_money"] is False

    overview = observer.overview()
    assert overview["first_scientific_review_completed_trades"] == 20
    assert overview["champion_status"] == "NONE"
    assert overview["real_money"] is False
    assert overview["supersedes"] == "FUTURE_SHADOW_PAPER_EVIDENCE_V1"
    assert overview["supersedes_status"] == "IMPLEMENTED_SUPERSEDED_BEFORE_FIRST_REAL_OBSERVATION"


def test_manual_paper_v2_is_untouched_by_the_hardening() -> None:
    assert MANUAL_EVIDENCE_VERSION == "FUTURE_PAPER_EVIDENCE_V2"
    assert MANUAL_STORE_PATH == "data/paper/PAPER_TRADES_V2.json"
    assert EVIDENCE_STORE_PATH != MANUAL_STORE_PATH
    assert HEALTH_STORE_PATH != MANUAL_STORE_PATH
    assert LEASE_PATH != MANUAL_STORE_PATH
    manual = (ROOT / "backend/app/product/paper_v2.py").read_bytes().replace(b"\r\n", b"\n")
    assert (
        hashlib.sha256(manual).hexdigest()
        == "1a219b66f88a66cb727cfc956aabe0edb15da287711ffe7a469a48011dd45025"
    )


# --- runtime artifacts must not dirty the scientific build ------------------------


def porcelain(*entries: str) -> str:
    return "\n".join(entries)


def test_observer_health_runtime_state_does_not_dirty_provenance() -> None:
    """The observed bug: the observer wrote its own health store and unverified itself."""
    status = porcelain(f"AM {HEALTH_STORE_PATH}")
    assert semantic_changes(status, RUNTIME_ARTIFACTS) == []
    assert is_governed_runtime_artifact(HEALTH_STORE_PATH, RUNTIME_ARTIFACTS)


def test_scientific_evidence_runtime_json_does_not_dirty_provenance() -> None:
    status = porcelain(f"?? {EVIDENCE_STORE_PATH}", f" M {EVIDENCE_STORE_PATH}")
    assert semantic_changes(status, RUNTIME_ARTIFACTS) == []


def test_lock_lease_and_staging_files_do_not_dirty_provenance() -> None:
    status = porcelain(
        f"?? {LEASE_PATH}",
        f"?? {EVIDENCE_STORE_PATH}.lock",
        f"?? {HEALTH_STORE_PATH}.lock",
        "?? data/paper/tmp8ac21f.staging",
        "?? data/paper/PAPER_TRADES_V2.json",
    )
    assert semantic_changes(status, RUNTIME_ARTIFACTS) == []


def test_semantic_source_modification_does_invalidate_provenance() -> None:
    for member in manifest_members(EVIDENCE_CONTRACT):
        status = porcelain(f" M {member}")
        assert semantic_changes(status, RUNTIME_ARTIFACTS) == [member], member


def test_evidence_contract_modification_does_invalidate_provenance() -> None:
    status = porcelain(f" M {EVIDENCE_CONTRACT}")
    assert semantic_changes(status, RUNTIME_ARTIFACTS) == [EVIDENCE_CONTRACT]
    assert not is_governed_runtime_artifact(EVIDENCE_CONTRACT, RUNTIME_ARTIFACTS)


def test_arbitrary_unrelated_tracked_source_modification_still_invalidates() -> None:
    unrelated = (
        " M scripts/check.py",
        " M backend/app/main.py",
        " M state/current_state.json",
        " M frontend/src/App.tsx",
        "?? backend/app/product/rogue.py",
        " M data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json",
        " M .gitignore",
    )
    for entry in unrelated:
        assert semantic_changes(porcelain(entry), RUNTIME_ARTIFACTS) == [entry[3:]], entry


def test_renamed_source_is_judged_by_its_destination() -> None:
    status = porcelain(f"R  docs/old.md -> {EVIDENCE_CONTRACT}")
    assert semantic_changes(status, RUNTIME_ARTIFACTS) == [EVIDENCE_CONTRACT]


def test_a_failed_git_invocation_is_never_a_clean_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.product.provenance._git", lambda *_: None)
    record = repository_provenance(
        observer_version=OBSERVER_VERSION,
        evidence_version=EVIDENCE_VERSION,
        contract_path=EVIDENCE_CONTRACT,
        runtime_artifacts=RUNTIME_ARTIFACTS,
    )
    assert record["worktree_clean"] is False
    assert record["verified"] is False
    assert record["unverified_reason"] == UNVERIFIED_REASON


def test_the_real_observer_declares_its_runtime_artifacts() -> None:
    assert RUNTIME_ARTIFACTS == {EVIDENCE_STORE_PATH, HEALTH_STORE_PATH, LEASE_PATH}
    record = default_observer().build_provenance()
    assert record["provenance_version"] == PROVENANCE_VERSION
    assert "unverified_paths" in record
    # Whatever the local tree looks like, no observer runtime store may be a reason.
    assert not any(
        is_governed_runtime_artifact(path, RUNTIME_ARTIFACTS) for path in record["unverified_paths"]
    )


def test_production_runtime_stores_are_ignored_and_untracked() -> None:
    """Git-native protection: the runtime stores can never be offered for staging."""
    runtime = (
        EVIDENCE_STORE_PATH,
        HEALTH_STORE_PATH,
        LEASE_PATH,
        MANUAL_STORE_PATH,
        "data/paper/FUTURE_SHADOW_PAPER_EVIDENCE_V1.json",
        "data/paper/PROSPECTIVE_SHADOW_OBSERVER_HEALTH_V1.json",
        "data/paper/anything.lock",
        "data/paper/anything.staging",
    )
    for path in runtime:
        assert _git_ignores(path), path

    tracked = subprocess.run(
        ["git", "ls-files", "data/paper/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert tracked == "", tracked

    # Source, contracts and governance must stay visible to Git.
    for path in (
        *manifest_members(EVIDENCE_CONTRACT),
        "scripts/check.py",
        "state/current_state.json",
    ):
        assert not _git_ignores(path), path


def test_runtime_code_never_mutates_the_git_index() -> None:
    forbidden = ("git add", "git commit", "git stash", "update-index", "write-tree")
    for source in (ROOT / "backend" / "app").rglob("*.py"):
        text = source.read_text(encoding="utf-8").lower()
        for phrase in forbidden:
            assert phrase not in text, f"{source}: {phrase}"
        if source.name == "provenance.py":
            # Provenance may only read repository state.
            assert '"rev-parse"' in text or "rev-parse" in text
            assert '"add"' not in text and '"commit"' not in text
    dev = (ROOT / "scripts" / "dev.py").read_text(encoding="utf-8").lower()
    assert "git" not in dev


def test_prospective_runtime_fix_changes_no_scientific_state() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert state["experiments_completed"] == 26
    assert state["observed_material_historical_hypotheses"] == 12
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False
    assert state["historical_discovery_status"] == "PAUSED"
    assert state["prospective_counters"]["prospective_shadow_trades_completed"] == 0
    observer = state["prospective_shadow_observer"]
    assert observer["stop_fraction"] == 0.02
    assert observer["target_fraction"] == 0.04
    assert observer["maximum_hold_minutes"] == 1440
    assert observer["cost_model_version"] == "BTCUSDT_SPOT_COST_V1"
    assert observer["first_scientific_review_completed_trades"] == 20


# --- BUILD_PROVENANCE_V1_1 frozen semantic manifest --------------------------------

# The bounded code closure that can materially change the signal, the live input, causal
# execution, costs, prospective admissibility, evidence integrity, or the observer
# lifecycle. Pinned so a member cannot silently disappear from the identity.
FROZEN_MANIFEST_MEMBERS = frozenset(
    {
        "backend/app/main.py",
        "backend/app/product/__init__.py",
        "backend/app/product/analysis.py",
        "backend/app/product/features.py",
        "backend/app/research/continuation.py",
        "backend/app/product/market_feed.py",
        "backend/app/product/execution_v2.py",
        "backend/app/product/shadow_observer.py",
        "backend/app/product/provenance.py",
        "backend/app/product/audit_chain.py",
        "backend/app/product/observer_lease.py",
        "backend/app/product/platform_file_io.py",
        "backend/app/backtest/models.py",
        "backend/app/backtest/__init__.py",
        "docs/contracts/FUTURE_SHADOW_PAPER_EVIDENCE_V1_1.md",
    }
)


def test_no_genuine_observation_exists_before_manifest_closure() -> None:
    assert not (ROOT / EVIDENCE_STORE_PATH).exists()
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert state["prospective_collection"]["genuine_observations"] == 0
    assert state["prospective_counters"] == {
        "prospective_observation_hours": 0,
        "prospective_long_signals": 0,
        "prospective_suppressed_signals": 0,
        "prospective_shadow_trades_open": 0,
        "prospective_shadow_trades_completed": 0,
    }


def test_build_provenance_v1_1_is_required_and_v1_is_superseded() -> None:
    assert PROVENANCE_VERSION == "BUILD_PROVENANCE_V1_1"
    assert SUPERSEDED_PROVENANCE_VERSION == "BUILD_PROVENANCE_V1"
    assert SUPERSEDED_PROVENANCE_STATUS == "SUPERSEDED_BEFORE_FIRST_REAL_OBSERVATION"

    record = default_observer().build_provenance()
    assert record["provenance_version"] == "BUILD_PROVENANCE_V1_1"
    assert record["supersedes"] == "BUILD_PROVENANCE_V1"
    assert record["supersedes_status"] == "SUPERSEDED_BEFORE_FIRST_REAL_OBSERVATION"

    # A record written under the superseded version is no longer admissible.
    stale = synthetic_provenance(provenance_version="BUILD_PROVENANCE_V1")
    with pytest.raises(ProvenanceError, match="unsupported build provenance version"):
        provenance_validate(stale)

    contract = (ROOT / EVIDENCE_CONTRACT).read_text(encoding="utf-8")
    assert "BUILD_PROVENANCE_V1_1" in contract
    assert "SUPERSEDED_BEFORE_FIRST_REAL_OBSERVATION" in contract


def test_the_semantic_manifest_member_set_is_pinned() -> None:
    """A required member cannot silently disappear from the scientific identity."""
    members = manifest_members(EVIDENCE_CONTRACT)
    assert set(members) == FROZEN_MANIFEST_MEMBERS
    assert len(members) == len(FROZEN_MANIFEST_MEMBERS) == 15
    assert set(semantic_manifest(EVIDENCE_CONTRACT)) == FROZEN_MANIFEST_MEMBERS
    for member in FROZEN_MANIFEST_MEMBERS:
        assert (ROOT / member).is_file(), member


@pytest.mark.parametrize(
    "member",
    [
        "backend/app/product/provenance.py",
        "backend/app/product/audit_chain.py",
        "backend/app/product/observer_lease.py",
        "backend/app/product/platform_file_io.py",
        "backend/app/product/features.py",
        "backend/app/product/market_feed.py",
        "backend/app/main.py",
    ],
)
def test_integrity_and_input_dependencies_are_manifest_members(member: str) -> None:
    assert member in manifest_members(EVIDENCE_CONTRACT)


def test_changing_each_manifest_member_changes_the_aggregate_identity() -> None:
    """Identity must not rest on git HEAD alone: every member's bytes move the SHA."""
    manifest = semantic_manifest(EVIDENCE_CONTRACT)
    baseline = aggregate_sha256(manifest)
    seen = set()
    for member in manifest:
        altered = {**manifest, member: "00" * 32}
        identity = aggregate_sha256(altered)
        assert identity != baseline, member
        assert identity not in seen, member
        seen.add(identity)
    assert len(seen) == len(FROZEN_MANIFEST_MEMBERS)

    # Dropping a member must also move the identity, not merely altering one.
    for member in manifest:
        reduced = {key: value for key, value in manifest.items() if key != member}
        assert aggregate_sha256(reduced) != baseline, member


def test_the_provenance_version_itself_binds_the_aggregate() -> None:
    manifest = semantic_manifest(EVIDENCE_CONTRACT)
    payload = "\n".join(f"{m}:{d}" for m, d in sorted(manifest.items()))
    under_v1 = hashlib.sha256(f"BUILD_PROVENANCE_V1\n{payload}\n".encode()).hexdigest()
    assert aggregate_sha256(manifest) != under_v1


def test_a_frozen_manifest_member_is_never_exempted_as_runtime_state() -> None:
    """No runtime path rule may hide a change to the code that defines the science."""
    protected = frozenset(manifest_members(EVIDENCE_CONTRACT))
    # Pretend a future rule wrongly lists every member as a runtime artifact.
    hostile = frozenset(protected)
    for member in protected:
        status = f" M {member}"
        assert semantic_changes(status, hostile, protected) == [member], member
        assert not is_governed_runtime_artifact(member, hostile, protected), member


def test_runtime_artifacts_still_do_not_affect_the_clean_verdict() -> None:
    protected = frozenset(manifest_members(EVIDENCE_CONTRACT))
    runtime = (
        EVIDENCE_STORE_PATH,
        HEALTH_STORE_PATH,
        LEASE_PATH,
        MANUAL_STORE_PATH,
        "data/paper/anything.lock",
        "data/paper/anything.lease",
        "data/paper/tmp1234.staging",
    )
    for path in runtime:
        assert semantic_changes(f"?? {path}", RUNTIME_ARTIFACTS, protected) == [], path
        assert semantic_changes(f" M {path}", RUNTIME_ARTIFACTS, protected) == [], path


def test_arbitrary_tracked_source_outside_runtime_state_still_unverifies() -> None:
    protected = frozenset(manifest_members(EVIDENCE_CONTRACT))
    outside = (
        "scripts/check.py",
        "state/current_state.json",
        "frontend/src/App.tsx",
        "contracts/project_state.schema.json",
        "backend/app/product/paper_v2.py",
        "backend/app/research/local_runner.py",
        "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json",
        ".gitignore",
    )
    for path in outside:
        assert semantic_changes(f" M {path}", RUNTIME_ARTIFACTS, protected) == [path], path


def test_manifest_closure_changed_no_scientific_semantics() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    observer = state["prospective_shadow_observer"]
    assert observer["strategy_version"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    assert observer["stop_fraction"] == 0.02
    assert observer["target_fraction"] == 0.04
    assert observer["maximum_hold_minutes"] == 1440
    assert observer["ambiguous_fill_policy"] == "STOP_FIRST_V1"
    assert observer["cost_model_version"] == "BTCUSDT_SPOT_COST_V1"
    assert observer["entry_timing_rule"] == "STRICTLY_AFTER_DURABLE_INTENT_NEXT_1M_OPEN"
    assert observer["first_scientific_review_completed_trades"] == 20
    assert observer["evidence_version"] == "FUTURE_SHADOW_PAPER_EVIDENCE_V1_1"
    assert state["experiments_completed"] == 26
    assert state["observed_material_historical_hypotheses"] == 12
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False


def test_manual_paper_v2_still_byte_frozen_after_closure() -> None:
    manual = (ROOT / "backend/app/product/paper_v2.py").read_bytes().replace(b"\r\n", b"\n")
    assert (
        hashlib.sha256(manual).hexdigest()
        == "1a219b66f88a66cb727cfc956aabe0edb15da287711ffe7a469a48011dd45025"
    )
    assert "backend/app/product/paper_v2.py" not in manifest_members(EVIDENCE_CONTRACT)
