# LIB-016 — “… and the Cross-Section of Expected Returns” — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `ssrn-2249314.pdf`  
Drive file id: `1I6jemQFT3mbMJDq8l9VIExhHq3WRrTi5`  
Local corpus id: `LIB-016`  
PDF pages: **101**  
Raw file size: **698,393 bytes**  
SHA-256: `ee2275c3409f3ccf3b83e3a3cc30c4c5c5f89ffa01f25fb55166a604c7ec3d9c`

## 1. Source identity

**Title:** *… and the Cross-Section of Expected Returns*  
**Authors:** Campbell R. Harvey, Yan Liu, Heqing Zhu  
**Manuscript date shown in source:** April 20, 2015  
**First SSRN posting shown in source:** April 11, 2013  
**Artifact type:** academic / research-methodology manuscript  
**Project classification:** RESEARCH_METHODOLOGY  
**Evidence tier:** A

The paper studies the statistical consequences of the very large number of proposed factors used to
explain the cross-section of expected stock returns.

Its core problem is not whether one particular factor has a large t-statistic in isolation, but:

> how should statistical evidence be evaluated when hundreds or thousands of related hypotheses have
> been tried, only a subset of attempts is observable, and publication incentives favor significant
> results?

The paper's main answer is that ordinary single-test significance thresholds are too permissive in
this setting.

## 2. Study coverage

The complete accessible PDF was reviewed.

Coverage included:

- abstract and introduction;
- search-process construction;
- factor taxonomy;
- all multiple-testing sections;
- FWER / FDR discussion;
- Bonferroni, Holm and BHY procedures;
- historical and projected adjusted thresholds;
- robustness to dependence;
- hidden / unpublished tests;
- structural correlation model;
- conclusion;
- the full multi-page factor list;
- bibliography;
- Appendix A — sampling procedure;
- Appendix B — unknown total number of tests;
- Appendix C — Bayesian framework;
- Appendix D — FDP-control method;
- Appendix E — FAQ;
- full-document visual scan of all 101 pages.

No outside source was used to fill gaps or reconcile the manuscript with later versions.

## 3. Central research question

The paper starts from the observation that finance had accumulated hundreds of proposed explanatory
factors.

If only one hypothesis were ever tested, a conventional significance rule might be reasonable.

But if researchers have tried:

- many candidate variables;
- many transformations;
- many specifications;
- many factors that were never published;

then the probability that some apparently impressive result occurs by chance increases sharply.

The paper therefore asks:

> what statistical hurdle should a newly proposed factor clear after accounting for the history of
> previous searches?

This is the durable methodological problem relevant to Trading Bot.

## 4. Factor search universe

### SOURCE CLAIM

The authors assemble **313 articles** studying cross-sectional return patterns.

The paper states that this set includes:

- **250 published articles**;
- **63 working papers**.

They catalogue **316 different factors**.

The source explicitly acknowledges that 316 is likely an **under-count** of the real number of
factors tested because:

- the search is concentrated on selected journals;
- working papers are sampled selectively;
- multiple variants may be represented by only one main version;
- failed factors are rarely published;
- industry "trade secrets" may never become public.

### RESEARCH DIRECTOR INTERPRETATION

The observed research record is not the same thing as the complete search process.

For Trading Bot, the analogue is direct:

the research ledger must include failed candidates, parameter variants and abandoned hypotheses.
Otherwise any later statistical confidence can be materially overstated.

## 5. Publication and search bias

The paper identifies several mechanisms that distort the observed evidence base.

### 5.1 Failed tests are hidden

A factor that fails to reach conventional significance is much less likely to appear in the
literature.

Therefore the published factor universe is selected toward large test statistics.

### 5.2 Replication is under-produced

The authors contrast financial economics with scientific fields in which direct replication studies
are more common.

They argue that finance has stronger incentives to publish **new factors** rather than replication
of known factors.

### 5.3 Cheap computation increases search capacity

The conclusion emphasizes that modern researchers can search vastly more specifications because
data and computation have become cheaper.

This increases the opportunity for accidental discoveries.

### PROJECT IMPLICATION

For Trading Bot, compute efficiency must never be treated as scientific permission to explore an
unbounded parameter/configuration space.

The number of effective attempts is part of the evidence.

## 6. Factor taxonomy

The paper divides the factor zoo into two broad groups.

### Common factors — 113 identified

These are intended to proxy for common sources of risk / common movements.

Subcategories:

