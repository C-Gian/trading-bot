# LIB-018 — The Probability of Backtest Overfitting — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `ssrn-2326253.pdf`  
Drive file id: `10SKN0AMgP-QfycugAn-Jpksk-EuIxrdM`  
Local corpus id: `LIB-018`  
PDF pages: 34  
File size: 1,184,988 bytes  
SHA-256: `c80ed793bd485868c1330e7d83141e26cb8178ef62cd3c57a469168203969ecb`

## 1. Source identity

**Title:** *The Probability of Backtest Overfitting*  
**Authors:** David H. Bailey, Jonathan M. Borwein, Marcos López de Prado, Qiji Jim Zhu  
**Document date:** February 27, 2015  
**Revision shown in file:** February 2015  
**Source type:** academic / research-methodology paper  
**Project classification:** RESEARCH_METHODOLOGY  
**Evidence tier:** A

The paper proposes a general framework for quantifying **backtest overfitting** in investment-strategy
selection and presents **Combinatorially Symmetric Cross-Validation (CSCV)** as one concrete,
model-free, non-parametric implementation.

The source is methodological. It does not provide evidence for any particular BTC trading edge.

## 2. Complete study coverage

The complete 34-page PDF was reviewed.

Coverage included:

- abstract;
- full introduction;
- comparison with hold-out / scenario-generation / econometric multiple-testing approaches;
- Section 2 general framework;
- Definitions 2.1 and 2.2;
- full CSCV algorithm;
- all equations materially relevant to implementation;
- all four overfit statistics;
- CSCV design properties;
- parameter discussion for `S`, `N`, and `T`;
- design limitations;
- application/misuse limitations;
- complete practical application;
- conclusions;
- all 13 figures;
- references;
- full-document visual scan.

The separate mathematical appendices referenced by the paper are **not part of this source** and were
not used to fill gaps in this dossier.

## 3. Problem the paper addresses

### SOURCE CLAIM

Investment research often tries a large number of:

- strategy forms;
- parameter values;
- securities;
- sampling frequencies;
- entry/exit rules;
- stop-loss settings;

on a finite historical dataset.

The paper argues that conventional significance statements can become misleading when the same
historical data are repeatedly searched.

A nominal false-positive rate applies to one test, not automatically to millions of related trials.

### SOURCE CLAIM

Computational power makes it easy to manufacture apparently attractive backtests by fitting
historical noise.

The paper gives moving-average trend research as a motivating example: even a conceptually simple
strategy can generate a very large configuration space once multiple sample lengths, thresholds,
stops and other parameters are considered.

### RESEARCH DIRECTOR INTERPRETATION

The **search process is part of the evidence**.

A backtest result cannot be evaluated scientifically without knowing how many alternatives and search
paths produced it.

For Trading Bot, failed configurations cannot disappear merely because they were not eventually
selected.

## 4. What the paper means by backtest overfitting

This distinction is important.

### SOURCE DEFINITION

Suppose there are `N` strategy configurations.

A selection process chooses the configuration with best performance **in-sample (IS)**.

Backtest overfitting is characterized by that IS winner performing poorly relative to the remaining
configurations **out-of-sample (OOS)**.

The paper's formal definition describes overfitting when the expected OOS rank of the IS-optimal
strategy falls below the OOS median.

### Important scope clarification from the paper

The authors explicitly state that their use of **IS** refers to:

> the observations used to select the optimal strategy among the N alternatives.

They say it does **not** necessarily mean the historical period used to estimate the underlying
forecasting model itself.

Therefore the PBO framework is specifically about **strategy/configuration selection overfit**.

It is not a universal definition of every possible kind of model-calibration overfit.

### RESEARCH DIRECTOR INTERPRETATION

This materially qualifies an overly broad reading of the paper.

The source strongly warns against performance-driven parameter fitting, but its formal PBO machinery
is aimed at the reliability of a **selection procedure among alternatives**.

That is relevant to our future distinction between:

- development/calibration;
- candidate selection;
- protected evaluation.

## 5. Probability of Backtest Overfitting (PBO)

### SOURCE DEFINITION

PBO is the probability that the configuration selected as optimal IS will rank **below the median**
of the tested configurations OOS.

In the CSCV implementation, this becomes the fraction of negative rank-logit outcomes.

Conceptually:

- low PBO -> IS winners tend to remain relatively strong OOS;
- high PBO -> IS winners often become mediocre/poor OOS.

