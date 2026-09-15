"""Deterministic guards for the frozen P2 cycle design and its power preparation.

None of these tests may compute, import or assert the actual BTCUSDT training-selected
period, outer validation power, pooled statistic, structural p-value, or market
classification.
"""

from __future__ import annotations

import ast
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from app.data.policy import CUTOFF
from app.data.store import available
from app.research.cycle_structure import (
    AR_MAXIMUM_ORDER,
    BAND_MAXIMUM_DAYS,
    BAND_MINIMUM_DAYS,
    BAR_US,
    BLOCK_EXPECTED_OBSERVATIONS,
    CALIBRATION_PERIOD_DAYS,
    EMBARGO_DAYS,
    FORBIDDEN_ARTIFACT_KEYS,
    GATE_SNR,
    NULL_REPLICATES,
    OVERSAMPLING,
    PHASE_COUNT,
    READY,
    REDESIGN,
    SNR_GRID,
    STREAM_BENCHMARK,
    SYNTHETIC_REPLICATES_PER_CELL,
    TARGET_POWER,
    CycleFold,
    CycleLattice,
    JointNullDesign,
    PrepModeViolation,
    SimulatedPath,
    assert_no_result_leakage,
    binomial_interval,
    build_fold_design,
    combine,
    critical_value,
    detection_power,
    evaluate_power_gate,
    fidelity_criteria,
    fidelity_statistics,
    fit_sieve,
    fold_validation_power,
    frequency_grid,
    injection_amplitude,
    injection_matrix,
    injection_path,
    phase_index,
    phase_value,
    pooled_statistic,
    project,
    replicate_statistics,
    simulate_joint_paths,
    unit_injection,
)
from app.research.evaluation_protocol import load_protocol, utc_us

ROOT = Path(__file__).resolve().parents[2]
POWER = ROOT / "reports/power"
PREREGISTRATION = POWER / "P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1.json"
FIDELITY = POWER / "P2-CYCLE-NULL-FIDELITY-V1.json"
BENCHMARK = POWER / "P2-CYCLE-COMPUTE-BENCHMARK-V1.json"
DETECTABILITY = POWER / "P2-CYCLE-DETECTABILITY-V1.json"
GATE_JSON = POWER / "P2-CYCLE-FOUNDATION-POWER-GATE-V1.json"
GATE_MD = POWER / "P2-CYCLE-FOUNDATION-POWER-GATE-V1.md"
PROTOCOL = ROOT / "research/protocols/P2-CYCLE-FOUNDATION-V1.json"
DESIGN = ROOT / "research/design/BTC_TIME_CYCLE_STRUCTURE_V1_DESIGN.md"
MODULE = ROOT / "backend/app/research/cycle_structure.py"
LAB = ROOT / "backend/app/research/cycle_structure_lab.py"
STATE = ROOT / "state/current_state.json"

SLOTS = 4200
GAPS = (137, 1993, 3301)


def _lattice(gaps: tuple[int, ...] = GAPS) -> CycleLattice:
    eligible = np.ones(SLOTS, dtype=bool)
    eligible[list(gaps)] = False
    return CycleLattice(start_us=0, slot_count=SLOTS, eligible=eligible)


def _folds() -> tuple[CycleFold, ...]:
    return (
        CycleFold("F1", train_stop=1400, validation_start=1500, validation_stop=2000),
        CycleFold("F2", train_stop=2400, validation_start=2500, validation_stop=3000),
        CycleFold("F3", train_stop=3400, validation_start=3500, validation_stop=4200),
    )


def _series(seed: int = 7) -> np.ndarray:
    generator = np.random.default_rng(seed)
    innovation = generator.standard_normal(SLOTS) * 0.02
    values = np.zeros(SLOTS)
    for index in range(1, SLOTS):
        values[index] = 0.05 * values[index - 1] + innovation[index]
    return values


def _joint(
    gaps: tuple[int, ...] = GAPS,
) -> tuple[CycleLattice, tuple[CycleFold, ...], JointNullDesign]:
    lattice = _lattice(gaps)
    folds = _folds()
    values = _series()
    models = tuple(
        fit_sieve(
            fold.fold_id,
            values[: fold.train_stop],
            lattice.eligible[: fold.train_stop],
            fold.train_stop,
        )
        for fold in folds
    )
    design = JointNullDesign(
        lattice=lattice,
        folds=folds,
        models=models,
        stage_bounds=(0, *(fold.train_stop for fold in folds), SLOTS),
        stage_models=(0, *range(len(models))),
    )
    return lattice, folds, design


