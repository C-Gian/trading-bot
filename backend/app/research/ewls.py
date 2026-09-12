"""`EXPONENTIALLY_WEIGHTED_LINEAR_NET_R_V1`: recency-weighted least squares.

A prospectively frozen adaptive architecture. One model becomes effective at the first
UTC hour of each calendar month and its coefficients are then held fixed until the next
monthly model, so feature importance may drift through time without any refit inside a
validation window.

Every training row carries ``w = exp(-ln(2) * age_days / 180)``, measured from the row's
signal instant to the model's effective instant. The 180 calendar-day half-life is frozen
before any result and no alternative is evaluated.

Scaling uses the training-only weighted mean and weighted population variance under the
same weights. There is no regularization, no hyperparameter search, no coefficient
thresholding, no feature dropping and no validation refit.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

ALGORITHM = "NUMPY_FLOAT64_EXPONENTIALLY_WEIGHTED_LEAST_SQUARES_WITH_INTERCEPT"
MODEL_VERSION = "EXPONENTIALLY_WEIGHTED_LINEAR_NET_R_V1"
HALF_LIFE_DAYS = 180.0
UPDATE_CADENCE = "FIRST_UTC_HOUR_OF_EACH_CALENDAR_MONTH"
MIN_STD_EXCLUSIVE = 1e-12
SIGNAL_THRESHOLD = 0.0
DAY_US = 86_400_000_000


class EwlsModelError(ValueError):
    """The frozen weighted fit or its declared inputs were invalid."""


def recency_weights(signal_times: np.ndarray, effective_us: int) -> np.ndarray:
    """``exp(-ln(2) * age_days / 180)`` for every training row."""
    times = np.asarray(signal_times, dtype="<i8")
    if times.size == 0:
        raise EwlsModelError("recency weights require at least one training row")
    if np.any(times >= effective_us):
        raise EwlsModelError("training rows must precede the model effective instant")
    age_days = (effective_us - times.astype(np.float64)) / DAY_US
    weights = np.exp(-math.log(2.0) * age_days / HALF_LIFE_DAYS)
    if not np.isfinite(weights).all() or np.any(weights <= 0.0):
        raise EwlsModelError("recency weights are non-finite or non-positive")
    return np.asarray(weights, dtype=np.float64)


def weighted_moments(values: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Weighted mean and weighted population standard deviation under one weight set."""
    matrix = np.asarray(values, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)
    total = float(w.sum())
    if not math.isfinite(total) or total <= 0.0:
        raise EwlsModelError("weighted scaling requires a positive total weight")
    means = (w[:, None] * matrix).sum(axis=0) / total
    variance = (w[:, None] * (matrix - means) ** 2).sum(axis=0) / total
    if np.any(variance < 0.0):
        raise EwlsModelError("weighted variance is negative")
    stds = np.sqrt(variance)
    if np.any(stds <= MIN_STD_EXCLUSIVE):
        raise EwlsModelError("training feature weighted standard deviation is <= 1e-12")
    return np.asarray(means, dtype=np.float64), np.asarray(stds, dtype=np.float64)


