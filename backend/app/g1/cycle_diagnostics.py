"""Deterministic synthetic method-validation diagnostics for SYSTEM-G1-CYCLE-METHOD-V1.

Runs the frozen six-scale implementation on the seven contract fixtures (clean in-band sinusoid,
two-frequency mixture, trend + cycle, white noise, abrupt period change, amplitude decay, missing
observations) and reports continuous diagnostics only.

Scientific boundary: this module selects NO quality threshold and assigns no WEAK/USABLE label.
The artifact is returned to the Research Director, who alone may freeze the thresholds. No BTC or
other market series is read.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

import numpy as np

from .cycle import (
    CYCLE_DECISION_ACTIVATION,
    METHOD_STATUS,
    METHOD_VERSION,
    SCALES,
    Scale,
    ScaleTracker,
)
from .cycle_reference import reference_acp

ARTIFACT_PATH = "reports/research/SYSTEM-G1-CYCLE-SYNTHETIC-DIAGNOSTICS-V1.json"
ARTIFACT_VERSION = "SYSTEM-G1-CYCLE-SYNTHETIC-DIAGNOSTICS-V1"
EVALUATION_BARS = 384
AMPLITUDE = 10.0
EPOCH = datetime(2001, 1, 1, tzinfo=UTC)
SEED = 20260925
FIXTURES = (
    "clean_in_band_sinusoid",
    "two_frequency_mixture",
    "trend_plus_cycle",
    "white_noise",
    "abrupt_period_change",
    "amplitude_decay",
    "missing_observations",
)


def _periods(scale: Scale) -> dict[str, float]:
    nominal = float(scale.nominal_samples)
    second = float(min(round(nominal * 1.4), scale.period2 - 1))
    changed = float(max(round(nominal * 0.75), scale.period1 + 1))
    return {"nominal": nominal, "second": second, "changed": changed}


def fixture_series(scale: Scale, fixture: str) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """(values, present-mask, truth) for one scale's input-bar series."""
    total = scale.warmup_bars + EVALUATION_BARS
    t = np.arange(total, dtype=float)
    p = _periods(scale)
    present = np.ones(total, dtype=bool)
    truth: dict[str, Any] = {"periods": [p["nominal"]]}
    sine = AMPLITUDE * np.sin(2 * np.pi * t / p["nominal"])
    if fixture == "clean_in_band_sinusoid":
        values = 100 + sine
    elif fixture == "two_frequency_mixture":
        values = 100 + sine + 0.6 * AMPLITUDE * np.sin(2 * np.pi * t / p["second"])
        truth = {"periods": [p["nominal"], p["second"]], "amplitude_ratio": 0.6}
    elif fixture == "trend_plus_cycle":
        values = 100 + 0.05 * t + sine
        truth["trend_per_bar"] = 0.05
    elif fixture == "white_noise":
        rng = np.random.default_rng(SEED + scale.nominal_samples * 1000 + scale.period2)
        values = 100 + rng.normal(0.0, AMPLITUDE / math.sqrt(2), total)
        truth = {"periods": [], "noise_sd": AMPLITUDE / math.sqrt(2)}
    elif fixture == "abrupt_period_change":
        change = scale.warmup_bars + EVALUATION_BARS // 2
        phase_at_change = 2 * np.pi * change / p["nominal"]
        after = phase_at_change + 2 * np.pi * (t - change) / p["changed"]
        values = 100 + AMPLITUDE * np.where(
            t < change, np.sin(2 * np.pi * t / p["nominal"]), np.sin(after)
        )
        truth = {"periods": [p["nominal"], p["changed"]], "change_index": change}
    elif fixture == "amplitude_decay":
        tau = total / 3
        values = 100 + np.exp(-t / tau) * sine
        truth["decay_time_constant_bars"] = tau
    elif fixture == "missing_observations":
        values = 100 + sine
        gap_start = scale.warmup_bars + 64
        present[gap_start : gap_start + 3] = False
        truth["missing_indices"] = [gap_start, gap_start + 1, gap_start + 2]
    else:  # pragma: no cover - fixtures are a closed list
        raise ValueError(fixture)
    return values, present, truth


