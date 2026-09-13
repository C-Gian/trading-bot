"""Independent WP-015 reconstruction; never imports its primary lab or runner."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import pickle
import sys
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.backtest.engine import simulate
from app.backtest.models import ExitReason, Intent
from app.research.continuation_lab import DATASET_HASH, DATASET_ID, ResearchInputs, costs
from app.research.evaluation_protocol import EPOCH, HOUR_US, utc_us
from app.research.supervised import (
    FULL_FEATURES,
    LABEL_VERSION,
    SupervisedDataError,
    isolated_label,
    load_feature_source,
)

PRIMARY = "INTERNAL_PLUS_FUNDING_HGBR"
CONTROL = "INTERNAL_HGBR_MATCHED_FUNDING"
VARIANTS = (PRIMARY, CONTROL)
EXPERIMENTS = {
    PRIMARY: "EXP-ML-024-INTERNAL-PLUS-FUNDING-HGBR",
    CONTROL: "EXP-ML-025-INTERNAL-HGBR-MATCHED-FUNDING",
}
PARAMETERS: dict[str, Any] = {
    "loss": "squared_error",
    "learning_rate": 0.05,
    "max_iter": 64,
    "max_leaf_nodes": 7,
    "max_depth": 3,
    "min_samples_leaf": 128,
    "l2_regularization": 1.0,
    "max_bins": 63,
    "early_stopping": False,
    "random_state": 0,
}
FEATURE = "LATEST_SETTLED_FUNDING_RATE"
TOLERANCE = 1e-10
MINUTE_US = 60_000_000
TRIALS_PATH = "data/derived/WP-015-funding-trials.parquet"
PREDICTIONS_PATH = "data/derived/WP-015-funding-predictions.parquet"
COMPARISON_PATH = "reports/research/WP-015-COMPARISON.json"
RECONCILIATION_PATH = "reports/validation/WP-015-MODEL-RECONCILIATION.json"
MANIFEST_PATH = "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json"
WALK_FORWARD_PATH = "research/protocols/WP-015-WALK-FORWARD-V1.json"
PROTOCOL_PATH = "research/protocols/WP-015-PERPETUAL-FUNDING-HGBR-V1.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matrix_hash(times: np.ndarray, matrix: np.ndarray, features: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(list(features), separators=(",", ":")).encode())
    digest.update(np.asarray(matrix.shape, dtype="<i8").tobytes())
    digest.update(np.asarray(times, dtype="<i8").tobytes())
    digest.update(np.asarray(matrix, dtype="<f8").tobytes(order="C"))
    return digest.hexdigest()


def target_hash(times: np.ndarray, target: np.ndarray, outcomes: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(LABEL_VERSION.encode())
    digest.update(np.asarray(times, dtype="<i8").tobytes())
    digest.update(np.asarray(target, dtype="<f8").tobytes())
    digest.update(np.asarray(outcomes, dtype="<i8").tobytes())
    return digest.hexdigest()


def independent_funding() -> tuple[list[int], list[float]]:
    manifest = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    times_ms: list[int] = []
    rates: list[float] = []
    for request in manifest["raw_requests"]:
        path = ROOT / request["path"]
        if sha256(path) != request["sha256"]:
            raise ValueError("independent raw funding hash mismatch")
        page = json.loads(path.read_text(encoding="utf-8"))
        if len(page) != request["row_count"]:
            raise ValueError("independent raw funding row count mismatch")
        for item in page:
            if item["symbol"] != "BTCUSDT" or int(item["fundingTime"]) > 1_735_689_599_999:
                raise ValueError("funding symbol or cutoff violation")
            times_ms.append(int(item["fundingTime"]))
            rates.append(float(Decimal(str(item["fundingRate"]))))
    if len(times_ms) != 5819 or any(b <= a for a, b in zip(times_ms, times_ms[1:], strict=False)):
        raise ValueError("independent funding chronology mismatch")
    canonical = pq.read_table(ROOT / manifest["canonical"]["path"])
    canonical_us = [int(value) for value in canonical["funding_time"].cast(pa.int64()).to_pylist()]
    canonical_rates = [float(value) for value in canonical["funding_rate"].to_pylist()]
    times_us = [value * 1000 for value in times_ms]
    if canonical_us != times_us or canonical_rates != rates:
        raise ValueError("independently rebuilt canonical funding differs")
    return times_us, rates


def main(
    trials_path: Path | None = None,
    predictions_path: Path | None = None,
    comparison_path: Path | None = None,
    output_path: Path | None = None,
) -> int:
    trials_path = trials_path or ROOT / TRIALS_PATH
    predictions_path = predictions_path or ROOT / PREDICTIONS_PATH
    comparison_path = comparison_path or ROOT / COMPARISON_PATH
    output_path = output_path or ROOT / RECONCILIATION_PATH
    if sklearn.__version__ != "1.7.2":
        raise ValueError("independent path requires scikit-learn 1.7.2")
    protocol = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    if protocol["hgbr_parameters"] != PARAMETERS:
        raise ValueError("frozen HGBR identity differs")
    folds = json.loads((ROOT / WALK_FORWARD_PATH).read_text(encoding="utf-8"))["folds"]
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    funding_times, funding_rates = independent_funding()
    inputs = ResearchInputs.load(ROOT)
    source = load_feature_source(ROOT)
    first_hour = ((funding_times[0] // HOUR_US) + 1) * HOUR_US
    last_signal = max(utc_us(fold["last_signal_inclusive"]) for fold in folds)
    rows: dict[int, Any] = {}
    funding: dict[int, tuple[int, float]] = {}
    for signal_us in range(first_hour, last_signal + 1, HOUR_US):
        index = bisect.bisect_left(funding_times, signal_us) - 1
        if index < 0 or funding_times[index] >= signal_us:
            continue
        try:
            row = source.at(signal_us)
        except SupervisedDataError:
            continue
        rows[signal_us] = row
        funding[signal_us] = (funding_times[index], funding_rates[index])
    labels = {signal: isolated_label(inputs, row) for signal, row in rows.items()}
    mismatches: list[dict[str, Any]] = []

    def mismatch(**item: Any) -> None:
        if len(mismatches) < 50:
            mismatches.append(item)

    expected_counts = {
        fold["fold_id"]: sum(
            utc_us(fold["validation_start"]) <= signal <= utc_us(fold["last_signal_inclusive"])
            for signal in rows
        )
        for fold in folds
    }
    recorded_counts = comparison["configurations"][PRIMARY]["prediction_diagnostics"]["per_fold"]
    universe_ok = all(
        expected_counts[fold] == recorded_counts[fold]["eligible_hours"] for fold in expected_counts
    ) and all(
        comparison["configurations"][PRIMARY]["prediction_diagnostics"]["per_fold"][fold][
            "eligible_hours"
        ]
        == comparison["configurations"][CONTROL]["prediction_diagnostics"]["per_fold"][fold][
            "eligible_hours"
        ]
        for fold in expected_counts
    )
    models: dict[str, dict[str, HistGradientBoostingRegressor]] = defaultdict(dict)
    training_ok = True
    for variant in VARIANTS:
        stored = json.loads(
            (ROOT / f"research/experiments/{EXPERIMENTS[variant]}/fold-models.json").read_text(
                encoding="utf-8"
            )
        )["fold_models"]
        features = (*FULL_FEATURES, FEATURE) if variant == PRIMARY else FULL_FEATURES
        for fold, saved in zip(folds, stored, strict=True):
            boundary = utc_us(fold["train_end_exclusive"])
            start = utc_us(fold["train_start"])
            train = [
                rows[signal]
                for signal in sorted(rows)
                if start <= signal < boundary
                and labels[signal].status == "VALID"
                and labels[signal].net_r is not None
                and labels[signal].outcome_us < boundary
            ]
            times = np.asarray([row.signal_us for row in train], dtype=np.int64)
            matrix = np.asarray(
                [
                    (*row.values, funding[row.signal_us][1]) if variant == PRIMARY else row.values
                    for row in train
                ],
                dtype=np.float64,
            )
            target = np.asarray([labels[row.signal_us].net_r for row in train], dtype=np.float64)
            outcomes = np.asarray(
                [labels[row.signal_us].outcome_us for row in train], dtype=np.int64
            )
            estimator = HistGradientBoostingRegressor(**PARAMETERS).fit(matrix, target)
            models[variant][fold["fold_id"]] = estimator
            manifest = saved["training_manifest"]
            expected = {
                "fit_rows": len(train),
                "training_signal_min_us": int(times.min()),
                "training_signal_max_us": int(times.max()),
                "max_training_label_outcome_us": int(outcomes.max()),
                "purge_boundary_exclusive_us": boundary,
                "validation_start_us": utc_us(fold["validation_start"]),
                "training_matrix_logical_sha256": matrix_hash(times, matrix, features),
                "training_label_logical_sha256": target_hash(times, target, outcomes),
            }
            serialized = hashlib.sha256(pickle.dumps(estimator, protocol=5)).hexdigest()
            if (
                any(manifest[key] != value for key, value in expected.items())
                or saved["model"]["serialization_sha256"] != serialized
            ):
                training_ok = False
                mismatch(variant=variant, fold=fold["fold_id"], field="training_or_model")
    predictions: dict[str, dict[int, float]] = defaultdict(dict)
    for variant in VARIANTS:
        for fold in folds:
            signals = [
                signal
                for signal in sorted(rows)
                if utc_us(fold["validation_start"])
                <= signal
                <= utc_us(fold["last_signal_inclusive"])
            ]
            matrix = np.asarray(
                [
                    (*rows[signal].values, funding[signal][1])
                    if variant == PRIMARY
                    else rows[signal].values
                    for signal in signals
                ],
                dtype=np.float64,
            )
            values = models[variant][fold["fold_id"]].predict(matrix)
            predictions[variant].update(zip(signals, map(float, values), strict=True))
    stored_predictions = pq.read_table(predictions_path).to_pylist()
    maximum_prediction_gap = 0.0
    for item in stored_predictions:
        value = predictions[item["variant"]].get(item["signal_us"])
        if value is None:
            mismatch(variant=item["variant"], signal=item["signal_us"], field="prediction_missing")
            continue
        gap = abs(value - item["predicted_default_net_r"])
        maximum_prediction_gap = max(maximum_prediction_gap, gap)
        if gap > TOLERANCE or funding[item["signal_us"]][0] != item["funding_time_us"]:
            mismatch(variant=item["variant"], signal=item["signal_us"], field="prediction")
    expected_prediction_rows = sum(expected_counts.values()) * 2
    prediction_ok = len(stored_predictions) == expected_prediction_rows and not any(
        item.get("field", "").startswith("prediction") for item in mismatches
    )
    stored_trials = pq.read_table(trials_path).to_pylist()
    stored_default = {
        (item["variant"], item["signal_us"]): item
        for item in stored_trials
        if item["profile"] == "DEFAULT"
    }
    execution_ok = True
    metric_ok = True
    for variant in VARIANTS:
        rebuilt: list[dict[str, Any]] = []
        for fold in folds:
            blocked_until = -1
            for signal in range(
                utc_us(fold["validation_start"]),
                utc_us(fold["last_signal_inclusive"]) + 1,
                HOUR_US,
            ):
                prediction = predictions[variant].get(signal)
                if prediction is None or prediction <= 0.0 or signal < blocked_until:
                    continue
                row = rows[signal]
                instant = EPOCH + timedelta(microseconds=signal)
                reference = Decimal(str(row.reference))
                intent = Intent(
                    f"{variant}:DEFAULT",
                    f"SHALLOW_INTERNAL_HGBR_V1:{variant}",
                    DATASET_ID,
                    DATASET_HASH,
                    instant,
                    "LONG",
                    "NEXT_1M_OPEN",
                    reference * Decimal("0.98"),
                    reference * Decimal("1.04"),
                    "FIXED_TARGET_OR_STOP_OR_24H",
                    1440,
                )
                record = simulate(intent, inputs.path(signal), costs("DEFAULT"))
                exit_us = utc_us(record.exit_timestamp) if record.exit_timestamp else None
                net_r = float(record.net_r) if record.net_r is not None else None
                gross_r = float(record.gross_r) if record.gross_r is not None else None
                rebuilt.append(
                    {
                        "signal_us": signal,
                        "status": record.data_quality_status,
                        "reason": str(record.exit_reason),
                        "net_r": net_r,
                        "gross_r": gross_r,
                        "exit_us": exit_us,
                    }
                )
                if record.data_quality_status == "VALID":
                    assert exit_us is not None
                    blocked_until = (
                        exit_us if record.exit_reason == ExitReason.EXPIRY else exit_us + MINUTE_US
                    )
                elif record.data_quality_status == "UNRESOLVED":
                    blocked_until = signal + 1440 * MINUTE_US
                else:
                    blocked_until = signal
        for item in rebuilt:
            saved = stored_default.get((variant, item["signal_us"]))
            if saved is None or any(saved[key] != item[key] for key in item if key != "signal_us"):
                execution_ok = False
                mismatch(variant=variant, signal=item["signal_us"], field="default_execution")
        if len(rebuilt) != sum(key[0] == variant for key in stored_default):
            execution_ok = False
        valid = [item for item in rebuilt if item["status"] == "VALID"]
        metrics = comparison["configurations"][variant]["profiles"]["DEFAULT"]["metrics"]
        mean = round(math.fsum(item["net_r"] for item in valid) / len(valid), 10)
        cumulative = round(math.fsum(item["net_r"] for item in valid), 10)
        if (
            metrics["trade_count"] != len(valid)
            or abs(metrics["net_expectancy_r"] - mean) > TOLERANCE
            or abs(metrics["cumulative_net_r"] - cumulative) > TOLERANCE
        ):
            metric_ok = False
            mismatch(variant=variant, field="default_metrics")
    checks = {
        "raw_funding_canonicalization": "PASS",
        "strict_prior_funding_asof": "PASS"
        if all(funding[signal][0] < signal for signal in funding)
        else "FAIL",
        "matched_eligible_universe": "PASS" if universe_ok else "FAIL",
        "annual_boundaries_outcome_containment_and_model_identity": "PASS"
        if training_ok
        else "FAIL",
        "all_fold_predictions_within_tolerance": "PASS" if prediction_ok else "FAIL",
        "default_spot_execution": "PASS" if execution_ok else "FAIL",
        "default_metrics": "PASS" if metric_ok else "FAIL",
    }
    output = {
        "schema_version": 1,
        "work_package": "WP-015",
        "status": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
        "independent_of_primary_runner": True,
        "prediction_tolerance": TOLERANCE,
        "maximum_prediction_absolute_difference": maximum_prediction_gap,
        "funding_records_rebuilt": len(funding_times),
        "eligible_hour_counts": expected_counts,
        "model_refits": 10,
        "checks": checks,
        "mismatches": mismatches,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(output, indent=2))
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials-path", type=Path)
    parser.add_argument("--predictions-path", type=Path)
    parser.add_argument("--comparison-path", type=Path)
    parser.add_argument("--output-path", type=Path)
    arguments = parser.parse_args()
    raise SystemExit(
        main(
            trials_path=arguments.trials_path,
            predictions_path=arguments.predictions_path,
            comparison_path=arguments.comparison_path,
            output_path=arguments.output_path,
        )
    )
