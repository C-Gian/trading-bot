"""Prospective cluster-aware power design for CROSS_SECTION_COMMON_EFFECT_V1.

Structural safety property: every pooled-effect estimator in this module requires an
explicit non-zero placebo shift and refuses shift zero, so the true (zero-alignment)
pooled ALIGNED beta, its t statistic and its p value cannot be produced here. The real
outcome enters only through a fixed-effects residualization that never sees the ALIGNED
regressor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from .cross_section import (
    CLUSTER_METHOD,
    DEGREES_OF_FREEDOM_RULE,
    EFFECTIVE_ALPHA,
    MINIMUM_ASSET_CLUSTERS,
    MINIMUM_WEEK_CLUSTERS,
    PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS,
    TARGET_POWER,
)

# A placebo participant needs the excluded band on both sides plus one free band.
PLACEBO_MINIMUM_POSITIONS = 3 * PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS
INSTRUMENT_EPOCH_GAP_HOURS = 720


class ZeroAlignmentForbidden(ValueError):
    """The true unshifted ALIGNED alignment may never be evaluated in this checkpoint."""


@dataclass
class Panel:
    """Eligible decision rows: asset/time factors, frozen outcome, frozen raw signal."""

    asset_index: np.ndarray
    time_index: np.ndarray
    week_index: np.ndarray
    outcome_bps: np.ndarray
    signal: np.ndarray
    asset_labels: list[str]
    asset_offsets: np.ndarray
    time_count: int

    @property
    def rows(self) -> int:
        return len(self.outcome_bps)

    @property
    def asset_count(self) -> int:
        return len(self.asset_labels)

    def asset_lengths(self) -> np.ndarray:
        return np.diff(self.asset_offsets)


class TwoWayAbsorber:
    """Exact within transform for the asset and decision-time factors.

    The time factor is absorbed analytically and the remaining asset problem is a dense
    `A x A` normal system, so the transform is exact rather than iterative and every
    placebo replicate reuses the same factorization.
    """

    def __init__(
        self, asset_index: np.ndarray, time_index: np.ndarray, asset_count: int, time_count: int
    ):
        self.asset_index = asset_index
        self.time_index = time_index
        self.asset_count = asset_count
        self.time_count = time_count
        self.time_counts = np.bincount(time_index, minlength=time_count).astype(np.float64)
        self.asset_counts = np.bincount(asset_index, minlength=asset_count).astype(np.float64)
        safe_time = np.where(self.time_counts > 0, self.time_counts, 1.0)
        self._safe_time = safe_time
        flat = time_index.astype(np.int64) * asset_count + asset_index.astype(np.int64)
        incidence = np.bincount(flat, minlength=time_count * asset_count).astype(np.float64)
        incidence = incidence.reshape(time_count, asset_count)
        gram = incidence.T @ (incidence / safe_time[:, None])
        self.gram = np.diag(self.asset_counts) - gram
        self.inverse = np.linalg.pinv(self.gram, rcond=1e-10)

    def _time_demean(self, values: np.ndarray) -> np.ndarray:
        means = np.bincount(self.time_index, weights=values, minlength=self.time_count)
        return values - (means / self._safe_time)[self.time_index]

    def residualize(self, values: np.ndarray) -> np.ndarray:
        centered = self._time_demean(values.astype(np.float64, copy=False))
        loadings = np.bincount(self.asset_index, weights=centered, minlength=self.asset_count)
        coefficients = self.inverse @ loadings
        return self._time_demean(values - coefficients[self.asset_index])

    def diagnostics(self, values: np.ndarray) -> dict[str, float]:
        """Confirm the transform actually annihilates both factor spaces."""
        residual = self.residualize(values)
        asset_means = np.bincount(
            self.asset_index, weights=residual, minlength=self.asset_count
        ) / np.where(self.asset_counts > 0, self.asset_counts, 1.0)
        time_means = (
            np.bincount(self.time_index, weights=residual, minlength=self.time_count)
            / self._safe_time
        )
        scale = float(np.max(np.abs(residual))) or 1.0
        return {
            "max_absolute_asset_mean": float(np.max(np.abs(asset_means))) / scale,
            "max_absolute_time_mean": float(np.max(np.abs(time_means))) / scale,
        }


def two_way_cluster_variance(
    regressor: np.ndarray,
    residual: np.ndarray,
    asset_index: np.ndarray,
    week_index: np.ndarray,
    intersection_index: np.ndarray,
) -> dict[str, Any]:
    """Cameron-Gelbach-Miller two-way cluster covariance for a single regressor.

    `V = V_asset + V_week - V_intersection`, each term the usual cluster sandwich with the
    `G / (G - 1)` finite-sample correction.
    """
    scores = regressor * residual
    bread = float(np.dot(regressor, regressor))
    if bread <= 0:
        raise ValueError("degenerate residualized regressor")
    terms: dict[str, float] = {}
    for name, index in (
        ("asset", asset_index),
        ("week", week_index),
        ("intersection", intersection_index),
    ):
        size = int(index.max()) + 1
        totals = np.bincount(index, weights=scores, minlength=size)
        groups = int(np.count_nonzero(np.bincount(index, minlength=size)))
        correction = groups / (groups - 1) if groups > 1 else 1.0
        terms[name] = correction * float(np.dot(totals, totals))
        terms[f"{name}_groups"] = float(groups)
    meat = terms["asset"] + terms["week"] - terms["intersection"]
    variance = meat / (bread * bread)
    return {
        "bread": bread,
        "meat_asset": terms["asset"],
        "meat_week": terms["week"],
        "meat_intersection": terms["intersection"],
        "meat": meat,
        "variance": variance,
        "standard_error": math.sqrt(variance) if variance > 0 else float("nan"),
        "asset_groups": int(terms["asset_groups"]),
        "week_groups": int(terms["week_groups"]),
        "intersection_groups": int(terms["intersection_groups"]),
        "positive_semidefinite": bool(meat > 0),
    }


def placebo_shift_grid(lengths: np.ndarray, maximum_shifts: int) -> dict[str, Any]:
    """Deterministic shift grid derived only from panel geometry, never from outcomes.

    Shifts are bounded by the shortest participating history so that every asset receives
    exactly the same absolute displacement and no asset is ever dropped from a replicate.
    """
    if not len(lengths):
        return {"shifts": [], "upper_bound": 0, "reason": "NO_PARTICIPATING_ASSETS"}
    upper = int(lengths.min()) - PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS
    if upper < PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS:
        return {"shifts": [], "upper_bound": upper, "reason": "SHORTEST_HISTORY_TOO_SHORT"}
    candidates = list(range(PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS, upper + 1))
    stride = max(1, math.ceil(2 * len(candidates) / maximum_shifts))
    selected = candidates[::stride]
    shifts = sorted({shift for value in selected for shift in (value, -value)})
    return {
        "shifts": shifts,
        "upper_bound": upper,
        "stride": stride,
        "reason": "OK",
    }


def shift_signal(panel: Panel, shift: int) -> np.ndarray:
    """Circularly shift each asset's frozen binary ALIGNED sequence by the same magnitude."""
    if shift == 0:
        raise ZeroAlignmentForbidden("placebo calibration may never use shift zero")
    if abs(shift) < PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS:
        raise ZeroAlignmentForbidden("placebo shift is inside the excluded near-zero band")
    shifted = np.empty(panel.rows, dtype=np.float64)
    for asset in range(panel.asset_count):
        start, end = int(panel.asset_offsets[asset]), int(panel.asset_offsets[asset + 1])
        if end == start:
            continue
        length = end - start
        effective = shift % length
        if min(effective, length - effective) < PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS:
            raise ZeroAlignmentForbidden(
                "shift grid admitted a displacement inside the excluded band"
            )
        shifted[start:end] = np.roll(panel.signal[start:end], effective)
    return shifted


