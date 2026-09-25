"""Candidate #1 frozen admission calculation (`CANDIDATE_1_FROZEN_ADMISSION_V1`).

Implements `research/protocols/CANDIDATE-1-FROZEN-ADMISSION-V1.md` exactly. Every quantity is
known at or before the event hour `T`; nothing after `T` is read. No forward return, label,
outcome or model exists in this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import NormalDist
from typing import Any

import numpy as np

VERSION = "CANDIDATE_1_FROZEN_ADMISSION_V1"
PROTOCOL_PATH = "research/protocols/CANDIDATE-1-FROZEN-ADMISSION-V1.md"
RECORD_PATH = "reports/validation/CANDIDATE-1-FROZEN-ADMISSION-V1.json"

HOUR = 3600
SHOCK_HOURS = 4
VOL_RETURNS = 168
Z_THRESHOLD = -2.0
COOLDOWN_HOURS = 4
DECISION_DELAY_SECONDS = 15 * 60
OI_MAX_AGE_SECONDS = 600
OI_ADMITTED_START = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp())
DOMAIN_START = OI_ADMITTED_START + SHOCK_HOURS * HOUR  # 2022-01-01T04:00Z
DOMAIN_END = int(datetime(2024, 12, 31, 23, tzinfo=UTC).timestamp())
YEARS = (2022, 2023, 2024)
SOURCE_COVERAGE_MINIMUM = 0.95
MINIMUM_COMMON_SUPPORT_YEARS = 2
ALPHA_ONE_SIDED = 0.05
TARGET_POWER = 0.80
MAXIMUM_REQUIRED_EFFECT = 0.50
SHOCK_BANDS = ((-math.inf, -4.0), (-4.0, -3.0), (-3.0, -2.0))  # (lower, upper] each
OI_JUMP = 0.05
SYNC_FLAG_BPS = 50.0

PERP_CLOSE_MISSING = "PERP_CLOSE_MISSING"
OI_NO_RECORD = "OI_NO_RECORD"
OI_OUTSIDE_ADMITTED_INTERVAL = "OI_OUTSIDE_ADMITTED_INTERVAL"
OI_STALE = "OI_STALE"
OI_NON_POSITIVE = "OI_NON_POSITIVE"
EXCLUSION_REASONS = (
    PERP_CLOSE_MISSING,
    OI_NO_RECORD,
    OI_OUTSIDE_ADMITTED_INTERVAL,
    OI_STALE,
    OI_NON_POSITIVE,
)
ADMITTED = "CANDIDATE_1_ADMITTED_FOR_PROTOCOL_DESIGN"
CLOSED = "CANDIDATE_1_CLOSED_CURRENT_ALLOCATION_SUPPORT_OR_FEASIBILITY"


@dataclass(frozen=True)
class HourlyInputs:
    """Aligned hourly grid. `closes[i]` is the close of the completed minute ending at `instants[i]`."""

    instants: np.ndarray  # int64 epoch seconds, consecutive hours
    spot_close: np.ndarray  # float64, NaN when not valid
    perp_close: np.ndarray  # float64, NaN when not valid
    oi_times: np.ndarray  # int64 epoch seconds, strictly increasing
    oi_quantity: np.ndarray  # float64


def _year(epoch: int) -> int:
    return datetime.fromtimestamp(epoch, UTC).year


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def shock_z(spot_close: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """`shock_z` and `sigma_prior_1h` per hour; NaN wherever any required close is missing."""
    log_close = np.log(spot_close)
    hours = log_close.shape[0]
    r1 = np.full(hours, np.nan)
    r1[1:] = log_close[1:] - log_close[:-1]
    r4 = np.full(hours, np.nan)
    r4[SHOCK_HOURS:] = log_close[SHOCK_HOURS:] - log_close[:-SHOCK_HOURS]
    finite = np.isfinite(r1)
    squares = np.where(finite, r1 * r1, 0.0)
    csum = np.concatenate(([0.0], np.cumsum(squares)))
    ccount = np.concatenate(([0], np.cumsum(finite.astype(np.int64))))
    sigma = np.full(hours, np.nan)
    # Returns ending at T-4h: r1[i-4], r1[i-5], ..., r1[i-4-167].
    for_index = np.arange(hours)
    last = for_index - SHOCK_HOURS  # inclusive
    first = last - VOL_RETURNS + 1  # inclusive; needs close[first-1]
    ok = first >= 1
    idx = for_index[ok]
    lo, hi = first[ok], last[ok] + 1
    count = ccount[hi] - ccount[lo]
    total = csum[hi] - csum[lo]
    full = count == VOL_RETURNS
    values = np.where(full, np.sqrt(np.where(full, total, 0.0) / VOL_RETURNS), np.nan)
    sigma[idx] = values
    sigma = np.where(sigma > 0, sigma, np.nan)
    z = r4 / (sigma * math.sqrt(SHOCK_HOURS))
    return z, sigma


def triggers(z: np.ndarray) -> tuple[list[int], int]:
    """First-crossing triggers with a 4-hour suppression, and the undetermined-crossing count."""
    events: list[int] = []
    undetermined = 0
    next_allowed = -1
    for i in range(1, z.shape[0]):
        if not (np.isfinite(z[i]) and z[i] <= Z_THRESHOLD):
            continue
        if not np.isfinite(z[i - 1]):
            undetermined += 1
            continue
        if z[i - 1] <= Z_THRESHOLD:
            continue
        if i < next_allowed:
            continue
        events.append(i)
        next_allowed = i + COOLDOWN_HOURS
    return events, undetermined


def oi_state(inputs: HourlyInputs, instant: int) -> tuple[float | None, str | None, int | None]:
    """OI quantity as of `instant` (largest `create_time <= instant`) or the exclusion reason."""
    position = int(np.searchsorted(inputs.oi_times, instant, side="right")) - 1
    if position < 0:
        return None, OI_NO_RECORD, None
    stamped = int(inputs.oi_times[position])
    if stamped < OI_ADMITTED_START:
        return None, OI_OUTSIDE_ADMITTED_INTERVAL, stamped
    if instant - stamped > OI_MAX_AGE_SECONDS:
        return None, OI_STALE, stamped
    quantity = float(inputs.oi_quantity[position])
    if not (math.isfinite(quantity) and quantity > 0):
        return None, OI_NON_POSITIVE, stamped
    return quantity, None, stamped


def _describe(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values)
    return {
        "min": round(float(array.min()), 6),
        "median": round(float(np.median(array)), 6),
        "max": round(float(array.max()), 6),
    }


def _band(z: float) -> str:
    for lower, upper in SHOCK_BANDS:
        if lower < z <= upper:
            return f"({lower},{upper}]"
    raise ValueError(z)


def required_standardized_effect(n: int) -> float:
    if n <= 0:
        return math.inf
    normal = NormalDist()
    return (normal.inv_cdf(1 - ALPHA_ONE_SIDED) + normal.inv_cdf(TARGET_POWER)) / math.sqrt(n)


def admission(inputs: HourlyInputs) -> dict[str, Any]:
    """The single frozen admission calculation."""
    instants = inputs.instants
    z, sigma = shock_z(inputs.spot_close)
    all_events, undetermined_all = triggers(z)
    in_domain = [i for i in all_events if DOMAIN_START <= int(instants[i]) <= DOMAIN_END]
    domain_hours = (instants >= DOMAIN_START) & (instants <= DOMAIN_END)
    spot_defined = domain_hours & np.isfinite(z)
    rel = np.log(inputs.perp_close / inputs.spot_close)

    exclusions = {reason: 0 for reason in EXCLUSION_REASONS}
    endpoint_reasons: dict[str, int] = {}
    episodes: list[dict[str, Any]] = []
    for i in in_domain:
        t = int(instants[i])
        lag = i - SHOCK_HOURS
        record: dict[str, Any] = {
            "T": _iso(t),
            "year": _year(t),
            "shock_z": float(z[i]),
            "sigma_prior_1h": float(sigma[i]),
        }
        reason = None
        if not (np.isfinite(inputs.perp_close[i]) and np.isfinite(inputs.perp_close[lag])):
            reason = PERP_CLOSE_MISSING
        oi_now, oi_reason_now, stamp_now = oi_state(inputs, t)
        oi_then, oi_reason_then, _ = oi_state(inputs, t - SHOCK_HOURS * HOUR)
        for label, why in (("T", oi_reason_now), ("T-4h", oi_reason_then)):
            if why is not None:
                key = f"{label}:{why}"
                endpoint_reasons[key] = endpoint_reasons.get(key, 0) + 1
        if reason is None:
            reason = oi_reason_now or oi_reason_then
        if reason is not None:
            exclusions[reason] += 1
            record["excluded"] = reason
            episodes.append(record)
            continue
        assert oi_now is not None and oi_then is not None
        assert stamp_now is not None and t + DECISION_DELAY_SECONDS > stamp_now
        d_oi = math.log(oi_now / oi_then)
        d_rel = float(rel[i] - rel[lag])
        record.update(
            {
                "oi_log_change_4h": d_oi,
                "relative_price_change_4h": d_rel,
                "abs_rel_bps_T": abs(float(rel[i])) * 1e4,
                "abs_rel_bps_T_minus_4h": abs(float(rel[lag])) * 1e4,
                "candidate": d_oi < 0 and d_rel < 0,
            }
        )
        # OI window diagnostics over (T-4h, T].
        window = (inputs.oi_times > t - SHOCK_HOURS * HOUR) & (inputs.oi_times <= t)
        times = inputs.oi_times[window]
        quantities = inputs.oi_quantity[window]
        expected = SHOCK_HOURS * HOUR // 300
        record["oi_window_gap"] = int(times.shape[0]) < expected
        positive = np.isfinite(quantities) & (quantities > 0)
        jumps = 0
        if times.shape[0] > 1:
            step = np.diff(np.log(np.where(positive, quantities, np.nan)))
            consecutive = np.diff(times) == 300
            jumps = int(np.count_nonzero(consecutive & (np.abs(np.nan_to_num(step)) > OI_JUMP)))
        record["oi_window_jumps"] = jumps
        record["oi_window_non_positive"] = int(np.count_nonzero(~positive))
        episodes.append(record)

    valid = [e for e in episodes if "excluded" not in e]
    candidates = [e for e in valid if e["candidate"]]
    controls = [e for e in valid if not e["candidate"]]
    intended = len(episodes)
    coverage = len(valid) / intended if intended else 0.0

    by_year = {
        str(y): {
            "intended": sum(e["year"] == y for e in episodes),
            "valid": sum(e["year"] == y for e in valid),
            "candidate": sum(e["year"] == y for e in candidates),
            "control": sum(e["year"] == y for e in controls),
        }
        for y in YEARS
    }
    by_band = {
        f"({lo},{hi}]": {
            "candidate": sum(_band(e["shock_z"]) == f"({lo},{hi}]" for e in candidates),
            "control": sum(_band(e["shock_z"]) == f"({lo},{hi}]" for e in controls),
        }
        for lo, hi in SHOCK_BANDS
    }
    sigmas = sorted(e["sigma_prior_1h"] for e in valid)
    terciles: list[float] = (
        [float(np.quantile(sigmas, 1 / 3)), float(np.quantile(sigmas, 2 / 3))] if sigmas else []
    )

    def tercile(value: float) -> str:
        if value <= terciles[0]:
            return "T1_LOW"
        return "T2_MID" if value <= terciles[1] else "T3_HIGH"

    by_vol = (
        {
            name: {
                "candidate": sum(tercile(e["sigma_prior_1h"]) == name for e in candidates),
                "control": sum(tercile(e["sigma_prior_1h"]) == name for e in controls),
            }
            for name in ("T1_LOW", "T2_MID", "T3_HIGH")
        }
        if terciles
        else {}
    )

    years_used = [y for y in YEARS if by_year[str(y)]["candidate"] and by_year[str(y)]["control"]]
    used_c = [e for e in candidates if e["year"] in years_used]
    used_k = [e for e in controls if e["year"] in years_used]

    def overlap(key: str) -> dict[str, Any]:
        if not used_c or not used_k:
            return {"overlap": False, "interval": None}
        lo = max(min(e[key] for e in used_c), min(e[key] for e in used_k))
        hi = min(max(e[key] for e in used_c), max(e[key] for e in used_k))
        return {"overlap": lo <= hi, "interval": [round(lo, 6), round(hi, 6)] if lo <= hi else None}

    shock_overlap, vol_overlap = overlap("shock_z"), overlap("sigma_prior_1h")
    common_support = (
        len(years_used) >= MINIMUM_COMMON_SUPPORT_YEARS
        and shock_overlap["overlap"]
        and vol_overlap["overlap"]
    )
    n_12m = min(by_year[str(y)]["candidate"] for y in YEARS)
    required = required_standardized_effect(n_12m)
    gates = {
        "AVAILABILITY_ASSUMPTION": True,
        "SOURCE_RELIABILITY": intended > 0 and coverage >= SOURCE_COVERAGE_MINIMUM,
        "COMMON_SUPPORT": bool(common_support),
        "DETECTABILITY_12M": required <= MAXIMUM_REQUIRED_EFFECT,
    }
    admitted = all(gates.values())
    rel_abs = [e["abs_rel_bps_T"] for e in valid] + [e["abs_rel_bps_T_minus_4h"] for e in valid]
    return {
        "version": VERSION,
        "protocol": PROTOCOL_PATH,
        "forward_returns_computed": False,
        "labels_or_outcomes_computed": False,
        "models_fitted": 0,
        "post_cutoff_data_accessed": False,
        "sealed_queries": 0,
        "support_calculations_executed": 1,
        "domain": [_iso(DOMAIN_START), _iso(DOMAIN_END)],
        "decision_delay_minutes": DECISION_DELAY_SECONDS // 60,
        "source_coverage": {
            "domain_hours": int(domain_hours.sum()),
            "domain_hours_shock_z_defined": int(spot_defined.sum()),
            "spot_crossing_undetermined_hours_full_grid": undetermined_all,
            "intended_episodes": intended,
            "valid_synchronized_episodes": len(valid),
            "coverage": round(coverage, 6),
            "exclusion_reasons": exclusions,
            "oi_endpoint_unavailability": dict(sorted(endpoint_reasons.items())),
        },
        "oi_window_diagnostics_valid_episodes": {
            "episodes_with_window_gap": sum(e["oi_window_gap"] for e in valid),
            "episodes_with_5m_abs_log_jump_gt_0_05": sum(e["oi_window_jumps"] > 0 for e in valid),
            "episodes_with_non_positive_window_record": sum(
                e["oi_window_non_positive"] > 0 for e in valid
            ),
        },
        "synchronization_valid_episodes": {
            "abs_log_perp_over_spot_bps": _describe(rel_abs),
            "endpoints_above_50bp": sum(v > SYNC_FLAG_BPS for v in rel_abs),
        },
        "counts": {
            "intended": intended,
            "valid": len(valid),
            "candidate": len(candidates),
            "control": len(controls),
        },
        "by_year": by_year,
        "by_shock_band": by_band,
        "prior_vol_terciles": [round(v, 8) for v in terciles],
        "by_prior_vol_tercile": by_vol,
        "descriptors": {
            "candidate": {
                "shock_z": _describe([e["shock_z"] for e in candidates]),
                "sigma_prior_1h": _describe([e["sigma_prior_1h"] for e in candidates]),
            },
            "control": {
                "shock_z": _describe([e["shock_z"] for e in controls]),
                "sigma_prior_1h": _describe([e["sigma_prior_1h"] for e in controls]),
            },
        },
        "common_support": {
            "years_used": years_used,
            "shock_z": shock_overlap,
            "sigma_prior_1h": vol_overlap,
            "pass": bool(common_support),
        },
        "detectability_12m": {
            "method": "N_12M = MIN_ANNUAL_VALID_CANDIDATE_EPISODES_2022_2024; "
            "REQUIRED = (Z_0.95 + Z_0.80) / SQRT(N_12M); OPTIMISTIC_INDEPENDENT_EPISODES",
            "n_12m": n_12m,
            "alpha_one_sided": ALPHA_ONE_SIDED,
            "target_power": TARGET_POWER,
            "required_standardized_effect": (
                round(required, 6) if math.isfinite(required) else "INFINITE"
            ),
            "maximum_allowed": MAXIMUM_REQUIRED_EFFECT,
            "is_mesi_or_expected_effect": False,
        },
        "gates": gates,
        "disposition": ADMITTED if admitted else CLOSED,
        "project_state": "CANDIDATE_1_PROTOCOL_DESIGN_PENDING"
        if admitted
        else "STRONG_STOP_PENDING_ASTRA",
        "episodes": episodes,
    }
