"""Frozen WP-016 attention-context HGBR and matched funding-control laboratory."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
import pyarrow as pa

from .evaluation_protocol import HOUR_US, utc_us
from .supervised import FULL_FEATURES, IsolatedLabel, SupervisedRow, label_hash, vector_hash
from .wikimedia import FEATURE, AttentionContextSource, AttentionValue, WikimediaDataError
from .wp014_lab import PURGE_US, FoldModel
from .wp015_lab import FundingContextLab
from .wp015_model import FittedFundingHGBR, fit_hgbr

PRIMARY_VARIANT = "INTERNAL_FUNDING_PLUS_ATTENTION_HGBR"
CONTROL_VARIANT = "INTERNAL_PLUS_FUNDING_HGBR_MATCHED_ATTENTION"
VARIANTS = (PRIMARY_VARIANT, CONTROL_VARIANT)
FUNDING_FEATURES = (*FULL_FEATURES, "LATEST_SETTLED_FUNDING_RATE")
PRIMARY_FEATURES = (*FUNDING_FEATURES, FEATURE)
TRIAL_SCHEMA = pa.schema(
    [
        ("variant", pa.string(), False),
        ("profile", pa.string(), False),
        ("fold_id", pa.string(), False),
        ("signal_us", pa.int64(), False),
        ("prediction_signal_us", pa.int64(), False),
        ("predicted_default_net_r", pa.float64(), False),
        ("funding_rate", pa.float64(), False),
        ("attention_observation_us", pa.int64(), False),
        ("attention_availability_us", pa.int64(), False),
        ("attention_shock", pa.float64(), False),
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
        ("attention_observation_us", pa.int64(), False),
        ("attention_availability_us", pa.int64(), False),
        ("attention_shock", pa.float64(), False),
        ("predicted_default_net_r", pa.float64(), False),
    ]
)


class WP016LabError(ValueError):
    """WP-016 eligibility, training, or frozen feature order was violated."""


class AttentionContextLab(FundingContextLab):
    def __init__(
        self,
        inputs: Any,
        features: Any,
        funding: Any,
        attention: AttentionContextSource,
        walk_forward: dict[str, Any],
    ):
        super().__init__(inputs, features, funding, walk_forward)
        self.attention = attention
        self.attention_values: dict[int, AttentionValue] = {}

    def row(self, signal_us: int) -> SupervisedRow | None:
        row = super().row(signal_us)
        if row is None:
            return None
        try:
            value = self.attention.at(signal_us)
        except WikimediaDataError:
            self.exclusions["attention_unavailable"] += 1
            self._rows[signal_us] = None
            return None
        if value.availability_us > signal_us:
            raise WP016LabError("attention observation is not legally available")
        self.attention_values[signal_us] = value
        return row

    def training_rows(
        self, fold: dict[str, Any]
    ) -> tuple[list[SupervisedRow], list[IsolatedLabel]]:
        rows, labels = super().training_rows(fold)
        if any(
            self.attention_values[row.signal_us].availability_us > row.signal_us for row in rows
        ):
            raise WP016LabError("training attention availability leaked")
        return rows, labels

    def fit_fold(self, variant: str, fold: dict[str, Any]) -> FoldModel:
        if variant not in VARIANTS:
            raise WP016LabError("undeclared WP-016 configuration")
        rows, labels = self.training_rows(fold)
        if utc_us(fold["validation_start"]) - utc_us(fold["train_end_exclusive"]) != PURGE_US:
            raise WP016LabError("frozen 216h purge boundary changed")
        features = PRIMARY_FEATURES if variant == PRIMARY_VARIANT else FUNDING_FEATURES
        values = []
        for row in rows:
            funding_rate = self.funding_values[row.signal_us][1]
            base = (*row.values, funding_rate)
            values.append(
                (*base, self.attention_values[row.signal_us].shock)
                if variant == PRIMARY_VARIANT
                else base
            )
        times = np.asarray([row.signal_us for row in rows], dtype=np.int64)
        matrix = np.asarray(values, dtype=np.float64)
        target = np.asarray([label.net_r for label in labels], dtype=np.float64)
        outcomes = np.asarray([label.outcome_us for label in labels], dtype=np.int64)
        dependency_hash = hashlib.sha256(
            json.dumps(
                getattr(self, "dependencies", []), sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        matrix_identity = vector_hash(times, matrix, features)
        label_identity = label_hash(times, target, outcomes)
        model = fit_hgbr(
            matrix,
            target,
            features,
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
                "feature_order": list(features),
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
                "attention_available_at_or_before_signal": True,
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
                raise WP016LabError("unexpected WP-016 model type")
            for signal_us in range(start - HOUR_US, end + 1, HOUR_US):
                if signal_us in predictions:
                    continue
                row = self.row(signal_us)
                if row is None:
                    continue
                base = (*row.values, self.funding_values[signal_us][1])
                values = (
                    (*base, self.attention_values[signal_us].shock)
                    if len(model.feature_order) == len(PRIMARY_FEATURES)
                    else base
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
            value = self.attention_values[trade["signal_us"]]
            trade.update(
                attention_observation_us=value.observation_us,
                attention_availability_us=value.availability_us,
                attention_shock=value.shock,
            )
        return result

    def run_configuration(self, variant: str) -> dict[str, Any]:
        if variant not in VARIANTS:
            raise WP016LabError("undeclared WP-016 configuration")
        fits = tuple(self.fit_fold(variant, fold) for fold in self.folds)
        predictions = self.predict(fits)
        profiles = {
            profile: self.run_profile(variant, predictions, profile)
            for profile in ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")
        }
        prediction_records = []
        for fold in self.folds:
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            for signal_us in range(start, end + 1, HOUR_US):
                prediction = predictions.get(signal_us)
                if prediction is None:
                    continue
                attention = self.attention_values[signal_us]
                funding_time, funding_rate = self.funding_values[signal_us]
                prediction_records.append(
                    {
                        "variant": variant,
                        "fold_id": str(fold["fold_id"]),
                        "signal_us": signal_us,
                        "funding_time_us": funding_time,
                        "funding_rate": funding_rate,
                        "attention_observation_us": attention.observation_us,
                        "attention_availability_us": attention.availability_us,
                        "attention_shock": attention.shock,
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
            "attention_observation_us": trade["attention_observation_us"],
            "attention_availability_us": trade["attention_availability_us"],
            "attention_shock": trade["attention_shock"],
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
    "FUNDING_FEATURES",
    "PREDICTION_SCHEMA",
    "PRIMARY_FEATURES",
    "PRIMARY_VARIANT",
    "TRIAL_SCHEMA",
    "VARIANTS",
    "AttentionContextLab",
    "WP016LabError",
    "parquet_rows",
]
