"""Frozen, source-free UTC calendar features for the first Generation V2 family.

The vector is a pure function of a timezone-aware UTC decision timestamp.  It reads no
market value, label, external source or future timestamp.  The ordered names and formulas
are governed by ``PREDICTIVE_V2_DETERMINISTIC_CALENDAR_FEATURES_V1``.
"""

from __future__ import annotations

import calendar
import math
from datetime import UTC, datetime

FEATURE_SET_VERSION = "PREDICTIVE_V2_DETERMINISTIC_CALENDAR_FEATURES_V1"
FEATURE_NAMES = (
    "UTC_HOUR_SIN",
    "UTC_HOUR_COS",
    "UTC_WEEKDAY_SIN",
    "UTC_WEEKDAY_COS",
    "UTC_YEAR_PHASE_SIN",
    "UTC_YEAR_PHASE_COS",
    "UTC_WEEKEND",
)
FEATURE_COUNT = len(FEATURE_NAMES)


class CalendarFeatureError(ValueError):
    """The frozen timestamp-only feature contract was violated."""


def _require_utc(moment: datetime) -> datetime:
    offset = moment.utcoffset()
    if moment.tzinfo is None or offset is None:
        raise CalendarFeatureError("the decision timestamp must be timezone-aware UTC")
    if offset.total_seconds() != 0:
        raise CalendarFeatureError("local time and non-UTC offsets are forbidden")
    # Normalize zero-offset timezone objects to the canonical UTC timezone without changing
    # the instant. This makes the representation independent of the caller's tzinfo class.
    return moment.astimezone(UTC)


def calendar_feature_vector(moment: datetime) -> tuple[float, ...]:
    """Return the exact seven-feature vector for one aware UTC timestamp."""
    utc = _require_utc(moment)
    weekday = utc.weekday()
    day_of_year = utc.timetuple().tm_yday
    days_in_year = 366 if calendar.isleap(utc.year) else 365
    hour_phase = 2.0 * math.pi * utc.hour / 24.0
    weekday_phase = 2.0 * math.pi * weekday / 7.0
    year_phase = 2.0 * math.pi * (day_of_year - 1) / days_in_year
    vector = (
        math.sin(hour_phase),
        math.cos(hour_phase),
        math.sin(weekday_phase),
        math.cos(weekday_phase),
        math.sin(year_phase),
        math.cos(year_phase),
        1.0 if weekday in {5, 6} else 0.0,
    )
    if len(vector) != FEATURE_COUNT or not all(math.isfinite(value) for value in vector):
        raise CalendarFeatureError("the deterministic calendar vector is invalid")
    return vector


def calendar_feature_vector_from_epoch(open_time: int) -> tuple[float, ...]:
    """Build the vector from a Unix-second UTC decision timestamp."""
    if isinstance(open_time, bool) or not isinstance(open_time, int):
        raise CalendarFeatureError("the decision timestamp must be an integer Unix second")
    try:
        moment = datetime.fromtimestamp(open_time, tz=UTC)
    except (OverflowError, OSError, ValueError) as error:
        raise CalendarFeatureError(
            "the decision timestamp is outside the supported range"
        ) from error
    return calendar_feature_vector(moment)


def feature_contract() -> dict[str, object]:
    """Machine-readable statement of the frozen information boundary."""
    return {
        "version": FEATURE_SET_VERSION,
        "ordered_names": list(FEATURE_NAMES),
        "feature_count": FEATURE_COUNT,
        "input": "TIMEZONE_AWARE_UTC_DECISION_TIMESTAMP_T_ONLY",
        "market_values_read": False,
        "labels_read": False,
        "external_sources_read": False,
        "future_timestamps_read": False,
        "local_timezone_or_dst_used": False,
        "leap_year_denominator": 366,
        "ordinary_year_denominator": 365,
        "invalid_row_policy": "IMPLEMENTATION_DEFECT_FAIL_CLOSED_BEFORE_MODEL_EXECUTION",
    }


__all__ = [
    "FEATURE_COUNT",
    "FEATURE_NAMES",
    "FEATURE_SET_VERSION",
    "CalendarFeatureError",
    "calendar_feature_vector",
    "calendar_feature_vector_from_epoch",
    "feature_contract",
]
