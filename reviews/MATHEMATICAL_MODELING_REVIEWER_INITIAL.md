# MATHEMATICAL_MODELING_REVIEWER — Initial Independent Review

## Review identity

- Role: `MATHEMATICAL_MODELING_REVIEWER`
- Disposition: **FAIL**
- Scope: `<build-root>/modelrigor`
- Build snapshot reviewed:
  - `scripts/core.py`: `7040f5232d1a18296ac24daef5a72075491814363a1279507ff8b485109c05c6`
  - `scripts/cqex.py`: `53aa5b2b231be9f663f403c0d8950d7e97c7cd87ba6896c66079562dc7b787c4`
  - `scripts/run_semantic_regressions.py`: `c918881e88399d213ca5e520d768a5db49752c3b0699f016d4431441ccfd9086`
  - `SKILL.md`: `7aa2feb48f7b147d350904e4ea192ceb0ade11570e86756e756bd3d8fa4c0be3`
  - `policy.json`: `95cc37f00540b65fb78c4508256719e822fb8819f11b7a32ab970b10d9807f0b`

The initial review found reproducible false-positive Scientific Freeze and Handoff paths. No build file was modified.

## Blocking findings

### P0-1 — Required outputs could freeze with no results and no claims

At the reviewed snapshot, `scripts/core.py:278-303` accepted an empty Result Registry, `scripts/core.py:306-329` accepted an empty Claim Map, and `scripts/core.py:542-565` did not map `question_contract.required_outputs` to results or claims.

Reproduction:

1. Create an otherwise structurally valid question.
2. Set `required_outputs` to a nonempty value such as `numeric answer`.
3. Use `{"schema_version":"5.0","results":[]}` as `result_registry.json`.
4. Leave `claim_evidence_map.csv` with only its header.
5. Run `audit_scientific` and `freeze_scientific`.

Observed result:

```text
scientific_issues []
SCIENTIFIC FREEZE PASS
freeze_rc 0
frozen_result_ids []
```

Required fix: define a total coverage relation from every required output to an approved result or analytical claim. Empty results/claims must fail whenever the question requires an output.

Retest standard: an end-to-end Scientific Freeze negative test must reproduce the setup above and fail with an explicit uncovered-output diagnostic.

### P0-2 — Analytical result truth was self-referential

At `scripts/core.py:266-270`, the analytical branch assigned the observed value from the registered `raw_value`; it checked only that the locator text occurred in the proof artifact. At `scripts/core.py:278-303`, verification was required only when `approved` was true, and a verification file's content was not interpreted.

Reproduction:

1. Create a proof artifact containing `[THM] The unique result is x=2.`
2. Register `raw_value=999`, pointing at `[THM]`.
3. Attach an arbitrary file whose registry metadata says `status=PASS`.
4. Separately test the same result with `approved=false` and no verification.

Observed result:

```text
wrong_analytical_value_with_fake_PASS []
unapproved_without_verification []
```

Required fix: analytical values must resolve from structured source data or a verifier-produced structured observed value. Every frozen result must be approved, have a current verification binding, match the freeze version, and have a checked raw/display/tolerance relation.

Retest standard: proof value `2` versus registered value `999`, unapproved results, stale verification hashes, invalid verification payloads, wrong display values, and wrong scientific versions must all fail.

### P0-3 — Benchmark and Bound/Gap triggers were self-declared and bypassable

At `scripts/core.py:506-520`, the gate trusted the booleans `comparative_superiority_claimed` and `hybrid_component_contribution_claimed`; it neither derived triggers from Claim Map nor resolved the evidence. The benchmark summarizer at `scripts/core.py:430-450` treated an invalid direction as minimization and accepted a negative tolerance.

Reproduction:

1. Add a passing claim: `Method A is superior to B`.
2. Leave `comparative_superiority_claimed=false` and `benchmark.triggered=false`.
3. Separately set a triggered benchmark's evidence to a nonexistent locator.
4. Call the summarizer with `direction=sideways` and `tolerance=-1`.

Observed result:

```text
superiority_claim_issues []
skipped_benchmark_gate_issues []
unresolved_trigger_evidence_issues []
invalid_direction_negative_tolerance {'status': 'CLEAR_WINNER', 'winner': 'B', 'gap': 1.0, 'tolerance': -1.0}
```

Required fix: derive Benchmark and Bound/Gap triggers from typed claims and the candidate-method set; resolve a hash-bound structured report during freeze; validate direction, tolerance basis, finite values, distinct competitors, feasibility, repeated runs, seed distribution, and fairness fields.

