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

    directories = {p.name for p in (ROOT / "research/experiments").iterdir() if p.is_dir()}
    assert directories == set(EXPERIMENTS) | set(SPEC)
    assert len(results) == state["experiments_completed"] == 9
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
    from app.research.search_memory import load_memory
    from app.research.search_memory_v2 import validate_search_memory_v2
    from app.research.wp004 import SPEC, immutable_from_first_commit

    memory = load_memory()
    assert state["schema_version"] == 3
    assert state["search_memory"] == {
        "version": "SEARCH_MEMORY_V2",
        "status": "VALIDATED",
        "families_tracked": len(memory["families"]["families"]),
    }
    prior = validate_adaptive()
    assert state["adaptive_search"] == {
        **prior,
        "numeric_parameter_variants": 0,
        "adaptive_decisions": 2,
        "result_dependent_forks": 2,
        "integrity_replay_profiles": 12,
        "diagnostic_evaluations": 35,
        "diagnostic_execution_attempts": 2,
    }
    assert validate_search_memory_v2()["status"] == "PASS"
    assert state["selected_family"]["name"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    assert state["selected_family"]["primary_experiment_id"] == "EXP-ALG-009-ALIGNED"
    assert (
        state["latest_reviewed_checkpoint"] == "WP-004"
        and state["latest_executor_checkpoint"] == "WP-005"
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
    from app.research.wp005_validation import validate_wp005

    wp005 = validate_wp005(data_available=False)
    assert state["wp005_integrity"] == {
        "status": "PASS",
        "source_provenance_classification": wp005["source_provenance"],
        "independent_reconciliation": wp005["independent_reconciliation"],
        "integrity_replay_profiles": wp005["integrity_replay_profiles"],
        "matched_control_classification": wp005["classification"],
        "remote_ci": "PENDING_PUSH",
    }


def dataset_scope_checks() -> None:
    """Metadata/inventory admission also runs in a checkout with no installed market data."""
    from app.research.continuation_lab import MANIFEST_SHA256
    from app.research.runner import sha256 as text_sha

    approved = ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
    assert set((ROOT / "data/manifests").glob("*.json")) == {approved}
    manifest = validate_json(approved, ROOT / "contracts/dataset_manifest.schema.json")
    assert text_sha(approved) == MANIFEST_SHA256 and manifest["symbol"] == "BTCUSDT"
    assert manifest["coverage"]["end"] == "2024-12-31T23:59:00Z"
    raw = {ROOT / item["path"] for item in manifest["source"]["raw_objects"]}
    assert set((ROOT / "data/raw").rglob("*.zip")) <= raw
    approved_parquet = {ROOT / item["path"] for item in manifest["files"].values()}
    assert (
        set((ROOT / "data/canonical").rglob("*.parquet"))
        | set((ROOT / "data/derived").rglob("*.parquet"))
        <= approved_parquet
    )


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
    ]
    assert all((ROOT / x).is_file() for x in required)
    assert "## STATUS\nCOMPLETED" in (ROOT / "tasks/CURRENT_TASK.md").read_text(
        encoding="utf-8"
    ).replace("\r\n", "\n")
    assert (ROOT / "tasks/archive/WP-005.md").read_bytes().replace(
        b"\r\n", b"\n"
    ) == (ROOT / "tasks/CURRENT_TASK.md").read_bytes().replace(b"\r\n", b"\n")
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
    for ancestor in (SEED, PREDECESSOR, REVIEWED, WP004_BASE, WP005_BASE):
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
    from app.main import app

    assert all(
        set(route.methods or ()) <= {"GET", "HEAD"}
        for route in app.routes
        if hasattr(route, "methods")
    )
    return state


def data_checks(state: dict) -> None:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from analyze_gaps import build_artifact
    from app.data.policy import parse_utc_instant
    from app.research.source_grid import grid_audit

    schema = ROOT / "contracts/dataset_manifest.schema.json"
    manifests = list((ROOT / "data/manifests").glob("*.json"))
    assert manifests
    for path in manifests:
        m = validate_json(path, schema)
        assert m["symbol"] == "BTCUSDT" and parse_utc_instant(m["coverage"]["end"]) <= CUTOFF
    path = ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
    manifest = validate_json(path, schema)
    assert (
        sha256(path) == state["development_dataset"]["manifest_sha256"]
        and manifest["content_hash"]["value"] == state["development_dataset"]["content_hash"]
    )
    raw = {ROOT / x["path"] for x in manifest["source"]["raw_objects"]}
    assert set((ROOT / "data/raw").rglob("*.zip")) == raw
    assert all(
        "BTCUSDT" in p.name and not any(f"-{y}-" in p.name for y in range(2025, 2100)) for p in raw
    )
    parquet = {ROOT / x["path"] for x in manifest["files"].values()}
    assert (
        set((ROOT / "data/canonical").rglob("*.parquet"))
        | set((ROOT / "data/derived").rglob("*.parquet"))
        == parquet
    )
    for record in [*manifest["source"]["raw_objects"], *manifest["files"].values()]:
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
    print("WP-005 deterministic validation: PASS (profitability is not a validation gate)")


if __name__ == "__main__":
    main()
