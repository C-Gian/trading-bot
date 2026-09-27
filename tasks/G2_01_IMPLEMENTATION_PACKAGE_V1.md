# G2-01 Implementation Package V1 — Causal Trader Vertical Slice

Status: **AUTHORIZED ENGINEERING PACKAGE — NON-ECONOMIC GATE B ONLY**  
Date: 2026-09-27  
Generation: `G2_DEVELOPMENT_SYSTEM`

## 1. Authority

Read only the minimum required set:

1. `AGENTS.md`
2. `state/current_state.json -> current_project_status` and `g2_development_system`
3. `tasks/CURRENT_TASK.md`
4. this file
5. `docs/canonical/G2_PROFESSIONAL_KNOWLEDGE_MODEL_V1.md`
6. `docs/canonical/G2_FORECAST_POLICY_EXECUTION_CONTRACTS_V1.md`
7. `research/g2/G2_DATA_EXPOSURE_AND_EXECUTION_MANIFEST_V1.md`
8. `research/g2/G2_CYCLE_CAUSALITY_CHECKPOINT_V1.md`
9. only the engineering files explicitly listed below when reuse is needed

Strategic authority:
- `reports/strategic/ASTRA_TRADING_BOT_DEVELOPMENT_SYSTEM_DIRECTIVE_V2.md`
- `decisions/ADR-0052-ADOPT-ASTRA-G2-DEVELOPMENT-SYSTEM-AND-OPEN-G2-00.md`
- `reports/checkpoints/G2-00-GATE-A-CONTRACT-FREEZE-V1.md`

Do not reread the whole repository or old task archive.

## 2. Objective

Implement one deterministic, causal, interpretable **G2-V0 vertical slice** that can:

`market facts -> G2 state -> continuous 4h forecast -> LONG/SHORT utility -> LONG/SHORT/NO_TRADE -> risk/execution simulation -> immutable records -> replay/UI inspection`

The purpose of G2-01 is engineering/scientific correctness.

It MUST NOT determine whether G2 is profitable.

Gate B asks only whether the frozen G2 contracts are implemented causally, deterministically and inspectably.

## 3. Absolute prohibitions

During G2-01:

- no cumulative BTC strategy-performance comparison;
- no G2-V0 economic selection;
- no parameter, feature, timeframe, model, threshold or cost tuning;
- no G1 rescue or reuse of G1 playbook economics;
- no inspection of protected 2025+ outcomes;
- no discovery/enumeration of protected observation objects as a convenience;
- no new alpha-data family;
- no alternate model class;
- no cycle-method tournament;
- no activation of cycle alpha/timing in V0;
- no prospective strategy collection;
- no paper or real orders;
- no real-money credentials or capital.

Small explicitly declared windows ending no later than 2024-12-31 are allowed only for parser, aggregation, causal replay and parity tests described below.

## 4. Frozen scientific semantics — executor may not reinterpret

Implement exactly the contracts, including:

- raw substrate: BTCUSDT USD-M 1m;
- eligible decision grid: completed 15m candles;
- local state: completed 1h;
- directional context: completed 4h;
- Daily/Weekly: display-only;
- primary target: 4h log return;
- predictive dictionary: exactly 8 numeric columns defined by the contract;
- transparent ridge readout with frozen penalties;
- training-only robust median/MAD scaling;
- monthly UTC refit;
- 730-day max / 180-day min training span and 10,000 mature-row minimum;
- prequential empirical predictive distribution plus frozen causal fallback;
- separate LONG and SHORT utility ridge heads using NET_R labels;
- prudential-margin action rule;
- one-position risk governor;
- 0.25% planned risk, 1.0x max gross notional, 5% path drawdown stop;
- 2x ATR14 1h protective stop;
- 4h expiry;
- market-only historical execution;
- 1m base latency;
- frozen adverse historical friction convention;
- settled funding as accounting cost only;
- cycle state shadow-only in G2-V0;
- immutable prediction, decision and trade-lifecycle records;
- canonical reason codes.

If code behavior conflicts with the frozen contract, the contract wins.

## 5. Architecture boundary

