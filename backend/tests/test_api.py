from datetime import UTC, datetime

import pytest
from app.data.policy import require_allowed
from app.main import app
from fastapi.testclient import TestClient


def test_health_truthful():
    r = TestClient(app).get("/api/v1/system/health")
    assert r.status_code == 200
    assert r.json()["real_money_authorized"] is False


def test_research_empty():
    assert TestClient(app).get("/api/v1/research/status").json()["experiments_completed"] == 0


def test_cutoff_guard():
    with pytest.raises(ValueError):
        require_allowed("BTCUSDT", datetime(2025, 1, 1, tzinfo=UTC))


def test_market_cutoff_guard():
    r = TestClient(app).get(
        "/api/v1/market/candles",
        params={"start": "2024-12-31T00:00:00Z", "end": "2025-01-01T00:00:00Z"},
    )
    assert r.status_code == 400
