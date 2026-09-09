from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from app.research.report_guard import (
    ReportGuardError,
    declared_base,
    load_chronology,
    validate_report_bases,
)
from app.research.wp004 import ROOT

WP006_BASE = "444172a359e2663887624da82254cc2185ff85e1"
WP007_BASE = "d92088d5ef0426bf64f34326a3224dd9aba93603"


def _mirror(tmp_path: Path) -> Path:
    """Point the guard at a copied chronology while Git ancestry stays authoritative."""
    (tmp_path / "governance").mkdir(parents=True)
    (tmp_path / "reports/reviews").mkdir(parents=True)
    (tmp_path / "reports/checkpoints").mkdir(parents=True)
    shutil.copy(
        ROOT / "governance/WORK_PACKAGE_CHRONOLOGY.json",
        tmp_path / "governance/WORK_PACKAGE_CHRONOLOGY.json",
    )
    shutil.copy(
        ROOT / "reports/reviews/WP-005-RESEARCH-DIRECTOR-REVIEW.md",
        tmp_path / "reports/reviews/WP-005-RESEARCH-DIRECTOR-REVIEW.md",
    )
    return tmp_path


def _write(root: Path, document: dict) -> None:
    (root / "governance/WORK_PACKAGE_CHRONOLOGY.json").write_text(
        json.dumps(document), encoding="utf-8"
    )


def test_repository_chronology_passes_and_pins_every_enforced_base():
    result = validate_report_bases()
    assert result["status"] == "PASS"
    assert result["base_guard_enforced"] == ["WP-006", "WP-007"]
    assert declared_base("WP-006") == WP006_BASE
    assert declared_base("WP-007") == WP007_BASE
    assert result["documented_reporting_errors"] == [
        {"work_package": "WP-005", "kind": "REPORTED_BASE_HEAD_TYPO"}
    ]


def test_wrong_declared_base_is_rejected(tmp_path: Path):
    root = _mirror(tmp_path)
    document = load_chronology(root)
    document["work_packages"][2]["start_head"] = "3fdeffe5de59ebf3d80dcb70e26fe8dff8a28153"
    _write(root, document)
    (root / "reports/checkpoints/WP-006.md").write_text(
        f"Base reviewed HEAD: `{WP006_BASE}`\n", encoding="utf-8"
    )
    with pytest.raises(ReportGuardError, match="not the declared starting HEAD"):
        validate_report_bases(root)


def test_enforced_checkpoint_must_state_a_base(tmp_path: Path):
    root = _mirror(tmp_path)
    (root / "reports/checkpoints/WP-006.md").write_text("no base claimed\n", encoding="utf-8")
    with pytest.raises(ReportGuardError, match="must state the exact Base reviewed HEAD"):
        validate_report_bases(root)


def test_report_base_typo_must_stay_documented_and_unrewritten(tmp_path: Path):
    root = _mirror(tmp_path)
    review = root / "reports/reviews/WP-005-RESEARCH-DIRECTOR-REVIEW.md"
    review.write_text(
        review.read_text(encoding="utf-8").replace(
            "2b40aa03cfc05ac7f57d269f596f1ebacdc9d356", "REDACTED"
        ),
        encoding="utf-8",
    )
    with pytest.raises(ReportGuardError, match="omits the reported or the true base"):
        validate_report_bases(root)


def test_fabricated_span_is_rejected(tmp_path: Path):
    root = _mirror(tmp_path)
    document = load_chronology(root)
    document["work_packages"][1]["final_head"] = document["work_packages"][1]["start_head"]
    _write(root, document)
    with pytest.raises(ReportGuardError, match="not a real chronological ancestry"):
        validate_report_bases(root)