Create a distinct G2 implementation package, preferably:

`backend/app/g2/`

Use small cohesive modules. A reasonable layout is:

- `records.py` — immutable domain/event records and enums;
- `bars.py` / `causal.py` — completed-bar views and availability rules;
- `features.py` — exact eight-column G2-V0 state;
- `models.py` — fixed ridge/scaling/monthly fit manifests;
- `distribution.py` — prequential archive and fallback distribution;
- `forecast.py` — continuous prediction construction;
- `utility.py` — LONG/SHORT NET_R labels and utility heads;
- `risk.py` — sizing, one-position and path-drawdown governor;
- `execution.py` — entry/stop/expiry/friction/funding/filter semantics;
- `cycle.py` — adapter around the preserved causal ACP implementation;
- `store.py` — append-only/immutable event storage;
- `core.py` — authoritative scientific state machine;
- `replay.py` / `service.py` / `api.py` — thin product/replay boundary;
- `fixtures.py` — synthetic deterministic acceptance fixtures.

Names may vary if a simpler layout is clearer. Do not mix G2 economic semantics into G1 modules.

## 6. Allowed G1 reuse

Reuse implementation only when semantics match.

Candidate reusable infrastructure:
- `backend/app/g1/bars.py` — completed-bar/causal aggregation patterns;
- `backend/app/g1/clock.py` — replay pacing/virtual-clock concepts;
- `backend/app/g1/canonical.py` — deterministic canonical serialization;
- `backend/app/g1/store.py` — immutable record-store patterns;
- `backend/app/g1/records.py` — patterns only where record semantics remain valid;
- `backend/app/g1/ledger.py` — accounting mechanics only where they exactly match G2 contracts;
- `backend/app/g1/cycle.py` and related cycle tests — frozen ACP lineage;
- `backend/app/g1/service.py` — causal cursor/completed-review separation pattern;
- existing source/manifests and data-integrity utilities.

Do **not** inherit automatically:
- G1 playbooks;
- G1 signal voting/conjunction logic;
- G1 forecaster semantics;
- G1 configuration selection;
- G1 thresholds;
- G1 economic results;
- G1 Phase A/B assumptions.

Prefer a thin reusable shared primitive over duplicating code if and only if moving it does not alter historical G1 behavior.

## 7. Data/I-O requirements

Implement a phase-bounded G2 loader boundary.

It must:
1. receive the authorized interval before observation I/O;
2. open only objects intersecting that interval;
3. reject unauthorized objects;
4. filter to bounds before returning observations;
5. log requested/opened/returned intervals;
6. allow metadata-only manifest reads without observation access;
7. fail tests if 2025+ observation objects are touched in G2-01.

For engineering market fixtures use only explicitly declared <=2024 windows.

No loader may enumerate 2025+ files during G2-01.

## 8. Feature-engine requirements

Implement exactly:

- LOCAL_STRUCTURE;
- CONTEXT_STRUCTURE;
- PRICE_EXTENSION;
- RELATIVE_PARTICIPATION;
- TAKER_IMBALANCE;
- VOLATILITY_STATE;
- LOCAL_STRUCTURE_X_PARTICIPATION;
- IMBALANCE_X_PRICE_RESPONSE.

Also compute the contract-defined:
- PRICE_RESPONSE;
- SIGMA_4H;
- ATR14_1H;
- completed Daily/Weekly display state.

Missing critical inputs produce explicit unavailable states. They never become zero and never use future forward-fill.

Every emitted G2 state must expose the maximum source timestamp consumed.

## 9. Model/forecast requirements

Implement deterministic monthly model fitting with:
- training-only median/MAD scaling;
- fixed clip [-8,+8];
- constant-feature zero behavior;
- fixed ridge penalties;
- mature-label cut-off;
- no random CV or model search.

A prediction record is emitted on every eligible decision candle, including unavailable forecasts.

Forecast output must contain:
- mean/median return;
- q10/q50/q90;
- p_positive;
- SIGMA_4H;
- calibration/evidence status;
- view strength and display label;
- direction;
- model contributions;
- source/model hashes;
- model-fit/training boundaries;
- latest admitted mature label timestamp.

