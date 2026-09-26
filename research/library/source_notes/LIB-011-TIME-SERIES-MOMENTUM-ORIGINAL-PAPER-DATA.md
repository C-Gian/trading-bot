# LIB-011 — Time Series Momentum Original Paper Data — Dataset Dossier

Status: **REVIEWED — COMPLETE WORKBOOK INSPECTION**  
Study date: 2026-09-26  
Source file: `Time Series Momentum Original Paper Data.xlsx`  
Drive file id: `1QGGdj54WNKst45EY0AZyeISHDhDFCVyv`  
Local corpus id: `LIB-011`  
Raw file size: 40,014 bytes  
SHA-256: `91bdbae6366ccb0693581b690236dc14862562a98ee83052c4f440f8b6ae0db8`

## 1. Source identity and provenance

The workbook identifies itself as:

**AQR Capital Management, LLC — Time Series Momentum: Original Paper Data**

The workbook states that it contains the TSMOM factors used in:

Moskowitz, Tobias J., Yao Hua Ooi and Lasse H. Pedersen (2012),  
**“Time Series Momentum,” Journal of Financial Economics, 104(2), 228–250.**

The workbook includes a link to the associated paper:

`http://people.stern.nyu.edu/lpederse/papers/TimeSeriesMomentum.pdf`

That external paper was **not opened or used during this source study**. This dossier is grounded only
in the workbook itself.

The workbook states:

> monthly excess returns of the time series momentum factors, 1985–2009

for:

- all assets;
- global equity indices;
- currencies;
- fixed income;
- commodities.

Copyright notice in the workbook:

**Copyright ©2012 Tobias Moskowitz, Yao Hua Ooi, and Lasse Heje Pedersen**

## 2. Workbook structure

The workbook contains exactly two worksheets.

### Sheet 1 — `TSMOM factors`

Used range:

`A1:F311`

Structure:

- rows 1–10: title, provenance, paper link, copyright and dataset description;
- row 11: data headers;
- rows 12–311: monthly factor returns;
- 300 monthly observations total.

Columns:

| Column | Header | Workbook meaning |
|---|---|---|
| A | DATE | observation date |
| B | TSMOM | time-series-momentum factor across all assets |
| C | TSMOM^EQ | global equity-index TSMOM factor |
| D | TSMOM^FX | currency TSMOM factor |
| E | TSMOM^FI | fixed-income TSMOM factor |
| F | TSMOM^CM | commodity TSMOM factor |

The workbook itself explains the superscripts:

- no superscript = all assets;
- EQ = global equity indices;
- FX = currencies;
- FI = fixed income;
- CM = commodities.

### Sheet 2 — `Disclosures`

The visible cells contain a `Disclosures` title.

The substantive disclosure text is stored in a **text box / drawing object**, not ordinary cells.

This was inspected separately so that disclosure content was not missed by normal tabular parsing.

## 3. Disclosure content

The disclosure text states, in substance, that:

- the information is provided solely for informational purposes;
- it is not an offer, solicitation, advice or recommendation;
- the information is impersonal and not tailored to a person/entity;
- it is subject to review/revision;
- AQR is not responsible for errors/omissions or results obtained from its use;
- the information may become outdated;
- accuracy, adequacy and completeness are not warranted;
- it should not be the sole basis for an investment decision;
- no investment strategy is assured to succeed;
- historical trends are not reliable indicators of future behavior/performance;
- cited index performance uses total returns with dividends reinvested;
- currency movements may adversely affect investments;
- past performance is not indicative of future results.

These disclosures are part of the workbook and should remain attached to any interpretation of the
data.

## 4. Data coverage audit

### Time coverage

First observation:

**1985-01-31**

Last observation:

**2009-12-31**

Observation count:

**300 months**

This is exactly 25 years of monthly observations.

### Continuity

The dates are:

- strictly increasing;
- unique;
- monthly with no missing calendar month.

No monthly gap was detected between January 1985 and December 2009.

Some dates are the last trading/business day rather than the literal calendar month-end; this is
visible directly in the workbook.

### Missing values

Missing-value count:

| Series | Missing values |
|---|---:|
| DATE | 0 |
| TSMOM | 0 |
| TSMOM^EQ | 0 |
| TSMOM^FX | 0 |
| TSMOM^FI | 0 |
| TSMOM^CM | 0 |

The local workbook therefore provides a complete rectangular monthly panel for the five factor
series over its stated period.

## 5. Units and interpretation supported by the workbook

The workbook explicitly labels the values as:

**monthly excess returns**

The numerical representation is decimal return form.

Example:

`0.04100435`

corresponds to approximately:

`+4.10%`

for that monthly factor observation.

The workbook does **not** state inside this file:

- the precise TSMOM signal-construction formula;
- the exact underlying 58 instruments;
- signal lookback;
- volatility scaling;
- portfolio weights;
- contract rolling rules;
- leverage;
- rebalancing details;
- transaction-cost treatment;
- slippage;
- financing mechanics;
- statistical estimation procedure.

Those details must not be inferred from this dataset alone.

## 6. Data examples

First data row:

**1985-01-31**

- TSMOM: 0.04100435
- TSMOM^EQ: 0.1058403
- TSMOM^FX: 0.07231003
- TSMOM^FI: -0.006098145
- TSMOM^CM: -0.01392326

Last data row:

**2009-12-31**

- TSMOM: -0.01696685
- TSMOM^EQ: 0.06104244
- TSMOM^FX: -0.03777016
- TSMOM^FI: -0.09996179
- TSMOM^CM: 0.009136912

These examples are included only to demonstrate the schema and scale.

## 7. Research Director descriptive audit

The following statistics are **computed directly from the workbook values by the Research Director**.

They are not statistics printed by AQR in this workbook and must not be attributed to the authors.

Simple annualization used below:

- arithmetic annualized mean = monthly mean × 12;
- annualized volatility = monthly sample standard deviation × √12;
- mean/volatility ratio = annualized arithmetic mean ÷ annualized volatility.

This is a descriptive audit only, not a reproduction of the paper's official statistics.

| Series | Mean month | Monthly vol | Annualized mean | Annualized vol | Mean/vol ratio | Positive months |
|---|---:|---:|---:|---:|---:|---:|
| TSMOM | 1.423% | 3.559% | 17.075% | 12.330% | 1.385 | 67.3% |
| TSMOM^EQ | 1.951% | 8.173% | 23.409% | 28.311% | 0.827 | 60.3% |
| TSMOM^FX | 1.171% | 5.460% | 14.053% | 18.913% | 0.743 | 60.0% |
| TSMOM^FI | 1.844% | 8.599% | 22.129% | 29.789% | 0.743 | 58.7% |
| TSMOM^CM | 1.206% | 3.932% | 14.475% | 13.620% | 1.063 | 63.0% |

### Extreme monthly observations in the supplied series

| Series | Worst month | Return | Best month | Return |
|---|---|---:|---|---:|
| TSMOM | 1987-10-30 | -11.761% | 1986-03-31 | +11.668% |
| TSMOM^EQ | 1987-10-30 | -35.034% | 1986-03-31 | +32.605% |
| TSMOM^FX | 1989-02-28 | -18.193% | 2008-10-31 | +20.380% |
| TSMOM^FI | 1994-02-28 | -25.907% | 1998-09-30 | +31.159% |
| TSMOM^CM | 1999-03-31 | -9.881% | 2008-02-29 | +16.563% |

These extremes show that the component factor series can experience very large monthly moves.

They should not be read as live-trading drawdowns without understanding the factor construction,
leverage/scaling and portfolio mechanics that are absent from this workbook.

## 8. Correlation audit

The following correlations are also Research Director computations from the supplied 300 monthly
observations.

### All-assets factor versus component factors

| Pair | Correlation |
|---|---:|
| TSMOM vs TSMOM^EQ | 0.675 |
| TSMOM vs TSMOM^FX | 0.548 |
| TSMOM vs TSMOM^FI | 0.538 |
| TSMOM vs TSMOM^CM | 0.609 |

### Cross-component correlations

| Pair | Correlation |
|---|---:|
| EQ vs FX | 0.201 |
| EQ vs FI | 0.213 |
| EQ vs CM | 0.198 |
| FX vs FI | 0.045 |
| FX vs CM | 0.130 |
| FI vs CM | 0.072 |

### Director interpretation

Within this supplied period, the four asset-class TSMOM component series are only weakly to
moderately correlated with one another.

This is consistent with the dataset containing economically distinct asset-class sleeves.

However:

- the workbook does not explain the exact aggregation from sleeves into TSMOM;
- the correlation table is a descriptive property of this sample;
- it does not establish diversification for BTC;
- it does not establish causality or persistence outside 1985–2009.

## 9. Relationship to LIB-015

`LIB-015 — Time Series Momentum.pdf`

was a two-page AQR secondary summary.

This workbook is materially different.

It is a **numeric dataset** and explicitly states that it contains the TSMOM factors used in the
original 2012 academic paper.

LIB-015 summarized the claimed phenomenon.

LIB-011 provides monthly factor-return series associated with the original paper.

Neither local file, by itself, contains the full academic-paper methodology.

Therefore:

- LIB-015 is not a substitute for LIB-011;
- LIB-011 is not a substitute for the full paper;
- the two should not be counted as independent empirical confirmations of the same result.

