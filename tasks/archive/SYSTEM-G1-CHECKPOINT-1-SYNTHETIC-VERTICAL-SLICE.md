# CURRENT TASK — SYSTEM-G1-CHECKPOINT-1-SYNTHETIC-VERTICAL-SLICE

Status: IMPLEMENTATION_AUTHORIZED — SYNTHETIC/CAUSAL ONLY — MARKET OUTCOMES FORBIDDEN

## Authority

Owner mission:
`docs/canonical/OWNER_PRODUCT_MISSION_V2.md`

Strategic architecture:
`docs/canonical/PROFESSIONAL_MULTISIGNAL_SYSTEM_ARCHITECTURE_V1.md`

Decision:
`decisions/ADR-0044-ADOPT-SYSTEM-G1-PROFESSIONAL-MULTISIGNAL-ARCHITECTURE.md`

Constitution:
`governance/SCIENTIFIC_CONSTITUTION.md` Version 4.0.

Core contracts:
`research/protocols/SYSTEM-G1-CORE-CONTRACTS-V1.md`

Cycle contract:
`research/protocols/SYSTEM-G1-CYCLE-METHOD-V1.md`

Playbooks are registered but **their historical-performance definitions are not yet authorized**:

- `research/playbooks/SYSTEM-G1-P1-DIRECTIONAL-CONTINUATION.md`
- `research/playbooks/SYSTEM-G1-P2-FAILED-AUCTION-REENTRY.md`

## Objective

Build the first causal synthetic vertical slice of System G1.

The checkpoint must prove that the architecture can represent and replay a professional
multi-signal LONG/SHORT/NO_TRADE system without look-ahead and without accidentally reviving the old
ALIGNED strategy.

This task may use synthetic fixtures only for new System G1 market/replay behavior.

It does **not** authorize a System G1 historical backtest, development batch or inspection of new
market outcomes.

## Mandatory read set

Read only:

1. `AGENTS.md`
2. `docs/operations/NEW_CHAT_BOOTSTRAP.md`
3. Constitution Version 4.0 active section
4. `state/current_state.json` -> `current_project_status`
5. this task
6. System G1 architecture
7. System G1 core contracts
8. System G1 cycle method contract
9. P1/P2 cards
10. the smallest existing backend/frontend/accounting files required for reuse

Do not reopen historical research.

## Stage 0 — migrate fail-closed semantics first

The current repository temporarily keeps
`current_project_status.disposition=PARKED_NO_CREDIBLE_EDGE_UNDER_CURRENT_CONSTRAINTS`
because the legacy app guard only fails closed for that exact value.

Replace this brittle behavior before any other surface becomes reachable.

Required behavior:

- if `current_project_status.validated_strategy is null`, the production/live action surface must
  not evaluate ALIGNED or any historical strategy;
- product analysis returns NO_TRADE with a development/no-validated-strategy status;
- paper-trade creation remains disabled;
- old generic research-run start remains disabled unless a future task explicitly authorizes it;
- no old ALIGNED/predictive family can become an active fallback because the strategic disposition
  changed.

After deterministic tests prove this, update state so:

- `current_project_status.disposition` =
  `PROFESSIONAL_MULTISIGNAL_PAPER_SYSTEM_DEVELOPMENT_ARCHITECTURE_ADOPTED_PROTOCOLS_PENDING`;
- `strategic_disposition` remains the same value;
- remove/resolve the temporary operational compatibility note;
- `validated_strategy = null`;
- operational action remains NO_TRADE;
- market trial / confirmation / prospective collection remain false.

## Stage 1 — System G1 domain/event skeleton

Implement minimal versioned domain records matching the core contract:

- RunManifest;
- SignalSnapshot;
- CycleState;
- MarketState;
- ModelArtifact;
- PredictionSnapshot;
- PredictionRealization;
- DecisionSnapshot;
- TradePlan;
- OrderFillEvent;
- PositionLedger / position state;
- HotWindow;
- PostAnalysisReport metadata;
- ResearchExposureRecord or the existing equivalent.

Do not over-generalize into a framework for arbitrary assets/strategies.

BTCUSDT/System G1 is sufficient.

Issued state/prediction/decision records must be immutable by construction or storage policy.

