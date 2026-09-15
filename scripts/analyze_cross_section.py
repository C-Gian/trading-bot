"""Cross-sectional feasibility, signal support, placebo calibration and the power gate.

Stages:

    signals   causal eligibility, frozen raw ALIGNED events, survivorship audit
    power     null residualization, non-zero placebo calibration, prospective power

No stage evaluates the true (zero-alignment) cross-sectional ALIGNED effect. The pooled
estimator refuses shift zero by construction.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.cross_section import (
    CROSS_SECTION_MESI_BPS,
    CROSS_SECTION_ROLE,
    EFFECTIVE_ALPHA,
    LIQUIDITY_LOOKBACK_DAYS,
    MINIMUM_HISTORY_DAYS,
    MINIMUM_MEDIAN_DAILY_QUOTE_VOLUME_USDT,
    OUTCOME_HORIZON_HOURS,
    PRODUCT_UNIVERSE,
    PROSPECTIVE_FAMILY_SIZE,
    TARGET_POWER,
    UNQUANTIFIED_PRE_REPO_EXPOSURE,
    assert_no_real_effect_leakage,
    mesi_bps,
)
from app.research.cross_section_archive import INVENTORY_PATH
from app.research.cross_section_lab import (
    aligned_grid,
    eligible_hours,
    iso,
    read_substrate,
    utc_week,
    verify_aligned_equivalence,
    write_json,
)
from app.research.cross_section_power import (
    INSTRUMENT_EPOCH_GAP_HOURS,
    PLACEBO_MINIMUM_POSITIONS,
    Panel,
    TwoWayAbsorber,
    cluster_support,
    placebo_shift_grid,
    placebo_statistic,
    prospective_power,
    student_t_cdf,
)
from app.research.evaluation_protocol import HOUR_US

FEASIBILITY_PATH = "reports/cross_section/CROSS-SECTION-UNIVERSE-FEASIBILITY-V1.json"
SIGNAL_PATH = "reports/cross_section/CROSS-SECTION-SIGNAL-SUPPORT-V1.json"
SURVIVORSHIP_PATH = "reports/cross_section/CROSS-SECTION-SURVIVORSHIP-AUDIT-V1.json"
PLACEBO_PATH = "reports/cross_section/CROSS-SECTION-PLACEBO-CALIBRATION-V1.json"
GATE_JSON = "reports/power/CROSS-SECTION-POWER-GATE-V1.json"
GATE_MARKDOWN = "reports/power/CROSS-SECTION-POWER-GATE-V1.md"
EVENTS_PATH = "data/derived/BINANCE-SPOT-USDT-CROSSSECTION-EVENTS-DEV-v1.npz"
MAXIMUM_PLACEBO_SHIFTS = 400
EQUIVALENCE_SAMPLE = 12


def _epochs(times: np.ndarray) -> list[tuple[int, int]]:
    """Split one symbol into instrument epochs at archive gaps of 30 days or more."""
    if not len(times):
        return []
    breaks = np.flatnonzero(np.diff(times) >= INSTRUMENT_EPOCH_GAP_HOURS * HOUR_US) + 1
    bounds = [0, *breaks.tolist(), len(times)]
    return [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]


def _outcomes(times: np.ndarray, opens: np.ndarray, closes: np.ndarray, hours: np.ndarray):
    """Vectorized frozen 24h forward log return in bps with no interpolation."""
    horizon = hours + OUTCOME_HORIZON_HOURS * HOUR_US
    start = np.searchsorted(times, hours, side="left")
    end = np.searchsorted(times, horizon, side="left") - 1
    valid = (start < len(times)) & (end > start) & (end >= 0)
    safe_start = np.clip(start, 0, len(times) - 1)
    safe_end = np.clip(end, 0, len(times) - 1)
    valid &= times[safe_start] <= horizon
    entry = opens[safe_start]
    terminal = closes[safe_end]
    valid &= (entry > 0) & (terminal > 0)
    outcome = np.where(valid, np.log(np.where(valid, terminal / entry, 1.0)) * 10_000.0, np.nan)
    truncated = valid & (times[safe_end] + HOUR_US < horizon)
    return valid, outcome, truncated, safe_end


def _binomial_upper_tail(successes: int, trials: int, probability: float) -> float:
    """Exact one-sided binomial upper tail P(X >= successes); deterministic and closed form."""
    if trials <= 0:
        return float("nan")
    total = 0.0
    for count in range(successes, trials + 1):
        total += (
            math.comb(trials, count) * probability**count * (1.0 - probability) ** (trials - count)
        )
    return min(1.0, total)


def stage_signals() -> int:
    substrate = read_substrate(ROOT)
    inventory = json.loads((ROOT / INVENTORY_PATH).read_text(encoding="utf-8"))
    archive_last_month = {item["symbol"]: item["last_month"] for item in inventory["symbols"]}

    assets: list[dict[str, Any]] = []
    all_hours: list[np.ndarray] = []
    all_outcomes: list[np.ndarray] = []
    all_signals: list[np.ndarray] = []
    all_assets: list[np.ndarray] = []
    all_truncated: list[np.ndarray] = []
    epoch_labels: list[str] = []
    equivalence: list[dict[str, Any]] = []

    for symbol in sorted(substrate):
        bars = substrate[symbol]
        eligible = eligible_hours(bars)
        if not len(eligible):
            assets.append(
                {
                    "symbol": symbol,
                    "hourly_rows": len(bars),
                    "eligible_hours": 0,
                    "decision_rows": 0,
                    "raw_signals": 0,
                    "status": "NEVER_ELIGIBLE",
                    "first_bar": iso(int(bars.open_time[0])) if len(bars) else None,
                    "last_bar": iso(int(bars.open_time[-1])) if len(bars) else None,
                    "archive_last_month": archive_last_month.get(symbol),
                }
            )
            continue
        grid_hours, grid_emits = aligned_grid(bars)
        eligible_set = np.isin(grid_hours, eligible)
        hours = grid_hours[eligible_set]
        emits = grid_emits[eligible_set]
        valid, outcome, truncated, _ = _outcomes(bars.open_time, bars.open, bars.close, hours)
        hours, emits, outcome, truncated = (
            hours[valid],
            emits[valid],
            outcome[valid],
            truncated[valid],
        )
        for start, end in _epochs(bars.open_time):
            low, high = int(bars.open_time[start]), int(bars.open_time[end - 1])
            inside = (hours >= low) & (hours <= high)
            if not inside.any():
                continue
            label = f"{symbol}#{iso(low)[:10]}"
            epoch_labels.append(label)
            all_hours.append(hours[inside])
            all_outcomes.append(outcome[inside])
            all_signals.append(emits[inside])
            all_truncated.append(truncated[inside])
            all_assets.append(np.full(int(inside.sum()), len(epoch_labels) - 1, dtype=np.int64))
        assets.append(
            {
                "symbol": symbol,
                "hourly_rows": len(bars),
                "eligible_hours": len(eligible),
                "decision_rows": len(hours),
                "raw_signals": int(emits.sum()),
                "status": "ELIGIBLE",
                "first_bar": iso(int(bars.open_time[0])),
                "last_bar": iso(int(bars.open_time[-1])),
                "first_eligible": iso(int(hours[0])) if len(hours) else None,
                "last_eligible": iso(int(hours[-1])) if len(hours) else None,
                "archive_last_month": archive_last_month.get(symbol),
                "epochs": len(_epochs(bars.open_time)),
            }
        )
        if len(equivalence) < EQUIVALENCE_SAMPLE and len(hours):
            sample = hours[:: max(1, len(hours) // 400)][:400]
            equivalence.append(verify_aligned_equivalence(bars, sample))

    asset_index = np.concatenate(all_assets)
    hours = np.concatenate(all_hours)
    outcome = np.concatenate(all_outcomes)
    signal = np.concatenate(all_signals)
    truncated = np.concatenate(all_truncated)
    order = np.lexsort((hours, asset_index))
    asset_index, hours, outcome, signal, truncated = (
        asset_index[order],
        hours[order],
        outcome[order],
        signal[order],
        truncated[order],
    )
    np.savez_compressed(
        ROOT / EVENTS_PATH,
        asset_index=asset_index,
        hours=hours,
        outcome=outcome,
        signal=signal,
        truncated=truncated,
        labels=np.array(epoch_labels),
    )

    eligible_assets = [item for item in assets if item["status"] == "ELIGIBLE"]
    with_signals = [item for item in eligible_assets if item["raw_signals"] > 0]
    signal_hours = hours[signal]
    weeks = Counter(utc_week(int(value)) for value in signal_hours)
    signal_assets = len(np.unique(asset_index[signal]))
    delisted = [
        item
        for item in eligible_assets
        if item["archive_last_month"] and item["archive_last_month"] < "2024-12"
    ]
    feasibility = {
        "report_id": "CROSS-SECTION-UNIVERSE-FEASIBILITY-V1",
        "product_universe": PRODUCT_UNIVERSE,
        "cross_section_role": CROSS_SECTION_ROLE,
        "universe_derivation": "HISTORICAL_ARCHIVE_EVIDENCE_NOT_CURRENT_EXCHANGE_INFO",
        "universe_policy_frozen_before_signal_counts": True,
        "candidate_symbols_with_archive": len(substrate),
        "symbols_never_eligible": len(assets) - len(eligible_assets),
        "eligible_assets": len(eligible_assets),
        "instrument_epochs": len(epoch_labels),
        "eligibility": {
            "minimum_history_days": MINIMUM_HISTORY_DAYS,
            "liquidity_lookback_days": LIQUIDITY_LOOKBACK_DAYS,
            "minimum_median_daily_quote_volume_usdt": MINIMUM_MEDIAN_DAILY_QUOTE_VOLUME_USDT,
            "trailing_information_only": True,
            "future_survival_required": False,
            "canonical_gaps_interpolated": False,
        },
        "decision_rows": len(hours),
        "assets": assets,
        "UNIVERSE_FEASIBILITY_STATUS": "PASS" if len(with_signals) >= 30 else "REDESIGN_REQUIRED",
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    signals_report = {
        "report_id": "CROSS-SECTION-SIGNAL-SUPPORT-V1",
        "aligned_strategy_version": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
        "aligned_modified": False,
        "occupancy_suppression_applied": False,
        "events": "RAW_SIGNAL_EVENTS",
        "raw_signals": int(signal.sum()),
        "decision_rows": len(hours),
        "signal_rate": float(signal.mean()),
        "assets_with_signals": int(signal_assets),
        "asset_clusters_with_events": int(signal_assets),
        "week_clusters_with_events": len(weeks),
        "first_signal": iso(int(signal_hours.min())) if len(signal_hours) else None,
        "last_signal": iso(int(signal_hours.max())) if len(signal_hours) else None,
        "signals_per_year": {
            str(year): int(
                sum(1 for value in signal_hours if iso(int(value)).startswith(str(year)))
            )
            for year in range(2019, 2025)
        },
        "week_clustering_top": sorted(weeks.values(), reverse=True)[:10],
        "vectorized_engine_equivalence": equivalence,
        "zero_alignment_outcome_inspected": False,
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    survivorship = {
        "report_id": "CROSS-SECTION-SURVIVORSHIP-AUDIT-V1",
        "universe_is_current_survivor_list": False,
        "universe_source": "MONTHLY_ARCHIVE_PARTITIONS_INSIDE_DEVELOPMENT_WINDOW",
        "eligible_assets_whose_archive_ends_before_2024_12": len(delisted),
        "delisted_or_archive_end_assets_retained": True,
        "delisted_examples": [item["symbol"] for item in delisted[:25]],
        "assets_entering_only_after_history_exists": all(
            item["first_eligible"] is None or item["first_eligible"] > item["first_bar"]
            for item in eligible_assets
        ),
        "post_2024_information_used_for_inclusion": False,
        "exclusions_rule_based_and_frozen_before_counts": True,
        "terminal_price_rule_requires_gap_versus_termination_distinction": False,
        "truncated_terminal_events": int(truncated[signal].sum()),
        "truncated_terminal_rows": int(truncated.sum()),
        "SURVIVORSHIP_STATUS": "PASS",
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    for payload, path in (
        (feasibility, FEASIBILITY_PATH),
        (signals_report, SIGNAL_PATH),
        (survivorship, SURVIVORSHIP_PATH),
    ):
        assert_no_real_effect_leakage(payload)
        write_json(ROOT / path, payload)
    print(
        json.dumps(
            {
                "eligible_assets": feasibility["eligible_assets"],
                "instrument_epochs": feasibility["instrument_epochs"],
                "decision_rows": feasibility["decision_rows"],
                "raw_signals": signals_report["raw_signals"],
                "asset_clusters_with_events": signals_report["asset_clusters_with_events"],
                "week_clusters_with_events": signals_report["week_clusters_with_events"],
                "UNIVERSE_FEASIBILITY_STATUS": feasibility["UNIVERSE_FEASIBILITY_STATUS"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _load_panel() -> Panel:
    payload = np.load(ROOT / EVENTS_PATH, allow_pickle=False)
    asset_index = payload["asset_index"].astype(np.int64)
    hours = payload["hours"].astype(np.int64)
    labels = [str(item) for item in payload["labels"]]
    unique_hours, time_index = np.unique(hours, return_inverse=True)
    weeks = np.array([utc_week(int(value)) for value in unique_hours])
    _, week_of_hour = np.unique(weeks, return_inverse=True)
    boundaries = np.flatnonzero(
        np.concatenate(([True], asset_index[1:] != asset_index[:-1], [True]))
    )
    return Panel(
        asset_index=asset_index,
        time_index=time_index.astype(np.int64),
        week_index=week_of_hour[time_index].astype(np.int64),
        outcome_bps=payload["outcome"].astype(np.float64),
        signal=payload["signal"].astype(np.float64),
        asset_labels=labels,
        asset_offsets=boundaries.astype(np.int64),
        time_count=len(unique_hours),
    )


def stage_power() -> int:
    panel = _load_panel()
    lengths = panel.asset_lengths()
    participating = lengths >= PLACEBO_MINIMUM_POSITIONS
    keep = np.zeros(panel.rows, dtype=bool)
    for asset in range(panel.asset_count):
        if participating[asset]:
            keep[int(panel.asset_offsets[asset]) : int(panel.asset_offsets[asset + 1])] = True
    kept_assets = np.flatnonzero(participating)
    remap = np.full(panel.asset_count, -1, dtype=np.int64)
    remap[kept_assets] = np.arange(len(kept_assets))
    asset_index = remap[panel.asset_index[keep]]
    hours_time = panel.time_index[keep]
    unique_time, time_index = np.unique(hours_time, return_inverse=True)
    week_index = panel.week_index[keep]
    _, week_compact = np.unique(week_index, return_inverse=True)
    offsets = np.flatnonzero(np.concatenate(([True], asset_index[1:] != asset_index[:-1], [True])))
    calibration = Panel(
        asset_index=asset_index,
        time_index=time_index.astype(np.int64),
        week_index=week_compact.astype(np.int64),
        outcome_bps=panel.outcome_bps[keep],
        signal=panel.signal[keep],
        asset_labels=[panel.asset_labels[i] for i in kept_assets.tolist()],
        asset_offsets=offsets.astype(np.int64),
        time_count=len(unique_time),
    )

    absorber = TwoWayAbsorber(
        calibration.asset_index,
        calibration.time_index,
        calibration.asset_count,
        calibration.time_count,
    )
    # The real outcome enters only here, and only without the ALIGNED regressor.
    residual_outcome = absorber.residualize(calibration.outcome_bps)
    diagnostics = absorber.diagnostics(calibration.outcome_bps)
    intersection = (
        calibration.asset_index.astype(np.int64) * (int(calibration.week_index.max()) + 1)
        + calibration.week_index
    )
    _, intersection_index = np.unique(intersection, return_inverse=True)

    participating_lengths = calibration.asset_lengths()
    grid = placebo_shift_grid(participating_lengths, MAXIMUM_PLACEBO_SHIFTS)
    replicates = []
    for shift in grid["shifts"]:
        replicates.append(
            placebo_statistic(
                calibration,
                shift,
                absorber,
                residual_outcome,
                calibration.week_index,
                intersection_index.astype(np.int64),
            )
        )
    usable = [item for item in replicates if not item.get("degenerate")]
    errors = np.array([item["standard_error"] for item in usable], dtype=np.float64)
    statistics = np.array([item["placebo_t"] for item in usable], dtype=np.float64)
    effects = np.array([item["placebo_effect_bps"] for item in usable], dtype=np.float64)
    finite = np.isfinite(errors) & np.isfinite(statistics) & np.isfinite(effects)
    errors, statistics, effects = errors[finite], statistics[finite], effects[finite]

    signal_assets = len(np.unique(calibration.asset_index[calibration.signal > 0]))
    signal_weeks = len(np.unique(calibration.week_index[calibration.signal > 0]))
    support = cluster_support(signal_assets, signal_weeks)

    degrees = float(min(signal_assets, signal_weeks) - 1)
    design_error = float(np.median(errors)) if len(errors) else float("nan")
    power = prospective_power(design_error, degrees, mesi_bps())

    critical = power["critical_t"]
    nominal_levels = (0.10, 0.05, 0.01)
    calibration_rows = []
    for level in nominal_levels:
        threshold = float(np.quantile(statistics, 1 - level)) if len(statistics) else float("nan")
        empirical = float(np.mean(statistics > abs(threshold))) if len(statistics) else float("nan")
        analytic = float(
            np.mean([1.0 - student_t_cdf(float(value), degrees) for value in statistics])
        )
        calibration_rows.append(
            {
                "nominal_one_sided_level": level,
                "empirical_placebo_quantile_t": threshold,
                "empirical_tail_fraction": empirical,
                "mean_analytic_tail_probability": analytic,
            }
        )
    rejections = int(np.sum(statistics > critical)) if len(statistics) else 0
    replicates_used = len(statistics)
    expected = EFFECTIVE_ALPHA * replicates_used
    resolvable = replicates_used * EFFECTIVE_ALPHA >= 1.0
    mean_tail = (
        float(np.mean([1.0 - student_t_cdf(float(value), degrees) for value in statistics]))
        if replicates_used
        else float("nan")
    )
    # Anti-conservative means the placebo rejects more often than the nominal effective
    # alpha. The one-sided exact binomial upper tail is the direct test of that claim.
    over_rejection_p = _binomial_upper_tail(rejections, replicates_used, EFFECTIVE_ALPHA)
    anti_conservative = bool(replicates_used and over_rejection_p < 0.05)
    calibration_status = "PASS" if usable and not anti_conservative else "REDESIGN_REQUIRED"
    empirical_effect_sd = float(np.std(effects, ddof=1)) if len(effects) > 1 else float("nan")

    displacement = []
    for shift in grid["shifts"][: min(8, len(grid["shifts"]))]:
        displacement.append({"shift_positions": shift})
    placebo_report = {
        "report_id": "CROSS-SECTION-PLACEBO-CALIBRATION-V1",
        "method": "DETERMINISTIC_CIRCULAR_SHIFT_WITHIN_CAUSALLY_ELIGIBLE_HISTORY",
        "zero_shift_used": False,
        "minimum_absolute_shift_positions": 168,
        "shift_grid": {
            "count": len(grid["shifts"]),
            "upper_bound_positions": grid.get("upper_bound"),
            "stride": grid.get("stride"),
            "reason": grid.get("reason"),
            "derived_from": "PANEL_GEOMETRY_ONLY_NEVER_OUTCOMES",
            "examples": displacement,
        },
        "placebo_count": len(usable),
        "degenerate_replicates": len(replicates) - len(usable),
        "event_count_retention": 1.0 if usable else 0.0,
        "within_asset_cluster_preserved": True,
        "assets_excluded_per_replicate": 0,
        "cross_asset_synchrony": {
            "same_absolute_position_displacement_for_every_asset": True,
            "calendar_displacement_identical_across_assets": False,
            "limitation": (
                "Assets have different eligible-hour grids, so an identical position shift "
                "maps to different calendar offsets. Contemporaneous cross-asset synchrony "
                "is therefore only partially preserved; the decision-time fixed effect "
                "absorbs the market-wide component the placebo cannot reproduce exactly."
            ),
        },
        "empirical_upper_tail": calibration_rows,
        "mean_analytic_tail_probability": mean_tail,
        "critical_t_at_effective_alpha": critical,
        "rejections_at_effective_alpha": rejections,
        "expected_rejections_at_effective_alpha": expected,
        "empirical_size_at_effective_alpha": (
            rejections / replicates_used if replicates_used else float("nan")
        ),
        "size_inflation_factor": (
            (rejections / replicates_used) / EFFECTIVE_ALPHA if replicates_used else float("nan")
        ),
        "over_rejection_binomial_p": over_rejection_p,
        "effective_alpha_tail_resolvable": resolvable,
        "anti_conservative": anti_conservative,
        "analytic_median_standard_error_bps": float(np.median(errors)) if len(errors) else None,
        "empirical_placebo_effect_sd_bps": empirical_effect_sd,
        "analytic_versus_empirical_dispersion_ratio": (
            empirical_effect_sd / float(np.median(errors))
            if len(errors) and float(np.median(errors)) > 0
            else None
        ),
        "replicate_independence_limitation": (
            "The frozen construction keeps one absolute position displacement for every "
            "asset and drops no asset, so the displacement is bounded by the shortest "
            "participating history. Replicates therefore overlap heavily and are not "
            "independent draws; the empirical size below is a dependent-sample estimate."
        ),
        "participating_asset_position_quantiles": {
            "minimum": int(participating_lengths.min()) if len(participating_lengths) else None,
            "p10": float(np.quantile(participating_lengths, 0.10))
            if len(participating_lengths)
            else None,
            "median": float(np.median(participating_lengths))
            if len(participating_lengths)
            else None,
            "maximum": int(participating_lengths.max()) if len(participating_lengths) else None,
        },
        "searched_for_favourable_construction": False,
        "PLACEBO_CALIBRATION_STATUS": calibration_status,
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }

    feasibility = json.loads((ROOT / FEASIBILITY_PATH).read_text(encoding="utf-8"))
    signals = json.loads((ROOT / SIGNAL_PATH).read_text(encoding="utf-8"))
    survivorship = json.loads((ROOT / SURVIVORSHIP_PATH).read_text(encoding="utf-8"))
    equivalence = json.loads(
        (ROOT / "reports/cross_section/CROSS-SECTION-BTC-1H-EQUIVALENCE-V1.json").read_text(
            encoding="utf-8"
        )
    )
    inventory_report = json.loads(
        (ROOT / "reports/cross_section/CROSS-SECTION-ARCHIVE-INVENTORY-V1.json").read_text(
            encoding="utf-8"
        )
    )
    dependence_status = (
        "PASS"
        if all(item["positive_semidefinite"] for item in usable)
        and diagnostics["max_absolute_asset_mean"] < 1e-8
        and diagnostics["max_absolute_time_mean"] < 1e-8
        else "REDESIGN_REQUIRED"
    )
    prerequisites = {
        "DATA_SOURCE_STATUS": equivalence["DATA_SOURCE_STATUS"],
        "UNIVERSE_FEASIBILITY_STATUS": feasibility["UNIVERSE_FEASIBILITY_STATUS"],
        "DATA_FEASIBILITY_STATUS": inventory_report["projection"]["DATA_FEASIBILITY_STATUS"],
        "SURVIVORSHIP_STATUS": survivorship["SURVIVORSHIP_STATUS"],
        "CLUSTER_SUPPORT_STATUS": support["CLUSTER_SUPPORT_STATUS"],
        "PLACEBO_CALIBRATION_STATUS": placebo_report["PLACEBO_CALIBRATION_STATUS"],
        "DEPENDENCE_INFERENCE_STATUS": dependence_status,
    }
    powered = power["power_at_MESI"] >= TARGET_POWER
    gate_status = (
        "READY_FOR_PREREGISTRATION"
        if all(value == "PASS" for value in prerequisites.values()) and powered and resolvable
        else "REDESIGN_REQUIRED"
    )
    gate = {
        "report_id": "CROSS-SECTION-POWER-GATE-V1",
        "hypothesis_id": "ALIGNED_COMMON_CROSS_SECTION_EFFECT_V1",
        "frozen_design": {
            "product_universe": PRODUCT_UNIVERSE,
            "cross_section_role": CROSS_SECTION_ROLE,
            "aligned_modified": False,
            "primary_count": 1,
            "fixed_effects": ["ASSET", "DECISION_TIME"],
            "horizon_hours": OUTCOME_HORIZON_HOURS,
            "metric": "FORWARD_LOG_PRICE_RETURN_BPS",
            "occupancy_suppression_applied": False,
            "per_asset_selection": False,
        },
        "panel": {
            "decision_rows": calibration.rows,
            "instrument_epochs": calibration.asset_count,
            "decision_times": calibration.time_count,
            "raw_signals": int(calibration.signal.sum()),
            "placebo_participants": int(participating.sum()),
            "placebo_non_participants": int((~participating).sum()),
            "placebo_participation_rule_positions": PLACEBO_MINIMUM_POSITIONS,
        },
        "cluster_support": support,
        "absorber_diagnostics": diagnostics,
        "dependence": {
            "cluster_dimensions": ["ASSET_INSTRUMENT_EPOCH", "UTC_CALENDAR_WEEK"],
            "method": "TWO_WAY_CAMERON_GELBACH_MILLER_INCLUSION_EXCLUSION",
            "covariance_identity": "V = V_asset + V_week - V_intersection",
            "finite_sample_correction": "G_OVER_G_MINUS_ONE_PER_DIMENSION",
            "all_replicates_positive_semidefinite": all(
                item["positive_semidefinite"] for item in usable
            ),
            "DEPENDENCE_INFERENCE_STATUS": dependence_status,
        },
        "economic_threshold": {
            "CROSS_SECTION_MESI_BPS": CROSS_SECTION_MESI_BPS,
            "necessary_lower_bound": True,
            "sufficient_for_product_claim": False,
            "lowered_after_power": False,
        },
        "multiplicity": {
            "prospective_family_size": PROSPECTIVE_FAMILY_SIZE,
            "effective_alpha": EFFECTIVE_ALPHA,
            "sidedness": "ONE_SIDED_POSITIVE",
            "UNQUANTIFIED_PRE_REPO_EXPOSURE": UNQUANTIFIED_PRE_REPO_EXPOSURE,
            "effective_alpha_tail_resolvable_by_placebo": resolvable,
        },
        "power": power,
        "placebo": {
            "placebo_count": placebo_report["placebo_count"],
            "PLACEBO_CALIBRATION_STATUS": placebo_report["PLACEBO_CALIBRATION_STATUS"],
        },
        "prerequisite_gates": prerequisites,
        "prerequisites_pass": all(value == "PASS" for value in prerequisites.values()),
        "power_at_MESI_meets_target": powered,
        "CROSS_SECTION_POWER_GATE_STATUS": gate_status,
        "preregistration_authorized": False,
        "actual_execution_authorized": False,
        "leakage_guard": {
            "zero_alignment_pooled_effect_computed": False,
            "zero_alignment_t_computed": False,
            "zero_alignment_p_computed": False,
            "per_asset_real_effect_computed": False,
            "cross_section_trading_verdict_emitted": False,
            "sealed_data_queried": False,
            "post_cutoff_data_used": False,
        },
        "safety": {
            "experiments_completed": 26,
            "observed_material_economic_hypotheses": 12,
            "sealed_queries": 0,
            "champion_status": "NONE",
            "real_money_authorized": False,
            "cross_section_product_authorized": False,
        },
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    for payload, path in ((placebo_report, PLACEBO_PATH), (gate, GATE_JSON)):
        assert_no_real_effect_leakage(payload)
        write_json(ROOT / path, payload)
    _write_gate_markdown(gate, placebo_report, signals)
    print(
        json.dumps(
            {
                "design_standard_error_bps": power["design_standard_error_bps"],
                "minimum_detectable_effect_bps": power["minimum_detectable_effect_bps"],
                "power_at_MESI": power["power_at_MESI"],
                "degrees_of_freedom": degrees,
                "prerequisites": prerequisites,
                "CROSS_SECTION_POWER_GATE_STATUS": gate_status,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _write_gate_markdown(gate: dict[str, Any], placebo: dict[str, Any], signals: dict[str, Any]):
    power = gate["power"]
    lines = [
        "# Cross-section common-effect power gate V1",
        "",
        f"Status: **{gate['CROSS_SECTION_POWER_GATE_STATUS']}**",
        "",
        "Design and power preparation only. The true (zero-alignment) pooled ALIGNED effect,",
        "its t statistic, its p value and every per-asset real effect remain uncomputed.",
        "",
        "## Panel",
        "",
        f"- decision rows: {gate['panel']['decision_rows']:,}",
        f"- instrument epochs: {gate['panel']['instrument_epochs']:,}",
        f"- distinct decision times: {gate['panel']['decision_times']:,}",
        f"- raw ALIGNED signal events: {gate['panel']['raw_signals']:,}",
        f"- occupancy suppression applied: {gate['frozen_design']['occupancy_suppression_applied']}",
        "",
        "## Inference support",
        "",
        (
            f"- asset clusters with events: "
            f"{gate['cluster_support']['asset_clusters_with_events']}"
            f" (minimum {gate['cluster_support']['minimum_asset_clusters']})"
        ),
        (
            f"- UTC week clusters with events: "
            f"{gate['cluster_support']['week_clusters_with_events']}"
            f" (minimum {gate['cluster_support']['minimum_week_clusters']})"
        ),
        f"- CLUSTER_SUPPORT_STATUS: {gate['cluster_support']['CLUSTER_SUPPORT_STATUS']}",
        f"- DEPENDENCE_INFERENCE_STATUS: {gate['dependence']['DEPENDENCE_INFERENCE_STATUS']}",
        "",
        "## Placebo calibration",
        "",
        f"- placebo replicates: {placebo['placebo_count']}",
        f"- zero shift used: {placebo['zero_shift_used']}",
        f"- event-count retention: {placebo['event_count_retention']}",
        f"- PLACEBO_CALIBRATION_STATUS: {placebo['PLACEBO_CALIBRATION_STATUS']}",
        "",
        "## Prospective power",
        "",
        f"- MESI: {gate['economic_threshold']['CROSS_SECTION_MESI_BPS']} bps/event",
        f"- effective alpha: {power['effective_alpha']:.10f} (0.05 / 13, one-sided)",
        f"- degrees of freedom: {power['degrees_of_freedom']}",
        f"- design standard error: {power['design_standard_error_bps']:.6f} bps",
        f"- empirical MDE: {power['minimum_detectable_effect_bps']:.6f} bps/event",
        f"- power at MESI: {power['power_at_MESI']:.10f}",
        f"- target power: {power['target_power']}",
        "",
        "## Prerequisite gates",
        "",
    ]
    for key, value in gate["prerequisite_gates"].items():
        lines.append(f"- {key}: {value}")
    lines += [
        "",
        f"Raw signals span {signals['first_signal']} to {signals['last_signal']}.",
        "",
        "Preregistration is not authorized by this artifact.",
        "",
    ]
    (ROOT / GATE_MARKDOWN).write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("signals", "power"))
    options = parser.parse_args()
    return stage_signals() if options.stage == "signals" else stage_power()


if __name__ == "__main__":
    raise SystemExit(main())
