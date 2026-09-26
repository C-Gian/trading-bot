# LIB-015 — Time Series Momentum — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-26  
Source file: `Time Series Momentum.pdf`  
Drive file id: `1uqHPWXeoYYkG_LUAW3g9wa54oOqBCZkT`  
Local corpus id: `LIB-015`

## 1. Source identity

Title shown in file:

**Time Series Momentum**

Date shown in file:

**May 1, 2012**

Category shown in file:

**Alternative Investing**

Publisher / distributor:

**AQR Capital Management**

Artifact type:

**Institutional secondary summary / informational note**

Important classification point:

The file explicitly states that:

- it is provided for information purposes;
- it is secondary information;
- it should not be the primary source for an investment/allocation decision;
- it is not research and should not be treated as research;
- it is not investment advice;
- information may be incomplete and is not guaranteed;
- historical market trends are not reliable indicators of future performance;
- no assurance is made that any investment strategy will be successful.

Therefore this local Drive artifact is **not the complete academic paper** *Time Series Momentum* and
must not be treated as though it contains the paper's full methodology, tables, statistical tests,
portfolio construction, transaction-cost analysis or appendices.

The substantive local artifact is approximately two pages.

## 2. What this source actually claims

### SOURCE CLAIM — existence of a time-series momentum effect

The note reports an anomaly called **time series momentum**.

The defining idea is:

> an instrument's own past return contains positive information about its own future return.

The source reports this effect across **58 diverse futures and forward contracts**, including:

- country equity indices;
- currencies;
- commodities;
- sovereign bonds.

The evidence is described as covering **more than 25 years of data**.

### SOURCE CLAIM — 12-month own return predicts future return

The source says that the **past 12-month excess return** of each instrument is a positive predictor
of its future return.

This is the central signal description contained in the local file.

No more detailed transformation, volatility scaling, threshold, portfolio-construction rule or
execution rule is supplied in this artifact.

### SOURCE CLAIM — persistence followed by partial reversal

The note states that the time-series momentum / trend effect:

- persists for roughly **one year**;
- then **partially reverses over longer horizons**.

This means the source does not describe an indefinitely persistent trend effect.

### SOURCE CLAIM — robustness across design choices

The note reports that the findings are robust across:

- multiple sub-samples;
- multiple look-back periods;
- multiple holding periods.

However, the local summary does **not** enumerate those exact alternatives or provide the associated
statistics.

Therefore the robustness claim can be retained only at the level explicitly stated.

### SOURCE CLAIM — positive profits across every contract studied

The source reports that **12-month time-series-momentum profits were positive for every asset
contract examined**, not merely positive on average across the entire set.

This is a strong statement in the summary, but the local file does not provide:

- the individual contract returns;
- uncertainty around each estimate;
- cost assumptions;
- turnover;
- implementation details.

It should not be converted into a stronger universal claim.

## 3. Time-series momentum versus cross-sectional momentum

This distinction is one of the most important concepts in the source.

### Cross-sectional momentum

The note describes the traditional finance-literature momentum effect as primarily **relative**.

Conceptually:

- compare securities against their peers;
- recent relative winners tend to continue outperforming relative losers over a subsequent horizon.

The source describes the usual prior-performance window as approximately **3–12 months**, followed
by examination of subsequent relative performance.

### Time-series momentum

Time-series momentum does **not** require comparison against peer securities.

It asks:

> Is this instrument's own past return positive or negative, and does that help predict its own future
> return?

This distinction matters greatly for a single-asset project such as Trading Bot.

A BTC-only system cannot directly implement conventional cross-sectional momentum without introducing
a comparison universe, but it can in principle define a time-series trend/momentum state from BTC's
own history.

That is a Research Director interpretation of the conceptual distinction, not evidence that the
12-month rule transfers to BTC.

## 4. Relationship between time-series and cross-sectional momentum

### SOURCE CLAIM

The note says that time-series and cross-sectional momentum are related but distinct.

When the authors decompose the profits of both types, the source reports that the dominant force in
both is:

> significant positive auto-covariance between next month's excess return and the lagged one-year
> return.

In simple terms, the local source attributes much of both momentum effects to a tendency for recent
return direction to contain information about subsequent return direction.

### LIMITATION

The local summary does not provide:

- the decomposition equations;
- the relative magnitude of each component;
- standard errors;
- alternative specifications;
- asset-specific decomposition.

