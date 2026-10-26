#!/usr/bin/env python3
import sys; sys.dont_write_bytecode=True
import argparse
import json
from pathlib import Path
from core import load_json

p = argparse.ArgumentParser()
p.add_argument("project_state", type=Path)
p.add_argument("--upstream", required=True)
p.add_argument("--change", choices=("scientific", "presentation"), required=True)
a = p.parse_args()
d = load_json(a.project_state)
if a.change == "scientific":
    queue = [a.upstream]
    stale = set()
    while queue:
        cur = queue.pop(0)
        for edge in d.get("dependencies", []):
            if edge.get("from") == cur and edge.get("to") not in stale:
                stale.add(edge["to"]); queue.append(edge["to"])
    for q in stale:
        d.setdefault("questions", {}).setdefault(q, {})["status"] = "STALE"
        d["questions"][q]["stale_reason"] = f"upstream scientific change: {a.upstream}"
    print("SCIENTIFIC STALE propagated to " + ",".join(sorted(stale)))
else:
    d["presentation_version"] = int(d.get("presentation_version", 0)) + 1
    print("PRESENTATION changed; scientific results preserved, paper/QA review required")
a.project_state.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
