# ADVERSARIAL_REVIEWER — Initial Independent Review

## Verdict

**FAIL.** The current build has useful policy prose and a meaningful positive/negative test skeleton, but its executable gates remain fail-open. A fully fabricated question can pass both freezes. This blocks packaging as v5.0.

Role: `ADVERSARIAL_REVIEWER`  
Review mode: independent, read-only against `<build-root>/modelrigor`  
Reproduction artifact: `work/v5/reviews/adversarial_repro.py`  
Snapshot hashes:

- `SKILL.md`: `7aa2feb48f7b147d350904e4ea192ceb0ade11570e86756e756bd3d8fa4c0be3`
- `scripts/core.py`: `7040f5232d1a18296ac24daef5a72075491814363a1279507ff8b485109c05c6`
- `scripts/cqex.py`: `53aa5b2b231be9f663f403c0d8950d7e97c7cd87ba6896c66079562dc7b787c4`
- `scripts/check_skill_integrity.py`: `4df20739759cd9c5bab0d895b013f7b8d23b4557a45c57b25a91b4910c00391f`
- `schemas/csv_headers.json`: `fa7ae1628c719fb4e739aabdc83baf8f3d048bf14763c96d9a560fa17471c44b`
- `templates/conditional_gates.json`: `fd9320ab1415e97acb822f4d9a412f4df61618d87a9c829fa296bddf520980b5`

## Executed tests

### Published integrity command

The command was run with the real legacy B paper and the real read-only `cumcm-step-review` resource root. Result:

```text
PACKAGING PASS
SCHEMA FAIL
  conditional_gates.json missing hybrid_component_contribution_claimed
PY_COMPILE PASS
RULE_CONSISTENCY PASS
WORKFLOW_CONSISTENCY PASS
DOMAIN_PROFESSIONALISM_REGRESSION PASS
CONTENT_DEPTH_REGRESSION PASS
VISUAL_REGRESSION PASS
COMPETITIVE_QUALITY_REGRESSION PASS
ANTI_OVEREXPANSION_REGRESSION PASS
OVERALL INTEGRITY FAIL
```

The schema failure shows drift between `conditional_gates.json` and `templates.schema.json`. More seriously, all behavioral groups except schema reported PASS while the adversarial suite below demonstrated 20 fail-open cases. Therefore the current integrity groups do not yet support their names.

### Minimal false-positive suite

Command:

```text
python work/v5/reviews/adversarial_repro.py
```

Observed result: `FALSE_POSITIVES=20/20`.

The suite created only temporary artifacts and did not modify the build. It reproduced all of the following:

1. A nonexistent official page-rule source, forged hash and negative total page limit pass `audit_page_budget` as `VERIFIED`.
2. A legacy root-level `total_page_limit=19` survives while status is `UNSET`.
3. `route-depth` leaves `allocated_pages`, `question_page_targets` and `figures_required`, so legacy Depth coupling survives under alternate field names.
4. An empty Result Registry passes.
5. An unapproved result with no verification and `display_value="999 m"` for raw value `2` passes.
6. An empty Claim–Evidence Map passes.
7. A claim saying “globally optimal and robust” can cite an unapproved result and a nonexistent paper locator and still pass.
8. Every uncertainty category can have zero verification, and `dominant_risks` can name a nonexistent category, yet pass.
9. Content can be `APPROPRIATE` using nonexistent evidence and paper locators.
10. A physical mechanism requirement can be bypassed with bare `NOT_APPLICABLE` and no reason.
11. A nonexistent `equivalent_expression` passes the physical mechanism visual gate.
12. Five forged reviewer reports with distinct self-declared run IDs and nonexistent inputs pass.
13. Benchmark/Bound/Alternative/Ablation gates accept nonexistent evidence.
14. Arbitrary bytes pass as a DOCX, PNG and A4 page-level QA record.
15. A question with fake prompt locator, generic domain token, fake review input hashes, zero results, zero claims and zero validation passes the scientific audit.
16. The same question obtains `SCIENTIFIC FREEZE PASS`.
17. Fabricated content locators, peer sources, quality locators and five reviewer inputs pass the research audit.
18. The same question obtains `RESEARCH FREEZE PASS`.
19. After `REOPEN_FOR_DEVELOPMENT`, the question still passes `audit_research`, because the Research Manifest status and frozen bindings are not audited.
20. A handoff bound to a manifest whose status is `DRAFT` passes as `READY`.

