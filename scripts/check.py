from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
REVIEWED = "47dd69d73768a9e3a3c92fe08eb1e7e3e8c239f5"
WP004_BASE = "2b40aa03cfc05ac7f57d269f596f1ebacdc9d356"
WP005_BASE = "3fdeffe5de59ebf3d80dcb70e26fe8dff8a28153"
WP006_BASE = "444172a359e2663887624da82254cc2185ff85e1"
WP005_BASE_SUCCESSOR = "444172a359e2663887624da82254cc2185ff85e1"
WP006_HEAD = "d92088d5ef0426bf64f34326a3224dd9aba93603"
WP007_BASE = "d92088d5ef0426bf64f34326a3224dd9aba93603"
WP007_HEAD = "762b3b77f686305b1c73f19956d0b9b16b7a9b1c"
WP008_HEAD = "ffeb73d6c0799ccfc09d0ee3b85c25d8e52364c2"
WP012_HEAD = "d88a1465560ecfe02d2eae6a924da27238fa898e"
WP013_HEAD = "e59318268099d428df0c108144aca739f5504b40"
WP014_HEAD = "478f2fcab10569f20a81136bca1b5cff6b66d601"
WP006_EXPERIMENTS = {
    "EXP-ALG-010-PULLBACK-RECOVERY-CORE": 4,
    "EXP-ALG-011-PULLBACK-RECOVERY-CONFIRM": 4,
}
PREDECESSOR = "60ab3141862da74028763e2df72ac3c88b63b5a8"
SEED = "c6c526124945aa1624118bd7ee6aef9ae5c011b2"
CUTOFF = datetime(2024, 12, 31, 23, 59, tzinfo=UTC)
EXPERIMENTS = {
    "EXP-BASE-001-BUYHOLD": 1,
    "EXP-CTRL-002-RANDOM": 32,
    "EXP-BASE-003-TREND": 3,
    "EXP-BASE-004-BREAKOUT": 3,
    "EXP-CTRL-005-TREND-DELAY-1H": 1,
    "EXP-CTRL-006-NO-TRADE": 1,
}


def run(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(
        command, cwd=cwd, check=True, shell=sys.platform == "win32" and command[0] == "npm"
    )


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def suite_hash() -> str:
    paths = sorted(
        [
            *(ROOT / "backend/app/backtest").glob("*.py"),
            ROOT / "backend/tests/test_engine.py",
            ROOT / "backend/tests/test_splitter.py",
            ROOT / "backend/tests/test_v2_corrections.py",
            ROOT / "backend/tests/test_contracts.py",
            ROOT / "research/fixtures/synthetic_execution_golden.json",
        ]
    )
    digest = hashlib.sha256()
    for path in paths:
        content = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(path.relative_to(ROOT).as_posix().encode() + b"\0" + content + b"\0")
    return digest.hexdigest()


def validate_json(path: Path, schema_path: Path) -> dict:
    payload, schema = (
        json.loads(path.read_text(encoding="utf-8")),
        json.loads(schema_path.read_text(encoding="utf-8")),
    )
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
        payload
    )
    return payload


def validate_experiments(state: dict, results: list[Path]) -> None:
    from app.research.records import validate_result
    from app.research.runner import declared_content_identity
    from app.research.runner import sha256 as runner_sha
    from app.research.wp004 import SPEC
    from app.research.wp004_validation import validate_checkpoint
    from app.research.wp006 import SPEC as WP006_SPEC
    from app.research.wp007 import SPEC as WP007_SPEC
    from app.research.wp008 import SPEC as WP008_SPEC
    from app.research.wp011 import EXPERIMENTS as WP011_EXPERIMENTS
    from app.research.wp012 import EXPERIMENTS as WP012_EXPERIMENTS
    from app.research.wp013 import EXPERIMENTS as WP013_EXPERIMENTS
    from app.research.wp014 import EXPERIMENTS as WP014_EXPERIMENTS
    from app.research.wp015 import EXPERIMENTS as WP015_EXPERIMENTS

    directories = {p.name for p in (ROOT / "research/experiments").iterdir() if p.is_dir()}
    assert directories == (
        set(EXPERIMENTS)
        | set(SPEC)
        | set(WP006_SPEC)
        | set(WP007_SPEC)
        | set(WP008_SPEC)
        | set(WP011_EXPERIMENTS.values())
        | set(WP012_EXPERIMENTS.values())
        | set(WP013_EXPERIMENTS.values())
        | set(WP014_EXPERIMENTS.values())
        | set(WP015_EXPERIMENTS.values())
    )
    assert set(WP006_SPEC) == set(WP006_EXPERIMENTS)
    assert len(results) == state["experiments_completed"] == 25
    for experiment_id, budget in EXPERIMENTS.items():
        directory = ROOT / "research/experiments" / experiment_id
        prereg_path, result_path = directory / "preregistration.json", directory / "result.json"
        prereg, result = (
            validate_json(prereg_path, ROOT / "contracts/experiment_preregistration.schema.json"),
            validate_result(result_path, prereg_path),
        )
        plan, strategy = (
            prereg["parameter_space"]["trial_plan"],
            ROOT / prereg["parameter_space"]["strategy_path"],
        )
        assert (
            prereg["trial_budget"]
            == budget
            == len(plan)
            == result["trial_accounting"]["executed_trials"]
        )
        assert (
            len({x["trial_id"] for x in plan}) == budget
            and runner_sha(strategy) == prereg["parameter_space"]["strategy_sha256"]
        )
        assert declared_content_identity(strategy, plan) == prereg["code_config_reference"]
        trials = json.loads((directory / "trials.json").read_text(encoding="utf-8"))
        assert len(trials) == budget and {x["trial_id"] for x in trials} == {
            x["trial_id"] for x in plan
        }
        pre_commit = git(
            "log", "--diff-filter=A", "--format=%H", "--", str(prereg_path.relative_to(ROOT))
        ).splitlines()[-1]
        result_commit = git(
            "log", "--diff-filter=A", "--format=%H", "--", str(result_path.relative_to(ROOT))
        ).splitlines()[-1]
        assert pre_commit != result_commit
        run(["git", "merge-base", "--is-ancestor", pre_commit, result_commit])
    for experiment_id in WP015_EXPERIMENTS.values():
        directory = ROOT / "research/experiments" / experiment_id
        prereg_path = directory / "preregistration.json"
        result_path = directory / "result.json"
        result = validate_result(result_path, prereg_path)
        assert result["trial_accounting"] == {"declared_budget": 4, "executed_trials": 4}
        assert result["secondary_results"]["independent_reconciliation"] == "PASS"
        pre_commit = git(
            "log", "--diff-filter=A", "--format=%H", "--", str(prereg_path.relative_to(ROOT))
        ).splitlines()[-1]
        result_commit = git(
            "log", "--diff-filter=A", "--format=%H", "--", str(result_path.relative_to(ROOT))
        ).splitlines()[-1]
        assert pre_commit != result_commit
        run(["git", "merge-base", "--is-ancestor", pre_commit, result_commit])
    random_trials = json.loads(
        (ROOT / "research/experiments/EXP-CTRL-002-RANDOM/trials.json").read_text()
    )
    assert len({x["seed"] for x in random_trials}) == 32
    assert (
        json.loads((ROOT / "research/experiments/EXP-CTRL-006-NO-TRADE/result.json").read_text())[
            "secondary_results"
        ]["attempted_setups"]
        == 0
    )
    assert (
        json.loads((ROOT / "reports/validation/PRE-EXPERIMENT-GATE-V1.json").read_text())["status"]
        == "PASS"
    )
    audit = validate_checkpoint()
    assert (
        state["selected_family"]["terminal_classification"]
        == audit["selected_family_terminal_classification"]
    )