Original predictions are immutable; outcomes append later.

## 10. Policy/actionability requirements

Implement standardized LONG and SHORT shadow labels exactly from the frozen geometry.

Fit separate utility heads with the same eight-column dictionary and fit schedule.

Until the relevant prequential evidence threshold is satisfied:
- action = NO_TRADE;
- reason includes `INSUFFICIENT_POLICY_EVIDENCE`.

Then implement the exact prudential-margin decision rule, including:
- LONG_SELECTED;
- SHORT_SELECTED;
- UTILITY_MARGIN_NOT_POSITIVE;
- UTILITY_MARGIN_TIE;
- PATH_UTILITY_OVERRIDES_TERMINAL_VIEW when applicable.

Forecast direction must never directly force the action.

## 11. Risk and execution requirements

Implement:
- virtual 10,000 USDT normalized research equity;
- 0.25% planned stop-risk sizing;
- max gross notional 1.0x equity;
- one open position;
- no pyramiding;
- no same-candle flip/re-entry;
- 5% peak-equity path drawdown stop;
- contract-filter rounding from a pinned/synthetic exchangeInfo snapshot;
- exact 1m entry/expiry requirements;
- stop-gap adverse fill semantics;
- base friction and declared stress scenarios as data/configuration, not hidden constants;
- settled funding at settlement time only;
- last-price funding proxy clearly flagged for historical fixtures;
- forecasts continue while a position is open.

Do not compute headline development economics in this work package.

## 12. Cycle requirements

G2-V0 cycle role is **shadow only**:
- no forecast coefficient;
- no utility coefficient;
- no action veto.

Reuse the existing causal ACP lineage and add the G2-required amplitude/stability fields.

The implementation must pass every test in `G2_CYCLE_CAUSALITY_CHECKPOINT_V1.md §13`:
1. G1/G2 numeric parity where semantics are preserved;
2. white-noise gate;
3. coherent-cycle gate;
4. amplitude=1/noise-sd=0.5 fixture;
5. pure linear trend no-USABLE;
6. isolated jump abstention;
7. varying-frequency bounded behavior;
8. prefix invariance;
9. gap/reset/full re-warm;
10. projection amplitude validity;
11. exact period-stability field;
12. delayed confirmed turns;
13. replay-speed identity.

Only the Research Director may classify the result as `AVAILABLE_FOR_RESERVED_REVISION` after reviewing the tests.

## 13. Immutable records/event store

Persist/serialize enough state to reconstruct every decision without rereading future data.

Required record families:
- model fit manifest;
- market/G2 state;
- prediction;
- prediction maturity/outcome event;
- decision;
- shadow LONG label;
- shadow SHORT label;
- order intent;
- simulated fill;
- funding event;
- stop/expiry event;
- closed trade;
- risk-state event;
- cycle shadow state;
- source/exposure audit event.

Use stable IDs and deterministic canonical hashes.

Never mutate the original prediction/decision record when an outcome arrives.

## 14. Replay and product surface

Expose a G2-specific API rather than silently rebranding `/api/v1/g1`.

Minimum functionality:
- list registered G2 engineering runs;
- create causal replay session;
- pause/start/step/speed;
- read causal cursor state;
- completed-run review only after run completion;
- inspect prediction -> decision -> trade/event lineage.

Frontend minimum:
- existing local app remains usable;
- Home/Market surface can show latest G2 state for a registered engineering fixture/window;
- Replay shows candles plus distinct prediction and decision/trade markers;
- detail inspection exposes feature states, forecast distribution, evidence/calibration, utility margins, reason codes, risk and execution state;
- cycle visibly marked SHADOW;
- all engineering fixtures/windows visibly labelled **NOT PERFORMANCE EVIDENCE**.

Do not build final visual polish in G2-01.

## 15. Required deterministic acceptance tests

Create focused G2 test modules. At minimum Gate B requires:

### Causality / bars
- completed 15m/1h/4h/D/W aggregation never reads incomplete bars;
- max source timestamp <= decision timestamp;
- prefix invariance for feature/forecast outputs;
- replay-speed identity;
- deterministic identical-run hash.

