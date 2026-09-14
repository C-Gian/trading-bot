from __future__ import annotations

import json

from app.product.analysis_review import (
    ANALYSIS_REVIEW_BUNDLE_VERSION,
    analysis_review_payload,
    build_analysis_review_bundle,
)
from app.product.execution_v2 import PAPER_EXECUTION_VERSION


def _analysis(decision: str = "NO_TRADE") -> dict[str, object]:
    return {
        "decision": decision,
        "analysis_id": "a" * 64,
        "signal_time": "2026-09-14T10:00:00Z",
        "strategy_version": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
        "variant": "ALIGNED",
        "research_status": "PAPER_RESEARCH_CANDIDATE",
        "champion_status": "NONE",
        "analysis_version": "PAPER_RESEARCH_ANALYSIS_V1",
        "feature_version": "CONTINUATION_FEATURES_V2",
        "data_status": "OK",
        "data_detail": "completed contiguous lookback available",
        "features": {
            "persistent_up": True,
            "breakout": False,
            "participation": False,
            "relative_volume": 0.7,
        },
        # This plan is indicative before acceptance and must never enter the bundle.
        "plan": {
            "reference_price": 100.0,
            "stop_price": 98.0,
            "target_price": 104.0,
        },
        "reference_price": 100.0,
    }


def test_no_trade_bundle_is_deterministic_and_contains_no_paper_plan() -> None:
    analysis = _analysis()
    first = build_analysis_review_bundle(analysis)
    second = build_analysis_review_bundle(dict(reversed(list(analysis.items()))))
    assert first == second

    payload = json.loads(first)
    assert payload["bundle_version"] == ANALYSIS_REVIEW_BUNDLE_VERSION
    assert payload["decision"] == "NO_TRADE"
    assert payload["signal_timestamp"] == "2026-09-14T10:00:00Z"
    assert payload["data_quality"] == "OK"
    assert payload["direction_gate_status"] == "PASS"
    assert payload["movement_strength_gate_status"] == "FAIL"
    assert payload["volume_participation_gate_status"] == "FAIL"
    assert payload["paper_trade"] is None
    assert "paper_execution_version" not in payload
    assert "plan" not in payload
    assert "reference_price" not in payload
    assert "stop_price" not in first and "target_price" not in first


def test_long_before_acceptance_declares_execution_version_but_no_prices() -> None:
    payload = analysis_review_payload(_analysis("LONG"))
    assert payload["paper_execution_version"] == PAPER_EXECUTION_VERSION
    assert payload["paper_trade"] is None
    for forbidden in ("reference_price", "entry_price", "stop_price", "target_price"):
        assert forbidden not in payload


def test_related_paper_state_is_copied_only_from_the_persisted_record() -> None:
    paper = {
        "trade_id": "PAPER-V2-abc",
        "analysis_id": "a" * 64,
        "status": "PENDING_ENTRY",
        "evidence_stage": "MANUAL_PROSPECTIVE_PAPER",
        "initiation_mode": "OWNER_MANUAL",
        "execution_model_version": PAPER_EXECUTION_VERSION,
        "signal_timestamp": "2026-09-14T10:00:00Z",
        "analysis_completed_at": "2026-09-14T10:23:17Z",
        "intent_persisted_at": "2026-09-14T10:23:17.500000Z",
        "signal_age_seconds": 1397.5,
        "entry_not_before": "2026-09-14T10:24:00Z",
        "entry_time": None,
        "entry_price": None,
        "stop_price": None,
        "target_price": None,
        "expiry_time": None,
        "secret_internal_cursor": "must not leak",
    }
    payload = analysis_review_payload(_analysis("LONG"), [paper])
    assert payload["current_related_paper_status"] == "PENDING_ENTRY"
    assert payload["evidence_classification"] == "MANUAL_PROSPECTIVE_PAPER"
    assert payload["paper_trade"]["entry_price"] is None
    assert payload["paper_trade"]["entry_not_before"] == "2026-09-14T10:24:00Z"
    assert "secret_internal_cursor" not in payload["paper_trade"]


def test_absent_optional_values_are_not_invented() -> None:
    payload = analysis_review_payload({"decision": "NO_TRADE"})
    assert payload == {
        "bundle_version": ANALYSIS_REVIEW_BUNDLE_VERSION,
        "decision": "NO_TRADE",
        "paper_trade": None,
    }
