"""WP-006 governance: novelty gate, allocation and budget. No market data is loaded."""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from app.research.search_memory import SearchMemoryError
from app.research.search_memory_v2 import (
    admit_executable_spec,
    bind_executable_spec,
    classify_bound_spec,
    derived_fingerprint,
    validate_search_memory_v2,
)
from app.research.wp006 import (
    ADMISSION_PATH,
    ALLOCATION_PATH,
    BUDGET_PATH,
    ENTRY_EVENT,
    PRIMARY_VARIANT,
    REGISTRY_PATH,
    ROOT,
    ROOT_FAMILY,
    SPEC,
    NoveltyRejected,
    alias_map,
    executable_spec,
    legacy_signatures,
    novelty_decision,
    validate_admission,
    validate_allocation,
    validate_registry,
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
    """A byte-identical copy of everything the deterministic gate reads."""
    from app.research.pullback_lab import config_path
    from app.research.wp006 import SPEC_DEPENDENCY_PATHS

    root = tmp_path / "repo"
    relatives = [
        REGISTRY_PATH,
        BUDGET_PATH,
        ALLOCATION_PATH,
        ADMISSION_PATH,
        "research/memory/HYPOTHESIS_FAMILIES.json",
        "research/memory/SEARCH_BUDGET.json",
        "research/memory/SEARCH_LEDGER.jsonl",
        "research/memory/OUTCOMES.jsonl",
        "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json",
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


# -- the governed novelty gate --------------------------------------------


def test_committed_admission_reproduces_and_is_a_new_root():
    recorded = validate_admission()
    assert recorded["family_classification"] == "NEW_FAMILY"
    assert recorded["admitted"] is True
    assert recorded["market_results_observed_at_admission"] == 0
    assert recorded["classifier_modified"] is False
    assert recorded["renamed_to_force_novelty"] is False
    assert [item["experiment_id"] for item in recorded["variants"]] == list(SPEC)
    core, confirm = recorded["variants"]
    assert core["classification"] == "NEW_FAMILY" and core["matched_experiment_ids"] == []
    assert confirm["classification"] == "DESCENDANT_MECHANISM_CHANGE"
    assert confirm["matched_experiment_ids"] == [core["experiment_id"]]
    assert core["hypothesis_role"] == "ECONOMIC_CORE"


def test_the_new_root_does_not_collide_with_any_registered_anchor():
    aliases = alias_map(ROOT, exclude=ROOT_FAMILY)
    assert ROOT_FAMILY not in aliases and ENTRY_EVENT not in aliases
    assert "CLOSE_ABOVE_PRIOR_HIGH" in aliases and "FAST_SMA_ABOVE_SLOW_SMA" in aliases


def test_breakout_budget_remains_exhausted_and_is_not_reopened():
    assert validate_search_memory_v2()["breakout_strategy_budget"] == "EXHAUSTED"
    registry = json.loads((ROOT / REGISTRY_PATH).read_text(encoding="utf-8"))
    assert [item["family_id"] for item in registry["families"]] == [ROOT_FAMILY]
    budget = json.loads((ROOT / BUDGET_PATH).read_text(encoding="utf-8"))
    assert budget["prior_consumed"] == {
        "experiments": 9,
        "strategy_variants": 9,
        "trials": 53,
        "numeric_parameter_variants": 0,
    }


def test_neither_variant_duplicates_a_frozen_legacy_strategy():
    signatures = legacy_signatures()
    assert len(signatures) == 9
    for variant in SPEC.values():
        binding = bind_executable_spec(executable_spec(variant))
        decision = classify_bound_spec(binding, signatures)
        assert decision["classification"] == "NEW_FAMILY"
        assert binding.behavior_hash not in {item["behavior_hash"] for item in signatures}


def test_an_identical_spec_under_a_fresh_name_is_still_a_duplicate():
    spec = executable_spec(PRIMARY_VARIANT)
    signatures = [*legacy_signatures(), _signature(spec, "EXP-ALG-010-PULLBACK-RECOVERY-CORE")]
    renamed = replace(spec, root_family="FAM-RENAMED", family="FAM-RENAMED")
    with pytest.raises(SearchMemoryError, match="DUPLICATE"):
        admit_executable_spec(
            renamed,
            declared_family="FAM-RENAMED",
            declared_fingerprint=derived_fingerprint(renamed),
            signatures=signatures,
            aliases={},
        )


def test_numeric_drift_would_be_a_parameter_variant_not_a_new_family():
    from app.research.search_memory_v2 import NumericTerm

    spec = executable_spec(PRIMARY_VARIANT)
    drifted = replace(
        spec,
        numeric_parameters=tuple(
            NumericTerm("sma_hours", 20, "hours") if term.name == "sma_hours" else term
            for term in spec.numeric_parameters
        ),
    )
    signatures = [_signature(spec, "EXP-ALG-010-PULLBACK-RECOVERY-CORE")]
    decision = classify_bound_spec(bind_executable_spec(drifted), signatures)
    assert decision["classification"] == "PARAMETER_VARIANT"


def test_a_colliding_root_blocks_execution_instead_of_being_renamed(tmp_path: Path):
    root = _mirror(tmp_path)
    _rewrite(
        root,
        "research/memory/HYPOTHESIS_FAMILIES.json",
        lambda payload: payload["families"][3]["entry_event_anchors"].append(ENTRY_EVENT),
    )
    with pytest.raises(NoveltyRejected, match="collides with a registered anchor"):
        novelty_decision(root)


def test_runtime_spec_drift_invalidates_the_binding():
    spec = executable_spec(PRIMARY_VARIANT)
    with pytest.raises(SearchMemoryError, match="runner executable"):
        bind_executable_spec(
            spec, runtime_spec=replace(spec, confirmation_gates=("CHANGED_AT_RUNTIME",))
        )


# -- allocation and budget -------------------------------------------------


def test_allocation_authorizes_exactly_one_hypothesis_and_two_variants():
    allocation = validate_allocation()
    assert allocation["new_economic_hypotheses"] == 1
    assert allocation["strategy_variants"] == 2
    assert allocation["numeric_parameter_variants"] == 0
    assert allocation["profile_evaluations"] == 8
    assert allocation["profiles"] == ["DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"]
    assert allocation["cumulative_adaptive_decisions"] == 3
    assert allocation["cumulative_result_dependent_forks"] == 3
    assert allocation["sealed_queries"] == 0 and allocation["parameter_searches"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("strategy_variants", 3),
        ("numeric_parameter_variants", 1),
        ("profile_evaluations", 12),
        ("sealed_queries", 1),
        ("new_economic_hypotheses", 2),
    ],
)
def test_widened_allocation_is_refused(tmp_path: Path, field, value):
    root = _mirror(tmp_path)
    _rewrite(root, ALLOCATION_PATH, lambda payload: payload.__setitem__(field, value))
    with pytest.raises(SearchMemoryError, match="allocation"):
        validate_allocation(root)


def test_v2_budget_cannot_admit_an_unauthorized_family(tmp_path: Path):
    root = _mirror(tmp_path)
    _rewrite(
        root,
        BUDGET_PATH,
        lambda payload: payload["family_limits"].__setitem__(
            "FAM-BREAKOUT",
            {
                "experiments": 4,
                "strategy_variants": 4,
                "trials": 15,
                "numeric_parameter_variants": 0,
            },
        ),
    )
    with pytest.raises(SearchMemoryError, match="unauthorized family"):
        validate_registry(root)


def test_v2_registry_cannot_admit_a_second_family(tmp_path: Path):
    root = _mirror(tmp_path)
    _rewrite(
        root,
        REGISTRY_PATH,
        lambda payload: payload["families"].append(
            {
                "family_id": "FAM-EXTRA",
                "aliases": [],
                "entry_event_anchors": [],
                "parent_family_id": None,
            }
        ),
    )
    with pytest.raises(SearchMemoryError, match="never allocated"):
        validate_registry(root)


def test_admission_record_cannot_be_edited_after_the_fact(tmp_path: Path):
    root = _mirror(tmp_path)
    _rewrite(
        root,
        ADMISSION_PATH,
        lambda payload: payload["variants"][0].__setitem__("classification", "NEW_FAMILY_FORCED"),
    )
    with pytest.raises(SearchMemoryError, match="differs from the deterministic gate"):
        validate_admission(root)
