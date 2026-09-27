# LIB-007 — Trend Following and Drawdowns: Is This Time Different? — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `Man_AHL_Insights_Trend_Following_and_Drawdowns__Is_This_Time_Different__English_(United_States)_17-06-2025.pdf`  
Drive file id: `1BGwgPnBXF2_YaFUjivsdntguIDQdR2pg`  
Local corpus id: `LIB-007`  
SHA-256: `2caecf4dcdde8e5da1882cac3e505b411fa2c0aef10a096be4eb77ba10a9ae4e`

## 1. Source identity

**Title:** *Trend Following and Drawdowns: Is This Time Different?*  
**Date:** June 2025  
**Author:** Russell Korgaonkar  
**Role shown in source:** CIO, Man AHL  
**Publisher / institution:** Man AHL / Man Group  
**Artifact type:** institutional practitioner research / investment commentary  
**Project classification:** INSTITUTIONAL_PRACTITIONER  
**Evidence tier:** B

The author thanks Harry Moore for contribution to the analysis and additional Man colleagues for
assistance preparing figures.

The local PDF contains 18 physical pages:

- 16 pages of substantive article/figures;
- bibliography;
- legal/regulatory disclosures.

The paper is contemporary institutional analysis of a difficult period for trend following in 2025.

It is not a peer-reviewed academic experiment and is written by a firm professionally associated with
trend-following investment strategies. That does not invalidate the analysis, but it creates an
important **institutional-interest / advocacy context** that must remain visible.

## 2. Study coverage

The entire accessible PDF was reviewed.

Coverage included:

- title / key takeaways;
- opening discussion of edge decay;
- six-line investigation into whether the recent trend-following drawdown represents structural
  failure;
- all 12 figures and captions;
- all simulation assumptions stated in captions/text;
- historical examples;
- final portfolio-role argument;
- conclusion;
- bibliography;
- final disclosures.

No outside source was used to fill gaps or verify claims in this dossier.

## 3. Central question

The paper asks:

> does the difficult 2025 trend-following performance indicate that time-series trend following has
> structurally stopped working, or is the drawdown consistent with the normal behaviour of a
> probabilistic long-horizon strategy?

The author's answer is:

**the evidence examined does not support the conclusion that trend following is structurally broken.**

The paper argues that:

- some systematic edges genuinely do decay;
- very short-term trend is an example the author believes has substantially weakened;
- traditional time-series trend has shown materially greater persistence;
- large drawdowns are compatible with a strategy that still has positive long-run expected return;
- abandoning such a strategy after drawdown can impose substantial opportunity cost;
- the strategy's portfolio value partly comes from its historically convex behaviour during major
  equity stress.

This is the **source's conclusion**, not a Trading Bot conclusion.

## 4. Important distinction: some systematic edges really do disappear

The paper explicitly rejects the simplistic idea that:

> a strategy that worked historically should always continue working.

### SOURCE CLAIM — equity pairs-trading edge decay

The author uses systematic equity pairs / short-horizon mean-reversion as an example of an edge that
was once strong and later diminished.

The proposed explanation is:

- better technology;
- faster information processing;
- more capital competing for the same inefficiency;
- improved market efficiency.

The illustrated pairs strategy is described as:

- equity-sector mean reversion;
- rolling Z-score on normalized prices;
- holding period under 10 days;
- returns shown **before costs**;
- June 1973–May 2025.

The chart is explicitly illustrative rather than a canonical investable index.

### SOURCE CLAIM — very fast trend also decayed

The second example is a very fast trend system:

- moving-average crossover;
- peak weight at about two days;
- one-day lag used to simulate costs;
- diversified across roughly 100 markets;
- August 1960–May 2025.

The paper argues that trend on horizons shorter than about one week has become less effective as
information is incorporated into prices faster.

### RESEARCH DIRECTOR INTERPRETATION

This is highly relevant to Trading Bot.

The source itself provides a reason not to assume:

`trend exists historically -> faster trend must also work`.

It supports **horizon-specific edge reasoning**.

A durable trend phenomenon at medium/long horizons does not automatically validate minute/hour
versions.

This is particularly important because Owner Product Mission V2 targets much shorter horizons than
traditional institutional trend following.

