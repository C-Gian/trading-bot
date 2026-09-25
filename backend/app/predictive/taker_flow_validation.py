"""Deterministic validation of the public taker-flow foundation and its frozen descendant.

Metadata mode needs no market data: it re-derives the foundation's qualification and
selection from the committed result, proves every text dependency through the declared
canonical-text provenance record (`CANONICAL_UTF8_LF_TEXT_V1`, so an LF and a CRLF checkout of
the same committed text validate identically while any real change fails), regenerates the
report, checks the acquisition
manifest's exact market-month coverage and development-only boundary, and binds the
search-memory family, predictive outcome and descendant direction to the result.

Data mode additionally re-verifies every raw official object against the manifest, proves the
raw archive inventory is exactly the pinned set, and replays the foundation end to end.

Nothing here fits, reads or scores anything for `EXP-PRED-V2-006`; it only proves that the
descendant is still preregistered, blocked, and has produced no experiment artifact.
"""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

from ..research.text_provenance import (
    CANONICAL_TEXT_RULE,
    canonical_text_bytes,
    canonical_text_sha256,
    verify_text_dependency,
)
from .taker_flow_foundation import (
    EXPERIMENT_ID,
    FAMILY_SEED,
    FEATURE_NAMES,
    HORIZONS_HOURS,
    IMPLEMENTATION_PATHS,
    OUTER_FOLD_YEARS,
    REPORT_MARKDOWN_PATH,
    RESULT_PATH,
    VERSION,
    markdown_bytes,
    qualification,
    run_foundation,
    select_horizon,
)
from .taker_flow_source import (
    ARCHIVE_HOST,
    ARCHIVE_PREFIX,
    MANIFEST_PATH,
    PROTOCOL_PATH,
    RAW_ROOT,
    archive_url,
    load_manifest,
    parse_checksum_file,
    raw_path,
    verified_object,
)

ROOT = Path(__file__).resolve().parents[3]

STATE_PATH = "state/current_state.json"
FOUNDATION_KEY = "predictive_public_taker_flow_horizon_foundation"
INCREMENTAL_KEY = "predictive_public_taker_flow_1h_incremental"
GOVERNANCE_KEY = "governance_transition_v3"
FOUNDATION_CLASSIFICATION = "FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY"
FAMILY_ID = "FAM-PUBLIC-TAKER-FLOW-PROBABILITY"
FAMILY_PATH = f"research/memory/registry/families/{FAMILY_ID}.json"
OUTCOME_PATH = (
    "research/memory/registry/outcomes/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.jsonl"
)
DIRECTION_PATH = (
    "research/memory/registry/directions/PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE.json"
)
INCREMENTAL_EXPERIMENT_ID = "EXP-PRED-V2-006-PUBLIC-TAKER-FLOW-1H-INCREMENTAL"
INCREMENTAL_HYPOTHESIS_ID = "H-PRED-V2-PUBLIC-FLOW-INCREMENTAL-001"
INCREMENTAL_PROTOCOL_PATH = (
    "research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-V1.md"
)
INCREMENTAL_BLOCKED = "PREREGISTERED_EXECUTION_BLOCKED_PENDING_POWER_GATE"
# ADR-0035: the gate blocked the experiment before execution; this status is terminal.
INCREMENTAL_POWER_BLOCKED = "POWER_BLOCKED_NOT_EXECUTED"
INCREMENTAL_OUTCOME_PATH = (
    "research/memory/registry/outcomes/"
    "PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1.jsonl"
)
POWER_GATE_SEED = 2026092307
INCREMENTAL_SEED = 2026092306
MESI = 0.0002
LAST_DEVELOPMENT_MONTH = "2024-12"
SUPPORTED = {"24": False, "4": False, "1": True}
# These three result fields hash files; they are re-checked line-ending neutrally instead of
# being compared byte for byte with a replay that may run on a CRLF checkout.
FILE_HASH_FIELDS = (("protocol", "sha256"), ("source", "manifest_sha256"), ("implementation",))
TEXT_PROVENANCE_PATH = (
    "reports/validation/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1-TEXT-PROVENANCE.json"
)
# Every text dependency of the foundation, with the role its governed record must declare.
TEXT_DEPENDENCY_ROLES = {
    PROTOCOL_PATH: "FROZEN_PROTOCOL",
    MANIFEST_PATH: "SOURCE_MANIFEST",
    **dict.fromkeys(IMPLEMENTATION_PATHS, "FROZEN_IMPLEMENTATION"),
    RESULT_PATH: "IMMUTABLE_RESULT_ARTIFACT",
    REPORT_MARKDOWN_PATH: "GENERATED_REPORT",
}


