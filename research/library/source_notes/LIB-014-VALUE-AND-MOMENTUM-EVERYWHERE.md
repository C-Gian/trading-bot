# LIB-014 — Value and Momentum Everywhere — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**
Study date: 2026-09-26
Source file: `Value and Momentum Everywhere.pdf`
Drive file id: `13QBCcNRduhNyehFAn_KxwxDEC90P2-2D`
Local corpus id: `LIB-014`

## 1. Source identity

Title shown in file:

**Value and Momentum Everywhere**

Date shown in file:

**June 1, 2013**

Publisher / distributor:

**AQR Capital Management**

Artifact type:

**Institutional secondary summary / informational note**

Important classification point:

The file explicitly states that:

- it is provided as secondary information;
- it should not be the primary source for an investment/allocation decision;
- it is not research and should not be treated as research;
- it is not investment advice;
- its information may be incomplete and is not guaranteed;
- historical market trends are not reliable indicators of future performance.

Therefore this Drive artifact is **not the full academic paper** and must not be treated as if it
contained the underlying paper's full methodology, data construction, robustness tests, tables,
regressions or appendices.

The local source contains approximately two pages of material, including extensive legal/disclosure
language and one substantive summary section.

## 2. What this source actually claims

### SOURCE CLAIM — value and momentum premia appear across diverse markets

The note reports that the underlying work finds consistent **value** and **momentum** return premia
across eight diverse markets and asset classes.

This is a cross-market / cross-asset statement.

The source does **not** provide in this artifact:

- the eight markets;
- their sample periods;
- exact signal definitions;
- portfolio-construction rules;
- transaction-cost assumptions;
- individual performance tables;
- confidence intervals;
- implementation details.

Those details must not be inferred from this summary.

### SOURCE CLAIM — common factor structure

The note reports a strong common factor structure among value and momentum returns.

It states that value and momentum strategies correlate more strongly **across asset classes** than
the passive returns of the underlying asset classes themselves.

This suggests, at the level of the source's summary, that the relevant effects may have cross-market
commonality rather than being isolated quirks of one asset class.

### SOURCE CLAIM — value and momentum are negatively correlated

The source says value and momentum are negatively correlated with each other:

- within asset classes;
- across asset classes.

This is one of the most important statements in the file because it describes **interaction between
signal families**, not merely their standalone historical returns.

The source presents the negative relation as a potentially useful diversification property.

### SOURCE CLAIM — three-factor global framework

The note says the authors use a three-factor model to describe:

- a new set of 48 global across-asset-class test assets;
- Fama–French portfolios;
- several hedge-fund indices.

The precise mathematical definition of the three factors is not contained in this summary artifact.

Do not reconstruct or guess it from outside knowledge when using this dossier.

### SOURCE CLAIM — global funding-liquidity risk is a partial explanation

The source reports that **global funding liquidity risk** is a partial source of the observed
patterns.

The wording is important: **partial source**, not a complete explanation.

It also says these patterns are identifiable only when examining value and momentum **jointly across
markets**.

### SOURCE CLAIM — existing theories are challenged

The source says the findings are difficult to reconcile fully with then-existing:

- behavioral explanations;
- institutional explanations;
- rational risk-based asset-pricing explanations,

especially because many such theories had focused largely on U.S. equities.

The note emphasizes that a globally diversified value-and-momentum portfolio presents a stronger
explanatory challenge than looking at either effect independently in one market.

## 3. Evidence and methodology visible in this artifact

The local file provides only a high-level result summary.

What can be directly established from the file:

- the study concerns **eight diverse markets / asset classes**;
- it discusses **48 global across-asset-class test assets**;
- it uses a **three-factor model**;
- it examines value and momentum jointly;
- it associates part of the common structure with global funding-liquidity risk;
- it compares the resulting framework with Fama–French portfolios and hedge-fund indices.

What cannot be established from this file:

- exact return series;
- exact value metric;
- exact momentum metric;
- lookback horizons;
- rebalancing frequency;
- weighting scheme;
- leverage/risk scaling;
- fees or transaction costs;
- estimation window;
- exact sample dates;
- statistical significance;
- robustness procedures;
- turnover;
- execution assumptions;
- whether the findings survive realistic BTC-specific costs;
- whether the results apply to intraday horizons.

Those omissions materially limit how much this artifact alone can contribute to Trading Bot design.

## 4. Concepts relevant to professional trading

### 4.1 Signal-family diversification matters

The most relevant conceptual lesson is not simply:

> value works and momentum works.

The stronger idea in the source is:

> distinct return-predictive families can have meaningful **joint structure**, and the relationship
> between them may be as important as their isolated historical performance.

For Trading Bot this supports studying **interactions between signal families**, rather than treating
each indicator as an independent vote.

### 4.2 Negative correlation can be useful

If two professionally grounded signal families are negatively correlated, that does not mean one is
wrong.

It may mean they capture different economic mechanisms or perform in different environments.

Therefore a future multi-signal engine should not automatically interpret disagreement as:

`SIGNAL_A + SIGNAL_B = cancellation / uselessness`.

The disagreement itself can carry information.

This is a Research Director interpretation, not a trading rule stated by the source.

### 4.3 Signals can share latent/global drivers

The note's common-factor result implies that apparently different implementations across markets may
share deeper common sources.

For our architecture this argues against counting many superficially different indicators as
independent evidence merely because their formulas differ.

This complements, but does not by itself prove, the need for family-level grouping.

### 4.4 Funding/liquidity context may matter

