# LIB-020 — Trading and Exchanges: Market Microstructure for Practitioners — Source Dossier

Status: **REVIEWED — COMPLETE ACCESSIBLE SOURCE READ**  
Study date: 2026-09-26  
Source file: `Trading and Exchanges_ Market Microstructure for Practitioners - FULL -.pdf`  
Drive file id: `10eSdyQLw64madko3fb3h68Ak83uRxOER`  
Local corpus id: `LIB-020`

## 1. Source identity

**Title:** *Trading and Exchanges: Market Microstructure for Practitioners*  
**Author:** Larry Harris  
**Publisher:** Oxford University Press  
**Copyright:** 2003  
**Series:** Financial Management Association Survey and Synthesis Series  
**Artifact type:** professional/academic textbook  
**Corpus classification:** BOOK_TEXTBOOK  
**Evidence tier in project registry:** C

The local PDF contains 657 physical PDF pages. The printed book runs through approximately page
620 plus bibliography and index. It contains 29 chapters.

This source is a comprehensive textbook about **market microstructure**: how trading actually occurs,
who trades, why they trade, how orders and market structures work, where liquidity comes from,
why spreads and transaction costs exist, how informed and uninformed traders interact, and how
execution affects realized performance.

It is explicitly **not** a book about fundamental valuation of securities or about constructing one
specific profitable trading strategy.

## 2. Study coverage

The complete accessible PDF was reviewed.

Coverage included:

- front matter / scope;
- all 29 chapters;
- chapter examples and boxed practitioner cases where materially relevant;
- figures and tables via full-document visual scan;
- bibliography/index inspection;
- deeper study of the operationally critical chapters:
  - Ch. 4 — Orders and Order Properties;
  - Ch. 6 — Order-driven Markets;
  - Ch. 10 — Informed Traders and Market Efficiency;
  - Ch. 11 — Order Anticipators;
  - Ch. 13 — Dealers;
  - Ch. 14 — Bid/Ask Spreads;
  - Ch. 16 — Value Traders;
  - Ch. 18 — Buy-Side Traders;
  - Ch. 19 — Liquidity;
  - Ch. 20 — Volatility;
  - Ch. 21 — Liquidity and Transaction Cost Measurement;
  - Ch. 22 — Performance Evaluation and Prediction.

The book predates modern crypto exchanges, perpetual futures and the current HFT ecosystem. Historical
institution names, trading-floor practices, settlement conventions and exchange-specific rules must
therefore be separated from the enduring economics of microstructure.

## 3. What the book is fundamentally saying

### SOURCE CLAIM — trading is a search problem

A central organizing idea is that trading requires buyers and sellers to find each other under
constraints of:

- time;
- price;
- information;
- size;
- trust/credit;
- market rules.

Markets, brokers, dealers and exchanges reduce those search costs in different ways.

This perspective explains why liquidity is valuable and why immediacy has a price.

### SOURCE CLAIM — trading is competitive and approximately zero-sum relative to the market

Harris repeatedly frames speculative trading as a competitive game.

For one trader to earn excess trading profits, another party ultimately bears the corresponding
relative loss or cost.

The important implication is not merely that someone loses on each trade. It is that a successful
speculator needs a **comparative advantage**, not just an apparently sensible signal.

### SOURCE CLAIM — liquidity is a service with a price

Liquidity is the ability to trade desired size, when desired, at low cost.

The book treats liquidity as multi-dimensional. Important dimensions include:

- **width** — price cost / spread;
- **depth** — quantity available near the market;
- **immediacy** — how quickly a trade can be completed;
- **resilience** — how quickly price/liquidity recover after temporary order-flow pressure.

Impatient traders generally **buy liquidity**.

Patient traders can attempt to **supply liquidity**, but in doing so they accept execution uncertainty
and adverse-selection risk.

### SOURCE CLAIM — market orders and limit orders exchange different risks

Market orders primarily exchange price certainty for execution certainty:

- execution is likely/fast;
- final price is uncertain;
- spread/market impact are paid.

Limit orders primarily exchange execution certainty for price control:

- price is controlled;
- execution may never occur;
- the order gives the market an option to trade against the submitter;
- the submitter is exposed to adverse selection.

There is therefore no universally superior order type.

