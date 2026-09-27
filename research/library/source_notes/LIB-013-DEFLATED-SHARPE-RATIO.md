# LIB-013 — The Deflated Sharpe Ratio — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `deflated-sharpe.pdf`  
Drive file id: `1l7JxyZdx1_9go_JcyPi68-bv8izoOcKV`  
Local corpus id: `LIB-013`

## 1. Source identity

**Title:** *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality*  
**Authors:** David H. Bailey; Marcos López de Prado  
**First version:** 2014-04-15  
**Version studied:** 2014-07-31  
**Publication note in file:** Journal of Portfolio Management, forthcoming, 2014  
**Artifact type:** methodological research paper  
**Project classification:** RESEARCH_METHODOLOGY  
**Evidence tier:** A

The accessible PDF contains 22 pages including references and exhibits.

Complete review included:

- abstract and introduction;
- all methodological sections;
- numerical example;
- conclusions;
- all three appendices;
- all four exhibits;
- bibliography;
- full visual inspection of every PDF page to verify formulas, graphs and layout against the text extraction.

No external source was used to fill gaps in this paper.

## 2. Research problem

The paper addresses a specific statistical problem:

> observed Sharpe ratios are systematically inflated when researchers search across many strategy
> variants and report only the best-looking result.

The authors identify two main inflation mechanisms relevant to their proposed statistic:

1. **selection bias / multiple testing**;
2. **non-Normal return distributions**, including skewness and kurtosis effects on Sharpe-ratio
   uncertainty.

Their proposed solution is the **Deflated Sharpe Ratio (DSR)**.

The paper is not primarily about:

- discovering alpha;
- choosing indicators;
- execution;
- BTC;
- portfolio construction.

It is about assessing whether a selected Sharpe ratio remains statistically convincing after
accounting for the research process that produced it.

## 3. Multiple testing

### SOURCE CLAIM

Suppose many candidate strategies are tested on the same data.

Even if every individual test uses the same nominal false-positive threshold, the probability that
**at least one invalid strategy looks significant** rises as the number of trials increases.

Therefore a result cannot be interpreted correctly without knowing how much searching occurred
before that result was selected.

### Core implication

A backtest is not scientifically interpretable in isolation from its **search history**.

The paper treats the number of tested alternatives as part of the evidence itself.

### Project relevance

For Trading Bot, a future development process must retain an audit trail of:

- strategy variants;
- parameter trials;
- signal combinations;
- rejected candidates;
- meaningful manual changes prompted by prior results.

Deleting failed trials from the record would make later statistical evidence appear stronger than it
really is.

## 4. Selection bias

### SOURCE CLAIM

Selection bias arises when only favorable outcomes from multiple experiments are shown.

The paper discusses examples including:

- file-drawer effects;
- publication bias;
- survivorship bias;
- self-selection;
- backfilled manager histories.

The common structure is that the decision-maker does not observe the full search process and
therefore underestimates the true false-positive probability.

### Project relevance

A future Trading Bot research ledger should preserve negative as well as positive outcomes.

A candidate strategy that survives a large hidden search is less persuasive than an equally good
candidate generated from a small, theory-constrained search.

## 5. Backtest overfitting

### SOURCE CLAIM

If enough strategy configurations are tested, random historical patterns will eventually produce a
strategy with apparently excellent performance.

Optimizing parameters to maximize historical performance can therefore fit noise rather than genuine
predictive structure.

The paper illustrates this with a coin-toss example: a rule can be engineered to explain a random
past sequence perfectly yet have no future predictive power.

### Important distinction

The authors explicitly separate backtest overfitting from structural breaks.

A strategy can fail out of sample even in a stable process simply because the selected historical
pattern was random.

### Project relevance

For Trading Bot:

- strong backtest P&L is not enough;
- higher Sharpe after more search is not automatically stronger evidence;
- research effort itself creates an evidentiary penalty.

## 6. Memory effects

### SOURCE CLAIM

The paper distinguishes processes in which random historical patterns are merely **diluted** by new
data from processes with **memory effects**, where extreme historical patterns can be actively
undone.

The authors argue that financial series often exhibit memory effects and that an overfit rule may
therefore perform worse than simply reverting to zero edge: it can systematically lose as the
historical pattern reverses.

