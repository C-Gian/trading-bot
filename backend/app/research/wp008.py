"""WP-008 fixed model identity, SEARCH_MEMORY_V2 gate, and execution chronology."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .continuation_lab import DATASET_HASH, DATASET_ID, PROFILES
from .linear_lab import validate_config
from .model_search_memory import (
    ExecutableModelSpec,
    admit_model_spec,
    bind_model_spec,
    model_fingerprint,
)
from .records import validate_preregistration
from .registry import admission_ledger, alias_map, registry_ledger, signatures
from .runner import declared_content_identity, sha256
from .search_memory import SearchMemoryError
from .search_memory_v2 import DependencyIdentity
from .supervised import CONFIG_FEATURES, FEATURE_VERSION, LABEL_VERSION, STRATEGY_VERSION
from .wp004 import ROOT, ancestor, first_commit, git, immutable_from_first_commit
from .wp007 import substrate_gate

BASE = "762b3b77f686305b1c73f19956d0b9b16b7a9b1c"
ROOT_FAMILY = "FAM-SUPERVISED-LINEAR"
HYPOTHESIS_ID = STRATEGY_VERSION
PRIMARY_VARIANT = "LINEAR_FULL"
SPEC = {
    "EXP-ML-014-LINEAR-NET-R-FULL": "LINEAR_FULL",
    "EXP-ML-015-LINEAR-NET-R-NO-FLOW": "LINEAR_NO_FLOW",
}
ROLES = {"LINEAR_FULL": "ECONOMIC_CORE", "LINEAR_NO_FLOW": "STRUCTURAL_CONFIRMATION_VARIANT"}
STEMS = {"LINEAR_FULL": "linear_full", "LINEAR_NO_FLOW": "linear_no_flow"}
ALLOCATION_ID = "WP008-LINEAR-SUPERVISED-ALLOCATION"
ALLOCATION_PATH = f"research/memory/registry/allocations/{ALLOCATION_ID}.json"
FAMILY_PATH = f"research/memory/registry/families/{ROOT_FAMILY}.json"
ADMISSION_PATH = "research/memory/registry/admissions/WP008-NOVELTY-ADMISSION.json"
REJECTION_PATH = "research/memory/registry/admissions/WP008-NOVELTY-REJECTION.json"
LEDGER_PATH = "research/memory/registry/ledger/WP-008.jsonl"
OUTCOMES_PATH = "research/memory/registry/outcomes/WP-008.jsonl"
ATTEMPT_PATH = "research/runs/WP-008-ATTEMPT.json"
PROTOCOL_PATH = "research/protocols/WP-008-LINEAR-NET-R-V1.json"

SPEC_DEPENDENCY_PATHS = (
    "backend/app/data/policy.py",
    "backend/app/backtest/models.py",
    "backend/app/backtest/engine.py",
    "backend/app/research/evaluation_protocol.py",
    "backend/app/research/source_grid.py",
    "backend/app/research/continuation_lab.py",
    "backend/app/research/order_flow.py",
    "backend/app/research/supervised.py",
    "backend/app/research/linear_model.py",
    "backend/app/research/linear_lab.py",
    "backend/app/research/artifacts.py",
    "backend/app/research/model_search_memory.py",
    "backend/app/research/search_memory_v2.py",
    PROTOCOL_PATH,
)
IMPLEMENTATION_PATHS = (
    *SPEC_DEPENDENCY_PATHS,
    "backend/app/research/registry.py",
    "backend/app/research/records.py",
    "backend/app/research/runner.py",
    "backend/app/research/wp008.py",
    "scripts/run_wp008.py",
    "scripts/preregister_wp008.py",
    "docs/contracts/RESEARCH_ARTIFACT_STORAGE_V1.md",
    "docs/contracts/SUPERVISED_CHALLENGER_V1.md",
    "docs/contracts/DEVELOPMENT_EVALUATION_V1.md",
    "docs/contracts/EXECUTION_MODEL_V2.md",
    "docs/contracts/COST_MODEL_V1.md",
    "docs/contracts/RESEARCH_SEARCH_MEMORY_V2.md",
    "docs/contracts/RESEARCH_SEARCH_MEMORY_V2_MODEL_EXTENSION.md",
    "contracts/executable_model_spec_v2.schema.json",
    "uv.lock",
    "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json",
    "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json",
    ALLOCATION_PATH,
    ADMISSION_PATH,
    FAMILY_PATH,
)


class NoveltyRejected(SearchMemoryError):
    """The fixed primary proposal was not a new family; market evaluation is blocked."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(variant: str) -> str:
    if variant not in STEMS:
        raise SearchMemoryError("undeclared WP-008 model configuration")
    return f"research/configs/wp008/{STEMS[variant]}.json"


