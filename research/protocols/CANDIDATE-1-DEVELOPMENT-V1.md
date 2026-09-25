# Candidate #1 Development Lab protocol V1

Status: **FROZEN BEFORE OUTCOME INSPECTION**

Frozen by the Research Director on 2026-09-25 under Constitution 3.0,
`RESEARCH_STAGE_POLICY_V1`, Astra Strategic Operating Directive V2, ADR-0038 and the
Candidate #1 frozen admission.

This protocol authorizes **no market execution by itself**. It freezes the scientific question and
the implementation contract that an executor must implement and validate before a separate
Research Director execution authorization.

No Candidate #1 forward return, trade payoff, model result or economic outcome has been inspected
when this protocol is frozen.

## 1. Mechanism and lineage

Candidate #1 asks whether a sharp BTC spot sell-off accompanied by:

1. contraction in USD-M perpetual open-interest **quantity**; and
2. weakening of the traded perpetual price relative to traded spot

identifies a temporary-pressure state whose subsequent LONG payoff is materially better than the
payoff of otherwise comparable sharp sell-offs.

Lineage classification remains `DISTINCT_BUT_HEAVILY_PRIOR_CONSTRAINED`.

This is an observational conditional-payoff hypothesis. OI contraction does not prove liquidation,
relative perpetual weakness does not prove mispricing, and a positive result would not by itself
establish causality.

No flow, funding, news, calendar, RSI, VWAP, extra technical gate, learned classifier or additional
source is admitted.

## 2. Eligible population and state

The eligible event population and positioning state are inherited **unchanged** from
`CANDIDATE-1-FROZEN-ADMISSION-V1`.

Development interval: admitted OI interval 2022-2024 only.

For completed hour T:

- `R4 = log(spot_close_T / spot_close_(T-4h))`;
- prior hourly realized volatility uses the 168 completed 1h returns ending at T-4h,
  `sigma_prior_1h = sqrt(mean(r_k^2))`;
- `shock_z = R4 / (sigma_prior_1h * sqrt(4))`;
- event trigger is the first crossing from `shock_z > -2.0` to `shock_z <= -2.0`;
- triggers at T+1h, T+2h and T+3h are suppressed; a new trigger may occur from T+4h.

Candidate state at T requires both:

- `log(OI_T / OI_(T-4h)) < 0`;
- `log(perp_close_T / spot_close_T) - log(perp_close_(T-4h) / spot_close_(T-4h)) < 0`.

Every other valid sharp-sell-off episode is a control candidate for matching.

Admission availability and source rules remain binding, including the 2022-2024 OI restriction,
quantity-only OI, strict source validity and the T+15m decision timestamp.

The event, state, source population, windows and thresholds may not change after this freeze.

## 3. Primary playbook

At a valid Candidate-state event T:

- decision timestamp: `T + 15 minutes`;
- primary entry: raw BTCUSDT spot 1m **open** at `T + 16 minutes`;
- primary time exit: raw BTCUSDT spot 1m **open** at `T + 4 hours + 15 minutes`;
- fixed notional;
- LONG only;
- no leverage;
- no stop loss;
- no profit target;
- no trailing rule;
- no scale-in or scale-out;
- no model-generated confidence or sizing.

The one-minute gap between decision and entry prevents a simultaneous-decision/fill assumption.
The primary exposure is therefore 239 minutes inside a nominal four-hour event horizon.

The prior position exits at the next eligible event's decision timestamp before a possible new entry,
so the frozen four-hour episode rule does not create overlapping primary positions.

If the exact required entry or exit 1m open is unavailable or invalid, the trade is unscorable and
remains in the relevant denominator. No later favorable fill may replace it.

## 4. Primary execution costs

Primary development cost profile:

`CANDIDATE_1_SPOT_COST_PRIMARY_V1`

- entry fee: 10 bp;
- exit fee: 10 bp;
- adverse entry execution friction: 2 bp;
- adverse exit execution friction: 2 bp;
- nominal round trip: 24 bp.

This intentionally inherits the repository's conservative research convention as a provisional
development assumption. It is not asserted to be a current factual fee schedule for a future
execution venue.

Costs are applied with the existing cost-accounting semantics. Favorable slippage is unavailable.

## 5. Outcome and economic quantities

Per-trade outcome is arithmetic **net return on initial spot notional**, reported in basis points.

For each scorable trade report:

- raw entry and exit prices;
- gross return bp;
- fees bp;
- execution-friction bp;
- net return bp;
- holding minutes.

Primary absolute estimand:

`ABS_NET_BP = mean(candidate net return bp)`

Primary incremental estimand:

`INCREMENTAL_NET_BP = mean(candidate net return bp - matched-control net return bp)`

The incremental estimand is the primary scientific test of the positioning-state claim.
Absolute Candidate economics is a mandatory promotion gate.

