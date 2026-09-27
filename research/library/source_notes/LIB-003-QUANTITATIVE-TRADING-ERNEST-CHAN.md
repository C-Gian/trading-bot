# LIB-003 — Quantitative Trading: How to Build Your Own Algorithmic Trading Business — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `Quantitative trading _ how to build your own algorithmic trading business.pdf`  
Drive file id: `13Yq37aveSXm2QdOkbpm-FaJKpCDzAER_`  
Local corpus id: `LIB-003`  
Author: **Ernest P. Chan**  
Publisher: **John Wiley & Sons, Inc.**  
Copyright / publication: **2009**  
Local PDF pages: **181**  
Raw file size: **729,650 bytes**  
SHA-256: `4d18c7a14b2583372dff2da16e638095807856aefbd47c8e3f3733b3565183ba`

## 1. Source identity and accessible-artifact qualification

The source is:

**Ernest P. Chan — Quantitative Trading: How to Build Your Own Algorithmic Trading Business**

The local PDF contains:

- title/copyright matter;
- contents;
- Chapters 1–8;
- a MATLAB appendix;
- bibliography;
- author page;
- index.

The table of contents refers to a Preface and Acknowledgments, but those sections are not present in
the accessible local PDF: the file moves from the contents directly to Chapter 1.

Therefore `REVIEWED` means:

> complete review of the accessible 181-page PDF artifact,

not a claim that every page of every print edition was available.

The complete PDF was also visually scanned page-by-page in rendered form to verify that figures,
tables, examples and code-heavy sections were not silently lost by text extraction.

## 2. What kind of source this is

This is a practitioner-oriented quantitative-trading book focused on the end-to-end process of:

1. finding strategy ideas;
2. screening them;
3. backtesting;
4. avoiding common research errors;
5. implementing execution;
6. managing money and risk;
7. understanding common statistical-arbitrage strategy families;
8. operating a small quantitative trading business.

It is not one unified empirical paper and does not establish one specific trading edge.

Much of the technology, brokerage and U.S. market-structure discussion reflects the **2008–2009**
environment and must not be copied literally into a 2026 BTC system.

Its strongest durable value for Trading Bot lies in:

- research process;
- causal backtesting;
- data-snooping control;
- strategy refinement discipline;
- transaction-cost realism;
- paper/live divergence diagnosis;
- risk and leverage concepts;
- distinction between momentum and mean reversion;
- regime dependence;
- execution and operational risk.

## 3. Core definition of quantitative trading

### SOURCE CLAIM

Chan defines quantitative / algorithmic trading broadly as trading where buy/sell decisions are
determined by computer algorithms and historical strategy performance can be tested on historical
financial data.

He explicitly argues that quantitative trading can use more than traditional technical analysis.

Potential inputs include:

- price/technical information;
- fundamental information;
- news or other machine-readable information.

The essential condition is that the information can be represented in a form usable by a computer.

### RESEARCH DIRECTOR INTERPRETATION

The book's framing supports a **multi-information architecture** rather than an "indicator-only"
architecture.

However, the source does not prescribe a final signal-family taxonomy or weighting system.

## 4. Simplicity as a recurring principle

### SOURCE CLAIM

A strong theme throughout the book is that simple, understandable models can be preferable to highly
complex models.

Chan is particularly skeptical of models that:

- contain many free parameters;
- discover patterns without economic/rational justification;
- obtain exceptional backtests through flexible nonlinear fitting;
- use limited financial history as though observations were independent.

His preferred properties for predictive models include:

- a sound econometric or rational basis;
- few fitted parameters;
- conceptual simplicity;
- optimization using only prior data;
- continuous demonstration on future unseen data.

### IMPORTANT NUANCE

Chan is **not anti-adaptation or anti-machine-learning in absolute terms**.

Later in the book he presents a regime-switching example using a perceptron / machine-learning tool,
provided that:

- optimization occurs inside a backward-looking moving window;
- future unseen data are not used;
- the candidate parameter/rule space is constrained.

This creates an important internal nuance:

> complexity is not rejected categorically; uncontrolled degrees of freedom and future leakage are.

## 5. Strategy discovery and initial screening

### SOURCE CLAIM — ideas are abundant; viable implementation is scarce

Chan argues that finding published trading ideas is not the hardest part.

Ideas can come from:

- academic research;
- financial publications;
- trader forums;
- blogs;
- other practitioners.

The harder task is determining which strategies are:

- plausible;
- implementable;
- compatible with the trader's resources;
- robust enough to justify deeper work.

### SOURCE CLAIM — strategy suitability depends on the operator

