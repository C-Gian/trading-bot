"""WP-015 fixed funding-information admission, protocol, and preregistration gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .continuation_lab import DATASET_HASH, DATASET_ID, PROFILES
from .funding import FEATURE, MANIFEST_PATH
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
from .wp004 import ROOT
from .wp014_model import HGBR_PARAMETERS, SKLEARN_VERSION
from .wp015_lab import CONTROL_VARIANT, PRIMARY_FEATURES, PRIMARY_VARIANT

ROOT_FAMILY = "FAM-DERIVATIVES-SENTIMENT-CONTEXT"
HYPOTHESIS_ID = "SETTLED_FUNDING_ADDS_POSITIONING_INFORMATION_V1"
EXPERIMENTS = {
    PRIMARY_VARIANT: "EXP-ML-024-INTERNAL-PLUS-FUNDING-HGBR",
    CONTROL_VARIANT: "EXP-ML-025-INTERNAL-HGBR-MATCHED-FUNDING",
}
VARIANTS = (PRIMARY_VARIANT, CONTROL_VARIANT)
ROLES = {PRIMARY_VARIANT: "ECONOMIC_CORE", CONTROL_VARIANT: "MATCHED_KNOWN_CONTROL"}
ALLOCATION_ID = "WP015-DERIVATIVES-SENTIMENT-ALLOCATION"
ALLOCATION_PATH = f"research/memory/registry/allocations/{ALLOCATION_ID}.json"
FAMILY_PATH = f"research/memory/registry/families/{ROOT_FAMILY}.json"
ADMISSION_PATH = "research/memory/registry/admissions/WP015-NOVELTY-ADMISSION.json"
LEDGER_PATH = "research/memory/registry/ledger/WP-015.jsonl"
OUTCOMES_PATH = "research/memory/registry/outcomes/WP-015.jsonl"
PROTOCOL_PATH = "research/protocols/WP-015-PERPETUAL-FUNDING-HGBR-V1.json"
WALK_FORWARD_PATH = "research/protocols/WP-015-WALK-FORWARD-V1.json"
STEMS = {
    PRIMARY_VARIANT: "internal_plus_funding_hgbr",
    CONTROL_VARIANT: "internal_hgbr_matched_funding",
}
MAXIMUM_MODEL_FITS = 10
PREDICTION_TOLERANCE = 1e-10

TRANSFORMATIONS = {
    "LOG_RETURN_1H": "LN(CURRENT_1H_CLOSE/CURRENT_1H_OPEN)",
    "LOG_RETURN_24H": "LN(CURRENT_1H_CLOSE/CLOSE_24H_EARLIER)",
    "LOG_DISTANCE_TO_PRIOR_24H_HIGH": "LN(CURRENT_CLOSE/MAX_PREVIOUS_24_HIGH_EXCLUDING_CURRENT)",
    "REALIZED_VOL_24H": "SQRT(MEAN(EXACT_24_CLOSE_TO_CLOSE_LOG_RETURN_SQUARED))",
    "LOG_RELATIVE_VOLUME_1H": "LN(CURRENT_BASE_VOLUME/MEAN_PREVIOUS_24_BASE_VOLUME)",
    "DIRECTIONAL_EFFICIENCY_4H": "(SUM_POSITIVE_42_CHANGES-ABS_SUM_NEGATIVE)/(SUM_POSITIVE+ABS_SUM_NEGATIVE)",
    "TAKER_BUY_SHARE_1H_CENTERED": "ORDER_FLOW_FEATURES_V1_CURRENT_1H_SHARE_MINUS_0.5",
    "TAKER_BUY_SHARE_4H_CENTERED": "ORDER_FLOW_FEATURES_V1_NONOVERLAPPING_4H_SHARE_MINUS_0.5",
    FEATURE: "RAW_LATEST_SETTLED_FUNDING_RATE_WITH_FUNDING_TIME_STRICTLY_BEFORE_SIGNAL",
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
    "backend/app/research/wp014_model.py",
    "backend/app/research/wp014_lab.py",
    "backend/app/research/wp015_model.py",
    "backend/app/research/wp015_lab.py",
    "backend/app/research/artifacts.py",
    "backend/app/research/model_search_memory.py",
    "backend/app/research/search_memory_v2.py",
    "docs/contracts/PERPETUAL_FUNDING_CONTEXT_V1.md",
    MANIFEST_PATH,
    PROTOCOL_PATH,
    WALK_FORWARD_PATH,
    "pyproject.toml",
    "uv.lock",
)


class WP015Error(SearchMemoryError):
    """WP-015 fixed declaration or chronology was violated."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(variant: str) -> str:
    if variant not in STEMS:
        raise WP015Error("undeclared WP-015 configuration")
    return f"research/configs/wp015/{STEMS[variant]}.json"