### Initialization and command-surface probes

`init-project` currently creates only:

```text
page_budget.json
project_state.json
result_registry.json
visual_semantics.json
```

Although templates now exist for `whole_problem_map`, `numbering_registry`, `symbol_registry`, `figure_portfolio` and `paper_numeric_map`, the initialization command does not create them. The command advertised in `SKILL.md` as `audit-paper` does not exist; only `audit-paper-qa` exists, and that command checks hashes/self-reported page records rather than whole-paper scientific, numerical, assumption, visual and content consistency.

## P0 findings

### P0-1 — Scientific and Research Freeze are self-attestation gates

`audit_scientific` checks nonempty structure but does not connect required outputs to approved results/claims, does not validate the task locator, accepts zero results and claims, and accepts uncertainty without evidence. `audit_research` then accepts unresolved competitive evidence locators and forged reviewers. The manifests faithfully hash invalid registries, which only freezes the false positive.

Required fix:

- Derive required result/claim obligations from the Question Contract and require every applicable required output to resolve to approved Result Registry entries and Claim–Evidence rows.
- Validate prompt, paper, development, quality and evidence locators against actual artifacts and hashes.
- Require every approved scientific result to have verification appropriate to its source type; require explicit `NO_NUMERIC_RESULT_REQUIRED` only when the contract supports it.
- Treat reviewer provenance as an externally supplied, hash-verified artifact set, not Boolean self-report.
- Make both freeze commands refuse all unresolved/PENDING/forged obligations.

Retest standard: the end-to-end fake question in `adversarial_repro.py` must fail before manifest creation, while a real closed direct-calculation or analytical case can still pass without an optimization objective or forced benchmark/figure.

### P0-2 — Official page compliance can be fabricated

For `VERIFIED`, a missing source is not rejected; locator and excerpt are not checked; limit type/range is not checked; every counting component may remain `UNKNOWN`. Root-level legacy limits are not rejected under `UNSET`.

Required fix:

- Require an existing official-current-year artifact, matching hash, resolvable locator and matching excerpt.
- Require a positive integral total limit and explicit counting decisions for all required sections, using a separately documented ambiguity state only where the official text is truly silent.
- Recursively reject legacy page target/limit aliases while status is `UNSET`.

Retest standard: both page probes above must fail; the untouched page template must remain `UNSET` and pass.

### P0-3 — Handoff accepts an unfrozen or stale source

`check_handoff.py` checks only manifest hash and version. It does not require `SCIENTIFIC_FROZEN`, validate the source question, resolve handed-off objects/symbols/assumptions/evaluator, or compare current upstream hashes. A `DRAFT` manifest passes.

Required fix:

- Require a current `SCIENTIFIC_FROZEN` manifest with valid artifact bindings.
- Resolve every handed-off object, symbol/unit, assumption and evaluator reference to the source snapshot.
- Validate `from_question`, target dependency edge and upstream version.
- Integrate scientific-change propagation with freeze/reopen/project-state transitions; do not rely on a manually separate stale command.

Retest standard: the DRAFT-manifest probe must fail; modifying any upstream scientific artifact or version must make the handoff and every transitive downstream dependency `STALE`.

### P0-4 — Whole-paper audit and Word page QA are not real gates

The promised `audit-paper` command is absent. `audit_page_qa` accepts arbitrary bytes based on suffix and self-reported checks; it verifies neither DOCX structure, image format/dimensions, A4 rendering, page coverage/order nor the `page_qa.status`. It also does not check paper numbers against Result Registry.

