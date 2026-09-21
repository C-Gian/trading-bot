# Checkpoint — PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1

Status: **COMPLETE**. Family disposition: **REJECTED_DEVELOPMENT_NO_SEALED**.

Starting HEAD `ea85142b1d17b3983fd4a15afae526140234f20c`. The one prospective source-semantics
remediation authorized for the ALFRED macro information family inside
`PREDICTIVE_RESEARCH_GENERATION_V1` was executed in full. Both preregistered configurations
were run and both failed the frozen advancement gate. Champion remains `NONE`, sealed queries
remain 0, real money remains `false`.

## 1. The predecessor, preserved

`PREDICTIVE-STAGE3-MACRO-VINTAGE-V1` remains immutable with disposition
`BLOCKED_MACRO_SOURCE_COVERAGE_V1`: 0 model fits, 0 outer predictions, 0 configurations
consumed, 0 sealed queries. It is not reclassified as negative market evidence and none of its
records were edited. The pre-execution admission of this checkpoint hash-pins its search plan,
source audit, admission, both preregistrations, its checkpoint report and its source contract,
and the deterministic validator re-checks those seven hashes on every run.

Its defect was a source-design defect, not a market result. It compared the *observation
period* date of the latest available release with the BTC decision date and rejected a monthly
release once that gap exceeded a fixed number of days. CPI describes a month that closed before
it was published, so the genuinely latest-known release was judged stale for most of every
month — 55,342 typed `CPIAUCSL_CURRENT_ANCHOR_UNAVAILABLE_OR_STALE` failures and 10.72%–13.73%
fold coverage.

## 2. Corrected source semantics

`docs/contracts/PREDICTIVE_MACRO_RELEASE_STATE_V1.md` separates two ideas the predecessor
conflated:

- **state persistence** — the last value actually published and available at `T` is the
  current known macro state and stays current until a later release becomes available;
- **interpolation or backfill** — inventing, forward-dating or importing a value that was not
  available at `T`, which remains forbidden.

Strict availability is unchanged: a decision at `T` sees only records whose conservative
`availability_time` is not later than `T`, and every anchor of one feature vector comes from
one and the same as-of-`T` snapshot. What changed is that the current known level is the value
on the greatest observation date in that snapshot, with no expiry measured against `T`.
Historical anchors keep their tolerances, measured against the intended historical anchor date.

The substrate is byte-identical to the predecessor's: manifest `ALFRED-MACRO-CONTEXT-DEV-v1`,
artifact SHA-256 `448f1ea8…`, catalog SHA-256 `cfc08c40…`, the same eight series, availability
rule `NEXT_CALENDAR_DAY_00_00_UTC_AFTER_VINTAGE_START`, current-revised substitution false,
post-2024 vintages 0.

## 3. Source gates, all decided before any fit

Source audit `SOURCE_GATES_PASSED`
(`reports/validation/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1-SOURCE-AUDIT.json`,
SHA-256 `1139b274…`).

**Semantics** were demonstrated, not asserted: 192 as-of-`T` snapshots rebuilt by independent
rescan with 0 mismatches; a synthetic later vintage invisible before and visible after its
availability boundary; a synthetic future monthly release invisible at `T` and current once
available; a latest-known monthly release unchanged across the stretch between releases; and
48 exact-month anchor checks with 0 mismatches, of which 25 are cases where the final revision
of that month differs from the as-of-`T` value, so reading a later revision would have shown up.
The monthly persistence probe held the same current CPI release for 481 consecutive decision
hours.

**Source-cadence integrity** passed. Maximum observation-date gaps against limits: `DFF` 1/10,
`DGS10` 4/10, `T10Y2Y` 4/10, `VIXCLS` 4/10, `NFCI` 7/21, `WALCL` 7/21, `CPIAUCSL` 31/70,
`UNRATE` 31/70. This is what makes persistence safe rather than a way to hide a frozen source.

**Coverage** was computed from canonical bar timestamps and macro source validity alone; no BTC
close, return, direction label or prediction entered the fold choice.

| fold | eligible | coverage | feature-valid history (days) | included |
| --- | --- | --- | --- | --- |
| 2019 | 8673 | 1.00000 | 81 | no |
| 2020 | 8713 | 1.00000 | 446 | yes |
| 2021 | 8699 | 1.00000 | 812 | yes |
| 2022 | 8737 | 1.00000 | 1177 | yes |
| 2023 | 8733 | 1.00000 | 1542 | yes |
| 2024 | 8760 | 1.00000 | 1907 | yes |

Five admissible folds against a declared minimum of five; pooled coverage 1.00000 against 0.95.
2019 is excluded on the same frozen 365-day history condition the predecessor used, not on
coverage — the substrate's first feature-valid instant is 2018-10-12. `N = 5` fixes the
two-thirds rule at 4 of 5. The 9,971 typed unavailable vectors all sit before 2019 in the
warm-up block, 8,597 of them on the CPI 12-month anchor at the start of the substrate.

## 4. Frozen family and identities

`PREDICTIVE_STAGE3_MACRO_RELEASE_STATE_FAMILY_V1`, `PREDICTIVE_MACRO_VINTAGE_FEATURES_V2` — the
same thirteen quantities in the same order as V1, under the corrected semantics. Direction and
calibrated probability only; no magnitude, no basis, no Stage-1 repair, no rejected-family
features.

- search plan SHA-256 `20c337d7…`
- predictive contract SHA-256 `5665b0ba…`
- `EXP-PRED-009-MACRO-RELEASE-STATE-LINEAR` (`H-PRED-MACRO-003`) preregistration `8ef79eb7…`
- `EXP-PRED-010-MACRO-RELEASE-STATE-HGBR` (`H-PRED-MACRO-004`) preregistration `a25a392c…`
- admission identity `10ac482089f40b8dc446188ae2abb9634b9914d6e5dc85f64e453890f5ab3cea`

