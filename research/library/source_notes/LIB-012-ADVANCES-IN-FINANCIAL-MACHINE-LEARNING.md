# LIB-012 — Advances in Financial Machine Learning — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `Advances-in-Financial-Machine-Learning.pdf`  
Drive file id: `1-PpSbPLJNNrJnPu6IVxFrVlJoY9BtuDM`  
Local corpus id: `LIB-012`  
Raw file size: 20,011,437 bytes  
SHA-256: `2d5f8aec174bcaf7a33d4caf070c018a5ac4a07cdc72ddb5cc2df3a6e2650b80`

## 1. Source identity

**Title:** *Advances in Financial Machine Learning*  
**Author:** Marcos López de Prado  
**Publisher:** John Wiley & Sons  
**Copyright:** 2018  
**Hardcover ISBN:** 978-1-119-48208-6  
**ePDF ISBN:** 978-1-119-48211-6  
**ePub ISBN:** 978-1-119-48210-9  
**Artifact type:** professional/technical book  
**Corpus classification:** BOOK_TEXTBOOK  
**Evidence tier in project registry:** C

Chapter 22 is coauthored with **Kesheng Wu** and **Horst D. Simon**.

The local PDF contains **518 physical PDF pages** and 22 chapters organized into five parts:

1. Data Analysis;
2. Modelling;
3. Backtesting;
4. Useful Financial Features;
5. High-Performance Computing Recipes.

The book is not a BTC trading manual and does not present one finished trading strategy. Its primary
purpose is to adapt machine-learning and statistical research workflows to the peculiarities of
financial data.

## 2. Study coverage

The complete accessible PDF was reviewed.

Coverage included:

- title/front matter and preamble;
- table of contents;
- all 22 chapters;
- chapter conclusions and exercises where they clarified intended use;
- formulas, code snippets and examples where materially relevant;
- a visual inspection of every chapter opening;
- targeted visual inspection of important figures/tables, including:
  - triple-barrier labeling;
  - sequential bootstrap / uniqueness;
  - fractional differentiation;
  - feature-importance examples;
  - combinatorial purged CV;
  - drawdown / time-under-water;
  - Deflated Sharpe Ratio;
  - structural-break tests;
  - market-microstructure features;
- bibliography/index-level checks.

The source was studied independently. No external paper or web source was used to fill gaps in the
book.

## 3. Overall thesis of the book

### SOURCE CLAIM — financial ML is a distinct problem class

The book argues that applying generic machine-learning recipes directly to financial data often
fails because financial observations are:

- noisy;
- non-stationary;
- dependent rather than IID;
- affected by overlapping outcomes;
- prone to structural change;
- vulnerable to data leakage;
- unusually exposed to selection/backtest overfitting.

The author therefore builds a finance-specific research stack around:

- better data representation;
- event-based sampling;
- labeling;
- sample weighting;
- leakage-aware validation;
- feature importance;
- robust hyper-parameter tuning;
- bet sizing;
- backtest-overfitting controls;
- structural-break and microstructure features.

### SOURCE CLAIM — research infrastructure matters

The book criticizes isolated researchers repeatedly mining strategies in silos.

It advocates an organized research process in which distinct roles handle:

- data curation;
- feature research;
- strategy formulation;
- validation/backtesting;
- implementation/deployment.

The intended advantage is not merely organizational efficiency. Shared research infrastructure is
presented as a way to reduce duplicated mistakes and uncontrolled data mining.

### RESEARCH DIRECTOR INTERPRETATION

This is highly compatible with the Owner's project governance in which:

- ChatGPT owns scientific direction;
- repository artifacts preserve research truth;
- executors implement rather than decide science;
- trial/search history must survive;
- evaluation evidence must be separated from development.

The book does **not** validate our specific governance or algorithm.

## 4. Part I — Data Analysis

# Chapter 1 — Financial Machine Learning as a Distinct Subject

### SOURCE CLAIMS

Financial ML projects have unusually high failure risk because:

- financial signal-to-noise ratios are low;
- data are adaptive and dependent;
- many apparently successful discoveries are selection artifacts;
- standard academic/ML assumptions often do not hold.

