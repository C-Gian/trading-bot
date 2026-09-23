"""Official Binance spot + USD-M BTCUSDT 1m klines for the public taker-flow foundation.

Frozen protocol: `research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md`.

The only admitted source class is the official Binance public data archive
(`data.binance.vision`), monthly 1m kline objects for BTCUSDT on two markets:

- spot: `data/spot/monthly/klines/BTCUSDT/1m`;
- USD-M perpetual: `data/futures/um/monthly/klines/BTCUSDT/1m`.

Development source window: 2020-01-01 through 2024-12-31 inclusive. No post-cutoff object is
ever requested and a post-cutoff record fails the load closed.

Every monthly object is verified against the archive's own `.CHECKSUM` file on acquisition,
and its source path, byte size, member name, member size and official checksum are pinned in
an immutable manifest. Every later load re-verifies each stored object against that manifest,
so no silently substituted or revised object can enter the foundation.

Minute validity is strict and never repaired. A minute is VALID only when exactly one record
carries it, on the one-minute grid, complete (`close_time == open_time + 59_999`), inside its
own monthly object, with finite close, quote volume and taker-buy quote volume. Absent,
duplicated, timestamp-invalid or incomplete minutes are recorded as such; nothing is
interpolated, forward-filled or de-duplicated.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import zipfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

SOURCE_VERSION = "BINANCE_PUBLIC_BTCUSDT_SPOT_AND_USDM_1M_KLINES_V1"
MANIFEST_ID = "BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1"
MANIFEST_PATH = f"data/manifests/{MANIFEST_ID}.json"
RAW_ROOT = "data/raw/public-taker-flow"
PROTOCOL_PATH = "research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md"
OWNER_DECISION_PATH = "decisions/ADR-0032-OWNER-SELECTS-NO-COST-PUBLIC-DATA-PATH.md"

SYMBOL = "BTCUSDT"
INTERVAL = "1m"
ARCHIVE_HOST = "https://data.binance.vision"
SOURCE_NAME = "BINANCE_OFFICIAL_PUBLIC_DATA_ARCHIVE"

SPOT = "SPOT"
USDM = "USDM_PERPETUAL"
MARKETS = (SPOT, USDM)
ARCHIVE_PREFIX = {
    SPOT: "data/spot/monthly/klines/BTCUSDT/1m",
    USDM: "data/futures/um/monthly/klines/BTCUSDT/1m",
}
RAW_DIRECTORY = {SPOT: "spot", USDM: "um"}

FIRST_MONTH = (2020, 1)
LAST_MONTH = (2024, 12)
WINDOW_START_MS = int(datetime(2020, 1, 1, tzinfo=UTC).timestamp() * 1000)
WINDOW_END_MS = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp() * 1000)
DEVELOPMENT_CEILING = "2024-12-31T23:59:59.999Z"
MINUTE_MS = 60_000
MINUTE_CLOSE_OFFSET_MS = MINUTE_MS - 1
WINDOW_MINUTES = (WINDOW_END_MS - WINDOW_START_MS) // MINUTE_MS

# The archive's own kline column order. Futures objects may carry this exact header line.
KLINE_COLUMNS = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "count",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "ignore",
)
OPEN_TIME, CLOSE, CLOSE_TIME, QUOTE_VOLUME, TAKER_BUY_QUOTE_VOLUME = 0, 4, 6, 7, 10

# Minute status codes.
ABSENT = 0
VALID = 1
INVALID = 2

# Why a minute is INVALID. Counted per market; the first rule that fires is recorded.
DUPLICATED_MINUTE = "DUPLICATED_MINUTE"
OFF_GRID_TIMESTAMP = "OFF_GRID_TIMESTAMP"
INCOMPLETE_MINUTE = "INCOMPLETE_MINUTE"
OUTSIDE_OWN_MONTH = "OUTSIDE_OWN_MONTH"
NON_FINITE_VALUE = "NON_FINITE_VALUE"
INVALIDITY_TAXONOMY = (
    DUPLICATED_MINUTE,
    OFF_GRID_TIMESTAMP,
    INCOMPLETE_MINUTE,
    OUTSIDE_OWN_MONTH,
    NON_FINITE_VALUE,
)


class TakerFlowSourceError(RuntimeError):
    """The public kline substrate is not usable as the frozen protocol specifies."""


# --------------------------------------------------------------------------------------
# Archive identity.
# --------------------------------------------------------------------------------------


def months() -> tuple[tuple[int, int], ...]:
    """Every development month in chronological order."""
    out: list[tuple[int, int]] = []
    year, month = FIRST_MONTH
    while (year, month) <= LAST_MONTH:
        out.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return tuple(out)


def archive_name(year: int, month: int) -> str:
    return f"{SYMBOL}-{INTERVAL}-{year:04d}-{month:02d}.zip"


def member_name(year: int, month: int) -> str:
    return archive_name(year, month).removesuffix(".zip") + ".csv"


def source_path(market: str, year: int, month: int) -> str:
    """The object's path inside the official archive host."""
    return f"{ARCHIVE_PREFIX[market]}/{archive_name(year, month)}"


