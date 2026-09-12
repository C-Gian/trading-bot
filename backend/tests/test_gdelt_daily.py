"""GDELT_NEWS_CONTEXT_V1_1 daily acquisition semantics.

These cover only this checkpoint: the prospective amendment, the frozen five-channel
identity, daily resolution, next-day availability, and bounded/idempotent acquisition.
"""

from __future__ import annotations

import gzip
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from app.research import gdelt_daily
from app.research.exogenous import (
    GDELT_CHANNELS,
    GDELT_DAILY_PILOT_END,
    ExogenousDataError,
    calendar_days,
    daily_availability,
    validate_catalogs,
)
from app.research.gdelt_daily import (
    AMENDMENT_PATH,
    MAX_ATTEMPTS,
    MAX_THROTTLE_RESPONSES,
    _aggregate,
    _valid_payload,
    _validate_acquired_document,
    acquire,
    build,
    pilot_specs,
    request_specs,
    request_url,
)
from app.research.wp004 import ROOT

PILOT_START = "2017-08-17T00:00:00Z"
PILOT_END = "2017-12-31T23:59:59Z"


def _document(mode: str, points: list[dict[str, object]]) -> dict[str, object]:
    return {
        "query_details": {"date_resolution": "day", "timelinesmooth": 0},
        "timeline": [{"series": mode, "data": points}],
    }


def _spec_points(spec: dict[str, object]) -> list[dict[str, object]]:
    days = calendar_days(
        datetime.fromisoformat(str(spec["start_utc"])), datetime.fromisoformat(str(spec["end_utc"]))
    )
    if spec["mode"] == "TimelineVolRaw":
        return [
            {"date": f"{day:%Y%m%d}T000000Z", "value": index + 1, "norm": 1000 + index}
            for index, day in enumerate(days)
        ]
    return [
        {"date": f"{day:%Y%m%d}T000000Z", "value": -1.5 + index * 0.001}
        for index, day in enumerate(days)
    ]