class TakerFlowValidationError(AssertionError):
    """A governed public taker-flow record is missing, altered or inconsistent."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TakerFlowValidationError(message)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(root: Path) -> dict[str, Any]:
    manifest = load_manifest(root)  # exact market-month coverage, frozen identity
    for entry in manifest["archives"]:
        year, month = (int(part) for part in entry["month"].split("-"))
        require(entry["month"] <= LAST_DEVELOPMENT_MONTH, f"post-cutoff archive {entry['month']}")
        require(date(year, month, 1) >= date(2020, 1, 1), f"pre-window archive {entry['month']}")
        require(entry["raw_path"] == raw_path(entry["market"], year, month), "raw path drift")
        require(entry["url"] == archive_url(entry["market"], year, month), "source URL drift")
        require(
            entry["source_path"].startswith(ARCHIVE_PREFIX[entry["market"]] + "/"),
            "an archive object is outside the official prefix",
        )
        require(entry["url"].startswith(ARCHIVE_HOST + "/"), "a non-official archive host")
        require(
            entry["sha256"] == entry["official_checksum_sha256"]
            and entry["official_checksum_verified"] is True,
            f"{entry['raw_path']}: official checksum not verified",
        )
    require(manifest["official_checksums_verified"] == manifest["objects"] == 120, "not 120")
    require(manifest["request_ceiling"] == "2024-12-31T23:59:59.999Z", "request ceiling drift")
    return manifest


def validate_raw_objects(root: Path, manifest: dict[str, Any]) -> int:
    """Every raw official object exists, matches its pin, and nothing else is stored."""
    pinned = {root / entry["raw_path"] for entry in manifest["archives"]}
    stored = set((root / RAW_ROOT).rglob("*.zip"))
    require(stored == pinned, "the public taker-flow raw inventory differs from the manifest")
    for entry in manifest["archives"]:
        verified_object(root, entry)
        path = root / entry["raw_path"]
        checksum = path.with_name(path.name + ".CHECKSUM")
        require(checksum.is_file(), f"{entry['raw_path']}: official checksum file missing")
        official = parse_checksum_file(checksum.read_text(encoding="utf-8"), path.name)
        require(official == entry["official_checksum_sha256"], "checksum sidecar drift")
    return len(pinned)


def _pointer(record: Any, pointer: str) -> Any:
    for name in pointer.lstrip("/").split("/"):
        name = name.replace("~1", "/").replace("~0", "~")
        record = record[int(name)] if isinstance(record, list) else record[name]
    return record


def _recorded_document(root: Path, relative: str) -> Any:
    path = root / relative
    if relative.endswith(".jsonl"):
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        require(len(lines) == 1, f"{relative}: expected exactly one record")
        return json.loads(lines[0])
    return read_json(path)


def validate_text_provenance(root: Path, state: dict[str, Any]) -> dict[str, str]:
    """Check each declared text dependency by its canonical text, never by checkout bytes.

    The historical raw digests stay exactly where they were recorded; this proves every
    recorded location still carries its preserved raw digest, and that the file on disk
    has the canonical text that raw digest was declared equivalent to. Any change other than
    a newline encoding changes the canonical digest and fails.
    """
    pinned = state[FOUNDATION_KEY]["text_provenance"]
    require(pinned["path"] == TEXT_PROVENANCE_PATH, "text provenance path drift")
    record_path = root / TEXT_PROVENANCE_PATH
    require(
        canonical_text_sha256(record_path) == pinned["canonical_text_sha256"],
        "the text provenance record changed",
    )
    record = read_json(record_path)
    require(record["rule"] == CANONICAL_TEXT_RULE, "text provenance rule drift")
    require(record["experiment_id"] == EXPERIMENT_ID, "text provenance experiment drift")
    require(record["historical_result_rewritten"] is False, "historical result rewritten")
    declared = {item["path"]: item for item in record["dependencies"]}
    require(len(declared) == len(record["dependencies"]), "a dependency is declared twice")
    require(set(declared) == set(TEXT_DEPENDENCY_ROLES), "text dependency set drift")
    relations: dict[str, str] = {}
    for path, item in declared.items():
        require(item["role"] == TEXT_DEPENDENCY_ROLES[path], f"{path}: role drift")
        require(item["recorded_at"], f"{path}: no recorded historical pin")
        for location in item["recorded_at"]:
            document = _recorded_document(root, location["artifact"])
            require(
                _pointer(document, location["json_pointer"]) == item["raw_sha256"],
                f"{path}: the preserved raw digest differs at {location['artifact']}",
            )
        try:
            relations[path] = verify_text_dependency(root / path, item)
        except ValueError as exc:
            raise TakerFlowValidationError(str(exc)) from exc
    return relations


def _strip_file_hashes(result: dict[str, Any]) -> dict[str, Any]:
    stripped = copy.deepcopy(result)
    for field in FILE_HASH_FIELDS:
        target = stripped
        for name in field[:-1]:
            target = target[name]
        target.pop(field[-1])
    return stripped


def validate_result(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    record = state[FOUNDATION_KEY]
    pinned = record["result"]
    result_path = root / RESULT_PATH
    require(pinned["path"] == RESULT_PATH, "result path drift")
    validate_text_provenance(root, state)
    result = read_json(result_path)
    require(result["experiment_id"] == EXPERIMENT_ID and result["version"] == VERSION, "identity")
    # Protocol, manifest and implementation identity are proven by the text provenance
    # record above, which binds each preserved raw pin in this result to canonical text.
    require(result["protocol"]["path"] == PROTOCOL_PATH, "protocol path drift")
    require(result["source"]["manifest_path"] == MANIFEST_PATH, "manifest path drift")
    require(set(result["implementation"]) == set(IMPLEMENTATION_PATHS), "implementation set")

    design = result["design"]
    require(design["features"] == list(FEATURE_NAMES), "feature drift")
    require(design["horizons_hours_in_frozen_order"] == list(HORIZONS_HOURS), "horizon drift")
    require(design["outer_fold_years"] == list(OUTER_FOLD_YEARS), "fold drift")
    require(design["family_seed"] == FAMILY_SEED, "seed drift")
    require(design["bootstrap_replicates"] == 10_000, "replicate drift")

    classifications = {}
    for horizon in HORIZONS_HOURS:
        item = result["horizons"][str(horizon)]
        derived = qualification(item)
        require(derived == item["qualification"], f"{horizon}h qualification does not re-derive")
        supported = derived["classification"] == "FOUNDATION_SIGNAL_SUPPORTED"
        require(supported is SUPPORTED[str(horizon)], f"{horizon}h classification drift")
        require(
            result["classifications"][str(horizon)] == derived["classification"],
            f"{horizon}h summary classification drift",
        )
        summary = pinned["horizons"][str(horizon)]
        require(summary["classification"] == derived["classification"], "state summary drift")
        require(summary["scored_rows"] == item["scored_rows"], "state scored-row drift")
        require(
            summary["pooled_brier_improvement"] == item["pooled_brier_improvement"],
            "state effect drift",
        )
        require(summary["adjusted_interval"] == item["bootstrap"]["interval"], "interval drift")
        classifications[horizon] = derived["classification"]
    selection = select_horizon(classifications)
    require(
        selection == result["selection"] == pinned["selection"] == FOUNDATION_CLASSIFICATION
        and record["classification"] == FOUNDATION_CLASSIFICATION,
        "foundation selection drift",
    )
    boundaries = result["boundaries"]
    require(
        boundaries["sealed_queries"] == 0
        and boundaries["champion_status"] == "NONE"
        and boundaries["real_money"] is False
        and boundaries["action_threshold_used"] is False
        and boundaries["trading_pnl"] is False,
        "foundation boundary drift",
    )
    # The report was written from the in-memory result, whose criteria keep their frozen
    # evaluation order; the stored JSON is key-sorted. Re-derive that order to regenerate it.
    regenerated = copy.deepcopy(result)
    for horizon in HORIZONS_HOURS:
        item = regenerated["horizons"][str(horizon)]
        item["qualification"] = qualification(item)
    report = root / REPORT_MARKDOWN_PATH
    require(pinned["report"] == REPORT_MARKDOWN_PATH, "report path drift")
    require(
        report.read_bytes().replace(b"\r\n", b"\n") == markdown_bytes(regenerated),
        "report does not regenerate from the result",
    )
    require(pinned["deterministic_replay"] == "PASS", "replay status drift")
    require(record["model_fits_observed"] == result["model_fits"] == 12, "model-fit drift")
    require(record["sealed_queries"] == 0 and record["real_money"] is False, "boundary drift")
    require(record["champion_status"] == "NONE", "Champion drift")
    return result


def validate_search_memory(root: Path, result_sha256: str) -> None:
    from ..research.registry import predictive_outcomes, validate_predictive_outcomes

    family = read_json(root / FAMILY_PATH)
    require(family["family_id"] == FAMILY_ID, "family identity drift")
    require(family["parent_family_id"] == "FAM-ORDER-FLOW", "family parent drift")
    require(family["relation_to_parent"]["parent_rejection_intact"] is True, "WP-007 rescue")
    validate_predictive_outcomes(root)
    outcomes = [
        item for item in predictive_outcomes(root) if item["experiment_id"] == EXPERIMENT_ID
    ]
    require(len(outcomes) == 1, "the foundation outcome must be recorded exactly once")
    outcome = outcomes[0]
    require(outcome["family_id"] == FAMILY_ID, "outcome family drift")
    require(outcome["result_sha256"] == result_sha256, "outcome result hash drift")
    require(outcome["terminal_classification"] == FOUNDATION_CLASSIFICATION, "outcome drift")
    require(
        outcome["horizon_classifications"]
        == {"24h": "NOT_SUPPORTED", "4h": "NOT_SUPPORTED", "1h": "SUPPORTED"},
        "outcome horizon drift",
    )
    direction = read_json(root / DIRECTION_PATH)
    require(direction["root_family"] == FAMILY_ID, "direction family drift")
    require(direction["experiment_id"] == INCREMENTAL_EXPERIMENT_ID, "direction experiment")
    require(direction["hypothesis_id"] == INCREMENTAL_HYPOTHESIS_ID, "direction hypothesis")
    require(direction["source_decision"]["result_sha256"] == result_sha256, "direction source")
    require(direction["model_fits"] == 0, "the descendant direction fitted a model")


def validate_incremental(root: Path, state: dict[str, Any]) -> None:
    record = state[INCREMENTAL_KEY]
    require(record["experiment_id"] == INCREMENTAL_EXPERIMENT_ID, "experiment identity")
    require(record["hypothesis_id"] == INCREMENTAL_HYPOTHESIS_ID, "hypothesis identity")
    require(record["hypothesis_id"] != record["experiment_id"], "hypothesis equals experiment")
    require(record["protocol"] == INCREMENTAL_PROTOCOL_PATH, "protocol path drift")
    require(
        canonical_text_sha256(root / INCREMENTAL_PROTOCOL_PATH)
        == record["protocol_canonical_text_sha256"],
        "the frozen incremental protocol changed",
    )
    require(
        record["status"] in {INCREMENTAL_BLOCKED, INCREMENTAL_POWER_BLOCKED},
        "the incremental experiment left its block",
    )
    require(record["execution_authorized"] is False, "execution was authorized")
    require(record["model_fits_observed"] == 0, "the incremental candidate was fitted")
    require(record["market_results_observed"] is False, "incremental results observed")
    require(
        not (root / "research/experiments" / INCREMENTAL_EXPERIMENT_ID).exists(),
        "an EXP-PRED-V2-006 experiment artifact exists",
    )
    if record["status"] == INCREMENTAL_POWER_BLOCKED:
        validate_power_block(root, record)
    gate = record["power_gate"]
    require(gate["mesi"] == MESI and gate["mesi_lowerable_after_block"] is False, "MESI drift")
    require(gate["bootstrap"]["seed"] == POWER_GATE_SEED, "power-gate seed drift")
    require(record["inference"]["seed"] == INCREMENTAL_SEED, "inference seed drift")
    require(
        len({FAMILY_SEED, POWER_GATE_SEED, INCREMENTAL_SEED}) == 3,
        "seeds must stay distinct",
    )
    require(gate["proxy_classification"] == "ANALOG_DEPENDENCE_AND_VARIANCE_PROXY", "proxy")
    require(
        gate["mde_statement"]
        == "MDE_IS_ANALOG_EXPECTED_DETECTABILITY_NOT_REALIZED_INCREMENTAL_VARIANCE",
        "the MDE statement drifted",
    )
    require(gate["pass_authorizes_execution"] is False, "a pass may not authorize execution")
    require(
        gate["future_price_only_or_price_plus_flow_predictions_used"] is False
        and gate["outer_candidate_or_control_fits_allowed"] is False,
        "the power gate may not use the future contrast",
    )


def validate_power_block(root: Path, record: dict[str, Any]) -> None:
    """The terminal power block is bound to its gate record, outcome and decision.

    Nothing about the incremental hypothesis was observed, and nothing may bypass the block.
    """
    from ..research.registry import predictive_outcomes
    from .taker_flow_power_gate import BLOCKED, GATE_JSON_PATH, GATE_MARKDOWN_PATH

    gate = record["power_gate"]
    require(record["terminal_classification"] == INCREMENTAL_POWER_BLOCKED, "terminal drift")
    require(gate["classification"] == BLOCKED, "the recorded gate did not block")
    require(gate["record"] == GATE_JSON_PATH and gate["report"] == GATE_MARKDOWN_PATH, "paths")
    require(
        canonical_text_sha256(root / GATE_JSON_PATH) == gate["record_canonical_text_sha256"]
        and canonical_text_sha256(root / GATE_MARKDOWN_PATH)
        == gate["report_canonical_text_sha256"],
        "the power-gate outputs differ from their state pins",
    )
    written = read_json(root / GATE_JSON_PATH)
    require(written["classification"] == BLOCKED, "the gate record did not block")
    require(gate["power_at_mesi"] == written["analysis"]["power_at_mesi"], "power drift")
    require(gate["power_at_mesi"] < 0.80, "a blocked gate cannot reach target power")
    require(gate["analog_mde"] == written["analysis"]["mde"]["mde"], "MDE drift")
    require(gate["deterministic_replay"] == "PASS", "gate replay status drift")
    require(
        record["price_only_control_fitted"] is False
        and record["price_plus_flow_candidate_fitted"] is False
        and record["incremental_hypothesis_result_inferable"] is False
        and record["next_engineering_task_authorized"] is False,
        "the power block was bypassed",
    )
    require((root / record["decision_record"]).is_file(), "the power-block decision is missing")
    require((root / record["checkpoint_report"]).is_file(), "the power-block checkpoint is missing")
    require(record["search_memory_outcome"] == INCREMENTAL_OUTCOME_PATH, "outcome path drift")
    outcomes = [
        item
        for item in predictive_outcomes(root)
        if item["experiment_id"] == INCREMENTAL_EXPERIMENT_ID
    ]
    require(len(outcomes) == 1, "the power block must be recorded exactly once in search memory")
    outcome = outcomes[0]
    require(outcome["terminal_classification"] == INCREMENTAL_POWER_BLOCKED, "outcome drift")
    require(outcome["result_sha256"] == gate["record_canonical_text_sha256"], "outcome pin")
    require(
        outcome["model_fits"] == 0 and outcome["market_outcomes_observed"] is False,
        "the outcome claims an incremental observation",
    )


def active_task_title(root: Path) -> str:
    """The work-package identifier in the header of `tasks/CURRENT_TASK.md`."""
    header = (root / "tasks/CURRENT_TASK.md").read_text(encoding="utf-8").splitlines()[0]
    prefix = "# CURRENT TASK — "
    require(header.startswith(prefix), "the active task has no work-package header")
    return header.removeprefix(prefix).strip()


def expected_state_pointers(root: Path, state: dict[str, Any]) -> dict[str, str]:
    """Top-level pointers derived from the latest reviewed public taker-flow checkpoint.

    Once the incremental power gate is closed (ADR-0035) its checkpoint is the latest one;
    before that, the foundation's. Once the Constitution 3.0 governance transition is recorded
    (ADR-0036) its checkpoint is the latest executor checkpoint, and it is also the latest
    reviewed one only after review. The next work package is the active task's header.
    """
    if GOVERNANCE_KEY in state:
        return _governance_pointers(root, state)
    incremental = state[INCREMENTAL_KEY]
    if incremental["status"] == INCREMENTAL_POWER_BLOCKED:
        record = incremental
    else:
        record = state[FOUNDATION_KEY]
        require(
            record["status"] == "COMPLETE_RESEARCH_DIRECTOR_ACCEPTED",
            "the foundation checkpoint has not been reviewed",
        )
    report = root / record["checkpoint_report"]
    require(report.is_file(), "the latest checkpoint report is missing")
    require((root / record["decision_record"]).is_file(), "the latest checkpoint is unreviewed")
    checkpoint = report.stem
    next_work_package = active_task_title(root)
    require(
        next_work_package == state[INCREMENTAL_KEY]["next_work_package"],
        "the active task is not the recorded next work package",
    )
    return {
        "latest_executor_checkpoint": checkpoint,
        "latest_reviewed_checkpoint": checkpoint,
        "next_recommended_work_package": next_work_package,
        "status": "REVIEWED",
        "research_architecture.next_checkpoint": next_work_package.replace("-", "_"),
    }


def _governance_pointers(root: Path, state: dict[str, Any]) -> dict[str, str]:
    record = state[GOVERNANCE_KEY]
    report = root / record["checkpoint_report"]
    require(report.is_file(), "the governance checkpoint report is missing")
    for decision in record["decision_records"]:
        require((root / decision).is_file(), f"decision record {decision} is missing")
    executor = report.stem
    if record["status"] == "REVIEWED":
        reviewed = executor
    else:
        previous = state[INCREMENTAL_KEY]
        require(previous["status"] == INCREMENTAL_POWER_BLOCKED, "no prior reviewed checkpoint")
        reviewed = Path(previous["checkpoint_report"]).stem
    next_work_package = active_task_title(root)
    require(
        next_work_package == record["next_work_package"],
        "the active task is not the recorded next work package",
    )
    return {
        "latest_executor_checkpoint": executor,
        "latest_reviewed_checkpoint": reviewed,
        "next_recommended_work_package": next_work_package,
        "status": record["status"],
        "research_architecture.next_checkpoint": next_work_package.replace("-", "_"),
    }


def validate_state_pointers(root: Path, state: dict[str, Any]) -> None:
    for field, expected in expected_state_pointers(root, state).items():
        head, _, tail = field.partition(".")
        actual = state[head][tail] if tail else state[head]
        require(actual == expected, f"state pointer {field} is stale: {actual} != {expected}")


def validate_power_gate(root: Path, state: dict[str, Any], data_available: bool) -> str:
    """The EXP-PRED-V2-006 power-gate record, once written, is governed and hash-checked.

    Before the Owner runs the gate neither output may exist. Afterwards both must, the record
    must be internally consistent with the frozen design, every text dependency must still
    have the canonical text it names, the Markdown must regenerate from the JSON, and data
    mode replays the gate itself. A written gate never authorizes execution.
    """
    from . import taker_flow_power_gate as gate

    present = [path for path in gate.GATE_PATHS if (root / path).exists()]
    gate_state = state[INCREMENTAL_KEY]["power_gate"]
    if not present:
        require(
            gate_state["status"] == "NOT_COMPUTED_PENDING_IMPLEMENTATION",
            "state claims a power-gate result that does not exist",
        )
        return "NOT_COMPUTED"
    require(len(present) == len(gate.GATE_PATHS), "the power-gate outputs are incomplete")
    json_path = root / gate.GATE_JSON_PATH
    record = read_json(json_path)
    try:
        gate.validate_record(record, root)
    except gate.PowerGateError as exc:
        raise TakerFlowValidationError(f"power gate: {exc}") from exc
    require(
        canonical_text_bytes(json_path.read_bytes()) == gate.canonical_json_bytes(record),
        "the power-gate JSON is not in canonical form",
    )
    require(
        canonical_text_bytes((root / gate.GATE_MARKDOWN_PATH).read_bytes())
        == gate.markdown_bytes(record),
        "the power-gate report does not regenerate from its record",
    )
    pinned = gate_state.get("record_canonical_text_sha256")
    if pinned is not None:
        require(canonical_text_sha256(json_path) == pinned, "power-gate record differs from state")
    require(state[INCREMENTAL_KEY]["execution_authorized"] is False, "execution was authorized")
    if data_available:
        replay = gate.run_power_gate(root)
        require(
            gate.canonical_json_bytes(replay) == gate.canonical_json_bytes(record),
            "the power-gate replay does not reproduce the written record",
        )
    return str(record["classification"])


def validate_public_taker_flow(root: Path = ROOT, data_available: bool = False) -> dict[str, Any]:
    state = read_json(root / STATE_PATH)
    manifest = validate_manifest(root)
    result = validate_result(root, state)
    validate_search_memory(root, state[FOUNDATION_KEY]["result"]["sha256"])
    validate_incremental(root, state)
    validate_state_pointers(root, state)
    power_gate = validate_power_gate(root, state, data_available)
    raw_objects = 0
    if data_available:
        raw_objects = validate_raw_objects(root, manifest)
        replay = run_foundation(root)
        require(
            _strip_file_hashes(replay) == _strip_file_hashes(result),
            "the foundation replay does not reproduce the committed result",
        )
    return {
        "status": "PASS",
        "data_replayed": data_available,
        "raw_objects_verified": raw_objects,
        "classification": result["selection"],
        "power_gate": power_gate,
    }


__all__ = [
    "TakerFlowValidationError",
    "active_task_title",
    "expected_state_pointers",
    "validate_incremental",
    "validate_manifest",
    "validate_power_gate",
    "validate_public_taker_flow",
    "validate_raw_objects",
    "validate_result",
    "validate_search_memory",
    "validate_state_pointers",
    "validate_text_provenance",
]
