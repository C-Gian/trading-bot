"""Stage the cross-sectional feasibility substrate from the official Binance archive.

Stages are explicit and safe-stoppable:

    inventory     enumerate candidate symbols and monthly objects, project storage
    equivalence   prove BTCUSDT direct-1h reproduces the frozen ALIGNED semantics
    acquire       download and preserve every in-window monthly object
    substrate     build the consolidated on-grid hourly parquet and its manifest

No stage evaluates the true cross-sectional ALIGNED effect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.cross_section import (
    CROSS_SECTION_ROLE,
    PRODUCT_UNIVERSE,
    assert_no_real_effect_leakage,
)
from app.research.cross_section_archive import (
    INVENTORY_PATH,
    build_inventory,
    download_month,
    write_json,
)
from app.research.cross_section_lab import (
    BTC_EQUIVALENCE_PATH,
    SUBSTRATE_PATH,
    btc_equivalence_report,
    build_substrate,
)

INVENTORY_REPORT = "reports/cross_section/CROSS-SECTION-ARCHIVE-INVENTORY-V1.json"
EQUIVALENCE_MONTHS = [
    f"{year:04d}-{month:02d}" for year in range(2017, 2025) for month in range(1, 13)
]
EQUIVALENCE_MONTHS = [month for month in EQUIVALENCE_MONTHS if "2017-08" <= month <= "2024-12"]
BYTES_PER_HOURLY_ROW = 100
BYTES_PER_PARQUET_ROW = 12
DOWNLOAD_BYTES_PER_SECOND = 2_000_000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _projection(inventory: dict[str, Any]) -> dict[str, Any]:
    months = inventory["monthly_object_count"]
    compressed = inventory["compressed_bytes"]
    rows = months * 730
    uncompressed = rows * BYTES_PER_HOURLY_ROW
    return {
        "candidate_symbol_count": inventory["candidate_symbol_count"],
        "symbols_with_development_archive": inventory["candidate_with_development_archive_count"],
        "monthly_object_count": months,
        "compressed_download_bytes": compressed,
        "compressed_download_gib": round(compressed / 1024**3, 4),
        "projected_hourly_rows": rows,
        "projected_uncompressed_bytes": uncompressed,
        "projected_uncompressed_gib": round(uncompressed / 1024**3, 4),
        "projected_parquet_bytes": rows * BYTES_PER_PARQUET_ROW,
        "projected_parquet_gib": round(rows * BYTES_PER_PARQUET_ROW / 1024**3, 4),
        "projected_download_seconds": round(compressed / DOWNLOAD_BYTES_PER_SECOND, 1),
        "substrate_resolution": "1H_RESEARCH_SUBSTRATE_NOT_1M_MULTI_ASSET_PRODUCT",
        "one_minute_history_downloaded": False,
        "DATA_FEASIBILITY_STATUS": "PASS" if compressed < 8 * 1024**3 else "REDESIGN_REQUIRED",
    }


def stage_inventory() -> int:
    inventory = build_inventory(workers=12)
    assert_no_real_effect_leakage(inventory)
    write_json(ROOT / INVENTORY_PATH, inventory)
    report = {
        "report_id": "CROSS-SECTION-ARCHIVE-INVENTORY-V1",
        "product_universe": PRODUCT_UNIVERSE,
        "cross_section_role": CROSS_SECTION_ROLE,
        "inventory_manifest": INVENTORY_PATH,
        "archive_symbol_count": inventory["archive_symbol_count"],
        "usdt_quoted_count": inventory["usdt_quoted_count"],
        "leveraged_token_excluded_count": inventory["leveraged_token_excluded_count"],
        "leveraged_token_excluded": inventory["leveraged_token_excluded"],
        "projection": _projection(inventory),
        "ACTUAL_CROSS_SECTION_EFFECT_OBSERVED": False,
    }
    write_json(ROOT / INVENTORY_REPORT, report)
    print(json.dumps(report["projection"], indent=2, sort_keys=True))
    return 0


def stage_equivalence() -> int:
    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(lambda month: download_month(ROOT, "BTCUSDT", month), EQUIVALENCE_MONTHS))
    report = btc_equivalence_report(ROOT)
    assert_no_real_effect_leakage(report)
    write_json(ROOT / BTC_EQUIVALENCE_PATH, report)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "source_discrepancies"},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["DATA_SOURCE_STATUS"] == "PASS" else 1


def stage_acquire(workers: int) -> int:
    inventory = json.loads((ROOT / INVENTORY_PATH).read_text(encoding="utf-8"))
    jobs = [
        (record["symbol"], month) for record in inventory["symbols"] for month in record["months"]
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(lambda job: download_month(ROOT, job[0], job[1]), jobs))
    objects = sorted(records, key=lambda item: (item["symbol"], item["month"]))
    inventory["objects"] = objects
    inventory["object_count"] = len(objects)
    inventory["object_rows"] = sum(item["rows"] for item in objects)
    inventory["objects_sha256"] = hashlib.sha256(
        "\n".join(f"{item['path']}:{item['sha256']}" for item in objects).encode()
    ).hexdigest()
    write_json(ROOT / INVENTORY_PATH, inventory)
    print(json.dumps({"objects": len(objects), "rows": inventory["object_rows"]}, sort_keys=True))
    return 0


def stage_substrate() -> int:
    inventory = json.loads((ROOT / INVENTORY_PATH).read_text(encoding="utf-8"))
    symbols = [record["symbol"] for record in inventory["symbols"]]
    summary = build_substrate(ROOT, symbols)
    path = ROOT / SUBSTRATE_PATH
    inventory["substrate"] = {
        "path": SUBSTRATE_PATH,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "hourly_rows": summary["hourly_rows"],
        "symbols_with_rows": summary["symbols_with_rows"],
    }
    inventory["substrate_symbols"] = summary["symbols"]
    write_json(ROOT / INVENTORY_PATH, inventory)
    print(json.dumps(inventory["substrate"], indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("inventory", "equivalence", "acquire", "substrate"))
    parser.add_argument("--workers", type=int, default=12)
    options = parser.parse_args()
    if options.stage == "inventory":
        return stage_inventory()
    if options.stage == "equivalence":
        return stage_equivalence()
    if options.stage == "acquire":
        return stage_acquire(options.workers)
    return stage_substrate()


if __name__ == "__main__":
    raise SystemExit(main())