## 5. The six lines of investigation

The paper structures its defence of trend following around six questions.

---

## 5.1 Investigation 1 — Is the current drawdown historically extraordinary?

### SOURCE CLAIM — current 12-month drawdown

To 30 April 2025, the paper reports a rolling 12-month SG Trend Index return of:

**-18.6%**

It states that since January 2000 only two rolling 12-month observations had been worse than -15%,
with the previous worst reported as:

**-16.0% in January 2019**

The histogram shown in Figure 2 covers January 2000–April 2025.

### SOURCE CLAIM — positive skew

The paper emphasizes that:

- rolling losses worse than -15% were rare;
- gains above +30% occurred more frequently.

It interprets this as evidence of a positively skewed return distribution associated with trend
following.

### IMPORTANT LIMITATION

This figure describes the **SG Trend Index**, not an abstract universal trend strategy.

It does not show:

- all trend funds;
- all possible trend rules;
- BTC;
- a single market;
- intraday trend.

### SOURCE CLAIM — what followed previous drawdowns?

The paper reports:

- +82.5% from the January 2019 12-month low to the beginning of the then-current drawdown in May
  2024;
- across previous rolling 12-month drawdowns greater than 10%, the following 12-month return
  averaged **+9.8%**.

Two then-current drawdown periods had not yet completed their following 12-month window and are
marked unknown in the figure.

### SCIENTIFIC CAUTION

The paper does **not** establish:

`drawdown causes rebound`.

This is an historical conditional observation from a small number of episodes.

It can be affected by:

- overlapping rolling windows;
- small sample size;
- strategy/index construction;
- regime dependence.

The correct source-level claim is:

> previous severe SG Trend 12-month drawdowns were often followed by positive subsequent returns in
> the available sample.

Not:

> after a trend drawdown one should expect +9.8%.

---

## 5.2 Investigation 1b — Are large drawdowns mathematically compatible with a good strategy?

Figure 4 switches from historical trend data to a **hypothetical simulation**.

Assumptions stated:

- Sharpe ratio = 0.5;
- annualized volatility = 10%;
- zero autocorrelation;
- returns assumed normal and identically distributed.

The paper reports the estimated probability of experiencing a drawdown of 20% or more:

| Track-record length | Probability |
|---|---:|
| 5 years | 21% |
| 10 years | 41% |
| 15 years | 58% |
| 20 years | 71% |
| 25 years | 79% |
| 30 years | 83% |

### SOURCE INTERPRETATION

Even an investment with seemingly attractive long-run properties can have a large drawdown over a
long enough life.

### CRITICAL LIMITATION

This table is **not empirical evidence about actual trend-following drawdowns**.

It is a simulated generic strategy under:

- normality;
- IID returns;
- fixed Sharpe;
- fixed volatility;
- zero autocorrelation.

Real trading returns may violate all of these assumptions.

### PROJECT RELEVANCE

This is a useful warning against a future governance rule of the form:

> a sufficiently large drawdown automatically proves system death.

Drawdown magnitude must be interpreted relative to:

- expected return distribution;
- realized volatility;
- horizon;
- prior evidence;
- structural evidence of edge deterioration.

It does not justify tolerating arbitrary drawdowns in Trading Bot.

---

## 5.3 Investigation 2 — Is trend becoming overcrowded or arbitraged away?

The paper examines crowding from several angles.

### AUM share

Figure 5 compares CTA assets under management with total hedge-fund assets.

The paper concludes that trend/CTA AUM has **not** grown into an obviously alarming share of hedge
fund assets.

### Futures-market participation

The second panel estimates trend followers' share of listed futures trading volume.

The plotted share falls materially from earlier decades and is around low-single-digit percentages in
recent years.

The source therefore concludes that trend following does not appear to dominate futures-market
turnover.

### Flows vs performance

Figure 6 compares monthly trend-following performance with normalized net flows.

Data range:

**April 1973–April 2025**

The paper reports correlation:

**-0.1**

It says the conclusion is similar using lagged performance or absolute flows.

### SOURCE CONCLUSION

The author finds no evidence in these measures that recent performance deterioration is being driven
by trend-follower crowding/flows.

