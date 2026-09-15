"""Prospective power preparation for BTC_TIME_CYCLE_STRUCTURE_V1 (P2).

This module prepares, but never executes, the frozen structural cycle experiment. It
owns the deterministic mathematics of the frozen design: the Fourier-spaced frequency
grid, the floating-mean generalized Lomb-Scargle statistic, the training-only AR sieve
plus stationary residual block bootstrap null, the joint six-fold replicate semantics,
the null-fidelity diagnostic, and the synthetic detectability curves.

Two structural guards keep the actual BTC cycle outcome unreachable from here:

* the only spectral entry point, :func:`replicate_statistics`, accepts a
  :class:`SimulatedPath`, which can be constructed only by the simulators in this
  module; real market returns therefore cannot enter frequency selection;
* :func:`assert_no_result_leakage` fails closed on every artifact key that could carry
  an actual selected period, validation power, pooled statistic, p-value, or
  SUPPORTED / NOT_SUPPORTED classification.

Real validation-period returns are never loaded at all; only their timestamps are used,
to build the design quantities that the simulated chronology is evaluated on.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

DESIGN_ID = "BTC_TIME_CYCLE_STRUCTURE_V1"
HYPOTHESIS_ID = "BTC_TIME_CYCLE_STRUCTURE_V1"
PROTOCOL_ID = "P2_CYCLE_FOUNDATION_V1"
GATE_ID = "P2-CYCLE-FOUNDATION-POWER-GATE-V1"
FIDELITY_ID = "P2-CYCLE-NULL-FIDELITY-V1"
FIDELITY_PREREGISTRATION_ID = "P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1"
BENCHMARK_ID = "P2-CYCLE-COMPUTE-BENCHMARK-V1"

# --- frozen representation -------------------------------------------------------
BAR_HOURS = 4
BAR_US = BAR_HOURS * 3_600_000_000
DAY_US = 86_400_000_000
BARS_PER_DAY = 24 // BAR_HOURS
REPRESENTATION = "CONTIGUOUS_4H_CLOSE_TO_CLOSE_LOG_RETURN"

# --- frozen period band and grid -------------------------------------------------
BAND_MINIMUM_DAYS = 2.0
BAND_MAXIMUM_DAYS = 90.0
OVERSAMPLING = 4
ESTIMATOR = "FLOATING_MEAN_GENERALIZED_LOMB_SCARGLE"
SELECTION_RULE = "TRAINING_MAXIMUM_POWER_ONE_PERIOD_LONGER_PERIOD_TIE_BREAK"
EVALUATION_RULE = "VALIDATION_POWER_AT_TRAINING_SELECTED_FREQUENCY_ONLY"
EMBARGO_DAYS = 90

# --- frozen null -----------------------------------------------------------------
AR_MAXIMUM_ORDER = 42
AR_ORDER_SET = tuple(range(AR_MAXIMUM_ORDER + 1))
BLOCK_EXPECTED_OBSERVATIONS = 42
BURN_IN_OBSERVATIONS = 504
NULL_METHOD = (
    "TRAINING_ONLY_AR_SIEVE_BIC_0_TO_42_PLUS_STATIONARY_RESIDUAL_BLOCK_BOOTSTRAP_EXPECTED_42"
)
JOINT_REPLICATION_METHOD = "JOINT_NESTED_PREFIX_CAUSAL_SIEVE_PATH_V1"

# --- frozen inference budget -----------------------------------------------------
PRIMARY_ALPHA = 0.05
TARGET_POWER = 0.80
NULL_REPLICATES = 4999
SYNTHETIC_REPLICATES_PER_CELL = 2000
FIDELITY_REPLICATES = 999
SEED = 20260915
CALIBRATION_PERIOD_DAYS = (3.0, 7.0, 14.0, 30.0, 60.0)
PHASE_COUNT = 16
SNR_GRID = (0.0, 0.10, 0.25, 0.50, 0.75, 1.00)
GATE_SNR = 0.50

# --- deterministic RNG stream identifiers ---------------------------------------
STREAM_NULL = 1
STREAM_SYNTHETIC = 2
STREAM_FIDELITY = 3
STREAM_BENCHMARK = 4

READY = "READY_FOR_PREREGISTRATION"
REDESIGN = "REDESIGN_REQUIRED"
PASS = "PASS"

FORBIDDEN_ARTIFACT_KEYS = frozenset(
    {
        "actual_cycle_classification",
        "actual_p_value",
        "actual_pooled_statistic",
        "actual_selected_frequency_per_day",
        "actual_selected_period_days",
        "actual_validation_power",
        "bartels_statistic",
        "btc_cycle_p_value",
        "btc_primary_statistic",
        "btc_selected_period_days",
        "cross_fold_period_stability",
        "cycle_p_value",
        "observed_pooled_validation_power",
        "observed_selected_period_days",
        "observed_validation_power",
        "pooled_validation_power",
        "primary_classification",
        "selected_frequency_per_day",
        "selected_period_days",
        "structural_classification",
        "structural_p_value",
        "validation_power_by_fold",
    }
)


PATH_PROVENANCE = frozenset(
    {
        "NULL_REPLICATE",
        "SYNTHETIC_REPLICATE",
        "BENCHMARK_REPLICATE",
        "DETERMINISTIC_INJECTION",
    }
)


class PrepModeViolation(ValueError):
    """A caller attempted an operation that could expose the P2 cycle outcome."""


def _rounded(value: float) -> float:
    return round(float(value), 10)


def assert_no_result_leakage(value: Any, pointer: str = "") -> None:
    """Fail closed if any artifact key could carry the unobserved P2 cycle outcome."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_ARTIFACT_KEYS:
                raise PrepModeViolation(f"forbidden P2 outcome key at {pointer}/{key}")
            assert_no_result_leakage(child, f"{pointer}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_result_leakage(child, f"{pointer}/{index}")


# ---------------------------------------------------------------------------------
# Lattice, folds and frequency grid
# ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class CycleLattice:
    """A regular 4h return lattice plus the canonical eligibility mask.

    A lattice slot `i` denotes the close-to-close log return ending at
    `start_us + i * BAR_US`. `eligible` marks the slots whose two endpoint 4h bars are
    both canonically complete and exactly consecutive. Ineligible slots are never
    interpolated: they carry no observation, and the frozen pipeline masks them out
    after simulation exactly as it masks them out of the real series.
    """

    start_us: int
    slot_count: int
    eligible: np.ndarray

    def __post_init__(self) -> None:
        if self.start_us % BAR_US:
            raise ValueError("lattice origin must sit on a canonical 4h boundary")
        if self.slot_count <= 0 or self.eligible.shape != (self.slot_count,):
            raise ValueError("eligibility mask must cover every lattice slot")
        if self.eligible.dtype != np.bool_:
            raise ValueError("eligibility mask must be boolean")

    @property
    def times_us(self) -> np.ndarray:
        return self.start_us + np.arange(self.slot_count, dtype=np.int64) * BAR_US

    @property
    def times_days(self) -> np.ndarray:
        """Elapsed days from the lattice origin; GLS power is time-origin invariant."""
        return np.arange(self.slot_count, dtype=np.float64) * (BAR_HOURS / 24.0)


@dataclass(frozen=True)
class CycleFold:
    """One outer fold expressed as half-open lattice index ranges.

    `train_stop` is the embargoed training-selection boundary: the frozen 90-day
    pre-validation embargo is already removed, so no slot in `[train_stop,
    validation_start)` can influence frequency selection.
    """

    fold_id: str
    train_stop: int
    validation_start: int
    validation_stop: int

    def __post_init__(self) -> None:
        if not 0 < self.train_stop <= self.validation_start < self.validation_stop:
            raise ValueError("fold ranges must be chronological and non-empty")


def frequency_grid(span_days: float) -> np.ndarray:
    """Fourier spacing `1 / T_train` oversampled by 4, clipped to the frozen band."""
    if not math.isfinite(span_days) or span_days <= 0:
        raise ValueError("training span must be a positive number of days")
    minimum = 1.0 / BAND_MAXIMUM_DAYS
    maximum = 1.0 / BAND_MINIMUM_DAYS
    spacing = 1.0 / (OVERSAMPLING * span_days)
    count = math.floor((maximum - minimum) / spacing) + 1
    if count < 2:
        raise ValueError("training span is too short to resolve the frozen band")
    return minimum + np.arange(count, dtype=np.float64) * spacing


def _design_terms(times_days: np.ndarray, frequencies: np.ndarray) -> dict[str, np.ndarray]:
    """Timestamp-only floating-mean GLS terms; reused by every replicate."""
    count = times_days.size
    if count < 3:
        raise ValueError("a GLS segment needs at least three observations")
    weight = 1.0 / count
    cos_sum = np.empty(frequencies.size, dtype=np.float64)
    sin_sum = np.empty(frequencies.size, dtype=np.float64)
    cos2_sum = np.empty(frequencies.size, dtype=np.float64)
    sin2_sum = np.empty(frequencies.size, dtype=np.float64)
    for start in range(0, frequencies.size, 256):
        block = frequencies[start : start + 256]
        angle = (2.0 * math.pi) * block[:, None] * times_days[None, :]
        cos_sum[start : start + 256] = np.cos(angle).sum(axis=1)
        sin_sum[start : start + 256] = np.sin(angle).sum(axis=1)
        double = 2.0 * angle
        cos2_sum[start : start + 256] = np.cos(double).sum(axis=1)
        sin2_sum[start : start + 256] = np.sin(double).sum(axis=1)
    mean_cos = cos_sum * weight
    mean_sin = sin_sum * weight
    # cos^2 = (1 + cos 2x) / 2, sin^2 = (1 - cos 2x) / 2, cos sin = sin 2x / 2.
    term_cc = 0.5 * (1.0 + cos2_sum * weight) - mean_cos * mean_cos
    term_ss = 0.5 * (1.0 - cos2_sum * weight) - mean_sin * mean_sin
    term_cs = 0.5 * (sin2_sum * weight) - mean_cos * mean_sin
    determinant = term_cc * term_ss - term_cs * term_cs
    if not np.all(np.isfinite(determinant)) or np.any(determinant <= 0.0):
        raise ValueError("degenerate GLS design at a frozen grid frequency")
    return {
        "mean_cos": mean_cos,
        "mean_sin": mean_sin,
        "cc": term_cc,
        "ss": term_ss,
        "cs": term_cs,
        "determinant": determinant,
    }


def gls_power(
    terms: dict[str, np.ndarray],
    sum_cos: np.ndarray,
    sum_sin: np.ndarray,
    sum_y: np.ndarray,
    sum_yy: np.ndarray,
    count: int,
) -> np.ndarray:
    """Normalized floating-mean generalized Lomb-Scargle power in `[0, 1]`.

    `sum_cos` and `sum_sin` are the raw Fourier sums `sum(y cos)` and `sum(y sin)` with
    shape `(frequencies, replicates)`; `sum_y` and `sum_yy` are per-replicate. Splitting
    the statistic this way is an exact algebraic reformulation: the only replicate-
    dependent work is a matrix product against the fixed timestamp design.
    """
    weight = 1.0 / count
    mean_y = sum_y * weight
    variance = sum_yy * weight - mean_y * mean_y
    if np.any(variance <= 0.0):
        raise ValueError("a replicate segment has no variance to explain")
    centered_cos = sum_cos * weight - terms["mean_cos"][:, None] * mean_y[None, :]
    centered_sin = sum_sin * weight - terms["mean_sin"][:, None] * mean_y[None, :]
    numerator = (
        terms["ss"][:, None] * centered_cos * centered_cos
        + terms["cc"][:, None] * centered_sin * centered_sin
        - 2.0 * terms["cs"][:, None] * centered_cos * centered_sin
    )
    return numerator / (terms["determinant"][:, None] * variance[None, :])


@dataclass(frozen=True)
class FoldDesign:
    """Precomputed timestamp-only design for one fold's training and validation spans.

    The validation span contributes timestamps only. No real validation return is ever
    loaded, so the actual outer-validation cycle statistic cannot be formed here.
    """

    fold_id: str
    frequencies: np.ndarray
    train_slots: np.ndarray
    validation_slots: np.ndarray
    train_times: np.ndarray
    validation_times: np.ndarray
    train_terms: dict[str, np.ndarray]
    validation_terms: dict[str, np.ndarray]
    train_span_days: float

    @property
    def frequency_count(self) -> int:
        return int(self.frequencies.size)

    @property
    def train_count(self) -> int:
        return int(self.train_slots.size)

    @property
    def validation_count(self) -> int:
        return int(self.validation_slots.size)


def build_fold_design(lattice: CycleLattice, fold: CycleFold) -> FoldDesign:
    """Frequency grid and GLS design terms rebuilt from this fold's own timestamps."""
    slots = np.nonzero(lattice.eligible)[0]
    times = lattice.times_days
    train_slots = slots[slots < fold.train_stop]
    validation_slots = slots[(slots >= fold.validation_start) & (slots < fold.validation_stop)]
    if train_slots.size < 3 or validation_slots.size < 3:
        raise ValueError("fold segment is too sparse for the frozen estimator")
    train_times = times[train_slots]
    validation_times = times[validation_slots]
    span = float(train_times[-1] - train_times[0])
    frequencies = frequency_grid(span)
    return FoldDesign(
        fold_id=fold.fold_id,
        frequencies=frequencies,
        train_slots=train_slots,
        validation_slots=validation_slots,
        train_times=train_times,
        validation_times=validation_times,
        train_terms=_design_terms(train_times, frequencies),
        validation_terms=_design_terms(validation_times, frequencies),
        train_span_days=span,
    )


# ---------------------------------------------------------------------------------
# Training-only AR sieve and stationary residual block bootstrap
# ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class SieveModel:
    """One fold's training-only AR sieve fit and its centered residual pool."""

    fold_id: str
    order: int
    coefficients: np.ndarray
    residuals: np.ndarray
    bic: float
    observations: int
    training_observations: int


def _lag_matrix(
    values: np.ndarray, eligible: np.ndarray, order: int, maximum_order: int
) -> tuple[np.ndarray, np.ndarray]:
    """Rows usable at the fixed maximum order, so every BIC candidate shares a sample."""
    count = values.size
    usable = np.zeros(count, dtype=bool)
    if count > maximum_order:
        usable[maximum_order:] = True
        for lag in range(maximum_order + 1):
            usable[maximum_order:] &= eligible[maximum_order - lag : count - lag]
    rows = np.nonzero(usable)[0]
    if rows.size <= maximum_order + 1:
        raise ValueError("training segment has too few contiguous runs for the AR sieve")
    design = np.empty((rows.size, order), dtype=np.float64)
    for lag in range(1, order + 1):
        design[:, lag - 1] = values[rows - lag]
    return design, rows


def fit_sieve(
    fold_id: str,
    values: np.ndarray,
    eligible: np.ndarray,
    training_observations: int,
) -> SieveModel:
    """Select the AR order by BIC over the frozen 0..42 set, using training data only."""
    if values.shape != eligible.shape:
        raise ValueError("value and eligibility arrays must align")
    best: tuple[float, int, np.ndarray, np.ndarray] | None = None
    for order in AR_ORDER_SET:
        design, rows = _lag_matrix(values, eligible, order, AR_MAXIMUM_ORDER)
        target = values[rows]
        if order:
            coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
            residuals = target - design @ coefficients
        else:
            coefficients = np.zeros(0, dtype=np.float64)
            residuals = target.copy()
        sample = rows.size
        sigma2 = float(residuals @ residuals) / sample
        if sigma2 <= 0.0:
            raise ValueError("degenerate AR residual variance in the training segment")
        bic = sample * math.log(sigma2) + order * math.log(sample)
        if best is None or bic < best[0]:
            best = (bic, order, coefficients, residuals)
    assert best is not None
    bic, order, coefficients, residuals = best
    centered = residuals - float(residuals.mean())
    return SieveModel(
        fold_id=fold_id,
        order=order,
        coefficients=coefficients,
        residuals=centered,
        bic=bic,
        observations=int(centered.size),
        training_observations=int(training_observations),
    )


def stationary_block_draw(
    generator: np.random.Generator, length: int, expected_block: int
) -> tuple[np.ndarray, np.ndarray]:
    """Block structure for a stationary bootstrap: per-slot block id and start fraction.

    Block lengths are geometric with mean `expected_block`; each block begins at a
    uniform fraction of whichever residual pool it is later mapped onto. Returning the
    structure rather than pool indices is what lets one replicate drive every
    chronological stage of the joint path from a single shared resampling realization.
    """
    if length <= 0 or expected_block <= 0:
        raise ValueError("stationary block draw needs positive length and block size")
    fresh = generator.random(length) < (1.0 / expected_block)
    fresh[0] = True
    block_id = np.cumsum(fresh) - 1
    positions = np.arange(length, dtype=np.int64)
    block_start = np.maximum.accumulate(np.where(fresh, positions, -1))
    offset = positions - block_start
    fractions = generator.random(int(block_id[-1]) + 1)
    return block_id.astype(np.int64), np.stack((fractions[block_id], offset.astype(np.float64)))


def block_indices(structure: np.ndarray, pool_size: int) -> np.ndarray:
    """Map the shared block structure onto one residual pool, wrapping inside the pool."""
    if pool_size <= 0:
        raise ValueError("residual pool must be non-empty")
    starts = np.floor(structure[0] * pool_size).astype(np.int64)
    return (starts + structure[1].astype(np.int64)) % pool_size


# ---------------------------------------------------------------------------------
# Joint six-fold replicate semantics
# ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class JointNullDesign:
    """The complete joint null: one replicate is one realization of the whole history.

    The six expanding training windows are nested prefixes of a single chronology, so
    the joint path is generated once over the union lattice and every fold reads its own
    training and validation slots out of that same realization. Fold `k`'s training
    segment is literally the prefix that fold `k+1` also trains on, and fold `k`'s
    validation segment is literally the data later folds train on, which reproduces the
    overlap-induced dependence instead of assuming it away.

    `stage_bounds` splits the lattice at the embargoed training boundaries and
    `stage_models` names the sieve model generating each stage. Every stage after the
    first is generated by a model fitted only on real observations that end at or before
    that stage begins, so no generated slot depends on a fit that saw its own future.
    """

    lattice: CycleLattice
    folds: tuple[CycleFold, ...]
    models: tuple[SieveModel, ...]
    stage_bounds: tuple[int, ...]
    stage_models: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.stage_bounds) != len(self.stage_models) + 1:
            raise ValueError("every stage needs a bound pair and a generating model")
        if self.stage_bounds[0] != 0 or self.stage_bounds[-1] != self.lattice.slot_count:
            raise ValueError("stages must tile the whole union lattice")
        if any(
            later <= earlier
            for earlier, later in zip(self.stage_bounds, self.stage_bounds[1:], strict=False)
        ):
            raise ValueError("stage bounds must be strictly increasing")
        for stage, model_index in enumerate(self.stage_models):
            if not 0 <= model_index < len(self.models):
                raise ValueError("stage refers to an unknown sieve model")
            if stage and self.models[model_index].training_observations > self.stage_bounds[stage]:
                raise ValueError("stage model was fitted on observations from its own future")

    @property
    def innovation_rms(self) -> float:
        """Slot-weighted RMS of the innovations that actually generate the joint path."""
        total = 0.0
        for stage, model_index in enumerate(self.stage_models):
            width = self.stage_bounds[stage + 1] - self.stage_bounds[stage]
            residuals = self.models[model_index].residuals
            total += width * float(residuals @ residuals) / residuals.size
        return math.sqrt(total / self.lattice.slot_count)

    @property
    def cross_fold_dependence_handling(self) -> str:
        return "SINGLE_JOINT_PATH_PER_REPLICATE_SIX_FOLD_STATISTICS_READ_FROM_ONE_REALIZATION"

    @property
    def shared_history_handling(self) -> str:
        return (
            "NESTED_PREFIX_TRAINING_WINDOWS_SHARE_IDENTICAL_SIMULATED_SLOTS_AND_EARLIER_"
            "VALIDATION_SLOTS_REAPPEAR_IN_LATER_TRAINING_WINDOWS"
        )


