# CURRENT TASK — WP-008
# Leakage-Safe Linear Supervised Challenger + Research Artifact Scaling

## STATUS
ACTIVE

## EXECUTOR
Primary: Codex.
Fallback/overflow: Claude Code if Codex usage is unavailable.
This task is executor-neutral. Scientific truth lives in repository artifacts.
ChatGPT / GPT-5.6 Sol remains Research Director and final scientific authority.
Astra Ultra is NOT allocated to WP-008.

---

# 0. RESEARCH DIRECTOR DECISION

WP-007 is independently accepted.

Verified remote facts:
- final HEAD: `762b3b77f686305b1c73f19956d0b9b16b7a9b1c`
- true base / merge base: `d92088d5ef0426bf64f34326a3224dd9aba93603`
- WP-007 is 16 commits ahead / 0 behind;
- GitHub Actions `check`, run `34375244463`, completed SUCCESS;
- effective preregistration-v2 commit: `e541da5db097d322a10d9f7666973a2f4829a0c2`
- result commit: `d5fd0bcbc5fc0f6aaae42ebba721ba55c9447ac3`
- result commit has the effective preregistration commit as direct parent;
- order-flow canonical/source integrity PASS;
- SEARCH_MEMORY_V2 admitted FLOW_CORE as NEW_FAMILY before results;
- SEALED_EVALUATION_V1_1 remains locked at 0 authorized / 0 consumed BTC queries;
- no post-cutoff BTC data acquired or inspected.

Scientific result:
`FAM-ORDER-FLOW = REJECT_COST_DOMINATED`

FLOW_CORE:
- default expectancy `-0.0667167056 R`
- zero-cost `+0.0533577522 R`
- double-cost `-0.1867911419 R`
- delay `-0.0619009982 R`
- resolved trades `1,828`
- nonnegative folds `1/6`
- minimum-fold trades `241`

This is adequately sampled and economically negative under realistic friction.
Do NOT rescue FAM-ORDER-FLOW by moving the 0.5 threshold or adding filters.

---

# 1. WHY WP-008 CHANGES THE RESEARCH METHOD

The lab has now tested five material economic hypotheses and thirteen configurations:
- trend;
- breakout;
- selective aligned continuation;
- pullback recovery;
- taker-flow transition.

Repeated observation: several simple mechanisms are positive gross / zero-cost but fail or weaken
materially after realistic costs.

ALIGNED remains the strongest exposed-development clue, but is INCONCLUSIVE and its family budget
is exhausted.

Continuing to hand-invent deterministic patterns risks the exact circular search the Owner forbade.

The Scientific Constitution says:
- prefer simple deterministic baselines before complex models;
- machine learning is a challenger family, not a prerequisite;
- record adaptive search/trial burden;
- do not win by trying strategies until one looks good.

WP-008 therefore authorizes ONE simple interpretable supervised challenger:
a low-dimensional deterministic linear model trained only on historical data before each validation
fold, with a frozen feature set and zero tuning.

No model zoo.

---

# 2. REQUIRED START

Repository: `C-Gian/trading-bot`
Branch: `main`
Required starting HEAD:
`762b3b77f686305b1c73f19956d0b9b16b7a9b1c`

Reviewed predecessor:
`d92088d5ef0426bf64f34326a3224dd9aba93603`

Do not create a branch.
Do not rewrite history.
Do not push.

---

# 3. RECORD WP-007 RESEARCH DIRECTOR REVIEW

Create:
`reports/reviews/WP-007-RESEARCH-DIRECTOR-REVIEW.md`

Verdict:
`ACCEPTED`

Record:
- exact base/head ancestry;
- real remote CI SUCCESS run 34375244463;
- effective preregistration/result chronology;
- two zero-result pre-execution tooling corrections;
- order-flow integrity PASS;
- canonical dataset unchanged;
- SEARCH_MEMORY chronology;
- SEALED_EVALUATION_V1_1 locked at zero;
- FAM-ORDER-FLOW = REJECT_COST_DOMINATED;
- FLOW_PRICE_RESPONSE does not replace FLOW_CORE;
- no threshold rescue;
- Champion NONE;
- sealed=0;
- paper=0;
- real money=false.

