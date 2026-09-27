"""G2-02 exposed-data integrity preflight (non-economic; 2020-01-01..2024-12-31 only).

Audits the canonical BTCUSDT USD-M 1m kline objects and the settled-funding artifact through the
phase-bounded loader: object presence versus the manifest, missing / duplicate / out-of-order /
off-grid minutes, gap distribution, incomplete 15m/1h/4h bars, the share of 15m decision instants
whose frozen G2-V0 state would be unavailable under the continuity and re-warm rules (including
the separate 4h context re-warm loss), and the funding settlement grid.

Only availability is recorded. No model is fitted, no forecast is scored, no action, P&L or return
is produced, and no protected 2025+ observation can be requested (the loader refuses it).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from app.predictive import taker_flow_source as klines

from .bars import Aggregator, Minute, valid_minute
from .contract import COLUMNS, FUNDING_INTERVAL
from .features import AVAILABLE, WARMUP, FeatureEngine
from .sources import KLINE_MANIFEST, MARKET, Authorization, PhaseBoundedLoader

ARTIFACT_PATH = "reports/validation/G2-02-DATA-INTEGRITY-PREFLIGHT-V1.json"
ARTIFACT_ID = "G2-02-DATA-INTEGRITY-PREFLIGHT-V1"
LEDGER_DECLARATION = "G2-02-DATA-PREFLIGHT-DECLARATION-001"
START = datetime(2020, 1, 1, tzinfo=UTC)
END = datetime(2025, 1, 1, tzinfo=UTC)  # exclusive: last observation 2024-12-31 23:59
MINUTE_MS = 60_000
TOTAL_MINUTES = int((END - START) // timedelta(minutes=1))
GAP_BUCKETS = ((1, 1), (2, 5), (6, 15), (16, 60), (61, 240), (241, 1440), (1441, 10**9))
BAR_MINUTES = {"15m": 15, "1h": 60, "4h": 240}


def expected_months() -> list[str]:
    return [f"{y:04d}-{m:02d}" for y in range(2020, 2025) for m in range(1, 13)]


def _month_bounds(month: str) -> tuple[datetime, datetime]:
    year, number = (int(part) for part in month.split("-"))
    return (
        datetime(year, number, 1, tzinfo=UTC),
        datetime(year + (number == 12), number % 12 + 1, 1, tzinfo=UTC),
    )


def _float(text: str) -> float:
    try:
        return float(text)
    except ValueError:
        return math.nan


def _gap_runs(present: np.ndarray) -> list[tuple[int, int]]:
    """(start index, length) of every maximal run of missing minutes."""
    missing = (~present).astype(np.int8)
    edges = np.diff(np.concatenate([[0], missing, [0]]))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return [(int(s), int(e - s)) for s, e in zip(starts, ends, strict=True)]


def _minute_time(index: int) -> str:
    return (START + timedelta(minutes=index)).isoformat()


class _Coverage:
    """Frozen G2-V0 state availability at every 15m decision instant (features only)."""

    def __init__(self) -> None:
        self.aggregator = Aggregator(("15m", "1h", "4h", "1d", "1w"))
        self.engine = FeatureEngine()
        self.next_decision = START + timedelta(minutes=15)
        self.first_available: datetime | None = None
        self.reasons: Counter[str] = Counter()
        self.rows: list[tuple[datetime, str | None, tuple[str, ...], bool]] = []

    def _decide_until(self, moment: datetime) -> None:
        while self.next_decision <= moment:
            for bar in self.aggregator.close_until(self.next_decision):
                self.engine.on_bar(bar)
            snap = self.engine.snapshot(self.next_decision)
            reason = None if snap.reason is None else str(snap.reason)
            if reason is None and self.first_available is None:
                self.first_available = self.next_decision
            self.rows.append((self.next_decision, reason, snap.term_status, snap.atr14 is not None))
            self.next_decision += timedelta(minutes=15)

    def add(self, minute: Minute) -> None:
        self._decide_until(minute.open_time)
        for bar in self.aggregator.add(minute):
            self.engine.on_bar(bar)

    def finish(self) -> None:
        self._decide_until(END)

    def summary(self) -> dict[str, Any]:
        total = len(self.rows)
        first = self.first_available
        initial = [r for r in self.rows if first is None or r[0] < first]
        after = [r for r in self.rows if first is not None and r[0] >= first]
        context = COLUMNS.index("CONTEXT_STRUCTURE")
        unavailable_after = [r for r in after if r[1] is not None]
        context_rewarm = [r for r in after if r[2][context] == WARMUP]
        context_only = [
            r
            for r in context_rewarm
            if all(s == AVAILABLE for i, s in enumerate(r[2]) if i != context)
        ]
        by_year: dict[str, dict[str, int]] = {}
        for moment, reason, _, _ in self.rows:
            year = by_year.setdefault(str(moment.year), {"decisions": 0, "unavailable": 0})
            year["decisions"] += 1
            year["unavailable"] += reason is not None
        term_warmup_after = {
            name: sum(r[2][i] == WARMUP for r in after) for i, name in enumerate(COLUMNS)
        }
        term_missing_after = {
            name: sum(r[2][i] == "MISSING_DATA" for r in after) for i, name in enumerate(COLUMNS)
        }
        return {
            "decision_instants": total,
            "state_unavailable_total": sum(r[1] is not None for r in self.rows),
            "state_unavailable_share": sum(r[1] is not None for r in self.rows) / total,
            "unavailable_by_reason": dict(sorted(Counter(r[1] for r in self.rows if r[1]).items())),
            "first_available_decision": None if first is None else first.isoformat(),
            "initial_warmup_decisions": len(initial),
            "after_initial_warmup": {
                "decisions": len(after),
                "unavailable": len(unavailable_after),
                "unavailable_share": len(unavailable_after) / len(after) if after else None,
                "unavailable_by_reason": dict(
                    sorted(Counter(r[1] for r in unavailable_after).items())
                ),
                "context_4h_rewarm_decisions": len(context_rewarm),
                "context_4h_rewarm_share": len(context_rewarm) / len(after) if after else None,
                "context_4h_rewarm_sole_cause_decisions": len(context_only),
                "context_4h_rewarm_sole_cause_share": (
                    len(context_only) / len(after) if after else None
                ),
                "term_warmup_decisions": term_warmup_after,
                "term_missing_decisions": term_missing_after,
                "atr14_unavailable_decisions": sum(not r[3] for r in after),
            },
            "by_year": by_year,
            "note": (
                "availability of the frozen state only; no model, forecast or action. The single "
                "decision instant 2025-01-01T00:00Z is the close of the final 2024 candle; no 2025 "
                "observation is read."
            ),
        }


def _audit_klines(loader: PhaseBoundedLoader, root: Path) -> tuple[dict[str, Any], np.ndarray, Any]:
    manifest = json.loads((root / KLINE_MANIFEST).read_text(encoding="utf-8"))
    listed = sorted(
        (a for a in manifest["archives"] if a["market"] == MARKET), key=lambda a: a["month"]
    )
    listed_months = [a["month"] for a in listed]
    expected = expected_months()
    authorized = loader.authorized_objects()
    missing_local = [a["raw_path"] for a in authorized if not (root / a["raw_path"]).is_file()]
    objects = {
        "months_expected": len(expected),
        "months_in_manifest": len([m for m in expected if m in listed_months]),
        "months_missing_from_manifest": [m for m in expected if m not in listed_months],
        "objects_authorized": [a["raw_path"] for a in authorized],
        "objects_missing_locally": missing_local,
        "manifest_object_index_sha256": manifest["object_index_sha256"],
    }
    present = np.zeros(TOTAL_MINUTES, dtype=bool)
    if objects["months_missing_from_manifest"] or missing_local:
        return {"objects": objects, "status": "BLOCKED"}, present, None
    coverage = _Coverage()
    per_month: dict[str, dict[str, int]] = {}
    for archive in authorized:
        month = archive["month"]
        lo, hi = _month_bounds(month)
        content = loader._open(archive["raw_path"], (lo, hi))
        if hashlib.sha256(content).hexdigest() != archive["sha256"]:
            raise ValueError(f"{archive['raw_path']}: object hash differs from the manifest")
        year, number = (int(part) for part in month.split("-"))
        _, member = klines.archive_member(content, year, number)
        lo_ms, hi_ms = int(lo.timestamp() * 1000), int(hi.timestamp() * 1000)
        stats: Counter[str] = Counter()
        seen: set[int] = set()
        previous: int | None = None
        valid_minutes: list[Minute] = []
        for position, row in enumerate(csv.reader(io.StringIO(member.decode("utf-8")))):
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if position == 0 and tuple(c.strip() for c in row) == klines.KLINE_COLUMNS:
                stats["header_rows"] += 1
                continue
            stats["rows"] += 1
            if len(row) != len(klines.KLINE_COLUMNS):
                stats["malformed_rows"] += 1
                continue
            try:
                open_ms, close_ms = int(row[0]), int(row[6])
            except ValueError:
                stats["malformed_rows"] += 1
                continue
            if previous is not None and open_ms < previous:
                stats["out_of_order_rows"] += 1
            previous = open_ms if previous is None else max(previous, open_ms)
            if open_ms in seen:
                stats["duplicate_timestamps"] += 1
                continue
            seen.add(open_ms)
            if open_ms % MINUTE_MS or close_ms != open_ms + MINUTE_MS - 1:
                stats["off_grid_rows"] += 1
                continue
            if not lo_ms <= open_ms < hi_ms:
                stats["outside_own_month_rows"] += 1
                continue
            values = [_float(row[k]) for k in (1, 2, 3, 4, 5, 7, 9)]
            opened = datetime.fromtimestamp(open_ms / 1000, tz=UTC)
            o, h, low, c, v, quote, taker = values
            minute = Minute(opened, o, h, low, c, v, quote, taker)
            if not valid_minute(minute) or not all(math.isfinite(v) for v in values[5:]):
                stats["invalid_value_rows"] += 1
                continue
            stats["valid_minutes"] += 1
            if v <= 0:
                stats["zero_volume_valid_minutes"] += 1
            present[int((opened - START) // timedelta(minutes=1))] = True
            valid_minutes.append(minute)
        valid_minutes.sort(key=lambda m: m.open_time)
        for minute in valid_minutes:
            coverage.add(minute)
        expected_minutes = int((hi - lo) // timedelta(minutes=1))
        stats["expected_minutes"] = expected_minutes
        stats["missing_minutes"] = expected_minutes - stats["valid_minutes"]
        per_month[month] = dict(sorted(stats.items()))
    coverage.finish()
    objects["objects_read"] = [a["raw_path"] for a in authorized]
    loader.log.append(
        {
            "kind": "OBSERVATION_READ",
            "source": KLINE_MANIFEST,
            "requested": [loader.authorization.start, loader.authorization.end],
            "opened_objects": objects["objects_read"],
            "rows": int(present.sum()),
        }
    )
    by_year: dict[str, Counter[str]] = {}
    for month, month_stats in per_month.items():
        by_year.setdefault(month[:4], Counter()).update(month_stats)
    return (
        {
            "objects": objects,
            "status": "EXECUTED",
            "by_month": per_month,
            "by_year": {year: dict(sorted(v.items())) for year, v in sorted(by_year.items())},
        },
        present,
        coverage,
    )


def _gaps_and_bars(present: np.ndarray) -> dict[str, Any]:
    runs = _gap_runs(present)
    longest = max(runs, key=lambda r: (r[1], -r[0])) if runs else None
    buckets = {
        f"{lo}-{hi if hi < 10**9 else 'inf'}": sum(1 for _, n in runs if lo <= n <= hi)
        for lo, hi in GAP_BUCKETS
    }
    missing_in_buckets = {
        f"{lo}-{hi if hi < 10**9 else 'inf'}": sum(n for _, n in runs if lo <= n <= hi)
        for lo, hi in GAP_BUCKETS
    }
    bars = {}
    for tf, size in BAR_MINUTES.items():
        counts = present.reshape(-1, size).sum(axis=1)
        bars[tf] = {
            "windows": len(counts),
            "complete": int((counts == size).sum()),
            "incomplete_partial": int(((counts > 0) & (counts < size)).sum()),
            "absent": int((counts == 0).sum()),
        }
    return {
        "total_expected_minutes": TOTAL_MINUTES,
        "valid_minutes": int(present.sum()),
        "missing_minutes": int((~present).sum()),
        "gap_runs": len(runs),
        "longest_gap": None
        if longest is None
        else {"start": _minute_time(longest[0]), "minutes": longest[1]},
        "ten_longest_gaps": [
            {"start": _minute_time(s), "minutes": n}
            for s, n in sorted(runs, key=lambda r: (-r[1], r[0]))[:10]
        ],
        "gap_count_by_length": buckets,
        "missing_minutes_by_gap_length": missing_in_buckets,
        "bars": bars,
    }


def _audit_funding(loader: PhaseBoundedLoader) -> dict[str, Any]:
    rows = loader.funding()
    times = [moment for moment, _ in rows]
    minutes = [m.replace(second=0, microsecond=0) for m in times]
    exact_dupes = sum(n - 1 for n in Counter(times).values() if n > 1)
    minute_dupes = sum(n - 1 for n in Counter(minutes).values() if n > 1)

    def on_grid(m: datetime) -> bool:
        return m.minute == 0 and m.hour % 8 == 0

    off_grid = [m.isoformat() for m in minutes if not on_grid(m)]
    sub_minute = Counter(
        "EXACT"
        if t.second == 0 and t.microsecond == 0
        else "SUB_SECOND_OFFSET"
        if t.second == 0
        else "SECONDS_OFFSET"
        for t in times
    )
    expected = []
    moment = START
    while moment < END:
        expected.append(moment)
        moment += FUNDING_INTERVAL
    recorded = set(minutes)
    missing = [m.isoformat() for m in expected if m not in recorded]
    non_finite = sum(1 for _, rate in rows if not math.isfinite(rate))
    ordered = all(a < b for a, b in zip(times, times[1:], strict=False))
    valid_grid = not missing and not off_grid and minute_dupes == 0
    return {
        "records_in_window": len(rows),
        "first": times[0].isoformat() if times else None,
        "last": times[-1].isoformat() if times else None,
        "strictly_increasing": ordered,
        "exact_duplicate_timestamps": exact_dupes,
        "duplicate_settlement_minutes": minute_dupes,
        "expected_8h_settlements": len(expected),
        "missing_expected_settlements": missing,
        "off_grid_settlements": off_grid,
        "timestamp_precision": dict(sorted(sub_minute.items())),
        "non_finite_rates": non_finite,
        "historical_8h_grid_assumption_valid": valid_grid,
    }


def build(root: Path) -> dict[str, Any]:
    authorization = Authorization(START, END, "G2-02 data integrity preflight", LEDGER_DECLARATION)
    loader = PhaseBoundedLoader(authorization, root)
    identity = loader.manifest_identity()
    klines_audit, present, coverage = _audit_klines(loader, root)
    payload: dict[str, Any] = {
        "artifact": ARTIFACT_ID,
        "ledger_declaration": LEDGER_DECLARATION,
        "evidence_class": "NON_ECONOMIC_DATA_INTEGRITY_PREFLIGHT",
        "instrument": "BTCUSDT_USDM_PERPETUAL",
        "interval": [START.isoformat(), END.isoformat()],
        "interval_end_exclusive": True,
        "manifest_identity": identity,
        "klines": klines_audit,
    }
    if klines_audit["status"] == "BLOCKED":
        payload["status"] = "BLOCKED_MISSING_SOURCE_OBJECTS"
    else:
        payload["minute_grid"] = _gaps_and_bars(present)
        payload["decision_coverage"] = coverage.summary()
        payload["funding"] = _audit_funding(loader)
        payload["status"] = "EXECUTED"
    opened = sorted({o for entry in loader.log for o in entry.get("opened_objects", [])})
    payload["opened_objects"] = opened
    payload["protected_objects_opened"] = any("2025" in o for o in opened)
    payload["claims"] = {
        "model_fitting": False,
        "forecast_scoring": False,
        "economic_decisions": False,
        "pnl_return_sharpe_profit_factor": False,
        "variant_comparison_or_tuning": False,
        "protected_2025_observations": False,
    }
    return payload
