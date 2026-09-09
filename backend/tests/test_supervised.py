from __future__ import annotations

from datetime import UTC, datetime
from math import log, sqrt

import pytest
from app.research.evaluation_protocol import HOUR_US, utc_us
from app.research.supervised import (
    CONTEXT_US,
    FULL_FEATURES,
    NO_FLOW_FEATURES,
    ContextBar,
    HourBar,
    SupervisedDataError,
    SupervisedFeatureSource,
    load_supervised_protocol,
)


def source(signal_us: int) -> SupervisedFeatureSource:
    hours = tuple(
        HourBar(
            signal_us - offset * HOUR_US,
            100.0 + (25 - offset),
            102.0 + (25 - offset),
            101.0 + (25 - offset),
            10.0 + (25 - offset),
            0.51 + (25 - offset) / 1000,
            True,
        )
        for offset in range(25, 0, -1)
    )
    context_latest = (signal_us - 5 * HOUR_US) // CONTEXT_US * CONTEXT_US
    context = tuple(
        ContextBar(
            context_latest - offset * CONTEXT_US,
            200.0 + (42 - offset),
            0.52,
            True,
        )
        for offset in range(42, -1, -1)
    )
    return SupervisedFeatureSource(hours, context)


def test_exact_feature_order_and_values() -> None:
    signal = utc_us(datetime(2020, 1, 2, tzinfo=UTC))
    row = source(signal).at(signal)
    assert len(FULL_FEATURES) == 8 and NO_FLOW_FEATURES == FULL_FEATURES[:6]
    assert row.feature_available_us == signal
    assert row.context_close_us <= signal - HOUR_US
    current_open, current_close = 124.0, 125.0
    closes = [101.0 + index for index in range(25)]
    returns = [log(closes[index] / closes[index - 1]) for index in range(1, 25)]
    assert row.values[0] == pytest.approx(log(current_close / current_open))
    assert row.values[1] == pytest.approx(log(current_close / closes[0]))
    assert row.values[2] == pytest.approx(log(current_close / 125.0))
    assert row.values[3] == pytest.approx(sqrt(sum(value * value for value in returns) / 24))
    assert row.values[4] == pytest.approx(log(34.0 / 21.5))
    assert row.values[5] == pytest.approx(1.0)
    assert row.values[6] == pytest.approx(0.034)
    assert row.values[7] == pytest.approx(0.02)


def test_future_and_incomplete_feature_injections_fail_closed() -> None:
    signal = utc_us(datetime(2020, 1, 2, tzinfo=UTC))
    valid = source(signal)
    with pytest.raises(SupervisedDataError, match="post-cutoff"):
        valid.at(utc_us("2025-01-01T00:00:00Z"))
    hours = list(valid.hourly.values())
    hours[-1] = HourBar(**{**hours[-1].__dict__, "eligible": False})
    with pytest.raises(SupervisedDataError, match="incomplete or quarantined"):
        SupervisedFeatureSource(tuple(hours), tuple(valid.context.values())).at(signal)
    future_substitution = (
        *list(valid.hourly.values())[:-1],
        HourBar(signal, 1.0, 1.0, 1.0, 1.0, 0.5, True),
    )
    with pytest.raises(SupervisedDataError, match="incomplete or quarantined"):
        SupervisedFeatureSource(future_substitution, tuple(valid.context.values())).at(signal)


def test_protocol_is_exact() -> None:
    document = load_supervised_protocol()
    assert document["training"]["purge_boundary_hours"] == 216
    assert document["model"]["signal_rule"] == "predicted_default_net_R > 0.0"
