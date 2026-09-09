# Development evaluation V1

The exact machine schedule is `research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json`.
It is frozen before algorithm design implementation or new market outcomes.

Six expanding chronological folds validate calendar years 2019–2024. The initial
development span starts at dataset inception. Each year's first UTC day is an
embargo; validation begins January 2, ends at the following January 1 exclusively,
and permits signals through end minus 24 hours inclusively. The final exclusive
fence is 2025-01-01T00:00:00Z, not permission to read any minute opening then.
All accessed minute opens are at or before 2024-12-31T23:59:00Z.

Each train/development end is nine days before validation start. The 216-hour
purge covers the oldest required 4h bar open (up to 175 hours old), the optional
one-hour timing shift, and the 24-hour maximum outcome. Subsequent expanding
development spans may contain earlier validation observations; this is explicit
development reuse. There is no random K-fold and no sealed feedback.

The selected rules have no fitted parameters, fold-specific calibration, or model
selection. Train spans define permissible chronology and warm-up, not an unused
optimization license. Causal feature warm-up may cross the purge because the purge
excludes fitting labels, not legitimately available past market observations.
Each validation component starts flat and ends with no newly opened position whose
declared maximum outcome interval would exceed its boundary.

Primary aggregate: total default-cost net R divided by all valid resolved trades
across the six disjoint validation intervals. Invalid and unresolved outcomes have
no invented P&L; both counts and rates are shown. Unresolved positions quarantine
new entries until their original expiry. Stability includes each fold (including
empty folds), equal-fold mean, positive/nonnegative fraction, extrema, absolute
P&L and trade-count concentration, positive-profit concentration, leave-one-fold-out
means, yearly attribution, and predeclared regime attribution.

Minimum diagnostics are 120 total resolved trades, 15 in every fold, an estimated
trade ESS of 60, and unresolved/attempted <=1%. ESS is n divided by
1+2 times the sum of positive empirical autocorrelations at trade lags 1–5,
capped at n. It is only a dependence diagnostic, not a proof of independence.
Each lag uses the whole-sequence mean, lagged centered-product sum divided by
the whole-sequence centered-square sum. A constant sequence assigns zero to
undefined autocorrelations and is explicitly flagged; ESS then equals n without
implying independent observations.
Also show the effective number of active weeks (Kish concentration of weekly
trade counts). No significance or confidence level is inferred from either.

Terminal classification is deterministic, in order: inadequate count/ESS/data
diagnostics -> INCONCLUSIVE; default <=0 and zero-cost >0 ->
REJECT_COST_DOMINATED; default <=0 otherwise -> REJECT; positive default but
negative doubled-cost -> REJECT_COST_DOMINATED; positive default with fewer than
four nonnegative folds, any nonpositive leave-one-fold-out mean, or more than half
of positive fold profit concentrated in one fold -> REJECT_UNSTABLE; otherwise
PROMISING_DEVELOPMENT_ONLY. Structural invalidity blocks finalization entirely.
The family follows the ALIGNED primary variant, never the best result.

Timing perturbation delays the frozen condition exactly one hourly clock, using
the latest completed close at execution-decision time for unchanged barriers.
The horizon remains 24 hours from entry. Old feature observations are not updated
after the condition was formed. Structural ablations supply the required feature
and regime robustness checks. DEFAULT, ZERO, DOUBLE, and DELAY_1H are all retained.

Existing WP-003 controls are compared using their immutable trade records sliced
to these signal windows, including the full 24-hour outcome containment rule.
No control is rerun, no seed is selected. Earlier occupancy, their 169-hour
eligibility, and historical intraminute exit orchestration limit comparability.
These are descriptive controls, not paired causal estimates of gate effects.
Buy-and-hold is excluded from product-horizon comparisons. Full-history summaries
remain descriptive and do not override the validation metric hierarchy.