The author treats backtest overfitting as one of the central unsolved practical problems in
quantitative finance.

The chapter advocates a research "factory" rather than repeatedly asking one researcher to perform
every step from raw data to trading strategy.

### PROJECT RELEVANCE

Durable implications for later synthesis:

- research process is part of model quality;
- provenance, data contracts and deterministic validation matter;
- repeated human/algorithmic search is itself a source of overfitting;
- a professional system needs infrastructure for research, not only signal code.

No trading signal is derived from this chapter.

# Chapter 2 — Financial Data Structures

### SOURCE CLAIM — data categories and point-in-time integrity

The book groups financial information broadly into:

- fundamental;
- market;
- analytics;
- alternative data.

It stresses that release timestamps, restatements/backfills and availability timing must be known
before a variable is used historically.

### SOURCE CLAIM — time bars are not universally efficient sampling units

The author argues that fixed-clock bars can:

- oversample quiet periods;
- undersample high-information periods;
- inherit undesirable statistical properties.

Alternatives include:

- tick bars;
- volume bars;
- dollar bars;
- imbalance bars;
- run bars.

Information-driven bars attempt to sample when observed order-flow imbalance departs materially from
its expected state.

### SOURCE CLAIM — event-based sampling

The book promotes filters such as CUSUM to identify events worth sampling rather than forcing a
model prediction at every arbitrary instant.

### RESEARCH DIRECTOR INTERPRETATION

For Trading Bot this raises two separate design questions:

1. what clock the **user/product** wants for continuous predictions;
2. what sampling/event representation a **research feature/model** should use internally.

The Owner requires prediction at every eligible candle. That does not necessarily mean every feature
must be learned on naive fixed-clock observations.

No replacement of the current canonical 1m market data is authorized here.

# Chapter 3 — Labeling

### SOURCE CLAIM — fixed-time labels can be poor abstractions

The author criticizes labels based only on:

- a fixed horizon;
- a constant return threshold,

because volatility changes over time and because the path taken before the terminal horizon matters
to many trading decisions.

### SOURCE CLAIM — triple-barrier method

The triple-barrier framework combines:

- an upper horizontal barrier;
- a lower horizontal barrier;
- a vertical time barrier.

The label can depend on which barrier is reached first.

The horizontal barriers can be scaled to estimated volatility.

### SOURCE CLAIM — learning side and size separately

The book distinguishes:

- **side**: long vs short directional decision;
- **size/action**: whether/how strongly to act on that direction.

### SOURCE CLAIM — meta-labeling

A primary model can determine side while a secondary ML model predicts whether the proposed trade
should be acted upon.

The meta-label is binary:

- take;
- pass.

The author presents meta-labeling as a way to:

- improve precision;
- reduce false positives;
- let the primary model preserve interpretability/domain knowledge;
- use ML for conditional actionability/sizing rather than for generating direction from scratch.

### RESEARCH DIRECTOR INTERPRETATION

This is one of the most relevant architectural ideas in the book for the Owner's intended product.

A future architecture **could**, subject to corpus synthesis and Astra review, resemble:

- interpretable professional evidence engine -> directional forecast;
- separate actionability layer -> LONG / SHORT / NO_TRADE;
- potentially a calibrated statistical/ML layer estimating whether the primary opportunity is worth
  acting on.

This is only a candidate interpretation.

The book does not demonstrate that meta-labeling improves BTCUSDT at our horizon.

# Chapter 4 — Sample Weights

### SOURCE CLAIM — overlapping labels violate naive IID assumptions

When outcomes overlap in time, observations share information.

Treating every labeled example as independent overstates the effective sample size.

The book defines concepts including:

- concurrency;
- average uniqueness;
- sample weights;
- sequential bootstrap.

### SOURCE CLAIM — sequential bootstrap

Sequential bootstrap aims to select observations whose information overlaps less with observations
already sampled.

The book argues that this can increase average sample uniqueness relative to ordinary bootstrap
sampling.

### SOURCE CLAIM — return attribution and time decay

Samples can be weighted using:

- uniqueness;
- attributed absolute return;
- time decay;
- class balancing.

### RESEARCH DIRECTOR INTERPRETATION

