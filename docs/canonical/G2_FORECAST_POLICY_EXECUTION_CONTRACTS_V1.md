# G2 Forecast, Policy and Execution Contracts V1

Status: FROZEN AT G2-00 GATE A — NO ECONOMIC MARKET RUN AUTHORIZED BY THIS FILE  
Date: 2026-09-27  
Authority: ADR-0052; Astra Development System Directive V2; G2 Professional Knowledge Model V1

## 1. Contract hierarchy

G2 keeps four objects distinct:

1. market observation/state;
2. 4h market forecast;
3. entry/actionability policy;
4. risk and execution.

A correct forecast does not imply a trade. A profitable trade does not prove forecast calibration.
Good P&L does not excuse an execution/risk violation.

## 2. Time semantics

All timestamps are UTC.

Canonical raw clock:
- 1 minute.

Official decision grid:
- every completed 15-minute candle;
- decision instant T is the right boundary of [T-15m, T);
- only data whose availability is at or before T may enter the state.

Primary market target:
- r4h(T) = log(P(T+4h) / P(T));
- P(T) is the last traded USD-M BTCUSDT perpetual price represented by the completed bar ending at T;
- the target matures only when the price at T+4h is available.

Context clocks:
- completed 1h: local structure/timing;
- completed 4h: directional context;
- completed Daily UTC: display/context only in V0;
- completed Weekly UTC: display/background only in V0.

No incomplete higher-timeframe candle may be read.

If a decision point cannot satisfy data/warm-up requirements, a record is still emitted with
FORECAST_UNAVAILABLE and a reason code.

## 3. Causal EWM operator

For any completed-bar series x and half-life H measured in bars:

lambda(H) = 2^(-1/H)

EWM_t = lambda(H) * EWM_(t-1) + (1-lambda(H)) * x_t

The first finite observation initializes the recursion. A dependent feature is not eligible until at
least four times the longest half-life used by that feature has been observed without a critical
gap.

A gap that violates the source continuity contract invalidates the dependent recursive state and
requires re-warm. No value is backfilled from the future.

## 4. G2-V0 raw predictive observables

### 4.1 LOCAL_STRUCTURE

Use completed 1h log close.

LOCAL_FAST = EWM half-life 4 completed 1h bars.
LOCAL_SLOW = EWM half-life 16 completed 1h bars.

LOCAL_STRUCTURE_RAW = LOCAL_FAST - LOCAL_SLOW.

This is one declared trend representation, not an EMA tournament.

### 4.2 CONTEXT_STRUCTURE

Use completed 4h log close.

CONTEXT_FAST = EWM half-life 6 completed 4h bars.
CONTEXT_SLOW = EWM half-life 24 completed 4h bars.

CONTEXT_STRUCTURE_RAW = CONTEXT_FAST - CONTEXT_SLOW.

### 4.3 PRICE_EXTENSION

At decision T:

PRICE_EXTENSION_RAW = log(P(T)) - LOCAL_FAST(T).

It may make an otherwise positive directional state unattractive to enter without changing the sign
of the slower context.

### 4.4 RELATIVE_PARTICIPATION

For each completed 15m candle let Q be quote-asset volume.

LQ_t = log(1 + Q_t).

PARTICIPATION_BASELINE_PRE_T is the 15m EWM of LQ with half-life 96 bars, evaluated through the
previous completed 15m candle and therefore excluding the current decision candle.

RELATIVE_PARTICIPATION_RAW = LQ_current - PARTICIPATION_BASELINE_PRE_T.

Only this normalization of volume enters V0.

### 4.5 TAKER_IMBALANCE

For the completed decision 15m candle:

B = taker-buy base-asset volume.
V = total base-asset volume.

If V <= 0 the field is unavailable.

TAKER_IMBALANCE_RAW = (2*B - V) / V.

The value lies in [-1, 1]. Positive means more taker-buy than taker-sell base volume under the venue
field definition; it does not identify trader motive or future direction.

### 4.6 VOLATILITY_STATE and forecast scale

Let r15 be completed 15m log returns.

Fast variance:
- EWM of r15^2, half-life 16 bars (4h).

Slow variance:
- EWM of r15^2, half-life 96 bars (24h).

Both include the just-completed decision candle and no future return.

VOLATILITY_STATE_RAW = 0.5 * log(max(V_fast, eps) / max(V_slow, eps)).

Forecast scale:
SIGMA_4H(T) = sqrt(16 * V_slow(T)).

eps = 1e-12.

