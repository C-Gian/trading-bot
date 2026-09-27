# LIB-002 — Expected Returns: An Investor’s Guide to Harvesting Market Rewards — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `Expected returns.pdf`  
Drive file id: `1A5wxjxXAKnX7weeU0SUFkq5f7GbA8wJx`  
Local corpus id: `LIB-002`  
Author: **Antti Ilmanen**  
Publisher: **John Wiley & Sons Ltd**  
First published: **2011**  
PDF pages: **594**  
SHA-256: `c6f54a3e52059f6bdc0000d127690b674aee0dd2ee04922e8f28e29adab1d1df`

## 1. Source identity and scope

*Expected Returns: An Investor’s Guide to Harvesting Market Rewards* is a professional synthesis of
historical evidence, asset-pricing theory, behavioral finance, forward-looking indicators, strategy
styles, risk factors, tactical forecasting, regime/cycle analysis, portfolio construction and
implementation considerations.

The book's organizing problem is not simply:

> Which asset has historically performed best?

It asks how investors should form **forward-looking expected-return judgments** using several
different kinds of evidence while recognizing that expected returns are unobservable, time-varying
and estimated with substantial uncertainty.

The source is a book-level synthesis, not one single controlled empirical paper.

Project registry classification:

`BOOK_TEXTBOOK / EVIDENCE TIER C`

This tier does not mean the content is unimportant. It means individual empirical claims often
summarize a wider literature or the author's own historical analysis and therefore require their
underlying primary sources before being treated as Tier-A empirical evidence.

## 2. Study coverage

The complete accessible 594-page PDF was reviewed.

Coverage included:

- front matter and stated scope;
- all 29 chapters;
- all three major book parts;
- figures/tables through full-volume visual inspection;
- Appendix A;
- Appendix B on data sources and data-series construction;
- bibliography and index;
- deeper reading of the sections most relevant to Trading Bot:
  - return predictability and data-mining caveats;
  - value;
  - currency carry;
  - commodity momentum / trend following;
  - volatility selling;
  - growth, inflation, liquidity and tail-risk factors;
  - feedback loops / endogenous risk;
  - forward-looking expected-return indicators;
  - interpretation of carry;
  - tactical forecasting;
  - seasonality;
  - business cycles and regimes;
  - secular trends;
  - risk, horizon, skill and costs;
  - final investment takeaways.

The source was not supplemented with outside material during this study.

## 3. The book's core framework

### SOURCE CLAIM — expected-return estimation needs multiple perspectives

Ilmanen repeatedly argues that expected returns cannot be inferred reliably from one backward-looking
number.

He organizes expected-return judgments around several perspectives:

1. **historical performance**;
2. **financial / economic theory**;
3. **behavioral explanations**;
4. **forward-looking indicators**;
5. discretionary or view-based expectations where appropriate.

Historical averages are informative but sample-dependent and often poor estimates of current expected
returns when:

- valuations have changed;
- risk premia vary over time;
- structural conditions change;
- the sample contains unusual tailwinds/headwinds.

### SOURCE CLAIM — expected returns are time-varying and unobservable

Realized returns and expected returns must be kept separate.

A strong realized return may reflect:

- a previously high expected return;
- an unexpected favorable shock;
- valuation repricing;
- luck.

A poor realized return can similarly occur even when the ex ante expected return was reasonable.

Because expected returns are not directly observable, empirical interpretation always contains
uncertainty.

### SOURCE CLAIM — there are several useful axes of diversification

A central visual/conceptual framework in the book separates:

- **asset classes**;
- **strategy styles**;
- **underlying risk factors**.

Important strategy styles discussed include:

- value;
- carry;
- momentum / trend;
- volatility selling.

Important underlying factors include:

- growth;
- inflation;
- liquidity;
- tail risk / higher-moment risks.

The source argues that diversification across **styles or underlying risk factors** can sometimes be
more meaningful than nominal diversification across asset classes.

## 4. Methodological lessons

### 4.1 Historical averages are noisy

The source repeatedly warns that even multi-decade samples can be misleading.

Problems include:

- unusually favorable or unfavorable starting/ending valuations;
- structural changes;
- time-varying risk premia;
- rare disasters absent from the sample;
- survivorship / selection issues;
- data mining.

A 20-year history is not automatically a large sample for slow-moving financial phenomena.

### 4.2 Predictive relationships can be economically useful even when correlations are small

Ilmanen emphasizes that financial return prediction is intrinsically noisy.

A predictor does not need an enormous correlation with next-period returns to have practical value,
especially when:

