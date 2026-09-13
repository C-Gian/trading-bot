"""Frozen shallow HGBR implementation for WP-014."""

from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import dataclass
from typing import Any

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor

from .supervised import FULL_FEATURES, SupervisedDataError

MODEL_VERSION = "SHALLOW_INTERNAL_HGBR_V1"
SKLEARN_VERSION = "1.7.2"
HGBR_PARAMETERS: dict[str, Any] = {
    "loss": "squared_error",
    "learning_rate": 0.05,
    "max_iter": 64,
    "max_leaf_nodes": 7,
    "max_depth": 3,
    "min_samples_leaf": 128,
    "l2_regularization": 1.0,
    "max_bins": 63,
    "early_stopping": False,
    "random_state": 0,
}


class HGBRModelError(SupervisedDataError):
    """The fixed nonlinear model or its governed inputs were invalid."""


def _canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class FittedHGBR:
    feature_order: tuple[str, ...]
    estimator: HistGradientBoostingRegressor
    training_matrix_hash: str
    training_label_hash: str
    dependency_hash: str
    serialization_sha256: str
    identity_sha256: str

    def predict(self, matrix: np.ndarray) -> np.ndarray:
        values = np.asarray(matrix, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != len(self.feature_order):
            raise HGBRModelError("prediction matrix differs from frozen F1-F8 shape/order")
        if not np.isfinite(values).all():
            raise HGBRModelError("prediction matrix contains non-finite values")
        return np.asarray(self.estimator.predict(values), dtype=np.float64)

    def as_record(self) -> dict[str, Any]:
        iterations = int(self.estimator.n_iter_)
        trees_per_iteration = int(self.estimator.n_trees_per_iteration_)
        return {
            "model_version": MODEL_VERSION,
            "algorithm": "sklearn.ensemble.HistGradientBoostingRegressor",
            "sklearn_version": sklearn.__version__,
            "feature_order": list(self.feature_order),
            "input_scaling": "NONE_RAW_GOVERNED_VALUES",
            "parameters": dict(HGBR_PARAMETERS),
            "training_matrix_hash": self.training_matrix_hash,
            "training_label_hash": self.training_label_hash,
            "dependency_hash": self.dependency_hash,
            "serialization_format": "PYTHON_PICKLE_PROTOCOL_5_NOT_COMMITTED",
            "serialization_sha256": self.serialization_sha256,
            "identity_sha256": self.identity_sha256,
            "boosting_iterations": iterations,
            "trees_per_iteration": trees_per_iteration,
            "tree_count": iterations * trees_per_iteration,
            "leaf_node_statistics": "UNAVAILABLE_IN_PUBLIC_SKLEARN_API_NOT_INSPECTED",
            "hyperparameters_searched": 0,
            "feature_variants": 0,
            "thresholds_searched": 0,
        }


def fit_hgbr(
    matrix: np.ndarray,
    labels: np.ndarray,
    *,
    training_matrix_hash: str,
    training_label_hash: str,
    dependency_hash: str,
) -> FittedHGBR:
    values = np.asarray(matrix, dtype=np.float64)
    target = np.asarray(labels, dtype=np.float64)
    if sklearn.__version__ != SKLEARN_VERSION:
        raise HGBRModelError(
            f"scikit-learn {SKLEARN_VERSION} is required, found {sklearn.__version__}"
        )
    if values.ndim != 2 or values.shape != (len(target), len(FULL_FEATURES)):
        raise HGBRModelError("training data differ from the frozen F1-F8 matrix")
    if not len(target) or not np.isfinite(values).all() or not np.isfinite(target).all():
        raise HGBRModelError("training data are empty or non-finite")
    estimator = HistGradientBoostingRegressor(**HGBR_PARAMETERS)
    estimator.fit(values, target)
    if int(estimator.n_iter_) != HGBR_PARAMETERS["max_iter"]:
        raise HGBRModelError("early stopping or iteration drift changed the fixed model")
    serialized = pickle.dumps(estimator, protocol=5)
    serialization_sha256 = hashlib.sha256(serialized).hexdigest()
    identity_sha256 = _canonical_hash(
        {
            "model_version": MODEL_VERSION,
            "sklearn_version": sklearn.__version__,
            "feature_order": list(FULL_FEATURES),
            "parameters": HGBR_PARAMETERS,
            "training_matrix_hash": training_matrix_hash,
            "training_label_hash": training_label_hash,
            "dependency_hash": dependency_hash,
            "serialization_sha256": serialization_sha256,
        }
    )
    return FittedHGBR(
        FULL_FEATURES,
        estimator,
        training_matrix_hash,
        training_label_hash,
        dependency_hash,
        serialization_sha256,
        identity_sha256,
    )


__all__ = [
    "HGBR_PARAMETERS",
    "MODEL_VERSION",
    "SKLEARN_VERSION",
    "FittedHGBR",
    "HGBRModelError",
    "fit_hgbr",
]
