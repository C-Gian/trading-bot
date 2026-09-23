"""Canonical text provenance for scientific text dependencies.

A raw SHA-256 of a text file depends on how Git checked it out: with `core.autocrlf` a
Windows working tree holds CRLF bytes while CI holds LF bytes for the very same committed
text. A raw-byte pin taken on one platform therefore fails on the other although nothing
scientific changed.

`CANONICAL_UTF8_LF_TEXT_V1` removes that environment dependence and nothing else:

1. decode the bytes as strict UTF-8 (undecodable bytes fail);
2. replace every CRLF, then every remaining lone CR, with LF;
3. change no other character: no trimming, no trailing-newline repair, no BOM handling;
4. SHA-256 the resulting UTF-8 bytes.

Any non-newline change still changes the digest. The rule applies only where it is
explicitly declared: newly created scientific text dependencies should record
`canonical_text_sha256`, and a historical raw-byte pin is honoured only through a governed
record that preserves the raw digest and declares its canonical equivalent. Binary files,
data objects and undeclared dependencies keep exact raw-byte identity.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

CANONICAL_TEXT_RULE = "CANONICAL_UTF8_LF_TEXT_V1"
RAW_IDENTICAL = "RAW_IDENTICAL"
CANONICAL_TEXT_EQUIVALENT = "CANONICAL_TEXT_EQUIVALENT"


class TextProvenanceError(ValueError):
    """A declared text dependency is not the text its provenance record names."""


def canonical_text_bytes(raw: bytes) -> bytes:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TextProvenanceError("a canonical text dependency must be valid UTF-8") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def canonical_text_sha256(path: Path) -> str:
    return hashlib.sha256(canonical_text_bytes(path.read_bytes())).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_text_dependency(path: Path, declared: Mapping[str, Any]) -> str:
    """Check one declared dependency; return how the current bytes relate to the pin.

    `declared` carries `rule`, the preserved historical `raw_sha256` and the
    `canonical_text_sha256`. The canonical digest must match exactly. The raw digest is
    reported, never required, because checkout line endings may legitimately differ.
    """
    if declared["rule"] != CANONICAL_TEXT_RULE:
        raise TextProvenanceError(f"{path.name}: undeclared text equivalence rule")
    raw = path.read_bytes()
    canonical = hashlib.sha256(canonical_text_bytes(raw)).hexdigest()
    if canonical != declared["canonical_text_sha256"]:
        raise TextProvenanceError(f"{path.name}: canonical text differs from its provenance")
    if hashlib.sha256(raw).hexdigest() == declared["raw_sha256"]:
        return RAW_IDENTICAL
    return CANONICAL_TEXT_EQUIVALENT


__all__ = [
    "CANONICAL_TEXT_EQUIVALENT",
    "CANONICAL_TEXT_RULE",
    "RAW_IDENTICAL",
    "TextProvenanceError",
    "canonical_text_bytes",
    "canonical_text_sha256",
    "raw_sha256",
    "verify_text_dependency",
]
