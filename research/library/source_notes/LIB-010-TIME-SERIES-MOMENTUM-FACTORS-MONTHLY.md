# LIB-010 — Time Series Momentum Factors Monthly — Dataset Dossier

Status: **REVIEWED — COMPLETE WORKBOOK INSPECTION**  
Study date: 2026-09-26  
Source file: `Time Series Momentum Factors Monthly.xlsx`  
Drive file id: `1n6m6gjimKjiep_1IDSrrqCh5IIGDLcT-`  
Local corpus id: `LIB-010`  
Drive modified timestamp: `2026-09-26T09:00:44.450Z`  
Raw file size: 139,830 bytes  
SHA-256: `33470930e2269c0d97be4732ec2d9c27ddbc69ac8133b059a263e27400263eeb`

## 1. Source identity

The workbook identifies itself as:

**AQR Capital Management, LLC — Time Series Momentum: Factors, Monthly**

It states that it contains the **excess returns of long/short Time Series Momentum (TSMOM)
factors**.

The workbook describes the portfolios as an:

**updated and extended version**

of the factors used in:

Moskowitz, Tobias J., Yao Hua Ooi and Lasse H. Pedersen (2012),  
**“Time Series Momentum,” Journal of Financial Economics, 104(2), 228–250.**

Important source qualification:

The workbook explicitly states that although portfolio construction is based on Moskowitz, Ooi and
Pedersen (2012), **there can be differences in data sources and methodology**.

Therefore this dataset must not be treated as a byte-for-byte or methodologically identical
continuation of the original-paper dataset.

## 2. Workbook structure

The workbook contains four worksheets:

1. `TSMOM Factors`
2. `Definitions`
3. `Data Sources`
4. `Disclosures`

The workbook contains **no spreadsheet formula cells**. The return series are stored as values.

Important implementation detail:

Substantive content in `Definitions`, `Data Sources` and `Disclosures` is partly stored as
embedded graphical/text objects rather than ordinary worksheet cells.

Those objects were inspected separately; they are included in this dossier and were not ignored by
tabular parsing.

## 3. TSMOM Factors sheet

The workbook states that it reports monthly excess returns for:

- `TSMOM` — all assets;
- `TSMOM^CM` — commodities;
- `TSMOM^EQ` — global equity indices;
- `TSMOM^FI` — fixed income;
- `TSMOM^FX` — currencies.

The workbook explicitly defines the factor shown here as:

**a 12-month time-series-momentum strategy with a 1-month holding period.**

It also states:

- data are updated and maintained by AQR;
- data are updated as they become available;
- **AQR reconstructs the full history each time the returns are updated**;
- not all available data may be displayed depending on the user's selected download;
- the full selection is available through AQR.

This reconstruction statement is scientifically important and is treated separately below.

## 4. Dataset coverage audit

### Observation range

First observation:

**1985-01-31**

Last observation:

**2026-05-29**

Total observations:

**497 monthly observations**

### Continuity

The observations:

- are strictly chronological;
- contain no duplicate dates;
- contain no missing calendar month between January 1985 and May 2026.

Dates frequently correspond to the last trading/business day rather than literal calendar month-end.

### Missing values

Across the 497 displayed observations:

| Series | Missing values |
|---|---:|
| TSMOM | 0 |
| TSMOM^CM | 0 |
| TSMOM^EQ | 0 |
| TSMOM^FI | 0 |
| TSMOM^FX | 0 |

The downloaded data panel is therefore complete for the displayed period.

## 5. Definitions — return construction

The `Definitions` sheet describes the construction process.

### SOURCE CLAIM — reconstruct daily return series

The methodology starts by constructing a return series for each of the **58 underlying instruments**.

For futures:

- each day the return of the most liquid futures contract is used;
- this is typically the nearest or next-nearest delivery contract;
- daily excess returns are compounded into a total-return index;
- horizon returns can then be computed from that index.

### PROJECT INTERPRETATION

The factor is therefore based on a reconstructed investable-instrument return stream rather than on
a single continuously held contract ticker.

The exact rolling mechanics and possible roll costs are not fully specified in the workbook.

## 6. Definitions — volatility scaling

The workbook explains that volatility varies materially across asset classes, so returns are scaled
by their volatilities to make cross-asset comparisons meaningful.

