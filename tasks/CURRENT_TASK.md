# CURRENT TASK — RESEARCH-RUNNER-V1

## Owner-initiated local backtesting

Status: IMPLEMENTATION IN PROGRESS

Starting HEAD: `b12f13f1f5fe7ab5d94893f9297e75d8f9c5b467` on `main`.

Build a local Research Lab workflow with a source-controlled candidate allowlist,
non-blocking deterministic Python execution, atomic gitignored runtime state, meaningful
progress, an Owner-facing result summary, and a compact review bundle.

V1 exposes exactly `WP015_REPRODUCTION_V1`. It is a reproduction of already-exposed
development evidence, not a new experiment. It cannot change scientific counters, paper
trades, Champion status, sealed-query accounting, or real-money state.

The implementation checkpoint must use only mocked or synthetic test execution. The real
WP-015 historical workload must not be run by the executor.
