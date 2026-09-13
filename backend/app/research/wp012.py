"""WP-012 governance: frozen protocol, novelty admission and allocation validation.

`FAM-REGIME-CONDITIONED-LINEAR` is submitted to SEARCH_MEMORY_V2 before any market
result. The mechanism under test is conditioning, not a new predictor: the eight frozen
internal features are unchanged, and a single point-in-time NFCI reading selects which of
two independently fitted experts speaks at each hour.

WP-008 falsified one fixed global linear weight vector over those features, and WP-011
falsified adding macro levels to the feature matrix. Neither tested whether the
relationship between internal features and forward net R differs between financial
regimes. That is the only question here.

The threshold is exactly 0.0. It is not fitted, not searched, and no alternative
threshold, macro variable, regime count, smoothing, hysteresis or lag variant exists in
this work package.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .continuation_lab import DATASET_HASH, DATASET_ID, PROFILES
from .linear_model import ALGORITHM, MIN_STD_EXCLUSIVE, SIGNAL_THRESHOLD
from .model_search_memory import ExecutableModelSpec, admit_model_spec, model_fingerprint
from .records import validate_preregistration
from .regime import (
    NORMAL_OR_LOOSE,
    REGIME_SERIES,
    REGIME_THRESHOLD,
    REGIME_VERSION,
    REGIMES,
    TIGHT,
)
from .registry import alias_map, signatures
from .runner import sha256 as runner_sha256
from .search_memory import SearchMemoryError
from .search_memory_v2 import DependencyIdentity
from .supervised import FEATURE_VERSION as INTERNAL_FEATURE_VERSION
from .supervised import FULL_FEATURES, LABEL_VERSION
from .wp004 import ROOT

ROOT_FAMILY = "FAM-REGIME-CONDITIONED-LINEAR"
HYPOTHESIS_ID = "FINANCIAL_REGIME_CONDITIONED_SIGNAL_WEIGHTS_V1"
PRIMARY_VARIANT = "REGIME_TWO_EXPERTS"
CONTROL_VARIANT = "GLOBAL_SINGLE_EXPERT_MATCHED"
VARIANTS = (PRIMARY_VARIANT, CONTROL_VARIANT)
GLOBAL_KEY = "GLOBAL"
ARCHITECTURE = "REGIME_CONDITIONED_LINEAR_EXPERTS_V1"
ROLES = {
    PRIMARY_VARIANT: "ECONOMIC_CORE",
    CONTROL_VARIANT: "MATCHED_UNCONDITIONED_CONTROL",
}
EXPERIMENTS = {
    PRIMARY_VARIANT: "EXP-ML-018-REGIME-TWO-EXPERTS",
    CONTROL_VARIANT: "EXP-ML-019-GLOBAL-MATCHED-CONTROL",
}
STEMS = {
    PRIMARY_VARIANT: "regime_two_experts",
    CONTROL_VARIANT: "global_single_expert_matched",
}
EXPERTS_PER_FOLD = {PRIMARY_VARIANT: len(REGIMES), CONTROL_VARIANT: 1}
FOLD_COUNT = 6
MAXIMUM_EXPERT_FITS = FOLD_COUNT * sum(EXPERTS_PER_FOLD.values())

ALLOCATION_ID = "WP012-REGIME-CONDITIONED-ALLOCATION"
ALLOCATION_PATH = f"research/memory/registry/allocations/{ALLOCATION_ID}.json"
FAMILY_PATH = f"research/memory/registry/families/{ROOT_FAMILY}.json"
ADMISSION_PATH = "research/memory/registry/admissions/WP012-NOVELTY-ADMISSION.json"
PROTOCOL_PATH = "research/protocols/WP-012-REGIME-CONDITIONED-V1.json"
LEDGER_PATH = "research/memory/registry/ledger/WP-012.jsonl"
OUTCOMES_PATH = "research/memory/registry/outcomes/WP-012.jsonl"

MACRO_MANIFEST = "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json"
DATASET_MANIFEST = "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"

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
    "backend/app/research/regime.py",
    "backend/app/research/wp012_lab.py",
    "backend/app/research/artifacts.py",
    "backend/app/research/search_memory_v2.py",
    PROTOCOL_PATH,
)
SPEC_DEPENDENCY_PATHS = IMPLEMENTATION_PATHS

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
}


class WP012Error(SearchMemoryError):
    """WP-012 governance, admission, or frozen-specification validation failed."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(variant: str) -> str:
    if variant not in VARIANTS:
        raise WP012Error("undeclared WP-012 configuration")
    return f"research/configs/wp012/{STEMS[variant]}.json"


