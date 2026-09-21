# PREDICTIVE_V2_INTERNAL_CAUSAL_FEATURES_V1

The information boundary of the second Generation V2 family,
`PREDICTIVE_V2_INTERNAL_STRUCTURE_SELECTIVE_FAMILY_V1`.

This contract **inherits** a definition. It does not restate one.

## Inheritance

| | |
| --- | --- |
| V2 feature identity | `PREDICTIVE_V2_INTERNAL_CAUSAL_FEATURES_V1` |
| inherited definition | `PREDICTIVE_INTERNAL_CAUSAL_FEATURES_V1` |
| definition module | `backend/app/predictive/internal_features.py` |
| definition rewritten | no |
| feature count | 18 |

The eighteen causal quantities, their order, their formulas, their two named degenerate
values and their availability rule live in the module above and are reused byte-for-byte. The
V2 module `backend/app/predictive/internal_selective_features.py` names that definition and
calls its builder; it defines no formula of its own.

This is deliberate. A transcribed copy of a frozen definition can agree with itself while
drifting from the immutable Generation V1 record, and the drift would be invisible in every
artifact that quotes the copy. Reuse is therefore proved on fixed fixtures rather than
asserted in prose.

## Ordered features

1. `logret_1h`
2. `logret_6h`
3. `logret_24h`
4. `logret_72h`
5. `logret_168h`
6. `rv_6h`
7. `rv_24h`
8. `rv_72h`
9. `rv_168h`
10. `signed_efficiency_24h`
11. `signed_efficiency_72h`
12. `signed_efficiency_168h`
13. `up_fraction_24h`
14. `up_fraction_168h`
15. `close_position_24h`
16. `close_position_168h`
17. `log_volume_relative_24h`
18. `log_volume_regime_24_168h`

## Information boundary

At decision timestamp `T`, only completed canonical BTCUSDT 1h bars at or before `T` may
enter. The bar `[T, T+1h)` is completed at `T` and is readable; the horizon bar is the label
and is never readable. The full causal surface is exactly the 169 bars `T-168h .. T`
inclusive, which `feature_source_open_times` returns and a guarded bar index asserts against.

No label, external source, future bar, funding, open-interest, cross-asset, macro, news,
sentiment or on-chain value participates.

## Availability — unchanged, and not repaired

Every hourly bar in the 169-bar lookback must exist and be complete. All closes used in logs
must be strictly positive, volume must be non-negative and the volume denominators strictly
positive. A zero efficiency denominator yields `0.0`; a zero rolling high-low range yields
`0.5`. Anything else invalid or non-finite makes the **whole** vector unavailable.

Nothing is interpolated, forward filled, backward filled or substituted by a nearest bar.

The Stage-1 substrate debt remains **deferred and unrepaired** in this family. A
feature-unavailable row keeps its hour slot, carries no probability, is counted, and is
excluded from every rate — in training and in outer evaluation alike. It is never imputed.

No fold is removed because its feature availability is low, and feature availability never
redefines the primary control `FULL_FOLD_UP_RATE`. The feature-valid UP rate is reported
alongside it as mandatory secondary transparency, pooled from counts and never by averaging
fold rates.

## Separation from Generation V1 results

The definition is inherited; the evidence is not. No V1 fitted model, probability, score
tail, reliability bin or reconstructed action is loaded, read or consulted by this family's
design or execution. The V2 runner refits from the raw canonical bars, and the execution path
opens no result artifact at all — prior results are read in exactly one place, the pre-result
admission, byte-wise, for a digest.