He emphasizes matching a strategy to:

- available working time;
- programming/automation capability;
- capital;
- data/infrastructure budget;
- desired income profile;
- holding period;
- leverage/capacity constraints.

This is a business-level point, not an alpha claim.

### SOURCE CLAIM — initial skepticism checklist

Before committing to a full backtest, Chan recommends evaluating issues such as:

- performance relative to an appropriate benchmark;
- consistency / Sharpe ratio;
- drawdown depth and duration;
- realistic transaction costs;
- survivorship bias;
- deterioration in recent years;
- data-snooping risk;
- strategy capacity / competitive niche.

### RESEARCH DIRECTOR INTERPRETATION

For Trading Bot, this supports a design principle that a signal or setup should not be assessed only
by gross return.

Its research dossier should eventually include:

- net expectancy;
- drawdown;
- stability;
- costs;
- temporal decay;
- effective search burden;
- capacity/execution constraints.

No numeric threshold from this 2009 book is frozen for the project.

## 6. Capacity and competition

### SOURCE CLAIM

Chan treats **capacity** as a major economic property of a trading strategy.

Some strategies can remain attractive for a small trader precisely because they cannot absorb enough
capital to interest large institutions.

He argues that competition can erode profitable opportunities:

- mean-reversion/arbitrage opportunities can gradually disappear;
- momentum opportunities may survive over progressively shorter horizons as information is absorbed
  faster.

### RESEARCH DIRECTOR INTERPRETATION

A small-capacity edge can still be economically valid for the Owner's product because V1/V2 is not
designed to deploy institutional-size capital.

This is a potentially favorable structural constraint, but it is **not evidence that any current
Trading Bot strategy has such an edge**.

## 7. Backtesting: purpose and philosophy

### SOURCE CLAIM

Chan describes backtesting as serving several purposes:

- reproduce and verify a strategy;
- ensure the strategy is correctly understood;
- identify implementation/research errors;
- estimate historical performance;
- experiment with defensible variations;
- refine a strategy.

This source therefore explicitly treats historical backtesting as a **development tool as well as a
verification tool**.

### CRITICAL QUALIFICATION

Chan places limits on that refinement.

Changes intended to improve training performance should:

- remain simple;
- ideally have an economic or well-studied market rationale;
- also behave reasonably on a distinct test set.

He explicitly warns against changing parameters/conditions to improve the test set after observing
it, because that turns the test set into another training set.

### PROJECT RELEVANCE

This supports a staged distinction between:

- development data that may legitimately provide feedback;
- protected evaluation evidence that must not be recycled indefinitely into development.

This dossier records the source position only; final Trading Bot governance will be decided after
the full corpus is studied.

## 8. Data quality and point-in-time discipline

### SOURCE CLAIM — survivorship bias

Historical datasets that omit securities that disappeared through bankruptcy/delisting/etc. can
materially inflate strategy performance.

Chan particularly highlights risk to strategies that buy apparently cheap/distressed securities.

### SOURCE CLAIM — point-in-time information matters

A backtest must use information actually available at the historical decision time.

He recommends survivorship-bias-free / point-in-time data where needed and recognizes the practical
cost of obtaining it.

### SOURCE CLAIM — corporate-action adjustment

For equities, splits and dividends must be handled correctly to avoid false signals.

### SOURCE CLAIM — high/low data can create false fills

Historical intraday/daily high and low fields can be noisier and less executable than opens/closes.

A limit price lying inside a recorded daily high-low range does not prove the order would actually
have filled.

### RESEARCH DIRECTOR INTERPRETATION

For Trading Bot, the durable lesson is broader than stock-data mechanics:

> historical observability is not the same thing as historical executability.

The future replay engine must distinguish market observations from trades that could actually have
been made under the frozen execution contract.

## 9. Look-ahead bias and the truncated-history invariance test

This is one of the book's strongest directly reusable methodological ideas.

### SOURCE CLAIM

A backtest has look-ahead bias whenever a historical decision uses information that was unavailable at
the time.

Examples include:

- using a day's final low before the day is complete;
- fitting a regression with future observations and then using the fitted coefficients in prior
  periods.

### SOURCE PROCEDURE

Chan proposes a deterministic diagnostic:

1. run the backtest on the complete historical dataset and save all historical positions;
2. remove the most recent part of the input history;
3. rerun the model;
4. compare decisions over the common historical interval.

If decisions in the retained past change when future observations are removed, the implementation has
used future information.

### RESEARCH DIRECTOR INTERPRETATION

This should be retained as a strong candidate for a permanent Trading Bot causal-invariance test.

