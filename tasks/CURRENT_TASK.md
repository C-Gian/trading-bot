# CURRENT TASK — WP-007
# Order-Flow Feature Foundation + Aggressive Buy-Flow Transition Family

## STATUS
ACTIVE

## EXECUTOR
Primary: Codex.
Fallback/overflow: Claude Code if Codex usage is unavailable.

This task is executor-neutral. Scientific truth lives in repository artifacts.

ChatGPT / GPT-5.6 Sol remains Research Director and final scientific authority.
Astra Ultra is NOT allocated to WP-007.

---

# 0. PURPOSE

WP-006 is independently accepted as structurally sound, with one non-material current-state
reporting fix assigned here.

WP-006 produced a genuinely distinct pullback/recovery family, but the primary rule is not worth
parameter rescue:

- RECOVERY_CORE default expectancy: +0.0003823075 R
- ZERO: +0.1204381257 R
- DOUBLE: -0.1196734624 R
- 126 resolved trades
- only 3/6 nonnegative folds
- minimum fold trades = 8
- positive-fold profit concentration = 68.64%

RECOVERY_CONFIRM:
- default +0.0219437002 R
- 103 trades
- 4/6 nonnegative folds
- minimum fold trades = 7
- still INCONCLUSIVE

The family is parked. Do NOT modify it.

The strongest current development clue remains ALIGNED:
`+0.1373934676 R` default, but INCONCLUSIVE and not seal-eligible.

Across multiple price-only families, gross expectancy has often existed while default friction
consumed much or all of the margin.

WP-007 therefore moves to a genuinely different information source already present in the
accepted canonical Binance Spot data:

- `taker_base`
- `taker_quote`
- total base `volume`
- total `quote_volume`

The new economic question is:

> Does an exchange-reported transition toward aggressive taker buying, when broader completed
> 4h taker flow is already buy-dominant, contain enough next-day continuation information to
> survive realistic BTCUSDT Spot friction?

This is an order-flow proxy hypothesis, not another breakout/trend/pullback price pattern.

WP-007 has three major objectives:

1. independently audit and version the historical taker-volume feature substrate;
2. prospectively correct sealed-query authorization governance so ordinary scientific sealed
   allocation does not require Owner interruption, while keeping query budget at zero;
3. preregister and evaluate exactly one new order-flow family with two fixed variants and zero
   parameter search.

---

# 1. REQUIRED START

Repository:
`C-Gian/trading-bot`

Branch:
`main`

Required starting HEAD:
`d92088d5ef0426bf64f34326a3224dd9aba93603`

Reviewed predecessor:
`444172a359e2663887624da82254cc2185ff85e1`

Do not create a branch.
Do not rewrite history.
Do not push.

---

# 2. WP-006 RESEARCH DIRECTOR REVIEW

Create:

`reports/reviews/WP-006-RESEARCH-DIRECTOR-REVIEW.md`

Record:

## Verdict

`ACCEPTED_WITH_STATE_FIX`

## Verified evidence

- WP-006 starts exactly from `444172a...`;
- final HEAD `d92088d...`;
- real GitHub Actions run `34362902153` completed SUCCESS;
- novelty admission commit preceded preregistration/result commits;
- effective v2 preregistrations were committed before result finalization;
- the pre-execution binding correction happened with zero trials/results;
- originals were preserved;
- RECOVERY_CORE and RECOVERY_CONFIRM are both INCONCLUSIVE;
- no parameter optimization occurred;
- FAM-BREAKOUT remained exhausted;
- 0 sealed BTC queries;
- sealed dataset state `RESERVED_NOT_ACQUIRED`;
- 0 paper trades;
- Champion NONE;
- real money false.

## Non-material state finding

`state/current_state.json` still contains:
`wp005_integrity.remote_ci = PENDING_PUSH`

even though WP-005 real remote CI was already verified SUCCESS.

Fix the authoritative current state prospectively.

Do not rewrite historical WP-005/WP-006 checkpoint artifacts merely to update a once-pending
external fact.

Add current-state remote-CI truth fields sufficient to represent:

- WP-005: SUCCESS
- WP-006: SUCCESS after Research Director review

and remove stale pending state from the authoritative current state.

---

# 3. SCIENTIFIC START STATE

Expected before new experiment execution:

- experiments_completed = 11
- material economic hypotheses = 4
- configuration variants = 11
- profile/seed trials = 61
- numeric parameter variants = 0
- adaptive decisions = 3
- result-dependent forks = 3
- sealed queries = 0
- sealed evaluations = 0
- paper trades = 0
- Champion = NONE
- forward evidence = NONE
- real money = false

---

# 4. FORBIDDEN WORK

Do NOT:

- modify ALIGNED;
- reopen FAM-BREAKOUT;
- modify pullback recovery;
- adopt RECOVERY_CONFIRM because it scored better;
- test contraction-to-expansion in this WP;
- add price breakout/trend/pullback gates to the new order-flow core;
- optimize the 50% flow-balance threshold;
- test 51/52/55/60% taker ratios;
- optimize context duration;
- optimize stop/target/horizon;
- add RSI/MACD/TA indicator zoo;
- grid search;
- random/Bayesian/evolutionary search;
- access BTC data after `2024-12-31T23:59:00Z`;
- acquire sealed BTC data;
- query sealed BTC data;
- access non-BTC assets;
- SHORT;
- leverage/perpetuals;
- paper trade;
- enable Analyze Market;
- produce product LONG/NO_TRADE advice;
- create Champion;
- real-money/exchange execution code;
- create a new branch;
- push.

Profitability is never a structural PASS criterion.

---

# 5. STAGE A — SEALED AUTHORITY CORRECTION BEFORE FIRST USE

WP-006 sealed infrastructure is technically sound, but its unlock text unnecessarily requires
Owner authorization for an ordinary scientific sealed evaluation.

The Owner has already delegated research direction and experiment allocation to the Research
Director. Owner interruption is reserved for genuinely consequential Owner decisions such as real
capital, external irreversible actions, expenditure/credentials, or material changes to the
product/risk objective.

A historical sealed evaluation is a scientific research allocation, not real-capital authorization.

Prospectively create:

`SEALED_EVALUATION_V1_1`

and:

`decisions/ADR-0008-SEALED-SCIENTIFIC-ALLOCATION-AUTHORITY.md`

Do NOT rewrite the WP-006 contract as though the earlier wording never existed.

V1.1 must change ONLY authorization governance:

- only an explicit Research Director sealed-allocation artifact may raise the query budget;
- executors cannot self-authorize;
- automated workflows cannot self-authorize;
- candidate eligibility rules remain unchanged;
- query consumption/immutability rules remain unchanged;
- real money remains a separate mandatory Owner gate;
- authorized BTC queries remain 0;
- consumed BTC queries remain 0;
- sealed dataset remains RESERVED_NOT_ACQUIRED.

No sealed query in WP-007.

Update synthetic tests accordingly.

---

# 6. STAGE B — CANONICAL TAKER-FIELD INTEGRITY AUDIT

The accepted canonical 1m Parquet already contains:

- open_time
- OHLC
- volume
- quote_volume
- trades
- taker_base
- taker_quote

The new family may not use these fields until a deterministic integrity audit passes.

Create:

`docs/contracts/ORDER_FLOW_FEATURES_V1.md`

`reports/validation/WP-007-ORDER-FLOW-INTEGRITY.json`

`reports/research/WP-007-ORDER-FLOW-DATA.md`

## Audit every available canonical 1m row

Verify at minimum:

- same accepted dataset content identity;
- max timestamp <= development cutoff;
- no post-cutoff read;
- `volume >= 0`;
- `quote_volume >= 0`;
- `taker_base >= 0`;
- `taker_quote >= 0`;
- `taker_base <= volume` within an explicitly documented numerical tolerance;
- `taker_quote <= quote_volume` within an explicitly documented numerical tolerance;
- counts of zero-volume rows;
- counts of zero-quote-volume rows;
- counts of invalid taker ratios;
- finite numeric values;
- canonical timestamps remain ordered/unique;
- known source-grid quarantine is applied;
- missing minutes remain unfilled.

