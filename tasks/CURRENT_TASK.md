# CURRENT TASK — RESEARCH-DIRECTOR-REVIEW-STAGE-2-OPEN-INTEREST-CLOSURE

Status: AWAITING_RESEARCH_DIRECTOR_REVIEW_NO_EXECUTOR_WORK_AUTHORIZED

Predecessor: `PREDICTIVE-STAGE2-OPEN-INTEREST-V1` — executed, family disposition
`REJECTED_DEVELOPMENT_NO_SEALED`.

`PREDICTIVE_STAGE2_OPEN_INTEREST_MODEL_FAMILY_V1` is **closed**. Both predeclared
configurations were executed in one work package, the search budget is fully consumed, and
nothing is reserved.

## Where the predictive generation now stands

Six configurations across three information families have been executed on the frozen BTCUSDT
24h terminal target. None advanced.

| family | configuration | win rate | coverage | primary delta | 97.5% paired interval | classification |
| --- | --- | --- | --- | --- | --- | --- |
| Stage 1 internal | `INTERNAL_LINEAR_DUAL_HEAD_V1` | 0.4888 | 0.9357 | −0.0351 vs `ALWAYS_UP` | [−0.0608, −0.0080] | `NO_ADVANCE_INTERNAL_LINEAR_V1` |
| Stage 1 internal | `INTERNAL_HGBR_DUAL_HEAD_V1` | 0.4896 | 0.9357 | −0.0343 vs `ALWAYS_UP` | [−0.0575, −0.0100] | `NO_ADVANCE_INTERNAL_HGBR_V1` |
| Stage 2 funding | `FUNDING_LINEAR_DUAL_HEAD_V1` | 0.4855 | 0.99998 | −0.0093 vs base rate | [−0.0296, +0.0126] | `NO_ADVANCE_FUNDING_LINEAR_V1` |
| Stage 2 funding | `FUNDING_HGBR_DUAL_HEAD_V1` | 0.4941 | 0.99998 | −0.0006 vs base rate | [−0.0177, +0.0174] | `NO_ADVANCE_FUNDING_HGBR_V1` |
| Stage 2 open interest | `OPEN_INTEREST_LINEAR_DUAL_HEAD_V1` | 0.4846 | 0.9901 | −0.0241 vs `ALWAYS_UP` | [−0.0523, +0.0079] | `NO_ADVANCE_OPEN_INTEREST_LINEAR_V1` |
| Stage 2 open interest | `OPEN_INTEREST_HGBR_DUAL_HEAD_V1` | 0.5052 | 0.9901 | −0.0035 vs `ALWAYS_UP` | [−0.0326, +0.0298] | `NO_ADVANCE_OPEN_INTEREST_HGBR_V1` |

All three families are `REJECTED_DEVELOPMENT_NO_SEALED`; all six configurations are
`NOT_ELIGIBLE_REJECTED_DEVELOPMENT`.

What the three families have now separated:

- **Stage 1** failed on both coverage and direction — a substrate defect and a null signal at
  once.
- **Stage 2 funding** passed coverage at 0.99998 and failed on direction alone.
- **Stage 2 open interest** passed coverage at 0.9901 and failed on direction alone, on a
  source built from scratch under a fail-closed provenance regime.

Coverage is therefore no longer a candidate explanation for any negative result. No magnitude
head in the generation has beaten `ZERO_RETURN_MAGNITUDE`, and no configuration has beaten its
matched training-base-rate Brier.

## No executor work is authorized by this file

There is no preregistered experiment to run. Specifically forbidden without a new
Research-Director-frozen design:

- any tuned descendant of any of the six executed configurations;
- a third configuration in any closed family;
- combining open interest with the rejected Stage-1 or settled-funding features;
- acquiring or admitting basis, long/short ratios, top-trader ratios, liquidations, CFTC,
  macro, news, sentiment or on-chain data;
- repairing canonical hourly gaps or relaxing the Stage-1 contiguity rule;
- changing the frozen target, horizon, labels, folds, scorer, reliability bins, bootstrap
  parameters, MESI, alpha allocation or advancement semantics;
- expanding the asset universe beyond BTCUSDT;
- inverting or negating `PREVIOUS_24H_SIGN_PERSISTENCE`;
- any sealed or post-cutoff query.

Champion stays `NONE`. Real money stays `false`.

## Decisions the Research Director owns

1. **Basis, or stop adding Stage-2 series.** Basis is the remaining declared Stage-2
   derivatives series. Two of three admitted families have now returned nulls against matched
   `ALWAYS_UP` with intervals straddling zero; whether a third is worth its multiplicity is a
   judgement about expected information, not about the two results just observed.
2. **The 24h terminal target.** Six rejections across price structure, carry and positioning
   quantity is the strongest evidence yet that the frozen target may not be predictable from
   these families at this horizon. Revisiting horizon or target would open a new research
   generation rather than another family inside this one.
3. **Substrate debt.** Whether to pay down the Stage-1 canonical hourly gap defect under an
   independent protocol. Stage 2 has now twice shown the defect was never the reason the
   directional evidence failed, which weakens the case for treating it as a research priority.
4. **Generation disposition.** Whether `PREDICTIVE_RESEARCH_GENERATION_V1` continues into
   Stage 3, pauses, or is recorded with an explicit disposition.

## Note for whoever writes the next package

The open-interest source foundation is now admitted and reusable:
`data/manifests/BTCUSDT-USDM-OPEN-INTEREST-DEV-v1.json` with
`docs/contracts/PREDICTIVE_OPEN_INTEREST_STRUCTURE_V1.md`. Its archive history begins
2020-09-01, which is what excluded folds 2020 and 2021 here. Any future family on this source
inherits the same 180-day training-history rule and will face the same fold set unless the
rule itself is reconsidered on its own terms.

## Validation for any future package

Backend tests PASS; frontend validation PASS if touched; `check.py --no-data` PASS; ruff /
format / mypy PASS; deterministic result replay PASS with development data installed; exact
search-budget accounting; sealed queries 0; Champion `NONE`; real money `false`; clean tree;
commit and push to `main`; exact-head CI SUCCESS.
