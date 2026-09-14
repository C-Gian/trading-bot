"""Independent WP-017 reconstruction; never imports its primary lab or runner."""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import io
import json
import math
import pickle
import sys
import zipfile
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
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

PRIMARY = "INTERNAL_PLUS_CFTC_LEVERAGED_NET_HGBR"
CONTROL = "INTERNAL_HGBR_MATCHED_CFTC"
VARIANTS = (PRIMARY, CONTROL)
CFTC_FEATURE = "CFTC_LEVERAGED_FUNDS_NET_OI_SHARE_V1"
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
CUTOFF_US = int(datetime(2024, 12, 31, 23, 59, tzinfo=UTC).timestamp() * 1_000_000)
MARKET_NAME = "BITCOIN - CHICAGO MERCANTILE EXCHANGE"
MARKET_CODE = "133741"
CFTC_MANIFEST = "data/manifests/CFTC-CME-BITCOIN-TFF-DEV-v1.json"
PROTOCOL_PATH = "research/protocols/WP-017-CFTC-LEVERAGED-POSITIONING-V1.json"
WALK_PATH = "research/protocols/WP-015-WALK-FORWARD-V1.json"
RECONCILIATION_STRENGTH = "PARTIAL_INDEPENDENT_OF_WP017_LAB_AND_RUNNER"
SHARED_PRIMITIVES = (
    "app.research.supervised feature source and isolated label",
    "app.backtest.engine simulate and BTCUSDT_SPOT_COST_V1 cost model",
    "app.research.continuation_lab governed spot inputs",
)


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


