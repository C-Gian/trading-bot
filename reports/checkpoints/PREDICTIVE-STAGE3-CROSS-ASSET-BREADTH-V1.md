# Predictive Stage 3 — cross-asset breadth V1

The first Stage-3 information family of `PREDICTIVE_RESEARCH_GENERATION_V1`:
`PREDICTIVE_STAGE3_CROSS_ASSET_BREADTH_FAMILY_V1`, testing whether contemporaneous
crypto-market breadth — what the *rest* of the market is doing at the BTC decision instant —
carries 24h directional information about BTCUSDT.

Family disposition: **`REJECTED_DEVELOPMENT_NO_SEALED`**. Both configurations failed five of
seven predeclared gates; neither is sealed-eligible. Full numbers:
`reports/research/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1.md` and its JSON; the immutable
records are `research/experiments/EXP-PRED-007-…` and `EXP-PRED-008-…`.

## Research Director decisions, recorded before execution

`PREDICTIVE_RESEARCH_GENERATION_V1` continues; six rejected configurations were not treated as
a reason to change the frozen 24h target, and a target change is deferred because it would open
a new research generation. The Stage-1 canonical-hourly gap debt remains
`DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH`. Basis was **not** authorized — deferred, not
rejected: after nulls from settled funding (a carry/price channel) and open interest (a
positioning-quantity channel), a third derivatives/carry series was judged to carry less
expected information than an orthogonal cross-asset channel. The incremental control was
omitted deliberately, because no predictive family has been admitted and an incremental control
over an admitted feature set would be information-free. Three rejected families keep their
results, their disposition and their lack of sealed eligibility.

BTCUSDT remained the sole prediction and product target throughout. Every other asset is a
context feature; no asset was authorized for trading and no second target was created.

## The source already existed; the point-in-time semantics had to be earned

No acquisition was needed. The substrate is the already-governed
`BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1`: 17,925 official monthly objects from
`data.binance.vision/data/spot/monthly/klines`, credential-free, consolidated into 12,886,210
hourly rows over 486 symbols, hash-verified before a single row is read. 52 leveraged tokens are
excluded by the manifest's frozen symbol rule, and **BTCUSDT is removed from its own
cross-section entirely**, leaving 485 admitted context symbols. Only `symbol`, `open_time` and
`close` are read: `volume` and `quote_volume` are never touched, so no liquidity screen and no
volume weighting can exist. Prior cross-sectional research on this substrate answered a
different question under a different protocol and was **not** imported as predictive evidence.

At a decision instant `T` an asset participates only when it carries all four endpoint bars
`T`, `T-1h`, `T-24h`, `T-168h`, and the instant is usable only when at least 30 such assets
exist. Membership is recomputed at every instant and may grow or shrink causally.

**The audit demonstrates this rather than asserting it.** At one probe per candidate fold the
feature vector is recomputed twice: once from a panel that contains *only* the four endpoint
rows — so every asset in it has four observed bars in its entire history, against a retired
participation rule of 504 — and once from a panel whose columns have been permuted. Both
reproduce the real vector exactly, at every available probe. That single construction rules out,
together: any bar after `T`, any bar other than the four endpoints, any rule keyed to an asset's
total row count, any future-survival filter, and any per-asset weight. Nothing is interpolated,
forward-filled, substituted or reconstructed; a missing endpoint removes that asset from that
instant and is counted.

The residual assumption is recorded rather than hidden: the substrate is a monthly archive
reconstruction, so a bar the archive never published is absent rather than late, and absence
removes the asset instead of admitting a stale value. Abstention, not imputation, is this
source's only failure mode.

## The pre-result gates decided the fold set

Provenance, the exercised point-in-time semantics and the minimum-universe gate all passed. The
coverage gate then chose the folds from source availability alone — no label, no return value
and no candidate prediction entered the choice:

| fold | eligible | breadth coverage | causal pre-fold history | included |
| --- | --- | --- | --- | --- |
| 2019 | 8,673 | 0.8121 | 0 days | no |
| 2020 | 8,713 | 0.9958 | 300 days | yes |
| 2021 | 8,699 | 0.9967 | 666 days | yes |
| 2022 | 8,737 | 1.0000 | 1,031 days | yes |
| 2023 | 8,733 | 0.9997 | 1,396 days | yes |
| 2024 | 8,760 | 1.0000 | 1,761 days | yes |

2019 fails both conditions: the substrate itself opens 2019-01-01, so the fold has no causal
pre-fold history at all, and the young USDT cross-section does not reach 30 eligible assets for
19% of its hours. Five folds and 43,642 eligible timestamps survive, against declared minima of
five and 40,000. `N = 5` fixes the two-thirds rule at 4 of 5.

