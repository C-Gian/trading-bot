# Predictive source roadmap V1

Canonical. Owner-authorized prediction-first objective; see
[ADR-0026](../../decisions/ADR-0026-PREDICTION-FIRST-RESEARCH-OBJECTIVE.md).

This document stages which information families the BTCUSDT predictor may eventually
study, and the conditions each must satisfy before it enters. It authorizes nothing by
itself: it is a map, not a schedule, and no family is admitted by appearing here.

Scoring rules live in
[`PREDICTIVE_EVALUATION_CONTRACT_V1.md`](PREDICTIVE_EVALUATION_CONTRACT_V1.md).

## Admission rule

Every family enters through **one preregistered incremental-information experiment** that
asks a single question: does this family add predictive information beyond the already
admitted set, on the frozen target and the frozen metric set?

Each such experiment must, before execution, declare:

1. the exact point-in-time availability rule for every series — publication timestamp,
   vintage/revision semantics, and the lag actually applied at the decision timestamp;
2. a matched control fitted on the already-admitted feature set over the identical
   eligible universe, so the comparison isolates the new information;
3. its search-budget consumption and multiplicity-family membership;
4. its primary metric and minimum important effect expressed in that metric.

A family whose point-in-time availability cannot be defended is blocked before execution,
not weakened until it passes. Data that is only available in revised or current-vintage
form is inadmissible where a point-in-time vintage is required.

Do not ingest all families at once. Narrative plausibility alone is never evidence: a
family that "obviously should" predict BTC must still beat its matched control.

## Stage 0 — foundation, before any family

Deterministic labels and evaluation, then simple chronological baselines. Label causality
and evaluation correctness are proven before any model complexity and before any external
family. This is the next work package, not a source family.

## Stage 1 — internal market structure

Available from canonical 1m BTCUSDT data already in the repository, under the existing
development cutoff.

| Family | Content |
| --- | --- |
| `INTERNAL_PRICE_RETURN_STRUCTURE` | multi-scale returns, trend/mean-reversion structure, realized path shape |
| `VOLUME_LIQUIDITY_VOLATILITY` | traded volume, realized volatility, dispersion, activity regimes |
| `TECHNICAL_AND_MICROSTRUCTURE` | technical patterns, order-flow-derived features already governed by the order-flow contract |

Point-in-time risk is lowest here; the real risk is look-ahead inside feature construction
and label overlap. Stage 1 is where the predictor must first demonstrate that it beats the
declared baselines at all.

## Stage 2 — derivatives and positioning

| Family | Content | Condition |
| --- | --- | --- |
| `DERIVATIVES_FUNDING_OPEN_INTEREST` | perpetual funding, open interest, basis | timestamped at exchange publication; settlement vs. observation semantics declared |
| `REGULATED_POSITIONING` | CFTC-style positioning reports | report date is never treated as availability; publication date governs |

Both families have prior repository experience under the superseded generation. Their
integrity tooling and manifests are reusable; their historical *results* belong to the
superseded generation and are not evidence for the predictive objective.

## Stage 3 — cross-asset and macro context

| Family | Content | Condition |
| --- | --- | --- |
| `CROSS_ASSET_CONTEXT` | equity, rates, dollar, gold, crypto majors | aligned to BTC decision timestamps with venue calendars and stale-quote handling declared |
| `MACROECONOMIC_VINTAGE` | macro series and financial-conditions indices | strict vintage/as-of control; revised current values are inadmissible |
| `CALENDAR_AND_CYCLE` | session, weekday, month, halving-epoch and other deterministic calendar structure | deterministic and fully causal; low point-in-time risk, high multiple-testing risk |

Calendar structure is cheap to test and therefore cheap to over-search. It consumes search
budget like any other family.

## Stage 4 — public information and attention

| Family | Content | Condition |
| --- | --- | --- |
| `PUBLIC_NEWS_AND_EVENTS` | timestamped public news and event records | event availability timestamp, not event occurrence timestamp; archive completeness declared |
| `POLICY_AND_GEOPOLITICAL_EVENTS` | policy, regulatory and geopolitical events as timestamped public information | no partisan interpretation, no editorial judgement; events are facts with timestamps |
| `PUBLIC_ATTENTION_AND_SENTIMENT` | search/pageview/attention and sentiment proxies | provenance and vintage must be valid; back-revised aggregates are inadmissible |

This stage carries the highest provenance risk. A source whose history is silently
rewritten by its publisher cannot support a point-in-time claim, whatever its apparent
predictive value.

## Stage 5 — on-chain

| Family | Content | Condition |
| --- | --- | --- |
| `ON_CHAIN` | chain-level activity, flows and supply metrics | block-confirmation and indexing availability semantics must be defensible; derived analytics with undocumented methodology changes are inadmissible |

## Permanent constraints

- No family may use information unavailable at the decision timestamp.
- No family may be admitted on narrative grounds.
- No family may access sealed post-cutoff BTCUSDT market data.
- Every family's entry consumes search budget and is recorded in search memory, whether it
  succeeds or fails.
- A rejected family stays rejected in the record; its negative result is preserved.
- Economic viability is never assessed at family-admission time. Admission is a predictive
  question only.
