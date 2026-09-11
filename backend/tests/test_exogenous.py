from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from app.research.alfred import asof_values, parse_snapshot
from app.research.exogenous import (
    ALFRED_SERIES,
    GDELT_CHANNELS,
    ExogenousDataError,
    next_day_availability,
    validate_catalogs,
)
from app.research.exogenous_oracle import (
    _alfred_oracle,
    _gdelt_chunk_boundary_samples,
)
from app.research.gdelt import _aggregate, _valid_payload, _validate_acquired_document


def test_catalogs_have_exact_preselected_sources_queries_and_series() -> None:
    catalogs = validate_catalogs()
    assert catalogs["source"]["authorized_source_family_count"] == 2
    assert tuple(item["channel_id"] for item in catalogs["gdelt"]["channels"]) == GDELT_CHANNELS
    assert tuple(item["series_id"] for item in catalogs["alfred"]["series"]) == ALFRED_SERIES


def test_date_only_vintage_is_not_available_until_next_utc_day() -> None:
    assert next_day_availability(date(2020, 1, 15)) == datetime(2020, 1, 16, tzinfo=UTC)


def test_alfred_oracle_has_no_pre_catalog_vintage_at_grid_start() -> None:
    values = _alfred_oracle(Path(), {}, datetime(2017, 8, 17, tzinfo=UTC))
    assert all(values[f"{series.lower()}_data_available"] is False for series in ALFRED_SERIES)


def test_alfred_oracle_does_not_bridge_an_explicit_source_gap() -> None:
    vintage = date(2018, 1, 23)
    request_index = {
        (series, vintage): {"request_status": "SOURCE_VINTAGE_UNAVAILABLE_NO_OBSERVATIONS"}
        for series in ALFRED_SERIES
    }
    values = _alfred_oracle(Path(), request_index, datetime(2018, 1, 24, tzinfo=UTC))
    assert all(values[f"{series.lower()}_data_available"] is False for series in ALFRED_SERIES)


def test_oracle_samples_both_sides_of_frozen_gdelt_chunk_boundaries() -> None:
    samples = _gdelt_chunk_boundary_samples()
    first_boundary = datetime(2017, 8, 24, tzinfo=UTC)
    assert {
        first_boundary - timedelta(hours=1),
        first_boundary,
        first_boundary + timedelta(hours=1),
    } <= samples


def test_later_macro_revision_cannot_leak_backward() -> None:
    records = [
        {
            "series_id": "CPIAUCSL",
            "observation_date": date(2020, 1, 1),
            "value": 100.0,
            "vintage_start": date(2020, 2, 1),
            "vintage_end": date(2020, 2, 9),
            "availability_time": datetime(2020, 2, 2, tzinfo=UTC),
            "source_request_id": "old",
        },
        {
            "series_id": "CPIAUCSL",
            "observation_date": date(2020, 1, 1),
            "value": 101.0,
            "vintage_start": date(2020, 2, 10),
            "vintage_end": None,
            "availability_time": datetime(2020, 2, 11, tzinfo=UTC),
            "source_request_id": "revision",
        },
    ]
    before = asof_values(records, datetime(2020, 2, 10, 23, 59, tzinfo=UTC))
    after = asof_values(records, datetime(2020, 2, 11, tzinfo=UTC))
    assert before["CPIAUCSL"]["value"] == 100.0
    assert after["CPIAUCSL"]["value"] == 101.0


def test_alfred_parser_rejects_current_revision_substitution() -> None:
    current = b"observation_date,DFF_20260909\n2020-01-01,1.55\n"
    with pytest.raises(ExogenousDataError, match="series or vintage identity"):
        parse_snapshot(current, "DFF", date(2020, 1, 15))


def test_alfred_parser_accepts_only_requested_series_vintage() -> None:
    frozen = b"observation_date,DFF_20200115\n2020-01-01,1.55\n"
    assert parse_snapshot(frozen, "DFF", date(2020, 1, 15)) == {date(2020, 1, 1): 1.55}


def test_gdelt_rejects_daily_resolution() -> None:
    payload = b'{"query_details":{"date_resolution":"day"},"timeline":[]}'
    with pytest.raises(ExogenousDataError, match="not subdaily/hourly"):
        _valid_payload(payload)


def test_frozen_gdelt_acquisition_requires_hourly_points_within_request() -> None:
    spec = {
        "start_utc": "2020-01-01T00:00:00Z",
        "end_utc": "2020-01-07T23:59:59Z",
    }
    subhour = {
        "query_details": {"date_resolution": "15m"},
        "timeline": [{"data": []}],
    }
    with pytest.raises(ExogenousDataError, match="did not return hourly"):
        _validate_acquired_document(subhour, spec)
    outside = {
        "query_details": {"date_resolution": "hour"},
        "timeline": [{"data": [{"date": "20200108T000000Z", "value": 0, "norm": 1}]}],
    }
    with pytest.raises(ExogenousDataError, match="escaped frozen request bounds"):
        _validate_acquired_document(outside, spec)


def test_gdelt_missing_subhour_source_coverage_is_not_zero() -> None:
    document = {
        "query_details": {"date_resolution": "15m"},
        "timeline": [
            {
                "series": "Article Count",
                "data": [
                    {"date": "20200101T000000Z", "value": 2, "norm": 100},
                    {"date": "20200101T001500Z", "value": 0, "norm": 120},
                    {"date": "20200101T003000Z", "value": 1, "norm": 110},
                ],
            }
        ],
    }
    result = _aggregate(document, mode="TimelineVolRaw")[datetime(2020, 1, 1, tzinfo=UTC)]
    assert result["data_available"] is False
    assert result["matched_articles"] is None


def test_gdelt_complete_subhour_source_coverage_aggregates_exactly() -> None:
    document = {
        "query_details": {"date_resolution": "30m"},
        "timeline": [
            {
                "series": "Article Count",
                "data": [
                    {"date": "20200101T000000Z", "value": 2, "norm": 100},
                    {"date": "20200101T003000Z", "value": 3, "norm": 150},
                ],
            }
        ],
    }
    result = _aggregate(document, mode="TimelineVolRaw")[datetime(2020, 1, 1, tzinfo=UTC)]
    assert result["data_available"] is True
    assert result["matched_articles"] == 5
    assert result["monitored_articles_norm"] == 250
    assert result["coverage_share"] == 0.02
