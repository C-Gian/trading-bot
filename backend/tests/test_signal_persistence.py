"""Deterministic guards for the P1A design and prospective power gate.

None of these tests may compute, import or assert the unshifted 120h ALIGNED statistic.
"""

from __future__ import annotations

import ast
import json
import math
from pathlib import Path
from typing import Any

import pytest
from app.research.continuation import CUTOFF_US, VARIANTS, FeatureBar, FeatureSource
from app.research.evaluation_protocol import HOUR_US, load_protocol, utc_us
from app.research.signal_persistence import (
    EFFECTIVE_ALPHA,
    FAMILY_ALPHA,
    MESI_BPS_PER_EVENT,
    MINIMUM_SHIFT_HOURS,
    OWNER_ANNUAL_MESI_BPS,
    POWER_TARGET,
    PRIMARY_HORIZON_HOURS,
    PROSPECTIVE_FAMILY_SIZE,
    READY,
    REDESIGN,
    REFERENCE_FOLDS,
    REFERENCE_RESOLVED_TRADES,
    FoldSignalSeries,
    PrepModeViolation,
    admissible_shifts,
    assert_no_result_leakage,
    build_null_distribution,
    circular_displacement,
    empirical_power,
    evaluate_power_gate,
    placebo_pooled_mean_bps,
    render_power_gate_markdown,
    shifted_positions,
)
from app.research.signal_persistence_lab import fold_decision_span

ROOT = Path(__file__).resolve().parents[2]
POWER = ROOT / "reports/power"
NULL_PATH = POWER / "P1A-ALIGNED-SIGNAL-PERSISTENCE-NULL-DISTRIBUTION-V1.json"
GATE_PATH = POWER / "P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-V1.json"
GATE_MD = POWER / "P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-V1.md"
DESIGN = ROOT / "research/design/ALIGNED_SIGNAL_PERSISTENCE_V1_DESIGN.md"
SIZE = 1000


def _series(
    positions: tuple[int, ...] = (10, 11, 12, 400),
    *,
    fold_id: str = "DEV-TEST",
    size: int = SIZE,
) -> FoldSignalSeries:
    return FoldSignalSeries(
        fold_id=fold_id,
        decision_times_us=tuple(index * HOUR_US for index in range(size)),
        forward_bps=tuple(float(index) for index in range(size)),
        signal_positions=positions,
        grid_span_hours=size,
        feature_ineligible_clocks=0,
        outcome_ineligible_clocks=0,
        emitted_conditions_on_span=len(positions),
    )


def _null() -> dict[str, Any]:
    return json.loads(NULL_PATH.read_text(encoding="utf-8"))


def _gate() -> dict[str, Any]:
    return json.loads(GATE_PATH.read_text(encoding="utf-8"))


# --- frozen ALIGNED semantics -------------------------------------------------------


INSTANT = 200 * HOUR_US


def _bars(count: int, width: int, volume: float) -> tuple[FeatureBar, ...]:
    return tuple(
        FeatureBar(index * width, 100.0 + index, 100.0 + index, volume)
        for index in range(1, count + 1)
    )


def _source() -> FeatureSource:
    return FeatureSource(_bars(260, HOUR_US, 1.0), _bars(80, 4 * HOUR_US, 1.0))


def test_raw_aligned_event_generation_is_the_frozen_decision() -> None:
    """P1A reuses the frozen gates; it never reimplements or relaxes them."""
    emits, feature, reference = _source().decision(INSTANT, "ALIGNED", 0)
    assert VARIANTS == ("REGIME_ONLY", "PARTICIPATION_ONLY", "ALIGNED")
    assert emits is (feature.breakout and feature.persistent_up and feature.participation)
    assert feature.asof_us == INSTANT and reference == feature.reference
    assert INSTANT <= CUTOFF_US


