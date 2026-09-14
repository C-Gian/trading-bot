"""Create WP-017 SEARCH_MEMORY admission and preregistration before results."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.cftc import FEATURE as CFTC_FEATURE
from app.research.cftc import MANIFEST_PATH as CFTC_MANIFEST_PATH
from app.research.continuation_lab import DATASET_HASH
from app.research.model_search_memory import bind_model_spec, model_fingerprint
from app.research.registry import cumulative_accounting
from app.research.runtime_v2 import RUNTIME_VERSION
from app.research.wp014_model import HGBR_PARAMETERS, MODEL_VERSION, SKLEARN_VERSION
from app.research.wp017 import (
    ADMISSION_PATH,
    ALLOCATION_ID,
    ALLOCATION_PATH,
    CFTC_TRANSFORMATION,
    CONTROL_VARIANT,
    EXPERIMENTS,
    FAMILY_PATH,
    HYPOTHESIS_ID,
    LEDGER_PATH,
    MAXIMUM_MODEL_FITS,
    PREDICTION_TOLERANCE,
    PRIMARY_VARIANT,
    ROOT_FAMILY,
    SUCCESS_CRITERIA,
    VARIANTS,
    config_path,
    dependency_manifest,
    executable_spec,
    features_for,
    novelty_decision,
    preflight,
    sha256,
)
from app.research.wp017_lab import PROFILES

CREATED_AT = "2026-09-14T12:00:00Z"
PREFLIGHT_PATH = "reports/validation/WP-017-PREFLIGHT.json"
PRIMARY_HYPOTHESIS = (
    "The latest point-in-time-safe CFTC CME Bitcoin Traders in Financial Futures Leveraged "
    "Funds net position, normalized by total open interest, may provide incremental "
    "predictive information about subsequent BTCUSDT LONG outcomes beyond the existing "
    "frozen internal F1-F8 feature set."
)
CONTROL_HYPOTHESIS = (
    "The frozen internal F1-F8 HGBR is repeated on the identical CFTC-available universe as "
    "a matched known-mechanism control."
)
LEAKAGE_CONTROLS = [
    "EXACT_FROZEN_F1_F8_SEMANTICS",
    "REPORT_DATE_IS_NEVER_TREATED_AS_AVAILABILITY",
    "AVAILABILITY_IS_UTC_MIDNIGHT_AFTER_ACTUAL_CFTC_PUBLICATION_DATE",
    "UNRESOLVED_PUBLICATION_DATE_MAKES_THE_ROW_INELIGIBLE",
    "ASOF_USES_LATEST_RECORD_WITH_AVAILABILITY_AT_OR_BEFORE_SIGNAL",
    "NO_INTERPOLATION_NO_REPORT_AGE_FEATURE_NO_FRESHNESS_CUTOFF",
    "NUMERATOR_AND_DENOMINATOR_COME_FROM_THE_SAME_OFFICIAL_REPORT",
    "PRIMARY_AND_CONTROL_REQUIRE_IDENTICAL_CFTC_AVAILABLE_TIMESTAMPS",
    "TRAINING_SIGNAL_AND_COMPLETE_OUTCOME_STRICTLY_BEFORE_PURGE_BOUNDARY",
    "NO_VALIDATION_REFIT_SELECTION_SCALING_OR_EARLY_STOPPING",
    "NO_POST_CUTOFF_OR_SEALED_ACCESS",
]
EVALUATION_DESIGN = (
    "Five complete annual expanding folds 2020-2024 under RESEARCH_RUNTIME_V2_BATCH; CFTC "
    "availability derived from actual publication dates; identical primary/control universe; "
    "complete outcomes before validation_start-216h; four fixed profiles with DEFAULT, ZERO "
    "and DOUBLE reusing one prediction set and DELAY_1H using governed deterministic delay "
    "alignment."
)
STOPPING_RULE = (
    "Owner executes four profiles once through the allowlisted runner; no alternative CFTC "
    "trader group, normalizer, change/momentum transform, rolling window, interaction, regime "
    "split, feature subset, algorithm, hyperparameter, signal threshold, funding or news "
    "combination, and no result-dependent fork."
)


def write(relative: str, payload: Any) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    if any(
        (ROOT / f"research/experiments/{experiment}/result.json").exists()
        for experiment in EXPERIMENTS.values()
    ):
        raise RuntimeError("refusing to regenerate WP-017 admission after results")
    prior = cumulative_accounting(ROOT)
    cftc = json.loads((ROOT / CFTC_MANIFEST_PATH).read_text(encoding="utf-8"))
    combined_hash = hashlib.sha256(
        f"{DATASET_HASH}:{cftc['canonical']['logical_sha256']}".encode()
    ).hexdigest()
    admission = novelty_decision(ROOT)
    write(ADMISSION_PATH, admission)
    write(
        FAMILY_PATH,
        {
            "schema_version": 1,
            "work_package": "WP-017",
            "family_id": ROOT_FAMILY,
            "parent_family_id": None,
            "allocation_id": ALLOCATION_ID,
            "admitted_by": ADMISSION_PATH,
            "status": "ADMITTED_PREREGISTERED_PENDING_OWNER_EXECUTION",
            "aliases": [HYPOTHESIS_ID, CFTC_FEATURE, PRIMARY_VARIANT],
            "entry_event_anchors": ["PREDICTED_DEFAULT_NET_R_STRICTLY_ABOVE_ZERO"],
            "information_source": "OFFICIAL_CFTC_TRADERS_IN_FINANCIAL_FUTURES_CME_BITCOIN_133741",
            "mechanism": (
                "One reported regulated-futures Leveraged Funds net position share, available "
                "only after its actual CFTC publication date, is added to the frozen internal "
                "F1-F8 inputs."
            ),
            "matched_control": {
                "variant": CONTROL_VARIANT,
                "classification": "KNOWN_INTERNAL_HGBR_MATCHED_CONTROL",
                "related_to": "EXP-ML-022-SHALLOW-INTERNAL-HGBR",
                "novelty_claimed": False,
            },
            "failure_experiment_ids": [],
            "legitimate_revisit": (
                "Only a new explicit Research Director allocation; no exposed-result tuning."
            ),
        },
    )
    allocation = {
        "schema_version": 1,
        "work_package": "WP-017",
        "allocation_id": ALLOCATION_ID,
        "authority": "Owner WP-017 CFTC leveraged-positioning preparation instruction",
        "review_authority": "reports/source_gates/WP017-SOURCE-DISCOVERY-GATE.md",
        "kind": "DELIBERATE_NEW_INFORMATION_FAMILY_ALLOCATION",
        "root_family": ROOT_FAMILY,
        "hypothesis_id": HYPOTHESIS_ID,
        "architecture": MODEL_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "experiment_ids": [EXPERIMENTS[variant] for variant in VARIANTS],
        "primary_variant": PRIMARY_VARIANT,
        "matched_control_variant": CONTROL_VARIANT,
        "new_economic_hypotheses": 1,
        "model_configurations": 2,
        "profiles": list(PROFILES),
        "profiles_per_configuration": 4,
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
        "architecture_variants": 0,
        "funding_combinations": 0,
        "news_combinations": 0,
        "model_selection_forks": 0,
        "sealed_queries": 0,
        "paper_observations": 0,
        "adaptive_decision_increment": 1,
        "result_dependent_fork_increment": 0,
        "prior_adaptive_decisions": prior["adaptive_decisions"],
        "prior_result_dependent_forks": prior["result_dependent_forks"],
        "cumulative_adaptive_decisions": prior["adaptive_decisions"] + 1,
        "cumulative_result_dependent_forks": prior["result_dependent_forks"],
        "family_limits": {
            "experiments": 2,
            "strategy_variants": 2,
            "trials": 8,
            "numeric_parameter_variants": 0,
        },
        "conditionality": (
            "Official CFTC TFF integrity, availability derived from actual publication dates, "
            "exactly one new feature, exact frozen F1-F8 inputs and HGBR model, matched CFTC "
            "availability, 216h purge, complete outcomes, and RESEARCH_RUNTIME_V2_BATCH."
        ),
    }
    write(ALLOCATION_PATH, allocation)
    dependencies = dependency_manifest(ROOT)
    for decision in admission["variants"]:
        variant = decision["variant"]
        experiment = EXPERIMENTS[variant]
        spec = executable_spec(variant, ROOT)
        binding = bind_model_spec(spec)
        features = list(features_for(variant))
        parameter_space = {
            "allocation_id": ALLOCATION_ID,
            "root_family": ROOT_FAMILY,
            "hypothesis_id": HYPOTHESIS_ID,
            "variant": variant,
            "features": features,
            "feature_count": len(features),
            "only_new_feature": CFTC_FEATURE if variant == PRIMARY_VARIANT else None,
            "new_feature_count": 1 if variant == PRIMARY_VARIANT else 0,
            "cftc_manifest_id": cftc["manifest_id"],
            "cftc_logical_sha256": cftc["canonical"]["logical_sha256"],
            "cftc_market": cftc["market"]["name"],
            "cftc_contract_market_code": cftc["market"]["cftc_contract_market_code"],
            "cftc_raw_rows": cftc["row_counts"]["raw_cftc_rows"],
            "cftc_canonical_eligible_rows": cftc["row_counts"][
                "canonical_point_in_time_eligible_rows"
            ],
            "cftc_availability": "UTC_MIDNIGHT_CALENDAR_DAY_AFTER_ACTUAL_CFTC_PUBLICATION_DATE",
            "cftc_transform": CFTC_TRANSFORMATION,
            "cftc_asof_rule": "LATEST_RECORD_WITH_AVAILABILITY_TIMESTAMP_AT_OR_BEFORE_SIGNAL_TIME",
            "matched_cftc_eligible_universe": True,
            "funding_feature_included": False,
            "input_scaling": "NONE_RAW_GOVERNED_VALUES",
            "hgbr_parameters": dict(HGBR_PARAMETERS),
            "sklearn_version": SKLEARN_VERSION,
            "runtime_version": RUNTIME_VERSION,
            "validation_years": list(range(2020, 2025)),
            "purge_hours": 216,
            "model_fits": 5,
            "success_criteria": list(SUCCESS_CRITERIA),
            "cftc_trader_group_variants": 0,
            "normalizer_variants": 0,
            "change_or_momentum_variants": 0,
            "rolling_transform_variants": 0,
            "interaction_variants": 0,
            "regime_split_variants": 0,
            "feature_subsets": 0,
            "algorithm_variants": 0,
            "hyperparameter_variants": 0,
            "feature_variants": 0,
            "threshold_variants": 0,
            "architecture_variants": 0,
            "funding_combinations": 0,
            "news_combinations": 0,
            "model_selection_forks": 0,
            "signal_threshold": 0.0,
            "update_cadence": "ONCE_PER_FOLD_NO_VALIDATION_REFIT",
            "prediction_tolerance": PREDICTION_TOLERANCE,
            "sealed_data_access": "PROHIBITED",
            "known_control_mechanism": "EXP-ML-022-SHALLOW-INTERNAL-HGBR"
            if variant == CONTROL_VARIANT
            else None,
            "declared_trial_budget": {
                "configurations": 1,
                "profiles": 4,
                "model_fits": 5,
                "seeds": 0,
                "total_trials": 4,
            },
            "behavior_hash": binding.behavior_hash,
            "structural_hash": binding.structural_hash,
            "executable_spec_hash": binding.executable_spec_hash,
            "dependency_hash": binding.dependency_hash,
            "model_fingerprint": model_fingerprint(spec),
            "executable_model_spec": spec.to_dict(),
            "dependencies": dependencies,
        }
        write(
            f"research/experiments/{experiment}/preregistration.json",
            {
                "schema_version": 2,
                "experiment_id": experiment,
                "experiment_version": 1,
                "created_at_utc": CREATED_AT,
                "status": "PREREGISTERED",
                "hypothesis": PRIMARY_HYPOTHESIS
                if variant == PRIMARY_VARIANT
                else CONTROL_HYPOTHESIS,
                "rationale": (
                    "One frozen regulated-futures positioning share versus a matched known "
                    "internal HGBR control; predictive, not causal, with no model search."
                ),
                "research_scope": (
                    "BTCUSDT_SPOT_LONG_ONLY_CFTC_INFORMATIONAL_NO_SEALED_NO_LIVE_TRADING"
                ),
                "dataset": {
                    "manifest_id": "BTCUSDT-SPOT-1M-DEV-v1 + CFTC-CME-BITCOIN-TFF-DEV-v1",
                    "content_hash": combined_hash,
                    "maximum_timestamp": "2024-12-31T23:59:00Z",
                },
                "metrics": {
                    "primary": "POOLED_VALID_RESOLVED_DEFAULT_NET_R",
                    "secondary": [
                        "profiles",
                        "annual_folds",
                        "trade_ess_and_concentration",
                        "prediction_positive_hours",
                        "oos_prediction_label_pearson",
                        "primary_minus_control_default_net_r",
                        "stage_timings",
                        "independent_reconciliation",
                    ],
                },
                "evaluation_design": EVALUATION_DESIGN,
                "leakage_controls": LEAKAGE_CONTROLS,
                "parameter_space": parameter_space,
                "code_config_reference": sha256(ROOT / config_path(variant)),
                "cost_execution_reference": (
                    "BACKTEST_ENGINE_V2 / EXECUTION_MODEL_V2 / BTCUSDT_SPOT_COST_V1"
                ),
                "seeds": [0],
                "trial_budget": 4,
                "stopping_rule": STOPPING_RULE,
            },
        )
    ledger = []
    for decision in admission["variants"]:
        variant = decision["variant"]
        experiment = EXPERIMENTS[variant]
        prereg_path = f"research/experiments/{experiment}/preregistration.json"
        ledger.append(
            {
                "schema_version": 2,
                "work_package": "WP-017",
                "record_kind": "PREREGISTERED_ADMISSION"
                if variant == PRIMARY_VARIANT
                else "PREREGISTERED_MATCHED_DUPLICATE_CONTROL",
                "experiment_id": experiment,
                "strategy_label": variant,
                "root_family": ROOT_FAMILY,
                "allocation_id": ALLOCATION_ID,
                "hypothesis_id": HYPOTHESIS_ID,
                "hypothesis_role": decision["hypothesis_role"],
                "classification": decision["classification"],
                "novelty": decision["classification"],
                "behavior_hash": decision["behavior_hash"],
                "structural_hash": decision["structural_hash"],
                "executable_spec_hash": decision["executable_spec_hash"],
                "dependency_hash": decision["dependency_hash"],
                "matched_experiment_ids": decision["matched_experiment_ids"],
                "parent_experiment_ids": []
                if variant == PRIMARY_VARIANT
                else [EXPERIMENTS[PRIMARY_VARIANT]],
                "claimed_market_mechanism": (
                    "Point-in-time-safe reported CFTC Leveraged Funds net positioning share may "
                    "add regulated-futures positioning information."
                ),
                "scientific_reason": "New-information family primary."
                if variant == PRIMARY_VARIANT
                else "Known internal HGBR on the matched CFTC-available universe.",
                "preregistration_path": prereg_path,
                "preregistration_sha256": sha256(ROOT / prereg_path),
                "result_path": f"research/experiments/{experiment}/result.json",
                "outcome_reference": experiment,
                "budget_units": {
                    "experiments": 1,
                    "strategy_variants": 1,
                    "trials": 4,
                    "numeric_parameter_variants": 0,
                },
            }
        )
    (ROOT / LEDGER_PATH).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / LEDGER_PATH).write_text(
        "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in ledger),
        encoding="utf-8",
        newline="\n",
    )
    write(PREFLIGHT_PATH, preflight(ROOT))
    print(
        json.dumps(
            {
                "family": admission["family_classification"],
                "experiments": list(EXPERIMENTS.values()),
                "runtime": RUNTIME_VERSION,
                "results_observed": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
