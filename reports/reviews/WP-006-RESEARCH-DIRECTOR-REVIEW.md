# WP-006 Research Director review

## Verdict

- Structural verdict: **ACCEPTED_WITH_STATE_FIX**
- Scientific family verdict: **PERSISTENT_TREND_PULLBACK_RECOVERY_V1 = INCONCLUSIVE**
- WP-006 starting HEAD: `444172a359e2663887624da82254cc2185ff85e1`
- Final WP-006 HEAD: `d92088d5ef0426bf64f34326a3224dd9aba93603`

## Verified evidence

- WP-006 starts exactly from `444172a359e2663887624da82254cc2185ff85e1`.
- Final HEAD is `d92088d5ef0426bf64f34326a3224dd9aba93603`.
- Real GitHub Actions run
  [34362902153](https://github.com/C-Gian/trading-bot/actions/runs/34362902153) —
  workflow `check`, branch `main`, event `push`, head `d92088d` — completed
  **SUCCESS** at `2026-09-09T14:20:55Z`. Recorded in
  `reports/reviews/WP-006-CI-EVIDENCE.json`.
- The governed novelty admission commit precedes both preregistration commits and
  every result commit; Git ancestry proves the ordering.
- The effective version-2 preregistrations were committed before any result was
  finalized, and both were frozen in the same commit.
- The pre-execution identity-binding correction happened with **zero strategy trials
  and zero results** observed, and added no variant, profile, seed or numeric search.
- The superseded original preregistrations are preserved unchanged under an immutable
  amendment registry.
- `RECOVERY_CORE` and `RECOVERY_CONFIRM` are both **INCONCLUSIVE** under an unchanged
  `DEVELOPMENT_EVALUATION_V1`.
- No parameter optimization occurred: zero numeric parameter variants, zero searches.
- `FAM-BREAKOUT` remained exhausted at 4/4 configurations and 15/15 trials, and the
  V1 ledger, outcomes, budget, family registry and adaptive decisions are byte
  identical to their first commits.
- 0 sealed BTC queries; sealed dataset state `RESERVED_NOT_ACQUIRED`.
- 0 paper trades; Champion `NONE`; forward evidence `NONE`; real money `false`.

## Non-material state finding

`state/current_state.json` still carried `wp005_integrity.remote_ci = "PENDING_PUSH"`
even though WP-005 remote CI had already been independently verified SUCCESS
(run `34355806303`) and recorded in `reports/reviews/WP-005-CI-EVIDENCE.json`.

This is a stale authoritative-state field, not a scientific error. The value was
truthful when the WP-005 and WP-006 checkpoint reports were written, and those
historical artifacts are **not** rewritten merely because a once-pending external
fact has since resolved.

The fix is prospective and applied to the authoritative current state only:

- `wp005_integrity.remote_ci` is removed from the current state;
- a top-level `remote_ci` block now carries per-work-package remote CI truth,
  linked to the immutable evidence files;
- WP-005 = `SUCCESS`, WP-006 = `SUCCESS` after this review.

## Interpretation

Two consecutive families — `ALIGNED_PARTICIPATION_CONTINUATION_V1` and
`PERSISTENT_TREND_PULLBACK_RECOVERY_V1` — have now produced gross-positive but
friction-consumed, sparsely sampled and concentrated development evidence. Both are
`INCONCLUSIVE` and neither is seal-eligible.

The repeated pattern is informative: price-shape families keep generating a gross
margin that default BTCUSDT Spot friction consumes. Continuing to enumerate price
patterns is unlikely to change that.

## Directions

- Park `FAM-PULLBACK-RECOVERY`; its budget is consumed. Do not modify it, do not
  rescue it with parameters, and do not adopt `RECOVERY_CONFIRM` as the family
  conclusion because it scored higher than the preselected primary.
- Keep `FAM-BREAKOUT` exhausted and `ALIGNED` parked at `INCONCLUSIVE`.
- Move to a genuinely different information source already present in the accepted
  canonical data: the exchange-reported taker volume fields.
- Correct the sealed unlock governance prospectively before any first use, so an
  ordinary scientific sealed allocation is a Research Director decision rather than
  an Owner interruption — while keeping the BTC budget at zero authorized and zero
  consumed, and keeping real capital a separate mandatory Owner gate.
