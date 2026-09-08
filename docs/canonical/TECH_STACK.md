# Trading Bot — Technical Architecture v0.1

## Principle

Quantitative research and trading logic live in Python.

The user interface is a modern browser-based application.

V1 runs locally. V2 moves the same architecture to an always-on server without rewriting the scientific core.

## Backend

Use:

- Python
- FastAPI
- deterministic research/domain modules separated from HTTP concerns

Responsibilities:
- market-data synchronization;
- feature calculation;
- approved strategy evaluation;
- paper-trade lifecycle;
- statistics;
- experiment/state access;
- REST API for the frontend.

Trading logic must never depend on frontend code.

## Frontend

Use:

- React
- TypeScript
- Vite

The frontend is a presentation/control layer only.

It must never calculate authoritative strategy outcomes independently from the backend.

## Financial charts

Use TradingView Lightweight Charts for:
- candlestick charts;
- entry markers;
- stop-loss lines;
- take-profit / exit lines;
- signal markers;
- trade visualization.

Use a normal React charting library for non-market statistics if needed.

Do not build custom chart primitives unnecessarily.

## Storage — V1

Use:
- Parquet for canonical and derived market data;
- DuckDB for analytical querying;
- SQLite for lightweight local application/control state when relational persistence is needed.

Avoid PostgreSQL in the first local bootstrap unless demonstrated necessary.

## Storage — V2

When Trading Bot becomes always-on:
- retain Parquet/DuckDB for research and historical analytics where useful;
- migrate operational/control-plane state to PostgreSQL if continuous multi-process runtime warrants it.

Do not perform this migration early.

## Local application experience

The Owner should eventually start Trading Bot with one simple command/script.

Example goal:

```text
start-trading-bot
```

The launcher should:
1. start backend;
2. start/serve frontend;
3. perform health checks;
4. open the local browser automatically when practical.

The Owner should not manually start five services.

## API boundary

Version API routes from the beginning:

```text
/api/v1/...
```

Likely future endpoints include:

```text
POST /api/v1/analysis/run
GET  /api/v1/signal/current
GET  /api/v1/market/candles
GET  /api/v1/paper-trades
GET  /api/v1/statistics
GET  /api/v1/research/status
GET  /api/v1/system/health
```

Exact schemas are defined prospectively when implemented.

## Deployment philosophy

V1:
- Windows-friendly local development/runtime;
- minimal moving parts;
- localhost only by default.

V2:
- containerized/server runtime;
- secure remote access;
- background scheduler;
- notification service;
- persistent operational database.

Do not build V2 infrastructure before V1 research credibility exists.

## Excluded initially

Do not introduce without demonstrated need:
- Kubernetes;
- Redis;
- ClickHouse;
- message brokers;
- microservices;
- GPU workloads;
- deep learning;
- complex cloud infrastructure.