The modern implementation can generalize the comparison from positions to:

- indicators;
- forecasts;
- probabilities/confidence;
- regime states;
- LONG/SHORT/NO_TRADE decisions;
- entry/exit instructions.

No implementation is authorized by this dossier alone.

## 10. Data-snooping / overfitting

### SOURCE CLAIM

Chan treats data-snooping bias as pervasive in financial modelling because the amount of genuinely
independent information is limited.

The risk comes from more than numerical parameter fitting.

It also comes from repeatedly changing qualitative choices such as:

- entry at open vs close;
- overnight vs intraday;
- stock universe;
- holding period;
- thresholds;
- filters.

### SOURCE HEURISTICS

The book provides practical heuristics, including:

- keep the number of free parameters small;
- use sufficient history relative to parameter count;
- divide data into training and test sets;
- perform sensitivity analysis;
- simplify aggressively;
- prefer solutions that remain acceptable over nearby parameter values;
- do not tune against the test set after seeing its result.

Chan gives a rough sample-size heuristic of approximately 252 observations per free parameter for
daily models.

### LIMITATION

That numerical heuristic is explicitly practitioner judgement, not a universally established
statistical theorem.

It should **not** become a Trading Bot governance rule without independent justification.

## 11. Moving optimization / "parameterless" models

### SOURCE CLAIM

Chan uses "parameterless" in a nonliteral sense.

The model still has parameters, but they can be dynamically determined from a historical moving
window rather than fixed forever from one global fit.

He argues this can reduce certain forms of fixed-parameter overfitting if:

- only historical data inside the current lookback are used;
- the moving optimization itself is honestly simulated through history.

He also suggests averaging decisions over multiple reasonable parameter configurations rather than
always selecting one single historical optimum.

### RESEARCH DIRECTOR INTERPRETATION

Two useful concepts for later corpus synthesis are:

- **causal adaptive calibration**;
- **parameter/model averaging** instead of brittle point optimization.

Neither concept is automatically appropriate for Trading Bot; both add degrees of freedom and would
need frozen development governance.

## 12. Out-of-sample testing and paper trading

### SOURCE CLAIM

Chan calls actual unseen future data the strongest form of out-of-sample testing short of real
capital.

Paper trading can reveal:

- hidden look-ahead assumptions;
- software bugs;
- differences between backtest and executable behavior;
- operational timing problems;
- data availability issues;
- realistic transaction costs;
- actual capital usage and trade frequency.

### IMPORTANT SOURCE POSITION

When testing a strategy published earlier, the historical interval after publication can be genuinely
out-of-sample **only if the researcher has not used it to re-optimize the published model**.

### RESEARCH DIRECTOR INTERPRETATION

This is closely aligned with the project's evidence hierarchy:

future paper evidence can answer questions that even a careful historical simulator cannot.

## 13. Sensitivity analysis and robust refinement

### SOURCE CLAIM

After optimization, nearby parameter changes and simple structural simplifications should be tested.

A strategy is suspect if:

- only one narrow parameter value works;
- small changes destroy out-of-sample performance.

Chan explicitly encourages removing:

- unnecessary conditions;
- unnecessary constraints;
- unnecessary parameters,

even if this reduces training performance, when test performance is preserved.

### SOURCE CLAIM — refinement should have a rationale

Minor strategy variations may improve an old or crowded idea, but Chan prefers refinements grounded
in:

- economic reasoning;
- established market phenomena,

rather than arbitrary trial-and-error rules.

### PROJECT RELEVANCE

This is highly relevant to the Owner's desire to learn from development errors without degenerating
into unconstrained backtest rescue.

A future iteration ledger should record:

- what changed;
- why;
- which evidence motivated the change;
- whether it was structural/rational or purely performance-seeking.

## 14. Transaction costs

### SOURCE CLAIM

A backtest is not realistic without transaction costs.

Chan identifies multiple cost components:

- commissions;
- bid/ask or liquidity cost;
- opportunity cost from non-execution;
- market impact;
- slippage / execution delay.

### SOURCE EXAMPLES

The book shows examples where apparently excellent gross strategies become poor or strongly negative
after realistic costs.

This is used to demonstrate that:

> gross predictability is not equivalent to net tradability.

### SOURCE CLAIM — execution and liquidity constrain capacity

Position size must be considered relative to:

- trading volume;
- market capitalization / liquidity;
- available execution infrastructure.

Specific numerical rules of thumb in the book are dated and equity-specific.

### RESEARCH DIRECTOR INTERPRETATION

For Trading Bot, the durable rule is:

> costs and execution are part of the strategy's economics, not a post-processing subtraction.

