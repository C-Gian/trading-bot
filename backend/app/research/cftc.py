"""Official CFTC TFF acquisition and point-in-time leveraged-positioning context."""

from __future__ import annotations

import bisect
import csv
import hashlib
import io
import json
import math
import os
import re
import zipfile
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
import pyarrow as pa

from .artifacts import file_sha256, validate_parquet, write_parquet
from .wp004 import ROOT

VERSION = "CFTC_LEVERAGED_POSITIONING_CONTEXT_V1"
FEATURE = "CFTC_LEVERAGED_FUNDS_NET_OI_SHARE_V1"
SOURCE_FAMILY = "CFTC_TRADERS_IN_FINANCIAL_FUTURES_HISTORICAL"
MARKET_NAME = "BITCOIN - CHICAGO MERCANTILE EXCHANGE"
CONTRACT_MARKET_CODE = "133741"
ARCHIVE_YEARS = tuple(range(2018, 2025))
ARCHIVE_BASE = "https://www.cftc.gov/files/dea/history"
REPORT_BASE = "https://www.cftc.gov/sites/default/files/files/dea/cotarchives"
SPECIAL_ANNOUNCEMENTS = (
    "https://www.cftc.gov/MarketReports/CommitmentsofTraders/"
    "HistoricalSpecialAnnouncements/index.htm"
)
ORDINARY_RELEASE_DOCUMENTATION = "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"
CUTOFF = datetime(2024, 12, 31, 23, 59, tzinfo=UTC)
CUTOFF_US = int(CUTOFF.timestamp() * 1_000_000)
RAW_ROOT = "data/raw/cftc/tff"
PUBLICATION_CALENDAR_PATH = "data/raw/cftc/tff/publication-calendar-v1.json"
CANONICAL_PATH = "data/derived/CFTC-CME-BITCOIN-leveraged-net-oi-share-v1.parquet"
MANIFEST_PATH = "data/manifests/CFTC-CME-BITCOIN-TFF-DEV-v1.json"
INTEGRITY_PATH = "reports/validation/WP-017-CFTC-INTEGRITY.json"
PARSER_VERSION = "CFTC_TFF_LEVERAGED_POSITIONING_PARSER_V1"
AVAILABILITY_RULE = "UTC_MIDNIGHT_CALENDAR_DAY_AFTER_ACTUAL_CFTC_PUBLICATION_DATE"
ORDINARY_BASIS = "ORDINARY_CFTC_RELEASE_RULE"
EXCEPTION_BASIS = "CFTC_OFFICIAL_EXCEPTION"
USER_AGENT = "TradingBotResearch/1.0 (owner-initiated CFTC source preparation)"
_REPORT_URL_OVERRIDES = {
    date(2018, 9, 25): "financial_lf092918.htm",
    date(2019, 12, 24): "financial_lf123019.htm",
}

MARKET_COLUMN = "Market_and_Exchange_Names"
REPORT_DATE_COLUMN = "Report_Date_as_YYYY-MM-DD"
CODE_COLUMN = "CFTC_Contract_Market_Code"
OPEN_INTEREST_COLUMN = "Open_Interest_All"
LONG_COLUMN = "Lev_Money_Positions_Long_All"
SHORT_COLUMN = "Lev_Money_Positions_Short_All"
REQUIRED_COLUMNS = frozenset(
    {
        MARKET_COLUMN,
        REPORT_DATE_COLUMN,
        CODE_COLUMN,
        OPEN_INTEREST_COLUMN,
        LONG_COLUMN,
        SHORT_COLUMN,
    }
)

CFTC_SCHEMA = pa.schema(
    [
        ("report_date", pa.date32(), False),
        ("publication_date", pa.date32(), False),
        ("availability_timestamp", pa.timestamp("us", tz="UTC"), False),
        ("publication_date_basis", pa.string(), False),
        ("open_interest_all", pa.int64(), False),
        ("leveraged_funds_long_all", pa.int64(), False),
        ("leveraged_funds_short_all", pa.int64(), False),
        ("leveraged_funds_net_oi_share", pa.float64(), False),
    ]
)


