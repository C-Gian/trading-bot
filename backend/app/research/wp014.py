"""WP-014 frozen governance, SEARCH_MEMORY admission, and preregistration gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .continuation_lab import DATASET_HASH, DATASET_ID, PROFILES
from .linear_model import ALGORITHM as OLS_ALGORITHM
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

ROOT_FAMILY = "FAM-SHALLOW-NONLINEAR-INTERNAL"
HYPOTHESIS_ID = "NONLINEAR_INTERNAL_SIGNAL_INTERACTIONS_V1"
PRIMARY_VARIANT = "SHALLOW_INTERNAL_HGBR"
CONTROL_VARIANT = "INTERNAL_LINEAR_MATCHED"
VARIANTS = (PRIMARY_VARIANT, CONTROL_VARIANT)
EXPERIMENTS = {
    PRIMARY_VARIANT: "EXP-ML-022-SHALLOW-INTERNAL-HGBR",
    CONTROL_VARIANT: "EXP-ML-023-INTERNAL-LINEAR-MATCHED",
}
ROLES = {PRIMARY_VARIANT: "ECONOMIC_CORE", CONTROL_VARIANT: "MATCHED_DUPLICATE_CONTROL"}
ALLOCATION_ID = "WP014-SHALLOW-NONLINEAR-ALLOCATION"
ALLOCATION_PATH = f"research/memory/registry/allocations/{ALLOCATION_ID}.json"
FAMILY_PATH = f"research/memory/registry/families/{ROOT_FAMILY}.json"
ADMISSION_PATH = "research/memory/registry/admissions/WP014-NOVELTY-ADMISSION.json"
LEDGER_PATH = "research/memory/registry/ledger/WP-014.jsonl"
OUTCOMES_PATH = "research/memory/registry/outcomes/WP-014.jsonl"
PROTOCOL_PATH = "research/protocols/WP-014-SHALLOW-INTERNAL-HGBR-V1.json"
STEMS = {
    PRIMARY_VARIANT: "shallow_internal_hgbr",
    CONTROL_VARIANT: "internal_linear_matched",
}
MAXIMUM_MODEL_FITS = 12
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
}

IMPLEMENTATION_PATHS = (
    "backend/app/data/policy.py",
    "backend/app/backtest/models.py",
    "backend/app/backtest/engine.py",
    "backend/app/research/evaluation_protocol.py",
    "backend/app/research/continuation_lab.py",
    "backend/app/research/order_flow.py",
    "backend/app/research/supervised.py",
    "backend/app/research/linear_model.py",
    "backend/app/research/wp014_model.py",
    "backend/app/research/wp014_lab.py",
    "backend/app/research/artifacts.py",
    "backend/app/research/model_search_memory.py",
    "backend/app/research/search_memory_v2.py",
    PROTOCOL_PATH,
    "pyproject.toml",
    "uv.lock",
)


class WP014Error(SearchMemoryError):
    """The fixed WP-014 declaration, novelty gate, or chronology was violated."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(variant: str) -> str:
    if variant not in STEMS:
        raise WP014Error("undeclared WP-014 configuration")
    return f"research/configs/wp014/{STEMS[variant]}.json"


def dependency_manifest(root: Path = ROOT) -> list[dict[str, str]]:
    return [{"path": path, "sha256": sha256(root / path)} for path in IMPLEMENTATION_PATHS]


def _feature_specs() -> tuple[dict[str, Any], ...]:
    return tuple(
        {"name": name, "transformation": TRANSFORMATIONS[name], "order": index + 1}
        for index, name in enumerate(FULL_FEATURES)
    )


