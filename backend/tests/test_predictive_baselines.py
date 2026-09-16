"""The four required baselines, the fold design, and Amendment A1's probability semantics."""

from __future__ import annotations

import pytest
from app.predictive import ABSTAIN, DOWN, HORIZON_HOURS, NEUTRAL, UP
from app.predictive.baselines import (
    ALWAYS_UP,
    BASELINE_NAMES,
    DECLARATIONS,
    PREVIOUS_24H_SIGN_PERSISTENCE,
    TRAINING_UP_BASE_RATE,
    ZERO_RETURN_MAGNITUDE,
    BaselineError,
    always_up_predictions,
    fit_training_up_base_rate,
    previous_24h_sign_predictions,
    training_up_base_rate_predictions,
    zero_return_magnitude_predictions,
)
from app.predictive.folds import (
    FOLD_BOUNDARIES,
    PURGE_EMBARGO_HOURS,
    assert_no_boundary_leak,
    build_folds,
    epoch,
)
from app.predictive.labels import HOUR_SECONDS, Bar, Label, index_bars

HOUR = HOUR_SECONDS


def _label(open_time: int, r_24h: float) -> Label:
    direction = UP if r_24h > 0 else DOWN if r_24h < 0 else NEUTRAL
    return Label(
        open_time=open_time,
        decision_close=100.0,
        horizon_close=100.0 * (1 + r_24h),
        r_24h=r_24h,
        direction=direction,
    )


def _training(up: int, down: int, neutral: int = 0) -> list[Label]:
    labels = []
    index = 0
    for _ in range(up):
        labels.append(_label(index * HOUR, 0.01))
        index += 1
    for _ in range(down):
        labels.append(_label(index * HOUR, -0.01))
        index += 1
    for _ in range(neutral):
        labels.append(_label(index * HOUR, 0.0))
        index += 1
    return labels


# --- Amendment A1 §5.1: probability always means P(declared direction correct) --------


def test_an_up_majority_declares_up_and_carries_p_up() -> None:
    fit = fit_training_up_base_rate(_training(up=60, down=40))
    assert fit.p_up == pytest.approx(0.6)
    assert fit.direction == UP
    assert fit.probability == pytest.approx(0.6)
    assert fit.tie_applied is False


def test_a_down_majority_declares_down_and_carries_one_minus_p_up() -> None:
    """The defect Amendment A1 fixes: the probability must not stay at p_up here."""
    fit = fit_training_up_base_rate(_training(up=45, down=55))
    assert fit.p_up == pytest.approx(0.45)
    assert fit.direction == DOWN
    assert fit.probability == pytest.approx(0.55)
    assert fit.probability != pytest.approx(fit.p_up)


@pytest.mark.parametrize(("up", "down"), [(60, 40), (45, 55), (99, 1), (1, 99), (50, 50)])
def test_the_declared_probability_is_never_below_one_half(up: int, down: int) -> None:
    fit = fit_training_up_base_rate(_training(up=up, down=down))
    assert fit.probability >= 0.5
    expected = fit.p_up if fit.direction == UP else 1 - fit.p_up
    assert fit.probability == pytest.approx(expected)


def test_the_tie_rule_is_deterministic_and_declares_up() -> None:
    fit = fit_training_up_base_rate(_training(up=50, down=50))
    assert fit.p_up == 0.5
    assert fit.direction == UP
    assert fit.probability == 0.5
    assert fit.tie_applied is True


def test_neutral_training_labels_are_excluded_from_p_up_and_counted() -> None:
    fit = fit_training_up_base_rate(_training(up=30, down=20, neutral=7))
    assert fit.p_up == pytest.approx(0.6), "neutral labels must not enter the denominator"
    assert fit.neutral_labels == 7
    record = fit.as_record()
    assert record["training_neutral_labels_excluded"] == 7
    assert record["training_up_labels"] == 30 and record["training_down_labels"] == 20


def test_a_training_portion_with_no_direction_is_refused_rather_than_guessed() -> None:
    with pytest.raises(BaselineError, match="no directional label"):
        fit_training_up_base_rate(_training(up=0, down=0, neutral=5))


def test_the_base_rate_prediction_is_constant_across_the_evaluation_fold() -> None:
    fit = fit_training_up_base_rate(_training(up=70, down=30))
    evaluation = [_label(index * HOUR, 0.01) for index in range(5)]
    predictions = training_up_base_rate_predictions(fit, evaluation)
    assert {p.direction for p in predictions} == {UP}
    assert {p.probability for p in predictions} == {0.7}
    assert [p.open_time for p in predictions] == [label.open_time for label in evaluation]


# --- Amendment A1 §5.2 and §5.3: declared quantities ----------------------------------


def test_the_declared_quantities_are_exactly_the_contract_ones() -> None:
    assert set(BASELINE_NAMES) == {
        TRAINING_UP_BASE_RATE,
        ALWAYS_UP,
        PREVIOUS_24H_SIGN_PERSISTENCE,
        ZERO_RETURN_MAGNITUDE,
    }
    assert DECLARATIONS[TRAINING_UP_BASE_RATE] == {
        "direction": True,
        "probability": True,
        "magnitude": False,
    }
    for name in (ALWAYS_UP, PREVIOUS_24H_SIGN_PERSISTENCE):
        assert DECLARATIONS[name] == {
            "direction": True,
            "probability": False,
            "magnitude": False,
        }
    assert DECLARATIONS[ZERO_RETURN_MAGNITUDE] == {
        "direction": False,
        "probability": False,
        "magnitude": True,
    }


