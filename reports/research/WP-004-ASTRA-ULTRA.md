# WP-004 scientific interpretation

DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE

Selected family: `ALIGNED_PARTICIPATION_CONTINUATION_V1`, an adaptive descendant of
`FAM-BREAKOUT`. Preselected primary: `ALIGNED`. Frozen terminal verdict:
**INCONCLUSIVE**. No Champion, sealed evaluation, paper action, or live authorization.
Structural success and research profitability are separate questions.

## What the previous evidence justified

WP-003 is accepted at `2b40aa03cfc05ac7f57d269f596f1ebacdc9d356`, with the real successful
remote CI check retained in the [review](../reviews/WP-003-RESEARCH-DIRECTOR-REVIEW.md).
Its default-cost trend, breakout, random, and delayed control results were negative;
no-trade correctly produced zero trades. Buy-and-hold is a long-horizon reference only.
Breakout's +0.0722123707 R zero-cost versus -0.0482093869 R default was an economic
margin problem, not proof of statistically non-random predictability. One asset/history,
unstable years, adaptive attention and unmatched controls preclude that inference.

This clue justified one small falsifiable allocation, not optimization. Fixed 2% risk
means nominal 24 bps friction costs approximately 0.12 R/trade. Trading fewer signals
reduces aggregate cost but does not itself improve per-trade net expectancy. Selectivity
must raise gross opportunity quality enough to cover the same friction, with usable
coverage across years. Wider stops would mechanically change R and confound that test.

## Ex-ante choice and chronology

The [design memo](../../research/design/ALGORITHM_FAMILY_V1_DESIGN.md) ranked exactly
three candidates before implementation/results:

1. Aligned participation continuation: prior-24h breakout plus completed 4h directional
   persistence and unusually high completed-hour volume. Selected because two small,
   inspectable gates directly address weak gross margin and regime instability, while
   keeping the baseline event and exit geometry unchanged.
2. Contraction-to-expansion release: deferred without testing. More choices concerning
   volatility normalization, compression, release and exit geometry create extra confounds.
3. Persistent-trend pullback recovery: deferred without testing. A different event needs
   additional reversal/recovery timing definitions and a less direct response to WP-003.

Volume is unsigned participation, not observed buyer demand. Directional persistence is
a path descriptor, not a causal regime oracle. Neither name supplies evidence of edge.
The three executed structures are regime-only, participation-only, and their conjunction;
ALIGNED remains primary even if an ablation has a more attractive number.

Protocol commit `a8c91b8`; design/ranking `17cc59a`; implementation `9044228`;
original preregistrations/admissions `4023928`; integrity correction `9fe1a00`;
effective version-2 preregistrations `8b6e983`. Execution used the latter committed HEAD.
Original declarations, negative results and admissions have not been rewritten.

The first post-preregistration loader failed closed on off-grid source timestamps,
before feature construction, conditions, profiles, attempt marker, or strategy results.
[ADR-0005](../../decisions/ADR-0005-PREEXECUTION-SOURCE-GRID-QUARANTINE.md) records the
zero-trial correction: 21,602 source opens in December 2017 / February 2018; quarantine
363 intersecting 1h and 92 intersecting 4h buckets. No source snapping, filling, deletion,
new data or changed scientific parameter. Three immutable version-2 declarations
supersede, not overwrite, their version-1 records. The 12-profile budget is unchanged.
Full-history WP-003 interpretations gain this availability limitation. These anomalies
precede 2019 validation and its context windows; that is a timestamp fact, not an
outcome-based assertion that rerunning WP-003 would be unchanged.

## Fixed evaluation and complete results

Six expanding annual development folds, 2019–2024; training begins at inception and
ends December 24 preceding each year; nine-day purge to January 2 validation start;
January 1 embargo. Validation ends at next January 1 00:00 UTC, with last signal
December 31 00:00 to contain its full 24h outcome. No fitting or fold selection.
The final boundary is close-time metadata of the last allowed minute, not 2025 data.
Completed contiguous bars, quarantines, as-of joins and one-position occupancy are
mandatory. A position is not released at an intrabar exit's opening timestamp.

The history was already exposed. This is structured chronological development validation,
not fresh OOS, sealed, independent forward, or paper evidence. Purge/embargo cannot erase
prior human/agent knowledge. The primary is pooled default-cost resolved net R/trade.

