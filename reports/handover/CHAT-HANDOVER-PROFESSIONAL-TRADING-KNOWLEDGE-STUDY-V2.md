# Trading Bot — New Main Chat Handover

Paste this entire file as the initialization prompt for the new main Trading Bot chat.

---

["incolla qui vecchio prompt handover"]

---

# CONTINUAZIONE HANDOVER — STATO SUCCESSIVO ALLA CHAT PRECEDENTE

The block above is the previous handover and should be treated as historical continuity.

This continuation records the decisions and work completed after that handover.

## Authority / conflict rule

Use this precedence when something conflicts:

1. current repository canonical files and `state/current_state.json`;
2. this continuation handover;
3. the older handover pasted above;
4. informal historical chat recollection.

Do not resurrect an older research programme merely because it appears in the old handover.

Repository:

`C-Gian/trading-bot`

The repository is the persistent source of truth.

## Current Owner role / interaction contract

The Owner delegates scientific direction, architecture, experiment interpretation and engineering
coordination.

The Owner should not be required to:

- write code;
- debug;
- inspect raw logs;
- study trading theory;
- manually interpret experiments;
- coordinate agents.

ChatGPT is Research Director / product lead / scientific brain.

Claude Code remains an implementation arm, not a scientific authority.

Astra is used as an independent strategic/scientific reviewer at major checkpoints.

Never authorize real capital automatically.

## Current product mission

Owner Product Mission V2 remains active:

- BTC-focused;
- professional multi-signal system;
- continuous prediction at eligible candles;
- prediction should represent direction, force/magnitude, risk and calibrated probability/confidence
  only where valid;
- separate action output: `LONG / SHORT / NO_TRADE`;
- multi-timeframe context including cycles;
- manual historical backtest / replay;
- causal candle-by-candle replay;
- live/local web app initially;
- chart + live board of algorithm inputs/state;
- prediction and trade/decision glyphs in replay;
- retain and score predictions separately from selective trade-policy outcomes;
- paper only;
- no real money.

## G1 / historical research state

System G1 remains closed / terminal parked.

Do not rescue or rerun G1.

No System G2 has been authorized yet.

Current market/alpha research allocation remains zero during the knowledge-base study.

Operational state remains:

- validated strategy: NONE;
- Champion: NONE;
- operational action: NO_TRADE;
- real money: false.

The corpus study does not authorize BTC backtests, parameter optimization, Phase B, strategy orders or
prospective collection.

Relevant governance:

- `decisions/ADR-0050-ADOPT-ASTRA-SYSTEM-G1-TERMINAL-PARK.md`
- `decisions/ADR-0051-OWNER-DIRECTED-PROFESSIONAL-TRADING-KNOWLEDGE-BASE-STUDY.md`

## Why the project entered a knowledge-base phase

The Owner clarified that the desired future algorithm should not be built by:

1. starting with one isolated indicator;
2. testing it as a standalone strategy;
3. adding one more signal;
4. repeating until something appears profitable.

Instead, the intended future development philosophy is:

- identify the **limited set of genuinely relevant professional information families**;
- understand what each family is for;
- understand how professional traders interpret conflicts and confirmations;
- build a complete interpretable trader from the beginning;
- then iterate on development history by studying recurring reasoning/decision errors;
- keep development evidence separate from protected evaluation evidence;
- eventually freeze the system and evaluate it out of development;
- prospective future paper evidence remains the strongest evidence.

This philosophy is not yet a frozen System G2 specification.

It is a design objective to be revisited only after corpus synthesis and Astra review.

## Important conceptual brainstorming retained for later synthesis

These ideas emerged before/during corpus study but are NOT yet frozen architecture.

### Stable professional importance + bounded empirical adjustment

The Owner proposed the idea of:

- a stable source-grounded base importance for each professional signal family;
- a much weaker empirical adjustment learned during development.

Conceptually:

`base importance × small bounded empirical modifier`

The empirical modifier must never have enough freedom to erase or completely rewrite the professional
importance hierarchy simply because of noisy historical P&L.