They are related artifacts around the same underlying research programme.

## 10. What this dataset supports

This workbook supports the factual statements that:

1. the authors/AQR distribute 300 monthly observations labelled as TSMOM factor excess returns;
2. the supplied period is January 1985 through December 2009;
3. the workbook contains an all-assets factor and four asset-class factor series;
4. the four classes are EQ, FX, FI and CM;
5. the supplied series contain no missing month/value over that interval;
6. the numeric series can be independently inspected and summarized;
7. the workbook identifies these as the factors used in the 2012 JFE paper.

The workbook allows direct verification of the historical return series distributed in this file.

## 11. What this dataset does NOT support

The workbook alone does not support conclusions about:

- why TSMOM works;
- the exact signal formula;
- causal mechanism;
- transaction costs;
- modern live implementability;
- robustness beyond 2009;
- post-publication decay;
- BTC/crypto transferability;
- intraday trend;
- 15m/1h/4h forecasting;
- Binance execution;
- a specific signal weight;
- a LONG/SHORT threshold;
- the optimal lookback;
- the original paper's complete statistical significance claims.

It also does not prove that the supplied factor returns are directly investable returns available to
a modern trader after all costs.

## 12. Relevance to Trading Bot

Classification:

`METHODOLOGY / EXTERNAL EMPIRICAL DATASET`

### Useful later for

- verifying that the time-series-momentum research has an actual distributed numeric record;
- understanding how a broad TSMOM factor can be decomposed by asset class;
- studying historical variability of trend-factor returns;
- studying cross-asset-class diversification conceptually;
- reproduction/validation work if the full paper is later admitted as a source.

### Not directly useful for

- training or calibrating the BTC system;
- choosing BTC signal weights;
- selecting an intraday lookback;
- evaluating BTC execution;
- selecting stops/targets;
- asserting a current trend edge.

The data are traditional-asset monthly factor returns through 2009, not BTC market observations.

## 13. Important scientific caution

This workbook should **not** enter a future BTC model as a training dataset.

Doing so would conflate:

- external literature evidence;
- a cross-asset monthly factor-return dataset;
- BTC-specific development data.

Its correct role in the current project is **knowledge/evidence provenance**, not model fitting.

## 14. Potential project implications

These are Research Director interpretations to preserve for final synthesis, not frozen design rules.

### 14.1 Trend evidence exists at the portfolio/factor level

The dataset provides a concrete numeric artifact behind the broader professional literature on
time-series momentum.

This strengthens the case that trend/momentum deserves consideration as a professional information
family.

It does not determine its BTC implementation.

### 14.2 Cross-market diversification may matter to interpretation

The relatively low pairwise correlation among the four asset-class sleeves suggests that a broad
trend phenomenon need not be driven by one single asset class.

That is useful as external evidence against interpreting the original research as merely a U.S.
equity effect.

It still says nothing directly about BTC.

### 14.3 Portfolio-level TSMOM is not the same thing as one-asset trend signal

The all-assets TSMOM factor is a diversified portfolio construct.

Trading Bot is initially a single BTCUSDT system.

Therefore the strong descriptive properties of the all-assets series cannot be transferred directly
to a single BTC trend signal.

This distinction is essential.

## 15. Questions for Astra at final corpus review

1. How much evidentiary weight should a distributed factor dataset receive relative to the full
   academic paper that defines its construction?
2. Should LIB-011 and LIB-015 be treated as one evidence family rather than two independent sources?
3. Is the low cross-component correlation relevant to our architecture, or mostly a portfolio-level
   property outside the single-asset product?
4. What parts of the original TSMOM construction, if any, are conceptually transferable to a
   single-asset short-horizon BTC system?
5. Should the full academic paper be required before freezing any trend/momentum architecture?
6. Does the absence of post-2009 data in this original-paper dataset materially weaken its relevance
   for a 2026 system?
7. What crypto-specific dataset would be required before claiming that the historical TSMOM
   phenomenon transfers to BTC?
8. Should future Trading Bot evidence reports explicitly separate:
   - external literature datasets;
   - BTC development data;
   - protected BTC evaluation;
   - prospective paper evidence?

## 16. Final source disposition

`REVIEWED`

Reason:

The complete workbook was inspected, including:

- both worksheets;
- all 300 monthly observations;
- dataset metadata/provenance;
- data schema;
- date continuity;
- missing-value audit;
- disclosure text stored in the drawing/text-box object;
- descriptive statistics;
- factor correlations;
- source limitations.

No outside source was used to fill missing methodology.

No Trading Bot strategy, signal weight, parameter, System G2 design or market experiment is
authorized by this dataset.
