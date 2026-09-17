# Predictive Stage 2 — settled funding structure V1

The first Stage-2 information family of `PREDICTIVE_RESEARCH_GENERATION_V1`.
`PREDICTIVE_STAGE2_SETTLED_FUNDING_FAMILY_V1` tested `H-PRED-FUND-001` on two preregistered
configurations over the frozen 2020–2024 outer folds.

Family disposition: **`REJECTED_DEVELOPMENT_NO_SEALED`**. Both configurations failed five of
seven predeclared gates; neither is sealed-eligible. Full numbers:
`reports/research/PREDICTIVE-STAGE2-SETTLED-FUNDING-V1.md` and its JSON; the immutable
records are `research/experiments/EXP-PRED-003-…` and `EXP-PRED-004-…`.

## Stage-1 closure, recorded first

The Research Director's decisions are in `state/current_state.json`
(`predictive_stage1_disposition`) and in this checkpoint's frozen records:

- `PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1` is `REJECTED_DEVELOPMENT_NO_SEALED`;
- both Stage-1 configurations are `NOT_ELIGIBLE_REJECTED_DEVELOPMENT`;
- the canonical hourly gaps were **not** repaired and the 169-bar contiguity rule was **not**
  relaxed — the defect is recorded as `DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH`.

Neither Stage-1 result was touched. The rejection covers the defined two-configuration
family, not the proposition that all internal BTCUSDT information is useless.

## The design was frozen before the first Stage-2 number existed

Search plan, both preregistrations, the new predictive contract and the pre-execution
admission were committed in `080c6ea`, one commit before either configuration ran. The
admission hashes the plan, both preregistrations, the contract, the canonical funding
artifact and eleven implementation files. Admission identity
`562d2db613df5bb5b3d7a33416d55f3043ea184934e996c009fe89ec73d2adac`.

Both configurations were executed in this single work package, as preregistered, with no
result-dependent early stop and no post-hoc winner selection.

## Source and point-in-time semantics

`BTCUSDT-USDM-FUNDING-DEV-v1`: 5,819 settled records, 2019-09-10 to 2024-12-31, credential-free
Binance USD-M public market data, loaded through the existing integrity tooling so the
manifest hash, the column set and the development cutoff are all verified. Only `funding_time`
and `funding_rate` are read.

A settlement is available at `T` only when `funding_time < T` exactly; one stamped at `T` is
not. The vector needs the last nine strictly-prior settlements with every consecutive gap
inside the chain at most 8h + 60s. Nothing is interpolated or forward filled.

A new contract, `PREDICTIVE_SETTLED_FUNDING_STRUCTURE_V1`, governs this; the historical
`PERPETUAL_FUNDING_CONTEXT_V1` is untouched and its results are not evidence here. The family
deliberately does not inherit the rejected Stage-1 contiguity rule.

46,361 of 64,323 admissible labels carry a funding vector. All 17,962 unavailable ones are
`INSUFFICIENT_PRIOR_SETTLEMENTS` — they precede the source's September 2019 start and lie
entirely outside the 2020–2024 evaluation folds. `SETTLEMENT_GAP_TOO_LARGE` 0.

**Coverage was not the problem this time.** Pooled source coverage is 0.99998 over 43,642
eligible timestamps, and every fold is ≥ 0.99989. Both coverage gates passed. Unlike Stage 1,
the failure here is purely directional.

## The result

| | linear | HGBR |
| --- | --- | --- |
| win rate | 0.4855 | 0.4941 |
| coverage | 0.99998 | 0.99998 |
| matched control win rate | 0.4948 | 0.4948 |
| primary delta | −0.0093 | −0.0006 |
| 97.5% paired interval | [−0.0296, +0.0126] | [−0.0177, +0.0174] |
| matched `ALWAYS_UP` | 0.5270 | 0.5270 |
| secondary delta | −0.0415 | −0.0329 |
| Brier | 0.2584 | 0.2618 |
| control Brier | 0.2546 | 0.2546 |
| magnitude MAE | 2.2938 pp | 2.4702 pp |

