"""Frozen WP-015 funding-context HGBR and matched internal HGBR laboratory."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
import pyarrow as pa

from .evaluation_protocol import HOUR_US, utc_us
from .funding import FEATURE, FundingContextSource, FundingDataError
from .supervised import FULL_FEATURES, IsolatedLabel, SupervisedRow, label_hash, vector_hash
from .wp014_lab import PURGE_US, FoldModel, ShallowInternalLab
from .wp015_model import FittedFundingHGBR, fit_hgbr

PRIMARY_VARIANT = "INTERNAL_PLUS_FUNDING_HGBR"
CONTROL_VARIANT = "INTERNAL_HGBR_MATCHED_FUNDING"
VARIANTS = (PRIMARY_VARIANT, CONTROL_VARIANT)
PRIMARY_FEATURES = (*FULL_FEATURES, FEATURE)
TRIAL_SCHEMA = pa.schema(
    [
        ("variant", pa.string(), False),
        ("profile", pa.string(), False),
        ("fold_id", pa.string(), False),
        ("signal_us", pa.int64(), False),
        ("prediction_signal_us", pa.int64(), False),
        ("predicted_default_net_r", pa.float64(), False),
        ("funding_rate", pa.float64(), False),
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
        ("funding_time_us", pa.int64(), False),
        ("funding_rate", pa.float64(), False),
        ("predicted_default_net_r", pa.float64(), False),
    ]
)


class WP015LabError(ValueError):
    """WP-015 frozen eligibility, training, or model declaration was violated."""


class FundingContextLab(ShallowInternalLab):
    def __init__(
        self,
        inputs: Any,
        features: Any,
        funding: FundingContextSource,
        walk_forward: dict[str, Any],
    ):
        super().__init__(inputs, features, walk_forward)
        self.funding = funding
        self.funding_values: dict[int, tuple[int, float]] = {}

    def row(self, signal_us: int) -> SupervisedRow | None:
        row = super().row(signal_us)
        if row is None:
            return None
        try:
            settled = self.funding.at(signal_us)
        except FundingDataError:
            self.exclusions["funding_unavailable"] += 1
            self._rows[signal_us] = None
            return None
        if settled[0] >= signal_us:
            raise WP015LabError("fundingTime is not strictly earlier than signalTime")
        self.funding_values[signal_us] = settled
        return row

    def training_rows(
        self, fold: dict[str, Any]
    ) -> tuple[list[SupervisedRow], list[IsolatedLabel]]:
        rows, labels = super().training_rows(fold)
        if any(self.funding_values[row.signal_us][0] >= row.signal_us for row in rows):
            raise WP015LabError("training funding availability leaked")
        return rows, labels

    def fit_fold(self, variant: str, fold: dict[str, Any]) -> Any:
        rows, labels = self.training_rows(fold)
        if utc_us(fold["validation_start"]) - utc_us(fold["train_end_exclusive"]) != PURGE_US:
            raise WP015LabError("frozen 216h purge boundary changed")
        feature_order = PRIMARY_FEATURES if variant == PRIMARY_VARIANT else FULL_FEATURES
        values = [
            (*row.values, self.funding_values[row.signal_us][1])
            if variant == PRIMARY_VARIANT
            else row.values
            for row in rows
        ]
        times = np.asarray([row.signal_us for row in rows], dtype=np.int64)
        matrix = np.asarray(values, dtype=np.float64)
        target = np.asarray([label.net_r for label in labels], dtype=np.float64)
        outcomes = np.asarray([label.outcome_us for label in labels], dtype=np.int64)
        dependencies = getattr(self, "dependencies", [])
        dependency_hash = hashlib.sha256(
            json.dumps(dependencies, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        matrix_identity = vector_hash(times, matrix, feature_order)
        label_identity = label_hash(times, target, outcomes)
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
                "fit_rows": len(rows),
                "training_signal_min_us": int(times.min()),
                "training_signal_max_us": int(times.max()),
                "max_training_label_outcome_us": int(outcomes.max()),
                "purge_boundary_exclusive_us": utc_us(fold["train_end_exclusive"]),
                "validation_start_us": utc_us(fold["validation_start"]),
                "training_matrix_logical_sha256": matrix_identity,
                "training_label_logical_sha256": label_identity,
                "funding_time_strictly_before_signal": True,
                "training_rows_committed": False,
            },
        )

    def predict(self, fits: Any) -> dict[int, float]:
        predictions: dict[int, float] = {}
        for fold, fit in zip(self.folds, fits, strict=True):
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            model = fit.model
            if not isinstance(model, FittedFundingHGBR):
                raise WP015LabError("unexpected WP-015 model type")
            for signal_us in range(start - HOUR_US, end + 1, HOUR_US):
                if signal_us in predictions:
                    continue
                row = self.row(signal_us)
                if row is None:
                    continue
                values = (
                    (*row.values, self.funding_values[signal_us][1])
                    if len(model.feature_order) == 9
                    else row.values
                )
                predictions[signal_us] = float(
                    model.predict(np.asarray([values], dtype=np.float64))[0]
                )
        return predictions

    def run_profile(
        self, variant: str, predictions: dict[int, float], profile: str
    ) -> dict[str, Any]:
        result = super().run_profile(variant, predictions, profile)
        for trade in result["trades"]:
            trade["funding_rate"] = self.funding_values[trade["signal_us"]][1]
            trade["funding_time_us"] = self.funding_values[trade["signal_us"]][0]
        return result

    def run_configuration(self, variant: str) -> dict[str, Any]:
        if variant not in VARIANTS:
            raise WP015LabError("undeclared WP-015 configuration")
        fits = tuple(self.fit_fold(variant, fold) for fold in self.folds)
        predictions = self.predict(fits)
        profiles = {
            profile: self.run_profile(variant, predictions, profile)
            for profile in ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")
        }
        prediction_records: list[dict[str, Any]] = []
        positive_funding: list[float] = []
        nonpositive_funding: list[float] = []
        for fold in self.folds:
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start, end + 1, HOUR_US):
                prediction = predictions.get(signal_us)
                settled = self.funding_values.get(signal_us)
                if prediction is None or settled is None:
                    continue
                rate = settled[1]
                (positive_funding if prediction > 0.0 else nonpositive_funding).append(rate)
                prediction_records.append(
                    {
                        "variant": variant,
                        "fold_id": str(fold["fold_id"]),
                        "signal_us": signal_us,
                        "funding_time_us": settled[0],
                        "funding_rate": rate,
                        "predicted_default_net_r": prediction,
                    }
                )
        return {
            "variant": variant,
            "strategy_version": "SHALLOW_INTERNAL_HGBR_V1",
            "folds": [
                {
                    "fold_id": fit.fold_id,
                    "model": fit.model.as_record(),
                    "training_manifest": fit.manifest,
                }
                for fit in fits
            ],
            "model_fits": len(fits),
            "prediction_diagnostics": self.prediction_diagnostics(predictions),
            "funding_prediction_diagnostics": {
                "mean_funding_positive_prediction_hours": (
                    float(np.mean(positive_funding)) if positive_funding else None
                ),
                "mean_funding_nonpositive_prediction_hours": (
                    float(np.mean(nonpositive_funding)) if nonpositive_funding else None
                ),
            },
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
            "funding_rate": trade["funding_rate"],
            "status": trade["status"],
            "reason": trade["reason"],
            "net_r": trade.get("net_r"),
            "gross_r": trade.get("gross_r"),
            "exit_us": trade.get("exit_us"),
        }
        for trade in profile_result["trades"]
    ]


__all__ = [
    "CONTROL_VARIANT",
    "PREDICTION_SCHEMA",
    "PRIMARY_FEATURES",
    "PRIMARY_VARIANT",
    "TRIAL_SCHEMA",
    "VARIANTS",
    "FundingContextLab",
    "WP015LabError",
    "parquet_rows",
]
