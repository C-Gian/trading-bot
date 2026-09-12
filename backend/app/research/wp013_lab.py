"""Frozen WP-013 annual walk-forward for raw NFCI interaction OLS."""

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
from .nfci_context import NFCIContextSource
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
from .wp013 import (
    CONTROL_VARIANT,
    FEATURES,
    PRIMARY_VARIANT,
    VARIANTS,
    dependency_manifest,
)

STRATEGY_VERSION = "CONTEXTUAL_NFCI_INTERACTION_OLS_V1"
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
        ("nfci", pa.float64(), False),
        ("status", pa.string(), False),
        ("reason", pa.string(), False),
        ("net_r", pa.float64()),
        ("gross_r", pa.float64()),
        ("exit_us", pa.int64()),
    ]
)


class WP013LabError(SupervisedDataError):
    """The contextual-interaction substrate violated its frozen declaration."""


@dataclass(frozen=True)
class ContextRow:
    signal_us: int
    reference: float
    nfci: float
    base: tuple[float, ...]

    def values(self, variant: str) -> tuple[float, ...]:
        if variant == CONTROL_VARIANT:
            return self.base
        if variant == PRIMARY_VARIANT:
            return self.base + tuple(value * self.nfci for value in self.base)
        raise WP013LabError("undeclared WP-013 configuration")


@dataclass(frozen=True)
class FoldModel:
    fold_id: str
    model: FittedLinearModel
    manifest: dict[str, Any]