If SIGMA_4H is non-finite or non-positive, forecast is unavailable.

### 4.7 PRICE_RESPONSE for the second interaction

PRICE_RESPONSE_RAW = r15_current / sqrt(max(V_slow(T), eps)).

PRICE_RESPONSE is not a standalone main-effect column in V0.

### 4.8 Interactions

I1_RAW = LOCAL_STRUCTURE_RAW * RELATIVE_PARTICIPATION_RAW.
I2_RAW = TAKER_IMBALANCE_RAW * PRICE_RESPONSE_RAW.

The forecast dictionary is exactly the six main observables plus I1 and I2.

## 5. Training-only robust scaling

At every scheduled fit, each of the eight model columns is transformed using training data only.

For each column j:
- center_j = median(x_j);
- mad_j = median(abs(x_j - center_j));
- scale_j = 1.4826 * mad_j.

If scale_j <= 1e-8 or is non-finite, the column is declared CONSTANT_TRAINING_FEATURE for that fit:
its standardized value and coefficient are fixed to zero until the next scheduled refit. It is not
replaced by another feature.

Otherwise:
x_std = clip((x - center_j) / scale_j, -8, +8).

Training centers/scales are stored in the model manifest and reused unchanged for every prediction
until the next scheduled fit.

## 6. Forecast target and estimator

Normalized training target:

z4h(T) = r4h(T) / SIGMA_4H(T).

Only rows for which T+4h is at or before the fit boundary are mature.

Model class:
- linear ridge regression;
- intercept unpenalized;
- no sign constraints;
- no automated feature selection.

Objective:

mean((z - beta0 - X beta)^2)
+ 0.25 * sum(beta_main^2)
+ 1.00 * sum(beta_interaction^2).

The first six columns use penalty 0.25.
The two interaction columns use penalty 1.00.

These constants are engineering shrinkage conventions, not estimated alpha parameters. No
cross-validation or P&L search chooses them.

## 7. Fit calendar and training window

Scheduled refit:
- 00:00 UTC on the first calendar day of each month.

Training window:
- only past data;
- maximum trailing span 730 days;
- minimum calendar span 180 days;
- at least 10,000 valid mature rows;
- no target crossing the fit cut-off.

If minimum support is not met, the conditional model is unavailable.

A scheduled refit is part of the frozen algorithm and is not a new research revision. Changing fit
frequency, window or penalty after seeing outcomes is a scientific revision.

## 8. Predictive distribution

The point model produces mu_z.

The preferred residual distribution is a PREQUENTIAL residual archive:
- each residual comes from a forecast genuinely issued by the then-active prior monthly fit;
- the associated target must already have matured;
- maximum trailing residual age: 730 days;
- residuals from a changed scientific system version never silently mix with another version.

Use the prequential residual CDF when it contains:
- at least 2,000 mature residual records; and
- at least 30 calendar days from first to last residual.

Status:
PREQUENTIAL_CDF_UNCALIBRATED.

Before that threshold, use a causal fallback:
- take the mature z4h targets in the current training window;
- center them by their training mean;
- treat that centered empirical distribution as residual-like baseline noise.

Status:
TRAINING_TARGET_BASELINE_UNVALIDATED.

This fallback permits an honest distributional record before sufficient prequential history exists.
It is not called calibrated.

For every residual atom e:
forecast atom in z-space = mu_z + e.
Return-space atom = (mu_z + e) * SIGMA_4H(T).

Outputs:
- mean return;
- median return;
- q10;
- q50;
- q90;
- p_positive = fraction of atoms with return > 0;
- SIGMA_4H;
- evidence/calibration status.

Ties at exactly zero are neither positive nor negative for p_positive.

## 9. Strength, probability, uncertainty and conviction

These are distinct fields.

Probability:
- p_positive is the probability-like empirical distribution estimate for r4h > 0;
- it is always accompanied by calibration_status.

Aleatory uncertainty:
- q90 - q10 and the full empirical distribution.

Epistemic/evidence state:
- model support;
- residual-source status;
- missingness;
- drift diagnostics;
- model version.

View strength:
VIEW_STRENGTH_Z = abs(median_return) / SIGMA_4H.

Display-only fixed labels:
- WEAK: < 0.25;
- MODERATE: >= 0.25 and < 0.75;
- STRONG: >= 0.75.

These labels are not action thresholds and not empirical success probabilities.

Conviction:
- the tuple of direction, VIEW_STRENGTH_Z and evidence status;
- no single hidden scalar is allowed.

