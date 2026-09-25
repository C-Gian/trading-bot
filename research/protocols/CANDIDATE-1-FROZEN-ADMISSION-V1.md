# Candidate #1 frozen admission specification V1

`CANDIDATE_1_FROZEN_ADMISSION_V1` — frozen by the Research Director on 2026-09-25 under Astra
adjudication `PRIOR_SUPPORT_DIAGNOSTIC_NONAUTHORITATIVE — ONE_DIRECTOR_FROZEN_ADMISSION_ALLOWED`
([ADR-0037](../../decisions/ADR-0037-CANDIDATE-1-ASTRA-ADJUDICATION-AND-FROZEN-ADMISSION-SPEC.md)).
Strategic authority: `ASTRA_TRADING_BOT_STRATEGIC_OPERATING_DIRECTIVE_V2`.

This document is frozen **before** the admission calculation runs. Budget: exactly one support
calculation; a deterministic rerun only to correct a demonstrated implementation defect without
changing this specification. No threshold grid, preview run, alternate cooldown, alternate risk
normalization, alternate state definition or new source. No forward return, trade outcome,
label, model or backtest performance is computed or inspected.

The earlier executor diagnostic (`research/candidates/evidence/CANDIDATE-1-EXECUTOR-SUPPORT-DIAGNOSTIC-V1/`,
73 events / 25 joint-state) is `EXPOSED_SUPPORT_DIAGNOSTIC — DIRECTOR_UNAPPROVED_SPECIFICATION`:
preserved, non-authoritative, and not an input to this admission.

## 1. Data and interval

Only already-authorized cached pre-cutoff data:

- traded BTCUSDT spot and USD-M perpetual 1m klines, `BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1`
  (loaded through `taker_flow_source.load_minute_books`, official-checksum verified);
- USD-M OI 5m **quantity** `sum_open_interest`, `BTCUSDT-USDM-OPEN-INTEREST-DEV-v1` (loaded
  through `open_interest_source.load_open_interest`; notional OI is excluded).

Evaluation interval: the previously admitted OI interval 2022-2024. Excluded OI years are not
restored.

## 2. Sharp sell-off event (Director-frozen)

Hourly decision grid. For completed hour `T`:

- `R4 = log(spot_close_T / spot_close_(T-4h))`;
- prior hourly realized volatility from the 168 completed 1h returns ending at `T-4h`; the shock
  interval does not enter the risk estimator;
- `shock_z = R4 / (sigma_prior_1h * sqrt(4))`;
- sharp sell-off iff `shock_z <= -2.0`;
- trigger only on the first crossing from `shock_z > -2.0` to `shock_z <= -2.0`;
- after a trigger, new triggers are suppressed for 4 hours (operational episode/occupancy rule,
  not a claim of statistical independence).

## 3. Positioning state (Director-frozen)

At the same `T`, both:

1. `log(OI_T / OI_(T-4h)) < 0` (OI quantity);
2. `log(perp_close_T / spot_close_T) - log(perp_close_(T-4h) / spot_close_(T-4h)) < 0`
   (synchronized traded prices).

No magnitude thresholds, no OR condition, no extra gates. Candidate events: sell-off episodes in
the joint state. Control events: valid sell-off episodes not in the joint state.

## 4. Availability semantics (Director-frozen)

Operational decision timestamp `T + 15 minutes`. Inputs refer only to observations timestamped
no later than `T` and satisfy the inherited source-quality / strict-prior rules. The 15-minute
delay is an explicit historical availability assumption, not proof of publication latency.

**Defensibility (decided before execution): SUPPORTED.** `PREDICTIVE_OPEN_INTEREST_STRUCTURE_V1`
§3 already records the residual assumption that the archive's publication lag does not exceed
five minutes (newest usable record `T_decision - 5m`). Here every OI observation is stamped
`<= T` and the decision is at `T + 15m`, so the assumption required is a lag of at most 15
minutes — strictly weaker than the contract's recorded residual assumption. Klines are completed
bars (close time `T - 1ms`). The assumption is therefore at least as conservative as existing
provenance, and no delay tuning occurs.

## 5. Implementation readings fixed before execution

These resolve wording only; none is a scientific alternative, and none may change after the
calculation.

1. `spot_close_T` / `perp_close_T` = close of the completed 1m kline `[T-1m, T)` (close time
   `T - 1ms`), status `VALID` in the verified minute book. Grid `T` = every UTC hour boundary.
2. Prior returns: `r_k = log(close_(T-4h-(k-1)h) / close_(T-4h-kh))`, `k = 1..168`, requiring all
   169 spot closes valid. `sigma_prior_1h = sqrt(mean(r_k^2))` (zero-mean realized volatility).
   `shock_z` is undefined if any required close is missing or `sigma_prior_1h = 0`.
