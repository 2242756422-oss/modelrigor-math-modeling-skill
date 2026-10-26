#!/usr/bin/env python3
"""Whole-paper inventory only; deliberately cannot issue a visual-quality PASS."""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from core import load_json, load_csv, resolve, document_text, sha256


def build_inventory(project):
    whole=load_json(project/"whole_problem_map.json"); state=load_json(project/"project_state.json")
    questions=whole.get("questions",[]); rows=[]; tables=[]; blockers=[]
    allowed={"SOLVED","DRAFTED","FROZEN","SCIENTIFIC_FROZEN","RESEARCH_FROZEN","LEGACY_COMPLETED"}
    for q in questions:
        qid=q.get("question_id"); record=state.get("questions",{}).get(qid,{})
        if q.get("major",True) and record.get("status",q.get("status")) not in allowed:
            blockers.append(qid or "unnamed question")
        path=resolve(project,q.get("path",qid or ""))
        claims=load_csv(path/"claim_evidence_map.csv") if (path/"claim_evidence_map.csv").exists() else []
        for figure in load_csv(path/"figure_candidates.csv") if (path/"figure_candidates.csv").exists() else []:
            if figure.get("status") not in ("DELIVERED","EQUIVALENT"): continue
            ref=figure.get("paper_locator",""); text=""
            if "#" in ref: text=document_text(resolve(path,ref.split("#",1)[0]))
            panels=figure.get("panels","")
            if panels:
                panel_tasks=json.loads(panels)
            else:
                panel_tasks=[]
            try: count=int(figure.get("panel_count") or 1)
            except (ValueError,TypeError): count=0
            rows.append({"Figure ID":figure.get("figure_id"),"Question":qid,
                         "Section":figure.get("section") or ref,"Figure Role":figure.get("role"),
                         "Chart Type":figure.get("preferred_chart_type"),"Panel Count":count,
                         "Panel Tasks":panel_tasks,"Evidence Claim":figure.get("message"),
                         "Referenced By":[c.get("claim_id") for c in claims if c.get("paper_locator")==ref],
                         "Color Semantics":figure.get("color_semantics","visual_semantics.json"),
                         "Page Cost":figure.get("page_cost"),"Status":figure.get("status"),
                         "Output":figure.get("output_path"),"Text Available":bool(text),
                         "Evidence Bearing":bool(figure.get("data_source") and figure.get("message")),
                         "Action":"PENDING_ACTUAL_VISUAL_REVIEW","Priority":"UNASSESSED"})
        if (path/"table_portfolio.csv").exists():
            tables.extend({"question":qid,**r} for r in load_csv(path/"table_portfolio.csv") if r.get("status")=="DELIVERED")
    panel_roles=[]
    for row in rows:
        tasks=row["Panel Tasks"]
        if tasks:
            panel_roles.extend(t.get("role",row["Figure Role"]) for t in tasks)
        else:
            panel_roles.append(row["Figure Role"])
    return {"trigger_ready":bool(questions) and not blockers,"not_ready_questions":blockers,
            "formal_figure_count":sum(r["Status"]=="DELIVERED" for r in rows),
            "effective_panel_count":sum(r["Panel Count"] for r in rows if r["Status"]=="DELIVERED"),
            "evidence_bearing_figure_count":sum(r["Evidence Bearing"] for r in rows if r["Status"]=="DELIVERED"),
            "table_count":len(tables),"question_distribution":dict(Counter(r["Question"] for r in rows)),
            "role_distribution":dict(Counter(panel_roles)),"formal_role_distribution":dict(Counter(r["Figure Role"] for r in rows)),"figures":rows,"tables":tables,
            "page_budget_sha256":sha256(project/"page_budget.json"),
            "limits":"Inventory counts declared panels; inspect actual panels, captions, flowcharts embedded only in Word, and rendered page rhythm before accepting these counts. This is not a scientific/visual PASS."}


def main():
    p=argparse.ArgumentParser(); p.add_argument("project",type=Path); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    inventory=build_inventory(a.project)
    if not inventory["trigger_ready"]:
        print("WHOLE-PAPER VISUAL AUDIT NOT READY:",inventory["not_ready_questions"]); return 1
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"whole_paper_figure_inventory.json").write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# WHOLE_PAPER_FIGURE_AUDIT", "", "Status: PENDING_ACTUAL_WHOLE_PAPER_REVIEW", "",
           f"A. Formal Figure Count: {inventory['formal_figure_count']}",f"B. Effective Panel Count: {inventory['effective_panel_count']}",
           f"C. Evidence-bearing Figure Count: {inventory['evidence_bearing_figure_count']}",f"D. Table Count: {inventory['table_count']}",
           "", "Inventory: whole_paper_figure_inventory.json; page_budget is hash-bound above.", ""]
    for heading in ("各问题/角色分布","视觉密度和图文顺序","跨问重复与新增结构","缺失核心Figure及信息损失","DELETE候选","MERGE候选","MOVE_TO_APPENDIX候选","颜色/字体/视觉一致性","Page Budget影响","最终Figure Portfolio"):
        lines += ["## "+heading,"","待实际阅读全文、查看所有正式图和A4页面；不得用数量/字段代替审查。",""]
    lines += ["Allowed actions: KEEP / POLISH / REDRAW / MERGE / DELETE / MOVE_TO_APPENDIX / CONVERT_TO_TABLE / ADD_MISSING_FIGURE.","Priority: P0 core argument missing; P1 material improvement; P2 optional if space. No automatic redraw."]
    (a.out/"WHOLE_PAPER_FIGURE_AUDIT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("INVENTORY CREATED; WHOLE-PAPER SCIENTIFIC VISUAL REVIEW STILL REQUIRED"); return 0


if __name__=="__main__": raise SystemExit(main())