def dependency_manifest(root: Path = ROOT) -> list[dict[str, str]]:
    return [{"path": path, "sha256": sha256(root / path)} for path in IMPLEMENTATION_PATHS]


def features_for(variant: str) -> tuple[str, ...]:
    return PRIMARY_FEATURES if variant == PRIMARY_VARIANT else FULL_FEATURES


def executable_spec(variant: str, root: Path = ROOT) -> ExecutableModelSpec:
    names = features_for(variant)
    funding_manifest = read_json(root / MANIFEST_PATH)
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
            "update_cadence": "ONCE_PER_FOLD_NO_VALIDATION_REFIT",
        },
        scaling={"scope": "NONE_RAW_GOVERNED_VALUES", "mean": False, "std": False},
        regularization={"kind": "FIXED_L2_LEAF_REGULARIZATION", "value": 1.0, "searched": False},
        hyperparameters={
            "parameters": dict(HGBR_PARAMETERS),
            "searched": 0,
            "feature_selection": "NONE",
            "funding_transformations": 0,
            "funding_thresholds": 0,
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
            "funding_manifest_id": funding_manifest["manifest_id"],
            "funding_logical_sha256": funding_manifest["canonical"]["logical_sha256"],
            "funding_availability": "STRICTLY_PRIOR_SETTLEMENT",
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
        raise WP015Error("funding-information mechanism was not admitted as a new family")
    primary.update(
        experiment_id=EXPERIMENTS[PRIMARY_VARIANT],
        variant=PRIMARY_VARIANT,
        hypothesis_role=ROLES[PRIMARY_VARIANT],
        spec=primary_spec.to_dict(),
    )
    control_spec = executable_spec(CONTROL_VARIANT, root)
    control_binding = bind_model_spec(control_spec)
    control = {
        "admitted": False,
        "authorized_as_matched_control": True,
        "classification": "KNOWN_INTERNAL_HGBR_MATCHED_CONTROL",
        "duplicate_gate_unchanged": True,
        "known_mechanism_experiment_ids": ["EXP-ML-022-SHALLOW-INTERNAL-HGBR"],
        "root_family": ROOT_FAMILY,
        "matched_experiment_ids": [],
        "behavior_hash": control_binding.behavior_hash,
        "structural_hash": control_binding.structural_hash,
        "executable_spec_hash": control_binding.executable_spec_hash,
        "dependency_hash": control_binding.dependency_hash,
        "experiment_id": EXPERIMENTS[CONTROL_VARIANT],
        "variant": CONTROL_VARIANT,
        "hypothesis_role": ROLES[CONTROL_VARIANT],
        "spec": control_spec.to_dict(),
    }
    return {
        "schema_version": 1,
        "work_package": "WP-015",
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
        "mechanism_distinction": "One strictly prior settled derivatives funding value adds new information to frozen F1-F8.",
        "matched_control_policy": "Internal HGBR is disclosed as the known WP-014 mechanism on the matched funding-available universe; no novelty is claimed.",
        "variants": [primary, control],
    }


def load_protocol(root: Path = ROOT) -> dict[str, Any]:
    document = read_json(root / PROTOCOL_PATH)
    if (
        document["folds"] != list(range(2020, 2025))
        or document["internal_features"] != list(FULL_FEATURES)
        or document["primary_feature_order"] != list(PRIMARY_FEATURES)
        or document["hgbr_parameters"] != HGBR_PARAMETERS
        or document["model_fits"] != 10
        or document["profiles"] != list(PROFILES)
        or document["funding"]["feature"] != FEATURE
        or document["funding"]["transformations"] != 0
    ):
        raise WP015Error("WP-015 protocol drifted")
    return document


def load_walk_forward(root: Path = ROOT) -> dict[str, Any]:
    document = read_json(root / WALK_FORWARD_PATH)
    if [fold["fold_id"] for fold in document["folds"]] != [
        f"DEV-{year}" for year in range(2020, 2025)
    ]:
        raise WP015Error("WP-015 validation folds drifted")
    return document


def validate_admission(root: Path = ROOT) -> dict[str, Any]:
    recorded = read_json(root / ADMISSION_PATH)
    if recorded != json.loads(json.dumps(novelty_decision(root))):
        raise WP015Error("WP-015 admission differs from deterministic output")
    return recorded


def validate_allocation(root: Path = ROOT) -> dict[str, Any]:
    allocation = read_json(root / ALLOCATION_PATH)
    required = {
        "new_economic_hypotheses": 1,
        "model_configurations": 2,
        "profile_evaluations": 8,
        "supervised_model_fits": 10,
        "funding_transformations": 0,
        "funding_thresholds": 0,
        "feature_subsets": 0,
        "algorithm_variants": 0,
        "hyperparameter_variants": 0,
        "threshold_variants": 0,
        "result_dependent_fork_increment": 0,
        "sealed_queries": 0,
    }
    if any(allocation.get(key) != value for key, value in required.items()):
        raise WP015Error("WP-015 allocation drifted")
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
        ):
            raise WP015Error("WP-015 preregistration drifted")
        hashes[variant] = sha256(root / relative)
    return hashes


