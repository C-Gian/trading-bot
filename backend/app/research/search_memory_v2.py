"""SEARCH_MEMORY_V2 executable-spec binding for future material research.

This module governs declared specifications. It does not claim semantic equivalence
for arbitrary Python and does not retroactively reinterpret V1 evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .search_memory import SearchMemoryError, accounting, load_memory, text_sha256

ROOT = Path(__file__).resolve().parents[3]
ENVIRONMENT_FIELDS = {"dataset", "cost_model_reference", "execution_model_reference"}


def _canonical(value: Any, *, mask_numbers: bool = False) -> Any:
    if isinstance(value, dict):
        return {
            key: _canonical(value[key], mask_numbers=mask_numbers) for key in sorted(value)
        }
    if isinstance(value, (tuple, list)):
        return [_canonical(item, mask_numbers=mask_numbers) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise SearchMemoryError("executable specs cannot contain non-finite values")
        if mask_numbers:
            return "<NUMBER>"
        return int(value) if value == int(value) else value
    return value


def _hash(value: Any, *, mask_numbers: bool = False) -> str:
    payload = json.dumps(
        _canonical(value, mask_numbers=mask_numbers),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class NumericTerm:
    name: str
    value: int | float
    unit: str


@dataclass(frozen=True)
class FeaturePrimitive:
    name: str
    transformation: str
    timeframe_minutes: int
    lookback: NumericTerm | None = None


@dataclass(frozen=True)
class Comparison:
    left: str
    operator: str
    right: str
    threshold: NumericTerm | None = None


@dataclass(frozen=True)
class Rule:
    family: str
    value: NumericTerm | None = None
    detail: str = ""


@dataclass(frozen=True)
class DependencyIdentity:
    path: str
    sha256: str

    def __post_init__(self) -> None:
        if Path(self.path).is_absolute() or ".." in Path(self.path).parts:
            raise SearchMemoryError("dependency path must stay inside the repository")
        if len(self.sha256) != 64 or any(char not in "0123456789abcdef" for char in self.sha256):
            raise SearchMemoryError("dependency SHA-256 is invalid")


@dataclass(frozen=True)
class ExecutableStrategySpec:
    schema_version: int
    root_family: str
    family: str
    entry_event: str
    feature_primitives: tuple[FeaturePrimitive, ...]
    comparisons: tuple[Comparison, ...]
    numeric_parameters: tuple[NumericTerm, ...]
    regime_gates: tuple[str, ...]
    confirmation_gates: tuple[str, ...]
    signal_timeframe_minutes: int
    context_timeframe_minutes: int
    direction: str
    reference_price_rule: str
    stop: Rule
    exit: Rule
    holding_horizon_minutes: int | None
    timing_perturbation: str
    position_policy: str
    execution_model_reference: str
    cost_model_reference: str
    dataset: Mapping[str, str]
    implementation_dependencies: tuple[DependencyIdentity, ...]
    config_dependencies: tuple[DependencyIdentity, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 2:
            raise SearchMemoryError("missing SEARCH_MEMORY_V2 executable spec identity")
        if self.direction not in {"LONG", "NO_TRADE"}:
            raise SearchMemoryError("unsupported governed direction")
        if self.signal_timeframe_minutes <= 0 or self.context_timeframe_minutes < 0:
            raise SearchMemoryError("invalid governed time scale")
        if self.holding_horizon_minutes is not None and not 1 <= self.holding_horizon_minutes <= 1440:
            raise SearchMemoryError("holding horizon is outside governance")
        names = [item.name for item in self.numeric_parameters]
        if len(names) != len(set(names)):
            raise SearchMemoryError("duplicate numeric parameter name")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutableBinding:
    spec: ExecutableStrategySpec
    fingerprint: Mapping[str, Any]
    behavior_hash: str
    structural_hash: str
    executable_spec_hash: str
    dependency_hash: str


def derived_fingerprint(spec: ExecutableStrategySpec) -> dict[str, Any]:
    """Derive governance identity only from the runner's typed executable spec."""
    payload = spec.to_dict()
    return {
        key: payload[key]
        for key in (
            "entry_event",
            "feature_primitives",
            "comparisons",
            "numeric_parameters",
            "regime_gates",
            "confirmation_gates",
            "signal_timeframe_minutes",
            "context_timeframe_minutes",
            "direction",
            "reference_price_rule",
            "stop",
            "exit",
            "holding_horizon_minutes",
            "timing_perturbation",
            "position_policy",
            "execution_model_reference",
            "cost_model_reference",
            "dataset",
        )
    }