- the signal is repeatedly observed;
- implementation is diversified;
- transaction costs are low enough;
- the signal complements other information.

This does **not** mean weak correlations should be accepted uncritically.

### 4.3 Data mining is a real alternative explanation

Chapter 7 explicitly treats apparent return predictability as potentially arising from:

- genuine risk premia;
- market inefficiency;
- data mining / statistical mirage.

Economic rationale helps constrain research but does not eliminate data-mining risk.

### 4.4 Ex ante and ex post analysis must be separated

The book repeatedly distinguishes information available **before** the return from explanations
constructed afterward.

This is especially important in:

- business-cycle analysis;
- regime analysis;
- macroeconomic variables;
- valuation timing.

Contemporaneous relationships between returns and realized macro conditions are not automatically
tradable because the macro state may only become clear after:

- release delays;
- revisions;
- hindsight classification.

### 4.5 Structural change matters

Historical relations can fail when:

- institutions change;
- regulations change;
- participation/crowding changes;
- investor behavior changes;
- long-run secular forces change.

The book does not endorse blindly assuming either:

- permanent stationarity; or
- "this time is different."

Both require evidence.

## 5. Rational and behavioral explanations

### Rational side

Ilmanen reviews the evolution from simple CAPM-style thinking toward richer asset-pricing models.

A key message is that **when losses occur** can matter more than unconditional volatility.

Assets/strategies that lose particularly badly when:

- economic conditions deteriorate;
- funding becomes scarce;
- marginal utility is high;
- liquidity vanishes

may deserve large expected risk premia.

This motivates attention to:

- covariance with bad times;
- liquidity risk;
- tail risk;
- correlation risk;
- funding conditions.

### Behavioral side

The book reviews mechanisms including:

- extrapolation;
- underreaction;
- conservatism;
- overconfidence;
- representativeness;
- disposition effects;
- attention constraints;
- social interaction / herding.

Behavioral forces can coexist with limits to arbitrage, allowing mispricing to persist.

### SOURCE LIMIT

The book frequently presents rational and behavioral explanations as competing or complementary
interpretations.

Historical return predictability alone often cannot identify which explanation is correct.

That uncertainty must be preserved.

## 6. Value

### SOURCE CLAIM

Value strategies buy relatively cheap assets/securities and sell relatively expensive ones using
some defensible valuation measure.

The book reviews broad historical evidence of value outperformance across:

- equities;
- asset allocation;
- multiple markets.

### Behavioral interpretation

A central explanation discussed is excessive extrapolation:

investors may project recent superior growth too far into the future, causing growth assets to become
too expensive relative to their subsequently realized growth.

### Value traps

Cheapness is not sufficient.

Some distressed securities are cheap for genuine reasons and can continue to deteriorate.

The source discusses filters such as:

- quality;
- profitability;
- momentum

as possible ways of reducing exposure to value traps.

### Value and momentum interaction

The book repeatedly treats value and momentum as natural opposites / complements.

Value can become cheaper for a long time before reversing.

Momentum can therefore serve as information about whether a value opportunity is:

- still deteriorating;
- stabilizing;
- beginning to reverse.

The source argues qualitatively for combining these perspectives rather than demanding that one
always dominate.

### PROJECT INTERPRETATION

This supports the later idea that **signal disagreement can itself be informative**.

It does not establish a BTC-specific value signal.

Traditional fundamental value has no obvious direct one-to-one definition for a single BTC spot
instrument in this source.

## 7. Carry

### SOURCE CLAIM — carry has historically been rewarded

The currency-carry case study reports that buying high-yielding currencies and shorting low-yielding
currencies was historically profitable over long samples.

Related forms of yield/carry seeking appear in multiple markets.

### SOURCE CLAIM — carry is not free alpha

The source repeatedly associates carry with:

- negative skew;
- crowding;
- deleveraging;
- liquidity stress;
- concentrated losses in bad times.

Carry can resemble **selling insurance**:

many modest gains can be interrupted by rare severe losses.

### Cross-style relationship

Momentum/trend strategies are described as useful complements because their returns can be lowly or
negatively correlated with carry/value returns.

### SOURCE CLAIM — carry measures can contain two kinds of information

A yield spread can reflect:

1. market expectations about future price/rate changes;
2. a required risk premium.

Chapter 22 examines this distinction across markets.

The empirical evidence reviewed by Ilmanen generally finds that carry measures predict near-term
returns more strongly than subsequent offsetting price/rate changes, but the source cautions that
biased investor expectations may also explain part of the result.

### PROJECT LIMIT

Nothing in this chapter establishes that crypto perpetual funding is equivalent to the macro/asset
carry concepts studied here.

