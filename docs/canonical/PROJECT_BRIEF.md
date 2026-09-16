# Trading Bot — Project Brief

## Product vision

Trading Bot is a multi-year experimental trading-research product.

The eventual user experience is intentionally simple:

1. The Owner starts the local web application.
2. Trading Bot synchronizes the latest market data.
3. The approved predictor evaluates the current market.
4. Trading Bot returns a forecast for the declared horizon, and separately an action.
5. The forecast shows:
   - symbol and forecast horizon;
   - predicted direction;
   - calibrated probability that the declared direction is correct;
   - strength 0-100, a magnitude scale and never a probability;
   - expected move in percent and in approximate quote-currency units;
   - uncertainty and context, including coverage and sample size;
   - predictor version.
6. The action is shown separately: `LONG` or `NO_TRADE` for paper-only V1.
7. Trade economics, when shown at all, are shown separately from prediction quality.
8. The simulated outcome is recorded automatically and becomes research evidence.

Trading Bot must never be forced to invent a trade or a confident forecast. `NO_TRADE` and
an explicitly uncertain forecast are valid and important outputs. The UI never presents an
uncalibrated model score as a probability and never claims certainty.

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
- Canonical market-data resolution: 1 minute
- Forecast decision cadence: 1 hour, closed-bar, UTC
- Primary forecast horizon: 24h terminal return, `r_24h = log(close[t+24h] / close[t])`
- Predicted direction: UP / DOWN / NEUTRAL_UNCERTAIN
- Trade action (separate concept): LONG / NO_TRADE
- Regime/context timeframe: 4 hours
- Signal style: closed-bar decision, next-bar execution
- Leverage, shorts and perpetuals: not in V1
- Real money: forbidden

ETH and other assets are future extensions or robustness validators. They are not needed to prove the first research pipeline and would add degrees of freedom too early.

SHORT/perpetual research is a later branch because it adds leverage, funding, mark price, liquidation and venue-specific mechanics.

## Scientific objective

The objective is a statistically credible BTCUSDT predictor: future price direction, a
calibrated probability, and an expected movement magnitude over explicitly declared
horizons.

Directional win rate is a primary human-facing metric, and it is never interpreted alone.
Every win rate is reported with sample size and prediction coverage, alongside calibration,
magnitude error, predeclared chronological baselines and a dependence-aware uncertainty
interval. A high win rate obtained by abstaining almost everywhere, by class imbalance, or
by selective reporting is not predictive success.

No win-rate target is declared before evidence establishes what is feasible.

Prediction quality is judged independently of capital size, exchange fees, leverage,
slippage, network costs and position sizing. Those belong to the downstream economic layer,
which decides whether a correct prediction is also a profitable trade — a separate question
with a separate answer.

The frozen definitions live in
[`PREDICTIVE_EVALUATION_CONTRACT_V1.md`](PREDICTIVE_EVALUATION_CONTRACT_V1.md).

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
