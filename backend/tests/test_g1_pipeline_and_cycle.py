"""System G1 Checkpoint 1: prediction/decision pipeline contract and cycle method evidence."""

from __future__ import annotations

import dataclasses
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from app.g1 import fixtures
from app.g1.core import G1Core, run_manifest, run_to_end
from app.g1.cycle import (
    CYCLE_DECISION_ACTIVATION,
    SCALES,
    AutocorrelationPeriodogram,
    CycleEngine,
    ScaleTracker,
)
from app.g1.cycle_reference import reference_acp
from app.g1.ledger import RiskPolicy
from app.g1.records import (
    Action,
    ClosedTrade,
    Conviction,
    CycleState,
    DecisionSnapshot,
    Direction,
    FillKind,
    MarketState,
    ModelArtifact,
    OrderFillEvent,
    PredictionRealization,
    PredictionSnapshot,
    Side,
    SignalRole,
    SignalSnapshot,
    TradePlan,
)

ROOT = Path(__file__).resolve().parents[2]
QUALIFIERS = {"CYCLE_SUPPORTS_LONG", "CYCLE_SUPPORTS_SHORT", "CYCLE_MIXED_OR_WEAK"}
BARS = fixtures.minute_path()
POLICY = RiskPolicy()
MANIFEST = run_manifest(BARS, fixtures.START, fixtures.END, POLICY)


def _core() -> G1Core:
    return G1Core(MANIFEST, fixtures.scenario_step, fixtures.FUNDING_RATES, POLICY)


@pytest.fixture(scope="module")
def run() -> G1Core:
    return run_to_end(_core(), BARS)


def _decision_at(run: G1Core, day: int, hhmm: str) -> DecisionSnapshot:
    hours, minutes = (int(x) for x in hhmm.split(":"))
    moment = fixtures.START + timedelta(days=day, hours=hours, minutes=minutes)
    return next(d for d in run.store.of_type(DecisionSnapshot) if d.decision_time == moment)


def test_prediction_contract_fields_and_links(run) -> None:
    store = run.store
    ids: dict[type, set] = {type(r): set() for r in store}
    for record in store:
        ids[type(record)].add(dataclasses.astuple(record)[0])
    predictions = store.of_type(PredictionSnapshot)
    assert {p.predicted_direction for p in predictions} == set(Direction)
    assert {p.conviction for p in predictions} == set(Conviction)
    for p in predictions:
        assert p.target_end == p.issue_time + timedelta(hours=4)
        assert p.information_cutoff == p.issue_time == p.available_at
        assert p.market_state_id in ids[MarketState] and p.cycle_state_id in ids[CycleState]
        assert p.model_artifact_id in ids[ModelArtifact]
        assert p.decision_timeframe == "15m"
        if p.predicted_direction is Direction.UNAVAILABLE:
            assert (
                p.unavailable_reason and p.probability_up is None and p.mean_terminal_return is None
            )
        else:
            assert p.probability_status.startswith("UNCALIBRATED")
            assert p.lower_quantile_return < p.median_terminal_return < p.upper_quantile_return
            assert p.standardized_strength is not None and p.prior_risk_scale is not None
    model = store.of_type(ModelArtifact)[0]
    assert model.fitted is False and model.training_interval is None
    assert len(model.conditioning_cells) == 9


def test_decision_fixtures_cover_the_required_cases(run) -> None:
    weak = _decision_at(run, 0, "15:00")
    assert weak.action is Action.NO_TRADE and "CONVICTION_NOT_HIGH" in weak.blockers
    occupied = _decision_at(run, 0, "06:30")
    assert occupied.conviction is Conviction.HIGH and occupied.action is Action.NO_TRADE
    assert occupied.blockers == ("POSITION_OCCUPIED",)
    assert occupied.actionability.setup_ready and not occupied.actionability.occupancy_free
    daily = _decision_at(run, 1, "08:00")
    assert daily.conviction is Conviction.HIGH and daily.blockers == ("DAILY_LOSS_ENTRY_STOP",)
    assert not daily.actionability.risk_eligible
    long_ = _decision_at(run, 0, "06:00")
    short = _decision_at(run, 0, "12:00")
    assert long_.action is Action.LONG and short.action is Action.SHORT
    assert long_.trade_plan_id and short.trade_plan_id and not long_.blockers
    conflict = _decision_at(run, 0, "14:30")
    assert conflict.action is Action.NO_TRADE and "CONFLICTING_PLAYBOOKS" in conflict.blockers
    missing = _decision_at(run, 1, "10:15")
    assert "DECISION_BAR_INCOMPLETE_OR_MISSING" in missing.blockers
    assert not missing.actionability.data_ready
    warmup = _decision_at(run, 0, "01:00")
    assert warmup.blockers[0] == "WARMUP_4H_CONTEXT_UNAVAILABLE"
    decisions = run.store.of_type(DecisionSnapshot)
    no_trade = [d for d in decisions if d.action is Action.NO_TRADE]
    assert len(no_trade) > 250  # NO_TRADE is persisted as first-class data
    plans = {p.trade_plan_id: p for p in run.store.of_type(TradePlan)}
    for decision in decisions:
        if decision.action is Action.NO_TRADE:
            assert decision.trade_plan_id is None and decision.blockers
        else:
            plan = plans[decision.trade_plan_id]
            assert plan.decision_id == decision.decision_id
            assert plan.side.value == decision.action.value
            assert (
                plan.max_hold_minutes <= 240
                and plan.planned_risk_amount == plan.virtual_equity * POLICY.risk_fraction
            )