The UI must never display a percentage derived from an arbitrary score as calibrated confidence.

## 10. Forecast direction

Display direction:
- UP if median_return > 0;
- DOWN if median_return < 0;
- NEUTRAL if median_return == 0 within numerical tolerance 1e-12.

A directional display does not cause a trade.

## 11. ATR stop-scale definition

Use completed 1h bars only.

True Range for 1h bar k:
TR_k = max(
  high_k - low_k,
  abs(high_k - close_(k-1)),
  abs(low_k - close_(k-1))
).

ATR14 uses Wilder recursion:
- seed = arithmetic mean of the first 14 valid TR values;
- ATR_k = (13*ATR_(k-1) + TR_k) / 14.

A gap/incomplete required 1h bar invalidates ATR until the source continuity contract is restored
and the indicator re-warms.

## 12. Standardized shadow trade geometry

Every eligible decision T eventually receives, for research labeling only, one LONG shadow and one
SHORT shadow under identical geometry.

These are counterfactual labels, not simultaneous portfolio positions.

Base latency:
- 1 minute.

Raw market entry:
- open price of the exact 1m bar beginning T+1m;
- if that bar is missing/incomplete, the shadow label is unavailable rather than opportunistically
  filled later;
- the intent expires before T+15m.

Stop distance:
D = 2 * ATR14_1H(T).

LONG stop = raw_entry - D.
SHORT stop = raw_entry + D.

No take-profit.
No trailing stop.

Expiry:
- T+4h;
- if no stop is hit, exit on the open of the exact 1m bar beginning T+4h;
- missing required exit data makes the shadow label unavailable.

Stop fill:
- LONG: if a later 1m bar opens at or below stop, raw exit is that open; otherwise if low touches
  stop, raw exit is stop.
- SHORT: if a later 1m bar opens at or above stop, raw exit is that open; otherwise if high touches
  stop, raw exit is stop.
- the entry 1m bar itself is eligible to hit the stop after its open.
- because there is no take-profit, same-bar high/low ordering cannot create a favorable ambiguity.
- any remaining ambiguity is resolved adversely and counted.

## 13. Historical friction convention

The current repository does not contain a point-in-time historical bid/ask feed or a user-specific
fee schedule for the full 2020-2024 sandbox.

Therefore historical G2 development does not claim exact Binance execution cost.

Base all-in adverse execution haircut:
- 0.0012 = 12 basis points per executed side.

This is an explicitly labeled research convention inherited from the prior 24bp round-trip G1
friction envelope. It aggregates fee + spread + slippage for the bar-based historical simulator and
is not represented as a current Binance fee.

Application:
- LONG buy accounting price = raw price * (1 + f);
- LONG sell accounting price = raw price * (1 - f);
- SHORT sell accounting price = raw price * (1 - f);
- SHORT buy-to-cover accounting price = raw price * (1 + f).

Predeclared stress:
- 1.5x: f = 0.0018 per side;
- 2.0x: f = 0.0024 per side;
- latency stress: base latency + 5 additional minutes;
- gap/outage stress is reported separately.

The base/scenario definitions cannot be reduced after seeing performance to rescue a candidate.

Future paper/live must record actual quote timestamps and the actual applicable fee schedule when
available; the historical aggregate convention then remains only a comparison scenario.

## 14. Funding cost

Settled funding is an execution/accounting cost in V0, not a predictor.

Existing historical funding records contain funding_time and funding_rate but not a guaranteed
historical record of the pre-settlement predicted funding state.

Therefore:
- funding information is never backfilled into earlier decisions;
- a settled rate becomes usable for P&L only at its settlement timestamp;
- no funding feature enters the forecast or policy.

For a position open across a settlement:
funding_pnl = - side_sign * funding_rate * abs(quantity) * price_proxy_at_funding.

side_sign:
- LONG = +1;
- SHORT = -1.

Historical price proxy:
- the USD-M 1m last-price close at the funding timestamp, because historical mark-price observations
  are not part of the current pinned development artifact.

The use of last price as mark proxy is explicitly reported as a historical accounting approximation.
It may be replaced by genuine point-in-time mark data in a future separately versioned data
contract, not silently.

## 15. Shadow payoff label

For each side:

gross_price_pnl_per_unit =
  side_sign * (raw_exit - raw_entry).

Accounting P&L includes the base historical execution haircut and all funding settlements while the
position is open.

Initial risk distance per unit = D.

NET_R = net_pnl_per_unit / D.

