"""The four required naive baselines of `PREDICTIVE_EVALUATION_CONTRACT_V1` §5.

Each baseline declares exactly the quantities §5 says it declares, and nothing is imputed
to satisfy a metric it never claimed:

- `TRAINING_UP_BASE_RATE`   direction + probability, fitted on training only (§5.1);
- `ALWAYS_UP`               direction only, `PROBABILITY_NOT_DECLARED` (§5.2);
- `PREVIOUS_24H_SIGN_PERSISTENCE` direction only, abstains when unobservable (§5.2);
- `ZERO_RETURN_MAGNITUDE`   magnitude only, `DIRECTION_NOT_DECLARED` (§5.3).

None of these is a model. There is no fit beyond one counted base rate, no parameter
search, and nothing is tuned.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import ABSTAIN, DOWN, HORIZON_HOURS, NEUTRAL, UP
from .evaluation import Prediction
from .labels import Bar, Label, trailing_return

TRAINING_UP_BASE_RATE = "TRAINING_UP_BASE_RATE"
ALWAYS_UP = "ALWAYS_UP"
PREVIOUS_24H_SIGN_PERSISTENCE = "PREVIOUS_24H_SIGN_PERSISTENCE"
ZERO_RETURN_MAGNITUDE = "ZERO_RETURN_MAGNITUDE"

BASELINE_NAMES = (
    TRAINING_UP_BASE_RATE,
    ALWAYS_UP,
    PREVIOUS_24H_SIGN_PERSISTENCE,
    ZERO_RETURN_MAGNITUDE,
)

DECLARATIONS: Mapping[str, dict[str, bool]] = {
    TRAINING_UP_BASE_RATE: {"direction": True, "probability": True, "magnitude": False},
    ALWAYS_UP: {"direction": True, "probability": False, "magnitude": False},
    PREVIOUS_24H_SIGN_PERSISTENCE: {"direction": True, "probability": False, "magnitude": False},
    ZERO_RETURN_MAGNITUDE: {"direction": False, "probability": False, "magnitude": True},
}


class BaselineError(RuntimeError):
    """A baseline was asked to predict outside its frozen definition."""


@dataclass(frozen=True)
class BaseRateFit:
    """The whole of `TRAINING_UP_BASE_RATE`: one counted base rate and one declared side."""

    up_labels: int
    down_labels: int
    neutral_labels: int
    p_up: float
    direction: str
    probability: float
    tie_applied: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "training_up_labels": self.up_labels,
            "training_down_labels": self.down_labels,
            "training_neutral_labels_excluded": self.neutral_labels,
            "p_up": self.p_up,
            "declared_direction": self.direction,
            "probability": self.probability,
            "tie_rule_applied": self.tie_applied,
        }


def fit_training_up_base_rate(training: Sequence[Label]) -> BaseRateFit:
    """Fit on the fold's chronological training portion only (§5.1).

    `probability` is always P(declared direction correct), so it is `p_up` when UP is
    declared and `1 - p_up` when DOWN is declared. The tie rule is deterministic and was
    preregistered: `p_up >= 0.5` declares UP.
    """
    up = sum(1 for label in training if label.direction == UP)
    down = sum(1 for label in training if label.direction == DOWN)
    neutral = sum(1 for label in training if label.direction == NEUTRAL)
    decided = up + down
    if decided == 0:
        raise BaselineError("the training portion contains no directional label")
    p_up = up / decided
    tie = p_up == 0.5
    direction = UP if p_up >= 0.5 else DOWN
    probability = p_up if direction == UP else 1.0 - p_up
    return BaseRateFit(
        up_labels=up,
        down_labels=down,
        neutral_labels=neutral,
        p_up=p_up,
        direction=direction,
        probability=probability,
        tie_applied=tie,
    )


def training_up_base_rate_predictions(
    fit: BaseRateFit, evaluation: Sequence[Label]
) -> list[Prediction]:
    return [
        Prediction(
            open_time=label.open_time,
            direction=fit.direction,
            probability=fit.probability,
        )
        for label in evaluation
    ]


def always_up_predictions(evaluation: Sequence[Label]) -> list[Prediction]:
    """Deterministic. Declares no probability, so it is never scored for calibration."""
    return [Prediction(open_time=label.open_time, direction=UP) for label in evaluation]


def previous_24h_sign_predictions(
    evaluation: Sequence[Label],
    bars_by_open: Mapping[int, Bar],
    hours: int = HORIZON_HOURS,
) -> list[Prediction]:
    """Sign of the trailing realized 24h return, abstaining when it is unobservable.

    Uses only bars at or before the decision instant, so it is causal by construction. An
    exactly flat trailing window has no sign, so the baseline abstains rather than guessing.
    """
    predictions: list[Prediction] = []
    for label in evaluation:
        trailing = trailing_return(bars_by_open, label.open_time, hours=hours)
        if trailing is None or trailing == 0.0:
            direction = ABSTAIN
        else:
            direction = UP if trailing > 0 else DOWN
        predictions.append(Prediction(open_time=label.open_time, direction=direction))
    return predictions


def zero_return_magnitude_predictions(evaluation: Sequence[Label]) -> list[Prediction]:
    """Magnitude only. Declares no direction, so it has no win rate and no coverage."""
    return [
        Prediction(open_time=label.open_time, direction=ABSTAIN, expected_return=0.0)
        for label in evaluation
    ]


__all__ = [
    "ALWAYS_UP",
    "BASELINE_NAMES",
    "DECLARATIONS",
    "PREVIOUS_24H_SIGN_PERSISTENCE",
    "TRAINING_UP_BASE_RATE",
    "ZERO_RETURN_MAGNITUDE",
    "BaseRateFit",
    "BaselineError",
    "always_up_predictions",
    "fit_training_up_base_rate",
    "previous_24h_sign_predictions",
    "training_up_base_rate_predictions",
    "zero_return_magnitude_predictions",
]
