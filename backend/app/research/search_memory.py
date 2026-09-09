"""Deterministic research admission and append-only evidence validation.

The vocabulary is a scientific declaration, not semantic analysis of arbitrary code.
New vocabulary/mechanisms require review; labels never establish novelty or reset budgets.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[3]
MEMORY_PATH = Path("research/memory")
ENVIRONMENT_KEYS = {"dataset", "cost_model", "execution_model"}
SET_KEYS = {"feature_families", "feature_transformations"}
LEGACY_IMPORT_IDS = {
    "EXP-BASE-001-BUYHOLD",
    "EXP-CTRL-002-RANDOM",
    "EXP-BASE-003-TREND",
    "EXP-BASE-004-BREAKOUT",
    "EXP-CTRL-005-TREND-DELAY-1H",
    "EXP-CTRL-006-NO-TRADE",
}


class SearchMemoryError(ValueError):
    pass


def canonicalize(value: Any, *, numeric_mask: bool = False, key: str = "") -> Any:
    """Sort maps and declared sets, preserve ordered lists, unify 24 and 24.0."""
    if isinstance(value, dict):
        return {
            name: canonicalize(value[name], numeric_mask=numeric_mask, key=name)
            for name in sorted(value)
        }
    if isinstance(value, list):
        values = [canonicalize(x, numeric_mask=numeric_mask) for x in value]
        return (
            sorted(values, key=lambda x: json.dumps(x, sort_keys=True))
            if key in SET_KEYS
            else values
        )
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise SearchMemoryError("fingerprints cannot contain non-finite values")
        if numeric_mask:
            return "<NUMBER>"
        return int(value) if value == int(value) else value
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(canonicalize(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint_hash(fingerprint: dict[str, Any], *, structural: bool = False) -> str:
    """Behavior excludes evaluation environment; changing fees/data cannot disguise a replay."""
    behavior = {k: v for k, v in fingerprint.items() if k not in ENVIRONMENT_KEYS}
    canonical = canonicalize(behavior, numeric_mask=structural)
    return hashlib.sha256(canonical_json(canonical).encode("utf-8")).hexdigest()


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SearchMemoryError(f"cannot read JSON: {path}") from exc


def _jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]
    except (OSError, ValueError) as exc:
        raise SearchMemoryError(f"cannot read ledger: {path}") from exc


def _schema(record: dict[str, Any], name: str, root: Path) -> None:
    schema = _json(root / "contracts" / f"search_{name}.schema.json")
    try:
        jsonschema.Draft202012Validator(schema).validate(record)
    except jsonschema.ValidationError as exc:
        raise SearchMemoryError(f"{name} schema: {exc.message}") from exc


def load_memory(root: Path = ROOT) -> dict[str, Any]:
    directory = root / MEMORY_PATH
    return {
        "entries": _jsonl(directory / "SEARCH_LEDGER.jsonl"),
        "outcomes": _jsonl(directory / "OUTCOMES.jsonl"),
        "families": _json(directory / "HYPOTHESIS_FAMILIES.json"),
        "budget": _json(directory / "SEARCH_BUDGET.json"),
    }


def _families(memory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {x["family_id"]: x for x in memory["families"]["families"]}


def _root_family(family_id: str, families: dict[str, dict[str, Any]]) -> str:
    seen: set[str] = set()
    while family_id in families:
        if family_id in seen:
            raise SearchMemoryError("cyclic family ancestry")
        seen.add(family_id)
        parent = families[family_id]["parent_family_id"]
        if parent is None:
            return family_id
        family_id = parent
    raise SearchMemoryError("unknown family ancestry")


def resolve_family(proposal: dict[str, Any], memory: dict[str, Any]) -> str | None:
    families = _families(memory)
    candidates: set[str] = set()
    supplied = proposal["family_id"]
    parent_family = proposal.get("parent_family_id")
    event = proposal["fingerprint"]["entry_event"]
    behavior = fingerprint_hash(proposal["fingerprint"])
    for family in families.values():
        if (
            supplied == family["family_id"]
            or supplied in family["aliases"]
            or parent_family == family["family_id"]
            or event in family["entry_event_anchors"]
        ):
            candidates.add(_root_family(family["family_id"], families))
    parents = set(proposal.get("parent_experiment_ids", []))
    known_parents = {x["experiment_id"] for x in memory["entries"]}
    if not parents <= known_parents:
        raise SearchMemoryError("unknown parent experiment")
    for entry in memory["entries"]:
        if entry["experiment_id"] in parents or fingerprint_hash(entry["fingerprint"]) == behavior:
            candidates.add(_root_family(entry["family_id"], families))
    if len(candidates) > 1:
        raise SearchMemoryError("declared family conflicts with behavioral anchor or ancestry")
    return next(iter(candidates)) if candidates else None


def classify_proposal(proposal: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any]:
    fingerprint = proposal["fingerprint"]
    behavior, structure = (
        fingerprint_hash(fingerprint),
        fingerprint_hash(fingerprint, structural=True),
    )
    family = resolve_family(proposal, memory)
    exact = [x for x in memory["entries"] if fingerprint_hash(x["fingerprint"]) == behavior]
    if exact:
        classification, matches = "DUPLICATE", exact
    else:
        related = [x for x in memory["entries"] if x["family_id"] == family]
        numeric = [
            x for x in related if fingerprint_hash(x["fingerprint"], structural=True) == structure
        ]
        if numeric:
            classification, matches = "PARAMETER_VARIANT", numeric
        elif family is None:
            classification, matches = "NEW_FAMILY", []
        elif related:
            parents = set(proposal.get("parent_experiment_ids", []))
            parent_rows = [x for x in related if x["experiment_id"] in parents]
            # Removing one or more declared filters is a scientific ablation, not a new mechanism.
            ablation = any(
                any(
                    fingerprint[key] == "NONE" and x["fingerprint"][key] != "NONE"
                    for key in ("regime_filter", "confirmation_filter")
                )
                for x in parent_rows
            )
            gating_changed = all(
                any(
                    fingerprint[key] != x["fingerprint"][key]
                    for key in (
                        "regime_filter",
                        "confirmation_filter",
                        "stop_family",
                        "exit_family",
                    )
                )
                for x in related
            )
            classification = (
                "MEANINGFUL_ABLATION"
                if ablation
                else "NEW_MECHANISM_WITHIN_FAMILY"
                if gating_changed
                else "NEAR_DUPLICATE"
            )
            matches = related
        else:
            classification, matches = "NEW_FAMILY", []
    return {
        "classification": classification,
        "family_id": family,
        "matched_experiment_ids": sorted(x["experiment_id"] for x in matches),
        "behavior_hash": behavior,
        "structure_hash": structure,
    }


def _safe_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()) or Path(relative).is_absolute():
        raise SearchMemoryError("evidence path escapes repository")
    return candidate


def _verify_file(root: Path, relative: str, expected_hash: str) -> dict[str, Any]:
    path = _safe_path(root, relative)
    if not path.is_file() or text_sha256(path) != expected_hash:
        raise SearchMemoryError(f"immutable evidence hash mismatch: {relative}")
    return _json(path)


def text_sha256(path: Path) -> str:
    """Hash repository text identically under Windows CRLF and Unix LF checkouts."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _pointer(record: Any, pointer: str) -> Any:
    try:
        for name in pointer.lstrip("/").split("/"):
            name = name.replace("~1", "/").replace("~0", "~")
            record = record[int(name)] if isinstance(record, list) else record[name]
        return record
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise SearchMemoryError(f"evidence pointer missing: {pointer}") from exc