The correct choice depends on urgency, liquidity price, order-book state, consequences of non-fill
and information risk.

## 4. Trader taxonomy

The book's trader taxonomy is one of its most useful contributions for Trading Bot.

### 4.1 Utilitarian traders

These traders primarily use markets to solve non-speculative problems:

- investors;
- borrowers;
- hedgers;
- asset exchangers;
- gamblers and other non-profit-maximizing participants.

Their willingness to trade for reasons other than superior information creates opportunities for
profit-motivated participants.

### 4.2 Informed speculators

Harris separates informed traders into distinct mechanisms.

#### Value traders

Estimate fundamental value and buy when price is below their estimate or sell when above it.

They can supply depth and resilience when uninformed order flow pushes prices away from perceived
value.

They face:

- adverse selection;
- estimation error;
- the winner's curse.

#### News traders

Act on new information about fundamental values before the information is fully reflected in price.

Their advantage decays as information becomes public.

#### Information-oriented technical traders

Search for systematic price patterns indicating that current prices may not fully reflect available
information.

This is an important conceptual qualification:

the book does **not** present "technical analysis" as a collection of magical independent indicators.
It treats technical trading as potentially informed only when the observed pattern reflects an
informational inefficiency.

#### Arbitrageurs

Compare related instruments and trade inconsistencies.

They help enforce the law of one price and connect liquidity/information across markets.

The book stresses that apparent arbitrage can be false if the trader misunderstands:

- carry;
- financing;
- basis;
- settlement;
- instrument differences;
- execution costs.

### 4.3 Order anticipators

These traders profit from information about **other traders' future orders**, rather than fundamental
value.

Examples include:

- front runners;
- quote matchers;
- sentiment-oriented technical traders;
- squeezers.

The book generally treats them as parasitic on other order flow.

### 4.4 Bluffers / manipulators

Attempt to make others misinterpret:

- information;
- order flow;
- price movements.

Examples include rumormongers and price manipulators.

The practical lesson is that a price move or order-flow imbalance cannot automatically be interpreted
as fundamental information.

### 4.5 Dealers / liquidity suppliers

Dealers sell immediacy.

They try to:

- buy and then resell;
- sell and then rebuy;
- keep inventory near target;
- balance order flow;
- avoid being systematically selected against by better-informed traders.

Their problem is not directional forecasting in the same sense as a speculator. It is pricing
liquidity while managing inventory and information risk.

## 5. Information, price discovery and market efficiency

### SOURCE CLAIM — informed trading makes prices more informative

Informed traders move prices toward their estimates of fundamental value.

Uninformed flow can temporarily move price away from those values.

Market prices become informative through a competitive process in which participants trade on their
information.

### SOURCE CLAIM — perfectly informative prices create a paradox

If prices instantly reflected all costly information, traders would have little reason to acquire and
trade on that information.

The book therefore treats real-world market efficiency as a balance between:

- information acquisition;
- trading costs;
- liquidity;
- competition.

### SOURCE CLAIM — comparative advantage matters more than absolute competence

A trader may be intelligent, disciplined and analytically strong yet still have no reason to earn
excess profits if competitors possess the same or better information/resources.

The book's recurring question is effectively:

> Why should this trader win, and why should the other side lose?

This is stronger than merely asking whether a pattern has looked profitable historically.

## 6. Orders and order-book economics

### 6.1 Market orders

Market orders are appropriate when completion is sufficiently valuable relative to liquidity cost.

Risks include:

- spread;
- slippage;
- price impact;
- uncertain final price for larger orders.

Large market orders can walk available liquidity and therefore have highly nonlinear execution cost.

### 6.2 Limit orders

Limit orders supply liquidity but expose the trader to:

- non-execution;
- partial execution;
- stale pricing;
- adverse selection;
- queue/precedence effects;
- missed-trade opportunity cost.

A favorable quoted price does not imply a favorable realized decision if the order fills primarily
when the counterparty knows more.

### 6.3 Stop orders and momentum

The book notes that stop orders demand liquidity after price moves and can add momentum to price
movements.

It distinguishes momentum trading from contrarian trading in market-impact terms:

- momentum traders buy into rises / sell into declines;
- contrarians do the opposite.

