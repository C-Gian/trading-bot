"""Deterministic official-archive inventory for the cross-sectional feasibility study.

Listing the bucket today is allowed: it only enumerates which historical objects exist.
Every object admitted into development must carry a month partition inside the frozen
development window, so no post-cutoff market information can reach the universe.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import time
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .cross_section import (
    ARCHIVE_LISTING_BASE,
    ARCHIVE_PREFIX,
    DEVELOPMENT_END_US,
    KLINE_INTERVAL,
    QUOTE_ASSET,
    ArchiveObject,
    is_candidate_symbol,
    is_leveraged_token,
    month_in_development,
    monthly_object_url,
)

INVENTORY_PATH = "data/manifests/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.json"
RAW_ROOT = "data/raw/cross_section"
USER_AGENT = "trading-bot-research/1.0 (official public archive; no credentials)"
CONTENTS = re.compile(r"<Contents>(.*?)</Contents>", re.DOTALL)
KEY = re.compile(r"<Key>([^<]+)</Key>")
SIZE = re.compile(r"<Size>(\d+)</Size>")
PREFIX_TAG = re.compile(r"<Prefix>([^<]+)</Prefix>")
NEXT_MARKER = re.compile(r"<NextMarker>([^<]+)</NextMarker>")
OBJECT_NAME = re.compile(r"([A-Z0-9]+)-1h-(\d{4}-\d{2})\.zip$")


def _fetch(url: str, *, attempts: int = 6) -> bytes:
    """Read one public object with bounded deterministic retries and no credentials."""
    last: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=120) as handle:
                return handle.read()
        except Exception as error:  # transient archive/network failure; bounded retry
            last = error
            time.sleep(min(2.0 * (attempt + 1), 10.0))
    raise RuntimeError(f"official archive unavailable: {url}") from last


def _list(prefix: str, *, delimiter: bool) -> list[str]:
    collected: list[str] = []
    marker = ""
    while True:
        url = f"{ARCHIVE_LISTING_BASE}?prefix={urllib.parse.quote(prefix)}"
        if delimiter:
            url += "&delimiter=/"
        if marker:
            url += f"&marker={urllib.parse.quote(marker)}"
        body = _fetch(url).decode("utf-8")
        if delimiter:
            collected.extend(item for item in PREFIX_TAG.findall(body) if item != prefix)
        else:
            collected.extend(CONTENTS.findall(body))
        if "<IsTruncated>true</IsTruncated>" not in body:
            return collected
        found = NEXT_MARKER.search(body)
        if found:
            marker = found.group(1)
        elif delimiter and collected:
            marker = collected[-1]
        else:
            last_key = KEY.search(collected[-1]) if collected else None
            if not last_key:
                return collected
            marker = last_key.group(1)


def archive_symbols() -> list[str]:
    """Every spot symbol that has a monthly kline archive directory, delisted included."""
    prefix = f"{ARCHIVE_PREFIX}/"
    return sorted({item[len(prefix) :].strip("/") for item in _list(prefix, delimiter=True)})


def symbol_objects(symbol: str) -> list[ArchiveObject]:
    """Monthly 1h archive objects for one symbol, restricted to the development window."""
    prefix = f"{ARCHIVE_PREFIX}/{symbol}/{KLINE_INTERVAL}/"
    objects: list[ArchiveObject] = []
    for block in _list(prefix, delimiter=False):
        key_match, size_match = KEY.search(block), SIZE.search(block)
        if not key_match or not size_match:
            continue
        key = key_match.group(1)
        named = OBJECT_NAME.search(key)
        if not named or named.group(1) != symbol:
            continue
        month = named.group(2)
        if not month_in_development(month):
            continue
        objects.append(
            ArchiveObject(
                symbol=symbol,
                month=month,
                key=key,
                url=monthly_object_url(symbol, month),
                size_bytes=int(size_match.group(1)),
            )
        )
    return sorted(objects, key=lambda item: item.month)


def build_inventory(*, workers: int = 8, symbols: list[str] | None = None) -> dict[str, Any]:
    """Enumerate candidate symbols and their in-window monthly objects without downloading."""
    every = symbols if symbols is not None else archive_symbols()
    usdt = [symbol for symbol in every if symbol.endswith(QUOTE_ASSET) and symbol != QUOTE_ASSET]
    excluded = sorted(symbol for symbol in usdt if is_leveraged_token(symbol))
    candidates = sorted(symbol for symbol in usdt if is_candidate_symbol(symbol))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        listings = list(pool.map(symbol_objects, candidates))
    records = []
    for symbol, objects in zip(candidates, listings, strict=True):
        if not objects:
            continue
        records.append(
            {
                "symbol": symbol,
                "quote_asset": QUOTE_ASSET,
                "months": [item.month for item in objects],
                "month_count": len(objects),
                "first_month": objects[0].month,
                "last_month": objects[-1].month,
                "compressed_bytes": sum(item.size_bytes for item in objects),
                "availability_status": "ARCHIVE_EVIDENCE_IN_DEVELOPMENT_WINDOW",
            }
        )
    records.sort(key=lambda item: str(item["symbol"]))
    compressed = sum(int(str(item["compressed_bytes"])) for item in records)
    months = sum(int(str(item["month_count"])) for item in records)
    return {
        "inventory_id": "BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1",
        "source": {
            "provider": "Binance",
            "archive_base": ARCHIVE_LISTING_BASE,
            "prefix": ARCHIVE_PREFIX,
            "interval": KLINE_INTERVAL,
            "market_type": "spot",
            "credentials_used": False,
        },
        "universe_derivation": "HISTORICAL_ARCHIVE_EVIDENCE_NOT_CURRENT_EXCHANGE_INFO",
        "archive_symbol_count": len(every),
        "usdt_quoted_count": len(usdt),
        "leveraged_token_excluded": excluded,
        "leveraged_token_excluded_count": len(excluded),
        "candidate_symbol_count": len(candidates),
        "candidate_with_development_archive_count": len(records),
        "monthly_object_count": int(months),
        "compressed_bytes": int(compressed),
        "symbols": records,
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }


KLINE_COLUMNS = 12


def parse_monthly_csv(payload: bytes, symbol: str, month: str) -> list[list[str]]:
    """Decode one official monthly 1h zip into integer-microsecond OHLCV rows."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"unexpected archive layout for {symbol} {month}")
        text = archive.read(names[0]).decode("utf-8")
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.split(",")
        if len(fields) < KLINE_COLUMNS:
            raise ValueError(f"malformed kline row for {symbol} {month}")
        if fields[0].strip().lower().startswith("open_time"):
            continue  # newer partitions carry a header line
        rows.append(fields)
    return rows


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def download_month(root: Path, symbol: str, month: str) -> dict[str, Any]:
    """Fetch one monthly object, preserve it verbatim, and record its source metadata."""
    url = monthly_object_url(symbol, month)
    directory = root / RAW_ROOT / symbol
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{symbol}-{KLINE_INTERVAL}-{month}.zip"
    payload = path.read_bytes() if path.is_file() else _fetch(url)
    if not path.is_file():
        path.write_bytes(payload)
    rows = parse_monthly_csv(payload, symbol, month)
    opens = [int(row[0]) for row in rows]
    return {
        "symbol": symbol,
        "month": month,
        "url": url,
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": sha256_bytes(payload),
        "rows": len(rows),
        "first_open_us": min(opens) if opens else None,
        "last_open_us": max(opens) if opens else None,
        "quote_asset": QUOTE_ASSET,
        "availability_status": "DOWNLOADED",
    }


def scale_open_time(value: int) -> int:
    """Binance switched kline timestamps from milliseconds to microseconds in 2025 files."""
    return value * 1000 if value < 10_000_000_000_000 else value


def within_development(open_us: int) -> bool:
    return open_us <= DEVELOPMENT_END_US


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
