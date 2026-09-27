# LIB-017 — Mathematical Appendices to “The Probability of Backtest Overfitting” — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `ssrn-2568435.pdf`  
Drive file id: `1X1OtPeJTP4jyVTQYhh0L2cOZRkdcTt3B`  
Local corpus id: `LIB-017`  
Physical pages: **8**  
Raw file size: **573,517 bytes**  
SHA-256: `1530b9463e6e9f72366b93cfd2a27519b9d28e390106293bfe67863683085ad3`

## 1. Source identity

Title:

**Mathematical Appendices to “The Probability of Backtest Overfitting”**

Authors:

- David H. Bailey
- Jonathan M. Borwein
- Marcos López de Prado
- Jim Zhu

The document points to:

- source code at `www.QuantResearch.info`;
- the main paper at SSRN abstract `2326253`;
- this appendix at SSRN abstract `2568435`.

The local PDF metadata shows a creation/modification date of **2015-02-22**.

Artifact type:

**Academic / mathematical supplement**

Project classification:

`RESEARCH_METHODOLOGY`

Evidence tier in the current registry:

`A`

Important scope point:

This is **not an independent empirical trading study**. It is a mathematical/simulation supplement
whose purpose is to test and explain the behavior and accuracy of the PBO/CSCV methodology discussed
in the associated main paper.

The associated main paper was **not used to fill gaps in this dossier**. This dossier is grounded in
the eight-page appendix itself.

## 2. Complete document structure

The source contains two main sections.

### A.1 — Test Cases

Three synthetic cases are constructed:

1. Full overfit
2. High overfit
3. Low overfit

### A.2 — Accuracy of the Test

The accuracy of CSCV's estimate of Probability of Backtest Overfitting is evaluated by:

1. Monte Carlo simulation;
2. Extreme Value Theory;
3. comparison of CSCV, Monte Carlo and EVT across a grid of test cases.

The document also contains:

- one Python snippet for Monte Carlo estimation;
- one Python snippet for EVT-based numerical integration;
- one final table comparing methods.

## 3. Core object being studied

The source considers a performance matrix `M` with:

- `T` rows representing observations;
- `N` columns representing alternative strategy trials/configurations.

The synthetic design usually creates:

- `N - 1` trials with true Sharpe ratio 0;
- one special trial whose Sharpe ratio is varied.

The strategy-selection procedure selects the trial with the highest **in-sample** Sharpe ratio.

The quantity of interest is whether that selected in-sample winner subsequently performs **below the
median of the candidate trials out of sample**.

The source denotes the Probability of Backtest Overfitting by `φ`.

### SOURCE CLAIM

A high `φ` means that the strategy selected as optimal in sample is frequently inferior to the
median candidate out of sample.

This is a **selection-risk** concept.

It is not simply a measure of whether one strategy has a negative raw return.

## 4. A.1.1 — Full-overfit test case

### Construction

The source sets:

- `T = 1000`;
- `N = 100`.

For every trial:

1. draw `T` observations from a standard Normal distribution;
2. re-scale and re-center the sample so its Sharpe ratio is 0.

All 100 candidates therefore have the same true/null Sharpe ratio.

### SOURCE CLAIM

If the researcher chooses the strategy with the highest in-sample Sharpe ratio, there is no genuine
reason for that selected candidate to outperform the median out of sample.

The source reports:

`φ -> 1`

in this case.

In other words, the in-sample "winner" is almost certainly a selection artifact.

### Robustness observations stated in the source

Increasing:

- `T` from 1000 to 2000;

or:

- `N` from 100 to 200

does not materially alter the full-overfit conclusion because all candidates remain equally null.

### Research Director interpretation

This is a clean demonstration of a fundamental point:

> selecting the best result from many equally valueless alternatives can manufacture an apparently
> superior in-sample strategy even when no true superior strategy exists.

This is directly relevant to any future Trading Bot process that tries many combinations,
thresholds or variants.