Do not silently clamp a bad ratio to [0,1].

If material violations exist:

- preserve counts/examples;
- do not run order-flow market experiments;
- WP-007 research stage becomes PARTIAL;
- do not modify the accepted canonical dataset.

## Source provenance sample

Independently verify the taker fields against immutable raw Binance archives for a deterministic
sample spread across the development history.

The sample selection rule must be frozen before inspection and use only timestamp/hash identity,
not values.

At minimum:
- one deterministic sample per calendar quarter with available raw data;
- include both known off-grid anomaly intervals;
- compare canonical volume/quote_volume/taker_base/taker_quote to raw CSV fields exactly or under
  the same deterministic float parsing semantics used by acquisition.

Record mismatches.

No third-party data.

---

# 7. STAGE C — ORDER-FLOW DERIVED FEATURE SUBSTRATE

Do NOT alter canonical data.

Create a separate versioned derived feature substrate:

`BTCUSDT-SPOT-ORDERFLOW-DEV-v1`

Suggested local files:

- `data/derived/BTCUSDT-1h-orderflow-v1.parquet`
- `data/derived/BTCUSDT-4h-orderflow-v1.parquet`

and tracked manifest:

`data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json`

Actual large derived files remain subject to existing data/git policy.

## 1h feature bucket

For each UTC-aligned completed 1h bucket:

- `source_minutes`
- `complete`
- total base volume
- total quote volume
- total taker-buy base volume
- total taker-buy quote volume
- `taker_buy_base_share = sum(taker_base) / sum(volume)` if denominator > 0 else null
- source-grid-quarantine status
- eligible status

## 4h feature bucket

Same aggregation on UTC-aligned completed 4h buckets.

No mean of minute-level ratios.
Use ratio of summed taker volume to summed total volume.

Incomplete/quarantined buckets are ineligible.

No fill.

## Independent oracle

Create an independent aggregation/oracle path that does not call the production feature builder.

Reconcile:
- full bucket counts;
- eligible bucket counts;
- deterministic sample values;
- edge buckets;
- source-grid anomaly buckets;
- hashes.

If the derived substrate cannot reproduce deterministically, stop before market results.

---

# 8. STAGE D — ORDER-FLOW FEATURE SEMANTICS

Use `taker_buy_base_share`.

Interpretation must be conservative:

It is Binance's exchange-reported **taker buy base asset volume share**.

It is a proxy for aggressive buy-side participation on that venue.

Do NOT claim:
- complete market-wide order flow;
- investor intent;
- signed net demand across exchanges;
- causality merely from correlation.

Natural balance point:

`0.5`

means taker-buy base volume equals half total base volume.

The exact threshold 0.5 is chosen from the field's accounting meaning, not fitted.

No alternate threshold is authorized in WP-007.

---

# 9. STAGE E — NEW FAMILY ALLOCATION

Create:

`WP007-AGGRESSIVE-BUY-FLOW-ALLOCATION`

This is one adaptive/result-dependent research allocation because accumulated development evidence
motivated moving away from price-only patterns toward a closer-to-mechanism feature family.

Increment:

- adaptive decisions +1
- result-dependent forks +1

Authorize exactly:

- new economic hypotheses: 1
- strategy configurations: 2
- numeric parameter variants: 0
- profiles per configuration: 4

Profiles:
- DEFAULT
- ZERO
- DOUBLE
- DELAY_1H

Total new strategy profile evaluations:
8

No additional seed/control in WP-007.

If results later justify matched controls, they require another explicit allocation.

---

# 10. STAGE F — PROPOSED ROOT FAMILY

Proposed root:

`FAM-ORDER-FLOW`

Hypothesis ID:

`AGGRESSIVE_BUY_FLOW_TRANSITION_V1`

Economic hypothesis:

> A transition from non-dominant to dominant exchange-reported taker buying in the just-completed
> 1h bar, when the most recently available non-overlapping completed 4h context is already
> buy-dominant, may indicate renewed aggressive demand with enough next-day continuation to
> survive BTCUSDT Spot friction.

