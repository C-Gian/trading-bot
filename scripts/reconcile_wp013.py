"""Independent WP-013 reconstruction; never imports the primary lab or runner."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from bisect import bisect_right
from collections import defaultdict
from datetime import UTC, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np
import pyarrow.parquet as pq
from app.backtest.engine import simulate
from app.backtest.models import ExitReason, Intent
from app.research.continuation_lab import DATASET_HASH, DATASET_ID, ResearchInputs, costs
from app.research.evaluation_protocol import EPOCH, HOUR_US, utc_us
from app.research.macro import verified_records
from app.research.supervised import (
    LABEL_VERSION,
    SupervisedDataError,
    SupervisedRow,
    isolated_label,
    load_feature_source,
)
from app.research.wp013 import (
    CONTROL_VARIANT,
    EXPERIMENTS,
    FEATURES,
    INTERACTION_FEATURES,
    PRIMARY_VARIANT,
    VARIANTS,
    load_protocol,
)

RECONCILIATION_PATH = "reports/validation/WP-013-MODEL-RECONCILIATION.json"
TRIALS_PATH = "data/derived/WP-013-context-interaction-trials.parquet"
COMPARISON_PATH = "reports/research/WP-013-COMPARISON.json"
DIAGNOSTICS_PATH = "reports/research/WP-013-INTERACTION-DIAGNOSTICS.json"
WALK_FORWARD_PATH = "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json"
HISTORY_START = "2017-08-17T04:00:00Z"
MINUTE_US = 60_000_000
TOLERANCE = 1e-9


def raw_nfci_timeline(root: Path) -> tuple[list[int], list[tuple[date, float]]]:
    events = []
    for record in verified_records(root):
        if record["series_id"] != "NFCI":
            continue
        observation = record["observation_date"]
        available = record["availability_time"]
        if observation > date(2024, 12, 31) or available.tzinfo is None:
            raise ValueError("invalid independent NFCI vintage")
        events.append((utc_us(available.astimezone(UTC)), observation, float(record["value"])))
    events.sort(key=lambda item: (item[0], item[1]))
    state: dict[date, float] = {}
    times: list[int] = []
    latest: list[tuple[date, float]] = []
    for index, (available, observation, value) in enumerate(events):
        state[observation] = value
        if index + 1 < len(events) and events[index + 1][0] == available:
            continue
        newest = max(state)
        times.append(available)
        latest.append((newest, state[newest]))
    if not times:
        raise ValueError("no independent NFCI timeline")
    return times, latest


def nfci_at(times: list[int], latest: list[tuple[date, float]], signal_us: int) -> float | None:
    position = bisect_right(times, signal_us) - 1
    return None if position < 0 else latest[position][1]


def matrix_values(base: tuple[float, ...], nfci: float, variant: str) -> tuple[float, ...]:
    if variant == CONTROL_VARIANT:
        return base
    if variant == PRIMARY_VARIANT:
        return base + tuple(value * nfci for value in base)
    raise ValueError("undeclared variant")


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


def independent_fit(matrix: np.ndarray, labels: np.ndarray, width: int) -> dict[str, Any]:
    count = len(labels)
    means = np.asarray([math.fsum(column) / count for column in matrix.T], dtype=np.float64)
    stds = np.asarray(
        [
            math.sqrt(math.fsum((value - mean) ** 2 for value in column) / count)
            for column, mean in zip(matrix.T, means, strict=True)
        ],
        dtype=np.float64,
    )
    if count <= width or np.any(stds <= 1e-12):
        raise ValueError("independent OLS infeasible")
    design = np.column_stack((np.ones(count), (matrix - means) / stds))
    solution, _, rank, singular = np.linalg.lstsq(design, labels, rcond=None)
    if int(rank) != width + 1:
        raise ValueError("independent OLS is not full rank")
    return {
        "means": means,
        "stds": stds,
        "intercept": float(solution[0]),
        "coefficients": np.asarray(solution[1:]),
        "rank": int(rank),
        "condition_number": float(singular[0] / singular[-1]),
    }


def gap(left: Any, right: Any) -> float:
    return float(
        np.max(np.abs(np.asarray(left, dtype=np.float64) - np.asarray(right, dtype=np.float64)))
    )


def execute_default(
    inputs: ResearchInputs, signal_us: int, reference: float, variant: str
) -> tuple[dict[str, Any], int]:
    instant = EPOCH + timedelta(microseconds=signal_us)
    ref = Decimal(str(reference))
    intent = Intent(
        f"{variant}:DEFAULT",
        f"CONTEXTUAL_NFCI_INTERACTION_OLS_V1:{variant}",
        DATASET_ID,
        DATASET_HASH,
        instant,
        "LONG",
        "NEXT_1M_OPEN",
        ref * Decimal("0.98"),
        ref * Decimal("1.04"),
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
        assert record.exit_timestamp is not None and record.net_r is not None
        assert record.gross_r is not None
        item.update(
            net_r=float(record.net_r),
            gross_r=float(record.gross_r),
            exit_us=utc_us(record.exit_timestamp),
        )
        blocked = (
            item["exit_us"]
            if record.exit_reason == ExitReason.EXPIRY
            else item["exit_us"] + MINUTE_US
        )
    elif record.data_quality_status == "UNRESOLVED":
        blocked = signal_us + 1440 * MINUTE_US
    else:
        blocked = signal_us
    return item, int(blocked)


def add(mismatches: list[dict[str, Any]], **values: Any) -> None:
    if len(mismatches) < 50:
        mismatches.append(values)


def main() -> int:
    load_protocol(ROOT)
    comparison = json.loads((ROOT / COMPARISON_PATH).read_text(encoding="utf-8"))
    diagnostics = json.loads((ROOT / DIAGNOSTICS_PATH).read_text(encoding="utf-8"))
    folds = json.loads((ROOT / WALK_FORWARD_PATH).read_text(encoding="utf-8"))["folds"]
    inputs = ResearchInputs.load(ROOT)
    internal = load_feature_source(ROOT)
    times, latest = raw_nfci_timeline(ROOT)
    last_signal = max(utc_us(fold["last_signal_inclusive"]) for fold in folds)

    rows: list[tuple[int, float, float, tuple[float, ...]]] = []
    for signal_us in range(utc_us(HISTORY_START), last_signal + 1, HOUR_US):
        try:
            internal_row = internal.at(signal_us)
        except SupervisedDataError:
            continue
        nfci = nfci_at(times, latest, signal_us)
        if nfci is not None:
            rows.append((signal_us, internal_row.reference, nfci, internal_row.values))
    by_signal = {row[0]: row for row in rows}
    print(f"independent matched universe: {len(rows)} rows", flush=True)

    labels = {}
    for signal_us, reference, _nfci, base in rows:
        proxy = SupervisedRow(signal_us, reference, 0, 0, signal_us, base)
        labels[signal_us] = isolated_label(inputs, proxy)
    print("independent isolated labels built", flush=True)

    checks: dict[str, str] = {}
    mismatches: list[dict[str, Any]] = []
    validation_counts = []
    for fold in folds:
        start, end = utc_us(fold["validation_start"]), utc_us(fold["last_signal_inclusive"])
        validation_counts.append(sum(start <= row[0] <= end for row in rows))
    recorded_counts = [
        diagnostics["configurations"][PRIMARY_VARIANT]["prediction"]["per_fold"][fold["fold_id"]][
            "eligible_hours"
        ]
        for fold in folds
    ]
    checks["raw_nfci_and_matched_eligible_universe"] = (
        "PASS" if validation_counts == recorded_counts else "FAIL"
    )

    models: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    max_scaling = max_coefficient = max_condition = 0.0
    fit_start = len(mismatches)
    for variant in VARIANTS:
        recorded = json.loads(
            (ROOT / f"research/experiments/{EXPERIMENTS[variant]}/fold-models.json").read_text()
        )["fold_models"]
        for fold, stored in zip(folds, recorded, strict=True):
            boundary = utc_us(fold["train_end_exclusive"])
            start = utc_us(fold["train_start"])
            train = [
                row
                for row in rows
                if start <= row[0] < boundary
                and labels[row[0]].status == "VALID"
                and labels[row[0]].net_r is not None
                and labels[row[0]].outcome_us < boundary
            ]
            signal_times = np.asarray([row[0] for row in train], dtype=np.int64)
            matrix = np.asarray(
                [matrix_values(row[3], row[2], variant) for row in train], dtype=np.float64
            )
            target = np.asarray([labels[row[0]].net_r for row in train], dtype=np.float64)
            outcomes = np.asarray([labels[row[0]].outcome_us for row in train], dtype=np.int64)
            rebuilt = independent_fit(matrix, target, len(FEATURES[variant]))
            models[variant][fold["fold_id"]] = rebuilt
            model, manifest = stored["model"], stored["training_manifest"]
            expected_manifest = {
                "fit_rows": len(train),
                "training_signal_min_us": int(signal_times.min()),
                "training_signal_max_us": int(signal_times.max()),
                "max_training_label_outcome_us": int(outcomes.max()),
                "purge_boundary_exclusive_us": boundary,
                "validation_start_us": utc_us(fold["validation_start"]),
                "training_matrix_logical_sha256": matrix_hash(
                    signal_times, matrix, FEATURES[variant]
                ),
                "training_label_logical_sha256": target_hash(signal_times, target, outcomes),
            }
            for field, expected in expected_manifest.items():
                if manifest[field] != expected:
                    add(mismatches, variant=variant, fold=fold["fold_id"], field=field)
            mean_gap, std_gap = (
                gap(rebuilt["means"], model["means"]),
                gap(rebuilt["stds"], model["stds_ddof_0"]),
            )
            coef_gap = max(
                gap(rebuilt["coefficients"], model["coefficients"]),
                abs(rebuilt["intercept"] - model["intercept"]),
            )
            condition_gap = abs(rebuilt["condition_number"] - model["condition_number"])
            max_scaling, max_coefficient, max_condition = (
                max(max_scaling, mean_gap, std_gap),
                max(max_coefficient, coef_gap),
                max(max_condition, condition_gap),
            )
            if (
                max(mean_gap, std_gap, coef_gap, condition_gap) > TOLERANCE
                or rebuilt["rank"] != model["rank"]
            ):
                add(mismatches, variant=variant, fold=fold["fold_id"], field="model_values")
    fit_clean = len(mismatches) == fit_start
    checks["raw_interactions_training_rows_and_purge"] = "PASS" if fit_clean else "FAIL"
    checks["training_only_scaling_rank_coefficients"] = "PASS" if fit_clean else "FAIL"
    print("independent model refits: 12", flush=True)

    predictions: dict[str, dict[int, float]] = defaultdict(dict)
    max_prediction = 0.0
    prediction_start = len(mismatches)
    for variant in VARIANTS:
        for fold in folds:
            start, end = utc_us(fold["validation_start"]), utc_us(fold["last_signal_inclusive"])
            model = models[variant][fold["fold_id"]]
            for signal_us in range(start - HOUR_US, end + 1, HOUR_US):
                if signal_us in predictions[variant] or signal_us not in by_signal:
                    continue
                row = by_signal[signal_us]
                vector = np.asarray(matrix_values(row[3], row[2], variant))
                predictions[variant][signal_us] = float(
                    model["intercept"]
                    + ((vector - model["means"]) / model["stds"]) @ model["coefficients"]
                )
    table = pq.read_table(ROOT / TRIALS_PATH).to_pylist()
    executed: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in table:
        executed[(row["variant"], row["profile"])].append(row)
        prediction = predictions[row["variant"]].get(row["prediction_signal_us"])
        if prediction is None:
            add(mismatches, variant=row["variant"], field="missing_prediction")
            continue
        value_gap = abs(prediction - row["predicted_default_net_r"])
        max_prediction = max(max_prediction, value_gap)
        if value_gap > TOLERANCE or row["nfci"] != by_signal[row["signal_us"]][2]:
            add(mismatches, variant=row["variant"], field="prediction_or_nfci")
    checks["oos_predictions"] = "PASS" if len(mismatches) == prediction_start else "FAIL"

    execution_start = len(mismatches)
    attempts = 0
    for variant in VARIANTS:
        rebuilt_trades = []
        for fold in folds:
            blocked = -1
            start, end = utc_us(fold["validation_start"]), utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start, end + 1, HOUR_US):
                context_row = by_signal.get(signal_us)
                prediction = predictions[variant].get(signal_us)
                if (
                    context_row is None
                    or prediction is None
                    or prediction <= 0.0
                    or signal_us < blocked
                ):
                    continue
                trade, blocked = execute_default(inputs, signal_us, context_row[1], variant)
                trade.update(
                    signal_us=signal_us, fold_id=fold["fold_id"], predicted_default_net_r=prediction
                )
                rebuilt_trades.append(trade)
        attempts += len(rebuilt_trades)
        recorded = sorted(executed[(variant, "DEFAULT")], key=lambda row: row["signal_us"])
        if [r["signal_us"] for r in rebuilt_trades] != [r["signal_us"] for r in recorded]:
            add(mismatches, variant=variant, field="default_signal_set")
            continue
        for rebuilt, stored in zip(rebuilt_trades, recorded, strict=True):
            for field in ("fold_id", "status", "reason", "exit_us"):
                if rebuilt[field] != stored[field]:
                    add(mismatches, variant=variant, signal_us=rebuilt["signal_us"], field=field)
            for field in ("predicted_default_net_r", "net_r", "gross_r"):
                left, right = rebuilt[field], stored[field]
                if (left is None) != (right is None) or (
                    left is not None and abs(left - right) > TOLERANCE
                ):
                    add(mismatches, variant=variant, signal_us=rebuilt["signal_us"], field=field)
        valid = [row["net_r"] for row in rebuilt_trades if row["status"] == "VALID"]
        metrics = comparison["configurations"][variant]["profiles"]["DEFAULT"]["metrics"]
        if (
            len(valid) != metrics["trade_count"]
            or abs(math.fsum(valid) / len(valid) - metrics["net_expectancy_r"]) > TOLERANCE
        ):
            add(mismatches, variant=variant, field="default_metrics")
    clean_execution = len(mismatches) == execution_start
    checks["default_signals_and_direct_execution"] = "PASS" if clean_execution else "FAIL"
    checks["default_metrics"] = "PASS" if clean_execution else "FAIL"

    report = {
        "schema_version": 1,
        "work_package": "WP-013",
        "reconciliation": "INDEPENDENT_CONTEXTUAL_NFCI_INTERACTION_OLS_V1",
        "independent_path": "RAW_VERIFIED_ALFRED_TIMELINE_LONGHAND_INTERACTIONS_OLS_PREDICTIONS_AND_DIRECT_DEFAULT_SIMULATION_NOT_PRIMARY_LAB_OR_RUNNER",
        "status": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
        "tolerance": TOLERANCE,
        "checks": checks,
        "independent_universe_rows": len(rows),
        "validation_eligible_counts": validation_counts,
        "independent_model_refits": 12,
        "independent_default_attempts": attempts,
        "maximum_scaling_gap": max_scaling,
        "maximum_coefficient_gap": max_coefficient,
        "maximum_condition_number_gap": max_condition,
        "maximum_prediction_gap": max_prediction,
        "executed_rows_examined": len(table),
        "interaction_features": list(INTERACTION_FEATURES),
        "mismatches": mismatches,
    }
    path = ROOT / RECONCILIATION_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({k: v for k, v in report.items() if k != "mismatches"}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
