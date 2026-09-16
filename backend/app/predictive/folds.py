"""Chronological folds with purge and embargo. Random K-fold is not implemented here.

Training labels must close at least one embargo before a fold opens, and evaluation labels
must close before the fold ends, so no label window crosses a fold boundary in either
direction.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from . import HORIZON_HOURS
from .labels import HOUR_SECONDS, Label

PURGE_EMBARGO_HOURS = 24
FOLD_DESIGN = "EXPANDING_CHRONOLOGICAL_WALK_FORWARD"

WARMUP_END = "2019-01-01T00:00:00Z"
FOLD_BOUNDARIES = (
    ("2019", "2019-01-01T00:00:00Z", "2020-01-01T00:00:00Z"),
    ("2020", "2020-01-01T00:00:00Z", "2021-01-01T00:00:00Z"),
    ("2021", "2021-01-01T00:00:00Z", "2022-01-01T00:00:00Z"),
    ("2022", "2022-01-01T00:00:00Z", "2023-01-01T00:00:00Z"),
    ("2023", "2023-01-01T00:00:00Z", "2024-01-01T00:00:00Z"),
    ("2024", "2024-01-01T00:00:00Z", "2025-01-01T00:00:00Z"),
)


def epoch(moment: str) -> int:
    return int(datetime.strptime(moment, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp())


@dataclass(frozen=True)
class Fold:
    """One evaluation fold and the training portion that precedes it."""

    name: str
    start: int
    end: int
    training: tuple[Label, ...]
    evaluation: tuple[Label, ...]


@dataclass(frozen=True)
class FoldSet:
    folds: tuple[Fold, ...]
    horizon_hours: int
    purge_embargo_hours: int
    unassigned: dict[str, int]

    def eligible_total(self) -> int:
        return sum(len(fold.evaluation) for fold in self.folds)


def build_folds(
    labels: Sequence[Label],
    horizon_hours: int = HORIZON_HOURS,
    purge_embargo_hours: int = PURGE_EMBARGO_HOURS,
) -> FoldSet:
    """Assign admissible labels to folds under the frozen purge/embargo rules."""
    horizon = horizon_hours * HOUR_SECONDS
    embargo = purge_embargo_hours * HOUR_SECONDS
    ordered = sorted(labels, key=lambda item: item.open_time)
    folds: list[Fold] = []
    assigned: set[int] = set()

    for name, start_text, end_text in FOLD_BOUNDARIES:
        start, end = epoch(start_text), epoch(end_text)
        training = tuple(label for label in ordered if label.open_time + horizon + embargo <= start)
        evaluation = tuple(
            label
            for label in ordered
            if start <= label.open_time and label.open_time + horizon <= end
        )
        for label in evaluation:
            assigned.add(label.open_time)
        folds.append(
            Fold(name=name, start=start, end=end, training=training, evaluation=evaluation)
        )

    warmup_end = epoch(WARMUP_END)
    unassigned = {"WARMUP_TRAINING_BLOCK": 0, "FOLD_BOUNDARY_EMBARGO": 0}
    for label in ordered:
        if label.open_time in assigned:
            continue
        key = "WARMUP_TRAINING_BLOCK" if label.open_time < warmup_end else "FOLD_BOUNDARY_EMBARGO"
        unassigned[key] += 1

    return FoldSet(
        folds=tuple(folds),
        horizon_hours=horizon_hours,
        purge_embargo_hours=purge_embargo_hours,
        unassigned=unassigned,
    )


def assert_no_boundary_leak(fold_set: FoldSet) -> None:
    """Prove the frozen rules hold on the built folds instead of trusting the construction."""
    horizon = fold_set.horizon_hours * HOUR_SECONDS
    embargo = fold_set.purge_embargo_hours * HOUR_SECONDS
    for fold in fold_set.folds:
        for label in fold.training:
            if label.open_time + horizon + embargo > fold.start:
                raise ValueError(f"{fold.name}: a training label reaches into the fold")
        for label in fold.evaluation:
            if label.open_time < fold.start or label.open_time + horizon > fold.end:
                raise ValueError(f"{fold.name}: an evaluation label crosses the fold boundary")
        training_times = {label.open_time for label in fold.training}
        evaluation_times = {label.open_time for label in fold.evaluation}
        if training_times & evaluation_times:
            raise ValueError(f"{fold.name}: training and evaluation overlap")


__all__ = [
    "FOLD_BOUNDARIES",
    "FOLD_DESIGN",
    "PURGE_EMBARGO_HOURS",
    "WARMUP_END",
    "Fold",
    "FoldSet",
    "assert_no_boundary_leak",
    "build_folds",
    "epoch",
]
