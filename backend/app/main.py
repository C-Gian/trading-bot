from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from . import __version__
from .backtest import COST_VERSION, ENGINE_VERSION, EXECUTION_VERSION
from .data.store import available, candles
from .g1.api import g1_router
from .g1.service import G1ReplayService
from .product.analysis import RESEARCH_STATUS, STRATEGY_VERSION, VARIANT, analyse
from .product.analysis_review import build_analysis_review_bundle
from .product.market_feed import recent_candles
from .product.paper_v2 import (
    STORE_PATH,
    PaperTradeError,
    PaperTradeStore,
    create_from_analysis,
    listing,
    update_lifecycle,
)
from .product.shadow_observer import (
    AUTOMATIC_COLLECTION_ENABLED,
    AUTOMATIC_COLLECTION_STATUS,
    OBSERVER_VERSION,
    default_observer,
)
from .product.shadow_observer import (
    EVIDENCE_STAGE as SHADOW_EVIDENCE_STAGE,
)
from .product.shadow_observer import (
    EVIDENCE_VERSION as SHADOW_EVIDENCE_VERSION,
)
from .product.shadow_observer import (
    INITIATION_MODE as SHADOW_INITIATION_MODE,
)
from .product.statistics import statistics
from .research.checkpoint_views import budget_view, experiment_view
from .research.local_runner import (
    CandidateGateError,
    LocalResearchRunner,
    RequiredDataError,
    RunConflictError,
    RunNotFoundError,
    UnknownCandidateError,
    default_runner,
)
from .research.wp006_views import v2_budget_view
from .sealed import public_status
from .state import StateRepository

# Fail-closed action guard (System G1 Checkpoint 1, superseding the ADR-0042 PARKED check).
# The guard depends only on `current_project_status.validated_strategy`: while it is null (or the
# canonical status block is absent) no historical strategy — ALIGNED or any predictive family — is
# evaluated, the action output is NO_TRADE, paper-trade creation is disabled and the legacy research
# runner cannot start. A change of strategic disposition can never re-enable a historical fallback.
PARKED_DISPOSITION = "PARKED_NO_CREDIBLE_EDGE_UNDER_CURRENT_CONSTRAINTS"
FAIL_CLOSED_DATA_STATUS = "NO_VALIDATED_STRATEGY"
FAIL_CLOSED_RESEARCH_STATUS = "DEVELOPMENT_NO_VALIDATED_STRATEGY"
FAIL_CLOSED_DETAIL = (
    "No validated strategy exists (System G1 is in synthetic development), so the honest "
    "action output is NO_TRADE."
)
RUNNER_DISABLED_DETAIL = (
    "the legacy local research runner is disabled until a future task explicitly authorizes it"
)


def validated_strategy(state: dict[str, Any]) -> Any:
    """The validated strategy identity, or None. A missing status block is never validated."""
    return state.get("current_project_status", {}).get("validated_strategy")


def fail_closed(state: dict[str, Any]) -> bool:
    return validated_strategy(state) is None


def legacy_runner_authorized(state: dict[str, Any]) -> bool:
    """Only an explicit future authorization flag reopens the legacy research runner."""
    return state.get("current_project_status", {}).get("legacy_research_runner_authorized") is True


def fail_closed_analysis(state: dict[str, Any]) -> dict[str, Any]:
    """The fail-closed action output: NO_TRADE, no plan, without evaluating any strategy."""
    current = state.get("current_project_status", {})
    return {
        "analysis_version": "FAIL_CLOSED_NO_TRADE_V2",
        "classification": "NO_VALIDATED_STRATEGY",
        "symbol": "BTCUSDT",
        "strategy_version": "NONE",
        "variant": "NONE",
        "feature_version": "NONE",
        "research_status": FAIL_CLOSED_RESEARCH_STATUS,
        "champion_status": state["champion_status"],
        "project_disposition": current.get("disposition"),
        "active_system_generation": current.get("active_system_generation"),
        "analysis_time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "signal_time": None,
        "data_status": FAIL_CLOSED_DATA_STATUS,
        "data_detail": FAIL_CLOSED_DETAIL,
        "decision": "NO_TRADE",
        "plan": None,
        "paper_trade_persisted": False,
        "real_money": False,
    }


