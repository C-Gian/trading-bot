# ADR-0048 — Accept G1 implementation and authorize Phase A only

Status: ACCEPTED — Research Director, 2026-09-25

## Review conclusion

The ADR-0047 incomplete-bar correction at
`cf0f77d8534e0a474b0cbd8e6c0cfccfd7853fe7` is accepted.

The frozen System G1 Development V1 protocol hash remains unchanged.
The seven configuration identity and source bindings remain unchanged.
Only the intended recursive-indicator implementation identity changed.

Synthetic/no-data validation passes.

No real historical System G1 outcome has been inspected.

## Execution authorization

Authorize **exactly one real historical System G1 Phase A execution**:

`2021-01-01T00:00:00Z <= decision_time < 2023-01-01T00:00:00Z`

with 2020 used only for the frozen warm-up / forecaster training semantics.

Phase A evaluates exactly the seven frozen configurations:

1. S0
2. S_FULL
3. S_MINUS_CYCLE
4. S_MINUS_PARTICIPATION
5. S_MINUS_DAILY_HTF
6. S_P1_ONLY
7. S_P2_ONLY

and applies only the frozen automatic selection rule.

No human selection or override is authorized.

## Phase-scoped execution guard requirement

Before opening real market observations, the executor must make one mechanical safety change:

- execution authorization must carry an explicit allowed phase;
- the runner must pass the requested phase to the authorization guard;
- real sources must refuse unless the requested phase equals the currently authorized phase;
- this ADR authorizes only phase `A`;
- phase `B` must remain refused even after a successful Phase-A selection artifact exists.

This change is governance/execution safety only. It may not change:

- protocol;
- indicators;
- playbooks;
- cycle;
- forecaster;
- configurations;
- scoring;
- economic gates;
- costs;
- risk;
- source binding;
- windows.

The executor must complete no-data validation after this guard change and before opening real
observations.

## Phase A result handling

The Phase-A artifact is write-once.

After Phase A:

- immediately disarm real historical execution in canonical state;
- record Phase A as executed;
- record whether an automatically selected configuration exists;
- do not run Phase B;
- do not inspect 2023-2024 economics;
- leave the repository pending Research Director adjudication.

If no configuration is eligible, the frozen disposition is
`SYSTEM_G1_DEVELOPMENT_REJECTED_SELECTION_STAGE` and Phase B remains impossible.

If one configuration is selected, that result does **not** authorize Phase B. The Research Director
must inspect Phase A and separately authorize Phase B.

## Scientific meaning

Phase A is exposed historical development/selection evidence, not confirmation.

Its purpose is not to claim a winning strategy. It only determines whether any of the seven
predeclared G1 configurations earns access to the locked 2023-2024 Development evaluation.

Champion remains NONE.
Validated strategy remains NONE.
Production action remains NO_TRADE.
Real money remains false.
Sealed queries remain 0.