def trade_at(
    inputs: ResearchInputs,
    row: ContextRow,
    prediction_signal_us: int,
    prediction: float,
    variant: str,
    profile: str,
) -> tuple[dict[str, Any], int]:
    instant = EPOCH + timedelta(microseconds=row.signal_us)
    reference = Decimal(str(row.reference))
    intent = Intent(
        f"{variant}:{profile}", f"{STRATEGY_VERSION}:{variant}", DATASET_ID, DATASET_HASH,
        instant, "LONG", "NEXT_1M_OPEN", reference * Decimal("0.98"),
        reference * Decimal("1.04"), "FIXED_TARGET_OR_STOP_OR_24H", 1440,
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
        "nfci": row.nfci,
        "regime": "UNCLASSIFIED",
    }
    if record.data_quality_status == "VALID":
        assert record.exit_timestamp is not None and record.net_r is not None
        assert record.gross_r is not None and record.net_pnl is not None
        assert record.entry_raw_price is not None
        exit_us = utc_us(record.exit_timestamp)
        trade.update(
            exit_us=exit_us, net_r=float(record.net_r), gross_r=float(record.gross_r),
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


class ContextInteractionLab:
    """Build one matched universe, then fit one deterministic model per config/fold."""

    def __init__(self, inputs: ResearchInputs, internal: SupervisedFeatureSource,
                 context: NFCIContextSource, walk_forward: dict[str, Any]):
        self.inputs = inputs
        self.internal = internal
        self.context = context
        self.walk_forward = walk_forward
        self.folds = walk_forward["folds"]
        self._rows: dict[int, ContextRow | None] = {}
        self._labels: dict[int, IsolatedLabel] = {}
        self.exclusions: Counter[str] = Counter()

    def row(self, signal_us: int) -> ContextRow | None:
        if signal_us in self._rows:
            return self._rows[signal_us]
        try:
            internal = self.internal.at(signal_us)
        except SupervisedDataError:
            self.exclusions["internal_feature_ineligible"] += 1
            self._rows[signal_us] = None
            return None
        reading = self.context.at(signal_us)
        if reading is None:
            self.exclusions["nfci_unavailable"] += 1
            self._rows[signal_us] = None
            return None
        row = ContextRow(signal_us, internal.reference, reading.value, internal.values)
        if len(row.base) != len(FULL_FEATURES):
            raise WP013LabError("base feature row is not the frozen eight-value vector")
        if len(row.values(PRIMARY_VARIANT)) != 16 or len(row.values(CONTROL_VARIANT)) != 8:
            raise WP013LabError("contextual feature matrix width changed")
        self._rows[signal_us] = row
        return row

    def label(self, row: ContextRow) -> IsolatedLabel:
        if row.signal_us not in self._labels:
            proxy = SupervisedRow(row.signal_us, row.reference, 0, 0, row.signal_us, row.base)
            self._labels[row.signal_us] = isolated_label(self.inputs, proxy)
        return self._labels[row.signal_us]

    def training_rows(self, fold: dict[str, Any]) -> tuple[list[ContextRow], list[IsolatedLabel]]:
        start, boundary = utc_us(fold["train_start"]), utc_us(fold["train_end_exclusive"])
        if utc_us(fold["validation_start"]) - boundary != PURGE_US:
            raise WP013LabError("frozen 216h purge boundary changed")
        rows: list[ContextRow] = []
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
        return rows, labels

    def fit_fold(self, variant: str, fold: dict[str, Any]) -> FoldModel:
        rows, labels = self.training_rows(fold)
        if not rows:
            raise WP013LabError("fold has no eligible training rows")
        times = np.asarray([row.signal_us for row in rows], dtype=np.int64)
        matrix = np.asarray([row.values(variant) for row in rows], dtype=np.float64)
        target = np.asarray([label.net_r for label in labels], dtype=np.float64)
        outcomes = np.asarray([label.outcome_us for label in labels], dtype=np.int64)
        dependencies = dependency_manifest()
        dependency_hash = hashlib.sha256(
            json.dumps(dependencies, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        model = fit_ols(
            matrix, target, FEATURES[variant],
            training_matrix_hash=vector_hash(times, matrix, FEATURES[variant]),
            training_label_hash=label_hash(times, target, outcomes),
            dependency_hash=dependency_hash,
        )
        manifest = {
            "fold_id": fold["fold_id"], "variant": variant, "fit_rows": len(rows),
            "training_signal_min_us": int(times.min()), "training_signal_max_us": int(times.max()),
            "max_training_label_outcome_us": int(outcomes.max()),
            "purge_boundary_exclusive_us": utc_us(fold["train_end_exclusive"]),
            "validation_start_us": utc_us(fold["validation_start"]),
            "condition_number": model.condition_number, "rank": model.rank,
            "training_matrix_logical_sha256": model.training_matrix_hash,
            "training_label_logical_sha256": model.training_label_hash,
            "training_rows_committed": False,
        }
        return FoldModel(fold["fold_id"], model, manifest)

    def fit_configuration(self, variant: str) -> tuple[FoldModel, ...]:
        if variant not in VARIANTS:
            raise WP013LabError("undeclared WP-013 configuration")
        return tuple(self.fit_fold(variant, fold) for fold in self.folds)

    def predict(self, variant: str, fits: tuple[FoldModel, ...]) -> dict[int, float]:
        predictions: dict[int, float] = {}
        for fold, fit in zip(self.folds, fits, strict=True):
            start, end = utc_us(fold["validation_start"]), utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start - HOUR_US, end + 1, HOUR_US):
                if signal_us in predictions:
                    continue
                row = self.row(signal_us)
                if row is None:
                    continue
                vector = np.asarray([row.values(variant)], dtype=np.float64)
                predictions[signal_us] = float(fit.model.predict(vector)[0])
        return predictions

    def run_profile(self, variant: str, predictions: dict[int, float], profile: str) -> dict[str, Any]:
        if profile not in PROFILES:
            raise WP013LabError("undeclared profile")
        trades: list[dict[str, Any]] = []
        diagnostics = []
        for fold in self.folds:
            start, end = utc_us(fold["validation_start"]), utc_us(fold["last_signal_inclusive"])
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
            diagnostics.append({
                "fold_id": fold["fold_id"], "validation_eligible_count": eligible,
                "prediction_positive_count": positive, "suppressed_positive_count": suppressed,
                "emitted_trade_count": sum(t["fold_id"] == fold["fold_id"] for t in trades),
            })
        return {"profile": profile, "variant": variant, "trades": trades,
                "fold_diagnostics": diagnostics,
                "summary": summarize_trades(trades, self.walk_forward, allow_unclassified_regime=True)}

    def prediction_diagnostics(self, predictions: dict[int, float]) -> dict[str, Any]:
        paired: list[tuple[float, float]] = []
        positive = eligible = 0
        per_fold: dict[str, Any] = {}
        for fold in self.folds:
            fold_pairs: list[tuple[float, float]] = []
            fold_positive = fold_eligible = 0
            start, end = utc_us(fold["validation_start"]), utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start, end + 1, HOUR_US):
                row = self.row(signal_us)
                if row is None:
                    continue
                fold_eligible += 1
                prediction = predictions.get(signal_us)
                if prediction is None:
                    continue
                fold_positive += int(prediction > 0.0)
                label = self.label(row)
                if label.status == "VALID" and label.net_r is not None:
                    fold_pairs.append((prediction, label.net_r))
            eligible += fold_eligible
            positive += fold_positive
            paired.extend(fold_pairs)
            per_fold[fold["fold_id"]] = {
                "eligible_hours": fold_eligible, "prediction_positive_hours": fold_positive,
                "paired_labels": len(fold_pairs),
                "pearson": float(np.corrcoef(np.asarray(fold_pairs).T)[0, 1]) if len(fold_pairs) > 1 else None,
            }
        return {
            "eligible_validation_hours": eligible, "prediction_positive_hours": positive,
            "paired_label_count": len(paired),
            "pooled_prediction_label_pearson": (
                float(np.corrcoef(np.asarray(paired).T)[0, 1]) if len(paired) > 1 else None
            ),
            "per_fold": per_fold,
        }

    def run_configuration(self, variant: str) -> dict[str, Any]:
        fits = self.fit_configuration(variant)
        predictions = self.predict(variant, fits)
        profiles = {p: self.run_profile(variant, predictions, p) for p in PROFILES}
        return {
            "variant": variant, "strategy_version": STRATEGY_VERSION,
            "folds": [{"fold_id": f.fold_id,
                       "model": {**f.model.as_record(), "model_hash": model_hash(f.model)},
                       "training_manifest": f.manifest} for f in fits],
            "model_fits": len(fits), "prediction_diagnostics": self.prediction_diagnostics(predictions),
            "profiles": profiles,
        }


def parquet_rows(profile_result: dict[str, Any]) -> list[dict[str, Any]]:
    return [{
        "variant": profile_result["variant"], "profile": profile_result["profile"],
        "fold_id": trade["fold_id"], "signal_us": trade["signal_us"],
        "prediction_signal_us": trade["prediction_signal_us"],
        "predicted_default_net_r": trade["predicted_default_net_r"], "nfci": trade["nfci"],
        "status": trade["status"], "reason": trade["reason"],
        "net_r": trade.get("net_r"), "gross_r": trade.get("gross_r"),
        "exit_us": trade.get("exit_us"),
    } for trade in profile_result["trades"]]


__all__ = [
    "PURGE_US",
    "STRATEGY_VERSION",
    "TRIAL_SCHEMA",
    "ContextInteractionLab",
    "ContextRow",
    "FoldModel",
    "WP013LabError",
    "parquet_rows",
    "trade_at",
]
