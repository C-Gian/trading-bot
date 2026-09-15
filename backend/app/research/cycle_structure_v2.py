"""Gap-safe raw-return stationary bootstrap for the P2 Cycle Null V2.

This module is append-only relative to the rejected V1 null.  It reuses only the
mathematically unchanged frozen P2 lattice, GLS, fidelity-statistic, and synthetic
injection helpers.  It contains no entry point that can evaluate the actual BTC cycle
result: paths accepted by the spectral pipeline retain the simulated provenance guard
defined in :mod:`app.research.cycle_structure`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from .cycle_structure import (
    CALIBRATION_PERIOD_DAYS,
    GATE_SNR,
    NULL_REPLICATES,
    PASS,
    REDESIGN,
    SEED,
    SNR_GRID,
    SYNTHETIC_REPLICATES_PER_CELL,
    TARGET_POWER,
    CycleFold,
    CycleLattice,
    PrepModeViolation,
    SimulatedPath,
    assert_no_result_leakage,
)

NULL_V1_DISPOSITION = "FAILED_FIDELITY_REJECTED_FOR_INFERENCE"
NULL_V2_ID = "P2_CYCLE_NULL_V2"
NULL_METHOD_V2 = "TRAINING_ONLY_RAW_RETURN_STATIONARY_BLOCK_BOOTSTRAP_EXPECTED_1080_V2"
JOINT_REPLICATION_METHOD_V2 = "JOINT_NESTED_PREFIX_CAUSAL_LONG_BLOCK_PATH_V2"
BLOCK_EXPECTED_OBSERVATIONS_V2 = 1080
BLOCK_LENGTHS_TESTED_V2 = (BLOCK_EXPECTED_OBSERVATIONS_V2,)
SUPPORT_LAGS = (42, 90, 180, 360, 540)
MINIMUM_LAG_540_SURVIVAL = 0.50
SUPPORT_REPLICATES = 999
STREAM_NULL_V2 = 11
STREAM_SYNTHETIC_V2 = 12
STREAM_FIDELITY_V2 = 13
STREAM_SUPPORT_V2 = 14
STREAM_BENCHMARK_V2 = 15


@dataclass(frozen=True)
class DonorTopology:
    """One causal stage's training-only raw-return donor pool and gap topology."""

    fold_id: str
    values: np.ndarray
    eligible: np.ndarray
    training_observations: int
    segment_starts: np.ndarray
    segment_stops: np.ndarray
    run_length_from_start: np.ndarray

    def __post_init__(self) -> None:
        if self.values.shape != self.eligible.shape:
            raise ValueError("donor values and eligibility must align")
        if self.values.ndim != 1 or self.eligible.dtype != np.bool_:
            raise ValueError("donor pool must be a one-dimensional masked series")
        if self.training_observations != self.values.size:
            raise ValueError("donor pool may not extend beyond its causal training boundary")
        if self.segment_starts.shape != self.segment_stops.shape:
            raise ValueError("donor segment bounds must align")
        if not np.any(self.eligible):
            raise ValueError("donor pool has no eligible raw returns")
        if np.any(self.values[~self.eligible] != 0.0):
            raise ValueError("canonical gaps must remain empty, never interpolated")
        for start, stop in zip(self.segment_starts, self.segment_stops, strict=True):
            if not (0 <= start < stop <= self.values.size):
                raise ValueError("invalid donor segment")
            if not np.all(self.eligible[start:stop]):
                raise ValueError("a donor segment crosses a canonical gap")

    @property
    def admissible_starts(self) -> np.ndarray:
        """Every genuine training return is a legal stationary-bootstrap start."""
        return np.flatnonzero(self.eligible)

    @property
    def segment_lengths(self) -> np.ndarray:
        return self.segment_stops - self.segment_starts

    @property
    def raw_return_rms(self) -> float:
        selected = self.values[self.eligible]
        return math.sqrt(float(selected @ selected) / selected.size)


