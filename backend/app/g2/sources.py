"""Phase-bounded G2 observation loader (data exposure manifest section 10).

1. The authorized interval is fixed before any observation I/O and may not reach 2025+.
2. Only manifest-listed USD-M monthly objects intersecting the interval are opened; directories
   are never enumerated.
3. Any other object is refused before it is opened.
4. Rows are filtered to the authorized bounds before they are returned.
5. Requested / opened / returned intervals are logged.
6. Manifest identity is readable without opening any observation object.
"""

from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.g1.sources import parse_kline_csv
from app.predictive import taker_flow_source as klines

from .bars import Minute
from .contract import PROTECTED_START

ROOT = Path(__file__).resolve().parents[3]
KLINE_MANIFEST = klines.MANIFEST_PATH
FUNDING_MANIFEST = "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json"
MARKET = klines.USDM
EXPOSED = "EXPOSED_DEVELOPMENT_ENGINEERING_WINDOW_NOT_PERFORMANCE_EVIDENCE"


class UnauthorizedObservationError(PermissionError):
    """An observation outside the authorized phase interval was requested or touched."""


@dataclass(frozen=True)
class Authorization:
    start: datetime
    end: datetime  # exclusive
    purpose: str
    ledger_record: str

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None or self.start >= self.end:
            raise UnauthorizedObservationError("the interval must be a non-empty UTC interval")
        if self.end > PROTECTED_START:  # exclusive end: at most the 2024-12-31 ceiling
            raise UnauthorizedObservationError("G2-01 may not request 2025+ observations")


def _month_bounds(month: str) -> tuple[datetime, datetime]:
    year, number = (int(part) for part in month.split("-"))
    start = datetime(year, number, 1, tzinfo=UTC)
    end = datetime(year + (number == 12), number % 12 + 1, 1, tzinfo=UTC)
    return start, end


def _read_file(path: Path) -> bytes:
    return path.read_bytes()


class PhaseBoundedLoader:
    def __init__(
        self,
        authorization: Authorization,
        root: Path = ROOT,
        opener: Callable[[Path], bytes] = _read_file,
    ) -> None:
        self.authorization = authorization
        self.root = root
        self._opener = opener
        self.log: list[dict[str, Any]] = []

    # ------------------------------------------------------------ metadata only
    def manifest_identity(self) -> dict[str, Any]:
        """Manifest metadata (identity/hashes); opens no observation object."""
        kline = json.loads((self.root / KLINE_MANIFEST).read_text(encoding="utf-8"))
        funding = json.loads((self.root / FUNDING_MANIFEST).read_text(encoding="utf-8"))
        self.log.append({"kind": "METADATA_READ", "objects": [KLINE_MANIFEST, FUNDING_MANIFEST]})
        return {
            "kline_manifest": kline["manifest_id"],
            "kline_object_index_sha256": kline["object_index_sha256"],
            "kline_request_ceiling": kline["request_ceiling"],
            "funding_manifest": funding["manifest_id"],
            "funding_file_sha256": funding["canonical"]["file_sha256"],
            "funding_last_time": funding["last_funding_time"],
        }

    def authorized_objects(self) -> list[dict[str, Any]]:
        """Manifest-listed USD-M monthly objects intersecting the interval (metadata only)."""
        kline = json.loads((self.root / KLINE_MANIFEST).read_text(encoding="utf-8"))
        chosen = []
        for archive in sorted(kline["archives"], key=lambda a: a["month"]):
            if archive["market"] != MARKET:
                continue
            start, end = _month_bounds(archive["month"])
            if start >= PROTECTED_START:
                continue  # never considered, never opened
            if start < self.authorization.end and end > self.authorization.start:
                chosen.append(archive)
        return chosen

    # ------------------------------------------------------------ observation I/O
    def _open(self, relative: str, covers: tuple[datetime, datetime]) -> bytes:
        start, end = covers
        auth = self.authorization
        if start >= PROTECTED_START or not (start < auth.end and end > auth.start):
            raise UnauthorizedObservationError(f"{relative} is outside the authorized interval")
        return self._opener(self.root / relative)

    def minutes(self) -> list[Minute]:
        auth = self.authorization
        out: list[Minute] = []
        opened: list[str] = []
        for archive in self.authorized_objects():
            bounds = _month_bounds(archive["month"])
            content = self._open(archive["raw_path"], bounds)
            opened.append(archive["raw_path"])
            if hashlib.sha256(content).hexdigest() != archive["sha256"]:
                raise UnauthorizedObservationError(f"{archive['raw_path']}: hash differs")
            year, number = (int(part) for part in archive["month"].split("-"))
            _, member = klines.archive_member(content, year, number)
            for bar in parse_kline_csv(member.decode("utf-8")):
                if not auth.start <= bar.open_time < auth.end:
                    continue
                out.append(
                    Minute(
                        bar.open_time,
                        float(bar.open),
                        float(bar.high),
                        float(bar.low),
                        float(bar.close),
                        float(bar.volume),
                        None if bar.quote_volume is None else float(bar.quote_volume),
                        None
                        if bar.taker_buy_base_volume is None
                        else float(bar.taker_buy_base_volume),
                    )
                )
        self.log.append(
            {
                "kind": "OBSERVATION_READ",
                "source": KLINE_MANIFEST,
                "requested": [auth.start, auth.end],
                "opened_objects": opened,
                "returned": [out[0].open_time, out[-1].available_at] if out else None,
                "rows": len(out),
            }
        )
        return out

    def funding(self) -> list[tuple[datetime, float]]:
        import pyarrow.parquet as pq

        auth = self.authorization
        manifest = json.loads((self.root / FUNDING_MANIFEST).read_text(encoding="utf-8"))
        canonical = manifest["canonical"]
        first = datetime.fromisoformat(manifest["first_funding_time"])
        last = datetime.fromisoformat(manifest["last_funding_time"])
        content = self._open(canonical["path"], (first, last + timedelta(minutes=1)))
        if hashlib.sha256(content).hexdigest() != canonical["file_sha256"]:
            raise UnauthorizedObservationError("funding artifact hash differs from its manifest")
        table = pq.read_table(io.BytesIO(content))
        rows = []
        for moment, rate in zip(
            table.column("funding_time").to_pylist(),
            table.column("funding_rate").to_pylist(),
            strict=True,
        ):
            moment = moment.astimezone(UTC)
            if auth.start <= moment < auth.end:
                rows.append((moment, float(rate)))
        self.log.append(
            {
                "kind": "OBSERVATION_READ",
                "source": FUNDING_MANIFEST,
                "requested": [auth.start, auth.end],
                "opened_objects": [canonical["path"]],
                "returned": [rows[0][0], rows[-1][0]] if rows else None,
                "rows": len(rows),
            }
        )
        return rows


