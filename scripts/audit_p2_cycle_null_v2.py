"""Preregister, execute, and verify the append-only P2 Cycle Null V2 gates.

The execution order is fail-closed: block support, unchanged training-only fidelity,
joint-replication proof, compute benchmark, then prospective synthetic detectability.
No mode can load real outer-validation returns or compute the actual P2 market result.
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
    ABSOLUTE_ACF_LAGS,
    CALIBRATION_PERIOD_DAYS,
    FIDELITY_REPLICATES,
    GATE_SNR,
    NULL_REPLICATES,
    PASS,
    PHASE_COUNT,
    PRIMARY_ALPHA,
    REALIZED_VOLATILITY_HORIZONS,
    REDESIGN,
    RETURN_ACF_LAGS,
    SEED,
    SNR_GRID,
    SYNTHETIC_REPLICATES_PER_CELL,
    TARGET_POWER,
    VARIANCE_RATIO_HORIZONS,
    FoldDesign,
    FoldProjection,
    SimulatedPath,
    assert_no_result_leakage,
    binomial_interval,
    combine,
    critical_value,
    fidelity_criteria,
    injection_amplitude,
    injection_matrix,
    injection_path,
    phase_index,
    phase_value,
    pooled_statistic,
    project,
    replicate_statistics,
)
from app.research.cycle_structure import (
    fold_validation_power as _fold_validation_power,
)
from app.research.cycle_structure_v2 import (
    BLOCK_EXPECTED_OBSERVATIONS_V2,
    JOINT_REPLICATION_METHOD_V2,
    MINIMUM_LAG_540_SURVIVAL,
    NULL_METHOD_V2,
    NULL_V1_DISPOSITION,
    NULL_V2_ID,
    STREAM_BENCHMARK_V2,
    STREAM_FIDELITY_V2,
    STREAM_NULL_V2,
    STREAM_SUPPORT_V2,
    STREAM_SYNTHETIC_V2,
    SUPPORT_LAGS,
    SUPPORT_REPLICATES,
    JointLongBlockDesign,
    evaluate_power_gate_v2,
    null_paths_v2,
    simulate_joint_paths_v2,
    synthetic_base_paths_v2,
)
from app.research.statistical_governance import json_bytes

POWER_DIR = ROOT / "reports/power"
V1_PREREGISTRATION = POWER_DIR / "P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1.json"
PREREGISTRATION = POWER_DIR / "P2-CYCLE-NULL-V2-PREREGISTRATION.json"
BLOCK_SUPPORT = POWER_DIR / "P2-CYCLE-NULL-V2-BLOCK-SUPPORT.json"
FIDELITY = POWER_DIR / "P2-CYCLE-NULL-V2-FIDELITY.json"
COMPUTE = POWER_DIR / "P2-CYCLE-NULL-V2-COMPUTE.json"
DETECTABILITY = POWER_DIR / "P2-CYCLE-NULL-V2-DETECTABILITY.json"
GATE_JSON = POWER_DIR / "P2-CYCLE-POWER-GATE-V2.json"
GATE_MD = POWER_DIR / "P2-CYCLE-POWER-GATE-V2.md"

V1_FROZEN_HASHES = {
    "reports/power/P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1.json": (
        "7bc16573c460fb6949b6dffbd8968fabf842d7f5c0a763ec63fc14e1ba5f151a"
    ),
    "reports/power/P2-CYCLE-NULL-FIDELITY-V1.json": (
        "846abb4344aff653051810dfa2f1bfc535a8423f18f459dab674a3bc94492d02"
    ),
    "reports/power/P2-CYCLE-COMPUTE-BENCHMARK-V1.json": (
        "81c2c1df0b831ea50269b188dc0bb38a5e672c40d66cee8b7d0e324d068a4d9c"
    ),
    "reports/power/P2-CYCLE-FOUNDATION-POWER-GATE-V1.json": (
        "664da38072570c24aca09971e9a7c4db91ef4144d52c4795dca2a4f5b27320cb"
    ),
    "reports/power/P2-CYCLE-FOUNDATION-POWER-GATE-V1.md": (
        "f9d3af4ce7f6da84d0076e13c60e62688f2bebd35a459179854aec082901869f"
    ),
}

BATCH = 250
JOINT_PROOF_REPLICATES = 120
BENCHMARK_REPLICATES = 50
RUNTIME_BUDGET_SECONDS = 14_400.0
POOLED_SD_RATIO_TOLERANCE = 0.02
SELECTION_AGREEMENT_TOLERANCE = 0.10


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _rounded(value: float) -> float:
    return round(float(value), 10)


def _batches(total: int, size: int) -> list[tuple[int, int]]:
    return [(start, min(size, total - start)) for start in range(0, total, size)]


def assert_v1_artifacts_unchanged() -> None:
    for relative, expected in V1_FROZEN_HASHES.items():
        actual = sha256_bytes(ROOT / relative)
        if actual != expected:
            raise ValueError(f"Null V1 artifact changed: {relative}")


def preregistration_artifact() -> dict[str, Any]:
    v1 = json.loads(V1_PREREGISTRATION.read_text(encoding="utf-8"))
    criteria = fidelity_criteria()
    if v1["criteria"] != criteria:
        raise ValueError("implemented fidelity thresholds drifted from immutable Null V1")
    return {
        "schema_version": 1,
        "artifact_id": "P2-CYCLE-NULL-V2-PREREGISTRATION",
        "design_id": "BTC_TIME_CYCLE_STRUCTURE_V1",
        "null_id": NULL_V2_ID,
        "null_method": NULL_METHOD_V2,
        "purpose": (
            "Freeze Null V2 and the unchanged Null V1 fidelity contract before any V2 "
            "block-support or fidelity value is measured."
        ),
        "null_v1_disposition": NULL_V1_DISPOSITION,
        "immutable_v1_criterion_artifact": {
            "path": V1_PREREGISTRATION.relative_to(ROOT).as_posix(),
            "sha256": sha256_text(V1_PREREGISTRATION),
        },
        "thresholds_unchanged_from_v1": True,
        "criteria": criteria,
        "criterion_semantics": v1["criterion_semantics"],
        "statistic_families": {
            "marginal_dispersion_and_tails": [
                "return_sd",
                "excess_kurtosis",
                "tail_ratio_q995_q50",
            ],
            "return_autocorrelation_short_memory_lags": list(RETURN_ACF_LAGS),
            "absolute_return_dependence_long_lags": list(ABSOLUTE_ACF_LAGS),
            "multi_day_realized_volatility_horizons": [
                {"name": name, "observations": observations}
                for name, observations in REALIZED_VOLATILITY_HORIZONS
            ],
            "variance_ratio_horizons": list(VARIANCE_RATIO_HORIZONS),
        },
        "training_only": True,
        "validation_results_used": False,
        "raw_returns_resampled_directly": True,
        "canonical_gaps_interpolated": False,
        "donor_blocks_cross_canonical_gaps": False,
        "forced_gap_termination": True,
        "mean_model": None,
        "volatility_model": None,
        "ar_garch_har_figarch_used": False,
        "expected_block_observations": BLOCK_EXPECTED_OBSERVATIONS_V2,
        "expected_block_days_nominal": 180,
        "block_length_rationale": (
            "Twice the longest searched 90-day period, fixed before V2 fidelity measurement."
        ),
        "alternative_block_lengths_tested": False,
        "alternative_block_lengths_may_be_tested_after_measurement": False,
        "ideal_same_block_survival": {
            str(lag): _rounded((1.0 - 1.0 / BLOCK_EXPECTED_OBSERVATIONS_V2) ** lag)
            for lag in SUPPORT_LAGS
        },
        "ideal_survival_is_observed_btc_target": False,
        "block_support_gate": {
            "measured_before_fidelity": True,
            "lags_four_hour_intervals": list(SUPPORT_LAGS),
            "minimum_same_block_survival_at_lag540_every_fold": (MINIMUM_LAG_540_SURVIVAL),
            "failure_status": REDESIGN,
            "failure_action": (
                "STOP_WITHOUT_CHANGING_BLOCK_LENGTH_OR_GAP_SEMANTICS_AND_RETURN_TO_"
                "RESEARCH_DIRECTOR"
            ),
        },
        "fidelity_replicates": FIDELITY_REPLICATES,
        "support_replicates": SUPPORT_REPLICATES,
        "seed": SEED,
        "rng_streams": {
            "null": STREAM_NULL_V2,
            "synthetic": STREAM_SYNTHETIC_V2,
            "fidelity": STREAM_FIDELITY_V2,
            "support": STREAM_SUPPORT_V2,
            "benchmark": STREAM_BENCHMARK_V2,
        },
        "joint_replication_method": JOINT_REPLICATION_METHOD_V2,
        "donor_pool_by_stage": (
            "LATEST_TRAINING_ONLY_PREFIX_HISTORICALLY_AVAILABLE_AT_CAUSAL_STAGE"
        ),
        "shared_history_handling": (
            "NESTED_PREFIXES_SHARE_IDENTICAL_GENERATED_SLOTS_AND_EARLIER_SIMULATED_"
            "VALIDATION_REAPPEARS_IN_LATER_SIMULATED_TRAINING"
        ),
        "cross_fold_dependence_handling": "ONE_COMPLETE_CHRONOLOGY_PER_REPLICATE",
        "folds_simulated_independently": False,
        "null_replicates": NULL_REPLICATES,
        "synthetic_replicates_per_cell": SYNTHETIC_REPLICATES_PER_CELL,
        "period_days": list(CALIBRATION_PERIOD_DAYS),
        "phase_count": PHASE_COUNT,
        "snr_grid": list(SNR_GRID),
        "target_power": TARGET_POWER,
        "gate_snr": GATE_SNR,
        "decision_rule": (
            "NULL_V2_FIDELITY_STATUS is PASS only when every unchanged V1 material "
            "criterion passes in every fold; otherwise REDESIGN_REQUIRED."
        ),
        "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED": False,
    }


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


def run_joint_proof_v2(
    designs: tuple[FoldDesign, ...], joint: JointLongBlockDesign
) -> dict[str, Any]:
    slot_sets = [set(design.train_slots.tolist()) for design in designs]
    validation_sets = [set(design.validation_slots.tolist()) for design in designs]
    nested = all(slot_sets[index] < slot_sets[index + 1] for index in range(len(slot_sets) - 1))
    reused = [
        len(validation_sets[index] & slot_sets[index + 1]) for index in range(len(slot_sets) - 1)
    ]
    joint_path = SimulatedPath(
        "BENCHMARK_REPLICATE",
        0,
        simulate_joint_paths_v2(joint, STREAM_BENCHMARK_V2, 0, JOINT_PROOF_REPLICATES),
    )
    powers = [_fold_validation_power(design, project(design, joint_path)) for design in designs]
    selections = [_selected_indices(design, joint_path) for design in designs]
    weights = [design.validation_count for design in designs]
    pooled = pooled_statistic(powers, weights)

    independent_powers = []
    independent_selections = []
    for index, design in enumerate(designs):
        path = SimulatedPath(
            "BENCHMARK_REPLICATE",
            0,
            simulate_joint_paths_v2(
                joint, STREAM_BENCHMARK_V2 + 10 * (index + 1), 0, JOINT_PROOF_REPLICATES
            ),
        )
        independent_powers.append(_fold_validation_power(design, project(design, path)))
        independent_selections.append(_selected_indices(design, path))
    independent_pooled = pooled_statistic(independent_powers, weights)

    def agreement(items: list[np.ndarray]) -> float:
        result = []
        for index in range(len(items) - 1):
            earlier = designs[index].frequencies[items[index]]
            later = designs[index + 1].frequencies[items[index + 1]]
            result.append(
                float(np.mean(np.abs(later - earlier) <= SELECTION_AGREEMENT_TOLERANCE * earlier))
            )
        return float(np.mean(result))

    joint_sd = float(np.std(pooled, ddof=1))
    independent_sd = float(np.std(independent_pooled, ddof=1))
    ratio = joint_sd / independent_sd
    joint_agreement = agreement(selections)
    independent_agreement = agreement(independent_selections)
    required = {
        "single_path_per_replicate": True,
        "nested_training_prefixes_identical_within_a_replicate": nested,
        "earlier_validation_slots_reused_in_later_training": all(value > 0 for value in reused),
        "joint_pooled_sd_at_least_independent": ratio >= 1.0 - POOLED_SD_RATIO_TOLERANCE,
        "adjacent_fold_selection_more_concordant_than_independent": (
            joint_agreement >= independent_agreement
        ),
    }
    status = PASS if all(required.values()) else REDESIGN
    return {
        "joint_replication_method": JOINT_REPLICATION_METHOD_V2,
        "donor_pool_by_stage": joint.donor_pool_by_stage,
        "shared_history_handling": joint.shared_history_handling,
        "cross_fold_dependence_handling": joint.cross_fold_dependence_handling,
        "folds_simulated_independently": False,
        "stage_bounds": list(joint.stage_bounds),
        "shared_training_slots_with_next_fold": [len(item) for item in slot_sets[:-1]],
        "earlier_validation_slots_reused_in_later_training": reused,
        "joint_proof_replicates": JOINT_PROOF_REPLICATES,
        "joint_pooled_sd": _rounded(joint_sd),
        "independent_pooled_sd": _rounded(independent_sd),
        "pooled_sd_ratio": _rounded(ratio),
        "joint_adjacent_selection_agreement": _rounded(joint_agreement),
        "independent_adjacent_selection_agreement": _rounded(independent_agreement),
        "checks": {
            **required,
            "fold_nulls_concatenated_from_independent_draws": False,
        },
        "JOINT_REPLICATION_STATUS": status,
    }


def _expand(source: FoldProjection, phases: np.ndarray) -> FoldProjection:
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


def run_benchmark_v2(
    grids: Any, designs: tuple[FoldDesign, ...], joint: JointLongBlockDesign
) -> dict[str, Any]:
    elements = sum(
        design.frequency_count * (design.train_count + design.validation_count)
        for design in designs
    )
    phases = np.asarray([phase_index(index) for index in range(BENCHMARK_REPLICATES)])
    started = time.perf_counter()
    path = SimulatedPath(
        "BENCHMARK_REPLICATE",
        0,
        simulate_joint_paths_v2(joint, STREAM_BENCHMARK_V2, 0, BENCHMARK_REPLICATES),
    )
    statistics = replicate_statistics(designs, path)
    path_seconds = time.perf_counter() - started
    if statistics.shape != (BENCHMARK_REPLICATES,):
        raise ValueError("V2 benchmark produced the wrong replicate count")
    period = CALIBRATION_PERIOD_DAYS[0]
    unit = injection_matrix(grids.lattice, period)
    base = [project(design, path) for design in designs]
    injected = [
        _expand(project(design, injection_path(grids.lattice, period)), phases)
        for design in designs
    ]
    crosses = [_cross_terms(design, path.values, unit, phases) for design in designs]
    scale = np.full(BENCHMARK_REPLICATES, 0.5, dtype=np.float64)
    started = time.perf_counter()
    cell = pooled_statistic(
        [
            _fold_validation_power(
                design, combine(base[index], injected[index], crosses[index], scale)
            )
            for index, design in enumerate(designs)
        ],
        [design.validation_count for design in designs],
    )
    combination_seconds = time.perf_counter() - started
    if cell.shape != (BENCHMARK_REPLICATES,):
        raise ValueError("V2 combination benchmark produced the wrong replicate count")
    path_projections = NULL_REPLICATES + SYNTHETIC_REPLICATES_PER_CELL
    injection_projections = len(CALIBRATION_PERIOD_DAYS) * PHASE_COUNT
    combination_cells = (
        len(CALIBRATION_PERIOD_DAYS) * len(SNR_GRID) * (SYNTHETIC_REPLICATES_PER_CELL)
    )
    projected = (path_seconds / BENCHMARK_REPLICATES) * (
        path_projections + injection_projections
    ) + (combination_seconds / BENCHMARK_REPLICATES) * combination_cells
    memory = (
        grids.lattice.slot_count * BATCH * 8 * 3
        + sum(design.frequency_count for design in designs) * BATCH * 8 * 8
        + max(design.train_count for design in designs) * 512 * 8 * 2
    ) / (1024 * 1024)
    return {
        "frequencies_per_fold": {design.fold_id: design.frequency_count for design in designs},
        "training_observations_per_fold": {
            design.fold_id: design.train_count for design in designs
        },
        "validation_observations_per_fold": {
            design.fold_id: design.validation_count for design in designs
        },
        "elements_per_replicate": elements,
        "benchmark_replicates": BENCHMARK_REPLICATES,
        "benchmark_elapsed_seconds": _rounded(path_seconds + combination_seconds),
        "benchmark_path_seconds": _rounded(path_seconds),
        "benchmark_combination_seconds": _rounded(combination_seconds),
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
        "block_length_changed": False,
        "approximation_for_speed": False,
        "COMPUTATIONAL_STATUS": PASS if projected <= RUNTIME_BUDGET_SECONDS else REDESIGN,
    }


def run_detectability_v2(
    grids: Any, designs: tuple[FoldDesign, ...], joint: JointLongBlockDesign
) -> dict[str, Any]:
    lattice = grids.lattice
    weights = [design.validation_count for design in designs]
    innovation_rms = joint.innovation_rms
    null = np.empty(NULL_REPLICATES, dtype=np.float64)
    for first, count in _batches(NULL_REPLICATES, BATCH):
        null[first : first + count] = replicate_statistics(
            designs, null_paths_v2(joint, first, count)
        )
    threshold = critical_value(null)
    units = {period: injection_matrix(lattice, period) for period in CALIBRATION_PERIOD_DAYS}
    injected = {
        period: [project(design, injection_path(lattice, period)) for design in designs]
        for period in CALIBRATION_PERIOD_DAYS
    }
    amplitudes = {
        (period, phase, snr): injection_amplitude(
            lattice, period, phase_value(phase), snr, innovation_rms
        )
        for period in CALIBRATION_PERIOD_DAYS
        for phase in range(PHASE_COUNT)
        for snr in SNR_GRID
    }
    detections = {(period, snr): 0 for period in CALIBRATION_PERIOD_DAYS for snr in SNR_GRID}
    for first, count in _batches(SYNTHETIC_REPLICATES_PER_CELL, BATCH):
        base_path = synthetic_base_paths_v2(joint, first, count)
        phases = np.asarray([phase_index(first + column) for column in range(count)])
        base = [project(design, base_path) for design in designs]
        for period in CALIBRATION_PERIOD_DAYS:
            expanded = [_expand(item, phases) for item in injected[period]]
            crosses = [
                _cross_terms(design, base_path.values, units[period], phases) for design in designs
            ]
            for snr in SNR_GRID:
                scale = np.asarray([amplitudes[(period, int(phase), snr)] for phase in phases])
                statistic = pooled_statistic(
                    [
                        _fold_validation_power(
                            design,
                            combine(base[index], expanded[index], crosses[index], scale),
                        )
                        for index, design in enumerate(designs)
                    ],
                    weights,
                )
                detections[(period, snr)] += int(np.sum(statistic > threshold))
    cells = []
    minimum = {}
    for period in CALIBRATION_PERIOD_DAYS:
        key = f"{period:g}"
        minimum[key] = None
        for snr in SNR_GRID:
            successes = detections[(period, snr)]
            power = successes / SYNTHETIC_REPLICATES_PER_CELL
            low, high = binomial_interval(successes, SYNTHETIC_REPLICATES_PER_CELL)
            cells.append(
                {
                    "period_days": period,
                    "snr": snr,
                    "detections": successes,
                    "replicates": SYNTHETIC_REPLICATES_PER_CELL,
                    "power": _rounded(power),
                    "wilson_95_low": low,
                    "wilson_95_high": high,
                }
            )
            if minimum[key] is None and power >= TARGET_POWER:
                minimum[key] = snr
    return {
        "schema_version": 1,
        "artifact_id": "P2-CYCLE-NULL-V2-DETECTABILITY",
        "null_replicates": NULL_REPLICATES,
        "synthetic_replicates_per_cell": SYNTHETIC_REPLICATES_PER_CELL,
        "phase_count": PHASE_COUNT,
        "seed": SEED,
        "alpha": PRIMARY_ALPHA,
        "critical_pooled_power": _rounded(threshold),
        "effect_scale": "SNR_CYCLE_RMS_INJECTED_RETURN_OVER_TRAINING_RMS_NULL_INNOVATION",
        "injection_domain": "LOG_PRICE_THEN_DIFFERENCE_TO_4H_LOG_RETURN",
        "cells": cells,
        "minimum_detectable_snr": minimum,
        "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED": False,
    }


def render_markdown(gate: dict[str, Any]) -> str:
    statuses = gate["prerequisite_gates"]
    lines = [
        "# P2 Cycle Null V2 + Power Gate",
        "",
        f"- P2_POWER_GATE_STATUS: {gate['P2_POWER_GATE_STATUS']}",
        f"- BLOCK_SUPPORT_STATUS: {statuses['BLOCK_SUPPORT_STATUS']}",
        f"- NULL_V2_FIDELITY_STATUS: {statuses['NULL_V2_FIDELITY_STATUS']}",
        f"- JOINT_REPLICATION_STATUS: {statuses['JOINT_REPLICATION_STATUS']}",
        f"- COMPUTATIONAL_STATUS: {statuses['COMPUTATIONAL_STATUS']}",
        f"- detectability executed: {gate['detectability'] is not None}",
        "- actual BTC cycle result observed: False",
        "- actual selected BTC period: NOT_COMPUTED",
        "- actual validation powers: NOT_COMPUTED",
        "- actual pooled primary statistic: NOT_COMPUTED",
        "- actual structural p-value: NOT_COMPUTED",
        "- actual cycle classification: NOT_EMITTED",
        "",
        "The actual structural experiment remains DESIGNED_NOT_PREREGISTERED_NOT_EXECUTED.",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(outputs: dict[Path, bytes]) -> None:
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def write_gate(
    support: dict[str, Any],
    fidelity: dict[str, Any] | None,
    joint: dict[str, Any] | None,
    compute: dict[str, Any] | None,
    detectability: dict[str, Any] | None,
) -> dict[str, Any]:
    gate = evaluate_power_gate_v2(support, fidelity, joint, compute, detectability)
    assert_no_result_leakage(gate)
    write_outputs(
        {
            GATE_JSON: json_bytes(gate),
            GATE_MD: render_markdown(gate).encode("utf-8"),
        }
    )
    return gate


def preregister() -> int:
    assert_v1_artifacts_unchanged()
    artifact = preregistration_artifact()
    assert_no_result_leakage(artifact)
    write_outputs({PREREGISTRATION: json_bytes(artifact)})
    print("P2 Cycle Null V2 preregistered")
    return 0


def generate() -> int:
    from app.research.cycle_structure_v2_lab import (
        block_support_report,
        build_designs,
        build_donors,
        build_joint_design_v2,
        fidelity_report_v2,
        load_grids,
    )

    assert_v1_artifacts_unchanged()
    if not PREREGISTRATION.is_file():
        raise SystemExit("commit the Null V2 preregistration before measuring support")
    if json_bytes(preregistration_artifact()) != PREREGISTRATION.read_bytes():
        raise SystemExit("Null V2 preregistration drift")
    grids = load_grids(ROOT)
    donors = build_donors(grids)
    joint_design = build_joint_design_v2(grids, donors)

    support = block_support_report(grids, donors, ROOT)
    assert_no_result_leakage(support)
    write_outputs({BLOCK_SUPPORT: json_bytes(support)})
    if support["BLOCK_SUPPORT_STATUS"] != PASS:
        gate = write_gate(support, None, None, None, None)
        print(f"BLOCK_SUPPORT_STATUS: {support['BLOCK_SUPPORT_STATUS']}")
        print(f"P2_POWER_GATE_STATUS: {gate['P2_POWER_GATE_STATUS']}")
        return 0

    fidelity = fidelity_report_v2(grids, joint_design, support, ROOT)
    assert_no_result_leakage(fidelity)
    write_outputs({FIDELITY: json_bytes(fidelity)})
    if fidelity["NULL_V2_FIDELITY_STATUS"] != PASS:
        gate = write_gate(support, fidelity, None, None, None)
        print(f"NULL_V2_FIDELITY_STATUS: {fidelity['NULL_V2_FIDELITY_STATUS']}")
        print(f"P2_POWER_GATE_STATUS: {gate['P2_POWER_GATE_STATUS']}")
        return 0

    designs = build_designs(grids)
    joint = run_joint_proof_v2(designs, joint_design)
    compute = run_benchmark_v2(grids, designs, joint_design)
    compute_artifact = {
        "schema_version": 1,
        "artifact_id": "P2-CYCLE-NULL-V2-COMPUTE",
        "joint_replication": joint,
        "compute": compute,
        "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED": False,
    }
    assert_no_result_leakage(compute_artifact)
    write_outputs({COMPUTE: json_bytes(compute_artifact)})
    detectability = None
    if joint["JOINT_REPLICATION_STATUS"] == PASS and compute["COMPUTATIONAL_STATUS"] == PASS:
        detectability = run_detectability_v2(grids, designs, joint_design)
        assert_no_result_leakage(detectability)
        write_outputs({DETECTABILITY: json_bytes(detectability)})
    gate = write_gate(support, fidelity, joint, compute, detectability)
    print(f"P2_POWER_GATE_STATUS: {gate['P2_POWER_GATE_STATUS']}")
    return 0


def load_optional(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def check() -> int:
    assert_v1_artifacts_unchanged()
    if json_bytes(preregistration_artifact()) != PREREGISTRATION.read_bytes():
        raise SystemExit("Null V2 preregistration drift")
    support = json.loads(BLOCK_SUPPORT.read_text(encoding="utf-8"))
    fidelity = load_optional(FIDELITY)
    compute_artifact = load_optional(COMPUTE)
    joint = compute_artifact["joint_replication"] if compute_artifact else None
    compute = compute_artifact["compute"] if compute_artifact else None
    detectability = load_optional(DETECTABILITY)
    gate = evaluate_power_gate_v2(support, fidelity, joint, compute, detectability)
    for artifact in (support, fidelity, compute_artifact, detectability, gate):
        if artifact is not None:
            assert_no_result_leakage(artifact)
            if artifact["ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED"]:
                raise SystemExit("a V2 artifact claims an observed P2 market result")
    expected = {
        GATE_JSON: json_bytes(gate),
        GATE_MD: render_markdown(gate).encode("utf-8"),
    }
    drift = [path for path, content in expected.items() if path.read_bytes() != content]
    if drift:
        raise SystemExit("P2 Cycle Null V2 gate drift")
    if support["BLOCK_SUPPORT_STATUS"] != PASS and any(
        path.is_file() for path in (FIDELITY, COMPUTE, DETECTABILITY)
    ):
        raise SystemExit("failed block support did not stop downstream execution")
    print("P2 Cycle Null V2 audit: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregister", action="store_true")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if sum((args.preregister, args.generate, args.check)) != 1:
        raise SystemExit("choose exactly one mode")
    if args.preregister:
        return preregister()
    return generate() if args.generate else check()


if __name__ == "__main__":
    raise SystemExit(main())
