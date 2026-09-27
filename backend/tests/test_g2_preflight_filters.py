"""G2-02 data-integrity preflight mechanics and pinned exchangeInfo filters (no market data needed)."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from app.g2 import preflight
from app.g2.sources import (
    EXCHANGE_INFO_MANIFEST,
    UnauthorizedObservationError,
    normalized_filters,
    pinned_market_filters,
    symbol_object_sha256,
)
from test_g2_data_boundary import fake_root  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]


def test_gap_runs_and_incomplete_bar_counting():
    present = np.ones(preflight.TOTAL_MINUTES, dtype=bool)
    present[10] = False
    present[1000:1003] = False
    runs = preflight._gap_runs(present)
    assert runs == [(10, 1), (1000, 3)]
    grid = preflight._gaps_and_bars(present)
    assert grid["missing_minutes"] == 4 and grid["gap_runs"] == 2
    assert grid["longest_gap"] == {"start": "2020-01-01T16:40:00+00:00", "minutes": 3}
    assert grid["gap_count_by_length"]["1-1"] == 1 and grid["gap_count_by_length"]["2-5"] == 1
    assert grid["bars"]["15m"]["incomplete_partial"] == 2
    assert grid["bars"]["4h"]["incomplete_partial"] == 2
    assert grid["bars"]["1h"]["absent"] == 0


class FundingStub:
    def __init__(self, rows):
        self.rows = rows

    def funding(self):
        return self.rows


def test_funding_grid_audit_detects_missing_duplicates_and_off_grid():
    start = preflight.START
    grid = []
    moment = start
    while moment < preflight.END:
        grid.append((moment, 0.0001))
        moment += timedelta(hours=8)
    clean = preflight._audit_funding(FundingStub(grid))
    assert clean["historical_8h_grid_assumption_valid"] is True
    assert clean["missing_expected_settlements"] == [] and clean["expected_8h_settlements"] == len(
        grid
    )
    broken = [row for row in grid if row[0] != start + timedelta(hours=16)]
    broken.append((start + timedelta(hours=8, milliseconds=1), 0.0002))  # same settlement minute
    broken.append((start + timedelta(hours=9), 0.0001))  # off grid
    broken.sort()
    audit = preflight._audit_funding(FundingStub(broken))
    assert audit["historical_8h_grid_assumption_valid"] is False
    assert audit["missing_expected_settlements"] == [(start + timedelta(hours=16)).isoformat()]
    assert audit["duplicate_settlement_minutes"] == 1
    assert audit["off_grid_settlements"] == [(start + timedelta(hours=9)).isoformat()]
    assert audit["timestamp_precision"]["SUB_SECOND_OFFSET"] == 1


def test_missing_source_objects_block_the_preflight_without_narrowing(fake_root):  # noqa: F811
    payload = preflight.build(fake_root)
    assert payload["status"] == "BLOCKED_MISSING_SOURCE_OBJECTS"
    objects = payload["klines"]["objects"]
    assert "2020-01" in objects["months_missing_from_manifest"]
    assert len(objects["months_missing_from_manifest"]) == 58
    assert "minute_grid" not in payload and payload["protected_objects_opened"] is False
    assert not any(payload["claims"].values())


def test_committed_preflight_artifact_claims_are_non_economic():
    artifact = json.loads((ROOT / preflight.ARTIFACT_PATH).read_text(encoding="utf-8"))
    assert artifact["ledger_declaration"] == preflight.LEDGER_DECLARATION
    assert artifact["protected_objects_opened"] is False and not any(artifact["claims"].values())
    assert artifact["interval"] == ["2020-01-01T00:00:00+00:00", "2025-01-01T00:00:00+00:00"]
    assert all("2025" not in path for path in artifact["opened_objects"])
    serialized = json.dumps({k: v for k, v in artifact.items() if k != "claims"}).lower()
    for word in ("sharpe", "profit_factor", 'pnl":', "net_r"):
        assert word not in serialized


def test_pinned_filters_come_from_filters_not_precision_fields():
    record = json.loads((ROOT / EXCHANGE_INFO_MANIFEST).read_text(encoding="utf-8"))
    assert record["status"] == "PINNED" and record["credentials_used"] is False
    assert record["endpoint"] == "https://fapi.binance.com/fapi/v1/exchangeInfo"
    assert datetime.fromisoformat(record["retrieval_utc"]).tzinfo is not None
    assert len(record["raw_snapshot_sha256"]) == 64
    symbol = record["symbol_object"]
    assert symbol_object_sha256(symbol) == record["symbol_object_sha256"]
    assert normalized_filters(symbol) == record["normalized"]
    assert record["normalized"]["contract_type"] == "PERPETUAL"
    assert record["normalized"]["status"] == "TRADING"
    filters = pinned_market_filters(ROOT)
    market = record["normalized"]["market_lot_size"]
    assert (filters.step_size, filters.min_qty, filters.max_qty) == (
        market["stepSize"],
        market["minQty"],
        market["maxQty"],
    )
    assert filters.tick_size == record["normalized"]["price_filter"]["tickSize"]
    assert filters.min_notional == record["normalized"]["min_notional"]
    # a precision-only change must not affect the normalized filters
    altered = copy.deepcopy(symbol)
    altered["pricePrecision"] = 0
    altered["quantityPrecision"] = 0
    assert normalized_filters(altered) == record["normalized"]


def test_tampered_pinned_snapshot_is_refused(tmp_path):
    record = json.loads((ROOT / EXCHANGE_INFO_MANIFEST).read_text(encoding="utf-8"))
    record["symbol_object"]["filters"][0]["tickSize"] = "1.00"
    target = tmp_path / EXCHANGE_INFO_MANIFEST
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(UnauthorizedObservationError):
        pinned_market_filters(tmp_path)


def test_preflight_interval_cannot_reach_protected_data():
    assert preflight.END == datetime(2025, 1, 1, tzinfo=UTC)