## Stage 2 — causal completed-bar aggregation and virtual clock

Implement a synthetic replay provider and deterministic UTC aggregation sufficient for:

- 1m source events;
- 3m;
- 15m;
- 1h;
- 4h;
- completed UTC day;
- weekly/monthly boundaries where synthetic fixtures exercise them.

Required:

- higher-timeframe bars unavailable until complete;
- explicit `available_at`;
- virtual cursor;
- start / pause / single-step / speed semantics;
- speed changes wall-clock pacing only;
- identical event/output identities at every replay speed;
- future observations rejected.

Do not use current wall-clock time as scientific event identity.

## Stage 3 — native bidirectional reference-paper ledger

Adapt/reuse existing accounting rather than forking two ledgers.

Reference paper instrument semantics:

BTCUSDT USD-M traded-price reference for both LONG and SHORT.

Synthetic tests must prove:

- LONG gains/loss signs;
- SHORT gains/loss signs;
- quantity/notional/equity bookkeeping;
- adverse fee/friction direction;
- funding credit/debit semantics for signed positions;
- next-eligible-minute fill after readiness/delay;
- missing-minute unscorable/rejected handling;
- adverse gap handling;
- same-minute stop/target collision conservative resolution;
- maximum-hold expiry;
- one-position occupancy;
- no pyramiding/hedging;
- 0.25% planned-risk sizing with <=1x gross notional;
- 1% UTC-day entry stop;
- 5% run drawdown entry stop.

Do not claim exchange liquidation/margin fidelity.

## Stage 4 — prediction / decision / realization pipeline

Create a deterministic synthetic prediction emitter that exercises the **contract**, not real market
skill.

At every eligible synthetic 15m candle it must be capable of emitting:

- UP / DOWN / NEUTRAL / UNAVAILABLE;
- raw probability fields with calibration status;
- terminal-return summary fields;
- risk/support fields;
- LOW/MEDIUM/HIGH conviction;
- actionability;
- linked market/cycle/model IDs.

Use fixture-controlled values; do not invent or fit a real statistical model in this checkpoint.

PredictionRealization must be a separate later event after synthetic +4h maturity.

DecisionSnapshot exists for every eligible candle, including NO_TRADE.

Synthetic fixtures must exercise:

- no trade with weak prediction;
- HIGH conviction but risk-blocked NO_TRADE;
- LONG plan;
- SHORT plan;
- conflicting playbook NO_TRADE.

Do not implement historical P1/P2 profitability rules yet.

## Stage 5 — cycle method implementation and synthetic method evidence

Implement the frozen
`SYSTEM-G1-CYCLE-METHOD-V1` exactly enough to run its synthetic method-validation fixtures.

Required six scales and resolutions/ranges are fixed by the contract.

No alternate cycle method, period range, smoothing constant or market-return tuning.

Produce deterministic synthetic diagnostics for:

- clean in-band sinusoid;
- two-frequency mixture;
- trend + cycle;
- white noise;
- abrupt period change;
- amplitude decay;
- missing observations.

Important scientific boundary:

**Claude must NOT choose the final WEAK/USABLE quality thresholds from these diagnostics.**

Return the synthetic diagnostic artifact to the Research Director.

Until a later Director adjudication freezes those thresholds:

- all cycle states exposed to the trading-decision path remain `METHOD_NOT_READY`;
- cycle state may be displayed diagnostically but cannot raise conviction or authorize a trade.

Tests must prove no cycle influence before activation.

## Stage 6 — replay API and one functional UI vertical slice

Implement the smallest V1 Backtest/Replay slice needed to demonstrate architecture using only a
synthetic registered run.

It must include:

- replay chart advancing with virtual time;
- play/pause;
- single-step;
- speed selection;
- prediction glyph above eligible decision candle;
- decision glyph below eligible decision candle;
- LONG/SHORT entry and exit marks at simulated execution times;
- hover/detail for prediction snapshot;
- hover/detail for decision/trade;
- a small current signal/state panel;
- current prediction panel;
- current LONG/SHORT/NO_TRADE decision panel;
- matured-only running stats.

The synthetic dataset may be bundled as a tiny test/dev fixture.

Do not expose free scientific parameter knobs.

