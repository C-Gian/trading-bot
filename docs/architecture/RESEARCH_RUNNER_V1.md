# Research Runner V1

## PREPARE → MANUAL RUN → REVIEW

PREPARE is the scientific gate. A future candidate is implemented and preregistered in
Git before its id can enter the explicit Python allowlist. The HTTP caller supplies only
that id; it cannot supply a command, module, path, model parameter, threshold, or dataset.
Each allowlist entry binds the expected preregistration file hashes; a future
`NEW_EXPERIMENT` entry without a frozen identity is rejected by the registry.

MANUAL RUN begins only when the Owner clicks **Avvia test storico** in the local Research
Lab. FastAPI persists a queued record atomically and starts the fixed adapter on one local
background thread, so the request returns immediately. A filesystem lock permits one run
at a time. The deterministic adapter publishes real stage transitions as work completes.
Refreshing the browser reloads the persisted record. If the backend restarts mid-run, the
record becomes `FAILED / INTERRUPTED`; it is never reported as successful.

REVIEW presents a small generic result contract and a deterministic copyable bundle. The
bundle carries code/data identities, fold metrics, cost stress, control comparison,
reconciliation status, and evidence classification. Raw runtime artifacts and logs remain
under the gitignored `data/research_runs/<run_id>/` directory.

## Scientific separation

Canonical scientific truth remains in preregistrations, experiment records, manifests,
validation reports, and `state/current_state.json`. Local run records are operational UI
state only. They do not finalize or rewrite experiments, increment scientific counters,
consume sealed queries, create paper trades, select a Champion, or authorize real money.

V1 registers exactly `WP015_REPRODUCTION_V1`. Its fixed adapter recomputes the frozen
2020–2024 WP-015 primary/control profiles into the local run directory and invokes the
independent WP-015 reconciliation against those runtime artifacts. It is labeled
`REPRODUCTION_OF_ALREADY_EXPOSED_DEVELOPMENT_RESULT` and creates no new evidence.

The runner has no order, futures execution, credential, balance, sealed-data, or
post-cutoff development-data surface.
