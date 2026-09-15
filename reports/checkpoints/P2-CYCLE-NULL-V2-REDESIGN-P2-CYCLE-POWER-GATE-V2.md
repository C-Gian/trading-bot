# P2 Null V2 redesign + power gate V2

Status: COMPLETED_PARTIAL_PENDING_RESEARCH_DIRECTOR_REVIEW

Starting HEAD: `bb3d9683c773755772bcbd7d7ce51c96b331041b` on local `main`.
Preregistration commit: `87b4bf2`.

## Result

Null V1 is preserved byte-identically and formally dispositioned
`FAILED_FIDELITY_REJECTED_FOR_INFERENCE`. Its 28 failed checks remain a methodological
failure; `BTC_TIME_CYCLE_STRUCTURE_V1` was neither rejected nor supported and remains
`DESIGNED_NOT_PREREGISTERED_NOT_EXECUTED`.

Null V2 froze direct stationary resampling of training-only raw contiguous 4h returns,
expected block length 1,080, no fitted mean/volatility model, and forced termination at
canonical gaps. No alternative block length was tried. The immutable V1 fidelity
criteria were bound by SHA-256 before topology measurement.

`BLOCK_SUPPORT_STATUS = REDESIGN_REQUIRED`. The actual canonical topology cannot retain
the required 90-day horizon:

| fold | segments | longest segment | mean realized block | survival 7d | 15d | 30d | 60d | 90d |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DEV-2019 | 11 | 807 | 221.97 | 0.8267 | 0.6668 | 0.4752 | 0.2359 | 0.0685 |
| DEV-2020 | 17 | 807 | 213.56 | 0.8377 | 0.6782 | 0.4644 | 0.2031 | 0.0698 |
| DEV-2021 | 24 | 807 | 208.82 | 0.8359 | 0.6786 | 0.4711 | 0.1924 | 0.0515 |
| DEV-2022 | 33 | 928 | 212.83 | 0.8315 | 0.6741 | 0.4623 | 0.1970 | 0.0701 |
| DEV-2023 | 33 | 2,216 | 294.59 | 0.8558 | 0.7172 | 0.5261 | 0.2776 | 0.1475 |
| DEV-2024 | 34 | 3,245 | 359.06 | 0.8701 | 0.7442 | 0.5673 | 0.3303 | 0.1983 |

Every fold is below the preregistered minimum 0.50 survival at lag 540. Per protocol,
the workflow stopped. Null V2 fidelity, joint spectral inference proof, compute
benchmarking, and synthetic detectability were not executed. `P2_POWER_GATE_STATUS =
REDESIGN_REQUIRED` is not a rejection of cycles.

## Integrity and accounting

No actual BTC training-selected period, validation spectral power, pooled primary
statistic, structural p-value or market classification was computed. No validation
return entered preparation and no sealed query occurred. The redesign adds exactly one
adaptive decision and one result-dependent fork; completed experiments remain 26 and
observed material economic hypotheses remain 12. Champion is NONE and real money is
false.

Next action: RESEARCH DIRECTOR REVIEW.

