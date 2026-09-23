"""Pre-execution power gate for `EXP-PRED-V2-006-PUBLIC-TAKER-FLOW-1H-INCREMENTAL`.

Frozen definition: the "Pre-execution power gate" section of
`research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-V1.md` (ADR-0033).

`MDE_IS_ANALOG_EXPECTED_DETECTABILITY_NOT_REALIZED_INCREMENTAL_VARIANCE`

The gate estimates expected detectability under a frozen analogous dependence and noise
assumption (`ANALOG_DEPENDENCE_AND_VARIANCE_PROXY`). The proxy series is the already exposed
EXP-PRED-V2-005 1h per-row `FLOW_ONLY_BRIER_LOSS - TRAINING_BASE_RATE_CONSTANT_BRIER_LOSS`.
It is rebuilt by running the frozen foundation's own `evaluate_horizon` for 1h, unchanged,
and capturing the scored folds it hands to its bootstrap. Before the series is used, that
replay must reproduce the committed 1h result exactly; otherwise the gate records
`POWER_GATE_FAILED_CLOSED` and computes no power.

Nothing here constructs a price feature, a price-only control or a price-plus-flow candidate,
and nothing here reads an EXP-PRED-V2-006 outcome: those predictions do not exist.

Power: `D0` is the 48h fold-stratified moving-block bootstrap distribution of the pooled
proxy mean (10,000 replicates, chunks of 500, `numpy.random.default_rng(2026092307)`,
folds 2021..2024 in order, blocks never crossing a fold), centred by the observed pooled mean.
`power(delta) = mean over d in D0 of [delta + d + quantile_0.025(D0) > 0]`, evaluated
literally. The MDE is the smallest `delta = k * 1e-7`, `k = 0..100000`, with power >= 0.80,
found by bisection over `k`; bisection is exact because `delta + d + q` is non-decreasing in
`delta` under IEEE rounding, and every probe evaluates the literal formula.
"""

from __future__ import annotations

import contextlib
import json
import math
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

from ..research.text_provenance import CANONICAL_TEXT_RULE, canonical_text_sha256
from . import taker_flow_foundation as foundation
from .paired_inference import block_sums
from .taker_flow_foundation import (
    FEATURE_NAMES,
    HOUR_SECONDS,
    OUTER_FOLD_YEARS,
    RESULT_PATH,
    ScoredFold,
    build_panel,
    horizon_seed_sequences,
)
from .taker_flow_source import MANIFEST_PATH, load_minute_books

ROOT = Path(__file__).resolve().parents[3]

RECORD_ID = "PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1"
GATE_JSON_PATH = f"reports/validation/{RECORD_ID}.json"
GATE_MARKDOWN_PATH = f"reports/validation/{RECORD_ID}.md"
GATE_PATHS = (GATE_JSON_PATH, GATE_MARKDOWN_PATH)
INCREMENTAL_PROTOCOL_PATH = (
    "research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-V1.md"
)
FOUNDATION_PROTOCOL_PATH = (
    "research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md"
)
DECISION_RECORD = (
    "decisions/ADR-0033-PUBLIC-TAKER-FLOW-FOUNDATION-1H-ONLY-AND-INCREMENTAL-ALLOCATION.md"
)
EXPERIMENT_ID = "EXP-PRED-V2-006-PUBLIC-TAKER-FLOW-1H-INCREMENTAL"
HYPOTHESIS_ID = "H-PRED-V2-PUBLIC-FLOW-INCREMENTAL-001"
SOURCE_EXPERIMENT_ID = foundation.EXPERIMENT_ID
CODE_DEPENDENCIES = (
    "backend/app/predictive/taker_flow_power_gate.py",
    "backend/app/predictive/taker_flow_foundation.py",
    "backend/app/predictive/taker_flow_source.py",
    "backend/app/predictive/paired_inference.py",
    "backend/app/research/text_provenance.py",
    "scripts/run_public_taker_flow_1h_incremental_power_gate.py",
)
TEXT_DEPENDENCIES = (
    INCREMENTAL_PROTOCOL_PATH,
    FOUNDATION_PROTOCOL_PATH,
    DECISION_RECORD,
    RESULT_PATH,
    MANIFEST_PATH,
    *CODE_DEPENDENCIES,
)