def test_signal_decision_uses_only_completed_history() -> None:
    """The 25th hourly bar ends at the decision instant, so nothing after it is read."""
    truncated = FeatureSource(
        tuple(bar for bar in _bars(260, HOUR_US, 1.0) if bar.open_us < INSTANT),
        tuple(bar for bar in _bars(80, 4 * HOUR_US, 1.0) if bar.open_us < INSTANT),
    )
    assert _source().decision(INSTANT, "ALIGNED", 0) == truncated.decision(INSTANT, "ALIGNED", 0)


def test_portfolio_occupancy_cannot_suppress_a_p1a_event() -> None:
    """Three consecutive hourly events survive; the historical run suppressed two."""
    series = _series((10, 11, 12))
    assert series.signal_count == 3
    for shift in (MINIMUM_SHIFT_HOURS, 400, SIZE - MINIMUM_SHIFT_HOURS):
        assert len(shifted_positions(series, shift)) == 3
    assert "position_available_us" not in FoldSignalSeries.__dataclass_fields__
    collector = (ROOT / "backend/app/research/signal_persistence_lab.py").read_text(
        encoding="utf-8"
    )
    for occupancy in ("blocked_until", "position_available_us", "suppressed", "trade_at"):
        assert occupancy not in collector


# --- causal 120h endpoint -----------------------------------------------------------


def test_120h_endpoint_uses_no_information_after_the_signal_fold() -> None:
    protocol = load_protocol()
    for fold in protocol["folds"]:
        start, last = fold_decision_span(fold)
        end = utc_us(fold["validation_end_exclusive"])
        assert start == utc_us(fold["validation_start"])
        assert end - last == PRIMARY_HORIZON_HOURS * HOUR_US
        assert last < utc_us(fold["last_signal_inclusive"])
    assert PRIMARY_HORIZON_HOURS == 120


def test_decision_grid_instants_are_hourly_and_increasing() -> None:
    with pytest.raises(ValueError):
        FoldSignalSeries(
            fold_id="BAD",
            decision_times_us=(0, 30 * 60_000_000) + tuple(i * HOUR_US for i in range(2, SIZE)),
            forward_bps=tuple(0.0 for _ in range(SIZE)),
            signal_positions=(),
            grid_span_hours=SIZE,
            feature_ineligible_clocks=0,
            outcome_ineligible_clocks=0,
            emitted_conditions_on_span=0,
        )


# --- prep-mode leakage safeguards ---------------------------------------------------


def test_zero_shift_is_forbidden_in_prep_mode() -> None:
    series = _series()
    with pytest.raises(PrepModeViolation):
        shifted_positions(series, 0)
    with pytest.raises(PrepModeViolation):
        placebo_pooled_mean_bps((series,), 0)
    with pytest.raises(PrepModeViolation):
        placebo_pooled_mean_bps((series,), SIZE)


def test_minimum_shift_strictly_exceeds_the_primary_horizon() -> None:
    assert MINIMUM_SHIFT_HOURS == 168 > PRIMARY_HORIZON_HOURS
    series = _series()
    for shift in range(-MINIMUM_SHIFT_HOURS + 1, MINIMUM_SHIFT_HOURS):
        with pytest.raises(PrepModeViolation):
            placebo_pooled_mean_bps((series,), shift)
    assert math.isfinite(placebo_pooled_mean_bps((series,), MINIMUM_SHIFT_HOURS))


