"""Frozen foldwise OLS training and production execution for WP-008."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

import numpy as np
import pyarrow as pa

from app.backtest.engine import simulate
from app.backtest.models import ExitReason, Intent

from .continuation_lab import DATASET_HASH, DATASET_ID, MINUTE_US, PROFILES, ResearchInputs, costs
from .evaluation_protocol import EPOCH, HOUR_US, summarize_trades, utc_us
from .linear_model import FittedLinearModel, fit_ols, model_hash
from .supervised import (
    CONFIG_FEATURES,
    FEATURE_VERSION,
    FULL_FEATURES,
    STRATEGY_VERSION,
    IsolatedLabel,
    SupervisedDataError,
    SupervisedFeatureSource,
    SupervisedRow,
    dependency_identity,
    isolated_label,
    label_hash,
    vector_hash,
)

TRIAL_SCHEMA = pa.schema(
    [
        pa.field("profile", pa.string(), nullable=False),
        pa.field("fold_id", pa.string(), nullable=False),
        pa.field("signal_us", pa.int64(), nullable=False),
        pa.field("prediction_signal_us", pa.int64(), nullable=False),
        pa.field("predicted_default_net_r", pa.float64(), nullable=False),
        pa.field("reference", pa.float64(), nullable=False),
        pa.field("status", pa.string(), nullable=False),
        pa.field("reason", pa.string(), nullable=False),
        pa.field("exit_us", pa.int64(), nullable=True),
        pa.field("net_r", pa.float64(), nullable=True),
        pa.field("gross_r", pa.float64(), nullable=True),
        pa.field("cost_drag_r", pa.float64(), nullable=True),
        pa.field("net_return_bps", pa.float64(), nullable=True),
        pa.field("position_available_us", pa.int64(), nullable=False),
    ]
)


def validate_config(config: dict[str, Any]) -> None:
    variant_value = config.get("variant")
    if not isinstance(variant_value, str):
        raise SupervisedDataError("linear configuration lacks a variant")
    variant = variant_value
    expected = {
        "strategy_version": STRATEGY_VERSION,
        "variant": variant,
        "feature_version": FEATURE_VERSION,
        "features": list(CONFIG_FEATURES.get(variant, ())),
        "label": "ISOLATED_FIXED_PLAN_DEFAULT_NET_R_V1",
        "algorithm": "NUMPY_FLOAT64_ORDINARY_LEAST_SQUARES_WITH_INTERCEPT",
        "fit_intercept": True,
        "scaling": "TRAINING_ONLY_MEAN_STD_DDOF_0",
        "regularization": "NONE",
        "signal_rule": "predicted_default_net_R > 0.0",
        "signal_threshold": 0.0,
        "stop_fraction": 0.02,
        "target_fraction": 0.04,
        "max_hold_minutes": 1440,
        "profiles": list(PROFILES),
        "hyperparameter_searches": 0,
        "threshold_searches": 0,
    }
    if variant not in CONFIG_FEATURES or config != expected:
        raise SupervisedDataError("linear configuration differs from the frozen declaration")


def trade_at(
    inputs: ResearchInputs,
    row: SupervisedRow,
    prediction_signal_us: int,
    prediction: float,
    variant: str,
    profile: str,
) -> tuple[dict[str, Any], int]:
    instant = EPOCH + timedelta(microseconds=row.signal_us)
    reference = Decimal(str(row.reference))
    intent = Intent(
        f"{variant}:{profile}",
        f"{STRATEGY_VERSION}:{variant}",
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
    record = simulate(intent, inputs.path(row.signal_us), costs(profile))
    trade: dict[str, Any] = {
        "signal_us": row.signal_us,
        "year": instant.year,
        "status": record.data_quality_status,
        "reason": str(record.exit_reason),
        "record": record.deterministic_dict(),
        "prediction_signal_us": prediction_signal_us,
        "predicted_default_net_r": prediction,
        "reference": row.reference,
        "regime": "UNCLASSIFIED",
    }
    if record.data_quality_status == "VALID":
        assert record.exit_timestamp is not None and record.net_r is not None
        assert record.gross_r is not None and record.net_pnl is not None
        assert record.entry_raw_price is not None
        exit_us = utc_us(record.exit_timestamp)
        trade.update(
            exit_us=exit_us,
            net_r=float(record.net_r),
            gross_r=float(record.gross_r),
            cost_drag_r=float(record.gross_r - record.net_r),
            net_return_bps=float(record.net_pnl / record.entry_raw_price * 10000),
        )
        available_us = exit_us if record.exit_reason == ExitReason.EXPIRY else exit_us + MINUTE_US
    elif record.data_quality_status == "UNRESOLVED":
        available_us = row.signal_us + 1440 * MINUTE_US
    else:
        available_us = row.signal_us
    trade["position_available_us"] = available_us
    return trade, available_us


@dataclass(frozen=True)
class FoldFit:
    fold_id: str
    model: FittedLinearModel
    manifest: dict[str, Any]
    validation_rows: tuple[SupervisedRow, ...]
    validation_predictions: np.ndarray
    validation_diagnostics: dict[str, Any]


class LinearChallengerLab:
    """Build each fold from historical rows only, then execute four frozen profiles."""

    def __init__(
        self,
        inputs: ResearchInputs,
        features: SupervisedFeatureSource,
        protocol: dict[str, Any],
    ):
        self.inputs = inputs
        self.features = features
        self.protocol = protocol
        self._labels: dict[int, IsolatedLabel] = {}

    def _row(self, signal_us: int) -> SupervisedRow | None:
        try:
            return self.features.at(signal_us)
        except SupervisedDataError:
            return None

    def _label(self, row: SupervisedRow) -> IsolatedLabel:
        if row.signal_us not in self._labels:
            self._labels[row.signal_us] = isolated_label(self.inputs, row)
        return self._labels[row.signal_us]

    def fit_fold(self, config: dict[str, Any], fold: dict[str, Any]) -> FoldFit:
        validate_config(config)
        names = tuple(config["features"])
        indices = tuple(FULL_FEATURES.index(name) for name in names)
        train_start = utc_us(fold["train_start"])
        train_end = utc_us(fold["train_end_exclusive"])
        validation_start = utc_us(fold["validation_start"])
        if validation_start - train_end != 216 * HOUR_US:
            raise SupervisedDataError("frozen 216h training purge boundary changed")
        train_rows: list[SupervisedRow] = []
        train_labels: list[IsolatedLabel] = []
        exclusions: Counter[str] = Counter()
        for signal_us in range(train_start, train_end, HOUR_US):
            row = self._row(signal_us)
            if row is None:
                exclusions["feature_ineligible"] += 1
                continue
            label = self._label(row)
            if label.status != "VALID" or label.net_r is None:
                exclusions[f"label_{label.status.lower()}"] += 1
                continue
            if label.outcome_us >= validation_start:
                raise SupervisedDataError("training label outcome overlaps validation")
            train_rows.append(row)
            train_labels.append(label)
        if not train_rows:
            raise SupervisedDataError("fold has no eligible training labels")
        times = np.asarray([row.signal_us for row in train_rows], dtype=np.int64)
        matrix = np.asarray(
            [[row.values[index] for index in indices] for row in train_rows], dtype=np.float64
        )
        labels = np.asarray([label.net_r for label in train_labels], dtype=np.float64)
        outcomes = np.asarray([label.outcome_us for label in train_labels], dtype=np.int64)
        matrix_identity = vector_hash(times, matrix, names)
        label_identity = label_hash(times, labels, outcomes)
        dependencies = dependency_identity()
        dependency_hash = hashlib.sha256(
            json.dumps(dependencies, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        model = fit_ols(
            matrix,
            labels,
            names,
            training_matrix_hash=matrix_identity,
            training_label_hash=label_identity,
            dependency_hash=dependency_hash,
        )
        validation_rows = tuple(
            row
            for signal_us in range(
                validation_start, utc_us(fold["last_signal_inclusive"]) + 1, HOUR_US
            )
            if (row := self._row(signal_us)) is not None
        )
        validation_matrix = np.asarray(
            [[row.values[index] for index in indices] for row in validation_rows], dtype=np.float64
        )
        predictions = model.predict(validation_matrix)
        validation_labels = [self._label(row) for row in validation_rows]
        paired = [
            (prediction, label.net_r)
            for prediction, label in zip(predictions.tolist(), validation_labels, strict=True)
            if label.status == "VALID" and label.net_r is not None
        ]
        correlation = (
            float(np.corrcoef([item[0] for item in paired], [item[1] for item in paired])[0, 1])
            if len(paired) > 1
            else None
        )
        positive_labels = [label for prediction, label in paired if prediction > 0.0]
        manifest = {
            "fold_id": fold["fold_id"],
            "feature_version": FEATURE_VERSION,
            "feature_order": list(names),
            "fit_rows": len(train_rows),
            "training_signal_min_us": int(times.min()),
            "training_signal_max_us": int(times.max()),
            "max_training_label_outcome_us": int(outcomes.max()),
            "validation_start_us": validation_start,
            "validation_end_exclusive_us": utc_us(fold["validation_end_exclusive"]),
            "purge_boundary_exclusive_us": train_end,
            "exclusions": dict(sorted(exclusions.items())),
            "training_matrix_logical_sha256": matrix_identity,
            "training_label_logical_sha256": label_identity,
            "feature_label_dependencies": dependencies,
            "dependency_hash": dependency_hash,
            "regeneration_command": ".venv/Scripts/python.exe scripts/run_wp008.py",
            "training_rows_committed": False,
        }
        validation_diagnostics = {
            "fold_id": fold["fold_id"],
            "validation_eligible_count": len(validation_rows),
            "prediction_positive_count": int(np.count_nonzero(predictions > 0.0)),
            "isolated_label_valid_count": len(paired),
            "isolated_label_exclusions": len(validation_rows) - len(paired),
            "prediction_label_pearson": correlation,
            "mean_prediction": float(predictions.mean()),
            "mean_isolated_realized_r_prediction_positive": (
                float(np.mean(positive_labels)) if positive_labels else None
            ),
            "prediction_hash": hashlib.sha256(
                np.asarray([row.signal_us for row in validation_rows], dtype="<i8").tobytes()
                + np.asarray(predictions, dtype="<f8").tobytes()
            ).hexdigest(),
        }
        return FoldFit(
            fold["fold_id"], model, manifest, validation_rows, predictions, validation_diagnostics
        )

    def fit_configuration(self, config: dict[str, Any]) -> tuple[FoldFit, ...]:
        validate_config(config)
        return tuple(self.fit_fold(config, fold) for fold in self.protocol["folds"])

    def run_profile(
        self, config: dict[str, Any], fits: tuple[FoldFit, ...], profile: str
    ) -> dict[str, Any]:
        validate_config(config)
        if profile not in PROFILES:
            raise SupervisedDataError("undeclared robustness profile")
        variant = config["variant"]
        feature_indices = tuple(FULL_FEATURES.index(name) for name in config["features"])
        trades: list[dict[str, Any]] = []
        fold_diagnostics = []
        for fold, fit in zip(self.protocol["folds"], fits, strict=True):
            if fit.fold_id != fold["fold_id"]:
                raise SupervisedDataError("fold model order changed")
            blocked_until = -1
            suppressed = 0
            predictions = {
                row.signal_us: float(value)
                for row, value in zip(fit.validation_rows, fit.validation_predictions, strict=True)
            }
            emitted = 0
            for row in fit.validation_rows:
                prediction_signal_us = (
                    row.signal_us - HOUR_US if profile == "DELAY_1H" else row.signal_us
                )
                if profile == "DELAY_1H":
                    prior = self._row(prediction_signal_us)
                    if prior is None:
                        continue
                    vector = np.asarray(
                        [[prior.values[index] for index in feature_indices]], dtype=np.float64
                    )
                    prediction = float(fit.model.predict(vector)[0])
                else:
                    prediction = predictions[row.signal_us]
                if prediction <= 0.0:
                    continue
                emitted += 1
                if row.signal_us < blocked_until:
                    suppressed += 1
                    continue
                trade, blocked_until = trade_at(
                    self.inputs, row, prediction_signal_us, prediction, variant, profile
                )
                trade["fold_id"] = fold["fold_id"]
                trades.append(trade)
            fold_diagnostics.append(
                {
                    "fold_id": fold["fold_id"],
                    "validation_eligible_count": len(fit.validation_rows),
                    "prediction_positive_count": emitted,
                    "suppressed_positive_count": suppressed,
                    "emitted_trade_count": sum(
                        trade["fold_id"] == fold["fold_id"] for trade in trades
                    ),
                }
            )
        return {
            "profile": profile,
            "variant": variant,
            "trades": trades,
            "fold_diagnostics": fold_diagnostics,
            "summary": summarize_trades(trades, self.protocol, allow_unclassified_regime=True),
        }

    def run_configuration(self, config: dict[str, Any]) -> dict[str, Any]:
        fits = self.fit_configuration(config)
        profiles = {profile: self.run_profile(config, fits, profile) for profile in PROFILES}
        return {
            "variant": config["variant"],
            "fits": [
                {
                    "fold_id": fit.fold_id,
                    "model": {**fit.model.as_record(), "model_hash": model_hash(fit.model)},
                    "training_manifest": fit.manifest,
                    "validation_diagnostics": fit.validation_diagnostics,
                }
                for fit in fits
            ],
            "profiles": profiles,
        }


def parquet_rows(profile_result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for trade in profile_result["trades"]:
        rows.append(
            {
                "profile": profile_result["profile"],
                "fold_id": trade["fold_id"],
                "signal_us": trade["signal_us"],
                "prediction_signal_us": trade["prediction_signal_us"],
                "predicted_default_net_r": trade["predicted_default_net_r"],
                "reference": trade["reference"],
                "status": trade["status"],
                "reason": trade["reason"],
                "exit_us": trade.get("exit_us"),
                "net_r": trade.get("net_r"),
                "gross_r": trade.get("gross_r"),
                "cost_drag_r": trade.get("cost_drag_r"),
                "net_return_bps": trade.get("net_return_bps"),
                "position_available_us": trade["position_available_us"],
            }
        )
    return rows
