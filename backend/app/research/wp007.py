"""WP-007 immutable identities, novelty gate and admission chronology.

Nothing here loads market data. The governed SEARCH_MEMORY_V2 gate runs on typed
executable specs, against both the frozen V1 reference signatures and every V2-era
admitted behaviour, before any market result exists. A non-new-root classification for
the primary variant blocks execution rather than being renamed away.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

from .continuation_lab import DATASET_HASH, DATASET_ID, PROFILES
from .evaluation_protocol import load_protocol, protocol_hash
from .flow import BALANCE, CONTEXT_MINUTES, CONTEXT_RULE, STRATEGY_VERSION, VARIANTS
from .flow_lab import config_path, validate_config
from .order_flow import DATASET_ID as FLOW_DATASET_ID
from .order_flow import FEATURE_VERSION
from .order_flow import MANIFEST_PATH as FLOW_MANIFEST_PATH
from .records import validate_preregistration
from .registry import ALLOCATIONS, admission_ledger, alias_map, registry_ledger, signatures
from .runner import declared_content_identity, sha256
from .search_memory import SearchMemoryError
from .search_memory_v2 import (
    Comparison,
    DependencyIdentity,
    ExecutableStrategySpec,
    FeaturePrimitive,
    NumericTerm,
    Rule,
    admit_executable_spec,
    bind_executable_spec,
    derived_fingerprint,
)
from .wp004 import ROOT, ancestor, first_commit, git, immutable_from_first_commit

BASE = "d92088d5ef0426bf64f34326a3224dd9aba93603"
ROOT_FAMILY = "FAM-ORDER-FLOW"
HYPOTHESIS_ID = STRATEGY_VERSION
ENTRY_EVENT = "TAKER_BUY_SHARE_CROSSES_BALANCE_IN_BUY_DOMINANT_CONTEXT"
PRIMARY_VARIANT = "FLOW_CORE"
SPEC = {
    "EXP-ALG-012-ORDERFLOW-CORE": "FLOW_CORE",
    "EXP-ALG-013-ORDERFLOW-PRICE-RESPONSE": "FLOW_PRICE_RESPONSE",
}
ROLES = {
    "FLOW_CORE": "ECONOMIC_CORE",
    "FLOW_PRICE_RESPONSE": "STRUCTURAL_CONFIRMATION_VARIANT",
}
ALLOCATION_ID = "WP007-AGGRESSIVE-BUY-FLOW-ALLOCATION"
ALLOCATION_PATH = f"research/memory/registry/allocations/{ALLOCATION_ID}.json"
FAMILY_PATH = f"research/memory/registry/families/{ROOT_FAMILY}.json"
ADMISSION_PATH = "research/memory/registry/admissions/WP007-NOVELTY-ADMISSION.json"
REJECTION_PATH = "research/memory/registry/admissions/WP007-NOVELTY-REJECTION.json"
LEDGER_PATH = "research/memory/registry/ledger/WP-007.jsonl"
OUTCOMES_PATH = "research/memory/registry/outcomes/WP-007.jsonl"
ATTEMPT_PATH = "research/runs/WP-007-ATTEMPT.json"
AMENDMENT_PATH = "research/protocols/WP-007-PREEXECUTION-AMENDMENTS.json"
INTEGRITY_PATH = "reports/validation/WP-007-ORDER-FLOW-INTEGRITY.json"
RECONCILIATION_PATH = "reports/validation/WP-007-ORDER-FLOW-RECONCILIATION.json"
NEW_ROOT_CLASSIFICATIONS = {"NEW_FAMILY"}
DESCENDANT_CLASSIFICATIONS = {"DESCENDANT_MECHANISM_CHANGE"}

# Files whose bytes determine executable behaviour; frozen before admission.
SPEC_DEPENDENCY_PATHS = (
    "backend/app/data/policy.py",
    "backend/app/backtest/models.py",
    "backend/app/backtest/engine.py",
    "backend/app/research/evaluation_protocol.py",
    "backend/app/research/source_grid.py",
    "backend/app/research/continuation_lab.py",
    "backend/app/research/order_flow.py",
    "backend/app/research/flow.py",
    "backend/app/research/flow_lab.py",
)
# The wider declared manifest frozen into each preregistration.
IMPLEMENTATION_PATHS = (
    *SPEC_DEPENDENCY_PATHS,
    "backend/app/backtest/__init__.py",
    "backend/app/research/order_flow_audit.py",
    "backend/app/research/order_flow_oracle.py",
    "backend/app/research/records.py",
    "backend/app/research/registry.py",
    "backend/app/research/runner.py",
    "backend/app/research/search_memory.py",
    "backend/app/research/search_memory_v2.py",
    "backend/app/research/wp007.py",
    "backend/tests/test_flow.py",
    "backend/tests/test_order_flow.py",
    "scripts/run_wp007.py",
    "research/design/AGGRESSIVE_BUY_FLOW_V1_DESIGN.md",
    "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json",
    ALLOCATION_PATH,
    ADMISSION_PATH,
    FAMILY_PATH,
    "docs/contracts/ORDER_FLOW_FEATURES_V1.md",
    "docs/contracts/DEVELOPMENT_EVALUATION_V1.md",
    "docs/contracts/EXECUTION_MODEL_V2.md",
    "docs/contracts/COST_MODEL_V1.md",
    "docs/contracts/RESEARCH_SEARCH_MEMORY_V2.md",
    INTEGRITY_PATH,
    RECONCILIATION_PATH,
    "uv.lock",
    "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json",
    FLOW_MANIFEST_PATH,
)


class NoveltyRejected(SearchMemoryError):
    """The governed gate refused the proposal; no market result may be produced."""


class OrderFlowGateError(SearchMemoryError):
    """The order-flow substrate is not admissible for a market experiment."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dependency_manifest(root: Path = ROOT) -> list[dict[str, str]]:
    return [{"path": path, "sha256": sha256(root / path)} for path in IMPLEMENTATION_PATHS]


