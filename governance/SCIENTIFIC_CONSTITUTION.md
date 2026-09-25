# Trading Bot — Scientific Constitution

> **OWNER SCOPE UPDATE — 2026-09-25:** Product-scope portions of Constitution 3.0 that
> restrict the active mission to BTC spot `LONG / NO_TRADE` are superseded by
> `docs/canonical/OWNER_PRODUCT_MISSION_V2.md` and ADR-0043, pending Astra's strategic redesign
> and a formal Constitution-version migration. All scientific-integrity, anti-leakage,
> anti-overfitting, evidence and real-capital rules remain binding. No new market experiment is
> authorized by this scope update.

Version 3.0 — practical economic usefulness

Owner-authorized on 2026-09-25, translating the Owner's clarified product objective and
`ASTRA_TRADING_BOT_STRATEGIC_OPERATING_DIRECTIVE_V2` into repository truth. Supersedes
Version 2.0, which is preserved verbatim in Appendix B; Version 2.0 itself preserved
Version 1.0, which remains verbatim in Appendix A. See
[ADR-0036](../decisions/ADR-0036-OWNER-PRACTICAL-ECONOMIC-OBJECTIVE-AND-CONSTITUTION-V3.md).

## Mission

Trading Bot is intended to become a practical, reproducible BTC spot `LONG` / `NO_TRADE`
paper system whose final product advancement objective is practical, risk-constrained economic
usefulness, demonstrated by frozen prospective economic confirmation — while minimizing the
probability of mistaking overfitting, leakage, look-ahead, execution artifacts, repeated
testing or random luck for a genuine edge.

Professional trading mechanisms generate bounded hypotheses. Statistics evaluates them and
prevents self-deception. The project does not continue inventing increasingly elaborate alpha
questions merely because previous ideas failed.

Where a playbook uses a prediction, prediction quality remains a distinct scientific quantity
and is evaluated on its own terms. A good prediction is not by itself an economically useful
system, and an economic claim is never supported by prediction-layer evidence alone.

`NO_TRADE` is a valid operational output and a valid permanent project outcome.

Trading Bot is research-first. It is not a promise of profit. Real money is a separate
explicit Owner gate.

## Evidence hierarchy

From strongest to weakest:

1. immutable frozen prospective paper / forward evidence;
2. sealed locked evaluation;
3. properly purged chronological walk-forward / out-of-sample validation;
4. robustness, cost and stress tests;
5. development backtests and development-period fits;
6. narrative explanations.

Lower-quality evidence cannot override stronger evidence.

Historical development is exposed exploratory evidence, even when it is chronological or
walk-forward. It does not become fresh confirmation through repeated rescoring, new names,
new scorers or new models. Prospective evidence outranks exposed historical development.

## Research sequence

The governed sequence is:

`PLAUSIBLE MECHANISM -> EXPLICIT PLAYBOOK -> BOUNDED HISTORICAL DEVELOPMENT -> PROMOTION GATE -> FROZEN PROSPECTIVE ECONOMIC CONFIRMATION`

- Historical development may formalize a mechanism, inspect support, estimate gross/net scale,
  diagnose failure modes and spend a small preregistered robustness budget.
- Prospective evidence is scarce. It is earned only by a candidate with materially useful
  development economics, credible execution margin, adequate support and acceptable
  concentration, and feasible detectability.
- The default confirmation calendar ceiling is 12 months. An effect that cannot plausibly
  resolve its economic MESI inside that budget is not tested prospectively.
- A p-value alone is never promotion.
- Frontier R&D is exceptional. Ordinary strategy failure is never an R&D trigger.

The Development Lab, Promotion Gate, Confirmation and Frontier R&D stages, and the escalation
policy, are defined in `docs/canonical/RESEARCH_STAGE_POLICY_V1.md`. That policy may be
tightened but not weakened, and never after a result it would govern has been observed.

## Non-negotiable rules

- AI may propose hypotheses, code and interpretations. Deterministic tooling evaluates them.
- Every material experiment is preregistered before execution.
- Hypothesis, primary metric, evaluation design, parameter/search space and trial budget
  are declared before results are observed.
- Failed and negative experiments are preserved.
- Results are never rewritten after observation.
- A material playbook, predictor or strategy change creates a new experiment version.
- Signals and features use only information available at signal time.
- Transaction costs, delay and execution assumptions are mandatory and versioned for every
  economic or trading claim.
