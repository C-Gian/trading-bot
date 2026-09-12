# WP-011 Research Director review

Verdict: **ACCEPTED**

## Identity

- Reviewed base: `dfd57339d9a1b60ed64ae865c36fd3df279733c5`
- Reviewed result HEAD: `16344c17bf7a0be579bb60fc42b58b04b9dc6c88`
- Ancestry: 5 commits ahead / 0 behind `main`
- Phase-1 admission and preregistration commit:
  `ca98565f1df6ea52dfcd3cd770ffb50cc5e76ee5`

The Phase-1 commit precedes every market result in Git history. Admission, allocation and
both preregistrations were committed before a single validation hour was evaluated, and
the admission record itself carries `market_results_observed_at_admission = 0`.

## Scientific disposition

- `FAM-ADAPTIVE-EWLS-MACRO` primary `EWLS_INTERNAL_MACRO`: **REJECT_COST_DOMINATED**
- Structural ablation `EWLS_INTERNAL_ONLY`: **INCONCLUSIVE**
- Macro incremental effect: **NEGATIVE**

The primary executed 1,487 resolved trades across the six frozen annual folds at
-0.0987513255 R per trade, cumulative -146.84 R, with 0 of 6 nonnegative folds. Gross
expectancy is barely positive (ZERO +0.0212985363 R) and is consumed by realistic costs;
DOUBLE -0.2188011787 R and DELAY_1H -0.1081651326 R confirm the loss is cost structure
rather than a timing artifact.

Adding the eight point-in-time macro features cost -0.0460 R per trade against the
internal-only ablation (-0.0527152557 R) and took fold stability from 2 of 6 to 0 of 6,
while the macro block absorbed 69.7% of mean absolute standardized coefficient mass and
its coefficient signs flipped across the 71 monthly fits. That is the signature of
fitting noise, not a durable economic relationship.

## Accepted on evidence quality

- Independent reconciliation **PASS**: a longhand weighted fit that never calls the
  production lab reproduced the 50,595-row universe, re-fitted twelve monthly models
  across both configurations and every fold, and agreed on fit rows, rank, DEFAULT
  executed metrics, signal and model timestamps, ZERO/DOUBLE signal reuse and purge
  containment.
- Macro point-in-time audit **PASS**: 216 level comparisons agree exactly with a naive
  independent rescan, 494 revision boundaries checked, zero backward leaks.
- ALFRED source integrity **PASS**: deterministic rebuild over all 43,104 committed raw
  vintage files reproduces the accepted manifest.
- One pre-execution correction was recorded before any result, refusing the inadmissible
  2019-01 monthly fit rather than weakening the frozen hard-fail rule.

## Authorizations withheld

- **No tuning or rescue is authorized.** The half-life, cadence, feature set, threshold
  and geometry are exposed and must not be re-searched on this family.
- The family is **parked**. A legitimate revisit requires a new explicit Research
  Director allocation with cumulative accounting.
- Champion: **NONE**.
- Sealed queries: **0**. No sealed query is authorized by this review.
- Both configurations are sealed-ineligible: `EWLS_INTERNAL_MACRO`
  `NOT_ELIGIBLE_REJECTED`, `EWLS_INTERNAL_ONLY` `NOT_ELIGIBLE_INCONCLUSIVE`.
- Paper strategy unchanged: the V1 ALIGNED paper-research candidate is untouched by this
  result and no model from WP-011 may begin paper evidence.

## What this does and does not settle

Falsified: that a prospectively fixed 180-day recency-weighted linear combination of these
eight internal and eight point-in-time macro features, refitted monthly, selects BTCUSDT
long opportunities with robust positive net expectancy after realistic costs.

Not falsified: the Owner's broader multi-signal thesis. Non-linear structure, regime
conditioning, interaction terms, other information families including the paused WP-009
news channel, other labels, horizons and prospective forward evidence all remain
untested.

Next direction: `RESEARCH_DIRECTOR_SELECTED_REGIME_CONDITIONED_CHALLENGER`.
