# Checkpoint — CANDIDATE-1-FROZEN-ADMISSION-V1

Status: **EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_REVIEW**. Specification frozen and
committed at `998f24c` before its single calculation; executor diagnostic preserved at
`367c922`.

## Result ([ADR-0038](../../decisions/ADR-0038-CANDIDATE-1-ADMITTED-FOR-PROTOCOL-DESIGN.md))

Record `reports/validation/CANDIDATE-1-FROZEN-ADMISSION-V1.json` (replay PASS).

- Source reliability: 335 / 336 intended episodes valid (0.997); one `OI_NON_POSITIVE`
  exclusion; no perpetual gaps; 3 valid episodes contain a 5m OI jump > 0.05 in their window;
  max |log(perp/spot)| 21 bp.
- Candidate / control: 116 / 219; by year 41/80, 40/54, 35/85.
- Common support: PASS (three years; overlapping `shock_z` and prior-volatility ranges).
- 12-month screen: `n_12m = 35` → required standardized effect 0.4203 <= 0.50: PASS.

Disposition **`CANDIDATE_1_ADMITTED_FOR_PROTOCOL_DESIGN`**; project state
`CANDIDATE_1_PROTOCOL_DESIGN_PENDING`. The economic hypothesis is untested; no market trial is
authorized.

## Accounting

Support calculations 1 of 1; forward returns / outcomes / labels / models: none; new data: none
(cached pre-cutoff manifests only); sealed queries 0; Champion NONE; real money false.

## Next

`RESEARCH-DIRECTOR-PROTOCOL-DESIGN-CANDIDATE-1-V1` — Research Director protocol design; no
executor work authorized.
