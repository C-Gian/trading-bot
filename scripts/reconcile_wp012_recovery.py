"""Recovery-grade independent reconciliation of the WP-012 walk-forward.

This path does not call ``RegimeExpertLab`` or the WP-012 runner. It reconstructs the
point-in-time NFCI gate from verified ALFRED records, rebuilds every training matrix and
OLS fit, regenerates OOS predictions and DEFAULT signals, and independently simulates
the DEFAULT trades. Any material mismatch fails.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
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
    FULL_FEATURES,
    LABEL_VERSION,
    SupervisedDataError,
    SupervisedRow,
    isolated_label,
    load_feature_source,
)
from app.research.wp012 import EXPERIMENTS, GLOBAL_KEY, PRIMARY_VARIANT, VARIANTS, load_protocol

RECONCILIATION_PATH = "reports/validation/WP-012-MODEL-RECONCILIATION.json"
TRIALS_PATH = "data/derived/WP-012-regime-trials.parquet"
COMPARISON_PATH = "reports/research/WP-012-COMPARISON.json"
DIAGNOSTICS_PATH = "reports/research/WP-012-REGIME-DIAGNOSTICS.json"
WALK_FORWARD_PATH = "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json"
PURGE_US = 216 * HOUR_US
MINUTE_US = 60_000_000
HISTORY_START = "2017-08-17T04:00:00Z"
REGIMES = ("NORMAL_OR_LOOSE", "TIGHT")
TOLERANCE = 1e-9


def regime_label(value: float) -> str:
    """Restate the frozen gate locally instead of reusing the production classifier."""
    return "TIGHT" if value > 0.0 else "NORMAL_OR_LOOSE"


def independent_regime_timeline(root: Path) -> tuple[list[int], list[tuple[date, float]]]:
    """Construct visible NFCI states directly from verified historical vintage records."""
    events = []
    for record in verified_records(root):
        if record["series_id"] != "NFCI":
            continue
        observation = record["observation_date"]
        if observation > date(2024, 12, 31):
            raise ValueError("independent path found post-2024 NFCI")
        available = record["availability_time"]
        if available.tzinfo is None:
            raise ValueError("independent path found naive NFCI availability")
        events.append((utc_us(available.astimezone(UTC)), observation, float(record["value"])))
    events.sort(key=lambda item: (item[0], item[1]))
    if not events:
        raise ValueError("independent path found no NFCI history")

    state: dict[date, float] = {}
    available_steps: list[int] = []
    latest_steps: list[tuple[date, float]] = []
    for index, (available_us, observation, value) in enumerate(events):
        state[observation] = value
        if index + 1 < len(events) and events[index + 1][0] == available_us:
            continue
        newest = max(state)
        available_steps.append(available_us)
        latest_steps.append((newest, state[newest]))
    return available_steps, latest_steps


def regime_at(
    available_steps: list[int], latest_steps: list[tuple[date, float]], signal_us: int
) -> str | None:
    position = bisect_right(available_steps, signal_us) - 1
    if position < 0:
        return None
    return regime_label(latest_steps[position][1])


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


def independent_fit(matrix: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    """OLS written out locally with population scaling and the frozen feasibility rule."""
    count = len(labels)
    if count <= len(FULL_FEATURES):
        raise ValueError("insufficient rows")
    means = np.array([float(math.fsum(column) / count) for column in matrix.T], dtype=np.float64)
    stds = np.array(
        [
            math.sqrt(math.fsum((x - mean) ** 2 for x in column) / count)
            for column, mean in zip(matrix.T, means, strict=True)
        ],
        dtype=np.float64,
    )
    if np.any(stds <= 1e-12):
        raise ValueError("standard deviation <= 1e-12")
    standardized = (matrix - means) / stds
    design = np.column_stack((np.ones(count, dtype=np.float64), standardized))
    solution, _, rank, singular = np.linalg.lstsq(design, labels, rcond=None)
    if int(rank) != len(FULL_FEATURES) + 1:
        raise ValueError("not full column rank")
    return {
        "means": means,
        "stds": stds,
        "intercept": float(solution[0]),
        "coefficients": np.asarray(solution[1:], dtype=np.float64),
        "rank": int(rank),
        "condition_number": float(singular[0] / singular[-1]),
    }


def maximum_gap(left: np.ndarray, right: Any) -> float:
    return float(np.max(np.abs(left - np.asarray(right, dtype=np.float64))))


def independent_default_trade(
    inputs: ResearchInputs,
    signal_us: int,
    reference: float,
    variant: str,
) -> tuple[dict[str, Any], int]:
    """Execute DEFAULT directly through the frozen engine without a WP-012 lab helper."""
    instant = EPOCH + timedelta(microseconds=signal_us)
    ref = Decimal(str(reference))
    intent = Intent(
        f"{variant}:DEFAULT",
        f"REGIME_CONDITIONED_LINEAR_EXPERTS_V1:{variant}",
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
    rebuilt: dict[str, Any] = {
        "status": record.data_quality_status,
        "reason": str(record.exit_reason),
        "net_r": None,
        "gross_r": None,
        "exit_us": None,
    }
    if record.data_quality_status == "VALID":
        assert record.exit_timestamp is not None
        assert record.net_r is not None and record.gross_r is not None
        rebuilt.update(
            net_r=float(record.net_r),
            gross_r=float(record.gross_r),
            exit_us=utc_us(record.exit_timestamp),
        )
        blocked_until = (
            rebuilt["exit_us"]
            if record.exit_reason == ExitReason.EXPIRY
            else rebuilt["exit_us"] + MINUTE_US
        )
    elif record.data_quality_status == "UNRESOLVED":
        blocked_until = signal_us + 1440 * MINUTE_US
    else:
        blocked_until = signal_us
    return rebuilt, int(blocked_until)


def add_mismatch(mismatches: list[dict[str, Any]], **fields: Any) -> None:
    if len(mismatches) < 50:
        mismatches.append(fields)


def main() -> int:
    load_protocol(ROOT)
    comparison = json.loads((ROOT / COMPARISON_PATH).read_text(encoding="utf-8"))
    diagnostics = json.loads((ROOT / DIAGNOSTICS_PATH).read_text(encoding="utf-8"))
    folds = json.loads((ROOT / WALK_FORWARD_PATH).read_text(encoding="utf-8"))["folds"]
    inputs = ResearchInputs.load(ROOT)
    internal = load_feature_source(ROOT)
    available_steps, latest_steps = independent_regime_timeline(ROOT)

    last_signal = max(utc_us(fold["last_signal_inclusive"]) for fold in folds)
    rows: list[tuple[int, float, str, tuple[float, ...]]] = []
    for signal_us in range(utc_us(HISTORY_START), last_signal + 1, HOUR_US):
        try:
            item = internal.at(signal_us)
        except SupervisedDataError:
            continue
        regime = regime_at(available_steps, latest_steps, signal_us)
        if regime is None:
            continue
        rows.append((signal_us, item.reference, regime, item.values))
    row_by_signal = {row[0]: row for row in rows}
    print(f"independent universe: {len(rows)} eligible rows", flush=True)

    labels: dict[int, Any] = {}
    for signal_us, reference, _regime, values in rows:
        proxy = SupervisedRow(signal_us, reference, 0, 0, signal_us, values)
        labels[signal_us] = isolated_label(inputs, proxy)
    print("independent labels built", flush=True)

    checks: dict[str, str] = {}
    mismatches: list[dict[str, Any]] = []
    gate_partition = Counter(
        regime
        for signal_us in range(utc_us(HISTORY_START), utc_us("2024-12-31T23:00:00Z") + 1, HOUR_US)
        if (regime := regime_at(available_steps, latest_steps, signal_us)) is not None
    )
    partition = Counter(row[2] for row in rows)
    checks["regime_assignment_and_partition"] = (
        "PASS"
        if gate_partition == Counter({"NORMAL_OR_LOOSE": 64152, "TIGHT": 336})
        and sum(partition.values()) == len(rows)
        and set(partition) == set(REGIMES)
        and partition["TIGHT"] == 336
        else "FAIL"
    )

    rebuilt_models: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    refits = 0
    maximum_scaling_gap = 0.0
    maximum_coefficient_gap = 0.0
    maximum_condition_gap = 0.0
    fit_mismatch_start = len(mismatches)
    for variant in VARIANTS:
        recorded = json.loads(
            (ROOT / f"research/experiments/{EXPERIMENTS[variant]}/fold-experts.json").read_text(
                encoding="utf-8"
            )
        )["fold_experts"]
        rebuilt_models[variant] = {}
        if [item["fold_id"] for item in recorded] != [fold["fold_id"] for fold in folds]:
            add_mismatch(mismatches, variant=variant, field="fold_order")
        for fold, item in zip(folds, recorded, strict=True):
            fold_id = fold["fold_id"]
            boundary = utc_us(fold["train_end_exclusive"])
            train_start = utc_us(fold["train_start"])
            eligible = [
                row
                for row in rows
                if train_start <= row[0] < boundary
                and labels[row[0]].status == "VALID"
                and labels[row[0]].net_r is not None
                and labels[row[0]].outcome_us < boundary
            ]
            groups = (
                {regime: [row for row in eligible if row[2] == regime] for regime in REGIMES}
                if variant == PRIMARY_VARIANT
                else {GLOBAL_KEY: eligible}
            )
            rebuilt_models[variant][fold_id] = {}
            for key, group in groups.items():
                recorded_model = item["experts"].get(key)
                times = np.asarray([row[0] for row in group], dtype=np.int64)
                matrix = np.asarray([row[3] for row in group], dtype=np.float64)
                target = np.asarray([labels[row[0]].net_r for row in group], dtype=np.float64)
                outcomes = np.asarray([labels[row[0]].outcome_us for row in group], dtype=np.int64)
                try:
                    rebuilt = independent_fit(matrix, target)
                except ValueError:
                    if recorded_model is not None or key not in item["infeasible_experts"]:
                        add_mismatch(
                            mismatches,
                            variant=variant,
                            fold=fold_id,
                            expert=key,
                            field="independent_infeasible_disagreement",
                        )
                    continue
                if recorded_model is None:
                    add_mismatch(
                        mismatches,
                        variant=variant,
                        fold=fold_id,
                        expert=key,
                        field="recorded_expert_missing",
                    )
                    continue
                refits += 1
                rebuilt_models[variant][fold_id][key] = rebuilt
                manifest = item["training_manifests"].get(key, {})
                expected_manifest = {
                    "fit_rows": len(group),
                    "training_signal_min_us": int(times.min()),
                    "training_signal_max_us": int(times.max()),
                    "max_training_label_outcome_us": int(outcomes.max()),
                    "purge_boundary_exclusive_us": boundary,
                    "validation_start_us": utc_us(fold["validation_start"]),
                    "training_matrix_logical_sha256": matrix_hash(times, matrix),
                    "training_label_logical_sha256": target_hash(times, target, outcomes),
                }
                for field, expected in expected_manifest.items():
                    if manifest.get(field) != expected:
                        add_mismatch(
                            mismatches,
                            variant=variant,
                            fold=fold_id,
                            expert=key,
                            field=field,
                            recorded=manifest.get(field),
                            rebuilt=expected,
                        )
                if tuple(recorded_model["feature_order"]) != FULL_FEATURES:
                    add_mismatch(
                        mismatches,
                        variant=variant,
                        fold=fold_id,
                        expert=key,
                        field="feature_order",
                    )
                if rebuilt["rank"] != recorded_model["rank"]:
                    add_mismatch(
                        mismatches, variant=variant, fold=fold_id, expert=key, field="rank"
                    )
                mean_gap = maximum_gap(rebuilt["means"], recorded_model["means"])
                std_gap = maximum_gap(rebuilt["stds"], recorded_model["stds_ddof_0"])
                coef_gap = maximum_gap(rebuilt["coefficients"], recorded_model["coefficients"])
                intercept_gap = abs(rebuilt["intercept"] - recorded_model["intercept"])
                condition_gap = abs(
                    rebuilt["condition_number"] - recorded_model["condition_number"]
                )
                maximum_scaling_gap = max(maximum_scaling_gap, mean_gap, std_gap)
                maximum_coefficient_gap = max(maximum_coefficient_gap, coef_gap, intercept_gap)
                maximum_condition_gap = max(maximum_condition_gap, condition_gap)
                if max(mean_gap, std_gap, coef_gap, intercept_gap, condition_gap) > TOLERANCE:
                    add_mismatch(
                        mismatches,
                        variant=variant,
                        fold=fold_id,
                        expert=key,
                        field="model_values",
                        mean_gap=mean_gap,
                        std_gap=std_gap,
                        coefficient_gap=coef_gap,
                        intercept_gap=intercept_gap,
                        condition_number_gap=condition_gap,
                    )
    fit_clean = len(mismatches) == fit_mismatch_start
    checks["training_rows_and_purge_containment"] = "PASS" if fit_clean else "FAIL"
    checks["per_expert_training_only_scaling"] = "PASS" if fit_clean else "FAIL"
    checks["coefficients_and_condition_numbers"] = "PASS" if fit_clean else "FAIL"
    print(f"independent refits: {refits}", flush=True)

    predictions: dict[str, dict[int, tuple[float, str, str]]] = {}
    prediction_counts: dict[str, Counter[str]] = {}
    maximum_prediction_gap = 0.0
    prediction_mismatch_start = len(mismatches)
    for variant in VARIANTS:
        predictions[variant] = {}
        prediction_counts[variant] = Counter()
        for fold in folds:
            fold_id = fold["fold_id"]
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start - HOUR_US, end + 1, HOUR_US):
                if signal_us in predictions[variant]:
                    continue
                row = row_by_signal.get(signal_us)
                if row is None:
                    continue
                key = row[2] if variant == PRIMARY_VARIANT else GLOBAL_KEY
                model = rebuilt_models[variant][fold_id].get(key)
                if model is None:
                    continue
                vector = np.asarray(row[3], dtype=np.float64)
                value = float(
                    model["intercept"]
                    + ((vector - model["means"]) / model["stds"]) @ model["coefficients"]
                )
                predictions[variant][signal_us] = (value, row[2], key)
                if start <= signal_us <= end:
                    prediction_counts[variant][row[2]] += int(value > 0.0)

    table = pq.read_table(ROOT / TRIALS_PATH).to_pylist()
    executed: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in table:
        executed[(row["variant"], row["profile"])].append(row)
        source = predictions[row["variant"]].get(row["prediction_signal_us"])
        if source is None:
            add_mismatch(
                mismatches,
                variant=row["variant"],
                profile=row["profile"],
                signal_us=row["signal_us"],
                field="stored_trade_without_rebuilt_prediction",
            )
            continue
        gap = abs(source[0] - row["predicted_default_net_r"])
        maximum_prediction_gap = max(maximum_prediction_gap, gap)
        if gap > TOLERANCE or source[2] != row["expert"]:
            add_mismatch(
                mismatches,
                variant=row["variant"],
                profile=row["profile"],
                signal_us=row["signal_us"],
                field="prediction_or_expert",
                prediction_gap=gap,
                rebuilt_expert=source[2],
                recorded_expert=row["expert"],
            )
        expected_regime_us = (
            row["prediction_signal_us"] if row["profile"] == "DELAY_1H" else row["signal_us"]
        )
        expected_regime = row_by_signal[expected_regime_us][2]
        if row["regime"] != expected_regime:
            add_mismatch(
                mismatches,
                variant=row["variant"],
                profile=row["profile"],
                signal_us=row["signal_us"],
                field="regime_decision",
                rebuilt=expected_regime,
                recorded=row["regime"],
            )
    for variant in VARIANTS:
        recorded_regimes = diagnostics["configurations"][variant]["per_regime"]
        for regime in REGIMES:
            if (
                prediction_counts[variant][regime]
                != recorded_regimes[regime]["prediction_positive_hours"]
            ):
                add_mismatch(
                    mismatches,
                    variant=variant,
                    regime=regime,
                    field="prediction_positive_hours",
                    rebuilt=prediction_counts[variant][regime],
                    recorded=recorded_regimes[regime]["prediction_positive_hours"],
                )
    prediction_clean = len(mismatches) == prediction_mismatch_start
    checks["oos_predictions_and_expert_selection"] = "PASS" if prediction_clean else "FAIL"

    execution_mismatch_start = len(mismatches)
    independently_executed = 0
    for variant in VARIANTS:
        rebuilt_trades: list[dict[str, Any]] = []
        for fold in folds:
            blocked_until = -1
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start, end + 1, HOUR_US):
                row = row_by_signal.get(signal_us)
                source = predictions[variant].get(signal_us)
                if row is None or source is None or source[0] <= 0.0 or signal_us < blocked_until:
                    continue
                trade, blocked_until = independent_default_trade(inputs, signal_us, row[1], variant)
                trade.update(
                    signal_us=signal_us,
                    fold_id=fold["fold_id"],
                    regime=row[2],
                    expert=source[2],
                    predicted_default_net_r=source[0],
                )
                rebuilt_trades.append(trade)
        independently_executed += len(rebuilt_trades)
        recorded_trades = sorted(executed[(variant, "DEFAULT")], key=lambda item: item["signal_us"])
        if [row["signal_us"] for row in rebuilt_trades] != [
            row["signal_us"] for row in recorded_trades
        ]:
            add_mismatch(mismatches, variant=variant, field="default_signal_set")
            continue
        for rebuilt, recorded in zip(rebuilt_trades, recorded_trades, strict=True):
            for field in ("fold_id", "regime", "expert", "status", "reason", "exit_us"):
                if rebuilt[field] != recorded[field]:
                    add_mismatch(
                        mismatches,
                        variant=variant,
                        signal_us=rebuilt["signal_us"],
                        field=field,
                        rebuilt=rebuilt[field],
                        recorded=recorded[field],
                    )
            for field in ("predicted_default_net_r", "net_r", "gross_r"):
                left, right = rebuilt[field], recorded[field]
                if (left is None) != (right is None) or (
                    left is not None and abs(float(left) - float(right)) > TOLERANCE
                ):
                    add_mismatch(
                        mismatches,
                        variant=variant,
                        signal_us=rebuilt["signal_us"],
                        field=field,
                        rebuilt=left,
                        recorded=right,
                    )
        valid = [row["net_r"] for row in rebuilt_trades if row["status"] == "VALID"]
        recorded_metrics = comparison["configurations"][variant]["profiles"]["DEFAULT"]["metrics"]
        rebuilt_metrics: dict[str, int | float | None] = {
            "trade_count": len(valid),
            "net_expectancy_r": float(math.fsum(valid) / len(valid)) if valid else None,
            "cumulative_net_r": float(math.fsum(valid)) if valid else None,
        }
        for field, summary_value in rebuilt_metrics.items():
            recorded_value = recorded_metrics[field]
            if (summary_value is None) != (recorded_value is None) or (
                summary_value is not None
                and abs(float(summary_value) - float(recorded_value)) > TOLERANCE
            ):
                add_mismatch(
                    mismatches,
                    variant=variant,
                    field=f"default_{field}",
                    rebuilt=summary_value,
                    recorded=recorded_value,
                )
    execution_clean = len(mismatches) == execution_mismatch_start
    checks["default_signals"] = "PASS" if execution_clean else "FAIL"
    checks["independent_default_execution_and_metrics"] = "PASS" if execution_clean else "FAIL"

    profile_mismatch_start = len(mismatches)
    for variant in VARIANTS:
        default_signals = {row["signal_us"] for row in executed[(variant, "DEFAULT")]}
        for profile in ("ZERO", "DOUBLE"):
            if {row["signal_us"] for row in executed[(variant, profile)]} != default_signals:
                add_mismatch(mismatches, variant=variant, field=f"{profile}_signal_reuse")
        for profile in ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"):
            for trial_row in executed[(variant, profile)]:
                if trial_row["signal_us"] % HOUR_US or trial_row["signal_us"] > utc_us(
                    "2024-12-31T23:00:00Z"
                ):
                    add_mismatch(
                        mismatches, variant=variant, profile=profile, field="signal_timestamp"
                    )
                expected_source = (
                    trial_row["signal_us"] - HOUR_US
                    if profile == "DELAY_1H"
                    else trial_row["signal_us"]
                )
                if trial_row["prediction_signal_us"] != expected_source:
                    add_mismatch(
                        mismatches,
                        variant=variant,
                        profile=profile,
                        field="prediction_timestamp",
                    )
    checks["profile_prediction_reuse_and_timestamps"] = (
        "PASS" if len(mismatches) == profile_mismatch_start else "FAIL"
    )

    report = {
        "schema_version": 1,
        "work_package": "WP-012",
        "reconciliation": "INDEPENDENT_REGIME_CONDITIONED_EXPERTS_V1",
        "independent_path": (
            "RAW_VERIFIED_ALFRED_TIMELINE_LONGHAND_OLS_REBUILT_PREDICTIONS_AND_DIRECT_"
            "DEFAULT_SIMULATION_NOT_THE_PRODUCTION_LAB_OR_RUNNER"
        ),
        "status": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
        "tolerance": TOLERANCE,
        "checks": checks,
        "independent_universe_rows": len(rows),
        "independent_gate_counts": dict(sorted(gate_partition.items())),
        "independent_regime_counts": dict(sorted(partition.items())),
        "independent_expert_refits": refits,
        "independent_default_attempts": independently_executed,
        "maximum_scaling_gap": maximum_scaling_gap,
        "maximum_coefficient_gap": maximum_coefficient_gap,
        "maximum_condition_number_gap": maximum_condition_gap,
        "maximum_prediction_gap": maximum_prediction_gap,
        "executed_rows_examined": len(table),
        "mismatches": mismatches,
        "cost_profile": costs("DEFAULT").profile,
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
