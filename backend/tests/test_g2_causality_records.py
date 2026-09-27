"""G2-01 causality, replay determinism and immutable-record acceptance tests."""

from __future__ import annotations

import dataclasses
from datetime import timedelta

import pytest
from app.g1.canonical import canonical_bytes as g1_canonical_bytes
from app.g2 import runs
from app.g2.bars import Aggregator, FutureObservationError, MinuteTape, completed_bars
from app.g2.records import (
    ClosedTrade,
    CycleShadowState,
    Decision,
    FundingEvent,
    MarketState,
    Prediction,
    PredictionOutcome,
    Reason,
    ShadowLabel,
    SimulatedFill,
    StopExpiryEvent,
)
from app.g2.store import G2Store, ImmutableRecordError, canonical_bytes
from g2_support import MINUTE, T0, flat_minutes, full_run, short_built


def test_completed_bars_are_emitted_only_at_close_and_incomplete_is_flagged():
    minutes = flat_minutes(T0, 60)
    aggregator = Aggregator(("15m", "1h"))
    emitted = []
    for m in minutes[:14]:
        emitted.extend(aggregator.add(m))
    assert emitted == []  # the 15m window [T0, T0+15m) has not closed
    assert aggregator.close_until(T0 + 14 * MINUTE) == []
    emitted.extend(aggregator.add(minutes[14]))
    closed = aggregator.close_until(T0 + 15 * MINUTE)
    assert [b.timeframe for b in closed] == ["15m"] and closed[0].available_at == T0 + 15 * MINUTE
    gap = [m for m in minutes if m.open_time != T0 + 20 * MINUTE]
    bars = completed_bars(gap, "15m")
    assert [b.complete for b in bars] == [True, False, True, True]
    hourly = completed_bars(gap, "1h")
    assert len(hourly) == 1 and not hourly[0].complete


def test_minute_tape_refuses_reads_beyond_the_cursor():
    tape = MinuteTape(T0, 60)
    for m in flat_minutes(T0, 60):
        tape.put(m)
    tape.advance(T0 + 10 * MINUTE)
    assert tape.minute(T0 + 9 * MINUTE) is not None
    with pytest.raises(FutureObservationError):
        tape.minute(T0 + 10 * MINUTE)
    with pytest.raises(FutureObservationError):
        tape.window(T0, T0 + 30 * MINUTE)


def test_state_never_consumes_a_source_after_its_decision_instant():
    for state in full_run().core.store.of_type(MarketState):
        assert state.max_source_time is None or state.max_source_time <= state.decision_time
    for prediction in full_run().core.store.of_type(Prediction):
        assert prediction.max_source_time is None or (
            prediction.max_source_time <= prediction.decision_time
        )


def test_continuous_prediction_and_decision_on_every_eligible_candle():
    run = full_run()
    store = run.core.store
    predictions, decisions = store.of_type(Prediction), store.of_type(Decision)
    start, end = run.built.manifest.dataset_start, run.built.manifest.dataset_end
    expected = int((end - start) // timedelta(minutes=15))
    assert len(predictions) == len(decisions) == expected
    assert [p.decision_time for p in predictions] == [
        start + (k + 1) * timedelta(minutes=15) for k in range(expected)
    ]
    reasons = {r for p in predictions for r in p.reason_codes}
    for code in (
        Reason.FORECAST_AVAILABLE,
        Reason.FORECAST_UNAVAILABLE_WARMUP,
        Reason.FORECAST_UNAVAILABLE_MISSING_DATA,
        Reason.FORECAST_UNAVAILABLE_NO_MODEL,
        Reason.TRAINING_TARGET_BASELINE_UNVALIDATED,
        Reason.PREQUENTIAL_CDF_UNCALIBRATED,
    ):
        assert str(code) in reasons, code


def records_until(core, cursor):
    return [canonical_bytes(r) for r in core.store if r.available_at <= cursor]


def test_prefix_invariance_of_every_record():
    built = short_built()
    full = runs.run_batch(built)
    for cut in (timedelta(days=5, minutes=7), timedelta(days=17, hours=3)):
        cursor = built.manifest.dataset_start + cut
        prefix = runs.run_batch(built, cursor)
        assert records_until(prefix, cursor) == records_until(full, cursor)


def test_replay_speed_identity_and_deterministic_hash():
    built = short_built()
    reference = runs.run_batch(built).store.fingerprint()
    for step in (timedelta(minutes=37), timedelta(days=1)):
        assert runs.run_in_steps(built, step).store.fingerprint() == reference
    again = runs.build(built.spec)
    assert again.manifest.run_id == built.manifest.run_id
    assert runs.run_batch(again).store.fingerprint() == reference


def test_records_are_immutable_and_the_store_is_append_only():
    store = full_run().core.store
    prediction = store.of_type(Prediction)[-100]
    with pytest.raises(dataclasses.FrozenInstanceError):
        prediction.median_return = 0.0  # type: ignore[misc]
    fresh = G2Store()
    fresh.append(prediction)
    fresh.append(prediction)  # byte-identical re-issue is idempotent
    with pytest.raises(ImmutableRecordError):
        fresh.append(
            dataclasses.replace(
                prediction, direction="UP" if prediction.direction != "UP" else "DOWN"
            )
        )
    assert not hasattr(fresh, "update") and not hasattr(fresh, "delete")
    # outcomes append as separate records; the original prediction is never rewritten
    assert all(p.maturity_status == "PENDING" for p in store.of_type(Prediction))
    outcomes = store.of_type(PredictionOutcome)
    assert outcomes and all(o.available_at == o.target_time for o in outcomes)


def test_canonical_hash_is_stable_and_matches_the_g1_canonical_form():
    store = full_run().core.store
    for kind in (Prediction, Decision, ShadowLabel, CycleShadowState, MarketState):
        for record in store.of_type(kind)[-3:]:
            assert canonical_bytes(record) == g1_canonical_bytes(record)
    assert full_run().fingerprint == store.fingerprint()


def test_reason_codes_are_canonical():
    canonical = {str(code) for code in Reason}
    store = full_run().core.store
    for kind in (
        Prediction,
        Decision,
        MarketState,
        ShadowLabel,
        SimulatedFill,
        FundingEvent,
        StopExpiryEvent,
        CycleShadowState,
    ):
        for record in store.of_type(kind):
            assert set(record.reason_codes) <= canonical, (kind, record.reason_codes)
    for trade in store.of_type(ClosedTrade):
        assert set(trade.violation_flags) <= canonical


def test_cycle_state_is_shadow_only_in_every_decision():
    store = full_run().core.store
    cycles = store.of_type(CycleShadowState)
    assert len(cycles) == len(store.of_type(Decision))
    for cycle in cycles:
        assert cycle.runtime_role == "SHADOW_ONLY"
        assert cycle.forecast_coefficients == 0 and cycle.policy_coefficients == 0
        assert cycle.veto_authority == "NONE" and "CYCLE_SHADOW_ONLY" in cycle.reason_codes
    usable = [s for c in cycles for s in c.scales if s.quality_label == "USABLE"]
    assert usable, "the synthetic path should produce some USABLE shadow scales"