Any such mapping requires crypto-specific evidence.

## 8. Momentum and trend following

Chapter 14 is one of the most relevant source sections for Trading Bot.

### SOURCE CLAIM — several markets show intermediate-horizon momentum

The book reviews evidence that returns often display positive continuation at intermediate horizons.

It distinguishes:

- **cross-sectional momentum** — recent relative winners versus losers;
- **time-series / trend following** — an instrument's own recent direction.

### Signal representations discussed

Examples include:

- past returns;
- moving-average rules;
- breakout-style rules;
- consistency of prior movement;
- multiple lookback horizons.

The book does not claim one representation is universally optimal.

### Horizon dependence

The reviewed literature generally places useful continuation at intermediate horizons, while:

- very short horizons can show reversal/microstructure effects;
- very long horizons can show reversal.

The exact historical "best" horizon is unstable and only known with hindsight.

This is a strong warning against blindly optimizing a lookback.

### Trend performs differently across market environments

The source describes trend-following as working best when price moves are:

- sustained;
- directional;
- sufficiently persistent.

It struggles when markets are:

- range-bound;
- rapidly reversing.

Macro trend reversals can be particularly painful.

### Diversification role

Trend/momentum is described as having historically valuable diversification characteristics,
including performance in several major equity-market stress episodes.

Ilmanen characterizes trend exposure as having option-like / convex characteristics in some
environments, while stressing that it is not literally the same as owning volatility.

### Potential explanations

Behavioral explanations include:

- underreaction;
- gradual information diffusion;
- later overreaction.

Some markets, especially commodities, can also admit more direct economic mechanisms involving:

- inventories;
- supply/demand;
- futures curves.

### Costs

Momentum strategies often have higher turnover.

Their apparent gross profitability must therefore be evaluated after realistic trading costs.

### PROJECT INTERPRETATION

This source strongly supports **trend/momentum as a professional information family**.

It does not support copying its monthly multi-asset lookbacks into BTC intraday trading.

## 9. Volatility selling

### SOURCE CLAIM

Equity-index volatility selling historically earned attractive average returns because implied
volatility often exceeded subsequent realized volatility.

However, its high historical Sharpe ratio can be misleading.

### Tail-risk character

The strategy resembles selling insurance:

- frequent gains;
- rare but very large losses;
- losses concentrated in severe market stress.

A sample that omits the rare catastrophe can dramatically overstate attractiveness.

### Higher moments matter

The chapter stresses that investment evaluation should look beyond variance toward:

- skewness;
- correlation;
- jumps;
- tail exposure.

### Correlation risk

The gap between index and single-stock volatility pricing suggests that part of the compensation may
be a **correlation risk premium**, not merely "volatility" compensation.

### PROJECT INTERPRETATION

This is important to our future risk architecture:

a signal/strategy with a high average payoff can be undesirable if its losses coincide with states
where the rest of the system is already stressed.

No options/volatility-selling strategy is authorized for the BTC product.

## 10. Growth and inflation factors

The source studies how assets respond to:

- economic growth;
- inflation;
- surprises in those variables.

A key distinction is between:

- exposure to realized macro outcomes;
- expected exposure available ex ante.

Assets can look attractive under average conditions yet fail during particular growth/inflation
regimes.

### PROJECT INTERPRETATION

The useful concept is **regime/context sensitivity**, not importing a macro trading model.

For short-horizon BTC decisions, any macro context must meet point-in-time availability and lag/
revision requirements.

## 11. Liquidity

### SOURCE CLAIM

Liquidity itself varies over time.

Illiquidity can command a premium because investors require compensation for:

- difficulty exiting;
- transaction costs;
- inability to rebalance;
- losses that often coincide with systemic stress.

Systematic liquidity risk is especially costly because liquidity tends to become scarce in bad times.

### Time-varying liquidity premium

The source argues that expected compensation for bearing illiquidity is not constant.

When too much capital chases illiquid assets, the prospective premium can become small.

After crises, when capital is scarce, compensation can become much larger.

### PROJECT INTERPRETATION

This reinforces LIB-020/Harris conceptually but from a return-premium perspective:

liquidity can affect both:

- **execution quality**;
- **expected compensation / regime state**.

These roles must not be conflated in the future system.

## 12. Tail risk, volatility, correlation and skewness

### SOURCE CLAIM

Unconditional volatility alone is an incomplete measure of risk.

Higher expected returns are more plausibly connected to exposures that lose during particularly bad
states, including:

- high correlation;
- negative skew;
- funding stress;
- tail events.

