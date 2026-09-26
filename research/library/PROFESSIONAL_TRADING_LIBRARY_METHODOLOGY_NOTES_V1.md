# Professional Trading Library — Methodology Notes V1

Date: 2026-09-26  
Status: progressive corpus study; not complete  
Authority: ADR-0051

This note deliberately separates:

1. what a source actually argues;
2. Research Director interpretation;
3. provisional project implication.

It is not a substitute for the source registry and does not upgrade any source to BTC-specific
evidence.

## M-001 — Deflated Sharpe Ratio (Bailey & López de Prado)

### Source says

The Deflated Sharpe Ratio addresses performance inflation caused by selection/multiple testing and
non-normal returns. The procedure uses information including the number/effective multiplicity of
trials, dispersion of Sharpe estimates, track-record length and higher moments.

The paper explicitly argues that multiple-testing exercises should be planned rather than expanded
merely because computation is cheap.

### Director interpretation

A seemingly impressive backtest metric becomes less persuasive when it was selected from a large
search. The *search process* is therefore part of the scientific evidence.

### Provisional Trading Bot implication

Maintain an append-only trial/search ledger. When a stage actually selects among many candidates,
use multiplicity-aware inference/diagnostics appropriate to that stage rather than treating the
chosen result as if it were the only test ever run.

Do not use DSR itself as a parameter-search objective.

## M-002 — Probability of Backtest Overfitting (Bailey et al.)

### Source says

The paper defines a probability-of-backtest-overfitting framework and presents CSCV as one
implementation for evaluating a strategy-selection procedure.

Its limitations are material:

- incomplete reporting of tested trials biases the assessment;
- correct PBO does not fix look-ahead, bad transaction costs or other incorrect backtest
  assumptions;
- regime changes outside the available sample remain unresolved;
- PBO/CSCV must not be turned into the objective used to search for an 'optimal' strategy.

### Director interpretation

Overfitting control is a layer on top of an already-causal, economically realistic simulation. It
cannot rescue a bad execution model or a leaky dataset.

### Provisional Trading Bot implication

If a future development stage performs enough candidate selection to justify PBO-style diagnostics,
preserve every legitimate candidate outcome and apply the diagnostic *after* the candidate-generation
rule is frozen. Never optimize the architecture to minimize PBO.

## M-003 — Harvey, Liu & Zhu: multiple testing / factor zoo

### Source says

In the cross-sectional asset-pricing literature, the accumulation of hundreds of tested factors
makes conventional single-hypothesis significance hurdles too permissive. Their paper proposes
multiple-testing corrections and argues that a newly proposed factor in that research context needed
substantially stronger evidence than the traditional t≈2 convention.

The authors also note that data mining need not be zero: research can create knowledge if bias is
handled statistically.

### Director interpretation

The important transferable lesson is not a magic t-statistic. It is that evidentiary thresholds
depend on the effective number of hypotheses searched and on prior/theoretical justification.

### Provisional Trading Bot implication

Do not install 't > 3' as a universal gate. Track search multiplicity and pre-existing theory, then
choose inference appropriate to our target/statistic/dependence structure.

## M-004 — López de Prado: financial CV and backtesting

### Source says

The book argues that ordinary K-fold cross-validation can leak in financial problems because
observations/labels are not IID and can overlap in time. It advocates purging overlapping labels and
embargoing adjacent observations in appropriate settings.

The book takes a deliberately strict position on final backtests: a backtest should not become the
feedback mechanism used to mutate the model until it wins. It recommends doing research/specification
before the final historical performance simulation and tracking every backtest.

### Director interpretation

Two distinct ideas must not be conflated:

1. **causal/time-aware validation** is an implementation requirement;
2. **whether development may iterate on exposed history** is a governance choice about evidence
   classes.

The second point is contested by other professional sources.

### Provisional Trading Bot implication

Purging/embargo/dependence awareness becomes mandatory whenever our future labels or train/test
construction require it.

The 'never refine from backtest' position is recorded but not yet adopted as the sole project rule.

## M-005 — Ernest Chan: causal backtests, costs and refinement

