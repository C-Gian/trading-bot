from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
CUTOFF_US = 1_735_689_540_000_000
BASE = "60ab3141862da74028763e2df72ac3c88b63b5a8"
SEED = "c6c526124945aa1624118bd7ee6aef9ae5c011b2"


def run(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(
        command, cwd=cwd, check=True, shell=sys.platform == "win32" and command[0] == "npm"
    )


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
            *(ROOT / "backend/tests").glob("test_engine.py"),
            *(ROOT / "backend/tests").glob("test_splitter.py"),
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
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
        payload
    )
    return payload


def governance_checks() -> dict:
    required = [
        "governance/SCIENTIFIC_CONSTITUTION.md",
        "reports/reviews/WP-001-RESEARCH-DIRECTOR-REVIEW.md",
        "decisions/ADR-0002-BACKTEST-EXECUTION-SEMANTICS.md",
        "docs/contracts/BACKTEST_ENGINE_V1.md",
        "docs/contracts/EXECUTION_MODEL_V1.md",
        "docs/contracts/COST_MODEL_V1.md",
        "docs/contracts/TIME_SERIES_EVALUATION_V1.md",
        "data/reports/BTCUSDT-SPOT-1M-DEV-v1-gaps.json",
    ]
    assert all((ROOT / item).is_file() for item in required)
    baseline = subprocess.check_output(
        ["git", "show", f"{SEED}:SCIENTIFIC_CONSTITUTION.md"], cwd=ROOT
    )
    assert (ROOT / "governance/SCIENTIFIC_CONSTITUTION.md").read_bytes() == baseline
    if not os.environ.get("CI"):
        assert (
            subprocess.check_output(["git", "rev-parse", "main"], cwd=ROOT, text=True).strip()
            == SEED
        )
    assert (
        subprocess.check_output(["git", "merge-base", BASE, "HEAD"], cwd=ROOT, text=True).strip()
        == BASE
    )
    state = validate_json(
        ROOT / "state/current_state.json", ROOT / "contracts/project_state.schema.json"
    )
    assert (
        state["experiments_completed"]
        == state["sealed_evaluations_completed"]
        == state["paper_trades_completed"]
        == 0
    )
    assert state["champion_status"] == state["forward_evidence"] == "NONE"
    assert state["real_money_authorized"] is False and state["owner_decision_required"] is False
    assert state["backtest_substrate"]["status"] == "VALIDATED"
    assert state["backtest_substrate"]["synthetic_validation"]["status"] == "PASS"
    gap_path = ROOT / "data/reports/BTCUSDT-SPOT-1M-DEV-v1-gaps.json"
    assert sha256(gap_path) == state["backtest_substrate"]["gap_artifact"]["sha256"]
    assert not any(path.is_file() for path in (ROOT / "research/experiments").rglob("*"))
    forbidden_paths = [
        ROOT / "backend/app/strategies",
        ROOT / "backend/app/exchange",
        ROOT / "backend/app/orders",
        ROOT / "backend/app/credentials",
    ]
    assert not any(path.exists() for path in forbidden_paths)
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "backend/app").rglob("*.py")
    )
    assert all(
        token not in source
        for token in ("create_order(", "api_key", "secret_key", "ccxt", "binance.client")
    )
    return state


def data_checks(state: dict) -> None:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from analyze_gaps import build_artifact

    manifests = list((ROOT / "data/manifests").glob("*.json"))
    assert manifests
    schema = ROOT / "contracts/dataset_manifest.schema.json"
    for path in manifests:
        manifest = validate_json(path, schema)
        assert (
            manifest["symbol"] == "BTCUSDT"
            and manifest["coverage"]["end"] <= state["development_cutoff"]
        )
    manifest = validate_json(ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json", schema)
    assert (
        sha256(ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json")
        == state["development_dataset"]["manifest_sha256"]
    )
    assert manifest["content_hash"]["value"] == state["development_dataset"]["content_hash"]
    expected_raw = {ROOT / record["path"] for record in manifest["source"]["raw_objects"]}
    assert set((ROOT / "data/raw").rglob("*.zip")) == expected_raw
    assert all(
        "BTCUSDT" in path.name and not any(f"-{year}-" in path.name for year in range(2025, 2100))
        for path in expected_raw
    )
    expected_parquet = {ROOT / record["path"] for record in manifest["files"].values()}
    assert (
        set((ROOT / "data/canonical").rglob("*.parquet"))
        | set((ROOT / "data/derived").rglob("*.parquet"))
        == expected_parquet
    )
    for record in [*manifest["source"]["raw_objects"], *manifest["files"].values()]:
        assert sha256(ROOT / record["path"]) == record["sha256"]
    for label, record in manifest["files"].items():
        table = pq.read_table(ROOT / record["path"])
        assert table.num_rows == manifest["row_counts"]["1m" if label == "canonical" else label]
        opens = pc.cast(table["open_time"], pa.int64())
        assert opens[-1].as_py() <= CUTOFF_US and pc.count_distinct(opens).as_py() == table.num_rows
        if label == "canonical":
            invalid = pc.or_(
                pc.less(table["high"], pc.max_element_wise(table["open"], table["close"])),
                pc.or_(
                    pc.greater(table["low"], pc.min_element_wise(table["open"], table["close"])),
                    pc.less(table["volume"], 0),
                ),
            )
            assert pc.sum(pc.cast(invalid, pa.int64())).as_py() == 0
        else:
            incomplete = table.num_rows - pc.sum(pc.cast(table["complete"], pa.int64())).as_py()
            assert incomplete == manifest["integrity"]["incomplete_windows"][label]
    artifact_path = ROOT / "data/reports/BTCUSDT-SPOT-1M-DEV-v1-gaps.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert (
        artifact == build_artifact()
        and artifact["total_missing_minutes"] == manifest["integrity"]["missing_minutes"]
    )
    assert sha256(artifact_path) == state["backtest_substrate"]["gap_artifact"]["sha256"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-data", action="store_true")
    options = parser.parse_args()
    state = governance_checks()
    run([sys.executable, "-m", "ruff", "check", "backend", "scripts"])
    run([sys.executable, "-m", "ruff", "format", "--check", "backend", "scripts"])
    run([sys.executable, "-m", "mypy", "backend"])
    run([sys.executable, "-m", "pytest", "-q"])
    run(["npm", "run", "lint"], ROOT / "frontend")
    run(["npm", "run", "typecheck"], ROOT / "frontend")
    run(["npm", "run", "test"], ROOT / "frontend")
    run(["npm", "run", "build"], ROOT / "frontend")
    assert state["backtest_substrate"]["synthetic_validation"]["suite_hash"] == suite_hash()
    if not options.no_data:
        data_checks(state)
    print("WP-002 deterministic validation: PASS")


if __name__ == "__main__":
    main()
