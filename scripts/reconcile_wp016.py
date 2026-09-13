"""Independent WP-016 reconstruction; never imports its primary lab or runner."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import pickle
import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
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

PRIMARY = "INTERNAL_FUNDING_PLUS_ATTENTION_HGBR"
CONTROL = "INTERNAL_PLUS_FUNDING_HGBR_MATCHED_ATTENTION"
VARIANTS = (PRIMARY, CONTROL)
FUNDING_FEATURE = "LATEST_SETTLED_FUNDING_RATE"
ATTENTION_FEATURE = "BITCOIN_WIKIPEDIA_ATTENTION_SHOCK_V1"
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
TOLERANCE = 1e-10
MINUTE_US = 60_000_000
FUNDING_MANIFEST = "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json"
ATTENTION_MANIFEST = "data/manifests/WIKIMEDIA-BITCOIN-PAGEVIEWS-DEV-v1.json"
PROTOCOL_PATH = "research/protocols/WP-016-WIKIPEDIA-ATTENTION-HGBR-V1.json"
WALK_PATH = "research/protocols/WP-015-WALK-FORWARD-V1.json"


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
    manifest = json.loads((ROOT / FUNDING_MANIFEST).read_text(encoding="utf-8"))
    times: list[int] = []
    rates: list[float] = []
    for request in manifest["raw_requests"]:
        path = ROOT / request["path"]
        if sha256(path) != request["sha256"]:
            raise ValueError("raw funding hash mismatch")
        for item in json.loads(path.read_text(encoding="utf-8")):
            timestamp = int(item["fundingTime"]) * 1000
            if item["symbol"] != "BTCUSDT" or timestamp > 1_735_689_599_999_000:
                raise ValueError("funding source identity or cutoff violation")
            times.append(timestamp)
            rates.append(float(Decimal(str(item["fundingRate"]))))
    if len(times) != len(set(times)) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("funding chronology violation")
    canonical = pq.read_table(ROOT / manifest["canonical"]["path"])
    if (
        times != canonical["funding_time"].cast(pa.int64()).to_pylist()
        or rates != canonical["funding_rate"].to_pylist()
    ):
        raise ValueError("funding canonical rebuild mismatch")
    return times, rates


def independent_attention() -> tuple[list[int], list[int], list[float]]:
    manifest = json.loads((ROOT / ATTENTION_MANIFEST).read_text(encoding="utf-8"))
    days: list[int] = []
    views: list[int] = []
    for request in manifest["raw_requests"]:
        path = ROOT / request["path"]
        if sha256(path) != request["sha256"]:
            raise ValueError("raw Wikimedia hash mismatch")
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload["items"]:
            if {
                key: item[key] for key in ("project", "article", "access", "agent", "granularity")
            } != {
                "project": "en.wikipedia",
                "article": "Bitcoin",
                "access": "all-access",
                "agent": "user",
                "granularity": "daily",
            }:
                raise ValueError("Wikimedia selector mismatch")
            observed = datetime.strptime(item["timestamp"], "%Y%m%d00").replace(tzinfo=UTC)
            if observed > datetime(2024, 12, 31, tzinfo=UTC):
                raise ValueError("post-cutoff attention observation")
            days.append(int(observed.timestamp() * 1_000_000))
            views.append(int(item["views"]))
    day_us = 86_400_000_000
    if len(days) != len(set(days)) or any(b - a != day_us for a, b in zip(days, days[1:])):
        raise ValueError("attention duplicate or missing day")
    available: list[int] = []
    shocks: list[float] = []
    observations: list[int] = []
    for index in range(28, len(days)):
        observations.append(days[index])
        available.append(days[index] + 2 * day_us)
        shocks.append(math.log((views[index] + 1) / (median(views[index - 28 : index]) + 1)))
    canonical = pq.read_table(ROOT / manifest["canonical"]["path"])
    if (
        days != canonical["observation_date"].cast(pa.int64()).to_pylist()
        or views != canonical["pageviews"].to_pylist()
    ):
        raise ValueError("attention canonical rebuild mismatch")
    return observations, available, shocks


def main(
    trials_path: Path,
    predictions_path: Path,
    comparison_path: Path,
    models_path: Path,
    output_path: Path,
) -> int:
    if sklearn.__version__ != "1.7.2":
        raise ValueError("independent path requires scikit-learn 1.7.2")
    protocol = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    if protocol["hgbr_parameters"] != PARAMETERS:
        raise ValueError("frozen HGBR parameters differ")
    folds = json.loads((ROOT / WALK_PATH).read_text(encoding="utf-8"))["folds"]
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    saved_models = json.loads(models_path.read_text(encoding="utf-8"))["fold_models"]
    funding_times, funding_rates = independent_funding()
    attention_observations, attention_available, attention_shocks = independent_attention()
    inputs, source = ResearchInputs.load(ROOT), load_feature_source(ROOT)
    start = max(((funding_times[0] // HOUR_US) + 1) * HOUR_US, attention_available[0])
    last_signal = max(utc_us(fold["last_signal_inclusive"]) for fold in folds)
    rows: dict[int, Any] = {}
    contexts: dict[int, tuple[int, float, int, int, float]] = {}
    for signal in range(start, last_signal + 1, HOUR_US):
        fi = bisect.bisect_left(funding_times, signal) - 1
        ai = bisect.bisect_right(attention_available, signal) - 1
        if fi < 0 or ai < 0 or funding_times[fi] >= signal or attention_available[ai] > signal:
            continue
        try:
            row = source.at(signal)
        except SupervisedDataError:
            continue
        rows[signal] = row
        contexts[signal] = (
            funding_times[fi],
            funding_rates[fi],
            attention_observations[ai],
            attention_available[ai],
            attention_shocks[ai],
        )
    labels = {signal: isolated_label(inputs, row) for signal, row in rows.items()}
    mismatches: list[dict[str, Any]] = []
    expected_counts = {
        fold["fold_id"]: sum(
            utc_us(fold["validation_start"]) <= signal <= utc_us(fold["last_signal_inclusive"])
            for signal in rows
        )
        for fold in folds
    }
    primary_counts = comparison["configurations"][PRIMARY]["prediction_diagnostics"]["per_fold"]
    control_counts = comparison["configurations"][CONTROL]["prediction_diagnostics"]["per_fold"]
    universe_ok = all(
        primary_counts[key]["eligible_hours"]
        == expected_counts[key]
        == control_counts[key]["eligible_hours"]
        for key in expected_counts
    )
    models: dict[str, dict[str, HistGradientBoostingRegressor]] = defaultdict(dict)
    training_ok = True
    for variant in VARIANTS:
        features = (
            (*FULL_FEATURES, FUNDING_FEATURE, ATTENTION_FEATURE)
            if variant == PRIMARY
            else (*FULL_FEATURES, FUNDING_FEATURE)
        )
        for fold, saved in zip(folds, saved_models[variant], strict=True):
            boundary, train_start = utc_us(fold["train_end_exclusive"]), utc_us(fold["train_start"])
            train = [
                rows[signal]
                for signal in sorted(rows)
                if train_start <= signal < boundary
                and labels[signal].status == "VALID"
                and labels[signal].net_r is not None
                and labels[signal].outcome_us < boundary
            ]
            times = np.asarray([row.signal_us for row in train], dtype=np.int64)
            matrix = np.asarray(
                [
                    (*row.values, contexts[row.signal_us][1], contexts[row.signal_us][4])
                    if variant == PRIMARY
                    else (*row.values, contexts[row.signal_us][1])
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
            manifest = saved["training_manifest"]
            if (
                any(manifest[key] != value for key, value in expected.items())
                or saved["model"]["serialization_sha256"]
                != hashlib.sha256(pickle.dumps(estimator, protocol=5)).hexdigest()
            ):
                training_ok = False
                mismatches.append(
                    {"variant": variant, "fold": fold["fold_id"], "field": "training_or_model"}
                )
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
                    (*rows[signal].values, contexts[signal][1], contexts[signal][4])
                    if variant == PRIMARY
                    else (*rows[signal].values, contexts[signal][1])
                    for signal in signals
                ],
                dtype=np.float64,
            )
            predictions[variant].update(
                zip(
                    signals,
                    map(float, models[variant][fold["fold_id"]].predict(matrix)),
                    strict=True,
                )
            )
    maximum_gap = 0.0
    stored_predictions = pq.read_table(predictions_path).to_pylist()
    prediction_ok = len(stored_predictions) == sum(expected_counts.values()) * 2
    for item in stored_predictions:
        actual = predictions[item["variant"]].get(item["signal_us"])
        if actual is None:
            prediction_ok = False
            continue
        gap = abs(actual - item["predicted_default_net_r"])
        maximum_gap = max(maximum_gap, gap)
        context = contexts[item["signal_us"]]
        if (
            gap > TOLERANCE
            or item["funding_time_us"] != context[0]
            or item["attention_observation_us"] != context[2]
            or item["attention_availability_us"] != context[3]
            or abs(item["attention_shock"] - context[4]) > TOLERANCE
        ):
            prediction_ok = False
    stored_default = {
        (item["variant"], item["signal_us"]): item
        for item in pq.read_table(trials_path).to_pylist()
        if item["profile"] == "DEFAULT"
    }
    execution_ok = metric_ok = True
    for variant in VARIANTS:
        rebuilt: list[dict[str, Any]] = []
        for fold in folds:
            blocked_until = -1
            for signal in range(
                utc_us(fold["validation_start"]), utc_us(fold["last_signal_inclusive"]) + 1, HOUR_US
            ):
                prediction = predictions[variant].get(signal)
                if prediction is None or prediction <= 0.0 or signal < blocked_until:
                    continue
                row = rows[signal]
                reference = Decimal(str(row.reference))
                intent = Intent(
                    f"{variant}:DEFAULT",
                    f"SHALLOW_INTERNAL_HGBR_V1:{variant}",
                    DATASET_ID,
                    DATASET_HASH,
                    EPOCH + timedelta(microseconds=signal),
                    "LONG",
                    "NEXT_1M_OPEN",
                    reference * Decimal("0.98"),
                    reference * Decimal("1.04"),
                    "FIXED_TARGET_OR_STOP_OR_24H",
                    1440,
                )
                record = simulate(intent, inputs.path(signal), costs("DEFAULT"))
                exit_us = utc_us(record.exit_timestamp) if record.exit_timestamp else None
                item = {
                    "signal_us": signal,
                    "status": record.data_quality_status,
                    "reason": str(record.exit_reason),
                    "net_r": float(record.net_r) if record.net_r is not None else None,
                    "gross_r": float(record.gross_r) if record.gross_r is not None else None,
                    "exit_us": exit_us,
                }
                rebuilt.append(item)
                saved = stored_default.get((variant, signal))
                if saved is None or any(
                    saved[key] != value for key, value in item.items() if key != "signal_us"
                ):
                    execution_ok = False
                if record.data_quality_status == "VALID":
                    assert exit_us is not None
                    blocked_until = (
                        exit_us if record.exit_reason == ExitReason.EXPIRY else exit_us + MINUTE_US
                    )
                elif record.data_quality_status == "UNRESOLVED":
                    blocked_until = signal + 1440 * MINUTE_US
                else:
                    blocked_until = signal
        valid = [item for item in rebuilt if item["status"] == "VALID"]
        metrics = comparison["configurations"][variant]["profiles"]["DEFAULT"]["metrics"]
        if (
            metrics["trade_count"] != len(valid)
            or abs(
                metrics["net_expectancy_r"]
                - round(math.fsum(item["net_r"] for item in valid) / len(valid), 10)
            )
            > TOLERANCE
            or abs(
                metrics["cumulative_net_r"] - round(math.fsum(item["net_r"] for item in valid), 10)
            )
            > TOLERANCE
        ):
            metric_ok = False
    checks = {
        "raw_funding_canonicalization": "PASS",
        "raw_attention_canonicalization": "PASS",
        "conservative_attention_asof": "PASS"
        if all(contexts[s][3] <= s for s in contexts)
        else "FAIL",
        "strict_prior_funding_asof": "PASS"
        if all(contexts[s][0] < s for s in contexts)
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
        "work_package": "WP-016",
        "status": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
        "independent_of_primary_runner": True,
        "prediction_tolerance": TOLERANCE,
        "maximum_prediction_absolute_difference": maximum_gap,
        "eligible_hour_counts": expected_counts,
        "model_refits": 10,
        "checks": checks,
        "mismatches": mismatches[:50],
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
    parser.add_argument("--trials-path", type=Path, required=True)
    parser.add_argument("--predictions-path", type=Path, required=True)
    parser.add_argument("--comparison-path", type=Path, required=True)
    parser.add_argument("--models-path", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(
        main(
            args.trials_path,
            args.predictions_path,
            args.comparison_path,
            args.models_path,
            args.output_path,
        )
    )
