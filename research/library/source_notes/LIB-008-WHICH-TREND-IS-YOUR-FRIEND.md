# LIB-008 — Which Trend Is Your Friend? — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `lasse_heje_pedersen_et_al_which_trend_is_your_friend_publishersversion.pdf`  
Drive file id: `1xspqO4DGcziazpO9Z9h-1mc6FK5Fncoo`  
Local corpus id: `LIB-008`

## 1. Source identity

**Title:** *Which Trend Is Your Friend?*  
**Authors:** Ari Levine and Lasse Heje Pedersen  
**Journal:** Financial Analysts Journal  
**Volume / issue:** 72(3)  
**Pages:** 51–66  
**Publication year:** 2016  
**DOI:** `10.2469/faj.v72.n3.3`  
**License shown in repository copy:** CC BY  
**Source type:** peer-reviewed academic paper  
**Project evidence tier:** A

The PDF contains:

- repository cover / publication metadata;
- the complete published article;
- 14 figures;
- 2 empirical result tables;
- Appendix A — HP filter;
- Appendix B — OLS best-fit trend;
- Appendix C — data sources;
- notes and references.

The complete accessible source was reviewed, including visual inspection of every PDF page.

## 2. Research question

The paper asks a deceptively important question:

> When practitioners use different trend-following indicators, are they actually extracting different
> information, or are many of them alternative representations of the same underlying trend signal?

The two principal methods studied are:

- **time-series momentum (TSMOM)**;
- **moving-average crossover (MACROSS)**.

The authors then broaden the argument to other linear filters used in finance, economics and signal
processing.

The paper is therefore primarily about:

- **signal representation**;
- **filter equivalence**;
- **horizon selection**;
- and the practical importance of implementation.

It is not a paper claiming that one particular indicator formula is universally optimal.

## 3. Core theoretical result

### SOURCE CLAIM — generalized TSMOM and generalized MACROSS are equivalent

The paper's central theoretical result is that the most general forms of:

- TSMOM written as weighted past returns;
- MACROSS written as weighted past prices;

can be converted into one another.

A general TSMOM signal is represented as a weighted combination of past price changes / returns:

`TSMOM_t = sum_s c_s (P_{t-s+1} - P_{t-s})`

where the coefficient `c_s` determines how much the return at lag `s` contributes to the trend
estimate.

A general MACROSS is the difference between two weighted moving averages of past price levels:

`MACROSS_t = MA_fast - MA_slow`.

Because price changes are differences of adjacent price levels, the two representations can be
translated algebraically into one another by changing the weights.

### Important implication

The fact that two indicators have different names or formulas does **not** imply that they contain
independent information.

Two trend rules can be very close representations of the same linear filter applied in:

- price space;
- return space.

This is one of the strongest source-grounded lessons for the future Trading Bot architecture.

## 4. Time-series momentum in the paper

### 4.1 Simplest TSMOM

The simplest TSMOM signal is the asset's return over a chosen lookback horizon:

`TSMOM_t^m = Return_{t-m,t}`.

For example, a 12-month TSMOM signal is positive when the asset has risen over the preceding
12 months and negative when it has fallen.

The paper notes that returns can be constructed from:

- price ratios;
- log-price differences;
- or return indices that account for dividends/coupons, roll yields and financing where appropriate.

For analytical simplicity in this paper, the authors work primarily with differences in log prices
or index levels.

### 4.2 Smoothing

The paper distinguishes:

- **back-end smoothing** — averaging prices around the older endpoint;
- **front-end smoothing** — averaging prices around the current endpoint.

Back-end smoothing can reduce arbitrary endpoint noise.

Front-end smoothing also reduces noise and potentially turnover, but it delays the response to
recent information.

This creates an explicit trade-off:

> smoother signal versus faster reaction to a changing trend.

### 4.3 Generalized TSMOM

The paper generalizes TSMOM by assigning an independent coefficient to each lagged return.

Positive coefficients correspond naturally to trend-following exposure.

Negative coefficients can introduce reversal or acceleration/deceleration effects.

