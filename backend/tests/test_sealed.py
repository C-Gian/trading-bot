"""Synthetic sealed-evaluation tests. No reserved BTCUSDT data exists or is created."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from app.sealed import (
    SealedAccessDenied,
    SealedEvaluationError,
    SealedEvaluator,
    development_open,
    is_sealed_path,
    load_budget,
    manifest_is_development_only,
    public_status,
)
from app.sealed.evaluator import request_identity
from app.sealed.isolation import ROOT

SCOPE = "SYNTHETIC_TEST_SCOPE"
PRIMARY = "pooled_net_expectancy_r"


def _freeze(request: dict[str, Any]) -> dict[str, Any]:
    request["request_hash"] = request_identity(request)
    return request


@pytest.fixture
def lab(tmp_path: Path) -> Path:
    """A synthetic repository whose only sealed dataset is a fabricated fixture."""
    root = tmp_path / "repo"
    (root / "contracts").mkdir(parents=True)
    (root / "research/sealed/SYNTHETIC/results").mkdir(parents=True)
    (root / "data/manifests").mkdir(parents=True)
    (root / "data/sealed/SYNTHETIC").mkdir(parents=True)
    (root / "research/experiments/EXP-SYNTH-001").mkdir(parents=True)
    for name in ("sealed_evaluation_request.schema.json", "sealed_evaluation_result.schema.json"):
        shutil.copy(ROOT / "contracts" / name, root / "contracts" / name)
    shutil.copy(
        ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json",
        root / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json",
    )
    (root / "data/sealed/SYNTHETIC/fixture.json").write_text('{"synthetic": true}\n')
    (root / "research/sealed/SYNTHETIC/CONSUMPTION_LEDGER.jsonl").write_text("")
    (root / "research/experiments/EXP-SYNTH-001/result.json").write_text(
        '{"experiment_id": "EXP-SYNTH-001"}\n', encoding="utf-8", newline="\n"
    )
    (root / "strategy.py").write_text("# synthetic frozen strategy\n", encoding="utf-8")
    _write_allocation(root)
    _write_budget(root, authorized=1)
    _write_eligibility(root, classification="PROMISING_DEVELOPMENT_ONLY")
    return root


ALLOCATION_PATH = "research/sealed/allocations/SYNTHETIC-ALLOC.json"


def _write_allocation(
    root: Path, *, issuer: str = "RESEARCH_DIRECTOR", queries: int = 1, **changes
):
    payload = {
        "schema_version": 1,
        "allocation_id": "SYNTHETIC-ALLOC",
        "kind": "SEALED_SCIENTIFIC_ALLOCATION",
        "issuer": issuer,
        "scope": SCOPE,
        "authorized_queries": queries,
        "candidate_experiment_ids": ["EXP-SYNTH-001"],
        "real_money_authorized": False,
    }
    payload.update(changes)
    path = root / ALLOCATION_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def _write_budget(
    root: Path,
    *,
    authorized: int,
    consumed: int = 0,
    record: str | None = ALLOCATION_PATH,
    allocation_queries: int | None = None,
) -> None:
    """Keep the Research Director allocation consistent with the budget it grants."""
    if authorized > 0 and record == ALLOCATION_PATH:
        _write_allocation(
            root, queries=authorized if allocation_queries is None else allocation_queries
        )
    (root / "research/sealed/SEALED_QUERY_BUDGET.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "SEALED_EVALUATION_V1_1",
                "eligibility_table": "research/sealed/SYNTHETIC_ELIGIBILITY.json",
                "isolation_policy": "APPLICATION_AND_REPOSITORY_LAYER_ONLY_NOT_OS_ENFORCED",
                "authorization_policy": {
                    "authority": "RESEARCH_DIRECTOR_SEALED_ALLOCATION",
                    "allocation_directory": "research/sealed/allocations",
                    "executor_self_authorization": False,
                    "automated_self_authorization": False,
                    "accepted_issuers": ["RESEARCH_DIRECTOR"],
                    "rejected_issuers": ["EXECUTOR", "AUTOMATION"],
                    "owner_gate_required_for": ["REAL_CAPITAL"],
                },
                "scopes": {
                    SCOPE: {
                        "symbol": "SYNTHETIC",
                        "dataset_state": "SYNTHETIC_FIXTURE",
                        "sealed_interval_start": "2025-01-01T00:00:00Z",
                        "authorized_queries": authorized,
                        "consumed_queries": consumed,
                        "status": (
                            "LOCKED_NO_AUTHORIZED_QUERY" if authorized == 0 else "AUTHORIZED"
                        ),
                        "authorization_record": None if authorized == 0 else record,
                        "sealed_root": "data/sealed/SYNTHETIC",
                        "consumption_ledger": "research/sealed/SYNTHETIC/CONSUMPTION_LEDGER.jsonl",
                        "result_directory": "research/sealed/SYNTHETIC/results",
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_eligibility(root: Path, *, classification: str, allocation: str = "SYNTHETIC-ALLOC"):
    (root / "research/sealed/SYNTHETIC_ELIGIBILITY.json").write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "experiment_id": "EXP-SYNTH-001",
                        "terminal_classification": classification,
                        "structural_validator": "PASS",
                        "search_memory_v2_binding": "VALID",
                        "unresolved_material_integrity_issues": 0,
                        "sealed_allocation": {"allocation_id": allocation},
                        "executable_spec_hash": "a" * 64,
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _request(root: Path, **changes: Any) -> dict[str, Any]:
    from app.sealed.evaluator import canonical_hash, text_sha256

    dependencies = [{"path": "strategy.py", "sha256": text_sha256(root / "strategy.py")}]
    result_hash = text_sha256(root / "research/experiments/EXP-SYNTH-001/result.json")
    request = {
        "schema_version": 1,
        "version": "SEALED_EVALUATION_V1",
        "query_id": "SYNTH-QUERY-001",
        "scope": SCOPE,
        "created_at_utc": "2026-01-01T00:00:00Z",
        "candidate": {
            "experiment_id": "EXP-SYNTH-001",
            "experiment_version": 1,
            "terminal_classification": "PROMISING_DEVELOPMENT_ONLY",
            "development_result_path": "research/experiments/EXP-SYNTH-001/result.json",
            "development_result_sha256": result_hash,
        },
        "executable_spec_hash": "a" * 64,
        "dependency_hash": canonical_hash(sorted([x["path"], x["sha256"]] for x in dependencies)),
        "dependencies": dependencies,
        "development_result_hash": result_hash,
        "sealed_interval": {
            "dataset_id": "SYNTHETIC-SEALED-v1",
            "content_hash": "b" * 64,
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-06-30T23:59:00Z",
            "path": "data/sealed/SYNTHETIC/fixture.json",
        },
        "engine_version": "BACKTEST_ENGINE_V2",
        "execution_model_version": "EXECUTION_MODEL_V2",
        "cost_model_version": "BTCUSDT_SPOT_COST_V1",
        "primary_metric": PRIMARY,
        "allowed_secondary_metrics": ["trade_count"],
        "robustness_profiles": ["DEFAULT", "DOUBLE"],
        "query_budget": {"authorized_queries": 1, "requested_queries": 1},
        "allocation": {
            "allocation_id": "SYNTHETIC-ALLOC",
            "authority": "tests",
            "research_director_record": "tests",
        },
        "request_hash": "0" * 64,
    }
    request.update(changes)
    return _freeze(request)


def _runner(_request: Any) -> dict[str, Any]:
    return {PRIMARY: 0.25, "trade_count": 180}


# -- repository state ------------------------------------------------------


def test_repository_sealed_scope_is_locked_with_zero_queries():
    status = public_status()
    scope = status["scopes"][0]
    assert status["version"] == "SEALED_EVALUATION_V1_1"
    assert scope["scope"] == "BTCUSDT_POST_CUTOFF" and scope["symbol"] == "BTCUSDT"
    assert scope["status"] == "LOCKED_NO_AUTHORIZED_QUERY"
    assert scope["authorized_queries"] == 0 and scope["consumed_queries"] == 0
    assert scope["dataset_state"] == "RESERVED_NOT_ACQUIRED"
    assert not (ROOT / "data/sealed").exists()


def test_repository_isolation_claim_is_not_overstated():
    assert load_budget()["isolation_policy"].endswith("NOT_OS_ENFORCED")


def test_repository_uses_v1_1_research_director_authority():
    budget = load_budget()
    assert budget["version"] == "SEALED_EVALUATION_V1_1"
    policy = budget["authorization_policy"]
    assert policy["authority"] == "RESEARCH_DIRECTOR_SEALED_ALLOCATION"
    assert policy["executor_self_authorization"] is False
    assert policy["automated_self_authorization"] is False
    assert policy["accepted_issuers"] == ["RESEARCH_DIRECTOR"]
    assert sorted(policy["rejected_issuers"]) == ["AUTOMATION", "EXECUTOR"]
    assert "REAL_CAPITAL" in policy["owner_gate_required_for"]
    assert not list((ROOT / "research/sealed/allocations").glob("*.json"))
    assert budget["scopes"]["BTCUSDT_POST_CUTOFF"]["authorization_record"] is None


def test_eligibility_rules_are_unchanged_by_the_authority_correction():
    """V1.1 changes who may allocate, never who may be queried."""
    from app.sealed.evaluator import ELIGIBLE

    assert ELIGIBLE == "PROMISING_DEVELOPMENT_ONLY"
    table = json.loads(
        (ROOT / "research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json").read_text(encoding="utf-8")
    )
    assert all(
        row["sealed_eligibility"] != "DEVELOPMENT_ELIGIBLE" or row["sealed_allocation"]
        for row in table["candidates"]
    )


def test_a_raised_budget_without_an_allocation_is_refused(lab: Path):
    _write_budget(lab, authorized=1, record=None)
    with pytest.raises(SealedEvaluationError, match="without an allocation"):
        load_budget(lab)


@pytest.mark.parametrize("issuer", ["EXECUTOR", "AUTOMATION"])
def test_executor_and_automation_cannot_self_authorize(lab: Path, issuer: str):
    _write_allocation(lab, issuer=issuer)
    with pytest.raises(SealedEvaluationError, match="self-authorized"):
        load_budget(lab)
    with pytest.raises(SealedEvaluationError, match="self-authorized"):
        SealedEvaluator(lab).evaluate(_request(lab), _runner)


def test_an_allocation_cannot_grant_more_than_it_declares(lab: Path):
    _write_budget(lab, authorized=2, allocation_queries=1)
    with pytest.raises(SealedEvaluationError, match="does not grant the claimed query count"):
        load_budget(lab)


def test_an_allocation_for_another_scope_is_refused(lab: Path):
    _write_allocation(lab, scope="OTHER_SCOPE")
    with pytest.raises(SealedEvaluationError, match="different scope"):
        load_budget(lab)


def test_a_sealed_allocation_can_never_authorize_real_capital(lab: Path):
    _write_allocation(lab, real_money_authorized=True)
    with pytest.raises(SealedEvaluationError, match="never authorize real capital"):
        load_budget(lab)


def test_a_budget_claiming_executor_self_authorization_is_refused(lab: Path):
    path = lab / "research/sealed/SEALED_QUERY_BUDGET.json"
    budget = json.loads(path.read_text(encoding="utf-8"))
    budget["authorization_policy"]["executor_self_authorization"] = True
    path.write_text(json.dumps(budget, indent=2), encoding="utf-8")
    with pytest.raises(SealedEvaluationError, match="may self-authorize"):
        load_budget(lab)


def test_an_allocation_outside_the_declared_directory_is_refused(lab: Path):
    stray = lab / "research/sealed/STRAY-ALLOC.json"
    stray.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "allocation_id": "STRAY",
                "kind": "SEALED_SCIENTIFIC_ALLOCATION",
                "issuer": "RESEARCH_DIRECTOR",
                "scope": SCOPE,
                "authorized_queries": 1,
                "candidate_experiment_ids": ["EXP-SYNTH-001"],
                "real_money_authorized": False,
            }
        ),
        encoding="utf-8",
    )
    _write_budget(lab, authorized=1, record="research/sealed/STRAY-ALLOC.json")
    with pytest.raises(SealedEvaluationError, match="must live under"):
        load_budget(lab)


def test_a_locked_scope_may_not_name_an_allocation(lab: Path):
    _write_budget(lab, authorized=0)
    path = lab / "research/sealed/SEALED_QUERY_BUDGET.json"
    budget = json.loads(path.read_text(encoding="utf-8"))
    budget["scopes"][SCOPE]["authorization_record"] = ALLOCATION_PATH
    path.write_text(json.dumps(budget, indent=2), encoding="utf-8")
    with pytest.raises(SealedEvaluationError, match="locked but names an authorization record"):
        load_budget(lab)


def test_unauthorized_btc_request_is_refused_before_touching_anything(lab: Path):
    _write_budget(lab, authorized=0)
    evaluator = SealedEvaluator(lab)
    with pytest.raises(SealedAccessDenied, match="LOCKED_NO_AUTHORIZED_QUERY"):
        evaluator.evaluate(
            _request(lab, query_budget={"authorized_queries": 0, "requested_queries": 1}), _runner
        )
    assert (lab / "research/sealed/SYNTHETIC/CONSUMPTION_LEDGER.jsonl").read_text() == ""
    assert not list((lab / "research/sealed/SYNTHETIC/results").iterdir())


# -- development loader isolation -----------------------------------------


def test_development_loader_cannot_open_a_sealed_path(lab: Path):
    assert is_sealed_path("data/sealed/SYNTHETIC/fixture.json", lab)
    assert is_sealed_path("data/canonical/../sealed/SYNTHETIC/fixture.json", lab)
    with pytest.raises(SealedAccessDenied, match="may not open a sealed path"):
        development_open("data/sealed/SYNTHETIC/fixture.json", lab)
    with development_open("data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json", lab) as handle:
        assert handle.read(1) == b"{"


def test_approved_development_manifest_references_no_sealed_path():
    manifest = json.loads(
        (ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json").read_text(encoding="utf-8")
    )
    assert manifest_is_development_only(manifest)


def test_ordinary_research_loader_is_pinned_to_the_development_manifest():
    """The loader admits one byte-pinned manifest, so no sealed path is reachable."""
    from app.research.continuation_lab import MANIFEST_SHA256
    from app.research.runner import sha256

    approved = ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
    assert sha256(approved) == MANIFEST_SHA256
    assert not is_sealed_path(approved)


# -- governance gates ------------------------------------------------------


def test_inconclusive_candidate_cannot_query(lab: Path):
    _write_eligibility(lab, classification="INCONCLUSIVE")
    request = _request(
        lab, candidate={**_request(lab)["candidate"], "terminal_classification": "INCONCLUSIVE"}
    )
    with pytest.raises(SealedEvaluationError, match="not seal-eligible"):
        SealedEvaluator(lab).evaluate(request, _runner)


def test_missing_sealed_allocation_is_refused(lab: Path):
    _write_eligibility(lab, classification="PROMISING_DEVELOPMENT_ONLY", allocation="OTHER-ALLOC")
    with pytest.raises(SealedEvaluationError, match="explicit Research Director sealed allocation"):
        SealedEvaluator(lab).evaluate(_request(lab), _runner)


def test_missing_executable_spec_identity_is_refused(lab: Path):
    request = deepcopy(_request(lab))
    del request["executable_spec_hash"]
    with pytest.raises(Exception, match="executable_spec_hash"):
        SealedEvaluator(lab).evaluate(request, _runner)


def test_code_drift_after_freezing_is_refused(lab: Path):
    request = _request(lab)
    (lab / "strategy.py").write_text("# edited after the freeze\n", encoding="utf-8")
    with pytest.raises(SealedEvaluationError, match="code/config drift"):
        SealedEvaluator(lab).evaluate(request, _runner)


def test_mutated_request_is_refused(lab: Path):
    request = _request(lab)
    request["primary_metric"] = "something_else"
    with pytest.raises(SealedEvaluationError, match="mutated after it was frozen"):
        SealedEvaluator(lab).evaluate(request, _runner)


def test_development_and_sealed_datasets_must_be_separate(lab: Path):
    development = json.loads(
        (lab / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json").read_text(encoding="utf-8")
    )
    request = _request(
        lab,
        sealed_interval={
            **_request(lab)["sealed_interval"],
            "dataset_id": development["manifest_id"],
        },
    )
    with pytest.raises(SealedEvaluationError, match="separate identities"):
        SealedEvaluator(lab).evaluate(request, _runner)


def test_sealed_interval_cannot_reach_development_history(lab: Path):
    request = _request(
        lab,
        sealed_interval={
            **_request(lab)["sealed_interval"],
            "start": "2024-06-01T00:00:00Z",
            "end": "2024-12-01T00:00:00Z",
        },
    )
    with pytest.raises(SealedEvaluationError, match="after the development cutoff"):
        SealedEvaluator(lab).evaluate(request, _runner)


def test_undeclared_metric_is_refused_and_still_consumes_budget(lab: Path):
    def greedy(_request: Any) -> dict[str, Any]:
        return {PRIMARY: 0.25, "trade_count": 180, "sharpe": 1.4}

    with pytest.raises(SealedEvaluationError, match="undeclared sealed metric"):
        SealedEvaluator(lab).evaluate(_request(lab), greedy)
    ledger = (lab / "research/sealed/SYNTHETIC/CONSUMPTION_LEDGER.jsonl").read_text()
    assert len(ledger.splitlines()) == 1


# -- successful synthetic query and its consequences -----------------------


def test_authorized_synthetic_query_succeeds_once(lab: Path):
    result = SealedEvaluator(lab).evaluate(_request(lab), _runner)
    assert result["status"] == "COMPLETED"
    assert result["primary_result"] == 0.25 and result["secondary_results"] == {"trade_count": 180}
    assert result["consumed_query_index"] == 1
    assert result["evidence_stage"] == "SEALED_LOCKED_EVALUATION"
    path = lab / "research/sealed/SYNTHETIC/results/SYNTH-QUERY-001.json"
    assert json.loads(path.read_text(encoding="utf-8")) == result


def test_duplicate_query_and_result_overwrite_are_refused(lab: Path):
    evaluator = SealedEvaluator(lab)
    evaluator.evaluate(_request(lab), _runner)
    _write_budget(lab, authorized=2, consumed=1)
    with pytest.raises(SealedEvaluationError, match="duplicate sealed query identity"):
        evaluator.evaluate(_request(lab), _runner)
    with pytest.raises(SealedEvaluationError, match="already consumed a sealed query"):
        evaluator.evaluate(_request(lab, query_id="SYNTH-QUERY-002"), _runner)


def test_exhausted_budget_is_refused(lab: Path):
    evaluator = SealedEvaluator(lab)
    evaluator.evaluate(_request(lab), _runner)
    _write_budget(lab, authorized=1, consumed=1)
    with pytest.raises(SealedAccessDenied, match="no authorized sealed query"):
        evaluator.evaluate(_request(lab, query_id="SYNTH-QUERY-003"), _runner)


def test_deleting_the_result_cannot_restore_a_consumed_query(lab: Path):
    evaluator = SealedEvaluator(lab)
    evaluator.evaluate(_request(lab), _runner)
    (lab / "research/sealed/SYNTHETIC/results/SYNTH-QUERY-001.json").unlink()
    _write_budget(lab, authorized=2, consumed=1)
    with pytest.raises(SealedEvaluationError, match="duplicate sealed query identity"):
        evaluator.evaluate(_request(lab), _runner)
    _write_budget(lab, authorized=1, consumed=1)
    with pytest.raises(SealedAccessDenied, match="no authorized sealed query"):
        evaluator.evaluate(_request(lab, query_id="SYNTH-QUERY-004"), _runner)


def test_budget_cannot_understate_its_append_only_ledger(lab: Path):
    SealedEvaluator(lab).evaluate(_request(lab), _runner)
    _write_budget(lab, authorized=2, consumed=0)
    with pytest.raises(SealedEvaluationError, match="differs from its append-only ledger"):
        load_budget(lab)


def test_failed_execution_still_consumes_and_finalizes_a_truthful_result(lab: Path):
    def broken(_request: Any) -> dict[str, Any]:
        raise RuntimeError("synthetic sealed execution failure")

    result = SealedEvaluator(lab).evaluate(_request(lab), broken)
    assert result["status"] == "EXECUTION_FAILED" and result["primary_result"] is None
    assert result["consumed_query_index"] == 1
