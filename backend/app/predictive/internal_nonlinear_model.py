"""The reserved Stage-1 configuration `INTERNAL_HGBR_DUAL_HEAD_V1`.

The structural parameters, the loss, the seed and the inheritance rule were frozen in
`research/protocols/PREDICTIVE-STAGE1-INTERNAL-SEARCH-PLAN-V1.json` in commit `54dc831`,
before the linear result existed. Nothing here chooses anything: it executes what the
reserved specification already says.

This module is separate from `internal_model` because that file's bytes are hashed by the
executed `PREDICTIVE-INTERNAL-STRUCTURE-V1` admission artifact and may not change. The
calibration split, the action rule and the probability rule are imported from it unmodified,
so both Stage-1 configurations provably share one procedure rather than two copies of it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from . import DOWN, UP
from .internal_features import FEATURE_COUNT
from .internal_model import (
    CALIBRATION_EMBARGO_HOURS,
    CALIBRATION_SPLIT_FRACTION,
    PLATT_PARAMETERS,
    RESERVED_HGBR_PARAMETERS,
    SKLEARN_VERSION,
    CalibrationSplit,
    ModelError,
    calibration_split,
    reserved_hgbr_specification,
)
from .labels import HOUR_SECONDS

MODEL_VERSION = "INTERNAL_HGBR_DUAL_HEAD_V1"
MAGNITUDE_LOSS = "squared_error"

# Inherited verbatim from the linear configuration. Standardisation is part of the V1
# pipeline the reserved specification inherits; it is not a new modelling choice.
DIRECTION_INPUT_SCALING = "STANDARD_SCALER_FITTED_ON_BASE_FIT_ROWS_ONLY"
MAGNITUDE_INPUT_SCALING = "STANDARD_SCALER_FITTED_ON_ALL_FEATURE_VALID_TRAINING_ROWS"


@dataclass(frozen=True)
class NonlinearDirectionHead:
    """A frozen scaler, a frozen boosted classifier and a training-only Platt map."""

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
class NonlinearMagnitudeHead:
    """A frozen scaler, a frozen boosted regressor and the training-only strength reference."""

    scaler: Any
    regressor: Any
    reference_absolute_returns: Any
    training_rows: int

    def expected_return(self, features: Sequence[Sequence[float]]) -> list[float]:
        import numpy as np

        matrix = np.asarray(features, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[1] != FEATURE_COUNT:
            raise ModelError("the magnitude head was given the wrong feature width")
        return [float(value) for value in self.regressor.predict(self.scaler.transform(matrix))]

    def strength(self, predicted_returns: Sequence[float]) -> list[float]:
        """Inclusive empirical percentile rank against training-only realized moves.

        Identical in definition to the linear head's strength; duplicated rather than
        imported because the linear module's bytes are frozen by an executed admission.
        """
        import numpy as np

        reference = self.reference_absolute_returns
        total = int(reference.shape[0])
        if total == 0:
            raise ModelError("the strength reference distribution is empty")
        magnitudes = np.abs(np.asarray(predicted_returns, dtype=np.float64))
        ranks = np.searchsorted(reference, magnitudes, side="right")
        return [float(100.0 * value / total) for value in ranks]


def fit_direction_head(
    open_times: Sequence[int],
    features: Sequence[Sequence[float]],
    directions: Sequence[str],
) -> NonlinearDirectionHead:
    """Fit the reserved direction pipeline on one fold's training portion only."""
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier
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
    base = HistGradientBoostingClassifier(**RESERVED_HGBR_PARAMETERS)
    base.fit(scaler.transform(matrix[base_mask]), truth[base_mask])
    raw = base.decision_function(scaler.transform(matrix[calibration_mask])).reshape(-1, 1)
    platt = LogisticRegression(**PLATT_PARAMETERS)
    platt.fit(raw, truth[calibration_mask])
    if list(platt.classes_) != [0, 1]:
        raise ModelError("the Platt map did not see both directional classes")
    return NonlinearDirectionHead(scaler=scaler, base=base, platt=platt, split=split)


