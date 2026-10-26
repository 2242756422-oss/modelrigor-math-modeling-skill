#!/usr/bin/env python3
from __future__ import annotations

import sys; sys.dont_write_bytecode=True
import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from efficient import PROFILE, ACCEPTANCE_NAMES, is_efficient, scientific_names, affected_by_change, evidence_dependencies, domain_checks, SPECIALIST_CHECKS, ALIASES

from core import (QUALITY, RESEARCH_NAMES, SCIENTIFIC_NAMES, audit_manifest_bindings,
                  audit_page_budget, audit_page_qa, audit_paper, audit_research,
                  audit_scientific, claim_science_digest, load_json, resolve, sha256,
                  summarize_benchmark)

ROOT=Path(__file__).resolve().parents[1]; TEMPLATES=ROOT/"templates"


def write_json(path:Path,data:object)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def copy_once(src:Path,dst:Path)->None:
    if not dst.exists(): dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)


def init_project(path:Path,project_id:str)->None:
    path.mkdir(parents=True,exist_ok=True)
    names=("page_budget.json","project_state.json","result_registry.json","visual_semantics.json","whole_problem_map.json","numbering_registry.json","symbol_registry.json","figure_portfolio.csv","paper_numeric_map.csv","whole_paper_audit.json")
    for name in names: copy_once(TEMPLATES/name,path/name)
    state=load_json(path/"project_state.json")
    if not state.get("project_id"): state["project_id"]=project_id; write_json(path/"project_state.json",state)
    whole=load_json(path/"whole_problem_map.json")
    if not whole.get("problem_id"): whole["problem_id"]=project_id; write_json(path/"whole_problem_map.json",whole)
    print("WHOLE PROBLEM INITIALIZED (existing files preserved)")


def init_question(path:Path,qid:str,profile:str="LEGACY_FULL")->None:
    path.mkdir(parents=True,exist_ok=True)
    names=("question_contract.json","question_plan.json","domain_model_map.json","model_contract.json","assumption_ledger.csv","literature_to_model_map.csv","uncertainty_budget.json","result_registry.json","claim_evidence_map.csv","figure_candidates.csv","table_portfolio.csv","content_units.csv","evidence_promotion.csv","resource_consumption.csv","visual_semantics.json","scientific_manifest.json","research_manifest.json","quality_assessment.json","conditional_gates.json","competitive_development.json","handoff.json")
    if profile==PROFILE:
        names=("question_contract.json","question_plan.json","domain_model_map.json","model_contract.json","assumption_ledger.csv","uncertainty_budget.json")
    else: (path/"reviews").mkdir(exist_ok=True)
    for name in names:
        src=("domain_model_map_adaptive.json" if name=="domain_model_map.json" else "uncertainty_budget_adaptive.json" if name=="uncertainty_budget.json" else name) if profile==PROFILE else name
        copy_once(TEMPLATES/src,path/name)
    for name in ("question_contract.json","question_plan.json","domain_model_map.json","model_contract.json","uncertainty_budget.json","scientific_manifest.json","research_manifest.json"):
        p=path/name
        if not p.exists(): continue
        d=load_json(p)
        if not d.get("question_id"): d["question_id"]=qid; write_json(p,d)
    plan=load_json(path/"question_plan.json")
    if "workflow_profile" not in plan:
        plan["workflow_profile"]=profile; write_json(path/"question_plan.json",plan)
    print("QUESTION INITIALIZED (existing files preserved; profile="+plan["workflow_profile"]+")")


def prepare_stage(path:Path,stage:str)->None:
    if not is_efficient(path):
        print("LEGACY PROJECT: existing stage artifacts preserved"); return
    names={"solve":["result_registry.json","conditional_gates.json","claim_evidence_map.csv"],
           "develop":["figure_candidates.csv","table_portfolio.csv","visual_semantics.json","research_review.json"],
           "handoff":["handoff.json"]}[stage]
    if stage=="solve" and load_json(path/"domain_model_map.json").get("literature_grounding",{}).get("status")!="NOT_APPLICABLE":
        names.append("literature_to_model_map.csv")
    for name in names: copy_once(TEMPLATES/name,path/name)
    print("STAGE PREPARED",stage,len(names))


