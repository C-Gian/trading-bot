"""G2-02 batch execution: phase-bounded sources, run manifests, simulation and extraction.

Each variant is simulated by one `DevelopmentCore` over 2020-01-01..2025-01-01 (exclusive) through
the phase-bounded loader (2025+ is refused before any object is opened). 2020 initializes models
and residual archives; no economic position can be opened before 2021-01-01 00:00 UTC.

After the run, the immutable record store is reduced to compact per-decision arrays plus the
trade/fill/funding/fit/risk records the scorer needs, written as runtime cache under the
git-ignored `data/research_runs/`. The cache is an intermediate, not an artifact: the committed
artifacts are rebuilt from it deterministically and bound to its content hash.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from app.g1.canonical import content_id, digest

from ..bars import Minute
from ..contract import BASE_FRICTION_SCENARIO, FRICTION_SCENARIOS, MINUTE, frozen_identity
from ..execution import FundingBook
from ..records import (
    ClosedTrade,
    Decision,
    FitManifest,
    FundingEvent,
    Prediction,
    PredictionOutcome,
    RiskStateEvent,
    RunManifest,
    ShadowLabel,
    SimulatedFill,
    SourceAuditEvent,
    StopExpiryEvent,
    record_key,
)
from ..runs import minutes_sha256
from ..sources import (
    ROOT,
    Authorization,
    PhaseBoundedLoader,
    pinned_market_filters,
)
from ..store import plain
from .core import DevelopmentCore
from .variants import ECONOMIC_START, INITIALIZATION_START, OBSERVATION_END, VARIANTS, Variant

PACKAGE = "G2-02-BASELINE-AND-DIAGNOSTICS-V1"
IMPLEMENTATION = "G2-02-DEVELOPMENT-RUNNER-V1"
EVIDENCE_CLASS = "EXPOSED_DEVELOPMENT_EVIDENCE_NOT_VALIDATION"
AUTHORIZATION_RECORD = "G2-02-DEV-RUN-AUTHORIZATION-001"
CACHE_DIR = Path("data/research_runs/g2-02-development-cycle-1-v1")
CACHE_SCHEMA = "G2-02-RUN-CACHE-V1"
PROGRESS_EVERY_MINUTES = 1440


def authorization() -> Authorization:
    return Authorization(
        INITIALIZATION_START,
        OBSERVATION_END,
        "G2-02 exposed development batch (2020 initialization, 2021-2024 scored)",
        AUTHORIZATION_RECORD,
    )


@dataclass
class Sources:
    identity: dict[str, Any]
    minutes: list[Minute]
    funding: list[tuple[datetime, float]]
    filters: Any
    audit_log: list[dict[str, Any]]
    minutes_sha256: str
    funding_sha256: str

    @property
    def zero_volume_minutes(self) -> int:
        return sum(1 for m in self.minutes if m.volume <= 0)


def load_sources(root: Path = ROOT) -> Sources:
    loader = PhaseBoundedLoader(authorization(), root)
    identity = loader.manifest_identity()
    minutes = loader.minutes()
    funding = loader.funding()
    filters = pinned_market_filters(root)
    return Sources(
        identity,
        minutes,
        funding,
        filters,
        loader.log,
        minutes_sha256(minutes),
        digest([(m, r) for m, r in funding]),
    )


def run_manifest(variant: Variant, sources: Sources) -> RunManifest:
    friction = FRICTION_SCENARIOS[BASE_FRICTION_SCENARIO]
    hashes = (
        ("fixture_or_window", "G2-02-EXPOSED-2020-2024"),
        ("kline_object_index_sha256", str(sources.identity["kline_object_index_sha256"])),
        ("funding_file_sha256", str(sources.identity["funding_file_sha256"])),
        ("minutes_sha256", sources.minutes_sha256),
        ("funding_sha256", sources.funding_sha256),
    )
    frozen = tuple((k, digest(v)) for k, v in sorted(frozen_identity().items())) + (
        ("variant", digest(variant.identity())),
        ("economic_start", ECONOMIC_START.isoformat()),
    )
    payload = (
        variant.run_key,
        INITIALIZATION_START,
        OBSERVATION_END,
        hashes,
        sources.filters.sha256(),
        friction,
        frozen,
        variant.system_version,
        IMPLEMENTATION,
    )
    return RunManifest(
        content_id("G2DEV", payload),
        INITIALIZATION_START,
        variant.system_version,
        IMPLEMENTATION,
        EVIDENCE_CLASS,
        f"G2-02 {variant.run_key} — EXPOSED DEVELOPMENT, NOT VALIDATION",
        INITIALIZATION_START,
        OBSERVATION_END,
        hashes,
        sources.filters.as_pairs(),
        sources.filters.sha256(),
        BASE_FRICTION_SCENARIO,
        friction,
        frozen,
    )


def audit_events(run_id: str, sources: Sources) -> tuple[SourceAuditEvent, ...]:
    events = []
    for index, entry in enumerate(sources.audit_log):
        returned = entry.get("returned") or [None, None]
        events.append(
            SourceAuditEvent(
                record_key("G2A", run_id, index),
                run_id,
                INITIALIZATION_START,
                entry["kind"],
                str(entry.get("source", ",".join(entry.get("objects", [])))),
                INITIALIZATION_START,
                OBSERVATION_END,
                tuple(entry.get("opened_objects", ())),
                returned[0],
                returned[1],
                int(entry.get("rows", 0)),
                EVIDENCE_CLASS,
                f"ledger={AUTHORIZATION_RECORD}; package={PACKAGE}",
            )
        )
    return tuple(events)


def new_core(variant: Variant, sources: Sources) -> DevelopmentCore:
    manifest = run_manifest(variant, sources)
    return DevelopmentCore(
        manifest,
        FundingBook(sources.funding),
        sources.filters,
        manifest.friction,
        audit_events(manifest.run_id, sources),
        variant,
        ECONOMIC_START,
    )


def simulate(
    core: DevelopmentCore,
    minutes: list[Minute],
    progress: Callable[[int, int, datetime], None] | None = None,
) -> DevelopmentCore:
    """Drive the core minute by minute (identical to `runs.run_batch`) with progress callbacks."""
    total = int((core.end - core.start) // MINUTE)
    next_report = 0
    for minute in minutes:
        core.advance_to(minute.open_time)
        core.ingest(minute)
        done = int((core.cursor - core.start) // MINUTE)
        if progress is not None and done >= next_report:
            progress(done, total, core.cursor)
            next_report = done + PROGRESS_EVERY_MINUTES
    core.advance_to(core.end)
    if progress is not None:
        progress(total, total, core.cursor)
    return core


# ---------------------------------------------------------------------- extraction
def _minutes(moment: datetime | None) -> int:
    if moment is None:
        return -1
    return int((moment - INITIALIZATION_START) // MINUTE)


def _f(value: float | None) -> float:
    return np.nan if value is None else float(value)


def extract(core: DevelopmentCore) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Compact per-decision arrays + event records (plain JSON) from the immutable store."""
    store = core.store
    predictions: list[Prediction] = store.of_type(Prediction)
    decisions: list[Decision] = store.of_type(Decision)
    outcomes = {o.decision_time: o for o in store.of_type(PredictionOutcome)}
    labels: dict[tuple[datetime, str], ShadowLabel] = {
        (label.decision_time, label.side): label for label in store.of_type(ShadowLabel)
    }
    n = len(decisions)
    assert n == len(predictions)
    fit_ids = sorted({p.fit_id for p in predictions if p.fit_id is not None})
    fit_index = {fit_id: i for i, fit_id in enumerate(fit_ids)}
    reason_table: dict[str, int] = {}
    reason_sets: list[str] = []
    reason_set_index: dict[str, int] = {}

    def reason_id(codes: tuple[str, ...]) -> int:
        key = "|".join(codes)
        if key not in reason_set_index:
            reason_set_index[key] = len(reason_sets)
            reason_sets.append(key)
            for code in codes:
                reason_table.setdefault(code, len(reason_table))
        return reason_set_index[key]

    source_code = {"NONE": 0, "TRAINING_TARGET_BASELINE_UNVALIDATED": 1}
    source_code["PREQUENTIAL_CDF_UNCALIBRATED"] = 2
    action_code = {"NO_TRADE": 0, "LONG": 1, "SHORT": -1}
    position_code = {"FLAT": 0, "ENTRY_PENDING": 1, "OPEN": 2}
    status_code = {"MATURED": 1, "TARGET_UNAVAILABLE": 0}
    label_status = {"AVAILABLE": 1, "UNAVAILABLE": 0}
    exit_code = {None: 0, "STOP": 1, "STOP_GAP": 2, "EXPIRY": 3}
    a: dict[str, list[Any]] = {
        key: []
        for key in (
            "t",
            "forecast_available",
            "mu_z",
            "sigma",
            "mean",
            "median",
            "q10",
            "q50",
            "q90",
            "p_positive",
            "residual_source",
            "residual_count",
            "fit",
            "view",
            "price",
            "outcome_status",
            "realized",
            "realized_z",
            "action",
            "selection",
            "reasons",
            "position",
            "equity",
            "marked",
            "drawdown",
            "locked",
            "long_pred",
            "long_margin",
            "short_pred",
            "short_margin",
            "stop_distance",
        )
    }
    for side in ("long", "short"):
        for key in ("status", "net_r", "exit", "gross", "friction", "funding", "reasons"):
            a[f"shadow_{side}_{key}"] = []
    raw = np.full((n, 8), np.nan)
    scaled = np.full((n, 8), np.nan)
    for i, (p, d) in enumerate(zip(predictions, decisions, strict=True)):
        assert p.decision_time == d.decision_time and p.decision_id == d.decision_id
        t = p.decision_time
        a["t"].append(_minutes(t))
        available = p.median_return is not None
        a["forecast_available"].append(available)
        for key, value in (
            ("mu_z", p.mu_z),
            ("sigma", p.sigma_4h),
            ("mean", p.mean_return),
            ("median", p.median_return),
            ("q10", p.q10),
            ("q50", p.q50),
            ("q90", p.q90),
            ("p_positive", p.p_positive),
            ("view", p.view_strength_z),
            ("price", d.reference_price),
            ("stop_distance", d.stop_distance),
        ):
            a[key].append(_f(value))
        a["residual_source"].append(source_code[p.residual_source])
        a["residual_count"].append(p.residual_count)
        a["fit"].append(-1 if p.fit_id is None else fit_index[p.fit_id])
        raw[i] = [_f(v) for v in p.raw_terms]
        scaled[i] = [_f(v) for v in p.scaled_terms]
        outcome: PredictionOutcome | None = outcomes.get(t)
        a["outcome_status"].append(-1 if outcome is None else status_code[outcome.status])
        a["realized"].append(_f(None if outcome is None else outcome.realized_return))
        a["realized_z"].append(_f(None if outcome is None else outcome.realized_z))
        a["action"].append(action_code[str(d.action)])
        a["selection"].append(
            {"NONE": 0, "LONG_SELECTED": 1, "SHORT_SELECTED": -1}[d.policy_selection]
        )
        a["reasons"].append(reason_id(d.reason_codes))
        a["position"].append(position_code[d.position_state])
        a["equity"].append(d.risk.equity)
        a["marked"].append(d.risk.marked_equity)
        a["drawdown"].append(d.risk.drawdown)
        a["locked"].append(d.risk.drawdown_stop_active)
        a["long_pred"].append(_f(d.long_utility.predicted_utility))
        a["long_margin"].append(_f(d.long_utility.prudential_margin))
        a["short_pred"].append(_f(d.short_utility.predicted_utility))
        a["short_margin"].append(_f(d.short_utility.prudential_margin))
        for side, name in (("LONG", "long"), ("SHORT", "short")):
            label = labels.get((t, side))
            a[f"shadow_{name}_status"].append(-1 if label is None else label_status[label.status])
            a[f"shadow_{name}_net_r"].append(_f(None if label is None else label.net_r))
            a[f"shadow_{name}_exit"].append(0 if label is None else exit_code[label.exit_kind])
            a[f"shadow_{name}_gross"].append(
                _f(None if label is None else label.gross_pnl_per_unit)
            )
            a[f"shadow_{name}_friction"].append(
                _f(None if label is None else label.friction_per_unit)
            )
            a[f"shadow_{name}_funding"].append(
                _f(None if label is None else label.funding_per_unit)
            )
            a[f"shadow_{name}_reasons"].append(
                reason_id(() if label is None else label.reason_codes)
            )
    arrays: dict[str, np.ndarray] = {}
    for key, values in a.items():
        if key in ("forecast_available", "locked"):
            arrays[key] = np.asarray(values, dtype=bool)
        elif (
            key in ("mu_z", "sigma", "mean", "median", "q10", "q50", "q90", "p_positive")
            or key.endswith(("net_r", "gross", "friction", "funding"))
            or key
            in (
                "view",
                "price",
                "realized",
                "realized_z",
                "equity",
                "marked",
                "drawdown",
                "long_pred",
                "long_margin",
                "short_pred",
                "short_margin",
                "stop_distance",
            )
        ):
            arrays[key] = np.asarray(values, dtype=float)
        else:
            arrays[key] = np.asarray(values, dtype=np.int64)
    arrays["raw_terms"] = raw
    arrays["scaled_terms"] = scaled
    archive = core.archives["FORECAST"]
    count = len(archive)
    arrays["archive_times"] = _as_minutes(archive._times[:count])
    arrays["archive_matured"] = _as_minutes(archive._matured[:count])
    arrays["archive_values"] = archive._values[:count].copy()
    for j, fit_id in enumerate(fit_ids):
        atoms = core.forecast_atoms.get(fit_id)
        if atoms is not None:
            arrays[f"atoms_{j}"] = np.asarray(atoms, dtype=float)
    events = {
        "run_manifest": plain(core.manifest),
        "fit_ids": fit_ids,
        "reason_sets": reason_sets,
        "fits": [_fit_summary(f) for f in store.of_type(FitManifest)],
        "trades": [plain(t) for t in store.of_type(ClosedTrade)],
        "fills": [plain(f) for f in store.of_type(SimulatedFill)],
        "funding": [plain(f) for f in store.of_type(FundingEvent)],
        "stop_expiry": [plain(e) for e in store.of_type(StopExpiryEvent)],
        "risk_events": [plain(e) for e in store.of_type(RiskStateEvent)],
        "open_trade_at_end": None if core.trade is None else plain(_open_trade(core)),
        "pending_intent_at_end": None if core.intent is None else plain(core.intent),
        "record_counts": store.counts(),
        "invalid_minutes": core.invalid_minutes,
        "final_governor": {
            "equity": core.governor.equity,
            "marked_equity": core.governor.mark,
            "peak_equity": core.governor.peak,
            "locked": core.governor.locked,
        },
    }
    return arrays, events


