"""Governed records of the public taker-flow foundation and its blocked 1h descendant.

Metadata only: nothing here reads market data, replays the foundation or fits a model.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest
from app.predictive import taker_flow_validation as validation
from app.research import registry
from app.research.sealed_eligibility import build_eligibility_table
from app.research.text_provenance import (
    CANONICAL_TEXT_EQUIVALENT,
    RAW_IDENTICAL,
    TextProvenanceError,
    canonical_text_bytes,
    canonical_text_sha256,
)

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = "EXP-PRED-V2-005-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION"


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def state_errors(state: dict) -> list:
    schema = read_json("contracts/project_state.schema.json")
    return list(jsonschema.Draft202012Validator(schema).iter_errors(state))


def test_foundation_and_descendant_validate_without_market_data() -> None:
    finding = validation.validate_public_taker_flow(ROOT, data_available=False)
    assert finding == {
        "status": "PASS",
        "data_replayed": False,
        "raw_objects_verified": 0,
        "classification": "FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY",
    }


def test_foundation_outcome_is_search_memory_but_never_a_sealed_candidate() -> None:
    outcomes = registry.validate_predictive_outcomes(ROOT)
    assert [item["experiment_id"] for item in outcomes] == [EXPERIMENT]
    outcome = outcomes[0]
    assert outcome["family_id"] == "FAM-PUBLIC-TAKER-FLOW-PROBABILITY"
    assert outcome["terminal_classification"] == "FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY"
    assert outcome["horizon_classifications"] == {
        "24h": "NOT_SUPPORTED",
        "4h": "NOT_SUPPORTED",
        "1h": "SUPPORTED",
    }
    assert outcome["sealed_eligibility"] == "NONE_NOT_AUTHORIZED"
    assert EXPERIMENT in {item["experiment_id"] for item in registry.all_outcomes(ROOT)}
    assert EXPERIMENT not in {item["experiment_id"] for item in registry.strategy_outcomes(ROOT)}
    table = build_eligibility_table(ROOT)
    assert EXPERIMENT not in {item["experiment_id"] for item in table["candidates"]}
    assert table == read_json("research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sealed_eligibility", "DEVELOPMENT_ELIGIBLE_PENDING_RESEARCH_DIRECTOR_SEALED_ALLOCATION"),
        ("champion_status", "CHAMPION"),
        ("real_money", True),
        ("family_id", "FAM-UNREGISTERED"),
        ("result_sha256", "0" * 64),
    ],
)
def test_a_distorted_predictive_outcome_fails_closed(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    outcome = copy.deepcopy(registry.predictive_outcomes(ROOT)[0])
    outcome[field] = value
    monkeypatch.setattr(registry, "predictive_outcomes", lambda root=ROOT: [outcome])
    with pytest.raises(ValueError):
        registry.validate_predictive_outcomes(ROOT)


def test_predictive_outcome_facts_must_match_the_immutable_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome = copy.deepcopy(registry.predictive_outcomes(ROOT)[0])
    outcome["evidence_facts"][0]["expected_value"] = "KEEP_24H_FOR_NEXT_PUBLIC_FLOW_FAMILY"
    monkeypatch.setattr(registry, "predictive_outcomes", lambda root=ROOT: [outcome])
    with pytest.raises(ValueError, match="differs from result"):
        registry.validate_predictive_outcomes(ROOT)
    del outcome["forbidden_rescues"]
    with pytest.raises(ValueError, match="lacks"):
        registry.validate_predictive_outcomes(ROOT)


def test_state_validates_against_the_explicit_schema() -> None:
    state = read_json("state/current_state.json")
    assert state_errors(state) == []


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("predictive_public_taker_flow_1h_incremental", "execution_authorized"), True),
        (("predictive_public_taker_flow_1h_incremental", "power_gate", "mesi"), 0.0001),
        (
            ("predictive_public_taker_flow_1h_incremental", "power_gate", "bootstrap", "seed"),
            2026092306,
        ),
        (("predictive_public_taker_flow_horizon_foundation", "classification"), "KEEP_24H"),
        (("predictive_public_taker_flow_horizon_foundation", "champion_status"), "CHAMPION"),
        (("chat_handover", "search_memory_reset_on_new_chat"), True),
        (("predictive_v2_internal_structure_selective", "stage1_substrate_debt"), "REPAIRED"),
    ],
)
def test_schema_rejects_governed_drift(path: tuple[str, ...], value: object) -> None:
    state = read_json("state/current_state.json")
    target = state
    for name in path[:-1]:
        target = target[name]
    target[path[-1]] = value
    assert state_errors(state)


def test_schema_rejects_unknown_fields_and_missing_blocks() -> None:
    state = read_json("state/current_state.json")
    state["predictive_public_taker_flow_1h_incremental"]["threshold"] = 0.6
    assert state_errors(state)
    state = read_json("state/current_state.json")
    del state["chat_handover"]
    assert state_errors(state)


def test_hypothesis_and_experiment_identifiers_are_distinct() -> None:
    record = read_json("state/current_state.json")["predictive_public_taker_flow_1h_incremental"]
    assert record["hypothesis_id"] == "H-PRED-V2-PUBLIC-FLOW-INCREMENTAL-001"
    assert record["experiment_id"] == "EXP-PRED-V2-006-PUBLIC-TAKER-FLOW-1H-INCREMENTAL"
    assert not (ROOT / "research/experiments" / record["experiment_id"]).exists()
    gate = record["power_gate"]
    assert gate["proxy_classification"] == "ANALOG_DEPENDENCE_AND_VARIANCE_PROXY"
    assert gate["pass_authorizes_execution"] is False


PROTOCOL = "research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md"
HISTORICAL_PROTOCOL_RAW = "6fb5da71b18a44bd6c8891f50b0490311f48a988eef27ea46ff66546762fe012"
PROTOCOL_CANONICAL = "fdb355fcb66566f83c0a10ff646ebf8647ccc1c83289bbec2ab1e2a84801b7cd"


def test_canonical_text_digest_ignores_only_newline_encoding(tmp_path: Path) -> None:
    lf = "héllo  \n\tworld\n".encode()
    variants = {
        "lf": lf,
        "crlf": lf.replace(b"\n", b"\r\n"),
        "cr": lf.replace(b"\n", b"\r"),
    }
    digests = set()
    for name, payload in variants.items():
        path = tmp_path / name
        path.write_bytes(payload)
        digests.add(canonical_text_sha256(path))
    assert digests == {hashlib.sha256(lf).hexdigest()}
    changed = tmp_path / "changed"
    changed.write_bytes(lf.replace(b"world", b"World"))
    assert canonical_text_sha256(changed) not in digests
    spaced = tmp_path / "spaced"
    spaced.write_bytes(lf.replace(b"  \n", b"\n"))  # whitespace is not normalized
    assert canonical_text_sha256(spaced) not in digests
    invalid = tmp_path / "invalid"
    invalid.write_bytes(b"\xff\xfe")
    with pytest.raises(TextProvenanceError):
        canonical_text_sha256(invalid)


def test_the_historical_protocol_hash_is_preserved_not_rewritten() -> None:
    result = read_json(
        "research/experiments/EXP-PRED-V2-005-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION/result.json"
    )
    assert result["protocol"]["sha256"] == HISTORICAL_PROTOCOL_RAW
    record = read_json(validation.TEXT_PROVENANCE_PATH)
    [protocol] = [item for item in record["dependencies"] if item["path"] == PROTOCOL]
    assert protocol["raw_sha256"] == HISTORICAL_PROTOCOL_RAW
    assert protocol["canonical_text_sha256"] == PROTOCOL_CANONICAL
    assert canonical_text_sha256(ROOT / PROTOCOL) == PROTOCOL_CANONICAL
    assert record["historical_result_rewritten"] is False


def _mirror(tmp_path: Path) -> Path:
    """A minimal repository copy holding every file the text provenance check reads."""
    record = read_json(validation.TEXT_PROVENANCE_PATH)
    paths = {validation.TEXT_PROVENANCE_PATH, "state/current_state.json"}
    for item in record["dependencies"]:
        paths.add(item["path"])
        paths.update(location["artifact"] for location in item["recorded_at"])
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    return tmp_path


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_validator_accepts_lf_and_crlf_checkouts_of_the_same_protocol(
    tmp_path: Path, newline: bytes
) -> None:
    root = _mirror(tmp_path)
    text = canonical_text_bytes((ROOT / PROTOCOL).read_bytes())
    (root / PROTOCOL).write_bytes(text.replace(b"\n", newline))
    state = read_json("state/current_state.json")
    relations = validation.validate_text_provenance(root, state)
    # The historical pin was taken over CRLF bytes; an LF checkout is canonically equal.
    expected = RAW_IDENTICAL if newline == b"\r\n" else CANONICAL_TEXT_EQUIVALENT
    assert relations[PROTOCOL] == expected


def test_validator_rejects_a_real_protocol_change(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    original = (ROOT / PROTOCOL).read_bytes()
    (root / PROTOCOL).write_bytes(original.replace(b"24h", b"12h", 1))
    with pytest.raises(validation.TakerFlowValidationError, match="canonical text"):
        validation.validate_text_provenance(root, read_json("state/current_state.json"))


def test_validator_rejects_a_rewritten_historical_raw_pin(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    result_path = root / "research/experiments" / EXPERIMENT / "result.json"
    document = json.loads(result_path.read_text(encoding="utf-8"))
    document["protocol"]["sha256"] = PROTOCOL_CANONICAL
    result_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(validation.TakerFlowValidationError, match="preserved raw digest"):
        validation.validate_text_provenance(root, read_json("state/current_state.json"))


def test_top_level_pointers_are_derived_from_records() -> None:
    state = read_json("state/current_state.json")
    pointers = validation.expected_state_pointers(ROOT, state)
    assert pointers["latest_executor_checkpoint"] == (
        "PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1"
    )
    assert pointers["next_recommended_work_package"] == (
        "IMPLEMENT-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1"
    )
    validation.validate_state_pointers(ROOT, state)
    state["latest_executor_checkpoint"] = "PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1"
    with pytest.raises(validation.TakerFlowValidationError, match="stale"):
        validation.validate_state_pointers(ROOT, state)


def test_the_manifest_is_development_only_and_official() -> None:
    manifest = validation.validate_manifest(ROOT)
    assert manifest["objects"] == 120
    assert max(entry["month"] for entry in manifest["archives"]) == "2024-12"
    assert min(entry["month"] for entry in manifest["archives"]) == "2020-01"
    assert all(
        entry["url"].startswith("https://data.binance.vision/") for entry in manifest["archives"]
    )
