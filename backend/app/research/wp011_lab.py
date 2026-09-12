"""WP-011 adaptive walk-forward lab: monthly recency-weighted models, four profiles.

One `EXPONENTIALLY_WEIGHTED_LINEAR_NET_R_V1` model becomes effective at the first UTC
hour of each calendar month. Its training universe is every eligible historical signal
row whose own instant and whose complete label outcome both fall strictly before the
purge boundary ``effective - 216h``, weighted by a frozen 180-day half-life.

Validation hours use whichever monthly model was already effective, so no validation
information can reach a fit. Nothing is refitted inside a validation window.
"""

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
from .ewls import (
    HALF_LIFE_DAYS,
    MODEL_VERSION,
    SIGNAL_THRESHOLD,
    FittedEwlsModel,
    fit_ewls,
    model_hash,
    prediction_hash,
)
from .macro import MacroFeatureSource, effective_model_index, monthly_effective_instants
from .supervised import (
    IsolatedLabel,
    SupervisedDataError,
    SupervisedFeatureSource,
    SupervisedRow,
    isolated_label,
    label_hash,
    vector_hash,
)
from .wp011 import PRIMARY_VARIANT, VARIANTS, dependency_manifest

STRATEGY_VERSION = "ADAPTIVE_EWLS_MACRO_NET_R_V1"
PURGE_US = 216 * HOUR_US
MINUTE_US = 60_000_000
HISTORY_START = "2017-08-17T04:00:00Z"

TRIAL_SCHEMA = pa.schema(
    [
        ("variant", pa.string(), False),
        ("profile", pa.string(), False),
        ("fold_id", pa.string(), False),
        ("signal_us", pa.int64(), False),
        ("prediction_signal_us", pa.int64(), False),
        ("model_effective_us", pa.int64(), False),
        ("predicted_default_net_r", pa.float64(), False),
        ("status", pa.string(), False),
        ("reason", pa.string(), False),
        ("net_r", pa.float64()),
        ("gross_r", pa.float64()),
        ("exit_us", pa.int64()),
    ]
)


class WP011LabError(SupervisedDataError):
    """The adaptive walk-forward substrate violated its frozen declaration."""


@dataclass(frozen=True)
class CombinedRow:
    """One hourly signal row carrying the frozen internal and macro feature values."""

    signal_us: int
    reference: float
    values: tuple[float, ...]


@dataclass(frozen=True)
class MonthlyModel:
    effective_us: int
    model: FittedEwlsModel
    manifest: dict[str, Any]


def trade_at(
    inputs: ResearchInputs,
    row: CombinedRow,
    prediction_signal_us: int,
    model_effective_us: int,
    prediction: float,
    variant: str,
    profile: str,
) -> tuple[dict[str, Any], int]:
    """Execute one frozen 2/4/24 plan under the requested cost profile."""
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
        "model_effective_us": model_effective_us,
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