Do not convert the old production ALIGNED page into a new historical-performance claim.

The live/home production action surface remains fail-closed NO_TRADE because no G1 strategy is
validated yet.

## Stage 7 — event/news isolation contract in code

Implement only the storage/API boundary or placeholder necessary to prove:

- HotWindow can be created from replay output;
- PostAnalysisReport is a separate after-run entity;
- neither can be consumed by Signal/MarketState/Prediction/Decision code.

Do not browse the web or fetch news in this task.

## Reuse requirements

Reuse existing:

- FastAPI / React app shell;
- canonical data models/utilities where semantics fit;
- cost/accounting primitives where correct for signed positions;
- manifests/provenance patterns;
- deterministic IDs/replay conventions;
- tests/helpers.

Explicitly adapt LONG-only assumptions rather than silently wrapping them.

Do not build:

- a generic multi-asset platform;
- exchange connectivity;
- WebSocket execution;
- real-money support;
- generic strategy plugin marketplace;
- ML framework;
- optimizer.

## Absolute prohibitions

Do not:

- run System G1 on real historical BTC outcomes;
- inspect post-cutoff/protected market data;
- fetch new market data;
- calculate P1/P2 performance;
- fit a real forecaster;
- choose cycle quality thresholds from BTC behavior;
- define/optimize G1 trigger thresholds based on outcomes;
- revive Candidate #1;
- run ALIGNED;
- create a third playbook;
- create Candidate #2;
- authorize prospective collection;
- place orders or use credentials.

Existing historical result files may be read only when a deterministic repository test requires
format compatibility; do not analyze their market content.

## Required validation

At minimum:

- focused System G1 synthetic tests;
- causal future-data rejection tests;
- replay-speed invariance;
- long/short accounting tests;
- risk-control tests;
- cycle synthetic diagnostic replay;
- API fail-closed test proving old analyser is not called;
- frontend tests for replay annotation semantics;
- ruff;
- mypy;
- full backend tests;
- frontend checks;
- `scripts/check.py --no-data`.

Do not run data-mode checks that inspect market outcomes.

## Artifacts

Create:

- one concise Checkpoint-1 implementation validation JSON;
- one checkpoint Markdown report;
- one cycle synthetic diagnostic artifact;
- architecture/schema API docs only where needed.

Do not create a G1 historical experiment result.

## Post-task state

On successful implementation:

- strategic disposition remains System G1 architecture adopted;
- current operational disposition may now equal the System G1 strategic disposition because
  fail-closed no longer depends on `PARKED`;
- `validated_strategy = null`;
- action output = NO_TRADE;
- active generation = SYSTEM_G1;
- historical market trial authorized = false;
- confirmation = false;
- prospective collection = false;
- Champion NONE;
- real money false;
- cycle status = `SYNTHETIC_DIAGNOSTICS_PENDING_RESEARCH_DIRECTOR_QUALITY_GATE`;
- next task = Research Director Checkpoint-1 review; executor market work forbidden.

Archive this task and leave a review-only CURRENT_TASK.

## Git

Local commits on main are authorized after full no-data validation.

Do not push.

## Completion report

Return only:

`SYSTEM_G1_CHECKPOINT_1_READY_PENDING_RESEARCH_DIRECTOR_REVIEW`

Then:

- changed_files
- local_commit_sha(s)
- fail_closed_migration: PASS/FAIL
- domain_contracts: PASS/FAIL
- causal_aggregation_virtual_clock: PASS/FAIL
- long_short_ledger: PASS/FAIL
- prediction_decision_pipeline: PASS/FAIL
- cycle_method_implementation: PASS/FAIL
- cycle_synthetic_diagnostic_artifact
- cycle_active_in_decisions: NO
- replay_api: PASS/FAIL
- replay_ui_vertical_slice: PASS/FAIL
- hot_window_post_analysis_isolation: PASS/FAIL
- synthetic_test_count
- full_no_data_validation: PASS/FAIL
- real_historical_g1_outcomes_inspected: NO
- new_market_data_accessed: NO
- sealed_queries: 0
- validated_strategy: NONE
- operational_action: NO_TRADE
- champion: NONE
- real_money: false
- blockers: concise only