Update authoritative current remote CI truth:
- WP-005 SUCCESS
- WP-006 SUCCESS
- WP-007 SUCCESS

Do not rewrite historical executor reports.

---

# 4. SCIENTIFIC START STATE

Expected:
- experiments_completed = 13
- material_economic_hypotheses = 5
- configuration_variants = 13
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

---

# 5. FORBIDDEN WORK

Do NOT:
- modify/reopen ALIGNED or FAM-BREAKOUT;
- rescue pullback recovery;
- rescue order-flow thresholds;
- test contraction-to-expansion;
- invent a second model family;
- compare many algorithms;
- use neural nets, trees, random forest, XGBoost, boosting, SVM or k-NN;
- feature-select based on observed results;
- search regularization;
- search signal thresholds;
- search feature subsets;
- add interactions after results;
- PCA;
- automated feature generation;
- grid/random/Bayesian/evolutionary optimization;
- random K-fold;
- change fold boundaries;
- change stop/target/horizon;
- access BTCUSDT after `2024-12-31T23:59:00Z`;
- acquire/query sealed BTC data;
- use other assets;
- SHORT;
- leverage/perpetuals;
- paper trade;
- enable Analyze Market;
- product LONG/NO_TRADE output;
- Champion promotion;
- real-money/exchange execution;
- create a branch;
- push.

---

# 6. STAGE A — RESEARCH ARTIFACT STORAGE V1

Do NOT delete/rewrite/migrate historical experiment evidence.

Prospectively create:
`docs/contracts/RESEARCH_ARTIFACT_STORAGE_V1.md`

For WP-008 onward:

## Keep as compact tracked text
- preregistrations;
- configs/specs;
- allocations/admissions;
- result summaries;
- fold summaries;
- reports;
- artifact manifests/hashes;
- state/checkpoints.

## High-volume row artifacts
Do NOT emit enormous pretty-printed JSON.

Executed trial/trade rows:
- deterministic ZSTD-compressed Parquet;
- explicit fixed schema;
- deterministically sorted;
- file SHA-256;
- logical row-content SHA-256;
- result summary references exact path/hash.

Training matrices / training labels:
- do NOT commit row-by-row matrices to Git;
- commit only deterministic manifests containing:
  - fold;
  - schema/features;
  - row count;
  - min/max signal timestamp;
  - exclusions;
  - logical hash;
  - feature/label code hash;
  - regeneration command.

Historical JSON remains untouched.

Add validation.

---

# 7. STAGE B — SUPERVISED CHALLENGER CONTRACT

Create:
`docs/contracts/SUPERVISED_CHALLENGER_V1.md`

Create frozen protocol:
`research/protocols/WP-008-LINEAR-NET-R-V1.json`

At each eligible hourly signal timestamp:
- compute features using completed information available by signal time;
- for TRAINING ONLY compute an isolated fixed-plan DEFAULT-cost net-R label;
- fit one deterministic linear model using only historical training rows;
- predict default net R on future validation rows;
- LONG iff `predicted_default_net_R > 0.0`.

No threshold search.

---

# 8. STAGE C — EXACT TRAINING LABEL

Target:
`ISOLATED_FIXED_PLAN_DEFAULT_NET_R_V1`

At eligible signal boundary t:
- reference = just-completed 1h close;
- entry = next canonical 1m open;
- stop = reference * 0.98;
- target = reference * 1.04;
- horizon = 1,440 minutes;
- execution = BACKTEST_ENGINE_V2 / EXECUTION_MODEL_V2;
- cost = BTCUSDT_SPOT_COST_V1;
- do NOT apply position occupancy to label generation.

Label = isolated hypothetical plan's realized DEFAULT-cost `net_r`.

Invalid/unresolved/missing future path labels:
- exclude from fitting;
- count explicitly;
- never impute.

No clipping/winsorization.

The production strategy later applies normal single-position occupancy.

---

# 9. STAGE D — EXPANDING CHRONOLOGICAL TRAINING

Use the fixed six annual validation folds:
2019, 2020, 2021, 2022, 2023, 2024.

For validation year Y:
training signals may only occur up to:

`validation_start - 216 hours`

Use an expanding window from earliest eligible development history.

