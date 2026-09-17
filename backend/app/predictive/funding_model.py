"""The two frozen Stage-2 settled-funding dual-head configurations.

`FUNDING_LINEAR_DUAL_HEAD_V1` and `FUNDING_HGBR_DUAL_HEAD_V1` differ only in their
estimators. They share the five funding features, the source-validity rules, the folds, the
chronological 80/20 split with a 48h embargo, the training-only Platt calibration, the action
rule, the magnitude target and the strength rule.

The calibration split, the action rule and the probability rule are imported from
`internal_model` rather than restated: that file's bytes are hashed by two executed
admissions and cannot change, so both Stage-2 configurations provably use the same procedure
the Stage-1 family used.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from . import DOWN, UP
from .funding_source import FEATURE_COUNT
from .internal_model import (
    CALIBRATION_EMBARGO_HOURS,
    CALIBRATION_SPLIT_FRACTION,
    PLATT_PARAMETERS,
    SKLEARN_VERSION,
    CalibrationSplit,
    ModelError,
    calibration_split,
)
from .labels import HOUR_SECONDS

FAMILY = "PREDICTIVE_STAGE2_SETTLED_FUNDING_FAMILY_V1"
LINEAR_MODEL_VERSION = "FUNDING_LINEAR_DUAL_HEAD_V1"
HGBR_MODEL_VERSION = "FUNDING_HGBR_DUAL_HEAD_V1"

LINEAR_DIRECTION_PARAMETERS: dict[str, Any] = {
    "penalty": "l2",
    "C": 1.0,
    "solver": "lbfgs",
    "fit_intercept": True,
    "max_iter": 2000,
    "tol": 1e-8,
    "class_weight": None,
}
LINEAR_MAGNITUDE_PARAMETERS: dict[str, Any] = {"alpha": 1.0, "fit_intercept": True}

HGBR_PARAMETERS: dict[str, Any] = {
    "learning_rate": 0.05,
    "max_iter": 200,
    "max_leaf_nodes": 15,
    "min_samples_leaf": 50,
    "l2_regularization": 1.0,
    "max_bins": 255,
    "early_stopping": False,
    "random_state": 20260916,
}
HGBR_MAGNITUDE_LOSS = "squared_error"

DECISION_RULE = "DECLARE_UP_WHEN_CALIBRATED_P_UP_GREATER_OR_EQUAL_0_5_TIES_UP"
PROBABILITY_RULE = "EXPOSE_P_DECLARED_DIRECTION_CORRECT"
STRENGTH_RULE = "TRAINING_ONLY_INCLUSIVE_PERCENTILE_RANK_OF_ABSOLUTE_PREDICTED_RETURN"


@dataclass(frozen=True)
class DirectionHead:
    """A frozen optional scaler, a frozen base model and a training-only Platt map."""

    scaler: Any
    base: Any
    platt: Any
    split: CalibrationSplit

    def _design(self, features: Sequence[Sequence[float]]) -> Any:
        import numpy as np

        matrix = np.asarray(features, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[1] != FEATURE_COUNT:
            raise ModelError("the direction head was given the wrong feature width")
        return matrix if self.scaler is None else self.scaler.transform(matrix)

    def probability_up(self, features: Sequence[Sequence[float]]) -> list[float]:
        """Calibrated P(UP). The only route from features to an exposed probability."""
        raw = self.base.decision_function(self._design(features)).reshape(-1, 1)
        return [float(value) for value in self.platt.predict_proba(raw)[:, 1]]


@dataclass(frozen=True)
class MagnitudeHead:
    """A frozen optional scaler, a frozen regressor and the training-only strength reference."""

    scaler: Any
    regressor: Any
    reference_absolute_returns: Any
    training_rows: int

    def _design(self, features: Sequence[Sequence[float]]) -> Any:
        import numpy as np

        matrix = np.asarray(features, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[1] != FEATURE_COUNT:
            raise ModelError("the magnitude head was given the wrong feature width")
        return matrix if self.scaler is None else self.scaler.transform(matrix)

    def expected_return(self, features: Sequence[Sequence[float]]) -> list[float]:
        return [float(value) for value in self.regressor.predict(self._design(features))]

    def strength(self, predicted_returns: Sequence[float]) -> list[float]:
        """Inclusive empirical percentile rank against training-only realized moves."""
        import numpy as np

        reference = self.reference_absolute_returns
        total = int(reference.shape[0])
        if total == 0:
            raise ModelError("the strength reference distribution is empty")
        magnitudes = np.abs(np.asarray(predicted_returns, dtype=np.float64))
        ranks = np.searchsorted(reference, magnitudes, side="right")
        return [float(100.0 * value / total) for value in ranks]


def _base_estimator(model_version: str) -> Any:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression

    if model_version == LINEAR_MODEL_VERSION:
        return LogisticRegression(**LINEAR_DIRECTION_PARAMETERS)
    if model_version == HGBR_MODEL_VERSION:
        return HistGradientBoostingClassifier(**HGBR_PARAMETERS)
    raise ModelError(f"unknown Stage-2 configuration: {model_version}")


def _magnitude_estimator(model_version: str) -> Any:
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge

    if model_version == LINEAR_MODEL_VERSION:
        return Ridge(**LINEAR_MAGNITUDE_PARAMETERS)
    if model_version == HGBR_MODEL_VERSION:
        return HistGradientBoostingRegressor(loss=HGBR_MAGNITUDE_LOSS, **HGBR_PARAMETERS)
    raise ModelError(f"unknown Stage-2 configuration: {model_version}")


def _scales(model_version: str) -> bool:
    """Only the linear configuration standardises; HGBR needs no scaling and declares none."""
    return model_version == LINEAR_MODEL_VERSION


def fit_direction_head(
    model_version: str,
    open_times: Sequence[int],
    features: Sequence[Sequence[float]],
    directions: Sequence[str],
) -> DirectionHead:
    """Fit the frozen direction pipeline on one fold's training portion only."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    if not (len(open_times) == len(features) == len(directions)):
        raise ModelError("the training rows are not aligned")
    if any(value not in {UP, DOWN} for value in directions):
        raise ModelError("a training row carries a non-directional label")

    split = calibration_split(open_times)
    embargo = CALIBRATION_EMBARGO_HOURS * HOUR_SECONDS
    boundary = split.boundary_open_time
    matrix = np.asarray(features, dtype=np.float64)
    truth = np.asarray([1 if value == UP else 0 for value in directions], dtype=np.int64)
    moments = np.asarray(open_times, dtype=np.int64)

    base_mask = moments + embargo <= boundary
    calibration_mask = moments >= boundary
    if len(np.unique(truth[base_mask])) < 2 or len(np.unique(truth[calibration_mask])) < 2:
        raise ModelError("a frozen split side lacks both directional classes")

    scaler = StandardScaler().fit(matrix[base_mask]) if _scales(model_version) else None
    design = matrix[base_mask] if scaler is None else scaler.transform(matrix[base_mask])
    base = _base_estimator(model_version)
    base.fit(design, truth[base_mask])
    calibration_design = (
        matrix[calibration_mask] if scaler is None else scaler.transform(matrix[calibration_mask])
    )
    raw = base.decision_function(calibration_design).reshape(-1, 1)
    platt = LogisticRegression(**PLATT_PARAMETERS)
    platt.fit(raw, truth[calibration_mask])
    if list(platt.classes_) != [0, 1]:
        raise ModelError("the Platt map did not see both directional classes")
    return DirectionHead(scaler=scaler, base=base, platt=platt, split=split)


