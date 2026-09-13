"""Independent WP-014 reconstruction; never imports the primary lab or runner."""

from __future__ import annotations

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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np
import pyarrow.parquet as pq
import sklearn
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
from sklearn.ensemble import HistGradientBoostingRegressor

PRIMARY = "SHALLOW_INTERNAL_HGBR"
CONTROL = "INTERNAL_LINEAR_MATCHED"
VARIANTS = (PRIMARY, CONTROL)
EXPERIMENTS = {
    PRIMARY: "EXP-ML-022-SHALLOW-INTERNAL-HGBR",
    CONTROL: "EXP-ML-023-INTERNAL-LINEAR-MATCHED",
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
TOLERANCE = 1e-10
MINUTE_US = 60_000_000
HISTORY_START = "2017-08-17T04:00:00Z"
TRIALS_PATH = "data/derived/WP-014-shallow-internal-trials.parquet"
COMPARISON_PATH = "reports/research/WP-014-COMPARISON.json"
RECONCILIATION_PATH = "reports/validation/WP-014-MODEL-RECONCILIATION.json"
WALK_FORWARD_PATH = "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json"
PROTOCOL_PATH = "research/protocols/WP-014-SHALLOW-INTERNAL-HGBR-V1.json"


def matrix_hash(times: np.ndarray, matrix: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(list(FULL_FEATURES), separators=(",", ":")).encode())
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


def independent_ols(matrix: np.ndarray, target: np.ndarray) -> dict[str, Any]:
    count = len(target)
    means = np.asarray([math.fsum(column) / count for column in matrix.T], dtype=np.float64)
    stds = np.asarray(
        [
            math.sqrt(math.fsum((value - mean) ** 2 for value in column) / count)
            for column, mean in zip(matrix.T, means, strict=True)
        ],
        dtype=np.float64,
    )
    design = np.column_stack((np.ones(count), (matrix - means) / stds))
    solution, _, rank, singular = np.linalg.lstsq(design, target, rcond=None)
    if int(rank) != len(FULL_FEATURES) + 1:
        raise ValueError("independent OLS is not full rank")
    return {
        "kind": "OLS",
        "means": means,
        "stds": stds,
        "intercept": float(solution[0]),
        "coefficients": np.asarray(solution[1:], dtype=np.float64),
        "condition_number": float(singular[0] / singular[-1]),
    }


def independent_hgbr(matrix: np.ndarray, target: np.ndarray) -> dict[str, Any]:
    if sklearn.__version__ != "1.7.2":
        raise ValueError("independent path requires frozen scikit-learn 1.7.2")
    estimator = HistGradientBoostingRegressor(**PARAMETERS)
    estimator.fit(np.asarray(matrix, dtype=np.float64), np.asarray(target, dtype=np.float64))
    return {
        "kind": "HGBR",
        "estimator": estimator,
        "serialization_sha256": hashlib.sha256(pickle.dumps(estimator, protocol=5)).hexdigest(),
    }


def predict(model: dict[str, Any], matrix: np.ndarray) -> np.ndarray:
    values = np.asarray(matrix, dtype=np.float64)
    if model["kind"] == "HGBR":
        return np.asarray(model["estimator"].predict(values), dtype=np.float64)
    return np.asarray(
        model["intercept"] + ((values - model["means"]) / model["stds"]) @ model["coefficients"],
        dtype=np.float64,
    )


def execute_default(
    inputs: ResearchInputs, signal_us: int, reference: float, variant: str
) -> tuple[dict[str, Any], int]:
    instant = EPOCH + timedelta(microseconds=signal_us)
    value = Decimal(str(reference))
    intent = Intent(
        f"{variant}:DEFAULT",
        f"SHALLOW_INTERNAL_HGBR_V1:{variant}",
        DATASET_ID,
        DATASET_HASH,
        instant,
        "LONG",
        "NEXT_1M_OPEN",
        value * Decimal("0.98"),
        value * Decimal("1.04"),
        "FIXED_TARGET_OR_STOP_OR_24H",
        1440,
    )
    record = simulate(intent, inputs.path(signal_us), costs("DEFAULT"))
    item: dict[str, Any] = {
        "status": record.data_quality_status,
        "reason": str(record.exit_reason),
        "net_r": None,
        "gross_r": None,
        "exit_us": None,
    }
    if record.data_quality_status == "VALID":
        assert record.exit_timestamp is not None
        assert record.net_r is not None and record.gross_r is not None
        exit_us = utc_us(record.exit_timestamp)
        item.update(net_r=float(record.net_r), gross_r=float(record.gross_r), exit_us=exit_us)
        blocked = exit_us if record.exit_reason == ExitReason.EXPIRY else exit_us + MINUTE_US
    elif record.data_quality_status == "UNRESOLVED":
        blocked = signal_us + 1440 * MINUTE_US
    else:
        blocked = signal_us
    return item, int(blocked)


def add(mismatches: list[dict[str, Any]], **values: Any) -> None:
    if len(mismatches) < 50:
        mismatches.append(values)


def main() -> int:
    protocol = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    if protocol["models"][PRIMARY]["parameters"] != PARAMETERS:
        raise ValueError("independent frozen HGBR identity differs from protocol")
    comparison = json.loads((ROOT / COMPARISON_PATH).read_text(encoding="utf-8"))
    folds = json.loads((ROOT / WALK_FORWARD_PATH).read_text(encoding="utf-8"))["folds"]
    inputs = ResearchInputs.load(ROOT)
    source = load_feature_source(ROOT)
    last_signal = max(utc_us(fold["last_signal_inclusive"]) for fold in folds)
    rows = []
    for signal_us in range(utc_us(HISTORY_START), last_signal + 1, HOUR_US):
        try:
            row = source.at(signal_us)
        except SupervisedDataError:
            continue
        rows.append(row)
    by_signal = {row.signal_us: row for row in rows}
    labels = {row.signal_us: isolated_label(inputs, row) for row in rows}
    print(f"independent internal universe: {len(rows)} rows", flush=True)

    checks: dict[str, str] = {}
    mismatches: list[dict[str, Any]] = []
    validation_counts = [
        sum(
            utc_us(fold["validation_start"])
            <= row.signal_us
            <= utc_us(fold["last_signal_inclusive"])
            for row in rows
        )
        for fold in folds
    ]
    recorded_counts = [
        comparison["configurations"][PRIMARY]["prediction_diagnostics"]["per_fold"][
            fold["fold_id"]
        ]["eligible_hours"]
        for fold in folds
    ]
    checks["eligible_f1_f8_universe"] = "PASS" if validation_counts == recorded_counts else "FAIL"

    models: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    max_model_gap = 0.0
    training_start = len(mismatches)
    for variant in VARIANTS:
        stored_folds = json.loads(
            (ROOT / f"research/experiments/{EXPERIMENTS[variant]}/fold-models.json").read_text(
                encoding="utf-8"
            )
        )["fold_models"]
        for fold, stored in zip(folds, stored_folds, strict=True):
            start = utc_us(fold["train_start"])
            boundary = utc_us(fold["train_end_exclusive"])
            if utc_us(fold["validation_start"]) - boundary != 216 * HOUR_US:
                add(mismatches, variant=variant, fold=fold["fold_id"], field="purge")
            train = [
                row
                for row in rows
                if start <= row.signal_us < boundary
                and labels[row.signal_us].status == "VALID"
                and labels[row.signal_us].net_r is not None
                and labels[row.signal_us].outcome_us < boundary
            ]
            times = np.asarray([row.signal_us for row in train], dtype=np.int64)
            matrix = np.asarray([row.values for row in train], dtype=np.float64)
            target = np.asarray([labels[row.signal_us].net_r for row in train], dtype=np.float64)
            outcomes = np.asarray(
                [labels[row.signal_us].outcome_us for row in train], dtype=np.int64
            )
            model = (
                independent_hgbr(matrix, target)
                if variant == PRIMARY
                else independent_ols(matrix, target)
            )
            models[variant][fold["fold_id"]] = model
            manifest = stored["training_manifest"]
            expected = {
                "fit_rows": len(train),
                "training_signal_min_us": int(times.min()),
                "training_signal_max_us": int(times.max()),
                "max_training_label_outcome_us": int(outcomes.max()),
                "purge_boundary_exclusive_us": boundary,
                "validation_start_us": utc_us(fold["validation_start"]),
                "training_matrix_logical_sha256": matrix_hash(times, matrix),
                "training_label_logical_sha256": target_hash(times, target, outcomes),
            }
            for field, value in expected.items():
                if manifest[field] != value:
                    add(mismatches, variant=variant, fold=fold["fold_id"], field=field)
            recorded_model = stored["model"]
            if variant == PRIMARY:
                if (
                    recorded_model["parameters"] != PARAMETERS
                    or recorded_model["sklearn_version"] != "1.7.2"
                    or recorded_model["serialization_sha256"] != model["serialization_sha256"]
                ):
                    add(
                        mismatches,
                        variant=variant,
                        fold=fold["fold_id"],
                        field="hgbr_identity",
                    )
            else:
                gaps = [
                    float(
                        np.max(
                            np.abs(
                                np.asarray(model[left], dtype=np.float64)
                                - np.asarray(recorded_model[right], dtype=np.float64)
                            )
                        )
                    )
                    for left, right in (
                        ("means", "means"),
                        ("stds", "stds_ddof_0"),
                        ("coefficients", "coefficients"),
                    )
                ]
                gaps.append(abs(model["intercept"] - recorded_model["intercept"]))
                max_model_gap = max(max_model_gap, *gaps)
                if max(gaps) > TOLERANCE:
                    add(
                        mismatches,
                        variant=variant,
                        fold=fold["fold_id"],
                        field="ols_values",
                    )
    training_clean = len(mismatches) == training_start
    checks["training_boundaries_complete_outcomes_and_hashes"] = (
        "PASS" if training_clean else "FAIL"
    )
    checks["frozen_hgbr_identity_and_matched_ols"] = "PASS" if training_clean else "FAIL"
    print("independent model refits: 12", flush=True)

    predictions: dict[str, dict[int, float]] = defaultdict(dict)
    for variant in VARIANTS:
        for fold in folds:
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            model = models[variant][fold["fold_id"]]
            for signal_us in range(start - HOUR_US, end + 1, HOUR_US):
                if signal_us in predictions[variant] or signal_us not in by_signal:
                    continue
                matrix = np.asarray([by_signal[signal_us].values], dtype=np.float64)
                predictions[variant][signal_us] = float(predict(model, matrix)[0])

    table = pq.read_table(ROOT / TRIALS_PATH).to_pylist()
    executed: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    maximum_prediction_gap = 0.0
    prediction_start = len(mismatches)
    for row in table:
        executed[(row["variant"], row["profile"])].append(row)
        value = predictions[row["variant"]].get(row["prediction_signal_us"])
        if value is None:
            add(mismatches, variant=row["variant"], field="missing_prediction")
            continue
        difference = abs(value - row["predicted_default_net_r"])
        maximum_prediction_gap = max(maximum_prediction_gap, difference)
        if difference > TOLERANCE:
            add(
                mismatches,
                variant=row["variant"],
                signal_us=row["signal_us"],
                field="prediction",
            )
    checks["fold_predictions_and_profile_reuse"] = (
        "PASS" if len(mismatches) == prediction_start else "FAIL"
    )

    execution_start = len(mismatches)
    attempts = 0
    for variant in VARIANTS:
        rebuilt = []
        for fold in folds:
            blocked = -1
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start, end + 1, HOUR_US):
                row = by_signal.get(signal_us)
                prediction = predictions[variant].get(signal_us)
                if row is None or prediction is None or prediction <= 0.0 or signal_us < blocked:
                    continue
                trade, blocked = execute_default(inputs, signal_us, row.reference, variant)
                trade.update(
                    signal_us=signal_us,
                    fold_id=fold["fold_id"],
                    predicted_default_net_r=prediction,
                )
                rebuilt.append(trade)
        attempts += len(rebuilt)
        recorded = sorted(executed[(variant, "DEFAULT")], key=lambda row: row["signal_us"])
        if [row["signal_us"] for row in rebuilt] != [row["signal_us"] for row in recorded]:
            add(mismatches, variant=variant, field="default_signal_set")
            continue
        for left, right in zip(rebuilt, recorded, strict=True):
            for field in ("fold_id", "status", "reason", "exit_us"):
                if left[field] != right[field]:
                    add(mismatches, variant=variant, signal_us=left["signal_us"], field=field)
            for field in ("predicted_default_net_r", "net_r", "gross_r"):
                first, second = left[field], right[field]
                if (first is None) != (second is None) or (
                    first is not None and abs(first - second) > TOLERANCE
                ):
                    add(mismatches, variant=variant, signal_us=left["signal_us"], field=field)
        valid = [row["net_r"] for row in rebuilt if row["status"] == "VALID"]
        metrics = comparison["configurations"][variant]["profiles"]["DEFAULT"]["metrics"]
        if (
            len(valid) != metrics["trade_count"]
            or abs(math.fsum(valid) / len(valid) - metrics["net_expectancy_r"]) > TOLERANCE
        ):
            add(mismatches, variant=variant, field="default_metrics")
    execution_clean = len(mismatches) == execution_start
    checks["default_signal_timestamps_and_direct_execution"] = "PASS" if execution_clean else "FAIL"
    checks["default_metrics"] = "PASS" if execution_clean else "FAIL"

    report = {
        "schema_version": 1,
        "work_package": "WP-014",
        "reconciliation": "INDEPENDENT_SHALLOW_INTERNAL_HGBR_V1",
        "independent_path": (
            "COMMON_FROZEN_F1_F8_AND_LABEL_SUBSTRATE_THEN_SEPARATE_SKLEARN_HGBR_MANUAL_OLS_"
            "PREDICTIONS_AND_DIRECT_DEFAULT_SIMULATION_NOT_PRIMARY_WP014_LAB_OR_RUNNER"
        ),
        "status": "PASS" if checks and set(checks.values()) == {"PASS"} else "FAIL",
        "prediction_tolerance": TOLERANCE,
        "checks": checks,
        "independent_universe_rows": len(rows),
        "validation_eligible_counts": validation_counts,
        "independent_model_refits": 12,
        "independent_default_attempts": attempts,
        "maximum_ols_parameter_gap": max_model_gap,
        "maximum_prediction_gap": maximum_prediction_gap,
        "executed_rows_examined": len(table),
        "mismatches": mismatches,
    }
    path = ROOT / RECONCILIATION_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps({key: value for key, value in report.items() if key != "mismatches"}, indent=2)
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
