"""Pre-result structural tests for the fixed WP-014 challenger."""

from __future__ import annotations

import inspect
import json
import math
from collections import Counter

import numpy as np
from app.research.evaluation_protocol import HOUR_US, utc_us
from app.research.supervised import FULL_FEATURES, IsolatedLabel, SupervisedRow
from app.research.wp004 import ROOT
from app.research.wp014 import (
    CONTROL_VARIANT,
    PREDICTION_TOLERANCE,
    PRIMARY_VARIANT,
    novelty_decision,
    preflight,
)
from app.research.wp014_lab import PURGE_US, ShallowInternalLab
from app.research.wp014_model import HGBR_PARAMETERS, MODEL_VERSION, SKLEARN_VERSION, fit_hgbr


def synthetic_matrix(rows: int = 512) -> tuple[np.ndarray, np.ndarray]:
    index = np.arange(rows, dtype=np.float64)
    matrix = np.column_stack(
        (
            np.sin(index / 7),
            np.cos(index / 11),
            (index % 17) / 17,
            np.sqrt(index + 1) / 25,
            np.log1p(index) / 10,
            ((index % 29) - 14) / 14,
            np.sin(index / 19) * 0.4,
            np.cos(index / 23) * 0.4,
        )
    )
    target = 0.2 * (matrix[:, 0] > 0) - 0.1 * matrix[:, 1] * matrix[:, 6]
    return matrix, target


def test_exact_hgbr_parameters_and_deterministic_serialization() -> None:
    expected = {
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
    assert HGBR_PARAMETERS == expected
    assert MODEL_VERSION == "SHALLOW_INTERNAL_HGBR_V1"
    assert SKLEARN_VERSION == "1.7.2"
    matrix, target = synthetic_matrix()
    values = [
        fit_hgbr(
            matrix,
            target,
            training_matrix_hash="a" * 64,
            training_label_hash="b" * 64,
            dependency_hash="c" * 64,
        )
        for _ in range(2)
    ]
    assert values[0].serialization_sha256 == values[1].serialization_sha256
    assert values[0].identity_sha256 == values[1].identity_sha256
    assert np.array_equal(values[0].predict(matrix), values[1].predict(matrix))
    record = values[0].as_record()
    assert record["input_scaling"] == "NONE_RAW_GOVERNED_VALUES"
    assert record["boosting_iterations"] == 64
    assert record["tree_count"] == 64


class SyntheticLab(ShallowInternalLab):
    def __init__(self, fold: dict, rows: list[SupervisedRow], labels: list[IsolatedLabel]):
        self.inputs = None  # type: ignore[assignment]
        self.features = None  # type: ignore[assignment]
        self.walk_forward = {"folds": [fold]}
        self.folds = [fold]
        self._rows = {row.signal_us: row for row in rows}
        self._labels = {label.signal_us: label for label in labels}
        self._training = {}
        self.exclusions = Counter()


def test_training_purge_outcome_containment_and_matched_universe() -> None:
    validation = utc_us("2020-01-02T00:00:00Z")
    boundary = validation - PURGE_US
    start = boundary - 520 * HOUR_US
    fold = {
        "fold_id": "SYNTHETIC",
        "train_start": "2019-12-02T08:00:00Z",
        "train_end_exclusive": "2019-12-24T00:00:00Z",
        "validation_start": "2020-01-02T00:00:00Z",
    }
    assert utc_us(fold["train_start"]) == start
    matrix, target = synthetic_matrix(520)
    rows = [
        SupervisedRow(
            start + index * HOUR_US,
            100.0,
            0,
            0,
            start + index * HOUR_US,
            tuple(float(value) for value in matrix[index]),
        )
        for index in range(520)
    ]
    labels = [
        IsolatedLabel(row.signal_us, "VALID", "EXPIRY", row.signal_us + HOUR_US, float(value))
        for row, value in zip(rows, target, strict=True)
    ]
    labels[-1] = IsolatedLabel(rows[-1].signal_us, "VALID", "EXPIRY", boundary, 0.0)
    lab = SyntheticLab(fold, rows, labels)
    selected_rows, selected_labels = lab.training_rows(fold)
    assert len(selected_rows) == len(selected_labels) == 519
    assert max(label.outcome_us for label in selected_labels) < boundary
    primary = lab.fit_fold(PRIMARY_VARIANT, fold)
    control = lab.fit_fold(CONTROL_VARIANT, fold)
    assert (
        primary.manifest["training_matrix_logical_sha256"]
        == control.manifest["training_matrix_logical_sha256"]
    )
    assert (
        primary.manifest["training_label_logical_sha256"]
        == control.manifest["training_label_logical_sha256"]
    )
    assert primary.manifest["input_scaling"] == "NONE_RAW_GOVERNED_VALUES"
    assert control.manifest["input_scaling"] == "TRAINING_ONLY_MEAN_STD_DDOF_0"
    assert (
        control.manifest["validation_start_us"] - control.manifest["purge_boundary_exclusive_us"]
        == 216 * HOUR_US
    )


def test_protocol_feature_scope_profiles_and_threshold_are_frozen() -> None:
    protocol = json.loads(
        (ROOT / "research/protocols/WP-014-SHALLOW-INTERNAL-HGBR-V1.json").read_text()
    )
    assert protocol["features"] == list(FULL_FEATURES)
    assert protocol["models"][PRIMARY_VARIANT]["parameters"] == HGBR_PARAMETERS
    assert protocol["models"][PRIMARY_VARIANT]["input_scaling"] == ("NONE_RAW_GOVERNED_VALUES")
    assert protocol["profiles"] == ["DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"]
    assert protocol["signal"] == {
        "operator": ">",
        "predicted_field": "predicted_default_net_R",
        "threshold": 0.0,
        "threshold_variants": 0,
    }
    assert PREDICTION_TOLERANCE == 1e-10
    source = inspect.getsource(ShallowInternalLab).lower()
    assert all(word not in source for word in ("nfci", "macro", "exogenous", "aligned"))


def test_search_memory_admits_primary_and_discloses_duplicate_control() -> None:
    admission = novelty_decision(ROOT)
    primary, control = admission["variants"]
    assert primary["classification"] == "NEW_FAMILY" and primary["admitted"] is True
    assert control["classification"] == "DUPLICATE_MATCHED_CONTROL_REPLICATION"
    assert control["admitted"] is False and control["authorized_as_matched_control"] is True
    assert control["matched_experiment_ids"] == ["EXP-ML-014-LINEAR-NET-R-FULL"]


def test_wp014_preflight_passes_without_loading_market_data() -> None:
    report = preflight(ROOT)
    assert report["status"] == "PASS"
    assert report["market_results_observed"] == 0
    assert report["post_cutoff_access"] == report["sealed_queries"] == 0
    assert report["forbidden_features"] == []
    assert math.isclose(report["prediction_tolerance"], 1e-10, rel_tol=0, abs_tol=0)
