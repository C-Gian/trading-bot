"""G2-02 fixed batch: authorization, parallel execution, scoring, uncertainty, autopsy, artifacts.

Order of operations (task G2_02 sections B-C and "Executed systems"):
1. focused deterministic tests (run by the operator before authorization);
2. `authorize`: append the real-UTC ledger authorization record (code/data/filter hashes, every
   identity, scorecard/uncertainty/autopsy rules, no adaptive revision) BEFORE any economic run;
3. `execute`: simulate G2-V0, ABL-G2-01, ABL-G2-02, the TREND reference run and the NULL run in
   parallel worker processes (+ a byte-identical G2-V0 repeat for determinism), with progress;
4. `build`: deterministic scorecards, weekly-block uncertainty, reconciliation audits, autopsy and
   artifacts, then one executed-record ledger entry per system.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from ..contract import BASE_FRICTION_SCENARIO, FRICTION_SCENARIOS, frozen_identity
from ..sources import (
    EXCHANGE_INFO_MANIFEST,
    FUNDING_MANIFEST,
    KLINE_MANIFEST,
    ROOT,
    pinned_market_filters,
)
from ..validation import text_sha256
from . import autopsy, scoring
from .runner import (
    AUTHORIZATION_RECORD,
    CACHE_DIR,
    CACHE_SCHEMA,
    EVIDENCE_CLASS,
    PACKAGE,
    cache_dir,
    cache_identity,
    read_cache,
    run_variant,
    scored_mask,
)
from .variants import (
    BATCH,
    CASH_SYSTEM,
    ECONOMIC_START,
    FORECAST_COMPARISONS,
    FORECAST_SYSTEMS,
    INITIALIZATION_START,
    OBSERVATION_END,
    POLICY_COMPARISONS,
    POLICY_SYSTEMS,
    SYSTEM_RUN,
    VARIANTS,
)

LEDGER = "research/g2/G2_RESEARCH_LEDGER_V1.jsonl"
EXPERIMENT_DIR = "research/experiments/G2-DEVELOPMENT-CYCLE-1-V1"
RESULTS_PATH = f"{EXPERIMENT_DIR}/RESULTS.json"
AUTOPSY_PATH = f"{EXPERIMENT_DIR}/AUTOPSY.json"
AUTHORIZATION_PATH = f"{EXPERIMENT_DIR}/AUTHORIZATION.json"
BATCH_MANIFEST_PATH = f"{EXPERIMENT_DIR}/BATCH_MANIFEST.json"
VALIDATION_PATH = "reports/validation/G2-02-DEVELOPMENT-BATCH-VALIDATION-V1.json"
VALIDATION_LOG = "reports/validation/G2-02-DEVELOPMENT-BATCH-VALIDATION-V1.log"
VALIDATION_REPORT = "reports/validation/G2-02-DEVELOPMENT-BATCH-VALIDATION-V1.md"
CHECKPOINT_REPORT = "reports/checkpoints/G2-02-BASELINE-AND-DIAGNOSTICS-V1.md"
RESULTS_REPORT = f"{EXPERIMENT_DIR}/README.md"
TRADES_SYSTEMS = ("G2-V0", "ABL-G2-01", "ABL-G2-02", "TREND_REFERENCE_POLICY")
REPEAT_KEY = "G2-V0"
STATUS = "EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_G2_02_REVIEW"
FROZEN_CODE = tuple(
    f"backend/app/g2/{name}.py"
    for name in (
        "bars",
        "contract",
        "core",
        "cycle",
        "distribution",
        "execution",
        "features",
        "models",
        "records",
        "risk",
        "runs",
        "sources",
        "store",
    )
)
DEVELOPMENT_CODE = tuple(
    f"backend/app/g2/development/{name}.py"
    for name in (
        "__init__",
        "variants",
        "core",
        "runner",
        "scoring",
        "autopsy",
        "reports",
        "batch",
    )
) + ("scripts/run_g2_development.py",)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def dumps(payload: Any) -> str:
    return json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_ledger(root: Path) -> list[dict[str, Any]]:
    path = root / LEDGER
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def append_ledger(root: Path, record: dict[str, Any]) -> None:
    ids = {entry["record_id"] for entry in read_ledger(root)}
    if record["record_id"] in ids:
        raise ValueError(f"ledger record {record['record_id']} already exists (append-only)")
    line = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
    with (root / LEDGER).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")


# ---------------------------------------------------------------------- authorization
def data_identity(root: Path) -> dict[str, Any]:
    """Metadata only (manifests and the pinned filter snapshot); no observation object is read."""
    kline = json.loads((root / KLINE_MANIFEST).read_text(encoding="utf-8"))
    funding = json.loads((root / FUNDING_MANIFEST).read_text(encoding="utf-8"))
    snapshot = json.loads((root / EXCHANGE_INFO_MANIFEST).read_text(encoding="utf-8"))
    filters = pinned_market_filters(root)
    return {
        "kline_manifest": KLINE_MANIFEST,
        "kline_manifest_id": kline["manifest_id"],
        "kline_object_index_sha256": kline["object_index_sha256"],
        "funding_manifest": FUNDING_MANIFEST,
        "funding_manifest_id": funding["manifest_id"],
        "funding_file_sha256": funding["canonical"]["file_sha256"],
        "exchange_info_manifest": EXCHANGE_INFO_MANIFEST,
        "exchange_info_raw_sha256": snapshot["raw_snapshot_sha256"],
        "exchange_filters_source": filters.source,
        "exchange_filters_sha256": filters.sha256(),
        "exchange_filters": dict(filters.as_pairs()),
    }


def code_identity(root: Path) -> dict[str, str]:
    return {path: text_sha256(root / path) for path in FROZEN_CODE + DEVELOPMENT_CODE}


def scorecard_definitions() -> dict[str, Any]:
    return {
        "forecast": {
            "primary": "mean CRPS of the issued empirical predictive distribution (return units)",
            "secondary": [
                "q10/q50/q90 pinball loss",
                "Brier score of r4h > 0 using uncalibrated p_positive",
                "q10-q90 empirical coverage",
                "MAE of the median forecast",
                "direction hit rate (descriptive only)",
                (
                    "fixed strata: view strength WEAK <0.25 / MODERATE <0.75 / STRONG, by residual "
                    "evidence source"
                ),
                "availability/support counts",
            ],
            "scored_decisions": "2021-01-01T00:00Z <= T < 2025-01-01T00:00Z with a forecast "
            "and a matured 4h target",
        },
        "policy": {
            "primary": "common-timeline simulated portfolio net return relative CASH: mean "
            "simple 15m return of marked equity on the 2021-01-01..2025-01-01 UTC grid",
            "secondary": [
                "mean realized NET_R of executed trades",
                "total net return",
                "max drawdown and time under water (marked 15m grid)",
                "turnover per year",
                "occupancy (position time fraction)",
                "LONG/SHORT mix",
                "friction and funding share of |gross|",
                "trade count and calendar distribution (year/quarter), top-5 concentration",
                "NO_TRADE primary reasons (fixed precedence) and all reason-code counts",
                (
                    "standardized LONG/SHORT shadow NET_R distributions (unconditional and "
                    "policy-selected)"
                ),
            ],
            "economic_window": "no economic position may be opened before 2021-01-01T00:00Z; "
            "initial virtual equity 10,000 USDT at the window start",
        },
        "execution": [
            "decision-to-fill delay",
            "raw vs accounting fills (12bp/side convention)",
            "friction paid; funding paid/received",
            "gap stops, ambiguous fills, rejected entries, late exits, funding-invalid events",
            "entry implementation shortfall vs decision close (no historical quotes exist)",
        ],
    }


def uncertainty_rules() -> dict[str, Any]:
    return {
        "blocks": "contiguous UTC calendar weeks (Monday 00:00) of the scored window; the "
        "partial first/last weeks are their own blocks",
        "resampling": "complete weeks with replacement; one common resampling matrix for "
        "every comparison",
        "replicates": scoring.REPLICATES,
        "seed": scoring.SEED,
        "rng": "numpy.random.default_rng(seed).integers(0, weeks, size=(replicates, weeks))",
        "reported": "point delta and 10th/50th/90th percentiles",
        "forecast_comparisons": [list(pair) for pair in FORECAST_COMPARISONS],
        "forecast_paired_metrics": ["crps", "brier"],
        "policy_comparisons": [list(pair) for pair in POLICY_COMPARISONS],
        "policy_paired_metric": "15m marked-equity simple return (common grid)",
        "path_metrics": "max drawdown reported raw plus a weekly-block path distribution",
        "interpretation": "internal stability diagnostic only; not independent validation and "
        "not a discovery p-value",
    }


def autopsy_rules() -> dict[str, Any]:
    return {
        "system": "G2-V0",
        "favorable_trades": autopsy.FAVORABLE_N,
        "unfavorable_trades": autopsy.UNFAVORABLE_N,
        "pseudo_random_trades": autopsy.RANDOM_TRADES_N,
        "pseudo_random_missed_episodes": autopsy.RANDOM_MISSED_N,
        "seed": f"SeedSequence({scoring.SEED}, spawn_key={autopsy.AUTOPSY_SPAWN_KEY})",
        "standardized_opportunity": f"shadow NET_R >= +{autopsy.OPPORTUNITY_NET_R}R at a "
        "NO_TRADE decision; episodes group qualifying decisions <= 4h apart; representative "
        "= first decision",
        "missed_classes": [
            autopsy.MODEL,
            autopsy.RISK,
            autopsy.EXECUTION,
            autopsy.COUNTERFACTUAL,
        ],
        "extended_entry_threshold_scaled_units": autopsy.EXTENDED_SCALED,
        "structure": "FACT -> CAUSAL HYPOTHESIS -> REQUIRED TEST; no test executed in G2-02",
    }


def authorization_payload(root: Path) -> dict[str, Any]:
    return {
        "record_type": "DEVELOPMENT_RUN_AUTHORIZATION",
        "record_id": AUTHORIZATION_RECORD,
        "timestamp_utc": utc_now(),
        "generation": "G2_DEVELOPMENT_SYSTEM",
        "work_package": PACKAGE,
        "package_version": "tasks/G2_02_BASELINE_AND_DIAGNOSTICS_V1.md",
        "package_sha256": text_sha256(root / "tasks/G2_02_BASELINE_AND_DIAGNOSTICS_V1.md"),
        "author": "Claude Code (AI executor, overflow for Codex)",
        "evidence_class": EVIDENCE_CLASS,
        "interval": {
            "initialization_training": [
                INITIALIZATION_START.isoformat(),
                ECONOMIC_START.isoformat(),
            ],
            "scored_exposed_development": [
                ECONOMIC_START.isoformat(),
                OBSERVATION_END.isoformat(),
            ],
            "end_exclusive": True,
            "forbidden": "any 2025+ observation (phase-bounded loader refuses it before I/O)",
        },
        "code_sha256": code_identity(root),
        "data": data_identity(root),
        "frozen_contract_identity_sha256": sha256_text(dumps(frozen_identity())),
        "friction": {
            "scenario": BASE_FRICTION_SCENARIO,
            "per_side": FRICTION_SCENARIOS[BASE_FRICTION_SCENARIO],
            "stress_scenarios_executed": False,
        },
        "baseline": VARIANTS["G2-V0"].identity(),
        "references": {
            "NULL_FORECAST": VARIANTS["NULL-FORECAST"].identity(),
            "TREND_ONLY_FORECAST+TREND_REFERENCE_POLICY": VARIANTS["TREND-REFERENCE"].identity(),
            CASH_SYSTEM: {"definition": "zero exposure"},
        },
        "ablations": {
            "ABL-G2-01": VARIANTS["ABL-G2-01"].identity(),
            "ABL-G2-02": VARIANTS["ABL-G2-02"].identity(),
        },
        "common_state_support": "all systems share the eight-column G2-V0 state availability "
        "and training-row finiteness gates",
        "scorecards": scorecard_definitions(),
        "uncertainty": uncertainty_rules(),
        "autopsy": autopsy_rules(),
        "determinism": "G2-V0 simulated twice; fingerprints and cache hashes must be identical",
        "adaptive_revision_authorized": False,
        "statement": "No adaptive revision is authorized. G2-V0, the four references and the two "
        "ablations are executed as frozen, once each (G2-V0 is additionally re-simulated once, "
        "unchanged, only to prove byte-identical determinism); no parameter, feature, threshold, "
        "cost, risk or cycle change; no change card; no R1/R2/R3/RCYCLE; no 2025+ access.",
        "general_revision_slots_consumed": 0,
        "cycle_revision_slots_consumed": 0,
        "protected_outcomes_read": False,
        "sealed_queries": 0,
        "real_money_authorized": False,
    }


def authorize(root: Path = ROOT) -> dict[str, Any]:
    ids = {entry["record_id"] for entry in read_ledger(root)}
    if AUTHORIZATION_RECORD in ids:
        raise ValueError("the G2-02 run authorization already exists (append-only)")
    payload = authorization_payload(root)
    append_ledger(root, payload)
    path = root / AUTHORIZATION_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(payload), encoding="utf-8")
    return payload


def authorization_record(root: Path) -> dict[str, Any]:
    for entry in read_ledger(root):
        if entry["record_id"] == AUTHORIZATION_RECORD:
            return entry
    raise LookupError("no G2-02 run authorization in the ledger: execution is refused")


# ---------------------------------------------------------------------- execution
def _worker(run_key: str, root_text: str, parent_job: str, repeat: bool) -> dict[str, Any]:
    from app.operations.jobs import Job

    root = Path(root_text)
    label = f"{run_key}{'-REPEAT' if repeat else ''}"
    phases = ["load sources", "simulate", "fingerprint", "extract"]
    job = Job("g2-02-worker", phases, root, job_id=f"{parent_job}--{label}")
    state: dict[str, str | None] = {"phase": None}

    def progress(phase: str, done: int | None, total: int | None, text: str) -> None:
        if phase != state["phase"]:
            state["phase"] = phase
            job.phase(phase, total, "simulated minutes" if total else None, f"{label}: {text}")
        elif done is not None:
            job.advance(done, f"{label}: {text}")

    with job:
        if repeat:
            # The repeat writes to its own cache directory and is compared, then removed.
            from . import runner

            original = runner.CACHE_DIR
            runner.CACHE_DIR = original / "_repeat"
            try:
                result = run_variant(run_key, root, progress)
            finally:
                runner.CACHE_DIR = original
        else:
            result = run_variant(run_key, root, progress)
    result["repeat"] = repeat
    return result


def execute(root: Path, job: Any, workers: int) -> dict[str, Any]:
    authorization = authorization_record(root)
    if authorization["code_sha256"] != code_identity(root):
        raise RuntimeError("code changed after the ledger authorization: execution refused")
    tasks = [(variant.run_key, False) for variant in BATCH] + [(REPEAT_KEY, True)]
    total_minutes = int((OBSERVATION_END - INITIALIZATION_START).total_seconds() // 60)
    job.phase(
        "simulate batch",
        total_minutes * len(tasks),
        "simulated minutes (all systems)",
        f"{len(tasks)} worker simulations",
    )
    job.set_aggregate(lambda: _aggregate(root, job.job_id, tasks, total_minutes))
    results: dict[str, Any] = {}
    with ProcessPoolExecutor(max_workers=min(workers, len(tasks))) as pool:
        futures = {
            pool.submit(_worker, key, str(root), job.job_id, repeat): (key, repeat)
            for key, repeat in tasks
        }
        for future in as_completed(futures):
            key, repeat = futures[future]
            result = future.result()
            results[f"{key}{'#repeat' if repeat else ''}"] = result
            job.log(
                f"worker {key}{' (repeat)' if repeat else ''} done: run_id={result['run_id']} "
                f"fingerprint={result['fingerprint']} elapsed={result['elapsed_seconds']}s"
            )
    job.set_aggregate(None)
    first, second = results[REPEAT_KEY], results[f"{REPEAT_KEY}#repeat"]
    identical = first["fingerprint"] == second["fingerprint"] and first["cache"] == second["cache"]
    shutil.rmtree(root / CACHE_DIR / "_repeat", ignore_errors=True)
    manifest = {
        "schema": CACHE_SCHEMA,
        "authorization_record": AUTHORIZATION_RECORD,
        "runs": {
            key: {k: v for k, v in results[key].items() if k != "repeat"}
            for key in (variant.run_key for variant in BATCH)
        },
        "determinism": {
            "repeated_run": REPEAT_KEY,
            "fingerprint_identical": first["fingerprint"] == second["fingerprint"],
            "cache_identical": first["cache"] == second["cache"],
            "repeat_fingerprint": second["fingerprint"],
        },
    }
    if not identical:
        raise RuntimeError("G2-V0 repeat run differs: the batch is not deterministic")
    (root / CACHE_DIR / "run_manifest.json").write_text(dumps(manifest), encoding="utf-8")
    return manifest


def _aggregate(
    root: Path, parent: str, tasks: list[tuple[str, bool]], total: int
) -> dict[str, Any]:
    from app.operations.jobs import read_job

    done = 0
    children: list[dict[str, Any]] = []
    for key, repeat in tasks:
        label = f"{key}{'-REPEAT' if repeat else ''}"
        state = read_job(f"{parent}--{label}", root, tail=0)
        if state is None:
            children.append({"worker": label, "status": "QUEUED"})
            continue
        phase = state.get("phase")
        if state.get("status") == "PASS" or phase in ("fingerprint", "extract"):
            units = total
        elif phase == "simulate":
            units = int(state.get("completed_units") or 0)
        else:
            units = 0
        done += units
        children.append(
            {
                "worker": label,
                "status": state.get("status"),
                "phase": phase,
                "completed_units": units,
                "message": state.get("message"),
            }
        )
    busy = [c["worker"] for c in children if c.get("status") == "RUNNING"]
    return {
        "completed_units": done,
        "children": children,
        "message": f"running: {', '.join(busy) if busy else 'none'}",
    }


# ---------------------------------------------------------------------- scoring
def _load(root: Path) -> tuple[dict[str, Any], dict[str, tuple[dict[str, Any], dict[str, Any]]]]:
    manifest = json.loads((root / CACHE_DIR / "run_manifest.json").read_text(encoding="utf-8"))
    caches = {}
    for variant in BATCH:
        identity = cache_identity(root, variant.run_key)
        if identity != manifest["runs"][variant.run_key]["cache"]:
            raise RuntimeError(f"{variant.run_key}: run cache differs from the run manifest")
        caches[variant.run_key] = read_cache(root, variant.run_key)
    return manifest, caches


def reconcile(system: str, arrays: dict[str, Any], events: dict[str, Any]) -> dict[str, Any]:
    """Deterministic accounting / rule-compliance audit of one simulated system."""
    trades = events["trades"]
    per_trade = all(
        abs(t["net_pnl"] - (t["gross_pnl"] - t["friction_cost"] + t["funding_pnl"])) < 1e-6
        and abs(t["realized_net_r"] - t["net_pnl"] / t["planned_risk"]) < 1e-9
        for t in trades
    )
    open_trade = events["open_trade_at_end"]
    open_adjust = 0.0
    if open_trade is not None:
        friction = FRICTION_SCENARIOS[BASE_FRICTION_SCENARIO]
        open_adjust = (
            -open_trade["quantity"] * open_trade["raw_entry"] * friction + open_trade["funding_pnl"]
        )
    realized = events["final_governor"]["equity"] - 10_000.0
    closed = sum(t["net_pnl"] for t in trades)
    intervals = sorted((t["entry_time"], t["exit_time"]) for t in trades)
    non_overlapping = all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:], strict=False))
    first_entry = intervals[0][0] if intervals else None
    lock_times = [
        e["event_time"] for e in events["risk_events"] if e["kind"] == "DRAWDOWN_STOP_TRIGGERED"
    ]
    after_lock = (
        [t for t in trades if lock_times and t["entry_time"] > lock_times[0]] if lock_times else []
    )
    loader = events["loader_log"]
    # `returned` holds [first open, last availability]: the last 2024 minute becomes available
    # exactly at 2025-01-01T00:00Z, so "at or before the exclusive end" means no 2025 minute.
    returned = [
        datetime.fromisoformat(str(entry["returned"][1]))
        for entry in loader
        if entry.get("returned")
    ]
    last = max(returned, default=None)
    returned_max = None if last is None else last.isoformat()
    scored = scored_mask(arrays["t"])
    return {
        "system": system,
        "per_trade_net_equals_gross_minus_friction_plus_funding": per_trade,
        "realized_equity_change_equals_closed_net_plus_open_adjustment": abs(
            realized - (closed + open_adjust)
        )
        < 1e-6,
        "realized_equity_change": realized,
        "closed_trade_net_sum": closed,
        "one_position_at_a_time": non_overlapping,
        "first_entry_time": first_entry,
        "no_entry_before_economic_window": first_entry is None
        or first_entry >= ECONOMIC_START.isoformat().replace("+00:00", "Z"),
        "drawdown_lock_time": lock_times[0] if lock_times else None,
        "entries_after_drawdown_lock": len(after_lock),
        "loader_max_returned_instant": returned_max,
        "no_observation_at_or_after_2025": last is not None and last <= OBSERVATION_END,
        "invalid_minutes": events["invalid_minutes"],
        "scored_decisions": int(scored.sum()),
    }


def _pair_forecast(
    contributions: dict[str, dict[str, Any]],
    arrays: dict[str, dict[str, Any]],
    boot: scoring.WeeklyBootstrap,
    metric: str,
    a: str,
    b: str,
) -> dict[str, Any]:
    ta, tb = arrays[a]["t"], arrays[b]["t"]
    if not np.array_equal(ta, tb):
        raise RuntimeError("forecast systems do not share one decision grid")
    realized_equal = np.array_equal(
        np.nan_to_num(arrays[a]["realized"], nan=0.0), np.nan_to_num(arrays[b]["realized"], nan=0.0)
    )
    both = contributions[a]["usable"] & contributions[b]["usable"]
    delta = np.where(both, contributions[a][metric] - contributions[b][metric], np.nan)
    weeks = scoring.week_index(ta)
    return {
        "system": a,
        "versus": b,
        "metric": metric,
        "delta_definition": f"mean({metric}[{a}] - {metric}[{b}]) on common support; negative "
        "favours the first system (lower is better)",
        "common_support": int(both.sum()),
        "realized_targets_identical": bool(realized_equal),
        **boot.mean_distribution(delta, weeks),
    }


def build(root: Path = ROOT) -> dict[str, Any]:
    manifest, caches = _load(root)
    authorization = authorization_record(root)
    arrays = {key: caches[key][0] for key in caches}
    events = {key: caches[key][1] for key in caches}
    system_arrays = {system: arrays[run] for system, run in SYSTEM_RUN.items()}
    system_events = {system: events[run] for system, run in SYSTEM_RUN.items()}
    grid = arrays["G2-V0"]["t"]
    for key in arrays:
        if not np.array_equal(arrays[key]["t"], grid):
            raise RuntimeError(f"{key} does not share the common decision grid")
    scored = scored_mask(grid)
    boot = scoring.WeeklyBootstrap(scoring.week_index(grid[scored]))

    # ---- forecast
    contributions = {
        system: scoring.forecast_contributions(system_arrays[system]) for system in FORECAST_SYSTEMS
    }
    forecast = {
        system: scoring.forecast_scorecard(system_arrays[system], contributions[system])
        for system in FORECAST_SYSTEMS
    }
    forecast_uncertainty = [
        _pair_forecast(contributions, system_arrays, boot, metric, a, b)
        for a, b in FORECAST_COMPARISONS
        for metric in ("crps", "brier")
    ]

    # ---- policy / execution
    policy = {}
    execution = {}
    returns: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for system in POLICY_SYSTEMS:
        if system == CASH_SYSTEM:
            policy[system] = scoring.policy_scorecard(system, None, None, None)
            execution[system] = scoring.execution_scorecard(system, None)
            continue
        data, info = system_arrays[system], system_events[system]
        policy[system] = scoring.policy_scorecard(system, data, info, info["reason_sets"])
        execution[system] = scoring.execution_scorecard(system, info)
        t, marked = scoring.equity_path(data)
        returns[system] = scoring.interval_returns(t, marked)
    starts = returns["G2-V0"][0]
    returns[CASH_SYSTEM] = (starts, np.zeros_like(returns["G2-V0"][1]))
    weeks = scoring.week_index(starts)
    policy_uncertainty = []
    for a, b in POLICY_COMPARISONS:
        if not np.array_equal(returns[a][0], returns[b][0]):
            raise RuntimeError("policy systems do not share the common timeline")
        delta = returns[a][1] - returns[b][1]
        policy_uncertainty.append(
            {
                "system": a,
                "versus": b,
                "metric": "15m marked-equity simple return",
                "delta_definition": f"mean(r[{a}] - r[{b}]) per 15m interval; positive "
                "favours the first system",
                **boot.mean_distribution(delta, weeks),
            }
        )
    path_distributions = {
        system: {
            "raw_max_drawdown": policy[system]["max_drawdown"],
            "weekly_block_path_max_drawdown": boot.max_drawdown_distribution(
                returns[system][1], weeks
            ),
        }
        for system in POLICY_SYSTEMS
        if system != CASH_SYSTEM
    }
    for system in POLICY_SYSTEMS:
        if system != CASH_SYSTEM:
            policy[system]["weekly_mean_return_bootstrap"] = boot.mean_distribution(
                returns[system][1], weeks
            )

    # ---- audits, coverage, anomalies, autopsy
    audits = {
        system: reconcile(system, system_arrays[system], system_events[system])
        for system in ("G2-V0", "ABL-G2-01", "ABL-G2-02", "TREND_REFERENCE_POLICY", "NULL_FORECAST")
    }
    coverage = coverage_report(system_arrays["G2-V0"], system_events["G2-V0"])
    anomalies = {
        system: anomaly_report(system_arrays[system], system_events[system])
        for system in ("G2-V0", "ABL-G2-01", "ABL-G2-02", "TREND_REFERENCE_POLICY", "NULL_FORECAST")
    }
    autopsy_payload = autopsy.build(
        system_arrays["G2-V0"], system_events["G2-V0"], system_arrays["TREND_REFERENCE_POLICY"]
    )
    results = {
        "artifact": "G2-DEVELOPMENT-CYCLE-1-V1/RESULTS",
        "work_package": PACKAGE,
        "status": STATUS,
        "evidence_class": EVIDENCE_CLASS,
        "evidence_statement": "Exposed development evidence only. Not validation, not a "
        "discovery test, not a candidate or Champion. Production action remains NO_TRADE.",
        "authorization_record": AUTHORIZATION_RECORD,
        "authorization_timestamp_utc": authorization["timestamp_utc"],
        "systems": {
            "baseline": ["G2-V0"],
            "fixed_references": [
                "NULL_FORECAST",
                "TREND_ONLY_FORECAST",
                "TREND_REFERENCE_POLICY",
                CASH_SYSTEM,
            ],
            "diagnostic_ablations": ["ABL-G2-01", "ABL-G2-02"],
            "ablations_promotable": False,
        },
        "runs": {
            key: {
                "run_id": value["run_id"],
                "fingerprint": value["fingerprint"],
                "record_counts": value["record_counts"],
                "cache_sha256": value["cache"],
            }
            for key, value in manifest["runs"].items()
        },
        "determinism": manifest["determinism"],
        "forecast_scorecards": forecast,
        "policy_scorecards": policy,
        "execution_scorecards": execution,
        "uncertainty": {
            "rules": uncertainty_rules(),
            "weeks": len(boot.weeks),
            "forecast_comparisons": forecast_uncertainty,
            "policy_comparisons": policy_uncertainty,
            "path_distributions": path_distributions,
        },
        "coverage": coverage,
        "data_execution_anomalies": anomalies,
        "reconciliation": audits,
        "autopsy_artifact": AUTOPSY_PATH,
        "claims": {
            "adaptive_revision_executed": False,
            "change_card_created": False,
            "stress_scenarios_executed": False,
            "protected_2025_outcomes_read": False,
            "candidate_or_champion_declared": False,
            "paper_trading_enabled": False,
            "real_money_authorized": False,
            "validated_strategy": None,
            "sealed_queries": 0,
        },
    }
    return {"results": results, "autopsy": autopsy_payload, "manifest": manifest}


def coverage_report(arrays: dict[str, Any], events: dict[str, Any]) -> dict[str, Any]:
    scored = scored_mask(arrays["t"])
    reason_sets = events["reason_sets"]
    unavailable: dict[str, int] = {}
    for index in arrays["reasons"][scored & ~arrays["forecast_available"]]:
        for code in reason_sets[int(index)].split("|"):
            if code.startswith("FORECAST_UNAVAILABLE"):
                unavailable[code] = unavailable.get(code, 0) + 1
    all_unavailable: dict[str, int] = {}
    post_2020_warm = arrays["t"] >= 0
    for index in arrays["reasons"][post_2020_warm & ~arrays["forecast_available"]]:
        for code in reason_sets[int(index)].split("|"):
            if code.startswith("FORECAST_UNAVAILABLE"):
                all_unavailable[code] = all_unavailable.get(code, 0) + 1
    return {
        "scored_decisions": int(scored.sum()),
        "scored_forecast_unavailable_by_reason": dict(sorted(unavailable.items())),
        "all_run_forecast_unavailable_by_reason_including_2020_warmup": dict(
            sorted(all_unavailable.items())
        ),
        "zero_volume_minutes_2020_2024": events["zero_volume_minutes"],
        "source_minutes": events["source_minutes"],
        "funding_records": events["funding_records"],
        "zero_volume_semantics": "retained under frozen V0 fail-closed semantics (taker "
        "imbalance undefined when V <= 0); not reclassified, deleted or interpolated",
        "preflight_reference": "reports/validation/G2-02-DATA-INTEGRITY-PREFLIGHT-V1.json "
        "(332 zero-volume minutes; 16 post-warmup unavailable decision instants)",
    }


def anomaly_report(arrays: dict[str, Any], events: dict[str, Any]) -> dict[str, Any]:
    scored = scored_mask(arrays["t"])
    reason_sets = events["reason_sets"]
    label_reasons: dict[str, int] = {}
    for side in ("long", "short"):
        mask = scored & (arrays[f"shadow_{side}_status"] != 1)
        for index in arrays[f"shadow_{side}_reasons"][mask]:
            for code in reason_sets[int(index)].split("|") or ["NONE"]:
                key = f"{side.upper()}:{code or 'NO_LABEL'}"
                label_reasons[key] = label_reasons.get(key, 0) + 1
    fills = events["fills"]
    return {
        "invalid_minutes_ingested": events["invalid_minutes"],
        "shadow_label_unavailable_scored": dict(sorted(label_reasons.items())),
        "entry_rejections": sum(1 for f in fills if f["kind"] == "ENTRY_REJECTED"),
        "late_exit_data_missing": sum(
            1 for t in events["trades"] if t["exit_kind"] == "EXPIRY_LATE_EXIT_DATA_MISSING"
        ),
        "funding_invalid_events": sum(1 for f in events["funding"] if f["status"] != "SETTLED"),
        "forecast_targets_unmatured_at_ceiling": int(
            (scored & arrays["forecast_available"] & (arrays["outcome_status"] != 1)).sum()
        ),
        "open_trade_at_observation_ceiling": events["open_trade_at_end"],
        "pending_intent_at_observation_ceiling": events["pending_intent_at_end"],
    }


# ---------------------------------------------------------------------- artifacts
def trades_csv(events: dict[str, Any]) -> str:
    columns = (
        "trade_id",
        "side",
        "intended_entry_time",
        "entry_time",
        "exit_time",
        "exit_kind",
        "raw_entry",
        "raw_exit",
        "stop_price",
        "quantity",
        "planned_risk",
        "gross_pnl",
        "friction_cost",
        "funding_pnl",
        "net_pnl",
        "realized_net_r",
        "entry_shortfall",
        "violation_flags",
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for trade in events["trades"]:
        writer.writerow(
            ["|".join(trade[c]) if c == "violation_flags" else trade[c] for c in columns]
        )
    return buffer.getvalue()


def write_artifacts(
    root: Path, built: dict[str, Any], log_lines: list[str] | None
) -> dict[str, str]:
    """Write every artifact; `log_lines=None` (rebuild from cache) keeps the execution log."""
    from . import reports

    results, autopsy_payload = built["results"], built["autopsy"]
    written: dict[str, str] = {}

    def put(path: str, text: str) -> None:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        written[path] = sha256_text(text)

    _, caches = _load(root)
    for system in TRADES_SYSTEMS:
        put(f"{EXPERIMENT_DIR}/TRADES-{system}.csv", trades_csv(caches[SYSTEM_RUN[system]][1]))
    put(RESULTS_PATH, dumps(results))
    put(AUTOPSY_PATH, dumps(autopsy_payload))
    put(RESULTS_REPORT, reports.results_markdown(results, autopsy_payload))
    put(CHECKPOINT_REPORT, reports.checkpoint_markdown(results, autopsy_payload))
    validation = reports.validation_payload(results, written)
    put(VALIDATION_PATH, dumps(validation))
    put(VALIDATION_REPORT, reports.validation_markdown(validation))
    if log_lines is None:
        written[VALIDATION_LOG] = text_sha256(root / VALIDATION_LOG)
    else:
        put(VALIDATION_LOG, "\n".join(log_lines) + "\n")
    batch_manifest = {
        "artifact": "G2-DEVELOPMENT-CYCLE-1-V1/BATCH_MANIFEST",
        "authorization_record": AUTHORIZATION_RECORD,
        "run_cache_schema": CACHE_SCHEMA,
        "runs": results["runs"],
        "determinism": results["determinism"],
        "artifacts_sha256": dict(sorted(written.items())),
        "code_sha256": authorization_record(root)["code_sha256"],
    }
    put(BATCH_MANIFEST_PATH, dumps(batch_manifest))
    return written


def executed_records(root: Path, results: dict[str, Any], written: dict[str, str]) -> None:
    """One executed-record ledger entry per simulated system, then the completion checkpoint."""
    now = utc_now()
    for variant in BATCH:
        run = results["runs"][variant.run_key]
        record = {
            "record_type": "DEVELOPMENT_SYSTEM_EXECUTED",
            "record_id": f"G2-02-EXECUTED-{variant.run_key}",
            "timestamp_utc": now,
            "generation": "G2_DEVELOPMENT_SYSTEM",
            "work_package": PACKAGE,
            "authorization_record": AUTHORIZATION_RECORD,
            "systems": list(variant.systems),
            "role": variant.role,
            "run_id": run["run_id"],
            "fingerprint": run["fingerprint"],
            "automatic_monthly_refits": sum(
                1
                for fit in json.loads(
                    (cache_dir(root, variant.run_key) / "events.json").read_text(encoding="utf-8")
                )["fits"]
                if fit["head"] == "FORECAST"
            ),
            "automatic_refits_consume_revision_slot": False,
            "revision_slot_consumed": False,
            "eligible_development_version": variant.role == "BASELINE",
            "promotable_in_g2_02": False,
            "results_artifact": RESULTS_PATH,
            "protected_outcomes_read": False,
            "sealed_queries": 0,
        }
        append_ledger(root, record)
    append_ledger(
        root,
        {
            "record_type": "DEVELOPMENT_SYSTEM_EXECUTED",
            "record_id": "G2-02-EXECUTED-CASH_REFERENCE",
            "timestamp_utc": now,
            "generation": "G2_DEVELOPMENT_SYSTEM",
            "work_package": PACKAGE,
            "authorization_record": AUTHORIZATION_RECORD,
            "systems": [CASH_SYSTEM],
            "role": "FIXED_REFERENCE",
            "definition": "zero exposure; no simulation required",
            "revision_slot_consumed": False,
            "results_artifact": RESULTS_PATH,
            "protected_outcomes_read": False,
            "sealed_queries": 0,
        },
    )
    append_ledger(
        root,
        {
            "record_type": "DEVELOPMENT_BATCH_CHECKPOINT",
            "record_id": "G2-02-CHECKPOINT-001",
            "timestamp_utc": utc_now(),
            "generation": "G2_DEVELOPMENT_SYSTEM",
            "work_package": PACKAGE,
            "status": STATUS,
            "authorization_record": AUTHORIZATION_RECORD,
            "results_artifact": RESULTS_PATH,
            "results_sha256": written[RESULTS_PATH],
            "autopsy_artifact": AUTOPSY_PATH,
            "validation_artifact": VALIDATION_PATH,
            "checkpoint": CHECKPOINT_REPORT,
            "determinism_fingerprint_identical": results["determinism"]["fingerprint_identical"],
            "general_revision_slots_consumed": 0,
            "cycle_revision_slots_consumed": 0,
            "adaptive_revision_executed": False,
            "protected_outcomes_read": False,
            "sealed_queries": 0,
            "note": "Fixed batch complete; interpretation and the next allocation are Research "
            "Director decisions.",
        },
    )