Carver later provided a useful professional precedent for stable/robust structural weighting and
cautious adjustment from uncertain historical performance.

No actual formula or bounds are frozen.

### Weight is not the algorithm

For a signal family the future system may need to distinguish:

- structural importance;
- current signed strength;
- quality/reliability;
- current contextual relevance;
- timeframe alignment;
- role in the decision.

Possible roles discussed:

- DIRECTION;
- CONFIRMATION;
- TIMING;
- CONTEXT;
- RISK;
- VETO.

This is conceptual vocabulary only, not a frozen schema.

### Candidate three-layer reasoning architecture

A useful conceptual model discussed was:

1. **Signal engines**
   - causal measurements/facts;
2. **Interpretation engine**
   - maps measurements to direction, strength, quality, relevance and interactions;
3. **Decision engine**
   - prediction, conviction, risk, LONG/SHORT/NO_TRADE, entry/stop/objective/actionability.

Again: not frozen until corpus synthesis.

### How future iteration should work

Future development should primarily diagnose recurring categories such as:

- wrong interpretation/context;
- wrong signal interaction/conflict handling;
- wrong timing/actionability;
- threshold errors;
- trade geometry errors;
- execution errors;
- only secondarily small empirical weight adjustment.

Do not modify a system after one losing trade.

Executed trades alone are not enough for diagnosis: the Owner wants continuous predictions, so future
analysis should also consider all eligible predictions, NO_TRADE decisions, near misses and false
negatives.

## Professional Trading Knowledge Base programme

The Owner performed a deep research collection and placed source material in the Google Drive folder:

`Trading`

Drive folder id:

`1CCH0iTYb0MEFESY1RSGW2ud39zzVZtjv`

Initial inventory:

- 20 accessible sources;
- 18 PDFs;
- 2 Excel datasets.

Canonical files:

- `research/library/PROFESSIONAL_TRADING_LIBRARY_SOURCE_REGISTRY_V1.json`
- `research/library/PROFESSIONAL_TRADING_LIBRARY_INVENTORY_V1.md`
- `research/library/PROFESSIONAL_TRADING_LIBRARY_METHODOLOGY_NOTES_V1.md`
- `research/library/PROFESSIONAL_TRADING_LIBRARY_LINEAR_STUDY_PROTOCOL_V2.md`
- `tasks/CURRENT_TASK.md`

## Final study protocol chosen by Owner

The Owner explicitly changed the reading workflow.

Do NOT group the primary reading by topic.

Do NOT decide which source to study next.

The Owner chooses one source at a time.

For each selected source:

1. study only that source;
2. read the complete accessible source;
3. preserve the source's own terminology and framing;
4. do not silently fill gaps using outside knowledge;
5. inspect figures/tables/appendices when materially relevant;
6. for spreadsheets inspect every sheet, metadata, provenance, schema and non-cell objects where
   relevant;
7. clearly distinguish:
   - SOURCE CLAIM;
   - EVIDENCE / METHOD;
   - LIMITATIONS;
   - RESEARCH DIRECTOR INTERPRETATION;
   - POTENTIAL PROJECT RELEVANCE;
   - OPEN QUESTIONS FOR ASTRA;
8. create one persistent source dossier in:
   `research/library/source_notes/`;
9. only after complete study mark that source `REVIEWED` in the canonical registry;
10. stop and wait for the Owner to choose the next source.

No cross-source final brainstorming while individual source study is incomplete.

No weights, System G2 or BTC experiments during this phase.

## Astra's agreed role

Astra should NOT automatically reread the entire raw corpus in parallel.

Workflow:

1. ChatGPT Research Director performs the primary complete source reading.
2. One substantial `.md` dossier is created for every source.
3. After the entire corpus is complete, ChatGPT creates the cross-source synthesis.
4. Astra receives:
   - source registry;
   - all source dossiers;
   - contradiction/uncertainty register;
   - final synthesis draft.
