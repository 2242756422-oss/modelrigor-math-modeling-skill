#!/usr/bin/env python3
"""Minimal false-positive probes for the v5 build (read-only against build)."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BUILD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUILD / "scripts"))

from core import (  # noqa: E402
    REVIEWERS,
    audit_claims,
    audit_conditional_gates,
    audit_content,
    audit_figures,
    audit_page_budget,
    audit_page_qa,
    audit_result_registry,
    audit_reviewers,
    audit_research,
    audit_scientific,
    audit_uncertainty,
    sha256,
)
from cqex import route_depth  # noqa: E402


def jwrite(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cwrite(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows([{k: row.get(k, "") for k in header} for row in rows])


def probe(name: str, false_positive: bool, detail: str) -> tuple[str, bool, str]:
    print(f"{name}: {'FALSE_POSITIVE' if false_positive else 'BLOCKED'} — {detail}")
    return name, false_positive, detail


def main() -> int:
    found: list[tuple[str, bool, str]] = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        page = json.loads((BUILD / "templates/page_budget.json").read_text(encoding="utf-8"))
        page["hard_page_compliance"].update({
            "status": "VERIFIED", "official_rule_source": "missing-official.pdf",
            "competition_year": 2099, "source_sha256": "forged", "locator": "p.1",
            "verbatim_excerpt": "forged", "total_page_limit": -7,
            "counting_scope": {k: "UNKNOWN" for k in ("cover", "abstract", "main_text", "references", "appendix", "ai_declaration")},
        })
        pp = d / "page_budget.json"; jwrite(pp, page)
        found.append(probe("PAGE_MISSING_SOURCE_NEGATIVE_LIMIT", not audit_page_budget(pp), "nonexistent official source and negative page limit accepted"))

        page = json.loads((BUILD / "templates/page_budget.json").read_text(encoding="utf-8"))
        page["total_page_limit"] = 19
        pp2 = d / "page_budget_root_limit.json"; jwrite(pp2, page)
        found.append(probe("PAGE_ROOT_UNSUPPORTED_LIMIT", not audit_page_budget(pp2), "legacy root total_page_limit survives UNSET"))

        plan = d / "plan.json"; jwrite(plan, {"question_depth": "L1", "allocated_pages": 6.5, "question_page_targets": {"q1": 3}, "figures_required": 5})
        route_depth(plan, "L3")
        routed = json.loads(plan.read_text())
        found.append(probe("DEPTH_ROUTER_LEGACY_KEYS_SURVIVE", any(k in routed for k in ("allocated_pages", "question_page_targets", "figures_required")), "router only removes a narrow key list"))

        rp = d / "result_registry.json"; jwrite(rp, {"schema_version": "5.0", "results": []})
        found.append(probe("EMPTY_RESULT_REGISTRY", not audit_result_registry(rp), "zero results accepted"))

        proof = d / "proof.md"; proof.write_text("TOKEN_ONLY\n", encoding="utf-8")
        reg = {"schema_version": "5.0", "results": [{
            "result_id": "R1", "meaning": "claimed optimum", "unit": "m", "raw_value": 2,
            "display_value": "999 m", "source": {"type": "analytical", "artifact": "proof.md", "locator": "TOKEN_ONLY"},
            "artifact_sha256": sha256(proof), "scientific_version": 1, "verification": [], "approved": False,
        }]}
        jwrite(rp, reg)
        found.append(probe("UNAPPROVED_RESULT_BAD_DISPLAY", not audit_result_registry(rp), "unapproved result and unrelated display value accepted"))

        claim_header = json.loads((BUILD / "schemas/csv_headers.json").read_text())["claim_evidence_map.csv"]
        cp = d / "claims.csv"; cwrite(cp, claim_header, [])
        found.append(probe("EMPTY_CLAIM_MAP", not audit_claims(cp, rp), "zero claims accepted"))
        cwrite(cp, claim_header, [{
            "claim_id": "C1", "claim_text": "globally optimal and robust", "claim_type": "result",
            "paper_locator": "missing-paper.md#NOPE", "evidence_refs": "result:R1", "scope": "all cases",
            "boundary": "none", "status": "PASS",
        }])
        found.append(probe("CLAIM_FAKE_PAPER_LOCATOR_UNAPPROVED_RESULT", not audit_claims(cp, rp), "strong claim can cite nonexistent paper location and unapproved result"))

        uncertainty = json.loads((BUILD / "templates/uncertainty_budget.json").read_text())
        for row in uncertainty["categories"]:
            row.update({"status": "ASSESSED", "risk": "high", "impact": "large", "verification": []})
        uncertainty["dominant_risks"] = ["not-a-category"]
        up = d / "uncertainty.json"; jwrite(up, uncertainty)
        found.append(probe("UNCERTAINTY_NO_VERIFICATION", not audit_uncertainty(up), "dominant risk need not resolve to a category or verification"))

        content_header = json.loads((BUILD / "schemas/csv_headers.json").read_text())["content_units.csv"]
        cont = d / "content.csv"; cwrite(cont, content_header, [{
            "unit_id": "U1", "question_id": "q1", "requirement": "complete derivation", "importance": "HIGH",
            "evidence_refs": "DOES_NOT_EXIST", "paper_locator": "missing.md#NOPE", "development": "self report",
            "promotion_decision": "KEEP", "redundancy": "NO", "status": "COVERED",
        }])
        found.append(probe("CONTENT_FAKE_LOCATORS", audit_content(cont)[0] == "APPROPRIATE", "content adequacy accepts unresolved evidence and paper locators"))

        figure_header = json.loads((BUILD / "schemas/csv_headers.json").read_text())["figure_candidates.csv"]
        figs = d / "figures.csv"; cwrite(figs, figure_header, [{
            "figure_id": "F1", "question_id": "q1", "role": "MECHANISM", "research_question": "how",
            "message": "mechanism", "data_source": "none", "preferred_chart_type": "schematic", "figure_cost": "L",
            "page_cost": "L", "importance": "HIGH", "status": "NOT_APPLICABLE", "equivalent_expression": "",
            "output_path": "", "source_sha256": "",
        }])
        found.append(probe("PHYSICAL_MECHANISM_NOT_APPLICABLE_NO_REASON", audit_figures(figs, "physical")[0] == "PASS", "physical mechanism gate is bypassed by bare NOT_APPLICABLE"))
        cwrite(figs, figure_header, [{
            "figure_id": "F1", "question_id": "q1", "role": "MECHANISM", "research_question": "how",
            "message": "mechanism", "data_source": "none", "preferred_chart_type": "schematic", "figure_cost": "L",
            "page_cost": "L", "importance": "HIGH", "status": "EQUIVALENT", "equivalent_expression": "missing.md#NOPE",
            "output_path": "", "source_sha256": "",
        }])
        found.append(probe("PHYSICAL_FAKE_EQUIVALENT", audit_figures(figs, "physical")[0] == "PASS", "nonexistent equivalent expression accepted"))

        rd = d / "reviews"; rd.mkdir()
        for i, role in enumerate(REVIEWERS):
            jwrite(rd / f"{role}.json", {
                "role": role, "run_id": f"forged-{i}", "independent": True,
                "input_hashes": {"missing": "forged"}, "artifacts_read": ["missing"], "overall": "PASS",
            })
        found.append(probe("FORGED_REVIEWERS", not audit_reviewers(rd), "five distinct self-declared run IDs with fake inputs accepted"))

        gates = json.loads((BUILD / "templates/conditional_gates.json").read_text())
        # Exercise current schema without assuming older claim booleans remain.
        for name in ("benchmark", "bound_gap", "alternative_formulation", "ablation"):
            gates[name].update({"triggered": True, "reason": "self report", "evidence": ["missing.md#NOPE"]})
        gp = d / "gates.json"; jwrite(gp, gates)
        found.append(probe("CONDITIONAL_GATES_FAKE_EVIDENCE", not audit_conditional_gates(gp), "triggered gates accept unresolved evidence"))

        fake_doc = d / "fake.docx"; fake_doc.write_bytes(b"not a zip/docx")
        fake_png = d / "page-99.png"; fake_png.write_bytes(b"not a png and not A4")
        qa = {"paper_artifact": "fake.docx", "paper_sha256": sha256(fake_doc), "page_qa": {"document_sha256": sha256(fake_doc), "pages": [{"page": 99, "image": "page-99.png", "sha256": sha256(fake_png), "manual_status": "PASS", "checks": ["self report"]}]}}
        qap = d / "fake_qa.json"; jwrite(qap, qa)
        found.append(probe("FAKE_WORD_AND_PAGE_QA", not audit_page_qa(qap), "arbitrary bytes pass as DOCX, PNG and A4 page QA"))

        # End-to-end: construct a self-reported question with no results, claims,
        # validations, paper, or real reviews and see whether both freezes pass.
        q = d / "q_fake"; q.mkdir()
        qc = json.loads((BUILD / "templates/question_contract.json").read_text())
        qc.update({"question_id": "q_fake", "task_text_locator": "missing.pdf#q1", "required_outputs": ["answer"], "inputs": ["a"], "decision_or_unknowns": ["x"], "acceptance_evaluator": {"definition": "self-check", "inputs": ["a"], "outputs": ["x"], "aggregation_quantifiers": ["all"]}, "status": "PASS"})
        jwrite(q / "question_contract.json", qc)
        note = q / "domain_note.md"; note.write_text("GENERIC_TOKEN\n", encoding="utf-8")
        domain_report = q / "domain_review.json"; jwrite(domain_report, {"role": "DOMAIN_EXPERT", "run_id": "domain-forged", "overall": "PASS"})
        dm = json.loads((BUILD / "templates/domain_model_map.json").read_text())
        dm.update({"question_id": "q_fake", "domain_family": "theoretical", "domain_objects": ["x"], "model_ladder": ["one line"], "ladder_rationale": "self report", "literature_grounding": {"status": "NOT_APPLICABLE", "reason": "self-contained"}, "review_status": "PASS", "domain_review": {"role": "DOMAIN_EXPERT", "run_id": "domain-forged", "independent": True, "input_hashes": {"missing": "forged"}, "artifacts_read": ["missing"], "report_artifact": "domain_review.json", "report_sha256": sha256(domain_report)}})
        for ans in dm["answers"]:
            ans.update({"answer": "self report", "evidence_locators": ["domain_note.md#GENERIC_TOKEN"]})
        jwrite(q / "domain_model_map.json", dm)
        (q / "literature_to_model_map.csv").write_bytes((BUILD / "templates/literature_to_model_map.csv").read_bytes())
        solver = q / "solver.py"; solver.write_text("def evaluate(a): return a\n", encoding="utf-8")
        mc = json.loads((BUILD / "templates/model_contract.json").read_text())
        mc.update({"question_id": "q_fake", "model_type": "direct_calculation", "mathematical_objects": ["x"], "index_domains": ["scalar"], "inputs": ["a"], "outputs": ["x"], "variables": [{"name": "x", "unit": "1"}], "parameters": [{"name": "a", "unit": "1"}], "governing_relations": ["x=a"], "quantifiers": ["all a"], "evaluator": {"definition": "identity", "artifact": "solver.py", "artifact_sha256": sha256(solver), "version": "1", "inputs": ["a"], "outputs": ["x"], "numerical_interface": "evaluate(a)"}, "identifiability": "self report", "failure_modes": ["none"], "closure_explanations": {"initial_boundary_conditions": "not applicable", "constraints": "all real", "objective": "not optimization"}, "assumption_closure_reason": "self-contained", "status": "PASS"})
        jwrite(q / "model_contract.json", mc)
        (q / "assumption_ledger.csv").write_bytes((BUILD / "templates/assumption_ledger.csv").read_bytes())
        uncertainty = json.loads((BUILD / "templates/uncertainty_budget.json").read_text())
        uncertainty["question_id"] = "q_fake"
        for row in uncertainty["categories"]:
            row.update({"status": "ASSESSED", "risk": "self report", "impact": "self report", "verification": []})
        uncertainty["dominant_risks"] = ["fabricated"]
        jwrite(q / "uncertainty_budget.json", uncertainty)
        jwrite(q / "result_registry.json", {"schema_version": "5.0", "results": []})
        (q / "claim_evidence_map.csv").write_bytes((BUILD / "templates/claim_evidence_map.csv").read_bytes())
        gates = json.loads((BUILD / "templates/conditional_gates.json").read_text())
        for name in ("benchmark", "bound_gap", "alternative_formulation", "ablation"):
            gates[name].update({"triggered": False, "reason": "self report"})
        jwrite(q / "conditional_gates.json", gates)
        sci_issues = audit_scientific(q)
        found.append(probe("SCIENTIFIC_GATE_SELF_REPORT", not sci_issues, "full scientific audit accepts fake prompt locator, fake review inputs, and zero results/claims/validation"))
        freeze_sci = subprocess.run([sys.executable, str(BUILD / "scripts/cqex.py"), "freeze-scientific", str(q)], text=True, capture_output=True)
        found.append(probe("SCIENTIFIC_FREEZE_SELF_REPORT", freeze_sci.returncode == 0, freeze_sci.stdout.strip().splitlines()[-1] if freeze_sci.stdout.strip() else freeze_sci.stderr.strip()))

        # Forge all competitive artifacts as structurally nonempty self-reports.
        ch = json.loads((BUILD / "schemas/csv_headers.json").read_text())
        cwrite(q / "content_units.csv", ch["content_units.csv"], [{"unit_id": "U", "question_id": "q_fake", "source_kind": "invented", "source_ids": "none", "requirement": "complete", "importance": "HIGH", "evidence_refs": "missing", "paper_locator": "missing.md#NOPE", "paper_sha256": "forged", "development": "done", "promotion_decision": "KEEP", "redundancy": "NO", "status": "COVERED"}])
        cwrite(q / "figure_candidates.csv", ch["figure_candidates.csv"], [])
        for name in ("evidence_promotion.csv", "table_portfolio.csv"):
            (q / name).write_bytes((BUILD / "templates" / name).read_bytes())
        dev = json.loads((BUILD / "templates/competitive_development.json").read_text())
        for name in ("derivation_sufficiency", "method_exposition", "formula_architecture", "table_architecture", "result_interpretation", "writing_quality"):
            dev[name] = {"status": "PASS", "evidence_locators": ["missing.md#NOPE"]}
        dev["evidence_promotion"] = {"status": "PASS", "scanned_roots": ["missing"], "decision_artifact": "evidence_promotion.csv"}
        dev["hero_figure_attempt"] = {"status": "NOT_APPLICABLE", "reason": "self report", "candidate_id": None}
        dev["peer_gap"] = {"status": "PASS", "comparison_sources": ["invented"], "gaps": [], "disposition": ["done"]}
        jwrite(q / "competitive_development.json", dev)
        reviews = q / "reviews"; reviews.mkdir()
        for i, role in enumerate(REVIEWERS):
            jwrite(reviews / f"{role}.json", {"role": role, "run_id": f"fake-{i}", "independent": True, "input_hashes": {"missing": "forged"}, "artifacts_read": ["missing"], "overall": "PASS"})
        quality = json.loads((BUILD / "templates/quality_assessment.json").read_text())
        for name in quality["dimensions"]:
            quality["dimensions"][name] = {"status": "PASS", "evidence_locators": ["missing.md#NOPE"], "reviewer_run_ids": ["invented"]}
        jwrite(q / "quality_assessment.json", quality)
        research_issues = audit_research(q)
        found.append(probe("RESEARCH_GATE_SELF_REPORT", not research_issues, "research audit accepts fabricated locators/review provenance and empty evidence promotion/tables"))
        freeze_research = subprocess.run([sys.executable, str(BUILD / "scripts/cqex.py"), "freeze-research", str(q)], text=True, capture_output=True)
        found.append(probe("RESEARCH_FREEZE_SELF_REPORT", freeze_research.returncode == 0, freeze_research.stdout.strip().splitlines()[-1] if freeze_research.stdout.strip() else freeze_research.stderr.strip()))
        reopen = subprocess.run([sys.executable, str(BUILD / "scripts/cqex.py"), "reopen-development", str(q)], text=True, capture_output=True)
        reopened_still_audits = reopen.returncode == 0 and not audit_research(q)
        found.append(probe("REOPENED_STATE_STILL_RESEARCH_AUDITS_PASS", reopened_still_audits, "audit_research does not validate Research Manifest status or its frozen bindings"))

        # Handoff can bind a DRAFT manifest and arbitrary one-character contracts.
        draft_manifest = q / "draft_manifest.json"; jwrite(draft_manifest, {"scientific_version": 0, "status": "DRAFT"})
        handoff = {"from_question": "q1", "to_question": "q2", "scientific_version": 0, "scientific_manifest": "draft_manifest.json", "scientific_manifest_sha256": sha256(draft_manifest), "objects": ["x"], "symbols_units": {"x": "?"}, "assumptions": [], "evaluator_contract": "x", "status": "READY"}
        hp = q / "handoff_bad.json"; jwrite(hp, handoff)
        handoff_run = subprocess.run([sys.executable, str(BUILD / "scripts/check_handoff.py"), str(hp)], text=True, capture_output=True)
        found.append(probe("HANDOFF_BINDS_DRAFT_MANIFEST", handoff_run.returncode == 0, handoff_run.stdout.strip().splitlines()[0] if handoff_run.stdout.strip() else handoff_run.stderr.strip()))

    total = sum(hit for _, hit, _ in found)
    print(f"FALSE_POSITIVES={total}/{len(found)}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