def activate_domain(path:Path,families:list[str])->None:
    if not is_efficient(path): raise ValueError("Explicitly migrate legacy layout before adaptive domain activation")
    normalized=[ALIASES.get(f,f) for f in families]
    if not normalized or any(f not in SPECIALIST_CHECKS for f in normalized):
        raise ValueError("Unknown discipline; choose "+",".join(SPECIALIST_CHECKS))
    target=path/"domain_model_map.json"; data=load_json(target)
    existing={r.get("id"):r for r in data.get("checks",[])}
    data["domain_family"]=normalized[0]; data["domain_families"]=normalized
    data["checks"]=[existing.get(name,{"id":name,"finding":"","evidence":[]}) for name in sorted(domain_checks(normalized))]
    write_json(target,data)
    print("PROFESSIONAL CHECKS ACTIVATED",len(data["checks"]),"(substantive review still required)")


def project_root(question_dir:Path)->Path|None:
    for p in (question_dir.parent,question_dir.parent.parent):
        if (p/"project_state.json").is_file(): return p
    return None


def mark_dependents_stale(root:Path,changed_qid:str,new_version:int)->None:
    sp=root/"project_state.json"; state=load_json(sp); changed=False
    state.setdefault("questions",{}).setdefault(changed_qid,{})["scientific_version"]=new_version
    state["questions"][changed_qid]["status"]="SCIENTIFIC_FROZEN"; changed=True
    frontier={changed_qid}
    while frontier:
        nxt=set()
        for dep in state.get("dependencies",[]):
            upstream=dep.get("from",dep.get("upstream")); downstream=dep.get("to",dep.get("downstream"))
            if upstream in frontier and downstream:
                rec=state["questions"].setdefault(downstream,{})
                if rec.get("status")!="STALE": rec["status"]="STALE"; rec["stale_reason"]=f"upstream {changed_qid} advanced to scientific v{new_version}"; nxt.add(downstream); changed=True
        frontier=nxt
    if changed: state["scientific_version"]=max(int(state.get("scientific_version",0)),new_version); write_json(sp,state)


def is_question_stale(path:Path)->bool:
    root=project_root(path)
    if not root:return False
    qid=load_json(path/"question_contract.json").get("question_id")
    return load_json(root/"project_state.json").get("questions",{}).get(qid,{}).get("status")=="STALE"


def current_upstream_versions(path:Path)->tuple[dict[str,int],list[str]]:
    root=project_root(path)
    if not root:return {},[]
    qid=load_json(path/"question_contract.json").get("question_id");state=load_json(root/"project_state.json");versions={};issues=[]
    for dep in state.get("dependencies",[]):
        upstream=dep.get("from",dep.get("upstream"));downstream=dep.get("to",dep.get("downstream"))
        if downstream!=qid:continue
        whole=root/"whole_problem_map.json"
        records=load_json(whole).get("questions",[]) if whole.exists() else []
        rel=next((r.get("path") for r in records if r.get("question_id")==upstream),None)
        manifest=resolve(root,rel or upstream)/"scientific_manifest.json"
        if not manifest.is_file():issues.append(f"upstream {upstream} scientific manifest missing");continue
        md=load_json(manifest)
        if md.get("status")!="SCIENTIFIC_FROZEN" or audit_manifest_bindings(manifest,scientific_names(manifest.parent)) or audit_scientific(manifest.parent,md.get("scientific_version")):issues.append(f"upstream {upstream} scientific snapshot invalid");continue
        versions[upstream]=md["scientific_version"]
    return versions,issues


def audit(path:Path,phase:str)->int:
    issues=audit_scientific(path) if phase=="scientific" else audit_research(path,False)
    if is_question_stale(path): issues.append("project_state marks this question STALE")
    if issues:
        print(f"{phase.upper()} AUDIT FAIL"); [print("-",x) for x in issues]; return 1
    print(f"{phase.upper()} AUDIT PASS")
    if phase=='scientific': print('SCOPE: structural/evidence checks and attributed review; not automatic proof of well-posedness or scientific truth')
    return 0