def _as_minutes(values: np.ndarray) -> np.ndarray:
    origin = np.datetime64(INITIALIZATION_START.replace(tzinfo=None), "m")
    return (values - origin).astype("timedelta64[m]").astype(np.int64)


def _fit_summary(fit: FitManifest) -> dict[str, Any]:
    return {
        "fit_id": fit.fit_id,
        "head": fit.head,
        "fit_boundary": plain(fit.fit_boundary),
        "status": fit.status,
        "detail": fit.support_detail,
        "rows": fit.rows,
        "training_start": plain(fit.training_start),
        "training_end": plain(fit.training_end),
        "latest_label_time": plain(fit.latest_label_time),
        "intercept": plain(fit.intercept),
        "coefficients": plain(fit.coefficients),
        "constant_columns": list(fit.constant_columns),
        "fallback_atoms": fit.fallback_atoms,
        "fallback_atoms_sha256": fit.fallback_atoms_sha256,
    }


def _open_trade(core: DevelopmentCore) -> dict[str, Any]:
    trade = core.trade
    assert trade is not None
    return {
        "trade_id": trade.trade_id,
        "side": trade.side,
        "entry_time": plain(trade.entry_time),
        "raw_entry": trade.raw_entry,
        "quantity": trade.quantity,
        "stop_price": trade.stop_price,
        "intended_expiry_time": plain(trade.intended_expiry_time),
        "funding_pnl": trade.funding_pnl,
        "status": "OPEN_AT_OBSERVATION_CEILING_MARKED_NOT_CLOSED",
    }


