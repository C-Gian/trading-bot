# LIB-019 — Options, Futures, and Other Derivatives (6th Edition) — Source Dossier

Status: **REVIEWED — COMPLETE SOURCE COVERAGE**
Study date: 2026-09-27
Source file: `Options, Futures and Other Derivatives (6th Edition).pdf`
Drive file id: `13EVTsuQKijyJZx4Ako7V7DaL0oIDZ2zZ`
Local corpus id: `LIB-019`
Raw file size: 23,843,928 bytes
SHA-256: `37d6def4f9217a5a34c88d687c2751f36177df85d43ede73120dd674043dd70b`

## 1. Source identity

**Title:** *Options, Futures, and Other Derivatives*  
**Edition:** Sixth Edition  
**Author:** John C. Hull  
**Publisher:** Prentice Hall / Pearson Education  
**Copyright:** 2006  
**Artifact type:** textbook  
**Project classification:** BOOK_TEXTBOOK  
**Evidence tier in registry:** C

The local PDF contains **811 physical PDF pages**.

The core text contains **32 chapters**, followed by:

- glossary;
- DerivaGem software material;
- exchange reference material;
- normal-distribution tables;
- author index;
- subject index.

The source is a broad derivatives textbook. Its central purpose is to explain:

- how forwards, futures, swaps and options work;
- how derivatives are used for hedging, speculation and arbitrage;
- no-arbitrage pricing;
- option valuation;
- volatility and correlation;
- risk measures;
- credit derivatives;
- interest-rate models;
- numerical methods;
- governance lessons from derivatives failures.

It is **not** a book presenting a specific directional trading strategy for BTC or any other single
market.

## 2. Study coverage

The complete accessible source was covered.

Coverage included:

- front matter and detailed table of contents;
- all 32 chapters;
- chapter summaries;
- key formulas and examples where relevant to the current project;
- representative visual inspection of pages/figures;
- glossary/reference sections sufficiently to confirm scope;
- deeper inspection of project-relevant chapters:
  - Ch. 1 — Introduction;
  - Ch. 2 — Mechanics of futures markets;
  - Ch. 3 — Hedging strategies using futures;
  - Ch. 5 — Determination of forward and futures prices;
  - Ch. 15 — The Greek letters;
  - Ch. 18 — Value at risk;
  - Ch. 19 — Estimating volatilities and correlations;
  - Ch. 32 — Derivatives mishaps and what we can learn from them.

The source is from 2006. Market examples, regulation, LIBOR usage, exchange organization and some
implementation details are historically dated. Enduring financial principles are separated below
from period-specific details.

## 3. Core conceptual framework

### SOURCE CLAIM — derivatives serve different purposes

Hull repeatedly distinguishes three broad participant motives:

- **hedging** — reducing an existing exposure;
- **speculation** — taking exposure to future market movements;
- **arbitrage** — exploiting inconsistent prices while offsetting relevant risks.

This distinction is foundational.

A derivative position cannot be judged only by its payoff shape; the economic purpose of the
position matters.

### SOURCE CLAIM — no-arbitrage relationships are different from forecasts

A recurring theme is that many derivative prices are constrained by **arbitrage relationships**.

Examples include:

- forward/futures pricing;
- put-call parity;
- swap valuation;
- option-pricing relationships.

This is materially different from predicting where the underlying market will move.

### RESEARCH DIRECTOR INTERPRETATION

For Trading Bot, a variable such as:

- futures basis;
- forward premium;
- option-implied quantity;
- funding-like carry variable,

must not automatically be treated as a directional forecast.

Some derivatives prices primarily encode financing, carry, storage, yields, volatility expectations,
risk premia or no-arbitrage constraints.

A future crypto-specific source is required before mapping these ideas onto perpetual-futures funding
or BTC basis.

## 4. Futures-market mechanics

### 4.1 Standardization and settlement

The source explains that exchange-traded futures are standardized contracts with rules governing:

- contract size;
- deliverable asset;
- delivery timing/location;
- price quotation;
- settlement;
- margin.

Futures positions are marked to market.

Margin therefore creates daily cash-flow consequences that differ from simply holding an equivalent
forward until maturity.

### 4.2 Convergence

As delivery approaches, the futures price should converge toward spot under the contract's delivery
mechanism.

