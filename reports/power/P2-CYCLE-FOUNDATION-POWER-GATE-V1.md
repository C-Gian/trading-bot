# P2-CYCLE-FOUNDATION-POWER-GATE-V1

Design: `BTC_TIME_CYCLE_STRUCTURE_V1`. Future structural hypothesis: `BTC_TIME_CYCLE_STRUCTURE_V1`.

Prospective preparation only. The actual BTCUSDT cycle result was not computed:
no training-selected period, no outer validation power, no pooled statistic, no
structural p-value and no market classification exists.

ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED = False

## Frozen design

- representation: CONTIGUOUS_4H_CLOSE_TO_CLOSE_LOG_RETURN
- period band (days): [2.0, 90.0]
- frequency grid: FOURIER_SPACING_OVERSAMPLING_4_CLIPPED_TO_FROZEN_BAND
- spectral estimator: FLOATING_MEAN_GENERALIZED_LOMB_SCARGLE
- structural primaries: 1
- maximum diagnostics: 2
- outer folds: DEVELOPMENT_WALK_FORWARD_V1_ANNUAL_2019_TO_2024
- pre-validation embargo (days): 90
- selection: TRAINING_MAXIMUM_POWER_ONE_PERIOD_LONGER_PERIOD_TIE_BREAK
- evaluation: VALIDATION_POWER_AT_TRAINING_SELECTED_FREQUENCY_ONLY
- validation frequency search: False
- economic MESI: None

## Null fidelity

- method: TRAINING_ONLY_AR_SIEVE_BIC_0_TO_42_PLUS_STATIONARY_RESIDUAL_BLOCK_BOOTSTRAP_EXPECTED_42
- expected block length (4h obs): 42
- block tuned after observation: False
- training only: True
- validation results used: False
- fidelity replicates: 999
- thresholds preregistered: 7bc16573c460fb6949b6dffbd8968fabf842d7f5c0a763ec63fc14e1ba5f151a
- material failures: 28

### NULL_FIDELITY_STATUS: REDESIGN_REQUIRED

Materially failing checks:

- `DEV-2019/absolute_acf_lag180`
- `DEV-2019/absolute_acf_lag360`
- `DEV-2019/absolute_acf_lag42`
- `DEV-2019/absolute_acf_lag90`
- `DEV-2019/return_acf_lag1`
- `DEV-2019/return_acf_lag2`
- `DEV-2020/absolute_acf_lag180`
- `DEV-2020/absolute_acf_lag360`
- `DEV-2020/absolute_acf_lag42`
- `DEV-2020/absolute_acf_lag90`
- `DEV-2020/return_acf_lag2`
- `DEV-2021/absolute_acf_lag180`
- `DEV-2021/absolute_acf_lag360`
- `DEV-2021/absolute_acf_lag42`
- `DEV-2021/absolute_acf_lag90`
- `DEV-2022/absolute_acf_lag180`
- `DEV-2022/absolute_acf_lag360`
- `DEV-2022/absolute_acf_lag42`
- `DEV-2022/absolute_acf_lag90`
- `DEV-2022/return_acf_lag2`
- `DEV-2023/absolute_acf_lag180`
- `DEV-2023/absolute_acf_lag360`
- `DEV-2023/absolute_acf_lag42`
- `DEV-2023/absolute_acf_lag90`
- `DEV-2024/absolute_acf_lag180`
- `DEV-2024/absolute_acf_lag360`
- `DEV-2024/absolute_acf_lag42`
- `DEV-2024/absolute_acf_lag90`

## Joint six-fold null semantics

- joint replication method: JOINT_NESTED_PREFIX_CAUSAL_SIEVE_PATH_V1
- cross-fold dependence handling: SINGLE_JOINT_PATH_PER_REPLICATE_SIX_FOLD_STATISTICS_READ_FROM_ONE_REALIZATION
- shared history handling: NESTED_PREFIX_TRAINING_WINDOWS_SHARE_IDENTICAL_SIMULATED_SLOTS_AND_EARLIER_VALIDATION_SLOTS_REAPPEAR_IN_LATER_TRAINING_WINDOWS
- folds simulated independently: False
- joint pooled SD: 0.0004433391
- independent pooled SD: 0.000414181
- joint / independent SD ratio: 1.0703994131

### JOINT_REPLICATION_STATUS: PASS

## Computational feasibility

- frequencies per fold: {'DEV-2019': 807, 'DEV-2020': 1521, 'DEV-2021': 2237, 'DEV-2022': 2950, 'DEV-2023': 3664, 'DEV-2024': 4378}
- training observations per fold: {'DEV-2019': 2442, 'DEV-2020': 4611, 'DEV-2021': 6788, 'DEV-2022': 8954, 'DEV-2023': 11144, 'DEV-2024': 13332}
- validation observations per fold: {'DEV-2019': 2165, 'DEV-2020': 2169, 'DEV-2021': 2167, 'DEV-2022': 2184, 'DEV-2023': 2182, 'DEV-2024': 2190}
- Fourier sum elements per replicate: 183701444
- benchmark replicates: 50
- benchmark elapsed seconds: 4.402879
- projected full runtime seconds: 673.53665498
- peak memory estimate (MiB): 436.9008483887
- optimizations: PRECOMPUTED_FIXED_TIMESTAMP_GLS_DESIGN_TERMS, BATCHED_BLAS_FOURIER_PROJECTIONS_OVER_REPLICATES, EXACT_LINEAR_REUSE_OF_ONE_PATH_ACROSS_THE_FROZEN_SNR_GRID, SIXTEEN_PHASE_INJECTIONS_PROJECTED_ONCE_PER_FROZEN_PERIOD, IMMUTABLE_PER_FOLD_FREQUENCY_GRIDS_REUSED_BY_EVERY_REPLICATE
- replicates reduced: False
- frequency grid coarsened: False

### COMPUTATIONAL_STATUS: PASS

## Prospective detectability

Not computed. A prerequisite gate did not pass, so the frozen synthetic
detectability curves were not run and no actual market result was exposed.

## P2_POWER_GATE_STATUS: REDESIGN_REQUIRED

- gate rule: POWER_AT_LEAST_0_80_AT_SNR_CYCLE_0_50_FOR_EVERY_FROZEN_PERIOD
- target power: 0.8
- gate SNR: 0.5
- power at gate SNR by period: {}
- prerequisites pass: False
- preregistration authorized: False
- actual execution authorized: False
- next action: RESEARCH_DIRECTOR_REVIEW
