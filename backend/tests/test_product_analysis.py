"""WP-010A: one on-demand ALIGNED paper-research analysis.

Covers NO_TRADE, LONG, fail-closed incomplete data, the absence of any real-money or
order surface, the research-status labels, and that nothing analyses on startup.
"""

from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.main import create_app
from app.product.analysis import (
    CHAMPION_STATUS,
    CLASSIFICATION,
    MAX_HOLD_MINUTES,
    RESEARCH_STATUS,
    STRATEGY_VERSION,
    VARIANT,
    analyse,
)
from app.product.features import ProspectiveFeatureSource
from app.product.market_feed import Kline, MarketFeedError, _parse, fetch_klines
from app.research.continuation import CUTOFF_US, FeatureBar, FeatureSource
from fastapi.testclient import TestClient
from state_fixtures import preserved_mechanics

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 3, 5, 12, 30, tzinfo=UTC)
SIGNAL = datetime(2026, 3, 5, 12, tzinfo=UTC)
HOUR_MS = 3_600_000
FOUR_HOUR_MS = 4 * HOUR_MS


def _hourly(*, breakout: bool, participation: bool) -> list[Kline]:
    """26 completed hourly bars ending at the bar that opens one hour before SIGNAL."""
    last_open = int(SIGNAL.timestamp() * 1000) - HOUR_MS
    bars = []
    for index in range(26):
        open_ms = last_open - (25 - index) * HOUR_MS
        bars.append(Kline(open_ms, high=100.0, low=90.0, close=95.0, volume=10.0))
    final = bars[-1]
    bars[-1] = Kline(
        final.open_ms,
        high=120.0 if breakout else 99.0,
        low=90.0,
        close=120.0 if breakout else 95.0,
        volume=40.0 if participation else 5.0,
    )
    return bars


def _context(*, persistent_up: bool) -> list[Kline]:
    """44 completed four-hour bars ending at the last one closed before SIGNAL."""
    last_open = int(SIGNAL.timestamp() * 1000) // FOUR_HOUR_MS * FOUR_HOUR_MS - FOUR_HOUR_MS
    bars = []
    for index in range(44):
        open_ms = last_open - (43 - index) * FOUR_HOUR_MS
        close = 50.0 + index if persistent_up else 50.0 + (index % 2)
        bars.append(Kline(open_ms, high=close + 5.0, low=close - 5.0, close=close, volume=10.0))
    return bars


def _feed(hourly: list[Kline], context: list[Kline]):
    def feed(interval: str, _limit: int, **_: object) -> tuple[Kline, ...]:
        return tuple(hourly if interval == "1h" else context)

    return feed


def _long_feed():
    return _feed(_hourly(breakout=True, participation=True), _context(persistent_up=True))


def _no_trade_feed():
    return _feed(_hourly(breakout=False, participation=False), _context(persistent_up=False))


# --- decisions -------------------------------------------------------------------


def test_no_trade_when_the_frozen_gates_do_not_all_fire() -> None:
    result = analyse(now=NOW, feed=_no_trade_feed())
    assert result["data_status"] == "OK"
    assert result["decision"] == "NO_TRADE"
    assert result["plan"] is None
    assert result["symbol"] == "BTCUSDT"
    assert result["signal_time"] == "2026-03-05T12:00:00Z"


def test_long_plan_uses_the_frozen_stop_target_entry_and_horizon() -> None:
    result = analyse(now=NOW, feed=_long_feed())
    assert result["data_status"] == "OK"
    assert result["decision"] == "LONG"
    plan = result["plan"]
    assert plan is not None
    assert result["reference_price"] == plan["reference_price"] == 120.0
    assert plan["stop_price"] == pytest.approx(120.0 * 0.98)
    assert plan["target_price"] == pytest.approx(120.0 * 1.04)
    assert (plan["stop_fraction"], plan["target_fraction"]) == (0.02, 0.04)
    assert plan["entry_rule"] == "STRICTLY_AFTER_DURABLE_INTENT_NEXT_1M_OPEN"
    assert plan["execution_model"] == "EXECUTION_MODEL_V2"
    assert plan["exit_policy"] == "FIXED_TARGET_OR_STOP_OR_24H"
    assert plan["direction"] == "LONG"
    assert plan["max_hold_minutes"] == MAX_HOLD_MINUTES == 1440
    assert plan["expiry_time"] == (SIGNAL + timedelta(minutes=1440)).isoformat().replace(
        "+00:00", "Z"
    )
    assert plan["leverage"] is False and plan["short"] is False
    assert plan["order_placed"] is False


def test_analysis_is_deterministic_for_the_same_inputs() -> None:
    feed = _long_feed()
    assert analyse(now=NOW, feed=feed) == analyse(now=NOW, feed=feed)


