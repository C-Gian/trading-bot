"""The frozen scorer for `PREDICTIVE_EVALUATION_CONTRACT_V1` (Amendment A1).

Win rate, coverage, sample accounting, calibration, magnitude error, the signed
magnitude-match diagnostic, and a dependence-aware moving-block bootstrap interval.

A metric is computed exactly when the quantity it scores is declared. A predictor that
declares no probability receives no Brier score and no reliability table; a predictor that
declares no magnitude receives no MAE. Nothing is imputed to fill a required field.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from . import ABSTAIN, DOWN, NEUTRAL, UP

MAGNITUDE_EPSILON = 1e-4
MAGNITUDE_RANGE = (-100.0, 100.0)
RELIABILITY_BIN_EDGES = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)

BLOCK_LENGTH_HOURS = 48
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260916
BOOTSTRAP_ALPHA = 0.05
_BOOTSTRAP_CHUNK = 500

PROBABILITY_NOT_DECLARED = "PROBABILITY_NOT_DECLARED"
MAGNITUDE_NOT_DECLARED = "MAGNITUDE_NOT_DECLARED"
DIRECTION_NOT_DECLARED = "DIRECTION_NOT_DECLARED"

NEAR_ZERO_BOTH = "NEAR_ZERO_BOTH"
NEUTRAL_REALIZED = "NEUTRAL_REALIZED"
ABSTAINED_MAGNITUDE = "ABSTAINED_MAGNITUDE"
MAGNITUDE_EXCLUSIONS = (NEAR_ZERO_BOTH, NEUTRAL_REALIZED, ABSTAINED_MAGNITUDE)

# 95% two-sided normal quantile; the frozen protocol fixes alpha at 0.05.
_Z_95 = 1.959963984540054


class EvaluationError(RuntimeError):
    """The scorer was asked for a metric the predictor never declared."""


@dataclass(frozen=True)
class Prediction:
    """One prediction at one eligible decision instant.

    `direction` is UP, DOWN or NEUTRAL_UNCERTAIN (an abstention). `probability` is
    P(declared direction correct) and is None for a deterministic predictor.
    `expected_return` is the signed 24h log return and is None for a directional predictor.
    """

    open_time: int
    direction: str
    probability: float | None = None
    expected_return: float | None = None


@dataclass(frozen=True)
class Outcome:
    """The realized truth at one eligible decision instant."""

    open_time: int
    r_24h: float
    direction: str


def magnitude_match(predicted: float, actual: float, epsilon: float = MAGNITUDE_EPSILON) -> float:
    """Signed magnitude-match diagnostic, bounded, symmetric, floored at `epsilon`."""
    low, high = sorted((max(abs(predicted), epsilon), max(abs(actual), epsilon)))
    agreement = 1.0 if (predicted > 0) == (actual > 0) else -1.0
    return 100.0 * agreement * low / high


def magnitude_match_class(
    predicted: float, actual: float, epsilon: float = MAGNITUDE_EPSILON
) -> str | None:
    """Which deterministic exclusion rule owns this record, or None when it is scored.

    The order is the frozen one: near-zero pair, then neutral truth, then an abstaining
    magnitude. A record is owned by the first rule that fires.
    """
    if abs(predicted) < epsilon and abs(actual) < epsilon:
        return NEAR_ZERO_BOTH
    if actual == 0.0:
        return NEUTRAL_REALIZED
    if abs(predicted) < epsilon:
        return ABSTAINED_MAGNITUDE
    return None


def wilson_interval(successes: int, trials: int, alpha: float = BOOTSTRAP_ALPHA) -> list[float]:
    """Optimistic independence-assuming reference only. Never the headline interval."""
    if abs(alpha - 0.05) > 1e-12:
        raise EvaluationError("the frozen protocol fixes the Wilson reference at alpha 0.05")
    if trials <= 0:
        return [float("nan"), float("nan")]
    proportion = successes / trials
    denominator = 1 + _Z_95 * _Z_95 / trials
    centre = (proportion + _Z_95 * _Z_95 / (2 * trials)) / denominator
    spread = (
        _Z_95
        * math.sqrt(proportion * (1 - proportion) / trials + _Z_95 * _Z_95 / (4 * trials * trials))
        / denominator
    )
    return [max(0.0, centre - spread), min(1.0, centre + spread)]


def moving_block_bootstrap(
    correct: Sequence[bool],
    block_length: int = BLOCK_LENGTH_HOURS,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
    alpha: float = BOOTSTRAP_ALPHA,
) -> list[float]:
    """Dependence-aware interval for a win rate over overlapping, hourly-sampled labels.

    Blocks are contiguous in the chronologically ordered sequence, so the overlap structure
    of 24h labels sampled every hour survives resampling instead of being destroyed by an
    independence assumption.
    """
    import numpy as np

    total = len(correct)
    if total == 0:
        return [float("nan"), float("nan")]
    if block_length <= 0:
        raise EvaluationError("the bootstrap block length must be strictly positive")
    values = np.asarray(correct, dtype=np.float64)
    span = min(block_length, total)
    starts_available = total - span + 1
    draws = math.ceil(total / span)
    offsets = np.arange(span)
    generator = np.random.default_rng(seed)
    means = np.empty(replicates, dtype=np.float64)
    done = 0
    while done < replicates:
        size = min(_BOOTSTRAP_CHUNK, replicates - done)
        starts = generator.integers(0, starts_available, size=(size, draws))
        index = (starts[:, :, None] + offsets[None, None, :]).reshape(size, draws * span)
        means[done : done + size] = values[index[:, :total]].mean(axis=1)
        done += size
    lower, upper = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return [float(lower), float(upper)]


def reliability_table(
    probabilities: Sequence[float], correct: Sequence[bool]
) -> list[dict[str, Any]]:
    """Fixed predeclared bins. Never merged, never re-cut, and empty bins are reported."""
    pairs = list(zip(probabilities, correct, strict=True))
    rows: list[dict[str, Any]] = []
    bins = len(RELIABILITY_BIN_EDGES) - 1
    for index in range(bins):
        low, high = RELIABILITY_BIN_EDGES[index], RELIABILITY_BIN_EDGES[index + 1]
        last = index == bins - 1
        members = [
            (value, hit) for value, hit in pairs if low <= value <= high if last or value < high
        ]
        count = len(members)
        rows.append(
            {
                "bin": f"[{low:.1f},{high:.1f}{']' if last else ')'}",
                "count": count,
                "mean_predicted_probability": (
                    sum(value for value, _ in members) / count if count else None
                ),
                "empirical_frequency_correct": (
                    sum(1 for _, hit in members if hit) / count if count else None
                ),
            }
        )
    return rows


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    size = len(ordered)
    middle = size // 2
    if size % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _directional_report(
    actionable: Sequence[tuple[Prediction, Outcome]],
    correct: Sequence[bool],
    eligible: int,
    declared_side_neutral_truth: int,
    abstentions: int,
    block_length: int,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    hits = sum(correct)
    return {
        "actionable_directional_predictions": len(actionable),
        "declared_side_on_neutral_truth": declared_side_neutral_truth,
        "abstentions": abstentions,
        "correct_directional_predictions": hits,
        "win_rate": (hits / len(actionable)) if actionable else None,
        "coverage": (len(actionable) / eligible) if eligible else None,
        "win_rate_interval_method": "MOVING_BLOCK_BOOTSTRAP",
        "win_rate_interval_block_length_hours": block_length,
        "win_rate_interval_moving_block": moving_block_bootstrap(
            correct, block_length=block_length, replicates=replicates, seed=seed
        ),
        "win_rate_interval_naive_wilson_optimistic_reference": wilson_interval(
            hits, len(actionable)
        ),
    }


def score(
    predictions: Sequence[Prediction],
    outcomes: Sequence[Outcome],
    *,
    declares_direction: bool,
    declares_probability: bool,
    declares_magnitude: bool,
    block_length: int = BLOCK_LENGTH_HOURS,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Score one predictor over one eligible universe under the frozen contract."""
    if declares_probability and not declares_direction:
        raise EvaluationError("a probability without a declared direction has no meaning")
    truth = {item.open_time: item for item in outcomes}
    if len(truth) != len(outcomes):
        raise EvaluationError("the eligible universe contains duplicate decision instants")
    ordered = sorted(predictions, key=lambda item: item.open_time)
    if {item.open_time for item in ordered} != set(truth):
        raise EvaluationError("predictions and the eligible universe are not the same set")

    eligible = len(truth)
    neutral_truths = sum(1 for item in truth.values() if item.direction == NEUTRAL)
    actionable: list[tuple[Prediction, Outcome]] = []
    declared_side_neutral_truth = 0
    abstentions = 0
    for prediction in ordered:
        outcome = truth[prediction.open_time]
        if not declares_direction:
            continue
        if prediction.direction not in {UP, DOWN}:
            if prediction.direction != ABSTAIN:
                raise EvaluationError(f"unknown declared direction: {prediction.direction}")
            abstentions += 1
            continue
        if outcome.direction == NEUTRAL:
            declared_side_neutral_truth += 1
            continue
        actionable.append((prediction, outcome))

    correct = [prediction.direction == outcome.direction for prediction, outcome in actionable]
    report: dict[str, Any] = {
        "eligible_decision_timestamps": eligible,
        "neutral_truths": neutral_truths,
        "declares_direction": declares_direction,
        "declares_probability": declares_probability,
        "declares_magnitude": declares_magnitude,
    }

    if declares_direction:
        report.update(
            _directional_report(
                actionable,
                correct,
                eligible,
                declared_side_neutral_truth,
                abstentions,
                block_length,
                replicates,
                seed,
            )
        )
        bucket_total = len(actionable) + declared_side_neutral_truth + abstentions
        if bucket_total != eligible:
            raise EvaluationError("directional sample accounting does not close")
    else:
        report.update(
            {
                "direction_flag": DIRECTION_NOT_DECLARED,
                "actionable_directional_predictions": None,
                "win_rate": None,
                "coverage": None,
            }
        )

    if declares_probability:
        values = [prediction.probability for prediction, _ in actionable]
        if any(value is None for value in values):
            raise EvaluationError("a probabilistic predictor omitted a probability")
        declared = [float(value) for value in values if value is not None]
        if any(not 0.0 <= value <= 1.0 for value in declared):
            raise EvaluationError("a declared probability is outside [0, 1]")
        report["brier_score"] = (
            sum(
                (value - (1.0 if hit else 0.0)) ** 2
                for value, hit in zip(declared, correct, strict=True)
            )
            / len(declared)
            if declared
            else None
        )
        report["reliability_table"] = reliability_table(declared, correct)
    else:
        report["probability_flag"] = PROBABILITY_NOT_DECLARED
        report["brier_score"] = None
        report["reliability_table"] = None

    if declares_magnitude:
        pairs = [
            (prediction.expected_return, truth[prediction.open_time].r_24h)
            for prediction in ordered
            if prediction.expected_return is not None
        ]
        if len(pairs) != eligible:
            raise EvaluationError("a magnitude predictor omitted a magnitude")
        errors = [abs(float(predicted) - actual) for predicted, actual in pairs]
        excluded = dict.fromkeys(MAGNITUDE_EXCLUSIONS, 0)
        scored: list[float] = []
        for predicted, actual in pairs:
            reason = magnitude_match_class(float(predicted), actual)
            if reason is not None:
                excluded[reason] += 1
                continue
            scored.append(magnitude_match(float(predicted), actual))
        report.update(
            {
                "magnitude_mae_percentage_points": sum(errors) / len(errors) * 100,
                "magnitude_mae_basis_points": sum(errors) / len(errors) * 10_000,
                "magnitude_median_absolute_error_percentage_points": _median(errors) * 100,
                "magnitude_match_included": len(scored),
                "magnitude_match_mean": (sum(scored) / len(scored)) if scored else None,
                "magnitude_match_exclusions": excluded,
            }
        )
    else:
        report.update(
            {
                "magnitude_flag": MAGNITUDE_NOT_DECLARED,
                "magnitude_mae_percentage_points": None,
                "magnitude_match_mean": None,
            }
        )

    return report


__all__ = [
    "ABSTAINED_MAGNITUDE",
    "BLOCK_LENGTH_HOURS",
    "BOOTSTRAP_ALPHA",
    "BOOTSTRAP_REPLICATES",
    "BOOTSTRAP_SEED",
    "DIRECTION_NOT_DECLARED",
    "MAGNITUDE_EPSILON",
    "MAGNITUDE_EXCLUSIONS",
    "MAGNITUDE_NOT_DECLARED",
    "MAGNITUDE_RANGE",
    "NEAR_ZERO_BOTH",
    "NEUTRAL_REALIZED",
    "PROBABILITY_NOT_DECLARED",
    "RELIABILITY_BIN_EDGES",
    "EvaluationError",
    "Outcome",
    "Prediction",
    "magnitude_match",
    "magnitude_match_class",
    "moving_block_bootstrap",
    "reliability_table",
    "score",
    "wilson_interval",
]
