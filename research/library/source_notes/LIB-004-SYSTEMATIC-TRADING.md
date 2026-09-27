# LIB-004 — Systematic Trading — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-27  
Source file: `Systematic-Trading_-A-unique-new-method-for-designing-trading-and-investing-systems.pdf`  
Drive file id: `1TfhN_PXlmB1262Yz7FV3ZftYVSGQw-Aj`  
Local corpus id: `LIB-004`

## 1. Source identity

**Title:** *Systematic Trading: A Unique New Method for Designing Trading and Investing Systems*  
**Author:** Robert Carver  
**First published:** 2015  
**Publisher:** Harriman House  
**Artifact type:** professional/systematic-trading book  
**Corpus classification:** BOOK_TEXTBOOK  
**Evidence tier in project registry:** C  
**Local PDF length:** 359 pages

The book presents a modular framework for systematic investing/trading rather than one isolated
alpha strategy.

Carver explicitly designs the framework so it can be used by three different styles:

1. **asset allocating investor** — largely avoids directional forecasting and uses a constant
   positive forecast;
2. **semi-automatic trader** — makes discretionary directional forecasts but delegates risk,
   position sizing and exits to a systematic framework;
3. **staunch systems trader** — uses multiple systematic rules and combines them inside the full
   framework.

The source therefore distinguishes **forecast generation** from the rest of the trading system.

## 2. Study coverage

The complete accessible PDF was reviewed.

Coverage includes:

- preface and introduction;
- Part One — Theory;
- Part Two — Toolbox;
- Part Three — Framework;
- Part Four — Practice;
- all 15 chapters;
- epilogue;
- glossary;
- Appendices A–D;
- figures/tables via a full visual scan of all 359 PDF pages.

The chapters were read in order, not sampled only through index/search hits.

The technically central sections received additional attention:

- fitting / over-fitting;
- portfolio allocation;
- forecast construction and scaling;
- combined forecasts;
- volatility targeting;
- position sizing;
- portfolio construction;
- speed / transaction costs / capital constraints;
- systematic EWMAC and carry rule appendices;
- bootstrap optimisation;
- forecast/instrument diversification multipliers;
- volatility estimation.

No outside source was used to fill gaps in this dossier.

## 3. The book's central architecture

### SOURCE CLAIM — the trading system should be modular

Carver rejects a design in which entry, exit, risk, position size and portfolio allocation are mixed
together ad hoc.

The framework separates:

1. instruments;
2. trading rules / forecasts;
3. combined forecasts;
4. volatility target;
5. position sizing;
6. instrument/portfolio allocation;
7. trading and transaction-cost control.

Conceptually:

`market information -> forecast -> combined forecast -> risk-scaled position -> portfolio position -> trade`

A forecast is therefore **not a position**, and a position is not merely a signal vote.

### SOURCE CLAIM — systematic process can contain discretionary forecasts

A major feature of the book is that the framework does not require every directional opinion to be
generated algorithmically.

Carver permits:

- constant forecasts;
- discretionary forecasts;
- systematic forecasts,

provided they are converted into the same risk-aware framework.

This supports the broader concept that the **decision architecture** can be systematic even when
different sources of directional information are heterogeneous.

## 4. Human judgement and behavioural failure

Chapter 1 motivates systematisation primarily as protection against predictable human errors.

The source discusses:

- prospect-theory-like asymmetry;
- disposition effect;
- taking profits too early;
- allowing losses to run;
- overconfidence;
- excessive leverage;
- overtrading;
- meddling with a system after it is deployed.

Carver's preferred response is not maximum complexity.

He repeatedly favours systems that are:

- objective;
- simple;
- transparent;
- explainable;
- based on prior ideas rather than an unrestricted search of historical data.

### DIRECTOR INTERPRETATION

For Trading Bot, explainability is not merely a UI preference. In this source it is part of the
anti-overfitting and risk-control philosophy.

A future algorithm should ideally be able to explain:

- what information moved the forecast;
- what changed the position;
- what changed risk;
- what triggered or suppressed a trade.

## 5. Where returns may come from

Carver discusses several broad economic sources of returns / systematic opportunities.

These include, at a conceptual level:

- persistent risk premia;
- time-varying risk premia;
- skew premia;
- leverage constraints;
- liquidity / size premia;
- forced or constrained traders;
- provision of liquidity;
- barriers to entry / effort;
- behavioural effects;
- self-reinforcing technical effects;
- rarer forms of genuine alpha.

