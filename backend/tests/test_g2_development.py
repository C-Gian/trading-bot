"""G2-02 development batch machinery (synthetic only; no market observation is opened)."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

import numpy as np
import pytest
from app.g2 import runs
from app.g2.contract import COLUMNS, PENALTIES
from app.g2.development import scoring
from app.g2.development.core import (
    ECONOMIC_WINDOW_NOT_OPEN,
    TREND_NO_SIGNAL,
    TREND_UNAVAILABLE,
    DevelopmentCore,
    trend_policy,
)
from app.g2.development.runner import as_datetime, extract, simulate
from app.g2.development.variants import (
    ABL_G2_01,
    ABL_G2_02,
    G2_V0,
    NULL,
    TREND,
    VARIANTS,
    Variant,
)
from app.g2.distribution import Distribution, ResidualArchive
from app.g2.execution import FundingBook
from app.g2.models import TrainingSet, fit_readout, fit_scaler, ridge
from app.g2.records import Decision, Prediction
from g2_support import short_built

ROOT = Path(__file__).resolve().parents[2]


def dev_core(built: runs.BuiltRun, variant: Variant, economic_start=None) -> DevelopmentCore:
    return DevelopmentCore(
        built.manifest,
        FundingBook(built.funding),
        built.spec.filters,
        built.manifest.friction,
        built.audit,
        variant,
        economic_start,
    )


@cache
def synthetic_v0() -> DevelopmentCore:
    built = runs.build(runs.synthetic_spec())
    return simulate(dev_core(built, G2_V0), built.minutes)


def test_development_core_is_byte_identical_to_the_frozen_core_for_g2_v0():
    """The G2-V0 decision/refit transcription reproduces the Gate-B synthetic fingerprint."""
    artifact = json.loads(
        (ROOT / "reports/validation/G2-01-ENGINEERING-VALIDATION-V1.json").read_text("utf-8")
    )
    assert synthetic_v0().store.fingerprint() == artifact["synthetic_run"]["fingerprint"]


def test_reconstructed_residual_sets_reproduce_every_issued_quantile():
    arrays, _ = extract(synthetic_v0())
    lo, hi = scoring.windows(arrays)
    rows = np.flatnonzero(arrays["forecast_available"])
    assert rows.size > 1000
    assert set(np.unique(arrays["residual_source"][rows])) == {1, 2}  # fallback and prequential
    report = scoring.verify_reconstruction(arrays, lo, hi, rows)
    assert report == {"checked": int(rows.size), "mismatched": 0, "bit_identical": True}


def test_windows_equal_the_residual_archive_selection():
    core = synthetic_v0()
    arrays, _ = extract(core)
    lo, hi = scoring.windows(arrays)
    archive: ResidualArchive = core.archives["FORECAST"]
    for i in np.flatnonzero(arrays["forecast_available"])[::97]:
        moment = as_datetime(int(arrays["t"][i]))
        times, values = archive.window(moment)
        assert np.array_equal(values, arrays["archive_values"][lo[i] : hi[i]])
        assert len(times) == hi[i] - lo[i]


def test_economic_gate_blocks_entries_but_not_forecasts():
    built = short_built()
    free = simulate(dev_core(built, G2_V0), built.minutes)
    gated = simulate(dev_core(built, G2_V0, built.manifest.dataset_end), built.minutes)
    assert [p for p in free.store.of_type(Prediction)] == gated.store.of_type(Prediction)
    end = built.manifest.dataset_end
    decisions = gated.store.of_type(Decision)
    before = [d for d in decisions if d.decision_time < end]
    assert before and all(ECONOMIC_WINDOW_NOT_OPEN in d.reason_codes for d in before)
    # The window opens exactly at its start instant (2021-01-01T00:00Z may trade).
    assert all(
        ECONOMIC_WINDOW_NOT_OPEN not in d.reason_codes for d in decisions if d.decision_time == end
    )
    assert all(ECONOMIC_WINDOW_NOT_OPEN not in d.reason_codes for d in free.store.of_type(Decision))


def _training(seed: int = 7, n: int = 18_000) -> TrainingSet:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, len(COLUMNS)))
    y = x @ np.linspace(-0.3, 0.4, len(COLUMNS)) + rng.normal(size=n)
    times = np.datetime64("2001-01-01T00:00") + np.arange(n) * np.timedelta64(15, "m")
    return TrainingSet(times, x, y, times + np.timedelta64(241, "m"))


def _bare(variant: Variant) -> DevelopmentCore:
    core = DevelopmentCore.__new__(DevelopmentCore)
    core.variant = variant
    core._mask = variant.mask
    return core


@pytest.mark.parametrize("variant", [ABL_G2_01, ABL_G2_02, TREND])
def test_ablation_masks_equal_a_ridge_on_the_retained_columns(variant: Variant):
    training = _training()
    scaler = fit_scaler(training.x)
    readout = _bare(variant)._fit_head(training, scaler, forecast=True)
    keep = np.array(variant.mask)
    xs = scaler.transform(training.x)[:, keep]
    penalties = tuple(p for p, k in zip(PENALTIES, keep, strict=True) if k)
    intercept, coefficients = ridge(xs, training.y, penalties)
    assert np.allclose(np.asarray(readout.coefficients)[keep], coefficients, atol=1e-12)
    assert all(c == 0.0 for c, k in zip(readout.coefficients, keep, strict=True) if not k)
    assert readout.intercept == pytest.approx(intercept, abs=1e-12)


def test_full_mask_equals_the_frozen_fit_readout():
    training = _training(11)
    scaler = fit_scaler(training.x)
    assert _bare(G2_V0)._fit_head(training, scaler, forecast=True) == fit_readout(training, scaler)


def test_null_forecast_has_location_zero():
    training = _training(3)
    scaler = fit_scaler(training.x)
    readout = _bare(NULL)._fit_head(training, scaler, forecast=True)
    assert readout.intercept == 0.0 and set(readout.coefficients) == {0.0}
    assert readout.terms(training.x[0])[2] == 0.0


def test_trend_reference_policy_rule():
    def dist(q10: float, q90: float) -> Distribution:
        return Distribution(0.0, 0.0, q10, 0.0, q90, 0.5, 100, "X")

    assert trend_policy(dist(0.001, 0.02))[0] == "LONG"
    assert trend_policy(dist(-0.02, -0.001))[0] == "SHORT"
    assert trend_policy(dist(-0.01, 0.01)) == ("NONE", [TREND_NO_SIGNAL])
    assert trend_policy(dist(0.0, 0.01)) == ("NONE", [TREND_NO_SIGNAL])  # q10 must be > 0
    assert trend_policy(None) == ("NONE", [TREND_UNAVAILABLE])


def test_batch_definitions_are_the_frozen_ones():
    assert G2_V0.active == COLUMNS and G2_V0.cycle_shadow and G2_V0.policy_mode == "UTILITY"
    assert set(COLUMNS) - set(ABL_G2_01.active) == {
        "RELATIVE_PARTICIPATION",
        "TAKER_IMBALANCE",
        "LOCAL_STRUCTURE_X_PARTICIPATION",
        "IMBALANCE_X_PRICE_RESPONSE",
    }
    assert ABL_G2_02.active == COLUMNS[:6]
    assert TREND.active == ("LOCAL_STRUCTURE", "CONTEXT_STRUCTURE", "PRICE_EXTENSION")
    assert TREND.policy_mode == "TREND_QUANTILE" and not TREND.utility_heads
    assert NULL.forecast_mode == "NULL" and NULL.policy_mode == "NONE"
    assert set(VARIANTS) == {"G2-V0", "ABL-G2-01", "ABL-G2-02", "TREND-REFERENCE", "NULL-FORECAST"}


# ---------------------------------------------------------------------- scoring math
def test_sliding_crps_equals_bruteforce_on_moving_windows():
    rng = np.random.default_rng(5)
    values = rng.standard_t(4, size=400)
    sliding = scoring.SlidingCrps(values)
    for lo, hi in ((0, 30), (5, 60), (5, 61), (40, 200), (199, 250), (250, 400)):
        sliding.move(lo, hi)
        for mu, y in ((0.0, 0.3), (0.2, -1.5), (-0.1, 5.0)):
            expected = scoring.crps_bruteforce(mu + values[lo:hi], y)
            assert sliding.crps_z(mu, y) == pytest.approx(expected, abs=1e-10)


def test_fixed_atoms_crps_equals_bruteforce_and_ties():
    atoms = np.array([0.0, 0.0, 1.0, -2.0, 3.5, 1.0])
    fixed = scoring.FixedAtoms(atoms)
    for y in (-3.0, 0.0, 1.0, 0.5, 10.0):
        assert fixed.crps_z(0.25, y) == pytest.approx(
            scoring.crps_bruteforce(0.25 + atoms, y), abs=1e-12
        )


def test_week_blocks_start_on_monday_utc():
    monday = int((np.datetime64("2021-01-04") - np.datetime64("2020-01-01")).astype(int)) * 1440
    weeks = scoring.week_index(np.array([monday - 1, monday, monday + 7 * 1440 - 1]))
    assert weeks[0] + 1 == weeks[1] == weeks[2]


def test_weekly_bootstrap_is_deterministic_and_centered_on_the_point():
    rng = np.random.default_rng(1)
    t = np.arange(0, 60 * 7 * 1440, 15)
    values = rng.normal(0.01, 1.0, size=t.size)
    weeks = scoring.week_index(t)
    first = scoring.WeeklyBootstrap(weeks).mean_distribution(values, weeks)
    second = scoring.WeeklyBootstrap(weeks).mean_distribution(values, weeks)
    assert first == second
    assert first["replicates"] == 5000 and first["seed"] == 2026092702
    assert first["p10"] < first["point"] < first["p90"]


def test_drawdown_statistics():
    t = np.arange(6) * 15
    marked = np.array([100.0, 110.0, 99.0, 104.5, 111.0, 111.0])
    stats = scoring.drawdown_stats(t, marked)
    assert stats["max_drawdown"] == pytest.approx(0.1)
    assert stats["time_under_water_fraction"] == pytest.approx(2 / 6)