# --- fail closed -----------------------------------------------------------------


def test_incomplete_market_data_fails_closed_to_no_trade() -> None:
    short_hourly = _hourly(breakout=True, participation=True)[6:]
    result = analyse(now=NOW, feed=_feed(short_hourly, _context(persistent_up=True)))
    assert result["decision"] == "NO_TRADE"
    assert result["plan"] is None
    assert result["data_status"] == "INCOMPLETE_MARKET_DATA"


def test_a_gap_in_the_lookback_fails_closed_to_no_trade() -> None:
    hourly = _hourly(breakout=True, participation=True)
    hourly.pop(10)
    result = analyse(now=NOW, feed=_feed(hourly, _context(persistent_up=True)))
    assert result["decision"] == "NO_TRADE"
    assert result["plan"] is None
    assert result["data_status"] == "INCOMPLETE_MARKET_DATA"


def test_an_unavailable_market_feed_fails_closed_to_no_trade() -> None:
    def failing(*_: object, **__: object) -> tuple[Kline, ...]:
        raise MarketFeedError("market feed transport failure: offline")

    result = analyse(now=NOW, feed=failing)
    assert result["decision"] == "NO_TRADE"
    assert result["plan"] is None
    assert result["data_status"] == "MARKET_DATA_UNAVAILABLE"


def test_incomplete_current_bars_are_never_used() -> None:
    now_ms = int(NOW.timestamp() * 1000)
    closed = int(SIGNAL.timestamp() * 1000) - HOUR_MS
    rows = [
        [closed, "1", "2", "0.5", "1.5", "3"],
        [closed + HOUR_MS, "1", "2", "0.5", "1.5", "3"],
        [closed + 2 * HOUR_MS, "1", "2", "0.5", "1.5", "3"],
    ]
    # Only the 11:00-12:00 bar has closed by 12:30; the in-progress and future bars are dropped.
    parsed = _parse(rows, "1h", now_ms)
    assert [kline.open_ms for kline in parsed] == [closed]


def test_market_feed_rejects_malformed_or_unaligned_payloads() -> None:
    now_ms = int(NOW.timestamp() * 1000)
    with pytest.raises(MarketFeedError, match="unexpected payload"):
        _parse({"error": "nope"}, "1h", now_ms)
    with pytest.raises(MarketFeedError, match="malformed"):
        _parse([["x", "1", "2", "3", "4", "5"]], "1h", now_ms)
    with pytest.raises(MarketFeedError, match="unaligned"):
        _parse(
            [[int(SIGNAL.timestamp() * 1000) - HOUR_MS + 1, "1", "2", "3", "4", "5"]], "1h", now_ms
        )


def test_market_feed_rejects_a_non_200_response() -> None:
    class _Client:
        @staticmethod
        def get(*_: object, **__: object):
            class _Response:
                status_code = 503

            return _Response()

    with pytest.raises(MarketFeedError, match="status 503"):
        fetch_klines("1h", 48, now=NOW, client=_Client())


# --- scientific separation -------------------------------------------------------


def test_the_frozen_aligned_implementation_is_used_unmodified() -> None:
    """continuation.py is hash-frozen by the committed novelty admission."""
    source = (ROOT / "backend/app/research/continuation.py").read_text(encoding="utf-8")
    assert 'CUTOFF_US = utc_us("2024-12-31T23:59:00Z")' in source
    assert "scope" not in source
    bar = FeatureBar(CUTOFF_US + 3_600_000_000, 10.0, 9.0, 1.0, True)
    with pytest.raises(ValueError, match="development instants"):
        FeatureSource((bar,), ())


def test_no_timestamp_translation_remains_in_the_product_path() -> None:
    for name in ("analysis.py", "paper.py", "features.py", "execution.py"):
        source = (ROOT / "backend/app/product" / name).read_text(encoding="utf-8")
        assert "clock_shift_us" not in source
        assert "ANCHOR_US" not in source
        if name in {"analysis.py", "paper.py"}:
            assert "FeatureSource(" not in source or "ProspectiveFeatureSource(" in source


def test_analysis_evaluates_real_post_cutoff_instants_end_to_end() -> None:
    result = analyse(now=NOW, feed=_long_feed())
    assert result["signal_time"] == "2026-03-05T12:00:00Z"
    assert result["prospective_features_version"] == "PROSPECTIVE_PAPER_FEATURES_V1"
    assert result["feature_version"] == "CONTINUATION_FEATURES_V2"
    signal_us = int(SIGNAL.timestamp()) * 1_000_000
    assert signal_us > CUTOFF_US
    direct = ProspectiveFeatureSource(
        tuple(
            FeatureBar(k.open_ms * 1000, k.high, k.close, k.volume)
            for k in _hourly(breakout=True, participation=True)
        ),
        tuple(
            FeatureBar(k.open_ms * 1000, k.high, k.close, k.volume)
            for k in _context(persistent_up=True)
        ),
    ).decision(signal_us, VARIANT)
    assert direct[0] is True
    assert result["reference_price"] == direct[2]


