"""Backend-owned review bundle for one on-demand product analysis."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from .execution_v2 import PAPER_EXECUTION_VERSION

ANALYSIS_REVIEW_BUNDLE_VERSION = "DASHBOARD_ANALYSIS_REVIEW_BUNDLE_V1"

_ANALYSIS_FIELDS = (
    "decision",
    "analysis_id",
    "strategy_version",
    "variant",
    "research_status",
    "champion_status",
    "analysis_version",
    "feature_version",
)
_PAPER_FIELDS = (
    "trade_id",
    "status",
    "evidence_stage",
    "initiation_mode",
    "execution_model_version",
    "signal_timestamp",
    "analysis_completed_at",
    "intent_persisted_at",
    "signal_age_seconds",
    "entry_not_before",
    "entry_time",
    "entry_price",
    "stop_price",
    "target_price",
    "expiry_time",
    "exit_time",
    "exit_price",
    "exit_reason",
    "net_r",
    "resolution_detail",
)
_GATES = (
    (
        "direction_gate_status",
        "persistent_up",
        "Direzione del mercato",
        "Il contesto direzionale è favorevole.",
        "Il contesto direzionale non è favorevole.",
    ),
    (
        "movement_strength_gate_status",
        "breakout",
        "Forza del movimento",
        "Il movimento ha forza sufficiente.",
        "Il movimento non ha forza sufficiente.",
    ),
    (
        "volume_participation_gate_status",
        "participation",
        "Conferma dai volumi",
        "La partecipazione conferma il movimento.",
        "La partecipazione non conferma il movimento.",
    ),
)


def _present(source: Mapping[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    """Copy only authoritative fields that actually exist on the source object."""
    return {key: source[key] for key in keys if key in source}


def _related_paper(
    analysis_id: object, paper_records: Iterable[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    if not isinstance(analysis_id, str) or not analysis_id:
        return None
    matches = [record for record in paper_records if record.get("analysis_id") == analysis_id]
    return matches[-1] if matches else None


def analysis_review_payload(
    analysis: Mapping[str, Any], paper_records: Iterable[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    """Build a compact bundle without copying an indicative pre-acceptance plan."""
    payload: dict[str, Any] = {
        "bundle_version": ANALYSIS_REVIEW_BUNDLE_VERSION,
        **_present(analysis, _ANALYSIS_FIELDS),
    }
    if "signal_time" in analysis:
        payload["signal_timestamp"] = analysis["signal_time"]
    if "data_status" in analysis:
        payload["data_quality"] = analysis["data_status"]
    if "data_detail" in analysis:
        payload["data_detail"] = analysis["data_detail"]

    features = analysis.get("features")
    reasons: list[dict[str, str]] = []
    if isinstance(features, Mapping):
        for output_key, feature_key, label, pass_reason, fail_reason in _GATES:
            value = features.get(feature_key)
            if isinstance(value, bool):
                status = "PASS" if value else "FAIL"
                payload[output_key] = status
                reasons.append(
                    {
                        "gate": label,
                        "status": status,
                        "reason": pass_reason if value else fail_reason,
                    }
                )
    if reasons:
        payload["owner_facing_reasons"] = reasons

    decision = analysis.get("decision")
    if decision == "LONG":
        payload["paper_execution_version"] = PAPER_EXECUTION_VERSION

    related = _related_paper(analysis.get("analysis_id"), paper_records)
    if related is None:
        payload["paper_trade"] = None
    else:
        paper = _present(related, _PAPER_FIELDS)
        payload["paper_trade"] = paper
        if "status" in paper:
            payload["current_related_paper_status"] = paper["status"]
        if "evidence_stage" in paper:
            payload["evidence_classification"] = paper["evidence_stage"]
    return payload


def build_analysis_review_bundle(
    analysis: Mapping[str, Any], paper_records: Iterable[Mapping[str, Any]] = ()
) -> str:
    """Serialize the authoritative bundle deterministically for the clipboard."""
    return json.dumps(
        analysis_review_payload(analysis, paper_records),
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    )


__all__ = [
    "ANALYSIS_REVIEW_BUNDLE_VERSION",
    "analysis_review_payload",
    "build_analysis_review_bundle",
]
