# Professional Trading Library — Inventory V1

Date: 2026-09-26  
Authority: ADR-0051  
Drive folder: `Trading`  
Initial visible file count: **20**

This is the Phase-1 inventory and first-pass classification. It is **not** a claim that all 20
sources have been fully studied.

Machine-readable registry:

`research/library/PROFESSIONAL_TRADING_LIBRARY_SOURCE_REGISTRY_V1.json`

## 1. Library inventory

Initial scan found:

- 18 PDFs;
- 2 Excel datasets;
- 20 accessible files total.

The corpus includes:

- 8 professional books/textbooks/interview books;
- 6 academic/research-method papers or supplements;
- 4 institutional practitioner/secondary research artifacts;
- 2 documented numeric datasets.

No exact duplicate file has been identified in the initial scan.

One source, Barry Johnson's *Algorithmic Trading & DMA*, is an image/scanned PDF. Drive's text
extractor returns no useful text, but rendered pages are readable; it is therefore not classified
UNREADABLE.

## 2. Source registry

| ID | Source | Author(s) | Year | Class | Tier | Status |
|---|---|---|---:|---|---|---|
| LIB-001 | Algorithmic Trading & DMA | Barry Johnson | 2010 | Book/Textbook | C | PARTIALLY_REVIEWED |
| LIB-002 | Expected Returns | Antti Ilmanen | 2011 | Book/Textbook | C | IDENTIFIED |
| LIB-003 | Quantitative Trading | Ernest P. Chan | 2009 | Book/Textbook | C | PARTIALLY_REVIEWED |
| LIB-004 | Systematic Trading | Robert Carver | 2015 | Book/Textbook | C | PARTIALLY_REVIEWED |
| LIB-005 | Market Wizards: The Next Generation | Jack D. Schwager; George F. Coyle | 2025/2026* | Book/Interviews | C | IDENTIFIED |
| LIB-006 | Trend Following: Equity and Bond Crisis Alpha | Hamill; Rattray; van Hemert | 2016 | Institutional Practitioner | B | PARTIALLY_REVIEWED |
| LIB-007 | Trend Following and Drawdowns: Is This Time Different? | Russell Korgaonkar | 2025 | Institutional Practitioner | B | PARTIALLY_REVIEWED |
| LIB-008 | Which Trend Is Your Friend? | Levine; Pedersen | 2016 | Peer-reviewed paper | A | PARTIALLY_REVIEWED |
| LIB-009 | A Century of Evidence on Trend-Following Investing | Hurst; Ooi; Pedersen | 2017 | Peer-reviewed paper | A | PARTIALLY_REVIEWED |
| LIB-010 | AQR Time Series Momentum Factors, Monthly | AQR | — | Dataset | A | DATASET_INSPECTED |
| LIB-011 | AQR Time Series Momentum Original Paper Data | Moskowitz; Ooi; Pedersen | 2012 | Dataset | A | DATASET_INSPECTED |
| LIB-012 | Advances in Financial Machine Learning | Marcos López de Prado | 2018 | Book/Textbook | C | PARTIALLY_REVIEWED |
| LIB-013 | The Deflated Sharpe Ratio | Bailey; López de Prado | 2014 | Research Methodology | A | PARTIALLY_REVIEWED |
| LIB-014 | Value and Momentum Everywhere — AQR summary | AQR | 2013 | Institutional summary | B | PARTIALLY_REVIEWED |
| LIB-015 | Time Series Momentum — AQR summary | AQR | 2012 | Institutional summary | B | PARTIALLY_REVIEWED |
| LIB-016 | … and the Cross-Section of Expected Returns | Harvey; Liu; Zhu | 2015 | Research Methodology | A | PARTIALLY_REVIEWED |
| LIB-017 | Mathematical Appendices to PBO | Bailey; Borwein; López de Prado; Zhu | 2015 | Research Methodology supplement | A | PARTIALLY_REVIEWED |
| LIB-018 | The Probability of Backtest Overfitting | Bailey; Borwein; López de Prado; Zhu | 2015 | Research Methodology | A | PARTIALLY_REVIEWED |
| LIB-019 | Options, Futures, and Other Derivatives, 6e | John C. Hull | 2006 | Book/Textbook | C | IDENTIFIED |
| LIB-020 | Trading and Exchanges | Larry Harris | 2003 | Book/Textbook | C | PARTIALLY_REVIEWED |

