# System G1 Core Contracts V1

Status: **FROZEN FOR CHECKPOINT-1 SYNTHETIC IMPLEMENTATION**
Date: 2026-09-25
Parent: `docs/canonical/PROFESSIONAL_MULTISIGNAL_SYSTEM_ARCHITECTURE_V1.md`

This contract governs the synthetic causal vertical slice. It does not authorize market-outcome
inspection or historical G1 execution.

## 1. Time and availability

- All timestamps are UTC.
- Canonical raw market clock: 1m.
- Decision/forecast clock: completed 15m bars.
- A completed bar with interval `[t0,t1)` is available no earlier than `t1`.
- Higher-timeframe bars use deterministic UTC boundaries and are invisible until complete.
- Historical replay may expose only records with `available_at <= replay_cursor`.
- A value may carry both `market_time` and later `available_at`; consumers use the latter.
- No centered smoothing, future pivot, forward/backward filtering or future-labeled turn may enter
  the live/replay decision graph.

## 2. Core identity

Every run has immutable:

- run_id;
- configuration_id/version;
- algorithm version;
- source-manifest identities;
- input dataset interval;
- decision clock;
- forecast horizon;
- cost/risk contract version;
- creation/execution provenance.

Changing scientific semantics creates a new registered configuration/version.

## 3. Signal snapshot

Every signal snapshot stores:

- family;
- signal name/version;
- market_time / available_at;
- timeframe;
- numeric value(s);
- categorical state/direction;
- quality/readiness;
- role: ACTIVE / CONTEXT_ONLY / DIAGNOSTIC / METHOD_NOT_READY;
- reason text/code;
- source/state references.

Signals are measurements, not votes by default.

## 4. Market state

One immutable MarketState per decision candle contains:

- directional_bias: BEARISH / NEUTRAL / BULLISH;
- structural_mode: TREND / RANGE / TRANSITION / UNAVAILABLE;
- 1h structure state;
- 4h directional context;
- completed daily location/context;
- VWAP / prior-day boundary location where available;
- participation/flow corroboration state;
- cycle family summary;
- data/execution readiness;
- explicit supporting and opposing reasons;
- as-of/availability timestamps.

The state must preserve disagreement; it may not average away opposing higher/lower timeframe facts.

## 5. Conviction and actionability

Conviction:

- LOW — no complete approved setup or material contextual disagreement;
- MEDIUM — approved setup/context forming but trigger/corroboration incomplete;
- HIGH — exactly one approved playbook's complete frozen evidence/trigger pattern is satisfied.

Conviction is computed before outcomes and is not a probability.

Actionability is a separate object with:

- setup_ready;
- data_ready;
- execution_ready;
- risk_eligible;
- occupancy_free;
- final decision;
- blockers.

A HIGH-conviction state may still be NO_TRADE because of risk, data or occupancy.

## 6. PredictionSnapshot

Issue one snapshot at every eligible completed 15m candle, including LOW/neutral observations.

Required fields:

- prediction_id / run_id;
- algorithm/estimator/schema/source versions;
- issue_time;
- information_cutoff;
- available_at;
- decision timeframe = 15m;
- target_end = issue reference + 4h;
- reference instrument/price identity;
- directional bias;
- predicted direction: UP / DOWN / NEUTRAL / UNAVAILABLE;
- probability fields with explicit calibration status;
- mean and median terminal return;
- lower/upper terminal-return quantiles;
- standardized movement strength;
- prior-risk scale;
- uncertainty/support status;
- LOW/MEDIUM/HIGH conviction;
- actionability snapshot;
- playbook context;
- supporting/opposing family reasons;
- linked MarketState / CycleState / ModelArtifact IDs;
- missing-data/unavailable reason where applicable.

The prediction is immutable.

## 7. PredictionRealization

Stored separately after target maturity:

- prediction_id;
- resolution_time;
- realized terminal return;
- realized direction;
- direction correctness;
- magnitude error;
- applicable probability/distribution scores;
- baseline values/scores;
- resolution validity.

No outcome field is written back into PredictionSnapshot.

## 8. DecisionSnapshot

Every eligible decision candle gets one:

- decision_id / prediction_id / market_state_id;
- LONG / SHORT / NO_TRADE;
- playbook_id if applicable;
- conviction;
- actionability;
- blocker codes;
- proposed TradePlan ID if any;
- decision_time / available_at.

NO_TRADE is first-class data, not an omitted row.

## 9. TradePlan

A proposed paper trade stores:

- side LONG/SHORT;
- playbook/version;
- trigger time;
- readiness time;
- reference paper instrument;
- entry order rule/expiry;
- structural invalidation/stop;
- objective/exit rule;
- maximum hold <=4h;
- planned reward/risk;
- cost/funding assumptions;
- virtual equity;
- planned risk amount;
- max notional;
- quantity if/when determinable;
- conviction;
- supporting/opposing reasons;
- data-quality and reference-paper validity.

Plan != order != fill != position != closed trade.

## 10. Reference paper ledger

Reference instrument: BTCUSDT USD-M traded-price series for both LONG and SHORT.

Signed price P&L:

- LONG gains when exit > entry;
- SHORT gains when exit < entry.

Ledger includes:

- entry/exit fees;
- adverse execution friction;
- settlement funding when applicable;
- position quantity/notional;
- realized/unrealized P&L;
- equity;
- drawdown;
- occupancy.

Research defaults:

- initial equity 10,000 quote units;
- planned risk 0.25% equity/position;
- max gross notional 1× equity;
- one open position;
- no pyramiding/hedging/martingale/adaptive sizing;
- daily new-entry stop after 1% equity loss;
- run new-entry stop after 5% peak-to-trough drawdown;
- primary 24bp round-trip fee/friction assumption + funding;
- later frozen stress: 48bp + funding;
- later frozen delay stress: +5m.

This is a paper reference model; no margin/liquidation or live-account claim is made.

## 11. Execution events

Checkpoint-1 synthetic simulator must support:

- explicit readiness time;
- deterministic operational delay;
- next eligible 1m open fill;
- directional adverse friction;
- missing-minute failure;
- gap-through stop/target;
- same-minute stop/target collision resolved conservatively;
- maximum-hold expiry;
- unresolved end state;
- funding event accounting;
- identical semantics for historical replay and live paper adapters.

## 12. Replay

Historical replay is an event-stream simulation.

Controls:

- start;
- pause;
- single step;
- speed multiplier.

Speed affects UI wall time only, never event order or outputs.

The API must support a causal cursor view and a completed-run review view as distinct modes.

## 13. Candle annotations

Prediction glyph above each eligible 15m decision candle.

During causal replay it exposes only issued information. Realized score appears only after target
maturity.

Decision glyph below each eligible decision candle, including NO_TRADE and blockers. If a trade is
planned/filled, entry/exit markers use their actual simulated timestamps.

## 14. Post-analysis isolation

HotWindow/PostAnalysisReport records are not inputs to Signal/State/Prediction/Decision modules.

The post-analysis module may run only after replay completion.

No retrospective event finding may mutate an existing run or configuration.

## 15. Checkpoint-1 acceptance

Synthetic vertical slice passes only if deterministic tests prove:

- completed-bar availability;
- future-data rejection;
- immutable issued prediction;
- separate realization;
- LONG/SHORT signed P&L;
- fee/friction sign correctness;
- funding accounting;
- one-position occupancy;
- risk vetoes;
- conservative gap/collision handling;
- higher-timeframe availability;
- pivot/turn confirmation timestamps where fixtures use them;
- replay speed invariance;
- identical core outputs under historical and live-style synthetic adapters;
- prediction/decision glyph semantics;
- NO_TRADE persistence.

No real historical performance data is required or authorized.
