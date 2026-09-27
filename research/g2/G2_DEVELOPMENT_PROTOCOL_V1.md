# G2 Development Protocol V1

Status: FROZEN AT G2-00 GATE A — DEVELOPMENT GOVERNANCE ONLY  
Date: 2026-09-27  
Authority: Constitution 4.0; ADR-0052; Astra Development System Directive V2

## 1. Scientific object

G2 is a complete development system, not a claim that a strategy is already valid.

The development question is:

Can one bounded, transparent BTCUSDT USD-M system:

1. issue a causally correct 4h predictive distribution at every eligible 15m decision point;
2. estimate actionability separately from terminal direction through frozen LONG/SHORT path-payoff
   labels;
3. select LONG/SHORT/NO_TRADE under fixed risk/execution semantics;
4. improve on simple frozen references without depending on hidden search, a few episodes or fragile
   cost assumptions?

Development evidence is exposed even when walk-forward, causal and statistically impressive.

## 2. Stages

The G2 sequence is:

SPECIFICATION
-> ENGINEERING_REPLAY
-> EXPOSED_DEVELOPMENT
-> FROZEN_CANDIDATE
-> PROTECTED_EVALUATION
-> PREDECLARED_STRESS
-> FUTURE_PAPER.

Current G2-00/G2-01 work does not authorize EXPOSED_DEVELOPMENT economics.

## 3. Development data boundary

Initialization:
- 2020 exposed history.

Exposed sandbox:
- 2021-01-01 through 2024-12-31.

Protected candidate history:
- 2025+ only after a separate exposure audit and G2-03 plan.

Future paper:
- observations actually emitted after explicit future-paper activation.

No historical relabeling can make exposed data pristine again.

## 4. Walk-forward semantics

Within the exposed sandbox:
- decisions every eligible completed 15m candle;
- monthly UTC model refit exactly as frozen in G2_FORECAST_POLICY_EXECUTION_CONTRACTS_V1;
- each fit uses only prior mature labels;
- training rows whose 4h market target or shadow trade label extends beyond the fit boundary are
  excluded;
- outcomes remain on the common UTC timeline including periods with no position.

No random K-fold model fitting is used.

Development uncertainty/comparison summaries use UTC-week block resampling so overlapping 4h labels
are not treated as independent rows.

## 5. Search budget

Eligible G2 development versions:

- G2-V0: one baseline;
- up to three general substantive revisions: G2-R1, G2-R2, G2-R3;
- one separately reserved cycle-timing revision: G2-RCYCLE.

Maximum eligible development-system versions = 5.

If the cycle method never reaches AVAILABLE_FOR_RESERVED_REVISION or no defensible cycle timing
change card is approved, G2-RCYCLE remains unused.

Its slot cannot be repurposed to another feature/model/threshold idea.

Renaming a version does not reset the budget.

The budget counts material scientific versions, not scheduled monthly refits.

## 6. Fixed references

Every eligible version is compared against:

1. NULL_FORECAST;
2. TREND_ONLY_FORECAST;
3. TREND_REFERENCE_POLICY;
4. CASH_REFERENCE.

Their definitions are frozen in G2_FORECAST_POLICY_EXECUTION_CONTRACTS_V1.

References are not tuned separately.

## 7. Predeclared diagnostic ablations

Exactly two diagnostic ablations are allowed in the first bounded cycle.

They are diagnostic-only and cannot be promoted directly as a G2 candidate.

ABL-G2-01 — FULL_MINUS_PARTICIPATION_FLOW_RESPONSE:
- remove RELATIVE_PARTICIPATION;
- remove TAKER_IMBALANCE;
- remove LOCAL_STRUCTURE_X_PARTICIPATION;
- remove IMBALANCE_X_PRICE_RESPONSE;
- refit the same ridge procedures under the same calendar/window/penalty conventions;
- retain structure, extension and volatility state.

Question:
Does the participation/flow-response block add useful information to the complete system beyond the
other V0 families?

