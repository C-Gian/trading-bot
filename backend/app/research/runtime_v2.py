"""Prospective batch runtime primitives for future preregistered research.

This module is deliberately additive.  Frozen WP-008/WP-011--WP-015 labs keep their
original execution paths and identities; future candidates must bind this runtime
explicitly before using it.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

import numpy as np

RUNTIME_VERSION = "RESEARCH_RUNTIME_V2_BATCH"
RUNTIME_RECORD_VERSION = 1
PREDICTION_TOLERANCE = 1e-12
HOUR_US = 3_600_000_000
PROFILES = ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")
TIMED_STAGES = (
    "LOAD_DATA",
    "BUILD_FEATURES",
    "BUILD_LABELS",
    "FIT",
    "PREDICT",
    "PROFILES",
    "RECONCILIATION",
    "FINALIZE",
)


class RuntimeV2Error(ValueError):
    """A future candidate violated the V2 deterministic runtime contract."""


class MatrixPredictor(Protocol):
    def predict(self, matrix: np.ndarray) -> np.ndarray: ...


def _ordered_ids(values: Sequence[int], *, label: str) -> tuple[int, ...]:
    ids = tuple(values)
    if any(type(value) is not int for value in ids):
        raise RuntimeV2Error(f"{label} must contain integer identities")
    if any(right <= left for left, right in zip(ids, ids[1:], strict=False)):
        raise RuntimeV2Error(f"{label} must be unique and strictly increasing")
    return ids


@dataclass(frozen=True)
class OrderedPredictions:
    """One prediction per governed row, retained in exact input order."""

    signal_ids: tuple[int, ...]
    values: tuple[float, ...]
    runtime_version: str = RUNTIME_VERSION

    def __post_init__(self) -> None:
        _ordered_ids(self.signal_ids, label="prediction signal ids")
        if len(self.signal_ids) != len(self.values):
            raise RuntimeV2Error("prediction identities and values differ in length")
        if self.runtime_version != RUNTIME_VERSION or not all(
            math.isfinite(value) for value in self.values
        ):
            raise RuntimeV2Error("prediction record has invalid runtime or values")

    def as_mapping(self) -> dict[int, float]:
        return dict(zip(self.signal_ids, self.values, strict=True))

    def positive_decisions(self) -> tuple[bool, ...]:
        """The governed signal threshold is exactly and only prediction > 0."""
        return tuple(value > 0.0 for value in self.values)


@dataclass(frozen=True)
class PredictionView:
    """Predictions aligned to evaluation clocks with their source clocks explicit."""

    signal_ids: tuple[int, ...]
    prediction_signal_ids: tuple[int, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        _ordered_ids(self.signal_ids, label="profile signal ids")
        _ordered_ids(self.prediction_signal_ids, label="profile prediction source ids")
        if not (
            len(self.signal_ids) == len(self.prediction_signal_ids) == len(self.values)
        ) or not all(math.isfinite(value) for value in self.values):
            raise RuntimeV2Error("profile prediction view is malformed")

    def positive_decisions(self) -> tuple[bool, ...]:
        return tuple(value > 0.0 for value in self.values)


@dataclass(frozen=True)
class FoldPredictionInput:
    """One fitted model and its already-governed validation matrix."""

    fold_id: str
    model: MatrixPredictor
    signal_ids: tuple[int, ...]
    matrix: np.ndarray


def predict_ordered(
    model: MatrixPredictor,
    signal_ids: Sequence[int],
    matrix: np.ndarray,
    *,
    batch_rows: int | None = None,
) -> OrderedPredictions:
    """Predict once for a governed matrix, or in deterministic bounded batches."""
    ids = _ordered_ids(signal_ids, label="prediction signal ids")
    values = np.asarray(matrix, dtype=np.float64, order="C")
    if values.ndim != 2 or values.shape[0] != len(ids):
        raise RuntimeV2Error("prediction matrix and governed row identities do not align")
    if not np.isfinite(values).all():
        raise RuntimeV2Error("prediction matrix contains non-finite values")
    if batch_rows is not None and (type(batch_rows) is not int or batch_rows <= 0):
        raise RuntimeV2Error("batch_rows must be a positive integer or None")
    if len(ids) == 0:
        return OrderedPredictions((), ())

    size = batch_rows or len(ids)
    chunks: list[np.ndarray] = []
    for start in range(0, len(ids), size):
        predicted = np.asarray(model.predict(values[start : start + size]), dtype=np.float64)
        if predicted.ndim != 1 or predicted.shape[0] != min(size, len(ids) - start):
            raise RuntimeV2Error("model returned predictions with an invalid shape")
        if not np.isfinite(predicted).all():
            raise RuntimeV2Error("model returned non-finite predictions")
        chunks.append(predicted)
    combined = np.concatenate(chunks)
    return OrderedPredictions(ids, tuple(float(value) for value in combined))


def predict_folds(
    folds: Sequence[FoldPredictionInput], *, batch_rows: int | None = None
) -> OrderedPredictions:
    """Iterate folds deterministically and batch each validation matrix once by default."""
    if not folds or len({fold.fold_id for fold in folds}) != len(folds):
        raise RuntimeV2Error("fold prediction inputs must be nonempty with unique identities")
    signal_ids: list[int] = []
    values: list[float] = []
    for fold in folds:
        if not fold.fold_id:
            raise RuntimeV2Error("fold prediction identity is empty")
        predicted = predict_ordered(fold.model, fold.signal_ids, fold.matrix, batch_rows=batch_rows)
        signal_ids.extend(predicted.signal_ids)
        values.extend(predicted.values)
    return OrderedPredictions(tuple(signal_ids), tuple(values))


def build_profile_prediction_views(
    predictions: OrderedPredictions,
    evaluation_signal_ids: Sequence[int],
    *,
    delay_us: int = HOUR_US,
) -> Mapping[str, PredictionView]:
    """Reuse base predictions for cost stress and shift only DELAY_1H alignment."""
    evaluation = _ordered_ids(evaluation_signal_ids, label="evaluation signal ids")
    if type(delay_us) is not int or delay_us <= 0:
        raise RuntimeV2Error("delay_us must be a positive integer")
    lookup = predictions.as_mapping()
    try:
        base_values = tuple(lookup[signal] for signal in evaluation)
    except KeyError as exc:
        raise RuntimeV2Error("a base profile prediction is missing") from exc
    base = PredictionView(evaluation, evaluation, base_values)
    delayed_rows = [
        (signal, signal - delay_us, lookup[signal - delay_us])
        for signal in evaluation
        if signal - delay_us in lookup
    ]
    delayed = PredictionView(
        tuple(row[0] for row in delayed_rows),
        tuple(row[1] for row in delayed_rows),
        tuple(row[2] for row in delayed_rows),
    )
    return {
        "DEFAULT": base,
        "ZERO": base,
        "DOUBLE": base,
        "DELAY_1H": delayed,
    }


@dataclass
class StageTimer:
    """Accumulate real durations under a fixed, serializable stage vocabulary."""

    clock: Callable[[], float] = perf_counter
    _seconds: dict[str, float] = field(
        default_factory=lambda: dict.fromkeys(TIMED_STAGES, 0.0), init=False
    )

    @contextmanager
    def measure(self, stage: str) -> Iterator[None]:
        if stage not in self._seconds:
            raise RuntimeV2Error(f"undeclared runtime stage: {stage}")
        started = self.clock()
        try:
            yield
        finally:
            duration = self.clock() - started
            if not math.isfinite(duration) or duration < 0:
                raise RuntimeV2Error("runtime clock moved backward or became non-finite")
            self._seconds[stage] += duration

    def as_record(self) -> dict[str, Any]:
        durations = {stage: self._seconds[stage] for stage in TIMED_STAGES}
        return {
            "record_version": RUNTIME_RECORD_VERSION,
            "runtime_version": RUNTIME_VERSION,
            "stage_order": list(TIMED_STAGES),
            "duration_seconds": durations,
            "total_seconds": sum(durations.values()),
        }


def validate_stage_timing_record(record: Mapping[str, Any]) -> None:
    if (
        record.get("record_version") != RUNTIME_RECORD_VERSION
        or record.get("runtime_version") != RUNTIME_VERSION
        or record.get("stage_order") != list(TIMED_STAGES)
    ):
        raise RuntimeV2Error("stage timing identity is invalid")
    durations = record.get("duration_seconds")
    if not isinstance(durations, dict) or tuple(durations) != TIMED_STAGES:
        raise RuntimeV2Error("stage timing keys are incomplete or out of order")
    if any(
        not isinstance(durations[stage], (int, float))
        or isinstance(durations[stage], bool)
        or not math.isfinite(float(durations[stage]))
        or float(durations[stage]) < 0
        for stage in TIMED_STAGES
    ):
        raise RuntimeV2Error("stage timing contains an invalid duration")
    total = record.get("total_seconds")
    if (
        not isinstance(total, (int, float))
        or isinstance(total, bool)
        or not math.isclose(
            float(total),
            sum(float(durations[stage]) for stage in TIMED_STAGES),
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ):
        raise RuntimeV2Error("stage timing total does not reconcile")


__all__ = [
    "HOUR_US",
    "PREDICTION_TOLERANCE",
    "PROFILES",
    "RUNTIME_VERSION",
    "TIMED_STAGES",
    "FoldPredictionInput",
    "OrderedPredictions",
    "PredictionView",
    "RuntimeV2Error",
    "StageTimer",
    "build_profile_prediction_views",
    "predict_folds",
    "predict_ordered",
    "validate_stage_timing_record",
]
