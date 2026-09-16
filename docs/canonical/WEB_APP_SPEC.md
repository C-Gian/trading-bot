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
BTCUSDT — 24h forecast

Direction            UP | DOWN | UNCERTAIN
Probability          calibrated, that the declared direction is correct
Strength             0-100 magnitude scale, NOT a probability
Expected move        signed %, and approximate quote-currency move
Uncertainty          coverage, sample size, context
Predictor version

Action               LONG | NO_TRADE   (paper only)
```

The forecast and the action are two separate blocks. The action never restates the
forecast, and the forecast is never re-derived from the action.

If the action is `LONG`, the paper plan follows underneath: signal time, entry, stop loss,
take profit / exit rule, expiry, strategy version.

Probability appears only when it is empirically calibrated. Strength is always labelled as
magnitude and never as probability. An uncalibrated model score is never displayed as a
probability.

Until an approved predictor exists, the surface says so rather than displaying a
placeholder number.

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

Prediction quality and trade economics are separate sections and are never mixed into one
headline number.

Predictive quality (the prediction layer) reports, per
[`PREDICTIVE_EVALUATION_CONTRACT_V1.md`](PREDICTIVE_EVALUATION_CONTRACT_V1.md):
- actionable directional win rate, always shown with sample size and coverage;
- calibration: Brier score and a reliability table;
- magnitude error (MAE) and the signed magnitude-match diagnostic;
- comparison against the predeclared baselines;
- a dependence-aware uncertainty interval;
- a breakdown by chronological fold, including unfavourable ones.

Trade economics (the economic layer) reports:
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
