"""WP-016 Wikipedia-attention admission, protocol, and preregistration gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .continuation_lab import DATASET_HASH, DATASET_ID, PROFILES
from .funding import FEATURE as FUNDING_FEATURE
from .funding import MANIFEST_PATH as FUNDING_MANIFEST_PATH
from .model_search_memory import (
    ExecutableModelSpec,
    admit_model_spec,
    bind_model_spec,
    model_fingerprint,
)
from .records import validate_preregistration
from .registry import alias_map, signatures
from .runner import sha256
from .search_memory import SearchMemoryError
from .search_memory_v2 import DependencyIdentity
from .supervised import FEATURE_VERSION, FULL_FEATURES, LABEL_VERSION
from .wikimedia import FEATURE as ATTENTION_FEATURE
from .wikimedia import MANIFEST_PATH as ATTENTION_MANIFEST_PATH
from .wp004 import ROOT
from .wp014_model import HGBR_PARAMETERS, SKLEARN_VERSION
from .wp015 import TRANSFORMATIONS as WP015_TRANSFORMATIONS
from .wp016_lab import CONTROL_VARIANT, FUNDING_FEATURES, PRIMARY_FEATURES, PRIMARY_VARIANT

ROOT_FAMILY = "FAM-EXTERNAL-PUBLIC-ATTENTION"
HYPOTHESIS_ID = "WIKIPEDIA_ATTENTION_SHOCK_ADDS_INFORMATION_V1"
EXPERIMENTS = {
    PRIMARY_VARIANT: "EXP-ML-026-INTERNAL-FUNDING-PLUS-ATTENTION-HGBR",
    CONTROL_VARIANT: "EXP-ML-027-INTERNAL-PLUS-FUNDING-HGBR-MATCHED-ATTENTION",
}
VARIANTS = (PRIMARY_VARIANT, CONTROL_VARIANT)
ROLES = {PRIMARY_VARIANT: "ECONOMIC_CORE", CONTROL_VARIANT: "MATCHED_KNOWN_CONTROL"}
ALLOCATION_ID = "WP016-EXTERNAL-PUBLIC-ATTENTION-ALLOCATION"
ALLOCATION_PATH = f"research/memory/registry/allocations/{ALLOCATION_ID}.json"
FAMILY_PATH = f"research/memory/registry/families/{ROOT_FAMILY}.json"
ADMISSION_PATH = "research/memory/registry/admissions/WP016-NOVELTY-ADMISSION.json"
LEDGER_PATH = "research/memory/registry/ledger/WP-016.jsonl"
PROTOCOL_PATH = "research/protocols/WP-016-WIKIPEDIA-ATTENTION-HGBR-V1.json"
WALK_FORWARD_PATH = "research/protocols/WP-015-WALK-FORWARD-V1.json"
AUDIT_PATH = "reports/validation/WP-016-WIKIMEDIA-ATTENTION-AUDIT.json"
STEMS = {
    PRIMARY_VARIANT: "internal_funding_plus_attention_hgbr",
    CONTROL_VARIANT: "internal_plus_funding_hgbr_matched_attention",
}
MAXIMUM_MODEL_FITS = 10
PREDICTION_TOLERANCE = 1e-10
TRANSFORMATIONS = {
    **WP015_TRANSFORMATIONS,
    ATTENTION_FEATURE: "LOG((PAGEVIEWS_D+1)/(MEDIAN(PREVIOUS_28_DAILY_PAGEVIEWS_EXCLUDING_D)+1))",
}
IMPLEMENTATION_PATHS = (
    "backend/app/data/policy.py",
    "backend/app/backtest/models.py",
    "backend/app/backtest/engine.py",
    "backend/app/research/evaluation_protocol.py",
    "backend/app/research/continuation_lab.py",
    "backend/app/research/order_flow.py",
    "backend/app/research/supervised.py",
    "backend/app/research/funding.py",
    "backend/app/research/wikimedia.py",
    "backend/app/research/wp014_model.py",
    "backend/app/research/wp015_model.py",
    "backend/app/research/wp015_lab.py",
    "backend/app/research/wp016_lab.py",
    "backend/app/research/wp016_runner.py",
    "backend/app/research/artifacts.py",
    "backend/app/research/model_search_memory.py",
    "backend/app/research/search_memory_v2.py",
    "scripts/reconcile_wp016.py",
    "docs/contracts/PERPETUAL_FUNDING_CONTEXT_V1.md",
    "docs/contracts/WIKIPEDIA_ATTENTION_CONTEXT_V1.md",
    FUNDING_MANIFEST_PATH,
    ATTENTION_MANIFEST_PATH,
    PROTOCOL_PATH,
    WALK_FORWARD_PATH,
    "pyproject.toml",
    "uv.lock",
)


class WP016Error(SearchMemoryError):
    """WP-016 fixed declaration or chronology was violated."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(variant: str) -> str:
    if variant not in STEMS:
        raise WP016Error("undeclared WP-016 configuration")
    return f"research/configs/wp016/{STEMS[variant]}.json"


