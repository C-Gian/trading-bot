from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from app.research.search_memory import (
    ROOT,
    SearchMemoryError,
    accounting,
    admit_proposal,
    canonical_json,
    classify_proposal,
    fingerprint_hash,
    load_memory,
    resolve_family,
    text_sha256,
    validate_memory,
)


@pytest.fixture
def memory():
    value = load_memory()
    # Historical six provide a fixed test base even after new admissions are appended.
    value["entries"] = [x for x in value["entries"] if x["work_package"] == "WP-003"]
    value["outcomes"] = [
        x
        for x in value["outcomes"]
        if x["experiment_id"] in {r["experiment_id"] for r in value["entries"]}
    ]
    return value


def _baseline(memory):
    return deepcopy(next(x for x in memory["entries"] if "BREAKOUT" in x["experiment_id"]))


def _hashes(proposal):
    proposal["behavior_hash"] = fingerprint_hash(proposal["fingerprint"])
    proposal["structure_hash"] = fingerprint_hash(proposal["fingerprint"], structural=True)
    return proposal


def _gated(memory, *, evidence=True):
    proposal = _baseline(memory)
    source = next(x for x in memory["outcomes"] if x["experiment_id"] == proposal["experiment_id"])
    proposal.update(
        experiment_id="EXP-TEST-GATED",
        work_package="WP-004",
        record_kind="PREREGISTERED_ADMISSION",
        strategy_label="Synthetic admission test, not a real strategy trial",
        hypothesis_id="HYP-SELECTIVE-CONTINUATION-V1",
        parent_experiment_ids=["EXP-BASE-004-BREAKOUT"],
        parent_family_id="FAM-BREAKOUT",
        novelty="REVISIT_WITH_NEW_EVIDENCE",
        scientific_reason="Test whether completed 4h directional context isolates a distinct subset.",
        budget_units={
            "experiments": 1,
            "strategy_variants": 1,
            "trials": 4,
            "numeric_parameter_variants": 0,
        },
        new_evidence_basis={
            "kind": "OBSERVED_DIAGNOSTIC_WITH_STRUCTURAL_RESPONSE",
            "source_experiment_id": source["experiment_id"],
            "source_path": source["result_path"],
            "source_sha256": source["result_sha256"],
            "observations": [
                {"json_pointer": "/primary_result", "expected_value": -0.0482093869},
                {
                    "json_pointer": "/secondary_results/zero_cost_metrics/net_expectancy_r",
                    "expected_value": 0.0722123707,
                },
            ],
            "structural_response": "A completed 4h context gate selects directional persistence.",
            "falsifiable_prediction": "Default-cost expectancy remains positive across fixed folds.",
        }
        if evidence
        else None,
    )
    proposal["fingerprint"]["context_minutes"] = 240
    proposal["fingerprint"]["regime_filter"] = "SIGNED_EFFICIENCY_GATE"
    return _hashes(proposal)


def test_exact_wp003_breakout_is_rejected(memory):
    proposal = _baseline(memory)
    proposal["experiment_id"] = "EXP-TEST-REPLAY"
    assert classify_proposal(proposal, memory)["classification"] == "DUPLICATE"
    with pytest.raises(SearchMemoryError, match="DUPLICATE"):
        admit_proposal(proposal, memory)


def test_window_24_to_25_is_parameter_variant(memory):
    proposal = _baseline(memory)
    proposal["fingerprint"]["parameters"]["breakout_hours"] = 25
    assert classify_proposal(proposal, memory)["classification"] == "PARAMETER_VARIANT"
    proposal.update(experiment_id="EXP-TEST-NUMERIC", novelty="PARAMETER_VARIANT")
    with pytest.raises(SearchMemoryError, match="new_evidence_basis"):
        admit_proposal(_hashes(proposal), memory)


def test_renamed_duplicate_and_metadata_drift_are_rejected(memory):
    proposal = _baseline(memory)
    proposal.update(
        experiment_id="EXP-TEST-NEW-NAME",
        strategy_label="A completely different sounding strategy",
        family_id="A_FRESH_FAMILY_NAME",
        claimed_market_mechanism="Changed prose cannot establish novelty.",
        hypothesis_id="NEW_WORDING",
        parent_experiment_ids=[],
    )
    assert classify_proposal(proposal, memory)["classification"] == "DUPLICATE"
    with pytest.raises(SearchMemoryError, match="DUPLICATE"):
        admit_proposal(proposal, memory)


def test_material_four_hour_gate_is_structural_same_family(memory):
    result = classify_proposal(_gated(memory), memory)
    assert result["classification"] == "NEW_MECHANISM_WITHIN_FAMILY"
    assert result["family_id"] == "FAM-BREAKOUT"


def test_failed_family_without_evidence_rejected(memory):
    with pytest.raises(SearchMemoryError, match="new_evidence_basis"):
        admit_proposal(_gated(memory, evidence=False), memory)


def test_failed_family_with_verified_evidence_requires_remaining_budget(memory):
    proposal = _gated(memory)
    assert admit_proposal(proposal, memory)["admitted"]
    memory["budget"]["family_limits"]["FAM-BREAKOUT"]["experiments"] = 1
    with pytest.raises(SearchMemoryError, match="budget exceeded"):
        admit_proposal(proposal, memory)


def test_different_name_same_fingerprint_resolves_same_family(memory):
    proposal = _baseline(memory)
    proposal.update(family_id="REBRANDED_FAMILY", parent_family_id=None, parent_experiment_ids=[])
    assert resolve_family(proposal, memory) == "FAM-BREAKOUT"