def freeze_scientific(path:Path)->int:
    target=path/"scientific_manifest.json"; old=load_json(target) if target.exists() else {}
    names=scientific_names(path)
    artifacts={name:sha256(path/name) for name in names if (path/name).is_file()}
    digest=claim_science_digest(path/"claim_evidence_map.csv") if (path/"claim_evidence_map.csv").exists() else ""
    upstream_versions,upstream_issues=current_upstream_versions(path)
    current_issues=audit_scientific(path,old.get("scientific_version")) if old.get("status")=="SCIENTIFIC_FROZEN" else []
    unchanged=(old.get("status")=="SCIENTIFIC_FROZEN" and old.get("artifacts")==artifacts and old.get("scientific_claim_digest")==digest and old.get("upstream_scientific_versions",{})==upstream_versions and not audit_manifest_bindings(target,names) and not current_issues and not upstream_issues)
    if unchanged: print("SCIENTIFIC FREEZE PASS (UNCHANGED SNAPSHOT)"); return 0
    version=int(old.get("scientific_version",0))+1
    issues=audit_scientific(path,version)+upstream_issues
    if is_question_stale(path): issues.append("question is STALE; reconcile upstream before freezing")
    if issues:
        [print("-",x) for x in issues]; print("SCIENTIFIC FREEZE FAIL"); return 1
    results=load_json(path/"result_registry.json").get("results",[])
    data={"schema_version":"5.0","question_id":load_json(path/"question_contract.json")["question_id"],"status":"SCIENTIFIC_FROZEN","scientific_version":version,"created_at":datetime.now(timezone.utc).isoformat(),"artifacts":artifacts,"scientific_claim_digest":digest,"result_ids":[r["result_id"] for r in results],"verification_ids":sorted({v.get("id",v.get("artifact","")) for r in results for v in r.get("verification",[])}),"upstream_scientific_versions":upstream_versions}
    if is_efficient(path): data["schema_version"]="5.1"
    write_json(target,data)
    if is_efficient(path):
        data["external_bindings"]={str(p):sha256(p) for p in evidence_dependencies(path,False)}
        write_json(target,data)
    root=project_root(path)
    if root: mark_dependents_stale(root,data["question_id"],version)
    rm=path/"research_manifest.json"
    if rm.exists(): rd=load_json(rm); rd["status"]="STALE"; rd["stale_reason"]="scientific snapshot changed"; write_json(rm,rd)
    print("SCIENTIFIC FREEZE PASS"); return 0


def freeze_research(path:Path)->int:
    issues=audit_research(path,False)
    if is_question_stale(path): issues.append("question is STALE; reconcile upstream before Research Freeze")
    if issues:
        [print("-",x) for x in issues]; print("RESEARCH FREEZE FAIL"); return 1
    sm=path/"scientific_manifest.json"; target=path/"research_manifest.json"; old=load_json(target) if target.exists() else {}
    efficient=is_efficient(path)
    artifacts={name:sha256(path/name) for name in (ACCEPTANCE_NAMES if efficient else RESEARCH_NAMES)}
    if not efficient:
        for p in sorted((path/"reviews").glob("*.json")): artifacts[str(p.relative_to(path))]=sha256(p)
    unchanged=(old.get("status")=="RESEARCH_FROZEN" and old.get("scientific_manifest_sha256")==sha256(sm) and old.get("artifacts")==artifacts)
    version=int(old.get("research_version",0))+(0 if unchanged else 1)
    quality={"dimensions":{k:{"status":"PASS"} for k in QUALITY}} if efficient else load_json(path/"quality_assessment.json")
    data={"schema_version":"5.0","question_id":load_json(sm)["question_id"],"status":"RESEARCH_FROZEN","research_version":version,"scientific_manifest_sha256":sha256(sm),"created_at":old.get("created_at") if unchanged else datetime.now(timezone.utc).isoformat(),"artifacts":artifacts,"content_sufficiency":"APPROPRIATE","quality":{k:quality["dimensions"][k]["status"] for k in QUALITY},"review_run_ids":[load_json(p)["run_id"] for p in sorted((path/"reviews").glob("*.json"))]}
    if efficient:
        data["schema_version"]="5.1"; data["review_run_ids"]=[]
        data["acceptance_reviewer"]=load_json(path/"research_review.json").get("reviewer")
    write_json(target,data)
    root=project_root(path)
    if root:
        state=load_json(root/"project_state.json"); qid=data["question_id"]; rec=state.setdefault("questions",{}).setdefault(qid,{}); rec.update({"status":"RESEARCH_FROZEN","scientific_version":load_json(sm)["scientific_version"],"research_version":version})
        if not unchanged: state["presentation_version"]=int(state.get("presentation_version",0))+1
        write_json(root/"project_state.json",state)
    print("RESEARCH FREEZE PASS"+(" (UNCHANGED SNAPSHOT)" if unchanged else "")); return 0


