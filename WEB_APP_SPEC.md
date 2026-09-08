# Trading Bot — Web Application Product Spec v0.1

## Product philosophy

The Owner is not a professional trader.

The UI must answer the important question first:

> What does the currently approved system say I should do now?

Scientific detail is available underneath, but the primary interface must remain understandable.

## Page 1 — Dashboard / Decision Now

This is the default page.

Primary action:

`ANALYZE MARKET`

Primary result must be visually obvious:

### Case A

```text
NO_TRADE
No approved setup is currently valid.
```

### Case B

```text
LONG BTCUSDT

Signal time
Entry
Stop loss
Take profit / exit rule
Expiry
Strategy version
```

Confidence appears only if it has a calibrated meaning.

Never display fake precision.

Also show:
- current BTC price;
- data freshness;
- strategy status;
- market/regime label if the approved model uses one;
- paper/live mode badge.

The application is PAPER ONLY during the research program.

## Page 2 — Market

Interactive BTCUSDT candlestick chart.

Required future overlays:
- signal timestamp;
- entry;
- stop loss;
- take profit / exit;
- paper-trade markers;
- relevant approved indicators only.

Allow timeframe switching for visualization, but visual timeframe switching must not change the approved strategy rules.

## Page 3 — Paper Trades

Show all prospective paper trades.

Columns/cards:
- signal time;
- entry time;
- direction;
- entry;
- stop;
- target/exit;
- expiry;
- outcome;
- net R;
- strategy version.

Failed and losing trades must remain visible.

## Page 4 — Strategy Statistics

Owner-friendly statistics:
- net expectancy in R;
- cumulative paper P&L in R;
- profit factor;
- maximum drawdown;
- hit rate;
- average win;
- average loss;
- trade count;
- effective sample size when available;
- transaction-cost drag;
- current evidence stage.

Include charts for:
- equity / cumulative R;
- drawdown;
- rolling expectancy;
- outcome distribution;
- performance by regime when scientifically valid.

Always distinguish:
- development backtest;
- walk-forward;
- sealed evaluation;
- future paper evidence.

Never visually mix them into one misleading performance number.

## Page 5 — Research Lab

High-level scientific status, not raw logs.

Show:
- current approved strategy / Champion or NONE;
- challenger under evaluation;
- current experiment;
- number of completed experiments;
- recent negative results;
- evidence stage;
- sealed budget status when implemented;
- next research checkpoint.

The UI must make negative results look normal, not like system errors.

## Page 6 — System

Show:
- backend health;
- market-data freshness;
- local database status;
- current software version;
- current strategy version;
- paper mode status;
- last successful analysis;
- errors that genuinely require attention.

## UX rules

- desktop-first but responsive;
- dark mode preferred for long chart sessions;
- clear red/green semantics only where they do not imply certainty;
- `NO_TRADE` should look like a successful system decision, not failure;
- paper mode must always be unmistakable;
- real-money buttons do not exist during the research phases;
- raw logs are not part of the normal Owner UX.

## Future V2 additions

When server-hosted:
- notification history;
- live system uptime;
- current active paper position;
- signal alert acknowledgement;
- remote read-only dashboard.

No V2 functionality should distort V1 architecture prematurely.