## 5. A.1.2 — High-overfit test case

### Construction

Again:

- `T = 1000`;
- `N = 100`.

But now:

- `N - 1` candidates have Sharpe 0;
- one candidate is re-scaled/re-centered to Sharpe 1.

There is therefore one genuinely better candidate.

### SOURCE CLAIM

Even though one candidate has a positive true Sharpe ratio, random in-sample variation among many
null candidates can still cause the selection procedure to choose a false winner.

The source reports PBO approximately:

**0.7–0.8**

for `T = 1000, N = 100`.

### Effect of increasing the number of trials

When `N` is increased to 200, the source reports `φ` around:

**0.75–0.85**

The stated explanation is that more tried alternatives increase the chance that one null candidate
looks unusually good in sample.

The authors explicitly connect this to the importance of reporting the possibilities actually tried.

### Effect of increasing the sample size

When `T` increases to 2000, the source reports PBO falling to approximately:

**0.4–0.5**

The stated explanation is that more observations make in-sample performance more informative.

### Research Director interpretation

A real signal can exist and the research process can **still select the wrong strategy** if the
candidate search is sufficiently broad relative to the amount of data.

This is highly relevant to Trading Bot because "there is some edge in the design space" and "the
configuration we selected has that edge" are different scientific claims.

## 6. A.1.3 — Low-overfit test case

### Construction

Again:

- `T = 1000`;
- `N = 100`.

But the special candidate has:

`Sharpe = 2`

while the remaining candidates have Sharpe 0.

### SOURCE CLAIM

Because the genuinely superior candidate is now more strongly separated from the null alternatives,
the strategy-selection procedure is more likely to identify it correctly in sample.

The source reports PBO approximately:

**0.1–0.2**

for `T = 1000, N = 100`.

### Increasing search breadth

At `N = 200`, reported PBO rises to approximately:

**0.2–0.3**.

### Increasing sample size

At `T = 2000`, reported PBO falls to approximately:

**0–0.04**.

### Research Director interpretation

Selection risk depends jointly on at least:

- true signal separation;
- amount of data;
- number of alternatives searched.

A strong signal is easier to distinguish from noise, but an unnecessarily large search still makes
selection harder.

## 7. Regression analogy

The authors draw an analogy with overfitting in regression.

A regression design matrix has:

- `T` observations;
- `N` explanatory factors.

The source notes that degrees of freedom behave roughly like:

`T - N`.

Increasing `T` gives the estimation problem more information.

Increasing `N` increases the flexibility/search burden.

### Source-level conclusion

The observed behavior of PBO is consistent with the familiar intuition that:

- larger samples reduce overfitting risk;
- larger model/search spaces increase overfitting risk.

### Limitation

This is an analogy.

The appendix does not claim that every strategy-selection process is literally equivalent to an
ordinary regression with exactly `T-N` effective degrees of freedom.

## 8. A.2 — What “accuracy” means here

The source asks whether CSCV's estimated PBO actually corresponds to the probability that the
strategy selected in sample will perform below the median candidate out of sample.

It evaluates this using two independent benchmark procedures:

1. direct Monte Carlo experiments;
2. an Extreme Value Theory approximation.

This is the central purpose of the appendix.

## 9. A.2.1 — Monte Carlo accuracy benchmark

The source generates:

**1,000 independent matrices `M`**

for each test case.

For the stated benchmark case, each matrix has order:

`1000 x 100`

The sample is split into equal in-sample and out-of-sample halves.

For each experiment:

1. estimate Sharpe ratios in sample;
2. select the candidate with maximum in-sample Sharpe;
3. evaluate its out-of-sample Sharpe;
4. compare that out-of-sample Sharpe with the median out-of-sample Sharpe across candidates;
5. count the experiment as overfit when the selected candidate falls below that median.

The resulting proportion is treated as a direct Monte Carlo estimate of the relevant overfitting
probability.

### Python code

