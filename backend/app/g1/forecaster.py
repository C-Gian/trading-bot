"""Frozen System G1 continuous 4h forecaster (Development V1 protocol section 11).

- target: USD-M terminal log return exactly 4h after each completed-15m issue;
- prior risk: sample standard deviation (ddof = 1) of the previous 96 completed 15m log returns,
  `sigma4h = sigma15m * sqrt(16)`; unavailable/non-positive -> prediction UNAVAILABLE;
- standardized target `z = r4h / sigma4h_at_issue`;
- at most nine cells: directional bias {BEARISH, NEUTRAL, BULLISH} x conviction {LOW, MEDIUM,
  HIGH};
- annual expanding training: for evaluation year Y only matured observations with
  `issue + 4h <= Y-01-01T00:00Z` (the exact 4h purge) enter the estimator;
- fixed shrinkage `w = n / (n + 256)` towards the unconditional training distribution;
- probability of a positive return, mean, median, q10 and q90 all from the same weighted mixture;
  moments/quantiles are translated back to raw log return with the issue-time risk scale;
- probability status `EMPIRICAL_SHRUNK_CONDITIONAL_PROBABILITY_NOT_CALIBRATED`.

Weighted quantile definition (deterministic): sort the pooled mixture atoms by value (ties keep
cell atoms before unconditional atoms, then training order); the q-quantile is the first atom whose
cumulative weight reaches `q * total_weight` (lower inverse CDF). Predicted display direction is UP
if the mixture probability exceeds 0.5, DOWN if below, NEUTRAL if exactly 0.5. The forecast never
gates a trade. Nothing here is fitted to market data unless a later authorized runner feeds it.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import stdev

SHRINKAGE_PRIOR = 256
RISK_WINDOW = 96
HORIZON = timedelta(hours=4)
SQRT_HORIZON_STEPS = math.sqrt(16)
QUANTILES = (0.10, 0.90)
PROBABILITY_STATUS = "EMPIRICAL_SHRUNK_CONDITIONAL_PROBABILITY_NOT_CALIBRATED"
BIASES = ("BEARISH", "NEUTRAL", "BULLISH")
CONVICTIONS = ("LOW", "MEDIUM", "HIGH")
ESTIMATOR_VERSION = "G1-EMPIRICAL-SHRUNK-CONDITIONAL-4H-V1"


def shrinkage_weight(n: int) -> float:
    return n / (n + SHRINKAGE_PRIOR)


def prior_risk_scale(log_returns: Sequence[float]) -> float | None:
    """sigma4h from exactly the previous 96 completed 15m log returns, or None."""
    if len(log_returns) != RISK_WINDOW or not all(math.isfinite(x) for x in log_returns):
        return None
    sigma = stdev(log_returns) * SQRT_HORIZON_STEPS
    return sigma if math.isfinite(sigma) and sigma > 0 else None


@dataclass(frozen=True)
class TrainingRow:
    issue_time: datetime
    bias: str
    conviction: str
    z: float


def training_boundary(year: int) -> datetime:
    return datetime(year, 1, 1, tzinfo=UTC)


def eligible_rows(rows: Iterable[TrainingRow], year: int) -> list[TrainingRow]:
    """Matured before Jan 1 of `year` with the exact 4h purge: issue + 4h <= boundary."""
    boundary = training_boundary(year)
    return [row for row in rows if row.issue_time + HORIZON <= boundary]


def weighted_quantile(atoms: Sequence[tuple[float, float]], level: float) -> float:
    ordered = sorted(enumerate(atoms), key=lambda item: (item[1][0], item[0]))
    total = sum(weight for _, (_, weight) in ordered)
    target = level * total
    cumulative = 0.0
    for _, (value, weight) in ordered:
        cumulative += weight
        if cumulative >= target - 1e-15:
            return value
    return ordered[-1][1][0]


@dataclass(frozen=True)
class Forecast:
    available: bool
    probability_up: float | None
    mean_return: float | None
    median_return: float | None
    lower_return: float | None
    upper_return: float | None
    mean_z: float | None
    cell_n: int
    weight: float | None
    unavailable_reason: str | None
    training_year: int | None

    @property
    def direction(self) -> str:
        if not self.available or self.probability_up is None:
            return "UNAVAILABLE"
        if self.probability_up > 0.5:
            return "UP"
        return "DOWN" if self.probability_up < 0.5 else "NEUTRAL"


def unavailable(reason: str, year: int | None = None) -> Forecast:
    return Forecast(False, None, None, None, None, None, None, 0, None, reason, year)


class EmpiricalShrunkForecaster:
    """One fitted year of the frozen estimator."""

    def __init__(self, year: int, rows: Iterable[TrainingRow]) -> None:
        self.year = year
        self.rows = eligible_rows(rows, year)
        self.cells: dict[tuple[str, str], list[float]] = {
            (b, c): [] for b in BIASES for c in CONVICTIONS
        }
        for row in self.rows:
            if (row.bias, row.conviction) not in self.cells:
                raise ValueError(f"unknown conditioning cell {row.bias}x{row.conviction}")
            self.cells[(row.bias, row.conviction)].append(row.z)
        self.unconditional = [row.z for row in self.rows]
        self.up_rate = (
            None
            if not self.unconditional
            else sum(1 for z in self.unconditional if z > 0) / len(self.unconditional)
        )

    def mixture(self, bias: str, conviction: str) -> tuple[list[tuple[float, float]], float, int]:
        cell = self.cells[(bias, conviction)]
        n = len(cell)
        w = shrinkage_weight(n)
        atoms = [(z, w / n) for z in cell] if n else []
        base = self.unconditional
        atoms += [(z, (1 - w) / len(base)) for z in base]
        return atoms, w, n

    def predict(self, bias: str, conviction: str, sigma4h: float | None) -> Forecast:
        if sigma4h is None or not math.isfinite(sigma4h) or sigma4h <= 0:
            return unavailable("PRIOR_RISK_SCALE_UNAVAILABLE", self.year)
        if not self.unconditional:
            return unavailable("NO_TRAINING_OBSERVATIONS", self.year)
        atoms, w, n = self.mixture(bias, conviction)
        total = sum(weight for _, weight in atoms)
        probability = sum(weight for z, weight in atoms if z > 0) / total
        mean_z = sum(z * weight for z, weight in atoms) / total
        median_z = weighted_quantile(atoms, 0.5)
        low_z = weighted_quantile(atoms, QUANTILES[0])
        high_z = weighted_quantile(atoms, QUANTILES[1])
        probability = min(1.0, max(0.0, probability))
        return Forecast(
            True,
            probability,
            mean_z * sigma4h,
            median_z * sigma4h,
            low_z * sigma4h,
            high_z * sigma4h,
            mean_z,
            n,
            w,
            None,
            self.year,
        )