The paper frames PBO in a Bayesian sense: whether a particular historical selection process was
overfit is deterministic, but evidence can support a probability that overfitting has occurred.

## 6. CSCV input contract

The CSCV procedure starts from a matrix:

`M : T x N`

where:

- `T` = synchronized performance observations;
- `N` = strategy/model configurations tried;
- each column = one configuration's P&L/performance series;
- every configuration must have the same observation index.

Two explicit source requirements are:

1. all columns have the same number of rows and are synchronized;
2. the chosen performance metric can be computed on subsamples.

If configurations trade at different frequencies, the paper says observations should be aggregated
onto a common index.

### PROJECT IMPLICATION

PBO cannot be retrofitted correctly from only a leaderboard containing final Sharpe ratios.

We would need to preserve synchronized **per-observation performance series for every admissible
trial/configuration**.

## 7. CSCV algorithm

The source's implementation proceeds as follows.

### Step 1 — collect all trials

Construct the `T x N` matrix `M`.

### Step 2 — split history into `S` equal slices

`S` must be even.

The rows of `M` are divided into `S` disjoint, equal-size blocks.

### Step 3 — enumerate symmetric half-sample combinations

Choose every possible set of `S/2` blocks as the IS set.

The complementary `S/2` blocks form the OOS set.

Number of combinations:

`C(S, S/2)`

Example in the paper:

- `S = 16`
- 12,870 combinations.

### Step 4 — for each IS/OOS pair

For every combination:

1. reconstruct IS in original time order;
2. reconstruct complementary OOS in original time order;
3. calculate performance for all `N` configurations on IS;
4. rank the configurations IS;
5. identify the IS winner;
6. calculate all `N` performances OOS;
7. determine the OOS rank of the IS winner;
8. convert its relative OOS rank into a logit.

If the selection process is robust, the IS winner should systematically rank well OOS.

### Step 5 — construct the logit distribution

Collect the logit from every symmetric combination.

The PBO estimate is the proportion of the distribution below zero.

### SOURCE DESIGN PROPERTY

Each IS subset is reused as an OOS subset elsewhere.

The procedure is deliberately symmetric.

## 8. Why the paper criticizes a single hold-out set

The paper gives several objections to simple hold-out validation in investment backtesting.

### 8.1 Researcher contamination

If the historical period is public/known, the researcher may already know how markets behaved in the
supposed hold-out interval.

This can contaminate design even without literally fitting on the hold-out observations.

### 8.2 Small-sample problem

Splitting a limited financial history can leave:

- too little data for development;
- too little OOS data for a statistically useful conclusion.

The paper cites external work arguing that hold-out is unreliable for small datasets.

### 8.3 High variance from arbitrary hold-out choice

Different historical hold-out windows can produce different conclusions.

A particular interval can accidentally validate a bad strategy or reject a good one.

### 8.4 Consuming recent observations

Using the most recent history as hold-out removes potentially more representative observations from
strategy development.

Using old history as hold-out may test on a less relevant regime.

### 8.5 Failure to account for trial multiplicity

Most importantly for this paper, hold-out does not directly account for how many strategy
configurations were tried before a winner was selected.

### RESEARCH DIRECTOR CAUTION

These are the authors' arguments for PBO/CSCV.

They do **not** logically imply that Trading Bot should discard protected evaluation or future
prospective testing.

The project's evidence hierarchy can still treat protected/future evidence as stronger confirmation
while using PBO as a development-selection diagnostic.

## 9. Other approaches discussed

### Pseudorandom market scenarios

The paper acknowledges simulation-based testing can produce distributions of outcomes.

Its criticism is that the model generating synthetic market data can itself:

- be overfit;
- omit important empirical structure;
- require market-specific customization.

### Econometric multiple-testing corrections

The paper recognizes econometric methods that adjust significance for many tested regressions.

It argues that many practical trading systems are not naturally represented by one algebraic
forecasting equation, motivating a model-free framework.

## 10. Four complementary diagnostics

The source does not present PBO as the only useful output.

It identifies four related analyses.

### 10.1 PBO

Probability that the IS-selected winner falls below the OOS median.

### 10.2 Performance degradation

Compare performance of IS winners with their OOS performance.

The paper expects strong optimization to often be associated with deteriorating OOS performance.

### 10.3 Probability of loss

Fraction of combinations in which the IS-selected winner has negative OOS performance.

This is distinct from PBO.

A strategy can have:

- low PBO;
- but high probability of OOS loss.