def test_trade_path_exercises_objective_stop_expiry_funding_and_rejection(run) -> None:
    trades = run.store.of_type(ClosedTrade)
    reasons = {t.exit_reason for t in trades}
    assert {"OBJECTIVE", "STOP", "MAX_HOLD_EXPIRY"} <= reasons
    assert {t.side for t in trades} == {Side.LONG, Side.SHORT}
    fills = run.store.of_type(OrderFillEvent)
    assert any(f.reason == "REJECTED_MISSING_MINUTE" for f in fills)
    funding = [f for f in fills if f.kind is FillKind.FUNDING]
    assert any(f.side is Side.LONG and f.funding_amount < 0 for f in funding)
    assert any(f.side is Side.SHORT and f.funding_amount > 0 for f in funding)
    for trade in trades:
        # Next eligible minute after the decision plus the frozen 1m primary delay.
        assert trade.entry_time.minute % 15 == 1


def test_realizations_are_scored_only_after_maturity(run) -> None:
    realizations = run.store.of_type(PredictionRealization)
    predictions = {p.prediction_id: p for p in run.store.of_type(PredictionSnapshot)}
    validity = {r.resolution_validity for r in realizations}
    assert (
        validity == {"VALID", "UNSCORABLE_PREDICTION_UNAVAILABLE"}
        or "UNSCORABLE_MISSING_TERMINAL_MINUTE" in validity
    )
    for r in realizations:
        issued = predictions[r.prediction_id]
        if r.resolution_validity == "VALID" and issued.predicted_direction in (
            Direction.UP,
            Direction.DOWN,
        ):
            assert r.direction_correct is not None
        if issued.predicted_direction is Direction.NEUTRAL:
            assert r.direction_correct is None
        assert r.probability_score.startswith("NOT_SCORED")
    # Predictions within 4h of the end never mature inside the run.
    assert len(realizations) == len(predictions) - 16


def test_scenario_signals_are_diagnostic_and_cycle_states_are_active(run) -> None:
    """Checkpoint-1 scenario records: plumbing signals stay DIAGNOSTIC; since ADR-0046 every
    CycleState is an ACTIVE component carrying the frozen timing qualifier."""
    for signal in run.store.of_type(SignalSnapshot):
        assert signal.role is SignalRole.DIAGNOSTIC
    for state in run.store.of_type(CycleState):
        assert state.decision_role is SignalRole.ACTIVE
        assert state.timing_qualifier in QUALIFIERS
        for scale in state.scales:
            assert scale.quality_label in ("UNAVAILABLE", "WEAK", "USABLE")
    for state in run.store.of_type(MarketState):
        assert state.cycle_summary in QUALIFIERS
    assert CYCLE_DECISION_ACTIVATION is True


def test_cycle_state_has_no_influence_on_decisions(run, monkeypatch) -> None:
    """Replace every cycle snapshot with a maximal, 'confirmed-up', ACTIVE-looking state."""
    original = CycleEngine.snapshot

    def forged(self, run_id, decision_time):
        state = original(self, run_id, decision_time)
        return dataclasses.replace(
            state,
            cycle_state_id=state.cycle_state_id + "-FORGED",
            decision_role=SignalRole.ACTIVE,
            timing_qualifier="CYCLE_SUPPORTS_LONG",
        )

    def mutated(self, run_id, decision_time):
        state = forged(self, run_id, decision_time)
        scales = tuple(
            dataclasses.replace(
                s, slope_direction="RISING", coordinate=-1.0, quality_label="USABLE"
            )
            for s in state.scales
        )
        return dataclasses.replace(state, scales=scales)

    monkeypatch.setattr(CycleEngine, "snapshot", mutated)
    other = run_to_end(_core(), BARS)
    key = lambda d: (d.decision_time, d.action, d.blockers, d.conviction, d.playbook_id)
    assert [key(d) for d in other.store.of_type(DecisionSnapshot)] == [
        key(d) for d in run.store.of_type(DecisionSnapshot)
    ]


