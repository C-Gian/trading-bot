# WP-006 — PERSISTENT_TREND_PULLBACK_RECOVERY_V1

DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE. Champion NONE. No sealed
query was executed. All six folds are previously exposed development history.

## What was tested

Exactly one new economic hypothesis under a new root family
`FAM-PULLBACK-RECOVERY`: during an already persistent multi-day uptrend, an hourly
close recovering above its one-day mean after the previous hour was at or below that
mean may identify a temporary countertrend weakness ending, offering a better
continuation entry than buying a fresh high.

Two frozen variants, primary fixed before results:

- **RECOVERY_CORE** (primary): `previous_close <= SMA24_prev`, `current_close > SMA24_t`,
  `persistent_up(t)`.
- **RECOVERY_CONFIRM**: `RECOVERY_CORE` and `current_close > previous_1h_high`.

No breakout condition, no SMA168, no volume gate, no pullback-depth threshold, no
alternate mean period, and zero numeric parameter variants. Geometry is fixed at
stop `-2%`, target `+4%`, maximum hold 1,440 minutes, one active LONG position.
The 4h persistence descriptor and the entire data-eligibility, quarantine and
contiguity universe are inherited unchanged from WP-004 and are **not** independent
new evidence.

## Governed novelty gate, before any market result

The two typed executable specs were submitted to SEARCH_MEMORY_V2 before a single
market array was loaded. The proposed root and its entry event were checked against
all 19 registered aliases and anchors; there was no collision.

| Variant | Classification | Matched prior experiments |
|---|---|---|
| RECOVERY_CORE | `NEW_FAMILY` | none |
| RECOVERY_CONFIRM | `DESCENDANT_MECHANISM_CHANGE` | RECOVERY_CORE only |

Family classification: **NEW_FAMILY**. The classifier was not modified, nothing was
renamed to force novelty, and no budget was reset. `FAM-BREAKOUT` remains exhausted
at 4/4 configurations and 15/15 trials.

The record is `research/memory/WP006-NOVELTY-ADMISSION.json` and reproduces exactly
from the frozen specs. Had the gate returned DUPLICATE, PARAMETER_VARIANT,
NEAR_DUPLICATE or a conflicting root, the rejection would have been preserved and no
market result produced.

## A pre-execution integrity correction

Before any trial ran, the preregistration identity binding was found to be
unverifiable: the typed spec was stored as JSON but compared against the in-memory
dataclass form. The validator was corrected to compare through one canonical JSON
round trip and to additionally pin the structural and dependency hashes.

Because correcting the validator changed its own file hash, the frozen dependency
manifest had to be re-frozen. The original preregistrations are **preserved
unchanged** and superseded prospectively by `preregistration.v2.json` under
`research/protocols/WP-006-PREEXECUTION-AMENDMENTS.json`, which records zero strategy
trials and zero results before the amendment, and zero added variants, profiles or
numeric searches. The hypothesis, primary metric, primary variant and evaluation
protocol are unchanged.

## Results — DEVELOPMENT_EVALUATION_V1, unchanged

| | RECOVERY_CORE | RECOVERY_CONFIRM |
|---|---:|---:|
| Terminal classification | **INCONCLUSIVE** | **INCONCLUSIVE** |
| Default net expectancy R | +0.0003823075 | +0.0219437002 |
| Zero-cost net expectancy R | +0.1204381257 | +0.1420066513 |
| Double-cost net expectancy R | −0.1196734624 | −0.0981191942 |
| DELAY_1H net expectancy R | +0.0069160662 | +0.0321112582 |
| Resolved trades (default) | 126 | 103 |
| Unresolved rate | 0.79% | 0.00% |
| Nonnegative folds | 3/6 | 4/6 |
| Worst-fold trades | 8 | 7 |
| Trade ESS | 117.25 | 91.53 |
| Max positive-fold profit share | 68.64% | 46.27% |

Per-fold default trades — core: 2019:22, 2020:21, 2021:20, 2022:8, 2023:30, 2024:25;
confirm: 2019:18, 2020:17, 2021:15, 2022:7, 2023:25, 2024:21.

