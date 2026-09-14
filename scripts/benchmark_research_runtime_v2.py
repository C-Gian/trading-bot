"""Benchmark and equivalence proof for RESEARCH_RUNTIME_V2_BATCH.

The governed path reproduces one already-exposed WP-015 fold/model on development data.
It creates engineering evidence only: no experiment result, scientific counter, sealed
query, or WP-016 path is touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.continuation_lab import ResearchInputs
from app.research.evaluation_protocol import utc_us
from app.research.funding import load_funding_context
from app.research.runtime_v2 import (
    PREDICTION_TOLERANCE,
    RUNTIME_VERSION,
    StageTimer,
    build_profile_prediction_views,
    predict_ordered,
)
from app.research.supervised import load_feature_source
from app.research.wp014_model import HGBR_PARAMETERS
from app.research.wp015 import (
    PRIMARY_VARIANT,
    dependency_manifest,
    load_walk_forward,
)
from app.research.wp015_lab import FundingContextLab

DEFAULT_OUTPUT = ROOT / "reports/benchmarks/RESEARCH-RUNTIME-V2-BATCH.json"
KNOWN_WP015_RUNTIME_SECONDS = 1067.810941
SEED = 20260914


def _hash_json(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _prediction_benchmark(model: Any, signal_ids: tuple[int, ...], matrix: np.ndarray) -> dict:
    started = perf_counter()
    rowwise = np.asarray([model.predict(row[None, :])[0] for row in matrix], dtype=np.float64)
    rowwise_seconds = perf_counter() - started
    started = perf_counter()
    batched = predict_ordered(model, signal_ids, matrix)
    batch_seconds = perf_counter() - started
    batch_values = np.asarray(batched.values, dtype=np.float64)
    maximum = float(np.max(np.abs(rowwise - batch_values))) if len(rowwise) else 0.0
    mismatches = int(np.count_nonzero((rowwise > 0.0) != (batch_values > 0.0)))
    if maximum > PREDICTION_TOLERANCE or mismatches:
        raise RuntimeError("batch prediction failed its engineering equivalence gate")
    return {
        "rows": len(signal_ids),
        "rowwise_seconds": rowwise_seconds,
        "batch_seconds": batch_seconds,
        "speedup": rowwise_seconds / batch_seconds,
        "max_abs_prediction_difference": maximum,
        "signal_mismatch_count": mismatches,
        "rowwise_predictions": rowwise,
        "batched_predictions": batched,
    }


def synthetic_benchmark(rows: int) -> dict[str, Any]:
    rng = np.random.default_rng(SEED)
    training = rng.normal(size=(4000, 8))
    labels = training[:, 0] * 0.20 - training[:, 3] * 0.10 + np.sin(training[:, 5]) * 0.05
    validation = rng.normal(size=(rows, 8))
    model = HistGradientBoostingRegressor(**HGBR_PARAMETERS).fit(training, labels)
    measured = _prediction_benchmark(model, tuple(range(rows)), validation)
    measured.pop("rowwise_predictions")
    measured.pop("batched_predictions")
    return measured


def _feature_values(lab: FundingContextLab, signal_us: int, width: int) -> tuple[float, ...]:
    row = lab.row(signal_us)
    if row is None:
        raise RuntimeError("governed WP-015 sample unexpectedly contains an ineligible row")
    return (*row.values, lab.funding_values[signal_us][1]) if width == 9 else tuple(row.values)


def governed_wp015_benchmark(sample_rows: int) -> tuple[dict[str, Any], dict[str, Any]]:
    state_path = ROOT / "state/current_state.json"
    state_before = hashlib.sha256(state_path.read_bytes()).hexdigest()
    timer = StageTimer()
    with timer.measure("LOAD_DATA"):
        inputs = ResearchInputs.load(ROOT)
        features = load_feature_source(ROOT)
        funding = load_funding_context(ROOT)
        walk = load_walk_forward(ROOT)
    lab = FundingContextLab(inputs, features, funding, walk)
    lab.dependencies = dependency_manifest(ROOT)
    fold = walk["folds"][0]
    lab.folds = [fold]
    with timer.measure("FIT"):
        fitted = lab.fit_fold(PRIMARY_VARIANT, fold)
    committed_models = json.loads(
        (
            ROOT / "research/experiments/EXP-ML-024-INTERNAL-PLUS-FUNDING-HGBR/fold-models.json"
        ).read_text(encoding="utf-8")
    )["fold_models"]
    committed_identity = next(
        item["model"]["identity_sha256"]
        for item in committed_models
        if item["fold_id"] == fold["fold_id"]
    )
    if fitted.model.identity_sha256 != committed_identity:
        raise RuntimeError("governed reproduction did not recover the committed WP-015 model")
    start = int(fitted.manifest["validation_start_us"])
    stop = utc_us(fold["last_signal_inclusive"])
    signals: list[int] = []
    with timer.measure("BUILD_FEATURES"):
        cursor = start - 3_600_000_000
        while cursor <= stop and len(signals) < sample_rows + 1:
            if lab.row(cursor) is not None:
                signals.append(cursor)
            cursor += 3_600_000_000
        if len(signals) < sample_rows + 1:
            raise RuntimeError("governed WP-015 fold is too short for the requested sample")
        matrix = np.asarray(
            [_feature_values(lab, signal, len(fitted.model.feature_order)) for signal in signals],
            dtype=np.float64,
        )
    with timer.measure("PREDICT"):
        measured = _prediction_benchmark(fitted.model, tuple(signals), matrix)
    rowwise = measured.pop("rowwise_predictions")
    batched = measured.pop("batched_predictions")
    rowwise_mapping = dict(zip(signals, (float(value) for value in rowwise), strict=True))
    batch_mapping = batched.as_mapping()
    evaluation_signals = tuple(signal for signal in signals if signal >= start)
    views = build_profile_prediction_views(batched, evaluation_signals)
    if not (views["DEFAULT"] is views["ZERO"] is views["DOUBLE"]):
        raise RuntimeError("cost profiles did not reuse the identical prediction view")
    legacy_delay = tuple(
        rowwise_mapping[signal - 3_600_000_000]
        for signal in evaluation_signals
        if signal - 3_600_000_000 in rowwise_mapping
    )
    if legacy_delay != views["DELAY_1H"].values:
        raise RuntimeError("DELAY_1H prediction alignment changed")
    with timer.measure("PROFILES"):
        legacy_profile = lab.run_profile(PRIMARY_VARIANT, rowwise_mapping, "DEFAULT")
        batch_profile = lab.run_profile(PRIMARY_VARIANT, batch_mapping, "DEFAULT")
    identity_fields = ("fold_id", "signal_us", "prediction_signal_us", "status", "reason")
    legacy_identities = [
        tuple(trade.get(field) for field in identity_fields) for trade in legacy_profile["trades"]
    ]
    batch_identities = [
        tuple(trade.get(field) for field in identity_fields) for trade in batch_profile["trades"]
    ]
    if legacy_identities != batch_identities:
        raise RuntimeError("governed WP-015 trade identities changed")
    legacy_metrics = legacy_profile["summary"]["metrics"]
    batch_metrics = batch_profile["summary"]["metrics"]
    if legacy_metrics != batch_metrics:
        raise RuntimeError("governed WP-015 metrics changed")
    with timer.measure("FINALIZE"):
        state_after = hashlib.sha256(state_path.read_bytes()).hexdigest()
        if state_after != state_before:
            raise RuntimeError("engineering benchmark changed canonical scientific state")
    return (
        {
            **measured,
            "fold_id": fold["fold_id"],
            "variant": PRIMARY_VARIANT,
            "model_identity_sha256": fitted.model.identity_sha256,
            "committed_model_identity_matched": True,
            "training_matrix_logical_sha256": fitted.manifest["training_matrix_logical_sha256"],
            "sample_matrix_sha256": hashlib.sha256(
                np.asarray(signals, dtype=np.int64).tobytes() + matrix.tobytes()
            ).hexdigest(),
            "signal_decisions_identical": True,
            "trade_identities_identical": True,
            "trade_identity_sha256": _hash_json(batch_identities),
            "trade_count": len(batch_identities),
            "metrics_identical": True,
            "metrics_sha256": _hash_json(batch_metrics),
            "cost_profile_prediction_object_reused": True,
            "delay_alignment_identical": True,
            "scientific_state_sha256": state_after,
        },
        timer.as_record(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--synthetic-rows", type=int, default=10_000)
    parser.add_argument("--governed-rows", type=int, default=512)
    args = parser.parse_args()
    if args.synthetic_rows <= 0 or args.governed_rows <= 0:
        parser.error("benchmark row counts must be positive")
    synthetic = synthetic_benchmark(args.synthetic_rows)
    governed, timings = governed_wp015_benchmark(args.governed_rows)
    payload = {
        "benchmark_version": "RESEARCH_RUNTIME_V2_BATCH_BENCHMARK_V1",
        "classification": "ENGINEERING_EQUIVALENCE_REPRODUCTION",
        "runtime_version": RUNTIME_VERSION,
        "scientific_evidence": False,
        "experiment_counter_increment": 0,
        "sealed_queries": 0,
        "wp016_executed": False,
        "known_full_wp015_reproduction_seconds": KNOWN_WP015_RUNTIME_SECONDS,
        "whole_experiment_speedup_claimed": False,
        "prediction_tolerance": PREDICTION_TOLERANCE,
        "seed": SEED,
        "numpy_version": np.__version__,
        "sklearn_version": sklearn.__version__,
        "synthetic_prediction": synthetic,
        "governed_wp015_prediction_and_profile": governed,
        "governed_stage_timings": timings,
        "governed_timing_scope": (
            "Frozen WP-015 fit_fold combines training feature/label construction and model fit "
            "inside FIT; zero BUILD_LABELS is not a claim of zero label cost."
        ),
        "cache_implemented": False,
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(payload, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