MDE_STATEMENT = "MDE_IS_ANALOG_EXPECTED_DETECTABILITY_NOT_REALIZED_INCREMENTAL_VARIANCE"
PROXY_CLASSIFICATION = "ANALOG_DEPENDENCE_AND_VARIANCE_PROXY"
PROXY_SERIES = "FLOW_ONLY_BRIER_LOSS - TRAINING_BASE_RATE_CONSTANT_BRIER_LOSS"
PROXY_HORIZON_HOURS = 1
MESI = 0.0002
ALPHA = 0.05
INTERVAL_MASS = 0.95
LOWER_QUANTILE = ALPHA / 2
TARGET_POWER = 0.80
BLOCK_LENGTH_HOURS = 48
REPLICATES = 10_000
REPLICATE_CHUNK = 500
POWER_GATE_SEED = 2026092307
GRID_STEP = 1e-7
GRID_MAX_K = 100_000

PASSES = "ANALOG_POWER_GATE_PASSES_PENDING_RESEARCH_DIRECTOR_REVIEW"
BLOCKED = "POWER_BLOCKED_NOT_EXECUTED"
FAILED_CLOSED = "POWER_GATE_FAILED_CLOSED"
CLASSIFICATIONS = (PASSES, BLOCKED, FAILED_CLOSED)


class PowerGateError(RuntimeError):
    """The power gate was asked for something its frozen definition does not allow."""


class ProxyReplayMismatch(PowerGateError):
    """The replayed proxy does not reproduce the committed EXP-PRED-V2-005 1h result."""


# --------------------------------------------------------------------------------------
# Exact replay of the exposed foundation's 1h scored folds.
# --------------------------------------------------------------------------------------


@contextlib.contextmanager
def _capture_scored_folds() -> Iterator[list[Sequence[ScoredFold]]]:
    """Record the scored folds the frozen `evaluate_horizon` passes to its own bootstrap.

    The frozen function is called unchanged and its bootstrap still runs, so the replayed
    summary can be compared with the committed result field for field.
    """
    captured: list[Sequence[ScoredFold]] = []
    original = foundation.bootstrap_interval

    def recording(folds: Sequence[ScoredFold], *args: Any, **kwargs: Any) -> dict[str, Any]:
        captured.append(tuple(folds))
        return original(folds, *args, **kwargs)

    foundation.bootstrap_interval = recording  # type: ignore[assignment]
    try:
        yield captured
    finally:
        foundation.bootstrap_interval = original  # type: ignore[assignment]


def replay_proxy_folds(panel: foundation.HourlyPanel) -> tuple[dict[str, Any], list[ScoredFold]]:
    """The frozen 1h foundation summary and the per-row proxy series behind it."""
    if panel.features.shape[1] != len(FEATURE_NAMES):
        raise PowerGateError("the replay panel must hold exactly the three frozen flow features")
    seed = horizon_seed_sequences()[PROXY_HORIZON_HOURS]
    with _capture_scored_folds() as captured:
        summary = foundation.evaluate_horizon(panel, PROXY_HORIZON_HOURS, seed)
    if len(captured) != 1:
        raise PowerGateError("the foundation replay did not expose exactly one fold set")
    return summary, list(captured[0])


