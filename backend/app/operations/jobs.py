"""Long-running job progress telemetry (docs/operations/LONG_RUNNING_JOB_PROGRESS_V1.md).

A job writes an atomically replaced JSON state file plus an append-only operational log under the
git-ignored runtime directory `.runtime/jobs/`. A daemon heartbeat thread keeps refreshing the state
even while a child command emits nothing, so a quiet job never looks hung.

This is operational telemetry only. It is never scientific evidence, never committed and never read
by a scientific artifact. Percent is reported only when a measured denominator of work units
exists; ETA only when the current phase's measured rate or a recorded historical phase duration
supports it. Otherwise both are None ("unknown"). Nothing is fabricated.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self, TextIO

ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DIR = Path(".runtime/jobs")
HISTORY_FILE = "history.json"
STATUSES = ("QUEUED", "RUNNING", "PASS", "FAIL", "CANCELLED")
TERMINAL = ("PASS", "FAIL", "CANCELLED")
HEARTBEAT_SECONDS = 2.0
LOG_TAIL = 40
# A RUNNING job whose heartbeat is older than this is reported as STALE (its process died).
STALE_SECONDS = 60.0


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.isoformat().replace("+00:00", "Z")


def parse(text: str | None) -> datetime | None:
    return None if text is None else datetime.fromisoformat(text)


def jobs_dir(root: Path = ROOT) -> Path:
    return root / RUNTIME_DIR


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    temporary.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    for attempt in range(20):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:  # Windows: a reader holds the file open for an instant
            time.sleep(0.05 * (attempt + 1))
    os.replace(temporary, path)


def format_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    safe = max(0, int(seconds))
    hours, rest = divmod(safe, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:d}:{secs:02d}"


class Job:
    """One job's runtime state. Thread-safe; every mutation rewrites the state file atomically."""

    def __init__(
        self,
        job_type: str,
        phases: list[str],
        root: Path = ROOT,
        job_id: str | None = None,
        echo: TextIO | None = None,
        heartbeat_seconds: float = HEARTBEAT_SECONDS,
    ) -> None:
        self.root = root
        self.job_type = job_type
        self.phases = list(phases)
        started = utc_now()
        self.job_id = job_id or f"{job_type}-{started:%Y%m%dT%H%M%S}-{os.getpid()}"
        self.directory = jobs_dir(root)
        self.state_path = self.directory / f"{self.job_id}.json"
        self.log_path = self.directory / f"{self.job_id}.log"
        self.echo = echo
        self.heartbeat_seconds = heartbeat_seconds
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._phase_started: float | None = None
        self._phase_durations: dict[str, float] = {}
        self._history = _read_history(root).get(job_type, {})
        self._last_echo = 0.0
        self._aggregate: Callable[[], dict[str, Any]] | None = None
        self.state: dict[str, Any] = {
            "job_id": self.job_id,
            "job_type": job_type,
            "status": "QUEUED",
            "pid": os.getpid(),
            "phases": self.phases,
            "phase_count": len(self.phases),
            "phase_index": 0,
            "phase": None,
            "last_completed_phase": None,
            "completed_units": None,
            "total_units": None,
            "unit_label": None,
            "percent": None,
            "phase_percent": None,
            "started_at": iso(started),
            "updated_at": iso(started),
            "heartbeat_at": iso(started),
            "elapsed_seconds": 0.0,
            "phase_eta_seconds": None,
            "eta_seconds": None,
            "eta_basis": "UNKNOWN",
            "message": "queued",
            "exit_code": None,
            "error": None,
            "children": [],
            "evidence": "OPERATIONAL_TELEMETRY_NOT_SCIENTIFIC_EVIDENCE",
        }
        self._write()

    # ------------------------------------------------------------------ lifecycle
    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, kind: object, error: BaseException | None, _tb: object) -> None:
        if self.state["status"] in TERMINAL:
            self._halt()
            return
        if error is None:
            self.finish("PASS", 0)
        elif isinstance(error, KeyboardInterrupt):
            self.finish("CANCELLED", 130, "interrupted")
        else:
            code = (
                error.code if isinstance(error, SystemExit) and isinstance(error.code, int) else 1
            )
            self.finish("FAIL", code, f"{type(error).__name__}: {error}"[:2000])

    def start(self) -> None:
        with self._lock:
            self.state["status"] = "RUNNING"
            self.state["message"] = "started"
            self._write()
        self.log(f"job {self.job_id} started ({len(self.phases)} phases)")
        self._thread = threading.Thread(target=self._beat, name=f"heartbeat-{self.job_id}")
        self._thread.daemon = True
        self._thread.start()

    def phase(
        self,
        name: str,
        total_units: int | None = None,
        unit_label: str | None = None,
        message: str | None = None,
    ) -> None:
        with self._lock:
            self._close_phase()
            index = self.phases.index(name) + 1 if name in self.phases else None
            if index is None:
                self.phases.append(name)
                self.state["phases"] = self.phases
                self.state["phase_count"] = len(self.phases)
                index = len(self.phases)
            self.state.update(
                phase=name,
                phase_index=index,
                completed_units=0 if total_units else None,
                total_units=total_units or None,
                unit_label=unit_label,
                message=message or name,
            )
            self._phase_started = time.monotonic()
            self._refresh()
            self._write()
        self.log(f"phase {index}/{len(self.phases)}: {name}")

    def advance(self, completed_units: int, message: str | None = None) -> None:
        with self._lock:
            self.state["completed_units"] = completed_units
            if message is not None:
                self.state["message"] = message
            self._refresh()
            self._write()

    def note(self, message: str) -> None:
        with self._lock:
            self.state["message"] = message
            self._refresh()
            self._write()
        self.log(message)

    def set_aggregate(self, reader: Callable[[], dict[str, Any]] | None) -> None:
        """A callable polled on every heartbeat returning {completed_units, children, message}."""
        self._aggregate = reader

    def log(self, message: str) -> None:
        line = f"{iso(utc_now())} {message}"
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        if self.echo is not None:
            print(f"[{self.job_type}] {message}", file=self.echo, flush=True)

    def finish(self, status: str, exit_code: int, error: str | None = None) -> None:
        if status not in TERMINAL:
            raise ValueError(f"terminal status must be one of {TERMINAL}")
        with self._lock:
            self._close_phase()
            if status == "PASS" and self.state["total_units"]:
                self.state["completed_units"] = self.state["total_units"]
            self.state.update(status=status, exit_code=exit_code, error=error)
            self.state["message"] = "finished" if status == "PASS" else (error or status)
            self._refresh()
            self.state["eta_seconds"] = self.state["phase_eta_seconds"] = None
            self._write()
        self._halt()
        self.log(f"job {status} exit_code={exit_code}" + (f" error={error}" if error else ""))
        if status == "PASS":
            _record_history(self.root, self.job_type, self._phase_durations)

    # ------------------------------------------------------------------ internals
    def _halt(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=5)

    def _close_phase(self) -> None:
        name = self.state["phase"]
        if name is not None and self._phase_started is not None:
            self._phase_durations[name] = time.monotonic() - self._phase_started
            self.state["last_completed_phase"] = name

    def _refresh(self) -> None:
        now = utc_now()
        started = parse(self.state["started_at"])
        assert started is not None
        self.state["updated_at"] = self.state["heartbeat_at"] = iso(now)
        self.state["elapsed_seconds"] = round((now - started).total_seconds(), 1)
        done, total = self.state["completed_units"], self.state["total_units"]
        phase_elapsed = (
            None if self._phase_started is None else time.monotonic() - self._phase_started
        )
        phase_eta: float | None = None
        percent: float | None = None
        if total and done is not None:
            percent = round(100.0 * min(done, total) / total, 2)
            if done > 0 and phase_elapsed is not None and phase_elapsed > 5:
                phase_eta = phase_elapsed * (total - done) / done
        self.state["phase_percent"] = percent
        # Whole-job percent only when every phase is unit-measured is not generally known: the
        # job-level percent is the current phase percent only for single-phase jobs.
        self.state["percent"] = percent if len(self.phases) == 1 else None
        self.state["phase_eta_seconds"] = None if phase_eta is None else round(phase_eta, 1)
        eta, basis = self._eta(phase_eta, phase_elapsed)
        self.state["eta_seconds"] = None if eta is None else round(eta, 1)
        self.state["eta_basis"] = basis

    def _eta(
        self, phase_eta: float | None, phase_elapsed: float | None
    ) -> tuple[float | None, str]:
        """Remaining time: current-phase measured rate plus historical durations of later phases."""
        index = self.state["phase_index"]
        later = self.phases[index:] if index else self.phases
        history = self._history
        if any(name not in history for name in later):
            if len(self.phases) == 1 or index == len(self.phases):
                return phase_eta, "CURRENT_PHASE_RATE" if phase_eta is not None else "UNKNOWN"
            return None, "UNKNOWN"
        remaining_later = sum(float(history[name]) for name in later)
        current = self.state["phase"]
        if phase_eta is not None:
            current_left = phase_eta
            basis = "CURRENT_PHASE_RATE_PLUS_HISTORY"
        elif current in history and phase_elapsed is not None:
            current_left = max(0.0, float(history[current]) - phase_elapsed)
            basis = "HISTORICAL_PHASE_DURATIONS"
        else:
            return None, "UNKNOWN"
        return current_left + remaining_later, basis

    def _write(self) -> None:
        _atomic_write(self.state_path, self.state)

    def _beat(self) -> None:
        while not self._stop.wait(self.heartbeat_seconds):
            aggregate = self._aggregate
            with self._lock:
                if aggregate is not None:
                    try:
                        update = aggregate()
                    except Exception as error:  # telemetry must never kill the job
                        update = {"message": f"progress aggregation unavailable: {error}"}
                    for key in ("completed_units", "children", "message"):
                        if key in update:
                            self.state[key] = update[key]
                self._refresh()
                self._write()
                snapshot = dict(self.state)
            if self.echo is not None and time.monotonic() - self._last_echo >= 10:
                self._last_echo = time.monotonic()
                print(status_line(snapshot), file=self.echo, flush=True)