ABL-G2-02 — FULL_ADDITIVE_ONLY:
- retain all six main observables;
- remove both interaction terms;
- refit same procedures.

Question:
Do the two predeclared interactions add useful conditional information beyond the additive main
effects?

No ablation result is a license to construct another unbudgeted child. A later revision may use an
ablation as supporting diagnosis only through a normal change card and revision slot.

## 8. What is not a development trial

These are recorded but do not consume a substantive revision slot:
- a scheduled monthly refit required by the frozen algorithm;
- rerunning a byte-identical deterministic check;
- synthetic fixtures that do not inspect market performance;
- correcting a proven implementation defect so code conforms to an already frozen contract;
- a factual source-schema or exchange-rule update that is required for correctness and does not
  choose an economically favorable alternative.

Affected market runs are invalidated and retained when a true bug is corrected.

## 9. What consumes a substantive revision

A revision slot is consumed before running a changed system whenever the change can alter economic
semantics, including:
- feature formula or active feature membership;
- interaction membership;
- model penalty or model class;
- fit calendar/window;
- target/horizon;
- predictive distribution construction;
- utility-head target or prudential margin;
- action rule;
- stop/expiry;
- execution friction/latency assumption chosen rather than factually corrected;
- risk sizing/limit;
- cycle activation/timing terms.

A change is still scientific when motivated by a plausible autopsy.

A profitable or losing outcome does not determine whether something was a bug.

## 10. Changes outside ordinary G2 revision authority

The following require Astra rather than an ordinary G2-R slot:
- change primary 4h forecast horizon;
- change BTCUSDT USD-M research instrument;
- expand or replace the six-family catalogue;
- introduce a new external data family;
- replace the transparent linear-ridge model family with trees/boosting/neural/ensemble models;
- increase the predictive/utility dictionary beyond eight numeric columns;
- change product mission;
- weaken protected-data/evidence hierarchy;
- exceed the total revision budget;
- reopen a lineage explicitly closed outside G2.

Real capital always requires the Owner.

## 11. Change-card contract

Before executing G2-R1/R2/R3/G2-RCYCLE, create an append-only change card containing:

- change_id and parent_version;
- author/proposer (human/AI);
- timestamp before execution;
- episodes/reports already observed;
- exact exposed data seen;
- recurring phenomenon and denominator;
- contrary examples/evidence;
- family/role implicated;
- causal mechanism hypothesis;
- smallest proposed change;
- exact old/new formula/parameter;
- predicted primary effect;
- predeclared primary diagnostic metric and direction;
- collateral-harm guardrails;
- why existing negative lineage does not already answer the question;
- expected additional degrees of freedom;
- source/corpus basis if any;
- code/data/model manifests to be frozen;
- revision-budget slot consumed.

One conceptual block is changed per revision.

Changing threshold + stop + horizon together is not a small revision.

## 12. Development scorecards

### Forecast scorecard

Primary proper score:
- mean CRPS of the empirical predictive distribution.

Secondary:
- q10/q50/q90 pinball loss;
- Brier score of r4h > 0;
- q10-q90 empirical coverage;
- MAE of median forecast;
- direction hit rate as descriptive only;
- all metrics by fixed view-strength/evidence strata.

Coverage/unavailability is always reported.

### Policy scorecard

Primary economic series:
- common-timeline simulated portfolio net return relative cash.

Secondary:
- mean realized NET_R of executed trades;
- total net return;
- max drawdown;
- time under water;
- turnover;
- occupancy/capital time;
- LONG/SHORT mix;
- cost and funding share;
- trade count plus calendar/episode distribution;
- NO_TRADE reasons;
- standardized LONG/SHORT shadow payoff distributions.

Hit rate is never the primary objective.

### Execution scorecard

- decision-to-fill delay;
- raw vs accounting fill;
- friction paid;
- funding paid/received;
- gaps/ambiguous fills;
- rejected/unavailable entry/exit counts;
- implementation shortfall when quotes later exist.

