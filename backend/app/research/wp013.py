"""WP-013 frozen governance and pre-result novelty/preregistration gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .continuation_lab import DATASET_HASH, DATASET_ID, PROFILES
from .linear_model import ALGORITHM, MIN_STD_EXCLUSIVE, SIGNAL_THRESHOLD
from .model_search_memory import ExecutableModelSpec, admit_model_spec, model_fingerprint
from .nfci_context import CONTEXT_SERIES, CONTEXT_VERSION
from .records import validate_preregistration
from .registry import alias_map, signatures
from .runner import sha256
from .search_memory import SearchMemoryError
from .search_memory_v2 import DependencyIdentity
from .supervised import FEATURE_VERSION, FULL_FEATURES, LABEL_VERSION
from .wp004 import ROOT

ROOT_FAMILY = "FAM-CONTEXTUAL-MACRO-INTERACTIONS"
HYPOTHESIS_ID = "NFCI_MODULATES_INTERNAL_SIGNAL_VALUE_V1"
ARCHITECTURE = "CONTEXTUAL_NFCI_INTERACTION_OLS_V1"
PRIMARY_VARIANT = "NFCI_CONTEXT_INTERACTIONS"
CONTROL_VARIANT = "INTERNAL_ONLY_MATCHED_NFCI"
VARIANTS = (PRIMARY_VARIANT, CONTROL_VARIANT)
EXPERIMENTS = {
    PRIMARY_VARIANT: "EXP-ML-020-NFCI-CONTEXT-INTERACTIONS",
    CONTROL_VARIANT: "EXP-ML-021-INTERNAL-NFCI-MATCHED",
}
ROLES = {
    PRIMARY_VARIANT: "ECONOMIC_CORE",
    CONTROL_VARIANT: "MATCHED_INTERNAL_ONLY_CONTROL",
}
STEMS = {
    PRIMARY_VARIANT: "nfci_context_interactions",
    CONTROL_VARIANT: "internal_only_matched_nfci",
}
INTERACTION_FEATURES = tuple(f"{name}_X_NFCI" for name in FULL_FEATURES)
PRIMARY_FEATURES = FULL_FEATURES + INTERACTION_FEATURES
FEATURES = {PRIMARY_VARIANT: PRIMARY_FEATURES, CONTROL_VARIANT: FULL_FEATURES}
FOLD_COUNT = 6
MAXIMUM_MODEL_FITS = 12

ALLOCATION_ID = "WP013-CONTEXTUAL-NFCI-ALLOCATION"
ALLOCATION_PATH = f"research/memory/registry/allocations/{ALLOCATION_ID}.json"
FAMILY_PATH = f"research/memory/registry/families/{ROOT_FAMILY}.json"
ADMISSION_PATH = "research/memory/registry/admissions/WP013-NOVELTY-ADMISSION.json"
PROTOCOL_PATH = "research/protocols/WP-013-CONTEXTUAL-NFCI-INTERACTIONS-V1.json"
LEDGER_PATH = "research/memory/registry/ledger/WP-013.jsonl"
OUTCOMES_PATH = "research/memory/registry/outcomes/WP-013.jsonl"
MACRO_MANIFEST = "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json"

IMPLEMENTATION_PATHS = (
    "backend/app/data/policy.py",
    "backend/app/backtest/models.py",
    "backend/app/backtest/engine.py",
    "backend/app/research/evaluation_protocol.py",
    "backend/app/research/continuation_lab.py",
    "backend/app/research/order_flow.py",
    "backend/app/research/supervised.py",
    "backend/app/research/linear_model.py",
    "backend/app/research/macro.py",
    "backend/app/research/nfci_context.py",
    "backend/app/research/wp013_lab.py",
    "backend/app/research/artifacts.py",
    "backend/app/research/search_memory_v2.py",
    PROTOCOL_PATH,
)

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


class WP013Error(SearchMemoryError):
    """The WP-013 frozen declaration or chronology gate failed."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(variant: str) -> str:
    if variant not in VARIANTS:
        raise WP013Error("undeclared WP-013 configuration")
    return f"research/configs/wp013/{STEMS[variant]}.json"


def dependency_manifest(root: Path = ROOT) -> list[dict[str, str]]:
    return [{"path": path, "sha256": sha256(root / path)} for path in IMPLEMENTATION_PATHS]


