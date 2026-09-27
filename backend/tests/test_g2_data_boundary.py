"""G2-01 phase-bounded data I/O acceptance tests (data exposure manifest section 10).

A fake repository root with a fake manifest and fake monthly objects is used, so the tests never
need (or touch) real market observations.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.g2.sources import (
    FUNDING_MANIFEST,
    KLINE_MANIFEST,
    Authorization,
    PhaseBoundedLoader,
    UnauthorizedObservationError,
)

HEADER = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore"


def monthly_object(year: int, month: int) -> bytes:
    rows = [HEADER]
    start = int(datetime(year, month, 1, tzinfo=UTC).timestamp() * 1000)
    for k in range(3 * 1440):  # the first three days of the month
        t = start + k * 60_000
        rows.append(f"{t},100,101,99,100.5,2,{t + 59_999},201,5,1,100.5,0")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"BTCUSDT-1m-{year:04d}-{month:02d}.csv", "\n".join(rows))
    return buffer.getvalue()


@pytest.fixture()
def fake_root(tmp_path: Path) -> Path:
    archives = []
    for year, month in ((2024, 5), (2024, 6), (2025, 1)):
        content = monthly_object(year, month)
        relative = f"data/raw/public-taker-flow/um/BTCUSDT-1m-{year:04d}-{month:02d}.zip"
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_bytes(content)
        archives.append(
            {
                "market": "USDM_PERPETUAL",
                "month": f"{year:04d}-{month:02d}",
                "raw_path": relative,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    manifest = {
        "manifest_id": "FAKE",
        "object_index_sha256": "0" * 64,
        "request_ceiling": "2024-12-31T23:59:59.999Z",
        "archives": archives,
    }
    (tmp_path / KLINE_MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / KLINE_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    funding = {
        "manifest_id": "FAKE-FUNDING",
        "first_funding_time": "2019-09-10T08:00:00Z",
        "last_funding_time": "2024-12-31T16:00:00Z",
        "canonical": {"path": "data/derived/fake.parquet", "file_sha256": "0" * 64},
    }
    (tmp_path / FUNDING_MANIFEST).write_text(json.dumps(funding), encoding="utf-8")
    return tmp_path


class Spy:
    def __init__(self) -> None:
        self.opened: list[str] = []

    def __call__(self, path: Path) -> bytes:
        self.opened.append(path.as_posix())
        return path.read_bytes()


def june() -> Authorization:
    return Authorization(
        datetime(2024, 6, 1, 12, tzinfo=UTC), datetime(2024, 6, 2, tzinfo=UTC), "test", "LEDGER"
    )


def test_an_exposed_2024_window_opens_only_intersecting_objects_and_filters_rows(fake_root):
    spy = Spy()
    loader = PhaseBoundedLoader(june(), fake_root, spy)
    minutes = loader.minutes()
    assert [Path(p).name for p in spy.opened] == ["BTCUSDT-1m-2024-06.zip"]
    assert minutes[0].open_time == datetime(2024, 6, 1, 12, tzinfo=UTC)
    assert minutes[-1].open_time == datetime(2024, 6, 1, 23, 59, tzinfo=UTC) and len(minutes) == 720
    (entry,) = [e for e in loader.log if e["kind"] == "OBSERVATION_READ"]
    assert entry["requested"] == [june().start, june().end]
    assert entry["returned"] == [minutes[0].open_time, minutes[-1].available_at]
    assert entry["rows"] == 720 and len(entry["opened_objects"]) == 1


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (datetime(2024, 12, 31, tzinfo=UTC), datetime(2025, 1, 2, tzinfo=UTC)),
        (datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 2, 1, tzinfo=UTC)),
    ],
)
def test_2025_observation_access_is_rejected_before_any_open(fake_root, start, end):
    spy = Spy()
    with pytest.raises(UnauthorizedObservationError):
        PhaseBoundedLoader(Authorization(start, end, "x", "y"), fake_root, spy).minutes()
    assert spy.opened == []


def test_protected_objects_are_never_considered_even_if_listed(fake_root):
    wide = Authorization(
        datetime(2024, 5, 1, tzinfo=UTC), datetime(2025, 1, 1, tzinfo=UTC), "x", "y"
    )
    spy = Spy()
    loader = PhaseBoundedLoader(wide, fake_root, spy)
    assert [a["month"] for a in loader.authorized_objects()] == ["2024-05", "2024-06"]
    loader.minutes()
    assert not any("2025" in path for path in spy.opened)


def test_touching_an_unauthorized_object_fails(fake_root):
    spy = Spy()
    loader = PhaseBoundedLoader(june(), fake_root, spy)
    with pytest.raises(UnauthorizedObservationError):
        loader._open(
            "data/raw/public-taker-flow/um/BTCUSDT-1m-2024-05.zip",
            (datetime(2024, 5, 1, tzinfo=UTC), datetime(2024, 6, 1, tzinfo=UTC)),
        )
    with pytest.raises(UnauthorizedObservationError):
        loader._open(
            "data/raw/public-taker-flow/um/BTCUSDT-1m-2025-01.zip",
            (datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 2, 1, tzinfo=UTC)),
        )
    assert spy.opened == []


def test_metadata_only_manifest_read_opens_no_observation(fake_root):
    spy = Spy()
    loader = PhaseBoundedLoader(june(), fake_root, spy)
    identity = loader.manifest_identity()
    assert identity["kline_manifest"] == "FAKE" and spy.opened == []
    assert [a["month"] for a in loader.authorized_objects()] == ["2024-06"]
    assert spy.opened == [] and loader.log[0]["kind"] == "METADATA_READ"


def test_hash_mismatch_is_refused(fake_root):
    target = fake_root / "data/raw/public-taker-flow/um/BTCUSDT-1m-2024-06.zip"
    target.write_bytes(monthly_object(2024, 5))
    with pytest.raises(UnauthorizedObservationError):
        PhaseBoundedLoader(june(), fake_root).minutes()