The source includes Python code implementing this experiment.

The code:

- creates Gaussian samples;
- re-scales and re-centers them to target Sharpe ratios;
- computes in-sample and out-of-sample Sharpe ratios;
- selects the in-sample maximum;
- counts whether that winner underperforms the OOS median.

### Important limitation

The code is demonstration code tied to the synthetic assumptions of the test.

It should **not** be copied into Trading Bot as a production overfitting validator without checking
all assumptions and the later project data structure.

## 10. A.2.2 — Extreme Value Theory benchmark

The second benchmark uses Extreme Value Theory.

### SOURCE CLAIM

When many alternative configurations are backtested and the maximum in-sample Sharpe is selected,
the problem naturally involves the distribution of an extreme statistic.

The source states that Sharpe-ratio estimates are asymptotically Gaussian under the referenced
conditions.

For the maximum of many independent Gaussian variables, the document invokes the
Fisher-Tippett-Gnedenko result and approximates the distribution of the maximum by a **Gumbel
distribution**.

### Gumbel parameterization

The appendix writes the mean and standard deviation of the maximum distribution as:

- expected maximum = `α + γβ`;
- standard deviation = `βπ / sqrt(6)`;

where `γ` is the Euler-Mascheroni constant.

It then fits `α` and `β` by method of moments.

### PBO decomposition

The source decomposes PBO into:

`φ = φ1 + φ2`

with two probability regions:

- one associated with selecting a null strategy instead of the genuine positive-Sharpe candidate;
- one associated with even the positive-Sharpe candidate producing sufficiently extreme in-sample
  performance that its constrained OOS performance falls below the median.

The appendix supplies the corresponding integrals and a Python implementation of the numerical
integration.

### Research Director interpretation

The EVT section makes an important methodological point:

> the best result among many noisy alternatives is itself an extreme-value object.

Therefore the selected maximum cannot be interpreted using the same intuition as a randomly chosen
single backtest.

## 11. A.2.3 — Empirical accuracy study

The final comparison varies:

- true Sharpe of the special candidate: `0, 1, 2, 3`;
- sample length `T`: `500, 1000, 2500`;
- number of candidate trials `N`: `10, 50, 100, 500`.

For each combination:

- Monte Carlo probability is computed from 1,000 experiments;
- EVT probability is computed analytically/numerically;
- CSCV PBO is computed on 1,000 randomly generated matrices, producing a mean and standard deviation.

## 12. Final accuracy results reported by the source

### Monte Carlo vs EVT

The source reports that Monte Carlo and EVT results are close.

Maximum absolute deviation:

**4.2 percentage points**

### CSCV vs EVT

Across the tested parameter combinations, the source reports:

- mean absolute error: **2.1 percentage points**;
- standard deviation of absolute error: **2.9 percentage points**;
- median error: **0.7 percentage points**;
- 5th percentile error: **0%**;
- 95th percentile error: **8.51 percentage points**;
- maximum absolute error: **9.9 percentage points**.

The largest error occurs at:

`SR_case = 3, T = 500, N = 500`

where:

- CSCV estimates PBO = **24.7%**;
- EVT estimates PBO = **14.8%**.

The appendix characterizes this error as conservative.

The source states that there is only one tested case in which CSCV underestimates PBO, and that
underestimation is only **0.1 percentage points**.

### SOURCE CONCLUSION

Within the synthetic experiments studied in this appendix:

> CSCV provides accurate PBO estimates, with relatively small errors that are mostly conservative.

That conclusion must remain bounded to the conditions actually studied.

## 13. What the final table demonstrates

Table 1 makes three qualitative relationships visually clear.

### 13.1 More trials increase selection risk

Holding signal strength and sample length roughly fixed, increasing `N` generally raises PBO.

### 13.2 More observations reduce selection risk

Holding signal strength and search breadth roughly fixed, increasing `T` generally lowers PBO.

### 13.3 Stronger genuine performance separation lowers selection risk