Win rate, median return and forecast-style metrics are descriptive only.

## 6. Price-only control and matching

The control is a sharp-sell-off episode from the frozen eligible population that does **not** satisfy
the joint positioning state.

Matching is outcome-blind and uses only information known at T.

Perform matching separately inside each UTC calendar year.

Matching covariates:

1. `shock_z`;
2. `log(sigma_prior_1h)`.

Within each year, standardize each covariate using the mean and standard deviation over all valid
Candidate and control sell-off episodes in that year. A zero or invalid standard deviation blocks
that year's matching.

A Candidate-control edge is feasible only when both absolute standardized covariate differences are
`<= 0.50`.

Choose a deterministic **maximum-cardinality, minimum-total-squared-distance, one-to-one matching
without replacement** inside each year. After cardinality and distance, ties are broken
lexicographically by Candidate timestamp and then control timestamp.

No outcome, future return or execution result may affect the matching.

Matching gates before outcome interpretation:

- matched Candidate coverage >= 80% overall;
- matched Candidate coverage >= 70% in each of 2022, 2023 and 2024;
- absolute pooled post-match standardized mean difference <= 0.10 for each matching covariate;
- absolute within-year post-match standardized mean difference <= 0.25 for each matching covariate.

Failure is `BLOCKED_DATA_OR_SUPPORT`; do not inspect or rescue the economic result.

## 7. Outcome coverage and support gates

Primary execution must remain scorable for:

- >=95% of frozen Candidate episodes overall;
- >=95% of the frozen matched pairs.

At least 25 scorable Candidate trades must remain in **each** of 2022, 2023 and 2024.

Missing/untradeable events remain reported with fixed reason codes. No missingness rule may be
relaxed after output inspection.

## 8. Material economic thresholds

These thresholds are frozen before outcomes and are not selected from an attainable MDE.

Candidate #1 may be promotion-eligible only if all are satisfied under the primary specification:

### Absolute economics

- `ABS_NET_BP >= +25 bp/trade`.

### Incremental positioning value

- `INCREMENTAL_NET_BP >= +20 bp/matched pair`.

### Conservative annual opportunity value

Let `N_year_min` be the smallest scorable Candidate-trade count among 2022, 2023 and 2024.

Require:

`N_year_min * ABS_NET_BP >= 500 bp`

interpreted as at least 5% simple fixed-notional annual contribution under the conservative observed
annual opportunity count. This is not a compounded portfolio forecast.

### Tail / drawdown acceptability

On the matched sample:

- Candidate 10% expected shortfall may not be worse than matched control 10% expected shortfall by
  more than 25 bp.

On the chronological Candidate policy:

- maximum peak-to-trough cumulative fixed-notional net-return drawdown must be <= 1,000 bp.

These are product-risk screens, not alpha claims.

## 9. Stability and concentration gates

All are predeclared:

- Candidate mean net return must be >0 in at least 2 of the 3 calendar years;
- matched incremental mean must be >0 in at least 2 of the 3 calendar years;
- after removing the three Candidate trades with the highest primary net returns, Candidate pooled
  mean net return must remain >0;
- remove the corresponding three matched pairs from the incremental sample; pooled incremental mean
  must remain >0.

The removed-winner analysis is a concentration stress only. It cannot replace the primary result.

Report contribution of the largest 1, 3 and 5 winning Candidate events and calendar-year
concentration, but no additional subgroup may be selected as a successor.

## 10. Predeclared robustness analyses

Exactly two robustness analyses are allocated.

### Cost stress

Same population, matching, entry and exit as primary.

`CANDIDATE_1_SPOT_COST_STRESS_V1`:

- entry fee 15 bp;
- exit fee 15 bp;
- adverse entry friction 3 bp;
- adverse exit friction 3 bp;
- nominal round trip 36 bp.

Require Candidate mean net return >0.

### Delay stress

Same population, matching and primary 24 bp cost profile.

- decision remains T+15m;
- stressed entry = exact spot 1m open at `T + 46m`;
- stressed exit remains the exact spot 1m open at `T + 4h + 15m`.

This adds 30 minutes of entry delay while preserving the event's fixed terminal recovery window.

Require:

- Candidate stressed mean net return >0;
- stressed matched incremental mean >0.

No combined cost+delay stress is authorized. Neither stress can replace a failed primary result.

## 11. Diagnostics

Report, without creating selectable successors:

- intended / valid / scorable Candidate and control episodes;
- matching counts, distance summaries and balance;
- gross and net expectancy;
- incremental matched effect;
- break-even all-in transaction cost;
- win rate and median;
- per-year absolute and incremental means;
- cumulative fixed-notional net P&L and max drawdown;
- 10% expected shortfall;
- maximum adverse excursion and maximum favorable excursion for descriptive path analysis only;
- occupied minutes, occupied fraction and net bp per occupied hour;
- conservative annual contribution;
- top-winner and year contribution concentration;
- primary, cost-stress and delay-stress results;
- source/execution missingness and exclusion reasons.

