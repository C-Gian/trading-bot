"""G2-01 model fitting and predictive-distribution acceptance tests (contract s.5-10, 16)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from app.g2.contract import COLUMNS, MIN_RESIDUALS, MIN_TRAINING_ROWS, PENALTIES, SYSTEM_VERSION
from app.g2.distribution import (
    FALLBACK,
    PREQUENTIAL,
    ResidualArchive,
    VersionMixError,
    direction,
    distribution,
    quantiles,
    strength_label,
)
from app.g2.models import (
    Scaler,
    SupportError,
    TrainingSet,
    check_support,
    first_of_month,
    fit_readout,
    fit_scaler,
    ridge,
    select_training,
)
from app.g2.records import FitManifest, Prediction, PredictionOutcome
from g2_support import full_run

BOUNDARY = datetime(2002, 3, 1, tzinfo=UTC)


def grid(rows: int, start: datetime, step: timedelta = timedelta(minutes=15)) -> np.ndarray:
    base = np.datetime64(start.replace(tzinfo=None), "m")
    return base + np.arange(rows) * np.timedelta64(int(step.total_seconds() // 60), "m")


def test_training_uses_only_labels_mature_at_the_boundary_and_the_730_day_window():
    times = grid(4, BOUNDARY - timedelta(days=800), timedelta(days=200))
    times = np.append(times, np.datetime64((BOUNDARY - timedelta(hours=2)).replace(tzinfo=None)))
    labels = times + np.timedelta64(240, "m")
    x = np.ones((5, 8))
    y = np.arange(5, dtype=float)
    selected = select_training(times, x, y, labels, BOUNDARY)
    # row 0 is older than 730 days; the last row's 4h label matures after the boundary
    assert list(selected.y) == [1.0, 2.0, 3.0]
    assert (selected.label_times <= np.datetime64(BOUNDARY.replace(tzinfo=None))).all()


def test_unmatured_or_missing_labels_are_excluded():
    times = grid(3, BOUNDARY - timedelta(days=5))
    labels = times + np.timedelta64(240, "m")
    y = np.array([1.0, np.nan, 3.0])
    x = np.ones((3, 8))
    x[2, 4] = np.nan
    assert list(select_training(times, x, y, labels, BOUNDARY).y) == [1.0]


def test_support_gate_is_exact():
    def training(rows: int, span_days: float) -> TrainingSet:
        start = BOUNDARY - timedelta(days=span_days) - timedelta(days=1)
        step = timedelta(days=span_days) / (rows - 1)
        times = np.array(
            [np.datetime64((start + k * step).replace(tzinfo=None), "m") for k in range(rows)]
        )
        return TrainingSet(times, np.ones((rows, 8)), np.ones(rows), times)

    check_support(training(MIN_TRAINING_ROWS, 180))
    with pytest.raises(SupportError):
        check_support(training(MIN_TRAINING_ROWS - 1, 200))
    with pytest.raises(SupportError):
        check_support(training(MIN_TRAINING_ROWS, 179.99))


def test_train_only_robust_scaling_constant_column_and_clip():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, (500, 8))
    x[:, 3] = 7.0  # constant in training
    scaler = fit_scaler(x)
    assert scaler.scales[3] is None and scaler.constant == (COLUMNS[3],)
    j = 0
    center = float(np.median(x[:, j]))
    assert scaler.centers[j] == center
    assert scaler.scales[j] == pytest.approx(1.4826 * float(np.median(np.abs(x[:, j] - center))))
    row = np.array([[1e9, 0, 0, 123.0, 0, 0, 0, 0]])
    scaled = scaler.transform(row)[0]
    assert scaled[0] == 8.0 and scaled[3] == 0.0
    # scaling is a pure function of the training rows: later data cannot mutate it
    frozen = dataclasses.astuple(scaler)
    scaler.transform(rng.normal(0, 50, (100, 8)))
    assert dataclasses.astuple(scaler) == frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        scaler.centers = ()  # type: ignore[misc]


def test_fixed_ridge_penalty_identity_against_augmented_least_squares():
    rng = np.random.default_rng(7)
    n = 400
    xs = rng.normal(0, 1, (n, 8))
    y = xs @ np.linspace(-0.5, 0.5, 8) + 0.3 + rng.normal(0, 0.2, n)
    intercept, beta = ridge(xs, y, PENALTIES)
    # mean((y - b0 - Xb)^2) + sum(l_j b_j^2)  <=>  ||[y; 0] - [1 X; 0 sqrt(n l)] [b0; b]||^2 / n
    design = np.vstack(
        [
            np.column_stack([np.ones(n), xs]),
            np.column_stack([np.zeros(8), np.diag(np.sqrt(n * np.array(PENALTIES)))]),
        ]
    )
    target = np.concatenate([y, np.zeros(8)])
    reference = np.linalg.lstsq(design, target, rcond=None)[0]
    assert intercept == pytest.approx(reference[0], abs=1e-10)
    assert beta == pytest.approx(reference[1:], abs=1e-10)
    assert PENALTIES == (0.25,) * 6 + (1.0, 1.0)


def test_constant_training_feature_coefficient_is_fixed_to_zero():
    rng = np.random.default_rng(3)
    x = rng.normal(0, 1, (12_000, 8))
    x[:, 5] = 2.0
    times = grid(12_000, BOUNDARY - timedelta(days=300), timedelta(minutes=30))
    training = TrainingSet(times, x, x[:, 0] * 0.5 + rng.normal(0, 1, 12_000), times)
    readout = fit_readout(training, fit_scaler(x))
    assert readout.coefficients[5] == 0.0
    scaled, contributions, _ = readout.terms(np.array([0, 0, 0, 0, 0, 99.0, 0, 0]))
    assert scaled[5] == 0.0 and contributions[5] == 0.0


def test_monthly_boundary_predicate_and_fitted_boundaries_are_exact():
    assert first_of_month(datetime(2001, 8, 1, tzinfo=UTC))
    assert not first_of_month(datetime(2001, 8, 1, 0, 15, tzinfo=UTC))
    assert not first_of_month(datetime(2001, 8, 2, tzinfo=UTC))
    fits = full_run().core.store.of_type(FitManifest)
    assert fits and all(f.fit_boundary.day == 1 and f.fit_boundary.hour == 0 for f in fits)
    assert all(f.fit_boundary.minute == 0 for f in fits)
    fitted = [f for f in fits if f.status == "FITTED"]
    assert fitted, "the synthetic path must reach full model support"
    for fit in fitted:
        assert fit.rows >= MIN_TRAINING_ROWS
        assert fit.latest_label_time is not None and fit.latest_label_time <= fit.fit_boundary
        assert fit.training_start is not None and fit.training_end is not None
        assert fit.training_end - fit.training_start >= timedelta(days=180)
    unfitted = [f for f in fits if f.status != "FITTED" and f.head == "FORECAST"]
    assert all(
        ("< 10000" in f.support_detail) or ("180 days" in f.support_detail) for f in unfitted
    )


def test_predictions_reuse_the_frozen_fit_manifest_without_mutation():
    store = full_run().core.store
    fits = {f.fit_id: f for f in store.of_type(FitManifest)}
    for prediction in store.of_type(Prediction):
        if prediction.fit_id is None or prediction.mu_z is None:
            continue
        fit = fits[prediction.fit_id]
        assert fit.fit_boundary <= prediction.decision_time
        # the latest fit boundary before the decision is the active one
        assert prediction.decision_time - fit.fit_boundary < timedelta(days=32)
        contributions = [c for c in prediction.contributions if c is not None]
        assert len(contributions) == 8
        for scaled, coefficient, contribution in zip(
            prediction.scaled_terms, fit.coefficients, prediction.contributions, strict=True
        ):
            assert contribution == pytest.approx(scaled * coefficient, abs=1e-12)  # type: ignore[operator]
        assert prediction.mu_z == pytest.approx(
            fit.intercept + sum(contributions),
            abs=1e-12,  # type: ignore[operator]
        )


# ---------------------------------------------------------------- distribution


def test_exact_quantiles_mean_and_strict_p_positive():
    residuals = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    dist = distribution(0.0, 0.5, residuals, FALLBACK)
    returns = residuals * 0.5
    assert (dist.q10, dist.q50, dist.q90) == tuple(np.quantile(returns, [0.1, 0.5, 0.9]))
    assert dist.q10 == pytest.approx(-0.8) and dist.q90 == pytest.approx(0.8)
    assert dist.median_return == dist.q50 == 0.0 and dist.mean_return == 0.0
    assert dist.p_positive == 2 / 5  # the atom exactly at zero is neither positive nor negative
    shifted = distribution(1.0, 2.0, residuals, PREQUENTIAL)
    assert shifted.p_positive == 3 / 5 and shifted.median_return == 2.0  # atoms -2,0,2,4,6
    assert quantiles(np.array([1.0, 2.0])) == (1.1, 1.5, 1.9)


def test_direction_and_display_only_strength_labels():
    assert direction(1e-11) == "UP" and direction(-1e-11) == "DOWN"
    assert direction(5e-13) == "NEUTRAL" and direction(0.0) == "NEUTRAL"
    assert strength_label(0.2499) == "WEAK" and strength_label(0.25) == "MODERATE"
    assert strength_label(0.7499) == "MODERATE" and strength_label(0.75) == "STRONG"


def test_residual_archive_thresholds_window_and_version_isolation():
    archive = ResidualArchive(SYSTEM_VERSION)
    start = datetime(2001, 1, 1, tzinfo=UTC)
    for k in range(MIN_RESIDUALS):
        t = start + k * timedelta(minutes=15)
        archive.append(t, t + timedelta(hours=4), 0.1, SYSTEM_VERSION)
    ready, count, span = archive.status(start + timedelta(days=40))
    assert count == MIN_RESIDUALS and span is not None and span < 30 and not ready
    t = start + timedelta(days=31)
    archive.append(t, t + timedelta(hours=4), 0.2, SYSTEM_VERSION)
    assert archive.status(t + timedelta(hours=4))[0] is True
    assert archive.status(t + timedelta(hours=3))[0] is False  # not yet matured
    later = start + timedelta(days=760)
    assert archive.status(later)[1] == 1  # 730-day trailing age limit
    with pytest.raises(VersionMixError):
        archive.append(later, later, 0.0, "G2-V1")


def test_fallback_then_prequential_status_in_the_synthetic_run():
    store = full_run().core.store
    statuses = [p.calibration_status for p in store.of_type(Prediction) if p.fit_id is not None]
    first_prequential = statuses.index(PREQUENTIAL)
    assert first_prequential > 0
    assert set(statuses[:first_prequential]) == {FALLBACK}
    for prediction in store.of_type(Prediction):
        if prediction.p_positive is not None:
            assert prediction.calibration_status in (PREQUENTIAL, FALLBACK)
            assert prediction.calibration_status in prediction.reason_codes
            assert 0.0 <= prediction.p_positive <= 1.0
        else:
            assert prediction.calibration_status == "UNAVAILABLE"
            assert prediction.q10 is None and prediction.direction == "UNAVAILABLE"


def test_prequential_archive_holds_only_genuinely_issued_matured_residuals():
    run = full_run()
    store = run.core.store
    predictions = {p.prediction_id: p for p in store.of_type(Prediction)}
    archived = [o for o in store.of_type(PredictionOutcome) if o.residual_archived]
    assert len(archived) == len(run.core.archives["FORECAST"])
    for outcome in archived:
        prediction = predictions[outcome.prediction_id]
        assert prediction.mu_z is not None and prediction.fit_id is not None
        assert outcome.available_at == prediction.decision_time + timedelta(hours=4)
        assert outcome.residual_z == pytest.approx(outcome.realized_z - prediction.mu_z)  # type: ignore[operator]
    unissued = [
        o for o in store.of_type(PredictionOutcome) if predictions[o.prediction_id].mu_z is None
    ]
    assert unissued and not any(o.residual_archived for o in unissued)


def test_scaler_dataclass_is_frozen():
    assert dataclasses.is_dataclass(Scaler)
    assert Scaler.__dataclass_params__.frozen  # type: ignore[attr-defined]
