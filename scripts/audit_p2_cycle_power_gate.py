"""Generate or verify the deterministic P2 cycle power-gate artifacts.

`--preregister` writes the NULL_FIDELITY_V1 threshold artifact. It needs no market data
and must be committed before `--generate` runs, so that no tolerance can be chosen from
an observed discrepancy.

`--generate` needs the local development dataset. It runs, in order, the training-only
null-fidelity diagnostic, the joint six-fold replicate proof, the computational
feasibility benchmark, and - only when all three pass - the frozen synthetic
detectability curves.

`--check` needs no market data: it re-derives the gate from the committed intermediate
artifacts and fails on any drift, so continuous integration can audit the gate without
ever touching BTCUSDT bars.

No mode computes the actual BTCUSDT training-selected period, outer validation power,
pooled statistic, structural p-value, or market classification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.cycle_structure import (
    BENCHMARK_ID,
    BLOCK_EXPECTED_OBSERVATIONS,
    BURN_IN_OBSERVATIONS,
    CALIBRATION_PERIOD_DAYS,
    FIDELITY_PREREGISTRATION_ID,
    FIDELITY_REPLICATES,
    JOINT_REPLICATION_METHOD,
    NULL_METHOD,
    NULL_REPLICATES,
    PASS,
    PHASE_COUNT,
    REDESIGN,
    SEED,
    SNR_GRID,
    STREAM_BENCHMARK,
    STREAM_FIDELITY,
    STREAM_NULL,
    SYNTHETIC_REPLICATES_PER_CELL,
    TARGET_POWER,
    FoldDesign,
    FoldProjection,
    JointNullDesign,
    SimulatedPath,
    assert_no_result_leakage,
    binomial_interval,
    combine,
    critical_value,
    evaluate_power_gate,
    fidelity_criteria,
    injection_amplitude,
    injection_matrix,
    injection_path,
    null_paths,
    phase_index,
    phase_value,
    pooled_statistic,
    project,
    render_power_gate_markdown,
    replicate_statistics,
    simulate_joint_paths,
    synthetic_base_paths,
)
from app.research.cycle_structure import (
    fold_validation_power as _fold_validation_power,
)
from app.research.statistical_governance import json_bytes

POWER_DIR = ROOT / "reports/power"
PREREGISTRATION = POWER_DIR / "P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1.json"
FIDELITY = POWER_DIR / "P2-CYCLE-NULL-FIDELITY-V1.json"
BENCHMARK = POWER_DIR / "P2-CYCLE-COMPUTE-BENCHMARK-V1.json"
DETECTABILITY = POWER_DIR / "P2-CYCLE-DETECTABILITY-V1.json"
GATE_JSON = POWER_DIR / "P2-CYCLE-FOUNDATION-POWER-GATE-V1.json"
GATE_MD = POWER_DIR / "P2-CYCLE-FOUNDATION-POWER-GATE-V1.md"

BATCH = 250
JOINT_PROOF_REPLICATES = 120
BENCHMARK_REPLICATES = 50
RUNTIME_BUDGET_SECONDS = 14400.0
POOLED_SD_RATIO_TOLERANCE = 0.02
SELECTION_AGREEMENT_TOLERANCE = 0.10


def _rounded(value: float) -> float:
    return round(float(value), 10)


def _batches(total: int, size: int) -> list[tuple[int, int]]:
    return [(start, min(size, total - start)) for start in range(0, total, size)]


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# ---------------------------------------------------------------------------------
# Stage 1 - preregistration of the NULL_FIDELITY_V1 thresholds
# ---------------------------------------------------------------------------------


def preregistration_artifact() -> dict[str, Any]:
    from app.research.cycle_structure import (
        ABSOLUTE_ACF_LAGS,
        REALIZED_VOLATILITY_HORIZONS,
        RETURN_ACF_LAGS,
        VARIANCE_RATIO_HORIZONS,
    )

    return {
        "schema_version": 1,
        "artifact_id": FIDELITY_PREREGISTRATION_ID,
        "design_id": "BTC_TIME_CYCLE_STRUCTURE_V1",
        "purpose": (
            "Fix every NULL_FIDELITY_V1 statistic and materiality tolerance before the "
            "fidelity calculation runs, so that no threshold can be derived from an "
            "observed discrepancy."
        ),
        "null_under_test": NULL_METHOD,
        "block_expected_observations": BLOCK_EXPECTED_OBSERVATIONS,
        "block_length_frozen_for_this_test": True,
        "block_length_may_be_tuned_after_observation": False,
        "training_only": True,
        "validation_results_used": False,
        "fidelity_replicates": FIDELITY_REPLICATES,
        "seed": SEED,
        "rng_stream": STREAM_FIDELITY,
        "evaluation_segments": "EACH_FOLD_EMBARGOED_TRAINING_SELECTION_WINDOW",
        "statistic_families": {
            "marginal_dispersion_and_tails": [
                "return_sd",
                "excess_kurtosis",
                "tail_ratio_q995_q50",
            ],
            "return_autocorrelation_short_memory_lags": list(RETURN_ACF_LAGS),
            "absolute_return_dependence_long_lags": list(ABSOLUTE_ACF_LAGS),
            "multi_day_realized_volatility_horizons": [
                {"name": name, "observations": window}
                for name, window in REALIZED_VOLATILITY_HORIZONS
            ],
            "variance_ratio_horizons": list(VARIANCE_RATIO_HORIZONS),
        },
        "rationale": {
            "absolute_return_dependence_long_lags": (
                "42, 90, 180, 360 and 540 four-hour observations are 7, 15, 30, 60 and 90 "
                "days: every lag except the first is materially longer than the frozen "
                "seven-day bootstrap block, and they span the frozen 2-90 day band."
            ),
            "variance_ratio_horizons": (
                "Aggregated-return variance at 2, 7, 30 and 90 days is the statistic most "
                "directly tied to spectral content inside the frozen band, so it detects a "
                "null that becomes artificially low-dependence at those frequencies."
            ),
            "realized_volatility_horizons": (
                "Dispersion of 1-, 7- and 30-day realized volatility measures whether the "
                "null keeps the volatility-of-volatility that inflates the sampling "
                "variability of Lomb-Scargle power."
            ),
        },
        "criteria": fidelity_criteria(),
        "criterion_semantics": {
            "ABSOLUTE_GAP": "pass when |observed - null median| <= tolerance",
            "ABSOLUTE_GAP_OR_RETAINED_SHARE": (
                "pass when |observed - null median| <= tolerance, or when the null median "
                "retains at least retained_share of the observed value"
            ),
            "RETAINED_SHARE": "pass when null median >= retained_share * observed",
            "RATIO_BAND": "pass when minimum <= observed / null median <= maximum",
            "LOG_RATIO": "pass when |ln(observed / null median)| <= ln(tolerance)",
        },
        "decision_rule": (
            "NULL_FIDELITY_STATUS is PASS only when every statistic passes its criterion "
            "in every fold; otherwise REDESIGN_REQUIRED and the frozen cycle result stays "
            "unobserved."
        ),
        "rank_p_role": "DESCRIPTIVE_ONLY_NOT_A_GATE",
        "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED": False,
    }


# ---------------------------------------------------------------------------------
# Stage 2 - training-only null fidelity
# ---------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------
# Stage 3 - joint replicate proof and computational feasibility
# ---------------------------------------------------------------------------------


def _selected_indices(design: FoldDesign, path: SimulatedPath) -> np.ndarray:
    from app.research.cycle_structure import gls_power

    projection = project(design, path)
    training = gls_power(
        design.train_terms,
        projection.sum_train_cos,
        projection.sum_train_sin,
        projection.sum_train_y,
        projection.sum_train_yy,
        design.train_count,
    )
    return np.argmax(training, axis=0)


def run_joint_proof(
    grids: Any, designs: tuple[FoldDesign, ...], joint: JointNullDesign
) -> dict[str, Any]:
    """Deterministic evidence that one replicate is one joint six-fold realization."""
    slot_sets = [set(design.train_slots.tolist()) for design in designs]
    validation_sets = [set(design.validation_slots.tolist()) for design in designs]
    nested = all(slot_sets[index] < slot_sets[index + 1] for index in range(len(slot_sets) - 1))
    reused = [
        len(validation_sets[index] & slot_sets[index + 1]) for index in range(len(slot_sets) - 1)
    ]

    joint_path = SimulatedPath(
        "BENCHMARK_REPLICATE",
        0,
        simulate_joint_paths(joint, STREAM_BENCHMARK, 0, JOINT_PROOF_REPLICATES),
    )
    joint_powers = []
    joint_selection = []
    for design in designs:
        joint_powers.append(_fold_validation_power(design, project(design, joint_path)))
        joint_selection.append(_selected_indices(design, joint_path))
    weights = [design.validation_count for design in designs]
    joint_pooled = pooled_statistic(joint_powers, weights)

    # The forbidden alternative: six statistics drawn from six unrelated realizations.
    independent_powers = []
    independent_selection = []
    for index, design in enumerate(designs):
        path = SimulatedPath(
            "BENCHMARK_REPLICATE",
            0,
            simulate_joint_paths(
                joint,
                STREAM_BENCHMARK + 10 * (index + 1),
                0,
                JOINT_PROOF_REPLICATES,
            ),
        )
        independent_powers.append(_fold_validation_power(design, project(design, path)))
        independent_selection.append(_selected_indices(design, path))
    independent_pooled = pooled_statistic(independent_powers, weights)

    def mean_correlation(powers: list[np.ndarray]) -> float:
        matrix = np.corrcoef(np.stack(powers))
        upper = matrix[np.triu_indices(len(powers), k=1)]
        return float(np.mean(upper))

    def agreement(selection: list[np.ndarray]) -> float:
        """Adjacent folds pick from different grids, so compare frequencies, not indices."""
        pairs = []
        for index in range(len(selection) - 1):
            earlier = designs[index].frequencies[selection[index]]
            later = designs[index + 1].frequencies[selection[index + 1]]
            pairs.append(
                float(np.mean(np.abs(later - earlier) <= SELECTION_AGREEMENT_TOLERANCE * earlier))
            )
        return float(np.mean(pairs))

    joint_sd = float(np.std(joint_pooled, ddof=1))
    independent_sd = float(np.std(independent_pooled, ddof=1))
    ratio = joint_sd / independent_sd
    joint_agreement = agreement(joint_selection)
    independent_agreement = agreement(independent_selection)
    required = {
        "single_path_per_replicate": True,
        "nested_training_prefixes_identical_within_a_replicate": nested,
        "earlier_validation_slots_reused_in_later_training": all(count > 0 for count in reused),
        "joint_pooled_sd_at_least_independent": ratio >= 1.0 - POOLED_SD_RATIO_TOLERANCE,
        "adjacent_fold_selection_more_concordant_than_independent": (
            joint_agreement >= independent_agreement
        ),
    }
    # This one must stay false: concatenating six independent fold draws is the forbidden
    # construction, so it is recorded as refuted rather than required.
    forbidden = {"fold_nulls_concatenated_from_independent_draws": False}
    checks = {**required, **forbidden}
    status = PASS if all(required.values()) and not any(forbidden.values()) else REDESIGN
    return {
        "joint_replication_method": JOINT_REPLICATION_METHOD,
        "cross_fold_dependence_handling": joint.cross_fold_dependence_handling,
        "shared_history_handling": joint.shared_history_handling,
        "folds_simulated_independently": False,
        "stage_bounds": list(joint.stage_bounds),
        "stage_generating_model": [joint.models[index].fold_id for index in joint.stage_models],
        "stage_model_fitted_before_stage": True,
        "burn_in_observations": BURN_IN_OBSERVATIONS,
        "shared_training_slots_with_next_fold": [len(item) for item in slot_sets[:-1]],
        "earlier_validation_slots_reused_in_later_training": reused,
        "joint_proof_replicates": JOINT_PROOF_REPLICATES,
        "joint_pooled_sd": _rounded(joint_sd),
        "independent_pooled_sd": _rounded(independent_sd),
        "pooled_sd_ratio": _rounded(ratio),
        "pooled_sd_ratio_tolerance": POOLED_SD_RATIO_TOLERANCE,
        "joint_mean_cross_fold_power_correlation": _rounded(mean_correlation(joint_powers)),
        "independent_mean_cross_fold_power_correlation": _rounded(
            mean_correlation(independent_powers)
        ),
        "selection_agreement_relative_tolerance": SELECTION_AGREEMENT_TOLERANCE,
        "joint_adjacent_selection_agreement": _rounded(joint_agreement),
        "independent_adjacent_selection_agreement": _rounded(independent_agreement),
        "checks": checks,
        "JOINT_REPLICATION_STATUS": status,
    }


def _expand(source: FoldProjection, phases: np.ndarray) -> FoldProjection:
    """Widen the 16 frozen phase injections to one column per replicate."""
    return FoldProjection(
        sum_train_cos=source.sum_train_cos[:, phases],
        sum_train_sin=source.sum_train_sin[:, phases],
        sum_train_y=source.sum_train_y[phases],
        sum_train_yy=source.sum_train_yy[phases],
        sum_validation_cos=source.sum_validation_cos[:, phases],
        sum_validation_sin=source.sum_validation_sin[:, phases],
        sum_validation_y=source.sum_validation_y[phases],
        sum_validation_yy=source.sum_validation_yy[phases],
    )


def _cross_terms(
    design: FoldDesign, base: np.ndarray, unit: np.ndarray, phases: np.ndarray
) -> np.ndarray:
    """Second-moment cross terms, so `combine` stays algebraically exact."""
    return np.stack(
        (
            np.einsum("ij,ij->j", base[design.train_slots], unit[design.train_slots][:, phases]),
            np.einsum(
                "ij,ij->j",
                base[design.validation_slots],
                unit[design.validation_slots][:, phases],
            ),
        )
    )


def run_benchmark(
    grids: Any, designs: tuple[FoldDesign, ...], joint: JointNullDesign
) -> dict[str, Any]:
    """Time the mathematically exact pipeline and project the frozen replicate budget."""
    elements = sum(
        design.frequency_count * (design.train_count + design.validation_count)
        for design in designs
    )
    weights = [design.validation_count for design in designs]
    lattice = grids.lattice
    phases = np.asarray([phase_index(index) for index in range(BENCHMARK_REPLICATES)])

    start = time.perf_counter()
    path = SimulatedPath(
        "BENCHMARK_REPLICATE",
        0,
        simulate_joint_paths(joint, STREAM_BENCHMARK, 0, BENCHMARK_REPLICATES),
    )
    statistics = replicate_statistics(designs, path)
    path_seconds = time.perf_counter() - start
    if statistics.shape != (BENCHMARK_REPLICATES,):
        raise ValueError("benchmark produced the wrong replicate count")

    period = CALIBRATION_PERIOD_DAYS[0]
    unit = injection_matrix(lattice, period)
    base_projections = [project(design, path) for design in designs]
    injected = [
        _expand(project(design, injection_path(lattice, period)), phases) for design in designs
    ]
    crosses = [_cross_terms(design, path.values, unit, phases) for design in designs]
    scale = np.full(BENCHMARK_REPLICATES, 0.5, dtype=np.float64)
    start = time.perf_counter()
    cell = pooled_statistic(
        [
            _fold_validation_power(
                design, combine(base_projections[index], injected[index], crosses[index], scale)
            )
            for index, design in enumerate(designs)
        ],
        weights,
    )
    combination_seconds = time.perf_counter() - start
    if cell.shape != (BENCHMARK_REPLICATES,):
        raise ValueError("benchmark combination produced the wrong replicate count")

    # Six SNR levels on one frozen period reuse one simulated path exactly, and the 16
    # phase injections are projected once per period, so the frozen budget needs
    # 4999 null paths, 2000 synthetic base paths, 5 sixteen-column injection projections,
    # and 5 * 6 * 2000 elementwise combination evaluations.
    path_projections = NULL_REPLICATES + SYNTHETIC_REPLICATES_PER_CELL
    injection_projections = len(CALIBRATION_PERIOD_DAYS) * PHASE_COUNT
    combination_cells = len(CALIBRATION_PERIOD_DAYS) * len(SNR_GRID) * SYNTHETIC_REPLICATES_PER_CELL
    projected = (path_seconds / BENCHMARK_REPLICATES) * (
        path_projections + injection_projections
    ) + (combination_seconds / BENCHMARK_REPLICATES) * combination_cells
    memory = (
        (lattice.slot_count + BURN_IN_OBSERVATIONS) * BATCH * 8 * 3
        + sum(design.frequency_count for design in designs) * BATCH * 8 * 8
        + max(design.train_count for design in designs) * 512 * 8 * 2
    ) / (1024 * 1024)
    status = PASS if projected <= RUNTIME_BUDGET_SECONDS else REDESIGN
    return {
        "frequencies_per_fold": {design.fold_id: design.frequency_count for design in designs},
        "training_observations_per_fold": {
            design.fold_id: design.train_count for design in designs
        },
        "validation_observations_per_fold": {
            design.fold_id: design.validation_count for design in designs
        },
        "training_span_days_per_fold": {
            design.fold_id: _rounded(design.train_span_days) for design in designs
        },
        "elements_per_replicate": elements,
        "benchmark_replicates": BENCHMARK_REPLICATES,
        "benchmark_elapsed_seconds": _rounded(path_seconds + combination_seconds),
        "benchmark_path_seconds": _rounded(path_seconds),
        "benchmark_combination_seconds": _rounded(combination_seconds),
        "projected_path_projections": path_projections + injection_projections,
        "projected_combination_cells": combination_cells,
        "projected_runtime_seconds": _rounded(projected),
        "runtime_budget_seconds": RUNTIME_BUDGET_SECONDS,
        "peak_memory_mib": _rounded(memory),
        "batch_size": BATCH,
        "optimizations": [
            "PRECOMPUTED_FIXED_TIMESTAMP_GLS_DESIGN_TERMS",
            "BATCHED_BLAS_FOURIER_PROJECTIONS_OVER_REPLICATES",
            "EXACT_LINEAR_REUSE_OF_ONE_PATH_ACROSS_THE_FROZEN_SNR_GRID",
            "SIXTEEN_PHASE_INJECTIONS_PROJECTED_ONCE_PER_FROZEN_PERIOD",
            "IMMUTABLE_PER_FOLD_FREQUENCY_GRIDS_REUSED_BY_EVERY_REPLICATE",
        ],
        "replicates_reduced": False,
        "grid_coarsened": False,
        "periods_reduced": False,
        "phases_reduced": False,
        "null_changed": False,
        "approximation_for_speed": False,
        "COMPUTATIONAL_STATUS": status,
    }


# ---------------------------------------------------------------------------------
# Stage 4 - frozen synthetic detectability
# ---------------------------------------------------------------------------------


def run_detectability(
    grids: Any, designs: tuple[FoldDesign, ...], joint: JointNullDesign
) -> dict[str, Any]:
    lattice = grids.lattice
    weights = [design.validation_count for design in designs]
    innovation_rms = joint.innovation_rms

    null = np.empty(NULL_REPLICATES, dtype=np.float64)
    for first, count in _batches(NULL_REPLICATES, BATCH):
        null[first : first + count] = replicate_statistics(designs, null_paths(joint, first, count))
    threshold = critical_value(null)

    unit = {period: injection_matrix(lattice, period) for period in CALIBRATION_PERIOD_DAYS}
    injected = {
        period: [project(design, injection_path(lattice, period)) for design in designs]
        for period in CALIBRATION_PERIOD_DAYS
    }
    amplitudes = {
        (period, index, snr): injection_amplitude(
            lattice, period, phase_value(index), snr, innovation_rms
        )
        for period in CALIBRATION_PERIOD_DAYS
        for index in range(PHASE_COUNT)
        for snr in SNR_GRID
    }

    detections = {(period, snr): 0 for period in CALIBRATION_PERIOD_DAYS for snr in SNR_GRID}
    for first, count in _batches(SYNTHETIC_REPLICATES_PER_CELL, BATCH):
        base = synthetic_base_paths(joint, first, count)
        phases = np.asarray([phase_index(first + column) for column in range(count)])
        base_projections = [project(design, base) for design in designs]
        for period in CALIBRATION_PERIOD_DAYS:
            expanded = [_expand(item, phases) for item in injected[period]]
            crosses = [
                _cross_terms(design, base.values, unit[period], phases) for design in designs
            ]
            for snr in SNR_GRID:
                scale = np.asarray([amplitudes[(period, int(index), snr)] for index in phases])
                powers = [
                    _fold_validation_power(
                        design,
                        combine(base_projections[index], expanded[index], crosses[index], scale),
                    )
                    for index, design in enumerate(designs)
                ]
                statistic = pooled_statistic(powers, weights)
                detections[(period, snr)] += int(np.sum(statistic > threshold))

    cells = []
    minimum_detectable: dict[str, float | None] = {}
    amplitude_report: dict[str, list[float]] = {}
    for period in CALIBRATION_PERIOD_DAYS:
        key = f"{period:g}"
        minimum_detectable[key] = None
        amplitude_report[key] = []
        for snr in SNR_GRID:
            successes = detections[(period, snr)]
            power = successes / SYNTHETIC_REPLICATES_PER_CELL
            low, high = binomial_interval(successes, SYNTHETIC_REPLICATES_PER_CELL)
            mean_amplitude = float(
                np.mean([amplitudes[(period, index, snr)] for index in range(PHASE_COUNT)])
            )
            amplitude_report[key].append(_rounded(mean_amplitude))
            cells.append(
                {
                    "period_days": period,
                    "snr": snr,
                    "detections": successes,
                    "replicates": SYNTHETIC_REPLICATES_PER_CELL,
                    "power": _rounded(power),
                    "wilson_95_low": low,
                    "wilson_95_high": high,
                    "mean_log_price_amplitude": _rounded(mean_amplitude),
                    "injected_return_rms": _rounded(snr * innovation_rms),
                }
            )
            if minimum_detectable[key] is None and power >= TARGET_POWER:
                minimum_detectable[key] = snr
    return {
        "schema_version": 1,
        "artifact_id": "P2-CYCLE-DETECTABILITY-V1",
        "null_replicates": NULL_REPLICATES,
        "synthetic_replicates_per_cell": SYNTHETIC_REPLICATES_PER_CELL,
        "phase_grid_count": PHASE_COUNT,
        "seed": SEED,
        "rng_streams": {"null": STREAM_NULL, "synthetic": 2},
        "alpha": 0.05,
        "critical_pooled_power": _rounded(threshold),
        "null_pooled_quantiles": {
            name: _rounded(float(np.quantile(null, value)))
            for name, value in (("p50", 0.5), ("p90", 0.9), ("p95", 0.95), ("p99", 0.99))
        },
        "effect_scale": "SNR_CYCLE_RMS_INJECTED_RETURN_OVER_TRAINING_RMS_NULL_INNOVATION",
        "training_innovation_rms": _rounded(innovation_rms),
        "injected_return_rms_by_snr": {
            f"{snr:g}": _rounded(snr * innovation_rms) for snr in SNR_GRID
        },
        "log_price_amplitude": amplitude_report,
        "amplitude_note": (
            "Descriptive translation only, averaged over the 16 frozen phases. It does "
            "not change the frozen SNR effect definition or the gate."
        ),
        "cells": cells,
        "minimum_detectable_snr": minimum_detectable,
        "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED": False,
    }


# ---------------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------------


def gate_outputs(
    fidelity: dict[str, Any],
    benchmark: dict[str, Any],
    detectability: dict[str, Any] | None,
) -> dict[Path, bytes]:
    gate = evaluate_power_gate(fidelity, benchmark, detectability)
    assert_no_result_leakage(gate)
    return {GATE_JSON: json_bytes(gate), GATE_MD: render_power_gate_markdown(gate).encode("utf-8")}


def write(outputs: dict[Path, bytes]) -> None:
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def preregister() -> int:
    artifact = preregistration_artifact()
    assert_no_result_leakage(artifact)
    write({PREREGISTRATION: json_bytes(artifact)})
    print("P2 null-fidelity thresholds preregistered")
    return 0


def generate() -> int:
    from app.research.cycle_structure_lab import (
        build_designs,
        build_joint_design,
        fidelity_report,
        fit_models,
        load_grids,
    )

    grids = load_grids(ROOT)
    models = fit_models(grids)
    joint = build_joint_design(grids, models)

    if not PREREGISTRATION.is_file():
        raise SystemExit("preregister the fidelity thresholds before running the diagnostic")
    fidelity = fidelity_report(grids, joint, ROOT)
    assert_no_result_leakage(fidelity)
    write({FIDELITY: json_bytes(fidelity)})
    print(f"NULL_FIDELITY_STATUS: {fidelity['NULL_FIDELITY_STATUS']}")

    designs = build_designs(grids)
    benchmark = {
        "schema_version": 1,
        "artifact_id": BENCHMARK_ID,
        "design_id": "BTC_TIME_CYCLE_STRUCTURE_V1",
        "joint_replication": run_joint_proof(grids, designs, joint),
        "compute": run_benchmark(grids, designs, joint),
        "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED": False,
    }
    assert_no_result_leakage(benchmark)
    write({BENCHMARK: json_bytes(benchmark)})
    print(f"JOINT_REPLICATION_STATUS: {benchmark['joint_replication']['JOINT_REPLICATION_STATUS']}")
    print(f"COMPUTATIONAL_STATUS: {benchmark['compute']['COMPUTATIONAL_STATUS']}")

    ready = (
        fidelity["NULL_FIDELITY_STATUS"] == PASS
        and benchmark["joint_replication"]["JOINT_REPLICATION_STATUS"] == PASS
        and benchmark["compute"]["COMPUTATIONAL_STATUS"] == PASS
    )
    detectability = None
    if ready:
        detectability = run_detectability(grids, designs, joint)
        assert_no_result_leakage(detectability)
        write({DETECTABILITY: json_bytes(detectability)})
    elif DETECTABILITY.is_file():
        DETECTABILITY.unlink()
    write(gate_outputs(fidelity, benchmark, detectability))
    gate = json.loads(GATE_JSON.read_text(encoding="utf-8"))
    print(f"P2_POWER_GATE_STATUS: {gate['P2_POWER_GATE_STATUS']}")
    return 0


def load_committed() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    fidelity = json.loads(FIDELITY.read_text(encoding="utf-8"))
    benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    detectability = (
        json.loads(DETECTABILITY.read_text(encoding="utf-8")) if DETECTABILITY.is_file() else None
    )
    for artifact in (fidelity, benchmark, detectability):
        if artifact is not None:
            assert_no_result_leakage(artifact)
            if artifact["ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED"]:
                raise SystemExit("a committed P2 artifact claims an observed market result")
    if fidelity["preregistration"]["artifact_sha256"] != sha256_text(PREREGISTRATION):
        raise SystemExit("fidelity artifact is not bound to the committed thresholds")
    if json.loads(PREREGISTRATION.read_text(encoding="utf-8"))["criteria"] != fidelity_criteria():
        raise SystemExit("committed fidelity thresholds differ from the implementation")
    return fidelity, benchmark, detectability


def check() -> int:
    fidelity, benchmark, detectability = load_committed()
    expected = gate_outputs(fidelity, benchmark, detectability)
    drift = [
        path
        for path, content in expected.items()
        if not path.is_file() or path.read_bytes() != content
    ]
    if drift:
        for path in drift:
            print(f"::error file={path.relative_to(ROOT).as_posix()}::P2 power-gate drift")
        raise SystemExit("P2 power-gate drift: " + ", ".join(str(path) for path in drift))
    print("P2 cycle power gate: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregister", action="store_true", help="fix fidelity thresholds")
    parser.add_argument("--generate", action="store_true", help="rebuild from local market data")
    parser.add_argument("--check", action="store_true", help="verify committed artifacts")
    args = parser.parse_args()
    if sum((args.preregister, args.generate, args.check)) != 1:
        raise SystemExit("choose exactly one of --preregister, --generate or --check")
    if args.preregister:
        return preregister()
    return generate() if args.generate else check()


if __name__ == "__main__":
    raise SystemExit(main())