def _identity_root(tmp_path: Path) -> Path:
    """A build root carrying the frozen catalog and amendment the manifest hashes."""
    for relative in (AMENDMENT_PATH, "research/exogenous/GDELT_QUERY_CATALOG_V1.json"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    return tmp_path


class _StubResponse:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content


class _StubClient:
    """Answers every frozen pilot request once, from its own request identity."""

    def __init__(self, specs: tuple[dict[str, object], ...], *, status: int = 200) -> None:
        self.by_url = {request_url(spec): spec for spec in specs}
        self.status = status
        self.calls: list[str] = []

    def get(self, url: str, **_: object) -> _StubResponse:
        self.calls.append(url)
        if self.status != 200:
            return _StubResponse(self.status, b"throttled")
        spec = self.by_url[url]
        document = _document(str(spec["mode"]), _spec_points(spec))
        return _StubResponse(200, json.dumps(document).encode("utf-8"))


# --- amendment -------------------------------------------------------------------


def test_amendment_is_prospective_and_changes_no_query_semantics() -> None:
    amendment = json.loads((ROOT / AMENDMENT_PATH).read_text(encoding="utf-8"))
    catalog = validate_catalogs()["gdelt"]
    assert amendment["amendment_id"] == "GDELT_NEWS_CONTEXT_V1_1"
    assert amendment["prospective"] is True
    assert amendment["accepted_v1_1_rows_before_amendment"] == 0
    assert amendment["catalog_channels_or_vocabulary_changed"] is False
    assert amendment["keywords_added"] == amendment["keywords_removed"] == 0
    assert amendment["semantic_channel_count"] == len(catalog["channels"]) == 5
    assert amendment["btc_prices_returns_or_outcomes_used"] is False
    assert amendment["btc_outcomes_consulted_for_this_decision"] is False
    assert amendment["strategy_results_consulted_for_this_decision"] is False
    assert amendment["motivation"]["decision_basis"] == "INFRASTRUCTURE_FEASIBILITY_ONLY"
    assert "429" in amendment["motivation"]["operational_blocker"]
    assert amendment["preserved_v1_evidence"]["deleted"] == 0
    assert amendment["preserved_v1_evidence"]["rewritten"] == 0
    assert amendment["v1_1_news_semantics"]["timeline_smooth"] == 0
    assert amendment["v1_1_news_semantics"]["modes"] == ["TimelineVolRaw", "TimelineTone"]
    assert amendment["v1_1_news_semantics"]["same_day_availability_forbidden"] is True


def test_v1_hourly_cache_and_module_are_preserved_untouched() -> None:
    v1_root = ROOT / "data/raw/exogenous/gdelt-doc-v2"
    assert (ROOT / "backend/app/research/gdelt.py").is_file()
    assert len(list(v1_root.rglob("*.json.gz"))) == len(list(v1_root.rglob("*.meta.json")))
    assert gdelt_daily.RAW_ROOT != "data/raw/exogenous/gdelt-doc-v2"


# --- frozen request identity -----------------------------------------------------


def test_pilot_is_exactly_five_channels_two_modes_over_the_frozen_interval() -> None:
    specs = pilot_specs()
    assert len(specs) == 10
    assert {spec["channel_id"] for spec in specs} == set(GDELT_CHANNELS)
    assert {spec["mode"] for spec in specs} == {"TimelineVolRaw", "TimelineTone"}
    assert {spec["start_utc"] for spec in specs} == {PILOT_START}
    assert {spec["end_utc"] for spec in specs} == {PILOT_END}
    assert all(spec["params"]["timelinesmooth"] == "0" for spec in specs)
    assert len({spec["request_id"] for spec in specs}) == 10


def test_request_identity_is_deterministic_and_uses_the_frozen_queries() -> None:
    queries = {
        item["channel_id"]: item["query"] for item in validate_catalogs()["gdelt"]["channels"]
    }
    first, second = pilot_specs(), pilot_specs()
    assert [spec["request_id"] for spec in first] == [spec["request_id"] for spec in second]
    assert all(spec["params"]["query"] == queries[spec["channel_id"]] for spec in first)


def test_full_design_never_requests_after_the_development_cutoff() -> None:
    specs = request_specs()
    assert len(specs) == 80
    assert max(spec["end_utc"] for spec in specs) == "2024-12-31T23:59:59Z"
    with pytest.raises(ExogenousDataError, match="never request data after"):
        request_specs(end=datetime(2025, 1, 1, tzinfo=UTC))


# --- resolution and bounds -------------------------------------------------------


def test_returned_resolution_is_validated_not_assumed() -> None:
    for resolution in ("hour", "15m", "month", None):
        payload = json.dumps(
            {"query_details": {"date_resolution": resolution}, "timeline": []}
        ).encode("utf-8")
        with pytest.raises(ExogenousDataError, match="not daily resolution"):
            _valid_payload(payload)
    assert _valid_payload(json.dumps(_document("TimelineVolRaw", [])).encode("utf-8"))


def test_declared_smoothing_is_rejected() -> None:
    payload = json.dumps(
        {"query_details": {"date_resolution": "day", "timelinesmooth": 5}, "timeline": []}
    ).encode("utf-8")
    with pytest.raises(ExogenousDataError, match="smoothing"):
        _valid_payload(payload)


def test_points_outside_the_frozen_window_or_after_the_cutoff_are_rejected() -> None:
    spec = {"start_utc": PILOT_START, "end_utc": PILOT_END}
    escaped = _document("TimelineVolRaw", [{"date": "20180101T000000Z", "value": 1, "norm": 2}])
    with pytest.raises(ExogenousDataError, match="escaped frozen request bounds"):
        _validate_acquired_document(escaped, spec)
    intraday = _document("TimelineVolRaw", [{"date": "20170901T130000Z", "value": 1, "norm": 2}])
    with pytest.raises(ExogenousDataError, match="intraday timestamp"):
        _validate_acquired_document(intraday, spec)


# --- aggregation -----------------------------------------------------------------


def test_daily_volume_retains_raw_matched_norm_and_coverage_inputs() -> None:
    document = _document(
        "TimelineVolRaw", [{"date": "20170817T000000Z", "value": 25, "norm": 5000}]
    )
    result = _aggregate(document, mode="TimelineVolRaw")[date(2017, 8, 17)]
    assert result == {
        "matched_articles": 25,
        "monitored_articles_norm": 5000,
        "norm_available": True,
    }


def test_missing_normalization_is_not_silently_treated_as_available() -> None:
    document = _document("TimelineVolRaw", [{"date": "20170817T000000Z", "value": 3}])
    assert _aggregate(document, mode="TimelineVolRaw")[date(2017, 8, 17)]["norm_available"] is False


def test_duplicate_source_day_is_rejected() -> None:
    document = _document(
        "TimelineVolRaw",
        [
            {"date": "20170817T000000Z", "value": 1, "norm": 10},
            {"date": "20170817T000000Z", "value": 2, "norm": 10},
        ],
    )
    with pytest.raises(ExogenousDataError, match="duplicate GDELT daily source point"):
        _aggregate(document, mode="TimelineVolRaw")


# --- availability ----------------------------------------------------------------


def test_a_complete_utc_day_is_available_only_on_the_next_day_at_midnight() -> None:
    assert daily_availability(date(2017, 8, 17)) == datetime(2017, 8, 18, tzinfo=UTC)
    assert daily_availability(date(2017, 12, 31)) == datetime(2018, 1, 1, tzinfo=UTC)
    assert daily_availability(date(2020, 2, 28)) == datetime(2020, 2, 29, tzinfo=UTC)


# --- bounded, resumable, idempotent, hash-verified acquisition --------------------


def test_persistent_throttling_stops_bounded_and_preserves_successful_entries(
    tmp_path: Path,
) -> None:
    specs = pilot_specs()
    sleeps: list[float] = []
    client = _StubClient(specs, status=429)
    progress = acquire(tmp_path, specs=specs, sleep=sleeps.append, client=client)
    assert progress["throttle_429_responses"] == MAX_THROTTLE_RESPONSES
    assert progress["stopped_on_persistent_throttle"] is True
    assert progress["status"] == "PARTIAL_SOURCE_THROTTLED"
    assert progress["fetched"] == 0 and progress["failed"] == 10
    assert len(client.calls) == MAX_THROTTLE_RESPONSES
    assert len(sleeps) == MAX_THROTTLE_RESPONSES
    assert len(client.calls) <= MAX_ATTEMPTS * len(specs)


def test_pilot_acquisition_is_resumable_idempotent_and_hash_verified(tmp_path: Path) -> None:
    specs = pilot_specs()
    client = _StubClient(specs)
    first = acquire(tmp_path, specs=specs, sleep=lambda _: None, client=client)
    assert first == {
        "version": "GDELT_NEWS_CONTEXT_V1_1",
        "expected": 10,
        "fetched": 10,
        "reused": 0,
        "failed": 0,
        "completed": 10,
        "throttle_429_responses": 0,
        "stopped_on_persistent_throttle": False,
        "status": "COMPLETE",
        "errors": [],
    }
    second = acquire(tmp_path, specs=specs, sleep=lambda _: None, client=client)
    assert second["reused"] == 10 and second["fetched"] == 0
    assert len(client.calls) == 10

    meta = json.loads((tmp_path / str(specs[0]["meta_path"])).read_text(encoding="utf-8"))
    assert len(meta["response_sha256"]) == len(meta["compressed_file_sha256"]) == 64
    assert meta["date_resolution"] == "day"


def test_corrupted_cache_entry_fails_hash_verification(tmp_path: Path) -> None:
    specs = pilot_specs()
    acquire(tmp_path, specs=specs, sleep=lambda _: None, client=_StubClient(specs))
    raw_path = tmp_path / str(specs[0]["raw_path"])
    tampered = _document("TimelineVolRaw", [{"date": "20170817T000000Z", "value": 9, "norm": 9}])
    raw_path.write_bytes(gzip.compress(json.dumps(tampered).encode("utf-8"), mtime=0))
    with pytest.raises(ExogenousDataError, match="identity or hash mismatch"):
        acquire(tmp_path, specs=specs, sleep=lambda _: None, client=_StubClient(specs))


def test_pilot_build_is_deterministic_daily_and_gap_explicit(tmp_path: Path) -> None:
    root = _identity_root(tmp_path)
    specs = pilot_specs()
    acquire(root, specs=specs, sleep=lambda _: None, client=_StubClient(specs))
    manifest, integrity = build(root, specs=specs)
    rebuilt_manifest, rebuilt_integrity = build(root, specs=specs)
    assert manifest == rebuilt_manifest and integrity == rebuilt_integrity

    days = calendar_days(datetime.fromisoformat(PILOT_START), GDELT_DAILY_PILOT_END)
    assert manifest["days"] == len(days) == 137
    assert manifest["daily_rows"] == integrity["daily_rows"] == 5 * len(days)
    assert manifest["daily_rows_per_channel"] == dict.fromkeys(GDELT_CHANNELS, len(days))
    assert manifest["response_resolutions"] == ["day"]
    assert manifest["timeline_smooth"] == 0
    assert manifest["post_2024_rows"] == 0
    assert manifest["scope"] == "DETERMINISTIC_PILOT_INTERVAL"
    assert manifest["remaining_years_acquired"] is False
    assert manifest["btc_price_return_or_outcome_columns_loaded"] is False
    assert manifest["rolling_or_normalization_transforms"] is False
    assert manifest["trading_score"] is False
    assert integrity["status"] == "PASS"

    import pyarrow.parquet as pq

    rows = pq.read_table(root / gdelt_daily.CANONICAL_PATH).to_pylist()
    assert len({(row["channel_id"], row["day"]) for row in rows}) == len(rows)
    for row in rows:
        assert row["availability_time"] == daily_availability(row["day"])
        assert row["availability_time"] > datetime.combine(row["day"], datetime.max.time(), UTC)
        assert row["day"] <= date(2024, 12, 31)
        assert row["coverage_share"] == row["matched_articles"] / row["monitored_articles_norm"]


def test_build_refuses_to_invent_rows_for_a_missing_response(tmp_path: Path) -> None:
    root = _identity_root(tmp_path)
    specs = pilot_specs()
    acquire(root, specs=specs, sleep=lambda _: None, client=_StubClient(specs))
    (root / str(specs[0]["raw_path"])).unlink()
    with pytest.raises(ExogenousDataError, match="missing frozen GDELT daily response"):
        build(root, specs=specs)


def test_daily_pilot_touches_no_market_or_strategy_module() -> None:
    import ast

    source = (ROOT / "backend/app/research/gdelt_daily.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not modules & {
        "app.data.store",
        "app.backtest",
        "app.research.runner",
        "app.research.supervised",
    }
    assert "BTCUSDT" not in source
    assert "data/canonical" not in source and "data/derived/BTC" not in source
    assert {line.strip() for line in source.splitlines() if "btc" in line.lower()} == {
        '"btc_price_return_or_outcome_columns_loaded": False,',
        '"no_btc_prices_returns_outcomes_or_strategy": "PASS",',
    }
