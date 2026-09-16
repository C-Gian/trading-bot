# CURRENT TASK — PROSPECTIVE-SHADOW-EVIDENCE-INTEGRITY-HARDENING-V1_1

Status: IMPLEMENTED_PENDING_RESEARCH_DIRECTOR_REVIEW

Starting HEAD: `c261a63ec13ac4d5d147f942cfebf33e55b12b25` on local `main`.

The Research Director accepted `PROSPECTIVE-SHADOW-PAPER-OBSERVER-V1` as software. That
implementation produced zero genuine prospective observations, so its evidence contract
is recorded `IMPLEMENTED_SUPERSEDED_BEFORE_FIRST_REAL_OBSERVATION` and preserved as
implementation history. Nothing was migrated, because there was nothing to migrate.

`FUTURE_SHADOW_PAPER_EVIDENCE_V1_1` and `PROSPECTIVE_SHADOW_PAPER_OBSERVER_V1_1` harden
evidence integrity before the first genuine observation. `BUILD_PROVENANCE_V1` identifies
a scientific build by git HEAD, branch, clean worktree, the application, observer,
strategy, execution and cost-model versions, and a manifest hashing the exact bytes of
every semantic source the observer depends on, with the cost implementation resolved from
the objects actually imported. Only a verified build may record a genuine decision; an
unverified or dirty build evaluates no signal and yields a typed missed decision once the
five-minute window closes.

A single interprocess lease is acquired before activation and held for the observer's
lifetime, so a second process cannot evaluate the market or write evidence and reports
`ANOTHER_OBSERVER_INSTANCE_ACTIVE`. Every governed transition appends one immutable
hash-linked audit event from an explicit `GENESIS`; the snapshot and chain share one
atomically replaced document, the chain is validated before evidence is used, and
integrity failure degrades the observer without rewriting anything.

ALIGNED, the execution geometry, the cost model, LONG/NO_TRADE semantics, manual paper V2,
historical research, and the 20-completed-trade review boundary are unchanged. Tests are
synthetic-clock and synthetic-feed only; the production observer was never deliberately
started and no genuine future observation was created. Historical accounting remains 26
experiments, 12 observed material historical hypotheses, zero sealed queries, Champion
`NONE`, and real money false.

Next action: RESEARCH DIRECTOR REVIEW.