MAE/MFE, path data and diagnostics may not be used to invent a stop, target, alternate holding horizon
or successor inside this allocation.

## 12. Dependence-aware uncertainty

Inference is descriptive Development-Lab evidence; no p-value alone can promote the Candidate.

For Candidate absolute net returns:

- compute a one-way UTC-calendar-month cluster-robust standard error.

For matched Candidate-minus-control differences:

- compute a two-way cluster-robust standard error using Candidate UTC month and matched-control UTC
  month as the two cluster dimensions.

Use standard finite-cluster corrections and report two-sided 95% confidence intervals.

Also report:

- raw standard deviations;
- per-year estimates;
- leave-one-year-out pooled estimates.

If a cluster-robust variance is undefined/non-finite or the implementation cannot support the
declared clustering faithfully, classify the relevant uncertainty analysis as invalid and do not
claim promotion eligibility.

No alternative block length, bootstrap, HAC bandwidth or inferential method may be substituted after
seeing results.

## 13. Prospective detectability gate after Development

Passing Development economics is insufficient.

Prospective planning uses two future economic claims:

1. absolute Candidate net expectancy >0 with economic MESI **+25 bp/trade**;
2. incremental Candidate-minus-control net advantage >0 with economic MESI **+20 bp/pair**.

For planning only:

- family-wise alpha = 0.05;
- allocate one-sided alpha = 0.025 to each claim;
- target power = 0.80 for each;
- maximum confirmation horizon = 12 months;
- prospective Candidate arrivals = the minimum scorable Candidate count among 2022, 2023 and 2024.

For each claim define a conservative planning standard deviation as the maximum of:

- its raw pooled per-observation standard deviation;
- its dependence-aware cluster standard error multiplied by `sqrt(N)`;
- the largest finite within-year raw standard deviation for that quantity.

Use the standard normal planning approximation:

`required_n = ceil(((z_(1-alpha) + z_0.80) * planning_sd / MESI)^2)`.

Both claims must have `required_n <= prospective Candidate arrivals`.

This is a promotion feasibility gate, not confirmation. A later prospective protocol must still
freeze the complete system and its actual dependence method before future collection.

The MESIs may not be increased after results merely to make the power gate pass.

## 14. Search / analysis budget

Authorized:

- one primary Candidate policy;
- one price-only matched control;
- one higher-cost stress;
- one longer-delay stress;
- the explicitly listed diagnostics, stability and concentration analyses;
- deterministic replays required for implementation verification.

Not authorized:

- alternative sell-off definitions;
- alternative OI or relative-price state definitions;
- another holding horizon;
- stop/target optimization;
- threshold search;
- different matching covariates;
- alternate calipers;
- alternate cost profiles;
- alternate delay values;
- funding, flow, volume, news, calendar or technical gates;
- model fitting / classifier search;
- subgroup winner selection;
- Candidate #2;
- any post-cutoff or sealed-data access.

## 15. Development dispositions

Apply in this order:

1. `INVALID_EXECUTION`
   - implementation violated the frozen protocol, or deterministic replay fails.

2. `BLOCKED_DATA_OR_SUPPORT`
   - matching, balance, source or outcome-coverage gates fail before valid economic adjudication.

3. `DEVELOPMENT_REJECTED`
   - any primary material-economic, tail/drawdown, stability/concentration or robustness gate fails.

4. `INCONCLUSIVE_NO_PROMOTION`
   - Development gates pass but one or both prospective detectability gates fail, or declared
     uncertainty is not defensibly estimable.

5. `PROMOTION_ELIGIBLE`
   - every integrity, support, economic, risk, concentration, robustness, uncertainty and
     prospective-detectability gate passes.

Only `PROMOTION_ELIGIBLE` permits preparation of one frozen prospective confirmation.

Every other valid terminal disposition closes the current Candidate #1 allocation and moves the
project to `STRONG_STOP_PENDING_ASTRA`. No Candidate #2, parameter rescue or successor is
automatically allocated.

## 16. Execution staging

This protocol freeze does **not** authorize economic outcome inspection.

Next stage:

1. Claude Code implements the protocol and deterministic/synthetic tests.
2. Outcome-free validation verifies population inheritance, matching mechanics, execution timing,
   cost accounting, stress semantics, diagnostics and replay.
3. Claude stops with `IMPLEMENTATION_READY_PENDING_RESEARCH_DIRECTOR_EXECUTION_AUTHORIZATION`.
4. The Research Director reviews the implementation.
5. Only a subsequent explicit repository task may authorize the single Development execution.

Champion remains NONE. Sealed queries remain 0. Real money remains false.
