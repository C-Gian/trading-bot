from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from app.research.evaluation_protocol import HOUR_US
from app.research.wikimedia import (
    ARTICLE,
    CUTOFF_DATE,
    MANIFEST_PATH,
    SOURCE_START,
    AttentionContextSource,
    WikimediaDataError,
    acquire,
    build,
    load_attention_context,
    parse_response,
    request_url,
    request_windows,
)

DAY_US = 24 * HOUR_US


def day_us(value: date) -> int:
    return int(datetime(value.year, value.month, value.day, tzinfo=UTC).timestamp() * 1_000_000)


def payload(start: date, end: date, *, article: str = ARTICLE) -> bytes:
    items = []
    current = start
    while current <= end:
        items.append(
            {
                "project": "en.wikipedia",
                "article": article,
                "granularity": "daily",
                "timestamp": current.strftime("%Y%m%d00"),
                "access": "all-access",
                "agent": "user",
                "views": 100 + (current - SOURCE_START).days % 31,
            }
        )
        current += timedelta(days=1)
    return json.dumps({"items": items}, separators=(",", ":")).encode()


def test_request_is_exact_official_source_and_cutoff_bounded() -> None:
    url = request_url(date(2024, 1, 1), CUTOFF_DATE)
    assert url == (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        "en.wikipedia/all-access/user/Bitcoin/daily/2024010100/2024123100"
    )
    assert request_windows()[0] == (SOURCE_START, date(2015, 12, 31))
    assert request_windows()[-1] == (date(2024, 1, 1), CUTOFF_DATE)
    with pytest.raises(WikimediaDataError, match="development window"):
        request_url(date(2024, 1, 1), date(2025, 1, 1))


def test_parser_rejects_selector_drift_and_postcutoff() -> None:
    valid = parse_response(
        payload(date(2024, 1, 1), date(2024, 1, 2)), date(2024, 1, 1), date(2024, 1, 2)
    )
    assert [row["pageviews"] for row in valid] == [100 + 3106 % 31, 100 + 3107 % 31]
    with pytest.raises(WikimediaDataError, match="selectors"):
        parse_response(
            payload(date(2024, 1, 1), date(2024, 1, 1), article="Ethereum"),
            date(2024, 1, 1),
            date(2024, 1, 1),
        )
    with pytest.raises(WikimediaDataError, match="request window"):
        parse_response(
            payload(date(2025, 1, 1), date(2025, 1, 1)),
            date(2024, 12, 31),
            date(2024, 12, 31),
        )


def test_attention_uses_current_day_only_at_day_start_plus_48h() -> None:
    start = date(2020, 1, 1)
    observations = [day_us(start + timedelta(days=index)) for index in range(31)]
    views = [10] * 28 + [50, 100, 200]
    source = AttentionContextSource(observations, views)
    availability = observations[29] + 2 * DAY_US
    before = source.at(availability - HOUR_US)
    at_boundary = source.at(availability)
    assert before.observation_us == observations[28]
    assert at_boundary.observation_us == observations[29]
    assert at_boundary.trailing_median == 10
    assert at_boundary.shock == pytest.approx(math.log(101 / 11))


def test_full_28_prior_observations_and_no_gap_are_required() -> None:
    start = date(2020, 1, 1)
    observations = [day_us(start + timedelta(days=index)) for index in range(29)]
    source = AttentionContextSource(observations, [10] * len(observations))
    with pytest.raises(WikimediaDataError, match="full 28"):
        source.at(observations[27] + 2 * DAY_US)
    assert source.at(observations[28] + 2 * DAY_US).shock == 0.0
    complete = [day_us(start + timedelta(days=index)) for index in range(30)]
    missing = complete[:10] + complete[11:]
    broken = AttentionContextSource(missing, [10] * len(missing))
    with pytest.raises(WikimediaDataError, match="missing daily"):
        broken.at(missing[-1] + 2 * DAY_US)


def test_postcutoff_and_misaligned_signals_are_rejected() -> None:
    start = date(2024, 11, 1)
    observations = [day_us(start + timedelta(days=index)) for index in range(61)]
    source = AttentionContextSource(observations, [10] * len(observations))
    with pytest.raises(WikimediaDataError, match="misaligned or post-cutoff"):
        source.at(day_us(date(2025, 1, 1)))
    with pytest.raises(WikimediaDataError, match="misaligned or post-cutoff"):
        source.at(day_us(date(2024, 12, 1)) + 1)


def test_synthetic_acquisition_build_and_load_are_deterministic(tmp_path: Path) -> None:
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        for start, end in request_windows():
            if url == request_url(start, end):
                return payload(start, end)
        raise AssertionError("unexpected request")

    first = acquire(tmp_path, fetch)
    second = acquire(tmp_path, lambda _url: (_ for _ in ()).throw(AssertionError("fetch")))
    manifest = build(tmp_path)
    assert first == {"windows": 10, "fetched": 10, "reused": 0}
    assert second == {"windows": 10, "fetched": 0, "reused": 10}
    assert len(calls) == 10
    assert manifest["records"] == (CUTOFF_DATE - SOURCE_START).days + 1
    assert manifest["integrity"] == {
        "duplicates": 0,
        "missing_days": 0,
        "missing_day_values": [],
        "strictly_increasing": True,
        "post_cutoff_rows": 0,
    }
    context = load_attention_context(tmp_path)
    assert context.at(day_us(date(2020, 1, 2))).availability_us <= day_us(date(2020, 1, 2))
    assert (tmp_path / MANIFEST_PATH).is_file()


def test_installed_wikimedia_dataset_if_available() -> None:
    root = Path(__file__).resolve().parents[2]
    manifest = (
        json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
        if (root / MANIFEST_PATH).is_file()
        else None
    )
    if manifest is None or not (root / manifest["canonical"]["path"]).is_file():
        pytest.skip("local Wikimedia integration dataset is not installed")
    source = load_attention_context(root)
    value = source.at(day_us(date(2024, 12, 31)))
    assert value.availability_us <= day_us(date(2024, 12, 31))