def verify_replay(
    summary: Mapping[str, Any], folds: Sequence[ScoredFold], committed: Mapping[str, Any]
) -> list[str]:
    """Every check the proxy must pass before use; raises on the first mismatch."""
    import numpy as np

    expected = committed["horizons"][str(PROXY_HORIZON_HOURS)]
    checks = []

    def require(condition: bool, name: str) -> None:
        if not condition:
            raise ProxyReplayMismatch(name)
        checks.append(name)

    require([fold.year for fold in folds] == list(OUTER_FOLD_YEARS), "FOLD_YEARS")
    require(json.loads(json.dumps(summary)) == expected, "FULL_1H_SUMMARY_EQUALS_COMMITTED")
    require(summary["scored_rows"] == expected["scored_rows"], "POOLED_SCORED_ROWS")
    total = sum(int(np.asarray(fold.differences).shape[0]) for fold in folds)
    require(total == expected["scored_rows"], "PROXY_ROW_COUNT")
    pooled = float(np.concatenate([np.asarray(f.differences) for f in folds]).mean())
    require(
        math.isclose(pooled, expected["pooled_brier_improvement"], rel_tol=0, abs_tol=1e-15),
        "POOLED_BRIER_IMPROVEMENT",
    )
    for fold, item in zip(folds, expected["folds"], strict=True):
        differences = np.asarray(fold.differences)
        require(fold.year == item["year"], f"FOLD_{fold.year}_IDENTITY")
        require(differences.shape[0] == item["scored_rows"], f"FOLD_{fold.year}_SCORED_ROWS")
        require(
            math.isclose(
                float(differences.mean()), item["brier_improvement"], rel_tol=0, abs_tol=1e-15
            ),
            f"FOLD_{fold.year}_BRIER_IMPROVEMENT",
        )
    return checks


# --------------------------------------------------------------------------------------
# Empirical noise distribution, power and MDE.
# --------------------------------------------------------------------------------------


def observed_pooled_mean(folds: Sequence[ScoredFold]) -> float:
    import numpy as np

    return float(np.concatenate([np.asarray(fold.differences) for fold in folds]).mean())