He strongly discourages treating a profitable historical pattern as sufficient explanation.

### SOURCE CLAIM — understand why the strategy might make money

The book repeatedly asks for an economic or behavioural reason that could plausibly support the
return source.

### LIMITATION

This taxonomy is general and multi-asset.

It does not establish which mechanism applies to BTCUSDT.

## 6. Ideas-first versus data-first research

### SOURCE POSITION

Carver distinguishes:

- **ideas first** — start from an economically or behaviourally defensible concept, then test a
  small number of implementations;
- **data first** — search a broad model/parameter space for patterns.

He generally prefers ideas-first systematic research.

He accepts that data-first approaches may make more sense in settings such as genuine high-frequency
research where very large samples exist and models can be continually refitted.

For the style of trading covered in this book, he considers unrestricted data mining highly
dangerous.

### Project relevance

This is compatible with our current knowledge-base programme:

- professional/source-grounded concepts first;
- implementation choices second;
- BTC evidence later.

It is not support for selecting a system from thousands of indicator combinations.

## 7. Backtesting, fitting and over-fitting

This is one of the most important sections of the book.

### 7.1 Backtest failure modes

Carver identifies problems including:

- over-fitting;
- forward-looking information;
- survivorship;
- unrealistic transaction costs;
- short-selling/implementation constraints;
- insufficient history;
- structural change;
- crowding.

### 7.2 In-sample fitting

The source strongly criticises selecting rules on the same history on which they are then reported.

Carver describes this as effectively using a time machine.

### 7.3 Out-of-sample methods

He discusses:

- fixed split / holdout approaches;
- expanding-window out-of-sample testing;
- rolling-window approaches.

His preference in many contexts is **expanding out-of-sample**, because it preserves more historical
information while maintaining temporal order.

Rolling windows may be justified when older history is genuinely less relevant, but shorter windows
increase estimation uncertainty.

### 7.4 Multiple testing

The book gives examples showing that when enough candidate rules or parameters are tested, apparently
excellent historical performers can emerge from noise.

Carver demonstrates that choosing the historical winner can be worse than:

- a random candidate;
- or blending multiple reasonable candidates.

### 7.5 How much data is needed?

The source repeatedly stresses that distinguishing realistic Sharpe ratios from zero, or one plausible
rule from another, can require many years or decades of history.

A few attractive years are therefore weak evidence.

### 7.6 Pooling across instruments

Carver strongly prefers generic rules fitted across many instruments instead of independently fitting
parameters for each individual market.

The rationale is statistical:

- more observations;
- less freedom to explain idiosyncratic noise;
- better chance of learning a general effect.

### 7.7 Carver's preferred fitting style

His preferred workflow is approximately:

1. begin with a small number of defensible rule ideas;
2. create a small number of variations;
3. choose variations based mainly on behaviour such as:
   - speed;
   - correlation/redundancy;
   - transaction cost;
4. do **not** select variations merely because they had the best historical P&L;
5. give weaker historical performers smaller weight only cautiously;
6. rarely set a plausible rule's weight to exactly zero on the basis of noisy performance.

### DIRECTOR INTERPRETATION

Carver permits development/calibration but attempts to constrain the degrees of freedom.

This is important for our final methodology debate:

the source does **not** support either extreme of:

- unrestricted iterative optimisation;
- or “never use development history to calibrate anything.”

It instead proposes ideas-first, bounded, uncertainty-aware calibration.

Cross-source reconciliation with López de Prado / Chan is deferred until final corpus synthesis.

## 8. An empirical illustration of over-fitting

One example examines many variants and shows that selecting a recent historical winner can perform
poorly subsequently.

The source's broader lesson is:

> the precision implied by a historical ranking is often much greater than the information actually
> contained in the sample.

### Project implication

Future Trading Bot diagnostics should preserve:

- all legitimate variants tried;
- the reason each was introduced;
- how candidate selection occurred.

A historical “winner” must not be treated as if it were the only system ever considered.

No specific validation protocol is frozen by this dossier.

## 9. Sharpe ratio, skew and realistic expectations

Carver uses Sharpe ratio extensively but repeatedly cautions against interpreting it alone.

### SOURCE CLAIM — skew matters

Two strategies with similar Sharpe ratios can carry very different risk.

The book distinguishes:

- positive-skew strategies — many small losses, occasional large gains;
- negative-skew strategies — frequent small gains, occasional large losses.

The second category can look deceptively attractive for long periods before suffering a severe loss.

### SOURCE CLAIM — very high persistent Sharpe ratios are suspicious

