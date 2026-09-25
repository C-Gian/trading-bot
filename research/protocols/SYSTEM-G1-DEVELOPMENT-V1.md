# System G1 Development Protocol V1

Status: **FROZEN BEFORE SYSTEM G1 HISTORICAL OUTCOME INSPECTION**
Date: 2026-09-25
Generation: SYSTEM_G1
Authority: Constitution 4.0, ADR-0044, ADR-0046.

This protocol defines the first and only bounded historical Development batch for System G1.

It does not itself authorize execution. Implementation and synthetic/outcome-blind validation must
be reviewed first.

## 1. Scientific question

Can one bounded, interpretable BTC professional multi-signal system:

1. produce useful continuous 4h forecasts whose quality improves at higher declared conviction; and
2. produce selective LONG/SHORT paper trades with positive net economics and acceptable risk

under fixed causal timing, costs and risk?

The system contains exactly two playbooks:

- P1 directional continuation after pullback;
- P2 failed-auction re-entry.

No third playbook is authorized.

## 2. Data and evaluation interval

Use only already-cached, pre-cutoff official data identified by repository manifests.

Primary market/reference instrument:
BTCUSDT USD-M traded prices.

Context source:
BTCUSDT spot where a declared signal requires the independent spot series.

Canonical raw resolution:
1m.

No new market download is authorized for this batch.

Data may be used through:
`2024-12-31T23:59:00Z`.

### Research windows

- 2020: forecaster training / indicator warm-up only.
- 2021-2022: bounded configuration-selection window.
- 2023-2024: locked Development evaluation window.

The executor must not compute 2023-2024 G1 configuration economics before the automatic
2021-2022 selection is complete and its selected configuration identity has been written to the run
artifact.

No human intervention may alter the selection after seeing 2021-2022 results.

This remains exposed historical Development evidence, not sealed/prospective evidence.

## 3. Time architecture

- source/execution: completed 1m;
- decision/prediction issue: every completed 15m candle;
- continuous forecast target: terminal log return exactly 4h after issue;
- structure: completed 1h;
- regime: completed 4h;
- daily: completed UTC days / current UTC-session VWAP;
- cycle scales: frozen ADR-0046 hierarchy.

All signals use only observations available at decision time.

## 4. Shared technical state

All indicator implementations are deterministic and use standard recursive definitions.

### 4.1 4h regime — Wilder ADX/DI

Use 14-period Wilder ADX/+DI/-DI on completed USD-M 4h bars.

- `TREND_BULL`: ADX >=25 and +DI > -DI.
- `TREND_BEAR`: ADX >=25 and -DI > +DI.
- `RANGE`: ADX <=20.
- otherwise `TRANSITION`.

No alternate ADX period or threshold is allocated.

### 4.2 1h structure

Use EMA20 and EMA50 on completed USD-M 1h closes.

- `BULLISH`: EMA20 > EMA50 and close > EMA20.
- `BEARISH`: EMA20 < EMA50 and close < EMA20.
- otherwise `NEUTRAL`.

### 4.3 15m volatility

Use Wilder ATR14 on completed USD-M 15m bars.

ATR must be finite and positive for an actionable setup.

### 4.4 Current UTC-session VWAP

Use completed USD-M 1m observations since 00:00 UTC.

VWAP = cumulative quote volume / cumulative base volume.

If volume is zero/invalid or required minutes are unavailable under the source-quality rule, VWAP is
unavailable.

### 4.5 Completed previous-day boundaries

Previous completed UTC day's high and low from USD-M 1m/derived daily bars.

These are fixed before the current day begins.

### 4.6 Daily directional corroboration

On completed USD-M daily closes use EMA20.

- `DAILY_BULL`: close > EMA20 and EMA20 > EMA20 three completed days earlier.
- `DAILY_BEAR`: close < EMA20 and EMA20 < EMA20 three completed days earlier.
- otherwise `DAILY_NEUTRAL`.

For P1 full-system trades the daily state may support or be neutral; it may not oppose the proposed
direction.

P2 has no daily directional veto.

Weekly/monthly price context remains display/research context only in G1 and is not an additional
entry condition.

## 5. Participation/aggressive-flow corroboration

Use the completed 15m trigger candle.

### Relative volume

`RVOL = current base volume / median(base volume of previous 20 completed 15m candles)`.

Required:

`RVOL >= 1.20`.

The current trigger candle is excluded from the baseline median.

### Taker imbalance