This generalized representation is much broader than a single "12-month momentum" rule.

## 5. Moving-average crossover in the paper

MACROSS uses two moving averages:

- `MA_fast`, which emphasizes recent prices;
- `MA_slow`, which emphasizes more distant prices.

The signal is:

`MACROSS = MA_fast - MA_slow`.

A positive value implies that recent prices are above older prices and is interpreted as an upward
trend.

The paper permits arbitrary weighting schemes for the moving averages, including:

- equal weights;
- exponential weights.

A moving average is considered "faster" when it systematically places more cumulative weight on
recent observations.

## 6. Price space and return space

A major conceptual contribution of the article is the graphical distinction between:

### Price signature plot

Shows the weight the signal places on each historical **price level**.

### Return signature plot

Shows the weight placed on each historical **price change / return**.

The authors use these plots to reveal that apparently different indicator formulas can embody very
similar exposure to historical returns.

### Example: 20/260 equal-weight MACROSS

In price space:

- recent prices receive positive weight;
- older prices receive negative weight.

When translated into return space, the MACROSS assigns:

- less weight to the most recent returns;
- greatest weight to intermediate lags;
- declining weight to older returns.

By comparison, a simple 260-day TSMOM gives equal weight to every return inside its lookback.

### Research Director interpretation

For Trading Bot, comparing indicators by name is scientifically weak.

A better question is:

> What historical returns does each indicator effectively weight, and with what shape?

This provides a principled way to detect redundant indicators.

## 7. TSMOM as MACROSS and MACROSS as TSMOM

The authors explicitly derive both directions.

### MACROSS -> TSMOM

The difference between the fast and slow moving-average weights on prices can be converted into
coefficients on past returns.

For ordinary trend-following MACROSS rules in which the fast average is uniformly faster, the
resulting TSMOM coefficients are positive.

### TSMOM -> MACROSS

A simple TSMOM return between two endpoints can itself be represented as a moving-average
difference where the "fast" average is concentrated on the current price and the "slow" average is
concentrated on the lagged price.

More sophisticated TSMOM smoothing maps to more sophisticated moving-average structures.

### SOURCE CAUTION

The representation in moving-average space is not always unique because the same component can be
added to both moving averages without changing their difference.

The return-space TSMOM coefficients provide a more fundamental description of the filter.

## 8. Exponentially weighted moving averages

The paper studies EWMA crossover filters.

Instead of equal weighting inside fixed windows, historical prices receive exponentially declining
weights.

The authors parameterize the exponential moving average using a **center of mass (COM)**, which is
more intuitive than the raw decay coefficient.

The COM represents the effective historical location of the moving average.

The corresponding return-space weights are smoother than those generated by a rectangular/equal-
weighted moving-average crossover.

### Project relevance

This reinforces the idea that:

- SMA;
- EMA;
- crossover variants;

should not automatically become separate evidence families in Trading Bot.

They are often variations in the **shape and horizon of a common trend filter**.

## 9. General linear filters

### SOURCE CLAIM — broad equivalence class

The paper states that a large class of linear filters can be expressed within the generalized TSMOM /
MACROSS framework.

More formally, any filter that is:

- **causal** — depends only on past information;
- **linear**;
- **time invariant**;

can be represented as a weighted sum of past observations.

The authors then show how several familiar filtering methods map into this framework.

### Critical limitation

This result does **not** mean every possible trading rule is equivalent.

The equivalence applies to the relevant class of linear filters.

Nonlinear effects are not automatically captured by the basic framework.

Examples include:

- persistence of signs;
- state-dependent rules;
- nonlinear transformations;
- acceleration or other interactions.

Some such effects can be approximated by generalized return weights, but the theoretical equivalence
must not be overstated beyond the paper's assumptions.

## 10. Hodrick-Prescott filter

The HP filter separates a price series into:

- a smooth growth component;
- a cyclical/noise component.

The paper shows mathematically in Appendix A that the estimated growth component is a linear
combination of prices.

The change in the growth component is therefore a difference between two moving averages and thus a
MACROSS signal.

