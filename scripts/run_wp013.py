"""Execute the frozen WP-013 walk-forward after the committed preflight gate."""

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
from app.research.nfci_context import load_nfci_context
from app.research.supervised import FULL_FEATURES, load_feature_source
from app.research.wp013 import (
    CONTROL_VARIANT,
    EXPERIMENTS,
    INTERACTION_FEATURES,
    PRIMARY_VARIANT,
    VARIANTS,
    load_protocol,
    preflight,
)
from app.research.wp013_lab import TRIAL_SCHEMA, ContextInteractionLab, parquet_rows

TRIALS_PATH = "data/derived/WP-013-context-interaction-trials.parquet"
PREFLIGHT_PATH = "reports/validation/WP-013-PREFLIGHT.json"
COMPARISON_PATH = "reports/research/WP-013-COMPARISON.json"
DIAGNOSTICS_PATH = "reports/research/WP-013-INTERACTION-DIAGNOSTICS.json"


def write_json(relative: str, payload: Any) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def fold_diagnostics(result: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for fold in result["folds"]:
        model = fold["model"]
        coefficients = dict(zip(model["feature_order"], model["coefficients"], strict=True))
        stds = dict(zip(model["feature_order"], model["stds_ddof_0"], strict=True))
        item: dict[str, Any] = {
            "fold_id": fold["fold_id"], "fit_rows": fold["training_manifest"]["fit_rows"],
            "condition_number": model["condition_number"], "model_hash": model["model_hash"],
            "standardized_coefficients": coefficients,
        }
        if result["variant"] == PRIMARY_VARIANT:
            effective = {}
            for index, base in enumerate(FULL_FEATURES):
                interaction = INTERACTION_FEATURES[index]
                base_slope = coefficients[base] / stds[base]
                interaction_slope = coefficients[interaction] / stds[interaction]
                effective[base] = {
                    "NFCI_-1": base_slope - interaction_slope,
                    "NFCI_0": base_slope,
                    "NFCI_+1": base_slope + interaction_slope,
                    "raw_interaction_slope": interaction_slope,
                }
            item["effective_raw_feature_slopes"] = effective
        items.append(item)
    return items


def main() -> int:
    gate = preflight(ROOT)
    audit = json.loads((ROOT / "reports/validation/WP-013-NFCI-ASOF-AUDIT.json").read_text())
    if gate["status"] != "PASS" or audit["status"] != "PASS":
        raise RuntimeError("WP-013 pre-result gate failed")
    if any((ROOT / f"research/experiments/{e}/result.json").exists()
           for e in EXPERIMENTS.values()):
        raise RuntimeError("WP-013 results already exist; refusing rerun")
    write_json(PREFLIGHT_PATH, gate)
    protocol, walk_forward = load_protocol(ROOT), load_walk_forward()
    lab = ContextInteractionLab(ResearchInputs.load(ROOT), load_feature_source(ROOT),
                                load_nfci_context(ROOT), walk_forward)
    results: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    for variant in VARIANTS:
        print(f"running {variant}", flush=True)
        result = lab.run_configuration(variant)
        results[variant] = result
        for profile in PROFILES:
            rows.extend(parquet_rows(result["profiles"][profile]))
        write_json(f"research/experiments/{EXPERIMENTS[variant]}/fold-models.json", {
            "schema_version": 1, "work_package": "WP-013", "experiment_id": EXPERIMENTS[variant],
            "variant": variant, "architecture": protocol["architecture"],
            "fold_models": result["folds"], "model_fits": result["model_fits"],
        })
    manifest = write_parquet(ROOT / TRIALS_PATH, rows, schema=TRIAL_SCHEMA,
                             sort_key=["variant", "profile", "signal_us"], root=ROOT)
    comparison: dict[str, Any] = {
        "schema_version": 1, "work_package": "WP-013", "protocol_id": protocol["protocol_id"],
        "architecture": protocol["architecture"], "context_version": protocol["context"]["version"],
        "primary_variant": PRIMARY_VARIANT, "control_variant": CONTROL_VARIANT,
        "artifact": manifest, "configurations": {},
    }
    for variant in VARIANTS:
        summaries = {p: results[variant]["profiles"][p]["summary"] for p in PROFILES}
        default = summaries["DEFAULT"]
        comparison["configurations"][variant] = {
            "experiment_id": EXPERIMENTS[variant],
            "primary_result": default["metrics"]["net_expectancy_r"],
            "terminal_classification": terminal_classification(
                summaries["DEFAULT"], summaries["ZERO"], summaries["DOUBLE"], walk_forward),
            "profiles": {p: {"metrics": summaries[p]["metrics"],
                             "stability": summaries[p]["stability"],
                             "diagnostics": summaries[p]["diagnostics"],
                             "folds": summaries[p]["folds"]} for p in PROFILES},
            "prediction_diagnostics": results[variant]["prediction_diagnostics"],
            "model_fits": results[variant]["model_fits"],
        }
    primary = comparison["configurations"][PRIMARY_VARIANT]
    control = comparison["configurations"][CONTROL_VARIANT]
    comparison["interaction_effect"] = {
        "primary_minus_control_default_net_expectancy_r": primary["primary_result"] - control["primary_result"],
        "primary_default_trade_count": primary["profiles"]["DEFAULT"]["metrics"]["trade_count"],
        "control_default_trade_count": control["profiles"]["DEFAULT"]["metrics"]["trade_count"],
        "eligible_universe_matched": True, "executed_trade_sets_paired": False,
        "interpretation_guard": "Same eligible hours do not imply paired executed trades because predictions and occupancy differ.",
    }
    write_json(COMPARISON_PATH, comparison)
    write_json(DIAGNOSTICS_PATH, {
        "schema_version": 1, "work_package": "WP-013", "context_version": protocol["context"]["version"],
        "predictive_not_causal": True, "diagnostic_context_values": [-1.0, 0.0, 1.0],
        "eligibility_exclusions": dict(sorted(lab.exclusions.items())),
        "configurations": {variant: {"folds": fold_diagnostics(results[variant]),
                                     "prediction": results[variant]["prediction_diagnostics"]}
                           for variant in VARIANTS},
    })
    print(json.dumps(comparison["interaction_effect"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
