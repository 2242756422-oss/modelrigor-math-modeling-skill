# QUESTION DECISION PACKET

- mode: `KEY_DECISION_ONLY`
- question_id: `<qN>`
- decision_status: `DRAFT`
- scientific_freeze: `NOT_ATTEMPTED`
- research_freeze: `NOT_ATTEMPTED`

## 1. Task Contract

- exact question request:
- required inputs and sources:
- required outputs/deliverables:
- official templates/files to fill:
- hard constraints:
- evaluator/metric:
- precision/rounding rules:
- upstream dependencies:
- downstream dependencies:

## 2. Domain Professional Decision

- domain objects:
- professional standard model chain:
- mechanisms that must be represented:
- mechanisms omitted and why:
- applicability boundary:
- failure conditions:
- decision-critical literature/support and locators:

## 3. Main Model / Formulation

- selected formulation:
- model type:
- variables and units:
- parameters, units, and provenance:
- governing equations / objective / constraints:
- initial conditions:
- boundary conditions:
- observation/evaluation relation:
- identifiability / well-posedness:
- selected route rationale:
- rejected material alternatives and reason:
- core structure that the executor must not silently change:

## 4. Execution Specification

- recommended numerical/statistical/optimization strategy:
- discretization / representation:
- feasibility rules:
- convergence / termination rules:
- initialization / seed policy if relevant:
- required intermediate quantities:
- required final quantities:
- official workbook/table mapping:

## 5. Verification Design

### Required

- highest-risk failure modes:
- minimum independent checks:
- numerical/statistical verification:
- constraint/feasibility verification:
- result/workbook consistency checks:

### Conditional

- Benchmark trigger and decision:
- Bound/Gap trigger and decision:
- Ablation trigger and decision:
- Alternative Formulation trigger and decision:
- sensitivity / robustness / uncertainty obligations:

## 6. Claims and Boundaries

- claims the final paper should support:
- claims that are prohibited without additional evidence:
- interpretation obligations:

## 7. Visual Research Questions

List distinct reader-facing questions that deserve visual evidence. Do not prescribe a figure count.

1.
2.
3.

For each adopted visual task, state the evidence it should expose and why prose/table alone would be weaker.

## 8. Paper Development Obligations

- professional mechanism that must be explained:
- derivations that must appear:
- results that require interpretation:
- model evaluation/limitations that must appear:
- literature-to-model links that must appear:

## 9. Cross-Question Invariants / Handoff

- inherited items that must remain unchanged:
- values/objects to hand to the next question:
- definitions and units that must remain stable:

## 10. MODEL_DEVIATION_REQUEST Triggers

The external executor must stop and request a model decision if any of the following occurs:

- dimensional/physical inconsistency in the approved formulation;
- non-identifiability or non-uniqueness that changes the answer;
- infeasible or contradictory constraints;
- required data/parameter is absent and cannot be justified;
- a materially different model/evaluator is needed;
- core results depend on an assumption outside the approved boundary.

## 11. Execution Acceptance Checklist

The returned package can be considered for final audit only if it contains traceable code/results/verification/figures/tables as applicable and a paper draft consistent with this packet.

## FINAL DECISION

`READY_FOR_EXTERNAL_EXECUTION | NEEDS_USER_INPUT | BLOCKED_BY_MODEL_AMBIGUITY`

**STOP after this packet in KEY_DECISION_ONLY mode. Do not implement the full solution and do not start the next question.**
