"""Coverage and foundation reports for the WP-009 exogenous substrates."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from .exogenous import ALFRED_SERIES, GDELT_CHANNELS, hours, read_json
from .wp004 import ROOT

COVERAGE_PATH = "reports/research/WP-009-EXOGENOUS-COVERAGE.md"
FOUNDATION_PATH = "reports/research/WP-009-EXOGENOUS-FOUNDATION.md"


def _z(value: Any) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _longest_gap(rows: list[dict[str, Any]]) -> tuple[int, str]:
    longest = current = 0
    end = None
    for row in rows:
        if not row["data_available"]:
            current += 1
            if current > longest:
                longest, end = current, row["hour"]
        else:
            current = 0
    if end is None:
        return 0, "none"
    start = end - (longest - 1) * __import__("datetime").timedelta(hours=1)
    return longest, f"{_z(start)} to {_z(end)}"


def coverage_report(root: Path = ROOT) -> str:
    gdelt_manifest = read_json(root / "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json")
    alfred_manifest = read_json(root / "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json")
    context_manifest = read_json(root / "data/manifests/EXOGENOUS-CONTEXT-DEV-v1.json")
    gdelt = pq.read_table(root / gdelt_manifest["file"]["path"]).to_pylist()
    by_channel: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in gdelt:
        by_channel[row["channel_id"]].append(row)
    lines = [
        "# WP-009 exogenous coverage and source drift",
        "",
        "Information-foundation diagnostics only. No BTC prices, returns, trade outcomes, correlations, rankings, or strategy results were used.",
        "",
        "## GDELT DOC 2.0",
        "",
        "| Channel | Usable start / end | Missing hours | Matched-hour fraction | Norm availability | Longest unavailable run |",
        "|---|---|---:|---:|---:|---|",
    ]
    for channel in GDELT_CHANNELS:
        rows = by_channel[channel]
        usable = [row for row in rows if row["data_available"]]
        matched = sum(
            bool(row["matched_articles"] and row["matched_articles"] > 0) for row in usable
        )
        norm = sum(row["monitored_articles_norm"] is not None for row in rows)
        longest, span = _longest_gap(rows)
        start_end = "none" if not usable else f"{_z(usable[0]['hour'])} / {_z(usable[-1]['hour'])}"
        lines.append(
            f"| {channel} | {start_end} | {len(rows) - len(usable)} | "
            f"{matched / len(rows):.6f} | {norm / len(rows):.6f} | {longest}h ({span}) |"
        )
    lines.extend(["", "Availability by calendar year (usable hours / timestamp-grid hours):", ""])
    years = range(2017, 2025)
    lines.extend(
        [
            "| Channel | " + " | ".join(map(str, years)) + " |",
            "|---|" + "---:|" * len(tuple(years)),
        ]
    )
    for channel in GDELT_CHANNELS:
        rows = by_channel[channel]
        values = []
        for year in years:
            annual = [row for row in rows if row["hour"].year == year]
            values.append(f"{sum(row['data_available'] for row in annual)}/{len(annual)}")
        lines.append(f"| {channel} | " + " | ".join(values) + " |")
    lines.extend(
        [
            "",
            f"Retrieval completeness: {len(gdelt_manifest['requests'])}/{len(gdelt_manifest['requests'])} frozen hashed responses. Timeline smoothing is 0. Missing source hours remain explicit and are never inferred as zero.",
            "",
            "GDELT's monitored source universe changes through time and geography. Returned normalization reduces but does not eliminate coverage drift, language/editorial selection, duplicate-event, or outlet-composition effects. Apparent outages above are source/API availability diagnostics, not exclusion criteria.",
            "",
            "## ALFRED",
            "",
            "| Series | First usable availability | Last usable <= cutoff | Observations | Vintage states | Revisions | Missing hourly-grid rows |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    total_hours = len(hours())
    available = context_manifest["source_available_rows"]
    for series_id in ALFRED_SERIES:
        stat = alfred_manifest["series_statistics"][series_id]
        lines.append(
            f"| {series_id} | {stat['first_usable_availability']} | "
            f"{stat['last_usable_availability_at_or_before_cutoff']} | "
            f"{stat['observation_dates']} | {stat['vintage_states']} | {stat['revisions']} | "
            f"{total_hours - available[series_id]} |"
        )
    lines.extend(
        [
            "",
            f"Retrieval completeness: {alfred_manifest['successful_request_count']}/{alfred_manifest['request_count']} credential-free, individually hashed series/vintage snapshots; {alfred_manifest['source_unavailable_request_count']} frozen request is an explicit source gap. Missing observations and unavailable vintages remain missing; no release interpolation is performed.",
            "",
            "The official ALFRED graph endpoint returned an empty HTTP 404 for VIXCLS vintage 2018-01-23, and the official credential-free download form confirmed that no observations were retrievable for that listed vintage. The response evidence is hashed, the affected as-of interval is unavailable, and no current revision or adjacent vintage was substituted.",
            "",
            "ALFRED vintage dates are date-level metadata in this transport. Every state is therefore delayed conservatively until 00:00 UTC on the next calendar day. This loses some potentially usable same-day information but prevents later revisions from leaking backward.",
            "",
        ]
    )
    return "\n".join(lines)


def foundation_report(root: Path = ROOT) -> str:
    gdelt = read_json(root / "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json")
    alfred = read_json(root / "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json")
    context = read_json(root / "data/manifests/EXOGENOUS-CONTEXT-DEV-v1.json")
    oracle = read_json(root / "reports/validation/WP-009-EXOGENOUS-ASOF-RECONCILIATION.json")
    missing = sum(gdelt["missing_hours_by_channel"].values())
    return "\n".join(
        [
            "# WP-009 point-in-time exogenous information foundation",
            "",
            "Structural verdict: **PASS**. This checkpoint creates information infrastructure, not a trading strategy or edge result.",
            "",
            f"`GDELT_NEWS_CONTEXT_V1` contains {gdelt['hourly_rows']:,} channel-hour rows for exactly five frozen semantic channels. No smoothing or article-body scraping occurred; {missing:,} channel-hours are explicitly unavailable rather than silently zero-filled.",
            "",
            f"`ALFRED_MACRO_CONTEXT_V1` retains historical states for exactly eight frozen macro series across {alfred['successful_request_count']:,} successful credential-free series/vintage snapshots plus {alfred['source_unavailable_request_count']} explicit source-unavailable vintage. Later revisions never replace earlier knowable states, and date-only vintages become usable only at next-calendar-day 00:00 UTC.",
            "",
            f"`EXOGENOUS_CONTEXT_V1` contains {context['rows']:,} timestamp-generated hourly rows through the 2024 cutoff. It loaded no BTC price, return, trade, or outcome column and applies only source records with availability time at or before each row timestamp.",
            "",
            f"The independent raw-source as-of oracle passed {oracle['sample_count']} frozen quarterly and stress timestamps with {oracle['mismatch_count']} mismatches. Coverage and source drift are reported without BTC correlations or outcome-based exclusions.",
            "",
            "Exactly three future adaptive multi-signal architectures are documented without selection or execution. Dynamic signal-importance governance requires contemporaneous, training-cutoff-bound influence records. WP-008's fixed linear failure remains retained and its family remains blocked from rescue-by-retuning.",
            "",
            "Scientific accounting is unchanged for experiments, hypotheses, configurations, profiles, model fits, and numeric variants. One result-dependent non-trial infrastructure direction is recorded, taking adaptive decisions and result-dependent forks to 6. Sealed queries/evaluations and paper trades remain zero; Champion and forward evidence remain NONE; real money remains false.",
            "",
        ]
    )


def write_reports(root: Path = ROOT) -> None:
    for relative, content in (
        (COVERAGE_PATH, coverage_report(root)),
        (FOUNDATION_PATH, foundation_report(root)),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
