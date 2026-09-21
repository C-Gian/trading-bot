# Trading Bot — Scientific Constitution

Version 2.0 — prediction-first

Owner-authorized on 2026-09-16. Supersedes Version 1.0, which is preserved verbatim in
Appendix A. See [ADR-0026](../decisions/ADR-0026-PREDICTION-FIRST-RESEARCH-OBJECTIVE.md).

## Mission

Develop a statistically credible BTCUSDT predictor that estimates future price direction,
calibrated probability, and expected movement magnitude over explicitly declared horizons,
while minimizing the probability of mistaking overfitting, leakage, look-ahead,
repeated testing or random luck for genuine predictive skill.

Prediction quality is judged on its own terms. The prediction layer is evaluated
independently of capital size, exchange fees, leverage, slippage, blockchain or network
costs, position sizing, and every other execution or economic choice.

Economic execution is a downstream layer. It may later translate a prediction into a
paper or live decision using costs and capital assumptions, but it never defines whether
the underlying market prediction was correct.

Trading Bot is research-first. It is not a promise of profit, and a credible predictor is
not by itself a profitable product.

## Evidence hierarchy

From strongest to weakest:

1. immutable future prospective / forward predictive evidence;
2. sealed locked evaluation;
3. properly purged chronological walk-forward / out-of-sample validation;
4. robustness and stress tests;
5. development backtests and development-period predictive fits;
6. narrative explanations.

Lower-quality evidence cannot override stronger evidence.

## Non-negotiable rules

- AI may propose hypotheses, code and interpretations. Deterministic tooling evaluates them.
- Every material experiment is preregistered before execution.
- Hypothesis, primary metric, evaluation design, parameter/search space and trial budget
  are declared before results are observed.
- Failed and negative experiments are preserved.
- Results are never rewritten after observation.
- A material predictor or strategy change creates a new model/experiment version.
- Signals and features use only information available at signal time.
- Ambiguous fills are handled conservatively, never optimistically.
- Sealed holdout data is inaccessible to research agents.
- Repeated sealed queries consume explicit evaluation budget.
- Exposed holdouts are retired from sealed status.
- Standard random K-fold is forbidden for overlapping financial time-series labels.
- Prefer simple deterministic baselines before complex models.
- Machine learning is a challenger family, not a prerequisite.
- Trial count and adaptive search must be recorded for multiple-testing analysis.
- No AI agent may access or deploy real-money credentials.
- Paper success is not permission for live capital.
- Any real-capital transition requires a separate explicit Owner gate.

## Predictive evaluation rules

These rules replace the Version 1.0 rule that hit rate is secondary to robust net
expectancy. They govern every experiment whose claim is predictive.

- Directional win rate is a primary human-facing predictive metric.
- It must never be interpreted alone.
- Every reported win rate is paired with sample size and prediction coverage.
- Probabilistic predictions are evaluated for calibration.
- Magnitude forecasts are evaluated separately from direction.
- All metrics are compared against predeclared simple chronological baselines and reported
  with uncertainty intervals.
- No high win rate obtained by trivial abstention, class imbalance, or selective reporting
  may be treated as predictive success.
- A win rate above 50% is not by itself scientifically interesting. A predictor must beat
  its predeclared baselines out of sample with nontrivial coverage.
- No win-rate target is declared before evidence establishes what is feasible.
- Uncalibrated model scores are never presented as probabilities.
- Probability and magnitude strength are distinct quantities and are never conflated.

The frozen metric set, baselines and magnitude diagnostics live in
`docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md`, which may be extended but not
weakened, and never after a result it would govern has been observed.

## Prediction and economics are separate layers

The governed order is:

`PREDICTION LAYER -> DECISION/POLICY LAYER -> ECONOMIC/EXECUTION SIMULATION`

- Prediction quality must not depend on capital size, fee schedule, leverage, slippage,
  blockchain/network costs, or position sizing.
- Those variables belong to downstream scenario analysis and paper/live execution only.
- Any reference capital amount is a configurable display or scenario assumption. It is
  never a training target and never a prediction-quality parameter.
