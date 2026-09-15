# P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-V1

Design: `ALIGNED_SIGNAL_PERSISTENCE_V1`. Future hypothesis: `ALIGNED_SIGNAL_PERSISTS_TO_120H_V1`.

Prospective design and power analysis only. The unshifted 120h ALIGNED result was
not computed, no material experiment was executed, and P1A is not preregistered.

## Signal

- raw ALIGNED signal events: 180
- per fold: DEV-2019 38; DEV-2020 37; DEV-2021 12; DEV-2022 7; DEV-2023 43; DEV-2024 43
- frozen reference cadence: 20.8333333333 events/year
- observed prep cadence: 30.0 events/year
- portfolio occupancy suppression: not applied (information study)
- ALIGNED semantics changed: False

## Primary design

- horizon: 120h (7200 minutes)
- metric: FORWARD_120H_BTCUSDT_PRICE_RETURN_BPS
- start price: GOVERNED_NEXT_1M_OPEN_AT_SIGNAL_INSTANT
- terminal price: CLOSE_OF_THE_1M_BAR_OPENING_AT_SIGNAL_PLUS_7199_MINUTES
- stop / target / trailing: False / False / False
- one position at a time: False
- R denominator: False
- costs: IDENTICAL_FOR_SIGNAL_AND_PLACEBO_DIFFERENTIAL_IN_EXCESS_BPS

## Matched timing control

- method: DETERMINISTIC_WITHIN_FOLD_CIRCULAR_CALENDAR_SHIFT_V1
- central estimator: ARITHMETIC_MEAN_OF_PLACEBO_EVENT_MEAN_RETURNS
- minimum displacement: 168h
- admissible shifts: 7369 (168..7536)
- placebo centre: 112.5650719822 bps/event
- placebo range: -195.4117321016 .. 353.3469079357 bps/event
- event count, clustering, exposure, horizon and sparsity preserved

## Economic threshold

- Owner annual MESI: 500.0 bps/year
- translation: 500 bps per year / (125 resolved DEFAULT trades / 6 annual folds) = 24.0 bps
- P1A event-level MESI: 24.0 bps/event
- 24 bps per event is a NECESSARY informational lower bound at roughly the historical ALIGNED product cadence. It is not sufficient evidence that a 120h execution strategy would earn five percentage points per year; execution feasibility under longer holding belongs to P1B.

## Power

- prospective family size: 13
- effective alpha: 0.0038461538461538464
- basis: HOLM_FIRST_RANK_FAMILYWISE_THRESHOLD_ALPHA_0.05/13_TWELVE_OBSERVED_MATERIAL_HYPOTHESES_PLUS_P1A
- target power: 0.8
- empirical MDE: 285.640052 bps/event
- power at MESI (24.0 bps): 1.4249%
- minimum attainable randomization p: 0.000135685210312076
- randomization resolution sufficient: True

## POWER_GATE_STATUS: REDESIGN_REQUIRED

- integrity tests pass: True
- preregistration authorized: False
- runner candidate registered: False
- next action: RESEARCH_DIRECTOR_REVIEW

The documented material family is a lower bound; pre-repository exposure remains unquantified and is not converted into a numeric family size.
