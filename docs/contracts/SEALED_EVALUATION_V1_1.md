# Sealed evaluation V1.1

Status: active. Supersedes **only** the "Unlocking" section of
`docs/contracts/SEALED_EVALUATION_V1.md`, which remains in the repository unchanged
and still describes everything else that governs sealed evaluation.

Authority for this change: `decisions/ADR-0008-SEALED-SCIENTIFIC-ALLOCATION-AUTHORITY.md`.

Current state: **LOCKED**. Zero authorized and zero consumed BTC queries; reserved
data never acquired; no allocation artifact exists.

## What changed

V1 required an Owner-authorised allocation to raise a scope's query budget. That
mis-assigned authority: a historical sealed evaluation is a scientific research
allocation, and research direction and experiment allocation are delegated to the
Research Director. Owner interruption is reserved for real capital, external
irreversible actions, expenditure or credentials, and material changes to the
product/risk objective.

## Authorization rules

A scope's `authorized_queries` may exceed zero **only** when the budget's
`authorization_record` names an existing Research Director sealed-allocation artifact
under `research/sealed/allocations/` satisfying all of:

- `kind = SEALED_SCIENTIFIC_ALLOCATION`;
- `issuer = RESEARCH_DIRECTOR`;
- `scope` equal to the scope it authorizes;
- `authorized_queries` equal to the scope's authorized count;
- `candidate_experiment_ids` naming every candidate the allocation covers;
- an explicit `real_money_authorized: false`.

The loader enforces this on **every** budget read, including the read the evaluator
performs before it touches anything. A raised budget with no allocation, a mismatched
scope, a mismatched count, or an allocation issued by anyone other than the Research
Director fails closed, and no query can run.

- **Executors cannot self-authorize.** An artifact with `issuer = EXECUTOR` is
  rejected, so writing one is not a bypass.
- **Automated workflows cannot self-authorize.** An artifact with
  `issuer = AUTOMATION` is rejected the same way.
- **Real money remains a separate mandatory Owner gate.** Nothing in this contract
  authorizes real capital, and a sealed result never does.

## What is unchanged from V1

Everything else. In particular:

- **Candidate eligibility.** Only `PROMISING_DEVELOPMENT_ONLY` with a passing
  structural validator, a valid SEARCH_MEMORY_V2 binding, no unresolved material
  integrity issue, and a sealed allocation naming the candidate. `INCONCLUSIVE` is
  never seal-eligible.
- **Request freezing.** Candidate identity and version, executable-spec hash, code and
  dependency hashes, development-result hash, sealed interval identity, engine,
  execution and cost versions, primary metric, allowed secondary metrics, robustness
  profiles, query ID and query budget are all frozen, and `request_hash` detects any
  later mutation.
- **Consumption.** One query is consumed by the append-only ledger **before** any
  result exists. Negative results, post-consumption rejections and execution failures
  all consume. Deleting a result never restores capacity.
- **Immutability.** One result per query identity, finalized atomically, never
  overwritten. A candidate identity that already consumed a query cannot query again.
- **Bounded output.** Only declared metrics for declared profiles. There is no sealed
  data browser, and the API and UI expose only version, status and counters.
- **Isolation, stated honestly.** Application and repository layer only. It is **not**
  OS-enforced and claims no OS-grade secrecy. A privileged operator with a shell can
  still read files; the guarantee is that no research agent or ordinary research code
  path can reach reserved data, and that any access is visible in the ledger and in
  Git history.

## Machine-readable surface

- `research/sealed/SEALED_QUERY_BUDGET.json` — `version: SEALED_EVALUATION_V1_1`,
  with an `authorization_policy` block naming the allocation directory and explicitly
  denying executor and automation self-authorization.
- `research/sealed/allocations/` — Research Director sealed-allocation artifacts.
  Currently empty.
- `contracts/sealed_evaluation_request.schema.json` and
  `contracts/sealed_evaluation_result.schema.json` accept both V1 and V1.1 identities,
  so no historical record is invalidated.