Since MACROSS can be represented as TSMOM, the HP trend is also representable as generalized TSMOM.

The paper notes that HP return weights can contain a small negative component, which gives the signal
some acceleration-like behavior in addition to simple momentum.

### Important project caution

The fact that the HP filter is mathematically representable inside this linear trend family does not
prove that "cycles" as a general market concept are the same thing as trend.

The paper is discussing the **HP filtering operation**, not establishing equivalence between all
cycle-analysis frameworks and trend-following.

## 11. Kalman filter

The paper discusses the Kalman filter as a method for estimating a hidden trend in noisy data.

Under a simple **local trend model**:

- price follows a random walk with a trend;
- the trend itself follows a random walk;
- the hidden trend is estimated from observed prices.

Citing Harvey (1984), the authors note that in this model the optimal Kalman trend estimate becomes
an exponentially weighted moving average of past returns.

Therefore, under this particular structure, the Kalman trend estimate is also a TSMOM-type linear
filter.

### Limitation

The result depends on the underlying model.

More elaborate nonlinear or state-dependent Kalman specifications are not automatically covered by
this simple equivalence.

## 12. OLS trend regression

Another trend estimator studied is an ordinary least-squares line fitted to price over a chosen
historical window.

The signal is the estimated slope.

The authors show in Appendix B that the estimated slope can be written as a weighted sum of past
prices and therefore as a weighted sum of historical returns.

The associated return weighting differs from simple TSMOM and MACROSS:

- returns near the middle of the estimation window receive more weight;
- returns near the beginning and end receive less.

Again, what differs is primarily the **shape of lag weights**, not an entirely distinct source of
market information.

## 13. Wavelets and other filters

The article briefly notes that operations such as wavelet-based filtering can also be understood as
weighted historical-return operations in suitable linear implementations.

Wavelets are not empirically tested in the paper.

Their mention should therefore be retained only as part of the conceptual filtering framework, not
as evidence that a wavelet trading rule performs well.

## 14. Empirical dataset

The empirical study uses **58 liquid instruments**:

- 24 commodity futures;
- 13 developed-country government bond futures;
- 12 currency pairs covering 9 underlying currencies;
- 9 developed-country equity indices.

The sample covers:

**January 1985 through April 2015.**

The dataset extends the universe used by Moskowitz, Ooi and Pedersen (2012).

### Return construction

Signals are calculated from return indices built from rolling:

- futures;
- forwards.

The paper states that these indices implicitly incorporate:

- financing;
- carry / rolldown.

Because futures and forwards embed financing, the indices are naturally excess of cash.

Appendix C lists instrument/data-source provenance.

## 15. Empirical strategy definitions

The authors deliberately choose comparable standard implementations.

### TSMOM strategies

Three lookback horizons:

- `TSMOM(22)` — approximately 1 month;
- `TSMOM(66)` — approximately 3 months;
- `TSMOM(260)` — approximately 12 months.

Signal:

`log return index today - log return index n trading days ago`.

### MACROSS strategies

Exponentially weighted moving averages are used because the authors describe them as common in
investment practice.

Three COM pairs:

- `MACROSS(3,12)`;
- `MACROSS(8,32)`;
- `MACROSS(32,128)`.

The slow COM values are chosen to correspond approximately to the TSMOM horizons; the fast COM is
one-quarter of the slow COM.

### Holding / rebalancing

The primary tests use:

- daily rebalancing;
- a new portfolio formed each day;
- one-day holding.

The authors report that one-month holding periods produced qualitatively similar results but lower
Sharpe ratios.

## 16. Portfolio construction and risk scaling

To place all six trend signals on a comparable footing, the authors apply the same portfolio
construction methodology.

For each asset:

- only the **sign** of the signal is used;
- exposure is inversely scaled by estimated volatility;
- volatility is an exponentially weighted estimate with COM = 60 days;
- the per-asset risk target is calibrated at approximately 0.65% annualized volatility.

Across assets this produces portfolio volatility of approximately **10% annualized** for each of the
six strategies.

### Important interpretation

The paper's empirical performance is therefore not merely the raw prediction from an indicator.

