"""WP-007 governance: novelty gate, allocation, registry and substrate gate."""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from app.research.registry import alias_map, cumulative_accounting, signatures, validate_budgets
from app.research.search_memory import SearchMemoryError
from app.research.search_memory_v2 import (
    NumericTerm,
    admit_executable_spec,
    bind_executable_spec,
    classify_bound_spec,
    derived_fingerprint,
)
from app.research.wp007 import (
    ADMISSION_PATH,
    ALLOCATION_PATH,
    ENTRY_EVENT,
    FAMILY_PATH,
    PRIMARY_VARIANT,
    ROOT,
    ROOT_FAMILY,
    SPEC,
    NoveltyRejected,
    OrderFlowGateError,
    executable_spec,
    novelty_decision,
    substrate_gate,
    validate_admission,
    validate_allocation,
    validate_family_record,
)

MIRRORED = (
    ALLOCATION_PATH,
    FAMILY_PATH,
    ADMISSION_PATH,
    "research/memory/HYPOTHESIS_FAMILIES.json",
    "research/memory/SEARCH_BUDGET.json",
    "research/memory/SEARCH_LEDGER.jsonl",
    "research/memory/OUTCOMES.jsonl",
    "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json",
    "research/memory/FAMILY_REGISTRY_V2.json",
    "research/memory/SEARCH_BUDGET_V2.json",
    "research/memory/ADMISSION_LEDGER_V2.jsonl",
    "research/memory/OUTCOMES_V2.jsonl",
    "research/memory/WP006-PULLBACK-RECOVERY-ALLOCATION.json",
    "research/memory/ADAPTIVE_DIAGNOSTICS_V2.json",
    "reports/validation/WP-007-ORDER-FLOW-INTEGRITY.json",
    "reports/validation/WP-007-ORDER-FLOW-RECONCILIATION.json",
    "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json",
)


def _signature(spec, experiment_id="LEGACY"):
    binding = bind_executable_spec(spec)
    return {
        "experiment_id": experiment_id,
        "root_family": spec.root_family,
        "behavior_hash": binding.behavior_hash,
        "structural_hash": binding.structural_hash,
    }


def _mirror(tmp_path: Path) -> Path:
    """A byte-identical copy of everything the deterministic gates read."""
    from app.research.flow_lab import config_path
    from app.research.wp007 import SPEC_DEPENDENCY_PATHS

    root = tmp_path / "repo"
    relatives = [
        *MIRRORED,
        *SPEC_DEPENDENCY_PATHS,
        *(config_path(variant) for variant in SPEC.values()),
    ]
    for relative in relatives:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relative, target)
    return root


def _rewrite(root: Path, relative: str, mutate) -> None:
    payload = json.loads((root / relative).read_text(encoding="utf-8"))
    mutate(payload)
    (root / relative).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# -- substrate gate --------------------------------------------------------


def test_substrate_gate_passes_and_binds_the_audited_identity():
    gate = substrate_gate()
    manifest = json.loads(
        (ROOT / "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json").read_text(encoding="utf-8")
    )
    assert gate["integrity_status"] == "PASS" and gate["reconciliation_status"] == "PASS"
    assert gate["substrate_content_hash"] == manifest["content_hash"]["value"]
    assert gate["eligible_1h_buckets"] > 0 and gate["eligible_4h_buckets"] > 0


@pytest.mark.parametrize(
    "relative,mutate,message",
    [
        (
            "reports/validation/WP-007-ORDER-FLOW-INTEGRITY.json",
            lambda payload: payload.__setitem__("status", "FAIL"),
            "integrity audit did not pass",
        ),
        (
            "reports/validation/WP-007-ORDER-FLOW-INTEGRITY.json",
            lambda payload: payload.__setitem__("material_violations", 1),
            "integrity audit did not pass",
        ),
        (
            "reports/validation/WP-007-ORDER-FLOW-RECONCILIATION.json",
            lambda payload: payload.__setitem__("content_hash_match", False),
            "oracle reconciliation did not pass",
        ),
        (
            "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json",
            lambda payload: payload.__setitem__("canonical_data_modified", True),
            "canonical data was modified",
        ),
    ],
)
def test_a_failed_substrate_gate_blocks_every_market_experiment(
    tmp_path: Path, relative, mutate, message
):
    root = _mirror(tmp_path)
    _rewrite(root, relative, mutate)
    with pytest.raises(OrderFlowGateError, match=message):
        substrate_gate(root)


