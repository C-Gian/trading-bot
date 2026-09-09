"""Freeze both WP-007 preregistrations and admissions; never touches market tables."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.continuation_lab import PROFILES, costs
from app.research.evaluation_protocol import load_protocol, protocol_hash
from app.research.flow import BALANCE, CONTEXT_RULE
from app.research.flow_lab import config_path
from app.research.order_flow import FEATURE_VERSION
from app.research.order_flow import MANIFEST_PATH as FLOW_MANIFEST_PATH
from app.research.records import validate_preregistration
from app.research.runner import declared_content_identity, sha256
from app.research.search_memory_v2 import bind_executable_spec, derived_fingerprint
from app.research.wp007 import (
    ALLOCATION_ID,
    HYPOTHESIS_ID,
    LEDGER_PATH,
    PRIMARY_VARIANT,
    ROLES,
    ROOT_FAMILY,
    SPEC,
    dependency_manifest,
    executable_spec,
    git,
    read_json,
    substrate_gate,
    validate_admission,
    validate_allocation,
    validate_family_record,
    validate_identity,
    validate_ledger,
)

STRATEGY_PATH = "backend/app/research/flow.py"
MECHANISM = {
    "FLOW_CORE": (
        "A transition from non-dominant to dominant exchange-reported taker buying in the "
        "just-completed 1h bar, when the most recently available non-overlapping completed 4h "
        "context is already buy-dominant, may indicate renewed aggressive demand with enough "
        "next-day continuation to survive BTCUSDT Spot friction."
    ),
    "FLOW_PRICE_RESPONSE": (
        "The same flow transition, additionally requiring the completed hour to close above its "
        "open, to test whether the transition is more informative when price responded positively "
        "during the same hour or whether confirmation only reduces coverage."
    ),
}
PREDICTION = (
    "A sufficiently sampled fixed order-flow transition rule has positive default-cost expectancy "
    "distributed across the six annual development folds, with robustness to doubled costs."
)


def main() -> None:
    if git("status", "--porcelain") or git("branch", "--show-current") != "main":
        raise ValueError("commit the admitted implementation on main before preregistration")
    if any((ROOT / f"research/experiments/{eid}/preregistration.json").exists() for eid in SPEC):
        raise FileExistsError("a WP-007 preregistration already exists")
    if (ROOT / LEDGER_PATH).exists():
        raise FileExistsError("the WP-007 admission ledger already exists")
    substrate = substrate_gate()
    validate_allocation()
    validate_family_record()
    admission = validate_admission()
    admitted = {item["experiment_id"]: item for item in admission["variants"]}
    flow_manifest = read_json(ROOT / FLOW_MANIFEST_PATH)
    protocol = load_protocol()
    created = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    commit = git("rev-parse", "HEAD")
    dependencies = dependency_manifest()
    strategy = ROOT / STRATEGY_PATH
    cost_profiles = {
        profile: {
            key: str(getattr(costs(profile), key))
            for key in (
                "entry_fee_bps",
                "exit_fee_bps",
                "entry_friction_bps",
                "exit_friction_bps",
            )
        }
        for profile in PROFILES
    }
    entries = []
    for experiment_id, variant in SPEC.items():
        spec = executable_spec(variant)
        binding = bind_executable_spec(spec, declared_fingerprint=derived_fingerprint(spec))
        reference = admitted[experiment_id]
        relative = config_path(variant)
        plan = [
            {
                "trial_id": f"{variant}:{profile}",
                "config_path": relative,
                "config_sha256": sha256(ROOT / relative),
            }
            for profile in PROFILES
        ]
        parents = [] if variant == PRIMARY_VARIANT else ["EXP-ALG-012-ORDERFLOW-CORE"]
        prereg = {
            "schema_version": 2,
            "experiment_id": experiment_id,
            "experiment_version": 1,
            "created_at_utc": created,
            "hypothesis": f"{PREDICTION} Configuration: {variant}.",
            "rationale": MECHANISM[variant],
            "research_scope": (
                "BTCUSDT Spot LONG/no-entry; exposed development only; no optimization, threshold "
                "search, sealed query, paper action or Champion."
            ),
            "dataset": {
                "manifest_id": spec.dataset["manifest_id"],
                "content_hash": spec.dataset["content_hash"],
                "maximum_timestamp": spec.dataset["maximum_timestamp"],
            },
            "metrics": {
                "primary": (
                    "Pooled valid resolved default-cost net expectancy R over six fixed "
                    "chronological folds"
                ),
                "secondary": ["profiles", "terminal_classification", "execution_provenance"],
            },
            "evaluation_design": (
                "DEVELOPMENT_EVALUATION_V1 / DEVELOPMENT_WALK_FORWARD_V1, unchanged; no fitting "
                "or fold-wise selection; FLOW_CORE is the preselected family primary; every "
                "profile and fold is retained."
            ),
            "leakage_controls": [
                "only completed, unquarantined, traded order-flow buckets at signal time",
                "the 4h context closes at or before the current signal hour opens",
                "inherited source-grid quarantine; no forward fill or manufactured bucket",
                "position availability blocks overlapping entries",
                "216h purge / 24h embargo",
                "full 24h outcome containment",
                "cutoff enforced before any data inspection",
            ],
            "cost_execution_reference": (
                "BACKTEST_ENGINE_V2 / EXECUTION_MODEL_V2 / BTCUSDT_SPOT_COST_V1"
            ),
            "parameter_space": {
                "classification": "BOUNDED_NEW_FAMILY_EXPLORATION",
                "hypothesis_role": ROLES[variant],
                "allocation_id": ALLOCATION_ID,
                "root_family": ROOT_FAMILY,
                "hypothesis_id": HYPOTHESIS_ID,
                "primary_family_variant": PRIMARY_VARIANT,
                "parent_experiment_ids": parents,
                "novelty": reference["classification"],
                "novelty_admission_record": (
                    "research/memory/registry/admissions/WP007-NOVELTY-ADMISSION.json"
                ),
                "balance_threshold": BALANCE,
                "threshold_searches": 0,
                "context_rule": CONTEXT_RULE,
                "feature_version": FEATURE_VERSION,
                "feature_substrate": {
                    "manifest_id": flow_manifest["manifest_id"],
                    "content_hash": flow_manifest["content_hash"]["value"],
                    "eligible_1h_buckets": flow_manifest["eligible_counts"]["1h"],
                    "eligible_4h_buckets": flow_manifest["eligible_counts"]["4h"],
                    "integrity_artifact_sha256": substrate["integrity_artifact_sha256"],
                },
                # Validate the exact JSON representation that will be persisted. The
                # dataclass form contains tuples, while JSON arrays load back as lists.
                "executable_spec": json.loads(json.dumps(spec.to_dict())),
                "executable_spec_fingerprint": derived_fingerprint(spec),
                "executable_spec_hash": binding.executable_spec_hash,
                "behavior_hash": binding.behavior_hash,
                "structural_hash": binding.structural_hash,
                "dependency_hash": binding.dependency_hash,
                "implementation_commit": commit,
                "strategy_path": STRATEGY_PATH,
                "strategy_sha256": sha256(strategy),
                "trial_plan": plan,
                "dependencies": dependencies,
                "cost_profiles": cost_profiles,
                "walk_forward": protocol,
                "protocol_sha256": protocol_hash(protocol),
                "robustness": {
                    "cost": ["DEFAULT", "ZERO", "DOUBLE"],
                    "timing": "SIGNAL_DELAY_1H_CONDITION_ONLY_REFERENCE_UNCHANGED",
                    "structural_variants": list(SPEC),
                    "selection": "NO_BEST_PROFILE_OR_VARIANT_SELECTION",
                },
                "metric_hierarchy": [
                    "default pooled net expectancy",
                    "count/ESS/data-quality sufficiency",
                    "fold/year stability",
                    "doubled costs",
                    "timing and confirmation diagnostics",
                ],
                "falsification": (
                    "DEVELOPMENT_EVALUATION_V1 deterministic terminal rule; an adequately sampled "
                    "nonpositive default net expectancy rejects economic sufficiency, sparse "
                    "evidence is inconclusive. Profitability is not a structural PASS gate."
                ),
                "numeric_parameter_searches": 0,
                "trial_units": {
                    "core_hypotheses_shared": 1,
                    "this_structural_variant": 1,
                    "profile_trials": 4,
                    "fold_executions": 24,
                    "family_structural_variant_cap": 2,
                    "parameter_searches": 0,
                },
            },
            "trial_budget": 4,
            "stopping_rule": (
                "Run every declared profile exactly once; preserve failures and negatives; no "
                "post-result edits, added variants, added profiles or threshold changes."
            ),
            "seeds": [0],
            "code_config_reference": declared_content_identity(strategy, plan),
            "status": "PREREGISTERED",
        }
        validate_identity(prereg)
        directory = ROOT / "research/experiments" / experiment_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "preregistration.json"
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(prereg, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
        validate_preregistration(path)
        entries.append(
            {
                "schema_version": 2,
                "experiment_id": experiment_id,
                "work_package": "WP-007",
                "record_kind": "PREREGISTERED_ADMISSION",
                "strategy_label": variant,
                "root_family": ROOT_FAMILY,
                "hypothesis_id": HYPOTHESIS_ID,
                "hypothesis_role": ROLES[variant],
                "claimed_market_mechanism": MECHANISM[variant],
                "allocation_id": ALLOCATION_ID,
                "classification": reference["classification"],
                "matched_experiment_ids": reference["matched_experiment_ids"],
                "behavior_hash": binding.behavior_hash,
                "structural_hash": binding.structural_hash,
                "executable_spec_hash": binding.executable_spec_hash,
                "dependency_hash": binding.dependency_hash,
                "parent_experiment_ids": parents,
                "novelty": reference["classification"],
                "scientific_reason": MECHANISM[variant],
                "budget_units": {
                    "experiments": 1,
                    "strategy_variants": 1,
                    "trials": 4,
                    "numeric_parameter_variants": 0,
                },
                "preregistration_path": path.relative_to(ROOT).as_posix(),
                "preregistration_sha256": sha256(path),
                "result_path": (directory / "result.json").relative_to(ROOT).as_posix(),
                "outcome_reference": experiment_id,
            }
        )
    ledger = ROOT / LEDGER_PATH
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("x", encoding="utf-8", newline="\n") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, separators=(",", ":"), allow_nan=False) + "\n")
    counts = validate_ledger()
    print(
        f"Two preregistrations and admissions created: {counts['experiments']} experiments, "
        f"{counts['trials']} profile trials, {counts['numeric_parameter_variants']} numeric "
        "variants. Commit before execution."
    )


if __name__ == "__main__":
    main()
