"""WP-017 CFTC leveraged-positioning admission, protocol, and preregistration gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cftc import FEATURE as CFTC_FEATURE
from .cftc import MANIFEST_PATH as CFTC_MANIFEST_PATH
from .continuation_lab import DATASET_HASH, DATASET_ID
from .model_search_memory import (
    ExecutableModelSpec,
    admit_model_spec,
    bind_model_spec,
    model_fingerprint,
)
from .records import validate_preregistration
from .registry import alias_map, signatures
from .runner import sha256
from .runtime_v2 import RUNTIME_VERSION
from .search_memory import SearchMemoryError
from .search_memory_v2 import DependencyIdentity
from .supervised import FEATURE_VERSION, FULL_FEATURES, LABEL_VERSION
from .wp004 import ROOT
from .wp014_model import HGBR_PARAMETERS, SKLEARN_VERSION
from .wp015 import TRANSFORMATIONS as WP015_TRANSFORMATIONS
from .wp017_lab import (
    CONTROL_FEATURES,
    CONTROL_VARIANT,
    PRIMARY_FEATURES,
    PRIMARY_VARIANT,
    PROFILES,
)

ROOT_FAMILY = "FAM-CFTC-REGULATED-FUTURES-POSITIONING"
HYPOTHESIS_ID = "CFTC_LEVERAGED_FUNDS_NET_POSITIONING_ADDS_INFORMATION_V1"
EXPERIMENTS = {
    PRIMARY_VARIANT: "EXP-ML-028-INTERNAL-PLUS-CFTC-LEVERAGED-NET-HGBR",
    CONTROL_VARIANT: "EXP-ML-029-INTERNAL-HGBR-MATCHED-CFTC",
}
VARIANTS = (PRIMARY_VARIANT, CONTROL_VARIANT)
ROLES = {PRIMARY_VARIANT: "ECONOMIC_CORE", CONTROL_VARIANT: "MATCHED_KNOWN_CONTROL"}
ALLOCATION_ID = "WP017-CFTC-REGULATED-FUTURES-POSITIONING-ALLOCATION"
ALLOCATION_PATH = f"research/memory/registry/allocations/{ALLOCATION_ID}.json"
FAMILY_PATH = f"research/memory/registry/families/{ROOT_FAMILY}.json"
ADMISSION_PATH = "research/memory/registry/admissions/WP017-NOVELTY-ADMISSION.json"
LEDGER_PATH = "research/memory/registry/ledger/WP-017.jsonl"
PROTOCOL_PATH = "research/protocols/WP-017-CFTC-LEVERAGED-POSITIONING-V1.json"
WALK_FORWARD_PATH = "research/protocols/WP-015-WALK-FORWARD-V1.json"
INTEGRITY_PATH = "reports/validation/WP-017-CFTC-INTEGRITY.json"
CONTRACT_PATH = "docs/contracts/CFTC_LEVERAGED_POSITIONING_CONTEXT_V1.md"
STEMS = {
    PRIMARY_VARIANT: "internal_plus_cftc_leveraged_net_hgbr",
    CONTROL_VARIANT: "internal_hgbr_matched_cftc",
}
MAXIMUM_MODEL_FITS = 10
PREDICTION_TOLERANCE = 1e-10
CFTC_TRANSFORMATION = (
    "(Lev_Money_Positions_Long_All - Lev_Money_Positions_Short_All) / Open_Interest_All"
)
TRANSFORMATIONS = {
    **{name: WP015_TRANSFORMATIONS[name] for name in FULL_FEATURES},
    CFTC_FEATURE: CFTC_TRANSFORMATION,
}
SUCCESS_CRITERIA = (
    "PRIMARY_DEFAULT_MEAN_NET_R_ABOVE_ZERO",
    "PRIMARY_DEFAULT_MEAN_NET_R_ABOVE_CONTROL_DEFAULT_MEAN_NET_R",
    "AT_LEAST_3_OF_5_PRIMARY_ANNUAL_DEFAULT_FOLDS_WITH_MEAN_NET_R_AT_OR_ABOVE_ZERO",
    "PRIMARY_DOUBLE_MEAN_NET_R_AT_OR_ABOVE_ZERO",
)
IMPLEMENTATION_PATHS = (
    "backend/app/data/policy.py",
    "backend/app/backtest/models.py",
    "backend/app/backtest/engine.py",
    "backend/app/research/evaluation_protocol.py",
    "backend/app/research/continuation_lab.py",
    "backend/app/research/order_flow.py",
    "backend/app/research/supervised.py",
    "backend/app/research/cftc.py",
    "backend/app/research/runtime_v2.py",
    "backend/app/research/wp014_model.py",
    "backend/app/research/wp014_lab.py",
    "backend/app/research/wp015_model.py",
    "backend/app/research/wp017_lab.py",
    "backend/app/research/wp017_runner.py",
    "backend/app/research/artifacts.py",
    "backend/app/research/model_search_memory.py",
    "backend/app/research/search_memory_v2.py",
    "scripts/reconcile_wp017.py",
    CONTRACT_PATH,
    CFTC_MANIFEST_PATH,
    PROTOCOL_PATH,
    WALK_FORWARD_PATH,
    "pyproject.toml",
    "uv.lock",
)


class WP017Error(SearchMemoryError):
    """WP-017 fixed declaration or chronology was violated."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(variant: str) -> str:
    if variant not in STEMS:
        raise WP017Error("undeclared WP-017 configuration")
    return f"research/configs/wp017/{STEMS[variant]}.json"


