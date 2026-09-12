# WP-013 contextual NFCI interaction result

`FAM-CONTEXTUAL-MACRO-INTERACTIONS` is **REJECT_COST_DOMINATED** under the frozen
`DEVELOPMENT_EVALUATION_V1` rule. This is exposed development evidence, predictive and
not causal.

The primary `NFCI_CONTEXT_INTERACTIONS` model scored -0.1086772939 R/trade over 1,060
resolved DEFAULT trades (cumulative -115.1979 R), with 1/6 nonnegative annual folds,
minimum fold 75, trade ESS 900.78, and OOS prediction/isolated-label Pearson
-0.0058938223. ZERO was +0.0113442309, DOUBLE -0.2286988141, and DELAY_1H
-0.0829523178 R/trade. Costs consume the small gross expectancy; neither doubled costs
nor a one-hour delay is viable.

The matched `INTERNAL_ONLY_MATCHED_NFCI` control scored -0.1103044148 R/trade over
1,001 trades. The primary-control difference is +0.0016271209 R/trade, descriptive rather
than paired because the generated signals and occupancy differ. Annual expectancy deltas
were positive in four folds and negative in two, but the primary itself was nonnegative
only in 2019. The improvement is therefore neither economically material nor robust.

Five of eight standardized interaction coefficients retained one exact sign across all
six expanding folds. The fitted raw effective slopes at NFCI -1, 0, and +1 differ
substantially and frequently reverse sign between endpoints. That proves the added terms
can express contextual relationships, not that those relationships generalize: pooled
OOS correlation fell below zero, 2023 deteriorated sharply against control, and DEFAULT
expectancy remained deeply negative. The evidence is more consistent with added unstable
degrees of freedom than useful context learning.

Independent reconciliation rebuilt the raw ALFRED vintage timeline, 59,025-row matched
universe, all eight raw interaction columns, training rows, twelve longhand OLS fits,
48,784 validation-hour predictions, DEFAULT signals, 2,077 direct execution attempts,
and metrics without importing the primary lab or runner. All checks passed with no
mismatch.

Descriptive comparisons (not paired across families): WP-013 was better than WP-008
LINEAR_FULL (-0.1142218454) by +0.0055445515 R/trade, worse than WP-011 internal-only
(-0.0527152557) by -0.0559620382, worse than WP-011 macro (-0.0987513255) by
-0.0099259684, worse than WP-012 primary (-0.1071860713) by -0.0014912226, and far below
ALIGNED (+0.1373934676). Breakout was -0.0482093869; no-trade executed zero trades and
has no expectancy estimate.

No Champion, sealed query, paper-strategy replacement, or real-money authorization
follows. WP-009 remains paused and the V1 ALIGNED paper candidate is unchanged.
