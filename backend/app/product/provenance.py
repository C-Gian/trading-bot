"""Deterministic BUILD_PROVENANCE_V1 identity for automated prospective evidence.

A scientific build is not identified by ``git rev-parse HEAD`` alone.  A commit says
nothing about whether the working tree that actually produced an observation matched it,
so this module hashes the exact bytes of the semantic sources the observer depends on and
binds them to the repository state.  A prospective decision may only be recorded under a
verified build.
"""

from __future__ import annotations

import hashlib
import inspect
import subprocess
import sys
from pathlib import Path
from typing import Any, Protocol

from .. import __version__
from ..backtest import COST_VERSION
from ..backtest.models import CostModel
from .analysis import STRATEGY_VERSION
from .execution_v2 import PAPER_EXECUTION_VERSION

ROOT = Path(__file__).resolve().parents[3]

PROVENANCE_VERSION = "BUILD_PROVENANCE_V1"
UNVERIFIED_REASON = "UNVERIFIED_SCIENTIFIC_BUILD"

# Semantic sources whose exact bytes define the observer's scientific behaviour.  The
# cost implementation is resolved from the objects the observer actually imports rather
# than from a hand-written path, so the manifest cannot drift from repository truth.
_DECLARED_MANIFEST_MEMBERS = (
    "backend/app/product/shadow_observer.py",
    "backend/app/product/analysis.py",
    "backend/app/research/continuation.py",
    "backend/app/product/execution_v2.py",
)


class ProvenanceError(RuntimeError):
    """The scientific build identity cannot be computed."""


class ProvenanceProvider(Protocol):
    """Seam allowing tests to inject a synthetic verified or unverified build."""

    def __call__(self) -> dict[str, Any]: ...


def _repository_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def cost_source_members() -> tuple[str, ...]:
    """Resolve the governed cost implementation deterministically from live objects."""
    members: list[str] = []
    for obj in (CostModel, inspect.getmodule(CostModel)):
        source = inspect.getsourcefile(obj) if obj is not None else None
        if source is None:
            raise ProvenanceError("the governed cost implementation has no source file")
        relative = _repository_relative(Path(source))
        if relative not in members:
            members.append(relative)
    # ``COST_VERSION`` is declared by the backtest package itself, so a version change must
    # also move the identity.  Resolve that package through the import system rather than
    # by constructing a path.
    module = inspect.getmodule(CostModel)
    package = sys.modules.get(module.__package__) if module and module.__package__ else None
    package_source = inspect.getsourcefile(package) if package is not None else None
    if package_source is None:
        raise ProvenanceError("the governed cost package has no source file")
    relative = _repository_relative(Path(package_source))
    if relative not in members:
        members.append(relative)
    return tuple(members)


def manifest_members(contract_path: str) -> tuple[str, ...]:
    """Every semantic source bound into the evidence identity, in a stable order."""
    members = [*_DECLARED_MANIFEST_MEMBERS, *cost_source_members(), contract_path]
    seen: list[str] = []
    for member in members:
        if member not in seen:
            seen.append(member)
    return tuple(seen)


def semantic_manifest(contract_path: str) -> dict[str, str]:
    """Hash the exact bytes of each semantic source."""
    manifest: dict[str, str] = {}
    for member in manifest_members(contract_path):
        path = ROOT / member
        if not path.is_file():
            raise ProvenanceError(f"semantic manifest member is missing: {member}")
        manifest[member] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def aggregate_sha256(manifest: dict[str, str]) -> str:
    """Bind the whole manifest into one deterministic aggregate identity."""
    payload = "\n".join(f"{member}:{digest}" for member, digest in sorted(manifest.items()))
    return hashlib.sha256(f"{PROVENANCE_VERSION}\n{payload}\n".encode()).hexdigest()


def _git(*arguments: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *arguments], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def repository_provenance(
    *, observer_version: str, evidence_version: str, contract_path: str
) -> dict[str, Any]:
    """Capture the running build identity and decide whether it is scientifically usable."""
    head = _git("rev-parse", "HEAD")
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    status = _git("status", "--porcelain")
    worktree_clean = status == ""
    try:
        manifest = semantic_manifest(contract_path)
        aggregate = aggregate_sha256(manifest)
    except ProvenanceError:
        manifest, aggregate = {}, None

    verified = bool(head) and worktree_clean and aggregate is not None
    return {
        "provenance_version": PROVENANCE_VERSION,
        "verified": verified,
        "unverified_reason": None if verified else UNVERIFIED_REASON,
        "git_head": head,
        "git_branch": branch if branch not in {None, "HEAD"} else None,
        "worktree_clean": worktree_clean,
        "application_version": __version__,
        "observer_version": observer_version,
        "evidence_version": evidence_version,
        "strategy_version": STRATEGY_VERSION,
        "execution_version": PAPER_EXECUTION_VERSION,
        "cost_model_version": COST_VERSION,
        "semantic_manifest": manifest,
        "semantic_manifest_sha256": aggregate,
    }


def provenance_identity(provenance: dict[str, Any]) -> str:
    """The short identity recorded on every individual scientific record."""
    aggregate = provenance.get("semantic_manifest_sha256")
    if not isinstance(aggregate, str):
        raise ProvenanceError("provenance has no semantic manifest identity")
    return aggregate


def validate(provenance: dict[str, Any]) -> None:
    """Reject a provenance block that cannot support a genuine observation."""
    if provenance.get("provenance_version") != PROVENANCE_VERSION:
        raise ProvenanceError("unsupported build provenance version")
    if provenance.get("verified") is not True:
        raise ProvenanceError(str(provenance.get("unverified_reason") or UNVERIFIED_REASON))
    if not isinstance(provenance.get("git_head"), str) or not provenance["git_head"]:
        raise ProvenanceError("a verified build must record its git HEAD")
    if provenance.get("worktree_clean") is not True:
        raise ProvenanceError(UNVERIFIED_REASON)
    manifest = provenance.get("semantic_manifest")
    if not isinstance(manifest, dict) or not manifest:
        raise ProvenanceError("a verified build must record its semantic manifest")
    if aggregate_sha256(manifest) != provenance.get("semantic_manifest_sha256"):
        raise ProvenanceError("semantic manifest does not match its aggregate identity")


__all__ = [
    "PROVENANCE_VERSION",
    "UNVERIFIED_REASON",
    "ProvenanceError",
    "ProvenanceProvider",
    "aggregate_sha256",
    "cost_source_members",
    "manifest_members",
    "provenance_identity",
    "repository_provenance",
    "semantic_manifest",
    "validate",
]
