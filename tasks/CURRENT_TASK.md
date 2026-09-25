# CURRENT TASK — RESEARCH-DIRECTOR-G1-DEVELOPMENT-EXECUTION-REVIEW-V1

Status: REVIEW_ONLY — EXECUTOR MARKET WORK FORBIDDEN

## Authority

- Constitution 4.0; ADR-0046; `research/protocols/SYSTEM-G1-DEVELOPMENT-V1.md`.
- Completed executor package (archived verbatim):
  `tasks/archive/IMPLEMENT-SYSTEM-G1-DEVELOPMENT-V1.md`.

## Review inputs

- Checkpoint report: `reports/checkpoints/IMPLEMENT-SYSTEM-G1-DEVELOPMENT-V1.md`
- Implementation validation / identities:
  `reports/validation/SYSTEM-G1-DEVELOPMENT-IMPLEMENTATION-V1.json`
- Implementation: `backend/app/g1/` (`indicators.py`, `playbooks.py`, `forecaster.py`,
  `development.py`, `scoring.py`, `batch.py`, `sources.py`, `cycle.py`), guarded command
  `scripts/run_g1_development.py`, tests `backend/tests/test_g1_dev_*.py`.
- API/record reference: `docs/canonical/SYSTEM_G1_REPLAY_API_V1.md`.

## Research Director decisions pending

1. Review the implementation and the implementation choices listed in the checkpoint report.
2. Decide whether to authorize the single historical G1 Development batch. Authorization must be
   written to `state/current_state.json -> system_g1_development` (`historical_execution_authorized`
   and an existing `execution_authorization_record`); until then the runner refuses.

## Boundaries

- No executor work is authorized by this file.
- No System G1 historical run, market-data fetch, P1/P2 performance calculation, real forecaster
  fit, threshold/rule change, Candidate #2, prospective collection, sealed query, Champion change,
  order placement, credential or real money.
- `validated_strategy` remains null and the operational action remains `NO_TRADE`.
