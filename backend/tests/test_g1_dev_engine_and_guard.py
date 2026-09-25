"""System G1 Development V1: engine integration, staged selection lock, execution guard, sources."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from app.g1 import batch, dev_fixtures, scoring
from app.g1.clock import ReplayController
from app.g1.development import (
    COST_STRESS,
    DevelopmentEngine,
    development_manifest,
    drive,
    primary_book,
    stress_books,
)
from app.g1.forecaster import PROBABILITY_STATUS
from app.g1.playbooks import CONFIGURATIONS
from app.g1.records import DecisionSnapshot, FillKind, PredictionSnapshot, Side, TradePlan
from app.g1.sources import RealSourceHandle, SourceBindingError, binding_identity, parse_kline_csv

ROOT = Path(__file__).resolve().parents[2]
BARS = dev_fixtures.synthetic_path()
FUNDING = dev_fixtures.synthetic_funding()
START, END = dev_fixtures.START, dev_fixtures.END


def engine_for(books, bars=BARS, end=END, display=None, retain=True) -> DevelopmentEngine:
    manifest = development_manifest(
        (("synthetic", dev_fixtures.path_hash(bars)),),
        START,
        end,
        tuple(books),
        batch.SYNTHETIC_EVIDENCE,
        "test",
    )
    engine = DevelopmentEngine(
        manifest, books, FUNDING, display_book=display, retain_records=retain
    )
    return drive(engine, [b for b in bars if b.available_at <= end])


@pytest.fixture(scope="module")
def seven() -> DevelopmentEngine:
    books = tuple(primary_book(c, START, END) for c in CONFIGURATIONS)
    return engine_for(books, display="S0:PRIMARY")


def test_every_issue_gets_one_forecast_and_the_training_boundary_is_annual(seven) -> None:
    expected = int((END - START) / timedelta(minutes=15))
    assert seven.issues == len(seven.forecasts) == expected
    in_2000 = [r for r in seven.forecasts if r.issue_time.year == 2000]
    in_2001 = [r for r in seven.forecasts if r.issue_time.year == 2001]
    assert not any(r.available for r in in_2000)  # no prior training year
    assert sum(r.available for r in in_2001) > 0.9 * len(in_2001)
    predictions = seven.store.of_type(PredictionSnapshot)
    assert {p.probability_status for p in predictions if p.issue_time.year == 2001} >= {
        PROBABILITY_STATUS
    }
    assert {p.unavailable_reason for p in predictions if p.issue_time.year == 2000} >= {
        "NO_TRAINING_OBSERVATIONS"
    }
    for p in predictions:
        assert p.target_end == p.issue_time + timedelta(hours=4)
        assert p.actionability.final_decision.value == "NO_TRADE"  # prediction never gates trades


def test_books_share_recognition_and_differ_only_by_configuration(seven) -> None:
    counts = {book.spec.config_id: book.decisions for book in seven.books.values()}
    assert len(set(counts.values())) == 1
    only_full = engine_for((primary_book("S_FULL", START, END),), retain=False)
    assert only_full.forecasts == seven.forecasts  # forecasts/conviction never depend on books
    assert (
        only_full.books["S_FULL:PRIMARY"].ledger.trades
        == seven.books["S_FULL:PRIMARY"].ledger.trades
    )
    s0 = seven.books["S0:PRIMARY"].ledger.trades
    assert {t.playbook_id for t in s0} == {
        "SYSTEM-G1-P1-DIRECTIONAL-CONTINUATION",
        "SYSTEM-G1-P2-FAILED-AUCTION-REENTRY",
    }
    assert {t.side for t in s0} == {Side.LONG, Side.SHORT}


def test_long_short_execution_uses_the_frozen_plan_and_1m_delay(seven) -> None:
    plans = {p.trade_plan_id: p for p in seven.store.of_type(TradePlan)}
    decisions = {d.decision_id: d for d in seven.store.of_type(DecisionSnapshot)}
    assert plans
    entries = [f for f in seven.books["S0:PRIMARY"].ledger.events if f.kind is FillKind.ENTRY]
    for fill in entries:
        plan = plans[fill.trade_plan_id]
        assert fill.event_time == plan.readiness_time + timedelta(minutes=1)
        decision = decisions[plan.decision_id]
        assert decision.action.value == plan.side.value
        if plan.playbook_id.endswith("CONTINUATION"):
            assert plan.planned_reward_risk == Decimal("2.0000")
        else:
            assert plan.planned_reward_risk >= Decimal("1.5")
        assert plan.side.sign * (plan.objective_price - plan.reference_price) > 0
        assert plan.side.sign * (plan.reference_price - plan.stop_price) > 0
    for trade in seven.books["S0:PRIMARY"].ledger.trades:
        assert trade.holding_minutes <= 240


def test_engine_is_causal_future_minutes_never_change_past_records(seven) -> None:
    cut = datetime(2000, 12, 20, tzinfo=UTC)
    partial = engine_for(
        tuple(primary_book(c, START, END) for c in CONFIGURATIONS), end=cut, display="S0:PRIMARY"
    )
    early = [r for r in seven.forecasts if r.issue_time <= cut - timedelta(hours=4)]
    assert partial.forecasts[: len(early)] == early

    def content(d):  # identities embed the run manifest (its end differs); compare content
        return (d.decision_time, d.action, d.blockers, d.conviction, d.playbook_id, d.actionability)

    full_decisions = [
        content(d) for d in seven.store.of_type(DecisionSnapshot) if d.decision_time <= cut
    ]
    assert [content(d) for d in partial.store.of_type(DecisionSnapshot)] == full_decisions


def test_replay_speed_and_batching_invariance_for_the_development_engine() -> None:
    end = START + timedelta(days=8)
    bars = tuple(b for b in BARS if b.available_at <= end)
    books = (primary_book("S0", START, end),)
    reference = engine_for(books, bars, end)
    manifest = reference.manifest
    replay = DevelopmentEngine(manifest, books, FUNDING)
    controller = ReplayController(replay, bars)
    controller.set_speed(14400)
    controller.run_to_end(pace=lambda: 0.37)
    assert replay.fingerprint() == reference.fingerprint()


def test_stress_books_are_the_two_frozen_views() -> None:
    cost, delay = stress_books("S_FULL", START, END)
    assert (
        cost.costs == COST_STRESS and cost.costs.entry_fee_bps + cost.costs.entry_friction_bps == 24
    )
    assert delay.policy.operational_delay_minutes == 6 and delay.costs.profile.startswith("BTCUSDT")


# ------------------------------------------------------------------ guard / stages
def windows() -> batch.PhaseWindows:
    return batch.PhaseWindows(
        START,
        datetime(2000, 12, 12, tzinfo=UTC),
        datetime(2001, 1, 1, tzinfo=UTC),
        datetime(2001, 1, 1, tzinfo=UTC),
        END,
        (2000,),
        (2001,),
    )


def source() -> batch.SyntheticSource:
    return batch.SyntheticSource(
        BARS, FUNDING, windows(), {"synthetic": dev_fixtures.path_hash(BARS)}
    )


def _live_record() -> dict:
    state = json.loads((ROOT / batch.STATE_PATH).read_text(encoding="utf-8"))
    return state[batch.STATE_KEY]


def test_canonical_state_guard_is_phase_scoped() -> None:
    """Only the phase the canonical state authorizes is accepted; Phase B is refused now.

    This test never opens market observations: constructing a handle reads manifest metadata only,
    and the subprocess only ever requests Phase B.
    """
    record = _live_record()
    for phase in ("A", "B"):
        allowed = (
            record.get("historical_execution_authorized") is True
            and record.get("authorized_phase") == phase
        )
        if allowed:
            handle = batch.authorize_real_sources(phase, ROOT)
            assert handle.phase == phase
        else:
            with pytest.raises(batch.ExecutionNotAuthorized):
                batch.authorize_real_sources(phase, ROOT)
    with pytest.raises(batch.ExecutionNotAuthorized):
        batch.authorize_real_sources("B", ROOT)  # ADR-0048: never Phase B
    with pytest.raises(PermissionError):
        RealSourceHandle(ROOT, "x", object(), "A")
    completed = subprocess.run(
        [sys.executable, "scripts/run_g1_development.py", "--phase", "B"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0 and "REFUSED" in completed.stderr
    assert not (ROOT / batch.RUN_DIR / batch.EVALUATION_FILE).exists()


def _authorization_root(tmp_path: Path, record: dict, adr: bool = True) -> Path:
    for path in ("data/manifests", "state", "decisions"):
        (tmp_path / path).mkdir(parents=True, exist_ok=True)
    for manifest in (
        "BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1.json",
        "BTCUSDT-USDM-FUNDING-DEV-v1.json",
    ):
        shutil.copy(ROOT / "data/manifests" / manifest, tmp_path / "data/manifests" / manifest)
    if adr:
        (tmp_path / "decisions/ADR-X.md").write_text("authorized", encoding="utf-8")
    state = {batch.STATE_KEY: record}
    (tmp_path / batch.STATE_PATH).write_text(json.dumps(state), encoding="utf-8")
    return tmp_path


ARMED_A = {
    "historical_execution_authorized": True,
    "execution_authorization_record": "decisions/ADR-X.md",
    "authorized_phase": "A",
}


def test_phase_a_is_accepted_only_with_an_explicit_phase_and_record(tmp_path) -> None:
    root = _authorization_root(tmp_path, ARMED_A)
    handle = batch.authorize_real_sources("A", root)
    assert isinstance(handle, RealSourceHandle) and handle.phase == "A"
    assert handle.identity["market_observations_read"] is False
    with pytest.raises(batch.ExecutionNotAuthorized):
        batch.authorize_real_sources("B", root)
    with pytest.raises(batch.ExecutionNotAuthorized):
        batch.authorize_real_sources("C", root)


@pytest.mark.parametrize(
    ("record", "adr"),
    [
        ({**ARMED_A, "authorized_phase": None}, True),
        ({**ARMED_A, "authorized_phase": "B"}, True),
        ({**ARMED_A, "authorized_phase": "a"}, True),
        ({k: v for k, v in ARMED_A.items() if k != "authorized_phase"}, True),
        ({**ARMED_A, "historical_execution_authorized": False}, True),
        ({**ARMED_A, "execution_authorization_record": None}, True),
        (ARMED_A, False),
    ],
    ids=[
        "null-phase",
        "wrong-phase",
        "lowercase",
        "no-phase",
        "disarmed",
        "no-record",
        "missing-adr",
    ],
)
def test_phase_a_is_refused_without_every_authorization_condition(tmp_path, record, adr) -> None:
    root = _authorization_root(tmp_path, record, adr)
    with pytest.raises(batch.ExecutionNotAuthorized):
        batch.authorize_real_sources("A", root)


def test_a_phase_a_handle_can_never_drive_phase_b(tmp_path) -> None:
    root = _authorization_root(tmp_path, ARMED_A)
    handle = batch.authorize_real_sources("A", root)
    with pytest.raises(batch.ExecutionNotAuthorized):
        batch.run_phase_b(handle, root / batch.RUN_DIR, root)
    fake = type("Handle", (), {"phase": "B"})()
    with pytest.raises(batch.ExecutionNotAuthorized):
        batch.run_phase_a(fake, root / batch.RUN_DIR, root)


def test_phase_b_refuses_without_selection_and_synthetic_never_writes_to_the_run_dir(
    tmp_path,
) -> None:
    with pytest.raises(batch.StageLockError):
        batch.run_phase_b(source(), tmp_path)
    with pytest.raises(batch.StageLockError):
        batch.run_phase_a(source(), ROOT / batch.RUN_DIR)


def test_phase_a_no_eligible_configuration_makes_phase_b_impossible(tmp_path) -> None:
    artifact = batch.run_phase_a(source(), tmp_path)
    assert artifact["configurations_inspected"] == list(CONFIGURATIONS)
    assert artifact["selected_configuration"] is None
    assert (
        artifact["disposition"] == scoring.REJECTED_SELECTION
        and artifact["phase_b_possible"] is False
    )
    with pytest.raises(batch.StageLockError, match="impossible"):
        batch.run_phase_b(source(), tmp_path)
    with pytest.raises(batch.StageLockError, match="already"):
        batch.run_phase_a(source(), tmp_path)


def _eligible_table():
    from test_g1_dev_forecaster_scoring import result, trade

    trades = [trade(i, "10" if i % 3 else "-5", 2000) for i in range(45)]
    return scoring.phase_a_table([result("S_P2_ONLY", trades), result("S0", trades[:30])], (2000,))


def test_phase_b_uses_only_the_automatic_selection_and_detects_tampering(tmp_path) -> None:
    written = batch.write_selection(tmp_path, source(), _eligible_table())
    assert written["selected_configuration"] == "S_P2_ONLY"
    evaluation = batch.run_phase_b(source(), tmp_path)
    assert evaluation["selected_configuration"] == "S_P2_ONLY"
    assert set(evaluation["metrics"]) == {
        "S_P2_ONLY:PRIMARY",
        "S_P2_ONLY:COST_48BP",
        "S_P2_ONLY:DELAY_PLUS_5M",
    }
    assert evaluation["disposition"] in scoring.DISPOSITION_ORDER
    with pytest.raises(batch.StageLockError, match="already"):
        batch.run_phase_b(source(), tmp_path)
    tampered = tmp_path / "tampered"
    tampered.mkdir()
    batch.write_selection(tampered, source(), _eligible_table())
    path = tampered / batch.SELECTION_FILE
    data = json.loads(path.read_text(encoding="utf-8"))
    data["selected_configuration"] = "S_FULL"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(batch.StageLockError, match="modified"):
        batch.run_phase_b(source(), tampered)
    import inspect

    assert "config" not in "".join(inspect.signature(batch.run_phase_b).parameters)


# ------------------------------------------------------------------ source bindings
HEADER = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore"


def test_kline_parser_reads_every_g1_field_and_leaves_invalid_rows_missing() -> None:
    ms = 1609459200000  # 2021-01-01T00:00Z
    rows = [
        HEADER,
        f"{ms},100,101,99,100.5,2.5,{ms + 59999},251.2,10,1.5,150.7,0",
        f"{ms + 60000},100,99,101,100,1,{ms + 119999},100,1,0.5,50,0",  # inconsistent OHLC
        f"{ms + 120001},100,101,99,100,1,{ms + 180000},100,1,0.5,50,0",  # off grid
        f"{ms + 180000},100,101,99,nan,1,{ms + 239999},100,1,0.5,50,0",  # non-finite
    ]
    bars = list(parse_kline_csv("\n".join(rows)))
    assert len(bars) == 1
    [bar] = bars
    assert bar.open_time == datetime(2021, 1, 1, tzinfo=UTC)
    assert (bar.volume, bar.quote_volume, bar.taker_buy_base_volume) == (
        Decimal("2.5"),
        Decimal("251.2"),
        Decimal("1.5"),
    )
    with pytest.raises(SourceBindingError):
        list(parse_kline_csv("1,2,3"))
    late = 1735689600000  # 2025-01-01
    with pytest.raises(SourceBindingError):
        list(parse_kline_csv(f"{late},1,1,1,1,1,{late + 59999},1,1,1,1,0"))


def test_source_bindings_are_identity_only_and_complete() -> None:
    identity = binding_identity(ROOT)
    klines = identity["reference_klines"]
    assert klines["market"] == "USDM_PERPETUAL" and klines["months"] == ["2020-01", "2024-12", 60]
    assert "taker_buy_volume" in klines["fields"] and "quote_volume" in klines["fields"]
    assert identity["funding"]["fields"] == ["funding_time", "funding_rate"]
    assert identity["spot_1m"]["status"].startswith("NOT_REQUIRED")
    assert identity["market_observations_read"] is False
