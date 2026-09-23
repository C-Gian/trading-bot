# ADR-0035 — The 1h incremental taker-flow test is power-blocked and not executed

Status: RESEARCH_DIRECTOR_ACCEPTED (2026-09-23)

## Evidence reviewed

- Frozen protocol `research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-V1.md`
  and [ADR-0033](ADR-0033-PUBLIC-TAKER-FLOW-FOUNDATION-1H-ONLY-AND-INCREMENTAL-ALLOCATION.md).
- Owner-executed gate record
  `reports/validation/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1.json`
  (canonical text sha256 `09f5e05562aa6439a2e6a9a9b5fc2c94fde1293116502d9d74f08ba9562e5c01`)
  and its report (`26e65370eabc4104b28fb5999e9b72bdaef4f5b56a8b75d9556982287745bcd0`).
- Proxy replay of EXP-PRED-V2-005 1h: `REPRODUCED_EXACTLY` (35,030 scored rows).
- Owner deterministic `--check` replay: PASS.

## Result

`MDE_IS_ANALOG_EXPECTED_DETECTABILITY_NOT_REALIZED_INCREMENTAL_VARIANCE`

| Quantity | Value |
|---|---|
| Proxy | `ANALOG_DEPENDENCE_AND_VARIANCE_PROXY` |
| Frozen MESI | 0.00020 |
| Expected power at MESI | 0.1871 |
| Target power | 0.80 |
| Empirical analog MDE (grid 1e-7) | 0.0005414 |

## Decision

`EXP-PRED-V2-006-PUBLIC-TAKER-FLOW-1H-INCREMENTAL` (hypothesis
`H-PRED-V2-PUBLIC-FLOW-INCREMENTAL-001`) is terminally `POWER_BLOCKED_NOT_EXECUTED`.

Interpretation, preserved exactly:

- The gate does not show that 1h taker flow lacks incremental information.
- It shows that the frozen 2020-2024 historical design has insufficient expected
  detectability for the preregistered MESI 0.00020: power 0.1871 < 0.80, and the analog MDE
  0.0005414 exceeds the MESI.
- The price-only control and the price-plus-flow candidate were never fitted; their
  predictions were never generated; EXP-PRED-V2-006 model fits = 0; the incremental market
  outcome is unobserved. No result may be inferred for the incremental hypothesis itself,
  and it is not `INCREMENTAL_TAKER_FLOW_NOT_SUPPORTED_1H`.

Forbidden as a rescue: changing the MESI, the power method, the proxy, the seed, the block
length, alpha or target power after observing the gate; executing EXP-PRED-V2-006 anyway; or
re-running the gate under another definition and treating it as this hypothesis.

## Allocation

No successor engineering experiment is authorized. The active task becomes a Research
Director reallocation gate. A forthcoming independent strategic review may inform that
allocation; it is an input, not an authority over scientific truth.

## Permanent state

Sealed queries 0. Champion NONE. Real money false. Product horizon unchanged (24h).
EXP-PRED-V2-005 remains `FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY`.