- financial — 46;
- macro — 40;
- microstructure — 11;
- behavioral — 3;
- accounting — 8;
- other — 5.

### Firm characteristics — 202 identified

These are security-specific characteristics associated with the cross-section of expected returns.

Subcategories:

- financial — 61;
- microstructure — 28;
- behavioral — 3;
- accounting — 87;
- other — 24.

The paper's count/taxonomy is specific to cross-sectional equity asset-pricing research.

### RESEARCH DIRECTOR INTERPRETATION

The useful idea for Trading Bot is not to copy this taxonomy literally.

The relevant lesson is that a large feature universe contains **families of economically related
variables**, and several published variables can be proxies for the same underlying phenomenon.

Therefore raw feature count is not equivalent to independent information count.

## 7. Why single-test significance fails under multiplicity

Suppose each candidate is tested at a conventional significance level.

Even if every null hypothesis were true, enough repeated tests make false positives likely.

The paper distinguishes two broad error-control objectives.

### Family-Wise Error Rate — FWER

FWER controls the probability of making **at least one false discovery** among the family of tests.

This is strict.

### False Discovery Rate — FDR

FDR controls the expected fraction of false discoveries among the set of discoveries.

This is more permissive and can retain more power in large testing problems.

### SOURCE CAUTION

The paper does **not** claim that FWER or FDR is universally superior.

It reports both because the appropriate trade-off between false positives and false negatives depends
on the application.

## 8. Type I versus Type II error

The paper explicitly recognizes the trade-off:

- making the threshold stricter reduces false positives;
- making it stricter can also increase false negatives.

Therefore the scientific objective is not:

> eliminate every possible false discovery at any cost.

It is:

> control a chosen Type-I-error criterion while retaining as much discovery power as possible.

### PROJECT IMPLICATION

Trading Bot governance should not treat "never accept a false candidate" as the only scientific goal.

Overly conservative rules can also discard real signal.

The research process needs an explicit balance between:

- false edge discovery;
- missed genuine edge.

This is a conceptual lesson, not a numeric rule supplied for BTC.

## 9. Multiple-testing methods studied

The paper presents three principal adjustments.

### 9.1 Bonferroni

Controls FWER.

It applies a single-step multiplicity penalty based primarily on the number of tests.

The paper emphasizes that Bonferroni is easy to understand but usually conservative.

### 9.2 Holm

Also controls FWER.

It is a sequential / step-down method.

The paper notes that Holm is uniformly at least as powerful as Bonferroni in the relevant sense:
anything rejected by Bonferroni is also rejected by Holm, while Holm can reject additional
hypotheses.

### 9.3 Benjamini-Hochberg-Yekutieli — BHY

Controls FDR.

It is sequential and is designed to remain valid under general dependence among tests.

Compared with FWER procedures it can permit more discoveries because it targets the expected
proportion of false discoveries rather than the probability of any false discovery.

## 10. Demonstration example

The paper uses a hypothetical ten-test example.

Under ordinary single-test significance, all ten examples would be considered significant.

After multiplicity adjustment, substantially fewer survive:

- Bonferroni: 3;
- Holm: 4;
- BHY under the example's chosen FDR setting: 6.

### RESEARCH DIRECTOR INTERPRETATION

The number itself is illustrative.

The important lesson is that a result can look compelling under isolated evaluation while failing
when judged as one result selected from a broader search.

## 11. Growth of the factor zoo

### SOURCE CLAIM

The paper reports a sharp acceleration in factor production.

It states approximately:

- around one new factor per year in the early 1980–1991 period;
- around five per year in 1991–2003;
- around eighteen per year in the most recent nine-year period considered.

It reports **164 factors** discovered in the latest nine-year period, roughly double the **84**
discovered in all prior years represented in that comparison.

### PROJECT IMPLICATION

The effective prior probability that a newly generated feature represents a durable phenomenon
should not be treated as independent of the size of the research search space.

## 12. Main threshold results when published tests are treated as the universe

The paper first analyzes a deliberately optimistic case in which all relevant tests are assumed to
be observed (`M = R`).

This is explicitly described as unrealistic but useful as a **lower-bound / benchmark** exercise.

For the full observed factor sample, the paper reports that by 2012 approximately:

- Bonferroni threshold: **t ≈ 3.78**;
- Holm threshold: **t ≈ 3.64**;
- BHY under stricter FDR settings: around the mid-3 range;
- BHY at 5% FDR: **t ≈ 2.78**.

