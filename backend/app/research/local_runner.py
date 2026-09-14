"""Allowlisted, owner-initiated local research execution.

Runtime records live outside the canonical scientific record.  This module never
accepts commands or configuration from HTTP callers: a candidate id resolves to a
fixed in-process adapter registered in source control.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import threading
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parents[3]
RUN_ROOT = ROOT / "data/research_runs"
TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED"})
RUNNABLE_CANDIDATE_STATUSES = frozenset({"AVAILABLE", "PREREGISTERED_AVAILABLE"})


class RunnerError(RuntimeError):
    """Base error for the local research runner."""


class UnknownCandidateError(RunnerError):
    """The caller supplied an id absent from the source-controlled allowlist."""


class RunConflictError(RunnerError):
    """Only one local research run may be active."""


class RequiredDataError(RunnerError):
    """The fixed candidate's governed local inputs are not installed."""


class CandidateGateError(RunnerError):
    """The source-controlled preregistration identity is absent or has drifted."""


class RunNotFoundError(RunnerError):
    """No persisted runtime record has the requested id."""


class CandidateAdapter(Protocol):
    def __call__(self, context: RunContext) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CandidateDefinition:
    candidate_id: str
    display_name: str
    purpose: str
    run_type: str
    status: str
    expected_stages: tuple[str, ...]
    required_local_datasets: tuple[str, ...]
    fixed_runner_adapter: str
    scientific_warning: str
    scientific_evidence_type: str
    execution_counts_as_new_evidence: bool
    preregistration_sha256: tuple[tuple[str, str], ...]
    adapter: CandidateAdapter

    def preregistration_ready(self, root: Path) -> bool:
        return all(
            (root / relative).is_file()
            and hashlib.sha256((root / relative).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            == expected
            for relative, expected in self.preregistration_sha256
        )

    def readiness(self, root: Path) -> dict[str, Any]:
        files = {relative: (root / relative).is_file() for relative in self.required_local_datasets}
        return {"ready": all(files.values()), "files": files}

    def public_record(self, root: Path) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "display_name": self.display_name,
            "purpose": self.purpose,
            "run_type": self.run_type,
            "status": self.status,
            "runnable": self.status in RUNNABLE_CANDIDATE_STATUSES,
            "expected_stages": list(self.expected_stages),
            "required_local_datasets": list(self.required_local_datasets),
            "required_data": self.readiness(root),
            "fixed_runner_adapter": self.fixed_runner_adapter,
            "scientific_warning": self.scientific_warning,
            "scientific_evidence_type": self.scientific_evidence_type,
            "execution_counts_as_new_evidence": self.execution_counts_as_new_evidence,
            "preregistration_frozen": self.preregistration_ready(root),
            "preregistration_paths": [path for path, _ in self.preregistration_sha256],
            "arbitrary_execution": False,
        }