## 13. Development uncertainty report

For comparisons between two versions:
- construct paired metric contributions on a common timeline where meaningful;
- group timestamps into contiguous UTC calendar weeks;
- sample complete weeks with replacement;
- 5,000 bootstrap replicates;
- deterministic seed = 2026092702;
- report point delta and 10th/50th/90th percentiles.

This 80% interval is an internal stability diagnostic only. It is not independent validation and is
not reported as a discovery p-value.

For non-decomposable path metrics such as maximum drawdown, report both raw version values and
bootstrap path distributions rather than forcing a paired pointwise delta.

## 14. Revision preference rule

A child revision does not automatically replace its parent because one headline metric improved.

Before the child run, the change card identifies one primary metric consistent with the changed
role:
- forecast change -> lower CRPS;
- actionability/timing change -> higher common-timeline mean net portfolio return;
- execution-only factual repair -> no scientific preference contest; affected prior run invalidates.

The child becomes the preferred development version only if:
1. its primary point estimate improves in the predeclared direction;
2. the 10th percentile of the paired weekly-block improvement distribution is above zero;
3. no deterministic integrity/risk rule fails;
4. the change does not create a material new execution/cost burden;
5. coverage/support does not collapse in a way that invalidates the intended role.

If these are not all satisfied, the simpler parent remains preferred.

This is a development selection rule, not proof of future edge.

If two surviving versions are otherwise equivalent inside the reported uncertainty, choose:
1. fewer active terms/rules;
2. fewer changed components;
3. earlier registered version.

Never select purely by maximum Sharpe or cumulative return.

## 15. Coverage-collapse definition

For a policy revision, coverage collapse means either:
- executed-position time falls below 25% of its parent while the primary net-return improvement does
  not satisfy the revision preference rule; or
- more than 95% of otherwise eligible decisions become NO_TRADE because of the newly changed block.

These thresholds are development diagnostics, not profit targets.

A sparse policy can still be useful, but it must not appear superior solely because it nearly stops
trading.

## 16. Autopsy protocol

Autopsy starts only after target/trade maturity and first verifies:
- timestamp/data quality;
- model/version identity;
- execution/accounting;
- rule compliance.

The unit of qualitative diagnosis is an episode, not each overlapping 15m forecast.

Canonical factual categories:
- forecast sign error;
- magnitude/quantile error;
- evidence/calibration state issue;
- regime/context mismatch;
- feature relevance/conflict;
- actionability/path error;
- late/extended entry;
- stop/path loss despite correct terminal direction;
- cost/funding erosion;
- execution/data failure;
- false positive under explicit standardized payoff label;
- false negative/missed standardized opportunity;
- risk violation;
- drift/edge-decay candidate.

Every autopsy separates:
FACT -> CAUSAL HYPOTHESIS -> REQUIRED TEST.

Reports include favorable, unfavorable and deterministic pseudo-random sampled episodes. They may not
contain only researcher-selected charts.

## 17. Missed-opportunity semantics

A missed opportunity is evaluated only against the frozen standardized shadow trade at its original
decision point.

No best hindsight entry/exit.
No simultaneous portfolio accounting of every overlapping shadow.
No assumption of infinite capital.

Classes:
- MODEL_ABSTENTION;
- RISK_OR_CAPACITY_ABSTENTION;
- EXECUTION_FAILURE;
- COUNTERFACTUAL_REFERENCE_OPPORTUNITY.

Counterfactual payoff is diagnostic, not booked P&L.

## 18. Cycle reserved revision

G2-RCYCLE is the only cycle activation trial inside this G2 budget.

Prerequisites:
- actual G2 code passes every test in G2_CYCLE_CAUSALITY_CHECKPOINT_V1;
- cycle state has remained shadow in G2-V0;
- a pre-run change card documents the intended timing hypothesis.

