"""SEALED_EVALUATION_V1: locked, budgeted, preregistered sealed evaluation.

The package contains no reserved market data and cannot acquire any. It exposes a
bounded evaluator, not a sealed-data browser.
"""

from .evaluator import (
    SealedAccessDenied,
    SealedEvaluationError,
    SealedEvaluator,
    canonical_hash,
    load_budget,
    public_status,
)
from .isolation import (
    SEALED_ROOTS,
    development_open,
    is_sealed_path,
    manifest_is_development_only,
)

VERSION = "SEALED_EVALUATION_V1"

__all__ = [
    "SEALED_ROOTS",
    "VERSION",
    "SealedAccessDenied",
    "SealedEvaluationError",
    "SealedEvaluator",
    "canonical_hash",
    "development_open",
    "is_sealed_path",
    "load_budget",
    "manifest_is_development_only",
    "public_status",
]
