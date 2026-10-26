# EXECUTION RETURN

- question_id: `<qN>`
- decision_packet: `<path/hash if available>`
- executor_status: `COMPLETE | PARTIAL | MODEL_DEVIATION_REQUEST`

## 1. Decision Compliance

Map each decision-critical item to the implementation/result artifact that satisfies it. State any deviation explicitly.

## 2. Actual Execution

- code actually executed:
- environment/toolchain actually available:
- data actually used:
- main runs actually completed:
- runs designed but not executed:

## 3. Results

List the core result values, units, precision, and exact artifact locations.

## 4. Verification

List independent checks, convergence/holdout/feasibility/constraint checks, sensitivity/robustness/uncertainty work, and their artifact locations.

## 5. Figures and Tables

For every adopted figure/table, state its research question, source data, and output path. Mark rejected visual candidates and the redundancy/quality reason when relevant.

## 6. Paper Section

- draft path:
- claims supported:
- limitations/boundaries retained:

## 7. Deviations / Open Risks

State any scientific, numerical, data, toolchain, or interpretation issue that Codex must decide before freeze.

## RETURN DISPOSITION

`READY_FOR_RETURN_AUDIT | PARTIAL | MODEL_DEVIATION_REQUEST`
