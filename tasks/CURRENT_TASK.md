# CURRENT TASK — OWNER-MISSION-V2-ASTRA-STRATEGIC-REDESIGN

Status: OWNER_SCOPE_CHANGE_REOPENING_REVIEW_PENDING_ASTRA — EXECUTOR MARKET WORK FORBIDDEN

## Owner-authorized mission

Canonical product mission:

`docs/canonical/OWNER_PRODUCT_MISSION_V2.md`

Decision:

`decisions/ADR-0043-OWNER-PROFESSIONAL-MULTISIGNAL-LONG-SHORT-MISSION.md`

The Owner has clarified that Trading Bot is intended to be a professional multi-signal BTC trading
system, not a sequence of isolated standalone-alpha candidate tests.

The intended V1 includes:

- local live web dashboard;
- live BTC chart;
- visible professional signal / market-state board;
- continuous prediction on every eligible candle;
- distinct selective `LONG / SHORT / NO_TRADE` paper decision;
- multi-timeframe analysis, including explicit multi-timeframe cyclical research;
- manual fast-forward backtest/replay with chart and predictions changing candle by candle;
- separate prediction and trade annotations per candle;
- trade outcome history and statistics;
- local cached historical market/signal data where feasible;
- post-backtest event/news investigation of predeclared hot periods;
- established professional trader concepts first, not invented exotic R&D.

Prediction quality and selective trade economics are separate evaluation layers. Low-conviction
prediction misses remain visible but do not automatically invalidate a high-conviction selective
trading policy.

## Relationship to parked state

ADR-0042 parking remains valid for the previous narrower programme and all historical closures remain
binding.

This Owner-authorized scope change is a legitimate ADR-0042 reopening trigger.

However, it does **not** itself authorize a market experiment.

Active alpha allocation remains zero until Astra completes strategic redesign.

Candidate #1 remains closed. No rescue.

## Required next decision

Astra must redesign the bounded research and product architecture around
`OWNER_PRODUCT_MISSION_V2`.

The strategic output must define, at minimum:

1. product architecture and page-level functional model;
2. professional signal/playbook catalogue and how components can interact;
3. multi-timeframe architecture, with special treatment of cyclical analysis;
4. continuous candle prediction contract;
5. selective LONG/SHORT/NO_TRADE decision contract;
6. risk/execution contract;
7. replay/backtest architecture and per-candle visualization semantics;
8. prediction-vs-trade evaluation methodology, including importance/conviction strata;
9. historical data/source plan and what can/cannot be reconstructed point-in-time;
10. post-backtest hot-period news/event research boundary;
11. staged research programme that reuses prior evidence without requiring each signal to prove
    standalone profitability;
12. bounded anti-overfitting/search governance appropriate to a composite professional trading
    system;
13. Constitution/state/schema migration plan from the old narrow scope.

Astra must not simply choose another Candidate Card or another isolated alpha hypothesis.

## Executor instruction

No Claude Code market/research implementation is authorized yet.

Do not:

- run a backtest or market experiment;
- create Candidate #2;
- rescue Candidate #1;
- inspect new market outcomes;
- fetch new market data;
- modify the trading algorithm;
- implement LONG/SHORT execution;
- build the new UI;
- open a new source/model search.

Governance/document reconciliation after Astra may be delegated to Claude.

Champion NONE. Real money false.
