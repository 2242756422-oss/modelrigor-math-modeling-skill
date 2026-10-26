#!/usr/bin/env python3
"""Derive unambiguous scientific-value bindings; do not guess result identity.

Ordinary structure is filtered by core.scientific_numeric_tokens. Ambiguous or
unregistered scientific values remain unresolved for targeted review, not
silently assigned to an arbitrary registry result with the same number.
"""
import argparse
import csv
import json
from pathlib import Path
from core import load_json, document_text, read_document, scientific_numeric_tokens, sha256


def derive(paper, question_dirs):
    records={}
    for q in question_dirs:
        for result in load_json(q/"result_registry.json").get("results",[]):
            if result.get("approved"):
                records.setdefault(str(result.get("display_value")),[]).append(result["result_id"])
    rows=[]; unresolved=[]; digest=sha256(paper)
    document=read_document(paper); document_text(paper,document)
    for segment in document['segments']:
      for paragraph in segment['text'].splitlines():
        for value in scientific_numeric_tokens(paragraph):
            matches=records.get(value,[])
            if len(matches)!=1:
                unresolved.append({"value":value,"context":paragraph,"candidate_result_ids":matches}); continue
            fragment=(f"page={segment['page']}::" if 'page' in segment else '')+paragraph
            rows.append({"paper_value_id":f"PV-{len(rows)+1:04d}","paper_locator":str(paper.resolve())+"#"+fragment,
                         "paper_sha256":digest,"displayed_value":value,"source_kind":"RESULT_REGISTRY",
                         "source_id":matches[0],"source_display_value":value,"source_evidence":"","status":"PASS"})
    return rows,unresolved


if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("paper",type=Path); p.add_argument("question_dirs",nargs="+",type=Path); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    rows,unresolved=derive(a.paper,a.question_dirs)
    header=["paper_value_id","paper_locator","paper_sha256","displayed_value","source_kind","source_id","source_display_value","source_evidence","status"]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=header); writer.writeheader(); writer.writerows(rows)
    print(json.dumps({"derived_bindings":len(rows),"targeted_review_required":unresolved},ensure_ascii=False,indent=2))
    raise SystemExit(1 if unresolved else 0)
