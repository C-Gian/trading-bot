"""Frozen WP-014 annual walk-forward for HGBR and matched OLS."""

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

from .continuation_lab import DATASET_HASH, DATASET_ID, PROFILES, ResearchInputs, costs
from .evaluation_protocol import EPOCH, HOUR_US, summarize_trades, utc_us
from .linear_model import FittedLinearModel, fit_ols, model_hash
from .supervised import (
    FULL_FEATURES,
    IsolatedLabel,
    SupervisedDataError,
    SupervisedFeatureSource,
    SupervisedRow,
    isolated_label,
    label_hash,
    vector_hash,
)
from .wp014 import CONTROL_VARIANT, PRIMARY_VARIANT, VARIANTS, dependency_manifest
from .wp014_model import FittedHGBR, fit_hgbr

STRATEGY_VERSION = "SHALLOW_INTERNAL_HGBR_V1"
PURGE_US = 216 * HOUR_US
MINUTE_US = 60_000_000

TRIAL_SCHEMA = pa.schema(
    [
        ("variant", pa.string(), False),
        ("profile", pa.string(), False),
        ("fold_id", pa.string(), False),
        ("signal_us", pa.int64(), False),
        ("prediction_signal_us", pa.int64(), False),
        ("predicted_default_net_r", pa.float64(), False),
        ("status", pa.string(), False),
        ("reason", pa.string(), False),
        ("net_r", pa.float64()),
        ("gross_r", pa.float64()),
        ("exit_us", pa.int64()),
    ]
)


class WP014LabError(SupervisedDataError):
    """The shallow nonlinear substrate violated its frozen declaration."""


@dataclass(frozen=True)
class FoldModel:
    fold_id: str
    model: FittedHGBR | FittedLinearModel
    manifest: dict[str, Any]


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


