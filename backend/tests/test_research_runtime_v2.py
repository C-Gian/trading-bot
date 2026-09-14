"""Behavioral and equivalence tests for the prospective batch research runtime."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from app.research.runtime_v2 import (
    HOUR_US,
    PREDICTION_TOLERANCE,
    RUNTIME_VERSION,
    TIMED_STAGES,
    FoldPredictionInput,
    RuntimeV2Error,
    StageTimer,
    build_profile_prediction_views,
    predict_folds,
    predict_ordered,
    validate_stage_timing_record,
)
from app.research.wp014_model import HGBR_PARAMETERS
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[2]


class CountingPredictor:
    def __init__(self) -> None:
        self.calls = 0

    def predict(self, matrix: np.ndarray) -> np.ndarray:
        self.calls += 1
        return matrix[:, 0] * 0.5 - matrix[:, 1]


def _clock(values: list[float]):
    instants: Iterator[float] = iter(values)
    return lambda: next(instants)


def test_batch_prediction_preserves_governed_row_order_and_uses_one_call() -> None:
    model = CountingPredictor()
    signals = (HOUR_US, 2 * HOUR_US, 3 * HOUR_US)
    matrix = np.asarray([[2.0, 0.1], [4.0, 0.5], [8.0, 1.0]], dtype=np.float32)
    result = predict_ordered(model, signals, matrix)
    assert model.calls == 1
    assert result.runtime_version == RUNTIME_VERSION
    assert result.signal_ids == signals
    assert result.values == pytest.approx((0.9, 1.5, 3.0))
    assert list(result.as_mapping()) == list(signals)


def test_bounded_batches_are_deterministic_and_reject_unsafe_inputs() -> None:
    model = CountingPredictor()
    signals = tuple(range(1, 8))
    matrix = np.column_stack((np.arange(7, dtype=float), np.zeros(7)))
    result = predict_ordered(model, signals, matrix, batch_rows=3)
    assert model.calls == 3 and result.values[-1] == 3.0
    with pytest.raises(RuntimeV2Error, match="strictly increasing"):
        predict_ordered(model, (2, 1), matrix[:2])
    with pytest.raises(RuntimeV2Error, match="do not align"):
        predict_ordered(model, signals, matrix[:2])
    unsafe = matrix.copy()
    unsafe[0, 0] = np.nan
    with pytest.raises(RuntimeV2Error, match="non-finite"):
        predict_ordered(model, signals, unsafe)


def test_fold_orchestration_uses_one_batch_per_fold_and_preserves_global_order() -> None:
    first = CountingPredictor()
    second = CountingPredictor()
    predictions = predict_folds(
        (
            FoldPredictionInput("DEV-2020", first, (1, 2), np.asarray([[2.0, 1.0], [4.0, 1.0]])),
            FoldPredictionInput("DEV-2021", second, (3, 4), np.asarray([[6.0, 1.0], [8.0, 1.0]])),
        )
    )
    assert first.calls == second.calls == 1
    assert predictions.signal_ids == (1, 2, 3, 4)
    assert predictions.values == (0.0, 1.0, 2.0, 3.0)


def test_fixed_seed_hgbr_rowwise_and_batch_predictions_are_exactly_equivalent() -> None:
    rng = np.random.default_rng(20260914)
    training = rng.normal(size=(1200, 8))
    labels = training[:, 0] * 0.2 - training[:, 3] * 0.1 + np.sin(training[:, 5]) * 0.05
    validation = rng.normal(size=(1500, 8))
    model = HistGradientBoostingRegressor(**HGBR_PARAMETERS).fit(training, labels)
    rowwise = np.asarray([model.predict(row[None, :])[0] for row in validation])
    batched = predict_ordered(model, tuple(range(len(validation))), validation)
    difference = np.max(np.abs(rowwise - np.asarray(batched.values)))
    assert difference <= PREDICTION_TOLERANCE
    assert tuple(rowwise > 0.0) == batched.positive_decisions()


def test_threshold_is_strictly_positive_and_profile_reuse_and_delay_are_explicit() -> None:
    predictions = predict_ordered(
        CountingPredictor(),
        (0, HOUR_US, 2 * HOUR_US, 3 * HOUR_US),
        np.asarray([[0, 0], [2, 1], [0, 0], [4, 1]], dtype=float),
    )
    assert predictions.values == (0.0, 0.0, 0.0, 1.0)
    assert predictions.positive_decisions() == (False, False, False, True)
    views = build_profile_prediction_views(predictions, (HOUR_US, 2 * HOUR_US, 3 * HOUR_US))
    assert views["DEFAULT"] is views["ZERO"] is views["DOUBLE"]
    assert views["DELAY_1H"].signal_ids == (HOUR_US, 2 * HOUR_US, 3 * HOUR_US)
    assert views["DELAY_1H"].prediction_signal_ids == (0, HOUR_US, 2 * HOUR_US)
    assert views["DELAY_1H"].values == predictions.values[:3]


def test_identical_predictions_produce_identical_signals_trades_and_metrics() -> None:
    model = CountingPredictor()
    signals = tuple(range(1, 101))
    matrix = np.column_stack((np.linspace(-2, 2, 100), np.full(100, 0.1)))
    rowwise_values = tuple(float(model.predict(row[None, :])[0]) for row in matrix)
    batched = predict_ordered(CountingPredictor(), signals, matrix)

    def evaluate(values: tuple[float, ...]) -> tuple[list[str], dict[str, float | int]]:
        trades = [
            f"TRADE-{signal}" for signal, value in zip(signals, values, strict=True) if value > 0.0
        ]
        return trades, {"trade_count": len(trades), "prediction_sum": sum(values)}

    assert rowwise_values == batched.values
    assert evaluate(rowwise_values) == evaluate(batched.values)


def test_stage_timing_uses_fixed_order_accumulates_and_round_trips() -> None:
    timer = StageTimer(clock=_clock([10.0, 11.25, 20.0, 20.5, 30.0, 30.25]))
    with timer.measure("LOAD_DATA"):
        pass
    with timer.measure("FIT"):
        pass
    with timer.measure("FIT"):
        pass
    record = timer.as_record()
    validate_stage_timing_record(record)
    assert record["stage_order"] == list(TIMED_STAGES)
    assert record["duration_seconds"]["LOAD_DATA"] == 1.25
    assert record["duration_seconds"]["FIT"] == 0.75
    assert record["total_seconds"] == 2.0
    record["duration_seconds"]["PREDICT"] = -1
    with pytest.raises(RuntimeV2Error, match="invalid duration"):
        validate_stage_timing_record(record)


def test_frozen_historical_runtime_identities_remain_unchanged() -> None:
    manifest = json.loads(
        (ROOT / "research/runtime/FROZEN-HISTORICAL-RUNTIME-IDENTITIES.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["baseline_commit"] == "63bbcf8ab6531926fbede318218eacddb3086004"
    for relative, expected in manifest["files"].items():
        content = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(content).hexdigest() == expected, relative


def test_runtime_v2_code_and_benchmark_identities_are_bound() -> None:
    manifest = json.loads(
        (ROOT / "research/runtime/RESEARCH-RUNTIME-V2-BATCH.json").read_text(encoding="utf-8")
    )
    assert manifest["runtime_version"] == RUNTIME_VERSION
    assert manifest["cache"]["implemented"] is False
    for relative, expected in manifest["code_identity"]["sources"].items():
        content = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(content).hexdigest() == expected, relative
    benchmark = ROOT / manifest["benchmark"]["path"]
    content = benchmark.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(content).hexdigest() == manifest["benchmark"]["sha256_lf_normalized"]