Carver argues that sustained high Sharpe ratios are rare in realistic systematic trading.

He uses conservative expectations throughout the framework and is skeptical of backtests claiming
extreme Sharpe performance without a compelling explanation.

### Project relevance

This argues against optimizing only:

- hit rate;
- smooth equity curve;
- historical Sharpe.

Tail behaviour and failure mode matter.

## 10. Portfolio allocation and the instability of optimisation

### SOURCE CLAIM — classic point-estimate optimisation is unstable

Mean-variance optimisation can produce extreme weights because expected returns are very noisy.

Small changes in estimates can cause large changes in the “optimal” portfolio.

Carver considers correlations materially more estimable than expected returns.

### Equal weights

Where expected returns, volatility and correlations are sufficiently similar, simple equal weighting
is difficult to beat reliably.

### Bootstrapping

The book recommends bootstrap-based portfolio construction as one robust approach.

The procedure is:

1. sample historical returns;
2. estimate means/correlations from the sample;
3. optimise that sample;
4. repeat many times;
5. average the resulting weights.

Block bootstrap is discussed when serial dependence requires consecutive observations to remain
together.

### Handcrafting

For users who cannot or do not want to bootstrap, Carver gives a hierarchical handcrafting approach:

- group related assets/rules;
- allocate within the groups;
- combine groups using approximate correlation structure.

The aim is robust allocation, not mathematical point optimality.

## 11. A particularly important distinction: certain versus uncertain information

This is one of the strongest concepts in the book for the Owner's earlier `peso_base + peso2`
discussion.

Carver treats adjustment magnitude differently depending on confidence in the information.

### Relatively certain information

Examples include known or reasonably measurable transaction-cost differences.

These can justify meaningful allocation adjustments.

### Uncertain historical performance information

Historical Sharpe differences receive much smaller adjustments.

The book's guidance becomes especially conservative with limited history.

In the framework described by Carver:

- more than roughly a decade of performance can justify a cautious historical-SR adjustment;
- with substantially less evidence, he often recommends **no performance-based adjustment**.

### DIRECTOR INTERPRETATION

This is not literally the Owner's proposed `peso_base × peso2` formula.

It is, however, a strong professional precedent for separating:

- stable structural allocation;
- from a smaller empirical modifier whose strength depends on evidence quality.

It argues against unrestricted optimisation of signal weights from historical P&L.

No Trading Bot numeric weight or modifier bound is derived here.

## 12. Forecasts: signed and continuous information

Carver defines a forecast as both:

- **direction**;
- **strength**.

It is not merely:

- buy;
- sell;
- neutral.

### Recommended standardisation in the source

Within Carver's own framework:

- forecasts are scaled so their long-run average absolute magnitude is approximately 10;
- values are capped around -20 / +20;
- long-only applications floor negative forecasts to zero.

These are author-specific conventions, not universal market truths.

### Why standardise?

Forecast standardisation makes heterogeneous rules comparable.

A given forecast magnitude should imply a similar amount of expected risk-adjusted opportunity,
regardless of the specific rule/instrument.

### Why cap?

The source's reasons include:

- sparse evidence in extreme signal states;
- risk containment;
- instability of very large signals;
- the possibility that extreme trends reverse;
- relatively little expected performance loss from limiting tails.

### DIRECTOR INTERPRETATION

This is highly relevant to Trading Bot's desired continuous prediction.

It supports separating:

- signal direction;
- signal strength;
- risk;
- eventual position/action.

It does **not** establish that Trading Bot should use Carver's numerical -20…+20 scale.

## 13. Forecast rescaling

Appendix D gives a procedure for rescaling a new trading rule.

The objective is not to maximize P&L.

Instead:

1. calculate historical raw forecast values;
2. find their average absolute magnitude across long histories / many instruments;
3. multiply by a scalar so average absolute forecast is around the framework target.

This is a **signal-scale calibration**, not performance optimisation.

### Project relevance

This is a useful conceptual distinction:

- calibrating the units of a signal;
- versus optimizing the signal for profitability.

The two should not be conflated in future research governance.

## 14. Systematic rule example: EWMAC trend

Appendix B specifies a trend-following rule based on fast and slow exponentially weighted moving
averages.

Core construction:

1. calculate fast EWMA;
2. calculate slow EWMA;
3. take their difference;
4. divide by recent price volatility;
5. apply a forecast scalar;
6. cap the final forecast.

The book uses a family of look-back pairs approximately:

- 2 / 8;
- 4 / 16;
- 8 / 32;
- 16 / 64;
- 32 / 128;
- 64 / 256 days.

The slow look-back is four times the fast one.

### SOURCE RATIONALE

The source deliberately uses several trend speeds because future trend length is unknown.

It avoids filling every possible intermediate speed because nearby variants become highly
correlated.

Carver uses a ~0.95 correlation threshold as a heuristic for pruning near-duplicate variants.

### LIMITATION

These are daily, multi-asset examples.

Nothing in this book validates these look-backs for BTC intraday forecasting.

### DIRECTOR INTERPRETATION

The deeper transferable lesson is **not** “use six moving-average rules.”

It is:

> represent materially different horizons, but avoid counting highly correlated variants as
> independent evidence.

## 15. Carry rule

Appendix B also specifies a carry forecast.

Depending on asset type, carry is built from economically appropriate financing/yield relationships.

Examples include:

- dividend yield versus funding;
- FX interest-rate differential;
- futures curve relationships.

The resulting expected return is:

- annualised;
- volatility-standardised;
- rescaled to the common forecast scale;
- capped.

### Project limitation

The literal futures carry formulation is not a BTC signal specification.

Crypto funding/perpetual basis may have superficially related concepts but cannot be assumed
equivalent without crypto-specific evidence.

## 16. Combining forecasts

This is one of the most relevant parts of the book.

### SOURCE CLAIM — combine with weights, not raw votes

Individual rule forecasts are combined using positive weights that sum to 100%.

Forecast variants that carry similar information should not receive the same total effective
influence as a set of independent rules.

### Correlation matters

Carver explicitly models correlation among forecasts/rule returns.

Highly correlated rules provide less diversification benefit.

### Forecast diversification multiplier

Because a diversified weighted average of forecasts has lower natural amplitude, the framework
applies a diversification multiplier based on weights and correlations.

The conceptual expression is:

`1 / sqrt(W × H × Wᵀ)`

where:

- `W` = weights;
- `H` = correlation matrix.

The source recommends flooring negative correlations at zero for this purpose, to avoid inflating
risk aggressively from unstable negative-correlation estimates.

Carver also places an upper cap on the multiplier in his own implementation.

### DIRECTOR INTERPRETATION

This is direct professional support for avoiding **indicator vote counting**.

If:

- several moving averages;
- MACD-like rules;
- multiple momentum transforms

are mostly expressions of the same underlying trend information, they should not automatically count
as several independent confirmations.

The exact correlation machinery for Trading Bot remains unfrozen.

## 17. Example of correlation-aware rule weighting

In the staunch-systems example, Carver combines:

- three relatively slow EWMAC trend variations;
- one carry rule.

The middle EWMAC variation receives less weight because it is more correlated with both neighboring
trend speeds.

The lesson is structural:

> weight can reflect marginal diversification/information, not merely standalone profitability.

This is highly relevant to the Owner's intended professional evidence engine.

It does not imply the example's numerical weights are appropriate for BTC.

## 18. Forecasts versus complete trading systems

The book repeatedly distinguishes:

- a rule that produces a forecast;
- from a complete position-management system.

A signal alone does not define:

- account risk;
- position size;
- portfolio allocation;
- trade execution;
- transaction costs.

### Project relevance

This is one of the strongest source-grounded reasons not to evaluate every Trading Bot information
family as though it must independently be a profitable standalone strategy.

A component can be useful as:

- directional information;
- risk input;
- diversification input;
- context,

without itself specifying the full trade.

The final role taxonomy for Trading Bot is deferred until corpus synthesis.

## 19. Volatility targeting

Carver treats the percentage volatility target as a central system-level choice.

### Concept

Choose an expected annualised portfolio volatility as a percentage of current trading capital.

As capital changes, the cash risk target changes.

### Kelly framework

The book discusses Kelly sizing as a theoretical upper bound under restrictive assumptions.

Carver recommends being substantially more conservative:

- Half-Kelly rather than full Kelly;
- further reduction for negatively skewed strategies;
- pessimistic rather than backtest-maximized Sharpe assumptions.

### Important caution

A system's historical Sharpe should be **degraded** before it informs risk.

The risk target should not inherit backtest optimism.

### Project relevance

This supports explicitly separating:

- evidence about expected return;
- from allowable risk exposure.

It does not authorize the author's risk percentages for Trading Bot.

## 20. Position sizing

The framework converts a forecast into a position through volatility scaling.

Conceptually:

- estimate daily instrument price volatility;
- translate it into currency risk per instrument block;
- divide desired daily cash risk by that instrument risk;
- multiply by forecast strength.

Within the author's notation:

`subsystem position ∝ volatility scalar × forecast`

### Important implication

For the same directional forecast:

- higher market volatility -> smaller position;
- lower market volatility -> larger position.

### Low-volatility danger

Carver repeatedly warns that very low measured volatility can produce dangerously large leverage if
the system assumes the low-vol regime will persist.

### Project relevance

Volatility is therefore principally a **risk/sizing state**, not automatically a directional vote.

This distinction is important for our future signal-role taxonomy.

## 21. Volatility estimation

The book uses relatively simple recent-volatility estimates.

It discusses:

- simple moving standard deviation;
- exponentially weighted estimates.

Carver prefers simple, robust look-backs rather than optimizing the exact volatility window.

For his standard daily framework, he uses an approximately five-week recent-volatility horizon,
with an EWMA equivalent.

For slower/expensive systems he sometimes recommends slower volatility estimates to reduce turnover.

### LIMITATION

The author's daily windows are design choices for his framework, not BTC 1m/15m/1h/4h parameters.

## 22. Portfolio construction

The final position in an instrument is a function of:

- subsystem position;
- instrument weight;
- instrument diversification multiplier.

The book aims to equalize/allocate risk rather than simply allocate equal cash amounts.

### Diversification

Carver repeatedly describes diversification as one of the most robust sources of improved
risk-adjusted performance.

In his multi-asset context, adding genuinely different instruments can be more valuable than adding
many highly similar rules.

### Important limitation for Trading Bot

The Owner's initial product is intentionally single-asset BTCUSDT.

We cannot import Carver's cross-asset diversification benefit into the initial product by pretending
that several correlated indicators are independent assets.

This makes redundancy control among signal families even more important.

## 23. Position inertia

The source introduces a practical cost-control rule:

do not trade when the current position is already sufficiently close to the desired target.

Carver uses approximately a 10% tolerance in his examples.

The intended effect is:

- substantially lower turnover;
- little loss of pre-cost performance for sufficiently slow systems.

### DIRECTOR INTERPRETATION

The exact 10% threshold should not be copied blindly.

The broader concept may later map to an **actionability/execution hysteresis layer**:

a forecast can change without requiring a trade whenever the economic improvement is too small
relative to execution cost.

This is potentially very relevant to LONG / SHORT / NO_TRADE.

## 24. Trading costs as a design input

Chapter 12 treats transaction cost as part of strategy design, not an afterthought.

Costs include:

- execution cost/spread;
- per-ticket charges;
- per-unit charges;
- value-based taxes/fees;
- additional holding/financing costs where relevant.

### Standardised cost

The book expresses round-trip cost in risk-adjusted units by dividing it by the instrument's
annualised risk scale.

This allows costs to be compared across instruments.

### Turnover

Turnover is defined in volatility-standardised round trips.

The principal source of turnover for dynamic systems is typically forecast changes.

Other sources include:

- volatility estimate changes;
- account-capital changes;
- FX changes;
- changes to system parameters.

### SOURCE CLAIM — cost is more predictable than gross edge

Carver argues that transaction costs can often be estimated with greater confidence than historical
differences in pre-cost Sharpe.

Therefore a faster rule needs strong evidence that its extra gross return compensates for its
relatively certain extra cost.

### Speed limit

The author creates a “speed limit”:

do not allow expected annual trading cost to consume too large a fraction of a pessimistic expected
gross edge.

His own examples use a maximum around one-third of expected gross Sharpe.

These are author-specific heuristics, not universal constants.

### Day trading

Within the instrument/cost environment discussed in the 2015 book, Carver argues that day trading
requires:

- unusually high gross edge;
- extremely low execution cost;
- or consistent spread capture.

### Project relevance

For BTC, the exact numbers are obsolete/non-transferable.

The durable principle is:

> trading frequency should be justified by **net** expected edge, not by raw signal responsiveness.

## 25. Execution and account size

### Small trader assumption

When order size is below available inside-market depth, the book uses half-spread as a conservative
simplified execution cost in several examples.

### Large trader

When orders exceed available top-of-book size, simple half-spread assumptions become invalid.

The source discusses:

- walking the book;
- posting large visible orders;
- information leakage;
- splitting orders;
- execution algorithms.

### Small accounts

At the other extreme, indivisible contract size causes **lumpy risk**.

