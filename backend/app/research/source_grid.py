"""Describe malformed source timestamps without repairing or reinterpreting prices."""

from __future__ import annotations

import hashlib
from datetime import timedelta

import numpy as np

from .evaluation_protocol import EPOCH, HOUR_US

MINUTE_US = 60_000_000


def grid_audit(times: np.ndarray) -> dict:
    bad = np.flatnonzero(times % MINUTE_US != 0)
    groups = np.split(bad, np.flatnonzero(np.diff(bad) != 1) + 1) if len(bad) else []

    def instant(value):
        return (EPOCH + timedelta(microseconds=int(value))).isoformat().replace("+00:00", "Z")

    return {
        "policy": "QUARANTINE_SOURCE_OFF_GRID_INTERVALS_V1",
        "off_grid_rows": len(bad),
        "intervals": [
            {
                "start": instant(times[group[0]]),
                "end": instant(times[group[-1]]),
                "rows": len(group),
            }
            for group in groups
        ],
        "quarantined_1h_buckets": len(unsafe_buckets(times, HOUR_US)),
        "quarantined_4h_buckets": len(unsafe_buckets(times, 4 * HOUR_US)),
        "repairs_or_fills": 0,
        "off_grid_timestamps_sha256": hashlib.sha256(
            times[bad].astype("<i8").tobytes()
        ).hexdigest(),
        "quarantine_masks_sha256": hashlib.sha256(
            np.asarray(sorted(unsafe_buckets(times, HOUR_US)), dtype="<i8").tobytes()
            + np.asarray(sorted(unsafe_buckets(times, 4 * HOUR_US)), dtype="<i8").tobytes()
        ).hexdigest(),
    }


def unsafe_buckets(times: np.ndarray, width_us: int) -> set[int]:
    if width_us not in (HOUR_US, 4 * HOUR_US):
        raise ValueError("unsupported feature timeframe")
    bad_times = times[times % MINUTE_US != 0]
    # Entire [open,open+1m) interval, including a late close crossing the next bucket.
    starts = bad_times // width_us * width_us
    ends = (bad_times + MINUTE_US - 1) // width_us * width_us
    return set(map(int, np.concatenate((starts, ends))))