The paper's broad message is that the conventional `|t| ≈ 1.96–2.0` hurdle is too low once the
history of factor searching is recognized.

### Important source nuance

The exact benchmark depends on:

- error criterion;
- chosen significance level;
- number of trials;
- dependence;
- assumptions about hidden tests;
- sample construction.

Therefore no single number is presented as universally correct for every finance problem.

## 13. Hidden tests: M > R

The authors explicitly model the fact that the number of attempted factors `M` exceeds the number
of observed/published results `R`.

### Truncated-distribution approach

Appendix B models the published t-statistic sample as a truncated exponential distribution.

The baseline construction focuses on observations above **2.57** to reduce the uncertain
under-representation of marginal results between 1.96 and 2.57.

The paper estimates:

- roughly **71.1%** of tried factors may be unobserved/discarded under this model;
- approximately **824** total factor tests under one baseline truncated-distribution calculation;
- around **30%** of the t-statistics expected in the 1.96–2.57 region may be hidden from the observed
  sample.

These are model-based estimates, not directly observed counts.

### Adjusted thresholds with hidden tests

Under the simulation framework that incorporates hidden tests, the paper reports approximately:

- Bonferroni: **4.01**;
- Holm: **3.96**;
- BHY at 1%: **3.68**;
- BHY at 5%: **3.18**

for the baseline sampling-ratio case.

The authors therefore emphasize a hurdle above **3.0** as a practical summary for a newly proposed
factor in their research context.

## 14. Correlation among tests

A major concern is that many factor tests are correlated.

If two tests are effectively identical, counting them as two independent searches would overstate
multiplicity.

The paper explicitly discusses this.

### SOURCE CLAIM

Positive dependence can make generic multiple-testing procedures overly conservative.

In the extreme case of perfectly correlated tests, no multiplicity adjustment would be required
beyond the single-test hurdle because all tests contain effectively the same information.

### Robustness example

The paper notes that even if the universe is reduced from 316 factors to the **113 common factors**,
the general conclusion remains.

It gives a Holm threshold around:

- 3.29 for 113 factors;
- versus roughly 3.64 for the larger 316-factor universe.

### PROJECT IMPLICATION

Trading Bot must not count 20 highly correlated transforms as 20 independent discoveries.

Effective search multiplicity should account for redundancy.

This strongly supports family-level organization of signals and trial accounting.

## 15. Structural model with correlated factor returns

Section 5 introduces a direct model intended to combine:

- true versus zero-mean factors;
- missing/hidden tests;
- cross-factor correlation.

### Main assumptions

The model standardizes factor-strategy annual volatility to approximately 15%.

The population mean of candidate strategies is modeled as a mixture:

- point mass at zero with probability `p0`;
- positive exponential distribution for true factor means.

Contemporaneous strategy-return correlation is summarized by `rho`.

The authors stress that the exponential assumption is chosen for simplicity and for the intuition
that very profitable true factors should be rarer than small ones.

### Estimation

Rather than fit ordinary moments, they match:

- total discoveries;
- selected quantiles of the observed t-statistic distribution.

The baseline augmented sample uses:

- discovery count: 353;
- 20th percentile t: 2.39;
- median t: 3.16;
- 90th percentile t: 6.34.

Parameters are estimated through simulation / minimum-distance style matching.

## 16. Results of the correlation model

The paper reports a broad range because the result depends on assumed correlation and the amount of
missing research.

### Baseline missing-data case

For `r = 1/2`, estimates of total tests range roughly from:

- **1,297** at rho = 0;
- through **1,378** at rho = 0.2;
- to more than **3,000** at high rho.

For a more severe missing-test assumption, estimated total tests rise further.

### Typical threshold summary

Across correlation specifications, the paper says approximately:

- **t ≈ 3.9** is needed for FWER at 5%;
- **t ≈ 3.0** is needed for FDR at 1%.

### Correlation level

Using several pieces of evidence, the authors regard average factor-return correlation around
**0.20** as plausible.

They explicitly describe this estimate as uncertain / only weakly identified.

## 17. Statistical truth versus economic importance

This is a crucial nuance.

The paper notes that many factors classified as statistically true can still have small economic
payoffs.

It reports that around **70%** of statistically true factors in their model have an annual Sharpe
ratio below **0.5**.

### PROJECT IMPLICATION

Statistical significance is not the same thing as useful net expectancy.

For Trading Bot, even a robustly non-zero signal would still need to clear:

- fees;
- spread;
- slippage;
- funding where relevant;
- execution risk;
- opportunity cost;
- drawdown/risk constraints.

This source therefore supports the project's existing objective of **robust positive net expectancy**,
not significance hunting.

## 18. How many factors survive?

The conclusion provides an intentionally provocative assessment.

Among **296 published factors described as significant**, the paper reports that the number that
would be treated as false discoveries is:

- **158** under Bonferroni;
- **142** under Holm;
- **132** under BHY at 1%;
- **80** under BHY at 5%.

These counts are specific to the paper's asset-pricing factor sample and chosen procedures.

They must not be interpreted as a universal percentage of "fake trading signals".

## 19. Theory-driven versus purely empirical discoveries

The paper explicitly rejects the idea that all hypotheses deserve exactly the same prior treatment.

### SOURCE CLAIM

A factor developed from economic first principles can reasonably face a lower hurdle than a factor
discovered through a broad empirical search.

The rationale is that a theory-driven hypothesis has a more constrained search space and therefore
less data-mining freedom.

However, the authors still argue that the conventional t ≈ 2 hurdle is too weak even for a
theoretically motivated modern factor.

### PROJECT IMPLICATION

A pre-specified, source-grounded Trading Bot hypothesis should receive more credibility than a
pattern discovered after searching thousands of transformations.

But professional plausibility does **not** waive empirical validation.

This is directly relevant to the Owner's plan to derive base architecture from professional sources
before touching BTC development data.

## 20. Conditional effects caveat

The authors explicitly acknowledge that their principal tests are unconditional.

A factor can appear marginal on average yet be important in a specific economic environment.

### PROJECT IMPLICATION

This matters for a regime-aware Trading Bot.

Failure of an unconditional average test does not automatically prove that a signal has no
conditional informational role.

However, conditioning introduces additional degrees of freedom and therefore additional search
multiplicity.

The source does not solve that trade-off for us.

## 21. Out-of-sample evidence

The paper calls genuine out-of-sample testing the cleanest way to rule out spurious discoveries when
it is feasible.

But it makes a sharp distinction:

- holding out already observable historical data is useful;
- truly future data are a stronger, genuinely out-of-sample test.

Finance often requires years to accumulate such future observations.

### PROJECT IMPLICATION

This aligns with the project's evidence hierarchy:

future paper evidence should remain stronger than retrospective historical development evidence.

It also supports the distinction between:

- development sandbox;
- protected evaluation;
- future prospective paper.

## 22. Bayesian appendix

Appendix C examines a hierarchical Bayesian multiple-testing framework.

### Potential benefit

Multiplicity penalties arise naturally through posterior inference / model complexity.

### Problems emphasized by the authors

For this application:

- many tried factors are unobserved;
- conditional independence assumptions may be unrealistic;
- normality/hierarchical structure can be restrictive;
- high dimensionality creates computational difficulty;
- a final posterior-probability decision threshold is still required.

The authors therefore do not implement the Bayesian framework as their main solution.

### PROJECT IMPLICATION

"Use Bayesian methods" is not a magic escape from research multiplicity.

The search process and prior/model assumptions remain part of the evidence.

## 23. Realized FDP appendix

Appendix D examines a method that controls the probability that the realized false-discovery
proportion exceeds a chosen bound.

For one illustrative setting:

- FDP threshold gamma = 0.10;
- significance alpha = 0.05;

the paper reports a benchmark around **t = 2.70**.

This provides another example in which the appropriate hurdle is materially above conventional
single-test significance.

Again, it is an asset-pricing example, not a Trading Bot threshold.

## 24. FAQ clarifications

The FAQ section resolves several common misreadings.

### 24.1 High correlation does not invalidate Type-I-error control

If tests are extremely correlated, generic corrections can become too conservative.

The problem then is **low power / Type II error**, not failure to control Type I error.

### 24.2 More observations alone do not require a higher single-test threshold

A single independent test does not need a rising t-threshold merely because sample size grows.

The rising hurdle in this paper comes from **more hypotheses being searched**, not merely more data
points.

### 24.3 New discoveries may deserve tougher treatment

The authors' reasoning is not simply "new = bad".

They argue that:

- low-hanging true effects are likely found earlier;
- available datasets are finite;
- search costs have fallen dramatically;
- researchers may exhaust broad first-principles theories and increasingly search specialized
  variants.

### 24.4 Non-stationary / arbitraged-away anomalies