@dataclass(frozen=True)
class SimulatedPath:
    """A batch of simulated joint chronologies; the only input frequency selection takes.

    Constructing one requires a simulator in this module, which is what makes it
    impossible for real BTC returns to reach the selection/evaluation pipeline.
    """

    provenance: str
    first_replicate: int
    values: np.ndarray

    def __post_init__(self) -> None:
        if self.provenance not in PATH_PROVENANCE:
            raise PrepModeViolation("unknown simulated-path provenance")
        if self.values.ndim != 2:
            raise ValueError("simulated paths must be shaped (slots, replicates)")

    @property
    def replicates(self) -> int:
        return int(self.values.shape[1])


def replicate_seed(stream: int, replicate: int) -> np.random.Generator:
    """Deterministic child stream; period, SNR and phase never enter the RNG."""
    return np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(stream, replicate)))


def simulate_joint_paths(
    design: JointNullDesign, stream: int, first_replicate: int, replicates: int
) -> np.ndarray:
    """Simulate `replicates` complete joint chronologies under the frozen null."""
    if replicates <= 0:
        raise ValueError("a simulation batch needs at least one replicate")
    slots = design.lattice.slot_count
    total = BURN_IN_OBSERVATIONS + slots
    innovations = np.empty((total, replicates), dtype=np.float64)
    structures = []
    for column in range(replicates):
        generator = replicate_seed(stream, first_replicate + column)
        _, structure = stationary_block_draw(generator, total, BLOCK_EXPECTED_OBSERVATIONS)
        structures.append(structure)
    stages = [(0, BURN_IN_OBSERVATIONS, design.stage_models[0])]
    stages += [
        (
            BURN_IN_OBSERVATIONS + design.stage_bounds[stage],
            BURN_IN_OBSERVATIONS + design.stage_bounds[stage + 1],
            model_index,
        )
        for stage, model_index in enumerate(design.stage_models)
    ]
    for start, stop, model_index in stages:
        pool = design.models[model_index].residuals
        for column, structure in enumerate(structures):
            indices = block_indices(structure[:, start:stop], pool.size)
            innovations[start:stop, column] = pool[indices]
    path = np.zeros((AR_MAXIMUM_ORDER + total, replicates), dtype=np.float64)
    for start, stop, model_index in stages:
        model = design.models[model_index]
        order = model.order
        coefficients = model.coefficients
        for position in range(AR_MAXIMUM_ORDER + start, AR_MAXIMUM_ORDER + stop):
            value = innovations[position - AR_MAXIMUM_ORDER]
            if order:
                lags = path[position - order : position][::-1]
                value = value + coefficients @ lags
            path[position] = value
    return path[AR_MAXIMUM_ORDER + BURN_IN_OBSERVATIONS :]


