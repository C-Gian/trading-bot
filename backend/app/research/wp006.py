"""WP-006 immutable identities, novelty gate and admission chronology.

Nothing here loads market data. The governed SEARCH_MEMORY_V2 gate runs on typed
executable specs before any market result exists, and a non-new-root classification
blocks execution rather than being renamed away.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

from .continuation_lab import DATASET_HASH, DATASET_ID, PROFILES
from .evaluation_protocol import load_protocol, protocol_hash
from .pullback import (
    CONTEXT_INCREMENTS,
    SMA_HOURS,
    STRATEGY_VERSION,
    UP_TO_DOWN_RATIO,
    VARIANTS,
)
from .pullback_lab import config_path, validate_config
from .records import validate_preregistration
from .runner import declared_content_identity, sha256
from .search_memory import SearchMemoryError, load_memory
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

BASE = "444172a359e2663887624da82254cc2185ff85e1"
ROOT_FAMILY = "FAM-PULLBACK-RECOVERY"
HYPOTHESIS_ID = STRATEGY_VERSION
ENTRY_EVENT = "CLOSE_RECOVERS_ABOVE_DAILY_MEAN_AFTER_PULLBACK"
PRIMARY_VARIANT = "RECOVERY_CORE"
SPEC = {
    "EXP-ALG-010-PULLBACK-RECOVERY-CORE": "RECOVERY_CORE",
    "EXP-ALG-011-PULLBACK-RECOVERY-CONFIRM": "RECOVERY_CONFIRM",
}
ROLES = {
    "RECOVERY_CORE": "ECONOMIC_CORE",
    "RECOVERY_CONFIRM": "STRUCTURAL_CONFIRMATION_VARIANT",
}
ALLOCATION_ID = "WP006-PULLBACK-RECOVERY-ALLOCATION"
ALLOCATION_PATH = "research/memory/WP006-PULLBACK-RECOVERY-ALLOCATION.json"
REGISTRY_PATH = "research/memory/FAMILY_REGISTRY_V2.json"
BUDGET_PATH = "research/memory/SEARCH_BUDGET_V2.json"
ADMISSION_PATH = "research/memory/WP006-NOVELTY-ADMISSION.json"
LEDGER_PATH = "research/memory/ADMISSION_LEDGER_V2.jsonl"
OUTCOMES_PATH = "research/memory/OUTCOMES_V2.jsonl"
ATTEMPT_PATH = "research/runs/WP-006-ATTEMPT.json"
AMENDMENT_PATH = "research/protocols/WP-006-PREEXECUTION-AMENDMENTS.json"
NEW_ROOT_CLASSIFICATIONS = {"NEW_FAMILY"}
DESCENDANT_CLASSIFICATIONS = {"DESCENDANT_MECHANISM_CHANGE"}

# Files whose bytes determine executable behaviour; frozen before admission.
SPEC_DEPENDENCY_PATHS = (
    "backend/app/data/policy.py",
    "backend/app/backtest/models.py",
    "backend/app/backtest/engine.py",
    "backend/app/research/evaluation_protocol.py",
    "backend/app/research/source_grid.py",
    "backend/app/research/continuation.py",
    "backend/app/research/continuation_lab.py",
    "backend/app/research/pullback.py",
    "backend/app/research/pullback_lab.py",
)
# The wider declared manifest frozen into each preregistration.
IMPLEMENTATION_PATHS = (
    *SPEC_DEPENDENCY_PATHS,
    "backend/app/backtest/__init__.py",
    "backend/app/research/records.py",
    "backend/app/research/runner.py",
    "backend/app/research/search_memory.py",
    "backend/app/research/search_memory_v2.py",
    "backend/app/research/wp006.py",
    "backend/tests/test_pullback.py",
    "scripts/run_wp006.py",
    "research/design/PULLBACK_RECOVERY_V1_DESIGN.md",
    "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json",
    "research/memory/SEARCH_BUDGET_V2.json",
    "research/memory/FAMILY_REGISTRY_V2.json",
    ALLOCATION_PATH,
    ADMISSION_PATH,
    "docs/contracts/DEVELOPMENT_EVALUATION_V1.md",
    "docs/contracts/EXECUTION_MODEL_V2.md",
    "docs/contracts/COST_MODEL_V1.md",
    "docs/contracts/RESEARCH_SEARCH_MEMORY_V2.md",
    "uv.lock",
    "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json",
)


class NoveltyRejected(SearchMemoryError):
    """The governed gate refused the proposal; no market result may be produced."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dependency_manifest(root: Path = ROOT) -> list[dict[str, str]]:
    return [{"path": path, "sha256": sha256(root / path)} for path in IMPLEMENTATION_PATHS]


