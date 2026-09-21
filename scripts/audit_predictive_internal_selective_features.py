"""Prove the inherited causal vector's causality and V1 reconciliation before any fit."""

from __future__ import annotations

import inspect
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive import HORIZON_HOURS
from app.predictive.folds import PURGE_EMBARGO_HOURS, assert_no_boundary_leak, build_folds
from app.predictive.internal_features import (
    LOOKBACK_BAR_INCOMPLETE,
    LOOKBACK_BAR_MISSING,
    NON_POSITIVE_CLOSE,
    REQUIRED_BARS,
    ZERO_EFFICIENCY_DENOMINATOR_VALUE,
    ZERO_RANGE_CLOSE_POSITION_VALUE,
    OhlcvBar,
    assert_feature_causality,
    build_feature_vector,
    feature_source_open_times,
    index_ohlcv,
    load_hourly_ohlcv,
)
from app.predictive.internal_selective import (
    FEATURE_PROOF_PATH,
    IMPLEMENTATION_FILES,
    PRIOR_V1_RESULT_PATHS,
    PRIOR_V2_RESULT_PATHS,
    _execute_configuration,
    _fit_fold,
    canonical_bytes,
    feature_cache,
    run_family,
)
from app.predictive.internal_selective_features import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    INHERITED_FROM,
    feature_contract,
    reconcile_with_v1,
)
from app.predictive.internal_selective_model import fit_probability_head
from app.predictive.labels import HOUR_SECONDS, Bar, build_labels

HOUR = HOUR_SECONDS
BASE = 1_600_000_000 - 1_600_000_000 % HOUR


def _series(count: int, *, start: float = 100.0, step: float = 0.5) -> list[OhlcvBar]:
    """A strictly positive, complete synthetic series with a non-degenerate range."""
    bars = []
    for index in range(count):
        close = start + step * index
        bars.append(
            OhlcvBar(
                open_time=BASE + index * HOUR,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=10.0 + index % 7,
                complete=True,
            )
        )
    return bars


