# Predictive Stage 2 — open interest V1

The second Stage-2 information family of `PREDICTIVE_RESEARCH_GENERATION_V1`:
`PREDICTIVE_STAGE2_OPEN_INTEREST_MODEL_FAMILY_V1`, testing whether the **quantity** of
leveraged BTCUSDT perpetual positioning carries 24h directional information.

Family disposition: **`REJECTED_DEVELOPMENT_NO_SEALED`**. Both configurations failed four or
five of seven predeclared gates; neither is sealed-eligible. Full numbers:
`reports/research/PREDICTIVE-STAGE2-OPEN-INTEREST-V1.md` and its JSON; the immutable records
are `research/experiments/EXP-PRED-005-…` and `EXP-PRED-006-…`.

## Research Director decisions, recorded before execution

`PREDICTIVE_RESEARCH_GENERATION_V1` continues; four negative configurations were not treated
as a reason to change the frozen 24h target, and a target change is deferred because it would
create a new research generation. The Stage-1 canonical-hourly gap debt remains
`DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH` — no gaps were repaired and the 169-bar rule was
not relaxed. Open interest was admitted ahead of basis because it measures the quantity of
leveraged exposure, whereas settled funding already tested a price/carry channel. Basis was
not authorized. Both rejected families keep their results, their disposition and their lack
of sealed eligibility.

## The source had to be built, and it was built fail-closed

The repository had no admitted historical open-interest source. The only class accepted was
the official Binance public data archive: `data.binance.vision`,
`futures/um/daily/metrics/BTCUSDT`, credential-free. **1,583 daily objects** from 2020-09-01
to 2024-12-31, every one downloaded with its own `.CHECKSUM` and verified against it before
parsing, with the archive's exact CSV header enforced so an upstream schema change would fail
the parse rather than shift a column. No third-party vendor, no scrape, no mirror, no REST
snapshot window, no backfill.

Only two fields are admitted: `create_time` and `sum_open_interest`.
`sum_open_interest_value` is excluded because notional mechanically embeds BTC price, and
every long/short, top-trader and taker ratio column is excluded, so the family stays
interpretable as positioning quantity.

One upstream quirk had to be handled rather than ignored: some early daily objects emit every
record **twice, byte-identically**. Exact repetitions are collapsed under a declared policy
and counted (75,255); two different quantities at one timestamp would abort the acquisition,
and none occurred. The result is 455,273 records on a strict 5-minute grid, 631 missing of
455,904 across 155 gaps, 0 duplicates, 0 post-cutoff records.

## Point-in-time semantics, with the residual assumption stated

At an hourly decision instant `T` the OI state is the latest record with `create_time < T` —
a record stamped exactly `T` is unavailable — and it must be no older than ten minutes. No
interpolation, no forward fill.

The archive documents the measurement timestamp but not a separate publication lag. Because
the cadence is five minutes and the rule is strictly prior, the newest usable record is
normally stamped `T-5m`, so a look-ahead would require the archive's publication lag to exceed
five minutes. That residual assumption is recorded in the contract, in the source audit and in
both preregistrations rather than hidden.

## The pre-result gates decided the fold set

Provenance, semantics and the five-minute cadence gate all passed. The coverage gate then
chose the folds from source quality alone — no return value and no candidate prediction
entered the choice:

| fold | eligible | OI coverage | prior source history | included |
| --- | --- | --- | --- | --- |
| 2020 | 8,713 | 0.3206 | 0 days | no |
| 2021 | 8,699 | 0.9768 | 122 days | no |
| 2022 | 8,737 | 0.9961 | 487 days | yes |
| 2023 | 8,733 | 0.9943 | 852 days | yes |
| 2024 | 8,760 | 0.9800 | 1,217 days | yes |

2020 fails on both coverage and history; 2021 fails only the 180-day training-history rule,
with 122 days. Three folds and 26,230 eligible timestamps survive — both exactly at the
declared minimum, so the checkpoint proceeded rather than blocking. `N = 3` fixes the
two-thirds rule at 2 of 3.

**Coverage was not the confound.** Pooled candidate coverage is 0.9901 and every included fold
clears 0.90, so both coverage gates passed and the failure is directional.

## The result

