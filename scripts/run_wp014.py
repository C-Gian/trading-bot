"""Execute the frozen WP-014 walk-forward after the committed Phase-1 gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.artifacts import write_parquet
from app.research.continuation_lab import PROFILES, ResearchInputs
from app.research.evaluation_protocol import load_protocol as load_walk_forward
from app.research.evaluation_protocol import terminal_classification
from app.research.supervised import load_feature_source
from app.research.wp014 import (
    CONTROL_VARIANT,
    EXPERIMENTS,
    PRIMARY_VARIANT,
    VARIANTS,
    load_protocol,
    preflight,
)
from app.research.wp014_lab import TRIAL_SCHEMA, ShallowInternalLab, parquet_rows

TRIALS_PATH = "data/derived/WP-014-shallow-internal-trials.parquet"
PREFLIGHT_PATH = "reports/validation/WP-014-PREFLIGHT.json"
COMPARISON_PATH = "reports/research/WP-014-COMPARISON.json"
DIAGNOSTICS_PATH = "reports/research/WP-014-NONLINEAR-DIAGNOSTICS.json"


def write_json(relative: str, payload: Any) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    gate = preflight(ROOT)
    if gate["status"] != "PASS":
        raise RuntimeError("WP-014 pre-result gate failed")
    if any(
        (ROOT / f"research/experiments/{experiment}/result.json").exists()
        for experiment in EXPERIMENTS.values()
    ):
        raise RuntimeError("WP-014 results already exist; refusing rerun")
    write_json(PREFLIGHT_PATH, gate)
    protocol = load_protocol(ROOT)
    walk_forward = load_walk_forward()
    lab = ShallowInternalLab(ResearchInputs.load(ROOT), load_feature_source(ROOT), walk_forward)
    results: dict[str, Any] = {}
    artifact_rows: list[dict[str, Any]] = []
    for variant in VARIANTS:
        print(f"running {variant}", flush=True)
        result = lab.run_configuration(variant)
        results[variant] = result
        for profile in PROFILES:
            artifact_rows.extend(parquet_rows(result["profiles"][profile]))
        write_json(
            f"research/experiments/{EXPERIMENTS[variant]}/fold-models.json",
            {
                "schema_version": 1,
                "work_package": "WP-014",
                "experiment_id": EXPERIMENTS[variant],
                "variant": variant,
                "architecture": protocol["models"][variant]["algorithm"],
                "fold_models": result["folds"],
                "model_fits": result["model_fits"],
            },
        )
    artifact = write_parquet(
        ROOT / TRIALS_PATH,
        artifact_rows,
        schema=TRIAL_SCHEMA,
        sort_key=["variant", "profile", "signal_us"],
        root=ROOT,
    )
    comparison: dict[str, Any] = {
        "schema_version": 1,
        "work_package": "WP-014",
        "protocol_id": protocol["protocol_id"],
        "model_version": "SHALLOW_INTERNAL_HGBR_V1",
        "primary_variant": PRIMARY_VARIANT,
        "control_variant": CONTROL_VARIANT,
        "artifact": artifact,
        "configurations": {},
    }
    for variant in VARIANTS:
        summaries = {
            profile: results[variant]["profiles"][profile]["summary"] for profile in PROFILES
        }
        default = summaries["DEFAULT"]
        comparison["configurations"][variant] = {
            "experiment_id": EXPERIMENTS[variant],
            "primary_result": default["metrics"]["net_expectancy_r"],
            "terminal_classification": terminal_classification(
                summaries["DEFAULT"],
                summaries["ZERO"],
                summaries["DOUBLE"],
                walk_forward,
            ),
            "profiles": {
                profile: {
                    "metrics": summaries[profile]["metrics"],
                    "stability": summaries[profile]["stability"],
                    "diagnostics": summaries[profile]["diagnostics"],
                    "folds": summaries[profile]["folds"],
                }
                for profile in PROFILES
            },
            "prediction_diagnostics": results[variant]["prediction_diagnostics"],
            "model_fits": results[variant]["model_fits"],
        }
    primary = comparison["configurations"][PRIMARY_VARIANT]
    control = comparison["configurations"][CONTROL_VARIANT]
    comparison["primary_vs_control"] = {
        "default_net_expectancy_difference_r": (
            primary["primary_result"] - control["primary_result"]
        ),
        "default_trade_count_difference": (
            primary["profiles"]["DEFAULT"]["metrics"]["trade_count"]
            - control["profiles"]["DEFAULT"]["metrics"]["trade_count"]
        ),
        "eligible_universe_matched": True,
        "executed_trade_sets_paired": False,
        "control_duplicate_of": "EXP-ML-014-LINEAR-NET-R-FULL",
        "interpretation_guard": (
            "Matched eligible hours do not make executed trades paired because predictions "
            "and occupancy differ."
        ),
    }
    write_json(COMPARISON_PATH, comparison)
    write_json(
        DIAGNOSTICS_PATH,
        {
            "schema_version": 1,
            "work_package": "WP-014",
            "model_version": "SHALLOW_INTERNAL_HGBR_V1",
            "predictive_not_causal": True,
            "used_to_adapt_experiment": False,
            "eligibility_exclusions": dict(sorted(lab.exclusions.items())),
            "configurations": {
                variant: {
                    "folds": results[variant]["folds"],
                    "prediction": results[variant]["prediction_diagnostics"],
                }
                for variant in VARIANTS
            },
        },
    )
    print(json.dumps(comparison["primary_vs_control"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
