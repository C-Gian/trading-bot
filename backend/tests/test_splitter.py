from datetime import UTC, datetime, timedelta

import pytest
from app.backtest.splitter import make_folds


def test_purged_walk_forward_has_no_overlap_and_is_deterministic():
    args = (
        datetime(2020, 1, 1, tzinfo=UTC),
        datetime(2020, 3, 1, tzinfo=UTC),
        timedelta(days=20),
        timedelta(days=10),
        timedelta(days=2),
        timedelta(days=1),
        timedelta(days=1),
    )
    first = make_folds(*args)
    assert first == make_folds(*args) and first
    for fold in first:
        assert (
            fold.train_end + fold.purge == fold.validation_start
            and fold.train_end < fold.validation_start
        )


def test_splitter_rejects_insufficient_purge_and_cutoff():
    with pytest.raises(ValueError):
        make_folds(
            datetime(2020, 1, 1, tzinfo=UTC),
            datetime(2020, 3, 1, tzinfo=UTC),
            timedelta(days=20),
            timedelta(days=10),
            timedelta(0),
            timedelta(0),
            timedelta(days=1),
        )
    with pytest.raises(ValueError):
        make_folds(
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2025, 1, 1, tzinfo=UTC),
            timedelta(days=20),
            timedelta(days=10),
            timedelta(days=1),
            timedelta(0),
            timedelta(days=1),
        )