Otherwise arbitrage opportunities can arise.

### 4.3 Margin and liquidity risk

Daily settlement reduces counterparty credit exposure but creates liquidity requirements.

A position can be economically sensible over its intended horizon and still fail operationally if
adverse interim price moves generate margin calls that cannot be funded.

### PROJECT RELEVANCE

This is important if Trading Bot ever moves from paper spot-like exposure to actual derivatives.

Mark-to-market liquidity risk must be treated separately from final-horizon directional correctness.

## 5. Hedging and basis risk

### SOURCE CLAIM — hedging usually replaces one risk with another

A hedge does not normally eliminate all uncertainty.

Hull emphasizes **basis risk**:

`basis = spot price - futures price`

If the relationship between the hedged exposure and hedge instrument changes, the hedge is imperfect.

### Minimum-variance hedge ratio

The source presents a statistical hedge-ratio framework based on the relationship between spot and
futures changes.

Conceptually, the optimal hedge need not be one-for-one.

### Rolling hedges

When the desired exposure extends beyond liquid futures maturity, hedges may be rolled through
successive contracts.

This introduces:

- basis evolution;
- rollover risk;
- cash-flow pressure.

The Metallgesellschaft case illustrates that a hedge can create severe interim financing pressure
even when its long-run economic rationale appears defensible.

### PROJECT RELEVANCE

For the current Trading Bot, this is mainly risk-methodology knowledge.

It does **not** authorize a futures-hedging layer.

## 6. Forward/futures pricing: one of the most important project lessons

Chapter 5 separates **investment assets** from **consumption assets** and develops no-arbitrage
relationships for forward/futures prices.

### Cost of carry

The book defines cost of carry from financing and carrying costs net of income from the asset.

For investment assets, forward/futures prices can often be tightly related to spot through
no-arbitrage.

For consumption assets, **convenience yield** can matter and an exact equality may not follow from
observable carry variables alone.

### SOURCE CLAIM — futures price is not automatically expected future spot

Hull explicitly separates:

- today's futures/forward price;
- the market's expected future spot price.

Under the model discussed in the book, their relationship depends on risk characteristics.

They are not generally identical.

### RESEARCH DIRECTOR INTERPRETATION

This is directly relevant to future crypto research.

If we later observe:

- BTC perpetual premium;
- term futures basis;
- funding rate,

we must not make the naive inference:

> positive premium = market predicts price will rise.

The observed derivative price may contain carry/risk/liquidity components.

A crypto-specific causal model is required before converting basis/funding into directional evidence.

## 7. Options and payoff engineering

Chapters 8–17 develop:

- option-market mechanics;
- call/put properties;
- put-call parity;
- spread/combination strategies;
- binomial valuation;
- stochastic processes;
- Black-Scholes-Merton;
- options on indices/currencies/futures;
- Greeks;
- volatility smiles;
- numerical valuation.

### Durable conceptual lesson

Options separate different dimensions of risk and payoff:

- direction;
- convexity;
- volatility;
- time;
- rates.

This is useful because a market view cannot always be represented by a single "bullish/bearish"
number.

### PROJECT LIMITATION

Trading Bot's current mission is not an options-trading system.

Therefore option structures and pricing formulas are retained mainly as:

- risk-decomposition knowledge;
- volatility knowledge;
- examples of separating state variables.

They are not candidate V1 trading rules.

## 8. Greeks: decomposing risk instead of using one score

Hull describes option risk through multiple sensitivities:

- **delta** — sensitivity to the underlying;
- **gamma** — sensitivity of delta / curvature;
- **vega** — sensitivity to volatility;
- **theta** — sensitivity to time;
- **rho** — sensitivity to rates.

### RESEARCH DIRECTOR INTERPRETATION

The conceptual value for Trading Bot is not to import option Greeks.

The useful principle is:

> risk is multidimensional and should not be collapsed into one number before understanding its
> components.

This supports a future architecture where:

- directional conviction;
- volatility risk;
- liquidity/execution risk;
- timing risk

remain distinguishable even if they ultimately feed one trade decision.

## 9. Volatility smiles and model misspecification

Chapter 16 emphasizes that the simple lognormal/constant-volatility assumptions behind basic
Black-Scholes do not match observed option prices.