def load_protocol(root: Path = ROOT) -> dict[str, Any]:
    document = read_json(root / PROTOCOL_PATH)
    validate_protocol(document)
    return document


def validate_protocol(document: dict[str, Any]) -> None:
    if (
        document["protocol_id"] != "WP-013-CONTEXTUAL-NFCI-INTERACTIONS-V1"
        or document["architecture"] != ARCHITECTURE
        or document["root_family"] != ROOT_FAMILY
        or document["primary_variant"] != PRIMARY_VARIANT
        or document["control_variant"] != CONTROL_VARIANT
        or document["configurations"] != 2
        or document["profile_evaluations"] != 8
        or document["numeric_parameter_variants"] != 0
        or document["interaction_subsets_searched"] != 0
        or document["profiles"] != list(PROFILES)
        or document["folds"] != list(range(2019, 2025))
    ):
        raise WP013Error("WP-013 protocol identity or budget drifted")
    features = document["features"]
    if (
        tuple(features["base"]) != FULL_FEATURES
        or tuple(features["control"]) != FULL_FEATURES
        or tuple(features["interactions"]) != INTERACTION_FEATURES
        or features["interaction_formula"]
        != "Ii=RAW_Fi*RAW_POINT_IN_TIME_NFCI_BEFORE_STANDARDIZATION"
    ):
        raise WP013Error("WP-013 feature matrix drifted")
    context = document["context"]
    if (
        context["version"] != CONTEXT_VERSION
        or context["series"] != CONTEXT_SERIES
        or context["direct_feature_count"] != 0
        or context["thresholds"] != 0
        or context["context_transformations_searched"] != 0
        or context["lag_searches"] != 0
        or context["smoothing"] != "NONE"
        or context["clipping"] != "NONE"
        or context["interpolation"] != "NONE"
    ):
        raise WP013Error("raw NFCI context semantics drifted")
    training, model, execution = document["training"], document["model"], document["execution"]
    if (
        training["purge_boundary_hours"] != 216
        or training["label"] != LABEL_VERSION
        or training["scaling"] != "TRAINING_ONLY_MEAN_AND_POPULATION_STD_DDOF_0"
        or "MATCHED_ACROSS_CONFIGS" not in training["eligibility"]
        or model["algorithm"] != ALGORITHM
        or model["minimum_std_exclusive"] != MIN_STD_EXCLUSIVE
        or model["signal_threshold"] != SIGNAL_THRESHOLD
        or model["threshold_searches"] != 0
        or model["hyperparameter_searches"] != 0
        or model["regularization"] != "NONE"
        or not model["require_full_column_rank"]
        or model["feature_dropping"]
        or model["coefficient_thresholding"]
        or model["pca"]
        or execution != {
            "direction": "LONG",
            "entry": "NEXT_CANONICAL_1M_OPEN",
            "max_hold_minutes": 1440,
            "position_policy": "SINGLE_LONG_NO_OVERLAP",
            "stop_fraction": 0.02,
            "target_fraction": 0.04,
        }
    ):
        raise WP013Error("WP-013 training/model/execution declaration drifted")


def _feature_specs(variant: str) -> tuple[dict[str, Any], ...]:
    items = []
    for index, name in enumerate(FEATURES[variant]):
        transformation = (
            TRANSFORMATIONS[name]
            if name in TRANSFORMATIONS
            else f"RAW_{name.removesuffix('_X_NFCI')}*RAW_POINT_IN_TIME_NFCI"
        )
        items.append({"name": name, "transformation": transformation, "order": index + 1})
    return tuple(items)


