# CURRENT TASK — EXECUTE-CANDIDATE-1-DEVELOPMENT-V1

Status: SINGLE_FROZEN_DEVELOPMENT_EXECUTION_AUTHORIZED

## Authority

- Frozen protocol: `research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md`
- Protocol freeze: `decisions/ADR-0039-CANDIDATE-1-DEVELOPMENT-PROTOCOL-FREEZE.md`
- Execution authorization: `decisions/ADR-0040-CANDIDATE-1-DEVELOPMENT-EXECUTION-AUTHORIZATION.md`
- Implementation checkpoint: `reports/checkpoints/IMPLEMENT-CANDIDATE-1-DEVELOPMENT-V1.md`

The Research Director reviewed and accepted the implementation checkpoint without inspecting any
Candidate #1 economic outcome.

This task authorizes exactly **one** frozen Development Lab execution.

## Required read set

Read:

1. `AGENTS.md`
2. `docs/operations/NEW_CHAT_BOOTSTRAP.md`
3. `state/current_state.json`
4. this task
5. `research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md`
6. ADR-0039 and ADR-0040
7. the implementation checkpoint and validation record

Do not reopen design discussion.

## Execution

Preflight:

- require a clean worktree;
- verify protocol / freeze / admission / implementation identities;
- replay the outcome-free implementation validation;
- verify state carries `execution_authorized = true`;
- verify no Development result already exists.

Then execute exactly once:

`python scripts/run_candidate_1_development.py --execute`

Do not run an alternate command, altered specification or exploratory preview.

The frozen 2022-2024 historical economic outcomes may now be inspected **only through this execution**.

## Absolute prohibitions

Do not:

- modify the frozen protocol or its thresholds;
- change event/state/population;
- change matching/calipers;
- change entry, exit or holding period;
- change costs or delay stress;
- change MESIs, support/risk/stability gates or inference;
- run another horizon, stop, target, filter or subgroup;
- add a source or feature;
- fetch new market data;
- access post-cutoff or sealed data;
- create Candidate #2;
- rerun under a changed scientific definition;
- prepare prospective confirmation automatically;
- designate a Champion;
- authorize real money.

A deterministic rerun is permitted only if the initial run is proven technically invalid and the
scientific specification remains byte-identical. Preserve the invalid run and stop for Research
Director review before any rerun if the defect is consequential or ambiguous.

## Result preservation

After the single valid run:

1. preserve `research/experiments/CANDIDATE-1-DEVELOPMENT-V1/result.json` immutably;
2. create a concise human-readable Development checkpoint report;
3. create/append the appropriate research-memory outcome record without altering historical parents;
4. record exact code/protocol/data identities and deterministic replay;
5. record every frozen gate individually, including failures;
6. record all predeclared primary, yearly, risk, concentration, cost-stress, delay-stress,
   uncertainty and prospective-detectability quantities;
7. do not omit unfavorable diagnostics.

The result's mechanically computed disposition is one of:

- `INVALID_EXECUTION`
- `BLOCKED_DATA_OR_SUPPORT`
- `DEVELOPMENT_REJECTED`
- `INCONCLUSIVE_NO_PROMOTION`
- `PROMOTION_ELIGIBLE`

Do not reinterpret it.

## Post-run governance

After one valid execution:

- set `execution_authorized = false`;
- set `market_trial_authorized = false`;
- increment the Development execution / market-trial counters exactly once;
- set `economic_hypothesis_tested = true`;
- set `market_outcomes_inspected = true`;
- record the mechanical Development disposition;
- project state becomes
  `CANDIDATE_1_DEVELOPMENT_RESULT_PENDING_RESEARCH_DIRECTOR_ADJUDICATION`.

Do **not** move to confirmation or strategic reallocation in this task regardless of result.

Archive this task and leave `tasks/CURRENT_TASK.md` as a Research-Director adjudication checkpoint
with executor work forbidden.

## Validation

After recording the result, run deterministic replay/identity validation and the repository's
appropriate no-new-data checks.

Do not run any additional market experiment.

## Git

Local commits on `main` are authorized after the single result and validation are fully recorded.

Do not push.

## Completion report

Return only:

`CANDIDATE_1_DEVELOPMENT_RESULT_PENDING_RESEARCH_DIRECTOR_ADJUDICATION`

Then report:

- development_disposition
- result_path
- execution_commit_sha(s)
- protocol_identity: PASS/FAIL
- implementation_identity: PASS/FAIL
- admission_identity_replay: PASS/FAIL
- candidate_trades / matched_pairs / per-year counts
- source_and_execution_coverage
- ABS_NET_BP
- INCREMENTAL_NET_BP
- primary gate PASS/FAIL details
- per_year_absolute
- per_year_incremental
- annual_contribution_bp
- ES10_candidate / ES10_control
- max_drawdown_bp
- without_top3_absolute / incremental
- cost_stress_abs_net_bp
- delay_stress_abs_net_bp / incremental_net_bp
- uncertainty summary and 95% intervals
- prospective planning SD / required N for both claims
- prospective_detectability: PASS/FAIL
- deterministic_replay: PASS/FAIL
- full_validation: PASS/FAIL
- market_outcomes_inspected: YES
- new_market_data_accessed: NO
- sealed_queries: 0
- champion: NONE
- real_money: false
- unexpected_conditions: concise only
