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
PAPER_RUNTIME_HEAD = "95362a1a24adde6b4e5a75eb2062c52dcc4fdb6d"
P01_VERIFIED_HEAD = "292f3eb468e388a8844ed7431a24e4a446162e8c"
P1A_VERIFIED_HEAD = "8d3286a29093e542ed2fdeff5c457666dca5ea66"
P2_VERIFIED_HEAD = "15fd9361a16c78781650b8b5a1ecce7527200bb4"
P2_CLOSURE_HEAD = "334b76670cb7ef06f1e6a960c1aae67ce79eaae5"
CROSS_SECTION_HEAD = "922fb11100bce442a25435d8b661fe4380acf955"
GATE_INTENSITY_HEAD = "f67830859d5c1de0c11986796074ffed898dd400"
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
    from app.research.wp016 import EXPERIMENTS as WP016_EXPERIMENTS
    from app.research.wp017 import EXPERIMENTS as WP017_EXPERIMENTS

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
        | set(WP016_EXPERIMENTS.values())
        | set(WP017_EXPERIMENTS.values())
    )
    assert set(WP006_SPEC) == set(WP006_EXPERIMENTS)
    assert len(results) == state["experiments_completed"] == 26
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
    for experiment_id in WP016_EXPERIMENTS.values():
        directory = ROOT / "research/experiments" / experiment_id
        prereg_path = directory / "preregistration.json"
        validate_json(prereg_path, ROOT / "contracts/experiment_preregistration.schema.json")
        assert not (directory / "result.json").exists()
        assert not (directory / "trials.json").exists()
    wp017_primary = (
        ROOT / "research/experiments" / WP017_EXPERIMENTS["INTERNAL_PLUS_CFTC_LEVERAGED_NET_HGBR"]
    )
    wp017_control = ROOT / "research/experiments" / WP017_EXPERIMENTS["INTERNAL_HGBR_MATCHED_CFTC"]
    wp017_result = validate_result(
        wp017_primary / "result.json", wp017_primary / "preregistration.json"
    )
    assert wp017_result["secondary_results"]["annual_folds"]["terminal_classification"] == (
        "REJECT"
    )
    assert wp017_result["secondary_results"]["independent_reconciliation"]["status"] == "PASS"
    assert wp017_result["secondary_results"]["annual_folds"]["trade_count"] == 1030
    assert (wp017_primary / "trials.parquet").exists()
    assert not (wp017_control / "result.json").exists()
    assert not (wp017_control / "trials.json").exists()
    # WP-017 preregistration must be an ancestor of HEAD and precede runner exposure.
    for experiment_id in WP017_EXPERIMENTS.values():
        relative = f"research/experiments/{experiment_id}/preregistration.json"
        prereg_commit = git("log", "--diff-filter=A", "--format=%H", "--", relative).splitlines()[
            -1
        ]
        exposure_commit = git(
            "log",
            "-S",
            "WP017_CFTC_LEVERAGED_POSITIONING_V1",
            "--format=%H",
            "--",
            "backend/app/research/local_runner.py",
        ).splitlines()[-1]
        assert prereg_commit != exposure_commit
        run(["git", "merge-base", "--is-ancestor", prereg_commit, exposure_commit])
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
    assert state["latest_reviewed_checkpoint"] == ("CROSS-SECTION-SPARSE-POWER-BLOCK-REVIEW")
    assert state["latest_executor_checkpoint"] == (
        "GATE-INTENSITY-CAUSAL-CORRECTION-POWER-RESUME-V1_1"
    )
    assert state["project_phase"] == "STRATEGY_RESEARCH" and not state["owner_decision_required"]
    from app.research.local_runner import research_candidate_registry
    from app.research.wp016 import EXPERIMENTS as WP016_EXPERIMENTS
    from app.research.wp016 import preflight as wp016_preflight
    from app.research.wp017 import EXPERIMENTS as WP017_EXPERIMENTS

    wp016 = wp016_preflight()
    assert wp016["status"] == "PASS"
    assert wp016["market_results_observed"] == wp016["model_fits_executed"] == 0
    assert not any(
        (ROOT / f"research/experiments/{experiment}/result.json").exists()
        for experiment in WP016_EXPERIMENTS.values()
    )
    wp017 = json.loads((ROOT / "reports/validation/WP-017-PREFLIGHT.json").read_text())
    assert wp017["status"] == "PASS"
    assert wp017["market_results_observed"] == wp017["model_fits_executed"] == 0
    assert wp017["post_cutoff_access"] == wp017["sealed_queries"] == 0
    assert wp017["new_feature_count"] == 1
    assert wp017["only_new_feature"] == "CFTC_LEVERAGED_FUNDS_NET_OI_SHARE_V1"
    assert wp017["runtime_version"] == "RESEARCH_RUNTIME_V2_BATCH"
    assert wp017["matched_eligible_universe"] is True
    assert wp017["report_date_used_as_availability"] is False
    assert wp017["cftc_excluded_publication_date_unresolved"] == 0
    assert wp017["cftc_excluded_availability_after_cutoff"] == 1
    assert wp017["cftc_last_availability_timestamp"] <= state["development_cutoff"]
    assert (
        ROOT
        / f"research/experiments/{WP017_EXPERIMENTS['INTERNAL_PLUS_CFTC_LEVERAGED_NET_HGBR']}/result.json"
    ).exists()
    assert not (
        ROOT / f"research/experiments/{WP017_EXPERIMENTS['INTERNAL_HGBR_MATCHED_CFTC']}/result.json"
    ).exists()
    registry = research_candidate_registry()
    candidates = registry.public_records(ROOT)
    assert [item["candidate_id"] for item in candidates] == [
        "WP017_CFTC_LEVERAGED_POSITIONING_V1",
        "WP016_WIKIPEDIA_ATTENTION_V1",
        "WP015_REPRODUCTION_V1",
    ]
    assert state["research_runner"]["candidate_ids"] == [
        item["candidate_id"] for item in candidates
    ]
    assert candidates[0]["status"] == "REVIEWED_REJECTED"
    assert candidates[0]["runnable"] is False
    assert candidates[0]["runtime_version"] == "RESEARCH_RUNTIME_V2_BATCH"
    assert candidates[0]["preregistration_frozen"] is True
    assert candidates[0]["execution_counts_as_new_evidence"] is True
    assert candidates[1]["status"] == "BLOCKED_BEFORE_EXECUTION"
    assert candidates[1]["runnable"] is False and candidates[2]["runnable"] is True
    assert candidates[1]["runtime_version"] == "WP016_PREREGISTERED_RUNTIME_V1"
    assert candidates[2]["runtime_version"] == "WP015_FROZEN_RUNTIME_V1"
    runtime = state["research_runtime"]
    assert runtime["version"] == "RESEARCH_RUNTIME_V2_BATCH"
    assert runtime["batch_prediction_validation"] == "PASS_SYNTHETIC_AND_GOVERNED_WP015"
    assert runtime["wp017_runtime"] == "RESEARCH_RUNTIME_V2_BATCH"
    assert runtime["wp017_status"] == "REVIEWED_REJECTED"
    challenger = state["cftc_positioning_challenger"]
    assert challenger["status"] == "VALIDATED_REVIEWED_REJECTED"
    assert challenger["actual_model_fits"] == challenger["reserved_model_fits"] == 10
    assert challenger["market_results_observed"] is True
    assert challenger["terminal_classification"] == "REJECT"
    assert challenger["run_id"] == "f475f7a2ef4b4ed693b5f86aa56d4b38"
    assert challenger["new_feature_count"] == 1
    assert runtime["max_prediction_difference"] == runtime["signal_mismatches"] == 0
    assert runtime["trade_identities_identical"] and runtime["metrics_identical"]
    assert not runtime["cache_implemented"] and not runtime["whole_experiment_speedup_measured"]
    assert state["attention_context_challenger"]["actual_model_fits"] == 0
    assert state["attention_context_challenger"]["market_results_observed"] is False
    assert state["attention_context_challenger"]["status"] == (
        "BLOCKED_POINT_IN_TIME_VINTAGE_UNPROVEN"
    )
    assert state["champion_status"] == "NONE"
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["real_money_authorized"] is False
    assert state["next_recommended_work_package"] == (
        "RESEARCH-DIRECTOR-REVIEW-ALIGNED-DEVELOPMENT-PARK"
    )
    assert state["owner_economic_policy"] == {
        "annual_net_excess_return_mesi_percentage_points": 5,
        "buy_and_hold_role": "SECONDARY_PRODUCT_BENCHMARK",
        "policy": "governance/ECONOMIC_SIGNIFICANCE_POLICY_V1.json",
        "primary_benchmark_family": "MATCHED_CONTROL",
        "real_money_authorized": False,
        "reference_capital_eur": 5000,
    }
    assert state["statistical_governance"]["known_discovery_family_size"] == 12
    assert state["statistical_governance"]["unquantified_pre_repo_exposure"] is True
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
    assert wp007["sealed"] == {"assessed": 26, "eligible": 0, "queries": 0}

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
        "name": "CFTC_LEVERAGED_POSITIONING_CONTEXT_V1",
        "root_family": "FAM-CFTC-REGULATED-FUTURES-POSITIONING",
        "primary_experiment_id": "EXP-ML-028-INTERNAL-PLUS-CFTC-LEVERAGED-NET-HGBR",
        "novelty_classification": "NEW_FAMILY",
        "terminal_classification": "REJECT",
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
    assert set(remote) == {
        "WP-005",
        "WP-006",
        "WP-007",
        "WP-008",
        "WP-012",
        "WP-013",
        "WP-014",
        "PAPER-ENTRY-V2-RESEARCH-RUNTIME-V2",
        "P0.1-DETECTABILITY-INFERENCE-AND-CI-PORTABILITY-FIX",
        "P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-PREP",
        "P2-CYCLE-FOUNDATION-POWER-GATE-PREP",
        "P2-METHODOLOGY-BLOCK-CLOSURE",
        "CROSS-SECTION-FEASIBILITY-AND-POWER-DESIGN-V1",
        "CROSS-SECTION-SPARSE-HYPOTHESIS-CLOSURE-ALIGNED-GATE-INTENSITY-POWER-GATE-V1",
    }
    for work_package, expected_head in (
        ("WP-005", WP005_BASE_SUCCESSOR),
        ("WP-006", WP006_HEAD),
        ("WP-007", WP007_HEAD),
        ("WP-008", WP008_HEAD),
        ("WP-012", WP012_HEAD),
        ("WP-013", WP013_HEAD),
        ("WP-014", WP014_HEAD),
        ("PAPER-ENTRY-V2-RESEARCH-RUNTIME-V2", PAPER_RUNTIME_HEAD),
        ("P0.1-DETECTABILITY-INFERENCE-AND-CI-PORTABILITY-FIX", P01_VERIFIED_HEAD),
        ("P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-PREP", P1A_VERIFIED_HEAD),
        ("P2-CYCLE-FOUNDATION-POWER-GATE-PREP", P2_VERIFIED_HEAD),
        ("P2-METHODOLOGY-BLOCK-CLOSURE", P2_CLOSURE_HEAD),
        ("CROSS-SECTION-FEASIBILITY-AND-POWER-DESIGN-V1", CROSS_SECTION_HEAD),
        (
            "CROSS-SECTION-SPARSE-HYPOTHESIS-CLOSURE-ALIGNED-GATE-INTENSITY-POWER-GATE-V1",
            GATE_INTENSITY_HEAD,
        ),
    ):
        record = remote[work_package]
        evidence = json.loads((ROOT / record["evidence"]).read_text(encoding="utf-8"))
        assert record["status"] == "SUCCESS" and record["head"] == expected_head
        assert evidence["conclusion"] == "success" and evidence["branch"] == "main"
        assert evidence["reviewed_head"] == expected_head
        assert evidence["run_id"] == record["run_id"]


