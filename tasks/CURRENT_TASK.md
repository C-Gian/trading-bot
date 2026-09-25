# CURRENT TASK — SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1

Status: SYNTHETIC_METHOD_VALIDATION_AUTHORIZED — MARKET OUTCOMES FORBIDDEN

## Authority

- ADR-0045:
  `decisions/ADR-0045-ACCEPT-G1-CHECKPOINT-1-AND-FREEZE-CYCLE-QUALITY-GATE.md`
- Frozen quality protocol:
  `research/protocols/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.md`
- Cycle method:
  `research/protocols/SYSTEM-G1-CYCLE-METHOD-V1.md`
- System architecture:
  `docs/canonical/PROFESSIONAL_MULTISIGNAL_SYSTEM_ARCHITECTURE_V1.md`

Checkpoint 1 infrastructure is accepted by the Research Director.

This task is a **small synthetic method gate**, not System G1 historical development.

## Objective

1. Implement the already-frozen cycle quality labels.
2. Run the frozen multi-seed synthetic quality gate.
3. Correct the System G1 primary operational-delay default from 0m to the architecture's frozen 1m.
4. Stop for Research Director review.

Do not inspect any real BTC market outcome.

## Mandatory read set

Read only:

1. `AGENTS.md`
2. `tasks/CURRENT_TASK.md`
3. ADR-0045
4. cycle method contract
5. cycle synthetic quality-gate protocol
6. Checkpoint-1 cycle implementation / diagnostics / tests
7. smallest ledger/tests needed for delay correction

Do not reopen broad historical research.

## Cycle quality implementation

Implement exactly:

### UNAVAILABLE

- normal warm-up incomplete; or
- active gap/re-warm; or
- dominant period unavailable; or
- causal projection unavailable.

### USABLE

All required:

- otherwise available;
- `explained_fraction >= 0.90` on current scale input bar;
- `explained_fraction >= 0.90` on each immediately preceding two completed input bars;
- no gap/reset in that three-bar persistence window.

### WEAK

Available but not USABLE.

No other quality metric may influence the label.

Do not change the 0.90 threshold or 3-bar persistence.

## Synthetic gate execution

Execute exactly the frozen ensembles/protocol.

Minimum per scale:

- 128 independent deterministic white-noise paths;
- 48 clean-cycle paths spanning lower/mid/upper band with deterministic phase variation;
- 48 trend+cycle paths with the same period/phase structure;
- preserve the existing non-gating mixture, amplitude-decay, abrupt-change and missing-data
  diagnostics.

Record all seeds/configuration identities.

Mandatory pass criteria are exactly those in
`SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.md`.

Do not search alternative thresholds or quality features if a gate fails.

## Cycle activation prohibition

Even if every synthetic gate passes:

- do NOT set `CYCLE_DECISION_ACTIVATION = True`;
- do NOT let cycle raise conviction;
- do NOT modify P1/P2 decisions.

A PASS is only:

`CYCLE_SYNTHETIC_QUALITY_GATE_PASS_PENDING_RESEARCH_DIRECTOR_ACTIVATION`.

The Research Director must inspect the artifact before activation.

## Primary delay correction

System G1 architecture froze one-minute primary operational delay after required inputs are ready.

Change the G1 primary/default policy from 0 to **1 minute**.

Required:

- default RiskPolicy delay = 1m;
- synthetic plans created under default G1 policy inherit 1m;
- exact next-eligible-minute semantics remain causal;
- update tests and version strings/identities affected by this scientific contract correction;
- existing legacy/frozen historical engines remain untouched.

The later robustness delay stress remains +5m relative to primary.

Do not alter cost rates or risk limits.

## Artifacts

Create:

- `reports/research/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.json`;
- concise checkpoint Markdown;
- deterministic replay/check command.

Artifact must include:

- frozen rule identity/hash;
- method/code identity;
- every scale's noise median/p95 occupancy;
- clean and trend+cycle median/p10 occupancy;
- period-error metrics;
- integrity results;
- PASS/FAIL per gate/scale;
- final mechanical disposition;
- confirmation that no market data was read.

## Post-task state

On completion:

- Checkpoint 1 remains reviewed/accepted;
- cycle remains inactive in decisions;
- cycle quality gate result recorded;
- historical market trial authorized = false;
- P1/P2 performance computed = false;
- forecaster fitted = false;
- validated strategy = null;
- production output = NO_TRADE;
- no prospective collection;
- sealed queries = 0;
- Champion NONE;
- real money false;
- next task = Research Director cycle-quality adjudication.

Archive this task and leave CURRENT_TASK review-only.

## Validation

Run:

- focused cycle synthetic tests/gate replay;
- ledger delay tests;
- existing G1 synthetic tests;
- ruff;
- mypy;
- full backend/frontend tests;
- `scripts/check.py --no-data`.

Do not run a data-mode check.

## Git

Local commits on main are authorized after validation.

Do not push.

## Completion report

Return only:

`SYSTEM_G1_CYCLE_QUALITY_RESULT_PENDING_RESEARCH_DIRECTOR_ADJUDICATION`

Then:

- cycle_quality_disposition
- changed_files
- local_commit_sha(s)
- frozen_rule_identity: PASS/FAIL
- per_scale_noise_occupancy_median_p95
- per_scale_clean_occupancy_median_p10
- per_scale_trend_cycle_occupancy_median_p10
- per_scale_period_error
- integrity_gates: PASS/FAIL
- primary_delay_default: 1m PASS/FAIL
- cycle_active_in_decisions: NO
- synthetic_validation: PASS/FAIL
- full_no_data_validation: PASS/FAIL
- real_historical_g1_outcomes_inspected: NO
- new_market_data_accessed: NO
- sealed_queries: 0
- validated_strategy: NONE
- operational_action: NO_TRADE
- champion: NONE
- real_money: false
- blockers: concise only
