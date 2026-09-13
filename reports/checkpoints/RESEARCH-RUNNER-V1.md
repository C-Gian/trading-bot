# Research Runner V1 checkpoint

RESEARCH-RUNNER-V1 completed as an engineering-only checkpoint. The local app now exposes
one source-controlled candidate, `WP015_REPRODUCTION_V1`, through a narrow FastAPI contract
and a dedicated Italian Research Lab surface.

The Owner supplies only the allowlisted candidate id. One background thread executes the
fixed adapter behind an atomic filesystem lock; runtime state and artifacts persist under
gitignored `data/research_runs/`. Browser refresh restores the current/last record, and a
backend restart marks unfinished work `FAILED / INTERRUPTED`. Arbitrary commands,
configuration, paths, credentials, orders, balances, futures execution, sealed access,
and post-cutoff development access are absent.

The fixed adapter reuses WP-015's frozen 2020–2024 primary/control/profile semantics,
writes only local runtime artifacts, invokes its independent reconciliation with explicit
runtime paths, and requires a numerical match to the committed WP-015 comparison. The UI
shows real runner stages and produces a compact deterministic review bundle.

Only mocked/synthetic runner stages were executed during implementation. No real WP-015
historical reproduction or new experiment ran. Scientific counters, paper trades,
Champion status, sealed queries, ALIGNED, and real-money authorization are unchanged.

Validation: 621 backend tests, 36 frontend tests, Ruff, formatting, mypy, frontend lint,
typecheck/build, and `python scripts/check.py --no-data` passed.