The authors recognize that some effects may be transitory and disappear after discovery.

Their preferred conceptual universe contains:

- more persistent/systematic effects;
- transitory abnormalities that can be arbitraged away.

A rising research hurdle is intended partly to reduce repeated discovery of transitory noise.

## 25. The full factor table

Table 6 spans many pages and is part of the paper's empirical foundation.

It records factors chronologically, with fields including:

- year;
- cumulative common/characteristic number;
- factor name;
- construction/formation;
- category;
- journal;
- short reference.

The table includes flags for:

- statistically insignificant results;
- duplicated factors;
- missing p-values.

It demonstrates directly that the 316-count is not a collection of identical indicators.

The factors cover:

- financial;
- macro;
- accounting;
- microstructure;
- behavioral;
- momentum/trend;
- liquidity;
- volatility;
- financing;
- investment;
- analyst/information;
- many other mechanisms.

### PROJECT INTERPRETATION

The table is useful evidence against "feature soup" reasoning.

A broad factor zoo exists, but publication and statistical significance do not imply that all
features belong simultaneously in one system.

## 26. What this paper supports for Trading Bot

This paper strongly supports the following research-governance principles.

### 26.1 Maintain an append-only experiment/search ledger

Failed trials are scientifically relevant.

They cannot disappear merely because the final configuration looks good.

### 26.2 Count families / effective hypotheses, not only filenames

Highly correlated variants should not be treated as fully independent tests.

But correlation also cannot be used as an excuse to ignore multiplicity completely.

### 26.3 Predeclare rationale where possible

Source-grounded, economically justified hypotheses have stronger prior credibility than
post-hoc mined patterns.

### 26.4 Preserve protected evaluation

Repeated inspection converts a dataset into development evidence.

True future observations remain a stronger evidence class.

### 26.5 Adjust confidence for the search process

A candidate selected from hundreds of alternatives requires more evidence than a genuinely
pre-specified candidate.

### 26.6 Separate statistical evidence from economic usefulness

Even statistically credible factors may have too little economic magnitude to survive costs.

## 27. What this paper does NOT support

This source does **not** justify any of the following:

- using `t > 3.0` as a universal Trading Bot pass/fail rule;
- treating every trade as an independent observation;
- applying cross-sectional equity factor thresholds directly to BTC time-series predictions;
- treating all signal families as independent tests;
- rejecting conditional signals merely because unconditional mean return is weak;
- choosing a strategy by maximizing t-statistic;
- declaring a BTC strategy validated from statistical significance alone;
- replacing walk-forward / protected evaluation with a p-value correction;
- ignoring execution costs;
- inferring any particular BTC signal weight;
- inferring any specific trend, cycle, volume or microstructure edge.

## 28. Critical transferability limits

The paper studies **cross-sectional equity asset-pricing factor discovery**.

Trading Bot targets:

- one asset initially: BTCUSDT;
- time-series decisions;
- overlapping prediction horizons;
- sequential market states;
- selective LONG / SHORT / NO_TRADE decisions;
- trading costs and execution;
- multi-family conditional logic.

Those are materially different statistical structures.

In particular, future Trading Bot observations may be:

- serially dependent;
- overlapping;
- conditionally selected;
- regime dependent;
- generated by the same evolving decision policy.

Therefore the paper's literal t-statistic cutoffs are not plug-and-play.

The transferable content is principally **research multiplicity discipline**.

## 29. Specific implications for the Owner's iterative-development plan

This source does **not** imply that iterative development is forbidden.

It implies that iteration has a cost to evidentiary independence.

A scientifically coherent reconciliation is:

1. allow an explicit development sandbox;
2. log every meaningful model/configuration/hypothesis trial;
3. do not call development performance independent confirmation;
4. control the number and structure of empirical degrees of freedom;
5. freeze the final candidate before protected evaluation;
6. preserve future paper data as the strongest practical confirmation.

This is a Research Director interpretation built directly from the paper's multiplicity logic.

The precise governance rule will be decided only during final corpus synthesis.

## 30. Relationship to signal weights

This source says almost nothing directly about how a multi-signal trading system should assign
directional weights.

Its relevance to weights is **indirect but important**:

- unrestricted weight optimization is a large multiple-testing/search problem;
- trying many weight combinations inflates selection bias;
- correlated signals reduce the effective independent dimension but do not eliminate overfitting;
- source-derived structural weights can reduce the search space;
- bounded empirical corrections are scientifically safer than unconstrained optimization, all else
  equal.

