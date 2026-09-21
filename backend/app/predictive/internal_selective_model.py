"""Frozen fitting procedures for the second Generation V2 family.

Same shape as the first V2 family — one base classifier and one training-only Platt map per
fold — over the inherited eighteen-feature causal internal vector, with this family's own
declared inference seed. No V1 fitted model, prediction or probability artifact is loaded
here: the family refits from the raw canonical bars.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from . import DOWN, UP
from .internal_selective_features import FEATURE_COUNT
from .labels import HOUR_SECONDS

LINEAR_MODEL_VERSION = "V2_INTERNAL_LINEAR_V1"
HGBR_MODEL_VERSION = "V2_INTERNAL_HGBR_V1"
SKLEARN_VERSION = "1.7.2"
INFERENCE_SEED = 20260922
CALIBRATION_SPLIT_FRACTION = 0.80
CALIBRATION_EMBARGO_HOURS = 48

LINEAR_PARAMETERS: dict[str, Any] = {
    "penalty": "l2",
    "C": 1.0,
    "class_weight": None,
    "fit_intercept": True,
    "solver": "lbfgs",
    "max_iter": 2000,
    "tol": 1e-8,
}
HGBR_PARAMETERS: dict[str, Any] = {
    "learning_rate": 0.05,
    "max_iter": 200,
    "max_leaf_nodes": 15,
    "min_samples_leaf": 50,
    "l2_regularization": 1.0,
    "max_bins": 255,
    "early_stopping": False,
    "random_state": INFERENCE_SEED,
}
PLATT_PARAMETERS: dict[str, Any] = {
    "penalty": None,
    "solver": "lbfgs",
    "fit_intercept": True,
    "max_iter": 2000,
    "tol": 1e-8,
}


class InternalSelectiveModelError(RuntimeError):
    """The frozen model or calibration procedure cannot be honoured."""


@dataclass(frozen=True)
class CalibrationSplit:
    boundary_open_time: int
    boundary_index: int
    base_fit_rows: int
    calibration_rows: int
    dropped_to_embargo: int


@dataclass(frozen=True)
class InternalProbabilityHead:
    model_version: str
    scaler: Any | None
    base: Any
    platt: Any
    split: CalibrationSplit

    def probability_up(self, features: Sequence[Sequence[float]]) -> list[float]:
        """Return calibrated P(r_24h > 0), never a raw model score."""
        import numpy as np

        matrix = np.asarray(features, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[1] != FEATURE_COUNT:
            raise InternalSelectiveModelError("the internal head was given the wrong width")
        transformed = self.scaler.transform(matrix) if self.scaler is not None else matrix
        raw = self.base.decision_function(transformed).reshape(-1, 1)
        probabilities = self.platt.predict_proba(raw)[:, 1]
        if not np.all(np.isfinite(probabilities)) or not np.all(
            (probabilities >= 0.0) & (probabilities <= 1.0)
        ):
            raise InternalSelectiveModelError("the calibrated probability output is invalid")
        return [float(value) for value in probabilities]


def calibration_split(open_times: Sequence[int]) -> CalibrationSplit:
    """Chronological 80/20 split with the frozen 48h embargo."""
    total = len(open_times)
    if total < 2:
        raise InternalSelectiveModelError("the outer-training portion is too small to split")
    ordered = list(open_times)
    if any(ordered[index] <= ordered[index - 1] for index in range(1, total)):
        raise InternalSelectiveModelError("the outer-training portion is not chronological")
    index = min(int(CALIBRATION_SPLIT_FRACTION * total), total - 1)
    boundary = ordered[index]
    embargo = CALIBRATION_EMBARGO_HOURS * HOUR_SECONDS
    base_fit = sum(1 for moment in ordered if moment + embargo <= boundary)
    calibration = sum(1 for moment in ordered if moment >= boundary)
    if base_fit == 0 or calibration == 0:
        raise InternalSelectiveModelError("the frozen calibration split leaves an unusable side")
    return CalibrationSplit(
        boundary_open_time=boundary,
        boundary_index=index,
        base_fit_rows=base_fit,
        calibration_rows=calibration,
        dropped_to_embargo=total - base_fit - calibration,
    )


def fit_probability_head(
    model_version: str,
    open_times: Sequence[int],
    features: Sequence[Sequence[float]],
    directions: Sequence[str],
) -> InternalProbabilityHead:
    """Fit exactly one base classifier and one training-only Platt map."""
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    if model_version not in {LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION}:
        raise InternalSelectiveModelError(f"unknown frozen internal model: {model_version}")
    if not (len(open_times) == len(features) == len(directions)):
        raise InternalSelectiveModelError("the training rows are not aligned")
    if any(direction not in {UP, DOWN} for direction in directions):
        raise InternalSelectiveModelError("a training row carries a non-directional label")

    split = calibration_split(open_times)
    matrix = np.asarray(features, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != FEATURE_COUNT:
        raise InternalSelectiveModelError("the training matrix has the wrong feature width")
    if not np.all(np.isfinite(matrix)):
        raise InternalSelectiveModelError("the training matrix contains an invalid feature")
    truth = np.asarray([1 if direction == UP else 0 for direction in directions], dtype=np.int64)
    moments = np.asarray(open_times, dtype=np.int64)
    embargo = CALIBRATION_EMBARGO_HOURS * HOUR_SECONDS
    base_mask = moments + embargo <= split.boundary_open_time
    calibration_mask = moments >= split.boundary_open_time
    if len(np.unique(truth[base_mask])) < 2 or len(np.unique(truth[calibration_mask])) < 2:
        raise InternalSelectiveModelError("a frozen fitting side lacks both directional classes")

    scaler: Any | None
    if model_version == LINEAR_MODEL_VERSION:
        scaler = StandardScaler().fit(matrix[base_mask])
        base_input = scaler.transform(matrix[base_mask])
        calibration_input = scaler.transform(matrix[calibration_mask])
        base = LogisticRegression(**LINEAR_PARAMETERS)
    else:
        scaler = None
        base_input = matrix[base_mask]
        calibration_input = matrix[calibration_mask]
        base = HistGradientBoostingClassifier(**HGBR_PARAMETERS)
    base.fit(base_input, truth[base_mask])
    raw = base.decision_function(calibration_input).reshape(-1, 1)
    platt = LogisticRegression(**PLATT_PARAMETERS)
    platt.fit(raw, truth[calibration_mask])
    if list(platt.classes_) != [0, 1]:
        raise InternalSelectiveModelError("the Platt map did not see both directional classes")
    return InternalProbabilityHead(
        model_version=model_version,
        scaler=scaler,
        base=base,
        platt=platt,
        split=split,
    )


def model_specification(model_version: str) -> dict[str, Any]:
    if model_version == LINEAR_MODEL_VERSION:
        estimator = "StandardScaler + LogisticRegression"
        parameters = dict(LINEAR_PARAMETERS)
        scaling = "STANDARD_SCALER_FITTED_ON_BASE_FIT_ROWS_ONLY"
    elif model_version == HGBR_MODEL_VERSION:
        estimator = "HistGradientBoostingClassifier"
        parameters = dict(HGBR_PARAMETERS)
        scaling = "NONE"
    else:
        raise InternalSelectiveModelError(f"unknown frozen internal model: {model_version}")
    return {
        "model_version": model_version,
        "sklearn_version": SKLEARN_VERSION,
        "base_estimator": estimator,
        "base_parameters": parameters,
        "input_scaling": scaling,
        "calibration_estimator": "LogisticRegression",
        "calibration_parameters": dict(PLATT_PARAMETERS),
        "calibration_input": "BASE_MODEL_RAW_DECISION_FUNCTION_SCORE",
        "calibration_split_fraction": CALIBRATION_SPLIT_FRACTION,
        "calibration_embargo_hours": CALIBRATION_EMBARGO_HOURS,
        "probability_semantics": "P_R_24H_GREATER_THAN_ZERO",
        "magnitude_estimator": None,
        "hyperparameter_search": False,
        "threshold_search": False,
        "v1_fitted_model_or_prediction_loaded": False,
    }


__all__ = [
    "CALIBRATION_EMBARGO_HOURS",
    "CALIBRATION_SPLIT_FRACTION",
    "HGBR_MODEL_VERSION",
    "HGBR_PARAMETERS",
    "INFERENCE_SEED",
    "LINEAR_MODEL_VERSION",
    "LINEAR_PARAMETERS",
    "PLATT_PARAMETERS",
    "SKLEARN_VERSION",
    "CalibrationSplit",
    "InternalProbabilityHead",
    "InternalSelectiveModelError",
    "calibration_split",
    "fit_probability_head",
    "model_specification",
]
