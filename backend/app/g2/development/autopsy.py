"""Deterministic G2-V0 autopsy (development protocol sections 16-17).

The unit of diagnosis is an episode: one executed trade, or one missed standardized opportunity
(a run of NO_TRADE decisions whose standardized shadow payoff on one side reached the predeclared
threshold, grouped while consecutive qualifying decisions are at most 4h apart; the episode is
represented by its FIRST decision, never the hindsight-best one).

Episode selection is fixed before outcomes are opened: the 5 most favourable and 5 least
favourable trades by realized NET_R, 5 pseudo-random further trades and 5 pseudo-random missed
episodes drawn with a seed derived from the frozen uncertainty seed. Categories are assigned by
deterministic rules. Every entry separates FACT -> CAUSAL HYPOTHESIS -> REQUIRED TEST; hypotheses
are not conclusions and no test is executed in G2-02 (each would need a change card and a slot).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from ..contract import COLUMNS
from .runner import INITIALIZATION_START, scored_mask, utc_iso
from .scoring import SEED, primary_reason

FAVORABLE_N = UNFAVORABLE_N = RANDOM_TRADES_N = RANDOM_MISSED_N = 5
AUTOPSY_SPAWN_KEY = (1,)
OPPORTUNITY_NET_R = 1.0  # standardized shadow NET_R >= +1.0R qualifies as an opportunity
EPISODE_GAP_DECISIONS = 16  # consecutive qualifying decisions <= 4h apart form one episode
EXTENDED_SCALED = 2.0  # |scaled PRICE_EXTENSION| >= 2 robust units in the trade direction

MODEL = "MODEL_ABSTENTION"
RISK = "RISK_OR_CAPACITY_ABSTENTION"
EXECUTION = "EXECUTION_FAILURE"
COUNTERFACTUAL = "COUNTERFACTUAL_REFERENCE_OPPORTUNITY"
CLASS_OF = {
    "INSUFFICIENT_POLICY_EVIDENCE": MODEL,
    "UTILITY_MARGIN_NOT_POSITIVE": MODEL,
    "UTILITY_MARGIN_TIE": MODEL,
    "FORECAST_UNAVAILABLE_NO_MODEL": MODEL,
    "FORECAST_UNAVAILABLE_WARMUP": MODEL,
    "POSITION_ALREADY_OPEN": RISK,
    "PATH_DRAWDOWN_STOP_ACTIVE": RISK,
    "CONTRACT_FILTER_NOT_MET": RISK,
    "FORECAST_UNAVAILABLE_MISSING_DATA": EXECUTION,
    "FORECAST_UNAVAILABLE_INVALID_SIGMA": EXECUTION,
    "SOURCE_STALE_OR_INVALID": EXECUTION,
}

HYPOTHESIS = {
    "forecast sign error": (
        (
            "The conditional 4h location was on the wrong side of the realized move at this "
            "decision; the eight-column state may not carry the information that moved price."
        ),
        (
            "Across all trades, compare realized NET_R by forecast-sign correctness and by "
            "view-strength stratum; any change to the dictionary needs a change card."
        ),
    ),
    "magnitude/quantile error": (
        (
            "The realized 4h return fell outside the issued q10-q90 band; the residual scale "
            "(SIGMA_4H x prequential residuals) may understate tail risk in this regime."
        ),
        (
            "Coverage by year/volatility state from the forecast scorecard; no residual-rule change "
            "without a change card."
        ),
    ),
    "evidence/calibration state issue": (
        "The forecast used the training-target baseline rather than the prequential archive.",
        "Count trades issued under the fallback distribution; expected zero in 2021-2024.",
    ),
    "regime/context mismatch": (
        (
            "The entry side opposed the completed 4h CONTEXT_STRUCTURE sign; the utility head may "
            "weigh local terms against slower context."
        ),
        "Realized NET_R of trades with side aligned vs opposed to context sign (all trades).",
    ),
    "actionability/path error": (
        (
            "The utility head selected a side opposite to the terminal median forecast "
            "(PATH_UTILITY_OVERRIDES_TERMINAL_VIEW) and the trade lost."
        ),
        "Realized NET_R of override vs non-override trades (all trades, weekly blocks).",
    ),
    "late/extended entry": (
        (
            "Price was stretched from LOCAL_FAST in the trade direction at entry (scaled "
            "PRICE_EXTENSION beyond 2 robust units), leaving less favourable path."
        ),
        "Realized NET_R by scaled PRICE_EXTENSION in trade direction (all trades).",
    ),
    "stop/path loss despite correct terminal direction": (
        (
            "The terminal 4h direction was right but the 2xATR stop was reached first; stop "
            "geometry relative to path volatility may be tight."
        ),
        (
            "Share of stop exits whose decision-time 4h return had the trade's sign; stop geometry "
            "is frozen and changing it consumes a slot."
        ),
    ),
    "cost/funding erosion": (
        "Gross price P&L was positive but friction/funding made the trade net negative.",
        (
            "Friction/funding share of |gross| (policy scorecard) and the predeclared cost stress "
            "in a later authorized package."
        ),
    ),
    "execution/data failure": (
        "The trade carries an execution/data violation flag.",
        "Audit the flagged source minutes/funding records.",
    ),
    "false positive under explicit standardized payoff label": (
        (
            "The standardized shadow trade on the selected side was itself negative: the utility "
            "margin was positive while the frozen label was not."
        ),
        "Selected-side shadow NET_R distribution (policy scorecard) vs unconditional shadow.",
    ),
    "risk violation": ("A risk rule was violated.", "Deterministic risk audit."),
    "correct direction held to expiry": (
        "The selected side matched the realized path and was held to the 4h expiry.",
        "Whether favourable trades concentrate in a few weeks (concentration diagnostics).",
    ),
}


def _sample(rng: np.random.Generator, pool: list[int], k: int) -> list[int]:
    if not pool:
        return []
    chosen = rng.choice(len(pool), size=min(k, len(pool)), replace=False)
    return sorted(pool[int(i)] for i in chosen)


def _decision_index(arrays: dict[str, np.ndarray]) -> dict[int, int]:
    return {int(t): i for i, t in enumerate(arrays["t"])}


def _minutes_of(text: str) -> int:
    moment = datetime.fromisoformat(text)
    return int((moment - INITIALIZATION_START).total_seconds() // 60)


def trade_facts(
    trade: dict[str, Any], arrays: dict[str, np.ndarray], index: dict[int, int]
) -> dict[str, Any]:
    decision_minutes = _minutes_of(trade["intended_entry_time"]) - 1
    i = index[decision_minutes]
    sign = 1 if trade["side"] == "LONG" else -1
    realized = float(arrays["realized"][i])
    median = float(arrays["median"][i])
    chosen = "shadow_long_net_r" if sign > 0 else "shadow_short_net_r"
    other = "shadow_short_net_r" if sign > 0 else "shadow_long_net_r"
    return {
        "trade_id": trade["trade_id"],
        "side": trade["side"],
        "decision_time": utc_iso(decision_minutes),
        "entry_time": trade["entry_time"],
        "exit_time": trade["exit_time"],
        "exit_kind": trade["exit_kind"],
        "raw_entry": trade["raw_entry"],
        "raw_exit": trade["raw_exit"],
        "stop_price": trade["stop_price"],
        "realized_net_r": trade["realized_net_r"],
        "net_pnl": trade["net_pnl"],
        "gross_pnl": trade["gross_pnl"],
        "friction_cost": trade["friction_cost"],
        "funding_pnl": trade["funding_pnl"],
        "violation_flags": trade["violation_flags"],
        "forecast": {
            "median_return": median,
            "q10": float(arrays["q10"][i]),
            "q90": float(arrays["q90"][i]),
            "p_positive_uncalibrated": float(arrays["p_positive"][i]),
            "view_strength_z": float(arrays["view"][i]),
            "residual_source": int(arrays["residual_source"][i]),
        },
        "realized_r4h_from_decision": realized,
        "utility": {
            "long_margin": float(arrays["long_margin"][i]),
            "short_margin": float(arrays["short_margin"][i]),
        },
        "raw_terms": dict(zip(COLUMNS, (float(v) for v in arrays["raw_terms"][i]), strict=True)),
        "scaled_terms": dict(
            zip(COLUMNS, (float(v) for v in arrays["scaled_terms"][i]), strict=True)
        ),
        "shadow_net_r_selected_side": float(arrays[chosen][i]),
        "shadow_net_r_other_side": float(arrays[other][i]),
        "_sign": sign,
        "_index": i,
    }


def categories(facts: dict[str, Any]) -> list[str]:
    sign = facts["_sign"]
    realized = facts["realized_r4h_from_decision"]
    median = facts["forecast"]["median_return"]
    lost = facts["realized_net_r"] < 0
    out: list[str] = []
    if np.isfinite(realized) and median != 0 and np.sign(median) != np.sign(realized):
        out.append("forecast sign error")
    q10, q90 = facts["forecast"]["q10"], facts["forecast"]["q90"]
    if np.isfinite(realized) and not q10 <= realized <= q90:
        out.append("magnitude/quantile error")
    if facts["forecast"]["residual_source"] != 2:
        out.append("evidence/calibration state issue")
    context = facts["raw_terms"]["CONTEXT_STRUCTURE"]
    if lost and context * sign < 0:
        out.append("regime/context mismatch")
    if lost and median * sign < 0:
        out.append("actionability/path error")
    if lost and facts["scaled_terms"]["PRICE_EXTENSION"] * sign >= EXTENDED_SCALED:
        out.append("late/extended entry")
    stopped = facts["exit_kind"] in ("STOP", "STOP_GAP")
    if stopped and np.isfinite(realized) and realized * sign > 0:
        out.append("stop/path loss despite correct terminal direction")
    if facts["gross_pnl"] > 0 and facts["net_pnl"] <= 0:
        out.append("cost/funding erosion")
    if facts["violation_flags"]:
        out.append("execution/data failure")
    if facts["shadow_net_r_selected_side"] < 0:
        out.append("false positive under explicit standardized payoff label")
    if not lost and facts["exit_kind"] == "EXPIRY":
        out.append("correct direction held to expiry")
    return out


def _episode(kind: str, facts: dict[str, Any]) -> dict[str, Any]:
    cats = categories(facts)
    public = {k: v for k, v in facts.items() if not k.startswith("_")}
    return {
        "selection": kind,
        "FACT": public,
        "categories": cats,
        "CAUSAL_HYPOTHESIS": [
            {"category": c, "hypothesis": HYPOTHESIS[c][0]} for c in cats if c in HYPOTHESIS
        ],
        "REQUIRED_TEST": [
            {"category": c, "test": HYPOTHESIS[c][1], "executed_in_g2_02": False}
            for c in cats
            if c in HYPOTHESIS
        ],
    }


def missed_episodes(
    arrays: dict[str, np.ndarray],
    reason_sets: list[str],
    reference: dict[str, np.ndarray] | None,
    rejected_decisions: set[int],
) -> list[dict[str, Any]]:
    scored = scored_mask(arrays["t"])
    out: list[dict[str, Any]] = []
    for side, key, sign in (("LONG", "shadow_long_net_r", 1), ("SHORT", "shadow_short_net_r", -1)):
        payoff = arrays[key]
        qualifying = np.flatnonzero(
            scored & (arrays["action"] == 0) & np.isfinite(payoff) & (payoff >= OPPORTUNITY_NET_R)
        )
        previous = None
        for i in qualifying:
            if previous is not None and i - previous <= EPISODE_GAP_DECISIONS:
                out[-1]["decisions_in_episode"] += 1
                previous = i
                continue
            previous = i
            codes = set(reason_sets[int(arrays["reasons"][i])].split("|"))
            primary = primary_reason(codes)
            klass = CLASS_OF.get(primary, MODEL)
            if int(arrays["t"][i]) in rejected_decisions:
                klass = EXECUTION
            reference_took = bool(
                reference is not None
                and int(reference["t"][i]) == int(arrays["t"][i])
                and int(reference["selection"][i]) == sign
            )
            out.append(
                {
                    "side": side,
                    "first_decision_time": utc_iso(int(arrays["t"][i])),
                    "first_decision_index": int(i),
                    "primary_reason": primary,
                    "class": klass,
                    "trend_reference_selected_same_side": reference_took,
                    "counterfactual_shadow_net_r_first_decision": float(payoff[i]),
                    "decisions_in_episode": 1,
                    "v0_policy_selection": int(arrays["selection"][i]),
                    "long_margin": float(arrays["long_margin"][i]),
                    "short_margin": float(arrays["short_margin"][i]),
                }
            )
    out.sort(key=lambda e: (e["first_decision_time"], e["side"]))
    return out


def build(
    arrays: dict[str, np.ndarray],
    events: dict[str, Any],
    reference: dict[str, np.ndarray] | None,
) -> dict[str, Any]:
    rng = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=AUTOPSY_SPAWN_KEY))
    index = _decision_index(arrays)
    reason_sets = events["reason_sets"]
    trades = events["trades"]
    facts = [trade_facts(trade, arrays, index) for trade in trades]
    order = sorted(range(len(facts)), key=lambda k: (facts[k]["realized_net_r"], k))
    unfavorable = order[:UNFAVORABLE_N]
    favorable = order[::-1][:FAVORABLE_N]
    taken = set(unfavorable) | set(favorable)
    random_trades = _sample(rng, [k for k in range(len(facts)) if k not in taken], RANDOM_TRADES_N)
    category_counts: dict[str, int] = {}
    for fact in facts:
        for category in categories(fact):
            category_counts[category] = category_counts.get(category, 0) + 1
    rejected = {
        _minutes_of(f["event_time"]) - 1 for f in events["fills"] if f["kind"] == "ENTRY_REJECTED"
    }
    missed = missed_episodes(arrays, reason_sets, reference, rejected)
    class_counts: dict[str, dict[str, Any]] = {}
    for episode in missed:
        entry = class_counts.setdefault(
            episode["class"], {"episodes": 0, "mean_counterfactual_net_r": 0.0}
        )
        entry["episodes"] += 1
        entry["mean_counterfactual_net_r"] += episode["counterfactual_shadow_net_r_first_decision"]
    for entry in class_counts.values():
        entry["mean_counterfactual_net_r"] /= entry["episodes"]
    random_missed = _sample(rng, list(range(len(missed))), RANDOM_MISSED_N)
    net_r = np.array([f["realized_net_r"] for f in facts], dtype=float)
    years = np.array([f["decision_time"][:4] for f in facts])
    return {
        "system": "G2-V0",
        "rules": {
            "favorable": FAVORABLE_N,
            "unfavorable": UNFAVORABLE_N,
            "pseudo_random_trades": RANDOM_TRADES_N,
            "pseudo_random_missed": RANDOM_MISSED_N,
            "seed": f"SeedSequence({SEED}, spawn_key={AUTOPSY_SPAWN_KEY})",
            "standardized_opportunity_net_r": OPPORTUNITY_NET_R,
            "episode_gap_decisions": EPISODE_GAP_DECISIONS,
            "extended_entry_scaled_units": EXTENDED_SCALED,
            "missed_representative": "first decision of the episode (no hindsight best entry)",
            "counterfactual_payoff": "diagnostic only, not booked P&L; no infinite capital, no "
            "simultaneous accounting of overlapping shadows",
        },
        "verification_first": {
            "timestamps_and_data_quality": "see anomalies section",
            "model_version_identity": "run manifests/fingerprints in the batch manifest",
            "execution_accounting": "trade net = gross - friction + funding (checked per trade)",
            "rule_compliance": "one position, no pyramiding/flip; drawdown lock audited",
        },
        "trade_category_counts": {
            "denominator_trades": len(facts),
            "counts": dict(sorted(category_counts.items())),
        },
        "realized_net_r_by_year": {
            year: {
                "trades": int((years == year).sum()),
                "mean_net_r": float(net_r[years == year].mean()),
            }
            for year in sorted(set(years.tolist()))
        },
        "favorable_episodes": [_episode("FAVORABLE_TOP_NET_R", facts[k]) for k in favorable],
        "unfavorable_episodes": [
            _episode("UNFAVORABLE_BOTTOM_NET_R", facts[k]) for k in unfavorable
        ],
        "pseudo_random_trade_episodes": [
            _episode("PSEUDO_RANDOM_TRADE", facts[k]) for k in random_trades
        ],
        "missed_opportunities": {
            "episodes": len(missed),
            "class_counts": dict(sorted(class_counts.items())),
            "trend_reference_selected_same_side": sum(
                1 for e in missed if e["trend_reference_selected_same_side"]
            ),
            "counterfactual_reference_class": COUNTERFACTUAL,
            "pseudo_random_missed_episodes": [
                {
                    "FACT": missed[k],
                    "CAUSAL_HYPOTHESIS": _missed_hypothesis(missed[k]),
                    "REQUIRED_TEST": _missed_test(missed[k]),
                }
                for k in random_missed
            ],
        },
    }


def _missed_hypothesis(episode: dict[str, Any]) -> str:
    klass = episode["class"]
    if klass == MODEL:
        return (
            "The utility heads' prudential margins did not clear zero although the standardized "
            f"{episode['side']} shadow reached +{OPPORTUNITY_NET_R:.0f}R: the margin (prediction "
            "+ residual q10) may be too conservative for this state, or the state lacked the "
            "information."
        )
    if klass == RISK:
        return "Capacity: one position was already open (or a risk lock was active)."
    return "Data/execution unavailability prevented a decision or an entry."


def _missed_test(episode: dict[str, Any]) -> dict[str, Any]:
    return {
        "test": "Distribution of shadow NET_R at MODEL_ABSTENTION decisions vs policy-selected "
        "decisions (weekly blocks); any margin change is an actionability revision needing a "
        "change card and a slot.",
        "executed_in_g2_02": False,
    }