def replicate_statistics(
    folds: Sequence[ScoredFold],
    block_hours: int = BLOCK_LENGTH_HOURS,
    replicates: int = REPLICATES,
    seed: int = POWER_GATE_SEED,
    chunk: int = REPLICATE_CHUNK,
) -> tuple[Any, dict[str, dict[str, int]]]:
    """Pooled proxy mean of every moving-block replicate, and the per-fold draw geometry.

    Blocks are contiguous on each fold's hourly timeline (an unscored hour keeps its slot and
    contributes nothing) and are drawn independently inside each fold in chronological
    order, so no block crosses a fold boundary.
    """
    import numpy as np

    if not folds or replicates <= 0 or chunk <= 0 or block_hours <= 0:
        raise PowerGateError("the bootstrap needs folds and a positive budget")
    generator = np.random.default_rng(seed)
    totals = np.zeros(replicates, dtype=np.float64)
    counts = np.zeros(replicates, dtype=np.float64)
    geometry: dict[str, dict[str, int]] = {}
    for fold in folds:
        span = fold.span_hours
        slots = ((np.asarray(fold.times) - fold.first_time) // HOUR_SECONDS).astype(np.int64)
        if slots.shape[0] and (slots.min() < 0 or slots.max() >= span):
            raise PowerGateError(f"{fold.year}: a scored row sits outside its fold timeline")
        values = np.zeros(span, dtype=np.float64)
        present = np.zeros(span, dtype=np.float64)
        values[slots] = fold.differences
        present[slots] = 1.0
        full_v, partial_v, draws, block = block_sums(values, block_hours)
        full_p, partial_p, _, _ = block_sums(present, block_hours)
        starts_available = int(full_v.shape[0])
        geometry[str(fold.year)] = {
            "timeline_hours": span,
            "effective_block_hours": block,
            "blocks_per_replicate": draws,
            "block_start_positions": starts_available,
            "scored_rows": int(slots.shape[0]),
        }
        done = 0
        while done < replicates:
            size = min(chunk, replicates - done)
            starts = generator.integers(0, starts_available, size=(size, draws))
            head, tail = starts[:, : draws - 1], starts[:, draws - 1]
            totals[done : done + size] += full_v[head].sum(axis=1) + partial_v[tail]
            counts[done : done + size] += full_p[head].sum(axis=1) + partial_p[tail]
            done += size
    if not np.all(counts > 0):
        raise PowerGateError("a bootstrap replicate resampled no scored row")
    return totals / counts, geometry


def noise_distribution(statistics: Any, observed: float) -> Any:
    """`D0`: replicate pooled statistics centred by the observed pooled proxy mean."""
    import numpy as np

    return np.asarray(statistics, dtype=np.float64) - observed


def lower_quantile(d0: Any) -> float:
    import numpy as np

    return float(np.quantile(d0, LOWER_QUANTILE))


def power(delta: float, d0: Any, quantile: float) -> float:
    """`mean over d in D0 of [delta + d + quantile_0.025(D0) > 0]`, literally."""
    import numpy as np

    return float(np.mean(delta + d0 + quantile > 0))


def minimum_detectable_effect(d0: Any, quantile: float) -> dict[str, Any]:
    """Smallest grid effect `k * 1e-7` (k = 0..100000) reaching the target power."""

    def reaches(k: int) -> bool:
        return power(k * GRID_STEP, d0, quantile) >= TARGET_POWER

    if not reaches(GRID_MAX_K):
        return {"reached": False, "k": None, "mde": None, "power_at_mde": None}
    low, high = -1, GRID_MAX_K  # reaches(high) holds; low is the largest known failure
    while high - low > 1:
        middle = (low + high) // 2
        if reaches(middle):
            high = middle
        else:
            low = middle
    if high > 0 and reaches(high - 1):
        raise PowerGateError("expected power is not monotone on the MDE grid")
    mde = high * GRID_STEP
    return {"reached": True, "k": high, "mde": mde, "power_at_mde": power(mde, d0, quantile)}


def classify(power_at_mesi: float) -> str:
    return PASSES if power_at_mesi >= TARGET_POWER else BLOCKED


def power_analysis(folds: Sequence[ScoredFold]) -> dict[str, Any]:
    import numpy as np

    statistics, geometry = replicate_statistics(folds)
    observed = observed_pooled_mean(folds)
    d0 = noise_distribution(statistics, observed)
    quantile = lower_quantile(d0)
    at_mesi = power(MESI, d0, quantile)
    return {
        "observed_pooled_proxy_mean": observed,
        "proxy_fold_means": {
            str(fold.year): float(np.asarray(fold.differences).mean()) for fold in folds
        },
        "bootstrap_geometry": geometry,
        "noise_distribution": {
            "definition": "REPLICATE_POOLED_STATISTIC_MINUS_OBSERVED_POOLED_PROXY_MEAN",
            "replicates": int(d0.shape[0]),
            "mean": float(d0.mean()),
            "standard_deviation": float(d0.std(ddof=1)),
            "quantile_0_025": quantile,
            "quantile_0_975": float(np.quantile(d0, 1 - LOWER_QUANTILE)),
            "minimum": float(d0.min()),
            "maximum": float(d0.max()),
        },
        "power_at_mesi": at_mesi,
        "mde": minimum_detectable_effect(d0, quantile),
        "classification": classify(at_mesi),
    }


# --------------------------------------------------------------------------------------
# Governed record.
# --------------------------------------------------------------------------------------


def text_dependencies(root: Path) -> list[dict[str, str]]:
    return [
        {
            "path": path,
            "rule": CANONICAL_TEXT_RULE,
            "canonical_text_sha256": canonical_text_sha256(root / path),
        }
        for path in TEXT_DEPENDENCIES
    ]


def design() -> dict[str, Any]:
    return {
        "metric": "ABSOLUTE_PAIRED_BRIER_IMPROVEMENT",
        "mesi": MESI,
        "mesi_lowerable_after_block": False,
        "alpha": ALPHA,
        "interval_mass": INTERVAL_MASS,
        "target_power": TARGET_POWER,
        "proxy_classification": PROXY_CLASSIFICATION,
        "proxy_series": PROXY_SERIES,
        "proxy_source_experiment_id": SOURCE_EXPERIMENT_ID,
        "proxy_horizon_hours": PROXY_HORIZON_HOURS,
        "outer_fold_years": list(OUTER_FOLD_YEARS),
        "bootstrap": {
            "method": "FOLD_STRATIFIED_MOVING_BLOCK_ON_HOURLY_TIMELINE",
            "block_length_hours": BLOCK_LENGTH_HOURS,
            "blocks_cross_fold_boundaries": False,
            "replicates": REPLICATES,
            "replicate_chunk": REPLICATE_CHUNK,
            "seed": POWER_GATE_SEED,
        },
        "power_rule": "MEAN_OVER_D0_OF_DELTA_PLUS_D_PLUS_QUANTILE_0_025_OF_D0_ABOVE_ZERO",
        "quantile_method": "NUMPY_QUANTILE_LINEAR",
        "mde_grid": {"step": GRID_STEP, "k_min": 0, "k_max": GRID_MAX_K},
        "mde_search": "BISECTION_OVER_K_WITH_LITERAL_POWER_EVALUATION",
        "pass_classification": PASSES,
        "block_classification": BLOCKED,
        "failed_closed_classification": FAILED_CLOSED,
    }


def boundaries() -> dict[str, Any]:
    return {
        "price_features_constructed": False,
        "price_only_or_price_plus_flow_predictions_used": False,
        "incremental_experiment_model_fits": 0,
        "observed_incremental_effect_used": False,
        "foundation_models_refitted_for_exact_replay_only": True,
        "execution_authorized": False,
        "pass_authorizes_execution": False,
        "research_director_review_required": True,
        "sealed_queries": 0,
        "post_cutoff_data_used": False,
        "champion_status": "NONE",
        "real_money": False,
    }


def build_record(
    root: Path,
    classification: str,
    replay: dict[str, Any],
    analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    if classification not in CLASSIFICATIONS:
        raise PowerGateError(f"unknown power-gate classification {classification}")
    return {
        "schema_version": 1,
        "record": RECORD_ID,
        "statement": MDE_STATEMENT,
        "experiment_id": EXPERIMENT_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "decision_record": DECISION_RECORD,
        "protocol": INCREMENTAL_PROTOCOL_PATH,
        "classification": classification,
        "design": design(),
        "replay": replay,
        "analysis": analysis,
        "text_dependencies": text_dependencies(root),
        "boundaries": boundaries(),
    }


def run_power_gate(root: Path = ROOT) -> dict[str, Any]:
    """Replay the exposed proxy exactly, then compute the frozen power gate once."""
    committed = json.loads((root / RESULT_PATH).read_text(encoding="utf-8"))
    books, _ = load_minute_books(root)
    panel = build_panel(books)
    summary, folds = replay_proxy_folds(panel)
    replay: dict[str, Any]
    try:
        checks = verify_replay(summary, folds, committed)
    except ProxyReplayMismatch as mismatch:
        replay = {
            "status": "MISMATCH_FAILED_CLOSED",
            "failed_check": str(mismatch),
            "source_result": RESULT_PATH,
        }
        return build_record(root, FAILED_CLOSED, replay, None)
    replay = {
        "status": "REPRODUCED_EXACTLY",
        "checks": checks,
        "source_result": RESULT_PATH,
        "scored_rows": summary["scored_rows"],
        "pooled_brier_improvement": summary["pooled_brier_improvement"],
    }
    analysis = power_analysis(folds)
    return build_record(root, analysis["classification"], replay, analysis)


def canonical_json_bytes(record: Mapping[str, Any]) -> bytes:
    return (json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _fmt(value: float | None, digits: int = 7) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def markdown_bytes(record: Mapping[str, Any]) -> bytes:
    lines = [
        f"# {RECORD_ID}",
        "",
        f"**`{record['statement']}`**",
        "",
        "The minimum detectable effect below is expected detectability under the frozen",
        f"`{PROXY_CLASSIFICATION}` assumption. It is not the variance of the realized",
        "price-only versus price-plus-flow contrast, which has not been computed.",
        "",
        f"Experiment: `{record['experiment_id']}` — hypothesis `{record['hypothesis_id']}`",
        f"Protocol: `{record['protocol']}`",
        "",
        f"**Classification: `{record['classification']}`**",
        "",
    ]
    analysis = record["analysis"]
    if analysis is None:
        lines += [
            (
                f"Proxy replay: `{record['replay']['status']}` "
                f"(failed check `{record['replay']['failed_check']}`). No power was computed."
            ),
            "",
        ]
    else:
        noise = analysis["noise_distribution"]
        mde = analysis["mde"]
        mde_text = _fmt(mde["mde"]) if mde["reached"] else "NOT_REACHED"
        lines += [
            (
                f"Proxy replay: `{record['replay']['status']}` "
                f"({len(record['replay']['checks'])} checks, "
                f"{record['replay']['scored_rows']} scored rows)."
            ),
            "",
            "| Quantity | Value |",
            "|---|---|",
            f"| MESI | {_fmt(MESI)} |",
            f"| Expected power at MESI | {_fmt(analysis['power_at_mesi'], 4)} |",
            f"| Target power | {_fmt(TARGET_POWER, 2)} |",
            f"| Empirical MDE (grid 1e-7) | {mde_text} |",
            f"| Observed pooled proxy mean | {_fmt(analysis['observed_pooled_proxy_mean'])} |",
            f"| D0 standard deviation | {_fmt(noise['standard_deviation'])} |",
            f"| D0 2.5% quantile | {_fmt(noise['quantile_0_025'])} |",
            "",
        ]
    lines += [
        "A pass does not authorize EXP-PRED-V2-006; Research Director review is mandatory.",
        "No price feature, price-only or price-plus-flow prediction, EXP-PRED-V2-006 fit,",
        "sealed or post-cutoff data was used. Champion NONE. Real money false.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def validate_record(record: Mapping[str, Any], root: Path = ROOT) -> None:
    """Internal consistency of a written gate record; recomputes nothing from market data."""

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise PowerGateError(message)

    require(record["record"] == RECORD_ID and record["statement"] == MDE_STATEMENT, "identity")
    require(record["experiment_id"] == EXPERIMENT_ID, "experiment identity")
    require(record["hypothesis_id"] == HYPOTHESIS_ID, "hypothesis identity")
    require(record["design"] == json.loads(json.dumps(design())), "frozen design drift")
    require(record["boundaries"] == boundaries(), "boundary drift")
    declared = {item["path"]: item for item in record["text_dependencies"]}
    require(set(declared) == set(TEXT_DEPENDENCIES), "text dependency set drift")
    for path, item in declared.items():
        require(item["rule"] == CANONICAL_TEXT_RULE, f"{path}: rule drift")
        require(
            canonical_text_sha256(root / path) == item["canonical_text_sha256"],
            f"{path}: canonical text differs from the gate record",
        )
    analysis = record["analysis"]
    if record["classification"] == FAILED_CLOSED:
        require(analysis is None, "a failed-closed gate may not report power")
        require(record["replay"]["status"] == "MISMATCH_FAILED_CLOSED", "replay status drift")
        return
    require(record["replay"]["status"] == "REPRODUCED_EXACTLY", "replay status drift")
    require(analysis is not None, "a computed gate must report its analysis")
    require(analysis["classification"] == record["classification"], "classification drift")
    require(classify(analysis["power_at_mesi"]) == record["classification"], "verdict drift")
    require(0.0 <= analysis["power_at_mesi"] <= 1.0, "power out of range")
    mde = analysis["mde"]
    if mde["reached"]:
        require(0 <= mde["k"] <= GRID_MAX_K, "MDE grid index out of range")
        require(mde["mde"] == mde["k"] * GRID_STEP, "MDE grid arithmetic drift")
        require(mde["power_at_mde"] >= TARGET_POWER, "MDE below target power")
    else:
        require(record["classification"] == BLOCKED, "an unreached MDE cannot pass")
    require(analysis["noise_distribution"]["replicates"] == REPLICATES, "replicate drift")


__all__ = [
    "BLOCKED",
    "CLASSIFICATIONS",
    "FAILED_CLOSED",
    "GATE_JSON_PATH",
    "GATE_MARKDOWN_PATH",
    "GATE_PATHS",
    "MDE_STATEMENT",
    "PASSES",
    "PowerGateError",
    "ProxyReplayMismatch",
    "build_record",
    "canonical_json_bytes",
    "classify",
    "lower_quantile",
    "markdown_bytes",
    "minimum_detectable_effect",
    "noise_distribution",
    "observed_pooled_mean",
    "power",
    "power_analysis",
    "replay_proxy_folds",
    "replicate_statistics",
    "run_power_gate",
    "validate_record",
    "verify_replay",
]
