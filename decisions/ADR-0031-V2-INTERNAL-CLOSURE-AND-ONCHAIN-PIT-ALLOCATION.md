# ADR-0031 — Close V2 internal selective family; prioritize point-in-time on-chain exchange flows

Status: RESEARCH_DIRECTOR_ACCEPTED_PENDING_OWNER_DATA_ACCESS_DECISION (2026-09-21)

## Evidence reviewed

- `PREDICTIVE-V2-INTERNAL-STRUCTURE-SELECTIVE-V1` ending at
  `8ff94e93fde65a36c7bed048c34e90035fb851ac`;
- exact-head CI run `35624079509` = SUCCESS;
- external literature review `BTC Predictive Deep Research 2026`;
- current official Glassnode, CryptoQuant and Coin Metrics documentation reviewed by the
  Research Director on 2026-09-21.

## V2 internal selective verdict

Accept the executor disposition `REJECTED_DEVELOPMENT_NO_SEALED`.

Both frozen configurations passed only pooled action-coverage/count gates and failed the
per-fold support, 60% selective-win-rate, +5pp enrichment, positive dependence-aware interval,
fold consistency, Brier and action-calibration gates.

The linear configuration's +2.34pp pooled enrichment is below the frozen +5pp gate and its
97.5% interval crosses zero. HGBR has negative pooled enrichment. Action is concentrated in one
fold and is absent in most folds.

No threshold, feature, fold, model, calibration or substrate rescue is authorized.

## Stage-1 substrate debt

Remain `DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH`.

The historical contiguity debt reduces early-fold feature availability, but it does not
plausibly explain the failed family: later full/high-coverage folds also produce no durable
selective action, and both models fail probability calibration and pooled directional gates.
Further internal-structure research is parked for now.

## Research allocation after external evidence review

Do not open a third V2 market-model family immediately.

Highest-priority untested mechanism at the current 24h horizon:
`POINT_IN_TIME_BTC_EXCHANGE_FLOW_STATE`.

Rationale:
- published BTC-specific evidence supports exchange reserve / inflow / outflow information as a
  plausible predictor of subsequent BTC returns;
- it is information-orthogonal to the rejected OHLCV, funding, OI, breadth, macro and calendar
  families;
- the mechanism is naturally compatible with selective LONG / NO_TRADE;
- entity-labelled exchange metrics have a material historical-revision/lookahead risk, so
  point-in-time source semantics are a prerequisite rather than an implementation detail.

## Current source feasibility ruling

1. Glassnode documents append-only Point-in-Time variants for BTC exchange balance, exchange
   inflow, outflow and related exchange metrics, explicitly intended for backtesting.
2. Glassnode's public pricing page currently exposes Point-in-Time metrics only on its
   Professional tier; Advanced does not include PIT metrics. Professional pricing/access is
   configurable rather than a fixed project-approved expense.
3. CryptoQuant explicitly states that its BTC exchange-flow history does not support PIT
   accuracy because wallet-address clustering is updated and historical values can change.
   Therefore retrospective CryptoQuant exchange-flow history is inadmissible for this project.
4. Coin Metrics documents exchange flow/supply as Network Data Pro. Community API existence does
   not establish that the required historical exchange-flow metrics are freely accessible or
   immutable point-in-time snapshots. It is not admitted as a free PIT substitute without a
   source-specific proof.

## Decision boundary

The scientifically preferred next experiment requires credentialed/commercial PIT exchange-flow
data unless an equivalent free PIT source is proven.

Purchasing or supplying credentials is an Owner decision. No purchase, signup, credential use,
trial activation or vendor contact is authorized by this ADR.

If the Owner authorizes professional/trial PIT data access, the next checkpoint will be a
source-only admission/coverage package before any model is fitted.

If the Owner declines paid/credentialed access, the Research Director will allocate next to a
no-cost horizon/source foundation using public exchange-native data rather than downgrade PIT
standards.

## Permanent state

- Generation V1 remains closed.
- V2 calendar family remains rejected.
- V2 internal selective family remains rejected.
- Magnitude remains `DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`.
- Sealed queries = 0.
- Champion = NONE.
- Real money = false.
