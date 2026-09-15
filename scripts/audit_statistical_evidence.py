"""Generate or verify the deterministic P0 statistical-governance artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.research.statistical_governance import (
    build_aligned_provenance_audit,
    build_repository_ledger,
    json_bytes,
    reconstruct_statistical_evidence,
    render_ledger_markdown,
    render_provenance_markdown,
    render_statistics_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = {
    "ledger_json": ROOT / "reports/statistics/MATERIAL-HYPOTHESIS-LEDGER-V1.json",
    "ledger_md": ROOT / "reports/statistics/MATERIAL-HYPOTHESIS-LEDGER-V1.md",
    "provenance_json": ROOT / "reports/statistics/ALIGNED-CONSTANT-PROVENANCE-V1.json",
    "provenance_md": ROOT / "reports/statistics/ALIGNED-CONSTANT-PROVENANCE-V1.md",
    "statistics_json": ROOT / "reports/statistics/STATISTICAL-EVIDENCE-AUDIT-V1.json",
    "statistics_md": ROOT / "reports/statistics/STATISTICAL-EVIDENCE-AUDIT-V1.md",
}


def json_differences(actual: Any, expected: Any, pointer: str = "") -> list[str]:
    """Return deterministic JSON pointers whose scalar/type values differ."""
    if type(actual) is not type(expected):
        return [pointer or "/"]
    if isinstance(actual, dict):
        differences: list[str] = []
        for key in sorted(set(actual) | set(expected)):
            child = f"{pointer}/{key.replace('~', '~0').replace('/', '~1')}"
            if key not in actual or key not in expected:
                differences.append(child)
            else:
                differences.extend(json_differences(actual[key], expected[key], child))
        return differences
    if isinstance(actual, list):
        differences = []
        if len(actual) != len(expected):
            differences.append(f"{pointer}/length")
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected, strict=False)):
            differences.extend(json_differences(actual_item, expected_item, f"{pointer}/{index}"))
        return differences
    return [] if actual == expected else [pointer or "/"]


def drift_details(path: Path, expected: bytes) -> str:
    if not path.is_file():
        return "missing"
    if path.suffix == ".json":
        try:
            actual_value = json.loads(path.read_text(encoding="utf-8"))
            expected_value = json.loads(expected.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return "invalid JSON"
        pointers = json_differences(actual_value, expected_value)
        return ", ".join(pointers) if pointers else "byte encoding/newline only"
    actual_lines = path.read_text(encoding="utf-8").splitlines()
    expected_lines = expected.decode("utf-8").splitlines()
    changed = [
        str(index + 1)
        for index, pair in enumerate(zip(actual_lines, expected_lines, strict=False))
        if pair[0] != pair[1]
    ]
    if len(actual_lines) != len(expected_lines):
        changed.append("line-count")
    return "lines " + ", ".join(changed[:40])


def expected_outputs() -> dict[Path, bytes]:
    ledger = build_repository_ledger(ROOT)
    provenance = build_aligned_provenance_audit()
    statistics = reconstruct_statistical_evidence(ROOT)
    return {
        OUTPUTS["ledger_json"]: json_bytes(ledger),
        OUTPUTS["ledger_md"]: render_ledger_markdown(ledger).encode("utf-8"),
        OUTPUTS["provenance_json"]: json_bytes(provenance),
        OUTPUTS["provenance_md"]: render_provenance_markdown(provenance).encode("utf-8"),
        OUTPUTS["statistics_json"]: json_bytes(statistics),
        OUTPUTS["statistics_md"]: render_statistics_markdown(statistics).encode("utf-8"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if committed outputs drift")
    args = parser.parse_args()
    expected = expected_outputs()
    if args.check:
        drift = [
            path
            for path, content in expected.items()
            if not path.is_file() or path.read_bytes() != content
        ]
        if drift:
            for path in drift:
                relative = path.relative_to(ROOT).as_posix()
                print(f"::error file={relative}::{drift_details(path, expected[path])}")
            raise SystemExit("statistical audit drift: " + ", ".join(str(path) for path in drift))
        print("statistical audit: PASS")
        return 0
    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print("statistical audit artifacts generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