This is directly relevant to Trading Bot's overlapping forecast horizons.

If predictions occur every 15m but targets can extend several hours, thousands of predictions do
not constitute thousands of independent trials.

Later statistical analysis must account for this dependence.

# Chapter 5 — Fractionally Differentiated Features

### SOURCE CLAIM — stationarity versus memory

Standard integer differencing can make a price series more stationary while destroying a large
amount of historical memory.

The book presents **fractional differentiation** as a compromise:

- induce sufficient stationarity;
- retain more long-memory information.

A fixed-width implementation is proposed to avoid the drift associated with expanding weights.

### SOURCE EXAMPLE

An E-mini S&P 500 example is used to show that relatively low fractional differentiation can satisfy
an ADF-style stationarity test while preserving very high correlation with the original log-price
series.

A multi-futures example is also presented.

### LIMITATION / PROJECT RELEVANCE

This source does not establish that fractionally differentiated BTC prices outperform ordinary
returns or other representations.

It is a candidate feature-engineering technique, not a required component.

## 5. Part II — Modelling

# Chapter 6 — Ensemble Methods

### SOURCE CLAIMS

The chapter decomposes prediction error into:

- bias;
- variance;
- irreducible noise.

It discusses:

- bagging;
- random forests;
- boosting.

Bagging works best when constituent estimators are sufficiently decorrelated.

In finance, heavily overlapping/non-IID observations can weaken ordinary bootstrap assumptions.

The author generally favors variance-reduction approaches such as bagging when overfitting is a
larger danger than underfitting.

### PROJECT RELEVANCE

If ML is eventually admitted, model diversity must be genuine.

Several models trained on nearly identical information should not be interpreted as independent
confirmation.

# Chapter 7 — Cross-Validation in Finance

### SOURCE CLAIM — ordinary K-fold CV can leak

Financial labels and features often overlap through time.

Randomly assigning observations to folds can let training observations contain information whose
outcome period overlaps the test sample.

### SOURCE CLAIM — purging

Training samples whose label intervals overlap test intervals should be removed where appropriate.

### SOURCE CLAIM — embargo

An additional period after test observations can be withheld from training when feature/outcome
dependencies make adjacent samples unsafe.

### RESEARCH DIRECTOR INTERPRETATION

Time-series order alone does not automatically guarantee leakage safety.

Future validation must reason explicitly about:

- feature availability;
- target intervals;
- overlapping labels;
- training/test temporal contact.

This reinforces an existing project guardrail.

# Chapter 8 — Feature Importance

### SOURCE POSITION

The author argues that repeated backtesting is a poor way to discover what features matter.

Instead, feature importance should be investigated directly.

Methods discussed include:

- Mean Decrease Impurity (MDI);
- Mean Decrease Accuracy / permutation importance (MDA);
- Single Feature Importance (SFI).

### SOURCE CLAIM — substitution effects

When features are correlated or redundant, one feature can substitute for another.

This can distort importance estimates and create false interpretations.

The book also discusses orthogonalization/PCA and synthetic experiments for understanding feature
importance.

### RESEARCH DIRECTOR INTERPRETATION

This is extremely relevant to the Owner's concern about "all relevant professional signals" without
feature soup.

Later architecture should operate at the level of **information families**, not give independent
votes to:

- multiple moving averages;
- momentum return;
- MACD-like transforms;
- breakouts,

if they substantially encode the same underlying state.

Feature redundancy should be measured, not merely guessed.

# Chapter 9 — Hyper-Parameter Tuning with Cross-Validation

### SOURCE CLAIMS

The book presents:

- grid search;
- randomized search;
- purged CV integration;
- scoring choices.

Randomized search is presented as useful in high-dimensional hyper-parameter spaces.

The author recommends probability-sensitive scoring such as log-loss where confidence estimates
matter and highlights F1 for imbalanced meta-label settings.

### RESEARCH DIRECTOR INTERPRETATION

Hyper-parameter tuning is itself part of the search burden.

A future development process cannot treat tuned parameters as though they were predeclared.

No parameter search is authorized by this source study.

## 6. Part III — Backtesting

