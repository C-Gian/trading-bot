# P2-CYCLE-FOUNDATION-POWER-GATE-PREP

Result: **PARTIAL**. The three prerequisite gates were built and run in order; two pass
and one fails, so the frozen synthetic detectability curves were not computed and the
actual BTCUSDT cycle result remains unobserved.

`ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED = false` in every artifact this checkpoint wrote.

## Frozen design, unchanged

| | |
| --- | --- |
| structural primary | `BTC_TIME_CYCLE_STRUCTURE_V1` (exactly one) |
| representation | contiguous 4h close-to-close log returns |
| period band | 2-90 UTC days, Fourier spacing oversampled 4, clipped to the band |
| estimator | floating-mean generalized Lomb-Scargle |
| outer procedure | six chronological `DEVELOPMENT_WALK_FORWARD_V1` annual folds, 2019-2024 |
| pre-validation embargo | 90 days, binding before every fold's selection window |
| diagnostics | 2, both non-rescuing, neither executed |
| economic logic | none; no MESI, no trading rule, no asset expansion |

No representation, estimator, band, structural primary or diagnostic was added. The
90-day embargo, the 42-observation block, the 4,999/2,000 replicate budget, the frozen
period and phase grids, the SNR grid and the 0.80 target power are all unchanged.

## A — implementation

`backend/app/research/cycle_structure.py` holds the market-data-free mathematics: the
per-fold frequency grid, the floating-mean generalized Lomb-Scargle statistic split into
a fixed timestamp design and a per-replicate Fourier projection, the training-only AR
sieve, the stationary block bootstrap, the joint replicate semantics, the fidelity
statistics and the gate arithmetic. `backend/app/research/cycle_structure_lab.py` owns
canonical data access. `scripts/audit_p2_cycle_power_gate.py` runs the stages and
verifies the committed artifacts without market data.

Eligible 4h returns: 16,062 of 16,145 union lattice slots. A slot carries a return only
when its two endpoint 4h bars are both canonically complete and exactly consecutive;
gaps are dropped and never interpolated, in the real series and inside every replicate.

| fold | training obs | training span (d) | grid frequencies | validation obs | AR order |
| --- | --- | --- | --- | --- | --- |
| DEV-2019 | 2,442 | 412.5 | 807 | 2,165 | 7 |
| DEV-2020 | 4,611 | 777.5 | 1,521 | 2,169 | 7 |
| DEV-2021 | 6,788 | 1,143.5 | 2,237 | 2,167 | 7 |
| DEV-2022 | 8,954 | 1,508.5 | 2,950 | 2,184 | 7 |
| DEV-2023 | 11,144 | 1,873.5 | 3,664 | 2,182 | 7 |
| DEV-2024 | 13,332 | 2,238.5 | 4,378 | 2,190 | 7 |

## B — null fidelity: REDESIGN_REQUIRED

Thresholds were preregistered and committed in `f33d9e6`, before any fidelity value was
computed; the fidelity artifact carries that file's sha256 so the ordering is auditable.
21 statistics per fold, 999 joint null replicates, training segments only, no outer
validation data and no spectral statistic anywhere in the diagnostic.

28 of 126 checks fail materially. The pattern is systematic across all six folds: the
seven-day block bootstrap cannot carry volatility dependence past its own block, so the
null becomes artificially low-dependence at precisely the periods the primary searches.

| statistic | horizon | DEV-2019 obs/null | DEV-2024 obs/null | result |
| --- | --- | --- | --- | --- |
| `absolute_acf_lag42` | 7 d | 0.1078 / 0.0210 | 0.1498 / 0.0415 | fail, all folds |
| `absolute_acf_lag90` | 15 d | 0.1266 / 0.0043 | 0.1288 / 0.0185 | fail, all folds |
| `absolute_acf_lag180` | 30 d | 0.1221 / -0.0045 | 0.1144 / 0.0084 | fail, all folds |
| `absolute_acf_lag360` | 60 d | 0.0795 / -0.0074 | 0.0767 / 0.0057 | fail, all folds |
| `absolute_acf_lag540` | 90 d | -0.0041 / -0.0066 | 0.0511 / 0.0068 | pass on the absolute-gap escape |
| `return_acf_lag1` | 4 h | -0.1127 / -0.0619 | -0.0543 / -0.0497 | fail in DEV-2019 |
| `return_acf_lag2` | 8 h | -0.0012 / -0.0575 | 0.0027 / -0.0419 | fail in DEV-2019/2020/2022 |
| `log_realized_volatility_sd_30d` | 30 d | 0.4382 / 0.2917 | 0.4343 / 0.3177 | pass |
| `variance_ratio_180` | 30 d | 1.1954 / 0.8303 | 1.2082 / 0.8815 | pass |
| `return_sd` | — | 0.0228 / 0.0212 | 0.0163 / 0.0189 | pass |
| `excess_kurtosis` | — | 13.74 / 15.99 | 18.89 / 19.32 | pass |

