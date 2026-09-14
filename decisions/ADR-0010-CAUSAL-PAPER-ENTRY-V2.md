# ADR-0010 — causal paper entry V2

Status: accepted prospectively before any V2 paper trade exists.

## Decision

The active manual paper workflow is versioned as
`PAPER_EXECUTION_V2_CAUSAL_NEXT_MINUTE`:

`ANALYZE → PERSIST INTENT → OBSERVE STRICTLY FUTURE MINUTE → FILL → MANAGE PAPER POSITION`

The server first atomically persists an unarmed LONG intent. That durable record contains
no entry, stop, target, or expiry. Only after the first commit succeeds does the server
record authoritative UTC persistence instant `P` and arm the lower bound. The earliest
permitted entry is the minute boundary strictly later than `P`. Therefore a persistence
instant of `10:23:17.500Z` permits `10:24:00Z`, while exactly `10:24:00.000Z` permits only
`10:25:00Z`. `open_time >= P` is not the rule.

Lifecycle reconciliation considers completed 1m opportunities conservatively. A
successful check that finds a minute absent advances a persisted causal cursor, so an
earlier minute cannot later be backfilled into a trade. Transport failure advances
nothing. After five unavailable completed opportunities the intent terminates as
`INVALIDATED_ENTRY_UNAVAILABLE`.

Store mutations are serialized by a same-path thread lock and an operating-system file
lock, including across overlapping local backend processes. Each staged JSON document
is flushed before an atomic same-directory replacement; Windows replacement requests
write-through and POSIX replacement flushes the containing directory. A restart can
therefore recover either the prior complete record or the next complete record, never a
partially written fill.

The actual observed fill anchors the unchanged 2% stop, 4% target, and 1,440-minute
maximum hold. Records are `MANUAL_PROSPECTIVE_PAPER` with initiation mode `OWNER_MANUAL`.
They are prospective but remain vulnerable to discretionary click timing and do not
automatically establish unbiased forward evidence, a Champion, or permission for money.

## Why V1 remains blocked

V1 could reconstruct the signal-boundary minute open after manual analysis had already
observed that boundary. Production V1 creation remains fail-closed and its contract,
store identity, code, and historical record are not redefined. No genuine V1 paper trade
exists, so no prior evidence was contaminated.

## Safety boundary

All strategy decisions and timestamps are server-owned. The HTTP caller supplies no
decision, strategy, price, plan, or timestamp. V2 places no order, handles no credential,
supports no leverage or SHORT, and does not feed paper records into development research.
