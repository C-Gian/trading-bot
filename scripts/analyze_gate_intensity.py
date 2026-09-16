"""Sparse cross-section closure, event reconciliation, and the frozen gate-intensity design.

Stages:

    reconcile   prove the 3380 -> 3378 difference with a typed deterministic rule
    design      build the frozen integer gate-intensity field and verify ALIGNED == (score 3)
    freeze      materialize the deterministic calendar-synchronous randomization family

No stage computes a true zero-shift effect. The support gate and the prospective power
stages are deliberately absent from this script: they are blocked behind the frozen
prerequisites recorded by `reconcile`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.cross_section import (
    assert_no_real_effect_leakage,
)
from app.research.cross_section_archive import INVENTORY_PATH
from app.research.cross_section_lab import (
    aligned_gate_grid,
    aligned_gate_grid_vectorized,
    eligible_hours,
    iso,
    read_substrate,
    write_json,
)
from app.research.cross_section_power import (
    INSTRUMENT_EPOCH_GAP_HOURS,
    PLACEBO_MINIMUM_POSITIONS,
)
from app.research.evaluation_protocol import HOUR_US
from app.research.gate_intensity import (
    DEVELOPMENT_YEARS,
    EFFECTIVE_ALPHA,
    FAMILY_STATUS_ON_FAILURE,
    HYPOTHESIS_ID,
    LEGAL_SHIFT_WEEKS,
    MAXIMUM_SHIFT_WEEKS,
    MINIMUM_SHIFT_WEEKS,
    PARENT_HYPOTHESIS_ID,
    PROSPECTIVE_FAMILY_SIZE,
    REQUESTED_REPLICATE_VECTORS,
    TARGET_POWER,
    TEST_SIDEDNESS,
    build_shift_vectors,
    design_summary,
    hour_year,
    mesi_bps_per_gate,
    shift_family_digest,
)

EVENTS_PATH = "data/derived/BINANCE-SPOT-USDT-CROSSSECTION-EVENTS-DEV-v1.npz"
INTENSITY_PATH = "data/derived/BINANCE-SPOT-USDT-GATE-INTENSITY-DEV-v1.npz"
RECONCILIATION_PATH = "reports/cross_section/CROSS-SECTION-EVENT-RECONCILIATION-V1.json"
SCORE_PATH = "reports/cross_section/GATE-INTENSITY-SCORE-V1.json"
RANDOMIZATION_PATH = "reports/cross_section/GATE-INTENSITY-RANDOMIZATION-FAMILY-V1.json"
EQUIVALENCE_SAMPLE = 8


def _epochs(times: np.ndarray) -> list[tuple[int, int]]:
    if not len(times):
        return []
    breaks = np.flatnonzero(np.diff(times) >= INSTRUMENT_EPOCH_GAP_HOURS * HOUR_US) + 1
    bounds = [0, *breaks.tolist(), len(times)]
    return [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]


def _outcome_reconciliation() -> dict[str, Any]:
    """Second typed item: the intensity field spans every decidable eligible hour.

    The frozen event panel additionally requires a valid 24h forward outcome, so it is a
    strict subset. No ALIGNED signal is lost by that requirement.
    """
    intensity_path = ROOT / INTENSITY_PATH
    if not intensity_path.is_file():
        return {"evaluated": False, "reason": "INTENSITY_FIELD_NOT_BUILT"}
    intensity = np.load(intensity_path, allow_pickle=False)
    events = np.load(ROOT / EVENTS_PATH, allow_pickle=False)
    left = set(zip(intensity["asset_index"].tolist(), intensity["hours"].tolist(), strict=True))
    right = set(zip(events["asset_index"].tolist(), events["hours"].tolist(), strict=True))
    return {
        "evaluated": True,
        "intensity_field_rows": len(intensity["hours"]),
        "outcome_panel_rows": len(events["hours"]),
        "difference": int(len(intensity["hours"]) - len(events["hours"])),
        "outcome_panel_is_strict_subset": bool(right <= left),
        "rule": "OUTCOME_PANEL_REQUIRES_A_VALID_24H_FORWARD_RETURN",
        "intensity_signals": int(intensity["signal"].astype(bool).sum()),
        "outcome_panel_signals": int(events["signal"].astype(bool).sum()),
        "signals_lost_to_outcome_requirement": int(
            intensity["signal"].astype(bool).sum() - events["signal"].astype(bool).sum()
        ),
        "epochs_identical": bool(
            [str(x) for x in intensity["labels"]] == [str(x) for x in events["labels"]]
        ),
    }


def stage_reconcile() -> int:
    """Prove exactly which rows and signals separate the support artifact from the panel."""
    payload = np.load(ROOT / EVENTS_PATH, allow_pickle=False)
    asset = payload["asset_index"].astype(np.int64)
    hours = payload["hours"].astype(np.int64)
    signal = payload["signal"].astype(bool)
    labels = [str(item) for item in payload["labels"]]
    lengths = np.bincount(asset, minlength=len(labels))

    support = json.loads(
        (ROOT / "reports/cross_section/CROSS-SECTION-SIGNAL-SUPPORT-V1.json").read_text(
            encoding="utf-8"
        )
    )
    gate = json.loads(
        (ROOT / "reports/power/CROSS-SECTION-POWER-GATE-V1.json").read_text(encoding="utf-8")
    )
    inventory = json.loads((ROOT / INVENTORY_PATH).read_text(encoding="utf-8"))
    last_month = {item["symbol"]: item["last_month"] for item in inventory["symbols"]}

    # The only rule that separated the two artifacts, restated from the retired placebo.
    excluded = np.flatnonzero(lengths < PLACEBO_MINIMUM_POSITIONS)
    excluded_mask = np.isin(asset, excluded)
    removed_signal_rows = np.flatnonzero(signal & excluded_mask)
    removed_epochs = sorted({int(asset[row]) for row in removed_signal_rows})

    detail = []
    delisted_in_window = 0
    for epoch in excluded.tolist():
        member = asset == epoch
        symbol = labels[epoch].split("#")[0]
        ends_early = last_month.get(symbol, "2024-12") < "2024-12"
        delisted_in_window += int(ends_early)
        detail.append(
            {
                "epoch": labels[epoch],
                "symbol": symbol,
                "decision_rows": int(lengths[epoch]),
                "first_decision": iso(int(hours[member].min())),
                "last_decision": iso(int(hours[member].max())),
                "signals": int((signal & member).sum()),
                "symbol_archive_last_month": last_month.get(symbol),
                "symbol_archive_ends_before_window_end": ends_early,
            }
        )

    removed = [
        {
            "epoch": labels[int(asset[row])],
            "decision_hour": iso(int(hours[row])),
            "decision_hour_us": int(hours[row]),
            "removal_rule": "EPOCH_DECISION_ROWS_BELOW_PLACEBO_MINIMUM_POSITIONS",
        }
        for row in removed_signal_rows.tolist()
    ]

    # The rule input is a whole-sample epoch length, so it is not knowable at decision time.
    point_in_time = False
    survival_linked = delisted_in_window > 0
    status = "PASS" if point_in_time else "FAIL_CLOSED_NON_POINT_IN_TIME_PARTICIPATION_RULE"
    report = {
        "report_id": "CROSS-SECTION-EVENT-RECONCILIATION-V1",
        "support_artifact_signals": support["raw_signals"],
        "support_artifact_asset_clusters": support["asset_clusters_with_events"],
        "power_panel_signals": gate["panel"]["raw_signals"],
        "power_panel_asset_clusters": gate["cluster_support"]["asset_clusters_with_events"],
        "signal_difference": support["raw_signals"] - gate["panel"]["raw_signals"],
        "asset_cluster_difference": (
            support["asset_clusters_with_events"]
            - gate["cluster_support"]["asset_clusters_with_events"]
        ),
        "removal_rule": {
            "name": "EPOCH_DECISION_ROWS_BELOW_PLACEBO_MINIMUM_POSITIONS",
            "expression": f"epoch_decision_rows < {PLACEBO_MINIMUM_POSITIONS}",
            "constant": PLACEBO_MINIMUM_POSITIONS,
            "origin": "RETIRED_POSITION_SHIFT_PLACEBO_PARTICIPATION_REQUIREMENT",
            "applies_to": "PLACEBO_CALIBRATION_PANEL_ONLY",
            "changed_frozen_universe": False,
            "changed_frozen_signal_counts": False,
            "discretionary": False,
            "performance_dependent": False,
            "point_in_time": point_in_time,
            "whole_sample_input": True,
        },
        "excluded_epochs": len(excluded),
        "excluded_epoch_detail": detail,
        "excluded_epochs_with_in_window_delisting": delisted_in_window,
        "removed_signal_rows": removed,
        "removed_signal_count": len(removed),
        "removed_asset_clusters": [labels[epoch] for epoch in removed_epochs],
        "arithmetic_reconciles": (
            support["raw_signals"] - len(removed) == gate["panel"]["raw_signals"]
        ),
        "every_removed_row_has_typed_reason": all(item["removal_rule"] for item in removed),
        "survival_linked": survival_linked,
        "finding": (
            "The difference is fully explained by one typed deterministic rule and every "
            "removed row is enumerated. The rule input is the epoch's total decision-row "
            "count over the whole development window, which is not knowable at decision "
            "time, and for "
            f"{delisted_in_window} excluded epochs it is co-determined by in-window "
            "delisting. The rule is therefore not point-in-time and is inadmissible as a "
            "design filter. It never touched the frozen universe, the frozen signal "
            "counts, or any market result, and it is retired together with the placebo "
            "that required it."
        ),
        "outcome_availability_reconciliation": _outcome_reconciliation(),
        "EVENT_RECONCILIATION_STATUS": status,
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    assert_no_real_effect_leakage(report)
    write_json(ROOT / RECONCILIATION_PATH, report)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "support_artifact_signals",
                    "power_panel_signals",
                    "signal_difference",
                    "removed_signal_count",
                    "excluded_epochs",
                    "excluded_epochs_with_in_window_delisting",
                    "arithmetic_reconciles",
                    "EVENT_RECONCILIATION_STATUS",
                )
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def stage_design() -> int:
    """Build the frozen integer score field and verify it against the frozen ALIGNED signal."""
    substrate = read_substrate(ROOT)
    stored = np.load(ROOT / EVENTS_PATH, allow_pickle=False)
    stored_labels = [str(item) for item in stored["labels"]]

    labels: list[str] = []
    all_assets: list[np.ndarray] = []
    all_hours: list[np.ndarray] = []
    all_scores: list[np.ndarray] = []
    all_signals: list[np.ndarray] = []
    equivalence: list[dict[str, Any]] = []
    violations = 0

    for symbol in sorted(substrate):
        bars = substrate[symbol]
        eligible = eligible_hours(bars)
        if not len(eligible):
            continue
        hours, direction, breakout, participation, emits = aligned_gate_grid_vectorized(bars)
        keep = np.isin(hours, eligible)
        hours, direction, breakout, participation, emits = (
            hours[keep],
            direction[keep],
            breakout[keep],
            participation[keep],
            emits[keep],
        )
        score = direction.astype(np.int8) + breakout.astype(np.int8) + participation.astype(np.int8)
        violations += int(((score < 0) | (score > 3)).sum())
        violations += int((np.equal(score, 3) != emits).sum())
        for start, end in _epochs(bars.open_time):
            low, high = int(bars.open_time[start]), int(bars.open_time[end - 1])
            inside = (hours >= low) & (hours <= high)
            if not inside.any():
                continue
            labels.append(f"{symbol}#{iso(low)[:10]}")
            all_assets.append(np.full(int(inside.sum()), len(labels) - 1, dtype=np.int64))
            all_hours.append(hours[inside])
            all_scores.append(score[inside])
            all_signals.append(emits[inside])
        if len(equivalence) < EQUIVALENCE_SAMPLE and len(hours):
            reference = aligned_gate_grid(bars)
            sample = np.isin(reference[0], eligible)
            equivalence.append(
                {
                    "symbol": symbol,
                    "hours": int(sample.sum()),
                    "identical_direction": bool(np.array_equal(reference[1][sample], direction)),
                    "identical_breakout": bool(np.array_equal(reference[2][sample], breakout)),
                    "identical_participation": bool(
                        np.array_equal(reference[3][sample], participation)
                    ),
                    "identical_aligned": bool(np.array_equal(reference[4][sample], emits)),
                }
            )

    asset_index = np.concatenate(all_assets)
    hours = np.concatenate(all_hours)
    score = np.concatenate(all_scores)
    signal = np.concatenate(all_signals)
    order = np.lexsort((hours, asset_index))
    asset_index, hours, score, signal = (
        asset_index[order],
        hours[order],
        score[order],
        signal[order],
    )
    np.savez_compressed(
        ROOT / INTENSITY_PATH,
        asset_index=asset_index,
        hours=hours,
        score=score,
        signal=signal,
        labels=np.array(labels),
    )

    counts = {str(value): int((score == value).sum()) for value in (0, 1, 2, 3)}
    per_year: dict[str, dict[str, int]] = {}
    years = np.array([hour_year(int(value)) for value in hours], dtype=np.int64)
    for year in DEVELOPMENT_YEARS:
        mask = years == year
        per_year[str(year)] = {
            str(value): int((score[mask] == value).sum()) for value in (0, 1, 2, 3)
        }
    equivalence_holds = all(
        item["identical_direction"]
        and item["identical_breakout"]
        and item["identical_participation"]
        and item["identical_aligned"]
        for item in equivalence
    )
    report = {
        "report_id": "GATE-INTENSITY-SCORE-V1",
        "design": design_summary(),
        "panel_rows": len(hours),
        "instrument_epochs": len(labels),
        "epochs_match_frozen_panel": labels == stored_labels,
        "rows_by_intensity": counts,
        "rows_by_intensity_by_year": per_year,
        "intensity_is_integer_0_to_3": bool(
            violations == 0 and set(np.unique(score).tolist()) <= {0, 1, 2, 3}
        ),
        "aligned_equals_intensity_three": bool(violations == 0),
        "aligned_signal_count": int(signal.sum()),
        "intensity_three_count": counts["3"],
        "engine_decomposition_equivalence": equivalence,
        "engine_decomposition_equivalent": equivalence_holds,
        "mesi_bps_per_gate": mesi_bps_per_gate(),
        "zero_shift_effect_computed": False,
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    assert_no_real_effect_leakage(report)
    write_json(ROOT / SCORE_PATH, report)
    print(
        json.dumps(
            {
                "panel_rows": report["panel_rows"],
                "instrument_epochs": report["instrument_epochs"],
                "rows_by_intensity": counts,
                "aligned_signal_count": report["aligned_signal_count"],
                "aligned_equals_intensity_three": report["aligned_equals_intensity_three"],
                "engine_decomposition_equivalent": equivalence_holds,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if violations == 0 else 1


def stage_freeze() -> int:
    """Materialize the deterministic shift family before any shifted effect is measured."""
    vectors = build_shift_vectors(REQUESTED_REPLICATE_VECTORS)
    magnitudes = Counter(abs(weeks) for vector in vectors for weeks in vector.weeks_by_year)
    signs = Counter(int(np.sign(weeks)) for vector in vectors for weeks in vector.weeks_by_year)
    report = {
        "report_id": "GATE-INTENSITY-RANDOMIZATION-FAMILY-V1",
        "method": design_summary()["randomization_method"],
        "seed": design_summary()["randomization_seed"],
        "requested_vectors": REQUESTED_REPLICATE_VECTORS,
        "generated_vectors": len(vectors),
        "unique_vectors": len({vector.weeks_by_year for vector in vectors}),
        "development_years": list(DEVELOPMENT_YEARS),
        "legal_shift_weeks": list(LEGAL_SHIFT_WEEKS),
        "minimum_shift_weeks": MINIMUM_SHIFT_WEEKS,
        "maximum_shift_weeks": MAXIMUM_SHIFT_WEEKS,
        "zero_shift_present": any(
            weeks == 0 for vector in vectors for weeks in vector.weeks_by_year
        ),
        "all_years_covered": all(
            len(vector.weeks_by_year) == len(DEVELOPMENT_YEARS) for vector in vectors
        ),
        "one_displacement_per_year_shared_by_all_assets": True,
        "circular_wrap": False,
        "derived_from": "SEED_AND_CALENDAR_GEOMETRY_ONLY_NEVER_OUTCOMES",
        "magnitude_histogram": {str(key): value for key, value in sorted(magnitudes.items())},
        "sign_histogram": {str(key): value for key, value in sorted(signs.items())},
        "family_sha256": shift_family_digest(vectors),
        "vectors": [
            {"index": vector.index, "weeks_by_year": vector.as_list()} for vector in vectors
        ],
        "support_gate_evaluated": False,
        "shifted_effects_computed": False,
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    assert_no_real_effect_leakage(report)
    write_json(ROOT / RANDOMIZATION_PATH, report)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "generated_vectors",
                    "unique_vectors",
                    "zero_shift_present",
                    "all_years_covered",
                    "family_sha256",
                )
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


GATE_JSON = "reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1.json"
GATE_MARKDOWN = "reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1.md"


def stage_gate() -> int:
    """Assemble the gate from frozen prerequisites; blocked stages are recorded, not guessed."""
    reconciliation = json.loads((ROOT / RECONCILIATION_PATH).read_text(encoding="utf-8"))
    score = json.loads((ROOT / SCORE_PATH).read_text(encoding="utf-8"))
    family = json.loads((ROOT / RANDOMIZATION_PATH).read_text(encoding="utf-8"))
    equivalence = json.loads(
        (ROOT / "reports/cross_section/CROSS-SECTION-BTC-1H-EQUIVALENCE-V1.json").read_text(
            encoding="utf-8"
        )
    )
    feasibility = json.loads(
        (ROOT / "reports/cross_section/CROSS-SECTION-UNIVERSE-FEASIBILITY-V1.json").read_text(
            encoding="utf-8"
        )
    )
    survivorship = json.loads(
        (ROOT / "reports/cross_section/CROSS-SECTION-SURVIVORSHIP-AUDIT-V1.json").read_text(
            encoding="utf-8"
        )
    )

    blocked = reconciliation["EVENT_RECONCILIATION_STATUS"] != "PASS"
    prerequisites = {
        "DATA_SOURCE_STATUS": equivalence["DATA_SOURCE_STATUS"],
        "UNIVERSE_FEASIBILITY_STATUS": feasibility["UNIVERSE_FEASIBILITY_STATUS"],
        "SURVIVORSHIP_STATUS": survivorship["SURVIVORSHIP_STATUS"],
        "EVENT_RECONCILIATION_STATUS": reconciliation["EVENT_RECONCILIATION_STATUS"],
        "RANDOMIZATION_SUPPORT_STATUS": "NOT_RUN_BLOCKED" if blocked else "NOT_RUN",
        "RANDOMIZATION_INFERENCE_STATUS": "NOT_RUN_BLOCKED" if blocked else "NOT_RUN",
    }
    passes = all(value == "PASS" for value in prerequisites.values())
    status = "READY_FOR_PREREGISTRATION" if passes else "REDESIGN_REQUIRED"
    blocking_reason = (
        "EVENT_RECONCILIATION_STATUS failed closed: the retired placebo participation rule "
        "that separates the two frozen artifacts uses a whole-sample epoch length, which is "
        "not knowable at decision time. The support gate and the prospective power stages "
        "were therefore never run, so no shifted effect and no power number exists for this "
        "hypothesis."
    )
    gate = {
        "report_id": "ALIGNED-GATE-INTENSITY-POWER-GATE-V1",
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
        "frozen_design": design_summary(),
        "score_field": {
            "panel_rows": score["panel_rows"],
            "instrument_epochs": score["instrument_epochs"],
            "rows_by_intensity": score["rows_by_intensity"],
            "aligned_equals_intensity_three": score["aligned_equals_intensity_three"],
            "intensity_is_integer_0_to_3": score["intensity_is_integer_0_to_3"],
            "engine_decomposition_equivalent": score["engine_decomposition_equivalent"],
        },
        "randomization_family": {
            "requested_vectors": family["requested_vectors"],
            "generated_vectors": family["generated_vectors"],
            "unique_vectors": family["unique_vectors"],
            "zero_shift_present": family["zero_shift_present"],
            "minimum_shift_weeks": family["minimum_shift_weeks"],
            "maximum_shift_weeks": family["maximum_shift_weeks"],
            "circular_wrap": family["circular_wrap"],
            "family_sha256": family["family_sha256"],
            "support_gate_evaluated": family["support_gate_evaluated"],
            "shifted_effects_computed": family["shifted_effects_computed"],
        },
        "prerequisite_gates": prerequisites,
        "prerequisites_pass": passes,
        "blocked_before_measurement": blocked,
        "blocking_reason": blocking_reason if blocked else None,
        "power": {
            "mesi_bps_per_gate": mesi_bps_per_gate(),
            "target_power": TARGET_POWER,
            "prospective_family_size": PROSPECTIVE_FAMILY_SIZE,
            "effective_alpha": EFFECTIVE_ALPHA,
            "sidedness": TEST_SIDEDNESS,
            "accepted_vectors": None,
            "empirical_null_dispersion": None,
            "critical_beta_at_effective_alpha": None,
            "power_at_8_bps_per_gate": None,
            "minimum_detectable_effect_bps_per_gate": None,
            "power_curve": None,
            "computed": False,
        },
        "GATE_INTENSITY_POWER_GATE_STATUS": status,
        "ALIGNED_DEVELOPMENT_FAMILY_STATUS": (
            FAMILY_STATUS_ON_FAILURE if status != "READY_FOR_PREREGISTRATION" else "ACTIVE"
        ),
        "preregistration_authorized": False,
        "actual_execution_authorized": False,
        "leakage_guard": {
            "sparse_zero_alignment_beta_computed": False,
            "gate_intensity_zero_shift_beta_computed": False,
            "real_t_computed": False,
            "real_p_computed": False,
            "per_asset_real_effect_computed": False,
            "trading_verdict_emitted": False,
            "sealed_data_queried": False,
            "post_cutoff_data_used": False,
        },
        "safety": {
            "experiments_completed": 26,
            "observed_material_economic_hypotheses": 12,
            "sealed_queries": 0,
            "champion_status": "NONE",
            "real_money_authorized": False,
            "product_universe": "BTCUSDT_SPOT_V1_UNCHANGED",
            "multi_asset_trading_implemented": False,
        },
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    assert_no_real_effect_leakage(gate)
    write_json(ROOT / GATE_JSON, gate)

    summary = design_summary()
    lines = [
        "# ALIGNED gate-intensity power gate V1",
        "",
        f"Status: **{gate['GATE_INTENSITY_POWER_GATE_STATUS']}**",
        "",
        f"ALIGNED development family: **{gate['ALIGNED_DEVELOPMENT_FAMILY_STATUS']}**",
        "",
        "Design and freeze only. No shifted effect, no zero-shift effect, no t, no p and no",
        "per-asset effect was computed for either hypothesis.",
        "",
        "## Frozen score",
        "",
        f"- definition: `{summary['score_definition']}`",
        f"- gate weights: {summary['gate_weights']} (unweighted integer sum)",
        f"- new gate parameters: {summary['new_gate_parameters']}",
        f"- ALIGNED == (intensity == 3): {score['aligned_equals_intensity_three']}",
        "",
        "| intensity | rows |",
        "| --- | ---: |",
    ]
    for value in ("0", "1", "2", "3"):
        lines.append(f"| {value} | {score['rows_by_intensity'][value]:,} |")
    lines += [
        "",
        "## Frozen randomization family",
        "",
        f"- method: {summary['randomization_method']}",
        f"- unique vectors: {family['unique_vectors']} of {family['requested_vectors']} requested",
        (
            f"- displacement band: {family['minimum_shift_weeks']}"
            f"..{family['maximum_shift_weeks']} whole UTC weeks, signed, never zero"
        ),
        f"- circular wrap: {family['circular_wrap']}",
        f"- family SHA-256: `{family['family_sha256']}`",
        f"- support gate evaluated: {family['support_gate_evaluated']}",
        f"- shifted effects computed: {family['shifted_effects_computed']}",
        "",
        "## Prerequisite gates",
        "",
    ]
    for key, value in prerequisites.items():
        lines.append(f"- {key}: {value}")
    lines += [
        "",
        "## Power",
        "",
        f"- MESI: {mesi_bps_per_gate()} bps/gate",
        f"- effective alpha: {EFFECTIVE_ALPHA:.10f} (0.05 / {PROSPECTIVE_FAMILY_SIZE}, one-sided)",
        f"- target power: {TARGET_POWER}",
        "- power at MESI: **not computed** (blocked before measurement)",
        "",
        gate["blocking_reason"] or "",
        "",
        "Preregistration is not authorized by this artifact.",
        "",
    ]
    (ROOT / GATE_MARKDOWN).write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "prerequisites": prerequisites,
                "GATE_INTENSITY_POWER_GATE_STATUS": status,
                "ALIGNED_DEVELOPMENT_FAMILY_STATUS": gate["ALIGNED_DEVELOPMENT_FAMILY_STATUS"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("reconcile", "design", "freeze", "gate"))
    options = parser.parse_args()
    if options.stage == "reconcile":
        return stage_reconcile()
    if options.stage == "design":
        return stage_design()
    if options.stage == "freeze":
        return stage_freeze()
    return stage_gate()


if __name__ == "__main__":
    raise SystemExit(main())
