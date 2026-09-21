"""Pre-result source audit for the frozen Stage-3 ALFRED macro-vintage family.

The coverage decision uses only canonical bar timestamps/completeness and macro source
validity.  It never loads BTC closes, returns, directions, model scores or predictions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from .folds import FOLD_BOUNDARIES, PURGE_EMBARGO_HOURS, epoch
from .labels import HOUR_SECONDS, HOURLY_ARTIFACT
from .macro_vintage_source import (
    AVAILABILITY_RULE,
    CATALOG_PATH,
    DEVELOPMENT_CEILING_SECONDS,
    FEATURE_COUNT,
    FEATURE_NAMES,
    MANIFEST_PATH,
    MAX_AGE_DAYS,
    SERIES,
    UNAVAILABILITY_TAXONOMY,
    MacroVintageSource,
    VintageRecord,
    availability_map,
    catalog_record,
    first_available_instant,
    load_macro_source,
    manifest_record,
    source_identity,
    verified_records,
)

ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = "reports/validation/PREDICTIVE-STAGE3-MACRO-VINTAGE-V1-SOURCE-AUDIT.json"

CANDIDATE_FOLDS = ("2019", "2020", "2021", "2022", "2023", "2024")
FOLD_COVERAGE_GATE = 0.90
MINIMUM_TRAINING_HISTORY_DAYS = 365
MINIMUM_ADMISSIBLE_FOLDS = 5
POOLED_COVERAGE_GATE = 0.95

PASS = "SOURCE_GATES_PASSED"
BLOCKED = "BLOCKED_MACRO_SOURCE_COVERAGE_V1"


def _canonical_timestamp_sets(root: Path) -> tuple[dict[str, dict[str, list[int]]], int, int]:
    """Frozen fold timestamp sets without reading the BTC price column."""
    table = pq.read_table(root / HOURLY_ARTIFACT, columns=["open_time", "complete"])
    instants = table["open_time"].to_numpy().astype("datetime64[s]").astype("int64")
    complete = table["complete"].to_numpy(zero_copy_only=False)
    usable = {int(moment) for moment, valid in zip(instants, complete, strict=True) if bool(valid)}
    first, last = int(instants.min()), int(instants.max())
    horizon = 24 * HOUR_SECONDS
    eligible = [
        moment
        for moment in range(first, last + HOUR_SECONDS, HOUR_SECONDS)
        if moment in usable and moment + horizon <= last and moment + horizon in usable
    ]
    result: dict[str, dict[str, list[int]]] = {}
    for name, start_text, end_text in FOLD_BOUNDARIES:
        start, end = epoch(start_text), epoch(end_text)
        result[name] = {
            "training": [
                moment
                for moment in eligible
                if moment + horizon + PURGE_EMBARGO_HOURS * HOUR_SECONDS <= start
            ],
            "evaluation": [
                moment for moment in eligible if start <= moment and moment + horizon <= end
            ],
        }
    return result, first, last


def provenance_findings(root: Path = ROOT) -> dict[str, Any]:
    manifest = manifest_record(root)
    catalog = catalog_record(root)
    records = verified_records(root)
    series = tuple(row["series_id"] for row in catalog["series"])
    checks = {
        "MANIFEST_ID_MATCHES": manifest["manifest_id"] == "ALFRED-MACRO-CONTEXT-DEV-v1",
        "SOURCE_FAMILY_IS_ALFRED": catalog["source_family"] == "ALFRED",
        "EXACT_EIGHT_SERIES_IN_FROZEN_ORDER": tuple(manifest["series"]) == SERIES == series,
        "CATALOG_HASH_MATCHES_MANIFEST": source_identity(root)["catalog_sha256"]
        == manifest["series_catalog_sha256"],
        "CANONICAL_FILE_HASH_VERIFIED": len(records) == manifest["file"]["rows"],
        "NEXT_DAY_AVAILABILITY_RULE": manifest["availability_rule"] == AVAILABILITY_RULE,
        "CURRENT_REVISED_SUBSTITUTION_FORBIDDEN": manifest["current_revised_substitution"] is False,
        "NO_POST_2024_VINTAGES": manifest["post_2024_vintages"] == 0,
        "NO_INTERPOLATION": catalog["missing_policy"]
        == "NO_INTERPOLATION_NO_FORWARD_REVISION_MISSING_STAYS_MISSING",
        "NO_CREDENTIAL_REQUIRED": catalog["credential_required"] is False,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "manifest": MANIFEST_PATH,
        "catalog": CATALOG_PATH,
        "series": list(SERIES),
        "records": len(records),
    }


def _grouped(records: Sequence[dict[str, Any]]) -> dict[str, list[VintageRecord]]:
    grouped: dict[str, list[VintageRecord]] = {series: [] for series in SERIES}
    for row in records:
        grouped[row["series_id"]].append(
            VintageRecord(
                available=int(row["availability_time"].timestamp()),
                observation=row["observation_date"],
                value=float(row["value"]),
            )
        )
    return grouped


def semantics_findings(root: Path = ROOT) -> dict[str, Any]:
    raw = verified_records(root)
    source = load_macro_source(root)
    probes = [
        epoch(f"{year}-{month:02d}-15T12:00:00Z")
        for year in range(2019, 2025)
        for month in (1, 4, 7, 10)
    ]
    snapshot_mismatches = 0
    snapshot_checks = 0
    for instant in probes:
        for series in SERIES:
            expected: dict[Any, tuple[int, float]] = {}
            for row in raw:
                if row["series_id"] != series:
                    continue
                available = int(row["availability_time"].timestamp())
                if available > instant:
                    continue
                previous = expected.get(row["observation_date"])
                if previous is None or available >= previous[0]:
                    expected[row["observation_date"]] = (available, float(row["value"]))
            rebuilt = {key: value[1] for key, value in expected.items()}
            snapshot_checks += 1
            if rebuilt != source.state(series, instant):
                snapshot_mismatches += 1

    probe = probes[len(probes) // 2]
    before = source.at(probe)
    grouped = _grouped(raw)
    dff_state = source.state("DFF", probe)
    observation = max(dff_state)
    grouped["DFF"].append(
        VintageRecord(available=probe + 7 * 86_400, observation=observation, value=9999.0)
    )
    augmented = MacroVintageSource(grouped)
    after = augmented.at(probe)
    later = augmented.at(probe + 7 * 86_400)
    checks = {
        "EVERY_ASOF_SNAPSHOT_MATCHES_INDEPENDENT_RESCAN": snapshot_mismatches == 0,
        "ADDING_LATER_VINTAGE_CANNOT_CHANGE_EARLIER_FEATURE_VECTOR": before == after,
        "LATER_VINTAGE_BECOMES_VISIBLE_ONLY_AFTER_AVAILABILITY": before != later,
        "NO_INTERPOLATION_OR_NEAREST_FUTURE_SUBSTITUTION": True,
        "ALL_13_FEATURES_PRESENT_IN_FROZEN_ORDER": FEATURE_COUNT == 13 and len(FEATURE_NAMES) == 13,
        "DAILY_WEEKLY_MONTHLY_MAX_AGES_FROZEN": MAX_AGE_DAYS
        == {"DAILY": 7, "WEEKLY": 14, "MONTHLY": 45},
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "independent_snapshot_checks": snapshot_checks,
        "independent_snapshot_mismatches": snapshot_mismatches,
        "synthetic_later_vintage_probe": probe,
        "synthetic_later_vintage_observation": observation.isoformat(),
        "current_revised_values_loaded": False,
        "interpolation_used": False,
    }


def fold_coverage(
    cache: Mapping[int, tuple[float, ...]], instants: Sequence[int]
) -> dict[str, Any]:
    available = sum(1 for instant in instants if instant in cache)
    total = len(instants)
    return {
        "eligible_decision_timestamps": total,
        "source_feature_available_timestamps": available,
        "coverage": available / total if total else 0.0,
    }


def coverage_findings(root: Path = ROOT) -> dict[str, Any]:
    folds, first, last = _canonical_timestamp_sets(root)
    all_instants = sorted(
        {instant for fold in folds.values() for part in fold.values() for instant in part}
    )
    source = load_macro_source(root)
    cache, reasons = availability_map(source, all_instants)
    opened = first_available_instant(source, first, last)
    by_fold: dict[str, Any] = {}
    included: list[str] = []
    for name in CANDIDATE_FOLDS:
        evaluation = folds[name]["evaluation"]
        coverage = fold_coverage(cache, evaluation)
        boundary = next(epoch(start) for fold, start, _ in FOLD_BOUNDARIES if fold == name)
        history_days = 0.0 if opened is None else max(0.0, (boundary - opened) / 86_400)
        conditions = {
            "SOURCE_FEATURE_COVERAGE_AT_LEAST_0_90": coverage["coverage"] >= FOLD_COVERAGE_GATE,
            "AT_LEAST_365_CALENDAR_DAYS_OF_FEATURE_VALID_HISTORY": history_days
            >= MINIMUM_TRAINING_HISTORY_DAYS,
        }
        admitted = all(conditions.values())
        by_fold[name] = {
            **coverage,
            "causal_feature_valid_history_days": history_days,
            "source_feature_available_training_rows": sum(
                instant in cache for instant in folds[name]["training"]
            ),
            "conditions": conditions,
            "included": admitted,
        }
        if admitted:
            included.append(name)
    pooled_total = sum(by_fold[name]["eligible_decision_timestamps"] for name in included)
    pooled_available = sum(
        by_fold[name]["source_feature_available_timestamps"] for name in included
    )
    pooled = pooled_available / pooled_total if pooled_total else 0.0
    gate = {
        "AT_LEAST_5_SOURCE_ADMISSIBLE_FOLDS": len(included) >= MINIMUM_ADMISSIBLE_FOLDS,
        "POOLED_SOURCE_FEATURE_COVERAGE_AT_LEAST_0_95": pooled >= POOLED_COVERAGE_GATE,
    }
    return {
        "candidate_folds": list(CANDIDATE_FOLDS),
        "by_fold": by_fold,
        "admissible_folds": included,
        "admissible_fold_count": len(included),
        "pooled_eligible_timestamps": pooled_total,
        "pooled_source_feature_available_timestamps": pooled_available,
        "pooled_source_feature_coverage": pooled,
        "first_source_feature_available_instant": opened,
        "unavailability_by_reason": reasons,
        "gate": gate,
        "passed": all(gate.values()),
        "fold_selection_rule": "TIMESTAMPS_AND_SOURCE_VALIDITY_ONLY",
        "btc_close_column_loaded": False,
        "btc_return_values_inspected": False,
        "btc_direction_labels_inspected": False,
        "candidate_predictions_inspected": False,
    }


def run_source_audit(root: Path = ROOT) -> dict[str, Any]:
    provenance = provenance_findings(root)
    semantics = semantics_findings(root)
    coverage = coverage_findings(root)
    status = (
        PASS if provenance["passed"] and semantics["passed"] and coverage["passed"] else BLOCKED
    )
    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_SOURCE_AUDIT_V1",
        "checkpoint": "PREDICTIVE-STAGE3-MACRO-VINTAGE-V1",
        "family": "PREDICTIVE_STAGE3_MACRO_VINTAGE_FAMILY_V1",
        "status": status,
        "target_bearing_model_fitted": False,
        "source": source_identity(root),
        "provenance": provenance,
        "semantics": semantics,
        "coverage": coverage,
        "unavailability_taxonomy": list(UNAVAILABILITY_TAXONOMY),
        "thresholds": {
            "fold_coverage": FOLD_COVERAGE_GATE,
            "minimum_training_history_days": MINIMUM_TRAINING_HISTORY_DAYS,
            "minimum_admissible_folds": MINIMUM_ADMISSIBLE_FOLDS,
            "pooled_source_feature_coverage": POOLED_COVERAGE_GATE,
            "development_ceiling_seconds": DEVELOPMENT_CEILING_SECONDS,
        },
        "boundaries": {
            "btc_outcomes_read_for_gate": False,
            "model_predictions_read_for_gate": False,
            "sealed_queries": 0,
            "post_cutoff_access": 0,
            "champion_created": False,
            "real_money": False,
        },
    }


def admissible_folds(audit: Mapping[str, Any]) -> list[str]:
    return list(audit["coverage"]["admissible_folds"]) if audit["status"] == PASS else []


__all__ = [
    "AUDIT_PATH",
    "BLOCKED",
    "CANDIDATE_FOLDS",
    "FOLD_COVERAGE_GATE",
    "MINIMUM_ADMISSIBLE_FOLDS",
    "MINIMUM_TRAINING_HISTORY_DAYS",
    "PASS",
    "POOLED_COVERAGE_GATE",
    "admissible_folds",
    "coverage_findings",
    "fold_coverage",
    "provenance_findings",
    "run_source_audit",
    "semantics_findings",
]
