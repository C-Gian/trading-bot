"""Order-flow substrate: aggregation semantics, eligibility, and oracle reconciliation."""

from __future__ import annotations

import json

import numpy as np
import pytest
from app.research.evaluation_protocol import HOUR_US, utc_us
from app.research.order_flow import (
    AGGREGATION,
    BALANCE,
    DATASET_ID,
    FEATURE_VERSION,
    FILES,
    MANIFEST_PATH,
    build_buckets,
    content_hash,
)
from app.research.wp004 import ROOT

MINUTE_US = 60_000_000
START = utc_us("2020-01-01T00:00:00Z")
RECONCILIATION = ROOT / "reports/validation/WP-007-ORDER-FLOW-RECONCILIATION.json"
DATA_AVAILABLE = (ROOT / "data/canonical/BTCUSDT-1m.parquet").is_file()


def _source(minutes: list[tuple[int, float, float]], *, offset: int = 0):
    """Build a synthetic canonical slice: (minute index, volume, taker base)."""
    times = np.asarray(
        [START + index * MINUTE_US + offset for index, _, _ in minutes], dtype=np.int64
    )
    volume = np.asarray([value for _, value, _ in minutes], dtype=float)
    taker = np.asarray([value for _, _, value in minutes], dtype=float)
    return {
        "times": times,
        "columns": {
            "open": np.full(len(minutes), 100.0),
            "close": np.full(len(minutes), 101.0),
            "volume": volume,
            "quote_volume": volume * 10.0,
            "taker_base": taker,
            "taker_quote": taker * 10.0,
        },
    }


def _full_hour(volume: float, taker: float, *, offset: int = 0):
    return _source([(index, volume, taker) for index in range(60)], offset=offset)


def test_share_is_a_ratio_of_sums_not_a_mean_of_minute_ratios():
    """One heavy sell-aggressed minute must outweigh 59 tiny fully-bought ones."""
    minutes = [(0, 1000.0, 100.0)] + [(index, 1.0, 1.0) for index in range(1, 60)]
    bucket = build_buckets("1h", _source(minutes))[0]
    assert bucket.share == pytest.approx((100.0 + 59.0) / (1000.0 + 59.0))
    assert bucket.share < BALANCE, "the heavy sell-aggressed minute must dominate"
    mean_of_ratios = (0.1 + 59 * 1.0) / 60
    assert mean_of_ratios > BALANCE, "a mean of minute ratios would say the opposite"
    assert bucket.share != pytest.approx(mean_of_ratios)


def test_a_complete_unquarantined_traded_bucket_is_eligible():
    bucket = build_buckets("1h", _full_hour(2.0, 1.5))[0]
    assert bucket.source_minutes == 60 and bucket.complete
    assert not bucket.quarantined and bucket.eligible
    assert bucket.share == pytest.approx(0.75)
    assert bucket.volume == pytest.approx(120.0) and bucket.taker_base == pytest.approx(90.0)


def test_an_incomplete_bucket_is_ineligible_and_never_filled():
    minutes = [(index, 1.0, 0.75) for index in range(40)]
    bucket = build_buckets("1h", _source(minutes))[0]
    assert bucket.source_minutes == 40 and not bucket.complete
    assert not bucket.eligible
    assert bucket.volume == pytest.approx(40.0), "a missing minute must not be filled"


def test_a_quarantined_bucket_is_ineligible():
    bucket = build_buckets("1h", _full_hour(1.0, 0.8, offset=30_000_000))[0]
    assert bucket.quarantined and not bucket.eligible


def test_a_zero_volume_bucket_has_a_null_share_and_is_ineligible():
    bucket = build_buckets("1h", _full_hour(0.0, 0.0))[0]
    assert bucket.share is None and not bucket.eligible
    assert bucket.volume == 0.0


