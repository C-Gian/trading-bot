"""Bounded sealed evaluator: eligibility, immutability, budget, and atomic finality.

The evaluator never browses sealed data. It executes exactly one preregistered,
frozen request, emits only declared metrics, and consumes budget before finalizing.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema

from app.data.policy import CUTOFF, parse_utc_instant

from .isolation import SealedAccessDenied, is_sealed_path

ROOT = Path(__file__).resolve().parents[3]
BUDGET_PATH = Path("research/sealed/SEALED_QUERY_BUDGET.json")
VERSION = "SEALED_EVALUATION_V1"
LOCKED = "LOCKED_NO_AUTHORIZED_QUERY"
ELIGIBLE = "PROMISING_DEVELOPMENT_ONLY"
MetricRunner = Callable[[Mapping[str, Any]], Mapping[str, Any]]


class SealedEvaluationError(ValueError):
    """A sealed request failed a governance gate; nothing was evaluated."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SealedEvaluationError(message)


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def request_identity(request: Mapping[str, Any]) -> str:
    """The frozen identity of everything a request may not change after submission."""
    return canonical_hash({key: value for key, value in request.items() if key != "request_hash"})


def _ledger_entries(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def load_budget(root: Path = ROOT) -> dict[str, Any]:
    document = json.loads((root / BUDGET_PATH).read_text(encoding="utf-8"))
    _require(document["schema_version"] == 1 and document["version"] == VERSION, "unknown budget")
    for name, scope in document["scopes"].items():
        authorized, consumed = scope["authorized_queries"], scope["consumed_queries"]
        _require(0 <= consumed <= authorized, f"{name} budget is incoherent")
        _require(
            (scope["status"] == LOCKED) == (authorized == 0),
            f"{name} status disagrees with its authorized query count",
        )
        _require(
            scope["authorization_record"] is not None or authorized == 0,
            f"{name} claims authorized queries without an authorization record",
        )
        ledger = root / scope["consumption_ledger"]
        _require(ledger.is_file(), f"{name} has no append-only consumption ledger")
        _require(
            len(_ledger_entries(ledger)) == consumed,
            f"{name} consumed count differs from its append-only ledger",
        )
    return document


def public_status(root: Path = ROOT) -> dict[str, Any]:
    """Bounded, non-exploratory projection for the research UI and API."""
    document = load_budget(root)
    return {
        "version": document["version"],
        "isolation": document["isolation_policy"],
        "scopes": [
            {
                "scope": name,
                "symbol": scope["symbol"],
                "dataset_state": scope["dataset_state"],
                "status": scope["status"],
                "authorized_queries": scope["authorized_queries"],
                "consumed_queries": scope["consumed_queries"],
            }
            for name, scope in sorted(document["scopes"].items())
        ],
    }


class SealedEvaluator:
    """One evaluator per repository root; it holds no sealed data of its own."""

    def __init__(self, root: Path = ROOT):
        self.root = root
        self.schema = json.loads(
            (root / "contracts/sealed_evaluation_request.schema.json").read_text(encoding="utf-8")
        )
        self.result_schema = json.loads(
            (root / "contracts/sealed_evaluation_result.schema.json").read_text(encoding="utf-8")
        )

    def _scope(self, document: Mapping[str, Any], name: str) -> dict[str, Any]:
        _require(name in document["scopes"], f"unknown sealed scope: {name}")
        return dict(document["scopes"][name])

    def _eligibility(self, document: Mapping[str, Any], experiment_id: str) -> dict[str, Any]:
        path = self.root / document["eligibility_table"]
        _require(path.is_file(), "sealed candidate eligibility table is missing")
        table = json.loads(path.read_text(encoding="utf-8"))
        rows = [row for row in table["candidates"] if row["experiment_id"] == experiment_id]
        _require(len(rows) == 1, f"candidate is not in the eligibility table: {experiment_id}")
        return rows[0]

    def _validate_candidate(self, row: Mapping[str, Any], request: Mapping[str, Any]) -> None:
        candidate = request["candidate"]
        _require(
            row["terminal_classification"] == candidate["terminal_classification"],
            "request restates a development classification the eligibility table does not hold",
        )
        _require(
            row["terminal_classification"] == ELIGIBLE,
            f"candidate is not seal-eligible: {row['terminal_classification']}",
        )
        _require(
            row["structural_validator"] == "PASS", "candidate structural validator is not PASS"
        )
        _require(
            row["search_memory_v2_binding"] == "VALID",
            "candidate SEARCH_MEMORY_V2 binding is not valid",
        )
        _require(
            row["unresolved_material_integrity_issues"] == 0,
            "candidate has an unresolved material integrity issue",
        )
        allocation = row["sealed_allocation"]
        _require(
            allocation is not None
            and allocation["allocation_id"] == request["allocation"]["allocation_id"],
            "candidate lacks an explicit Research Director sealed allocation for this query",
        )
        _require(
            row["executable_spec_hash"] == request["executable_spec_hash"],
            "candidate executable spec identity differs from the eligibility table",
        )

    def _validate_identity(self, request: Mapping[str, Any]) -> None:
        for item in request["dependencies"]:
            path = self.root / item["path"]
            _require(path.is_file(), f"declared dependency is missing: {item['path']}")
            _require(
                text_sha256(path) == item["sha256"],
                f"code/config drift since the request was frozen: {item['path']}",
            )
        _require(
            canonical_hash(sorted([x["path"], x["sha256"]] for x in request["dependencies"]))
            == request["dependency_hash"],
            "dependency hash differs from the declared dependency set",
        )
        result_path = self.root / request["candidate"]["development_result_path"]
        _require(result_path.is_file(), "development result is missing")
        digest = text_sha256(result_path)
        _require(
            digest == request["candidate"]["development_result_sha256"]
            and digest == request["development_result_hash"],
            "development result identity differs from the frozen request",
        )

    def _validate_separation(
        self, document: Mapping[str, Any], scope: Mapping[str, Any], request: Mapping[str, Any]
    ) -> None:
        interval = request["sealed_interval"]
        _require(
            is_sealed_path(interval["path"], self.root),
            "sealed dataset must live under a registered sealed root",
        )
        start, end = parse_utc_instant(interval["start"]), parse_utc_instant(interval["end"])
        _require(start > CUTOFF, "sealed interval must start after the development cutoff")
        _require(end >= start, "sealed interval is empty")
        _require(
            parse_utc_instant(scope["sealed_interval_start"]) <= start,
            "sealed interval precedes the scope's reserved boundary",
        )
        development = json.loads(
            (self.root / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json").read_text(encoding="utf-8")
        )
        _require(
            interval["dataset_id"] != development["manifest_id"]
            and interval["content_hash"] != development["content_hash"]["value"],
            "sealed and development datasets must be separate identities",
        )
        _require(
            document["isolation_policy"].endswith("NOT_OS_ENFORCED"), "isolation claim changed"
        )

    def _validate_metrics(self, request: Mapping[str, Any], produced: Mapping[str, Any]) -> None:
        declared = set(request["allowed_secondary_metrics"])
        _require(
            request["primary_metric"] not in declared,
            "the primary metric cannot also be declared as secondary",
        )
        _require(
            request["primary_metric"] in produced,
            "the evaluator produced no value for the declared primary metric",
        )
        extra = set(produced) - declared - {request["primary_metric"]}
        _require(not extra, f"undeclared sealed metric produced: {sorted(extra)}")

    def _consume(self, scope: Mapping[str, Any], request: Mapping[str, Any]) -> int:
        """Append-only consumption; nothing downstream can restore this capacity."""
        ledger = self.root / scope["consumption_ledger"]
        index = len(_ledger_entries(ledger)) + 1
        record = {
            "consumed_query_index": index,
            "query_id": request["query_id"],
            "scope": request["scope"],
            "candidate_experiment_id": request["candidate"]["experiment_id"],
            "executable_spec_hash": request["executable_spec_hash"],
            "request_hash": request["request_hash"],
            "consumed_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        with ledger.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        return index

    def _finalize(self, path: Path, payload: dict[str, Any]) -> None:
        if path.exists():
            raise SealedEvaluationError("a finalized sealed result is immutable")
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
        ) as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            staging = Path(handle.name)
        try:
            jsonschema.Draft202012Validator(
                self.result_schema, format_checker=jsonschema.FormatChecker()
            ).validate(payload)
            if path.exists():
                raise SealedEvaluationError("a finalized sealed result is immutable")
            os.link(staging, path)
        finally:
            staging.unlink(missing_ok=True)

    def evaluate(self, request: Mapping[str, Any], runner: MetricRunner) -> dict[str, Any]:
        """Run one authorized sealed query. Budget is consumed before any result exists."""
        jsonschema.Draft202012Validator(
            self.schema, format_checker=jsonschema.FormatChecker()
        ).validate(request)
        document = load_budget(self.root)
        scope = self._scope(document, request["scope"])
        authorized = scope["authorized_queries"]
        if scope["status"] == LOCKED or authorized <= scope["consumed_queries"]:
            raise SealedAccessDenied(
                f"no authorized sealed query for {request['scope']}: {scope['status']}"
            )
        _require(
            request["query_budget"]["authorized_queries"] <= authorized,
            "request claims more authorization than the budget grants",
        )
        _require(
            request_identity(request) == request["request_hash"],
            "request was mutated after it was frozen",
        )
        self._validate_candidate(
            self._eligibility(document, request["candidate"]["experiment_id"]), request
        )
        self._validate_identity(request)
        self._validate_separation(document, scope, request)
        ledger = self.root / scope["consumption_ledger"]
        for entry in _ledger_entries(ledger):
            _require(entry["query_id"] != request["query_id"], "duplicate sealed query identity")
            _require(
                (entry["candidate_experiment_id"], entry["executable_spec_hash"])
                != (request["candidate"]["experiment_id"], request["executable_spec_hash"]),
                "this candidate identity has already consumed a sealed query",
            )
        result_path = self.root / scope["result_directory"] / f"{request['query_id']}.json"
        _require(not result_path.exists(), "a finalized sealed result is immutable")
        index = self._consume(scope, request)
        try:
            produced = dict(runner(request))
            self._validate_metrics(request, produced)
            primary = produced.pop(request["primary_metric"])
            status, secondary = "COMPLETED", produced
        except SealedEvaluationError:
            raise
        except Exception:
            status, primary, secondary = "EXECUTION_FAILED", None, {}
        payload: dict[str, Any] = {
            "schema_version": 1,
            "version": VERSION,
            "query_id": request["query_id"],
            "scope": request["scope"],
            "candidate_experiment_id": request["candidate"]["experiment_id"],
            "candidate_experiment_version": request["candidate"]["experiment_version"],
            "request_hash": request["request_hash"],
            "executable_spec_hash": request["executable_spec_hash"],
            "dependency_hash": request["dependency_hash"],
            "sealed_dataset_id": request["sealed_interval"]["dataset_id"],
            "sealed_content_hash": request["sealed_interval"]["content_hash"],
            "status": status,
            "primary_metric": request["primary_metric"],
            "primary_result": primary,
            "secondary_results": secondary,
            "robustness_profiles": list(request["robustness_profiles"]),
            "consumed_query_index": index,
            "finalized_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "evidence_stage": "SEALED_LOCKED_EVALUATION",
            "interpretation": (
                "Sealed locked evaluation of one preregistered candidate. It is not forward "
                "evidence, not a Champion promotion, and not permission for real capital."
            ),
        }
        payload["result_hash"] = canonical_hash(payload)
        self._finalize(result_path, payload)
        return payload
