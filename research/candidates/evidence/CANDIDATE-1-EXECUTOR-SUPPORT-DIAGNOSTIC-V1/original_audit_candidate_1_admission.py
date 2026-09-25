"""Candidate #1 source/timing/support admission audit (GOVERNANCE-TRANSITION-AND-CANDIDATE-ADMISSION-V1).

Positioning-conditioned recovery after a sharp BTC spot sell-off. This audit decides only
whether the already-manifested sources can support protocol design. It computes **no forward
return, no label, no outcome and no model**: every quantity below is known at or before its
decision instant `T`. Support definitions are declared here, before the audit runs, and are
diagnostic only; they are not the candidate's frozen eligibility rule.

Usage:
    python scripts/audit_candidate_1_admission.py          # write the record
    python scripts/audit_candidate_1_admission.py --check  # replay and compare
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.open_interest_source import (
    MANIFEST_PATH as OI_MANIFEST_PATH,
)
from app.predictive.open_interest_source import (
    load_open_interest,
)
from app.predictive.taker_flow_source import (
    MANIFEST_PATH as KLINE_MANIFEST_PATH,
)
from app.predictive.taker_flow_source import (
    SPOT,
    USDM,
    VALID,
    WINDOW_START_MS,
    load_minute_books,
)

RECORD_PATH = "reports/validation/CANDIDATE-1-SOURCE-SUPPORT-ADMISSION-V1.json"
VERSION = "CANDIDATE_1_SOURCE_SUPPORT_ADMISSION_AUDIT_V1"
HOUR = 3600
FIVE_MINUTES = 300

# Declared before execution. Diagnostic support definitions only.
LOOKBACK_HOURS = 24
SELL_OFF_THRESHOLDS = (-0.05, -0.075, -0.10)  # trailing 24h spot log return at or below
REFERENCE_THRESHOLD = -0.05
DECLUSTER_HOURS = 72  # after an event at T, the next event is eligible from T + 72h
ADMISSIBLE_YEARS = (2022, 2023, 2024)  # carried forward from the Stage-2 OI coverage gate
INFORMATIONAL_YEARS = (2020, 2021)  # records exist; not automatically admissible
OI_JUMP_THRESHOLDS = (0.05, 0.10)  # absolute 5m log change in OI quantity
# Timing rules for the OI state at decision instant T.
TIMING_RULES = {
    # Existing contract PREDICTIVE_OPEN_INTEREST_STRUCTURE_V1 section 3.
    "CONTRACT_V1_STRICTLY_BEFORE_T_AGE_LE_10M": {"lag": 0, "max_age": 600},
    # Conservative candidate rule: one full cadence of assumed publication lag.
    "CONSERVATIVE_CREATE_TIME_LE_T_MINUS_5M_AGE_LE_15M": {"lag": FIVE_MINUTES, "max_age": 900},
}
FEASIBILITY_RULE = {
    "reference_threshold": REFERENCE_THRESHOLD,
    "minimum_pooled_admissible_events_per_arm": 30,
    "minimum_event_input_completeness": 0.90,
    "minimum_hourly_joint_availability_per_admissible_year": 0.95,
    "arms": "JOINT_STATE (OI_24H_LOG_CHANGE<0 AND REL_PRICE_24H_CHANGE<0) VS COMPLEMENT",
    "note": "Support feasibility only. Detectability/power requires the protocol-design power "
    "gate and is not decided here.",
}


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _year(epoch: int) -> int:
    return datetime.fromtimestamp(epoch, UTC).year


def hourly_closes(book: Any) -> tuple[np.ndarray, np.ndarray]:
    """Close of the completed minute [T-1m, T) for every hour T on the window grid.

    Index h is decision instant T = window_start + h hours; the minute used is h*60 - 1.
    """
    minutes = book.status.shape[0]
    hours = minutes // 60
    index = np.arange(1, hours + 1) * 60 - 1
    valid = book.status[index] == VALID
    close = np.where(valid, book.close[index], np.nan)
    return close, valid


def oi_hourly_states(
    times: np.ndarray, quantities: np.ndarray, instants: np.ndarray, lag: int, max_age: int
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """As-of OI quantity at each instant: latest create_time <= T - lag (strictly < T if 0)."""
    cutoff = instants - lag if lag else instants
    side = "right" if lag else "left"
    position = np.searchsorted(times, cutoff, side=side) - 1
    none = position < 0
    safe = np.clip(position, 0, len(times) - 1)
    stamped = times[safe]
    value = quantities[safe]
    stale = ~none & (instants - stamped > max_age)
    non_positive = ~none & ~stale & ~(np.isfinite(value) & (value > 0))
    ok = ~none & ~stale & ~non_positive
    reasons = {
        "NO_PRIOR_OPEN_INTEREST_RECORD": none,
        "OPEN_INTEREST_STATE_TOO_STALE": stale,
        "NON_POSITIVE_OPEN_INTEREST": non_positive,
    }
    return np.where(ok, value, np.nan), reasons


def _by_year(mask: np.ndarray, years: np.ndarray, domain: np.ndarray) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for year in sorted(set(years[domain].tolist())):
        in_year = domain & (years == year)
        total = int(in_year.sum())
        hit = int((mask & in_year).sum())
        out[str(year)] = {"hours": total, "available": hit, "rate": round(hit / total, 6)}
    return out


def decluster(candidates: np.ndarray, instants: np.ndarray) -> list[int]:
    events: list[int] = []
    next_allowed = -math.inf
    for index in np.flatnonzero(candidates):
        if instants[index] >= next_allowed:
            events.append(int(index))
            next_allowed = instants[index] + DECLUSTER_HOURS * HOUR
    return events


def build_record(root: Path = ROOT) -> dict[str, Any]:
    books, kline_manifest = load_minute_books(root)
    source = load_open_interest(root)
    oi_manifest = json.loads((root / OI_MANIFEST_PATH).read_text(encoding="utf-8"))
    oi_times = np.asarray(source.times, dtype=np.int64)
    oi_qty = np.asarray(source.quantities, dtype=np.float64)

    spot_close, spot_ok = hourly_closes(books[SPOT])
    perp_close, perp_ok = hourly_closes(books[USDM])
    hours = spot_close.shape[0]
    start = WINDOW_START_MS // 1000
    instants = start + np.arange(1, hours + 1, dtype=np.int64) * HOUR
    years = np.array([_year(int(t) - 1) for t in instants])  # year of the completed minute

    oi_first = int(oi_times[0])
    # Decision instants whose full 24h lookback lies inside the OI archive span.
    domain = instants - LOOKBACK_HOURS * HOUR >= oi_first + HOUR

    # ---- OI quantity/unit integrity, missingness and discontinuity -------------------------
    oi_years = np.array([_year(int(t)) for t in oi_times])
    non_positive = ~(np.isfinite(oi_qty) & (oi_qty > 0))
    positive = ~non_positive
    log_oi = np.where(positive, np.log(np.where(positive, oi_qty, 1.0)), np.nan)
    consecutive = np.diff(oi_times) == FIVE_MINUTES
    step = np.diff(log_oi)
    step_ok = consecutive & np.isfinite(step)
    gaps = oi_manifest["integrity"]["gaps"]
    gap_by_year: dict[str, dict[str, int]] = {}
    for gap in gaps:
        year = gap["after"][:4]
        slot = gap_by_year.setdefault(year, {"gaps": 0, "missing_records": 0, "max_missing": 0})
        slot["gaps"] += 1
        slot["missing_records"] += gap["missing_records"]
        slot["max_missing"] = max(slot["max_missing"], gap["missing_records"])
    np_by_year = {
        str(y): int((non_positive & (oi_years == y)).sum()) for y in sorted(set(oi_years.tolist()))
    }
    np_zero = int((oi_qty == 0).sum())
    jumps: dict[str, dict[str, int]] = {}
    for threshold in OI_JUMP_THRESHOLDS:
        big = step_ok & (np.abs(np.nan_to_num(step)) > threshold)
        jumps[f"abs_5m_log_change_gt_{threshold}"] = {
            str(y): int((big & (oi_years[1:] == y)).sum()) for y in sorted(set(oi_years.tolist()))
        }
    oi_integrity = {
        "manifest": OI_MANIFEST_PATH,
        "admitted_quantity": "sum_open_interest (contract quantity in BTC; notional excluded)",
        "records": len(oi_times),
        "first_record": _iso(int(oi_times[0])),
        "last_record": _iso(int(oi_times[-1])),
        "strictly_increasing": bool(np.all(np.diff(oi_times) > 0)),
        "off_grid_records": int((oi_times % FIVE_MINUTES != 0).sum()),
        "post_cutoff_records": int((oi_times > 1_735_689_599).sum()),
        "manifest_gap_summary_by_year": gap_by_year,
        "non_positive_quantities_total": int(non_positive.sum()),
        "non_positive_quantities_exact_zero": np_zero,
        "non_positive_quantities_by_year": np_by_year,
        "five_minute_discontinuities_by_year": jumps,
    }

    # ---- Hourly as-of availability under both timing rules ----------------------------------
    timing: dict[str, Any] = {}
    oi_state: dict[str, np.ndarray] = {}
    for name, rule in TIMING_RULES.items():
        state, reasons = oi_hourly_states(oi_times, oi_qty, instants, rule["lag"], rule["max_age"])
        oi_state[name] = state
        lag_index = LOOKBACK_HOURS
        prior = np.full(hours, np.nan)
        prior[lag_index:] = state[:-lag_index]
        window_ok = np.isfinite(state) & np.isfinite(prior)
        timing[name] = {
            "rule": rule,
            "hourly_state_availability_by_year": _by_year(np.isfinite(state), years, domain),
            "unavailability_reasons_in_domain": {
                key: int((mask & domain).sum()) for key, mask in reasons.items()
            },
            "oi_24h_change_availability_by_year": _by_year(window_ok, years, domain),
        }

    # ---- Synchronized traded perpetual/spot relative price -----------------------------------
    both = spot_ok & perp_ok
    rel = np.where(both, np.log(perp_close / spot_close), np.nan)
    lag = LOOKBACK_HOURS
    spot_prior = np.full(hours, np.nan)
    spot_prior[lag:] = spot_close[:-lag]
    rel_prior = np.full(hours, np.nan)
    rel_prior[lag:] = rel[:-lag]
    r24 = np.log(spot_close / spot_prior)  # trailing, known at T
    d_rel = rel - rel_prior
    finite_rel = np.isfinite(rel) & domain
    abs_rel_bps = np.abs(rel[finite_rel]) * 1e4
    relative_price = {
        "definition": "q_T = log(UM_PERP_1M_CLOSE / SPOT_1M_CLOSE), both the completed minute "
        "[T-1m, T) of the traded BTCUSDT instruments; deterioration = q_T - q_(T-24h) < 0",
        "not_used": ["MARK_PRICE", "INDEX_PRICE", "PREMIUM_INDEX", "FUNDING_RATE", "NOTIONAL_OI"],
        "availability_by_year": _by_year(np.isfinite(rel), years, domain),
        "change_24h_availability_by_year": _by_year(np.isfinite(d_rel), years, domain),
        "abs_level_bps_quantiles_in_domain": {
            q: round(float(np.quantile(abs_rel_bps, float(q))), 3) for q in ("0.5", "0.99", "0.999")
        },
        "synchronization_caveat": "1m closes are last trades inside the same minute, not "
        "simultaneous quotes; residual asynchrony is bounded by one minute and is noise, not "
        "look-ahead.",
    }

    # ---- Event/common support (no forward outcome is computed) ------------------------------
    primary_rule = "CONSERVATIVE_CREATE_TIME_LE_T_MINUS_5M_AGE_LE_15M"
    oi_now = oi_state[primary_rule]
    oi_prior = np.full(hours, np.nan)
    oi_prior[lag:] = oi_now[:-lag]
    d_oi = np.log(oi_now / oi_prior)
    joint_available = np.isfinite(d_oi) & np.isfinite(d_rel) & np.isfinite(r24)
    hourly_joint = _by_year(joint_available, years, domain)
    support: dict[str, Any] = {}
    for threshold in SELL_OFF_THRESHOLDS:
        candidates = domain & np.isfinite(r24) & (r24 <= threshold)
        events = decluster(candidates, instants)
        rows: dict[str, dict[str, int]] = {}
        for index in events:
            slot = rows.setdefault(
                str(years[index]),
                {"events": 0, "complete_inputs": 0, "joint_state": 0, "complement": 0},
            )
            slot["events"] += 1
            if joint_available[index]:
                slot["complete_inputs"] += 1
                if d_oi[index] < 0 and d_rel[index] < 0:
                    slot["joint_state"] += 1
                else:
                    slot["complement"] += 1
        admissible = {
            key: sum(rows.get(str(y), {}).get(key, 0) for y in ADMISSIBLE_YEARS)
            for key in ("events", "complete_inputs", "joint_state", "complement")
        }
        support[str(threshold)] = {
            "by_year": rows,
            "admissible_2022_2024": admissible,
            "admissible_events_per_year": round(admissible["events"] / len(ADMISSIBLE_YEARS), 3),
        }

    reference = support[str(REFERENCE_THRESHOLD)]["admissible_2022_2024"]
    completeness = reference["complete_inputs"] / reference["events"] if reference["events"] else 0
    joint_rates = [hourly_joint[str(y)]["rate"] for y in ADMISSIBLE_YEARS]
    checks = {
        "joint_state_arm_events": reference["joint_state"],
        "complement_arm_events": reference["complement"],
        "event_input_completeness": round(completeness, 6),
        "minimum_hourly_joint_availability_admissible_years": min(joint_rates),
    }
    feasible = (
        reference["joint_state"] >= FEASIBILITY_RULE["minimum_pooled_admissible_events_per_arm"]
        and reference["complement"] >= FEASIBILITY_RULE["minimum_pooled_admissible_events_per_arm"]
        and completeness >= FEASIBILITY_RULE["minimum_event_input_completeness"]
        and min(joint_rates)
        >= FEASIBILITY_RULE["minimum_hourly_joint_availability_per_admissible_year"]
    )
    return {
        "version": VERSION,
        "candidate": "CANDIDATE-1-POSITIONING-CONDITIONED-SELL-OFF-RECOVERY",
        "forward_returns_computed": False,
        "labels_or_outcomes_computed": False,
        "models_fitted": 0,
        "post_cutoff_data_accessed": False,
        "sealed_queries": 0,
        "sources": {
            "spot_and_perpetual_1m_klines": {
                "manifest": KLINE_MANIFEST_PATH,
                "window": kline_manifest["development_source_window"],
                "objects_verified": kline_manifest["official_checksums_verified"],
                "spot_minutes": books[SPOT].summary(),
                "perpetual_minutes": books[USDM].summary(),
            },
            "open_interest_5m": {"manifest": OI_MANIFEST_PATH},
        },
        "usable_intersection": {
            "raw_overlap": [_iso(oi_first), "2024-12-31T23:59:59Z"],
            "first_decision_instant_with_24h_lookback": _iso(int(instants[domain][0])),
            "admissible_evaluation_years": list(ADMISSIBLE_YEARS),
            "informational_only_years": list(INFORMATIONAL_YEARS),
            "eligibility_carry_forward": "Stage-2 OI coverage/history gate admitted 2022-2024; "
            "2020-09..2021 records exist but are not automatically admissible.",
        },
        "oi_integrity": oi_integrity,
        "timing": timing,
        "relative_price": relative_price,
        "hourly_joint_availability_by_year": hourly_joint,
        "support_definitions": {
            "sell_off": "trailing 24h spot log return at T <= threshold (known at T)",
            "thresholds": list(SELL_OFF_THRESHOLDS),
            "decluster_hours": DECLUSTER_HOURS,
            "joint_state": "OI_24H_LOG_CHANGE < 0 AND REL_PRICE_24H_CHANGE < 0 at T",
            "oi_timing_rule": primary_rule,
            "status": "DIAGNOSTIC_SUPPORT_ONLY_NOT_FROZEN_ELIGIBILITY",
        },
        "support": support,
        "feasibility_rule": FEASIBILITY_RULE,
        "feasibility_checks": checks,
        "support_feasible": bool(feasible),
    }


def canonical(record: dict[str, Any]) -> str:
    return json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    text = canonical(build_record())
    path = ROOT / RECORD_PATH
    if options.check:
        stored = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if stored != text:
            raise SystemExit("candidate #1 admission record does not replay")
        print("candidate #1 admission audit replay: PASS")
        return
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {RECORD_PATH}")


if __name__ == "__main__":
    main()
