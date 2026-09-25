"""System G1 Development V1 staged batch runner with the hard execution guard (sections 14-17).

Phase A (selection, 2021-2022): all seven frozen configurations, primary execution; the automatic
selection and the complete table are written to the selection artifact before anything else.
Phase B (evaluation, 2023-2024): only the configuration the Phase-A artifact selected, plus the two
frozen robustness views (48bp costs; +5m delay), never combined.

Fail-closed rules:

- real observations are reachable only through `authorize_real_sources`, which refuses unless the
  canonical state carries an explicit Research Director G1 execution authorization whose record
  exists; importing, testing, `check.py --no-data` and synthetic replay never construct it;
- Phase B refuses before a Phase-A artifact exists, re-derives the selection from the artifact's
  table (no caller-supplied configuration exists), verifies protocol/code/source identities, and is
  impossible when Phase A selected nothing;
- each phase writes its artifact once; an existing artifact is never overwritten;
- real runs write only to the fixed experiment directory; synthetic runs never may.
There is no preview mode.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from . import scoring
from .bars import Bar
from .canonical import to_plain
from .development import (
    PROTOCOL_PATH,
    BookSpec,
    DevelopmentEngine,
    development_manifest,
    drive,
    primary_book,
    stress_books,
)
from .playbooks import CONFIGURATIONS

ROOT = Path(__file__).resolve().parents[3]
STATE_PATH = "state/current_state.json"
STATE_KEY = "system_g1_development"
RUN_DIR = "research/experiments/SYSTEM-G1-DEVELOPMENT-V1"
SELECTION_FILE = "PHASE-A-SELECTION.json"
EVALUATION_FILE = "PHASE-B-EVALUATION.json"
REAL_EVIDENCE = "EXPOSED_HISTORICAL_DEVELOPMENT_EVIDENCE"
SYNTHETIC_EVIDENCE = "SYNTHETIC_FIXTURE_NOT_MARKET_EVIDENCE"
GUARD_TOKEN = object()
CODE_PATHS = (
    "backend/app/g1/__init__.py",
    "backend/app/g1/bars.py",
    "backend/app/g1/batch.py",
    "backend/app/g1/canonical.py",
    "backend/app/g1/cycle.py",
    "backend/app/g1/development.py",
    "backend/app/g1/forecaster.py",
    "backend/app/g1/indicators.py",
    "backend/app/g1/ledger.py",
    "backend/app/g1/playbooks.py",
    "backend/app/g1/records.py",
    "backend/app/g1/scoring.py",
    "backend/app/g1/sources.py",
    "backend/app/g1/store.py",
    "backend/app/backtest/models.py",
)


class ExecutionNotAuthorized(PermissionError):
    """The canonical state does not authorize the single historical G1 batch."""


class StageLockError(RuntimeError):
    """A staged-execution rule would be violated."""


@dataclass(frozen=True)
class PhaseWindows:
    engine_start: datetime
    selection_start: datetime
    selection_end: datetime
    evaluation_start: datetime
    evaluation_end: datetime
    selection_years: tuple[int, ...]
    evaluation_years: tuple[int, ...]


FROZEN_WINDOWS = PhaseWindows(
    datetime(2020, 1, 1, tzinfo=UTC),
    datetime(2021, 1, 1, tzinfo=UTC),
    datetime(2023, 1, 1, tzinfo=UTC),
    datetime(2023, 1, 1, tzinfo=UTC),
    datetime(2025, 1, 1, tzinfo=UTC),
    scoring.SELECTION_YEARS,
    scoring.EVALUATION_YEARS,
)


def canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def code_identity(root: Path = ROOT) -> dict[str, str]:
    return {path: canonical_sha256(root / path) for path in CODE_PATHS}


def protocol_sha256(root: Path = ROOT) -> str:
    return canonical_sha256(root / PROTOCOL_PATH)


# ------------------------------------------------------------------ sources
@dataclass(frozen=True)
class SyntheticSource:
    """A synthetic stream for tests/replay. Never market data; never writes to RUN_DIR."""

    bars: tuple[Bar, ...]
    funding_rates: dict[datetime, Decimal]
    windows: PhaseWindows
    identity: Any
    evidence_class: str = SYNTHETIC_EVIDENCE

    def minutes(self) -> Iterator[Bar]:
        return iter(self.bars)

    def funding(self) -> dict[datetime, Decimal]:
        return dict(self.funding_rates)


def execution_authorization(root: Path = ROOT) -> dict[str, Any]:
    state = json.loads((root / STATE_PATH).read_text(encoding="utf-8"))
    return state.get(STATE_KEY, {})


PHASES = ("A", "B")


def authorize_real_sources(phase: str, root: Path = ROOT) -> Any:
    """The only path to real observations, scoped to one requested phase (ADR-0048).

    Refuses unless the canonical state has `historical_execution_authorized is True`, an existing
    `execution_authorization_record`, and `authorized_phase` equal to the requested phase.
    """
    if phase not in PHASES:
        raise ExecutionNotAuthorized(f"unknown System G1 phase {phase!r}")
    record = execution_authorization(root)
    decision = record.get("execution_authorization_record")
    if record.get("historical_execution_authorized") is not True or not decision:
        raise ExecutionNotAuthorized(
            "System G1 historical execution is not authorized by the canonical state"
        )
    if not (root / decision).is_file():
        raise ExecutionNotAuthorized(f"authorization record {decision} does not exist")
    if record.get("authorized_phase") != phase:
        raise ExecutionNotAuthorized(
            f"phase {phase} is not authorized (authorized_phase={record.get('authorized_phase')!r})"
        )
    from .sources import RealSourceHandle

    return RealSourceHandle(root, decision, GUARD_TOKEN, phase)


def _require_phase(source: Any, phase: str) -> None:
    """A real handle opened for one phase can never drive the other phase."""
    if not isinstance(source, SyntheticSource) and getattr(source, "phase", None) != phase:
        raise ExecutionNotAuthorized(f"the real source handle was not authorized for phase {phase}")


# ------------------------------------------------------------------ helpers
def _output_dir(source: Any, out_dir: Path, root: Path) -> Path:
    real = (root / RUN_DIR).resolve()
    if isinstance(source, SyntheticSource):
        if out_dir.resolve() == real:
            raise StageLockError("synthetic runs may never write to the G1 experiment directory")
        return out_dir
    if out_dir.resolve() != real:
        raise StageLockError("real runs write only to the fixed G1 experiment directory")
    return out_dir


def _windows(source: Any) -> PhaseWindows:
    return source.windows if isinstance(source, SyntheticSource) else FROZEN_WINDOWS


def _source_identity(source: Any) -> Any:
    return source.identity


def _evidence(source: Any) -> str:
    return source.evidence_class if isinstance(source, SyntheticSource) else REAL_EVIDENCE


def _identities(source: Any, root: Path) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL_PATH,
        "protocol_canonical_sha256": protocol_sha256(root),
        "code_canonical_sha256": code_identity(root),
        "source_identity": to_plain(_source_identity(source)),
        "configurations": list(CONFIGURATIONS),
    }


def _digest(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "artifact_sha256"}
    return hashlib.sha256(
        json.dumps(to_plain(body), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def artifact_digest(payload: dict[str, Any]) -> str:
    """Deterministic verification of a write-once phase artifact's self-hash."""
    return _digest(payload)