def _q(values: list[float], level: float) -> float | None:
    if not values:
        return None
    return float(np.quantile(np.asarray(values), level))


def _summary(values: list[float]) -> dict[str, float | None]:
    return {
        "p10": _q(values, 0.1),
        "median": None if not values else float(median(values)),
        "p90": _q(values, 0.9),
    }


def run_fixture(scale: Scale, fixture: str) -> dict[str, Any]:
    values, present, truth = fixture_series(scale, fixture)
    tracker = ScaleTracker(scale)
    step = timedelta(minutes=scale.bar_minutes)
    rows = []
    for index, value in enumerate(values):
        if not present[index]:
            continue
        open_time = EPOCH + index * step
        tracker.update(open_time, open_time + step, float(value), True)
        state = tracker.state()
        rows.append((index, state))
    evaluation = [(i, s) for i, s in rows if i >= scale.warmup_bars]
    available = [(i, s) for i, s in evaluation if s.dominant_period_bars is not None]
    dominant = [float(s.dominant_period_bars) for _, s in available]  # type: ignore[arg-type]
    metrics: dict[str, list[float]] = {}
    for _, s in available:
        for name, number in s.quality_metrics:
            if isinstance(number, float):
                metrics.setdefault(name, []).append(number)
    result: dict[str, Any] = {
        "fixture": fixture,
        "truth": truth,
        "series_bars": len(values),
        "warmup_bars": scale.warmup_bars,
        "evaluation_bars": len(evaluation),
        "available_fraction": len(available) / len(evaluation) if evaluation else 0.0,
        "dominant_period_bars": _summary(dominant),
        "quality_metrics": {name: _summary(series) for name, series in sorted(metrics.items())},
        "quality_label_assigned": sorted({s.quality_label for _, s in evaluation}),
    }
    periods = truth.get("periods", [])
    if fixture == "abrupt_period_change":
        change = truth["change_index"]
        before = [float(s.dominant_period_bars) for i, s in available if i < change]  # type: ignore[arg-type]
        after = [(i, float(s.dominant_period_bars)) for i, s in available if i >= change]  # type: ignore[arg-type]
        new = periods[1]
        settled = next(
            (
                i - change
                for i, d in after
                if all(abs(x - new) / new <= 0.1 for _, x in after if _ >= i)
            ),
            None,
        )
        result["pre_change_dominant_median"] = None if not before else float(median(before))
        result["post_change_dominant_median"] = (
            None if not after else float(median(d for _, d in after))
        )
        result["bars_until_within_10pct_of_new_period"] = settled
    elif len(periods) == 1 and dominant:
        true = periods[0]
        errors = [abs(d - true) / true for d in dominant]
        result["median_relative_period_error"] = float(median(errors))
        result["fraction_within_10pct"] = sum(e <= 0.1 for e in errors) / len(errors)
    elif len(periods) == 2 and dominant:
        result["fraction_between_component_periods"] = sum(
            min(periods) * 0.9 <= d <= max(periods) * 1.1 for d in dominant
        ) / len(dominant)
    if fixture == "missing_observations":
        gap = truth["missing_indices"][0]
        rewarm = [i for i, s in rows if i > gap and s.warmup_ready]
        result["first_ready_index_after_gap"] = rewarm[0] if rewarm else None
        result["rewarm_bars_after_gap"] = None if not rewarm else rewarm[0] - gap
        result["gap_states_seen"] = sorted({s.gap_state for _, s in rows})
    turns = [s.last_confirmed_turn for _, s in evaluation if s.last_confirmed_turn is not None]
    distinct = {(t.kind, t.estimated_turn_time, t.confirmation_time) for t in turns}
    delays = [(t.confirmation_time - t.estimated_turn_time) / step for t in {x for x in turns}]
    result["confirmed_turns"] = len(distinct)
    result["turn_confirmation_delay_bars"] = _summary([float(d) for d in delays])
    result["turn_confirmation_never_before_estimate"] = all(
        t.confirmation_time > t.estimated_turn_time for t in turns
    )
    if fixture == "clean_in_band_sinusoid":
        result["expected_turns_in_evaluation"] = round(2 * EVALUATION_BARS / periods[0])
    if bool(present.all()):
        _, ref = reference_acp(values, scale.period1, scale.period2)
        stream = np.array(
            [np.nan if s.dominant_period_bars is None else s.dominant_period_bars for _, s in rows]
        )
        mask = ~np.isnan(ref[scale.warmup_bars :])
        diff = np.abs(stream[scale.warmup_bars :][mask] - ref[scale.warmup_bars :][mask])
        result["reference_reconciliation_max_abs_period_diff"] = (
            float(diff.max()) if diff.size else 0.0
        )
        result["reference_availability_matches"] = bool(
            np.array_equal(
                np.isnan(stream[scale.warmup_bars :]), np.isnan(ref[scale.warmup_bars :])
            )
        )
    return result


