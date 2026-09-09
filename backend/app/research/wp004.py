"""WP-004 immutable identities and admission gates, independent of market loading."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .adaptive import validate_adaptive
from .continuation_lab import PROFILES, validate_config
from .evaluation_protocol import load_protocol, protocol_hash
from .records import validate_preregistration
from .runner import declared_content_identity, sha256
from .search_memory import load_memory, validate_memory

ROOT = Path(__file__).resolve().parents[3]
BASE = "2b40aa03cfc05ac7f57d269f596f1ebacdc9d356"
DESIGN_COMMIT = "17cc59a"
PROTOCOL_COMMIT = "a8c91b8"
SPEC = {
    "EXP-ALG-007-REGIME": ("REGIME_ONLY", "regime_only"),
    "EXP-ALG-008-PARTICIPATION": ("PARTICIPATION_ONLY", "participation_only"),
    "EXP-ALG-009-ALIGNED": ("ALIGNED", "aligned"),
}
IMPLEMENTATION_PATHS = (
    "backend/app/data/policy.py",
    "backend/app/backtest/__init__.py",
    "backend/app/backtest/models.py",
    "backend/app/backtest/engine.py",
    "backend/app/research/baselines.py",
    "backend/app/research/records.py",
    "backend/app/research/runner.py",
    "backend/app/research/search_memory.py",
    "backend/app/research/adaptive.py",
    "backend/app/research/evaluation_protocol.py",
    "backend/app/research/continuation.py",
    "backend/app/research/continuation_lab.py",
    "backend/app/research/source_grid.py",
    "backend/app/research/wp004.py",
    "backend/tests/test_continuation.py",
    "backend/tests/test_evaluation_protocol.py",
    "backend/tests/test_search_memory.py",
    "backend/tests/test_wp004.py",
    "backend/tests/test_source_grid.py",
    "scripts/run_wp004.py",
    "research/design/ALGORITHM_FAMILY_V1_DESIGN.md",
    "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json",
    "research/protocols/CONTINUATION_FEATURES_V1.json",
    "research/protocols/CONTINUATION_FEATURES_V2.json",
    "reports/validation/WP-004-SOURCE-GRID.json",
    "reports/validation/WP-004-PREEXECUTION-ABORT.json",
    "decisions/ADR-0005-PREEXECUTION-SOURCE-GRID-QUARANTINE.md",
    "research/memory/SEARCH_BUDGET.json",
    "research/memory/ADAPTIVE_DECISIONS.json",
    "docs/contracts/DEVELOPMENT_EVALUATION_V1.md",
    "docs/contracts/EXECUTION_MODEL_V2.md",
    "docs/contracts/COST_MODEL_V1.md",
    "uv.lock",
    "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json",
)


def git(*args: str, root: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True, encoding="utf-8").strip()


def ancestor(older: str, newer: str, root: Path = ROOT) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", older, newer],
            cwd=root,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def first_commit(path: str, root: Path = ROOT) -> str:
    commits = git("log", "--diff-filter=A", "--format=%H", "--", path, root=root).splitlines()
    if not commits:
        raise ValueError(f"scientific record is not committed: {path}")
    return commits[-1]


def immutable_from_first_commit(path: str, root: Path = ROOT) -> str:
    commit = first_commit(path, root)
    content = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=root)
    if content.replace(b"\r\n", b"\n") != (root / path).read_bytes().replace(b"\r\n", b"\n"):
        raise ValueError(f"immutable scientific record changed: {path}")
    return commit


def dependency_manifest(root: Path = ROOT) -> list[dict[str, str]]:
    return [{"path": path, "sha256": sha256(root / path)} for path in IMPLEMENTATION_PATHS]


def effective_preregistration(experiment_id: str, root: Path = ROOT) -> Path:
    registry_path = root / "research/protocols/WP-004-PREEXECUTION-AMENDMENTS.json"
    registry = json.loads(registry_path.read_text())
    if (
        registry["kind"] != "PRE_EXECUTION_DATA_INTEGRITY_CORRECTION"
        or registry["strategy_trials_before_amendment"] != 0
        or set(registry["amendments"]) != set(SPEC)
    ):
        raise ValueError("invalid pre-execution supersession registry")
    item = registry["amendments"][experiment_id]
    expected = f"research/experiments/{experiment_id}/preregistration.v2.json"
    old = root / f"research/experiments/{experiment_id}/preregistration.json"
    if item["effective_path"] != expected or item["superseded_sha256"] != sha256(old):
        raise ValueError("superseded preregistration identity changed")
    path = root / expected
    if sha256(path) != item["effective_sha256"]:
        raise ValueError("effective preregistration identity changed")
    return path


def validate_historical_identity(prereg: dict[str, Any], root: Path = ROOT) -> None:
    space = prereg["parameter_space"]
    commit = space["implementation_commit"]

    def blob(path):
        return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=root).replace(
            b"\r\n", b"\n"
        )

    for item in space["dependencies"]:
        if hashlib.sha256(blob(item["path"])).hexdigest() != item["sha256"]:
            raise ValueError("historical preregistration dependency identity mismatch")
    strategy = blob(space["strategy_path"])
    digest = hashlib.sha256(strategy)
    if hashlib.sha256(strategy).hexdigest() != space["strategy_sha256"]:
        raise ValueError("historical strategy identity mismatch")
    for item in space["trial_plan"]:
        content = blob(item["config_path"])
        if hashlib.sha256(content).hexdigest() != item["config_sha256"]:
            raise ValueError("historical configuration identity mismatch")
        digest.update(item["trial_id"].encode() + b"\0" + content + b"\0")
    if digest.hexdigest() != prereg["code_config_reference"]:
        raise ValueError("historical combined identity mismatch")


def validate_identity(prereg: dict[str, Any], root: Path = ROOT) -> None:
    experiment_id = prereg["experiment_id"]
    if experiment_id not in SPEC:
        raise ValueError("unallocated WP-004 experiment")
    variant, stem = SPEC[experiment_id]
    space = prereg["parameter_space"]
    config_path = f"research/configs/wp004/{stem}.json"
    config = json.loads((root / config_path).read_text())
    validate_config(config)
    if config["variant"] != variant:
        raise ValueError("experiment maps to a different structural variant")
    expected_plan = [
        {
            "trial_id": f"{variant}:{profile}",
            "config_path": config_path,
            "config_sha256": sha256(root / config_path),
        }
        for profile in PROFILES
    ]
    if (
        space["trial_plan"] != expected_plan
        or prereg["trial_budget"] != 4
        or prereg["seeds"] != [0]
    ):
        raise ValueError("undeclared variant/profile/configuration trial")
    if space["dependencies"] != dependency_manifest(root):
        raise ValueError("implementation dependency identity mismatch")
    strategy_path = root / "backend/app/research/continuation.py"
    if (
        space["strategy_path"] != "backend/app/research/continuation.py"
        or space["strategy_sha256"] != sha256(strategy_path)
        or declared_content_identity(strategy_path, expected_plan)
        != prereg["code_config_reference"]
    ):
        raise ValueError("strategy content identity mismatch")
    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    if space["walk_forward"] != protocol or space["protocol_sha256"] != protocol_hash(protocol):
        raise ValueError("walk-forward freeze mismatch")
    if (
        space["family_id"] != "FAM-BREAKOUT"
        or space["hypothesis_id"] != "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    ):
        raise ValueError("strategy family lineage mismatch")
    if space["primary_family_variant"] != "ALIGNED":
        raise ValueError("primary family hypothesis changed")


def preflight(root: Path = ROOT) -> dict[str, Any]:
    """Must complete before the runner loads development arrays or computes a signal."""
    if git("branch", "--show-current", root=root) != "main":
        raise ValueError("WP-004 must execute on main")
    if git("status", "--porcelain", root=root):
        raise ValueError("commit all scientific declarations before market execution")
    head = git("rev-parse", "HEAD", root=root)
    if not all(ancestor(commit, head, root) for commit in (BASE, DESIGN_COMMIT, PROTOCOL_COMMIT)):
        raise ValueError("required scientific chronology is not in ancestry")
    memory = load_memory(root)
    count = validate_memory(root)
    adaptive = validate_adaptive(root)
    if count["global"]["trials"] != 53 or adaptive["wp004_variants_reserved"] != 3:
        raise ValueError("all three variants must be reserved before any results")
    if count["completed_experiments"] != 6:
        raise ValueError("WP-004 results have already been observed")
    records = {}
    pre_commits = set()
    for experiment_id in SPEC:
        directory = root / "research/experiments" / experiment_id
        if any((directory / name).exists() for name in ("result.json", "trials.json")):
            raise ValueError("WP-004 execution cannot overwrite or repeat an observed trial")
        original_path = f"research/experiments/{experiment_id}/preregistration.json"
        immutable_from_first_commit(original_path, root)
        validate_historical_identity(json.loads((root / original_path).read_text()), root)
        pre_path = effective_preregistration(experiment_id, root).relative_to(root).as_posix()
        prereg = validate_preregistration(root / pre_path)
        validate_identity(prereg, root)
        commit = immutable_from_first_commit(pre_path, root)
        implementation = prereg["parameter_space"]["implementation_commit"]
        if commit == implementation or not ancestor(implementation, commit, root):
            raise ValueError("implementation must be committed before preregistration")
        if implementation == git("rev-parse", DESIGN_COMMIT, root=root) or not ancestor(
            DESIGN_COMMIT, implementation, root
        ):
            raise ValueError("algorithm ranking must precede implementation")
        entry = next(item for item in memory["entries"] if item["experiment_id"] == experiment_id)
        if entry["fingerprint"] != prereg["parameter_space"]["fingerprint"]:
            raise ValueError("registered fingerprint differs from strategy declaration")
        records[experiment_id] = sha256(root / pre_path)
        pre_commits.add(commit)
    if len(pre_commits) != 1:
        raise ValueError("all WP-004 preregistrations must be frozen together")
    if (root / "research/runs/WP-004-ATTEMPT.json").exists():
        raise ValueError("an execution attempt already exists; scientific reruns are not implicit")
    return {
        "status": "PASS",
        "execution_commit": head,
        "preregistration_commit": pre_commits.pop(),
        "preregistration_hashes": records,
        "adaptive_accounting": adaptive,
        "dependency_manifest_sha256": hashlib.sha256(
            json.dumps(dependency_manifest(root), sort_keys=True).encode()
        ).hexdigest(),
    }
