# Professional Multi-Signal Paper System Architecture V1

Status: **ADOPTED — PROTOCOLS PENDING IMPLEMENTATION**
Date: 2026-09-25
Authority: Owner Product Mission V2, ADR-0043, Astra
`ASTRA_PROFESSIONAL_TRADING_SYSTEM_STRATEGIC_ARCHITECTURE_V1`.

## Strategic disposition

`PROFESSIONAL_MULTISIGNAL_PAPER_SYSTEM_DEVELOPMENT — ARCHITECTURE_ADOPTED_PROTOCOLS_PENDING`

ADR-0042 remains the correct historical disposition for the narrower predecessor programme.
Candidate #1 remains `DEVELOPMENT_REJECTED`. The Owner-authorized mission reset opens one bounded
new system generation, **System G1**.

System G1 is not a strategy factory. It is one interpretable BTC paper-trading system with:

- continuous candle forecasts;
- selective `LONG / SHORT / NO_TRADE` decisions;
- shared multi-timeframe market state;
- exactly two initial playbooks;
- one explicit risk/execution contract;
- one causal live/replay core;
- a finite controlled comparison budget.

## Product defaults

| Decision | V1 |
|---|---|
| App | Local FastAPI + React/TypeScript |
| Market | BTCUSDT; spot and USD-M retain separate identities |
| Actions | LONG / SHORT / NO_TRADE, paper only |
| Decision clock | Completed 15m candles |
| Execution clock | Canonical 1m bars |
| Forecast target | Terminal 4h price-return distribution |
| Context | 1h structure, 4h regime, completed daily context, weekly/monthly background |
| Playbooks | P1 directional continuation after pullback; P2 failed-auction re-entry |
| Position policy | One open position system-wide; no pyramiding/hedging |
| Forecaster | One transparent shrunken empirical conditional distribution; no learner tournament |
| Cycle family | One documented causal family, six fixed nominal scales |
| Data | Local immutable cache/manifests; no repeated API dependency for replay |

The 15m clock is not selected from historical profitability. It is the operational issue cadence.
The 4h forecast is a prediction target, not a forced holding period for every trade.

## Functional modules

1. **Market Data** — provenance, availability, gaps, source identity.
2. **Timeframe Aggregation** — deterministic UTC completed bars.
3. **Signal Engines** — bounded professional measurements with role/quality/reason.
4. **Cycle Engine** — documented causal multi-scale state.
5. **Market State** — trend/range/transition, price location, disagreement.
6. **Conviction / Actionability** — ex-ante coherence and operational readiness.
7. **Prediction Engine** — immutable 4h forecast distribution at every eligible 15m issue.
8. **Playbook Engine** — recognizes only P1/P2.
9. **Trade Decision** — LONG / SHORT / NO_TRADE and blockers.
10. **Risk** — size/veto/daily and run-level controls.
11. **Execution Simulation** — signed USD-M reference-paper fills, costs and funding.
12. **Historical Replay** — causal virtual clock; speed affects UI only.
13. **Prediction Scoring** — every matured forecast.
14. **Trade Scoring** — selected policy and portfolio path.
15. **Event/News Post-Analysis** — retrospective explanation only, outside input graph.
16. **Research Memory** — lineage, exposure, configuration and disposition.
17. **API** — versioned immutable snapshots/control operations.
18. **Live Web UI** — display only; no trading logic.

Historical and live adapters must feed the **same core algorithm**.

## Finite G1 signal catalogue

### Active system families

- **Structure / trend** — 1h structure and 4h directional context; setup routing and direction.
- **Price location / value** — session VWAP, previous completed day high/low, confirmed swing levels.
- **Momentum / volatility** — normalized trailing movement and prior-risk scale; timing/risk.
- **Participation / aggressive flow** — relative volume and exchange-reported taker imbalance as one
  corroboration family.
- **Cyclical state** — six fixed nominal scales under the separate cycle method contract.
- **Derivatives state** — OI quantity, settled funding and spot/perpetual relation for board/context;
  funding also belongs to accounting.
- **Execution / data quality** — staleness, gaps, friction, source readiness, occupancy; veto layer.

### Deferred / descriptive

- volume profile is descriptive unless exact historical price-bin volume is available;
- exact order-book absorption is not inferred from OHLCV/taker aggregates;
- news/macro/intermarket information is not a G1 alpha input;
- event/news research is post-hoc explanation only.