def dependency_manifest(root: Path = ROOT) -> list[dict[str, str]]:
    return [{"path": path, "sha256": sha256(root / path)} for path in IMPLEMENTATION_PATHS]


def features_for(variant: str) -> tuple[str, ...]:
    if variant == PRIMARY_VARIANT:
        return PRIMARY_FEATURES
    if variant == CONTROL_VARIANT:
        return CONTROL_FEATURES
    raise WP017Error("undeclared WP-017 configuration")


def executable_spec(variant: str, root: Path = ROOT) -> ExecutableModelSpec:
    names = features_for(variant)
    cftc = read_json(root / CFTC_MANIFEST_PATH)
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
            "cftc_context_required_at_historical_signal": True,
            "update_cadence": "ONCE_PER_FOLD_NO_VALIDATION_REFIT",
        },
        scaling={"scope": "NONE_RAW_GOVERNED_VALUES", "mean": False, "std": False},
        regularization={"kind": "FIXED_L2_LEAF_REGULARIZATION", "value": 1.0, "searched": False},
        hyperparameters={
            "parameters": dict(HGBR_PARAMETERS),
            "searched": 0,
            "feature_selection": "NONE",
            "cftc_trader_group_variants": 0,
            "cftc_normalizer_variants": 0,
            "cftc_transformations": 0,
            "cftc_windows": 0,
        },
        signal_rule={"field": "predicted_default_net_R", "operator": ">", "threshold": 0.0},
        execution_geometry={
            "direction": "LONG",
            "reference": "JUST_COMPLETED_1H_CLOSE",
            "entry": "NEXT_CANONICAL_1M_OPEN",
            "stop_fraction": 0.02,
            "target_fraction": 0.04,
            "max_hold_minutes": 1440,
            "ambiguous_intrabar_hit": "STOP_FIRST",
            "position_policy": "SINGLE_LONG_NO_OVERLAP",
            "profiles": list(PROFILES),
            "stress_retrain": False,
        },
        dataset={
            "manifest_id": DATASET_ID,
            "content_hash": DATASET_HASH,
            "feature_version": FEATURE_VERSION,
            "order_flow_version": "ORDER_FLOW_FEATURES_V1",
            "cftc_manifest_id": cftc["manifest_id"],
            "cftc_logical_sha256": cftc["canonical"]["logical_sha256"],
            "cftc_availability": "UTC_MIDNIGHT_CALENDAR_DAY_AFTER_ACTUAL_CFTC_PUBLICATION_DATE",
            "matched_cftc_eligible_universe": "REQUIRED_FOR_PRIMARY_AND_CONTROL",
            "runtime_version": RUNTIME_VERSION,
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
        raise WP017Error("regulated-futures positioning mechanism was not admitted")
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
        "classification": "KNOWN_INTERNAL_HGBR_MATCHED_CONTROL",
        "duplicate_gate_unchanged": True,
        "known_mechanism_experiment_ids": ["EXP-ML-022-SHALLOW-INTERNAL-HGBR"],
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
        "work_package": "WP-017",
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
        "mechanism_distinction": (
            "One point-in-time-safe regulated-futures positioning share, taken from official "
            "CFTC Traders in Financial Futures reports at their actual publication "
            "availability, adds reported-positioning information to the frozen internal "
            "F1-F8 inputs."
        ),
        "matched_control_policy": (
            "The frozen WP-014 internal HGBR is disclosed as a known mechanism on the exact "
            "CFTC-available universe; no novelty is claimed for the control."
        ),
        "variants": [primary, control],
    }


