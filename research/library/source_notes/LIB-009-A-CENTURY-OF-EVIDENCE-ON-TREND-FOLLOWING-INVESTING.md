# LIB-009 — A Century of Evidence on Trend-Following Investing — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `AQR JPM Fall 2017.pdf`  
Drive file id: `19VKw0xmAvsgZtaPq7f2SR2zT1tPQG6Pv`  
Local corpus id: `LIB-009`  
Raw PDF pages: **16**  
Raw file size: **2,752,830 bytes**  
SHA-256: `d2b96b73e6b7e90c244562822e98455c110796bc03056d12fff17fb1bf825dfa`

## 1. Source identity

**Title:** *A Century of Evidence on Trend-Following Investing*  
**Authors:** Brian Hurst, Yao Hua Ooi, Lasse Heje Pedersen  
**Publication:** *The Journal of Portfolio Management*  
**Volume / issue:** Volume 44, Number 1  
**Date:** Fall 2017

Author affiliations shown in the article:

- Brian Hurst — AQR Capital Management;
- Yao Hua Ooi — AQR Capital Management;
- Lasse Heje Pedersen — AQR Capital Management, Copenhagen Business School, and New York University.

Artifact type:

**Published academic/practitioner research article**

Project classification:

`PEER_REVIEWED_ACADEMIC_PAPER / EXTERNAL EMPIRICAL EVIDENCE`

The article studies whether trend-following / time-series momentum documented in recent decades is a
statistical accident or a long-lived characteristic of speculative markets.

## 2. Complete study coverage

The full accessible PDF was reviewed, including:

- abstract/introduction;
- Data;
- Constructing the Time-Series Momentum Strategy;
- Performance over a Century;
- Performance during Crisis Periods;
- Performance across Economic Environments;
- Conclusion;
- Exhibits 1–11;
- Appendix A — Markets and Data Sources;
- Appendix B — Simulation of Fees and Transaction Costs;
- endnotes;
- references.

The PDF was also visually checked page-by-page so tables/figures were not treated as plain-text
omissions.

## 3. Core research question

### SOURCE CLAIM

The authors ask whether the strong performance of trend following observed in modern datasets is:

- a statistical fluke;
- a result of data mining;
- or a more persistent phenomenon that survives across long historical periods and many economic
  environments.

They extend time-series-momentum analysis back to **1880**.

The resulting simulated strategy-return sample runs from:

**January 1880 through December 2016**

because three years of prior observations are needed for the volatility estimates.

## 4. Data universe

### SOURCE CLAIM

The main text uses monthly returns for **67 markets** across four asset classes:

- **29 commodities**;
- **11 equity indices**;
- **15 bond markets**;
- **12 currency pairs**.

The universe changes over time according to data availability.

The strategy therefore operates only on markets with available data at each historical date.

### 4.1 Commodities

The commodity dataset is especially important to the paper.

The authors manually reconstruct historical futures data extending as far back as the late 1870s.

For the early period:

- historical Chicago Board of Trade annual reports were manually transcribed;
- two independent data vendors transcribed the data;
- the two versions were cross-checked;
- where closing prices were unavailable, the average of high and low prices was used.

Later commodity data come from electronic sources including Bloomberg and Commodity Systems Inc.

### 4.2 Equity indices and bonds

Where futures data exist, futures returns are used.

Before futures are available, the authors simulate exposure using:

- cash indices;
- locally relevant short-term financing rates.

For historical bond data, duration adjustments are made for some cash bond series.

### 4.3 Currencies

The strategy uses 12 currency-pair series in Exhibit A1.

The appendix prose describes underlying currency spot/forward and interest-rate sources used to
construct historical currency returns.

### 4.4 Historical realism caveat

The authors explicitly state that they are **not claiming the complete strategy was literally
implementable in the 1880s**.

Reasons include:

- modern financing markets did not exist;
- equity-index futures did not exist;
- bond futures did not exist.

The commodity-futures portion is the most directly implementable part of the early historical sample.

The paper's stated purpose is to test whether **market trends themselves existed historically**, not
to claim that an 1880 investor could have traded the exact modern portfolio.

## 5. Strategy construction

This is one of the most important parts of the paper.

### SOURCE CLAIM — deliberately simple trend model

The authors intentionally avoid a highly complex trend model.

They construct an **equal-weighted combination of three time-series momentum strategies** based on:

- past **1-month** excess return;
- past **3-month** excess return;
- past **12-month** excess return.

