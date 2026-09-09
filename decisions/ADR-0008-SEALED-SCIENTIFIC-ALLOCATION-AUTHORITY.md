# ADR-0008 — Sealed scientific allocation is a Research Director decision

Status: accepted (WP-007), prospective correction to ADR-0006

## Context

`SEALED_EVALUATION_V1` was built locked in WP-006 and is technically sound. Its
unlock text, however, required an **Owner-authorised** allocation before
`authorized_queries` could exceed zero.

That wording mis-assigns authority. AGENTS.md delegates quantitative research
direction, experiment interpretation and experiment allocation to the Research
Director, and reserves Owner interruption for genuinely consequential Owner
decisions: real capital, external irreversible actions, expenditure or credentials,
and material changes to the product/risk objective.

A historical sealed evaluation is none of those. It reads reserved historical data
under a preregistered, budgeted, one-shot protocol. It is a scientific research
allocation. Requiring an Owner gate for it would either stall legitimate research or,
worse, create pressure to route around the gate.

The correction must not weaken anything else. The reason sealed evaluation is
valuable is precisely that its eligibility, immutability and consumption rules are
strict, and none of those rules is at issue here.

## Decision

Introduce `SEALED_EVALUATION_V1_1` as a prospective successor that changes
**authorization governance only**.

`docs/contracts/SEALED_EVALUATION_V1.md` is **not** rewritten. Its original wording
stays in the repository and in Git history; V1.1 states exactly which section it
supersedes and why.

What V1.1 changes:

- Only an explicit **Research Director sealed-allocation artifact** may raise a
  scope's query budget above zero. The artifact must declare
  `issuer: RESEARCH_DIRECTOR`, the scope it authorizes, and the exact number of
  queries, and the budget must reference it.
- An executor may not self-authorize. An allocation whose issuer is `EXECUTOR` is
  rejected by the loader, so writing one is not a bypass.
- An automated workflow may not self-authorize. An allocation whose issuer is
  `AUTOMATION` is rejected the same way.
- Real money remains a **separate mandatory Owner gate**, unaffected by this ADR. A
  sealed result is not forward evidence, not a Champion promotion, and never
  permission for real capital.

What V1.1 deliberately does **not** change:

- candidate eligibility — still only `PROMISING_DEVELOPMENT_ONLY` with a passing
  structural validator, a valid SEARCH_MEMORY_V2 binding, no unresolved material
  integrity issue, and an explicit sealed allocation naming the candidate;
- request freezing and immutability;
- append-only budget consumption before any result exists;
- one immutable result per query, never overwritten;
- declared-metric-only output, and no sealed-data browser;
- honest isolation: application and repository layer, not OS-enforced.

## State at the time of this decision

WP-007 performs **no** sealed query. The BTC scope remains:

- `authorized_queries = 0`
- `consumed_queries = 0`
- `status = LOCKED_NO_AUTHORIZED_QUERY`
- `dataset_state = RESERVED_NOT_ACQUIRED`

No allocation artifact exists. `research/sealed/allocations/` is empty.

## Consequences

- A future sealed evaluation can be allocated by the Research Director without an
  Owner interruption, which is the correct division of authority.
- The loader enforces the authority rule mechanically: a raised budget with no
  allocation, or with an executor- or automation-issued allocation, fails closed and
  no query can run.
- Because the rule lives in `load_budget`, every read of the budget — including the
  read the evaluator performs before touching anything — enforces it.
- The residual risk is unchanged and stated plainly: isolation is not OS-enforced, so
  a privileged operator with a shell can still read files. The scientific guarantee is
  that no research agent or ordinary research code path can reach reserved data, and
  that any consumption is visible in the append-only ledger and in Git history.