def placebo_statistic(
    panel: Panel,
    shift: int,
    absorber: TwoWayAbsorber,
    residual_outcome: np.ndarray,
    compact_week: np.ndarray,
    intersection_index: np.ndarray,
) -> dict[str, Any]:
    """One placebo pooled statistic. Structurally impossible to call at the true alignment."""
    shifted = shift_signal(panel, shift)
    demeaned = absorber.residualize(shifted)
    denominator = float(np.dot(demeaned, demeaned))
    if denominator <= 0:
        return {"shift": shift, "degenerate": True}
    effect = float(np.dot(demeaned, residual_outcome)) / denominator
    residual = residual_outcome - effect * demeaned
    covariance = two_way_cluster_variance(
        demeaned, residual, panel.asset_index, compact_week, intersection_index
    )
    standard_error = covariance["standard_error"]
    finite = standard_error and math.isfinite(standard_error) and standard_error > 0
    return {
        "shift": shift,
        "degenerate": False,
        "placebo_effect_bps": effect,
        "standard_error": standard_error,
        "placebo_t": effect / standard_error if finite else float("nan"),
        "signal_variation": denominator,
        "events": int(shifted.sum()),
        "asset_clusters": covariance["asset_groups"],
        "week_clusters": covariance["week_groups"],
        "positive_semidefinite": covariance["positive_semidefinite"],
    }


