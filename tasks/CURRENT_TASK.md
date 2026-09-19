# CURRENT TASK — RESEARCH-DIRECTOR-REVIEW-STAGE-3-CROSS-ASSET-BREADTH-CLOSURE

Status: AWAITING_RESEARCH_DIRECTOR_REVIEW_NO_EXECUTOR_WORK_AUTHORIZED

Predecessor: `PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1` — executed, family disposition
`REJECTED_DEVELOPMENT_NO_SEALED`.

`PREDICTIVE_STAGE3_CROSS_ASSET_BREADTH_FAMILY_V1` is **closed**. Both predeclared
configurations were executed in one work package, the search budget is fully consumed, and
nothing is reserved.

## Where the predictive generation now stands

Eight configurations across four information families have been executed on the frozen BTCUSDT
24h terminal target. None advanced.

| family | configuration | win rate | coverage | primary delta | 97.5% paired interval | classification |
| --- | --- | --- | --- | --- | --- | --- |
| Stage 1 internal | `INTERNAL_LINEAR_DUAL_HEAD_V1` | 0.4888 | 0.9357 | −0.0351 vs `ALWAYS_UP` | [−0.0608, −0.0080] | `NO_ADVANCE_INTERNAL_LINEAR_V1` |
| Stage 1 internal | `INTERNAL_HGBR_DUAL_HEAD_V1` | 0.4896 | 0.9357 | −0.0343 vs `ALWAYS_UP` | [−0.0575, −0.0100] | `NO_ADVANCE_INTERNAL_HGBR_V1` |
| Stage 2 funding | `FUNDING_LINEAR_DUAL_HEAD_V1` | 0.4855 | 0.99998 | −0.0093 vs base rate | [−0.0296, +0.0126] | `NO_ADVANCE_FUNDING_LINEAR_V1` |
| Stage 2 funding | `FUNDING_HGBR_DUAL_HEAD_V1` | 0.4941 | 0.99998 | −0.0006 vs base rate | [−0.0177, +0.0174] | `NO_ADVANCE_FUNDING_HGBR_V1` |
| Stage 2 open interest | `OPEN_INTEREST_LINEAR_DUAL_HEAD_V1` | 0.4846 | 0.9901 | −0.0241 vs `ALWAYS_UP` | [−0.0523, +0.0079] | `NO_ADVANCE_OPEN_INTEREST_LINEAR_V1` |
| Stage 2 open interest | `OPEN_INTEREST_HGBR_DUAL_HEAD_V1` | 0.5052 | 0.9901 | −0.0035 vs `ALWAYS_UP` | [−0.0326, +0.0298] | `NO_ADVANCE_OPEN_INTEREST_HGBR_V1` |
| Stage 3 cross-asset breadth | `CROSS_ASSET_BREADTH_LINEAR_V1` | 0.4930 | 0.9984 | −0.0338 vs base rate | [−0.0597, −0.0071] | `NO_ADVANCE_CROSS_ASSET_BREADTH_LINEAR_V1` |
| Stage 3 cross-asset breadth | `CROSS_ASSET_BREADTH_HGBR_V1` | 0.4882 | 0.9984 | −0.0386 vs base rate | [−0.0616, −0.0148] | `NO_ADVANCE_CROSS_ASSET_BREADTH_HGBR_V1` |

All four families are `REJECTED_DEVELOPMENT_NO_SEALED`; all eight configurations are
`NOT_ELIGIBLE_REJECTED_DEVELOPMENT`.

What the four families have now separated:

- **Stage 1** failed on both coverage and direction — a substrate defect and a null signal at
  once.
- **Stage 2 funding** passed coverage at 0.99998 and failed on direction alone.
- **Stage 2 open interest** passed coverage at 0.9901 and failed on direction alone.
- **Stage 3 cross-asset breadth** passed coverage at 0.9984, on the largest sample and the
  widest source yet, and failed on direction with an interval that **excludes zero on the wrong
  side**.

Coverage has not explained a negative result in three consecutive families. No magnitude head in
the generation has beaten `ZERO_RETURN_MAGNITUDE`, and no configuration has beaten its matched
training-base-rate Brier. Stage 3 declared no magnitude at all, by design.

## The Stage-3 finding is qualitatively different and must not be mis-read

