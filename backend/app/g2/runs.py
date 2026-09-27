"""Registered G2 engineering runs: manifests, deterministic construction and batch execution.

A registered run binds its source (synthetic fixture or a declared <=2024 exposed engineering
window), pinned filters and friction scenario into a content-derived run identity. The batch
driver and the incremental replay adapter feed the same `G2Core`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.g1.canonical import content_id, digest

from . import fixtures
from .bars import Minute
from .contract import (
    BASE_FRICTION_SCENARIO,
    FRICTION_SCENARIOS,
    IMPLEMENTATION_VERSION,
    SYSTEM_VERSION,
    frozen_identity,
)
from .core import G2Core
from .execution import FundingBook
from .records import RunManifest, SourceAuditEvent, record_key
from .risk import ExchangeFilters

SYNTHETIC = "SYNTHETIC_FIXTURE_NOT_MARKET_EVIDENCE"
EXPOSED_WINDOW = "EXPOSED_ENGINEERING_WINDOW_NOT_PERFORMANCE_EVIDENCE"
NOT_PERFORMANCE_EVIDENCE = "NOT PERFORMANCE EVIDENCE"


def minutes_sha256(minutes: Sequence[Minute]) -> str:
    h = hashlib.sha256()
    for m in minutes:
        h.update(
            repr(
                (
                    m.open_time.isoformat(),
                    m.open,
                    m.high,
                    m.low,
                    m.close,
                    m.volume,
                    m.quote_volume,
                    m.taker_buy_base_volume,
                )
            ).encode("ascii")
        )
    return h.hexdigest()


@dataclass(frozen=True)
class RunSpec:
    key: str
    label: str
    evidence_class: str
    start: datetime
    end: datetime
    minutes: Callable[[], list[Minute]]
    funding: Callable[[], list[tuple[datetime, float]]]
    filters: ExchangeFilters
    audit: Callable[[str], tuple[SourceAuditEvent, ...]]
    description: str


def build_manifest(
    spec: RunSpec, minutes: Sequence[Minute], funding: Sequence[tuple[datetime, float]]
) -> RunManifest:
    friction = FRICTION_SCENARIOS[BASE_FRICTION_SCENARIO]
    sources = (
        ("fixture_or_window", spec.key),
        ("minutes_sha256", minutes_sha256(minutes)),
        ("funding_sha256", digest([(m, r) for m, r in funding])),
    )
    frozen = tuple((k, digest(v)) for k, v in sorted(frozen_identity().items()))
    payload = (
        spec.key,
        spec.start,
        spec.end,
        sources,
        spec.filters.sha256(),
        friction,
        frozen,
        SYSTEM_VERSION,
        IMPLEMENTATION_VERSION,
    )
    return RunManifest(
        content_id("G2RUN", payload),
        spec.start,
        SYSTEM_VERSION,
        IMPLEMENTATION_VERSION,
        spec.evidence_class,
        spec.label,
        spec.start,
        spec.end,
        sources,
        spec.filters.as_pairs(),
        spec.filters.sha256(),
        BASE_FRICTION_SCENARIO,
        friction,
        frozen,
    )


def synthetic_audit(
    run_id: str, start: datetime, end: datetime, rows: int
) -> tuple[SourceAuditEvent, ...]:
    return (
        SourceAuditEvent(
            record_key("G2A", run_id, "SYNTHETIC"),
            run_id,
            start,
            "SYNTHETIC_SOURCE",
            fixtures.FIXTURE_ID,
            start,
            end,
            (),
            start,
            end,
            rows,
            SYNTHETIC,
            f"seeded synthetic generator seed={fixtures.SEED}; no market observation opened",
        ),
    )


def synthetic_spec() -> RunSpec:
    return RunSpec(
        "G2-SYN-V0-ENGINEERING",
        "Synthetic engineering path — NOT PERFORMANCE EVIDENCE",
        SYNTHETIC,
        fixtures.START,
        fixtures.END,
        fixtures.synthetic_minutes,
        fixtures.synthetic_funding,
        fixtures.SYNTHETIC_FILTERS,
        lambda run_id: (),
        "Seeded synthetic 1m path exercising every G2-V0 contract path with frozen constants.",
    )


ENGINEERING_WINDOW_LEDGER = "G2-01-ENG-WINDOW-001"
ENGINEERING_WINDOW = (
    datetime(2024, 6, 3, tzinfo=UTC),
    datetime(2024, 6, 10, tzinfo=UTC),
)
ENGINEERING_FILTERS = ExchangeFilters(
    source="ENGINEERING_PLACEHOLDER_NOT_PINNED_EXCHANGEINFO_NO_ECONOMIC_USE",
    tick_size="0.1",
    step_size="0.001",
    min_qty="0.001",
    max_qty="1000",
    min_notional="100",
)


def engineering_window_spec(root: Path | None = None) -> RunSpec:
    """The declared <=2024 exposed engineering window (ledger G2-01-ENG-WINDOW-001).

    Seven days cannot satisfy the 180-day training minimum, so no model fits and no economic
    action can occur; the run exercises parser/aggregation/causality/replay/UI only.
    """
    from .sources import Authorization, PhaseBoundedLoader

    start, end = ENGINEERING_WINDOW
    authorization = Authorization(start, end, "G2-01 engineering parity", ENGINEERING_WINDOW_LEDGER)
    loader = (
        PhaseBoundedLoader(authorization)
        if root is None
        else PhaseBoundedLoader(authorization, root)
    )

    def audit(run_id: str) -> tuple[SourceAuditEvent, ...]:
        events = []
        for index, entry in enumerate(loader.log):
            returned = entry.get("returned") or [None, None]
            events.append(
                SourceAuditEvent(
                    record_key("G2A", run_id, index),
                    run_id,
                    start,
                    entry["kind"],
                    str(entry.get("source", ",".join(entry.get("objects", [])))),
                    start,
                    end,
                    tuple(entry.get("opened_objects", ())),
                    returned[0],
                    returned[1],
                    int(entry.get("rows", 0)),
                    EXPOSED_WINDOW,
                    f"ledger={ENGINEERING_WINDOW_LEDGER}; purpose=engineering parity only",
                )
            )
        return tuple(events)

    def minutes() -> list[Minute]:
        loader.manifest_identity()
        return loader.minutes()

    return RunSpec(
        "G2-EXPOSED-ENGINEERING-WINDOW-2024-06-03",
        "Exposed <=2024 engineering window — NOT PERFORMANCE EVIDENCE",
        EXPOSED_WINDOW,
        start,
        end,
        minutes,
        loader.funding,
        ENGINEERING_FILTERS,
        audit,
        "BTCUSDT USD-M 1m, 2024-06-03..2024-06-10 (declared); parser/aggregation/replay parity only.",
    )


@dataclass
class BuiltRun:
    spec: RunSpec
    manifest: RunManifest
    minutes: list[Minute]
    funding: list[tuple[datetime, float]]
    audit: tuple[SourceAuditEvent, ...]

    def new_core(self) -> G2Core:
        return G2Core(
            self.manifest,
            FundingBook(self.funding),
            self.spec.filters,
            self.manifest.friction,
            self.audit,
        )


def build(spec: RunSpec) -> BuiltRun:
    minutes = spec.minutes()
    funding = spec.funding()
    manifest = build_manifest(spec, minutes, funding)
    audit = spec.audit(manifest.run_id) or synthetic_audit(
        manifest.run_id, spec.start, spec.end, len(minutes)
    )
    return BuiltRun(spec, manifest, minutes, funding, audit)


def run_batch(built: BuiltRun, until: datetime | None = None) -> G2Core:
    """Drive a fresh core minute by minute to `until` (default: run end)."""
    core = built.new_core()
    target = until or built.manifest.dataset_end
    for minute in built.minutes:
        if minute.available_at > target:
            break
        core.advance_to(minute.open_time)
        core.ingest(minute)
    core.advance_to(target)
    return core


def run_in_steps(built: BuiltRun, step: timedelta) -> G2Core:
    """Same core, driven in coarse virtual-time steps (replay-speed identity checks)."""
    core = built.new_core()
    pending = list(built.minutes)
    index = 0
    cursor = built.manifest.dataset_start
    while cursor < built.manifest.dataset_end:
        cursor = min(cursor + step, built.manifest.dataset_end)
        while index < len(pending) and pending[index].available_at <= cursor:
            core.ingest(pending[index])
            index += 1
        core.advance_to(cursor)
    return core


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)
