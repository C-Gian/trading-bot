# G2-02 Baseline and Diagnostics V1

Status: **AUTHORIZED EXPOSED DEVELOPMENT — G2-V0 BASELINE ONLY; NO ADAPTIVE REVISION**

## Read first

1. `AGENTS.md`
2. `state/current_state.json -> current_project_status` and `g2_development_system`
3. `tasks/CURRENT_TASK.md`
4. this file
5. `research/g2/G2_DEVELOPMENT_PROTOCOL_V1.md`
6. `docs/canonical/G2_FORECAST_POLICY_EXECUTION_CONTRACTS_V1.md`
7. `reports/reviews/G2-01-GATE-B-REREVIEW-V1.md`
8. `docs/operations/LONG_RUNNING_JOB_PROGRESS_V1.md`

Do not bulk-read historical Markdown.

## Objective

Execute the first non-adaptive exposed G2 development batch:

- G2-V0 baseline;
- the four frozen references;
- the two predeclared diagnostic ablations.

Then stop for Research Director interpretation.

Do **not** design or execute G2-R1/R2/R3/G2-RCYCLE in this task.

## Exposure

Initialization/training history:
- 2020-01-01 through 2020-12-31 exposed.

Scored exposed-development sandbox:
- 2021-01-01 through 2024-12-31.

Strictly forbidden:
- any 2025+ market observation;
- protected evaluation;
- future-paper collection;
- real orders/capital.

The phase-bounded loader remains mandatory.

## Before opening economic outcomes

### A. Implement generic long-job progress

Implement `docs/operations/LONG_RUNNING_JOB_PROGRESS_V1.md`.

At minimum instrument:
- `scripts/check.py --progress`;
- the G2-02 development runner.

Add a small read-only operations API/UI so the Owner can inspect an active job from the local app.

Progress files/logs are git-ignored runtime telemetry and never scientific evidence.

### B. Freeze the development run

Before the first economic execution append a real-UTC ledger authorization record containing:
- package/version;
- code/data/filter snapshot hashes;
- exposed interval;
- G2-V0 baseline identity;
- four reference identities;
- ABL-G2-01 and ABL-G2-02 identities;
- scorecard definitions;
- uncertainty seed/block rules;
- explicit statement that no adaptive revision is authorized.

No rounded/invented timestamps.

### C. Pre-execution deterministic validation

Run only focused deterministic tests needed to establish that the new development scorer/runner
implements the already frozen protocol.

Do not run market economics while fixing these tests.

## Executed systems

### Main baseline

`G2-V0` exactly as frozen at Gate A/B.

No parameter, feature, threshold, cost, risk or cycle change.

### Fixed references

Exactly:
1. `NULL_FORECAST`;
2. `TREND_ONLY_FORECAST`;
3. `TREND_REFERENCE_POLICY`;
4. `CASH_REFERENCE`.

Definitions come only from the frozen G2 forecast/policy/execution contract. Do not tune them.

### Diagnostic ablations

Exactly:

`ABL-G2-01 — FULL_MINUS_PARTICIPATION_FLOW_RESPONSE`
- remove RELATIVE_PARTICIPATION;
- remove TAKER_IMBALANCE;
- remove LOCAL_STRUCTURE_X_PARTICIPATION;
- remove IMBALANCE_X_PRICE_RESPONSE;
- same ridge/fit calendar/window/penalties.

`ABL-G2-02 — FULL_ADDITIVE_ONLY`
- retain six main observables;
- remove both interaction terms;
- same ridge/fit calendar/window/penalties.

Ablations are diagnostic only and cannot be promoted directly.

## Required scorecards

Implement exactly the protocol scorecards.

Forecast:
- mean CRPS primary;
- q10/q50/q90 pinball;
- Brier sign;
- q10-q90 coverage;
- median MAE;
- descriptive direction hit rate;
- fixed strength/evidence strata;
- availability/support.

Policy:
- common-timeline simulated portfolio net return relative cash primary;
- mean realized NET_R;
- total net return;
- max drawdown/time under water;
- turnover;
- occupancy/capital time;
- LONG/SHORT mix;
- cost/funding share;
- trade count and temporal distribution;
- NO_TRADE reasons;
- standardized LONG/SHORT shadow-payoff distributions.

Execution:
- decision-to-fill delay;
- raw/accounting fills;
- friction;
- funding;
- gap/ambiguous/rejected/unavailable counts.

References and ablations receive the applicable same scorecards.

## Uncertainty

For eligible comparisons:
- common UTC week blocks;
- paired contributions where meaningful;
- 5,000 complete-week bootstrap replicates;
- seed `2026092702`;
- point delta plus 10th/50th/90th percentiles.

Do not call this independent validation or a discovery p-value.

## Autopsy

After the fixed batch is complete, create deterministic diagnostic/autopsy artifacts following
G2_DEVELOPMENT_PROTOCOL_V1 §§16-17.

Include:
- favorable episodes;
- unfavorable episodes;
- deterministic pseudo-random episodes;
- NO_TRADE/missed standardized opportunities;
- data/execution anomalies;
- FACT -> CAUSAL HYPOTHESIS -> REQUIRED TEST separation.

Do not modify G2-V0 based on the autopsy in this task.

## Zero-volume observation

The 332 zero-volume exposed minutes and 16 post-warmup unavailable decision instants are retained
under frozen V0 semantics.

Report them as coverage/data-quality diagnostics.

Do not reclassify, delete, interpolate or create a new rule in this task.

## Outputs

Create deterministic versioned artifacts under:
- `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/`;
- `reports/validation/`;
- `reports/checkpoints/`.

The canonical result must clearly distinguish:
- G2-V0;
- each fixed reference;
- each diagnostic ablation;
- forecast/policy/execution scorecards;
- uncertainty;
- coverage;
- autopsy;
- data/execution failures;
- exact manifests/hashes.

Append ledger records for each executed version/reference/ablation.

## Long-run UX

The economic batch itself must expose:
- job/phase status;
- progress through calendar/run units;
- elapsed;
- heartbeat;
- ETA when defensible;
- log tail through the local Operations surface.

The Owner must be able to tell whether the run is progressing without asking the executor.

## Validation efficiency

During implementation use focused tests.

Run the full `python scripts/check.py --progress` only on the intended final code/artifact state,
except when a failed final run genuinely requires another final verification.

Do not repeatedly run the full suite for small allowlist/test-title fixes.

## Completion

Leave:
`EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_G2_02_REVIEW`.

Do not:
- create a revision change card;
- execute R1/R2/R3/RCYCLE;
- access 2025+;
- declare a candidate/Champion;
- enable paper trading;
- change production NO_TRADE;
- authorize real money.

The Research Director will interpret the complete fixed batch and decide the next development
allocation.
