from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import jsonschema

R = Path(__file__).resolve().parents[1]


def run(cmd, cwd=R):
    subprocess.run(cmd, cwd=cwd, check=True, shell=sys.platform == "win32" and cmd[0] == "npm")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--no-data", action="store_true")
    o = a.parse_args()
    required = [
        "governance/SCIENTIFIC_CONSTITUTION.md",
        "state/current_state.json",
        "decisions/ADR-0001-HISTORICAL-DEVELOPMENT-BOUNDARY.md",
        "backend/app/main.py",
        "frontend/src/main.tsx",
    ]
    assert all((R / p).exists() for p in required)
    state = json.loads((R / "state/current_state.json").read_text())
    schema = json.loads((R / "contracts/project_state.schema.json").read_text())
    jsonschema.validate(state, schema)
    assert state["real_money_authorized"] is False and state["experiments_completed"] == 0
    assert (R / "governance/SCIENTIFIC_CONSTITUTION.md").read_bytes() == (
        subprocess.check_output(["git", "show", "main:SCIENTIFIC_CONSTITUTION.md"], cwd=R)
    )
    run([sys.executable, "-m", "ruff", "check", "backend", "scripts"])
    run([sys.executable, "-m", "mypy", "backend"])
    run([sys.executable, "-m", "pytest", "-q"])
    run(["npm", "run", "lint"], R / "frontend")
    run(["npm", "run", "test"], R / "frontend")
    run(["npm", "run", "build"], R / "frontend")
    if not o.no_data:
        m = json.loads((R / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json").read_text())
        jsonschema.validate(
            m, json.loads((R / "contracts/dataset_manifest.schema.json").read_text())
        )
        assert (
            m["coverage"]["end"] <= "2024-12-31T23:59:00Z"
            and m["integrity"]["duplicates"] == 0
            and m["integrity"]["invalid_ohlcv"] == 0
        )

        def digest(path: Path) -> str:
            h = hashlib.sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    h.update(block)
            return h.hexdigest()

        for record in [*m["source"]["raw_objects"], *m["files"].values()]:
            assert digest(R / record["path"]) == record["sha256"]
        import pyarrow.parquet as pq

        maximum_us = pq.read_table(
            R / m["files"]["canonical"]["path"], columns=["open_time"]
        )["open_time"][-1].value
        assert maximum_us <= 1_735_689_540_000_000
    print("WP-001 deterministic validation: PASS")


if __name__ == "__main__":
    main()
