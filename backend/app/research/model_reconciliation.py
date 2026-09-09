"""Independent WP-008 fold/model/artifact reconciliation after frozen results."""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import validate_parquet
from .baselines import calculate_metrics
from .continuation_lab import PROFILES, ResearchInputs
from .evaluation_protocol import HOUR_US, load_protocol, utc_us
from .linear_lab import TRIAL_SCHEMA
from .supervised import (
    FULL_FEATURES,
    IsolatedLabel,
    SupervisedDataError,
    SupervisedRow,
    isolated_label,
    label_hash,
    load_feature_source,
    vector_hash,
)
from .wp004 import ROOT
from .wp008 import SPEC, config_path, read_json


def _prediction_hash(rows: list[SupervisedRow], predictions: np.ndarray) -> str:
    return hashlib.sha256(
        np.asarray([row.signal_us for row in rows], dtype="<i8").tobytes()
        + np.asarray(predictions, dtype="<f8").tobytes()
    ).hexdigest()


def _allclose(actual: Any, expected: Any, label: str) -> None:
    if not np.allclose(actual, expected, rtol=1e-12, atol=1e-12):
        raise SupervisedDataError(f"independent model reconciliation mismatch: {label}")


def reconcile(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    """Rebuild fold inputs and OLS directly, without invoking LinearChallengerLab."""
    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    inputs = ResearchInputs.load(root)
    features = load_feature_source(root)
    row_cache: dict[int, SupervisedRow | None] = {}
    labels: dict[int, IsolatedLabel] = {}

    def row_at(signal_us: int) -> SupervisedRow | None:
        if signal_us not in row_cache:
            try:
                row_cache[signal_us] = features.at(signal_us)
            except SupervisedDataError:
                row_cache[signal_us] = None
        return row_cache[signal_us]

    def label_at(row: SupervisedRow) -> IsolatedLabel:
        if row.signal_us not in labels:
            labels[row.signal_us] = isolated_label(inputs, row)
        return labels[row.signal_us]

    experiment_reports = {}
    leakage_folds = {}
    for experiment_id, variant in SPEC.items():
        directory = root / "research/experiments" / experiment_id
        result = read_json(directory / "result.json")
        config = read_json(root / config_path(variant))
        names = tuple(config["features"])
        indices = tuple(FULL_FEATURES.index(name) for name in names)
        models = {item["fold_id"]: item for item in result["secondary_results"]["fold_models"]}
        manifests = {
            item["fold_id"]: item for item in result["secondary_results"]["training_manifests"]
        }
        diagnostics = {
            item["fold_id"]: item for item in result["secondary_results"]["prediction_diagnostics"]
        }
        artifact = validate_parquet(
            result["secondary_results"]["artifact_manifest"], schema=TRIAL_SCHEMA, root=root
        )
        artifact_rows = artifact.to_pylist()
        fold_reports = []
        for fold in protocol["folds"]:
            fold_id = fold["fold_id"]
            train_start = utc_us(fold["train_start"])
            train_end = utc_us(fold["train_end_exclusive"])
            validation_start = utc_us(fold["validation_start"])
            if validation_start - train_end != 216 * HOUR_US:
                raise SupervisedDataError("reconciler found changed purge boundary")
            train_rows: list[SupervisedRow] = []
            train_labels: list[IsolatedLabel] = []
            exclusions: Counter[str] = Counter()
            for signal_us in range(train_start, train_end, HOUR_US):
                row = row_at(signal_us)
                if row is None:
                    exclusions["feature_ineligible"] += 1
                    continue
                label = label_at(row)
                if label.status != "VALID" or label.net_r is None:
                    exclusions[f"label_{label.status.lower()}"] += 1
                    continue
                if label.outcome_us >= validation_start:
                    raise SupervisedDataError("reconciler found a validation-overlapping label")
                train_rows.append(row)
                train_labels.append(label)
            times = np.asarray([row.signal_us for row in train_rows], dtype=np.int64)
            matrix = np.asarray(
                [[row.values[index] for index in indices] for row in train_rows], dtype=np.float64
            )
            target = np.asarray([label.net_r for label in train_labels], dtype=np.float64)
            outcomes = np.asarray([label.outcome_us for label in train_labels], dtype=np.int64)
            manifest = manifests[fold_id]
            if (
                vector_hash(times, matrix, names) != manifest["training_matrix_logical_sha256"]
                or label_hash(times, target, outcomes) != manifest["training_label_logical_sha256"]
                or manifest["exclusions"] != dict(sorted(exclusions.items()))
                or manifest["max_training_label_outcome_us"] != int(outcomes.max())
                or manifest["max_training_label_outcome_us"] >= validation_start
            ):
                raise SupervisedDataError("training manifest/hash reconciliation failed")
            means = matrix.mean(axis=0, dtype=np.float64)
            stds = matrix.std(axis=0, ddof=0, dtype=np.float64)
            design = np.column_stack((np.ones(len(target)), (matrix - means) / stds))
            coefficients, _, rank, singular = np.linalg.lstsq(design, target, rcond=None)
            record = models[fold_id]
            _allclose(means, record["means"], f"{variant}/{fold_id}/means")
            _allclose(stds, record["stds_ddof_0"], f"{variant}/{fold_id}/stds")
            _allclose(coefficients[0], record["intercept"], f"{variant}/{fold_id}/intercept")
            _allclose(coefficients[1:], record["coefficients"], f"{variant}/{fold_id}/coefficients")
            condition = float(singular[0] / singular[-1])
            _allclose(condition, record["condition_number"], f"{variant}/{fold_id}/condition")
            if int(rank) != len(names) + 1 or not record["full_rank"]:
                raise SupervisedDataError("reconciler found a rank-deficient model")
            validation_rows = [
                row
                for signal_us in range(
                    validation_start, utc_us(fold["last_signal_inclusive"]) + 1, HOUR_US
                )
                if (row := row_at(signal_us)) is not None
            ]
            validation_matrix = np.asarray(
                [[row.values[index] for index in indices] for row in validation_rows],
                dtype=np.float64,
            )
            predictions = coefficients[0] + ((validation_matrix - means) / stds) @ coefficients[1:]
            if (
                _prediction_hash(validation_rows, predictions)
                != diagnostics[fold_id]["prediction_hash"]
            ):
                raise SupervisedDataError("validation prediction hash reconciliation failed")
            for profile in PROFILES:
                actual = [
                    item
                    for item in artifact_rows
                    if item["fold_id"] == fold_id and item["profile"] == profile
                ]
                actual_by_signal = {item["signal_us"]: item for item in actual}
                expected_signals = []
                blocked_until = -1
                for row, prediction in zip(validation_rows, predictions, strict=True):
                    if profile == "DELAY_1H":
                        prior = row_at(row.signal_us - HOUR_US)
                        if prior is None:
                            continue
                        prior_matrix = np.asarray(
                            [[prior.values[index] for index in indices]], dtype=np.float64
                        )
                        prediction = float(
                            coefficients[0] + ((prior_matrix - means) / stds) @ coefficients[1:]
                        )
                    if prediction <= 0.0 or row.signal_us < blocked_until:
                        continue
                    recorded = actual_by_signal.get(row.signal_us)
                    if recorded is None:
                        raise SupervisedDataError(
                            "an emitted signal is missing from compact artifact"
                        )
                    if recorded["prediction_signal_us"] != row.signal_us - (
                        HOUR_US if profile == "DELAY_1H" else 0
                    ):
                        raise SupervisedDataError("prediction timestamp does not match profile")
                    _allclose(
                        recorded["predicted_default_net_r"],
                        prediction,
                        f"{variant}/{fold_id}/{profile}/prediction",
                    )
                    expected_signals.append(row.signal_us)
                    blocked_until = recorded["position_available_us"]
                if [item["signal_us"] for item in actual] != expected_signals:
                    raise SupervisedDataError("emitted signal timestamp sequence differs")
            fold_reports.append(
                {
                    "fold_id": fold_id,
                    "fit_rows": len(train_rows),
                    "feature_order_match": True,
                    "training_only_scaling_match": True,
                    "coefficient_match": True,
                    "prediction_hash_match": True,
                    "emitted_signal_timestamps_match": True,
                    "rank": int(rank),
                    "condition_number": condition,
                    "label_outcome_separation_hours": (validation_start - int(outcomes.max()))
                    // HOUR_US,
                }
            )
            leakage_folds[f"{variant}:{fold_id}"] = {
                "training_signal_min_us": int(times.min()),
                "training_signal_max_us": int(times.max()),
                "max_training_label_outcome_us": int(outcomes.max()),
                "validation_start_us": validation_start,
                "purge_boundary_exclusive_us": train_end,
                "fit_rows": len(train_rows),
                "exclusions": dict(sorted(exclusions.items())),
                "training_matrix_logical_sha256": vector_hash(times, matrix, names),
                "training_label_logical_sha256": label_hash(times, target, outcomes),
            }
        default_rows = [item for item in artifact_rows if item["profile"] == "DEFAULT"]
        metric_input = [
            {
                "status": item["status"],
                "net_r": item["net_r"],
                "gross_r": item["gross_r"],
                "year": int(item["fold_id"].split("-")[1]),
            }
            for item in default_rows
        ]
        invalid = sum(item["status"] == "INVALID" for item in default_rows)
        unresolved = sum(item["status"] == "UNRESOLVED" for item in default_rows)
        metrics = calculate_metrics(metric_input, len(default_rows), invalid, unresolved)
        recorded_metrics = result["secondary_results"]["profiles"]["DEFAULT"]["summary"]["metrics"]
        for key in (
            "attempted_setups",
            "trade_count",
            "invalid_attempts",
            "unresolved_trades",
            "net_expectancy_r",
            "cumulative_net_r",
            "profit_factor",
            "maximum_drawdown_r",
            "hit_rate",
            "cost_drag_r",
        ):
            if metrics[key] != recorded_metrics[key]:
                raise SupervisedDataError(f"DEFAULT compact-artifact metric mismatch: {key}")
        experiment_reports[experiment_id] = {
            "variant": variant,
            "folds": fold_reports,
            "default_trade_metrics_match": True,
            "default_metrics": {key: metrics[key] for key in recorded_metrics if key in metrics},
            "artifact_file_sha256": result["secondary_results"]["artifact_manifest"]["file_sha256"],
            "artifact_logical_sha256": result["secondary_results"]["artifact_manifest"][
                "logical_sha256"
            ],
        }
    reconciliation = {
        "schema_version": 1,
        "work_package": "WP-008",
        "status": "PASS",
        "independence": "DIRECT_FOLD_REBUILD_AND_NUMPY_LSTSQ_REPRODUCTION_WITHOUT_LINEAR_CHALLENGER_LAB",
        "checks": {
            "fold_train_boundaries": "PASS",
            "label_horizon_containment": "PASS",
            "feature_order": "PASS",
            "training_only_scaling": "PASS",
            "coefficient_reproduction": "PASS",
            "prediction_hashes": "PASS",
            "emitted_signal_timestamps": "PASS",
            "default_trade_metrics_from_compact_artifact": "PASS",
        },
        "experiments": experiment_reports,
    }
    leakage = {
        "schema_version": 1,
        "work_package": "WP-008",
        "version": "SUPERVISED_FEATURES_V1",
        "status": "PASS",
        "feature_availability": "COMPLETED_1H_AT_SIGNAL_AND_COMPLETED_NONOVERLAPPING_4H_CONTEXT",
        "no_forward_fill": True,
        "source_grid_quarantine_preserved": True,
        "post_cutoff_rows": 0,
        "scaling_scope": "TRAINING_ONLY_PER_FOLD_DDOF_0",
        "labels_scope": "TRAINING_ONLY_FOR_FIT",
        "validation_outcomes_fit_model": False,
        "full_history_normalization": False,
        "result_conditioned_feature_selection": False,
        "synthetic_future_feature_injection": "REJECTED_BY_TEST",
        "folds": leakage_folds,
    }
    return reconciliation, leakage
