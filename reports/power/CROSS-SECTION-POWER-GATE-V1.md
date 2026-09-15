# Cross-section common-effect power gate V1

Status: **REDESIGN_REQUIRED**

Design and power preparation only. The true (zero-alignment) pooled ALIGNED effect,
its t statistic, its p value and every per-asset real effect remain uncomputed.

## Panel

- decision rows: 2,547,356
- instrument epochs: 355
- distinct decision times: 40,141
- raw ALIGNED signal events: 3,378
- occupancy suppression applied: False

## Inference support

- asset clusters with events: 258 (minimum 30)
- UTC week clusters with events: 184 (minimum 100)
- CLUSTER_SUPPORT_STATUS: PASS
- DEPENDENCE_INFERENCE_STATUS: PASS

## Placebo calibration

- placebo replicates: 338
- zero shift used: False
- event-count retention: 1.0
- PLACEBO_CALIBRATION_STATUS: REDESIGN_REQUIRED

## Prospective power

- MESI: 24.0 bps/event
- effective alpha: 0.0038461538 (0.05 / 13, one-sided)
- degrees of freedom: 183.0
- design standard error: 12.680466 bps
- empirical MDE: 44.872236 bps/event
- power at MESI: 0.2116739765
- target power: 0.8

## Prerequisite gates

- DATA_SOURCE_STATUS: PASS
- UNIVERSE_FEASIBILITY_STATUS: PASS
- DATA_FEASIBILITY_STATUS: PASS
- SURVIVORSHIP_STATUS: PASS
- CLUSTER_SUPPORT_STATUS: PASS
- PLACEBO_CALIBRATION_STATUS: REDESIGN_REQUIRED
- DEPENDENCE_INFERENCE_STATUS: PASS

Raw signals span 2019-02-05T18:00:00Z to 2024-12-28T01:00:00Z.

Preregistration is not authorized by this artifact.
