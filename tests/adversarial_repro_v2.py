#!/usr/bin/env python3
"""Second-wave bypass probes for the stable v5 candidate."""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BUILD = Path(__file__).resolve().parents[1]
SCRIPTS = BUILD / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import (  # noqa: E402
    QUALITY,
    REVIEWERS,
    audit_evidence_promotion,
    audit_page_budget,
    audit_paper,
    audit_paper_numeric_map,
    audit_resource_consumption,
    audit_result_registry,
    audit_reviewers,
    audit_whole_problem_map,
    load_json,
    sha256,
)
from cqex import freeze_research, freeze_scientific, init_project  # noqa: E402
from run_semantic_regressions import (  # noqa: E402
    build_valid_question,
    hashed,
    headers,
    jwrite,
    page_qa_record,
    reviewer,
    write_docx,
    write_png,
)


def cwrite(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows([{k: row.get(k, "") for k in header} for row in rows])


def record(out: list[dict[str, object]], name: str, bypass: bool, detail: str) -> None:
    out.append({"name": name, "bypass": bypass, "detail": detail})
    print(f"{name}: {'BYPASS' if bypass else 'BLOCKED'} — {detail}")


def make_whole(base: Path) -> tuple[Path, Path, Path]:
    wp = base / "whole"
    init_project(wp, "WP")
    q = build_valid_question(wp)
    assert freeze_scientific(q) == 0
    assert freeze_research(q) == 0
    paper = wp / "paper.docx"
    write_docx(paper, "The registered result is 2.")
    image = wp / "page-1.png"
    write_png(image)
    manual = wp / "manual.md"
    manual.write_text("[MODELS] checked\n[ASSUMPTIONS] checked\n[SYMBOLS] checked\n[CLAIMS] checked\n", encoding="utf-8")
    fragments={"models_evaluators":"[MODELS]","assumptions":"[ASSUMPTIONS]","symbols_units":"[SYMBOLS]","claims_results":"[CLAIMS]"}
    whole = load_json(wp / "whole_problem_map.json")
    whole.update({
        "questions": [{"question_id": "q1", "path": "q1"}],
        "dependencies": [],
        "research_roles":{"q1":"theory core"}, "evidence_priorities":{"q1":"verified result"}, "writing_priorities":{"q1":"concise derivation"},
        "consistency_checks": [
            {"category": name, "status": "PASS", "evidence_locator": hashed(manual, fragments[name])}
            for name in fragments
        ],
        "status": "PASS",
    })
    jwrite(wp / "whole_problem_map.json", whole)
    cwrite(wp / "paper_numeric_map.csv", headers("paper_numeric_map.csv"), [{
        "paper_value_id": "PV1", "paper_locator": "paper.docx#2",
        "paper_sha256": sha256(paper), "displayed_value": "2",
        "source_kind":"RESULT_REGISTRY", "source_id": "R1", "source_display_value": "2", "source_evidence":"", "status": "PASS",
    }])
    audit = load_json(BUILD / "templates/whole_paper_audit.json")
    audit.update({
        "paper_artifact": "paper.docx", "paper_sha256": sha256(paper),
        "project_state": "project_state.json", "question_dirs": ["q1"],
        "paper_numeric_map": "paper_numeric_map.csv", "scientific_consistency": "PASS",
        "content_sufficiency": "APPROPRIATE", "quality": {k: "PASS" for k in QUALITY},
    })
    audit["page_qa"] = page_qa_record(wp,paper,image)
    ap = wp / "whole_paper_audit.json"
    jwrite(ap, audit)
    assert not audit_paper(ap), audit_paper(ap)
    return wp, q, ap


def main() -> int:
    findings: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # Official rule semantics: valid source/hash/locator but fake excerpt/year.
        rule = d / "rule.txt"
        rule.write_text("[LIMIT] The total limit is 30 pages.\n", encoding="utf-8")
        page = load_json(BUILD / "templates/page_budget.json")
        page["hard_page_compliance"].update({
            "status": "VERIFIED", "official_rule_source": "rule.txt",
            "competition_year": 1999, "source_sha256": sha256(rule), "locator": "[LIMIT]",
            "verbatim_excerpt": "fabricated excerpt absent from source", "total_page_limit": 30,
            "counting_scope": {k: "UNKNOWN" for k in ("cover", "abstract", "main_text", "references", "appendix", "ai_declaration")},
        })
        pp = d / "page.json"; jwrite(pp, page)
        record(findings, "PAGE_FAKE_EXCERPT_AND_WRONG_YEAR", not audit_page_budget(pp), "VERIFIED does not bind excerpt or current competition year")

        page = load_json(BUILD / "templates/page_budget.json")
        page["question_development"] = {"q1": {"writing": {"target_pages": 6.5}, "depth": "L3"}}
        jwrite(pp, page)
        record(findings, "PAGE_NESTED_DEPTH_TARGET", not audit_page_budget(pp), "nested legacy page targets evade the shallow alias scan")

        # Results: registry row status and cross-version consistency.
        q = build_valid_question(d)
        rr = load_json(q / "result_registry.json")
        rr["results"][0]["verification"][0]["status"] = "FAIL"
        jwrite(q / "result_registry.json", rr)
        record(findings, "VERIFICATION_RECORD_STATUS_IGNORED", not audit_result_registry(q / "result_registry.json", 1), "registry says verification FAIL while report says PASS")
        q = build_valid_question(d)
        rr = load_json(q / "result_registry.json")
        rr["results"][0]["scientific_version"] = 2
        jwrite(q / "result_registry.json", rr)
        record(findings, "RESULT_VERSION_MISMATCH_WITHOUT_EXPECTED_VERSION", not audit_result_registry(q / "result_registry.json"), "result v2 and verification v1 pass the standalone audit")

        # Five structurally valid copies still pass as independent.
        q = build_valid_question(d)
        for p in (q / "reviews").glob("*.json"):
            p.unlink()
        for role in REVIEWERS:
            report=reviewer(q / "reviews", role, q / "paper.md", f"self-{role}")
            report["findings"][0]["statement"]="Cloned review says no issue."
            report["findings"][0]["evidence_locator"]=hashed(q/"paper.md","[P]")
            jwrite(q / "reviews" / f"{role}.json", report)
        record(findings, "CLONED_REVIEWERS_SELF_DECLARE_INDEPENDENCE", not audit_reviewers(q / "reviews"), "five template-identical reviews over one paragraph pass independence")

        # Resource use can be invented around any local file; outputs/results are not resolved.
        resource = d / "ordinary.txt"; resource.write_text("ordinary local file\n", encoding="utf-8")
        validation = d / "validation.md"; validation.write_text("[V] self-declared success\n", encoding="utf-8")
        rc = d / "resource.csv"
        cwrite(rc, headers("resource_consumption.csv"), [{
            "capability_id": "fake", "resource_path": "ordinary.txt", "source_sha256": sha256(resource),
            "reason": "claim resource use", "actual_interface": "none", "inputs": "missing.in",
            "result_ids": "MISSING", "outputs": "missing.out", "exit_code": "0", "adaptations": "none",
            "excluded_legacy_policies": "none", "validation_evidence": hashed(validation, "[V]"),
            "semantic_review_status": "PASS",
        }])
        record(findings, "RESOURCE_CONSUMPTION_FAKE_OUTPUTS", not audit_resource_consumption(rc), "resource path need not be a recognized resource and inputs/outputs/result IDs are unresolved")

        # Evidence promotion can omit saved evidence yet claim scan completeness.
        ep_root = d / "promotion"; ep_root.mkdir()
        kept = ep_root / "kept.json"; kept.write_text("{}\n", encoding="utf-8")
        omitted = ep_root / "omitted.csv"; omitted.write_text("critical,value\n", encoding="utf-8")
        ep = ep_root / "evidence_promotion.csv"
        cwrite(ep, headers("evidence_promotion.csv"), [{
            "evidence_id": "EV-1", "artifact": "kept.json", "locator": f"sha256:{sha256(kept)}",
            "claim_value": "minor", "independence": "SELF", "proposed_form": "text", "page_cost": "low",
            "decision": "KEEP_SUPPORTING", "reason": "self-selected subset",
        }])
        dev = ep_root / "competitive_development.json"
        jwrite(dev, {"evidence_promotion": {"status": "PASS", "scanned_roots": [hashed(validation, "[V]")]}})
        record(findings, "EVIDENCE_PROMOTION_INCOMPLETE_SCAN", not audit_evidence_promotion(ep, dev), "unindexed saved artifact does not invalidate PASS")

        # Scanner can include its prior output and immediately stale its own hash.
        scan_root = d / "scan"; scan_root.mkdir(); (scan_root / "data.json").write_text("{}\n", encoding="utf-8")
        inventory = scan_root / "inventory.csv"
        scan_cmd = [sys.executable, str(SCRIPTS / "scan_evidence.py"), str(scan_root), str(inventory)]
        subprocess.run(scan_cmd, check=True, capture_output=True, text=True)
        second = subprocess.run(scan_cmd, check=True, capture_output=True, text=True)
        rows = list(csv.DictReader(inventory.open(encoding="utf-8")))
        self_rows = [r for r in rows if r["artifact"] == "inventory.csv"]
        stale_self = bool(self_rows) and self_rows[0]["locator"] != f"sha256:{sha256(inventory)}"
        record(findings, "EVIDENCE_SCANNER_SELF_STALES", "PASS" in second.stdout and stale_self, "custom in-root output is indexed before overwrite, producing an immediately stale PASS file")

        # Whole map accepts absent roles/priorities and fabricated shared-object hashes.
        map_root = d / "map"; map_root.mkdir()
        qdirs = []
        for qid in ("q1", "q2"):
            qd = map_root / qid; qd.mkdir(); jwrite(qd / "question_contract.json", {"question_id": qid}); qdirs.append(qd)
        evidence = map_root / "evidence.md"; evidence.write_text("[C] self-declared consistency\n", encoding="utf-8")
        wm = load_json(BUILD / "templates/whole_problem_map.json")
        wm.update({
            "problem_id": "P", "questions": [{"question_id": "q1"}, {"question_id": "q2"}], "dependencies": [],
            "shared_models": [{"id": "ghost-model", "question_hashes": {"q1": "forged", "q2": "forged"}}],
            "shared_evaluators": [{"id": "ghost-evaluator", "question_hashes": {"q1": "forged", "q2": "forged"}}],
            "research_roles": {}, "evidence_priorities": {}, "writing_priorities": {},
            "consistency_checks": [{"category": n, "status": "PASS", "evidence_locator": hashed(evidence, "[C]")} for n in ("models_evaluators", "assumptions", "symbols_units", "claims_results")],
            "status": "PASS",
        })
        wmp = map_root / "whole_problem_map.json"; jwrite(wmp, wm)
        record(findings, "WHOLE_MAP_FAKE_SHARED_HASHES", not audit_whole_problem_map(wmp, qdirs), "shared model/evaluator hashes do not resolve to question artifacts")
        record(findings, "WHOLE_MAP_EMPTY_PRIORITIES", not audit_whole_problem_map(wmp, qdirs), "research roles and evidence/writing priorities may be empty at PASS")

        # Build the suite's own accepted whole-paper fixture, then attack unused registries.
        wp, wq, ap = make_whole(d)
        (wp / "numbering_registry.json").write_text("not json\n", encoding="utf-8")
        (wp / "symbol_registry.json").write_text('{"symbols":[{"symbol":"x","unit":"m"},{"symbol":"x","unit":"s"}]}\n', encoding="utf-8")
        (wp / "figure_portfolio.csv").write_text("figure_id,question_id,role,status,source_manifest,output_path,paper_locator\nF99,q1,MECHANISM,DELIVERED,missing,missing.png,missing\n", encoding="utf-8")
        record(findings, "WHOLE_AUDIT_IGNORES_GLOBAL_REGISTRIES", not audit_paper(ap), "malformed numbering plus contradictory symbols and missing figure still pass")

        state = load_json(wp / "project_state.json"); state["questions"] = {}; jwrite(wp / "project_state.json", state)
        record(findings, "WHOLE_AUDIT_EMPTY_PROJECT_QUESTION_STATE", not audit_paper(ap), "audit scope need not match project_state questions or versions")

        # Numeric map can bind another artifact, and does not prove completeness.
        decoy = wp / "decoy.md"; decoy.write_text("[X] 2\n", encoding="utf-8")
        cwrite(wp / "paper_numeric_map.csv", headers("paper_numeric_map.csv"), [{
            "paper_value_id": "PV1", "paper_locator": "decoy.md#2", "paper_sha256": sha256(decoy),
            "displayed_value": "2", "source_kind":"RESULT_REGISTRY", "source_id": "R1", "source_display_value": "2", "source_evidence":"", "status": "PASS",
        }])
        record(findings, "NUMERIC_MAP_BINDS_DECOY_NOT_PAPER", not audit_paper_numeric_map(wp / "paper_numeric_map.csv", wp / "paper.docx", [wq]), "row locator/hash need not target paper_artifact")
        record(findings, "NUMERIC_MAP_DOES_NOT_DETECT_UNMAPPED_VALUES", not audit_paper(ap), "paper contains unmapped 999 and 2026 but one mapped value closes audit")

        # Global result-id collision silently resolves to the last registry.
        q2 = wp / "q2"; q2.mkdir(); rr2 = load_json(wq / "result_registry.json"); rr2["results"][0]["display_value"] = "999"; jwrite(q2 / "result_registry.json", rr2)
        cwrite(wp / "paper_numeric_map.csv", headers("paper_numeric_map.csv"), [{
            "paper_value_id": "PV2", "paper_locator": "decoy.md#2", "paper_sha256": sha256(decoy),
            "displayed_value": "999", "source_kind":"RESULT_REGISTRY", "source_id": "R1", "source_display_value": "999", "source_evidence":"", "status": "PASS",
        }])
        record(findings, "DUPLICATE_RESULT_IDS_ACROSS_QUESTIONS", not audit_paper_numeric_map(wp / "paper_numeric_map.csv", wp / "paper.docx", [wq, q2]), "duplicate R1 silently overwrites the first question's result")

        # Valid-looking DOCX + arbitrary white image and claimed renderer log pass.
        cwrite(wp / "paper_numeric_map.csv", headers("paper_numeric_map.csv"), [{
            "paper_value_id": "PV1", "paper_locator": "paper.docx#2", "paper_sha256": sha256(wp / "paper.docx"),
            "displayed_value": "2", "source_kind":"RESULT_REGISTRY", "source_id": "R1", "source_display_value": "2", "source_evidence":"", "status": "PASS",
        }])
        write_png(wp/"page-1.png",ink=False)
        record(findings, "WORD_QA_NO_RENDER_CORRESPONDENCE", not audit_paper(ap), "blank generated PNG and arbitrary renderer log are not cryptographically tied to rendering the DOCX")

        # Handoff does not resolve the transferred semantic payload or project version.
        qh = build_valid_question(d / "handoff_project")
        assert freeze_scientific(qh) == 0
        sm = qh / "scientific_manifest.json"
        hand = load_json(BUILD / "templates/handoff.json")
        hand.update({
            "from_question": "q1", "to_question": "q2", "scientific_manifest": "scientific_manifest.json",
            "scientific_version": load_json(sm)["scientific_version"], "scientific_manifest_sha256": sha256(sm),
            "objects": ["ghost-object"], "symbols_units": {"ghost": "?"}, "assumptions": ["ghost-assumption"],
            "evaluator_contract": "ghost-evaluator", "status": "READY",
        })
        hp = qh / "handoff.json"; jwrite(hp, hand)
        hr = subprocess.run([sys.executable, str(SCRIPTS / "check_handoff.py"), str(hp)], text=True, capture_output=True)
        record(findings, "HANDOFF_SEMANTIC_PAYLOAD_UNRESOLVED", hr.returncode == 0, "ghost objects/symbols/assumptions/evaluator pass against a valid manifest")

        # Integrity can skip all real-paper and real-render tests, and omits required docs.
        pkg_parent = d / "pkg"; pkg = pkg_parent / "modelrigor"
        shutil.copytree(BUILD, pkg)
        for p in list(pkg.rglob("*.pyc")):
            p.unlink()
        for p in sorted(pkg.rglob("__pycache__"), reverse=True):
            p.rmdir()
        missing_doc = pkg / "CHANGELOG.md"
        if not missing_doc.exists(): missing_doc = pkg / "V5_CHANGELOG.md"
        if missing_doc.exists(): missing_doc.unlink()
        step_review = Path.home() / ".codex" / "skills" / "cumcm-step-review"
        if step_review.exists():
            try:
                os.symlink(step_review, pkg_parent / "cumcm-step-review")
            except OSError:
                pass
        env = dict(os.environ); env["PYTHONDONTWRITEBYTECODE"] = "1"
        ir = subprocess.run([sys.executable, str(pkg / "scripts/check_skill_integrity.py"), str(pkg)], text=True, capture_output=True, env=env)
        record(findings, "PACKAGING_OMITS_REQUIRED_DOC", ir.returncode == 0 and "OVERALL INTEGRITY PASS" in ir.stdout, "integrity accepts missing changelog")
        record(findings, "INTEGRITY_SKIPS_REAL_PAPER_AND_WORD_QA", ir.returncode == 0 and "OVERALL INTEGRITY PASS" in ir.stdout, "real paper/render/manual evidence arguments are optional and silently skipped")

    count = sum(bool(x["bypass"]) for x in findings)
    print(f"NEW_BYPASSES={count}/{len(findings)}")
    return 1 if count else 0


if __name__ == "__main__":
    raise SystemExit(main())