# -- the governed novelty gate --------------------------------------------


def test_committed_admission_reproduces_and_is_a_new_root():
    recorded = validate_admission()
    assert recorded["family_classification"] == "NEW_FAMILY"
    assert recorded["admitted"] is True
    assert recorded["market_results_observed_at_admission"] == 0
    assert recorded["classifier_modified"] is False
    assert recorded["renamed_to_force_novelty"] is False
    assert recorded["conditions_added_to_force_novelty"] is False
    core, confirm = recorded["variants"]
    assert core["classification"] == "NEW_FAMILY" and core["matched_experiment_ids"] == []
    assert confirm["classification"] == "DESCENDANT_MECHANISM_CHANGE"
    assert confirm["matched_experiment_ids"] == [core["experiment_id"]]
    assert core["hypothesis_role"] == "ECONOMIC_CORE"


def test_the_gate_checks_both_v1_and_v2_historical_signatures():
    recorded = validate_admission()
    reference = recorded["reference_signatures"]
    assert reference["v1_reference_translations"] == 9
    assert reference["v2_admitted_behaviours"] == 2
    wp008 = {
        "EXP-ML-014-LINEAR-NET-R-FULL",
        "EXP-ML-015-LINEAR-NET-R-NO-FLOW",
    }
    wp011 = {"EXP-ML-016-EWLS-INTERNAL-MACRO", "EXP-ML-017-EWLS-INTERNAL-ONLY"}
    wp012 = {
        "EXP-ML-018-REGIME-TWO-EXPERTS",
        "EXP-ML-019-GLOBAL-MATCHED-CONTROL",
    }
    wp013 = {
        "EXP-ML-020-NFCI-CONTEXT-INTERACTIONS",
        "EXP-ML-021-INTERNAL-NFCI-MATCHED",
    }
    assert len(signatures(exclude_experiment_ids=set(SPEC))) == 11
    assert len(signatures(exclude_experiment_ids=wp008)) == 13
    assert len(signatures(exclude_experiment_ids=wp011)) == 15
    assert len(signatures(exclude_experiment_ids=wp012)) == 17
    assert len(signatures(exclude_experiment_ids=wp013)) == 19
    assert len(signatures()) == 21


def test_neither_variant_duplicates_any_prior_admitted_behaviour():
    known = signatures(exclude_experiment_ids=set(SPEC))
    for variant in SPEC.values():
        binding = bind_executable_spec(executable_spec(variant))
        assert binding.behavior_hash not in {item["behavior_hash"] for item in known}
        assert classify_bound_spec(binding, known)["classification"] == "NEW_FAMILY"


def test_the_new_root_does_not_collide_with_any_registered_anchor():
    aliases = alias_map(ROOT, exclude=ROOT_FAMILY)
    assert ROOT_FAMILY not in aliases and ENTRY_EVENT not in aliases
    for anchor in ("CLOSE_ABOVE_PRIOR_HIGH", "FAST_SMA_ABOVE_SLOW_SMA"):
        assert anchor in aliases
    assert "CLOSE_RECOVERS_ABOVE_DAILY_MEAN_AFTER_PULLBACK" in aliases


def test_an_identical_spec_under_a_fresh_name_is_still_a_duplicate():
    spec = executable_spec(PRIMARY_VARIANT)
    known = [*signatures(), _signature(spec, "EXP-ALG-012-ORDERFLOW-CORE")]
    renamed = replace(spec, root_family="FAM-RENAMED", family="FAM-RENAMED")
    with pytest.raises(SearchMemoryError, match="DUPLICATE"):
        admit_executable_spec(
            renamed,
            declared_family="FAM-RENAMED",
            declared_fingerprint=derived_fingerprint(renamed),
            signatures=known,
            aliases={},
        )


def test_moving_the_balance_threshold_would_be_a_parameter_variant():
    """0.51 or 0.55 is numeric drift, not a new mechanism."""
    spec = executable_spec(PRIMARY_VARIANT)
    known = [_signature(spec, "EXP-ALG-012-ORDERFLOW-CORE")]
    for threshold in (0.51, 0.55, 0.6):
        drifted = replace(
            spec,
            numeric_parameters=tuple(
                NumericTerm("balance_threshold", threshold, "share")
                if term.name == "balance_threshold"
                else term
                for term in spec.numeric_parameters
            ),
        )
        decision = classify_bound_spec(bind_executable_spec(drifted), known)
        assert decision["classification"] == "PARAMETER_VARIANT"


