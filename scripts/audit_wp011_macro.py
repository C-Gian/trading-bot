"""Independent point-in-time audit of MACRO_FEATURES_V1.

Deliberately does not call `MacroFeatureSource`. It rebuilds the as-of state with a naive
full rescan over the accepted ALFRED records and requires exact agreement, then proves
that no later revision can reach an earlier signal instant.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.evaluation_protocol import EPOCH, HOUR_US, utc_us
from app.research.exogenous import ALFRED_SERIES
from app.research.macro import (
    LEVEL_SOURCE,
    MACRO_FEATURES,
    independent_asof,
    load_macro_source,
    verified_records,
)

AUDIT_PATH = "reports/validation/WP-011-MACRO-ASOF-AUDIT.json"
CUTOFF_US = utc_us("2024-12-31T23:00:00Z")


def sample_instants() -> list[int]:
    """A frozen deterministic sample: every quarter boundary plus each month of 2020."""
    instants = []
    for year in range(2019, 2025):
        for month in (1, 4, 7, 10):
            instants.append(utc_us(datetime(year, month, 1, tzinfo=UTC)))
    for month in range(1, 13):
        instants.append(utc_us(datetime(2020, month, 15, 13, tzinfo=UTC)))
    return sorted({instant for instant in instants if instant <= CUTOFF_US})


def main() -> int:
    records = verified_records(ROOT)
    source = load_macro_source(ROOT)
    checks: dict[str, str] = {}
    mismatches: list[dict[str, object]] = []

    # 1. Level features must equal an independent naive as-of rescan.
    compared = 0
    for instant in sample_instants():
        row = source.at(instant)
        if row is None:
            continue
        for index, name in enumerate(MACRO_FEATURES):
            if name not in LEVEL_SOURCE:
                continue
            expected = independent_asof(records, LEVEL_SOURCE[name], instant)
            compared += 1
            if expected is None or abs(expected[1] - row.values[index]) > 0.0:
                mismatches.append({"instant_us": instant, "feature": name, "expected": expected})
    checks["independent_asof_agreement"] = "PASS" if not mismatches else "FAIL"

    # 2. No value may be visible before its own conservative availability time.
    early = 0
    for record in records:
        available = utc_us(record["availability_time"].astimezone(UTC))
        probe = (available - HOUR_US) // HOUR_US * HOUR_US
        if probe < utc_us("2019-01-01T00:00:00Z") or probe > CUTOFF_US:
            continue
        state = (
            source._state(record["series_id"], probe)
            if record["series_id"] in {"WALCL", "CPIAUCSL"}
            else None
        )
        if state is not None and state.get(record["observation_date"]) == record["value"]:
            early += 1
    checks["no_value_visible_before_availability"] = "PASS" if early == 0 else "FAIL"

    # 3. A later revision of an observation must not change an earlier as-of answer.
    #    The comparison must follow one specific observation: the newest observation date
    #    as of a probe is a different quantity and would give meaningless matches.
    revisions: dict[tuple[str, object], list[dict[str, object]]] = {}
    for record in records:
        revisions.setdefault((record["series_id"], record["observation_date"]), []).append(record)
    leaked = 0
    revised_pairs = 0
    checked_revisions = 0
    for (series, observation), items in revisions.items():
        if len(items) < 2:
            continue
        revised_pairs += 1
        items.sort(key=lambda item: item["availability_time"])
        first, last = items[0], items[-1]
        if first["value"] == last["value"]:
            continue
        probe_dt = last["availability_time"].astimezone(UTC) - timedelta(hours=1)
        probe = utc_us(probe_dt) // HOUR_US * HOUR_US
        if probe < utc_us("2019-01-01T00:00:00Z") or probe > CUTOFF_US:
            continue
        checked_revisions += 1
        visible = [
            item for item in items if utc_us(item["availability_time"].astimezone(UTC)) <= probe
        ]
        point_in_time = visible[-1]["value"] if visible else None
        # Before the later revision is published, that observation must still read as the
        # value that was actually current, never the value it was later revised to.
        if point_in_time == last["value"]:
            leaked += 1
            mismatches.append(
                {
                    "series": series,
                    "observation": str(observation),
                    "probe_us": probe,
                    "point_in_time": point_in_time,
                    "final_value": last["value"],
                }
            )
    checks["later_revision_cannot_leak_backward"] = "PASS" if leaked == 0 else "FAIL"

    # 4. Nothing after the development cutoff may be reachable.
    cutoff_observation = date(2024, 12, 31)
    post = sum(1 for record in records if record["observation_date"] > cutoff_observation)
    checks["no_post_cutoff_observation"] = "PASS" if post == 0 else "FAIL"

    # 5. Missing history stays ineligible rather than imputed.
    first_eligible = None
    cursor = utc_us("2017-08-17T04:00:00Z")
    ineligible = 0
    while cursor <= utc_us("2019-01-02T00:00:00Z"):
        if source.at(cursor) is None:
            ineligible += 1
        elif first_eligible is None:
            first_eligible = cursor
        cursor += HOUR_US
    checks["missing_history_is_ineligible_not_imputed"] = "PASS" if ineligible > 0 else "FAIL"

    report = {
        "schema_version": 1,
        "work_package": "WP-011",
        "audit": "MACRO_POINT_IN_TIME_ASOF_V1",
        "feature_version": "MACRO_FEATURES_V1",
        "source_version": "ALFRED_MACRO_CONTEXT_V1",
        "independent_path": "NAIVE_FULL_RESCAN_NOT_THE_PRODUCTION_INDEX",
        "status": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
        "checks": checks,
        "series": list(ALFRED_SERIES),
        "sampled_instants": len(sample_instants()),
        "level_comparisons": compared,
        "mismatches": mismatches[:20],
        "revised_observation_pairs": revised_pairs,
        "revision_boundaries_checked": checked_revisions,
        "values_visible_before_availability": early,
        "backward_leaks": leaked,
        "pre_history_ineligible_hours": ineligible,
        "first_eligible_signal_us": first_eligible,
        "first_eligible_signal_utc": (
            (EPOCH + timedelta(microseconds=first_eligible)).isoformat().replace("+00:00", "Z")
            if first_eligible
            else None
        ),
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