### RESEARCH DIRECTOR CAUTION

This is evidence **against one simple crowding story**, not proof that crowding cannot matter.

AUM, volume share and monthly flows may fail to detect:

- similarity of models;
- position concentration;
- simultaneous deleveraging;
- liquidity-sensitive crowding;
- crowded entry/exit timing;
- common risk controls.

Therefore retain:

> these particular aggregate crowding proxies do not show an obvious deterioration story.

Do not retain:

> trend following is not crowded.

## 6. Investigation 3 — Is the environment currently unsuitable?

### SOURCE CLAIM — difficult environments have occurred before

The paper points to 2009–2013:

- SG Trend Index total return reported: **-1.8%**
- 2014 return reported: **+19.7%**

The author argues that investors who concluded the strategy had stopped working during the flat
period would have missed the later strong year.

### SOURCE CLAIM — whipsaw environment

The paper characterizes part of 2025 as unusually hostile to trend following because repeated sharp
policy-driven reversals produced **whipsaws**:

- models repositioned in response to large moves;
- subsequent reversals invalidated the position before a sustained trend could develop.

The paper uses one contemporaneous policy-reversal episode as an illustrative case.

### RESEARCH DIRECTOR INTERPRETATION

This is one of the strongest concepts for our future architecture:

**trend quality is not the same thing as raw directional movement.**

A market can move violently while still being poor for trend if:

- direction changes faster than the model can adapt;
- breaks repeatedly reverse;
- signal horizon and regime duration are mismatched.

This supports treating:

- trend direction;
- trend persistence/quality;
- whipsaw risk

as distinct concepts.

It does not define a Trading Bot formula for them.

## 7. Single-market persistence and the cocoa example

Figure 8 shows representative trend-following returns for more than 100 markets from January 2018
to March 2024, highlighting cocoa.

The highlighted cocoa sleeve experienced:

- years of cumulative losses;
- then a sharp recovery that erased those losses and moved materially positive.

The author uses this to argue that removing an underperforming market after a long difficult period
can cause investors to miss the trend that eventually emerges.

### SOURCE CLAIM

Individual trend markets often produce:

> many small/protracted losses followed by occasional large gains.

### IMPORTANT LIMITATION

This is one highlighted market example.

It does not establish that every persistently losing market will recover.

The phrase in the article that trends "inevitably emerge" is stronger than the evidence shown by one
example and should not be treated as a scientific certainty.

### PROJECT RELEVANCE

For Trading Bot, a losing run in a signal family should not automatically trigger removal.

But neither should the cocoa example justify endless patience.

A valid future decision would need evidence about:

- whether the hypothesized mechanism remains present;
- whether realized behaviour is statistically compatible with prior expectations;
- whether execution/cost structure changed;
- whether the signal's horizon still matches the market.

## 8. Investigation 4 — Drawdowns are compatible with positive long-run expectancy

Figure 9 is another **simulation**, not historical trend data.

Assumptions stated:

- Sharpe ratio = 0.6;
- annualized volatility = 15%;
- normal IID returns.

The illustrated 30-year path ends at more than eight times initial capital but contains:

- roughly a -32% drawdown;
- another roughly -33% drawdown;
- a period in which capital remains below a prior high for about nine years.

### SOURCE CONCLUSION

A profitable long-run process can look broken for years.

### RESEARCH DIRECTOR INTERPRETATION

This is directly relevant to scientific governance:

**pathwise pain is not identical to evidence of edge failure.**

A strategy should be rejected because evidence about its expected process deteriorates, not merely
because the realized sequence was unpleasant.

However:

- a simulated IID normal path is illustrative;
- real structural breaks do occur;
- a strategy cannot use this argument as immunity from falsification.

The correct tension is:

> do not kill a strategy merely because it draws down; do not protect it from evidence merely by
> calling every failure "normal drawdown."

## 9. Investigation 5 — Opportunity cost of drawdown-based abandonment

The paper asks whether deallocating after a drawdown protects investors at too high a cost.

### Simulation design

Three hypothetical independent strategies:

- each Sharpe = 0.6;
- each annualized volatility = 15%;
- assumed uncorrelated;
- normal IID returns;
- equal one-third starting allocations.

