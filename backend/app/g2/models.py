"""Transparent fixed ridge readouts with training-only robust scaling (sections 5-7, 16).

No cross-validation, search or random state exists here. A fit uses only rows whose label had
matured at the fit boundary; its centers/scales/coefficients are frozen in the fit manifest and
reused unchanged until the next scheduled monthly refit.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from .contract import (
    CLIP,
    COLUMNS,
    CONSTANT_SCALE,
    MAD_FACTOR,
    MAX_TRAINING_SPAN,
    MIN_TRAINING_ROWS,
    MIN_TRAINING_SPAN,
    PENALTIES,
)


class SupportError(ValueError):
    """Minimum training support is not met: the conditional model is unavailable."""


@dataclass(frozen=True)
class Scaler:
    centers: tuple[float, ...]
    scales: tuple[float | None, ...]  # None => CONSTANT_TRAINING_FEATURE

    @property
    def constant(self) -> tuple[str, ...]:
        return tuple(c for c, s in zip(COLUMNS, self.scales, strict=True) if s is None)

    def transform(self, raw: np.ndarray) -> np.ndarray:
        """Standardize (clip +-8); constant columns are fixed to exactly zero."""
        raw = np.asarray(raw, dtype=float)
        out = np.zeros_like(raw, dtype=float)
        for j, (center, scale) in enumerate(zip(self.centers, self.scales, strict=True)):
            if scale is None:
                continue
            out[..., j] = np.clip((raw[..., j] - center) / scale, -CLIP, CLIP)
        return out


def fit_scaler(x: np.ndarray) -> Scaler:
    centers: list[float] = []
    scales: list[float | None] = []
    for j in range(x.shape[1]):
        column = x[:, j]
        center = float(np.median(column))
        mad = float(np.median(np.abs(column - center)))
        scale = MAD_FACTOR * mad
        centers.append(center)
        scales.append(scale if np.isfinite(scale) and scale > CONSTANT_SCALE else None)
    return Scaler(tuple(centers), tuple(scales))


def ridge(
    xs: np.ndarray,
    y: np.ndarray,
    penalties: tuple[float, ...] = PENALTIES,
    constant: tuple[bool, ...] | None = None,
) -> tuple[float, np.ndarray]:
    """Minimize mean((y - b0 - X b)^2) + sum(penalty_j * b_j^2); intercept unpenalized.

    Closed form after centering: (Xc'Xc/n + diag(penalty)) b = Xc'yc/n, b0 = mean(y) - mean(X) b.
    Constant columns keep a coefficient of exactly zero.
    """
    n, k = xs.shape
    keep = np.array([not c for c in (constant or (False,) * k)], dtype=bool)
    coefficients = np.zeros(k)
    x_mean = xs.mean(axis=0)
    y_mean = float(y.mean())
    if keep.any():
        xc = xs[:, keep] - x_mean[keep]
        yc = y - y_mean
        gram = xc.T @ xc / n + np.diag(np.asarray(penalties, dtype=float)[keep])
        coefficients[keep] = np.linalg.solve(gram, xc.T @ yc / n)
    intercept = y_mean - float(x_mean @ coefficients)
    return intercept, coefficients


@dataclass(frozen=True)
class TrainingSet:
    times: np.ndarray  # datetime64[m] decision times
    x: np.ndarray  # raw eight-column terms
    y: np.ndarray  # target (z4h or NET_R)
    label_times: np.ndarray  # datetime64[m] maturity instants


def select_training(
    times: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    label_times: np.ndarray,
    boundary: datetime,
) -> TrainingSet:
    """Rows mature at the boundary inside the trailing 730-day window, with finite values."""
    limit = np.datetime64(boundary.replace(tzinfo=None), "m")
    oldest = np.datetime64((boundary - MAX_TRAINING_SPAN).replace(tzinfo=None), "m")
    mask = (
        (label_times <= limit)
        & (times >= oldest)
        & (times < limit)
        & np.isfinite(y)
        & np.isfinite(x).all(axis=1)
    )
    return TrainingSet(times[mask], x[mask], y[mask], label_times[mask])


def check_support(training: TrainingSet) -> None:
    rows = len(training.y)
    if rows < MIN_TRAINING_ROWS:
        raise SupportError(f"{rows} mature rows < {MIN_TRAINING_ROWS}")
    span = (training.times.max() - training.times.min()).astype("timedelta64[m]").astype(int)
    if span < MIN_TRAINING_SPAN.total_seconds() // 60:
        raise SupportError(f"training span {span} minutes < 180 days")


@dataclass(frozen=True)
class Readout:
    """A fitted head: scaler (shared per fit boundary), intercept, coefficients."""

    scaler: Scaler
    intercept: float
    coefficients: tuple[float, ...]

    def terms(self, raw: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
        """(scaled terms, per-column contributions, prediction) for one row."""
        scaled = self.scaler.transform(raw.reshape(1, -1))[0]
        contributions = scaled * np.asarray(self.coefficients)
        return scaled, contributions, float(self.intercept + contributions.sum())


def fit_readout(training: TrainingSet, scaler: Scaler) -> Readout:
    check_support(training)
    xs = scaler.transform(training.x)
    constant = tuple(s is None for s in scaler.scales)
    intercept, coefficients = ridge(xs, training.y, PENALTIES, constant)
    return Readout(scaler, intercept, tuple(float(c) for c in coefficients))


def atoms_sha256(atoms: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(atoms, dtype="<f8").tobytes()).hexdigest()


def first_of_month(moment: datetime) -> bool:
    return moment.day == 1 and moment.hour == 0 and moment.minute == 0