# Chapter 10 — Bet Sizing

### SOURCE CLAIM — direction alone is insufficient

Even a directional model with useful information can produce poor economic results if position
sizing is wrong.

The chapter discusses:

- strategy-independent sizing;
- predicted-probability sizing;
- averaging active bets;
- discretized sizes to reduce turnover;
- dynamic position size;
- limit-price concepts.

### SOURCE CLAIM — probability/confidence can inform size

In a meta-labeling framework, estimated probability can be mapped into the magnitude of a position.

### RESEARCH DIRECTOR INTERPRETATION

For the Owner's product this reinforces a clean separation among:

- direction;
- forecast confidence;
- conviction/actionability;
- risk/size.

Those concepts should not be collapsed into a single arbitrary score.

# Chapter 11 — The Dangers of Backtesting

### SOURCE POSITION — a backtest is not an experiment

A historical simulation does not create a controlled counterfactual environment.

The book catalogs common errors including:

- survivorship bias;
- look-ahead / point-in-time errors;
- narrative/storytelling bias;
- data mining;
- transaction-cost errors;
- outlier dependence;
- shorting/financing/practical constraints.

### SOURCE POSITION — strict anti-refinement doctrine

López de Prado takes a deliberately strict position:

- research/specification should precede the final backtest;
- every backtest should be recorded;
- a failed final backtest should lead to rejection/restart rather than iterative repair based on the
  same result.

### IMPORTANT CORPUS CONTRADICTION

This position is **not** treated as universal consensus.

Earlier corpus sources differ:

- Ernest Chan explicitly allows simple economically motivated refinement with separate test
  discipline;
- Robert Carver allows ideas-first calibration/variants while warning strongly against broad data
  mining.

This disagreement must remain unresolved until final corpus synthesis and Astra review.

### PROJECT RELEVANCE

Regardless of which stage-specific development policy is eventually chosen, this chapter strongly
supports:

- trial logging;
- point-in-time discipline;
- realistic costs;
- accounting for researcher search;
- not recycling protected evaluation as development evidence.

# Chapter 12 — Backtesting through Cross-Validation

### SOURCE CLAIM — walk-forward has strengths and weaknesses

Walk-forward simulation preserves historical sequence and can provide a realistic filtration view.

Weaknesses include:

- one realized historical path;
- path dependence;
- early periods with less training information.

Purging may still be needed.

### SOURCE CLAIM — combinatorial purged CV (CPCV)

CPCV constructs multiple purged train/test combinations and multiple backtest paths.

The purpose is to obtain a distribution of performance outcomes rather than rely on one historical
path.

### PROJECT RELEVANCE

CPCV is a candidate diagnostic framework when the future problem structure supports it.

It is not automatically appropriate for every rule-based component or every Trading Bot metric.

# Chapter 13 — Backtesting on Synthetic Data

### SOURCE CLAIM — trading rules can be separated from investment strategy

The chapter distinguishes:

- an investment strategy / economic thesis;
- trading rules that implement entry/exit behavior.

### SOURCE POSITION

Optimizing stop-loss/profit-taking rules directly over historical data can overfit the realized path.

The chapter demonstrates synthetic calibration using an Ornstein-Uhlenbeck process.

### LIMITATION

The O-U framework is an educational/modeling assumption.

The source does not establish that BTC follows O-U dynamics or that its synthetic-calibration
procedure should be copied into Trading Bot.

### RESEARCH DIRECTOR INTERPRETATION

Synthetic data can be valuable for:

- deterministic stress tests;
- validating trade-geometry logic;
- understanding failure surfaces,

provided the simulated process is justified.

# Chapter 14 — Backtest Statistics

### SOURCE CLAIM — a backtest needs more than headline return

The chapter proposes reporting categories including:

**General characteristics**
- time range;
- market/regime coverage;
- AUM/capacity;
- leverage;
- concentration;
- long/short exposure;
- bet frequency;
- holding period;
- turnover.

**Performance**
- P&L;
- annualized return;
- hit ratio;
- average gains/losses.

**Runs / path**
- drawdown;
- time under water;
- concentration of outcomes.

**Implementation**
- implementation shortfall.

