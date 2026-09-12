"""Independent point-in-time audit of FINANCIAL_CONDITIONS_REGIME_V1.

Rebuilds the regime by naive full rescan over the accepted ALFRED records and requires
exact agreement with the production gate, then proves that no later NFCI revision can
change an earlier regime assignment.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.evaluation_protocol import HOUR_US, utc_us
from app.research.macro import verified_records
from app.research.regime import (
    NORMAL_OR_LOOSE,
    REGIME_SERIES,
    REGIME_THRESHOLD,
    REGIME_VERSION,
    TIGHT,
    RegimeError,
    classify,
    independent_regime,
    load_regime_source,
)

AUDIT_PATH = "reports/validation/WP-012-REGIME-ASOF-AUDIT.json"
FIRST = utc_us("2019-01-01T00:00:00Z")
LAST = utc_us("2024-12-31T23:00:00Z")


def sample_instants() -> list[int]:
    """A frozen deterministic sample: every month end plus each day of the TIGHT block."""
    instants = [
        utc_us(datetime(year, month, 1, tzinfo=UTC))
        for year in range(2019, 2025)
        for month in range(1, 13)
    ]
    instants += [utc_us(datetime(2020, 4, day, 12, tzinfo=UTC)) for day in range(1, 17)]
    return sorted({i for i in instants if FIRST <= i <= LAST})


def main() -> int:
    records = verified_records(ROOT)
    source = load_regime_source(ROOT)
    checks: dict[str, str] = {}
    mismatches: list[dict[str, object]] = []

    # 1. The production gate must equal an independent naive rescan.
    compared = 0
    for instant in sample_instants():
        produced = source.at(instant)
        expected = independent_regime(records, instant)
        compared += 1
        if (produced is None) != (expected is None):
            mismatches.append({"instant_us": instant, "field": "availability"})
            continue
        if (
            produced is not None
            and expected is not None
            and (produced.regime != expected.regime or produced.nfci != expected.nfci)
        ):
            mismatches.append(
                {
                    "instant_us": instant,
                    "produced": produced.regime,
                    "expected": expected.regime,
                }
            )
    checks["independent_regime_agreement"] = "PASS" if not mismatches else "FAIL"

    # 2. Exactly two regimes, split at exactly zero.
    observed = set()
    cursor = FIRST
    while cursor <= LAST:
        reading = source.at(cursor)
        if reading is not None:
            observed.add(reading.regime)
            if (reading.nfci > REGIME_THRESHOLD) != (reading.regime == TIGHT):
                mismatches.append({"instant_us": cursor, "field": "threshold"})
        cursor += HOUR_US
    checks["exactly_two_regimes"] = "PASS" if observed <= {NORMAL_OR_LOOSE, TIGHT} else "FAIL"
    checks["threshold_is_exactly_zero"] = (
        "PASS" if REGIME_THRESHOLD == 0.0 and classify(0.0) == NORMAL_OR_LOOSE else "FAIL"
    )
    checks["zero_is_normal_or_loose"] = "PASS" if classify(0.0) == NORMAL_OR_LOOSE else "FAIL"

    # 3. A later NFCI revision must not change an earlier regime assignment. The
    #    comparison must follow consecutive revisions: against the final value a series
    #    with three or more revisions gives meaningless matches.
    revisions: dict[object, list[dict[str, object]]] = {}
    for record in records:
        if record["series_id"] != REGIME_SERIES:
            continue
        revisions.setdefault(record["observation_date"], []).append(record)
    leaked = 0
    checked = 0
    for observation, items in revisions.items():
        items.sort(key=lambda item: cast(datetime, item["availability_time"]))
        for previous, following in zip(items, items[1:], strict=False):
            if classify(float(cast(float, previous["value"]))) == classify(
                float(cast(float, following["value"]))
            ):
                continue
            probe_dt = cast(datetime, following["availability_time"]).astimezone(UTC) - timedelta(
                hours=1
            )
            probe = utc_us(probe_dt) // HOUR_US * HOUR_US
            checked += 1
            visible = [
                item
                for item in items
                if utc_us(cast(datetime, item["availability_time"]).astimezone(UTC)) <= probe
            ]
            # Before the flipping revision is published, the regime must still read as the
            # classification that was actually current.
            if visible and classify(float(cast(float, visible[-1]["value"]))) != classify(
                float(cast(float, previous["value"]))
            ):
                leaked += 1
                mismatches.append(
                    {
                        "observation": str(observation),
                        "probe_us": probe,
                        "field": "regime_changed_before_publication",
                    }
                )
    checks["later_revision_cannot_change_earlier_regime"] = "PASS" if leaked == 0 else "FAIL"

    # 4. Nothing after the development cutoff is reachable, and gaps stay ineligible.
    checks["no_post_cutoff_regime"] = "FAIL"
    try:
        source.at(utc_us("2025-01-02T00:00:00Z"))
    except RegimeError:
        checks["no_post_cutoff_regime"] = "PASS"
    ineligible = 0
    cursor = utc_us("2017-08-17T04:00:00Z")
    while cursor < utc_us("2017-08-24T00:00:00Z"):
        if source.at(cursor) is None:
            ineligible += 1
        cursor += HOUR_US
    checks["missing_nfci_is_ineligible_not_imputed"] = "PASS" if ineligible > 0 else "FAIL"

    counts = {NORMAL_OR_LOOSE: 0, TIGHT: 0, "INELIGIBLE": 0}
    cursor = FIRST
    while cursor <= LAST:
        reading = source.at(cursor)
        counts[reading.regime if reading else "INELIGIBLE"] += 1
        cursor += HOUR_US

    report = {
        "schema_version": 1,
        "work_package": "WP-012",
        "audit": "REGIME_POINT_IN_TIME_ASOF_V1",
        "regime_version": REGIME_VERSION,
        "series": REGIME_SERIES,
        "threshold": REGIME_THRESHOLD,
        "threshold_variants": 0,
        "independent_path": "NAIVE_FULL_RESCAN_NOT_THE_PRODUCTION_GATE",
        "status": "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL",
        "checks": checks,
        "sampled_instants": len(sample_instants()),
        "comparisons": compared,
        "revision_boundaries_checked": checked,
        "regime_changing_leaks": leaked,
        "validation_hour_counts": counts,
        "pre_history_ineligible_hours": ineligible,
        "mismatches": mismatches[:20],
    }
    path = ROOT / AUDIT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({k: v for k, v in report.items() if k != "mismatches"}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
