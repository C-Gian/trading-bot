# ADR-0009 — An append-only research registry instead of a layer per work package

Status: accepted (WP-007), generalizes ADR-0007

## Context

ADR-0007 introduced a second record layer because the WP-004 audit pins the V1 ledger,
outcomes, budget, family registry and adaptive decisions to their exact first-commit
bytes. That was the right call, but it does not scale: the WP-006 audit now pins
`FAMILY_REGISTRY_V2.json`, `SEARCH_BUDGET_V2.json` and `ADMISSION_LEDGER_V2.jsonl` the
same way, so WP-007 would have needed a third bespoke layer, WP-008 a fourth, and so on.

A layer per work package is not just ugly. Each new layer is a new place a reader has to
know about to compute the true cumulative search burden, and every missed layer
understates that burden — which is exactly the failure mode the search-memory design
exists to prevent.

## Decision

Add one **append-only directory** that every later work package extends by writing new
files, never by editing an existing one:

```
research/memory/registry/
  families/<FAMILY-ID>.json          one immutable record per admitted root family
  allocations/<ALLOCATION-ID>.json   one immutable result-dependent allocation
  admissions/<WP>-NOVELTY-*.json     the governed gate decision, or its rejection
  ledger/<WP>.jsonl                  that work package's admissions
  outcomes/<WP>.jsonl                that work package's finalized outcomes
```

`backend/app/research/registry.py` is the single reader. It merges the frozen V1 layer,
the frozen WP-006 layer and every file in this directory, and exposes one view of
families, aliases and entry-event anchors, executable-spec signatures, family budgets and
consumed units, allocations, outcomes, and cumulative accounting.

Consequently:

- adding a family means adding a file, so no frozen record is ever touched;
- the novelty gate checks a proposal against **all** layers at once, so a duplicate
  cannot hide behind a newer file;
- an alias or an entry-event anchor registered in any layer blocks a colliding root, so a
  rename cannot mint a fresh budget;
- cumulative accounting sums every layer, so no counter is reset by introducing a file;
- `wp006_views.cumulative_accounting` and the API budget view now delegate here, so
  there is one source of truth rather than two that could drift.

## Consequences

- WP-008 and later add files under `research/memory/registry/` and need no new layer, no
  new module and no change to the audits.
- The V1 and WP-006 layers stay byte-identical, so the WP-004 and WP-006 audits keep
  passing unchanged and the older evidence keeps its guarantee.
- The cost is one indirection: a reader must go through `registry.py` rather than a
  single file. That is accepted, because the alternative is a growing set of files a
  reader must remember to add up by hand.
- Deleting a registry file would understate the search burden. That is why the WP-007
  audit re-derives the ledger, checks every admitted behaviour against the committed gate
  record, and asserts that prior work packages' admissions are still present.