Practitioners instead observe strike- and maturity-dependent implied volatility patterns.

### SOURCE CLAIM

Market prices imply distributions that differ materially from the simplest model.

### RESEARCH DIRECTOR INTERPRETATION

This is an important general modeling lesson:

> a mathematically convenient model can be internally coherent and still be empirically
> misspecified.

Trading Bot should therefore distinguish:

- model convenience;
- empirical adequacy.

A clean formula is not evidence that market behavior follows the formula.

## 10. Numerical methods

The book covers:

- trees;
- finite-difference methods;
- Monte Carlo simulation;
- extensions for path-dependent instruments;
- multi-factor models.

### Durable lesson

The appropriate numerical method depends on:

- path dependence;
- dimensionality;
- early-exercise features;
- required accuracy;
- computational burden.

### PROJECT RELEVANCE

This is mostly background methodology.

It does not imply that Trading Bot needs Monte Carlo or derivative-pricing infrastructure in V1.

## 11. Value at Risk

Chapter 18 defines VaR in terms of:

- horizon;
- confidence level;
- loss threshold.

It covers:

- historical simulation;
- model-based VaR;
- option/nonlinear exposures;
- Monte Carlo;
- stress testing;
- back testing;
- principal-components approaches.

### SOURCE CLAIM — VaR does not describe the severity beyond the threshold

Hull discusses the weakness that two portfolios can have the same VaR while having radically
different losses beyond that cutoff.

The chapter therefore discusses **Conditional VaR / Expected Shortfall** as a measure of expected
loss conditional on being in the tail.

### SOURCE CLAIM — stress testing is necessary

The book argues that VaR should be accompanied by:

- scenario analysis;
- stress testing.

Extreme events can occur far more often than simple normal assumptions imply.

### SOURCE CLAIM — risk-model back testing is required

A VaR model should be checked against realized exceptions.

If a nominal 99% one-day VaR is exceeded far more often than about 1% of observations, the model is
suspect.

### RESEARCH DIRECTOR INTERPRETATION

Trading Bot should not use VaR as the sole V1 risk-control system.

The durable lessons are:

- tail severity matters;
- historical simulation alone is insufficient;
- normal assumptions are fragile;
- model risk must be tested;
- stress scenarios should accompany average-case backtests.

This supports cost/risk stress tests in later evaluation.

## 12. Time-varying volatility and correlation

Chapter 19 is directly relevant to the future state engine.

### SOURCE CLAIM — volatility is not constant

Hull explicitly treats volatility as time varying and unobservable.

The chapter describes estimators that weight recent observations more heavily.

### EWMA

The exponentially weighted moving average updates variance using:

- the previous variance estimate;
- the most recent squared return.

Older observations receive exponentially declining weight.

### GARCH(1,1)

The GARCH(1,1) formulation adds a long-run variance component to:

- recent squared return;
- previous variance.

The book notes the stability condition requiring the dynamic weights to sum to less than one in the
usual parameterization.

### SOURCE CLAIM — analogous methods can update covariance/correlation

The same general framework extends to covariance estimation.

### RESEARCH DIRECTOR INTERPRETATION

This provides a professional basis for treating **volatility/regime state as dynamic**, not a
constant nuisance parameter.

For Trading Bot this could later inform:

- risk scaling;
- regime/context;
- confidence/relevance;
- stop/target geometry.

It does **not** tell us that EWMA or GARCH should automatically become a signal.

No parameter value is imported from this source.

## 13. Credit risk and credit derivatives

Chapters 20–21 distinguish:

- real-world default probabilities;
- risk-neutral default probabilities;
- netting;
- collateral;
- downgrade triggers;
- CDS and structured-credit products.

### PROJECT RELEVANCE

Mostly outside the current BTC trading mission.

The durable methodological lesson is that:

> a probability used for forecasting real-world events is not necessarily the same probability used
> for pricing a derivative.

This distinction is conceptually valuable for future probability calibration.

## 14. Interest-rate models, measure changes and advanced derivatives

Chapters 25–30 cover:

- martingales and numeraires;
- risk-neutral measures;
- caps/floors/swap options;
- convexity adjustments;
- short-rate models;
- HJM;
- LMM;
- advanced swaps.