def null_paths(design: JointNullDesign, first_replicate: int, replicates: int) -> SimulatedPath:
    return SimulatedPath(
        "NULL_REPLICATE",
        first_replicate,
        simulate_joint_paths(design, STREAM_NULL, first_replicate, replicates),
    )


def synthetic_base_paths(
    design: JointNullDesign, first_replicate: int, replicates: int
) -> SimulatedPath:
    return SimulatedPath(
        "SYNTHETIC_REPLICATE",
        first_replicate,
        simulate_joint_paths(design, STREAM_SYNTHETIC, first_replicate, replicates),
    )


# ---------------------------------------------------------------------------------
# Synthetic cycle injection
# ---------------------------------------------------------------------------------


def phase_index(replicate: int) -> int:
    """Balanced deterministic phase assignment over the 16 frozen phases."""
    if replicate < 0:
        raise ValueError("replicate index must be non-negative")
    return replicate % PHASE_COUNT


def phase_value(index: int) -> float:
    if not 0 <= index < PHASE_COUNT:
        raise ValueError("phase index is outside the frozen grid")
    return 2.0 * math.pi * index / PHASE_COUNT


def unit_injection(lattice: CycleLattice, period_days: float, phase: float) -> np.ndarray:
    """Unit-amplitude log-price sinusoid differenced onto the 4h return lattice."""
    if not math.isfinite(period_days) or period_days <= 0:
        raise ValueError("injected period must be positive")
    angular = 2.0 * math.pi / period_days
    times = lattice.times_days
    step = BAR_HOURS / 24.0
    return np.sin(angular * times + phase) - np.sin(angular * (times - step) + phase)


