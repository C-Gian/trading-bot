"""Pin the current Binance USD-M `exchangeInfo` BTCUSDT contract filters (credential-free).

Retrieves the primary-source public endpoint once, stores the full raw response under the
git-ignored raw data tree, and writes a small versioned manifest with the retrieval UTC time, the
raw SHA-256, the verbatim BTCUSDT symbol object and the normalized filters. Tick/step are taken
from the filters only, never from precision fields. If retrieval fails the manifest records
BLOCKED; no remembered value is ever written.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.g2.sources import (
    EXCHANGE_INFO_ENDPOINT,
    EXCHANGE_INFO_MANIFEST,
    normalized_filters,
    symbol_object_sha256,
)

RAW_DIR = "data/raw/binance/exchangeinfo"


def main() -> None:
    retrieved = datetime.now(UTC)
    record: dict = {
        "manifest_id": "BTCUSDT-USDM-EXCHANGEINFO-SNAPSHOT-V1",
        "version": 1,
        "endpoint": EXCHANGE_INFO_ENDPOINT,
        "source": "BINANCE_USDM_FUTURES_PUBLIC_REST_EXCHANGE_INFO",
        "credentials_used": False,
        "retrieval_utc": retrieved.isoformat(timespec="microseconds"),
        "symbol": "BTCUSDT",
    }
    try:
        with urllib.request.urlopen(EXCHANGE_INFO_ENDPOINT, timeout=60) as response:
            raw = response.read()
            record["http_status"] = response.status
    except Exception as exc:  # primary source unavailable: BLOCKED, never remembered values
        record.update({"status": "BLOCKED_PRIMARY_SOURCE_UNAVAILABLE", "error": repr(exc)})
    else:
        payload = json.loads(raw)
        symbol = next(s for s in payload["symbols"] if s["symbol"] == "BTCUSDT")
        raw_name = f"exchangeInfo-{retrieved:%Y%m%dT%H%M%SZ}.json.gz"
        (ROOT / RAW_DIR).mkdir(parents=True, exist_ok=True)
        (ROOT / RAW_DIR / raw_name).write_bytes(gzip.compress(raw, mtime=0))
        record.update(
            {
                "status": "PINNED",
                "server_time_ms": payload.get("serverTime"),
                "raw_snapshot_sha256": hashlib.sha256(raw).hexdigest(),
                "raw_snapshot_bytes": len(raw),
                "raw_snapshot_local_path": f"{RAW_DIR}/{raw_name}",
                "symbol_object": symbol,
                "symbol_object_sha256": symbol_object_sha256(symbol),
                "normalized": normalized_filters(symbol),
                "precision_fields_used_for_filters": False,
            }
        )
    path = ROOT / EXCHANGE_INFO_MANIFEST
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(record["status"], json.dumps(record.get("normalized"), sort_keys=True))


if __name__ == "__main__":
    main()
