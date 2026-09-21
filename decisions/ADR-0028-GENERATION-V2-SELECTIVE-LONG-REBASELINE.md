# ADR-0028 — Generation V1 closes with no directional admission; Generation V2 tests selective LONG

Status: ACCEPTED (2026-09-21)

Closes `PREDICTIVE_RESEARCH_GENERATION_V1` and opens `PREDICTIVE_RESEARCH_GENERATION_V2`.
Builds on [ADR-0026](ADR-0026-PREDICTION-FIRST-RESEARCH-OBJECTIVE.md) and
[ADR-0027](ADR-0027-BASELINE-PROBABILITY-SEMANTICS-AND-METRIC-APPLICABILITY.md), both of which
remain in force. It rewrites no result, reopens no experiment and weakens no rule.

Freezes `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V2.md` (Amendment B1) and
`docs/contracts/ALFRED_OBSERVATION_DATE_GUARD_V1.md`. No predictive model is fitted in this
decision and no market prediction is produced.

## Context

### What Generation V1 actually tested

Five genuinely executed information families were tested against the frozen BTCUSDT 24h
terminal direction target:

| family | configurations | disposition |
| --- | --- | --- |
| internal market structure | 2 | rejected in development |
| settled funding | 2 | rejected in development |
| open interest | 2 | rejected in development |
| cross-asset breadth | 2 | rejected in development |
| strict point-in-time macro release state | 2 | rejected in development |

Ten predictive configurations were consumed. None advanced. None is sealed-eligible. Sealed
queries remain 0, Champion remains `NONE`, real money remains `false`.

`PREDICTIVE-STAGE3-MACRO-VINTAGE-V1` is a **source block**, not a market-result family: it
executed 0 fits and observed 0 outer predictions, and it must never be counted among the ten
executed configurations.

### What that does and does not establish

It does **not** establish that BTCUSDT is unpredictable. It establishes something narrower and
more useful: the tested *always-declare* 24h formulations failed to add credible directional
information over their frozen controls. Four of the five families passed coverage cleanly —
three at essentially full coverage and the macro family at 1.00000 on every included fold — so
substrate quality explains none of it.

Generation V1 forced nearly every eligible hour into a directional declaration. That is a
sound test of universal hourly classification. It is not the product the Owner asked for.

### The macro residual source defect

`PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1` recorded
`MACRO_RELEASE_STATE_FUTURE_DATED_OBSERVATION_V1`: twenty admitted `VIXCLS` rows carry an
`observation_date` later than their own `vintage_start`, exposing a future-dated level at 1.43%
of evaluation instants and 0.87% of training instants.

## Decision

### 1. Generation V1 closes

`PREDICTIVE_RESEARCH_GENERATION_V1` is closed with disposition
`CLOSED_NO_DIRECTIONAL_ADMISSION_NO_SEALED`.

No V1 result may be rescued by inversion, thresholding, fold removal, hyperparameter search,
feature pruning or re-execution. Every V1 result file, source audit, admission, checkpoint
report and residual record stays byte-identical with its recorded disposition.

### 2. The macro residual ruling

The committed negative macro result **stands as recorded**. The defect's direction is the whole
argument: a lookahead can only make a candidate look better, and both macro configurations were
rejected by wide margins (pooled enrichment-equivalent deltas of −0.0446 and −0.0457 with 97.5%
intervals entirely below zero). A defect that could only have flattered the candidate cannot
have manufactured that.

Neither macro result is re-run or rewritten. Instead the wording gap is closed prospectively by
`docs/contracts/ALFRED_OBSERVATION_DATE_GUARD_V1.md`, which requires, at decision timestamp `T`,
both `availability_time <= T` **and** `observation_date <= UTC_date(T)`. Later vintage revisions
remain usable only from their own availability time. Current-revised substitution, interpolation
and nearest-future substitution remain forbidden. The old macro contracts and every historical
artifact are untouched, and the exhausted macro source-redesign budget is not revived.

### 3. Generation V2 changes the evaluation question, not the target

The Owner wants `LONG` when the evidence is strong enough, `NO_TRADE` otherwise, a probability
with an empirical calibration meaning, and — later — a separate estimate of movement strength.

Generation V2 therefore tests **selective directional prediction** rather than universal hourly
classification. The change is preregistered now, after V1 closure, for candidates that do not
yet exist, and is never applied retrospectively to a V1 model score.