def substrate_gate(root: Path = ROOT) -> dict[str, Any]:
    """No order-flow experiment may run unless integrity and reconciliation both pass."""
    integrity = read_json(root / INTEGRITY_PATH)
    reconciliation = read_json(root / RECONCILIATION_PATH)
    manifest = read_json(root / FLOW_MANIFEST_PATH)
    if integrity["status"] != "PASS" or integrity["material_violations"]:
        raise OrderFlowGateError("canonical taker-field integrity audit did not pass")
    if integrity["canonical_data_modified"] or manifest["canonical_data_modified"]:
        raise OrderFlowGateError("canonical data was modified")
    if reconciliation["status"] != "PASS" or not reconciliation["content_hash_match"]:
        raise OrderFlowGateError("independent oracle reconciliation did not pass")
    if reconciliation["accepted_1h_cross_check"]["status"] != "PASS":
        raise OrderFlowGateError("new bucketing disagrees with the accepted derived hours")
    if reconciliation["substrate_content_hash"] != manifest["content_hash"]["value"]:
        raise OrderFlowGateError("substrate identity differs from its reconciliation record")
    if manifest["integrity_audit"]["artifact_sha256"] != integrity["artifact_sha256"]:
        raise OrderFlowGateError("substrate manifest references a different integrity artifact")
    return {
        "integrity_status": integrity["status"],
        "integrity_artifact_sha256": integrity["artifact_sha256"],
        "reconciliation_status": reconciliation["status"],
        "substrate_manifest_id": manifest["manifest_id"],
        "substrate_content_hash": manifest["content_hash"]["value"],
        "eligible_1h_buckets": manifest["eligible_counts"]["1h"],
        "eligible_4h_buckets": manifest["eligible_counts"]["4h"],
    }


def _numeric_parameters() -> tuple[NumericTerm, ...]:
    return (
        NumericTerm("balance_threshold", BALANCE, "share"),
        NumericTerm("context_minutes", CONTEXT_MINUTES, "minutes"),
        NumericTerm("stop_fraction", 0.02, "fraction"),
        NumericTerm("target_fraction", 0.04, "fraction"),
    )