def test_four_hour_buckets_aggregate_the_same_way():
    minutes = [(index, 1.0, 0.6) for index in range(240)]
    buckets = build_buckets("4h", _source(minutes))
    assert len(buckets) == 1
    assert buckets[0].source_minutes == 240 and buckets[0].complete and buckets[0].eligible
    assert buckets[0].share == pytest.approx(0.6)


def test_bucket_boundaries_are_utc_aligned():
    minutes = [(index, 1.0, 0.5) for index in range(120)]
    buckets = build_buckets("1h", _source(minutes))
    assert [bucket.open_us for bucket in buckets] == [START, START + HOUR_US]


def test_content_hash_changes_with_any_bucket_value():
    left = {"1h": build_buckets("1h", _full_hour(1.0, 0.5))}
    right = {"1h": build_buckets("1h", _full_hour(1.0, 0.6))}
    assert content_hash(left) != content_hash(right)
    assert content_hash(left) == content_hash({"1h": build_buckets("1h", _full_hour(1.0, 0.5))})


def test_committed_substrate_manifest_is_coherent():
    manifest = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    source = json.loads(
        (ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json").read_text(encoding="utf-8")
    )
    assert manifest["manifest_id"] == DATASET_ID
    assert manifest["feature_version"] == FEATURE_VERSION
    assert manifest["aggregation"] == AGGREGATION
    assert manifest["balance_point"] == BALANCE
    assert manifest["canonical_data_modified"] is False
    assert manifest["derived_from"]["content_hash"] == source["content_hash"]["value"]
    assert manifest["derived_from"]["canonical_sha256"] == source["files"]["canonical"]["sha256"]
    assert manifest["integrity_audit"]["status"] == "PASS"
    assert set(manifest["files"]) == set(FILES)
    for timeframe, relative in FILES.items():
        assert manifest["files"][timeframe]["path"] == relative
        assert manifest["integrity"][timeframe]["fills_or_repairs"] == 0
        assert manifest["eligible_counts"][timeframe] <= manifest["row_counts"][timeframe]


def test_committed_reconciliation_passes_bit_for_bit():
    report = json.loads(RECONCILIATION.read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["content_hash_match"] is True
    assert report["production_content_hash"] == manifest["content_hash"]["value"]
    assert report["substrate_content_hash"] == manifest["content_hash"]["value"]
    assert report["arithmetic"].startswith("EXACTLY_ROUNDED_FSUM")
    assert report["method"].endswith("SHARES_NO_AGGREGATION_CODE")
    for timeframe in FILES:
        item = report["timeframes"][timeframe]
        assert item["record_mismatches"] == 0
        assert item["bucket_count_match"] and item["eligible_count_match"]
        assert item["sampled_values_match"] and item["edge_values_match"]
        assert item["anomaly_values_match"]
        assert item["production_buckets"] == manifest["row_counts"][timeframe]
        assert item["production_eligible"] == manifest["eligible_counts"][timeframe]


def test_new_bucketing_agrees_with_the_already_accepted_derived_hours():
    cross = json.loads(RECONCILIATION.read_text(encoding="utf-8"))["accepted_1h_cross_check"]
    assert cross["status"] == "PASS"
    assert cross["price_mismatches"] == 0 and cross["structure_mismatches"] == 0
    assert cross["buckets_absent_from_accepted_file"] == 0
    assert cross["exact_open_close_structure_matches"] == cross["compared_buckets"]
    assert cross["maximum_absolute_volume_difference"] < 1e-6


@pytest.mark.skipif(not DATA_AVAILABLE, reason="installed development data required")
def test_substrate_reproduces_from_installed_canonical_data():
    from app.research.order_flow import build_substrate, read_buckets

    built = build_substrate(ROOT)
    stored = {timeframe: read_buckets(timeframe, ROOT) for timeframe in FILES}
    assert content_hash(built) == content_hash(stored)
    manifest = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    assert content_hash(built) == manifest["content_hash"]["value"]