### Feature formulas
- exact hand-calculated fixtures for all eight columns;
- EWM warm-up/reset behavior;
- missing critical data -> unavailable, never zero;
- taker imbalance bounds and V<=0 handling;
- volatility/SIGMA edge cases;
- ATR14 exact fixture.

### Model fitting
- fit uses only labels mature at fit boundary;
- monthly fit boundary exact;
- training window/support gate exact;
- train-only scaling;
- constant training feature fixed to zero;
- fixed ridge penalty identity;
- no post-fit scaler mutation.

### Predictive distribution
- fallback status before prequential threshold;
- prequential archive uses only genuinely issued matured residuals;
- scientific-version residual isolation;
- exact q10/q50/q90/p_positive behavior;
- probability always carries calibration status.

### Policy
- shadow LONG/SHORT geometry exact;
- exact entry/expiry bar required;
- prudential margin cases: neither/one/both/tie;
- opposite terminal-view action emits override reason;
- insufficient utility evidence forces NO_TRADE.

### Risk/execution
- risk sizing and max-notional cap;
- filter rounding/minimum veto;
- one-position/no-flip behavior;
- drawdown-stop lock;
- gap stop worse-open fill;
- adverse friction by side;
- funding sign/timestamp/accounting;
- missing entry/exit/funding/filter data fail closed.

### Cycle
- all 13 checkpoint tests above.

### Records
- prediction/decision immutability;
- append-only maturity/outcome;
- stable hash;
- full lineage reconstruction;
- reason codes are canonical.

### Data boundary
- <=2024 engineering window allowed;
- 2025+ observation access rejected before open;
- unauthorized object-touch test fails;
- metadata-only manifest read does not read observations.

### Product/API
- causal cursor never exposes future realization/fill;
- completed review unavailable before completion;
- API output matches authoritative G2 core;
- UI does not derive authoritative decisions independently.

## 16. Allowed exposed-data engineering checks

After synthetic tests pass, use at most a few small explicitly named <=2024 windows solely to verify:
- parser correctness;
- aggregation parity;
- source timestamp semantics;
- prefix invariance;
- deterministic replay;
- API/frontend rendering.

Before each such check, record the window and engineering purpose in the G2 ledger/artifact.

Forbidden outputs from these windows:
- cumulative strategy return;
- Sharpe;
- profit factor;
- economic ranking;
- model/version preference;
- threshold choice.

## 17. Validation command

Integrate G2 into the normal deterministic validation entry point:

`python scripts/check.py`

Add narrower commands/tests if useful, but the full repository validation must remain green.

Frontend tests/build must remain green.

## 18. Deliverables

Required code/artifacts:
- `backend/app/g2/` authoritative implementation;
- G2-focused backend tests;
- G2 API integration;
- minimal frontend Home/Replay integration;
- deterministic synthetic fixtures;
- any phase-bounded data access helper required by G2;
- concise engineering validation artifact under `reports/validation/`;
- concise checkpoint report under `reports/checkpoints/`.

Do not alter the frozen G2 scientific contracts to make implementation easier. If a true contradiction is found, stop that specific path and document it for Research Director review.

## 19. Executor completion state

At executor completion, leave G2-01 as:

`EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_GATE_B_REVIEW`

Do not:
- authorize G2-02;
- run G2-V0 economic development;
- mark cycle predictive utility proven;
- declare a candidate/Champion;
- change `validated_strategy`;
- enable production paper trading.

## 20. Gate B pass criteria

Research Director may pass Gate B only if:

1. all deterministic causal/integrity tests pass;
2. frozen contract parity is demonstrated;
3. no protected outcomes were touched;
4. exposed engineering windows were used only for engineering purposes;
5. G2-V0 predictions are emitted continuously when data/model state permits;
6. NO_TRADE/reason semantics work when they do not;
7. risk/execution/event records are reproducible and inspectable;
8. cycle code receives a reviewed method disposition;
9. replay and API are driven by the same authoritative G2 core;
10. repository full validation remains green.

Only after Gate B may the Research Director design/authorize G2-02 economic development.