class CandidateRegistry:
    def __init__(self, candidates: tuple[CandidateDefinition, ...]):
        ids = [candidate.candidate_id for candidate in candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate ids must be unique")
        if any(
            candidate.run_type == "NEW_EXPERIMENT" and not candidate.preregistration_sha256
            for candidate in candidates
        ):
            raise ValueError("a new experiment needs a source-controlled preregistration hash")
        self._candidates = {candidate.candidate_id: candidate for candidate in candidates}

    def get(self, candidate_id: str) -> CandidateDefinition:
        try:
            return self._candidates[candidate_id]
        except KeyError as exc:
            raise UnknownCandidateError("candidate is not in the fixed allowlist") from exc

    def public_records(self, root: Path) -> list[dict[str, Any]]:
        return [candidate.public_record(root) for candidate in self._candidates.values()]

    def __len__(self) -> int:
        return len(self._candidates)


class RunStore:
    """Small atomic JSON store for non-canonical local execution state."""

    def __init__(self, path: Path):
        self.path = path
        self.lock_path = path / "active.lock"
        self._mutex = threading.RLock()
        self.path.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        if not run_id or any(character not in "0123456789abcdef-" for character in run_id):
            raise RunNotFoundError("invalid run id")
        return self.path / f"{run_id}.json"

    def write(self, record: Mapping[str, Any]) -> None:
        target = self._path(str(record["run_id"]))
        with self._mutex:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path, delete=False, suffix=".staging"
            ) as handle:
                json.dump(record, handle, indent=2, sort_keys=True, allow_nan=False)
                handle.write("\n")
                staging = Path(handle.name)
            os.replace(staging, target)

    def read(self, run_id: str) -> dict[str, Any]:
        path = self._path(run_id)
        if not path.is_file():
            raise RunNotFoundError("local research run was not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def latest(self) -> dict[str, Any] | None:
        paths = sorted(self.path.glob("*.json"), key=lambda item: item.stat().st_mtime_ns)
        return json.loads(paths[-1].read_text(encoding="utf-8")) if paths else None

    def records(self) -> list[dict[str, Any]]:
        """Return persisted runs without treating runtime state as scientific truth."""
        paths = sorted(self.path.glob("*.json"), key=lambda item: item.stat().st_mtime_ns)
        return [json.loads(path.read_text(encoding="utf-8")) for path in paths]

    def acquire(self, run_id: str) -> None:
        with self._mutex:
            try:
                descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError as exc:
                raise RunConflictError("another local research run is active") from exc
            with os.fdopen(descriptor, "w", encoding="ascii") as handle:
                json.dump({"schema_version": 1, "run_id": run_id, "owner_pid": os.getpid()}, handle)

    def release(self, run_id: str) -> None:
        with self._mutex:
            if self.lock_path.is_file() and self._lock_identity()[0] == run_id:
                self.lock_path.unlink()

    def _lock_identity(self) -> tuple[str, int | None]:
        raw = self.lock_path.read_text(encoding="ascii").strip()
        try:
            lock = json.loads(raw)
        except json.JSONDecodeError:
            return raw, None  # Compatibility with runner locks created before schema v1.
        if not isinstance(lock, dict):
            return "", None
        run_id = lock.get("run_id")
        owner_pid = lock.get("owner_pid")
        return (
            run_id if isinstance(run_id, str) else "",
            owner_pid if isinstance(owner_pid, int) and owner_pid > 0 else None,
        )

    def recover_interrupted(self) -> None:
        """A process restart cannot resume a fit, so it records an honest failure."""
        with self._mutex:
            if not self.lock_path.is_file():
                return
            run_id, owner_pid = self._lock_identity()
            if owner_pid is not None and _process_is_alive(owner_pid):
                return
            try:
                record = self.read(run_id)
            except RunNotFoundError:
                self.lock_path.unlink(missing_ok=True)
                return
            if record.get("status") not in TERMINAL_STATUSES:
                now = utc_now()
                record.update(
                    status="FAILED",
                    stage="INTERRUPTED",
                    finished_at=now,
                    error="Backend restarted while the local research run was active.",
                )
                self.write(record)
            self.lock_path.unlink(missing_ok=True)


def _process_is_alive(pid: int) -> bool:
    """Check a lock owner's liveness without sending it a signal on Windows."""
    if sys.platform == "win32":
        import ctypes

        process = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)
        if not process:
            return False
        try:
            return ctypes.windll.kernel32.WaitForSingleObject(process, 0) == 0x00000102
        finally:
            ctypes.windll.kernel32.CloseHandle(process)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@dataclass(frozen=True)
class RunContext:
    root: Path
    run_dir: Path
    run_id: str
    candidate: CandidateDefinition
    progress: Callable[[str, int, str | None], None]