def fit_magnitude_head(
    features: Sequence[Sequence[float]], returns: Sequence[float]
) -> NonlinearMagnitudeHead:
    """Fit the reserved magnitude head on every feature-valid outer-training row."""
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler

    if len(features) != len(returns):
        raise ModelError("the magnitude training rows are not aligned")
    matrix = np.asarray(features, dtype=np.float64)
    targets = np.asarray(returns, dtype=np.float64)
    if matrix.shape[0] == 0:
        raise ModelError("the magnitude head has no training rows")
    scaler = StandardScaler().fit(matrix)
    regressor = HistGradientBoostingRegressor(loss=MAGNITUDE_LOSS, **RESERVED_HGBR_PARAMETERS)
    regressor.fit(scaler.transform(matrix), targets)
    return NonlinearMagnitudeHead(
        scaler=scaler,
        regressor=regressor,
        reference_absolute_returns=np.sort(np.abs(targets)),
        training_rows=int(matrix.shape[0]),
    )


def nonlinear_specification() -> dict[str, Any]:
    """The executed configuration, expanded from the reserved specification."""
    reserved = reserved_hgbr_specification()
    return {
        "model_version": MODEL_VERSION,
        "family": reserved["family"],
        "sklearn_version": SKLEARN_VERSION,
        "frozen_by": "research/protocols/PREDICTIVE-STAGE1-INTERNAL-SEARCH-PLAN-V1.json",
        "frozen_in_commit": "54dc831d15b0ddf625425f6a416a84704258f1f1",
        "direction_base_estimator": reserved["direction_estimator"],
        "direction_base_parameters": dict(RESERVED_HGBR_PARAMETERS),
        "direction_input_scaling": DIRECTION_INPUT_SCALING,
        "calibration_estimator": "LogisticRegression",
        "calibration_parameters": dict(PLATT_PARAMETERS),
        "calibration_input": "BASE_MODEL_RAW_DECISION_FUNCTION_SCORE",
        "calibration_split_fraction": CALIBRATION_SPLIT_FRACTION,
        "calibration_embargo_hours": CALIBRATION_EMBARGO_HOURS,
        "magnitude_estimator": reserved["magnitude_estimator"],
        "magnitude_parameters": dict(RESERVED_HGBR_PARAMETERS),
        "magnitude_loss": MAGNITUDE_LOSS,
        "magnitude_input_scaling": MAGNITUDE_INPUT_SCALING,
        "magnitude_target": "r_24h",
        "magnitude_target_clipping": False,
        "decision_rule": "DECLARE_UP_WHEN_CALIBRATED_P_UP_GREATER_OR_EQUAL_0_5_TIES_UP",
        "probability_rule": "EXPOSE_P_DECLARED_DIRECTION_CORRECT",
        "strength_rule": ("TRAINING_ONLY_INCLUSIVE_PERCENTILE_RANK_OF_ABSOLUTE_PREDICTED_RETURN"),
        "probability_threshold_searched": False,
        "hyperparameter_search": False,
        "inherited_from_linear_configuration": [
            "FEATURE_SET",
            "FEATURE_VALIDITY_RULES",
            "OUTER_FOLDS",
            "CALIBRATION_SPLIT",
            "CALIBRATION_PROCEDURE",
            "ACTION_RULE",
            "SCORING_SEMANTICS",
            "INPUT_STANDARDISATION",
        ],
    }


__all__ = [
    "DIRECTION_INPUT_SCALING",
    "MAGNITUDE_INPUT_SCALING",
    "MAGNITUDE_LOSS",
    "MODEL_VERSION",
    "NonlinearDirectionHead",
    "NonlinearMagnitudeHead",
    "fit_direction_head",
    "fit_magnitude_head",
    "nonlinear_specification",
]