def test_a_colliding_root_blocks_execution_instead_of_being_renamed(tmp_path: Path):
    root = _mirror(tmp_path)
    _rewrite(
        root,
        "research/memory/FAMILY_REGISTRY_V2.json",
        lambda payload: payload["families"][0]["entry_event_anchors"].append(ENTRY_EVENT),
    )
    with pytest.raises(NoveltyRejected, match="collides with a registered anchor"):
        novelty_decision(root)


def test_admission_record_cannot_be_edited_after_the_fact(tmp_path: Path):
    root = _mirror(tmp_path)
    _rewrite(
        root,
        ADMISSION_PATH,
        lambda payload: payload["variants"][0].__setitem__("classification", "NEW_FAMILY_FORCED"),
    )
    with pytest.raises(SearchMemoryError, match="differs from the deterministic gate"):
        validate_admission(root)


# -- allocation, registry and budgets --------------------------------------


def test_allocation_authorizes_exactly_one_hypothesis_and_two_variants():
    allocation = validate_allocation()
    assert allocation["new_economic_hypotheses"] == 1
    assert allocation["strategy_variants"] == 2
    assert allocation["numeric_parameter_variants"] == 0
    assert allocation["profile_evaluations"] == 8
    assert allocation["profiles"] == ["DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"]
    assert allocation["threshold_searches"] == 0 and allocation["parameter_searches"] == 0
    assert allocation["additional_controls_or_seeds"] == 0
    assert allocation["cumulative_adaptive_decisions"] == 4
    assert allocation["cumulative_result_dependent_forks"] == 4
    assert allocation["sealed_queries"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("strategy_variants", 3),
        ("numeric_parameter_variants", 1),
        ("profile_evaluations", 12),
        ("threshold_searches", 1),
        ("sealed_queries", 1),
        ("new_economic_hypotheses", 2),
        ("additional_controls_or_seeds", 32),
    ],
)
def test_widened_allocation_is_refused(tmp_path: Path, field, value):
    root = _mirror(tmp_path)
    _rewrite(root, ALLOCATION_PATH, lambda payload: payload.__setitem__(field, value))
    with pytest.raises(SearchMemoryError, match="allocation"):
        validate_allocation(root)


def test_prior_family_dispositions_cannot_be_weakened(tmp_path: Path):
    root = _mirror(tmp_path)
    _rewrite(
        root,
        ALLOCATION_PATH,
        lambda payload: payload.__setitem__(
            "prior_family_budget_policy", "FAM-BREAKOUT may be reopened."
        ),
    )
    with pytest.raises(SearchMemoryError, match="weakened a prior family disposition"):
        validate_allocation(root)


def test_family_record_is_bound_to_its_governed_admission(tmp_path: Path):
    assert validate_family_record()["family_id"] == ROOT_FAMILY
    root = _mirror(tmp_path)
    _rewrite(
        root, FAMILY_PATH, lambda payload: payload.__setitem__("parent_family_id", "FAM-TREND")
    )
    with pytest.raises(SearchMemoryError, match="admitted root identity"):
        validate_family_record(root)


def test_no_family_exceeds_its_budget_and_prior_budgets_are_unchanged():
    consumed = validate_budgets()
    assert consumed["FAM-BREAKOUT"] == {
        "experiments": 4,
        "strategy_variants": 4,
        "trials": 15,
        "numeric_parameter_variants": 0,
    }
    assert consumed["FAM-PULLBACK-RECOVERY"] == {
        "experiments": 2,
        "strategy_variants": 2,
        "trials": 8,
        "numeric_parameter_variants": 0,
    }


def test_cumulative_accounting_never_resets_a_counter():
    totals = cumulative_accounting()
    assert totals["numeric_parameter_variants"] == 0
    assert totals["sealed_queries"] == 0
    assert totals["configuration_variants"] >= 11
    assert totals["profile_trials"] >= 61
    assert totals["adaptive_decisions"] >= 3
