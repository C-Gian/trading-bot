"""Run the WP-007 canonical taker-field integrity audit and freeze its artifact.

Reads only the accepted development dataset and the immutable raw Binance archives.
Writes no canonical data and repairs no value.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.order_flow_audit import canonical_hash, order_flow_integrity

ARTIFACT = "reports/validation/WP-007-ORDER-FLOW-INTEGRITY.json"


def main() -> None:
    report = order_flow_integrity()
    payload = {
        **report,
        "recorded_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    payload["artifact_sha256"] = canonical_hash(
        {key: value for key, value in payload.items() if key != "recorded_at_utc"}
    )
    path = ROOT / ARTIFACT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    audit = report["canonical_audit"]
    provenance = report["source_provenance_sample"]
    print(
        f"Order-flow integrity: {report['status']}; "
        f"{audit['dataset']['rows']} canonical rows audited, "
        f"{report['material_violations']} material violations, "
        f"{provenance['total_rows_compared']} raw rows re-verified."
    )
    if report["status"] != "PASS":
        raise SystemExit("order-flow integrity audit failed; no market experiment may run")


if __name__ == "__main__":
    main()
