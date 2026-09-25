# CURRENT TASK — IMPLEMENT-SYSTEM-G1-DEVELOPMENT-V1

Status: IMPLEMENTATION_AUTHORIZED — HISTORICAL G1 EXECUTION FORBIDDEN

## Authority

- Constitution 4.0
- `decisions/ADR-0046-ACCEPT-G1-CYCLE-QUALITY-AND-ACTIVATE-CYCLE-COMPONENT.md`
- `research/protocols/SYSTEM-G1-DEVELOPMENT-V1.md`
- `research/protocols/SYSTEM-G1-CORE-CONTRACTS-V1.md`
- `research/protocols/SYSTEM-G1-CYCLE-METHOD-V1.md`
- `research/protocols/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.md`

The Research Director has accepted the synthetic cycle quality gate and frozen the complete
System G1 Development V1 scientific specification.

This task implements that specification only.

It does **not** authorize running System G1 on historical BTC outcomes.

## Mandatory read set

Read only:

1. `AGENTS.md`
2. `docs/operations/NEW_CHAT_BOOTSTRAP.md`
3. Constitution 4.0 active section
4. `state/current_state.json` -> current G1 blocks
5. this task
6. `SYSTEM-G1-DEVELOPMENT-V1.md`
7. ADR-0046
8. existing `backend/app/g1` Checkpoint-1 implementation
9. smallest existing source/manifest parsers needed to wire future execution

Do not reopen old research.

## Objective

Implement the frozen G1 system end-to-end so that a later explicitly authorized runner can perform
the one historical Development batch exactly as preregistered.

All new behavior must be validated with synthetic/deterministic fixtures or outcome-blind manifest
identity checks.

No real historical G1 performance metric may be produced in this task.

## 1. Activate the admitted cycle component

Implement ADR-0046 quality labels and timing qualifier exactly:

- UNAVAILABLE / WEAK / USABLE;
- FAST = 45m + 3h;
- INTERMEDIATE = 1d + 4d;
- SLOW = 1w + 4w;
- LONG support iff >=1 FAST USABLE, all USABLE FAST are RISING, and no USABLE INTERMEDIATE has most
  recent confirmed DOWN turn;
- SHORT symmetric;
- SLOW disagreement is recorded only;
- otherwise CYCLE_MIXED_OR_WEAK.

Remove the Checkpoint-1 hardcoded METHOD_NOT_READY decision behavior.

Do not change cycle math, quality threshold, persistence, scale bands or synthetic gate.

Synthetic tests must prove cycle alone cannot create a setup/trade.

## 2. Implement frozen shared indicators/state

Implement exactly the protocol definitions:

- 4h Wilder ADX/+DI/-DI 14 with 25/20 TREND/RANGE boundaries;
- 1h EMA20/EMA50 structure;
- 15m Wilder ATR14;
- UTC-session VWAP = cumulative quote volume / base volume;
- previous completed UTC-day high/low;
- completed daily EMA20 directional corroboration;
- 15m RVOL using prior-20 median excluding trigger candle;
- exchange-reported taker imbalance sign.

No alternative indicator period/threshold or fallback definition.

Every output must have causal `available_at`, readiness and missing-data semantics.

## 3. Implement P1 exactly

Implement one causal state machine for:

`SYSTEM-G1-P1-DIRECTIONAL-CONTINUATION`

including:

- directional prerequisites;
- 1h EMA20 pullback arming;
- four-15m-candle arming lifetime;
- exact 15m reclaim/break trigger;
- ATR stop buffer;
- exact 2R objective;
- 4h maximum hold;
- daily/participation/cycle full-system corroboration.

Synthetic fixtures must cover bullish, bearish, expiry, invalidation, unavailable input and no-lookahead.

Do not add another P1 variant.

## 4. Implement P2 exactly

Implement:

`SYSTEM-G1-P2-FAILED-AUCTION-REENTRY`

including:

- 4h RANGE prerequisite;
- previous-day boundary;
- 0.25 ATR excursion;
- same completed-15m re-entry;
- ATR stop buffer;
- UTC-session VWAP objective;
- minimum 1.50R;
- 4h maximum hold;
- participation/cycle full-system corroboration.

Synthetic fixtures must cover LONG, SHORT, insufficient excursion, failed re-entry, invalid reward/risk,
unavailable VWAP/boundary and no-lookahead.

Do not add another P2 variant.

## 5. Implement conflict / occupancy semantics

Exactly:

- opposite simultaneous P1/P2 -> NO_TRADE / PLAYBOOK_CONFLICT;
- same direction -> larger planned reward/risk;
- exact tie -> P1;
- one system position only;
- no double sizing.

Risk/data/occupancy vetoes occur after setup recognition.

## 6. Implement conviction

Use S-full evidence exactly:

- LOW;
- MEDIUM;
- HIGH.

HIGH requires exactly one complete S-full playbook/direction.

Risk/occupancy may block a HIGH-conviction trade without changing the conviction label.

No numeric learned conviction score.

## 7. Implement continuous forecaster

Implement the frozen 4h empirical shrunken forecaster:

- issue every eligible completed 15m candle;
- USD-M terminal 4h log return target;
- previous-96-15m-return prior risk scale;
- nine bias × conviction cells maximum;
- annual expanding training;
- exact 4h purge;
- fixed shrinkage `w=n/(n+256)`;
- empirical mixture probability/mean/median/q10/q90;
- probability status
  `EMPIRICAL_SHRUNK_CONDITIONAL_PROBABILITY_NOT_CALIBRATED`.

The model must **not** be fitted to real BTC data in this task.

Use synthetic training fixtures to prove:

- no future-year leakage;
- purge correctness;
- shrinkage formula;
- cell/unconditional mixture;
- probabilities bounded;
- weighted quantiles deterministic;
- low-support shrinkage;
- unavailable risk state.

The prediction must not gate trades.

## 8. Implement seven frozen configurations

Register exactly:

- S0
- S_FULL
- S_MINUS_CYCLE
- S_MINUS_PARTICIPATION
- S_MINUS_DAILY_HTF
- S_P1_ONLY
- S_P2_ONLY

No eighth configuration.

Implement shared deterministic configuration runner logic.

Synthetic tests must prove each configuration removes only its declared component/playbook.

## 9. Implement staged selector/evaluator guard

Build the future historical runner with a hard execution guard.

The implementation must support:

### Phase A

2021-2022 seven-configuration selection with exact eligibility and automatic selection rules from the
protocol.

### Phase B

2023-2024 selected-configuration-only evaluation.

Critical fail-closed behavior:

- Phase B cannot run before a Phase-A selection artifact exists;
- Phase B accepts only the automatically selected configuration ID;
- no caller may override selected configuration;
- if Phase A yields no eligible configuration, Phase B is impossible;
- the runner must refuse real execution unless a later state authorization explicitly permits the
  G1 historical batch.

Do not execute Phase A or Phase B on real market data now.

Synthetic fixture tests should exercise selection success and no-eligible rejection.

## 10. Implement scoring/adjudication

Implement the frozen metrics/gates, including:

- support/coverage;
- yearly and pooled trade economics;
- net R;
- equity return;
- profit factor;
- LONG/SHORT split;
- top-3 removal;
- max drawdown;
- 48bp cost stress;
- +5m delay stress;
- HIGH-conviction Brier vs training up-rate baseline;
- HIGH-conviction MAE vs zero-return baseline;
- exact terminal disposition ordering.

Use synthetic result fixtures only.

Do not add statistical/economic gates not present in the protocol.

## 11. Source bindings — identity only

Wire the future runner to existing repository source manifests/parsers needed for:

- official USD-M 1m klines;
- spot 1m context if needed;
- funding history/accounting;
- kline base/quote/taker-buy volumes.

You may read manifest metadata, schemas and parser code.

Do **not** scan real market observations or calculate signal/trade/prediction outcomes.

If an exact required field/source is unavailable, stop and report the blocker rather than substitute a
different source.

## 12. UI/replay integration

Upgrade the existing G1 replay types/UI so the real G1 records can display, once a later run exists:

- grouped signal board;
- cycle six-scale state + FAST/INTERMEDIATE/SLOW disagreement;
- MarketState;
- prediction fields and explicit not-calibrated probability status;
- LOW/MEDIUM/HIGH conviction;
- P1/P2 setup/decision reasons;
- LONG/SHORT/NO_TRADE;
- stop/objective/RR;
- above-candle prediction glyph;
- below-candle decision/trade glyph.

Use synthetic registered runs only in this task.

Production Home remains fail-closed NO_TRADE because `validated_strategy=null`.

## 13. Outcome exposure guard

Create a dedicated execution command/runner that refuses unless machine-readable state explicitly
contains a future Research Director G1 execution authorization.

Importing modules, running tests, `check.py --no-data`, or rendering synthetic replay must not read
real G1 market outcomes.

No convenience preview mode is allowed.

## Required validation

At minimum:

- cycle activation semantics;
- P1/P2 causal synthetic fixtures;
- indicator availability;
- forecaster leakage/purge/shrinkage tests;
- seven-configuration identity tests;
- staged selector lock tests;
- full economic/adjudication synthetic tests;
- LONG/SHORT execution regression;
- replay/API/frontend tests;
- fail-closed production action test;
- ruff;
- mypy;
- frontend lint/typecheck/build;
- full backend/frontend tests;
- `scripts/check.py --no-data`.

Do not run any data-mode command.

## Artifacts

Create:

- `reports/validation/SYSTEM-G1-DEVELOPMENT-IMPLEMENTATION-V1.json`;
- `reports/checkpoints/IMPLEMENT-SYSTEM-G1-DEVELOPMENT-V1.md`;
- any concise API/schema documentation needed for G1 records;
- protocol/code/config identity hashes.

Do not create a real G1 historical result.

## Post-task state

Set:

`SYSTEM_G1_DEVELOPMENT_IMPLEMENTATION_READY_PENDING_RESEARCH_DIRECTOR_EXECUTION_REVIEW`

and:

- historical G1 execution authorized = false;
- real G1 outcomes inspected = false;
- cycle method = ACTIVE_COMPONENT;
- forecaster real-fitted = false;
- P1/P2 real performance computed = false;
- validated strategy = null;
- production action = NO_TRADE;
- sealed queries = 0;
- Champion NONE;
- real money false.

Archive this task and leave CURRENT_TASK review-only.

## Git

Local commits on main are authorized after validation.

Do not push.

## Completion report

Return only:

`SYSTEM_G1_DEVELOPMENT_IMPLEMENTATION_READY_PENDING_RESEARCH_DIRECTOR_EXECUTION_REVIEW`

Then:

- changed_files
- local_commit_sha(s)
- protocol_identity: PASS/FAIL
- cycle_component_active_in_g1_logic: PASS/FAIL
- shared_state_indicators: PASS/FAIL
- p1_implementation: PASS/FAIL
- p2_implementation: PASS/FAIL
- conflict_occupancy: PASS/FAIL
- conviction: PASS/FAIL
- forecaster_implementation: PASS/FAIL
- seven_configurations: PASS/FAIL
- staged_selection_guard: PASS/FAIL
- scoring_adjudication: PASS/FAIL
- source_manifest_bindings: PASS/FAIL or blocker
- replay_ui_integration: PASS/FAIL
- execution_guard: PASS/FAIL
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