def p2_power_gate_checks(state: dict, protocol: dict) -> None:
    """The P2 preparation may never carry, or authorize, an actual BTCUSDT cycle outcome."""
    from app.research.cycle_structure import (
        BLOCK_EXPECTED_OBSERVATIONS,
        CALIBRATION_PERIOD_DAYS,
        SNR_GRID,
        assert_no_result_leakage,
        fidelity_criteria,
    )
    from app.research.cycle_structure_lab import preregistration_sha256

    record = state["cycle_power_gate"]
    gate = json.loads((ROOT / record["report_json"]).read_text(encoding="utf-8"))
    fidelity = json.loads((ROOT / record["null_fidelity_report"]).read_text(encoding="utf-8"))
    benchmark = json.loads((ROOT / record["compute_benchmark"]).read_text(encoding="utf-8"))
    preregistered = json.loads(
        (ROOT / record["null_fidelity_preregistration"]).read_text(encoding="utf-8")
    )
    for artifact in (gate, fidelity, benchmark, preregistered):
        assert_no_result_leakage(artifact)
        assert artifact["ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED"] is False

    # Thresholds were fixed before measurement and the fidelity report is bound to them.
    assert preregistered["criteria"] == fidelity_criteria()
    assert preregistered["block_expected_observations"] == BLOCK_EXPECTED_OBSERVATIONS == 42
    assert preregistered["block_length_may_be_tuned_after_observation"] is False
    assert fidelity["preregistration"]["artifact_sha256"] == preregistration_sha256(ROOT)
    assert fidelity["preregistration"]["thresholds_fixed_before_calculation"] is True
    assert fidelity["training_only"] and not fidelity["validation_results_used"]
    assert fidelity["block_length_tuned_after_observation"] is False
    assert fidelity["ar_order_uses_training_only"] is True
    assert all(0 <= order <= 42 for order in fidelity["ar_order_by_fold"].values())

    # The frozen design is intact and the frozen budget was never reduced.
    design = gate["frozen_design"]
    assert design["representation"] == "CONTIGUOUS_4H_CLOSE_TO_CLOSE_LOG_RETURN"
    assert design["period_band_days"] == [2.0, 90.0]
    assert design["spectral_estimator"] == "FLOATING_MEAN_GENERALIZED_LOMB_SCARGLE"
    assert design["primary_structural_hypotheses"] == 1
    assert design["maximum_diagnostics"] == 2 and design["diagnostics_non_rescuing"]
    assert design["validation_frequency_search"] is False
    assert design["embargo_days"] == 90 and design["economic_mesi"] is None
    assert not design["economic_trading_logic"] and not design["period_band_changed"]
    assert not design["representation_added"] and not design["estimator_added"]
    assert not design["structural_primary_added"] and not design["diagnostic_added"]
    assert gate["null_replicates"] == 4999 and gate["synthetic_replicates_per_cell"] == 2000
    assert gate["calibration_period_days"] == list(CALIBRATION_PERIOD_DAYS)
    assert gate["snr_grid"] == list(SNR_GRID) and gate["phase_grid_count"] == 16
    assert gate["target_power"] == 0.8 and gate["gate_snr"] == 0.5
    joint = benchmark["joint_replication"]
    assert joint["folds_simulated_independently"] is False
    assert joint["checks"]["fold_nulls_concatenated_from_independent_draws"] is False
    assert joint["checks"]["single_path_per_replicate"] is True
    assert joint["cross_fold_dependence_handling"] and joint["shared_history_handling"]
    compute = benchmark["compute"]
    assert not compute["replicates_reduced"] and not compute["grid_coarsened"]
    assert not compute["periods_reduced"] and not compute["phases_reduced"]
    assert not compute["null_changed"] and not compute["approximation_for_speed"]

    # State, protocol and artifacts agree, and nothing authorizes execution.
    assert record["null_fidelity_status"] == fidelity["NULL_FIDELITY_STATUS"]
    assert record["joint_replication_status"] == joint["JOINT_REPLICATION_STATUS"]
    assert record["computational_status"] == compute["COMPUTATIONAL_STATUS"]
    assert record["power_gate_status"] == gate["P2_POWER_GATE_STATUS"]
    assert record["null_fidelity_material_failures"] == fidelity["material_failure_count"]
    assert record["ar_order_by_fold"] == fidelity["ar_order_by_fold"]
    assert record["detectability_executed"] == (gate["detectability"] is not None)
    assert protocol["power_gate"]["P2_POWER_GATE_STATUS"] == gate["P2_POWER_GATE_STATUS"]
    assert protocol["power_gate"]["NULL_FIDELITY_STATUS"] == fidelity["NULL_FIDELITY_STATUS"]
    assert protocol["detectability"]["status"] != "RUN"
    if record["power_gate_status"] != "READY_FOR_PREREGISTRATION":
        assert not record["detectability_executed"] and gate["detectability"] is None
        assert not (ROOT / "reports/power/P2-CYCLE-DETECTABILITY-V1.json").is_file()
    assert record["preregistration_authorized"] is False
    assert record["material_experiment_executed"] is False
    assert record["actual_market_primary_result_observed"] is False
    assert gate["preregistration_authorized"] is False
    assert gate["actual_execution_authorized"] is False
    assert all(value is False for value in gate["leakage_guard"].values())
    assert gate["safety"] == {
        "experiments_completed": 26,
        "observed_material_economic_hypotheses": 12,
        "sealed_queries": 0,
        "champion_status": "NONE",
        "real_money_authorized": False,
    }


