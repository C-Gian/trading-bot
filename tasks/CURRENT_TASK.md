# CURRENT TASK — G2-00-KNOWLEDGE-TO-CONTRACTS-V1

Status: RESEARCH-DIRECTOR-CONTRACT-FREEZE-ACTIVE — MARKET ECONOMIC EXECUTION FORBIDDEN

## Authority

- Owner Product Mission V2
- Constitution 4.0
- `reports/strategic/ASTRA_TRADING_BOT_DEVELOPMENT_SYSTEM_DIRECTIVE_V2.md`
- `decisions/ADR-0052-ADOPT-ASTRA-G2-DEVELOPMENT-SYSTEM-AND-OPEN-G2-00.md`
- `state/current_state.json -> current_project_status`

## Purpose

Translate the completed accessible professional-trading corpus and Astra's G2 directive into one
fully specified, implementable and causal contract package. This work package closes ambiguity before
engineering implementation. It does not test profitability.

## Required deliverables

1. `docs/canonical/G2_PROFESSIONAL_KNOWLEDGE_MODEL_V1.md`
2. `docs/canonical/G2_FORECAST_POLICY_EXECUTION_CONTRACTS_V1.md`
3. `research/g2/G2_DATA_EXPOSURE_AND_EXECUTION_MANIFEST_V1.md`
4. `research/g2/G2_CYCLE_CAUSALITY_CHECKPOINT_V1.md`
5. `research/g2/G2_DEVELOPMENT_PROTOCOL_V1.md`
6. `research/g2/G2_RESEARCH_LEDGER_V1.jsonl`
7. `tasks/G2_01_IMPLEMENTATION_PACKAGE_V1.md`

## Mandatory checkpoints

### CRYPTO-CONTRACT-01

Use current primary venue documentation only for instrument/price semantics, fields and units,
taker/aggressor semantics, funding timing/sign, contract filters, mark/index semantics and fee/cost
provenance. No crypto-alpha conclusion is permitted.

### CYCLE-CAUSALITY-01

Inspect the existing cycle implementation and lineage first. Use at most one method and validate only
causality/method quality on synthetic fixtures: noise, sinusoid + noise, trend without cycle,
changing frequency, jumps, prefix stability, declared lag and explicit `UNRELIABLE` behavior.
Passing does not establish predictive utility.

### DATA-EXPOSURE-01

Reconstruct the actual exposure boundary from repository manifests, ADRs and access history without
opening protected 2025+ price outcomes merely to document the boundary.

### DISTRIBUTION-PAYOFF-01

Freeze forecast target, label intervals, fit calendar, predictive-distribution semantics, trade
shadow labels, utility semantics and uncertainty scoring before economic replay.

## Design boundary inherited from Astra

- deterministic/versioned runtime;
- 15m completed-candle decisions;
- primary 4h market-return forecast;
- 1m raw/execution substrate;
- 1h local structure/timing;
- 4h directional context;
- completed Daily/Weekly context;
- six bounded knowledge families;
- transparent regularized predictive readout;
- separate transparent entry-utility readout;
- independent risk governor;
- market-only historical execution for V1;
- baseline + at most four substantive development revisions;
- at most two predeclared diagnostic group ablations;
- one revision slot reserved for cycle timing if the cycle method passes method quality.

These are design constraints, not validated alpha facts.

## Absolute prohibitions

No G1 rescue/rerun, BTC economic backtests, protected 2025+ outcome inspection for design,
parameter/timeframe/model tournaments, unbounded feature acquisition, DSR/PBO optimization, new
strategy implementation, prospective strategy collection, paper/real orders, leverage or real
capital.

Active alpha allocation remains zero.

## Gate A

Pass only when the repository answers without interpretation:

- what information was available at decision time;
- what is forecast and when it matures;
- how uncertainty, probability and conviction differ;
- why the action is LONG, SHORT or NO_TRADE;
- how entry, stop, expiry, payoff and risk are calculated;
- what happens when cycle/data/model state is unavailable;
- what is a bug fix versus a scientific revision;
- how many development attempts remain;
- which historical data may and may not be read;
- what G2-01 must implement and test.

No economically material `TBD` may remain before G2-01.

## Executor status

No G2 coding implementation task is active until Gate A passes.

## Current operational truth

- G1: CLOSED / TERMINAL PARK
- G2: DEVELOPMENT SYSTEM ALLOCATED
- current package: G2-00
- economic market execution: FORBIDDEN
- protected evaluation: NOT AUTHORIZED
- future paper: NOT AUTHORIZED
- validated strategy: NONE
- Champion: NONE
- operational action: NO_TRADE
- real money: false