### 5.1 Direction rule

For each lookback horizon and each market:

- positive past excess return -> **LONG**;
- negative past excess return -> **SHORT**.

Each underlying horizon strategy is therefore always either long or short in every eligible market.

There is no source-level `NO_TRADE` state in this design.

### 5.2 Position sizing

Each market position is volatility scaled so that markets contribute comparable risk.

This is intended to:

- improve diversification;
- prevent one naturally volatile market from dominating portfolio risk.

### 5.3 Signal aggregation

The three horizon strategies are combined with equal weight.

The combined position is then scaled to target:

**10% annualized ex-ante portfolio volatility**

### 5.4 Portfolio covariance estimate

The paper uses a covariance matrix estimated from:

**rolling three-year equally weighted monthly returns**

for portfolio volatility scaling.

### RESEARCH DIRECTOR INTERPRETATION

This architecture separates several concepts that are often incorrectly conflated:

1. **direction** — sign of past excess return;
2. **horizon diversification** — 1m / 3m / 12m;
3. **per-market risk normalization**;
4. **portfolio-level risk scaling**.

The paper does not infer directional conviction by simply increasing leverage because a market moved
more strongly in the same direction.

## 6. Relationship to previous TSMOM literature

The methodology follows:

- Moskowitz, Ooi & Pedersen (2012);
- Hurst, Ooi & Pedersen (2013).

The authors explicitly frame the very long pre-modern history as an **out-of-sample extension**
relative to prior literature.

The article also cites Levine & Pedersen (2016) for the result that generalized time-series momentum
can represent moving-average crossover signals and other linear trend filters.

Important project implication:

many superficially different linear trend indicators may belong to the **same information family**
rather than being independent confirmations.

The formal proof of that equivalence is not contained in this paper and should ultimately be grounded
in LIB-008 when that source dossier is completed.

## 7. Full-sample performance

### SOURCE RESULT — January 1880 to December 2016

Exhibit 1 reports:

- gross-of-fee, gross-of-cost annualized excess return: **18.0%**
- gross-of-fee, net-of-simulated-cost annualized excess return: **11.0%**
- net-of-hypothetical-2/20-fee, net-of-cost annualized excess return: **7.3%**
- realized volatility: **9.7%**
- net-of-fees-and-costs Sharpe ratio: **0.76**
- correlation to U.S. equity market: **-0.01**
- correlation to U.S. 10-year bond returns: **-0.03**

These are historical simulated portfolio results for this diversified strategy.

They are **not** BTC expectations.

### SOURCE CLAIM — decade consistency

The strategy produces positive simulated performance across the long historical record.

The authors emphasize that the effect appears in each decade, despite environments including:

- Great Depression;
- wars;
- recessions and expansions;
- stagflation;
- global financial crisis;
- rising and falling interest-rate regimes.

### IMPORTANT LIMITATION

The long sample does not create 137 years of identical-quality evidence.

Different eras use different instruments and reconstruction methods.

Therefore longevity and direct implementability must be separated.

## 8. Signal-horizon results

Exhibit 2 studies the three trend horizons separately.

### Full-sample gross Sharpe ratios

For January 1880–December 2016:

- 1-month signal: **1.38**
- 3-month signal: **1.19**
- 12-month signal: **1.32**

When execution of the signal is delayed by one month:

- 1-month signal lagged: **0.45**
- 3-month signal lagged: **0.64**
- 12-month signal lagged: **1.04**

### SOURCE INTERPRETATION

Lagging the signal generally reduces performance.

The deterioration is strongest for the shorter horizon.

This is consistent with the idea that faster signals lose more value when acted upon late.

### Recent-period qualification

For **2010–2016**, the gross Sharpe ratios in Exhibit 2 are much weaker:

- 1-month: **0.06**
- 3-month: **0.30**
- 12-month: **0.73**

Lagged:

- 1-month: **0.13**
- 3-month: **0.33**
- 12-month: **0.70**

This is important because the paper's full-sample result should not be summarized as if performance
were temporally uniform.

The long-horizon signal was materially stronger than the short-horizon signal in this recent
subperiod.

### RESEARCH DIRECTOR INTERPRETATION

The result supports:

- trend as horizon-sensitive;
- latency mattering more for fast signals;
- avoiding a single universal "trend parameter".

It does **not** tell us that BTC should use any of these horizons.

## 9. Cross-market robustness

### SOURCE RESULT

Across the **67 individual markets**, the paper reports positive average time-series-momentum returns
for every market in the full sample.