The book reviews evidence that within asset classes, very high-volatility securities can even have
poor average returns.

### Funding constraints

Leverage constraints and forced deleveraging can make low-beta / low-volatility assets attractive on
a risk-adjusted basis while still creating losses when funding conditions tighten.

### Time-varying tail premia

Tail-risk compensation may be highest after painful events when:

- recent losses are salient;
- risk-bearing capital has disappeared;
- insurance supply is scarce.

It may become exceptionally low after long calm periods.

### PROJECT INTERPRETATION

"Risk" in Trading Bot should eventually encompass more than a rolling standard deviation.

Potential distinctions for final synthesis include:

- ordinary volatility;
- liquidity stress;
- correlation/concentration;
- convexity / asymmetry;
- tail-state exposure.

No implementation is frozen here.

## 13. Feedback loops, crowding and endogenous risk

Chapter 20 is especially useful for understanding why historical signal behavior can change.

### SOURCE CLAIM

Markets can exhibit feedback from past returns into future behavior through:

- extrapolation;
- wealth changes;
- changing risk aversion;
- leverage;
- funding constraints;
- stop-loss/risk-control rules;
- investor flows.

These mechanisms can generate:

- momentum;
- bubbles;
- crashes;
- long-term reversals.

### Crowding

A profitable strategy can attract capital.

As participation grows:

- returns may become more correlated;
- trades can become more synchronous;
- exits can become crowded;
- negative skew / liquidation risk can rise.

A strategy can therefore become less attractive **because it became popular**.

### PROJECT INTERPRETATION

A signal family should not receive permanent authority merely because a historical backtest showed
strong returns.

Its economic environment and crowding regime can change.

## 14. Forward-looking expected-return indicators

Chapter 21 contrasts historical averages with more prospective measures.

A generic forward-looking decomposition is conceptually:

- current carry/yield;
- expected cash-flow growth;
- expected valuation change.

### Strengths

Forward-looking indicators can reflect today's:

- valuations;
- yields;
- spreads;
- prices.

They avoid blindly assuming that a historically high return continues after valuation changes.

### Weaknesses

They depend on assumptions about:

- mean reversion;
- growth;
- valuation normalization;
- structural stability.

They can be wrong for long periods.

### Horizon

The source stresses that valuation/carry measures are generally more useful at longer horizons.

At shorter horizons, other information such as:

- momentum;
- volatility;
- macro conditions

can become relatively more relevant.

## 15. Tactical forecasting — core multi-signal architecture concepts

Chapter 24 is the single most directly relevant chapter to the Owner's proposed professional
multi-signal reasoning system.

### 15.1 Predictor families

Ilmanen discusses tactical forecasting using information from multiple categories such as:

- value;
- carry;
- momentum;
- macroeconomic indicators;
- supply/demand;
- sentiment;
- liquidity/risk conditions;
- seasonality;
- price patterns.

This is not presented as permission to include every available indicator.

The emphasis is on economically interpretable signals with plausible predictive content.

### 15.2 Binary versus continuous signals

Signals can be represented as:

- simple directional/binary states;
- continuously scaled values reflecting strength.

The source therefore supports the general concept that a signal need not be reduced to a single
Boolean vote.

### 15.3 Predictive ability and signal strength are different

The book describes normalized regression logic in which a predictor's contribution depends on both:

- **how predictive that indicator has historically been**;
- **how extreme/strong the current signal is**.

Conceptually, this is close to separating:

- structural importance/reliability;
- current signal strength.

It is not identical to the Owner's proposed `peso_base × peso2 × strength × quality × relevance`
framework, and no such formula should be attributed to Ilmanen.

### 15.4 Correlated predictors must not be double counted

This is a major source-grounded insight.

When predictors are correlated, raw individual relationships with future returns are not additive.

Ilmanen discusses **partial predictive relationships** / multivariate approaches precisely because
two indicators can contain overlapping information.

### PROJECT INTERPRETATION

This strongly supports family-level deduplication.

Examples such as:

- moving-average slope;
- breakout;
- recent return;
- MACD-like transformations

cannot automatically count as four independent bullish confirmations if they mostly represent the
same underlying trend phenomenon.

### 15.5 Economic priors can constrain models

The source discusses constraining coefficient signs where economic reasoning strongly supports the
expected direction.

This is relevant to avoiding unstable coefficient flipping driven by noise.

### 15.6 Simple models can compete with complex models

More complex forecasting techniques do not automatically produce better out-of-sample performance.

The book discusses more sophisticated tools — dynamic parameters, Bayesian methods, regime switching,
Kalman-type approaches — but repeatedly returns to:

