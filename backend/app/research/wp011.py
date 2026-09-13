"""WP-011 governance: frozen protocol, novelty admission and allocation validation.

`FAM-ADAPTIVE-EWLS-MACRO` is submitted to SEARCH_MEMORY_V2 before any market result. The
family is a genuinely distinct mechanism: time-varying recency-weighted coefficients over
internal market features plus point-in-time macro context, not the fixed global linear
weights WP-008 rejected.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .continuation_lab import DATASET_HASH, DATASET_ID, PROFILES
from .ewls import ALGORITHM, HALF_LIFE_DAYS, MODEL_VERSION, SIGNAL_THRESHOLD, UPDATE_CADENCE
from .macro import FEATURE_VERSION as MACRO_FEATURE_VERSION
from .macro import MACRO_FEATURES
from .model_search_memory import ExecutableModelSpec, admit_model_spec, model_fingerprint
from .records import validate_preregistration
from .registry import alias_map, signatures
from .runner import sha256 as runner_sha256
from .search_memory import SearchMemoryError
from .search_memory_v2 import DependencyIdentity
from .supervised import FEATURE_VERSION as INTERNAL_FEATURE_VERSION
from .supervised import FULL_FEATURES, LABEL_VERSION
from .wp004 import ROOT

ROOT_FAMILY = "FAM-ADAPTIVE-EWLS-MACRO"
HYPOTHESIS_ID = "DYNAMIC_INTERNAL_MACRO_NET_R_V1"
PRIMARY_VARIANT = "EWLS_INTERNAL_MACRO"
ABLATION_VARIANT = "EWLS_INTERNAL_ONLY"
VARIANTS = (PRIMARY_VARIANT, ABLATION_VARIANT)
ROLES = {
    PRIMARY_VARIANT: "ECONOMIC_CORE",
    ABLATION_VARIANT: "STRUCTURAL_ABLATION_VARIANT",
}
EXPERIMENTS = {
    PRIMARY_VARIANT: "EXP-ML-016-EWLS-INTERNAL-MACRO",
    ABLATION_VARIANT: "EXP-ML-017-EWLS-INTERNAL-ONLY",
}
STEMS = {PRIMARY_VARIANT: "ewls_internal_macro", ABLATION_VARIANT: "ewls_internal_only"}
ALLOCATION_ID = "WP011-ADAPTIVE-EWLS-ALLOCATION"
ALLOCATION_PATH = f"research/memory/registry/allocations/{ALLOCATION_ID}.json"
FAMILY_PATH = f"research/memory/registry/families/{ROOT_FAMILY}.json"
ADMISSION_PATH = "research/memory/registry/admissions/WP011-NOVELTY-ADMISSION.json"
PROTOCOL_PATH = "research/protocols/WP-011-ADAPTIVE-EWLS-MACRO-V1.json"
LEDGER_PATH = "research/memory/registry/ledger/WP-011.jsonl"
OUTCOMES_PATH = "research/memory/registry/outcomes/WP-011.jsonl"

MACRO_MANIFEST = "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json"
DATASET_MANIFEST = "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
ORDER_FLOW_MANIFEST = "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json"

IMPLEMENTATION_PATHS = (
    "backend/app/data/policy.py",
    "backend/app/backtest/models.py",
    "backend/app/backtest/engine.py",
    "backend/app/research/evaluation_protocol.py",
    "backend/app/research/continuation_lab.py",
    "backend/app/research/order_flow.py",
    "backend/app/research/supervised.py",
    "backend/app/research/macro.py",
    "backend/app/research/ewls.py",
    "backend/app/research/wp011_lab.py",
    "backend/app/research/artifacts.py",
    "backend/app/research/search_memory_v2.py",
    PROTOCOL_PATH,
)
SPEC_DEPENDENCY_PATHS = IMPLEMENTATION_PATHS


class WP011Error(SearchMemoryError):
    """WP-011 governance, admission, or frozen-specification validation failed."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(variant: str) -> str:
    if variant not in VARIANTS:
        raise WP011Error("undeclared WP-011 configuration")
    return f"research/configs/wp011/{STEMS[variant]}.json"


def sha256(path: Path) -> str:
    return runner_sha256(path)


