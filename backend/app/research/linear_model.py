"""Deterministic OLS-with-intercept implementation frozen for WP-008."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np

ALGORITHM = "NUMPY_FLOAT64_ORDINARY_LEAST_SQUARES_WITH_INTERCEPT"
MIN_STD_EXCLUSIVE = 1e-12
SIGNAL_THRESHOLD = 0.0


class LinearModelError(ValueError):
    """The fixed OLS fit or its declared inputs were invalid."""


def array_hash(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for source in arrays:
        array = np.ascontiguousarray(source)
        digest.update(str(array.dtype).encode())
        digest.update(np.asarray(array.shape, dtype="<i8").tobytes())
        digest.update(array.tobytes())
    return digest.hexdigest()


@dataclass(frozen=True)
class FittedLinearModel:
    feature_order: tuple[str, ...]
    means: np.ndarray
    stds: np.ndarray
    intercept: float
    coefficients: np.ndarray
    rank: int
    condition_number: float
    training_matrix_hash: str
    training_label_hash: str
    dependency_hash: str

    def predict(self, matrix: np.ndarray) -> np.ndarray:
        values = np.asarray(matrix, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != len(self.feature_order):
            raise LinearModelError("prediction matrix feature order/shape changed")
        if not np.isfinite(values).all():
            raise LinearModelError("prediction matrix contains non-finite values")
        return np.asarray(
            self.intercept + ((values - self.means) / self.stds) @ self.coefficients,
            dtype=np.float64,
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "algorithm": ALGORITHM,
            "feature_order": list(self.feature_order),
            "means": self.means.tolist(),
            "stds_ddof_0": self.stds.tolist(),
            "intercept": self.intercept,
            "coefficients": self.coefficients.tolist(),
            "rank": self.rank,
            "full_rank": self.rank == len(self.feature_order) + 1,
            "condition_number": self.condition_number,
            "training_matrix_hash": self.training_matrix_hash,
            "training_label_hash": self.training_label_hash,
            "dependency_hash": self.dependency_hash,
            "regularization": "NONE",
            "hyperparameters_searched": 0,
            "signal_threshold": SIGNAL_THRESHOLD,
            "thresholds_searched": 0,
        }


def fit_ols(
    matrix: np.ndarray,
    labels: np.ndarray,
    feature_order: tuple[str, ...],
    *,
    training_matrix_hash: str,
    training_label_hash: str,
    dependency_hash: str,
) -> FittedLinearModel:
    values = np.asarray(matrix, dtype=np.float64)
    target = np.asarray(labels, dtype=np.float64)
    if values.ndim != 2 or values.shape != (len(target), len(feature_order)):
        raise LinearModelError("training X/y dimensions do not match the frozen feature order")
    if (
        len(target) <= len(feature_order)
        or not np.isfinite(values).all()
        or not np.isfinite(target).all()
    ):
        raise LinearModelError("training data are insufficient or non-finite")
    means = values.mean(axis=0, dtype=np.float64)
    stds = values.std(axis=0, ddof=0, dtype=np.float64)
    if np.any(stds <= MIN_STD_EXCLUSIVE):
        raise LinearModelError("training feature standard deviation is <= 1e-12")
    standardized = (values - means) / stds
    design = np.column_stack((np.ones(len(target), dtype=np.float64), standardized))
    coefficients, _, rank, singular = np.linalg.lstsq(design, target, rcond=None)
    required_rank = len(feature_order) + 1
    if int(rank) != required_rank:
        raise LinearModelError("OLS design matrix is not full column rank")
    condition = float(singular[0] / singular[-1])
    if not np.isfinite(coefficients).all() or not np.isfinite(condition):
        raise LinearModelError("OLS produced non-finite model output")
    return FittedLinearModel(
        feature_order,
        means,
        stds,
        float(coefficients[0]),
        np.asarray(coefficients[1:], dtype=np.float64),
        int(rank),
        condition,
        training_matrix_hash,
        training_label_hash,
        dependency_hash,
    )


def model_hash(model: FittedLinearModel) -> str:
    payload = json.dumps(model.as_record(), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()