def executable_spec(variant: str, root: Path = ROOT) -> ExecutableStrategySpec:
    """The single typed spec used by both the novelty gate and the runner."""
    if variant not in VARIANTS:
        raise SearchMemoryError("undeclared WP-007 strategy variant")
    confirm = variant == "FLOW_PRICE_RESPONSE"
    primitives = [
        FeaturePrimitive(
            "HOURLY_TAKER_BUY_BASE_SHARE",
            "RATIO_OF_SUMMED_TAKER_BASE_TO_SUMMED_BASE_VOLUME",
            60,
            NumericTerm("bucket_minutes", 60, "minutes"),
        ),
        FeaturePrimitive(
            "LAGGED_HOURLY_TAKER_BUY_BASE_SHARE",
            "RATIO_OF_SUMMED_TAKER_BASE_TO_SUMMED_BASE_VOLUME_ENDING_ONE_HOUR_EARLIER",
            60,
            NumericTerm("bucket_minutes", 60, "minutes"),
        ),
        FeaturePrimitive(
            "NON_OVERLAPPING_CONTEXT_TAKER_BUY_BASE_SHARE",
            "RATIO_OF_SUMMED_TAKER_BASE_TO_SUMMED_BASE_VOLUME_LAST_COMPLETED_CONTEXT",
            CONTEXT_MINUTES,
            NumericTerm("context_minutes", CONTEXT_MINUTES, "minutes"),
        ),
    ]
    comparisons = [
        Comparison(
            "previous_completed_1h_taker_buy_base_share",
            "<=",
            "balance_threshold",
            NumericTerm("balance_threshold", BALANCE, "share"),
        ),
        Comparison(
            "current_completed_1h_taker_buy_base_share",
            ">",
            "balance_threshold",
            NumericTerm("balance_threshold", BALANCE, "share"),
        ),
        Comparison(
            "context_4h_taker_buy_base_share",
            ">",
            "balance_threshold",
            NumericTerm("balance_threshold", BALANCE, "share"),
        ),
    ]
    if confirm:
        primitives.append(
            FeaturePrimitive(
                "CURRENT_HOUR_PRICE_DIRECTION",
                "COMPLETED_CLOSE_MINUS_COMPLETED_OPEN",
                60,
                NumericTerm("bars", 1, "bars"),
            )
        )
        comparisons.append(
            Comparison("current_completed_1h_close", ">", "current_completed_1h_open")
        )
    return ExecutableStrategySpec(
        schema_version=2,
        root_family=ROOT_FAMILY,
        family=ROOT_FAMILY,
        entry_event=ENTRY_EVENT,
        feature_primitives=tuple(primitives),
        comparisons=tuple(comparisons),
        numeric_parameters=_numeric_parameters(),
        regime_gates=("BUY_DOMINANT_NON_OVERLAPPING_4H_CONTEXT_GATE",),
        confirmation_gates=("SAME_HOUR_PRICE_RESPONSE_GATE",) if confirm else (),
        signal_timeframe_minutes=60,
        context_timeframe_minutes=CONTEXT_MINUTES,
        direction="LONG",
        reference_price_rule="LATEST_COMPLETED_1H_CLOSE",
        stop=Rule("FIXED_PERCENT_OF_SIGNAL_CLOSE", NumericTerm("stop_fraction", 0.02, "fraction")),
        exit=Rule(
            "FIXED_TARGET_OR_STOP_OR_HORIZON", NumericTerm("target_fraction", 0.04, "fraction")
        ),
        holding_horizon_minutes=1440,
        timing_perturbation="SIGNAL_DELAY_HOURS_0",
        position_policy="SINGLE_LONG_NO_OVERLAP",
        execution_model_reference="EXECUTION_MODEL_V2",
        cost_model_reference="BTCUSDT_SPOT_COST_V1",
        dataset={
            "content_hash": DATASET_HASH,
            "manifest_id": DATASET_ID,
            "maximum_timestamp": "2024-12-31T23:59:00Z",
            "feature_manifest_id": FLOW_DATASET_ID,
            "feature_version": FEATURE_VERSION,
            "context_rule": CONTEXT_RULE,
        },
        implementation_dependencies=tuple(
            DependencyIdentity(path, sha256(root / path)) for path in SPEC_DEPENDENCY_PATHS
        ),
        config_dependencies=(
            DependencyIdentity(config_path(variant), sha256(root / config_path(variant))),
        ),
    )


