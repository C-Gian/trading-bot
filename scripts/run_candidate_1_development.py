"""Candidate #1 Development Lab runner (`research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md`).

Modes:
    --validate  outcome-blind implementation validation record (default; no execution bars)
    --check     replay the implementation validation record
    --execute   the single Development execution; refuses unless state records an explicit
                Research Director execution authorization
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research import candidate_1_development as dev

VALIDATION_PATH = "reports/validation/CANDIDATE-1-DEVELOPMENT-IMPLEMENTATION-V1.json"
MODULE_PATH = "backend/app/research/candidate_1_development.py"
SCRIPT_PATH = "scripts/run_candidate_1_development.py"
TEST_PATH = "backend/tests/test_candidate_1_development.py"


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _finite(value: Any) -> Any:
    """Replace non-finite floats so the record stays strict JSON."""
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_finite(v) for v in value]
    return value


def validation_record() -> dict[str, Any]:
    identity = dev.identity_checks(ROOT)
    replay = subprocess.run(
        [sys.executable, "scripts/audit_candidate_1_frozen_admission.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    episodes, meta = dev.load_admission(ROOT)
    candidates = [e for e in episodes if e.candidate]
    matched = dev.matching(episodes)
    tests = ast.parse((ROOT / TEST_PATH).read_text(encoding="utf-8"))
    names = sorted(
        node.name
        for node in tests.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )
    post_cutoff_exit = sum(e.t + dev.EXIT_OFFSET > dev.DEVELOPMENT_LAST_MINUTE for e in candidates)
    return _finite(
        {
            "version": "CANDIDATE_1_DEVELOPMENT_IMPLEMENTATION_VALIDATION_V1",
            "protocol": dev.PROTOCOL_PATH,
            "protocol_canonical_sha256": dev.PROTOCOL_CANONICAL_SHA256,
            "freeze_decision": dev.ADR_PATH,
            "identity": identity,
            "admission_record": dev.ADMISSION_RECORD_PATH,
            "admission_identity_replay": replay.returncode == 0,
            "population": {
                **meta,
                "consumed_valid_episodes": len(episodes),
                "consumed_candidates": len(candidates),
                "non_overlapping_primary_positions": dev.non_overlapping([e.t for e in candidates]),
                "candidates_with_exit_minute_after_cutoff": post_cutoff_exit,
            },
            "outcome_blind_matching": {
                "pairs": len(matched["pairs"]),
                "coverage": matched["coverage"],
                "blocked_years": matched["blocked_years"],
                "gates": matched["gates"],
                "balance": matched["balance"],
                "years": {
                    year: {
                        key: value[key]
                        for key in ("candidates", "controls", "coverage", "feasible_edges")
                        if key in value
                    }
                    for year, value in matched["years"].items()
                },
                "reads_forward_prices": False,
            },
            "implementation_paths": [MODULE_PATH, SCRIPT_PATH, TEST_PATH],
            "implementation_sha256": {
                path: dev.canonical_text_sha256(ROOT / path)
                for path in (MODULE_PATH, SCRIPT_PATH, TEST_PATH)
            },
            "synthetic_tests": names,
            "execution_price_source": "data/canonical/BTCUSDT-1m.parquet (BTCUSDT-SPOT-1M-DEV-v1)",
            "execution_price_source_read": False,
            "market_outcomes_inspected": False,
            "new_market_data_accessed": False,
            "development_result_created": False,
            "execution_authorized": False,
            "sealed_queries": 0,
        }
    )


def execute() -> None:  # pragma: no cover - authorized run only
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    development = state["governance_transition_v3"]["candidate_1"]["development"]
    if development.get("execution_authorized") is not True:
        raise SystemExit("Candidate #1 Development execution is not authorized")
    result_path = ROOT / dev.RESULT_PATH
    if result_path.exists():
        raise SystemExit("the single Candidate #1 Development execution is already recorded")
    identity = dev.identity_checks(ROOT)
    replay = subprocess.run(
        [sys.executable, "scripts/audit_candidate_1_frozen_admission.py", "--check"],
        cwd=ROOT,
        check=False,
    )
    episodes, _ = dev.load_admission(ROOT)
    result = dev.evaluate(
        episodes,
        dev.canonical_spot_prices(ROOT),
        {**identity, "ADMISSION_REPLAY": replay.returncode == 0},
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(_json(_finite(result)), encoding="utf-8", newline="\n")
    print(f"wrote {dev.RESULT_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--execute", action="store_true")
    options = parser.parse_args()
    if options.execute:
        execute()
        return
    text = _json(validation_record())
    path = ROOT / VALIDATION_PATH
    if options.check:
        if path.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
            raise SystemExit("candidate #1 implementation validation does not replay")
        print("candidate #1 implementation validation replay: PASS")
        return
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {VALIDATION_PATH}")


if __name__ == "__main__":
    main()