In that case, its problem may not primarily be overfitting; the entire strategy family may simply
have poor performance.

### 10.4 Stochastic dominance

Compare the OOS distribution of the IS-selection procedure with the OOS distribution obtained from
the broader set of alternatives.

If optimizing/selecting IS does not improve the OOS distribution relative to alternatives, the
selection procedure is not adding value.

### PROJECT IMPLICATION

A future experiment report should avoid reducing strategy-selection quality to one number.

PBO, OOS-loss rate, degradation and selection-vs-random dominance answer different questions.

## 11. Performance degradation

### SOURCE CLAIM

The paper describes a frequent negative relation between higher optimized IS performance and OOS
performance.

The intuition is that aggressive fitting can increasingly capture historical noise.

### Important lesson from Figure 2

In the illustrated overfit case:

- all IS Sharpe ratios of selected winners are positive;
- IS Sharpe values are roughly 1–3;
- approximately 78% of corresponding OOS Sharpe ratios are negative;
- PBO is about 74%.

The authors explicitly warn that one cannot escape overfitting merely by requiring a sufficiently
high IS Sharpe ratio.

### Figure 3 counterexample

For a real investment-strategy example:

- OOS probability of loss is about 3%;
- selected configurations rarely fall below the broader OOS median;
- the displayed figure reports `ProbOverfit = 0.04`.

The prose says "PBO of 0.04%", while the plotted value `0.04` conventionally corresponds to about
4%.

This is an internal presentation ambiguity in the source.

Do not silently resolve it.

## 12. Stochastic dominance

The paper uses first- and second-order stochastic dominance to ask whether the **selection
procedure** adds OOS value.

### SOURCE IDEA

A strategy-selection procedure should ideally produce OOS outcomes that dominate what would have
been obtained from an unoptimized/random alternative.

This helps distinguish:

- a meaningful selection process;
- an optimization step that merely creates attractive IS winners.

### PROJECT IMPLICATION

For a future multi-configuration development process, it may be useful to ask not just:

> Which configuration had the highest development metric?

but also:

> Did the rule used to select it improve the OOS outcome distribution at all?

## 13. CSCV design properties

The source attributes the following properties to CSCV.

### Equal IS and OOS size

Every split uses half the observations IS and half OOS.

This makes estimation precision more comparable across the two sides.

### Symmetry

Every training subset can also appear as a testing subset.

### Preservation of chronological structure inside slices

Unlike random reassignment of individual observations, the method works with contiguous/subsample
blocks and recombines them.

The source argues that this helps retain time/seasonal structure.

### Deterministic result

For the same matrix and `S`, the same combinations/logits are obtained.

The result is reproducible rather than Monte-Carlo random.

### Model-free

The procedure only needs trial performance series.

It does not require access to the internal strategy equation.

### Non-parametric PBO estimate

The method uses ranks/logits and does not assume a parametric probability distribution for PBO.

## 14. Choice of `S`

The paper calls `S` a key CSCV parameter.

Trade-off:

- too small -> too few combinations, poor left-tail resolution;
- too large -> slices may become so short that important temporal/seasonal structure is broken.

Examples in the source:

- more than six years of data with `S = 24` gives roughly quarterly slices and 2,704,156 logits;
- `S = 16` gives 12,870 logits;
- with four years of daily data, `S = 16` also creates roughly quarterly slices.

The authors state that they consider `S = 16` reasonable in many cases.

### RESEARCH DIRECTOR CAUTION

This is not a universal Trading Bot default.

Our future observation dependence, holding horizon, overlapping trades and market regime structure
would have to determine whether CSCV is even appropriate and what a valid `S` would be.

## 15. Number of trials `N`

The source stresses that `N` materially affects PBO.

Too few trials mean coarse OOS ranks and a highly discrete logit distribution.

For sensitivity to PBO values below about 0.1, the paper argues that `N` should be substantially
greater than 10.

### Critical project implication

PBO requires a meaningful set of **legitimate alternatives**.

It is not useful to fabricate many nonsense configurations merely to increase `N`.

That issue is explicitly addressed in the misuse section.

## 16. Sample length `T`

The source notes that CSCV evaluates half-samples of size `T/2`, while the actual research process
may use `T` observations.

It therefore says `T` should be chosen with the size of the actual selection/design history in
mind.

The exact prescription in the paper should not be copied blindly into a different temporal design.

## 17. Full-trial disclosure is mandatory

This is one of the strongest governance lessons in the paper.

### SOURCE CLAIM