Because labels use at most 24h of future path, this leaves at least 192h between the latest possible
training outcome and validation start.

No validation-year information may enter:
- scaling;
- fitting;
- label creation;
- feature selection;
- threshold;
- model specification.

Persist exact per fold:
- training start/end;
- max training label outcome timestamp;
- validation start/end;
- fit rows;
- exclusions;
- hashes.

Hard-fail if any training label outcome overlaps validation.

---

# 10. STAGE E — EXACT FROZEN FEATURE SET

No feature may be added/removed after seeing WP-008 market results.

## F1 LOG_RETURN_1H
`ln(current_1h_close / current_1h_open)`

## F2 LOG_RETURN_24H
`ln(current_1h_close / close_24_hours_earlier)`

## F3 LOG_DISTANCE_TO_PRIOR_24H_HIGH
`ln(current_1h_close / max(high of previous 24 completed 1h bars excluding current))`

## F4 REALIZED_VOL_24H
Exactly 24 contiguous completed close-to-close hourly log returns ending at current close:
`sqrt(mean(r_i^2))`
No annualization.

## F5 LOG_RELATIVE_VOLUME_1H
`ln(current completed 1h base volume / arithmetic mean(previous 24 completed 1h base volumes excluding current))`
Require numerator and denominator >0; otherwise ineligible.

## F6 DIRECTIONAL_EFFICIENCY_4H
Use 42 close-to-close changes from 43 completed 4h closes on the latest completed NON-OVERLAPPING
4h context whose close <= t-1h.

Let U=sum positive changes; D=absolute sum negative changes.
`(U-D)/(U+D)`.
If U+D=0, ineligible.
Do NOT apply the old 2:1 gate.

## F7 TAKER_BUY_SHARE_1H_CENTERED
`current_1h_taker_buy_base_share - 0.5`

## F8 TAKER_BUY_SHARE_4H_CENTERED
`nonoverlapping_context_4h_taker_buy_base_share - 0.5`

Use ORDER_FLOW_FEATURES_V1 for F7/F8.

All windows must be complete/contiguous and respect quarantine.

---

# 11. STAGE F — FEATURE / LABEL LEAKAGE AUDIT

Create version:
`SUPERVISED_FEATURES_V1`

Create:
`reports/validation/WP-008-SUPERVISED-LEAKAGE-AUDIT.json`

Prove:
- every feature is available by signal time;
- current-hour features use a completed bar;
- 4h context is completed and non-overlapping;
- no forward fill;
- source-grid quarantine preserved;
- no post-cutoff;
- scaling is training-only;
- labels are training-only;
- latest training outcome precedes validation;
- validation outcomes never fit model;
- no full-history normalization;
- no result-conditioned feature selection.

Add synthetic future-feature injections that must be rejected.

Persist training/validation manifests and logical hashes.

---

# 12. STAGE G — MODEL FAMILY

Proposed root:
`FAM-SUPERVISED-LINEAR`

Hypothesis:
`LINEAR_NET_R_SELECTION_V1`

Claim:

A fixed low-dimensional linear combination of already-governed price, volatility, volume, regime
and taker-flow descriptors can estimate default-cost LONG opportunity quality well enough that
observations with predicted net R >0 produce robust positive realized net expectancy after realistic
execution costs.

This is predictive, not a causal claim.

---

# 13. STAGE H — EXACT MODEL

Use deterministic ordinary least squares with intercept.

No regularization/hyperparameter.

For each fold/configuration:

1. build training X/y;
2. calculate training-only mean/std (`ddof=0`);
3. hard-fail if any std <= 1e-12;
4. standardize X;
5. fit `y = intercept + beta^T z` using deterministic float64 least squares;
6. require full column rank;
7. record condition number;
8. save intercept, coefficients, train means/stds, feature order, matrix/label hashes and dependency hash;
9. apply model only to that fold's validation rows.

Use the already-pinned NumPy dependency.
Do not add scikit-learn.

No coefficient thresholding.
No feature dropping.
No validation refit.

---

# 14. STAGE I — EXACT TWO CONFIGURATIONS

## LINEAR_FULL — PRIMARY
Features F1-F8 exactly.

