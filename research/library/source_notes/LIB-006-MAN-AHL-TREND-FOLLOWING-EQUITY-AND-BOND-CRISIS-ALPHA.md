# LIB-006 — Trend Following: Equity and Bond Crisis Alpha — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `Man_AHL_Insights_Trend_Following__Equity_and_Bond_Crisis_Alpha_English_(United_States)_30-09-2016.pdf`  
Drive file id: `1YAR-alc4baagX9gRBnVrO2dyxFsv8TJo`  
Local corpus id: `LIB-006`

## 1. Source identity

**Title:** *Trend Following: Equity and Bond Crisis Alpha*  
**Authors:** Carl Hamill, Sandy Rattray, Otto van Hemert  
**Organization:** Man AHL  
**Date:** September 2016  
**Length:** 15 PDF pages  
**Artifact type:** institutional practitioner research / white paper  
**Project classification:** INSTITUTIONAL_PRACTITIONER  
**Evidence tier in registry:** B

The paper studies time-series momentum / trend-following across:

- government bonds;
- commodities;
- currencies;
- equity indices;

over a historical sample running primarily from **January 1960 to December 2015**.

The paper is explicitly framed as informational/educational material rather than investment advice.
The authors state that the strategy results shown are simulated and are not intended to represent
actual historical performance of a specific fund or product.

## 2. Research questions

The paper asks three principal questions.

### SOURCE QUESTION 1

Should futures trend-following be expected to remain profitable in an environment where government
bond yields rise?

This is motivated by concern that post-1985 trend-following performance could have been unusually
helped by the long government-bond bull market.

### SOURCE QUESTION 2

Are the crisis-protection characteristics of trend-following confined to equity sell-offs, or can
they also appear during government-bond market stress?

### SOURCE QUESTION 3

Can crisis protection be enhanced by preventing the strategy from holding long equity or long bond
positions?

These questions are evaluated empirically using a deliberately simple momentum framework.

## 3. High-level source conclusions

The paper reports that:

1. momentum/trend-following strategies performed consistently in both:
   - the pre-1985 bond-bear period;
   - the post-1985 bond-bull period;
2. trend-following returns are positively skewed, especially for faster/recent-return momentum;
3. there are similarities between trend-following and a dynamically replicated long-straddle payoff;
4. the studied strategy performs strongly in the worst equity and worst bond environments;
5. performance is also strong in the best equity and bond environments, producing an equity
   “smile” and a pronounced bond “smile”;
6. forbidding long equity or bond positions improves protection in the corresponding crisis
   environment but reduces average performance;
7. those restrictions also produce unfavorable cross-market effects;
8. the authors reject the claim that historical trend-following success can be explained only by
   the post-1985 fixed-income rally;
9. the authors also reject the view that trend following only protects during equity sell-offs.

These are source claims from this paper, not BTC-specific conclusions.

## 4. Data construction

### 4.1 Historical span

Strategy evaluation begins in **1960**.

The authors explain that earlier starting dates create data-quality problems, particularly in
commodities:

- missing futures contracts;
- intermittent data;
- use of spot returns that would omit roll yield.

The 1960 start also captures the severe historical bond-market drawdown associated with the long rise
in U.S. 10-year yields from below 5% in 1960 to nearly 16% in the early 1980s.

### 4.2 Warm-up

Although evaluation begins in 1960, some data begin as early as **1950** to provide a warm-up period
for:

- volatility estimates;
- correlation/risk estimates.

For securities whose data begin after 1960, the paper uses a **one-year warm-up period** before
including them in strategy returns.

### 4.3 Asset-specific history

#### Commodities

Agricultural futures and some metals are available back into the 1960s.

Oil futures generally appear only later, primarily in the 1980s.

#### Currencies

Currency data begin in **1973**.

The authors regard the Bretton Woods fixed-exchange-rate period as unsuitable for the intended
currency trend analysis.

For early years they use spot exchange rates adjusted for short-rate differentials to obtain
futures-comparable returns.

#### Equities and bonds

Monthly cash index/bond data are extended backward using Global Financial Data.

The local short rate is deducted to make cash returns comparable to returns on unfunded instruments
such as futures.

