from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .backtest import COST_VERSION, ENGINE_VERSION, EXECUTION_VERSION
from .data.store import available, candles
from .research.checkpoint_views import budget_view, experiment_view
from .state import StateRepository


def create_app(
    state_path: Path | None = None,
    data_probe: Callable[[], bool] = available,
    research_summary_path: Path | None = None,
) -> FastAPI:
    application = FastAPI(title="Trading Bot", version=__version__)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    repository = StateRepository(state_path)

    def state_repository() -> StateRepository:
        return repository

    @application.get("/api/v1/state")
    def current_state(repo: StateRepository = Depends(state_repository)):
        return repo.load()

    @application.get("/api/v1/system/health")
    def health(repo: StateRepository = Depends(state_repository)):
        state = repo.load()
        return {
            "service": "trading-bot",
            "health": "ok",
            "software_version": __version__,
            "project_phase": state["project_phase"],
            "status": state["status"],
            "paper_only": not state["real_money_authorized"],
            "real_money_authorized": state["real_money_authorized"],
            "development_data_available": data_probe(),
            "development_cutoff": state["development_cutoff"],
            "development_coverage": state["development_dataset"]["coverage"],
        }

    @application.get("/api/v1/research/status")
    def research_status(repo: StateRepository = Depends(state_repository)):
        state = repo.load()
        substrate = state["backtest_substrate"]
        return {
            "champion": state["champion_status"],
            "experiments_completed": state["experiments_completed"],
            "evidence": state["forward_evidence"],
            "backtest_substrate": substrate["status"],
            "engine_version": substrate["engine_version"],
            "execution_model_version": substrate["execution_model_version"],
            "cost_model_version": substrate["cost_model_version"],
            "synthetic_validation": substrate["synthetic_validation"]["status"],
            "search_memory": state.get("search_memory"),
            "adaptive_search": state.get("adaptive_search"),
            "selected_family": state.get("selected_family"),
            "family_budgets": budget_view(),
        }

    @application.get("/api/v1/backtest/substrate")
    def substrate_status(repo: StateRepository = Depends(state_repository)):
        return repo.load()["backtest_substrate"]

    @application.get("/api/v1/research/experiments")
    def research_experiments(repo: StateRepository = Depends(state_repository)):
        if research_summary_path is None:
            return experiment_view(state=repo.load())
        if not research_summary_path.is_file():
            return {"evidence_stage": "NONE", "experiments": []}
        return json.loads(research_summary_path.read_text(encoding="utf-8"))

    @application.get("/api/v1/market/candles")
    def market_candles(
        symbol: str = "BTCUSDT",
        timeframe: str = "1h",
        start: datetime = Query(...),
        end: datetime = Query(...),
        limit: int = 1000,
        repo: StateRepository = Depends(state_repository),
    ):
        state = repo.load()
        try:
            rows = candles(symbol, timeframe, start, end, limit)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(400, str(exc)) from exc
        return {
            "classification": "HISTORICAL DEVELOPMENT DATA — NOT CURRENT MARKET",
            "symbol": symbol,
            "timeframe": timeframe,
            "coverage": state["development_dataset"]["coverage"],
            "cutoff": state["development_cutoff"],
            "candles": rows,
        }

    return application


app = create_app()

__all__ = ["COST_VERSION", "ENGINE_VERSION", "EXECUTION_VERSION", "app", "create_app"]