- robustness;
- transparency;
- simple economic logic;
- avoiding overfit.

### 15.7 Different signals decay at different speeds

A crucial concept for Trading Bot:

information families can naturally operate at different horizons.

For example:

- valuation information changes slowly;
- short-term price/flow information can decay quickly.

There is no requirement that every signal refresh at the same frequency.

### 15.8 Divergent versus convergent styles

The source distinguishes broadly:

**Divergent / continuation-oriented**
- trend;
- momentum;
- volatility buying.

**Convergent / mean-reverting / insurance-oriented**
- value;
- carry;
- mean reversion;
- volatility selling.

These groups can behave very differently in stress regimes.

### 15.9 Context can alter signal usefulness

The source discusses conditioning signal effectiveness on environment.

Examples include:

- trend effectiveness varying with macro anchoring / volatility;
- carry becoming more vulnerable under high volatility or poor liquidity;
- different regime conditions changing expected payoffs.

### PROJECT INTERPRETATION

This is strong conceptual support for a future distinction among:

- base family importance;
- current signal strength;
- current relevance/context;
- interaction with other families.

It does **not** provide numeric BTC weights.

## 16. Seasonality

The source reviews recurring calendar patterns but is cautious.

Potential problems include:

- data mining;
- unstable anomalies;
- implementation cost;
- disappearance after publication.

Some seasonals have plausible economic explanations, especially in commodity markets.

### PROJECT INTERPRETATION

Seasonality should not become a core signal family merely because one pattern exists historically.

If ever used, it may be more appropriate as:

- context;
- timing adjustment;
- execution timing

than as a standalone directional engine.

No BTC seasonality is established here.

## 17. Business cycles and regimes

Chapter 26 studies returns across macroeconomic regimes.

### SOURCE CLAIM

Risky assets have historically shown different realized returns around:

- cycle troughs;
- expansions;
- peaks;
- contractions.

The source also considers joint growth/inflation and volatility-type regimes.

### Trend robustness

Trend/momentum is described as historically profitable across several regime classifications,
although performance varies.

### Critical causal caveat

This chapter repeatedly raises a problem central to Trading Bot:

**a regime identified ex post is not automatically observable ex ante.**

Macroeconomic data can be:

- released with delay;
- revised;
- ambiguous in real time.

A historical chart labelled "recession" can therefore overstate the usability of regime information.

### PROJECT INTERPRETATION

Future Trading Bot regimes should preferably be constructed from **causally available market state**,
unless the exact release/revision history of external macro data is modeled.

## 18. Secular trends and structural breaks

The source distinguishes:

- temporary valuation deviations that may mean-revert;
- long-lived secular changes that can invalidate historical anchors.

Examples can arise from:

- demographics;
- productivity;
- institutions;
- inflation regimes;
- regulation;
- technological change.

### PROJECT INTERPRETATION

This is an argument for humility around static baselines.

A system should neither:

- automatically mean-revert every extreme;
- automatically declare every extreme a new regime.

Evidence is required in both directions.

## 19. Risk, horizon, skill and costs

Chapter 28 synthesizes four ways an investor can improve outcomes.

### 19.1 Risk

The source argues that simply seeking the most volatile asset is often inferior to constructing a
better diversified portfolio and, where appropriate, scaling risk carefully.

Risk-adjusted quality matters.

### 19.2 Horizon

A genuine long horizon can be an edge because it permits investors to:

- tolerate temporary illiquidity;
- act contrarian;
- supply capital when others are forced to sell.

But many supposedly long-horizon investors discover during crises that their actual horizon was
shorter because of:

- liquidity needs;
- governance;
- psychology;
- leverage.

### 19.3 Skill

Skill is difficult to distinguish from luck.

Systematic investing can derive skill from:

- broad implementation of robust ideas;
- portfolio construction;
- risk management;
- cost control.

### 19.4 Costs

Cost reduction is described as one of the most reliable ways to improve **net** returns.

Costs include more than explicit fees.

Implementation quality matters.

### PROJECT INTERPRETATION

This aligns strongly with the project's objective:

**robust positive net expectancy after realistic costs**, not impressive gross backtests.

## 20. Final investment takeaways

Chapter 29 integrates the book rather than proposing one universal portfolio.

Important themes include:

- harvest several independent return sources;
- avoid judging risk solely by volatility;
- pay attention to bad-times losses;
- value starting valuations;
- combine value/carry with momentum/trend;
- use diversification across styles/risk factors;
- treat liquidity as valuable and time-varying;
- use moderate timing with humility;
- control costs;
- understand one's genuine comparative/natural advantages.