Because long equity/bond histories are available only monthly, the entire analysis is performed at
**monthly frequency**.

### 4.4 Cash-to-futures transition

As a general rule, the authors use:

- cash series historically;
- futures or forwards once those instruments become available.

### 4.5 Regulated / artificially low-volatility securities

The paper screens for periods where market regulation caused unusually suppressed volatility.

A security is flagged if its rolling 12-month volatility estimate drops to approximately 5% of its
average 12-month volatility.

Examples of delayed inclusion include:

- silver before 1972;
- Japanese 10-year bonds before 1972;
- Australian 10-year bonds before 1977.

This is intended to avoid treating administratively constrained prices as normal tradable market
behavior.

## 5. Asset universe

Table 1 contains a diversified cross-asset universe including:

### Bonds

Government bonds from several developed countries and multiple U.S. Treasury maturities.

### Commodities

Agricultural commodities, energy contracts and metals.

### Currencies

Major developed-market currency pairs versus USD.

### Equities

Major developed-country equity indices.

The precise universe is historical and changes with instrument availability.

### PROJECT INTERPRETATION

The strength of this paper is partly cross-sectional diversification across many instruments and
asset classes.

Trading Bot's initial BTC-only mission therefore cannot inherit the portfolio-level properties of
this research automatically.

## 6. Momentum signal definition

The paper defines a deliberately straightforward momentum signal for security `k` at time
`t-1`.

Conceptually:

`signal = weighted sum of lagged monthly returns / volatility / norm of lag weights`

More specifically, lagged returns receive weights:

`w1, w2, ...`

and the weighted return history is divided by:

- an ex-ante volatility estimate;
- the Euclidean norm of the lag-weight vector.

The lag weights are assumed to be the same across securities.

The normalization is designed so that different weight profiles produce approximately comparable
signal volatility.

### 6.1 Signal meaning

The signal value represents the number of risk units the strategy would like to hold in the asset.

To turn that signal into a position, the strategy divides by volatility a second time so that assets
with different raw volatility contribute comparable risk for a given signal strength.

This is an important structural distinction:

- return history determines direction/strength;
- volatility determines risk-normalized position exposure.

## 7. Volatility estimation

The security volatility estimate uses exponentially decaying observations.

The paper applies a floor-like robustness rule by taking the maximum of:

- a relatively fast estimate based on approximately a 6-month half-life;
- 0.5 times a slower estimate based on approximately a 24-month half-life.

The intent is to prevent temporarily very low observed volatility from creating excessive risk
exposure.

### RESEARCH DIRECTOR INTERPRETATION

This is a professional example of **risk normalization being separate from directional evidence**.

It also illustrates that a volatility estimate can need defensive constraints because mechanically
dividing by a temporarily low volatility number can create dangerous leverage.

No analogous BTC parameter is authorized from this paper.

## 8. Portfolio risk construction

The resulting portfolio is geared to approximately:

**10% ex-ante annualized volatility**

on average.

Risk is allocated approximately equally across four broad asset classes:

- bonds;
- commodities;
- currencies;
- equities.

Within equities, bonds and currencies, constituent securities are equal-weighted.

Within commodities, equal weighting is first applied across broad commodity subsectors and then
across constituents within each subsector.

If an instrument is unavailable in an early period, its risk allocation is redistributed among the
available securities in the same class.

The risk aggregation uses a correlation matrix estimated from constituent strategy returns with
exponentially decaying weights and an approximately **24-month half-life**.

### PROJECT LIMITATION

These portfolio-allocation rules are important to the paper's historical return properties.

They cannot be transferred directly to a single-instrument BTC system.

## 9. Return convention and costs

The paper primarily uses unfunded returns:

- futures;
- forwards;
- cash instruments financed at local short rates.

Reported strategy returns should therefore be interpreted as **excess returns**.

The authors do **not** include interest income in the plotted strategy results.

### Transaction costs

Main reported results are **gross of transaction costs and fees**.

The authors argue that costs would reduce profitability but would have less impact on the qualitative
dynamics that are the main focus.

They provide an illustrative estimate:

assuming approximately **2 basis points per outright trade**, annualized return for their main
`momCTA` strategy would be reduced by about **0.42 percentage points**.

