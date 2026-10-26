#!/usr/bin/env python3
import sys; sys.dont_write_bytecode=True
import argparse
from pathlib import Path
from core import SCIENTIFIC_NAMES, audit_manifest_bindings, audit_scientific, load_csv, load_json, resolve, sha256, validate_hashed_locator
from efficient import scientific_names

p=argparse.ArgumentParser(); p.add_argument("handoff",type=Path); a=p.parse_args(); d=load_json(a.handoff); issues=[]
for k in ("from_question","to_question","scientific_version","scientific_manifest_sha256","objects","symbols_units","evaluator_contract"):
    if d.get(k) in (None,"",[],{}): issues.append(f"missing {k}")
m=resolve(a.handoff.parent,d.get("scientific_manifest","scientific_manifest.json"))
if not m.is_file() or sha256(m)!=d.get("scientific_manifest_sha256"): issues.append("handoff scientific manifest binding is stale")
else:
    md=load_json(m)
    if md.get("status")!="SCIENTIFIC_FROZEN": issues.append("handoff manifest is not SCIENTIFIC_FROZEN")
    if md.get("scientific_version")!=d.get("scientific_version"): issues.append("handoff scientific version mismatch")
    issues.extend(audit_manifest_bindings(m,scientific_names(m.parent)))
    issues.extend(f"scientific audit: {x}" for x in audit_scientific(m.parent,md.get("scientific_version")))
    model=load_json(m.parent/"model_contract.json")
    allowed_objects=set(model.get("mathematical_objects",[]))
    for group in ("inputs","outputs","variables","parameters"):
        allowed_objects.update(x.get("id",x.get("name")) for x in model.get(group,[]) if isinstance(x,dict))
    if any(x not in allowed_objects for x in d.get("objects",[])): issues.append("handoff contains unknown mathematical objects")
    unit_map={}
    for group in ("inputs","outputs","variables","parameters"):
        for x in model.get(group,[]):
            if isinstance(x,dict): unit_map[x.get("id",x.get("name"))]=x.get("unit")
    if any(name not in unit_map or unit_map[name]!=unit for name,unit in d.get("symbols_units",{}).items()): issues.append("handoff symbol/unit payload disagrees with model contract")
    assumptions={r.get("assumption_id") for r in load_csv(m.parent/"assumption_ledger.csv")}
    if any(x not in assumptions for x in d.get("assumptions",[])): issues.append("handoff contains unknown assumptions")
    if not validate_hashed_locator(a.handoff.parent,d.get("evaluator_contract","")): issues.append("handoff evaluator contract is unresolved or stale")
root=None
for candidate in (a.handoff.parent.parent,a.handoff.parent.parent.parent):
    if (candidate/"project_state.json").is_file(): root=candidate; break
if root:
    rec=load_json(root/"project_state.json").get("questions",{}).get(d.get("from_question"),{})
    if rec.get("status") not in ("SCIENTIFIC_FROZEN","RESEARCH_FROZEN") or rec.get("scientific_version")!=d.get("scientific_version"): issues.append("source question project state/version is not frozen")
if d.get("status")!="READY": issues.append("handoff is not READY")
print("HANDOFF "+("PASS" if not issues else "FAIL")); [print("-",x) for x in issues]
raise SystemExit(1 if issues else 0)
