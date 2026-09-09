# ADR-0007 — A new root family and an additive SEARCH_MEMORY_V2 record layer

Status: accepted (WP-006)

## Context

Two pressures met in WP-006.

First, `FAM-BREAKOUT` is exhausted and `ALIGNED_PARTICIPATION_CONTINUATION_V1` stays
`INCONCLUSIVE`, so the only legitimate research move is exactly one genuinely new
algorithmic family, admitted by a governed novelty gate rather than by assertion.

Second, the WP-003/WP-004 evidence is deliberately frozen at the byte level. The
WP-004 audit pins `SEARCH_LEDGER.jsonl` to its exact bytes at commit `4023928`,
pins `OUTCOMES.jsonl` to its bytes at the WP-004 result commit, and requires
`SEARCH_BUDGET.json`, `HYPOTHESIS_FAMILIES.json` and `ADAPTIVE_DECISIONS.json` to be
unchanged since their first commit. Appending WP-006 admissions to those files would
either break that audit or force it to be weakened — which would destroy the very
guarantee that makes the prior evidence trustworthy.

## Decision

Record WP-006 in an **additive** SEARCH_MEMORY_V2 layer beside the frozen V1 records,
never inside them.

- `research/memory/FAMILY_REGISTRY_V2.json` — root families admitted under the
  executable-spec gate. WP-006 adds exactly one: `FAM-PULLBACK-RECOVERY`.
- `research/memory/SEARCH_BUDGET_V2.json` — carries the consumed V1 totals forward
  (9 configurations, 53 trials) and allocates 2 configurations and 8 trials to the new
  root only.
- `research/memory/WP006-PULLBACK-RECOVERY-ALLOCATION.json` — the one immutable
  result-dependent allocation, incrementing adaptive decisions and forks from 2 to 3.
- `research/memory/WP006-NOVELTY-ADMISSION.json` — the governed gate decision,
  deterministically reproducible from the frozen specs.
- `research/memory/ADMISSION_LEDGER_V2.jsonl` and `OUTCOMES_V2.jsonl` — the WP-006
  admissions and outcomes.
- `contracts/search_ledger_v2.schema.json` — the V2 admission schema.

Cumulative accounting is computed by summing the V1 and V2 layers, so a reader sees
one total search burden and no counter is ever reset. The V1 registry and ledger stay
authoritative for the nine frozen legacy strategies and are not rewritten.

## The admitted family

`PERSISTENT_TREND_PULLBACK_RECOVERY_V1` under the new root `FAM-PULLBACK-RECOVERY`,
anchored on the entry event `CLOSE_RECOVERS_ABOVE_DAILY_MEAN_AFTER_PULLBACK`.

The governed gate was run on typed executable specs before any market result existed
and returned `NEW_FAMILY` for the primary `RECOVERY_CORE` variant with no matched
legacy experiment, and `DESCENDANT_MECHANISM_CHANGE` for `RECOVERY_CONFIRM` within the
newly admitted root. Neither the classifier nor the family name was altered to obtain
that outcome, and the proposed root and entry event were checked against all 19
registered aliases and anchors for collision.

Had the gate returned `DUPLICATE`, `PARAMETER_VARIANT`, `NEAR_DUPLICATE` or a
conflicting root, the rejection would have been written to
`research/memory/WP006-NOVELTY-REJECTION.json` and execution would have stopped.

## Consequences

- One new economic hypothesis, two strategy variants, zero numeric parameter variants
  and eight profile evaluations are authorized — nothing more.
- `FAM-BREAKOUT` remains exhausted at 4/4 configurations and 15/15 trials, and this
  allocation resets nothing.
- The WP-004 byte-level audit continues to pass unchanged, so the frozen evidence keeps
  its guarantee.
- The cost is two record layers instead of one. That is accepted deliberately: an
  additive layer is honest about history, whereas editing frozen files to fit a new work
  package is exactly the failure mode the audit exists to prevent.
- Future work packages extend the V2 layer; they must never reopen the V1 layer.
