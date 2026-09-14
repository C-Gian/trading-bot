"""WP-017 CFTC leveraged-positioning HGBR and matched internal control laboratory.

This laboratory binds RESEARCH_RUNTIME_V2_BATCH explicitly.  Frozen WP-014--WP-016
labs keep their original V1 execution paths; nothing here changes them.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

import numpy as np
import pyarrow as pa

from .cftc import FEATURE, CFTCContextSource, CFTCDataError
from .evaluation_protocol import HOUR_US, summarize_trades, utc_us
from .runtime_v2 import (
    RUNTIME_VERSION,
    FoldPredictionInput,
    OrderedPredictions,
    PredictionView,
    StageTimer,
    build_profile_prediction_views,
    predict_folds,
)
from .supervised import FULL_FEATURES, IsolatedLabel, SupervisedRow, label_hash, vector_hash
from .wp014_lab import PURGE_US, FoldModel, ShallowInternalLab, trade_at
from .wp015_model import FittedFundingHGBR, fit_hgbr

PRIMARY_VARIANT = "INTERNAL_PLUS_CFTC_LEVERAGED_NET_HGBR"
CONTROL_VARIANT = "INTERNAL_HGBR_MATCHED_CFTC"
VARIANTS = (PRIMARY_VARIANT, CONTROL_VARIANT)
CONTROL_FEATURES = FULL_FEATURES
PRIMARY_FEATURES = (*FULL_FEATURES, FEATURE)
PROFILES = ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")
STRATEGY_VERSION = "SHALLOW_INTERNAL_HGBR_V1"

TRIAL_SCHEMA = pa.schema(
    [
        ("variant", pa.string(), False),
        ("profile", pa.string(), False),
        ("fold_id", pa.string(), False),
        ("signal_us", pa.int64(), False),
        ("prediction_signal_us", pa.int64(), False),
        ("predicted_default_net_r", pa.float64(), False),
        ("cftc_report_date", pa.date32(), False),
        ("cftc_availability_us", pa.int64(), False),
        ("cftc_leveraged_net_oi_share", pa.float64(), False),
        ("status", pa.string(), False),
        ("reason", pa.string(), False),
        ("net_r", pa.float64()),
        ("gross_r", pa.float64()),
        ("exit_us", pa.int64()),
    ]
)
PREDICTION_SCHEMA = pa.schema(
    [
        ("variant", pa.string(), False),
        ("fold_id", pa.string(), False),
        ("signal_us", pa.int64(), False),
        ("cftc_report_date", pa.date32(), False),
        ("cftc_availability_us", pa.int64(), False),
        ("cftc_leveraged_net_oi_share", pa.float64(), False),
        ("predicted_default_net_r", pa.float64(), False),
    ]
)


class WP017LabError(ValueError):
    """WP-017 eligibility, training, or frozen feature order was violated."""


def features_for(variant: str) -> tuple[str, ...]:
    if variant == PRIMARY_VARIANT:
        return PRIMARY_FEATURES
    if variant == CONTROL_VARIANT:
        return CONTROL_FEATURES
    raise WP017LabError("undeclared WP-017 configuration")


class CFTCPositioningLab(ShallowInternalLab):
    """One CFTC-available universe shared by the primary and its matched control."""

    dependencies: list[dict[str, str]]

    def __init__(
        self,
        inputs: Any,
        features: Any,
        cftc: CFTCContextSource,
        walk_forward: dict[str, Any],
        timer: StageTimer | None = None,
    ):
        super().__init__(inputs, features, walk_forward)
        self.cftc = cftc
        self.cftc_values: dict[int, tuple[int, date, float]] = {}
        self.timer = timer if timer is not None else StageTimer()
        self.runtime_version = RUNTIME_VERSION

    def row(self, signal_us: int) -> SupervisedRow | None:
        row = super().row(signal_us)
        if row is None:
            return None
        try:
            available_us, report_date, value = self.cftc.at(signal_us)
        except CFTCDataError:
            self.exclusions["cftc_unavailable"] += 1
            self._rows[signal_us] = None
            return None
        if available_us > signal_us:
            raise WP017LabError("CFTC report is not legally available at the signal timestamp")
        self.cftc_values[signal_us] = (available_us, report_date, value)
        return row

    def training_rows(
        self, fold: dict[str, Any]
    ) -> tuple[list[SupervisedRow], list[IsolatedLabel]]:
        rows, labels = super().training_rows(fold)
        if any(self.cftc_values[row.signal_us][0] > row.signal_us for row in rows):
            raise WP017LabError("training CFTC availability leaked")
        return rows, labels

    def values_for(self, variant: str, row: SupervisedRow) -> tuple[float, ...]:
        if variant == PRIMARY_VARIANT:
            return (*row.values, self.cftc_values[row.signal_us][2])
        if variant == CONTROL_VARIANT:
            return row.values
        raise WP017LabError("undeclared WP-017 configuration")

    def fit_fold(self, variant: str, fold: dict[str, Any]) -> FoldModel:
        if variant not in VARIANTS:
            raise WP017LabError("undeclared WP-017 configuration")
        with self.timer.measure("BUILD_FEATURES"):
            rows, labels = self.training_rows(fold)
        if utc_us(fold["validation_start"]) - utc_us(fold["train_end_exclusive"]) != PURGE_US:
            raise WP017LabError("frozen 216h purge boundary changed")
        feature_order = features_for(variant)
        times = np.asarray([row.signal_us for row in rows], dtype=np.int64)
        matrix = np.asarray(
            [self.values_for(variant, row) for row in rows], dtype=np.float64
        ).reshape(len(rows), len(feature_order))
        with self.timer.measure("BUILD_LABELS"):
            target = np.asarray([label.net_r for label in labels], dtype=np.float64)
            outcomes = np.asarray([label.outcome_us for label in labels], dtype=np.int64)
        dependency_hash = hashlib.sha256(
            json.dumps(
                getattr(self, "dependencies", []), sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        matrix_identity = vector_hash(times, matrix, feature_order)
        label_identity = label_hash(times, target, outcomes)
        with self.timer.measure("FIT"):
            model = fit_hgbr(
                matrix,
                target,
                feature_order,
                training_matrix_hash=matrix_identity,
                training_label_hash=label_identity,
                dependency_hash=dependency_hash,
            )
        return FoldModel(
            str(fold["fold_id"]),
            model,  # type: ignore[arg-type]
            {
                "fold_id": fold["fold_id"],
                "variant": variant,
                "feature_order": list(feature_order),
                "input_scaling": "NONE_RAW_GOVERNED_VALUES",
                "runtime_version": RUNTIME_VERSION,
                "fit_rows": len(rows),
                "training_signal_min_us": int(times.min()),
                "training_signal_max_us": int(times.max()),
                "max_training_label_outcome_us": int(outcomes.max()),
                "purge_boundary_exclusive_us": utc_us(fold["train_end_exclusive"]),
                "validation_start_us": utc_us(fold["validation_start"]),
                "training_matrix_logical_sha256": matrix_identity,
                "training_label_logical_sha256": label_identity,
                "cftc_available_at_or_before_signal": True,
                "training_rows_committed": False,
            },
        )

    def validation_signals(self) -> list[tuple[str, tuple[int, ...]]]:
        """Per-fold prediction hours.

        This is computed without reference to any configuration, so the primary and its
        matched control are structurally guaranteed to predict on identical timestamps.
        """
        seen: set[int] = set()
        plan: list[tuple[str, tuple[int, ...]]] = []
        for fold in self.folds:
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            signal_ids: list[int] = []
            for signal_us in range(start - HOUR_US, end + 1, HOUR_US):
                if signal_us in seen or self.row(signal_us) is None:
                    continue
                seen.add(signal_us)
                signal_ids.append(signal_us)
            plan.append((str(fold["fold_id"]), tuple(signal_ids)))
        return plan

    def fold_prediction_inputs(
        self, variant: str, fits: tuple[FoldModel, ...]
    ) -> list[FoldPredictionInput]:
        """One governed validation matrix per fold, in strictly increasing signal order."""
        feature_order = features_for(variant)
        inputs: list[FoldPredictionInput] = []
        for (fold_id, signal_ids), fit in zip(self.validation_signals(), fits, strict=True):
            if fold_id != fit.fold_id:
                raise WP017LabError("fold identity diverged from the governed fit order")
            model = fit.model
            if not isinstance(model, FittedFundingHGBR):
                raise WP017LabError("unexpected WP-017 model type")
            rows = [self.row(signal_us) for signal_us in signal_ids]
            if any(row is None for row in rows):
                raise WP017LabError("governed prediction universe became unavailable")
            inputs.append(
                FoldPredictionInput(
                    fit.fold_id,
                    model,
                    signal_ids,
                    np.asarray(
                        [self.values_for(variant, row) for row in rows if row is not None],
                        dtype=np.float64,
                    ).reshape(len(signal_ids), len(feature_order)),
                )
            )
        return inputs

    def predict(self, variant: str, fits: tuple[FoldModel, ...]) -> OrderedPredictions:  # type: ignore[override]
        with self.timer.measure("PREDICT"):
            return predict_folds(self.fold_prediction_inputs(variant, fits))

    def evaluation_signal_ids(self) -> tuple[int, ...]:
        """Eligible validation hours shared identically by the primary and the control."""
        signals: list[int] = []
        for fold in self.folds:
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start, end + 1, HOUR_US):
                if self.row(signal_us) is None:
                    continue
                if signals and signal_us <= signals[-1]:
                    continue
                signals.append(signal_us)
        return tuple(signals)

    def profile_views(self, predictions: OrderedPredictions) -> dict[str, PredictionView]:
        return dict(build_profile_prediction_views(predictions, self.evaluation_signal_ids()))

    def run_profile(  # type: ignore[override]
        self, variant: str, views: dict[str, PredictionView], profile: str
    ) -> dict[str, Any]:
        if profile not in PROFILES:
            raise WP017LabError("undeclared profile")
        view = views[profile]
        sources = dict(zip(view.signal_ids, view.prediction_signal_ids, strict=True))
        values = dict(zip(view.signal_ids, view.values, strict=True))
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
                prediction = values.get(signal_us)
                if prediction is None or prediction <= 0.0:
                    continue
                positive += 1
                if signal_us < blocked_until:
                    suppressed += 1
                    continue
                trade, blocked_until = trade_at(
                    self.inputs, row, sources[signal_us], prediction, variant, profile
                )
                available_us, report_date, value = self.cftc_values[signal_us]
                trade.update(
                    fold_id=fold["fold_id"],
                    cftc_report_date=report_date,
                    cftc_availability_us=available_us,
                    cftc_leveraged_net_oi_share=value,
                )
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

    def run_configuration(self, variant: str) -> dict[str, Any]:
        if variant not in VARIANTS:
            raise WP017LabError("undeclared WP-017 configuration")
        fits = tuple(self.fit_fold(variant, fold) for fold in self.folds)
        predictions = self.predict(variant, fits)
        with self.timer.measure("PROFILES"):
            views = self.profile_views(predictions)
            profiles = {profile: self.run_profile(variant, views, profile) for profile in PROFILES}
        mapping = predictions.as_mapping()
        prediction_records = []
        for fold in self.folds:
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start, end + 1, HOUR_US):
                prediction = mapping.get(signal_us)
                if prediction is None or self.row(signal_us) is None:
                    continue
                available_us, report_date, value = self.cftc_values[signal_us]
                prediction_records.append(
                    {
                        "variant": variant,
                        "fold_id": str(fold["fold_id"]),
                        "signal_us": signal_us,
                        "cftc_report_date": report_date,
                        "cftc_availability_us": available_us,
                        "cftc_leveraged_net_oi_share": value,
                        "predicted_default_net_r": prediction,
                    }
                )
        return {
            "variant": variant,
            "strategy_version": STRATEGY_VERSION,
            "runtime_version": RUNTIME_VERSION,
            "folds": [
                {
                    "fold_id": fit.fold_id,
                    "model": fit.model.as_record(),
                    "training_manifest": fit.manifest,
                }
                for fit in fits
            ],
            "model_fits": len(fits),
            "prediction_diagnostics": self.prediction_diagnostics(mapping),
            "prediction_records": prediction_records,
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
            "cftc_report_date": trade["cftc_report_date"],
            "cftc_availability_us": trade["cftc_availability_us"],
            "cftc_leveraged_net_oi_share": trade["cftc_leveraged_net_oi_share"],
            "status": trade["status"],
            "reason": trade["reason"],
            "net_r": trade.get("net_r"),
            "gross_r": trade.get("gross_r"),
            "exit_us": trade.get("exit_us"),
        }
        for trade in profile_result["trades"]
    ]


__all__ = [
    "CONTROL_FEATURES",
    "CONTROL_VARIANT",
    "PREDICTION_SCHEMA",
    "PRIMARY_FEATURES",
    "PRIMARY_VARIANT",
    "PROFILES",
    "STRATEGY_VERSION",
    "TRIAL_SCHEMA",
    "VARIANTS",
    "CFTCPositioningLab",
    "WP017LabError",
    "features_for",
    "parquet_rows",
]
