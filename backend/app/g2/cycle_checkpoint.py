"""G2 Cycle Causality Checkpoint V1, section 13: the thirteen code-level method tests.

Every test runs the actual G2 adapter (`ShadowScale`, which wraps the unchanged G1 ACP tracker) on
synthetic series only. The white-noise and coherent-cycle gates reuse the frozen G1 protocol
series generators and thresholds (SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1); nothing is tuned.
The additive-noise occupancy is recorded as a diagnostic next to the checkpoint's reference
numbers, never as a target. The Research Director alone classifies the result.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

import numpy as np

from app.g1 import cycle_quality_gate as gate
from app.g1.cycle import SCALES, UNAVAILABLE, USABLE, Scale, ScaleTracker

from .cycle import ShadowScale, period_stability, projection_amplitude

EPOCH = datetime(2001, 1, 1, tzinfo=UTC)
NOISE_REFERENCE = {  # checkpoint section 4 (diagnostic references, not targets)
    "45m": 0.674,
    "3h": 0.799,
    "1d": 0.861,
    "4d": 0.876,
    "1w": 1.000,
    "4w": 0.926,
}


def feed(
    scale_index: int, values: np.ndarray, present: np.ndarray | None = None
) -> list[dict[str, Any]]:
    """Run one fresh G2 shadow scale; one row per present input bar."""
    scale = SCALES[scale_index]
    shadow = ShadowScale(scale_index)
    step = timedelta(minutes=scale.bar_minutes)
    rows = []
    for index, value in enumerate(values):
        if present is not None and not present[index]:
            continue
        opened = EPOCH + index * step
        shadow.update(opened, opened + step, float(value), True)
        tracker = shadow.tracker
        turn = tracker.last_turn
        state = shadow.state()
        rows.append(
            {
                "index": index,
                "time": opened + step,
                "label": state.quality_label,
                "dominant": tracker.dominant if tracker.ready else None,
                "raw_dominant": tracker.dominant,
                "raw_previous": tracker.previous_dominant,
                "ready": tracker.ready,
                "phase": state.phase_degrees,
                "coordinate": state.projection_coordinate,
                "explained": tracker.explained,
                "amplitude": state.projection_amplitude,
                "stability": state.period_stability,
                "turn": None
                if turn is None
                else (turn.kind, turn.estimated_turn_time, turn.confirmation_time),
                "bars_seen": tracker.bars_seen,
                "trailing": tracker.acp.trailing_filtered(scale.period2),
            }
        )
    return rows


def occupancy(scale: Scale, rows: list[dict[str, Any]], evaluated: int) -> float:
    after = [r for r in rows if r["index"] >= scale.warmup_bars]
    return sum(r["label"] == USABLE for r in after) / evaluated


def _ensemble(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    return {
        "median": float(np.median(arr)),
        "p10": float(np.quantile(arr, 0.10)),
        "p95": float(np.quantile(arr, 0.95)),
    }


def t01_parity(length_extra: int = 160) -> dict[str, Any]:
    """G2 adapter vs an independent frozen G1 tracker: byte/numeric identical core outputs."""
    worst = 0.0
    mismatches = 0
    for i, scale in enumerate(SCALES):
        rng = np.random.default_rng(900 + i)
        n = scale.warmup_bars + length_extra
        t = np.arange(n)
        mid = (scale.period1 + scale.period2) / 2
        values = 100 + np.sin(2 * np.pi * t / mid) + rng.normal(0, 0.3, n)
        reference = ScaleTracker(scale)
        shadow = ShadowScale(i)
        step = timedelta(minutes=scale.bar_minutes)
        for k, value in enumerate(values):
            opened = EPOCH + k * step
            reference.update(opened, opened + step, float(value), True)
            shadow.update(opened, opened + step, float(value), True)
            a, b = reference.state(), shadow.tracker.state()
            if a != b:
                mismatches += 1
            for x, y in (
                (reference.dominant, shadow.tracker.dominant),
                (reference.phase, shadow.tracker.phase),
            ):
                if x is not None and y is not None:
                    worst = max(worst, abs(x - y))
                elif (x is None) != (y is None):
                    mismatches += 1
    return {
        "pass": mismatches == 0 and worst == 0.0,
        "mismatches": mismatches,
        "max_abs_difference": worst,
    }


def noise_scale(i: int, paths: int = gate.NOISE_PATHS) -> dict[str, Any]:
    scale = SCALES[i]
    occ = [
        occupancy(scale, feed(i, gate.noise_series(i, scale, p)), gate.EVALUATED_BARS)
        for p in range(paths)
    ]
    summary = _ensemble(occ)
    passed = summary["median"] <= gate.NOISE_MEDIAN_MAX and summary["p95"] <= gate.NOISE_P95_MAX
    return {**summary, "pass": passed}


def coherent_scale(i: int, paths: int = gate.CYCLE_PATHS) -> dict[str, Any]:
    scale = SCALES[i]
    families = {}
    for family, trend in (("clean_cycle", False), ("trend_plus_cycle", True)):
        occ, errors = [], []
        for p in range(paths):
            period, _ = gate.cycle_design(i, scale, p)
            rows = feed(i, gate.cycle_series(i, scale, p, trend))
            occ.append(occupancy(scale, rows, gate.EVALUATED_BARS))
            dominant = [
                r["dominant"]
                for r in rows
                if r["index"] >= scale.warmup_bars and r["dominant"] is not None
            ]
            if dominant:
                errors.append(float(median(abs(d - period) / period for d in dominant)))
        summary = _ensemble(occ)
        summary["period_error_median"] = float(median(errors)) if errors else math.inf
        passed = (
            summary["median"] >= gate.COHERENT_MEDIAN_MIN
            and summary["p10"] >= gate.COHERENT_P10_MIN
            and summary["period_error_median"] <= gate.PERIOD_ERROR_MAX
        )
        families[family] = {**summary, "pass": passed}
    return families


def additive_scale(i: int, paths: int = 48) -> dict[str, Any]:
    scale = SCALES[i]
    period = (scale.period1 + scale.period2) / 2
    n = scale.warmup_bars + gate.EVALUATED_BARS
    occ, errors, finite, abstained, labelled = [], [], True, 0, True
    for p in range(paths):
        rng = np.random.default_rng(31_000 + 1000 * i + p)
        phase = rng.uniform(0, 2 * np.pi)
        t = np.arange(n)
        values = 100 + np.sin(2 * np.pi * t / period + phase) + rng.normal(0, 0.5, n)
        rows = feed(i, values)
        after = [r for r in rows if r["index"] >= scale.warmup_bars]
        occ.append(occupancy(scale, rows, gate.EVALUATED_BARS))
        abstained += sum(r["label"] != USABLE for r in after)
        labelled &= all(r["label"] in (UNAVAILABLE, "WEAK", USABLE) for r in after)
        for r in after:
            for key in ("dominant", "phase", "coordinate", "explained", "amplitude"):
                if r[key] is not None and not math.isfinite(r[key]):
                    finite = False
        dominant = [r["dominant"] for r in after if r["dominant"] is not None]
        if dominant:
            errors.append(float(median(abs(d - period) / period for d in dominant)))
    return {
        **_ensemble(occ),
        "period_error_median": float(median(errors)) if errors else None,
        "reference_median_occupancy": NOISE_REFERENCE[scale.nominal],
        "finite": finite,
        "explicit_quality_label_every_bar": labelled,
        "abstained_bars": abstained,
        "pass": finite and labelled,
    }


def t02_white_noise(
    paths: int = gate.NOISE_PATHS, scales: dict[str, Any] | None = None
) -> dict[str, Any]:
    per_scale = scales or {s.nominal: noise_scale(i, paths) for i, s in enumerate(SCALES)}
    return {
        "pass": all(v["pass"] for v in per_scale.values()),
        "paths_per_scale": paths,
        "scales": per_scale,
    }


def t03_coherent_cycle(
    paths: int = gate.CYCLE_PATHS, scales: dict[str, Any] | None = None
) -> dict[str, Any]:
    per_scale = scales or {s.nominal: coherent_scale(i, paths) for i, s in enumerate(SCALES)}
    ok = all(f["pass"] for families in per_scale.values() for f in families.values())
    return {"pass": ok, "paths_per_scale": paths, "scales": per_scale}


def t04_additive_noise(paths: int = 48, scales: dict[str, Any] | None = None) -> dict[str, Any]:
    """Finite outputs, an explicit quality label on every bar and observed abstention.

    Abstention is required across the fixture, not per scale: the checkpoint's own reference
    shows ~100% 1w occupancy for this fixture, so a zero per-scale abstention count there is the
    recorded diagnostic, not a failure.
    """
    per_scale = scales or {s.nominal: additive_scale(i, paths) for i, s in enumerate(SCALES)}
    total = sum(v["abstained_bars"] for v in per_scale.values())
    return {
        "pass": all(v["pass"] for v in per_scale.values()) and total > 0,
        "paths_per_scale": paths,
        "abstained_bars_total": total,
        "scales": per_scale,
        "note": "occupancy is diagnostic; the reference values are not tuning targets",
    }


def t05_linear_trend() -> dict[str, Any]:
    usable = {}
    for i, scale in enumerate(SCALES):
        n = scale.warmup_bars + gate.EVALUATED_BARS
        rows = feed(i, 100 + 0.05 * np.arange(n))
        usable[scale.nominal] = sum(
            r["label"] == USABLE for r in rows if r["index"] >= scale.warmup_bars
        )
    return {"pass": all(v == 0 for v in usable.values()), "usable_after_warmup": usable}


def t06_isolated_jump() -> dict[str, Any]:
    usable = {}
    for i, scale in enumerate(SCALES):
        n = scale.warmup_bars + gate.EVALUATED_BARS
        jump = scale.warmup_bars + 100
        values = np.where(np.arange(n) >= jump, 110.0, 100.0)
        rows = feed(i, values)
        usable[scale.nominal] = sum(
            r["label"] == USABLE for r in rows if jump <= r["index"] < jump + 64
        )
    return {"pass": all(v == 0 for v in usable.values()), "usable_first_64_post_jump": usable}


def chirp(scale: Scale, n: int) -> np.ndarray:
    width = scale.period2 - scale.period1
    lo, hi = scale.period1 + 0.25 * width, scale.period1 + 0.75 * width
    periods = lo + (hi - lo) * np.arange(n) / (n - 1)
    phase = np.cumsum(2 * np.pi / periods)
    return 100 + np.sin(phase)


def t07_varying_frequency() -> dict[str, Any]:
    detail = {}
    ok = True
    for i, scale in enumerate(SCALES):
        n = scale.warmup_bars + gate.EVALUATED_BARS
        values = chirp(scale, n)
        rows = feed(i, values)
        after = [r for r in rows if r["index"] >= scale.warmup_bars]
        bounded = all(
            r["dominant"] is None or scale.period1 <= r["dominant"] <= scale.period2 for r in after
        ) and all(r["phase"] is None or 0.0 <= r["phase"] < 360.0 for r in after)
        prefix = feed(i, values[: n // 2])
        causal = _same(prefix, rows[: len(prefix)])
        detail[scale.nominal] = {"bounded": bounded, "no_look_ahead_prefix_identity": causal}
        ok &= bounded and causal
    return {"pass": ok, "scales": detail}


KEYS = ("label", "dominant", "phase", "coordinate", "explained", "amplitude", "stability", "turn")


def _same(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> bool:
    return len(a) == len(b) and all(x[k] == y[k] for x, y in zip(a, b, strict=True) for k in KEYS)


def t08_prefix_invariance() -> dict[str, Any]:
    detail = {}
    for i, scale in enumerate(SCALES):
        rng = np.random.default_rng(4_000 + i)
        n = scale.warmup_bars + 300
        values = 100 + np.sin(np.arange(n) / 3.0) + rng.normal(0, 0.4, n)
        present = np.ones(n, dtype=bool)
        present[scale.warmup_bars // 2] = False  # includes gap/reset state in the prefix
        full = feed(i, values, present)
        cut = scale.warmup_bars + 150
        prefix = feed(i, values[:cut], present[:cut])
        detail[scale.nominal] = _same(prefix, full[: len(prefix)])
    return {"pass": all(detail.values()), "scales": detail}


def t09_gap_reset() -> dict[str, Any]:
    detail = {}
    for i, scale in enumerate(SCALES):
        rng = np.random.default_rng(5_000 + i)
        n = 3 * scale.warmup_bars
        values = 100 + np.sin(2 * np.pi * np.arange(n) / scale.period1) + rng.normal(0, 0.2, n)
        gap_at = scale.warmup_bars + 20
        present = np.ones(n, dtype=bool)
        present[gap_at] = False
        rows = feed(i, values, present)
        post = [r for r in rows if r["index"] > gap_at]
        rewarm = post[: scale.warmup_bars - 1]
        unavailable = all(r["label"] == UNAVAILABLE and r["dominant"] is None for r in rewarm)
        restarted = post[0]["bars_seen"] == 1
        fresh = feed(i, values[gap_at + 1 :])
        tail_equal = all(
            x[k] == y[k]
            for x, y in zip(post, fresh, strict=True)
            for k in ("label", "dominant", "phase", "amplitude", "turn")
            if k != "turn"
        )
        # a partial (incomplete) input bar also resets
        shadow = ShadowScale(i)
        step = timedelta(minutes=scale.bar_minutes)
        for k in range(scale.warmup_bars + 5):
            opened = EPOCH + k * step
            shadow.update(opened, opened + step, float(values[k]), True)
        opened = EPOCH + (scale.warmup_bars + 5) * step
        shadow.update(opened, opened + step, 100.0, False)
        incomplete_reset = (
            shadow.tracker.bars_seen == 0 and shadow.state().quality_label == UNAVAILABLE
        )
        detail[scale.nominal] = {
            "unavailable_during_rewarm": unavailable,
            "counter_restarted": restarted,
            "equals_fresh_tracker_after_gap": tail_equal,
            "incomplete_bar_resets": incomplete_reset,
        }
    ok = all(all(v.values()) for v in detail.values())
    return {"pass": ok, "scales": detail}


def t10_projection_amplitude() -> dict[str, Any]:
    checked, bad = 0, 0
    for i, scale in enumerate(SCALES):
        rng = np.random.default_rng(6_000 + i)
        n = scale.warmup_bars + 200
        values = 100 + 2 * np.sin(2 * np.pi * np.arange(n) / scale.period2) + rng.normal(0, 0.3, n)
        for r in feed(i, values):
            if r["coordinate"] is None or not r["ready"]:
                continue
            checked += 1
            expected = projection_amplitude(r["trailing"], r["raw_dominant"])
            amp = r["amplitude"]
            if amp is None or not math.isfinite(amp) or amp < 0 or amp != expected:
                bad += 1
            length = round(r["raw_dominant"])
            window = r["trailing"][:length]
            omega = 2 * math.pi / length
            re = sum(x * math.cos(omega * k) for k, x in enumerate(window))
            im = sum(x * math.sin(omega * k) for k, x in enumerate(window))
            if abs(amp - 2 * math.sqrt(re * re + im * im) / length) > 1e-12:  # type: ignore[operator]
                bad += 1
    return {"pass": checked > 0 and bad == 0, "checked": checked, "violations": bad}


def t11_period_stability() -> dict[str, Any]:
    checked, bad, nulls = 0, 0, 0
    for i, scale in enumerate(SCALES):
        rng = np.random.default_rng(7_000 + i)
        n = scale.warmup_bars + 200
        values = 100 + np.sin(np.arange(n) / 2.5) + rng.normal(0, 0.5, n)
        for r in feed(i, values):
            current, previous = r["raw_dominant"], r["raw_previous"]
            if not r["ready"] or current is None or previous is None:
                nulls += r["stability"] is None
                bad += r["stability"] is not None
                continue
            checked += 1
            expected = abs(current - previous) / max(previous, 1e-12)
            bad += r["stability"] != expected or period_stability(current, previous) != expected
    return {"pass": checked > 0 and bad == 0, "checked": checked, "nulls": nulls, "violations": bad}


def t12_turn_confirmation() -> dict[str, Any]:
    turns, violations = 0, 0
    for i, scale in enumerate(SCALES):
        n = scale.warmup_bars + 300
        values = 100 + np.sin(2 * np.pi * np.arange(n) / ((scale.period1 + scale.period2) / 2))
        seen = set()
        for r in feed(i, values):
            if r["turn"] is None:
                continue
            _, estimated, confirmed = r["turn"]
            if confirmed > r["time"] or confirmed <= estimated:
                violations += 1
            if r["turn"] not in seen:
                seen.add(r["turn"])
                turns += 1
                if confirmed != r["time"]:  # first visible exactly when confirmed, never earlier
                    violations += 1
    return {"pass": turns > 0 and violations == 0, "turns": turns, "violations": violations}


def t13_replay_speed_identity() -> dict[str, Any]:
    from . import fixtures, runs
    from .records import CycleShadowState
    from .store import canonical_bytes

    spec = runs.RunSpec(
        "G2-CYCLE-REPLAY-SPEED",
        "cycle replay-speed identity",
        runs.SYNTHETIC,
        fixtures.START,
        fixtures.START + timedelta(days=12),
        lambda: fixtures.synthetic_minutes(days=12),
        lambda: fixtures.synthetic_funding(days=12),
        fixtures.SYNTHETIC_FILTERS,
        lambda run_id: (),
        "cycle replay-speed identity",
    )
    built = runs.build(spec)

    def cycle_bytes(core: Any) -> list[bytes]:
        return [canonical_bytes(c) for c in core.store.of_type(CycleShadowState)]

    reference = cycle_bytes(runs.run_batch(built))
    variants = [cycle_bytes(runs.run_in_steps(built, timedelta(minutes=m))) for m in (7, 240, 1440)]
    return {"pass": all(v == reference for v in variants), "records": len(reference)}


def run_checkpoint(
    noise_paths: int = gate.NOISE_PATHS,
    cycle_paths: int = gate.CYCLE_PATHS,
    additive_paths: int = 48,
) -> dict[str, Any]:
    tests = {
        "01_g1_g2_numeric_parity": t01_parity(),
        "02_white_noise_gate": t02_white_noise(noise_paths),
        "03_coherent_cycle_gate": t03_coherent_cycle(cycle_paths),
        "04_additive_noise_amp1_sd0_5": t04_additive_noise(additive_paths),
        "05_pure_linear_trend_no_usable": t05_linear_trend(),
        "06_isolated_jump_abstention": t06_isolated_jump(),
        "07_varying_frequency_bounded_causal": t07_varying_frequency(),
        "08_prefix_invariance": t08_prefix_invariance(),
        "09_gap_reset_full_rewarm": t09_gap_reset(),
        "10_projection_amplitude_valid": t10_projection_amplitude(),
        "11_period_stability_exact": t11_period_stability(),
        "12_turn_confirmation_delayed": t12_turn_confirmation(),
        "13_replay_speed_identity": t13_replay_speed_identity(),
    }
    return {
        "all_pass": all(t["pass"] for t in tests.values()),
        "tests": tests,
        "market_data_read": False,
        "parameters_tuned": False,
        "method_tournament": False,
        "classification_authority": "RESEARCH_DIRECTOR",
    }