**Efficiency**
- Sharpe;
- Probabilistic Sharpe Ratio (PSR);
- Deflated Sharpe Ratio (DSR).

**Classification**
- accuracy;
- precision;
- recall;
- F1;
- log-loss.

### SOURCE POSITION — trial history matters

Performance evidence should be interpreted in light of the number/distribution of alternative trials
that were tested.

### RESEARCH DIRECTOR INTERPRETATION

This aligns strongly with the Owner's objective of **net expectancy**, not hit rate.

Future reporting should score at least two distinct objects:

1. continuous forecast quality;
2. selective trade-policy economics.

A strategy can have mediocre hit rate and positive expectancy, or accurate directional forecasts but
bad trade economics.

# Chapter 15 — Understanding Strategy Risk

### SOURCE CLAIM

The chapter models strategy outcomes using simplified hit/miss processes to connect:

- probability of success;
- payoff asymmetry;
- number/frequency of bets;
- Sharpe target;
- probability of strategy failure.

### SOURCE IMPLICATION

A low-frequency strategy needs stronger per-bet evidence than a high-frequency strategy to reach the
same statistical/economic confidence.

### PROJECT RELEVANCE

This is useful when evaluating sparse systems.

A few profitable trades cannot carry the same evidentiary weight as a large independent sample.

No universal required precision or trade count is supplied for our BTC use case.

# Chapter 16 — Machine Learning Asset Allocation

### SOURCE CLAIM — instability of convex allocation

The chapter criticizes classical mean-variance allocation when covariance inversion and estimation
error lead to unstable/concentrated portfolios.

It introduces **Hierarchical Risk Parity (HRP)** using:

- hierarchical clustering;
- quasi-diagonalization;
- recursive bisection.

### PROJECT RELEVANCE

Trading Bot V1 is BTC-only, so HRP is not a direct portfolio-allocation requirement.

The more transferable concept is:

> correlated objects should be grouped structurally, and robust hierarchical allocation may be more
> stable than point-optimizing noisy covariance estimates.

That principle may later inform grouping of correlated signal families.

## 7. Part IV — Useful Financial Features

# Chapter 17 — Structural Breaks

### SOURCE CLAIM

Market relationships can change through structural breaks/regime transitions.

The chapter discusses tests including:

- CUSUM;
- Chow-type Dickey-Fuller;
- Supremum ADF (SADF);
- quantile/conditional variants;
- sub-/super-martingale tests.

The book uses examples of explosive behavior/bubbles and argues that structural-break detection can
create useful features.

### PROJECT RELEVANCE

This supports considering **regime/context** as a distinct information role.

A regime detector is not automatically a directional trading rule.

Any BTC implementation would need causal, current-market validation.

# Chapter 18 — Entropy Features

### SOURCE CLAIM

Information theory can describe:

- uncertainty;
- redundancy;
- dependence;
- nonlinear association.

The chapter covers:

- Shannon entropy;
- mutual information;
- plug-in estimators;
- Lempel-Ziv / Kontoyiannis-style entropy estimators;
- encoding choices;
- maximum entropy;
- concentration/effective diversity.

### SOURCE APPLICATIONS

Potential applications include:

- measuring market efficiency/redundancy;
- scenario generation;
- portfolio concentration;
- market microstructure.

### RESEARCH DIRECTOR INTERPRETATION

A short-horizon flow imbalance may be more informative if it is **unexpected** relative to recent
flow behavior than if it is merely large in absolute terms.

That interpretation is plausible from the source but not a frozen Trading Bot feature.

# Chapter 19 — Microstructural Features

### SOURCE CLAIM — microstructure data are information-rich

The chapter discusses raw events including:

- quotes;
- trades;
- cancellations;
- queue/book state;
- aggressor information;
- partial fills.

It reviews generations of microstructure models.

### First-generation examples

- tick rule;
- Roll model;
- high-low volatility;
- Corwin-Schultz-type spread estimates.

### Second-generation examples

- Kyle's lambda;
- Amihud's lambda;
- Hasbrouck-style price-impact measures.

### Third-generation examples

- sequential-trade models;
- PIN/VPIN-style models.

