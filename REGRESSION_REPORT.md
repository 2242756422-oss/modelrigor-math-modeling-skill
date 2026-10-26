# v5.0 Regression Report

> Historical baseline report below. Current v5.1 validation uses 64 legacy semantic cases, 39 legacy adversarial cases, new research-integrity regressions, actual controlled numerical/figure/Word example and one isolated forward test. Package/fixture success is not an actual competition-paper quality certificate. See active SKILL and the dated optimization report in the task workspace for measured results and limitations.

## Executed evidence

- Semantic suite: 59 positive/negative cases passed. It covers page/depth decoupling, model-family closure, analytical truth, result/claim coverage, conditional Benchmark/Bound/Ablation, content sufficiency, visual roles and monotony, evidence promotion, resource provenance, dual Freeze, whole-paper consistency, numeric completeness, Word QA, staleness propagation and semantic handoff.
- First adversarial suite: `FALSE_POSITIVES=0/20`.
- Second adversarial suite: `NEW_BYPASSES=0/19`.
- Fixed legacy B case: scientific work remains `LARGELY_PASS`; domain development is required, content is `UNDERDEVELOPED`, visual and competitive quality are `FAIL`, and the action is `REOPEN_FOR_DEVELOPMENT`. The artifact-backed counterfactual reaches the intended PASS profile.
- Real resource smoke: the read-only `cumcm-step-review` plotting API produced PNG/SVG/grayscale QA outputs without changing the source resource tree.
- Real Word regression: all 18 render images were hash-bound to the exact DOCX and page review. The gate correctly detected the existing page-18 footer defect and rejected a document mutation.

## Independent-review disposition

Five role attacks were used during construction: DOMAIN_EXPERT, MATHEMATICAL_MODELING_REVIEWER, COMPETITION_JUDGE, SCIENTIFIC_FIGURE_EDITOR and ADVERSARIAL_REVIEWER. Their initial FAIL findings drove the executable changes below; copied conclusions do not count as independent PASS.

- Domain: P0 answers now require real evidence locators, a problem-specific ladder, family-specific closure and an independent domain report. Literature mappings enter named model objects and validity ranges.
- Mathematical modeling: required outputs, typed quantifiers, source truth, evaluator/version alignment, risk verification, conditional reports and transitive stale propagation are fail-closed.
- Competition: content obligations are derived from the scientific artifacts; whole-paper state, registries, shared model/evaluator hashes and distinct consistency evidence are checked.
- Scientific figures: chart/data identity enums, synthetic quarantine, duplicate/monotony checks, resource bindings, visual semantics, mechanism evidence and renderer/page-review bindings are enforced.
- Adversarial: 39 recorded false-PASS probes are blocked. Integrity refuses packages missing required reports or real-paper/resource arguments.

## Known legacy-paper finding

The pre-existing contest paper is a fixed regression input, not a v5 output. Its eighteenth rendered page displays footer number 8 rather than 18. The v5 Word gate returns failure for that artifact as intended. The paper was not modified.

## Reproduction

Run `scripts/check_skill_integrity.py` with the Skill root, read-only legacy resource root, real DOCX, render directory, renderer log and page-review JSON. A valid package prints all ten group PASS lines followed by `OVERALL INTEGRITY PASS`.


## v5.0.5 focused regression addendum

新增回归只覆盖本次小范围变更：扩展chart type可被真实Figure审计接受；物理模型能派生MECHANISM/MODEL_STRUCTURE/VALIDATION/PHYSICAL_INTERPRETATION等强视觉机会；简单理论题的visual miner不因扩展词库机械膨胀。原59项语义回归与两轮adversarial测试必须继续全部通过。


## v5.0.5 collaboration-mode preservation checks

Static integrity now verifies the collaboration protocol and both handoff templates exist, `KEY_DECISION_ONLY` cannot claim Freeze, `RETURN_AUDIT` explicitly preserves the original final gates, and the full semantic/adversarial suite remains unchanged.
