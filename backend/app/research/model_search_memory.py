"""Prospective supervised-model fingerprints for SEARCH_MEMORY_V2."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from .search_memory import SearchMemoryError
from .search_memory_v2 import DependencyIdentity


def _canonical(value: Any, *, mask_numbers: bool = False) -> Any:
    if isinstance(value, dict):
        return {key: _canonical(value[key], mask_numbers=mask_numbers) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical(item, mask_numbers=mask_numbers) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise SearchMemoryError("model specs cannot contain non-finite values")
        return "<NUMBER>" if mask_numbers else int(value) if value == int(value) else value
    return value


def _hash(value: Any, *, mask_numbers: bool = False) -> str:
    payload = json.dumps(
        _canonical(value, mask_numbers=mask_numbers),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class ExecutableModelSpec:
    schema_version: int
    root_family: str
    family: str
    algorithm: str
    label: Mapping[str, Any]
    features: tuple[Mapping[str, Any], ...]
    train_window_rule: Mapping[str, Any]
    scaling: Mapping[str, Any]
    regularization: Mapping[str, Any]
    hyperparameters: Mapping[str, Any]
    signal_rule: Mapping[str, Any]
    execution_geometry: Mapping[str, Any]
    dataset: Mapping[str, str]
    cost_model_reference: str
    execution_model_reference: str
    implementation_dependencies: tuple[DependencyIdentity, ...]
    config_dependencies: tuple[DependencyIdentity, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 2 or self.family != self.root_family or not self.features:
            raise SearchMemoryError("invalid SEARCH_MEMORY_V2 supervised model identity")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutableModelBinding:
    spec: ExecutableModelSpec
    fingerprint: Mapping[str, Any]
    behavior_hash: str
    structural_hash: str
    executable_spec_hash: str
    dependency_hash: str


def model_fingerprint(spec: ExecutableModelSpec) -> dict[str, Any]:
    payload = spec.to_dict()
    return {
        key: payload[key]
        for key in (
            "algorithm",
            "label",
            "features",
            "train_window_rule",
            "scaling",
            "regularization",
            "hyperparameters",
            "signal_rule",
            "execution_geometry",
            "dataset",
            "cost_model_reference",
            "execution_model_reference",
        )
    }


def bind_model_spec(
    spec: ExecutableModelSpec,
    *,
    declared_fingerprint: Mapping[str, Any] | None = None,
) -> ExecutableModelBinding:
    fingerprint = model_fingerprint(spec)
    if declared_fingerprint is not None and _canonical(declared_fingerprint) != _canonical(
        fingerprint
    ):
        raise SearchMemoryError("declared model fingerprint differs from executable spec")
    dependency_hash = _hash(
        {
            "implementation": spec.to_dict()["implementation_dependencies"],
            "config": spec.to_dict()["config_dependencies"],
        }
    )
    return ExecutableModelBinding(
        spec,
        fingerprint,
        _hash(fingerprint),
        _hash(fingerprint, mask_numbers=True),
        _hash(spec.to_dict()),
        dependency_hash,
    )


def admit_model_spec(
    spec: ExecutableModelSpec,
    *,
    declared_family: str,
    signatures: list[dict[str, Any]],
    aliases: Mapping[str, str],
    declared_fingerprint: Mapping[str, Any] | None = None,
    family_budget_remaining: bool = True,
) -> dict[str, Any]:
    binding = bind_model_spec(spec, declared_fingerprint=declared_fingerprint)
    exact = [item for item in signatures if item["behavior_hash"] == binding.behavior_hash]
    numeric = [
        item
        for item in signatures
        if item["root_family"] == spec.root_family
        and item["structural_hash"] == binding.structural_hash
    ]
    related = [item for item in signatures if item["root_family"] == spec.root_family]
    if exact:
        classification, matches = "DUPLICATE", exact
    elif numeric:
        classification, matches = "PARAMETER_VARIANT", numeric
    elif related:
        classification, matches = "DESCENDANT_MECHANISM_CHANGE", related
    else:
        classification, matches = "NEW_FAMILY", []
    resolved = aliases.get(declared_family, declared_family)
    if classification in {"DUPLICATE", "PARAMETER_VARIANT"}:
        raise SearchMemoryError(f"{classification}: supervised behavior already registered")
    if resolved != spec.root_family or spec.family != spec.root_family:
        raise SearchMemoryError("family alias/conflict cannot reset canonical root budget")
    if not family_budget_remaining:
        raise SearchMemoryError("canonical root family budget exhausted")
    return {
        "classification": classification,
        "root_family": spec.root_family,
        "matched_experiment_ids": sorted(item["experiment_id"] for item in matches),
        "behavior_hash": binding.behavior_hash,
        "structural_hash": binding.structural_hash,
        "executable_spec_hash": binding.executable_spec_hash,
        "dependency_hash": binding.dependency_hash,
        "admitted": True,
    }
