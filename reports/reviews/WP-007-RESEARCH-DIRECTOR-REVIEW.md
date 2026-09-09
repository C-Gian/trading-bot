# WP-007 Research Director review

## Verdict

- Structural verdict: **ACCEPTED**
- Scientific family verdict: **FAM-ORDER-FLOW = REJECT_COST_DOMINATED**
- True base / merge base: `d92088d5ef0426bf64f34326a3224dd9aba93603`
- Final WP-007 HEAD: `762b3b77f686305b1c73f19956d0b9b16b7a9b1c`
- Ancestry: 16 commits ahead / 0 behind its reviewed base

## Verified evidence

- Real GitHub Actions run
  [34375244463](https://github.com/C-Gian/trading-bot/actions/runs/34375244463) —
  workflow `check`, branch `main`, event `push`, head `762b3b7` — completed
  **SUCCESS** at `2026-09-09T16:13:25Z`. The immutable observation is recorded in
  `reports/reviews/WP-007-CI-EVIDENCE.json`.
- The effective version-2 preregistrations were committed at
  `e541da5db097d322a10d9f7666973a2f4829a0c2` before the result commit
  `d5fd0bcbc5fc0f6aaae42ebba721ba55c9447ac3`; Git proves the preregistration
  commit is the result commit's direct parent.
- Two tooling corrections occurred before market evaluation. The first canonicalized
  an in-memory executable specification before any preregistration or admission
  artifact was written. The second excluded WP-007's own already-governed entries
  from novelty replay; the original preregistrations remain preserved and the
  correction led to committed version-2 declarations. Both records state zero
  strategy trials and zero observed results before correction, with no scientific
  scope, threshold, parameter, or executable-behavior change.
- Canonical/source order-flow integrity and independent oracle reconciliation both
  passed. The accepted canonical development dataset, manifest and content hash did
  not change.
- SEARCH_MEMORY_V2 admitted `FLOW_CORE` as `NEW_FAMILY` under `FAM-ORDER-FLOW` and
  `FLOW_PRICE_RESPONSE` as its structural descendant before results.
- `SEALED_EVALUATION_V1_1` stayed locked at 0 authorized / 0 consumed BTC queries;
  no post-cutoff or sealed BTC data was acquired or inspected.

## Scientific disposition

`FLOW_CORE`, the preselected primary, is **REJECT_COST_DOMINATED**: default expectancy
`-0.0667167056 R`, zero-cost `+0.0533577522 R`, double-cost `-0.1867911419 R`,
one-hour-delay `-0.0619009982 R`, 1,828 resolved trades, 1/6 nonnegative folds and
241 minimum-fold trades. The gross signal does not survive realistic friction.

`FLOW_PRICE_RESPONSE` is also **REJECT_COST_DOMINATED** and does not replace the
primary merely because it is less negative. `FAM-ORDER-FLOW` is parked: do not move
the fixed 0.5 balance threshold, add filters, or otherwise attempt a result-driven
rescue.

Champion remains `NONE`; sealed evaluations and queries remain 0; paper trades remain
0; forward evidence remains `NONE`; real-money authorization remains `false`.
