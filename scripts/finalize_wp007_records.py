"""Generate deterministic WP-007 comparison, lessons, report, and sealed eligibility."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.checkpoint_views import memory_views
from app.research.runner import sha256
from app.research.sealed_eligibility import write_eligibility_table
from app.research.wp007 import ADMISSION_PATH
from app.research.wp007_views import build_wp007_comparison


def write_json(relative: str, payload: dict) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def fmt(value: float) -> str:
    return f"{value:+.10f}"


def main() -> None:
    comparison = build_wp007_comparison(ROOT)
    comparison_path = "reports/research/WP-007-COMPARISON.json"
    write_json(comparison_path, comparison)
    core = comparison["variants"]["FLOW_CORE"]
    price = comparison["variants"]["FLOW_PRICE_RESPONSE"]
    admission_path = ROOT / ADMISSION_PATH
    lessons = {
        "schema_version": 1,
        "record_kind": "POST_RESULT_SCIENTIFIC_INTERPRETATION",
        "work_package": "WP-007",
        "root_family": "FAM-ORDER-FLOW",
        "selected_hypothesis": "AGGRESSIVE_BUY_FLOW_TRANSITION_V1",
        "primary_experiment_id": core["experiment_id"],
        "family_conclusion_policy": "The family follows preselected FLOW_CORE, never the better-scoring confirmation variant.",
        "family_terminal_classification": core["terminal_classification"],
        "novelty_admission": {
            "family_classification": "NEW_FAMILY",
            "path": ADMISSION_PATH,
            "sha256": sha256(admission_path),
        },
        "comparison": {
            "path": comparison_path,
            "sha256": sha256(ROOT / comparison_path),
            "core_minus_random_mean_r": comparison["core_deltas"]["random_control_mean"],
            "core_minus_trend_r": comparison["core_deltas"]["sma_trend"],
            "core_minus_breakout_r": comparison["core_deltas"]["breakout"],
            "core_minus_aligned_r": comparison["core_deltas"]["aligned"],
            "core_minus_pullback_recovery_r": comparison["core_deltas"]["pullback_recovery_core"],
        },
        "experiments": {
            item["experiment_id"]: {
                key: item[key]
                for key in (
                    "result_path",
                    "result_sha256",
                    "terminal_classification",
                    "default_net_expectancy_r",
                    "zero_cost_net_expectancy_r",
                    "double_cost_net_expectancy_r",
                    "delay_net_expectancy_r",
                    "trade_count",
                    "nonnegative_fold_count",
                    "minimum_fold_trades",
                    "trade_ess",
                    "max_positive_fold_profit_share",
                    "invalid_attempts",
                    "unresolved_trades",
                )
            }
            for item in (core, price)
        },
        "family_disposition": "FAM-ORDER-FLOW is REJECT_COST_DOMINATED after its one fixed allocation. Both configurations and all eight profiles are consumed; the family is not seal-eligible and has no Champion standing.",
        "key_lesson": "The transition has positive gross expectancy, but realistic default friction consumes it and doubled costs deepen the loss. Broad fold coverage and high ESS do not rescue negative net expectancy.",
        "confirmation_lesson": "FLOW_PRICE_RESPONSE improves default expectancy by 0.0161863519 R and reduces coverage by 263 trades, but remains cost-dominated and cannot replace the preselected primary.",
        "timing_lesson": "DELAY_1H changes CORE expectancy by only +0.0048157074 R and removes 10 trades; it does not reverse the negative net result.",
        "integrity_limitation": "All six folds are exposed development history. Binance taker-buy base share is a venue-level aggressive-participation proxy, not market-wide signed demand, investor intent, or causal evidence.",
        "blocked_directions": [
            "Changing the 0.5 accounting balance point, 4h context duration, 2%/4% barriers, or 24h horizon.",
            "Adding price, breakout, trend, pullback, persistence, indicator, volume-multiple, or other gates chosen after these results.",
            "Adopting FLOW_PRICE_RESPONSE as the family conclusion because its loss is smaller.",
            "Modifying ALIGNED or pullback recovery, or reopening exhausted FAM-BREAKOUT.",
            "Any sealed query, paper trade, Champion promotion, or real-money action on this evidence.",
        ],
        "new_trial_allocation": 0,
    }
    lessons_path = "research/memory/WP-007-LESSONS.json"
    write_json(lessons_path, lessons)

    rows = lambda item: ", ".join(
        f"{fold['fold_id'][-4:]}:{fold['trade_count']} ({fmt(fold['net_expectancy_r'])} R)"
        for fold in item["folds"]
    )
    report = f"""# WP-007 — Aggressive buy-flow transition

DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE. Champion NONE. No sealed
query was executed. All six folds are previously exposed development history.

## Feature integrity and semantics

The accepted canonical BTCUSDT 1m identity remained unchanged. All 3,870,559 rows
passed finite/nonnegative taker-field checks; `taker_base <= volume` and
`taker_quote <= quote_volume` held under the frozen tolerance without clamping.
The deterministic timestamp-only raw Binance sample compared 21,632 rows across every
available calendar quarter and both known off-grid intervals with zero mismatches.

`BTCUSDT-SPOT-ORDERFLOW-DEV-v1` contains 64,135 eligible 1h buckets and 16,008
eligible 4h buckets. Production aggregation and the independent oracle reconcile at
content hash `d16a5e18d19a9fe30a58ce24999d001d11bf3168d59703b8afd09552632464e5`.
Buckets use the ratio of summed taker-buy base volume to summed total base volume;
incomplete and quarantined buckets are ineligible and missing minutes remain unfilled.