def sha256(path: Path) -> str:
    return runner_sha256(path)


def load_protocol(root: Path = ROOT) -> dict[str, Any]:
    document = read_json(root / PROTOCOL_PATH)
    validate_protocol(document)
    return document


def validate_protocol(document: dict[str, Any]) -> None:
    """Fail closed if any frozen declaration drifted."""
    if document["protocol_id"] != "WP-012-REGIME-CONDITIONED-V1":
        raise WP012Error("WP-012 protocol identity changed")
    if document["architecture"] != ARCHITECTURE or document["root_family"] != ROOT_FAMILY:
        raise WP012Error("WP-012 architecture or family identity changed")
    features = document["features"]
    for variant in VARIANTS:
        if tuple(features[variant]) != FULL_FEATURES:
            raise WP012Error("expert features are not exactly the frozen eight internal features")
    regime = document["regime"]
    if (
        regime["version"] != REGIME_VERSION
        or regime["series"] != REGIME_SERIES
        or regime["threshold"] != REGIME_THRESHOLD
        or regime["threshold"] != 0.0
        or regime["threshold_variants"] != 0
        or tuple(regime["regimes"]) != REGIMES
        or regime["boundary_value_regime"] != NORMAL_OR_LOOSE
        or regime["rule"] != f"{TIGHT}_IF_POINT_IN_TIME_NFCI_STRICTLY_ABOVE_ZERO"
        or regime["macro_features_in_expert_matrix"] != 0
        or regime["macro_variable_variants"] != 0
        or regime["regime_count_variants"] != 0
        or regime["transition_smoothing"] != "NONE"
        or regime["hysteresis"] != "NONE"
        or regime["lag_variants"] != 0
        or regime["missing_regime_policy"] != "INELIGIBLE_COUNTED_NEVER_IMPUTED"
        or regime["infeasible_expert_policy"]
        != "EMIT_NO_MODEL_COUNT_AFFECTED_HOURS_NEVER_MERGE_REGIMES"
    ):
        raise WP012Error("frozen regime gate declaration drifted")
    training = document["training"]
    if (
        training["purge_boundary_hours"] != 216
        or training["label"] != LABEL_VERSION
        or training["scaling"] != "TRAINING_ONLY_PER_EXPERT_MEAN_AND_POPULATION_VARIANCE"
        or training["universe"] != "EXPANDING_CHRONOLOGICAL"
        or training["expert_partition"] != "DISJOINT_BY_POINT_IN_TIME_REGIME_OF_THE_SIGNAL_HOUR"
        or training["shared_coefficients_between_experts"]
        or training["eligibility"] != "INTERNAL_FEATURES_AND_POINT_IN_TIME_REGIME_BOTH_AVAILABLE"
    ):
        raise WP012Error("frozen training declaration drifted")
    model = document["model"]
    if (
        model["algorithm"] != ALGORITHM
        or model["minimum_std_exclusive"] != MIN_STD_EXCLUSIVE
        or model["signal_threshold"] != SIGNAL_THRESHOLD
        or model["threshold_searches"] != 0
        or model["hyperparameter_searches"] != 0
        or model["regularization"] != "NONE"
        or model["update_cadence"] != "ONCE_PER_FOLD_NO_VALIDATION_REFIT"
        or model["coefficient_thresholding"]
        or model["feature_dropping"]
        or model["validation_refit"]
        or not model["require_full_column_rank"]
    ):
        raise WP012Error("frozen model declaration drifted")
    execution = document["execution"]
    if (
        execution["stop_fraction"] != 0.02
        or execution["target_fraction"] != 0.04
        or execution["max_hold_minutes"] != 1440
        or document["profiles"] != list(PROFILES)
        or document["configurations"] != 2
        or document["profile_evaluations"] != 8
        or document["numeric_parameter_variants"] != 0
    ):
        raise WP012Error("frozen execution or budget declaration drifted")
    if [fold["fold_id"] for fold in document["folds"]] != [f"DEV-{y}" for y in range(2019, 2025)]:
        raise WP012Error("frozen annual folds changed")
    if document["experts_per_fold"] != EXPERTS_PER_FOLD:
        raise WP012Error("declared experts per fold changed")
    if document["maximum_expert_fits"] != MAXIMUM_EXPERT_FITS:
        raise WP012Error("declared maximum expert fit budget changed")
    if document["internal_feature_version"] != INTERNAL_FEATURE_VERSION:
        raise WP012Error("internal feature version changed")