RESULT_FIELDS = frozenset(
    {
        "candidate_id",
        "run_id",
        "status",
        "classification",
        "verdict",
        "default_expectancy_r",
        "zero_cost_expectancy_r",
        "double_cost_expectancy_r",
        "delay_expectancy_r",
        "trade_count",
        "nonnegative_folds",
        "fold_count",
        "minimum_fold_trades",
        "control_default_expectancy_r",
        "primary_minus_control_r",
        "oos_correlation",
        "reconciliation_status",
        "scientific_evidence_type",
    }
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def elapsed_seconds(record: Mapping[str, Any]) -> float:
    start = datetime.fromisoformat(str(record["started_at"]))
    end_text = record.get("finished_at") or utc_now()
    end = datetime.fromisoformat(str(end_text))
    return max(0.0, (end - start).total_seconds())


def validate_result(result: Mapping[str, Any], context: RunContext) -> None:
    missing = RESULT_FIELDS - result.keys()
    if missing:
        raise RunnerError(f"candidate result contract missing: {sorted(missing)}")
    if result["candidate_id"] != context.candidate.candidate_id:
        raise RunnerError("candidate result identity mismatch")
    if result["run_id"] != context.run_id or result["status"] != "COMPLETED":
        raise RunnerError("candidate returned an invalid run identity or status")
    if result["scientific_evidence_type"] != context.candidate.scientific_evidence_type:
        raise RunnerError("candidate changed its frozen evidence classification")


def build_review_bundle(result: Mapping[str, Any]) -> str:
    payload = {
        "bundle_version": "RESEARCH_RUNNER_REVIEW_BUNDLE_V1",
        "candidate": result["candidate_id"],
        "run_id": result["run_id"],
        "run_kind": result["scientific_evidence_type"],
        "code_head": result.get("code_head"),
        "dataset_identities": result.get("dataset_identities", {}),
        "reproduction_hashes": result.get("runtime_artifact_hashes", {}),
        "classification": result["classification"],
        "verdict": result["verdict"],
        "metrics": {
            key: result[key]
            for key in (
                "default_expectancy_r",
                "zero_cost_expectancy_r",
                "double_cost_expectancy_r",
                "delay_expectancy_r",
                "trade_count",
                "nonnegative_folds",
                "fold_count",
                "minimum_fold_trades",
                "oos_correlation",
                "elapsed_seconds",
            )
            if key in result
        },
        "fold_summary": result.get("fold_summary", []),
        "cost_stress": result.get("cost_stress", {}),
        "control_comparison": {
            "control_default_expectancy_r": result["control_default_expectancy_r"],
            "primary_minus_control_r": result["primary_minus_control_r"],
        },
        "reconciliation_status": result["reconciliation_status"],
        "warnings": result.get("warnings", []),
        "new_experiment": bool(result.get("new_experiment", False)),
    }
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False)


