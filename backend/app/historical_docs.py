"""Preserved historical document text (ADR-0053).

ADR-0053 compacted superseded Markdown (archived tasks, superseded contracts and navigation) into
pointers while keeping the pre-cleanup tree recoverable in Git. Validators that bind the text of a
historical record read that preserved revision instead of the live pointer; every other document is
read from the working tree unchanged.
"""

from __future__ import annotations

import subprocess
from functools import cache
from pathlib import Path

PRE_COMPACTION_REVISION = "0038c4d94f5569eb97353137051b7c84744ae9b7"
COMPACTION_REVISION = "7277b3eae140a6a0b2fba7b59c2b1465d9e0eab0"


def historical_text(root: Path, path: str, revision: str = PRE_COMPACTION_REVISION) -> str:
    """The LF-normalized text of `path` at a preserved Git revision."""
    blob = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=root)
    return blob.decode("utf-8").replace("\r\n", "\n")


@cache
def _compacted(root: Path) -> frozenset[str]:
    names = subprocess.check_output(
        ["git", "diff", "--name-only", PRE_COMPACTION_REVISION, COMPACTION_REVISION],
        cwd=root,
        text=True,
    )
    return frozenset(line.strip() for line in names.splitlines() if line.strip())


def compacted(root: Path, path: str) -> bool:
    return path in _compacted(root.resolve())


def document_text(root: Path, path: str) -> str:
    """Current LF text, or the preserved pre-compaction text of an ADR-0053 compacted document."""
    if compacted(root, path):
        return historical_text(root, path)
    return (root / path).read_text(encoding="utf-8").replace("\r\n", "\n")
