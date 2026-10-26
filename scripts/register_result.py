#!/usr/bin/env python3
from __future__ import annotations

import sys; sys.dont_write_bytecode=True
import argparse
import json
from pathlib import Path

from core import load_json, read_result_value, sha256
from provenance import audit_verification, audit_result_origin, source_equal, display_matches


def parse_value(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("registry", type=Path)
    p.add_argument("--id", required=True)
    p.add_argument("--meaning", required=True)
    p.add_argument("--unit", default="")
    p.add_argument("--raw-value", help="Optional assertion against the automatically read source value")
    p.add_argument("--display-value", help="Optional rounded display; defaults to source value")
    p.add_argument("--computation-receipt", default="")
    p.add_argument("--source-type", choices=("json_pointer", "csv_cell", "analytical"), required=True)
    p.add_argument("--source-category", choices=("COMPUTED","ANALYTICAL","OBSERVED","GIVEN","DEMO"))
    p.add_argument("--origin-provider")
    p.add_argument("--origin-nature")
    p.add_argument("--origin-locator")
    p.add_argument("--demo-label")
    p.add_argument("--artifact", required=True)
    p.add_argument("--pointer")
    p.add_argument("--row", type=int)
    p.add_argument("--column")
    p.add_argument("--required-output", action="append", default=[])
    p.add_argument("--scientific-version", type=int, required=True)
    p.add_argument("--verification-artifact", type=Path)
    a = p.parse_args()
    reg = load_json(a.registry)
    if any(r.get("result_id") == a.id for r in reg.get("results", [])):
        raise SystemExit("duplicate result_id")
    art = a.artifact
    art_path = Path(art) if Path(art).is_absolute() else (a.registry.parent / art).resolve()
    if not art_path.exists():
        raise SystemExit("source artifact missing")
    source = {"type": a.source_type, "artifact": art}
    if a.source_category: source['category']=a.source_category
    if any((a.origin_provider,a.origin_nature,a.origin_locator)):
        source['origin']={'provider':a.origin_provider,'nature':a.origin_nature,'locator':a.origin_locator}
    if a.demo_label: source['demo_label']=a.demo_label
    if not a.required_output and a.source_category not in ('GIVEN','OBSERVED'):
        raise SystemExit('modeled result must identify the required output; input data/parameters may omit it')
    if a.source_type in ("json_pointer", "analytical"): source["pointer"] = a.pointer
    elif a.source_type == "csv_cell": source.update({"row": a.row, "column": a.column})
    r = {
        "result_id": a.id, "meaning": a.meaning, "unit": a.unit,
        "raw_value": parse_value(a.raw_value) if a.raw_value is not None else None, "display_value": a.display_value,
        "display_tolerance": 0, "source_tolerance": 0, "source": source,
        "artifact_sha256": sha256(art_path), "scientific_version": a.scientific_version,
        "required_output_ids": a.required_output, "verification": [], "approved": False,
        "computation_receipt": a.computation_receipt,
    }
    actual, issues = read_result_value(r, a.registry.parent)
    if issues or (a.raw_value is not None and not source_equal(actual,r["raw_value"])):
        raise SystemExit("source value mismatch: " + "; ".join(issues))
    r["raw_value"]=actual
    r["display_value"]=a.display_value if a.display_value is not None else str(actual)
    if not display_matches(actual,r["display_value"]):
        raise SystemExit("display does not follow source-derived rounding")
    if a.verification_artifact:
        vp = a.verification_artifact.resolve()
        vd = load_json(vp)
        verification_issues=audit_verification(a.registry.parent,vd,r)
        if vd.get("status") != "PASS" or not vd.get("method") or vd.get("scientific_version")!=a.scientific_version or verification_issues:
            raise SystemExit("verification is unresolved: "+"; ".join(verification_issues))
        r["verification"] = [{"id": vp.stem, "artifact": str(vp), "sha256": sha256(vp), "status": "PASS"}]
        r["approved"] = True
        origin_issues=audit_result_origin(a.registry.parent,r)
        if origin_issues: raise SystemExit('source provenance unresolved: '+'; '.join(origin_issues))
    reg.setdefault("results", []).append(r)
    a.registry.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("RESULT REGISTERED FROM RESOLVED SOURCE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
