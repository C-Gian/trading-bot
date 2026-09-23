"""`PREDICTIVE_V2_PUBLIC_TAKER_FLOW_HORIZON_FOUNDATION_V1`, exactly as frozen.

Protocol: `research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md`.

Decision instants are the UTC hour boundaries `T` of the development window. At `T` only 1m
bars fully completed by `T` are read: the feature window is the 60 minutes with open times
`T-60m .. T-1m`, and the decision price `close[T]` is the spot close of the minute
`[T-1m, T)`. For horizon `H`, `close[T+H]` is the spot close of the minute `[T+H-1m, T+H)`,
and `r_H = log(close[T+H] / close[T])`: UP if > 0, DOWN if < 0, NEUTRAL if exactly zero.
NEUTRAL and label-unavailable instants are excluded from scoring and counted.

Per market, over the 60-minute window:

    buy_quote = sum(taker_buy_quote_volume)
    total_quote = sum(quote_asset_volume)
    imbalance = (2 * buy_quote - total_quote) / total_quote

The three features, in order, are the spot imbalance, the USD-M imbalance and their
difference. The vector is unavailable if any required minute in either market is absent,
duplicated, timestamp-invalid, incomplete or non-finite, or if a total_quote is <= 0 or
non-finite.

Outer evaluation folds are the calendar years 2021..2024. A fold trains only on decision
instants `T` whose label end `T+H` is at or before the fold start (horizon-specific purge).
Inside the outer-training set the first `floor(0.8 n)` rows (chronological) are the base-fit
candidates and the remaining rows are the calibration set; the calibration embargo of `2H`
drops every base candidate with `T + 2H > T_first_calibration`. The base model is a
StandardScaler + fixed L2 logistic regression; the raw decision score on the calibration set
fits an unpenalized one-dimensional Platt logistic. Every feature-valid outer row receives
the calibrated `p_up`.

Primary effect per horizon: pooled `CONTROL_BRIER - MODEL_BRIER`, the control being the
constant fold `TRAINING_UP_BASE_RATE` (UP share of that fold's outer-training rows), scored
on exactly the same rows. Its uncertainty is a paired fold-stratified moving-block bootstrap
laid on each fold's hourly timeline, with blocks of `max(48h, 2H)` that never cross a fold
boundary, 10,000 replicates and a Bonferroni central interval over the three horizons.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .paired_inference import block_sums
from .taker_flow_source import (
    MANIFEST_PATH,
    MARKETS,
    PROTOCOL_PATH,
    SPOT,
    USDM,
    VALID,
    WINDOW_MINUTES,
    WINDOW_START_MS,
    MinuteBook,
    load_minute_books,
)

ROOT = Path(__file__).resolve().parents[3]

VERSION = "PREDICTIVE_V2_PUBLIC_TAKER_FLOW_HORIZON_FOUNDATION_V1"
EXPERIMENT_ID = "EXP-PRED-V2-005-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION"
RESULT_PATH = f"research/experiments/{EXPERIMENT_ID}/result.json"
REPORT_MARKDOWN_PATH = "reports/research/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md"
RESULT_PATHS = (RESULT_PATH, REPORT_MARKDOWN_PATH)
IMPLEMENTATION_PATHS = (
    "backend/app/predictive/taker_flow_source.py",
    "backend/app/predictive/taker_flow_foundation.py",
    "backend/app/predictive/paired_inference.py",
    "scripts/acquire_public_taker_flow.py",
    "scripts/run_public_taker_flow_foundation.py",
)

HOUR_SECONDS = 3600
MINUTES_PER_HOUR = 60
WINDOW_START_SECONDS = WINDOW_START_MS // 1000
WINDOW_HOURS = WINDOW_MINUTES // MINUTES_PER_HOUR

FEATURE_NAMES = (
    "SPOT_TAKER_IMBALANCE_1H",
    "UM_TAKER_IMBALANCE_1H",
    "SPOT_MINUS_UM_TAKER_IMBALANCE_1H",
)
HORIZONS_HOURS = (24, 4, 1)  # frozen order: product target first, never score-selected
OUTER_FOLD_YEARS = (2021, 2022, 2023, 2024)

BASE_FIT_FRACTION = 0.8
CALIBRATION_EMBARGO_MULTIPLE = 2
LOGISTIC_PARAMETERS = {
    "penalty": "l2",
    "C": 1.0,
    "fit_intercept": True,
    "solver": "lbfgs",
    "max_iter": 2000,
    "tol": 1e-8,
    "class_weight": None,
}
PLATT_PARAMETERS = {
    "penalty": None,
    "fit_intercept": True,
    "solver": "lbfgs",
    "max_iter": 2000,
    "tol": 1e-8,
    "class_weight": None,
}

BOOTSTRAP_METHOD = "PAIRED_FOLD_STRATIFIED_MOVING_BLOCK_BOOTSTRAP_ON_HOURLY_TIMELINE"
MINIMUM_BLOCK_HOURS = 48
BOOTSTRAP_REPLICATES = 10_000
FAMILY_SEED = 20260923
FAMILYWISE_ALPHA = 0.05
PER_HORIZON_ALPHA = FAMILYWISE_ALPHA / len(HORIZONS_HOURS)
INTERVAL_MASS = 1.0 - PER_HORIZON_ALPHA
REPLICATE_CHUNK = 500

POOLED_COVERAGE_MINIMUM = 0.95
FOLD_COVERAGE_MINIMUM = 0.90
MINIMUM_NON_NEGATIVE_FOLDS = 3
LOG_LOSS_EPSILON = 1e-15
RELIABILITY_BINS = 10

SUPPORTED = "FOUNDATION_SIGNAL_SUPPORTED"
NOT_SUPPORTED = "FOUNDATION_SIGNAL_NOT_SUPPORTED"
SELECTION_OUTCOMES = {
    24: "KEEP_24H_FOR_NEXT_PUBLIC_FLOW_FAMILY",
    4: "FOUNDATION_SUPPORTS_4H_RESEARCH_ONLY",
    1: "FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY",
}
NO_HORIZON_SUPPORTED = "NO_PUBLIC_TAKER_FLOW_HORIZON_SUPPORTED"

# Target codes.
UP_CODE = 1
DOWN_CODE = 0
NEUTRAL_CODE = -1
UNAVAILABLE_CODE = -2


class FoundationError(RuntimeError):
    """The foundation was asked for something the frozen protocol does not allow."""


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def iso(seconds: int) -> str:
    return datetime.fromtimestamp(seconds, UTC).isoformat().replace("+00:00", "Z")


def year_start_seconds(year: int) -> int:
    return int(datetime(year, 1, 1, tzinfo=UTC).timestamp())


# --------------------------------------------------------------------------------------
# Hourly panel: exact frozen features and decision prices.
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HourlyPanel:
    """Row `j` is the decision instant `T_j = window start + (j + 1) hours`."""

    decision_times: Any  # int64 epoch seconds
    features: Any  # float64 (n, 3), NaN where unavailable
    feature_valid: Any  # bool (n,)
    decision_close: Any  # float64 (n,), spot close of the minute ending at T, NaN if unusable


def market_imbalance(book: MinuteBook) -> tuple[Any, Any]:
    """Per decision instant, the 60-minute imbalance and whether it is available."""
    import numpy as np

    status = book.status.reshape(WINDOW_HOURS, MINUTES_PER_HOUR)
    quote = book.quote.reshape(WINDOW_HOURS, MINUTES_PER_HOUR)
    taker = book.taker_quote.reshape(WINDOW_HOURS, MINUTES_PER_HOUR)
    complete = np.all(status == VALID, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        buy_quote = np.where(complete, taker.sum(axis=1), np.nan)
        total_quote = np.where(complete, quote.sum(axis=1), np.nan)
        usable = complete & np.isfinite(total_quote) & np.isfinite(buy_quote) & (total_quote > 0)
        imbalance = np.where(usable, (2.0 * buy_quote - total_quote) / total_quote, np.nan)
    usable &= np.isfinite(imbalance)
    return np.where(usable, imbalance, np.nan), usable


def build_panel(books: Mapping[str, MinuteBook]) -> HourlyPanel:
    import numpy as np

    if set(books) != set(MARKETS):
        raise FoundationError("the panel needs exactly the spot and USD-M minute books")
    spot, spot_ok = market_imbalance(books[SPOT])
    um, um_ok = market_imbalance(books[USDM])
    valid = spot_ok & um_ok
    features = np.column_stack((spot, um, spot - um))
    features[~valid] = np.nan
    valid &= np.all(np.isfinite(features), axis=1)

    last_minute = np.arange(WINDOW_HOURS) * MINUTES_PER_HOUR + (MINUTES_PER_HOUR - 1)
    spot_book = books[SPOT]
    close = spot_book.close[last_minute]
    close_ok = (spot_book.status[last_minute] == VALID) & np.isfinite(close) & (close > 0)
    decision_times = WINDOW_START_SECONDS + (np.arange(WINDOW_HOURS, dtype=np.int64) + 1) * (
        HOUR_SECONDS
    )
    return HourlyPanel(
        decision_times=decision_times,
        features=features,
        feature_valid=valid,
        decision_close=np.where(close_ok, close, np.nan),
    )


def horizon_targets(panel: HourlyPanel, horizon_hours: int) -> tuple[Any, Any]:
    """`(r_H, code)` per decision instant; code is UP/DOWN/NEUTRAL/UNAVAILABLE."""
    import numpy as np

    count = panel.decision_close.shape[0]
    later = np.full(count, np.nan, dtype=np.float64)
    if horizon_hours < count:
        later[: count - horizon_hours] = panel.decision_close[horizon_hours:]
    with np.errstate(invalid="ignore", divide="ignore"):
        returns = np.log(later / panel.decision_close)
    code = np.full(count, UNAVAILABLE_CODE, dtype=np.int8)
    finite = np.isfinite(returns)
    code[finite & (returns > 0)] = UP_CODE
    code[finite & (returns < 0)] = DOWN_CODE
    code[finite & (returns == 0)] = NEUTRAL_CODE
    return np.where(finite, returns, np.nan), code


# --------------------------------------------------------------------------------------
# Folds, purge and the calibration split.
# --------------------------------------------------------------------------------------


def outer_fold_masks(decision_times: Any, horizon_hours: int, year: int) -> tuple[Any, Any]:
    """`(training, evaluation)` instant masks for one annual outer fold, before eligibility.

    Evaluation: `T` inside the calendar year. Training: every earlier `T` whose label end
    `T + H` is at or before the fold start, so no training label reaches into the fold.
    """
    start = year_start_seconds(year)
    end = year_start_seconds(year + 1)
    evaluation = (decision_times >= start) & (decision_times < end)
    training = decision_times + horizon_hours * HOUR_SECONDS <= start
    return training, evaluation


def calibration_split(training_times: Sequence[int], horizon_hours: int) -> tuple[Any, Any]:
    """Chronological 80/20 base/calibration positions with the `2H` calibration embargo."""
    import numpy as np

    times = np.asarray(training_times, dtype=np.int64)
    if times.ndim != 1 or np.any(np.diff(times) <= 0):
        raise FoundationError("training instants must be strictly increasing")
    total = int(times.shape[0])
    boundary = math.floor(BASE_FIT_FRACTION * total)
    if boundary <= 0 or boundary >= total:
        raise FoundationError("the outer-training set is too small to split")
    embargo = CALIBRATION_EMBARGO_MULTIPLE * horizon_hours * HOUR_SECONDS
    first_calibration = int(times[boundary])
    base = np.flatnonzero(times[:boundary] + embargo <= first_calibration)
    calibration = np.arange(boundary, total)
    if base.shape[0] == 0:
        raise FoundationError("the calibration embargo removed every base-fit row")
    return base, calibration


# --------------------------------------------------------------------------------------
# Fixed model.
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FittedModel:
    scaler: Any
    logistic: Any
    platt: Any

    def raw_score(self, features: Any) -> Any:
        return self.logistic.decision_function(self.scaler.transform(features))

    def p_up(self, features: Any) -> Any:
        score = self.raw_score(features).reshape(-1, 1)
        return self.platt.predict_proba(score)[:, 1]

    def describe(self) -> dict[str, Any]:
        return {
            "scaler_mean": [float(value) for value in self.scaler.mean_],
            "scaler_scale": [float(value) for value in self.scaler.scale_],
            "logistic_coefficients": [float(value) for value in self.logistic.coef_[0]],
            "logistic_intercept": float(self.logistic.intercept_[0]),
            "logistic_iterations": int(self.logistic.n_iter_[0]),
            "platt_slope": float(self.platt.coef_[0][0]),
            "platt_intercept": float(self.platt.intercept_[0]),
            "platt_iterations": int(self.platt.n_iter_[0]),
        }


def fit_model(
    base_features: Any, base_up: Any, calibration_features: Any, calibration_up: Any
) -> FittedModel:
    """StandardScaler + fixed L2 logistic on base rows; unpenalized Platt on calibration."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    for name, labels in (("base", base_up), ("calibration", calibration_up)):
        if np.unique(labels).shape[0] != 2:
            raise FoundationError(f"the {name} segment does not contain both classes")
    scaler = StandardScaler().fit(base_features)
    logistic = LogisticRegression(**LOGISTIC_PARAMETERS).fit(
        scaler.transform(base_features), base_up
    )
    score = logistic.decision_function(scaler.transform(calibration_features)).reshape(-1, 1)
    platt = LogisticRegression(**PLATT_PARAMETERS).fit(score, calibration_up)
    return FittedModel(scaler=scaler, logistic=logistic, platt=platt)