The three earlier families returned nulls: intervals straddling zero, no information either way.
Stage 3 did not. Over 43,572 paired records at 0.9984 coverage, both configurations are
reliably *worse* than the information-free `TRAINING_UP_BASE_RATE`, and both also miss matched
`ALWAYS_UP`, which coincides with the base rate at 0.5268 because the training majority declared
`UP` in all five folds.

Two observations are recorded so they are not rediscovered as if they were new evidence:

1. The 2020 fold dominates the pooled damage (−0.1611 linear, −0.1551 HGBR). It also has the
   shortest breadth-valid training portion (7,019 rows against 41,924 for 2024) and the most
   lopsided matched base rate (0.5807 `UP`). The fold was admitted on source availability before
   any result existed and may not be removed now.
2. Inverting a reliably-wrong signal is forbidden as a post-hoc rescue, and would in any case
   still have to clear the matched `ALWAYS_UP` floor that both configurations miss.

## No executor work is authorized by this file

There is no preregistered experiment to run. Specifically forbidden without a new
Research-Director-frozen design:

- any tuned descendant of any of the eight executed configurations;
- a third configuration in any closed family;
- inverting, negating or thresholding the cross-asset breadth signal;
- dropping, re-cutting or re-weighting the 2020 fold, or reconsidering the 180-day
  training-history rule in order to change it;
- combining breadth with the rejected Stage-1, settled-funding or open-interest features;
- importing any historical cross-sectional research result as predictive evidence;
- introducing a future-survival filter, a whole-sample participation threshold, or any
  market-cap, volume or survivorship weighting into the cross-section;
- acquiring or admitting basis, long/short ratios, liquidations, CFTC, macro, calendar, news,
  sentiment or on-chain data;
- repairing canonical hourly gaps or relaxing the Stage-1 contiguity rule;
- changing the frozen target, horizon, labels, folds, scorer, reliability bins, bootstrap
  parameters, MESI, alpha allocation or advancement semantics;
- expanding the prediction or trading universe beyond BTCUSDT;
- inverting or negating `PREVIOUS_24H_SIGN_PERSISTENCE`;
- any sealed or post-cutoff query.

Champion stays `NONE`. Real money stays `false`.

## Decisions the Research Director owns

1. **What a reliably-wrong signal means.** Stage 3 is the first interval in this generation that
   excludes zero. Whether that is evidence about breadth and BTC, or an artefact of one fold's
   short training window and lopsided base rate, is a design question that may only be settled by
   a new preregistered experiment — never by re-reading these two.
2. **Basis, or stop adding derivatives series.** Basis remains deferred rather than rejected. It
   is now the only declared Stage-2 series never tested.
3. **The 24h terminal target.** Eight rejections across price structure, carry, positioning
   quantity and cross-asset breadth is the strongest evidence yet that the frozen target may not
   be predictable from these families at this horizon. Revisiting horizon or target would open a
   new research generation rather than another family inside this one.
4. **Magnitude.** Stage 3 declared none, on the stated ground that no family has earned
   directional admission. Whether that deferral continues into the next family is a decision to
   restate explicitly rather than inherit.
5. **Generation disposition.** Whether `PREDICTIVE_RESEARCH_GENERATION_V1` continues into another
   Stage-3 family, pauses, or is recorded with an explicit disposition.

## Note for whoever writes the next package

The cross-asset source foundation is now admitted and reusable:
`data/manifests/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.json` with
`docs/contracts/PREDICTIVE_CROSS_ASSET_BREADTH_CONTEXT_V1.md`. Its substrate opens 2019-01-01,
which is what excluded fold 2019 here. Any future family on this source inherits the same
four-endpoint membership rule, the same minimum universe of thirty, the same 180-day
training-history rule and the same fold set unless those rules are reconsidered on their own
terms and before any result.

The point-in-time proof technique is also reusable: recomputing a feature vector from a panel
stripped to its required endpoint rows kills the future-survival filter, the whole-sample
participation threshold and the look-ahead question in one construction.

## Validation for any future package

Backend tests PASS; frontend validation PASS if touched; `check.py --no-data` PASS; ruff /
format / mypy PASS; deterministic result replay PASS with development data installed; exact
search-budget accounting; sealed queries 0; Champion `NONE`; real money `false`; clean tree;
commit and push to `main`; exact-head CI SUCCESS.
