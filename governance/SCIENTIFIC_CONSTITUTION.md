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

## Governance

This Constitution is Owner-controlled and cannot be automatically weakened or replaced by an AI agent.

Lower-level research workflow may evolve, but never in conflict with this document.