**Why INCONCLUSIVE.** The rule is deterministic and was applied unchanged. The core
variant reaches 126 total resolved trades (≥120) but only 8 in DEV-2022 against a
required 15, so the sufficiency gate fires before any profitability gate is reached.
The confirm variant fails on both counts: 103 total and 7 in its worst fold. Neither
verdict is a claim that the mechanism has no edge; it is a statement that this
evidence cannot decide.

Had the sufficiency gate been met, the core variant would still have failed: only
3/6 nonnegative folds and 68.6% positive-fold profit concentration are both outside
the preregistered stability limits, and doubled costs turn it clearly negative.

## Comparison with preserved references

Descriptive only. Reference paths keep their own eligibility, occupancy and execution
semantics; none of this is a paired causal estimate.

| Reference | Default net expectancy R | Core delta |
|---|---:|---:|
| Random control (32 fixed seeds, mean) | −0.0967774607 | +0.0971597682 |
| SMA trend | −0.1081210229 | +0.1085033304 |
| Breakout (WP-003) | −0.0535976983 | +0.0539800058 |
| Matched parent breakout (WP-005) | −0.0547388706 | +0.0551211781 |
| ALIGNED (WP-004) | +0.1373934676 | −0.1370111601 |
| No-trade control | zero trades | not comparable |

Interpretation:

- **Gross margin.** +0.1204 R before costs, so the raw signal is not empty.
- **Default-cost survival.** Barely: +0.0004 R after a cost drag of 0.1201 R. That is
  economically indistinguishable from zero.
- **Double-cost sensitivity.** Fails outright at −0.1197 R. The edge, if any, is
  entirely inside the cost budget.
- **Fold coverage.** All six folds populated, but 2022 supplies only 8 trades.
- **Concentration.** 68.6% of positive-fold profit sits in one fold; 53.3 effective
  active weeks across 70 calendar weeks.
- **Confirmation effect.** Requiring the previous hour's high removes 23 of 126 trades
  and raises expectancy by +0.0216 R while lifting nonnegative folds to 4/6 — but it
  also drops the sample below the required minimum. Because CORE was fixed as primary
  before results, this is a diagnostic observation, **not** the family verdict.
- **Timing-delay sensitivity.** Shifting the condition one hour changes expectancy by
  only +0.0065 R and the trade count by +3, so the result is not knife-edge on
  immediate execution.
- **Distinction from breakout behaviour.** Of 127 executed core signals, **zero**
  coincide with any of the 912 executed matched-parent breakout signals or any of the
  125 executed ALIGNED signals. The rules fire at disjoint times, which is consistent
  with a distinct mechanism but does not by itself establish one.

## Scientific accounting

One new economic hypothesis, two configurations, eight profile evaluations, zero
numeric parameter variants, one adaptive decision and one result-dependent fork.
Cumulatively: 4 hypotheses, 11 configurations, 61 profile/seed trials, 0 numeric
variants, 3 adaptive decisions, 3 result-dependent forks, 0 sealed queries, 0 paper
trades, Champion NONE.

## Sealed eligibility

`SEALED_EVALUATION_V1` exists and is locked: 0 authorized and 0 consumed BTC queries,
reserved data never acquired. Across all 11 assessed candidates, **zero** are
seal-eligible. `EXP-ALG-009-ALIGNED` is `NOT_ELIGIBLE_INCONCLUSIVE`, and both WP-006
variants are `NOT_ELIGIBLE_INCONCLUSIVE`.

## What must not follow

No Champion, no sealed query, no paper trading. No mean-period, ratio, barrier or
horizon drift; that is numeric drift, not a revisit. No adoption of RECOVERY_CONFIRM
as the family conclusion because it scored better than the preselected primary. No
gate invented after seeing these numbers. `FAM-BREAKOUT` stays exhausted.

The binding limitation is trade sparsity in 2022 and profit concentration — not the
sign of the expectancy. A future allocation must respond to that, structurally, and
must come from the Research Director.