No third playbook, generic source ladder, autonomous AI trading policy or hidden ALIGNED fallback is
part of G1.

## Initial playbooks

### P1 — Directional continuation after pullback

Professional proposition: continuation of an established directional auction after a retracement to
a pre-existing value/structure reference.

- bullish and bearish branches are explicit;
- 4h context and 1h structure must support the same direction;
- completed 15m data supplies the trigger;
- participation/flow has a fixed corroboration role;
- cycle state may qualify timing but cannot override price/risk/data vetoes;
- one location construction, one trigger construction, one invalidation construction and one exit
  policy will be frozen before historical outcomes.

P1 overlaps adverse prior trend/pullback evidence and is not a fresh family by renaming.

### P2 — Failed-auction re-entry in a bounded market

Professional proposition: price fails to sustain trade beyond an already known prior-day range
boundary and then causally re-enters the range.

- failure below the known lower boundary may propose LONG;
- failure above the known upper boundary may propose SHORT;
- bounded/range market state is required;
- trigger is observed re-entry, not a future-labelled turning point;
- initial value objective is the value/VWAP reference known at trigger;
- no claim of hidden order-book absorption is made.

P2 is distinct from successful breakout trading and from Candidate #1.

### Routing

Trend state routes toward P1; bounded/range state routes toward P2; transition/uncertain state
defaults to NO_TRADE. Conflicting eligible plans -> NO_TRADE. Agreeing plans never double exposure.

## Timeframe architecture

One decision clock and one predictor are used.

- source/execution: 1m;
- operational decision/prediction: 15m;
- structure: 1h;
- directional regime: 4h;
- completed daily context;
- weekly/monthly background and slow-cycle context.

A derived 45m view may support cycle diagnostics but is not a second decision clock.

Fixed cycle scales:

`45m, 3h, 1d, 4d, 1w, 4w`

They are one hierarchical family, not six votes or six strategies.

Forecast horizon: exactly 4h terminal return from each eligible 15m issue. Adjacent forecasts
overlap and must be scored with dependence-aware inference.

## Forecast / conviction architecture

At every eligible decision candle issue a forecast, including low-conviction and neutral states.

V1 forecaster: one shrunken empirical distribution of risk-standardized 4h returns conditioned on
at most nine coarse cells:

`directional_bias {BEARISH, NEUTRAL, BULLISH} × conviction {LOW, MEDIUM, HIGH}`.

Sparse cells shrink toward the training unconditional distribution. Support/shrinkage/calibration
rules must be frozen before outcomes.

Conviction is ex-ante evidence coherence:

- LOW — no coherent approved setup or material disagreement;
- MEDIUM — coherent setup forming, but trigger/corroboration incomplete;
- HIGH — one approved playbook's full frozen evidence/trigger pattern is present.

Conviction is not probability. Actionability is separate and includes data readiness, risk,
occupancy and final trade decision.

## Paper trade / risk defaults

Reference research instrument for LONG and SHORT: **BTCUSDT USD-M traded prices**.
BTC spot remains an independently identified context source.

This is a paper reference contract, not a live venue authorization.

Initial risk policy:

- virtual initial equity: 10,000 quote units;
- planned equity risk per position: 0.25%;
- maximum virtual gross notional: 1× virtual equity;
- maximum one open position;
- no pyramiding, hedging, martingale or performance-adaptive sizing;
- daily new-entry loss limit: 1% of equity;
- run drawdown new-entry stop: 5%;
- one structural invalidation per playbook;
- one profit objective per playbook;
- maximum hold: 4h.

Primary research cost convention: inherited nominal 24bp round-trip fee/friction plus funding.
Predeclared robustness views: 48bp cost stress and +5m operational-delay stress.

Exact playbook stop/objective/reward-cost constructions are frozen in the later G1 development
protocol, before outcomes.

## Causal replay

A single virtual clock drives observations, aggregation, signals, cycles, state, forecasts,
decisions, risk, fills and score resolution.

At cursor T, only observations with `available_at <= T` are visible.

Replay speed changes wall-clock pacing only. Same sources + versions + configuration -> same event IDs
and outputs at every speed.

Persistent entities:

- RunManifest
- SourceManifest
- SignalSnapshot
- CycleState
- MarketState
- ModelArtifact
- PredictionSnapshot
- PredictionRealization
- DecisionSnapshot
- TradePlan
- OrderFillEvent
- PositionLedger
- HotWindow
- PostAnalysisReport
- ResearchExposureRecord

Issued predictions remain immutable. Realizations are separate records.

## V1 web application

Exactly three pages:

### Home / Live

- live/reference BTC chart;
- grouped signal board with role/timeframe/quality/as-of;
- multi-timeframe disagreement and cycle rows;
- forecast panel with direction, probability status, magnitude, interval, risk and conviction;
- decision panel with LONG/SHORT/NO_TRADE, playbook, blockers and paper plan;
- current position/risk budget and research-validity status.

### Backtest / Replay

- approved local dataset/date range/configuration;
- start/pause/single-step/speed;
- virtual time;
- causal advancing chart;
- replayed signal board, forecasts, decisions and positions;
- prediction glyph above each eligible candle;
- decision glyph below each eligible candle;
- entry/exit markers at actual simulated fill times;
- running matured-only statistics;
- final prediction/trade/risk/coverage/search reports;
- post-backtest event/news explanation.

### History / Research

- run history;
- forecast/trade drill-down;
- comparison tables;
- paper ledger;
- configuration/version lineage;
- governance/research status.

No free parameter/indicator optimizer is exposed in V1.

## Evaluation architecture

Evaluate distinct questions separately.

### Continuous forecasts

Score all eligible forecasts against same-timestamp baselines:

- availability/coverage;
- direction accuracy versus base rate;
- Brier/log loss where probabilities are valid;
- calibration/reliability;
- distribution/quantile scores;
- magnitude error;
- interval coverage.

### Conviction

Report LOW/MEDIUM/HIGH and trade-triggering strata with counts, calendar coverage and
composition-controlled skill. Test whether declared conviction actually stratifies useful
information.

Low-conviction errors remain visible but do not automatically reject the selective trade policy.

### Complete trading system

Primary economic object: calendar-time equity/P&L of the complete fixed-risk system under common
execution assumptions.

Also report:

- net expectancy/trade and/notional;
- LONG and SHORT separately;
- turnover and occupancy;
- costs/funding;
- tails/drawdown;
- worst periods;
- suppressed entries.

### Components

A component can justify its role through conditional incremental contribution; no standalone-profit
gate is imposed on context signals. Controlled removals keep clock, costs, eligibility and risk
fixed.

## G1 bounded comparison budget

Maximum seven predeclared configurations:

1. S0 — simple price/structure/risk versions of P1/P2.
2. S-full — complete approved composite, including admitted cycle timing.
3. S-full minus cycle.
4. S-full minus participation/flow corroboration.
5. S-full minus additional higher-timeframe corroboration.
6. S-full with P1 only.
7. S-full with P2 only.

No Cartesian combinations, alternative learners, alternative cycle methods, horizon tournament,
threshold tournament or exit tournament.

Before any market outcome the Director freezes:

- all definitions/configuration identities;
- training/calibration/evaluation schedule;
- selection rule across the seven-or-fewer configurations;
- material economic/predictive promotion claims;
- cost/delay robustness;
- support, tail, concentration and prospective-feasibility gates.

At most one already-declared configuration may advance.

## Stages

### Checkpoint 1 — Contracts and synthetic causal vertical slice

No historical performance.

Freeze contracts, playbook cards, cycle method, timing/data boundary, then implement:

- immutable run manifest;
- completed-bar aggregation;
- virtual clock;
- prediction/decision records;
- native LONG/SHORT ledger;
- one replay screen with above/below candle annotations;
- causal tests including future-data rejection and replay-speed invariance.

### Checkpoint 2 — One frozen G1 historical Development batch

Complete playbooks, cycle engine, board, forecaster and registered-run UI. Freeze one G1 batch before
outcomes; then execute only the declared configurations/stresses.

### Checkpoint 3 — One prospective system or stop

If no declared configuration passes, `SYSTEM_G1_REJECTED_PENDING_ASTRA`; no automatic G2.
If one qualifies, freeze one prospective paper system and return to Astra before confirmation.

## Governance

- Owner: product/risk/resource changes and real capital.
- Astra: material architecture/allocation, post-G1 promotion/stop.
- Research Director: protocols, ordinary numerical choices, implementation review/adjudication.
- Claude Code: engineering executor only.

No real money, credentials or live orders.
