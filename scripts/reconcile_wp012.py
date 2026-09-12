"""Independent reconciliation of the WP-012 regime-conditioned walk-forward.

Rebuilds the eligible universe, the regime partition, the per-expert fits and the DEFAULT
executed metrics from the committed artifacts using an independent code path. It never
calls `RegimeExpertLab`. Any mismatch fails.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np
import pyarrow.parquet as pq
from app.research.continuation_lab import ResearchInputs, costs
from app.research.evaluation_protocol import HOUR_US, utc_us
from app.research.regime import REGIMES, classify, load_regime_source
from app.research.supervised import (
    SupervisedDataError,
    SupervisedRow,
    isolated_label,
    load_feature_source,
)
from app.research.wp012 import EXPERIMENTS, GLOBAL_KEY, PRIMARY_VARIANT, VARIANTS, load_protocol

RECONCILIATION_PATH = "reports/validation/WP-012-MODEL-RECONCILIATION.json"
TRIALS_PATH = "data/derived/WP-012-regime-trials.parquet"
COMPARISON_PATH = "reports/research/WP-012-COMPARISON.json"
WALK_FORWARD_PATH = "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json"
PURGE_US = 216 * HOUR_US
HISTORY_START = "2017-08-17T04:00:00Z"


def independent_fit(matrix: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    """Ordinary least squares written out longhand, not the production implementation."""
    count = len(labels)
    means = np.array([float(math.fsum(column) / count) for column in matrix.T], dtype=np.float64)
    stds = np.array(
        [
            math.sqrt(math.fsum((x - mean) ** 2 for x in column) / count)
            for column, mean in zip(matrix.T, means, strict=True)
        ],
        dtype=np.float64,
    )
    standardized = (matrix - means) / stds
    design = np.column_stack((np.ones(count, dtype=np.float64), standardized))
    solution, _, rank, _ = np.linalg.lstsq(design, labels, rcond=None)
    return {
        "means": means,
        "stds": stds,
        "intercept": float(solution[0]),
        "coefficients": np.asarray(solution[1:], dtype=np.float64),
        "rank": int(rank),
    }


def main() -> int:
    protocol = load_protocol(ROOT)
    comparison = json.loads((ROOT / COMPARISON_PATH).read_text(encoding="utf-8"))
    folds = json.loads((ROOT / WALK_FORWARD_PATH).read_text(encoding="utf-8"))["folds"]
    inputs = ResearchInputs.load(ROOT)
    internal = load_feature_source(ROOT)
    regimes = load_regime_source(ROOT)

    last_signal = utc_us("2024-12-31T00:00:00Z")
    rows: list[tuple[int, str, tuple[float, ...]]] = []
    references: dict[int, float] = {}
    for signal_us in range(utc_us(HISTORY_START), last_signal + 1, HOUR_US):
        try:
            item = internal.at(signal_us)
        except SupervisedDataError:
            continue
        reading = regimes.at(signal_us)
        if reading is None:
            continue
        # Re-derive the regime from the raw value rather than trusting the gate's label.
        rows.append((signal_us, classify(reading.nfci), item.values))
        references[signal_us] = item.reference
    print(f"independent universe: {len(rows)} eligible rows", flush=True)

    labels: dict[int, Any] = {}
    for signal_us, _regime, values in rows:
        proxy = SupervisedRow(signal_us, references[signal_us], 0, 0, signal_us, values)
        labels[signal_us] = isolated_label(inputs, proxy)
    print("independent labels built", flush=True)

    checks: dict[str, str] = {}
    mismatches: list[dict[str, Any]] = []

    # 1. Re-fit every recorded expert and require the same rows, rank and coefficients.
    refits = 0
    coefficient_gap = 0.0
    for variant in VARIANTS:
        recorded = json.loads(
            (ROOT / f"research/experiments/{EXPERIMENTS[variant]}/fold-experts.json").read_text(
                encoding="utf-8"
            )
        )["fold_experts"]
        for fold, item in zip(folds, recorded, strict=True):
            boundary = utc_us(fold["train_end_exclusive"])
            train_start = utc_us(fold["train_start"])
            eligible = [
                (signal_us, regime, values)
                for signal_us, regime, values in rows
                if train_start <= signal_us < boundary
                and labels[signal_us].status == "VALID"
                and labels[signal_us].net_r is not None
                and labels[signal_us].outcome_us < boundary
            ]
            groups = (
                {regime: [r for r in eligible if r[1] == regime] for regime in REGIMES}
                if variant == PRIMARY_VARIANT
                else {GLOBAL_KEY: eligible}
            )
            for key, group in groups.items():
                model = item["experts"].get(key)
                if model is None:
                    # A refused expert must be refused for a recorded reason, and the rows
                    # it would have used must genuinely be too few to fit.
                    if key not in item["infeasible_experts"]:
                        mismatches.append(
                            {"variant": variant, "fold": fold["fold_id"], "field": "unexplained"}
                        )
                    elif len(group) > len(protocol["features"][variant]):
                        mismatches.append(
                            {
                                "variant": variant,
                                "fold": fold["fold_id"],
                                "expert": key,
                                "field": "refused_despite_sufficient_rows",
                                "rows": len(group),
                            }
                        )
                    continue
                manifest = item["training_manifests"][key]
                if len(group) != manifest["fit_rows"]:
                    mismatches.append(
                        {
                            "variant": variant,
                            "fold": fold["fold_id"],
                            "expert": key,
                            "field": "fit_rows",
                            "recorded": manifest["fit_rows"],
                            "rebuilt": len(group),
                        }
                    )
                    continue
                matrix = np.array([values for _s, _r, values in group], dtype=np.float64)
                target = np.array([labels[s].net_r for s, _r, _v in group], dtype=np.float64)
                rebuilt = independent_fit(matrix, target)
                refits += 1
                if rebuilt["rank"] != model["rank"]:
                    mismatches.append(
                        {"variant": variant, "fold": fold["fold_id"], "field": "rank"}
                    )
                gap = float(
                    np.max(np.abs(rebuilt["coefficients"] - np.array(model["coefficients"])))
                )
                coefficient_gap = max(coefficient_gap, gap)
                if gap > 1e-9 or abs(rebuilt["intercept"] - model["intercept"]) > 1e-9:
                    mismatches.append(
                        {
                            "variant": variant,
                            "fold": fold["fold_id"],
                            "expert": key,
                            "field": "coefficients",
                            "max_absolute_gap": gap,
                        }
                    )
    checks["expert_fits_reproduce_exactly"] = "PASS" if not mismatches else "FAIL"
    print(f"independent refits: {refits}", flush=True)

    # 2. The regime partition must be disjoint and exhaustive over eligible hours.
    partition: defaultdict[str, int] = defaultdict(int)
    for _signal_us, regime, _values in rows:
        partition[regime] += 1
    checks["regime_partition_is_exhaustive"] = (
        "PASS"
        if sum(partition.values()) == len(rows) and set(partition) <= set(REGIMES)
        else "FAIL"
    )

    # 3. DEFAULT executed metrics recomputed from the stored trial rows.
    table = pq.read_table(ROOT / TRIALS_PATH).to_pylist()
    executed = defaultdict(list)
    for row in table:
        executed[(row["variant"], row["profile"])].append(row)
    metric_mismatch: list[dict[str, Any]] = []
    for variant in VARIANTS:
        recorded_metrics = comparison["configurations"][variant]["profiles"]["DEFAULT"]["metrics"]
        trades = executed[(variant, "DEFAULT")]
        resolved = [row for row in trades if row["status"] == "VALID"]
        valid = [row["net_r"] for row in resolved]
        if len(resolved) != recorded_metrics["trade_count"]:
            metric_mismatch.append(
                {
                    "variant": variant,
                    "field": "trade_count",
                    "recorded": recorded_metrics["trade_count"],
                    "rebuilt": len(resolved),
                }
            )
        unresolved = [row for row in trades if row["status"] != "VALID"]
        if any(row["net_r"] is not None or row["gross_r"] is not None for row in unresolved):
            metric_mismatch.append(
                {"variant": variant, "field": "unresolved_rows_carry_invented_pnl"}
            )
        if valid:
            expectancy = float(sum(valid) / len(valid))
            if abs(expectancy - (recorded_metrics["net_expectancy_r"] or 0.0)) > 1e-9:
                metric_mismatch.append(
                    {
                        "variant": variant,
                        "field": "net_expectancy_r",
                        "recorded": recorded_metrics["net_expectancy_r"],
                        "rebuilt": expectancy,
                    }
                )
            if abs(float(sum(valid)) - (recorded_metrics["cumulative_net_r"] or 0.0)) > 1e-9:
                metric_mismatch.append({"variant": variant, "field": "cumulative_net_r"})
    checks["default_executed_metrics"] = "PASS" if not metric_mismatch else "FAIL"
    mismatches.extend(metric_mismatch)

    # 4. Every executed row must carry the regime the independent gate assigns it, and the
    #    expert that regime selects.
    truth = {signal_us: regime for signal_us, regime, _values in rows}
    gate_mismatch = 0
    for row in table:
        expected = truth.get(row["signal_us"])
        if expected is None or row["regime"] != expected:
            gate_mismatch += 1
            continue
        wanted = expected if row["variant"] == PRIMARY_VARIANT else GLOBAL_KEY
        if row["expert"] != wanted:
            gate_mismatch += 1
    checks["executed_rows_match_the_independent_gate"] = "PASS" if gate_mismatch == 0 else "FAIL"

    # 5. Signal timestamps hour-aligned, pre-cutoff, and the delay profile offset by 1h.
    bad_timestamps = 0
    for row in table:
        if row["signal_us"] % HOUR_US or row["signal_us"] > utc_us("2024-12-31T23:00:00Z"):
            bad_timestamps += 1
        if row["profile"] == "DELAY_1H":
            if row["prediction_signal_us"] != row["signal_us"] - HOUR_US:
                bad_timestamps += 1
        elif row["prediction_signal_us"] != row["signal_us"]:
            bad_timestamps += 1
    checks["signal_and_prediction_timestamps"] = "PASS" if bad_timestamps == 0 else "FAIL"

    # 6. ZERO/DOUBLE must reuse exactly the DEFAULT signal set; only cost differs.
    cost_reuse = "PASS"
    for variant in VARIANTS:
        default_signals = {row["signal_us"] for row in executed[(variant, "DEFAULT")]}
        for profile in ("ZERO", "DOUBLE"):
            if {row["signal_us"] for row in executed[(variant, profile)]} != default_signals:
                cost_reuse = "FAIL"
                mismatches.append({"variant": variant, "field": f"{profile}_signal_reuse"})
    checks["zero_double_reuse_default_signals"] = cost_reuse

    # 7. Every training label outcome precedes its own purge boundary.
    containment = "PASS"
    for variant in VARIANTS:
        recorded = json.loads(
            (ROOT / f"research/experiments/{EXPERIMENTS[variant]}/fold-experts.json").read_text(
                encoding="utf-8"
            )
        )["fold_experts"]
        for item in recorded:
            for key, manifest in item["training_manifests"].items():
                if manifest["max_training_label_outcome_us"] >= manifest[
                    "purge_boundary_exclusive_us"
                ] or (
                    manifest["validation_start_us"] - manifest["purge_boundary_exclusive_us"]
                    != PURGE_US
                ):
                    containment = "FAIL"
                    mismatches.append(
                        {
                            "variant": variant,
                            "fold": item["fold_id"],
                            "expert": key,
                            "field": "label_outcome_containment",
                        }
                    )
    checks["training_outcomes_precede_purge_boundary"] = containment

    report = {
        "schema_version": 1,
        "work_package": "WP-012",
        "reconciliation": "INDEPENDENT_REGIME_CONDITIONED_EXPERTS_V1",
        "independent_path": "LONGHAND_OLS_AND_RESCANNED_REGIME_NOT_THE_PRODUCTION_LAB",
        "status": "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL",
        "checks": checks,
        "independent_universe_rows": len(rows),
        "independent_regime_counts": dict(sorted(partition.items())),
        "independent_expert_refits": refits,
        "maximum_coefficient_gap": coefficient_gap,
        "executed_rows_examined": len(table),
        "mismatches": mismatches[:20],
        "cost_profile": costs("DEFAULT").profile,
    }
    path = ROOT / RECONCILIATION_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({k: v for k, v in report.items() if k != "mismatches"}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