Preselected family primary.

## LINEAR_NO_FLOW — STRUCTURAL ABLATION
Features F1-F6 exactly.

Purpose:
measure the incremental contribution of taker-flow descriptors within the identical supervised
architecture.

No other feature subset.

Family conclusion always follows LINEAR_FULL.

---

# 15. STAGE J — SEARCH_MEMORY_V2 ADMISSION

Before market results create executable/model specifications binding:

- model family/algorithm;
- feature order;
- feature transformations;
- label;
- expanding training rule;
- scaling;
- signal threshold;
- execution geometry;
- data/cost versions;
- code dependencies.

Submit to SEARCH_MEMORY_V2.

Expected:
- LINEAR_FULL = NEW_FAMILY;
- LINEAR_NO_FLOW = structural ablation/descendant.

If primary is duplicate / near-duplicate / parameter variant / conflicting root:
- preserve rejection;
- do not weaken/rename;
- do not run validation market results;
- WP-008 research stage PARTIAL.

---

# 16. STAGE K — RESEARCH ALLOCATION

Create:
`WP008-LINEAR-SUPERVISED-ALLOCATION`

This is one adaptive/result-dependent research decision.

Authorize exactly:

- economic hypotheses = 1
- model configurations = 2
- numeric hyperparameter variants = 0
- signal-threshold variants = 0
- algorithm variants = 0
- profiles/configuration = 4

Profiles:
- DEFAULT
- ZERO
- DOUBLE
- DELAY_1H

Total strategy profile evaluations: 8.

Track separately:
`supervised_model_fits = 12` (6 folds x 2 configs).

Learned coefficients are model outputs, not searched numeric variants.

---

# 17. STAGE L — SIGNAL / EXECUTION

For each validation row t:

Use only the fold's historical model.

Signal iff:
`predicted_default_net_R > 0.0`

If signal and flat:
- reference = current completed 1h close;
- enter next canonical 1m open;
- stop = reference*0.98;
- target = reference*1.04;
- max hold 1440m;
- normal occupancy;
- normal invalid/unresolved/gap policy.

Training labels do not bypass the production execution engine.

---

# 18. STAGE M — ROBUSTNESS PROFILES

Train ONCE per fold/configuration using DEFAULT-cost labels.

Do NOT retrain for stress profiles.

DEFAULT:
normal cost V1.

ZERO:
same model + same undelayed prediction timestamps; zero cost.

DOUBLE:
same model + same undelayed prediction timestamps; doubled cost.

DELAY_1H:
at t use the prediction generated from the exact feature vector available at t-1h with the same
fold model; if lagged prediction >0 signal at t; reference is current completed 1h close at t.

No other delays.

---

# 19. STAGE N — PREDECLARED SECONDARY DIAGNOSTICS

For each fold/configuration report only as secondary diagnostics:

- fit row count;
- invalid/unresolved label exclusions;
- validation eligible count;
- prediction-positive count;
- emitted trade count;
- validation isolated-label Pearson correlation with prediction;
- mean prediction;
- mean isolated realized R for prediction-positive rows;
- coefficient vector;
- coefficient sign consistency across folds;
- condition number.

Do NOT use these to:
- change features;
- change threshold;
- select NO_FLOW as primary;
- create post-hoc bins/deciles for a new strategy.

---

# 20. STAGE O — TERMINAL CLASSIFICATION

Use unchanged:
`DEVELOPMENT_EVALUATION_V1`

Possible:
- INCONCLUSIVE
- REJECT_COST_DOMINATED
- REJECT
- REJECT_UNSTABLE
- PROMISING_DEVELOPMENT_ONLY

Classification is based on actual executed validation trades.

Family result follows LINEAR_FULL.

No special favorable ML threshold.

Even if PROMISING:
- no Champion;
- no sealed query;
- no paper trade.

---

# 21. STAGE P — PREREGISTRATION CHRONOLOGY

Before any validation market result:

1. storage contract implemented;
2. feature/label code implemented;
3. leakage tests PASS;
4. model implementation complete;
5. executable specs frozen;
6. commit implementation;
7. SEARCH_MEMORY admission committed;
8. allocation committed;
9. both preregistrations created;
10. preregistrations committed;
11. only then fit final fold models and execute validation results.