def archive_url(market: str, year: int, month: int) -> str:
    return f"{ARCHIVE_HOST}/{source_path(market, year, month)}"


def raw_path(market: str, year: int, month: int) -> str:
    """Repository-relative storage path of the verified raw object."""
    return f"{RAW_ROOT}/{RAW_DIRECTORY[market]}/{archive_name(year, month)}"


def month_bounds_ms(year: int, month: int) -> tuple[int, int]:
    start = datetime(year, month, 1, tzinfo=UTC)
    end = (
        datetime(year + 1, 1, 1, tzinfo=UTC)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=UTC)
    )
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_checksum_file(text: str, expected_name: str) -> str:
    """The official `<sha256>  <file name>` line, checked against the object it describes."""
    fields = text.split()
    if len(fields) != 2:
        raise TakerFlowSourceError(f"{expected_name}: malformed official checksum file")
    digest, name = fields[0].strip().lower(), fields[1].strip()
    if name != expected_name:
        raise TakerFlowSourceError(f"{expected_name}: the checksum file names {name}")
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise TakerFlowSourceError(f"{expected_name}: the official checksum is not SHA-256")
    return digest


def verify_against_checksum(content: bytes, official: str, name: str) -> str:
    digest = sha256_bytes(content)
    if digest != official:
        raise TakerFlowSourceError(f"{name}: the object does not match its official checksum")
    return digest


def archive_member(content: bytes, year: int, month: int) -> tuple[str, bytes]:
    """The single CSV member an official monthly object must contain."""
    expected = member_name(year, month)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
        if names != [expected]:
            raise TakerFlowSourceError(f"{expected}: unexpected archive members {names}")
        return expected, archive.read(expected)


def manifest_entry(
    market: str,
    year: int,
    month: int,
    content: bytes,
    official_checksum: str,
    retrieval_time_utc: str,
) -> dict[str, Any]:
    """One immutable manifest record: source path, sizes and the official checksum."""
    digest = verify_against_checksum(content, official_checksum, archive_name(year, month))
    name, member = archive_member(content, year, month)
    return {
        "market": market,
        "month": f"{year:04d}-{month:02d}",
        "source_path": source_path(market, year, month),
        "url": archive_url(market, year, month),
        "raw_path": raw_path(market, year, month),
        "archive_size_bytes": len(content),
        "sha256": digest,
        "official_checksum_sha256": official_checksum,
        "official_checksum_verified": True,
        "member_name": name,
        "member_size_bytes": len(member),
        "member_sha256": sha256_bytes(member),
        "retrieval_time_utc": retrieval_time_utc,
    }