Dynamic rule:

- if a sleeve reaches a 20% drawdown, move that sleeve to cash;
- re-enter only once the strategy's hypothetical underlying track record recovers to flat;
- weights are not redistributed.

Comparison:

- **Dynamic Portfolio** — applies the drawdown rule;
- **Consistent Portfolio** — remains invested.

### SOURCE RESULT

In the illustrated sample the consistent portfolio materially outperforms because the dynamic
portfolio misses rebounds.

Across **10,000 simulated experiments**, the paper reports that the Consistent Portfolio
outperformed the Dynamic Portfolio by an average:

**2.2% per annum**

### IMPORTANT LIMITATION

This result is conditional on the simulated world where:

- the strategy's true return distribution never deteriorates;
- drawdowns are random realizations of the same fixed process;
- the strategy itself is not structurally broken.

Under those assumptions, drawdown-based deallocation is mechanically prone to sell a still-valid
strategy at a bad point.

The simulation does **not** answer the harder real-world question:

> what if the strategy's underlying expectancy has actually changed?

### PROJECT RELEVANCE

For Trading Bot governance, this argues against using **realized drawdown alone** as the system's
scientific kill switch.

A future retirement rule should ideally combine:

- realized performance;
- predeclared expected distribution;
- structural diagnostics;
- market/execution changes;
- independent evidence.

## 10. Quant-equity analogy

The paper also examines a separate market-neutral equity-factor portfolio:

- value;
- momentum;
- quality;
- low beta;
- equal-weighted;
- leverage factor 2;
- annual volatility roughly 12%.

Reported path:

- Jan 2010–31 Mar 2020: **+67%**
- subsequent peak-to-trough drawdown: **-29%**
- recovery from lows to 30 Apr 2025: **+84%**

### PURPOSE IN SOURCE

The example is not trend-following evidence.

It is used as an analogy:

> established strategies can experience long and severe drawdowns without necessarily losing their
> underlying rationale.

### PROJECT RELEVANCE

Do not count this as independent evidence that trend itself persists.

It is evidence only for the broader methodological point that:

- persistent investment processes can experience severe path-dependent underperformance.

## 11. Investigation 6 — What role does trend following play?

The paper argues that trend following's main portfolio benefit is not merely low average correlation
with equities.

It emphasizes **convexity**.

### SOURCE DEFINITION IN CONTEXT

Here, convexity means:

> trend following has historically delivered some of its strongest returns during the worst equity
> periods.

Figure 12 groups quarterly equity returns into quintiles and compares average quarterly performance
for:

- SG Trend Index;
- global bonds;
- multi-strategy hedge funds.

The paper shows trend performance strongest in the worst equity-return quintile, while the other two
diversifiers do not show the same pattern.

### SOURCE CONCLUSION

Trend may provide diversification particularly when equity markets experience sustained large
directional moves.

### IMPORTANT QUALIFICATION

Trend can still fail during:

- sharp reversals;
- V-shaped markets;
- repeated whipsaws.

Its crisis benefit depends on a dislocation lasting long enough for trend systems to:

- detect;
- reposition;
- hold the direction.

### PROJECT RELEVANCE

This reinforces a distinction between:

- **trend direction**
- **trend duration/persistence**
- **reversal risk**

A future Trading Bot trend engine should not equate:

`large move = good trend opportunity`.

## 12. Historical evidence versus simulation versus opinion

For final synthesis, the paper must be decomposed into evidence classes.

### A. Observed index / market history

Examples:

- SG Trend return distribution since 2000;
- previous SG Trend drawdowns and subsequent returns;
- trend AUM/volume proxies;
- flow/performance correlation;
- 2009–2014 SG Trend path;
- GFC trend/equity path;
- cocoa example;
- quant-equity factor example;
- equity-quintile diversification comparison.

### B. Hypothetical simulations

Examples:

- probability of a 20% drawdown for a 0.5 Sharpe / 10% vol IID normal strategy;
- 0.6 Sharpe / 15% vol 30-year illustrative path;
- dynamic 20%-drawdown-deallocation rule;
- 10,000-run comparison yielding the reported 2.2% annual opportunity cost.