This is an estimate tied to their strategy and historical trading assumptions.

It is not a cost assumption for BTC.

## 10. Lag-by-lag momentum evidence

The paper first studies strategies based on individual monthly return lags.

For each lag from 1 to 24 months, a strategy uses that lag alone as its momentum input.

### SOURCE RESULT

Returns from lags approximately **1 through 11 months** are reported as positively predictive of the
following month's return.

Lag 12 is much less predictive in the monthly-data experiment.

Lags beyond roughly one year become weak or negative.

### Monthly-data timing issue

The authors argue that monthly sampling mechanically makes the nominal 12-month lag older on average
than exactly 12 months.

For example, a signal fixed for an entire calendar month may effectively use information that becomes
12.5 months old mid-month and 13 months old by month-end.

They report unshown daily-data analysis suggesting the 12-month effect is stronger when the lag is
measured more precisely.

### U-shaped lag profile

Within lags 1–11, annualized momentum returns display a pronounced **U-shape**:

- strong for the most recent lags;
- weaker in the middle;
- stronger again around lags 9–11.

The authors do not offer one definitive economic explanation for the later-lag upturn.

They mention possibilities including:

- annual seasonality;
- reporting/evaluation practices;
- under-reaction.

## 11. Construction of the `momCTA` proxy

The authors attempt to create a simple momentum strategy whose returns resemble the representative
BTOP50 managed-futures index.

BTOP50 return history is available from **January 1987**.

### Fitting constraints

To reduce degrees of freedom, the authors:

- force lag weights to follow a **quadratic function** of lag;
- set weights for lag 12 and beyond to zero.

Subject to those restrictions, they choose the quadratic weights that maximize correlation with
BTOP50 excess returns.

This fitted strategy is called:

`momCTA`

### SOURCE RESULT

The monthly correlation between `momCTA` returns and BTOP50 excess returns over the available
29-year history is reported as:

**0.62**

The authors regard this as reasonably high given:

- their signal/risk calculations use monthly data;
- real managed-futures managers likely use higher-frequency/daily information.

### Weight concentration

Approximately **76% of the fitted quadratic weight** is assigned to the first four return lags.

Thus the fitted proxy is primarily a **faster/recent-return trend strategy**, even though the raw
lag-performance experiment also showed strong predictability around lags 9–11.

### RESEARCH DIRECTOR QUALIFICATION

The exact `momCTA` weight profile is **calibrated** using BTOP50 returns from the period available
from 1987 onward.

It therefore should not be interpreted as a completely independent test of that specific fitted
weighting function.

The paper tries to limit overfitting through a simple quadratic functional form and zero weights after
lag 11, but the fitting step remains a data-informed calibration.

This does not invalidate the descriptive exercise; it changes what evidentiary claim can be made from
it.

## 12. Four strategy variants

The paper compares four momentum strategies.

### `mom(1,4)`

Equal weight on returns from the most recent four months:

`w1 = w2 = w3 = w4 = 1/4`

All other lag weights are zero.

### `mom(5,8)`

Equal weight on returns from months 5 through 8:

`w5 = w6 = w7 = w8 = 1/4`

### `mom(9,11)`

Equal weight on returns from months 9 through 11:

`w9 = w10 = w11 = 1/3`

### `momCTA`

Quadratically constrained fitted weights on the first 11 lags, calibrated to resemble BTOP50.

## 13. Historical performance

### SOURCE RESULT — consistency

The paper reports that:

- `momCTA`;
- `mom(1,4)`;

perform quite consistently over the full 1960–2015 period.

`mom(9,11)` also performs consistently and, from the mid-1970s onward, approximately as well as
`mom(1,4)` in cumulative-return slope.

`mom(5,8)` is materially weaker.

### Relationship between `momCTA` and `mom(1,4)`

Monthly returns of the two strategies have reported correlation of approximately:

**0.92**

Other strategy-pair correlations are substantially lower, roughly **0.20–0.40**.

### Sharpe ratios

Table 2 reports annualized Sharpe ratios calculated from annualized excess return divided by
annualized volatility.

These are gross of transaction costs and fees.