The label is unavailable if:
- entry/expiry bar unavailable;
- ATR unavailable;
- critical source validity fails;
- D <= 0;
- required funding record is structurally inconsistent.

NET_R is the target of the actionability readout. It is not the 4h market-return forecast target.

## 16. Entry-utility readouts

Two separate transparent ridge models are fit:
- LONG_UTILITY_HEAD;
- SHORT_UTILITY_HEAD.

Targets:
- corresponding matured LONG or SHORT NET_R shadow label.

Predictor dictionary:
- exactly the same eight standardized columns as the forecast readout;
- no hidden extra features;
- same fixed penalties 0.25 main / 1.00 interactions;
- same monthly fit calendar;
- same 730-day maximum / 180-day minimum training span;
- same mature-label rule.

Each head maintains its own prequential residual archive under the same 2,000-record and 30-day
minimum before prudential action can be evaluated.

Until both relevant residual requirements are met:
NO_TRADE / INSUFFICIENT_POLICY_EVIDENCE.

## 17. Prudential action margin

For side s:

predicted_utility_s = ridge mean NET_R.
q10_residual_s = empirical 10th percentile of that side's mature prequential utility residuals.

PRUDENTIAL_MARGIN_s = predicted_utility_s + q10_residual_s.

This is a conservative empirical score, not a formal 90% confidence bound because residuals are
serially dependent and overlapping.

Decision before risk/execution vetoes:
- eligible LONG iff PRUDENTIAL_MARGIN_LONG > 0;
- eligible SHORT iff PRUDENTIAL_MARGIN_SHORT > 0;
- if neither: NO_TRADE / UTILITY_MARGIN_NOT_POSITIVE;
- if exactly one: select it;
- if both: choose the larger margin;
- if absolute difference <= 1e-6: NO_TRADE / UTILITY_MARGIN_TIE.

A selected side opposite to the terminal 4h median direction is allowed only with explicit reason
PATH_UTILITY_OVERRIDES_TERMINAL_VIEW in the immutable record. It is not a hidden override.

## 18. Portfolio/risk governor

Virtual initial equity for normalized research accounting:
- 10,000 USDT.

Per-trade planned risk budget:
- 0.25% of current simulated equity to the raw protective-stop distance.

Maximum gross notional:
- 1.0x current equity.

Position quantity before venue rounding:
min(
  risk_budget / D,
  current_equity / raw_entry
).

The run-time contract applies the pinned exchangeInfo quantity/price filters. If the rounded
quantity cannot satisfy the pinned minimum, action becomes NO_TRADE / CONTRACT_FILTER_NOT_MET.

Only one open position.

No pyramiding.
No flip on the same decision candle.
No re-entry on the same decision candle.

While a position is open:
- forecasts continue;
- entry action = NO_TRADE / POSITION_ALREADY_OPEN;
- management state is HOLD unless stop/expiry closes it.

Path drawdown stop:
- 5% from peak simulated equity.

Once triggered:
- no new economic positions for the remainder of that run;
- forecasts continue;
- shadow labels/diagnostics after the stop remain separate and cannot be stitched back into the
  economic equity curve;
- the threshold is not reset or widened after wins/losses.

A stop order is not treated as a guarantee against gap/slippage.

## 19. Cycle integration contract

G2-V0:
- cycle values are stored and displayed;
- zero cycle columns in forecast/utility readouts;
- no cycle veto.

Only the reserved cycle development revision may admit cycle state.

Prerequisites:
- G2 cycle checkpoint state must be AVAILABLE_FOR_RESERVED_REVISION;
- at most two cycle-derived terms;
- total readout columns remain <= 8, so cycle terms must replace existing terms rather than enlarge
  the model beyond the cap;
- no six-scale voting;
- one conceptual change card and one revision budget slot.

## 20. Daily/Weekly context

Completed Daily and Weekly bars are persisted for inspection.

V0 display fields:
- prior completed-bar return;
- prior completed-bar high-low range;
- timestamp and completeness.

They do not enter forecast or utility regression and do not veto an action.

## 21. Decision reason codes

Minimum canonical reason codes:

Forecast/data:
- FORECAST_AVAILABLE;
- FORECAST_UNAVAILABLE_WARMUP;
- FORECAST_UNAVAILABLE_MISSING_DATA;
- FORECAST_UNAVAILABLE_INVALID_SIGMA;
- FORECAST_UNAVAILABLE_NO_MODEL;
- TRAINING_TARGET_BASELINE_UNVALIDATED;
- PREQUENTIAL_CDF_UNCALIBRATED.

