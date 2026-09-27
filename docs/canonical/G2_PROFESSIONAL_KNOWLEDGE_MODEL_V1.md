# G2 Professional Knowledge Model V1

Status: FROZEN AT G2-00 GATE A — DEVELOPMENT ARCHITECTURE, NOT VALIDATED ALPHA  
Date: 2026-09-27  
Authority: ADR-0052 and reports/strategic/ASTRA_TRADING_BOT_DEVELOPMENT_SYSTEM_DIRECTIVE_V2.md

## 1. Purpose

This document defines the bounded professional-information model for G2.

It is a runtime knowledge graph, not an indicator catalogue. The runtime is numeric, deterministic
and versioned. AI may inspect and explain stored records during research, but it may not add an
unregistered rule, change a coefficient, infer a hidden participant identity, or alter a decision at
runtime.

The four epistemic levels are kept separate:

1. OBSERVATION — a timestamped market fact or deterministic transform.
2. INTERPRETATION — a declared hypothesis about what that fact may mean.
3. PREDICTION — a model estimate with explicit target and uncertainty.
4. ACTION — LONG, SHORT or NO_TRADE under policy, risk and execution rules.

No transition between these levels is automatic.

## 2. G2 comparative-advantage hypothesis

The bounded working hypothesis is:

A small-size, moderate-frequency BTC system may extract weak conditional persistence and may monetize
it better by selecting entries whose path and costs are more favorable, without being continuously
invested.

Possible mechanisms are slow/heterogeneous adjustment by participants and temporary or forced
pressure visible in price, participation and price response. These are hypotheses, not established
causes. G2 does not claim speed, private data, privileged news, market-making or LLM interpretation
as an advantage.

The hypothesis is weakened if the complete system adds no information over simple references,
collapses under plausible friction, depends on a few episodes, only learns abstention, or degrades
once frozen.

## 3. Knowledge-card contract

Every family records:

- identity and primary role;
- economic/professional rationale;
- source/evidence provenance and transfer limits;
- required observables and causal availability;
- dependencies/redundancy with other families;
- allowed and forbidden downstream links;
- epistemic state;
- invalidity/staleness/warm-up rules;
- diagnostics capable of challenging the role.

Runtime availability states are:

- AVAILABLE_USED;
- AVAILABLE_SHADOW;
- AVAILABLE_DISPLAY_ONLY;
- UNRELIABLE;
- UNAVAILABLE.

A displayed variable is not automatically a model input.

## 4. Stable role graph

The G2-V0 graph is:

USD-M completed market observations
  -> STRUCTURE_TREND
  -> PARTICIPATION_FLOW_RESPONSE
  -> VOLATILITY_PATH_RISK
  -> transparent 4h forecast readout
  -> transparent LONG/SHORT shadow-payoff utility readouts
  -> actionability comparison
  -> independent risk governor
  -> execution model
  -> trade lifecycle and outcome

CYCLE_TIME_STATE publishes shadow timing state into records and UI in V0. It may enter a reserved
development revision only after its method-quality contract is satisfied.

LIQUIDITY_EXECUTION constrains cost/fill/feasibility. It is not a directional alpha vote.

CONTRACT_DERIVATIVES_CONTEXT supplies contract semantics and funding cost in V0. It is not a
directional alpha vote.

Completed Daily and Weekly context is persisted/displayed but is not an additional coefficient in
G2-V0.

## 5. Family 1 — STRUCTURE_TREND

Primary roles:
- DIRECTION;
- PERSISTENCE;
- PRICE_LOCATION.

Evidence:
- LIB-004, LIB-006, LIB-007, LIB-008, LIB-009, LIB-010, LIB-011, LIB-015.
- These sources are dependent evidence families, not independent votes.
- Traditional multi-asset/monthly evidence is an architectural prior, not validation of BTC 4h.

V0 model observables:
- LOCAL_STRUCTURE;
- CONTEXT_STRUCTURE;
- PRICE_EXTENSION.

Interpretation:
- signed trend state is directional evidence;
- extension is location/actionability context and may oppose immediate entry without reversing the
  slower view.

Redundancy rule:
EMA, MACD, moving-average crossover, return momentum and other linear price filters are not separate
families merely because their formulas differ. G2-V0 uses one declared exponential-filter
representation.

Failure modes:
- whipsaw;
- abrupt reversal;
- stale persistence;
- strong extension after a move;
- horizon mismatch.