# ---------------------------------------------------------------------- cache
def cache_dir(root: Path, run_key: str) -> Path:
    return root / CACHE_DIR / run_key


def write_cache(
    root: Path, variant: Variant, arrays: dict[str, np.ndarray], events: dict[str, Any]
) -> dict[str, Any]:
    directory = cache_dir(root, variant.run_key)
    directory.mkdir(parents=True, exist_ok=True)
    np.savez(directory / "arrays.npz", **arrays)  # type: ignore[arg-type]  # uncompressed
    (directory / "events.json").write_text(
        json.dumps(events, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    return cache_identity(root, variant.run_key)


def cache_identity(root: Path, run_key: str) -> dict[str, Any]:
    directory = cache_dir(root, run_key)
    arrays = np.load(directory / "arrays.npz")
    array_hash = hashlib.sha256()
    for key in sorted(arrays.files):
        value = arrays[key]
        array_hash.update(key.encode("ascii"))
        array_hash.update(str(value.dtype).encode("ascii"))
        array_hash.update(repr(value.shape).encode("ascii"))
        array_hash.update(np.ascontiguousarray(value).tobytes())
    events = (directory / "events.json").read_bytes()
    return {
        "arrays_sha256": array_hash.hexdigest(),
        "events_sha256": hashlib.sha256(events).hexdigest(),
    }


def read_cache(root: Path, run_key: str) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    directory = cache_dir(root, run_key)
    with np.load(directory / "arrays.npz") as data:
        arrays = {key: data[key] for key in data.files}
    events = json.loads((directory / "events.json").read_text(encoding="utf-8"))
    return arrays, events


# ---------------------------------------------------------------------- worker
def run_variant(
    run_key: str,
    root: Path = ROOT,
    progress: Callable[[str, int | None, int | None, str], None] | None = None,
) -> dict[str, Any]:
    """Load sources, simulate one variant, extract, fingerprint and cache. Returns identities."""
    variant = VARIANTS[run_key]
    started = time.monotonic()

    def say(phase: str, done: int | None = None, total: int | None = None, text: str = "") -> None:
        if progress is not None:
            progress(phase, done, total, text)

    say("load sources", text="phase-bounded loader: 2020-01-01..2025-01-01 (exclusive)")
    sources = load_sources(root)
    core = new_core(variant, sources)
    total = int((core.end - core.start) // MINUTE)
    say("simulate", 0, total, "simulating")

    def tick(done: int, total_minutes: int, cursor: datetime) -> None:
        say("simulate", done, total_minutes, f"simulated through {cursor:%Y-%m-%d %H:%M} UTC")

    simulate(core, sources.minutes, tick)
    say("fingerprint", text="canonical record-stream fingerprint")
    fingerprint = core.store.fingerprint()
    say("extract", text="reducing records to scorer arrays")
    arrays, events = extract(core)
    events["fingerprint"] = fingerprint
    events["zero_volume_minutes"] = sources.zero_volume_minutes
    events["source_minutes"] = len(sources.minutes)
    events["funding_records"] = len(sources.funding)
    events["source_identity"] = sources.identity
    events["exchange_filters"] = {
        "source": sources.filters.source,
        "sha256": sources.filters.sha256(),
        "values": dict(sources.filters.as_pairs()),
    }
    events["loader_log"] = json.loads(json.dumps(sources.audit_log, default=str))
    identity = write_cache(root, variant, arrays, events)
    return {
        "run_key": run_key,
        "run_id": core.run_id,
        "fingerprint": fingerprint,
        "record_counts": events["record_counts"],
        "cache": identity,
        "elapsed_seconds": round(time.monotonic() - started, 1),
    }


def scored_mask(t_minutes: np.ndarray) -> np.ndarray:
    """Decisions T with 2021-01-01 00:00 <= T < 2025-01-01 00:00 (scored exposed development)."""
    lo = int((ECONOMIC_START - INITIALIZATION_START) // MINUTE)
    hi = int((OBSERVATION_END - INITIALIZATION_START) // MINUTE)
    return (t_minutes >= lo) & (t_minutes < hi)


def as_datetime(minutes: int) -> datetime:
    return INITIALIZATION_START + timedelta(minutes=int(minutes))


def utc_iso(minutes: int) -> str:
    return as_datetime(minutes).astimezone(UTC).isoformat().replace("+00:00", "Z")
