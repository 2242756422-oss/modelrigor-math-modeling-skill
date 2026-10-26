#!/usr/bin/env python3
"""Allocate a stable equation/figure/table/algorithm number once."""
import argparse, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("registry",type=Path);p.add_argument("kind",choices=("equation","figure","table","algorithm"));p.add_argument("stable_id");p.add_argument("--question",required=True);a=p.parse_args();d=json.loads(a.registry.read_text())
for rec in d.get("allocations",[]):
    if rec.get("stable_id")==a.stable_id:
        if rec.get("kind")!=a.kind:raise SystemExit("stable_id already allocated to another kind")
        print(rec["number"]);raise SystemExit(0)
d["counters"][a.kind]=int(d["counters"].get(a.kind,0))+1;number=d["counters"][a.kind];d.setdefault("allocations",[]).append({"stable_id":a.stable_id,"kind":a.kind,"question_id":a.question,"number":number});a.registry.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(number)