A target position might vary continuously while the tradable position remains unchanged because a
fractional contract cannot be traded.

### Project relevance

The simulator must eventually distinguish:

- continuous theoretical target;
- tradable rounded target;
- actual fill.

For BTC spot the minimum-size problem differs from futures, but the distinction remains conceptually
important.

## 26. Semi-automatic trader example

The semi-automatic example uses human forecasts but systematic:

- forecast scaling;
- stop loss;
- volatility estimate;
- position sizing;
- portfolio constraints;
- risk targeting.

Carver strongly discourages changing the original directional forecast after a position is opened,
because doing so can reintroduce disposition-effect behavior.

He instead uses a systematic trailing stop.

### Important qualification

This is an example architecture, not a universal exit rule.

The author himself notes that mean-reverting/relative-value systems can require different exit logic.

### Project relevance

The interesting durable point is that:

> directional opinion and position-management logic can be governed separately.

Trading Bot is not required to adopt Carver's stop system.

## 27. Asset-allocator example

The asset-allocator example deliberately assumes no forecasting edge:

- constant positive forecast;
- volatility scaling;
- diversified risk allocation;
- slow rebalancing;
- robust portfolio weights.

The example demonstrates that the framework can function even when expected return forecasts are
weak.

When discretionary long-run return views are introduced, Carver recommends only **small/infrequent**
weight tilts because expected returns are highly uncertain and extra adjustments generate cost.

### Project relevance

This reinforces the source's broader treatment of uncertain information:

uncertain directional belief should not automatically cause large position changes.

## 28. Staunch systems trader example

This is the closest example to an automated algorithm.

The example uses:

- multiple futures;
- EWMAC trend rules at several speeds;
- carry;
- forecast scaling;
- forecast weights;
- correlation-aware diversification;
- volatility target;
- instrument weights;
- cost constraints;
- position inertia.

### Important design choice

Carver requires several slow EWMAC variants because he finds insufficient evidence to identify one
specific speed as reliably superior.

He then combines them instead of choosing a historical winner.

### DIRECTOR INTERPRETATION

This is a strong professional example of **model averaging under parameter uncertainty**.

For Trading Bot later, a similar principle might mean:

- represent a family at several materially distinct horizons;
- aggregate rather than select the historical champion;
- correct for correlation/redundancy.

No such implementation is authorized yet.

## 29. Practical EWMAC details from Appendix B

The book's EWMAC example can be summarized as:

`raw trend = EWMA_fast(price) - EWMA_slow(price)`

then:

`vol-adjusted trend = raw trend / recent price-risk scale`

then:

`forecast = scalar × vol-adjusted trend`

then cap the forecast.

The author derives scalars from average forecast magnitude across many markets, not from maximizing
historical P&L.

### Important methodological distinction

This is **normalization**.

It should not be confused with optimizing the rule for profitability.

## 30. Carry details from Appendix B

The carry rule estimates what an asset would earn if spot/underlying conditions were otherwise
unchanged, after accounting for asset-specific financing/yield relationships.

It is then:

- annualised;
- divided by annualised volatility;
- rescaled;
- capped.

Carver suggests updating slowly enough to avoid noisy turnover.

### Project relevance

Carry is an example of a signal with a different economic mechanism from trend.

The broader architectural lesson is that combining **different mechanisms** is more valuable than
combining many formulas for the same mechanism.

## 31. Bootstrap details from Appendix C

Carver's bootstrap portfolio procedure:

1. resample historical returns;
2. estimate return/correlation structure;
3. optimise;
4. repeat;
5. average the resulting allocations.

If temporal dependence matters, block bootstrap is preferred over independently sampled days.

The author suggests a sample block length on the order of a fraction of the available historical
period rather than a tiny window.

He emphasizes that:

- more bootstrap iterations improve numerical stability with diminishing benefit;
- bootstrapping is not magic;
- it is mainly a way to represent uncertainty instead of pretending point estimates are exact.

## 32. Correlation heuristics

Appendix C contains rule-of-thumb correlations for:

- asset classes;
- instruments within regions;
- dynamic trading subsystems;
- different rule styles;
- variants of the same rule.

One especially relevant source idea:

- different styles are expected to be less correlated than variants within one style;
- adjacent EWMAC speeds are highly correlated.

### Project limitation

These numeric correlation tables are based on the author's multi-asset research/context and should
not be copied into Trading Bot.

The principle — **measure redundancy before aggregating evidence** — is durable.

## 33. Diversification multiplier details

Appendix D defines the same mathematical structure for:

- forecast diversification;
- instrument diversification.

The multiplier rises as components become less correlated.

The source floors negative correlations at zero before the calculation to avoid dangerously large
multipliers driven by uncertain negative-correlation estimates.

This is another example of Carver deliberately preferring conservative uncertainty treatment over
mathematically aggressive optimization.

## 34. Practical philosophy from the epilogue

Carver's closing principles are unusually consistent with the rest of the book:

- humility;
- pessimistic expectations;
- skepticism toward backtests;
- simplicity;
- understand the economic reason for returns;
- know transaction costs;
- diversify;
- use conservative risk;
- avoid low-volatility leverage traps;
- design carefully;
- then avoid constant meddling.

He explicitly acknowledges that a correctly designed system can still lose because luck remains
irreducible.

## 35. What this source suggests for a future Trading Bot architecture

The following are **Research Director interpretations from LIB-004**, not final design decisions.

### 35.1 Weight is not the algorithm

This source strongly supports the distinction.

A complete system contains at least:

- information/forecast engines;
- forecast normalization;
- aggregation;
- risk estimation;
- sizing;
- portfolio/exposure logic;
- transaction-cost/actionability logic.

Changing a signal weight is only one of many possible design decisions.

### 35.2 Family-level representation is preferable to indicator voting

Several highly correlated trend transforms should not automatically have multiple independent votes.

Potential later architecture:

- group related measures by information family;
- assess within-family redundancy;
- combine different mechanisms more strongly than cosmetic variants.

### 35.3 Base structural importance plus cautious empirical modification has precedent

Carver's handling of weights gives a professional precedent for:

- stable structure;
- correlation-aware allocation;
- stronger adjustment for known quantities such as costs;
- much weaker adjustment for noisy historical performance.

This does not prove our exact `peso_base / peso2` design but supports investigating it.

### 35.4 Signal strength should be continuous

Carver's forecast framework makes direction and magnitude explicit.

This is highly compatible with the Owner's continuous prediction requirement.

### 35.5 Volatility is primarily a risk state

Volatility changes position size and affordability.

It need not be treated as a bullish/bearish vote.

### 35.6 Actionability can differ from forecast

Position inertia and cost-based speed limits demonstrate that:

- a forecast can move;
- target position can change;
- yet no trade is economically justified.

This is conceptually close to separating:

- prediction;
- conviction;
- actionability;
- LONG / SHORT / NO_TRADE.

### 35.7 Calibration should distinguish scale from edge

Forecast normalization can be calibrated from historical behavior without fitting P&L.

This is potentially useful for a future governance model that separates:

- signal normalization;
- contextual interpretation;
- profitability calibration.

### 35.8 Multiple horizons can be averaged rather than optimized to one winner

Carver's trend example explicitly embraces parameter uncertainty.

The future system should investigate whether multiple professional horizons can coexist as a family
rather than choose one backtest-optimal horizon.

## 36. What this source does NOT support

LIB-004 does **not** establish:

- any BTCUSDT edge;
- any optimal BTC timeframe;
- any cycle signal;
- any crypto order-flow signal;
- any funding/OI rule;
- any 15m/1h/4h parameter;
- any Trading Bot numeric base weight;
- any `peso2` range;
- that EWMAC is the best trend representation;
- that carry is useful for BTC;
- that Carver's forecast range must be used;
- that a forecast cap of 20 is optimal for BTC;
- that a 10% position-inertia band is optimal;
- that a 25/36-day volatility lookback is optimal;
- that Half-Kelly is automatically safe for this project;
- that author's cost thresholds remain appropriate in 2026 crypto;
- that a cross-asset portfolio architecture transfers unchanged to a single-asset BTC product.

## 37. Important limitations

### 37.1 Market universe mismatch

The book is predominantly multi-asset and futures-oriented.

Trading Bot initially trades BTCUSDT only.

Cross-asset diversification is therefore unavailable in V1.

### 37.2 Horizon mismatch

Much of the framework operates at daily to multi-week/month horizons.

The Owner's product includes substantially shorter decision horizons.

Transferability of parameter values is unproven.

### 37.3 Publication date

First published in 2015.

Market technology, execution cost, electronic liquidity and the crypto ecosystem have changed
materially.

### 37.4 Author heuristics versus universal results

Several values are practical recommendations from Carver's experience/research rather than
universal laws:

- forecast target scale;
- forecast cap;
- diversification-multiplier cap;
- speed-limit fractions;
- volatility look-backs;
- position-inertia threshold;
- correlation rules of thumb;
- risk targets.