Researchers must provide **the actual trials conducted**.

If failed trials are hidden:

- relative OOS ranks are biased;
- PBO is underestimated;
- the diagnostic becomes falsely reassuring.

The paper explicitly analogizes this to dropping unsuccessful subjects from a medical trial.

### SOURCE CLAIM — do not pad with deliberately bad strategies

The opposite manipulation is also invalid.

Adding configurations that were obviously doomed to fail makes a favored model appear stronger.

The authors say such configurations should never have been included as reasonable research
alternatives in the first place.

### Guided searches

For an optimization procedure where each iteration depends on previous results, the paper says the
columns of `M` should be the **final converged result of each guided search**, not every intermediate
step.

### PROJECT IMPLICATION

Future Trading Bot experiment governance should preserve:

- every genuine candidate family/configuration that was actually eligible for selection;
- the search path;
- which trials are independent terminal search outcomes versus intermediate optimizer states.

## 18. PBO does not test backtest correctness

This limitation is explicit and critical.

### SOURCE CLAIM

PBO/CSCV cannot detect whether the underlying backtests are wrong because of:

- incorrect transaction costs;
- using information unavailable at decision time;
- other flawed assumptions.

If the input backtests are wrong, PBO evaluates wrong inputs.

### PROJECT IMPLICATION

PBO sits **after**:

- causality/leakage controls;
- realistic cost modeling;
- correct fill/execution assumptions;
- data-integrity validation.

It cannot replace them.

## 19. Structural-break limitation

### SOURCE CLAIM

PBO only sees structural breaks that exist inside the available dataset.

If all historical data belong to one regime and a new regime appears later, PBO cannot protect the
strategy from that future change.

### PROJECT IMPLICATION

Even an excellent PBO result cannot establish future robustness.

Prospective paper trading remains a separate and stronger evidence class.

## 20. High PBO does not necessarily mean every strategy is bad

The source gives an important edge case.

If all `N` strategies are strong and have similar Sharpe ratios, no one configuration may reliably
dominate the rest.

PBO can therefore be high even though the family contains skillful strategies.

### RESEARCH DIRECTOR INTERPRETATION

PBO evaluates the **selection problem**:

> Can we reliably identify the superior configuration?

It is not simply:

> Is this strategy family profitable?

This distinction is crucial.

## 21. Do not optimize PBO

This is arguably the strongest misuse warning in the paper.

### SOURCE CLAIM

CSCV/PBO must **not** become the objective function used to search for the optimal strategy.

Using an anti-overfitting diagnostic to optimize configurations simply creates another layer of
overfitting.

The authors explicitly invoke the principle that once a measure becomes a target, it stops being a
good measure.

### PROJECT RULE CANDIDATE

PBO should be a **diagnostic after a candidate-generation/selection process has been defined**, not a
score that Claude or an optimizer tries to maximize/minimize.

## 22. Practical application — experiment design

The paper demonstrates the method using a deliberately simple monthly seasonal trading rule.

Parameters:

- Entry day: 1–22;
- Holding period: 1–20;
- Stop loss: 0–10;
- Side: long/short.

Total configurations:

**8,800**

Historical series:

**1,000 daily prices**, approximately four years.

The underlying synthetic process lets the authors know whether a real effect exists.

## 23. Practical application — Example 1: pure random walk

The first price series is generated from a random walk with no true seasonal signal.

Optimization nevertheless finds an apparently strong configuration.

Reported optimal configuration:

- Entry day = 11;
- Holding period = 4;
- Stop loss = -1;
- Side = long.

Reported annualized Sharpe ratio:

**1.27**

Reported PSR-stat:

**2.83**

The paper notes that conventional interpretation would make the backtest look statistically strong.

### CSCV result

The visual/textual analysis reports approximately:

- **53%** of selected OOS Sharpe ratios below zero;
- **PBO = 55%**;
- no OOS stochastic dominance from the optimized selection procedure.

### SOURCE CONCLUSION

The apparently attractive backtest was generated from noise and CSCV correctly diagnoses a serious
selection-overfitting problem.

## 24. Practical application — Example 2: true seasonal effect injected

The second synthetic series is again a random walk, but the authors shift the first five random
observations of each month upward by approximately one quarter of a standard deviation.

This creates a real monthly seasonal effect.

Reported optimal configuration:

- Entry day = 1;
- Holding period = 4;
- Stop loss = -10;
- Side = long.

Reported annualized Sharpe ratio:

**1.54**