def _designs(lattice: CycleLattice, folds: tuple[CycleFold, ...]) -> tuple[Any, ...]:
    return tuple(build_fold_design(lattice, fold) for fold in folds)


def _artifact(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


# ---------------------------------------------------------------------------------
# Frozen representation
# ---------------------------------------------------------------------------------


def test_four_hour_representation_follows_canonical_causal_aggregation() -> None:
    source = LAB.read_text(encoding="utf-8")
    assert "data/derived/BTCUSDT-4h.parquet" in source
    # Eligibility demands two canonically complete bars that are exactly consecutive.
    assert "complete[1:] & complete[:-1] & consecutive" in source
    assert "np.diff(times) == BAR_US" in source
    assert "np.log(close[1:][inside]) - np.log(close[:-1][inside])" in source
    assert BAR_US == 4 * 3_600_000_000


def test_gaps_are_never_interpolated() -> None:
    lattice = _lattice()
    for fold in _folds():
        design = build_fold_design(lattice, fold)
        slots = np.concatenate((design.train_slots, design.validation_slots))
        assert np.all(lattice.eligible[slots])
        assert not set(slots.tolist()) & set(GAPS)
    assert "interpolat" in MODULE.read_text(encoding="utf-8")


def test_frozen_period_band_is_unchanged() -> None:
    assert (BAND_MINIMUM_DAYS, BAND_MAXIMUM_DAYS, OVERSAMPLING) == (2.0, 90.0, 4)
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    band = protocol["primary_method"]["period_band_days"]
    assert band == {"minimum": 2, "maximum": 90}
    assert "**2 through 90 UTC days**" in DESIGN.read_text(encoding="utf-8")
    grid = frequency_grid(1000.0)
    assert grid[0] == pytest.approx(1.0 / 90.0)
    assert grid[-1] <= 0.5 + 1e-12
    assert np.all(np.diff(grid) > 0)
    assert grid[1] - grid[0] == pytest.approx(1.0 / (4 * 1000.0))


def test_grid_spacing_is_rebuilt_from_each_training_span() -> None:
    lattice = _lattice()
    designs = _designs(lattice, _folds())
    spacings = [design.frequencies[1] - design.frequencies[0] for design in designs]
    assert spacings == sorted(spacings, reverse=True)
    for design in designs:
        assert design.frequencies[1] - design.frequencies[0] == pytest.approx(
            1.0 / (OVERSAMPLING * design.train_span_days)
        )


def test_exactly_one_structural_primary_and_at_most_two_diagnostics() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert len(protocol["primary_hypotheses"]) == 1
    assert protocol["primary_hypotheses"][0]["hypothesis_id"] == "BTC_TIME_CYCLE_STRUCTURE_V1"
    assert protocol["primary_hypotheses"][0]["economic"] is False
    assert len(protocol["diagnostics"]) <= 2
    assert protocol["budget"]["primary_structural_hypotheses"] == 1
    assert protocol["budget"]["maximum_diagnostics"] == 2
    assert protocol["budget"]["material_economic_hypotheses_executed"] == 0
    assert all("NON_RESCUING" in item["role"] for item in protocol["diagnostics"])


def test_frozen_embargo_is_ninety_days_and_binds_before_validation() -> None:
    assert EMBARGO_DAYS == 90
    protocol = load_protocol()
    for fold, record in zip(_folds(), protocol["folds"], strict=False):
        assert fold.train_stop < fold.validation_start
        assert record["validation_start"] < record["validation_end_exclusive"]


# ---------------------------------------------------------------------------------
# Selection / evaluation separation
# ---------------------------------------------------------------------------------


def test_validation_never_searches_frequency() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "fold_validation_power"
    )
    searches = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"argmax", "argmin", "argsort", "max"}
    ]
    assert len(searches) == 1
    assert isinstance(searches[0].args[0], ast.Name) and searches[0].args[0].id == "training"


