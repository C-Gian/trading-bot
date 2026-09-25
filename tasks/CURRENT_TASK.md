# CURRENT TASK — EXECUTE-SYSTEM-G1-PHASE-A-V1

Status: PHASE_A_ONLY_AUTHORIZED — PHASE_B FORBIDDEN

## Authority

- `decisions/ADR-0048-AUTHORIZE-SYSTEM-G1-PHASE-A-ONLY.md`
- `research/protocols/SYSTEM-G1-DEVELOPMENT-V1.md`
- Constitution 4.0.

The Research Director accepts the corrected System G1 implementation.

Exactly one real historical **Phase A** execution is authorized.

Phase B / 2023-2024 remains forbidden.

## Mandatory read set

Read only:

1. `AGENTS.md`
2. `docs/operations/NEW_CHAT_BOOTSTRAP.md`
3. this task
4. ADR-0048
5. System G1 Development V1 protocol
6. current `state/current_state.json -> system_g1_development`
7. `backend/app/g1/batch.py`, `scripts/run_g1_development.py`
8. the implementation validation identity record

Do not reopen historical research.

## Stage 0 — phase-scope the hard guard before any market read

Current canonical state is intentionally armed with:

- `historical_execution_authorized=true`
- `authorized_phase="A"`
- ADR-0048 authorization record.

Before calling `authorize_real_sources` or opening a real kline/funding observation:

1. change the authorization path so the requested phase is passed into the guard;
2. refuse unless:
   - `historical_execution_authorized is true`;
   - authorization record exists;
   - `authorized_phase == requested_phase`;
3. prove with tests:
   - A is accepted under current state;
   - B is refused under current state;
   - null/wrong phase is refused;
   - missing ADR is refused;
4. update identities/validation mechanically if the guard file hash changes.

Do not change any scientific execution behavior.

Run focused tests and `scripts/check.py --no-data`.

**Do not open market data until this validation passes.**

## Stage 1 — execute Phase A exactly once

Run only:

`uv run python scripts/run_g1_development.py --phase A`

The frozen engine may use 2020 only for warm-up/training and may trade/select only in 2021-2022 as
defined by the protocol.

Run exactly the seven frozen configurations.

Do not run Phase B regardless of the Phase-A result.

Do not manually inspect/select a preferred configuration beyond reporting the canonical artifact.

## Stage 2 — preserve and mechanically verify Phase A

Preserve the write-once Phase-A selection artifact in:

`research/experiments/SYSTEM-G1-DEVELOPMENT-V1/`

Record:

- exact protocol/code/source/config identities;
- all seven configuration rows;
- every frozen eligibility gate;
- automatic selected configuration, or null;
- mechanical selection-stage disposition;
- artifact hash;
- count of inspected configurations = 7;
- confirmation that 2023-2024 configuration economics were not computed.

Run deterministic artifact verification/replay if supported without re-running a second market
selection experiment. Do not overwrite the write-once artifact.

## Stage 3 — immediately disarm

After the Phase-A artifact is safely written:

Set canonical state:

- `historical_execution_authorized=false`;
- `authorized_phase=null`;
- `phase_a_executed=true`;
- `phase_b_executed=false`;
- `real_g1_outcomes_inspected=true`;
- `p1_p2_real_performance_computed=true` for Phase A development selection evidence;
- `forecaster_real_fitted=true` because the historical continuous forecaster is now fitted/evaluated
  within Phase A;
- next work package = `RESEARCH-DIRECTOR-SYSTEM-G1-PHASE-A-ADJUDICATION-V1`.

Do not set validated strategy.
Do not set Champion.
Do not authorize Phase B.

Archive this task and leave CURRENT_TASK review-only.

## Result report

Create a concise Phase-A checkpoint report that exposes enough for Research Director adjudication:

For each of the seven configurations:

- scorable trades total;
- 2021 / 2022 trade counts;
- coverage;
- 2021 net P&L / equity return;
- 2022 net P&L / equity return;
- cumulative net equity return;
- max drawdown;
- run-stop status;
- eligibility PASS/FAIL and failed gate names.

Then:

- selected configuration or NONE;
- selection reason according to frozen rule;
- Phase-B possible YES/NO.

Also report descriptive Phase-A forecast coverage/conviction counts if already produced by the
engine, but do not introduce new selection gates.

## Absolute prohibitions

Do not:

- run `--phase B`;
- open/evaluate 2023-2024 configuration economics;
- alter any strategy/scientific rule;
- add/remove a configuration;
- rescue an ineligible configuration;
- rerun Phase A with changed rules;
- fetch new data;
- access post-cutoff/sealed data;
- perform news/event research;
- authorize prospective collection;
- set Champion;
- place orders or use real-money credentials.

## Validation after result

Run only validation that does not itself create a second market experiment.

Repository/schema/governance/no-data tests are allowed.

Do not delete or regenerate the Phase-A result.

## Git

Commit the guard change, Phase-A artifact/report, and post-run governance locally.

Do not push.

## Completion report

Return only:

`SYSTEM_G1_PHASE_A_RESULT_PENDING_RESEARCH_DIRECTOR_ADJUDICATION`

Then:

- changed_files
- local_commit_sha(s)
- phase_scoped_guard: PASS/FAIL
- no_data_validation_before_market_read: PASS/FAIL
- phase_a_artifact
- phase_a_artifact_sha256
- configurations_inspected: 7
- per_configuration_summary
- selected_configuration: ID/NONE
- selection_stage_disposition
- phase_b_possible: YES/NO
- phase_b_executed: NO
- 2023_2024_configuration_economics_computed: NO
- state_disarmed_after_phase_a: PASS/FAIL
- new_market_data_downloaded: NO
- sealed_queries: 0
- validated_strategy: NONE
- operational_action: NO_TRADE
- champion: NONE
- real_money: false
- blockers: concise only