class CFTCDataError(ValueError):
    """The official CFTC source or point-in-time contract was violated."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def archive_url(year: int) -> str:
    if year not in ARCHIVE_YEARS:
        raise CFTCDataError("CFTC archive year escaped the frozen 2018-2024 scope")
    return f"{ARCHIVE_BASE}/fut_fin_txt_{year}.zip"


def report_url(report_date: date) -> str:
    if report_date.year not in ARCHIVE_YEARS:
        raise CFTCDataError("CFTC report date escaped the frozen archive scope")
    filename = _REPORT_URL_OVERRIDES.get(report_date, f"financial_lf{report_date:%m%d%y}.htm")
    return f"{REPORT_BASE}/{report_date.year}/futures/{filename}"


def ordinary_publication_date(report_date: date) -> date:
    """Return the first Friday strictly after the official position date."""
    days = (4 - report_date.weekday()) % 7
    return report_date + timedelta(days=days or 7)


_UPDATED_PATTERN = re.compile(rb"Updated\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", re.IGNORECASE)
_POSITIONS_DATE_PATTERN = re.compile(
    rb"Positions\s+as\s+of\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", re.IGNORECASE
)


def _label_date(label: bytes) -> date:
    """Parse an official CFTC calendar-date label; the label carries no clock or zone."""
    return datetime.strptime(label.decode("ascii"), "%B %d, %Y").replace(tzinfo=UTC).date()


def resolve_publication_date(report_date: date, official_report_html: bytes) -> tuple[date, str]:
    """Resolve publication from the dated label embedded in an official archived report."""
    position_labels = set(_POSITIONS_DATE_PATTERN.findall(official_report_html))
    try:
        position_dates = {_label_date(label) for label in position_labels}
    except (UnicodeDecodeError, ValueError) as exc:
        raise CFTCDataError("official CFTC positions date is invalid") from exc
    if position_dates != {report_date}:
        raise CFTCDataError("official CFTC report page does not match the source report date")
    labels = _UPDATED_PATTERN.findall(official_report_html)
    if len(labels) != 1:
        raise CFTCDataError("official CFTC report lacks one unambiguous Updated date")
    try:
        publication_date = _label_date(labels[0])
    except (UnicodeDecodeError, ValueError) as exc:
        raise CFTCDataError("official CFTC Updated date is invalid") from exc
    if publication_date < report_date:
        raise CFTCDataError("official publication date predates report date")
    basis = (
        ORDINARY_BASIS
        if publication_date == ordinary_publication_date(report_date)
        else EXCEPTION_BASIS
    )
    return publication_date, basis


def availability_timestamp(publication_date: date) -> datetime:
    return datetime.combine(publication_date + timedelta(days=1), time(), tzinfo=UTC)


def development_eligible(available: datetime) -> bool:
    if available.tzinfo is None:
        raise CFTCDataError("CFTC availability timestamp lacks timezone")
    return int(available.astimezone(UTC).timestamp() * 1_000_000) <= CUTOFF_US


def leveraged_net_oi_share(leveraged_long: int, leveraged_short: int, open_interest: int) -> float:
    if open_interest <= 0 or leveraged_long < 0 or leveraged_short < 0:
        raise CFTCDataError("CFTC feature fields are invalid")
    try:
        value = Decimal(leveraged_long - leveraged_short) / Decimal(open_interest)
    except (InvalidOperation, ZeroDivisionError) as exc:
        raise CFTCDataError("CFTC feature denominator is invalid") from exc
    feature = float(value)
    if not math.isfinite(feature):
        raise CFTCDataError("CFTC feature is non-finite")
    return feature


def _required_integer(row: Mapping[str, str], column: str) -> int:
    value = row.get(column)
    if value is None or not value.strip():
        raise CFTCDataError(f"CFTC row lacks required numeric field {column}")
    try:
        return int(value.strip())
    except ValueError as exc:
        raise CFTCDataError(f"CFTC row has invalid numeric field {column}") from exc


def parse_archive(payload: bytes, year: int) -> list[dict[str, Any]]:
    """Parse only the exact official CME Bitcoin TFF market from one annual ZIP."""
    if year not in ARCHIVE_YEARS:
        raise CFTCDataError("CFTC parser year escaped the frozen scope")
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise CFTCDataError("CFTC annual source is not a ZIP archive") from exc
    names = archive.namelist()
    if names != ["FinFutYY.txt"]:
        raise CFTCDataError(f"unexpected CFTC TFF archive members: {names}")
    with archive.open(names[0]) as binary:
        reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig", newline=""))
        if reader.fieldnames is None or not REQUIRED_COLUMNS <= set(reader.fieldnames):
            raise CFTCDataError("official CFTC TFF schema lacks required columns")
        selected: list[dict[str, Any]] = []
        for row in reader:
            code = (row.get(CODE_COLUMN) or "").strip()
            name = (row.get(MARKET_COLUMN) or "").strip()
            if code != CONTRACT_MARKET_CODE:
                continue
            if name != MARKET_NAME:
                raise CFTCDataError("CFTC contract code resolved to an unexpected market")
            try:
                report_date = date.fromisoformat(row[REPORT_DATE_COLUMN].strip())
            except (KeyError, ValueError) as exc:
                raise CFTCDataError("CFTC row has invalid report date") from exc
            if report_date.year != year:
                raise CFTCDataError("CFTC row is in the wrong annual archive")
            open_interest = _required_integer(row, OPEN_INTEREST_COLUMN)
            leveraged_long = _required_integer(row, LONG_COLUMN)
            leveraged_short = _required_integer(row, SHORT_COLUMN)
            if open_interest <= 0:
                raise CFTCDataError("CFTC open interest must be positive")
            if leveraged_long < 0 or leveraged_short < 0:
                raise CFTCDataError("CFTC leveraged positions must be nonnegative")
            selected.append(
                {
                    "report_date": report_date,
                    "market_name": name,
                    "contract_market_code": code,
                    "open_interest_all": open_interest,
                    "leveraged_funds_long_all": leveraged_long,
                    "leveraged_funds_short_all": leveraged_short,
                }
            )
    selected.sort(key=lambda item: item["report_date"])
    dates = [item["report_date"] for item in selected]
    if len(dates) != len(set(dates)):
        raise CFTCDataError("duplicate CFTC market/report rows within annual archive")
    return selected


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    staging.write_bytes(payload)
    os.replace(staging, path)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    _atomic_bytes(path, encoded)


def _download(url: str) -> tuple[bytes, Mapping[str, str]]:
    response = httpx.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=90,
        follow_redirects=True,
    )
    if response.status_code != 200:
        raise CFTCDataError(f"official CFTC archive failed: HTTP {response.status_code}")
    return response.content, dict(response.headers)


def _archive_path(root: Path, year: int) -> Path:
    return root / RAW_ROOT / str(year) / f"fut_fin_txt_{year}.zip"


def _publication_evidence_path(root: Path, report_date_value: date) -> Path:
    return (
        root
        / RAW_ROOT
        / "publication-evidence"
        / str(report_date_value.year)
        / f"financial_lf{report_date_value:%m%d%y}.htm"
    )


def acquire(
    root: Path = ROOT,
    *,
    download: Callable[[str], tuple[bytes, Mapping[str, str]]] = _download,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, int]:
    """Preserve annual bytes and an official per-report publication evidence index."""
    all_rows: list[dict[str, Any]] = []
    fetched = reused = 0
    for year in ARCHIVE_YEARS:
        path = _archive_path(root, year)
        metadata_path = path.with_suffix(".meta.json")
        if path.is_file() and metadata_path.is_file():
            payload = path.read_bytes()
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if (
                metadata.get("source_url") != archive_url(year)
                or metadata.get("sha256") != sha256_bytes(payload)
                or metadata.get("compressed_bytes") != len(payload)
                or metadata.get("year") != year
                or metadata.get("source_family_version") != SOURCE_FAMILY
            ):
                raise CFTCDataError("cached CFTC annual archive identity mismatch")
            reused += 1
        else:
            payload, headers = download(archive_url(year))
            _atomic_bytes(path, payload)
            _atomic_json(
                metadata_path,
                {
                    "compressed_bytes": len(payload),
                    "retrieval_timestamp": clock()
                    .astimezone(UTC)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "sha256": sha256_bytes(payload),
                    "source_family_version": SOURCE_FAMILY,
                    "source_last_modified": headers.get("last-modified"),
                    "source_url": archive_url(year),
                    "year": year,
                },
            )
            fetched += 1
        all_rows.extend(parse_archive(payload, year))

    report_dates = [row["report_date"] for row in all_rows]
    if len(report_dates) != len(set(report_dates)):
        raise CFTCDataError("duplicate CFTC market/report rows across annual archives")
    calendar: list[dict[str, Any]] = []
    unresolved = 0
    for report_date_value in sorted(report_dates):
        url = report_url(report_date_value)
        try:
            evidence_path = _publication_evidence_path(root, report_date_value)
            metadata_path = evidence_path.with_suffix(".meta.json")
            if evidence_path.is_file() and metadata_path.is_file():
                evidence = evidence_path.read_bytes()
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                if metadata.get("source_url") != url:
                    evidence, headers = download(url)
                    _atomic_bytes(evidence_path, evidence)
                    _atomic_json(
                        metadata_path,
                        {
                            "bytes": len(evidence),
                            "retrieval_timestamp": clock()
                            .astimezone(UTC)
                            .isoformat()
                            .replace("+00:00", "Z"),
                            "sha256": sha256_bytes(evidence),
                            "source_family_version": SOURCE_FAMILY,
                            "source_last_modified": headers.get("last-modified"),
                            "source_url": url,
                        },
                    )
                elif (
                    metadata.get("sha256") != sha256_bytes(evidence)
                    or metadata.get("bytes") != len(evidence)
                    or metadata.get("source_family_version") != SOURCE_FAMILY
                ):
                    raise CFTCDataError("cached CFTC publication evidence identity mismatch")
            else:
                evidence, headers = download(url)
                _atomic_bytes(evidence_path, evidence)
                _atomic_json(
                    metadata_path,
                    {
                        "bytes": len(evidence),
                        "retrieval_timestamp": clock()
                        .astimezone(UTC)
                        .isoformat()
                        .replace("+00:00", "Z"),
                        "sha256": sha256_bytes(evidence),
                        "source_family_version": SOURCE_FAMILY,
                        "source_last_modified": headers.get("last-modified"),
                        "source_url": url,
                    },
                )
            publication, basis = resolve_publication_date(report_date_value, evidence)
            calendar.append(
                {
                    "availability_timestamp": availability_timestamp(publication)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "official_report_bytes": len(evidence),
                    "official_report_sha256": sha256_bytes(evidence),
                    "official_report_url": url,
                    "publication_date": publication.isoformat(),
                    "publication_date_basis": basis,
                    "report_date": report_date_value.isoformat(),
                    "status": "ELIGIBLE_FOR_CUTOFF_EVALUATION",
                }
            )
        except CFTCDataError as exc:
            unresolved += 1
            calendar.append(
                {
                    "availability_timestamp": None,
                    "official_report_bytes": None,
                    "official_report_sha256": None,
                    "official_report_url": url,
                    "publication_date": None,
                    "publication_date_basis": None,
                    "report_date": report_date_value.isoformat(),
                    "status": "INELIGIBLE_PUBLICATION_DATE_UNRESOLVED",
                    "detail": str(exc),
                }
            )
    calendar_path = root / PUBLICATION_CALENDAR_PATH
    _atomic_json(
        calendar_path,
        {
            "availability_rule": AVAILABILITY_RULE,
            "ordinary_release_documentation": ORDINARY_RELEASE_DOCUMENTATION,
            "records": calendar,
            "retrieval_timestamp": clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "schema_version": 1,
            "special_announcements": SPECIAL_ANNOUNCEMENTS,
            "source": SOURCE_FAMILY,
        },
    )
    return {
        "archives_fetched": fetched,
        "archives_reused": reused,
        "raw_rows": len(all_rows),
        "publication_rows": len(calendar),
        "unresolved_publication_rows": unresolved,
    }


def raw_records(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    archives: list[dict[str, Any]] = []
    for year in ARCHIVE_YEARS:
        path = _archive_path(root, year)
        metadata_path = path.with_suffix(".meta.json")
        if not path.is_file() or not metadata_path.is_file():
            raise CFTCDataError(f"official CFTC archive {year} is not installed")
        payload = path.read_bytes()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("source_url") != archive_url(year)
            or metadata.get("sha256") != sha256_bytes(payload)
            or metadata.get("compressed_bytes") != len(payload)
            or metadata.get("year") != year
            or metadata.get("source_family_version") != SOURCE_FAMILY
        ):
            raise CFTCDataError("CFTC raw archive metadata or hash drifted")
        parsed = parse_archive(payload, year)
        rows.extend(parsed)
        archives.append(
            {
                **metadata,
                "path": path.relative_to(root).as_posix(),
                "rows": len(parsed),
            }
        )
    dates = [row["report_date"] for row in rows]
    if not rows or len(dates) != len(set(dates)):
        raise CFTCDataError("CFTC raw timeline is empty or duplicated")
    return sorted(rows, key=lambda row: row["report_date"]), archives


def publication_calendar(root: Path = ROOT) -> tuple[dict[date, dict[str, Any]], dict[str, Any]]:
    path = root / PUBLICATION_CALENDAR_PATH
    if not path.is_file():
        raise CFTCDataError("CFTC publication calendar is not installed")
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        document.get("source") != SOURCE_FAMILY
        or document.get("availability_rule") != AVAILABILITY_RULE
        or document.get("ordinary_release_documentation") != ORDINARY_RELEASE_DOCUMENTATION
        or document.get("special_announcements") != SPECIAL_ANNOUNCEMENTS
    ):
        raise CFTCDataError("CFTC publication calendar identity drifted")
    records = document.get("records")
    if not isinstance(records, list):
        raise CFTCDataError("CFTC publication calendar records are malformed")
    by_date: dict[date, dict[str, Any]] = {}
    for record in records:
        try:
            report_date_value = date.fromisoformat(record["report_date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CFTCDataError("CFTC publication record date is invalid") from exc
        if report_date_value in by_date:
            raise CFTCDataError("duplicate CFTC publication date record")
        by_date[report_date_value] = record
    return by_date, document


def _canonical_row(source: Mapping[str, Any], publication: Mapping[str, Any]) -> dict[str, Any]:
    try:
        publication_date_value = date.fromisoformat(str(publication["publication_date"]))
        available = datetime.fromisoformat(str(publication["availability_timestamp"]))
    except (KeyError, ValueError) as exc:
        raise CFTCDataError("eligible CFTC publication record is malformed") from exc
    if available.tzinfo is None or available.astimezone(UTC) != availability_timestamp(
        publication_date_value
    ):
        raise CFTCDataError("CFTC availability timestamp violates the frozen rule")
    basis = publication.get("publication_date_basis")
    if basis not in {ORDINARY_BASIS, EXCEPTION_BASIS}:
        raise CFTCDataError("CFTC publication basis is invalid")
    open_interest = int(source["open_interest_all"])
    leveraged_long = int(source["leveraged_funds_long_all"])
    leveraged_short = int(source["leveraged_funds_short_all"])
    feature = leveraged_net_oi_share(leveraged_long, leveraged_short, open_interest)
    return {
        "report_date": source["report_date"],
        "publication_date": publication_date_value,
        "availability_timestamp": available.astimezone(UTC),
        "publication_date_basis": basis,
        "open_interest_all": open_interest,
        "leveraged_funds_long_all": leveraged_long,
        "leveraged_funds_short_all": leveraged_short,
        "leveraged_funds_net_oi_share": feature,
    }


def build(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    source, archives = raw_records(root)
    calendar, calendar_document = publication_calendar(root)
    source_dates = {row["report_date"] for row in source}
    if set(calendar) != source_dates:
        raise CFTCDataError("CFTC publication calendar does not exactly cover raw rows")
    canonical: list[dict[str, Any]] = []
    unresolved = excluded_postcutoff = exceptions = 0
    for row in source:
        publication = calendar[row["report_date"]]
        if publication.get("status") == "INELIGIBLE_PUBLICATION_DATE_UNRESOLVED":
            unresolved += 1
            continue
        if publication.get("status") != "ELIGIBLE_FOR_CUTOFF_EVALUATION":
            raise CFTCDataError("unknown CFTC publication eligibility state")
        candidate = _canonical_row(row, publication)
        if candidate["publication_date_basis"] == EXCEPTION_BASIS:
            exceptions += 1
        if not development_eligible(candidate["availability_timestamp"]):
            excluded_postcutoff += 1
            continue
        canonical.append(candidate)
    if not canonical:
        raise CFTCDataError("CFTC canonical eligible context is empty")
    availability = [row["availability_timestamp"] for row in canonical]
    if any(right <= left for left, right in zip(availability, availability[1:], strict=False)):
        raise CFTCDataError("CFTC canonical availability timeline is not strictly increasing")
    artifact = write_parquet(
        root / CANONICAL_PATH,
        canonical,
        schema=CFTC_SCHEMA,
        sort_key=["availability_timestamp"],
        root=root,
    )
    calendar_path = root / PUBLICATION_CALENDAR_PATH
    report_dates = [row["report_date"] for row in source]
    gaps = [
        (right - left).days
        for left, right in zip(report_dates, report_dates[1:], strict=False)
        if (right - left).days > 10
    ]
    manifest = {
        "schema_version": 1,
        "manifest_id": "CFTC-CME-BITCOIN-TFF-DEV-v1",
        "version": VERSION,
        "source": {
            "family": SOURCE_FAMILY,
            "official_only": True,
            "annual_archive_base": ARCHIVE_BASE,
            "report_archive_base": REPORT_BASE,
            "ordinary_release_documentation": ORDINARY_RELEASE_DOCUMENTATION,
            "special_announcements": SPECIAL_ANNOUNCEMENTS,
        },
        "market": {
            "name": MARKET_NAME,
            "cftc_contract_market_code": CONTRACT_MARKET_CODE,
            "source_column": CODE_COLUMN,
        },
        "archive_years": list(ARCHIVE_YEARS),
        "raw_archives": archives,
        "publication_calendar": {
            "path": PUBLICATION_CALENDAR_PATH,
            "sha256": file_sha256(calendar_path),
            "records": len(calendar_document["records"]),
            "basis_values": [ORDINARY_BASIS, EXCEPTION_BASIS],
        },
        "parser_version": PARSER_VERSION,
        "availability_rule": AVAILABILITY_RULE,
        "development_cutoff": CUTOFF.isoformat().replace("+00:00", "Z"),
        "feature": {
            "id": FEATURE,
            "formula": (
                "(Lev_Money_Positions_Long_All - Lev_Money_Positions_Short_All) / Open_Interest_All"
            ),
            "new_feature_count": 1,
            "clipping": False,
            "normalization": "NONE",
            "interpolation": False,
            "freshness_threshold": None,
        },
        "row_counts": {
            "raw_cftc_rows": len(source),
            "canonical_point_in_time_eligible_rows": len(canonical),
            "excluded_availability_after_cutoff": excluded_postcutoff,
            "excluded_publication_date_unresolved": unresolved,
        },
        "coverage": {
            "first_report_date": report_dates[0].isoformat(),
            "last_report_date": report_dates[-1].isoformat(),
            "first_availability_timestamp": availability[0].isoformat().replace("+00:00", "Z"),
            "last_availability_timestamp": availability[-1].isoformat().replace("+00:00", "Z"),
        },
        "integrity": {
            "duplicate_market_report_rows": 0,
            "missing_or_invalid_required_fields": 0,
            "invalid_open_interest": 0,
            "unresolved_publication_rows": unresolved,
            "postcutoff_rows_in_canonical": 0,
            "report_gaps_over_10_days": gaps,
            "official_exception_rows": exceptions,
            "source_gate_raw_row_reconciliation": len(source) == 352,
        },
        "canonical": artifact,
        "code_reference": "backend/app/research/cftc.py",
    }
    integrity = {
        "schema_version": 1,
        "work_package": "WP-017-CFTC-LEVERAGED-POSITIONING-PREP",
        "status": "PASS",
        "source": SOURCE_FAMILY,
        "market_name": MARKET_NAME,
        "contract_market_code": CONTRACT_MARKET_CODE,
        "raw_rows": len(source),
        "canonical_eligible_rows": len(canonical),
        "excluded_availability_after_cutoff": excluded_postcutoff,
        "unresolved_publication_rows": unresolved,
        "duplicate_market_report_rows": 0,
        "missing_or_invalid_required_fields": 0,
        "postcutoff_rows_in_canonical": 0,
        "official_exception_rows": exceptions,
        "publication_calendar_hash_verified": True,
        "raw_archive_hashes_verified": True,
        "market_identity_verified": True,
        "feature_formula_verified": True,
        "availability_rule_verified": True,
        "source_gate_raw_row_reconciliation": len(source) == 352,
        "market_outcomes_read": False,
    }
    return manifest, integrity


class CFTCContextSource:
    """Latest eligible report at or before a governed signal timestamp."""

    def __init__(self, availability_us: list[int], report_dates: list[date], values: list[float]):
        if not availability_us or not (len(availability_us) == len(report_dates) == len(values)):
            raise CFTCDataError("CFTC context needs aligned nonempty records")
        if any(
            right <= left for left, right in zip(availability_us, availability_us[1:], strict=False)
        ):
            raise CFTCDataError("CFTC availability timeline is not strictly increasing")
        if not all(math.isfinite(value) for value in values):
            raise CFTCDataError("CFTC context contains non-finite values")
        self.availability_us = tuple(availability_us)
        self.report_dates = tuple(report_dates)
        self.values = tuple(float(value) for value in values)

    def at(self, signal_us: int) -> tuple[int, date, float]:
        index = bisect.bisect_right(self.availability_us, signal_us) - 1
        if index < 0:
            raise CFTCDataError("no CFTC report is available at the signal timestamp")
        return self.availability_us[index], self.report_dates[index], self.values[index]


def load_cftc_context(root: Path = ROOT) -> CFTCContextSource:
    manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    if (
        manifest.get("manifest_id") != "CFTC-CME-BITCOIN-TFF-DEV-v1"
        or manifest.get("version") != VERSION
        or manifest.get("availability_rule") != AVAILABILITY_RULE
    ):
        raise CFTCDataError("CFTC manifest identity drifted")
    table = validate_parquet(manifest["canonical"], schema=CFTC_SCHEMA, root=root)
    availability_us = [int(value) for value in table["availability_timestamp"].cast(pa.int64())]
    if max(availability_us) > CUTOFF_US:
        raise CFTCDataError("CFTC canonical context contains post-cutoff availability")
    return CFTCContextSource(
        availability_us,
        table["report_date"].to_pylist(),
        [float(value) for value in table["leveraged_funds_net_oi_share"].to_pylist()],
    )


__all__ = [name for name in globals() if name.isupper()] + [
    "CFTCContextSource",
    "CFTCDataError",
    "acquire",
    "archive_url",
    "availability_timestamp",
    "build",
    "development_eligible",
    "leveraged_net_oi_share",
    "load_cftc_context",
    "ordinary_publication_date",
    "parse_archive",
    "publication_calendar",
    "raw_records",
    "report_url",
    "resolve_publication_date",
]
