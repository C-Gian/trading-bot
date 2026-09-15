"""Verify the governed numerical dependency identity used by statistical audits."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "governance/NUMERICAL_DEPENDENCY_IDENTITY_V1.json"


def numerical_environment_errors(root: Path = ROOT) -> list[str]:
    policy = json.loads((root / POLICY_PATH.relative_to(ROOT)).read_text(encoding="utf-8"))
    errors: list[str] = []
    actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual_python != policy["python_major_minor"]:
        errors.append(f"python={actual_python}, governed={policy['python_major_minor']}")

    lock_path = root / policy["lockfile"]
    actual_lock_hash = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    if actual_lock_hash != policy["lockfile_sha256"]:
        errors.append(f"uv.lock sha256={actual_lock_hash}, governed={policy['lockfile_sha256']}")

    for distribution, governed_version in sorted(policy["numerical_packages"].items()):
        try:
            actual_version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            errors.append(f"{distribution}=NOT_INSTALLED, governed={governed_version}")
            continue
        if actual_version != governed_version:
            errors.append(f"{distribution}={actual_version}, governed={governed_version}")
    return errors


def main() -> int:
    errors = numerical_environment_errors()
    if errors:
        raise SystemExit("numerical dependency identity mismatch: " + "; ".join(errors))
    print("numerical dependency identity: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
