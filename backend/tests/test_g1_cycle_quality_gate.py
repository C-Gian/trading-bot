"""SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1: frozen labels, gate design and the 1m primary delay."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest
from app.g1 import cycle_quality_gate as gate
from app.g1 import fixtures
from app.g1.core import G1Core, run_manifest, run_to_end
from app.g1.cycle import (
    CYCLE_DECISION_ACTIVATION,
    SCALES,
    UNAVAILABLE,
    USABLE,
    USABLE_EXPLAINED_FRACTION,
    USABLE_PERSISTENCE_BARS,
    WEAK,
    ScaleTracker,
)
from app.g1.ledger import (
    DELAY_STRESS_MINUTES,
    PRIMARY_DELAY_MINUTES,
    RISK_CONTRACT_VERSION,
    RiskPolicy,
    with_delay,
)
from app.g1.records import (
    CycleState,
    DecisionSnapshot,
    FillKind,
    OrderFillEvent,
    SignalRole,
    TradePlan,
)

ROOT = Path(__file__).resolve().parents[2]
START = datetime(2001, 1, 1, tzinfo=UTC)


def _drive(tracker: ScaleTracker, values, skip=frozenset()):
    step = timedelta(minutes=tracker.scale.bar_minutes)
    rows = []
    for index, value in enumerate(values):
        if index in skip:
            continue
        opened = START + index * step
        tracker.update(opened, opened + step, float(value), True)
        rows.append((index, tracker.quality_label(), tracker.explained, tracker.ready))
    return rows


def _expected(rows, position: int, ready: bool, gap_epoch_start: int) -> str:
    _, _, explained, _ = rows[position]
    if not ready or explained is None:
        return UNAVAILABLE
    window = [r for r in rows[max(0, position - 2) : position + 1] if r[0] >= gap_epoch_start]
    if len(window) == USABLE_PERSISTENCE_BARS and all(
        r[2] is not None and r[2] >= USABLE_EXPLAINED_FRACTION for r in window
    ):
        return USABLE
    return WEAK


def test_frozen_rule_constants_are_unchanged() -> None:
    assert USABLE_EXPLAINED_FRACTION == 0.90 and USABLE_PERSISTENCE_BARS == 3
    assert CYCLE_DECISION_ACTIVATION is True  # ADR-0046 activation after the gate


@pytest.mark.parametrize("scale", SCALES[:3], ids=lambda s: s.nominal)
def test_labels_follow_exactly_the_frozen_rule(scale) -> None:
    rng = np.random.default_rng(3)
    t = np.arange(scale.warmup_bars + 300, dtype=float)
    values = 100 + 10 * np.sin(2 * np.pi * t / scale.nominal_samples) + rng.normal(0, 4, t.size)
    rows = _drive(ScaleTracker(scale), values)
    labels = {r[1] for r in rows}
    assert {UNAVAILABLE, WEAK} <= labels
    for position, row in enumerate(rows):
        assert row[1] == _expected(rows, position, row[3], 0), position


def test_gap_clears_persistence_and_requires_full_rewarm() -> None:
    scale = SCALES[1]
    t = np.arange(scale.warmup_bars * 2 + 100, dtype=float)
    values = 100 + 10 * np.sin(2 * np.pi * t / 14)
    gap = scale.warmup_bars + 40
    tracker = ScaleTracker(scale)
    rows = _drive(tracker, values, skip=frozenset({gap}))
    before = [r for r in rows if r[0] < gap and r[3]]
    assert before and before[-1][1] == USABLE
    after = [r for r in rows if r[0] > gap]
    assert all(r[1] == UNAVAILABLE for r in after[: scale.warmup_bars - 1])
    assert after[scale.warmup_bars - 1][3]  # ready again only after a normal warm-up
    for position, row in enumerate(rows):
        if row[0] > gap:
            assert row[1] == _expected(rows, position, row[3], gap + 1)


def test_gate_design_matches_the_frozen_protocol() -> None:
    assert gate.NOISE_PATHS >= 128 and gate.CYCLE_PATHS >= 48 and gate.EVALUATED_BARS >= 512
    assert (gate.NOISE_MEDIAN_MAX, gate.NOISE_P95_MAX) == (0.05, 0.15)
    assert (gate.COHERENT_MEDIAN_MIN, gate.COHERENT_P10_MIN, gate.PERIOD_ERROR_MAX) == (
        0.80,
        0.60,
        0.10,
    )
    for index, scale in enumerate(SCALES):
        lower, middle, upper = gate.band_periods(scale)
        assert scale.period1 < lower < middle < upper < scale.period2
        periods = [gate.cycle_design(index, scale, i)[0] for i in range(gate.CYCLE_PATHS)]
        assert periods.count(lower) == periods.count(middle) == periods.count(upper) == 16
        phases = {gate.cycle_design(index, scale, i)[1] for i in range(gate.CYCLE_PATHS)}
        assert len(phases) == gate.CYCLE_PATHS and all(0 <= p < 2 * math.pi for p in phases)
        seeds = {gate.noise_seed(index, i) for i in range(gate.NOISE_PATHS)}
        assert len(seeds) == gate.NOISE_PATHS
        trend = gate.cycle_series(index, scale, 5, trend=True)
        clean = gate.cycle_series(index, scale, 5, trend=False)
        assert np.allclose(trend - clean, gate.TREND_PER_BAR * np.arange(len(clean)))
        assert np.array_equal(
            gate.noise_series(index, scale, 7), gate.noise_series(index, scale, 7)
        )


def test_gate_artifact_records_a_mechanical_disposition_without_market_data() -> None:
    artifact = json.loads((ROOT / gate.ARTIFACT_PATH).read_text(encoding="utf-8"))
    assert (
        artifact["market_data_read"] is False and artifact["btc_returns_or_outcomes_used"] is False
    )
    assert artifact["threshold_or_method_search_performed"] is False
    assert artifact["cycle_active_in_decisions"] is False  # true when the gate ran
    rule = artifact["frozen_rule"]
    assert rule["explained_fraction_threshold"] == 0.9 and rule["persistence_bars"] == 3
    assert rule["protocol_canonical_sha256"] == gate.canonical_text_sha256(gate.PROTOCOL_PATH)
    assert rule["decision_canonical_sha256"] == gate.canonical_text_sha256(gate.DECISION_PATH)
    # ADR-0046 changed cycle.py source text (activation, qualifier), never its math; the
    # accepted artifact is preserved byte-for-byte and replayed by the gate `--check`.
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from build_g1_cycle_quality_gate import PRESERVED_SHA256

    raw = (ROOT / gate.ARTIFACT_PATH).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == PRESERVED_SHA256
    for path in ("backend/app/g1/cycle_reference.py", "backend/app/g1/cycle_quality_gate.py"):
        assert gate.canonical_text_sha256(path) == artifact["code_canonical_sha256"][path], path
    passed = all(all(g.values()) for g in artifact["scale_gate_results"].values()) and all(
        artifact["integrity"].values()
    )
    assert artifact["disposition"] == (gate.PASS if passed else gate.FAIL)
    assert [s["nominal_scale"] for s in artifact["scales"]] == [s.nominal for s in SCALES]
    for scale in artifact["scales"]:
        assert scale["white_noise"]["paths"] == 128
        assert scale["clean_cycle"]["paths"] == scale["trend_plus_cycle"]["paths"] == 48
        assert set(scale["non_gating_diagnostics"]) == set(gate.NON_GATING)


def test_active_cycle_states_carry_labels_and_the_frozen_qualifier() -> None:
    bars = fixtures.minute_path()
    policy = RiskPolicy()
    core = run_to_end(
        G1Core(
            run_manifest(bars, fixtures.START, fixtures.END, policy),
            fixtures.scenario_step,
            fixtures.FUNDING_RATES,
            policy,
        ),
        bars,
    )
    states = core.store.of_type(CycleState)
    assert any(s.quality_label == USABLE for state in states for s in state.scales)
    assert all(state.decision_role is SignalRole.ACTIVE for state in states)
    assert {state.timing_qualifier for state in states} <= {
        "CYCLE_SUPPORTS_LONG",
        "CYCLE_SUPPORTS_SHORT",
        "CYCLE_MIXED_OR_WEAK",
    }


def test_primary_operational_delay_is_one_minute() -> None:
    policy = RiskPolicy()
    assert policy.operational_delay_minutes == PRIMARY_DELAY_MINUTES == 1
    assert "1M_PRIMARY_DELAY" in RISK_CONTRACT_VERSION and policy.version == RISK_CONTRACT_VERSION
    assert DELAY_STRESS_MINUTES == 5
    assert (policy.risk_fraction, policy.max_gross_notional_multiple) == (
        Decimal("0.0025"),
        Decimal(1),
    )
    assert (policy.daily_loss_stop_fraction, policy.run_drawdown_stop_fraction) == (
        Decimal("0.01"),
        Decimal("0.05"),
    )
    bars = fixtures.minute_path()
    core = run_to_end(
        G1Core(
            run_manifest(bars, fixtures.START, fixtures.END, policy),
            fixtures.scenario_step,
            fixtures.FUNDING_RATES,
            policy,
        ),
        bars,
    )
    plans = core.store.of_type(TradePlan)
    decisions = {d.decision_id: d for d in core.store.of_type(DecisionSnapshot)}
    assert plans and all(plan.operational_delay_minutes == 1 for plan in plans)
    entries = {
        f.trade_plan_id: f for f in core.store.of_type(OrderFillEvent) if f.kind is FillKind.ENTRY
    }
    for plan in plans:
        decision = decisions[plan.decision_id]
        assert plan.readiness_time == decision.decision_time
        if plan.trade_plan_id in entries:
            assert entries[plan.trade_plan_id].event_time == plan.readiness_time + timedelta(
                minutes=1
            )
        assert with_delay(plan, DELAY_STRESS_MINUTES).operational_delay_minutes == 6