The book also discusses:

- order cancellation rates;
- limit/market order rates;
- signatures of predatory activity;
- execution-algorithm footprints;
- signed-order-flow serial dependence.

### LIMITATION

The book reports/uses models from the literature.

This dossier does not elevate every model, especially PIN/VPIN-style measures, into validated truth
for 2026 BTC markets.

### RESEARCH DIRECTOR INTERPRETATION

This reinforces Harris (LIB-020) conceptually:

- raw volume/flow should not be treated as a simple independent directional vote;
- flow must be interpreted relative to liquidity, expected activity and market structure;
- microstructure state may be useful for **timing/actionability/execution**, even when it is not the
  main directional signal.

No specific BTC order-flow feature is authorized yet.

## 8. Part V — High-Performance Computing Recipes

# Chapter 20 — Multiprocessing and Vectorization

### SOURCE CONTENT

The chapter discusses:

- vectorization;
- threading/multiprocessing;
- task partitioning;
- "atoms and molecules";
- linear/nested partitions;
- asynchronous processing;
- result reduction;
- memory-aware chunking.

### PROJECT RELEVANCE

This is engineering guidance rather than alpha evidence.

It is relevant to deterministic high-volume research infrastructure and recalls the G1 runtime
problem where repeated recomputation made Phase A take many hours.

It does not justify premature infrastructure complexity.

# Chapter 21 — Brute Force and Quantum Computers

### SOURCE CONTENT

The chapter frames some financial problems as combinatorial optimization problems and discusses why
brute-force search becomes intractable.

Quantum annealing is introduced as a possible computational approach for certain discrete
optimization problems.

### PROJECT RELEVANCE

The direct quantum-computing material is outside current V1 needs.

The durable lesson is more basic:

- combinatorial search spaces grow explosively;
- computation capacity does not remove statistical overfitting;
- search spaces need principled constraints.

# Chapter 22 — High-Performance Computational Intelligence and Forecasting Technologies

### SOURCE CONTENT

This chapter discusses a high-performance computing research programme motivated partly by the need
to analyze high-volume market data rapidly.

Topics include:

- HPC vs cloud-style workloads;
- parallel computation;
- streaming analysis;
- storage/I/O;
- scalable processing;
- VPIN-related examples.

### PROJECT RELEVANCE

Trading Bot V1 does not need an HPC cluster.

The relevant lessons are:

- data pipelines must scale predictably;
- I/O and computation architecture can alter research throughput;
- performance engineering should not change scientific semantics.

## 9. Cross-cutting source concepts most relevant to Trading Bot

### 9.1 Separate primary signal from actionability

The strongest architectural bridge to the Owner's desired product is meta-labeling.

Conceptually:

- professional/interpretable evidence can determine **direction**;
- a separate layer can estimate **whether to act**;
- probability/confidence can influence **size/conviction**.

This maps naturally to the product distinction:

- continuous prediction;
- LONG / SHORT / NO_TRADE.

However, the source does not establish the exact model or threshold we should use.

### 9.2 Treat overlapping forecasts as dependent

If predictions are produced every 15 minutes with outcomes extending hours, effective sample size is
much smaller than the candle count.

Purging, uniqueness weighting and dependence-aware statistics become candidate tools.

### 9.3 Prevent redundant signals from becoming multiple votes

Feature substitution/importance results reinforce the project guardrail against feature soup.

The eventual architecture should distinguish:

- multiple formulas;
- independent information.

Those are not the same thing.

### 9.4 Probability should mean something operational

Probability estimates are useful only if calibration/scoring and downstream sizing/actionability are
well specified.

A label such as "80% confidence" should not be decorative.

### 9.5 Development search must remain visible

Even if the final project adopts a more iterative development policy than de Prado recommends,
every:

- architecture variant;
- parameter trial;
- data transformation;
- evaluation reuse

must remain visible in the research ledger.

### 9.6 Forecast quality and trading performance need separate evaluation

The source contains tools for both:

- classification/probability evaluation;
- economic/backtest evaluation.

This is consistent with the Owner's requirement to retain and score every prediction while trading
only selectively.

## 10. What this source does NOT support