def preflight(root: Path = ROOT) -> dict[str, Any]:
    protocol = load_protocol(root)
    admission = validate_admission(root)
    validate_allocation(root)
    preregistrations = validate_preregistrations(root)
    integrity = read_json(root / "reports/validation/WP-015-FUNDING-INTEGRITY.json")
    asof = read_json(root / "reports/validation/WP-015-FUNDING-ASOF-AUDIT.json")
    manifest = read_json(root / MANIFEST_PATH)
    if integrity["status"] != "PASS" or asof["status"] != "PASS":
        raise WP015Error("funding integrity/as-of audit failed")
    if any(
        (root / f"research/experiments/{item}/result.json").exists()
        for item in EXPERIMENTS.values()
    ):
        raise WP015Error("WP-015 results already exist")
    return {
        "schema_version": 1,
        "work_package": "WP-015",
        "status": "PASS",
        "protocol_id": protocol["protocol_id"],
        "family_classification": admission["family_classification"],
        "control_classification": admission["variants"][1]["classification"],
        "features": list(PRIMARY_FEATURES),
        "only_new_feature": FEATURE,
        "forbidden_features": [],
        "hgbr_parameters": dict(HGBR_PARAMETERS),
        "input_scaling": "NONE_RAW_GOVERNED_VALUES",
        "validation_years": list(range(2020, 2025)),
        "purge_boundary_hours": 216,
        "complete_outcomes_before_boundary": True,
        "funding_time_strictly_before_signal": asof["strict_funding_time_before_signal_time"],
        "matched_eligible_universe": True,
        "funding_records": manifest["records"],
        "signal_threshold": 0.0,
        "profiles": list(PROFILES),
        "model_fits": MAXIMUM_MODEL_FITS,
        "prediction_tolerance": PREDICTION_TOLERANCE,
        "preregistration_sha256": preregistrations,
        "market_results_observed": 0,
        "post_cutoff_access": 0,
        "sealed_queries": 0,
    }


__all__ = [name for name in globals() if name.isupper()] + [
    "WP015Error",
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