def test_selection_ignores_validation_data() -> None:
    lattice, folds, joint = _joint()
    design = _designs(lattice, folds)[0]
    base = simulate_joint_paths(joint, STREAM_BENCHMARK, 0, 4)
    altered = base.copy()
    span = altered[folds[0].validation_start :].shape
    altered[folds[0].validation_start :] += np.random.default_rng(5).standard_normal(span) * 0.03
    first = SimulatedPath("BENCHMARK_REPLICATE", 0, base)
    second = SimulatedPath("BENCHMARK_REPLICATE", 0, altered)
    from app.research.cycle_structure import gls_power

    def selected(path: SimulatedPath) -> np.ndarray:
        projection = project(design, path)
        return np.argmax(
            gls_power(
                design.train_terms,
                projection.sum_train_cos,
                projection.sum_train_sin,
                projection.sum_train_y,
                projection.sum_train_yy,
                design.train_count,
            ),
            axis=0,
        )

    assert np.array_equal(selected(first), selected(second))
    assert not np.allclose(
        fold_validation_power(design, project(design, first)),
        fold_validation_power(design, project(design, second)),
    )


def test_longer_period_wins_an_exact_tie() -> None:
    lattice = _lattice()
    design = build_fold_design(lattice, _folds()[0])
    assert np.all(np.diff(design.frequencies) > 0)
    # Ascending frequencies plus first-match argmax is exactly the longer-period rule.
    tied = np.zeros((design.frequency_count, 1))
    tied[[3, 17]] = 1.0
    assert int(np.argmax(tied, axis=0)[0]) == 3
    assert 1.0 / design.frequencies[3] > 1.0 / design.frequencies[17]


def test_full_frequency_selection_recovers_an_injected_grid_frequency() -> None:
    lattice, folds, joint = _joint()
    design = build_fold_design(lattice, folds[0])
    target = 300
    frequency = design.frequencies[target]
    times = lattice.times_days
    step = 4 / 24.0
    component = np.sin(2 * math.pi * frequency * times) - np.sin(
        2 * math.pi * frequency * (times - step)
    )
    path = simulate_joint_paths(joint, STREAM_BENCHMARK, 0, 1)
    path[:, 0] += 40.0 * component
    from app.research.cycle_structure import gls_power

    projection = project(design, SimulatedPath("BENCHMARK_REPLICATE", 0, path))
    power = gls_power(
        design.train_terms,
        projection.sum_train_cos,
        projection.sum_train_sin,
        projection.sum_train_y,
        projection.sum_train_yy,
        design.train_count,
    )
    assert int(np.argmax(power, axis=0)[0]) == target


# ---------------------------------------------------------------------------------
# Leakage guards
# ---------------------------------------------------------------------------------


def test_real_series_cannot_enter_frequency_selection() -> None:
    lattice, folds, _ = _joint()
    designs = _designs(lattice, folds)
    real = _series()[:, None]
    with pytest.raises(PrepModeViolation):
        project(designs[0], real)  # type: ignore[arg-type]
    with pytest.raises(PrepModeViolation):
        replicate_statistics(designs, real)  # type: ignore[arg-type]
    with pytest.raises(PrepModeViolation):
        SimulatedPath("REAL_MARKET", 0, real)


def test_validation_returns_cannot_be_loaded() -> None:
    source = LAB.read_text(encoding="utf-8")
    assert "def validation_returns" in source
    assert "raise PrepModeViolation" in source
    tree = ast.parse(source)
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "validation_returns"
    )
    assert all(
        isinstance(node, ast.Raise) for node in function.body if not isinstance(node, ast.Expr)
    )


@pytest.mark.parametrize(
    "key",
    [
        "actual_selected_period_days",
        "btc_selected_period_days",
        "actual_validation_power",
        "pooled_validation_power",
        "actual_pooled_statistic",
        "structural_p_value",
        "actual_p_value",
        "primary_classification",
    ],
)
def test_actual_outcome_keys_cannot_be_emitted(key: str) -> None:
    assert key in FORBIDDEN_ARTIFACT_KEYS
    with pytest.raises(PrepModeViolation):
        assert_no_result_leakage({"power": {"cells": [{key: 1.0}]}})


def test_committed_power_artifacts_pass_the_forbidden_key_audit() -> None:
    for path in (PREREGISTRATION, FIDELITY, BENCHMARK, DETECTABILITY, GATE_JSON):
        artifact = _artifact(path)
        if artifact is None:
            continue
        assert_no_result_leakage(artifact)
        assert artifact["ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED"] is False