This is intentionally not a price-boundary, trend-membership or pullback-recovery hypothesis.

---

# 11. STAGE G — EXACT AS-OF CONTEXT

At UTC hourly decision boundary `t`:

Current signal hour:
`[t-1h, t)`

Previous signal hour:
`[t-2h, t-1h)`

For 4h context, use:

the most recent completed UTC-aligned 4h bucket whose close timestamp is
`<= t-1h`.

This guarantees the 4h context does NOT contain the current 1h signal bar.

Document the possible context staleness honestly.

No open/incomplete 4h bar.

All buckets must be complete, contiguous as required, and not quarantined.

---

# 12. STAGE H — EXACT VARIANTS

## Variant 1 — FLOW_CORE (PRIMARY)

Preselect as family primary before results.

Emit LONG iff all are true:

1. previous completed 1h `taker_buy_base_share <= 0.5`
2. current completed 1h `taker_buy_base_share > 0.5`
3. most recent non-overlapping completed 4h context `taker_buy_base_share > 0.5`

This is a transition event:
non-dominant -> dominant aggressive taker buying,
inside a buy-dominant slower context.

No price condition.

## Variant 2 — FLOW_PRICE_RESPONSE

FLOW_CORE
AND:

`current_completed_1h_close > current_completed_1h_open`

Scientific role:

Tests whether aggressive buy-flow transition is more informative when price responds positively
during the same completed hour.

This is the only price confirmation.

No breakout.
No SMA.
No persistence U/D.
No volume-multiple threshold.
No pullback rule.

---

# 13. STAGE I — SEARCH_MEMORY_V2 NOVELTY GATE

Before market results, create executable strategy specs for both variants.

Submit them to SEARCH_MEMORY_V2.

Expected primary classification:

`NEW_FAMILY`

or an equivalent governed new-root outcome.

FLOW_PRICE_RESPONSE may be a descendant/confirmation within the new root.

If primary is classified as:

- DUPLICATE;
- PARAMETER_VARIANT;
- NEAR_DUPLICATE;
- conflicting root/family;

then:

- do not weaken classifier;
- do not rename;
- do not add conditions just to force novelty;
- do not execute market results;
- preserve rejection;
- feature substrate may still complete;
- WP-007 research stage becomes PARTIAL.

Check against both V1 and V2 historical signatures.

---

# 14. STAGE J — EXECUTION RULES

Unchanged:

- BTCUSDT Spot
- LONG only
- 1h decision clock
- 4h context
- canonical 1m execution path
- BACKTEST_ENGINE_V2
- EXECUTION_MODEL_V2
- BTCUSDT_SPOT_COST_V1
- one active position
- no leverage
- no SHORT

Signal event ordering:

`BAR_CLOSE -> SIGNAL_DECISION -> NEXT_1M_OPEN_EXECUTION`

Reference price:

current completed 1h close.

Trade geometry:

- stop = reference * 0.98
- target = reference * 1.04
- max hold = 1,440 minutes

No exit search.

Existing gap/unresolved rules unchanged.

---

# 15. STAGE K — DEVELOPMENT EVALUATION

Use unchanged:

`DEVELOPMENT_EVALUATION_V1`

Six exposed-development folds:
2019–2024.

Do not modify:

- purge;
- embargo;
- containment;
- minimum total trades;
- minimum fold trades;
- ESS diagnostics;
- fold-stability rule;
- concentration rule;
- doubled-cost rule;
- terminal classification order.

No full-history optimizer.

---

# 16. STAGE L — ROBUSTNESS PROFILES

For each variant run exactly:

1. DEFAULT
2. ZERO
3. DOUBLE
4. DELAY_1H

## DELAY_1H

At boundary `t`, use the exact order-flow condition that was available at `t-1h`.

Use the latest current signal-time close at `t` as reference price following existing delay-control
convention.

No other timing shifts.

---

# 17. STAGE M — PREREGISTRATION CHRONOLOGY

Before any order-flow market result:

1. feature substrate integrity PASS;
2. production feature builder + independent oracle implemented;
3. exact strategy code/specs implemented;
4. synthetic tests PASS;
5. commit implementation;
6. SEARCH_MEMORY_V2 admission PASS;
7. family allocation/registry committed;
8. create both preregistrations;
9. commit preregistrations;
10. only then execute market results.

Suggested IDs:

- `EXP-ALG-012-ORDERFLOW-CORE`
- `EXP-ALG-013-ORDERFLOW-PRICE-RESPONSE`

If a true pre-execution integrity bug is discovered:

- preserve originals;
- record zero trials/results;
- correct prospectively.

If a material bug is discovered after result observation:

- preserve affected evidence;
- do not overwrite;
- stop and require a future allocation.

---

# 18. STAGE N — TERMINAL CLASSIFICATION

Use unchanged `DEVELOPMENT_EVALUATION_V1`.

Possible:

- INCONCLUSIVE
- REJECT_COST_DOMINATED
- REJECT
- REJECT_UNSTABLE
- PROMISING_DEVELOPMENT_ONLY

Family conclusion follows preselected `FLOW_CORE`, not the better-scoring variant.

Even if PROMISING:

- no Champion;
- no sealed query;
- no paper trade.

---

# 19. STAGE O — INTERPRETATION

Create:

`reports/research/WP-007-ORDER-FLOW.md`

Report:

- feature integrity;
- source provenance sample;
- exact order-flow semantics;
- variant definitions;
- fold results;
- cost sensitivity;
- timing sensitivity;
- total/fold trade counts;
- ESS/concentration;
- invalid/unresolved;
- comparison with prior preserved references.

At minimum compare descriptively with:

- random control;
- SMA trend;
- breakout;
- ALIGNED;
- pullback recovery core;
- no-trade.

Do not call comparisons paired unless they are actually matched.

Questions:

- Does taker-flow transition generate positive zero-cost expectancy?
- Does default friction consume the signal?
- Does double cost survive?
- Is evidence more evenly distributed than ALIGNED?
- Does price-response confirmation improve economics or only reduce coverage?
- Does DELAY_1H weaken the event?
- Is the new mechanism truly behaviorally distinct?

No new post-result gate.

---

# 20. STAGE P — SEARCH MEMORY UPDATE

If admitted and executed:

Add exactly:

- one new root family;
- one new economic hypothesis;
- two configurations;
- eight profile evaluations;
- zero numeric variants.

Cumulative expected if fully executed:

- experiments_completed = 13
- material economic hypotheses = 5
- configurations = 13
- profile/seed trials = 69
- numeric variants = 0
- adaptive decisions = 4
- result-dependent forks = 4

Preserve:

- FAM-BREAKOUT exhausted;
- FAM-PULLBACK-RECOVERY consumed/parked;
- ALIGNED parked INCONCLUSIVE.

No budget reset through names.

---

# 21. STAGE Q — SEALED ELIGIBILITY

Regenerate candidate eligibility under `SEALED_EVALUATION_V1_1`.

Still:

- authorized BTC queries = 0
- consumed BTC queries = 0
- sealed data RESERVED_NOT_ACQUIRED
- no sealed query.

ALIGNED remains NOT_ELIGIBLE_INCONCLUSIVE.

Pullback variants remain NOT_ELIGIBLE_INCONCLUSIVE.

If FLOW_CORE becomes PROMISING_DEVELOPMENT_ONLY:

record:

`DEVELOPMENT_ELIGIBLE_PENDING_RESEARCH_DIRECTOR_SEALED_ALLOCATION`

but execute no sealed query in WP-007.

FLOW_PRICE_RESPONSE does not replace the primary merely because it scores higher.

---

# 22. STAGE R — UI/API

Only small research inspection additions.

Research Lab may show:

- order-flow feature substrate status;
- latest family result;
- SEARCH_MEMORY_V2;
- SEALED_EVALUATION_V1_1;
- `LOCKED — 0 AUTHORIZED / 0 CONSUMED`;
- Champion NONE.

Dashboard remains:
- PAPER ONLY
- Analyze Market disabled
- no product signal