def _facts(record: dict[str, Any], observations: list[dict[str, Any]]) -> None:
    for fact in observations:
        if _pointer(record, fact["json_pointer"]) != fact["expected_value"]:
            raise SearchMemoryError("evidence observation differs from immutable source")


def _verify_evidence(proposal: dict[str, Any], memory: dict[str, Any], root: Path) -> None:
    basis = proposal["new_evidence_basis"]
    if basis is None:
        raise SearchMemoryError("failed family revisit requires structured new_evidence_basis")
    source_id = basis["source_experiment_id"]
    sources = [x for x in memory["entries"] if x["experiment_id"] == source_id]
    if not sources or sources[0]["result_path"] != basis["source_path"]:
        raise SearchMemoryError("new evidence must reference a registered immutable result")
    if resolve_family(proposal, memory) != _root_family(sources[0]["family_id"], _families(memory)):
        raise SearchMemoryError("new evidence must address the same family mechanism")
    outcomes = [x for x in memory["outcomes"] if x["experiment_id"] == source_id]
    if not outcomes or outcomes[0]["result_sha256"] != basis["source_sha256"]:
        raise SearchMemoryError("new evidence source lacks finalized outcome linkage")
    record = _verify_file(root, basis["source_path"], basis["source_sha256"])
    _facts(record, basis["observations"])
    if not basis["structural_response"].strip() or not basis["falsifiable_prediction"].strip():
        raise SearchMemoryError("new evidence needs structural response and falsifiable prediction")
    if not any(
        fact["json_pointer"] == "/primary_result"
        or fact["json_pointer"].startswith("/secondary_results/")
        for fact in basis["observations"]
    ):
        raise SearchMemoryError("new evidence requires a source result metric, not metadata")
    if classify_proposal(proposal, memory)["classification"] == "PARAMETER_VARIANT":
        raise SearchMemoryError("numeric drift is not a structural response to a failed family")


