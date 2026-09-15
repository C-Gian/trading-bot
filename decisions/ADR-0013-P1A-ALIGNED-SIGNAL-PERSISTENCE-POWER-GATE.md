# ADR-0013 — prospective power gate for ALIGNED 120h signal persistence

Status: accepted as design and prospective power analysis. P1A is not preregistered and
was not executed. Measured gate outcome: `REDESIGN_REQUIRED`.

## Decision

Before any 120h ALIGNED outcome could be observed, the design of the future material
hypothesis `ALIGNED_SIGNAL_PERSISTS_TO_120H_V1` is frozen, and the Constitution's
"Future power gate" is applied to it prospectively using placebo timing only.

Frozen before result exposure:

- primary horizon 120 hours, fixed by the five-day persistence question, with no horizon
  search and with 24h retained solely as the already-exposed historical reference;
- primary measurement: 120h forward BTCUSDT price return in bps, starting at the governed
  next-1m open at the signal instant and ending at the close of the 1m bar opening at
  signal + 7199 minutes;
- no stop, target, trailing logic, R denominator or one-position-at-a-time rule;
- raw ALIGNED signal events, with portfolio occupancy explicitly unable to suppress one;
- matched control by deterministic within-fold circular calendar shift with a minimum
  absolute displacement of 168 positions;
- central estimator: arithmetic mean of placebo event-mean returns;
- effective alpha 0.05/13; target power 0.80;
- `P1A_INFORMATION_MESI_BPS = 24.0`.

Full design: `research/design/ALIGNED_SIGNAL_PERSISTENCE_V1_DESIGN.md`.

## Why circular shift rather than the available alternatives

ALIGNED fires in tight bursts: 180 raw events occupy 63 active ISO weeks in the historical
record. Four candidate dependence treatments were rejected.

Naive event IID assumes away the clustering that dominates the sampling variance of a
five-day return. The historical positive-ACF trade ESS is a diagnostic that P0.1 already
forbade as an inferential basis, and it is computed on a different metric and a different
holding rule. Ordinary event-index Newey-West corrects serial correlation along the event
index, not along calendar time, so it does not control the real dependence between two
events three hours apart. Independently resampled random events preserve the event count
but destroy the burst structure, producing an optimistically narrow null.

Circularly shifting the whole binary signal sequence inside a fold preserves the number of
signals, the within-fold clustering and cyclic order, annual market exposure, the horizon
and sparsity, while breaking the alignment between signal timing and the subsequent
return. The empirical spread of the resulting null is the honest answer to "how much does
matched random timing with this shape move a 180-event mean".

## Why the decision grid is the eligible instant sequence

The grid used for shifting contains only hourly instants with a complete contiguous 120h
forward minute path inside the fold. Shifting in that index space makes every shifted
event outcome-defined, so the event count is preserved exactly under every admissible
shift, with no dropped events and no imputation. Consecutive grid instants are at least
one hour apart, so a 168-position displacement is always at least 168 hours of calendar
time — a 48-hour margin beyond the 120h horizon in both circular directions.

Requiring instead that all shifted events land on eligible instants of the dense hourly
grid was rejected: with 89-100% eligibility per fold and up to 43 events per fold, it
would have left essentially no admissible shift and would have failed the gate for a
reason unrelated to detectability.

## Containment cost is recorded, not hidden

Lengthening the required forward containment from 24h to 120h moves each fold's last
admissible decision instant from 31 December to 27 December and requires 7200 contiguous
minutes. Emitted conditions fall from 195 to 193, and retained raw events to 180. The
reduction is reported in the gate artifact per fold.

## Outcome

7369 deterministic admissible shifts were enumerated with no random seed. The minimum
attainable randomization p-value is 1/7370, well inside the 0.05/13 effective alpha, so
resolution is sufficient. The empirical MDE is 285.640052 bps/event and empirical power at
the frozen 24.0 bps/event MESI is 0.0142.

BTC-only development data therefore does **not** have sufficient prospective resolution to
answer the five-day persistence question at the Owner's economic threshold: the design can
only detect an event-level edge roughly twelve times larger than the effect that would
matter. `POWER_GATE_STATUS = REDESIGN_REQUIRED`.

## Consequences

P1A is not preregistered, no runnable candidate is registered, no material experiment is
consumed, and the actual 120h ALIGNED outcome remains unobserved and unobservable from the
prep command. The MESI is not lowered, no other horizon is tried, and no asset is added.
`experiments_completed` stays 26, observed material hypotheses stay 12, sealed queries stay
0, Champion stays NONE and real money stays false.

The gate is auditable without market data: the admissible placebo distribution is committed
and `scripts/audit_p1a_power_gate.py --check` re-derives the critical value, power and MDE
from it deterministically.

Redesign is a Research Director decision. The design records, but does not choose among,
the structural levers that could change detectability: a materially larger event universe,
a lower-variance informational metric, or an explicit acceptance of the study as
exploratory non-resolution evidence under the Constitution's power gate.
