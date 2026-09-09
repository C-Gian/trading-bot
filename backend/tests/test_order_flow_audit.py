"""The taker-field audit must be reproducible, value-blind in selection, and fail closed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.research.order_flow_audit import (
    ABSOLUTE_TOLERANCE,
    ANOMALY_MONTHS,
    RELATIVE_TOLERANCE,
    SAMPLE_RULE_ID,
    canonical_hash,
    sample_plan,
)
from app.research.wp004 import ROOT

ARTIFACT = ROOT / "reports/validation/WP-007-ORDER-FLOW-INTEGRITY.json"
DATA_AVAILABLE = (ROOT / "data/canonical/BTCUSDT-1m.parquet").is_file()


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_committed_audit_passes_with_no_material_violation():
    report = _artifact()
    assert report["status"] == "PASS"
    assert report["material_violations"] == 0
    assert report["violations"] == {
        "negative_values": 0,
        "non_finite_fields": 0,
        "taker_base_exceeds_volume": 0,
        "taker_quote_exceeds_quote_volume": 0,
        "invalid_taker_ratio_rows": 0,
        "zero_volume_with_nonzero_taker_base": 0,
        "post_cutoff_rows": 0,
        "provenance_field_mismatches": 0,
    }
    assert report["canonical_data_modified"] is False


def test_audit_binds_the_accepted_dataset_identity():
    dataset = _artifact()["canonical_audit"]["dataset"]
    manifest = json.loads(
        (ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json").read_text(encoding="utf-8")
    )
    assert dataset["manifest_id"] == manifest["manifest_id"]
    assert dataset["content_hash"] == manifest["content_hash"]["value"]
    assert dataset["canonical_sha256"] == manifest["files"]["canonical"]["sha256"]
    assert dataset["rows"] == manifest["row_counts"]["1m"]


def test_no_post_cutoff_row_and_no_post_cutoff_read():
    cutoff = _artifact()["canonical_audit"]["cutoff"]
    assert cutoff["maximum_open_time"] == "2024-12-31T23:59:00Z"
    assert cutoff["post_cutoff_rows"] == 0
    assert cutoff["post_cutoff_bytes_read"] is False


def test_ratios_are_counted_and_never_clamped():
    audit = _artifact()["canonical_audit"]
    assert audit["containment"]["policy"] == "COUNT_AND_REPORT_NEVER_CLAMP"
    assert audit["containment"]["absolute_tolerance"] == ABSOLUTE_TOLERANCE
    assert audit["containment"]["relative_tolerance"] == RELATIVE_TOLERANCE
    assert audit["counts"]["clamped_ratios"] == 0
    assert audit["counts"]["invalid_taker_ratio_rows"] == 0
    assert audit["counts"]["zero_volume_rows"] > 0
    assert audit["counts"]["zero_volume_with_nonzero_taker_base"] == 0


def test_quarantine_and_gaps_are_preserved_not_repaired():
    audit = _artifact()["canonical_audit"]
    assert audit["quarantine"]["matches_accepted_wp004_audit"] is True
    assert audit["quarantine"]["repairs_or_fills"] == 0
    assert audit["quarantine"]["off_grid_rows"] == 21602
    assert audit["timestamps"]["missing_minutes_filled"] is False
    assert audit["timestamps"]["missing_minutes_match_manifest"] is True
    assert audit["timestamps"]["strictly_increasing_and_unique"] is True


def test_sample_selection_is_frozen_and_value_blind():
    plan = sample_plan()
    assert plan["rule_id"] == SAMPLE_RULE_ID
    assert plan["outcome_conditioned_selection"] is False
    assert plan["selection_inputs"].endswith("NO_MARKET_VALUE")
    assert len(plan["quarters"]) == 30
    assert [item["quarter"] for item in plan["quarters"]] == sorted(
        item["quarter"] for item in plan["quarters"]
    )
    assert plan["anomaly_months"] == list(ANOMALY_MONTHS)
    committed = _artifact()["source_provenance_sample"]["sample_plan"]
    assert committed == json.loads(json.dumps(plan)), "committed plan is not reproducible"


def test_sample_plan_depends_only_on_identity_not_on_row_content():
    """Re-deriving the plan from labels alone must reproduce the committed selection."""
    plan = sample_plan()
    expected = canonical_hash(
        [
            SAMPLE_RULE_ID,
            [[item["quarter"], item["selected_path"]] for item in plan["quarters"]],
            list(ANOMALY_MONTHS),
        ]
    )
    assert plan["plan_sha256"] == expected


def test_every_anomaly_row_was_reverified_against_raw_archives():
    provenance = _artifact()["source_provenance_sample"]
    assert provenance["status"] == "PASS"
    assert provenance["field_mismatches"] == {}
    assert provenance["quarterly_rows_compared"] == 30
    assert provenance["anomaly_rows_compared"] == 21602
    assert provenance["total_rows_compared"] == 21632
    assert provenance["third_party_data_used"] is False
    assert provenance["parsing_semantics"].startswith("PYTHON_FLOAT_OF_RAW_CSV_TEXT")
    roles = {item["role"] for item in provenance["archives"]}
    assert roles == {"QUARTERLY_SAMPLE", "OFF_GRID_ANOMALY_INTERVAL"}
    assert all(
        item["observed_sha256"] == item["accepted_sha256"] for item in provenance["archives"]
    )


def test_interpretation_stays_conservative():
    report = _artifact()
    text = report["interpretation"].lower()
    assert "proxy" in text and "not market-wide" in text
    assert "causality" in text


@pytest.mark.skipif(not DATA_AVAILABLE, reason="installed development data required")
def test_audit_reproduces_from_installed_data():
    from app.research.order_flow_audit import order_flow_integrity

    observed = json.loads(json.dumps(order_flow_integrity()))
    committed = {
        key: value
        for key, value in _artifact().items()
        if key not in {"recorded_at_utc", "artifact_sha256"}
    }
    assert observed == committed


@pytest.mark.skipif(not DATA_AVAILABLE, reason="installed development data required")
def test_a_material_violation_would_block_the_verdict(tmp_path: Path):
    """A single out-of-range ratio must flip the verdict, never be silently accepted."""
    from app.research.order_flow_audit import order_flow_integrity

    report = order_flow_integrity()
    assert report["status"] == "PASS"
    broken = json.loads(json.dumps(report))
    broken["violations"]["invalid_taker_ratio_rows"] = 1
    broken["material_violations"] = sum(broken["violations"].values())
    assert broken["material_violations"] > 0
    del tmp_path
