from dataclasses import replace

import pytest

from app.research.search_memory import SearchMemoryError
from app.research.search_memory_v2 import (
    Comparison,
    ExecutableStrategySpec,
    FeaturePrimitive,
    NumericTerm,
    Rule,
    admit_executable_spec,
    bind_executable_spec,
    classify_bound_spec,
    derived_fingerprint,
    validate_legacy_signatures,
    validate_search_memory_v2,
)


def _spec(**changes):
    base = ExecutableStrategySpec(
        schema_version=2,
        root_family="FAM-BREAKOUT",
        family="FAM-BREAKOUT",
        entry_event="CLOSE_ABOVE_PRIOR_HIGH",
        feature_primitives=(
            FeaturePrimitive("PRICE_HIGH_BREAKOUT", "PRIOR_HIGH_MAXIMUM", 60),
        ),
        comparisons=(Comparison("close", ">", "prior_high"),),
        numeric_parameters=(NumericTerm("breakout_hours", 24, "hours"),),
        regime_gates=(),
        confirmation_gates=(),
        signal_timeframe_minutes=60,
        context_timeframe_minutes=0,
        direction="LONG",
        reference_price_rule="LATEST_COMPLETED_1H_CLOSE",
        stop=Rule("FIXED_PERCENT_OF_SIGNAL_CLOSE", NumericTerm("stop_fraction", 0.02, "fraction")),
        exit=Rule("FIXED_TARGET_OR_STOP_OR_HORIZON", NumericTerm("target_fraction", 0.04, "fraction")),
        holding_horizon_minutes=1440,
        timing_perturbation="NONE",
        position_policy="SINGLE_LONG_NO_OVERLAP",
        execution_model_reference="EXECUTION_MODEL_V2",
        cost_model_reference="BTCUSDT_SPOT_COST_V1",
        dataset={"manifest_id": "DEV", "content_hash": "a" * 64},
        implementation_dependencies=(),
        config_dependencies=(),
    )
    return replace(base, **changes)


def _signature(spec, experiment="LEGACY"):
    bound = bind_executable_spec(spec)
    return {
        "experiment_id": experiment,
        "root_family": spec.root_family,
        "behavior_hash": bound.behavior_hash,
        "structural_hash": bound.structural_hash,
    }


def test_renamed_identical_spec_and_false_family_are_duplicate():
    spec = _spec()
    signatures = [_signature(spec)]
    assert classify_bound_spec(bind_executable_spec(spec), signatures)["classification"] == "DUPLICATE"
    false_family = replace(spec, family="FRESH", root_family="FRESH")
    assert classify_bound_spec(bind_executable_spec(false_family), signatures)["classification"] == "DUPLICATE"
    with pytest.raises(SearchMemoryError, match="DUPLICATE"):
        admit_executable_spec(
            false_family,
            declared_family="FRESH",
            declared_fingerprint=derived_fingerprint(false_family),
            signatures=signatures,
            aliases={},
        )


def test_24_to_25_is_parameter_variant():
    base = _spec()
    changed = replace(
        base, numeric_parameters=(NumericTerm("breakout_hours", 25, "hours"),)
    )
    decision = classify_bound_spec(bind_executable_spec(changed), [_signature(base)])
    assert decision["classification"] == "PARAMETER_VARIANT"


def test_falsified_fingerprint_and_stale_threshold_are_rejected():
    spec = _spec()
    falsified = derived_fingerprint(spec) | {"entry_event": "SOMETHING_ELSE"}
    with pytest.raises(SearchMemoryError, match="declared fingerprint"):
        bind_executable_spec(spec, declared_fingerprint=falsified)
    changed = replace(
        spec, numeric_parameters=(NumericTerm("breakout_hours", 25, "hours"),)
    )
    with pytest.raises(SearchMemoryError, match="declared fingerprint"):
        bind_executable_spec(changed, declared_fingerprint=derived_fingerprint(spec))


def test_data_and_cost_do_not_create_behavioral_family():
    spec = _spec()
    changed = replace(
        spec,
        dataset={"manifest_id": "OTHER", "content_hash": "b" * 64},
        cost_model_reference="OTHER_COST",
    )
    assert bind_executable_spec(spec).behavior_hash == bind_executable_spec(changed).behavior_hash
    assert bind_executable_spec(spec).executable_spec_hash != bind_executable_spec(changed).executable_spec_hash


def test_true_orthogonal_gate_stays_descendant():
    base = _spec()
    gated = replace(base, confirmation_gates=("RELATIVE_VOLUME_GATE",))
    decision = classify_bound_spec(bind_executable_spec(gated), [_signature(base)])
    assert decision["classification"] == "DESCENDANT_MECHANISM_CHANGE"
    assert decision["root_family"] == "FAM-BREAKOUT"


def test_alias_cannot_reset_budget_and_exhaustion_is_enforced():
    base = _spec()
    gated = replace(base, confirmation_gates=("ORTHOGONAL_GATE",))
    with pytest.raises(SearchMemoryError, match="budget exhausted"):
        admit_executable_spec(
            gated,
            declared_family="BREAKOUT_ALIAS",
            declared_fingerprint=derived_fingerprint(gated),
            signatures=[_signature(base)],
            aliases={"BREAKOUT_ALIAS": "FAM-BREAKOUT"},
            family_budget_remaining=False,
        )


def test_manual_hash_runtime_drift_and_missing_spec_are_rejected():
    spec = _spec()
    with pytest.raises(SearchMemoryError, match="caller-supplied"):
        bind_executable_spec(spec, declared_behavior_hash="0" * 64)
    with pytest.raises(SearchMemoryError, match="runner executable"):
        bind_executable_spec(
            spec,
            runtime_spec=replace(spec, confirmation_gates=("CHANGED_AT_RUNTIME",)),
        )
    with pytest.raises(SearchMemoryError, match="missing"):
        bind_executable_spec(None)


def test_all_frozen_legacy_signatures_validate():
    assert validate_legacy_signatures() == {
        "version": "SEARCH_MEMORY_V2",
        "legacy_signatures": 9,
        "status": "PASS",
    }
    assert validate_search_memory_v2()["breakout_strategy_budget"] == "EXHAUSTED"