def dependency_manifest(root: Path = ROOT) -> list[dict[str, str]]:
    return [{"path": path, "sha256": sha256(root / path)} for path in SPEC_DEPENDENCY_PATHS]


def _feature_specs() -> tuple[dict[str, Any], ...]:
    return tuple(
        {"name": name, "transformation": TRANSFORMATIONS[name], "order": index + 1}
        for index, name in enumerate(FULL_FEATURES)
    )


def _conditioning(variant: str) -> dict[str, Any]:
    """The declared difference between the two configurations, and the only one."""
    if variant == PRIMARY_VARIANT:
        return {
            "kind": "POINT_IN_TIME_FINANCIAL_REGIME_CONDITIONED_EXPERTS",
            "regime_version": REGIME_VERSION,
            "regime_series": REGIME_SERIES,
            "regimes": list(REGIMES),
            "experts_per_fold": EXPERTS_PER_FOLD[PRIMARY_VARIANT],
            "expert_selection": "EXACTLY_ONE_EXPERT_PER_HOUR_NO_BLENDING",
            "shared_coefficients": False,
        }
    return {
        "kind": "UNCONDITIONED_SINGLE_EXPERT_MATCHED_TO_THE_SAME_ELIGIBLE_UNIVERSE",
        "regime_version": REGIME_VERSION,
        "regime_series": REGIME_SERIES,
        "regimes": list(REGIMES),
        "experts_per_fold": EXPERTS_PER_FOLD[CONTROL_VARIANT],
        "expert_selection": "SINGLE_EXPERT_FOR_EVERY_ELIGIBLE_HOUR",
        "shared_coefficients": True,
    }