def dependency_manifest(root: Path = ROOT) -> list[dict[str, str]]:
    return [{"path": path, "sha256": sha256(root / path)} for path in IMPLEMENTATION_PATHS]


def _feature_specs(variant: str) -> tuple[dict[str, Any], ...]:
    transformations = {
        "LOG_RETURN_1H": "LN(CURRENT_1H_CLOSE/CURRENT_1H_OPEN)",
        "LOG_RETURN_24H": "LN(CURRENT_1H_CLOSE/CLOSE_24H_EARLIER)",
        "LOG_DISTANCE_TO_PRIOR_24H_HIGH": "LN(CURRENT_CLOSE/MAX_PREVIOUS_24_HIGH_EXCLUDING_CURRENT)",
        "REALIZED_VOL_24H": "SQRT(MEAN(EXACT_24_CLOSE_TO_CLOSE_LOG_RETURN_SQUARED))",
        "LOG_RELATIVE_VOLUME_1H": "LN(CURRENT_BASE_VOLUME/MEAN_PREVIOUS_24_BASE_VOLUME)",
        "DIRECTIONAL_EFFICIENCY_4H": "(SUM_POSITIVE_42_CHANGES-ABS_SUM_NEGATIVE)/(SUM_POSITIVE+ABS_SUM_NEGATIVE)",
        "TAKER_BUY_SHARE_1H_CENTERED": "ORDER_FLOW_FEATURES_V1_CURRENT_1H_SHARE_MINUS_0.5",
        "TAKER_BUY_SHARE_4H_CENTERED": "ORDER_FLOW_FEATURES_V1_NONOVERLAPPING_4H_SHARE_MINUS_0.5",
    }
    return tuple(
        {"name": name, "transformation": transformations[name], "order": index + 1}
        for index, name in enumerate(CONFIG_FEATURES[variant])
    )


def executable_spec(variant: str, root: Path = ROOT) -> ExecutableModelSpec:
    if variant not in CONFIG_FEATURES:
        raise SearchMemoryError("undeclared WP-008 model configuration")
    relative = config_path(variant)
    config = read_json(root / relative)
    validate_config(config)
    implementation = tuple(
        DependencyIdentity(path, sha256(root / path)) for path in SPEC_DEPENDENCY_PATHS
    )
    return ExecutableModelSpec(
        schema_version=2,
        root_family=ROOT_FAMILY,
        family=ROOT_FAMILY,
        algorithm="NUMPY_FLOAT64_ORDINARY_LEAST_SQUARES_WITH_INTERCEPT",
        label={
            "version": LABEL_VERSION,
            "profile": "DEFAULT",
            "isolated": True,
            "invalid_unresolved": "EXCLUDE_COUNT_NEVER_IMPUTE",
        },
        features=_feature_specs(variant),
        train_window_rule={
            "kind": "EXPANDING_CHRONOLOGICAL",
            "folds": [2019, 2020, 2021, 2022, 2023, 2024],
            "purge_hours": 216,
            "training_signal_boundary": "STRICTLY_BEFORE",
            "label_outcome_before_validation": True,
        },
        scaling={"scope": "TRAINING_ONLY_PER_FOLD", "mean": True, "std_ddof": 0},
        regularization={"kind": "NONE", "searched": False},
        hyperparameters={"searched": 0, "feature_selection": "NONE", "interactions": "NONE"},
        signal_rule={"field": "predicted_default_net_R", "operator": ">", "threshold": 0.0},
        execution_geometry={
            "direction": "LONG",
            "reference": "JUST_COMPLETED_1H_CLOSE",
            "entry": "NEXT_CANONICAL_1M_OPEN",
            "stop_fraction": 0.02,
            "target_fraction": 0.04,
            "max_hold_minutes": 1440,
            "position_policy": "SINGLE_LONG_NO_OVERLAP",
            "profiles": list(PROFILES),
            "stress_retrain": False,
        },
        dataset={
            "manifest_id": DATASET_ID,
            "content_hash": DATASET_HASH,
            "feature_version": FEATURE_VERSION,
            "order_flow_version": "ORDER_FLOW_FEATURES_V1",
            "maximum_timestamp": "2024-12-31T23:59:00Z",
        },
        cost_model_reference="BTCUSDT_SPOT_COST_V1",
        execution_model_reference="EXECUTION_MODEL_V2",
        implementation_dependencies=implementation,
        config_dependencies=(DependencyIdentity(relative, sha256(root / relative)),),
    )


