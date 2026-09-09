"""Repository-layer sealed isolation.

Honest limitation: this is application and repository isolation, not operating-system
secrecy. It guarantees that ordinary development code paths refuse to open a sealed
location and that the approved development manifest cannot reference one. It does not
prevent a privileged operator from reading files directly.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

ROOT = Path(__file__).resolve().parents[3]
SEALED_ROOTS = ("data/sealed", "research/sealed/datasets")


class SealedAccessDenied(PermissionError):
    """An ordinary development code path attempted to reach a sealed location."""


def _relative(path: Path | str, root: Path) -> PurePosixPath:
    candidate = Path(path)
    resolved = candidate if candidate.is_absolute() else root / candidate
    try:
        return PurePosixPath(resolved.resolve().relative_to(root.resolve()).as_posix())
    except ValueError:
        return PurePosixPath(resolved.as_posix())


def is_sealed_path(path: Path | str, root: Path = ROOT) -> bool:
    """True for any path inside a registered sealed root, symlinks and ``..`` resolved."""
    relative = _relative(path, root)
    return any(
        relative == PurePosixPath(sealed) or PurePosixPath(sealed) in relative.parents
        for sealed in SEALED_ROOTS
    )


def development_open(path: Path | str, root: Path = ROOT) -> BinaryIO:
    """The only sanctioned development file opener; it can never reach sealed data."""
    if is_sealed_path(path, root):
        raise SealedAccessDenied(f"development loader may not open a sealed path: {path}")
    candidate = Path(path)
    return (candidate if candidate.is_absolute() else root / candidate).open("rb")


def manifest_is_development_only(manifest: dict[str, Any], root: Path = ROOT) -> bool:
    """A development manifest must not reference any sealed location."""
    paths = [item["path"] for item in manifest.get("files", {}).values()]
    paths += [item["path"] for item in manifest.get("source", {}).get("raw_objects", [])]
    return bool(paths) and not any(is_sealed_path(item, root) for item in paths)