def test_gate_artifacts_declare_no_observed_market_result() -> None:
    gate = _artifact(GATE_JSON)
    if gate is None:
        pytest.skip("power gate not generated yet")
    guard = gate["leakage_guard"]
    assert guard["actual_training_selected_period_computed"] is False
    assert guard["actual_validation_power_computed"] is False
    assert guard["actual_pooled_statistic_computed"] is False
    assert guard["actual_structural_p_value_computed"] is False
    assert guard["market_classification_emitted"] is False
    assert guard["real_validation_returns_loaded"] is False
    assert guard["sealed_data_queried"] is False
    assert guard["assets_expanded"] is False
    assert guard["cycle_trading_implemented"] is False
    assert gate["preregistration_authorized"] is False
    assert gate["actual_execution_authorized"] is False
    assert "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED = False" in GATE_MD.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------------
# Frozen null
# ---------------------------------------------------------------------------------


def test_ar_order_search_set_and_block_length_remain_frozen() -> None:
    assert AR_MAXIMUM_ORDER == 42
    assert BLOCK_EXPECTED_OBSERVATIONS == 42
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["primary_method"]["null"] == (
        "TRAINING_ONLY_AR_SIEVE_BIC_0_TO_42_PLUS_STATIONARY_RESIDUAL_BLOCK_BOOTSTRAP_EXPECTED_42"
    )
    preregistered = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    assert preregistered["block_expected_observations"] == 42
    assert preregistered["block_length_may_be_tuned_after_observation"] is False
    fidelity = _artifact(FIDELITY)
    if fidelity is not None:
        assert fidelity["block_expected_observations"] == 42
        assert fidelity["block_length_tuned_after_observation"] is False


def test_ar_order_uses_training_data_only() -> None:
    lattice = _lattice()
    fold = _folds()[0]
    values = _series()
    future = values.copy()
    future[fold.train_stop :] = 99.0
    first = fit_sieve(
        fold.fold_id,
        values[: fold.train_stop],
        lattice.eligible[: fold.train_stop],
        fold.train_stop,
    )
    second = fit_sieve(
        fold.fold_id,
        future[: fold.train_stop],
        lattice.eligible[: fold.train_stop],
        fold.train_stop,
    )
    assert first.order == second.order
    assert np.array_equal(first.coefficients, second.coefficients)
    assert first.residuals.size <= fold.train_stop
    assert first.training_observations == fold.train_stop


def test_sieve_residual_rows_require_contiguous_lag_history() -> None:
    lattice = _lattice(gaps=(500,))
    fold = _folds()[0]
    model = fit_sieve(
        fold.fold_id,
        _series()[: fold.train_stop],
        lattice.eligible[: fold.train_stop],
        fold.train_stop,
    )
    dense = fit_sieve(
        fold.fold_id,
        _series()[: fold.train_stop],
        np.ones(fold.train_stop, dtype=bool),
        fold.train_stop,
    )
    # One gap removes exactly the rows whose 42-lag window straddles it.
    assert dense.observations - model.observations == AR_MAXIMUM_ORDER + 1


def test_null_fidelity_statistics_cover_the_declared_families() -> None:
    criteria = fidelity_criteria()
    statistics = fidelity_statistics(_series())
    assert set(statistics) == set(criteria)
    assert "return_sd" in statistics and "excess_kurtosis" in statistics
    assert {f"return_acf_lag{lag}" for lag in range(1, 7)} <= set(statistics)
    assert {f"absolute_acf_lag{lag}" for lag in (42, 90, 180, 360, 540)} <= set(statistics)
    assert {
        "log_realized_volatility_sd_1d",
        "log_realized_volatility_sd_7d",
        "log_realized_volatility_sd_30d",
    } <= set(statistics)
    assert {f"variance_ratio_{horizon}" for horizon in (12, 42, 180, 540)} <= set(statistics)


def test_fidelity_thresholds_were_preregistered_before_measurement() -> None:
    preregistered = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    assert preregistered["criteria"] == fidelity_criteria()
    assert preregistered["training_only"] is True
    assert preregistered["validation_results_used"] is False
    assert preregistered["rank_p_role"] == "DESCRIPTIVE_ONLY_NOT_A_GATE"
    fidelity = _artifact(FIDELITY)
    if fidelity is None:
        pytest.skip("fidelity diagnostic not generated yet")
    assert fidelity["preregistration"]["thresholds_fixed_before_calculation"] is True
    assert fidelity["training_only"] is True
    assert fidelity["validation_results_used"] is False
    for fold in fidelity["folds"]:
        for check in fold["checks"].values():
            assert (
                check["criterion"]
                == preregistered["criteria"][
                    next(name for name, value in fold["checks"].items() if value is check)
                ]
            )