class AdaptiveEwlsLab:
    """Builds the combined row universe once, then fits one model per calendar month."""

    def __init__(
        self,
        inputs: ResearchInputs,
        internal: SupervisedFeatureSource,
        macro: MacroFeatureSource,
        protocol: dict[str, Any],
    ):
        self.inputs = inputs
        self.internal = internal
        self.macro = macro
        self.protocol = protocol
        self.feature_order: tuple[str, ...] = tuple(protocol["features"][PRIMARY_VARIANT])
        self._rows: dict[int, CombinedRow] = {}
        self._labels: dict[int, IsolatedLabel] = {}
        self.exclusions: Counter[str] = Counter()

    # -- universe -----------------------------------------------------------------

    def _internal_row(self, signal_us: int) -> SupervisedRow | None:
        try:
            return self.internal.at(signal_us)
        except SupervisedDataError:
            return None

    def row(self, signal_us: int) -> CombinedRow | None:
        """Frozen 16-value row, or ``None`` when any required input is unavailable."""
        if signal_us in self._rows:
            return self._rows[signal_us]
        internal = self._internal_row(signal_us)
        if internal is None:
            self.exclusions["internal_feature_ineligible"] += 1
            return None
        macro = self.macro.at(signal_us)
        if macro is None:
            self.exclusions["macro_unavailable"] += 1
            return None
        combined = CombinedRow(signal_us, internal.reference, internal.values + macro.values)
        if len(combined.values) != 16:
            raise WP011LabError("combined feature row is not the frozen 16-value vector")
        self._rows[signal_us] = combined
        return combined

    def label(self, row: CombinedRow) -> IsolatedLabel:
        if row.signal_us not in self._labels:
            proxy = SupervisedRow(row.signal_us, row.reference, 0, 0, row.signal_us, row.values[:8])
            self._labels[row.signal_us] = isolated_label(self.inputs, proxy)
        return self._labels[row.signal_us]

    def build_universe(self, start_us: int, end_us: int) -> list[CombinedRow]:
        """Every eligible hourly row in ``[start_us, end_us]``, chronologically."""
        rows = []
        for signal_us in range(start_us, end_us + 1, HOUR_US):
            row = self.row(signal_us)
            if row is not None:
                rows.append(row)
        return rows

    # -- monthly models -----------------------------------------------------------

    def _indices(self, variant: str) -> tuple[int, ...]:
        names = self.protocol["features"][variant]
        return tuple(self.feature_order.index(name) for name in names)

    def fit_month(
        self,
        variant: str,
        effective_us: int,
        universe: list[CombinedRow],
        dependency_hash: str,
    ) -> MonthlyModel:
        """One weighted fit whose entire training universe precedes the purge boundary."""
        names = tuple(self.protocol["features"][variant])
        indices = self._indices(variant)
        boundary = effective_us - PURGE_US
        train_rows: list[CombinedRow] = []
        train_labels: list[IsolatedLabel] = []
        excluded: Counter[str] = Counter()
        for row in universe:
            if row.signal_us >= boundary:
                break
            label = self.label(row)
            if label.status != "VALID" or label.net_r is None:
                excluded[f"label_{label.status.lower()}"] += 1
                continue
            if label.outcome_us >= boundary:
                excluded["outcome_after_purge_boundary"] += 1
                continue
            train_rows.append(row)
            train_labels.append(label)
        if len(train_rows) <= len(names):
            raise WP011LabError("monthly model has insufficient eligible training rows")

        times = np.asarray([row.signal_us for row in train_rows], dtype=np.int64)
        matrix = np.asarray(
            [[row.values[index] for index in indices] for row in train_rows], dtype=np.float64
        )
        labels = np.asarray([label.net_r for label in train_labels], dtype=np.float64)
        outcomes = np.asarray([label.outcome_us for label in train_labels], dtype=np.int64)
        if int(times.max()) >= boundary or int(outcomes.max()) >= boundary:
            raise WP011LabError("training row or label outcome crossed the purge boundary")
        model = fit_ewls(
            matrix,
            labels,
            times,
            names,
            effective_us=effective_us,
            training_matrix_hash=vector_hash(times, matrix, names),
            training_label_hash=label_hash(times, labels, outcomes),
            dependency_hash=dependency_hash,
        )
        manifest = {
            "variant": variant,
            "effective_us": effective_us,
            "effective_utc": (EPOCH + timedelta(microseconds=effective_us))
            .isoformat()
            .replace("+00:00", "Z"),
            "purge_boundary_exclusive_us": boundary,
            "fit_rows": len(train_rows),
            "training_signal_min_us": int(times.min()),
            "training_signal_max_us": int(times.max()),
            "max_training_label_outcome_us": int(outcomes.max()),
            "effective_sample_size": model.effective_sample_size,
            "total_weight": model.total_weight,
            "condition_number": model.condition_number,
            "rank": model.rank,
            "half_life_days": HALF_LIFE_DAYS,
            "exclusions": dict(sorted(excluded.items())),
            "training_matrix_logical_sha256": model.training_matrix_hash,
            "training_label_logical_sha256": model.training_label_hash,
            "training_rows_committed": False,
        }
        return MonthlyModel(effective_us, model, manifest)

    def fit_configuration(self, variant: str) -> tuple[MonthlyModel, ...]:
        if variant not in VARIANTS:
            raise WP011LabError("undeclared WP-011 configuration")
        folds = self.protocol["folds"]
        first_validation = utc_us(folds[0]["validation_start"])
        last_signal = utc_us(folds[-1]["last_signal_inclusive"])
        universe = self.build_universe(utc_us(HISTORY_START), last_signal)
        effective = monthly_effective_instants(first_validation, last_signal)
        dependencies = dependency_manifest()
        dependency_hash = hashlib.sha256(
            json.dumps(dependencies, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return tuple(
            self.fit_month(variant, instant, universe, dependency_hash) for instant in effective
        )

    # -- predictions --------------------------------------------------------------

    def predict_validation(
        self, variant: str, models: tuple[MonthlyModel, ...]
    ) -> dict[int, tuple[float, int]]:
        """Prediction and effective model instant for every eligible validation hour."""
        indices = self._indices(variant)
        effective = tuple(model.effective_us for model in models)
        predictions: dict[int, tuple[float, int]] = {}
        for fold in self.protocol["folds"]:
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            # One hour earlier so DELAY_1H can reuse an already generated prediction.
            for signal_us in range(start - HOUR_US, end + 1, HOUR_US):
                if signal_us in predictions:
                    continue
                row = self.row(signal_us)
                if row is None:
                    continue
                position = effective_model_index(effective, signal_us)
                model = models[position]
                vector = np.asarray([[row.values[index] for index in indices]], dtype=np.float64)
                predictions[signal_us] = (
                    float(model.model.predict(vector)[0]),
                    model.effective_us,
                )
        return predictions

    # -- execution ----------------------------------------------------------------

    def run_profile(
        self,
        variant: str,
        models: tuple[MonthlyModel, ...],
        predictions: dict[int, tuple[float, int]],
        profile: str,
    ) -> dict[str, Any]:
        if profile not in PROFILES:
            raise WP011LabError("undeclared robustness profile")
        trades: list[dict[str, Any]] = []
        fold_diagnostics = []
        for fold in self.protocol["folds"]:
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            blocked_until = -1
            suppressed = 0
            emitted = 0
            eligible = 0
            for signal_us in range(start, end + 1, HOUR_US):
                row = self.row(signal_us)
                if row is None:
                    continue
                eligible += 1
                prediction_signal_us = signal_us - HOUR_US if profile == "DELAY_1H" else signal_us
                source = predictions.get(prediction_signal_us)
                if source is None:
                    continue
                prediction, model_effective_us = source
                if prediction <= SIGNAL_THRESHOLD:
                    continue
                emitted += 1
                if signal_us < blocked_until:
                    suppressed += 1
                    continue
                trade, blocked_until = trade_at(
                    self.inputs,
                    row,
                    prediction_signal_us,
                    model_effective_us,
                    prediction,
                    variant,
                    profile,
                )
                trade["fold_id"] = fold["fold_id"]
                trades.append(trade)
            fold_diagnostics.append(
                {
                    "fold_id": fold["fold_id"],
                    "validation_eligible_count": eligible,
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
            "monthly_models": len(models),
        }

    def run_configuration(self, variant: str) -> dict[str, Any]:
        models = self.fit_configuration(variant)
        predictions = self.predict_validation(variant, models)
        profiles = {
            profile: self.run_profile(variant, models, predictions, profile) for profile in PROFILES
        }
        return {
            "variant": variant,
            "model_version": MODEL_VERSION,
            "monthly_models": [
                {
                    "effective_us": item.effective_us,
                    "model": {**item.model.as_record(), "model_hash": model_hash(item.model)},
                    "training_manifest": item.manifest,
                }
                for item in models
            ],
            "validation_diagnostics": self.validation_diagnostics(variant, predictions),
            "profiles": profiles,
        }

    # -- diagnostics --------------------------------------------------------------

    def validation_diagnostics(
        self, variant: str, predictions: dict[int, tuple[float, int]]
    ) -> dict[str, Any]:
        """Out-of-sample prediction quality against the isolated label, per fold."""
        per_fold = []
        pooled_pred: list[float] = []
        pooled_label: list[float] = []
        for fold in self.protocol["folds"]:
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            values: list[float] = []
            paired: list[tuple[float, float]] = []
            for signal_us in range(start, end + 1, HOUR_US):
                source = predictions.get(signal_us)
                row = self.row(signal_us)
                if source is None or row is None:
                    continue
                values.append(source[0])
                label = self.label(row)
                if label.status == "VALID" and label.net_r is not None:
                    paired.append((source[0], label.net_r))
            correlation = (
                float(np.corrcoef([p for p, _ in paired], [x for _, x in paired])[0, 1])
                if len(paired) > 1
                else None
            )
            pooled_pred.extend(p for p, _ in paired)
            pooled_label.extend(x for _, x in paired)
            times = np.asarray(
                [
                    signal_us
                    for signal_us in range(start, end + 1, HOUR_US)
                    if signal_us in predictions and self.row(signal_us) is not None
                ],
                dtype="<i8",
            )
            per_fold.append(
                {
                    "fold_id": fold["fold_id"],
                    "validation_eligible_count": len(values),
                    "prediction_positive_count": int(sum(1 for value in values if value > 0.0)),
                    "isolated_label_valid_count": len(paired),
                    "prediction_label_pearson": correlation,
                    "mean_prediction": float(np.mean(values)) if values else None,
                    "prediction_hash": prediction_hash(times, np.asarray(values, dtype="<f8")),
                }
            )
        pooled = (
            float(np.corrcoef(pooled_pred, pooled_label)[0, 1]) if len(pooled_pred) > 1 else None
        )
        return {
            "variant": variant,
            "per_fold": per_fold,
            "pooled_prediction_label_pearson": pooled,
            "pooled_paired_count": len(pooled_pred),
        }


def parquet_rows(profile_result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "variant": trade["record"]["strategy_reference"].split(":")[-1],
            "profile": profile_result["profile"],
            "fold_id": trade["fold_id"],
            "signal_us": trade["signal_us"],
            "prediction_signal_us": trade["prediction_signal_us"],
            "model_effective_us": trade["model_effective_us"],
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
    "HISTORY_START",
    "PURGE_US",
    "STRATEGY_VERSION",
    "TRIAL_SCHEMA",
    "AdaptiveEwlsLab",
    "CombinedRow",
    "MonthlyModel",
    "WP011LabError",
    "parquet_rows",
    "trade_at",
]