3. First crossing at `T` requires `shock_z(T) <= -2.0` **and** `shock_z(T-1h)` defined and
   `> -2.0`. An hour whose previous `shock_z` is undefined is not a trigger; such hours are
   counted and reported (`SPOT_CROSSING_UNDETERMINED`).
4. Cooldown: after a trigger at `T`, crossings at `T+1h`, `T+2h`, `T+3h` are suppressed (and do
   not start a new cooldown); the next trigger may occur from `T+4h`, whose `R4` window does not
   overlap the previous one. Triggers are computed on the full spot grid.
5. Episode domain: `2022-01-01T04:00Z <= T <= 2024-12-31T23:00Z`, so that `T-4h` lies in the
   admitted interval and `T + 15m` precedes the development cutoff. Year = UTC year of `T`.
6. `OI_t` (for `t = T` and `t = T-4h`) = the record with the largest `create_time <= t`,
   inheriting the contract's quality rules: `t - create_time <= 10 minutes`, quantity finite and
   `> 0`, and `create_time >= 2022-01-01T00:00Z` (admitted interval). Every selected record is
   strictly prior to the decision timestamp `T + 15m`.
7. Intended sell-off episodes = spot-defined triggers in the domain. A valid synchronized
   episode additionally has valid perp closes at `T` and `T-4h` and valid `OI_T`, `OI_(T-4h)`.
   Exclusion reasons, first applicable wins: `PERP_CLOSE_MISSING`, `OI_NO_RECORD`,
   `OI_OUTSIDE_ADMITTED_INTERVAL`, `OI_STALE`, `OI_NON_POSITIVE`.
8. Candidate iff both differences are strictly `< 0`; every other valid episode is a control.

## 6. Reports (descriptive, not gates)

Candidate/control counts by calendar year, by fixed `shock_z` bands `(-inf,-4]`, `(-4,-3]`,
`(-3,-2]`, and by prior-volatility terciles of all valid episodes; min/median/max of `shock_z`
and `sigma_prior_1h` per group; source coverage; exclusion reasons; OI endpoint validity;
episodes whose `(T-4h, T]` OI window contains a gap or a 5m `|Δlog OI| > 0.05`; distribution of
`|log(perp/spot)|` at `T` and `T-4h` and the count above 50 bp. Magnitudes appear only as
admission descriptors.

## 7. Admission gates (all required)

| Gate | Rule |
|---|---|
| `AVAILABILITY_ASSUMPTION` | §4 defensibility — SUPPORTED before execution |
| `SOURCE_RELIABILITY` | valid synchronized episodes / intended episodes `>= 0.95` |
| `COMMON_SUPPORT` | years used = years with at least one candidate **and** one control; at least 2 such years; within those years the closed ranges `[min, max]` of candidate and control `shock_z` overlap, and likewise for `sigma_prior_1h` |
| `DETECTABILITY_12M` | `required_standardized_effect <= 0.50` |

## 8. 12-month necessary detectability screen (method frozen before the result)

Episode counts only.

- Conservative 12-month usable Candidate-event arrival:
  `n_12m = min(valid candidate episodes in 2022, in 2023, in 2024)` — the worst observed complete
  calendar year of the frozen support population (a year with zero counts as zero).
- Primary positive incremental contrast: matched candidate-minus-control episode differences,
  one-sided `alpha = 0.05`, target power `0.80`, maximum horizon 12 months.
- Optimistic independent-episode approximation (independent matched differences with a common
  standard deviation, normal approximation):
  `required_standardized_effect = (z_0.95 + z_0.80) / sqrt(n_12m)`, with exact standard-normal
  quantiles (`z_0.95 = 1.6448536`, `z_0.80 = 0.8416212`); infinite when `n_12m = 0`.
- Admission requires `required_standardized_effect <= 0.50` (equivalently `n_12m >= 25`).

This is a necessary feasibility screen, not an economic MESI and not an expected Candidate #1
effect. Threshold, event definition, arrival method and population are not altered after the
result.

## 9. Dispositions

- Every gate passes: `CANDIDATE_1_ADMITTED_FOR_PROTOCOL_DESIGN`. No market trial is authorized.
- Any gate fails: `CANDIDATE_1_CLOSED_CURRENT_ALLOCATION_SUPPORT_OR_FEASIBILITY`; project state
  `STRONG_STOP_PENDING_ASTRA`; the economic Candidate #1 hypothesis remains untested; no
  Candidate #2 or successor may be designed.
