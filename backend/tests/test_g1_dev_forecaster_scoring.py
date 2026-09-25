"""System G1 Development V1: forecaster leakage/purge/shrinkage and frozen scoring/adjudication."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.g1 import scoring
from app.g1.development import ForecastRow
from app.g1.forecaster import (
    PROBABILITY_STATUS,
    SHRINKAGE_PRIOR,
    EmpiricalShrunkForecaster,
    TrainingRow,
    eligible_rows,
    prior_risk_scale,
    shrinkage_weight,
    weighted_quantile,
)
from app.g1.records import ClosedTrade, Side

UTC_ = UTC


def row(when: datetime, z: float, bias="NEUTRAL", conv="LOW") -> TrainingRow:
    return TrainingRow(when, bias, conv, z)


def test_probability_status_and_shrinkage_formula() -> None:
    assert PROBABILITY_STATUS == "EMPIRICAL_SHRUNK_CONDITIONAL_PROBABILITY_NOT_CALIBRATED"
    assert SHRINKAGE_PRIOR == 256
    assert shrinkage_weight(0) == 0 and shrinkage_weight(256) == 0.5
    assert shrinkage_weight(768) == pytest.approx(0.75)


def test_training_uses_only_prior_years_with_exact_4h_purge() -> None:
    boundary = datetime(2022, 1, 1, tzinfo=UTC)
    rows = [
        row(boundary - timedelta(hours=4), 1.0),  # target ends exactly at boundary: included
        row(boundary - timedelta(hours=4) + timedelta(minutes=15), 2.0),  # crosses: purged
        row(boundary + timedelta(minutes=15), 3.0),  # future year: excluded
        row(datetime(2021, 6, 1, tzinfo=UTC), 4.0),
    ]
    kept = eligible_rows(rows, 2022)
    assert [r.z for r in kept] == [1.0, 4.0]
    model = EmpiricalShrunkForecaster(2022, rows)
    assert sorted(model.unconditional) == [1.0, 4.0]


def test_future_year_observations_never_change_a_fitted_year() -> None:
    history = [
        row(datetime(2021, 1, 1, tzinfo=UTC) + timedelta(hours=i), (-1) ** i * 0.1 * i)
        for i in range(500)
    ]
    base = EmpiricalShrunkForecaster(2022, history).predict("NEUTRAL", "LOW", 0.02)
    polluted = history + [
        row(datetime(2022, 3, 1, tzinfo=UTC) + timedelta(hours=i), 99.0) for i in range(300)
    ]
    assert EmpiricalShrunkForecaster(2022, polluted).predict("NEUTRAL", "LOW", 0.02) == base


def test_cell_unconditional_mixture_moments_and_bounds() -> None:
    start = datetime(2021, 1, 1, tzinfo=UTC)
    cell = [row(start + timedelta(hours=i), 1.0, "BULLISH", "HIGH") for i in range(256)]
    other = [row(start + timedelta(hours=300 + i), -1.0) for i in range(256)]
    model = EmpiricalShrunkForecaster(2022, cell + other)
    forecast = model.predict("BULLISH", "HIGH", 0.02)
    # w = 256 / 512 = 0.5; unconditional is 50% +1 / 50% -1.
    assert forecast.weight == 0.5 and forecast.cell_n == 256
    assert forecast.probability_up == pytest.approx(0.5 * 1 + 0.5 * 0.5)
    assert forecast.mean_z == pytest.approx(0.5 * 1 + 0.5 * 0)
    assert forecast.mean_return == pytest.approx(0.5 * 0.02)
    assert forecast.lower_return == pytest.approx(-0.02) and forecast.upper_return == pytest.approx(
        0.02
    )
    assert forecast.median_return == pytest.approx(0.02)  # 75% mass at +1
    assert forecast.probability_up is not None and 0 <= forecast.probability_up <= 1
    assert forecast.direction == "UP"
    empty_cell = model.predict("BEARISH", "MEDIUM", 0.02)
    assert empty_cell.weight == 0 and empty_cell.probability_up == pytest.approx(0.5)
    assert empty_cell.direction == "NEUTRAL"


def test_low_support_cell_is_shrunk_towards_unconditional() -> None:
    start = datetime(2021, 1, 1, tzinfo=UTC)
    rows = [row(start + timedelta(hours=i), 5.0, "BEARISH", "HIGH") for i in range(4)]
    rows += [row(start + timedelta(hours=10 + i), 0.0 if i % 2 else -1.0) for i in range(1000)]
    forecast = EmpiricalShrunkForecaster(2022, rows).predict("BEARISH", "HIGH", 1.0)
    weight = 4 / 260
    assert forecast.weight == pytest.approx(weight)
    unconditional_mean = (4 * 5.0 + 500 * -1.0) / 1004
    assert forecast.mean_z == pytest.approx(weight * 5.0 + (1 - weight) * unconditional_mean)


def test_weighted_quantiles_are_deterministic_lower_inverse_cdf() -> None:
    atoms = [(3.0, 0.2), (1.0, 0.2), (2.0, 0.6)]
    assert weighted_quantile(atoms, 0.1) == 1.0
    assert weighted_quantile(atoms, 0.2) == 1.0
    assert weighted_quantile(atoms, 0.5) == 2.0
    assert weighted_quantile(atoms, 0.9) == 3.0
    assert weighted_quantile(list(reversed(atoms)), 0.5) == 2.0


def test_prior_risk_scale_and_unavailable_states() -> None:
    returns = [0.001 * ((-1) ** i) for i in range(96)]
    sigma = prior_risk_scale(returns)
    assert sigma == pytest.approx(0.001 * math.sqrt(96 / 95) * 4)
    assert prior_risk_scale(returns[:95]) is None
    assert prior_risk_scale([0.0] * 96) is None
    assert prior_risk_scale([*returns[:95], float("nan")]) is None
    model = EmpiricalShrunkForecaster(2022, [row(datetime(2021, 1, 1, tzinfo=UTC), 1.0)])
    assert (
        model.predict("NEUTRAL", "LOW", None).unavailable_reason == "PRIOR_RISK_SCALE_UNAVAILABLE"
    )
    assert (
        EmpiricalShrunkForecaster(2021, []).predict("NEUTRAL", "LOW", 0.02).unavailable_reason
        == "NO_TRAINING_OBSERVATIONS"
    )
    with pytest.raises(ValueError):
        EmpiricalShrunkForecaster(2022, [row(datetime(2021, 1, 1, tzinfo=UTC), 1.0, "UP", "LOW")])


# ------------------------------------------------------------------ scoring
def trade(i: int, pnl: str, year: int, side=Side.LONG, scorable=True) -> ClosedTrade:
    when = datetime(year, 3, 1, tzinfo=UTC) + timedelta(hours=6 * i)
    value = Decimal(pnl)
    return ClosedTrade(
        f"T{year}-{i}",
        f"P{i}",
        side,
        "P1",
        when,
        when + timedelta(hours=1),
        Decimal(100),
        Decimal(101),
        Decimal(100),
        Decimal(101),
        Decimal(1),
        Decimal(100),
        value,
        Decimal(0),
        Decimal(0),
        Decimal(0),
        value,
        Decimal(25),
        value / 25,
        "OBJECTIVE",
        scorable,
        60,
    )


def result(config_id: str, trades, stop=False) -> scoring.BookResult:
    return scoring.BookResult(f"{config_id}:PRIMARY", config_id, tuple(trades), len(trades), stop)


def eligible_trades(scale: str = "10"):
    good = [trade(i, scale if i % 3 else "-5", 2021) for i in range(20)]
    good += [trade(i, scale if i % 3 else "-5", 2022, Side.SHORT) for i in range(20)]
    return good


def test_trade_metrics_profit_factor_top3_and_drawdown() -> None:
    trades = [
        trade(0, "30", 2023),
        trade(1, "-10", 2023),
        trade(2, "20", 2024),
        trade(3, "-40", 2024),
        trade(4, "5", 2024),
    ]
    metrics = scoring.trade_metrics(result("S0", trades), (2023, 2024))
    assert metrics["net_pnl"] == Decimal(5)
    assert metrics["profit_factor"] == Decimal(55) / Decimal(50)
    assert metrics["net_pnl_without_top3_winners"] == Decimal(5) - Decimal(55)
    assert metrics["equity_return"]["2023"] == Decimal(20) / Decimal(10000)
    assert metrics["equity_return"]["2024"] == Decimal(-15) / Decimal(10020)
    assert metrics["max_drawdown"] == Decimal(40) / Decimal(10040)
    assert metrics["mean_net_r"] == Decimal(5) / 25 / 5


def test_unscorable_trades_reduce_coverage_and_never_count_economically() -> None:
    trades = [trade(i, "10", 2021) for i in range(19)] + [trade(99, "1000", 2021, scorable=False)]
    metrics = scoring.trade_metrics(result("S0", trades), (2021, 2022))
    assert metrics["scorable_trades"] == 19 and metrics["scorable_coverage"] == Decimal(19) / 20
    assert metrics["net_pnl"] == Decimal(190)


def test_selection_success_greatest_return_and_lexicographic_tie() -> None:
    table = scoring.phase_a_table(
        [
            result("S_FULL", eligible_trades("10")),
            result("S0", eligible_trades("20")),
            result("S_P1_ONLY", eligible_trades("20")),
            result("S_P2_ONLY", eligible_trades("50"), stop=True),  # best but ineligible
            result("S_MINUS_CYCLE", eligible_trades("10")[:30]),
        ]
    )
    assert all(table["S0"]["eligibility"].values())
    assert not table["S_P2_ONLY"]["eligibility"]["run_drawdown_stop_never_triggered"]
    assert not table["S_MINUS_CYCLE"]["eligibility"]["scorable_trades_ge_40"]
    assert scoring.select(table) == "S0"  # tie with S_P1_ONLY -> lexicographically smallest


def test_selection_rejects_when_nothing_is_eligible() -> None:
    losing = [trade(i, "-1", 2021) for i in range(20)] + [trade(i, "5", 2022) for i in range(20)]
    table = scoring.phase_a_table([result("S_FULL", losing)])
    assert not table["S_FULL"]["eligibility"]["net_pnl_2021_positive"]
    assert scoring.select(table) is None
    assert scoring.disposition(False, None, None) == scoring.REJECTED_SELECTION


def forecasts(n: int, conv="HIGH", good=True):
    rows = []
    for i in range(n):
        realized = 0.01 if i % 2 else -0.01
        p = (0.9 if realized > 0 else 0.1) if good else 0.5
        rows.append(
            ForecastRow(
                datetime(2023, 1, 1, tzinfo=UTC) + timedelta(minutes=15 * i),
                conv,
                True,
                p,
                realized / 2 if good else 0.0,
                0.5,
                realized,
                True,
            )
        )
    return rows


def test_forecast_gates_brier_and_mae_versus_baselines() -> None:
    metrics = scoring.forecast_metrics(forecasts(120) + forecasts(50, "LOW", False), (2023, 2024))
    high = metrics["by_conviction"]["HIGH"]
    assert high["valid"] == 120 and high["brier"] < high["brier_training_up_rate_baseline"]
    assert high["mae"] < high["mae_zero_return_baseline"]
    assert (
        metrics["by_conviction"]["LOW"]["valid"] == 50
        and metrics["by_conviction"]["ALL"]["valid"] == 170
    )
    weak = scoring.forecast_metrics(forecasts(120, good=False), (2023, 2024))["by_conviction"][
        "HIGH"
    ]
    assert not weak["brier"] < weak["brier_training_up_rate_baseline"]


def evaluation(primary_trades, cost_pnl="1", delay_pnl="1", fc=None, violations=False):
    years = (2023, 2024)
    primary = scoring.trade_metrics(result("S0", primary_trades), years)
    cost = scoring.trade_metrics(result("S0", [trade(0, cost_pnl, 2023)]), years)
    delay = scoring.trade_metrics(result("S0", [trade(0, delay_pnl, 2023)]), years)
    fcm = scoring.forecast_metrics(fc if fc is not None else forecasts(120), years)
    return scoring.evaluation_gates(primary, cost, delay, fcm, True, violations, years)


def strong_trades():
    out = []
    for year in (2023, 2024):
        for i in range(40):
            side = Side.LONG if i % 2 else Side.SHORT
            out.append(trade(i, "30" if i % 4 else "-12", year, side))
    return out


def test_terminal_disposition_ordering() -> None:
    gates = evaluation(strong_trades())
    assert all(all(group.values()) for group in gates.values())
    assert scoring.disposition(False, "S0", gates) == scoring.PROMOTION_ELIGIBLE
    assert scoring.disposition(True, "S0", gates) == scoring.INVALID_EXECUTION
    thin = evaluation(strong_trades()[:50])
    assert not thin["support"]["scorable_trades_ge_60"]
    assert scoring.disposition(False, "S0", thin) == scoring.INCONCLUSIVE
    stressed = evaluation(strong_trades(), cost_pnl="-1")
    assert not stressed["robustness"]["cost_48bp_net_pnl_positive"]
    assert scoring.disposition(False, "S0", stressed) == scoring.REJECTED_EVALUATION
    no_skill = evaluation(strong_trades(), fc=forecasts(120, good=False))
    assert scoring.disposition(False, "S0", no_skill) == scoring.REJECTED_EVALUATION
    few_high = evaluation(strong_trades(), fc=forecasts(99))
    assert not few_high["prediction"]["high_valid_ge_100"]
    violated = evaluation(strong_trades(), violations=True)
    assert scoring.disposition(False, "S0", violated) == scoring.INCONCLUSIVE
    assert scoring.DISPOSITION_ORDER[0] == scoring.INVALID_EXECUTION
    assert scoring.DISPOSITION_ORDER[-1] == scoring.PROMOTION_ELIGIBLE


def test_economic_gates_cover_every_frozen_condition() -> None:
    losing_long = [
        t
        if t.side is Side.SHORT
        else trade(int(t.trade_id.split("-")[1]), "-1", t.exit_time.year, Side.LONG)
        for t in strong_trades()
    ]
    gates = evaluation(losing_long)
    assert not gates["economic"]["long_net_pnl_nonnegative"]
    assert set(gates["economic"]) == {
        "equity_return_2023_positive",
        "equity_return_2024_positive",
        "mean_net_r_ge_0_10",
        "cumulative_equity_return_ge_5pct",
        "profit_factor_ge_1_15",
        "long_net_pnl_nonnegative",
        "short_net_pnl_nonnegative",
        "net_pnl_without_top3_winners_positive",
        "max_drawdown_below_5pct",
    }
    assert set(gates["robustness"]) == {
        "cost_48bp_net_pnl_positive",
        "delay_plus_5m_net_pnl_positive",
    }
    assert set(gates["prediction"]) == {
        "high_valid_ge_100",
        "high_brier_better_than_up_rate",
        "high_mae_better_than_zero_return",
    }