def injection_matrix(lattice: CycleLattice, period_days: float) -> np.ndarray:
    """Unit-amplitude injected return components for the 16 frozen phases."""
    return np.stack(
        [unit_injection(lattice, period_days, phase_value(index)) for index in range(PHASE_COUNT)],
        axis=1,
    )


def injection_path(lattice: CycleLattice, period_days: float) -> SimulatedPath:
    """The deterministic injected components, wrapped so they share the projection API."""
    return SimulatedPath("DETERMINISTIC_INJECTION", 0, injection_matrix(lattice, period_days))


def injection_amplitude(
    lattice: CycleLattice, period_days: float, phase: float, snr: float, innovation_rms: float
) -> float:
    """Log-price amplitude giving exactly `snr` on the frozen structural effect scale."""
    if snr < 0.0:
        raise ValueError("SNR must be non-negative")
    if innovation_rms <= 0.0:
        raise ValueError("innovation RMS must be positive")
    unit = unit_injection(lattice, period_days, phase)[lattice.eligible]
    unit_rms = math.sqrt(float(unit @ unit) / unit.size)
    if unit_rms <= 0.0:
        raise ValueError("injected component has no return-domain amplitude")
    return snr * innovation_rms / unit_rms


# ---------------------------------------------------------------------------------
# Selection and evaluation, run identically inside every replicate
# ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class FoldProjection:
    """Fourier sums and moments of one batch on one fold; linear in the path values."""

    sum_train_cos: np.ndarray
    sum_train_sin: np.ndarray
    sum_train_y: np.ndarray
    sum_train_yy: np.ndarray
    sum_validation_cos: np.ndarray
    sum_validation_sin: np.ndarray
    sum_validation_y: np.ndarray
    sum_validation_yy: np.ndarray


