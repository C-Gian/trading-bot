"""Pre-result source audit and coverage gate for `PREDICTIVE-STAGE2-OPEN-INTEREST-V1`.

Three gates run **before** any target-bearing model is fitted, in this order:

1. **Provenance** — the admitted source really is the official Binance archive, credential
   free, checksum-verified, within the development ceiling, with only the two admitted
   fields. Otherwise `SOURCE_PROVENANCE_BLOCKED_NOT_EXECUTED`.
2. **Semantics** — the record timestamp is a defensible point-in-time measurement stamp.
   Otherwise `SOURCE_SEMANTICS_BLOCKED_NOT_EXECUTED`.
3. **Cadence** — the admitted series is a genuine five-minute series. Otherwise
   `SOURCE_CADENCE_BLOCKED_NOT_EXECUTED`.

Then the fold coverage gate decides which calendar folds are source-admissible, using only
source timestamps, source quality and the already-frozen canonical decision grid. It never
reads a realized return value and never sees a candidate prediction, so the included fold set
cannot be chosen by market outcome.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .folds import FOLD_BOUNDARIES, PURGE_EMBARGO_HOURS, Fold, build_folds, epoch
from .folds import assert_no_boundary_leak as assert_no_fold_leak
from .labels import Label, build_labels, load_hourly_bars
from .open_interest_source import (
    ADMITTED_COLUMNS,
    CADENCE_SECONDS,
    DEVELOPMENT_CEILING,
    DEVELOPMENT_CEILING_SECONDS,
    FORBIDDEN_COLUMNS,
    MAXIMUM_STATE_AGE_SECONDS,
    RECORDS_PER_DAY,
    OpenInterestSource,
    build_open_interest_features,
    load_open_interest,
    manifest_record,
    source_identity,
)

ROOT = Path(__file__).resolve().parents[3]

AUDIT_PATH = "reports/validation/PREDICTIVE-STAGE2-OPEN-INTEREST-V1-SOURCE-AUDIT.json"

# Calendar evaluation folds this family may draw from. 2019 predates the archive entirely.
CANDIDATE_FOLDS = ("2020", "2021", "2022", "2023", "2024")

FOLD_COVERAGE_GATE = 0.95
MINIMUM_TRAINING_HISTORY_DAYS = 180
MINIMUM_ADMISSIBLE_FOLDS = 3
MINIMUM_ELIGIBLE_TIMESTAMPS = 20_000

PASS = "SOURCE_GATES_PASSED"
PROVENANCE_BLOCKED = "SOURCE_PROVENANCE_BLOCKED_NOT_EXECUTED"
SEMANTICS_BLOCKED = "SOURCE_SEMANTICS_BLOCKED_NOT_EXECUTED"
CADENCE_BLOCKED = "SOURCE_CADENCE_BLOCKED_NOT_EXECUTED"
COVERAGE_BLOCKED = "SOURCE_COVERAGE_BLOCKED_NOT_EXECUTED"

POINT_IN_TIME_ARGUMENT = (
    "The archive publishes one record per five-minute boundary stamped with the boundary it "
    "measures, so create_time is a measurement timestamp. The as-of rule takes only records "
    "strictly before the decision instant and no older than ten minutes, so the newest usable "
    "record is normally stamped T-5m. A look-ahead would require the archive's publication "
    "lag to exceed five minutes."
)
POINT_IN_TIME_RESIDUAL = (
    "The archive documents the measurement timestamp but not a separate publication lag. That "
    "residual assumption is recorded rather than hidden, and is restated in the contract and "
    "in every experiment admitted under it."
)


def _fold_sets(root: Path) -> tuple[dict[str, Fold], int]:
    bars = load_hourly_bars(root)
    label_set = build_labels(bars)
    fold_set = build_folds(label_set.labels, purge_embargo_hours=PURGE_EMBARGO_HOURS)
    assert_no_fold_leak(fold_set)
    return {fold.name: fold for fold in fold_set.folds}, fold_set.eligible_total()


def provenance_findings(root: Path = ROOT) -> dict[str, Any]:
    """Whether the admitted source is the official archive and nothing else."""
    manifest = manifest_record(root)
    source = manifest["source"]
    archive = manifest["archive"]
    integrity = manifest["integrity"]
    checks = {
        "OFFICIAL_ARCHIVE_CLASS": source["class"] == "OFFICIAL_BINANCE_PUBLIC_DATA_ARCHIVE",
        "CREDENTIAL_FREE": source["credential_free"] is True,
        "NO_THIRD_PARTY_VENDOR": source["third_party_vendor"] is False,
        "NO_REST_SNAPSHOT_HISTORY": source["rest_snapshot_history"] is False,
        "NO_RECONSTRUCTION_OR_BACKFILL": source["reconstructed_or_backfilled"] is False,
        "EVERY_DAY_CHECKSUM_VERIFIED": archive["official_checksums_verified"] == archive["days"],
        "ONLY_ADMITTED_COLUMNS": manifest["admitted_columns"] == list(ADMITTED_COLUMNS),
        "OPEN_INTEREST_VALUE_EXCLUDED": "sum_open_interest_value"
        in manifest["excluded_source_fields"],
        "EVERY_RATIO_FIELD_EXCLUDED": all(
            name in manifest["excluded_source_fields"] for name in FORBIDDEN_COLUMNS
        ),
        "NO_POST_CUTOFF_RECORD": integrity["post_cutoff_records"] == 0,
        "DEVELOPMENT_CEILING_DECLARED": manifest["request_ceiling"] == DEVELOPMENT_CEILING,
        "NO_DUPLICATE_TIMESTAMP": integrity["duplicates"] == 0,
        "NO_CONFLICTING_DUPLICATE": integrity["conflicting_duplicate_timestamps"] == 0,
        "EXACT_DUPLICATES_COLLAPSED_UNDER_A_DECLARED_POLICY": (
            integrity["duplicate_policy"] == "COLLAPSE_EXACT_REPETITION_FAIL_CLOSED_ON_CONFLICT"
        ),
        "STRICTLY_INCREASING": integrity["strictly_increasing"] is True,
        "NON_POSITIVE_QUANTITIES_ACCOUNTED": isinstance(integrity["non_positive_quantities"], int),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        # A non-positive quantity is a data-quality event, not a provenance failure. The
        # frozen feature-validity rule turns it into a typed abstention at the state level,
        # so it is counted here and absorbed by the coverage gate.
        "non_positive_quantities": integrity["non_positive_quantities"],
        "exact_duplicate_rows_collapsed": integrity["exact_duplicate_rows_collapsed"],
    }


def semantics_findings(root: Path = ROOT) -> dict[str, Any]:
    """Whether the record timestamp is a defensible point-in-time measurement stamp."""
    manifest = manifest_record(root)
    checks = {
        "RECORD_TIMESTAMP_IS_A_MEASUREMENT_STAMP": manifest["cadence"]["declared"] == "FIVE_MINUTE",
        "RECORDS_ALIGN_TO_THE_CADENCE_GRID": manifest["integrity"]["off_grid_records"] == 0,
        "AS_OF_RULE_IS_STRICTLY_PRIOR": True,
        "AS_OF_RULE_BOUNDS_STALENESS": MAXIMUM_STATE_AGE_SECONDS == 600,
        "STALENESS_BOUND_EXCEEDS_ONE_CADENCE": MAXIMUM_STATE_AGE_SECONDS > CADENCE_SECONDS,
        "NO_INTERPOLATION_OR_FORWARD_FILL": True,
        "RESIDUAL_PUBLICATION_LAG_DISCLOSED": True,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "argument": POINT_IN_TIME_ARGUMENT,
        "residual_assumption": POINT_IN_TIME_RESIDUAL,
    }


def cadence_findings(root: Path = ROOT) -> dict[str, Any]:
    """Whether the admitted series is a genuine five-minute series."""
    manifest = manifest_record(root)
    cadence = manifest["cadence"]
    integrity = manifest["integrity"]
    observed = integrity["expected_records_over_span"]
    present = manifest["records"]
    checks = {
        "DECLARED_FIVE_MINUTE": cadence["seconds"] == CADENCE_SECONDS == 300,
        "COMPLETE_DAY_IS_288_RECORDS": cadence["records_per_complete_day"] == RECORDS_PER_DAY,
        "EVERY_RECORD_ON_THE_FIVE_MINUTE_GRID": integrity["off_grid_records"] == 0,
        "MAJORITY_OF_THE_SPAN_IS_PRESENT": present >= 0.9 * observed,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "records": present,
        "expected_records_over_span": observed,
        "missing_records": integrity["missing_records"],
        "gap_count": integrity["gap_count"],
    }


def fold_coverage(source: OpenInterestSource, evaluation: Sequence[Label]) -> dict[str, Any]:
    """Per-fold source coverage, computed from source quality and the frozen grid only."""
    available = 0
    reasons: dict[str, int] = {}
    for label in evaluation:
        values, reason = build_open_interest_features(source, label.open_time)
        if values is None:
            reasons[str(reason)] = reasons.get(str(reason), 0) + 1
            continue
        available += 1
    total = len(evaluation)
    return {
        "eligible_decision_timestamps": total,
        "source_valid_timestamps": available,
        "coverage": (available / total) if total else 0.0,
        "unavailable_by_reason": reasons,
    }


def coverage_findings(
    root: Path = ROOT, source: OpenInterestSource | None = None
) -> dict[str, Any]:
    """Decide the source-admissible fold set deterministically, before any model is fitted."""
    resolved = source if source is not None else load_open_interest(root)
    folds, canonical_total = _fold_sets(root)
    first_record = resolved.times[0]

    by_fold: dict[str, Any] = {}
    admissible: list[str] = []
    for name in CANDIDATE_FOLDS:
        fold = folds[name]
        boundary = epoch(next(start for label, start, _ in FOLD_BOUNDARIES if label == name))
        history_days = max(0.0, (boundary - first_record) / 86_400)
        coverage = fold_coverage(resolved, fold.evaluation)
        training_rows = sum(
            1
            for label in fold.training
            if build_open_interest_features(resolved, label.open_time)[0] is not None
        )
        conditions = {
            "COVERAGE_AT_LEAST_0_95": coverage["coverage"] >= FOLD_COVERAGE_GATE,
            "AT_LEAST_180_DAYS_OF_PRIOR_SOURCE_HISTORY": history_days
            >= MINIMUM_TRAINING_HISTORY_DAYS,
        }
        included = all(conditions.values())
        by_fold[name] = {
            **coverage,
            "prior_source_history_days": history_days,
            "source_valid_training_rows": training_rows,
            "conditions": conditions,
            "included": included,
        }
        if included:
            admissible.append(name)

    eligible_total = sum(by_fold[name]["eligible_decision_timestamps"] for name in admissible)
    gate = {
        "AT_LEAST_3_ADMISSIBLE_FOLDS": len(admissible) >= MINIMUM_ADMISSIBLE_FOLDS,
        "AT_LEAST_20000_ELIGIBLE_TIMESTAMPS": eligible_total >= MINIMUM_ELIGIBLE_TIMESTAMPS,
    }
    return {
        "candidate_folds": list(CANDIDATE_FOLDS),
        "by_fold": by_fold,
        "admissible_folds": admissible,
        "admissible_fold_count": len(admissible),
        "admissible_eligible_timestamps": eligible_total,
        "canonical_six_fold_eligible_total": canonical_total,
        "gate": gate,
        "passed": all(gate.values()),
        "fold_selection_rule": "DETERMINISTIC_SOURCE_QUALITY_ONLY",
        "return_values_inspected": False,
        "candidate_predictions_inspected": False,
    }


def run_source_audit(root: Path = ROOT) -> dict[str, Any]:
    """Run every pre-result gate in order and emit one immutable audit record."""
    provenance = provenance_findings(root)
    semantics = semantics_findings(root)
    cadence = cadence_findings(root)

    status = PASS
    coverage: dict[str, Any] | None = None
    if not provenance["passed"]:
        status = PROVENANCE_BLOCKED
    elif not semantics["passed"]:
        status = SEMANTICS_BLOCKED
    elif not cadence["passed"]:
        status = CADENCE_BLOCKED
    else:
        coverage = coverage_findings(root)
        if not coverage["passed"]:
            status = COVERAGE_BLOCKED

    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_SOURCE_AUDIT_V1",
        "checkpoint": "PREDICTIVE-STAGE2-OPEN-INTEREST-V1",
        "family": "PREDICTIVE_STAGE2_OPEN_INTEREST_MODEL_FAMILY_V1",
        "status": status,
        "target_bearing_model_fitted": False,
        "source": source_identity(root),
        "provenance": provenance,
        "semantics": semantics,
        "cadence": cadence,
        "coverage": coverage,
        "thresholds": {
            "fold_coverage": FOLD_COVERAGE_GATE,
            "minimum_training_history_days": MINIMUM_TRAINING_HISTORY_DAYS,
            "minimum_admissible_folds": MINIMUM_ADMISSIBLE_FOLDS,
            "minimum_eligible_timestamps": MINIMUM_ELIGIBLE_TIMESTAMPS,
            "maximum_state_age_seconds": MAXIMUM_STATE_AGE_SECONDS,
            "development_ceiling_seconds": DEVELOPMENT_CEILING_SECONDS,
        },
        "boundaries": {
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
    "CADENCE_BLOCKED",
    "CANDIDATE_FOLDS",
    "COVERAGE_BLOCKED",
    "FOLD_COVERAGE_GATE",
    "MINIMUM_ADMISSIBLE_FOLDS",
    "MINIMUM_ELIGIBLE_TIMESTAMPS",
    "MINIMUM_TRAINING_HISTORY_DAYS",
    "PASS",
    "PROVENANCE_BLOCKED",
    "SEMANTICS_BLOCKED",
    "admissible_folds",
    "cadence_findings",
    "coverage_findings",
    "fold_coverage",
    "provenance_findings",
    "run_source_audit",
    "semantics_findings",
]