def validate_research_views(state: dict) -> None:
    from app.research.adaptive import validate_adaptive
    from app.research.checkpoint_views import build_comparison, experiment_view, memory_views
    from app.research.runner import sha256 as text_sha
    from app.research.search_memory_v2 import validate_search_memory_v2
    from app.research.wp004 import SPEC, immutable_from_first_commit

    assert state["schema_version"] == 3
    from app.research.registry import all_families

    assert state["search_memory"] == {
        "version": "SEARCH_MEMORY_V2",
        "status": "VALIDATED",
        "families_tracked": len(all_families()),
    }
    from app.research.wp006_views import cumulative_accounting

    prior = validate_adaptive()
    assert prior["adaptive_decisions"] == prior["result_dependent_forks"] == 1
    assert prior["profile_trials"] == 53 and prior["configuration_variants"] == 9
    assert state["adaptive_search"] == cumulative_accounting()
    assert state["adaptive_search"]["numeric_parameter_variants"] == 0
    assert state["adaptive_search"]["sealed_queries"] == 0
    assert validate_search_memory_v2()["status"] == "PASS"
    assert state["selected_family"]["name"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    assert state["selected_family"]["primary_experiment_id"] == "EXP-ALG-009-ALIGNED"
    assert (
        state["latest_reviewed_checkpoint"] == "WP-014"
        and state["latest_executor_checkpoint"] == "WP-015"
    )
    assert state["project_phase"] == "STRATEGY_RESEARCH" and not state["owner_decision_required"]
    path = "research/memory/WP-004-LESSONS.json"
    lessons = validate_json(ROOT / path, ROOT / "contracts/research_lessons.schema.json")
    immutable_from_first_commit(path)
    assert (
        lessons["family_terminal_classification"]
        == state["selected_family"]["terminal_classification"]
    )
    assert set(lessons["experiments"]) == set(SPEC)
    for eid, item in lessons["experiments"].items():
        result_path = ROOT / f"research/experiments/{eid}/result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        assert item["result_path"] == result_path.relative_to(ROOT).as_posix()
        assert item["result_sha256"] == text_sha(result_path)
        assert (
            item["terminal_classification"]
            == result["secondary_results"]["terminal_classification"]
        )
    comparison = "reports/research/WP-004-COMPARISON.json"
    immutable_from_first_commit(comparison)
    assert json.loads((ROOT / comparison).read_text(encoding="utf-8")) == build_comparison()
    for name, content in memory_views().items():
        assert (ROOT / "research/memory" / name).read_text(encoding="utf-8") == content
    projection = experiment_view(state=state)
    assert len(projection["experiments"]) == state["experiments_completed"]
    assert projection["latest_checkpoint"] == state["latest_executor_checkpoint"]
    from app.research.wp006_validation import validate_wp006

    wp006 = validate_wp006()
    assert wp006["status"] == "PASS" and wp006["novelty_classification"] == "NEW_FAMILY"
    assert wp006["variants"] == 2 and wp006["profile_trials"] == 8
    assert wp006["numeric_parameter_variants"] == 0
    assert wp006["sealed"]["seal_eligible"] == 0
    assert {"WP-006", "WP-007"} <= set(wp006["report_base_guard"])
    comparison = "reports/research/WP-006-COMPARISON.json"
    immutable_from_first_commit(comparison)
    from app.research.wp006_views import build_wp006_comparison

    assert json.loads((ROOT / comparison).read_text(encoding="utf-8")) == json.loads(
        json.dumps(build_wp006_comparison())
    )

    from app.research.wp007_validation import validate_wp007

    wp007 = validate_wp007()
    assert wp007["status"] == "PASS"
    assert wp007["family_terminal_classification"] == "REJECT_COST_DOMINATED"
    assert wp007["sealed"] == {"assessed": 25, "eligible": 0, "queries": 0}

    from app.research.wp008_validation import validate_wp008

    wp008 = validate_wp008()
    assert wp008["status"] == "PASS"
    assert wp008["classifications"] == {
        "LINEAR_FULL": "REJECT_COST_DOMINATED",
        "LINEAR_NO_FLOW": "REJECT_COST_DOMINATED",
    }
    assert wp008["model_fits"] == 12 and wp008["profile_trials"] == 8

    wp012_comparison = json.loads(
        (ROOT / "reports/research/WP-012-COMPARISON.json").read_text(encoding="utf-8")
    )
    wp012_reconciliation = json.loads(
        (ROOT / "reports/validation/WP-012-MODEL-RECONCILIATION.json").read_text(encoding="utf-8")
    )
    assert wp012_reconciliation["status"] == "PASS"
    assert not wp012_reconciliation["mismatches"]
    assert set(wp012_reconciliation["checks"].values()) == {"PASS"}
    assert wp012_comparison["regime"] == {
        "version": "FINANCIAL_CONDITIONS_REGIME_V1",
        "series": "NFCI",
        "threshold": 0.0,
        "threshold_variants": 0,
    }
    assert wp012_comparison["conditioning_effect"]["paired"] is False
    assert {
        variant: record["terminal_classification"]
        for variant, record in wp012_comparison["configurations"].items()
    } == {
        "REGIME_TWO_EXPERTS": "REJECT_COST_DOMINATED",
        "GLOBAL_SINGLE_EXPERT_MATCHED": "REJECT_COST_DOMINATED",
    }
    wp013_comparison = json.loads(
        (ROOT / "reports/research/WP-013-COMPARISON.json").read_text(encoding="utf-8")
    )
    wp013_reconciliation = json.loads(
        (ROOT / "reports/validation/WP-013-MODEL-RECONCILIATION.json").read_text(encoding="utf-8")
    )
    assert wp013_reconciliation["status"] == "PASS"
    assert not wp013_reconciliation["mismatches"]
    assert set(wp013_reconciliation["checks"].values()) == {"PASS"}
    assert wp013_comparison["context_version"] == "NFCI_CONTEXT_V1"
    assert wp013_comparison["interaction_effect"]["eligible_universe_matched"] is True
    assert wp013_comparison["interaction_effect"]["executed_trade_sets_paired"] is False
    assert {
        variant: record["terminal_classification"]
        for variant, record in wp013_comparison["configurations"].items()
    } == {
        "NFCI_CONTEXT_INTERACTIONS": "REJECT_COST_DOMINATED",
        "INTERNAL_ONLY_MATCHED_NFCI": "REJECT_COST_DOMINATED",
    }
    wp014_comparison = json.loads(
        (ROOT / "reports/research/WP-014-COMPARISON.json").read_text(encoding="utf-8")
    )
    wp014_reconciliation = json.loads(
        (ROOT / "reports/validation/WP-014-MODEL-RECONCILIATION.json").read_text(encoding="utf-8")
    )
    assert wp014_reconciliation["status"] == "PASS"
    assert not wp014_reconciliation["mismatches"]
    assert set(wp014_reconciliation["checks"].values()) == {"PASS"}
    assert wp014_reconciliation["prediction_tolerance"] == 1e-10
    wp014_reporting_correction = json.loads(
        (ROOT / "reports/validation/WP-014-REPORTING-CORRECTION.json").read_text(encoding="utf-8")
    )
    assert wp014_reporting_correction["status"] == "PASS"
    assert wp014_reporting_correction["correction"] == (
        "OOS_CORRELATION_MATERIALITY_NOT_ESTABLISHED"
    )
    assert wp014_reporting_correction["experiment_results_changed"] is False
    assert wp014_comparison["model_version"] == "SHALLOW_INTERNAL_HGBR_V1"
    assert wp014_comparison["primary_vs_control"]["eligible_universe_matched"] is True
    assert wp014_comparison["primary_vs_control"]["executed_trade_sets_paired"] is False
    assert {
        variant: record["terminal_classification"]
        for variant, record in wp014_comparison["configurations"].items()
    } == {
        "SHALLOW_INTERNAL_HGBR": "REJECT_COST_DOMINATED",
        "INTERNAL_LINEAR_MATCHED": "REJECT_COST_DOMINATED",
    }
    wp015_comparison = json.loads(
        (ROOT / "reports/research/WP-015-COMPARISON.json").read_text(encoding="utf-8")
    )
    wp015_reconciliation = json.loads(
        (ROOT / "reports/validation/WP-015-MODEL-RECONCILIATION.json").read_text(encoding="utf-8")
    )
    assert wp015_reconciliation["status"] == "PASS"
    assert not wp015_reconciliation["mismatches"]
    assert set(wp015_reconciliation["checks"].values()) == {"PASS"}
    assert wp015_reconciliation["prediction_tolerance"] == 1e-10
    assert wp015_comparison["primary_vs_control"]["eligible_universe_matched"] is True
    assert wp015_comparison["primary_vs_control"]["executed_trade_sets_paired"] is False
    assert {
        variant: record["terminal_classification"]
        for variant, record in wp015_comparison["configurations"].items()
    } == {
        "INTERNAL_PLUS_FUNDING_HGBR": "REJECT_COST_DOMINATED",
        "INTERNAL_HGBR_MATCHED_FUNDING": "REJECT",
    }
    assert state["latest_family"] == {
        "name": "PERPETUAL_FUNDING_CONTEXT_V1",
        "root_family": "FAM-DERIVATIVES-SENTIMENT-CONTEXT",
        "primary_experiment_id": "EXP-ML-024-INTERNAL-PLUS-FUNDING-HGBR",
        "novelty_classification": "NEW_FAMILY",
        "terminal_classification": "REJECT_COST_DOMINATED",
    }
    assert state["regime_conditioned_challenger"]["research_director_verdict"] == "ACCEPTED"
    assert state["regime_conditioned_challenger"]["family_status"] == (
        "PARKED_REJECTED_NO_TUNING_AUTHORIZED"
    )
    assert state["shallow_nonlinear_challenger"] == {
        "actual_model_fits": 12,
        "control": "INTERNAL_LINEAR_MATCHED",
        "control_novelty": "DUPLICATE_MATCHED_CONTROL_REPLICATION",
        "model_reconciliation": "PASS",
        "primary": "SHALLOW_INTERNAL_HGBR",
        "reserved_model_fits": 12,
        "root_family": "FAM-SHALLOW-NONLINEAR-INTERNAL",
        "safe_phase_1_commit": "45abdbc96132f85a412a0359f60c91286af710ff",
        "sealed_eligibility": "NOT_ELIGIBLE_REJECTED",
        "sklearn_version": "1.7.2",
        "status": "VALIDATED",
        "terminal_classification": "REJECT_COST_DOMINATED",
        "version": "SHALLOW_INTERNAL_HGBR_V1",
    }
    assert state["funding_context_challenger"] == {
        "actual_model_fits": 10,
        "control": "INTERNAL_HGBR_MATCHED_FUNDING",
        "funding_records": 5819,
        "funding_source": "BINANCE_USDM_FUTURES_PUBLIC_MARKET_DATA",
        "futures_execution": False,
        "model_reconciliation": "PASS",
        "primary": "INTERNAL_PLUS_FUNDING_HGBR",
        "reserved_model_fits": 10,
        "root_family": "FAM-DERIVATIVES-SENTIMENT-CONTEXT",
        "safe_phase_1_commit": "4010c889cc8422002ec320e88d06f2a7374ea639",
        "sealed_eligibility": "NOT_ELIGIBLE_REJECTED",
        "status": "VALIDATED",
        "terminal_classification": "REJECT_COST_DOMINATED",
        "validation_folds": 5,
        "version": "PERPETUAL_FUNDING_CONTEXT_V1",
    }

    # validate_wp009 is the completed-WP-009 validator; it may only run once state
    # declares finalization. A paused WP-009 is validated by wp009_governance_checks.
    pause = state.get("exogenous_acquisition_pause")
    if pause is None or pause.get("wp009_finalized"):
        from app.research.wp009_validation import validate_wp009

        wp009 = validate_wp009(data_available=False)
        assert wp009["status"] == "PASS" and not wp009["data_replayed"]
    else:
        assert pause["status"] == "PARTIAL" and pause["wp009_finalized"] is False

    from app.research.wp005_validation import validate_wp005

    wp005 = validate_wp005(data_available=False)
    assert state["wp005_integrity"] == {
        "status": "PASS",
        "source_provenance_classification": wp005["source_provenance"],
        "independent_reconciliation": wp005["independent_reconciliation"],
        "integrity_replay_profiles": wp005["integrity_replay_profiles"],
        "matched_control_classification": wp005["classification"],
    }
    assert "remote_ci" not in state["wp005_integrity"], "stale pending CI state was reintroduced"
    remote = state["remote_ci"]["work_packages"]
    assert set(remote) == {"WP-005", "WP-006", "WP-007", "WP-008", "WP-012", "WP-013", "WP-014"}
    for work_package, expected_head in (
        ("WP-005", WP005_BASE_SUCCESSOR),
        ("WP-006", WP006_HEAD),
        ("WP-007", WP007_HEAD),
        ("WP-008", WP008_HEAD),
        ("WP-012", WP012_HEAD),
        ("WP-013", WP013_HEAD),
        ("WP-014", WP014_HEAD),
    ):
        record = remote[work_package]
        evidence = json.loads((ROOT / record["evidence"]).read_text(encoding="utf-8"))
        assert record["status"] == "SUCCESS" and record["head"] == expected_head
        assert evidence["conclusion"] == "success" and evidence["branch"] == "main"
        assert evidence["reviewed_head"] == expected_head
        assert evidence["run_id"] == record["run_id"]


def dataset_scope_checks() -> None:
    """Metadata/inventory admission also runs in a checkout with no installed market data."""
    from app.research.continuation_lab import MANIFEST_SHA256
    from app.research.runner import sha256 as text_sha

    approved = ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
    order_flow = ROOT / "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json"
    gdelt = ROOT / "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json"
    alfred = ROOT / "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json"
    funding = ROOT / "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json"
    exogenous = ROOT / "data/manifests/EXOGENOUS-CONTEXT-DEV-v1.json"
    # The GDELT and combined-context manifests only exist once WP-009 is finalized; a
    # paused WP-009 must not be asked for them, and must not carry them either.
    wp009_final = gdelt.is_file() or exogenous.is_file()
    expected = {approved, order_flow, alfred, funding}
    if wp009_final:
        expected |= {gdelt, exogenous}
    assert set((ROOT / "data/manifests").glob("*.json")) == expected
    manifest = validate_json(approved, ROOT / "contracts/dataset_manifest.schema.json")
    flow_manifest = json.loads(order_flow.read_text(encoding="utf-8"))
    assert text_sha(approved) == MANIFEST_SHA256 and manifest["symbol"] == "BTCUSDT"
    assert manifest["coverage"]["end"] == "2024-12-31T23:59:00Z"
    assert flow_manifest["derived_from"]["content_hash"] == manifest["content_hash"]["value"]
    assert flow_manifest["coverage"]["end"] <= manifest["coverage"]["end"]
    raw = {ROOT / item["path"] for item in manifest["source"]["raw_objects"]}
    assert set((ROOT / "data/raw").rglob("*.zip")) <= raw
    alfred_manifest = json.loads(alfred.read_text(encoding="utf-8"))
    funding_manifest = json.loads(funding.read_text(encoding="utf-8"))
    approved_parquet = {
        *(ROOT / item["path"] for item in manifest["files"].values()),
        *(ROOT / item["path"] for item in flow_manifest["files"].values()),
        ROOT / alfred_manifest["file"]["path"],
        ROOT / alfred_manifest["request_index"]["path"],
        ROOT / funding_manifest["canonical"]["path"],
        ROOT / funding_manifest["request_index"]["path"],
    }
    if wp009_final:
        approved_parquet |= {
            ROOT / json.loads(gdelt.read_text(encoding="utf-8"))["file"]["path"],
            ROOT / json.loads(exogenous.read_text(encoding="utf-8"))["file"]["path"],
        }
    # Research trial artifacts are approved by the committed comparison that declares and
    # hash-pins them, so every parquet under data/ still traces to a tracked manifest.
    wp011_comparison = ROOT / "reports/research/WP-011-COMPARISON.json"
    if wp011_comparison.is_file():
        approved_parquet.add(
            ROOT / json.loads(wp011_comparison.read_text(encoding="utf-8"))["artifact"]["path"]
        )
    wp012_comparison = ROOT / "reports/research/WP-012-COMPARISON.json"
    if wp012_comparison.is_file():
        approved_parquet.add(
            ROOT / json.loads(wp012_comparison.read_text(encoding="utf-8"))["artifact"]["path"]
        )
    wp013_comparison = ROOT / "reports/research/WP-013-COMPARISON.json"
    if wp013_comparison.is_file():
        approved_parquet.add(
            ROOT / json.loads(wp013_comparison.read_text(encoding="utf-8"))["artifact"]["path"]
        )
    wp014_comparison = ROOT / "reports/research/WP-014-COMPARISON.json"
    if wp014_comparison.is_file():
        approved_parquet.add(
            ROOT / json.loads(wp014_comparison.read_text(encoding="utf-8"))["artifact"]["path"]
        )
    wp015_comparison = ROOT / "reports/research/WP-015-COMPARISON.json"
    if wp015_comparison.is_file():
        record = json.loads(wp015_comparison.read_text(encoding="utf-8"))
        approved_parquet |= {
            ROOT / record["trials_artifact"]["path"],
            ROOT / record["predictions_artifact"]["path"],
        }
    assert (
        set((ROOT / "data/canonical").rglob("*.parquet"))
        | set((ROOT / "data/derived").rglob("*.parquet"))
        <= approved_parquet
    )


WP009_FINAL_ARTIFACTS = (
    "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json",
    "data/manifests/EXOGENOUS-CONTEXT-DEV-v1.json",
    "reports/validation/WP-009-GDELT-INTEGRITY.json",
    "reports/validation/WP-009-EXOGENOUS-ASOF-RECONCILIATION.json",
    "reports/research/WP-009-EXOGENOUS-COVERAGE.md",
    "reports/research/WP-009-EXOGENOUS-FOUNDATION.md",
    "reports/checkpoints/WP-009.md",
    "tasks/archive/WP-009.md",
)
WP009_PAUSED_ARTIFACTS = (
    "research/exogenous/GDELT-NEWS-CONTEXT-AMENDMENT-V1_1.json",
    "research/exogenous/GDELT-NEWS-CONTEXT-V1_1-PAUSE-V1.json",
    "reports/validation/WP-009-GDELT-DAILY-PILOT-ACQUISITION.json",
    "reports/checkpoints/WP-009-GDELT-V1_1-PAUSE.md",
)


def wp009_governance_checks(root: Path = ROOT) -> str:
    """Validate WP-009 against whatever state truthfully declares, and nothing else.

    A paused WP-009 must not be asked for artifacts a completed WP-009 would have, and a
    WP-009 that claims completion must still produce every one of them. Neither branch
    relaxes any cutoff or sealed check.
    """
    state = json.loads((root / "state/current_state.json").read_text(encoding="utf-8"))
    pause = state.get("exogenous_acquisition_pause")
    finalized = bool(pause is None or pause.get("wp009_finalized"))
    task = (root / "tasks/CURRENT_TASK.md").read_text(encoding="utf-8").replace("\r\n", "\n")

    if finalized:
        missing = [x for x in WP009_FINAL_ARTIFACTS if not (root / x).is_file()]
        assert not missing, f"WP-009 is declared finalized but these are missing: {missing}"
        assert "CURRENT TASK — WP-009" in task and "## STATUS\nCOMPLETED" in task
        assert (root / "tasks/archive/WP-009.md").read_bytes().replace(b"\r\n", b"\n") == (
            root / "tasks/CURRENT_TASK.md"
        ).read_bytes().replace(b"\r\n", b"\n")
        return "COMPLETED"

    missing = [x for x in WP009_PAUSED_ARTIFACTS if not (root / x).is_file()]
    assert not missing, f"WP-009 is declared paused but its evidence is missing: {missing}"
    assert pause["status"] == "PARTIAL"
    assert pause["pause_reason"] == "PAUSED_FOR_PRODUCT_PRIORITY"
    assert pause["wp009_finalized"] is False
    assert pause["pilot_preserved_requests"] <= pause["pilot_expected_requests"]
    record = json.loads(
        (root / "research/exogenous/GDELT-NEWS-CONTEXT-V1_1-PAUSE-V1.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["status"] == "PARTIAL" and record["wp009_finalized"] is False
    assert record["btc_prices_returns_or_outcomes_used"] is False
    # A paused WP-009 must not silently carry finalized artifacts either.
    premature = [x for x in WP009_FINAL_ARTIFACTS if (root / x).is_file()]
    assert not premature, f"WP-009 is declared paused but finalized artifacts exist: {premature}"
    if "CURRENT TASK — WP-009" in task:
        assert "## STATUS\nCOMPLETED" not in task
    return "PAUSED"


def governance_checks(pre_experiment: bool) -> dict:
    required = [
        "governance/SCIENTIFIC_CONSTITUTION.md",
        "reports/reviews/WP-002-RESEARCH-DIRECTOR-REVIEW.md",
        "decisions/ADR-0003-PRE-EXPERIMENT-SUBSTRATE-CORRECTIONS.md",
        "docs/contracts/BACKTEST_ENGINE_V2.md",
        "docs/contracts/EXECUTION_MODEL_V2.md",
        "docs/contracts/COST_MODEL_V1.md",
        "data/reports/BTCUSDT-SPOT-1M-DEV-v1-gaps.json",
        "reports/reviews/WP-003-RESEARCH-DIRECTOR-REVIEW.md",
        "reports/research/WP-004-ASTRA-ULTRA.md",
        "governance/EXECUTOR_POLICY.md",
        "reports/reviews/WP-004-RESEARCH-DIRECTOR-REVIEW.md",
        "docs/contracts/RESEARCH_SEARCH_MEMORY_V2.md",
        "reports/validation/WP-005-SOURCE-PROVENANCE.json",
        "research/protocols/WP-005-MATCHED-CONTROLS-V1.json",
        "research/diagnostics/WP-005/final-classification.json",
        "reports/validation/WP-005-CHECKPOINT.json",
        "reports/checkpoints/WP-005.md",
        "tasks/archive/WP-005.md",
        "reports/reviews/WP-005-RESEARCH-DIRECTOR-REVIEW.md",
        "reports/reviews/WP-005-CI-EVIDENCE.json",
        "governance/WORK_PACKAGE_CHRONOLOGY.json",
        "docs/contracts/SEALED_EVALUATION_V1.md",
        "contracts/sealed_evaluation_request.schema.json",
        "contracts/sealed_evaluation_result.schema.json",
        "research/sealed/SEALED_QUERY_BUDGET.json",
        "research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json",
        "decisions/ADR-0006-SEALED-EVALUATION-ARCHITECTURE.md",
        "decisions/ADR-0007-PULLBACK-RECOVERY-ROOT-AND-V2-MEMORY-LAYER.md",
        "research/design/PULLBACK_RECOVERY_V1_DESIGN.md",
        "research/memory/WP006-NOVELTY-ADMISSION.json",
        "research/memory/WP006-PULLBACK-RECOVERY-ALLOCATION.json",
        "research/memory/WP-006-LESSONS.json",
        "reports/validation/WP-006-PREEXECUTION-CORRECTION.json",
        "reports/checkpoints/WP-006.md",
        "reports/research/WP-006-PULLBACK-RECOVERY.md",
        "tasks/archive/WP-006.md",
        "reports/reviews/WP-006-RESEARCH-DIRECTOR-REVIEW.md",
        "reports/reviews/WP-006-CI-EVIDENCE.json",
        "docs/contracts/SEALED_EVALUATION_V1_1.md",
        "decisions/ADR-0008-SEALED-SCIENTIFIC-ALLOCATION-AUTHORITY.md",
        "decisions/ADR-0009-APPEND-ONLY-RESEARCH-REGISTRY.md",
        "docs/contracts/ORDER_FLOW_FEATURES_V1.md",
        "reports/validation/WP-007-ORDER-FLOW-INTEGRITY.json",
        "reports/validation/WP-007-ORDER-FLOW-RECONCILIATION.json",
        "reports/validation/WP-007-PREREGISTRATION-TOOL-CORRECTION.json",
        "reports/validation/WP-007-PREFLIGHT-CORRECTION.json",
        "research/protocols/WP-007-PREEXECUTION-AMENDMENTS.json",
        "research/memory/WP-007-LESSONS.json",
        "reports/research/WP-007-COMPARISON.json",
        "reports/research/WP-007-ORDER-FLOW.md",
        "reports/checkpoints/WP-007.md",
        "tasks/archive/WP-007.md",
        "reports/reviews/WP-007-RESEARCH-DIRECTOR-REVIEW.md",
        "reports/reviews/WP-007-CI-EVIDENCE.json",
        "docs/contracts/RESEARCH_ARTIFACT_STORAGE_V1.md",
        "docs/contracts/SUPERVISED_CHALLENGER_V1.md",
        "docs/contracts/RESEARCH_SEARCH_MEMORY_V2_MODEL_EXTENSION.md",
        "contracts/executable_model_spec_v2.schema.json",
        "research/protocols/WP-008-LINEAR-NET-R-V1.json",
        "reports/validation/WP-008-SUPERVISED-LEAKAGE-AUDIT.json",
        "reports/validation/WP-008-MODEL-RECONCILIATION.json",
        "reports/research/WP-008-LINEAR-CHALLENGER.md",
        "reports/research/WP-008-COMPARISON.json",
        "research/memory/WP-008-LESSONS.json",
        "reports/checkpoints/WP-008.md",
        "tasks/archive/WP-008.md",
        "reports/reviews/WP-008-RESEARCH-DIRECTOR-REVIEW.md",
        "reports/reviews/WP-008-CI-EVIDENCE.json",
        "docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md",
        "docs/contracts/DYNAMIC_SIGNAL_IMPORTANCE_GOVERNANCE_V1.md",
        "research/exogenous/SOURCE_CATALOG_V1.json",
        "research/exogenous/GDELT_QUERY_CATALOG_V1.json",
        "research/exogenous/ALFRED_SERIES_CATALOG_V1.json",
        "research/exogenous/GDELT-ACQUISITION-AMENDMENT-V1.json",
        "research/exogenous/ALFRED-ACQUISITION-AMENDMENT-V1.json",
        "research/exogenous/ALFRED-SINGLE-VINTAGE-FALLBACK-V1.json",
        "research/exogenous/ALFRED-SINGLE-VINTAGE-FALLBACK-CORRECTION-V1.json",
        "research/design/ADAPTIVE_MULTISIGNAL_ARCHITECTURE_OPTIONS_V1.md",
        "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json",
        "reports/validation/WP-009-ALFRED-INTEGRITY.json",
        "reports/reviews/WP-012-RESEARCH-DIRECTOR-REVIEW.md",
        "reports/reviews/WP-012-CI-EVIDENCE.json",
        "reports/validation/WP-013-NFCI-ASOF-AUDIT.json",
        "reports/validation/WP-013-MODEL-RECONCILIATION.json",
        "reports/research/WP-013-COMPARISON.json",
        "reports/research/WP-013-INTERACTION-STABILITY.json",
        "reports/checkpoints/WP-013.md",
        "reports/reviews/WP-013-RESEARCH-DIRECTOR-REVIEW.md",
        "reports/reviews/WP-013-CI-EVIDENCE.json",
        "research/protocols/WP-014-SHALLOW-INTERNAL-HGBR-V1.json",
        "reports/validation/WP-014-PREFLIGHT.json",
        "reports/validation/WP-014-MODEL-RECONCILIATION.json",
        "reports/validation/WP-014-REPORTING-CORRECTION.json",
        "reports/research/WP-014-COMPARISON.json",
        "reports/research/WP-014-NONLINEAR-DIAGNOSTICS.json",
        "reports/research/WP-014-HISTORICAL-COMPARISON.json",
        "reports/research/WP-014-SCIENTIFIC-QUESTIONS.json",
        "reports/research/WP-014-SHALLOW-NONLINEAR.md",
        "reports/checkpoints/WP-014.md",
        "tasks/archive/WP-014.md",
        "reports/reviews/WP-014-RESEARCH-DIRECTOR-REVIEW.md",
        "reports/reviews/WP-014-CI-EVIDENCE.json",
        "docs/contracts/PERPETUAL_FUNDING_CONTEXT_V1.md",
        "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json",
        "reports/validation/WP-015-FUNDING-INTEGRITY.json",
        "reports/validation/WP-015-FUNDING-ASOF-AUDIT.json",
        "research/protocols/WP-015-PERPETUAL-FUNDING-HGBR-V1.json",
        "research/protocols/WP-015-WALK-FORWARD-V1.json",
        "reports/validation/WP-015-PREFLIGHT.json",
        "reports/validation/WP-015-MODEL-RECONCILIATION.json",
        "reports/research/WP-015-COMPARISON.json",
        "reports/research/WP-015-FUNDING-DIAGNOSTICS.json",
        "reports/research/WP-015-HISTORICAL-COMPARISON.json",
        "reports/research/WP-015-SCIENTIFIC-QUESTIONS.json",
        "reports/research/WP-015-PERPETUAL-FUNDING.md",
        "reports/checkpoints/WP-015.md",
        "tasks/archive/WP-015.md",
    ]
    assert all((ROOT / x).is_file() for x in required)
    wp009_governance_checks()
    wp005_ci = json.loads(
        (ROOT / "reports/reviews/WP-005-CI-EVIDENCE.json").read_text(encoding="utf-8")
    )
    assert wp005_ci["reviewed_head"] == "444172a359e2663887624da82254cc2185ff85e1"
    assert wp005_ci["conclusion"] == "success" and wp005_ci["branch"] == "main"
    review = (ROOT / "reports/reviews/WP-005-RESEARCH-DIRECTOR-REVIEW.md").read_text(
        encoding="utf-8"
    )
    assert "ACCEPTED" in review and WP005_BASE in review and WP004_BASE in review
    baseline = subprocess.check_output(
        ["git", "show", f"{SEED}:SCIENTIFIC_CONSTITUTION.md"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    constitution = (ROOT / "governance/SCIENTIFIC_CONSTITUTION.md").read_text(encoding="utf-8")
    assert constitution.replace("\r\n", "\n") == baseline.replace("\r\n", "\n")
    assert git("branch", "--show-current") == "main" or (
        git("branch", "--show-current") == "" and os.environ.get("CLEAN_CHECKOUT") == "1"
    )
    for ancestor in (
        SEED,
        PREDECESSOR,
        REVIEWED,
        WP004_BASE,
        WP005_BASE,
        WP006_BASE,
        WP007_BASE,
        WP007_HEAD,
        WP008_HEAD,
    ):
        run(["git", "merge-base", "--is-ancestor", ancestor, "HEAD"])
    state = validate_json(
        ROOT / "state/current_state.json", ROOT / "contracts/project_state.schema.json"
    )
    assert state["development_cutoff"] == "2024-12-31T23:59:00Z"
    approved_state = json.loads(git("show", f"{WP004_BASE}:state/current_state.json"))
    assert state["development_dataset"] == approved_state["development_dataset"]
    assert state["sealed_evaluations_completed"] == state["paper_trades_completed"] == 0
    assert (
        state["champion_status"] == state["forward_evidence"] == "NONE"
        and not state["real_money_authorized"]
    )
    substrate = state["backtest_substrate"]
    assert (
        substrate["engine_version"],
        substrate["execution_model_version"],
        substrate["cost_model_version"],
    ) == ("BACKTEST_ENGINE_V2", "EXECUTION_MODEL_V2", "BTCUSDT_SPOT_COST_V1")
    assert substrate["synthetic_validation"]["suite_hash"] == suite_hash()
    sealed_budget = json.loads(
        (ROOT / "research/sealed/SEALED_QUERY_BUDGET.json").read_text(encoding="utf-8")
    )
    authorization = sealed_budget["authorization_policy"]
    sealed_scope = sealed_budget["scopes"]["BTCUSDT_POST_CUTOFF"]
    assert sealed_budget["version"] == "SEALED_EVALUATION_V1_1"
    assert authorization["accepted_issuers"] == ["RESEARCH_DIRECTOR"]
    assert set(authorization["rejected_issuers"]) == {"EXECUTOR", "AUTOMATION"}
    assert not authorization["executor_self_authorization"]
    assert not authorization["automated_self_authorization"]
    assert sealed_scope["authorized_queries"] == sealed_scope["consumed_queries"] == 0
    assert sealed_scope["dataset_state"] == "RESERVED_NOT_ACQUIRED"
    assert not list((ROOT / "research/sealed/allocations").glob("*.json"))
    results = list((ROOT / "research/experiments").glob("*/result.json"))
    if pre_experiment:
        assert state["experiments_completed"] == 0 and not results
    else:
        validate_experiments(state, results)
        validate_research_views(state)
    dataset_scope_checks()
    assert not any(
        (ROOT / p).exists()
        for p in ("backend/app/exchange", "backend/app/orders", "backend/app/credentials")
    )
    source = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "backend/app").rglob("*.py"))
    assert all(
        x not in source
        for x in ("create_order(", "api_key", "secret_key", "ccxt", "binance.client")
    )
    for name in ("optimize", "grid_search", "bayesian", "evolutionary", "hyperopt", "optuna"):
        assert name not in source, f"an optimizer entered the research code: {name}"
    assert not (ROOT / "data/sealed").exists()
    for directory in ("data/raw", "data/canonical", "data/derived"):
        for path in (ROOT / directory).rglob("*"):
            assert path.is_dir() or not any(
                f"-{year}-" in path.name for year in range(2025, 2100)
            ), f"post-cutoff market file: {path.name}"
    from app.main import app

    # Three paper actions and one owner-initiated, allowlisted local-research action are
    # the complete POST surface. Everything else stays read-only.
    explicit_actions = {
        "/api/v1/product/analysis",
        "/api/v1/product/paper-trades",
        "/api/v1/product/paper-trades/lifecycle",
        "/api/v1/research/runner/runs",
    }
    for route in app.routes:
        route_path = str(getattr(route, "path", ""))
        methods = set(getattr(route, "methods", None) or ())
        if not methods:
            continue
        assert methods <= {"GET", "HEAD", "POST"}, f"unsafe method on {route_path}"
        if "POST" in methods:
            assert route_path in explicit_actions, f"undeclared mutating route: {route_path}"
        assert not any(
            word in route_path.lower()
            for word in ("order", "balance", "account", "credential", "withdraw", "live")
        ), f"forbidden trading surface: {route_path}"
    return state


def data_checks(state: dict) -> None:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from analyze_gaps import build_artifact
    from app.data.policy import parse_utc_instant
    from app.research.source_grid import grid_audit

    schema = ROOT / "contracts/dataset_manifest.schema.json"
    path = ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
    flow_path = ROOT / "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json"
    gdelt_path = ROOT / "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json"
    alfred_path = ROOT / "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json"
    context_path = ROOT / "data/manifests/EXOGENOUS-CONTEXT-DEV-v1.json"
    assert set((ROOT / "data/manifests").glob("*.json")) == {
        path,
        flow_path,
        gdelt_path,
        alfred_path,
        context_path,
    }
    manifest = validate_json(path, schema)
    flow_manifest = json.loads(flow_path.read_text(encoding="utf-8"))
    assert manifest["symbol"] == "BTCUSDT"
    assert parse_utc_instant(manifest["coverage"]["end"]) <= CUTOFF
    assert parse_utc_instant(flow_manifest["coverage"]["end"]) <= CUTOFF
    assert (
        sha256(path) == state["development_dataset"]["manifest_sha256"]
        and manifest["content_hash"]["value"] == state["development_dataset"]["content_hash"]
    )
    raw = {ROOT / x["path"] for x in manifest["source"]["raw_objects"]}
    assert set((ROOT / "data/raw").rglob("*.zip")) == raw
    assert all(
        "BTCUSDT" in p.name and not any(f"-{y}-" in p.name for y in range(2025, 2100)) for p in raw
    )
    parquet = {
        *(ROOT / x["path"] for x in manifest["files"].values()),
        *(ROOT / x["path"] for x in flow_manifest["files"].values()),
        ROOT / json.loads(gdelt_path.read_text(encoding="utf-8"))["file"]["path"],
        ROOT / json.loads(alfred_path.read_text(encoding="utf-8"))["file"]["path"],
        ROOT / json.loads(alfred_path.read_text(encoding="utf-8"))["request_index"]["path"],
        ROOT / json.loads(context_path.read_text(encoding="utf-8"))["file"]["path"],
        ROOT
        / json.loads(
            (ROOT / "reports/research/WP-013-COMPARISON.json").read_text(encoding="utf-8")
        )["artifact"]["path"],
        ROOT
        / json.loads(
            (ROOT / "reports/research/WP-014-COMPARISON.json").read_text(encoding="utf-8")
        )["artifact"]["path"],
    }
    assert (
        set((ROOT / "data/canonical").rglob("*.parquet"))
        | set((ROOT / "data/derived").rglob("*.parquet"))
        == parquet
    )
    for record in [*manifest["source"]["raw_objects"], *manifest["files"].values()]:
        assert sha256(ROOT / record["path"]) == record["sha256"]
    for record in flow_manifest["files"].values():
        assert sha256(ROOT / record["path"]) == record["sha256"]
    for label, record in manifest["files"].items():
        table = pq.read_table(ROOT / record["path"])
        assert table.num_rows == manifest["row_counts"]["1m" if label == "canonical" else label]
        opens = pc.cast(table["open_time"], pa.int64())
        assert (
            opens[-1].as_py() <= int(CUTOFF.timestamp() * 1_000_000)
            and pc.count_distinct(opens).as_py() == table.num_rows
        )
        if label == "canonical":
            assert grid_audit(opens.to_numpy()) == json.loads(
                (ROOT / "reports/validation/WP-004-SOURCE-GRID.json").read_text()
            )
    artifact = json.loads((ROOT / "data/reports/BTCUSDT-SPOT-1M-DEV-v1-gaps.json").read_text())
    assert (
        artifact == build_artifact()
        and artifact["total_missing_minutes"] == manifest["integrity"]["missing_minutes"]
    )
    from app.research.wp005_validation import validate_wp005

    assert validate_wp005(data_available=True)["status"] == "PASS"
    from app.research.order_flow_audit import order_flow_integrity
    from app.research.order_flow_oracle import reconcile

    audit = order_flow_integrity()
    oracle = reconcile(from_disk=True)
    assert audit["status"] == "PASS" and audit["material_violations"] == 0
    assert oracle["status"] == "PASS" and oracle["content_hash_match"]
    assert flow_manifest["content_hash"]["value"] == oracle["production_content_hash"]
    from app.research.wp008_validation import validate_installed_data_reconciliation

    assert validate_installed_data_reconciliation()["status"] == "PASS"
    from app.research.wp009_validation import validate_wp009

    assert validate_wp009(data_available=True)["status"] == "PASS"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-data", action="store_true")
    parser.add_argument("--pre-experiment", action="store_true")
    options = parser.parse_args()
    state = governance_checks(options.pre_experiment)
    for command in (
        [sys.executable, "-m", "ruff", "check", "backend", "scripts"],
        [sys.executable, "-m", "ruff", "format", "--check", "backend", "scripts"],
        [sys.executable, "-m", "mypy", "backend"],
        [sys.executable, "-m", "pytest", "-q"],
    ):
        run(command)
    for command in (
        ["npm", "run", "lint"],
        ["npm", "run", "typecheck"],
        ["npm", "run", "test"],
        ["npm", "run", "build"],
    ):
        run(command, ROOT / "frontend")
    if not options.no_data:
        data_checks(state)
    assert not git("status", "--porcelain"), "working tree must be clean at checkpoint validation"
    print("WP-009 deterministic validation: PASS (information integrity, not profitability)")


if __name__ == "__main__":
    main()