def build_manifest(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The immutable acquisition manifest over every market and development month."""
    ordered = sorted(entries, key=lambda item: (MARKETS.index(item["market"]), item["month"]))
    expected = [(market, f"{y:04d}-{m:02d}") for market in MARKETS for y, m in months()]
    observed = [(item["market"], item["month"]) for item in ordered]
    if observed != expected:
        raise TakerFlowSourceError("the manifest must pin exactly every market-month once")
    index_bytes = json.dumps(
        [[item["market"], item["month"], item["sha256"]] for item in ordered]
    ).encode("utf-8")
    return {
        "schema_version": 1,
        "manifest_id": MANIFEST_ID,
        "version": SOURCE_VERSION,
        "protocol": PROTOCOL_PATH,
        "owner_decision_record": OWNER_DECISION_PATH,
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "markets": list(MARKETS),
        "source": {
            "name": SOURCE_NAME,
            "host": ARCHIVE_HOST,
            "prefixes": dict(ARCHIVE_PREFIX),
            "granularity": "MONTHLY_OBJECTS",
            "credential_free": True,
            "third_party_vendor": False,
            "rest_api_history": False,
            "reconstructed_or_backfilled": False,
        },
        "development_source_window": ["2020-01-01", "2024-12-31"],
        "request_ceiling": DEVELOPMENT_CEILING,
        "raw_root": RAW_ROOT,
        "objects": len(ordered),
        "official_checksums_verified": len(ordered),
        "object_index_sha256": sha256_bytes(index_bytes),
        "archives": list(ordered),
    }


# --------------------------------------------------------------------------------------
# Parsing.
# --------------------------------------------------------------------------------------


def _is_header(row: Sequence[str]) -> bool:
    return tuple(cell.strip() for cell in row) == KLINE_COLUMNS


def iter_kline_rows(text: str) -> Iterator[tuple[int, int, float, float, float]]:
    """Yield `(open_time_ms, close_time_ms, close, quote_volume, taker_buy_quote_volume)`.

    Deterministic and fail-closed on schema: a row with the wrong column count or a
    non-integer timestamp aborts. Non-finite numeric values are passed through so the
    minute book can mark them unavailable rather than silently drop them.
    """
    reader = csv.reader(io.StringIO(text))
    for position, row in enumerate(reader):
        if not row or (len(row) == 1 and not row[0].strip()):
            continue
        if position == 0 and _is_header(row):
            continue
        if len(row) != len(KLINE_COLUMNS):
            raise TakerFlowSourceError(f"row {position}: expected 12 kline columns")
        try:
            open_time = int(row[OPEN_TIME])
            close_time = int(row[CLOSE_TIME])
            close = float(row[CLOSE])
            quote = float(row[QUOTE_VOLUME])
            taker_quote = float(row[TAKER_BUY_QUOTE_VOLUME])
        except ValueError as exc:
            raise TakerFlowSourceError(f"row {position}: unparseable kline field") from exc
        if open_time >= 10**14:
            raise TakerFlowSourceError(f"row {position}: timestamp is not in milliseconds")
        yield open_time, close_time, close, quote, taker_quote


@dataclass
class MinuteBook:
    """One market's development-window minute grid, indexed from 2020-01-01T00:00Z."""

    market: str
    status: Any = field(default=None)
    close: Any = field(default=None)
    quote: Any = field(default=None)
    taker_quote: Any = field(default=None)
    records: int = 0
    invalid_reasons: dict[str, int] = field(
        default_factory=lambda: {reason: 0 for reason in INVALIDITY_TAXONOMY}
    )

    def __post_init__(self) -> None:
        import numpy as np

        if self.status is None:
            self.status = np.zeros(WINDOW_MINUTES, dtype=np.int8)
            self.close = np.full(WINDOW_MINUTES, np.nan, dtype=np.float64)
            self.quote = np.full(WINDOW_MINUTES, np.nan, dtype=np.float64)
            self.taker_quote = np.full(WINDOW_MINUTES, np.nan, dtype=np.float64)

    def _invalidate(self, index: int, reason: str) -> None:
        import numpy as np

        self.invalid_reasons[reason] += 1
        self.status[index] = INVALID
        self.close[index] = np.nan
        self.quote[index] = np.nan
        self.taker_quote[index] = np.nan

    def ingest(
        self,
        rows: Iterator[tuple[int, int, float, float, float]],
        month_start_ms: int,
        month_end_ms: int,
    ) -> None:
        for open_time, close_time, close, quote, taker_quote in rows:
            self.records += 1
            if open_time >= WINDOW_END_MS:
                raise TakerFlowSourceError("refusing to admit a post-cutoff kline record")
            if open_time < WINDOW_START_MS:
                raise TakerFlowSourceError("a kline record precedes the development window")
            index = (open_time - WINDOW_START_MS) // MINUTE_MS
            if self.status[index] != ABSENT:
                self._invalidate(index, DUPLICATED_MINUTE)
                continue
            if (open_time - WINDOW_START_MS) % MINUTE_MS:
                self._invalidate(index, OFF_GRID_TIMESTAMP)
                continue
            if close_time != open_time + MINUTE_CLOSE_OFFSET_MS:
                self._invalidate(index, INCOMPLETE_MINUTE)
                continue
            if not month_start_ms <= open_time < month_end_ms:
                self._invalidate(index, OUTSIDE_OWN_MONTH)
                continue
            if not (math.isfinite(close) and math.isfinite(quote) and math.isfinite(taker_quote)):
                self._invalidate(index, NON_FINITE_VALUE)
                continue
            self.status[index] = VALID
            self.close[index] = close
            self.quote[index] = quote
            self.taker_quote[index] = taker_quote

    def summary(self) -> dict[str, Any]:
        import numpy as np

        return {
            "market": self.market,
            "records": self.records,
            "grid_minutes": WINDOW_MINUTES,
            "valid_minutes": int(np.count_nonzero(self.status == VALID)),
            "absent_minutes": int(np.count_nonzero(self.status == ABSENT)),
            "invalid_minutes": int(np.count_nonzero(self.status == INVALID)),
            "invalid_reasons": dict(self.invalid_reasons),
        }


def load_manifest(root: Path = ROOT) -> dict[str, Any]:
    path = root / MANIFEST_PATH
    if not path.is_file():
        raise TakerFlowSourceError(
            f"{MANIFEST_PATH} is missing: run scripts/acquire_public_taker_flow.py first"
        )
    manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("manifest_id") != MANIFEST_ID or manifest.get("version") != SOURCE_VERSION:
        raise TakerFlowSourceError("the manifest is not the frozen public taker-flow manifest")
    build_manifest(manifest["archives"])  # re-asserts exact market-month coverage
    return manifest


def verified_object(root: Path, entry: Mapping[str, Any]) -> bytes:
    """Re-read one stored raw object and re-verify it against its pinned manifest record."""
    path = root / entry["raw_path"]
    if not path.is_file():
        raise TakerFlowSourceError(f"{entry['raw_path']}: pinned raw object is missing")
    content = path.read_bytes()
    if len(content) != entry["archive_size_bytes"]:
        raise TakerFlowSourceError(f"{entry['raw_path']}: size differs from the manifest")
    if (
        sha256_bytes(content) != entry["sha256"]
        or entry["sha256"] != entry["official_checksum_sha256"]
    ):
        raise TakerFlowSourceError(f"{entry['raw_path']}: checksum differs from the manifest")
    return content


def load_minute_books(root: Path = ROOT) -> tuple[dict[str, MinuteBook], dict[str, Any]]:
    """Both markets' minute books, built only from manifest-verified official objects."""
    manifest = load_manifest(root)
    books = {market: MinuteBook(market) for market in MARKETS}
    for entry in manifest["archives"]:
        year, month = (int(part) for part in entry["month"].split("-"))
        content = verified_object(root, entry)
        name, member = archive_member(content, year, month)
        if name != entry["member_name"] or len(member) != entry["member_size_bytes"]:
            raise TakerFlowSourceError(f"{entry['raw_path']}: member differs from the manifest")
        start, end = month_bounds_ms(year, month)
        books[entry["market"]].ingest(iter_kline_rows(member.decode("utf-8")), start, end)
    return books, manifest


__all__ = [
    "ABSENT",
    "ARCHIVE_PREFIX",
    "INVALID",
    "INVALIDITY_TAXONOMY",
    "MANIFEST_ID",
    "MANIFEST_PATH",
    "MARKETS",
    "MINUTE_MS",
    "RAW_ROOT",
    "SPOT",
    "USDM",
    "VALID",
    "WINDOW_END_MS",
    "WINDOW_MINUTES",
    "WINDOW_START_MS",
    "MinuteBook",
    "TakerFlowSourceError",
    "archive_member",
    "archive_url",
    "build_manifest",
    "iter_kline_rows",
    "load_manifest",
    "load_minute_books",
    "manifest_entry",
    "month_bounds_ms",
    "months",
    "parse_checksum_file",
    "raw_path",
    "verified_object",
    "verify_against_checksum",
]