def accounting(memory: dict[str, Any]) -> dict[str, Any]:
    fields = ("experiments", "strategy_variants", "trials", "numeric_parameter_variants")
    totals = dict.fromkeys(fields, 0)
    families: dict[str, dict[str, int]] = {}
    hypotheses: set[str] = set()
    for entry in memory["entries"]:
        family = _root_family(entry["family_id"], _families(memory))
        family_totals = families.setdefault(family, dict.fromkeys(fields, 0))
        for field in fields:
            value = entry["budget_units"][field]
            totals[field] += value
            family_totals[field] += value
        if entry["hypothesis_role"] in {"ECONOMIC_CORE", "STRUCTURAL_ABLATION"}:
            hypotheses.add(entry["hypothesis_id"])
    return {
        "global": totals,
        "families": families,
        "material_economic_hypotheses": len(hypotheses),
        "reference_control_experiments": sum(
            x["hypothesis_role"] not in {"ECONOMIC_CORE", "STRUCTURAL_ABLATION"}
            for x in memory["entries"]
        ),
        "completed_experiments": len(memory["outcomes"]),
        "strategy_descendants": sum(bool(x["parent_experiment_ids"]) for x in memory["entries"]),
        "sealed_queries": 0,
    }


def _check_budgets(memory: dict[str, Any]) -> None:
    counts, budget = accounting(memory), memory["budget"]
    for field, value in counts["global"].items():
        if value > budget["global_limits"][field]:
            raise SearchMemoryError(f"global {field} budget exceeded")
    for family, units in counts["families"].items():
        limits = budget["family_limits"].get(family)
        if limits is None:
            raise SearchMemoryError("family lacks explicit budget allocation")
        for field, value in units.items():
            if value > limits[field]:
                raise SearchMemoryError(f"family {family} {field} budget exceeded")
    wp004 = [x for x in memory["entries"] if x["work_package"] == "WP-004"]
    limits = budget["wp004_limits"]
    hypotheses = {x["hypothesis_id"] for x in wp004}
    if len(hypotheses) > limits["economic_core_hypotheses"]:
        raise SearchMemoryError("WP-004 core hypothesis budget exceeded")
    for field in ("strategy_variants", "trials", "numeric_parameter_variants"):
        if sum(x["budget_units"][field] for x in wp004) > limits[field]:
            raise SearchMemoryError(f"WP-004 {field} budget exceeded")


def admit_proposal(
    proposal: dict[str, Any], memory: dict[str, Any], root: Path = ROOT
) -> dict[str, Any]:
    """Validate admission; return decision without writing or running any experiment."""
    _schema(proposal, "ledger", root)
    if any(x["experiment_id"] == proposal["experiment_id"] for x in memory["entries"]):
        raise SearchMemoryError("experiment ID already registered")
    decision = classify_proposal(proposal, memory)
    if decision["classification"] == "DUPLICATE":
        raise SearchMemoryError("DUPLICATE: previously registered behavior")
    family = decision["family_id"]
    if family is None or family != proposal["family_id"]:
        raise SearchMemoryError("canonical family allocation required; rename cannot reset budget")
    if (
        proposal["behavior_hash"] != decision["behavior_hash"]
        or proposal["structure_hash"] != decision["structure_hash"]
    ):
        raise SearchMemoryError("fingerprint hash mismatch")
    if not proposal["scientific_reason"].strip():
        raise SearchMemoryError("scientific reason required")
    family_record = _families(memory)[family]
    if family_record["failure_experiment_ids"]:
        _verify_evidence(proposal, memory, root)
    if proposal["novelty"] not in {decision["classification"], "REVISIT_WITH_NEW_EVIDENCE"}:
        raise SearchMemoryError("declared novelty disagrees with deterministic classification")
    if proposal["novelty"] == "REVISIT_WITH_NEW_EVIDENCE":
        _verify_evidence(proposal, memory, root)
    numeric = int(decision["classification"] == "PARAMETER_VARIANT")
    if proposal["budget_units"]["numeric_parameter_variants"] != numeric:
        raise SearchMemoryError("parameter variant accounting mismatch")
    _check_budgets({**memory, "entries": [*memory["entries"], proposal]})
    return {
        **decision,
        "admitted": True,
        "failed_family_revisit": bool(family_record["failure_experiment_ids"]),
    }