def load_protocol(root: Path = ROOT) -> dict[str, Any]:
    document = read_json(root / PROTOCOL_PATH)
    validate_protocol(document)
    return document


def validate_protocol(document: dict[str, Any]) -> None:
    """Fail closed if any frozen declaration drifted."""
    features, training, model = document["features"], document["training"], document["model"]
    if document["protocol_id"] != "WP-011-ADAPTIVE-EWLS-MACRO-V1":
        raise WP011Error("WP-011 protocol identity changed")
    if tuple(features[PRIMARY_VARIANT]) != FULL_FEATURES + MACRO_FEATURES:
        raise WP011Error("primary feature order is not the frozen 8 internal + 8 macro set")
    if tuple(features[ABLATION_VARIANT]) != FULL_FEATURES:
        raise WP011Error("ablation feature order is not exactly the frozen internal set")
    if len(features[PRIMARY_VARIANT]) != 16 or len(features[ABLATION_VARIANT]) != 8:
        raise WP011Error("feature counts drifted from 16/8")
    if (
        training["purge_boundary_hours"] != 216
        or training["half_life_days"] != 180
        or training["half_life_variants"] != 0
        or training["label"] != "ISOLATED_FIXED_PLAN_DEFAULT_NET_R_V1"
        or training["scaling"] != "TRAINING_ONLY_WEIGHTED_MEAN_AND_POPULATION_VARIANCE_SAME_WEIGHTS"
        or training["recency_weight"] != "EXP(-LN(2)*AGE_DAYS/180)"
    ):
        raise WP011Error("frozen training declaration drifted")
    if (
        model["version"] != MODEL_VERSION
        or model["algorithm"] != ALGORITHM
        or model["update_cadence"] != UPDATE_CADENCE
        or model["signal_threshold"] != SIGNAL_THRESHOLD
        or model["threshold_searches"] != 0
        or model["hyperparameter_searches"] != 0
        or model["regularization"] != "NONE"
        or model["coefficient_thresholding"]
        or model["feature_dropping"]
        or model["validation_refit"]
    ):
        raise WP011Error("frozen model declaration drifted")
    execution = document["execution"]
    if (
        execution["stop_fraction"] != 0.02
        or execution["target_fraction"] != 0.04
        or execution["max_hold_minutes"] != 1440
        or document["profiles"] != ["DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"]
        or document["configurations"] != 2
        or document["profile_evaluations"] != 8
        or document["numeric_parameter_variants"] != 0
    ):
        raise WP011Error("frozen execution or budget declaration drifted")
    if [fold["fold_id"] for fold in document["folds"]] != [f"DEV-{y}" for y in range(2019, 2025)]:
        raise WP011Error("frozen annual folds changed")
    if document["macro_feature_version"] != MACRO_FEATURE_VERSION:
        raise WP011Error("macro feature version changed")
    if document["internal_feature_version"] != INTERNAL_FEATURE_VERSION:
        raise WP011Error("internal feature version changed")
    groups = document["feature_groups"]
    grouped = [name for names in groups.values() for name in names]
    if sorted(grouped) != sorted(features[PRIMARY_VARIANT]) or len(grouped) != 16:
        raise WP011Error("grouped contribution map does not partition the primary features")


def dependency_manifest(root: Path = ROOT) -> list[dict[str, str]]:
    return [{"path": path, "sha256": sha256(root / path)} for path in SPEC_DEPENDENCY_PATHS]


