"""Pre-result structural validation for the fixed WP-015 funding challenger."""

from __future__ import annotations

import inspect
import json
from collections import Counter
from pathlib import Path

import numpy as np
from app.research.evaluation_protocol import HOUR_US, utc_us
from app.research.funding import FEATURE, FundingContextSource
from app.research.supervised import FULL_FEATURES, IsolatedLabel, SupervisedRow
from app.research.wp014_model import HGBR_PARAMETERS
from app.research.wp015 import (
    CONTROL_VARIANT,
    PRIMARY_VARIANT,
    load_protocol,
    novelty_decision,
    preflight,
)
from app.research.wp015_lab import PRIMARY_FEATURES, FundingContextLab

ROOT = Path(__file__).resolve().parents[2]


def matrix(rows: int = 520) -> tuple[np.ndarray, np.ndarray]:
    index = np.arange(rows, dtype=np.float64)
    values = np.column_stack(
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
    target = 0.2 * (values[:, 0] > 0) - 0.1 * values[:, 1] * values[:, 6]
    return values, target


class SyntheticLab(FundingContextLab):
    def __init__(self, fold: dict, rows: list[SupervisedRow], labels: list[IsolatedLabel]):
        self.inputs = None  # type: ignore[assignment]
        self.features = None  # type: ignore[assignment]
        self.walk_forward = {"folds": [fold]}
        self.folds = [fold]
        self._rows = {row.signal_us: row for row in rows}
        self._labels = {label.signal_us: label for label in labels}
        self._training = {}
        self.exclusions = Counter()
        self.funding = FundingContextSource([rows[0].signal_us - HOUR_US], [0.0001])
        self.funding_values = {}
        self.dependencies: list[dict[str, str]] = []


def test_frozen_protocol_has_one_new_raw_feature_and_exact_model() -> None:
    protocol = load_protocol(ROOT)
    assert protocol["internal_features"] == list(FULL_FEATURES)
    assert protocol["primary_feature_order"] == [*FULL_FEATURES, FEATURE]
    assert tuple(protocol["primary_feature_order"]) == PRIMARY_FEATURES
    assert protocol["hgbr_parameters"] == HGBR_PARAMETERS
    assert protocol["folds"] == [2020, 2021, 2022, 2023, 2024]
    assert protocol["funding"]["transformations"] == 0
    assert protocol["funding_thresholds"] == protocol["feature_subsets"] == 0


def test_matched_training_universe_and_outcomes_are_purged() -> None:
    validation = utc_us("2020-01-02T00:00:00Z")
    boundary = validation - 216 * HOUR_US
    start = boundary - 520 * HOUR_US
    fold = {
        "fold_id": "DEV-2020",
        "train_start": "2019-12-02T08:00:00Z",
        "train_end_exclusive": "2019-12-24T00:00:00Z",
        "validation_start": "2020-01-02T00:00:00Z",
        "last_signal_inclusive": "2020-01-02T02:00:00Z",
    }
    assert utc_us(fold["train_start"]) == start
    values, target = matrix()
    rows = [
        SupervisedRow(
            start + index * HOUR_US,
            100.0,
            0,
            0,
            start + index * HOUR_US,
            tuple(float(value) for value in values[index]),
        )
        for index in range(520)
    ]
    labels = [
        IsolatedLabel(row.signal_us, "VALID", "EXPIRY", row.signal_us + HOUR_US, float(value))
        for row, value in zip(rows, target, strict=True)
    ]
    labels[-1] = IsolatedLabel(rows[-1].signal_us, "VALID", "EXPIRY", boundary, 0.0)
    lab = SyntheticLab(fold, rows, labels)
    primary = lab.fit_fold(PRIMARY_VARIANT, fold)
    control = lab.fit_fold(CONTROL_VARIANT, fold)
    assert primary.manifest["fit_rows"] == control.manifest["fit_rows"] == 519
    assert (
        primary.manifest["training_label_logical_sha256"]
        == control.manifest["training_label_logical_sha256"]
    )
    assert primary.manifest["feature_order"] == list(PRIMARY_FEATURES)
    assert control.manifest["feature_order"] == list(FULL_FEATURES)
    assert primary.model.as_record()["parameters"] == HGBR_PARAMETERS
    assert control.model.as_record()["parameters"] == HGBR_PARAMETERS
    assert primary.manifest["max_training_label_outcome_us"] < boundary


def test_search_memory_and_preflight_precede_results_without_loading_data() -> None:
    admission = novelty_decision(ROOT)
    primary, control = admission["variants"]
    assert primary["classification"] == "NEW_FAMILY" and primary["admitted"] is True
    assert control["classification"] == "KNOWN_INTERNAL_HGBR_MATCHED_CONTROL"
    assert control["admitted"] is False and control["authorized_as_matched_control"] is True
    results_exist = any(
        (ROOT / "research/experiments" / experiment / "result.json").exists()
        for experiment in (
            "EXP-ML-024-INTERNAL-PLUS-FUNDING-HGBR",
            "EXP-ML-025-INTERNAL-HGBR-MATCHED-FUNDING",
        )
    )
    gate = (
        json.loads((ROOT / "reports/validation/WP-015-PREFLIGHT.json").read_text())
        if results_exist
        else preflight(ROOT)
    )
    assert gate["status"] == "PASS"
    assert gate["market_results_observed"] == gate["post_cutoff_access"] == 0
    assert gate["sealed_queries"] == 0
    assert gate["matched_eligible_universe"] is True


def test_committed_funding_audits_are_safe_metadata_only() -> None:
    integrity = json.loads((ROOT / "reports/validation/WP-015-FUNDING-INTEGRITY.json").read_text())
    asof = json.loads((ROOT / "reports/validation/WP-015-FUNDING-ASOF-AUDIT.json").read_text())
    assert integrity["status"] == asof["status"] == "PASS"
    assert integrity["post_cutoff_records"] == integrity["duplicates"] == 0
    assert integrity["mark_price_feature"] is False
    assert integrity["predicted_funding"] is False
    assert integrity["premium_basis_oi_ratio"] is False
    assert asof["strict_funding_time_before_signal_time"] is True
    assert asof["same_timestamp_exclusion_checks"] == 5819
    source = inspect.getsource(FundingContextLab).lower()
    assert all(word not in source for word in ("markprice", "predicted_funding", "open_interest"))