### Limitation

This is a general methodological argument.

The paper does not demonstrate that every financial series, every strategy, or BTC specifically
exhibits the same degree or form of memory.

### Project relevance

Do not interpret poor out-of-sample performance after optimization solely as "the regime changed".

Overfitting to a transient pattern is a separate explanation that must be considered.

## 7. Holdout validation is not sufficient protection

### SOURCE CLAIM

Splitting data into in-sample and out-of-sample sets is useful but does **not** by itself solve
multiple-testing overfit.

Why:

if the researcher repeatedly tries new models and repeatedly checks the holdout, eventually an invalid
model can pass that holdout by chance.

The holdout procedure then ceases to behave like a single untouched independent test.

### Project relevance

This is highly important for Trading Bot.

A supposedly "protected" evaluation period loses evidentiary independence if:

- we inspect the result;
- modify the system because of it;
- retest;
- repeat until it passes.

Therefore the label `OOS` is not enough.

What matters is whether that data remained **unexposed to adaptive decision-making**.

## 8. Probability of Backtest Overfitting versus DSR

The paper references the Probability of Backtest Overfitting (PBO) as a separate approach.

### SOURCE CHARACTERIZATION

PBO:

- evaluates whether a strategy-selection process tends to choose candidates that underperform
  out of sample;
- is non-parametric;
- can be applied to performance statistics beyond Sharpe;
- requires richer information about the candidate set.

DSR instead provides a **parametric correction focused on Sharpe-ratio significance**.

### Project implication

These tools answer related but not identical questions.

DSR should not be treated as a universal replacement for:

- causal simulation;
- protected evaluation;
- realistic costs;
- PBO or other search diagnostics.

## 9. Expected maximum Sharpe under multiple trials

A central mathematical insight of the paper is that even when a strategy class has no genuine
positive skill, the **maximum observed Sharpe** rises as more independent candidates are tested.

The paper approximates the expected maximum Sharpe across `N` independent trials using:

- the mean Sharpe across trials;
- the variance of Sharpe estimates across trials;
- an Extreme-Value-Theory approximation involving Normal quantiles and the Euler-Mascheroni
  constant.

### SOURCE CLAIM

The expected maximum increases when:

- `N`, the number of independent trials, increases;
- the cross-trial variance of Sharpe estimates increases.

Therefore a fixed Sharpe hurdle is inappropriate when comparing discoveries generated by very
different amounts of search.

### Project relevance

A future Trading Bot result such as:

`Sharpe = 1.5`

cannot be interpreted without context.

The meaning differs dramatically between:

- one predeclared specification;
- hundreds of related configurations;
- thousands of aggressively optimized combinations.

## 10. The Deflated Sharpe Ratio

### SOURCE DEFINITION

The DSR is built as a Probabilistic Sharpe Ratio in which the null/rejection threshold is raised to
reflect the multiplicity of trials.

Instead of asking only:

> Is the selected strategy's Sharpe above zero?

the procedure effectively asks:

> Is the selected Sharpe high enough to exceed what we would reasonably expect to see as the best
> result from this research search, after accounting for sampling uncertainty and non-Normal
> returns?

### Inputs used by DSR

The paper's DSR depends on information about the selected strategy and the search process.

Selected-strategy inputs include:

- estimated Sharpe ratio;
- sample length;
- return skewness;
- return kurtosis.

Search-process inputs include:

- number of **independent** trials;
- variance of Sharpe ratios across trials.

### Key conceptual point

A conventional Sharpe ratio summarizes return/risk from one observed series.

DSR incorporates information that conventional Sharpe ignores:

- how much searching occurred;
- how heterogeneous the tested Sharpe ratios were;
- whether the selected return distribution is non-Normal;
- how long the track record is.

## 11. Numerical example in the paper

The authors construct an example of a Treasury seasonality researcher.

The strategist tries multiple combinations involving:

- pre-auction periods;
- post-auction periods;
- tenors;
- holding periods;
- stop losses;
- related configuration choices.

He finds many configurations with annualized Sharpe around 2 and a selected one with Sharpe 2.5
over five years of daily observations.

The example supplies:

- `N = 100` independent trials;
- variance of tested Sharpe ratios = `1/2`;
- `T = 1250`;
- skewness `-3`;
- kurtosis `10`.

### SOURCE RESULT

After deflation, the paper obtains approximately:

`DSR = 0.9004`

which is below a 95% confidence threshold.

The selected Sharpe therefore does not qualify as a legitimate 95%-confidence discovery under the
authors' framework.

The paper further notes:

- with only `N = 46` independent trials, the DSR would be about `0.9505`;
- if returns were Normal, the same approximate confidence could tolerate more trials
  (`N = 88` in the example).

### Interpretation

A very high observed Sharpe can still be statistically weak when:

- the strategy was selected from many trials;
- returns are strongly non-Normal.

## 12. Non-Normality

### SOURCE CLAIM

Short samples and non-Normal returns can inflate apparent Sharpe significance.

DSR therefore incorporates:

- skewness;
- kurtosis;
- sample length.

### Project relevance

Trading Bot must not assume that a high Sharpe computed from a short, skewed or fat-tailed trade
history carries the same meaning as the same Sharpe from a long, well-behaved return series.

Crypto strategies are especially likely to require explicit distribution checks because the paper's
framework itself warns against Normality assumptions.

That last sentence is a Research Director relevance statement, not a BTC result from the paper.

## 13. Independent versus dependent trials

### SOURCE CLAIM

The `N` used in the expected-maximum-Sharpe correction should represent the number of
**independent** trials, not merely the raw number of configurations tested.

If `M` trials are highly redundant, then the effective number of independent trials is smaller than
`M`.

The appendix develops an approximate method based on average trial correlation.

At the intuitive extremes:

- perfectly redundant trials -> effective `N` approaches 1;
- mutually independent trials -> effective `N` approaches `M`.

### SOURCE CAUTION

The authors explicitly warn that average correlation has important limitations:

1. correlation measures only linear dependence;
2. when the number of tested strategies is large relative to sample length, the correlation matrix
   itself can be unstable/overfit.

They suggest information-theoretic redundancy measures as a deeper alternative.

### Project relevance

This matters directly for a future signal/parameter search.

Testing:

- EMA 19;
- EMA 20;
- EMA 21;

should not necessarily count as three fully independent discoveries.

But simply declaring them "one trial" is also unjustified.

The effective search burden needs a principled redundancy treatment.

## 14. When should testing stop?

The paper argues that multiple testing is useful but should be **planned rather than abused**.

A key statement is that investment theory, not computational power, should determine which
experiments are worth conducting.

The authors present the secretary-problem / 1/e stopping rule as a practical heuristic.

Conceptually:

1. define the set of theoretically justified configurations;
2. sample roughly 37% of them;
3. observe the best result;
4. then continue sequentially until finding the first candidate that exceeds all previously
   observed ones;
5. stop.

### Important limitation

This is presented as a rule of thumb derived from an optimal-stopping analogy.

It should not automatically become Trading Bot's exact search protocol.

### Durable lesson

The important source-grounded principle is:

> every extra trial has a statistical cost.

Therefore unlimited optimizer search is scientifically harmful even when compute is free.

## 15. Appendix A.1 — expected maximum Sharpe derivation

The first appendix derives the expected maximum of a set of independent Normal Sharpe estimates.

It standardizes the Sharpe estimates and applies an Extreme Value Theory approximation to the
maximum of standard Normal draws.

The resulting threshold is the basis for the multiplicity adjustment used later in DSR.

The appendix establishes that the expected best result rises systematically with search size.

## 16. Appendix A.2 — experimental verification

The authors numerically test the analytical expected-maximum approximation.

They simulate Normal trial Sharpe distributions across many:

- means;
- trial counts;
- variance settings.

The paper includes Python code for the experiment.

### SOURCE RESULT

The approximation error is largest for relatively small numbers of trials and declines as the number
of trials grows.

For one variance setting, the paper reports error below approximately 0.05 in the small-trial
region and about 0.006 by 1000 trials.

For a higher-variance case, the maximum error is around 0.11 and again converges toward zero as
trial count increases.

## 17. Appendix A.3 — estimating independent trials

The appendix provides an approximate mapping from:

- total trials `M`;
- average correlation between trial returns/results;

to an implied number of independent trials.

It also discusses practical instability when:

- `M` is large;
- sample length is short;
- the correlation matrix becomes ill-conditioned.

This is especially relevant to large parameter grids, where the raw number of configurations can
greatly exceed the effective number of independent observations.

## 18. Exhibits

### Exhibit 1

Shows the expected maximum Sharpe increasing as the number of independent trials grows.

Higher cross-trial Sharpe variance produces an even larger expected maximum.

### Exhibit 2

Shows simultaneously:

- the multiplicity-adjusted Sharpe rejection threshold rising with `N`;
- DSR falling as `N` rises.

This is the central visual intuition of the paper.

### Exhibits 3.1 and 3.2

Heat maps compare:

- analytical expected maximum Sharpe;
- numerically simulated expected maximum Sharpe.

They support the accuracy of the approximation used in the paper.

### Exhibit 4

Shows how the implied number of independent trials changes with:

- raw trial count;
- average correlation.

As redundancy rises, effective independent-trial count falls.

## 19. What DSR does well

According to this paper's framework, DSR directly addresses:

- selection from many tested alternatives;
- inflated expectations from picking the maximum;
- finite sample length;
- skewness;
- kurtosis;
- cross-trial Sharpe dispersion.

This makes DSR materially more informative than an unadjusted Sharpe ratio when a strategy was
chosen from a research search.

## 20. What DSR does NOT solve

The paper does not claim that DSR repairs:

- look-ahead bias;
- timestamp leakage;
- survivorship bias in the underlying market data;
- unrealistic fees;
- unrealistic fills;
- wrong slippage;
- wrong market-impact assumptions;
- bad execution simulation;
- regime changes;
- wrong economic theory;
- future structural breaks;
- poor data quality;
- hidden changes made after evaluation.

A high DSR cannot make a causally invalid backtest valid.

### Research Director implication

DSR belongs **after** causal data/execution correctness, not instead of it.

## 21. Important project rules derived from this source

These are Research Director implications grounded in LIB-013.

### 21.1 Maintain an append-only research ledger

For every future development search, preserve enough information to reconstruct:

- how many candidates were tried;
- what class they belonged to;
- which failed;
- which were selected;
- how similar/redundant the candidates were.

### 21.2 Do not report only the winner

The winning configuration cannot be evaluated scientifically without the candidate/search
distribution that generated it.

### 21.3 Count adaptive human changes too

The statistical search burden is not limited to automated grid search.

If humans repeatedly:

- inspect a backtest;
- alter a rule;
- rerun;
- keep improvements;

that is still adaptive search.

The exact effective-trial count may be hard to estimate, but the search cannot be treated as one
predeclared hypothesis.

### 21.4 Keep protected evaluation truly protected

Repeated use of an OOS block converts it into development information.

Calling it "test" or "OOS" does not preserve independence once its results influence subsequent
choices.

### 21.5 Prefer theory-constrained search

Before running alternatives, define a defensible reason for the search space.

More compute does not justify more hypotheses.

### 21.6 DSR is a diagnostic, not an optimization objective

Do not choose parameters because they maximize DSR.

Doing so would create another adaptive search around the diagnostic itself.

This specific prohibition is a Research Director application of the paper's multiple-testing logic.

## 22. Relation to the Owner's intended iterative development process

This paper does **not** imply that development must stop after one historical run.

What it clearly implies is that iterative learning has a statistical cost.

A stage-based interpretation compatible with the source is:

### Development

May be adaptive, but:

- every meaningful iteration is logged;
- development evidence is not called independent confirmation;
- the search space remains theory constrained.

### Evaluation

Must be materially less adaptive.

Once an evaluation result is inspected and used to modify the model, that dataset has contributed to
development and should not retain the same independent-evidence label.

### Prospective paper trading

Remains a stronger evidence class because it occurs after strategy freeze.

This staged interpretation is a Research Director governance application, not language stated
verbatim by the authors.

## 23. Relevance to Trading Bot signal weights

The paper does not tell us:

- which signals deserve high base weights;
- how to combine trend, cycles, volume or microstructure;
- what `peso2` should be;
- how much historical adjustment to permit.

