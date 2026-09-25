# CURRENT TASK — FIX-SYSTEM-G1-INCOMPLETE-BAR-RECURSIVE-STATE-V1

Status: PRE-EXECUTION_IMPLEMENTATION_FIX_AUTHORIZED — HISTORICAL G1 EXECUTION FORBIDDEN

## Authority

`decisions/ADR-0047-G1-IMPLEMENTATION-REVIEW-INCOMPLETE-BAR-CORRECTION.md`

The System G1 Development implementation is otherwise accepted.

This task fixes exactly one pre-outcome contract defect.

## Problem

The frozen G1 protocol defines ADX/DI, EMA structure, ATR and daily EMA from completed bars.

Current implementation marks an incomplete aggregated bar's output UNAVAILABLE but still updates the
recursive indicator with the partial OHLC/close. That can contaminate later READY values.

No real market outcome has been inspected, so correct this before execution.

## Required change

### 15m ATR

On any incomplete 15m bar:

- reset Wilder ATR recursive state;
- publish UNAVAILABLE;
- do not consume the incomplete OHLC/close;
- subsequent complete bars re-warm normally.

### 1h EMA structure

On any incomplete 1h bar:

- reset EMA20 and EMA50;
- publish UNAVAILABLE;
- do not consume its close;
- re-seed only from subsequent complete 1h closes.

### 4h ADX/+DI/-DI

On any incomplete 4h bar:

- reset the entire Wilder ADX/DI state;
- publish UNAVAILABLE;
- do not consume its OHLC;
- re-warm only from subsequent complete 4h bars.

### Daily context

On any incomplete 1d bar:

- reset daily EMA and its lookback history;
- boundary and daily direction become UNAVAILABLE;
- do not consume the incomplete day's close/high/low;
- re-warm from subsequent complete days.

Do not alter:

- Session VWAP behavior;
- Participation/RVOL behavior;
- cycle behavior;
- forecaster risk-window behavior;
- aggregation semantics.

## Required tests

For ATR, hourly EMA, ADX and daily EMA separately:

1. build two synthetic histories identical before an incomplete bar;
2. change the incomplete bar's OHLC/close radically between the two histories;
3. prove published state at the incomplete bar is UNAVAILABLE;
4. prove subsequent recursive state after reset/re-warm is identical between the two histories;
5. prove no READY reading appears before the normal frozen warm-up is satisfied.

Also retain/verify whole-bar-gap behavior.

Add an integration test showing an incomplete higher-timeframe bar cannot change a later P1/P2
decision after the relevant indicators have properly re-warmed.

## Identity / validation

Because scientific implementation code changes:

- update/regenerate `SYSTEM-G1-DEVELOPMENT-IMPLEMENTATION-V1.json` code identities;
- update the implementation checkpoint with the correction;
- protocol hash must remain unchanged;
- configuration identity must change only as mechanically implied by corrected implementation
  identity if it includes code identity;
- source bindings remain unchanged.

Run all focused G1 synthetic tests and complete `scripts/check.py --no-data`.

No data-mode command.

## Absolute prohibitions

Do not:

- read real BTC observations;
- run Phase A or Phase B;
- alter any G1 threshold/timeframe/playbook/cycle/forecaster/cost/risk rule;
- add a configuration;
- change source binding;
- fit the real forecaster;
- inspect P1/P2 historical performance.

## Post-task

Set:

`SYSTEM_G1_DEVELOPMENT_IMPLEMENTATION_READY_PENDING_RESEARCH_DIRECTOR_EXECUTION_REVIEW`

Historical execution remains false.

Leave CURRENT_TASK review-only.

## Git

Local commits on main are authorized.

Do not push.

## Completion report

Return only:

`SYSTEM_G1_INCOMPLETE_BAR_FIX_READY_PENDING_RESEARCH_DIRECTOR_REVIEW`

Then:

- changed_files
- local_commit_sha(s)
- protocol_identity: PASS/FAIL
- atr_incomplete_reset: PASS/FAIL
- ema_incomplete_reset: PASS/FAIL
- adx_incomplete_reset: PASS/FAIL
- daily_incomplete_reset: PASS/FAIL
- partial_bar_noncontamination_tests: PASS/FAIL
- integration_no_decision_contamination: PASS/FAIL
- implementation_identity_regenerated: PASS/FAIL
- full_no_data_validation: PASS/FAIL
- real_historical_g1_outcomes_inspected: NO
- new_market_data_accessed: NO
- sealed_queries: 0
- validated_strategy: NONE
- operational_action: NO_TRADE
- champion: NONE
- real_money: false
- blockers: concise only
