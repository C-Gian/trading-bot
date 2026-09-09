# ADR-0006 — Sealed evaluation architecture V1, built locked

Status: accepted (WP-006)

## Context

The Constitution ranks sealed locked evaluation second only to immutable forward
evidence, requires sealed data to be inaccessible to research agents, requires
repeated sealed queries to consume an explicit budget, and retires any exposed
holdout. Until WP-006 none of that existed as machinery, so the rule could only be
honoured by abstention.

Building the machinery is itself risky: the obvious way to test a sealed evaluator
is to give it sealed data. WP-005 also left `ALIGNED_PARTICIPATION_CONTINUATION_V1`
`INCONCLUSIVE`, which is exactly the class of candidate that must never reach a
sealed query even though its diagnostics look encouraging.

## Decision

Build `SEALED_EVALUATION_V1` in a permanently locked initial state and prove it
entirely with synthetic fixtures.

1. **No reserved data.** No BTCUSDT bytes after `2024-12-31T23:59:00Z` are acquired,
   read, summarized, charted or queried. `data/sealed/` does not exist. The BTC
   scope is `RESERVED_NOT_ACQUIRED` with `authorized_queries = 0`,
   `consumed_queries = 0`, status `LOCKED_NO_AUTHORIZED_QUERY`.
2. **Freeze before query.** A request freezes candidate identity and version,
   executable-spec hash, code and dependency hashes, development-result hash, sealed
   interval identity, engine/execution/cost versions, the primary metric, the allowed
   secondary metrics, the robustness profiles, the query ID and the query budget. Its
   `request_hash` makes post-freeze mutation detectable.
3. **Eligibility is derived, not asserted.** Only `PROMISING_DEVELOPMENT_ONLY` with a
   passing structural validator, a valid SEARCH_MEMORY_V2 binding, no unresolved
   material integrity issue, and an explicit Research Director sealed allocation can
   be queried. `INCONCLUSIVE` is never eligible, so ALIGNED is not eligible.
4. **Budget is consumed by an append-only ledger before any result exists.** Negative
   results, post-consumption rejections and execution failures all consume. Deleting a
   result cannot restore capacity, because the ledger and not the result directory is
   the record.
5. **Bounded output.** The evaluator emits only the declared metrics for the declared
   profiles and finalizes one immutable result atomically. It is not a sealed-data
   browser, and the API/UI expose only version, status and counters.
6. **Honest isolation.** Isolation is application and repository layer, enforced by a
   sanctioned development opener that refuses registered sealed roots and by the
   development loader's byte-pinned manifest. It is explicitly **not** OS-grade
   secrecy, and the contract says so rather than overclaiming.

## Consequences

- The Constitution's sealed rules are now mechanically enforced instead of merely
  observed.
- No candidate in the repository can be sealed-queried today, and WP-006 did not
  unlock anything.
- Unlocking requires an explicit Owner-authorised Research Director allocation
  recorded in the budget; no agent may perform it.
- The synthetic suite proves rejection of unauthorized, ineligible, drifted,
  duplicated, exhausted, undeclared-metric and overwrite attempts, and proves that a
  consumed synthetic query cannot be restored by deleting its output.
- Because isolation is not OS-enforced, a privileged operator remains able to read
  files directly. That residual risk is documented rather than hidden, and any real
  access would remain visible in the ledger and in Git history.