It is the result of a full construction containing:

- diversified assets;
- signal transformation to sign;
- volatility scaling;
- risk normalization;
- daily portfolio rebalancing.

This distinction is crucial when considering transferability to a single-asset BTC system.

## 17. Empirical performance

Table 1 reports the following results **before transaction costs**:

| Strategy | Annual excess return | Annualized volatility | Sharpe ratio |
|---|---:|---:|---:|
| MACROSS(3,12) | 10.3% | 10.2% | 1.01 |
| MACROSS(8,32) | 10.9% | 10.3% | 1.06 |
| MACROSS(32,128) | 12.8% | 9.7% | 1.33 |
| TSMOM(22) | 9.8% | 10.1% | 0.97 |
| TSMOM(66) | 12.1% | 10.1% | 1.20 |
| TSMOM(260) | 14.2% | 9.8% | 1.45 |

### SOURCE CLAIM

Both TSMOM and MACROSS produce broadly similar risk-adjusted performance at comparable horizons.

All six reported Sharpe ratios exceed 0.9 before costs.

### Critical limitation

These are:

- diversified cross-asset portfolio returns;
- from 1985–2015;
- before transaction costs.

They are not directly comparable to a BTC-only short-horizon system.

## 18. Regression comparison

The central empirical comparison regresses each MACROSS factor on the three TSMOM factors and vice
versa.

### SOURCE RESULT

All six regressions produce **R² above 80%**.

This provides strong empirical evidence that the commonly implemented TSMOM and MACROSS strategies
in the study are closely related, not just theoretically equivalent in their generalized forms.

### MACROSS on TSMOM

For each of the three tested MACROSS portfolios:

- no significant positive alpha remains over the combination of TSMOM signals;
- `MA(8,32)` has a statistically significant negative intercept in the reported regression.

### TSMOM on MACROSS

Some TSMOM portfolios show positive statistically significant intercepts relative to the three
MACROSS portfolios.

### Authors' caution

The authors explicitly warn **not** to conclude that TSMOM is intrinsically superior.

The asymmetry can arise because the selected TSMOM basis more easily approximates the particular
MACROSS weight shapes than the reverse.

Different MACROSS parameters or a richer set of MACROSS signals might eliminate the apparent
difference.

This is an important anti-overinterpretation point.

## 19. Figure 14 and basis flexibility

Figure 14 illustrates how:

- combinations of the selected TSMOM signals can closely reproduce the return-weight profile of a
  MACROSS signal;
- the selected MACROSS signals are less able to reproduce one example TSMOM profile.

The authors use this to explain why regression alpha asymmetry can arise even when the underlying
families are theoretically equivalent.

### Project implication

A backtest comparison between two indicator families can be misleading if one family has been given
a richer/more flexible parameter basis than the other.

Apparent superiority may reflect **representation flexibility**, not superior information.

## 20. Main conclusion of the paper

The paper's conclusion is unusually relevant to Trading Bot.

The authors state that many trend strategies that look distinct are related through a unified linear
filtering framework.

Their key practical conclusion is that the exact filtering methodology may matter **less** than:

- trend horizon;
- portfolio construction;
- risk management;
- implementation quality.

They specifically point investors toward:

- transaction-cost management;
- dynamic trading;
- diversification;
- position sizing;
- portfolio construction;
- risk management.

This does not mean filter design is irrelevant.

It means that choosing between superficially different linear filters can be a smaller decision than
choosing:

- which horizon is economically relevant;
- how the signal is transformed;
- how risk is allocated;
- how trading is executed.

## 21. Research Director interpretation for Trading Bot

The following are project interpretations, not claims directly made about BTC by the authors.

### 21.1 Trend should be a family, not an indicator collection

This source strongly argues against treating:

- SMA crossover;
- EMA crossover;
- raw return momentum;
- OLS trend;
- simple linear Kalman trend;
- HP linear trend;

as independent "votes" merely because they have different names.

At least within the linear, causal, time-invariant implementations studied, they are alternative
filters over substantially the same underlying information:

**past price changes.**

A future Trading Bot should therefore likely have a **trend family** whose internal implementations
are treated as:

- alternative estimators;
- different horizon/weight shapes;
- robustness checks;

rather than independent confirmations.

No final architecture is frozen by this dossier.

### 21.2 Correlated indicators must not receive additive evidence credit

If EMA crossover and TSMOM encode nearly the same lag-weight exposure, summing both as separate
bullish signals would artificially multiply one piece of evidence.

This source provides much stronger support for the existing project guardrail against feature
double-counting.

### 21.3 Horizon may matter more than branding

The source suggests that the choice between:

- TSMOM;
- MACROSS;
- another linear filter

may matter less than the effective historical horizon/weighting structure.

For Trading Bot, research should therefore focus on:

> What return horizon is relevant to the forecast/trade objective?

rather than:

> Which famous indicator name should we use?

### 21.4 Signal strength and execution remain separate problems

The paper's empirical strategy uses:

- sign transformation;
- volatility scaling;
- portfolio diversification;
- daily rebalancing.

Therefore a trend filter alone does not define a complete trading algorithm.

Trading Bot still needs separate treatment of:

- directional estimate;
- strength/quality;
- regime relevance;
- entry actionability;
- risk;
- execution.

### 21.5 Multi-timeframe trend does not imply independent evidence

Using the same trend family on:

- 15m;
- 1h;
- 4h;
- daily

may provide useful horizon structure.

But the outputs will be statistically and economically related.

They should not automatically be counted as four independent confirmations.

### 21.6 Acceleration may be a distinct feature only when genuinely distinct

The paper shows that allowing negative and positive lag weights can make a linear filter respond to
changes in trend strength / acceleration.

Therefore "momentum acceleration" should not automatically be added as a separate family without
checking whether it is simply another transform of the same past-return information.

## 22. Relationship to cycles

This paper does **not** establish a general theory of market cycles.

It discusses the Hodrick-Prescott filter and calls part of its decomposition cyclical/noise, but the
paper's mathematical argument concerns linear filtering of price history.

Therefore this source cannot be used to conclude:

- professional cycle analysis is redundant with trend;
- all cycle methods are linear trend filters;
- the Owner's intended multi-scale cyclic structure should be removed.

The only defensible conclusion is narrower:

> an HP-filter-based trend estimate lies inside the generalized linear trend-filter family analyzed
> by the paper.

Other cycle methodologies require their own evidence.

## 23. Applicability to BTCUSDT

### Direct conceptual transfer

Strongly transferable concepts:

- indicators can be algebraically redundant;
- signal family grouping should consider effective lag weights;
- horizon selection matters;
- smoothing introduces responsiveness/turnover trade-offs;
- linear filter choice can matter less than implementation/risk architecture.

### Empirical transfer remains unproven

The paper contains:

- no Bitcoin;
- no crypto exchange data;
- no perpetual futures;
- no 24/7 market;
- no intraday 15m/1h/4h evaluation;
- no Binance fees/slippage/funding;
- no single-asset BTC test.

Therefore the empirical Sharpe ratios and optimal-looking horizons must **not** be copied into Trading
Bot.

The paper supports an architecture prior, not BTC parameter calibration.

## 24. What this source does NOT support

The paper does not support:

- EMA as an independent confirmation on top of TSMOM;
- SMA + EMA + MACD + raw momentum being counted as several independent signals;
- any numeric trend-family weight;
- a specific BTC lookback;
- a 260-day BTC requirement;
- a 22/66/260-day parameter grid for Trading Bot;
- a specific Kalman implementation for BTC;
- a conclusion that TSMOM is universally better than MACROSS;
- a claim that the reported Sharpe ratios survive transaction costs;
- a claim that the filters are equivalent once nonlinear state logic is introduced;
- a claim that all technical analysis is reducible to TSMOM;
- a claim that all cycle analysis is reducible to trend.

## 25. Source limitations