Its relevance is indirect but crucial.

If future empirical calibration modifies signal weights, thresholds, relevance functions or
interaction rules after observing historical performance, those modifications contribute to the
research search burden.

Therefore:

> bounded empirical adjustment can be legitimate development, but it cannot be treated as free
> information.

## 24. What this source does NOT support

LIB-013 does not support:

- any BTC alpha claim;
- any signal family;
- any entry/exit rule;
- any timeframe;
- any risk percentage;
- any numerical signal weight;
- any specific acceptable Sharpe threshold for Trading Bot;
- a universal minimum DSR threshold for every stage;
- the claim that DSR alone proves a strategy is real;
- the claim that all iterative strategy development is invalid.

## 25. Limitations and assumptions

### 25.1 Sharpe-centric

DSR is designed around Sharpe-ratio inference.

Trading Bot may later care about additional quantities such as:

- expectancy;
- drawdown;
- calibration;
- directional forecast quality;
- tail losses;
- trade-level dependence.

DSR does not automatically solve multiplicity for every possible metric.

### 25.2 Independent-trial estimation is difficult

The effective `N` can be hard to infer when trials are highly correlated.

The paper itself acknowledges limitations of average-correlation approaches.

### 25.3 Distributional approximations

Parts of the expected-maximum framework rely on assumptions/approximations involving Sharpe
estimates and Extreme Value Theory.

### 25.4 Does not eliminate all model-selection bias

The paper presents a correction for major sources of performance inflation, not a complete guarantee
that the selected strategy generalizes.

### 25.5 No execution/economic validation

A statistically convincing Sharpe still requires a realistic and causal trading model.

## 26. Durable knowledge retained from LIB-013

The following points should survive into final corpus synthesis:

1. **Search history is part of the evidence.**
2. More trials mechanically increase the best Sharpe expected by chance.
3. Reporting only the winning backtest creates selection bias.
4. A holdout set does not remain protective under repeated adaptive reuse.
5. Backtest overfitting can occur without a structural break.
6. Financial memory effects may make overfit strategies particularly harmful out of sample.
7. DSR adjusts Sharpe significance for:
   - multiplicity;
   - cross-trial Sharpe variance;
   - sample length;
   - skewness;
   - kurtosis.
8. Effective independent trials matter more than raw configuration count.
9. Highly correlated strategies are redundant, but redundancy estimation is itself nontrivial.
10. Theory should constrain experiments before computation.
11. Every additional trial carries a false-positive cost.
12. DSR is an evidence diagnostic, not an alpha generator.
13. DSR does not repair leakage, cost errors or execution artifacts.
14. Development iteration can be allowed only if its adaptive nature remains explicit in the
    evidence hierarchy.
15. Protected evaluation loses independence when repeatedly used to guide changes.

## 27. Questions for Astra at final corpus review

1. What is the most defensible way to count effective independent trials in a mixed human + automated
   Trading Bot development process?
2. Should every material ruleset revision count as one trial, or should revisions be grouped into
   correlated research families?
3. Which future metrics besides Sharpe need analogous multiplicity controls?
4. At what stage should DSR be reported:
   - development;
   - candidate selection;
   - protected evaluation;
   - all of them with different interpretation?
5. How should DSR interact with PBO/CSCV rather than duplicate them?
6. How should overlapping trade outcomes and serial dependence affect Sharpe/DSR computation?
7. Should adaptive signal-weight calibration consume a formal research-budget ledger?
8. How should manually inspected replay/autopsy results be counted as information exposure?
9. Is the secretary-problem stopping rule useful as an actual governance mechanism here, or only as
   an intuition that testing has a cost?
10. What minimum information must be persisted for future DSR to be reconstructible rather than
    estimated after the fact?

## 28. Final source disposition

`REVIEWED`

Reason:

The complete 22-page accessible PDF was studied, including:

- all main sections;
- mathematical construction;
- numerical example;
- appendices;
- source code snippet;
- all exhibits;
- references;
- full visual page verification.

Source claims were separated from Research Director interpretation.

No outside source was used to supplement the paper.

No Trading Bot strategy, signal weight, parameter, System G2 design or market experiment is
authorized by this dossier.
