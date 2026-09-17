"""Acquire official Binance USD-M historical open interest for BTCUSDT, fail closed.

Source class: the official Binance public data archive only, credential-free, development
interval only. Every daily object is verified against the archive's own `.CHECKSUM` file
before it is parsed, and any day whose checksum, schema or symbol does not match aborts the
acquisition rather than entering the canonical artifact.

Only `create_time` and `sum_open_interest` are admitted. `sum_open_interest_value` and every
ratio column are read past and discarded, so the family stays interpretable as positioning
quantity and cannot embed BTC price.

No third-party vendor, scrape, mirror, REST snapshot history or backfill is used or accepted.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.open_interest_source import (
    ADMITTED_COLUMNS,
    ARCHIVE_HOST,
    ARCHIVE_PREFIX,
    CADENCE_SECONDS,
    CANONICAL_PATH,
    DEVELOPMENT_CEILING,
    DEVELOPMENT_CEILING_SECONDS,
    FORBIDDEN_COLUMNS,
    MANIFEST_PATH,
    RAW_ROOT,
    RECORDS_PER_DAY,
    SOURCE_NAME,
    SOURCE_VERSION,
    SYMBOL,
    OpenInterestError,
    parse_metrics_csv,
)

LISTING_HOST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NAMESPACE = "{http://s3.amazonaws.com/doc/2006-03-01/}"
DEVELOPMENT_LAST_DAY = date(2024, 12, 31)


def archive_url(day: date) -> str:
    return f"{ARCHIVE_HOST}/{ARCHIVE_PREFIX}/{SYMBOL}-metrics-{day.isoformat()}.zip"


def list_archive_days(client: httpx.Client) -> list[date]:
    """Enumerate every daily object the official archive actually publishes, paginated."""
    days: list[date] = []
    marker: str | None = None
    while True:
        params = {"delimiter": "/", "prefix": f"{ARCHIVE_PREFIX}/"}
        if marker:
            params["marker"] = marker
        response = client.get(LISTING_HOST, params=params, timeout=90.0)
        response.raise_for_status()
        tree = ElementTree.fromstring(response.text)
        keys = [element.text or "" for element in tree.iter(f"{NAMESPACE}Key")]
        for key in keys:
            name = key.rsplit("/", 1)[-1]
            if not name.endswith(".zip"):
                continue
            stamp = name.removeprefix(f"{SYMBOL}-metrics-").removesuffix(".zip")
            days.append(date.fromisoformat(stamp))
        truncated = tree.find(f"{NAMESPACE}IsTruncated")
        if truncated is None or truncated.text != "true" or not keys:
            break
        marker = keys[-1]
    return sorted(set(days))


def fetch_day(client: httpx.Client, day: date) -> dict[str, Any]:
    """Download one daily object and its official checksum, and verify them against each other."""
    url = archive_url(day)
    payload = client.get(url, timeout=180.0)
    payload.raise_for_status()
    checksum = client.get(f"{url}.CHECKSUM", timeout=90.0)
    checksum.raise_for_status()
    official = checksum.text.split()[0].strip().lower()
    digest = hashlib.sha256(payload.content).hexdigest()
    if digest != official:
        raise OpenInterestError(f"{day}: the download does not match the official checksum")
    return {
        "day": day,
        "url": url,
        "content": payload.content,
        "sha256": digest,
        "official_checksum_sha256": official,
        "retrieval_time_utc": datetime.now(UTC).replace(microsecond=0).isoformat() + "Z",
    }


def store_raw(record: dict[str, Any]) -> None:
    directory = ROOT / RAW_ROOT
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{SYMBOL}-metrics-{record['day'].isoformat()}"
    (directory / f"{name}.zip").write_bytes(record["content"])
    (directory / f"{name}.meta.json").write_text(
        json.dumps(
            {
                "url": record["url"],
                "sha256": record["sha256"],
                "official_checksum_sha256": record["official_checksum_sha256"],
                "retrieval_time_utc": record["retrieval_time_utc"],
                "source": SOURCE_NAME,
                "credential_free": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def rows_from(record: dict[str, Any]) -> list[tuple[int, float]]:
    archive = zipfile.ZipFile(io.BytesIO(record["content"]))
    names = archive.namelist()
    expected = f"{SYMBOL}-metrics-{record['day'].isoformat()}.csv"
    if names != [expected]:
        raise OpenInterestError(f"{record['day']}: unexpected archive member {names}")
    return parse_metrics_csv(archive.read(expected).decode("utf-8"))


def build(days: list[date], records: list[dict[str, Any]]) -> dict[str, Any]:
    import pyarrow as pa
    import pyarrow.parquet as pq

    rows: list[tuple[int, float]] = []
    day_index: list[dict[str, Any]] = []
    for record in records:
        parsed = rows_from(record)
        day = record["day"]
        boundary = int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp())
        for stamped, _ in parsed:
            if not boundary <= stamped < boundary + 86_400:
                raise OpenInterestError(f"{day}: a record falls outside its own daily file")
            if stamped % CADENCE_SECONDS:
                raise OpenInterestError(f"{day}: a record is off the 5-minute grid")
        day_index.append(
            {
                "day": day.isoformat(),
                "rows": len(parsed),
                "distinct_timestamps": len({stamped for stamped, _ in parsed}),
                "sha256": record["sha256"],
                "official_checksum_sha256": record["official_checksum_sha256"],
                "complete_day": len({stamped for stamped, _ in parsed}) == RECORDS_PER_DAY,
            }
        )
        rows.extend(parsed)

    rows.sort(key=lambda item: item[0])
    # Some early daily objects emit every record twice, byte-identically. An exact repetition
    # is collapsed and counted; two different quantities at one timestamp are ambiguous and
    # fail the acquisition closed rather than letting a choice be made silently.
    collapsed: list[tuple[int, float]] = []
    exact_duplicates = 0
    conflicts: list[dict[str, Any]] = []
    for stamped, quantity in rows:
        if collapsed and collapsed[-1][0] == stamped:
            if collapsed[-1][1] == quantity:
                exact_duplicates += 1
                continue
            conflicts.append(
                {"timestamp": stamped, "kept": collapsed[-1][1], "conflicting": quantity}
            )
            continue
        collapsed.append((stamped, quantity))
    if conflicts:
        raise OpenInterestError(
            f"the official archive gave {len(conflicts)} timestamps two different quantities"
        )
    rows = collapsed
    duplicates = 0
    post_cutoff = sum(1 for stamped, _ in rows if stamped > DEVELOPMENT_CEILING_SECONDS)
    if post_cutoff:
        raise OpenInterestError("refusing to admit a post-cutoff open-interest record")
    non_positive = sum(1 for _, quantity in rows if not quantity > 0.0)

    expected_span = (rows[-1][0] - rows[0][0]) // CADENCE_SECONDS + 1
    missing_records = expected_span - len(rows)
    gaps = [
        {
            "after": datetime.fromtimestamp(earlier[0], UTC).isoformat().replace("+00:00", "Z"),
            "before": datetime.fromtimestamp(later[0], UTC).isoformat().replace("+00:00", "Z"),
            "missing_records": (later[0] - earlier[0]) // CADENCE_SECONDS - 1,
        }
        for earlier, later in zip(rows, rows[1:])
        if later[0] - earlier[0] != CADENCE_SECONDS
    ]

    path = ROOT / CANONICAL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            ADMITTED_COLUMNS[0]: pa.array([stamped for stamped, _ in rows], pa.int64()),
            ADMITTED_COLUMNS[1]: pa.array([quantity for _, quantity in rows], pa.float64()),
        }
    )
    pq.write_table(table, path, compression="zstd", compression_level=9, version="2.6")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    index_bytes = json.dumps(day_index, sort_keys=True).encode("utf-8")
    calendar = {
        (rows[0][0] // 86_400 * 86_400) + offset * 86_400 for offset in range(len(days) + 2)
    }
    del calendar
    published = {item["day"] for item in day_index}
    first_day = date.fromisoformat(day_index[0]["day"])
    last_day = date.fromisoformat(day_index[-1]["day"])
    span_days = (last_day - first_day).days + 1
    absent_days = sorted(
        (first_day + timedelta(days=offset)).isoformat()
        for offset in range(span_days)
        if (first_day + timedelta(days=offset)).isoformat() not in published
    )

    return {
        "schema_version": 1,
        "version": SOURCE_VERSION,
        "manifest_id": "BTCUSDT-USDM-OPEN-INTEREST-DEV-v1",
        "symbol": SYMBOL,
        "raw_root": RAW_ROOT,
        "traded_instrument": "BTCUSDT_SPOT",
        "contract": "docs/contracts/PREDICTIVE_OPEN_INTEREST_STRUCTURE_V1.md",
        "source": {
            "name": SOURCE_NAME,
            "class": "OFFICIAL_BINANCE_PUBLIC_DATA_ARCHIVE",
            "host": ARCHIVE_HOST,
            "prefix": ARCHIVE_PREFIX,
            "credential_free": True,
            "third_party_vendor": False,
            "rest_snapshot_history": False,
            "reconstructed_or_backfilled": False,
        },
        "archive": {
            "days": len(day_index),
            "first_day": day_index[0]["day"],
            "last_day": day_index[-1]["day"],
            "absent_days": absent_days,
            "incomplete_days": [item["day"] for item in day_index if not item["complete_day"]],
            "official_checksums_verified": len(day_index),
            "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
            "day_index": day_index,
        },
        "admitted_columns": list(ADMITTED_COLUMNS),
        "excluded_source_fields": list(FORBIDDEN_COLUMNS),
        "cadence": {
            "seconds": CADENCE_SECONDS,
            "records_per_complete_day": RECORDS_PER_DAY,
            "declared": "FIVE_MINUTE",
        },
        "records": len(rows),
        "first_record": datetime.fromtimestamp(rows[0][0], UTC).isoformat().replace("+00:00", "Z"),
        "last_record": datetime.fromtimestamp(rows[-1][0], UTC).isoformat().replace("+00:00", "Z"),
        "request_ceiling": DEVELOPMENT_CEILING,
        "integrity": {
            "duplicates": duplicates,
            "exact_duplicate_rows_collapsed": exact_duplicates,
            "conflicting_duplicate_timestamps": 0,
            "duplicate_policy": "COLLAPSE_EXACT_REPETITION_FAIL_CLOSED_ON_CONFLICT",
            "post_cutoff_records": post_cutoff,
            "non_positive_quantities": non_positive,
            "expected_records_over_span": expected_span,
            "missing_records": missing_records,
            "gap_count": len(gaps),
            "gaps": gaps,
            "strictly_increasing": True,
            "off_grid_records": 0,
        },
        "canonical": {
            "artifact_storage_version": "RESEARCH_ARTIFACT_STORAGE_V1",
            "path": CANONICAL_PATH,
            "format": "PARQUET_ZSTD",
            "file_sha256": digest,
            "rows": len(rows),
            "columns": [
                {"name": ADMITTED_COLUMNS[0], "type": "int64", "nullable": False},
                {"name": ADMITTED_COLUMNS[1], "type": "double", "nullable": False},
            ],
            "sort_key": [ADMITTED_COLUMNS[0]],
        },
    }


def rebuild_from_raw() -> list[dict[str, Any]]:
    """Re-read the stored raw objects, re-verifying each against its stored official checksum."""
    directory = ROOT / RAW_ROOT
    records: list[dict[str, Any]] = []
    for archive in sorted(directory.glob(f"{SYMBOL}-metrics-*.zip")):
        meta = json.loads(archive.with_suffix(".meta.json").read_text(encoding="utf-8"))
        content = archive.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != meta["official_checksum_sha256"]:
            raise OpenInterestError(f"{archive.name}: stored object fails its official checksum")
        stamp = archive.stem.removeprefix(f"{SYMBOL}-metrics-")
        records.append(
            {
                "day": date.fromisoformat(stamp),
                "url": meta["url"],
                "content": content,
                "sha256": digest,
                "official_checksum_sha256": meta["official_checksum_sha256"],
                "retrieval_time_utc": meta["retrieval_time_utc"],
            }
        )
    if not records:
        raise OpenInterestError("no stored raw archive object was found")
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--from-raw",
        action="store_true",
        help="rebuild from already-downloaded, already-checksum-verified raw objects",
    )
    options = parser.parse_args()

    if options.from_raw:
        records = rebuild_from_raw()
        days = [record["day"] for record in records]
        print(f"rebuilding from {len(days)} verified raw archive objects")
    else:
        with httpx.Client(follow_redirects=True) as client:
            days = [day for day in list_archive_days(client) if day <= DEVELOPMENT_LAST_DAY]
            if not days:
                raise OpenInterestError("the official archive published no admissible day")
            print(f"official archive days in the development interval: {len(days)}")
            with ThreadPoolExecutor(max_workers=options.workers) as pool:
                records = list(pool.map(lambda day: fetch_day(client, day), days))
        records.sort(key=lambda item: item["day"])
        for record in records:
            store_raw(record)

    manifest = build(days, records)
    path = ROOT / MANIFEST_PATH
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        f"open interest acquired: days={manifest['archive']['days']} "
        f"records={manifest['records']} "
        f"first={manifest['first_record']} last={manifest['last_record']} "
        f"gaps={manifest['integrity']['gap_count']} "
        f"missing={manifest['integrity']['missing_records']}"
    )


if __name__ == "__main__":
    main()
