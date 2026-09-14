# FUTURE_PAPER_EVIDENCE_V2

Version: `FUTURE_PAPER_EVIDENCE_V2`.

Execution: `PAPER_EXECUTION_V2_CAUSAL_NEXT_MINUTE`.

Status: accepted prospectively before any V2 paper trade exists. V1 remains historically
blocked by `BLOCKED_CAUSAL_ENTRY_TIMING_V1` and is not redefined.

## Causal lifecycle

The only authorized sequence is:

`ANALYZE → PERSIST INTENT → OBSERVE STRICTLY FUTURE MINUTE → FILL → MANAGE PAPER POSITION`

The server reevaluates the frozen ALIGNED paper candidate. `NO_TRADE` creates nothing.
For LONG, a first atomic commit persists an unarmed intent with entry price, stop, target,
expiry, and entry observation all unknown. Once that commit is durable, the server takes
the authoritative UTC `intent_persisted_at=P` and atomically arms the record.

`entry_not_before` is always the first UTC minute boundary strictly later than `P`:

- `P=10:23:17.500Z` → `10:24:00Z`;
- `P=10:24:00.000Z` → `10:25:00Z`.

The permitted predicate is `open_time > P`, never `open_time >= P`. Client timestamps
are ignored. A crash leaving only the unarmed first commit can be invalidated but can
never fill.

## Availability and timeout

Lifecycle runs only on explicit Owner refresh. It uses credential-free public BTCUSDT
spot 1m data and considers only completed candidate minutes. Before a candidate minute
completes, the intent remains `PENDING_ENTRY` without requesting or guessing its price.

A successful lookup permanently consumes each missing opportunity by advancing the
persisted `entry_search_cursor`; a minute that appears later behind that cursor can never
be used retroactively. A transport or acquisition error consumes nothing. The timeout is
exactly five completed legal 1m opportunities. If none can be truthfully obtained, the
record becomes immutable `INVALIDATED_ENTRY_UNAVAILABLE` with no fill or return.
An interrupted second intent commit recovers only as immutable
`INVALIDATED_INTENT_PERSISTENCE`; its unarmed record never has an eligible entry.

Every lifecycle read/modify/write is serialized both within and across local backend
processes. Staging data is flushed before same-directory atomic replacement; replacement
metadata is made durable with Windows write-through or a POSIX directory flush.

## Filled plan

The first available legal bar supplies its actual open as `entry_price`. Only then:

- `stop_price = entry_price × (1 - 0.02)`;
- `target_price = entry_price × (1 + 0.04)`;
- `expiry_time = entry_time + 1,440 minutes`.

STOP/TARGET/EXPIRY, gaps, costs, and `STOP_FIRST_V1` retain the already-validated
prospective execution behavior. The actual observed entry bar is persisted so later
provider omissions cannot rewrite the fill. Terminal records are immutable.

## Evidence and separation

Each record is `MANUAL_PROSPECTIVE_PAPER` and `OWNER_MANUAL`. This is genuinely
prospective evidence but discretionary Owner timing remains a possible selection bias.
It does not automatically update `forward_evidence`, `paper_trades_completed`, Champion,
or any experiment/search/fit counter. Only a later explicit Owner review may count a
genuine completed record.

The V2 store is `data/paper/PAPER_TRADES_V2.json`, separate from V1 and from development
experiments. Tests use isolated synthetic stores and never create a genuine paper trade.
Real capital, exchange orders, credentials, leverage, SHORT, and automatic execution are
forbidden.