### SOURCE CLAIM — ex-ante volatility model

Each instrument receives an ex-ante volatility estimate based on:

- exponentially weighted;
- lagged;
- squared daily returns.

The workbook describes this as a simple univariate GARCH-style model.

The same volatility model is used across assets and through time.

The methodology emphasizes two reasons for this choice:

- simplicity;
- avoidance of look-ahead bias.

The workbook states that the volatility estimate available at time `t-1` is applied to time-`t`
returns so that future information does not contaminate the result.

### SOURCE CLAIM — annualization

The variance estimate is annualized using approximately the number of trading days in a year.

The exact mathematical formula is supplied graphically in the workbook.

### RESEARCH DIRECTOR INTERPRETATION

This source contains a concrete professional precedent for:

- normalizing signals/positions across instruments by ex-ante risk;
- using only lagged information in risk estimates;
- explicitly preventing look-ahead in volatility scaling.

It does not prove that this exact volatility estimator is appropriate for short-horizon BTC.

## 7. Definitions — 12-month TSMOM rule

The workbook describes the TSMOM strategy in explicit operational terms.

### SOURCE CLAIM

The strategy:

- uses a **12-month time-series momentum signal**;
- has a **1-month holding period**;
- evaluates each instrument/asset separately;
- then pools the instruments into a diversified TSMOM portfolio.

The direction of each position follows the sign of the instrument's trailing 12-month return.

### SOURCE CLAIM — volatility-scaled position size

Each long or short position is scaled so that the individual position has an ex-ante annualized
volatility target of approximately **40%** before aggregation.

The workbook explains that this 40% choice is mainly a normalization convention designed to make the
resulting diversified factor's risk comparable with common factor portfolios.

The source says that after equal-weight aggregation across securities, the diversified TSMOM factor
has annualized volatility roughly comparable to common factor portfolios in the literature.

### SOURCE CLAIM — aggregation

The workbook provides formulas for:

- the TSMOM return of an individual instrument;
- the overall TSMOM aggregate;
- the four asset-class aggregates.

The aggregate is formed across the securities available at the relevant time rather than requiring a
fixed universe at every date.

### LIMITATION

This workbook does not provide a modern execution simulator.

The 40% scaling convention is **not** a risk recommendation for Trading Bot.

## 8. Data Sources — 58-instrument universe

The source's data-source sheet explains the broad universe behind the construction.

The counts sum to **58 underlying instruments**:

- 9 country equity-index futures;
- 13 country bond-index futures;
- 12 currency/cross-currency series;
- 24 commodity futures.

## 9. Country equity indices

### SOURCE CLAIM

The equity universe consists of futures from nine developed equity markets, including:

- Australia — SPI 200;
- France — CAC 40;
- Germany — DAX;
- Italy — FTSE/MIB;
- Japan — TOPIX;
- Netherlands — AEX;
- Spain — IBEX 35;
- United Kingdom — FTSE 100;
- United States — S&P 500.

Futures prices are obtained from:

- Bloomberg;
- Datastream.

Prior to futures availability, MSCI country-level index returns are used.

### RESEARCH DIRECTOR INTERPRETATION

The historical factor is partly **spliced across data representations through time**.

It is not simply one homogeneous futures dataset from 1985 onward.

## 10. Country bond indices

### SOURCE CLAIM

The bond universe contains futures from 13 developed bond markets/instruments, including Australian,
Euro-area, Canadian, Japanese, U.K. and U.S. government-bond futures.

Data sources include:

- Bloomberg;
- Datastream;
- Morgan Markets.

Prior to futures availability, J.P. Morgan country-level bond-index returns are used.

The workbook states that returns are duration-scaled to standardize maturity exposure, using
different target durations for short-, medium- and long-maturity bond futures.

### RESEARCH DIRECTOR INTERPRETATION

Part of the apparent cross-asset comparability is deliberately engineered through risk/duration
normalization.

The factor is not simply the unadjusted sign of raw contract returns.

## 11. Foreign exchange

### SOURCE CLAIM

The dataset contains 12 cross-currency pairs.

The underlying currency-forward universe spans major developed currencies including:

- Australia;
- Canada;
- Germany / euro;
- Japan;
- New Zealand;
- Norway;
- Sweden;
- Switzerland;
- United Kingdom;
- United States.