- Transaction costs and execution assumptions remain mandatory and versioned for every
  experiment that claims economic or trading profitability. They are not part of the
  primary scoring of a pure prediction experiment.
- An economic claim may never be supported by prediction-layer evidence alone.

## Information sources

The predictor may study causally timestamped information families, but never all at once.
Each family enters through a preregistered incremental-information experiment with
point-in-time availability rules and search-budget accounting, as staged in
`docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`.

Narrative plausibility alone is never evidence. Political, policy and geopolitical events
are admissible only as timestamped public information, without partisan interpretation.

## Anti-overfitting principle

The laboratory's advantage must not be “try more models until one looks good.”

The advantage must be “run many experiments without allowing the number of attempts to
fool us.”

## Governance

This Constitution is Owner-controlled and cannot be automatically weakened or replaced by
an AI agent. Only the Owner may change the mission or the evaluation principles.

Lower-level research workflow may evolve, but never in conflict with this document.

Historical research generations, their experiments and their negative results are never
deleted or rewritten when the mission changes. A superseded generation is recorded with an
explicit disposition and preserved.

## Selection/evaluation separation

No feature set, feature weight, timeframe, signal threshold, label horizon,
stop/target geometry, risk parameter, model hyperparameter, or ensemble weight may be
selected using the final or outer evaluation metric.

Any authorized tuning must occur entirely within the chronological training portion of
the governed process. Outer evaluation remains unseen until candidate freeze. Any
post-result material optimization creates a new preregistered experiment and consumes
new search budget.

## Future power gate

Before executing any future `MATERIAL_ECONOMIC_HYPOTHESIS`, its preregistration must
freeze:

- experiment metric and MESI expressed in that metric;
- expected sample design and expected dependence structure;
- statistical dependence method;
- expected MDE or an explicit fail-closed reason it is unavailable;
- alpha and multiplicity-family membership;
- target power, defaulting to 0.80.

A design without adequate expected ability to distinguish its preregistered MESI must
not automatically be executed. It must be classified `REDESIGN_REQUIRED` or explicitly
accepted before execution as exploratory, non-resolution evidence. MESI and target power
may not be lowered after results are observed.

MDE and MESI are distinct: MDE describes design detectability under assumptions; MESI is
the minimum economically important effect. Neither changes a historical terminal
classification retrospectively.

The same gate applies to a `MATERIAL_PREDICTIVE_HYPOTHESIS`, with the minimum important
effect expressed in the predictive primary metric rather than in an economic one.

## Research generations

Version 2.0 governs every prediction-first research generation. A generation is a frozen
evaluation question, not a new mission and not a new set of rigour rules. Opening one never
weakens this Constitution, and closing one never deletes or reinterprets what it recorded.

`PREDICTIVE_RESEARCH_GENERATION_V1` tested universal hourly directional classification on the
frozen BTCUSDT 24h terminal target under
`docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md` (Amendment A1). It is closed with
disposition `CLOSED_NO_DIRECTIONAL_ADMISSION_NO_SEALED`: five executed information families,
ten consumed configurations, none advanced, none sealed-eligible. That closure establishes
that the tested always-declare formulations added no credible directional information over
their frozen controls. It does not establish that the market is unpredictable, and it is not
evidence for or against any question a later generation asks.

`PREDICTIVE_RESEARCH_GENERATION_V2` tests selective directional prediction — `LONG` when a
calibrated probability clears a frozen threshold, `NO_TRADE` otherwise — under
`docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V2.md` (Amendment B1). See
[ADR-0028](../decisions/ADR-0028-GENERATION-V2-SELECTIVE-LONG-REBASELINE.md).

Rules that bind every generation:

- a new evaluation question is preregistered before any candidate of that generation exists,
  and is never applied retrospectively to an earlier generation's model score;
- an earlier generation's rejected result never becomes evidence merely because the scorer
  changed;
- search memory, family dispositions, source blocks and search-burden accounting carry
  forward across generations; new hypotheses receive new IDs and new budgets;
- a generation's advancement thresholds may not be weakened after one of its candidates has
  been observed;