This is rigorous derivatives-pricing knowledge but low-priority for the current single-asset BTC
product.

It is retained as background, not as active architecture input.

### Historical caveat

The sixth edition makes extensive use of LIBOR-era market conventions.

Those conventions are not to be copied into a modern 2026 system.

## 15. Real options

Chapter 31 applies derivative logic to capital investment opportunities.

### PROJECT RELEVANCE

Low direct relevance.

The useful conceptual point is that flexibility itself can have option value.

No Trading Bot feature is derived from this chapter.

## 16. Derivatives failures and governance

Chapter 32 is one of the most project-relevant chapters in the book.

It reviews historical losses including examples involving:

- Barings;
- Orange County;
- LTCM;
- Metallgesellschaft;
- Procter & Gamble;
- Allied Irish;
- Sumitomo;
- others.

The source's main conclusion is not "derivatives are bad."

The conclusion is that misuse, weak controls, leverage, model error and mandate drift can turn
otherwise useful instruments into catastrophic exposures.

### 16.1 Define explicit risk limits

Risk limits should be:

- clear;
- measurable;
- monitored.

The organization should understand what losses may arise under specified market moves.

### 16.2 Enforce limits even after profits

A particularly important governance lesson is:

> violating a risk limit is still a violation when the result is profitable.

Ignoring profitable violations creates incentives for future uncontrolled risk taking.

### 16.3 Do not infer skill too quickly from a winning streak

Hull uses a simple multiple-trader example to show that an apparently exceptional short history can
arise by chance.

The exact illustrative percentages should not become Trading Bot thresholds.

The durable point is:

- recent success is weak evidence of persistent skill;
- selection among many attempts creates misleading winners.

### 16.4 Stress test

The source explicitly argues that ordinary risk metrics should be supplemented by extreme scenarios.

The LTCM discussion emphasizes:

- liquidity shocks;
- leverage;
- margin pressure;
- crowded strategies.

### 16.5 Do not blindly trust models

Large apparent profits or unusually favorable pricing can indicate:

- model error;
- system error;
- incorrect assumptions.

This is an unusually strong governance lesson for algorithmic research.

### 16.6 Crowding can turn a strategy against itself

When many participants follow similar strategies, liquidation/hedging flows can reinforce market
moves and destroy assumed liquidity.

### 16.7 Understand what is being traded

The book argues that organizations should not trade structures they cannot independently understand
and value.

### 16.8 Prevent mandate drift

A hedge mandate can slowly become speculation.

The book treats clear purpose + controls as protection against this transition.

## 17. Chapter-by-chapter coverage record

### Chapter 1 — Introduction

Defines derivatives, exchange/OTC markets, forwards, futures, options and the distinction among
hedgers, speculators and arbitrageurs.

### Chapter 2 — Mechanics of futures markets

Contract specification, convergence, margin, daily settlement, delivery, order types, regulation and
forward-vs-futures mechanics.

### Chapter 3 — Hedging strategies using futures

Long/short hedges, basis risk, cross hedging, minimum-variance hedge ratio, equity-index hedging and
rolling hedges.

### Chapter 4 — Interest rates

Compounding, zero rates, bootstrap curves, forward rates, FRAs, duration and convexity.

### Chapter 5 — Determination of forward and futures prices

No-arbitrage pricing, short selling, investment vs consumption assets, carry, income/yield, storage,
convenience yield and relation between futures price and expected future spot.

### Chapter 6 — Interest-rate futures

Treasury-bond futures, delivery options, Eurodollar futures, convexity adjustment and duration-based
hedging.

### Chapter 7 — Swaps

Interest-rate and currency swaps, transformation of exposures, valuation and counterparty risk.

### Chapter 8 — Mechanics of options markets

Calls, puts, market making, margin, exercise and market organization.

### Chapter 9 — Properties of stock options

Determinants of option value, bounds, put-call parity and early exercise.

### Chapter 10 — Trading strategies involving options

Covered calls, protective puts, spreads and combinations such as straddles/strangles.

### Chapter 11 — Binomial trees

No-arbitrage option valuation, risk-neutral valuation and dynamic delta.

### Chapter 12 — Wiener processes and Ito's lemma

Stochastic processes, Brownian motion, Ito processes, geometric Brownian motion and simulation.