def validate_memory(root: Path = ROOT) -> dict[str, Any]:
    memory = load_memory(root)
    _schema(memory["families"], "families", root)
    _schema(memory["budget"], "budget", root)
    families = _families(memory)
    if len(families) != len(memory["families"]["families"]):
        raise SearchMemoryError("duplicate family ID")
    aliases: dict[str, str] = {}
    for family in families.values():
        canonical = _root_family(family["family_id"], families)
        for alias in [family["family_id"], *family["aliases"], *family["entry_event_anchors"]]:
            if alias in aliases and aliases[alias] != canonical:
                raise SearchMemoryError("ambiguous family alias or anchor")
            aliases[alias] = canonical
    seen: dict[str, dict[str, Any]] = {}
    hashes: set[str] = set()
    preceding = {**memory, "entries": []}
    for entry in memory["entries"]:
        _schema(entry, "ledger", root)
        experiment_id = entry["experiment_id"]
        if experiment_id in seen:
            raise SearchMemoryError("duplicate ledger experiment ID")
        if entry["behavior_hash"] in hashes:
            raise SearchMemoryError("duplicate behavior admitted to ledger")
        for key, structural in (("behavior_hash", False), ("structure_hash", True)):
            if entry[key] != fingerprint_hash(entry["fingerprint"], structural=structural):
                raise SearchMemoryError("fingerprint hash mismatch")
        if entry["record_kind"] == "PREREGISTERED_ADMISSION":
            admit_proposal(entry, preceding, root)
        elif entry["work_package"] != "WP-003" or experiment_id not in LEGACY_IMPORT_IDS:
            raise SearchMemoryError("retrospective import restricted to original WP-003 records")
        elif resolve_family(entry, preceding) != entry["family_id"]:
            raise SearchMemoryError("retrospective family identity mismatch")
        prereg = _verify_file(root, entry["preregistration_path"], entry["preregistration_sha256"])
        if (
            prereg["experiment_id"] != experiment_id
            or prereg["trial_budget"] != entry["budget_units"]["trials"]
        ):
            raise SearchMemoryError("ledger differs from preregistration identity or trial budget")
        if prereg["dataset"] != entry["fingerprint"]["dataset"]:
            raise SearchMemoryError("fingerprint dataset differs from preregistration")
        expected_result = f"research/experiments/{experiment_id}/result.json"
        if entry["result_path"] != expected_result or entry["outcome_reference"] != experiment_id:
            raise SearchMemoryError("result/outcome linkage mismatch")
        seen[experiment_id] = entry
        hashes.add(entry["behavior_hash"])
        preceding["entries"].append(entry)
    outcome_ids: set[str] = set()
    for outcome in memory["outcomes"]:
        _schema(outcome, "outcome", root)
        experiment_id = outcome["experiment_id"]
        if experiment_id not in seen or experiment_id in outcome_ids:
            raise SearchMemoryError("unregistered or duplicate outcome")
        if outcome["result_path"] != seen[experiment_id]["result_path"]:
            raise SearchMemoryError("outcome result linkage mismatch")
        result = _verify_file(root, outcome["result_path"], outcome["result_sha256"])
        if result["experiment_id"] != experiment_id:
            raise SearchMemoryError("outcome experiment identity mismatch")
        if (
            result["trial_accounting"]["executed_trials"]
            != seen[experiment_id]["budget_units"]["trials"]
        ):
            raise SearchMemoryError("executed trial count differs from reserved search budget")
        _facts(result, outcome["evidence_facts"])
        outcome_ids.add(experiment_id)
    for experiment_id, entry in seen.items():
        if _safe_path(root, entry["result_path"]).is_file() and experiment_id not in outcome_ids:
            raise SearchMemoryError("finalized result lacks immutable memory outcome")
    for family in families.values():
        if not set(family["failure_experiment_ids"]) <= outcome_ids:
            raise SearchMemoryError("failure memory refers to missing outcome")
        for experiment_id in family["failure_experiment_ids"]:
            outcome = next(x for x in memory["outcomes"] if x["experiment_id"] == experiment_id)
            if not outcome["terminal_classification"].startswith("REJECT"):
                raise SearchMemoryError("failure memory must reference a negative terminal outcome")
            if _root_family(seen[experiment_id]["family_id"], families) != _root_family(
                family["family_id"], families
            ):
                raise SearchMemoryError("failure outcome belongs to another family")
    _check_budgets(memory)
    return accounting(memory)