def test_null_fidelity_uses_training_segments_only() -> None:
    fidelity = _artifact(FIDELITY)
    if fidelity is None:
        pytest.skip("fidelity diagnostic not generated yet")
    protocol = load_protocol()
    assert set(fidelity["training_segments"]) == {fold["fold_id"] for fold in protocol["folds"]}
    assert fidelity["ar_order_uses_training_only"] is True
    assert set(fidelity["ar_order_by_fold"]) == set(fidelity["training_segments"])
    assert all(0 <= order <= AR_MAXIMUM_ORDER for order in fidelity["ar_order_by_fold"].values())


# ---------------------------------------------------------------------------------
# Joint six-fold replicate semantics
# ---------------------------------------------------------------------------------


def test_one_replicate_is_one_joint_realization() -> None:
    lattice, folds, joint = _joint()
    values = simulate_joint_paths(joint, STREAM_BENCHMARK, 0, 3)
    designs = _designs(lattice, folds)
    for index in range(len(folds) - 1):
        earlier = set(designs[index].train_slots.tolist())
        later = set(designs[index + 1].train_slots.tolist())
        assert earlier < later
        shared = np.asarray(sorted(earlier))
        assert np.array_equal(values[shared], values[shared])
        validation = set(designs[index].validation_slots.tolist())
        assert validation & later


def test_fold_nulls_are_not_silently_treated_as_independent() -> None:
    lattice, folds, joint = _joint()
    designs = _designs(lattice, folds)
    weights = [design.validation_count for design in designs]
    joint_path = SimulatedPath(
        "BENCHMARK_REPLICATE", 0, simulate_joint_paths(joint, STREAM_BENCHMARK, 0, 96)
    )
    joint_pooled = pooled_statistic(
        [fold_validation_power(design, project(design, joint_path)) for design in designs], weights
    )
    independent = []
    for index, design in enumerate(designs):
        path = SimulatedPath(
            "BENCHMARK_REPLICATE",
            0,
            simulate_joint_paths(joint, STREAM_BENCHMARK + 11 * (index + 1), 0, 96),
        )
        independent.append(fold_validation_power(design, project(design, path)))
    independent_pooled = pooled_statistic(independent, weights)
    assert joint_pooled.shape == independent_pooled.shape
    assert not np.allclose(joint_pooled, independent_pooled)
    benchmark = _artifact(BENCHMARK)
    if benchmark is None:
        return
    record = benchmark["joint_replication"]
    assert record["folds_simulated_independently"] is False
    assert record["checks"]["fold_nulls_concatenated_from_independent_draws"] is False
    assert record["checks"]["single_path_per_replicate"] is True
    assert record["joint_replication_method"] == "JOINT_NESTED_PREFIX_CAUSAL_SIEVE_PATH_V1"
    assert record["cross_fold_dependence_handling"]
    assert record["shared_history_handling"]


def test_joint_stage_models_never_see_their_own_future() -> None:
    lattice, folds, joint = _joint()
    for stage, model_index in enumerate(joint.stage_models):
        if stage == 0:
            continue
        assert joint.models[model_index].training_observations <= joint.stage_bounds[stage]
    with pytest.raises(ValueError):
        JointNullDesign(
            lattice=lattice,
            folds=folds,
            models=joint.models,
            stage_bounds=joint.stage_bounds,
            stage_models=(0, 2, 2, 2),
        )


def test_committed_joint_proof_upper_bounds_the_overlap_dependence() -> None:
    benchmark = _artifact(BENCHMARK)
    if benchmark is None:
        pytest.skip("joint proof not generated yet")
    record = benchmark["joint_replication"]
    assert record["pooled_sd_ratio"] >= 1.0 - record["pooled_sd_ratio_tolerance"]
    assert all(count > 0 for count in record["earlier_validation_slots_reused_in_later_training"])
    assert record["stage_model_fitted_before_stage"] is True


# ---------------------------------------------------------------------------------
# Synthetic injection
# ---------------------------------------------------------------------------------


