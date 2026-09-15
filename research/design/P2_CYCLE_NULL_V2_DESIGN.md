# P2 Cycle Null V2 — append-only redesign

Status: FROZEN BEFORE BLOCK-SUPPORT AND FIDELITY MEASUREMENT.

This addendum changes only the future calibration null for
`BTC_TIME_CYCLE_STRUCTURE_V1`. It does not rewrite the frozen structural design or the
failed Null V1 record. The structural primary remains
`DESIGNED_NOT_PREREGISTERED_NOT_EXECUTED`; its actual BTC result is unavailable.

## Formal Null V1 disposition

`P2_NULL_V1_STATUS = FAILED_FIDELITY_REJECTED_FOR_INFERENCE`.

The frozen AR-sieve plus expected-seven-day residual stationary bootstrap failed 28
preregistered material fidelity checks. It systematically underrepresented long-horizon
absolute-return and volatility dependence inside the 2–90 day primary search band.
This is a methodological failure, not a rejection or support classification of the
unexecuted structural primary. Every Null V1 artifact remains immutable.

## Frozen Null V2

- ID: `P2_CYCLE_NULL_V2`.
- Method: `TRAINING_ONLY_RAW_RETURN_STATIONARY_BLOCK_BOOTSTRAP_EXPECTED_1080_V2`.
- Donors: only raw, eligible, embargoed-training 4h close-to-close log returns.
- Mean/volatility models: none. AR, GARCH, HAR and FIGARCH are not used.
- Expected geometric block length: exactly 1,080 eligible 4h observations, nominally
  180 days. No alternative block length may be tested.
- Rationale fixed before V2 measurement: 1,080 is twice the longest searched 90-day
  period. Under ideal stationary-bootstrap geometry the same-block survival is about
  96%, 92%, 85%, 72% and 61% at 7, 15, 30, 60 and 90 days respectively. These are
  theoretical properties, not observed BTC targets.

The unchanged primary uses contiguous 4h returns, the 2–90 UTC-day band, floating-mean
generalized Lomb–Scargle, six annual 2019–2024 `DEVELOPMENT_WALK_FORWARD_V1` folds, one
training-selected frequency per fold, and at most two non-rescuing diagnostics.

## Gap-safe donor semantics

Canonical gaps are never interpolated. A block continues only to the next eligible raw
return exactly one canonical 4h slot later. Encountering a source gap or the causal
training boundary terminates the block and draws a new uniformly sampled legal start
from the same training-only donor pool. Blocks never wrap or concatenate across gaps.

Before fidelity, each fold must report contiguous segment lengths, admissible starts,
the exact block-length distribution after forced termination, and same-block survival
at lags 42, 90, 180, 360 and 540. `BLOCK_SUPPORT_STATUS = PASS` only when lag-540
survival is at least 0.50 in every fold. Otherwise status is `REDESIGN_REQUIRED` and the
workflow stops without changing the block length or gap rule.

## Interpretation

Long real-return blocks deliberately retain volatility regimes, heavy tails,
short-memory return dependence, nonlinear dependence and local pseudo-periodic
structure. The null asks whether selected timing is more chronologically repeatable
than dependent/local structure already present in long observed training blocks.
Apparent local cycles are not removed from donors.

## Joint chronology

`JOINT_NESTED_PREFIX_CAUSAL_LONG_BLOCK_PATH_V2` generates one complete chronology per
replicate. Nested training prefixes read identical generated slots; earlier simulated
validation slots reappear in later simulated training. Each causal stage uses only the
latest market donor prefix historically available at its boundary, apart from the
first fold's necessary in-sample calibration prefix. Folds are never simulated as six
independent nulls.

## Immutable fidelity and prospective power gates

All 21 per-fold fidelity statistics and every materiality threshold are exactly those
in `P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1.json` at normalized SHA-256
`7bc16573c460fb6949b6dffbd8968fabf842d7f5c0a763ec63fc14e1ba5f151a`.
The count is 999 with seed 20260915. Any failed criterion produces
`NULL_V2_FIDELITY_STATUS = REDESIGN_REQUIRED` and stops the workflow.

Only after block support, fidelity, joint replication and compute all pass may the
unchanged workload run: 4,999 null replicates and 2,000 synthetic replicates per cell;
periods 3, 7, 14, 30 and 60 days; 16 phases; SNR 0, 0.10, 0.25, 0.50, 0.75 and 1.00;
target power 0.80 at gate SNR 0.50. Injection remains a log-price sinusoid differenced
to 4h returns. All training frequency selection is repeated. The 14,400-second compute
budget is unchanged.

No actual training-selected BTC period, outer-validation powers, pooled primary
statistic, structural p-value or support classification may be calculated or emitted.
No sealed data, asset expansion, cycle trading, or real money is authorized.