The block length stayed at 42 and was not tuned after the discrepancy was seen. The
simulator was verified faithful to the fitted model separately, so the gap belongs to
the frozen null rather than to its implementation. See
`decisions/ADR-0015-P2-CYCLE-NULL-FIDELITY-BLOCK.md`.

## C — joint six-fold semantics: PASS

`JOINT_NESTED_PREFIX_CAUSAL_SIEVE_PATH_V1`. One replicate is one realization of the
entire chronology. The six expanding training windows are nested prefixes of that single
path, so fold *k*'s training slots are literally the slots fold *k+1* also trains on, and
each fold's validation slots reappear in later folds' training windows — 1,633 to 1,650
shared slots per adjacent pair, exactly the validation year minus the next fold's embargo
and purge. Six independent fold statistics are never concatenated.

The path is generated in seven chronological stages split at the embargoed training
boundaries. Every stage after the first is driven by the most recent sieve model whose
training window has already closed, so no simulated slot depends on a fit that saw its
own future. One shared block-bootstrap structure per replicate drives all stages.

Measured against the forbidden independent construction on 120 replicates:

| | joint | independent |
| --- | --- | --- |
| pooled statistic SD | 0.00044334 | 0.00041418 |
| adjacent-fold selected-frequency agreement (10% relative) | 0.660 | 0.393 |

The joint null is wider, as a null preserving overlap must be, and the shared-history
channel shows up exactly where expected — in how often neighbouring folds freeze the
same frequency.

## D — selection and evaluation

Strict chronology holds. Training selects one frequency by maximum power with the longer
period winning an exact tie, which ascending grids plus first-match `argmax` implement
directly. Validation scores that one already-frozen index and never searches: an AST
test pins the single `argmax` to the training array, and a behavioural test perturbs the
validation segment and shows the selected index unmoved while the validation power
changes. The complete selection procedure is rerun inside every replicate, so the
multiplicity of the frequency search is calibrated rather than corrected analytically.

## E — synthetic detectability: not computed

Blocked by the fidelity gate, as the checkpoint requires. The frozen 5 periods x 16
phases x 6 SNR design is implemented and exercised by tests — phase assignment is
`replicate mod 16` and exactly balanced over 2,000 replicates; injected amplitude
reproduces its declared SNR to 1e-12 for every period, phase and SNR; power is
non-decreasing in SNR beyond Monte Carlo tolerance because the SNR grid shares one
simulated path per replicate. No power number was produced, and no descriptive amplitude
translation was reported, because producing them would have required the failed null.

## F — computational feasibility: PASS

The exact frozen budget, with no reduction of replicates, periods, phases or grid
resolution and no approximation chosen for speed.

| | |
| --- | --- |
| Fourier-sum elements per replicate | 183,701,444 |
| benchmark | 50 replicates, 4.41 s path projection + 0.046 s per combination cell |
| projected full runtime | ~673 s for 7,079 path projections and 60,000 combination cells |
| runtime budget | 14,400 s |
| peak memory estimate | 437 MiB at batch size 250 |

Optimizations are exact reformulations only: precomputed fixed-timestamp design terms,
batched BLAS projections over replicates, algebraic reuse of one path across the SNR grid
via linearity of the Fourier sums, one 16-column injection projection per period, and
immutable per-fold frequency grids.

## G — leakage

Two structural guards, not conventions. The only route from a series to a pooled
statistic is `replicate_statistics`, which accepts a `SimulatedPath` and refuses a raw
array; and `CycleGrids` has no accessor that pairs a fold's validation slots with real
returns — `validation_returns` always raises. Real returns are zeroed at and after the
last embargoed training boundary. Every artifact passes a forbidden-key audit over 22
keys that could carry a selected period, validation power, pooled statistic, p-value or
market classification.

## Deterministic validation

- `backend/tests/test_cycle_structure.py`: 44 tests covering causal 4h aggregation,
  non-interpolation, the frozen band, the single primary and diagnostic budget, the
  no-validation-search rules, every leakage guard, training-only AR order selection, the
  frozen block length, joint replicate semantics, phase determinism, SNR amplitude
  exactness, SNR monotonicity, the every-period gate rule, blocked execution on any
  failed prerequisite, and the scientific accounting.
- `scripts/audit_p2_cycle_power_gate.py --check` re-derives the gate from the committed
  intermediates with no market data.
- The fidelity artifact regenerates byte-identically from market data; only wall-clock
  fields of the compute benchmark vary between runs.

## Scientific accounting

Unchanged by this checkpoint: 26 completed experiments, 12 observed material economic
hypotheses, 0 sealed queries, Champion `NONE`, real money `false`, 0 material economic
hypotheses executed, no cycle component implemented, no economic strategy created.

## Next action

RESEARCH DIRECTOR REVIEW. A new null design and version is required for
`BTC_TIME_CYCLE_STRUCTURE_V1`, or an explicit recorded acceptance of the frozen null's
limitation. No remedy was attempted here.
