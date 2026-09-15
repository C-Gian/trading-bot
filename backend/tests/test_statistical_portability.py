from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_statistical_evidence import expected_outputs, json_differences
from scripts.check_numerical_environment import numerical_environment_errors

ROOT = Path(__file__).resolve().parents[2]


def test_numerical_dependency_identity_matches_lock_and_runtime() -> None:
    assert numerical_environment_errors(ROOT) == []


def test_bootstrap_and_ci_cannot_bypass_governed_lock() -> None:
    bootstrap = (ROOT / "scripts/bootstrap.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/check.yml").read_text(encoding="utf-8")
    assert '"pip"' not in bootstrap
    assert '"sync", "--frozen"' in bootstrap
    assert "astral-sh/setup-uv@bec219d24cd3e171d82865faccec33120bb574f4" in workflow
    assert "version: '0.12.10'" in workflow
    assert "uv run --frozen python scripts/check.py --no-data" in workflow


def test_statistical_outputs_are_byte_identical_on_repeated_reconstruction() -> None:
    first = expected_outputs()
    second = expected_outputs()
    assert first == second
    assert all(path.read_bytes() == content for path, content in first.items())


def test_json_differences_identifies_exact_drift_fields_deterministically() -> None:
    actual = {"z": 1, "rows": [{"p": 0.1}], "removed": True}
    expected = {"z": 2, "rows": [{"p": 0.2}], "added": True}
    forward = json_differences(actual, expected)
    reverse_order = json_differences(
        json.loads(json.dumps(actual, sort_keys=True)),
        json.loads(json.dumps(expected, sort_keys=True)),
    )
    assert forward == ["/added", "/removed", "/rows/0/p", "/z"]
    assert reverse_order == forward
