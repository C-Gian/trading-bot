"""System G1 Checkpoint 1: virtual clock, replay-speed invariance and adapter equivalence."""

from __future__ import annotations

import dataclasses
import re
from datetime import timedelta

import pytest
from app.g1 import fixtures
from app.g1.bars import MINUTE, FutureObservationError
from app.g1.canonical import canonical_bytes
from app.g1.clock import SPEEDS, LiveStyleAdapter, ReplayController, ReplayStatus
from app.g1.core import G1Core, run_manifest, run_to_end
from app.g1.ledger import RiskPolicy

BARS = fixtures.minute_path()
POLICY = RiskPolicy()
MANIFEST = run_manifest(BARS, fixtures.START, fixtures.END, POLICY)


def _core() -> G1Core:
    return G1Core(MANIFEST, fixtures.scenario_step, fixtures.FUNDING_RATES, POLICY)


@pytest.fixture(scope="module")
def reference() -> G1Core:
    return run_to_end(_core(), BARS)


def _ids(core: G1Core) -> list[str]:
    return [canonical_bytes(record).decode() for record in core.store]


def test_replay_at_every_speed_reproduces_identical_records(reference) -> None:
    for speed in SPEEDS:
        controller = ReplayController(_core(), BARS)
        controller.set_speed(speed)
        controller.run_to_end(pace=lambda: 0.25)
        assert controller.status is ReplayStatus.COMPLETE
        assert controller.core.fingerprint() == reference.fingerprint(), speed
        assert (_ids(controller.core) == _ids(reference)) is True


def test_irregular_wall_pacing_and_speed_changes_do_not_change_outputs(reference) -> None:
    controller = ReplayController(_core(), BARS)
    paces = iter([0.1, 3.0, 0.7, 5.0, 0.013] * 100000)
    controller.start()
    count = 0
    while controller.status is ReplayStatus.RUNNING:
        if count % 7 == 0:
            controller.set_speed(SPEEDS[count % len(SPEEDS)])
        controller.tick(next(paces))
        count += 1
    assert controller.core.fingerprint() == reference.fingerprint()


def test_single_step_pause_and_start_semantics() -> None:
    controller = ReplayController(_core(), BARS)
    assert controller.status is ReplayStatus.READY
    controller.tick(1.0)  # not running: pacing does nothing
    assert controller.cursor == fixtures.START
    controller.step("1m")
    assert controller.cursor == fixtures.START + MINUTE and controller.status is ReplayStatus.PAUSED
    controller.step("15m")
    assert controller.cursor == fixtures.START + timedelta(minutes=15)
    controller.start()
    with pytest.raises(ValueError):
        controller.step()
    controller.tick(1.0)
    assert controller.cursor == fixtures.START + timedelta(minutes=30)  # default 900x speed
    controller.pause()
    frozen = controller.cursor
    controller.tick(1.0)
    assert controller.cursor == frozen
    with pytest.raises(ValueError):
        controller.set_speed(7)


def test_live_style_adapter_produces_identical_core_outputs(reference) -> None:
    core = _core()
    adapter = LiveStyleAdapter(core)
    for index, bar in enumerate(BARS):
        adapter.on_minute(bar)
        if index % 97 == 0:
            adapter.heartbeat(bar.available_at)  # redundant heartbeats are harmless
    adapter.heartbeat(fixtures.END)
    assert core.fingerprint() == reference.fingerprint()
    assert (_ids(core) == _ids(reference)) is True


def test_batched_historical_steps_match_minute_steps(reference) -> None:
    for step in (timedelta(minutes=7), timedelta(hours=5), timedelta(days=4)):
        assert run_to_end(_core(), BARS, step).fingerprint() == reference.fingerprint()


def test_late_or_future_minutes_cannot_rewrite_history() -> None:
    core = _core()
    core.advance_to(fixtures.START + timedelta(minutes=10))
    with pytest.raises(FutureObservationError):
        core.ingest(BARS[3])  # its availability instant already passed without it
    with pytest.raises(ValueError):
        core.ingest(dataclasses.replace(BARS[20], timeframe="15m"))


def test_scientific_identities_contain_no_wall_clock(reference) -> None:
    again = run_to_end(_core(), BARS)
    assert again.fingerprint() == reference.fingerprint()
    text = b"".join(canonical_bytes(record) for record in reference.store).decode()
    years = set(re.findall(r'"(\d{4})-\d\d-\d\dT\d\d:\d\d:\d\dZ"', text))
    assert years == {"2001"}  # only synthetic event times; no wall-clock timestamp
