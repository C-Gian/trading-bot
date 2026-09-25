# CURRENT TASK — RESEARCH-DIRECTOR-REVIEW-SYSTEM-G1-CHECKPOINT-1

Status: REVIEW_ONLY — EXECUTOR MARKET WORK FORBIDDEN

## Authority

- Constitution Version 4.0; ADR-0044; `docs/canonical/PROFESSIONAL_MULTISIGNAL_SYSTEM_ARCHITECTURE_V1.md`.
- Completed executor package (archived verbatim):
  `tasks/archive/SYSTEM-G1-CHECKPOINT-1-SYNTHETIC-VERTICAL-SLICE.md`.

## Review inputs

- Checkpoint report: `reports/checkpoints/SYSTEM-G1-CHECKPOINT-1-SYNTHETIC-VERTICAL-SLICE.md`
- Implementation validation: `reports/validation/SYSTEM-G1-CHECKPOINT-1-IMPLEMENTATION-VALIDATION.json`
- Cycle synthetic diagnostics: `reports/research/SYSTEM-G1-CYCLE-SYNTHETIC-DIAGNOSTICS-V1.json`
- Implementation: `backend/app/g1/`, `backend/app/main.py` (fail-closed guard),
  `frontend/src/Replay.tsx`, tests `backend/tests/test_g1_*.py`,
  `backend/tests/test_fail_closed_action_surface.py`, `frontend/src/Replay.test.tsx`.

## Research Director decisions pending

1. Accept or reject the Checkpoint-1 synthetic vertical slice.
2. Adjudicate the cycle implementation choices listed in the diagnostic artifact and, if
   acceptable, freeze the WEAK/USABLE quality thresholds from the synthetic diagnostics only.
   Until then every decision-path cycle state remains `METHOD_NOT_READY`.
3. Decide the next bounded G1 task (protocol freeze before any historical outcome).

## Boundaries

- No executor work is authorized by this file.
- No System G1 historical market run, market-data fetch, P1/P2 performance calculation,
  forecaster fitting, threshold tuning, Candidate #2, prospective collection, sealed query,
  Champion change, order placement, credential or real money.
- `validated_strategy` remains null and the operational action remains `NO_TRADE`.