### Style diversification

The source gives special emphasis to combinations such as:

- value + momentum;
- carry + trend.

Their historically low/negative correlations can produce more effective diversification than
combining several nominal asset classes that share the same underlying growth/equity exposure.

### Important warning

The book explicitly notes that simulated strategy-style histories can look better than reality due to:

- overfitting;
- selection bias;
- ignored/understated trading costs.

This caveat is essential.

## 21. Chapter-by-chapter coverage record

### Chapter 1 — Introduction
Framework for expected returns: history, theory, forward-looking indicators, views, risk factors and
strategy styles.

### Chapter 2 — Historical averages and forward-looking returns
Why sample averages and current opportunity sets can differ substantially.

### Chapter 3 — Historical record
Long-run perspective across stocks, bonds, real assets, active styles, FX and cash.

### Chapter 4 — Terminology
Expected versus realized returns, time variation, rational/irrational expectations, currency and
risk-adjustment issues.

### Chapter 5 — Rational theories
Evolution of asset-pricing theory and compensation for economically painful risk.

### Chapter 6 — Behavioral finance
Limits to arbitrage and behavioral mechanisms that can generate predictable mispricing.

### Chapter 7 — Alternative interpretations
Risk premium versus inefficiency versus data-mining/mirage explanations.

### Chapter 8 — Equity risk premium
Historical and forward-looking equity premia and valuation dependence.

### Chapter 9 — Government-bond risk premium
Duration risk, yield-curve information and tactical bond predictors.

### Chapter 10 — Credit risk premium
Credit spreads, expected losses, liquidity, embedded options and bad-times risk.

### Chapter 11 — Alternative asset premia
Commodities, real estate, hedge funds, private equity and their measurement/selection problems.

### Chapter 12 — Value
Value evidence, behavioral mechanisms, value traps, cross-market value and interaction with
momentum.

### Chapter 13 — Currency carry
Carry profitability, crash risk, timing/crowding and cross-market carry analogues.

### Chapter 14 — Commodity momentum / trend following
Trend representations, horizons, behavioral/economic explanations, diversification and costs.

### Chapter 15 — Volatility selling
Variance/volatility premia, correlation/skew, insurance-like returns and rare-loss bias.

### Chapter 16 — Growth factor
Growth sensitivities and why high-growth assets need not provide high subsequent returns.

### Chapter 17 — Inflation factor
Inflation exposures, surprises and regime dependence.

### Chapter 18 — Liquidity factor
Liquidity variation, illiquidity premia and systemic liquidity risk.

### Chapter 19 — Tail risks
Volatility, correlation, skewness, leverage constraints and bad-times risk.

### Chapter 20 — Feedback effects
Flows, leverage, risk management, crowding, momentum and endogenous market instability.

### Chapter 21 — Forward-looking measures
Carry/valuation-based expected-return estimates and their limitations.

### Chapter 22 — Interpreting carry
Expected price changes versus risk premia versus biased expectations.

### Chapter 23 — Survey expectations
Using subjective forecasts to distinguish expected price changes from required returns.

### Chapter 24 — Tactical forecasting
Multi-indicator forecasting, normalization, correlated predictors, signal strength, predictive
ability, context and overfitting.

### Chapter 25 — Seasonality
Calendar effects, data-mining risk and limited tactical uses.

### Chapter 26 — Cyclical and regime-dependent returns
Business cycles, growth/inflation regimes, volatility regimes and ex-ante observability problems.

### Chapter 27 — Secular trends
Long-lasting structural changes and dangers of mechanical mean reversion.

### Chapter 28 — Risk, horizon, skill and costs
Ways to improve net outcomes beyond choosing the historically highest-return asset.

### Chapter 29 — Takeaways
Risk premia, style diversification, liquidity, timing, drawdown control, natural edge and governance.

### Appendices
Appendix B was specifically inspected for data provenance and construction.

The author states that many historical series are assembled from:

- Bloomberg;
- MSCI;
- bond-index providers;
- Kenneth French;
- Robert Shiller;
- Dimson–Marsh–Staunton;
- Ibbotson/Morningstar;
- other academic/practitioner datasets.

Some long histories are **spliced from multiple sources**.

This is important: not every long-run chart in the book represents one homogeneous point-in-time
dataset constructed under unchanged rules.

## 22. Direct relevance to Trading Bot

### HIGH conceptual relevance

This source is highly useful for:

- multi-signal architecture;
- separating signal family from individual indicator;
- distinguishing signal strength from reliability;
- correlated-predictor deduplication;
- regime/context-dependent relevance;
- divergent versus convergent signals;
- trend/momentum as a professional family;
- liquidity/tail-risk context;
- time-varying expected returns;
- cost-aware evaluation;
- avoiding Sharpe-only thinking;
- distinguishing ex ante from hindsight regime labels.

### MODERATE / hypothesis relevance

Potential later hypotheses:

- trend relevance changes by regime;
- liquidity/risk context changes signal actionability;
- value-like and momentum-like information can complement each other;
- carry-like exposures may have hidden tail risk;
- strategy crowding can change payoff structure.

These need BTC-specific evidence.

### LOW / outside current product scope

Much of the following is not directly useful to the initial BTC-only system:

- pension allocation;
- private equity;
- direct real estate;
- institutional liability matching;
- multi-asset strategic allocation;
- options-based volatility selling;
- currency carry implementation.

Their underlying principles may still inform risk reasoning.

## 23. Relation to the Owner's emerging signal-weight idea

This source is the strongest corpus item studied so far for the **conceptual architecture** behind
the Owner's earlier idea, but it does not justify a final formula.

A defensible later interpretation is:

1. each family has a professional/economic role;
2. the current market produces a signal with some magnitude;
3. historical/source evidence informs reliability;
4. context/regime changes current relevance;
5. correlated predictors must have their shared information discounted;
6. costs/risk/actionability remain separate from raw directional evidence.

This resembles the conceptual decomposition:

`base importance × current strength × quality × relevance`

but that expression is **Research Director shorthand**, not an Ilmanen formula.

Likewise, the Owner's proposed small empirical `peso2` remains an open design choice.

No numeric base weights are derived from this book.

## 24. Signal-family role implications

For final synthesis, this source supports considering distinct roles such as:

### DIRECTION
- trend/momentum;
- some macro/valuation signals at appropriate horizons.

### CONFIRMATION
- complementary independent predictors;
- current signal strength.

### CONTEXT
- growth regime;
- inflation regime;
- liquidity;
- volatility;
- crowding;
- valuation.

### RISK
- volatility;
- liquidity;
- tail exposure;
- correlation;
- funding/deleveraging state.

### TIMING
- momentum/trend;
- some seasonality;
- tactical value/carry changes.

The source does **not** give us permission to assign each listed variable a separate vote.

Its discussion of correlated predictors argues for the opposite.

## 25. Important implications for continuous prediction versus trade decision

### Research Director interpretation

Ilmanen's distinction among:

- expected return;
- risk;
- signal strength;
- implementation;
- cost;
- horizon

supports a future architecture in which a bullish directional forecast does not automatically imply
a LONG trade.

A model can reasonably say:

- expected direction positive;
- but current risk premium poor;
- liquidity unfavorable;
- trend overextended;
- cost/actionability weak;
- therefore NO_TRADE.

This interpretation aligns with Owner Mission V2 but is not a literal trading rule from the book.

## 26. Important implications for cycles

The source discusses:

- business cycles;
- regime dependence;
- secular trends;
- multiple return horizons;
- momentum followed by longer-term reversal;
- calendar/seasonal regularities.

However, it does **not** provide a dedicated causal market-cycle methodology of the type the Owner
wants to represent from roughly 40–45 minutes through longer scales.

Therefore:

`CYCLE METHODOLOGY COVERAGE = INSUFFICIENT`

This book cannot justify our final cycle engine.

## 27. What this source does NOT support

LIB-002 does **not** support:

- a profitable BTCUSDT strategy;
- any BTC-specific signal weight;
- a final `peso_base` value;
- a numeric `peso2` bound;
- 15m/1h/4h parameter values;
- a specific moving average;
- a specific breakout horizon;
- a specific stop or target;
- a specific conviction threshold;
- a crypto-funding rule;
- a BTC cycle length;
- a claim that value has an obvious BTC fundamental analogue;
- a claim that historical multi-asset trend parameters transfer intraday;
- using an ex-post recession label as a causal live input;
- treating several correlated momentum transforms as independent confirmations;
- maximizing Sharpe as the sole objective.

## 28. Source limitations

1. Published in 2011; markets, costs, electronic execution and crypto structure have changed.
2. Broad multi-asset focus, not BTC.
3. Many empirical results summarize other studies or proprietary/historical analyses.
4. Historical series sometimes splice multiple data sources.
5. Strategy simulations can contain selection/overfitting and cost assumptions.
6. The book primarily studies longer horizons than Trading Bot's main decision horizon.
7. Macro regime labels can be hard to know in real time.
8. Expected returns remain unobservable.
9. Rational and behavioral explanations are often observationally difficult to distinguish.
10. Strong long-run evidence does not imply immediate short-horizon tradability.