def test_deterministic_directional_baselines_declare_no_probability() -> None:
    evaluation = [_label(index * HOUR, 0.01) for index in range(3)]
    for prediction in always_up_predictions(evaluation):
        assert prediction.direction == UP
        assert prediction.probability is None
        assert prediction.expected_return is None


def test_the_magnitude_baseline_declares_no_direction() -> None:
    evaluation = [_label(index * HOUR, 0.01) for index in range(3)]
    for prediction in zero_return_magnitude_predictions(evaluation):
        assert prediction.direction == ABSTAIN
        assert prediction.probability is None
        assert prediction.expected_return == 0.0


# --- persistence baseline --------------------------------------------------------------


def _bars(closes: list[float]) -> dict[int, Bar]:
    return index_bars(
        Bar(open_time=index * HOUR, close=close, complete=True)
        for index, close in enumerate(closes)
    )


def test_persistence_declares_the_sign_of_the_trailing_window() -> None:
    closes = [100.0] * (HORIZON_HOURS + 1)
    closes[HORIZON_HOURS] = 110.0
    bars = _bars(closes)
    evaluation = [_label(HORIZON_HOURS * HOUR, 0.01)]
    assert previous_24h_sign_predictions(evaluation, bars)[0].direction == UP
    closes[HORIZON_HOURS] = 90.0
    assert previous_24h_sign_predictions(evaluation, _bars(closes))[0].direction == DOWN


def test_persistence_abstains_when_the_trailing_window_is_unobservable() -> None:
    bars = _bars([100.0] * (HORIZON_HOURS + 1))
    evaluation = [_label(0, 0.01)]
    assert previous_24h_sign_predictions(evaluation, bars)[0].direction == ABSTAIN


def test_persistence_abstains_on_an_exactly_flat_trailing_window() -> None:
    bars = _bars([100.0] * (HORIZON_HOURS + 1))
    evaluation = [_label(HORIZON_HOURS * HOUR, 0.01)]
    assert previous_24h_sign_predictions(evaluation, bars)[0].direction == ABSTAIN


def test_persistence_never_reads_a_bar_after_the_decision_instant() -> None:
    closes = [100.0] * (2 * HORIZON_HOURS + 1)
    closes[HORIZON_HOURS] = 110.0
    instant = HORIZON_HOURS * HOUR
    evaluation = [_label(instant, 0.01)]
    honest = previous_24h_sign_predictions(evaluation, _bars(closes))[0].direction
    future = list(closes)
    for index in range(HORIZON_HOURS + 1, len(future)):
        future[index] = 1.0
    assert previous_24h_sign_predictions(evaluation, _bars(future))[0].direction == honest


# --- folds -------------------------------------------------------------------------------


def _hourly_labels(start: str, end: str) -> list[Label]:
    first, last = epoch(start), epoch(end)
    return [_label(instant, 0.01) for instant in range(first, last, HOUR)]


def test_training_and_evaluation_never_share_a_label_window() -> None:
    labels = _hourly_labels("2018-11-01T00:00:00Z", "2019-03-01T00:00:00Z")
    fold_set = build_folds(labels)
    assert_no_boundary_leak(fold_set)
    fold = fold_set.folds[0]
    horizon = HORIZON_HOURS * HOUR
    embargo = PURGE_EMBARGO_HOURS * HOUR
    assert fold.training, "the 2019 fold must have a training portion"
    assert max(label.open_time for label in fold.training) + horizon + embargo <= fold.start
    assert min(label.open_time for label in fold.evaluation) >= fold.start


def test_every_evaluation_label_closes_before_its_fold_ends() -> None:
    labels = _hourly_labels("2018-12-01T00:00:00Z", "2020-02-01T00:00:00Z")
    fold_set = build_folds(labels)
    horizon = HORIZON_HOURS * HOUR
    for fold in fold_set.folds:
        for label in fold.evaluation:
            assert label.open_time + horizon <= fold.end


def test_the_fold_assignment_covers_every_admissible_label_exactly_once() -> None:
    labels = _hourly_labels("2018-12-25T00:00:00Z", "2019-01-10T00:00:00Z")
    fold_set = build_folds(labels)
    assigned = [label for fold in fold_set.folds for label in fold.evaluation]
    assert len(assigned) == len({label.open_time for label in assigned})
    assert len(assigned) + sum(fold_set.unassigned.values()) == len(labels)


def test_labels_before_the_first_fold_are_warmup_training_not_evaluated() -> None:
    labels = _hourly_labels("2018-12-01T00:00:00Z", "2018-12-10T00:00:00Z")
    fold_set = build_folds(labels)
    assert fold_set.eligible_total() == 0
    assert fold_set.unassigned["WARMUP_TRAINING_BLOCK"] == len(labels)


def test_the_fold_boundaries_are_the_frozen_calendar_years() -> None:
    assert [name for name, _, _ in FOLD_BOUNDARIES] == [
        "2019",
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
    ]
    assert PURGE_EMBARGO_HOURS == HORIZON_HOURS == 24


def test_a_boundary_leak_is_detected_rather_than_tolerated() -> None:
    labels = _hourly_labels("2018-12-01T00:00:00Z", "2019-02-01T00:00:00Z")
    fold_set = build_folds(labels)
    leaked = fold_set.folds[0]
    poisoned = type(fold_set)(
        folds=(
            type(leaked)(
                name=leaked.name,
                start=leaked.start,
                end=leaked.end,
                training=leaked.training + (_label(leaked.start, 0.01),),
                evaluation=leaked.evaluation,
            ),
        ),
        horizon_hours=fold_set.horizon_hours,
        purge_embargo_hours=fold_set.purge_embargo_hours,
        unassigned=fold_set.unassigned,
    )
    with pytest.raises(ValueError, match="reaches into the fold"):
        assert_no_boundary_leak(poisoned)