@pytest.mark.parametrize("scale", SCALES, ids=lambda s: s.nominal)
def test_streaming_acp_reconciles_with_the_independent_reference(scale) -> None:
    rng = np.random.default_rng(7)
    t = np.arange(420, dtype=float)
    values = 100 + 5 * np.sin(2 * np.pi * t / scale.nominal_samples) + rng.normal(0, 1, t.size)
    acp = AutocorrelationPeriodogram(scale.period1, scale.period2)
    stream = np.array(
        [
            np.nan if (o := acp.update(float(v))).dominant_period is None else o.dominant_period
            for v in values
        ]
    )
    _, reference = reference_acp(values, scale.period1, scale.period2)
    assert np.array_equal(np.isnan(stream), np.isnan(reference))
    assert np.nanmax(np.abs(stream - reference)) < 1e-9


def test_cycle_outputs_are_causal_prefix_invariant() -> None:
    scale = SCALES[0]
    t = np.arange(400, dtype=float)
    base = 100 + 5 * np.sin(2 * np.pi * t / 15)
    changed = base.copy()
    changed[300:] += 50 * np.cos(t[300:])  # rewrite the future only
    outputs = []
    for series in (base, changed):
        tracker = ScaleTracker(scale)
        start = datetime(2001, 1, 1, tzinfo=UTC)
        states = []
        for index, value in enumerate(series):
            opened = start + timedelta(minutes=3 * index)
            tracker.update(opened, opened + timedelta(minutes=3), float(value), True)
            states.append(tracker.state())
        outputs.append(states)
    assert outputs[0][:300] == outputs[1][:300]
    assert outputs[0][300:] != outputs[1][300:]


def test_warmup_gap_rewarm_and_turn_confirmation_timestamps() -> None:
    scale = SCALES[1]  # 3h on 15m bars
    tracker = ScaleTracker(scale)
    start = datetime(2001, 1, 1, tzinfo=UTC)
    step = timedelta(minutes=15)
    turns = set()
    for index in range(400):
        if index in (250, 251):
            continue
        opened = start + index * step
        tracker.update(opened, opened + step, 100 + 5 * math.sin(2 * math.pi * index / 12), True)
        state = tracker.state()
        if index < scale.warmup_bars - 1:
            assert (
                not state.warmup_ready
                and state.quality_label == "UNAVAILABLE"
                and state.dominant_period_bars is None
            )
        if 252 <= index < 252 + scale.warmup_bars - 1:
            assert state.gap_state == "REWARMING_AFTER_GAP" and not state.warmup_ready
        if state.last_confirmed_turn is not None:
            turns.add(state.last_confirmed_turn)
    assert tracker.state().warmup_ready
    assert turns and all(t.confirmation_time > t.estimated_turn_time for t in turns)
    assert all(t.confirmation_time - t.estimated_turn_time >= 2 * step for t in turns)
    incomplete = ScaleTracker(scale)
    incomplete.update(start, start + step, 100.0, False)
    assert incomplete.bars_seen == 0 and incomplete.gap_state == "REWARMING_AFTER_GAP"


def test_preserved_checkpoint_1_cycle_diagnostics_are_unchanged() -> None:
    """The IMPL-1 artifact is immutable history; ADR-0045 labels supersede its pending labels."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from build_g1_cycle_diagnostics import PRESERVED_V1_SHA256, preserved_sha256

    assert preserved_sha256() == PRESERVED_V1_SHA256
    path = ROOT / "reports/research/SYSTEM-G1-CYCLE-SYNTHETIC-DIAGNOSTICS-V1.json"
    content = path.read_bytes()
    artifact = json.loads(content)
    assert artifact["quality_thresholds_selected"] is False
    assert artifact["market_data_read"] is False and artifact["cycle_active_in_decisions"] is False
    assert artifact["reference_reconciliation_max_abs_period_diff"] < 1e-9
    assert [s["nominal_scale"] for s in artifact["scales"]] == ["45m", "3h", "1d", "4d", "1w", "4w"]
    for scale in artifact["scales"]:
        assert len(scale["fixtures"]) == 7
        for fixture in scale["fixtures"]:
            assert "WEAK" not in fixture["quality_label_assigned"]
            assert "USABLE" not in fixture["quality_label_assigned"]