def _common_spec_fields() -> dict[str, Any]:
    return {
        "label": {
            "version": LABEL_VERSION,
            "profile": "DEFAULT",
            "isolated": True,
            "invalid_unresolved": "EXCLUDE_COUNT_NEVER_IMPUTE",
        },
        "features": _feature_specs(),
        "signal_rule": {
            "field": "predicted_default_net_R",
            "operator": ">",
            "threshold": 0.0,
        },
        "execution_geometry": {
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
        "dataset": {
            "manifest_id": DATASET_ID,
            "content_hash": DATASET_HASH,
            "feature_version": FEATURE_VERSION,
            "order_flow_version": "ORDER_FLOW_FEATURES_V1",
            "maximum_timestamp": "2024-12-31T23:59:00Z",
        },
    }


def executable_spec(variant: str, root: Path = ROOT) -> ExecutableModelSpec:
    if variant not in VARIANTS:
        raise WP014Error("undeclared WP-014 configuration")
    relative = config_path(variant)
    implementation = tuple(
        DependencyIdentity(path, sha256(root / path)) for path in IMPLEMENTATION_PATHS
    )
    common = _common_spec_fields()
    if variant == PRIMARY_VARIANT:
        algorithm = f"SKLEARN_{SKLEARN_VERSION}_HIST_GRADIENT_BOOSTING_REGRESSOR"
        train = {
            "kind": "EXPANDING_CHRONOLOGICAL_PER_ANNUAL_FOLD",
            "folds": list(range(2019, 2025)),
            "purge_hours": 216,
            "training_signal_boundary": "STRICTLY_BEFORE_VALIDATION_START_MINUS_PURGE",
            "label_outcome_before_purge_boundary": True,
            "update_cadence": "ONCE_PER_FOLD_NO_VALIDATION_REFIT",
        }
        scaling = {"scope": "NONE_RAW_GOVERNED_F1_F8", "mean": False, "std": False}
        regularization = {
            "kind": "FIXED_L2_LEAF_REGULARIZATION",
            "value": 1.0,
            "searched": False,
        }
        hyperparameters = {
            "parameters": dict(HGBR_PARAMETERS),
            "searched": 0,
            "feature_selection": "NONE",
            "feature_variants": 0,
            "architecture_variants": 0,
        }
    else:
        # These fields intentionally reproduce the registered WP-008 LINEAR_FULL
        # behavior exactly. The control is disclosed as a duplicate replication,
        # never presented as a novel admission.
        algorithm = OLS_ALGORITHM
        train = {
            "kind": "EXPANDING_CHRONOLOGICAL",
            "folds": list(range(2019, 2025)),
            "purge_hours": 216,
            "training_signal_boundary": "STRICTLY_BEFORE",
            "label_outcome_before_validation": True,
        }
        scaling = {"scope": "TRAINING_ONLY_PER_FOLD", "mean": True, "std_ddof": 0}
        regularization = {"kind": "NONE", "searched": False}
        hyperparameters = {"searched": 0, "feature_selection": "NONE", "interactions": "NONE"}
    return ExecutableModelSpec(
        schema_version=2,
        root_family=ROOT_FAMILY,
        family=ROOT_FAMILY,
        algorithm=algorithm,
        label=common["label"],
        features=common["features"],
        train_window_rule=train,
        scaling=scaling,
        regularization=regularization,
        hyperparameters=hyperparameters,
        signal_rule=common["signal_rule"],
        execution_geometry=common["execution_geometry"],
        dataset=common["dataset"],
        cost_model_reference="BTCUSDT_SPOT_COST_V1",
        execution_model_reference="EXECUTION_MODEL_V2",
        implementation_dependencies=implementation,
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
        raise WP014Error("fixed HGBR proposal was not admitted as a new family")
    primary.update(
        experiment_id=EXPERIMENTS[PRIMARY_VARIANT],
        variant=PRIMARY_VARIANT,
        hypothesis_role=ROLES[PRIMARY_VARIANT],
        spec=primary_spec.to_dict(),
    )

    control_spec = executable_spec(CONTROL_VARIANT, root)
    control_binding = bind_model_spec(control_spec)
    exact = sorted(
        item["experiment_id"]
        for item in prior
        if item["behavior_hash"] == control_binding.behavior_hash
    )
    if exact != ["EXP-ML-014-LINEAR-NET-R-FULL"]:
        raise WP014Error("matched OLS control did not resolve to the frozen WP-008 duplicate")
    control = {
        "admitted": False,
        "authorized_as_matched_control": True,
        "classification": "DUPLICATE_MATCHED_CONTROL_REPLICATION",
        "duplicate_gate_unchanged": True,
        "root_family": ROOT_FAMILY,
        "matched_experiment_ids": exact,
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
        "work_package": "WP-014",
        "gate": "GOVERNED_MODEL_NOVELTY_ADMISSION_BEFORE_ANY_VALIDATION_RESULT",
        "proposed_root_family": ROOT_FAMILY,
        "proposed_hypothesis_id": HYPOTHESIS_ID,
        "family_classification": "NEW_FAMILY",
        "admitted": True,
        "market_results_observed_at_admission": 0,
        "classifier_modified": False,
        "renamed_to_force_novelty": False,
        "conditions_added_to_force_novelty": False,
        "reference_signatures": len(prior),
        "mechanism_distinction": (
            "A fixed low-capacity histogram gradient-boosted tree can represent bounded "
            "threshold/intersection relationships among raw F1-F8 that OLS cannot."
        ),
        "matched_control_policy": (
            "The OLS control is an explicitly disclosed duplicate replication of WP-008 "
            "LINEAR_FULL; duplicate detection is not weakened and no novelty is claimed."
        ),
        "variants": [primary, control],
    }


def validate_protocol(document: dict[str, Any]) -> None:
    model = document["models"][PRIMARY_VARIANT]
    control = document["models"][CONTROL_VARIANT]
    if (
        document["protocol_id"] != "WP-014-SHALLOW-INTERNAL-HGBR-V1"
        or document["root_family"] != ROOT_FAMILY
        or document["hypothesis_id"] != HYPOTHESIS_ID
        or document["primary_variant"] != PRIMARY_VARIANT
        or document["control_variant"] != CONTROL_VARIANT
        or document["features"] != list(FULL_FEATURES)
        or document["folds"] != list(range(2019, 2025))
        or document["profiles"] != list(PROFILES)
        or document["configurations"] != 2
        or document["profile_evaluations"] != 8
        or document["model_fits"] != 12
        or document["hyperparameter_variants"] != 0
        or document["feature_variants"] != 0
        or document["architecture_variants"] != 0
        or document["signal"]
        != {
            "operator": ">",
            "predicted_field": "predicted_default_net_R",
            "threshold": 0.0,
            "threshold_variants": 0,
        }
        or model["parameters"] != HGBR_PARAMETERS
        or model["input_scaling"] != "NONE_RAW_GOVERNED_VALUES"
        or control["algorithm"] != OLS_ALGORITHM
        or control["input_scaling"] != "TRAINING_ONLY_MEAN_STD_DDOF_0"
        or document["training"]["purge_boundary_hours"] != 216
        or document["training"]["validation_refits"] != 0
        or document["target"] != LABEL_VERSION
        or document["development_cutoff"] != "2024-12-31T23:59:00Z"
        or document["sklearn_version"] != SKLEARN_VERSION
    ):
        raise WP014Error("WP-014 protocol drifted from the fixed declaration")


def load_protocol(root: Path = ROOT) -> dict[str, Any]:
    document = read_json(root / PROTOCOL_PATH)
    validate_protocol(document)
    return document


def validate_admission(root: Path = ROOT) -> dict[str, Any]:
    recorded = read_json(root / ADMISSION_PATH)
    expected = json.loads(json.dumps(novelty_decision(root)))
    if recorded != expected:
        raise WP014Error("WP-014 admission differs from deterministic SEARCH_MEMORY output")
    return recorded


def validate_allocation(root: Path = ROOT) -> dict[str, Any]:
    allocation = read_json(root / ALLOCATION_PATH)
    required = {
        "allocation_id": ALLOCATION_ID,
        "root_family": ROOT_FAMILY,
        "hypothesis_id": HYPOTHESIS_ID,
        "new_economic_hypotheses": 1,
        "model_configurations": 2,
        "profile_evaluations": 8,
        "supervised_model_fits": 12,
        "numeric_parameter_variants": 0,
        "hyperparameter_variants": 0,
        "feature_variants": 0,
        "threshold_variants": 0,
        "architecture_variants": 0,
        "model_selection_forks": 0,
        "sealed_queries": 0,
    }
    if any(allocation.get(key) != value for key, value in required.items()):
        raise WP014Error("WP-014 allocation differs from the Owner-authorized budget")
    return allocation


def validate_preregistrations(root: Path = ROOT) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for variant, experiment in EXPERIMENTS.items():
        relative = f"research/experiments/{experiment}/preregistration.json"
        document = validate_preregistration(root / relative)
        space = document["parameter_space"]
        if (
            document["status"] != "PREREGISTERED"
            or space["allocation_id"] != ALLOCATION_ID
            or space["variant"] != variant
            or space["features"] != list(FULL_FEATURES)
            or space["numeric_parameter_variants"] != 0
            or space["hyperparameter_variants"] != 0
            or space["feature_variants"] != 0
            or space["threshold_variants"] != 0
            or space["architecture_variants"] != 0
            or space["signal_threshold"] != 0.0
        ):
            raise WP014Error("WP-014 preregistration drifted")
        hashes[variant] = sha256(root / relative)
    return hashes


def preflight(root: Path = ROOT) -> dict[str, Any]:
    protocol = load_protocol(root)
    admission = validate_admission(root)
    allocation = validate_allocation(root)
    preregistrations = validate_preregistrations(root)
    if any((root / f"research/experiments/{e}/result.json").exists() for e in EXPERIMENTS.values()):
        raise WP014Error("WP-014 results already exist")
    return {
        "schema_version": 1,
        "work_package": "WP-014",
        "status": "PASS",
        "protocol_id": protocol["protocol_id"],
        "family_classification": admission["family_classification"],
        "control_classification": admission["variants"][1]["classification"],
        "features": list(FULL_FEATURES),
        "forbidden_features": [],
        "hgbr_parameters": dict(HGBR_PARAMETERS),
        "hgbr_input_scaling": "NONE_RAW_GOVERNED_VALUES",
        "control_input_scaling": "TRAINING_ONLY_MEAN_STD_DDOF_0",
        "purge_boundary_hours": 216,
        "complete_outcomes_before_boundary": True,
        "signal_threshold": 0.0,
        "profiles": list(PROFILES),
        "model_fits": MAXIMUM_MODEL_FITS,
        "prediction_tolerance": PREDICTION_TOLERANCE,
        "allocation_id": allocation["allocation_id"],
        "preregistration_sha256": preregistrations,
        "market_results_observed": 0,
        "post_cutoff_access": 0,
        "sealed_queries": 0,
    }


__all__ = [name for name in globals() if name.isupper()] + [
    "WP014Error",
    "config_path",
    "dependency_manifest",
    "executable_spec",
    "load_protocol",
    "novelty_decision",
    "preflight",
    "validate_admission",
    "validate_allocation",
    "validate_preregistrations",
    "validate_protocol",
]
