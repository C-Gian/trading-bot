# WP-005 matched-control diagnostic contract

Status: preregistered before matched-control results.

This is exposed-development diagnostic work, not a new strategy experiment or
independent significance test. It adds zero economic hypotheses, strategy
variants, numeric variants, sealed queries, or paper observations. The existing
FAM-BREAKOUT strategy budget remains exhausted.

All controls use the WP-004 V2 annual windows, 26x1h and 43x4h common eligibility,
source-grid quarantine, hourly close/next-minute-open clock, canonical 1m paths,
2% stop, 4% target, 1,440-minute horizon, conservative gaps/unresolved handling,
and identical single-position occupancy/release semantics.

The matched parent is the frozen 24h close-above-prior-high rule with no regime or
participation gate, run exactly at DEFAULT, ZERO, and DOUBLE costs. Each of 32
fixed random controls selects, per fold and before occupancy, exactly as many
parent candidates as ALIGNED had raw gate-positive candidates. Ranking uses only
the preregistered seed and timestamp SHA-256; outcomes cannot affect selection.

Quantiles use sorted values, position `p*(n-1)`, and linear interpolation between
adjacent values (Hyndman-Fan type 7 / NumPy default), rounded to 10 decimals. The
q90 comparison is an allocation hurdle, not an alpha-level p-value.

Support requires every integrity prerequisite plus both `delta_parent >= 0.12 R`
and ALIGNED default expectancy strictly above the random-gate q90. Otherwise the
diagnostic is weakened; a prerequisite failure makes it unresolved. WP-004 stays
INCONCLUSIVE under every outcome, with no Champion, sealed evaluation, paper
trading, or parameter rescue.