### C. Practitioner judgement / forward-looking interpretation

Examples:

- very fast trend is unlikely to regain its old edge;
- current trend following is not structurally broken;
- current policy-driven whipsaws are likely to normalize;
- future divergent global trends may emerge.

These categories must **not** be assigned the same evidentiary weight.

## 13. Strongest lessons for Trading Bot

These are Research Director interpretations grounded in the source.

### 13.1 Edge decay is real and horizon-specific

The paper openly acknowledges that systematic strategies can lose their edge.

That supports ongoing surveillance for structural decay.

At the same time, it suggests decay can differ sharply by horizon:

- ultra-fast trend may disappear;
- slower trend may persist.

For Trading Bot, this is highly relevant because our target horizons are shorter than classical CTA
trend horizons.

### 13.2 Drawdown is evidence, but not sufficient evidence

A drawdown should update belief about a strategy.

It should not mechanically decide the strategy's fate.

The update must ask:

- was this drawdown plausible under the ex-ante expected process?
- has the market mechanism changed?
- did costs/liquidity change?
- is the observed failure concentrated in one regime?
- are independent signals of decay present?

### 13.3 Whipsaw should be treated explicitly

Trend failure in rapidly reversing markets is structurally different from trend failure caused by a
vanishing predictive relationship.

That suggests future diagnostics should distinguish:

- **trend absent / noisy**
- **trend present but reverses too quickly**
- **trend captured but execution loses**
- **trend model horizon mismatched**

### 13.4 Do not optimize by deleting recent losers

The cocoa example is a warning about ex-post universe pruning.

A market or component that has recently hurt performance may later supply a large trend.

This creates an anti-overfitting principle:

> removing components primarily because their recent P&L is unattractive is scientifically dangerous
> unless there is a predeclared structural reason.

### 13.5 Strategy lifecycle rules need a structural component

A future kill/reallocation mechanism should not be based only on:

- drawdown;
- rolling Sharpe;
- recent win rate.

It should also look for changes in:

- information incorporation speed;
- market structure;
- liquidity;
- crowding;
- signal horizon;
- costs;
- causal economic mechanism.

## 14. Direct relevance to Owner Product Mission V2

### Trend as a professional information family

This source strengthens the case that trend deserves a place in the final knowledge map.

But it does **not** specify a BTC implementation.

### Multi-timeframe importance

The paper's distinction between:

- decayed very-fast trend;
- persistent slower trend

directly argues for treating trend strength as a **function of horizon**, not a single scalar.

This supports multi-timeframe architecture conceptually.

### NO_TRADE / actionability

A trend signal may exist while the current environment is dominated by rapid reversals.

Therefore a future system may need:

- directional trend state;
- trend quality/persistence state;
- reversal/whipsaw risk;
- actionability.

This is compatible with the Owner's desire to distinguish prediction from trade action.

### Risk and strategy monitoring

The paper argues against panic abandonment after drawdown.

For Trading Bot, this suggests:

- drawdown is a risk/governance variable;
- it is not itself a directional input;
- system retirement should be evidence-based, not emotional or purely path-based.

## 15. What this source does NOT support

LIB-007 does not support:

- a specific BTC trend signal;
- a specific moving-average pair for BTC;
- a 15m/1h/4h trend parameter;
- any numerical signal weight;
- a claim that trend always recovers after drawdown;
- a claim that all CTA strategies remain profitable;
- a claim that trend following cannot become crowded;
- a claim that every losing market should be retained indefinitely;
- a 20% Trading Bot drawdown tolerance;
- a rule to add risk after losses;
- a rule to hold through any loss;
- a claim that the 2.2% simulated opportunity cost applies to BTC;
- a claim that traditional CTA convexity exists at our intended BTC horizon;
- a direct justification for real-money deployment.

## 16. Source limitations

### 16.1 Institutional conflict / advocacy context

Man AHL is a professional systematic investment manager and the article is written by its CIO.

The source therefore has a commercial/institutional perspective favourable to trend following.

The analysis should be taken seriously but not treated as independent adjudication.

### 16.2 Non-peer-reviewed format