From exchange-reported kline taker-buy base volume:

`imbalance = (2*taker_buy_base_volume - total_base_volume) / total_base_volume`.

LONG corroboration requires imbalance >0.
SHORT corroboration requires imbalance <0.

Participation support requires **both** relative-volume and imbalance conditions.

No magnitude threshold on imbalance is authorized.

Missing taker-volume fields make participation support unavailable/false; they are not imputed.

## 6. Cycle corroboration

Use ADR-0046 exactly.

LONG:

- >=1 USABLE FAST scale;
- all USABLE FAST scales RISING;
- no USABLE INTERMEDIATE scale whose most recent confirmed turn is DOWN.

SHORT symmetric.

SLOW state is displayed only.

Cycle cannot create a trade without a valid price/structure setup.

## 7. P1 — directional continuation after pullback

### 7.1 Base directional context

LONG requires:

- 4h `TREND_BULL`;
- 1h `BULLISH`.

SHORT requires the symmetric bearish states.

### 7.2 Pullback location and arming

Location reference:
the completed/currently available 1h EMA20.

A P1 pullback becomes armed when a completed 15m candle touches/crosses the 1h EMA20:

LONG:
`low <= EMA20`.

SHORT:
`high >= EMA20`.

The 4h and 1h directional contexts must remain valid.

The armed setup lasts through the next **four completed 15m candles**, including the arming candle.

If direction becomes invalid before trigger, the setup expires.

Only one P1 setup per direction may be armed at a time.

### 7.3 Trigger

While armed:

LONG trigger:
a completed 15m candle closes above both:

- the 1h EMA20 available at that candle close; and
- the immediately preceding completed 15m candle high.

SHORT is symmetric: close below EMA20 and below previous 15m low.

### 7.4 Stop and objective

The pullback window is the arming candle through trigger candle.

LONG stop:
`minimum(low of pullback window) - 0.25 * ATR14_15m`.

SHORT stop:
`maximum(high of pullback window) + 0.25 * ATR14_15m`.

Objective:
exactly `2.0R` from the reference entry price using the stop distance.

Maximum hold:
4h after actual fill.

No trailing stop, partial exit or discretionary extension.

### 7.5 Additional full-system corroboration

For S-full P1 actionability:

- daily context must not oppose direction;
- participation must support direction;
- cycle must support direction.

## 8. P2 — failed-auction re-entry

### 8.1 Base market state

4h regime must be `RANGE`.

### 8.2 Boundary

Use previous completed UTC-day high/low.

### 8.3 Excursion and re-entry trigger

Use one completed 15m candle.

LONG:

- candle low <= previous-day low - `0.25 * ATR14_15m`;
- candle close >= previous-day low.

SHORT:

- candle high >= previous-day high + `0.25 * ATR14_15m`;
- candle close <= previous-day high.

The boundary and ATR are values available at/through the trigger close.

No future confirmation candle is required.

### 8.4 Stop and value objective

LONG stop:
trigger low - `0.25 * ATR14_15m`.

SHORT stop:
trigger high + `0.25 * ATR14_15m`.

Objective:
current UTC-session VWAP available at the trigger.

The objective must be on the profitable side of the reference entry.

Minimum planned reward/risk:
`>= 1.50R`.

Otherwise NO_TRADE.

Maximum hold:
4h after actual fill.

No oscillator filter, alternate range definition or second target.

### 8.5 Additional full-system corroboration

For S-full P2 actionability:

- participation must support direction;
- cycle must support direction.

No daily directional veto.

## 9. Conflict and occupancy

Exactly one system position may be pending/open.

If P1 and P2 simultaneously propose opposite directions:
`NO_TRADE — PLAYBOOK_CONFLICT`.

If both propose the same direction:
choose the plan with the larger planned reward/risk.

Exact equality tie:
P1 wins by frozen precedence.

This does not double position size.

Risk/occupancy/data vetoes are applied after setup recognition.

## 10. Conviction

Conviction is evaluated under **S-full evidence**, independent of later ablation configuration.

### LOW

No P1/P2 base trigger is present, or market state is unavailable.

### MEDIUM

At least one P1/P2 base trigger is present, but exactly one approved full-system opportunity is not
complete because one or more optional corroborations are absent/opposed, or two playbooks conflict.

### HIGH

Exactly one playbook/direction satisfies its full S-full evidence pattern:

- base trigger;
- required higher-timeframe rule;
- participation;
- cycle.

