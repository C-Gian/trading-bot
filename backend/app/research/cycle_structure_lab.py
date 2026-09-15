"""Canonical 4h return access for the P2 cycle power preparation.

Data access lives here so that `cycle_structure` stays a pure, market-data-free design
module. The hard leakage boundary is enforced at load time rather than by convention:
:class:`CycleGrids` exposes real returns for training segments only, and raises
`PrepModeViolation` on any request for outer-validation returns. Validation contributes
its timestamps, which is all the frozen design needs in order to build the design
quantities that simulated chronologies are evaluated on.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

from app.data.policy import CUTOFF

from .continuation_lab import DATASET_ID, MANIFEST_SHA256
from .cycle_structure import (
    AR_MAXIMUM_ORDER,
    BAR_US,
    DAY_US,
    EMBARGO_DAYS,
    CycleFold,
    CycleLattice,
    FoldDesign,
    JointNullDesign,
    PrepModeViolation,
    SieveModel,
    build_fold_design,
    fit_sieve,
)
from .evaluation_protocol import load_protocol, utc_us

ROOT = Path(__file__).resolve().parents[3]
DERIVED_4H = "data/derived/BTCUSDT-4h.parquet"


def _verified_4h_table(root: Path) -> Any:
    """Read the canonical derived 4h bars only after the governed hashes match."""
    manifest_bytes = (root / f"data/manifests/{DATASET_ID}.json").read_bytes()
    if hashlib.sha256(manifest_bytes.replace(b"\r\n", b"\n")).hexdigest() != MANIFEST_SHA256:
        raise ValueError("unapproved manifest bytes; refusing data access")
    manifest = json.loads(manifest_bytes)
    record = manifest["files"]["4h"]
    if record["path"] != DERIVED_4H or manifest["symbol"] != "BTCUSDT":
        raise ValueError("unapproved dataset path")
    path = root / record["path"]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != record["sha256"]:
        raise ValueError("dataset bytes differ; refusing to inspect table")
    return pq.read_table(path)


@dataclass(frozen=True)
class CycleGrids:
    """Lattice, folds, and training-only real returns for the frozen P2 design.

    `returns` holds the real 4h close-to-close log returns on the union lattice, but
    every slot at or after the last embargoed training boundary is forced to zero: no
    real observation exists beyond the point where the frozen design stops being allowed
    to learn. Earlier folds' validation windows do carry real values, because later folds
    legitimately train on them under the frozen expanding schedule; what closes the
    leakage path is that the only way from a series to a cycle statistic is
    `replicate_statistics`, which accepts simulated paths alone, and that there is no
    accessor pairing a fold's validation slots with real returns.
    """

    lattice: CycleLattice
    folds: tuple[CycleFold, ...]
    returns: np.ndarray
    training_horizon: int
    eligible_returns: int
    ineligible_slots: int
    incomplete_bars: int
    non_consecutive_bars: int

    def __post_init__(self) -> None:
        if self.returns.shape != (self.lattice.slot_count,):
            raise ValueError("return series must cover the union lattice")
        if np.any(self.returns[self.training_horizon :] != 0.0):
            raise PrepModeViolation("validation-period returns must never be materialized")

    def training_segment(self, fold: CycleFold) -> tuple[np.ndarray, np.ndarray]:
        """Real returns and eligibility for one fold's embargoed training window."""
        if fold.train_stop > self.training_horizon:
            raise PrepModeViolation("training window crosses the outer-validation boundary")
        return (
            self.returns[: fold.train_stop].copy(),
            self.lattice.eligible[: fold.train_stop].copy(),
        )

    def validation_returns(self, fold: CycleFold) -> np.ndarray:
        """Always refuses: the actual outer-validation cycle result stays unobserved."""
        raise PrepModeViolation(
            f"real outer-validation returns for {fold.fold_id} are unavailable in prep mode"
        )


