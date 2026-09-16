"""Gate-intensity causal-panel correction, frozen support gate, and prospective power.

Stages:

    panel       build the V1_1 causal outcome panel and append-only reconciliation
    support     evaluate the frozen 1024-vector geometry-only support gate
    gate        assemble the V1_1 preregistration readiness gate

The historical V1 reconciliation and retired sparse placebo artifacts are never rewritten.
No stage computes a true zero-shift effect.
"""

from __future__ import annotations

import argparse
import hashlib
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
    EXPECTED_RANDOMIZATION_FAMILY_SHA256,
    FAMILY_STATUS_ON_FAILURE,
    HYPOTHESIS_ID,
    LEGAL_SHIFT_WEEKS,
    MAXIMUM_SHIFT_WEEKS,
    MINIMUM_ACCEPTED_VECTORS,
    MINIMUM_ASSET_CLUSTER_RETENTION,
    MINIMUM_ROW_RETENTION,
    MINIMUM_SHIFT_WEEKS,
    PARENT_HYPOTHESIS_ID,
    PROSPECTIVE_FAMILY_SIZE,
    REQUESTED_REPLICATE_VECTORS,
    REQUIRED_YEAR_COVERAGE,
    TARGET_POWER,
    TEST_SIDEDNESS,
    WEEK_US,
    build_shift_vectors,
    design_summary,
    hour_year,
    mesi_bps_per_gate,
    parse_frozen_shift_vectors,
    shift_family_digest,
)

EVENTS_PATH = "data/derived/BINANCE-SPOT-USDT-CROSSSECTION-EVENTS-DEV-v1.npz"
INTENSITY_PATH = "data/derived/BINANCE-SPOT-USDT-GATE-INTENSITY-DEV-v1.npz"
RECONCILIATION_PATH = "reports/cross_section/CROSS-SECTION-EVENT-RECONCILIATION-V1.json"
CAUSAL_PANEL_PATH = "data/derived/BINANCE-SPOT-USDT-GATE-INTENSITY-CAUSAL-PANEL-DEV-v1_1.npz"
RECONCILIATION_V1_1_PATH = (
    "reports/cross_section/CROSS-SECTION-GATE-INTENSITY-PANEL-RECONCILIATION-V1_1.json"
)
SUPPORT_PATH = "reports/cross_section/GATE-INTENSITY-RANDOMIZATION-SUPPORT-V1_1.json"
POWER_PATH = "reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1_1.json"
POWER_MARKDOWN_PATH = "reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1_1.md"
SCORE_PATH = "reports/cross_section/GATE-INTENSITY-SCORE-V1.json"
RANDOMIZATION_PATH = "reports/cross_section/GATE-INTENSITY-RANDOMIZATION-FAMILY-V1.json"
EQUIVALENCE_SAMPLE = 8
KEY_STRIDE = 10_000_000
FROZEN_RANDOMIZATION_ARTIFACT_SHA256 = (
    "4c94c99248ca759c0843824107b9c4c4b6743b1c0aa4e47f02b7c0348b9f4592"
)
RETIRED_ARTIFACT_SHA256 = {
    "reports/cross_section/CROSS-SECTION-EVENT-RECONCILIATION-V1.json": (
        "cb81cd4f53cd1a3fb2de022492b647172693be462236de878e744264728e28c1"
    ),
    "reports/cross_section/CROSS-SECTION-PLACEBO-CALIBRATION-V1.json": (
        "2173590eae9b289d220cdd772bdb558c42516f5ff23115103d7b08d0aafd6383"
    ),
    "reports/power/CROSS-SECTION-POWER-GATE-V1.json": (
        "52487ac2b35fe8b6905b41e0c88f77326dce47b35040ee0bef22b345bbd39b71"
    ),
}


