"""SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1: the frozen multi-seed synthetic quality gate.

Executes exactly the protocol frozen by ADR-0045
(`research/protocols/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.md`) against the frozen cycle
method and the frozen 0.90 / three-bar quality rule implemented in `cycle.ScaleTracker`.

Per scale: 128 deterministic white-noise paths; 48 clean-cycle paths (16 each at the lower
quartile, midpoint and upper quartile of the frozen ACP band, deterministic random phase); 48
trend + cycle paths with the same period/phase design. Each path has the normal warm-up plus 512
evaluated bars. Non-gating diagnostics (two-frequency mixture, amplitude decay, abrupt period
change, missing observations) are reported, never used to select anything.

Only synthetic series are generated. No market data or market outcome is read. The disposition is
mechanical; no threshold, quality feature, band, ACP parameter or method is searched.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np

from .cycle import (
    CYCLE_DECISION_ACTIVATION,
    METHOD_VERSION,
    QUALITY_RULE_ID,
    SCALES,
    USABLE,
    USABLE_EXPLAINED_FRACTION,
    USABLE_PERSISTENCE_BARS,
    Scale,
    ScaleTracker,
)
from .cycle_diagnostics import AMPLITUDE, fixture_series
from .cycle_reference import reference_acp

ROOT = Path(__file__).resolve().parents[3]
GATE_VERSION = "SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1"
ARTIFACT_PATH = "reports/research/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.json"
PROTOCOL_PATH = "research/protocols/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.md"
DECISION_PATH = "decisions/ADR-0045-ACCEPT-G1-CHECKPOINT-1-AND-FREEZE-CYCLE-QUALITY-GATE.md"
CODE_PATHS = (
    "backend/app/g1/cycle.py",
    "backend/app/g1/cycle_reference.py",
    "backend/app/g1/cycle_diagnostics.py",
    "backend/app/g1/cycle_quality_gate.py",
)
EVALUATED_BARS = 512
NOISE_PATHS = 128
CYCLE_PATHS = 48
TREND_PER_BAR = 0.05
NOISE_SD = AMPLITUDE / math.sqrt(2)
SEED_BASE = 20260926
EPOCH = datetime(2001, 1, 1, tzinfo=UTC)
NOISE_MEDIAN_MAX = 0.05
NOISE_P95_MAX = 0.15
COHERENT_MEDIAN_MIN = 0.80
COHERENT_P10_MIN = 0.60
PERIOD_ERROR_MAX = 0.10
RECONCILIATION_TOLERANCE = 1e-9
PASS = "CYCLE_SYNTHETIC_QUALITY_GATE_PASS_PENDING_RESEARCH_DIRECTOR_ACTIVATION"
FAIL = "CYCLE_SYNTHETIC_QUALITY_GATE_FAIL_METHOD_NOT_READY"
NON_GATING = (
    "two_frequency_mixture",
    "amplitude_decay",
    "abrupt_period_change",
    "missing_observations",
)


def canonical_text_sha256(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def band_periods(scale: Scale) -> tuple[float, float, float]:
    """Lower quartile, midpoint and upper quartile of the frozen ACP period band."""
    width = scale.period2 - scale.period1
    return (
        scale.period1 + 0.25 * width,
        scale.period1 + 0.5 * width,
        scale.period1 + 0.75 * width,
    )


def noise_seed(scale_index: int, path: int) -> int:
    return SEED_BASE + 1000 * scale_index + path


def phase_seed(scale_index: int, path: int) -> int:
    return SEED_BASE + 100000 + 1000 * scale_index + path


def cycle_design(scale_index: int, scale: Scale, path: int) -> tuple[float, float]:
    """(period, phase) of clean/trend path `path`: bands rotate, phase is seeded uniform."""
    period = band_periods(scale)[path % 3]
    phase = float(np.random.default_rng(phase_seed(scale_index, path)).uniform(0, 2 * math.pi))
    return period, phase


def series_length(scale: Scale) -> int:
    return scale.warmup_bars + EVALUATED_BARS


def noise_series(scale_index: int, scale: Scale, path: int) -> np.ndarray:
    rng = np.random.default_rng(noise_seed(scale_index, path))
    return 100 + rng.normal(0.0, NOISE_SD, series_length(scale))


def cycle_series(scale_index: int, scale: Scale, path: int, trend: bool) -> np.ndarray:
    period, phase = cycle_design(scale_index, scale, path)
    t = np.arange(series_length(scale), dtype=float)
    values = 100 + AMPLITUDE * np.sin(2 * np.pi * t / period + phase)
    return values + TREND_PER_BAR * t if trend else values


def run_path(
    scale: Scale, values: Iterable[float], present: np.ndarray | None = None
) -> list[dict[str, Any]]:
    """Feed one synthetic series through a fresh tracker; one row per present input bar."""
    tracker = ScaleTracker(scale)
    step = timedelta(minutes=scale.bar_minutes)
    rows = []
    for index, value in enumerate(values):
        if present is not None and not present[index]:
            continue
        opened = EPOCH + index * step
        tracker.update(opened, opened + step, float(value), True)
        turn = tracker.last_turn
        rows.append(
            {
                "index": index,
                "label": tracker.quality_label(),
                "dominant": tracker.dominant if tracker.ready else None,
                "turn": None
                if turn is None
                else (turn.kind, turn.estimated_turn_time, turn.confirmation_time),
                "gap_state": tracker.gap_state,
                "history_length": len(tracker.explained_history),
                "bars_seen": tracker.bars_seen,
            }
        )
    return rows


def path_metrics(scale: Scale, rows: list[dict[str, Any]], period: float | None) -> dict[str, Any]:
    evaluated = [row for row in rows if row["index"] >= scale.warmup_bars]
    labels = [row["label"] for row in evaluated]
    usable = sum(label == USABLE for label in labels)
    longest = streak = 0
    for label in labels:
        streak = streak + 1 if label == USABLE else 0
        longest = max(longest, streak)
    turns = {row["turn"] for row in rows if row["turn"] is not None}
    step = timedelta(minutes=scale.bar_minutes)
    delays = [(confirmed - estimated) / step for _, estimated, confirmed in turns]
    result: dict[str, Any] = {
        "usable_occupancy": usable / EVALUATED_BARS,
        "longest_usable_streak": longest,
        "confirmed_turns": len(turns),
        "turn_violations": sum(1 for _, estimated, confirmed in turns if confirmed <= estimated),
        "median_turn_confirmation_delay_bars": float(median(delays)) if delays else None,
    }
    dominant = [row["dominant"] for row in evaluated if row["dominant"] is not None]
    result["dominant_period_median"] = float(median(dominant)) if dominant else None
    if period is not None:
        errors = [abs(value - period) / period for value in dominant]
        result["median_relative_period_error"] = float(median(errors)) if errors else None
    return result


def quantile(values: list[float], level: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), level))


def _ensemble(paths: list[dict[str, Any]], coherent: bool) -> dict[str, Any]:
    occupancy = [path["usable_occupancy"] for path in paths]
    summary: dict[str, Any] = {
        "paths": len(paths),
        "occupancy_median": float(median(occupancy)),
        "occupancy_p10": quantile(occupancy, 0.10),
        "occupancy_p95": quantile(occupancy, 0.95),
        "occupancy_max": max(occupancy),
        "longest_streak_median": float(median(p["longest_usable_streak"] for p in paths)),
        "turn_violations": sum(p["turn_violations"] for p in paths),
    }
    if coherent:
        errors = [
            p["median_relative_period_error"]
            for p in paths
            if p["median_relative_period_error"] is not None
        ]
        summary["period_error_median_of_path_medians"] = float(median(errors))
        summary["period_error_p90_of_path_medians"] = quantile(errors, 0.90)
        summary["paths_without_period_estimate"] = len(paths) - len(errors)
    return summary


def run_scale(scale_index: int) -> dict[str, Any]:
    scale = SCALES[scale_index]
    noise = [
        {
            "seed": noise_seed(scale_index, i),
            **path_metrics(scale, run_path(scale, noise_series(scale_index, scale, i)), None),
        }
        for i in range(NOISE_PATHS)
    ]
    families: dict[str, list[dict[str, Any]]] = {"clean_cycle": [], "trend_plus_cycle": []}
    for family, trend in (("clean_cycle", False), ("trend_plus_cycle", True)):
        for i in range(CYCLE_PATHS):
            period, phase = cycle_design(scale_index, scale, i)
            rows = run_path(scale, cycle_series(scale_index, scale, i, trend))
            families[family].append(
                {
                    "phase_seed": phase_seed(scale_index, i),
                    "period": period,
                    "phase": phase,
                    **path_metrics(scale, rows, period),
                }
            )
    noise_summary = _ensemble(noise, coherent=False)
    clean = _ensemble(families["clean_cycle"], coherent=True)
    trend_summary = _ensemble(families["trend_plus_cycle"], coherent=True)
    gates = {
        "noise_median_occupancy_le_0.05": noise_summary["occupancy_median"] <= NOISE_MEDIAN_MAX,
        "noise_p95_occupancy_le_0.15": noise_summary["occupancy_p95"] <= NOISE_P95_MAX,
    }
    for name, summary in (("clean_cycle", clean), ("trend_plus_cycle", trend_summary)):
        gates[f"{name}_median_occupancy_ge_0.80"] = (
            summary["occupancy_median"] >= COHERENT_MEDIAN_MIN
        )
        gates[f"{name}_p10_occupancy_ge_0.60"] = summary["occupancy_p10"] >= COHERENT_P10_MIN
        gates[f"{name}_median_period_error_le_0.10"] = (
            summary["period_error_median_of_path_medians"] <= PERIOD_ERROR_MAX
        )
    return {
        "nominal_scale": scale.nominal,
        "input_resolution": scale.resolution,
        "acp_period_search": [scale.period1, scale.period2],
        "warmup_bars": scale.warmup_bars,
        "evaluated_bars_per_path": EVALUATED_BARS,
        "cycle_design_periods": list(band_periods(scale)),
        "noise_seeds": [noise_seed(scale_index, 0), noise_seed(scale_index, NOISE_PATHS - 1)],
        "phase_seeds": [phase_seed(scale_index, 0), phase_seed(scale_index, CYCLE_PATHS - 1)],
        "white_noise": noise_summary,
        "clean_cycle": clean,
        "trend_plus_cycle": trend_summary,
        "gates": gates,
        "gates_pass": all(gates.values()),
        "integrity": scale_integrity(scale_index, scale),
        "non_gating_diagnostics": non_gating(scale),
        "paths": {"white_noise": noise, **families},
    }


def scale_integrity(scale_index: int, scale: Scale) -> dict[str, Any]:
    """Gap/reset semantics and independent ACP reconciliation for one scale."""
    # Gap: a clean mid-band path with three missing bars after warm-up.
    values = cycle_series(scale_index, scale, 1, trend=False)
    present = np.ones(len(values), dtype=bool)
    gap = scale.warmup_bars + 100
    present[gap : gap + 3] = False
    rows = run_path(scale, values, present)
    after = [row for row in rows if row["index"] > gap]
    first = after[0]
    rewarm = [row for row in after if row["bars_seen"] < scale.warmup_bars]
    ready_again = next(row for row in after if row["bars_seen"] >= scale.warmup_bars)
    gap_pass = (
        first["bars_seen"] == 1
        and first["history_length"] == 1
        and first["gap_state"] == "REWARMING_AFTER_GAP"
        and all(row["label"] == "UNAVAILABLE" for row in rewarm)
        and len(rewarm) == scale.warmup_bars - 1
        and ready_again["gap_state"] == "NO_GAP"
    )
    # Independent reference reconciliation on one noise and one clean path.
    differences = []
    availability = True
    for series in (noise_series(scale_index, scale, 0), cycle_series(scale_index, scale, 0, False)):
        rows = run_path(scale, series)
        stream = np.array([np.nan if r["dominant"] is None else r["dominant"] for r in rows])
        _, reference = reference_acp(series, scale.period1, scale.period2)
        tail = slice(scale.warmup_bars, None)
        mask = ~np.isnan(reference[tail])
        availability = availability and bool(
            np.array_equal(np.isnan(stream[tail]), np.isnan(reference[tail]))
        )
        differences.append(float(np.max(np.abs(stream[tail][mask] - reference[tail][mask]))))
    return {
        "gap_reset_and_rewarm": gap_pass,
        "first_ready_bar_after_gap_offset": ready_again["index"] - gap,
        "reference_max_abs_period_diff": max(differences),
        "reference_availability_matches": availability,
        "reference_reconciliation": availability and max(differences) < RECONCILIATION_TOLERANCE,
    }


def non_gating(scale: Scale) -> dict[str, Any]:
    diagnostics = {}
    for fixture in NON_GATING:
        values, present, truth = fixture_series(scale, fixture)
        rows = run_path(scale, values, present)
        periods = truth.get("periods", [])
        metrics = path_metrics(scale, rows, periods[0] if len(periods) == 1 else None)
        if fixture == "abrupt_period_change":
            change = truth["change_index"]
            post = [r for r in rows if r["index"] >= change]
            metrics["post_change_usable_occupancy"] = sum(r["label"] == USABLE for r in post) / len(
                post
            )
            dominant = [r["dominant"] for r in post if r["dominant"] is not None]
            metrics["post_change_dominant_median"] = float(median(dominant)) if dominant else None
        diagnostics[fixture] = {"truth": truth, **metrics}
    return diagnostics


def replay_speed_label_identity() -> dict[str, Any]:
    """Labels exposed by the causal core replay are identical at every replay speed."""
    from . import fixtures
    from .clock import SPEEDS, ReplayController
    from .core import G1Core, run_manifest
    from .ledger import RiskPolicy
    from .records import CycleState

    bars = fixtures.minute_path()
    policy = RiskPolicy()
    manifest = run_manifest(bars, fixtures.START, fixtures.END, policy)
    sequences = []
    for speed in SPEEDS:
        core = G1Core(manifest, fixtures.scenario_step, fixtures.FUNDING_RATES, policy)
        controller = ReplayController(core, bars)
        controller.set_speed(speed)
        controller.run_to_end(pace=lambda: 0.25)
        sequences.append(
            [
                tuple(scale.quality_label for scale in state.scales)
                for state in core.store.of_type(CycleState)
            ]
        )
    labels = {label for sequence in sequences for row in sequence for label in row}
    return {
        "speeds": list(SPEEDS),
        "identical": all(sequence == sequences[0] for sequence in sequences),
        "labels_observed": sorted(labels),
        "decision_states": len(sequences[0]),
    }


def build_gate(workers: int = 1) -> dict[str, Any]:
    indices = range(len(SCALES))
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            scales = list(pool.map(run_scale, indices))
    else:
        scales = [run_scale(index) for index in indices]
    speed = replay_speed_label_identity()
    turn_violations = sum(
        s[f]["turn_violations"]
        for s in scales
        for f in ("white_noise", "clean_cycle", "trend_plus_cycle")
    )
    integrity = {
        "zero_turn_confirmation_violations": turn_violations == 0,
        "gap_reset_semantics": all(s["integrity"]["gap_reset_and_rewarm"] for s in scales),
        "replay_speed_label_invariance": speed["identical"],
        "independent_acp_reconciliation": all(
            s["integrity"]["reference_reconciliation"] for s in scales
        ),
    }
    passed = all(s["gates_pass"] for s in scales) and all(integrity.values())
    return {
        "artifact": GATE_VERSION,
        "evidence_class": "SYNTHETIC_METHOD_VALIDATION_ONLY",
        "market_data_read": False,
        "btc_returns_or_outcomes_used": False,
        "frozen_rule": {
            "rule_id": QUALITY_RULE_ID,
            "explained_fraction_threshold": USABLE_EXPLAINED_FRACTION,
            "persistence_bars": USABLE_PERSISTENCE_BARS,
            "protocol": PROTOCOL_PATH,
            "protocol_canonical_sha256": canonical_text_sha256(PROTOCOL_PATH),
            "decision": DECISION_PATH,
            "decision_canonical_sha256": canonical_text_sha256(DECISION_PATH),
            "altered_after_result": False,
        },
        "method_version": METHOD_VERSION,
        "code_canonical_sha256": {path: canonical_text_sha256(path) for path in CODE_PATHS},
        "design": {
            "white_noise_paths_per_scale": NOISE_PATHS,
            "cycle_paths_per_scale": CYCLE_PATHS,
            "evaluated_bars_per_path": EVALUATED_BARS,
            "amplitude": AMPLITUDE,
            "noise_sd": NOISE_SD,
            "trend_per_bar": TREND_PER_BAR,
            "seed_base": SEED_BASE,
            "noise_seed_rule": "SEED_BASE + 1000*scale_index + path",
            "phase_seed_rule": "SEED_BASE + 100000 + 1000*scale_index + path; phase ~ U[0, 2pi)",
            "period_rule": "path % 3 -> band lower quartile / midpoint / upper quartile",
            "occupancy": "USABLE bars / 512 evaluated post-warm-up bars",
            "period_error": "median over paths of the path-median |dominant - period| / period",
        },
        "mandatory_gate_thresholds": {
            "noise_median_occupancy_max": NOISE_MEDIAN_MAX,
            "noise_p95_occupancy_max": NOISE_P95_MAX,
            "coherent_median_occupancy_min": COHERENT_MEDIAN_MIN,
            "coherent_p10_occupancy_min": COHERENT_P10_MIN,
            "coherent_median_period_error_max": PERIOD_ERROR_MAX,
        },
        "scale_gate_results": {s["nominal_scale"]: s["gates"] for s in scales},
        "integrity": integrity,
        "replay_speed_label_identity": speed,
        "disposition": PASS if passed else FAIL,
        "cycle_active_in_decisions": CYCLE_DECISION_ACTIVATION,
        "threshold_or_method_search_performed": False,
        "scales": scales,
    }