No 2009 U.S.-equity basis-point assumption should be copied into BTC.

## 15. Strategy refinement example and its limitation

Chan demonstrates that a small change in execution timing can materially alter historical results.

The author's intended lesson is that simple, plausible modifications can matter.

### SCIENTIFIC CAUTION

A single example of a successful refinement does not prove that repeated strategy modification is
safe.

The book itself repeatedly warns that repeated choices consume the credibility of the historical
sample.

For Trading Bot, any comparable refinement process must preserve the full iteration/search record.

## 16. Automation and execution systems

### SOURCE CLAIM

Automated execution can:

- reduce manual errors;
- reduce delay;
- enforce strategy logic;
- permit multiple strategies;
- enable high-frequency operation.

The book distinguishes semiautomated and fully automated systems.

### DURABLE ARCHITECTURAL IDEA

A live quantitative system has a chain:

`market data -> strategy computation -> order generation -> transmission -> execution`

Errors at any layer can cause divergence from the backtest.

### HISTORICAL LIMITATION

Specific DDE, MATLAB, TradeStation, brokerage and 2008-era API/infrastructure recommendations are
historical.

The durable concept is the separation of:

- research/backtest logic;
- real-time data;
- decision generation;
- order execution;
- reconciliation/monitoring.

## 17. Paper/live reconciliation

### SOURCE CLAIM

Chan recommends directly comparing trades generated by the live/paper execution system against trades
generated by the backtest logic on the same newly available data.

If the difference cannot be explained by execution costs/delay, software defects are likely.

### RESEARCH DIRECTOR INTERPRETATION

Trading Bot should eventually support deterministic reconciliation between:

- historical replay;
- paper/live inference;
- executed paper trades.

The same timestamp and information set should produce the same pre-execution decision state.

## 18. Diagnosing live underperformance

Chan proposes a hierarchy of possible causes when real/paper results fail to match expectations:

1. software bugs;
2. mismatch between live and research logic;
3. underestimated costs/slippage;
4. liquidity/market-impact problems;
5. data-snooping / model overfit;
6. regime change;
7. ordinary bad luck.

### RESEARCH DIRECTOR INTERPRETATION

This supports a structured trade/system autopsy rather than immediately changing signals after losses.

For Trading Bot, later diagnostics should classify observed failure rather than simply answer
"winning trade / losing trade."

## 19. Risk and Kelly allocation

### SOURCE CLAIM

Chan presents Kelly-style allocation as a framework for maximizing long-run compounded growth under a
Gaussian return approximation.

For statistically independent strategies, the one-strategy form is proportional to:

`expected excess return / variance`.

For multiple correlated strategies, allocation depends on:

- expected returns;
- covariance among strategy returns.

### SOURCE CAUTION

Chan repeatedly warns that:

- return distributions are not truly Gaussian;
- fat-tail events are more frequent than Gaussian assumptions imply;
- estimated parameters are uncertain.

For these reasons he discusses **half-Kelly** and additional leverage constraints.

### IMPORTANT PROJECT LIMITATION

Kelly allocation is not automatically appropriate for Trading Bot.

The Owner's product objective and risk budget can legitimately require substantially less risk than
growth-optimal Kelly.

No leverage or sizing rule is frozen from this source.

## 20. Risk must adapt downward after losses

### SOURCE CLAIM

Risk management generally requires reducing position size when losses reduce equity or when the
estimated performance of a model deteriorates.

Chan prefers gradually reducing allocation as estimated edge declines rather than making purely
emotional all-or-nothing shutdown decisions.

### RESEARCH DIRECTOR INTERPRETATION

This is relevant to a future distinction between:

- evidence that a trade is weak;
- evidence that a strategy's live edge is deteriorating;
- capital/risk allocated to that strategy.

However, repeated live re-estimation can itself create instability and would require separate
governance.

## 21. Stop losses are strategy-dependent

### SOURCE CLAIM

Chan rejects the simplistic idea that a stop loss automatically prevents catastrophic loss.

A discontinuous move can execute far beyond the stop level.

More importantly, whether a stop is logically appropriate depends on the expected price process.

### Momentum/trend

If the process is believed to be trending, deterioration may justify exit because further movement in
the same adverse direction is plausible.

### Mean reversion

If the original mean-reversion hypothesis remains intact, a conventional stop can force exit near the
point where reversal is most expected.

Chan therefore prefers holding-period / target logic for many mean-reversion systems unless new
information suggests the regime changed.

### PROJECT RELEVANCE

Stops should eventually be connected to **trade thesis / regime**, not inserted as one universal
percentage parameter.