The target, cadence and horizon are deliberately unchanged: BTCUSDT spot, each completed UTC 1h
bar, 24h terminal, `r_24h = log(close[T+24h] / close[T])`. Changing selectivity and the horizon
at once would confound the two.

### 4. Frozen action policy

Every candidate emits a calibrated `p_up = P(r_24h > 0)` at every feature-valid eligible
timestamp. `LONG` iff `p_up >= 0.60`, otherwise `NO_TRADE`; exactly 0.60 acts `LONG`. A model
that cannot emit calibrated probabilities may not participate. `SHORT` is not authorized.

0.60 is a product/scientific threshold chosen before any Generation V2 candidate ran. It may
never be tuned on development results, and a candidate may not carry its own threshold.

### 5. Primary metric and enrichment control

`SELECTIVE_LONG_WIN_RATE = UP truths / actionable LONG predictions`, never reported without
actionable `N`, action coverage, chronological distribution, interval and calibration.

The primary control is `FULL_FOLD_UP_RATE`: the UP frequency over every directionally scorable
eligible timestamp in the same fold, computed without candidate action selection. The primary
effect is `SELECTIVE_LONG_WIN_RATE - FULL_FOLD_UP_RATE`.

This is the substantive scientific choice. "Did the LONGs win above 50%" is answerable by a
rising market; "did the model act on a better-than-ambient set of hours" is not. The control
may use evaluation-fold truth for scoring only, and is never visible to fitting, calibration,
threshold choice or fold selection.

### 6. Advancement requires all ten conditions

Coverage and count floors (>= 0.02 pooled and >= 0.005 per-fold action coverage; >= 500 pooled
and >= 30 per-fold actionable LONGs) come first, so a cosmetically perfect win rate over a
handful of cherry-picked hours fails before its win rate is considered. Directional enrichment
follows (>= 0.60 pooled selective win rate, >= +0.05 pooled enrichment, a dependence-aware
interval lower bound above zero, and non-negative enrichment in at least two thirds of folds).
Calibration closes it (full-probability Brier no worse than the matched training base rate, and
action calibration gap <= 0.05).

These thresholds may not be weakened after any V2 candidate result.

### 7. Dependence-aware inference

Fold-stratified moving-block bootstrap, 48h blocks, 10,000 replicates, a fixed seed declared per
family before execution, blocks never crossing a fold boundary, and — the point — both the
selected LONG win rate and the same-fold full-universe UP rate recomputed on every replicate so
the enrichment interval is genuinely paired. A replicate that draws no actionable LONG is
discarded and counted; above a 1% discard share the interval is `UNSTABLE_RESAMPLE_SUPPORT` and
the interval condition fails closed. Familywise alpha 0.05, Bonferroni over the declared family
size.

### 8. Magnitude stays deferred

`MAGNITUDE_STATUS = DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`. Every executed V1 magnitude
head failed to beat `ZERO_RETURN_MAGNITUDE`; searching for magnitude before a directional signal
exists spends search burden without evidence. A separate preregistered magnitude head is
required before any user-facing "strength 0–100" is shown.

### 9. Search memory carries forward

All V1 family dispositions, all ten executed configuration results, all source blocks, the
adaptive-search and search-burden records, the Stage-1 substrate debt, basis deferred, the
exhausted macro source-redesign budget, the ban on cross-asset inversion, and sealed queries 0.

New V2 hypotheses receive new IDs and new search budgets. They may reuse causal source
infrastructure, but no rejected V1 result becomes evidence merely because the scorer changed.

## Consequences

- A V2 candidate can now fail for a reason V1 had no way to express: acting rarely, on hours no
  better than the ones it declined. That is the intended tightening.
- The coverage and count floors make the "abstain until the sample is flattering" failure mode
  structurally unavailable, which is the failure mode selective prediction invites.
- The enrichment control means a bull market cannot be mistaken for skill.
- The scorer is implemented and synthetically tested in this checkpoint, before any candidate
  exists, so the first V2 candidate meets a scorer whose behaviour is already known.
- Nothing here makes any predictor easier to pass. Every V1 rigour rule remains in force.

## Boundaries

No model fitted. No market prediction produced. No experiment created. Sealed queries 0,
post-cutoff access 0, Champion `NONE`, real money `false`. No V1 artifact modified.
