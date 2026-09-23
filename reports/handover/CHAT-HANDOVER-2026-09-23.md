# CHAT HANDOVER SNAPSHOT — 2026-09-23

Classification: NON-CANONICAL_NAVIGATION_SNAPSHOT

This is a concise bridge between conversations. It does not override `state/current_state.json`,
`tasks/CURRENT_TASK.md`, ADRs, experiment artifacts or Git history. The next chat must verify
live `main` before acting.

## Owner / operating model

The Owner delegates quantitative research direction, architecture, experiment design and result
interpretation to ChatGPT as Research Director.

The Owner does not want to write/debug code or analyze raw experiment output.

Token-efficiency rule now frozen operationally:
- Codex/Claude Code primarily write code;
- the Owner runs heavy local acquisition, backtests, validations, Git commands and checks CI
  from copy/paste commands supplied by ChatGPT;
- ChatGPT interprets outcomes and decides the next checkpoint;
- target interaction is roughly one Owner execution step per research cycle, not repeated
  micro-interruptions.

No paid data for now. No real money.

## Product / scientific target

Current product scope remains BTCUSDT spot, LONG / NO_TRADE, paper only.

Prediction-first architecture:
`PREDICTION -> DECISION/POLICY -> ECONOMIC/EXECUTION SIMULATION`.

Generation V2 canonical action target remains 24h selective LONG:
`LONG iff calibrated p_up >= 0.60`, otherwise `NO_TRADE`.
The 10 frozen V2 advancement gates remain immutable for V2 admission experiments.

Magnitude remains `DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`.
Sealed queries = 0. Champion = NONE. Real money = false.

## Negative evidence that MUST survive the chat boundary

### Legacy / pre-pivot
Historical cost-expectancy research is preserved and superseded by the prediction-first Owner
objective. Do not treat the old ALIGNED work as a current Champion.

The append-only research registry under `research/memory/registry/` is mandatory search memory.

Important historical family relevant to the active direction:
- `FAM-ORDER-FLOW` (WP-007) already tested Binance spot exchange-reported taker-buy-share
  transition hypotheses.
- `EXP-ALG-012-ORDERFLOW-CORE` = `REJECT_COST_DOMINATED`.
- `EXP-ALG-013-ORDERFLOW-PRICE-RESPONSE` = `REJECT_COST_DOMINATED`.
- That evidence forbids simply retuning the 0.5 balance transition, context duration, barriers
  or old strategy gates after seeing the result.

### Predictive Generation V1
Generation V1 is closed:
`CLOSED_NO_DIRECTIONAL_ADMISSION_NO_SEALED`.

Executed predictive information families:
1. internal BTC OHLCV/price/volume/volatility;
2. settled funding;
3. open interest;
4. cross-asset breadth;
5. point-in-time macro release-state.

10 executed configurations, 0 advanced. This does NOT establish that BTC is unpredictable.
Macro-vintage source block is not counted as a market rejection.
Macro source-redesign budget is exhausted.
Cross-asset inversion remains forbidden.
Stage-1 substrate debt remains deferred and is not a rescue path.

### Predictive Generation V2 completed families
1. `PREDICTIVE_V2_DETERMINISTIC_CALENDAR_FAMILY_V1`
   - 2 configurations;
   - rejected development, no sealed;
   - action concentrated in 2021;
   - no credible enrichment/calibration.

2. `PREDICTIVE_V2_INTERNAL_STRUCTURE_SELECTIVE_FAMILY_V1`
   - 2 configurations;
   - rejected development, no sealed;
   - Linear: LONG N 3321, WR ~0.5495, enrichment ~+0.02335, 97.5% interval crosses zero;
   - HGBR: LONG N 3098, WR ~0.5145, enrichment negative;
   - both failed 8/10 advancement gates;
   - further work on the same internal feature family is parked.

## External research allocation

A separate BTC forecasting literature review was performed.

Research Director synthesis:
- model complexity by itself is not the missing ingredient;
- point-in-time on-chain exchange reserve/inflow/outflow is scientifically interesting at
  ~24h, but reliable retrospective entity-labelled PIT data appears commercial;
- CryptoQuant-style retrospectively revised exchange-wallet histories are not acceptable as
  PIT backtest inputs;
- the Owner chose NOT to pay for data now;
- paid PIT on-chain remains parked as a future enhancement if the free-data project later shows
  real potential;
- free exchange-native order-flow / lead-lag evidence tends to live at shorter horizons, so a
  horizon/source foundation is scientifically preferable to forcing another 24h V2 family.

Relevant decisions:
- `ADR-0031-V2-INTERNAL-CLOSURE-AND-ONCHAIN-PIT-ALLOCATION.md`
- `ADR-0032-OWNER-SELECTS-NO-COST-PUBLIC-DATA-PATH.md`

## Active checkpoint at handover

`tasks/CURRENT_TASK.md` =
`IMPLEMENT-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1`

Status at snapshot:
`ACTIVE_IMPLEMENTATION_ONLY_NO_EXECUTION`.

Frozen protocol:
`research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md`.

Purpose:
use free official Binance BTCUSDT 1m spot + USD-M perpetual klines to test a compact continuous
taker-flow imbalance signal across 24h -> 4h -> 1h, without opening another V2 admission family.

Frozen features:
1. spot 1h taker imbalance;
2. USD-M perpetual 1h taker imbalance;
3. spot minus USD-M imbalance.

One fixed logistic model + training-only Platt per horizon. No hyperparameter/feature/threshold
search. Primary foundation evidence is Brier improvement versus fold training-up-base-rate.

This is a legitimate structural revisit of historical order-flow evidence, NOT the project's
first order-flow test:
- prior WP-007 = spot-only event/transition strategy and economic/cost gate;
- current foundation = continuous spot + futures flow information, prediction-only scoring and
  explicit horizon-decay question.
It must NOT be used to retune or rescue WP-007.

Executor is authorized to IMPLEMENT ONLY. It must not download the full dataset, run the
foundation, perform full validation, do Git operations or poll CI.

Expected executor stop:
`CODE_READY` plus one acquisition command and one run command.

After CODE_READY:
1. Owner runs the acquisition command;
2. Owner runs the foundation/validation command;
3. Owner sends concise output/result paths to ChatGPT;
4. ChatGPT interprets and decides the next scientific action;
5. Git/CI are Owner-run from commands supplied by ChatGPT.

## Mandatory first action in the next chat

Read `docs/operations/NEW_CHAT_BOOTSTRAP.md`, resolve live main, then read live
`state/current_state.json` and `tasks/CURRENT_TASK.md`.

Do not create or propose another experiment before reconciling against the append-only research
registry and the predictive-generation negative evidence above.