def _write_once(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        raise StageLockError(f"{path.name} already exists; a phase runs exactly once")
    payload = dict(payload)
    payload["artifact_sha256"] = _digest(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_plain(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def _run(
    source: Any, books: tuple[BookSpec, ...], end: datetime, windows: PhaseWindows
) -> DevelopmentEngine:
    manifest = development_manifest(
        (("source", json.dumps(to_plain(_source_identity(source)), sort_keys=True)[:4096]),),
        windows.engine_start,
        end,
        books,
        _evidence(source),
        protocol_sha256(),
    )
    engine = DevelopmentEngine(manifest, books, source.funding(), retain_records=False)
    drive(engine, _bounded(source.minutes(), windows.engine_start, end))
    engine.finish()
    return engine


def _bounded(minutes: Iterable[Bar], start: datetime, end: datetime) -> Iterator[Bar]:
    for bar in minutes:
        if bar.open_time < start:
            continue
        if bar.available_at > end:
            return
        yield bar


def _result(engine: DevelopmentEngine, book_id: str) -> scoring.BookResult:
    book = engine.books[book_id]
    return scoring.BookResult(
        book_id,
        book.spec.config_id,
        tuple(book.ledger.trades),
        len(book.ledger.trades),
        book.run_stop_triggered,
        tuple(book.equity_path),
    )


# ------------------------------------------------------------------ phases
def write_selection(
    out_dir: Path, source: Any, table: dict[str, dict[str, Any]], root: Path = ROOT
) -> dict[str, Any]:
    selected = scoring.select(table)
    return _write_once(
        out_dir / SELECTION_FILE,
        {
            "phase": "A_SELECTION",
            "evidence_class": _evidence(source),
            "windows": to_plain(_windows(source)),
            "identities": _identities(source, root),
            "configurations_inspected": list(table),
            "table": table,
            "selected_configuration": selected,
            "disposition": None if selected is not None else scoring.REJECTED_SELECTION,
            "phase_b_possible": selected is not None,
        },
    )


def run_phase_a(source: Any, out_dir: Path, root: Path = ROOT) -> dict[str, Any]:
    _require_phase(source, "A")
    out_dir = _output_dir(source, out_dir, root)
    if (out_dir / SELECTION_FILE).exists():
        raise StageLockError("Phase A has already been executed")
    windows = _windows(source)
    books = tuple(
        primary_book(config, windows.selection_start, windows.selection_end)
        for config in CONFIGURATIONS
    )
    engine = _run(source, books, windows.selection_end, windows)
    results = [_result(engine, book.book_id) for book in books]
    table = scoring.phase_a_table(results, windows.selection_years)
    return write_selection(out_dir, source, table, root)


def load_selection(out_dir: Path, source: Any, root: Path = ROOT) -> str:
    """Re-derive and verify the Phase-A selection; the only way Phase B learns its config."""
    path = out_dir / SELECTION_FILE
    if not path.is_file():
        raise StageLockError("Phase B cannot run before a Phase-A selection artifact exists")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact.get("artifact_sha256") != _digest(artifact):
        raise StageLockError("the Phase-A selection artifact was modified")
    if artifact["evidence_class"] != _evidence(source):
        raise StageLockError("the Phase-A artifact belongs to a different evidence class")
    if artifact["identities"] != to_plain(_identities(source, root)):
        raise StageLockError("protocol/code/source identities differ from Phase A")
    derived = scoring.select(_decimalized(artifact["table"]))
    if derived != artifact["selected_configuration"]:
        raise StageLockError("the recorded selection is not the automatic selection")
    if derived is None:
        raise StageLockError("Phase A selected no eligible configuration: Phase B is impossible")
    return derived


def _decimalized(table: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {}
    for config_id, row in table.items():
        rows[config_id] = {
            "eligibility": row["eligibility"],
            "equity_return": {k: Decimal(v) for k, v in row["equity_return"].items()},
        }
    return rows


def run_phase_b(
    source: Any,
    out_dir: Path,
    root: Path = ROOT,
    violations: Callable[[DevelopmentEngine], bool] = lambda engine: False,
) -> dict[str, Any]:
    _require_phase(source, "B")
    out_dir = _output_dir(source, out_dir, root)
    if (out_dir / EVALUATION_FILE).exists():
        raise StageLockError("Phase B has already been executed")
    selected = load_selection(out_dir, source, root)
    windows = _windows(source)
    start, end = windows.evaluation_start, windows.evaluation_end
    primary = primary_book(selected, start, end)
    cost, delay = stress_books(selected, start, end)
    engine = _run(source, (primary, cost, delay), end, windows)
    years = windows.evaluation_years
    metrics = {
        book.book_id: scoring.trade_metrics(_result(engine, book.book_id), years)
        for book in (primary, cost, delay)
    }
    forecasts = scoring.forecast_metrics(engine.forecasts, years)
    gates = scoring.evaluation_gates(
        metrics[primary.book_id],
        metrics[cost.book_id],
        metrics[delay.book_id],
        forecasts,
        identities_pass=True,
        violations=violations(engine),
        years=years,
    )
    return _write_once(
        out_dir / EVALUATION_FILE,
        {
            "phase": "B_EVALUATION",
            "evidence_class": _evidence(source),
            "selected_configuration": selected,
            "identities": _identities(source, root),
            "metrics": metrics,
            "forecasts": forecasts,
            "gates": gates,
            "disposition": scoring.disposition(False, selected, gates),
        },
    )
