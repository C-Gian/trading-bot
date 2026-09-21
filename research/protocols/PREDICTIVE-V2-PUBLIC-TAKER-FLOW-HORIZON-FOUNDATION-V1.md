# PREDICTIVE V2 PUBLIC TAKER FLOW HORIZON FOUNDATION V1

Status: RESEARCH_DIRECTOR_FROZEN_BEFORE_IMPLEMENTATION

## Question

Does free, exchange-native BTCUSDT aggressive taker-flow information contain reproducible OOS directional information, and how quickly does that information decay across 24h, 4h and 1h horizons?

## Source

Official Binance public archive only.

Markets:
- spot BTCUSDT 1m klines;
- USD-M perpetual BTCUSDT 1m klines.

Development source window:
- 2020-01-01 through 2024-12-31 inclusive.

Do not use post-cutoff data.

For every downloaded archive member, preserve source path, size and official checksum in an immutable manifest.

## Exact features

At each hourly decision timestamp T use only 1m bars fully completed by T.

For each market over the immediately preceding completed 60 minutes:

`buy_quote = sum(taker_buy_quote_volume)`

`total_quote = sum(quote_asset_volume)`

`imbalance = (2 * buy_quote - total_quote) / total_quote`

If total_quote <= 0, non-finite, any required minute is absent, duplicated, timestamp-invalid or incomplete, the feature vector is unavailable.

Feature order:

1. `SPOT_TAKER_IMBALANCE_1H`
2. `UM_TAKER_IMBALANCE_1H`
3. `SPOT_MINUS_UM_TAKER_IMBALANCE_1H`

No OHLCV return, funding, OI, calendar, on-chain, technical indicator, order-book, extra lag, interaction or hand-built regime feature is allowed.

## Targets

Same BTCUSDT spot terminal-sign definition, evaluated separately at exactly:

1. 24h
2. 4h
3. 1h

For horizon H:

`r_H = log(close[T+H] / close[T])`

UP if > 0, DOWN if < 0, exact zero NEUTRAL.

Horizon order is deliberately 24h -> 4h -> 1h because the current product target is 24h. Do not choose a horizon by maximizing an observed score.

## Evaluation folds

Because the public-source foundation begins in 2020, use annual outer evaluation folds:

2021, 2022, 2023, 2024.

Each fold trains only on earlier source/label data. Apply horizon-specific purge so no training label reaches into the outer evaluation period.

No random CV.

## Model

Exactly one model per horizon:

- StandardScaler;
- LogisticRegression, penalty=l2, C=1.0, fit_intercept=true, solver=lbfgs, max_iter=2000, tol=1e-8, class_weight=null;
- chronological 80% base-fit / 20% calibration within each outer-training set;
- calibration embargo = 2 * target horizon;
- training-only Platt calibration on raw decision score using unpenalized logistic regression;
- no hyperparameter search;
- no feature search;
- no action threshold and no LONG/NO_TRADE policy in this foundation.

Every feature-valid outer row receives calibrated p_up.

## Primary evidence

For each horizon:

- full-probability Brier score;
- matched constant probability control using TRAINING_UP_BASE_RATE per fold;
- primary effect = CONTROL_BRIER - MODEL_BRIER, so positive is better;
- fold-stratified moving-block bootstrap;
- block length = max(48h, 2 * target horizon);
- 10,000 replicates;
- family seed = 20260923;
- familywise alpha 0.05 across 3 horizons, Bonferroni alpha = 0.0166666667 per horizon;
- central interval mass = 0.9833333333;
- blocks never cross fold boundaries.

Secondary:
- log loss versus same training-base-rate control;
- ROC AUC;
- reliability bins;
- per-fold Brier improvement;
- feature coverage.

## Horizon qualification

A horizon is `FOUNDATION_SIGNAL_SUPPORTED` only if all hold:

1. pooled feature coverage >= 0.95;
2. every fold feature coverage >= 0.90;
3. pooled Brier improvement > 0;
4. multiplicity-adjusted bootstrap lower bound of Brier improvement > 0;
5. at least 3 of 4 folds have non-negative Brier improvement;
6. pooled log loss <= matched control log loss.

Selection rule:

- if 24h qualifies: `KEEP_24H_FOR_NEXT_PUBLIC_FLOW_FAMILY`;
- else if 4h qualifies: `FOUNDATION_SUPPORTS_4H_RESEARCH_ONLY`;
- else if 1h qualifies: `FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY`;
- else: `NO_PUBLIC_TAKER_FLOW_HORIZON_SUPPORTED`.

A 4h or 1h result does not automatically change the product target or V2 contract. It only supports a later Research Director horizon decision.

## Boundaries

- no selective LONG gate;
- no trading PnL;
- no costs/execution simulation;
- no magnitude;
- no second model class;
- no threshold tuning;
- no feature additions after results;
- no aggTrades/order-book escalation in this checkpoint;
- no sealed data;
- Champion NONE;
- real money false.
