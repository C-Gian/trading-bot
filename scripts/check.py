from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
REVIEWED = "47dd69d73768a9e3a3c92fe08eb1e7e3e8c239f5"
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
        digest.update(
            path.relative_to(ROOT).as_posix().encode() + b"\0" + path.read_bytes() + b"\0"
        )
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

    directories = {p.name for p in (ROOT / "research/experiments").iterdir() if p.is_dir()}
    assert directories == set(EXPERIMENTS) and len(results) == state["experiments_completed"] == 6
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


def governance_checks(pre_experiment: bool) -> dict:
    required = [
        "governance/SCIENTIFIC_CONSTITUTION.md",
        "reports/reviews/WP-002-RESEARCH-DIRECTOR-REVIEW.md",
        "decisions/ADR-0003-PRE-EXPERIMENT-SUBSTRATE-CORRECTIONS.md",
        "docs/contracts/BACKTEST_ENGINE_V2.md",
        "docs/contracts/EXECUTION_MODEL_V2.md",
        "docs/contracts/COST_MODEL_V1.md",
        "data/reports/BTCUSDT-SPOT-1M-DEV-v1-gaps.json",
    ]
    assert all((ROOT / x).is_file() for x in required)
    baseline = subprocess.check_output(
        ["git", "show", f"{SEED}:SCIENTIFIC_CONSTITUTION.md"], cwd=ROOT
    )
    assert (ROOT / "governance/SCIENTIFIC_CONSTITUTION.md").read_bytes() == baseline
    assert git("branch", "--show-current") == "main"
    for ancestor in (SEED, PREDECESSOR, REVIEWED):
        run(["git", "merge-base", "--is-ancestor", ancestor, "HEAD"])
    state = validate_json(
        ROOT / "state/current_state.json", ROOT / "contracts/project_state.schema.json"
    )
    assert state["development_cutoff"] == "2024-12-31T23:59:00Z"
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
    assert not any(
        (ROOT / p).exists()
        for p in ("backend/app/exchange", "backend/app/orders", "backend/app/credentials")
    )
    source = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "backend/app").rglob("*.py"))
    assert all(
        x not in source
        for x in ("create_order(", "api_key", "secret_key", "ccxt", "binance.client")
    )
    return state


def data_checks(state: dict) -> None:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from analyze_gaps import build_artifact
    from app.data.policy import parse_utc_instant

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
    artifact = json.loads((ROOT / "data/reports/BTCUSDT-SPOT-1M-DEV-v1-gaps.json").read_text())
    assert (
        artifact == build_artifact()
        and artifact["total_missing_minutes"] == manifest["integrity"]["missing_minutes"]
    )


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
    print("WP-003 deterministic validation: PASS")


if __name__ == "__main__":
    main()