# ------------------------------------------------------------------ pinned contract filters
EXCHANGE_INFO_ENDPOINT = "https://fapi.binance.com/fapi/v1/exchangeInfo"
EXCHANGE_INFO_MANIFEST = "data/manifests/BTCUSDT-USDM-EXCHANGEINFO-SNAPSHOT-V1.json"


def symbol_object_sha256(symbol: dict[str, Any]) -> str:
    canonical = json.dumps(symbol, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def normalized_filters(symbol: dict[str, Any]) -> dict[str, Any]:
    """PRICE_FILTER / LOT_SIZE / MARKET_LOT_SIZE / MIN_NOTIONAL values (filters only)."""
    filters = {f["filterType"]: f for f in symbol["filters"]}
    price, lot = filters["PRICE_FILTER"], filters["LOT_SIZE"]
    market = filters.get("MARKET_LOT_SIZE")
    notional = filters.get("MIN_NOTIONAL", {})
    return {
        "contract_type": symbol["contractType"],
        "status": symbol["status"],
        "price_filter": {k: price[k] for k in ("tickSize", "minPrice", "maxPrice")},
        "lot_size": {k: lot[k] for k in ("stepSize", "minQty", "maxQty")},
        "market_lot_size": None
        if market is None
        else {k: market[k] for k in ("stepSize", "minQty", "maxQty")},
        "min_notional": notional.get("notional"),
    }


def pinned_market_filters(root: Path = ROOT) -> Any:
    """ExchangeFilters for simulated market orders from the pinned snapshot (MARKET_LOT_SIZE)."""
    from .risk import ExchangeFilters

    record = json.loads((root / EXCHANGE_INFO_MANIFEST).read_text(encoding="utf-8"))
    if record["status"] != "PINNED":
        raise UnauthorizedObservationError("no pinned exchangeInfo snapshot is available")
    if symbol_object_sha256(record["symbol_object"]) != record["symbol_object_sha256"]:
        raise UnauthorizedObservationError("the pinned symbol object hash differs")
    normalized = normalized_filters(record["symbol_object"])
    if normalized != record["normalized"]:
        raise UnauthorizedObservationError("the normalized filters differ from the symbol object")
    lot = normalized["market_lot_size"] or normalized["lot_size"]
    return ExchangeFilters(
        f"{record['manifest_id']}@{record['raw_snapshot_sha256'][:16]}",
        normalized["price_filter"]["tickSize"],
        lot["stepSize"],
        lot["minQty"],
        lot["maxQty"],
        normalized["min_notional"],
    )
