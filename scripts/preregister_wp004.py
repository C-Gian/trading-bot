"""Create all frozen preregistrations and admissions; never accesses market tables."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.continuation_lab import PROFILES, costs
from app.research.evaluation_protocol import load_protocol, protocol_hash
from app.research.records import validate_preregistration
from app.research.runner import declared_content_identity, sha256
from app.research.search_memory import (
    admit_proposal,
    fingerprint_hash,
    load_memory,
    render_failure_memory,
    render_research_map,
    validate_memory,
)
from app.research.wp004 import SPEC, dependency_manifest, git, validate_identity


def main() -> None:
    if git("status", "--porcelain") or git("branch", "--show-current") != "main":
        raise ValueError("commit the implementation on main before preregistration")
    if any((ROOT / f"research/experiments/{eid}/preregistration.json").exists() for eid in SPEC):
        raise FileExistsError("a WP-004 preregistration already exists")
    memory = load_memory()
    if validate_memory()["global"]["experiments"] != 6:
        raise ValueError("unexpected existing research allocation")
    baseline = next(
        row for row in memory["entries"] if row["experiment_id"] == "EXP-BASE-004-BREAKOUT"
    )
    source = next(
        row for row in memory["outcomes"] if row["experiment_id"] == baseline["experiment_id"]
    )
    protocol = load_protocol()
    features_path = ROOT / "research/protocols/CONTINUATION_FEATURES_V1.json"
    features = json.loads(features_path.read_text())
    created = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    commit = git("rev-parse", "HEAD")
    strategy = ROOT / "backend/app/research/continuation.py"
    dependencies = dependency_manifest()
    # Core admitted first; the two other configurations are explicit structural ablations.
    for eid in ("EXP-ALG-009-ALIGNED", "EXP-ALG-007-REGIME", "EXP-ALG-008-PARTICIPATION"):
        variant, stem = SPEC[eid]
        config_path = f"research/configs/wp004/{stem}.json"
        config = json.loads((ROOT / config_path).read_text())
        fingerprint = deepcopy(baseline["fingerprint"])
        fingerprint.update(
            context_minutes=240,
            feature_families=["PRICE_HIGH_BREAKOUT", "DIRECTIONAL_PERSISTENCE", "PARTICIPATION"],
            feature_transformations=[
                "PRIOR_HIGH_MAXIMUM",
                "SIGNED_PRICE_EFFICIENCY",
                "RELATIVE_BASE_VOLUME",
            ],
            regime_filter="NONE" if variant == "PARTICIPATION_ONLY" else "SIGNED_EFFICIENCY_GATE",
            confirmation_filter="NONE" if variant == "REGIME_ONLY" else "RELATIVE_VOLUME_GATE",
            parameters={
                key: config[key]
                for key in (
                    "breakout_hours",
                    "volume_baseline_hours",
                    "volume_multiplier",
                    "context_increments",
                    "up_to_down_ratio",
                    "stop_fraction",
                    "target_fraction",
                )
            }
            | {"history_1h_bars": 26, "context_bars": 43, "signal_delay_hours": 0},
        )
        parents = (
            [baseline["experiment_id"]]
            if variant == "ALIGNED"
            else ["EXP-ALG-009-ALIGNED", baseline["experiment_id"]]
        )
        novelty = "REVISIT_WITH_NEW_EVIDENCE" if variant == "ALIGNED" else "MEANINGFUL_ABLATION"
        role = "ECONOMIC_CORE" if variant == "ALIGNED" else "STRUCTURAL_ABLATION"
        basis = {
            "kind": "OBSERVED_DIAGNOSTIC_WITH_STRUCTURAL_RESPONSE",
            "source_experiment_id": source["experiment_id"],
            "source_path": source["result_path"],
            "source_sha256": source["result_sha256"],
            "observations": [
                {"json_pointer": "/primary_result", "expected_value": -0.0482093869},
                {
                    "json_pointer": "/secondary_results/zero_cost_metrics/net_expectancy_r",
                    "expected_value": 0.0722123707,
                },
            ],
            "structural_response": f"{variant}: distinguish sustained upward path and unusual participation as conditional filters, retaining baseline barriers.",
            "falsifiable_prediction": "A sufficiently sampled fixed rule has positive default-cost expectancy distributed across annual development folds, with robustness to doubled costs.",
        }
        plan = [
            {
                "trial_id": f"{variant}:{profile}",
                "config_path": config_path,
                "config_sha256": sha256(ROOT / config_path),
            }
            for profile in PROFILES
        ]
        cost_profiles = {}
        for profile in PROFILES:
            cost = costs(profile)
            cost_profiles[profile] = {
                key: str(getattr(cost, key))
                for key in (
                    "entry_fee_bps",
                    "exit_fee_bps",
                    "entry_friction_bps",
                    "exit_friction_bps",
                )
            }
        prereg = {
            "schema_version": 2,
            "experiment_id": eid,
            "experiment_version": 1,
            "created_at_utc": created,
            "hypothesis": basis["falsifiable_prediction"] + f" Configuration: {variant}.",
            "rationale": basis["structural_response"],
            "research_scope": "BTCUSDT Spot LONG/no-entry; exposed development only; no optimization, sealed test, paper action, or Champion.",
            "dataset": baseline["fingerprint"]["dataset"],
            "metrics": {
                "primary": "Pooled valid resolved default-cost net expectancy R over six fixed chronological folds",
                "secondary": ["profiles", "terminal_classification", "execution_provenance"],
            },
            "evaluation_design": "DEVELOPMENT_WALK_FORWARD_V1; no fitting or fold-wise selection; ALIGNED preselected family primary; every profile and fold retained.",
            "leakage_controls": [
                features["common_eligibility"],
                features["gaps"],
                features["position_availability"],
                "216h purge /24h embargo",
                "full 24h outcome containment",
                "cutoff enforced before data inspection",
            ],
            "cost_execution_reference": "BACKTEST_ENGINE_V2 / EXECUTION_MODEL_V2 / BTCUSDT_SPOT_COST_V1",
            "parameter_space": {
                "classification": "BOUNDED_FAMILY_EXPLORATION",
                "hypothesis_role": role,
                "adaptive_decision_id": "WP004-ADAPT-001",
                "family_id": "FAM-BREAKOUT",
                "hypothesis_id": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
                "primary_family_variant": "ALIGNED",
                "parent_experiment_ids": parents,
                "novelty": novelty,
                "new_evidence_basis": basis,
                "fingerprint": fingerprint,
                "implementation_commit": commit,
                "strategy_path": "backend/app/research/continuation.py",
                "strategy_sha256": sha256(strategy),
                "trial_plan": plan,
                "dependencies": dependencies,
                "feature_definitions": features,
                "feature_definitions_sha256": sha256(features_path),
                "cost_profiles": cost_profiles,
                "walk_forward": protocol,
                "protocol_sha256": protocol_hash(protocol),
                "robustness": {
                    "cost": ["DEFAULT", "ZERO", "DOUBLE"],
                    "timing": features["timing_perturbation"],
                    "structural_ablations": list(SPEC),
                    "selection": "NO_BEST_PROFILE_SELECTION",
                },
                "metric_hierarchy": [
                    "default pooled net expectancy",
                    "count/ESS/data-quality sufficiency",
                    "fold/year/regime stability",
                    "doubled costs",
                    "timing and structural diagnostics",
                ],
                "falsification": "DEVELOPMENT_EVALUATION_V1 deterministic terminal rule; adequately sampled nonpositive default net rejects economic sufficiency, sparse evidence is inconclusive.",
                "trial_units": {
                    "core_hypotheses_shared": 1,
                    "this_structural_variant": 1,
                    "profile_trials": 4,
                    "fold_executions": 24,
                    "family_structural_variant_cap": 3,
                    "parameter_searches": 0,
                },
            },
            "trial_budget": 4,
            "stopping_rule": "Run every declared profile exactly once; preserve failures and negatives; no post-result edits or added variants.",
            "seeds": [0],
            "code_config_reference": declared_content_identity(strategy, plan),
            "status": "PREREGISTERED",
        }
        validate_identity(prereg)
        directory = ROOT / "research/experiments" / eid
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "preregistration.json"
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(prereg, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
        validate_preregistration(path)
        proposal = {
            "schema_version": 1,
            "experiment_id": eid,
            "work_package": "WP-004",
            "record_kind": "PREREGISTERED_ADMISSION",
            "strategy_label": variant,
            "family_id": "FAM-BREAKOUT",
            "hypothesis_id": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
            "hypothesis_role": role,
            "claimed_market_mechanism": basis["structural_response"],
            "fingerprint": fingerprint,
            "behavior_hash": fingerprint_hash(fingerprint),
            "structure_hash": fingerprint_hash(fingerprint, structural=True),
            "parent_experiment_ids": parents,
            "parent_family_id": "FAM-BREAKOUT",
            "novelty": novelty,
            "scientific_reason": basis["structural_response"],
            "new_evidence_basis": basis,
            "budget_units": {
                "experiments": 1,
                "strategy_variants": 1,
                "trials": 4,
                "numeric_parameter_variants": 0,
            },
            "preregistration_path": path.relative_to(ROOT).as_posix(),
            "preregistration_sha256": sha256(path),
            "result_path": (directory / "result.json").relative_to(ROOT).as_posix(),
            "outcome_reference": eid,
        }
        admit_proposal(proposal, memory)
        with (ROOT / "research/memory/SEARCH_LEDGER.jsonl").open(
            "a", encoding="utf-8", newline="\n"
        ) as handle:
            handle.write(json.dumps(proposal, separators=(",", ":"), allow_nan=False) + "\n")
        memory["entries"].append(proposal)
    validate_memory()
    (ROOT / "research/memory/RESEARCH_MAP.md").write_text(
        render_research_map(memory), encoding="utf-8"
    )
    (ROOT / "research/memory/FAILURE_MEMORY.md").write_text(
        render_failure_memory(memory), encoding="utf-8"
    )
    print("Three preregistrations and cumulative admissions created. Commit before execution.")


if __name__ == "__main__":
    main()