| Strategy | All | Bonds | Commodities | FX | Equities |
|---|---:|---:|---:|---:|---:|
| momCTA | 1.56 | 1.18 | 1.07 | 0.57 | 0.64 |
| mom(1,4) | 1.30 | 0.99 | 0.87 | 0.48 | 0.55 |
| mom(5,8) | 0.64 | 0.32 | 0.56 | 0.19 | 0.34 |
| mom(9,11) | 1.12 | 0.54 | 0.91 | 0.52 | 0.51 |

### IMPORTANT LIMITATION

These are historical simulated cross-asset strategy results.

They are not:

- BTC Sharpe ratios;
- live realized fund returns;
- net-of-cost returns;
- evidence that an intraday BTC trend signal will achieve similar performance.

## 14. Pre-1985 versus post-1985 result

One of the paper's core motivations is the hypothesis that post-1985 trend-following success may have
been driven by the multi-decade bond bull market.

The authors report that trend strategies performed well both:

- before 1985, when bond excess returns were weak/negative on average;
- after 1985, during the long bond bull market.

### SOURCE CONCLUSION

The paper therefore argues against explaining trend-following's historical performance solely by the
post-1985 fixed-income rally.

### PROJECT INTERPRETATION

This is useful evidence about historical robustness across very different bond regimes.

It remains cross-asset monthly evidence and does not imply regime invariance for BTC.

## 15. Skewness

The authors argue that average return and volatility are insufficient to describe the strategy's
risk profile.

They focus on skewness, especially over multi-month evaluation windows.

### SOURCE RESULT

`momCTA` and `mom(1,4)` exhibit substantial **positive skewness**, particularly for 3-month and
12-month overlapping returns.

The slower/intermediate strategies show much smaller or sometimes negative skewness.

### Table 3 — 3-month overlapping-return annualized skewness

| Strategy | All | Bonds | Commodities | FX | Equities |
|---|---:|---:|---:|---:|---:|
| momCTA | 1.04 | 0.71 | 1.21 | 1.40 | 0.96 |
| mom(1,4) | 1.13 | 0.53 | 1.08 | 1.59 | 0.81 |
| mom(5,8) | -0.06 | -0.41 | 0.01 | 0.51 | -0.24 |
| mom(9,11) | 0.16 | 0.38 | 0.41 | 0.17 | 0.11 |

### Table 3 — 12-month overlapping-return annualized skewness

| Strategy | All | Bonds | Commodities | FX | Equities |
|---|---:|---:|---:|---:|---:|
| momCTA | 1.48 | 0.08 | 0.97 | 1.86 | 0.89 |
| mom(1,4) | 1.80 | 0.24 | 0.95 | 2.38 | 0.88 |
| mom(5,8) | -0.07 | -0.70 | -0.13 | 0.86 | 0.26 |
| mom(9,11) | -0.07 | 0.23 | -0.16 | 0.24 | -0.05 |

## 16. Skewness robustness checks

The paper tests the skewness conclusion several ways:

1. pre-1985 and post-1985 periods separately;
2. excluding 2008, a year with unusually strong positive trend-following performance;
3. alternative Bowley and Pearson skewness measures.

The authors report that the broad conclusion remains similar:

`momCTA` and `mom(1,4)` display substantial positive skewness over multi-month evaluation
windows.

## 17. Trend following and the long-straddle analogy

The paper argues that the payoff behavior of faster trend following resembles aspects of a
**long-straddle** strategy.

Intuition:

- when the underlying remains range-bound, small losses may occur repeatedly;
- when the underlying moves strongly in either direction, the strategy can make large gains.

The authors connect this to trend-following behavior:

- adding to winning positions;
- reducing losing positions;
- gradually varying exposure as the signal strengthens/weakens.

They compare the trend response function with the delta of a straddle.

### IMPORTANT QUALIFICATION

The paper explicitly says the analogy is weaker for a **binary** trend follower that only switches
between fixed long / fixed short / flat states.

The straddle-like relationship is more natural when position size changes continuously with signal
strength.

### PROJECT RELEVANCE

This is directly relevant to the conceptual distinction between:

- a continuous directional/strength estimate;
- a discrete LONG / SHORT / NO_TRADE action.