def dependency_manifest(root: Path = ROOT) -> list[dict[str, str]]:
    return [{"path": path, "sha256": sha256(root / path)} for path in IMPLEMENTATION_PATHS]


def features_for(variant: str) -> tuple[str, ...]:
    if variant == PRIMARY_VARIANT:
        return PRIMARY_FEATURES
    if variant == CONTROL_VARIANT:
        return FUNDING_FEATURES
    raise WP016Error("undeclared WP-016 configuration")


def executable_spec(variant: str, root: Path = ROOT) -> ExecutableModelSpec:
    names = features_for(variant)
    funding = read_json(root / FUNDING_MANIFEST_PATH)
    attention = read_json(root / ATTENTION_MANIFEST_PATH)
    relative = config_path(variant)
    return ExecutableModelSpec(
        schema_version=2,
        root_family=ROOT_FAMILY,
        family=ROOT_FAMILY,
        algorithm=f"SKLEARN_{SKLEARN_VERSION}_HIST_GRADIENT_BOOSTING_REGRESSOR",
        label={
            "version": LABEL_VERSION,
            "profile": "DEFAULT",
            "isolated": True,
            "invalid_unresolved": "EXCLUDE_COUNT_NEVER_IMPUTE",
        },
        features=tuple(
            {"name": name, "transformation": TRANSFORMATIONS[name], "order": index + 1}
            for index, name in enumerate(names)
        ),
        train_window_rule={
            "kind": "EXPANDING_CHRONOLOGICAL_PER_ANNUAL_FOLD",
            "folds": list(range(2020, 2025)),
            "purge_hours": 216,
            "training_signal_boundary": "STRICTLY_BEFORE_VALIDATION_START_MINUS_PURGE",
            "label_outcome_before_purge_boundary": True,
            "funding_context_required_at_historical_signal": True,
            "attention_context_required_at_historical_signal": True,
            "update_cadence": "ONCE_PER_FOLD_NO_VALIDATION_REFIT",
        },
        scaling={"scope": "NONE_RAW_GOVERNED_VALUES", "mean": False, "std": False},
        regularization={"kind": "FIXED_L2_LEAF_REGULARIZATION", "value": 1.0, "searched": False},
        hyperparameters={
            "parameters": dict(HGBR_PARAMETERS),
            "searched": 0,
            "feature_selection": "NONE",
            "attention_windows": 0,
            "attention_transformations": 0,
            "article_variants": 0,
            "architecture_variants": 0,
        },
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
            "funding_manifest_id": funding["manifest_id"],
            "funding_logical_sha256": funding["canonical"]["logical_sha256"],
            "funding_availability": "STRICTLY_PRIOR_SETTLEMENT",
            "attention_manifest_id": attention["manifest_id"],
            "attention_logical_sha256": attention["canonical"]["logical_sha256"],
            "attention_availability": "UTC_DAY_END_PLUS_24H",
            "matched_attention_eligible_universe": "REQUIRED_FOR_PRIMARY_AND_CONTROL",
            "maximum_timestamp": "2024-12-31T23:59:00Z",
        },
        cost_model_reference="BTCUSDT_SPOT_COST_V1",
        execution_model_reference="EXECUTION_MODEL_V2",
        implementation_dependencies=tuple(
            DependencyIdentity(path, sha256(root / path)) for path in IMPLEMENTATION_PATHS
        ),
        config_dependencies=(DependencyIdentity(relative, sha256(root / relative)),),
    )