Holding `T` and `N` fixed, increasing the special candidate's true Sharpe from 0 to 1, 2 or 3
dramatically reduces PBO.

These are properties of the source's controlled simulation environment.

## 14. Assumptions visible in the appendix

The accuracy demonstrations rely on deliberately simplified synthetic constructions.

Important visible assumptions include:

- Gaussian random draws;
- candidates explicitly re-scaled/re-centered to fixed full-sample Sharpe ratios;
- one special candidate against many null candidates;
- symmetric in-sample/out-of-sample split in the benchmark derivation;
- independence assumptions used in the EVT maximum-of-Gaussians argument;
- Sharpe ratio as the performance-selection statistic;
- a candidate set whose tested alternatives are explicitly known.

These assumptions make the appendix suitable for validating the mathematical behavior of the
method, but they are much cleaner than a real trading-research pipeline.

## 15. What this source does NOT demonstrate

This appendix does **not** show that CSCV/PBO is automatically accurate under every real financial
research process.

It does not directly validate the method under:

- strongly autocorrelated returns;
- overlapping trade outcomes;
- heterogeneous holding periods;
- fat-tailed/non-Gaussian strategy returns;
- highly dependent or near-duplicate candidate strategies;
- path-dependent strategy generation;
- human iterative research where the complete search history is unknown;
- changing market regimes;
- transaction-cost/model error;
- look-ahead leakage;
- incorrect point-in-time data;
- execution artifacts;
- adaptive stopping of the research process.

Some of these issues may be discussed by the associated main paper, but they are **not established
by this appendix alone**.

## 16. Relation to Trading Bot research governance

### 16.1 Search breadth is part of the experiment

The source provides strong methodological support for recording how many alternatives were actually
considered.

A result selected from:

- 5 deliberately justified candidates

is scientifically different from one selected from:

- hundreds of hidden variants.

### 16.2 More data does not erase unrestricted search

Increasing `T` helps, but the source shows that increasing `N` pushes risk in the opposite
direction.

Therefore:

> “we have lots of historical candles”

is not a license for an unlimited configuration search.

### 16.3 Genuine edge and correct model selection are separate problems

Even when one candidate truly has positive Sharpe in the synthetic experiment, a noisy selection
process can still choose the wrong candidate.

For Trading Bot this means we must distinguish:

1. whether some professional design contains useful information;
2. whether our development procedure correctly identifies it;
3. whether a selected configuration survives protected evaluation.

### 16.4 Complete experiment logging matters

The appendix explicitly notes that as the number of trials increases, reporting all possibilities
actually tested becomes important.

This supports an append-only research ledger for:

- configurations;
- thresholds;
- ablations;
- parameter alternatives;
- architecture variants.

Hidden failed variants would understate selection burden.

## 17. Relation to the Owner's iterative-development idea

This source does **not** prove that iterative development is invalid.

It proves something narrower and more useful:

> every additional alternative exposed to the same development evidence increases the selection
> problem unless the search is constrained and honestly accounted for.

A disciplined development sandbox can therefore coexist with this source if:

- adaptations are logged;
- search breadth is bounded where possible;
- development results are not mislabeled as independent confirmation;
- final protected evaluation is not repeatedly recycled;
- diagnostic tools such as PBO are not themselves optimized against.

The last point is especially important:

trying many architectures until one obtains a “good PBO” would simply create another search loop.

## 18. Relevance to future signal weights

This appendix provides **no evidence** for any particular trading signal or signal weight.

It does, however, constrain the future calibration process.

If Trading Bot later contains:

- base signal-family importance;
- bounded empirical modifier (`peso2`);
- thresholds;
- interaction rules;

then repeatedly searching all combinations of those values would create exactly the sort of
selection problem this source is designed to quantify.

Therefore the likely project implication is:

- derive structural choices primarily from professional/source knowledge;
- keep empirical degrees of freedom deliberately small;
- log every tested alternative;
- treat calibration search size as scientific debt.

