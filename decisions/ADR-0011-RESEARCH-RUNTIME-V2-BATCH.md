# ADR-0011 — prospective batch research runtime V2

Status: accepted for explicit use by future preregistered candidates.

## Decision

Future research may bind `RESEARCH_RUNTIME_V2_BATCH` as a distinct runtime identity.
The runtime predicts each governed validation matrix in one ordered vector call by
default, or in explicitly bounded deterministic batches. It rejects duplicate or
unordered row identities, matrix/identity length disagreement, non-finite values, and
invalid prediction shapes. Prediction-to-signal mapping remains positional and the
signal predicate remains exactly `prediction > 0.0`.

Fold inputs are iterated in declared order. `ZERO`, `DEFAULT`, and `DOUBLE` share the
same prediction-view object and never trigger a refit. `DELAY_1H` maps each evaluation
clock to the prior governed hourly prediction without retraining. Future V2 adapters
must persist timings for `LOAD_DATA`, `BUILD_FEATURES`, `BUILD_LABELS`, `FIT`, `PREDICT`,
`PROFILES`, `RECONCILIATION`, and `FINALIZE`.

Research Runner candidate definitions now bind a source-controlled runtime version.
The binding is included in runtime state, results, review bundles, and the Research Lab.
A V2 result without a valid timing record fails closed. Existing WP-015 reproduction
and blocked WP-016 adapters explicitly retain their pre-V2 frozen runtime identities;
no candidate switches implicitly.

## Historical isolation

WP-008, WP-011, WP-012, WP-013, WP-014, and WP-015 implementations were not modified.
Their Stage A content hashes are recorded in
`research/runtime/FROZEN-HISTORICAL-RUNTIME-IDENTITIES.json` and enforced by tests.
Historical results and preregistration dependencies remain unchanged.

## Equivalence evidence

`reports/benchmarks/RESEARCH-RUNTIME-V2-BATCH.json` is an
`ENGINEERING_EQUIVALENCE_REPRODUCTION`, not new scientific evidence. A fixed synthetic
10,000-row HGBR benchmark and a 513-row governed sample from already-exposed WP-015
fold DEV-2020 both produced maximum absolute prediction difference `0.0` and zero
signal mismatches. The governed fit reproduced the committed model identity; DEFAULT
trade identities and metrics were identical, cost profiles reused predictions, and
DELAY_1H alignment matched.

The measured prediction-operation speedups were approximately `470.76x` synthetic and
`251.07x` governed. These are not whole-experiment speedup claims; the known full
WP-015 reproduction remains `1067.810941s` and a complete V2 experiment has not run.

## Cache decision

No cache is implemented. A future cache must first bind code/runtime, candidate/config,
all manifest and content hashes, feature and target versions, fold definition, cutoff,
and source configuration. Avoiding stale-science risk currently outweighs speculative
substrate reuse.
