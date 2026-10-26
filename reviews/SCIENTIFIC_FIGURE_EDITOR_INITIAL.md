# SCIENTIFIC_FIGURE_EDITOR Initial Review

## Review identity

- Role: `SCIENTIFIC_FIGURE_EDITOR`
- Review type: independent, read-only review of the v5 build
- Build root: `<build-root>/modelrigor`
- Scope: visual role coverage, visual monotony, data identity and traceability, real resource use, Word A4 page QA, and anti-overexpansion behavior
- Build edits: none

## Verdict

**FAIL — blocking defects remain.**

The packaged integrity command reports every group as `PASS`, and the plotting smoke test successfully calls the installed `plot_style.py` API and exports a valid 300 DPI PNG, SVG, and grayscale preview. Those checks establish API compatibility and basic export capability. They do not establish the visual, provenance, reviewer, or A4 guarantees claimed by the Skill. Adversarial fixtures show that each of those gates can currently pass invalid evidence.

## What passes

1. `policy.json:9-10` enumerates `SCIENTIFIC_FIGURE_EDITOR` and a useful base set of figure roles.
2. `references/visual_research_engine.md:3-11` correctly separates visual tasks from figure quotas, defines monotony semantically, requires stable visual semantics, and requires exact-document A4 QA.
3. `references/resource_adapter.md:3-11` correctly states read-only resource use, production-consumption provenance, demo quarantine, real API names, and non-inheritance of historical page/figure quotas.
4. `templates/page_budget.json:3-22` starts with hard page compliance `UNSET`; the depth and simple zero-figure regressions pass.
5. `scripts/visual_resource_smoke.py:25-32` calls the installed production plotting functions. The observed output was 1770×1168 pixels at approximately 300 DPI, with PNG, SVG, and grayscale artifacts.

These are partial passes only. They do not offset the blocking failures below.

## Findings

### P0-FIG-01 — Visual role coverage and data identity can be bypassed

**Locator:** `scripts/core.py:373-399`; `templates/figure_candidates.csv:1`; `schemas/csv_headers.json:5`

`audit_figures` does not validate the role against `policy.json`, required row fields, status enumerations, or the existence and identity of `data_source`. For a delivered figure, it compares `source_sha256` with the output artifact hash (`scripts/core.py:384-388`), so the field named as the source hash is actually used as an output hash. There is no separate input-data hash, plotting-code hash, Result ID binding, data-identity classification, or output hash.

A high-importance row with `status=NOT_APPLICABLE` passes without a reason. A physical mechanism row can therefore be waived by a bare status token. An `EQUIVALENT` row passes on any nonempty string without resolving the locator or verifying its hash (`scripts/core.py:389-390`).

Observed counterexamples against the current build:

- physical `MECHANISM`, `HIGH`, `NOT_APPLICABLE`, empty reason: `PASS`;
- role `NOT_A_ROLE`, `data_source=missing.csv`, output containing bytes that are not an image, with `source_sha256` set to the output hash: `PASS`.

This defeats `SKILL.md:18`, `policy.json:18-20`, and `references/resource_adapter.md:9`.

**Required fix:** replace the overloaded source field with explicit provenance fields or a structured manifest: validated role and status enums, data-identity class (`OBSERVED`, `DERIVED`, `SIMULATED`, `SYNTHETIC_TEST`, `DEMO_QUARANTINED`, etc.), source artifact plus hash and locator, Result IDs, plotting-code artifact plus hash, output artifact plus hash and media validation, units/statistical definition, and a required reason/evidence locator for `NOT_APPLICABLE` or `EQUIVALENT`. Validate every locator and hash.

### P0-FIG-02 — Word A4 QA accepts arbitrary bytes and is not an actual rendering gate

**Locator:** `scripts/core.py:453-472`; `scripts/run_semantic_regressions.py:114-121`; `templates/whole_paper_audit.json:3-11`; `SKILL.md:47`; `scripts/cqex.py:165-189`

`audit_page_qa` checks only path existence, hashes, a nonempty page list, `manual_status=PASS`, and any nonempty `checks` value. It does not validate that the paper is a DOCX ZIP, that page files are decodable images, that the source page size is A4, that all pages were rendered exactly once and in order, that resolution is sufficient, or that clipping/overflow/caption/font checks have defined results. It also ignores `page_qa.status`.

The positive regression deliberately writes `b"docx-fixture"` and `b"png-fixture"` and treats them as a passing Word/page pair. An independent counterexample using non-DOCX and non-PNG bytes, page number 99, and `checks=["x"]` also returned no issues.