TRANSFORMATIONS = {
    "LOG_RETURN_1H": "LN(CURRENT_1H_CLOSE/CURRENT_1H_OPEN)",
    "LOG_RETURN_24H": "LN(CURRENT_1H_CLOSE/CLOSE_24H_EARLIER)",
    "LOG_DISTANCE_TO_PRIOR_24H_HIGH": "LN(CURRENT_CLOSE/MAX_PREVIOUS_24_HIGH_EXCLUDING_CURRENT)",
    "REALIZED_VOL_24H": "SQRT(MEAN(EXACT_24_CLOSE_TO_CLOSE_LOG_RETURN_SQUARED))",
    "LOG_RELATIVE_VOLUME_1H": "LN(CURRENT_BASE_VOLUME/MEAN_PREVIOUS_24_BASE_VOLUME)",
    "DIRECTIONAL_EFFICIENCY_4H": (
        "(SUM_POSITIVE_42_CHANGES-ABS_SUM_NEGATIVE)/(SUM_POSITIVE+ABS_SUM_NEGATIVE)"
    ),
    "TAKER_BUY_SHARE_1H_CENTERED": "ORDER_FLOW_FEATURES_V1_CURRENT_1H_SHARE_MINUS_0.5",
    "TAKER_BUY_SHARE_4H_CENTERED": "ORDER_FLOW_FEATURES_V1_NONOVERLAPPING_4H_SHARE_MINUS_0.5",
    "DFF_LEVEL": "ALFRED_POINT_IN_TIME_LATEST_AVAILABLE_DFF",
    "DGS10_LEVEL": "ALFRED_POINT_IN_TIME_LATEST_AVAILABLE_DGS10",
    "T10Y2Y_LEVEL": "ALFRED_POINT_IN_TIME_LATEST_AVAILABLE_T10Y2Y",
    "VIX_LEVEL": "ALFRED_POINT_IN_TIME_LATEST_AVAILABLE_VIXCLS",
    "NFCI_LEVEL": "ALFRED_POINT_IN_TIME_LATEST_AVAILABLE_NFCI",
    "WALCL_LOG_CHANGE_28D": (
        "LN(LATEST_AVAILABLE_WALCL/POINT_IN_TIME_WALCL_AT_OR_BEFORE_MINUS_28D)"
    ),
    "CPI_YOY": (
        "100*(LATEST_AVAILABLE_CPIAUCSL/POINT_IN_TIME_CPIAUCSL_12_OBSERVATION_MONTHS_EARLIER-1)"
    ),
    "UNRATE_LEVEL": "ALFRED_POINT_IN_TIME_LATEST_AVAILABLE_UNRATE",
}


def _feature_specs(variant: str, root: Path = ROOT) -> tuple[dict[str, Any], ...]:
    names = load_protocol(root)["features"][variant]
    return tuple(
        {"name": name, "transformation": TRANSFORMATIONS[name], "order": index + 1}
        for index, name in enumerate(names)
    )


def executable_spec(variant: str, root: Path = ROOT) -> ExecutableModelSpec:
    if variant not in VARIANTS:
        raise WP011Error("undeclared WP-011 configuration")
    relative = config_path(variant)
    protocol = load_protocol(root)
    implementation = tuple(
        DependencyIdentity(path, sha256(root / path)) for path in SPEC_DEPENDENCY_PATHS
    )
    return ExecutableModelSpec(
        schema_version=2,
        root_family=ROOT_FAMILY,
        family=ROOT_FAMILY,
        algorithm=ALGORITHM,
        label={
            "version": LABEL_VERSION,
            "profile": "DEFAULT",
            "isolated": True,
            "invalid_unresolved": "EXCLUDE_COUNT_NEVER_IMPUTE",
        },
        features=_feature_specs(variant, root),
        train_window_rule={
            "kind": "EXPANDING_CHRONOLOGICAL_MONTHLY_RECENCY_WEIGHTED",
            "update_cadence": UPDATE_CADENCE,
            "folds": [2019, 2020, 2021, 2022, 2023, 2024],
            "purge_hours": 216,
            "training_signal_boundary": "STRICTLY_BEFORE_EFFECTIVE_MINUS_PURGE",
            "label_outcome_before_purge_boundary": True,
            "recency_weight": "EXP(-LN(2)*AGE_DAYS/180)",
            "half_life_days": HALF_LIFE_DAYS,
            "half_life_variants": 0,
        },
        scaling={
            "scope": "TRAINING_ONLY_PER_MONTHLY_MODEL",
            "mean": True,
            "std_ddof": 0,
            "weighted": True,
        },
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
            "feature_version": INTERNAL_FEATURE_VERSION,
            "macro_feature_version": MACRO_FEATURE_VERSION,
            "macro_source_version": protocol["macro_source_version"],
            "order_flow_version": "ORDER_FLOW_FEATURES_V1",
            "maximum_timestamp": "2024-12-31T23:59:00Z",
        },
        cost_model_reference="BTCUSDT_SPOT_COST_V1",
        execution_model_reference="EXECUTION_MODEL_V2",
        implementation_dependencies=implementation,
        config_dependencies=(DependencyIdentity(relative, sha256(root / relative)),),
    )


