Research Director sealed-allocation artifacts live here, one file per allocation.

The directory is empty because no sealed query has ever been authorized. An artifact
must declare `kind: SEALED_SCIENTIFIC_ALLOCATION`, `issuer: RESEARCH_DIRECTOR`, the
scope it authorizes, the exact `authorized_queries`, the `candidate_experiment_ids`
it covers, and `real_money_authorized: false`.

Allocations issued by `EXECUTOR` or `AUTOMATION` are rejected by the budget loader,
so writing one is not a way to self-authorize. See
`docs/contracts/SEALED_EVALUATION_V1_1.md` and
`decisions/ADR-0008-SEALED-SCIENTIFIC-ALLOCATION-AUTHORITY.md`.