5. Astra independently challenges:
   - misinterpretation;
   - cherry-picking;
   - missing concepts;
   - duplicated/correlated evidence;
   - unsupported weights;
   - transferability to BTC;
   - overfitting/governance risk.
6. Astra may reopen the original source selectively wherever a claim is critical, disputed or
   insufficiently supported.
7. If Astra concludes a critical subset needs independent full-source rereading, do it before
   architecture freeze.

The dossiers are therefore intended as durable, source-grounded compressed memory for Astra.

## Current corpus completion state

As of 2026-09-27, the canonical source registry shows:

- **19 of 20 sources = REVIEWED**
- **1 source = PARTIALLY_REVIEWED**

The only incomplete source is:

### LIB-001

File:

`Algorithmic trading & DMA _ an introduction to direct access trading strategies.pdf`

Title:

*Algorithmic Trading & DMA: An Introduction to Direct Access Trading Strategies*

Author:

Barry Johnson

Year:

2010

Drive file id:

`1_1BdgOFL6PnODB58wgLTc-Bw3KzdfJHS`

Status:

`PARTIALLY_REVIEWED`

Reason:

- scanned/image PDF;
- Drive text extraction returns no useful text;
- rendered pages are readable;
- approximately 594 pages;
- requires visual/rendered-page study rather than normal text extraction.

The Owner intends to complete LIB-001 in a separate temporary chat.

Do not duplicate that work in the main chat unless explicitly asked.

When the main chat starts, read the current registry. If LIB-001 is still PARTIALLY_REVIEWED, wait for
the Owner/separate chat to complete it.

If LIB-001 is REVIEWED and its dossier exists, the corpus is ready for final synthesis.

## Existing canonical source dossiers

The registry is authoritative.

Reviewed dossier paths currently include:

- `LIB-002-EXPECTED-RETURNS.md`
- `LIB-003-QUANTITATIVE-TRADING-ERNEST-CHAN.md`
- `LIB-004-SYSTEMATIC-TRADING.md`
- `LIB-005-MARKET-WIZARDS-THE-NEXT-GENERATION.md`
- `LIB-006-MAN-AHL-TREND-FOLLOWING-EQUITY-AND-BOND-CRISIS-ALPHA.md`
- `LIB-007-TREND-FOLLOWING-AND-DRAWDOWNS-IS-THIS-TIME-DIFFERENT.md`
- `LIB-008-WHICH-TREND-IS-YOUR-FRIEND.md`
- `LIB-009-A-CENTURY-OF-EVIDENCE-ON-TREND-FOLLOWING-INVESTING.md`
- `LIB-010-TIME-SERIES-MOMENTUM-FACTORS-MONTHLY.md`
- `LIB-011-TIME-SERIES-MOMENTUM-ORIGINAL-PAPER-DATA.md`
- `LIB-012-ADVANCES-IN-FINANCIAL-MACHINE-LEARNING.md`
- `LIB-013-DEFLATED-SHARPE-RATIO.md`
- `LIB-014-VALUE-AND-MOMENTUM-EVERYWHERE.md`
- `LIB-015-TIME-SERIES-MOMENTUM.md`
- `LIB-016-CROSS-SECTION-OF-EXPECTED-RETURNS.md`
- `LIB-017-MATHEMATICAL-APPENDICES-PROBABILITY-OF-BACKTEST-OVERFITTING.md`
- `LIB-018-THE-PROBABILITY-OF-BACKTEST-OVERFITTING.md`
- `LIB-019-OPTIONS-FUTURES-AND-OTHER-DERIVATIVES-6E.md`
- `LIB-020-TRADING-AND-EXCHANGES-MARKET-MICROSTRUCTURE-FOR-PRACTITIONERS.md`

All live under:

`research/library/source_notes/`

There is also an unreferenced second LIB-020-named file in that directory. The canonical registry
points to the `...FOR-PRACTITIONERS.md` dossier above; use the registry as authority and do not
double-count the duplicate.

## Recent individually completed sources

### LIB-014 — Value and Momentum Everywhere

The local file is a two-page AQR secondary summary explicitly marked “not research,” not the full
academic paper.

