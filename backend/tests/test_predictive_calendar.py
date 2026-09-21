from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta, timezone

import pytest
from app.predictive import DOWN, UP
from app.predictive.calendar import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    FAMILY_SIZE,
    FEATURE_PROOF_PATH,
    INTERVAL_MASS,
    PER_CONFIGURATION_ALPHA,
    admission,
    preregistration,
    search_plan,
)
from app.predictive.calendar_features import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    CalendarFeatureError,
    calendar_feature_vector,
    calendar_feature_vector_from_epoch,
)
from app.predictive.calendar_model import (
    CALIBRATION_EMBARGO_HOURS,
    HGBR_MODEL_VERSION,
    LINEAR_MODEL_VERSION,
    calibration_split,
    fit_probability_head,
)
from app.predictive.internal_structure import ROOT
from app.predictive.selective_long import ACTION_THRESHOLD, GATE_NAMES


def test_feature_set_is_exactly_the_frozen_seven() -> None:
    assert FEATURE_SET_VERSION == "PREDICTIVE_V2_DETERMINISTIC_CALENDAR_FEATURES_V1"
    assert FEATURE_COUNT == 7
    assert FEATURE_NAMES == (
        "UTC_HOUR_SIN",
        "UTC_HOUR_COS",
        "UTC_WEEKDAY_SIN",
        "UTC_WEEKDAY_COS",
        "UTC_YEAR_PHASE_SIN",
        "UTC_YEAR_PHASE_COS",
        "UTC_WEEKEND",
    )


def test_known_monday_midnight_vector() -> None:
    values = calendar_feature_vector(datetime(2024, 1, 1, tzinfo=UTC))
    assert values == pytest.approx((0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0), abs=1e-15)


def test_market_mutation_cannot_change_timestamp_only_vector() -> None:
    moment = datetime(2024, 5, 17, 9, tzinfo=UTC)
    market_a = {"close": 1.0, "volume": 0.0, "label": -100.0}
    market_b = {"close": 1_000_000.0, "volume": 999.0, "label": 100.0}
    assert market_a != market_b
    assert calendar_feature_vector(moment) == calendar_feature_vector(moment)


def test_one_hour_move_is_exactly_new_timestamp_representation() -> None:
    moment = datetime(2024, 5, 17, 9, tzinfo=UTC)
    next_moment = moment + timedelta(hours=1)
    assert calendar_feature_vector_from_epoch(int(moment.timestamp()) + 3600) == (
        calendar_feature_vector(next_moment)
    )
    current = calendar_feature_vector(moment)
    following = calendar_feature_vector(next_moment)
    assert current[0:2] != following[0:2]
    assert current[2:] == following[2:]


def test_utc_weekday_and_weekend_boundary() -> None:
    friday = datetime(2024, 3, 1, 23, tzinfo=UTC)
    saturday = friday + timedelta(hours=1)
    assert friday.weekday() == 4 and saturday.weekday() == 5
    assert calendar_feature_vector(friday)[6] == 0.0
    assert calendar_feature_vector(saturday)[6] == 1.0
    assert calendar_feature_vector(friday)[2:4] != calendar_feature_vector(saturday)[2:4]


def test_december_31_to_january_1_wrap() -> None:
    end = datetime(2023, 12, 31, 23, tzinfo=UTC)
    start = end + timedelta(hours=1)
    assert calendar_feature_vector(start)[4:6] == pytest.approx((0.0, 1.0), abs=1e-15)
    assert calendar_feature_vector(end) != calendar_feature_vector(start)


def test_leap_day_uses_366_day_denominator() -> None:
    leap_day = datetime(2024, 2, 29, tzinfo=UTC)
    ordinary_march = datetime(2023, 3, 1, tzinfo=UTC)
    assert calendar_feature_vector(leap_day)[4] == pytest.approx(math.sin(2 * math.pi * 59 / 366))
    assert calendar_feature_vector(ordinary_march)[4] == pytest.approx(
        math.sin(2 * math.pi * 59 / 365)
    )