### Chapter 13 — Black-Scholes-Merton

Lognormal model, dynamic hedging, risk-neutral valuation and implied volatility.

### Chapter 14 — Options on indices, currencies and futures

Extension of option valuation to dividend yields, FX and futures; portfolio insurance.

### Chapter 15 — The Greek letters

Delta, gamma, vega, theta, rho and dynamic risk management.

### Chapter 16 — Volatility smiles

Observed departures from constant-volatility/lognormal assumptions; volatility surfaces.

### Chapter 17 — Basic numerical procedures

Trees, Monte Carlo and finite-difference methods.

### Chapter 18 — Value at risk

VaR, historical simulation, model-based estimation, tail-risk limitations, stress testing and model
back testing.

### Chapter 19 — Estimating volatilities and correlations

Historical volatility, EWMA, ARCH/GARCH, maximum likelihood and dynamic covariance estimation.

### Chapter 20 — Credit risk

Default probability, recovery, credit exposure, netting/collateral and credit VaR.

### Chapter 21 — Credit derivatives

CDS, total-return swaps, nth-to-default structures, CDOs and convertible-bond credit issues.

### Chapter 22 — Exotic options

Barrier, Asian, binary, lookback, compound, chooser and other path/nonstandard payoffs.

### Chapter 23 — Weather, energy and insurance derivatives

Nontraditional underlying risks and derivative-market risk transfer.

### Chapter 24 — More on models and numerical procedures

Stochastic-volatility/jump/CEV-style model extensions and advanced numerical valuation.

### Chapter 25 — Martingales and measures

Risk-neutral valuation, forward measures, numeraires and martingale methods.

### Chapter 26 — Interest-rate derivatives: standard market models

Black-style bond, cap/floor and swaption valuation.

### Chapter 27 — Convexity, timing and quanto adjustments

Situations where simply substituting forward values is not sufficient.

### Chapter 28 — Interest-rate derivatives: short-rate models

Equilibrium vs no-arbitrage term-structure models, including Ho-Lee and Hull-White.

### Chapter 29 — Interest-rate derivatives: HJM and LMM

Multi-period forward-rate modeling and mortgage-backed-security applications.

### Chapter 30 — Swaps revisited

Advanced/nonstandard swaps and embedded option structures.

### Chapter 31 — Real options

Use of option logic in capital-investment decisions.

### Chapter 32 — Derivatives mishaps and what we can learn from them

Risk limits, controls, stress testing, model risk, crowding, leverage, mandate discipline and
organizational governance.

## 18. What this source contributes to Trading Bot

### 18.1 Strong relevance

The strongest durable contributions are:

1. distinguish **pricing relationships** from **directional forecasts**;
2. preserve the distinction between hedging, speculation and arbitrage;
3. model volatility as time-varying;
4. use multiple dimensions of risk rather than one scalar;
5. supplement historical risk metrics with stress scenarios;
6. test risk models against realized outcomes;
7. enforce limits independent of recent profits;
8. guard against model error and crowding;
9. avoid interpreting futures/basis variables naively as expected future spot;
10. separate final economic outcome from interim liquidity/margin path.

### 18.2 Medium relevance

Potentially useful later:

- basis/carry framework;
- volatility estimation;
- correlation dynamics;
- scenario simulation;
- tail-risk measurement;
- risk decomposition.

These need modern BTC-specific validation.

### 18.3 Low relevance to current V1

Most of:

- exotic-option pricing;
- interest-rate derivative models;
- credit derivatives;
- real options;
- advanced swap structures

should remain background knowledge unless product scope later changes.

## 19. Implications for future signal architecture

These are **Research Director interpretations**, not Hull's direct trading rules.

### Volatility should likely be a risk/context family

Hull's treatment makes a strong case that volatility is:

- dynamic;
- forecastable to some extent;
- central to risk.

That supports volatility being a high-importance **RISK / CONTEXT** family rather than being forced
into a bullish/bearish vote.

### Derivatives context should not be naïvely directional

If future Trading Bot uses:

- funding;
- basis;
- perp/spot divergence;
- options-implied volatility,

those variables should first be interpreted through their economic roles.

A premium is not automatically a bullish forecast.

### Risk governance should be hard-coded, not learned from P&L

Risk limits should not expand merely because a configuration recently won.

