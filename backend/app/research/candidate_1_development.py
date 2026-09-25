"""Candidate #1 Development Lab implementation (`research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md`).

Implements the frozen protocol exactly. The population is *consumed* from the committed frozen
admission record, never re-derived. Matching reads only information known at the event hour.
Economic execution needs a spot 1m price source; the runner refuses to build one from real data
unless state carries an explicit Research Director execution authorization.

Implementation conventions (engineering readings, not scientific choices; see the
implementation-validation record): sample standard deviations (ddof=1); Austin standardized mean
difference on the matched raw covariates; t(G-1) critical values for cluster-robust intervals;
lower-tail expected shortfall over the worst ceil(10% N) observations; an exact exit or entry
minute after the development cutoff is unavailable, hence unscorable.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np

from app.backtest.models import CostModel

VERSION = "CANDIDATE_1_DEVELOPMENT_V1"
PROTOCOL_PATH = "research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md"
PROTOCOL_CANONICAL_SHA256 = "c47ffb9b5fc737962ec7e074c62344cb2aa9117ea7798a9f8a1ab19b07762313"
ADR_PATH = "decisions/ADR-0039-CANDIDATE-1-DEVELOPMENT-PROTOCOL-FREEZE.md"
ADR_CANONICAL_SHA256 = "d6183d9f70029c58814fd04593e42903ca6d298a5aadbf23a6bd7f448ce5d2cd"
ADMISSION_RECORD_PATH = "reports/validation/CANDIDATE-1-FROZEN-ADMISSION-V1.json"
ADMISSION_CANONICAL_SHA256 = "d79f533b2aa082853333858ed36319040d55f4bceef0f1cf69626c9d716ce2de"
ADMISSION_DISPOSITION = "CANDIDATE_1_ADMITTED_FOR_PROTOCOL_DESIGN"
RESULT_PATH = "research/experiments/CANDIDATE-1-DEVELOPMENT-V1/result.json"

YEARS = (2022, 2023, 2024)
MINUTE = 60
DECISION_OFFSET = 15 * MINUTE
PRIMARY_ENTRY_OFFSET = 16 * MINUTE
DELAY_ENTRY_OFFSET = 46 * MINUTE
EXIT_OFFSET = 4 * 3600 + 15 * MINUTE
DEVELOPMENT_LAST_MINUTE = int(datetime(2024, 12, 31, 23, 59, tzinfo=UTC).timestamp())
INTERVAL_START = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp())
INTERVAL_END = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp())

PRIMARY_COSTS = CostModel(profile="CANDIDATE_1_SPOT_COST_PRIMARY_V1")
STRESS_COSTS = CostModel(
    profile="CANDIDATE_1_SPOT_COST_STRESS_V1",
    entry_fee_bps=Decimal(15),
    exit_fee_bps=Decimal(15),
    entry_friction_bps=Decimal(3),
    exit_friction_bps=Decimal(3),
)

CALIPER = 0.50
MATCH_TIE_TOLERANCE = 1e-9
COVERAGE_OVERALL = 0.80
COVERAGE_YEAR = 0.70
SMD_POOLED = 0.10
SMD_YEAR = 0.25
SCORABLE_CANDIDATES = 0.95
SCORABLE_PAIRS = 0.95
MIN_SCORABLE_PER_YEAR = 25
ABS_MESI_BP = 25.0
INC_MESI_BP = 20.0
ANNUAL_MIN_BP = 500.0
ES_LEVEL = 0.10
ES_TOLERANCE_BP = 25.0
MAX_DRAWDOWN_BP = 1000.0
POSITIVE_YEARS = 2
TOP_REMOVED = 3
ALPHA_ONE_SIDED = 0.025
TARGET_POWER = 0.80
INTERVAL_MASS = 0.95

INVALID_EXECUTION = "INVALID_EXECUTION"
BLOCKED = "BLOCKED_DATA_OR_SUPPORT"
REJECTED = "DEVELOPMENT_REJECTED"
INCONCLUSIVE = "INCONCLUSIVE_NO_PROMOTION"
PROMOTION_ELIGIBLE = "PROMOTION_ELIGIBLE"
DISPOSITION_ORDER = (INVALID_EXECUTION, BLOCKED, REJECTED, INCONCLUSIVE, PROMOTION_ELIGIBLE)

ENTRY_MINUTE_UNAVAILABLE = "ENTRY_MINUTE_UNAVAILABLE"
EXIT_MINUTE_UNAVAILABLE = "EXIT_MINUTE_UNAVAILABLE"
ENTRY_AFTER_DEVELOPMENT_CUTOFF = "ENTRY_AFTER_DEVELOPMENT_CUTOFF"
EXIT_AFTER_DEVELOPMENT_CUTOFF = "EXIT_AFTER_DEVELOPMENT_CUTOFF"


class DevelopmentError(RuntimeError):
    """The frozen protocol cannot be applied faithfully."""


# --------------------------------------------------------------------------------------------
# 1. Frozen population ingestion
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Episode:
    t: int  # event hour T, epoch seconds
    year: int
    shock_z: float
    sigma_prior_1h: float
    candidate: bool

    @property
    def log_sigma(self) -> float:
        return math.log(self.sigma_prior_1h)


def canonical_text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _epoch(iso: str) -> int:
    return int(datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp())


def episodes_from_admission(record: Mapping[str, Any]) -> tuple[list[Episode], dict[str, Any]]:
    """The frozen valid Candidate and control episodes, exactly as the admission recorded them."""
    if record.get("disposition") != ADMISSION_DISPOSITION:
        raise DevelopmentError("the admission record does not admit Candidate #1")
    if record.get("forward_returns_computed") is not False:
        raise DevelopmentError("the admission record is not outcome-free")
    episodes: list[Episode] = []
    excluded: dict[str, int] = {}
    for item in record["episodes"]:
        if "excluded" in item:
            excluded[item["excluded"]] = excluded.get(item["excluded"], 0) + 1
            continue
        t = _epoch(item["T"])
        if datetime.fromtimestamp(t, UTC).year != item["year"]:
            raise DevelopmentError("admission episode year drifted")
        episodes.append(
            Episode(t, item["year"], item["shock_z"], item["sigma_prior_1h"], item["candidate"])
        )
    if [e.t for e in episodes] != sorted({e.t for e in episodes}):
        raise DevelopmentError("admission episodes are not strictly chronological")
    counts = record["counts"]
    if (
        len(episodes) != counts["valid"]
        or sum(e.candidate for e in episodes) != counts["candidate"]
    ):
        raise DevelopmentError("admission episode counts drifted")
    meta = {
        "intended": counts["intended"],
        "valid": counts["valid"],
        "candidate": counts["candidate"],
        "control": counts["control"],
        "admission_exclusions": excluded,
    }
    return episodes, meta


def load_admission(root: Path) -> tuple[list[Episode], dict[str, Any]]:
    path = root / ADMISSION_RECORD_PATH
    if canonical_text_sha256(path) != ADMISSION_CANONICAL_SHA256:
        raise DevelopmentError("the frozen admission record changed")
    return episodes_from_admission(json.loads(path.read_text(encoding="utf-8")))


def identity_checks(root: Path) -> dict[str, bool]:
    """Protocol, freeze decision and admission record are byte-identical to what was frozen."""
    return {
        "PROTOCOL_IDENTITY": canonical_text_sha256(root / PROTOCOL_PATH)
        == PROTOCOL_CANONICAL_SHA256,
        "FREEZE_DECISION_IDENTITY": canonical_text_sha256(root / ADR_PATH) == ADR_CANONICAL_SHA256,
        "ADMISSION_RECORD_IDENTITY": canonical_text_sha256(root / ADMISSION_RECORD_PATH)
        == ADMISSION_CANONICAL_SHA256,
    }


def non_overlapping(candidate_times: Sequence[int]) -> bool:
    """Each primary position exits (T + 4h15m) no later than the next Candidate entry."""
    ordered = sorted(candidate_times)
    return all(
        current + EXIT_OFFSET <= following + PRIMARY_ENTRY_OFFSET
        for current, following in zip(ordered, ordered[1:], strict=False)
    )


# --------------------------------------------------------------------------------------------
# 2. Outcome-blind matching
# --------------------------------------------------------------------------------------------


def _sample_sd(values: Sequence[float]) -> float:
    if len(values) < 2:
        return math.nan
    return float(np.std(np.asarray(values, dtype=float), ddof=1))


def assignment(weights: np.ndarray) -> list[tuple[int, int]]:
    """Exact minimum-weight assignment (Hungarian / Kuhn-Munkres, potentials form).

    Every row of a `rows <= cols` matrix is assigned to a distinct column; a wider-than-tall
    requirement is met by transposing. Ties resolve to the lowest column index.
    """
    rows, cols = weights.shape
    if rows > cols:
        return [(r, c) for c, r in assignment(weights.T)]
    u = np.zeros(rows + 1)
    v = np.zeros(cols + 1)
    owner = np.zeros(cols + 1, dtype=np.int64)  # owner[j] = 1-based row assigned to column j
    way = np.zeros(cols + 1, dtype=np.int64)
    for i in range(1, rows + 1):
        owner[0] = i
        j0 = 0
        minv = np.full(cols + 1, np.inf)
        used = np.zeros(cols + 1, dtype=bool)
        while True:
            used[j0] = True
            i0 = int(owner[j0])
            reduced = weights[i0 - 1] - u[i0] - v[1:]
            free = ~used[1:]
            better = free & (reduced < minv[1:])
            minv[1:][better] = reduced[better]
            way[1:][better] = j0
            candidates = np.where(free, minv[1:], np.inf)
            j1 = int(np.argmin(candidates)) + 1
            delta = float(candidates[j1 - 1])
            assigned = np.flatnonzero(used)
            u[owner[assigned]] += delta
            v[assigned] -= delta
            minv[~used] -= delta
            j0 = j1
            if owner[j0] == 0:
                break
        while True:
            j1 = int(way[j0])
            owner[j0] = owner[j1]
            j0 = j1
            if j0 == 0:
                break
    return sorted((int(owner[j]) - 1, j - 1) for j in range(1, cols + 1) if owner[j])


def _solve(cost: np.ndarray, feasible: np.ndarray) -> tuple[int, float]:
    """Maximum-cardinality, then minimum total squared distance, over a feasibility mask.

    Infeasible edges carry a weight larger than any sum of feasible distances, so a
    minimum-weight full assignment first minimizes infeasible edges (maximizing the feasible
    cardinality) and then the total feasible distance.
    """
    rows, cols = cost.shape
    if rows == 0 or cols == 0 or not feasible.any():
        return 0, 0.0
    big = float(cost[feasible].sum()) + 1.0
    chosen = [(r, c) for r, c in assignment(np.where(feasible, cost, big)) if feasible[r, c]]
    return len(chosen), float(sum(cost[r, c] for r, c in chosen))


def _objective(
    cost: np.ndarray,
    feasible: np.ndarray,
    fixed: Mapping[int, int | None],
) -> tuple[int, float]:
    rows = [i for i in range(cost.shape[0]) if i not in fixed]
    used = {j for j in fixed.values() if j is not None}
    cols = [j for j in range(cost.shape[1]) if j not in used]
    card, dist = _solve(cost[np.ix_(rows, cols)], feasible[np.ix_(rows, cols)])
    for i, j in fixed.items():
        if j is not None:
            card += 1
            dist += float(cost[i, j])
    return card, dist


def _same(a: tuple[int, float], b: tuple[int, float]) -> bool:
    return a[0] == b[0] and abs(a[1] - b[1]) <= MATCH_TIE_TOLERANCE * max(1.0, abs(b[1]))


def match_year(candidates: Sequence[Episode], controls: Sequence[Episode]) -> dict[str, Any]:
    """Frozen one-to-one matching inside one UTC year.

    Priority: (1) maximum cardinality, (2) minimum total squared standardized distance,
    (3) lexicographic by Candidate timestamp then control timestamp: Candidates are fixed in
    timestamp order, each to the earliest-timestamp control that keeps an optimal matching
    (or left unmatched when no optimal matching can match it).
    """
    candidates = sorted(candidates, key=lambda e: e.t)
    controls = sorted(controls, key=lambda e: e.t)
    pooled = [*candidates, *controls]
    stats: dict[str, Any] = {}
    standardized: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for name, getter in (
        ("shock_z", lambda e: e.shock_z),
        ("log_sigma_prior_1h", lambda e: e.log_sigma),
    ):
        values = [getter(e) for e in pooled]
        mean = float(np.mean(values)) if values else math.nan
        sd = _sample_sd(values)
        stats[name] = {"mean": mean, "sd": sd}
        if not (math.isfinite(sd) and sd > 0):
            return {"blocked": f"ZERO_OR_INVALID_SD_{name.upper()}", "pairs": [], "stats": stats}
        standardized[name] = (
            (np.array([getter(e) for e in candidates]) - mean) / sd,
            (np.array([getter(e) for e in controls]) - mean) / sd,
        )
    rows, cols = len(candidates), len(controls)
    cost = np.zeros((rows, cols))
    feasible = np.ones((rows, cols), dtype=bool)
    for cand, ctrl in standardized.values():
        diff = cand[:, None] - ctrl[None, :] if rows and cols else np.zeros((rows, cols))
        feasible &= np.abs(diff) <= CALIPER
        cost += diff * diff
    best = _objective(cost, feasible, {})
    fixed: dict[int, int | None] = {}
    for i in range(rows):
        choice: int | None = None
        used = {j for j in fixed.values() if j is not None}
        for j in range(cols):
            if j in used or not feasible[i, j]:
                continue
            if _same(_objective(cost, feasible, {**fixed, i: j}), best):
                choice = j
                break
        if choice is None and not _same(_objective(cost, feasible, {**fixed, i: None}), best):
            raise DevelopmentError("lexicographic matching lost optimality")  # pragma: no cover
        fixed[i] = choice
    pairs = [
        {
            "candidate": candidates[i].t,
            "control": controls[j].t,
            "squared_distance": float(cost[i, j]),
        }
        for i, j in fixed.items()
        if j is not None
    ]
    return {
        "blocked": None,
        "pairs": pairs,
        "stats": stats,
        "cardinality": best[0],
        "total_squared_distance": best[1],
        "feasible_edges": int(feasible.sum()),
    }


def smd(treated: Sequence[float], control: Sequence[float]) -> float:
    """Austin standardized mean difference: diff of means / sqrt((s_t^2 + s_c^2) / 2)."""
    if not treated or not control:
        return math.nan
    diff = float(np.mean(treated) - np.mean(control))
    var_t = _sample_sd(treated) ** 2 if len(treated) > 1 else 0.0
    var_c = _sample_sd(control) ** 2 if len(control) > 1 else 0.0
    scale = math.sqrt((var_t + var_c) / 2)
    if scale == 0:
        return 0.0 if diff == 0 else math.inf
    return diff / scale


def matching(episodes: Sequence[Episode]) -> dict[str, Any]:
    """Year-stratified matching plus the frozen coverage and balance gates."""
    by_t = {e.t: e for e in episodes}
    years: dict[str, Any] = {}
    pairs: list[tuple[int, int]] = []
    blocked: list[str] = []
    for year in YEARS:
        cands = [e for e in episodes if e.year == year and e.candidate]
        ctrls = [e for e in episodes if e.year == year and not e.candidate]
        result = match_year(cands, ctrls)
        if result["blocked"]:
            blocked.append(f"{year}:{result['blocked']}")
        pairs.extend((p["candidate"], p["control"]) for p in result["pairs"])
        result["candidates"] = len(cands)
        result["controls"] = len(ctrls)
        result["coverage"] = len(result["pairs"]) / len(cands) if cands else 0.0
        years[str(year)] = result
    pairs.sort()
    covariates = {"shock_z": lambda e: e.shock_z, "log_sigma_prior_1h": lambda e: e.log_sigma}
    balance: dict[str, Any] = {"pooled": {}, "by_year": {}}
    for name, getter in covariates.items():
        balance["pooled"][name] = smd(
            [getter(by_t[c]) for c, _ in pairs], [getter(by_t[k]) for _, k in pairs]
        )
    for year in YEARS:
        in_year = [(c, k) for c, k in pairs if by_t[c].year == year]
        balance["by_year"][str(year)] = {
            name: smd([getter(by_t[c]) for c, _ in in_year], [getter(by_t[k]) for _, k in in_year])
            for name, getter in covariates.items()
        }
    total_candidates = sum(e.candidate for e in episodes)
    coverage = len(pairs) / total_candidates if total_candidates else 0.0
    gates = {
        "NO_BLOCKED_YEAR": not blocked,
        "COVERAGE_OVERALL": coverage >= COVERAGE_OVERALL,
        "COVERAGE_EACH_YEAR": all(years[str(y)]["coverage"] >= COVERAGE_YEAR for y in YEARS),
        "SMD_POOLED": all(
            math.isfinite(v) and abs(v) <= SMD_POOLED for v in balance["pooled"].values()
        ),
        "SMD_EACH_YEAR": all(
            math.isfinite(v) and abs(v) <= SMD_YEAR
            for year in balance["by_year"].values()
            for v in year.values()
        ),
    }
    return {
        "pairs": pairs,
        "years": years,
        "blocked_years": blocked,
        "coverage": coverage,
        "balance": balance,
        "gates": gates,
    }


# --------------------------------------------------------------------------------------------
# 3. Execution semantics
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class MinuteBar:
    open: float
    high: float
    low: float
    close: float


PriceSource = Callable[[int], MinuteBar | None]
"""Maps a 1m bar open time (epoch seconds) to its valid bar, or None when unavailable."""


def trade_accounting(entry_raw: float, exit_raw: float, costs: CostModel) -> dict[str, float]:
    """`BACKTEST_ENGINE_V2` / `COST_MODEL_V1` accounting, expressed per initial spot notional.

    Entry friction raises the long entry, exit friction lowers the long exit, each fee applies to
    its effective notional, and every component is reported in bp of the raw entry price.
    """
    bps = Decimal(10_000)
    entry = Decimal(repr(entry_raw))
    exit_ = Decimal(repr(exit_raw))
    entry_effective = entry * (bps + costs.entry_friction_bps) / bps
    entry_fee = entry_effective * costs.entry_fee_bps / bps
    exit_effective = exit_ * (bps - costs.exit_friction_bps) / bps
    exit_fee = exit_effective * costs.exit_fee_bps / bps
    gross = exit_ - entry
    net = exit_effective - entry_effective - entry_fee - exit_fee
    friction = (entry_effective - entry) + (exit_ - exit_effective)

    def to_bp(value: Decimal) -> float:
        return float(value / entry * bps)

    return {
        "gross_bp": to_bp(gross),
        "fees_bp": to_bp(entry_fee + exit_fee),
        "friction_bp": to_bp(friction),
        "net_bp": to_bp(net),
    }


def execute(
    t: int, prices: PriceSource, costs: CostModel, entry_offset: int = PRIMARY_ENTRY_OFFSET
) -> dict[str, Any]:
    """One fixed-notional LONG from the exact entry open to the exact exit open."""
    entry_time, exit_time = t + entry_offset, t + EXIT_OFFSET
    record: dict[str, Any] = {"T": t, "entry_time": entry_time, "exit_time": exit_time}
    if entry_time > DEVELOPMENT_LAST_MINUTE:
        return {**record, "scorable": False, "reason": ENTRY_AFTER_DEVELOPMENT_CUTOFF}
    if exit_time > DEVELOPMENT_LAST_MINUTE:
        return {**record, "scorable": False, "reason": EXIT_AFTER_DEVELOPMENT_CUTOFF}
    entry_bar = prices(entry_time)
    if entry_bar is None or not (math.isfinite(entry_bar.open) and entry_bar.open > 0):
        return {**record, "scorable": False, "reason": ENTRY_MINUTE_UNAVAILABLE}
    exit_bar = prices(exit_time)
    if exit_bar is None or not (math.isfinite(exit_bar.open) and exit_bar.open > 0):
        return {**record, "scorable": False, "reason": EXIT_MINUTE_UNAVAILABLE}
    lows, highs, missing = [], [], 0
    for minute in range(entry_time, exit_time, MINUTE):
        bar = prices(minute)
        if bar is None:
            missing += 1
            continue
        lows.append(bar.low)
        highs.append(bar.high)
    accounting = trade_accounting(entry_bar.open, exit_bar.open, costs)
    return {
        **record,
        "scorable": True,
        "reason": None,
        "entry_raw": entry_bar.open,
        "exit_raw": exit_bar.open,
        **accounting,
        "holding_minutes": (exit_time - entry_time) // MINUTE,
        "mae_bp": (min(lows) / entry_bar.open - 1) * 1e4 if lows else None,
        "mfe_bp": (max(highs) / entry_bar.open - 1) * 1e4 if highs else None,
        "path_minutes_missing": missing,
        "cost_profile": costs.profile,
    }


# --------------------------------------------------------------------------------------------
# 4-5. Economic metrics and dependence-aware uncertainty
# --------------------------------------------------------------------------------------------


def month_key(t: int) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m")


def expected_shortfall(values: Sequence[float], level: float = ES_LEVEL) -> float:
    """Mean of the worst ceil(level * N) observations (lower tail, bp)."""
    if not values:
        return math.nan
    k = max(1, math.ceil(level * len(values)))
    return float(np.mean(sorted(values)[:k]))


def max_drawdown(values_in_time_order: Sequence[float]) -> float:
    """Largest peak-to-trough decline of the fixed-notional cumulative sum, starting at zero."""
    peak = cumulative = worst = 0.0
    for value in values_in_time_order:
        cumulative += value
        peak = max(peak, cumulative)
        worst = max(worst, peak - cumulative)
    return worst


def _cluster_meat(residuals: np.ndarray, labels: Sequence[Any]) -> tuple[float, int]:
    sums: dict[Any, float] = {}
    for value, label in zip(residuals, labels, strict=True):
        sums[label] = sums.get(label, 0.0) + float(value)
    return sum(v * v for v in sums.values()), len(sums)


def cluster_se(values: Sequence[float], *dimensions: Sequence[Any]) -> dict[str, Any]:
    """Cluster-robust SE of a mean: one-way, or two-way (Cameron-Gelbach-Miller).

    Each variance component carries its own finite-cluster correction G/(G-1) (with K = 1 the
    (N-1)/(N-K) factor is 1). Two-way: V = V_A + V_B - V_(A∩B). Undefined (fewer than two clusters
    in any dimension, or a non-positive / non-finite variance) returns `valid: False`.
    """
    x = np.asarray(values, dtype=float)
    n = x.shape[0]
    if n < 2 or not np.all(np.isfinite(x)):
        return {
            "valid": False,
            "se": None,
            "clusters": None,
            "reason": "INSUFFICIENT_OR_NON_FINITE",
        }
    residuals = x - x.mean()
    components: list[tuple[list[Any], int]] = [(list(d), 1) for d in dimensions]
    if len(dimensions) == 2:
        components.append((list(zip(dimensions[0], dimensions[1], strict=True)), -1))
    elif len(dimensions) != 1:
        raise DevelopmentError("only one-way or two-way clustering is declared")
    variance = 0.0
    counts: list[int] = []
    for labels, sign in components:
        meat, groups = _cluster_meat(residuals, labels)
        if groups < 2:
            return {
                "valid": False,
                "se": None,
                "clusters": groups,
                "reason": "FEWER_THAN_TWO_CLUSTERS",
            }
        counts.append(groups)
        variance += sign * (groups / (groups - 1)) * meat / (n * n)
    if not (math.isfinite(variance) and variance > 0):
        return {"valid": False, "se": None, "clusters": counts, "reason": "NON_POSITIVE_VARIANCE"}
    from scipy.stats import t as student_t

    se = math.sqrt(variance)
    df = min(counts[: len(dimensions)]) - 1
    critical = float(student_t.ppf(1 - (1 - INTERVAL_MASS) / 2, df))
    mean = float(x.mean())
    return {
        "valid": True,
        "se": se,
        "clusters": counts,
        "df": df,
        "mean": mean,
        "ci95": [mean - critical * se, mean + critical * se],
        "reason": None,
    }


def _mean(values: Sequence[float]) -> float:
    return float(np.mean(values)) if len(values) else math.nan


def _by_year(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for year in YEARS:
        values = [r[key] for r in rows if r["year"] == year]
        out[str(year)] = _mean(values)
    return out


def _year_sds(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, float]:
    return {str(y): _sample_sd([r[key] for r in rows if r["year"] == y]) for y in YEARS}


def _leave_one_year_out(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, float]:
    return {str(y): _mean([r[key] for r in rows if r["year"] != y]) for y in YEARS}


def required_n(planning_sd: float, mesi: float) -> float:
    if not (math.isfinite(planning_sd) and planning_sd >= 0):
        return math.inf
    normal = NormalDist()
    z = normal.inv_cdf(1 - ALPHA_ONE_SIDED) + normal.inv_cdf(TARGET_POWER)
    return float(math.ceil((z * planning_sd / mesi) ** 2))


def planning_sd(raw_sd: float, se: dict[str, Any], n: int, year_sds: Mapping[str, float]) -> float:
    if not se["valid"] or not math.isfinite(raw_sd):
        return math.nan
    finite = [v for v in year_sds.values() if math.isfinite(v)]
    return max([raw_sd, se["se"] * math.sqrt(n), *finite])


# --------------------------------------------------------------------------------------------
# 6-7. Evaluation and adjudication
# --------------------------------------------------------------------------------------------


def adjudicate(stages: Mapping[str, Mapping[str, bool]]) -> str:
    """First failing stage in the frozen order decides; later stages can never override it."""
    for disposition, stage in (
        (INVALID_EXECUTION, "integrity"),
        (BLOCKED, "support"),
        (REJECTED, "development"),
        (INCONCLUSIVE, "promotion_feasibility"),
    ):
        if not all(stages[stage].values()):
            return disposition
    return PROMOTION_ELIGIBLE


def _trade_rows(
    episodes: Iterable[Episode], prices: PriceSource, costs: CostModel, entry_offset: int
) -> dict[int, dict[str, Any]]:
    return {e.t: {**execute(e.t, prices, costs, entry_offset), "year": e.year} for e in episodes}


def evaluate(
    episodes: Sequence[Episode],
    prices: PriceSource,
    integrity: Mapping[str, bool],
) -> dict[str, Any]:
    """The complete frozen Development evaluation for one price source."""
    matched = matching(episodes)
    candidates = [e for e in episodes if e.candidate]
    pairs = matched["pairs"]
    needed = candidates + [e for e in episodes if e.t in {k for _, k in pairs}]

    primary = _trade_rows(needed, prices, PRIMARY_COSTS, PRIMARY_ENTRY_OFFSET)
    stress = _trade_rows(needed, prices, STRESS_COSTS, PRIMARY_ENTRY_OFFSET)
    delay = _trade_rows(needed, prices, PRIMARY_COSTS, DELAY_ENTRY_OFFSET)

    def candidate_rows(book: Mapping[int, dict[str, Any]]) -> list[dict[str, Any]]:
        return [book[e.t] for e in candidates if book[e.t]["scorable"]]

    def pair_rows(book: Mapping[int, dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for c, k in pairs:
            if book[c]["scorable"] and book[k]["scorable"]:
                rows.append(
                    {
                        "candidate": c,
                        "control": k,
                        "year": book[c]["year"],
                        "candidate_net_bp": book[c]["net_bp"],
                        "control_net_bp": book[k]["net_bp"],
                        "diff_bp": book[c]["net_bp"] - book[k]["net_bp"],
                        "candidate_month": month_key(c),
                        "control_month": month_key(k),
                    }
                )
        return rows

    cand = candidate_rows(primary)
    pair = pair_rows(primary)
    per_year_scorable = {str(y): sum(r["year"] == y for r in cand) for y in YEARS}
    n_year_min = min(per_year_scorable.values())
    unscorable: dict[str, int] = {}
    for e in candidates:
        reason = primary[e.t]["reason"]
        if reason:
            unscorable[reason] = unscorable.get(reason, 0) + 1

    support = {
        **{f"MATCHING_{k}": v for k, v in matched["gates"].items()},
        "SCORABLE_CANDIDATES_95": bool(candidates)
        and len(cand) / len(candidates) >= SCORABLE_CANDIDATES,
        "SCORABLE_PAIRS_95": bool(pairs) and len(pair) / len(pairs) >= SCORABLE_PAIRS,
        "SCORABLE_CANDIDATES_25_EACH_YEAR": n_year_min >= MIN_SCORABLE_PER_YEAR,
    }

    nets = [r["net_bp"] for r in cand]
    diffs = [r["diff_bp"] for r in pair]
    abs_net = _mean(nets)
    inc_net = _mean(diffs)
    chronological = [r["net_bp"] for r in sorted(cand, key=lambda r: r["T"])]
    drawdown = max_drawdown(chronological)
    es_candidate = expected_shortfall([r["candidate_net_bp"] for r in pair])
    es_control = expected_shortfall([r["control_net_bp"] for r in pair])
    year_abs = _by_year(cand, "net_bp")
    year_inc = _by_year(pair, "diff_bp")
    ranked = sorted(cand, key=lambda r: (-r["net_bp"], r["T"]))
    top3 = {r["T"] for r in ranked[:TOP_REMOVED]}
    abs_without_top3 = _mean([r["net_bp"] for r in cand if r["T"] not in top3])
    inc_without_top3 = _mean([r["diff_bp"] for r in pair if r["candidate"] not in top3])
    stress_cand = candidate_rows(stress)
    delay_cand, delay_pair = candidate_rows(delay), pair_rows(delay)
    stress_abs = _mean([r["net_bp"] for r in stress_cand])
    delay_abs = _mean([r["net_bp"] for r in delay_cand])
    delay_inc = _mean([r["diff_bp"] for r in delay_pair])

    def positive(value: float) -> bool:
        return math.isfinite(value) and value > 0

    development = {
        "ABS_NET_BP_AT_LEAST_25": math.isfinite(abs_net) and abs_net >= ABS_MESI_BP,
        "INCREMENTAL_NET_BP_AT_LEAST_20": math.isfinite(inc_net) and inc_net >= INC_MESI_BP,
        "ANNUAL_CONTRIBUTION_AT_LEAST_500": math.isfinite(abs_net)
        and n_year_min * abs_net >= ANNUAL_MIN_BP,
        "ES10_NOT_WORSE_THAN_CONTROL_BY_25": math.isfinite(es_candidate)
        and math.isfinite(es_control)
        and es_candidate >= es_control - ES_TOLERANCE_BP,
        "MAX_DRAWDOWN_AT_MOST_1000": drawdown <= MAX_DRAWDOWN_BP,
        "ABS_POSITIVE_IN_2_OF_3_YEARS": sum(positive(v) for v in year_abs.values())
        >= POSITIVE_YEARS,
        "INCREMENTAL_POSITIVE_IN_2_OF_3_YEARS": sum(positive(v) for v in year_inc.values())
        >= POSITIVE_YEARS,
        "ABS_POSITIVE_WITHOUT_TOP_3": positive(abs_without_top3),
        "INCREMENTAL_POSITIVE_WITHOUT_TOP_3_PAIRS": positive(inc_without_top3),
        "COST_STRESS_ABS_POSITIVE": positive(stress_abs),
        "DELAY_STRESS_ABS_POSITIVE": positive(delay_abs),
        "DELAY_STRESS_INCREMENTAL_POSITIVE": positive(delay_inc),
    }

    abs_se = cluster_se(nets, [month_key(r["T"]) for r in cand])
    inc_se = cluster_se(
        diffs, [r["candidate_month"] for r in pair], [r["control_month"] for r in pair]
    )
    abs_raw_sd, inc_raw_sd = _sample_sd(nets), _sample_sd(diffs)
    abs_year_sd, inc_year_sd = _year_sds(cand, "net_bp"), _year_sds(pair, "diff_bp")
    abs_plan = planning_sd(abs_raw_sd, abs_se, len(nets), abs_year_sd)
    inc_plan = planning_sd(inc_raw_sd, inc_se, len(diffs), inc_year_sd)
    abs_required = required_n(abs_plan, ABS_MESI_BP)
    inc_required = required_n(inc_plan, INC_MESI_BP)
    feasibility = {
        "ABS_UNCERTAINTY_VALID": bool(abs_se["valid"]),
        "INCREMENTAL_UNCERTAINTY_VALID": bool(inc_se["valid"]),
        "ABS_REQUIRED_N_WITHIN_12M_ARRIVALS": abs_required <= n_year_min,
        "INCREMENTAL_REQUIRED_N_WITHIN_12M_ARRIVALS": inc_required <= n_year_min,
    }
    stages = {
        "integrity": {
            **integrity,
            "NO_OVERLAPPING_PRIMARY_POSITIONS": non_overlapping([e.t for e in candidates]),
        },
        "support": support,
        "development": development,
        "promotion_feasibility": feasibility,
    }
    winners = sorted((r["net_bp"] for r in cand if r["net_bp"] > 0), reverse=True)
    total_positive = sum(winners)
    occupied = sum(r["holding_minutes"] for r in cand)
    interval_minutes = (INTERVAL_END - INTERVAL_START) // MINUTE
    return {
        "version": VERSION,
        "disposition": adjudicate(stages),
        "stages": stages,
        "matching": {
            "pairs": [{"candidate": c, "control": k} for c, k in pairs],
            "coverage": matched["coverage"],
            "years": matched["years"],
            "balance": matched["balance"],
        },
        "counts": {
            "candidates": len(candidates),
            "matched_pairs": len(pairs),
            "scorable_candidates": len(cand),
            "scorable_pairs": len(pair),
            "scorable_candidates_by_year": per_year_scorable,
            "n_year_min": n_year_min,
            "candidate_unscorable_reasons": unscorable,
        },
        "primary": {
            "ABS_NET_BP": abs_net,
            "INCREMENTAL_NET_BP": inc_net,
            "mean_gross_bp": _mean([r["gross_bp"] for r in cand]),
            "mean_fees_bp": _mean([r["fees_bp"] for r in cand]),
            "mean_friction_bp": _mean([r["friction_bp"] for r in cand]),
            "break_even_all_in_cost_bp": _mean([r["gross_bp"] for r in cand]),
            "conservative_annual_contribution_bp": n_year_min * abs_net,
            "yearly_abs_net_bp": year_abs,
            "yearly_incremental_bp": year_inc,
            "es10_candidate_matched_bp": es_candidate,
            "es10_control_matched_bp": es_control,
            "max_drawdown_bp": drawdown,
            "cumulative_net_bp": float(sum(chronological)),
            "win_rate": _mean([float(v > 0) for v in nets]),
            "median_net_bp": float(np.median(nets)) if nets else math.nan,
            "occupied_minutes": occupied,
            "occupied_fraction": occupied / interval_minutes,
            "net_bp_per_occupied_hour": float(sum(nets)) / (occupied / 60) if occupied else None,
            "top_winner_contribution_bp": {str(k): float(sum(winners[:k])) for k in (1, 3, 5)},
            "top_winner_share_of_positive_bp": {
                str(k): float(sum(winners[:k]) / total_positive) if total_positive else None
                for k in (1, 3, 5)
            },
            "abs_net_without_top3_bp": abs_without_top3,
            "incremental_without_top3_pairs_bp": inc_without_top3,
        },
        "robustness": {
            "cost_stress_abs_net_bp": stress_abs,
            "delay_stress_abs_net_bp": delay_abs,
            "delay_stress_incremental_bp": delay_inc,
        },
        "uncertainty": {
            "abs_one_way_month": abs_se,
            "incremental_two_way_months": inc_se,
            "abs_raw_sd": abs_raw_sd,
            "incremental_raw_sd": inc_raw_sd,
            "abs_by_year": year_abs,
            "incremental_by_year": year_inc,
            "abs_leave_one_year_out": _leave_one_year_out(cand, "net_bp"),
            "incremental_leave_one_year_out": _leave_one_year_out(pair, "diff_bp"),
        },
        "prospective_detectability": {
            "arrivals_12m": n_year_min,
            "abs_planning_sd": abs_plan,
            "abs_required_n": abs_required,
            "incremental_planning_sd": inc_plan,
            "incremental_required_n": inc_required,
            "alpha_one_sided_each": ALPHA_ONE_SIDED,
            "target_power": TARGET_POWER,
            "mesi_bp": {"abs": ABS_MESI_BP, "incremental": INC_MESI_BP},
        },
        "trades": {
            "primary": [primary[t] for t in sorted(primary)],
            "cost_stress": [stress[t] for t in sorted(stress)],
            "delay_stress": [delay[t] for t in sorted(delay)],
        },
    }


def canonical_spot_prices(root: Path) -> PriceSource:  # pragma: no cover - authorized run only
    """Exact valid 1m bars from the canonical `BTCUSDT-SPOT-1M-DEV-v1` spot artifact.

    Reads only 2022-01-01 .. the development cutoff. Only the authorized Development execution
    may call this: it exposes the forward execution bars.
    """
    import pyarrow.dataset as ds

    start = datetime.fromtimestamp(INTERVAL_START, UTC)
    end = datetime.fromtimestamp(DEVELOPMENT_LAST_MINUTE, UTC)
    table = ds.dataset(root / "data/canonical/BTCUSDT-1m.parquet", format="parquet").to_table(
        columns=["open_time", "open", "high", "low", "close"],
        filter=(ds.field("open_time") >= start) & (ds.field("open_time") <= end),
    )
    bars: dict[int, MinuteBar] = {}
    for row in table.to_pylist():
        values = (row["open"], row["high"], row["low"], row["close"])
        if all(math.isfinite(v) and v > 0 for v in values) and row["high"] >= row["low"]:
            bars[int(row["open_time"].timestamp())] = MinuteBar(*values)
    return bars.get