def render_research_map(memory: dict[str, Any]) -> str:
    counts = accounting(memory)
    outcomes = {x["experiment_id"]: x for x in memory["outcomes"]}
    lines = [
        "# Research map",
        "",
        "Generated from SEARCH_LEDGER.jsonl, HYPOTHESIS_FAMILIES.json, SEARCH_BUDGET.json and OUTCOMES.jsonl.",
        "DEVELOPMENT RESEARCH - NOT APPROVED STRATEGY PERFORMANCE. Champion NONE.",
        "",
        (
            f"Reserved: {counts['global']['experiments']} experiments/configurations; "
            f"{counts['global']['trials']} evaluation trials; "
            f"{counts['material_economic_hypotheses']} economic core hypotheses. "
            f"Completed: {counts['completed_experiments']}. Sealed queries: 0."
        ),
        "",
        "| Root family | Experiments (parent lineage) | Budget consumed / limit | Status and lesson |",
        "|---|---|---|---|",
    ]
    for family in memory["families"]["families"]:
        family_id = family["family_id"]
        entries = [x for x in memory["entries"] if x["family_id"] == family_id]
        units = counts["families"].get(family_id, {"experiments": 0, "trials": 0})
        limits = memory["budget"]["family_limits"].get(family_id, {"experiments": 0, "trials": 0})
        experiments = "; ".join(
            x["experiment_id"]
            + (" <- " + ", ".join(x["parent_experiment_ids"]) if x["parent_experiment_ids"] else "")
            for x in entries
        )
        statuses = "; ".join(
            outcomes[x["experiment_id"]]["terminal_classification"]
            if x["experiment_id"] in outcomes
            else "PREREGISTERED"
            for x in entries
        )
        lines.append(
            f"| {family_id} | {experiments} | "
            f"{units['experiments']}/{limits['experiments']} experiments; "
            f"{units['trials']}/{limits['trials']} trials | {statuses} |"
        )
    lines.extend(["", "## Legitimate directions and blocked repeats", ""])
    for family in memory["families"]["families"]:
        lines.append(f"- {family['family_id']}: {family['legitimate_revisit']}")
    lines.extend(
        [
            "",
            "Exact behavior and renamed exact behavior are blocked. Parameter-only changes are near duplicates,",
            "with no WP-004 numeric-search allowance. Cost profiles, folds and random seeds are not new mechanisms.",
            "No automatic promotion follows a positive development outcome. See FAILURE_MEMORY.md for falsified",
            "claims and limitations, and the adaptive decision ledger for result-dependent research forks.",
            "",
        ]
    )
    return "\n".join(lines)


def render_failure_memory(memory: dict[str, Any]) -> str:
    lines = [
        "# Failure memory",
        "",
        "Generated from immutable OUTCOMES.jsonl; links point to original finalized evidence.",
        "Negative results remain part of the permanent search burden. A null/no-trade result is not a loss.",
        "",
    ]
    for outcome in memory["outcomes"]:
        lines.extend(
            [
                f"## {outcome['experiment_id']} - {outcome['terminal_classification']}",
                "",
                f"[Immutable result](../../{outcome['result_path']}). {outcome['conclusion']}",
                "",
                f"Falsified/tested: {outcome['falsified']}",
                "",
                f"Not falsified: {outcome['not_falsified']}",
                "",
                f"Recorded failure modes: {', '.join(outcome['failure_modes']) or 'none claimed'}.",
                "",
                f"Legitimate revisit: {outcome['legitimate_revisit']}",
                "",
            ]
        )
    return "\n".join(lines)
