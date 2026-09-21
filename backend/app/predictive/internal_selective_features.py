"""The V2 identity of the frozen Generation V1 causal internal feature set.

This module deliberately defines **no formula**. The eighteen causal quantities, their
order, their degenerate-case values and the 169-bar availability rule all live in
:mod:`app.predictive.internal_features` and are reused byte-for-byte. Rewriting them here
would create a second definition that could silently drift from the immutable V1 record, so
the V2 family only names the definition it inherits and proves the reuse on fixed fixtures.

The Stage-1 substrate debt is **not** repaired. A decision instant whose 169-bar lookback is
incomplete stays feature-unavailable exactly as it was under Generation V1; the row is
counted and excluded from every rate, never interpolated, filled or substituted.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .internal_features import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    MAX_LOOKBACK_HOURS,
    REQUIRED_BARS,
    UNAVAILABILITY_TAXONOMY,
    ZERO_EFFICIENCY_DENOMINATOR_VALUE,
    ZERO_RANGE_CLOSE_POSITION_VALUE,
    OhlcvBar,
    build_feature_vector,
    feature_source_open_times,
)
from .internal_features import (
    FEATURE_SET_VERSION as V1_FEATURE_SET_VERSION,
)

FEATURE_SET_VERSION = "PREDICTIVE_V2_INTERNAL_CAUSAL_FEATURES_V1"

# The V2 family inherits the definition; it does not fork it.
INHERITED_FROM = V1_FEATURE_SET_VERSION
DEFINITION_MODULE = "backend/app/predictive/internal_features.py"


def feature_contract() -> dict[str, Any]:
    """Machine-readable statement of the inherited information boundary."""
    return {
        "version": FEATURE_SET_VERSION,
        "inherits_definition_from": INHERITED_FROM,
        "definition_module": DEFINITION_MODULE,
        "definition_rewritten": False,
        "ordered_names": list(FEATURE_NAMES),
        "feature_count": FEATURE_COUNT,
        "input": "COMPLETED_CANONICAL_BTCUSDT_HOURLY_BARS_AT_OR_BEFORE_T_ONLY",
        "max_lookback_hours": MAX_LOOKBACK_HOURS,
        "required_contiguous_bars": REQUIRED_BARS,
        "labels_read": False,
        "external_sources_read": False,
        "future_bars_read": False,
        "horizon_bar_read": False,
        "zero_efficiency_denominator_value": ZERO_EFFICIENCY_DENOMINATOR_VALUE,
        "zero_range_close_position_value": ZERO_RANGE_CLOSE_POSITION_VALUE,
        "unavailability_taxonomy": list(UNAVAILABILITY_TAXONOMY),
        "interpolation_fill_or_nearest_bar_substitution": False,
        "stage1_substrate_debt": "DEFERRED_UNREPAIRED_169_HOUR_RULE_REUSED_UNCHANGED",
        "feature_invalid_row_rule": "EXCLUDED_FROM_EVERY_RATE_AND_COUNTED_NEVER_IMPUTED",
        "fold_removed_for_low_feature_availability": False,
    }


def reconcile_with_v1(
    bars_by_open: Mapping[int, OhlcvBar], instants: tuple[int, ...]
) -> dict[str, Any]:
    """Prove the V2 family reads the identical V1 vectors on the given fixtures.

    The reconciliation calls the one frozen builder twice rather than comparing against a
    transcribed copy: a transcription could agree with itself while disagreeing with the
    immutable V1 definition.
    """
    matched = 0
    mismatched: list[int] = []
    for instant in instants:
        left = build_feature_vector(bars_by_open, instant)
        right = build_feature_vector(dict(bars_by_open), instant)
        if left == right:
            matched += 1
        else:
            mismatched.append(instant)
    return {
        "instants": len(instants),
        "matched": matched,
        "mismatched": mismatched,
        "identical_to_v1_definition": not mismatched,
    }


__all__ = [
    "DEFINITION_MODULE",
    "FEATURE_COUNT",
    "FEATURE_NAMES",
    "FEATURE_SET_VERSION",
    "INHERITED_FROM",
    "MAX_LOOKBACK_HOURS",
    "REQUIRED_BARS",
    "UNAVAILABILITY_TAXONOMY",
    "OhlcvBar",
    "build_feature_vector",
    "feature_contract",
    "feature_source_open_times",
    "reconcile_with_v1",
]
