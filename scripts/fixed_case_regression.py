#!/usr/bin/env python3
from __future__ import annotations
import sys; sys.dont_write_bytecode=True
import argparse
import copy
import json
import re
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile
from core import load_json, sha256


def inspect_docx(path: Path) -> dict:
    with ZipFile(path) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/") and not n.endswith("/")]
        xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    paragraphs = re.findall(r"<w:p[\s\S]*?</w:p>", xml)
    captions = []
    for p in paragraphs:
        parts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p)
        text = "".join(parts).strip()
        if re.match(r"^图\s*[1-9]", text): captions.append(text)
    return {"sha256": sha256(path), "embedded_images": len(media), "captions": captions}


def assess(features: dict) -> dict:
    f = features["reviewed_features"]
    missing_roles = sorted(set(f["applicable_visual_roles"]) - set(f["covered_visual_roles"]))
    science = "LARGELY_PASS" if f["scientific_provenance_and_verification_largely_present"] else "FAIL"
    domain = "PASS" if f["domain_standard_chain_enters_main_model_sufficiently"] and f["domain_omission_impact_closed"] else "NEEDS_DEVELOPMENT"
    content = "APPROPRIATE" if all([f["q2_structural_method_fully_developed"], f["q3_core_mechanism_fully_developed"], f["high_value_evidence_promoted"]]) else "UNDERDEVELOPED"
    visual = "PASS" if not missing_roles else "FAIL"
    competitive = "PASS" if domain == "PASS" and content == "APPROPRIATE" and visual == "PASS" and not f["caveat_repetition_obscures_contribution"] else "FAIL"
    action = "POLISH" if competitive == "PASS" else "REOPEN_FOR_DEVELOPMENT"
    return {"SCIENTIFIC_CORRECTNESS": science, "DOMAIN_PROFESSIONALISM": domain, "CONTENT_DEPTH": content, "VISUAL_QUALITY": visual, "COMPETITIVE_QUALITY": competitive, "missing_visual_roles": missing_roles, "action": action}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("features", type=Path)
    p.add_argument("--paper", type=Path)
    p.add_argument("--counterfactual", action="store_true")
    a = p.parse_args()
    d = load_json(a.features)
    if a.paper:
        actual = inspect_docx(a.paper)
        if actual["sha256"] != d["source_sha256"] or actual["embedded_images"] != d["extraction"]["embedded_images"]:
            print("FIXED CASE PROVENANCE FAIL")
            return 1
        if len(actual["captions"]) != d["extraction"]["embedded_images"]:
            print("FIXED CASE CAPTION EXTRACTION FAIL")
            return 1
        with tempfile.TemporaryDirectory() as td:
            anonymous=Path(td)/"anonymous_submission.docx"; shutil.copy2(a.paper,anonymous)
            if inspect_docx(anonymous)!=actual:
                print("FIXED CASE ANONYMOUS COPY REGRESSION FAIL")
                return 1
    if a.counterfactual:
        d = copy.deepcopy(d)
        f = d["reviewed_features"]
        f.update({
            "domain_standard_chain_enters_main_model_sufficiently": True,
            "domain_omission_impact_closed": True,
            "q2_structural_method_fully_developed": True,
            "q3_core_mechanism_fully_developed": True,
            "high_value_evidence_promoted": True,
            "covered_visual_roles": f["applicable_visual_roles"],
            "caveat_repetition_obscures_contribution": False,
            "old_audit_only_polish": False
        })
    result = assess(d)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    expected = ({"DOMAIN_PROFESSIONALISM": "PASS", "CONTENT_DEPTH": "APPROPRIATE", "VISUAL_QUALITY": "PASS", "COMPETITIVE_QUALITY": "PASS", "action": "POLISH"}
                if a.counterfactual else
                {"SCIENTIFIC_CORRECTNESS": "LARGELY_PASS", "DOMAIN_PROFESSIONALISM": "NEEDS_DEVELOPMENT", "CONTENT_DEPTH": "UNDERDEVELOPED", "VISUAL_QUALITY": "FAIL", "COMPETITIVE_QUALITY": "FAIL", "action": "REOPEN_FOR_DEVELOPMENT"})
    ok = all(result[k] == v for k, v in expected.items())
    print("FIXED CASE REGRESSION " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__": raise SystemExit(main())
