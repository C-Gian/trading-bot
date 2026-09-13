"""Data-independent structural tests for PERPETUAL_FUNDING_CONTEXT_V1."""

from __future__ import annotations

import json

import pytest
from app.research.evaluation_protocol import HOUR_US
from app.research.funding import (
    CUTOFF_MS,
    ENDPOINT,
    FEATURE,
    LIMIT,
    START_MS,
    FundingContextSource,
    FundingDataError,
    parse_response,
    request_params,
)


def test_strictly_prior_asof_excludes_same_timestamp() -> None:
    first = 1_600_000_000_000_000
    source = FundingContextSource([first, first + 8 * HOUR_US], [0.0001, -0.0002])
    with pytest.raises(FundingDataError, match="no strictly prior"):
        source.at(first)
    assert source.at(first + HOUR_US) == (first, 0.0001)
    assert source.at(first + 8 * HOUR_US) == (first, 0.0001)
    assert source.at(first + 9 * HOUR_US) == (first + 8 * HOUR_US, -0.0002)


def test_parser_rejects_duplicates_backwards_and_post_cutoff() -> None:
    def body(times: list[int]) -> bytes:
        return json.dumps(
            [
                {
                    "symbol": "BTCUSDT",
                    "fundingTime": value,
                    "fundingRate": "0.0001",
                    "markPrice": "1",
                }
                for value in times
            ]
        ).encode()

    assert parse_response(body([1, 2]))[0] == {
        "funding_time_ms": 1,
        "funding_rate_text": "0.0001",
    }
    for values in ([1, 1], [2, 1], [CUTOFF_MS + 1]):
        with pytest.raises(FundingDataError):
            parse_response(body(values))


def test_request_identity_is_frozen_and_credential_free() -> None:
    params = request_params(START_MS)
    assert params == {
        "symbol": "BTCUSDT",
        "startTime": START_MS,
        "endTime": CUTOFF_MS,
        "limit": LIMIT,
    }
    assert ENDPOINT == "https://fapi.binance.com/fapi/v1/fundingRate"
    assert FEATURE == "LATEST_SETTLED_FUNDING_RATE"
    assert all(word not in json.dumps(params).lower() for word in ("key", "secret", "signature"))
