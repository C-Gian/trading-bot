from __future__ import annotations

import math
from datetime import UTC, date, datetime

import pytest
from app.predictive.macro_vintage_source import (
    FEATURE_NAMES,
    MacroVintageSource,
    VintageRecord,
)


def stamp(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp())


def source_with_later_revision() -> MacroVintageSource:
    decision = stamp("2024-06-15T12:00:00")
    before = decision - 86_400
    records: dict[str, list[VintageRecord]] = {
        "DFF": [
            VintageRecord(before, date(2024, 5, 16), 5.0),
            VintageRecord(before, date(2024, 6, 15), 5.5),
            VintageRecord(decision + 86_400, date(2024, 6, 15), 99.0),
        ],
        "DGS10": [
            VintageRecord(before, date(2024, 5, 16), 4.0),
            VintageRecord(before, date(2024, 6, 15), 4.2),
        ],
        "T10Y2Y": [
            VintageRecord(before, date(2024, 5, 16), -0.5),
            VintageRecord(before, date(2024, 6, 15), -0.2),
        ],
        "VIXCLS": [
            VintageRecord(before, date(2024, 6, 10), 20.0),
            VintageRecord(before, date(2024, 6, 15), 22.0),
        ],
        "NFCI": [
            VintageRecord(before, date(2024, 5, 18), -0.4),
            VintageRecord(before, date(2024, 6, 15), -0.1),
        ],
        "WALCL": [
            VintageRecord(before, date(2024, 5, 18), 7_000_000.0),
            VintageRecord(before, date(2024, 6, 15), 7_070_000.0),
        ],
        "CPIAUCSL": [
            VintageRecord(before, date(2023, 6, 1), 300.0),
            VintageRecord(before, date(2024, 6, 1), 309.0),
        ],
        "UNRATE": [
            VintageRecord(before, date(2024, 3, 1), 3.8),
            VintageRecord(before, date(2024, 6, 1), 4.0),
        ],
    }
    return MacroVintageSource(records)


def test_the_frozen_feature_vector_has_exact_order_and_values():
    source = source_with_later_revision()
    values, reason = source.at(stamp("2024-06-15T12:00:00"))
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
            math.log(309.0 / 300.0),
            0.2,
        )
    )


def test_a_later_revision_cannot_change_an_earlier_vector():
    source = source_with_later_revision()
    earlier = source.at(stamp("2024-06-15T12:00:00"))[0]
    later = source.at(stamp("2024-06-17T12:00:00"))[0]
    assert earlier is not None and later is not None
    assert earlier[0] == 5.5
    assert later[0] == 99.0


def test_a_stale_anchor_fails_closed_with_a_typed_reason():
    source = source_with_later_revision()
    values, reason = source.at(stamp("2024-07-31T12:00:00"))
    assert values is None
    assert reason is not None and reason.endswith("ANCHOR_UNAVAILABLE_OR_STALE")