Forbidden:
- indicator tournament;
- several correlated trend transforms as additive confirmations;
- treating historical cross-asset trend Sharpe as BTC expected performance.

## 6. Family 2 — PARTICIPATION_FLOW_RESPONSE

Primary roles:
- CONDITIONAL_CONFIRMATION;
- CONDITIONAL_CONTRADICTION;
- PATH/TIMING CONTEXT.

Evidence:
- LIB-001 accessible portions, LIB-012 and LIB-020;
- prior Trading Bot public-taker-flow research and order-flow lineage.

V0 model observables:
- RELATIVE_PARTICIPATION;
- TAKER_IMBALANCE;
- two predeclared interactions:
  - LOCAL_STRUCTURE x RELATIVE_PARTICIPATION;
  - TAKER_IMBALANCE x PRICE_RESPONSE.

Observation semantics:
- quote volume measures activity;
- taker-buy volume identifies aggressive buying volume under the venue field semantics;
- neither observation identifies participant identity, motive, future order flow or fundamental
  information.

Prior project evidence:
- the frozen public-taker-flow foundation found support at 1h, not at 4h or 24h;
- the planned 1h incremental test was power-blocked and never executed;
- earlier order-flow strategy lineage was cost-dominated.

Therefore G2 has an adverse prior against treating standalone 4h flow as a fresh alpha discovery.
Flow is admitted only as part of the distinct complete-system conditional contract and does not reset
search memory.

Failure modes:
- hedging/inventory/liquidation/manipulation creates similar-looking flow;
- high activity without information;
- participant mix changes;
- field missingness or semantic drift.

Forbidden:
- HIGH_VOLUME = BULLISH;
- BUY_IMBALANCE = LONG;
- claiming hidden institutional absorption from OHLCV/taker fields;
- replacing missing flow with numeric zero.

## 7. Family 3 — VOLATILITY_PATH_RISK

Primary roles:
- FORECAST SCALE;
- REGIME/STATE;
- POSITION/RISK CONTEXT.

Evidence:
- LIB-002, LIB-004, LIB-019, plus methodological support in LIB-012.

V0 model observable:
- VOLATILITY_STATE, defined as the ratio of fast and slow causal realized-volatility estimates.

Additional use:
- SIGMA_4H scales the normalized forecast target;
- ATR_1H defines the baseline protective-stop distance;
- risk governor uses realized path and portfolio drawdown independently of alpha.

Interpretation:
higher volatility is not bullish or bearish by itself.

Failure modes:
- jumps/gaps;
- estimator lag;
- rapid state transitions;
- non-stationary tails.

Forbidden:
- volatility as a simple directional vote;
- loosening risk limits because recent P&L is favorable.

## 8. Family 4 — CYCLE_TIME_STATE

Primary roles:
- TIMING;
- MULTISCALE TEMPORAL CONTEXT.

Evidence:
- current corpus has weak direct professional cycle-method coverage;
- G1 contains a causal ACP method plus synthetic method-quality evidence;
- no BTC predictive utility is established.

G2-V0 role:
AVAILABLE_SHADOW only. It is recorded and displayed but has no coefficient and no veto.

Candidate scale map inherited as a measurement convention:
- 45m;
- 3h;
- 1d;
- 4d;
- 1w;
- 4w.

This grid is not a natural law and is not an optimization space.

The only candidate method is the existing causal Autocorrelation Periodogram lineage. No second
cycle-method tournament is authorized.

Required state:
- phase;
- projection amplitude;
- dominant period;
- period stability;
- explained fraction/quality;
- declared lag;
- UNRELIABLE/UNAVAILABLE state.

Activation rule:
cycle terms can enter only the one reserved substantive development revision and only after the
cycle checkpoint and implementation fixtures pass. At most two cycle-derived terms may be admitted,
and the total readout remains capped at eight columns.

Forbidden:
- six cycle scales as six independent directional votes;
- cycle phase alone creating LONG/SHORT;
- replacing a failed cycle method with another algorithm inside G2.

## 9. Family 5 — LIQUIDITY_EXECUTION

Primary roles:
- EXECUTION;
- COST;
- FEASIBILITY;
- VETO.

Evidence:
- LIB-001 accessible portions and LIB-020.

V0 historical state:
historical bid/ask/order-book data is not required. Historical execution is market-only and uses a
declared aggregate friction scenario.

Future-paper/live state:
best bid/ask timestamps are CORE for realized execution measurement when available.