The Skill says to use `audit-paper`, but that command does not exist. Running it returns an invalid-command error. Running `audit-paper-qa` on the untouched audit template crashes with `IsADirectoryError` because an empty paper path resolves to the template directory and is passed to `sha256`.

**Required fix:** implement an actual whole-paper command and a render-and-verify path. Verify DOCX package validity, render the exact DOCX to A4 pages, record renderer/version and page count, validate every page image and its dimensions/DPI, require contiguous unique page numbers, record structured checks for clipping, resolution, fonts, captions, legends, line weights, grayscale, and spacing, and bind all hashes to the exact DOCX. Invalid or empty paths must return a normal audit failure, never a traceback.

### P0-FIG-03 — The independent figure-editor role is nominal rather than enforced

**Locator:** `references/reviewer_protocol.md:3-11`; `templates/reviewer_report.json:3-10`; `scripts/core.py:402-427`

The reviewer protocol requires role-specific findings with locators, severity, attack, required evidence, and disposition. `audit_reviewers` checks only role presence, a distinct run ID, a truthy `independent` flag, any input-hash map, any artifact list, and `overall=PASS`. It does not verify input hashes against the artifacts, require findings, require `quality_conclusions`, require figure artifacts for the figure editor, or verify that the figure editor assessed role coverage, data identity, chart choice, semantics, diversity, and A4 pages.

Observed counterexample: five reports with distinct run IDs, `findings=[]`, `quality_conclusions={}`, and an unrelated artifact named `x` returned no issues.

**Required fix:** define and validate the reviewer finding schema; resolve every artifact and input hash; require the figure editor's artifact set to include the figure portfolio, visual semantics, source/result provenance, rendered figures, captions, and page-QA artifacts when applicable; require explicit dispositions for all P0/P1 findings; and bind `VISUAL_QUALITY` to the figure-editor run that supplied those findings.

### P1-FIG-04 — Monotony detection misses the common false-pass case

**Locator:** `references/visual_research_engine.md:7`; `scripts/core.py:373-399`; `scripts/run_semantic_regressions.py:106-112`

Monotony is raised only when at least three delivered rows have the same declared `preferred_chart_type` **and** a high-importance row is missing. Three or more repetitive figures pass whenever no high row is flagged missing. The audit reads the preferred type rather than the actual output encoding and does not compare research question, message, variables, panels, or claim contribution.

Observed counterexample: three delivered `line` rows covering `MECHANISM`, `MAIN_RESULT`, and `VALIDATION`, all pointing to the same byte artifact, returned `PASS`.

No monotony positive/negative regression is included in the visual regression group.

**Required fix:** detect duplicate outputs and repeated data/encoding/message independently of missing-role state; distinguish justified common encodings from repeated evidence; inspect actual figure metadata or a validated encoding manifest; and add regressions for duplicate artifacts, same data with relabeled roles, justified repeated encoding, and repeated encoding that crowds out distinct visual tasks.

### P1-FIG-05 — Real resource smoke is disconnected from production provenance and weakens its own checks

**Locator:** `scripts/visual_resource_smoke.py:19-41`; `templates/resource_consumption.csv:1`; `scripts/check_skill_integrity.py:95-100`; `scripts/core.py:568-600`; `scripts/cqex.py:116-129`

The smoke test genuinely exercises `plot_style.py`, which is useful. It hard-codes colors instead of loading `visual_semantics.json`, disables strict layout and strict design checks, and records a JSON shape that does not match the production `resource_consumption.csv` schema. The integrity check accepts only return code plus the literal stdout marker. It does not inspect the record or output media.

Production `resource_consumption.csv` is initialized but never audited, never required by `audit_research`, and not included in the Research Freeze manifest. A project can therefore reach Research Freeze without any real resource consumption record.

The read-only smoke also imported source bytecode without disabling cache writes. During this review, the external resource root acquired/updated `scripts/__pycache__/plot_style.cpython-312.pyc` at 2026-09-09 00:48:58, while `plot_style.py` itself was dated 2026-08-28. This is a concrete write side effect in the declared read-only resource tree.

**Required fix:** run the smoke with bytecode writes disabled; load the project visual semantics; enable or separately assert strict design/layout checks; validate the produced record and output formats/hashes/dimensions; add a Word resource/render smoke; audit every production consumption row; and include the consumption ledger plus consumed resource hashes in Research Freeze.

### P1-FIG-06 — Visual semantics and demo quarantine are declarative only

**Locator:** `references/visual_research_engine.md:9-11`; `references/resource_adapter.md:9`; `templates/visual_semantics.json:1-12`; `schemas/templates.schema.json:15`; `scripts/visual_resource_smoke.py:25-30`

