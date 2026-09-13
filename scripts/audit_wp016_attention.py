"""Independent raw/canonical/as-of audit for WP-016 attention; no market results."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.wikimedia import (
    ACCESS,
    AGENT,
    ARTICLE,
    FEATURE,
    GRANULARITY,
    MANIFEST_PATH,
    PROJECT,
    AttentionContextSource,
    WikimediaDataError,
)

REPORT_PATH = "reports/validation/WP-016-WIKIMEDIA-ATTENTION-AUDIT.json"
DAY_US = 86_400_000_000
HOUR_US = 3_600_000_000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_day(value: str) -> int:
    return int(datetime.strptime(value, "%Y%m%d00").replace(tzinfo=UTC).timestamp() * 1_000_000)


def main() -> int:
    manifest = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    observations: list[int] = []
    pageviews: list[int] = []
    raw_hashes_ok = True
    selectors_ok = True
    for request in manifest["raw_requests"]:
        path = ROOT / request["path"]
        raw_hashes_ok &= sha256(path) == request["sha256"]
        document = json.loads(path.read_text(encoding="utf-8"))
        for item in document["items"]:
            selectors_ok &= (
                item["project"],
                item["article"],
                item["access"],
                item["agent"],
                item["granularity"],
            ) == (PROJECT, ARTICLE, ACCESS, AGENT, GRANULARITY)
            observations.append(parse_day(item["timestamp"]))
            pageviews.append(int(item["views"]))
    canonical_path = ROOT / manifest["canonical"]["path"]
    table = pq.read_table(canonical_path)
    canonical_observations = [
        int(value) for value in table["observation_date"].cast(pa.int64()).to_pylist()
    ]
    canonical_availability = [
        int(value) for value in table["availability_time"].cast(pa.int64()).to_pylist()
    ]
    canonical_views = [int(value) for value in table["pageviews"].to_pylist()]
    chronology_ok = all(
        b - a == DAY_US for a, b in zip(observations, observations[1:], strict=False)
    )
    canonical_ok = (
        sha256(canonical_path) == manifest["canonical"]["file_sha256"]
        and canonical_observations == observations
        and canonical_views == pageviews
        and canonical_availability == [value + 2 * DAY_US for value in observations]
    )

    source = AttentionContextSource(observations, pageviews)
    maximum_difference = 0.0
    boundary_ok = True
    cutoff_us = int(datetime(2024, 12, 31, 23, 59, tzinfo=UTC).timestamp() * 1_000_000)
    for index in range(28, len(observations)):
        median = float(statistics.median(pageviews[index - 28 : index]))
        expected = math.log((pageviews[index] + 1.0) / (median + 1.0))
        availability = observations[index] + 2 * DAY_US
        if availability > cutoff_us:
            continue
        actual = source.at(availability)
        maximum_difference = max(maximum_difference, abs(expected - actual.shock))
        if actual.observation_us != observations[index] or actual.availability_us > availability:
            boundary_ok = False
        try:
            previous = source.at(availability - HOUR_US)
        except WikimediaDataError:
            if index != 28:
                boundary_ok = False
        else:
            if previous.observation_us >= observations[index]:
                boundary_ok = False

    checks = {
        "official_source_selectors": "PASS" if selectors_ok else "FAIL",
        "raw_response_hashes": "PASS" if raw_hashes_ok else "FAIL",
        "daily_no_duplicates_or_missing": "PASS" if chronology_ok else "FAIL",
        "canonical_exact_rebuild": "PASS" if canonical_ok else "FAIL",
        "no_post_cutoff_observation": "PASS" if max(observations) <= cutoff_us else "FAIL",
        "availability_day_end_plus_24h": "PASS" if boundary_ok else "FAIL",
        "trailing_28_excludes_current": "PASS" if maximum_difference <= 1e-15 else "FAIL",
    }
    output: dict[str, Any] = {
        "schema_version": 1,
        "work_package": "WP-016-PREPARATION",
        "status": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
        "market_results_observed": False,
        "source": "OFFICIAL_WIKIMEDIA_REST_PAGEVIEWS_API_ONLY",
        "selectors": {
            "project": PROJECT,
            "article": ARTICLE,
            "access": ACCESS,
            "agent": AGENT,
            "granularity": GRANULARITY,
        },
        "feature": FEATURE,
        "records_rebuilt": len(observations),
        "first_observation": datetime.fromtimestamp(observations[0] / 1_000_000, UTC)
        .date()
        .isoformat(),
        "last_observation": datetime.fromtimestamp(observations[-1] / 1_000_000, UTC)
        .date()
        .isoformat(),
        "duplicates": len(observations) - len(set(observations)),
        "missing_days": sum(
            (b - a) // DAY_US - 1 for a, b in zip(observations, observations[1:], strict=False)
        ),
        "post_cutoff_rows": sum(value > cutoff_us for value in observations),
        "maximum_independent_feature_difference": maximum_difference,
        "complete_validation_folds": [2020, 2021, 2022, 2023, 2024],
        "checks": checks,
        "canonical_sha256": sha256(canonical_path),
        "manifest_sha256": sha256(ROOT / MANIFEST_PATH),
    }
    path = ROOT / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
