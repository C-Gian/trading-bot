"""The frozen Stage-1 internal dual-head predictor family.

`INTERNAL_LINEAR_DUAL_HEAD_V1` is executed by `PREDICTIVE-INTERNAL-STRUCTURE-V1`.
`INTERNAL_HGBR_DUAL_HEAD_V1` is declared here so the reserved configuration is frozen
before the linear result exists, and is not executed by this checkpoint.

Both heads are fitted on the chronological training portion of one outer fold and nothing
else. No outer-evaluation row reaches a scaler, a coefficient, a calibration map or the
strength reference distribution. There is no hyperparameter search, no threshold search and
no probability-based abstention: when the causal feature vector exists the direction head
always declares a side.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from . import DOWN, UP
from .internal_features import FEATURE_COUNT
from .labels import HOUR_SECONDS

MODEL_FAMILY = "PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1"
LINEAR_MODEL_VERSION = "INTERNAL_LINEAR_DUAL_HEAD_V1"
HGBR_MODEL_VERSION = "INTERNAL_HGBR_DUAL_HEAD_V1"
SKLEARN_VERSION = "1.7.2"
RESERVED_RANDOM_STATE = 20260916

CALIBRATION_SPLIT_FRACTION = 0.80
# One 24h label horizon plus one further 24h embargo before the calibration side opens.
CALIBRATION_EMBARGO_HOURS = 48

DIRECTION_BASE_PARAMETERS: dict[str, Any] = {
    "penalty": "l2",
    "C": 1.0,
    "solver": "lbfgs",
    "fit_intercept": True,
    "max_iter": 2000,
    "tol": 1e-8,
    "class_weight": None,
}
PLATT_PARAMETERS: dict[str, Any] = {
    "penalty": None,
    "solver": "lbfgs",
    "fit_intercept": True,
    "max_iter": 2000,
    "tol": 1e-8,
}
MAGNITUDE_PARAMETERS: dict[str, Any] = {"alpha": 1.0, "fit_intercept": True}

# Frozen now so the linear result cannot influence the reserved configuration. Not executed
# in this checkpoint; see the Stage-1 search plan.
RESERVED_HGBR_PARAMETERS: dict[str, Any] = {
    "learning_rate": 0.05,
    "max_iter": 200,
    "max_leaf_nodes": 15,
    "min_samples_leaf": 50,
    "l2_regularization": 1.0,
    "max_bins": 255,
    "early_stopping": False,
    "random_state": RESERVED_RANDOM_STATE,
}

DECISION_RULE = "DECLARE_UP_WHEN_CALIBRATED_P_UP_GREATER_OR_EQUAL_0_5_TIES_UP"
PROBABILITY_RULE = "EXPOSE_P_DECLARED_DIRECTION_CORRECT"
STRENGTH_RULE = "TRAINING_ONLY_INCLUSIVE_PERCENTILE_RANK_OF_ABSOLUTE_PREDICTED_RETURN"


class ModelError(RuntimeError):
    """The frozen fitting procedure cannot be honoured, so the fold fails closed."""


@dataclass(frozen=True)
class CalibrationSplit:
    """Where the outer-training portion divides into base-fit and calibration rows."""

    boundary_open_time: int
    boundary_index: int
    base_fit_rows: int
    calibration_rows: int
    dropped_to_embargo: int


@dataclass(frozen=True)
class DirectionHead:
    """A frozen scaler, a frozen base model and a frozen training-only Platt map."""

    scaler: Any
    base: Any
    platt: Any
    split: CalibrationSplit

    def probability_up(self, features: Sequence[Sequence[float]]) -> list[float]:
        """Calibrated P(UP). The only route from features to an exposed probability."""
        import numpy as np

        matrix = np.asarray(features, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[1] != FEATURE_COUNT:
            raise ModelError("the direction head was given the wrong feature width")
        raw = self.base.decision_function(self.scaler.transform(matrix)).reshape(-1, 1)
        return [float(value) for value in self.platt.predict_proba(raw)[:, 1]]


@dataclass(frozen=True)
class MagnitudeHead:
    """A frozen scaler, a frozen ridge and the training-only strength reference."""

    scaler: Any
    ridge: Any
    reference_absolute_returns: Any
    training_rows: int

    def expected_return(self, features: Sequence[Sequence[float]]) -> list[float]:
        import numpy as np

        matrix = np.asarray(features, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[1] != FEATURE_COUNT:
            raise ModelError("the magnitude head was given the wrong feature width")
        return [float(value) for value in self.ridge.predict(self.scaler.transform(matrix))]

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


def calibration_split(open_times: Sequence[int]) -> CalibrationSplit:
    """The frozen 80% chronological boundary, with a 48h embargo before calibration.

    `S` is the timestamp at index `floor(0.80 * N)` of the chronologically ordered
    feature-valid outer-training rows. Base-fit rows satisfy `T + 48h <= S`; calibration
    rows satisfy `T >= S`. The rows between the two are dropped by the embargo and counted.
    """
    total = len(open_times)
    if total < 2:
        raise ModelError("the outer-training portion is too small to split")
    ordered = list(open_times)
    if any(ordered[index] <= ordered[index - 1] for index in range(1, total)):
        raise ModelError("the outer-training portion is not strictly chronological")
    index = int(CALIBRATION_SPLIT_FRACTION * total)
    index = max(0, min(index, total - 1))
    boundary = ordered[index]
    embargo = CALIBRATION_EMBARGO_HOURS * HOUR_SECONDS
    base_fit = sum(1 for moment in ordered if moment + embargo <= boundary)
    calibration = sum(1 for moment in ordered if moment >= boundary)
    if base_fit == 0 or calibration == 0:
        raise ModelError("the frozen calibration split leaves an unusable side")
    return CalibrationSplit(
        boundary_open_time=boundary,
        boundary_index=index,
        base_fit_rows=base_fit,
        calibration_rows=calibration,
        dropped_to_embargo=total - base_fit - calibration,
    )


def fit_direction_head(
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

    scaler = StandardScaler().fit(matrix[base_mask])
    base = LogisticRegression(**DIRECTION_BASE_PARAMETERS)
    base.fit(scaler.transform(matrix[base_mask]), truth[base_mask])
    raw = base.decision_function(scaler.transform(matrix[calibration_mask])).reshape(-1, 1)
    platt = LogisticRegression(**PLATT_PARAMETERS)
    platt.fit(raw, truth[calibration_mask])
    if list(platt.classes_) != [0, 1]:
        raise ModelError("the Platt map did not see both directional classes")
    return DirectionHead(scaler=scaler, base=base, platt=platt, split=split)


def fit_magnitude_head(
    features: Sequence[Sequence[float]], returns: Sequence[float]
) -> MagnitudeHead:
    """Fit the frozen magnitude head on every feature-valid outer-training row."""
    import numpy as np
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    if len(features) != len(returns):
        raise ModelError("the magnitude training rows are not aligned")
    matrix = np.asarray(features, dtype=np.float64)
    targets = np.asarray(returns, dtype=np.float64)
    if matrix.shape[0] == 0:
        raise ModelError("the magnitude head has no training rows")
    scaler = StandardScaler().fit(matrix)
    ridge = Ridge(**MAGNITUDE_PARAMETERS)
    ridge.fit(scaler.transform(matrix), targets)
    return MagnitudeHead(
        scaler=scaler,
        ridge=ridge,
        reference_absolute_returns=np.sort(np.abs(targets)),
        training_rows=int(matrix.shape[0]),
    )


def declared_direction(probability_up: float) -> str:
    """`p_up >= 0.5` declares UP; there is no threshold to search and no abstention here."""
    return UP if probability_up >= 0.5 else DOWN


def declared_probability(probability_up: float) -> float:
    """Always P(declared direction correct), as the evaluation contract requires."""
    return probability_up if probability_up >= 0.5 else 1.0 - probability_up


def linear_specification() -> dict[str, Any]:
    """The executed configuration, exactly as preregistered."""
    return {
        "model_version": LINEAR_MODEL_VERSION,
        "family": MODEL_FAMILY,
        "sklearn_version": SKLEARN_VERSION,
        "direction_base_estimator": "LogisticRegression",
        "direction_base_parameters": dict(DIRECTION_BASE_PARAMETERS),
        "direction_input_scaling": "STANDARD_SCALER_FITTED_ON_BASE_FIT_ROWS_ONLY",
        "calibration_estimator": "LogisticRegression",
        "calibration_parameters": dict(PLATT_PARAMETERS),
        "calibration_input": "BASE_MODEL_RAW_DECISION_FUNCTION_SCORE",
        "calibration_split_fraction": CALIBRATION_SPLIT_FRACTION,
        "calibration_embargo_hours": CALIBRATION_EMBARGO_HOURS,
        "magnitude_estimator": "Ridge",
        "magnitude_parameters": dict(MAGNITUDE_PARAMETERS),
        "magnitude_input_scaling": "STANDARD_SCALER_FITTED_ON_ALL_FEATURE_VALID_TRAINING_ROWS",
        "magnitude_target": "r_24h",
        "magnitude_target_clipping": False,
        "decision_rule": DECISION_RULE,
        "probability_rule": PROBABILITY_RULE,
        "strength_rule": STRENGTH_RULE,
        "probability_threshold_searched": False,
        "hyperparameter_search": False,
    }


def reserved_hgbr_specification() -> dict[str, Any]:
    """The reserved configuration, frozen before the linear result and not executed here."""
    return {
        "model_version": HGBR_MODEL_VERSION,
        "family": MODEL_FAMILY,
        "sklearn_version": SKLEARN_VERSION,
        "executed_in_this_checkpoint": False,
        "direction_estimator": "HistGradientBoostingClassifier",
        "magnitude_estimator": "HistGradientBoostingRegressor",
        "magnitude_loss": "squared_error",
        "structural_parameters": dict(RESERVED_HGBR_PARAMETERS),
        "feature_set": "IDENTICAL_TO_INTERNAL_LINEAR_DUAL_HEAD_V1",
        "feature_validity_rules": "IDENTICAL_TO_INTERNAL_LINEAR_DUAL_HEAD_V1",
        "folds": "IDENTICAL_TO_INTERNAL_LINEAR_DUAL_HEAD_V1",
        "calibration_split": "IDENTICAL_TO_INTERNAL_LINEAR_DUAL_HEAD_V1",
        "calibration_procedure": "TRAINING_ONLY_PLATT_ON_RAW_SCORE",
        "action_rule": "IDENTICAL_TO_INTERNAL_LINEAR_DUAL_HEAD_V1",
        "scoring_semantics": "IDENTICAL_TO_INTERNAL_LINEAR_DUAL_HEAD_V1",
        "hyperparameter_search": False,
    }


__all__ = [
    "CALIBRATION_EMBARGO_HOURS",
    "CALIBRATION_SPLIT_FRACTION",
    "DECISION_RULE",
    "DIRECTION_BASE_PARAMETERS",
    "HGBR_MODEL_VERSION",
    "LINEAR_MODEL_VERSION",
    "MAGNITUDE_PARAMETERS",
    "MODEL_FAMILY",
    "PLATT_PARAMETERS",
    "PROBABILITY_RULE",
    "RESERVED_HGBR_PARAMETERS",
    "RESERVED_RANDOM_STATE",
    "SKLEARN_VERSION",
    "STRENGTH_RULE",
    "CalibrationSplit",
    "DirectionHead",
    "MagnitudeHead",
    "ModelError",
    "calibration_split",
    "declared_direction",
    "declared_probability",
    "fit_direction_head",
    "fit_magnitude_head",
    "linear_specification",
    "reserved_hgbr_specification",
]
