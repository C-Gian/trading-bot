"""Pre-result source audit and coverage gate for `PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1`.

Three gates run **before** any target-bearing model is fitted, in this order:

1. **Provenance** — the admitted source really is the already-governed official Binance spot
   USDT archive substrate, credential-free, inside the development ceiling, with `BTCUSDT`
   and every leveraged token removed.
2. **Point-in-time semantics** — exercised, not asserted. At deterministic probe instants the
   feature vector is recomputed from a panel that contains *only* the four endpoint rows, and
   from a panel whose columns have been permuted. If either reproduces the real vector, then
   no bar after `T`, no bar other than the four endpoints, no asset's total row count and no
   per-asset weight can be influencing the result.
3. **Universe** — the frozen minimum point-in-time breadth of thirty non-BTC assets.

A failure of any of the three classifies the checkpoint
`SOURCE_BLOCKED_CROSS_ASSET_PIT_SEMANTICS` and no model is fitted.

Then the coverage gate decides which calendar folds are source-admissible, using only source
availability and the already-frozen canonical decision grid. It never reads `r_24h`, its
direction, a model score or a win rate, so the included fold set cannot be chosen by market
outcome. A failure here classifies `SOURCE_BLOCKED_CROSS_ASSET_COVERAGE`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .cross_asset_source import (
    ADMITTED_COLUMNS,
    CROSS_SECTIONAL_WEIGHTING,
    DEVELOPMENT_CEILING,
    DEVELOPMENT_CEILING_SECONDS,
    ENDPOINT_OFFSET_HOURS,
    FORBIDDEN_COLUMNS,
    HOUR_SECONDS,
    LONG_LOOKBACK_HOURS,
    MINIMUM_POINT_IN_TIME_UNIVERSE,
    QUOTE_ASSET,
    REQUIRED_ENDPOINT_BARS,
    TARGET_SYMBOL,
    UNAVAILABILITY_TAXONOMY,
    CrossSectionPanel,
    build_cross_asset_features,
    endpoint_mask,
    first_available_instant,
    is_admitted_symbol,
    is_leveraged_token,
    load_cross_section,
    manifest_record,
    point_in_time_universe,
    source_identity,
)
from .folds import FOLD_BOUNDARIES, PURGE_EMBARGO_HOURS, Fold, build_folds, epoch
from .folds import assert_no_boundary_leak as assert_no_fold_leak
from .labels import Label, build_labels, load_hourly_bars

ROOT = Path(__file__).resolve().parents[3]

AUDIT_PATH = "reports/validation/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1-SOURCE-AUDIT.json"

# Every calendar evaluation fold of the frozen design is a candidate; the gate decides.
CANDIDATE_FOLDS = ("2019", "2020", "2021", "2022", "2023", "2024")

FOLD_COVERAGE_GATE = 0.95
MINIMUM_TRAINING_HISTORY_DAYS = 180
MINIMUM_ADMISSIBLE_FOLDS = 5
MINIMUM_ELIGIBLE_TIMESTAMPS = 40_000

# The retired cross-section participation idea, named so the audit can prove it is dead.
RETIRED_PARTICIPATION_ROW_RULE = 504

# Archive rows the substrate builder refused, per symbol, before the artifact was written.
REJECTED_ROW_COUNTERS = ("off_grid_rows", "duplicate_rows", "out_of_window_rows", "invalid_rows")

PASS = "SOURCE_GATES_PASSED"
SEMANTICS_BLOCKED = "SOURCE_BLOCKED_CROSS_ASSET_PIT_SEMANTICS"
COVERAGE_BLOCKED = "SOURCE_BLOCKED_CROSS_ASSET_COVERAGE"

POINT_IN_TIME_ARGUMENT = (
    "A spot hourly bar stamped `t` closes at `t + 1h`, so the frozen decision instant `T` "
    "indexes the bar that has just closed and `close[T]` is knowable at `T`. Every endpoint "
    "a feature vector reads is one of `T`, `T-1h`, `T-24h` and `T-168h`, all at or before "
    "`T`, on the same official archive the BTC target already uses. Membership is decided "
    "bar by bar from what that asset has actually been observed to have by `T`, which the "
    "endpoint-only probe below demonstrates rather than asserts."
)
POINT_IN_TIME_RESIDUAL = (
    "The substrate is a monthly archive reconstruction of an hourly grid, so a bar the "
    "archive never published is simply absent rather than late: absence removes that asset "
    "from that instant instead of admitting a stale or reconstructed value. That is the "
    "conservative direction, and it is what makes abstention, not imputation, the only "
    "failure mode of this source."
)


def _fold_sets(root: Path) -> tuple[dict[str, Fold], int, tuple[Label, ...]]:
    bars = load_hourly_bars(root)
    label_set = build_labels(bars)
    fold_set = build_folds(label_set.labels, purge_embargo_hours=PURGE_EMBARGO_HOURS)
    assert_no_fold_leak(fold_set)
    return (
        {fold.name: fold for fold in fold_set.folds},
        fold_set.eligible_total(),
        label_set.labels,
    )


def scan(
    panel: CrossSectionPanel, instants: Sequence[int]
) -> tuple[dict[int, tuple[float, ...]], dict[str, int], dict[int, int]]:
    """One pass over the decision grid: feature vectors, typed reasons and universe sizes."""
    available: dict[int, tuple[float, ...]] = {}
    reasons = dict.fromkeys(UNAVAILABILITY_TAXONOMY, 0)
    sizes: dict[int, int] = {}
    for instant in instants:
        mask, _ = endpoint_mask(panel, instant)
        sizes[instant] = 0 if mask is None else int(mask.sum())
        values, reason = build_cross_asset_features(panel, instant)
        if values is None:
            reasons[str(reason)] += 1
            continue
        available[instant] = values
    return available, reasons, sizes


def provenance_findings(root: Path = ROOT) -> dict[str, Any]:
    """Whether the admitted source is the already-governed official archive and nothing else."""
    manifest = manifest_record(root)
    source = manifest["source"]
    substrate = manifest["substrate"]
    excluded = set(manifest["leveraged_token_excluded"])
    panel_symbols = [record["symbol"] for record in manifest["substrate_symbols"]]
    checks = {
        "OFFICIAL_BINANCE_SPOT_ARCHIVE": source["provider"] == "Binance"
        and source["market_type"] == "spot",
        "CREDENTIAL_FREE": source["credentials_used"] is False,
        "HOURLY_INTERVAL": source["interval"] == "1h",
        "USDT_QUOTED_ONLY": manifest["object_quote_asset"] == QUOTE_ASSET,
        "UNIVERSE_FROM_ARCHIVE_EVIDENCE_NOT_CURRENT_EXCHANGE_INFO": (
            manifest["universe_derivation"]
            == "HISTORICAL_ARCHIVE_EVIDENCE_NOT_CURRENT_EXCHANGE_INFO"
        ),
        "LEVERAGED_TOKENS_EXCLUDED_BY_THE_FROZEN_RULE": all(
            is_leveraged_token(symbol) for symbol in excluded
        ),
        "NO_LEVERAGED_TOKEN_SURVIVES_IN_THE_SUBSTRATE": not any(
            is_leveraged_token(symbol) for symbol in panel_symbols
        ),
        "PREDICTION_TARGET_IS_IN_THE_SUBSTRATE_AND_INADMISSIBLE_HERE": (
            TARGET_SYMBOL in panel_symbols and not is_admitted_symbol(TARGET_SYMBOL)
        ),
        "SUBSTRATE_HASH_DECLARED": isinstance(substrate["sha256"], str)
        and len(substrate["sha256"]) == 64,
        "EVERY_SUBSTRATE_SYMBOL_IS_IN_WINDOW": all(
            record["status"] == "IN_WINDOW" for record in manifest["substrate_symbols"]
        ),
        "EVERY_REJECTED_ARCHIVE_ROW_IS_COUNTED": all(
            isinstance(record.get(key, 0), int)
            for record in manifest["substrate_symbols"]
            for key in REJECTED_ROW_COUNTERS
        ),
        "SUBSTRATE_ROW_TOTAL_MATCHES_THE_PER_SYMBOL_RECORDS": (
            sum(record["rows"] for record in manifest["substrate_symbols"])
            == substrate["hourly_rows"]
        ),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "fields_read": list(ADMITTED_COLUMNS),
        "forbidden_fields": list(FORBIDDEN_COLUMNS),
        "archive_symbols": manifest["archive_symbol_count"],
        "usdt_quoted_symbols": manifest["usdt_quoted_count"],
        "leveraged_tokens_excluded": manifest["leveraged_token_excluded_count"],
        "substrate_symbols_with_rows": substrate["symbols_with_rows"],
        "substrate_hourly_rows": substrate["hourly_rows"],
        "admitted_non_target_symbols": sum(
            1 for symbol in panel_symbols if is_admitted_symbol(symbol)
        ),
        # Rows the substrate builder refused before the artifact existed. They are hygiene
        # evidence, not defects: an off-grid, duplicated, out-of-window or malformed archive
        # row is dropped and counted, never repaired and never admitted.
        "archive_rows_rejected_before_the_substrate": {
            key: sum(record.get(key, 0) for record in manifest["substrate_symbols"])
            for key in REJECTED_ROW_COUNTERS
        },
    }


def probe_instants(panel: CrossSectionPanel) -> list[int]:
    """Deterministic probe instants, one week into each candidate fold. No label is read."""
    offset = LONG_LOOKBACK_HOURS * HOUR_SECONDS
    probes = []
    for name, start, _ in FOLD_BOUNDARIES:
        if name not in CANDIDATE_FOLDS:
            continue
        instant = epoch(start) + offset
        if panel.first_open_time <= instant <= panel.last_open_time:
            probes.append(instant)
    return probes


def endpoint_only_panel(panel: CrossSectionPanel, instant: int) -> CrossSectionPanel:
    """A 169-hour panel holding **only** the four endpoint rows of `instant`, nothing else.

    Every asset in it has at most four observed bars in its entire history, far below any
    participation threshold, and no bar after `instant` exists at all.
    """
    import numpy as np

    index = panel.row_index(instant)
    first = instant - LONG_LOOKBACK_HOURS * HOUR_SECONDS
    matrix = np.full((LONG_LOOKBACK_HOURS + 1, len(panel.symbols)), np.nan, dtype=np.float64)
    for offset in ENDPOINT_OFFSET_HOURS:
        matrix[LONG_LOOKBACK_HOURS - offset] = panel.log_close[index - offset]
    return CrossSectionPanel(symbols=panel.symbols, first_open_time=first, log_close=matrix)


def permuted_panel(panel: CrossSectionPanel) -> CrossSectionPanel:
    """The same panel with a deterministic column permutation — equal weighting must not care."""
    import numpy as np

    order = np.argsort(np.array([symbol[::-1] for symbol in panel.symbols]), kind="stable")
    return CrossSectionPanel(
        symbols=tuple(panel.symbols[int(index)] for index in order),
        first_open_time=panel.first_open_time,
        log_close=panel.log_close[:, order],
    )


def semantics_findings(panel: CrossSectionPanel) -> dict[str, Any]:
    """Exercise every point-in-time claim on the loaded panel rather than asserting it."""
    probes = probe_instants(panel)
    records: list[dict[str, Any]] = []
    endpoint_only_agrees = True
    permutation_agrees = True
    permuted = permuted_panel(panel)
    for instant in probes:
        real, reason = build_cross_asset_features(panel, instant)
        if real is None:
            records.append({"instant": instant, "available": False, "reason": reason})
            continue
        stripped = build_cross_asset_features(endpoint_only_panel(panel, instant), instant)[0]
        shuffled = build_cross_asset_features(permuted, instant)[0]
        endpoint_only_agrees &= stripped == real
        permutation_agrees &= shuffled == real
        members = point_in_time_universe(panel, instant)
        records.append(
            {
                "instant": instant,
                "available": True,
                "point_in_time_universe": len(members),
                "endpoint_only_panel_reproduces_the_vector": stripped == real,
                "column_permutation_reproduces_the_vector": shuffled == real,
            }
        )
    usable = [record for record in records if record["available"]]
    checks = {
        "AT_LEAST_ONE_PROBE_IS_AVAILABLE": bool(usable),
        "EVERY_ENDPOINT_IS_AT_OR_BEFORE_THE_DECISION_INSTANT": all(
            offset >= 0 for offset in ENDPOINT_OFFSET_HOURS
        ),
        "FOUR_ENDPOINT_BARS_REQUIRED_FROM_THE_SAME_ASSET": REQUIRED_ENDPOINT_BARS == 4,
        "ONLY_THE_FOUR_ENDPOINT_BARS_ENTER_A_FEATURE": bool(usable) and endpoint_only_agrees,
        "NO_BAR_AFTER_THE_DECISION_INSTANT_ENTERS_A_FEATURE": bool(usable) and endpoint_only_agrees,
        "NO_FUTURE_SURVIVAL_FILTER": bool(usable) and endpoint_only_agrees,
        "NO_WHOLE_SAMPLE_PARTICIPATION_THRESHOLD": bool(usable) and endpoint_only_agrees,
        "RETIRED_504_ROW_PARTICIPATION_RULE_NOT_REVIVED": bool(usable)
        and endpoint_only_agrees
        and REQUIRED_ENDPOINT_BARS < RETIRED_PARTICIPATION_ROW_RULE,
        "EQUAL_WEIGHTED_CROSS_SECTION": CROSS_SECTIONAL_WEIGHTING == "EQUAL_WEIGHTED",
        "NO_MARKET_CAP_FUTURE_VOLUME_OR_SURVIVOR_WEIGHTING": bool(usable) and permutation_agrees,
        "PREDICTION_TARGET_ABSENT_FROM_THE_PANEL": TARGET_SYMBOL not in panel.symbols,
        "NO_LEVERAGED_TOKEN_IN_THE_PANEL": not any(
            is_leveraged_token(symbol) for symbol in panel.symbols
        ),
        "DEVELOPMENT_CEILING_RESPECTED": panel.last_open_time <= DEVELOPMENT_CEILING_SECONDS,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "argument": POINT_IN_TIME_ARGUMENT,
        "residual_assumption": POINT_IN_TIME_RESIDUAL,
        "probes": records,
        "panel_symbols": len(panel.symbols),
        "panel_first_open_time": panel.first_open_time,
        "panel_last_open_time": panel.last_open_time,
        "retired_participation_row_rule": RETIRED_PARTICIPATION_ROW_RULE,
        "endpoint_only_panel_rows_per_asset": REQUIRED_ENDPOINT_BARS,
    }


def universe_findings(sizes: Mapping[int, int]) -> dict[str, Any]:
    """Whether the frozen minimum breadth is meaningful on this substrate."""
    ordered = sorted(sizes.values())
    reached = sum(1 for size in ordered if size >= MINIMUM_POINT_IN_TIME_UNIVERSE)
    middle = len(ordered) // 2
    median = (
        0
        if not ordered
        else (ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) // 2)
    )
    checks = {
        "MINIMUM_UNIVERSE_IS_THIRTY": MINIMUM_POINT_IN_TIME_UNIVERSE == 30,
        "THE_MINIMUM_IS_REACHED_SOMEWHERE": reached > 0,
        "THE_PANEL_CAN_EXCEED_THE_MINIMUM": max(ordered, default=0)
        > MINIMUM_POINT_IN_TIME_UNIVERSE,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "minimum_universe": MINIMUM_POINT_IN_TIME_UNIVERSE,
        "decision_instants_measured": len(ordered),
        "instants_reaching_the_minimum": reached,
        "median_point_in_time_universe": median,
        "minimum_point_in_time_universe_observed": min(ordered, default=0),
        "maximum_point_in_time_universe_observed": max(ordered, default=0),
        "universe_size_is_a_model_feature": False,
    }


def fold_coverage(
    cache: Mapping[int, tuple[float, ...]], evaluation: Sequence[Label]
) -> dict[str, Any]:
    """Per-fold source coverage, computed from source availability and the frozen grid only."""
    available = sum(1 for label in evaluation if label.open_time in cache)
    total = len(evaluation)
    return {
        "eligible_decision_timestamps": total,
        "source_feature_available_timestamps": available,
        "coverage": (available / total) if total else 0.0,
    }


def coverage_findings(
    panel: CrossSectionPanel,
    cache: Mapping[int, tuple[float, ...]],
    reasons: Mapping[str, int],
    root: Path = ROOT,
) -> dict[str, Any]:
    """Decide the source-admissible fold set deterministically, before any model is fitted."""
    folds, canonical_total, _ = _fold_sets(root)
    opened = first_available_instant(panel)

    by_fold: dict[str, Any] = {}
    admissible: list[str] = []
    for name in CANDIDATE_FOLDS:
        fold = folds[name]
        boundary = epoch(next(start for label, start, _ in FOLD_BOUNDARIES if label == name))
        history_days = 0.0 if opened is None else max(0.0, (boundary - opened) / 86_400)
        coverage = fold_coverage(cache, fold.evaluation)
        training_rows = sum(1 for label in fold.training if label.open_time in cache)
        conditions = {
            "COVERAGE_AT_LEAST_0_95": coverage["coverage"] >= FOLD_COVERAGE_GATE,
            "AT_LEAST_180_DAYS_OF_CAUSAL_PRE_FOLD_HISTORY": history_days
            >= MINIMUM_TRAINING_HISTORY_DAYS,
        }
        included = all(conditions.values())
        by_fold[name] = {
            **coverage,
            "causal_pre_fold_history_days": history_days,
            "source_feature_available_training_rows": training_rows,
            "conditions": conditions,
            "included": included,
        }
        if included:
            admissible.append(name)

    eligible_total = sum(by_fold[name]["eligible_decision_timestamps"] for name in admissible)
    gate = {
        "AT_LEAST_5_ADMISSIBLE_FOLDS": len(admissible) >= MINIMUM_ADMISSIBLE_FOLDS,
        "AT_LEAST_40000_ELIGIBLE_TIMESTAMPS": eligible_total >= MINIMUM_ELIGIBLE_TIMESTAMPS,
    }
    return {
        "candidate_folds": list(CANDIDATE_FOLDS),
        "by_fold": by_fold,
        "admissible_folds": admissible,
        "admissible_fold_count": len(admissible),
        "admissible_eligible_timestamps": eligible_total,
        "canonical_six_fold_eligible_total": canonical_total,
        "first_source_feature_available_instant": opened,
        "unavailability_by_reason": dict(reasons),
        "gate": gate,
        "passed": all(gate.values()),
        "fold_selection_rule": "DETERMINISTIC_SOURCE_AVAILABILITY_ONLY",
        "return_values_inspected": False,
        "labels_inspected": False,
        "candidate_predictions_inspected": False,
    }


def run_source_audit(root: Path = ROOT) -> dict[str, Any]:
    """Run every pre-result gate in order and emit one immutable audit record."""
    provenance = provenance_findings(root)
    panel = load_cross_section(root)
    _, _, labels = _fold_sets(root)
    semantics = semantics_findings(panel)
    cache, reasons, sizes = scan(panel, [label.open_time for label in labels])
    universe = universe_findings(sizes)

    status = PASS
    coverage: dict[str, Any] | None = None
    if not (provenance["passed"] and semantics["passed"] and universe["passed"]):
        status = SEMANTICS_BLOCKED
    else:
        coverage = coverage_findings(panel, cache, reasons, root)
        if not coverage["passed"]:
            status = COVERAGE_BLOCKED

    return {
        "schema_version": 1,
        "record_type": "PREDICTIVE_SOURCE_AUDIT_V1",
        "checkpoint": "PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1",
        "family": "PREDICTIVE_STAGE3_CROSS_ASSET_BREADTH_FAMILY_V1",
        "status": status,
        "target_bearing_model_fitted": False,
        "source": source_identity(root),
        "provenance": provenance,
        "semantics": semantics,
        "universe": universe,
        "coverage": coverage,
        "unavailability_taxonomy": list(UNAVAILABILITY_TAXONOMY),
        "thresholds": {
            "fold_coverage": FOLD_COVERAGE_GATE,
            "minimum_training_history_days": MINIMUM_TRAINING_HISTORY_DAYS,
            "minimum_admissible_folds": MINIMUM_ADMISSIBLE_FOLDS,
            "minimum_eligible_timestamps": MINIMUM_ELIGIBLE_TIMESTAMPS,
            "minimum_point_in_time_universe": MINIMUM_POINT_IN_TIME_UNIVERSE,
            "development_ceiling": DEVELOPMENT_CEILING,
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
    "CANDIDATE_FOLDS",
    "COVERAGE_BLOCKED",
    "FOLD_COVERAGE_GATE",
    "MINIMUM_ADMISSIBLE_FOLDS",
    "MINIMUM_ELIGIBLE_TIMESTAMPS",
    "MINIMUM_TRAINING_HISTORY_DAYS",
    "PASS",
    "REJECTED_ROW_COUNTERS",
    "RETIRED_PARTICIPATION_ROW_RULE",
    "SEMANTICS_BLOCKED",
    "admissible_folds",
    "coverage_findings",
    "endpoint_only_panel",
    "fold_coverage",
    "permuted_panel",
    "probe_instants",
    "provenance_findings",
    "run_source_audit",
    "scan",
    "semantics_findings",
    "universe_findings",
]
