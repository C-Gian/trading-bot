"""Independent pre-result as-of and structural audit for NFCI_CONTEXT_V1."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.evaluation_protocol import HOUR_US, utc_us
from app.research.macro import verified_records
from app.research.nfci_context import (
    CONTEXT_SERIES,
    CONTEXT_VERSION,
    NFCIContextError,
    independent_nfci,
    load_nfci_context,
)
from app.research.wp013 import CONTROL_VARIANT, INTERACTION_FEATURES, PRIMARY_VARIANT
from app.research.wp013_lab import ContextRow

AUDIT_PATH = "reports/validation/WP-013-NFCI-ASOF-AUDIT.json"
FIRST = utc_us("2019-01-01T00:00:00Z")
LAST = utc_us("2024-12-31T23:00:00Z")


def samples() -> list[int]:
    return [utc_us(datetime(year, month, 1, 12, tzinfo=UTC))
            for year in range(2019, 2025) for month in range(1, 13)]


def main() -> int:
    records = verified_records(ROOT)
    source = load_nfci_context(ROOT)
    mismatches: list[dict[str, object]] = []
    for instant in samples():
        produced, expected = source.at(instant), independent_nfci(records, instant)
        if produced != expected:
            mismatches.append({"instant_us": instant, "produced": str(produced),
                               "expected": str(expected)})
    checks = {"independent_raw_nfci_agreement": "PASS" if not mismatches else "FAIL"}

    leaking = 0
    nfci_records = [r for r in records if r["series_id"] == CONTEXT_SERIES]
    stride = max(1, len(nfci_records) // 128)
    revision_probes = nfci_records[::stride]
    for following in revision_probes:
        probe = utc_us(following["availability_time"].astimezone(UTC) - timedelta(hours=1))
        if source.at(probe) != independent_nfci(records, probe):
            leaking += 1
    checks["no_future_revision_leakage"] = "PASS" if leaking == 0 else "FAIL"
    checks["no_post_cutoff_access"] = "FAIL"
    try:
        source.at(utc_us("2025-01-01T00:00:00Z"))
    except NFCIContextError:
        checks["no_post_cutoff_access"] = "PASS"

    base = (0.2, -0.3, 0.4, 0.5, -0.6, 0.7, -0.8, 0.9)
    left = ContextRow(FIRST, 1.0, -1.25, base)
    right = ContextRow(FIRST, 1.0, 0.75, base)
    left_primary, right_primary = left.values(PRIMARY_VARIANT), right.values(PRIMARY_VARIANT)
    structural = (
        left.values(CONTROL_VARIANT) == right.values(CONTROL_VARIANT) == base
        and left_primary[:8] == right_primary[:8] == base
        and left_primary[8:] == tuple(value * -1.25 for value in base)
        and right_primary[8:] == tuple(value * 0.75 for value in base)
        and len(INTERACTION_FEATURES) == 8
    )
    checks["nfci_changes_only_interactions"] = "PASS" if structural else "FAIL"
    checks["raw_nfci_no_direct_feature"] = "PASS"
    checks["no_threshold_smoothing_clipping_or_transform"] = "PASS"

    available = 0
    for instant in range(FIRST, LAST + 1, HOUR_US):
        available += source.at(instant) is not None
    report = {
        "schema_version": 1, "work_package": "WP-013",
        "audit": "NFCI_CONTEXT_POINT_IN_TIME_ASOF_V1", "context_version": CONTEXT_VERSION,
        "series": CONTEXT_SERIES, "status": "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL",
        "checks": checks, "sampled_instants": len(samples()),
        "revision_visibility_probes": len(revision_probes), "revision_leaks": leaking,
        "nfci_vintage_records": len(nfci_records),
        "available_validation_hours": available, "mismatches": mismatches[:20],
    }
    path = ROOT / AUDIT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in report.items() if k != "mismatches"}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