def load_protocol(root: Path = ROOT) -> dict[str, Any]:
    document = read_json(root / PROTOCOL_PATH)
    budget = document["budget"]
    zero_keys = (
        "cftc_trader_group_variants",
        "normalizer_variants",
        "change_or_momentum_variants",
        "rolling_transform_variants",
        "interaction_variants",
        "regime_split_variants",
        "threshold_variants",
        "algorithm_variants",
        "hyperparameter_variants",
        "feature_subsets",
        "funding_combinations",
        "news_combinations",
        "result_dependent_forks",
    )
    if (
        document["folds"] != list(range(2020, 2025))
        or document["internal_features"] != list(FULL_FEATURES)
        or document["cftc_feature"] != CFTC_FEATURE
        or document["primary_feature_order"] != list(PRIMARY_FEATURES)
        or document["control_feature_order"] != list(CONTROL_FEATURES)
        or document["funding_feature_included"] is not False
        or document["hgbr_parameters"] != HGBR_PARAMETERS
        or document["profiles"] != list(PROFILES)
        or document["runtime_version"] != RUNTIME_VERSION
        or document["cftc"]["formula"] != CFTC_TRANSFORMATION
        or document["cftc"]["cftc_contract_market_code"] != "133741"
        or document["success_criteria"]["pass_requires_all"] != list(SUCCESS_CRITERIA)
        or budget["model_fits"] != MAXIMUM_MODEL_FITS
        or any(budget[key] != 0 for key in zero_keys)
    ):
        raise WP017Error("WP-017 protocol drifted")
    return document


def load_walk_forward(root: Path = ROOT) -> dict[str, Any]:
    document = read_json(root / WALK_FORWARD_PATH)
    if [fold["fold_id"] for fold in document["folds"]] != [
        f"DEV-{year}" for year in range(2020, 2025)
    ]:
        raise WP017Error("WP-017 validation folds drifted")
    return document


def validate_admission(root: Path = ROOT) -> dict[str, Any]:
    recorded = read_json(root / ADMISSION_PATH)
    if recorded != json.loads(json.dumps(novelty_decision(root))):
        raise WP017Error("WP-017 admission differs from deterministic output")
    return recorded


def validate_allocation(root: Path = ROOT) -> dict[str, Any]:
    allocation = read_json(root / ALLOCATION_PATH)
    required = {
        "new_economic_hypotheses": 1,
        "model_configurations": 2,
        "profile_evaluations": 8,
        "supervised_model_fits": MAXIMUM_MODEL_FITS,
        "cftc_trader_group_variants": 0,
        "normalizer_variants": 0,
        "change_or_momentum_variants": 0,
        "rolling_transform_variants": 0,
        "interaction_variants": 0,
        "regime_split_variants": 0,
        "feature_subsets": 0,
        "algorithm_variants": 0,
        "hyperparameter_variants": 0,
        "threshold_variants": 0,
        "funding_combinations": 0,
        "news_combinations": 0,
        "result_dependent_fork_increment": 0,
        "sealed_queries": 0,
    }
    if any(allocation.get(key) != value for key, value in required.items()):
        raise WP017Error("WP-017 allocation drifted")
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
            or space["runtime_version"] != RUNTIME_VERSION
            or space["matched_cftc_eligible_universe"] is not True
            or space["success_criteria"] != list(SUCCESS_CRITERIA)
        ):
            raise WP017Error("WP-017 preregistration drifted")
        hashes[variant] = sha256(root / relative)
    return hashes