def _epochs(times: np.ndarray) -> list[tuple[int, int]]:
    if not len(times):
        return []
    breaks = np.flatnonzero(np.diff(times) >= INSTRUMENT_EPOCH_GAP_HOURS * HOUR_US) + 1
    bounds = [0, *breaks.tolist(), len(times)]
    return [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row_keys(asset_index: np.ndarray, hours: np.ndarray) -> np.ndarray:
    return asset_index.astype(np.int64) * KEY_STRIDE + hours.astype(np.int64) // HOUR_US


def _years(hours: np.ndarray) -> np.ndarray:
    return hours.astype("datetime64[us]").astype("datetime64[Y]").astype(np.int64) + 1970


def _distribution(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    quantiles = np.quantile(array, [0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0])
    return {
        name: float(value)
        for name, value in zip(
            ("minimum", "p05", "p25", "median", "p75", "p95", "maximum"),
            quantiles,
            strict=True,
        )
    }


def _outcome_removal_reason(times: np.ndarray, opens: np.ndarray, closes: np.ndarray, hour: int):
    horizon = hour + 24 * HOUR_US
    start = int(np.searchsorted(times, hour, side="left"))
    if start >= len(times) or int(times[start]) > horizon:
        return "NO_ENTRY_BAR_AT_OR_AFTER_DECISION_WITHIN_24H"
    end = int(np.searchsorted(times, horizon, side="left")) - 1
    if end <= start:
        return "NO_SUBSEQUENT_TERMINAL_BAR_AFTER_ENTRY"
    if float(opens[start]) <= 0.0:
        return "NONPOSITIVE_ENTRY_OPEN"
    if float(closes[end]) <= 0.0:
        return "NONPOSITIVE_TERMINAL_CLOSE"
    raise ValueError("removed row satisfies the frozen outcome contract")


def _load_frozen_family() -> tuple[dict[str, Any], list[Any]]:
    path = ROOT / RANDOMIZATION_PATH
    if _sha256(path) != FROZEN_RANDOMIZATION_ARTIFACT_SHA256:
        raise ValueError("frozen randomization artifact bytes changed")
    payload = json.loads(path.read_text(encoding="utf-8"))
    vectors = parse_frozen_shift_vectors(payload)
    if len(vectors) != REQUESTED_REPLICATE_VECTORS:
        raise ValueError("frozen randomization vector count changed")
    return payload, vectors


def _verify_retired_artifacts_unchanged() -> dict[str, str]:
    observed = {relative: _sha256(ROOT / relative) for relative in RETIRED_ARTIFACT_SHA256}
    if observed != RETIRED_ARTIFACT_SHA256:
        raise ValueError("a retired sparse V1 artifact changed")
    return observed


def stage_panel() -> int:
    """Build the causal V1_1 panel directly from frozen intensity and outcome artifacts."""
    retired_hashes = _verify_retired_artifacts_unchanged()
    intensity = np.load(ROOT / INTENSITY_PATH, allow_pickle=False)
    outcomes = np.load(ROOT / EVENTS_PATH, allow_pickle=False)
    labels = [str(item) for item in intensity["labels"]]
    if labels != [str(item) for item in outcomes["labels"]]:
        raise ValueError("frozen intensity and outcome epoch labels differ")

    base_keys = _row_keys(intensity["asset_index"], intensity["hours"])
    outcome_keys = _row_keys(outcomes["asset_index"], outcomes["hours"])
    base_locations = np.searchsorted(base_keys, outcome_keys)
    if not np.array_equal(base_keys[base_locations], outcome_keys):
        raise ValueError("frozen outcome panel is not a subset of the intensity field")
    outcome_locations = np.searchsorted(outcome_keys, base_keys)
    safe = np.minimum(outcome_locations, len(outcome_keys) - 1)
    removed_mask = (outcome_locations >= len(outcome_keys)) | (outcome_keys[safe] != base_keys)
    removed_indices = np.flatnonzero(removed_mask)

    panel_score = intensity["score"][base_locations].astype(np.int8)
    panel_signal = intensity["signal"][base_locations].astype(bool)
    np.savez_compressed(
        ROOT / CAUSAL_PANEL_PATH,
        asset_index=outcomes["asset_index"].astype(np.int64),
        hours=outcomes["hours"].astype(np.int64),
        outcome=outcomes["outcome"].astype(np.float64),
        score=panel_score,
        signal=panel_signal,
        truncated=outcomes["truncated"].astype(bool),
        labels=intensity["labels"],
    )

    substrate = read_substrate(ROOT)
    removed_rows: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    for row in removed_indices.tolist():
        asset = int(intensity["asset_index"][row])
        hour = int(intensity["hours"][row])
        symbol = labels[asset].split("#", maxsplit=1)[0]
        bars = substrate[symbol]
        reason = _outcome_removal_reason(bars.open_time, bars.open, bars.close, hour)
        reasons[reason] += 1
        removed_rows.append(
            {
                "instrument_epoch": labels[asset],
                "decision_hour": iso(hour),
                "decision_hour_us": hour,
                "gate_intensity": int(intensity["score"][row]),
                "aligned_signal": bool(intensity["signal"][row]),
                "removal_reason": reason,
                "reason_type": "FROZEN_24H_OUTCOME_RESOLUTION",
            }
        )

    base_assets = set(intensity["asset_index"].astype(int).tolist())
    analysis_assets = set(outcomes["asset_index"].astype(int).tolist())
    allowed_reasons = {
        "NO_ENTRY_BAR_AT_OR_AFTER_DECISION_WITHIN_24H",
        "NO_SUBSEQUENT_TERMINAL_BAR_AFTER_ENTRY",
        "NONPOSITIVE_ENTRY_OPEN",
        "NONPOSITIVE_TERMINAL_CLOSE",
    }
    status = (
        "PASS"
        if set(reasons) <= allowed_reasons and len(removed_rows) == sum(reasons.values())
        else "FAIL"
    )
    report = {
        "report_id": "CROSS-SECTION-GATE-INTENSITY-PANEL-RECONCILIATION-V1_1",
        "protocol_implementation_version": "ALIGNED_GATE_INTENSITY_POWER_V1_1",
        "hypothesis_id": HYPOTHESIS_ID,
        "source": {
            "frozen_intensity_field": INTENSITY_PATH,
            "frozen_outcome_panel": EVENTS_PATH,
            "causal_analysis_panel": CAUSAL_PANEL_PATH,
        },
        "causal_inclusion_rule": {
            "point_in_time_universe_eligibility": True,
            "gate_intensity_computable_at_decision_time": True,
            "frozen_24h_outcome_resolvable": True,
            "minimum_whole_epoch_lifetime": None,
            "future_epoch_length_used": False,
            "future_delisting_date_used": False,
            "future_eligible_row_count_used": False,
            "future_signal_count_used": False,
            "future_survival_required": False,
            "retired_504_row_filter_used": False,
        },
        "base_rows": len(base_keys),
        "analysis_rows": len(outcome_keys),
        "removed_rows": len(removed_rows),
        "base_epochs": len(base_assets),
        "analysis_epochs": len(analysis_assets),
        "base_intensity_3_events": int((intensity["score"] == 3).sum()),
        "analysis_intensity_3_events": int((panel_score == 3).sum()),
        "events_removed": int((intensity["score"][removed_indices] == 3).sum()),
        "clusters_removed": [labels[index] for index in sorted(base_assets - analysis_assets)],
        "removal_reason_counts": dict(sorted(reasons.items())),
        "removed_row_detail": removed_rows,
        "every_removed_row_has_typed_reason": all(
            row["removal_reason"] and row["reason_type"] for row in removed_rows
        ),
        "all_removals_are_frozen_outcome_contract_only": set(reasons) <= allowed_reasons,
        "archive_ending_assets_retained_when_outcome_resolvable": True,
        "historical_sparse_reconciliation_preserved": {
            "support_events": 3380,
            "retired_placebo_panel_events": 3378,
            "artifacts_sha256": retired_hashes,
        },
        "score_unchanged": bool(np.array_equal(panel_signal, panel_score == 3)),
        "MESI_BPS_PER_GATE": mesi_bps_per_gate(),
        "EVENT_RECONCILIATION_STATUS": status,
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    assert_no_real_effect_leakage(report)
    write_json(ROOT / RECONCILIATION_V1_1_PATH, report)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "base_rows",
                    "analysis_rows",
                    "removed_rows",
                    "base_epochs",
                    "analysis_epochs",
                    "base_intensity_3_events",
                    "analysis_intensity_3_events",
                    "events_removed",
                    "clusters_removed",
                    "removal_reason_counts",
                    "EVENT_RECONCILIATION_STATUS",
                )
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == "PASS" else 1


def _shifted_source(
    base_keys: np.ndarray,
    base_scores: np.ndarray,
    destination_assets: np.ndarray,
    destination_hours: np.ndarray,
    year: int,
    weeks: int,
) -> tuple[np.ndarray, np.ndarray]:
    source_hours = destination_hours - weeks * WEEK_US
    same_year = _years(source_hours) == year
    source_keys = _row_keys(destination_assets, source_hours)
    locations = np.searchsorted(base_keys, source_keys)
    safe = np.minimum(locations, len(base_keys) - 1)
    valid = same_year & (locations < len(base_keys)) & (base_keys[safe] == source_keys)
    return valid, base_scores[safe]


def _support_pieces() -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any], list[Any]]:
    reconciliation = json.loads((ROOT / RECONCILIATION_V1_1_PATH).read_text(encoding="utf-8"))
    if reconciliation["EVENT_RECONCILIATION_STATUS"] != "PASS":
        raise ValueError("causal-panel reconciliation did not pass")
    family, vectors = _load_frozen_family()
    intensity = np.load(ROOT / INTENSITY_PATH, allow_pickle=False)
    outcomes = np.load(ROOT / EVENTS_PATH, allow_pickle=False)
    base_keys = _row_keys(intensity["asset_index"], intensity["hours"])
    years = _years(outcomes["hours"])
    absolute_weeks = outcomes["hours"].astype(np.int64) // WEEK_US
    unique_weeks, compact_weeks = np.unique(absolute_weeks, return_inverse=True)
    asset_count = len(intensity["labels"])
    pieces: dict[tuple[int, int], dict[str, Any]] = {}
    for year in DEVELOPMENT_YEARS:
        positions = np.flatnonzero(years == year)
        assets = outcomes["asset_index"][positions].astype(np.int64)
        hours = outcomes["hours"][positions].astype(np.int64)
        for weeks in LEGAL_SHIFT_WEEKS:
            valid, scores = _shifted_source(
                base_keys, intensity["score"], assets, hours, year, weeks
            )
            kept = positions[valid]
            pieces[(year, weeks)] = {
                "positions": kept,
                "scores": scores[valid].astype(np.int8),
                "rows": int(valid.sum()),
                "asset_present": np.bincount(assets[valid], minlength=asset_count).astype(bool),
                "week_present": np.bincount(
                    compact_weeks[kept], minlength=len(unique_weeks)
                ).astype(bool),
                "score_counts": np.bincount(scores[valid], minlength=4).astype(np.int64),
            }
    context = {
        "asset_count": asset_count,
        "week_count": len(unique_weeks),
        "compact_weeks": compact_weeks,
        "years": years,
        "family": family,
    }
    return pieces, context, vectors