def novelty_decisions(root: Path = ROOT) -> list[dict[str, Any]]:
    """Classify both configurations against every registered executable signature."""
    prior = signatures(root, exclude_experiment_ids=set(EXPERIMENTS.values()))
    aliases = alias_map(root)
    decisions = []
    for variant in VARIANTS:
        spec = executable_spec(variant, root)
        try:
            decision = admit_model_spec(
                spec,
                declared_family=ROOT_FAMILY,
                signatures=prior,
                aliases=aliases,
                declared_fingerprint=model_fingerprint(spec),
            )
        except SearchMemoryError as exc:
            raise WP011Error(str(exc)) from exc
        decision.update(
            experiment_id=EXPERIMENTS[variant],
            variant=variant,
            hypothesis_role=ROLES[variant],
            spec=json.loads(json.dumps(spec.to_dict())),
        )
        decisions.append(decision)
        prior.append(
            {
                "experiment_id": EXPERIMENTS[variant],
                "root_family": ROOT_FAMILY,
                "behavior_hash": decision["behavior_hash"],
                "structural_hash": decision["structural_hash"],
            }
        )
    if decisions[0]["classification"] != "NEW_FAMILY":
        raise WP011Error("the primary adaptive configuration is not a new root family")
    if decisions[1]["classification"] != "DESCENDANT_MECHANISM_CHANGE":
        raise WP011Error("the ablation was not classified as a structural descendant")
    return decisions


def novelty_decision(root: Path = ROOT) -> dict[str, Any]:
    decisions = novelty_decisions(root)
    return {
        "schema_version": 1,
        "work_package": "WP-011",
        "version": "SEARCH_MEMORY_V2",
        "gate": "GOVERNED_MODEL_NOVELTY_ADMISSION_BEFORE_ANY_VALIDATION_RESULT",
        "proposed_root_family": ROOT_FAMILY,
        "proposed_hypothesis_id": HYPOTHESIS_ID,
        "entry_event": "PREDICTED_DEFAULT_NET_R_STRICTLY_ABOVE_ZERO",
        "mechanism_distinction": (
            "Time-varying recency-weighted coefficients refitted monthly over internal market "
            "features plus point-in-time macro context. WP-008 falsified fixed global linear "
            "weights over eight internal features only; neither time-varying weights, macro "
            "information, nor recency weighting were tested there."
        ),
        "reference_signatures": len(
            signatures(root, exclude_experiment_ids=set(EXPERIMENTS.values()))
        ),
        "family_classification": decisions[0]["classification"],
        "admitted": True,
        "classifier_modified": False,
        "renamed_to_force_novelty": False,
        "conditions_added_to_force_novelty": False,
        "market_results_observed_at_admission": 0,
        "model_fingerprint_fields": [
            "algorithm",
            "label",
            "features",
            "train_window_rule",
            "scaling",
            "regularization",
            "hyperparameters",
            "signal_rule",
            "execution_geometry",
            "dataset",
            "cost_model_reference",
            "execution_model_reference",
        ],
        "variants": decisions,
    }


def validate_admission(root: Path = ROOT) -> dict[str, Any]:
    """The committed gate record must reproduce exactly from the frozen specs."""
    recorded = read_json(root / ADMISSION_PATH)
    current = json.loads(json.dumps(novelty_decision(root)))
    for observed, frozen in zip(current["variants"], recorded["variants"], strict=True):
        for field in ("implementation_dependencies", "config_dependencies"):
            if [item["path"] for item in observed["spec"][field]] != [
                item["path"] for item in frozen["spec"][field]
            ]:
                raise WP011Error("admitted dependency path set changed")
            observed["spec"][field] = frozen["spec"][field]
        observed["executable_spec_hash"] = frozen["executable_spec_hash"]
        observed["dependency_hash"] = frozen["dependency_hash"]
    if recorded != current:
        raise WP011Error("novelty admission record differs from the deterministic gate")
    if recorded["family_classification"] != "NEW_FAMILY":
        raise WP011Error("admitted family is not an explicit new root")
    if recorded["market_results_observed_at_admission"] != 0:
        raise WP011Error("admission observed market results")
    return recorded