Policy:
- LONG_SELECTED;
- SHORT_SELECTED;
- UTILITY_MARGIN_NOT_POSITIVE;
- UTILITY_MARGIN_TIE;
- INSUFFICIENT_POLICY_EVIDENCE;
- PATH_UTILITY_OVERRIDES_TERMINAL_VIEW.

Risk/execution:
- POSITION_ALREADY_OPEN;
- PATH_DRAWDOWN_STOP_ACTIVE;
- CONTRACT_FILTER_NOT_MET;
- EXECUTION_ENTRY_DATA_MISSING;
- EXECUTION_EXIT_DATA_MISSING;
- FUNDING_DATA_INVALID;
- SOURCE_STALE_OR_INVALID.

Cycle:
- CYCLE_SHADOW_ONLY;
- CYCLE_UNRELIABLE;
- CYCLE_UNAVAILABLE.

Records may contain multiple reason codes but never an unstructured reason that silently changes the
decision semantics.

## 22. Immutable record contract

Each prediction stores:
- prediction_id;
- system_version;
- model-fit hash;
- source-manifest hashes;
- decision timestamp;
- max source timestamp read;
- training start/end;
- latest matured label timestamp admitted;
- eight raw/scaled model terms;
- context/display state;
- forecast distribution outputs;
- probability/calibration status;
- view strength;
- evidence state;
- model contributions;
- linked decision_id;
- maturity status.

Outcomes append as later events; the original prediction is immutable.

Each decision stores:
- decision_id;
- prediction_id;
- selected action;
- utility-head outputs and prudential margins;
- veto/reason codes;
- position state;
- risk state;
- intended entry/expiry.

Each trade lifecycle stores:
- intended entry;
- raw simulated fill;
- accounting fill/friction;
- stop;
- expiry;
- quantity;
- planned risk;
- funding events;
- raw/accounting exit;
- realized NET_R;
- implementation-shortfall fields where observable;
- violation flags.

## 23. Baseline references

The following are frozen references, not development candidates:

NULL_FORECAST:
- location zero;
- causal unconditional distribution/scale estimated only from past mature data.

TREND_ONLY_FORECAST:
- same fit calendar, scaling, target and ridge procedure;
- model dictionary limited to LOCAL_STRUCTURE, CONTEXT_STRUCTURE and PRICE_EXTENSION;
- no independent hyperparameter search.

TREND_REFERENCE_POLICY:
- use TREND_ONLY_FORECAST distribution;
- LONG only when q10 > 0;
- SHORT only when q90 < 0;
- otherwise NO_TRADE;
- use the exact same entry, stop, expiry, friction, funding and risk contract as G2.

CASH_REFERENCE:
- zero exposure.

References cannot be tuned to make G2 look good or bad.

## 24. Evaluation scorecards

Forecast:
- CRPS when implemented consistently with empirical distribution;
- pinball loss at q10/q50/q90;
- Brier score for r4h > 0;
- interval coverage;
- MAE of median/mean return;
- coverage and performance by predeclared strength/evidence states.

Policy:
- net portfolio return;
- mean NET_R;
- drawdown/time under water;
- turnover/occupancy;
- cost share;
- LONG/SHORT mix;
- NO_TRADE reasons and counterfactual standardized shadow payoff.

Execution:
- decision-to-fill delay;
- raw versus accounting fill;
- friction/funding;
- future-paper bid/ask shortfall when available;
- reject/cancel/data-gap counts.

Uncertainty and comparisons use temporal blocks; overlapping 15m/4h labels are never treated as
independent rows.

## 25. Scientific revision boundary

Engineering bug:
- deterministic violation of this frozen contract;
- fix immediately;
- invalidate affected runs;
- preserve original and corrected lineage.

Scientific revision:
any change that can alter economic semantics, including:
- feature formula;
- feature set;
- model class/penalty;
- fit schedule/window;
- target/horizon;
- residual-distribution rule;
- utility rule;
- action margin;
- stop/expiry;
- cost/latency assumption other than factual source correction;
- risk limit;
- cycle activation.

Scientific revisions consume G2 development budget unless Astra explicitly reclassifies a
project-level change.

Primary 4h horizon, BTCUSDT USD-M instrument, six-family catalogue and model-class family are outside
ordinary G2 revision scope and require Astra for material change.

## 26. Real-money boundary

Nothing in this contract authorizes:
- credentials;
- leverage;
- real orders;
- real capital.

The contract is for research and paper simulation only.
