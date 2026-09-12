"""WP-012 regime-conditioned walk-forward: two experts gated by point-in-time NFCI.

`REGIME_CONDITIONED_LINEAR_EXPERTS_V1`. Two independent deterministic OLS experts are
fitted once per annual fold, one on historical `NORMAL_OR_LOOSE` rows and one on
historical `TIGHT` rows. At a validation hour the point-in-time regime selects exactly
one expert; there is no interpolation, no probability weighting and no shared
coefficient.

The only mechanism under test is regime conditioning. The eight internal features and
their semantics are the frozen WP-008 set, no macro value ever enters an expert's feature
matrix, and NFCI appears solely as the gate.

A regime expert that is not deterministically feasible for a fold - too few training
rows, a degenerate feature, or a rank deficiency - is refused. The hours it would have
covered emit no prediction and are counted. Regimes are never merged to rescue a fold.
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
from .linear_model import FittedLinearModel, LinearModelError, fit_ols, model_hash
from .regime import REGIMES, RegimeSource
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
from .wp012 import GLOBAL_KEY, PRIMARY_VARIANT, VARIANTS, dependency_manifest

STRATEGY_VERSION = "REGIME_CONDITIONED_LINEAR_EXPERTS_V1"
PURGE_US = 216 * HOUR_US
MINUTE_US = 60_000_000

TRIAL_SCHEMA = pa.schema(
    [
        ("variant", pa.string(), False),
        ("profile", pa.string(), False),
        ("fold_id", pa.string(), False),
        ("regime", pa.string(), False),
        ("expert", pa.string(), False),
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


class WP012LabError(SupervisedDataError):
    """The regime-conditioned substrate violated its frozen declaration."""


@dataclass(frozen=True)
class RegimeRow:
    """One eligible hourly signal row: internal features plus its gating regime."""

    signal_us: int
    reference: float
    regime: str
    nfci: float
    values: tuple[float, ...]


@dataclass(frozen=True)
class FoldExperts:
    fold_id: str
    experts: dict[str, FittedLinearModel]
    manifests: dict[str, dict[str, Any]]
    infeasible: dict[str, str]


def trade_at(
    inputs: ResearchInputs,
    row: RegimeRow,
    prediction_signal_us: int,
    expert: str,
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
        "predicted_default_net_r": prediction,
        "reference": row.reference,
        "regime_label": row.regime,
        "expert": expert,
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


class RegimeExpertLab:
    """Builds the eligible universe once, then fits experts per fold and per regime."""

    def __init__(
        self,
        inputs: ResearchInputs,
        internal: SupervisedFeatureSource,
        regimes: RegimeSource,
        walk_forward: dict[str, Any],
    ):
        self.inputs = inputs
        self.internal = internal
        self.regimes = regimes
        self.walk_forward = walk_forward
        self.folds = walk_forward["folds"]
        self._rows: dict[int, RegimeRow | None] = {}
        self._labels: dict[int, IsolatedLabel] = {}
        self.exclusions: Counter[str] = Counter()

    # -- universe -----------------------------------------------------------------

    def row(self, signal_us: int) -> RegimeRow | None:
        """An hour is eligible only with both internal features and a regime."""
        if signal_us in self._rows:
            return self._rows[signal_us]
        try:
            internal = self.internal.at(signal_us)
        except SupervisedDataError:
            self.exclusions["internal_feature_ineligible"] += 1
            self._rows[signal_us] = None
            return None
        reading = self.regimes.at(signal_us)
        if reading is None:
            self.exclusions["regime_unavailable"] += 1
            self._rows[signal_us] = None
            return None
        row = RegimeRow(
            signal_us, internal.reference, reading.regime, reading.nfci, internal.values
        )
        if len(row.values) != len(FULL_FEATURES):
            raise WP012LabError("expert feature row is not the frozen eight-value vector")
        self._rows[signal_us] = row
        return row

    def label(self, row: RegimeRow) -> IsolatedLabel:
        if row.signal_us not in self._labels:
            proxy = SupervisedRow(row.signal_us, row.reference, 0, 0, row.signal_us, row.values)
            self._labels[row.signal_us] = isolated_label(self.inputs, proxy)
        return self._labels[row.signal_us]

    # -- fitting ------------------------------------------------------------------

    def _training_rows(self, fold: dict[str, Any]) -> tuple[list[RegimeRow], list[IsolatedLabel]]:
        """Every eligible row whose signal and label outcome precede the purge boundary."""
        train_start = utc_us(fold["train_start"])
        boundary = utc_us(fold["train_end_exclusive"])
        if utc_us(fold["validation_start"]) - boundary != PURGE_US:
            raise WP012LabError("frozen 216h training purge boundary changed")
        rows: list[RegimeRow] = []
        labels: list[IsolatedLabel] = []
        for signal_us in range(train_start, boundary, HOUR_US):
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

    def _fit(
        self,
        rows: list[RegimeRow],
        labels: list[IsolatedLabel],
        dependency_hash: str,
    ) -> FittedLinearModel:
        times = np.asarray([row.signal_us for row in rows], dtype=np.int64)
        matrix = np.asarray([row.values for row in rows], dtype=np.float64)
        target = np.asarray([label.net_r for label in labels], dtype=np.float64)
        outcomes = np.asarray([label.outcome_us for label in labels], dtype=np.int64)
        return fit_ols(
            matrix,
            target,
            FULL_FEATURES,
            training_matrix_hash=vector_hash(times, matrix, FULL_FEATURES),
            training_label_hash=label_hash(times, target, outcomes),
            dependency_hash=dependency_hash,
        )

    def fit_fold(self, variant: str, fold: dict[str, Any]) -> FoldExperts:
        """One expert per regime for the primary; one global expert for the control."""
        rows, labels = self._training_rows(fold)
        if not rows:
            raise WP012LabError("fold has no eligible training rows")
        dependencies = dependency_manifest()
        dependency_hash = hashlib.sha256(
            json.dumps(dependencies, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        groups: dict[str, tuple[list[RegimeRow], list[IsolatedLabel]]]
        if variant == PRIMARY_VARIANT:
            groups = {
                regime: (
                    [row for row in rows if row.regime == regime],
                    [
                        label
                        for row, label in zip(rows, labels, strict=True)
                        if row.regime == regime
                    ],
                )
                for regime in REGIMES
            }
        else:
            groups = {GLOBAL_KEY: (rows, labels)}

        experts: dict[str, FittedLinearModel] = {}
        manifests: dict[str, dict[str, Any]] = {}
        infeasible: dict[str, str] = {}
        for key, (group_rows, group_labels) in groups.items():
            if not group_rows:
                infeasible[key] = "no eligible training rows for this regime"
                continue
            try:
                model = self._fit(group_rows, group_labels, dependency_hash)
            except LinearModelError as exc:
                # The deterministic feasibility rule stands: refuse, record, emit nothing.
                infeasible[key] = str(exc)
                continue
            experts[key] = model
            times = [row.signal_us for row in group_rows]
            manifests[key] = {
                "fold_id": fold["fold_id"],
                "variant": variant,
                "expert": key,
                "fit_rows": len(group_rows),
                "training_signal_min_us": min(times),
                "training_signal_max_us": max(times),
                "max_training_label_outcome_us": max(item.outcome_us for item in group_labels),
                "purge_boundary_exclusive_us": utc_us(fold["train_end_exclusive"]),
                "validation_start_us": utc_us(fold["validation_start"]),
                "condition_number": model.condition_number,
                "rank": model.rank,
                "training_matrix_logical_sha256": model.training_matrix_hash,
                "training_label_logical_sha256": model.training_label_hash,
                "training_rows_committed": False,
            }
        return FoldExperts(fold["fold_id"], experts, manifests, infeasible)

    def fit_configuration(self, variant: str) -> tuple[FoldExperts, ...]:
        if variant not in VARIANTS:
            raise WP012LabError("undeclared WP-012 configuration")
        return tuple(self.fit_fold(variant, fold) for fold in self.folds)

    # -- prediction ---------------------------------------------------------------

    @staticmethod
    def _expert_key(variant: str, regime: str) -> str:
        return regime if variant == PRIMARY_VARIANT else GLOBAL_KEY

    def predict(
        self, variant: str, fits: tuple[FoldExperts, ...]
    ) -> tuple[dict[int, tuple[float, str, str]], Counter[str]]:
        """Prediction, gating regime and selected expert for each covered hour."""
        predictions: dict[int, tuple[float, str, str]] = {}
        uncovered: Counter[str] = Counter()
        for fold, fit in zip(self.folds, fits, strict=True):
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            # One hour earlier so DELAY_1H reuses an already generated prediction.
            for signal_us in range(start - HOUR_US, end + 1, HOUR_US):
                if signal_us in predictions:
                    continue
                row = self.row(signal_us)
                if row is None:
                    continue
                key = self._expert_key(variant, row.regime)
                model = fit.experts.get(key)
                if model is None:
                    uncovered[f"{fold['fold_id']}:{key}"] += 1
                    continue
                vector = np.asarray([row.values], dtype=np.float64)
                predictions[signal_us] = (float(model.predict(vector)[0]), row.regime, key)
        return predictions, uncovered

    # -- execution ----------------------------------------------------------------

    def run_profile(
        self,
        variant: str,
        predictions: dict[int, tuple[float, str, str]],
        profile: str,
    ) -> dict[str, Any]:
        if profile not in PROFILES:
            raise WP012LabError("undeclared robustness profile")
        trades: list[dict[str, Any]] = []
        diagnostics = []
        for fold in self.folds:
            start = utc_us(fold["validation_start"])
            end = utc_us(fold["last_signal_inclusive"])
            blocked_until = -1
            suppressed = 0
            emitted = 0
            eligible = 0
            uncovered = 0
            for signal_us in range(start, end + 1, HOUR_US):
                row = self.row(signal_us)
                if row is None:
                    continue
                eligible += 1
                source_us = signal_us - HOUR_US if profile == "DELAY_1H" else signal_us
                source = predictions.get(source_us)
                if source is None:
                    uncovered += 1
                    continue
                prediction, _regime, expert = source
                if prediction <= 0.0:
                    continue
                emitted += 1
                if signal_us < blocked_until:
                    suppressed += 1
                    continue
                trade, blocked_until = trade_at(
                    self.inputs, row, source_us, expert, prediction, variant, profile
                )
                trade["fold_id"] = fold["fold_id"]
                trades.append(trade)
            diagnostics.append(
                {
                    "fold_id": fold["fold_id"],
                    "validation_eligible_count": eligible,
                    "uncovered_hour_count": uncovered,
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
            "fold_diagnostics": diagnostics,
            "summary": summarize_trades(trades, self.walk_forward, allow_unclassified_regime=True),
        }

    def run_configuration(self, variant: str) -> dict[str, Any]:
        fits = self.fit_configuration(variant)
        predictions, uncovered = self.predict(variant, fits)
        profiles = {
            profile: self.run_profile(variant, predictions, profile) for profile in PROFILES
        }
        return {
            "variant": variant,
            "strategy_version": STRATEGY_VERSION,
            "folds": [
                {
                    "fold_id": fit.fold_id,
                    "experts": {
                        key: {**model.as_record(), "model_hash": model_hash(model)}
                        for key, model in fit.experts.items()
                    },
                    "training_manifests": fit.manifests,
                    "infeasible_experts": fit.infeasible,
                }
                for fit in fits
            ],
            "expert_fits": sum(len(fit.experts) for fit in fits),
            "infeasible_expert_count": sum(len(fit.infeasible) for fit in fits),
            "uncovered_hours": dict(sorted(uncovered.items())),
            "regime_diagnostics": self.regime_diagnostics(variant, predictions, profiles),
            "profiles": profiles,
        }

    # -- diagnostics --------------------------------------------------------------

    def regime_diagnostics(
        self,
        variant: str,
        predictions: dict[int, tuple[float, str, str]],
        profiles: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Per-regime eligibility, prediction and realised outcome, plus OOS correlation."""
        per_regime: dict[str, dict[str, Any]] = {}
        default_trades = profiles["DEFAULT"]["trades"]
        for regime in REGIMES:
            eligible = 0
            positive = 0
            paired: list[tuple[float, float]] = []
            for fold in self.folds:
                start = utc_us(fold["validation_start"])
                end = utc_us(fold["last_signal_inclusive"])
                for signal_us in range(start, end + 1, HOUR_US):
                    row = self.row(signal_us)
                    if row is None or row.regime != regime:
                        continue
                    eligible += 1
                    source = predictions.get(signal_us)
                    if source is None:
                        continue
                    if source[0] > 0.0:
                        positive += 1
                    label = self.label(row)
                    if label.status == "VALID" and label.net_r is not None:
                        paired.append((source[0], label.net_r))
            selected = [
                trade
                for trade in default_trades
                if trade["regime_label"] == regime and trade["status"] == "VALID"
            ]
            returns = [trade["net_r"] for trade in selected]
            folds = Counter(trade["fold_id"] for trade in selected)
            per_regime[regime] = {
                "eligible_validation_hours": eligible,
                "prediction_positive_hours": positive,
                "executed_trades": len(selected),
                "mean_net_r": float(np.mean(returns)) if returns else None,
                "cumulative_net_r": float(np.sum(returns)) if returns else None,
                "fold_distribution": dict(sorted(folds.items())),
                "prediction_label_pearson": (
                    float(np.corrcoef([p for p, _ in paired], [x for _, x in paired])[0, 1])
                    if len(paired) > 1
                    else None
                ),
                "isolated_label_valid_count": len(paired),
            }
        pooled = [
            (predictions[signal_us][0], self.label(row).net_r)
            for fold in self.folds
            for signal_us in range(
                utc_us(fold["validation_start"]), utc_us(fold["last_signal_inclusive"]) + 1, HOUR_US
            )
            if (row := self.row(signal_us)) is not None
            and signal_us in predictions
            and self.label(row).status == "VALID"
            and self.label(row).net_r is not None
        ]
        return {
            "variant": variant,
            "per_regime": per_regime,
            "pooled_prediction_label_pearson": (
                float(np.corrcoef([p for p, _ in pooled], [x for _, x in pooled])[0, 1])
                if len(pooled) > 1
                else None
            ),
            "pooled_paired_count": len(pooled),
        }


def parquet_rows(profile_result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "variant": profile_result["variant"],
            "profile": profile_result["profile"],
            "fold_id": trade["fold_id"],
            "regime": trade["regime_label"],
            "expert": trade["expert"],
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
    "FoldExperts",
    "RegimeExpertLab",
    "RegimeRow",
    "WP012LabError",
    "parquet_rows",
    "trade_at",
]
