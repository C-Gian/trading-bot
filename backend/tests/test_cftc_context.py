from __future__ import annotations

import csv
import io
import zipfile
from datetime import UTC, date, datetime

import pytest
from app.research.cftc import (
    EXCEPTION_BASIS,
    FEATURE,
    ORDINARY_BASIS,
    CFTCContextSource,
    CFTCDataError,
    availability_timestamp,
    development_eligible,
    leveraged_net_oi_share,
    ordinary_publication_date,
    parse_archive,
    resolve_publication_date,
)


def _us(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp() * 1_000_000)


def _official_doc(report: str, updated: str) -> bytes:
    return f"Positions as of {report}<footer>Updated {updated}</footer>".encode()


def _archive(rows: list[dict[str, str]]) -> bytes:
    columns = [
        "Market_and_Exchange_Names",
        "Report_Date_as_YYYY-MM-DD",
        "CFTC_Contract_Market_Code",
        "Open_Interest_All",
        "Lev_Money_Positions_Long_All",
        "Lev_Money_Positions_Short_All",
    ]
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("FinFutYY.txt", text.getvalue())
    return output.getvalue()


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "Market_and_Exchange_Names": "BITCOIN - CHICAGO MERCANTILE EXCHANGE",
        "Report_Date_as_YYYY-MM-DD": "2024-12-24",
        "CFTC_Contract_Market_Code": "133741",
        "Open_Interest_All": "100",
        "Lev_Money_Positions_Long_All": "30",
        "Lev_Money_Positions_Short_All": "50",
    }
    row.update(overrides)
    return row


def test_tuesday_report_date_is_not_availability() -> None:
    report = date(2024, 6, 11)
    assert ordinary_publication_date(report) == date(2024, 6, 14)
    assert availability_timestamp(date(2024, 6, 14)) == datetime(2024, 6, 15, tzinfo=UTC)
    assert availability_timestamp(date(2024, 6, 14)).date() != report


def test_ordinary_release_is_unavailable_before_and_available_at_boundary() -> None:
    source = CFTCContextSource([_us("2024-06-15T00:00:00Z")], [date(2024, 6, 11)], [-0.2])
    with pytest.raises(CFTCDataError, match="no CFTC report"):
        source.at(_us("2024-06-14T23:59:59.999999Z"))
    assert source.at(_us("2024-06-15T00:00:00Z")) == (
        _us("2024-06-15T00:00:00Z"),
        date(2024, 6, 11),
        -0.2,
    )


def test_official_delay_uses_actual_publication_not_ordinary_friday() -> None:
    publication, basis = resolve_publication_date(
        date(2023, 1, 31), _official_doc("January 31, 2023", "February 24, 2023")
    )
    assert publication == date(2023, 2, 24)
    assert basis == EXCEPTION_BASIS
    assert availability_timestamp(publication) == datetime(2023, 2, 25, tzinfo=UTC)


def test_ordinary_official_object_date_gets_ordinary_basis() -> None:
    publication, basis = resolve_publication_date(
        date(2024, 6, 11), _official_doc("June 11, 2024", "June 14, 2024")
    )
    assert publication == date(2024, 6, 14) and basis == ORDINARY_BASIS


@pytest.mark.parametrize(
    "document",
    [
        b"",
        b"not-a-date",
        _official_doc("June 11, 2024", "June 14, 2024") + b" Updated June 17, 2024",
    ],
)
def test_unresolved_publication_date_is_unavailable(document: bytes) -> None:
    with pytest.raises(CFTCDataError):
        resolve_publication_date(date(2024, 6, 11), document)


def test_http_last_modified_is_not_publication_evidence() -> None:
    with pytest.raises(CFTCDataError, match="report date"):
        resolve_publication_date(date(2024, 1, 2), b"Last-Modified: October 22, 2024")


def test_official_page_must_match_expected_report_date() -> None:
    with pytest.raises(CFTCDataError, match="does not match"):
        resolve_publication_date(
            date(2018, 9, 25), _official_doc("September 18, 2018", "September 21, 2018")
        )


def test_latest_eligible_prior_report_is_held_without_interpolation() -> None:
    source = CFTCContextSource(
        [_us("2024-06-15T00:00:00Z"), _us("2024-06-22T00:00:00Z")],
        [date(2024, 6, 11), date(2024, 6, 18)],
        [-0.2, 0.4],
    )
    assert source.at(_us("2024-06-20T12:34:00Z"))[2] == -0.2
    assert source.at(_us("2024-06-21T23:59:59Z"))[2] == -0.2
    assert source.at(_us("2024-06-22T00:00:00Z"))[2] == 0.4


def test_future_report_never_leaks_backward() -> None:
    source = CFTCContextSource(
        [_us("2024-06-15T00:00:00Z"), _us("2024-07-09T00:00:00Z")],
        [date(2024, 6, 11), date(2024, 7, 2)],
        [-0.2, 0.9],
    )
    assert source.at(_us("2024-07-08T23:59:59Z"))[2] == -0.2


def test_feature_uses_only_same_report_long_short_and_open_interest() -> None:
    parsed = parse_archive(_archive([_row()]), 2024)
    report = parsed[0]
    assert FEATURE == "CFTC_LEVERAGED_FUNDS_NET_OI_SHARE_V1"
    assert leveraged_net_oi_share(
        report["leveraged_funds_long_all"],
        report["leveraged_funds_short_all"],
        report["open_interest_all"],
    ) == pytest.approx((30 - 50) / 100)


@pytest.mark.parametrize("open_interest", [0, -1])
def test_invalid_same_report_denominator_fails_closed(open_interest: int) -> None:
    with pytest.raises(CFTCDataError, match="invalid"):
        leveraged_net_oi_share(30, 50, open_interest)


def test_postcutoff_availability_is_not_development_eligible() -> None:
    publication, basis = resolve_publication_date(
        date(2024, 12, 31), _official_doc("December 31, 2024", "January 06, 2025")
    )
    assert basis == EXCEPTION_BASIS
    assert not development_eligible(availability_timestamp(publication))


def test_wrong_market_identity_and_duplicate_rows_fail_closed() -> None:
    wrong = _row(Market_and_Exchange_Names="NOT BITCOIN")
    with pytest.raises(CFTCDataError, match="unexpected market"):
        parse_archive(_archive([wrong]), 2024)
    with pytest.raises(CFTCDataError, match="duplicate"):
        parse_archive(_archive([_row(), _row()]), 2024)