*The Market Wizards file says “First published in 2025” while copyright and a preface refer to
2026. Preserve both until bibliographic reconciliation is needed.

## 3. Classification

### Book / textbook / professional book

LIB-001, LIB-002, LIB-003, LIB-004, LIB-005, LIB-012, LIB-019, LIB-020.

### Peer-reviewed / academic or primary research-method paper

LIB-008, LIB-009, LIB-013, LIB-016, LIB-018.

LIB-017 is a technical supplement to LIB-018, not independent empirical evidence.

### Institutional practitioner / secondary research artifact

LIB-006, LIB-007, LIB-014, LIB-015.

Important distinction: the local LIB-014 and LIB-015 PDFs are AQR secondary summaries, not the
full underlying academic papers.

### Dataset

LIB-010 and LIB-011.

## 4. Evidence map

### Tier A

LIB-008, LIB-009, LIB-010, LIB-011, LIB-013, LIB-016, LIB-017, LIB-018.

### Tier B

LIB-006, LIB-007, LIB-014, LIB-015.

### Tier C

LIB-001, LIB-002, LIB-003, LIB-004, LIB-005, LIB-012, LIB-019, LIB-020.

No Tier-D source is currently present in the Drive inventory.

Tier is a source-classification aid, not a rule that a Tier-A finding from another market proves an
edge on BTCUSDT.

## 5. Topic map

| Topic | Main sources presently identified |
|---|---|
| Research hygiene / overfitting | LIB-003, 004, 012, 013, 016, 017, 018 |
| Backtesting / CV / leakage | LIB-003, 012, 018 |
| Trend / time-series momentum | LIB-006, 007, 008, 009, 010, 011, 015 |
| Signal combination / weighting | LIB-004; later synthesis pending other sources |
| Expected returns / factor logic | LIB-002, 014, 015, 016 |
| Market microstructure | LIB-001, 012, 020 |
| Execution / transaction costs | LIB-001, 003, 004, 020 |
| Risk / position sizing | LIB-002, 003, 004, 012, 019 |
| Portfolio construction | LIB-002, 004, 019 |
| Financial ML | LIB-012 |
| Trader process / psychology | LIB-005, 003 |
| Derivatives mechanics | LIB-019 |
| Cycle methodology | **weak coverage in current corpus** |
| BTC/crypto-specific microstructure / derivatives | **weak coverage in current corpus** |
| Heterogeneous professional multi-signal fusion | **not yet directly covered by a dedicated source** |

## 6. BTCUSDT relevance map

### Directly relevant

Research methodology, causal data timing, transaction-cost/execution discipline, microstructure
concepts and systematic forecast-combination architecture:

LIB-001, LIB-003, LIB-004, LIB-020, plus methodology rules from LIB-012/013/016/018.

### Hypothesis candidate

External-market evidence that may motivate bounded BTC hypotheses but cannot validate them:

LIB-005, LIB-006, LIB-007, LIB-008, LIB-009, LIB-015.

### Methodology only

LIB-002, LIB-010, LIB-011, LIB-012, LIB-013, LIB-014, LIB-016, LIB-017, LIB-018, LIB-019
unless a future protocol explicitly admits a narrower concept.

### Out of scope

Large parts of options pricing, multi-asset portfolio construction and cross-sectional factor
investing are outside the current BTC-focused product even though their methods can remain useful.

## 7. Duplicates / problems

No exact duplicate is confirmed.

Related-but-distinct clusters:

- LIB-010/LIB-011/LIB-015: AQR TSMOM updated factors, original-paper data and institutional summary;
- LIB-017/LIB-018: PBO mathematical appendix and main paper;
- LIB-006/007/008/009/015: trend-following evidence family.

Problems / qualifications:

- LIB-001 is a scanned 211 MB PDF; visual rendering is required.
- LIB-005 has a 2025/2026 bibliographic inconsistency.
- LIB-014 and LIB-015 are institutional summaries, not the complete academic articles.
- rights for copyrighted personal-library books are not assumed to permit redistribution or model
  training.
- no corruption has been observed in the initial scan.

## 8. Initial research rules

These rules are provisional until broader corpus review, but already have multi-source support:

1. **Log the research search path.** Configurations/trials cannot disappear from the record merely
   because they failed.
2. **Constrain search with theory/professional rationale before computation.** Compute power is not
   itself a reason to create more variants.
3. **Separate development from independent evaluation.** Repeated learning on development history
   consumes its evidentiary independence.
4. **Enforce causal data timing.** Add deterministic truncated-history invariance tests where
   practical: future truncation must not change prior decisions.
5. **Use time/dependence-aware validation.** If labels or outcomes overlap, ordinary random K-fold is
   unsafe; purge/embargo or another justified temporal design is required.
6. **Model executable costs.** Commission/fees alone are insufficient: spread/liquidity,
   delay/slippage, funding and material market impact/opportunity costs must be considered where
   relevant.
7. **Do not optimize anti-overfitting diagnostics.** DSR/PBO are diagnostics/governance tools, not
   objectives to tune against.
8. **Account for search multiplicity.** Statistical confidence must reflect how many effective
   hypotheses/configurations were tried; no universal t-statistic is copied from another research
   context.
9. **Treat regime/structural-break risk explicitly.** A clean historical validation cannot prove the
   future belongs to the same regime.
10. **External-market findings are external evidence.** They can motivate BTC tests but do not prove
    BTC profitability.
11. **Dataset provenance is part of the experiment.** Track exact data version, definitions,
    reconstruction/update policy and associated paper.
12. **Correlated signals are not independent votes.** Later signal architecture must model
    redundancy/grouping rather than count several transforms of the same underlying information as
    separate confirmations.

## 9. Contradictions / uncertainties

### C-001 — Is a backtest a development tool?

This is a real disagreement in the corpus.

- López de Prado argues that the final backtest should be used primarily to reject fully specified
  models; adapting the model to that result creates selection/overfit risk.
- Chan explicitly allows strategy refinement, provided changes remain simple, economically
  motivated and are checked on a separate test set rather than only the training set.
- Carver permits ideas-first calibration and rule variations, but strongly warns against mining
  large spaces of rules and parameter values.

Do not flatten this into a fake consensus. The eventual Trading Bot development policy must state
which *stage* is allowed to adapt and which evaluation evidence becomes immutable.

### C-002 — Trend evidence vs. target product

Trend/time-series momentum has substantial cross-asset evidence in the library. The available
material mostly concerns multi-asset futures/forwards and medium/long horizons, not BTCUSDT
intraday/short-horizon trading. Transferability remains unproven.

### C-003 — Source popularity vs. evidence

Professional interviews and practitioner books can be valuable for process design without receiving
the evidentiary status of peer-reviewed empirical work.

## 10. Missing knowledge

The initial corpus is strong on research hygiene, trend evidence, systematic design and
microstructure/execution.

Material gaps relative to Owner Product Mission V2 remain:

1. professional **cycle/time-structure** methodology at the scales the product wants to display;
2. BTC/crypto-specific exchange microstructure, perpetual/spot relation, OI/funding and execution;
3. a well-specified professional framework for combining heterogeneous evidence families
   (direction, confirmation, timing, context, risk, veto) without treating correlated indicators as
   independent votes;
4. empirical/professional guidance on the distinction between directional forecast, entry
   actionability and trade geometry at intraday horizons.

These are recorded as knowledge gaps, not automatic permission to acquire more sources or start a
new market experiment.

## Current study state

The inventory is complete for the 20 files visible in the initial Drive scan.

The library study is **not complete**.

No source is marked REVIEWED yet. Two datasets are DATASET_INSPECTED; several sources are
PARTIALLY_REVIEWED and the remainder IDENTIFIED.

No strategy, signal weight, G2 specification or market experiment has been authorized from this
inventory.
