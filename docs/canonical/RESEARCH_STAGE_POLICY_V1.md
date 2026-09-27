# Research Stage Policy V1

Status: **CURRENT UNDER CONSTITUTION 4.0 / ADR-0052**

This policy defines evidence stages. The active task and generation-specific protocol may tighten it but may not weaken causal, exposure or real-capital protections.

## 1. Stage sequence

`SPECIFICATION -> ENGINEERING_REPLAY -> EXPOSED_DEVELOPMENT -> FROZEN_CANDIDATE -> PROTECTED_EVALUATION -> PREDECLARED_STRESS -> FUTURE_PAPER`

### SPECIFICATION
Freeze the causal/data/model/policy/risk/execution contract before economic outcomes governed by it are inspected.

### ENGINEERING_REPLAY
Validate implementation, deterministic parity, timestamp availability, fail-closed behavior and synthetic/path fixtures. Passing engineering checks is not evidence of edge.

### EXPOSED_DEVELOPMENT
Learning and bounded adaptation are allowed on declared exposed history. Every material revision is logged and consumes the generation's search budget. Positive results remain development evidence.

### FROZEN_CANDIDATE
Freeze code/data/model manifests, references, primary estimand, support requirements, protected interval and stress plan before protected outcomes are opened.

### PROTECTED_EVALUATION
Evaluate the frozen candidate once under the predeclared plan. If results are used to modify economic rules, the observed interval becomes exposed for the successor.

### PREDECLARED_STRESS
Run only stress scenarios frozen before seeing the protected result. Stress is sensitivity evidence, not a second optimization surface.

### FUTURE_PAPER
Collect genuinely prospective immutable forecasts/decisions under a frozen update rule. Future paper is stronger evidence than historical evaluation.

Real money is a separate Owner gate after all of the above.

## 2. Development rules

Allowed inside an authorized development programme:
- diagnosis of recurring failures;
- causal walk-forward fitting;
- predeclared references/ablations;
- one minimal falsifiable change per revision;
- deterministic bug fixes that restore an already frozen specification.

Forbidden:
- unbounded feature/model/timeframe/threshold tournaments;
- hiding failed variants;
- calling a result-independent bug anything that changes the economic specification after seeing P&L;
- recycling protected evaluation as independent evidence after adapting to it;
- optimizing DSR/PBO or other anti-overfitting diagnostics.

Every generation-specific budget lives in its protocol. For current G2 use `research/g2/G2_DEVELOPMENT_PROTOCOL_V1.md`.

## 3. Evidence interpretation

Evidence hierarchy:

`FUTURE_PAPER > PROTECTED_EVALUATION > PURGED/WALK-FORWARD/ROBUSTNESS/COST-STRESS > EXPOSED_DEVELOPMENT > NARRATIVE`

A lower class can motivate the next stage; it cannot be renamed into a higher class.

Prediction quality, trade-policy quality and execution quality are separate questions.

Overlapping financial observations require dependence-aware uncertainty; raw row count is not effective sample size.

## 4. Promotion

A policy may be frozen for protected evaluation only when:
- causal/integrity gates pass;
- contracts are stable and reproducible;
- search ledger is complete;
- exposed development shows enough net utility/support to justify spending protected evidence;
- cost/risk behavior is credible;
- a predeclared evaluation plan can resolve a meaningful claim.

A technically useful analytical product may remain unpromoted if economic policy evidence is insufficient.

## 5. Authority

- **Owner** — mission, product/risk/resource objective and real capital.
- **Astra** — material allocation, new successor generation, reopening closed lineages, budget expansion, major architecture changes and Champion-level decisions.
- **ChatGPT Research Director** — routine design, preregistration, architecture, tasking, implementation review and adjudication inside Astra's allocation.
- **Codex** — primary engineering executor.
- **Claude Code** — overflow engineering executor.

No executor may authorize scientific expansion or real capital.

## 6. Current G2 exception boundary

ADR-0052 authorizes G2 development but not current economic execution.

Changes outside the exact ordinary-revision authority listed in `G2_DEVELOPMENT_PROTOCOL_V1.md` return to Astra.

This file no longer carries historical programme narratives; those remain in ADRs and Git history.
