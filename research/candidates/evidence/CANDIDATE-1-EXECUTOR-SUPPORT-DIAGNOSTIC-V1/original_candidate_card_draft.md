# Candidate Card #1 — Positioning-conditioned recovery after a sharp BTC spot sell-off

Status: **`CANDIDATE_1_REJECTED_OR_BLOCKED`** — source and timing feasible; support-blocked
under the declared admission rule; closed before protocol design. No replacement candidate.
Decision: [ADR-0037](../../decisions/ADR-0037-CANDIDATE-1-SOURCE-SUPPORT-ADMISSION-BLOCK.md).
Authority: [ADR-0036](../../decisions/ADR-0036-OWNER-PRACTICAL-ECONOMIC-OBJECTIVE-AND-CONSTITUTION-V3.md),
`docs/canonical/RESEARCH_STAGE_POLICY_V1.md`, `docs/canonical/STRATEGIC_ALLOCATION_MAP_V1.md`.

This is the only Candidate Card allocated. Candidate Card #2 is not allocated.

## Scientific question

> Among comparable sharp BTC sell-offs, does simultaneous contraction in leveraged positioning
> and deterioration in perpetual-relative pricing identify temporarily pressured episodes with
> a materially better subsequent long outcome?

Observational predictive/economic hypothesis. Falling OI does not prove forced liquidation;
a perpetual discount does not prove mispricing. The legitimate distinct mechanism is the
conditional economic response of a jointly defined positioning state among comparable price
sell-offs. It must not be an old pullback rule plus another gate, old aggressive-flow logic
renamed deleveraging, marginal OI/funding prediction with a new label, or an exposed old
fixed-barrier target under another model.

## Lineage (already adjudicated; not repeated)

The historical evidence-salvage audit's eight-dimension lineage comparison classified the
candidate **`DISTINCT_BUT_HEAVILY_PRIOR_CONSTRAINED`**. Historical parents that constrain it:

- pullback / sell-off recovery lineage: `PULLBACK_RECOVERY_V1` (EXP-ALG-010, EXP-ALG-011) —
  closed, no historical rescue;
- OI quantity as a predictor: `PREDICTIVE_STAGE2_OPEN_INTEREST` (EXP-PRED-005/006) —
  `REJECTED_DEVELOPMENT_NO_SEALED`, source contract `PREDICTIVE_OPEN_INTEREST_STRUCTURE_V1`;
- settled funding: EXP-PRED-003/004 and `FAM-DERIVATIVES-SENTIMENT-CONTEXT` (WP-015);
- regulated-futures leveraged positioning: `FAM-CFTC-REGULATED-FUTURES-POSITIONING` (WP-017);
- aggressive order flow: `FAM-ORDER-FLOW` (WP-007) and `FAM-PUBLIC-TAKER-FLOW-PROBABILITY`
  (EXP-PRED-V2-005; EXP-PRED-V2-006 power-blocked), whose control set already contained the
  1h spot-minus-perpetual return.

Programme descriptors: allocation posture `LATE_STAGE_WITHIN_CURRENT_ENVELOPE` /
`RESEARCH_WARNING`; scientific coverage
`MATURE_NEGATIVE_PREDICTOR_RESEARCH_WITH_LIMITED_PLAYBOOK_COVERAGE`.

## Admission review (source / timing / support only)

Deterministic record: `reports/validation/CANDIDATE-1-SOURCE-SUPPORT-ADMISSION-V1.json`,
produced and replayed by `scripts/audit_candidate_1_admission.py` (`--check`). It computes no
forward return, label, outcome or model; no post-cutoff data; sealed queries 0. Support
definitions and the feasibility rule were declared in the script before it ran and are
diagnostic, not a frozen eligibility rule.

### Source assets and usable intersection

| Asset | Manifest | Coverage | Integrity |
|---|---|---|---|
| BTCUSDT spot 1m klines (traded) | `BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1` | 2020-01..2024-12 | 60 objects, official checksums; 2,325 absent + 8 incomplete minutes |
| BTCUSDT USD-M perpetual 1m klines (traded) | same | 2020-01..2024-12 | 60 objects, official checksums; 0 absent / invalid minutes |
| BTCUSDT USD-M OI 5m `sum_open_interest` | `BTCUSDT-USDM-OPEN-INTEREST-DEV-v1` | 2020-09-01..2024-12-31 | 1,583 daily objects, official checksums; 631 missing records in 155 gaps |