def novelty_decision(root: Path = ROOT) -> dict[str, Any]:
    prior = signatures(root, exclude_experiment_ids=set(EXPERIMENTS.values()))
    aliases = alias_map(root, exclude=ROOT_FAMILY)
    primary_spec = executable_spec(PRIMARY_VARIANT, root)
    primary = admit_model_spec(
        primary_spec,
        declared_family=ROOT_FAMILY,
        signatures=prior,
        aliases=aliases,
        declared_fingerprint=model_fingerprint(primary_spec),
    )
    if primary["classification"] != "NEW_FAMILY":
        raise WP016Error("public-attention information mechanism was not admitted")
    primary.update(
        experiment_id=EXPERIMENTS[PRIMARY_VARIANT],
        variant=PRIMARY_VARIANT,
        hypothesis_role=ROLES[PRIMARY_VARIANT],
        spec=primary_spec.to_dict(),
    )
    control_spec = executable_spec(CONTROL_VARIANT, root)
    binding = bind_model_spec(control_spec)
    control = {
        "admitted": False,
        "authorized_as_matched_control": True,
        "classification": "KNOWN_FUNDING_HGBR_MATCHED_CONTROL",
        "duplicate_gate_unchanged": True,
        "known_mechanism_experiment_ids": ["EXP-ML-024-INTERNAL-PLUS-FUNDING-HGBR"],
        "root_family": ROOT_FAMILY,
        "matched_experiment_ids": [],
        "behavior_hash": binding.behavior_hash,
        "structural_hash": binding.structural_hash,
        "executable_spec_hash": binding.executable_spec_hash,
        "dependency_hash": binding.dependency_hash,
        "experiment_id": EXPERIMENTS[CONTROL_VARIANT],
        "variant": CONTROL_VARIANT,
        "hypothesis_role": ROLES[CONTROL_VARIANT],
        "spec": control_spec.to_dict(),
    }
    return {
        "schema_version": 1,
        "work_package": "WP-016",
        "gate": "GOVERNED_NEW_INFORMATION_ADMISSION_BEFORE_VALIDATION_RESULT",
        "proposed_root_family": ROOT_FAMILY,
        "proposed_hypothesis_id": HYPOTHESIS_ID,
        "family_classification": "NEW_FAMILY",
        "admitted": True,
        "market_results_observed_at_admission": 0,
        "classifier_modified": False,
        "renamed_to_force_novelty": False,
        "conditions_added_to_force_novelty": False,
        "reference_signatures": len(prior),
        "mechanism_distinction": "One point-in-time-safe public-attention shock adds official Wikimedia information to frozen spot and funding inputs.",
        "matched_control_policy": "WP-015 funding HGBR is disclosed as a known mechanism on the exact attention-available universe; no novelty is claimed.",
        "variants": [primary, control],
    }


def load_protocol(root: Path = ROOT) -> dict[str, Any]:
    document = read_json(root / PROTOCOL_PATH)
    budget = document["budget"]
    zero_keys = (
        "attention_windows",
        "article_variants",
        "transform_variants",
        "threshold_variants",
        "algorithm_variants",
        "hyperparameter_variants",
        "feature_subsets",
        "result_dependent_forks",
    )
    if (
        document["folds"] != list(range(2020, 2025))
        or document["internal_features"] != list(FULL_FEATURES)
        or document["funding_feature"] != FUNDING_FEATURE
        or document["attention_feature"] != ATTENTION_FEATURE
        or document["primary_feature_order"] != list(PRIMARY_FEATURES)
        or document["control_feature_order"] != list(FUNDING_FEATURES)
        or document["hgbr_parameters"] != HGBR_PARAMETERS
        or document["profiles"] != list(PROFILES)
        or budget["model_fits"] != 10
        or any(budget[key] != 0 for key in zero_keys)
    ):
        raise WP016Error("WP-016 protocol drifted")
    return document


def load_walk_forward(root: Path = ROOT) -> dict[str, Any]:
    document = read_json(root / WALK_FORWARD_PATH)
    if [fold["fold_id"] for fold in document["folds"]] != [
        f"DEV-{year}" for year in range(2020, 2025)
    ]:
        raise WP016Error("WP-016 validation folds drifted")
    return document


def validate_admission(root: Path = ROOT) -> dict[str, Any]:
    recorded = read_json(root / ADMISSION_PATH)
    if recorded != json.loads(json.dumps(novelty_decision(root))):
        raise WP016Error("WP-016 admission differs from deterministic output")
    return recorded