No methodology missing from that local artifact was invented.

### LIB-020 — Trading and Exchanges

Larry Harris, 2003.

Complete accessible 657-page PDF / 29 chapters reviewed.

Key durable areas include:

- market microstructure;
- liquidity dimensions;
- orders;
- adverse selection;
- spreads;
- transaction costs;
- order exposure;
- execution;
- skill versus luck;
- comparative advantage;
- separation of directional forecast from execution quality.

The book does not establish BTC alpha.

### LIB-015 — Time Series Momentum

The local file is a two-page AQR secondary summary, explicitly not the full academic paper.

It reports own-past-return TSMOM evidence across 58 futures/forward contracts over more than 25 years,
but its 12-month/one-year horizons must not be transferred directly to BTC intraday.

### LIB-011 — Time Series Momentum Original Paper Data

Complete workbook reviewed:

- two worksheets;
- 300 monthly observations;
- Jan 1985 – Dec 2009;
- series:
  - TSMOM;
  - TSMOM^EQ;
  - TSMOM^FX;
  - TSMOM^FI;
  - TSMOM^CM;
- no missing month;
- no missing series values;
- disclosure text stored in a drawing/text box was also inspected.

The workbook is external evidence/provenance and must not be used as BTC training data.

## Important methodological conclusions retained so far

These remain candidates for final synthesis, not frozen architecture.

### Backtest/development disagreement in professional sources

There is a real source disagreement:

- López de Prado takes a very strict position on adapting after final backtest results;
- Ernest Chan explicitly permits economically motivated strategy refinement with separate test
  discipline;
- Robert Carver permits ideas-first calibration and variants while warning strongly against mining.

Do not flatten this into fake consensus.

Likely reconciliation to challenge with Astra later:

- exposed development sandbox may support learning/calibration;
- every iteration is logged;
- protected evaluation is not recycled into development after inspection;
- future prospective paper evidence is higher-class evidence.

### Correlated indicators should not be independent votes

Multiple transformations of the same underlying phenomenon should not be counted as multiple
independent confirmations.

Future synthesis should reason at signal-family / information-family level.

### External literature is not BTC validation

A source can justify:

- a concept;
- professional prior;
- hypothesis;
- role;

without proving BTCUSDT profitability.

Do not turn cross-asset evidence into a validated BTC edge.

## What to do after LIB-001 is completed

Do not immediately implement code.

The next research milestone should be:

`PROFESSIONAL_TRADING_CORPUS_FINAL_SYNTHESIS_V1`

The synthesis should use **all 20 dossiers**, not just memory.

It should produce at minimum:

1. complete professional information/signal-family map;
2. role of each family;
3. consensus versus disagreement across sources;
4. source provenance for every important architectural claim;
5. redundancy/correlation map between families;
6. what is directional versus confirmation/timing/context/risk/veto/execution;
7. what can reasonably transfer to BTC;
8. what requires BTC-specific evidence;
9. missing knowledge still not covered by the corpus;
10. candidate stable base-importance framework, if justified;
11. explicit list of things that should NOT enter the model;
12. research/development governance proposal;
13. testable hypotheses for the future complete system;
14. uncertainty register.

Then send the dossiers + synthesis to Astra for independent strategic/scientific review.

Only after resolving material Astra objections should any System G2 architecture be frozen and handed
to Claude Code.

## Main-chat startup instructions

At the beginning of the new main chat:

1. read `tasks/CURRENT_TASK.md`;
2. read `state/current_state.json` relevant current_project_status;
3. read `research/library/PROFESSIONAL_TRADING_LIBRARY_SOURCE_REGISTRY_V1.json`;
4. read `research/library/PROFESSIONAL_TRADING_LIBRARY_LINEAR_STUDY_PROTOCOL_V2.md`;
5. verify whether LIB-001 has become REVIEWED;
6. do not ask the Owner to recap information already present in repository/handover;
7. continue from repository state.

Keep Owner-facing responses concise.

Do not force an Owner decision for ordinary scientific/technical choices.

No real capital.
