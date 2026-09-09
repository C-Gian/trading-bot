# WP-008 Research Director review

## Verdict

- Structural verdict: **ACCEPTED**
- Scientific family verdict: **FAM-SUPERVISED-LINEAR = REJECT_COST_DOMINATED**
- Required reviewed base: `762b3b77f686305b1c73f19956d0b9b16b7a9b1c`
- Final WP-008 HEAD: `ffeb73d6c0799ccfc09d0ee3b85c25d8e52364c2`
- Ancestry: 13 commits ahead / 0 behind the reviewed base

## Verified evidence

- Real GitHub Actions run
  [34392236263](https://github.com/C-Gian/trading-bot/actions/runs/34392236263) —
  workflow `check`, branch `main`, event `push`, head `ffeb73d` — completed
  **SUCCESS** at `2026-09-09T18:59:09Z`. The immutable observation is recorded in
  `reports/reviews/WP-008-CI-EVIDENCE.json`.
- Both fixed preregistrations were committed at
  `2d8bc11b2bbc76db387652804f7ad8c492e3d493` before the result commit
  `88e9c6e941be54b2fe65b802e15312eadc01c7ec`; Git proves the preregistration
  commit is the result commit's direct parent.
- `SUPERVISED_FEATURES_V1` leakage audit passed. Every expanding fold used
  training-only scaling and complete training-label outcomes strictly before
  validation; the closest outcome remained 193 hours before validation.
- Independent reconstruction passed for all 12 OLS fits, including train boundaries,
  feature order, scaling, coefficients, prediction hashes, emitted timestamps, and
  DEFAULT compact-artifact metrics.
- `RESEARCH_ARTIFACT_STORAGE_V1` passed deterministic file/logical hash validation.
  Historical evidence was not rewritten and training matrices were not committed.
- No hyperparameter, threshold, feature, model, regularization, or execution search
  occurred. No result-affecting dependency changed after results.

## Scientific disposition

`LINEAR_FULL`, the preselected primary, is **REJECT_COST_DOMINATED**: default
expectancy `-0.1142218454 R`, zero-cost `+0.0058246386 R`, double-cost
`-0.2342683271 R`, one-hour-delay `-0.1098336131 R`, 1,003 trades, 1/6
nonnegative folds, and 82 minimum-fold trades.

`LINEAR_NO_FLOW` is also **REJECT_COST_DOMINATED** and does not replace the primary.
`FAM-SUPERVISED-LINEAR` is parked; result-driven linear-family rescue remains blocked.

Champion remains `NONE`; sealed evaluations and queries remain 0; paper trades remain
0; forward evidence remains `NONE`; real-money authorization remains `false`.