No sealed browser.

---

# 23. STAGE S — STATE

On full execution:

Expected:

- experiments_completed = 13
- material_economic_hypotheses = 5
- configurations = 13
- profile_trials = 69
- numeric_parameter_variants = 0
- adaptive_decisions = 4
- result_dependent_forks = 4
- sealed_queries = 0
- sealed_evaluations = 0
- paper_trades = 0
- Champion = NONE
- forward evidence = NONE
- real money = false

Update:

- latest reviewed checkpoint = WP-006
- latest executor checkpoint = WP-007
- WP-005 remote CI = SUCCESS
- WP-006 remote CI = SUCCESS
- order-flow feature substrate identity/status
- latest family
- sealed version/status
- next recommended checkpoint.

If market execution is blocked, use truthful counters.

---

# 24. STAGE T — VALIDATION

Strengthen `python scripts/check.py`.

Validate at minimum:

## Review/state
- exact WP-007 base `d92088d...`;
- WP-006 real CI SUCCESS evidence;
- current state no stale WP-005 pending CI;
- report-base guard.

## Order-flow data
- canonical content hash unchanged;
- no canonical rewrite;
- taker-field audit PASS;
- source sample reproducible;
- no outcome-based sample selection;
- no invalid/clamped ratios;
- feature manifest/hash;
- production/oracle reconciliation;
- source-grid quarantine;
- no post-cutoff.

## Sealed
- SEALED_EVALUATION_V1_1;
- Research Director scientific allocation authority;
- executor cannot self-authorize;
- BTC authorized=0;
- BTC consumed=0;
- sealed dataset not acquired;
- no sealed result.

## Search/algorithm
- novelty admission before market results;
- exact one economic hypothesis;
- exact two configs;
- zero numeric variants;
- exact 50% threshold only;
- exact non-overlapping 4h context rule;
- exact FLOW_CORE;
- exact FLOW_PRICE_RESPONSE;
- no breakout/SMA/persistence/pullback gate;
- exact 4 profiles/config;
- fixed 2/4/24 geometry;
- DEVELOPMENT_EVALUATION_V1 unchanged;
- preregistration before result;
- all negative evidence retained;
- no optimizer.

## Governance
- BTC only;
- LONG only;
- no leverage;
- no post-cutoff;
- no sealed BTC query;
- no paper;
- Champion NONE;
- real money false.

## Software
- backend tests;
- frontend tests/build;
- lint;
- format;
- typing;
- clean-checkout no-data check;
- installed-data check;
- clean tree.

Remote CI in executor report:
`PENDING_PUSH`

---

# 25. DEFAULT BRANCH HOUSEKEEPING

Remote default branch may still be the historical WP-001 branch.

Do not block WP-007.

If safe already-authenticated repo administration is available without new credentials, set default
branch to `main`.

Otherwise report PENDING.

Do not delete old branches.

---

# 26. COMMIT CHRONOLOGY

Recommended:

1. `docs: record WP-006 Research Director review and sealed authority correction`
2. `audit: validate canonical Binance taker fields`
3. `feat: add deterministic order-flow feature substrate`
4. `research: allocate and admit aggressive buy-flow family`
5. `feat: implement governed order-flow variants and tests`
6. `research: preregister order-flow variants`
7. `research: finalize order-flow development results`
8. `feat: expose order-flow and sealed research status`
9. `chore: complete WP-007 validation state and checkpoint`

Preserve scientific chronology.

---

# 27. CHECKPOINT

Create:

- `reports/checkpoints/WP-007.md`
- `reports/research/WP-007-ORDER-FLOW.md`
- `tasks/archive/WP-007.md`

Mark CURRENT_TASK completed only on structural completion.

---

# 28. ACCEPTANCE CRITERIA

WP-007 PASS requires:

1. exact start HEAD;
2. main only;
3. no branch;
4. no push;
5. clean tree;
6. WP-006 review recorded;
7. WP-006 real CI SUCCESS recorded;
8. current-state stale WP-005 CI fixed;
9. sealed authority prospectively corrected without query;
10. sealed authorized=0;
11. sealed consumed=0;
12. sealed data not acquired;
13. canonical dataset unchanged;
14. taker field audit PASS;
15. deterministic raw-source sample PASS;
16. invalid ratios not silently clipped;
17. order-flow derived substrate versioned;
18. independent oracle reconciliation PASS;
19. quarantine preserved;
20. no post-cutoff data;
21. SEARCH_MEMORY_V2 admission before results;
22. no classifier weakening/rename workaround;
23. one new economic hypothesis max;
24. two configs max;
25. zero numeric variants;
26. exact 0.5 balance threshold;
27. exact non-overlapping 4h context;
28. exact FLOW_CORE;
29. exact FLOW_PRICE_RESPONSE;
30. no price gate in CORE;
31. no breakout/SMA/pullback/persistence gate;
32. fixed stop/target/horizon;
33. exactly 4 profiles each;
34. no parameter optimization;
35. preregistration before result;
36. family conclusion follows CORE;
37. no result rewrite;
38. counters truthful;
39. sealed=0;
40. paper=0;
41. Champion NONE;
42. forward evidence NONE;
43. real money=false;
44. full installed-data validation PASS;
45. clean-checkout no-data validation PASS;
46. remote CI reported PENDING_PUSH;
47. profitability does not determine structural PASS.

---

# 29. REQUIRED EXECUTOR RESPONSE

Return only:

```text
WP-007: PASS | PARTIAL | FAIL

Branch:
HEAD:
Base reviewed HEAD:
Remote CI:
- PENDING_PUSH

WP-006 review:
- verdict:
- real CI evidence:
- stale WP-005 CI state fixed:

Sealed governance:
- version:
- authorization authority:
- authorized BTC queries:
- consumed BTC queries:
- dataset state:
- sealed query executed:

Order-flow substrate:
- version:
- canonical dataset unchanged:
- taker_base integrity:
- taker_quote integrity:
- zero-volume rows:
- source provenance sample:
- 1h eligible buckets:
- 4h eligible buckets:
- production/oracle reconciliation:
- artifact/manifest hash:

Search-memory admission:
- proposed family:
- CORE classification:
- PRICE_RESPONSE classification:
- admitted:
- prior family budgets unchanged:

Algorithm:
- primary:
- secondary:
- threshold searched:
- other parameters searched:
- profiles executed:

Evaluation:
- FLOW_CORE: <classification, default R, trades, nonnegative folds, min-fold trades>
- FLOW_PRICE_RESPONSE: <classification, default R, trades, nonnegative folds, min-fold trades>
- CORE ZERO:
- CORE DOUBLE:
- CORE DELAY:
- concentration/stability:

Comparison:
- vs random:
- vs trend:
- vs breakout:
- vs ALIGNED:
- vs pullback core:
- interpretation: <one concise sentence>

Sealed eligibility:
- ALIGNED:
- PULLBACK_CORE:
- FLOW_CORE:
- FLOW_PRICE_RESPONSE:
- sealed query executed: NO

Scientific accounting:
- strategy experiments=<truth>
- material economic hypotheses=<truth>
- configurations=<truth>
- profile/seed trials=<truth>
- numeric parameter variants=0
- adaptive decisions=<truth>
- result-dependent forks=<truth>
- sealed_evaluations=0
- sealed_queries=0
- paper_trades=0
- champion=NONE
- forward_evidence=NONE
- real_money=false

Validation:
- <one concise line>

Forbidden-work check:
- ALIGNED modification: absent
- pullback rescue: absent
- breakout reopening: absent
- optimizer/search: absent
- post-cutoff access: absent
- sealed BTC access: absent
- non-BTC assets: absent
- SHORT/leverage: absent
- paper trading: absent
- real-money functionality: absent
- new branch: absent

External housekeeping:
- default branch main: DONE | PENDING

Material deviations:
- none
  OR
- <only material deviations>

Next recommendation:
- <one sentence; no automatic sealed query or Champion promotion>
```

Do not paste raw logs unless PARTIAL/FAIL and essential for diagnosis.
