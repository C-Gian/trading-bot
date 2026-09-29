"""Deterministic Markdown/JSON renderings of the G2-02 batch payload (no new computation)."""

from __future__ import annotations

from typing import Any

from .variants import CASH_SYSTEM, FORECAST_SYSTEMS, POLICY_SYSTEMS, VARIANTS

HEADER = (
    "> **Exposed development evidence only.** Not validation, not a discovery test, not a "
    "candidate or Champion. Production action remains `NO_TRADE`; real money is not authorized."
)


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if value != 0 and abs(value) < 10 ** (-digits + 2):
            return f"{value:.3e}"
        return f"{value:,.{digits}f}"
    return str(value)


def pct(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{100 * value:.{digits}f}%"


def table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def forecast_table(results: dict[str, Any]) -> str:
    rows = []
    for system in FORECAST_SYSTEMS:
        card = results["forecast_scorecards"][system]
        m, s = card["metrics"], card["support"]
        rows.append(
            [
                system,
                fmt(m["crps"], 6),
                fmt(m["pinball_q10"], 6),
                fmt(m["pinball_q50"], 6),
                fmt(m["pinball_q90"], 6),
                fmt(m["brier"], 5),
                pct(m["covered"]),
                fmt(m["abs_error_median"], 6),
                pct(m["direction_hit"]),
                fmt(s["matured_scoreable"]),
                pct(s["availability_fraction"]),
            ]
        )
    return table(
        [
            "System",
            "CRPS (primary)",
            "Pinball q10",
            "Pinball q50",
            "Pinball q90",
            "Brier r4h>0",
            "q10–q90 coverage",
            "MAE median",
            "Direction hit (descr.)",
            "Scored forecasts",
            "Availability",
        ],
        rows,
    )


def policy_table(results: dict[str, Any]) -> str:
    rows = []
    for system in POLICY_SYSTEMS:
        card = results["policy_scorecards"][system]
        if system == CASH_SYSTEM:
            rows.append([system, "0", "0.00%", "0.00%", "0", "—", "0.00%", "—", "—", "—"])
            continue
        mix = card["long_short_mix"]
        rows.append(
            [
                system,
                fmt(card["primary"]["mean_15m_return_relative_cash"], 8),
                pct(card["total_net_return"]),
                pct(card["max_drawdown"]),
                fmt(card["trade_count"]),
                fmt(card["mean_realized_net_r"], 4),
                pct(card["occupancy_fraction"]),
                f"{mix['LONG']['count']}/{mix['SHORT']['count']}",
                fmt(card["turnover_per_year"], 2),
                card["drawdown_stop_triggered_at"] or "not triggered",
            ]
        )
    return table(
        [
            "System",
            "Mean 15m return vs cash (primary)",
            "Total net return",
            "Max drawdown",
            "Trades",
            "Mean NET_R",
            "Occupancy",
            "LONG/SHORT",
            "Turnover / yr",
            "5% drawdown lock",
        ],
        rows,
    )


def uncertainty_table(items: list[dict[str, Any]], digits: int) -> str:
    rows = [
        [
            f"{item['system']} − {item['versus']}",
            item["metric"],
            fmt(item["point"], digits),
            fmt(item["p10"], digits),
            fmt(item["p50"], digits),
            fmt(item["p90"], digits),
            fmt(item.get("common_support", item.get("count"))),
        ]
        for item in items
    ]
    return table(["Comparison", "Metric", "Point Δ", "p10", "p50", "p90", "Support"], rows)


def execution_table(results: dict[str, Any]) -> str:
    rows = []
    for system in POLICY_SYSTEMS:
        card = results["execution_scorecards"][system]
        if system == CASH_SYSTEM:
            continue
        rows.append(
            [
                system,
                ",".join(str(v) for v in card["decision_to_fill_delay_minutes"]["distinct_values"])
                or "—",
                fmt(card["entries_filled"]),
                fmt(card["entries_rejected"]),
                fmt(card["friction_paid"], 2),
                fmt(card["funding_paid"], 2),
                fmt(card["funding_received"], 2),
                fmt(card["gap_stop_exits"]),
                fmt(card["late_exit_data_missing"]),
                fmt(card["funding_invalid_events"]),
            ]
        )
    return table(
        [
            "System",
            "Decision→fill (min)",
            "Entries",
            "Rejected",
            "Friction paid",
            "Funding paid",
            "Funding received",
            "Gap stops",
            "Late exits",
            "Funding invalid",
        ],
        rows,
    )


def _episode_line(episode: dict[str, Any]) -> str:
    fact = episode["FACT"]
    return (
        f"- `{fact['decision_time']}` {fact['side']} → {fact['exit_kind']} "
        f"NET_R {fact['realized_net_r']:+.3f} (gross {fact['gross_pnl']:+.2f}, friction "
        f"{fact['friction_cost']:.2f}, funding {fact['funding_pnl']:+.2f}); median "
        f"{fact['forecast']['median_return']:+.5f}, realized r4h "
        f"{fact['realized_r4h_from_decision']:+.5f}; categories: "
        f"{', '.join(episode['categories']) or 'none'}"
    )


def autopsy_section(autopsy: dict[str, Any]) -> str:
    counts = autopsy["trade_category_counts"]
    missed = autopsy["missed_opportunities"]
    lines = [
        "### Category frequencies over all G2-V0 trades (FACT)",
        "",
        table(
            ["Category", "Trades", "Share"],
            [
                [name, fmt(count), pct(count / max(1, counts["denominator_trades"]))]
                for name, count in counts["counts"].items()
            ],
        ),
        "",
        f"Denominator: {counts['denominator_trades']} trades.",
        "",
        "### Favourable episodes (top NET_R)",
        *[_episode_line(e) for e in autopsy["favorable_episodes"]],
        "",
        "### Unfavourable episodes (bottom NET_R)",
        *[_episode_line(e) for e in autopsy["unfavorable_episodes"]],
        "",
        "### Deterministic pseudo-random trade episodes",
        *[_episode_line(e) for e in autopsy["pseudo_random_trade_episodes"]],
        "",
        "### Missed standardized opportunities (NO_TRADE with shadow NET_R ≥ +1R)",
        "",
        table(
            ["Class", "Episodes", "Mean counterfactual NET_R (diagnostic)"],
            [
                [name, fmt(v["episodes"]), fmt(v["mean_counterfactual_net_r"], 3)]
                for name, v in missed["class_counts"].items()
            ],
        ),
        "",
        (
            f"Episodes: {missed['episodes']}; of which the TREND_REFERENCE_POLICY selected the same "
            f"side at the first decision ({missed['counterfactual_reference_class']}): "
            f"{missed['trend_reference_selected_same_side']}."
        ),
        "",
        (
            "Each episode in `AUTOPSY.json` separates FACT → CAUSAL HYPOTHESIS → REQUIRED TEST. "
            "Hypotheses are not conclusions; no test was executed and G2-V0 was not modified."
        ),
    ]
    return "\n".join(lines)


def _primary_finding(results: dict[str, Any]) -> list[str]:
    crps = [i for i in results["uncertainty"]["forecast_comparisons"] if i["metric"] == "crps"]
    policy = results["uncertainty"]["policy_comparisons"]
    v0 = results["policy_scorecards"]["G2-V0"]
    lines = [
        (
            f"- G2-V0 total net return {pct(v0['total_net_return'])}, max drawdown "
            f"{pct(v0['max_drawdown'])}, {v0['trade_count']} trades, mean realized NET_R "
            f"{fmt(v0['mean_realized_net_r'], 4)}; 5% drawdown lock: "
            f"{v0['drawdown_stop_triggered_at'] or 'not triggered'}."
        ),
    ]
    for item in crps:
        lines.append(
            f"- CRPS G2-V0 − {item['versus']}: point {fmt(item['point'], 8)} "
            f"(p10 {fmt(item['p10'], 8)}, p90 {fmt(item['p90'], 8)}); negative favours G2-V0."
        )
    for item in policy:
        lines.append(
            f"- Mean 15m return G2-V0 − {item['versus']}: point {fmt(item['point'], 8)} "
            f"(p10 {fmt(item['p10'], 8)}, p90 {fmt(item['p90'], 8)}); positive favours G2-V0."
        )
    return lines


def results_markdown(results: dict[str, Any], autopsy: dict[str, Any]) -> str:
    runs = results["runs"]
    lines = [
        "# G2 Development Cycle 1 V1 — fixed batch results",
        "",
        HEADER,
        "",
        f"Status: `{results['status']}`  ",
        (
            f"Authorization: `{results['authorization_record']}` "
            f"({results['authorization_timestamp_utc']})  "
        ),
        (
            "Interval: 2020 initialization/training; 2021-01-01..2024-12-31 UTC scored; 2025+ "
            "never requested."
        ),
        "",
        "## Executed systems",
        "",
        table(
            ["Run", "Systems", "Run id", "Record-stream fingerprint"],
            [
                [
                    key,
                    ", ".join(VARIANTS[key].systems),
                    value["run_id"],
                    f"`{value['fingerprint'][:16]}…`",
                ]
                for key, value in runs.items()
            ],
        ),
        "",
        (
            f"`{CASH_SYSTEM}` is zero exposure (no simulation). Ablations are diagnostic only and "
            "cannot be promoted."
        ),
        "",
        "## Headline (development, uncertainty = 80% weekly-block interval)",
        "",
        *_primary_finding(results),
        "",
        "## Forecast scorecard (2021–2024, matured targets)",
        "",
        forecast_table(results),
        "",
        "## Policy scorecard (common 15m timeline, 10,000 USDT virtual equity at 2021-01-01)",
        "",
        policy_table(results),
        "",
        "## Execution scorecard",
        "",
        execution_table(results),
        "",
        "## Uncertainty (5,000 complete-UTC-week bootstrap replicates, seed 2026092702)",
        "",
        "Forecast (lower CRPS/Brier is better; negative Δ favours the first system):",
        "",
        uncertainty_table(results["uncertainty"]["forecast_comparisons"], 8),
        "",
        "Policy (positive Δ favours the first system):",
        "",
        uncertainty_table(results["uncertainty"]["policy_comparisons"], 8),
        "",
        (
            "This is an internal stability diagnostic, not independent validation and not a "
            "discovery p-value."
        ),
        "",
        "## Coverage",
        "",
        f"- Scored decisions: {fmt(results['coverage']['scored_decisions'])}",
        (
            f"- Forecast unavailable (scored) by reason: "
            f"{results['coverage']['scored_forecast_unavailable_by_reason']}"
        ),
        (
            f"- Zero-volume minutes 2020–2024 (retained, frozen semantics): "
            f"{results['coverage']['zero_volume_minutes_2020_2024']}"
        ),
        "",
        "## Autopsy (G2-V0)",
        "",
        autopsy_section(autopsy),
        "",
    ]
    return "\n".join(lines)


def checkpoint_markdown(results: dict[str, Any], autopsy: dict[str, Any]) -> str:
    determinism = results["determinism"]
    audit = results["reconciliation"]
    lines = [
        "# G2-02 Baseline and Diagnostics V1 — executor checkpoint",
        "",
        HEADER,
        "",
        f"Status: `{results['status']}`",
        "",
        "## What was executed",
        "",
        (
            "- G2-V0 exactly as frozen at Gate A/B (no parameter, feature, threshold, cost, risk or "
            "cycle change); cycle SHADOW_ONLY."
        ),
        (
            "- Fixed references: NULL_FORECAST, TREND_ONLY_FORECAST, TREND_REFERENCE_POLICY, "
            "CASH_REFERENCE (definitions from the frozen contract §23; not tuned)."
        ),
        (
            "- Diagnostic ablations: ABL-G2-01 (FULL_MINUS_PARTICIPATION_FLOW_RESPONSE), "
            "ABL-G2-02 (FULL_ADDITIVE_ONLY); same ridge/calendar/window/penalties."
        ),
        (
            f"- Ledger authorization `{results['authorization_record']}` appended at "
            f"{results['authorization_timestamp_utc']} before the first economic simulation."
        ),
        (
            "- No adaptive revision, change card, stress scenario, R1/R2/R3/RCYCLE, 2025+ access, "
            "candidate/Champion, paper trading or real money."
        ),
        "",
        "## Integrity",
        "",
        (
            f"- G2-V0 simulated twice: fingerprint identical = "
            f"{fmt(determinism['fingerprint_identical'])}, cache identical = "
            f"{fmt(determinism['cache_identical'])}."
        ),
        (
            "- Development core ≡ frozen `G2Core` for G2-V0 on the synthetic engineering path "
            "(record-stream fingerprint equality test)."
        ),
        "- Issued predictive quantiles re-derived bit-identically from the reconstructed "
        "residual sets before CRPS scoring: "
        + ", ".join(
            f"{s}={fmt(results['forecast_scorecards'][s]['reconstruction_verification']['bit_identical'])}"
            for s in FORECAST_SYSTEMS
        )
        + ".",
        "- Accounting/rule audits: "
        + "; ".join(
            f"{s}: trades reconcile={fmt(a['per_trade_net_equals_gross_minus_friction_plus_funding'])},"
            f" equity reconciles={fmt(a['realized_equity_change_equals_closed_net_plus_open_adjustment'])},"
            f" one position={fmt(a['one_position_at_a_time'])},"
            f" no pre-2021 entry={fmt(a['no_entry_before_economic_window'])},"
            f" no 2025+ observation={fmt(a['no_observation_at_or_after_2025'])}"
            for s, a in audit.items()
        ),
        "",
        "## Results summary",
        "",
        *_primary_finding(results),
        "",
        "## Forecast",
        "",
        forecast_table(results),
        "",
        "## Policy",
        "",
        policy_table(results),
        "",
        "## Execution",
        "",
        execution_table(results),
        "",
        "## Autopsy (G2-V0)",
        "",
        autopsy_section(autopsy),
        "",
        "## Artifacts",
        "",
        "- `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/RESULTS.json` (canonical result)",
        "- `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/AUTOPSY.json`",
        "- `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/TRADES-*.csv`",
        (
            "- `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/AUTHORIZATION.json`, "
            "`BATCH_MANIFEST.json`"
        ),
        "- `reports/validation/G2-02-DEVELOPMENT-BATCH-VALIDATION-V1.{json,md,log}`",
        "",
        "Interpretation and the next development allocation are Research Director decisions.",
        "",
    ]
    return "\n".join(lines)


def validation_payload(results: dict[str, Any], written: dict[str, str]) -> dict[str, Any]:
    return {
        "artifact": "G2-02-DEVELOPMENT-BATCH-VALIDATION-V1",
        "status": results["status"],
        "authorization_record": results["authorization_record"],
        "authorization_timestamp_utc": results["authorization_timestamp_utc"],
        "determinism": results["determinism"],
        "runs": results["runs"],
        "reconstruction_verification": {
            system: results["forecast_scorecards"][system]["reconstruction_verification"]
            for system in FORECAST_SYSTEMS
        },
        "reconciliation": results["reconciliation"],
        "pre_execution_focused_tests": [
            "backend/tests/test_g2_development.py",
            "backend/tests/test_operations_jobs.py",
        ],
        "development_core_equivalence": "G2-V0 DevelopmentCore record-stream fingerprint equals "
        "the frozen G2Core synthetic fingerprint (test_g2_development.py)",
        "artifacts_sha256": dict(sorted(written.items())),
        "claims": results["claims"],
    }


def validation_markdown(validation: dict[str, Any]) -> str:
    lines = [
        "# G2-02 Development Batch Validation V1",
        "",
        HEADER,
        "",
        f"Status: `{validation['status']}`  ",
        (
            f"Authorization: `{validation['authorization_record']}` "
            f"({validation['authorization_timestamp_utc']})"
        ),
        "",
        "## Determinism",
        "",
        (
            f"- G2-V0 repeat fingerprint identical: "
            f"{fmt(validation['determinism']['fingerprint_identical'])}"
        ),
        f"- G2-V0 repeat cache identical: {fmt(validation['determinism']['cache_identical'])}",
        "",
        "## Forecast distribution reconstruction (bit-identical issued quantiles)",
        "",
        table(
            ["System", "Checked", "Mismatched", "Bit-identical"],
            [
                [s, fmt(v["checked"]), fmt(v["mismatched"]), fmt(v["bit_identical"])]
                for s, v in validation["reconstruction_verification"].items()
            ],
        ),
        "",
        "## Accounting and rule audits",
        "",
        table(
            [
                "System",
                "Trade identity",
                "Equity reconciles",
                "One position",
                "No pre-2021 entry",
                "Entries after lock",
                "No 2025+ observation",
            ],
            [
                [
                    s,
                    fmt(a["per_trade_net_equals_gross_minus_friction_plus_funding"]),
                    fmt(a["realized_equity_change_equals_closed_net_plus_open_adjustment"]),
                    fmt(a["one_position_at_a_time"]),
                    fmt(a["no_entry_before_economic_window"]),
                    fmt(a["entries_after_drawdown_lock"]),
                    fmt(a["no_observation_at_or_after_2025"]),
                ]
                for s, a in validation["reconciliation"].items()
            ],
        ),
        "",
        f"Development-core equivalence: {validation['development_core_equivalence']}.",
        "",
    ]
    return "\n".join(lines)
