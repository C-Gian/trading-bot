from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.data.policy import CUTOFF


@dataclass(frozen=True)
class Fold:
    fold_id: str
    train_start: datetime
    train_end: datetime
    validation_start: datetime
    validation_end: datetime
    purge: timedelta
    embargo: timedelta


def make_folds(
    start: datetime,
    end: datetime,
    train: timedelta,
    validation: timedelta,
    purge: timedelta,
    embargo: timedelta,
    horizon: timedelta,
) -> tuple[Fold, ...]:
    if (
        start.tzinfo is None
        or end.tzinfo is None
        or end > CUTOFF
        or train <= timedelta(0)
        or validation <= timedelta(0)
        or horizon <= timedelta(0)
        or purge < timedelta(0)
        or embargo < timedelta(0)
        or purge < horizon
    ):
        raise ValueError("invalid boundaries or insufficient horizon purge")
    folds = []
    cursor = start
    validation_start = cursor + train + purge
    while validation_start + validation <= end:
        train_start = cursor
        train_end = validation_start - purge
        validation_end = validation_start + validation
        identity = (
            "|".join(
                x.isoformat() for x in (train_start, train_end, validation_start, validation_end)
            )
            + f"|{purge.total_seconds()}|{embargo.total_seconds()}|{horizon.total_seconds()}"
        )
        folds.append(
            Fold(
                hashlib.sha256(identity.encode()).hexdigest()[:16],
                train_start,
                train_end,
                validation_start,
                validation_end,
                purge,
                embargo,
            )
        )
        cursor = validation_end + embargo
        validation_start = cursor + train + purge
    return tuple(folds)