def novelty_decision(root: Path = ROOT) -> dict[str, Any]:
    """Submit both variants to the governed gate; a non-new primary root blocks execution."""
    aliases = alias_map(root, exclude=ROOT_FAMILY)
    collisions = sorted({ROOT_FAMILY, ENTRY_EVENT} & set(aliases))
    if collisions:
        raise NoveltyRejected(
            f"proposed root family or entry event collides with a registered anchor: {collisions}"
        )
    # Reproduction after preregistration must compare against the same prior corpus
    # used at admission, not against WP-007's own append-only ledger entries.
    known = signatures(root, exclude_experiment_ids=set(SPEC))
    reference = {"v1_reference_translations": 9, "v2_admitted_behaviours": len(known) - 9}
    variants = []
    for experiment_id, variant in SPEC.items():
        spec = executable_spec(variant, root)
        binding = bind_executable_spec(
            spec, declared_fingerprint=derived_fingerprint(spec), runtime_spec=spec
        )
        decision = admit_executable_spec(
            spec,
            declared_family=ROOT_FAMILY,
            declared_fingerprint=derived_fingerprint(spec),
            signatures=known,
            aliases=aliases,
            declared_behavior_hash=binding.behavior_hash,
            runtime_spec=spec,
            family_budget_remaining=True,
        )
        classification = decision["classification"]
        allowed = (
            NEW_ROOT_CLASSIFICATIONS
            if variant == PRIMARY_VARIANT
            else NEW_ROOT_CLASSIFICATIONS | DESCENDANT_CLASSIFICATIONS
        )
        if classification not in allowed:
            raise NoveltyRejected(
                f"{experiment_id} classified {classification}; execution is blocked"
            )
        variants.append(
            {
                "experiment_id": experiment_id,
                "variant": variant,
                "hypothesis_role": ROLES[variant],
                "classification": classification,
                "matched_experiment_ids": decision["matched_experiment_ids"],
                "behavior_hash": binding.behavior_hash,
                "structural_hash": binding.structural_hash,
                "executable_spec_hash": binding.executable_spec_hash,
                "dependency_hash": binding.dependency_hash,
                "spec": spec.to_dict(),
            }
        )
        known = [
            *known,
            {
                "experiment_id": experiment_id,
                "root_family": ROOT_FAMILY,
                "behavior_hash": binding.behavior_hash,
                "structural_hash": binding.structural_hash,
            },
        ]
    return {
        "schema_version": 1,
        "version": "SEARCH_MEMORY_V2",
        "work_package": "WP-007",
        "gate": "GOVERNED_NOVELTY_ADMISSION_BEFORE_ANY_MARKET_RESULT",
        "proposed_root_family": ROOT_FAMILY,
        "proposed_hypothesis_id": HYPOTHESIS_ID,
        "entry_event": ENTRY_EVENT,
        "reference_signatures": reference,
        "conflicting_root_check": {
            "registered_aliases_and_anchors": len(aliases),
            "collisions": [],
            "prior_family_budgets": "UNCHANGED_AND_NOT_REOPENED",
        },
        "family_classification": "NEW_FAMILY",
        "admitted": True,
        "classifier_modified": False,
        "renamed_to_force_novelty": False,
        "conditions_added_to_force_novelty": False,
        "market_results_observed_at_admission": 0,
        "variants": variants,
    }


def validate_admission(root: Path = ROOT) -> dict[str, Any]:
    """The committed gate record must reproduce exactly from the frozen specs."""
    recorded = read_json(root / ADMISSION_PATH)
    if recorded != json.loads(json.dumps(novelty_decision(root))):
        raise SearchMemoryError("novelty admission record differs from the deterministic gate")
    if recorded["family_classification"] not in NEW_ROOT_CLASSIFICATIONS:
        raise SearchMemoryError("admitted family is not an explicit new root")
    return recorded


