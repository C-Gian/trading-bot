# System G1 parked engineering debt V1

Status: **PARKED — REQUIRES SEPARATE FUTURE ALLOCATION**
Date: 2026-09-26
Authority: Astra post-Phase-A strategic review / ADR-0050.

These items are reusable engineering debts, not active research tasks and not reopening triggers by
themselves.

## ED-G1-001 — Phase-bounded source I/O

Before any future staged historical replay:

- enforce the authorized interval at archive/file opening;
- do not open unauthorized next-period monthly archives;
- funding reads must be bounded before observation loading, not filtered only after full-file load;
- keep manifest-metadata inspection separate from observation access;
- deterministic tests must fail if source code attempts to open/read beyond the authorized phase.

This debt does not invalidate G1 Phase A.

## ED-G1-002 — Exact forecaster runtime

G1 Phase A took about 428 minutes primarily because the forecaster repeatedly sorted/reprocessed
growing historical distributions at every 15m forecast.

Any future allocation reusing the estimator/replay architecture should:

- preserve exact training windows, shrinkage, quantile and tie semantics;
- precompute/reuse cell and unconditional distribution representations at training boundaries;
- avoid approximate quantiles or changed statistics merely for speed;
- validate the optimized implementation byte/numerically against a slow reference on synthetic
  histories including sparse cells, ties, missingness and purge boundaries;
- demonstrate practical runtime on a synthetic workload comparable to two historical years before
  another market run.

Do not rerun G1 for benchmarking.

## Product implication

The Owner's desired replay remains an interactive UI capability.

If research is ever separately reopened, runtime engineering should be completed before another large
historical market run so the same causal engine can drive CLI governance and the visible web replay.

Current allocation: zero.