| Variant | Default R | Zero-cost R | Double-cost R | Delay 1h R | Default resolved trades | Frozen classification |
|---|---:|---:|---:|---:|---:|---|
| REGIME_ONLY | +0.0745672948 | +0.1948400902 | -0.0457054227 | +0.0294625972 | 186 | INCONCLUSIVE |
| PARTICIPATION_ONLY | +0.0231377752 | +0.1432997089 | -0.0970241010 | -0.0557704048 | 623 | REJECT_COST_DOMINATED |
| ALIGNED (primary) | +0.1373934676 | +0.2577702239 | +0.0170168144 | +0.0151299901 | 125 | INCONCLUSIVE |

| Default profile | Cumulative net R | Profit factor | Max drawdown R | Cost drag R | Mean net bps/trade | Positive folds | Minimum fold trades | Trade ESS / weekly Kish |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| REGIME_ONLY | 13.8695168268 | 1.1342852086 | 15.9005086561 | 22.3707399453 | 14.6891803068 | 4/6 | 10 | 146.18 / 52.42 |
| PARTICIPATION_ONLY | 14.4148339805 | 1.0453892729 | 19.6961866016 | 74.8608846399 | 4.5193585958 | 4/6 | 71 | 538.09 / 216.71 |
| ALIGNED | 17.1741834524 | 1.2657936152 | 11.5806334232 | 15.0470945348 | 27.0514092801 | 3/6 | 5 | 116.35 / 47.21 |

| Validation fold | REGIME_ONLY R (n) | PARTICIPATION_ONLY R (n) | ALIGNED R (n) |
|---|---:|---:|---:|
| 2019 | +0.285231 (42) | +0.036707 (110) | +0.404973 (30) |
| 2020 | +0.017653 (37) | +0.160730 (111) | -0.100900 (26) |
| 2021 | -0.175822 (27) | -0.096826 (95) | -0.118782 (12) |
| 2022 | -0.588923 (10) | +0.017864 (71) | -0.314077 (5) |
| 2023 | +0.200494 (38) | -0.000516 (114) | +0.059995 (28) |
| 2024 | +0.132947 (32) | +0.004304 (122) | +0.373512 (24) |

All 12 profiles completed. No invalid attempts. PARTICIPATION_ONLY retains one unresolved
path in each of default/zero/double (1/624 = 0.1603%) and two in delay (2/617 = 0.3241%);
these overlapping profiles are not independent missing events. No other unresolved
paths. No P&L is assigned to unresolved outcomes; occupancy is quarantined to expiry.
Full trade records, clock eligibility/suppression, all profile folds, regime breakdowns,
and diagnostics reside in the immutable experiment artifacts and
[evidence-only comparison](WP-004-COMPARISON.json).

## Where the behavior comes from — and what it does not establish

ALIGNED's gross margin is higher than the original breakout's, not merely fewer cost
payments. However, 2019 supplies 53.3015% of positive-fold profit, exceeding the frozen
50% limit. 2019 and 2024 together contribute 21.1135 R, more than the 17.1742 R total;
the other four years net negative together. This is a descriptive reading of the fixed
folds, not a searched alternative evaluation. Positive-fold count is only 3/6. Its
2021 and 2022 counts (12 and 5) fail the frozen 15-per-fold hurdle. Sufficiency takes
precedence, hence INCONCLUSIVE, not a retrospective relaxation to promising. It would
also fail the frozen stability criteria; uncertainty must not conceal that weakness.

All six leave-one-fold-out ALIGNED means remain positive, a useful but incomplete
counterpoint to concentration. Its equal-fold mean is only +0.050787 R, versus pooled
+0.137393 R. Maximum fold trade share is 24%; P&L concentration is more severe than
trade-count concentration. Best fold is 2019 (+0.404973 R); worst is 2022 (-0.314077 R).
Trade ESS 116.35 uses only positive sample autocorrelations at lags 1–5; 63 active weeks
have Kish concentration count 47.21. These are diagnostics, not 116 independent market
regimes, a confidence interval, a multiple-testing correction, or statistical significance.

The double-cost primary margin is only +2.9901 bps/trade (+0.017017 R). The delayed
condition produces +0.015130 R on 124 trades, versus +0.137393 R on 125: economically
much weaker, but still positive. Entry selection and occupancy change with delay, so
the contrast does not prove causal timing specificity or an exchange latency estimate.
The frozen rule uses cost/stability diagnostics, not selecting this robustness profile.

Regime-only has a 10-trade 2022 fold and negative equal-fold mean (-0.021403 R), plus
negative double-cost expectancy. Participation-only has sufficient nominal trade/ESS
coverage but a tiny default margin; double costs and delay turn negative. Its 2020
positive-fold profit share is 75.367%; dropping 2020 gives -0.006692 R. The frozen cost
rejection applies first; instability is an additional weakness, not an alternate verdict.