# --- deterministic Student-t helpers -------------------------------------------------
_TINY = 1e-300
_EPSILON = 1e-15


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """Modified Lentz evaluation of the beta continued fraction."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _TINY:
        d = _TINY
    d = 1.0 / d
    result = d
    for m in range(1, 300):
        m2 = 2 * m
        numerator = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + numerator * d
        if abs(d) < _TINY:
            d = _TINY
        c = 1.0 + numerator / c
        if abs(c) < _TINY:
            c = _TINY
        d = 1.0 / d
        result *= d * c
        numerator = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + numerator * d
        if abs(d) < _TINY:
            d = _TINY
        c = 1.0 + numerator / c
        if abs(c) < _TINY:
            c = _TINY
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < _EPSILON:
            break
    return result


def _incomplete_beta(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_continued_fraction(a, b, x) / a
    return 1.0 - front * _beta_continued_fraction(b, a, 1.0 - x) / b


def student_t_cdf(value: float, degrees: float) -> float:
    """Student-t distribution function, exact to double precision."""
    if degrees <= 0:
        raise ValueError("degrees of freedom must be positive")
    x = degrees / (degrees + value * value)
    tail = 0.5 * _incomplete_beta(degrees / 2.0, 0.5, x)
    return 1.0 - tail if value > 0 else tail


def student_t_quantile(probability: float, degrees: float) -> float:
    """Deterministic Student-t quantile by bisection on the exact distribution function."""
    if not 0.0 < probability < 1.0:
        raise ValueError("quantile probability must lie strictly inside the unit interval")
    low, high = -1.0e4, 1.0e4
    for _ in range(400):
        middle = (low + high) / 2.0
        if student_t_cdf(middle, degrees) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def prospective_power(standard_error: float, degrees: float, mesi_bps: float) -> dict[str, Any]:
    """One-sided power and MDE for the frozen design at the governed effective alpha."""
    critical = student_t_quantile(1.0 - EFFECTIVE_ALPHA, degrees)
    noncentrality = mesi_bps / standard_error
    power = 1.0 - student_t_cdf(critical - noncentrality, degrees)
    power_quantile = student_t_quantile(TARGET_POWER, degrees)
    return {
        "effective_alpha": EFFECTIVE_ALPHA,
        "degrees_of_freedom": degrees,
        "critical_t": critical,
        "design_standard_error_bps": standard_error,
        "noncentrality_at_MESI": noncentrality,
        "power_at_MESI": power,
        "minimum_detectable_effect_bps": (critical + power_quantile) * standard_error,
        "target_power": TARGET_POWER,
        "cluster_method": CLUSTER_METHOD,
        "degrees_of_freedom_rule": DEGREES_OF_FREEDOM_RULE,
    }


def cluster_support(asset_clusters: int, week_clusters: int) -> dict[str, Any]:
    ok = asset_clusters >= MINIMUM_ASSET_CLUSTERS and week_clusters >= MINIMUM_WEEK_CLUSTERS
    return {
        "asset_clusters_with_events": asset_clusters,
        "week_clusters_with_events": week_clusters,
        "minimum_asset_clusters": MINIMUM_ASSET_CLUSTERS,
        "minimum_week_clusters": MINIMUM_WEEK_CLUSTERS,
        "manual_asset_addition": False,
        "CLUSTER_SUPPORT_STATUS": "PASS" if ok else "REDESIGN_REQUIRED",
    }