class LocalResearchRunner:
    def __init__(
        self, registry: CandidateRegistry, root: Path = ROOT, store: RunStore | None = None
    ):
        self.registry = registry
        self.root = root
        self.store = store or RunStore(root / "data/research_runs")
        self._mutex = threading.Lock()
        self.store.recover_interrupted()

    def overview(self) -> dict[str, Any]:
        latest = self.store.latest()
        return {
            "runner_status": (
                "BUSY" if latest and latest.get("status") not in TERMINAL_STATUSES else "IDLE"
            ),
            "arbitrary_execution": False,
            "maximum_active_runs": 1,
            "candidates": self.registry.public_records(self.root),
            "current_or_last_run": self._public_run(latest) if latest else None,
        }

    def read(self, run_id: str) -> dict[str, Any]:
        return self._public_run(self.store.read(run_id))

    def start(self, candidate_id: str) -> dict[str, Any]:
        candidate = self.registry.get(candidate_id)
        if candidate.status not in RUNNABLE_CANDIDATE_STATUSES:
            raise CandidateGateError(f"candidate is not runnable: {candidate.status}")
        if not candidate.preregistration_ready(self.root):
            raise CandidateGateError("candidate preregistration identity is not frozen")
        readiness = candidate.readiness(self.root)
        if not readiness["ready"]:
            missing = [path for path, ready in readiness["files"].items() if not ready]
            raise RequiredDataError(f"required local datasets are unavailable: {missing}")
        run_id = uuid.uuid4().hex
        now = utc_now()
        record: dict[str, Any] = {
            "schema_version": 1,
            "run_id": run_id,
            "candidate_id": candidate_id,
            "status": "QUEUED",
            "stage": "READY",
            "progress": 0,
            "detail": None,
            "started_at": now,
            "finished_at": None,
            "error": None,
            "result": None,
            "review_bundle": None,
            "scientific_record_mutated": False,
        }
        with self._mutex:
            if candidate.run_type == "NEW_EXPERIMENT" and any(
                record.get("candidate_id") == candidate_id for record in self.store.records()
            ):
                raise RunConflictError(
                    "this preregistered new experiment already has a local execution record"
                )
            self.store.acquire(run_id)
            try:
                self.store.write(record)
                thread = threading.Thread(
                    target=self._execute,
                    args=(candidate, record),
                    name=f"research-{run_id[:8]}",
                    daemon=True,
                )
                thread.start()
            except Exception:
                self.store.release(run_id)
                raise
        return self._public_run(record)

    def _execute(self, candidate: CandidateDefinition, initial: dict[str, Any]) -> None:
        run_id = str(initial["run_id"])
        run_dir = self.store.path / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        def progress(stage: str, value: int, detail: str | None = None) -> None:
            if stage not in candidate.expected_stages:
                raise RunnerError(f"adapter emitted undeclared stage: {stage}")
            if not 0 <= value <= 100:
                raise RunnerError("progress must be between 0 and 100")
            record = self.store.read(run_id)
            record.update(status="RUNNING", stage=stage, progress=value, detail=detail)
            self.store.write(record)

        context = RunContext(self.root, run_dir, run_id, candidate, progress)
        try:
            progress("PREPARING_DATA", 2, "Verifica degli input locali governati")
            result = candidate.adapter(context)
            validate_result(result, context)
            record = self.store.read(run_id)
            finished = utc_now()
            record.update(
                status="COMPLETED",
                stage="COMPLETED",
                progress=100,
                detail="Esecuzione completata",
                finished_at=finished,
                result=result,
                review_bundle=build_review_bundle(result),
            )
            result["elapsed_seconds"] = elapsed_seconds(record)
            record["review_bundle"] = build_review_bundle(result)
            self.store.write(record)
        except Exception as exc:
            record = self.store.read(run_id)
            record.update(
                status="FAILED",
                stage="FAILED",
                finished_at=utc_now(),
                error=f"{type(exc).__name__}: {exc}",
            )
            self.store.write(record)
        finally:
            self.store.release(run_id)

    @staticmethod
    def _public_run(record: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(record)
        payload["elapsed_seconds"] = elapsed_seconds(record)
        return payload


def research_candidate_registry() -> CandidateRegistry:
    from .wp015_reproduction import REQUIRED_DATASETS, run_wp015_reproduction
    from .wp016_runner import (
        EVIDENCE_TYPE as WP016_EVIDENCE_TYPE,
    )
    from .wp016_runner import (
        REQUIRED_DATASETS as WP016_REQUIRED_DATASETS,
    )
    from .wp016_runner import run_wp016_attention

    funding_manifest = json.loads(
        (ROOT / "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json").read_text(encoding="utf-8")
    )
    attention_manifest = json.loads(
        (ROOT / "data/manifests/WIKIMEDIA-BITCOIN-PAGEVIEWS-DEV-v1.json").read_text(
            encoding="utf-8"
        )
    )
    wp016_required_datasets = tuple(
        dict.fromkeys(
            (
                *WP016_REQUIRED_DATASETS,
                *(item["path"] for item in funding_manifest["raw_requests"]),
                *(item["path"] for item in attention_manifest["raw_requests"]),
            )
        )
    )

    stages = (
        "READY",
        "PREPARING_DATA",
        "VALIDATING_INPUTS",
        "FOLD_2020",
        "FOLD_2021",
        "FOLD_2022",
        "FOLD_2023",
        "FOLD_2024",
        "COST_STRESS",
        "RECONCILIATION",
        "FINALIZING",
        "COMPLETED",
        "FAILED",
        "INTERRUPTED",
    )
    return CandidateRegistry(
        (
            CandidateDefinition(
                candidate_id="WP016_WIKIPEDIA_ATTENTION_V1",
                display_name="WP-016 · Shock di attenzione Wikipedia",
                purpose=(
                    "Valuta se l'attenzione pubblica anomala verso Bitcoin aggiunge "
                    "informazione ai segnali spot e al funding già congelati."
                ),
                run_type="NEW_EXPERIMENT",
                status="BLOCKED_PROJECT_RETROSPECTIVE_V1",
                expected_stages=stages,
                required_local_datasets=wp016_required_datasets,
                fixed_runner_adapter="app.research.wp016_runner.run_wp016_attention",
                scientific_warning=(
                    "BLOCKED BEFORE EXECUTION: the retrospective could not establish "
                    "point-in-time vintage integrity for the historical pageview series."
                ),
                scientific_evidence_type=WP016_EVIDENCE_TYPE,
                execution_counts_as_new_evidence=True,
                preregistration_sha256=(
                    (
                        "research/experiments/EXP-ML-026-INTERNAL-FUNDING-PLUS-ATTENTION-HGBR/preregistration.json",
                        "164f7ee45e3301f3a6a908685f6fcd7d4eebd629990588283df04428b1842984",
                    ),
                    (
                        "research/experiments/EXP-ML-027-INTERNAL-PLUS-FUNDING-HGBR-MATCHED-ATTENTION/preregistration.json",
                        "da04ab767e46b7b0ca172d6276521abbfb40d71f2fdbc27e7f3bbde43087be1a",
                    ),
                ),
                adapter=run_wp016_attention,
            ),
            CandidateDefinition(
                candidate_id="WP015_REPRODUCTION_V1",
                display_name="WP-015 · Contesto funding perpetual",
                purpose=(
                    "Riproduce localmente il test storico WP-015 già pubblicato, con la "
                    "configurazione congelata e il controllo interno abbinato."
                ),
                run_type="REPRODUCTION_ONLY",
                status="AVAILABLE",
                expected_stages=stages,
                required_local_datasets=REQUIRED_DATASETS,
                fixed_runner_adapter="app.research.wp015_reproduction.run_wp015_reproduction",
                scientific_warning=(
                    "REPRODUCTION ONLY · NOT A NEW EXPERIMENT · DOES NOT CHANGE SCIENTIFIC "
                    "COUNTERS · DOES NOT CREATE SEALED EVIDENCE"
                ),
                scientific_evidence_type=("REPRODUCTION_OF_ALREADY_EXPOSED_DEVELOPMENT_RESULT"),
                execution_counts_as_new_evidence=False,
                preregistration_sha256=(
                    (
                        "research/experiments/EXP-ML-024-INTERNAL-PLUS-FUNDING-HGBR/preregistration.json",
                        "33da6b2748e05d839debbe418e8ed77ba5b15c759dd3215b662f6f95c649e3f1",
                    ),
                    (
                        "research/experiments/EXP-ML-025-INTERNAL-HGBR-MATCHED-FUNDING/preregistration.json",
                        "41dc813a7bd4171b6716f8cf059d5c0384778b88f174e5886e4cb172f584f246",
                    ),
                ),
                adapter=run_wp015_reproduction,
            ),
        )
    )


def wp015_registry() -> CandidateRegistry:
    """Compatibility alias for callers written before the WP-016 registry extension."""
    return research_candidate_registry()


@lru_cache(maxsize=1)
def default_runner() -> LocalResearchRunner:
    return LocalResearchRunner(research_candidate_registry())


__all__ = [
    "CandidateDefinition",
    "CandidateGateError",
    "CandidateRegistry",
    "LocalResearchRunner",
    "RequiredDataError",
    "RunConflictError",
    "RunContext",
    "RunNotFoundError",
    "RunStore",
    "UnknownCandidateError",
    "build_review_bundle",
    "default_runner",
    "research_candidate_registry",
    "wp015_registry",
]