def _behavior(fingerprint: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in fingerprint.items() if key not in ENVIRONMENT_FIELDS}


def bind_executable_spec(
    spec: ExecutableStrategySpec | None,
    *,
    declared_fingerprint: Mapping[str, Any] | None = None,
    declared_behavior_hash: str | None = None,
    runtime_spec: ExecutableStrategySpec | None = None,
) -> ExecutableBinding:
    if spec is None:
        raise SearchMemoryError("executable spec identity is missing")
    fingerprint = derived_fingerprint(spec)
    if declared_fingerprint is not None and _canonical(declared_fingerprint) != _canonical(
        fingerprint
    ):
        raise SearchMemoryError("declared fingerprint differs from executable spec")
    behavior_hash = _hash(_behavior(fingerprint))
    if declared_behavior_hash is not None and declared_behavior_hash != behavior_hash:
        raise SearchMemoryError("caller-supplied behavior hash differs from executable spec")
    spec_hash = _hash(spec.to_dict())
    if runtime_spec is not None and _hash(runtime_spec.to_dict()) != spec_hash:
        raise SearchMemoryError("runner executable spec differs from admitted spec")
    dependency_hash = _hash(
        {
            "implementation": spec.to_dict()["implementation_dependencies"],
            "config": spec.to_dict()["config_dependencies"],
        }
    )
    return ExecutableBinding(
        spec=spec,
        fingerprint=fingerprint,
        behavior_hash=behavior_hash,
        structural_hash=_hash(_behavior(fingerprint), mask_numbers=True),
        executable_spec_hash=spec_hash,
        dependency_hash=dependency_hash,
    )


def classify_bound_spec(
    binding: ExecutableBinding,
    signatures: list[dict[str, Any]],
) -> dict[str, Any]:
    exact = [item for item in signatures if item["behavior_hash"] == binding.behavior_hash]
    if exact:
        classification = "DUPLICATE"
        matches = exact
    else:
        numeric = [
            item
            for item in signatures
            if item["root_family"] == binding.spec.root_family
            and item["structural_hash"] == binding.structural_hash
        ]
        if numeric:
            classification, matches = "PARAMETER_VARIANT", numeric
        else:
            related = [
                item for item in signatures if item["root_family"] == binding.spec.root_family
            ]
            classification = "DESCENDANT_MECHANISM_CHANGE" if related else "NEW_FAMILY"
            matches = related
    return {
        "classification": classification,
        "root_family": binding.spec.root_family,
        "matched_experiment_ids": sorted(item["experiment_id"] for item in matches),
        "behavior_hash": binding.behavior_hash,
        "structural_hash": binding.structural_hash,
        "executable_spec_hash": binding.executable_spec_hash,
        "dependency_hash": binding.dependency_hash,
    }


def admit_executable_spec(
    spec: ExecutableStrategySpec | None,
    *,
    declared_family: str,
    declared_fingerprint: Mapping[str, Any] | None,
    signatures: list[dict[str, Any]],
    aliases: Mapping[str, str],
    declared_behavior_hash: str | None = None,
    runtime_spec: ExecutableStrategySpec | None = None,
    family_budget_remaining: bool = True,
) -> dict[str, Any]:
    binding = bind_executable_spec(
        spec,
        declared_fingerprint=declared_fingerprint,
        declared_behavior_hash=declared_behavior_hash,
        runtime_spec=runtime_spec,
    )
    decision = classify_bound_spec(binding, signatures)
    resolved = aliases.get(declared_family, declared_family)
    if decision["classification"] == "DUPLICATE":
        raise SearchMemoryError("DUPLICATE: executable behavior already registered")
    if resolved != spec.root_family or spec.family != spec.root_family:
        raise SearchMemoryError("family alias/conflict cannot reset canonical root budget")
    if not family_budget_remaining:
        raise SearchMemoryError("canonical root family budget exhausted")
    return {**decision, "admitted": True}