The average individual-market Sharpe ratio is reported as approximately:

**0.4**

The authors also analyze pre-1985 observations for markets with at least 10 years of data and report
broad positive results.

### SOURCE INTERPRETATION

This pre-1985 test matters because Moskowitz et al. (2012) begin their principal modern sample in
1985.

The authors therefore view 1880–1984 as additional out-of-sample historical evidence relative to
that modern study.

### PROJECT CAUTION

This is still:

- cross-market;
- largely futures/forward;
- monthly;
- portfolio-scaled evidence.

It is not evidence that a single BTCUSDT intraday signal will have positive expectancy.

## 10. Crisis behavior

### SOURCE CLAIM — trend "smile"

The paper finds a convex or "smile"-shaped relationship between annual trend-following returns and
U.S. equity-market returns.

Historically, trend following performs especially well in:

- very strong equity bull markets;
- major equity bear markets.

### SOURCE RESULT — 60/40 drawdowns

During the 10 largest historical drawdowns of a conventional U.S. 60/40 stock/bond portfolio, the
trend strategy produces positive returns in:

**8 of 10 periods**

### SOURCE INTERPRETATION

Trend following can benefit from major bear markets when declines unfold gradually enough for trend
signals to turn negative and establish short positions.

The average peak-to-trough duration of the 10 largest 60/40 drawdowns is reported as roughly:

**15 months**

### SOURCE LIMITATION — abrupt crashes

The authors explicitly note that rapid crashes can be bad for trend following.

The 1987 crash is given as an example:

a strategy based on historical trends may not reposition quickly enough when a major reversal occurs
over only a few days.

This is an important counterweight to the simplistic claim:

> trend following always protects in crashes.

It does not.

## 11. Trend strategy's own drawdowns

Trend following itself experiences substantial and prolonged losses.

Exhibit 8 reports the 10 largest peak-to-trough drawdowns.

Largest reported drawdown:

- peak: August 1947;
- trough: December 1948;
- recovery: February 1951;
- peak-to-trough drawdown: **-24.7%**
- excess return during peak-to-trough interval: **-26.1%**
- peak-to-trough duration: **16 months**
- trough-to-recovery: **26 months**

Other major historical drawdowns are roughly in the -14% to -23% range.

A 2015–2016 drawdown was still unrecovered at the end of the paper's sample.

### SOURCE INTERPRETATION

The main failure environments are associated with:

- sharp reversals across markets;
- prolonged periods where many markets lack clear trends.

### PROJECT IMPLICATION

Trend should not be modeled as:

- permanently profitable;
- crisis-proof;
- continuously informative.

Whipsaw / reversal regimes are fundamental failure modes.

## 12. Diversification with traditional 60/40

Exhibit 7 compares:

### 60/40 alone

- annualized excess cash return: **4.1%**
- annualized volatility: **10.7%**
- maximum drawdown: **-62.3%**
- net-of-fee Sharpe ratio: **0.39**

### 80% of 60/40 + 20% TSMOM

- annualized excess cash return: **4.8%**
- annualized volatility: **8.7%**
- maximum drawdown: **-50.2%**
- net-of-fee Sharpe ratio: **0.55**

### IMPORTANT PROJECT LIMITATION

This result is portfolio-allocation evidence.

Trading Bot is currently a single-asset trading product.

The diversification result should therefore not be misused as evidence for BTC directional alpha.

## 13. Economic-regime analysis

The paper studies trend performance across:

- recession vs boom;
- low vs high inflation;
- major war vs peace;
- equity bull vs bear markets;
- equity-market volatility quintiles;
- changes in volatility;
- cross-market correlation quintiles;
- T-bill yield quintiles.

### SOURCE RESULT — growth / inflation / war

The strategy performs relatively similarly across:

- recessions and booms;
- low- and high-inflation regimes;
- war and peace.

Differences are generally not statistically significant.

### SOURCE RESULT — bull / bear markets

Performance is better in bear markets, but the binary bull/bear difference is described as only
marginally significant.

The authors regard the broader "smile" relationship as more robust.

## 14. A very important causal / point-in-time distinction

The paper explicitly distinguishes:

### Panel A — contemporaneous regime analysis

The regime and trend return are measured in the **same month**.

This is descriptive.

It cannot automatically support a timing decision because the full regime may not have been known
at the start of the month.

### Panel B — lagged regime analysis

The prior month's regime is related to the next month's trend return.

