"""PAPER_STATISTICS_V1: counts over genuine persisted paper trades only."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import create_app
from app.product.paper import PaperTradeStore
from app.product.statistics import STATISTICS_LABEL, STATISTICS_VERSION, statistics
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def _trade(trade_id: str, status: str, net_r: float | None) -> dict:
    return {
        "trade_id": trade_id,
        "evidence_version": "FUTURE_PAPER_EVIDENCE_V1",
        "analysis_id": trade_id,
        "status": status,
        "net_r": net_r,
        "symbol": "BTCUSDT",
        "direction": "LONG",
    }


def _store(tmp_path: Path, trades: list[dict]) -> PaperTradeStore:
    store = PaperTradeStore(tmp_path / "paper" / "PAPER_TRADES_V1.json")
    store.save(trades)
    return store


def _empty_store(tmp_path: Path) -> PaperTradeStore:
    return PaperTradeStore(tmp_path / "paper" / "PAPER_TRADES_V1.json")


# --- empty state -----------------------------------------------------------------


def test_no_trades_gives_an_explicit_empty_state(tmp_path: Path) -> None:
    result = statistics(_empty_store(tmp_path))
    assert result["total_paper_trades"] == 0
    assert result["empty"] is True
    assert "No terminal paper trade" in result["empty_detail"]
    for metric in (
        "win_rate",
        "mean_realized_r",
        "cumulative_realized_r",
        "expectancy_r_per_trade",
        "max_drawdown_r",
        "best_realized_r",
        "worst_realized_r",
    ):
        assert result[metric] is None, f"{metric} must be None, never a misleading zero"


def test_only_active_trades_still_report_no_realized_metrics(tmp_path: Path) -> None:
    store = _store(tmp_path, [_trade("a", "PENDING_ENTRY", None), _trade("b", "OPEN", None)])
    result = statistics(store)
    assert result["total_paper_trades"] == 2
    assert (result["pending_entry"], result["open"], result["active"]) == (1, 1, 2)
    assert result["closed"] == 0 and result["realized_trades"] == 0
    assert result["empty"] is True
    assert result["win_rate"] is None and result["cumulative_realized_r"] is None


# --- counts and realized metrics --------------------------------------------------


def test_counts_and_realized_metrics_are_exact(tmp_path: Path) -> None:
    store = _store(
        tmp_path,
        [
            _trade("w1", "CLOSED_TARGET", 1.5),
            _trade("w2", "CLOSED_TARGET", 0.5),
            _trade("l1", "CLOSED_STOP", -1.0),
            _trade("e1", "CLOSED_EXPIRY", -0.25),
            _trade("p1", "PENDING_ENTRY", None),
            _trade("o1", "OPEN", None),
            _trade("i1", "INVALIDATED", None),
        ],
    )
    result = statistics(store)
    assert result["total_paper_trades"] == 7
    assert (result["pending_entry"], result["open"], result["active"]) == (1, 1, 2)
    assert result["closed"] == 5
    assert result["invalidated"] == 1
    assert result["closed_target"] == 2 and result["closed_stop"] == 1
    assert result["expiries"] == 1
    assert result["realized_trades"] == 4
    assert result["wins"] == 2 and result["losses"] == 2
    assert result["win_rate"] == 0.5
    assert result["cumulative_realized_r"] == 0.75
    assert result["mean_realized_r"] == 0.1875
    assert result["expectancy_r_per_trade"] == 0.1875
    assert result["best_realized_r"] == 1.5 and result["worst_realized_r"] == -1.0
    assert result["empty"] is False


def test_open_trades_never_contribute_to_realized_metrics(tmp_path: Path) -> None:
    closed_only = statistics(_store(tmp_path, [_trade("w1", "CLOSED_TARGET", 2.0)]))
    with_open = statistics(
        _store(
            tmp_path,
            [
                _trade("w1", "CLOSED_TARGET", 2.0),
                _trade("o1", "OPEN", None),
                _trade("p1", "PENDING_ENTRY", None),
            ],
        )
    )
    for metric in ("win_rate", "mean_realized_r", "cumulative_realized_r", "max_drawdown_r"):
        assert with_open[metric] == closed_only[metric]
    assert with_open["realized_trades"] == closed_only["realized_trades"] == 1
    assert with_open["total_paper_trades"] == 3


def test_an_invalidated_trade_carries_no_return(tmp_path: Path) -> None:
    result = statistics(
        _store(tmp_path, [_trade("i1", "INVALIDATED", None), _trade("w1", "CLOSED_TARGET", 1.0)])
    )
    assert result["invalidated"] == 1
    assert result["realized_trades"] == 1
    assert result["cumulative_realized_r"] == 1.0


def test_an_unresolved_closed_trade_without_r_is_not_counted(tmp_path: Path) -> None:
    result = statistics(_store(tmp_path, [_trade("x", "CLOSED_EXPIRY", None)]))
    assert result["expiries"] == 1
    assert result["realized_trades"] == 0
    assert result["cumulative_realized_r"] is None


# --- drawdown ---------------------------------------------------------------------


def test_max_drawdown_tracks_the_cumulative_curve(tmp_path: Path) -> None:
    # Equity: 2.0, 1.0, -0.5, 1.5 -> peak 2.0, trough -0.5 -> drawdown -2.5
    store = _store(
        tmp_path,
        [
            _trade("a", "CLOSED_TARGET", 2.0),
            _trade("b", "CLOSED_STOP", -1.0),
            _trade("c", "CLOSED_STOP", -1.5),
            _trade("d", "CLOSED_TARGET", 2.0),
        ],
    )
    result = statistics(store)
    assert result["cumulative_realized_r"] == 1.5
    assert result["max_drawdown_r"] == -2.5


def test_a_monotonically_rising_curve_has_no_drawdown(tmp_path: Path) -> None:
    store = _store(tmp_path, [_trade("a", "CLOSED_TARGET", 1.0), _trade("b", "CLOSED_TARGET", 2.0)])
    assert statistics(store)["max_drawdown_r"] == 0.0


def test_a_losing_first_trade_sets_the_drawdown_immediately(tmp_path: Path) -> None:
    assert (
        statistics(_store(tmp_path, [_trade("a", "CLOSED_STOP", -1.0)]))["max_drawdown_r"] == -1.0
    )


def test_statistics_are_deterministic(tmp_path: Path) -> None:
    store = _store(tmp_path, [_trade("a", "CLOSED_TARGET", 1.0), _trade("b", "CLOSED_STOP", -0.5)])
    assert statistics(store) == statistics(store)


# --- no development contamination -------------------------------------------------


def test_statistics_carry_the_future_paper_evidence_label(tmp_path: Path) -> None:
    result = statistics(_empty_store(tmp_path))
    assert result["statistics_version"] == STATISTICS_VERSION == "PAPER_STATISTICS_V1"
    assert result["label"] == STATISTICS_LABEL
    assert result["label"] == "FUTURE PAPER EVIDENCE — NOT BACKTEST PERFORMANCE"
    assert result["evidence_stage"] == "PROSPECTIVE_PAPER_RESEARCH_NOT_DEVELOPMENT_EVIDENCE"
    assert result["development_backtest_metrics_included"] is False
    assert result["champion_status"] == "NONE"
    assert result["real_money"] is False


def test_no_development_backtest_metric_can_reach_paper_statistics() -> None:
    """Structural guarantee: the module cannot even reach development evidence."""
    import ast

    source = (ROOT / "backend/app/product/statistics.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not {
        name
        for name in modules
        if any(part in name for part in ("research", "backtest", "data.store", "sealed"))
    }
    assert modules == {"typing", "__future__", "paper"}
    for forbidden in ("walk_forward", "fold", "experiment", "EXP-", "pooled", "profile_trials"):
        assert forbidden not in source.lower()
    # "backtest" may appear only in the two declarations that forbid it.
    backtest_lines = {line.strip() for line in source.splitlines() if "backtest" in line.lower()}
    assert backtest_lines == {
        "FUTURE PAPER EVIDENCE — NOT BACKTEST PERFORMANCE.",
        'STATISTICS_LABEL = "FUTURE PAPER EVIDENCE — NOT BACKTEST PERFORMANCE"',
        '"development_backtest_metrics_included": False,',
    }


def test_the_statistics_payload_exposes_no_development_metric(tmp_path: Path) -> None:
    result = statistics(_store(tmp_path, [_trade("a", "CLOSED_TARGET", 1.0)]))
    declarations = {"development_backtest_metrics_included", "label"}
    for key in set(result) - declarations:
        assert not any(
            word in key.lower()
            for word in ("backtest", "fold", "experiment", "walk_forward", "pooled")
        )
    assert result["development_backtest_metrics_included"] is False
    assert "profile_trials" not in result and "net_r_pooled" not in result


def test_statistics_read_only_the_paper_store(tmp_path: Path) -> None:
    store = _store(tmp_path, [_trade("a", "CLOSED_TARGET", 1.0)])
    before = store.path.read_bytes()
    statistics(store)
    assert store.path.read_bytes() == before


def test_scientific_counters_are_untouched_by_statistics_fixtures() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert state["paper_trades_completed"] == 0
    assert state["experiments_completed"] == 23
    assert state["champion_status"] == "NONE"
    assert state["sealed_evaluations_completed"] == 0


# --- endpoint ---------------------------------------------------------------------


def test_statistics_endpoint_serves_the_paper_surface(tmp_path: Path) -> None:
    store = _store(tmp_path, [_trade("a", "CLOSED_TARGET", 1.0), _trade("b", "OPEN", None)])
    client = TestClient(create_app(paper_store=store))
    body = client.get("/api/v1/product/paper-trades/statistics").json()
    assert body["label"] == "FUTURE PAPER EVIDENCE — NOT BACKTEST PERFORMANCE"
    assert body["total_paper_trades"] == 2
    assert body["realized_trades"] == 1
    assert body["cumulative_realized_r"] == 1.0
    assert body["active"] == 1
    assert body["real_money"] is False


def test_statistics_endpoint_is_read_only(tmp_path: Path) -> None:
    client = TestClient(create_app(paper_store=_empty_store(tmp_path)))
    assert client.post("/api/v1/product/paper-trades/statistics").status_code == 405
    assert client.get("/api/v1/product/paper-trades/statistics").json()["empty"] is True