def test_current_algorithm_exact_replay_rejected(memory):
    current = [x for x in load_memory()["entries"] if x["work_package"] == "WP-004"]
    if not current:
        # Before preregistration, exercise identical admission semantics on synthetic declaration.
        current = [_gated(memory)]
        assert admit_proposal(current[0], memory)["admitted"]
    replay_memory = {**memory, "entries": [*memory["entries"], *current]}
    for registered in current:
        replay = deepcopy(registered)
        replay["experiment_id"] = "EXP-TEST-CURRENT-REPLAY"
        with pytest.raises(SearchMemoryError, match="DUPLICATE"):
            admit_proposal(replay, replay_memory)


def test_fingerprint_order_numeric_equivalence_and_environment_replay(memory):
    proposal = _baseline(memory)
    original = fingerprint_hash(proposal["fingerprint"])
    proposal["fingerprint"]["parameters"]["breakout_hours"] = 24.0
    proposal["fingerprint"]["parameters"] = dict(
        reversed(list(proposal["fingerprint"]["parameters"].items()))
    )
    proposal["fingerprint"]["dataset"]["content_hash"] = "a" * 64
    assert fingerprint_hash(proposal["fingerprint"]) == original
    assert canonical_json({"feature_families": ["B", "A"]}) == canonical_json(
        {"feature_families": ["A", "B"]}
    )
    with pytest.raises(SearchMemoryError, match="non-finite"):
        fingerprint_hash({"parameters": {"x": float("nan")}})


def test_fake_observation_and_prose_only_evidence_rejected(memory):
    proposal = _gated(memory)
    proposal["new_evidence_basis"]["observations"][0]["expected_value"] = 0.25
    with pytest.raises(SearchMemoryError, match="observation differs"):
        admit_proposal(proposal, memory)
    proposal["new_evidence_basis"] = "Maybe this number works better"
    with pytest.raises(SearchMemoryError, match="schema"):
        admit_proposal(proposal, memory)


def test_numeric_drift_cannot_reuse_old_failure_as_new_evidence(memory):
    proposal = _gated(memory)
    proposal["fingerprint"] = _baseline(memory)["fingerprint"]
    proposal["fingerprint"]["parameters"]["breakout_hours"] = 25
    with pytest.raises(SearchMemoryError, match="numeric drift"):
        admit_proposal(_hashes(proposal), memory)


def test_feature_renaming_without_structural_change_is_near_duplicate(memory):
    proposal = _baseline(memory)
    proposal["fingerprint"]["feature_transformations"] = ["REWORDED_ROLLING_MAX"]
    assert classify_proposal(proposal, memory)["classification"] == "NEAR_DUPLICATE"


def test_declared_parent_gate_removal_is_meaningful_ablation(memory):
    aligned = _gated(memory)
    aligned["fingerprint"]["confirmation_filter"] = "RELATIVE_VOLUME_GATE"
    _hashes(aligned)
    assert admit_proposal(aligned, memory)["admitted"]
    memory["entries"].append(aligned)
    ablation = deepcopy(aligned)
    ablation.update(
        experiment_id="EXP-TEST-REGIME-ABLATION",
        parent_experiment_ids=[aligned["experiment_id"], "EXP-BASE-004-BREAKOUT"],
        novelty="MEANINGFUL_ABLATION",
    )
    ablation["fingerprint"]["regime_filter"] = "NONE"
    decision = admit_proposal(_hashes(ablation), memory)
    assert decision["classification"] == "MEANINGFUL_ABLATION"
    assert decision["family_id"] == "FAM-BREAKOUT"


def test_near_duplicate_without_reason_is_rejected(memory):
    proposal = _gated(memory)
    proposal["scientific_reason"] = " "
    with pytest.raises(SearchMemoryError, match="scientific reason"):
        admit_proposal(proposal, memory)


def test_ancestor_budget_cannot_be_reset_by_child_family(memory):
    proposal = _gated(memory)
    memory["families"]["families"].append(
        {
            "family_id": "CHILD-RENAME",
            "aliases": [],
            "entry_event_anchors": ["A_NEW_LABEL"],
            "parent_family_id": "FAM-BREAKOUT",
            "mechanism": "Same failed ancestor",
            "status": "ACTIVE_BOUNDED_RESEARCH",
            "failure_experiment_ids": [],
            "legitimate_revisit": "Parent evidence and budget still required.",
        }
    )
    proposal.update(family_id="CHILD-RENAME", parent_family_id="CHILD-RENAME")
    assert resolve_family(proposal, memory) == "FAM-BREAKOUT"
    with pytest.raises(SearchMemoryError, match="rename cannot reset budget"):
        admit_proposal(proposal, memory)


def test_import_accounting_and_registered_evidence_integrity(memory):
    counts = accounting(memory)
    assert counts["global"] == {
        "experiments": 6,
        "strategy_variants": 6,
        "trials": 41,
        "numeric_parameter_variants": 0,
    }
    assert counts["material_economic_hypotheses"] == 2
    assert counts["reference_control_experiments"] == 4
    assert counts["families"]["FAM-RANDOM"]["trials"] == 32
    assert validate_memory()["completed_experiments"] >= 6


def test_text_evidence_hash_is_platform_independent(tmp_path: Path):
    lf, crlf = tmp_path / "lf.json", tmp_path / "crlf.json"
    lf.write_bytes(b'{"x": 1}\n')
    crlf.write_bytes(b'{"x": 1}\r\n')
    assert text_sha256(lf) == text_sha256(crlf)


def test_no_market_data_required_for_memory_validation():
    assert (ROOT / "research/memory/SEARCH_LEDGER.jsonl").is_file()
    assert validate_memory()["sealed_queries"] == 0