def _numeric_parameters() -> tuple[NumericTerm, ...]:
    return (
        NumericTerm("sma_hours", SMA_HOURS, "hours"),
        NumericTerm("context_increments", CONTEXT_INCREMENTS, "increments"),
        NumericTerm("up_to_down_ratio", UP_TO_DOWN_RATIO, "ratio"),
        NumericTerm("stop_fraction", 0.02, "fraction"),
        NumericTerm("target_fraction", 0.04, "fraction"),
    )


def executable_spec(variant: str, root: Path = ROOT) -> ExecutableStrategySpec:
    """The single typed spec used by both the novelty gate and the runner."""
    if variant not in VARIANTS:
        raise SearchMemoryError("undeclared WP-006 strategy variant")
    confirm = variant == "RECOVERY_CONFIRM"
    primitives = [
        FeaturePrimitive(
            "HOURLY_MEAN_LEVEL",
            "ARITHMETIC_MEAN_OF_COMPLETED_CLOSES",
            60,
            NumericTerm("sma_hours", SMA_HOURS, "hours"),
        ),
        FeaturePrimitive(
            "LAGGED_HOURLY_MEAN_LEVEL",
            "ARITHMETIC_MEAN_OF_COMPLETED_CLOSES_ENDING_ONE_HOUR_EARLIER",
            60,
            NumericTerm("sma_hours", SMA_HOURS, "hours"),
        ),
        FeaturePrimitive(
            "DIRECTIONAL_PERSISTENCE",
            "SIGNED_PRICE_EFFICIENCY",
            240,
            NumericTerm("context_increments", CONTEXT_INCREMENTS, "increments"),
        ),
    ]
    comparisons = [
        Comparison("previous_completed_1h_close", "<=", "sma24_previous"),
        Comparison("current_completed_1h_close", ">", "sma24"),
    ]
    if confirm:
        primitives.append(
            FeaturePrimitive(
                "PREVIOUS_HOUR_HIGH",
                "PRIOR_BAR_MAXIMUM",
                60,
                NumericTerm("previous_bars", 1, "bars"),
            )
        )
        comparisons.append(Comparison("current_completed_1h_close", ">", "previous_1h_high"))
    return ExecutableStrategySpec(
        schema_version=2,
        root_family=ROOT_FAMILY,
        family=ROOT_FAMILY,
        entry_event=ENTRY_EVENT,
        feature_primitives=tuple(primitives),
        comparisons=tuple(comparisons),
        numeric_parameters=_numeric_parameters(),
        regime_gates=("PERSISTENT_UP_4H_GATE",),
        confirmation_gates=("PREVIOUS_HOUR_HIGH_GATE",) if confirm else (),
        signal_timeframe_minutes=60,
        context_timeframe_minutes=240,
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
        },
        implementation_dependencies=tuple(
            DependencyIdentity(path, sha256(root / path)) for path in SPEC_DEPENDENCY_PATHS
        ),
        config_dependencies=(
            DependencyIdentity(config_path(variant), sha256(root / config_path(variant))),
        ),
    )


def legacy_signatures(root: Path = ROOT) -> list[dict[str, Any]]:
    document = read_json(root / "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json")
    return [
        {
            "experiment_id": item["experiment_id"],
            "root_family": item["root_family"],
            "behavior_hash": item["behavior_hash"],
            "structural_hash": item["structural_hash"],
        }
        for item in document["signatures"]
    ]


def alias_map(root: Path = ROOT, *, exclude: str | None = None) -> dict[str, str]:
    """Every registered alias and entry-event anchor, so a rename cannot mint a root.

    ``exclude`` drops one family so the gate can be replayed deterministically after the
    admitted family has been written into the V2 registry.
    """
    aliases: dict[str, str] = {}
    registries = [load_memory(root)["families"]]
    registry = root / REGISTRY_PATH
    if registry.is_file():
        registries.append(read_json(registry))
    for document in registries:
        for family in document["families"]:
            if family["family_id"] == exclude:
                continue
            for alias in [family["family_id"], *family["aliases"], *family["entry_event_anchors"]]:
                aliases[alias] = family["family_id"]
    return aliases


