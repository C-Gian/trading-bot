# Sealed evaluation V1

Status: built and **locked**. Zero sealed queries are authorized and zero have been
consumed. WP-006 built this infrastructure without acquiring, reading, summarizing
or querying any reserved BTCUSDT data.

Sealed evaluation is the second strongest evidence stage, below immutable forward
paper evidence and above purged chronological walk-forward validation. It is a
one-shot, budgeted confirmation of an already-frozen candidate, never a place to
explore.

## Machine-readable surface

- `contracts/sealed_evaluation_request.schema.json`
- `contracts/sealed_evaluation_result.schema.json`
- `research/sealed/SEALED_QUERY_BUDGET.json`
- `research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json`
- `research/sealed/<scope>/CONSUMPTION_LEDGER.jsonl` (append only)
- `research/sealed/<scope>/results/<query-id>.json` (immutable)
- `backend/app/sealed/` — evaluator, budget, isolation

## What a request must freeze

A request is frozen before it is submitted and cannot change afterwards. It carries
the candidate experiment ID and version, the executable-spec hash, the code and
dependency hashes with every declared path, the development-result hash, the sealed
interval identity (dataset ID, content hash, start, end, sealed path), the engine,
execution and cost model versions, the primary metric, the allowed secondary
metrics, the robustness profiles, the query ID, and the query budget. The
`request_hash` is the SHA-256 of the canonical request without that field; any later
mutation is detected and refused.

## What the evaluator does, in order

1. Validate the request against its schema.
2. Refuse immediately unless the scope has an unconsumed authorized query. A locked
   scope never proceeds and never touches a dataset.
3. Verify the request has not been mutated since it was frozen.
4. Validate candidate eligibility against the eligibility table.
5. Verify exact code and configuration identity for every declared dependency, plus
   the development-result identity.
6. Verify development and sealed dataset separation: distinct dataset identity,
   distinct content hash, a start strictly after the development cutoff, and a path
   inside a registered sealed root.
7. Refuse a duplicate query ID and refuse a candidate identity that already consumed
   a query.
8. Consume one query by appending to the ledger **before** any result exists.
9. Execute only the declared metrics and profiles; an undeclared metric is refused.
10. Atomically finalize one immutable result. An existing result is never replaced.

A negative result, a rejected-after-consumption request and a failed execution all
consume the same budget. Deleting a result file never restores capacity, because the
append-only ledger — not the result directory — is the record of consumption.

## Candidate eligibility

A candidate may be queried only if all of the following hold:

- its development terminal classification is `PROMISING_DEVELOPMENT_ONLY`;
- its structural validator is `PASS`;
- an explicit future Research Director sealed allocation names it;
- its SEARCH_MEMORY_V2 binding is valid;
- it has no unresolved material integrity issue.

`INCONCLUSIVE` is never seal-eligible. `ALIGNED_PARTICIPATION_CONTINUATION_V1`
(`EXP-ALG-009-ALIGNED`) is therefore **not eligible**, and no diagnostic support
changes that.

## Isolation — an honest statement

Isolation is **application and repository layer only. It is not operating-system
enforced and claims no OS-grade secrecy.** Concretely:

- `data/sealed/**` and `research/sealed/datasets/**` are registered sealed roots;
- `app.sealed.isolation.development_open` is the sanctioned development file opener
  and raises `SealedAccessDenied` for any sealed path, with `..` and symlinks
  resolved first;
- the approved development manifest is checked to reference no sealed path, and the
  ordinary development loader admits only that byte-pinned manifest, so it has no
  reachable code path to a sealed location;
- the sealed evaluator is the only component permitted to read a sealed dataset, and
  only under an authorized, budget-consuming, preregistered query.

A privileged operator with a shell can still read any file. This contract does not
pretend otherwise. The scientific guarantee is that no research agent or ordinary
research code path can reach reserved data, and that any access that did occur would
be visible in the append-only consumption ledger and in Git history.

## Unlocking

`authorized_queries` may be raised above zero only by an explicit Owner-authorised
Research Director allocation recorded in `authorization_record`. No executor, agent
or automated process may unlock a scope. Once a holdout is exposed it loses sealed
status permanently and is retired.

A sealed result is not forward evidence, not a Champion promotion, and never
permission for real capital.