A continuous internal forecast can coexist with a selective discrete trade policy.

That is a Research Director interpretation of the source, not a frozen Trading Bot rule.

## 18. Crisis alpha

The paper evaluates `momCTA` during different equity and bond market environments.

It forms quintiles based on rolling **3-month** returns of:

- S&P 500 for equity conditions;
- U.S. 10-year Treasury for bond conditions.

The authors use a multi-month window because large institutional portfolios may require time to
reposition in changing environments.

### SOURCE RESULT — equity smile

Trend-following performance is strong in:

- the worst equity-return quintile;
- the best equity-return quintile.

This is described as the familiar **equity smile**.

### SOURCE RESULT — bond smile

The same broad pattern appears across bond-market return quintiles and is described as an even more
pronounced **bond smile**.

### Source attribution by asset class

The paper reports that:

- equities;
- bonds;
- currencies;

show both equity and bond smile behavior.

Commodities display more left-skewed crisis behavior, with especially strong performance in the
worst equity/bond periods.

### SOURCE CONCLUSION

The authors interpret this as evidence that trend following has the potential to provide both:

- equity crisis alpha;
- bond crisis alpha.

## 19. Crisis-alpha sensitivity tests

The paper reports several checks.

### 19.1 12-month evaluation windows

With rolling 12-month equity-market evaluation:

- the equity smile becomes more strongly left-skewed;
- `momCTA` does best in the worst equity quintile and worst in the best equity quintile.

The bond smile becomes flatter, but performance remains strong in the worst bond quintile.

### 19.2 Post-1974 sample

Starting in 1974, when currency data are available, both equity and bond smile behavior remains.

### 19.3 Alternative lag families

The crisis-alpha pattern is clearest for:

`mom(1,4)`

and materially less clear for:

- `mom(5,8)`;
- `mom(9,11)`.

This aligns with the faster strategy's stronger positive skewness.

## 20. Long-position restrictions

The authors ask whether crisis protection can be strengthened by forbidding long exposure.

They test variants where:

- equity position is capped at zero;
- bond position is capped at zero.

The restricted strategy is rescaled ex post to match the baseline strategy's volatility for easier
comparison.

### SOURCE RESULT

Preventing long equity exposure improves performance in the worst equity quintile.

Preventing long bond exposure improves performance in the worst bond quintile.

However, the restriction:

- lowers performance in several normal/strong-market quintiles;
- lowers average return.

The authors characterize this as the price of enhanced crisis protection.

### Cross-market cost

A no-long-bond restriction worsens returns across equity quintiles.

A no-long-equity restriction worsens returns across bond quintiles.

The paper highlights the particularly undesirable deterioration in the opposite market's worst
quintile.

### Source explanation

The authors note that although equity/bond correlation is often positive under common fundamentals,
during severe equity uncertainty it can turn strongly negative because of flight-to-safety behavior.

Therefore hard crisis-protection restrictions in one asset class can remove positions that would have
helped hedge another crisis.

### PROJECT INTERPRETATION

This is a strong example of why a **hard veto** can have unintended cross-effects.

A rule that seems locally sensible for one risk objective may degrade the full-system behavior.

No direct BTC rule is derived from this observation.

## 21. Persistence / future profitability discussion

The paper explicitly acknowledges that 56 years of historical evidence do not guarantee future
profitability.

The authors note:

- momentum research predates their paper by decades;
- observed performance persisted after early academic publication;
- meaningful capital is dedicated to momentum;
- some large institutional participants may structurally trade against momentum-like characteristics.

They suggest that this may mitigate, but does not eliminate, concerns about crowding/edge decay.

### LIMITATION

This is an argument about potential persistence, not proof of future persistence.

## 22. Deliberately barebones design

One of the most important statements for the current project appears in the conclusion.

The authors emphasize that their momentum strategy is intentionally **barebones**.

Their reason is methodological:

adding many implementation details would make it harder to know whether the documented risk/return
characteristics are general trend-following effects or artifacts of one elaborate formulation.

They explicitly state that real live futures momentum requires additional work in:

- signal-definition fine-tuning;
- portfolio construction;
- risk management;
- execution.