## 29. Durable project knowledge retained from LIB-002

The following points should survive into final corpus synthesis:

1. **Expected return, realized return and trade outcome are different quantities.**
2. **Expected returns are time-varying and inherently noisy to estimate.**
3. Historical averages should not be treated as current expected returns.
4. Use multiple evidence perspectives: history, theory, behavior and forward-looking indicators.
5. **Asset class, strategy style and underlying risk factor are distinct analytical dimensions.**
6. Value, carry, momentum/trend and volatility exposure are economically distinct styles.
7. Growth, inflation, liquidity and tail risk are important context/risk dimensions.
8. Risk should be evaluated by **when losses occur**, not only by unconditional volatility.
9. High average return can compensate for very undesirable tail exposure.
10. Trend/momentum has substantial professional and historical grounding.
11. Trend signal representations are redundant to varying degrees and must not be blindly stacked.
12. Value and momentum can be complementary despite often disagreeing.
13. Carry can hide negative skew, crowding and crash exposure.
14. Liquidity is time-varying and bad-times liquidity risk can command compensation.
15. Volatility, correlation and skew are distinct risk concepts.
16. Crowding and feedback can alter a strategy's future payoff distribution.
17. Forward-looking signals can be preferable to long-run averages when valuations change.
18. Different signals naturally operate at different time horizons.
19. **Signal strength and historical predictive ability are conceptually distinct.**
20. **Correlated predictors must not be counted as independent evidence.**
21. Economic priors can be used to constrain noisy statistical models.
22. Simple models can outperform or match complex ones out of sample.
23. Context/regime can alter the relevance of a signal.
24. Ex-post regime classification is not automatically a valid live input.
25. Structural breaks can defeat mechanical mean reversion.
26. Costs are one of the most reliable determinants of net performance.
27. Strategy-style diversification can be more effective than nominal asset diversification.
28. Forecasting, risk management and implementation are separate problems.
29. Moderate timing may be useful, but certainty about timing should remain low.
30. A system should exploit genuine comparative/natural advantages rather than merely maximize a
    historical statistic.

## 30. Questions for Astra at final corpus review

1. Which of Ilmanen's multi-signal concepts transfer cleanly from multi-asset allocation to a
   single-asset BTC forecasting system?
2. Should Trading Bot explicitly maintain separate variables for:
   - structural family importance;
   - current strength;
   - empirical reliability;
   - regime relevance;
   - redundancy/correlation?
3. Is the Owner's `peso_base + bounded peso2` concept a good implementation of this distinction, or
   would another structure be scientifically cleaner?
4. How should correlated trend transforms be collapsed into one family without losing useful
   horizon information?
5. Should value/carry analogues be excluded from BTC unless a defensible crypto-specific economic
   definition exists?
6. How should liquidity and tail-risk variables be split between:
   - prediction;
   - actionability;
   - sizing;
   - hard veto?
7. Which regime variables can be constructed causally from market data rather than ex-post macro
   labels?
8. How much weight should historical cross-asset trend evidence receive when the target is BTC
   intraday?
9. How should a future model combine divergent signals (trend/momentum) and convergent signals
   (value/mean reversion) without creating unstable regime-switching complexity?
10. How should search multiplicity be controlled if the development sandbox later evaluates multiple
    indicator families and interaction rules?
11. Does the book's normalized multivariate signal logic offer a useful baseline architecture, or
    would it still grant too much freedom for overfitting?
12. Should forecast quality, risk quality and execution quality receive separate scorecards?
13. What additional dedicated source material is needed on causal market cycles before any cycle
    architecture is frozen?
14. Which claims in this dossier are central enough that Astra should reopen the original pages
    rather than relying on the dossier?
15. Does any important book-level conclusion become invalid when moving from long-horizon
    institutional portfolios to 15m–4h BTC decisions?

## 31. Final source disposition

`REVIEWED`

Reason:

- complete 594-page accessible PDF reviewed;
- all 29 chapters covered;
- full-volume visual scan completed;
- major figures/tables inspected;
- relevant chapters studied at greater depth;
- appendices/data provenance inspected;
- source claims separated from Research Director interpretation;
- BTC transfer limitations explicitly recorded;
- no numeric signal weight or Trading Bot parameter inferred from the source.

This source should be retained as a **foundational professional reference for expected-return
reasoning, signal combination, regime/context interpretation, risk-factor thinking and cost-aware
system design**.

It does not authorize System G2, BTC backtesting, parameter calibration, paper strategy execution or
real capital.