Those details cannot be reconstructed from this artifact alone.

## 5. Evidence and methodology visible in this artifact

What can be directly established from the local file:

- 58 futures and forward contracts;
- multiple broad traditional asset classes;
- more than 25 years of data;
- own past 12-month excess return as the central predictor;
- persistence for about one year;
- partial longer-horizon reversal;
- stated robustness across sub-samples/lookbacks/holding periods;
- stated positive 12-month TSMOM profits for every contract studied;
- distinction between time-series and cross-sectional momentum;
- reported positive auto-covariance as an important common mechanism.

What **cannot** be established from this local file:

- exact asset list;
- exact start/end dates;
- exact return calculation;
- precise signal formula;
- whether signals are binary or continuous;
- volatility scaling;
- leverage;
- portfolio weighting;
- rebalancing frequency;
- financing assumptions;
- commissions;
- bid/ask spread;
- slippage;
- market impact;
- exact Sharpe ratios;
- confidence intervals;
- statistical significance per asset;
- drawdowns;
- turnover;
- implementation shortfall;
- exact robustness grid;
- exact reversal horizon;
- live-trading feasibility.

These omissions materially limit the source's direct usefulness for Trading Bot parameterization.

## 6. Concepts relevant to Trading Bot

### 6.1 Trend / momentum deserves treatment as a professional information family

This artifact provides external evidence that a simple form of **own-history trend information** has
shown broad historical regularity across traditional asset classes.

That is enough to treat trend / time-series momentum as a professionally grounded concept worthy of
representation in the future knowledge map.

It is **not** enough to declare it a validated BTC edge.

### 6.2 Single-asset compatibility

The distinction from cross-sectional momentum is particularly relevant to the Owner's BTC-focused
mission.

Because time-series momentum uses an instrument's own past returns, the concept is naturally
compatible with a one-asset system at the conceptual level.

This does not determine:

- BTC horizon;
- signal representation;
- signal weight;
- trade direction threshold;
- entry timing.

### 6.3 Trend is horizon-dependent

The source's own description contains both:

- continuation;
- later partial reversal.

Therefore "trend" should not be treated as a timeless directional truth.

The chosen look-back and forecast/holding horizon matter.

This is a crucial conceptual warning for any multi-timeframe system.

### 6.4 Trend signal and trade action are not the same thing

The file supports a predictive relation at the level of historical returns.

It does **not** specify:

- when to enter within the horizon;
- where to place a stop;
- how to size;
- how to respond to conflicting signals;
- whether a current price is too extended;
- execution conditions.

Therefore time-series momentum is best interpreted from this source as a **directional information
family**, not a complete trading strategy.

That classification is a Research Director interpretation.

## 7. Relevance to the Owner's signal-weight concept

This source does not provide a numeric basis for:

- `peso_base`;
- `peso2`;
- confidence multipliers;
- signal voting.

What it does support qualitatively is that **trend/time-series momentum is not an arbitrary retail
indicator category**. It has documented cross-market evidence in the summarized study.

For later corpus synthesis, this may affect whether trend/momentum deserves a structural role in the
professional signal architecture.

It does not tell us how large that role should be.

No numeric importance score should be derived from this two-page summary.

## 8. Relevance to multi-timeframe reasoning

The source is highly relevant conceptually but not parametrically.

It demonstrates that:

- historical direction can contain information;
- continuation has a characteristic horizon;
- reversal can appear at longer horizons.

This suggests that direction may legitimately differ across horizons.

For example, in principle:

- a shorter horizon may be in continuation;
- a longer horizon may be nearer reversal,

or vice versa.

However, the source's empirical horizon is around months/year, not minutes/hours.

Therefore it cannot support the exact Trading Bot hierarchy:

- 15m;
- 1h;
- 4h;
- daily;
- weekly,

without new evidence.

## 9. Applicability to BTCUSDT

### HYPOTHESIS CANDIDATE

The source supports a bounded hypothesis of the form:

> BTC's own past return may contain directional information about its future return at some horizons.

It does **not** support:

> BTC should use a 12-month momentum signal for a 4h forecast.

Nor does it support:

> because time-series momentum worked in traditional futures, it must work in crypto.

### Important differences requiring BTC-specific verification

The local source contains no evidence about:

- BTC;
- crypto;
- 24/7 trading;
- perpetual futures;
- funding;
- crypto liquidation cascades;
- crypto-specific market microstructure;
- high intraday volatility;
- 15m/1h/4h signal horizons;
- Binance execution costs.

