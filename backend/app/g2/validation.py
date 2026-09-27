"""G2-01 deterministic engineering validation artifact (Gate B evidence, NOT performance evidence).

The artifact records, for the frozen G2-V0 implementation:
- the synthetic end-to-end run identity/fingerprint, record counts and reason-code coverage;
- determinism: repeated-run hash, replay-speed identity and prefix invariance of every record;
- the thirteen cycle-checkpoint method tests (full-size gates);
- the declared <=2024 exposed engineering window (data mode only): parser, aggregation,
  timestamp-semantics, prefix and replay parity, with no economic output of any kind;
- explicit negative claims (no economic run, no protected data, no tuning).

It contains no cumulative return, Sharpe, profit factor, ranking or threshold choice.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any

from app.g1.cycle import SCALES

from . import cycle_checkpoint, fixtures, runs
from .bars import completed_bars
from .contract import IMPLEMENTATION_VERSION, SYSTEM_VERSION, frozen_identity
from .records import (
    ClosedTrade,
    Decision,
    FitManifest,
    FundingEvent,
    MarketState,
    Prediction,
    Reason,
    ShadowLabel,
    SimulatedFill,
)

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_PATH = "reports/validation/G2-01-ENGINEERING-VALIDATION-V1.json"
ARTIFACT_ID = "G2-01-ENGINEERING-VALIDATION-V1"
DIGITS = 9
CODE_FILES = tuple(
    f"backend/app/g2/{name}.py"
    for name in (
        "__init__",
        "api",
        "bars",
        "contract",
        "core",
        "cycle",
        "cycle_checkpoint",
        "distribution",
        "execution",
        "features",
        "fixtures",
        "models",
        "records",
        "risk",
        "runs",
        "service",
        "sources",
        "store",
        "validation",
    )
)
CONTRACT_FILES = (
    "docs/canonical/G2_FORECAST_POLICY_EXECUTION_CONTRACTS_V1.md",
    "docs/canonical/G2_PROFESSIONAL_KNOWLEDGE_MODEL_V1.md",
    "research/g2/G2_DATA_EXPOSURE_AND_EXECUTION_MANIFEST_V1.md",
    "research/g2/G2_CYCLE_CAUSALITY_CHECKPOINT_V1.md",
    "tasks/G2_01_IMPLEMENTATION_PACKAGE_V1.md",
)
PREFIX_CUTS = (timedelta(days=213, hours=5, minutes=7), timedelta(days=245, hours=13))
STEPS = (timedelta(minutes=97), timedelta(days=1))


def text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def rounded(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, DIGITS) if math.isfinite(value) else str(value)
    if isinstance(value, dict):
        return {str(key): rounded(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [rounded(item) for item in value]
    return value


def artifact_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(rounded(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("ascii")


# ------------------------------------------------------------------ worker tasks (top level)


def _synthetic_batch(_: int = 0) -> dict[str, Any]:
    built = runs.build(runs.synthetic_spec())
    core = runs.run_batch(built)
    return {
        "run_id": built.manifest.run_id,
        "fingerprint": core.store.fingerprint(),
        "summary": synthetic_summary(built, core),
    }


def _synthetic_steps(minutes: int) -> str:
    built = runs.build(runs.synthetic_spec())
    return runs.run_in_steps(built, timedelta(minutes=minutes)).store.fingerprint()


def _prefix(cut_minutes: int) -> list[str]:
    from .store import canonical_bytes

    built = runs.build(runs.synthetic_spec())
    cursor = built.manifest.dataset_start + timedelta(minutes=cut_minutes)
    core = runs.run_batch(built, cursor)
    return [
        hashlib.sha256(canonical_bytes(r)).hexdigest()
        for r in core.store
        if r.available_at <= cursor
    ]


def _cycle(task: tuple[str, int]) -> Any:
    name, index = task
    if name == "noise":
        return cycle_checkpoint.noise_scale(index)
    if name == "coherent":
        return cycle_checkpoint.coherent_scale(index)
    if name == "additive":
        return cycle_checkpoint.additive_scale(index)
    return getattr(cycle_checkpoint, name)()


# ------------------------------------------------------------------ summaries


def synthetic_summary(built: runs.BuiltRun, core: Any) -> dict[str, Any]:
    store = core.store
    predictions = store.of_type(Prediction)
    decisions = store.of_type(Decision)
    start, end = built.manifest.dataset_start, built.manifest.dataset_end
    expected = int((end - start) // timedelta(minutes=15))
    zero_volume_decision = fixtures.ZERO_VOLUME_CANDLE + timedelta(minutes=15)
    zero = next(p for p in predictions if p.decision_time == zero_volume_decision)
    missing_after = [
        s
        for s in store.of_type(MarketState)
        if fixtures.MISSING_MINUTE < s.decision_time <= fixtures.MISSING_MINUTE + timedelta(hours=8)
    ]
    trades = store.of_type(ClosedTrade)
    labels = store.of_type(ShadowLabel)
    return {
        "run_key": built.spec.key,
        "evidence_class": built.manifest.evidence_class,
        "dataset": [
            built.manifest.dataset_start.isoformat(),
            built.manifest.dataset_end.isoformat(),
        ],
        "record_counts": store.counts(),
        "eligible_decision_candles": expected,
        "predictions_emitted": len(predictions),
        "decisions_emitted": len(decisions),
        "prediction_reason_counts": dict(
            sorted(Counter(r for p in predictions for r in p.reason_codes).items())
        ),
        "decision_reason_counts": dict(
            sorted(Counter(r for d in decisions for r in d.reason_codes).items())
        ),
        "action_counts": dict(sorted(Counter(str(d.action) for d in decisions).items())),
        "fits": [
            [f.head, f.fit_boundary.isoformat(), f.status, f.rows]
            for f in store.of_type(FitManifest)
        ],
        "calibration_status_counts": dict(
            sorted(Counter(p.calibration_status for p in predictions).items())
        ),
        "shadow_label_status_counts": dict(
            sorted(Counter(f"{label.side}:{label.status}" for label in labels).items())
        ),
        "closed_trade_exit_kinds": dict(sorted(Counter(t.exit_kind for t in trades).items())),
        "funding_events": len(store.of_type(FundingEvent)),
        "entry_rejections": dict(
            sorted(
                Counter(
                    r
                    for f in store.of_type(SimulatedFill)
                    if f.kind == "ENTRY_REJECTED"
                    for r in f.reason_codes
                ).items()
            )
        ),
        "trade_violation_flags": dict(
            sorted(Counter(v for t in trades for v in t.violation_flags).items())
        ),
        "scripted_injections": {
            "zero_volume_candle_decision_reasons": list(zero.reason_codes),
            "missing_minute_states": dict(sorted(Counter(s.status for s in missing_after).items())),
        },
        "max_source_not_after_decision": all(
            s.max_source_time is None or s.max_source_time <= s.decision_time
            for s in store.of_type(MarketState)
        ),
        "economic_summary": "NOT_COMPUTED_G2_01_ENGINEERING_ONLY",
    }


def engineering_window(root: Path) -> dict[str, Any]:
    """Parser/aggregation/timestamp/prefix/replay parity on the declared exposed window."""
    from app.g1.sources import parse_kline_csv
    from app.predictive import taker_flow_source as klines

    from .service import _engineering_data_present
    from .store import canonical_bytes

    if not _engineering_data_present(root):
        return {"status": "DATA_ABSENT_NOT_EXECUTED"}
    spec = runs.engineering_window_spec(root)
    built = runs.build(spec)
    minutes = built.minutes
    start, end = runs.ENGINEERING_WINDOW
    # Independent parser reference: the frozen G1 parser over the same verified object.
    archive = next(
        a
        for a in json.loads((root / klines.MANIFEST_PATH).read_text(encoding="utf-8"))["archives"]
        if a["market"] == klines.USDM and a["month"] == start.strftime("%Y-%m")
    )
    _, member = klines.archive_member(
        (root / archive["raw_path"]).read_bytes(), start.year, start.month
    )
    reference = [b for b in parse_kline_csv(member.decode("utf-8")) if start <= b.open_time < end]

    def optional(value: Any) -> float | None:
        return None if value is None else float(value)

    parser_parity = len(reference) == len(minutes) and all(
        (
            r.open_time,
            float(r.open),
            float(r.high),
            float(r.low),
            float(r.close),
            float(r.volume),
            optional(r.quote_volume),
            optional(r.taker_buy_base_volume),
        )
        == (
            m.open_time,
            m.open,
            m.high,
            m.low,
            m.close,
            m.volume,
            m.quote_volume,
            m.taker_buy_base_volume,
        )
        for r, m in zip(reference, minutes, strict=False)
    )
    aggregation = {}
    for tf, step in (("15m", 15), ("1h", 60), ("4h", 240), ("1d", 1440)):
        bars = completed_bars(minutes, tf)
        ok = True
        by_open: dict[Any, list[Any]] = {}
        for m in minutes:
            key = start + ((m.open_time - start) // timedelta(minutes=step)) * timedelta(
                minutes=step
            )
            by_open.setdefault(key, []).append(m)
        for b in bars:
            group = by_open[b.open_time]
            ok &= (
                b.open == group[0].open
                and b.close == group[-1].close
                and b.high == max(g.high for g in group)
                and b.low == min(g.low for g in group)
                and math.isclose(b.volume, sum(g.volume for g in group), rel_tol=1e-12)
                and b.source_minutes == len(group)
                and b.close_time == b.open_time + timedelta(minutes=step)
            )
        aggregation[tf] = {
            "bars": len(bars),
            "complete": sum(b.complete for b in bars),
            "parity": ok,
        }
    on_grid = all(m.open_time.second == 0 and m.open_time.microsecond == 0 for m in minutes)
    increasing = all(a.open_time < b.open_time for a, b in zip(minutes, minutes[1:], strict=False))
    funding_minutes = sorted({f.replace(second=0, microsecond=0) for f, _ in built.funding})
    core = runs.run_batch(built)
    fingerprint = core.store.fingerprint()
    cut = start + timedelta(days=4, hours=7, minutes=3)
    prefix = runs.run_batch(built, cut)
    prefix_ok = [canonical_bytes(r) for r in prefix.store if r.available_at <= cut] == [
        canonical_bytes(r) for r in core.store if r.available_at <= cut
    ]
    steps_ok = runs.run_in_steps(built, timedelta(minutes=53)).store.fingerprint() == fingerprint
    audits = [a for a in core.store if type(a).__name__ == "SourceAuditEvent"]
    opened = sorted({o for a in audits for o in a.opened_objects})
    predictions = core.store.of_type(Prediction)
    return {
        "status": "EXECUTED",
        "ledger_record": runs.ENGINEERING_WINDOW_LEDGER,
        "window": [start.isoformat(), end.isoformat()],
        "purposes": [
            "PARSER_CORRECTNESS",
            "AGGREGATION_PARITY",
            "SOURCE_TIMESTAMP_SEMANTICS",
            "PREFIX_INVARIANCE",
            "DETERMINISTIC_REPLAY",
            "API_FRONTEND_RENDERING",
        ],
        "run_id": built.manifest.run_id,
        "fingerprint": fingerprint,
        "minutes_returned": len(minutes),
        "parser_parity_with_frozen_g1_parser": parser_parity,
        "aggregation_parity": aggregation,
        "timestamps_on_minute_grid": on_grid,
        "timestamps_strictly_increasing": increasing,
        "minute_available_at_is_close": all(
            m.available_at == m.open_time + timedelta(minutes=1) for m in minutes
        ),
        "funding_settlements_on_8h_grid": all(
            f.hour % 8 == 0 and f.minute == 0 for f in funding_minutes
        ),
        "funding_settlements": len(funding_minutes),
        "opened_objects": opened,
        "protected_objects_opened": any("2025" in o for o in opened),
        "prefix_invariance": prefix_ok,
        "replay_speed_identity": steps_ok,
        "predictions_emitted": len(predictions),
        "forecast_status_counts": dict(
            sorted(Counter(r for p in predictions for r in p.reason_codes).items())
        ),
        "model_fits": len(core.store.of_type(FitManifest)),
        "economic_actions": sum(str(d.action) != "NO_TRADE" for d in core.store.of_type(Decision)),
        "economic_outputs": "NONE_BY_DECLARATION",
    }


def build(root: Path = ROOT, workers: int = 8, data: bool = True) -> dict[str, Any]:
    cycle_tasks: list[tuple[str, int]] = [
        (name, i) for name in ("noise", "coherent", "additive") for i in range(len(SCALES))
    ]
    cycle_tasks += [
        (name, -1)
        for name in (
            "t01_parity",
            "t05_linear_trend",
            "t06_isolated_jump",
            "t07_varying_frequency",
            "t08_prefix_invariance",
            "t09_gap_reset",
            "t10_projection_amplitude",
            "t11_period_stability",
            "t12_turn_confirmation",
            "t13_replay_speed_identity",
        )
    ]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        batch = [pool.submit(_synthetic_batch, k) for k in range(2)]
        steps = [pool.submit(_synthetic_steps, int(s.total_seconds() // 60)) for s in STEPS]
        prefixes = [pool.submit(_prefix, int(c.total_seconds() // 60)) for c in PREFIX_CUTS]
        cycles = {task: pool.submit(_cycle, task) for task in cycle_tasks}
        first, second = batch[0].result(), batch[1].result()
        step_prints = [f.result() for f in steps]
        prefix_hashes = [f.result() for f in prefixes]
        cycle_results = {task: future.result() for task, future in cycles.items()}
    from .store import canonical_bytes

    full = runs.run_batch(runs.build(runs.synthetic_spec()))  # prefix reference
    prefix_ok = {}
    for cut, hashes in zip(PREFIX_CUTS, prefix_hashes, strict=True):
        cursor = full.manifest.dataset_start + cut
        reference = [
            hashlib.sha256(canonical_bytes(r)).hexdigest()
            for r in full.store
            if r.available_at <= cursor
        ]
        prefix_ok[cursor.isoformat()] = hashes == reference
    nominal = [s.nominal for s in SCALES]
    checkpoint = {
        "01_g1_g2_numeric_parity": cycle_results[("t01_parity", -1)],
        "02_white_noise_gate": cycle_checkpoint.t02_white_noise(
            scales={nominal[i]: cycle_results[("noise", i)] for i in range(len(SCALES))}
        ),
        "03_coherent_cycle_gate": cycle_checkpoint.t03_coherent_cycle(
            scales={nominal[i]: cycle_results[("coherent", i)] for i in range(len(SCALES))}
        ),
        "04_additive_noise_amp1_sd0_5": cycle_checkpoint.t04_additive_noise(
            scales={nominal[i]: cycle_results[("additive", i)] for i in range(len(SCALES))}
        ),
        "05_pure_linear_trend_no_usable": cycle_results[("t05_linear_trend", -1)],
        "06_isolated_jump_abstention": cycle_results[("t06_isolated_jump", -1)],
        "07_varying_frequency_bounded_causal": cycle_results[("t07_varying_frequency", -1)],
        "08_prefix_invariance": cycle_results[("t08_prefix_invariance", -1)],
        "09_gap_reset_full_rewarm": cycle_results[("t09_gap_reset", -1)],
        "10_projection_amplitude_valid": cycle_results[("t10_projection_amplitude", -1)],
        "11_period_stability_exact": cycle_results[("t11_period_stability", -1)],
        "12_turn_confirmation_delayed": cycle_results[("t12_turn_confirmation", -1)],
        "13_replay_speed_identity": cycle_results[("t13_replay_speed_identity", -1)],
    }
    all_cycle = all(t["pass"] for t in checkpoint.values())
    determinism = {
        "repeat_run_fingerprint_identical": first["fingerprint"] == second["fingerprint"],
        "replay_speed_identity": {
            f"{int(s.total_seconds() // 60)}m_steps": p == first["fingerprint"]
            for s, p in zip(STEPS, step_prints, strict=True)
        },
        "prefix_invariance_every_record": prefix_ok,
    }
    window = engineering_window(root) if data else {"status": "NOT_EXECUTED_NO_DATA_MODE"}
    return {
        "artifact": ARTIFACT_ID,
        "work_package": IMPLEMENTATION_VERSION,
        "system_version": SYSTEM_VERSION,
        "evidence_class": "ENGINEERING_VALIDATION_NOT_PERFORMANCE_EVIDENCE",
        "frozen_contract_identity": frozen_identity(),
        "contract_documents_canonical_sha256": {p: text_sha256(root / p) for p in CONTRACT_FILES},
        "code_canonical_sha256": {p: text_sha256(root / p) for p in CODE_FILES},
        "synthetic_run": {
            "run_id": first["run_id"],
            "fingerprint": first["fingerprint"],
            **first["summary"],
        },
        "determinism": determinism,
        "cycle_checkpoint": {
            "tests": checkpoint,
            "all_pass": all_cycle,
            "method": "EXISTING_CAUSAL_ACP (unchanged G1 tracker) + G2 amplitude/stability fields",
            "market_data_read": False,
            "parameters_tuned": False,
            "method_tournament": False,
            "runtime_role": "SHADOW_ONLY",
            "classification": "PENDING_RESEARCH_DIRECTOR_REVIEW",
        },
        "engineering_window": window,
        "claims": {
            "economic_market_run_executed": False,
            "economic_summary_computed": False,
            "protected_2025_outcomes_read": False,
            "protected_2025_objects_opened": False,
            "parameters_features_thresholds_tuned": False,
            "g1_rescue": False,
            "cycle_active_in_forecast_or_policy": False,
            "paper_or_real_orders": False,
            "validated_strategy": None,
            "champion": None,
            "sealed_queries": 0,
        },
        "reason_codes_canonical": sorted(str(r) for r in Reason),
        "status": "EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_GATE_B_REVIEW",
    }
