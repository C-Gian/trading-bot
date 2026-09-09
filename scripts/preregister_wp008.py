"""Create both fixed WP-008 preregistrations after committed novelty admission."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.continuation_lab import DATASET_HASH, DATASET_ID, PROFILES
from app.research.model_search_memory import bind_model_spec, model_fingerprint
from app.research.runner import declared_content_identity, sha256
from app.research.wp004 import ancestor, git, immutable_from_first_commit
from app.research.wp008 import (
    ADMISSION_PATH,
    ALLOCATION_ID,
    LEDGER_PATH,
    PRIMARY_VARIANT,
    ROLES,
    SPEC,
    config_path,
    dependency_manifest,
    executable_spec,
    validate_admission,
    validate_allocation,
)

SECONDARY = [
    "profiles",
    "terminal_classification",
    "fold_models",
    "training_manifests",
    "prediction_diagnostics",
    "artifact_manifest",
    "execution_provenance",
]


def dump(path: Path, payload: object) -> None:
    if path.exists():
        raise FileExistsError(f"immutable preregistration artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n")


def main() -> None:
    if git("branch", "--show-current", root=ROOT) != "main" or git(
        "status", "--porcelain", root=ROOT
    ):
        raise RuntimeError("WP-008 preregistration requires a clean local main")
    admission = validate_admission(ROOT)
    validate_allocation(ROOT)
    admission_commit = immutable_from_first_commit(ADMISSION_PATH, ROOT)
    if not ancestor(admission_commit, "HEAD", ROOT):
        raise RuntimeError("admission must be committed before preregistration")
    created = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    ledger = []
    admitted = {item["experiment_id"]: item for item in admission["variants"]}
    for experiment_id, variant in SPEC.items():
        relative = config_path(variant)
        plan = [
            {
                "trial_id": f"{variant}:{profile}",
                "config_path": relative,
                "config_sha256": sha256(ROOT / relative),
            }
            for profile in PROFILES
        ]
        spec = executable_spec(variant, ROOT)
        binding = bind_model_spec(spec)
        prereg = {
            "schema_version": 2,
            "experiment_id": experiment_id,
            "experiment_version": 1,
            "created_at_utc": created,
            "hypothesis": "A fixed low-dimensional linear combination can select predicted-positive default-cost LONG opportunities with robust positive realized net expectancy.",
            "rationale": "One interpretable zero-tuning supervised challenger is authorized after repeated gross-positive but friction-consumed manual families.",
            "research_scope": "BTCUSDT Spot LONG-only exposed development walk-forward; predictive, not causal; exactly one primary and one no-flow ablation.",
            "dataset": {
                "manifest_id": DATASET_ID,
                "content_hash": DATASET_HASH,
                "maximum_timestamp": "2024-12-31T23:59:00Z",
            },
            "metrics": {
                "primary": "POOLED_VALID_RESOLVED_DEFAULT_NET_R",
                "secondary": SECONDARY,
            },
            "evaluation_design": "Six frozen annual expanding chronological folds; training signals end before validation_start-216h; DEFAULT-label OLS fitted once per fold/configuration; four fixed execution profiles.",
            "leakage_controls": [
                "FEATURES_AVAILABLE_BY_SIGNAL_TIME",
                "COMPLETED_CONTIGUOUS_UNQUARANTINED_WINDOWS",
                "NONOVERLAPPING_COMPLETED_4H_CONTEXT",
                "TRAINING_ONLY_DEFAULT_LABELS",
                "TRAINING_ONLY_SCALING_DDOF_0",
                "TRAINING_LABEL_OUTCOME_STRICTLY_BEFORE_VALIDATION",
                "NO_VALIDATION_REFIT_OR_FEATURE_SELECTION",
                "POST_CUTOFF_HARD_FAIL",
            ],
            "cost_execution_reference": "BACKTEST_ENGINE_V2 / EXECUTION_MODEL_V2 / BTCUSDT_SPOT_COST_V1",
            "parameter_space": {
                "root_family": "FAM-SUPERVISED-LINEAR",
                "hypothesis_id": "LINEAR_NET_R_SELECTION_V1",
                "variant": variant,
                "primary_family_variant": PRIMARY_VARIANT,
                "allocation_id": ALLOCATION_ID,
                "trial_plan": plan,
                "strategy_path": "backend/app/research/linear_lab.py",
                "strategy_sha256": sha256(ROOT / "backend/app/research/linear_lab.py"),
                "dependencies": dependency_manifest(ROOT),
                "model_fingerprint": model_fingerprint(spec),
                "executable_model_spec": json.loads(json.dumps(spec.to_dict())),
                "executable_spec_hash": binding.executable_spec_hash,
                "behavior_hash": binding.behavior_hash,
                "structural_hash": binding.structural_hash,
                "dependency_hash": binding.dependency_hash,
                "model_fits": 6,
                "numeric_parameter_variants": 0,
                "algorithm_variants": 0,
                "hyperparameter_searches": 0,
                "threshold_searches": 0,
            },
            "trial_budget": 4,
            "stopping_rule": "Execute all four declared profiles once; preserve every outcome; do not adapt features, model, threshold, or execution.",
            "seeds": [0],
            "code_config_reference": declared_content_identity(
                ROOT / "backend/app/research/linear_lab.py", plan
            ),
            "status": "PREREGISTERED",
        }
        path = ROOT / "research/experiments" / experiment_id / "preregistration.json"
        dump(path, prereg)
        decision = admitted[experiment_id]
        reason = (
            "The fixed eight-feature OLS challenger is the preselected family primary."
            if variant == PRIMARY_VARIANT
            else "The fixed six-feature no-flow configuration is a structural ablation only."
        )
        ledger.append(
            {
                "schema_version": 2,
                "experiment_id": experiment_id,
                "work_package": "WP-008",
                "record_kind": "PREREGISTERED_ADMISSION",
                "strategy_label": variant,
                "root_family": "FAM-SUPERVISED-LINEAR",
                "hypothesis_id": "LINEAR_NET_R_SELECTION_V1",
                "hypothesis_role": ROLES[variant],
                "claimed_market_mechanism": "A fixed OLS combination of governed descriptors may rank default-cost long opportunity quality; predictive, not causal.",
                "allocation_id": ALLOCATION_ID,
                "classification": decision["classification"],
                "matched_experiment_ids": decision["matched_experiment_ids"],
                "behavior_hash": decision["behavior_hash"],
                "structural_hash": decision["structural_hash"],
                "executable_spec_hash": decision["executable_spec_hash"],
                "dependency_hash": decision["dependency_hash"],
                "parent_experiment_ids": [] if variant == PRIMARY_VARIANT else [next(iter(SPEC))],
                "novelty": decision["classification"],
                "scientific_reason": reason,
                "budget_units": {
                    "experiments": 1,
                    "strategy_variants": 1,
                    "trials": 4,
                    "numeric_parameter_variants": 0,
                },
                "preregistration_path": path.relative_to(ROOT).as_posix(),
                "preregistration_sha256": sha256(path),
                "result_path": f"research/experiments/{experiment_id}/result.json",
                "outcome_reference": experiment_id,
            }
        )
    ledger_path = ROOT / LEDGER_PATH
    if ledger_path.exists():
        raise FileExistsError("immutable WP-008 ledger already exists")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        "".join(json.dumps(item, separators=(",", ":"), allow_nan=False) + "\n" for item in ledger)
    )
    print("Both fixed WP-008 preregistrations and admissions created; no market data loaded.")


if __name__ == "__main__":
    main()
