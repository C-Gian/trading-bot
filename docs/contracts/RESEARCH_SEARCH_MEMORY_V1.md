# Research search memory V1

Version: `SEARCH_MEMORY_V1`. Structured records are authoritative; human views summarize them.
Admission validates declarations without loading market data, executing trials, or changing files.

## Durable records

- `research/memory/SEARCH_LEDGER.jsonl`: one immutable admission per experiment, in admission order.
  The six original WP-003 entries are explicitly `RETROSPECTIVE_IMPORT`; they do not claim that this
  memory existed before WP-003. Their actual preregistrations/results remain unchanged.
- `HYPOTHESIS_FAMILIES.json`: canonical root mechanisms, event anchors, aliases, ancestry, failures
  and legitimate revisit conditions. Child labels resolve to the root budget.
- `SEARCH_BUDGET.json`: explicit global/root-family limits, including reservations for WP-004.
- `OUTCOMES.jsonl`: append-only terminal conclusions, normalized text hashes and JSON-pointer facts
  from immutable result files. An admission may exist without an outcome before execution; a
  finalized result must have an outcome. Never rewrite an admission after observing results.
- `FAILURE_MEMORY.md` and `RESEARCH_MAP.md`: compact human projections; refresh from authoritative
  JSON after admissions/outcomes. They are not independent editable scientific state.

The five `contracts/search_*.schema.json` schemas reject undeclared object fields, malformed hashes,
missing evidence facts, non-BTC/spot directions, and out-of-scope fingerprint data boundaries.
Result/preregistration hashes normalize CRLF to LF, preserving identity across Windows and CI.

## Fingerprints and novelty

Each entry contains a claimed market mechanism, hypothesis ID/role, canonical family, lineage,
budget units, scientific reason, and a structured behavioral fingerprint. The fingerprint declares
signal/context clocks, feature families and transformations, entry event, regime/confirmation
gates, position policy, stop/exit families, holding horizon, numeric parameters, dataset and
execution/cost versions. Historical buy-and-hold alone has a null holding horizon and reference role.

Canonicalization sorts object keys and the two declared feature sets, preserves all other array
order, normalizes integral floats to integers, and rejects nonfinite numbers. All actual numeric
choices belong in `parameters`, not encoded into renamed transformation strings.

`behavior_hash` excludes evaluation environment (`dataset`, `cost_model`, `execution_model`) and
all narrative/identity metadata. Consequently a new experiment name, wording, lineage claim,
outcome or evaluation profile cannot turn identical behavior into a new strategy.
`structure_hash` additionally masks numeric values to detect parameter-only drift.
Environment identity still remains in each strictly validated fingerprint and preregistration.

Classification is deterministic and ordered:

1. Same behavior is `DUPLICATE` and always rejected, including renamed/relabeled behavior.
2. Same structure with numeric changes is `PARAMETER_VARIANT`.
3. Unknown root/anchor is `NEW_FAMILY`, but cannot be admitted without prospective canonical family
   registration and an explicit budget. The classifier cannot allocate capacity.
4. Declared removal of a parent's gate is `MEANINGFUL_ABLATION`.
5. Changed regime, confirmation, stop or exit family is `NEW_MECHANISM_WITHIN_FAMILY`.
6. Feature wording/transformation drift without changed decision gates is `NEAR_DUPLICATE`.

An admitted failed-family follow-up may declare `REVISIT_WITH_NEW_EVIDENCE` while retaining the
underlying structural classification in the admission decision. Parameter/near-duplicate proposals
require a nonblank scientific reason and remaining budget. WP-004 has zero numeric-search capacity.
A new meaningful 4h regime gate remains a descendant of the breakout root, not a fresh root budget.

Family identity follows known event anchors, exact behavior, explicit aliases and parent ancestry.
Contradictory roots, unknown parent IDs, cyclic ancestry, or attempting to book a descendant against
a newly named budget fail closed. The supplied human label has no authority to establish novelty.

## Failure evidence and limits of automation

A failed root requires `new_evidence_basis`: an existing same-family result ID/path/hash, one or more
exact JSON-pointer observations, a structural response, and a falsifiable prediction. At least one
observation must be a result metric. The facts are checked against the immutable result; free text
alone, invented numbers, metadata-only citations, or numerical drift are rejected. Already observed
WP-003 gross-positive/net-negative evidence may motivate a *new structural response*; this does not
make that evidence independent or new data. Such follow-ups are adaptive and must also appear in
the adaptive-decision accounting defined by Stage C.

After WP-004, repeating the original WP-003 gross-positive/net-negative observation does not create
a new entitlement to try the same gates or drift their thresholds. A later allocation must retain
both generations of negative evidence and identify a new diagnostic and distinct structural
prediction. Exact replays remain forbidden; the same original clue cannot replenish a budget.

These checks establish integrity of the declaration and evidence, not causal truth. They cannot
prove that a self-authored explanation is persuasive, infer all semantically equivalent arbitrary
programs, or detect a dishonest feature name whose implementation differs from the declaration.
New vocabulary, code-to-fingerprint correspondence, and scientific materiality require inspectable
code, source/config hash linkage, synthetic tests, and Research Director review. Do not market this
as a universal semantic duplicate detector. Similar findings do not become independent confirmations.

## Accounting and admission API

`load_memory(root=ROOT)` loads the four authoritative memory files.
`classify_proposal(proposal, memory)` returns classification, root family, matches and hashes.
`admit_proposal(proposal, memory, root=ROOT)` validates the complete ledger-schema proposal and
returns a decision without writing. It rejects duplicates, unsupported revisits and exhausted
global, family or WP-004 budgets. The caller then appends the preregistered admission in a scientific
commit **before** real data execution. Never call an experiment runner based on classification alone.
`validate_memory(root=ROOT)` checks schemas, hashes, ordered admission validity, source/result facts,
family ancestry, linked failures and budget consumption; it returns derived accounting.
`accounting(memory)` exposes reservations and completed outcomes separately.

An experiment is one material protocol, not one random seed or fold. `strategy_variants` counts
configured strategy behaviors including controls/reference; `trials` counts declared evaluation
profiles/seed realizations. `numeric_parameter_variants` counts numeric search proposals, excluding
the original preregistered delayed-timing negative control. Two WP-003 economic core hypotheses
(trend and breakout) coexist with four reference/control experiments. Thirty-two random seeds are
32 evaluations of one control, not 32 independent market mechanisms. The delayed trend is one
descendant/control of the same trend hypothesis. New WP-004 ablations share one core hypothesis.

Initial reservations permit at most nine total experiments/configurations and 53 evaluation trials:
the six existing configurations used 41 trials (`1+32+3+3+1+1`); WP-004 may add three structural
configurations with four profiles each. The breakout root holds its old experiment plus these three
descendants: four experiments/configurations and 15 trials total. Sealed queries remain zero.
Failed, cancelled or negative admissions do not release spent search capacity. Budget extensions
require an explicit immutable Research Director decision, with history-preserving validator checks.
Separate adaptive decision/result-dependent-fork and evidence-stage accounting is defined in
`ADAPTIVE_RESEARCH_GOVERNANCE_V1.md`; it never resets this search history.