def fit_magnitude_head(
    model_version: str, features: Sequence[Sequence[float]], returns: Sequence[float]
) -> MagnitudeHead:
    """Fit the frozen magnitude head on every source-valid outer-training row."""
    import numpy as np
    from sklearn.preprocessing import StandardScaler

    if len(features) != len(returns):
        raise ModelError("the magnitude training rows are not aligned")
    matrix = np.asarray(features, dtype=np.float64)
    targets = np.asarray(returns, dtype=np.float64)
    if matrix.shape[0] == 0:
        raise ModelError("the magnitude head has no training rows")
    scaler = StandardScaler().fit(matrix) if _scales(model_version) else None
    design = matrix if scaler is None else scaler.transform(matrix)
    regressor = _magnitude_estimator(model_version)
    regressor.fit(design, targets)
    return MagnitudeHead(
        scaler=scaler,
        regressor=regressor,
        reference_absolute_returns=np.sort(np.abs(targets)),
        training_rows=int(matrix.shape[0]),
    )


def specification(model_version: str) -> dict[str, Any]:
    """The executed configuration, exactly as preregistered."""
    linear = model_version == LINEAR_MODEL_VERSION
    if model_version not in {LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION}:
        raise ModelError(f"unknown Stage-2 configuration: {model_version}")
    return {
        "model_version": model_version,
        "family": FAMILY,
        "sklearn_version": SKLEARN_VERSION,
        "direction_base_estimator": (
            "LogisticRegression" if linear else "HistGradientBoostingClassifier"
        ),
        "direction_base_parameters": dict(
            LINEAR_DIRECTION_PARAMETERS if linear else HGBR_PARAMETERS
        ),
        "direction_input_scaling": (
            "STANDARD_SCALER_FITTED_ON_BASE_FIT_ROWS_ONLY" if linear else "NONE_NOT_REQUIRED"
        ),
        "calibration_estimator": "LogisticRegression",
        "calibration_parameters": dict(PLATT_PARAMETERS),
        "calibration_input": "BASE_MODEL_RAW_DECISION_FUNCTION_SCORE",
        "calibration_split_fraction": CALIBRATION_SPLIT_FRACTION,
        "calibration_embargo_hours": CALIBRATION_EMBARGO_HOURS,
        "magnitude_estimator": "Ridge" if linear else "HistGradientBoostingRegressor",
        "magnitude_parameters": dict(LINEAR_MAGNITUDE_PARAMETERS if linear else HGBR_PARAMETERS),
        "magnitude_loss": None if linear else HGBR_MAGNITUDE_LOSS,
        "magnitude_input_scaling": (
            "STANDARD_SCALER_FITTED_ON_ALL_SOURCE_VALID_TRAINING_ROWS"
            if linear
            else "NONE_NOT_REQUIRED"
        ),
        "magnitude_target": "r_24h",
        "magnitude_target_clipping": False,
        "decision_rule": DECISION_RULE,
        "probability_rule": PROBABILITY_RULE,
        "strength_rule": STRENGTH_RULE,
        "probability_threshold_searched": False,
        "hyperparameter_search": False,
        "selective_abstention_beyond_source_availability": False,
    }


__all__ = [
    "DECISION_RULE",
    "FAMILY",
    "HGBR_MAGNITUDE_LOSS",
    "HGBR_MODEL_VERSION",
    "HGBR_PARAMETERS",
    "LINEAR_DIRECTION_PARAMETERS",
    "LINEAR_MAGNITUDE_PARAMETERS",
    "LINEAR_MODEL_VERSION",
    "PROBABILITY_RULE",
    "STRENGTH_RULE",
    "DirectionHead",
    "MagnitudeHead",
    "fit_direction_head",
    "fit_magnitude_head",
    "specification",
]