def test_the_product_path_never_writes_or_reads_development_storage() -> None:
    for name in ("analysis.py", "market_feed.py", "__init__.py"):
        source = (ROOT / "backend/app/product" / name).read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert not modules & {"app.data.store", "app.backtest", "app.sealed", ".data.store"}
        assert "data/canonical" not in source and "data/derived" not in source
        assert "write_text" not in source and "write_bytes" not in source


def test_the_product_path_carries_no_credential_or_order_surface() -> None:
    for name in ("analysis.py", "market_feed.py"):
        source = (ROOT / "backend/app/product" / name).read_text(encoding="utf-8").lower()
        for forbidden in ("api_key", "apikey", "secret", "signature", "hmac", "/order", "withdraw"):
            assert forbidden not in source


# --- endpoint --------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    return TestClient(
        create_app(**preserved_mechanics(), analyser=lambda: analyse(now=NOW, feed=_long_feed()))
    )


def test_endpoint_returns_a_labelled_paper_research_long_plan(client: TestClient) -> None:
    response = client.post("/api/v1/product/analysis")
    assert response.status_code == 200
    body = response.json()
    assert body["classification"] == CLASSIFICATION
    assert "NOT AN APPROVED LIVE STRATEGY" in body["classification"]
    assert body["research_status"] == RESEARCH_STATUS == "PAPER_RESEARCH_CANDIDATE"
    assert body["strategy_version"] == STRATEGY_VERSION
    assert body["variant"] == VARIANT == "ALIGNED"
    assert body["champion_status"] == CHAMPION_STATUS == "NONE"
    assert body["decision"] == "LONG"
    assert body["paper_trade_persisted"] is False
    assert body["paper_trades_completed"] == 0
    assert body["real_money"] is False and body["real_money_authorized"] is False
    bundle = json.loads(body["review_bundle"])
    assert bundle["bundle_version"] == "DASHBOARD_ANALYSIS_REVIEW_BUNDLE_V1"
    assert bundle["decision"] == "LONG"
    assert bundle["paper_trade"] is None
    assert "entry_price" not in bundle and "stop_price" not in bundle


def test_endpoint_returns_no_trade_without_a_plan() -> None:
    app = create_app(
        **preserved_mechanics(), analyser=lambda: analyse(now=NOW, feed=_no_trade_feed())
    )
    body = TestClient(app).post("/api/v1/product/analysis").json()
    assert body["decision"] == "NO_TRADE" and body["plan"] is None
    assert body["research_status"] == "PAPER_RESEARCH_CANDIDATE"
    bundle = json.loads(body["review_bundle"])
    assert bundle["decision"] == "NO_TRADE" and bundle["paper_trade"] is None


def test_analysis_runs_only_on_explicit_request(client: TestClient) -> None:
    calls: list[int] = []

    def counting() -> dict:
        calls.append(1)
        return analyse(now=NOW, feed=_long_feed())

    app = create_app(**preserved_mechanics(), analyser=counting)
    with TestClient(app) as started:
        assert calls == []
        for path in ("/api/v1/system/health", "/api/v1/state", "/api/v1/research/status"):
            started.get(path)
        assert calls == []
        assert started.post("/api/v1/product/analysis").status_code == 200
        assert calls == [1]


def test_analysis_is_not_reachable_by_get(client: TestClient) -> None:
    assert client.get("/api/v1/product/analysis").status_code == 405


def test_capability_declares_causal_persistence_but_no_order_or_real_money(
    client: TestClient,
) -> None:
    body = client.get("/api/v1/product/analysis/capability").json()
    assert body["surface"] == "AVAILABLE"
    assert body["trigger"] == "EXPLICIT_USER_ACTION_ONLY"
    assert body["research_status"] == "PAPER_RESEARCH_CANDIDATE"
    assert body["champion_status"] == "NONE"
    assert body["paper_trade_persistence"] is True
    assert body["order_placement"] is False
    assert body["real_money_authorized"] is False


def test_no_order_execution_or_credential_endpoint_exists(client: TestClient) -> None:
    paths = {getattr(route, "path", "") for route in create_app().routes}
    assert not [
        path
        for path in paths
        if any(
            word in path.lower()
            for word in ("order", "trade/execute", "key", "credential", "withdraw", "live")
        )
    ]
    for path in ("/api/v1/product/order", "/api/v1/trade/execute", "/api/v1/credentials"):
        assert client.post(path).status_code == 404