class ShallowInternalLab:
    """Build one F1-F8 universe and fit exactly one model per configuration/fold."""

    def __init__(
        self,
        inputs: ResearchInputs,
        features: SupervisedFeatureSource,
        walk_forward: dict[str, Any],
    ):
        self.inputs = inputs
        self.features = features
        self.walk_forward = walk_forward
        self.folds = walk_forward["folds"]
        self._rows: dict[int, SupervisedRow | None] = {}
        self._labels: dict[int, IsolatedLabel] = {}
        self._training: dict[str, tuple[list[SupervisedRow], list[IsolatedLabel]]] = {}
        self.exclusions: Counter[str] = Counter()

    def row(self, signal_us: int) -> SupervisedRow | None:
        if signal_us in self._rows:
            return self._rows[signal_us]
        try:
            row = self.features.at(signal_us)
        except SupervisedDataError:
            self.exclusions["internal_feature_ineligible"] += 1
            self._rows[signal_us] = None
            return None
        if len(row.values) != len(FULL_FEATURES):
            raise WP014LabError("feature row is not the frozen F1-F8 vector")
        self._rows[signal_us] = row
        return row

    def label(self, row: SupervisedRow) -> IsolatedLabel:
        if row.signal_us not in self._labels:
            self._labels[row.signal_us] = isolated_label(self.inputs, row)
        return self._labels[row.signal_us]

    def training_rows(
        self, fold: dict[str, Any]
    ) -> tuple[list[SupervisedRow], list[IsolatedLabel]]:
        fold_id = str(fold["fold_id"])
        if fold_id in self._training:
            return self._training[fold_id]
        start = utc_us(fold["train_start"])
        boundary = utc_us(fold["train_end_exclusive"])
        if utc_us(fold["validation_start"]) - boundary != PURGE_US:
            raise WP014LabError("frozen 216h purge boundary changed")
        rows: list[SupervisedRow] = []
        labels: list[IsolatedLabel] = []
        for signal_us in range(start, boundary, HOUR_US):
            row = self.row(signal_us)
            if row is None:
                continue
            label = self.label(row)
            if label.status != "VALID" or label.net_r is None:
                self.exclusions[f"label_{label.status.lower()}"] += 1
                continue
            if label.outcome_us >= boundary:
                self.exclusions["outcome_after_purge_boundary"] += 1
                continue
            rows.append(row)
            labels.append(label)
        if not rows:
            raise WP014LabError("fold has no eligible training rows")
        self._training[fold_id] = (rows, labels)
        return rows, labels

    def fit_fold(self, variant: str, fold: dict[str, Any]) -> FoldModel:
        rows, labels = self.training_rows(fold)
        times = np.asarray([row.signal_us for row in rows], dtype=np.int64)
        matrix = np.asarray([row.values for row in rows], dtype=np.float64)
        target = np.asarray([label.net_r for label in labels], dtype=np.float64)
        outcomes = np.asarray([label.outcome_us for label in labels], dtype=np.int64)
        dependencies = dependency_manifest()
        dependency_hash = hashlib.sha256(
            json.dumps(dependencies, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        matrix_identity = vector_hash(times, matrix, FULL_FEATURES)
        label_identity = label_hash(times, target, outcomes)
        if variant == PRIMARY_VARIANT:
            model: FittedHGBR | FittedLinearModel = fit_hgbr(
                matrix,
                target,
                training_matrix_hash=matrix_identity,
                training_label_hash=label_identity,
                dependency_hash=dependency_hash,
            )
            scaling = "NONE_RAW_GOVERNED_VALUES"
        elif variant == CONTROL_VARIANT:
            model = fit_ols(
                matrix,
                target,
                FULL_FEATURES,
                training_matrix_hash=matrix_identity,
                training_label_hash=label_identity,
                dependency_hash=dependency_hash,
            )
            scaling = "TRAINING_ONLY_MEAN_STD_DDOF_0"
        else:
            raise WP014LabError("undeclared WP-014 configuration")
        manifest = {
            "fold_id": fold["fold_id"],
            "variant": variant,
            "feature_order": list(FULL_FEATURES),
            "input_scaling": scaling,
            "fit_rows": len(rows),
            "training_signal_min_us": int(times.min()),
            "training_signal_max_us": int(times.max()),
            "max_training_label_outcome_us": int(outcomes.max()),
            "purge_boundary_exclusive_us": utc_us(fold["train_end_exclusive"]),
            "validation_start_us": utc_us(fold["validation_start"]),
            "training_matrix_logical_sha256": matrix_identity,
            "training_label_logical_sha256": label_identity,
            "training_rows_committed": False,
        }
        return FoldModel(str(fold["fold_id"]), model, manifest)

    def fit_configuration(self, variant: str) -> tuple[FoldModel, ...]:
        if variant not in VARIANTS:
            raise WP014LabError("undeclared WP-014 configuration")
        return tuple(self.fit_fold(variant, fold) for fold in self.folds)

    def predict(self, fits: tuple[FoldModel, ...]) -> dict[int, float]:
        predictions: dict[int, float] = {}
        for fold, fit in zip(self.folds, fits, strict=True):
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start - HOUR_US, end + 1, HOUR_US):
                if signal_us in predictions:
                    continue
                row = self.row(signal_us)
                if row is None:
                    continue
                matrix = np.asarray([row.values], dtype=np.float64)
                predictions[signal_us] = float(fit.model.predict(matrix)[0])
        return predictions

    def run_profile(
        self, variant: str, predictions: dict[int, float], profile: str
    ) -> dict[str, Any]:
        if profile not in PROFILES:
            raise WP014LabError("undeclared profile")
        trades: list[dict[str, Any]] = []
        diagnostics = []
        for fold in self.folds:
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            blocked_until = -1
            eligible = positive = suppressed = 0
            for signal_us in range(start, end + 1, HOUR_US):
                row = self.row(signal_us)
                if row is None:
                    continue
                eligible += 1
                source_us = signal_us - HOUR_US if profile == "DELAY_1H" else signal_us
                prediction = predictions.get(source_us)
                if prediction is None or prediction <= 0.0:
                    continue
                positive += 1
                if signal_us < blocked_until:
                    suppressed += 1
                    continue
                trade, blocked_until = trade_at(
                    self.inputs, row, source_us, prediction, variant, profile
                )
                trade["fold_id"] = fold["fold_id"]
                trades.append(trade)
            diagnostics.append(
                {
                    "fold_id": fold["fold_id"],
                    "validation_eligible_count": eligible,
                    "prediction_positive_count": positive,
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
            "fold_diagnostics": diagnostics,
            "summary": summarize_trades(trades, self.walk_forward, allow_unclassified_regime=True),
        }

    @staticmethod
    def _distribution(values: list[float]) -> dict[str, float | int | None]:
        if not values:
            return {
                "count": 0,
                "minimum": None,
                "q25": None,
                "median": None,
                "q75": None,
                "maximum": None,
                "mean": None,
                "std_ddof_0": None,
            }
        array = np.asarray(values, dtype=np.float64)
        return {
            "count": len(values),
            "minimum": float(array.min()),
            "q25": float(np.quantile(array, 0.25)),
            "median": float(np.quantile(array, 0.5)),
            "q75": float(np.quantile(array, 0.75)),
            "maximum": float(array.max()),
            "mean": float(array.mean()),
            "std_ddof_0": float(array.std(ddof=0)),
        }

    def prediction_diagnostics(self, predictions: dict[int, float]) -> dict[str, Any]:
        paired: list[tuple[float, float]] = []
        all_predictions: list[float] = []
        positive = eligible = 0
        per_fold: dict[str, Any] = {}
        for fold in self.folds:
            fold_pairs: list[tuple[float, float]] = []
            fold_predictions: list[float] = []
            fold_positive = fold_eligible = 0
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start, end + 1, HOUR_US):
                row = self.row(signal_us)
                if row is None:
                    continue
                fold_eligible += 1
                prediction = predictions.get(signal_us)
                if prediction is None:
                    continue
                fold_predictions.append(prediction)
                fold_positive += int(prediction > 0.0)
                label = self.label(row)
                if label.status == "VALID" and label.net_r is not None:
                    fold_pairs.append((prediction, label.net_r))
            eligible += fold_eligible
            positive += fold_positive
            all_predictions.extend(fold_predictions)
            paired.extend(fold_pairs)
            per_fold[str(fold["fold_id"])] = {
                "eligible_hours": fold_eligible,
                "prediction_positive_hours": fold_positive,
                "paired_labels": len(fold_pairs),
                "pearson": (
                    float(np.corrcoef(np.asarray(fold_pairs).T)[0, 1])
                    if len(fold_pairs) > 1
                    else None
                ),
                "distribution": self._distribution(fold_predictions),
            }
        return {
            "eligible_validation_hours": eligible,
            "prediction_positive_hours": positive,
            "paired_label_count": len(paired),
            "pooled_prediction_label_pearson": (
                float(np.corrcoef(np.asarray(paired).T)[0, 1]) if len(paired) > 1 else None
            ),
            "distribution": self._distribution(all_predictions),
            "per_fold": per_fold,
        }

    def run_configuration(self, variant: str) -> dict[str, Any]:
        fits = self.fit_configuration(variant)
        predictions = self.predict(fits)
        profiles = {
            profile: self.run_profile(variant, predictions, profile) for profile in PROFILES
        }
        fold_records = []
        for fit in fits:
            if isinstance(fit.model, FittedHGBR):
                model_record = fit.model.as_record()
            else:
                model_record = {**fit.model.as_record(), "model_hash": model_hash(fit.model)}
            fold_records.append(
                {
                    "fold_id": fit.fold_id,
                    "model": model_record,
                    "training_manifest": fit.manifest,
                }
            )
        return {
            "variant": variant,
            "strategy_version": STRATEGY_VERSION,
            "folds": fold_records,
            "model_fits": len(fits),
            "prediction_diagnostics": self.prediction_diagnostics(predictions),
            "profiles": profiles,
        }


def parquet_rows(profile_result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "variant": profile_result["variant"],
            "profile": profile_result["profile"],
            "fold_id": trade["fold_id"],
            "signal_us": trade["signal_us"],
            "prediction_signal_us": trade["prediction_signal_us"],
            "predicted_default_net_r": trade["predicted_default_net_r"],
            "status": trade["status"],
            "reason": trade["reason"],
            "net_r": trade.get("net_r"),
            "gross_r": trade.get("gross_r"),
            "exit_us": trade.get("exit_us"),
        }
        for trade in profile_result["trades"]
    ]


__all__ = [
    "PURGE_US",
    "STRATEGY_VERSION",
    "TRIAL_SCHEMA",
    "FoldModel",
    "ShallowInternalLab",
    "WP014LabError",
    "parquet_rows",
    "trade_at",
]