Therefore transferability is unproven.

## 10. Important distinction: academic phenomenon versus practical implementation

The source describes an empirical return-predictability phenomenon.

It does not give us a complete professional execution system.

A future Trading Bot implementation would still need independent decisions about:

- signal normalization;
- horizon;
- regime;
- interaction with structure/volume/cycles/order flow;
- volatility conditioning;
- risk sizing;
- entry actionability;
- stop/exit design;
- costs and fills.

This distinction should be preserved during final synthesis.

## 11. What this source does NOT support

LIB-015 does not support any of the following:

- a specific BTC momentum parameter;
- a 12-month BTC lookback;
- a 4h BTC forecast rule;
- a momentum weight of 1–5;
- a LONG/SHORT threshold;
- an RSI/MACD/EMA implementation;
- a claim that all trend indicators are equivalent;
- a claim that momentum always persists;
- a claim that momentum survives Binance costs;
- a claim that momentum should override other signal families;
- a claim that longer-term reversal should be traded contrarian;
- any particular stop, target or holding period for Trading Bot.

## 12. Source limitations

### 12.1 Secondary summary

The most important limitation is structural:

**this local file is not the complete academic paper.**

It explicitly calls itself secondary information and says it is not research.

### 12.2 No complete methods

The local file omits the mathematical/statistical implementation needed to independently reproduce
the reported result.

### 12.3 Traditional assets only

No crypto evidence appears.

### 12.4 Horizon mismatch

The central horizon is approximately 12 months / one year, far longer than the initial intraday/
short-horizon Trading Bot mission.

### 12.5 No visible realistic execution layer

No transaction-cost/execution implementation is visible in this artifact.

### 12.6 Historical evidence is not future guarantee

The file explicitly warns that past performance and historical market trends are not guarantees of
future behavior.

## 13. Durable project knowledge retained from LIB-015

The following points are strong enough to preserve for later cross-source synthesis:

1. **Time-series momentum uses an instrument's own past return, not relative peer performance.**
2. The summarized study reports the effect across **58 diverse futures/forward contracts**.
3. The summarized evidence spans **more than 25 years**.
4. The **past 12-month excess return** is reported as a positive predictor of future return.
5. The effect is reported to persist for roughly **one year** and then partially reverse at longer
   horizons.
6. The findings are reported as robust across several sub-samples, lookbacks and holding periods.
7. The source reports positive 12-month TSMOM profits for **every contract examined**.
8. Time-series and cross-sectional momentum are related but conceptually different.
9. Positive return auto-covariance is reported as an important common driver of both.
10. Trend/momentum is therefore a professionally grounded information family worth later
    consideration.
11. None of the reported traditional-market horizons or parameters can be copied directly into a
    short-horizon BTC system.
12. The local artifact is a **secondary AQR summary explicitly marked not research**, not the full
    underlying paper.

## 14. Questions for Astra at final corpus review

1. How much architectural prior should a broad cross-asset time-series-momentum literature receive
   when the target market/horizon is BTC intraday?
2. Should trend and momentum be one family or separate roles in the future Trading Bot architecture?
3. How should signal horizons be structured when continuation at one horizon can coexist with
   reversal at a longer horizon?
4. What evidence is required before translating a monthly/annual phenomenon into 15m–4h BTC
   forecasting?
5. Should a professional trend signal contribute to:
   - directional prediction;
   - conviction;
   - regime classification;
   - actionability;
   or some combination?
6. How should trend evidence be prevented from being double-counted through correlated transforms
   such as moving averages, momentum returns and breakout measures?
7. Should the full underlying academic paper be added/read before any final momentum architecture is
   frozen?
8. How should the associated AQR datasets be used, if at all, without confusing reproduction of the
   paper with BTC-specific validation?

## 15. Final source disposition

`REVIEWED`

Reason:

The complete accessible local Drive artifact has been read.

Its:

- substantive claims;
- terminology;
- visible evidence scope;
- limitations;
- relation to the Owner's product;
- unsupported extrapolations

have been recorded.

This status applies **only** to the local two-page AQR summary file.

It does **not** imply that the complete underlying academic paper *Time Series Momentum* has been
reviewed.

No Trading Bot strategy, signal weight, parameter, System G2 design or market experiment is
authorized by this dossier.
