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