def independent_cftc() -> tuple[list[int], list[date], list[float]]:
    """Re-parse the preserved official archives without the primary CFTC module."""
    manifest = json.loads((ROOT / CFTC_MANIFEST).read_text(encoding="utf-8"))
    if manifest["market"]["cftc_contract_market_code"] != MARKET_CODE:
        raise ValueError("CFTC market identity mismatch")
    reports: dict[date, tuple[int, int, int]] = {}
    for archive in manifest["raw_archives"]:
        path = ROOT / archive["path"]
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != archive["sha256"]:
            raise ValueError("raw CFTC annual archive hash mismatch")
        if len(payload) != archive["compressed_bytes"]:
            raise ValueError("raw CFTC annual archive size mismatch")
        with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
            names = bundle.namelist()
            if names != ["FinFutYY.txt"]:
                raise ValueError("unexpected CFTC archive members")
            with bundle.open(names[0]) as binary:
                reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig", newline=""))
                for row in reader:
                    if (row.get("CFTC_Contract_Market_Code") or "").strip() != MARKET_CODE:
                        continue
                    if (row.get("Market_and_Exchange_Names") or "").strip() != MARKET_NAME:
                        raise ValueError("CFTC contract code resolved to an unexpected market")
                    report = date.fromisoformat(row["Report_Date_as_YYYY-MM-DD"].strip())
                    if report in reports:
                        raise ValueError("duplicate CFTC market/report row")
                    open_interest = int(row["Open_Interest_All"].strip())
                    long_all = int(row["Lev_Money_Positions_Long_All"].strip())
                    short_all = int(row["Lev_Money_Positions_Short_All"].strip())
                    if open_interest <= 0 or long_all < 0 or short_all < 0:
                        raise ValueError("invalid CFTC required numeric field")
                    reports[report] = (open_interest, long_all, short_all)
    calendar_path = ROOT / manifest["publication_calendar"]["path"]
    if sha256(calendar_path) != manifest["publication_calendar"]["sha256"]:
        raise ValueError("CFTC publication calendar hash mismatch")
    calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
    available: list[int] = []
    report_dates: list[date] = []
    values: list[float] = []
    excluded_postcutoff = unresolved = 0
    for record in sorted(calendar["records"], key=lambda item: item["report_date"]):
        report = date.fromisoformat(record["report_date"])
        if report not in reports:
            raise ValueError("publication calendar does not match the raw rows")
        if record["status"] != "ELIGIBLE_FOR_CUTOFF_EVALUATION":
            unresolved += 1
            continue
        publication = date.fromisoformat(record["publication_date"])
        if publication < report:
            raise ValueError("publication predates the report date")
        expected = datetime.combine(publication + timedelta(days=1), time(), tzinfo=UTC)
        if datetime.fromisoformat(record["availability_timestamp"]) != expected:
            raise ValueError("availability timestamp violates the frozen rule")
        available_us = int(expected.timestamp() * 1_000_000)
        if available_us > CUTOFF_US:
            excluded_postcutoff += 1
            continue
        open_interest, long_all, short_all = reports[report]
        available.append(available_us)
        report_dates.append(report)
        values.append(float(Decimal(long_all - short_all) / Decimal(open_interest)))
    if len(reports) != len(calendar["records"]):
        raise ValueError("publication calendar does not exactly cover the raw rows")
    if any(b <= a for a, b in zip(available, available[1:], strict=False)):
        raise ValueError("CFTC availability timeline is not strictly increasing")
    counts = manifest["row_counts"]
    if (
        counts["raw_cftc_rows"] != len(reports)
        or counts["canonical_point_in_time_eligible_rows"] != len(available)
        or counts["excluded_availability_after_cutoff"] != excluded_postcutoff
        or counts["excluded_publication_date_unresolved"] != unresolved
    ):
        raise ValueError("CFTC row accounting does not reconcile")
    canonical = pq.read_table(ROOT / manifest["canonical"]["path"])
    if (
        canonical["availability_timestamp"].cast(pa.int64()).to_pylist() != available
        or canonical["report_date"].to_pylist() != report_dates
        or canonical["leveraged_funds_net_oi_share"].to_pylist() != values
    ):
        raise ValueError("CFTC canonical rebuild mismatch")
    return available, report_dates, values


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
    if protocol["primary_feature_order"] != [*FULL_FEATURES, CFTC_FEATURE]:
        raise ValueError("frozen primary feature order differs")
    if protocol["control_feature_order"] != list(FULL_FEATURES):
        raise ValueError("frozen control feature order differs")
    folds = json.loads((ROOT / WALK_PATH).read_text(encoding="utf-8"))["folds"]
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    saved_models = json.loads(models_path.read_text(encoding="utf-8"))["fold_models"]
    cftc_available, cftc_reports, cftc_values = independent_cftc()
    inputs, source = ResearchInputs.load(ROOT), load_feature_source(ROOT)
    start = ((cftc_available[0] // HOUR_US) + (1 if cftc_available[0] % HOUR_US else 0)) * HOUR_US
    last_signal = max(utc_us(fold["last_signal_inclusive"]) for fold in folds)
    rows: dict[int, Any] = {}
    contexts: dict[int, tuple[int, date, float]] = {}
    for signal in range(start, last_signal + 1, HOUR_US):
        index = bisect.bisect_right(cftc_available, signal) - 1
        if index < 0 or cftc_available[index] > signal:
            continue
        try:
            row = source.at(signal)
        except SupervisedDataError:
            continue
        rows[signal] = row
        contexts[signal] = (cftc_available[index], cftc_reports[index], cftc_values[index])
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
        features = (*FULL_FEATURES, CFTC_FEATURE) if variant == PRIMARY else FULL_FEATURES
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
                    (*row.values, contexts[row.signal_us][2]) if variant == PRIMARY else row.values
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
                    (*rows[signal].values, contexts[signal][2])
                    if variant == PRIMARY
                    else rows[signal].values
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
            or item["cftc_availability_us"] != context[0]
            or item["cftc_report_date"] != context[1]
            or abs(item["cftc_leveraged_net_oi_share"] - context[2]) > TOLERANCE
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
    primary_signals = {
        item["signal_us"] for item in stored_predictions if item["variant"] == PRIMARY
    }
    control_signals = {
        item["signal_us"] for item in stored_predictions if item["variant"] == CONTROL
    }
    checks = {
        "raw_cftc_canonicalization": "PASS",
        "publication_date_resolution_and_availability_rule": "PASS",
        "point_in_time_asof_never_after_signal": "PASS"
        if all(contexts[s][0] <= s for s in contexts)
        else "FAIL",
        "no_postcutoff_availability": "PASS"
        if all(contexts[s][0] <= CUTOFF_US for s in contexts)
        else "FAIL",
        "matched_eligible_universe": "PASS" if universe_ok else "FAIL",
        "identical_primary_and_control_timestamps": "PASS"
        if primary_signals == control_signals
        else "FAIL",
        "annual_boundaries_outcome_containment_and_model_identity": "PASS"
        if training_ok
        else "FAIL",
        "all_fold_predictions_within_tolerance": "PASS" if prediction_ok else "FAIL",
        "default_spot_execution": "PASS" if execution_ok else "FAIL",
        "default_metrics": "PASS" if metric_ok else "FAIL",
    }
    output = {
        "schema_version": 1,
        "work_package": "WP-017",
        "status": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
        "independent_of_primary_runner": True,
        "reconciliation_strength": RECONCILIATION_STRENGTH,
        "shared_primitives_not_independently_reimplemented": list(SHARED_PRIMITIVES),
        "prediction_tolerance": TOLERANCE,
        "maximum_prediction_absolute_difference": maximum_gap,
        "eligible_hour_counts": expected_counts,
        "cftc_eligible_rows": len(cftc_available),
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