Required fix:

- Implement `audit-paper` over current question manifests, evaluator/model consistency, assumption conflicts, paper numeric map, claim map, figure/table portfolio, content status, reviewer issues and page-rule compliance.
- Validate DOCX as an actual Office ZIP, render it with the supported document toolchain, verify A4 page dimensions and contiguous complete page coverage, and bind every render to the exact document hash.
- Require all manuscript values in scope to resolve through `paper_numeric_map` to approved Result Registry values with format/tolerance rules.

Retest standard: arbitrary bytes must fail; a real rendered DOCX passes; changing one document byte or one rendered page makes QA stale; `audit-paper` must be an executable command.

### P0-5 — Whole Problem Initialization is incomplete

The global registry templates exist but `init-project` omits them. This prevents the promised authoritative numbering, symbol, figure, numeric and dependency state from being established by the supported workflow.

Required fix:

- Make `init-project` idempotently create all required global artifacts, populate project identity, and audit their schemas.
- Add an initialization audit that checks question dependency nodes/edges, cross-question reusable model/evaluator candidates, preliminary research/evidence/writing roles, and leaves page status `UNSET` unless a verified official rule is present.

Retest standard: a fresh project contains every promised global registry, no question page targets, and passes an explicit initialization audit.

## P1 findings

### P1-1 — Result and Claim traceability is incomplete

Result display values are not checked against raw values/formatting, unapproved rows are accepted at Freeze, an analytical proof can contain only a locator token, and claims can point to nonexistent paper locations or unapproved results. Empty registries silently pass.

Fix: validate display transformation, source-specific proof/value locators, approval, verification, required-output coverage, claim strength triggers, and paper location/hash. “optimal/robust/stable/significant/superior” should derive conditional evidence obligations.

### P1-2 — Risk-driven Verification Pyramid is not enforced

`dominant_risks` is free text unrelated to categories, verification arrays are ignored, and no risk-to-test-to-result linkage exists.

Fix: use category IDs, severity/likelihood or explicit prioritization, verification IDs with current artifact hashes and outcomes, and coverage of every dominant risk. Keep `NOT_APPLICABLE` reasoned so a theoretical case is not forced into irrelevant experiments.

### P1-3 — Content sufficiency can be manufactured

One self-reported high-value row with fake references yields `APPROPRIATE`; required units are not derived from contract/domain/claim/peer-gap obligations. Evidence Promotion and Table Portfolio are required only to exist and may be empty.

Fix: derive content obligations, resolve locators/hashes, audit promotion decisions against a real saved-artifact inventory, and validate table evidence. Preserve independent `UNDERDEVELOPED` and `OVERDEVELOPED` directions.

### P1-4 — Visual role coverage is fail-open

Physical mechanism can be marked `NOT_APPLICABLE` without reason, `EQUIVALENT` is not resolved, candidate completeness is self-declared, and no optimization/data-specific role rules exist. The current check can also miss visual monotony when no missing candidate was registered. Data source and rendered output need separate hashes and the current build had schema/code drift during this review.

Fix: derive candidate roles from domain/model/claim/uncertainty obligations; validate reasoned non-applicability and equivalent locators; separately bind data, generation code, output, caption, paper location and page QA. Add optimization and data/ML regressions while preserving valid zero-figure theory.

### P1-5 — Conditional Benchmark/Bound/Ablation gates rely on self-report

Only explicit booleans currently trigger Benchmark/Ablation. Evidence strings are not resolved, no claim scan derives optimality/superiority/robustness/component obligations, and tolerance/fairness fields are self-asserted without provenance. The current template/schema are inconsistent.

Fix: derive triggers from contract, model type, solver class and Claim–Evidence Map; require hash-bound reports and fair-run provenance. Validate metric direction and nonnegative evidence-based tolerance. Maintain `PRACTICAL_TIE` below tolerance and allow simple analytical cases to skip all gates with a reason.

### P1-6 — Fixed B and anti-overfit regressions are too weak