def build_proof() -> dict:
    bars = _series(REQUIRED_BARS + 48)
    index = index_ohlcv(bars)
    instant = bars[REQUIRED_BARS - 1].open_time
    baseline, reason = build_feature_vector(index, instant)
    if baseline is None:
        raise RuntimeError(f"the synthetic fixture is not feature-valid: {reason}")

    checks: dict[str, bool] = {}

    # Causality: every bar strictly after T may be replaced by anything at all without
    # moving the vector at T, and a guarded view proves no later bar is even requested.
    mutated = dict(index)
    for later in bars[REQUIRED_BARS:]:
        mutated[later.open_time] = OhlcvBar(
            open_time=later.open_time,
            high=9.9e7,
            low=1e-7,
            close=4.2e6,
            volume=7.5e5,
            complete=True,
        )
    checks["future_bar_mutation_cannot_change_vector"] = (
        build_feature_vector(mutated, instant)[0] == baseline
    )
    try:
        assert_feature_causality(index, instant)
    except Exception:  # pragma: no cover - a guard failure must fail the proof, not crash
        checks["guarded_view_rejects_any_future_read"] = False
    else:
        checks["guarded_view_rejects_any_future_read"] = True

    # Exact lookback endpoints: the causal surface is exactly T-168h .. T inclusive.
    sources = feature_source_open_times(instant)
    checks["lookback_surface_is_exactly_169_bars"] = (
        len(sources) == REQUIRED_BARS == 169
        and sources[0] == instant - 168 * HOUR
        and sources[-1] == instant
    )
    closes = [bar.close for bar in bars[:REQUIRED_BARS]]
    endpoints = {
        1: math.log(closes[-1] / closes[-2]),
        6: math.log(closes[-1] / closes[REQUIRED_BARS - 1 - 6]),
        24: math.log(closes[-1] / closes[REQUIRED_BARS - 1 - 24]),
        72: math.log(closes[-1] / closes[REQUIRED_BARS - 1 - 72]),
        168: math.log(closes[-1] / closes[REQUIRED_BARS - 1 - 168]),
    }
    checks["logret_window_endpoints_exact"] = all(
        math.isclose(baseline[position], expected, rel_tol=1e-12)
        for position, expected in zip(range(5), endpoints.values(), strict=True)
    )

    # Availability rules: unchanged from the frozen V1 taxonomy, and never repaired.
    oldest = sources[0]
    missing = {key: value for key, value in index.items() if key != oldest}
    checks["missing_lookback_bar_fails_closed"] = build_feature_vector(missing, instant) == (
        None,
        LOOKBACK_BAR_MISSING,
    )
    incomplete = dict(index)
    incomplete[oldest] = OhlcvBar(
        open_time=oldest,
        high=index[oldest].high,
        low=index[oldest].low,
        close=index[oldest].close,
        volume=index[oldest].volume,
        complete=False,
    )
    checks["incomplete_lookback_bar_fails_closed"] = build_feature_vector(incomplete, instant) == (
        None,
        LOOKBACK_BAR_INCOMPLETE,
    )
    non_positive = dict(index)
    non_positive[oldest] = OhlcvBar(
        open_time=oldest,
        high=1.0,
        low=0.0,
        close=0.0,
        volume=1.0,
        complete=True,
    )
    checks["non_positive_close_fails_closed"] = build_feature_vector(non_positive, instant) == (
        None,
        NON_POSITIVE_CLOSE,
    )

    # Denominator edge rules: the two named degenerate cases keep their frozen values.
    flat = index_ohlcv(_series(REQUIRED_BARS, step=0.0))
    flat_instant = BASE + (REQUIRED_BARS - 1) * HOUR
    flat_vector, flat_reason = build_feature_vector(flat, flat_instant)
    if flat_vector is None:
        raise RuntimeError(f"the flat fixture is not feature-valid: {flat_reason}")
    checks["zero_efficiency_denominator_value"] = all(
        flat_vector[position] == ZERO_EFFICIENCY_DENOMINATOR_VALUE for position in (9, 10, 11)
    )
    zero_range = index_ohlcv(
        [
            OhlcvBar(
                open_time=BASE + position * HOUR,
                high=100.0,
                low=100.0,
                close=100.0,
                volume=5.0,
                complete=True,
            )
            for position in range(REQUIRED_BARS)
        ]
    )
    zero_vector, zero_reason = build_feature_vector(zero_range, flat_instant)
    if zero_vector is None:
        raise RuntimeError(f"the zero-range fixture is not feature-valid: {zero_reason}")
    checks["zero_range_close_position_value"] = all(
        zero_vector[position] == ZERO_RANGE_CLOSE_POSITION_VALUE for position in (14, 15)
    )

    # Reconciliation: the V2 family calls the one frozen V1 builder, not a transcription.
    fixtures = tuple(bar.open_time for bar in bars[REQUIRED_BARS - 1 :])
    reconciliation = reconcile_with_v1(index, fixtures)
    checks["fixed_fixture_vectors_identical_to_v1_definition"] = reconciliation[
        "identical_to_v1_definition"
    ]
    checks["feature_identity_inherits_v1_definition"] = (
        INHERITED_FROM == "PREDICTIVE_INTERNAL_CAUSAL_FEATURES_V1"
        and feature_contract()["definition_rewritten"] is False
        and list(FEATURE_NAMES) == feature_contract()["ordered_names"]
        and FEATURE_COUNT == 18
    )

    # No stored V1 model output may be reachable from the V2 implementation. Two precise
    # static statements, not a claim about intent: the V2 modules never import a Generation
    # V1 fitting/prediction module, and no function on the execution path opens any file.
    # Prior results are read in exactly one place -- `admission`, byte-wise, for a digest.
    leaked: list[str] = []
    forbidden_imports = (
        "internal_model",
        "internal_structure",
        "internal_report",
        "internal_nonlinear",
    )
    v2_modules = [name for name in IMPLEMENTATION_FILES if name.endswith(".py")]
    for relative in v2_modules:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for needle in forbidden_imports:
            if f"import {needle}" in text or f"from .{needle}" in text:
                leaked.append(f"{relative}:{needle}")
    checks["no_v1_fitting_or_prediction_module_imported"] = not leaked

    execution_path = (
        run_family,
        _execute_configuration,
        _fit_fold,
        feature_cache,
        fit_probability_head,
    )
    readers = [
        function.__name__
        for function in execution_path
        if any(
            needle in inspect.getsource(function)
            for needle in ("json.loads", "read_text", "read_bytes", "RESULT_PATHS")
        )
    ]
    checks["execution_path_opens_no_result_artifact"] = not readers
    leaked.extend(readers)

    bars_installed = load_hourly_ohlcv(ROOT)
    label_bars = tuple(
        Bar(open_time=bar.open_time, close=bar.close, complete=bar.complete)
        for bar in bars_installed
    )
    labels = build_labels(label_bars, horizon_hours=HORIZON_HOURS)
    folds = build_folds(
        labels.labels,
        horizon_hours=HORIZON_HOURS,
        purge_embargo_hours=PURGE_EMBARGO_HOURS,
    )
    assert_no_boundary_leak(folds)
    cache, unavailability = feature_cache(index_ohlcv(bars_installed), labels.labels)
    outer_valid = sum(
        1 for fold in folds.folds for label in fold.evaluation if label.open_time in cache
    )
    checks["every_available_vector_is_finite_width_eighteen"] = all(
        len(vector) == FEATURE_COUNT and all(math.isfinite(value) for value in vector)
        for vector in cache.values()
    )
    checks["unavailability_is_counted_not_filled"] = len(labels.labels) - len(cache) == sum(
        unavailability.values()
    )

    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"internal causal feature proof failed: {failed} {leaked}")
    return {
        "version": "PREDICTIVE_V2_INTERNAL_STRUCTURE_SELECTIVE_FEATURE_PROOFS_V1",
        "status": "PASS_BEFORE_FIRST_MODEL_FIT",
        "feature_set": FEATURE_SET_VERSION,
        "inherits_definition_from": INHERITED_FROM,
        "ordered_names": list(FEATURE_NAMES),
        "feature_count": FEATURE_COUNT,
        "checks": checks,
        "v1_reconciliation": reconciliation,
        "eligible_development_timestamps": len(labels.labels),
        "eligible_development_vectors_valid": len(cache),
        "eligible_development_feature_validity": len(cache) / len(labels.labels),
        "outer_fold_eligible_timestamps": folds.eligible_total(),
        "outer_fold_vectors_valid": outer_valid,
        "outer_fold_feature_validity": outer_valid / folds.eligible_total(),
        "unavailability_by_reason": unavailability,
        "stage1_substrate_debt_repaired": False,
        "prior_v1_results_pinned": len(PRIOR_V1_RESULT_PATHS),
        "prior_v2_results_pinned": len(PRIOR_V2_RESULT_PATHS),
        "folds": [fold.name for fold in folds.folds],
        "model_fits": 0,
        "outer_predictions": 0,
        "sealed_queries": 0,
    }


def main() -> None:
    proof = build_proof()
    path = ROOT / FEATURE_PROOF_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(proof))
    print(
        "internal causal feature proofs: "
        f"{proof['status']} validity={proof['outer_fold_feature_validity']}"
    )


if __name__ == "__main__":
    main()
