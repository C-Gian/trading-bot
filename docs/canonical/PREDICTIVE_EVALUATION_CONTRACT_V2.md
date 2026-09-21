# Predictive evaluation contract V2 — selective LONG

Canonical. Governs `PREDICTIVE_RESEARCH_GENERATION_V2` only. See
[ADR-0028](../../decisions/ADR-0028-GENERATION-V2-SELECTIVE-LONG-REBASELINE.md),
[the Constitution](../../governance/SCIENTIFIC_CONSTITUTION.md) and the Generation V1
contract it succeeds, [`PREDICTIVE_EVALUATION_CONTRACT_V1`](PREDICTIVE_EVALUATION_CONTRACT_V1.md).

This document is **Amendment B1**: it freezes how a Generation V2 prediction is defined,
scored and reported, before the first Generation V2 candidate exists. Like V1 it may be
extended by a later canonical version, never weakened, and never after a result it would
govern has been observed.

It authorizes no experiment, trains nothing, and fits nothing. Machine-readable current state
lives only in `state/current_state.json`; the executable freeze lives in
`backend/app/predictive/selective_long.py`.

## 0. What carries over unchanged from V1

Generation V1 is closed, not deleted. Its results stand exactly as recorded, and this contract
is **not** applied retrospectively to any V1 model score.

Carried forward verbatim from `PREDICTIVE_EVALUATION_CONTRACT_V1`:

- §1 frozen predictive target, label admissibility and eligible-timestamp definition;
- §2 canonical prediction fields, and the rule that a raw model score is never a probability;
- §6 signed magnitude-match diagnostic, for when magnitude returns;
- §7 purge/embargo and the ban on standard random K-fold;
- §8 layer separation, and `EUR 5,000` as a display-only scenario assumption;
- §9 product-output rules and §10 prohibitions;
- the fixed reliability bins `[0.0,0.1), [0.1,0.2), …, [0.9,1.0]`, reused without change.

What V2 replaces is the scoring question in V1 §3–§5, and only that.

## 1. Why the question changes

Generation V1 forced nearly every eligible hour into a directional declaration. That is a
sound test of universal hourly classification, and five orthogonal information families failed
it. It is not, however, the product the Owner asked for: a bot that goes `LONG` when the
evidence is strong enough and otherwise stays out.

Generation V2 therefore tests **selective directional prediction**. The change is
preregistered here, after V1 closure, for candidates that do not yet exist.

V1's closure does not establish that BTC is unpredictable. It establishes that the tested
always-declare 24h formulations added no credible directional information over their frozen
controls.

## 2. Target and action semantics

| Item | Value |
| --- | --- |
| Market | BTCUSDT spot, sole prediction target |
| Decision cadence | each completed UTC 1h bar |
| Primary forecast horizon | 24 hours, terminal |
| Prediction target | `r_24h = log(close[T + 24h] / close[T])` |
| Actions | `LONG`, `NO_TRADE` |
| Short | forbidden |
| Real money | forbidden |

Truth at decision timestamp `T`:

- `UP` when `r_24h > 0`;
- `DOWN` when `r_24h < 0`;
- `NEUTRAL` when `r_24h == 0` exactly.

The horizon is deliberately unchanged. Generation V2 alters selectivity and action semantics
first; it does not simultaneously search a new horizon.

Every candidate must emit a calibrated `p_up = P(r_24h > 0)` at every feature-valid eligible
timestamp. A model that cannot emit calibrated probabilities may not participate.

**Frozen action policy**

```
LONG      iff calibrated p_up >= 0.60
NO_TRADE  otherwise
```

Exactly `0.60` acts `LONG`. The threshold is a product/scientific choice made before any
Generation V2 candidate was run. It may never be tuned, swept or re-chosen on development
results, and a candidate may not carry its own threshold.

## 3. Counting rules

- An **eligible decision timestamp** is one whose 24h forward label is admissible, exactly as
  in V1 §1.
- A row is **feature-valid** when the candidate produced a `p_up` for it. A feature-invalid
  row is excluded from every rate and **counted**; it is never imputed and never silently
  dropped.
- A **LONG action** is a feature-valid row with `p_up >= 0.60`.
- An **actionable LONG prediction** is a LONG action whose realized truth is not `NEUTRAL`.
- A `NEUTRAL` truth is counted explicitly and is excluded from the win numerator *and* from
  every directional denominator. It is never counted as a win.
- **Directionally scorable** means the realized truth is `UP` or `DOWN`.

## 4. Primary metric

```
SELECTIVE_LONG_WIN_RATE = UP truths among actionable LONGs / actionable LONG predictions
action_coverage         = LONG actions / feature-valid eligible timestamps
```

A selective win rate may never be reported, quoted or interpreted without, in the same view:

- actionable `N`;
- action coverage;
- the chronological distribution by fold;
- the dependence-aware interval of §6;
- the calibration diagnostics of §5.

## 5. Primary control and the enrichment effect

Beating 50% is not the question. The question is whether the model **enriches** for UP
outcomes relative to the hours it declined to act on.

```
FULL_FOLD_UP_RATE = UP / (UP + DOWN) over every directionally scorable
                    eligible timestamp in the same evaluation fold
primary effect    = SELECTIVE_LONG_WIN_RATE - FULL_FOLD_UP_RATE
```

The control never uses candidate action selection, candidate feature validity, or any
candidate score. Evaluation-fold truth enters it **for scoring only**: it is never visible to
fitting, calibration, threshold choice or fold selection. Making it visible to any of those
would be a selection/evaluation separation breach under the Constitution.

A secondary diagnostic, `FEATURE_VALID_FOLD_UP_RATE`, is reported per fold over the candidate's
feature-valid scorable rows, so an enrichment that is really a source-coverage artifact is
visible rather than hidden.