Suggested experiment IDs:
- `EXP-ML-014-LINEAR-NET-R-FULL`
- `EXP-ML-015-LINEAR-NET-R-NO-FLOW`

A true pre-result tooling bug may be corrected prospectively only with originals preserved and zero
results observed.

If any validation result has been observed:
no material feature/model/threshold correction in the same allocation.

---

# 22. STAGE Q — INDEPENDENT RECONCILIATION

Create:
`reports/validation/WP-008-MODEL-RECONCILIATION.json`

Independent of the main high-level orchestration path, verify:

- fold train boundaries;
- label horizon containment;
- feature order;
- training-only scaling;
- model coefficient reproduction;
- prediction hashes;
- emitted signal timestamps;
- DEFAULT trade metrics from compact trial artifact.

Do not let the primary runner be its only validator.

---

# 23. STAGE R — RESEARCH REPORT

Create:
`reports/research/WP-008-LINEAR-CHALLENGER.md`

Compare descriptively with:
- random;
- SMA trend;
- breakout;
- ALIGNED;
- pullback recovery;
- order-flow;
- no-trade.

Questions:
- does the learned combination survive costs?
- doubled costs?
- fold stability?
- coefficient stability?
- does NO_FLOW differ materially?
- does the model merely learn broad BTC long drift?
- does delay materially change behavior?
- is one year dominant?
- does this improve on the strongest manual clue or merely rearrange exposed-development noise?

No post-result feature change.

---

# 24. STAGE S — ANTI-LOOP ML GOVERNANCE

Extend SEARCH_MEMORY so future model proposals fingerprint:

- algorithm;
- label;
- features;
- transformations;
- train-window rule;
- scaling;
- regularization/hyperparameters;
- signal threshold;
- execution geometry;
- data/cost versions.

Future logistic regression, feature changes, threshold changes, regularization, labels, etc. must be
classified relative to this family and consume explicit budget.

Annual fitted coefficient vectors are not separate hypotheses.

Add duplicate/parameter-drift tests.

---

# 25. STAGE T — SEALED ELIGIBILITY

SEALED_EVALUATION_V1_1 remains:
- authorized=0
- consumed=0
- dataset RESERVED_NOT_ACQUIRED

No query in WP-008.

If LINEAR_FULL becomes PROMISING_DEVELOPMENT_ONLY:
mark only:
`DEVELOPMENT_ELIGIBLE_PENDING_RESEARCH_DIRECTOR_SEALED_ALLOCATION`

No automatic query.

---

# 26. STAGE U — UI/API

Only modest research inspection.

Research Lab may show:
- supervised challenger status;
- fold model count;
- terminal classification;
- artifact-storage version;
- SEALED locked 0/0;
- Champion NONE.

Dashboard remains PAPER ONLY / Analyze Market disabled / no product signal.

---

# 27. STAGE V — STATE

If both experiments execute:

Expected cumulative:
- experiments_completed = 15
- material_economic_hypotheses = 6
- configuration_variants = 15
- profile_trials = 77
- numeric_parameter_variants = 0
- adaptive_decisions = 5
- result_dependent_forks = 5
- supervised_model_fits = 12
- sealed_queries = 0
- sealed_evaluations = 0
- paper_trades = 0
- Champion = NONE
- forward evidence = NONE
- real money = false

Add:
- artifact storage version;
- supervised challenger version;
- latest family/model classification;
- WP-007 remote CI SUCCESS;
- next recommended checkpoint.

If blocked, keep truthful counters.

---

# 28. STAGE W — VALIDATION

Strengthen `python scripts/check.py`.

Validate:

Repository/review:
- exact starting HEAD;
- main only;
- WP-007 CI SUCCESS evidence;
- review recorded;
- historical evidence unchanged.

Artifact scaling:
- historical JSON untouched;
- WP-008 detailed trials use deterministic compressed Parquet;
- file/logical hashes;
- no training matrices committed row-by-row.

Feature/label:
- exact F1-F8;
- NO_FLOW removes exactly F7/F8;
- no future access;
- 4h non-overlap;
- quarantine/gaps;
- no post-cutoff;
- training-only scaling;
- exact isolated label;
- invalid/unresolved labels counted;
- train label outcomes before validation;
- no random K-fold.