Harris discusses momentum as potentially destabilizing in specific microstructure contexts.

This is **not** evidence that momentum strategies are generally unprofitable.

### 6.4 Precedence and queue rules

Price priority is usually primary.

Other possible priorities include:

- time;
- public order;
- display;
- size.

Market rules change the value of displaying liquidity and therefore change participant behavior.

This is directly relevant to any future realistic limit-order simulator.

## 7. Order exposure and information leakage

One of the strongest practitioner themes in the book is **order exposure**.

Large traders need counterparties to discover their interest, but exposing too much can:

- reveal urgency;
- reveal information;
- invite front-running;
- make counterparties withdraw;
- worsen price.

Exposing too little can:

- prevent counterparties from finding the order;
- increase missed-trade risk;
- lengthen execution.

The book repeatedly frames skilled large-order execution as the art of deciding:

- when to expose;
- how much to expose;
- to whom;
- through which venue/intermediary.

Large orders are therefore often split or selectively exposed.

### RESEARCH DIRECTOR INTERPRETATION

For Trading Bot, a paper trade should not be evaluated as though a desired entry price automatically
means the entire desired position can be obtained at that price.

Even though V1 position size is small enough that BTC market impact may often be modest, the system
still needs to distinguish:

- signal timestamp;
- order decision;
- order submission;
- fill;
- fill price;
- non-fill;
- delay.

## 8. Dealers, spreads and adverse selection

### SOURCE CLAIM — spreads pay for more than mechanical service

Bid/ask spreads compensate liquidity suppliers for several costs and risks, including:

- operating/business costs;
- inventory risk;
- adverse selection;
- option value granted by standing quotes/orders.

### SOURCE CLAIM — adverse selection is structurally important

A liquidity supplier loses when a better-informed trader selectively trades against stale quotes.

For a dealer:

- informed buyers tend to arrive before price rises;
- informed sellers tend to arrive before price falls.

This creates inventory imbalances that are negatively related to subsequent price changes.

Realized spreads can therefore be much smaller than quoted spreads and may even be negative.

### SOURCE CLAIM — trade size contains information

Larger orders can imply greater information risk.

Liquidity suppliers may therefore widen prices or reduce size when they suspect informed demand.

### RESEARCH DIRECTOR INTERPRETATION

This book gives a strong reason to keep **execution state** separate from **directional signal state**.

A bullish forecast does not answer:

- whether current ask liquidity is expensive;
- whether spread is abnormal;
- whether the move has already consumed near-book depth;
- whether entering now is likely to suffer adverse price selection.

## 9. Value traders, depth and resilience

Harris treats value traders as important suppliers of liquidity beyond the inside quote.

They become especially relevant when:

- uninformed flow pushes price away from perceived value;
- dealers are unwilling to absorb more inventory.

Their willingness to trade can make markets more resilient.

However, they face the winner's curse:

when many informed/competent participants estimate an uncertain common value, being the trader
most willing to transact can itself be evidence that one's estimate is overly optimistic/pessimistic.

### PROJECT LIMITATION

BTC does not have a single uncontested fundamental-value model supplied by this book.

Therefore this concept cannot be converted directly into a BTC "value" signal merely because Harris
uses the term value trader.

## 10. Liquidity

The book defines liquidity operationally rather than as a single indicator.

A liquid market supports:

- meaningful size;
- fast execution;
- low price concession.

Different liquidity suppliers solve different parts of the problem:

- market makers -> immediacy;
- block dealers -> size/depth;
- value traders -> depth/resilience;
- arbitrageurs -> transfer of liquidity across linked markets;
- public limit-order traders -> displayed supply.

### RESEARCH DIRECTOR INTERPRETATION

A future Trading Bot should probably treat liquidity as a **state/family of information**, not one
scalar indicator.

Potential dimensions suggested by the source include:

- spread / width;
- available depth;
- time-to-fill / immediacy;
- post-impact recovery / resilience.

No numeric implementation is frozen by this dossier.

## 11. Volatility: fundamental vs transitory

Harris distinguishes:

### Fundamental volatility

Unexpected changes in genuine instrument value/information.

This volatility is necessary for prices to reflect new information.

### Transitory volatility