def p2_null_v2_checks(state: dict) -> None:
    """Null V2 stopped at support without exposing or classifying the P2 market result."""
    from app.research.cycle_structure import assert_no_result_leakage, fidelity_criteria
    from app.research.cycle_structure_v2 import (
        BLOCK_EXPECTED_OBSERVATIONS_V2,
        JOINT_REPLICATION_METHOD_V2,
        MINIMUM_LAG_540_SURVIVAL,
        NULL_METHOD_V2,
    )
    from app.research.cycle_structure_v2_lab import normalized_sha256

    record = state["cycle_null_v2"]
    preregistration = json.loads((ROOT / record["preregistration"]).read_text(encoding="utf-8"))
    support = json.loads((ROOT / record["block_support_report"]).read_text(encoding="utf-8"))
    gate = json.loads((ROOT / record["power_gate_report"]).read_text(encoding="utf-8"))
    protocol = json.loads(
        (ROOT / "research/protocols/P2-CYCLE-NULL-V2.json").read_text(encoding="utf-8")
    )
    for artifact in (preregistration, support, gate):
        assert_no_result_leakage(artifact)
        assert artifact["ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED"] is False

    v1 = ROOT / "reports/power/P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1.json"
    assert preregistration["criteria"] == fidelity_criteria()
    assert preregistration["immutable_v1_criterion_artifact"]["sha256"] == normalized_sha256(v1)
    assert preregistration["thresholds_unchanged_from_v1"] is True
    assert preregistration["expected_block_observations"] == BLOCK_EXPECTED_OBSERVATIONS_V2 == 1080
    assert preregistration["alternative_block_lengths_tested"] is False
    assert preregistration["ar_garch_har_figarch_used"] is False
    assert preregistration["joint_replication_method"] == JOINT_REPLICATION_METHOD_V2
    assert preregistration["fidelity_replicates"] == 999
    assert preregistration["null_replicates"] == 4999
    assert preregistration["synthetic_replicates_per_cell"] == 2000

    assert support["null_method"] == record["null_method"] == NULL_METHOD_V2
    assert support["support_measured_before_fidelity"] is True
    assert support["fidelity_executed_at_measurement_time"] is False
    assert support["forced_gap_termination"] is True
    assert support["canonical_gaps_interpolated"] is False
    assert support["donor_blocks_cross_canonical_gaps"] is False
    assert support["alternative_block_lengths_tested"] is False
    assert support["minimum_lag540_survival_every_fold"] == MINIMUM_LAG_540_SURVIVAL
    assert len(support["folds"]) == 6
    assert all(item["lag540_pass"] is False for item in support["folds"])
    assert all(
        item["same_block_survival_probability"]["540"] < MINIMUM_LAG_540_SURVIVAL
        for item in support["folds"]
    )
    assert support["BLOCK_SUPPORT_STATUS"] == "REDESIGN_REQUIRED"

    assert (
        record["block_support_status"]
        == gate["prerequisite_gates"]["BLOCK_SUPPORT_STATUS"]
        == "REDESIGN_REQUIRED"
    )
    assert record["null_fidelity_status"] == "NOT_RUN_BLOCKED"
    assert record["joint_replication_status"] == "NOT_RUN_BLOCKED"
    assert record["computational_status"] == "NOT_RUN_BLOCKED"
    assert record["detectability_executed"] is False
    assert record["fidelity_report_created"] is False
    assert gate["detectability"] is None and gate["prerequisites_pass"] is False
    assert gate["P2_POWER_GATE_STATUS"] == record["power_gate_status"] == "REDESIGN_REQUIRED"
    assert gate["preregistration_authorized"] is False
    assert gate["actual_execution_authorized"] is False
    assert all(value is False for value in gate["leakage_guard"].values())
    assert protocol["structural_primary"]["status"] == "DESIGNED_NOT_PREREGISTERED_NOT_EXECUTED"
    assert protocol["structural_primary"]["actual_market_result_inspected"] is False
    assert protocol["null_v1"]["status"] == "FAILED_FIDELITY_REJECTED_FOR_INFERENCE"
    assert protocol["null_v1"]["structural_primary_classified"] is False
    assert not any(
        (ROOT / path).is_file()
        for path in (
            "reports/power/P2-CYCLE-NULL-V2-FIDELITY.json",
            "reports/power/P2-CYCLE-NULL-V2-COMPUTE.json",
            "reports/power/P2-CYCLE-NULL-V2-DETECTABILITY.json",
        )
    )