def validate_allocation(root: Path = ROOT) -> dict[str, Any]:
    allocation = read_json(root / ALLOCATION_PATH)
    if (
        allocation["allocation_id"] != ALLOCATION_ID
        or allocation["root_family"] != ROOT_FAMILY
        or allocation["hypothesis_id"] != HYPOTHESIS_ID
        or allocation["new_economic_hypotheses"] != 1
        or allocation["model_configurations"] != 2
        or allocation["profile_evaluations"] != 8
        or allocation["numeric_parameter_variants"] != 0
        or allocation["hyperparameter_searches"] != 0
        or allocation["threshold_searches"] != 0
        or allocation["half_life_variants"] != 0
        or allocation["sealed_queries"] != 0
        or allocation["supervised_model_fits"] != 144
        or allocation["experiment_ids"] != [EXPERIMENTS[v] for v in VARIANTS]
        or allocation["primary_variant"] != PRIMARY_VARIANT
    ):
        raise WP011Error("WP-011 allocation drifted from its declared budget")
    family = read_json(root / FAMILY_PATH)
    if family["family_id"] != ROOT_FAMILY or family["allocation_id"] != ALLOCATION_ID:
        raise WP011Error("family record does not match the allocation")
    return allocation


def validate_preregistrations(root: Path = ROOT) -> dict[str, str]:
    """Every configuration must carry a schema-valid preregistration before results."""
    hashes = {}
    for variant in VARIANTS:
        relative = f"research/experiments/{EXPERIMENTS[variant]}/preregistration.json"
        document = validate_preregistration(root / relative)
        if document["experiment_id"] != EXPERIMENTS[variant]:
            raise WP011Error("preregistration identity mismatch")
        if document["status"] != "PREREGISTERED":
            raise WP011Error("preregistration is not in the preregistered state")
        if document["parameter_space"]["allocation_id"] != ALLOCATION_ID:
            raise WP011Error("preregistration is not bound to the WP-011 allocation")
        if document["parameter_space"]["half_life_days"] != 180:
            raise WP011Error("preregistered half-life changed")
        hashes[variant] = sha256(root / relative)
    return hashes


def preflight(root: Path = ROOT) -> dict[str, Any]:
    """Everything that must hold before a single validation-year result is produced."""
    protocol = load_protocol(root)
    admission = validate_admission(root)
    allocation = validate_allocation(root)
    preregistrations = validate_preregistrations(root)
    macro_manifest = read_json(root / MACRO_MANIFEST)
    return {
        "schema_version": 1,
        "work_package": "WP-011",
        "status": "PASS",
        "protocol_id": protocol["protocol_id"],
        "root_family": ROOT_FAMILY,
        "hypothesis_id": HYPOTHESIS_ID,
        "family_classification": admission["family_classification"],
        "configurations": list(VARIANTS),
        "primary_variant": PRIMARY_VARIANT,
        "feature_counts": {v: len(protocol["features"][v]) for v in VARIANTS},
        "half_life_days": protocol["training"]["half_life_days"],
        "update_cadence": protocol["model"]["update_cadence"],
        "purge_boundary_hours": protocol["training"]["purge_boundary_hours"],
        "macro_source_version": macro_manifest["version"],
        "macro_vintage_end": macro_manifest["coverage"]["vintage_end"],
        "allocation_id": allocation["allocation_id"],
        "preregistration_sha256": preregistrations,
        "market_results_observed": 0,
        "sealed_queries": 0,
    }


__all__ = [
    "ABLATION_VARIANT",
    "ADMISSION_PATH",
    "ALLOCATION_ID",
    "ALLOCATION_PATH",
    "EXPERIMENTS",
    "FAMILY_PATH",
    "HYPOTHESIS_ID",
    "PRIMARY_VARIANT",
    "PROTOCOL_PATH",
    "ROOT_FAMILY",
    "VARIANTS",
    "WP011Error",
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