@dataclass(frozen=True)
class FittedEwlsModel:
    effective_us: int
    feature_order: tuple[str, ...]
    means: np.ndarray
    stds: np.ndarray
    intercept: float
    coefficients: np.ndarray
    rank: int
    condition_number: float
    training_rows: int
    effective_sample_size: float
    total_weight: float
    oldest_training_us: int
    newest_training_us: int
    training_matrix_hash: str
    training_label_hash: str
    dependency_hash: str

    def predict(self, matrix: np.ndarray) -> np.ndarray:
        values = np.asarray(matrix, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != len(self.feature_order):
            raise EwlsModelError("prediction matrix feature order/shape changed")
        if not np.isfinite(values).all():
            raise EwlsModelError("prediction matrix contains non-finite values")
        return np.asarray(
            self.intercept + ((values - self.means) / self.stds) @ self.coefficients,
            dtype=np.float64,
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "algorithm": ALGORITHM,
            "model_version": MODEL_VERSION,
            "effective_us": self.effective_us,
            "feature_order": list(self.feature_order),
            "weighted_means": self.means.tolist(),
            "weighted_stds_population": self.stds.tolist(),
            "intercept": self.intercept,
            "coefficients": self.coefficients.tolist(),
            "rank": self.rank,
            "full_rank": self.rank == len(self.feature_order) + 1,
            "condition_number": self.condition_number,
            "training_rows": self.training_rows,
            "effective_sample_size": self.effective_sample_size,
            "total_weight": self.total_weight,
            "oldest_training_us": self.oldest_training_us,
            "newest_training_us": self.newest_training_us,
            "half_life_days": HALF_LIFE_DAYS,
            "update_cadence": UPDATE_CADENCE,
            "scaling": "TRAINING_ONLY_WEIGHTED_MEAN_AND_POPULATION_VARIANCE_SAME_WEIGHTS",
            "regularization": "NONE",
            "hyperparameters_searched": 0,
            "half_life_variants": 0,
            "signal_threshold": SIGNAL_THRESHOLD,
            "thresholds_searched": 0,
            "coefficient_thresholding": False,
            "feature_dropping": False,
            "validation_refit": False,
            "training_matrix_hash": self.training_matrix_hash,
            "training_label_hash": self.training_label_hash,
            "dependency_hash": self.dependency_hash,
        }


def fit_ewls(
    matrix: np.ndarray,
    labels: np.ndarray,
    signal_times: np.ndarray,
    feature_order: tuple[str, ...],
    *,
    effective_us: int,
    training_matrix_hash: str,
    training_label_hash: str,
    dependency_hash: str,
) -> FittedEwlsModel:
    """Deterministic weighted least squares with intercept over standardized features."""
    values = np.asarray(matrix, dtype=np.float64)
    target = np.asarray(labels, dtype=np.float64)
    times = np.asarray(signal_times, dtype="<i8")
    if values.ndim != 2 or values.shape != (len(target), len(feature_order)):
        raise EwlsModelError("training X/y dimensions do not match the frozen feature order")
    if len(times) != len(target):
        raise EwlsModelError("training timestamps do not match the label count")
    if (
        len(target) <= len(feature_order)
        or not np.isfinite(values).all()
        or not np.isfinite(target).all()
    ):
        raise EwlsModelError("training data are insufficient or non-finite")

    weights = recency_weights(times, effective_us)
    means, stds = weighted_moments(values, weights)
    standardized = (values - means) / stds
    root = np.sqrt(weights)
    design = np.column_stack((np.ones(len(target), dtype=np.float64), standardized))
    weighted_design = design * root[:, None]
    weighted_target = target * root
    coefficients, _, rank, singular = np.linalg.lstsq(weighted_design, weighted_target, rcond=None)
    required_rank = len(feature_order) + 1
    if int(rank) != required_rank:
        raise EwlsModelError("weighted design matrix is not full column rank")
    condition = float(singular[0] / singular[-1])
    if not np.isfinite(coefficients).all() or not np.isfinite(condition):
        raise EwlsModelError("weighted least squares produced non-finite model output")

    total = float(weights.sum())
    ess = float(total * total / float((weights * weights).sum()))
    return FittedEwlsModel(
        effective_us=effective_us,
        feature_order=feature_order,
        means=means,
        stds=stds,
        intercept=float(coefficients[0]),
        coefficients=np.asarray(coefficients[1:], dtype=np.float64),
        rank=int(rank),
        condition_number=condition,
        training_rows=len(target),
        effective_sample_size=ess,
        total_weight=total,
        oldest_training_us=int(times.min()),
        newest_training_us=int(times.max()),
        training_matrix_hash=training_matrix_hash,
        training_label_hash=training_label_hash,
        dependency_hash=dependency_hash,
    )


def model_hash(model: FittedEwlsModel) -> str:
    payload = json.dumps(model.as_record(), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def prediction_hash(signal_times: np.ndarray, predictions: np.ndarray) -> str:
    times = np.asarray(signal_times, dtype="<i8")
    values = np.asarray(predictions, dtype="<f8")
    if len(times) != len(values):
        raise EwlsModelError("prediction arrays have inconsistent lengths")
    if not np.isfinite(values).all():
        raise EwlsModelError("predictions contain non-finite values")
    digest = hashlib.sha256()
    digest.update(MODEL_VERSION.encode())
    digest.update(times.tobytes())
    digest.update(values.tobytes())
    return digest.hexdigest()


__all__ = [
    "ALGORITHM",
    "HALF_LIFE_DAYS",
    "MODEL_VERSION",
    "SIGNAL_THRESHOLD",
    "UPDATE_CADENCE",
    "EwlsModelError",
    "FittedEwlsModel",
    "fit_ewls",
    "model_hash",
    "prediction_hash",
    "recency_weights",
    "weighted_moments",
]