def build_diagnostics() -> dict[str, Any]:
    scales: list[dict[str, Any]] = []
    for scale in SCALES:
        scales.append(
            {
                "nominal_scale": scale.nominal,
                "input_resolution": scale.resolution,
                "nominal_samples": scale.nominal_samples,
                "acp_period_search": [scale.period1, scale.period2],
                "warmup_bars": scale.warmup_bars,
                "group": scale.group,
                "fixture_periods": _periods(scale),
                "fixtures": [run_fixture(scale, fixture) for fixture in FIXTURES],
            }
        )
    reconciliation = [
        f["reference_reconciliation_max_abs_period_diff"]
        for s in scales
        for f in s["fixtures"]
        if "reference_reconciliation_max_abs_period_diff" in f
    ]
    return {
        "artifact": ARTIFACT_VERSION,
        "method_version": METHOD_VERSION,
        "method_status": METHOD_STATUS,
        "contract": "research/protocols/SYSTEM-G1-CYCLE-METHOD-V1.md",
        "evidence_class": "SYNTHETIC_METHOD_VALIDATION_ONLY",
        "market_data_read": False,
        "btc_returns_or_outcomes_used": False,
        "quality_thresholds_selected": False,
        "quality_labels_assigned": [
            "UNAVAILABLE",
            "UNLABELED_THRESHOLDS_PENDING_RESEARCH_DIRECTOR",
        ],
        "threshold_authority": "RESEARCH_DIRECTOR_ONLY",
        "cycle_active_in_decisions": CYCLE_DECISION_ACTIVATION,
        "decision_path_cycle_role": "METHOD_NOT_READY",
        "implementation_choices_for_review": [
            "high-pass cutoff = period2 and SuperSmoother cutoff = period1 (2016 ACP companion)",
            "normalization by the current band maximum of R (no MaxPwr decay/AGC)",
            "DFT over lags 3..period2 (lags below the Pearson averaging length excluded)",
            (
                "phase-like coordinate = cos(atan2(sum x sin(wk), sum x cos(wk))) over "
                "round(period) trailing filtered samples; explained_fraction = "
                "(2/L)(re^2+im^2)/sum x^2"
            ),
            (
                "turn: slope sign change, confirmed by one further completed bar without "
                "reversal; estimated turn time = close of the bar before the sign change"
            ),
            "gap or incomplete input bar: full recursive reset and re-warm of max(4*period2, 128)",
        ],
        "quality_metric_definitions": {
            "explained_fraction": "variance share of the trailing window explained by the "
            "dominant-period projection (numerical, not a probability)",
            "mean_normalized_power": "mean normalized ACP power across the band (lower = more "
            "concentrated spectrum)",
            "peak_band_fraction": "share of band periods with normalized power >= 0.5",
            "period_change": "absolute one-bar change of the dominant period (bars)",
        },
        "evaluation_bars_per_fixture": EVALUATION_BARS,
        "fixture_amplitude": AMPLITUDE,
        "noise_seed_base": SEED,
        "reference_reconciliation_max_abs_period_diff": max(reconciliation),
        "scales": scales,
    }