def novelty_decisions(root: Path = ROOT) -> list[dict[str, Any]]:
    prior_signatures = signatures(root, exclude_experiment_ids=set(SPEC))
    aliases = alias_map(root)
    decisions = []
    for experiment_id, variant in SPEC.items():
        spec = executable_spec(variant, root)
        try:
            decision = admit_model_spec(
                spec,
                declared_family=ROOT_FAMILY,
                signatures=prior_signatures,
                aliases=aliases,
                declared_fingerprint=model_fingerprint(spec),
            )
        except SearchMemoryError as exc:
            raise NoveltyRejected(str(exc)) from exc
        decision.update(
            experiment_id=experiment_id,
            variant=variant,
            hypothesis_role=ROLES[variant],
            spec=json.loads(json.dumps(spec.to_dict())),
        )
        decisions.append(decision)
        prior_signatures.append(
            {
                "experiment_id": experiment_id,
                "root_family": ROOT_FAMILY,
                "behavior_hash": decision["behavior_hash"],
                "structural_hash": decision["structural_hash"],
            }
        )
    if decisions[0]["classification"] != "NEW_FAMILY":
        raise NoveltyRejected("LINEAR_FULL was not admitted as NEW_FAMILY")
    if decisions[1]["classification"] != "DESCENDANT_MECHANISM_CHANGE":
        raise NoveltyRejected("LINEAR_NO_FLOW was not classified as structural ablation")
    return decisions


def _recorded_spec(payload: dict[str, Any]) -> ExecutableModelSpec:
    """Reconstruct an immutable admitted spec without consulting current source files."""
    values = dict(payload)
    values["features"] = tuple(values["features"])
    values["implementation_dependencies"] = tuple(
        DependencyIdentity(**item) for item in values["implementation_dependencies"]
    )
    values["config_dependencies"] = tuple(
        DependencyIdentity(**item) for item in values["config_dependencies"]
    )
    return ExecutableModelSpec(**values)


def validate_admission(root: Path = ROOT) -> dict[str, Any]:
    admission = read_json(root / ADMISSION_PATH)
    if not admission["admitted"] or admission["market_results_observed_at_admission"] != 0:
        raise NoveltyRejected("WP-008 admission did not precede all market results")
    prior_signatures = signatures(root, exclude_experiment_ids=set(SPEC))
    aliases = alias_map(root)
    for actual in admission["variants"]:
        spec = _recorded_spec(actual["spec"])
        decision = admit_model_spec(
            spec,
            declared_family=ROOT_FAMILY,
            signatures=prior_signatures,
            aliases=aliases,
            declared_fingerprint=model_fingerprint(spec),
        )
        decision.update(
            experiment_id=actual["experiment_id"],
            variant=actual["variant"],
            spec=json.loads(json.dumps(spec.to_dict())),
        )
        for key in (
            "experiment_id",
            "variant",
            "classification",
            "behavior_hash",
            "structural_hash",
            "executable_spec_hash",
            "dependency_hash",
            "matched_experiment_ids",
            "spec",
        ):
            if actual[key] != decision[key]:
                raise NoveltyRejected(f"admission drift: {key}")
        prior_signatures.append(
            {
                "experiment_id": actual["experiment_id"],
                "root_family": ROOT_FAMILY,
                "behavior_hash": decision["behavior_hash"],
                "structural_hash": decision["structural_hash"],
            }
        )
    return admission


def validate_allocation(root: Path = ROOT) -> dict[str, Any]:
    allocation = read_json(root / ALLOCATION_PATH)
    if (
        allocation["allocation_id"] != ALLOCATION_ID
        or allocation["experiment_ids"] != list(SPEC)
        or allocation["primary_variant"] != PRIMARY_VARIANT
        or allocation["model_configurations"] != 2
        or allocation["profile_evaluations"] != 8
        or allocation["supervised_model_fits"] != 12
        or allocation["numeric_parameter_variants"] != 0
        or allocation["hyperparameter_searches"] != 0
        or allocation["threshold_searches"] != 0
        or allocation["algorithm_variants"] != 0
        or allocation["sealed_queries"] != 0
    ):
        raise SearchMemoryError("WP-008 allocation differs from its exact authority")
    return allocation