### Source says

Chan describes concrete backtest failure modes: look-ahead, data snooping, survivorship issues and
unrealistic transaction costs.

For look-ahead detection, he proposes a useful invariance concept: run the model on full history,
then truncate the future and rerun; positions before the truncation should not change.

Chan also permits strategy refinement, while warning that refinements should remain simple, have an
economic or well-studied market rationale and improve a separate test sample rather than merely the
training sample.

His transaction-cost discussion includes spread/liquidity, missed-fill opportunity costs, market
impact and execution delay/slippage in addition to commissions.

### Director interpretation

Chan describes an explicit **development process**, not only a one-shot confirmation test. This is
closer to the Owner's intended iterative complete-system engineering, provided development evidence
is never mislabeled as independent confirmation.

### Provisional Trading Bot implication

Add a deterministic truncated-history invariance test to the future causal replay test suite.

Separate a deliberately exposed development sandbox from protected evaluation before any future
iterative calibration is authorized.

## M-006 — Robert Carver: ideas-first calibration and robust combination

### Source says

Carver strongly warns against discovering apparently good rules by sifting huge rule spaces. His
preferred process begins with defensible ideas, then permits bounded calibration/variants.

His systematic framework standardizes rule forecasts and combines them using positive forecast
weights. He emphasizes diversification/correlation among rules and advocates robust handcrafted or
bootstrap-based weighting rather than fragile point optimization.

### Director interpretation

This is directly relevant to the Owner's emerging idea of stable base importance plus bounded
empirical adjustment:

- signals/rules that encode similar information should be grouped;
- their votes should not be counted as independent confirmations;
- weight stability can be more valuable than historical point-optimality.

Carver's literal futures portfolio framework is not automatically appropriate for BTCUSDT.

### Provisional Trading Bot implication

When the professional signal-family architecture is eventually designed, investigate a hierarchy:

- family role;
- base importance;
- current directional/strength state;
- quality/reliability;
- contextual relevance;
- small bounded empirical modifier;
- redundancy/correlation adjustment.

This remains architecture research, not a frozen formula.

## M-007 — Initial methodological contradiction: adaptation after results

### Source positions

**López de Prado:** final historical backtests should reject rather than iteratively improve a
strategy; using the backtest as feedback creates selection bias.

**Chan:** iterative refinement can be legitimate when simple, economically motivated and checked
against a distinct test sample.

**Carver:** ideas-first calibration is legitimate but broad rule/parameter mining is dangerous;
robust/stable choices are preferred to maximizing backtest performance.

### Current Research Director position

Do not resolve the disagreement by declaring one author universally correct.

The likely reconciliation is **stage-specific**:

- an explicitly exposed development sandbox can support learning/calibration;
- every iteration remains logged and contributes to the search burden;
- protected evaluation cannot be recycled as development after its result is inspected;
- future prospective paper evidence remains a higher evidence class.

This stage-specific policy is not yet a frozen governance change. It must be designed after broader
corpus study and independently reviewed before market work reopens.

## M-008 — Trend evidence: strong external literature, limited direct transfer

The library contains multiple mutually related trend/time-series-momentum sources, including
peer-reviewed work, institutional research and original factor datasets.

The corpus supports the statement that trend-following/time-series momentum has substantial
historical evidence across multiple traditional asset classes and horizons.

It does **not** yet support the stronger statement that a particular trend representation is
profitable on BTCUSDT at the product's decision horizon after costs.

Therefore trend remains professional prior knowledge / potential signal-family evidence, not a
validated Trading Bot edge.

## Next study blocks

Continue without market experimentation:

1. full systematic-design block: Carver + Chan;
2. microstructure/execution block: Harris + Johnson;
3. risk/expected-return block: Ilmanen + Hull where relevant;
4. trend evidence block: academic + AQR/Man sources and datasets;
5. professional trader-process block: Market Wizards;
6. financial-ML methods only where they materially affect validation or signal interpretation.

Only after these blocks should a canonical professional-signal knowledge map and base-importance
framework be drafted.
