# Algorithm family V1: ex-ante design and ranking

Status: frozen before implementation and before new market outcomes.
Evidence: WP-003 only; no strategy shopping, additional market summaries, or
alternative-candidate tests. Scope: BTCUSDT spot LONG, 1h decisions, completed 4h
context, canonical 1m execution, 24h maximum holding, development research only.

## What the evidence permits

The simple breakout's gross +0.0722123707 R became -0.0482093869 R under
default costs. Its gross result was not a stable calendar phenomenon. Random
entry's median was -0.0948689556 R; these unmatched, dependent development
comparisons do not establish statistical specificity. The trend and one-hour
delayed trend both lost after costs, weakening any claim that their precise
hourly timing mattered. We have evidence that this cost model matters, and a
reason to ask a conditional question, not evidence that a known profitable
population of trades merely needs to be uncovered.

With fixed 2% stop distance, nominal 24 bps friction costs about 0.12 R per trade.
Reducing trade count reduces total fees, but cannot by itself improve expectancy
per trade. A gate must select higher gross continuation payoff. Widening a stop
could cosmetically reduce cost in R while changing its meaning; changing both
selection and exits would make this first test difficult to interpret. We retain
the baseline barriers and explicitly accept their possible inefficiency.

## Candidate 1 — aligned participation continuation (rank 1, SELECTED)

Claim: a one-day upside price-boundary crossing is more likely to continue over
the next day when it agrees with sustained multi-day upward movement and arrives
with substantially greater participation than the preceding day. The economic
hypothesis is persistent demand plus contemporaneous attention/flow propagation.
OHLCV cannot identify investor motives or signed aggressive flow: this is a
falsifiable proxy claim, not a measured causal mechanism.

Minimal features: previous 24 completed 1h highs, current 1h close and base
volume, previous 24 completed 1h volumes, and 43 completed 4h closes. Current
close must strictly exceed all prior highs. Participation is current volume at
least twice the arithmetic mean of the previous 24 volumes, excluding current.
Two typical hours' activity concentrated in one hour supplies a simple unit-based
threshold; it is a design convention, not an estimated optimal value.

Context uses 42 four-hour close-to-close **price** increments (seven days). Let U
be the sum of positive increments and D the absolute sum of negative increments.
The gate is U >= 2D and U+D > 0, equivalently signed directional efficiency
(U-D)/(U+D) >= 1/3. This compares upward travel with retracement, avoiding a mere
positive-return test after a volatile round trip. Week/day time scales are fixed
calendar interpretations. Ratios make price level and absolute volume scale less
dominant; they do not make the strategy stationary.

4h context matters because it describes persistence slower than the hourly event.
Only bars whose closes precede or equal the signal are visible; context may be
0–3 hours old. No resampling of the open 4h bar is permitted. All required windows
must be complete and contiguous; gaps reset eligibility. Flat context and a zero
prior-volume mean fail their respective gates. No imputation or forward fill.

This differs structurally from WP-003 through two explicit gates, not renamed
breakout logic. It remains a descendant of that failed root family and consumes
its cumulative budget. Its opportunity to survive costs is higher conditional
gross payoff with the same barriers; sparsity alone is insufficient.

Expected failures: volume identifies climax/exhaustion; persistence selects late
entries after gains are already realized; attention is transient or mean-reverting;
gates mostly select high volatility that hits the fixed stop; large next-open
gaps invalidate plans; useful moves take longer than 24h; turnover stays costly;
or the intersection is too sparse for evidence. Base volume is unsigned and can
be affected by venue behavior. A daily denominator does not remove hour-of-day
seasonality. These are limits to interpret, not licenses for post-result filters.

Complexity: one existing event plus two scalar gates, two frozen thresholds, no
fit, no latent state, no learned weights, no feature library, and no exit search.
Overfitting risk remains material: selection was motivated by observed breakout
results and every year is already development-exposed. Three variants count as
three correlated configurations, not three independent confirmations.

Falsification: adequately sampled nonpositive default-cost expectancy falsifies
the claim that this frozen combination survives friction on these development
folds. Positive gross/negative net specifically falsifies economic sufficiency.
Fold concentration weakens portability; no improvement over either ablation
weakens the alignment story; no loss under a timing delay weakens hourly timing
specificity. Sparse evidence is INCONCLUSIVE, not a discovered edge or a reason
to lower thresholds. The locked classification rules determine outcomes.