This is a conceptual lesson, not a BTC-ready stop policy.

## 22. Model, software and operational risk

Chan distinguishes more than market risk.

### Model risk

Possible causes include:

- data-snooping;
- survivorship bias;
- incorrect assumptions;
- competition;
- market-structure change / edge decay.

### Software risk

Implementation may fail to reproduce the intended model because of bugs.

### Operational / physical risk

Examples include:

- connectivity failure;
- power failure;
- infrastructure failure.

### SOURCE RECOMMENDATION

Independent reproduction of research is valuable in reducing model risk.

### PROJECT RELEVANCE

The future Trading Bot system should maintain separate controls for:

- scientific/model correctness;
- software correctness;
- runtime/infrastructure correctness.

## 23. Psychological / governance lessons

Even systematic traders can override algorithms emotionally.

Chan highlights:

- loss aversion;
- status-quo/endowment effects;
- representativeness / overweighting recent events;
- despair after drawdowns;
- greed after successful periods;
- overleverage.

A particularly relevant warning is against modifying a model immediately after one dramatic recent
loss merely so that the modified backtest would have avoided that event.

### RESEARCH DIRECTOR INTERPRETATION

This directly supports the project's rule that one surprising trade should not trigger an immediate
model rewrite.

Changes should be motivated by recurring, pre-specified or statistically meaningful evidence rather
than emotional reaction to one case.

## 24. Mean reversion versus momentum

### SOURCE CLAIM

Chan presents mean reversion and momentum/trend as the two fundamental price-behavior archetypes.

Crucially, he says a market can display:

- mean reversion at one horizon;
- momentum at another horizon.

Therefore the two labels are not globally mutually exclusive.

### Momentum mechanisms discussed

The book proposes several mechanisms that can create momentum:

1. slow diffusion of new information;
2. incremental execution of a large institutional order;
3. herd behavior.

These mechanisms imply potentially different horizons.

### SOURCE CLAIM — competition changes the opportunity

With more competition:

- mean-reversion/arbitrage opportunities can become fewer/weaker;
- momentum effects can become shorter-lived as information is incorporated faster.

### PROJECT RELEVANCE

This is highly relevant to multi-timeframe architecture.

A future system should avoid treating:

`TRENDING`

or

`MEAN_REVERTING`

as one timeless property of BTC.

The horizon must be explicit.

## 25. Regime switching

### SOURCE CLAIM

Markets can change regimes in dimensions including:

- bull/bear;
- inflation/recession;
- high/low volatility;
- mean-reverting/trending behavior.

Chan is skeptical that generic Markov-regime models with constant transition probabilities are very
useful for actual trading because traders care about **when transition risk changes materially**.

### Data-driven regime example

The book shows a machine-learning search over technical conditions and holding periods with a moving
training window.

The author recognizes that broad model-category search can still introduce data-snooping bias even if
each local optimization is causal.

### RESEARCH DIRECTOR INTERPRETATION

This is a valuable distinction:

- causal rolling estimation does not automatically eliminate **researcher-level selection bias**.

Both levels must be governed separately.

## 26. Stationarity and cointegration

### SOURCE CLAIM

A stationary series tends not to wander indefinitely away from a stable range/mean.

Nonstationary securities can sometimes be combined into a stationary spread when they are
cointegrated.

Chan emphasizes that:

**cointegration is not correlation**.

Correlation concerns co-movement of returns over a horizon.

Cointegration concerns a longer-run relation among price levels / a stationary linear combination.

### PROJECT RELEVANCE

This is useful methodology for relative-value systems.

For the current single-asset BTC mission, pair cointegration is not directly actionable unless the
asset universe expands or a defensible linked market (e.g. spot/perpetual relation) is admitted
later.

No such expansion is authorized here.

## 27. Factor models

### SOURCE CLAIM

Chan describes factor models as expressing returns through:

- common factor exposures;
- common factor returns;
- stock/security-specific residual returns.

Potential factors can be:

- market/economic;
- fundamental;
- technical.

He notes that factor models become predictive only if some relevant factor-return behavior persists
into the next period.

### IMPORTANT LESSON

A factor's explanatory usefulness in-sample does not automatically make it predictive.

### RESEARCH DIRECTOR INTERPRETATION

For Trading Bot this reinforces the distinction between:

- explanatory state variables;
- genuinely predictive evidence.

A beautiful decomposition of BTC market state is not sufficient if it adds no causal predictive or
risk-management value.

## 28. Exit logic depends on the strategy mechanism

Chan identifies common exit structures:

- fixed holding period;
- target/profit cap;
- updated/reversed model signal;
- stop.

