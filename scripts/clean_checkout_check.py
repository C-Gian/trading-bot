from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="trading-bot-clean-") as temporary:
        checkout = Path(temporary) / "checkout"
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(checkout), "HEAD"], cwd=ROOT, check=True
        )
        try:
            env = os.environ.copy()
            uv = ROOT / ".tools/uv/uv.exe"
            if uv.is_file():
                env["UV_EXE"] = str(uv)
            env["CLEAN_CHECKOUT"] = "1"
            subprocess.run(
                [sys.executable, "scripts/bootstrap.py"], cwd=checkout, env=env, check=True
            )
            python = checkout / (
                ".venv/Scripts/python.exe" if sys.platform == "win32" else ".venv/bin/python"
            )
            state = json.loads((checkout / "state/current_state.json").read_text(encoding="utf-8"))
            command = [str(python), "scripts/check.py", "--no-data"]
            if state["experiments_completed"] == 0:
                command.append("--pre-experiment")
            subprocess.run(
                command,
                cwd=checkout,
                env=env,
                check=True,
            )
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(checkout)], cwd=ROOT, check=True
            )
    print("Clean-checkout bootstrap and no-data validation: PASS")


if __name__ == "__main__":
    main()