def test_phase_assignment_is_deterministic_and_balanced() -> None:
    assert [phase_index(index) for index in range(20)] == [index % 16 for index in range(20)]
    counts = np.bincount(
        [phase_index(index) for index in range(SYNTHETIC_REPLICATES_PER_CELL)],
        minlength=PHASE_COUNT,
    )
    assert counts.tolist() == [SYNTHETIC_REPLICATES_PER_CELL // PHASE_COUNT] * PHASE_COUNT
    assert phase_value(0) == 0.0
    assert phase_value(8) == pytest.approx(math.pi)
    with pytest.raises(ValueError):
        phase_value(PHASE_COUNT)


def test_synthetic_snr_injection_matches_its_declared_amplitude() -> None:
    lattice = _lattice()
    innovation = 0.0173
    for period in CALIBRATION_PERIOD_DAYS:
        for index in range(PHASE_COUNT):
            phase = phase_value(index)
            for snr in SNR_GRID:
                amplitude = injection_amplitude(lattice, period, phase, snr, innovation)
                injected = amplitude * unit_injection(lattice, period, phase)[lattice.eligible]
                observed = math.sqrt(float(injected @ injected) / injected.size)
                assert observed == pytest.approx(snr * innovation, abs=1e-15, rel=1e-12)


def test_injection_is_a_differenced_log_price_sinusoid() -> None:
    lattice = _lattice()
    period, phase = 7.0, phase_value(3)
    times = lattice.times_days
    step = 4 / 24.0
    expected = np.sin(2 * math.pi * times / period + phase) - np.sin(
        2 * math.pi * (times - step) / period + phase
    )
    assert np.allclose(unit_injection(lattice, period, phase), expected)
    matrix = injection_matrix(lattice, period)
    assert matrix.shape == (SLOTS, PHASE_COUNT)
    assert np.allclose(matrix[:, 3], expected)


def test_combination_reproduces_a_directly_projected_injected_path() -> None:
    lattice, folds, joint = _joint()
    design = build_fold_design(lattice, folds[2])
    base = simulate_joint_paths(joint, STREAM_BENCHMARK, 0, 6)
    path = SimulatedPath("SYNTHETIC_REPLICATE", 0, base)
    phases = np.asarray([phase_index(index) for index in range(6)])
    matrix = injection_matrix(lattice, 14.0)
    injected = project(design, injection_path(lattice, 14.0))
    from app.research.cycle_structure import FoldProjection

    widened = FoldProjection(
        sum_train_cos=injected.sum_train_cos[:, phases],
        sum_train_sin=injected.sum_train_sin[:, phases],
        sum_train_y=injected.sum_train_y[phases],
        sum_train_yy=injected.sum_train_yy[phases],
        sum_validation_cos=injected.sum_validation_cos[:, phases],
        sum_validation_sin=injected.sum_validation_sin[:, phases],
        sum_validation_y=injected.sum_validation_y[phases],
        sum_validation_yy=injected.sum_validation_yy[phases],
    )
    cross = np.stack(
        (
            np.einsum("ij,ij->j", base[design.train_slots], matrix[design.train_slots][:, phases]),
            np.einsum(
                "ij,ij->j",
                base[design.validation_slots],
                matrix[design.validation_slots][:, phases],
            ),
        )
    )
    scale = np.full(6, 0.004)
    combined = combine(project(design, path), widened, cross, scale)
    direct = project(
        design,
        SimulatedPath("SYNTHETIC_REPLICATE", 0, base + scale[None, :] * matrix[:, phases]),
    )
    assert np.allclose(combined.sum_train_cos, direct.sum_train_cos, rtol=1e-9, atol=1e-12)
    assert np.allclose(combined.sum_train_yy, direct.sum_train_yy, rtol=1e-9, atol=1e-15)
    assert np.allclose(
        fold_validation_power(design, combined),
        fold_validation_power(design, direct),
        rtol=1e-8,
        atol=1e-12,
    )


def test_increasing_snr_does_not_systematically_reduce_estimated_power() -> None:
    lattice, folds, joint = _joint()
    designs = _designs(lattice, folds)
    null = replicate_statistics(
        designs,
        SimulatedPath("NULL_REPLICATE", 0, simulate_joint_paths(joint, 91, 0, 199)),
    )
    threshold = float(np.sort(null)[::-1][9])
    base = simulate_joint_paths(joint, 92, 0, 64)
    phases = np.asarray([phase_index(index) for index in range(64)])
    matrix = injection_matrix(lattice, 14.0)
    powers = []
    for snr in (0.0, 0.25, 0.5, 1.0, 2.0):
        scale = np.asarray(
            [
                injection_amplitude(
                    lattice, 14.0, phase_value(int(index)), snr, joint.innovation_rms
                )
                for index in phases
            ]
        )
        path = SimulatedPath("SYNTHETIC_REPLICATE", 0, base + scale[None, :] * matrix[:, phases])
        powers.append(detection_power(replicate_statistics(designs, path), threshold))
    assert all(later >= earlier - 0.08 for earlier, later in zip(powers, powers[1:], strict=False))
    assert powers[-1] > powers[0]


# ---------------------------------------------------------------------------------
# Gate arithmetic
# ---------------------------------------------------------------------------------


def _fidelity(status: str = "PASS") -> dict[str, Any]:
    return {
        "null_method": "TRAINING_ONLY_AR_SIEVE",
        "block_expected_observations": 42,
        "block_length_tuned_after_observation": False,
        "training_only": True,
        "validation_results_used": False,
        "fidelity_replicates": 999,
        "material_failures": [] if status == "PASS" else ["DEV-2024/absolute_acf_lag540"],
        "material_failure_count": 0 if status == "PASS" else 1,
        "preregistration": {"artifact_sha256": "0" * 64},
        "NULL_FIDELITY_STATUS": status,
    }


def _benchmark(joint: str = "PASS", compute: str = "PASS") -> dict[str, Any]:
    return {
        "joint_replication": {
            "joint_replication_method": "JOINT_NESTED_PREFIX_CAUSAL_SIEVE_PATH_V1",
            "cross_fold_dependence_handling": "SINGLE_JOINT_PATH",
            "shared_history_handling": "NESTED_PREFIX",
            "folds_simulated_independently": False,
            "joint_pooled_sd": 0.002,
            "independent_pooled_sd": 0.0015,
            "pooled_sd_ratio": 1.33,
            "JOINT_REPLICATION_STATUS": joint,
        },
        "compute": {
            "frequencies_per_fold": {},
            "training_observations_per_fold": {},
            "validation_observations_per_fold": {},
            "elements_per_replicate": 1,
            "benchmark_replicates": 50,
            "benchmark_elapsed_seconds": 1.0,
            "projected_runtime_seconds": 600.0,
            "peak_memory_mib": 100.0,
            "optimizations": ["X"],
            "replicates_reduced": False,
            "grid_coarsened": False,
            "COMPUTATIONAL_STATUS": compute,
        },
    }


def _detectability(gate_power: dict[float, float]) -> dict[str, Any]:
    cells = [
        {"period_days": period, "snr": snr, "power": gate_power[period] if snr == GATE_SNR else 0.1}
        for period in CALIBRATION_PERIOD_DAYS
        for snr in SNR_GRID
    ]
    return {
        "null_replicates": NULL_REPLICATES,
        "synthetic_replicates_per_cell": SYNTHETIC_REPLICATES_PER_CELL,
        "phase_grid_count": PHASE_COUNT,
        "injected_return_rms_by_snr": {},
        "log_price_amplitude": {
            f"{period:g}": [0.0] * len(SNR_GRID) for period in CALIBRATION_PERIOD_DAYS
        },
        "minimum_detectable_snr": {f"{period:g}": None for period in CALIBRATION_PERIOD_DAYS},
        "cells": cells,
    }


def test_power_gate_requires_every_frozen_period_at_the_gate_snr() -> None:
    passing = _detectability(dict.fromkeys(CALIBRATION_PERIOD_DAYS, 0.9))
    gate = evaluate_power_gate(_fidelity(), _benchmark(), passing)
    assert gate["P2_POWER_GATE_STATUS"] == READY
    assert gate["gate_snr"] == GATE_SNR == 0.50
    assert gate["target_power"] == TARGET_POWER == 0.80
    for period in CALIBRATION_PERIOD_DAYS:
        weakened = dict.fromkeys(CALIBRATION_PERIOD_DAYS, 0.9)
        weakened[period] = 0.7999
        failing = evaluate_power_gate(_fidelity(), _benchmark(), _detectability(weakened))
        assert failing["P2_POWER_GATE_STATUS"] == REDESIGN


@pytest.mark.parametrize(
    "fidelity_status,joint_status,compute_status",
    [
        (REDESIGN, "PASS", "PASS"),
        ("PASS", REDESIGN, "PASS"),
        ("PASS", "PASS", REDESIGN),
    ],
)
def test_failed_prerequisite_gate_blocks_actual_execution(
    fidelity_status: str, joint_status: str, compute_status: str
) -> None:
    fidelity = _fidelity(fidelity_status)
    benchmark = _benchmark(joint_status, compute_status)
    gate = evaluate_power_gate(fidelity, benchmark, None)
    assert gate["P2_POWER_GATE_STATUS"] == REDESIGN
    assert gate["prerequisites_pass"] is False
    assert gate["detectability"] is None
    assert gate["actual_execution_authorized"] is False
    assert gate["preregistration_authorized"] is False
    with pytest.raises(PrepModeViolation):
        evaluate_power_gate(
            fidelity, benchmark, _detectability(dict.fromkeys(CALIBRATION_PERIOD_DAYS, 0.99))
        )


def test_critical_value_and_binomial_helpers_are_deterministic() -> None:
    sample = np.arange(4999, dtype=float)
    assert critical_value(sample) == 4749.0
    assert detection_power(np.asarray([1.0, 2.0, 3.0]), 1.5) == pytest.approx(2 / 3)
    low, high = binomial_interval(1600, 2000)
    assert 0.0 <= low < 0.8 < high <= 1.0


def test_power_gate_markdown_mirrors_the_machine_readable_gate() -> None:
    from app.research.cycle_structure import render_power_gate_markdown

    gate = evaluate_power_gate(_fidelity(), _benchmark(), None)
    markdown = render_power_gate_markdown(gate)
    assert "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED = False" in markdown
    assert f"P2_POWER_GATE_STATUS: {gate['P2_POWER_GATE_STATUS']}" in markdown
    assert "detectability curves were not run" in markdown


# ---------------------------------------------------------------------------------
# Scientific accounting
# ---------------------------------------------------------------------------------


def test_scientific_accounting_is_unchanged_by_this_preparation() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["experiments_completed"] == 26
    assert state["adaptive_search"]["sealed_queries"] == 0
    assert state["sealed_evaluations_completed"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False
    ledger = json.loads(
        (ROOT / "reports/statistics/MATERIAL-HYPOTHESIS-LEDGER-V1.json").read_text(encoding="utf-8")
    )
    assert ledger["known_material_hypothesis_count"] == 12
    assert ledger["known_family_size"] == 12
    cycle = state["cycle_foundation"]
    assert cycle["material_economic_hypotheses_executed"] == 0
    assert cycle["actual_market_result_inspected"] is False
    assert cycle["economic_strategy_created"] is False
    assert cycle["implemented_components"] == []
    assert cycle["maximum_diagnostics"] == 2 and cycle["diagnostic_count"] <= 2


# ---------------------------------------------------------------------------------
# Installed development data
# ---------------------------------------------------------------------------------


@pytest.mark.skipif(not available(), reason="installed development data required")
def test_installed_grids_follow_the_frozen_causal_representation() -> None:
    import pyarrow.parquet as pq
    from app.research.cycle_structure_lab import load_grids

    grids = load_grids(ROOT)
    table = pq.read_table(ROOT / "data/derived/BTCUSDT-4h.parquet")
    times = table["open_time"].cast("int64").to_numpy()
    close = np.asarray(table["close"].to_numpy(), dtype=np.float64)
    complete = np.asarray(table["complete"].to_numpy(zero_copy_only=False), dtype=bool)
    usable = complete[1:] & complete[:-1] & (np.diff(times) == BAR_US)
    assert grids.eligible_returns == int(usable.sum())
    assert np.all(grids.lattice.times_us <= utc_us(CUTOFF))
    # Ineligible slots stay empty; a gap is dropped, never interpolated.
    assert np.all(grids.returns[~grids.lattice.eligible] == 0.0)
    slot = int((times[1] - grids.lattice.start_us) // BAR_US)
    assert grids.returns[slot] == pytest.approx(math.log(close[1]) - math.log(close[0]))
    assert np.all(grids.returns[grids.training_horizon :] == 0.0)
    for fold in grids.folds:
        assert fold.train_stop <= grids.training_horizon
        with pytest.raises(PrepModeViolation):
            grids.validation_returns(fold)


@pytest.mark.skipif(not available(), reason="installed development data required")
def test_installed_folds_apply_the_frozen_ninety_day_embargo() -> None:
    from app.research.cycle_structure_lab import load_grids

    grids = load_grids(ROOT)
    protocol = load_protocol()
    for fold, record in zip(grids.folds, protocol["folds"], strict=True):
        assert fold.fold_id == record["fold_id"]
        start = grids.lattice.start_us
        assert start + fold.validation_start * BAR_US == utc_us(record["validation_start"])
        assert (fold.validation_start - fold.train_stop) * BAR_US == EMBARGO_DAYS * 86_400_000_000