def executable_spec(variant: str, root: Path = ROOT) -> ExecutableModelSpec:
    if variant not in VARIANTS:
        raise WP012Error("undeclared WP-012 configuration")
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
        features=_feature_specs(),
        train_window_rule={
            "kind": "EXPANDING_CHRONOLOGICAL_PER_FOLD_REGIME_PARTITIONED",
            "architecture": ARCHITECTURE,
            "conditioning": _conditioning(variant),
            "folds": [2019, 2020, 2021, 2022, 2023, 2024],
            "purge_hours": 216,
            "training_signal_boundary": "STRICTLY_BEFORE_VALIDATION_START_MINUS_PURGE",
            "label_outcome_before_purge_boundary": True,
            "eligibility": "INTERNAL_FEATURES_AND_POINT_IN_TIME_REGIME_BOTH_AVAILABLE",
            "infeasible_expert_policy": ("EMIT_NO_MODEL_COUNT_AFFECTED_HOURS_NEVER_MERGE_REGIMES"),
            "update_cadence": "ONCE_PER_FOLD_NO_VALIDATION_REFIT",
        },
        scaling={
            "scope": "TRAINING_ONLY_PER_EXPERT",
            "mean": True,
            "std_ddof": 0,
            "weighted": False,
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
            "regime_version": REGIME_VERSION,
            "regime_source_version": protocol["regime_source_version"],
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
            raise WP012Error(str(exc)) from exc
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
        raise WP012Error("the regime-conditioned configuration is not a new root family")
    if decisions[1]["classification"] != "DESCENDANT_MECHANISM_CHANGE":
        raise WP012Error("the matched control was not classified as a structural descendant")
    return decisions


def novelty_decision(root: Path = ROOT) -> dict[str, Any]:
    decisions = novelty_decisions(root)
    return {
        "schema_version": 1,
        "work_package": "WP-012",
        "version": "SEARCH_MEMORY_V2",
        "gate": "GOVERNED_MODEL_NOVELTY_ADMISSION_BEFORE_ANY_VALIDATION_RESULT",
        "proposed_root_family": ROOT_FAMILY,
        "proposed_hypothesis_id": HYPOTHESIS_ID,
        "entry_event": "PREDICTED_DEFAULT_NET_R_STRICTLY_ABOVE_ZERO",
        "mechanism_distinction": (
            "Two independently fitted linear experts over the frozen eight internal features, "
            "selected hour by hour by a point-in-time NFCI regime gate with a fixed zero "
            "threshold. WP-008 falsified a single fixed global weight vector over those same "
            "features and WP-011 falsified adding macro levels as additive predictors; neither "
            "tested whether the internal feature-to-net-R relationship itself differs between "
            "financial regimes. No macro value enters an expert feature matrix here."
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
                raise WP012Error("admitted dependency path set changed")
            observed["spec"][field] = frozen["spec"][field]
        observed["executable_spec_hash"] = frozen["executable_spec_hash"]
        observed["dependency_hash"] = frozen["dependency_hash"]
    if recorded != current:
        raise WP012Error("novelty admission record differs from the deterministic gate")
    if recorded["family_classification"] != "NEW_FAMILY":
        raise WP012Error("admitted family is not an explicit new root")
    if recorded["market_results_observed_at_admission"] != 0:
        raise WP012Error("admission observed market results")
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
        or allocation["regime_threshold_variants"] != 0
        or allocation["regime_count_variants"] != 0
        or allocation["macro_variable_variants"] != 0
        or allocation["sealed_queries"] != 0
        or allocation["maximum_expert_fits"] != MAXIMUM_EXPERT_FITS
        or allocation["supervised_model_fits"] != MAXIMUM_EXPERT_FITS
        or allocation["experiment_ids"] != [EXPERIMENTS[v] for v in VARIANTS]
        or allocation["primary_variant"] != PRIMARY_VARIANT
    ):
        raise WP012Error("WP-012 allocation drifted from its declared budget")
    family = read_json(root / FAMILY_PATH)
    if family["family_id"] != ROOT_FAMILY or family["allocation_id"] != ALLOCATION_ID:
        raise WP012Error("family record does not match the allocation")
    return allocation


def validate_preregistrations(root: Path = ROOT) -> dict[str, str]:
    """Every configuration must carry a schema-valid preregistration before results."""
    hashes = {}
    for variant in VARIANTS:
        relative = f"research/experiments/{EXPERIMENTS[variant]}/preregistration.json"
        document = validate_preregistration(root / relative)
        if document["experiment_id"] != EXPERIMENTS[variant]:
            raise WP012Error("preregistration identity mismatch")
        if document["status"] != "PREREGISTERED":
            raise WP012Error("preregistration is not in the preregistered state")
        space = document["parameter_space"]
        if space["allocation_id"] != ALLOCATION_ID:
            raise WP012Error("preregistration is not bound to the WP-012 allocation")
        if space["regime_threshold"] != 0.0 or space["regime_threshold_variants"] != 0:
            raise WP012Error("preregistered regime threshold is not the frozen fixed zero")
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
        "work_package": "WP-012",
        "status": "PASS",
        "protocol_id": protocol["protocol_id"],
        "architecture": ARCHITECTURE,
        "root_family": ROOT_FAMILY,
        "hypothesis_id": HYPOTHESIS_ID,
        "family_classification": admission["family_classification"],
        "configurations": list(VARIANTS),
        "primary_variant": PRIMARY_VARIANT,
        "feature_counts": {v: len(protocol["features"][v]) for v in VARIANTS},
        "regime_version": protocol["regime"]["version"],
        "regime_series": protocol["regime"]["series"],
        "regime_threshold": protocol["regime"]["threshold"],
        "regime_threshold_variants": 0,
        "macro_features_in_expert_matrix": 0,
        "purge_boundary_hours": protocol["training"]["purge_boundary_hours"],
        "regime_source_version": macro_manifest["version"],
        "regime_vintage_end": macro_manifest["coverage"]["vintage_end"],
        "maximum_expert_fits": MAXIMUM_EXPERT_FITS,
        "allocation_id": allocation["allocation_id"],
        "preregistration_sha256": preregistrations,
        "market_results_observed": 0,
        "sealed_queries": 0,
    }


__all__ = [
    "ADMISSION_PATH",
    "ALLOCATION_ID",
    "ALLOCATION_PATH",
    "ARCHITECTURE",
    "CONTROL_VARIANT",
    "EXPERIMENTS",
    "EXPERTS_PER_FOLD",
    "FAMILY_PATH",
    "GLOBAL_KEY",
    "HYPOTHESIS_ID",
    "MAXIMUM_EXPERT_FITS",
    "PRIMARY_VARIANT",
    "PROTOCOL_PATH",
    "ROOT_FAMILY",
    "VARIANTS",
    "WP012Error",
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