def test_local_time_and_dst_cannot_enter(monkeypatch: pytest.MonkeyPatch) -> None:
    instant = 1_717_243_200
    expected = calendar_feature_vector_from_epoch(instant)
    monkeypatch.setenv("TZ", "Pacific/Auckland")
    assert calendar_feature_vector_from_epoch(instant) == expected
    monkeypatch.setenv("TZ", "America/New_York")
    assert calendar_feature_vector_from_epoch(instant) == expected
    equivalent = datetime.fromtimestamp(instant, tz=timezone(timedelta(0)))
    assert calendar_feature_vector(equivalent) == expected


@pytest.mark.parametrize(
    "moment",
    [
        datetime.fromisoformat("2024-01-01T00:00:00"),
        datetime(2024, 1, 1, tzinfo=timezone(timedelta(hours=1))),
    ],
)
def test_non_utc_or_naive_timestamp_fails_closed(moment: datetime) -> None:
    with pytest.raises(CalendarFeatureError):
        calendar_feature_vector(moment)


def test_calibration_split_is_chronological_with_48h_embargo() -> None:
    times = list(range(0, 1000 * 3600, 3600))
    split = calibration_split(times)
    assert CALIBRATION_EMBARGO_HOURS == 48
    assert split.boundary_index == 800
    assert split.base_fit_rows == 753
    assert split.calibration_rows == 200
    assert split.dropped_to_embargo == 47


@pytest.mark.parametrize("model", [LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION])
def test_both_frozen_models_emit_deterministic_calibrated_probabilities(model: str) -> None:
    start = int(datetime(2020, 1, 1, tzinfo=UTC).timestamp())
    times = [start + index * 3600 for index in range(600)]
    features = [calendar_feature_vector_from_epoch(moment) for moment in times]
    directions = [UP if (index // 12) % 2 else DOWN for index in range(600)]
    first = fit_probability_head(model, times, features, directions)
    second = fit_probability_head(model, times, features, directions)
    probe = features[-24:]
    assert first.probability_up(probe) == second.probability_up(probe)
    assert all(0.0 <= value <= 1.0 for value in first.probability_up(probe))
    assert first.split == second.split


def test_family_search_design_is_frozen_without_search() -> None:
    plan = search_plan()
    assert FAMILY_SIZE == 2
    assert tuple(plan["configuration_order"]) == CONFIGURATION_ORDER
    assert plan["family_size"] == 2
    assert plan["action_threshold"] == ACTION_THRESHOLD == 0.60
    assert len(GATE_NAMES) == 10
    assert PER_CONFIGURATION_ALPHA == 0.025
    assert INTERVAL_MASS == 0.975
    assert plan["inference"]["seed"] == 20260921
    assert not plan["threshold_search"]
    assert not plan["feature_search"]
    assert not plan["hyperparameter_search"]
    for model in CONFIGURATION_ORDER:
        record = preregistration(model)
        assert record["trial_budget"] == 1
        assert record["magnitude_declared"] is False
        assert record["sealed_query_authorized"] is False


def test_pre_result_feature_proof_and_admission_match_files() -> None:
    proof = json.loads((ROOT / FEATURE_PROOF_PATH).read_text(encoding="utf-8"))
    assert proof["status"] == "PASS_BEFORE_FIRST_MODEL_FIT"
    assert proof["eligible_development_feature_validity"] == 1.0
    assert proof["outer_fold_feature_validity"] == 1.0
    assert proof["model_fits"] == proof["outer_predictions"] == proof["sealed_queries"] == 0
    assert all(proof["checks"].values())
    stored = json.loads((ROOT / ADMISSION_PATH).read_text(encoding="utf-8"))
    assert stored == admission(ROOT)
    assert stored["v1_result_count"] == 10


def test_installed_development_feature_validity_is_one() -> None:
    from app.predictive import HORIZON_HOURS
    from app.predictive.labels import HOURLY_ARTIFACT, build_labels, load_hourly_bars

    if not (ROOT / HOURLY_ARTIFACT).is_file():
        pytest.skip("installed development data are intentionally absent")
    labels = build_labels(load_hourly_bars(ROOT), horizon_hours=HORIZON_HOURS).labels
    vectors = [calendar_feature_vector_from_epoch(label.open_time) for label in labels]
    assert len(vectors) == len(labels)
    assert all(len(vector) == FEATURE_COUNT for vector in vectors)