No numeric `peso_base` or `peso2` rule is derivable from this paper.

## 31. Relationship to ablations

The paper's logic is compatible with post-design diagnostic ablations, but every large family of
alternative models/configurations increases the effective search burden.

Therefore:

- a small, predeclared ablation set can diagnose architecture;
- a combinatorial ablation tournament can become another factor zoo.

This distinction should be considered in final system governance.

## 32. Research Director interpretation

The most important lesson for Trading Bot is:

> **the unit of scientific evidence is not merely the final backtest. It is the final result plus the
> entire search process that produced it.**

That means the research system needs to preserve:

- what was hypothesized before results;
- how many alternatives were tried;
- which alternatives were discarded;
- which data had already been inspected;
- which changes were source/theory driven;
- which changes were response to historical performance;
- how correlated/redundant the alternatives were.

This paper provides one of the strongest methodological foundations in the corpus for that
requirement.

## 33. Open questions for Astra at final corpus review

1. How should the paper's multiple-testing logic be translated from cross-sectional factor discovery
   to a single-asset sequential BTC strategy?
2. What should count as an "effective hypothesis" when many signal variants are strongly
   correlated?
3. Should Trading Bot maintain separate search ledgers for:
   - architecture changes;
   - signal definitions;
   - weights;
   - thresholds;
   - exits;
   - execution rules?
4. Which multiplicity-aware diagnostic is most appropriate for the eventual development process:
   - DSR;
   - PBO/CSCV;
   - FDR-style control;
   - nested walk-forward;
   - another framework?
5. How should conditional/regime-specific signals be evaluated without multiplying hidden degrees of
   freedom uncontrollably?
6. How should overlapping 4h targets and serially dependent predictions alter conventional
   significance calculations?
7. Can a professional-source-derived base architecture legitimately reduce the multiplicity burden,
   and how should that reduction be documented?
8. How many bounded empirical weight adjustments can be permitted before the development process
   becomes effectively an optimization search?
9. Should evidence thresholds vary by whether a change was:
   - pre-specified from professional theory;
   - suggested by diagnostics;
   - discovered by broad empirical search?
10. What should be the project's primary inferential object:
    - per-signal significance;
    - forecast calibration;
    - conditional net expectancy;
    - policy-level performance;
    - some hierarchy of these?
11. How should the experiment ledger encode correlated variants so that search history is neither
    understated nor naively counted?
12. How should future prospective paper evidence be used to adjudicate a system that was heavily
    iterated on historical development data?

## 34. Durable project knowledge retained from LIB-016

1. Hundreds of financial factors have historically been proposed; the observed published set is only
   part of the true search universe.
2. Conventional single-test significance becomes too permissive under large-scale repeated search.
3. Failed and unpublished tests matter scientifically.
4. FWER and FDR represent different valid error-control objectives.
5. Bonferroni is simple but conservative; Holm is more powerful while controlling FWER; BHY controls
   FDR under general dependence.
6. A candidate selected from many trials requires stronger evidence than a genuinely isolated test.
7. The paper's asset-pricing application generally points toward a modern hurdle above conventional
   `t ≈ 2`, often around or above `t ≈ 3`.
8. The exact threshold depends on assumptions and is **not universal**.
9. Theory-driven hypotheses may deserve a lower hurdle than pure empirical searches, but theory does
   not eliminate the need for evidence.
10. Correlation/redundancy among tests reduces effective multiplicity.
11. Hidden failed tests can materially raise the required evidence threshold.
12. Genuine future out-of-sample evidence is cleaner than a historical holdout already observable to
    the researcher.
13. Conditional effects can exist even when unconditional averages are weak.
14. Statistical truth is not the same as economic usefulness.
15. Research iteration is scientifically permissible only if its search cost and loss of
    independence are acknowledged.
16. The entire search path is part of the evidence.

## 35. Final source disposition

`REVIEWED`

Reason:

- all 101 accessible pages reviewed;
- main argument and all major statistical methods covered;
- full factor taxonomy/list inspected;
- hidden-test simulation reviewed;
- dependence/correlation model reviewed;
- Bayesian appendix reviewed;
- FDP appendix reviewed;
- FAQ reviewed;
- full-document visual scan completed;
- source claims separated from Research Director interpretation;
- direct BTC-transfer limitations explicitly recorded.

No Trading Bot strategy, parameter, numeric signal weight, System G2 design or market experiment is
authorized by this source.
