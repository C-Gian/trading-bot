"""Authoritative work-package base identity; reports cannot claim a different base.

The chronology file is the single source of truth for each work package's starting
and final HEAD. Historical reports are never rewritten: a known reporting error is
recorded as a documented exception and its original text stays preserved.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .wp004 import ROOT, ancestor, git

CHRONOLOGY_PATH = Path("governance/WORK_PACKAGE_CHRONOLOGY.json")
BASE_CLAIM = re.compile(r"Base reviewed HEAD:\s*`?([0-9a-f]{7,40})`?")
SHA = re.compile(r"^[0-9a-f]{40}$")


class ReportGuardError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReportGuardError(message)


def load_chronology(root: Path = ROOT) -> dict[str, Any]:
    document = json.loads((root / CHRONOLOGY_PATH).read_text(encoding="utf-8"))
    _require(document["schema_version"] == 1, "unknown work-package chronology version")
    return document


def declared_base(work_package: str, root: Path = ROOT) -> str:
    for item in load_chronology(root)["work_packages"]:
        if item["work_package"] == work_package:
            return str(item["start_head"])
    raise ReportGuardError(f"work package has no declared base: {work_package}")


def _claims(text: str) -> list[str]:
    return BASE_CLAIM.findall(text.replace("\r\n", "\n"))


def validate_report_bases(root: Path = ROOT, *, repo: Path | None = None) -> dict[str, Any]:
    """Fail closed if any enforced report claims a base other than its declared HEAD.

    ``root`` locates the declaration and report files; ``repo`` is the Git repository
    whose real ancestry decides every commit claim.
    """
    document = load_chronology(root)
    repo = repo if repo is not None else ROOT
    head = git("rev-parse", "HEAD", root=repo)
    enforced: list[str] = []
    documented_errors: list[dict[str, Any]] = []
    for item in document["work_packages"]:
        work_package = item["work_package"]
        start, final = item["start_head"], item["final_head"]
        _require(bool(SHA.match(start)), f"{work_package} start HEAD is not a full SHA-256 commit")
        _require(ancestor(start, head, repo), f"{work_package} start HEAD is not in ancestry")
        if final is not None:
            _require(bool(SHA.match(final)), f"{work_package} final HEAD is not a full commit")
            _require(
                start != final and ancestor(start, final, repo) and ancestor(final, head, repo),
                f"{work_package} declared span is not a real chronological ancestry",
            )
        error = item["documented_reporting_error"]
        if error is not None:
            _require(
                error["true_value"] == start and error["reported_value"] != start,
                f"{work_package} documented reporting error does not match its declared base",
            )
            recorded = root / error["recorded_in"]
            _require(recorded.is_file(), f"{work_package} reporting error is not recorded")
            text = recorded.read_text(encoding="utf-8")
            _require(
                error["reported_value"] in text and error["true_value"] in text,
                f"{work_package} reporting error record omits the reported or the true base",
            )
            documented_errors.append({"work_package": work_package, "kind": error["kind"]})
        if not item["base_guard_enforced"]:
            continue
        enforced.append(work_package)
        checkpoint = f"reports/checkpoints/{work_package}.md"
        for relative in (checkpoint, f"reports/reviews/{work_package}-RESEARCH-DIRECTOR-REVIEW.md"):
            path = root / relative
            if not path.is_file():
                continue
            claimed = _claims(path.read_text(encoding="utf-8"))
            _require(
                relative != checkpoint or bool(claimed),
                f"{relative} must state the exact Base reviewed HEAD",
            )
            for value in claimed:
                _require(
                    start.startswith(value),
                    f"{relative} claims a base HEAD that is not the declared starting HEAD",
                )
    return {
        "status": "PASS",
        "work_packages": len(document["work_packages"]),
        "base_guard_enforced": enforced,
        "documented_reporting_errors": documented_errors,
    }