The note attributes part of the cross-market structure to global funding-liquidity risk.

For BTC this is only a **hypothesis candidate**.

The local artifact provides no evidence about:

- crypto funding rates;
- perpetual futures;
- exchange liquidity;
- BTC spot/perpetual basis;
- BTC order books.

Do not map the phrase "funding liquidity" directly onto Binance perpetual funding rates. They are not
the same concept.

## 5. What this source does NOT support

This file does not support any of the following conclusions:

- that value should be included in Trading Bot;
- that momentum should receive a particular weight;
- that momentum is profitable on BTCUSDT;
- that value is meaningful on BTC without defining a BTC-appropriate notion of value;
- that value and momentum retain the same negative correlation intraday on BTC;
- that a value/momentum combination is profitable after Binance fees/funding/slippage;
- that the three-factor model should be copied into Trading Bot;
- that global funding-liquidity risk is equivalent to crypto perpetual funding;
- that eight-asset-class evidence transfers to the Owner's short-horizon BTC system;
- that signal-family diversification guarantees economic diversification.

## 6. Research Director interpretation

### 6.1 Relevance to the Owner's multi-signal idea

This source is conceptually supportive of the Owner's view that a professional system should combine
multiple meaningful information families rather than test every indicator as an isolated strategy.

However, it does not provide enough information to determine:

- which families Trading Bot should use;
- their base importance;
- how they should be combined;
- how to resolve conflicting signals.

It is therefore **architecture inspiration / external evidence**, not a calibration source.

### 6.2 Relevance to `peso_base`

No numeric base weight can be derived from this artifact.

What may be retained for later synthesis is the qualitative principle:

> a family's importance should not be inferred only from standalone return performance; its
> relationship with other families may matter.

That is directly relevant to a future architecture in which:

- each family has a professional role;
- redundant families are not double counted;
- complementary/negatively related families may improve the information set;
- empirical adjustment is separated from structural importance.

No formula is authorized from this source.

### 6.3 Relevance to momentum

The file supports momentum as a phenomenon worth considering in a professional knowledge map,
because it reports consistent premia across diverse markets.

It does **not** resolve:

- which momentum representation;
- which horizon;
- whether trend following and momentum should be the same family;
- how short an admissible BTC horizon can be;
- whether BTC behaves similarly.

Those questions remain open.

### 6.4 Relevance to value

"Value" is much less directly transferable to the current BTC-only product.

Traditional value signals usually depend on relative valuation/fundamental anchors that may not have
a straightforward single-asset BTC analogue.

This source alone is insufficient to create a BTC value signal.

Therefore:

`VALUE -> METHODOLOGY / CROSS-ASSET CONCEPT ONLY`

unless future sources provide a defensible BTC-specific definition.

## 7. Limitations of the source itself

The most important limitation is structural:

**this is a secondary AQR summary, not the research paper.**

The artifact itself warns that it:

- is not research;
- is secondary information;
- may not be complete;
- should not be a primary basis for an investment decision.

Additional limitations for our project:

- no BTC/crypto data;
- no intraday study;
- no execution model visible;
- no cost model visible;
- no exact signal definitions visible;
- no complete methodology;
- no source tables available in the artifact;
- no ability from this file alone to independently verify the reported results.

## 8. Potential Trading Bot relevance

Classification:

`METHODOLOGY_ONLY / ARCHITECTURE_PRIOR`

Potentially useful later for:

- grouping indicators into information families;
- modeling relationships among families;
- avoiding independent-vote assumptions;
- distinguishing complementarity from directional agreement;
- recognizing liquidity/funding conditions as possible context variables;
- treating momentum as a professional information family worth evaluating.

Not useful by itself for:

- numeric weights;
- BTC parameter values;
- entry/exit rules;
- stop/target geometry;
- timeframe selection;
- live execution assumptions.

## 9. Open questions for final synthesis / Astra

1. Does the full underlying paper provide enough detail to support stronger claims than this
   secondary artifact?
2. Is value relevant at all to a single-asset BTC system, or should it remain outside the active
   signal universe?
3. Should signal-family correlation/redundancy become an explicit part of the future weighting
   architecture?
4. How should disagreement between structurally distinct families affect conviction versus
   direction?
5. Is there credible crypto-specific evidence that any analogous value/momentum relation exists?
6. Is "global funding liquidity" useful as a broad market-context variable for BTC, without
   confusing it with perpetual funding rates?
7. What evidence level should be required before a cross-asset factor becomes a Trading Bot input?

## 10. Source-derived knowledge retained

The durable source-derived points retained from LIB-014 are:

1. the artifact reports value and momentum premia across eight diverse markets/asset classes;
2. it reports a strong common factor structure across their returns;
3. value and momentum are reported as negatively correlated within and across asset classes;
4. their cross-asset correlations are reported as stronger than passive asset-class correlations;
5. a global three-factor framework is reported to explain a broad set of test assets;
6. global funding-liquidity risk is reported as a partial source of the patterns;
7. the source frames joint cross-market analysis as important to identifying those patterns;
8. the artifact itself explicitly says it is **secondary information and not research**.

## 11. Final source disposition

`REVIEWED`

Reason:

The complete accessible Drive artifact has been read and its substantive content, limitations,
classification and potential project relevance have been captured.

This status applies only to the local two-page AQR summary file.

It does **not** imply that the underlying academic paper *Value and Momentum Everywhere* has been
read or reviewed.

No Trading Bot strategy, weight, parameter or market experiment is authorized by this dossier.