No parameter/band/method search is allowed.

Reserved utility-head dictionary:
- keep the six V0 main observables;
- remove the two V0 interaction terms;
- add exactly:
  - CYCLE_FAST_TIMING;
  - CYCLE_INTERMEDIATE_TIMING.

For group G in FAST or INTERMEDIATE:
- include only scales whose quality is USABLE;
- q_i = clipped explained_fraction in [0,1];
- d_i = +1 for RISING, -1 for FALLING, 0 for FLAT;
- if sum(q_i) > 0:
  CYCLE_G_TIMING = sum(q_i*d_i) / sum(q_i);
- otherwise:
  CYCLE_G_TIMING = 0.

Availability/quality remains an explicit record field; numeric zero here means "no reliable signed
timing contribution admitted", not "observed equilibrium."

Cycle terms enter only LONG/SHORT utility heads.
The primary 4h market forecast remains G2-V0 and receives no cycle terms in the reserved revision.

Primary development metric for G2-RCYCLE:
- higher common-timeline mean net portfolio return versus its parent under identical risk/cost.

Cycle predictive utility is not inferred from standalone P&L or from this revision alone.

## 19. End-of-budget disposition

After the baseline and any executed allowed revisions, the Research Director chooses exactly one of:

A. FROZEN_ECONOMIC_CANDIDATE:
- preferred version is technically valid;
- development policy economics show positive net utility relative cash;
- value is not solely a tiny number of selected episodes;
- cost/risk behavior is credible;
- an evaluation feasibility note can define a protected test without inspecting protected outcomes.

B. ANALYTICAL_PRODUCT_ONLY:
- forecast/replay/autopsy product is valid but policy has not earned a protected economic test.

C. BOUNDED_REALLOCATION_PROPOSAL_TO_ASTRA:
- the full budget has produced a specific unresolved question whose answer may justify a new
  allocation.

There is no implicit fourth outcome "keep changing until profitable."

## 20. Protected-evaluation feasibility before Gate C

No universal raw trade-count threshold is used.

Before opening protected data for an economic candidate, create a frozen evaluation-feasibility
artifact from exposed development only containing:
- selected candidate and all references;
- economic minimum effect size for the protected claim;
- common-timeline primary estimand;
- temporal block length justified from holding/serial dependence;
- development-estimated block variance/concentration;
- expected protected interval length;
- minimum effective temporal support / precision needed;
- predeclared one-sided decision alpha;
- treatment of inconclusive results;
- all cost/stress scenarios;
- one-run access rule.

The minimum support/precision is frozen before protected outcomes are read.

If the planned protected interval cannot plausibly resolve the declared economic effect, do not
spend it merely because development P&L is positive.

## 21. Protected-evaluation contamination rule

If protected results are observed and then used to modify any economic model/policy rule:
- that interval becomes exposed for the successor;
- rerunning a changed model there is development evidence;
- a new freeze does not restore independence.

A proven implementation defect can invalidate a run, but researchers still retain what they saw; the
exposure ledger records it.

## 22. DSR/PBO

PBO is not a mandatory G2 gate because the small adaptive version set is highly correlated and too
small for informative CSCV ranks.

DSR may be reported as sensitivity if the series/trial-burden assumptions are interpretable.

Neither statistic is optimized and neither substitutes for:
- causality;
- realistic costs;
- bounded search;
- frozen protected evaluation;
- future paper.

## 23. Ledger requirement

Every:
- idea discussed;
- hypothesis/change card;
- executed version;
- automatic refit;
- ablation;
- bug rerun;
- source correction;
- protected access;
- future-paper activation

receives an append-only ledger record.

Human and AI authorship is preserved.

Raw trial count and lineage/correlation group are both retained. No post-hoc "effective number of
trials" is asserted as certain.

## 24. Real-money boundary

No G2 development, protected evaluation or future-paper success authorizes real capital.

Real capital remains an explicit Owner decision after separate risk/execution review.