def validate_allocation(root: Path = ROOT) -> dict[str, Any]:
    allocation = read_json(root / ALLOCATION_PATH)
    required = {
        "new_economic_hypotheses": 1,
        "model_configurations": 2,
        "profile_evaluations": 8,
        "supervised_model_fits": 10,
        "attention_windows": 0,
        "article_variants": 0,
        "attention_transformations": 0,
        "feature_subsets": 0,
        "algorithm_variants": 0,
        "hyperparameter_variants": 0,
        "threshold_variants": 0,
        "result_dependent_fork_increment": 0,
        "sealed_queries": 0,
    }
    if any(allocation.get(key) != value for key, value in required.items()):
        raise WP016Error("WP-016 allocation drifted")
    return allocation


def validate_preregistrations(root: Path = ROOT) -> dict[str, str]:
    hashes = {}
    for variant, experiment in EXPERIMENTS.items():
        relative = f"research/experiments/{experiment}/preregistration.json"
        document = validate_preregistration(root / relative)
        space = document["parameter_space"]
        if (
            document["status"] != "PREREGISTERED"
            or space["variant"] != variant
            or space["features"] != list(features_for(variant))
            or space["validation_years"] != list(range(2020, 2025))
            or space["model_fits"] != 5
            or space["signal_threshold"] != 0.0
            or space["matched_attention_eligible_universe"] is not True
        ):
            raise WP016Error("WP-016 preregistration drifted")
        hashes[variant] = sha256(root / relative)
    return hashes


def preflight(root: Path = ROOT) -> dict[str, Any]:
    protocol = load_protocol(root)
    admission = validate_admission(root)
    validate_allocation(root)
    preregistrations = validate_preregistrations(root)
    audit = read_json(root / AUDIT_PATH)
    manifest = read_json(root / ATTENTION_MANIFEST_PATH)
    if (
        audit["status"] != "PASS"
        or audit["market_results_observed"] is not False
        or audit["complete_validation_folds"] != list(range(2020, 2025))
    ):
        raise WP016Error("Wikimedia integrity/as-of audit failed")
    if any(
        (root / f"research/experiments/{item}/result.json").exists()
        for item in EXPERIMENTS.values()
    ):
        raise WP016Error("WP-016 results already exist")
    return {
        "schema_version": 1,
        "work_package": "WP-016-PREPARATION",
        "status": "PASS",
        "protocol_id": protocol["protocol_id"],
        "family_classification": admission["family_classification"],
        "control_classification": admission["variants"][1]["classification"],
        "features": list(PRIMARY_FEATURES),
        "only_new_feature": ATTENTION_FEATURE,
        "forbidden_sources": [
            "GOOGLE_TRENDS",
            "REDDIT",
            "NEWS",
            "OTHER_WIKIPEDIA_ARTICLES_OR_LANGUAGES",
        ],
        "hgbr_parameters": dict(HGBR_PARAMETERS),
        "input_scaling": "NONE_RAW_GOVERNED_VALUES",
        "validation_years": list(range(2020, 2025)),
        "purge_boundary_hours": 216,
        "complete_outcomes_before_boundary": True,
        "attention_available_at_or_before_signal": True,
        "same_day_attention_use": False,
        "trailing_median_excludes_current": True,
        "matched_eligible_universe": True,
        "attention_records": manifest["canonical"]["rows"],
        "post_cutoff_rows": manifest["integrity"]["post_cutoff_rows"],
        "signal_threshold": 0.0,
        "profiles": list(PROFILES),
        "model_fits_reserved": MAXIMUM_MODEL_FITS,
        "model_fits_executed": 0,
        "prediction_tolerance": PREDICTION_TOLERANCE,
        "preregistration_sha256": preregistrations,
        "market_results_observed": 0,
        "post_cutoff_access": 0,
        "sealed_queries": 0,
    }


__all__ = [name for name in globals() if name.isupper()] + [
    "WP016Error",
    "config_path",
    "dependency_manifest",
    "executable_spec",
    "features_for",
    "load_protocol",
    "load_walk_forward",
    "novelty_decision",
    "preflight",
    "validate_admission",
    "validate_allocation",
    "validate_preregistrations",
]