| | linear | HGBR |
| --- | --- | --- |
| win rate | 0.4846 | 0.5052 |
| coverage | 0.9901 | 0.9901 |
| matched `ALWAYS_UP` | 0.5087 | 0.5087 |
| primary delta | −0.0241 | −0.0035 |
| 97.5% paired interval | [−0.0523, +0.0079] | [−0.0326, +0.0298] |
| matched base-rate win rate | 0.5087 | 0.5087 |
| Brier | 0.2519 | 0.2514 |
| base-rate Brier | 0.2514 | 0.2514 |
| magnitude MAE | 1.9358 pp | 2.0172 pp |

Both primary intervals straddle zero, so this is a null result against matched `ALWAYS_UP`
rather than evidence of harm. Neither candidate reached the matched base-rate win rate — the
training majority declared `UP` in all three folds, so that control and `ALWAYS_UP` coincide
at 0.5087 — and neither beat the control's Brier. The magnitude heads remain worse than
predicting zero: `ZERO_RETURN_MAGNITUDE` scores 1.9222 pp on the same universe, against
1.9358 pp for the linear head and 2.0172 pp for the boosted one. The linear head is the
closest any predictive magnitude head in this generation has come to the zero baseline, and
it is still behind it.

Per-fold deltas versus `ALWAYS_UP`: linear +0.0055, −0.0536, −0.0243; HGBR +0.0339, −0.0536,
+0.0091. The linear configuration fails the two-thirds rule with 1 of 3; the boosted one
passes that condition with 2 of 3 and still fails four others.

Failed conditions, both configurations: the MESI, the interval lower bound, the base-rate win
rate and the base-rate Brier. The linear configuration additionally fails the two-thirds fold
rule.

## What was proven rather than asserted

Point-in-time semantics are proven on synthetic 5-minute timelines: a record stamped exactly
at `T` is excluded and one second later enters; a state older than ten minutes is unavailable
at exactly the boundary and one second past it; no record at or after `T` can move a feature;
a record older than the 24h window cannot move anything; the six features reproduce
hand-computed fixtures on a geometric series, including the declared `0.0` for a zero
dispersion; a missing hour and a non-positive state each abstain with their own typed reason;
feature availability depends on the source timeline alone and cannot see a label; the official
schema and the `BTCUSDT` symbol are enforced when parsing, and the notional column never
reaches the admitted rows.

The gate is proven to bind: a high win rate at 0.20 coverage cannot advance; beating a weak
training-majority control while missing matched `ALWAYS_UP` cannot advance; a worse Brier than
the control cannot advance. Both estimators are deterministic under the frozen settings, and
the committed results replay byte-identically.

One implementation defect was found and fixed **before** the source audit and before any
result: the first draft reused the settled-funding head classes, which validate against the
funding feature width of five, and would have rejected the six open-interest features. It was
caught by the family's own tests.

## Validation and accounting

Backend tests, `check.py --no-data`, ruff, format, mypy and frontend validation all pass. Both
committed experiment results replay byte-identically against the installed data.

Family budget: 2 of 2 configurations consumed, 0 remaining. Model fits 30 (15 per
configuration), plus 3 per-fold base-rate controls, which are counted base rates and not model
fits. Sealed queries 0. No asset-universe expansion, no basis, long/short, CFTC, macro, news
or on-chain data, no combination with the rejected Stage-1 or funding features, no Stage-1
substrate repair, no post-cutoff data. All four prior predictive experiment results are
unchanged. Champion `NONE`, real money `false`.

## Next

Six configurations across three information families have now been rejected on the frozen 24h
target: internal price/volume structure, settled funding, and open interest. `tasks/CURRENT_TASK.md`
becomes `RESEARCH-DIRECTOR-REVIEW-STAGE-2-OPEN-INTEREST-CLOSURE` and authorizes no executor work.

Worth the Research Director's attention: the 2023 fold is the worst for both configurations
(−0.0536 each), and the two configurations disagree most where they differ from the baseline,
which is the signature of noise rather than of a weak shared signal. Whether to admit basis as
the third Stage-2 series, to pay down the Stage-1 substrate debt under its own protocol, or to
reconsider the 24h terminal target itself, are decisions that may not be framed as a rescue of
any of the six executed experiments.
