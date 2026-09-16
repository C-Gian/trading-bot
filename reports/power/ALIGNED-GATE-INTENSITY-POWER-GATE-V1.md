# ALIGNED gate-intensity power gate V1

Status: **REDESIGN_REQUIRED**

ALIGNED development family: **PARKED_DEVELOPMENT_SEARCH_EXHAUSTED**

Design and freeze only. No shifted effect, no zero-shift effect, no t, no p and no
per-asset effect was computed for either hypothesis.

## Frozen score

- definition: `GATE_INTENSITY = int(direction_pass) + int(breakout_pass) + int(participation_pass)`
- gate weights: [1, 1, 1] (unweighted integer sum)
- new gate parameters: 0
- ALIGNED == (intensity == 3): True

| intensity | rows |
| --- | ---: |
| 0 | 2,210,069 |
| 1 | 293,370 |
| 2 | 49,716 |
| 3 | 3,380 |

## Frozen randomization family

- method: CALENDAR_SYNCHRONOUS_WHOLE_WEEK_YEAR_SHIFT_V1
- unique vectors: 1024 of 1024 requested
- displacement band: 2..13 whole UTC weeks, signed, never zero
- circular wrap: False
- family SHA-256: `7e135af46a20c30d8c1f19e39d56b663254ab293b007c84a694437e82e8cf12d`
- support gate evaluated: False
- shifted effects computed: False

## Prerequisite gates

- DATA_SOURCE_STATUS: PASS
- UNIVERSE_FEASIBILITY_STATUS: PASS
- SURVIVORSHIP_STATUS: PASS
- EVENT_RECONCILIATION_STATUS: FAIL_CLOSED_NON_POINT_IN_TIME_PARTICIPATION_RULE
- RANDOMIZATION_SUPPORT_STATUS: NOT_RUN_BLOCKED
- RANDOMIZATION_INFERENCE_STATUS: NOT_RUN_BLOCKED

## Power

- MESI: 8.0 bps/gate
- effective alpha: 0.0038461538 (0.05 / 13, one-sided)
- target power: 0.8
- power at MESI: **not computed** (blocked before measurement)

EVENT_RECONCILIATION_STATUS failed closed: the retired placebo participation rule that separates the two frozen artifacts uses a whole-sample epoch length, which is not knowable at decision time. The support gate and the prospective power stages were therefore never run, so no shifted effect and no power number exists for this hypothesis.

Preregistration is not authorized by this artifact.