This is intentionally similar in magnitude to the spurious first example.

### CSCV result

Reported approximately:

- **13%** of OOS Sharpe ratios below zero;
- **PBO = 13%**;
- optimized OOS distribution clearly dominates the broader alternative distribution.

### CORE LESSON

A high IS Sharpe ratio by itself does not distinguish:

- a noise-mined configuration;
- a genuine effect.

The structure of OOS rank consistency across the candidate set contains additional information.

## 25. Interesting source tension: the 5% threshold

Section 3.1 says that, following customary hypothesis-testing practice, one possible rule would be to
reject models with estimated PBO above 0.05.

Yet the practical application later describes the **13% PBO** true-seasonality example as correctly
recognized/valid in the sense that overfitting inflation is relatively small.

### RESEARCH DIRECTOR INTERPRETATION

The paper itself does not support treating `PBO <= 5%` as a universal hard gate.

Astra should review this tension before any project threshold is ever frozen.

## 26. PBO versus probability of loss

This distinction deserves explicit preservation.

A low PBO only says:

> the IS-selection procedure tends to retain relative ranking OOS.

It does not say:

> the selected strategy makes money OOS.

The paper explicitly notes that PBO may be near zero while OOS probability of loss is high.

Therefore:

- PBO is about **selection overfit**;
- probability of loss is about **absolute OOS economics**.

Trading Bot would need both kinds of information.

## 27. PBO versus Sharpe significance

The paper connects PBO with earlier work on:

- Probabilistic Sharpe Ratio (PSR);
- minimum track record length;
- Deflated Sharpe Ratio.

But it addresses a different issue.

A strategy can have:

- apparently statistically significant Sharpe;
- yet high probability that the selected configuration is overfit.

This is exactly what the first synthetic example demonstrates.

### PROJECT IMPLICATION

No single metric should serve as the project's "truth score."

At minimum, future evidence may need separate controls for:

- absolute economics;
- uncertainty of performance estimate;
- multiplicity/selection;
- selection degradation;
- robustness;
- realistic costs;
- prospective behavior.

## 28. What this source does NOT prove

LIB-018 does not prove:

- that CSCV is the best validation method for every trading problem;
- that PBO alone establishes robustness;
- that low PBO means a backtest is causally correct;
- that low PBO implies profitability;
- that low PBO protects against future regime change;
- that a 5% PBO threshold is universally correct;
- that `S = 16` should always be used;
- that every candidate configuration should be enumerated blindly;
- that iterative research is forbidden in all forms;
- that protected evaluation or prospective paper testing is unnecessary;
- anything about BTC alpha;
- anything about signal weights;
- anything about entries/exits for Trading Bot.

## 29. Relation to the Owner's iterative-development philosophy

This source needs careful interpretation.

### What it strongly supports

- log every legitimate search outcome;
- account for configuration-selection multiplicity;
- do not hide failed trials;
- constrain candidates to theoretically reasonable alternatives;
- distinguish selection diagnostics from backtest correctness;
- do not optimize the diagnostic itself;
- expect apparent winners to degrade OOS;
- do not trust high development Sharpe merely because it looks impressive.

### What it does not directly prohibit

The formal framework does not say that a project may never:

- learn from an exposed development sandbox;
- improve implementation bugs;
- redesign architecture based on development evidence;
- conduct hypothesis-driven iteration.

What it does imply is that such adaptation consumes evidentiary independence and must be recorded as
part of the research/search process.

### RESEARCH DIRECTOR INTERPRETATION

This fits a stage-based development model better than a simplistic:

> one backtest only, then stop forever.

But once a dataset is repeatedly used to guide design, its results are development evidence rather
than independent confirmation.

## 30. Relation to Trading Bot experiment design

Potential later uses, if scientifically appropriate:

### Development search ledger

Store every legitimate candidate/configuration/search outcome.

### Synchronized performance matrix

Future candidate comparisons could preserve per-candle/per-period return series sufficient for
selection-overfit diagnostics.

### Diagnostic package

For a frozen candidate-selection stage, possible outputs could include:

- PBO;
- OOS-loss probability;
- IS-vs-OOS degradation;
- stochastic dominance;
- trial count/search provenance.

### Hard separation from other controls

PBO must not substitute for:

- causal feature tests;
- phase-bounded I/O;
- transaction cost/slippage realism;
- fill modeling;
- structural-break analysis;
- protected evaluation;
- future paper trading.

## 31. Potential concern for future Astra review — dependent combinations