def validate_identity(
    prereg: dict[str, Any], root: Path = ROOT, *, validate_current_dependencies: bool = True
) -> None:
    experiment_id = prereg["experiment_id"]
    variant = SPEC.get(experiment_id)
    if variant is None:
        raise SearchMemoryError("unallocated WP-008 experiment")
    config = read_json(root / config_path(variant))
    validate_config(config)
    plan = [
        {
            "trial_id": f"{variant}:{profile}",
            "config_path": config_path(variant),
            "config_sha256": sha256(root / config_path(variant)),
        }
        for profile in PROFILES
    ]
    space = prereg["parameter_space"]
    if prereg["trial_budget"] != 4 or space["trial_plan"] != plan or prereg["seeds"] != [0]:
        raise SearchMemoryError("undeclared WP-008 trial plan")
    if validate_current_dependencies and space["dependencies"] != dependency_manifest(root):
        raise SearchMemoryError("WP-008 dependency identity mismatch")
    strategy_path = root / "backend/app/research/linear_lab.py"
    if (
        space["strategy_path"] != "backend/app/research/linear_lab.py"
        or space["strategy_sha256"] != sha256(strategy_path)
        or prereg["code_config_reference"] != declared_content_identity(strategy_path, plan)
    ):
        raise SearchMemoryError("WP-008 code/config identity mismatch")
    spec = (
        executable_spec(variant, root)
        if validate_current_dependencies
        else _recorded_spec(space["executable_model_spec"])
    )
    binding = bind_model_spec(spec, declared_fingerprint=space["model_fingerprint"])
    if (
        space["executable_model_spec"] != json.loads(json.dumps(spec.to_dict()))
        or space["executable_spec_hash"] != binding.executable_spec_hash
        or space["behavior_hash"] != binding.behavior_hash
        or space["structural_hash"] != binding.structural_hash
        or space["dependency_hash"] != binding.dependency_hash
        or space["allocation_id"] != ALLOCATION_ID
        or space["primary_family_variant"] != PRIMARY_VARIANT
    ):
        raise SearchMemoryError("WP-008 preregistration differs from admitted model spec")


def validate_ledger(root: Path = ROOT) -> dict[str, int]:
    entries = [entry for entry in registry_ledger(root) if entry["work_package"] == "WP-008"]
    admission = validate_admission(root)
    expected = {item["experiment_id"]: item for item in admission["variants"]}
    if len(entries) != 2:
        raise SearchMemoryError("WP-008 ledger must contain exactly two admissions")
    for entry in entries:
        item = expected[entry["experiment_id"]]
        prereg = root / entry["preregistration_path"]
        if sha256(prereg) != entry["preregistration_sha256"]:
            raise SearchMemoryError("WP-008 ledger preregistration hash mismatch")
        if any(
            entry[key] != item[key]
            for key in ("classification", "behavior_hash", "executable_spec_hash")
        ):
            raise SearchMemoryError("WP-008 ledger differs from novelty admission")
    return {"experiments": 2, "strategy_variants": 2, "trials": 8, "numeric_parameter_variants": 0}


def preflight(root: Path = ROOT) -> dict[str, Any]:
    if git("branch", "--show-current", root=root) != "main":
        raise SearchMemoryError("WP-008 must execute on main")
    if git("status", "--porcelain", root=root):
        raise SearchMemoryError("commit all preregistrations before WP-008 market evaluation")
    head = git("rev-parse", "HEAD", root=root)
    if not ancestor(BASE, head, root):
        raise SearchMemoryError("required accepted WP-007 HEAD is not in ancestry")
    substrate = substrate_gate(root)
    allocation = validate_allocation(root)
    admission = validate_admission(root)
    admission_commit = immutable_from_first_commit(ADMISSION_PATH, root)
    for dependency in SPEC_DEPENDENCY_PATHS:
        commit = first_commit(dependency, root)
        if commit == admission_commit or not ancestor(commit, admission_commit, root):
            raise SearchMemoryError("model implementation/spec must precede admission")
    prereg_hashes = {}
    prereg_commits = set()
    for experiment_id in SPEC:
        directory = root / "research/experiments" / experiment_id
        if any((directory / name).exists() for name in ("result.json", "trials.parquet")):
            raise SearchMemoryError("WP-008 cannot overwrite or repeat an observed result")
        path = directory / "preregistration.json"
        prereg = validate_preregistration(path)
        validate_identity(prereg, root)
        commit = immutable_from_first_commit(path.relative_to(root).as_posix(), root)
        if commit == admission_commit or not ancestor(admission_commit, commit, root):
            raise SearchMemoryError("preregistration must follow committed admission")
        prereg_hashes[experiment_id] = sha256(path)
        prereg_commits.add(commit)
    if len(prereg_commits) != 1:
        raise SearchMemoryError("both WP-008 preregistrations must be committed together")
    ledger = validate_ledger(root)
    if (root / ATTEMPT_PATH).exists():
        raise SearchMemoryError("WP-008 execution attempt already exists")
    return {
        "status": "PASS",
        "execution_commit": head,
        "admission_commit": admission_commit,
        "preregistration_commit": prereg_commits.pop(),
        "preregistration_hashes": prereg_hashes,
        "family_classification": admission["family_classification"],
        "allocation": allocation["allocation_id"],
        "accounting": ledger,
        "order_flow_gate": substrate,
    }


def prior_admission_count(root: Path = ROOT) -> int:
    return len(admission_ledger(root))
