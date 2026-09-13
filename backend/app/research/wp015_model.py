"""Exact WP-014 HGBR reused for WP-015 eight- or nine-column inputs."""

from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import dataclass
from typing import Any

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor

from .supervised import SupervisedDataError
from .wp014_model import HGBR_PARAMETERS, MODEL_VERSION, SKLEARN_VERSION


class WP015ModelError(SupervisedDataError):
    """WP-015 model input or frozen identity was invalid."""


@dataclass(frozen=True)
class FittedFundingHGBR:
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
            raise WP015ModelError("prediction matrix differs from frozen WP-015 feature order")
        if not np.isfinite(values).all():
            raise WP015ModelError("prediction matrix contains non-finite values")
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
            "funding_transformations_searched": 0,
            "funding_thresholds_searched": 0,
            "feature_subsets_searched": 0,
            "signal_thresholds_searched": 0,
        }


def fit_hgbr(
    matrix: np.ndarray,
    labels: np.ndarray,
    feature_order: tuple[str, ...],
    *,
    training_matrix_hash: str,
    training_label_hash: str,
    dependency_hash: str,
) -> FittedFundingHGBR:
    values = np.asarray(matrix, dtype=np.float64)
    target = np.asarray(labels, dtype=np.float64)
    if sklearn.__version__ != SKLEARN_VERSION:
        raise WP015ModelError(f"scikit-learn {SKLEARN_VERSION} required")
    if values.ndim != 2 or values.shape != (len(target), len(feature_order)):
        raise WP015ModelError("training matrix differs from frozen WP-015 feature order")
    if not len(target) or not np.isfinite(values).all() or not np.isfinite(target).all():
        raise WP015ModelError("training data are empty or non-finite")
    estimator = HistGradientBoostingRegressor(**HGBR_PARAMETERS)
    estimator.fit(values, target)
    if int(estimator.n_iter_) != HGBR_PARAMETERS["max_iter"]:
        raise WP015ModelError("fixed iteration count drifted")
    serialized = pickle.dumps(estimator, protocol=5)
    serialization_hash = hashlib.sha256(serialized).hexdigest()
    identity = hashlib.sha256(
        json.dumps(
            {
                "model_version": MODEL_VERSION,
                "sklearn_version": sklearn.__version__,
                "feature_order": list(feature_order),
                "parameters": HGBR_PARAMETERS,
                "training_matrix_hash": training_matrix_hash,
                "training_label_hash": training_label_hash,
                "dependency_hash": dependency_hash,
                "serialization_sha256": serialization_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return FittedFundingHGBR(
        feature_order,
        estimator,
        training_matrix_hash,
        training_label_hash,
        dependency_hash,
        serialization_hash,
        identity,
    )


__all__ = ["FittedFundingHGBR", "WP015ModelError", "fit_hgbr"]