This supports keeping:

- hard position limits;
- drawdown limits;
- exposure limits

outside empirical signal-weight optimization.

## 20. What this source does NOT support

LIB-019 does not establish:

- a BTC trading edge;
- a LONG/SHORT rule;
- an optimal BTC timeframe;
- a signal-family weight;
- a trend strategy;
- a cycle methodology;
- a funding/OI signal;
- a BTC volatility model;
- a particular GARCH/EWMA parameter;
- a stop/target;
- an entry threshold;
- a probability model for directional forecasts.

It also does not justify using derivatives merely because the product eventually allows SHORT.

## 21. Important limitations

1. **Publication date: 2006.**
2. No Bitcoin/crypto evidence.
3. Many market-practice examples are historically dated.
4. LIBOR-era assumptions are obsolete in modern traditional markets.
5. The source is a textbook synthesis, not one empirical alpha study.
6. Much of the text is about valuation rather than forecasting.
7. Models such as geometric Brownian motion/constant volatility are teaching frameworks and are
   explicitly shown later in the book to be imperfect.
8. Futures-market concepts do not automatically transfer to crypto perpetuals.
9. Option-implied information does not automatically imply direction.
10. The source contains extensive theory outside the current product's initial scope.

## 22. Durable knowledge retained from LIB-019

The following points should survive into final corpus synthesis:

1. Derivative **pricing** and market **forecasting** are different tasks.
2. Futures price is not generically identical to expected future spot price.
3. Carry/basis relationships can reflect financing and economic structure, not just directional
   belief.
4. Hedging, speculation and arbitrage must remain conceptually distinct.
5. Basis risk prevents many hedges from being perfect.
6. Mark-to-market creates path-dependent liquidity risk.
7. Volatility and correlation are time varying.
8. EWMA/GARCH are professional frameworks for modeling dynamic variance, but not automatically
   alpha signals.
9. Tail severity is not captured fully by VaR; expected-shortfall concepts and stress tests matter.
10. Risk models must be checked against realized outcomes.
11. Normal-distribution assumptions understate some real-world extreme-event behavior.
12. Apparent model profitability may reflect model/system error.
13. Profitable risk-limit violations are still governance failures.
14. Short winning histories can arise from chance when many traders/configurations are observed.
15. Crowded strategies can create self-reinforcing liquidity stress.
16. Hard risk limits should remain conceptually separate from alpha calibration.
17. A system should understand independently the instruments/risks it trades.
18. A future BTC derivatives layer would require new crypto-specific sources before implementation.

## 23. Questions for Astra at final corpus review

1. Which derivatives-derived variables, if any, belong in the future BTC information architecture:
   basis, funding, implied volatility, skew, open interest?
2. How do we prevent those variables from being interpreted as directional forecasts when they may
   primarily encode carry, hedging demand or risk premia?
3. Should volatility be strictly a RISK/CONTEXT family, or can some volatility dynamics legitimately
   contribute to direction?
4. Which hard risk limits should remain completely non-learned?
5. How should stress tests be designed for BTC without retroactively tailoring them to known crashes?
6. Should Expected Shortfall or another tail metric supplement maximum drawdown in later evaluation?
7. What modern crypto-specific evidence is needed before importing basis/carry relationships?
8. How should Trading Bot distinguish a model failure from an alpha failure?
9. What evidence threshold should be required before treating a recent winning streak as persistent
   skill rather than selection/luck?
10. Does the Owner's LONG/SHORT mission eventually require perpetual futures, or can directional
    paper positions remain instrument-agnostic during the research phase?

## 24. Final source disposition

`REVIEWED`

Reason:

- complete source scope covered;
- all 32 chapters reviewed;
- chapter-level coverage recorded;
- project-relevant chapters inspected in greater depth;
- representative figures/layout visually checked;
- source-derived concepts separated from Research Director interpretation;
- historical/market-structure limitations recorded;
- no unsupported BTC alpha or parameter imported.

This source should be treated as a **foundational derivatives/risk-management textbook** for final
knowledge synthesis, with especially strong relevance to:

- futures/basis interpretation;
- dynamic volatility;
- risk measurement;
- stress testing;
- governance.

It does not authorize any Trading Bot strategy, System G2, parameter calibration or market
experiment.