CSCV generates many logits from overlapping recombinations of the same underlying observations.

The paper presents a binomial-style standard-error intuition based on the number of generated logits.

### RESEARCH DIRECTOR QUESTION

Because CSCV combinations share underlying data, should those logits be treated as effectively
independent for uncertainty calculations?

The source does not fully resolve this question in the main paper.

This is not a rejection of CSCV; it is a point for Astra/statistical review before using nominal
precision figures literally.

## 32. Source inconsistencies / ambiguities to preserve

### A. Median versus mean in conclusion

The formal definition and most of the paper define PBO using the IS winner falling below the OOS
**median** rank.

The conclusion contains wording that says the optimal IS strategy "underperforms the mean OOS."

This appears inconsistent with the formal definition.

Do not silently rewrite the source; use the formal definition if implementation is later considered,
and flag the prose discrepancy.

### B. Figure 3 PBO percentage

Figure 3 displays:

`ProbOverfit = 0.04`

which naturally reads as 4%.

The accompanying prose states:

"PBO of 0.04%."

These are not numerically identical.

Preserve the ambiguity; do not use this example to calibrate a numerical threshold.

### C. 5% suggestion versus 13% "valid" example

The paper offers 5% as a customary possible rejection threshold, yet later presents a 13% PBO example
as having relatively small overfitting and being correctly recognized as valid.

This argues against extracting a universal binary threshold from the paper.

## 33. Durable project knowledge retained from LIB-018

The following points should survive into final cross-source synthesis:

1. **Backtest search multiplicity is part of the evidence.**
2. **The configuration-selection process can overfit even when the chosen IS Sharpe looks highly
   significant.**
3. **PBO measures rank degradation of the IS winner relative to the tested alternatives OOS.**
4. **CSCV is one model-free, non-parametric implementation, not the only possible implementation.**
5. **All legitimate trials must be preserved; hiding failures biases PBO downward.**
6. **Padding the trial set with obviously bad strategies is also invalid.**
7. **For guided searches, terminal search outcomes should be distinguished from intermediate
   optimizer steps.**
8. **PBO does not test whether the backtest itself is causally/cost-wise correct.**
9. **PBO cannot protect against structural breaks absent from the historical sample.**
10. **Low PBO does not imply positive OOS performance.**
11. **High PBO does not necessarily mean every candidate is unskilled; it can mean the selector
    cannot reliably distinguish similar strong candidates.**
12. **PBO must never become the optimization objective.**
13. **Selection-quality diagnostics should be separate from absolute economics.**
14. **A high IS Sharpe threshold is not protection against overfitting.**
15. **Protected/future evidence remains necessary for questions PBO cannot answer.**
16. **The paper's formal object is strategy-selection overfit, not every possible form of model
    calibration.**

## 34. Questions for Astra at final corpus review

1. Is CSCV appropriate at all for our future BTC candidate-selection process, given overlapping
   horizons and serial dependence?
2. If used, how should `S` be chosen from the target holding horizon and temporal dependence rather
   than copied as 16?
3. How should effective trial count be defined when candidate architectures share components or
   arise from guided search?
4. How should we prevent a curated candidate set from understating the true search burden?
5. Should intermediate human/AI architecture redesigns count as separate hypothesis families even
   when they are not columns in one CSCV matrix?
6. What uncertainty should be attached to PBO when combinatorial splits are strongly dependent?
7. Should PBO be used only diagnostically after a development selection round, while protected
   evaluation remains untouched?
8. How should PBO interact with Deflated Sharpe Ratio rather than duplicate it?
9. Does the paper's critique of hold-out justify changing our protected-evaluation design, or does it
   address a different problem?
10. What threshold, if any, is justified given the paper's own tension between a suggested 5% rule
    and its 13% positive example?
11. Should probability of OOS loss and selection stochastic dominance be mandatory companion metrics
    whenever PBO is reported?
12. How should candidate-generation theory/professional priors be documented so PBO cannot be gamed
    by adding/removing configurations?

## 35. Final source disposition

`REVIEWED`

Reason:

- all 34 PDF pages reviewed;
- complete main text read;
- all 13 figures visually inspected;
- formal definitions and CSCV algorithm reviewed;
- practical examples reviewed;
- design and application limitations reviewed;
- misuse warnings preserved;
- source inconsistencies documented;
- project implications kept separate from source claims.

No Trading Bot strategy, signal weight, System G2 design, market experiment or real/paper order is
authorized by this source.
