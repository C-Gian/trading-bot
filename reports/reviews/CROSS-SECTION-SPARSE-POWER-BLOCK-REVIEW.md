# Cross-section sparse power-block review

Research Director disposition: **POWER_BLOCKED_INFERENCE_CALIBRATION_FAILED_NOT_EXECUTED**

Reviewed hypothesis: `ALIGNED_COMMON_CROSS_SECTION_EFFECT_V1`.

## Disposition

The project did **not** observe the true zero-alignment cross-sectional ALIGNED effect.
This disposition is therefore none of the following:

- `REJECT`;
- `INCONCLUSIVE` market evidence;
- evidence that `beta <= 0`.

## Controlling facts

The immutable gate artifact `reports/power/CROSS-SECTION-POWER-GATE-V1.json` records:

1. frozen `CROSS_SECTION_MESI_BPS = 24.0` bps/event;
2. prospective `minimum_detectable_effect_bps = 44.872236` bps/event;
3. prospective `power_at_MESI = 0.211674` against a `target_power` of `0.80`;
4. the frozen analytic two-way clustered inference failed its own placebo calibration:
   empirical rejection `3.55%` against a nominal `0.05 / 13 = 0.385%`, a 9.2x size
   inflation with exact binomial `p = 1.26e-8`.

Two independent failures — insufficient resolution at the frozen threshold, and an
inference procedure the placebo showed to be anti-conservative.

## Authorization

No same-hypothesis inference rescue is authorized. Under this disposition the executor
may not try another sparse-ALIGNED placebo, change the universe, change the liquidity
cutoff, change the horizon, change MESI, choose assets, or change ALIGNED.

All `CROSS-SECTION-FEASIBILITY-AND-POWER-DESIGN-V1` artifacts are preserved
byte-identically.

## Accounting

No material economic hypothesis was consumed. Completed experiments remain 26, known
observed material economic hypotheses remain 12, sealed queries remain 0, Champion
remains `NONE`, and real money remains false.
