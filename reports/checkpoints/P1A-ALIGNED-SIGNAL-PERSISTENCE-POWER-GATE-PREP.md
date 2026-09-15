# Checkpoint — P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-PREP

Design and prospective power analysis only. No material experiment was executed, the
unshifted 120h ALIGNED result was not computed, and P1A is not preregistered.

Starting HEAD: `44c604508e470e4e06fa6ac5334d2c12f49c3d3e`.

## Question addressed

Not "does the ALIGNED signal persist to five days" — that is the future material
hypothesis `ALIGNED_SIGNAL_PERSISTS_TO_120H_V1`. This checkpoint answers only whether
BTC-only development data has sufficient prospective resolution to answer it at the
Owner's economic threshold.

Answer: **no**. `POWER_GATE_STATUS = REDESIGN_REQUIRED`.

## Frozen design

`research/design/ALIGNED_SIGNAL_PERSISTENCE_V1_DESIGN.md`, rationale in
`decisions/ADR-0013-P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE.md`.

- Primary horizon 120h, fixed by the five-day persistence question. No horizon search;
  24h retained only as the already-exposed historical reference.
- Primary measurement: 120h forward BTCUSDT price return in bps, starting at the governed
  next-1m open at the signal instant and ending at the close of the 1m bar opening at
  signal + 7199 minutes.
- No stop, target, trailing logic, R denominator or one-position-at-a-time rule.
- Raw ALIGNED signal events from the unchanged frozen decision logic; portfolio occupancy
  cannot suppress an event.
- Matched control: deterministic within-fold circular calendar shift, minimum absolute
  displacement 168 positions (≥168 hours), all admissible shifts enumerated, zero shift
  rejected by the API.
- Central estimator: arithmetic mean of placebo event-mean returns.
- `alpha_effective = 0.05 / 13`; target power 0.80; `P1A_INFORMATION_MESI_BPS = 24.0`.

## Signal

| fold | eligible decision instants | conditions emitted | raw events retained |
| --- | --- | --- | --- |
| DEV-2019 | 7871 | 45 | 38 |
| DEV-2020 | 7704 | 40 | 37 |
| DEV-2021 | 7884 | 13 | 12 |
| DEV-2022 | 8617 | 7 | 7 |
| DEV-2023 | 8496 | 45 | 43 |
| DEV-2024 | 8641 | 43 | 43 |
| total | — | 193 | **180** |

The historical 24h-containment window emitted 195 conditions and resolved 125 trades
after occupancy suppression. Moving to 120h containment shortens each fold's signal
window by 96 hours (195 → 193) and then requires a complete contiguous 7200-minute
forward path (193 → 180). Occupancy suppression is not applied here.

Frozen reference cadence 125/6 = 20.8333333333 events/year. Observed prep cadence
180/6 = 30.0 raw events/year.

## Power gate outcome

| quantity | value |
| --- | --- |
| admissible deterministic shifts | 7369 (168..7536) |
| placebo centre | 112.5650719822 bps/event |
| placebo range | −195.4117321016 .. 353.3469079357 bps/event |
| effective alpha | 0.0038461538461538464 (0.05/13) |
| minimum attainable randomization p | 0.000135685210312076 = 1/7370 |
| resolution sufficient | yes |
| one-sided critical excess | 216.4442374683 bps/event |
| empirical MDE at power 0.80 | **285.640052 bps/event** |
| power at the 24.0 bps MESI | **0.0142** |
| POWER_GATE_STATUS | **REDESIGN_REQUIRED** |

The design can only resolve an event-level edge roughly twelve times larger than the
effect that would matter economically. The randomization resolution is not the binding
constraint; the dispersion of the matched-timing null is.

Consequently: P1A is not preregistered, no runner candidate is registered, no other
horizon was tried, the MESI was not lowered and no asset was added.

## Leakage safeguards

- All aggregation routes through `placebo_pooled_mean_bps`, which raises
  `PrepModeViolation` for any circular displacement below 168 positions, zero included.
- A deterministic AST test proves no function in the prep surface aggregates outcomes
  outside that guarded path.
- `assert_no_result_leakage` fails closed on any artifact key that could carry the
  unobserved outcome; both committed JSON artifacts are checked.
- No actual zero-shift mean, ALIGNED-minus-placebo effect, P1A p-value or P1A performance
  classification exists in any artifact, and no future actual outcome artifact exists.

## Reproducibility

The full admissible placebo distribution is committed as
`reports/power/P1A-ALIGNED-SIGNAL-PERSISTENCE-NULL-DISTRIBUTION-V1.json`.
`scripts/audit_p1a_power_gate.py --check` re-derives the critical value, power and MDE
from it with no market data, so continuous integration audits the gate without touching
BTCUSDT bars. `--generate` rebuilds the distribution from the local development dataset.

## Scientific accounting

Unchanged: `experiments_completed` 26, observed material hypotheses 12, sealed queries 0,
Champion NONE, real money false, forward evidence NONE. ALIGNED semantics, stop, target,
volume, trend and breakout parameters untouched; historical research artifacts unchanged.

## Validation

`python scripts/check.py` exit 0 on a clean tree: governance, statistical audit, P1A gate
audit, ruff, mypy, 761 backend tests, 44 frontend tests, frontend build, and the
data-mode checks that reproduce the committed placebo distribution from the local
development dataset.

Exact head `8d3286a29093e542ed2fdeff5c457666dca5ea66` passed GitHub Actions run
`34993308932` (SUCCESS), evidence in
`reports/reviews/P1A-POWER-GATE-PREP-CI-EVIDENCE.json`.

Next action: Research Director review of the redesign decision.
