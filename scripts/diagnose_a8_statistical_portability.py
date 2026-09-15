"""Report exact a8 statistical fields changed by the legacy platform-sensitive path."""

from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

from audit_statistical_evidence import json_differences

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_HEAD = "a8e54d472add9d9257e7073c2b6c9258012884c2"
MODULE_PATH = "backend/app/research/statistical_governance.py"
ARTIFACT_PATH = "reports/statistics/STATISTICAL-EVIDENCE-AUDIT-V1.json"


def git_show(path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{REFERENCE_HEAD}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def legacy_reconstruction() -> dict[str, Any]:
    module_name = "a8_statistical_governance"
    module = types.ModuleType(module_name)
    module.__file__ = str(ROOT / MODULE_PATH)
    sys.modules[module_name] = module
    try:
        exec(  # noqa: S102
            compile(git_show(MODULE_PATH), MODULE_PATH, "exec"), module.__dict__
        )
        return module.reconstruct_statistical_evidence(ROOT)
    finally:
        del sys.modules[module_name]


def main() -> int:
    committed = json.loads(git_show(ARTIFACT_PATH))
    regenerated = legacy_reconstruction()
    differences = json_differences(committed, regenerated)
    detail = ", ".join(differences) if differences else "NONE"
    print(f"::notice file={ARTIFACT_PATH}::a8 legacy drift fields: {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