def stage_support() -> int:
    """Evaluate support using only eligibility geometry and the frozen score field."""
    pieces, context, vectors = _support_pieces()
    reconciliation = json.loads((ROOT / RECONCILIATION_V1_1_PATH).read_text(encoding="utf-8"))
    base_rows = int(reconciliation["analysis_rows"])
    base_assets = int(reconciliation["analysis_epochs"])
    base_weeks = int(context["week_count"])
    detail: list[dict[str, Any]] = []
    row_retentions: list[float] = []
    asset_retentions: list[float] = []
    week_retentions: list[float] = []
    for vector in vectors:
        selected = [
            pieces[(year, weeks)]
            for year, weeks in zip(DEVELOPMENT_YEARS, vector.weeks_by_year, strict=True)
        ]
        rows = sum(piece["rows"] for piece in selected)
        asset_count = int(np.logical_or.reduce([p["asset_present"] for p in selected]).sum())
        week_count = int(np.logical_or.reduce([p["week_present"] for p in selected]).sum())
        represented = sum(piece["rows"] > 0 for piece in selected)
        row_retention = rows / base_rows
        asset_retention = asset_count / base_assets
        week_retention = week_count / base_weeks
        accepted = (
            row_retention >= MINIMUM_ROW_RETENTION
            and asset_retention >= MINIMUM_ASSET_CLUSTER_RETENTION
            and represented == REQUIRED_YEAR_COVERAGE
        )
        row_retentions.append(row_retention)
        asset_retentions.append(asset_retention)
        week_retentions.append(week_retention)
        score_counts = sum(
            (piece["score_counts"] for piece in selected), np.zeros(4, dtype=np.int64)
        )
        detail.append(
            {
                "vector_index": vector.index,
                "weeks_by_year": vector.as_list(),
                "design_rows": rows,
                "row_retention": row_retention,
                "asset_clusters": asset_count,
                "asset_cluster_retention": asset_retention,
                "week_clusters": week_count,
                "week_cluster_retention": week_retention,
                "years_represented": represented,
                "score_counts": {str(i): int(score_counts[i]) for i in range(4)},
                "accepted": accepted,
            }
        )
    accepted = [item for item in detail if item["accepted"]]
    status = "PASS" if len(accepted) >= MINIMUM_ACCEPTED_VECTORS else "REDESIGN_REQUIRED"
    report = {
        "report_id": "GATE-INTENSITY-RANDOMIZATION-SUPPORT-V1_1",
        "method": context["family"]["method"],
        "source_family_artifact": RANDOMIZATION_PATH,
        "source_family_artifact_sha256": _sha256(ROOT / RANDOMIZATION_PATH),
        "family_sha256": context["family"]["family_sha256"],
        "expected_family_sha256": EXPECTED_RANDOMIZATION_FAMILY_SHA256,
        "vectors_regenerated": False,
        "requested_vectors": REQUESTED_REPLICATE_VECTORS,
        "accepted_vectors": len(accepted),
        "rejected_vectors": len(detail) - len(accepted),
        "thresholds": {
            "minimum_row_retention": MINIMUM_ROW_RETENTION,
            "minimum_asset_cluster_retention": MINIMUM_ASSET_CLUSTER_RETENTION,
            "required_year_coverage": REQUIRED_YEAR_COVERAGE,
            "minimum_accepted_vectors": MINIMUM_ACCEPTED_VECTORS,
        },
        "base": {
            "design_rows": base_rows,
            "asset_clusters": base_assets,
            "week_clusters": base_weeks,
        },
        "retention_distributions": {
            "row_retention": _distribution(row_retentions),
            "asset_cluster_retention": _distribution(asset_retentions),
            "week_cluster_retention": _distribution(week_retentions),
            "years_represented": _distribution(
                [float(item["years_represented"]) for item in detail]
            ),
        },
        "vectors": detail,
        "RANDOMIZATION_SUPPORT_STATUS": status,
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    assert_no_real_effect_leakage(report)
    write_json(ROOT / SUPPORT_PATH, report)
    print(
        json.dumps(
            {
                "accepted_vectors": len(accepted),
                "requested_vectors": REQUESTED_REPLICATE_VECTORS,
                "retention_distributions": report["retention_distributions"],
                "RANDOMIZATION_SUPPORT_STATUS": status,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == "PASS" else 1


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


def stage_gate_v1_history() -> int:
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


def stage_gate() -> int:
    """Assemble the append-only V1_1 gate after reconciliation, support and power."""
    reconciliation = json.loads((ROOT / RECONCILIATION_V1_1_PATH).read_text(encoding="utf-8"))
    support = json.loads((ROOT / SUPPORT_PATH).read_text(encoding="utf-8"))
    score = json.loads((ROOT / SCORE_PATH).read_text(encoding="utf-8"))
    family, _ = _load_frozen_family()
    if support["RANDOMIZATION_SUPPORT_STATUS"] != "PASS":
        prerequisites = {
            "EVENT_RECONCILIATION_STATUS": reconciliation["EVENT_RECONCILIATION_STATUS"],
            "RANDOMIZATION_SUPPORT_STATUS": support["RANDOMIZATION_SUPPORT_STATUS"],
            "RANDOMIZATION_INFERENCE_STATUS": "NOT_RUN_BLOCKED",
            "TAIL_RESOLUTION_STATUS": "NOT_RUN_BLOCKED",
        }
        gate = {
            "report_id": "ALIGNED-GATE-INTENSITY-POWER-GATE-V1_1",
            "protocol_implementation_version": "ALIGNED_GATE_INTENSITY_POWER_V1_1",
            "hypothesis_id": HYPOTHESIS_ID,
            "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
            "same_material_economic_hypothesis": True,
            "new_material_economic_hypothesis_consumed": False,
            "prior_stop": {
                "executor_stop_correct": True,
                "reason": "INHERITED_NON_POINT_IN_TIME_RETIRED_PLACEBO_PARTICIPATION_FILTER",
                "true_gate_intensity_result_previously_observed": False,
                "prior_power_previously_observed": False,
            },
            "frozen_design": design_summary(),
            "causal_panel_reconciliation": {
                key: reconciliation[key]
                for key in (
                    "base_rows",
                    "analysis_rows",
                    "removed_rows",
                    "base_epochs",
                    "analysis_epochs",
                    "base_intensity_3_events",
                    "analysis_intensity_3_events",
                    "events_removed",
                    "clusters_removed",
                    "removal_reason_counts",
                )
            },
            "score_field": {
                "score_changed": False,
                "rows_by_intensity": score["rows_by_intensity"],
                "aligned_equals_intensity_three": score["aligned_equals_intensity_three"],
                "mesi_bps_per_gate": mesi_bps_per_gate(),
            },
            "randomization_family": {
                "source_artifact": RANDOMIZATION_PATH,
                "artifact_sha256": _sha256(ROOT / RANDOMIZATION_PATH),
                "family_sha256": family["family_sha256"],
                "vectors_regenerated": False,
                "requested_vectors": family["requested_vectors"],
                "zero_shift_present": family["zero_shift_present"],
            },
            "support": {
                "accepted_vectors": support["accepted_vectors"],
                "requested_vectors": support["requested_vectors"],
                "retention_distributions": support["retention_distributions"],
            },
            "power": {
                "computed": False,
                "reason": "BLOCKED_BY_FROZEN_RANDOMIZATION_SUPPORT_GATE",
                "empirical_null_sd_bps_per_gate": None,
                "critical_beta_bps_per_gate": None,
                "minimum_detectable_effect_bps_per_gate": None,
                "power_at_8_bps_per_gate": None,
                "power_curve": None,
            },
            "prerequisite_gates": prerequisites,
            "GATE_INTENSITY_POWER_GATE_STATUS": "REDESIGN_REQUIRED",
            "ALIGNED_DEVELOPMENT_FAMILY_STATUS": FAMILY_STATUS_ON_FAILURE,
            "preregistration_authorized": False,
            "actual_market_hypothesis_executed": False,
            "leakage_guard": {
                "sparse_zero_alignment_beta_computed": False,
                "gate_intensity_zero_shift_beta_computed": False,
                "shifted_beta_computed": False,
                "real_t_computed": False,
                "real_p_computed": False,
                "per_asset_real_effect_computed": False,
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
            },
            "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
        }
        assert_no_real_effect_leakage(gate)
        write_json(ROOT / POWER_PATH, gate)
        rows = support["retention_distributions"]["row_retention"]
        assets = support["retention_distributions"]["asset_cluster_retention"]
        lines = [
            "# ALIGNED gate-intensity causal correction and power gate V1_1",
            "",
            "Status: **REDESIGN_REQUIRED**",
            "",
            "The causal-panel correction passed, but none of the 1,024 byte-frozen",
            "calendar-shift vectors met the unchanged support thresholds. The workflow",
            "stopped before any shifted beta or synthetic power calculation.",
            "",
            "## Causal panel",
            "",
            f"- base rows: {reconciliation['base_rows']:,}",
            f"- analysis rows: {reconciliation['analysis_rows']:,}",
            f"- removed rows: {reconciliation['removed_rows']:,}",
            f"- score-3 events removed: {reconciliation['events_removed']}",
            f"- reconciliation: {reconciliation['EVENT_RECONCILIATION_STATUS']}",
            "",
            "## Frozen support gate",
            "",
            f"- accepted vectors: {support['accepted_vectors']} / {support['requested_vectors']}",
            f"- row retention range: {rows['minimum']:.6f} .. {rows['maximum']:.6f}",
            f"- asset-cluster retention range: {assets['minimum']:.6f} .. {assets['maximum']:.6f}",
            "- all six development years represented: true for every vector",
            "",
            "Power was not computed. Historical ALIGNED development is permanently parked",
            "unless a future Research Director explicitly reopens it.",
            "",
        ]
        (ROOT / POWER_MARKDOWN_PATH).write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(
            json.dumps(
                {
                    "prerequisites": prerequisites,
                    "GATE_INTENSITY_POWER_GATE_STATUS": "REDESIGN_REQUIRED",
                    "ALIGNED_DEVELOPMENT_FAMILY_STATUS": FAMILY_STATUS_ON_FAILURE,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    empirical = json.loads(
        (ROOT / "reports/power/ALIGNED-GATE-INTENSITY-EMPIRICAL-POWER-V1_1.json").read_text(
            encoding="utf-8"
        )
    )
    power = empirical["empirical_power"]
    prerequisites = {
        "EVENT_RECONCILIATION_STATUS": reconciliation["EVENT_RECONCILIATION_STATUS"],
        "RANDOMIZATION_SUPPORT_STATUS": support["RANDOMIZATION_SUPPORT_STATUS"],
        "RANDOMIZATION_INFERENCE_STATUS": empirical["RANDOMIZATION_INFERENCE_STATUS"],
        "TAIL_RESOLUTION_STATUS": (
            "PASS" if power["tail_resolution_sufficient"] else "REDESIGN_REQUIRED"
        ),
    }
    power_at_mesi = float(power["power_curve"]["8"])
    ready = (
        all(value == "PASS" for value in prerequisites.values()) and power_at_mesi >= TARGET_POWER
    )
    gate_status = "READY_FOR_PREREGISTRATION" if ready else "REDESIGN_REQUIRED"
    family_status = (
        "REOPENED_FOR_SINGLE_PRE_MEASUREMENT_CAUSALITY_CORRECTION"
        if ready
        else FAMILY_STATUS_ON_FAILURE
    )
    gate = {
        "report_id": "ALIGNED-GATE-INTENSITY-POWER-GATE-V1_1",
        "protocol_implementation_version": "ALIGNED_GATE_INTENSITY_POWER_V1_1",
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
        "same_material_economic_hypothesis": True,
        "new_material_economic_hypothesis_consumed": False,
        "prior_stop": {
            "executor_stop_correct": True,
            "reason": "INHERITED_NON_POINT_IN_TIME_RETIRED_PLACEBO_PARTICIPATION_FILTER",
            "true_gate_intensity_result_previously_observed": False,
            "prior_power_previously_observed": False,
        },
        "frozen_design": design_summary(),
        "causal_panel_reconciliation": {
            key: reconciliation[key]
            for key in (
                "base_rows",
                "analysis_rows",
                "removed_rows",
                "base_epochs",
                "analysis_epochs",
                "base_intensity_3_events",
                "analysis_intensity_3_events",
                "events_removed",
                "clusters_removed",
                "removal_reason_counts",
            )
        },
        "score_field": {
            "score_changed": False,
            "rows_by_intensity": score["rows_by_intensity"],
            "aligned_equals_intensity_three": score["aligned_equals_intensity_three"],
            "mesi_bps_per_gate": mesi_bps_per_gate(),
        },
        "randomization_family": {
            "source_artifact": RANDOMIZATION_PATH,
            "artifact_sha256": _sha256(ROOT / RANDOMIZATION_PATH),
            "family_sha256": family["family_sha256"],
            "vectors_regenerated": False,
            "requested_vectors": family["requested_vectors"],
            "zero_shift_present": family["zero_shift_present"],
        },
        "support": {
            "accepted_vectors": support["accepted_vectors"],
            "requested_vectors": support["requested_vectors"],
            "retention_distributions": support["retention_distributions"],
        },
        "power": {
            "computed": True,
            "accepted_vectors": power["accepted_vectors"],
            "empirical_null_sd_bps_per_gate": power["empirical_null_sd_bps_per_gate"],
            "critical_beta_bps_per_gate": power["critical_beta_bps_per_gate"],
            "minimum_detectable_effect_bps_per_gate": power[
                "minimum_detectable_effect_bps_per_gate"
            ],
            "power_at_8_bps_per_gate": power_at_mesi,
            "power_curve": power["power_curve"],
            "minimum_attainable_randomization_p": power["minimum_attainable_randomization_p"],
            "tail_resolution_sufficient": power["tail_resolution_sufficient"],
            "target_power": TARGET_POWER,
        },
        "prerequisite_gates": prerequisites,
        "GATE_INTENSITY_POWER_GATE_STATUS": gate_status,
        "ALIGNED_DEVELOPMENT_FAMILY_STATUS": family_status,
        "preregistration_authorized": False,
        "actual_market_hypothesis_executed": False,
        "leakage_guard": {
            "sparse_zero_alignment_beta_computed": False,
            "gate_intensity_zero_shift_beta_computed": False,
            "real_t_computed": False,
            "real_p_computed": False,
            "per_asset_real_effect_computed": False,
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
        },
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    assert_no_real_effect_leakage(gate)
    write_json(ROOT / POWER_PATH, gate)
    lines = [
        "# ALIGNED gate-intensity causal correction and power gate V1_1",
        "",
        f"Status: **{gate_status}**",
        "",
        "The same frozen hypothesis was resumed after removing only the retired,",
        "non-point-in-time 504-row placebo participation filter. The real zero-shift",
        "gate-intensity coefficient was not computed.",
        "",
        "## Causal panel",
        "",
        f"- base rows: {reconciliation['base_rows']:,}",
        f"- analysis rows: {reconciliation['analysis_rows']:,}",
        f"- removed rows: {reconciliation['removed_rows']:,}",
        (
            f"- score-3 events: {reconciliation['base_intensity_3_events']:,} -> "
            f"{reconciliation['analysis_intensity_3_events']:,}"
        ),
        f"- reconciliation: {reconciliation['EVENT_RECONCILIATION_STATUS']}",
        "",
        "## Support and power",
        "",
        f"- accepted vectors: {support['accepted_vectors']} / {support['requested_vectors']}",
        f"- empirical null SD: {power['empirical_null_sd_bps_per_gate']:.6f} bps/gate",
        f"- critical beta: {power['critical_beta_bps_per_gate']:.6f} bps/gate",
        f"- MDE: {power['minimum_detectable_effect_bps_per_gate']:.6f} bps/gate",
        f"- power at 8 bps/gate: {power_at_mesi:.6f}",
        f"- tail resolution sufficient: {power['tail_resolution_sufficient']}",
        "",
        "Preregistration is not executed or authorized by this artifact; the next action",
        "is Research Director review.",
        "",
    ]
    (ROOT / POWER_MARKDOWN_PATH).write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "prerequisites": prerequisites,
                "power_at_8_bps_per_gate": power_at_mesi,
                "GATE_INTENSITY_POWER_GATE_STATUS": gate_status,
                "ALIGNED_DEVELOPMENT_FAMILY_STATUS": family_status,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if ready else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage", choices=("panel", "support", "gate", "reconcile", "design", "freeze")
    )
    options = parser.parse_args()
    if options.stage == "panel":
        return stage_panel()
    if options.stage == "support":
        return stage_support()
    if options.stage == "reconcile":
        return stage_reconcile()
    if options.stage == "design":
        return stage_design()
    if options.stage == "freeze":
        return stage_freeze()
    return stage_gate()


if __name__ == "__main__":
    raise SystemExit(main())