def p2_closure_checks(state: dict) -> None:
    """P2 closed without a market result, and the successor is a design checkpoint only."""
    closure = state["cycle_family_closure"]
    architecture = state["research_architecture"]
    review = (ROOT / closure["review"]).read_text(encoding="utf-8")
    synthesis = (ROOT / architecture["document"]).read_text(encoding="utf-8")

    # The actual BTC cycle result was never observed, so P2 is blocked, not classified.
    assert closure["hypothesis_status"] == "METHODOLOGY_BLOCKED_NOT_EXECUTED"
    assert closure["hypothesis_status"] not in {
        "REJECT",
        "NOT_SUPPORTED",
        "INCONCLUSIVE",
        "INCONCLUSIVE_MARKET_EVIDENCE",
        "SUPPORTED",
    }
    assert closure["actual_market_result_observed"] is False
    assert state["cycle_foundation"]["actual_market_result_inspected"] is False
    assert state["cycle_power_gate"]["actual_market_primary_result_observed"] is False
    assert state["cycle_null_v2"]["actual_market_primary_result_observed"] is False
    assert closure["material_economic_hypotheses_executed"] == 0
    assert "METHODOLOGY_BLOCKED_NOT_EXECUTED" in review
    assert "did **not** observe the actual BTC cycle primary result" in review

    # Both nulls stay rejected for inference and no third null exists anywhere.
    assert closure["null_v1_disposition"] == "FAILED_FIDELITY_REJECTED_FOR_INFERENCE"
    assert closure["null_v2_disposition"] == "FAILED_BLOCK_SUPPORT_REJECTED_FOR_INFERENCE"
    assert closure["null_v3_authorized"] is False
    assert closure["alternate_design_authorized"] is False
    for directory, pattern in (
        ("reports/power", "*NULL-V3*"),
        ("research/protocols", "*NULL-V3*"),
        ("research/design", "*NULL_V3*"),
        ("backend/app/research", "cycle_structure_v3*.py"),
    ):
        assert not list((ROOT / directory).glob(pattern)), f"a Null V3 artifact appeared: {pattern}"

    # The cycle family is parked and hands over to a design-only successor checkpoint.
    assert closure["family_status"] == "PARKED_METHODOLOGY_BLOCKED"
    assert architecture["cycle_research"] == "PARKED_METHODOLOGY_BLOCKED"
    assert state["cycle_foundation"]["next_checkpoint"] == (
        "NONE_CYCLE_FAMILY_PARKED_METHODOLOGY_BLOCKED"
    )
    assert architecture["primary_next_direction"] == "CROSS_SECTIONAL_FEASIBILITY_AND_POWER_DESIGN"
    assert architecture["secondary_parallel_direction"] == "PROSPECTIVE_PAPER_EVIDENCE_CONTINUES"
    assert architecture["btc_only_new_source_or_model_search"] == "DEPRIORITIZED"
    assert architecture["next_checkpoint"] == "CROSS-SECTION-FEASIBILITY-AND-POWER-DESIGN-V1"
    # The declared successor is honoured either by still being next, or by having run.
    successor = architecture["next_checkpoint"]
    assert (
        state["next_recommended_work_package"] == successor
        or (ROOT / f"reports/checkpoints/{successor}.md").is_file()
    )
    assert "CROSS_SECTIONAL_FEASIBILITY_AND_POWER_DESIGN" in synthesis
    assert len(architecture["evaluated_directions"]) == 3

    # The product is unchanged and no cross-sectional outcome exists.
    assert architecture["product_universe"] == "BTCUSDT_SPOT_V1_UNCHANGED"
    assert state["symbols"] == ["BTCUSDT"] and state["research_market"] == "crypto_spot"
    assert state["product_analysis"]["strategy_version"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    assert state["paper_trading"]["strategy_version"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    assert architecture["paper_strategy_semantics_changed"] is False
    assert architecture["cross_section_product_authorized"] is False
    assert architecture["cross_section_market_result_observed"] is False
    assert architecture["cross_section_universe_numerically_frozen"] is False
    # A cross-sectional *design* may exist; a cross-sectional market outcome may not.
    assert not list((ROOT / "research/experiments").glob("*CROSS-SECTION*"))
    gate = ROOT / "reports/power/CROSS-SECTION-POWER-GATE-V1.json"
    if gate.is_file():
        payload = json.loads(gate.read_text(encoding="utf-8"))
        assert payload["ACTUAL_CROSS_SECTION_EFFECT_OBSERVED"] is False
        assert payload["preregistration_authorized"] is False
        assert payload["actual_execution_authorized"] is False
        assert payload["safety"]["cross_section_product_authorized"] is False

    # Accounting is untouched by a formally recorded review.
    assert state["experiments_completed"] == 26
    assert state["statistical_governance"]["known_discovery_family_size"] == 12
    assert state["adaptive_search"]["adaptive_decisions"] == 16
    assert state["adaptive_search"]["result_dependent_forks"] == 13
    assert state["adaptive_search"]["sealed_queries"] == 0
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["champion_status"] == "NONE"
    assert state["paper_trading"]["genuine_paper_trades_completed"] == 0
    assert state["real_money_authorized"] is False
    assert state["paper_trading"]["real_money"] is False


def cross_section_raw_objects(manifest: dict) -> set[Path]:
    """Every preserved cross-sectional monthly object, derived from the compact schema."""
    rule = manifest["object_path_rule"]
    assert rule == "data/raw/cross_section/<symbol>/<symbol>-1h-<month>.zip"
    rows = [*manifest["objects"], *manifest["equivalence_warmup_objects"]]
    return {
        ROOT / f"data/raw/cross_section/{symbol}/{symbol}-1h-{month}.zip"
        for symbol, month, *_ in rows
    }


def cross_section_checks(state: dict) -> None:
    """The cross-sectional preparation stays a design study with no real effect exposed."""
    from app.research.cross_section import (
        CROSS_SECTION_MESI_BPS,
        EFFECTIVE_ALPHA,
        LEVERAGED_TOKEN_SUFFIXES,
        LIQUIDITY_LOOKBACK_DAYS,
        MINIMUM_ASSET_CLUSTERS,
        MINIMUM_HISTORY_DAYS,
        MINIMUM_MEDIAN_DAILY_QUOTE_VOLUME_USDT,
        MINIMUM_WEEK_CLUSTERS,
        OUTCOME_HORIZON_HOURS,
        PROSPECTIVE_FAMILY_SIZE,
        QUOTE_ASSET,
        TARGET_POWER,
        assert_no_real_effect_leakage,
        is_candidate_symbol,
        is_leveraged_token,
        mesi_bps,
    )
    from app.research.cross_section_power import PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS

    record = state["cross_section_feasibility"]
    protocol = json.loads(
        (ROOT / "research/protocols/CROSS-SECTION-FEASIBILITY-AND-POWER-V1.json").read_text(
            encoding="utf-8"
        )
    )
    gate = json.loads((ROOT / record["power_gate_report"]).read_text(encoding="utf-8"))
    placebo = json.loads((ROOT / record["placebo_report"]).read_text(encoding="utf-8"))
    signals = json.loads((ROOT / record["signal_support_report"]).read_text(encoding="utf-8"))
    feasibility = json.loads((ROOT / record["universe_report"]).read_text(encoding="utf-8"))
    survivorship = json.loads((ROOT / record["survivorship_report"]).read_text(encoding="utf-8"))
    equivalence = json.loads((ROOT / record["equivalence_report"]).read_text(encoding="utf-8"))
    inventory = json.loads((ROOT / record["inventory_report"]).read_text(encoding="utf-8"))
    artifacts = (gate, placebo, signals, feasibility, survivorship, equivalence, inventory)
    for artifact in artifacts:
        assert_no_real_effect_leakage(artifact)
        assert artifact["ACTUAL_CROSS_SECTION_EFFECT_OBSERVED"] is False

    # The true alignment is unreachable: no artifact may carry a real pooled effect.
    assert gate["leakage_guard"] == {
        "zero_alignment_pooled_effect_computed": False,
        "zero_alignment_t_computed": False,
        "zero_alignment_p_computed": False,
        "per_asset_real_effect_computed": False,
        "cross_section_trading_verdict_emitted": False,
        "sealed_data_queried": False,
        "post_cutoff_data_used": False,
    }
    assert signals["zero_alignment_outcome_inspected"] is False
    assert record["zero_alignment_effect_observed"] is False
    assert record["material_economic_hypotheses_executed"] == 0

    # Universe policy: archive-derived, USDT only, mechanical leveraged exclusion.
    assert QUOTE_ASSET == "USDT" and LEVERAGED_TOKEN_SUFFIXES == ("UP", "DOWN", "BULL", "BEAR")
    assert is_leveraged_token("BTCUPUSDT") and is_leveraged_token("ETHBEARUSDT")
    assert not is_leveraged_token("BTCUSDT") and not is_candidate_symbol("BTCUPUSDT")
    assert not is_candidate_symbol("ETHBTC") and is_candidate_symbol("ETHUSDT")
    assert protocol["universe_policy"]["derivation"] == (
        "HISTORICAL_ARCHIVE_EVIDENCE_NOT_CURRENT_EXCHANGE_INFO"
    )
    assert protocol["universe_policy"]["survival_to_2024_required"] is False
    assert protocol["universe_policy"]["frozen_before_signal_counts"] is True
    assert protocol["universe_policy"]["discretionary_asset_list"] is False
    assert protocol["universe_policy"]["stablecoin_or_fiat_pairs_manually_removed"] is False
    assert protocol["data_source"]["current_exchange_info_used_as_listing_truth"] is False
    assert protocol["data_source"]["one_minute_multi_asset_history_downloaded"] is False
    assert feasibility["universe_derivation"] == (
        "HISTORICAL_ARCHIVE_EVIDENCE_NOT_CURRENT_EXCHANGE_INFO"
    )
    assert feasibility["universe_policy_frozen_before_signal_counts"] is True
    assert survivorship["universe_is_current_survivor_list"] is False
    assert survivorship["delisted_or_archive_end_assets_retained"] is True
    assert survivorship["eligible_assets_whose_archive_ends_before_2024_12"] > 0
    assert survivorship["post_2024_information_used_for_inclusion"] is False
    assert survivorship["assets_entering_only_after_history_exists"] is True

    # Causal eligibility uses trailing information only and never interpolates.
    assert (MINIMUM_HISTORY_DAYS, LIQUIDITY_LOOKBACK_DAYS) == (30, 30)
    assert MINIMUM_MEDIAN_DAILY_QUOTE_VOLUME_USDT == 10_000_000.0
    assert feasibility["eligibility"]["trailing_information_only"] is True
    assert feasibility["eligibility"]["future_survival_required"] is False
    assert feasibility["eligibility"]["canonical_gaps_interpolated"] is False
    assert protocol["causal_eligibility"]["complete_day_required_for_liquidity_median"] is True

    # The frozen ALIGNED transfer is unmodified and raw events are never suppressed.
    assert signals["aligned_modified"] is False and signals["events"] == "RAW_SIGNAL_EVENTS"
    assert signals["occupancy_suppression_applied"] is False
    assert protocol["aligned_transfer"]["strategy_version"] == (
        "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    )
    assert protocol["aligned_transfer"]["breakout_hours"] == 24
    assert protocol["aligned_transfer"]["context_bars"] == 43
    assert protocol["aligned_transfer"]["context_increments"] == 42
    assert protocol["aligned_transfer"]["up_to_down_ratio"] == 2
    assert protocol["aligned_transfer"]["volume_multiplier"] == 2
    assert protocol["aligned_transfer"]["asset_specific_tuning"] is False
    assert all(item["equivalent"] for item in signals["vectorized_engine_equivalence"])
    assert equivalence["DATA_SOURCE_STATUS"] == "PASS"
    assert equivalence["aligned_decisions_match"] is True
    assert equivalence["identical_decisions"] == equivalence["both_decidable"]
    assert equivalence["canonical_aligned_signals"] == equivalence["archive_aligned_signals"]

    # Exactly one pooled primary, evaluated only in the future and never per asset.
    assert protocol["primary_estimand"]["count"] == gate["frozen_design"]["primary_count"] == 1
    assert gate["frozen_design"]["fixed_effects"] == ["ASSET", "DECISION_TIME"]
    assert gate["frozen_design"]["horizon_hours"] == OUTCOME_HORIZON_HOURS == 24
    assert gate["frozen_design"]["per_asset_selection"] is False
    assert protocol["primary_estimand"]["per_asset_beta_is_primary"] is False
    assert protocol["primary_estimand"]["per_asset_beta_may_rescue"] is False
    assert protocol["primary_estimand"]["evaluated_at_true_alignment"] is False
    assert protocol["future_outcome"]["terminal_interpolation"] is False
    assert protocol["future_outcome"]["one_position_constraint"] is False

    # Dependence, multiplicity and the economic threshold are the frozen ones.
    assert gate["dependence"]["cluster_dimensions"] == [
        "ASSET_INSTRUMENT_EPOCH",
        "UTC_CALENDAR_WEEK",
    ]
    assert gate["cluster_support"]["minimum_asset_clusters"] == MINIMUM_ASSET_CLUSTERS == 30
    assert gate["cluster_support"]["minimum_week_clusters"] == MINIMUM_WEEK_CLUSTERS == 100
    assert gate["cluster_support"]["manual_asset_addition"] is False
    assert mesi_bps() == CROSS_SECTION_MESI_BPS == 24.0
    assert gate["economic_threshold"]["lowered_after_power"] is False
    assert gate["multiplicity"]["prospective_family_size"] == PROSPECTIVE_FAMILY_SIZE == 13
    assert abs(gate["multiplicity"]["effective_alpha"] - 0.05 / 13) < 1e-15
    assert abs(EFFECTIVE_ALPHA - 0.05 / 13) < 1e-15
    assert gate["multiplicity"]["UNQUANTIFIED_PRE_REPO_EXPOSURE"] is True
    assert gate["power"]["target_power"] == TARGET_POWER == 0.8

    # The placebo is non-zero by construction and never rescues power.
    assert placebo["zero_shift_used"] is False
    assert placebo["minimum_absolute_shift_positions"] == PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS
    assert all(abs(shift) >= 168 for shift in _placebo_shift_bounds(placebo))
    assert placebo["searched_for_favourable_construction"] is False
    assert placebo["placebo_count"] > 0

    # Gate arithmetic: every prerequisite and the power target decide the status.
    prerequisites = gate["prerequisite_gates"]
    powered = gate["power"]["power_at_MESI"] >= TARGET_POWER
    expected = (
        "READY_FOR_PREREGISTRATION"
        if all(value == "PASS" for value in prerequisites.values()) and powered
        else "REDESIGN_REQUIRED"
    )
    assert gate["CROSS_SECTION_POWER_GATE_STATUS"] == expected
    assert record["power_gate_status"] == gate["CROSS_SECTION_POWER_GATE_STATUS"]
    assert record["placebo_calibration_status"] == placebo["PLACEBO_CALIBRATION_STATUS"]
    assert record["cluster_support_status"] == gate["cluster_support"]["CLUSTER_SUPPORT_STATUS"]
    assert record["data_source_status"] == equivalence["DATA_SOURCE_STATUS"]
    assert record["survivorship_status"] == survivorship["SURVIVORSHIP_STATUS"]
    assert protocol["status"] == "DESIGNED_NOT_PREREGISTERED_NOT_EXECUTED"
    if record["power_gate_status"] != "READY_FOR_PREREGISTRATION":
        assert gate["preregistration_authorized"] is False
        assert gate["actual_execution_authorized"] is False
        assert record["preregistration_authorized"] is False

    # Product and safety boundaries are untouched.
    assert record["product_universe"] == "BTCUSDT_SPOT_V1_UNCHANGED"
    assert record["cross_section_product_authorized"] is False
    assert record["multi_asset_trading_implemented"] is False
    assert state["symbols"] == ["BTCUSDT"]
    assert state["product_analysis"]["possible_outputs"] == ["NO_TRADE", "LONG"]
    assert state["paper_trading"]["strategy_version"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    assert gate["safety"] == {
        "experiments_completed": 26,
        "observed_material_economic_hypotheses": 12,
        "sealed_queries": 0,
        "champion_status": "NONE",
        "real_money_authorized": False,
        "cross_section_product_authorized": False,
    }
    assert state["experiments_completed"] == 26
    assert state["statistical_governance"]["known_discovery_family_size"] == 12
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False
    forbidden = {"cross_section", "multi_asset", "universe"}
    assert not any(
        word in str(getattr(route, "path", "")).lower()
        for route in _api_routes()
        for word in forbidden
    ), "a cross-sectional product surface was exposed"


def _placebo_shift_bounds(placebo: dict) -> list[int]:
    grid = placebo["shift_grid"]
    return [int(item["shift_positions"]) for item in grid.get("examples", [])]


def _api_routes() -> list:
    from app.main import app

    return list(app.routes)


def gate_intensity_checks(state: dict) -> None:
    """The V1_1 causal correction passes, then the immutable support gate parks the family."""
    from app.research.cross_section import assert_no_real_effect_leakage
    from app.research.gate_intensity import (
        EFFECTIVE_ALPHA,
        EXPECTED_RANDOMIZATION_FAMILY_SHA256,
        GATE_INTENSITY_MESI_BPS_PER_GATE,
        GATE_WEIGHTS,
        LEGAL_SHIFT_WEEKS,
        MAXIMUM_SHIFT_WEEKS,
        MINIMUM_SHIFT_WEEKS,
        NEW_GATE_PARAMETERS,
        PROSPECTIVE_FAMILY_SIZE,
        REQUESTED_REPLICATE_VECTORS,
        SYNTHETIC_SLOPES_BPS_PER_GATE,
        TARGET_POWER,
        ZeroShiftForbidden,
        aligned_from_intensity,
        gate_intensity,
        mesi_bps_per_gate,
        parse_frozen_shift_vectors,
        validate_shift_weeks,
    )

    record = state["gate_intensity_descendant"]
    sparse = state["cross_section_feasibility"]
    protocol = json.loads((ROOT / record["protocol"]).read_text(encoding="utf-8"))
    frozen = json.loads(
        (ROOT / "research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1.json").read_text(
            encoding="utf-8"
        )
    )
    gate = json.loads((ROOT / record["power_gate_report"]).read_text(encoding="utf-8"))
    score = json.loads((ROOT / record["score_report"]).read_text(encoding="utf-8"))
    family = json.loads((ROOT / record["randomization_report"]).read_text(encoding="utf-8"))
    support = json.loads(
        (ROOT / record["randomization_support_report"]).read_text(encoding="utf-8")
    )
    reconciliation = json.loads(
        (ROOT / record["causal_panel_reconciliation"]).read_text(encoding="utf-8")
    )
    legacy = json.loads((ROOT / sparse["event_reconciliation_report"]).read_text(encoding="utf-8"))
    for artifact in (gate, score, family, support, reconciliation, legacy):
        assert_no_real_effect_leakage(artifact)
        assert artifact["ACTUAL_CROSS_SECTION_EFFECT_OBSERVED"] is False

    # Retired sparse evidence remains unchanged and continues to reconcile 3380 -> 3378.
    assert sha256(ROOT / sparse["event_reconciliation_report"]) == (
        "cb81cd4f53cd1a3fb2de022492b647172693be462236de878e744264728e28c1"
    )
    assert sha256(ROOT / sparse["placebo_report"]) == (
        "2173590eae9b289d220cdd772bdb558c42516f5ff23115103d7b08d0aafd6383"
    )
    assert sha256(ROOT / sparse["power_gate_report"]) == (
        "52487ac2b35fe8b6905b41e0c88f77326dce47b35040ee0bef22b345bbd39b71"
    )
    assert legacy["support_artifact_signals"] == 3380
    assert legacy["power_panel_signals"] == 3378
    assert legacy["removed_signal_count"] == 2

    # V1_1 uses only frozen causal eligibility/intensity plus frozen outcome resolution.
    causal = reconciliation["causal_inclusion_rule"]
    assert causal["retired_504_row_filter_used"] is False
    assert causal["minimum_whole_epoch_lifetime"] is None
    assert causal["future_epoch_length_used"] is False
    assert causal["future_delisting_date_used"] is False
    assert causal["future_eligible_row_count_used"] is False
    assert causal["future_signal_count_used"] is False
    assert causal["future_survival_required"] is False
    assert reconciliation["base_rows"] == 2_556_535
    assert reconciliation["analysis_rows"] == 2_556_366
    assert reconciliation["removed_rows"] == 169
    assert reconciliation["base_epochs"] == reconciliation["analysis_epochs"] == 390
    assert reconciliation["base_intensity_3_events"] == 3380
    assert reconciliation["analysis_intensity_3_events"] == 3380
    assert reconciliation["events_removed"] == 0
    assert reconciliation["clusters_removed"] == []
    assert reconciliation["every_removed_row_has_typed_reason"] is True
    assert reconciliation["all_removals_are_frozen_outcome_contract_only"] is True
    assert reconciliation["EVENT_RECONCILIATION_STATUS"] == "PASS"
    assert record["event_reconciliation_status"] == "PASS"

    # Score, primary estimand, MESI and multiplicity are unchanged.
    assert GATE_WEIGHTS == (1, 1, 1) and NEW_GATE_PARAMETERS == 0
    assert gate_intensity(True, True, True) == 3 and aligned_from_intensity(3)
    assert gate_intensity(False, False, False) == 0 and not aligned_from_intensity(2)
    assert score["aligned_equals_intensity_three"] is True
    assert score["intensity_is_integer_0_to_3"] is True
    assert score["aligned_signal_count"] == score["intensity_three_count"] == 3380
    assert frozen["score"]["weights"] == [1, 1, 1]
    assert frozen["score"]["weighted"] is False
    assert frozen["primary_estimand"]["coefficient"] == "beta_gate"
    assert frozen["primary_estimand"]["count"] == 1
    assert mesi_bps_per_gate() == GATE_INTENSITY_MESI_BPS_PER_GATE == 8.0
    assert PROSPECTIVE_FAMILY_SIZE == 13 and record["prospective_family_size"] == 13
    assert abs(EFFECTIVE_ALPHA - 0.05 / 13) < 1e-15
    assert TARGET_POWER == 0.8
    assert SYNTHETIC_SLOPES_BPS_PER_GATE == (0.0, 4.0, 8.0, 16.0, 32.0)

    # The frozen family is read byte-identically; no replacement family was generated.
    assert sha256(ROOT / record["randomization_report"]) == (
        "4c94c99248ca759c0843824107b9c4c4b6743b1c0aa4e47f02b7c0348b9f4592"
    )
    assert family["family_sha256"] == EXPECTED_RANDOMIZATION_FAMILY_SHA256
    assert len(parse_frozen_shift_vectors(family)) == REQUESTED_REPLICATE_VECTORS == 1024
    assert family["zero_shift_present"] is False
    assert family["circular_wrap"] is False
    assert MINIMUM_SHIFT_WEEKS == 2 and MAXIMUM_SHIFT_WEEKS == 13
    assert 0 not in LEGAL_SHIFT_WEEKS
    for forbidden in (0, 1, -1, 14, -14):
        try:
            validate_shift_weeks(forbidden)
        except ZeroShiftForbidden:
            continue
        raise AssertionError("an illegal calendar displacement was accepted")
    assert support["vectors_regenerated"] is False
    assert support["thresholds"] == {
        "minimum_asset_cluster_retention": 0.8,
        "minimum_accepted_vectors": 512,
        "minimum_row_retention": 0.7,
        "required_year_coverage": 6,
    }

    # No vector passed support, so inference and power remain inaccessible and unmeasured.
    assert support["accepted_vectors"] == 0
    assert support["requested_vectors"] == 1024
    assert support["retention_distributions"]["row_retention"]["maximum"] < 0.7
    assert support["retention_distributions"]["years_represented"]["minimum"] == 6.0
    assert support["RANDOMIZATION_SUPPORT_STATUS"] == "REDESIGN_REQUIRED"
    assert gate["prerequisite_gates"]["RANDOMIZATION_INFERENCE_STATUS"] == "NOT_RUN_BLOCKED"
    assert gate["power"]["computed"] is False
    assert gate["power"]["power_at_8_bps_per_gate"] is None
    assert all(value is False for value in gate["leakage_guard"].values())
    assert gate["GATE_INTENSITY_POWER_GATE_STATUS"] == "REDESIGN_REQUIRED"
    assert gate["ALIGNED_DEVELOPMENT_FAMILY_STATUS"] == ("PARKED_DEVELOPMENT_SEARCH_EXHAUSTED")
    assert record["randomization_support_status"] == "REDESIGN_REQUIRED"
    assert record["randomization_inference_status"] == "NOT_RUN_BLOCKED"
    assert record["power_computed"] is False and record["power_at_mesi"] is None
    assert record["aligned_development_family_status"] == ("PARKED_DEVELOPMENT_SEARCH_EXHAUSTED")

    # Same hypothesis and unchanged safety/accounting/product boundaries.
    assert protocol["material_economic_hypothesis_changed"] is False
    assert protocol["material_economic_hypotheses_executed"] == 0
    assert record["material_economic_hypotheses_executed"] == 0
    assert record["product_universe"] == "BTCUSDT_SPOT_V1_UNCHANGED"
    assert state["symbols"] == ["BTCUSDT"]
    assert state["experiments_completed"] == 26
    assert state["statistical_governance"]["known_discovery_family_size"] == 12
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False


def dataset_scope_checks() -> None:
    """Metadata/inventory admission also runs in a checkout with no installed market data."""
    from app.research.continuation_lab import MANIFEST_SHA256
    from app.research.runner import sha256 as text_sha

    approved = ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
    order_flow = ROOT / "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json"
    gdelt = ROOT / "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json"
    alfred = ROOT / "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json"
    funding = ROOT / "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json"
    attention = ROOT / "data/manifests/WIKIMEDIA-BITCOIN-PAGEVIEWS-DEV-v1.json"
    exogenous = ROOT / "data/manifests/EXOGENOUS-CONTEXT-DEV-v1.json"
    cftc = ROOT / "data/manifests/CFTC-CME-BITCOIN-TFF-DEV-v1.json"
    cross_section = ROOT / "data/manifests/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.json"
    # The GDELT and combined-context manifests only exist once WP-009 is finalized; a
    # paused WP-009 must not be asked for them, and must not carry them either.
    wp009_final = gdelt.is_file() or exogenous.is_file()
    expected = {approved, order_flow, alfred, funding, attention, cftc, cross_section}
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
    cftc_manifest = json.loads(cftc.read_text(encoding="utf-8"))
    # Official CFTC annual TFF archives are the only other approved raw ZIP objects.
    raw |= {ROOT / item["path"] for item in cftc_manifest["raw_archives"]}
    cross_manifest = json.loads(cross_section.read_text(encoding="utf-8"))
    raw |= cross_section_raw_objects(cross_manifest)
    assert set((ROOT / "data/raw").rglob("*.zip")) <= raw
    alfred_manifest = json.loads(alfred.read_text(encoding="utf-8"))
    funding_manifest = json.loads(funding.read_text(encoding="utf-8"))
    attention_manifest = json.loads(attention.read_text(encoding="utf-8"))
    approved_parquet = {
        *(ROOT / item["path"] for item in manifest["files"].values()),
        *(ROOT / item["path"] for item in flow_manifest["files"].values()),
        ROOT / alfred_manifest["file"]["path"],
        ROOT / alfred_manifest["request_index"]["path"],
        ROOT / funding_manifest["canonical"]["path"],
        ROOT / funding_manifest["request_index"]["path"],
        ROOT / attention_manifest["canonical"]["path"],
        ROOT / cftc_manifest["canonical"]["path"],
        ROOT / cross_manifest["substrate"]["path"],
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
        "reports/reviews/RESEARCH-RUNNER-V1-RESEARCH-DIRECTOR-REVIEW.md",
        "docs/contracts/WIKIPEDIA_ATTENTION_CONTEXT_V1.md",
        "data/manifests/WIKIMEDIA-BITCOIN-PAGEVIEWS-DEV-v1.json",
        "reports/validation/WP-016-WIKIMEDIA-ATTENTION-AUDIT.json",
        "research/protocols/WP-016-WIKIPEDIA-ATTENTION-HGBR-V1.json",
        "reports/validation/WP-016-PREFLIGHT.json",
        "reports/audits/PROJECT-RETROSPECTIVE-V1.md",
        "reports/audits/PROJECT-RETROSPECTIVE-V1.json",
        "reports/checkpoints/PROJECT-RETROSPECTIVE-V1.md",
        "reports/reviews/PROJECT-RETROSPECTIVE-V1-RESEARCH-DIRECTOR-REVIEW.md",
        "tasks/archive/PROJECT-RETROSPECTIVE-V1.md",
        "decisions/ADR-0010-CAUSAL-PAPER-ENTRY-V2.md",
        "docs/contracts/FUTURE_PAPER_EVIDENCE_V2.md",
        "research/paper/FUTURE_PAPER_EVIDENCE_V2.json",
        "reports/checkpoints/PAPER-ENTRY-V2-STAGE-A.md",
        "decisions/ADR-0011-RESEARCH-RUNTIME-V2-BATCH.md",
        "research/runtime/FROZEN-HISTORICAL-RUNTIME-IDENTITIES.json",
        "research/runtime/RESEARCH-RUNTIME-V2-BATCH.json",
        "reports/benchmarks/RESEARCH-RUNTIME-V2-BATCH.json",
        "reports/checkpoints/PAPER-ENTRY-V2-RESEARCH-RUNTIME-V2.md",
        "reports/reviews/PAPER-ENTRY-V2-RESEARCH-RUNTIME-V2-CI-EVIDENCE.json",
        "reports/reviews/PAPER-ENTRY-V2-RESEARCH-RUNTIME-V2-RESEARCH-DIRECTOR-REVIEW.md",
        "reports/source_gates/WP017-SOURCE-DISCOVERY-GATE.md",
        "reports/source_gates/WP017-SOURCE-DISCOVERY-GATE.json",
        "reports/checkpoints/WP-017-SOURCE-DISCOVERY-GATE-OWNER-UX-V1_1.md",
        "reports/checkpoints/WP-017-CFTC-LEVERAGED-POSITIONING-PREP.md",
        "decisions/ADR-0012-WP017-CFTC-LEVERAGED-POSITIONING.md",
        "docs/contracts/CFTC_LEVERAGED_POSITIONING_CONTEXT_V1.md",
        "research/protocols/WP-017-CFTC-LEVERAGED-POSITIONING-V1.json",
        "reports/validation/WP-017-CFTC-INTEGRITY.json",
        "reports/validation/WP-017-PREFLIGHT.json",
        "tasks/archive/PAPER-ENTRY-V2-RESEARCH-RUNTIME-V2.md",
        "tasks/archive/WP-016-PREP.md",
        "tasks/archive/WP-017-CFTC-LEVERAGED-POSITIONING-PREP.md",
        "governance/RESEARCH_REBASELINE_V2.md",
        "governance/ECONOMIC_SIGNIFICANCE_POLICY_V1.json",
        "reports/reviews/WP-017-RESEARCH-DIRECTOR-REVIEW.json",
        "reports/reviews/WP-017-RESEARCH-DIRECTOR-REVIEW.md",
        "reports/statistics/MATERIAL-HYPOTHESIS-LEDGER-V1.json",
        "reports/statistics/MATERIAL-HYPOTHESIS-LEDGER-V1.md",
        "reports/statistics/ALIGNED-CONSTANT-PROVENANCE-V1.json",
        "reports/statistics/ALIGNED-CONSTANT-PROVENANCE-V1.md",
        "reports/statistics/STATISTICAL-EVIDENCE-AUDIT-V1.json",
        "reports/statistics/STATISTICAL-EVIDENCE-AUDIT-V1.md",
        "reports/checkpoints/RESEARCH-REBASELINE-V2-P0-STATISTICAL-GOVERNANCE-V1.md",
        "reports/validation/RESEARCH-REBASELINE-V2-P0-VALIDATION.json",
        "governance/NUMERICAL_DEPENDENCY_IDENTITY_V1.json",
        "reports/checkpoints/P0.1-DETECTABILITY-INFERENCE-AND-CI-PORTABILITY-FIX.md",
        "reports/reviews/P0.1-DETECTABILITY-CI-EVIDENCE.json",
        "reports/reviews/P1A-POWER-GATE-PREP-CI-EVIDENCE.json",
        "tasks/archive/RESEARCH-REBASELINE-V2-P0-STATISTICAL-GOVERNANCE-V1.md",
        "research/design/ALIGNED_SIGNAL_PERSISTENCE_V1_DESIGN.md",
        "decisions/ADR-0013-P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE.md",
        "reports/power/P1A-ALIGNED-SIGNAL-PERSISTENCE-NULL-DISTRIBUTION-V1.json",
        "reports/power/P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-V1.json",
        "reports/power/P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-V1.md",
        "reports/checkpoints/P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-PREP.md",
        "reports/reviews/P1A-POWER-BLOCK-REVIEW.md",
        "research/design/RESEARCH_ARCHITECTURE_SYNTHESIS_V1.md",
        "docs/canonical/CYCLE_RESEARCH_SOURCE_BOUNDARY_V1.md",
        "research/design/BTC_TIME_CYCLE_STRUCTURE_V1_DESIGN.md",
        "research/protocols/P2-CYCLE-FOUNDATION-V1.json",
        "research/memory/registry/directions/P2-CYCLE-FOUNDATION-DESIGN.json",
        "decisions/ADR-0014-P2-CYCLE-FOUNDATION-BOUNDARY.md",
        "reports/checkpoints/P1A-POWER-BLOCK-REVIEW-RESEARCH-ARCHITECTURE-SYNTHESIS-V1-P2-CYCLE-FOUNDATION-DESIGN.md",
        "tasks/archive/P1A-POWER-BLOCK-REVIEW-RESEARCH-ARCHITECTURE-SYNTHESIS-V1-P2-CYCLE-FOUNDATION-DESIGN.md",
        "decisions/ADR-0015-P2-CYCLE-NULL-FIDELITY-BLOCK.md",
        "reports/power/P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1.json",
        "reports/power/P2-CYCLE-NULL-FIDELITY-V1.json",
        "reports/power/P2-CYCLE-COMPUTE-BENCHMARK-V1.json",
        "reports/power/P2-CYCLE-FOUNDATION-POWER-GATE-V1.json",
        "reports/power/P2-CYCLE-FOUNDATION-POWER-GATE-V1.md",
        "reports/checkpoints/P2-CYCLE-FOUNDATION-POWER-GATE-PREP.md",
        "reports/reviews/P2-CYCLE-POWER-GATE-PREP-CI-EVIDENCE.json",
        "research/design/P2_CYCLE_NULL_V2_DESIGN.md",
        "research/protocols/P2-CYCLE-NULL-V2.json",
        "research/memory/registry/directions/P2-CYCLE-NULL-V2-REDESIGN.json",
        "decisions/ADR-0016-P2-CYCLE-NULL-V2.md",
        "decisions/ADR-0017-P2-CYCLE-NULL-V2-BLOCK-SUPPORT.md",
        "reports/power/P2-CYCLE-NULL-V2-PREREGISTRATION.json",
        "reports/power/P2-CYCLE-NULL-V2-BLOCK-SUPPORT.json",
        "reports/power/P2-CYCLE-POWER-GATE-V2.json",
        "reports/power/P2-CYCLE-POWER-GATE-V2.md",
        "reports/checkpoints/P2-CYCLE-NULL-V2-REDESIGN-P2-CYCLE-POWER-GATE-V2.md",
        "tasks/archive/P2-CYCLE-NULL-V2-REDESIGN-P2-CYCLE-POWER-GATE-V2.md",
        "reports/reviews/P2-METHODOLOGY-BLOCK-REVIEW.md",
        "research/design/RESEARCH_ARCHITECTURE_SYNTHESIS_V2.md",
        "decisions/ADR-0018-P2-METHODOLOGY-BLOCK-CLOSURE-AND-CROSS-SECTION-ALLOCATION.md",
        "reports/checkpoints/P2-METHODOLOGY-BLOCK-CLOSURE-RESEARCH-ARCHITECTURE-SYNTHESIS-V2.md",
        "tasks/archive/P2-METHODOLOGY-BLOCK-CLOSURE-RESEARCH-ARCHITECTURE-SYNTHESIS-V2.md",
        "reports/reviews/P2-METHODOLOGY-BLOCK-CLOSURE-CI-EVIDENCE.json",
        "research/design/CROSS_SECTION_COMMON_EFFECT_V1_DESIGN.md",
        "research/protocols/CROSS-SECTION-FEASIBILITY-AND-POWER-V1.json",
        "decisions/ADR-0019-CROSS-SECTION-FEASIBILITY-AND-POWER.md",
        "data/manifests/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.json",
        "reports/cross_section/CROSS-SECTION-ARCHIVE-INVENTORY-V1.json",
        "reports/cross_section/CROSS-SECTION-BTC-1H-EQUIVALENCE-V1.json",
        "reports/cross_section/CROSS-SECTION-UNIVERSE-FEASIBILITY-V1.json",
        "reports/cross_section/CROSS-SECTION-SIGNAL-SUPPORT-V1.json",
        "reports/cross_section/CROSS-SECTION-SURVIVORSHIP-AUDIT-V1.json",
        "reports/cross_section/CROSS-SECTION-PLACEBO-CALIBRATION-V1.json",
        "reports/power/CROSS-SECTION-POWER-GATE-V1.json",
        "reports/power/CROSS-SECTION-POWER-GATE-V1.md",
        "reports/checkpoints/CROSS-SECTION-FEASIBILITY-AND-POWER-DESIGN-V1.md",
        "tasks/archive/CROSS-SECTION-FEASIBILITY-AND-POWER-DESIGN-V1.md",
        "reports/reviews/CROSS-SECTION-FEASIBILITY-AND-POWER-CI-EVIDENCE.json",
        "reports/reviews/CROSS-SECTION-SPARSE-POWER-BLOCK-REVIEW.md",
        "reports/cross_section/CROSS-SECTION-EVENT-RECONCILIATION-V1.json",
        "research/design/ALIGNED_GATE_INTENSITY_COMMON_EFFECT_V1_DESIGN.md",
        "research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1.json",
        "research/memory/registry/directions/ALIGNED-GATE-INTENSITY-DESCENDANT.json",
        "decisions/ADR-0020-ALIGNED-GATE-INTENSITY-DESCENDANT.md",
        "reports/cross_section/GATE-INTENSITY-SCORE-V1.json",
        "reports/cross_section/GATE-INTENSITY-RANDOMIZATION-FAMILY-V1.json",
        "reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1.json",
        "reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1.md",
        "reports/checkpoints/CROSS-SECTION-SPARSE-HYPOTHESIS-CLOSURE-ALIGNED-GATE-INTENSITY-POWER-GATE-V1.md",
        "tasks/archive/CROSS-SECTION-SPARSE-HYPOTHESIS-CLOSURE-ALIGNED-GATE-INTENSITY-POWER-GATE-V1.md",
        "reports/reviews/ALIGNED-GATE-INTENSITY-CI-EVIDENCE.json",
        "research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1_1.json",
        "decisions/ADR-0021-GATE-INTENSITY-CAUSAL-CORRECTION-AND-SUPPORT-BLOCK.md",
        "reports/cross_section/CROSS-SECTION-GATE-INTENSITY-PANEL-RECONCILIATION-V1_1.json",
        "reports/cross_section/GATE-INTENSITY-RANDOMIZATION-SUPPORT-V1_1.json",
        "reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1_1.json",
        "reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1_1.md",
        "reports/checkpoints/GATE-INTENSITY-CAUSAL-CORRECTION-POWER-RESUME-V1_1.md",
        "tasks/archive/GATE-INTENSITY-CAUSAL-CORRECTION-POWER-RESUME-V1_1.md",
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
    baseline_normalized = baseline.replace("\r\n", "\n").rstrip()
    constitution_normalized = constitution.replace("\r\n", "\n")
    assert constitution_normalized.startswith(baseline_normalized + "\n\n")
    assert "## Selection/evaluation separation" in constitution_normalized
    assert "## Future power gate" in constitution_normalized
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
    source_gate = json.loads(
        (ROOT / "reports/source_gates/WP017-SOURCE-DISCOVERY-GATE.json").read_text(encoding="utf-8")
    )
    assert source_gate["recommended_source"] == "CFTC_CME_BITCOIN_COT"
    assert len(source_gate["candidates"]) >= 3
    assert all(
        candidate["point_in_time_status"] == "PASS" for candidate in source_gate["candidates"]
    )
    accounting = source_gate["scientific_accounting"]
    assert accounting == {
        "completed_experiments_before": 25,
        "completed_experiments_after": 25,
        "model_fits": 0,
        "backtests": 0,
        "sealed_queries": 0,
        "wp017_preregistered": False,
        "wp016_executed": False,
    }
    assert state["development_cutoff"] == "2024-12-31T23:59:00Z"
    approved_state = json.loads(git("show", f"{WP004_BASE}:state/current_state.json"))
    assert state["development_dataset"] == approved_state["development_dataset"]
    assert state["sealed_evaluations_completed"] == state["paper_trades_completed"] == 0
    assert (
        state["champion_status"] == state["forward_evidence"] == "NONE"
        and not state["real_money_authorized"]
    )
    p1a_state = state["signal_persistence_power_gate"]
    p1a_gate = json.loads((ROOT / p1a_state["report_json"]).read_text(encoding="utf-8"))
    assert p1a_state["power_gate_status"] == p1a_gate["power_gate_status"]
    assert p1a_state["power_at_mesi"] == p1a_gate["power"]["power_at_MESI"]
    assert (
        p1a_state["empirical_mde_bps_per_event"] == p1a_gate["power"]["empirical_MDE_bps_per_event"]
    )
    assert p1a_state["raw_signal_count"] == p1a_gate["signal"]["raw_signal_count"]
    assert not p1a_state["material_experiment_executed"]
    assert not p1a_state["zero_shift_statistic_computed"]
    assert p1a_state["hypothesis_status"] == "POWER_BLOCKED_NOT_EXECUTED"
    assert p1a_state["hypothesis_status"] not in {"REJECT", "INCONCLUSIVE"}
    assert p1a_gate["economic_threshold"]["P1A_INFORMATION_MESI_BPS"] == 24.0
    assert round(p1a_gate["power"]["empirical_MDE_bps_per_event"], 6) == 285.640052
    assert round(p1a_gate["power"]["power_at_MESI"], 8) == 0.01424888
    if p1a_state["power_gate_status"] != "READY_FOR_PREREGISTRATION":
        assert not p1a_state["preregistration_authorized"]
        assert not p1a_state["runner_candidate_registered"]
    p2 = json.loads(
        (ROOT / "research/protocols/P2-CYCLE-FOUNDATION-V1.json").read_text(encoding="utf-8")
    )
    p2_state = state["cycle_foundation"]
    assert len(p2["primary_hypotheses"]) == p2["budget"]["primary_structural_hypotheses"] == 1
    assert len(p2["diagnostics"]) <= p2["budget"]["maximum_diagnostics"] == 2
    assert p2["budget"]["material_economic_hypotheses_executed"] == 0
    assert not p2["actual_market_result_inspected"]
    assert not p2["detectability"]["actual_market_result_available"]
    assert p2["detectability"]["economic_mesi"] is None
    assert p2["detectability"]["target_power"] == 0.8
    assert not p2["economic_strategy_created"] and p2["implemented_components"] == []
    assert p2_state["primary_hypothesis_id"] == "BTC_TIME_CYCLE_STRUCTURE_V1"
    assert p2_state["diagnostic_count"] <= p2_state["maximum_diagnostics"] == 2
    assert not p2_state["actual_market_result_inspected"]
    assert not p2_state["economic_strategy_created"]
    p2_power_gate_checks(state, p2)
    p2_null_v2_checks(state)
    p2_closure_checks(state)
    cross_section_checks(state)
    gate_intensity_checks(state)
    boundary = (ROOT / p2["source_boundary"]).read_text(encoding="utf-8")
    for unsupported in (
        "complete centering algorithm",
        "universal swing-selection formula",
        "universal swing-value formula",
        "universal volume thresholds",
        "complete raccordo algorithm",
        "target algorithm",
        "official executable code",
    ):
        line = next(line for line in boundary.splitlines() if f"| {unsupported} |" in line)
        assert "| UNSPECIFIED |" in line
    forbidden_cycle_modules = {
        "cycle.py",
        "cycle_swing.py",
        "cycle_volume.py",
        "cycle_inverse.py",
        "cycle_vincolo.py",
        "cycle_raccordo.py",
        "cycle_target.py",
        "cycle_trading.py",
    }
    assert not forbidden_cycle_modules.intersection(
        path.name for path in (ROOT / "backend/app/research").glob("*.py")
    )
    assert state["experiments_completed"] == 26
    assert state["statistical_governance"]["known_discovery_family_size"] == 12
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False
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
    alfred_path = ROOT / "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json"
    funding_path = ROOT / "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json"
    attention_path = ROOT / "data/manifests/WIKIMEDIA-BITCOIN-PAGEVIEWS-DEV-v1.json"
    cftc_path = ROOT / "data/manifests/CFTC-CME-BITCOIN-TFF-DEV-v1.json"
    cross_path = ROOT / "data/manifests/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.json"
    assert set((ROOT / "data/manifests").glob("*.json")) == {
        path,
        flow_path,
        alfred_path,
        funding_path,
        attention_path,
        cftc_path,
        cross_path,
    }
    manifest = validate_json(path, schema)
    flow_manifest = json.loads(flow_path.read_text(encoding="utf-8"))
    alfred_manifest = json.loads(alfred_path.read_text(encoding="utf-8"))
    funding_manifest = json.loads(funding_path.read_text(encoding="utf-8"))
    attention_manifest = json.loads(attention_path.read_text(encoding="utf-8"))
    cftc_manifest = json.loads(cftc_path.read_text(encoding="utf-8"))
    assert manifest["symbol"] == "BTCUSDT"
    assert parse_utc_instant(manifest["coverage"]["end"]) <= CUTOFF
    assert parse_utc_instant(flow_manifest["coverage"]["end"]) <= CUTOFF
    assert (
        sha256(path) == state["development_dataset"]["manifest_sha256"]
        and manifest["content_hash"]["value"] == state["development_dataset"]["content_hash"]
    )
    raw = {ROOT / x["path"] for x in manifest["source"]["raw_objects"]}
    cftc_raw = {ROOT / x["path"] for x in cftc_manifest["raw_archives"]}
    cross_manifest = json.loads(cross_path.read_text(encoding="utf-8"))
    cross_raw = cross_section_raw_objects(cross_manifest)
    assert set((ROOT / "data/raw").rglob("*.zip")) == raw | cftc_raw | cross_raw
    assert all(
        "BTCUSDT" in p.name and not any(f"-{y}-" in p.name for y in range(2025, 2100)) for p in raw
    )
    for record in cftc_manifest["raw_archives"]:
        assert sha256(ROOT / record["path"]) == record["sha256"]
        assert record["year"] <= 2024, "post-cutoff CFTC archive year"
    parquet = {
        *(ROOT / x["path"] for x in manifest["files"].values()),
        *(ROOT / x["path"] for x in flow_manifest["files"].values()),
        ROOT / alfred_manifest["file"]["path"],
        ROOT / alfred_manifest["request_index"]["path"],
        ROOT / funding_manifest["canonical"]["path"],
        ROOT / funding_manifest["request_index"]["path"],
        ROOT / attention_manifest["canonical"]["path"],
        ROOT / cftc_manifest["canonical"]["path"],
        *(
            ROOT / relative
            for relative in (
                "data/derived/WP-011-adaptive-trials.parquet",
                "data/derived/WP-012-regime-trials.parquet",
                "data/derived/WP-013-context-interaction-trials.parquet",
                "data/derived/WP-014-shallow-internal-trials.parquet",
                "data/derived/WP-015-funding-predictions.parquet",
                "data/derived/WP-015-funding-trials.parquet",
            )
        ),
        ROOT / cross_manifest["substrate"]["path"],
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
    alfred_integrity = json.loads(
        (ROOT / "reports/validation/WP-009-ALFRED-INTEGRITY.json").read_text(encoding="utf-8")
    )
    assert alfred_integrity["status"] == "PASS"
    assert alfred_manifest["current_revised_substitution"] is False
    assert alfred_manifest["post_2024_vintages"] == 0
    assert sha256(ROOT / alfred_manifest["file"]["path"]) == alfred_manifest["file"]["file_sha256"]
    assert (
        sha256(ROOT / alfred_manifest["request_index"]["path"])
        == alfred_manifest["request_index"]["file_sha256"]
    )
    gdelt_pause = json.loads(
        (ROOT / "research/exogenous/GDELT-NEWS-CONTEXT-V1_1-PAUSE-V1.json").read_text(
            encoding="utf-8"
        )
    )
    preserved = gdelt_pause["preserved_requests"]
    assert gdelt_pause["status"] == "PARTIAL"
    assert gdelt_pause["preserved_request_count"] == len(preserved) == 3
    assert gdelt_pause["outstanding_request_count"] == 7
    daily_root = ROOT / gdelt_pause["preservation"]["v1_1_daily_cache_root"]
    assert set(daily_root.rglob("*.json.gz")) == {ROOT / item["raw_path"] for item in preserved}
    assert len(list(daily_root.rglob("*.meta.json"))) == len(preserved)
    for item in preserved:
        raw_path = ROOT / item["raw_path"]
        meta_path = raw_path.with_name(raw_path.name.removesuffix(".json.gz") + ".meta.json")
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        assert sha256(raw_path) == item["compressed_file_sha256"]
        assert all(
            metadata[key] == item[key]
            for key in (
                "request_id",
                "response_sha256",
                "compressed_file_sha256",
                "date_resolution",
                "retrieval_time_utc",
            )
        )
    from app.research.funding import load_funding_context
    from app.research.wikimedia import load_attention_context

    funding = load_funding_context()
    attention = load_attention_context()
    assert len(funding.rates) == funding_manifest["canonical"]["rows"] == 5819
    assert len(attention.observation_us) == attention_manifest["canonical"]["rows"] == 3472
    assert attention_manifest["integrity"] == {
        "duplicates": 0,
        "missing_day_values": [],
        "missing_days": 0,
        "post_cutoff_rows": 0,
        "strictly_increasing": True,
    }
    for external_manifest in (funding_manifest, attention_manifest):
        for record in external_manifest["raw_requests"]:
            assert sha256(ROOT / record["path"]) == record["sha256"]
    from app.research.signal_persistence import build_null_distribution
    from app.research.signal_persistence_lab import load_fold_series
    from app.research.statistical_governance import json_bytes

    null_path = ROOT / state["signal_persistence_power_gate"]["null_distribution"]
    assert json_bytes(build_null_distribution(load_fold_series(ROOT))) == null_path.read_bytes()
    from app.research.cycle_structure_lab import (
        build_joint_design,
        fidelity_report,
        fit_models,
        load_grids,
    )

    grids = load_grids(ROOT)
    joint = build_joint_design(grids, fit_models(grids))
    fidelity_path = ROOT / state["cycle_power_gate"]["null_fidelity_report"]
    assert json_bytes(fidelity_report(grids, joint, ROOT)) == fidelity_path.read_bytes()
    from app.research.cycle_structure_v2_lab import block_support_report, build_donors

    donors = build_donors(grids)
    support_path = ROOT / state["cycle_null_v2"]["block_support_report"]
    assert json_bytes(block_support_report(grids, donors, ROOT)) == support_path.read_bytes()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-data", action="store_true")
    parser.add_argument("--pre-experiment", action="store_true")
    options = parser.parse_args()
    state = governance_checks(options.pre_experiment)
    run([sys.executable, "scripts/check_numerical_environment.py"])
    run([sys.executable, "scripts/audit_statistical_evidence.py", "--check"])
    run([sys.executable, "scripts/audit_p1a_power_gate.py", "--check"])
    run([sys.executable, "scripts/audit_p2_cycle_power_gate.py", "--check"])
    run([sys.executable, "scripts/audit_p2_cycle_null_v2.py", "--check"])
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