# --------------------------------------------------------------------------------------
# Scoring.
# --------------------------------------------------------------------------------------


def brier_losses(probability: Any, up: Any) -> Any:
    import numpy as np

    return (np.asarray(probability, dtype=np.float64) - np.asarray(up, dtype=np.float64)) ** 2


def log_losses(probability: Any, up: Any) -> Any:
    import numpy as np

    p = np.clip(np.asarray(probability, dtype=np.float64), LOG_LOSS_EPSILON, 1 - LOG_LOSS_EPSILON)
    y = np.asarray(up, dtype=np.float64)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def roc_auc(probability: Any, up: Any) -> float | None:
    import numpy as np
    from sklearn.metrics import roc_auc_score

    if np.unique(up).shape[0] != 2:
        return None
    return float(roc_auc_score(up, probability))


def reliability_bins(probability: Any, up: Any) -> list[dict[str, Any]]:
    """Ten fixed equal-width probability bins on [0, 1]; the last bin is closed."""
    import numpy as np

    p = np.asarray(probability, dtype=np.float64)
    y = np.asarray(up, dtype=np.float64)
    index = np.minimum((p * RELIABILITY_BINS).astype(np.int64), RELIABILITY_BINS - 1)
    bins = []
    for position in range(RELIABILITY_BINS):
        members = index == position
        count = int(np.count_nonzero(members))
        bins.append(
            {
                "lower": position / RELIABILITY_BINS,
                "upper": (position + 1) / RELIABILITY_BINS,
                "count": count,
                "mean_p_up": float(p[members].mean()) if count else None,
                "observed_up_frequency": float(y[members].mean()) if count else None,
            }
        )
    return bins