This is practitioner research/commentary, not a peer-reviewed paper.

### 16.3 Small numbers of severe historical drawdowns

Conditional post-drawdown averages can be based on few episodes.

### 16.4 Rolling-window dependence

Rolling 12-month returns are overlapping and therefore not independent observations.

### 16.5 Simulations use simplified distributions

Key drawdown/opportunity-cost simulations assume normal IID returns and constant strategy quality.

Real strategies may have:

- skew;
- fat tails;
- autocorrelation;
- regime changes;
- edge decay.

### 16.6 Index evidence is not a universal trend system

SG Trend represents a category/index, not all possible implementations.

### 16.7 Traditional diversified CTA setting

The analysis concerns diversified cross-market trend portfolios.

Trading Bot initially trades one market:

**BTCUSDT**

Portfolio-level diversification and convexity cannot be copied directly.

### 16.8 Horizon mismatch

Institutional trend is generally much slower than the Owner's planned decision horizon.

The paper itself warns that very fast trend has decayed.

This is a major caution, not a minor footnote.

## 17. Durable knowledge retained from LIB-007

The following points should survive into final corpus synthesis:

1. **Systematic edges can decay.**
2. **Decay can be horizon-specific.**
3. Very fast trend is presented by this source as an example of an edge weakened by faster
   information incorporation.
4. Traditional time-series trend is argued to have shown greater persistence.
5. A severe drawdown can occur even when long-run expectancy remains positive.
6. Drawdown magnitude alone is insufficient to establish structural strategy death.
7. Historical post-drawdown rebounds do not imply deterministic mean reversion of strategy P&L.
8. Aggregate CTA AUM/volume and flow data in this paper do not show an obvious crowding explanation
   for recent weakness.
9. Whipsaw regimes are intrinsically hostile to trend.
10. Long periods of poor single-market trend performance can precede large profitable trends.
11. Ex-post deletion of recent losers can create selection error.
12. Mechanical drawdown-based deallocation can have high opportunity cost if the underlying edge
    remains unchanged.
13. That opportunity-cost result is conditional on strong simulation assumptions.
14. Trend's portfolio value is partly associated with positive skew / crisis convexity.
15. Trend's crisis benefit requires sufficiently persistent moves; sharp reversals can hurt badly.
16. Strategy monitoring should distinguish **bad luck / normal drawdown** from **structural edge
    deterioration**.
17. A future signal architecture should distinguish trend direction from trend quality/persistence
    and whipsaw risk.
18. Evidence from diversified institutional trend cannot directly validate short-horizon BTC trend.

## 18. Questions for Astra at final corpus review

1. How should the project formally distinguish **normal drawdown** from **edge decay**?
2. What structural diagnostics should be required before retiring a signal family?
3. Does the paper's fast-trend decay argument imply a strong prior against 15m–4h BTC trend, or is
   crypto sufficiently different to require fresh evidence?
4. How should trend quality / persistence / whipsaw risk be represented without creating a
   parameter-heavy feature soup?
5. Can trend direction and actionability be separated cleanly in the future scoring architecture?
6. How much weight should institutional practitioner evidence receive when the institution has a
   commercial interest in the strategy?
7. Should drawdown-based governance be replaced by an expectancy/structural-break framework?
8. What evidence would legitimately justify removing a historically poor market/component rather
   than retaining it for diversification?
9. Does the diversified CTA convexity literature have any meaningful analogue in a single-asset
   BTC strategy?
10. How should the project test for horizon-specific trend decay without mining a large grid of
    lookbacks?

## 19. Final source disposition

`REVIEWED`

Reason:

- complete 18-page PDF reviewed;
- all substantive text read;
- all 12 figures and their captions inspected;
- bibliography and disclosures inspected;
- observed historical evidence separated from hypothetical simulations;
- practitioner opinion separated from source data;
- transfer limits to BTC and short horizons recorded;
- no numeric Trading Bot parameter or strategy rule derived.

This source is retained as **important practitioner evidence about trend persistence, edge decay,
drawdown interpretation, whipsaw regimes and strategy lifecycle governance**.

It does not authorize System G2, a BTC trend implementation, parameter calibration, paper trading or
real capital.
