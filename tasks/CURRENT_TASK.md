# CURRENT TASK — RESEARCH-DIRECTOR-G1-INCOMPLETE-BAR-FIX-REVIEW-V1

Status: REVIEW_ONLY — EXECUTOR MARKET WORK FORBIDDEN

## Authority

- ADR-0047; `research/protocols/SYSTEM-G1-DEVELOPMENT-V1.md` (unchanged).
- Completed executor package (archived verbatim):
  `tasks/archive/FIX-SYSTEM-G1-INCOMPLETE-BAR-RECURSIVE-STATE-V1.md`.

## Review inputs

- Correction section of `reports/checkpoints/IMPLEMENT-SYSTEM-G1-DEVELOPMENT-V1.md`
- Regenerated identities: `reports/validation/SYSTEM-G1-DEVELOPMENT-IMPLEMENTATION-V1.json`
- Code: `backend/app/g1/indicators.py`; tests `backend/tests/test_g1_incomplete_bar_fix.py`.

## Research Director decisions pending

1. Accept or reject the incomplete-bar recursive-state correction.
2. Decide whether to authorize the single historical G1 Development batch (state
   `system_g1_development.historical_execution_authorized` plus an existing authorization record);
   until then `scripts/run_g1_development.py` refuses.

## Boundaries

- No executor work is authorized by this file.
- No Phase A/B run, market-data read, P1/P2 performance, real forecaster fit, rule/threshold
  change, new configuration, sealed query, Champion change, order, credential or real money.
- `validated_strategy` remains null and the operational action remains `NO_TRADE`.
