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
from .product.analysis import RESEARCH_STATUS, STRATEGY_VERSION, VARIANT, analyse
from .product.paper import (
    STORE_PATH,
    PaperTradeError,
    PaperTradeStore,
    create_from_analysis,
    listing,
    update_lifecycle,
)
from .research.checkpoint_views import budget_view, experiment_view
from .research.wp006_views import v2_budget_view
from .sealed import public_status
from .state import StateRepository


def create_app(
    state_path: Path | None = None,
    data_probe: Callable[[], bool] = available,
    research_summary_path: Path | None = None,
    analyser: Callable[[], dict] = analyse,
    paper_store: PaperTradeStore | None = None,
    lifecycle: Callable[[PaperTradeStore], dict] = update_lifecycle,
) -> FastAPI:
    application = FastAPI(title="Trading Bot", version=__version__)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    repository = StateRepository(state_path)
    trades = paper_store or PaperTradeStore(Path(__file__).resolve().parents[2] / STORE_PATH)

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
            "wp005_integrity": state.get("wp005_integrity"),
            "remote_ci": state.get("remote_ci"),
            "latest_family": state.get("latest_family"),
            "order_flow_substrate": state.get("order_flow_substrate"),
            "artifact_storage": state.get("artifact_storage"),
            "supervised_challenger": state.get("supervised_challenger"),
            "exogenous_foundation": state.get("exogenous_foundation"),
            "sealed_evaluation": state.get("sealed_evaluation"),
            "sealed_system": public_status(),
            "family_budgets": budget_view() + v2_budget_view(),
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

    @application.post("/api/v1/product/analysis")
    def product_analysis(repo: StateRepository = Depends(state_repository)):
        """One on-demand paper-research analysis. Explicit user action only.

        Never runs on startup, never persists a paper trade, and never places an order.
        """
        state = repo.load()
        if state["real_money_authorized"]:
            raise HTTPException(409, "real-money authorization is not supported by this surface")
        result = analyser()
        return {
            **result,
            "champion_status": state["champion_status"],
            "paper_trades_completed": state["paper_trades_completed"],
            "real_money_authorized": state["real_money_authorized"],
        }

    @application.get("/api/v1/product/analysis/capability")
    def product_analysis_capability(repo: StateRepository = Depends(state_repository)):
        state = repo.load()
        return {
            "surface": state.get("product_analysis", {}).get("surface", "UNAVAILABLE"),
            "trigger": "EXPLICIT_USER_ACTION_ONLY",
            "strategy_version": STRATEGY_VERSION,
            "variant": VARIANT,
            "research_status": RESEARCH_STATUS,
            "champion_status": state["champion_status"],
            "paper_trade_persistence": False,
            "order_placement": False,
            "real_money_authorized": state["real_money_authorized"],
        }

    @application.post("/api/v1/product/paper-trades")
    def create_paper_trade(repo: StateRepository = Depends(state_repository)):
        """Create one paper trade from a freshly evaluated LONG analysis.

        The plan is never supplied by the caller, so no price or geometry can be forged.
        """
        state = repo.load()
        if state["real_money_authorized"]:
            raise HTTPException(409, "real-money authorization is not supported by this surface")
        analysis = analyser()
        try:
            trade = create_from_analysis(analysis, trades)
        except PaperTradeError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"analysis_id": analysis["analysis_id"], "trade": trade, "real_money": False}

    @application.get("/api/v1/product/paper-trades")
    def read_paper_trades(limit: int = 20):
        return listing(trades, limit=max(1, min(limit, 100)))

    @application.post("/api/v1/product/paper-trades/lifecycle")
    def advance_paper_trades(repo: StateRepository = Depends(state_repository)):
        """Explicit lifecycle update only; nothing advances in the background."""
        state = repo.load()
        if state["real_money_authorized"]:
            raise HTTPException(409, "real-money authorization is not supported by this surface")
        return lifecycle(trades)

    return application


app = create_app()

__all__ = ["COST_VERSION", "ENGINE_VERSION", "EXECUTION_VERSION", "app", "create_app"]
