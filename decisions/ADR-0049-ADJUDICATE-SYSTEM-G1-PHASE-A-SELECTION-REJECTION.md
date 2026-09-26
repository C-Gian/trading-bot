# ADR-0049 — Adjudicate System G1 Phase A: selection-stage rejection

Status: ACCEPTED — Research Director, 2026-09-26

## Evidence

Canonical result:

`research/experiments/SYSTEM-G1-DEVELOPMENT-V1/PHASE-A-SELECTION.json`

Result commit:

`25ff0df2ec9bc6327da865f5b6efa975f4509b47`

Self-hash:

`375c3a9720ea93467af60b0af44a4bf2a58d42ed314c3001669e93ad35f03655`

File canonical SHA-256:

`efa615028bba7fcf45d52f9f5a7ccad6eeb39d58bb13d55246f762913941b568`

Evidence class:

`EXPOSED_HISTORICAL_DEVELOPMENT_EVIDENCE`

## Adjudication

Accept the mechanical Phase-A disposition:

`SYSTEM_G1_DEVELOPMENT_REJECTED_SELECTION_STAGE`

No configuration passed every frozen 2021-2022 eligibility gate.

Therefore:

- selected configuration = NONE;
- Phase B is not authorized and is mechanically impossible under the frozen protocol;
- 2023-2024 configuration economics remain uncomputed;
- System G1 has not earned Development evaluation;
- Champion remains NONE;
- validated strategy remains NONE;
- production action remains NO_TRADE;
- real money remains false.

## What Phase A established

The seven configurations failed in two materially different ways.

### Frequency-rich variants were economically adverse

`S0`:

- 47 scorable trades, all in 2021;
- cumulative equity return about -4.51%;
- profit factor about 0.55;
- run drawdown stop triggered around 5.10%.

`S_MINUS_CYCLE`:

- 52 scorable trades, all in 2021;
- cumulative equity return about -5.05%;
- profit factor about 0.50;
- run drawdown stop triggered.

These variants had enough opportunities to expose materially adverse economics.

### Highly filtered variants were too sparse to support a claim

`S_FULL`:

- 3 scorable trades across two years;
- cumulative return about +0.68%;
- failed all minimum-frequency gates.

`S_MINUS_DAILY_HTF`:

- 4 scorable trades;
- cumulative return about +1.21%;
- both years positive but far below the frozen minimum-support requirements.

`S_P1_ONLY` was identical to `S_FULL`, showing P2 contributed no trade to the full configuration.

`S_P2_ONLY` produced zero trades.

`S_MINUS_PARTICIPATION` produced 17 trades and about -2.03% cumulative return.

The Phase-A result therefore does not support either:

- a sufficiently frequent profitable G1 configuration; or
- a sparse positive configuration with enough evidence to justify opening the locked evaluation period.

## Interpretation boundaries

This result rejects **System G1 as frozen**, not the Owner's professional multi-signal product mission
in general.

It does not prove that:

- trend/pullback trading is impossible;
- failed-auction trading is impossible;
- cycle information is useless;
- professional multi-signal trading cannot work.

It establishes that the exact G1 definitions, corroboration structure, risk/execution rules and
playbook constructions did not produce an admissible selection-stage system in 2021-2022.

No component may be declared useful merely because a sparse variant happened to have positive P&L.

## Source-boundary note

The Phase-A engine did not ingest/evaluate 2023-2024 configuration economics.

However, the current source layer loads the complete settled-funding file through 2024 into memory
before the causal engine consumes only pre-2023 settlements. The kline source may also open the next
monthly archive before the causal bound stops iteration.

This did not affect Phase-A decisions or selection because future timestamps were not delivered to
the engine, and the data are already exposed development data rather than sealed evidence.

Still, it is weaker phase-boundary hygiene than intended. Before any future staged historical
programme, source handles should be phase-bounded at I/O so future-period observations are not read
at all.

This note does not invalidate the Phase-A result.

## Performance-engineering note

Phase A required about 428 minutes.

The dominant cause is computational inefficiency in the frozen forecaster implementation: the
growing empirical training distribution is repeatedly sorted/reprocessed at each 15-minute issue.

Runtime is not scientific evidence and does not change the result.

Do not optimize the forecaster merely to rerun G1, because G1 is terminally rejected at selection
stage. Performance engineering should occur only if Astra authorizes a successor programme that
reuses this architecture.

## Strategic consequence

Under Constitution 4.0:

`SYSTEM_G1_REJECTED_PENDING_ASTRA`

No automatic System G2, Phase B, threshold rescue, playbook rescue, additional configuration,
timeframe change or model change is authorized.

Astra must decide whether the Owner's clarified professional-trader mission warrants one successor
system generation, requires architectural correction, or should be parked under the current
resource/data envelope.

The strategic review must treat Phase A as real negative evidence while distinguishing:

- excessive sparsity caused by conjunction-heavy corroboration;
- economically adverse permissive variants;
- P2's zero-trigger support problem;
- the possibility that G1's exact playbook constructions were too brittle;
- the need to preserve bounded search rather than rescue G1.

No real-money decision is involved.
