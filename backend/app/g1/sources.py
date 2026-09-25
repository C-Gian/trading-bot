"""System G1 Development V1 source bindings (identity only until execution is authorized).

Bindings to existing repository manifests and parsers:

- USD-M perpetual BTCUSDT official 1m klines (reference paper instrument; OHLC, base volume, quote
  volume, taker-buy base volume): `BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1`, market
  `USDM_PERPETUAL`, 60 monthly official objects 2020-01..2024-12;
- USD-M settled funding history (signed accounting): `BTCUSDT-USDM-FUNDING-DEV-v1`;
- BTCUSDT spot 1m: NOT REQUIRED — no frozen G1 Development V1 definition reads spot.

`binding_identity` reads manifest metadata only. `parse_kline_csv` is a pure parser of CSV text.
`RealSourceHandle` — the only object that opens market observations — can be constructed only by
`app.g1.batch.authorize_real_sources`, behind the state execution guard.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.predictive import taker_flow_source as klines

from .bars import Bar, minute_bar

ROOT = Path(__file__).resolve().parents[3]
KLINE_MANIFEST = klines.MANIFEST_PATH
FUNDING_MANIFEST = "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json"
SPOT_MANIFEST = "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
REFERENCE_MARKET = klines.USDM
FIRST_MONTH, LAST_MONTH = "2020-01", "2024-12"
DATA_CEILING = datetime(2024, 12, 31, 23, 59, tzinfo=UTC)
PARSER_VERSION = "G1_USDM_1M_FULL_KLINE_PARSER_V1"
COLUMN_INDEX = {name: index for index, name in enumerate(klines.KLINE_COLUMNS)}


class SourceBindingError(RuntimeError):
    """A required field/source is unavailable: stop, never substitute another source."""


def canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _months() -> list[str]:
    return [f"{year:04d}-{month:02d}" for year in range(2020, 2025) for month in range(1, 13)]


def binding_identity(root: Path = ROOT) -> dict[str, Any]:
    """Outcome-blind identity of every bound source (manifest metadata only)."""
    kline = json.loads((root / KLINE_MANIFEST).read_text(encoding="utf-8"))
    funding = json.loads((root / FUNDING_MANIFEST).read_text(encoding="utf-8"))
    usdm = sorted(
        (a for a in kline["archives"] if a["market"] == REFERENCE_MARKET), key=lambda a: a["month"]
    )
    months = [a["month"] for a in usdm]
    if months != _months():
        raise SourceBindingError("USD-M 1m kline objects do not cover 2020-01..2024-12 exactly")
    if not all(a["official_checksum_verified"] for a in usdm):
        raise SourceBindingError("a USD-M kline object lacks official checksum verification")
    required = ("open", "high", "low", "close", "volume", "quote_volume", "taker_buy_volume")
    if not all(field in klines.KLINE_COLUMNS for field in required):
        raise SourceBindingError("the official kline schema lacks a required G1 field")
    columns = [c["name"] for c in funding["canonical"]["columns"]]
    if columns != ["funding_time", "funding_rate"]:
        raise SourceBindingError("the funding canonical schema differs from the binding")
    return {
        "reference_klines": {
            "manifest": KLINE_MANIFEST,
            "manifest_canonical_sha256": canonical_sha256(root / KLINE_MANIFEST),
            "manifest_id": kline["manifest_id"],
            "version": kline["version"],
            "market": REFERENCE_MARKET,
            "interval": kline["interval"],
            "object_index_sha256": kline["object_index_sha256"],
            "months": [months[0], months[-1], len(months)],
            "object_sha256": {a["month"]: a["sha256"] for a in usdm},
            "fields": list(required),
            "parser": PARSER_VERSION,
            "request_ceiling": kline["request_ceiling"],
        },
        "funding": {
            "manifest": FUNDING_MANIFEST,
            "manifest_canonical_sha256": canonical_sha256(root / FUNDING_MANIFEST),
            "canonical_path": funding["canonical"]["path"],
            "canonical_file_sha256": funding["canonical"]["file_sha256"],
            "canonical_logical_sha256": funding["canonical"]["logical_sha256"],
            "records": funding["records"],
            "last_funding_time": funding["last_funding_time"],
            "fields": columns,
        },
        "spot_1m": {
            "manifest": SPOT_MANIFEST,
            "status": "NOT_REQUIRED_NO_FROZEN_G1_DEFINITION_READS_SPOT",
        },
        "market_observations_read": False,
    }


def _decimal(text: str) -> Decimal | None:
    try:
        value = Decimal(text.strip())
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def parse_kline_csv(text: str) -> Iterator[Bar]:
    """Yield valid USD-M 1m bars with every G1 field; invalid rows are left missing."""
    reader = csv.reader(io.StringIO(text))
    for position, row in enumerate(reader):
        if not row or (len(row) == 1 and not row[0].strip()):
            continue
        if position == 0 and tuple(c.strip() for c in row) == klines.KLINE_COLUMNS:
            continue
        if len(row) != len(klines.KLINE_COLUMNS):
            raise SourceBindingError(f"row {position}: expected 12 kline columns")
        try:
            open_ms = int(row[COLUMN_INDEX["open_time"]])
            close_ms = int(row[COLUMN_INDEX["close_time"]])
        except ValueError as exc:
            raise SourceBindingError(f"row {position}: unparseable timestamp") from exc
        if open_ms % klines.MINUTE_MS or close_ms != open_ms + klines.MINUTE_CLOSE_OFFSET_MS:
            continue
        values = {
            name: _decimal(row[COLUMN_INDEX[name]])
            for name in (
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_volume",
                "taker_buy_volume",
            )
        }
        if any(value is None for value in values.values()):
            continue
        o, h, low, c = (values[k] for k in ("open", "high", "low", "close"))
        assert o is not None and h is not None and low is not None and c is not None
        if not low <= min(o, c) <= max(o, c) <= h or low <= 0:
            continue
        opened = datetime.fromtimestamp(open_ms / 1000, tz=UTC)
        if opened > DATA_CEILING:
            raise SourceBindingError("a kline beyond the development ceiling was presented")
        volume, quote, taker = values["volume"], values["quote_volume"], values["taker_buy_volume"]
        assert volume is not None
        yield minute_bar(opened, o, h, low, c, volume, quote, taker)


def funding_minute(funding_time: datetime) -> datetime:
    """Settlement instants are mapped to their UTC minute (exchange stamps carry milliseconds)."""
    return funding_time.replace(second=0, microsecond=0)


class RealSourceHandle:
    """Opens real observations. Constructed only by the authorized batch guard."""

    def __init__(self, root: Path, authorization: str, token: object) -> None:
        from . import batch

        if token is not batch.GUARD_TOKEN:
            raise PermissionError("real sources are reachable only through the execution guard")
        self.root = root
        self.authorization = authorization
        self.identity = binding_identity(root)

    def minutes(self) -> Iterator[Bar]:
        objects = self.identity["reference_klines"]["object_sha256"]
        for month, digest in objects.items():
            year, number = (int(part) for part in month.split("-"))
            path = self.root / klines.raw_path(REFERENCE_MARKET, year, number)
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != digest:
                raise SourceBindingError(f"{path.name}: object hash differs from the manifest")
            _, member = klines.archive_member(content, year, number)
            yield from parse_kline_csv(member.decode("utf-8"))

    def funding(self) -> dict[datetime, Decimal]:
        from app.predictive.funding_source import load_settled_funding

        source = load_settled_funding(self.root)
        rates = {}
        for time_us, rate in zip(source.times_us, source.rates, strict=True):
            if not math.isfinite(rate):
                continue
            moment = funding_minute(
                datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=time_us)
            )
            rates[moment] = Decimal(repr(rate))
        return rates
