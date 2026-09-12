"""Build the versioned order-flow feature substrate and reconcile it against the oracle.

Canonical data is read, never written. The build refuses to run unless the taker-field
integrity audit already passed, and refuses to publish unless the independent oracle
reconciles bit-for-bit.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.order_flow import (
    AGGREGATION,
    BALANCE,
    DATASET_ID,
    FEATURE_VERSION,
    FILES,
    MANIFEST_PATH,
    SOURCE_MANIFEST_PATH,
    build_substrate,
    content_hash,
    substrate_summary,
    to_table,
)
from app.research.order_flow_oracle import reconcile

INTEGRITY_ARTIFACT = "reports/validation/WP-007-ORDER-FLOW-INTEGRITY.json"
RECONCILIATION_ARTIFACT = "reports/validation/WP-007-ORDER-FLOW-RECONCILIATION.json"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def instant(value: int) -> str:
    return datetime.fromtimestamp(value / 1_000_000, UTC).isoformat().replace("+00:00", "Z")


def main() -> None:
    integrity = json.loads((ROOT / INTEGRITY_ARTIFACT).read_text(encoding="utf-8"))
    if integrity["status"] != "PASS":
        raise SystemExit("taker-field integrity audit did not pass; substrate build is blocked")
    source = json.loads((ROOT / SOURCE_MANIFEST_PATH).read_text(encoding="utf-8"))

    buckets = build_substrate(ROOT)
    for timeframe, relative in FILES.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(to_table(buckets[timeframe]), path, compression="zstd")

    summary = substrate_summary(buckets)
    hourly = buckets["1h"]
    manifest: dict[str, Any] = {
        "manifest_id": DATASET_ID,
        "dataset_version": 1,
        "schema_version": 1,
        "feature_version": FEATURE_VERSION,
        "contract": "docs/contracts/ORDER_FLOW_FEATURES_V1.md",
        "symbol": "BTCUSDT",
        "market_type": "spot",
        "derived_from": {
            "manifest_id": source["manifest_id"],
            "content_hash": source["content_hash"]["value"],
            "canonical_path": source["files"]["canonical"]["path"],
            "canonical_sha256": source["files"]["canonical"]["sha256"],
        },
        "integrity_audit": {
            "path": INTEGRITY_ARTIFACT,
            "status": integrity["status"],
            "artifact_sha256": integrity["artifact_sha256"],
        },
        "aggregation": AGGREGATION,
        "balance_point": BALANCE,
        "coverage": {
            "start": instant(hourly[0].open_us),
            "end": instant(hourly[-1].open_us),
        },
        "row_counts": {timeframe: item["buckets"] for timeframe, item in summary.items()},
        "eligible_counts": {timeframe: item["eligible"] for timeframe, item in summary.items()},
        "integrity": {
            timeframe: {
                "incomplete": item["buckets"] - item["complete"],
                "quarantined": item["quarantined"],
                "null_share": item["null_share"],
                "buy_dominant_eligible": item["buy_dominant_eligible"],
                "fills_or_repairs": 0,
            }
            for timeframe, item in summary.items()
        },
        "files": {
            timeframe: {"path": relative, "sha256": file_hash(ROOT / relative)}
            for timeframe, relative in FILES.items()
        },
        "content_hash": {
            "algorithm": "sha256-canonical-bucket-records-v1",
            "value": content_hash(buckets),
        },
        "canonical_data_modified": False,
    }
    (ROOT / MANIFEST_PATH).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    report = reconcile(ROOT, from_disk=True)
    payload = {
        **report,
        "substrate_manifest_id": DATASET_ID,
        "substrate_content_hash": manifest["content_hash"]["value"],
        "recorded_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    (ROOT / RECONCILIATION_ARTIFACT).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        f"Order-flow substrate {DATASET_ID}: "
        f"{manifest['row_counts']['1h']} 1h buckets ({manifest['eligible_counts']['1h']} eligible), "
        f"{manifest['row_counts']['4h']} 4h buckets ({manifest['eligible_counts']['4h']} eligible); "
        f"oracle reconciliation {report['status']}."
    )
    if report["status"] != "PASS":
        raise SystemExit("independent oracle reconciliation failed; no market result may run")


if __name__ == "__main__":
    main()