This is closer to a prospective timing test.

Even here, the authors warn that some regime labels are not known in real time.

Examples:

- recession dates may be published retrospectively;
- the low/high-inflation classification is constructed ex post.

### RESEARCH DIRECTOR INTERPRETATION

This is directly aligned with Trading Bot's point-in-time discipline.

A variable can show a strong historical association while still being **invalid as a live input**
because its classification relies on future/revised information.

The paper itself makes this distinction rather than merely reporting regime correlations.

## 15. Market correlation as the clearest regime relation

### SOURCE RESULT

Among the economic indicators studied, **average absolute pairwise correlation across markets** is
the variable with the clearest monotonic relationship to trend performance.

Historically:

- low cross-market correlation -> better trend performance;
- high cross-market correlation -> worse trend performance.

The paper reports that correlations rose materially from late 2008 through roughly mid-2014, during
a risk-on/risk-off environment where many markets moved together.

### SOURCE INTERPRETATION

Because portfolio volatility is targeted, high correlations force total exposures lower.

The authors also state the intuitive interpretation:

when correlations are high, there are **fewer genuinely distinct trends to bet on**.

### PROJECT LIMITATION

This finding depends strongly on a diversified **multi-market portfolio**.

Trading Bot initially trades BTCUSDT only.

Therefore this exact portfolio-correlation regime variable is not directly transferable.

A single-asset analogue would require a separate hypothesis, not a literal copy.

## 16. Volatility result

### SOURCE RESULT

The paper does not find a simple monotonic relationship between trend performance and changes in
equity-market volatility.

Performance is historically relatively similar across periods of:

- increasing volatility;
- decreasing volatility.

The authors therefore caution against casually describing trend following as simply a strategy that
is "long volatility."

### PROJECT IMPLICATION

Do not encode:

`high volatility = trend good`

or

`trend = long volatility`

as a source-supported rule.

The relationship is more nuanced.

## 17. Transaction costs

The paper subtracts simulated transaction costs.

Costs are based on proprietary 2012 estimates for average one-way transaction costs including:

- commissions;
- market impact.

### Exhibit B1 — assumed one-way transaction costs

#### Equities

- 1880–1992: **0.34%**
- 1993–2002: **0.11%**
- 2003–2016: **0.06%**

#### Bonds

- 1880–1992: **0.06%**
- 1993–2002: **0.02%**
- 2003–2016: **0.01%**

#### Commodities

- 1880–1992: **0.58%**
- 1993–2002: **0.19%**
- 2003–2016: **0.10%**

#### Currencies

- 1880–1992: **0.18%**
- 1993–2002: **0.06%**
- 2003–2016: **0.03%**

Historical assumptions are approximately:

- 2× modern costs for 1993–2002;
- 6× modern costs for 1880–1992.

### SOURCE LIMITATION

The authors explicitly state that cost estimates are uncertain.

They also state that the simulation does **not** include all possible costs, notably:

- futures roll costs / roll-down effects.

Therefore "net of cost" does not mean "all economically relevant frictions perfectly modeled."

## 18. Simulated investment-management fees

For the net-of-fee series, the paper subtracts:

- **2% annual management fee**
- **20% performance fee**

The performance fee is:

- accrued monthly;
- subject to an annual high-water mark.

This is intended to approximate historical managed-futures hedge-fund economics.

These fees are not a recommendation for Trading Bot and have no direct relevance to V1 paper
trading except as part of the source's robustness exercise.

## 19. Delay / implementability test

The paper recomputes each trend strategy with a **one-month lag** between signal formation and trade.

The lagged strategies generally remain positive over long history but weaken materially.

Shorter signals deteriorate the most.

### RESEARCH DIRECTOR INTERPRETATION

This is valuable because it tests more than raw signal existence.

It probes whether the signal depends on unrealistically instantaneous action.

For Trading Bot, an analogous principle may eventually require:

- timestamped feature availability;
- decision latency;
- execution latency;
- fill assumptions.

The paper does not tell us what delay matters for BTC intraday execution.

## 20. Behavioral / institutional explanations proposed

The paper discusses possible reasons trends might persist.

Examples include:

- anchoring;
- herding;
- underreaction / delayed information incorporation;
- trading by non-profit-maximizing participants such as:
  - central banks;
  - corporate hedgers.

These mechanisms are presented as plausible explanations consistent with prior literature.

The article does **not** prove one unique causal mechanism.

### PROJECT CAUTION

A persistent historical return pattern can have several competing explanations.