Model:
- OLS+intercept only;
- no regularization search;
- exact two configs;
- FULL primary;
- threshold exactly >0;
- no threshold variants;
- 12 fits exactly;
- full-rank/condition audit;
- no validation refit.

Chronology:
- implementation before prereg;
- admission before results;
- prereg before results;
- no material post-result change.

Evaluation:
- four profiles/config only;
- no stress-profile retrain;
- fixed geometry;
- DEVELOPMENT_EVALUATION_V1 unchanged;
- deterministic classification.

Governance:
- counters truthful;
- BTC only;
- LONG only;
- no leverage;
- no sealed;
- no paper;
- Champion NONE;
- real money false;
- no optimizer/model zoo.

Software:
- backend tests;
- frontend tests/build;
- lint;
- format;
- typing;
- installed-data validation;
- clean-checkout no-data;
- clean tree.

Remote CI executor status:
`PENDING_PUSH`

---

# 29. DEFAULT BRANCH HOUSEKEEPING

Remote default branch may still be historical WP-001.

Do not block WP-008.

If safe already-authenticated repo administration exists without new credentials, set default to
main. Otherwise report PENDING.

Do not delete historical branches.

---

# 30. COMMIT CHRONOLOGY

Recommended:

1. `docs: record WP-007 Research Director acceptance`
2. `feat: add scalable research artifact storage`
3. `feat: add leakage-safe supervised feature and label substrate`
4. `research: allocate and admit linear supervised challenger`
5. `feat: implement deterministic foldwise linear model`
6. `research: preregister WP-008 linear challengers`
7. `research: finalize WP-008 walk-forward results`
8. `feat: expose supervised research status`
9. `chore: complete WP-008 state validation and checkpoint`

Do not squash scientific chronology.

---

# 31. CHECKPOINT

Create:
- `reports/checkpoints/WP-008.md`
- `reports/research/WP-008-LINEAR-CHALLENGER.md`
- `tasks/archive/WP-008.md`

Mark CURRENT_TASK completed only on structural completion.

---

# 32. REQUIRED EXECUTOR RESPONSE

Return only:

```text
WP-008: PASS | PARTIAL | FAIL

Branch:
HEAD:
Base reviewed HEAD:
Remote CI:
- PENDING_PUSH

WP-007 review:
- verdict:
- real CI evidence:
- chronology:
- order-flow family disposition:

Artifact storage:
- version:
- historical evidence rewritten:
- new trial artifact format:
- training matrices committed:
- deterministic artifact validation:

Supervised substrate:
- version:
- target:
- features FULL:
- features NO_FLOW:
- training fold rule:
- leakage audit:
- training-label exclusions:
- feature/label manifest hashes:

Search-memory admission:
- proposed family:
- FULL classification:
- NO_FLOW classification:
- admitted:
- prior budgets unchanged:

Model:
- algorithm:
- primary:
- secondary:
- hyperparameters searched:
- thresholds searched:
- model fits:
- full-rank/conditioning:

Evaluation:
- LINEAR_FULL: <classification, default R, trades, nonnegative folds, min-fold trades>
- LINEAR_NO_FLOW: <classification, default R, trades, nonnegative folds, min-fold trades>
- FULL ZERO:
- FULL DOUBLE:
- FULL DELAY:
- prediction/label OOS diagnostics:
- concentration/stability:

Comparison:
- vs random:
- vs trend:
- vs breakout:
- vs ALIGNED:
- vs pullback:
- vs order-flow:
- interpretation: <one concise sentence>

Sealed eligibility:
- ALIGNED:
- LINEAR_FULL:
- LINEAR_NO_FLOW:
- authorized BTC queries: 0
- consumed BTC queries: 0
- sealed query executed: NO

Scientific accounting:
- strategy experiments=<truth>
- material economic hypotheses=<truth>
- configurations=<truth>
- profile/seed trials=<truth>
- supervised model fits=<truth>
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
- hand-strategy rescue: absent
- feature search: absent
- model zoo: absent
- hyperparameter optimization: absent
- threshold optimization: absent
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
