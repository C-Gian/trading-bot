"""System G1 Checkpoint 1: immutable records and causal completed-bar aggregation."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.g1 import fixtures
from app.g1.bars import (
    MINUTE,
    Aggregator,
    CausalView,
    FutureObservationError,
    minute_bar,
    window_end,
    window_start,
)
from app.g1.core import G1Core, run_manifest, run_to_end
from app.g1.ledger import RiskPolicy
from app.g1.records import (
    DecisionSnapshot,
    PredictionRealization,
    PredictionSnapshot,
    RunManifest,
)
from app.g1.store import EventStore, ImmutableRecordError

D = Decimal


def _minutes(start: datetime, count: int, skip: frozenset[int] = frozenset()):
    rows = []
    for index in range(count):
        if index in skip:
            continue
        price = D(100 + index)
        rows.append(
            minute_bar(start + index * MINUTE, price, price + 1, price - 1, price + D("0.5"))
        )
    return tuple(rows)


def _drive(bars, start: datetime, end: datetime):
    aggregator, view = Aggregator(), CausalView()
    pending = list(bars)
    emitted_log: list = []
    moment = start
    while moment < end:
        moment += MINUTE
        arrived = [b for b in pending if b.available_at == moment]
        pending = [b for b in pending if b.available_at != moment]
        emitted = aggregator.advance(moment, tuple(arrived))
        view.move_to(moment, emitted)
        emitted_log.extend((moment, bar) for bar in emitted)
    return view, emitted_log


@pytest.fixture(scope="module")
def completed_core() -> G1Core:
    bars = fixtures.minute_path()
    policy = RiskPolicy()
    manifest = run_manifest(bars, fixtures.START, fixtures.END, policy)
    core = G1Core(manifest, fixtures.scenario_step, fixtures.FUNDING_RATES, policy)
    return run_to_end(core, bars)


def test_utc_window_boundaries_including_week_and_month() -> None:
    moment = datetime(2001, 1, 31, 23, 59, tzinfo=UTC)
    assert window_start("3m", moment) == datetime(2001, 1, 31, 23, 57, tzinfo=UTC)
    assert window_start("15m", moment) == datetime(2001, 1, 31, 23, 45, tzinfo=UTC)
    assert window_start("1h", moment) == datetime(2001, 1, 31, 23, tzinfo=UTC)
    assert window_start("4h", moment) == datetime(2001, 1, 31, 20, tzinfo=UTC)
    assert window_start("1d", moment) == datetime(2001, 1, 31, tzinfo=UTC)
    # 2001-01-29 is a Monday: ISO weeks start Monday 00:00 UTC.
    assert window_start("1w", moment) == datetime(2001, 1, 29, tzinfo=UTC)
    assert window_end("1w", window_start("1w", moment)) == datetime(2001, 2, 5, tzinfo=UTC)
    assert window_start("1M", moment) == datetime(2001, 1, 1, tzinfo=UTC)
    assert window_end("1M", datetime(2001, 12, 1, tzinfo=UTC)) == datetime(2002, 1, 1, tzinfo=UTC)
    assert window_end("1M", datetime(2001, 2, 1, tzinfo=UTC)) == datetime(2001, 3, 1, tzinfo=UTC)


def test_higher_timeframe_bars_are_invisible_until_complete() -> None:
    start = datetime(2001, 1, 1, tzinfo=UTC)
    view, log = _drive(_minutes(start, 300), start, start + timedelta(minutes=300))
    for moment, bar in log:
        assert bar.available_at == bar.close_time == moment
    first_15m = next(bar for _, bar in log if bar.timeframe == "15m")
    assert first_15m.open_time == start and first_15m.available_at == start + timedelta(minutes=15)
    assert first_15m.open == D(100) and first_15m.close == D("114.5")
    assert first_15m.high == D(115) and first_15m.low == D(99) and first_15m.complete
    first_4h = [bar for _, bar in log if bar.timeframe == "4h"]
    assert len(first_4h) == 1 and first_4h[0].available_at == start + timedelta(hours=4)
    assert view.last("1d") is None  # the UTC day has not completed
    assert len(view.bars("3m")) == 100 and len(view.bars("1h")) == 5


def test_daily_weekly_monthly_boundaries_on_a_synthetic_path() -> None:
    start = datetime(2001, 1, 28, 22, tzinfo=UTC)  # Sunday evening, month end near
    minutes = 60 * 24 * 5  # through Friday 2 February
    view, _ = _drive(_minutes(start, minutes), start, start + timedelta(minutes=minutes))
    daily = view.bars("1d")
    assert [bar.open_time.day for bar in daily] == [28, 29, 30, 31, 1]
    assert daily[0].quality == "INCOMPLETE" and all(bar.complete for bar in daily[1:])
    weekly = view.bars("1w")
    # The week ending Monday 29 Jan 00:00 closes (incomplete: fixture started Sunday 22:00).
    assert len(weekly) == 1 and weekly[0].close_time == datetime(2001, 1, 29, tzinfo=UTC)
    assert weekly[0].quality == "INCOMPLETE" and weekly[0].source_minutes == 120
    monthly = view.bars("1M")
    assert len(monthly) == 1 and monthly[0].available_at == datetime(2001, 2, 1, tzinfo=UTC)
    assert monthly[0].quality == "INCOMPLETE"


def test_missing_minutes_make_the_window_incomplete_never_complete() -> None:
    start = datetime(2001, 1, 1, tzinfo=UTC)
    view, _ = _drive(_minutes(start, 30, frozenset({7})), start, start + timedelta(minutes=30))
    first, second = view.bars("15m")
    assert not first.complete and first.source_minutes == 14 and first.expected_minutes == 15
    assert second.complete


def test_future_observations_are_rejected() -> None:
    start = datetime(2001, 1, 1, tzinfo=UTC)
    bars = _minutes(start, 20)
    aggregator = Aggregator()
    with pytest.raises(FutureObservationError):
        aggregator.advance(start + timedelta(minutes=5), (bars[5],))
    view, _ = _drive(bars, start, start + timedelta(minutes=10))
    with pytest.raises(FutureObservationError):
        view.bar_closing_at("1m", start + timedelta(minutes=11))
    with pytest.raises(FutureObservationError):
        view.minute_at(start + timedelta(minutes=10))
    with pytest.raises(ValueError):
        view.move_to(start, [])  # the cursor never moves backwards
    with pytest.raises(FutureObservationError):
        CausalView().move_to(start, [bars[0]])


def test_records_are_frozen_and_the_store_is_append_only(completed_core) -> None:
    store = completed_core.store
    prediction = store.of_type(PredictionSnapshot)[40]
    with pytest.raises(dataclasses.FrozenInstanceError):
        prediction.predicted_direction = "DOWN"  # type: ignore[misc]
    forged = dataclasses.replace(prediction, mean_terminal_return=0.5)
    with pytest.raises(ImmutableRecordError):
        store.append(forged)
    assert store.append(prediction) is prediction  # identical re-issue is idempotent
    assert not hasattr(store, "update") and not hasattr(store, "delete")
    with pytest.raises(ImmutableRecordError):
        EventStore().append({"prediction_id": "x"})


def test_realization_is_a_separate_later_record(completed_core) -> None:
    store = completed_core.store
    predictions = {p.prediction_id: p for p in store.of_type(PredictionSnapshot)}
    realizations = store.of_type(PredictionRealization)
    assert realizations
    for realization in realizations:
        issued = predictions[realization.prediction_id]
        assert realization.resolution_time == issued.issue_time + timedelta(hours=4)
        assert realization.available_at == realization.resolution_time > issued.available_at
    outcome_words = ("realized", "correct", "error", "covered")
    for field in dataclasses.fields(PredictionSnapshot):
        assert not any(word in field.name for word in outcome_words), field.name


def test_every_eligible_decision_candle_has_prediction_and_decision(completed_core) -> None:
    store = completed_core.store
    decisions = store.of_type(DecisionSnapshot)
    predictions = store.of_type(PredictionSnapshot)
    expected = int((fixtures.END - fixtures.START) / timedelta(minutes=15))
    assert len(decisions) == len(predictions) == expected
    assert [d.decision_time for d in decisions] == [p.issue_time for p in predictions]
    assert {d.prediction_id for d in decisions} == {p.prediction_id for p in predictions}


def test_identities_are_content_derived_and_reproducible() -> None:
    bars = fixtures.minute_path()
    policy = RiskPolicy()
    first = run_manifest(bars, fixtures.START, fixtures.END, policy)
    second = run_manifest(bars, fixtures.START, fixtures.END, policy)
    assert isinstance(first, RunManifest) and first == second
    stressed = run_manifest(
        bars, fixtures.START, fixtures.END, RiskPolicy(operational_delay_minutes=5)
    )
    assert stressed.run_id != first.run_id and stressed.configuration_id != first.configuration_id
    assert first.evidence_class == "SYNTHETIC_FIXTURE_NOT_MARKET_EVIDENCE"
    assert first.dataset_start.year == 2001  # synthetic epoch: before BTC existed