The workbook states that:

- forwards for the relevant currencies versus USD are used;
- those currencies underlie the cross-currency pairs;
- Citigroup spot/forward interest-rate data are used for much of the return history;
- earlier periods use Datastream spot exchange rates and Bloomberg IBOR short rates to reconstruct
  returns.

### RESEARCH DIRECTOR INTERPRETATION

FX returns are themselves constructed from multiple source regimes through history.

Any reproduction requires data-source provenance, not just a currency-price series.

## 12. Commodities

### SOURCE CLAIM

The commodity universe contains 24 futures covering:

- industrial metals;
- energy;
- soft commodities;
- livestock;
- grains/oilseeds;
- precious metals.

The source names contracts traded historically on:

- LME;
- ICE;
- CME;
- CBOT;
- NYMEX;
- COMEX;
- TOCOM.

It explicitly notes at least one splice:

- RBOB gasoline is spliced with historical unleaded-gasoline data.

Futures prices are obtained from Bloomberg.

### RESEARCH DIRECTOR INTERPRETATION

Again, long histories may involve instrument/data substitutions.

This matters if anyone later tries to reproduce the dataset exactly.

## 13. Full-history reconstruction policy

This is one of the most important properties of LIB-010.

### SOURCE CLAIM

AQR states:

- data are maintained and updated as they become available;
- **the full history is reconstructed each time the returns are updated.**

### RESEARCH DIRECTOR INTERPRETATION

This means the historical portion of the dataset is **versioned data**, not an immutable original
historical record.

Consequences:

1. A later download can potentially revise earlier monthly factor returns.
2. The 1985–2009 portion of this file must not automatically be assumed identical to the original
   paper-data workbook.
3. A future reproduction must pin:
   - exact file;
   - download/version date;
   - file hash;
   - methodological/data-source version.
4. A "post-2009 extension" of this workbook is not necessarily a pure untouched out-of-sample append,
   because the provider explicitly reconstructs the entire history.

This observation follows directly from the workbook's versioning statement; it is not speculation
about whether specific historical rows actually changed.

## 14. Research Director descriptive audit — complete 1985–2026M05 sample

The following statistics are **computed from the downloaded workbook by the Research Director**.

They are not statistics printed by AQR.

Simple annualization:

- arithmetic annualized mean = monthly mean × 12;
- annualized volatility = monthly sample standard deviation × √12;
- mean/volatility ratio = annualized arithmetic mean ÷ annualized volatility.

The last metric is only a descriptive mean/volatility ratio; it is **not claimed as AQR's reported
Sharpe ratio**.

| Series | Annualized mean | Annualized vol | Mean/vol ratio | Positive months |
|---|---:|---:|---:|---:|
| TSMOM | 12.25% | 12.49% | 0.981 | 61.2% |
| TSMOM^CM | 9.66% | 14.87% | 0.649 | 59.4% |
| TSMOM^EQ | 15.04% | 27.56% | 0.546 | 59.0% |
| TSMOM^FI | 17.88% | 29.48% | 0.607 | 56.3% |
| TSMOM^FX | 10.09% | 18.36% | 0.550 | 57.5% |

## 15. Extreme monthly observations in the downloaded version

Research Director computation:

| Series | Worst month | Return | Best month | Return |
|---|---|---:|---|---:|
| TSMOM | 2021-11-30 | -11.47% | 2015-01-30 | +12.96% |
| TSMOM^CM | 2011-09-30 | -19.41% | 2020-03-31 | +19.06% |
| TSMOM^EQ | 1987-10-30 | -34.77% | 1986-03-31 | +31.67% |
| TSMOM^FI | 1994-02-28 | -25.87% | 1998-09-30 | +28.86% |
| TSMOM^FX | 1989-02-28 | -17.64% | 2015-01-30 | +24.42% |

These are factor-series observations, not direct single-instrument trade returns.

## 16. Cross-component correlation audit

Research Director computation over all 497 displayed months:

### All-assets factor versus components

| Pair | Correlation |
|---|---:|
| TSMOM vs CM | 0.664 |
| TSMOM vs EQ | 0.520 |
| TSMOM vs FI | 0.605 |
| TSMOM vs FX | 0.600 |

### Cross-component correlations