def reopen(path:Path)->int:
    rm=path/"research_manifest.json"
    if not rm.exists(): print("REOPEN FAIL - research manifest missing"); return 1
    d=load_json(rm); sm=path/"scientific_manifest.json"
    if d.get("status")!="RESEARCH_FROZEN" or not sm.is_file() or d.get("scientific_manifest_sha256")!=sha256(sm) or audit_manifest_bindings(sm,scientific_names(path)): print("REOPEN FAIL - no valid frozen scientific snapshot"); return 1
    d["status"]="REOPEN_FOR_DEVELOPMENT"; d["reopened_at"]=datetime.now(timezone.utc).isoformat(); d["preserved_scientific_manifest_sha256"]=sha256(sm); write_json(rm,d)
    root=project_root(path)
    if root:
        state=load_json(root/"project_state.json"); qid=d["question_id"]; state.setdefault("questions",{}).setdefault(qid,{})["status"]="REOPEN_FOR_DEVELOPMENT"; state["presentation_version"]=int(state.get("presentation_version",0))+1; write_json(root/"project_state.json",state)
    print("REOPENED FOR DEVELOPMENT; scientific snapshot preserved; paper QA is stale"); return 0


def benchmark(protocol_path:Path,runs_path:Path)->None:
    with runs_path.open(encoding="utf-8-sig",newline="") as f: runs=list(csv.DictReader(f))
    for r in runs: r["feasible"]=str(r.get("feasible","")).lower() in ("true","1","yes")
    print(json.dumps(summarize_benchmark(load_json(protocol_path),runs),ensure_ascii=False,indent=2))


def route_depth(path:Path,depth:str)->None:
    d=load_json(path) if path.exists() else {}; d["question_depth"]=depth
    strategies={"L1":{"solver_effort":"exact_or_direct_first","verification_effort":"substitution_boundary_and_dominant_risk","audit_effort":"one_core_review"},
                "L2":{"solver_effort":"structured_prototype_then_production","verification_effort":"numerical_accuracy_identification_and_dominant_risk","audit_effort":"core_plus_triggered_specialist"},
                "L3":{"solver_effort":"decomposition_resource_plan_then_production","verification_effort":"interface_propagation_and_critical_failure_attacks","audit_effort":"core_plus_triggered_specialist"}}
    d["depth_effects"]=strategies[depth]
    for key in ("page_target","target_pages","allocated_pages","question_page_targets","figure_target","figures_required","minimum_figures","table_target","tables_required","minimum_tables","formula_target","formulas_required","minimum_formulas","benchmark_required","auto_benchmark","ablation_required","auto_ablation"): d.pop(key,None)
    write_json(path,d); print("DEPTH ROUTED WITHOUT PAGE/FIGURE/BENCHMARK TRIGGERS")


def audit_whole(path:Path,apply_reopen:bool=False)->int:
    d=load_json(path); d["unresolved_issues"]=[]; d["status"]="PENDING"; write_json(path,d)
    issues=audit_paper(path); d=load_json(path); d["last_audit_at"]=datetime.now(timezone.utc).isoformat(); d["unresolved_issues"]=issues; d["status"]="PASS" if not issues else "FAIL"
    qdirs=[resolve(path.parent,x) for x in d.get("question_dirs",[])]; reopen_list=[]
    for qd in qdirs:
        qi=[x.split(": ",1)[-1] for x in issues if x.startswith(qd.name+": ")]
        if qi: reopen_list.append({"question":qd.name,"reasons":qi})
    d["reopen_questions"]=reopen_list; write_json(path,d)
    if apply_reopen:
        for rec in reopen_list:
            reopen_path=next((x for x in qdirs if x.name==rec["question"]),None)
            if reopen_path: reopen(reopen_path)
    print("WHOLE PAPER AUDIT "+("PASS" if not issues else "FAIL")); [print("-",x) for x in issues]; return 1 if issues else 0