Trading Bot should not convert a post-hoc narrative into a causal feature without separate evidence.

## 21. What this paper says about simple vs complex trend models

The authors intentionally use a simple model.

Reasons implied by the source:

- reduce arbitrary design choices;
- improve interpretability;
- make century-scale replication possible;
- test the broad phenomenon rather than optimize one implementation.

### RESEARCH DIRECTOR INTERPRETATION

This is important for our future architecture.

A source-grounded signal family should not automatically be represented by dozens of optimized
technical variants.

The information family can be real even if the optimal implementation is uncertain.

This fits the Owner's preference to include professionally meaningful families without creating a
feature zoo.

## 22. Relation to Trading Bot's multi-signal concept

This paper directly supports only a **trend/time-series momentum family**.

It does not define how trend should interact with:

- cycles;
- market structure;
- volume;
- order flow;
- volatility;
- derivatives positioning;
- liquidity;
- risk;
- execution.

However, it gives a useful precedent for combining **multiple horizons of the same information
family**.

### Important distinction

Three horizons are not necessarily three independent pieces of evidence.

They are three representations/scales of the same broad trend phenomenon.

The later architecture should therefore guard against counting:

- EMA trend;
- breakout trend;
- lagged return trend;
- moving-average crossover trend

as four independent confirmations merely because formulas differ.

## 23. Relevance to multi-timeframe architecture

The paper is strong evidence that the trend family itself can benefit from multiple horizons.

The exact horizons in this source are:

- 1 month;
- 3 months;
- 12 months.

Trading Bot's intended horizons are much shorter.

Therefore the transferable idea is:

> **multi-horizon trend representation**

not:

> copy 1m/3m/12m calendar-month parameters into BTC.

Any 15m/1h/4h/daily implementation remains a BTC-specific development question.

## 24. Relevance to risk architecture

The source gives strong precedent for:

- normalizing positions by volatility;
- controlling total portfolio risk;
- avoiding dominance by naturally volatile instruments;
- using an explicit ex-ante volatility target.

For Trading Bot, which initially trades one instrument, the exact portfolio machinery is not directly
transferable.

But the broader principle is:

> signal strength and risk allocation should be separate variables.

A strongly bullish state does not automatically justify unbounded exposure.

## 25. What this source does NOT establish

This paper does **not** establish:

- profitable BTCUSDT trend following;
- profitable intraday trend following;
- a 15m/1h/4h BTC signal;
- an optimal BTC momentum lookback;
- a numeric `peso_base`;
- a numeric `peso2`;
- an entry timing rule;
- stop-loss geometry;
- profit-target geometry;
- crypto order-flow alpha;
- funding/OI alpha;
- cycles;
- a complete Trading Bot algorithm;
- that trend should override other information families;
- that trend should always be traded;
- that volatility itself predicts trend profitability;
- that historical century-scale performance guarantees future persistence.

## 26. Key limitations

### 26.1 Historical instrument reconstruction

For large portions of the early sample, exact modern futures did not exist.

Cash indices plus financing assumptions are used.

### 26.2 Early-data quality

Early commodity prices are manually transcribed.

For some periods there are no official closing prices and high/low averages are used.

### 26.3 Transaction-cost uncertainty

Historical transaction costs are estimated and scaled backward using assumptions.

### 26.4 Omitted costs

The authors note that some costs, such as futures rolling costs, may be absent.

### 26.5 Multi-market vs single-asset target

The historical strategy obtains substantial benefit from diversification across many markets.

Trading Bot initially trades BTCUSDT only.

### 26.6 Frequency mismatch

The analysis is monthly.

Trading Bot's decision horizon is substantially shorter.

### 26.7 Ex-post regime classifications

Some macro labels are not available causally in real time.

### 26.8 Author affiliation

The authors are associated with AQR, an investment manager active in systematic strategies.

This does not invalidate the work, but institutional affiliation should remain part of source
provenance.

## 27. Durable project knowledge retained from LIB-009

The following source-grounded points are strong enough to carry into final synthesis:

1. **Time-series momentum has unusually long cross-market historical evidence.**
2. The source extends the evidence back to **1880** and through **2016**.
3. The study spans **67 markets across four asset classes**.
4. A deliberately simple combination of **1-, 3-, and 12-month own-return directions** performs
   robustly over the historical sample.
5. Direction and risk sizing are separate: the sign creates the position; volatility determines
   exposure.