def preflight(root: Path = ROOT) -> dict[str, Any]:
    protocol = load_protocol(root)
    admission = validate_admission(root)
    validate_allocation(root)
    preregistrations = validate_preregistrations(root)
    integrity = read_json(root / INTEGRITY_PATH)
    manifest = read_json(root / CFTC_MANIFEST_PATH)
    if (
        integrity["status"] != "PASS"
        or integrity["market_outcomes_read"] is not False
        or integrity["unresolved_publication_rows"] != 0
        or integrity["postcutoff_rows_in_canonical"] != 0
        or integrity["duplicate_market_report_rows"] != 0
        or integrity["contract_market_code"] != "133741"
    ):
        raise WP017Error("CFTC integrity/point-in-time audit failed")
    if any(
        (root / f"research/experiments/{item}/result.json").exists()
        for item in EXPERIMENTS.values()
    ):
        raise WP017Error("WP-017 results already exist")
    counts = manifest["row_counts"]
    coverage = manifest["coverage"]
    return {
        "schema_version": 1,
        "work_package": "WP-017-PREPARATION",
        "status": "PASS",
        "protocol_id": protocol["protocol_id"],
        "runtime_version": RUNTIME_VERSION,
        "family_classification": admission["family_classification"],
        "control_classification": admission["variants"][1]["classification"],
        "features": list(PRIMARY_FEATURES),
        "control_features": list(CONTROL_FEATURES),
        "only_new_feature": CFTC_FEATURE,
        "new_feature_count": 1,
        "forbidden_sources": [
            "THIRD_PARTY_COT_MIRRORS",
            "CURRENT_API_RECONSTRUCTION_OF_HISTORICAL_VALUES",
            "BINANCE_FUNDING",
            "NEWS",
            "OTHER_CFTC_TRADER_GROUPS",
        ],
        "hgbr_parameters": dict(HGBR_PARAMETERS),
        "input_scaling": "NONE_RAW_GOVERNED_VALUES",
        "validation_years": list(range(2020, 2025)),
        "purge_boundary_hours": 216,
        "complete_outcomes_before_boundary": True,
        "cftc_available_at_or_before_signal": True,
        "report_date_used_as_availability": False,
        "interpolation": False,
        "report_age_feature": False,
        "freshness_cutoff": False,
        "matched_eligible_universe": True,
        "cftc_manifest_id": manifest["manifest_id"],
        "cftc_canonical_sha256": manifest["canonical"]["logical_sha256"],
        "cftc_raw_rows": counts["raw_cftc_rows"],
        "cftc_canonical_eligible_rows": counts["canonical_point_in_time_eligible_rows"],
        "cftc_excluded_availability_after_cutoff": counts["excluded_availability_after_cutoff"],
        "cftc_excluded_publication_date_unresolved": counts["excluded_publication_date_unresolved"],
        "cftc_first_availability_timestamp": coverage["first_availability_timestamp"],
        "cftc_last_availability_timestamp": coverage["last_availability_timestamp"],
        "signal_threshold": 0.0,
        "profiles": list(PROFILES),
        "success_criteria": list(SUCCESS_CRITERIA),
        "model_fits_reserved": MAXIMUM_MODEL_FITS,
        "model_fits_executed": 0,
        "prediction_tolerance": PREDICTION_TOLERANCE,
        "preregistration_sha256": preregistrations,
        "market_results_observed": 0,
        "post_cutoff_access": 0,
        "sealed_queries": 0,
    }


__all__ = [name for name in globals() if name.isupper()] + [
    "WP017Error",
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
