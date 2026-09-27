"""Prequential residual archives and the empirical predictive distribution (sections 8-10, 16).

An archive holds residuals of forecasts/utility predictions genuinely issued by the then-active
fit of one scientific system version, appended only once the target matured. It is keyed by
system version: residuals of another version are refused, never mixed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from .contract import (
    DIRECTION_TOLERANCE,
    MAX_RESIDUAL_AGE,
    MIN_RESIDUAL_SPAN,
    MIN_RESIDUALS,
    QUANTILES,
    STRENGTH_MODERATE,
    STRENGTH_STRONG,
)
from .records import Reason

PREQUENTIAL = "PREQUENTIAL_CDF_UNCALIBRATED"
FALLBACK = "TRAINING_TARGET_BASELINE_UNVALIDATED"
UNAVAILABLE = "UNAVAILABLE"


class VersionMixError(ValueError):
    pass


class ResidualArchive:
    """Append-only (in matured order) residual log with a trailing 730-day read window."""

    def __init__(self, system_version: str) -> None:
        self.system_version = system_version
        self._n = 0
        self._times = np.empty(1024, dtype="datetime64[m]")
        self._matured = np.empty(1024, dtype="datetime64[m]")
        self._values = np.empty(1024, dtype=float)

    def append(
        self, decision_time: datetime, matured_at: datetime, value: float, system_version: str
    ) -> None:
        if system_version != self.system_version:
            raise VersionMixError("residuals of another scientific system version are refused")
        if not np.isfinite(value):
            raise ValueError("non-finite residual")
        matured = np.datetime64(matured_at.replace(tzinfo=None), "m")
        decided = np.datetime64(decision_time.replace(tzinfo=None), "m")
        if self._n and (matured < self._matured[self._n - 1] or decided < self._times[self._n - 1]):
            raise ValueError("residuals must be appended in maturity order")
        if self._n == len(self._values):
            self._times = np.concatenate([self._times, np.empty_like(self._times)])
            self._matured = np.concatenate([self._matured, np.empty_like(self._matured)])
            self._values = np.concatenate([self._values, np.empty_like(self._values)])
        self._times[self._n], self._matured[self._n] = decided, matured
        self._values[self._n] = float(value)
        self._n += 1

    def __len__(self) -> int:
        return self._n

    def window(self, at: datetime) -> tuple[np.ndarray, np.ndarray]:
        """(decision times, residuals) matured at or before `at` within the trailing 730 days."""
        now = np.datetime64(at.replace(tzinfo=None), "m")
        oldest = np.datetime64((at - MAX_RESIDUAL_AGE).replace(tzinfo=None), "m")
        hi = int(np.searchsorted(self._matured[: self._n], now, side="right"))
        lo = int(np.searchsorted(self._times[:hi], oldest, side="left"))
        return self._times[lo:hi], self._values[lo:hi]

    def status(self, at: datetime) -> tuple[bool, int, float | None]:
        times, values = self.window(at)
        if len(values) == 0:
            return False, 0, None
        span = (times.max() - times.min()).astype("timedelta64[m]").astype(int) / 1440.0
        ready = bool(len(values) >= MIN_RESIDUALS and span >= MIN_RESIDUAL_SPAN.days)
        return ready, len(values), float(span)


def quantiles(values: np.ndarray) -> tuple[float, float, float]:
    q = np.quantile(values, list(QUANTILES), method="linear")  # == QUANTILE_METHOD
    return float(q[0]), float(q[1]), float(q[2])


@dataclass(frozen=True)
class Distribution:
    mean_return: float
    median_return: float
    q10: float
    q50: float
    q90: float
    p_positive: float
    atoms: int
    status: str


def distribution(mu_z: float, sigma: float, residuals: np.ndarray, status: str) -> Distribution:
    """Atoms (mu_z + e) * SIGMA_4H; ties at exactly zero are neither positive nor negative."""
    returns = (mu_z + residuals) * sigma
    q10, q50, q90 = quantiles(returns)
    return Distribution(
        float(returns.mean()),
        q50,
        q10,
        q50,
        q90,
        float(np.count_nonzero(returns > 0) / len(returns)),
        len(returns),
        status,
    )


def direction(median_return: float) -> str:
    if median_return > DIRECTION_TOLERANCE:
        return "UP"
    if median_return < -DIRECTION_TOLERANCE:
        return "DOWN"
    return "NEUTRAL"


def strength_label(view_strength_z: float) -> str:
    if view_strength_z >= STRENGTH_STRONG:
        return "STRONG"
    if view_strength_z >= STRENGTH_MODERATE:
        return "MODERATE"
    return "WEAK"


def calibration_reason(status: str) -> Reason:
    return (
        Reason.PREQUENTIAL_CDF_UNCALIBRATED
        if status == PREQUENTIAL
        else (Reason.TRAINING_TARGET_BASELINE_UNVALIDATED)
    )