Frozen before execution: MESI +0.015 absolute win-rate points, familywise alpha 0.05,
Bonferroni 0.025 each, 97.5% central paired interval, fold-stratified 48h moving-block
bootstrap, 10,000 replicates, seed 20260921. No threshold search, no hyperparameter search, no
feature search, no result-dependent early stop.

## 5. Results

20 model fits in total: per configuration, 5 direction bases and 5 training-only Platt maps,
one pair per included fold. 5 counted base-rate control fits. 43,642 eligible decision
timestamps, 43,641 candidate-actionable.

| configuration | win rate | coverage | n | matched base rate | primary delta | 97.5% interval |
| --- | --- | --- | --- | --- | --- | --- |
| `MACRO_RELEASE_STATE_LINEAR_V1` | 0.4824 | 0.99998 | 43641 | 0.5270 | −0.0446 | [−0.0675, −0.0196] |
| `MACRO_RELEASE_STATE_HGBR_V1` | 0.4814 | 0.99998 | 43641 | 0.5270 | −0.0457 | [−0.0693, −0.0210] |

Matched `ALWAYS_UP` 0.5270 for both. Brier: linear 0.2826, HGBR 0.2565, against the control's
0.2500 — both worse, and the linear head is the worse calibrated of the two. Matched
`PREVIOUS_24H_SIGN_PERSISTENCE` 0.4681 at coverage 0.99895, descriptive only and never
inverted.

Per-fold candidate minus control:

| fold | linear | HGBR |
| --- | --- | --- |
| 2020 | −0.1592 | −0.1615 |
| 2021 | −0.0108 | 0.0000 |
| 2022 | 0.0000 | −0.0082 |
| 2023 | −0.0528 | −0.0589 |
| 2024 | −0.0005 | 0.0000 |

Both configurations failed five of the seven conditions: the pooled delta, the interval lower
bound, the `ALWAYS_UP` floor, the Brier comparison and the two-thirds fold rule. Coverage was
emphatically not the confound — it is 1.00000 on four folds and 0.99989 on 2024. Terminal
classifications `NO_ADVANCE_MACRO_RELEASE_STATE_LINEAR_V1` and
`NO_ADVANCE_MACRO_RELEASE_STATE_HGBR_V1`; family `REJECTED_DEVELOPMENT_NO_SEALED`; sealed
eligibility `NOT_ELIGIBLE_REJECTED_DEVELOPMENT` for both.

2020 again dominates the pooled damage for both configurations, as it did for cross-asset
breadth, and it again carries the most lopsided matched base rate at 0.5807 UP. Recorded as an
observation for the Research Director, not as a rescue: the fold was admitted before any result
existed and may not be removed now.

## 6. Residual source finding, recorded not repaired

`reports/validation/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1-RESIDUAL-SOURCE-FINDING.json`,
`MACRO_RELEASE_STATE_FUTURE_DATED_OBSERVATION_V1`, disposition
`RECORDED_NOT_REPAIRED_REFERRED_TO_RESEARCH_DIRECTOR`.

Found after execution, after both configurations had been rejected: twenty rows of the admitted
substrate — all `VIXCLS`, all on US market holidays, maximum lead 3 days — carry an
`observation_date` later than their own `vintage_start`, so their conservative
`availability_time` precedes the day they describe. The raw ALFRED responses confirm it: the
vintage retrieved for 2018-10-05 already contains an observation dated 2018-10-08.

The V1 current-anchor rule took the latest observation *on or before* the decision date, so it
could never use such a row as the current level. The V2 rule frozen in the contract takes the
greatest observation date in the as-of-`T` snapshot and does not additionally require that date
to be at or before `T`. The contract text is silent on the case, so the implementation is
compliant with what was frozen; the gap is in the frozen wording.

Exposure over the included folds: 624 of 43,642 evaluation instants (1.43%) and 480 of 55,516
training instants (0.87%), all on the weekend before a holiday Monday, and only through
`LOG_VIX_LEVEL` and `VIX_LOG_CHANGE_5D`.

This is recorded, not repaired. Repairing it would be a third macro source semantics inside
`PREDICTIVE_RESEARCH_GENERATION_V1`, which the active work package forbids, and re-running the
family after its result is known is the post-result redesign the Constitution forbids. The
direction matters for interpretation: a lookahead can only flatter a candidate, and both
candidates were rejected by wide margins, so it cannot have manufactured the negative result.
It is referred to the Research Director as an open source-design question, and it should be
settled before any future family reuses `PREDICTIVE_MACRO_VINTAGE_FEATURES_V2` semantics.

## 7. Budgets and boundaries

- Family configurations: 2 planned, 2 consumed, 0 remaining; both executed regardless of the
  other's result; no post-hoc winner selection.
- Macro source-semantics versions: 1 authorized, 1 consumed, 0 remaining. The macro source
  design is closed for this generation; a third redesign is forbidden.
- Generation predictive configurations executed: 10. The eight prior results are byte-identical
  and hash-pinned by the admission.
- Sealed queries 0; post-cutoff access 0; Champion `NONE`; real money `false`; no prospective
  observer, no descendant tuning, no coverage gate changed after observation.

## 8. Validation

Backend tests, ruff check, ruff format, mypy, `scripts/check.py --no-data` and the full
installed-development-data validation all pass, including byte-identical replay of the source
audit, the residual finding and the complete research report, and an independent recomputation
of all seven advancement conditions for both configurations from the reported numbers.

Next: `RESEARCH_DIRECTOR_REVIEW_STAGE_3_MACRO_RELEASE_STATE_CLOSURE`.