Price changes caused by trading pressure, especially uninformed/impatient trading, that are not
fully supported by value changes.

Transitory effects tend to reverse and are linked to:

- illiquidity;
- transaction costs;
- temporary order-flow imbalances.

### SOURCE CAUTION

The two components are difficult to separate empirically.

Short-run negative serial correlation can indicate transitory price effects, but similar-looking
patterns may arise for other economic reasons.

### RESEARCH DIRECTOR INTERPRETATION

This is directly relevant to the distinction between:

- **directional information**;
- **temporary execution/order-flow displacement**.

A sharp move caused by temporary liquidity consumption may deserve a different interpretation from a
move reflecting durable information.

The book does not provide a BTC-ready classifier for the two.

## 12. Transaction costs

Chapter 21 is highly relevant to Trading Bot.

The source divides transaction costs into:

### Explicit costs

Examples:

- commissions;
- exchange fees;
- taxes;
- trading infrastructure/personnel costs.

### Implicit costs

Examples:

- bid/ask spread;
- market impact;
- price concessions caused by one's own trading.

### Missed-trade opportunity costs

A passive order that fails to fill can cost more than an aggressively executed order if the desired
move subsequently occurs without the trader.

This means:

> cheapest fill price is not automatically best execution.

Execution aggressiveness must balance:

- direct/implicit cost;
- probability of fill;
- opportunity cost of non-fill.

## 13. Transaction-cost measurement

The book discusses several benchmark frameworks.

### Effective spread

Uses a contemporaneous quote midpoint as the benchmark around the executed trade.

It measures how far execution occurred from a contemporaneous value proxy.

### Realized spread

Uses a later quote midpoint.

The difference between effective and realized spread can reveal how much liquidity suppliers lost
to subsequent adverse price movement / informed trading.

### Implementation shortfall

Uses a pre-trade decision benchmark, commonly the quote midpoint around the time the manager decided
to trade.

It compares the realized portfolio with a hypothetical paper portfolio and can include both:

- completed-trade execution cost;
- unfilled-order opportunity cost.

### VWAP and other benchmarks

VWAP and daily open/close benchmarks are widely used, but benchmark choice changes interpretation and
can be gamed.

No transaction-cost estimator is noiseless.

### SOURCE CLAIM — many observations are required

Execution-quality estimates can be very noisy because prices move for many reasons unrelated to the
broker/order.

Evaluation needs sufficiently many trades.

### RESEARCH DIRECTOR INTERPRETATION

A future Trading Bot trade autopsy should not report only:

`entry price -> exit price -> P&L`.

It should preserve enough data to separate:

- forecast correctness;
- entry timing;
- spread/slippage;
- fill delay;
- partial/non-fill effects;
- missed opportunity.

## 14. Performance evaluation: skill vs luck

Chapter 22 is especially important scientifically.

### SOURCE CLAIM — past performance alone is a weak predictor

Observed performance combines:

- skill;
- market/environment effects;
- unpredictable luck.

Even sophisticated statistical methods often struggle to distinguish skill from luck over realistic
human samples.

### SOURCE CLAIM — sample-selection bias is dangerous

Winners are more visible than losers.

People also tend to:

- remember successful trades;
- forget failed trades;
- attribute their own successes to skill;
- attribute failures to bad luck.

The source treats these biases as serious obstacles to judging trading ability.

### SOURCE CLAIM — comparative advantage provides a stronger economic framework

Harris argues that long-run winners need a reason to outperform competitors.

Potential trader-level contributors include:

- intelligence;
- experience;
- education/training;
- creativity;
- memory;
- discipline;
- organization;
- drive;
- data access.

Firm-level contributors include:

- qualified personnel;
- information resources;
- research capability;
- organizational structure;
- internal controls;
- trading facilities;
- leadership.

But even possessing these qualities is only an **absolute advantage** unless they exceed what the
relevant competitors possess.

### RESEARCH DIRECTOR INTERPRETATION

For Trading Bot, a profitable development backtest should never be treated as sufficient evidence
that the algorithm has an edge.

The stronger research question is:

> What information/process/resource creates a repeatable comparative advantage after costs, and why
> should counterparties systematically be willing or forced to trade against it?

This is compatible with, but conceptually different from, pure statistical significance testing.

