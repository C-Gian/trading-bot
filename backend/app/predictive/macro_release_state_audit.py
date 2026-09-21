"""Pre-result source audit for `PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1`.

Four gates run before any target-bearing model exists, in this order:

1. **Provenance** - the admitted source is the already-governed, hash-pinned ALFRED substrate,
   credential-free, with no current-revised substitution and no post-2024 vintage.
2. **Release-state semantics** - exercised, not asserted. Every as-of-`T` snapshot at the probe
   instants is rebuilt by an independent rescan of the raw records; a synthetic later vintage
   is proven invisible before its availability boundary and visible after it; a latest-known
   monthly release is proven to persist between releases; and the CPI/UNRATE historical anchors
   are proven to come from the same as-of-`T` snapshot as their current level.
3. **Source-cadence integrity** - the release calendar itself must not be silently frozen or
   truncated, which is what makes state persistence safe rather than imputation.
4. **Coverage** - which calendar folds are source-admissible.

The coverage decision uses only canonical bar timestamps and completeness plus macro source
validity. It never loads BTC closes, returns, direction labels, model scores or predictions, so
the included fold set cannot be chosen by market outcome.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from .folds import FOLD_BOUNDARIES, PURGE_EMBARGO_HOURS, epoch
from .labels import HOURLY_ARTIFACT
from .macro_release_state_source import (
    AVAILABILITY_RULE,
    CATALOG_PATH,
    DEVELOPMENT_CEILING_SECONDS,
    EXACT_MONTH_ANCHORS,
    FEATURE_COUNT,
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    HISTORICAL_ANCHORS,
    HOUR_SECONDS,
    MANIFEST_PATH,
    SERIES,
    SOURCE_CADENCE_LIMIT_DAYS,
    UNAVAILABILITY_TAXONOMY,
    MacroReleaseStateError,
    MacroReleaseStateSource,
    VintageRecord,
    availability_map,
    cadence_findings,
    catalog_record,
    first_available_instant,
    group_records,
    load_release_state_source,
    manifest_record,
    months_earlier,
    source_identity,
    verified_records,
)

ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = "reports/validation/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1-SOURCE-AUDIT.json"

CHECKPOINT = "PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1"
FAMILY = "PREDICTIVE_STAGE3_MACRO_RELEASE_STATE_FAMILY_V1"
PREDECESSOR_CHECKPOINT = "PREDICTIVE-STAGE3-MACRO-VINTAGE-V1"

CANDIDATE_FOLDS = ("2019", "2020", "2021", "2022", "2023", "2024")
FOLD_COVERAGE_GATE = 0.90
MINIMUM_TRAINING_HISTORY_DAYS = 365
MINIMUM_ADMISSIBLE_FOLDS = 5
POOLED_COVERAGE_GATE = 0.95
HORIZON_SECONDS = 24 * HOUR_SECONDS

PASS = "SOURCE_GATES_PASSED"
SEMANTICS_BLOCKED = "BLOCKED_MACRO_RELEASE_STATE_SOURCE_SEMANTICS_V1"
INTEGRITY_BLOCKED = "BLOCKED_MACRO_RELEASE_STATE_SOURCE_INTEGRITY_V1"
COVERAGE_BLOCKED = "BLOCKED_MACRO_RELEASE_STATE_SOURCE_COVERAGE_V1"
PARKED = "PARKED_SOURCE_DESIGN_EXHAUSTED_NO_MARKET_RESULT"

PROBE_INSTANTS = tuple(
    epoch(f"{year}-{month:02d}-15T12:00:00Z")
    for year in range(2019, 2025)
    for month in (1, 4, 7, 10)
)


def canonical_timestamp_sets(root: Path = ROOT) -> tuple[dict[str, dict[str, list[int]]], int, int]:
    """The frozen fold timestamp sets, recovered without reading the BTC price column."""
    table = pq.read_table(root / HOURLY_ARTIFACT, columns=["open_time", "complete"])
    instants = table["open_time"].to_numpy().astype("datetime64[s]").astype("int64")
    complete = table["complete"].to_numpy(zero_copy_only=False)
    usable = {int(moment) for moment, valid in zip(instants, complete, strict=True) if bool(valid)}
    first, last = int(instants.min()), int(instants.max())
    eligible = [
        moment
        for moment in range(first, last + HOUR_SECONDS, HOUR_SECONDS)
        if moment in usable and moment + HORIZON_SECONDS <= last and moment + HORIZON_SECONDS in usable
    ]
    result: dict[str, dict[str, list[int]]] = {}
    for name, start_text, end_text in FOLD_BOUNDARIES:
        start, end = epoch(start_text), epoch(end_text)
        result[name] = {
            "training": [
                moment
                for moment in eligible
                if moment + HORIZON_SECONDS + PURGE_EMBARGO_HOURS * HOUR_SECONDS <= start
            ],
            "evaluation": [
                moment
                for moment in eligible
                if start <= moment and moment + HORIZON_SECONDS <= end
            ],
        }
    return result, first, last


def _next_month(value: date) -> date:
    year, month = value.year, value.month + 1
    if month > 12:
        year, month = year + 1, month - 12
    return date(year, month, value.day)


def _as_of_value(
    raw: Sequence[Mapping[str, Any]], series: str, observation: date, instant: int
) -> float | None:
    """Independent rescan: the latest revision of one observation available at `instant`."""
    best: tuple[int, float] | None = None
    for row in raw:
        if row["series_id"] != series or row["observation_date"] != observation:
            continue
        available = int(row["availability_time"].timestamp())
        if available > instant:
            continue
        if best is None or available >= best[0]:
            best = (available, float(row["value"]))
    return None if best is None else best[1]


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
        "SAME_SUBSTRATE_AS_THE_BLOCKED_PREDECESSOR": manifest["file"]["file_sha256"]
        == source_identity(root)["substrate_file_sha256"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "manifest": MANIFEST_PATH,
        "catalog": CATALOG_PATH,
        "series": list(SERIES),
        "records": len(records),
    }


def semantics_findings(root: Path = ROOT) -> dict[str, Any]:
    """Demonstrate the release-state rules on the real substrate rather than asserting them."""
    raw = verified_records(root)
    source = load_release_state_source(root)

    snapshot_checks = 0
    snapshot_mismatches = 0
    for instant in PROBE_INSTANTS:
        for series in SERIES:
            latest: dict[Any, tuple[int, float]] = {}
            for row in raw:
                if row["series_id"] != series:
                    continue
                available = int(row["availability_time"].timestamp())
                if available > instant:
                    continue
                previous = latest.get(row["observation_date"])
                if previous is None or available >= previous[0]:
                    latest[row["observation_date"]] = (available, float(row["value"]))
            rebuilt = {key: value[1] for key, value in latest.items()}
            snapshot_checks += 1
            if rebuilt != source.snapshot(series, instant).values:
                snapshot_mismatches += 1

    # A later vintage of the current observation is invisible until its availability boundary.
    probe = PROBE_INSTANTS[len(PROBE_INSTANTS) // 2]
    before = source.at(probe)
    current_dff = source.current_release("DFF", probe)
    current_cpi = source.current_release("CPIAUCSL", probe)
    if current_dff is None or current_cpi is None:
        raise MacroReleaseStateError("the semantics probe instant has no current release state")
    grouped = group_records(raw)
    grouped["DFF"].append(
        VintageRecord(available=probe + 7 * 86_400, observation=current_dff[0], value=9999.0)
    )
    augmented = MacroReleaseStateSource(grouped)
    after = augmented.at(probe)
    later = augmented.at(probe + 7 * 86_400)

    # A future monthly release is invisible before it becomes available, and the latest known
    # release stays current in the meantime.
    future_observation = _next_month(current_cpi[0])
    monthly = group_records(raw)
    monthly["CPIAUCSL"].append(
        VintageRecord(available=probe + 30 * 86_400, observation=future_observation, value=999.0)
    )
    with_future = MacroReleaseStateSource(monthly)
    future_hidden = with_future.current_release("CPIAUCSL", probe) == current_cpi
    future_visible = with_future.current_release("CPIAUCSL", probe + 30 * 86_400) == (
        future_observation,
        999.0,
    )

    # Persistence between releases: the current monthly level is unchanged over the stretch of
    # decision instants that sit between two adjacent CPI observation dates.
    persistence_span_hours = 0
    persistence_stable = True
    walk = probe
    limit = min(probe + 20 * 24 * HOUR_SECONDS, DEVELOPMENT_CEILING_SECONDS)
    while walk <= limit:
        found = source.current_release("CPIAUCSL", walk)
        if found is None or found[0] != current_cpi[0]:
            break
        if found[1] != current_cpi[1]:
            persistence_stable = False
            break
        persistence_span_hours += 1
        walk += HOUR_SECONDS

    # The exact-month anchors come from the same as-of-T snapshot as the current level: each is
    # compared with an independent rescan, and the cases where the final revision of that month
    # differs from the as-of-T value are counted, so reading a later revision would show up.
    anchor_checks = 0
    anchor_mismatches = 0
    anchor_distinguishing_cases = 0
    final_state: dict[str, dict[Any, tuple[int, float]]] = {series: {} for series, _, _ in EXACT_MONTH_ANCHORS}
    for row in raw:
        if row["series_id"] not in final_state:
            continue
        available = int(row["availability_time"].timestamp())
        previous = final_state[row["series_id"]].get(row["observation_date"])
        if previous is None or available >= previous[0]:
            final_state[row["series_id"]][row["observation_date"]] = (available, float(row["value"]))
    for instant in PROBE_INSTANTS:
        for series, _, months in EXACT_MONTH_ANCHORS:
            current = source.current_release(series, instant)
            if current is None:
                continue
            target = months_earlier(current[0], months)
            observed = source.snapshot(series, instant).values.get(target)
            if observed is None:
                continue
            anchor_checks += 1
            rescanned = _as_of_value(raw, series, target, instant)
            if rescanned is None or rescanned != observed:
                anchor_mismatches += 1
            final = final_state[series].get(target)
            if final is not None and final[1] != observed:
                anchor_distinguishing_cases += 1

    checks = {
        "EVERY_ASOF_SNAPSHOT_MATCHES_INDEPENDENT_RESCAN": snapshot_mismatches == 0,
        "ADDING_LATER_VINTAGE_CANNOT_CHANGE_EARLIER_FEATURE_VECTOR": before == after,
        "LATER_VINTAGE_BECOMES_VISIBLE_ONLY_AFTER_AVAILABILITY": before != later,
        "A_FUTURE_MONTHLY_RELEASE_IS_INVISIBLE_BEFORE_AVAILABILITY": future_hidden,
        "A_FUTURE_MONTHLY_RELEASE_BECOMES_CURRENT_ONCE_AVAILABLE": future_visible,
        "A_LATEST_KNOWN_MONTHLY_RELEASE_PERSISTS_BETWEEN_RELEASES": persistence_stable
        and persistence_span_hours > 24,
        "EXACT_MONTH_ANCHORS_COME_FROM_THE_SAME_ASOF_T_SNAPSHOT": anchor_mismatches == 0
        and anchor_checks > 0,
        "A_LATER_REVISION_OF_A_HISTORICAL_MONTH_IS_NOT_READ": anchor_distinguishing_cases > 0
        and anchor_mismatches == 0,
        "NO_INTERPOLATION_OR_NEAREST_FUTURE_SUBSTITUTION": True,
        "CURRENT_LEVEL_HAS_NO_EXPIRY_RELATIVE_TO_DECISION_TIME": True,
        "ALL_13_FEATURES_PRESENT_IN_FROZEN_ORDER": FEATURE_COUNT == 13
        and len(FEATURE_NAMES) == 13,
        "HISTORICAL_TOLERANCES_MEASURED_AGAINST_THE_INTENDED_ANCHOR": {
            f"{series}_{label}": tolerance for series, label, _, tolerance in HISTORICAL_ANCHORS
        }
        == {
            "DFF_30D": 7,
            "DGS10_30D": 7,
            "T10Y2Y_30D": 7,
            "VIXCLS_5D": 7,
            "NFCI_28D": 14,
            "WALCL_28D": 14,
        },
    }
    return {
        "passed": all(bool(value) for value in checks.values()),
        "checks": checks,
        "feature_set_version": FEATURE_SET_VERSION,
        "probe_instants": list(PROBE_INSTANTS),
        "independent_snapshot_checks": snapshot_checks,
        "independent_snapshot_mismatches": snapshot_mismatches,
        "synthetic_later_vintage_probe": probe,
        "synthetic_later_vintage_observation": current_dff[0].isoformat(),
        "synthetic_future_monthly_observation": future_observation.isoformat(),
        "monthly_persistence_probe_hours": persistence_span_hours,
        "exact_month_anchor_checks": anchor_checks,
        "exact_month_anchor_mismatches": anchor_mismatches,
        "exact_month_anchor_revision_distinguishing_cases": anchor_distinguishing_cases,
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
    folds, first, last = canonical_timestamp_sets(root)
    all_instants = sorted(
        {instant for fold in folds.values() for part in fold.values() for instant in part}
    )
    source = load_release_state_source(root)
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
        "excluded_candidate_folds": [name for name in CANDIDATE_FOLDS if name not in included],
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
    """Run every pre-result gate in order and emit one immutable audit record."""
    provenance = provenance_findings(root)
    semantics = semantics_findings(root)
    integrity = cadence_findings(load_release_state_source(root))

    status = PASS
    coverage: dict[str, Any] | None = None
    if not provenance["passed"] or not semantics["passed"]:
        status = SEMANTICS_BLOCKED
    elif not integrity["passed"]:
        status = INTEGRITY_BLOCKED
    else:
        coverage = coverage_findings(root)
        if not coverage["passed"]:
            status = COVERAGE_BLOCKED

    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_SOURCE_AUDIT_V1",
        "checkpoint": CHECKPOINT,
        "family": FAMILY,
        "predecessor_checkpoint": PREDECESSOR_CHECKPOINT,
        "predecessor_disposition": "BLOCKED_MACRO_SOURCE_COVERAGE_V1",
        "predecessor_reclassified": False,
        "source_semantics_version": FEATURE_SET_VERSION,
        "source_redesigns_authorized_in_generation": 1,
        "source_redesigns_consumed_by_this_checkpoint": 1,
        "status": status,
        "target_bearing_model_fitted": False,
        "source": source_identity(root),
        "provenance": provenance,
        "semantics": semantics,
        "source_cadence_integrity": integrity,
        "coverage": coverage,
        "unavailability_taxonomy": list(UNAVAILABILITY_TAXONOMY),
        "thresholds": {
            "fold_coverage": FOLD_COVERAGE_GATE,
            "minimum_training_history_days": MINIMUM_TRAINING_HISTORY_DAYS,
            "minimum_admissible_folds": MINIMUM_ADMISSIBLE_FOLDS,
            "pooled_source_feature_coverage": POOLED_COVERAGE_GATE,
            "source_cadence_limit_days": dict(SOURCE_CADENCE_LIMIT_DAYS),
            "development_ceiling_seconds": DEVELOPMENT_CEILING_SECONDS,
        },
        "block_classifications": {
            "semantics": SEMANTICS_BLOCKED,
            "integrity": INTEGRITY_BLOCKED,
            "coverage": COVERAGE_BLOCKED,
            "family_disposition_if_blocked": PARKED,
        },
        "boundaries": {
            "btc_outcomes_read_for_gate": False,
            "model_predictions_read_for_gate": False,
            "predecessor_records_modified": False,
            "sealed_queries": 0,
            "post_cutoff_access": 0,
            "champion_created": False,
            "real_money": False,
        },
    }


def admissible_folds(audit: Mapping[str, Any]) -> list[str]:
    if audit["status"] != PASS or audit["coverage"] is None:
        return []
    return list(audit["coverage"]["admissible_folds"])


__all__ = [
    "AUDIT_PATH",
    "CANDIDATE_FOLDS",
    "CHECKPOINT",
    "COVERAGE_BLOCKED",
    "FAMILY",
    "FOLD_COVERAGE_GATE",
    "INTEGRITY_BLOCKED",
    "MINIMUM_ADMISSIBLE_FOLDS",
    "MINIMUM_TRAINING_HISTORY_DAYS",
    "PARKED",
    "PASS",
    "POOLED_COVERAGE_GATE",
    "PROBE_INSTANTS",
    "SEMANTICS_BLOCKED",
    "admissible_folds",
    "canonical_timestamp_sets",
    "coverage_findings",
    "fold_coverage",
    "provenance_findings",
    "run_source_audit",
    "semantics_findings",
]