def _functions(path: Path) -> dict[str, ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def _names(node: ast.AST) -> set[str]:
    names = {child.attr for child in ast.walk(node) if isinstance(child, ast.Attribute)}
    return names | {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def test_zero_shift_statistic_is_inaccessible_from_the_prep_command() -> None:
    """Only the guarded chain can read an outcome, and it always validates the shift."""
    functions = _functions(ROOT / "backend/app/research/signal_persistence.py")
    readers = {name for name, node in functions.items() if "forward_bps" in _names(node)}
    assert readers == {"__post_init__", "placebo_event_returns"}
    assert "shifted_positions" in _names(functions["placebo_event_returns"])
    assert "validate_prep_shift" in _names(functions["shifted_positions"])
    assert "placebo_event_returns" in _names(functions["placebo_pooled_mean_bps"])
    assert "forward_bps" not in _names(functions["evaluate_power_gate"])

    prep = ROOT / "scripts/audit_p1a_power_gate.py"
    script = prep.read_text(encoding="utf-8")
    for forbidden in ("placebo_event_returns", "shifted_positions", "FoldSignalSeries"):
        assert forbidden not in script
    for name in set(functions) | set(_functions(prep)):
        assert not any(word in name for word in ("actual", "observed", "zero_shift"))


def test_prep_artifacts_contain_no_actual_aligned_statistic() -> None:
    for path in (NULL_PATH, GATE_PATH):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert_no_result_leakage(payload)
    gate = _gate()
    guard = gate["leakage_guard"]
    assert guard == {
        "zero_shift_statistic_computed": False,
        "actual_aligned_120h_mean_present": False,
        "actual_minus_placebo_effect_present": False,
        "p1a_p_value_present": False,
        "p1a_performance_classified": False,
        "prep_mode_rejects_zero_shift": True,
        "new_material_experiment_consumed": False,
        "sealed_data_inspected": False,
        "post_cutoff_data_used": False,
    }
    text = GATE_MD.read_text(encoding="utf-8").lower()
    assert "p-value observed" not in text and "actual aligned" not in text
    assert not list(POWER.glob("*OUTCOME*")) and not list(POWER.glob("*RESULT*"))


def test_leakage_guard_rejects_a_forbidden_key() -> None:
    with pytest.raises(PrepModeViolation):
        assert_no_result_leakage({"power": {"p1a_p_value": 0.01}})
    with pytest.raises(PrepModeViolation):
        evaluate_power_gate({**_null(), "zero_shift_present": True})


# --- matched control properties -----------------------------------------------------


def test_circular_shift_preserves_event_count_per_fold() -> None:
    series = _series((10, 11, 12, 400, 999))
    for shift in (MINIMUM_SHIFT_HOURS, 333, SIZE - MINIMUM_SHIFT_HOURS):
        shifted = shifted_positions(series, shift)
        assert len(set(shifted)) == series.signal_count


def test_circular_shift_preserves_clustering_and_order_structure() -> None:
    series = _series((10, 11, 12, 400, 999))
    base = sorted(
        (later - earlier) % SIZE
        for earlier, later in zip(
            series.signal_positions,
            series.signal_positions[1:] + series.signal_positions[:1],
            strict=True,
        )
    )
    for shift in (MINIMUM_SHIFT_HOURS, 333, SIZE - MINIMUM_SHIFT_HOURS):
        shifted = sorted(shifted_positions(series, shift))
        gaps = sorted(
            (later - earlier) % SIZE
            for earlier, later in zip(shifted, shifted[1:] + shifted[:1], strict=True)
        )
        assert gaps == base


def test_placebo_calculation_is_deterministic() -> None:
    folds = (_series((10, 11, 12, 400)), _series((5, 300), fold_id="DEV-OTHER", size=SIZE + 24))
    first = [placebo_pooled_mean_bps(folds, shift) for shift in admissible_shifts(folds)]
    second = [placebo_pooled_mean_bps(folds, shift) for shift in admissible_shifts(folds)]
    assert first == second
    assert build_null_distribution(folds) == build_null_distribution(folds)


def test_admissible_shifts_clear_the_rule_in_every_fold() -> None:
    folds = (_series(size=SIZE), _series(fold_id="DEV-OTHER", size=SIZE + 24))
    shifts = admissible_shifts(folds)
    assert shifts and 0 not in shifts
    assert all(
        circular_displacement(shift, series.grid_size) >= MINIMUM_SHIFT_HOURS
        for shift in shifts
        for series in folds
    )


# --- multiplicity, power and MDE ----------------------------------------------------


def test_effective_alpha_is_correct_for_family_size_thirteen() -> None:
    assert FAMILY_ALPHA == 0.05
    assert PROSPECTIVE_FAMILY_SIZE == 13
    assert EFFECTIVE_ALPHA == 0.05 / 13
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert state["statistical_governance"]["known_discovery_family_size"] == 12
    assert state["statistical_governance"]["familywise_alpha"] == FAMILY_ALPHA
    gate = _gate()
    assert gate["multiplicity"]["observed_material_hypotheses"] == 12
    assert gate["multiplicity"]["documented_family_is_lower_bound"] is True


def test_event_level_mesi_translation_is_frozen() -> None:
    assert OWNER_ANNUAL_MESI_BPS == 500.0
    assert REFERENCE_RESOLVED_TRADES == 125 and REFERENCE_FOLDS == 6
    assert MESI_BPS_PER_EVENT == OWNER_ANNUAL_MESI_BPS / (
        REFERENCE_RESOLVED_TRADES / REFERENCE_FOLDS
    )
    assert MESI_BPS_PER_EVENT == 24.0
    policy = json.loads(
        (ROOT / "governance/ECONOMIC_SIGNIFICANCE_POLICY_V1.json").read_text(encoding="utf-8")
    )
    assert policy["annual_net_mesi_percentage_points"] == 5.0


def test_increasing_injected_effect_cannot_reduce_empirical_power() -> None:
    gate = evaluate_power_gate(_null())
    required = sorted(
        gate["power"]["critical_placebo_pooled_mean_bps"] - value
        for value in _null()["placebo_pooled_mean_bps"]
    )
    previous = 0.0
    for effect in (0.0, 1.0, MESI_BPS_PER_EVENT, 100.0, 285.0, 1000.0, 10000.0):
        power = empirical_power(required, effect)
        assert power >= previous
        previous = power
    assert previous == 1.0


def test_empirical_mde_is_deterministic_and_reaches_target_power() -> None:
    first = evaluate_power_gate(_null())["power"]
    second = evaluate_power_gate(_null())["power"]
    assert first == second
    assert first["empirical_MDE_bps_per_event"] == first["empirical_MDE_bps_per_event"]
    assert first["power_at_MDE"] >= POWER_TARGET
    assert first["power_target"] == POWER_TARGET == 0.8


def test_randomization_resolution_or_the_gate_fails_closed() -> None:
    null = _null()
    assert 1.0 / (null["placebo_shift_count"] + 1) <= EFFECTIVE_ALPHA
    coarse = {
        **null,
        "shifts": null["shifts"][:50],
        "placebo_pooled_mean_bps": null["placebo_pooled_mean_bps"][:50],
        "placebo_shift_count": 50,
    }
    gate = evaluate_power_gate(coarse)
    assert gate["power"]["randomization_resolution_sufficient"] is False
    assert gate["power"]["empirical_MDE_bps_per_event"] is None
    assert gate["power"]["power_at_MESI"] is None
    assert gate["power_gate_status"] == REDESIGN


def test_gate_status_rule_is_exact() -> None:
    gate = _gate()
    power = gate["power"]
    expected = (
        READY
        if gate["integrity_pass"]
        and power["randomization_resolution_sufficient"]
        and power["power_at_MESI"] is not None
        and power["power_at_MESI"] >= POWER_TARGET
        else REDESIGN
    )
    assert gate["power_gate_status"] == expected
    assert gate["preregistration_authorized"] is False
    assert gate["runner_candidate_registered"] is False


def test_committed_gate_matches_the_committed_null_distribution() -> None:
    assert evaluate_power_gate(_null()) == _gate()
    assert render_power_gate_markdown(_gate()) == GATE_MD.read_text(encoding="utf-8")


def test_committed_null_distribution_is_structurally_admissible() -> None:
    null = _null()
    shifts = null["shifts"]
    assert null["zero_shift_present"] is False and 0 not in shifts
    assert shifts == list(range(shifts[0], shifts[-1] + 1))
    assert shifts[0] == MINIMUM_SHIFT_HOURS
    assert null["placebo_shift_count"] == len(shifts) == len(null["placebo_pooled_mean_bps"])
    assert null["raw_signal_count"] == sum(fold["raw_signal_count"] for fold in null["folds"])
    smallest = min(fold["eligible_decision_instants"] for fold in null["folds"])
    assert shifts[-1] == smallest - MINIMUM_SHIFT_HOURS


def test_six_annual_folds_are_retained_with_120h_containment() -> None:
    null = _null()
    protocol = load_protocol()
    assert [fold["fold_id"] for fold in null["folds"]] == [
        fold["fold_id"] for fold in protocol["folds"]
    ]
    assert len(null["folds"]) == REFERENCE_FOLDS == 6
    for fold in null["folds"]:
        assert (
            fold["eligible_decision_instants"] + fold["outcome_ineligible_clocks"]
            == (fold["decision_grid_span_hours"])
        )
        assert fold["raw_signal_count"] <= fold["emitted_conditions_on_span"]


def test_design_and_decision_records_exist() -> None:
    design = DESIGN.read_text(encoding="utf-8")
    assert "DESIGN ONLY" in design and "120 hours" in design
    assert "48h, 72h and 168h are **not** in the design" in design
    adr = (ROOT / "decisions/ADR-0013-P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE.md").read_text(
        encoding="utf-8"
    )
    assert "P1A is not preregistered" in adr
    index = (ROOT / "decisions/INDEX.md").read_text(encoding="utf-8")
    assert "ADR-0013" in index


# --- historical immutability and safety ---------------------------------------------


def test_historical_research_artifacts_are_unchanged() -> None:
    aligned = json.loads(
        (ROOT / "research/experiments/EXP-ALG-009-ALIGNED/result.json").read_text(encoding="utf-8")
    )
    assert aligned["primary_result"] == 0.1373934676
    assert aligned["secondary_results"]["terminal_classification"] == "INCONCLUSIVE"
    assert aligned["run_identity_hash"] == (
        "5dd302c977782710dcc97a2aa36332af2617a5baac3c30605f74f7d72bdd2bd0"
    )
    audit = json.loads(
        (ROOT / "reports/statistics/STATISTICAL-EVIDENCE-AUDIT-V1.json").read_text(encoding="utf-8")
    )
    assert audit["alpha"] == 0.05
    assert all(
        entry["multiplicity_basis"] == "BONFERRONI_WORST_CASE_ALPHA_0.05/12_KNOWN_FAMILY"
        for entry in audit["detectability"]
    )


def test_scientific_counters_are_untouched() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert state["experiments_completed"] == 26
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["sealed_evaluation"]["authorized_btc_queries"] == 0
    assert state["adaptive_search"]["sealed_queries"] == 0
    assert state["sealed_evaluations_completed"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False
    assert state["statistical_governance"]["known_discovery_family_size"] == 12
    gate = state["signal_persistence_power_gate"]
    assert gate["hypothesis_status"] == "POWER_BLOCKED_NOT_EXECUTED"
    assert gate["preregistration_authorized"] is False
    assert gate["material_experiment_executed"] is False
    assert gate["power_gate_status"] == _gate()["power_gate_status"]
    assert gate["empirical_mde_bps_per_event"] == (_gate()["power"]["empirical_MDE_bps_per_event"])
    assert gate["power_at_mesi"] == _gate()["power"]["power_at_MESI"]


def test_no_p1a_preregistration_or_runner_candidate_exists() -> None:
    assert not (ROOT / "research/experiments/EXP-P1A-ALIGNED-SIGNAL-PERSISTENCE").exists()
    assert not list((ROOT / "research/protocols").glob("*PERSISTENCE*"))
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert not any(
        "PERSISTENCE" in candidate for candidate in state["research_runner"]["candidate_ids"]
    )