1. Empirical universe is diversified traditional futures/forwards, not BTC.
2. Main sample ends April 2015.
3. Reported performance is before transaction costs.
4. Strategies use daily observations/rebalancing, not the Owner's intraday target.
5. Portfolio diversification materially contributes to aggregate risk properties.
6. The theoretical equivalence applies to generalized **linear causal time-invariant** filters.
7. Practical implementations can differ because of:
   - parameter choices;
   - signal transforms;
   - nonlinear portfolio construction;
   - implementation.
8. Sharpe-ratio differences among the six examples should not be interpreted as an optimized
   tournament.
9. The paper is affiliated with AQR; the authors disclose their affiliations.
10. The source does not establish future persistence of trend premia.

## 26. Durable project knowledge retained from LIB-008

The following points should survive into final corpus synthesis:

1. **Generalized TSMOM and generalized MACROSS are equivalent representations of linear trend
   filters.**
2. Trend signals can be represented in **price space** or **return space**.
3. **Trend signature plots** expose the effective historical weights of an indicator.
4. Different indicator names can encode highly redundant information.
5. Standard moving-average crossover generally gives greatest return weight to intermediate lags,
   whereas simple TSMOM weights returns uniformly within its lookback.
6. Front-end smoothing trades responsiveness for lower noise/turnover.
7. Back-end smoothing can reduce endpoint noise.
8. EWMA crossover is another smooth weighting variant of the same broad linear family.
9. HP-filter trend, local-trend Kalman filtering and OLS price-trend regression can be represented as
   generalized linear trend filters under the assumptions shown.
10. Nonlinear/state-dependent rules are not automatically covered by the equivalence result.
11. The empirical study uses 58 liquid instruments from commodities, bonds, FX and equity indices,
    January 1985–April 2015.
12. TSMOM horizons tested are 22, 66 and 260 trading days.
13. MACROSS COM pairs tested are (3,12), (8,32) and (32,128).
14. The six strategies use common volatility scaling and portfolio construction.
15. All six reported Sharpe ratios are around 1 or higher **before transaction costs**.
16. Cross-regressions have R² above 80%, showing substantial empirical overlap.
17. Apparent alpha asymmetry does not establish intrinsic TSMOM superiority.
18. Representation flexibility can create misleading comparisons between signal families.
19. The exact filter may matter less than **horizon, portfolio construction, risk management and
    implementation quality**.
20. A future multi-signal system should prevent multiple correlated trend transforms from being
    counted as independent evidence.

## 27. Questions for Astra at final corpus review

1. Should the future system contain one canonical `TREND` family with multiple internal estimators
   rather than separate EMA/TSMOM/MACROSS indicators?
2. Should signal redundancy be measured using effective lag-weight similarity, return correlation,
   or both?
3. How should multi-timeframe trend outputs be combined without counting the same underlying trend
   information several times?
4. What portions of the paper's linear-filter equivalence remain valid once regime-dependent
   relevance and nonlinear actionability logic are introduced?
5. Should trend estimators be averaged/ensembled for robustness, or should one transparent canonical
   estimator be selected?
6. How should the responsiveness-versus-smoothing trade-off be calibrated in the development
   sandbox without parameter mining?
7. What BTC-specific evidence is needed before selecting the effective horizon of the trend family?
8. Should acceleration/deceleration be considered a separate information family or merely a
   derivative feature inside trend/momentum?
9. Does the paper justify treating "technical indicator diversity" as much smaller than apparent
   indicator catalogs suggest?
10. How should transaction costs and dynamic trading alter the preferred filter horizon for a
    short-horizon BTC system?

## 28. Final source disposition

`REVIEWED`

Reason:

The complete accessible published paper was reviewed, including:

- all article pages;
- mathematical definitions and equivalence arguments;
- all 14 figures;
- both empirical tables;
- empirical data universe;
- signal definitions;
- portfolio construction;
- regressions;
- conclusion;
- Appendices A, B and C;
- notes;
- references;
- declared author affiliations;
- visual page inspection.

No external source was used to fill gaps in this dossier.

No Trading Bot strategy, signal weight, BTC horizon, parameter set, System G2 design or market
experiment is authorized by this paper alone.
