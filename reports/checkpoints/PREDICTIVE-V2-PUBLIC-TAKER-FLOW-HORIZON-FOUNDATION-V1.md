# Checkpoint — PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1

Status: **COMPLETE — FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY** (Research Director accepted,
[ADR-0033](../../decisions/ADR-0033-PUBLIC-TAKER-FLOW-FOUNDATION-1H-ONLY-AND-INCREMENTAL-ALLOCATION.md)).

Starting HEAD `5075a57ac0aec9d6630579db1317ab5aedd71f76`. The implementation, acquisition
manifest, result and report were produced in the working tree after that HEAD and are to be
committed together with this record.

## Identity

| Artifact | SHA-256 |
|---|---|
| `research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md` | `6fb5da71b18a44bd6c8891f50b0490311f48a988eef27ea46ff66546762fe012` |
| `data/manifests/BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1.json` (120 objects, official checksums verified) | `cf696350cfe6294ffcbb74bef657ba9e58be22d232e7aab30c9cc7aa4c204bc4` |
| `research/experiments/EXP-PRED-V2-005-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION/result.json` | `bc8150163b156840e711a916823ccd5dcd69bf747ab6e389302524d7a6497bbf` |
| `reports/research/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md` | `b77fe1f9c28bfc9fb057140b3a07b6f526bfab2c5af3a05d8528090b9bb0d50a` |
| `backend/app/predictive/taker_flow_foundation.py` | `4f633776a96716942bf4b8735395e7a233e59b721b2ea66bdded78d588a81d82` |
| `backend/app/predictive/taker_flow_source.py` | `83cab4b5cfcf785e1eb7c664b64fb66b8da086858e8ccc076af7db293e8bd644` |

The implementation hashes equal the ones the result pins.

## Execution (Owner, local)

- targeted tests `backend/tests/test_public_taker_flow_foundation.py`: 19 passed;
- acquisition: 120/120 objects verified; spot 2,325 absent and 8 incomplete minutes, USD-M
  none; 48 of 43,848 decision instants feature-unavailable;
- one run, 12 model fits (3 horizons x 4 annual folds), no search;
- `--check` deterministic replay: PASS.

## Result

| Horizon | Scored | Coverage | Brier improvement | 98.33% interval | Classification |
|---|---|---|---|---|---|
| 24h | 34997 | 0.9999 | -0.0037126 | [-0.0059875, -0.0013780] | NOT SUPPORTED |
| 4h | 35017 | 0.9999 | -0.0002184 | [-0.0007812, +0.0003397] | NOT SUPPORTED |
| 1h | 35030 | 0.9999 | +0.0006438 | [+0.0001705, +0.0011318] | SUPPORTED |

Frozen selection: `FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY`. The result artifact holds exact and
secondary values.

## Disposition

- 24h and 4h are closed for this source without rescue.
- 1h gets research budget only. It is not a strategy, not a Champion, not a sealed
  authorization, not a product-horizon change and not evidence of profitability.
- WP-007 `FAM-ORDER-FLOW` rejection is intact; this is a distinct structural prediction
  result recorded as descendant family `FAM-PUBLIC-TAKER-FLOW-PROBABILITY`.
- Next: `EXP-PRED-V2-006-PUBLIC-TAKER-FLOW-1H-INCREMENTAL`, preregistered in
  `research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-V1.md`, execution blocked
  pending `IMPLEMENT-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1`.
- Sealed queries 0. Champion NONE. Real money false.

## Record corrections (Research Director review of RECORDS_READY)

- Power gate: seed `2026092307` accepted; variance source frozen as
  `ANALOG_DEPENDENCE_AND_VARIANCE_PROXY` (exposed 1h flow-only minus base-rate per-row Brier
  differences, centred empirical noise distribution, empirical power at MESI and grid MDE).
  `MDE_IS_ANALOG_EXPECTED_DETECTABILITY_NOT_REALIZED_INCREMENTAL_VARIANCE`.
- Hypothesis `H-PRED-V2-PUBLIC-FLOW-INCREMENTAL-001` is distinct from experiment
  `EXP-PRED-V2-006-PUBLIC-TAKER-FLOW-1H-INCREMENTAL`.
- Search memory: predictive non-sealed outcome
  `research/memory/registry/outcomes/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.jsonl`;
  the registry now separates predictive outcomes from the sealed-candidate projection, which is
  unchanged.
- `contracts/project_state.schema.json` explicitly covers `chat_handover`, both public
  taker-flow blocks and the post-ADR-0031 values that had drifted; state validates.
- `scripts/check.py` recognizes the experiment, manifest and 120 official raw objects, verifies
  them against their official checksums, keeps the post-cutoff guard, and replays the
  foundation in data mode through `backend/app/predictive/taker_flow_validation.py`.
- The foundation protocol pin `6fb5da71…e012` was taken over the Windows CRLF working copy; its
  canonical text digest (`CANONICAL_UTF8_LF_TEXT_V1`, ADR-0034) is
  `fdb355fcb66566f83c0a10ff646ebf8647ccc1c83289bbec2ab1e2a84801b7cd`. The result is not
  rewritten: every raw pin is preserved and bound to its canonical text digest in
  `reports/validation/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1-TEXT-PROVENANCE.json`.
  Only those declared text dependencies use canonical identity; everything else stays raw-exact.
- Top-level state pointers now name this checkpoint (executor and reviewed), the active task as
  the next work package, and status `REVIEWED`; validation derives them from the records.