class ResearchRunRequest(BaseModel):
    """The only caller-controlled field is one allowlisted candidate identity."""

    model_config = ConfigDict(extra="forbid")
    candidate_id: str


class PaperTradeCreateRequest(BaseModel):
    """Creation accepts no client-owned decision, price, plan, or timestamp field."""

    model_config = ConfigDict(extra="forbid")


def create_app(
    state_path: Path | None = None,
    data_probe: Callable[[], bool] = available,
    research_summary_path: Path | None = None,
    analyser: Callable[[], dict] = analyse,
    paper_store: Any | None = None,
    lifecycle: Callable[[Any], dict] = update_lifecycle,
    market_view: Callable[[], dict] = recent_candles,
    research_runner: LocalResearchRunner | None = None,
    shadow_observer: Any | None = None,
    state_schema_path: Path | None = None,
    g1_service: G1ReplayService | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if shadow_observer is not None:
            shadow_observer.start()
        try:
            yield
        finally:
            if shadow_observer is not None:
                shadow_observer.stop()

    application = FastAPI(title="Trading Bot", version=__version__, lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    repository = StateRepository(state_path, state_schema_path)
    trades = paper_store or PaperTradeStore(Path(__file__).resolve().parents[2] / STORE_PATH)
    local_runner = research_runner or default_runner()
    # ADR-0026: automatic ALIGNED prospective collection is suspended on ``main``. An
    # explicitly injected observer — tests, or a future Owner-authorized revival — reports
    # its own live status instead of the suspension.
    collection_status = "ACTIVE" if shadow_observer is not None else AUTOMATIC_COLLECTION_STATUS

    def state_repository() -> StateRepository:
        return repository

    # System G1 Checkpoint 1: the synthetic replay slice. It never touches the fail-closed
    # production action surface above, which stays NO_TRADE while no strategy is validated.
    application.router.routes.extend(
        g1_router(g1_service or G1ReplayService(), repository.load).routes
    )

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

    @application.get("/api/v1/research/runner")
    def research_runner_status():
        """List only source-controlled candidates and persisted local runtime state."""
        return local_runner.overview()

    @application.post("/api/v1/research/runner/runs", status_code=202)
    def start_research_run(
        request: ResearchRunRequest, repo: StateRepository = Depends(state_repository)
    ):
        """Start one fixed local research adapter after an explicit Owner action.

        This route cannot accept commands, paths, parameters, credentials, or trading
        instructions and never updates canonical scientific or paper-trade state.
        """
        state = repo.load()
        if state["real_money_authorized"]:
            raise HTTPException(409, "local research is disabled if real money is authorized")
        if not legacy_runner_authorized(state):
            raise HTTPException(409, RUNNER_DISABLED_DETAIL)
        try:
            return local_runner.start(request.candidate_id)
        except UnknownCandidateError as exc:
            raise HTTPException(404, str(exc)) from exc
        except (CandidateGateError, RequiredDataError, RunConflictError) as exc:
            raise HTTPException(409, str(exc)) from exc

    @application.get("/api/v1/research/runner/runs/{run_id}")
    def research_run(run_id: str):
        try:
            return local_runner.read(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc

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
        result = fail_closed_analysis(state) if fail_closed(state) else analyser()
        response = {
            **result,
            "champion_status": state["champion_status"],
            "paper_trades_completed": state["paper_trades_completed"],
            "real_money_authorized": state["real_money_authorized"],
        }
        response["review_bundle"] = build_analysis_review_bundle(response, trades.load())
        return response

    @application.get("/api/v1/product/analysis/capability")
    def product_analysis_capability(repo: StateRepository = Depends(state_repository)):
        state = repo.load()
        if fail_closed(state):
            return {
                "surface": "FAIL_CLOSED_NO_TRADE",
                "trigger": "EXPLICIT_USER_ACTION_ONLY",
                "strategy_version": "NONE",
                "variant": "NONE",
                "research_status": FAIL_CLOSED_RESEARCH_STATUS,
                "project_disposition": state.get("current_project_status", {}).get("disposition"),
                "champion_status": state["champion_status"],
                "paper_trade_persistence": False,
                "order_placement": False,
                "real_money_authorized": state["real_money_authorized"],
            }
        return {
            "surface": state.get("product_analysis", {}).get("surface", "UNAVAILABLE"),
            "trigger": "EXPLICIT_USER_ACTION_ONLY",
            "strategy_version": STRATEGY_VERSION,
            "variant": VARIANT,
            "research_status": RESEARCH_STATUS,
            "champion_status": state["champion_status"],
            "paper_trade_persistence": True,
            "order_placement": False,
            "real_money_authorized": state["real_money_authorized"],
        }

    @application.post("/api/v1/product/paper-trades")
    def create_paper_trade(
        request: PaperTradeCreateRequest | None = None,
        repo: StateRepository = Depends(state_repository),
    ):
        """Create one paper trade from a freshly evaluated LONG analysis.

        The plan is never supplied by the caller, so no price or geometry can be forged.
        """
        del request
        state = repo.load()
        if state["real_money_authorized"]:
            raise HTTPException(409, "real-money authorization is not supported by this surface")
        if fail_closed(state):
            raise HTTPException(409, FAIL_CLOSED_DETAIL)
        analysis = analyser()
        try:
            trade = create_from_analysis(analysis, trades)
        except PaperTradeError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"analysis_id": analysis["analysis_id"], "trade": trade, "real_money": False}

    @application.get("/api/v1/product/paper-trades")
    def read_paper_trades(limit: int = 20):
        return listing(trades, limit=max(1, min(limit, 100)))

    @application.get("/api/v1/product/market/recent")
    def recent_market():
        """Current public read-only candles for the local chart. Nothing is persisted."""
        return market_view()

    @application.get("/api/v1/product/paper-trades/statistics")
    def paper_statistics():
        """Counts over genuine persisted paper trades only; never backtest performance."""
        return statistics(trades)

    @application.get("/api/v1/product/prospective-observer")
    def prospective_observer_status():
        """Read-only automated shadow-paper status; never triggers an evaluation."""
        if shadow_observer is not None:
            return {**shadow_observer.overview(), "automatic_collection": collection_status}
        return {
            "automatic_collection": collection_status,
            "status": "STOPPED",
            "label": "AUTOMATED PAPER RESEARCH — NO REAL MONEY",
            "observer_version": OBSERVER_VERSION,
            "evidence_version": SHADOW_EVIDENCE_VERSION,
            "evidence_stage": SHADOW_EVIDENCE_STAGE,
            "initiation_mode": SHADOW_INITIATION_MODE,
            "strategy_version": STRATEGY_VERSION,
            "last_evaluated_hourly_boundary": None,
            "last_heartbeat": None,
            "next_expected_boundary": None,
            "missed_prospective_decisions": 0,
            "raw_prospective_long_signals": 0,
            "suppressed_long_signals": 0,
            "open_shadow_trade": None,
            "completed_shadow_trades": 0,
            "manual_evidence_included": False,
            "order_placement": False,
            "credentials": False,
            "real_money": False,
        }

    @application.post("/api/v1/product/paper-trades/lifecycle")
    def advance_paper_trades(repo: StateRepository = Depends(state_repository)):
        """Explicit lifecycle update only; nothing advances in the background."""
        state = repo.load()
        if state["real_money_authorized"]:
            raise HTTPException(409, "real-money authorization is not supported by this surface")
        return lifecycle(trades)

    return application


# ADR-0026. Automated ALIGNED prospective collection is SUSPENDED_BY_OWNER_OBJECTIVE_PIVOT:
# the observer measures the superseded cost/net-expectancy objective, so ``main`` no longer
# constructs one. ``default_observer`` is preserved as legacy infrastructure and stays
# importable for tests and any future Owner-authorized revival.
app = create_app(shadow_observer=default_observer() if AUTOMATIC_COLLECTION_ENABLED else None)

__all__ = ["COST_VERSION", "ENGINE_VERSION", "EXECUTION_VERSION", "app", "create_app"]