### RESEARCH DIRECTOR INTERPRETATION

This directly supports keeping two questions separate:

1. **Does a broad information phenomenon exist?**
2. **How should a complete professional trading system use it?**

A simple research strategy can be appropriate for causal understanding even when it is insufficient
as a production trading algorithm.

That is highly relevant to the Owner's objection to treating each signal family as a standalone final
strategy.

## 23. What the paper contributes to the future Trading Bot knowledge map

This section records potential relevance only; no architecture is frozen yet.

### 23.1 Trend / time-series momentum is a directional-information family

The source provides substantial historical practitioner evidence that own-history return direction can
contain economically useful information across traditional futures markets.

### 23.2 Signal strength can be continuous

The strategy's position changes with normalized signal magnitude.

This is conceptually compatible with:

- direction;
- strength;
- conviction;

being separate from the final trade action.

### 23.3 Volatility belongs to risk normalization, not necessarily direction

The paper uses volatility to scale signal/position risk rather than as the primary directional vote.

This is a useful professional role distinction.

### 23.4 Faster and slower trend information are not interchangeable

The paper finds materially different:

- average performance;
- skewness;
- crisis behavior;

for different return-lag groups.

Therefore “trend” should not automatically be represented by one undifferentiated indicator.

At the same time, multiple correlated trend transforms should not be blindly counted as independent
votes.

### 23.5 Crisis behavior is conditional

Trend-following's value is not summarized by unconditional Sharpe alone.

The paper specifically studies behavior during:

- large equity declines;
- large bond declines.

This supports later evaluation of signal families by **conditional role**, not merely standalone mean
return.

### 23.6 Hard constraints can improve one objective while harming another

The no-long experiments demonstrate a clear trade-off between:

- stronger targeted crisis protection;
- lower unconditional returns;
- worse protection against another market shock.

This is relevant to future veto/risk-rule design.

## 24. What this source does NOT support

The paper does **not** establish:

- profitable BTCUSDT trend following;
- any 15m/1h/4h BTC momentum horizon;
- any BTC lookback;
- any numeric Trading Bot trend weight;
- that `momCTA` is optimal;
- that the fitted BTOP50 weights should be copied;
- that 10% portfolio volatility is appropriate for Trading Bot;
- that a 2 bp cost assumption applies to crypto;
- that trend should override market structure, cycles, volume or derivatives context;
- that trend-following crisis alpha applies identically to a single crypto asset;
- that positive skewness guarantees profitability;
- that the paper's cross-asset diversification can be reproduced in BTC-only trading;
- that restricting LONG/SHORT BTC exposure will improve crisis behavior.

## 25. Major source limitations

### 25.1 Cross-asset portfolio versus single-asset target

The results depend on a broad multi-market portfolio.

Trading Bot initially trades one asset.

### 25.2 Monthly frequency

The historical extension forces the analysis to monthly data.

The Owner's intended decision horizons are dramatically shorter.

### 25.3 Gross performance

Core tables/figures are gross of transaction costs and fees.

### 25.4 Historical proxies

Earlier history mixes:

- cash series;
- futures;
- forwards;
- interest-rate adjustments.

This is reasonable for the research question but introduces construction assumptions.

### 25.5 `momCTA` calibration

The BTOP50-like weighting function is fitted on 1987–2015 BTOP50 history.

The resulting proxy is descriptive/calibrated, not a pristine independently specified strategy.

### 25.6 Simulated strategy

The paper states that performance is simulated and not actual fund/product performance.

### 25.7 Institutional practitioner source

This is useful professional research but should not automatically receive the same evidentiary status
as an independently replicated peer-reviewed result.

## 26. Contradictions / tensions to preserve for final synthesis

### T-006-01 — Simple research model versus production strategy

The source deliberately uses a simple model to isolate general trend properties while simultaneously
acknowledging that live trading needs substantially more sophistication.

Do not mistake simplicity in a research experiment for a recommendation that a professional trading
system should contain only one signal.

### T-006-02 — Recent lags versus older lags

Raw historical lag analysis reports strong performance at both:

- recent lags;
- lags 9–11.

Yet the BTOP50-replicating fitted strategy concentrates 76% of weight in the first four months.

This may reflect:

- different practical risk properties;
- industry preference;
- calibration target;
- implementation considerations.

The paper does not fully resolve the discrepancy.

### T-006-03 — Crisis protection versus unconditional performance

Hard restrictions can improve a targeted crisis state while reducing:

- average return;
- performance in normal/bull markets;
- protection in a different crisis.

This trade-off must remain explicit.

## 27. Questions for Astra at final corpus review

1. How much weight should this institutional source receive relative to peer-reviewed TSMOM evidence?
2. Which parts of the result depend materially on **cross-asset diversification** and therefore do not
   transfer to BTC-only trading?
3. Is the source's separation of continuous signal magnitude and risk-normalized position a useful
   blueprint for distinguishing prediction/strength from trade action?
4. How should we treat the BTOP50-calibrated `momCTA` weights scientifically given that they were
   fit to the return series they are intended to mimic?
5. Does the strong difference between `mom(1,4)`, `mom(5,8)` and `mom(9,11)` argue for multiple
   trend horizons or merely for a better continuous trend representation?
6. How can conditional crisis behavior be studied in BTC without post-hoc regime definitions?
7. Does the long-straddle analogy meaningfully inform actionability/risk design, or is it mostly a
   descriptive return-shape analogy?
8. Should volatility be treated primarily as risk normalization/context rather than directional
   evidence in the future architecture?
9. What BTC-specific evidence would be required before any monthly cross-asset trend result informs
   15m–4h trading?
10. How should the future system avoid turning plausible professional refinements into a large
    overfit parameter space?
11. Does the paper's deliberate barebones research design strengthen the case for testing **families
    within a complete system** rather than demanding that every family be a standalone production
    strategy?
12. Which of the paper's risk controls are structural professional practices and which are
    portfolio-specific choices?

## 28. Durable source-derived knowledge retained

The following source-derived points should survive into final cross-source synthesis:

1. Trend-following historical performance in this study spans both pre-1985 bond-bear and post-1985
   bond-bull environments.
2. The research uses a diversified universe of bonds, commodities, currencies and equity indices.
3. Signal direction/strength is generated from weighted lagged returns and normalized by volatility.
4. Position risk is normalized separately, and total portfolio risk is targeted.
5. The source uses a defensive volatility floor mechanism to avoid excessive scaling during
   abnormally low volatility.
6. Return lags 1–11 are reported as positively predictive in the monthly experiment, with a
   U-shaped performance profile.
7. A BTOP50-like proxy fitted under a constrained quadratic weighting function places approximately
   76% of its lag weight on the first four months.
8. `momCTA` and `mom(1,4)` are highly correlated and display stronger positive skewness than the
   intermediate-lag strategy.
9. Faster trend strategies display the clearest equity/bond crisis-alpha pattern in the study.
10. The paper finds both equity and bond “smiles”.
11. Hard no-long restrictions strengthen targeted crisis protection but reduce average performance
    and create adverse cross-market effects.
12. Trend-following's positive-skew payoff is compared with a dynamically replicated long straddle.
13. The straddle analogy is weaker for binary fixed-size long/short/flat systems.
14. The authors deliberately keep the research strategy barebones to isolate broad trend effects.
15. The authors explicitly state that live momentum requires additional work on signal definition,
    portfolio construction, risk management and execution.
16. Core results are gross of transaction costs/fees and are simulated.
17. None of the paper's numerical horizons or weights are directly validated for BTC.

## 29. Final source disposition

`REVIEWED`

Reason:

The complete accessible 15-page PDF was reviewed, including:

- cover/overview;
- introduction;
- data section;
- Table 1 universe/data construction;
- momentum equations and footnotes;
- lag-performance analysis;
- BTOP50 fitting;
- cumulative performance;
- Sharpe table;
- skewness analysis and robustness checks;
- straddle analogy;
- crisis-alpha analysis;
- long-position restrictions and cross-effects;
- conclusion;
- references;
- appendix sensitivity analyses;
- legal/source qualifications.

All source claims were kept separate from Research Director interpretation.

No outside source was used to fill gaps.

No Trading Bot strategy, signal weight, parameter, System G2 design or market experiment is
authorized by this dossier.
