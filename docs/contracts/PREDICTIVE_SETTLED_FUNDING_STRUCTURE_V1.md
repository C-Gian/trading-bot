# Predictive settled funding structure V1

`PREDICTIVE_SETTLED_FUNDING_STRUCTURE_V1`

The point-in-time contract for the first Stage-2 information family of
`PREDICTIVE_RESEARCH_GENERATION_V1`. It governs how already-settled BTCUSDT USD-M perpetual
funding may enter a **prediction** of the frozen spot 24h terminal target.

This is a new contract. It does not replace, amend or reinterpret
[`PERPETUAL_FUNDING_CONTEXT_V1`](PERPETUAL_FUNDING_CONTEXT_V1.md), which remains the
historical contract of the superseded cost-expectancy generation and keeps its own results.

## 1. Source

| Item | Value |
| --- | --- |
| Manifest | `data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json` |
| Canonical artifact | `data/derived/BTCUSDT-USDM-settled-funding-v1.parquet` |
| Endpoint | `https://fapi.binance.com/fapi/v1/fundingRate` |
| Credentials | none; the acquisition is credential-free public market data |
| Fields read | `funding_time`, `funding_rate` — and nothing else |
| Development ceiling | `2024-12-31T23:59:59.999Z` |

The manifest, the artifact, the request index and the acquisition provenance are reused
unchanged. The artifact is loaded through the existing integrity tooling, which verifies the
manifest hash, the column set and the development cutoff, so this contract cannot silently
read a different file than the one the manifest admits.

**Never used:** predicted or unsettled funding, mark price, index price, premium, basis, open
interest, long/short position ratios, or any field absent from the canonical artifact.

## 2. Availability at a decision instant

At prediction decision timestamp `T`, a funding record is available **only** when

```
funding_time < T
```

holds exactly. A settlement stamped exactly `T` is **not** available: settlement and
observation are distinct events, and a rate stamped at the decision instant is not knowable
strictly before it.

There is no interpolation and no forward filling across a funding gap. A missing settlement
stays missing.

## 3. Feature window and validity

A funding feature vector at `T` reads exactly the **last nine** settlements with
`funding_time < T`, and nothing else.

The vector is available only when both hold:

1. those nine strictly-prior settlements all exist;
2. every consecutive gap **inside those nine records** is at most `8h + 60s`.

The natural cadence is eight hours; the sixty-second tolerance absorbs exchange stamping
jitter without ever bridging a missed settlement.

Otherwise the vector is unavailable and the timestamp is an explicit **counted abstention**,
never an imputed value. Unavailability is typed:

| Reason | Meaning |
| --- | --- |
| `INSUFFICIENT_PRIOR_SETTLEMENTS` | fewer than nine strictly-prior settlements exist |
| `SETTLEMENT_GAP_TOO_LARGE` | a consecutive gap inside the nine exceeds `8h + 60s` |
| `NON_FINITE_FUNDING_FEATURE` | a computed value is not finite |

The rules are ordered and mutually exclusive: the first that fires owns the instant.

## 4. Frozen feature set

`PREDICTIVE_SETTLED_FUNDING_FEATURES_V1` — exactly five features, in this order, derived only
from the nine valid strictly-prior settlements `r[0] … r[8]` where `r[8]` is the most recent:

| # | Name | Definition |
| --- | --- | --- |
| 1 | `LATEST_SETTLED_RATE` | `r[8]` |
| 2 | `MEAN_LAST_3_SETTLEMENTS` | mean of `r[6..8]` |
| 3 | `MEAN_LAST_9_SETTLEMENTS` | mean of `r[0..8]` |
| 4 | `DELTA_LATEST_PREVIOUS` | `r[8] - r[7]` |
| 5 | `STD_LAST_9_SETTLEMENTS` | population standard deviation of `r[0..8]` |

No other transform, clipping, sign flag, interaction, rolling window, threshold, momentum
term, calendar variable, spot-price feature or Stage-1 internal feature is authorized by this
contract.

The set deliberately does **not** inherit the Stage-1 169-bar contiguity rule. The Stage-1
substrate defect is therefore neither repaired nor carried forward by this family.

## 5. What this contract does not do

- It does not change the frozen prediction target, horizon, labels, folds, scorer,
  reliability bins or bootstrap parameters. Those remain
  [`PREDICTIVE_EVALUATION_CONTRACT_V1`](../canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md)
  Amendment A1 and `PREDICTIVE-BASELINES-V1`.
- It does not admit any other derivatives series. Open interest, basis and position ratios
  remain unadmitted.
- It does not make historical `PERPETUAL_FUNDING_CONTEXT_V1` results evidence for any
  predictive hypothesis. Only that generation's source-integrity tooling and canonical data
  are reused.
- It authorizes no sealed query, no Champion and no real money.
