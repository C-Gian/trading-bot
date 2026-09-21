"""Synthetic point-in-time proofs for the corrected macro release-state semantics.

Every fixture here is hand-built, so these tests run without the installed market data and
demonstrate the exact distinction the contract draws: a published release persists as the
current known state, while nothing that was not available at `T` is ever read.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime

import pytest
from app.predictive.macro_release_state_source import (
    FEATURE_NAMES,
    SOURCE_CADENCE_LIMIT_DAYS,
    MacroReleaseStateSource,
    VintageRecord,
    cadence_findings,
    months_earlier,
)

DECISION = "2024-06-15T12:00:00"
EARLIER_DECISION = "2024-05-26T12:00:00"
AFTER_MONTHLY_RELEASE = "2024-06-17T12:00:00"


def stamp(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp())


def next_day(value: date) -> int:
    return int(datetime(value.year, value.month, value.day, tzinfo=UTC).timestamp()) + 86_400


def daily(points: list[tuple[str, float]]) -> list[VintageRecord]:
    """One vintage per observation, conservatively available the next calendar day."""
    records = []
    for text, value in points:
        observation = date.fromisoformat(text)
        records.append(
            VintageRecord(available=next_day(observation), observation=observation, value=value)
        )
    return records


def fixture_records() -> dict[str, list[VintageRecord]]:
    """A complete eight-series substrate around a 2024-06-15 decision.

    The CPI and unemployment releases describing April become available on 2024-05-16, and the
    ones describing May only on 2024-06-16 - after the decision. At `T` the April release is
    75 calendar days older than the decision date, which the predecessor's single freshness
    rule would have rejected even though no newer release existed anywhere.
    """
    return {
        "DFF": daily([("2024-04-24", 4.8), ("2024-05-16", 5.0), ("2024-06-14", 5.5)]),
        "DGS10": daily([("2024-04-24", 3.8), ("2024-05-16", 4.0), ("2024-06-14", 4.2)]),
        "T10Y2Y": daily([("2024-04-24", -0.7), ("2024-05-16", -0.5), ("2024-06-14", -0.2)]),
        "VIXCLS": daily(
            [("2024-05-21", 18.0), ("2024-06-10", 20.0), ("2024-06-14", 22.0)]
        ),
        "NFCI": daily([("2024-04-27", -0.6), ("2024-05-18", -0.4), ("2024-06-14", -0.1)]),
        "WALCL": daily(
            [
                ("2024-04-27", 6_900_000.0),
                ("2024-05-18", 7_000_000.0),
                ("2024-06-12", 7_070_000.0),
            ]
        ),
        "CPIAUCSL": [
            VintageRecord(stamp("2023-05-15T00:00:00"), date(2023, 4, 1), 303.0),
            VintageRecord(stamp("2023-06-15T00:00:00"), date(2023, 5, 1), 304.0),
            VintageRecord(stamp("2024-05-16T00:00:00"), date(2024, 4, 1), 312.0),
            VintageRecord(stamp("2024-06-16T00:00:00"), date(2024, 5, 1), 313.0),
        ],
        "UNRATE": [
            VintageRecord(stamp("2024-02-10T00:00:00"), date(2024, 1, 1), 3.7),
            VintageRecord(stamp("2024-03-10T00:00:00"), date(2024, 2, 1), 3.8),
            VintageRecord(stamp("2024-05-16T00:00:00"), date(2024, 4, 1), 3.9),
            VintageRecord(stamp("2024-06-16T00:00:00"), date(2024, 5, 1), 4.1),
        ],
    }


def build(records: dict[str, list[VintageRecord]] | None = None) -> MacroReleaseStateSource:
    return MacroReleaseStateSource(records or fixture_records())


def test_the_frozen_feature_vector_has_exact_order_and_values():
    values, reason = build().at(stamp(DECISION))
    assert reason is None and values is not None
    assert len(values) == len(FEATURE_NAMES) == 13
    assert values == pytest.approx(
        (
            5.5,
            0.5,
            4.2,
            0.2,
            -0.2,
            0.3,
            math.log(22.0),
            math.log(22.0 / 20.0),
            -0.1,
            0.3,
            math.log(7_070_000.0 / 7_000_000.0),
            math.log(312.0 / 303.0),
            0.2,
        )
    )


def test_a_current_level_older_than_the_retired_45_day_rule_is_now_admitted():
    """The exact case that blocked the predecessor: an April CPI read on 15 June."""
    source = build()
    current = source.current_release("CPIAUCSL", stamp(DECISION))
    assert current is not None
    observation, value = current
    assert observation == date(2024, 4, 1) and value == 312.0
    age_days = (datetime.fromisoformat(DECISION).date() - observation).days
    assert age_days == 75
    assert source.at(stamp(DECISION))[0] is not None


def test_a_later_revision_cannot_change_an_earlier_feature_vector():
    records = fixture_records()
    earlier = build(records).at(stamp(DECISION))[0]
    records["DFF"].append(
        VintageRecord(stamp("2024-06-20T00:00:00"), date(2024, 6, 14), 99.0)
    )
    revised = build(records)
    assert revised.at(stamp(DECISION))[0] == earlier
    later = revised.at(stamp("2024-06-21T12:00:00"))[0]
    assert later is not None and later[0] == 99.0


def test_a_latest_known_monthly_release_persists_between_releases():
    source = build()
    early = source.current_release("CPIAUCSL", stamp(EARLIER_DECISION))
    late = source.current_release("CPIAUCSL", stamp(DECISION))
    assert early == late == (date(2024, 4, 1), 312.0)
    early_vector = source.at(stamp(EARLIER_DECISION))[0]
    late_vector = source.at(stamp(DECISION))[0]
    assert early_vector is not None and late_vector is not None
    # The CPI and unemployment components are identical; nothing was interpolated between them.
    assert early_vector[11] == late_vector[11]
    assert early_vector[12] == late_vector[12]


def test_a_future_monthly_release_is_invisible_before_its_availability():
    source = build()
    assert source.current_release("CPIAUCSL", stamp(DECISION)) == (date(2024, 4, 1), 312.0)
    assert source.current_release("CPIAUCSL", stamp(AFTER_MONTHLY_RELEASE)) == (
        date(2024, 5, 1),
        313.0,
    )
    before = source.at(stamp(DECISION))[0]
    after = source.at(stamp(AFTER_MONTHLY_RELEASE))[0]
    assert before is not None and after is not None
    assert before[11] == pytest.approx(math.log(312.0 / 303.0))
    assert after[11] == pytest.approx(math.log(313.0 / 304.0))


def test_the_exact_month_anchors_come_from_the_same_as_of_t_snapshot():
    records = fixture_records()
    # A later revision of the April 2023 CPI, available only after the decision.
    records["CPIAUCSL"].append(
        VintageRecord(stamp("2024-07-01T00:00:00"), date(2023, 4, 1), 999.0)
    )
    source = build(records)
    at_decision = source.at(stamp(DECISION))[0]
    assert at_decision is not None
    assert at_decision[11] == pytest.approx(math.log(312.0 / 303.0))
    # The revision exists in the substrate, and only its own availability boundary exposes it.
    assert source.snapshot("CPIAUCSL", stamp(DECISION)).values[date(2023, 4, 1)] == 303.0
    assert source.snapshot("CPIAUCSL", stamp("2024-07-02T12:00:00")).values[
        date(2023, 4, 1)
    ] == 999.0


def test_the_unemployment_anchor_is_exactly_three_calendar_months_earlier():
    source = build()
    current = source.current_release("UNRATE", stamp(DECISION))
    assert current is not None
    assert months_earlier(current[0], 3) == date(2024, 1, 1)
    values = source.at(stamp(DECISION))[0]
    assert values is not None and values[12] == pytest.approx(3.9 - 3.7)


def test_a_missing_exact_month_anchor_fails_closed_with_a_typed_reason():
    records = fixture_records()
    records["CPIAUCSL"] = [
        record for record in records["CPIAUCSL"] if record.observation != date(2023, 4, 1)
    ]
    values, reason = build(records).at(stamp(DECISION))
    assert values is None
    assert reason == "CPIAUCSL_12M_EXACT_ANCHOR_UNAVAILABLE"


def test_a_historical_anchor_outside_its_tolerance_fails_closed():
    records = fixture_records()
    # The 30-day anchor for 2024-06-15 is 2024-05-16; the nearest earlier observation is now
    # 2024-04-24, twenty-two days before it and well outside the seven-day tolerance.
    records["DFF"] = [
        record for record in records["DFF"] if record.observation != date(2024, 5, 16)
    ]
    values, reason = build(records).at(stamp(DECISION))
    assert values is None
    assert reason == "DFF_30D_HISTORICAL_ANCHOR_UNAVAILABLE"


def test_a_series_with_no_available_record_fails_closed_before_any_anchor():
    records = fixture_records()
    records["NFCI"] = [
        VintageRecord(stamp("2025-01-01T00:00:00"), date(2024, 12, 20), -0.2)
    ]
    values, reason = build(records).at(stamp(DECISION))
    assert values is None
    assert reason == "NFCI_CURRENT_RELEASE_STATE_UNAVAILABLE"


def test_a_non_positive_log_input_fails_closed():
    records = fixture_records()
    records["VIXCLS"] = daily(
        [("2024-05-21", 18.0), ("2024-06-10", 20.0), ("2024-06-14", 0.0)]
    )
    values, reason = build(records).at(stamp(DECISION))
    assert values is None
    assert reason == "VIXCLS_NON_POSITIVE_LEVEL"


def regular_calendar_records() -> dict[str, list[VintageRecord]]:
    """The same substrate with no hole in any release calendar."""
    records = fixture_records()
    records["DFF"] = daily([(f"2024-05-{day:02d}", 5.0) for day in range(1, 32)])
    records["DGS10"] = records["DFF"]
    records["T10Y2Y"] = records["DFF"]
    records["VIXCLS"] = records["DFF"]
    records["NFCI"] = daily([("2024-05-04", -0.4), ("2024-05-11", -0.4), ("2024-05-18", -0.4)])
    records["WALCL"] = records["NFCI"]
    records["CPIAUCSL"] = [
        VintageRecord(
            stamp(f"2024-{month:02d}-16T00:00:00"), date(2023, month, 1), 300.0 + month
        )
        for month in range(1, 13)
    ]
    records["UNRATE"] = [
        VintageRecord(stamp(f"2024-{month:02d}-16T00:00:00"), date(2023, month, 1), 3.5)
        for month in range(1, 13)
    ]
    return records


def test_the_source_cadence_gate_passes_a_regular_release_calendar():
    findings = cadence_findings(build(regular_calendar_records()))
    assert findings["limits"] == SOURCE_CADENCE_LIMIT_DAYS
    assert findings["by_series"]["CPIAUCSL"]["frequency"] == "MONTHLY"
    assert findings["by_series"]["CPIAUCSL"]["maximum_observation_gap_days"] == 31
    assert findings["by_series"]["NFCI"]["maximum_observation_gap_days"] == 7
    assert findings["passed"] is True


def test_the_source_cadence_gate_blocks_a_silently_frozen_series():
    records = fixture_records()
    records["DFF"] = daily([("2024-04-24", 4.8), ("2024-06-14", 5.5)])
    findings = cadence_findings(build(records))
    assert findings["by_series"]["DFF"]["maximum_observation_gap_days"] == 51
    assert findings["by_series"]["DFF"]["passed"] is False
    assert findings["passed"] is False


def test_a_misaligned_or_post_cutoff_decision_timestamp_is_refused():
    from app.predictive.macro_release_state_source import MacroReleaseStateError

    source = build()
    with pytest.raises(MacroReleaseStateError):
        source.at(stamp(DECISION) + 61)
    with pytest.raises(MacroReleaseStateError):
        source.at(stamp("2025-01-02T00:00:00"))