6. Multiple trend horizons can be combined without treating one horizon as universally optimal.
7. Signal delay materially reduces performance, especially for faster signals.
8. Trend performance is **not uniform through time**; 2010–2016 is much weaker for the shortest
   signal.
9. Trend following historically performs well in many prolonged equity crises but can fail in abrupt
   reversals.
10. The strategy itself can experience deep, multi-year drawdowns.
11. Cross-market trend diversification is important to the historical portfolio result.
12. Trend performance is not simply equivalent to being "long volatility."
13. Lower cross-market correlation is historically associated with better portfolio trend
    performance in this design.
14. Historical regime analysis must distinguish contemporaneous description from variables actually
    known ex ante.
15. Transaction costs materially reduce gross returns.
16. Cost modeling remains imperfect even in this careful paper.
17. A simple, economically interpretable family-level representation can be scientifically more
    defensible than optimizing many indicator variants.
18. None of the long historical evidence directly validates BTCUSDT intraday trend alpha.

## 28. Potential project implications

These are **Research Director interpretations**, not frozen design rules.

### 28.1 Trend should probably be a family, not an indicator

The evidence supports treating trend/time-series momentum as a professional information family.

The family may contain multiple horizons.

### 28.2 Correlated trend transforms should not receive independent votes

A later architecture should explicitly control redundancy among:

- returns over adjacent windows;
- moving-average crossover;
- breakout measures;
- other linear trend filters.

### 28.3 Faster signals require stronger execution discipline

The severe degradation of lagged 1-month versus lagged 12-month trend suggests a general principle:

> the shorter the alpha horizon, the more execution latency can consume the signal.

This becomes even more important for a future BTC intraday system.

### 28.4 Trend state should not equal trade authorization

The paper's own strategy always trades, but Trading Bot does not need to copy that design.

Given:

- costs;
- whipsaw;
- weak short-horizon periods;
- abrupt reversals;

it is entirely consistent for Trading Bot to estimate bullish/bearish trend while still outputting
`NO_TRADE` because other evidence or execution conditions are unfavorable.

That is a project architecture interpretation, not a source claim.

## 29. Questions for Astra at final corpus review

1. How much prior weight should century-scale multi-asset trend evidence receive when the target is
   one crypto asset at intraday horizons?
2. Does the evidence justify trend as a mandatory information family even if isolated BTC
   development performance is weak?
3. Should multiple trend horizons be combined structurally, and if so how do we prevent horizon
   redundancy?
4. Does the equal-weight 1m/3m/12m design provide a useful robustness precedent for avoiding
   backtest-optimized weights?
5. What BTC-specific evidence would be required before mapping the family to 15m/1h/4h/daily
   horizons?
6. Should signal latency sensitivity be an explicit research dimension for every fast signal family?
7. How should Trading Bot distinguish gradual trend regimes from abrupt reversal/crash regimes?
8. Is volatility-normalized trend evidence relevant to single-asset position sizing, or should risk
   architecture remain fully separate from signal construction?
9. Can any single-asset analogue of the paper's cross-market correlation regime be justified, or
   should that result remain portfolio-specific?
10. How much should historical cost uncertainty reduce the evidentiary weight of the 1880–1992
    period?
11. Should a later trend engine prefer a small set of source-grounded horizon representations over
    many technical-indicator variants?
12. How should this paper be grouped with LIB-015, LIB-011 and eventually LIB-008 so that related
    evidence is not counted as four independent confirmations?

## 30. Relation to other corpus items

This source belongs to the same broad research family as:

- `LIB-015 — Time Series Momentum.pdf` — AQR two-page secondary summary;
- `LIB-011 — Time Series Momentum Original Paper Data.xlsx` — original-paper factor dataset;
- `LIB-008 — Which Trend Is Your Friend?` — representation/equivalence of trend filters;
- `LIB-006 / LIB-007` — institutional trend-following research.

These are **not automatically independent evidence units**.

The final synthesis must account for:

- overlapping authors;
- shared methodology;
- shared datasets;
- citation dependence.

## 31. Final source disposition

`REVIEWED`

Reason:

The complete 16-page accessible PDF was reviewed, including:

- full text;
- all strategy-construction details;
- exhibits;
- crisis analysis;
- economic-regime analysis;
- appendices;
- cost assumptions;
- endnotes;
- references;
- page-level visual inspection.

Source claims have been separated from Research Director interpretation.

No BTC-specific alpha, signal weight, parameter, System G2 design or market experiment is authorized
by this dossier.