def load_grids(root: Path = ROOT) -> CycleGrids:
    """Build the union 4h lattice, the six embargoed folds, and training-only returns."""
    table = _verified_4h_table(root)
    protocol = load_protocol()
    times = table["open_time"].cast("int64").to_numpy()
    close = np.asarray(table["close"].to_numpy(), dtype=np.float64)
    complete = np.asarray(table["complete"].to_numpy(zero_copy_only=False), dtype=bool)
    if np.any(np.diff(times) <= 0) or np.any(times > utc_us(CUTOFF)):
        raise ValueError("invalid or post-cutoff derived 4h timestamps")
    if np.any(close <= 0.0) or not np.all(np.isfinite(close)):
        raise ValueError("non-positive canonical 4h close")

    # A slot is the close-to-close return ending on its own bar; it is eligible only when
    # both endpoint bars are canonically complete and exactly consecutive. Gaps are
    # dropped, never interpolated.
    consecutive = np.diff(times) == BAR_US
    usable = complete[1:] & complete[:-1] & consecutive
    start_us = int(times[0]) + BAR_US
    stop_us = max(utc_us(fold["validation_end_exclusive"]) for fold in protocol["folds"])
    slot_count = int((stop_us - start_us) // BAR_US)
    if slot_count <= 0:
        raise ValueError("union lattice is empty")
    eligible = np.zeros(slot_count, dtype=bool)
    values = np.zeros(slot_count, dtype=np.float64)
    slots = ((times[1:] - start_us) // BAR_US).astype(np.int64)
    inside = (slots >= 0) & (slots < slot_count) & usable
    eligible[slots[inside]] = True
    values[slots[inside]] = np.log(close[1:][inside]) - np.log(close[:-1][inside])
    if not np.all(np.isfinite(values)):
        raise ValueError("non-finite 4h log return")

    folds = []
    for fold in protocol["folds"]:
        if utc_us(fold["train_start"]) > start_us:
            raise ValueError("fold training start precedes the canonical lattice")
        validation_start = utc_us(fold["validation_start"])
        folds.append(
            CycleFold(
                fold_id=fold["fold_id"],
                train_stop=int((validation_start - EMBARGO_DAYS * DAY_US - start_us) // BAR_US),
                validation_start=int((validation_start - start_us) // BAR_US),
                validation_stop=int(
                    (utc_us(fold["validation_end_exclusive"]) - start_us) // BAR_US
                ),
            )
        )
    horizon = max(fold.train_stop for fold in folds)
    values[horizon:] = 0.0
    return CycleGrids(
        lattice=CycleLattice(start_us=start_us, slot_count=slot_count, eligible=eligible),
        folds=tuple(folds),
        returns=values,
        training_horizon=horizon,
        eligible_returns=int(eligible.sum()),
        ineligible_slots=int(slot_count - eligible.sum()),
        incomplete_bars=int((~complete).sum()),
        non_consecutive_bars=int((~consecutive).sum()),
    )


def build_designs(grids: CycleGrids) -> tuple[FoldDesign, ...]:
    return tuple(build_fold_design(grids.lattice, fold) for fold in grids.folds)


def fit_models(grids: CycleGrids) -> tuple[SieveModel, ...]:
    """One training-only AR sieve per fold, selected by BIC over the frozen 0..42 set."""
    models = []
    for fold in grids.folds:
        values, eligible = grids.training_segment(fold)
        models.append(fit_sieve(fold.fold_id, values, eligible, fold.train_stop))
    return tuple(models)


def build_joint_design(grids: CycleGrids, models: tuple[SieveModel, ...]) -> JointNullDesign:
    """Assemble the causal nested-prefix stage schedule for the joint null."""
    bounds = tuple(fold.train_stop for fold in grids.folds)
    if any(later <= earlier for earlier, later in zip(bounds, bounds[1:], strict=False)):
        raise ValueError("expanding training windows must be strictly nested")
    # Stage 0 is the first fold's own training prefix, which any sieve bootstrap must
    # generate in sample. Every later stage is generated by the most recent model whose
    # training window has already closed, so no simulated slot depends on its own future.
    stage_models = (0, *range(len(models)))
    return JointNullDesign(
        lattice=grids.lattice,
        folds=grids.folds,
        models=models,
        stage_bounds=(0, *bounds, grids.lattice.slot_count),
        stage_models=stage_models,
    )


def training_observations(grids: CycleGrids, fold: CycleFold) -> np.ndarray:
    """Eligible real training returns for one fold, used by the fidelity diagnostic."""
    values, eligible = grids.training_segment(fold)
    observations = values[eligible]
    if observations.size <= AR_MAXIMUM_ORDER:
        raise ValueError("training segment is too short")
    return observations