def novelty_decision(root: Path = ROOT) -> dict[str, Any]:
    """Submit both variants to the governed gate; a non-new root blocks execution."""
    aliases = alias_map(root, exclude=ROOT_FAMILY)
    collisions = sorted({ROOT_FAMILY, ENTRY_EVENT} & set(aliases))
    if collisions:
        raise NoveltyRejected(
            f"proposed root family or entry event collides with a registered anchor: {collisions}"
        )
    signature_path = "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json"
    signatures = legacy_signatures(root)
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
            signatures=signatures,
            aliases=aliases,
            declared_behavior_hash=binding.behavior_hash,
            runtime_spec=spec,
            family_budget_remaining=True,
        )
        classification = decision["classification"]
        allowed = (
            NEW_ROOT_CLASSIFICATIONS
            if variant == PRIMARY_VARIANT
            else (NEW_ROOT_CLASSIFICATIONS | DESCENDANT_CLASSIFICATIONS)
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
        signatures = [
            *signatures,
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
        "work_package": "WP-006",
        "gate": "GOVERNED_NOVELTY_ADMISSION_BEFORE_ANY_MARKET_RESULT",
        "proposed_root_family": ROOT_FAMILY,
        "proposed_hypothesis_id": HYPOTHESIS_ID,
        "entry_event": ENTRY_EVENT,
        "reference_signatures": {
            "path": signature_path,
            "sha256": sha256(root / signature_path),
            "legacy_count": 9,
        },
        "conflicting_root_check": {
            "registered_aliases_and_anchors": len(aliases),
            "collisions": [],
            "breakout_budget": "EXHAUSTED_AND_NOT_REOPENED",
        },
        "family_classification": "NEW_FAMILY",
        "admitted": True,
        "classifier_modified": False,
        "renamed_to_force_novelty": False,
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
        "work_package": "WP-006",
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
        "prior_adaptive_decisions": 2,
        "prior_result_dependent_forks": 2,
        "cumulative_adaptive_decisions": 3,
        "cumulative_result_dependent_forks": 3,
        "parameter_searches": 0,
        "sealed_queries": 0,
        "paper_observations": 0,
    }
    if any(allocation.get(key) != value for key, value in required.items()):
        raise SearchMemoryError("WP-006 allocation differs from the frozen authorization")
    if allocation["profiles"] != list(PROFILES) or sorted(allocation["experiment_ids"]) != sorted(
        SPEC
    ):
        raise SearchMemoryError("WP-006 allocation authorizes a different profile or variant set")
    if allocation["family_budget_policy"] != (
        "FAM-BREAKOUT remains exhausted; this allocation creates a new root and resets nothing."
    ):
        raise SearchMemoryError("WP-006 allocation weakened the breakout exhaustion policy")
    return allocation


def validate_registry(root: Path = ROOT) -> dict[str, Any]:
    registry = read_json(root / REGISTRY_PATH)
    families = registry["families"]
    if len(families) != 1 or families[0]["family_id"] != ROOT_FAMILY:
        raise SearchMemoryError("V2 family registry admits a family WP-006 never allocated")
    family = families[0]
    if family["parent_family_id"] is not None or family["entry_event_anchors"] != [ENTRY_EVENT]:
        raise SearchMemoryError("V2 family registry changed the admitted root identity")
    budget = read_json(root / BUDGET_PATH)
    limits = budget["family_limits"].get(ROOT_FAMILY)
    if limits != {
        "experiments": 2,
        "strategy_variants": 2,
        "trials": 8,
        "numeric_parameter_variants": 0,
    }:
        raise SearchMemoryError("V2 family budget differs from the WP-006 allocation")
    if set(budget["family_limits"]) != {ROOT_FAMILY} or budget["sealed_query_limit"] != 0:
        raise SearchMemoryError("V2 budget allocates an unauthorized family or sealed query")
    if budget["prior_budget_reference"] != "research/memory/SEARCH_BUDGET.json":
        raise SearchMemoryError("V2 budget does not carry the prior consumed allocation forward")
    return {"registry": registry, "budget": budget}


def ledger_entries(root: Path = ROOT) -> list[dict[str, Any]]:
    path = root / LEDGER_PATH
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def accounting(root: Path = ROOT) -> dict[str, int]:
    entries = ledger_entries(root)
    return {
        "experiments": len(entries),
        "strategy_variants": sum(item["budget_units"]["strategy_variants"] for item in entries),
        "trials": sum(item["budget_units"]["trials"] for item in entries),
        "numeric_parameter_variants": sum(
            item["budget_units"]["numeric_parameter_variants"] for item in entries
        ),
        "material_economic_hypotheses": len(
            {
                item["hypothesis_id"]
                for item in entries
                if item["hypothesis_role"] == "ECONOMIC_CORE"
            }
        ),
        "strategy_descendants": sum(bool(item["parent_experiment_ids"]) for item in entries),
    }


def validate_ledger(root: Path = ROOT) -> dict[str, int]:
    """Admissions never exceed the allocation and never restore a consumed budget."""
    schema = read_json(root / "contracts/search_ledger_v2.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    admission = read_json(root / ADMISSION_PATH)
    admitted = {item["experiment_id"]: item for item in admission["variants"]}
    seen: set[str] = set()
    for entry in ledger_entries(root):
        validator.validate(entry)
        experiment_id = entry["experiment_id"]
        if experiment_id in seen or experiment_id not in admitted:
            raise SearchMemoryError("unadmitted or duplicated V2 admission")
        reference = admitted[experiment_id]
        if any(entry[key] != reference[key] for key in ("behavior_hash", "executable_spec_hash")):
            raise SearchMemoryError("V2 admission identity differs from the governed gate")
        if entry["root_family"] != ROOT_FAMILY or entry["hypothesis_id"] != HYPOTHESIS_ID:
            raise SearchMemoryError("V2 admission changed the admitted family or hypothesis")
        prereg = root / entry["preregistration_path"]
        if not prereg.is_file() or sha256(prereg) != entry["preregistration_sha256"]:
            raise SearchMemoryError("V2 admission preregistration identity mismatch")
        seen.add(experiment_id)
    counts = accounting(root)
    limits = read_json(root / BUDGET_PATH)["family_limits"][ROOT_FAMILY]
    for field, limit in limits.items():
        if counts[field] > limit:
            raise SearchMemoryError(f"WP-006 {field} budget exceeded")
    return counts


def effective_preregistration(experiment_id: str, root: Path = ROOT) -> Path:
    """Resolve the effective preregistration through the pre-execution supersession registry.

    A correction is only admissible while zero strategy trials have been executed, and it may
    never add a variant, a profile or a numeric search. The superseded document is preserved.
    """
    registry = read_json(root / AMENDMENT_PATH)
    if (
        registry["kind"] != "PRE_EXECUTION_IDENTITY_BINDING_CORRECTION"
        or registry["strategy_trials_before_amendment"] != 0
        or registry["results_observed_before_amendment"] != 0
        or registry["additional_strategy_variants"] != 0
        or registry["additional_profile_trials"] != 0
        or registry["additional_numeric_parameter_variants"] != 0
        or set(registry["amendments"]) != set(SPEC)
    ):
        raise SearchMemoryError("invalid pre-execution supersession registry")
    item = registry["amendments"][experiment_id]
    expected = f"research/experiments/{experiment_id}/preregistration.v2.json"
    superseded = root / f"research/experiments/{experiment_id}/preregistration.json"
    if item["effective_path"] != expected or item["superseded_sha256"] != sha256(superseded):
        raise SearchMemoryError("superseded preregistration identity changed")
    path = root / expected
    if sha256(path) != item["effective_sha256"]:
        raise SearchMemoryError("effective preregistration identity changed")
    return path


def validate_identity(prereg: dict[str, Any], root: Path = ROOT) -> None:
    """The preregistration must bind to the exact admitted spec, config and protocol."""
    experiment_id = prereg["experiment_id"]
    if experiment_id not in SPEC:
        raise SearchMemoryError("unallocated WP-006 experiment")
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
    strategy_path = root / "backend/app/research/pullback.py"
    if (
        space["strategy_path"] != "backend/app/research/pullback.py"
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
    spec = executable_spec(variant, root)
    binding = bind_executable_spec(spec, declared_fingerprint=space["executable_spec_fingerprint"])
    # The stored spec is JSON, so compare through one canonical round trip.
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
        raise SearchMemoryError("WP-006 must execute on main")
    if git("status", "--porcelain", root=root):
        raise SearchMemoryError("commit all scientific declarations before market execution")
    head = git("rev-parse", "HEAD", root=root)
    if not ancestor(BASE, head, root):
        raise SearchMemoryError("required WP-006 starting HEAD is not in ancestry")
    validate_allocation(root)
    validate_registry(root)
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
            raise SearchMemoryError("WP-006 execution cannot overwrite or repeat an observed trial")
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
        raise SearchMemoryError("both WP-006 preregistrations must be frozen together")
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
        "v2_accounting": counts,
        "dependency_manifest_sha256": hashlib.sha256(
            json.dumps(dependency_manifest(root), sort_keys=True).encode()
        ).hexdigest(),
    }
