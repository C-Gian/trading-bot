"""Freeze both WP-006 preregistrations and V2 admissions; never touches market tables."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.continuation_lab import PROFILES, costs
from app.research.evaluation_protocol import load_protocol, protocol_hash
from app.research.pullback import FEATURE_VERSION
from app.research.pullback_lab import config_path
from app.research.records import validate_preregistration
from app.research.runner import declared_content_identity, sha256
from app.research.search_memory_v2 import bind_executable_spec, derived_fingerprint
from app.research.wp006 import (
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
    validate_admission,
    validate_allocation,
    validate_identity,
    validate_ledger,
    validate_registry,
)

STRATEGY_PATH = "backend/app/research/pullback.py"
MECHANISM = {
    "RECOVERY_CORE": (
        "An hourly close recovering above its one-day mean after the previous hour sat at or "
        "below it may mark the end of a temporary countertrend pullback inside an already "
        "persistent uptrend, giving a better continuation entry than buying a fresh high."
    ),
    "RECOVERY_CONFIRM": (
        "The same recovery transition, additionally requiring the current close to exceed the "
        "previous hour's high, to test whether immediate confirmation of the turn helps or "
        "merely re-imports lateness."
    ),
}
PREDICTION = (
    "A sufficiently sampled fixed recovery rule has positive default-cost expectancy distributed "
    "across the six annual development folds, with robustness to doubled costs."
)


def main() -> None:
    if git("status", "--porcelain") or git("branch", "--show-current") != "main":
        raise ValueError("commit the admitted implementation on main before preregistration")
    if any((ROOT / f"research/experiments/{eid}/preregistration.json").exists() for eid in SPEC):
        raise FileExistsError("a WP-006 preregistration already exists")
    if (ROOT / LEDGER_PATH).exists():
        raise FileExistsError("the WP-006 admission ledger already exists")
    validate_allocation()
    validate_registry()
    admission = validate_admission()
    admitted = {item["experiment_id"]: item for item in admission["variants"]}
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
        parents = [] if variant == PRIMARY_VARIANT else ["EXP-ALG-010-PULLBACK-RECOVERY-CORE"]
        prereg = {
            "schema_version": 2,
            "experiment_id": experiment_id,
            "experiment_version": 1,
            "created_at_utc": created,
            "hypothesis": f"{PREDICTION} Configuration: {variant}.",
            "rationale": MECHANISM[variant],
            "research_scope": (
                "BTCUSDT Spot LONG/no-entry; exposed development only; no optimization, sealed "
                "query, paper action or Champion."
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
                "or fold-wise selection; RECOVERY_CORE is the preselected family primary; every "
                "profile and fold is retained."
            ),
            "leakage_controls": [
                "only completed contiguous 1h and 4h observations at signal time",
                "inherited source-grid quarantine; no forward fill or manufactured bar",
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
                "novelty_admission_record": "research/memory/WP006-NOVELTY-ADMISSION.json",
                "executable_spec": spec.to_dict(),
                "executable_spec_fingerprint": derived_fingerprint(spec),
                "executable_spec_hash": binding.executable_spec_hash,
                "behavior_hash": binding.behavior_hash,
                "structural_hash": binding.structural_hash,
                "dependency_hash": binding.dependency_hash,
                "feature_version": FEATURE_VERSION,
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
                    "fold/year/regime stability",
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
                "post-result edits, added variants or added profiles."
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
                "work_package": "WP-006",
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
    with (ROOT / LEDGER_PATH).open("x", encoding="utf-8", newline="\n") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, separators=(",", ":"), allow_nan=False) + "\n")
    counts = validate_ledger()
    print(
        f"Two preregistrations and V2 admissions created: {counts['experiments']} experiments, "
        f"{counts['trials']} profile trials, {counts['numeric_parameter_variants']} numeric "
        "variants. Commit before execution."
    )


if __name__ == "__main__":
    main()
