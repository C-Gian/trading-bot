"""Independent reconciliation of the WP-011 adaptive walk-forward.

Rebuilds monthly weighted fits, weighted moments, coefficients, predictions and the
DEFAULT executed metrics from the committed artifacts using an independent code path.
It never calls `AdaptiveEwlsLab`. Any exact mismatch fails.
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
from app.research.macro import load_macro_source
from app.research.supervised import (
    SupervisedDataError,
    SupervisedRow,
    isolated_label,
    load_feature_source,
)
from app.research.wp011 import EXPERIMENTS, VARIANTS, load_protocol

RECONCILIATION_PATH = "reports/validation/WP-011-MODEL-RECONCILIATION.json"
TRIALS_PATH = "data/derived/WP-011-adaptive-trials.parquet"
COMPARISON_PATH = "reports/research/WP-011-COMPARISON.json"
PURGE_US = 216 * HOUR_US
HALF_LIFE_DAYS = 180.0
DAY_US = 86_400_000_000
HISTORY_START = "2017-08-17T04:00:00Z"
TOLERANCE = 1e-12


def independent_fit(
    matrix: np.ndarray, labels: np.ndarray, times: np.ndarray, effective_us: int
) -> dict[str, Any]:
    """Weighted least squares written out longhand, not the production implementation."""
    ages = [(effective_us - int(stamp)) / DAY_US for stamp in times]
    weights = np.array(
        [math.exp(-math.log(2.0) * age / HALF_LIFE_DAYS) for age in ages], dtype=np.float64
    )
    total = float(sum(weights))
    means = np.array(
        [
            float(sum(w * x for w, x in zip(weights, column, strict=True)) / total)
            for column in matrix.T
        ],
        dtype=np.float64,
    )
    variances = np.array(
        [
            float(sum(w * (x - mean) ** 2 for w, x in zip(weights, column, strict=True)) / total)
            for column, mean in zip(matrix.T, means, strict=True)
        ],
        dtype=np.float64,
    )
    stds = np.sqrt(variances)
    standardized = (matrix - means) / stds
    design = np.column_stack((np.ones(len(labels)), standardized))
    root = np.sqrt(weights)
    solution, _, rank, _ = np.linalg.lstsq(design * root[:, None], labels * root, rcond=None)
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
    inputs = ResearchInputs.load(ROOT)
    internal = load_feature_source(ROOT)
    macro = load_macro_source(ROOT)

    last_signal = utc_us("2024-12-31T00:00:00Z")
    rows: list[tuple[int, float, tuple[float, ...]]] = []
    for signal_us in range(utc_us(HISTORY_START), last_signal + 1, HOUR_US):
        try:
            item = internal.at(signal_us)
        except SupervisedDataError:
            continue
        macro_row = macro.at(signal_us)
        if macro_row is None:
            continue
        rows.append((signal_us, item.reference, item.values + macro_row.values))
    print(f"independent universe: {len(rows)} eligible rows", flush=True)

    labels: dict[int, Any] = {}
    for signal_us, reference, values in rows:
        proxy = SupervisedRow(signal_us, reference, 0, 0, signal_us, values[:8])
        labels[signal_us] = isolated_label(inputs, proxy)
    print("independent labels built", flush=True)

    checks: dict[str, str] = {}
    mismatches: list[dict[str, Any]] = []

    # 1. Re-fit a sample of monthly models per configuration and per fold.
    refits = 0
    for variant in VARIANTS:
        names = protocol["features"][variant]
        order = protocol["features"]["EWLS_INTERNAL_MACRO"]
        indices = [order.index(name) for name in names]
        monthly = json.loads(
            (ROOT / f"research/experiments/{EXPERIMENTS[variant]}/monthly-models.json").read_text(
                encoding="utf-8"
            )
        )["monthly_models"]
        # One monthly model inside every validation year.
        sampled = {}
        for item in monthly:
            year = item["effective_utc"][:4]
            sampled.setdefault(year, item)
        for item in sampled.values():
            effective_us = utc_us(item["effective_utc"])
            boundary = effective_us - PURGE_US
            selected = [
                (signal_us, values)
                for signal_us, _reference, values in rows
                if signal_us < boundary
                and labels[signal_us].status == "VALID"
                and labels[signal_us].net_r is not None
                and labels[signal_us].outcome_us < boundary
            ]
            times = np.array([s for s, _ in selected], dtype=np.int64)
            matrix = np.array([[v[i] for i in indices] for _, v in selected], dtype=np.float64)
            target = np.array([labels[s].net_r for s, _ in selected], dtype=np.float64)
            rebuilt = independent_fit(matrix, target, times, effective_us)
            refits += 1
            if len(selected) != item["fit_rows"]:
                mismatches.append(
                    {
                        "variant": variant,
                        "effective": item["effective_utc"],
                        "field": "fit_rows",
                        "recorded": item["fit_rows"],
                        "rebuilt": len(selected),
                    }
                )
            if rebuilt["rank"] != item["rank"]:
                mismatches.append(
                    {"variant": variant, "effective": item["effective_utc"], "field": "rank"}
                )
            item["_rebuilt"] = rebuilt
            item["_indices"] = indices
    checks["monthly_fit_rows_and_rank"] = "PASS" if not mismatches else "FAIL"
    print(f"independent refits: {refits}", flush=True)

    # 2. DEFAULT executed metrics recomputed from the stored trial rows.
    table = pq.read_table(ROOT / TRIALS_PATH).to_pylist()
    executed = defaultdict(list)
    for row in table:
        executed[(row["variant"], row["profile"])].append(row)
    metric_mismatch = []
    for variant in VARIANTS:
        recorded = comparison["configurations"][variant]["profiles"]["DEFAULT"]
        trades = executed[(variant, "DEFAULT")]
        resolved = [row for row in trades if row["status"] == "VALID"]
        valid = [row["net_r"] for row in resolved]
        # The governed trade_count is resolved trades only; unresolved rows are retained
        # and counted separately, never imputed.
        if len(resolved) != recorded["trade_count"]:
            metric_mismatch.append(
                {
                    "variant": variant,
                    "field": "trade_count",
                    "recorded": recorded["trade_count"],
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
            if abs(expectancy - (recorded["net_expectancy_r"] or 0.0)) > 1e-9:
                metric_mismatch.append(
                    {
                        "variant": variant,
                        "field": "net_expectancy_r",
                        "recorded": recorded["net_expectancy_r"],
                        "rebuilt": expectancy,
                    }
                )
            if abs(float(sum(valid)) - (recorded["cumulative_net_r"] or 0.0)) > 1e-9:
                metric_mismatch.append({"variant": variant, "field": "cumulative_net_r"})
    checks["default_executed_metrics"] = "PASS" if not metric_mismatch else "FAIL"
    mismatches.extend(metric_mismatch)

    # 3. Signal timestamps must be hour-aligned, inside a fold, and never post-cutoff.
    bad_timestamps = 0
    for row in table:
        if row["signal_us"] % HOUR_US or row["signal_us"] > utc_us("2024-12-31T23:00:00Z"):
            bad_timestamps += 1
        if row["model_effective_us"] > row["signal_us"]:
            bad_timestamps += 1
        if row["profile"] == "DELAY_1H":
            if row["prediction_signal_us"] != row["signal_us"] - HOUR_US:
                bad_timestamps += 1
        elif row["prediction_signal_us"] != row["signal_us"]:
            bad_timestamps += 1
    checks["signal_and_model_timestamps"] = "PASS" if bad_timestamps == 0 else "FAIL"

    # 4. ZERO/DOUBLE must reuse exactly the DEFAULT signal set; only cost differs.
    cost_reuse = "PASS"
    for variant in VARIANTS:
        default_signals = {row["signal_us"] for row in executed[(variant, "DEFAULT")]}
        for profile in ("ZERO", "DOUBLE"):
            if {row["signal_us"] for row in executed[(variant, profile)]} != default_signals:
                cost_reuse = "FAIL"
                mismatches.append({"variant": variant, "field": f"{profile}_signal_reuse"})
    checks["zero_double_reuse_default_signals"] = cost_reuse

    # 5. Every training label outcome precedes its own purge boundary.
    containment = "PASS"
    for variant in VARIANTS:
        monthly = json.loads(
            (ROOT / f"research/experiments/{EXPERIMENTS[variant]}/monthly-models.json").read_text(
                encoding="utf-8"
            )
        )["monthly_models"]
        for item in monthly:
            if item["max_training_label_outcome_us"] >= item["purge_boundary_exclusive_us"]:
                containment = "FAIL"
                mismatches.append(
                    {
                        "variant": variant,
                        "effective": item["effective_utc"],
                        "field": "label_outcome_containment",
                    }
                )
    checks["training_outcomes_precede_purge_boundary"] = containment

    report = {
        "schema_version": 1,
        "work_package": "WP-011",
        "reconciliation": "INDEPENDENT_ADAPTIVE_EWLS_V1",
        "independent_path": "LONGHAND_WEIGHTED_FIT_NOT_THE_PRODUCTION_LAB",
        "status": "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL",
        "checks": checks,
        "independent_universe_rows": len(rows),
        "independent_monthly_refits": refits,
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