The template provides observation, baseline, main model, reference, validation, training, and test entries, but omits the promised scenario and group semantics. The schema requires only that a `semantics` key exists; an empty object passes schema validation. No audit checks semantic keys, values, contrast, grayscale distinguishability, or consistency between a figure and the project registry. The smoke duplicates selected colors manually instead of consuming the registry.

There is no `data_identity` or quarantine/promotion state in the figure template and no machine check for `DEMO_QUARANTINED`. The fixture named `visual_real.csv` is a small constructed test series; its smoke record has no explicit `TEST_FIXTURE` identity or `claims_allowed=false` marker.

**Required fix:** define required/conditional semantic identities and validate their line/marker/color combinations; make plotting consume the registry; add figure-level semantic bindings; introduce explicit demo/synthetic/test identities and promotion evidence; and fail any paper-delivered figure that remains quarantined or lacks a real Result/input binding.

### P1-FIG-07 — Anti-overexpansion validation does not test visual or document inflation

**Locator:** `CONTENT_DEPTH_AND_LENGTH_DESIGN.md:3-7`; `scripts/core.py:349-370`; `scripts/core.py:397-398`; `scripts/check_skill_integrity.py:79-84`; `scripts/fixed_case_regression.py:54-69`

The written policy correctly rejects quotas and distinguishes insufficient from excessive content. The machine audit detects excess only when rows self-report `REDUNDANT` or `redundancy=YES`; it has no cross-artifact evidence-density or duplicate-content check. The anti-overexpansion regression group tests only that depth does not force benchmark/figure targets and that a theoretical case may have zero figures. It has no excessive-figure, duplicate-message, duplicate-output, redundant-table, repeated-caveat, or page-density case.

The fixed-case counterfactual sets `covered_visual_roles` equal to `applicable_visual_roles` in memory and then expects `VISUAL_QUALITY=PASS`; it does not require delivered figures, valid data, page rendering, or a figure-editor report. That regression is therefore tautological for visual improvement.

**Required fix:** add evidence-density and duplicate-output/message checks; connect content, figure, table, and page portfolios; require a reason for each retained low-value figure/table; and add adversarial regressions for both underdevelopment and overdevelopment. Replace the boolean counterfactual with concrete artifact fixtures that pass the same production audits used at freeze time.

## Mandatory remediation set

The build should not be accepted until all of the following are implemented:

1. Make figure role/status/data provenance machine-verifiable, with separate input, code, result, and output identities and hashes.
2. Resolve equivalent-expression and `NOT_APPLICABLE` claims to real evidence and require reasons.
3. Validate actual image media and actual visual encodings; add meaningful monotony and duplication tests.
4. Implement real DOCX-to-A4 rendering QA and the documented whole-paper audit command, with graceful failures.
5. Enforce substantive `SCIENTIFIC_FIGURE_EDITOR` findings and bind `VISUAL_QUALITY` to that independent run.
6. Audit production resource consumption, visual-semantics use, and demo quarantine; include them in Research Freeze.
7. Eliminate writes to the read-only resource root.
8. Add artifact-based positive and negative regressions for data identity, role coverage, monotony, A4 validity, reviewer substance, resource provenance, and overexpansion.

## Reverification criteria

Reverification is `PASS` only if all criteria below hold on the rebuilt package:

1. The normal integrity suite passes and explicitly lists new visual/provenance/A4/anti-expansion cases.
2. Each counterexample documented above fails with a precise finding ID and locator.
3. A valid delivered data figure passes only when input artifact/hash/locator, Result IDs, plotting-code hash, output hash, media validation, and semantic bindings all resolve.
4. Synthetic or demo data cannot be promoted to a paper-delivered empirical figure without explicit identity, allowed claim scope, and promotion evidence.
5. Repeated figures fail or receive an evidenced justification independent of whether another high-importance role is missing.
6. A real DOCX is rendered to A4; every page is validated, hash-bound, contiguous, and traceable. Non-DOCX/non-image bytes fail. Changing the DOCX invalidates the QA.
7. `audit-paper` exists and returns clean `PASS`/`FAIL`; an untouched template returns a structured failure rather than a traceback.
8. Empty or irrelevant reviewer reports fail. A passing figure-editor report contains role-specific findings, verified input hashes, actual artifacts read, quality conclusions, and dispositions.
9. A production project cannot Research Freeze with missing, stale, malformed, or semantically unreviewed resource-consumption records.
10. The resource smoke leaves the external legacy resource tree byte-for-byte unchanged.
11. Anti-overexpansion tests catch duplicate visual evidence and excessive low-value content while preserving valid zero-figure theoretical cases and justified repeated encodings.