The book does **not** establish:

- a profitable BTCUSDT strategy;
- that machine learning should be the core of Trading Bot;
- that black-box ML should replace professional trading logic;
- any signal-family base weight;
- any `peso2` adjustment;
- any optimal BTC timeframe;
- any BTC cycle method;
- any Binance execution model;
- any specific LONG/SHORT threshold;
- any stop/target for BTC;
- any probability calibration valid for our market without testing;
- any claim that meta-labeling will improve our system;
- any claim that fractional differentiation will improve BTC prediction;
- any claim that VPIN or a particular microstructure model is reliable on BTC;
- any universal minimum Sharpe / trade count / precision;
- that HRP is necessary in a single-asset product.

No System G2 design should be copied mechanically from this book.

## 11. Important limitations

### 11.1 Not BTC-specific

Examples span equities, futures and broader financial datasets.

Crypto/perpetual-specific structure is not the book's target.

### 11.2 2018 publication date

Some:

- software APIs;
- computing assumptions;
- market-technology examples

are dated.

Conceptual statistical issues are generally more durable than implementation details.

### 11.3 Authorial methodology is opinionated

The book does not merely describe tools; it makes strong prescriptions about:

- backtesting;
- research organization;
- validation.

Those prescriptions must be compared with other credible sources rather than treated as project law
by authority.

### 11.4 Many methods introduce additional degrees of freedom

Techniques such as:

- event sampling;
- fractional differentiation;
- structural-break tests;
- entropy measures;
- ML ensembles;
- meta-labeling

can themselves create a huge research search space if introduced indiscriminately.

Using an anti-overfitting technique does not make unrestricted model search safe.

### 11.5 Complexity can exceed the product's needs

The Owner currently wants an interpretable professional trader, not ML for its own sake.

The correct criterion is whether a method solves a demonstrated problem better than a simpler
alternative.

## 12. Major contradiction to preserve for final corpus synthesis

### C-AFML-001 — Can exposed historical backtests be used for iterative development?

**López de Prado position**

The book takes a strict view:

- research first;
- final backtest primarily as rejection filter;
- do not repeatedly modify the model after inspecting historical backtest failure.

**Other corpus positions already encountered**

Chan:

- permits simple, economically motivated refinement with distinct train/test discipline.

Carver:

- permits ideas-first calibration and rule variants while strongly discouraging large search spaces
  and fragile point optimization.

### Research Director status

**UNRESOLVED UNTIL FINAL CORPUS SYNTHESIS.**

A likely stage-based reconciliation may be possible:

- explicitly exposed development sandbox for learning;
- append-only trial/search history;
- protected evaluation that cannot be recycled;
- prospective paper evidence as higher-level confirmation.

But this is not frozen by this dossier.

## 13. Potential role of ML in the future project

This section is Research Director interpretation only.

The book does **not** convince us that Trading Bot should become a black-box ML system.

Its strongest potential value for the Owner's intended architecture is instead:

### Research methodology

- point-in-time integrity;
- dependence-aware CV;
- purging/embargo;
- sample uniqueness;
- feature redundancy;
- multiplicity-aware performance interpretation.

### Optional secondary modelling

Potential future roles, only if later justified:

- meta-labeling / actionability;
- calibrated probability;
- regime classification;
- feature-quality estimation.

### Feature research

Potential concepts:

- event-based sampling;
- structural breaks;
- entropy;
- microstructure;
- fractional differentiation.

These are **candidate research tools**, not an instruction to include all of them.

## 14. Durable project knowledge retained from LIB-012

The following principles are strong enough to preserve for final cross-source synthesis:

1. Financial observations frequently violate IID assumptions.
2. Point-in-time availability must be explicit; backfills/revisions can create hidden leakage.
3. Fixed time bars are not the only meaningful sampling representation.
4. Event-based sampling can separate information arrival from arbitrary clock ticks.
5. Labels should reflect the economic/path-dependent outcome being modeled.
6. Direction and actionability/size can be modeled separately.
7. Meta-labeling is a professional precedent for a primary directional model plus secondary
   take/pass layer.