**Coverage was not the confound.** Pooled candidate coverage is 0.9984 — the highest of any
family in this generation — and every included fold clears 0.90 comfortably. The point-in-time
universe over the included timestamps runs to a median of 322 assets and a maximum of 387.

## The result

| | linear | HGBR |
| --- | --- | --- |
| win rate | 0.4930 | 0.4882 |
| coverage | 0.9984 | 0.9984 |
| actionable predictions | 43,572 | 43,572 |
| matched `TRAINING_UP_BASE_RATE` | 0.5268 | 0.5268 |
| primary delta | −0.0338 | −0.0386 |
| 97.5% paired interval | [−0.0597, −0.0071] | [−0.0616, −0.0148] |
| matched `ALWAYS_UP` | 0.5268 | 0.5268 |
| Brier | 0.2561 | 0.2563 |
| base-rate Brier | 0.2500 | 0.2500 |

This is the first family in the generation whose paired interval **excludes zero** — and it
does so on the wrong side. Both candidates are reliably *worse* than the information-free
control over 43,572 paired records, not merely indistinguishable from it. The training majority
declared `UP` in all five folds, so `TRAINING_UP_BASE_RATE` and `ALWAYS_UP` coincide at 0.5268
on the matched universe, and both candidates miss that floor as well. Neither beats the
control's Brier.

Per-fold deltas versus the base rate: linear −0.1611, +0.0051, +0.0369, −0.0349, −0.0153; HGBR
−0.1551, −0.0030, +0.0258, −0.0523, −0.0091. The linear configuration clears 2 of the required
4 folds, the boosted one 1 of 4.

2020 dominates the pooled damage for both configurations. Its training portion is also the
shortest — 7,019 breadth-valid rows against 41,924 for 2024 — and its base rate is the most
lopsided of the five at 0.5807 `UP` on the matched universe. Both configurations declared `DOWN`
far more often than that fold rewarded. This is an observation, not a rescue: the fold was
admitted before any result existed, it is not removable after one, and no descendant may be
tuned from it.

Failed conditions, both configurations: the MESI, the interval lower bound, the matched
`ALWAYS_UP` floor, the base-rate Brier, and the two-thirds fold rule.

## What was proven rather than asserted

Synthetic fixtures prove the eight features against hand computation on a symmetric
cross-section where every breadth share is exactly one half, every median exactly zero and each
MAD exactly `k · drift`; that a return of exactly zero is not an up move; that an asset missing
any one of the four endpoints leaves the universe at that instant and rejoins later; that a
future-only asset and a future-only bar cannot move the vector at `T` while the newcomer does
join once its own four endpoints exist; that only the four endpoint bars enter a vector; that
the statistics are invariant to column permutation; that the prediction target and every
leveraged token are refused by the panel itself; and both typed abstention rules.

The gate is proven to bind: a high win rate at 0.20 coverage cannot advance; clearing the
information-free control by a wide margin while missing matched `ALWAYS_UP` cannot advance; a
worse Brier than the control cannot advance. Both estimators are deterministic under the frozen
settings, and the committed results replay byte-identically.

## Validation and accounting

Backend tests, `check.py --no-data`, ruff, format, mypy and frontend validation all pass. Both
committed experiment results replay byte-identically against the installed data.

Family budget: 2 of 2 configurations consumed, 0 remaining. Model fits 20 (10 per configuration:
5 direction bases and 5 training-only Platt maps), plus 5 per-fold base-rate controls, which are
counted base rates and not model fits. Magnitude was not declared and none was fitted. Sealed
queries 0. No expansion of the prediction target, no combination with the rejected Stage-1,
settled-funding or open-interest features, no import of historical cross-section research
results, no basis, CFTC, macro, calendar, news, sentiment or on-chain source, no Stage-1
substrate repair, no post-cutoff data. All six prior predictive experiment results are
unchanged. Champion `NONE`, real money `false`.

## Next

Eight configurations across four information families have now been rejected on the frozen 24h
target: internal price/volume structure, settled funding, open interest, and cross-asset
breadth. `tasks/CURRENT_TASK.md` becomes
`RESEARCH-DIRECTOR-REVIEW-STAGE-3-CROSS-ASSET-BREADTH-CLOSURE` and authorizes no executor work.

Worth the Research Director's attention: this family is qualitatively different from the three
before it. The earlier nulls had intervals straddling zero — no information either way. Here the
paired interval excludes zero on the wrong side, at the highest coverage and the largest sample
the generation has produced. A signal that is reliably wrong is still a signal about the
substrate, and the obvious temptation — inverting it — is exactly the kind of post-hoc rescue
this protocol forbids, and would in any case still have to clear the matched `ALWAYS_UP` floor
that both configurations miss. Whether the finding reflects something real about breadth and BTC,
or the 2020 fold's short training window and lopsided base rate, is a question that may only be
answered by a new preregistered design, never by re-reading these two.