Risk, data, occupancy or reward/cost vetoes do not lower HIGH conviction; they may still force
NO_TRADE.

No numeric post-hoc conviction score is used in G1 Development.

## 11. Continuous prediction model

Prediction is **not** an entry gate in G1.

It is a separate continuous information layer.

### 11.1 Target

At every eligible completed 15m issue T:

`r4h = log(USD-M close[T+4h] / USD-M close[T])`.

The terminal 1m/15m observation must exist exactly; otherwise realization is unscorable.

### 11.2 Prior risk scale

Use the sample standard deviation of the previous 96 completed 15m log returns, excluding any future
return.

`sigma4h = sigma15m * sqrt(16)`.

If the risk scale is unavailable/non-positive, prediction is UNAVAILABLE.

Standardized target:

`z4h = r4h / sigma4h_at_issue`.

### 11.3 Conditioning cells

Exactly:

`directional_bias {BEARISH, NEUTRAL, BULLISH} × conviction {LOW, MEDIUM, HIGH}`.

Directional bias:

- BULLISH when 4h and 1h states are bullish;
- BEARISH when both are bearish;
- otherwise NEUTRAL.

Maximum nine cells.

### 11.4 Expanding training

For evaluation year Y in 2021..2024:

train only on matured predictions before 00:00 UTC Jan 1 Y, with a 4h purge at the boundary.

No future-year observation enters the estimator.

### 11.5 Fixed shrinkage

For each cell, let n be training observations.

Frozen shrinkage weight:

`w = n / (n + 256)`.

The cell distribution is the weighted mixture:

`w * empirical_cell + (1-w) * empirical_unconditional_training_distribution`.

Use the same mixture for:

- probability return >0;
- mean standardized return;
- median;
- q10/q90.

Translate standardized moments/quantiles back to raw return using the issue-time risk scale.

No alternative shrinkage constant or model family is authorized.

### 11.6 Probability labeling

The probability output is:

`EMPIRICAL_SHRUNK_CONDITIONAL_PROBABILITY_NOT_CALIBRATED`.

The UI/API must not call it calibrated probability.

No Platt/isotonic/neural calibration is added in G1.

## 12. Trade configurations

Exactly seven configurations may be computed in the 2021-2022 selection phase:

1. `S0` — base P1/P2 price/structure/risk triggers; no participation, cycle or daily P1 veto.
2. `S_FULL` — complete rules.
3. `S_MINUS_CYCLE` — S_FULL except cycle corroboration removed.
4. `S_MINUS_PARTICIPATION` — S_FULL except participation removed.
5. `S_MINUS_DAILY_HTF` — S_FULL except P1 daily veto removed.
6. `S_P1_ONLY` — S_FULL P1 only.
7. `S_P2_ONLY` — S_FULL P2 only.

All share identical execution/risk/cost logic.

No other configuration may be calculated.

## 13. Primary execution/risk

Reference paper instrument:
BTCUSDT USD-M traded prices.

- initial virtual equity: 10,000 quote units;
- planned risk per position: 0.25% current equity;
- max gross notional: 1x current equity;
- one pending/open position;
- no pyramiding/hedging/martingale;
- primary operational delay: 1m;
- next eligible exact 1m open fill;
- nominal fees/friction: frozen 24bp round-trip convention;
- funding: signed settlement accounting;
- UTC-day new-entry stop after 1% equity loss;
- run new-entry stop after 5% peak-to-trough drawdown;
- maximum hold 4h.

Missing exact fill minute rejects entry; missing minute while open makes the trade unscorable and
forces conservative exit under the frozen ledger rules.

## 14. Configuration selection — 2021-2022 only

The executor runs all seven configurations on 2021-2022 only.

A configuration is selection-eligible only if:

- >=40 scorable closed trades total;
- >=15 scorable trades in 2021 and >=15 in 2022;
- scorable-trade coverage >=95%;
- net calendar P&L >0 in 2021;
- net calendar P&L >0 in 2022;
- run drawdown entry stop never triggers.

Among eligible configurations select the one with greatest cumulative net equity return over
2021-2022.

Exact numerical tie:
lexicographically smallest configuration ID.

Write the selected ID and complete 2021-2022 table before evaluating 2023-2024.

If none is eligible:

`SYSTEM_G1_DEVELOPMENT_REJECTED_SELECTION_STAGE`

and do not compute 2023-2024 configuration economics.

No human choice is permitted.