## 15. Market manipulation and deceptive flow

The book warns that market-observed information can be strategically generated.

Examples include:

- misleading rumors;
- manipulative trading;
- front-running;
- stop exploitation;
- bluffing;
- squeezes.

### RESEARCH DIRECTOR INTERPRETATION

Future order-flow / volume / short-horizon momentum features should not be interpreted as though every
observed trade reflects independent information about fundamental direction.

The possibility of:

- strategic trading;
- forced trading;
- inventory management;
- hedging;
- liquidation;
- anticipation

means that the **origin of flow** matters.

This source does not provide an algorithm that identifies those origins.

## 16. Market structure and venue design

The book compares:

- quote-driven;
- order-driven;
- brokered;
- call-auction;
- continuous;
- floor;
- electronic;
- fragmented;
- centralized structures.

A durable lesson is that market structure changes participant incentives and therefore affects:

- liquidity;
- spread;
- transparency;
- execution;
- information leakage;
- price discovery.

Different traders prefer different market structures because their needs differ.

Examples:

- small traders may prefer transparent exposure;
- large traders may prefer controlled exposure;
- uninformed traders may benefit from being identifiable;
- informed traders often value anonymity;
- impatient traders value immediacy;
- patient traders can use order-driven liquidity provision.

## 17. Chapter-by-chapter coverage record

### Chapter 1 — Introduction

Core framework:

- market microstructure;
- bilateral search;
- liquidity;
- transaction cost;
- informative prices;
- volatility;
- trading profits;
- option value of standing orders;
- adverse selection;
- zero-sum competition.

### Chapter 2 — Trading Stories

Practical cases demonstrate:

- retail and institutional execution;
- large-order search;
- selective exposure;
- order splitting;
- market vs limit decisions;
- brokers/dealers;
- block trades;
- futures hedging;
- options;
- bonds;
- FX dealing.

Important recurring distinction:

execution urgency depends on why the trader believes the opportunity exists.

### Chapter 3 — The Trading Industry

Covers buy-side/sell-side roles, brokers, dealers, exchanges and regulation.

Liquidity is the principal service purchased by the buy side.

### Chapter 4 — Orders and Order Properties

Market/limit/stop orders, standing order option value, ex-post regret, execution uncertainty,
adverse selection and aggressiveness.

### Chapter 5 — Market Structures

Quote-driven, order-driven and brokered structures; call vs continuous; transparency; physical vs
distributed trading.

### Chapter 6 — Order-driven Markets

Order precedence, matching, trade-pricing rules and how market rules change trader incentives.

### Chapter 7 — Brokers

Search, negotiation, order-exposure management, agency problems, best execution, clearing,
settlement, custody and audit.

### Chapter 8 — Why People Trade

Separates utilitarian traders, informed speculators, order anticipators, bluffers, dealers and futile
traders.

### Chapter 9 — Good Markets

Good markets combine low transaction costs/liquidity with informative prices.

These objectives can conflict.

### Chapter 10 — Informed Traders and Market Efficiency

Value/news/technical/arbitrage information mechanisms, efficiency and comparative advantage.

### Chapter 11 — Order Anticipators

Front-running, sentiment anticipation, squeezes and exploitation of predictable order flow.

### Chapter 12 — Bluffers and Market Manipulation

Strategic misinformation and price manipulation.

### Chapter 13 — Dealers

Inventory, two-sided flow, price discovery, adverse selection and dealer economics.

### Chapter 14 — Bid/Ask Spreads

Spread determinants:

- information asymmetry;
- volatility;
- trading activity;
- competition;
- cost of standing liquidity.

### Chapter 15 — Block Traders

Large-order search, selective exposure, anonymity, information leakage and block facilitation.

### Chapter 16 — Value Traders

Depth/resilience provision, adverse selection and winner's curse.

### Chapter 17 — Arbitrageurs

Law of one price, basis/carry, connected markets and execution discipline.

### Chapter 18 — Buy-Side Traders

Order-submission strategy, liquidity price, market-vs-limit choice, order splitting and exposure.

### Chapter 19 — Liquidity

Liquidity dimensions, bilateral search and heterogeneous liquidity suppliers.

### Chapter 20 — Volatility

Fundamental vs transitory volatility and their different origins.