def validate_allocation(root: Path = ROOT) -> dict[str, Any]:
    allocation = read_json(root / ALLOCATION_PATH)
    required = {
        "schema_version": 1,
        "allocation_id": ALLOCATION_ID,
        "work_package": "WP-007",
        "kind": "RESULT_DEPENDENT_NEW_FAMILY_ALLOCATION",
        "root_family": ROOT_FAMILY,
        "hypothesis_id": HYPOTHESIS_ID,
        "primary_variant": PRIMARY_VARIANT,
        "new_economic_hypotheses": 1,
        "strategy_variants": 2,
        "numeric_parameter_variants": 0,
        "profiles_per_variant": 4,
        "profile_evaluations": 8,
        "adaptive_decision_increment": 1,
        "result_dependent_fork_increment": 1,
        "prior_adaptive_decisions": 3,
        "prior_result_dependent_forks": 3,
        "cumulative_adaptive_decisions": 4,
        "cumulative_result_dependent_forks": 4,
        "parameter_searches": 0,
        "threshold_searches": 0,
        "sealed_queries": 0,
        "paper_observations": 0,
        "additional_controls_or_seeds": 0,
    }
    if any(allocation.get(key) != value for key, value in required.items()):
        raise SearchMemoryError("WP-007 allocation differs from the frozen authorization")
    if allocation["profiles"] != list(PROFILES) or sorted(allocation["experiment_ids"]) != sorted(
        SPEC
    ):
        raise SearchMemoryError("WP-007 allocation authorizes a different profile or variant set")
    if allocation["family_limits"] != {
        "experiments": 2,
        "strategy_variants": 2,
        "trials": 8,
        "numeric_parameter_variants": 0,
    }:
        raise SearchMemoryError("WP-007 family limits differ from the allocation")
    if allocation["prior_family_budget_policy"] != (
        "FAM-BREAKOUT stays exhausted, FAM-PULLBACK-RECOVERY stays consumed and parked, and "
        "ALIGNED stays parked at INCONCLUSIVE. This allocation creates a new root and resets "
        "nothing."
    ):
        raise SearchMemoryError("WP-007 allocation weakened a prior family disposition")
    return allocation


def validate_family_record(root: Path = ROOT) -> dict[str, Any]:
    family = read_json(root / FAMILY_PATH)
    if family["family_id"] != ROOT_FAMILY or family["parent_family_id"] is not None:
        raise SearchMemoryError("WP-007 family record changed the admitted root identity")
    if family["entry_event_anchors"] != [ENTRY_EVENT]:
        raise SearchMemoryError("WP-007 family record changed its entry-event anchor")
    if family["allocation_id"] != ALLOCATION_ID or family["admitted_by"] != ADMISSION_PATH:
        raise SearchMemoryError("WP-007 family record is not bound to its governed admission")
    entries = registry_ledger(root)
    if {entry["root_family"] for entry in entries} - {ROOT_FAMILY}:
        raise SearchMemoryError("the WP-007 registry ledger admits an unallocated family")
    return family


