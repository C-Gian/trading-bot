# ADR-0047 — System G1 Development implementation review: accepted subject to incomplete-bar fail-closed correction

Status: ACCEPTED WITH REQUIRED PRE-EXECUTION FIX — Research Director, 2026-09-25

## Review basis

Reviewed remote implementation commit:

`e6062ad487acdbf09d1b6b483558ce4f929a5b70`

against:

- Constitution 4.0;
- ADR-0046;
- `research/protocols/SYSTEM-G1-DEVELOPMENT-V1.md`;
- implementation validation/checkpoint;
- staged batch guard;
- source bindings;
- forecaster;
- indicators;
- P1/P2;
- scoring/adjudication.

No real historical System G1 outcome was inspected.

## Accepted implementation findings

The implementation is accepted in substance for:

- active admitted cycle semantics;
- seven and only seven configurations;
- P1/P2 causal state machines;
- conflict/occupancy rules;
- S-full conviction semantics;
- annual expanding forecaster with exact 4h purge and fixed shrinkage;
- Phase-A 2021-2022 automatic selection;
- Phase-B selected-configuration-only lock;
- write-once artifacts and source execution guard;
- source identity bindings;
- trade/economic/prediction scoring;
- 1m primary delay and declared stress books;
- replay/UI compatibility;
- no preview or caller override of the selected Phase-B configuration.

## Accepted ordinary implementation choices

The following executor choices are accepted and frozen before market outcomes:

1. session VWAP becomes unavailable for the remainder of a UTC session after any missing minute;
2. previous-day boundaries require a complete prior UTC day;
3. RVOL requires twenty contiguous complete prior 15m candles;
4. P1 unavailable daily state fails the daily-not-opposing requirement;
5. P1 may trigger on the arming candle because the frozen four-candle lifetime explicitly includes
   the arming candle;
6. a plan veto may preserve base-trigger/conviction evidence but cannot create a trade proposal or a
   playbook conflict;
7. HIGH conviction requires exactly one complete S-full playbook/direction pair;
8. forecaster MAE uses the frozen mixture mean as point forecast; weighted quantiles use lower
   inverse CDF;
9. P&L is attributed by exit year; an unresolved position at a phase boundary is closed
   unscorable without using prices beyond that phase;
10. funding timestamps are mapped to their UTC minute;
11. entry orders expire fifteen minutes after the frozen readiness+delay point. Because the ledger
   already rejects a missing exact eligible fill minute rather than rolling forward, this expiry is
   an operational safety bound rather than an alternate fill rule.

## Required correction

The implementation currently lets an aggregated `INCOMPLETE` 15m/1h/4h/1d bar update recursive
indicator internals while publishing that bar's reading as UNAVAILABLE.

That is not accepted.

The frozen protocol specifies indicators on **completed** bars. Feeding partial OHLC into EMA,
Wilder ATR, Wilder ADX/DI or daily EMA contaminates later recursive state even though the partial
bar itself is not used directly.

Before historical execution:

- any incomplete 15m bar must reset/re-warm ATR state and be UNAVAILABLE;
- any incomplete 1h bar must reset/re-warm EMA20/EMA50 state and be UNAVAILABLE;
- any incomplete 4h bar must reset/re-warm ADX/DI state and be UNAVAILABLE;
- any incomplete 1d bar must reset/re-warm daily EMA history, make boundary/direction UNAVAILABLE,
  and not contribute to later recursion;
- the next complete bar starts the normal frozen warm-up after the reset;
- no partial OHLC may enter later recursive indicator values.

Participation's explicit complete-window logic, VWAP's session-broken rule, cycle gap/re-warm rules
and the forecaster's 97-complete-bar risk window already fail closed appropriately and should not be
relaxed.

## Execution status

Historical System G1 execution remains **NOT AUTHORIZED**.

After the correction:

- regenerate implementation identities;
- rerun all synthetic/no-data validation;
- prove partial-bar perturbations cannot influence any later READY recursive indicator value until
  the declared re-warm has completed;
- return for one final Research Director execution review.

No scientific threshold, playbook rule, configuration, forecaster rule, cost/risk rule or source
binding may change in this correction.

Champion NONE. Validated strategy NONE. Operational action NO_TRADE. Real money false.