## 15. Locked Development evaluation — 2023-2024

Evaluate **only the automatically selected configuration** on 2023-2024.

The forecaster continues to use annual expanding training as defined above.

### 15.1 Support / integrity gates

All required:

- exact protocol/config/source identities PASS;
- prediction issue coverage >=95% eligible 15m decisions;
- scorable closed-trade coverage >=95%;
- >=60 scorable trades total;
- >=20 scorable trades in each of 2023 and 2024;
- >=10 LONG and >=10 SHORT scorable trades total;
- no causal/data/provenance violation;
- no run drawdown entry stop trigger.

Failure:
`SYSTEM_G1_INCONCLUSIVE_OR_BLOCKED_NO_PROMOTION`.

### 15.2 Trade economic gates

All required:

- cumulative net equity return >0 in 2023;
- cumulative net equity return >0 in 2024;
- pooled mean net R/trade >= +0.10R;
- cumulative 2023-2024 net equity return >= +5.0%;
- profit factor >=1.15;
- LONG cumulative net P&L >=0;
- SHORT cumulative net P&L >=0;
- removing the three largest winning trades leaves cumulative net P&L >0;
- maximum peak-to-trough drawdown <5.0%.

### 15.3 Robustness gates

All required:

- 48bp round-trip fee/friction stress + funding: cumulative net P&L >0;
- +5m additional operational-delay stress under primary costs: cumulative net P&L >0.

Do not run a combined stress.

### 15.4 Continuous-prediction gates

Evaluate all matured 15m forecasts and report LOW/MEDIUM/HIGH separately.

Baselines are fit on the same training information:

- direction probability baseline = unconditional training up-rate;
- magnitude baseline = zero terminal return.

Promotion requires on 2023-2024 HIGH-conviction forecasts:

- >=100 valid matured HIGH forecasts;
- Brier score strictly better than unconditional up-rate baseline;
- mean absolute terminal-return error strictly better than zero-return baseline.

Also report all-forecast and LOW/MEDIUM metrics; they are not hidden and do not independently reject
the selective trading system.

No raw hit-rate gate is used.

### 15.5 Concentration/stability diagnostics

Report, but do not add undeclared rescue gates:

- yearly/monthly P&L;
- LONG/SHORT;
- P1/P2 where applicable;
- top 1/3/5 trade contribution;
- loss tails / worst trades;
- occupancy;
- turnover;
- cost/funding share;
- conviction-stratified realized movement;
- forecast calibration/reliability plots/tables;
- hot-window dates.

## 16. Development disposition

Order:

1. `INVALID_EXECUTION`
2. `SYSTEM_G1_INCONCLUSIVE_OR_BLOCKED_NO_PROMOTION`
3. `SYSTEM_G1_DEVELOPMENT_REJECTED_SELECTION_STAGE`
4. `SYSTEM_G1_DEVELOPMENT_REJECTED_EVALUATION_STAGE`
5. `SYSTEM_G1_PROMOTION_ELIGIBLE_PENDING_ASTRA`

If selection succeeds but any 2023-2024 economic/robustness/prediction gate fails:

`SYSTEM_G1_DEVELOPMENT_REJECTED_EVALUATION_STAGE`.

Only if every declared 2023-2024 gate passes:

`SYSTEM_G1_PROMOTION_ELIGIBLE_PENDING_ASTRA`.

No prospective system starts automatically.

Any terminal result returns to the Research Director; promotion or project reallocation returns to
Astra as required by Constitution 4.0.

## 17. Search/exposure rules

Before historical execution:

- code/config/protocol hashes are frozen;
- all seven 2021-2022 configs are counted as inspected;
- only selected config may touch 2023-2024 G1 economics;
- no alternative threshold/timeframe/cycle method/forecast model/stop/target is allowed;
- no post-result LONG-only/SHORT-only rescue;
- no third playbook;
- no Candidate #1 reopening.

Every inspected result enters research memory.

## 18. Event/news report

Hot windows are selected using only predeclared market-path criteria after the selected 2023-2024
replay completes.

External news/event research remains a separate explanatory post-analysis and is not part of this
historical execution authorization.

No web/news retrieval is required to adjudicate the G1 market result itself.

## 19. Current authorization

This protocol authorizes **implementation only** until a separate Research Director decision reviews
the implementation and explicitly authorizes the single historical G1 batch.

No real money. No live orders. No credentials. No protected/post-cutoff data.
