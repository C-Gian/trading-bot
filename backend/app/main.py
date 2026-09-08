from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .data.policy import CUTOFF
from .data.store import available, candles

app = FastAPI(title="Trading Bot", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/v1/system/health")
def health():
    return {
        "service": "trading-bot",
        "health": "ok",
        "software_version": __version__,
        "project_phase": "FOUNDATION_DATA",
        "status": "READY" if available() else "DATA_PENDING",
        "paper_only": True,
        "real_money_authorized": False,
        "development_data_available": available(),
        "development_cutoff": CUTOFF.isoformat().replace("+00:00", "Z"),
    }


@app.get("/api/v1/research/status")
def research_status():
    return {"champion": "NONE", "experiments_completed": 0, "evidence": "NONE"}


@app.get("/api/v1/market/candles")
def market_candles(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    start: datetime = Query(...),
    end: datetime = Query(...),
    limit: int = 1000,
):
    try:
        rows = candles(symbol, timeframe, start, end, limit)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "classification": "HISTORICAL DEVELOPMENT DATA — NOT CURRENT MARKET",
        "symbol": symbol,
        "timeframe": timeframe,
        "cutoff": CUTOFF.isoformat().replace("+00:00", "Z"),
        "candles": rows,
    }
