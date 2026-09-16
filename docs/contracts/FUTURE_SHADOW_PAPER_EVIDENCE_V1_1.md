# FUTURE_SHADOW_PAPER_EVIDENCE_V1_1

Version: `FUTURE_SHADOW_PAPER_EVIDENCE_V1_1`.

Observer: `PROSPECTIVE_SHADOW_PAPER_OBSERVER_V1_1`.

Evidence stage: `AUTOMATED_PROSPECTIVE_SHADOW_PAPER`.

Initiation mode: `AUTOMATED_RESEARCH_OBSERVER`.

Status: accepted prospectively before any automated observation or shadow trade exists.
The manual `FUTURE_PAPER_EVIDENCE_V2` contract and its durable store remain separate and
unchanged.

## Relationship to V1

`FUTURE_SHADOW_PAPER_EVIDENCE_V1` is
`IMPLEMENTED_SUPERSEDED_BEFORE_FIRST_REAL_OBSERVATION`. Its software was accepted, it
produced zero genuine prospective observations, and its contract and artifacts remain in
the repository as implementation history. Nothing is migrated, because there is nothing
to migrate. V1_1 strengthens evidence integrity before the first genuine observation and
changes no scientific semantics: ALIGNED, the execution geometry, the cost model, the
LONG/NO_TRADE decision rule, and the 20-trade review boundary are all unchanged.

## Verified build provenance

A scientific build is not identified by a commit alone. `BUILD_PROVENANCE_V1` records the
git HEAD, the branch where available, whether the worktree was clean, the application,
observer, strategy, execution, and cost-model versions, and a manifest that hashes the
exact bytes of every semantic source the observer depends on: the observer, the analysis
and continuation modules, the causal execution engine, the governed cost implementation
resolved from the objects actually imported, and this contract. The manifest and its
aggregate SHA256 are persisted with the evidence.

A genuine prospective decision may be recorded only under a verified build. For local
repository execution this requires a clean worktree and a resolvable HEAD. If the build
cannot be verified the observer reports `DEGRADED` with `UNVERIFIED_SCIENTIFIC_BUILD`,
evaluates no market signal, and permanently records the boundary as
`MISSED_PROSPECTIVE_DECISION` if the condition is not repaired inside the five-minute
decision window. A signal is never evaluated first and relabelled afterwards.

## Single active observer

Exactly one process may hold the scientific observer lease. It is acquired before
activation through an ordinary non-blocking OS file lock, held for the observer's
lifetime, and released on clean stop or when the process handle closes; no stale PID
heuristic is authoritative. A process that cannot take the lease does not activate a
second observer, reports `DEGRADED` with `ANOTHER_OBSERVER_INSTANCE_ACTIVE`, and neither
evaluates the market nor writes evidence. Per-file atomic locks continue to serialise
individual writes.

## Tamper-evident audit chain

Every scientific transition appends one immutable event to a logical append-only chain:
decision persisting, observed, missed, or suppressed; shadow intent persisting and
persisted; entry established; reconciliation that changes governed state; trade closed;
and data-quality failure. Each event carries a sequence number, event type, entity
identity, event timestamp, payload digest, the previous event hash, and its own hash,
which deterministically binds all of those fields. The first event links to the explicit
genesis value `GENESIS`.

Validation rejects a missing or duplicate sequence, a broken previous-hash link, an
altered event, reordered or deleted events, and a snapshot whose governed scientific
state disagrees with its latest event. The payload digest covers scientifically material
fields only, so routine bookkeeping does not manufacture events. There is no secret key:
this is tamper evidence and corruption detection, not authentication.

## Crash and load semantics

The snapshot and its audit chain live in one document written by a single atomic durable
replace, so a crash cannot leave the chain describing one state and the snapshot another.
The complete chain is validated on load before any evidence is used. If integrity
validation fails the observer is `DEGRADED`, no new scientific decision is evaluated, and
existing evidence is never automatically rewritten to make it validate again.

## Prospective decision clock

One local observer evaluates `ALIGNED_PARTICIPATION_CONTINUATION_V1` once for each new
completed UTC hourly boundary that occurs while the observer is active. Its first
eligible boundary is strictly after durable activation, under a verified build, while
holding the lease. It never catches up a signal boundary that passed while the backend
was stopped. Opening the backend is not itself an observation.

A decision must be evaluated and durably committed no later than five minutes after its
boundary. A boundary that was missed, or that cannot be recorded inside that window, is
permanently recorded as `MISSED_PROSPECTIVE_DECISION`; it can never create a later trade.
Every sound `NO_TRADE` and `LONG` decision is evidence and remains in the ledger.

## Durable LONG intent and entry

A LONG decision first commits an unarmed automated shadow intent. Only after that commit
is durable is the intent armed. Entry is the first available completed BTCUSDT one-minute
open whose timestamp is strictly later than durable intent persistence. The already
observed hourly boundary-minute open is forbidden.

Only one automated shadow intent or position may be active. A further LONG observation
is retained with status `LONG_SIGNAL_SUPPRESSED_ACTIVE_SHADOW_POSITION` but creates no
trade.

The frozen execution geometry is LONG-only spot with no leverage: 2% stop, 4% target,
1,440-minute maximum hold, `STOP_FIRST_V1` ambiguity handling, and
`BTCUSDT_SPOT_COST_V1`. Entry and exit observations are public read-only market data;
there is no credential, account, balance, or order endpoint.

## Restart and data quality

Missed decisions are never reconstructed. A pending entry interrupted by backend
downtime is closed without a fill. An already-entered prospective position may be
reconciled after restart using immutable public bars because its intent, entry, and full
execution rule were durable before those bars existed. Reconciliation preserves the
original timestamps and records restart metadata. Missing or inconsistent required bars
fail closed as a data-quality terminal state.

Observer health is stored separately from evidence. It records backend starts,
activations, heartbeats, successful market fetches, evaluated and missed boundaries, the
next expected boundary, build verification, lease ownership, and current errors. It never
implies availability while the app was closed.

## Scientific freeze and accounting

ALIGNED parameters, execution geometry, costs, and this observer contract are frozen
through at least 20 completed automated shadow trades. This is a minimum adaptation
boundary, not a sufficiency claim. Integrity fixes are versioned and never rewrite prior
evidence; a semantic change requires a new evidence version.

Automated observations are prospective evidence, not historical experiments, manual
paper evidence, Champion evidence, owner-authorized trades, or permission for real
capital. Historical accounting remains 26 completed experiments, 12 observed material
historical hypotheses, zero sealed queries, Champion `NONE`, and real money false.

The durable evidence store is `data/paper/FUTURE_SHADOW_PAPER_EVIDENCE_V1_1.json`. Health
is stored separately at `data/paper/PROSPECTIVE_SHADOW_OBSERVER_HEALTH_V1_1.json` and the
scientific lease at `data/paper/PROSPECTIVE_SHADOW_OBSERVER_V1_1.lease`.
