#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
import json
import py_compile
import re
import subprocess
import sys
import tempfile
import os
from pathlib import Path


GROUPS = ["PACKAGING", "SCHEMA", "PY_COMPILE", "RULE_CONSISTENCY", "WORKFLOW_CONSISTENCY", "DOMAIN_PROFESSIONALISM_REGRESSION", "CONTENT_DEPTH_REGRESSION", "VISUAL_REGRESSION", "COMPETITIVE_QUALITY_REGRESSION", "ANTI_OVEREXPANSION_REGRESSION"]


def run(cmd, env=None):
    merged=dict(os.environ); merged["PYTHONDONTWRITEBYTECODE"]="1"
    if env: merged.update(env)
    return subprocess.run(cmd, text=True, capture_output=True, env=merged)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("skill_root", type=Path)
    p.add_argument("--scope",choices=("package","full"),default="full",help="Package integrity is not an actual paper scientific/visual assessment")
    p.add_argument("--legacy-resource-root", type=Path)
    p.add_argument("--real-paper", type=Path)
    p.add_argument("--real-render-dir", type=Path)
    p.add_argument("--renderer-artifact", type=Path)
    p.add_argument("--page-review", type=Path)
    a = p.parse_args()
    root = a.skill_root.resolve()
    if a.scope=="full" and not all((a.real_paper,a.real_render_dir,a.renderer_artifact,a.page_review)):
        p.error("full scope requires actual paper, renders, renderer manifest and substantive page review; use --scope package for package-only checks")
    if not a.legacy_resource_root: a.legacy_resource_root=root.parent/"cumcm-step-review"
    status = {g: True for g in GROUPS}; detail = {g: [] for g in GROUPS}

    # Packaging
    required = ["SKILL.md", "policy.json", "scripts/core.py", "scripts/cqex.py", "scripts/provenance.py", "scripts/record_run.py", "scripts/efficient.py", "scripts/final_visual_inventory.py", "scripts/contest_rules.py", "scripts/run_semantic_regressions.py", "scripts/real_word_qa_regression.py", "references/efficient_research_protocol.md", "references/domain_and_model_protocol.md", "references/scientific_visualization_cookbook.md", "references/data_quality_preprocessing_playbook.md", "references/key_decision_only_protocol.md", "templates/QUESTION_DECISION_PACKET.md", "templates/EXECUTION_RETURN.md", "templates/domain_model_map.json", "templates/domain_model_map_adaptive.json", "templates/uncertainty_budget_adaptive.json", "templates/research_review.json", "templates/visual_review.json", "templates/contest_rule_profile.json", "schemas/templates.schema.json", "tests/test_research_integrity.py", "tests/adversarial_repro.py", "tests/adversarial_repro_v2.py", "CHANGELOG.md", "REGRESSION_REPORT.md", "INSTALL_PROMPT.md", "VERIFY_PROMPT.md", "MIGRATION_GUIDE.md"]
    for rel in required:
        if not (root / rel).is_file(): status["PACKAGING"] = False; detail["PACKAGING"].append("missing " + rel)
    for rel in ('tests/test_targeted_enhancements.py','examples/conservative_exchange.py','examples/conservative_exchange_plot.py'):
        if not (root/rel).is_file(): status['PACKAGING']=False; detail['PACKAGING'].append('missing '+rel)
    for rel in ('tests/test_audit_hardening.py','schemas/execution_receipt.schema.json'):
        if not (root/rel).is_file(): status['PACKAGING']=False; detail['PACKAGING'].append('missing '+rel)
    if root.name not in ("modelrigor", "modelrigor-math-modeling-skill"): status["PACKAGING"] = False; detail["PACKAGING"].append("root directory name mismatch")
    debris=list(root.rglob("__pycache__"))+list(root.rglob("*.pyc"))+list(root.rglob('.pytest_cache'))
    if debris: detail["PACKAGING"].append("runtime caches ignored by integrity checks; exclude them and .git when distributing")
    skill = (root / "SKILL.md").read_text(encoding="utf-8") if (root / "SKILL.md").exists() else ""
    fm = re.match(r"^---\n(.*?)\n---", skill, re.S)
    if not fm or not re.search(r"^name:\s*modelrigor\s*$", fm.group(1), re.M): status["PACKAGING"] = False; detail["PACKAGING"].append("YAML name mismatch")

    # Schema and template validation.
    try:
        schemas = json.loads((root/"schemas/templates.schema.json").read_text())
        for name, spec in schemas.items():
            d = json.loads((root/"templates"/name).read_text())
            for key in spec.get("required", []):
                if key not in d: raise ValueError(f"{name} missing {key}")
            for parent, keys in spec.get("nested_required", {}).items():
                for key in keys:
                    if key not in d[parent]: raise ValueError(f"{name}.{parent} missing {key}")
        headers = json.loads((root/"schemas/csv_headers.json").read_text())
        receipt_schema = json.loads((root/'schemas/execution_receipt.schema.json').read_text())
        if receipt_schema.get('properties',{}).get('schema_version',{}).get('const') != '5.1.2': raise ValueError('receipt schema version mismatch')
        for name, expected in headers.items():
            with (root/"templates"/name).open(encoding="utf-8-sig",newline="") as f: actual=next(csv.reader(f))
            if actual != expected: raise ValueError(f"{name} header mismatch")
    except Exception as e: status["SCHEMA"] = False; detail["SCHEMA"].append(str(e))

    # Compile without writing into the Skill tree.
    try:
        with tempfile.TemporaryDirectory() as td:
            for i, src in enumerate(sorted((root/"scripts").glob("*.py"))):
                py_compile.compile(str(src), cfile=str(Path(td)/f"{i}.pyc"), doraise=True)
    except Exception as e: status["PY_COMPILE"] = False; detail["PY_COMPILE"].append(str(e))

    # Rule/source consistency.
    try:
        policy=json.loads((root/"policy.json").read_text())
        if policy.get("skill")!="modelrigor" or policy.get("version")!="5.1.2" or '# ModelRigor v'+policy['version'] not in skill: raise ValueError("policy/SKILL identity/version mismatch")
        for rel in re.findall(r"\]\(([^)]+)\)", skill):
            if not (root/rel).exists(): raise ValueError("broken SKILL link: "+rel)
        active="\n".join(x.read_text(encoding="utf-8") for x in [root/"SKILL.md", *sorted((root/"references").glob("*.md"))])
        forbidden=[r"L3\s*(?:->|→|=).*?(?:页|page)",r"L3\s*(?:->|→|=).*?(?:figure|图)",r"L3\s*(?:->|→|=).*?benchmark",r"正文\s*19\s*页",r"q1\s*=\s*3页",r"4\.5页",r"6\.5页"]
        for pat in forbidden:
            if re.search(pat,active,re.I): raise ValueError("active legacy coupling: "+pat)
        if "Scientific Freeze" not in skill or "Research Freeze" not in skill: raise ValueError("dual freeze missing")
        collab=(root/"references/key_decision_only_protocol.md").read_text(encoding="utf-8")
        decision=(root/"templates/QUESTION_DECISION_PACKET.md").read_text(encoding="utf-8")
        returned=(root/"templates/EXECUTION_RETURN.md").read_text(encoding="utf-8")
        for phrase in ("KEY_DECISION_ONLY","RETURN_AUDIT","MODEL_DEVIATION_REQUEST","READY_FOR_EXTERNAL_EXECUTION"):
            if phrase not in collab+decision+returned: raise ValueError("collaboration protocol missing "+phrase)
        if "do not" not in collab.lower() or "Scientific Freeze" not in collab or "图表质量不能" not in collab:
            raise ValueError("collaboration quality-preservation contract incomplete")
        if "collaboration_modes" not in policy or set(policy["collaboration_modes"]) != {"FULL_RESEARCH","KEY_DECISION_ONLY","RETURN_AUDIT"}:
            raise ValueError("collaboration modes missing or altered")
    except Exception as e: status["RULE_CONSISTENCY"] = False; detail["RULE_CONSISTENCY"].append(str(e))

    # Workflow is executable and the semantic suite contains positive and negative behavior.
    sem = run([sys.executable, str(root/"scripts/run_semantic_regressions.py")])
    if sem.returncode != 0:
        status["WORKFLOW_CONSISTENCY"] = False; detail["WORKFLOW_CONSISTENCY"].append(sem.stdout+sem.stderr)
    for script,marker in (("adversarial_repro.py","FALSE_POSITIVES=0/20"),("adversarial_repro_v2.py","NEW_BYPASSES=0/19")):
        attack=run([sys.executable,str(root/"tests"/script)])
        if attack.returncode or marker not in attack.stdout:
            status["WORKFLOW_CONSISTENCY"]=False; detail["WORKFLOW_CONSISTENCY"].append(f"{script} failed:\n"+attack.stdout+attack.stderr)
    new=run([sys.executable,str(root/"tests/test_research_integrity.py")])
    if new.returncode:
        status["WORKFLOW_CONSISTENCY"]=False; detail["WORKFLOW_CONSISTENCY"].append(new.stdout+new.stderr)
    else: detail["WORKFLOW_CONSISTENCY"].append("v5.1 adversarial/positive regressions executed; fixture success is not scientific/visual certification")
    targeted=run([sys.executable,str(root/'tests/test_targeted_enhancements.py')])
    if targeted.returncode:
        status['WORKFLOW_CONSISTENCY']=False; detail['WORKFLOW_CONSISTENCY'].append(targeted.stdout+targeted.stderr)
    hardening=run([sys.executable,str(root/'tests/test_audit_hardening.py')])
    if hardening.returncode:
        status['WORKFLOW_CONSISTENCY']=False; detail['WORKFLOW_CONSISTENCY'].append(hardening.stdout+hardening.stderr)
    checks={
      "DOMAIN_PROFESSIONALISM_REGRESSION":["complete_domain_map_passes_structure","domain_nonexistent_locator_fails","physical_model_missing_boundary_and_observation_fails","optimization_missing_feasible_domain_fails","data_ML_missing_leakage_control_fails","physical_case_without_mechanism_fails"],
      "CONTENT_DEPTH_REGRESSION":["single_low_content_row_is_underdeveloped","content_appropriate_detected","content_overdeveloped_detected","simple_theory_research_freeze_without_mechanical_expansion","research_manifest_detects_postfreeze_change"],
      "VISUAL_REGRESSION":["simple_theory_zero_figures_passes","physical_case_without_mechanism_fails","invalid_visual_role_and_source_fail","expanded_chart_type_forest_accepted","visual_miner_derives_model_validation_interpretation","visual_miner_simple_theory_no_mechanical_expansion","visual_miner_allows_multiple_distinct_result_views","visual_miner_complex_task_prefers_richer_nonredundant_portfolio","visual_monotony_detected","fake_docx_page_QA_fails","word_page_QA_stales_after_document_change"],
      "ANTI_OVEREXPANSION_REGRESSION":["simple_theory_research_freeze_without_mechanical_expansion","L3_no_page_figure_benchmark_and_preserves_evidence","simple_theory_zero_figures_passes"],
    }
    checks["WORKFLOW_CONSISTENCY"]=["whole_problem_initialization_complete","scientific_manifest_exact_set","whole_paper_audit_command_passes_valid_case","whole_paper_audit_detects_and_reopens_stale_research","scientific_version_change_propagates_downstream_STALE","draft_manifest_handoff_fails"]
    checks["COMPETITIVE_QUALITY_REGRESSION"]=["superiority_claim_derives_benchmark_gate","hybrid_contribution_derives_ablation_gate","optimality_claim_derives_bound_gap_gate","benchmark_aggregates_distinct_methods"]
    for group,names in checks.items():
        if sem.returncode != 0 or any(name not in sem.stdout for name in names): status[group]=False; detail[group].append("semantic cases absent or failed")

    fixture=root/"tests/fixtures/legacy_b_reviewed_features.json"
    cmd=[sys.executable,str(root/"scripts/fixed_case_regression.py"),str(fixture)]
    fixed=run(cmd); improved=run(cmd+["--counterfactual"])
    if fixed.returncode or improved.returncode or "REOPEN_FOR_DEVELOPMENT" not in fixed.stdout or '"COMPETITIVE_QUALITY": "PASS"' not in improved.stdout:
        status["COMPETITIVE_QUALITY_REGRESSION"]=False; detail["COMPETITIVE_QUALITY_REGRESSION"].append(fixed.stdout+fixed.stderr+improved.stdout+improved.stderr)
    else:
        detail["COMPETITIVE_QUALITY_REGRESSION"].append("Legacy feature/counterfactual logic only, not a real improved paper or visual-quality PASS")

    # Exercise the actual resource API; discover sibling when installed, accept explicit root for build validation.
    legacy=a.legacy_resource_root
    has_legacy = bool(legacy and legacy.is_dir())
    before={p: p.stat().st_mtime_ns for p in legacy.rglob("*") if p.is_file()} if has_legacy else {}
    with tempfile.TemporaryDirectory() as td:
        smoke_cmd = [sys.executable,str(root/"scripts/visual_resource_smoke.py"),"--out",td]
        if has_legacy:
            smoke_cmd.extend(["--resource-root",str(legacy)])
        vis=run(smoke_cmd)
    if vis.returncode or "VISUAL RESOURCE SMOKE PASS" not in vis.stdout:
        status["VISUAL_REGRESSION"]=False; detail["VISUAL_REGRESSION"].append("real resource call failed: "+vis.stdout+vis.stderr)
    after={p: p.stat().st_mtime_ns for p in legacy.rglob("*") if p.is_file()} if has_legacy else {}
    if before!=after:
        status["VISUAL_REGRESSION"]=False; detail["VISUAL_REGRESSION"].append("read-only legacy resource tree was modified")

    if a.scope=="full":
        print("ACTUAL_PAPER_SCIENTIFIC_COMPETITIVE_QUALITY NOT_CERTIFIED (full scope adds real render/binding checks, not substantive CUMCM acceptance)")
        qa=run([sys.executable,str(root/"scripts/real_word_qa_regression.py"),"--paper",str(a.real_paper),"--render-dir",str(a.real_render_dir),"--renderer-artifact",str(a.renderer_artifact),"--page-review",str(a.page_review)])
        if qa.returncode or "REAL WORD QA REGRESSION PASS" not in qa.stdout:
            status["VISUAL_REGRESSION"]=False; detail["VISUAL_REGRESSION"].append("real Word page QA regression failed: "+qa.stdout+qa.stderr)
    else:
        print("ACTUAL_PAPER_SCIENTIFIC_VISUAL_QUALITY NOT_ASSESSED (package scope)")

    for group in GROUPS:
        print(f"{group} " + ("PASS" if status[group] else "FAIL"))
        for x in detail[group]: print("  "+x.replace("\n","\n  "))
    overall=all(status.values())
    print("OVERALL "+a.scope.upper()+" INTEGRITY " + ("PASS" if overall else "FAIL"))
    return 0 if overall else 1

if __name__ == "__main__": raise SystemExit(main())