All ALIGNED/regime-only trades are in PERSISTENT_UP by construction, not evidence of
cross-regime robustness. In participation-only, the predeclared PERSISTENT_UP subgroup
is +0.140002 R on 115 resolved trades versus -0.003318 R on 508 OTHER trades. This is
consistent with the gating hypothesis, but is neither independent replication nor causal
identification. Those 115 are not the ALIGNED 125: removing OTHER entries changes
position occupancy, so filtering executed trades is not equivalent to rerunning a gate.

## Comparisons to preserved WP-003 controls

Existing trade artifacts were sliced to the identical 2019–2024 signal windows and full
horizon containment. No baseline or random seed was re-executed or selected.

| Stored control | Default net expectancy R | Resolved trades | Nonnegative folds |
|---|---:|---:|---:|
| Random, median of all 32 fixed seeds | -0.1031396170 | median 1,254/seed | seed fold details in artifact |
| SMA trend | -0.1081210229 | 1,955 | 1/6 |
| 24h breakout | -0.0535976983 | 911 | 3/6 |
| Delayed trend | -0.1099414994 | 1,960 | 2/6 |
| No trade | N/A | 0 | N/A |

Every stored random seed is negative (range -0.1384075900 to -0.0440530266 R), but the
32 seeds share one market history and do not supply a valid independent null test of
the new sparse strategy. Random turnover/regime exposure is unmatched. Baselines retain
their old eligibility, pre-window occupancy, and intrabar reentry semantics; WP-004
requires contiguous 4h context and conservative position release. These are descriptive,
not paired comparisons. Full-history WP-003 results remain in their original records,
not replaced by the sliced values. Buy-and-hold is deliberately excluded.

The primary's positive net behavior is economically more interesting than simply moving
the same weak gross mean, but broad improvement is not established. Summed R and bps
are unit-trade accounting, not compounded funded returns, capacity, or equal-capital
deployment performance. Default-cost profitability alone is not the current sole
bottleneck: temporal concentration, evidence sparsity, occupancy comparability and
source availability now matter at least as much as friction.

## Scientific memory, burden and next allocation

Cumulative burden is nine admitted/completed experiment configurations, 53 profile/seed
evaluations, three economic core hypotheses, four reference/control experiment roles,
four descendants, one observed-result adaptive decision and one result-dependent fork.
WP-004 spent one core hypothesis, three structural variants, 12 profiles and 72 fold
components; zero numeric parameter variants. Folds/profiles/32 random seeds do not become
independent mechanism confirmations. The timestamp repair added zero strategy trials.
No sealed holdout query, optimizer, extra fourth variant or alternative-family test ran.

The conjunction remains plausible, but its broad robust development claim is unsupported;
ALIGNED stays parked INCONCLUSIVE. Temporarily retire the ungated trend/breakout and
volume-only direction and park the tested single-gate branches. Preserve their falsified
claims without asserting that every possible continuation mechanism is false.

A further allocation is not justified as "improve the backtest." The strongest next step
is Research Director review followed by a bounded integrity/control-comparability
checkpoint: audit historical derived-bar availability and execution occupancy, then decide
whether a genuinely new, separately preregistered diagnostic of regime coverage can
discriminate mechanism from episodic selection. The ALIGNED gross-margin clue merits
consideration for that diagnostic only; this report grants **zero new trials**. Any
authorized controlled comparison later must count even identical-strategy replays as
evaluation burden under an explicit integrity question, never a renamed new hypothesis.
There is no fresh historical interval here that can undo prior exposure. Prospective
evidence would ultimately be stronger but remains unauthorized in this work package.

Do not next change breakout hours, volume/efficiency thresholds, stops, targets, horizon,
folds, ESS or minimum sample counts to rescue this result. Do not choose another primary,
add seeds until a control looks favorable, or rush to the two untested design alternatives.
Do not recycle the consumed WP-003 clue as new independent evidence. Any extension needs
an immutable allocation, both generations of evidence, and a distinct falsifiable question.

The [research map](../../research/memory/RESEARCH_MAP.md) and
[failure memory](../../research/memory/FAILURE_MEMORY.md) are generated from structured
records, including immutable post-result lessons. Deterministic fingerprints reject exact
renames and classify numeric drift; root budgets cannot be reset by labels. This is not
a universal semantic-equivalence oracle: genuinely new vocabulary and implementation-to-
fingerprint correspondence still need scientific review. The repository, not recollection
or this narrative, retains the audit trail.