The feature is Binance's exchange-reported taker-buy base asset volume share: a proxy
for aggressive buy-side participation on that venue. It is not complete market-wide
order flow, investor intent, cross-exchange signed demand, or causal evidence.

## Frozen family and chronology

SEARCH_MEMORY_V2 admitted FLOW_CORE as `NEW_FAMILY` under `FAM-ORDER-FLOW` and
FLOW_PRICE_RESPONSE as `DESCENDANT_MECHANISM_CHANGE` before results. The classifier
was not weakened, no condition was added to force novelty, and prior budgets were not
reset. The exact 0.5 accounting balance point, non-overlapping 4h context, 2% stop,
4% target, 1,440-minute horizon, and four profiles per variant were fixed with zero
parameter search.

FLOW_CORE emits LONG only when the previous completed 1h share is <=0.5, current
completed 1h share is >0.5, and the most recent completed UTC 4h bucket closing at or
before the current signal hour opens is >0.5. FLOW_PRICE_RESPONSE adds only
`current_completed_1h_close > current_completed_1h_open`.

Two tooling defects were found before market evaluation. The first wrote no
preregistration; the second occurred after the original preregistrations were committed
but before any market array or trial was loaded. Both are recorded as zero-result
corrections. The original preregistrations are preserved and effective v2 declarations
were committed before the result run; scientific scope and executable behavior did not
change.

## Results — DEVELOPMENT_EVALUATION_V1 unchanged

| | FLOW_CORE | FLOW_PRICE_RESPONSE |
|---|---:|---:|
| Terminal classification | **{core["terminal_classification"]}** | **{price["terminal_classification"]}** |
| Default net expectancy R | {fmt(core["default_net_expectancy_r"])} | {fmt(price["default_net_expectancy_r"])} |
| Zero-cost net expectancy R | {fmt(core["zero_cost_net_expectancy_r"])} | {fmt(price["zero_cost_net_expectancy_r"])} |
| Double-cost net expectancy R | {fmt(core["double_cost_net_expectancy_r"])} | {fmt(price["double_cost_net_expectancy_r"])} |
| DELAY_1H net expectancy R | {fmt(core["delay_net_expectancy_r"])} | {fmt(price["delay_net_expectancy_r"])} |
| Resolved trades | {core["trade_count"]} | {price["trade_count"]} |
| Invalid / unresolved | {core["invalid_attempts"]} / {core["unresolved_trades"]} | {price["invalid_attempts"]} / {price["unresolved_trades"]} |
| Nonnegative folds | {core["nonnegative_fold_count"]}/6 | {price["nonnegative_fold_count"]}/6 |
| Minimum fold trades | {core["minimum_fold_trades"]} | {price["minimum_fold_trades"]} |
| Trade ESS | {core["trade_ess"]:.2f} | {price["trade_ess"]:.2f} |
| Positive-fold profit concentration | {core["max_positive_fold_profit_share"]:.2%} | {price["max_positive_fold_profit_share"]:.2%} |

CORE folds: {rows(core)}.

PRICE_RESPONSE folds: {rows(price)}.

Both rules have positive zero-cost expectancy, but default friction consumes the
signal and doubled costs deepen the loss. CORE is positive in only one fold, by just
+0.0001895828 R, so its positive-fold concentration is 100%. Evidence is much more
frequent than ALIGNED, but not more evenly profitable. PRICE_RESPONSE removes 263
trades and improves default expectancy by +0.0161863519 R, yet remains
cost-dominated. DELAY_1H improves CORE by only +0.0048157074 R and leaves it negative;
the event is not rescued by a one-hour lag.

## Descriptive preserved-reference comparison

These are not paired comparisons; each reference retains its own eligibility and
occupancy semantics.

| Reference | Default expectancy R | CORE delta R |
|---|---:|---:|
| Random control mean | {fmt(comparison["references"]["random_control_mean"])} | {fmt(comparison["core_deltas"]["random_control_mean"])} |
| SMA trend | {fmt(comparison["references"]["sma_trend"])} | {fmt(comparison["core_deltas"]["sma_trend"])} |
| Breakout | {fmt(comparison["references"]["breakout"])} | {fmt(comparison["core_deltas"]["breakout"])} |
| ALIGNED | {fmt(comparison["references"]["aligned"])} | {fmt(comparison["core_deltas"]["aligned"])} |
| Pullback recovery core | {fmt(comparison["references"]["pullback_recovery_core"])} | {fmt(comparison["core_deltas"]["pullback_recovery_core"])} |
| No-trade | zero trades | not comparable |

The new mechanism is structurally distinct in information source and entry rule, but
its development economics do not survive realistic friction. The preselected CORE
sets the family conclusion: **REJECT_COST_DOMINATED**. The less-negative confirmation
variant does not replace it.

## Accounting and disposition

One economic hypothesis, two configurations, eight profile evaluations, zero numeric
variants, one adaptive decision, and one result-dependent fork were consumed.
Cumulatively: 5 hypotheses, 13 configurations, 69 profile/seed trials, 0 numeric
variants, 4 adaptive decisions, and 4 result-dependent forks.

FAM-ORDER-FLOW is parked as cost-dominated. FAM-BREAKOUT remains exhausted;
FAM-PULLBACK-RECOVERY and ALIGNED remain parked. No sealed query, paper trade,
Champion, forward evidence, or real-money authorization follows.
"""
    report_path = ROOT / "reports/research/WP-007-ORDER-FLOW.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8", newline="\n")
    write_eligibility_table(ROOT)
    for name, content in memory_views(ROOT).items():
        (ROOT / "research/memory" / name).write_text(content, encoding="utf-8", newline="\n")
    print("WP-007 comparison, lessons, report, and sealed eligibility generated.")


if __name__ == "__main__":
    main()
