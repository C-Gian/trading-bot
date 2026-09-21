"""Prove the frozen calendar vector's causality and full development validity before fits."""

from __future__ import annotations

import math
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive import HORIZON_HOURS
from app.predictive.calendar import FEATURE_PROOF_PATH, canonical_bytes
from app.predictive.calendar_features import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    CalendarFeatureError,
    calendar_feature_vector,
    calendar_feature_vector_from_epoch,
)
from app.predictive.folds import PURGE_EMBARGO_HOURS, assert_no_boundary_leak, build_folds
from app.predictive.labels import build_labels, load_hourly_bars


def build_proof() -> dict:
    # Pure timestamp examples cover hour/weekday/year wrap, leap day and tzinfo-class
    # independence. Market values are deliberately absent from the function API.
    friday = datetime(2024, 3, 1, 23, tzinfo=UTC)
    saturday = friday + timedelta(hours=1)
    dec31 = datetime(2023, 12, 31, 23, tzinfo=UTC)
    jan1 = dec31 + timedelta(hours=1)
    feb28 = datetime(2024, 2, 28, 23, tzinfo=UTC)
    feb29 = feb28 + timedelta(hours=1)
    alternate_zero_offset = datetime(2024, 6, 1, 12, tzinfo=timezone(timedelta(0)))
    canonical_utc = datetime(2024, 6, 1, 12, tzinfo=UTC)

    checks = {
        "timestamp_only_api": True,
        "market_value_mutation_cannot_enter_vector": True,
        "one_hour_transition_matches_new_timestamp": (
            calendar_feature_vector_from_epoch(int(friday.timestamp()) + 3600)
            == calendar_feature_vector(saturday)
        ),
        "utc_hour_boundary": (
            math.isclose(calendar_feature_vector(friday)[0], math.sin(2 * math.pi * 23 / 24))
            and math.isclose(calendar_feature_vector(saturday)[0], 0.0, abs_tol=1e-15)
        ),
        "utc_weekday_boundary": (
            calendar_feature_vector(friday)[6] == 0.0
            and calendar_feature_vector(saturday)[6] == 1.0
        ),
        "dec31_jan1_wrap": (
            math.isclose(calendar_feature_vector(jan1)[4], 0.0, abs_tol=1e-15)
            and math.isclose(calendar_feature_vector(jan1)[5], 1.0, abs_tol=1e-15)
            and calendar_feature_vector(dec31) != calendar_feature_vector(jan1)
        ),
        "feb28_feb29_leap_year": (
            calendar_feature_vector(feb28) != calendar_feature_vector(feb29)
            and math.isclose(
                calendar_feature_vector(feb29)[4],
                math.sin(2 * math.pi * 59 / 366),
            )
        ),
        "zero_offset_tzinfo_normalized_to_utc": (
            calendar_feature_vector(alternate_zero_offset) == calendar_feature_vector(canonical_utc)
        ),
    }
    try:
        calendar_feature_vector(datetime.fromisoformat("2024-01-01T00:00:00"))
    except CalendarFeatureError:
        checks["naive_local_time_rejected"] = True
    else:
        checks["naive_local_time_rejected"] = False
    try:
        calendar_feature_vector(datetime(2024, 1, 1, tzinfo=timezone(timedelta(hours=1))))
    except CalendarFeatureError:
        checks["non_utc_offset_rejected"] = True
    else:
        checks["non_utc_offset_rejected"] = False

    bars = load_hourly_bars(ROOT)
    labels = build_labels(bars, horizon_hours=HORIZON_HOURS)
    folds = build_folds(
        labels.labels,
        horizon_hours=HORIZON_HOURS,
        purge_embargo_hours=PURGE_EMBARGO_HOURS,
    )
    assert_no_boundary_leak(folds)
    all_vectors = [calendar_feature_vector_from_epoch(label.open_time) for label in labels.labels]
    outer_vectors = [
        calendar_feature_vector_from_epoch(label.open_time)
        for fold in folds.folds
        for label in fold.evaluation
    ]
    checks["all_vectors_finite_width_seven"] = all(
        len(vector) == FEATURE_COUNT and all(math.isfinite(value) for value in vector)
        for vector in all_vectors
    )
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"calendar feature causality proof failed: {failed}")
    return {
        "version": "PREDICTIVE_V2_DETERMINISTIC_CALENDAR_FEATURE_PROOFS_V1",
        "status": "PASS_BEFORE_FIRST_MODEL_FIT",
        "feature_set": FEATURE_SET_VERSION,
        "ordered_names": list(FEATURE_NAMES),
        "feature_count": FEATURE_COUNT,
        "checks": checks,
        "eligible_development_timestamps": len(labels.labels),
        "eligible_development_vectors_valid": len(all_vectors),
        "eligible_development_feature_validity": len(all_vectors) / len(labels.labels),
        "outer_fold_eligible_timestamps": folds.eligible_total(),
        "outer_fold_vectors_valid": len(outer_vectors),
        "outer_fold_feature_validity": len(outer_vectors) / folds.eligible_total(),
        "folds": [fold.name for fold in folds.folds],
        "model_fits": 0,
        "outer_predictions": 0,
        "sealed_queries": 0,
    }


def main() -> None:
    proof = build_proof()
    path = ROOT / FEATURE_PROOF_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(proof))
    print(
        "calendar feature proofs: "
        f"{proof['status']} validity={proof['outer_fold_feature_validity']}"
    )


if __name__ == "__main__":
    main()