The real B paper can be hash-bound when `--real-paper` is supplied, which is good. However the classification is read from manually frozen feature Booleans rather than recomputed from evidence; the counterfactual merely flips those Booleans. The real-paper argument is optional in the integrity suite. Anti-overexpansion covers direct calculation/theory and a physical visual omission, but lacks full optimization and data/ML cases.

Fix: require the real B artifact for the fixed-case group, bind manual feature judgments to locators/extractions, and make the counterfactual add actual reviewable artifacts. Add optimization and data/ML positive and negative fixtures.

### P1-7 — Freeze/REOPEN/STALE state machines are disconnected

`reopen-development` edits only Research Manifest status. `audit_research` ignores that status and ignores the Research Manifest's frozen artifact bindings. `mark_downstream_stale.py` is not integrated into freeze/reopen changes and project state is not synchronized.

Fix: define transition preconditions/postconditions in one implementation, validate current manifest state and bindings, and atomically propagate scientific changes through dependency/handoff state. Presentation-only changes should stale Word/page QA without invalidating scientific results.

## P2 findings

1. `__pycache__` files are already present inside the build and must be excluded from the final ZIP.
2. Packaging checks only a small required-file subset and do not verify that the ZIP has exactly one first-level `cumcm-question-expert/` directory or that every runtime file is represented in a manifest.
3. Model variables/parameters require a `unit` key but allow an empty unit without an explicit dimensionless marker; evaluator artifacts are hash-checked but not interface-smoke-tested per model contract.
4. Domain answers can all cite the same generic token. The independent domain report's declared `input_hashes` and `artifacts_read` are not checked against actual files, so the new 14-answer schema does not ensure proposition-level grounding.
5. Migration guidance is directionally safe and preserves old projects, but there is no executable dry migration validator that reports legacy page coupling, manifest status, retained hashes and recomputation triggers without editing the project.

## What is already sound enough to KEEP

- The root skill identity/version and the explicit separation of Scientific Freeze, Research Freeze, content sufficiency and hard page compliance.
- The initial `page_budget` template is `UNSET` and has no question page targets.
- Direct calculation may omit an objective with an explanation.
- Analytical result sources are modeled separately from experiments.
- Benchmark summary returns `PRACTICAL_TIE` at or below tolerance and refuses ranking when declared fairness differs.
- Simple theory may use zero figures; Benchmark/Ablation are conceptually conditional rather than Depth quotas.
- The fixed B case is keyed by content hash rather than filename, and the expected competitive conclusion is `REOPEN_FOR_DEVELOPMENT`.
- `cumcm-step-review` is treated as a read-only resource root by the smoke test and policy prose.

## Mandatory revalidation criteria

The adversarial role can return PASS only when all of the following hold on one stable build snapshot:

1. The published integrity command, with the real B paper and real resource root, produces every requested group PASS and `OVERALL INTEGRITY PASS`.
2. `adversarial_repro.py` reports zero false positives, or each formerly accepted fixture is explicitly rejected with the intended reason.
3. A fresh Whole Problem Initialization produces and audits all promised registries with page budget `UNSET`.
4. A valid minimal analytical/direct case still passes without forced objective, Benchmark, Ablation or figures.
5. Physical, optimization and data/ML fixtures each demonstrate both a meaningful PASS and at least one domain-specific FAIL.
6. A real evidence-complete question passes both freezes; changing evaluator, result, evidence, review input, research artifact or upstream manifest produces the correct stale/fail behavior.
7. `audit-paper` runs against an actual rendered DOCX and fails on a changed number, missing registry link, missing page, non-A4 render, stale figure/table or unresolved reviewer issue.
8. The final ZIP contains one top-level directory, no caches/runtime outputs, all required reports, and passes integrity after extraction without modifying the installed v4.1 skill or `cumcm-step-review`.

Until these criteria pass, the adversarial conclusion remains **FAIL / REOPEN_IMPLEMENTATION**.