Retest standard: superiority and optimality claims must fail without their respective reports; missing/stale evidence, invalid direction, negative tolerance, duplicate methods, and single lucky-seed comparisons must fail.

### P0-4 — Handoff accepted a DRAFT manifest and downstream STALE was advisory

At `scripts/check_handoff.py:11-19`, Handoff checked only the manifest file hash and version. It did not require `SCIENTIFIC_FROZEN` or recursively audit the manifest. `scripts/core.py:480-487` accepted `artifacts={}`. `scripts/cqex.py:76-102` did not automatically invoke downstream invalidation, and question audit/freeze did not read project-state STALE.

Reproduction:

1. Create a scientific manifest with `status=DRAFT`, `scientific_version=7`, and `artifacts={}`.
2. Hash it and create a `READY` handoff that points to that hash/version.
3. Run `scripts/check_handoff.py`.

Observed result:

```text
HANDOFF PASS
exit 0
```

Required fix: manifests must contain exactly the required artifact set; Handoff must require and recursively validate a current Scientific Freeze; a changed scientific version must propagate STALE transactionally, and STALE must block downstream freeze and handoff.

Retest standard: DRAFT, incomplete, stale, or forged manifests and a STALE source question must all fail Handoff. An upstream scientific change must mark every transitive dependent STALE.

### P1-1 — Contradictory quantifiers passed independently

At `scripts/core.py:119-129` and `scripts/core.py:203-231`, quantity-bearing fields were checked only for nonemptiness. There was no consistency check between the Question and Model Contract evaluators.

Reproduction:

1. Require `for all scenarios` in the Question Contract.
2. Use `there exists one scenario` in the Model Contract.
3. Give the two evaluators incompatible acceptance definitions.
4. Audit both contracts.

Observed result:

```text
question_issues []
contradictory_model_issues []
```

Required fix: use structured quantifiers and compare Question/Model inputs, outputs, unknowns, evaluator direction, quantifier domains, quantifier order, and aggregation semantics.

Retest standard: FOR_ALL versus EXISTS, ALL_PASS versus ANY_PASS, domain mismatch, and evaluator direction mismatch must fail the integrated scientific audit.

### P1-2 — Scientific versions were not idempotent or synchronized

At `scripts/cqex.py:91-99`, every freeze used `old scientific_version + 1`, regardless of whether the scientific snapshot changed. Result `scientific_version` was only checked for presence by `scripts/core.py:287`; upstream versions were copied from the old manifest.

Required fix: derive snapshot identity from scientific artifact hashes and claim digest. An unchanged freeze must be idempotent. A changed freeze must compute one target version and require all results, verification outputs, evaluators, and upstream bindings to agree with it.

Retest standard: two identical freezes keep the same version and manifest identity; a scientific artifact change advances exactly once and invalidates mismatched result/upstream versions.

### P1-3 — Research Freeze had no current-manifest audit

At `scripts/core.py:568-600`, research audit validated current working artifacts and the scientific manifest, but not the existing research manifest's status or frozen artifact hashes. A post-freeze research edit or `REOPEN_FOR_DEVELOPMENT` status could therefore coexist with a passing research audit.

Required fix: add a current Research Freeze audit that validates status, scientific-manifest hash, exact research artifact set, and all artifact hashes.

Retest standard: post-freeze changes and REOPEN status must fail any audit used to claim completion.

### P1-4 — Claim files and reviewer provenance lacked complete hash resolution

At `scripts/core.py:321-326`, `file:` claim evidence had no required hash. At `scripts/core.py:402-427`, reviewer `input_hashes` were only required to be nonempty; they were not compared with actual files. Quality evidence locators were similarly only checked for nonemptiness at `scripts/core.py:490-503`.

Required fix: use `path + locator + sha256` for every mutable evidence object; validate reviewer inputs and quality conclusions against actual reports and current hashes.

Retest standard: changing any claim evidence or reviewer input after review must make the relevant freeze stale.

## Test-suite assessment

The then-current 25 semantic tests passed. They did not include end-to-end tests for empty results/claims, wrong analytical values, unapproved results, contradictory quantifiers, derived Benchmark/Bound/Gap triggers, exact manifest sets, idempotent versions, DRAFT/stale Handoff, or downstream STALE propagation.

The complete integrity command returned `OVERALL INTEGRITY FAIL` in the review interpreter because the visual-resource smoke test could not import `matplotlib`. That environment finding was separate from the mathematical blocking findings above.

## Initial disposition

**FAIL.** Scientific Freeze and Handoff could certify materially incomplete or false mathematical results. All P0 items and the version/quantifier consistency items were mandatory before a final PASS review.
