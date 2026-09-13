# Research Runner V1

## PREPARE → MANUAL RUN → REVIEW

PREPARE is the scientific gate. A candidate is implemented and preregistered in Git
before its id can enter the explicit Python allowlist. The HTTP caller supplies only that
id; it cannot supply a command, module, path, model parameter, threshold, or dataset.
Every new experiment binds exact preregistration hashes.

MANUAL RUN begins only when the Owner clicks **Avvia test storico** in the local Research
Lab. FastAPI persists a queued record atomically and starts its fixed adapter on one local
background thread. A filesystem lock permits one run at a time. The deterministic adapter
publishes real stages. Refresh reloads the record; a backend restart marks an unfinished
run `FAILED / INTERRUPTED`.

REVIEW presents a generic result contract and deterministic copyable bundle with code and
data identities, fold metrics, cost stress, control comparison, reconciliation, warnings,
and evidence classification. Logs and runtime artifacts stay in the gitignored
`data/research_runs/<run_id>/` directory.

## Scientific separation

Canonical truth remains in preregistrations, experiment records, manifests, validation
reports, and `state/current_state.json`. Local run records are operational UI state only.
The runner cannot finalize or rewrite experiments, increment scientific counters, consume
sealed queries, create paper trades, select a Champion, or authorize real money.

The registry retains `WP015_REPRODUCTION_V1` as reproduction history and exposes
`WP016_WIKIPEDIA_ATTENTION_V1` as the primary runnable candidate only after its exact
preregistration hashes and required local datasets pass. A WP-016 result remains local
and pending Research Director review until a later governed checkpoint records it.

The runner has no order, futures execution, credential, balance, sealed-data, or
post-cutoff development-data surface.