def status_line(state: dict[str, Any]) -> str:
    parts = [
        f"[{state['job_type']}] {state['status']}",
        f"phase {state['phase_index']}/{state['phase_count']} {state['phase'] or '-'}",
        f"elapsed {format_seconds(state['elapsed_seconds'])}",
    ]
    if state.get("phase_percent") is not None:
        parts.append(
            f"{state['phase_percent']:.1f}% ({state['completed_units']:,}/{state['total_units']:,}"
            f" {state.get('unit_label') or 'units'})"
        )
    parts.append(f"ETA {format_seconds(state.get('eta_seconds'))}")
    parts.append("heartbeat ok")
    if state.get("message"):
        parts.append(str(state["message"])[:120])
    return " | ".join(parts)


# ---------------------------------------------------------------------- history (ETA only)
def _read_history(root: Path) -> dict[str, dict[str, float]]:
    path = jobs_dir(root) / HISTORY_FILE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _record_history(root: Path, job_type: str, durations: dict[str, float]) -> None:
    history = _read_history(root)
    history[job_type] = {name: round(seconds, 1) for name, seconds in durations.items()}
    _atomic_write(jobs_dir(root) / HISTORY_FILE, history)


# ---------------------------------------------------------------------- read-only views
def _public(state: dict[str, Any], now: datetime) -> dict[str, Any]:
    heartbeat = parse(state.get("heartbeat_at"))
    age = None if heartbeat is None else max(0.0, (now - heartbeat).total_seconds())
    view = dict(state)
    view["heartbeat_age_seconds"] = None if age is None else round(age, 1)
    view["stale"] = bool(
        state.get("status") == "RUNNING" and age is not None and age > STALE_SECONDS
    )
    return view


