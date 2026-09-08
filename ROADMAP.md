# Trading Bot — Roadmap

## Phase 0 — Scientific + engineering foundation

Create:
- governance;
- experiment lifecycle;
- preregistration contract;
- project state;
- data contract;
- evaluation stages;
- anti-overfitting controls;
- backend/frontend skeleton;
- deterministic validation;
- one-command local developer bootstrap where practical.

No market-data backfill.
No strategy search.

## Phase 1 — Data foundation

Build and validate:
- BTCUSDT canonical 1m history;
- immutable raw source archive;
- normalized Parquet;
- gap/integrity reports;
- deterministic 1h and 4h aggregation;
- dataset manifests and hashes;
- API endpoint for read-only market data;
- Market page fed from real canonical data.

## Phase 2 — Credible backtest substrate

Implement:
- fees;
- spread/slippage assumptions;
- next-bar execution;
- 1m intrabar resolution;
- ambiguous TP/SL policy;
- deterministic reproducibility;
- Freqtrade integration or equivalent validated substrate;
- web views for backtest/evidence inspection.

## Phase 3 — Baselines and negative controls

Before complex strategy research:
- Buy & Hold reference;
- random-entry control;
- simple trend;
- simple breakout;
- shifted-signal / future-feature leak controls.

Goal: prove the laboratory can distinguish credible implementation behavior from nonsense.

## Phase 4 — Strategy research

Prospectively research:
- trend;
- breakout;
- momentum;
- volatility/regime;
- volume;
- combinations after component ablations.

Primary objective:
robust net expectancy after costs.

## Phase 5 — Locked evaluation

Introduce:
- sealed holdout;
- limited query budget;
- coarse evaluator feedback;
- red-team promotion gates;
- independent finalist validation.

## Phase 6 — Local Paper Advisor V1

Complete the intended local product:

```text
open Trading Bot
→ Analyze Market
→ sync latest data
→ approved strategy evaluation
→ NO_TRADE
   or
→ LONG BTCUSDT
   signal timestamp
   entry
   stop loss
   take profit / exit
   expiry
   strategy version
→ record paper outcome
```

Dashboard, chart, trade history and statistics become Owner-ready.

Still no real money.

## Phase 7 — Long-running prospective evidence

Run the approved strategy prospectively for months.

Never rewrite historical paper signals.

## Phase 8 — Always-on Server V2

Move:
- collection;
- signal generation;
- paper trading;
- scheduler;
- web dashboard;
- notifications

to an always-on server.

Notify the Owner only for approved signals.

## Phase 9 — Research extensions

Only after the BTC pipeline is credible:
- ETH and other assets;
- cross-asset robustness;
- ML challengers;
- perpetual / SHORT research;
- microstructure / alternative data.

## Phase 10 — Possible real-capital gate

Only after sufficiently strong future evidence.

Requires explicit Owner decision.