### Chapter 21 — Liquidity and Transaction Cost Measurement

Explicit/implicit/opportunity costs, effective/realized spreads, implementation shortfall, VWAP and
benchmark problems.

### Chapter 22 — Performance Evaluation and Prediction

Skill vs luck, sample selection, weak persistence of past returns and comparative advantage.

### Chapter 23 — Index and Portfolio Markets

Low-cost portfolio risk transfer and liquidity in index products.

### Chapter 24 — Specialists

Designated liquidity provision, privileges, obligations and interaction with public liquidity.

### Chapter 25 — Internalization, Preferencing, and Crossing

Trade-offs between dealer execution, centralized price discovery and incentives to display
liquidity.

### Chapter 26 — Competition Within and Among Markets

Order-flow externalities, fragmentation and heterogeneous trader preferences.

### Chapter 27 — Floor Versus Automated Trading Systems

Electronic trading advantages in speed/cost/auditability versus historical negotiation/information
advantages of floors.

Specific technology comparisons are dated; structural trade-offs remain relevant.

### Chapter 28 — Bubbles, Crashes, and Circuit Breakers

Extreme volatility, limits of value correction, momentum/reversal dynamics and market-stabilization
rules.

### Chapter 29 — Insider Trading

Information asymmetry, regulation, liquidity and price-informativeness trade-offs.

Primarily regulatory background for the current project.

## 18. What the book suggests for a future Trading Bot architecture

The following are **Research Director interpretations from this source**, not frozen system rules.

### 18.1 Prediction must be separate from execution

The system should not collapse:

`Will BTC move up/down?`

and

`Should I trade now, with this order, at this price?`

into one score.

A correct directional forecast can still produce a bad trade because of:

- spread;
- slippage;
- temporary impact;
- late entry;
- non-fill;
- adverse selection;
- poor liquidity.

### 18.2 Market state should include microstructure/execution state

Potential source-grounded dimensions for later architecture consideration:

- spread / liquidity width;
- visible depth;
- recent liquidity consumption;
- short-horizon flow imbalance;
- transitory displacement risk;
- volatility regime;
- execution urgency;
- expected fill quality.

No exact features or thresholds are authorized here.

### 18.3 Signal role matters

The Harris taxonomy supports distinguishing information roles rather than treating everything as one
directional vote.

Possible conceptual roles include:

- value/information;
- news;
- technical informational pattern;
- order anticipation;
- liquidity/market-making context;
- execution/risk.

This is compatible with a future professional multi-family architecture, but the book does not
specify Trading Bot's final family set.

### 18.4 NO_TRADE can be economically rational even with directional belief

If expected informational advantage is too small relative to:

- spread;
- execution uncertainty;
- adverse selection;
- opportunity geometry,

then declining the trade is rational.

This is much stronger than using NO_TRADE merely because indicators disagree.

### 18.5 Trade diagnostics should classify failure type

A future replay/autopsy could distinguish:

- directional prediction error;
- timing error;
- sizing/risk error;
- execution-cost error;
- non-fill/opportunity-cost error;
- temporary-liquidity displacement.

This classification is a project implication, not a taxonomy provided verbatim by Harris.

## 19. What this source does NOT support

This book does **not** establish:

- any profitable BTCUSDT strategy;
- any numerical signal weight;
- any cycle methodology;
- any optimal technical indicator;
- any optimal timeframe;
- any BTC trend/momentum edge;
- any crypto funding/OI edge;
- any direct order-flow threshold;
- any optimal stop/target;
- any probability-calibration method for BTC;
- any claim that market microstructure alone predicts medium-horizon direction.

It should not be used as authority for numeric alpha parameters.

## 20. Applicability to BTC / crypto

### Directly transferable at the conceptual level

Likely durable:

- market vs limit order trade-offs;
- spread as liquidity price;
- adverse selection;
- inventory/order-flow effects;
- price impact;
- liquidity dimensions;
- missed-trade opportunity cost;
- implementation shortfall logic;
- order exposure;
- separation of forecast and execution;
- skill vs luck;
- comparative advantage.

### Requires crypto-specific verification

Needs current crypto evidence/data before use:

- magnitude of spread and depth effects;
- order-book resiliency;
- queue/fill probabilities;
- taker-flow information content;
- spot/perpetual interaction;
- liquidation effects;
- exchange fragmentation;
- latency;
- funding;
- 24/7 market structure.

### Historical/datetime caveat

The book reflects market technology/regulation circa 2003.

Specific details about:

- floor exchanges;
- specialist systems;
- settlement cycles;
- then-current ECNs;
- old NYSE/Nasdaq rules

are historical and must not be copied into a 2026 crypto implementation.

## 21. Important source limitations

1. **No crypto/BTC evidence.**
2. **Published in 2003.**
3. Primarily conceptual/textbook synthesis rather than one unified empirical experiment.
4. Many examples concern U.S. equities, futures, options, bonds and FX under then-current market
   structures.
5. Fundamental value is central to several arguments; BTC fundamental value is not defined here.
6. The book explains why microstructure costs and behavior exist but does not give a modern
   exchange-specific execution simulator.
7. Some institutional examples and market-design details are obsolete.
8. The book is not evidence that every theoretically informed trader can earn excess returns.

## 22. Durable project knowledge retained from LIB-020

The following points are strong enough to retain for the later cross-source synthesis:

1. **Trading and forecasting are different problems.**
2. **Liquidity is multidimensional and has a price.**
3. **Market orders buy immediacy; limit orders sell liquidity while accepting fill/adverse-selection
   risk.**
4. **Non-fill has an opportunity cost and must be included in execution evaluation.**
5. **Spread and slippage are not incidental implementation details; they are economic variables.**
6. **Adverse selection is a core reason liquidity providers demand compensation.**
7. **Trade size and order exposure can themselves reveal information.**
8. **Order flow can arise from many motives and should not automatically be interpreted as
   directional information.**
9. **Fundamental and transitory volatility are conceptually different.**
10. **Temporary liquidity-driven price movement can reverse.**
11. **Implementation shortfall is more informative than simple commission accounting for total
    execution quality.**
12. **Performance must be separated from luck and selection bias.**
13. **A trader needs comparative advantage, not merely absolute competence.**
14. **Correlated/competitive market participants continually adapt, so an apparent pattern needs an
    economic reason to persist.**
15. **Large-order execution is partly an information-management problem.**
16. **Market structure changes incentives and therefore changes observed data.**
17. **NO_TRADE can be optimal because the cost/actionability problem is separate from directional
    prediction.**
18. **A professional trading system should preserve enough state to diagnose whether failure came
    from prediction, timing or execution.**

## 23. Questions to send to Astra at final corpus review

1. Should future Trading Bot architecture explicitly separate:
   - forecast state;
   - opportunity/actionability state;
   - execution/liquidity state?
2. Which Harris microstructure principles remain robust in a modern 24/7 BTC spot/perpetual market,
   and which require new crypto-specific evidence?
3. How should short-horizon order flow be interpreted without confusing informative flow, hedging,
   liquidation, inventory management and manipulation?
4. Should liquidity dimensions become model inputs, trade vetoes, sizing inputs, or execution-only
   variables?
5. How should missed-trade opportunity cost be modeled in historical replay without introducing
   counterfactual hindsight?
6. What level of fill/queue realism is scientifically necessary for the Owner's intended position
   sizes?
7. Can the concept of transitory volatility be operationalized causally for BTC without becoming a
   post-hoc mean-reversion label?
8. What explicit comparative advantage is the future algorithm hypothesized to possess relative to
   professional competitors?
9. Should Trading Bot evaluate forecast quality and execution quality with separate scorecards?
10. Which market-structure variables deserve to be included in the professional knowledge map before
    any System G2 is designed?

## 24. Final source disposition

`REVIEWED`

Reason:

- complete accessible PDF reviewed;
- all 29 chapters covered;
- full-document visual scan completed;
- operationally important figures/tables and chapters inspected in greater depth;
- source claims separated from Research Director interpretation;
- historical limitations recorded;
- no unsupported BTC alpha claim or numeric signal weight derived.

This source should be treated as a **foundational microstructure/execution reference** for the later
professional Trading Bot knowledge synthesis.

It is not itself a trading strategy and does not authorize any market experiment, System G2,
parameter calibration or real/paper order execution.