No numeric search budget is authorized by this source alone.

## 19. PBO is not a substitute for causal correctness

A low PBO would not prove that a backtest is valid if the simulation contains:

- future leakage;
- unrealistic fills;
- wrong costs;
- data errors;
- bad timestamp alignment.

This follows from the fact that this appendix evaluates **strategy-selection overfit** in controlled
matrices, not the correctness of the underlying market simulator.

Therefore Trading Bot still requires independent safeguards for:

- point-in-time data;
- causal feature computation;
- execution realism;
- cost realism;
- regime robustness.

## 20. PBO is not a universal performance score

The appendix studies a specific question:

> how likely is an in-sample-selected winner to underperform the median alternative out of sample?

That is not identical to:

- expected future P&L;
- probability of profitability;
- Sharpe confidence interval;
- probability of ruin;
- forecast calibration;
- drawdown risk;
- execution quality.

PBO should therefore remain one diagnostic among several rather than the master objective of the
research programme.

## 21. Durable project knowledge retained from LIB-017

The following points are strong enough to preserve for final corpus synthesis:

1. Selecting the best backtest among many null alternatives can produce near-certain overfitting.
2. A genuinely superior candidate can still lose the in-sample selection contest to noisy null
   alternatives.
3. Increasing the number of tested alternatives increases selection-overfit risk.
4. Increasing the number of observations reduces selection-overfit risk.
5. Stronger true separation between the best candidate and the rest reduces selection-overfit risk.
6. The selected maximum among many candidate Sharpe ratios is naturally an extreme-value problem.
7. Under the appendix's synthetic assumptions, the maximum of Gaussian Sharpe estimates is modeled
   with a Gumbel distribution.
8. The appendix validates CSCV/PBO against both Monte Carlo and EVT benchmarks over a broad synthetic
   parameter grid.
9. Under those test conditions, CSCV's average absolute error versus EVT is reported at 2.1
   percentage points and is mostly conservative.
10. The accuracy result is conditional on simplified synthetic assumptions and should not be
    generalized automatically to every real market-research workflow.
11. Accurate accounting of the tested candidate set is scientifically important.
12. PBO measures selection overfit; it does not diagnose leakage, cost-model error, bad execution or
    regime instability.
13. PBO should be used as a diagnostic/governance tool, not an optimization target.
14. Future Trading Bot calibration should minimize unnecessary degrees of freedom and retain a
    complete trial ledger.

## 22. Questions for Astra at final corpus review

1. Under what dependence structure among Trading Bot variants would CSCV/PBO remain informative?
2. How should the project's effective number of trials be defined when variants share most of their
   logic?
3. How should iterative human reasoning be counted when not every idea becomes an executable
   configuration?
4. Can PBO be meaningfully applied to a complete-system architecture with correlated signal-family
   ablations, or only to more homogeneous candidate sets?
5. What minimum number of observations/trades would make PBO numerically meaningful for the future
   BTC system?
6. How should overlapping 4h outcomes alter the effective sample size or validation design?
7. Should PBO be used during the development sandbox, only at candidate-freeze time, or both?
8. How do we prevent repeated inspection of PBO itself from becoming another adaptive selection
   channel?
9. Which complementary diagnostics should sit beside PBO for non-normal returns and time dependence?
10. How should trial-ledger governance treat manual architecture changes derived from trade autopsy?

## 23. Final source disposition

`REVIEWED`

Reason:

The complete eight-page accessible PDF was reviewed, including:

- all test cases;
- all mathematical derivations visible in the source;
- both code snippets;
- EVT/Gumbel construction;
- full empirical accuracy discussion;
- final comparison table;
- full-page visual verification.

The source is retained as a **research-methodology supplement**, not as independent trading-alpha
evidence.

No Trading Bot strategy, signal weight, market parameter, System G2 design or real/paper trading
authorization follows from this document.
