# Trading Bot — Project Brief

## Product vision

Trading Bot is a multi-year experimental trading-research product.

The eventual user experience is intentionally simple:

1. The Owner starts the local web application.
2. Trading Bot synchronizes the latest market data.
3. The approved strategy evaluates the current market.
4. Trading Bot returns either `NO_TRADE` or one actionable paper-trade plan.
5. If a trade is proposed, the UI shows:
   - symbol;
   - signal timestamp;
   - direction;
   - entry rule / entry price;
   - stop loss;
   - take-profit / exit rule;
   - expiry / maximum holding time;
   - strategy version;
   - calibrated confidence only when scientifically justified.
6. The simulated outcome is recorded automatically and becomes research evidence.

Trading Bot must never be forced to invent a trade. `NO_TRADE` is a valid and important output.

## V1 — Local on-demand web application

V1 runs locally on the Owner's PC.

The Owner comes home, turns on the PC, starts Trading Bot and opens the browser.

Trading Bot:
- resumes persisted state;
- updates required market data;
- evaluates the approved strategy;
- shows the current decision;
- records paper trades and outcomes;
- exposes charts, statistics and research status.

No 24/7 requirement exists in V1.

## V2 — Always-on server

Later, Trading Bot runs continuously on a server.

It:
- keeps market data updated;
- evaluates the approved algorithm automatically;
- runs paper trading continuously;
- notifies the Owner when an approved trade signal appears.

The same web application becomes a remotely accessible dashboard.

## Initial research scope

- Market: crypto spot
- Initial symbol: BTCUSDT only
- Direction: LONG / NO_TRADE
- Canonical market-data resolution: 1 minute
- Signal timeframe: 1 hour
- Regime/context timeframe: 4 hours
- Initial maximum holding horizon: approximately 24 hours
- Signal style: closed-bar decision, next-bar execution
- Real money: forbidden

ETH and other assets are future extensions or robustness validators. They are not needed to prove the first research pipeline and would add degrees of freedom too early.

SHORT/perpetual research is a later branch because it adds leverage, funding, mark price, liquidation and venue-specific mechanics.

## Scientific objective

The objective is NOT a target win rate.

The objective is robust positive net expectancy after realistic transaction costs and execution assumptions.

A system may be profitable with a hit rate below 50% if average wins are sufficiently larger than average losses. A high hit rate can still lose money.

Hit rate remains visible in the UI, but it is a secondary metric.

## Owner interaction model

The Owner is intentionally not acting as quant researcher or engineer.

The Owner should not be required to:
- write code;
- debug;
- inspect raw logs;
- learn trading theory;
- manually analyze experiments;
- coordinate AI agents;
- translate research findings into technical tasks.

ChatGPT acts as Research Director and scientific/technical brain.

Codex is the primary implementation arm.
Claude or other coding agents may be used as overflow implementation arms when needed, but they do not define scientific direction.

Only decisions that genuinely require the Owner should interrupt the Owner.

## Real-capital rule

Backtests, sealed evaluation and paper trading can never automatically authorize real money.

Any future transition to real capital requires a separate explicit human decision after long-term prospective evidence.