def _segment_sums(
    times: np.ndarray, frequencies: np.ndarray, values: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Chunked `sum(y cos)` / `sum(y sin)` against the fixed timestamp design."""
    cos_sums = np.empty((frequencies.size, values.shape[1]), dtype=np.float64)
    sin_sums = np.empty((frequencies.size, values.shape[1]), dtype=np.float64)
    for start in range(0, frequencies.size, 512):
        block = frequencies[start : start + 512]
        angle = (2.0 * math.pi) * block[:, None] * times[None, :]
        cos_sums[start : start + 512] = np.cos(angle) @ values
        sin_sums[start : start + 512] = np.sin(angle) @ values
    return cos_sums, sin_sums


def project(design: FoldDesign, path: SimulatedPath) -> FoldProjection:
    """Project one batch of simulated full-lattice series onto this fold's frozen design.

    Only a :class:`SimulatedPath` is accepted, so a real BTC return array cannot be
    projected onto a validation design and turned into an actual cycle statistic.
    """
    if not isinstance(path, SimulatedPath):
        raise PrepModeViolation("the frozen pipeline projects simulated paths only")
    values = path.values
    train = values[design.train_slots]
    validation = values[design.validation_slots]
    train_cos, train_sin = _segment_sums(design.train_times, design.frequencies, train)
    validation_cos, validation_sin = _segment_sums(
        design.validation_times, design.frequencies, validation
    )
    return FoldProjection(
        sum_train_cos=train_cos,
        sum_train_sin=train_sin,
        sum_train_y=train.sum(axis=0),
        sum_train_yy=np.einsum("ij,ij->j", train, train),
        sum_validation_cos=validation_cos,
        sum_validation_sin=validation_sin,
        sum_validation_y=validation.sum(axis=0),
        sum_validation_yy=np.einsum("ij,ij->j", validation, validation),
    )


def combine(
    base: FoldProjection, injected: FoldProjection, cross: np.ndarray, scale: np.ndarray
) -> FoldProjection:
    """Exact projection of `base + scale * injected` without re-touching the series.

    The Fourier sums and the first moment are linear in the series and the second moment
    is quadratic with a precomputed cross term, so every SNR level on a frozen period
    reuses one simulated path. This is an algebraic reformulation of the identical
    statistic, not an approximation, and it makes the SNR grid share common random
    numbers by construction.
    """
    return FoldProjection(
        sum_train_cos=base.sum_train_cos + scale * injected.sum_train_cos,
        sum_train_sin=base.sum_train_sin + scale * injected.sum_train_sin,
        sum_train_y=base.sum_train_y + scale * injected.sum_train_y,
        sum_train_yy=base.sum_train_yy
        + 2.0 * scale * cross[0]
        + scale * scale * injected.sum_train_yy,
        sum_validation_cos=base.sum_validation_cos + scale * injected.sum_validation_cos,
        sum_validation_sin=base.sum_validation_sin + scale * injected.sum_validation_sin,
        sum_validation_y=base.sum_validation_y + scale * injected.sum_validation_y,
        sum_validation_yy=base.sum_validation_yy
        + 2.0 * scale * cross[1]
        + scale * scale * injected.sum_validation_yy,
    )


def fold_validation_power(design: FoldDesign, projection: FoldProjection) -> np.ndarray:
    """Select one training frequency, then score validation at that frequency only.

    Frequencies ascend, so `argmax` resolves an exact tie towards the lowest frequency,
    which is the frozen longer-period tie break. Validation never searches: it reads the
    single already-frozen grid index chosen by training.
    """
    training = gls_power(
        design.train_terms,
        projection.sum_train_cos,
        projection.sum_train_sin,
        projection.sum_train_y,
        projection.sum_train_yy,
        design.train_count,
    )
    selected = np.argmax(training, axis=0)
    columns = np.arange(selected.size)
    terms = {key: value[selected] for key, value in design.validation_terms.items()}
    count = design.validation_count
    weight = 1.0 / count
    mean_y = projection.sum_validation_y * weight
    variance = projection.sum_validation_yy * weight - mean_y * mean_y
    if np.any(variance <= 0.0):
        raise ValueError("a replicate validation segment has no variance to explain")
    centered_cos = (
        projection.sum_validation_cos[selected, columns] * weight - terms["mean_cos"] * mean_y
    )
    centered_sin = (
        projection.sum_validation_sin[selected, columns] * weight - terms["mean_sin"] * mean_y
    )
    numerator = (
        terms["ss"] * centered_cos * centered_cos
        + terms["cc"] * centered_sin * centered_sin
        - 2.0 * terms["cs"] * centered_cos * centered_sin
    )
    return numerator / (terms["determinant"] * variance)


def pooled_statistic(powers: list[np.ndarray], weights: list[int]) -> np.ndarray:
    """Eligible-observation-weighted mean of the six validation powers."""
    if len(powers) != len(weights) or not powers:
        raise ValueError("pooling needs one weight per fold")
    total = float(sum(weights))
    stacked = np.stack(powers)
    factors = np.asarray(weights, dtype=np.float64)[:, None] / total
    return (stacked * factors).sum(axis=0)


def replicate_statistics(designs: tuple[FoldDesign, ...], path: SimulatedPath) -> np.ndarray:
    """Run the complete frozen six-fold procedure on one batch of simulated paths.

    This is the only entry point from a series to a pooled statistic, and it accepts a
    :class:`SimulatedPath` only. Real market returns have no route into it.
    """
    if not isinstance(path, SimulatedPath):
        raise PrepModeViolation("frequency selection accepts simulated paths only")
    powers = []
    weights = []
    for design in designs:
        powers.append(fold_validation_power(design, project(design, path)))
        weights.append(design.validation_count)
    return pooled_statistic(powers, weights)


# ---------------------------------------------------------------------------------
# Inference from the joint null
# ---------------------------------------------------------------------------------


def rejection_index(replicates: int, alpha: float) -> int:
    """Zero-based rank in the descending null whose value the statistic must exceed."""
    budget = math.floor(alpha * (replicates + 1)) - 1
    if budget < 0:
        raise ValueError("null replicate budget cannot resolve the frozen alpha")
    return budget


def critical_value(null_statistics: np.ndarray, alpha: float = PRIMARY_ALPHA) -> float:
    if null_statistics.ndim != 1 or null_statistics.size == 0:
        raise ValueError("null statistics must be a non-empty one-dimensional sample")
    ordered = np.sort(null_statistics)[::-1]
    return float(ordered[rejection_index(int(null_statistics.size), alpha)])


def detection_power(statistics: np.ndarray, threshold: float) -> float:
    return float(np.mean(statistics > threshold))


def binomial_interval(successes: int, trials: int) -> tuple[float, float]:
    """Wilson 95% interval; descriptive Monte Carlo uncertainty, not an inference."""
    if trials <= 0:
        raise ValueError("binomial interval needs a positive trial count")
    z = 1.959963984540054
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    center = (proportion + z * z / (2 * trials)) / denominator
    half = (
        z
        * math.sqrt(proportion * (1 - proportion) / trials + z * z / (4 * trials * trials))
        / denominator
    )
    return _rounded(max(0.0, center - half)), _rounded(min(1.0, center + half))


# ---------------------------------------------------------------------------------
# NULL_FIDELITY_V1
# ---------------------------------------------------------------------------------

RETURN_ACF_LAGS = (1, 2, 3, 4, 5, 6)
ABSOLUTE_ACF_LAGS = (42, 90, 180, 360, 540)
REALIZED_VOLATILITY_HORIZONS = (("1d", 6), ("7d", 42), ("30d", 180))
VARIANCE_RATIO_HORIZONS = (12, 42, 180, 540)


def _autocorrelation(values: np.ndarray, lag: int) -> float:
    if lag <= 0 or values.size <= lag + 2:
        raise ValueError("autocorrelation lag exceeds the sample")
    centered = values - float(values.mean())
    denominator = float(centered @ centered)
    if denominator <= 0.0:
        raise ValueError("constant series has no autocorrelation")
    return float(centered[:-lag] @ centered[lag:]) / denominator


def _log_realized_volatility_dispersion(values: np.ndarray, window: int) -> float:
    blocks = values.size // window
    if blocks < 4:
        raise ValueError("too few non-overlapping windows for realized volatility")
    squared = (values[: blocks * window] ** 2).reshape(blocks, window).sum(axis=1)
    if np.any(squared <= 0.0):
        raise ValueError("a realized-volatility window is degenerate")
    return float(np.std(0.5 * np.log(squared), ddof=1))


def _variance_ratio(values: np.ndarray, horizon: int) -> float:
    blocks = values.size // horizon
    if blocks < 4:
        raise ValueError("too few non-overlapping windows for a variance ratio")
    aggregated = values[: blocks * horizon].reshape(blocks, horizon).sum(axis=1)
    base = float(np.var(values, ddof=1))
    if base <= 0.0:
        raise ValueError("degenerate return variance")
    return float(np.var(aggregated, ddof=1)) / (horizon * base)


def fidelity_statistics(values: np.ndarray) -> dict[str, float]:
    """Frozen NULL_FIDELITY_V1 statistics for one training segment of 4h returns."""
    if values.ndim != 1 or values.size < 4 * max(ABSOLUTE_ACF_LAGS):
        raise ValueError("fidelity statistics need a long contiguous training segment")
    centered = values - float(values.mean())
    absolute = np.abs(centered)
    deviation = float(np.std(centered, ddof=1))
    if deviation <= 0.0:
        raise ValueError("degenerate training dispersion")
    standardized = centered / deviation
    statistics: dict[str, float] = {
        "return_sd": deviation,
        "excess_kurtosis": float(np.mean(standardized**4)) - 3.0,
        "tail_ratio_q995_q50": float(
            np.quantile(absolute, 0.995) / max(np.quantile(absolute, 0.50), 1e-300)
        ),
    }
    for lag in RETURN_ACF_LAGS:
        statistics[f"return_acf_lag{lag}"] = _autocorrelation(centered, lag)
    for lag in ABSOLUTE_ACF_LAGS:
        statistics[f"absolute_acf_lag{lag}"] = _autocorrelation(absolute, lag)
    for name, window in REALIZED_VOLATILITY_HORIZONS:
        statistics[f"log_realized_volatility_sd_{name}"] = _log_realized_volatility_dispersion(
            centered, window
        )
    for horizon in VARIANCE_RATIO_HORIZONS:
        statistics[f"variance_ratio_{horizon}"] = _variance_ratio(centered, horizon)
    return statistics


def fidelity_criteria() -> dict[str, dict[str, Any]]:
    """Predeclared materiality rules, fixed before any fidelity value is computed.

    Every rule is stated as a tolerance on the observed value against the null-replicate
    median, never as a tolerance chosen from an observed discrepancy. A rank p-value is
    reported alongside but does not decide the gate: with 999 replicates almost any real
    financial statistic is formally extreme, so the gate asks the materially relevant
    question instead - whether the null keeps enough of the dependence that matters
    inside the frozen 2-90 day band.
    """
    criteria: dict[str, dict[str, Any]] = {
        "return_sd": {"rule": "RATIO_BAND", "minimum": 0.50, "maximum": 2.00},
        "excess_kurtosis": {"rule": "RATIO_BAND", "minimum": 0.25, "maximum": 4.00},
        "tail_ratio_q995_q50": {"rule": "RATIO_BAND", "minimum": 0.50, "maximum": 2.00},
    }
    for lag in RETURN_ACF_LAGS:
        criteria[f"return_acf_lag{lag}"] = {"rule": "ABSOLUTE_GAP", "tolerance": 0.05}
    for lag in ABSOLUTE_ACF_LAGS:
        criteria[f"absolute_acf_lag{lag}"] = {
            "rule": "ABSOLUTE_GAP_OR_RETAINED_SHARE",
            "tolerance": 0.05,
            "retained_share": 0.50,
        }
    for name, _ in REALIZED_VOLATILITY_HORIZONS:
        criteria[f"log_realized_volatility_sd_{name}"] = {
            "rule": "RETAINED_SHARE",
            "retained_share": 0.50,
        }
    for horizon in VARIANCE_RATIO_HORIZONS:
        criteria[f"variance_ratio_{horizon}"] = {"rule": "LOG_RATIO", "tolerance": 1.50}
    return criteria


def _apply_criterion(rule: dict[str, Any], observed: float, median: float) -> bool:
    kind = rule["rule"]
    if kind == "ABSOLUTE_GAP":
        return abs(observed - median) <= rule["tolerance"]
    if kind == "ABSOLUTE_GAP_OR_RETAINED_SHARE":
        if abs(observed - median) <= rule["tolerance"]:
            return True
        return median >= rule["retained_share"] * observed
    if kind == "RETAINED_SHARE":
        return median >= rule["retained_share"] * observed
    if kind == "RATIO_BAND":
        if median == 0.0 or observed / median <= 0.0:
            return False
        return rule["minimum"] <= observed / median <= rule["maximum"]
    if kind == "LOG_RATIO":
        if median <= 0.0 or observed <= 0.0:
            return False
        return abs(math.log(observed / median)) <= math.log(rule["tolerance"])
    raise ValueError("unknown fidelity criterion")


def evaluate_fidelity(
    observed: dict[str, dict[str, float]],
    replicated: dict[str, dict[str, list[float]]],
    criteria: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compare training observations against the joint null's replicate distributions."""
    rules = criteria if criteria is not None else fidelity_criteria()
    folds: list[dict[str, Any]] = []
    failures: list[str] = []
    for fold_id, values in observed.items():
        checks: dict[str, Any] = {}
        for name, value in values.items():
            sample = np.asarray(replicated[fold_id][name], dtype=np.float64)
            median = float(np.median(sample))
            at_least = int(np.sum(sample >= value))
            at_most = int(np.sum(sample <= value))
            rank_p = min(1.0, 2.0 * (1 + min(at_least, at_most)) / (sample.size + 1))
            passed = _apply_criterion(rules[name], value, median)
            if not passed:
                failures.append(f"{fold_id}/{name}")
            checks[name] = {
                "observed": _rounded(value),
                "null_median": _rounded(median),
                "null_p05": _rounded(float(np.quantile(sample, 0.05))),
                "null_p95": _rounded(float(np.quantile(sample, 0.95))),
                "two_sided_rank_p": _rounded(rank_p),
                "criterion": rules[name],
                "material_pass": passed,
            }
        folds.append({"fold_id": fold_id, "checks": checks, "material_pass": not failures})
    status = PASS if not failures else REDESIGN
    return {
        "schema_version": 1,
        "artifact_id": FIDELITY_ID,
        "design_id": DESIGN_ID,
        "null_method": NULL_METHOD,
        "block_expected_observations": BLOCK_EXPECTED_OBSERVATIONS,
        "block_length_tuned_after_observation": False,
        "training_only": True,
        "validation_results_used": False,
        "fidelity_replicates": FIDELITY_REPLICATES,
        "folds": folds,
        "material_failures": sorted(failures),
        "material_failure_count": len(failures),
        "NULL_FIDELITY_STATUS": status,
        "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED": False,
    }


# ---------------------------------------------------------------------------------
# Power gate
# ---------------------------------------------------------------------------------


def evaluate_power_gate(
    fidelity: dict[str, Any],
    benchmark: dict[str, Any],
    detectability: dict[str, Any] | None,
) -> dict[str, Any]:
    """Combine the three prerequisite gates with the frozen detectability rule."""
    prerequisites = {
        "NULL_FIDELITY_STATUS": fidelity["NULL_FIDELITY_STATUS"],
        "JOINT_REPLICATION_STATUS": benchmark["joint_replication"]["JOINT_REPLICATION_STATUS"],
        "COMPUTATIONAL_STATUS": benchmark["compute"]["COMPUTATIONAL_STATUS"],
    }
    prerequisites_pass = all(value == PASS for value in prerequisites.values())
    gate_periods: dict[str, float] = {}
    gate_pass = False
    if detectability is not None:
        if not prerequisites_pass:
            raise PrepModeViolation("detectability may not be computed before its gates pass")
        gate_pass = True
        for cell in detectability["cells"]:
            if cell["snr"] != GATE_SNR:
                continue
            gate_periods[f"{cell['period_days']:g}"] = cell["power"]
            gate_pass = gate_pass and cell["power"] >= TARGET_POWER
        gate_pass = gate_pass and len(gate_periods) == len(CALIBRATION_PERIOD_DAYS)
    status = READY if prerequisites_pass and gate_pass else REDESIGN
    return {
        "schema_version": 1,
        "artifact_id": GATE_ID,
        "design_id": DESIGN_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "protocol_id": PROTOCOL_ID,
        "hypothesis_status": "DESIGNED_NOT_PREREGISTERED_NOT_EXECUTED",
        "frozen_design": {
            "representation": REPRESENTATION,
            "period_band_days": [BAND_MINIMUM_DAYS, BAND_MAXIMUM_DAYS],
            "frequency_grid": "FOURIER_SPACING_OVERSAMPLING_4_CLIPPED_TO_FROZEN_BAND",
            "spectral_estimator": ESTIMATOR,
            "primary_structural_hypotheses": 1,
            "maximum_diagnostics": 2,
            "diagnostics_non_rescuing": True,
            "outer_folds": "DEVELOPMENT_WALK_FORWARD_V1_ANNUAL_2019_TO_2024",
            "embargo_days": EMBARGO_DAYS,
            "selection": SELECTION_RULE,
            "evaluation": EVALUATION_RULE,
            "validation_frequency_search": False,
            "alpha": PRIMARY_ALPHA,
            "economic_mesi": None,
            "economic_trading_logic": False,
            "representation_added": False,
            "estimator_added": False,
            "period_band_changed": False,
            "structural_primary_added": False,
            "diagnostic_added": False,
        },
        "null_fidelity": {
            "method": fidelity["null_method"],
            "block_expected_observations": fidelity["block_expected_observations"],
            "block_length_tuned_after_observation": fidelity[
                "block_length_tuned_after_observation"
            ],
            "training_only": fidelity["training_only"],
            "validation_results_used": fidelity["validation_results_used"],
            "fidelity_replicates": fidelity["fidelity_replicates"],
            "material_failures": fidelity["material_failures"],
            "material_failure_count": fidelity["material_failure_count"],
            "preregistration": fidelity["preregistration"],
            "NULL_FIDELITY_STATUS": fidelity["NULL_FIDELITY_STATUS"],
        },
        "joint_replication": benchmark["joint_replication"],
        "compute": benchmark["compute"],
        "prerequisite_gates": prerequisites,
        "prerequisites_pass": prerequisites_pass,
        "detectability": detectability,
        "gate_rule": "POWER_AT_LEAST_0_80_AT_SNR_CYCLE_0_50_FOR_EVERY_FROZEN_PERIOD",
        "target_power": TARGET_POWER,
        "gate_snr": GATE_SNR,
        "null_replicates": NULL_REPLICATES,
        "synthetic_replicates_per_cell": SYNTHETIC_REPLICATES_PER_CELL,
        "calibration_period_days": list(CALIBRATION_PERIOD_DAYS),
        "snr_grid": list(SNR_GRID),
        "phase_grid_count": PHASE_COUNT,
        "seed": SEED,
        "power_at_gate_snr_by_period": gate_periods,
        "P2_POWER_GATE_STATUS": status,
        "preregistration_authorized": False,
        "actual_execution_authorized": False,
        "leakage_guard": {
            "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED": False,
            "actual_training_selected_period_computed": False,
            "actual_validation_power_computed": False,
            "actual_pooled_statistic_computed": False,
            "actual_structural_p_value_computed": False,
            "market_classification_emitted": False,
            "real_validation_returns_loaded": False,
            "sealed_data_queried": False,
            "post_cutoff_data_used": False,
            "assets_expanded": False,
            "cycle_trading_implemented": False,
            "real_money_authorized": False,
        },
        "safety": {
            "experiments_completed": 26,
            "observed_material_economic_hypotheses": 12,
            "sealed_queries": 0,
            "champion_status": "NONE",
            "real_money_authorized": False,
        },
        "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED": False,
        "next_action": "RESEARCH_DIRECTOR_REVIEW",
    }


def _line(label: str, value: Any) -> str:
    return f"- {label}: {value}"


def render_power_gate_markdown(gate: dict[str, Any]) -> str:
    """Human-readable mirror of the machine-readable gate; it adds no new numbers."""
    design = gate["frozen_design"]
    fidelity = gate["null_fidelity"]
    joint = gate["joint_replication"]
    compute = gate["compute"]
    detectability = gate["detectability"]
    observed = gate["ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED"]
    lines = [
        f"# {gate['artifact_id']}",
        "",
        f"Design: `{gate['design_id']}`. Future structural hypothesis: `{gate['hypothesis_id']}`.",
        "",
        "Prospective preparation only. The actual BTCUSDT cycle result was not computed:",
        "no training-selected period, no outer validation power, no pooled statistic, no",
        "structural p-value and no market classification exists.",
        "",
        f"ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED = {observed}",
        "",
        "## Frozen design",
        "",
        _line("representation", design["representation"]),
        _line("period band (days)", design["period_band_days"]),
        _line("frequency grid", design["frequency_grid"]),
        _line("spectral estimator", design["spectral_estimator"]),
        _line("structural primaries", design["primary_structural_hypotheses"]),
        _line("maximum diagnostics", design["maximum_diagnostics"]),
        _line("outer folds", design["outer_folds"]),
        _line("pre-validation embargo (days)", design["embargo_days"]),
        _line("selection", design["selection"]),
        _line("evaluation", design["evaluation"]),
        _line("validation frequency search", design["validation_frequency_search"]),
        _line("economic MESI", design["economic_mesi"]),
        "",
        "## Null fidelity",
        "",
        _line("method", fidelity["method"]),
        _line("expected block length (4h obs)", fidelity["block_expected_observations"]),
        _line("block tuned after observation", fidelity["block_length_tuned_after_observation"]),
        _line("training only", fidelity["training_only"]),
        _line("validation results used", fidelity["validation_results_used"]),
        _line("fidelity replicates", fidelity["fidelity_replicates"]),
        _line("thresholds preregistered", fidelity["preregistration"]["artifact_sha256"]),
        _line("material failures", fidelity["material_failure_count"]),
        "",
        f"### NULL_FIDELITY_STATUS: {fidelity['NULL_FIDELITY_STATUS']}",
        "",
    ]
    if fidelity["material_failures"]:
        lines += ["Materially failing checks:", ""]
        lines += [f"- `{name}`" for name in fidelity["material_failures"]]
        lines.append("")
    lines += [
        "## Joint six-fold null semantics",
        "",
        _line("joint replication method", joint["joint_replication_method"]),
        _line("cross-fold dependence handling", joint["cross_fold_dependence_handling"]),
        _line("shared history handling", joint["shared_history_handling"]),
        _line("folds simulated independently", joint["folds_simulated_independently"]),
        _line("joint pooled SD", joint["joint_pooled_sd"]),
        _line("independent pooled SD", joint["independent_pooled_sd"]),
        _line("joint / independent SD ratio", joint["pooled_sd_ratio"]),
        "",
        f"### JOINT_REPLICATION_STATUS: {joint['JOINT_REPLICATION_STATUS']}",
        "",
        "## Computational feasibility",
        "",
        _line("frequencies per fold", compute["frequencies_per_fold"]),
        _line("training observations per fold", compute["training_observations_per_fold"]),
        _line("validation observations per fold", compute["validation_observations_per_fold"]),
        _line("Fourier sum elements per replicate", compute["elements_per_replicate"]),
        _line("benchmark replicates", compute["benchmark_replicates"]),
        _line("benchmark elapsed seconds", compute["benchmark_elapsed_seconds"]),
        _line("projected full runtime seconds", compute["projected_runtime_seconds"]),
        _line("peak memory estimate (MiB)", compute["peak_memory_mib"]),
        _line("optimizations", ", ".join(compute["optimizations"])),
        _line("replicates reduced", compute["replicates_reduced"]),
        _line("frequency grid coarsened", compute["grid_coarsened"]),
        "",
        f"### COMPUTATIONAL_STATUS: {compute['COMPUTATIONAL_STATUS']}",
        "",
        "## Prospective detectability",
        "",
    ]
    if detectability is None:
        lines += [
            "Not computed. A prerequisite gate did not pass, so the frozen synthetic",
            "detectability curves were not run and no actual market result was exposed.",
            "",
        ]
    else:
        header = " | ".join(f"SNR {value:g}" for value in SNR_GRID)
        lines += [
            _line("null replicates", detectability["null_replicates"]),
            _line("synthetic replicates per cell", detectability["synthetic_replicates_per_cell"]),
            _line("phase grid", detectability["phase_grid_count"]),
            _line("injected 4h-return RMS by SNR", detectability["injected_return_rms_by_snr"]),
            "",
            f"| period (d) | {header} | min SNR at 0.80 |",
            "| --- | " + " | ".join("---" for _ in SNR_GRID) + " | --- |",
        ]
        for period in CALIBRATION_PERIOD_DAYS:
            cells = []
            for snr in SNR_GRID:
                cell = next(
                    item
                    for item in detectability["cells"]
                    if item["period_days"] == period and item["snr"] == snr
                )
                cells.append(f"{cell['power']:.4f}")
            minimum = detectability["minimum_detectable_snr"][f"{period:g}"]
            reached = minimum if minimum is not None else "NOT_REACHED"
            lines.append(f"| {period:g} | " + " | ".join(cells) + f" | {reached} |")
        lines.append("")
        lines += [
            "Descriptive amplitude translation, reported without changing the effect",
            "definition (training-only scale estimates):",
            "",
            "| period (d) | " + " | ".join(f"SNR {value:g}" for value in SNR_GRID) + " |",
            "| --- | " + " | ".join("---" for _ in SNR_GRID) + " |",
        ]
        for period in CALIBRATION_PERIOD_DAYS:
            amplitudes = detectability["log_price_amplitude"][f"{period:g}"]
            row = " | ".join(f"{value:.8f}" for value in amplitudes)
            lines.append(f"| {period:g} | {row} |")
        lines.append("")
    lines += [
        f"## P2_POWER_GATE_STATUS: {gate['P2_POWER_GATE_STATUS']}",
        "",
        _line("gate rule", gate["gate_rule"]),
        _line("target power", gate["target_power"]),
        _line("gate SNR", gate["gate_snr"]),
        _line("power at gate SNR by period", gate["power_at_gate_snr_by_period"]),
        _line("prerequisites pass", gate["prerequisites_pass"]),
        _line("preregistration authorized", gate["preregistration_authorized"]),
        _line("actual execution authorized", gate["actual_execution_authorized"]),
        _line("next action", gate["next_action"]),
        "",
    ]
    return "\n".join(lines)


__all__ = [
    "BAND_MAXIMUM_DAYS",
    "BAND_MINIMUM_DAYS",
    "BLOCK_EXPECTED_OBSERVATIONS",
    "CALIBRATION_PERIOD_DAYS",
    "SNR_GRID",
    "CycleFold",
    "CycleLattice",
    "FoldDesign",
    "JointNullDesign",
    "PrepModeViolation",
    "SieveModel",
    "SimulatedPath",
    "assert_no_result_leakage",
    "build_fold_design",
    "combine",
    "critical_value",
    "detection_power",
    "evaluate_fidelity",
    "evaluate_power_gate",
    "fidelity_criteria",
    "fidelity_statistics",
    "fit_sieve",
    "fold_validation_power",
    "frequency_grid",
    "injection_amplitude",
    "injection_matrix",
    "injection_path",
    "null_paths",
    "phase_index",
    "phase_value",
    "pooled_statistic",
    "project",
    "render_power_gate_markdown",
    "replicate_statistics",
    "simulate_joint_paths",
    "synthetic_base_paths",
    "unit_injection",
]
