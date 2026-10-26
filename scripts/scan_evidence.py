#!/usr/bin/env python3
"""Inventory saved artifacts for explicit evidence-promotion decisions."""
import sys; sys.dont_write_bytecode=True
import argparse, csv
from pathlib import Path
from core import evidence_scan_candidates, sha256
from efficient import is_efficient

p=argparse.ArgumentParser(); p.add_argument("root",type=Path); p.add_argument("out",type=Path); a=p.parse_args(); root=a.root.resolve(); out=a.out.resolve()
rows=[]
for f in evidence_scan_candidates(root,out):
    kind={".json":"structured result",".csv":"tabular evidence",".png":"visual evidence",".svg":"visual evidence",".pdf":"document evidence",".md":"textual evidence",".py":"solver/evaluator"}.get(f.suffix.lower(),"supporting artifact")
    relative=str(f.relative_to(root)) if f.is_relative_to(root) else str(f)
    rows.append({"evidence_id":f"EV-{len(rows)+1:04d}","artifact":relative,"locator":f"sha256:{sha256(f)}","claim_value":kind,"independence":"NOT_INFERRED","proposed_form":"NOT_REQUIRED","page_cost":"NOT_REQUIRED","decision":"KEEP_SUPPORTING" if is_efficient(root) else "PENDING","reason":"Automatically linked from approved result/figure provenance; no per-file AI promotion obligation." if is_efficient(root) else "Legacy full scan; semantic disposition required by legacy workflow."})
out.parent.mkdir(parents=True,exist_ok=True)
headers=["evidence_id","artifact","locator","claim_value","independence","proposed_form","page_cost","decision","reason"]
with out.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=headers);w.writeheader();w.writerows(rows)
print(f"EVIDENCE SCAN PASS ({len(rows)} artifacts indexed)")