def executable_spec(variant: str, root: Path = ROOT) -> ExecutableModelSpec:
    if variant not in VARIANTS:
        raise WP013Error("undeclared WP-013 configuration")
    relative = config_path(variant)
    implementation = tuple(DependencyIdentity(p, sha256(root / p)) for p in IMPLEMENTATION_PATHS)
    return ExecutableModelSpec(
        schema_version=2,
        root_family=ROOT_FAMILY,
        family=ROOT_FAMILY,
        algorithm=ALGORITHM,
        label={"version": LABEL_VERSION, "profile": "DEFAULT", "isolated": True,
               "invalid_unresolved": "EXCLUDE_COUNT_NEVER_IMPUTE"},
        features=_feature_specs(variant),
        train_window_rule={
            "kind": "EXPANDING_CHRONOLOGICAL_PER_ANNUAL_FOLD",
            "architecture": ARCHITECTURE,
            "folds": list(range(2019, 2025)),
            "purge_hours": 216,
            "training_signal_boundary": "STRICTLY_BEFORE_VALIDATION_START_MINUS_PURGE",
            "label_outcome_before_purge_boundary": True,
            "eligibility": "INTERNAL_FEATURES_AND_POINT_IN_TIME_NFCI_BOTH_AVAILABLE_MATCHED_ACROSS_CONFIGS",
            "context": {
                "version": CONTEXT_VERSION,
                "series": CONTEXT_SERIES,
                "role": "RAW_INTERACTION_ONLY" if variant == PRIMARY_VARIANT else "MATCHED_ELIGIBILITY_ONLY",
                "direct_predictor": False,
                "thresholds": 0,
                "transformations_searched": 0,
            },
            "update_cadence": "ONCE_PER_FOLD_NO_VALIDATION_REFIT",
        },
        scaling={"scope": "TRAINING_ONLY_ALL_COLUMNS", "mean": True, "std_ddof": 0,
                 "weighted": False, "interactions_formed_before_scaling": True},
        regularization={"kind": "NONE", "searched": False},
        hyperparameters={"searched": 0, "feature_selection": "NONE",
                         "interaction_subsets_searched": 0, "context_transforms_searched": 0},
        signal_rule={"field": "predicted_default_net_R", "operator": ">", "threshold": 0.0},
        execution_geometry={"direction": "LONG", "reference": "JUST_COMPLETED_1H_CLOSE",
                            "entry": "NEXT_CANONICAL_1M_OPEN", "stop_fraction": 0.02,
                            "target_fraction": 0.04, "max_hold_minutes": 1440,
                            "position_policy": "SINGLE_LONG_NO_OVERLAP",
                            "profiles": list(PROFILES), "stress_retrain": False},
        dataset={"manifest_id": DATASET_ID, "content_hash": DATASET_HASH,
                 "feature_version": FEATURE_VERSION, "context_version": CONTEXT_VERSION,
                 "context_source_version": "ALFRED_MACRO_CONTEXT_V1",
                 "order_flow_version": "ORDER_FLOW_FEATURES_V1",
                 "maximum_timestamp": "2024-12-31T23:59:00Z"},
        cost_model_reference="BTCUSDT_SPOT_COST_V1",
        execution_model_reference="EXECUTION_MODEL_V2",
        implementation_dependencies=implementation,
        config_dependencies=(DependencyIdentity(relative, sha256(root / relative)),),
    )


def novelty_decisions(root: Path = ROOT) -> list[dict[str, Any]]:
    prior = signatures(root, exclude_experiment_ids=set(EXPERIMENTS.values()))
    decisions = []
    for variant in VARIANTS:
        spec = executable_spec(variant, root)
        decision = admit_model_spec(spec, declared_family=ROOT_FAMILY, signatures=prior,
                                    aliases=alias_map(root),
                                    declared_fingerprint=model_fingerprint(spec))
        decision.update(experiment_id=EXPERIMENTS[variant], variant=variant,
                        hypothesis_role=ROLES[variant], spec=spec.to_dict())
        decisions.append(decision)
        prior.append({"experiment_id": EXPERIMENTS[variant], "root_family": ROOT_FAMILY,
                      "behavior_hash": decision["behavior_hash"],
                      "structural_hash": decision["structural_hash"]})
    if decisions[0]["classification"] != "NEW_FAMILY":
        raise WP013Error("contextual interaction mechanism was not admitted as a new family")
    if decisions[1]["classification"] != "DESCENDANT_MECHANISM_CHANGE":
        raise WP013Error("matched control was not admitted as a descendant")
    return decisions


def novelty_decision(root: Path = ROOT) -> dict[str, Any]:
    decisions = novelty_decisions(root)
    return {
        "schema_version": 1, "work_package": "WP-013", "version": "SEARCH_MEMORY_V2",
        "gate": "GOVERNED_MODEL_NOVELTY_ADMISSION_BEFORE_ANY_VALIDATION_RESULT",
        "proposed_root_family": ROOT_FAMILY, "proposed_hypothesis_id": HYPOTHESIS_ID,
        "entry_event": "PREDICTED_DEFAULT_NET_R_STRICTLY_ABOVE_ZERO",
        "mechanism_distinction": (
            "Raw point-in-time NFCI enters only through eight fixed products with the frozen "
            "internal features, permitting continuous context-dependent slopes. It is neither "
            "an additive macro predictor nor a threshold regime gate."
        ),
        "reference_signatures": len(signatures(root, exclude_experiment_ids=set(EXPERIMENTS.values()))),
        "family_classification": decisions[0]["classification"], "admitted": True,
        "classifier_modified": False, "renamed_to_force_novelty": False,
        "conditions_added_to_force_novelty": False, "market_results_observed_at_admission": 0,
        "variants": decisions,
    }


