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
    _write_budget(root, authorized=1)
    _write_eligibility(root, classification="PROMISING_DEVELOPMENT_ONLY")
    return root


def _write_budget(root: Path, *, authorized: int, consumed: int = 0) -> None:
    (root / "research/sealed/SEALED_QUERY_BUDGET.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "SEALED_EVALUATION_V1",
                "eligibility_table": "research/sealed/SYNTHETIC_ELIGIBILITY.json",
                "isolation_policy": "APPLICATION_AND_REPOSITORY_LAYER_ONLY_NOT_OS_ENFORCED",
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
                        "authorization_record": None if authorized == 0 else "SYNTHETIC-ALLOC",
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
    assert status["version"] == "SEALED_EVALUATION_V1"
    assert scope["scope"] == "BTCUSDT_POST_CUTOFF" and scope["symbol"] == "BTCUSDT"
    assert scope["status"] == "LOCKED_NO_AUTHORIZED_QUERY"
    assert scope["authorized_queries"] == 0 and scope["consumed_queries"] == 0
    assert scope["dataset_state"] == "RESERVED_NOT_ACQUIRED"
    assert not (ROOT / "data/sealed").exists()


def test_repository_isolation_claim_is_not_overstated():
    assert load_budget()["isolation_policy"].endswith("NOT_OS_ENFORCED")


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
