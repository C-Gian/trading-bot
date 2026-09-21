"""Post-result residual source finding for `PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1`.

This module changes nothing about the executed experiment. The frozen contract, search plan,
preregistrations, admission and both results are immutable and are not touched here.

It records, deterministically and additively, one defect found in the admitted ALFRED
substrate *after* the family had been executed and rejected: twenty `VIXCLS` rows carry an
`observation_date` later than their own `vintage_start`, so their conservative
`availability_time` precedes the day they describe. Every one of them falls on a US market
holiday whose value FRED published inside the preceding business day's vintage.

The V1 semantics never used such a row as the current level, because the retired rule took the
latest observation *on or before* the decision date. The V2 rule frozen in
`PREDICTIVE_MACRO_RELEASE_STATE_V1` takes the greatest observation date present in the as-of-`T`
snapshot and does not additionally require that date to be at or before `T`, so a small number
of decision instants read a `VIXCLS` level stamped one to two days ahead.

This is recorded, not repaired. Repairing it would be a third macro source semantics inside
`PREDICTIVE_RESEARCH_GENERATION_V1`, which the active work package forbids, and re-running the
family after its result is known is exactly the post-result redesign the Constitution forbids.
The direction of the defect matters for interpretation: a lookahead can only flatter a
candidate, and both candidates were rejected, so it cannot have manufactured the negative
result. It is referred to the Research Director as an open source-design question.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .macro_release_state_audit import canonical_timestamp_sets
from .macro_release_state_source import (
    SERIES,
    load_release_state_source,
    source_identity,
    verified_records,
)

ROOT = Path(__file__).resolve().parents[3]

RESIDUAL_PATH = (
    "reports/validation/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1-RESIDUAL-SOURCE-FINDING.json"
)
CHECKPOINT = "PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1"
FINDING_ID = "MACRO_RELEASE_STATE_FUTURE_DATED_OBSERVATION_V1"
DISPOSITION = "RECORDED_NOT_REPAIRED_REFERRED_TO_RESEARCH_DIRECTOR"
INCLUDED_FOLDS = ("2020", "2021", "2022", "2023", "2024")


def substrate_rows(root: Path = ROOT) -> list[dict[str, Any]]:
    """Every admitted row whose observation date is later than its own vintage start."""
    rows = []
    for row in verified_records(root):
        if row["observation_date"] <= row["vintage_start"]:
            continue
        rows.append(
            {
                "series_id": row["series_id"],
                "observation_date": row["observation_date"].isoformat(),
                "vintage_start": row["vintage_start"].isoformat(),
                "availability_time": row["availability_time"]
                .astimezone(UTC)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lead_days": (row["observation_date"] - row["vintage_start"]).days,
            }
        )
    return sorted(rows, key=lambda item: (item["series_id"], item["observation_date"]))


def _exposure(
    root: Path, instants: Sequence[int]
) -> tuple[int, list[dict[str, Any]], dict[str, int]]:
    source = load_release_state_source(root)
    affected = 0
    by_series: dict[str, int] = dict.fromkeys(SERIES, 0)
    detail: dict[tuple[str, str, str], int] = {}
    for instant in instants:
        decision_date = datetime.fromtimestamp(instant, UTC).date()
        hit = False
        for series in SERIES:
            current = source.current_release(series, instant)
            if current is None or current[0] <= decision_date:
                continue
            hit = True
            by_series[series] += 1
            key = (series, decision_date.isoformat(), current[0].isoformat())
            detail[key] = detail.get(key, 0) + 1
        if hit:
            affected += 1
    instances = [
        {
            "series_id": series,
            "decision_date": decision,
            "current_observation_date": observation,
            "decision_instants": count,
            "lead_days": (
                datetime.fromisoformat(observation).date() - datetime.fromisoformat(decision).date()
            ).days,
        }
        for (series, decision, observation), count in sorted(detail.items())
    ]
    return affected, instances, by_series


def residual_finding(root: Path = ROOT) -> dict[str, Any]:
    """The complete, deterministic record of the residual. It reads no BTC outcome."""
    folds, _, _ = canonical_timestamp_sets(root)
    evaluation = sorted({moment for name in INCLUDED_FOLDS for moment in folds[name]["evaluation"]})
    training = sorted({moment for name in INCLUDED_FOLDS for moment in folds[name]["training"]})
    rows = substrate_rows(root)
    evaluation_affected, evaluation_instances, evaluation_by_series = _exposure(root, evaluation)
    training_affected, _, training_by_series = _exposure(root, training)
    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_RESIDUAL_SOURCE_FINDING_V1",
        "finding_id": FINDING_ID,
        "checkpoint": CHECKPOINT,
        "found": "AFTER_EXECUTION_AND_AFTER_BOTH_CONFIGURATIONS_WERE_REJECTED",
        "disposition": DISPOSITION,
        "source": source_identity(root),
        "defect": {
            "description": (
                "An admitted substrate row whose observation_date is later than its own "
                "vintage_start, so the conservative availability_time precedes the calendar "
                "day the observation describes."
            ),
            "substrate_rows": len(rows),
            "affected_series": sorted({row["series_id"] for row in rows}),
            "maximum_lead_days": max((row["lead_days"] for row in rows), default=0),
            "rows": rows,
        },
        "semantics_interaction": {
            "v1_current_anchor_rule": "LATEST_OBSERVATION_ON_OR_BEFORE_THE_DECISION_DATE",
            "v1_could_use_a_future_dated_observation_as_current": False,
            "v2_current_state_rule": "GREATEST_OBSERVATION_DATE_IN_THE_AS_OF_T_SNAPSHOT",
            "v2_requires_observation_date_at_or_before_decision_date": False,
            "introduced_by_this_checkpoint": True,
            "present_in_the_frozen_contract_text": True,
        },
        "exposure": {
            "included_folds": list(INCLUDED_FOLDS),
            "evaluation_decision_instants": len(evaluation),
            "evaluation_instants_affected": evaluation_affected,
            "evaluation_share_affected": (
                evaluation_affected / len(evaluation) if evaluation else 0.0
            ),
            "evaluation_instants_by_series": evaluation_by_series,
            "training_decision_instants": len(training),
            "training_instants_affected": training_affected,
            "training_share_affected": training_affected / len(training) if training else 0.0,
            "training_instants_by_series": training_by_series,
            "evaluation_instances": evaluation_instances,
        },
        "interpretation": {
            "direction": "A_LOOKAHEAD_CAN_ONLY_FLATTER_A_CANDIDATE",
            "both_configurations_rejected": True,
            "negative_result_weakened_by_the_defect": False,
            "result_rewritten": False,
            "family_re_executed": False,
            "third_source_semantics_created": False,
            "coverage_gate_changed": False,
            "requires_research_director_decision": True,
        },
        "boundaries": {
            "btc_outcomes_read": False,
            "model_predictions_read": False,
            "predecessor_records_modified": False,
            "committed_result_modified": False,
            "sealed_queries": 0,
            "real_money": False,
        },
    }


__all__ = [
    "CHECKPOINT",
    "DISPOSITION",
    "FINDING_ID",
    "INCLUDED_FOLDS",
    "RESIDUAL_PATH",
    "residual_finding",
    "substrate_rows",
]