Secondary references, each reported and none of them the primary effect:

- `TRAINING_UP_BASE_RATE` — training-only, per fold, as in V1 §5.1;
- `ALWAYS_UP` — full-fold win rate;
- `PREVIOUS_24H_SIGN_PERSISTENCE` — descriptive only, never inverted.

**Calibration.** Two distinct quantities are scored and neither substitutes for the other:

1. **Full-probability Brier** over all feature-valid, directionally scorable outer rows, of
   `p_up` against the UP indicator. Its matched control is the fold's training-only `p_up`
   used as a constant probability of UP. This is `P(UP)`, not V1's
   `P(declared direction correct)`; the two coincide only when the declared direction is `UP`,
   and conflating them would score the control against a claim it never made.
2. **Action calibration** among actionable LONGs:
   `abs(mean_predicted_p_up - empirical_LONG_win_rate)`, reported with the fixed V1 reliability
   bins over the actionable LONG probabilities.

## 6. Dependence-aware inference

Consecutive 24h labels at a 1h cadence overlap by up to 23 hours, so independence is false by
construction.

Frozen:

- fold-stratified moving-block bootstrap;
- block length 48 hours;
- 10,000 replicates;
- a fixed integer seed declared **per family before execution**, never chosen after a result;
- blocks are drawn independently inside each fold and never cross a fold boundary;
- every replicate recomputes **both** the selected LONG win rate and the same-fold
  full-universe UP rate on the resampled slots, and the enrichment is their paired difference;
- an abstention, a `NO_TRADE`, a feature-invalid row or a canonical gap keeps its hour slot and
  contributes no record, so nothing is pulled into adjacency by resampling;
- a replicate that draws no actionable LONG at all has no selective win rate; it is
  **discarded and counted**, never imputed. If more than 1% of replicates are discarded the
  interval is classified `UNSTABLE_RESAMPLE_SUPPORT` and condition 7 of §7 fails closed;
- familywise alpha is 0.05, Bonferroni-corrected over the declared family size, and the
  per-configuration interval mass is `1 - alpha/family_size`;
- a naive independence-assuming interval may be reported only when explicitly labelled as an
  optimistic reference, never as the headline.

## 7. Advancement gate

A Generation V2 candidate may advance development only if **all ten** conditions hold. No
secondary metric ever rescues a failed condition, and these thresholds may not be weakened
after any V2 candidate result is observed.

| # | Condition | Threshold |
| --- | --- | --- |
| 1 | pooled LONG action coverage | >= 0.02 |
| 2 | every included fold LONG action coverage | >= 0.005 |
| 3 | pooled actionable LONG count | >= 500 |
| 4 | every included fold actionable LONG count | >= 30 |
| 5 | pooled selective LONG win rate | >= 0.60 |
| 6 | pooled enrichment over `FULL_FOLD_UP_RATE` | >= +0.05 absolute |
| 7 | lower bound of the dependence-aware enrichment interval | > 0 |
| 8 | folds with non-negative enrichment | >= `ceil(2 * N_folds / 3)` |
| 9 | full-probability Brier over all feature-valid outer rows | <= matched `TRAINING_UP_BASE_RATE` Brier |
| 10 | `abs(mean_predicted_p_up - empirical_LONG_win_rate)` among actionable LONGs | <= 0.05 |

Conditions 1–4 prevent a cosmetically high win rate produced by a tiny number of cherry-picked
actions. Conditions 5–8 test actual directional enrichment. Conditions 9–10 require the
displayed probabilities to mean what they claim.

Advancing development is not sealed eligibility, is not a Champion, and is not permission for
capital of any kind.

## 8. Magnitude

`MAGNITUDE_STATUS = DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`.

Magnitude remains a required product goal and is **not** a Generation V2 advancement head.
Every executed V1 magnitude head failed to beat `ZERO_RETURN_MAGNITUDE`, and searching for
magnitude before a directional signal exists would spend search burden without evidence.

Once a V2 directional candidate advances development, the next research package must
preregister a separate magnitude/strength head before any user-facing "strength 0–100" is
shown. Until then the product surface shows no strength number.

## 9. Search memory

Generation V2 is not a reset of scientific memory. Carried forward explicitly: every V1 family
disposition, all ten executed V1 configuration results, every source block, the
adaptive-search and search-burden records, the Stage-1 substrate debt, basis deferred, the
exhausted macro source-redesign budget, the ban on cross-asset inversion, and sealed
queries 0.

New V2 hypotheses receive new IDs and new search budgets. They may reuse causal source
infrastructure, but **no rejected V1 result becomes evidence merely because the scorer
changed**, and no V1 result may be rescued by inversion, thresholding, fold removal,
hyperparameter search, feature pruning or re-execution.

All future ALFRED use is additionally bound by
[`ALFRED_OBSERVATION_DATE_GUARD_V1`](../contracts/ALFRED_OBSERVATION_DATE_GUARD_V1.md).

## 10. What this contract forbids

- Tuning, sweeping or re-choosing the 0.60 action threshold on development results.
- Reporting a selective win rate without actionable `N`, action coverage, fold distribution,
  interval and calibration.
- Letting the `FULL_FOLD_UP_RATE` control reach fitting, calibration, thresholding or fold
  selection.
- Weakening any §7 threshold after a candidate result is observed.
- Presenting an uncalibrated score as a probability, or strength as a probability.
- Declaring a magnitude head before a directional candidate advances.
- Re-scoring, rescuing or reinterpreting a Generation V1 result under these semantics.
- `SHORT`, leverage, sealed or post-cutoff data, a Champion, or real money.