def _legacy_spec(entry: dict[str, Any]) -> ExecutableStrategySpec:
    fingerprint = entry["fingerprint"]
    parameters = tuple(
        NumericTerm(name, value, "DECLARED_V1_UNIT")
        for name, value in sorted(fingerprint["parameters"].items())
    )
    transformations = list(fingerprint["feature_transformations"])
    primitives = tuple(
        FeaturePrimitive(
            name,
            transformations[index] if index < len(transformations) else "NONE",
            fingerprint["context_minutes"]
            if "PERSISTENCE" in name or "REGIME" in name
            else fingerprint["signal_minutes"],
        )
        for index, name in enumerate(fingerprint["feature_families"])
    )
    return ExecutableStrategySpec(
        schema_version=2,
        root_family=entry["family_id"],
        family=entry["family_id"],
        entry_event=fingerprint["entry_event"],
        feature_primitives=primitives,
        comparisons=(Comparison("LEGACY_LEFT", "LEGACY_DECLARED_COMPARISON", "LEGACY_RIGHT"),),
        numeric_parameters=parameters,
        regime_gates=()
        if fingerprint["regime_filter"] == "NONE"
        else (fingerprint["regime_filter"],),
        confirmation_gates=()
        if fingerprint["confirmation_filter"] == "NONE"
        else (fingerprint["confirmation_filter"],),
        signal_timeframe_minutes=fingerprint["signal_minutes"],
        context_timeframe_minutes=fingerprint["context_minutes"],
        direction=fingerprint["direction"],
        reference_price_rule="FROZEN_LEGACY_V1_REFERENCE",
        stop=Rule(fingerprint["stop_family"]),
        exit=Rule(fingerprint["exit_family"]),
        holding_horizon_minutes=fingerprint["max_hold_minutes"],
        timing_perturbation=f"SIGNAL_DELAY_HOURS_{fingerprint['parameters'].get('signal_delay_hours', 0)}",
        position_policy=fingerprint["position_policy"],
        execution_model_reference=fingerprint["execution_model"],
        cost_model_reference=fingerprint["cost_model"],
        dataset=fingerprint["dataset"],
        implementation_dependencies=(),
        config_dependencies=(),
    )


def generate_legacy_signatures(root: Path = ROOT) -> dict[str, Any]:
    memory = load_memory(root)
    signatures = []
    for entry in memory["entries"]:
        spec = _legacy_spec(entry)
        binding = bind_executable_spec(spec)
        signatures.append(
            {
                "experiment_id": entry["experiment_id"],
                "root_family": entry["family_id"],
                "behavior_hash": binding.behavior_hash,
                "structural_hash": binding.structural_hash,
                "executable_spec_hash": binding.executable_spec_hash,
                "dependency_hash": binding.dependency_hash,
                "spec": spec.to_dict(),
            }
        )
    return {
        "schema_version": 2,
        "version": "SEARCH_MEMORY_V2",
        "purpose": "FROZEN_LEGACY_DUPLICATE_REFERENCE_ONLY_NOT_RETROACTIVE_EVIDENCE",
        "signatures": signatures,
    }


def validate_legacy_signatures(root: Path = ROOT) -> dict[str, Any]:
    path = root / "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    expected = generate_legacy_signatures(root)
    if _canonical(document) != _canonical(expected):
        raise SearchMemoryError("legacy executable signatures differ from deterministic translation")
    if len(document["signatures"]) != 9:
        raise SearchMemoryError("all nine frozen legacy strategies require V2 signatures")
    if len({item["behavior_hash"] for item in document["signatures"]}) != 9:
        raise SearchMemoryError("legacy V2 signatures contain a duplicate")
    return {"version": "SEARCH_MEMORY_V2", "legacy_signatures": 9, "status": "PASS"}


def validate_search_memory_v2(root: Path = ROOT) -> dict[str, Any]:
    registry = json.loads(
        (root / "research/memory/SEARCH_MEMORY_V2.json").read_text(encoding="utf-8")
    )
    signature_path = root / registry["legacy_signatures_path"]
    if registry != {
        "schema_version": 2,
        "version": "SEARCH_MEMORY_V2",
        "status": "VALIDATED",
        "activation_work_package": "WP-005",
        "contract": "docs/contracts/RESEARCH_SEARCH_MEMORY_V2.md",
        "executable_spec_schema": "contracts/executable_strategy_spec_v2.schema.json",
        "legacy_signatures_path": "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json",
        "legacy_signatures_sha256": text_sha256(signature_path),
        "legacy_evidence_policy": "REFERENCE_ONLY_NO_RETROACTIVE_REWRITE",
        "future_admission_policy": "FINGERPRINT_DERIVED_FROM_RUNNER_EXECUTABLE_SPEC",
        "strategy_budget_reference": "research/memory/SEARCH_BUDGET.json",
    }:
        raise SearchMemoryError("SEARCH_MEMORY_V2 registry differs from frozen contract")
    legacy = validate_legacy_signatures(root)
    memory = load_memory(root)
    counts = accounting(memory)["families"]["FAM-BREAKOUT"]
    limits = memory["budget"]["family_limits"]["FAM-BREAKOUT"]
    if counts != limits:
        raise SearchMemoryError("FAM-BREAKOUT strategy budget is not exhausted")
    return {**legacy, "breakout_strategy_budget": "EXHAUSTED"}