def list_jobs(root: Path = ROOT, limit: int = 20) -> list[dict[str, Any]]:
    directory = jobs_dir(root)
    if not directory.is_dir():
        return []
    now = utc_now()
    states = []
    for path in directory.glob("*.json"):
        if path.name == HISTORY_FILE:
            continue
        try:
            states.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    states.sort(key=lambda s: str(s.get("updated_at")), reverse=True)
    active = [s for s in states if s.get("status") in ("QUEUED", "RUNNING")]
    rest = [s for s in states if s.get("status") not in ("QUEUED", "RUNNING")]
    return [_public(s, now) for s in (active + rest)[:limit]]


def read_job(job_id: str, root: Path = ROOT, tail: int = LOG_TAIL) -> dict[str, Any] | None:
    if not job_id or any(c in job_id for c in "/\\") or job_id.startswith("."):
        return None
    directory = jobs_dir(root)
    path = directory / f"{job_id}.json"
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    view = _public(state, utc_now())
    view["log_tail"] = log_tail(directory / f"{job_id}.log", tail)
    return view


def log_tail(path: Path, lines: int = LOG_TAIL) -> list[str]:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 64 * 1024))
            text = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    return text.splitlines()[-lines:]


def stderr_echo(enabled: bool) -> TextIO | None:
    return sys.stderr if enabled else None