### Momentum

The information-diffusion process has a finite lifetime, so holding period matters and can shorten as
competition accelerates information absorption.

A later opposite momentum signal can rationally serve as an exit.

### Mean reversion

Chan discusses estimating a mean-reversion half-life using an Ornstein-Uhlenbeck representation.

The mean / expected reversion horizon can provide a structural basis for:

- target;
- maximum holding period.

### PROJECT RELEVANCE

Entry and exit design should arise from the mechanism hypothesized to create the edge, not from one
generic trade template.

## 29. Seasonal strategies

Chan presents equity and commodity examples and emphasizes an important methodological principle:

seasonality is more credible when it has a plausible recurring economic mechanism.

He also shows examples of effects that weakened or disappeared.

### LIMITATION

The particular seasonal trades are historical examples from traditional markets.

They provide no direct BTC signal and should not be ported into Trading Bot.

## 30. High-frequency trading

### SOURCE CLAIM

Chan argues that high-frequency strategies can achieve high Sharpe ratios when:

- the edge has positive mean expectancy;
- many sufficiently independent opportunities occur.

But he stresses that high-frequency profitability is strongly constrained by:

- bid/ask data;
- transaction costs;
- execution speed;
- sometimes full order-book information;
- realistic fill simulation.

At very short horizons, backtesting alone may be insufficient.

### PROJECT RELEVANCE

This supports keeping Trading Bot's initial product away from pretending that 1m data alone can
faithfully model sub-second or order-book-dependent HFT.

The current 1m execution layer is not equivalent to HFT.

## 31. Capacity and the small-trader advantage

### SOURCE CLAIM

Chan argues that an independent trader can sometimes possess a structural advantage because:

- small strategies can operate in niches too small for large institutions;
- large funds must deploy much more capital;
- large positions consume liquidity and become harder to exit;
- institutional constraints can force suboptimal strategy choices;
- large funds may overcomplicate models to deploy capital.

### RESEARCH DIRECTOR INTERPRETATION

The Owner's modest paper-capital environment can legitimately explore edges that would not scale to
institutional capital.

But "small trader" is not itself an edge.

There still must be a causal/executable reason for positive net expectancy.

## 32. Edge decay and ongoing research

### SOURCE CLAIM

Chan does not portray a profitable model as permanent.

Strategies can weaken because:

- others discover the opportunity;
- market structure changes;
- regulation changes;
- information moves faster;
- the underlying regime changes.

He therefore describes ongoing research as necessary.

### PROJECT RELEVANCE

A production Trading Bot should eventually distinguish:

- a validated strategy;
- monitoring evidence about whether the edge remains within expected behavior;
- a research environment for potential successors.

These should not be silently mixed.

## 33. Chapter-by-chapter coverage record

### Chapter 1 — The Whats, Whos, and Whys of Quantitative Trading

Covered:

- definition of quantitative trading;
- technical/fundamental/news inputs;
- independence vs institutional trading;
- advantages of systematic/automated operation;
- simplicity;
- quantitative trading as a small business.

### Chapter 2 — Fishing for Ideas

Covered:

- sources of ideas;
- strategy/operator fit;
- capital/infrastructure constraints;
- benchmark and Sharpe screening;
- drawdown;
- transaction costs;
- survivorship bias;
- recent-performance decay;
- data-snooping;
- capacity and institutional competition;
- author's skepticism toward unconstrained AI pattern fitting.

### Chapter 3 — Backtesting

Covered:

- backtest tooling;
- data sourcing and adjustment;
- survivorship bias;
- historical high/low execution problems;
- performance measurement;
- Sharpe/drawdown;
- look-ahead;
- truncated-history bias detection;
- data-snooping;
- train/test splits;
- moving optimization;
- parameter averaging;
- sensitivity analysis;
- transaction costs;
- strategy refinement.

### Chapter 4 — Setting Up Your Business

Covered:

- retail vs proprietary trading;
- brokerage/execution-quality considerations;
- liquidity access;
- APIs;
- paper/simulator accounts;
- infrastructure;
- connectivity/continuity.

Most specific legal, brokerage and technology details are historically dated and not directly
portable.

### Chapter 5 — Execution Systems

Covered:

- semiautomated vs fully automated trading;
- data -> model -> orders -> broker pipeline;
- programming/automation;
- transaction-cost minimization;
- paper trading;
- real/backtest divergence;
- regime change;
- shortability/operational constraints.

### Chapter 6 — Money and Risk Management

Covered:

- Kelly allocation;
- covariance across strategies;
- half-Kelly;
- fat tails;
- leverage;
- risk reduction after losses;
- contagion;
- strategy-dependent stop logic;
- model/software/physical risk;
- behavioral risk;
- overleverage.

### Chapter 7 — Special Topics in Quantitative Trading

Covered:

- mean reversion vs momentum;
- momentum mechanisms;
- regime switching;
- machine-learning example;
- stationarity;
- cointegration vs correlation;
- factor models;
- exit strategies;
- OU half-life;
- seasonal strategies;
- high-frequency trading;
- leverage vs beta.

### Chapter 8 — Conclusion: Can Independent Traders Succeed?

Covered:

- capacity;
- liquidity provision;
- institutional constraints;
- complexity and data snooping;
- small-trader niches;
- scaling;
- continuous research;
- edge decay.

### Appendix — A Quick Survey of MATLAB

Reviewed to completion.

It provides language/tooling examples rather than additional trading theory.

The specific MATLAB implementation advice is historical; the durable lesson is the value of a
reusable numerical/research toolkit.

## 34. Figures / tables inspected

The complete rendered PDF was visually scanned.

Material visual elements include:

- strategy/source tables;
- capital-choice tables;
- drawdown diagrams;
- performance tables;
- backtest/code examples;
- automated-system flow diagrams;
- Kelly/risk examples;
- machine-learning workflow screenshots;
- stationary/nonstationary spread charts;
- seasonal-return tables.

No material figure was interpreted as stronger evidence than the surrounding text permits.

## 35. What this source supports for Trading Bot

This source is strong support for retaining the following **research/process principles** for later
cross-source synthesis:

1. research ideas must be executable and testable, not merely narratively plausible;
2. simple mechanisms with few degrees of freedom are generally safer than unconstrained searches;
3. development may include refinement, but protected evaluation must not be tuned after inspection;
4. historical information must be causal and point-in-time;
5. use a truncated-history invariance test to detect hidden future leakage;
6. log and control both numerical and qualitative research degrees of freedom;
7. robustness to nearby parameters/conditions matters;
8. transaction costs are intrinsic to strategy economics;
9. paper trading is uniquely valuable for software/operational validation;
10. live divergence requires diagnosis before model mutation;
11. regime and edge decay are real research concerns;
12. momentum and mean reversion are horizon-conditional mechanisms;
13. exit/risk logic should be consistent with the underlying strategy mechanism;
14. model, software, execution and operational risk are distinct;
15. recent dramatic losses should not automatically trigger reactive parameter changes;
16. small capital/capacity can change which opportunities are feasible.

## 36. What this source does NOT support

LIB-003 does **not** establish:

- a profitable BTCUSDT strategy;
- a specific BTC trend rule;
- a specific BTC mean-reversion rule;
- any signal-family base weight;
- any `peso2` value;
- any 15m/1h/4h parameter;
- any crypto funding/OI rule;
- any cycle-analysis method;
- any current brokerage/exchange cost;
- any Binance fill/slippage assumption;
- any optimal BTC stop/target;
- any exact Kelly leverage for the Owner;
- any claim that machine learning should be used in Trading Bot;
- any claim that the book's 2008 market examples remain profitable today.

The numerical examples are educational/historical, not present-day Trading Bot parameters.

## 37. Important source limitations

1. **Publication date:** 2009; many brokerage, market-structure and technology examples are obsolete.
2. **Traditional markets:** primarily U.S. equities, ETFs, futures and FX; no crypto evidence.
3. **Practitioner heuristics:** several thresholds/rules of thumb are based on experience rather than
   formal statistical proof.
4. **Examples are illustrative:** a successful book example is not independent confirmation of a
   durable edge.
5. **Research-search accounting is incomplete by modern standards:** the book recognizes
   data-snooping but does not provide the later formal multiple-testing machinery available in newer
   literature.
6. **Gaussian Kelly assumptions are fragile:** the author explicitly acknowledges fat tails.
7. **Regime examples can themselves be selection-prone:** the book acknowledges category-level
   search bias.
8. **No BTC-specific execution layer.**
9. **Accessible artifact lacks the Preface/Acknowledgments listed in the contents.**

## 38. Internal tensions worth preserving for Astra

### T-003-01 — Refinement versus test-set purity

The author encourages strategy refinement after initial backtests.

At the same time he explicitly says:

- train on training data;
- require reasonable behavior on a test set;
- do not then optimize against that test set.

A future development governance must preserve that distinction.

### T-003-02 — AI skepticism versus machine-learning example

The author strongly warns against high-parameter AI pattern discovery.

Later he demonstrates a perceptron-based regime model.

The reconciliation inside this source appears to be:

- constrained hypothesis space;
- causal moving-window fitting;
- limited optimized parameters;
- awareness that researcher-level model-category selection still causes snooping.

### T-003-03 — Adaptive parameters can reduce one bias but create another research layer

Rolling optimization prevents future data from entering each historical fit.

It does **not** eliminate the possibility that the researcher chose the rolling procedure because it
looked good after seeing historical results.

### T-003-04 — Stop-loss rules depend on the model's market hypothesis

The book rejects one universal stop philosophy.

This creates an architectural requirement to distinguish the reason for the trade before defining the
exit.

## 39. Questions for Astra at final corpus review

1. Which of Chan's development/refinement practices remain scientifically defensible under modern
   multiple-testing governance?
2. How should Trading Bot reconcile iterative development with a genuinely protected evaluation
   boundary?
3. Should truncated-history invariance become a mandatory deterministic test across every future
   signal engine and decision output?
4. How should qualitative design changes be counted in the search ledger, not just numeric
   parameters?
5. Is a bounded parameter/model-averaging approach preferable to selecting a single optimized value
   for some signal families?
6. Which risk-sizing concepts from Kelly are useful as theory without adopting growth-optimal risk?
7. How should the project formally classify live underperformance into software, execution, model,
   regime and ordinary-noise causes?
8. Should mean-reversion and momentum be separate evidence families, regime states, or conditional
   interpretations of the same price data?
9. How much of Chan's mechanism-based momentum discussion survives at BTC's 15m–4h horizon?
10. Can "small capacity" be treated as a legitimate design constraint for finding edges unavailable
    to institutional-scale traders, without using it as an excuse for weak evidence?
11. What modern execution evidence is required before applying the book's general cost principles to
    BTCUSDT?
12. Which of the book's practitioner heuristics should be discarded rather than canonized because
    they are dated or insufficiently formal?
13. How should exits be conditioned on trade thesis without creating too many adaptive degrees of
    freedom?
14. Should paper/live reconciliation be a first-class product feature in addition to trade history?
15. How should the eventual system detect edge decay without repeatedly overreacting to short recent
    samples?

## 40. Durable source-derived knowledge retained

The durable points preserved from LIB-003 are:

1. quantitative trading can combine any machine-readable information, not just chart indicators;
2. simplicity and limited degrees of freedom are central defenses against data snooping;
3. strategy selection must consider implementation, capital, costs and capacity;
4. benchmark-relative performance, Sharpe and drawdown convey different information;
5. point-in-time data and causal timing are mandatory;
6. survivorship bias and execution assumptions can overwhelm apparent alpha;
7. hidden look-ahead can be detected using truncated-history invariance;
8. training and protected test data must play different roles;
9. a test set should not become a second training set after inspection;
10. sensitivity and simplification tests are valuable robustness diagnostics;
11. economically/rationally justified refinement is preferable to arbitrary historical curve fitting;
12. realistic transaction costs include more than commission;
13. paper trading tests both science and engineering;
14. backtest/live divergence should be diagnosed before strategy modification;
15. risk allocation depends on expected return, variance and correlation, but Kelly assumptions are
    fragile and leverage must be conservative;
16. fat-tail risk invalidates naive Gaussian confidence;
17. stop/exit logic should depend on the strategy mechanism;
18. mean reversion and trend can coexist at different horizons;
19. momentum can arise through information diffusion, large-order execution and herding;
20. competition can weaken mean reversion and shorten momentum horizons;
21. causal rolling optimization does not remove researcher-level model-selection bias;
22. cointegration and correlation are not interchangeable;
23. explanatory factors are not automatically predictive factors;
24. HFT requires execution realism beyond ordinary bar backtests;
25. small-capacity strategies can have a different competitive landscape from institutional
    strategies;
26. strategy edges can decay and require ongoing research;
27. scientific/model risk, software risk and operational risk must be treated separately;
28. systematic traders remain vulnerable to behavioral errors, especially reactive model changes
    after recent losses.

## 41. Final source disposition

`REVIEWED`

Reason:

- all 181 accessible PDF pages were reviewed;
- all 8 chapters and the MATLAB appendix were covered;
- the complete PDF was visually scanned;
- material tables/figures/examples were inspected;
- source claims were separated from Research Director interpretation;
- dated operational material was identified;
- unsupported BTC extrapolations were explicitly excluded;
- no outside source was used to fill gaps in the book.

This source is retained as a **foundational practitioner reference for quantitative research,
backtesting, execution, risk and strategy-development process**.

It does not authorize System G2, BTC backtesting, parameter calibration, paper orders or real capital.