| Pair | Correlation |
|---|---:|
| CM vs EQ | 0.121 |
| CM vs FI | 0.109 |
| CM vs FX | 0.235 |
| EQ vs FI | 0.110 |
| EQ vs FX | 0.174 |
| FI vs FX | 0.175 |

### Director interpretation

In this downloaded version, the asset-class sleeves remain relatively weakly correlated with one
another.

This is consistent with diversification being an important property of the all-assets TSMOM
portfolio.

It does **not** imply that a single BTC trend signal will inherit the risk-adjusted characteristics
of the diversified factor.

## 17. Original-era versus later-era descriptive split

Because this file extends far beyond the original paper period, a purely descriptive split is useful.

This is **not** a formal structural-break test and is not attributed to AQR.

### 1985–2009

| Series | Annualized mean | Annualized vol | Mean/vol ratio | Positive months |
|---|---:|---:|---:|---:|
| TSMOM | 16.84% | 11.93% | 1.411 | 67.3% |
| CM | 14.08% | 13.92% | 1.012 | 64.7% |
| EQ | 23.39% | 28.17% | 0.830 | 60.3% |
| FI | 20.92% | 29.66% | 0.705 | 59.0% |
| FX | 14.46% | 18.44% | 0.784 | 60.0% |

### 2010–2026M05

| Series | Annualized mean | Annualized vol | Mean/vol ratio | Positive months |
|---|---:|---:|---:|---:|
| TSMOM | 5.25% | 13.06% | 0.402 | 51.8% |
| CM | 2.92% | 16.06% | 0.182 | 51.3% |
| EQ | 2.34% | 26.25% | 0.089 | 56.9% |
| FI | 13.25% | 29.21% | 0.454 | 52.3% |
| FX | 3.44% | 18.11% | 0.190 | 53.8% |

### Director interpretation

The later period in this **current reconstructed dataset version** has materially lower descriptive
return-to-volatility characteristics than the 1985–2009 period, especially for:

- all-assets TSMOM;
- equities;
- currencies;
- commodities.

This is a meaningful observation for later research discussion, but it does **not** by itself prove:

- permanent trend-edge decay;
- crowding;
- regime change;
- loss of statistical significance;
- failure of all momentum strategies.

A formal conclusion would require a predeclared analysis with appropriate inference and awareness
that AQR reconstructs historical data when updating the series.

## 18. Relationship to the original-paper concept

This workbook adds materially more implementation detail than the two-page LIB-015 summary.

It establishes from the source itself that the distributed factor uses:

- a 12-month time-series-momentum rule;
- a 1-month holding period;
- sign-based long/short direction;
- ex-ante volatility normalization;
- equal-weighted diversified aggregation;
- lagged volatility estimates to avoid look-ahead;
- 58 underlying cross-asset instruments.

It is therefore useful not merely as a return table but as a compact methodology/data package.

However, the workbook explicitly warns that current construction/data sources can differ from the
2012 implementation.

## 19. What this source supports for Trading Bot

### Strong conceptual relevance

The source provides professional precedent for:

1. **signal direction from own-history momentum**;
2. **separating direction from position risk scaling**;
3. **ex-ante volatility normalization**;
4. **strictly lagged risk estimates to avoid look-ahead**;
5. **cross-instrument aggregation only after normalizing risk**;
6. **versioned data provenance**;
7. **evaluating a signal family across heterogeneous markets rather than relying on one market**.

### Important limitation

The excellent historical properties of the diversified TSMOM factor cannot be transferred directly
to a BTC-only system.

The factor's diversification across 58 instruments is structurally different from one BTC position.

## 20. What this source does NOT support

LIB-010 does not establish:

- a profitable BTCUSDT strategy;
- a 12-month BTC lookback;
- a 1-month BTC holding period;
- a 40% BTC volatility target;
- any 15m/1h/4h BTC parameter;
- any signal weight for Trading Bot;
- any optimal stop/target;
- any crypto-specific order-flow mechanism;
- any cycle rule;
- that the factor returns are net of all realistic modern trading costs;
- that post-2009 performance is equally strong;
- that the current dataset is identical to the original paper dataset.

## 21. Data-versioning implication for future scientific governance

This source creates a concrete provenance rule for Trading Bot:

> Any external dataset whose provider can reconstruct historical values must be pinned by immutable
> local copy and hash before it is used in an experiment.

For this specific file, the canonical local fingerprint is:

`33470930e2269c0d97be4732ec2d9c27ddbc69ac8133b059a263e27400263eeb`

If a later AQR download differs, it is a **new dataset version**, even if the filename and date range
look similar.

## 22. Disclosures

The workbook states, in substance, that:

- it is for informational purposes;
- it is not an offer, solicitation or investment recommendation;
- information is impersonal and may be revised;
- AQR does not warrant accuracy/adequacy/completeness;
- no strategy is assured to succeed;
- historic market trends are not reliable indicators of future performance;
- historical information should not be treated as a recommendation;
- cited index performance is total-return based;
- exchange-rate changes can affect investment results;
- past performance is not an indication of future results.

These disclosures were read from the embedded disclosure object rather than inferred from the data
sheet.

## 23. Durable project knowledge retained from LIB-010

1. The current AQR TSMOM dataset is an **updated and extended** descendant of the 2012 paper factors.
2. AQR explicitly allows for differences in **data sources and methodology** versus the original.
3. The distributed factor is a **12-month TSMOM / 1-month holding** strategy.
4. Direction follows each instrument's trailing 12-month return sign.
5. Positions are normalized using lagged ex-ante volatility.
6. The source uses a common risk-normalization framework across heterogeneous markets.
7. Individual positions are scaled to a 40% ex-ante annualized-volatility convention before
   diversification; this is a research normalization convention, not a recommendation.
8. The overall factor aggregates across **58 underlying instruments** spanning equity indices,
   bonds, FX and commodities.
9. Historical data sources are spliced in multiple markets when futures/history are unavailable.
10. AQR **reconstructs the full historical return series whenever the data are updated**.
11. Therefore exact dataset version/hash is part of scientific provenance.
12. The downloaded version contains 497 continuous monthly observations from 1985-01 through
    2026-05.
13. No values are missing in the five displayed return series.
14. The asset-class sleeves are only weakly correlated in this version, making diversification an
    important property of the aggregate.
15. Descriptive performance after 2009 is materially weaker than in 1985–2009 in the current
    reconstructed series.
16. This cross-asset portfolio evidence cannot be converted directly into a single-BTC expected
    performance claim.

## 24. Questions for Astra at final corpus review

1. How much of TSMOM's historical strength should be attributed to the directional phenomenon versus
   cross-asset diversification and volatility normalization?
2. Does the 12-month-sign formulation teach us anything about *signal architecture* that transfers
   across horizons, even when the numeric 12-month parameter does not?
3. Should Trading Bot normalize directional evidence by current volatility, or should volatility
   affect only sizing/actionability?
4. What is the cleanest way to prevent a professional trend family from being double-counted through
   multiple correlated transforms?
5. How should the material weakening of the updated factor after 2009 affect the prior assigned to
   trend/momentum, without overinterpreting an informal period split?
6. Does full-history reconstruction by AQR prevent the post-2009 portion from being called a pristine
   out-of-sample extension of the original factor?
7. If this source is used in any later reproduction exercise, should its exact hash be frozen in the
   experiment manifest?
8. Which elements of its no-look-ahead volatility methodology should become deterministic tests in
   Trading Bot?
9. How much relevance should the 40% single-position risk normalization have for a one-asset system,
   if any?
10. What current BTC-specific evidence would be required before transferring any of these concepts
    from monthly diversified futures to short-horizon BTC?

## 25. Final source disposition

`REVIEWED`

Reason:

The complete workbook was inspected, including:

- all four worksheets;
- all 497 displayed monthly observations;
- metadata/provenance;
- dataset schema;
- date continuity and missing-value audit;
- methodology embedded in `Definitions`;
- embedded `Data Sources`;
- embedded `Disclosures`;
- absence of spreadsheet formula cells;
- descriptive return/risk statistics;
- cross-component correlations;
- a clearly labeled descriptive 1985–2009 versus 2010–2026M05 comparison;
- provider full-history-reconstruction policy;
- limitations and Trading Bot relevance.

No external source was used to fill gaps in the workbook.

No Trading Bot strategy, signal weight, parameter, System G2 design or market experiment is
authorized by this dataset.