@dataclass(frozen=True)
class ScoredFold:
    """One outer fold's hourly evaluation timeline and its paired Brier differences."""

    year: int
    first_time: int
    last_time: int
    times: Any  # int64 decision instants of scored rows, strictly increasing
    differences: Any  # control Brier loss - model Brier loss, per scored row

    @property
    def span_hours(self) -> int:
        return (self.last_time - self.first_time) // HOUR_SECONDS + 1


def block_length_hours(horizon_hours: int) -> int:
    return max(MINIMUM_BLOCK_HOURS, 2 * horizon_hours)


def horizon_seed_sequences() -> dict[int, Any]:
    """One independent child stream of the family seed per horizon, in frozen order."""
    import numpy as np

    children = np.random.SeedSequence(FAMILY_SEED).spawn(len(HORIZONS_HOURS))
    return dict(zip(HORIZONS_HOURS, children, strict=True))


def bootstrap_interval(
    folds: Sequence[ScoredFold],
    block_hours: int,
    seed: Any,
    replicates: int = BOOTSTRAP_REPLICATES,
    alpha: float = PER_HORIZON_ALPHA,
    chunk: int = REPLICATE_CHUNK,
) -> dict[str, Any]:
    """Central `1 - alpha` percentile interval for the pooled Brier improvement.

    Blocks are contiguous on each fold's hourly timeline (an unscored hour keeps its slot and
    contributes nothing) and are drawn independently inside each fold, so no block ever
    crosses a fold boundary. A replicate pools the resampled differences across folds and
    divides by the resampled number of scored rows.
    """
    import numpy as np

    if not folds:
        raise FoundationError("the bootstrap has no fold")
    if replicates <= 0 or chunk <= 0 or block_hours <= 0:
        raise FoundationError("the bootstrap budget and block length must be positive")
    generator = np.random.default_rng(seed)
    difference_totals = np.zeros(replicates, dtype=np.float64)
    record_totals = np.zeros(replicates, dtype=np.float64)
    geometry: dict[str, dict[str, int]] = {}
    for fold in folds:
        slots = ((np.asarray(fold.times) - fold.first_time) // HOUR_SECONDS).astype(np.int64)
        if slots.shape[0] and (slots.min() < 0 or slots.max() >= fold.span_hours):
            raise FoundationError(f"{fold.year}: a scored row sits outside its fold timeline")
        values = np.zeros(fold.span_hours, dtype=np.float64)
        present = np.zeros(fold.span_hours, dtype=np.float64)
        values[slots] = fold.differences
        present[slots] = 1.0
        full_d, partial_d, draws, block = block_sums(values, block_hours)
        full_m, partial_m, _, _ = block_sums(present, block_hours)
        starts_available = int(full_d.shape[0])
        geometry[str(fold.year)] = {
            "timeline_hours": fold.span_hours,
            "effective_block_hours": block,
            "blocks_per_replicate": draws,
            "block_start_positions": starts_available,
            "scored_rows": int(slots.shape[0]),
        }
        done = 0
        while done < replicates:
            size = min(chunk, replicates - done)
            starts = generator.integers(0, starts_available, size=(size, draws))
            head, tail = starts[:, : draws - 1], starts[:, draws - 1]
            difference_totals[done : done + size] += full_d[head].sum(axis=1) + partial_d[tail]
            record_totals[done : done + size] += full_m[head].sum(axis=1) + partial_m[tail]
            done += size
    if not np.all(record_totals > 0):
        raise FoundationError("a bootstrap replicate resampled no scored row")
    statistics = difference_totals / record_totals
    lower, upper = np.quantile(statistics, [alpha / 2, 1 - alpha / 2])
    return {
        "method": BOOTSTRAP_METHOD,
        "block_length_hours": block_hours,
        "replicates": replicates,
        "family_seed": FAMILY_SEED,
        "alpha": alpha,
        "interval_mass": 1.0 - alpha,
        "interval": [float(lower), float(upper)],
        "lower_bound": float(lower),
        "blocks_cross_fold_boundaries": False,
        "fold_geometry": geometry,
    }


# --------------------------------------------------------------------------------------
# Qualification and horizon selection.
# --------------------------------------------------------------------------------------


def qualification(summary: Mapping[str, Any]) -> dict[str, Any]:
    """The six frozen criteria; the horizon is supported only if every one holds."""
    folds = summary["folds"]
    criteria = {
        "pooled_feature_coverage_at_least_0_95": summary["pooled_feature_coverage"]
        >= POOLED_COVERAGE_MINIMUM,
        "every_fold_feature_coverage_at_least_0_90": all(
            fold["feature_coverage"] >= FOLD_COVERAGE_MINIMUM for fold in folds
        ),
        "pooled_brier_improvement_positive": summary["pooled_brier_improvement"] > 0,
        "adjusted_bootstrap_lower_bound_positive": summary["bootstrap"]["lower_bound"] > 0,
        "at_least_3_of_4_folds_non_negative": sum(
            1 for fold in folds if fold["brier_improvement"] >= 0
        )
        >= MINIMUM_NON_NEGATIVE_FOLDS,
        "pooled_log_loss_not_worse_than_control": summary["pooled_model_log_loss"]
        <= summary["pooled_control_log_loss"],
    }
    return {
        "criteria": criteria,
        "classification": SUPPORTED if all(criteria.values()) else NOT_SUPPORTED,
    }


def select_horizon(classifications: Mapping[int, str]) -> str:
    """The frozen 24h -> 4h -> 1h precedence; never a score maximisation."""
    if set(classifications) != set(HORIZONS_HOURS):
        raise FoundationError("selection needs a classification for every frozen horizon")
    for horizon in HORIZONS_HOURS:
        if classifications[horizon] == SUPPORTED:
            return SELECTION_OUTCOMES[horizon]
    return NO_HORIZON_SUPPORTED


# --------------------------------------------------------------------------------------
# One horizon, end to end.
# --------------------------------------------------------------------------------------


def evaluate_horizon(
    panel: HourlyPanel,
    horizon_hours: int,
    seed: Any,
    replicates: int = BOOTSTRAP_REPLICATES,
    fold_years: Sequence[int] = OUTER_FOLD_YEARS,
) -> dict[str, Any]:
    import numpy as np

    returns, code = horizon_targets(panel, horizon_hours)
    del returns
    times = panel.decision_times
    eligible = (code == UP_CODE) | (code == DOWN_CODE)
    usable = eligible & panel.feature_valid
    folds: list[dict[str, Any]] = []
    scored: list[ScoredFold] = []
    pooled_p: list[Any] = []
    pooled_c: list[Any] = []
    pooled_y: list[Any] = []

    for year in fold_years:
        training_mask, evaluation_mask = outer_fold_masks(times, horizon_hours, year)
        training_rows = np.flatnonzero(training_mask & usable)
        base, calibration = calibration_split(times[training_rows], horizon_hours)
        base_rows, calibration_rows = training_rows[base], training_rows[calibration]
        up = (code == UP_CODE).astype(np.int64)
        model = fit_model(
            panel.features[base_rows],
            up[base_rows],
            panel.features[calibration_rows],
            up[calibration_rows],
        )
        base_rate = float(up[training_rows].mean())

        eligible_rows = np.flatnonzero(evaluation_mask & eligible)
        evaluation_rows = np.flatnonzero(evaluation_mask & usable)
        if evaluation_rows.shape[0] == 0:
            raise FoundationError(f"{year}: no feature-valid evaluation row")
        p_up = model.p_up(panel.features[evaluation_rows])
        y = up[evaluation_rows]
        control = np.full(y.shape[0], base_rate, dtype=np.float64)
        model_brier = brier_losses(p_up, y)
        control_brier = brier_losses(control, y)
        evaluation_all = np.flatnonzero(evaluation_mask)
        folds.append(
            {
                "year": year,
                "evaluation_instants": int(evaluation_all.shape[0]),
                "label_eligible_rows": int(eligible_rows.shape[0]),
                "neutral_labels": int(np.count_nonzero(evaluation_mask & (code == NEUTRAL_CODE))),
                "label_unavailable": int(
                    np.count_nonzero(evaluation_mask & (code == UNAVAILABLE_CODE))
                ),
                "scored_rows": int(evaluation_rows.shape[0]),
                "feature_coverage": float(evaluation_rows.shape[0] / eligible_rows.shape[0]),
                "training_rows": int(training_rows.shape[0]),
                "training_first": iso(int(times[training_rows[0]])),
                "training_last": iso(int(times[training_rows[-1]])),
                "training_last_label_end": iso(
                    int(times[training_rows[-1]]) + horizon_hours * HOUR_SECONDS
                ),
                "base_fit_rows": int(base_rows.shape[0]),
                "calibration_rows": int(calibration_rows.shape[0]),
                "embargo_dropped_rows": int(
                    math.floor(BASE_FIT_FRACTION * training_rows.shape[0]) - base_rows.shape[0]
                ),
                "training_up_base_rate": base_rate,
                "model": model.describe(),
                "model_brier": float(model_brier.mean()),
                "control_brier": float(control_brier.mean()),
                "brier_improvement": float(control_brier.mean() - model_brier.mean()),
                "model_log_loss": float(log_losses(p_up, y).mean()),
                "control_log_loss": float(log_losses(control, y).mean()),
                "roc_auc": roc_auc(p_up, y),
                "evaluation_up_rate": float(y.mean()),
                "mean_p_up": float(p_up.mean()),
            }
        )
        scored.append(
            ScoredFold(
                year=year,
                first_time=int(times[evaluation_all[0]]),
                last_time=int(times[evaluation_all[-1]]),
                times=times[evaluation_rows],
                differences=control_brier - model_brier,
            )
        )
        pooled_p.append(p_up)
        pooled_c.append(control)
        pooled_y.append(y)

    p_all = np.concatenate(pooled_p)
    c_all = np.concatenate(pooled_c)
    y_all = np.concatenate(pooled_y)
    eligible_total = sum(fold["label_eligible_rows"] for fold in folds)
    model_brier = float(brier_losses(p_all, y_all).mean())
    control_brier = float(brier_losses(c_all, y_all).mean())
    summary: dict[str, Any] = {
        "horizon_hours": horizon_hours,
        "block_length_hours": block_length_hours(horizon_hours),
        "scored_rows": int(y_all.shape[0]),
        "label_eligible_rows": eligible_total,
        "pooled_feature_coverage": float(y_all.shape[0] / eligible_total),
        "pooled_model_brier": model_brier,
        "pooled_control_brier": control_brier,
        "pooled_brier_improvement": control_brier - model_brier,
        "pooled_model_log_loss": float(log_losses(p_all, y_all).mean()),
        "pooled_control_log_loss": float(log_losses(c_all, y_all).mean()),
        "pooled_roc_auc": roc_auc(p_all, y_all),
        "pooled_up_rate": float(y_all.mean()),
        "reliability_bins": reliability_bins(p_all, y_all),
        "folds": folds,
    }
    summary["bootstrap"] = bootstrap_interval(
        scored, block_length_hours(horizon_hours), seed, replicates=replicates
    )
    summary["qualification"] = qualification(summary)
    return summary


def file_sha256(root: Path, relative: str) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


def run_foundation(root: Path = ROOT, replicates: int = BOOTSTRAP_REPLICATES) -> dict[str, Any]:
    """Verify the pinned source, build the panel and evaluate every frozen horizon once."""
    books, manifest = load_minute_books(root)
    panel = build_panel(books)
    seeds = horizon_seed_sequences()
    horizons = {
        str(horizon): evaluate_horizon(panel, horizon, seeds[horizon], replicates=replicates)
        for horizon in HORIZONS_HOURS
    }
    classifications = {
        horizon: horizons[str(horizon)]["qualification"]["classification"]
        for horizon in HORIZONS_HOURS
    }
    valid = int(panel.feature_valid.sum())
    return {
        "schema_version": 1,
        "version": VERSION,
        "experiment_id": EXPERIMENT_ID,
        "protocol": {"path": PROTOCOL_PATH, "sha256": file_sha256(root, PROTOCOL_PATH)},
        "source": {
            "manifest_path": MANIFEST_PATH,
            "manifest_sha256": file_sha256(root, MANIFEST_PATH),
            "manifest_id": manifest["manifest_id"],
            "object_index_sha256": manifest["object_index_sha256"],
            "objects_verified": manifest["objects"],
            "minute_books": {market: books[market].summary() for market in MARKETS},
        },
        "implementation": {path: file_sha256(root, path) for path in IMPLEMENTATION_PATHS},
        "design": {
            "features": list(FEATURE_NAMES),
            "horizons_hours_in_frozen_order": list(HORIZONS_HOURS),
            "outer_fold_years": list(OUTER_FOLD_YEARS),
            "base_fit_fraction": BASE_FIT_FRACTION,
            "calibration_embargo_multiple_of_horizon": CALIBRATION_EMBARGO_MULTIPLE,
            "logistic": dict(LOGISTIC_PARAMETERS),
            "platt": dict(PLATT_PARAMETERS),
            "bootstrap_replicates": replicates,
            "family_seed": FAMILY_SEED,
            "familywise_alpha": FAMILYWISE_ALPHA,
            "per_horizon_alpha": PER_HORIZON_ALPHA,
            "interval_mass": INTERVAL_MASS,
            "log_loss_probability_clip": LOG_LOSS_EPSILON,
            "reliability_bins": RELIABILITY_BINS,
        },
        "panel": {
            "decision_instants": int(panel.decision_times.shape[0]),
            "first_decision": iso(int(panel.decision_times[0])),
            "last_decision": iso(int(panel.decision_times[-1])),
            "feature_valid_instants": valid,
            "feature_unavailable_instants": int(panel.decision_times.shape[0]) - valid,
        },
        "horizons": horizons,
        "classifications": {str(horizon): value for horizon, value in classifications.items()},
        "selection": select_horizon(classifications),
        "boundaries": {
            "action_threshold_used": False,
            "trading_pnl": False,
            "costs_or_execution": False,
            "magnitude": False,
            "hyperparameter_search": False,
            "feature_search": False,
            "sealed_queries": 0,
            "champion_status": "NONE",
            "real_money": False,
        },
        "model_fits": len(HORIZONS_HOURS) * len(OUTER_FOLD_YEARS),
    }


# --------------------------------------------------------------------------------------
# Writers. Nothing here is called until the Owner runs the frozen foundation once.
# --------------------------------------------------------------------------------------


def result_bytes(result: Mapping[str, Any]) -> bytes:
    return canonical_bytes(result)


def _number(value: Any, digits: int = 6) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def markdown_bytes(result: Mapping[str, Any]) -> bytes:
    lines = [
        "# PREDICTIVE V2 PUBLIC TAKER FLOW HORIZON FOUNDATION V1 — result",
        "",
        f"Experiment: `{result['experiment_id']}`",
        f"Protocol: `{result['protocol']['path']}` (sha256 `{result['protocol']['sha256']}`)",
        (
            f"Source manifest: `{result['source']['manifest_path']}` "
            f"(sha256 `{result['source']['manifest_sha256']}`)"
        ),
        "",
        f"**Selection: `{result['selection']}`**",
        "",
        (
            "| Horizon | Scored rows | Coverage | Model Brier | Control Brier | Improvement | "
            "Adjusted interval | Model log loss | Control log loss | AUC | Classification |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for horizon in HORIZONS_HOURS:
        item = result["horizons"][str(horizon)]
        lower, upper = item["bootstrap"]["interval"]
        lines.append(
            f"| {horizon}h | {item['scored_rows']} | {_number(item['pooled_feature_coverage'], 4)} "
            f"| {_number(item['pooled_model_brier'])} | {_number(item['pooled_control_brier'])} "
            f"| {_number(item['pooled_brier_improvement'], 7)} "
            f"| [{_number(lower, 7)}, {_number(upper, 7)}] "
            f"| {_number(item['pooled_model_log_loss'])} "
            f"| {_number(item['pooled_control_log_loss'])} "
            f"| {_number(item['pooled_roc_auc'], 4)} "
            f"| {item['qualification']['classification']} |"
        )
    for horizon in HORIZONS_HOURS:
        item = result["horizons"][str(horizon)]
        lines += [
            "",
            f"## {horizon}h",
            "",
            "| Fold | Scored | Coverage | Base rate | Brier improvement | AUC |",
            "|---|---|---|---|---|---|",
        ]
        for fold in item["folds"]:
            lines.append(
                f"| {fold['year']} | {fold['scored_rows']} | "
                f"{_number(fold['feature_coverage'], 4)} | "
                f"{_number(fold['training_up_base_rate'], 4)} | "
                f"{_number(fold['brier_improvement'], 7)} | {_number(fold['roc_auc'], 4)} |"
            )
        lines += ["", "Criteria:"]
        for name, passed in item["qualification"]["criteria"].items():
            lines.append(f"- {name}: {'PASS' if passed else 'FAIL'}")
    lines += [
        "",
        (
            "Prediction-only foundation: no action threshold, trading PnL, costs, magnitude or "
            "sealed data. Champion NONE. Real money false."
        ),
        "",
    ]
    return "\n".join(lines).encode("utf-8")


__all__ = [
    "BOOTSTRAP_REPLICATES",
    "EXPERIMENT_ID",
    "FAMILY_SEED",
    "FEATURE_NAMES",
    "HORIZONS_HOURS",
    "NOT_SUPPORTED",
    "NO_HORIZON_SUPPORTED",
    "OUTER_FOLD_YEARS",
    "REPORT_MARKDOWN_PATH",
    "RESULT_PATH",
    "RESULT_PATHS",
    "SELECTION_OUTCOMES",
    "SUPPORTED",
    "FoundationError",
    "HourlyPanel",
    "ScoredFold",
    "block_length_hours",
    "bootstrap_interval",
    "build_panel",
    "calibration_split",
    "evaluate_horizon",
    "fit_model",
    "horizon_seed_sequences",
    "horizon_targets",
    "markdown_bytes",
    "market_imbalance",
    "outer_fold_masks",
    "qualification",
    "result_bytes",
    "run_foundation",
    "select_horizon",
]