- Ambiguous fills are handled conservatively, never optimistically.
- Sealed holdout data is inaccessible to research agents.
- Repeated sealed queries consume explicit evaluation budget.
- Exposed holdouts are retired from sealed status.
- Standard random K-fold is forbidden for overlapping financial time-series labels.
- Prefer simple deterministic baselines and meaningful controls before complex models.
- Machine learning is a challenger family, not a prerequisite.
- Trial count and adaptive search must be recorded for multiple-testing analysis.
- Search memory and every negative, blocked or parked result remain binding. A renamed family
  is not new evidence.
- Outcome-driven parameter rescue is forbidden unless the dimension, range or branch rule was
  explicitly budgeted before inspection. Every inspected version remains in the exposed lineage.
- No AI agent may access or deploy real-money credentials.
- Paper success is not permission for live capital.
- Any real-capital transition requires a separate explicit Owner gate.

## Economic and predictive quantities

Economic usefulness is judged on predeclared net estimands: versioned costs, delay, occupancy,
eligibility and exits are part of the frozen playbook, and every economic effect is compared
with a meaningful predeclared control, not only with zero.

Where a playbook declares a prediction, these predictive evaluation rules apply to that
component:

- Directional win rate is a primary human-facing predictive metric.
- It must never be interpreted alone.
- Every reported win rate is paired with sample size and prediction coverage.
- Probabilistic predictions are evaluated for calibration.
- Magnitude forecasts are evaluated separately from direction.
- Metrics are compared against predeclared chronological baselines with dependence-aware
  uncertainty intervals.
- No high win rate obtained by trivial abstention, class imbalance or selective reporting is
  predictive success.
- Uncalibrated model scores are never presented as probabilities, and magnitude strength is
  never presented as a probability.
- A selective contrast is composition-controlled — matched within fold or otherwise defined
  before outcomes — so acting inside a favourable regime is not mistaken for skill.

`docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md` and
`docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V2.md` continue to govern predictive claims;
they may be extended but not weakened.

## Information sources

Information families are not searched as a universal source ladder. A family enters only as
an input to an admitted mechanism or playbook, with point-in-time availability rules,
declared timing and missingness semantics, and search-budget accounting. The current
allocation dispositions live in `docs/canonical/STRATEGIC_ALLOCATION_MAP_V1.md`; they are
allocation decisions, not impossibility claims.

`docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md` remains the historical source ladder of the
prediction-first generations and does not authorize new work by itself.

Narrative plausibility alone is never evidence. Political, policy and geopolitical events are
admissible only as timestamped public information, without partisan interpretation.

## Anti-overfitting principle

The laboratory's advantage must not be “try more strategies or models until one looks good.”

The advantage must be “run a small number of bounded, mechanism-led experiments without
allowing the number of attempts to fool us.”

## Governance

This Constitution is Owner-controlled and cannot be automatically weakened or replaced by an
AI agent. Only the Owner may change the mission or the evaluation principles.

Within it, Astra is the strategic scientific authority for material research-allocation
decisions; the Research Director owns routine scientific design, architecture, tasking,
implementation review, experiment adjudication and ordinary decisions inside Astra's
directive; Claude Code is the sole coding and repository implementation executor. No agent can
authorize real capital. Scientific truth lives in repository artifacts, not in conversations.

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

Prospective confirmation defaults to target power 0.80 at the predeclared economic MESI and a
family-wise false-positive budget of 0.05 across its declared confirmatory claims, unless a
stronger reason is recorded before confirmation begins.

## Research generations

`COST_EXPECTANCY_RESEARCH_GENERATION_V1` (Appendix A), `PREDICTIVE_RESEARCH_GENERATION_V1` and
`PREDICTIVE_RESEARCH_GENERATION_V2` (Appendix B) keep every recorded result, disposition and
negative finding. Version 3.0 opens no new prediction-first family by default: a predictive
component is evaluated only as part of an admitted playbook. Search memory, family
dispositions, source blocks and search-burden accounting carry forward; new hypotheses receive
new IDs and new budgets, and an earlier rejected result never becomes evidence merely because
the scorer, the name or the stage changed.

---

## Appendix B — superseded Version 2.0, preserved verbatim

Version 2.0 governed the prediction-first research generations. Its text is reproduced below
exactly as it stood when the Owner authorized Version 3.0, up to (and not including) its own
Appendix A, which follows unchanged after this appendix. Nothing in it is edited, and the
historical results it governed are not reinterpreted.

Where Version 3.0 above conflicts with the text below, Version 3.0 governs. The material
conflicts are the mission (prediction-first versus practical economic usefulness) and the
universal predictive source ladder; every rigour rule below remains in force.

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