## Candidate 2 — contraction-to-expansion release (rank 2, DESIGN ONLY)

Claim: a narrow recent range represents temporarily balanced supply and demand;
a completed upside range escape with renewed movement may propagate far enough
to cover friction. Minimal hypothetical inputs are completed 1h highs/lows/closes,
a daily versus weekly range comparison, and the breakout event. 4h context is
optional, since the distinct claim is volatility transition rather than sustained
direction. All range windows would end before the event and execution follow its
close. No exact configuration is registered or executable in WP-004.

Novelty would lie in volatility state, not another breakout window. The attraction
is entering near the start of expansion; the failure is that calm regimes merely
offer insufficient daily movement, while apparent escapes revert. Stops tied to
a narrow range amplify costs in R, and defining contraction/release/stop widths
adds interacting numerical choices. A fixed <=24h expiry would test a prompt
release, not an unlimited trend. Nonpositive net payoff after costs or expansion
only after the horizon would falsify a frozen version. Ranked below candidate 1
because it invites more joint choices and the WP-003 evidence does not identify
pre-breakout compression as the problem. Not implemented or tested.

## Candidate 3 — persistent-trend pullback recovery (rank 3, DESIGN ONLY)

Claim: a transient countertrend price concession inside persistent demand may
offer a better entry price than chasing a new high; recovery on a completed 1h
bar could indicate the concession ended. Minimal hypothetical features are a
completed 4h persistence measure and 1h drawdown/recovery prices. Unlike WP-003,
the entry event is recovery from a retreat, not breakout or continuous trend
membership. 4h context separates the slower demand hypothesis from the local
price concession. Every reference level would be fixed before the signal close.

Potential cost survival comes from improved entry value and asymmetric recovery,
but a pullback may be the start of a regime reversal and a confirmation may give
back the entire concession. It needs choices of pullback depth, recovery event,
stop, and invalidation, creating more degrees of freedom than candidate 1. A
<=24h stop/expiry design would demand prompt recovery; no recovery within that
horizon or no net edge would falsify a frozen version. Rank 3 because our current
evidence says little about this distinct mechanism. Not implemented or tested.

## Frozen WP-004 structure and priority

There is **one core hypothesis**, `ALIGNED_PARTICIPATION_CONTINUATION_V1`, under
the existing breakout root. Exactly three variants will be preregistered:

| Variant | Entry gates beyond prior-24h-high breakout | Scientific role |
|---|---|---|
| REGIME_ONLY | 4h U >= 2D | Participation ablation |
| PARTICIPATION_ONLY | 1h volume >= 2 times prior-day mean | Regime ablation |
| ALIGNED | Both gates | Preselected primary family claim |

The ablations do not create independent core hypotheses. ALIGNED determines the
family conclusion regardless of which result is numerically best. A favorable
ablation requires a newly recorded adaptive decision and future allocation.

All variants freeze the same signal-close reference, stop=0.98*reference,
target=1.04*reference, 1,440-minute expiry, next-1m-open entry, costs V1 and
engine/execution V2. One position at a time. An entry open outside the barriers
is invalid. Missing path while open is unresolved; the original expiry prevents
early re-entry. An intraminute exit is available only after that minute closes;
even an exit at an hourly open conservatively cannot reopen at that same open.
An expiry at the previous minute's close is available at the new boundary.

To compare the gates and delay on a common data-quality universe, every variant
requires 26 complete contiguous 1h bars at decision time plus valid 43-bar 4h
context both at decision time and one hour earlier. This is a completeness rule,
not a price-regime gate. Normal features use the latest 25 hours/current context;
DELAY_1H uses the condition at t-1h and the latest signal-close reference at t.
Signals near fold end must allow the entire entry-plus-24h path within validation.

Four execution profiles per variant: DEFAULT, ZERO diagnostic, DOUBLE stress,
and DEFAULT with DELAY_1H. No other timing shifts, thresholds, exits, folds,
random seeds, or configurations. Structural ablations meet the additional
feature/regime robustness requirement. Exactly 12 profile trials / 72 annual
components are allocated. No full-history optimization and no tested alternatives.

Evaluation and terminal rules are frozen in DEVELOPMENT_EVALUATION_V1. Report
net R alongside raw-price net return per trade to expose denominator artifacts,
cost drag, suppression/invalid/unresolved counts, all six folds, year/regime
concentration, and fixed-control comparisons. Different occupancy between rules
limits causal attribution; shared time windows do not make trades matched.
All output is DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE.