8. Overlapping outcomes reduce effective sample independence.
9. Sample uniqueness/concurrency should be considered where targets overlap.
10. Stationarity transformations can destroy useful memory; feature representation is a trade-off.
11. Ensemble diversity is useful only when models contain genuinely different information/errors.
12. Random K-fold CV is unsafe when temporal/outcome dependence leaks across folds.
13. Purging and embargo are candidate safeguards for overlapping financial labels.
14. Correlated features create substitution effects; feature count is not evidence count.
15. Feature importance can be more informative for research than repeatedly selecting systems from
    backtests.
16. Hyper-parameter tuning itself consumes research degrees of freedom.
17. Probability/confidence can be tied explicitly to action/size rather than displayed decoratively.
18. A historical backtest is not a controlled experiment.
19. Search/trial history is part of the evidence.
20. Walk-forward and cross-validation answer different questions and have different failure modes.
21. Multiple purged historical paths can characterize path uncertainty better than a single selected
    backtest path in suitable problems.
22. Synthetic data can test mechanisms/trade geometry without pretending the simulated process is
    the real market.
23. Backtest reporting should include path, implementation and selection-aware metrics, not only
    return/hit rate.
24. Sparse strategies require appropriately stronger evidence.
25. Stable hierarchical treatment of correlated objects may be preferable to noisy point
    optimization.
26. Structural breaks/regimes can be modeled as features rather than narrated after the fact.
27. Entropy/information measures can represent unpredictability and redundancy.
28. Order-flow/microstructure variables must be interpreted structurally, not counted as simple
    independent votes.
29. Computational architecture should improve throughput without silently altering model semantics.
30. Anti-overfitting machinery does not grant permission for unconstrained feature/model search.

## 15. Questions for Astra at final corpus review

1. Which AFML methods solve a real problem in the Owner's intended interpretable system, and which
   would add complexity without enough expected value?
2. Is **meta-labeling** a scientifically defensible candidate for the future
   forecast -> actionability separation, or should the first system remain entirely deterministic?
3. If forecasts occur every eligible 15m candle with multi-hour horizons, which combination of:
   - uniqueness weights;
   - purging;
   - embargo;
   - block bootstrap;
   - CPCV
   is actually appropriate?
4. Should feature-family redundancy be measured with:
   - supervised feature importance;
   - correlations;
   - clustering/PCA;
   - a hybrid approach?
5. Can fractional differentiation add useful information beyond ordinary normalized returns/trend
   features for BTC, or is it likely unnecessary complexity?
6. What validation stage, if any, should permit hyper-parameter optimization?
7. How should the project reconcile de Prado's strict no-refinement stance with Chan/Carver and the
   Owner's explicit iterative-development objective?
8. Can structural-break tests serve as causal regime/context features at 15m–4h horizons without
   producing unstable or lagging classifications?
9. Are entropy features useful enough to justify their additional degrees of freedom?
10. Which microstructure measures from Chapter 19 remain credible for modern crypto, and which need
    contemporary crypto-specific evidence before even entering the candidate knowledge map?
11. Should probability calibration and meta-labeling be postponed until the deterministic
    professional rule system has enough trade/forecast support?
12. Which metrics from Chapter 14 should become mandatory for:
    - continuous predictions;
    - selective trades;
    - execution quality?
13. Is CPCV appropriate for our exact dependent forecast geometry, or would purged rolling
    walk-forward diagnostics be more interpretable?
14. How should every development iteration be recorded so DSR/PBO-style selection accounting remains
    possible later?
15. Does the project have a sufficiently clear **comparative advantage hypothesis** before ML is
    allowed to optimize anything?

## 16. Final source disposition

`REVIEWED`

Reason:

- complete accessible 518-page PDF reviewed;
- all 22 chapters covered;
- source structure and chapter openings visually verified;
- key figures/tables visually inspected;
- source claims separated from Research Director interpretation;
- methodological conflict with other corpus sources explicitly preserved;
- BTC/crypto transfer limits recorded;
- no external material used to fill gaps;
- no System G2, signal weight, parameter or market experiment derived from the source.

This book should be treated as a **foundational financial-research-methodology and optional-ML
reference**, not as authority that Trading Bot must become an ML system.