- a selective predictor is additionally governed by predeclared coverage and sample-size
  floors, so a high win rate obtained by acting rarely is not predictive success;
- a selective predictor is compared against the ambient outcome rate of the same evaluation
  period, so acting inside a favourable regime is not mistaken for skill.

---

## Appendix A — superseded Version 1.0, preserved verbatim

Version 1.0 governed the cost-adjusted strategy-selection research generation
`COST_EXPECTANCY_RESEARCH_GENERATION_V1`. It is reproduced below exactly as it stood when
the Owner authorized the prediction-first objective, including every section appended to
it during that generation. Nothing in it is edited, and the historical results it governed
are not reinterpreted.

Where Version 2.0 above conflicts with the text below, Version 2.0 governs. The single
material conflict is the mission and the treatment of hit rate; every rigour rule below
remains in force.

# Trading Bot — Scientific Constitution

Version 1.0

## Mission

Search for statistically credible and economically positive trading strategies while minimizing the probability of mistaking overfitting, leakage, execution artifacts, repeated testing or random luck for genuine edge.

Trading Bot is research-first. It is not a promise of profit.

## Evidence hierarchy

From strongest to weakest:

1. immutable future paper / forward evidence;
2. sealed locked evaluation;
3. properly purged chronological walk-forward / out-of-sample validation;
4. robustness and transaction-cost stress tests;
5. development backtests;
6. narrative explanations.

Lower-quality evidence cannot override stronger evidence.

## Non-negotiable rules

- AI may propose hypotheses, code and interpretations. Deterministic tooling evaluates them.
- Every material experiment is preregistered before execution.
- Hypothesis, primary metric and search budget are declared before results are observed.
- Failed and negative experiments are preserved.
- Results are never rewritten after observation.
- A material strategy change creates a new strategy/experiment version.
- Signals and features use only information available at signal time.
- Transaction costs and execution assumptions are mandatory and versioned.
- Ambiguous fills are handled conservatively, never optimistically.
- Sealed holdout data is inaccessible to research agents.
- Repeated sealed queries consume explicit evaluation budget.
- Exposed holdouts are retired from sealed status.
- Standard random K-fold is forbidden for overlapping financial time-series labels.
- Prefer simple deterministic baselines before complex models.
- Machine learning is a challenger family, not a prerequisite.
- Trial count and adaptive search must be recorded for multiple-testing analysis.
- Hit rate is secondary to robust net expectancy and evidence quality.
- No AI agent may access or deploy real-money credentials.
- Paper success is not permission for live capital.
- Any real-capital transition requires a separate explicit Owner gate.

## Anti-overfitting principle

The laboratory's advantage must not be “try more strategies until one looks good.”

The advantage must be “run many experiments without allowing the number of attempts to fool us.”

## Governance

This Constitution is Owner-controlled and cannot be automatically weakened or replaced by an AI agent.

Lower-level research workflow may evolve, but never in conflict with this document.

## Selection/evaluation separation

No feature set, feature weight, timeframe, signal threshold, label horizon,
stop/target geometry, risk parameter, model hyperparameter, or ensemble weight may be
selected using the final or outer evaluation metric.

Any authorized tuning must occur entirely within the chronological training portion of
the governed process. Outer evaluation remains unseen until candidate freeze. Any
post-result material optimization creates a new preregistered experiment and consumes
new search budget.

## Future power gate

Before executing any future `MATERIAL_ECONOMIC_HYPOTHESIS`, its preregistration must
freeze:

- experiment metric and MESI expressed in that metric;
- expected sample design and expected dependence structure;
- statistical dependence method;
- expected MDE or an explicit fail-closed reason it is unavailable;
- alpha and multiplicity-family membership;
- target power, defaulting to 0.80.

A design without adequate expected ability to distinguish its preregistered MESI must
not automatically be executed. It must be classified `REDESIGN_REQUIRED` or explicitly
accepted before execution as exploratory, non-resolution evidence. MESI and target power
may not be lowered after results are observed.

MDE and MESI are distinct: MDE describes design detectability under assumptions; MESI is
the minimum economically important effect. Neither changes a historical terminal
classification retrospectively.