def validate_ledger(root: Path = ROOT) -> dict[str, int]:
    """Admissions never exceed the allocation and never restore a consumed budget."""
    schema = read_json(root / "contracts/search_ledger_v2.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    admission = read_json(root / ADMISSION_PATH)
    admitted = {item["experiment_id"]: item for item in admission["variants"]}
    seen: set[str] = set()
    entries = registry_ledger(root)
    for entry in entries:
        validator.validate(entry)
        experiment_id = entry["experiment_id"]
        if experiment_id in seen or experiment_id not in admitted:
            raise SearchMemoryError("unadmitted or duplicated WP-007 admission")
        reference = admitted[experiment_id]
        if any(entry[key] != reference[key] for key in ("behavior_hash", "executable_spec_hash")):
            raise SearchMemoryError("WP-007 admission identity differs from the governed gate")
        if entry["root_family"] != ROOT_FAMILY or entry["hypothesis_id"] != HYPOTHESIS_ID:
            raise SearchMemoryError("WP-007 admission changed the admitted family or hypothesis")
        prereg = root / entry["preregistration_path"]
        if not prereg.is_file() or sha256(prereg) != entry["preregistration_sha256"]:
            raise SearchMemoryError("WP-007 admission preregistration identity mismatch")
        seen.add(experiment_id)
    limits = read_json(root / ALLOCATION_PATH)["family_limits"]
    counts = {
        "experiments": len(entries),
        "strategy_variants": sum(item["budget_units"]["strategy_variants"] for item in entries),
        "trials": sum(item["budget_units"]["trials"] for item in entries),
        "numeric_parameter_variants": sum(
            item["budget_units"]["numeric_parameter_variants"] for item in entries
        ),
    }
    for field, limit in limits.items():
        if counts[field] > limit:
            raise SearchMemoryError(f"WP-007 {field} budget exceeded")
    prior = {item["experiment_id"] for item in admission_ledger(root)} - set(SPEC)
    if len(prior) != 2:
        raise SearchMemoryError("a prior work package's admissions changed")
    return counts


def effective_preregistration(experiment_id: str, root: Path = ROOT) -> Path:
    """Resolve the prospectively corrected, zero-result WP-007 declaration."""
    registry = read_json(root / AMENDMENT_PATH)
    if (
        registry["kind"] != "PRE_EXECUTION_NOVELTY_SELF_REFERENCE_CORRECTION"
        or registry["strategy_trials_before_amendment"] != 0
        or registry["results_observed_before_amendment"] != 0
        or registry["additional_strategy_variants"] != 0
        or registry["additional_profile_trials"] != 0
        or registry["additional_numeric_parameter_variants"] != 0
        or set(registry["amendments"]) != set(SPEC)
    ):
        raise SearchMemoryError("invalid WP-007 pre-execution supersession registry")
    item = registry["amendments"][experiment_id]
    expected = f"research/experiments/{experiment_id}/preregistration.v2.json"
    superseded = root / f"research/experiments/{experiment_id}/preregistration.json"
    if item["effective_path"] != expected or item["superseded_sha256"] != sha256(superseded):
        raise SearchMemoryError("superseded WP-007 preregistration identity changed")
    path = root / expected
    if sha256(path) != item["effective_sha256"]:
        raise SearchMemoryError("effective WP-007 preregistration identity changed")
    return path


def validate_identity(prereg: dict[str, Any], root: Path = ROOT) -> None:
    """The preregistration must bind to the exact admitted spec, config and protocol."""
    experiment_id = prereg["experiment_id"]
    if experiment_id not in SPEC:
        raise SearchMemoryError("unallocated WP-007 experiment")
    variant = SPEC[experiment_id]
    space = prereg["parameter_space"]
    relative = config_path(variant)
    config = read_json(root / relative)
    validate_config(config)
    if config["variant"] != variant:
        raise SearchMemoryError("experiment maps to a different structural variant")
    expected_plan = [
        {
            "trial_id": f"{variant}:{profile}",
            "config_path": relative,
            "config_sha256": sha256(root / relative),
        }
        for profile in PROFILES
    ]
    if (
        space["trial_plan"] != expected_plan
        or prereg["trial_budget"] != 4
        or prereg["seeds"] != [0]
    ):
        raise SearchMemoryError("undeclared variant/profile/configuration trial")
    if space["dependencies"] != dependency_manifest(root):
        raise SearchMemoryError("implementation dependency identity mismatch")
    strategy_path = root / "backend/app/research/flow.py"
    if (
        space["strategy_path"] != "backend/app/research/flow.py"
        or space["strategy_sha256"] != sha256(strategy_path)
        or declared_content_identity(strategy_path, expected_plan)
        != prereg["code_config_reference"]
    ):
        raise SearchMemoryError("strategy content identity mismatch")
    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    if space["walk_forward"] != protocol or space["protocol_sha256"] != protocol_hash(protocol):
        raise SearchMemoryError("walk-forward freeze mismatch")
    if space["root_family"] != ROOT_FAMILY or space["hypothesis_id"] != HYPOTHESIS_ID:
        raise SearchMemoryError("strategy family lineage mismatch")
    if space["primary_family_variant"] != PRIMARY_VARIANT:
        raise SearchMemoryError("primary family hypothesis changed")
    if space["allocation_id"] != ALLOCATION_ID or space["numeric_parameter_searches"] != 0:
        raise SearchMemoryError("undeclared allocation or parameter search")
    if space["balance_threshold"] != BALANCE or space["threshold_searches"] != 0:
        raise SearchMemoryError("the balance threshold was searched or changed")
    if space["context_rule"] != CONTEXT_RULE:
        raise SearchMemoryError("the non-overlapping context rule changed")
    if space["feature_substrate"]["manifest_id"] != FLOW_DATASET_ID:
        raise SearchMemoryError("preregistered feature substrate identity changed")
    spec = executable_spec(variant, root)
    binding = bind_executable_spec(spec, declared_fingerprint=space["executable_spec_fingerprint"])
    if (
        space["executable_spec"] != json.loads(json.dumps(spec.to_dict()))
        or space["executable_spec_hash"] != binding.executable_spec_hash
        or space["behavior_hash"] != binding.behavior_hash
        or space["structural_hash"] != binding.structural_hash
        or space["dependency_hash"] != binding.dependency_hash
    ):
        raise SearchMemoryError("preregistered executable spec differs from the admitted spec")


def preflight(root: Path = ROOT) -> dict[str, Any]:
    """Must complete before the runner loads development arrays or computes a signal."""
    if git("branch", "--show-current", root=root) != "main":
        raise SearchMemoryError("WP-007 must execute on main")
    if git("status", "--porcelain", root=root):
        raise SearchMemoryError("commit all scientific declarations before market execution")
    head = git("rev-parse", "HEAD", root=root)
    if not ancestor(BASE, head, root):
        raise SearchMemoryError("required WP-007 starting HEAD is not in ancestry")
    substrate = substrate_gate(root)
    validate_allocation(root)
    validate_family_record(root)
    admission = validate_admission(root)
    admission_commit = immutable_from_first_commit(ADMISSION_PATH, root)
    for dependency in SPEC_DEPENDENCY_PATHS:
        commit = first_commit(dependency, root)
        if commit == admission_commit or not ancestor(commit, admission_commit, root):
            raise SearchMemoryError("executable behaviour must be committed before admission")
    records: dict[str, str] = {}
    pre_commits: set[str] = set()
    for experiment_id in SPEC:
        directory = root / "research/experiments" / experiment_id
        if any((directory / name).exists() for name in ("result.json", "trials.json")):
            raise SearchMemoryError("WP-007 execution cannot overwrite or repeat an observed trial")
        original = f"research/experiments/{experiment_id}/preregistration.json"
        original_commit = immutable_from_first_commit(original, root)
        if original_commit == admission_commit or not ancestor(
            admission_commit, original_commit, root
        ):
            raise SearchMemoryError("preregistration must follow the governed novelty admission")
        effective = effective_preregistration(experiment_id, root)
        prereg = validate_preregistration(effective)
        validate_identity(prereg, root)
        commit = immutable_from_first_commit(effective.relative_to(root).as_posix(), root)
        if commit == original_commit or not ancestor(original_commit, commit, root):
            raise SearchMemoryError("effective preregistration must follow the superseded one")
        records[experiment_id] = sha256(effective)
        pre_commits.add(commit)
    if len(pre_commits) != 1:
        raise SearchMemoryError("both WP-007 preregistrations must be frozen together")
    counts = validate_ledger(root)
    if counts["experiments"] != 2 or counts["trials"] != 8 or counts["strategy_variants"] != 2:
        raise SearchMemoryError("both variants must be admitted before any result")
    if (root / ATTEMPT_PATH).exists():
        raise SearchMemoryError("an execution attempt already exists; reruns are not implicit")
    return {
        "status": "PASS",
        "execution_commit": head,
        "admission_commit": admission_commit,
        "preregistration_commit": pre_commits.pop(),
        "preregistration_hashes": records,
        "family_classification": admission["family_classification"],
        "order_flow_substrate": substrate,
        "wp007_accounting": counts,
        "dependency_manifest_sha256": hashlib.sha256(
            json.dumps(dependency_manifest(root), sort_keys=True).encode()
        ).hexdigest(),
    }


ALLOCATION_DIRECTORY = ALLOCATIONS
