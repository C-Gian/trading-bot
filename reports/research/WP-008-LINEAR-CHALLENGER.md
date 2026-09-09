# WP-008 leakage-safe linear challenger

**DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE**

## Design and chronology

SEARCH_MEMORY_V2 admitted `LINEAR_FULL` as a new `FAM-SUPERVISED-LINEAR` root and
`LINEAR_NO_FLOW` as its structural ablation before results. Implementation preceded
admission; both fixed preregistrations preceded the result commit. Exactly twelve OLS
fits and eight execution profiles ran, with no model, feature, hyperparameter, or
threshold search.

Each annual model used only expanding historical rows strictly before the validation
start minus 216 hours. Labels were isolated default-cost 2% stop / 4% target / 24h
plans. Invalid and unresolved labels were excluded and counted. Training-only
`ddof=0` scaling, full-rank OLS with intercept, and the strict
`predicted_default_net_R > 0.0` signal rule were fixed. The independent reconciliation
reproduced all coefficients, prediction hashes, emitted signal timestamps, and DEFAULT
metrics; the closest training-label outcome remained 193 hours before validation.

## Results

| Configuration | Classification | DEFAULT R | ZERO R | DOUBLE R | DELAY_1H R | Trades | Nonnegative folds | Min fold |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LINEAR_FULL | REJECT_COST_DOMINATED | -0.1142218454 | +0.0058246386 | -0.2342683271 | -0.1098336131 | 1,003 | 1/6 | 82 |
| LINEAR_NO_FLOW | REJECT_COST_DOMINATED | -0.1172203904 | +0.0028474849 | -0.2372882645 | -0.1041653216 | 969 | 1/6 | 72 |

FULL predicted positive on 9,535 of 48,784 eligible validation rows (19.55%), so it
did not merely signal the broad long drift continuously. Nevertheless, its isolated
prediction/label correlation changed sign by fold and ranged from `-0.0330652157` to
`+0.1090860500`. Only 2023 had positive executed DEFAULT expectancy; positive-fold
profit concentration is 100%. Condition numbers remained benign (`5.10–5.28`), so
numerical ill-conditioning does not explain the economic failure. Five of eight FULL
coefficient signs were consistent across folds, but sign consistency did not translate
to stable future net expectancy.

Removing the two taker-flow descriptors worsened DEFAULT expectancy by only
`0.0029985450 R` and left the classification unchanged. This ablation does not show a
material incremental flow contribution inside the fixed linear architecture and cannot
replace the preselected FULL primary.

## Descriptive comparison

FULL is worse than the frozen random-control mean (`-0.0967774607 R`), SMA trend
(`-0.1081210229 R`), breakout (`-0.0535976983 R`), ALIGNED (`+0.1373934676 R`),
pullback recovery core (`+0.0003823075 R`), and order-flow core (`-0.0667167056 R`).
No-trade remains zero exposure rather than a return estimate. These are descriptive,
unpaired comparisons because eligibility and occupancy differ between families.

The learned combination barely produces positive gross/zero-cost expectancy, while
default friction overwhelms it and doubled friction deepens the loss. Delay changes
the magnitude only modestly and never changes the disposition. The model therefore
rearranges exposed-development noise rather than improving on the strongest manual
clue, ALIGNED.

## Disposition

`FAM-SUPERVISED-LINEAR` is parked as `REJECT_COST_DOMINATED`. Do not tune its feature
set, threshold, regularization, algorithm, interactions, label, barriers, horizon, or
profiles. Neither configuration is seal-eligible. Champion remains `NONE`; sealed BTC
queries, paper trades, and real-money authorization remain zero/absent.