Both primary intervals straddle zero, so this is a null result against the information-free
control rather than evidence of harm against it. Against `ALWAYS_UP` both are clearly below.
Both are worse-calibrated than a constant training base rate, and the boosted magnitude head
is worse than predicting zero (`ZERO_RETURN_MAGNITUDE` 2.2530 pp).

Per-fold primary deltas: linear +0.0099, −0.0002, +0.0030, −0.0528, −0.0062; HGBR +0.0134,
+0.0000, +0.0032, −0.0155, −0.0043. Two of five and three of five non-negative, against a
required four.

Seven gates, both configurations: coverage conditions 1 and 2 **pass**; conditions 3
(MESI), 4 (interval above zero), 5 (beat matched `ALWAYS_UP`), 6 (4 of 5 folds) and 7
(Brier at most the control's) **fail**.

## What the 2020 fold actually shows

The only fold where either candidate clearly beat the control is 2020, and it is a control
artifact, not a candidate success. The matched `TRAINING_UP_BASE_RATE` is refit per fold on
the source-eligible training rows, and in 2020 that is only 2,580 directional labels from
September–December 2019, where `p_up` was 0.4136. Amendment A1 therefore made it declare
`DOWN` for the whole of 2020 — a year in which `ALWAYS_UP` scored 0.5807. The control scored
0.4193 and both candidates edged past it while themselves scoring 0.43.

This is why the design carries a second, absolute reference. Gate 5 exists precisely so that
beating a badly-fitted information-free control cannot be mistaken for skill, and it is one
of the five gates both candidates failed.

## What was proven rather than asserted

Point-in-time semantics are proven on synthetic timelines: a settlement stamped exactly at
`T` is excluded and one second later enters; the causal surface is exactly the nine
strictly-prior settlements; mutating every later settlement cannot move a feature; the five
features reproduce hand-computed fixtures; fewer than nine settlements and an over-long gap
inside the chain each abstain with their own typed reason; the tolerance is exactly 8h + 60s
at both boundaries; a gap *before* the window never invalidates it; the feature names share
nothing with the Stage-1 set.

Fitting separation is proven for both estimators: perturbing rows on the calibration side
leaves the base model bit-identical while the Platt map moves, and perturbing rows inside the
48h embargo moves neither. Both estimators are deterministic under the fixed seed.

The gate is proven to bind: a high win rate at 0.20 coverage cannot advance; a candidate that
beats the training base rate but not matched `ALWAYS_UP` cannot advance; a candidate whose
Brier is worse than the control's cannot advance. A tamper test confirms the validator rejects
a result whose classification was edited after the fact — all seven conditions are recomputed
from the reported numbers.

## Validation and accounting

Backend tests, `check.py --no-data`, ruff, format, mypy and frontend validation all pass. Both
committed experiment results replay byte-identically against the installed data.

Stage-2 budget: 2 of 2 configurations consumed, 0 remaining. Model fits 30 (15 per
configuration), plus 5 per-fold matched-control base rates, which are counted base rates and
not model fits. Sealed queries 0. No additional information family — no open interest, basis,
position ratios, CFTC, macro, news or on-chain data was acquired or admitted. No post-cutoff
data. No Stage-1 rescue and no canonical hourly gap repair. `PREDICTIVE-BASELINES-V1`,
`PREDICTIVE-INTERNAL-STRUCTURE-V1` and `PREDICTIVE-INTERNAL-NONLINEAR-V1` results unchanged.
Champion `NONE`, real money `false`.

## Next

Neither configuration advanced, so no sealed query, no Champion, no prospective observer and
no tuned descendant was created. `tasks/CURRENT_TASK.md` becomes
`RESEARCH-DIRECTOR-REVIEW-STAGE-2-CLOSURE` and authorizes no executor work.

Two families have now been tested and rejected on the frozen target: internal price/volume
structure and settled perpetual funding. The open decisions — whether to admit a further
Stage-2 series such as open interest or basis, whether to pay down the Stage-1 substrate debt
under its own protocol, and whether the 24h terminal target itself should be revisited — are
the Research Director's, and none of them may be framed as a rescue of the four executed
experiments.
