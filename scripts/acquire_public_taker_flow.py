"""Acquire official Binance spot + USD-M BTCUSDT 1m monthly klines, 2020-2024, fail closed.

Source class: the official Binance public data archive only, credential-free, development
window only (`research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md`).
Every monthly object is verified against the archive's own `.CHECKSUM` file before it is
stored, and its source path, sizes and official checksum are pinned in the immutable manifest
`data/manifests/BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1.json`.

Re-running is safe: an already-stored object is re-verified against its stored official
checksum instead of being downloaded again. Once the manifest exists it is never rewritten;
a re-run only re-verifies every pinned object against it.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.taker_flow_source import (
    MANIFEST_PATH,
    MARKETS,
    TakerFlowSourceError,
    archive_url,
    build_manifest,
    load_manifest,
    manifest_entry,
    months,
    parse_checksum_file,
    raw_path,
    verified_object,
    verify_against_checksum,
)

ATTEMPTS = 5


def get(client: httpx.Client, url: str) -> bytes:
    for attempt in range(ATTEMPTS):
        try:
            response = client.get(url, timeout=180.0)
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError:
            raise
        except httpx.HTTPError:
            if attempt == ATTEMPTS - 1:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def acquire_object(client: httpx.Client, market: str, year: int, month: int) -> dict[str, Any]:
    """Download (or re-verify) one monthly object against its official checksum."""
    path = ROOT / raw_path(market, year, month)
    checksum_path = path.with_name(path.name + ".CHECKSUM")
    stamp_path = path.with_name(path.name + ".retrieved")
    if path.is_file() and checksum_path.is_file() and stamp_path.is_file():
        checksum_text = checksum_path.read_text(encoding="utf-8")
        content = path.read_bytes()
        retrieved = stamp_path.read_text(encoding="utf-8").strip()
    else:
        url = archive_url(market, year, month)
        content = get(client, url)
        checksum_text = get(client, f"{url}.CHECKSUM").decode("utf-8")
        retrieved = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    official = parse_checksum_file(checksum_text, path.name)
    verify_against_checksum(content, official, path.name)
    entry = manifest_entry(market, year, month, content, official, retrieved)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_bytes(content)
        checksum_path.write_text(checksum_text, encoding="utf-8", newline="\n")
        stamp_path.write_text(retrieved + "\n", encoding="utf-8", newline="\n")
    return entry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    options = parser.parse_args()

    manifest_file = ROOT / MANIFEST_PATH
    if manifest_file.is_file():
        manifest = load_manifest(ROOT)
        for entry in manifest["archives"]:
            verified_object(ROOT, entry)
        print(
            f"public taker-flow source already pinned: objects={manifest['objects']} "
            f"re-verified={manifest['objects']} manifest={MANIFEST_PATH}"
        )
        return

    jobs = [(market, year, month) for market in MARKETS for year, month in months()]
    with (
        httpx.Client(follow_redirects=True) as client,
        ThreadPoolExecutor(max_workers=options.workers) as pool,
    ):
        entries = list(pool.map(lambda job: acquire_object(client, *job), jobs))
    manifest = build_manifest(entries)
    if manifest["official_checksums_verified"] != len(jobs):
        raise TakerFlowSourceError("not every object was verified against its official checksum")
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    size = sum(entry["archive_size_bytes"] for entry in entries)
    print(
        f"public taker-flow source acquired: objects={manifest['objects']} "
        f"bytes={size} manifest={MANIFEST_PATH}"
    )


if __name__ == "__main__":
    main()
