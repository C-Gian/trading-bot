# ADR-0023 — Prospective shadow evidence integrity V1_1

Status: ACCEPTED

Supersedes the evidence contract of [ADR-0022](ADR-0022-ALIGNED-FINAL-CLOSURE-AND-PROSPECTIVE-SHADOW-OBSERVER.md);
its scientific decisions remain in force.

## Context

The Research Director accepted `PROSPECTIVE-SHADOW-PAPER-OBSERVER-V1` as software.
Historical ALIGNED development remains `PARKED_DEVELOPMENT_SEARCH_EXHAUSTED` and the
primary research phase remains `PROSPECTIVE_EVIDENCE_COLLECTION`.

The V1 implementation produced zero genuine prospective observations. That leaves a
short window in which evidence-integrity semantics can be strengthened at no scientific
cost, because there is no recorded observation to migrate, reinterpret, or invalidate.
Three weaknesses were identified before that window closed.

First, the observer identified its scientific build with `git rev-parse HEAD` alone. A
commit says nothing about whether the working tree that actually produced an observation
matched it, so a modified checkout could have recorded evidence under a commit whose code
it was not running.

Second, per-file atomic locks serialise individual writes but do not establish that only
one observer is scientifically active. Two processes could each evaluate the same hourly
boundary and interleave individually-valid writes.

Third, a JSON snapshot alone cannot distinguish genuine evidence from a later edit. A
prospective ledger whose whole value is that it was written before the outcome was known
needs to make careless or partial modification detectable.

## Decision

Create `FUTURE_SHADOW_PAPER_EVIDENCE_V1_1` with observer
`PROSPECTIVE_SHADOW_PAPER_OBSERVER_V1_1`, and record
`FUTURE_SHADOW_PAPER_EVIDENCE_V1` as
`IMPLEMENTED_SUPERSEDED_BEFORE_FIRST_REAL_OBSERVATION`. Nothing is migrated or
fabricated; the V1 contract and artifacts stay as implementation history.

Adopt `BUILD_PROVENANCE_V1`. A scientific build records its git HEAD, branch, clean or
dirty worktree, application, observer, strategy, execution and cost-model versions, and a
manifest hashing the exact bytes of every semantic source the observer depends on. The
cost implementation is resolved from the objects the observer actually imports rather
than a hand-written path, so the manifest cannot drift from repository truth. A genuine
prospective decision may be recorded only under a verified build, which for local
repository execution requires a clean worktree. An unverified build reports `DEGRADED`
with `UNVERIFIED_SCIENTIFIC_BUILD`, evaluates no market signal, and lets the boundary
become a typed missed decision if the condition is not repaired inside the frozen
five-minute window.

Adopt a single interprocess observer lease acquired before scientific activation, held
for the observer's lifetime, and released by the operating system even on unclean exit.
A process that cannot take it does not become a second observer and reports
`ANOTHER_OBSERVER_INSTANCE_ACTIVE`.

Adopt `SHADOW_EVIDENCE_AUDIT_CHAIN_V1`. Every governed transition appends one immutable
event whose hash binds its sequence, type, entity, timestamp, payload digest and the
previous event hash, starting from an explicit `GENESIS` value. The snapshot and the
chain live in one atomically replaced document and the chain is validated before any
evidence is used. Integrity failure degrades the observer and never rewrites evidence.

## Consequences

The observer becomes scientifically evidence-ready. The first genuine boundary must be
strictly after durable activation, under a verified clean build, while holding the lease.
Opening the backend is not itself an observation.

ALIGNED, the execution geometry, the cost model, the LONG/NO_TRADE rule, the manual
paper V2 workflow, and the 20-completed-trade review boundary are unchanged. Historical
accounting remains 26 experiments, 12 observed material historical hypotheses, zero
sealed queries, Champion `NONE`, and real money false.

The audit chain is tamper *evidence*, not authentication. There is deliberately no secret
key, so anyone able to rewrite the entire file could recompute a consistent chain. What it
guarantees is that partial edits, reordering, deletion, corruption, and snapshot/audit
divergence cannot pass validation. Stronger guarantees would need an external notary,
which is not justified at this stage.

Requiring a clean worktree means ordinary local development while the backend runs
produces missed boundaries rather than evidence. That is the intended trade: a gap in
observation is recoverable, a scientifically unidentifiable observation is not.