def validate_admission(root: Path = ROOT) -> dict[str, Any]:
    recorded = read_json(root / ADMISSION_PATH)
    if recorded != json.loads(json.dumps(novelty_decision(root))):
        raise WP013Error("WP-013 admission differs from deterministic SEARCH_MEMORY output")
    if recorded["market_results_observed_at_admission"] != 0:
        raise WP013Error("admission observed market results")
    return recorded


def validate_allocation(root: Path = ROOT) -> dict[str, Any]:
    item = read_json(root / ALLOCATION_PATH)
    required = {
        "allocation_id": ALLOCATION_ID, "root_family": ROOT_FAMILY,
        "hypothesis_id": HYPOTHESIS_ID, "new_economic_hypotheses": 1,
        "model_configurations": 2, "profile_evaluations": 8,
        "supervised_model_fits": MAXIMUM_MODEL_FITS, "numeric_parameter_variants": 0,
        "interaction_subsets_searched": 0, "context_transforms_searched": 0,
        "threshold_searches": 0, "sealed_queries": 0,
    }
    if any(item.get(key) != value for key, value in required.items()):
        raise WP013Error("WP-013 allocation drifted")
    family = read_json(root / FAMILY_PATH)
    if family["family_id"] != ROOT_FAMILY or family["allocation_id"] != ALLOCATION_ID:
        raise WP013Error("WP-013 family record drifted")
    return item


def validate_preregistrations(root: Path = ROOT) -> dict[str, str]:
    hashes = {}
    for variant in VARIANTS:
        relative = f"research/experiments/{EXPERIMENTS[variant]}/preregistration.json"
        document = validate_preregistration(root / relative)
        space = document["parameter_space"]
        if (document["status"] != "PREREGISTERED" or space["allocation_id"] != ALLOCATION_ID
                or space["numeric_parameter_variants"] != 0
                or space["interaction_subsets_searched"] != 0
                or space["context_transforms_searched"] != 0
                or space["nfci_direct_feature"]):
            raise WP013Error("WP-013 preregistration drifted")
        hashes[variant] = sha256(root / relative)
    return hashes


def preflight(root: Path = ROOT) -> dict[str, Any]:
    protocol = load_protocol(root)
    admission = validate_admission(root)
    allocation = validate_allocation(root)
    preregs = validate_preregistrations(root)
    macro = read_json(root / MACRO_MANIFEST)
    return {
        "schema_version": 1, "work_package": "WP-013", "status": "PASS",
        "protocol_id": protocol["protocol_id"], "architecture": ARCHITECTURE,
        "root_family": ROOT_FAMILY, "hypothesis_id": HYPOTHESIS_ID,
        "family_classification": admission["family_classification"],
        "configurations": list(VARIANTS), "primary_variant": PRIMARY_VARIANT,
        "feature_counts": {v: len(FEATURES[v]) for v in VARIANTS},
        "context_version": CONTEXT_VERSION, "context_series": CONTEXT_SERIES,
        "nfci_direct_feature": False, "interaction_count": len(INTERACTION_FEATURES),
        "interactions_before_standardization": True, "matched_eligible_universe": True,
        "purge_boundary_hours": 216, "training_only_scaling": True,
        "full_rank_required": True, "macro_source_version": macro["version"],
        "macro_vintage_end": macro["coverage"]["vintage_end"],
        "maximum_model_fits": MAXIMUM_MODEL_FITS, "allocation_id": allocation["allocation_id"],
        "preregistration_sha256": preregs, "market_results_observed": 0,
        "sealed_queries": 0,
    }


__all__ = [name for name in globals() if name.isupper()] + [
    "WP013Error", "config_path", "dependency_manifest", "executable_spec",
    "load_protocol", "novelty_decision", "preflight", "validate_admission",
    "validate_allocation", "validate_preregistrations", "validate_protocol",
]