def main()->int:
    ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest="cmd",required=True)
    p=sp.add_parser("init-project"); p.add_argument("path",type=Path); p.add_argument("--id",required=True)
    p=sp.add_parser("init-question"); p.add_argument("path",type=Path); p.add_argument("--id",required=True); p.add_argument("--profile",choices=(PROFILE,"LEGACY_FULL"),default=PROFILE)
    p=sp.add_parser("prepare-stage"); p.add_argument("path",type=Path); p.add_argument("stage",choices=("solve","develop","handoff"))
    p=sp.add_parser("activate-domain"); p.add_argument("path",type=Path); p.add_argument("families",nargs="+")
    p=sp.add_parser("audit-delivery"); p.add_argument("profile",type=Path); p.add_argument("paper",type=Path)
    p=sp.add_parser("impact"); p.add_argument("path",type=Path); p.add_argument("changed",nargs="+"); p.add_argument("--apply",action="store_true")
    p=sp.add_parser("audit-question"); p.add_argument("path",type=Path); p.add_argument("--phase",choices=("scientific","research"),required=True)
    p=sp.add_parser("freeze-scientific"); p.add_argument("path",type=Path)
    p=sp.add_parser("freeze-research"); p.add_argument("path",type=Path)
    p=sp.add_parser("reopen-development"); p.add_argument("path",type=Path)
    p=sp.add_parser("audit-page-budget"); p.add_argument("path",type=Path)
    p=sp.add_parser("audit-paper-qa"); p.add_argument("path",type=Path)
    p=sp.add_parser("audit-paper"); p.add_argument("path",type=Path); p.add_argument("--apply-reopen",action="store_true")
    p=sp.add_parser("benchmark"); p.add_argument("protocol",type=Path); p.add_argument("runs",type=Path)
    p=sp.add_parser("route-depth"); p.add_argument("path",type=Path); p.add_argument("depth",choices=("L1","L2","L3"))
    a=ap.parse_args()
    if a.cmd=="init-project": init_project(a.path,a.id); return 0
    if a.cmd=="init-question": init_question(a.path,a.id,a.profile); return 0
    if a.cmd=="prepare-stage": prepare_stage(a.path,a.stage); return 0
    if a.cmd=="activate-domain": activate_domain(a.path,a.families); return 0
    if a.cmd=="audit-delivery":
        from contest_rules import audit_delivery
        issues=audit_delivery(a.profile,a.paper)
        print("DELIVERY "+("FAIL" if issues else "PASS (mechanical checks; recorded human inspections)"))
        for issue in issues: print("-",issue)
        return bool(issues)
    if a.cmd=="impact":
        result=affected_by_change(a.path,a.changed)
        if a.apply and result["scientific_invalidated"]:
            for name in ("scientific_manifest.json","research_manifest.json"):
                target=a.path/name
                if target.is_file():
                    data=load_json(target); data["status"]="STALE"; data["stale_reason"]=result; write_json(target,data)
            root=project_root(a.path)
            if root:
                qid=load_json(a.path/"question_contract.json")["question_id"]
                state=load_json(root/"project_state.json"); version=state.get("questions",{}).get(qid,{}).get("scientific_version",0)
                mark_dependents_stale(root,qid,version)
                state=load_json(root/"project_state.json"); state["questions"][qid]["status"]="STALE"; write_json(root/"project_state.json",state)
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    if a.cmd=="audit-question": return audit(a.path,a.phase)
    if a.cmd=="freeze-scientific": return freeze_scientific(a.path)
    if a.cmd=="freeze-research": return freeze_research(a.path)
    if a.cmd=="reopen-development": return reopen(a.path)
    if a.cmd=="audit-paper": return audit_whole(a.path,a.apply_reopen)
    if a.cmd=="benchmark": benchmark(a.protocol,a.runs); return 0
    if a.cmd=="route-depth": route_depth(a.path,a.depth); return 0
    issues=audit_page_budget(a.path) if a.cmd=="audit-page-budget" else audit_page_qa(a.path)
    print(("PASS" if not issues else "FAIL")+"\n"+"\n".join(f"- {x}" for x in issues)); return 1 if issues else 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except (OSError,ValueError,KeyError,TypeError) as error:
        print("AUDIT/COMMAND FAIL - invalid or incomplete artifact:",error); raise SystemExit(1)
