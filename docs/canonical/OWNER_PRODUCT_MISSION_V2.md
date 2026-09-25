# Owner Product Mission V2 — Professional Multi-Signal Trading System

Status: **OWNER-AUTHORIZED PRODUCT MISSION**
Date: 2026-09-25
Authority: Owner scope clarification. This document supersedes narrower product-scope assumptions
such as BTC spot LONG/NO_TRADE-only research where they conflict with this mission. Historical
results remain valid for the exact scopes in which they were produced.

## 1. Product objective

Trading Bot is intended to become a local web application whose algorithm behaves as a
**systematic professional trader**, combining multiple established trading-information families
and playbooks to continuously assess BTC and selectively propose paper trades.

The project is not primarily a hunt for one isolated quantitative anomaly.

The intended development philosophy is:

> use established mechanisms and decision concepts that experienced human traders already use,
> combine them coherently, make every component point-in-time and reproducible, and let rigorous
> historical / forward evidence determine which components and playbooks deserve to remain.

Statistics is the evaluator and guardrail. It must prevent leakage, overfitting and false claims,
but it must not redefine the product into a sequence of isolated single-feature alpha tests.

No novel exotic alpha mechanism should be invented merely because conventional components fail.
Frontier R&D remains exceptional and separately governed.

## 2. V1 user experience

V1 remains a local web app.

### Home / live market board

The landing page is a live BTC dashboard containing:

- a live BTC chart;
- a board of the professional signals / market-state inputs currently used by the algorithm;
- multi-timeframe context;
- the algorithm's continuous market prediction;
- a prominent trade-decision panel.

The live board should refresh at the natural cadence of each input. Price may update every second
or minute where technically appropriate; candle-derived state updates when the required observation
is complete.

### Continuous prediction

At every completed candle of the active prediction timeframe the algorithm emits a prediction,
regardless of whether it wants to trade.

The prediction surface should expose at minimum:

- predicted direction: UP / DOWN / NEUTRAL where appropriate;
- calibrated probability or confidence only if it is actually calibrated;
- expected movement magnitude / strength;
- risk / uncertainty;
- signal importance / conviction;
- relevant multi-timeframe state;
- concise reasons / contributing signal families.

A prediction is **not** the same as a trade instruction.

### Selective trade decision

The trade engine may output:

- LONG;
- SHORT;
- NO_TRADE.

A trade is proposed only when the combined evidence is sufficiently actionable under the governed
risk / execution policy.

When a trade is proposed the UI should show the actionable paper plan, including direction,
confidence / probability where scientifically valid, risk, invalidation / exit logic, expected
holding context and the signals that justified the decision.

The system must support LONG and SHORT as native paper-trading decisions. The future real execution
venue for SHORT is a separate engineering / Owner risk decision; this mission does not authorize
leverage or real capital.

## 3. Backtest experience

Backtesting is manually started by the Owner from the web app.

A backtest must behave like replaying history in accelerated time rather than only producing a final
report.

During replay:

- the BTC chart advances candle by candle;
- the same signal board updates causally;
- the same continuous prediction is produced for every eligible candle;
- the trade-decision panel changes as it would have at that historical moment;
- no future information is visible to the algorithm.

The UI should support a progress indicator but the primary experience is visual market replay.

### Per-candle annotations

Every evaluated candle should support two distinct visual annotations:

1. **Trade annotation**, displayed below the candle:
   - no trade / trade proposed;
   - if proposed: LONG or SHORT;
   - hover details include the complete frozen trade plan and eventual trade outcome.

2. **Prediction annotation**, displayed above the candle:
   - whether direction prediction was correct;
   - predicted vs realized magnitude / movement;
   - confidence / importance / risk;
   - hover details include the prediction snapshot and scoring details.

The same candle can therefore contain a prediction result even when no trade existed.

## 4. Prediction evaluation is not trade evaluation

Backtests may produce a very large number of candle-level predictions and far fewer trades.

The system must never reject an otherwise useful trading policy merely because many low-conviction
continuous predictions are wrong.

All predictions remain recorded and scored, but evaluation must distinguish:

- low-information / low-conviction forecasts;
- medium-conviction forecasts;
- high-conviction forecasts;
- actual trade-triggering forecasts.

Prediction quality should therefore be reported across predeclared importance / confidence strata
and with calibration / magnitude quality, not collapsed into an unqualified raw hit-rate.

Trade quality is evaluated separately using realistic economic outcomes, risk, execution and
opportunity frequency.

The algorithm is expected to be most economically accountable at the high-conviction / trade-decision
end of the distribution.

This separation must not become an excuse to hide poor predictions: coverage, calibration and every
stratum remain visible.

## 5. Professional signal / playbook philosophy

The algorithm should be constructed from a finite, explicit catalogue of established professional
trading concepts and coherent playbooks, not from an unconstrained feature soup.

Families to map and assess include, without assuming they are individually profitable:

- trend / market structure;
- momentum and acceleration/deceleration;
- breakout and failed breakout;
- pullback / continuation;
- mean reversion where economically justified;
- support / resistance;
- VWAP and volume-profile / price-location concepts;
- volume and participation;
- volatility / range expansion and contraction;
- order-flow / absorption / imbalance where historical point-in-time data exists;
- derivatives state such as funding, open interest and spot/perpetual relationships where relevant;
- cross-market / intermarket confirmation where a concrete mechanism exists;
- cyclical / temporal structure;
- scheduled or unscheduled public event context where point-in-time availability can be proven;
- risk / liquidity / execution state.

A signal family does not need to demonstrate standalone profitability to be eligible as a component
of a coherent professional playbook. Its value may be conditional or interaction-based.

Conversely, merely adding many indicators is not evidence. The project should model recognizable
professional decision logic and then evaluate the complete system and its components with controlled
ablations / comparisons.

## 6. Multi-timeframe requirement and cyclical analysis

Timeframe choice is part of system architecture, not a one-time arbitrary global constant.

The system must support a hierarchy of timeframes because different professional signals operate at
different scales.

Cyclical analysis is an explicit required research family and must be studied across multiple
timeframes rather than on one chart only. The Owner specifically wants cycle structure considered
from roughly 40-45 minute scale through daily, weekly, monthly and longer structures when the data
supports them.

This requirement does **not** declare cyclical trading validated or profitable. It declares that a
credible implementation of professional cycle analysis cannot be judged from one timeframe alone.

The architecture should distinguish at least:

- an execution / prediction timeframe;
- faster micro context if useful;
- slower regime / structure timeframes;
- longer cyclical context.

The exact canonical timeframe set and how signals are synchronized must be designed before the next
research execution. It must avoid look-ahead and use only completed/available observations.

## 7. Historical data policy

Historical market data should be cached locally and identified by manifests/hashes so backtests do
not repeatedly depend on remote APIs.

Canonical raw resolution should remain sufficiently fine to derive the required higher timeframes
without repeated downloads.

For every historical signal family:

- prefer locally cached point-in-time data;
- preserve source / timestamp / availability semantics;
- do not silently substitute present-day reconstructed values for information that was unavailable
  historically;
- if a professional signal cannot be reconstructed historically, report the limitation explicitly
  and decide whether it belongs only to live/future evaluation.

Live mode may call external APIs for current data, subject to source reliability and credentials /
cost governance.

Large datasets should not be committed to Git when inappropriate; manifests and reproducible cache
locations are the source of identity.

## 8. Hot-period event / news report

During a backtest the engine may identify unique dates / periods that were unusually active according
to predeclared market-only criteria such as volume, volatility or large movement.

Those unique periods may be placed into a post-backtest research queue.

Only **after** the trading replay is complete, an external-information report may investigate
whether notable public news, political, policy, economic or market events coincided with those hot
periods.

This post-hoc report is explanatory and must not retroactively alter the backtest signal or score.

If event/news information is later promoted into the trading algorithm itself, it requires a
separate point-in-time data contract proving what was knowable at decision time.

## 9. Scientific objective

The final objective remains practical paper-trading usefulness after realistic costs and risk, but
the research unit is now the **professional multi-signal system / playbook architecture**, not the
requirement that every individual signal independently carry a large alpha.

Evidence must separately answer:

1. Does the continuous prediction layer contain useful, calibrated information, especially as
   conviction rises?
2. Do selective LONG / SHORT trade decisions produce robust positive net expectancy and acceptable
   risk?
3. Which professional components materially help or hurt the complete decision process?
4. Does the system remain useful across relevant market regimes and timeframes?
5. Can promising behaviour survive proper out-of-sample / prospective confirmation?

Negative historical results remain binding for the exact formulations already tested, but they do
not automatically ban a signal from being used as a context component in a genuinely different,
predeclared composite playbook unless the prior evidence directly answers that role.

## 10. Scope boundaries

Current V1 product scope:

- primary instrument: BTC / BTCUSDT;
- paper only;
- LONG / SHORT / NO_TRADE;
- local web application;
- live dashboard plus manual historical replay/backtest;
- continuous candle-level prediction plus selective trade policy;
- professional, established trading concepts first;
- no real capital.

Not authorized by this document:

- real-money trading;
- leverage as a product requirement;
- multi-asset expansion merely to increase trials;
- arbitrary indicator/model tournaments;
- post-hoc strategy rescue;
- unconstrained AI-generated alpha hypotheses.

## 11. Governance consequence

The prior parked disposition was scientifically correct for the narrower BTC spot LONG/NO_TRADE
single-allocation programme then in force.

This Owner mission clarification is a **material product/scope change** and therefore is a legitimate
ADR-0042 reopening trigger.

It does not itself authorize a new market experiment.

Astra must now redesign the strategic research programme around this mission, reusing historical
evidence and infrastructure rather than restarting from zero.

The first strategic output should be a finite functional/scientific architecture for:

- the signal catalogue;
- multi-timeframe state;
- continuous prediction;
- selective LONG/SHORT policy;
- risk/execution;
- replay/backtest;
- evaluation and ablation;
- event/news reporting;
- staged implementation.

The programme must remain bounded and anti-overfitting, but it must optimize for building the
intended trader system rather than for finding one isolated standalone mechanism.