Relevant concepts:
- spread/width;
- available quantity;
- delay;
- slippage;
- gap risk;
- non-fill;
- implementation shortfall.

This family can veto an action because execution data are invalid or the contract cannot be
satisfied. It has no direct bullish/bearish coefficient in V0.

Forbidden:
- assuming candle volume equals executable depth;
- assuming a touched limit order filled;
- inventing historical queue position or L2/L3 data.

## 10. Family 6 — CONTRACT_DERIVATIVES_CONTEXT

Primary roles:
- INSTRUMENT CONTRACT;
- CARRY/COST;
- RISK/ACCOUNTING CONTEXT.

Evidence:
- LIB-019, LIB-002, LIB-014; current venue documentation for factual contract semantics.

V0 active inputs:
- instrument identity/specification;
- mark/index only where a contract/accounting rule explicitly requires them;
- settled funding as realized holding cost.

Not V0 alpha:
- open interest;
- liquidations;
- basis;
- long/short account ratios;
- options/implied variables;
- funding level as directional signal.

Prior project evidence:
settled-funding linear and nonlinear predictive families were rejected in development. G2 does not
treat funding as fresh directional evidence.

Forbidden:
- positive funding = bullish or bearish rule;
- OI = new longs/new shorts;
- futures/perpetual premium = expected future spot direction.

## 11. Exact G2-V0 predictive dictionary

The predictive readout has exactly six main columns and two interaction columns:

Main:
1. LOCAL_STRUCTURE
2. CONTEXT_STRUCTURE
3. PRICE_EXTENSION
4. RELATIVE_PARTICIPATION
5. TAKER_IMBALANCE
6. VOLATILITY_STATE

Interactions:
7. LOCAL_STRUCTURE_X_PARTICIPATION
8. IMBALANCE_X_PRICE_RESPONSE

No other variable enters G2-V0 forecast or utility heads.

Daily/Weekly observations, cycle state, liquidity state and derivatives context remain visible in
their declared roles without becoming hidden coefficients.

## 12. Prior negative lineage that G2 inherits

G2 search memory includes, at minimum:

- Candidate #1 development rejection;
- predictive Generation V1 internal linear/nonlinear failures at the frozen 24h question;
- settled-funding linear/nonlinear development rejection;
- public taker-flow 4h and 24h foundation non-support;
- public taker-flow 1h foundation support without executed incremental proof;
- prior order-flow cost-dominated lineage;
- System G1 Phase-A selection-stage rejection.

G2 is materially different because it tests one 4h complete trader contract with continuous
distributional forecasting, path-aware actionability, explicit costs and bounded iterative
development. That distinction does not erase the adverse priors above.

## 13. Deliberately excluded from G2-V0

No V0 alpha terms for:

- news/NLP;
- social sentiment;
- on-chain;
- macro/intermarket;
- undefined BTC value;
- options skew/implied volatility;
- liquidation maps;
- open interest;
- basis;
- long/short ratios;
- volume profile as a new family;
- latent regime clustering;
- tree/boosting/ensemble model zoo.

A later addition must solve a specific recorded failure/hypothesis and requires the governance
appropriate to its scope.

## 14. Falsification and diagnostics

The complete knowledge model is challenged by:

- null and trend-only forecast references;
- trend-only policy reference under identical geometry/cost/risk;
- two predeclared group ablations;
- forecast calibration/proper scoring;
- path/actionability diagnostics;
- cost/latency stress;
- concentration and episode analysis;
- frozen protected evaluation;
- prospective paper behavior.

A family may remain descriptively useful even if it provides no incremental predictive utility.
Descriptive product value is never relabeled as alpha.

## 15. Current epistemic state

STRUCTURE_TREND: DEVELOPMENT PRIOR  
PARTICIPATION_FLOW_RESPONSE: DEVELOPMENT PRIOR WITH ADVERSE 4H STANDALONE SEARCH MEMORY  
VOLATILITY_PATH_RISK: ACTIVE RISK/STATE CONTRACT, NOT DIRECTIONAL EDGE  
CYCLE_TIME_STATE: SHADOW METHOD ONLY  
LIQUIDITY_EXECUTION: ACTIVE EXECUTION CONTRACT  
CONTRACT_DERIVATIVES_CONTEXT: ACTIVE COST/CONTRACT ROLE, NOT DIRECTIONAL EDGE

No G2 family is a validated BTC alpha source at Gate A.