Raw overlap 2020-09-01..2024-12-31. **Admissible evaluation window 2022-2024**, carried forward
from the Stage-2 OI coverage/history gate; 2020-09..2021 records exist but are not
automatically admissible (2021 holds 148 of the 155 OI gaps).

### OI quantity / unit integrity, synchronization, missingness, discontinuity

- Quantity only (`sum_open_interest`, BTC contract quantity); notional excluded because it
  embeds price. Strict 5m grid, strictly increasing, 0 off-grid, 0 post-cutoff.
- 448 non-positive quantities, all exact zeros (2021: 10, 2022: 117, 2023: 16, 2024: 305) —
  an upstream archive quirk; treated as unavailable, never imputed.
- Hourly as-of OI availability in 2022-2024 >= 0.9957 under both timing rules; 24h OI change
  availability >= 0.9918.
- 5m |Δlog OI| > 0.05: 0 / 10 / 2 in 2022 / 2023 / 2024 (> 0.10: none) — no material
  discontinuity in the admissible window.
- Stress-event missingness: every declustered sell-off event in every year had complete OI,
  spot and perpetual inputs (completeness 1.0).

### Information availability / latency

The archive documents measurement time, not publication lag (residual assumption already
recorded by the OI contract). Defensible assumption for this candidate: the conservative rule
`create_time <= T - 5m` and `T - create_time <= 15m` (one full cadence of assumed lag). It
costs almost no availability relative to the contract rule (`create_time < T`, age <= 10m).
A confirmation-stage system would additionally have to log real arrival times. Traded 1m
klines are known at the minute's close.

### Traded perpetual versus traded spot relative price

`q_T = log(UM_PERP_1M_CLOSE / SPOT_1M_CLOSE)` on the completed minute `[T-1m, T)` of both
traded BTCUSDT instruments; deterioration `q_T - q_(T-24h) < 0`. Not mark, index, premium index,
funding or notional. |q| median 4.5 bp, p99 18.0 bp. Availability 2022-2024 >= 0.9995.
Residual asynchrony (last trades within the same minute) is bounded by one minute and is noise,
not look-ahead.

### Event / common support (no outcomes inspected)

Diagnostic sell-off: trailing 24h spot log return at `T` <= threshold, declustered 72h. Joint
state: 24h OI log change < 0 **and** relative-price 24h change < 0 (conservative OI timing).

| Threshold | 2022-2024 events | per year | joint state | complement |
|---|---|---|---|---|
| **-0.05 (reference)** | 73 | 24.3 | **25** | 48 |
| -0.075 | 32 | 10.7 | 16 | 16 |
| -0.10 | 9 | 3.0 | 4 | 5 |

Declared feasibility rule (reference threshold): >= 30 pooled admissible events per arm,
event input completeness >= 0.90, hourly joint availability >= 0.95 in each admissible year.
Result: completeness and availability pass; **joint-state arm 25 < 30 — FAIL**
(`support_feasible: false`).

Outcome-free detectability context (arithmetic only): at the admissible joint-state rate of
~8.3 events per year, a 12-month prospective confirmation would have a one-sided (alpha 0.05,
power 0.80) minimum detectable effect of about 0.86 per-event standard deviations
(`(z_0.95 + z_0.80) / sqrt(8.3)`), before any comparator variance — not a plausible economic
MESI for this mechanism inside the 12-month ceiling.

### Reuse versus new work

Reused unchanged: `taker_flow_source.load_minute_books` (verified traded klines),
`open_interest_source.load_open_interest` (verified OI), the OI as-of semantics, manifests and
checksum verification. New: only the admission audit script and its record. Nothing general
was rebuilt.

## Disposition

`CANDIDATE_1_REJECTED_OR_BLOCKED` — **blocked on support**, not rejected on outcomes: no
long outcome was ever computed, so nothing is known about the candidate's economics. Sources
and timing are feasible. The support shortfall under the declared rule, together with the
prospective event rate, means the candidate cannot plausibly reach a resolvable 12-month
confirmation.

Forbidden as rescue: lowering the support floor, changing the reference threshold, the
declustering window, the joint-state definition, the timing rule or the admissible years after
this record, or re-admitting the question under another name. Reopening requires Astra.

No replacement candidate is designed. Strategic reallocation is required before any new
market research.