def build_donor_topology(
    fold_id: str, values: np.ndarray, eligible: np.ndarray, training_observations: int
) -> DonorTopology:
    """Measure contiguous eligible runs without filling or bridging a source gap."""
    if values.shape != eligible.shape or values.size != training_observations:
        raise ValueError("training-only donor inputs must share the frozen prefix")
    padded = np.concatenate((np.asarray([False]), eligible, np.asarray([False])))
    changes = np.diff(padded.astype(np.int8))
    starts = np.flatnonzero(changes == 1)
    stops = np.flatnonzero(changes == -1)
    runway = np.zeros(values.size, dtype=np.int64)
    for start, stop in zip(starts, stops, strict=True):
        runway[start:stop] = np.arange(stop - start, 0, -1, dtype=np.int64)
    return DonorTopology(
        fold_id=fold_id,
        values=values.copy(),
        eligible=eligible.copy(),
        training_observations=training_observations,
        segment_starts=starts,
        segment_stops=stops,
        run_length_from_start=runway,
    )


def stationary_raw_return_draw(
    generator: np.random.Generator, topology: DonorTopology, length: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Draw raw returns in geometric blocks, terminating before every source gap.

    The return tuple is ``(values, source_indices, block_ids, forced_terminations)``.
    A continuation step is legal only when the next source index is an eligible return
    exactly one canonical 4h slot later.  Otherwise the current block ends and a new
    uniformly sampled legal training-only donor start is used.
    """
    if length <= 0:
        raise ValueError("a bootstrap draw needs positive length")
    starts = topology.admissible_starts
    values = np.empty(length, dtype=np.float64)
    indices = np.empty(length, dtype=np.int64)
    blocks = np.empty(length, dtype=np.int64)
    forced = np.zeros(length, dtype=np.bool_)
    source = int(generator.choice(starts))
    block = 0
    for position in range(length):
        if position:
            stochastic_restart = bool(generator.random() < (1.0 / BLOCK_EXPECTED_OBSERVATIONS_V2))
            next_source = source + 1
            continuation_legal = next_source < topology.values.size and bool(
                topology.eligible[next_source]
            )
            if stochastic_restart or not continuation_legal:
                if not stochastic_restart and not continuation_legal:
                    forced[position] = True
                source = int(generator.choice(starts))
                block += 1
            else:
                source = next_source
        values[position] = topology.values[source]
        indices[position] = source
        blocks[position] = block
    return values, indices, blocks, forced


def exact_same_block_survival(topology: DonorTopology, lag: int) -> float:
    """Exact same-block survival under geometric restarts and actual gap runways."""
    if lag < 0:
        raise ValueError("support lag must be non-negative")
    starts = topology.admissible_starts
    geometric = (1.0 - 1.0 / BLOCK_EXPECTED_OBSERVATIONS_V2) ** lag
    topology_share = float(np.mean(topology.run_length_from_start[starts] > lag))
    return geometric * topology_share


def block_length_distribution(topology: DonorTopology) -> dict[str, Any]:
    """Exact block-length law after stochastic and forced gap/boundary termination."""
    starts = topology.admissible_starts
    runways = topology.run_length_from_start[starts]
    maximum = int(runways.max())
    q = 1.0 - 1.0 / BLOCK_EXPECTED_OBSERVATIONS_V2
    # P(L >= k) = q^(k-1) P(runway >= k), for integer block length L >= 1.
    survival = np.asarray(
        [
            (q ** (length - 1)) * float(np.mean(runways >= length))
            for length in range(1, maximum + 1)
        ]
    )

    def quantile(probability: float) -> int:
        # Smallest k with P(L <= k) >= probability, equivalently P(L >= k+1) <= 1-p.
        candidates = np.flatnonzero(survival[1:] <= 1.0 - probability)
        return int(candidates[0] + 1) if candidates.size else maximum

    forced_probability = float(np.mean(q**runways))
    return {
        "mean_observations": round(float(survival.sum()), 10),
        "median_observations": quantile(0.50),
        "p90_observations": quantile(0.90),
        "p95_observations": quantile(0.95),
        "p99_observations": quantile(0.99),
        "maximum_observations": maximum,
        "forced_gap_or_training_boundary_probability": round(forced_probability, 10),
    }


@dataclass(frozen=True)
class JointLongBlockDesign:
    """One V2 bootstrap chronology shared by all six nested outer folds."""

    lattice: CycleLattice
    folds: tuple[CycleFold, ...]
    donors: tuple[DonorTopology, ...]
    stage_bounds: tuple[int, ...]
    stage_donors: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.stage_bounds) != len(self.stage_donors) + 1:
            raise ValueError("every causal stage needs one donor pool")
        if self.stage_bounds[0] != 0 or self.stage_bounds[-1] != self.lattice.slot_count:
            raise ValueError("joint stages must tile the complete chronology")
        if any(
            later <= earlier
            for earlier, later in zip(self.stage_bounds, self.stage_bounds[1:], strict=False)
        ):
            raise ValueError("joint stages must be strictly chronological")
        for stage, donor_index in enumerate(self.stage_donors):
            if not 0 <= donor_index < len(self.donors):
                raise ValueError("stage refers to an unknown donor pool")
            if stage and self.donors[donor_index].training_observations > self.stage_bounds[stage]:
                raise PrepModeViolation("a causal stage donor pool contains its future")

    @property
    def innovation_rms(self) -> float:
        total = 0.0
        slots = 0
        for stage, donor_index in enumerate(self.stage_donors):
            width = self.stage_bounds[stage + 1] - self.stage_bounds[stage]
            rms = self.donors[donor_index].raw_return_rms
            total += width * rms * rms
            slots += width
        return math.sqrt(total / slots)

    @property
    def donor_pool_by_stage(self) -> list[dict[str, Any]]:
        return [
            {
                "stage_start_slot": self.stage_bounds[stage],
                "stage_stop_slot": self.stage_bounds[stage + 1],
                "donor_fold": self.donors[index].fold_id,
                "donor_training_stop": self.donors[index].training_observations,
            }
            for stage, index in enumerate(self.stage_donors)
        ]

    @property
    def shared_history_handling(self) -> str:
        return (
            "NESTED_PREFIX_TRAINING_WINDOWS_SHARE_IDENTICAL_GENERATED_SLOTS_AND_EARLIER_"
            "SIMULATED_VALIDATION_SLOTS_REAPPEAR_IN_LATER_SIMULATED_TRAINING"
        )

    @property
    def cross_fold_dependence_handling(self) -> str:
        return "ONE_COMPLETE_SIMULATED_CHRONOLOGY_PER_REPLICATE_NOT_INDEPENDENT_FOLD_DRAWS"


def replicate_seed_v2(stream: int, replicate: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(stream, replicate)))


def simulate_joint_paths_v2(
    design: JointLongBlockDesign, stream: int, first_replicate: int, replicates: int
) -> np.ndarray:
    """Generate complete causal V2 chronologies, one path per replicate."""
    if replicates <= 0:
        raise ValueError("a simulation batch needs at least one replicate")
    paths = np.empty((design.lattice.slot_count, replicates), dtype=np.float64)
    for column in range(replicates):
        generator = replicate_seed_v2(stream, first_replicate + column)
        for stage, donor_index in enumerate(design.stage_donors):
            start = design.stage_bounds[stage]
            stop = design.stage_bounds[stage + 1]
            drawn, _, _, _ = stationary_raw_return_draw(
                generator, design.donors[donor_index], stop - start
            )
            paths[start:stop, column] = drawn
    return paths


def null_paths_v2(
    design: JointLongBlockDesign, first_replicate: int, replicates: int
) -> SimulatedPath:
    return SimulatedPath(
        "NULL_REPLICATE",
        first_replicate,
        simulate_joint_paths_v2(design, STREAM_NULL_V2, first_replicate, replicates),
    )


def synthetic_base_paths_v2(
    design: JointLongBlockDesign, first_replicate: int, replicates: int
) -> SimulatedPath:
    return SimulatedPath(
        "SYNTHETIC_REPLICATE",
        first_replicate,
        simulate_joint_paths_v2(design, STREAM_SYNTHETIC_V2, first_replicate, replicates),
    )


def prerequisite_statuses(
    block_support: dict[str, Any],
    fidelity: dict[str, Any] | None,
    joint: dict[str, Any] | None,
    compute: dict[str, Any] | None,
) -> dict[str, str]:
    return {
        "BLOCK_SUPPORT_STATUS": block_support["BLOCK_SUPPORT_STATUS"],
        "NULL_V2_FIDELITY_STATUS": (
            fidelity["NULL_V2_FIDELITY_STATUS"] if fidelity else "NOT_RUN_BLOCKED"
        ),
        "JOINT_REPLICATION_STATUS": (
            joint["JOINT_REPLICATION_STATUS"] if joint else "NOT_RUN_BLOCKED"
        ),
        "COMPUTATIONAL_STATUS": compute["COMPUTATIONAL_STATUS"] if compute else "NOT_RUN_BLOCKED",
    }


def evaluate_power_gate_v2(
    block_support: dict[str, Any],
    fidelity: dict[str, Any] | None,
    joint: dict[str, Any] | None,
    compute: dict[str, Any] | None,
    detectability: dict[str, Any] | None,
) -> dict[str, Any]:
    """Fail closed unless all four V2 prerequisites pass before detectability."""
    statuses = prerequisite_statuses(block_support, fidelity, joint, compute)
    ready = all(value == PASS for value in statuses.values())
    if detectability is not None and not ready:
        raise PrepModeViolation("detectability cannot exist before every V2 prerequisite passes")
    powers: dict[str, float] = {}
    status = REDESIGN
    if ready and detectability is not None:
        for period in CALIBRATION_PERIOD_DAYS:
            cell = next(
                item
                for item in detectability["cells"]
                if item["period_days"] == period and item["snr"] == GATE_SNR
            )
            powers[f"{period:g}"] = cell["power"]
        if all(value >= TARGET_POWER for value in powers.values()):
            status = "READY_FOR_PREREGISTRATION"
    gate = {
        "schema_version": 1,
        "artifact_id": "P2-CYCLE-POWER-GATE-V2",
        "design_id": "BTC_TIME_CYCLE_STRUCTURE_V1",
        "null_id": NULL_V2_ID,
        "null_method": NULL_METHOD_V2,
        "expected_block_observations": BLOCK_EXPECTED_OBSERVATIONS_V2,
        "alternative_block_lengths_tested": False,
        "ar_garch_har_figarch_used": False,
        "prerequisite_gates": statuses,
        "prerequisites_pass": ready,
        "detectability": detectability,
        "power_at_gate_snr_by_period": powers,
        "null_replicates": NULL_REPLICATES,
        "synthetic_replicates_per_cell": SYNTHETIC_REPLICATES_PER_CELL,
        "period_days": list(CALIBRATION_PERIOD_DAYS),
        "phase_count": 16,
        "snr_grid": list(SNR_GRID),
        "gate_snr": GATE_SNR,
        "target_power": TARGET_POWER,
        "P2_POWER_GATE_STATUS": status,
        "preregistration_authorized": status == "READY_FOR_PREREGISTRATION",
        "actual_execution_authorized": False,
        "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED": False,
        "leakage_guard": {
            "actual_training_selected_period_computed": False,
            "actual_validation_power_computed": False,
            "actual_pooled_statistic_computed": False,
            "actual_structural_p_value_computed": False,
            "market_classification_emitted": False,
            "real_validation_returns_loaded": False,
            "sealed_data_queried": False,
            "assets_expanded": False,
            "cycle_trading_implemented": False,
            "real_money_authorized": False,
        },
    }
    assert_no_result_leakage(gate)
    return gate