Preserve the **principles**, not the numbers, unless later evidence supports the numbers.

### 37.5 No crypto evidence

The source does not study:

- BTC;
- perpetual futures;
- crypto funding;
- liquidation cascades;
- 24/7 crypto microstructure.

## 38. Durable source-derived knowledge retained from LIB-004

The following points are strong enough to preserve for final corpus synthesis:

1. A trading system should separate forecast generation from risk, sizing, allocation and trading.
2. Forecasts are best represented as signed continuous strength, not only binary decisions.
3. Heterogeneous forecasts should be normalized onto a comparable scale before combination.
4. Forecast normalization can be calibrated independently of historical profitability.
5. Correlated rule variants should not be treated as independent evidence.
6. Combining several plausible variants can be safer than selecting the historical winner.
7. Different economic mechanisms are more valuable sources of diversification than cosmetic
   variations of one mechanism.
8. Ideas-first research materially reduces the degrees of freedom relative to unconstrained data
   mining.
9. Development/calibration is permissible in Carver's framework, but search size and uncertainty
   must be constrained.
10. Expanding/rolling temporal validation is preferable to forward-looking fitting.
11. Historical performance differences are much more uncertain than known cost differences.
12. Stable structural weights with modest evidence-dependent adjustments are preferable to fragile
   point-optimal weights.
13. Volatility scaling is primarily a risk/sizing mechanism.
14. Skew/tail behaviour matters even when Sharpe looks attractive.
15. Very low measured volatility can cause dangerous leverage if sizing is purely inverse-volatility.
16. Transaction cost must be included when deciding how fast a strategy is allowed to react.
17. Expected cost may be estimated more reliably than small differences in expected gross alpha.
18. Forecast changes do not always justify trades; an execution/actionability layer can suppress
   economically pointless turnover.
19. Signal direction, risk target, target position and actual trade are distinct system states.
20. Risk should be based on pessimistic expectations, not the best historical backtest.
21. Full-system robustness matters more than finding the single historically best rule.
22. Single-asset Trading Bot cannot claim Carver's multi-asset diversification benefit merely by
   adding many correlated indicators.

## 39. Questions for Astra at final corpus review

1. Which parts of Carver's modular architecture should transfer directly to a single-asset BTC
   decision engine?
2. Should Trading Bot adopt a formal distinction among:
   - raw measurement;
   - normalized signal;
   - interpreted family forecast;
   - aggregate prediction;
   - actionability;
   - execution?
3. Is a family-level base importance plus bounded empirical modifier scientifically preferable to
   direct optimisation of all signal weights?
4. What evidence should determine the permitted magnitude of empirical weight adjustment?
5. Should multiple signal horizons be model-averaged rather than one horizon selected by
   backtest?
6. What is the correct way to account for correlated indicators within one family?
7. Can Carver's forecast-normalisation concept be adapted without importing the arbitrary -20…+20
   scale?
8. How should Trading Bot distinguish signal-scale calibration from profitability calibration in
   governance?
9. Can position inertia be reframed as an actionability threshold based on expected incremental
   benefit versus transaction cost?
10. Which of Carver's risk ideas remain valid at BTC's 24/7 intraday horizon?
11. How much of the book's cost-speed argument survives under current BTC spot/perpetual market
   structure?
12. Should the eventual architecture use trend representations such as EWMAC, or treat EWMAC only
   as one implementation candidate within a broader professional trend family?
13. How should Carver's permissive-but-constrained fitting philosophy be reconciled with stricter
   anti-backtest-feedback literature?
14. In a BTC-only system, what can replace the robustness benefit Carver obtains from broad
   cross-asset diversification?
15. Which author heuristics should be explicitly prohibited from entering the system until
   BTC-specific evidence exists?

## 40. Final source disposition

`REVIEWED`

Reason:

The complete accessible 359-page PDF has been studied, including:

- every chapter;
- all four parts;
- epilogue;
- glossary;
- Appendices A–D;
- full-page visual scan;
- additional review of the fitting, weighting, forecast, risk, position-sizing, portfolio,
  cost/speed and rule-definition sections.

Source claims have been separated from Research Director interpretations.

No Trading Bot strategy, numeric signal weight, BTC parameter, System G2 design or market experiment
is authorized by this dossier.

LIB-004 should be retained as a **foundational source for systematic system architecture, forecast
combination, robust weighting, risk normalization and cost-aware implementation**, not as proof of
BTC profitability.
