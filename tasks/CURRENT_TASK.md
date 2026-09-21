# CURRENT TASK — RESEARCH-DIRECTOR-REVIEW-PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1

Status: ACTIVE_RESEARCH_DIRECTOR_REVIEW_NO_EXECUTION_AUTHORIZED

Starting HEAD: `5cc4f153f37b0b200b46834e0b714498164889fc` on `main`, followed by the
immutable result checkpoint for `PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1`.

Review the completed first-family Generation V2 evidence without re-running, re-scoring,
tuning, inverting or rescuing either configuration.

Sources of truth:

- `reports/checkpoints/PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1.md`;
- `reports/research/PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1.json`;
- `research/experiments/EXP-PRED-V2-001-CALENDAR-LINEAR/result.json`;
- `research/experiments/EXP-PRED-V2-002-CALENDAR-HGBR/result.json`;
- `reports/validation/PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1-ADMISSION.json`;
- `decisions/ADR-0029-PREDICTIVE-V2-DETERMINISTIC-CALENDAR.md`;
- `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V2.md`.

Required review:

1. confirm both frozen configurations were executed exactly once and the pre-result commit is
   an ancestor of the result commit;
2. confirm deterministic installed-data replay and V1 byte-integrity;
3. interpret the failed coverage-distribution, enrichment, Brier and calibration gates without
   weakening any threshold;
4. accept or reject the executor disposition `REJECTED_DEVELOPMENT_NO_SEALED`;
5. preserve magnitude as `DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`, sealed queries 0,
   Champion `NONE`, real money false;
6. decide the next bounded Generation V2 work package, if any, with a new preregistered family
   and search budget; no experiment is authorized by this review task itself.

Do not access sealed/post-cutoff BTC data. Do not create a second family, fit a model or produce
new market predictions in this review task.
