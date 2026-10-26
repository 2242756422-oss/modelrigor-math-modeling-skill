"""Risk-routed work and research acceptance; no weaker scientific standards.

Legacy projects retain their artifact layouts. New projects create only the
current-stage artifacts. Administrative coverage is not a research-quality score.
"""
from __future__ import annotations
import json
from pathlib import Path

PROFILE = "HIGH_QUALITY_EFFICIENT"
COMMON_CHECKS = {"task_semantics", "model_closure", "assumptions_and_limits"}
SPECIALIST_CHECKS = {
    "physical_engineering": {"balance_and_dimensions", "initial_boundary_and_observation", "discretization_and_stability"},
    "optimization": {"feasible_domain_and_information", "objective_and_solver_structure", "solution_certificate_scope"},
    "statistical": {"data_generation_and_identification", "dependence_and_confounding", "estimation_and_uncertainty"},
    "machine_learning": {"split_and_leakage", "generalization_and_comparison", "prediction_uncertainty_and_interpretation"},
    "theoretical": {"definitions_and_quantifiers", "proof_and_counterexample", "degeneracy_and_uniqueness"},
    "direct_calculation": {"exact_relation_and_units", "substitution_and_boundary"},
}
ALIASES = {"physical": "physical_engineering", "physics": "physical_engineering", "engineering": "physical_engineering",
           "operations_research": "optimization", "data_ml": "machine_learning", "ml": "machine_learning",
           "data": "statistical", "statistics": "statistical", "theory": "theoretical"}
ACCEPTANCE_NAMES = ["claim_evidence_map.csv", "figure_candidates.csv", "table_portfolio.csv", "visual_semantics.json", "research_review.json"]
SCIENTIFIC_REUSABLE = {"SCIENTIFIC_CORRECTNESS","DOMAIN_PROFESSIONALISM","MODELING_DEPTH","EVIDENCE_QUALITY"}


def is_efficient(q):
    from core import load_json
    path = q / "question_plan.json"
    return path.is_file() and load_json(path).get("workflow_profile") == PROFILE


def domain_checks(families):
    if isinstance(families, str): families = [families]
    checks = set(COMMON_CHECKS)
    for family in families:
        checks.update(SPECIALIST_CHECKS.get(ALIASES.get(family, family), set()))
    return checks


def audit_adaptive_domain(path):
    from core import load_json, validate_hashed_locator
    d = load_json(path); issues = []; family = d.get("domain_family")
    families = d.get("domain_families", [family]); normalized = [ALIASES.get(f, f) for f in families]
    if not normalized or any(f not in SPECIALIST_CHECKS for f in normalized):
        issues.append("unrecognized domain: explicitly select applicable disciplines")
    expected = domain_checks(families); answers = {x.get("id"): x for x in d.get("checks", [])}
    if not expected.issubset(answers):
        issues.append("missing activated professional checks: " + ",".join(sorted(expected-set(answers))))
    for name in expected:
        row = answers.get(name, {})
        if not row.get("finding") or not row.get("evidence"):
            issues.append("professional finding/evidence missing: " + name)
        for binding in row.get("evidence", []):
            if not validate_hashed_locator(path.parent, binding):
                issues.append("professional evidence stale: " + name)
    if not d.get("domain_objects") or not d.get("model_ladder") or not d.get("ladder_rationale"):
        issues.append("problem-specific domain objects/model choice missing")
    if any(x.get("status") not in ("RESOLVED", "NOT_APPLICABLE") for x in d.get("p0_issues", [])):
        issues.append("unresolved domain P0")
    review = d.get("core_review", {})
    if review.get("outcome") != "ACCEPTED" or not all(review.get(k) for k in ("reviewer", "reasoning", "limitations", "risks_checked")):
        issues.append("substantive core scientific review required; a PASS label is not sufficient")
    for binding in review.get("evidence", []):
        if not validate_hashed_locator(path.parent, binding):
            issues.append("core review evidence invalid")
    if not review.get("evidence"):
        issues.append("core review has no actual evidence")
    for risk in d.get("specialist_attacks", []):
        if risk.get("triggered"):
            if not risk.get("risk") or not risk.get("reasoning") or not validate_hashed_locator(path.parent,risk.get("evidence", "")) or risk.get("outcome") != "RESOLVED":
                issues.append("triggered specialist attack unresolved")
    grounding = d.get("literature_grounding", {})
    if grounding.get("status") not in ("PASS", "NOT_APPLICABLE") or (grounding.get("status") == "NOT_APPLICABLE" and not grounding.get("reason")):
        issues.append("domain grounding unresolved")
    return issues


def scientific_names(q):
    from core import SCIENTIFIC_NAMES, load_json
    names = list(SCIENTIFIC_NAMES)
    domain = q / "domain_model_map.json"
    if is_efficient(q) and domain.is_file() and load_json(domain).get("literature_grounding", {}).get("status") == "NOT_APPLICABLE":
        names.remove("literature_to_model_map.csv")
    return names


def audit_acceptance(q, require_frozen=False):
    from core import (QUALITY, load_json, load_csv, audit_scientific, audit_manifest_bindings,
                      audit_claims, audit_figures, audit_tables, audit_visual_semantics,
                      validate_file_binding, validate_hashed_locator, sha256)
    issues=[]; sm=q/"scientific_manifest.json"
    if not sm.is_file() or load_json(sm).get("status") != "SCIENTIFIC_FROZEN":
        return ["current Scientific Freeze required before research acceptance"]
    issues.extend(audit_manifest_bindings(sm, scientific_names(q)))
    # Structural integrity checks are cheap; experiments are not re-executed.
    issues.extend(audit_scientific(q, load_json(sm).get("scientific_version")))
    missing=[n for n in ACCEPTANCE_NAMES if not (q/n).is_file()]
    if missing: return issues + ["missing acceptance artifact: " + n for n in missing]
    issues.extend(audit_claims(q/"claim_evidence_map.csv", q/"result_registry.json",True))
    family=load_json(q/"domain_model_map.json").get("domain_family", "")
    review=load_json(q/"research_review.json")
    equivalent=review.get("assessments",{}).get("VISUAL_QUALITY",{}).get("mechanism_equivalence",{})
    mechanism_required=None
    if equivalent:
        if equivalent.get("reasoning") and validate_hashed_locator(q,equivalent.get("evidence","")):
            # A simple derivation or inherited valid diagram may already explain
            # the mechanism. Required VISUAL outputs are still checked below.
            mechanism_required=False
        else: issues.append("mechanism equivalent/inheritance requires substantive, bound justification")
    _, local = audit_figures(q/"figure_candidates.csv",family,q/"result_registry.json",mechanism_required); issues.extend(local)
    # A required visual output cannot be closed by a descriptive claim or
    # numeric registry entry. This is a task requirement, not a figure quota.
    contract=load_json(q/"question_contract.json")
    figures=load_csv(q/"figure_candidates.csv")
    for required in contract.get("required_outputs",[]):
        if str(required.get("evidence_type","")).upper() not in ("VISUAL","FIGURE","DIAGRAM","FLOWCHART"):
            continue
        accepted={"DELIVERED","EQUIVALENT"} if required.get("allow_equivalent",False) else {"DELIVERED"}
        candidates=[r for r in figures if required.get("output_id") in r.get("required_output_ids","").split(";") and r.get("status") in accepted]
        if not candidates: issues.append("required scientific visual not delivered: "+str(required.get("output_id")))
    issues.extend(audit_tables(q/"table_portfolio.csv"))
    issues.extend(audit_visual_semantics(q/"visual_semantics.json",q/"figure_candidates.csv"))
    if review.get("outcome") != "ACCEPTED" or not review.get("reviewer"):
        issues.append("substantive research acceptance required")
    if not validate_file_binding(q, review.get("scientific_manifest", "")) or review.get("scientific_manifest","").rsplit("@",1)[0] != "scientific_manifest.json":
        issues.append("acceptance review must bind the current scientific snapshot")
    read=review.get("artifacts_inspected",[])
    if not read or any(not validate_file_binding(q,x) for x in read):
        issues.append("acceptance review inspected artifacts missing/stale")
    claims=load_csv(q/"claim_evidence_map.csv")
    papers={r.get("paper_locator","").split("#",1)[0] for r in claims if r.get("status")=="PASS"}
    inspected={x.rsplit("@",1)[0] for x in read}
    if not papers.issubset(inspected): issues.append("actual question text must be read, not just content-unit locators")
    assessments=review.get("assessments",{})
    for dim in QUALITY:
        a=assessments.get(dim,{})
        if a.get('reuse')=='CURRENT_SCIENTIFIC_FREEZE':
            if dim not in SCIENTIFIC_REUSABLE or a.get('outcome')!='ACCEPTED':
                issues.append('only unchanged scientific dimensions may reuse the current audited snapshot: '+dim)
            # The current manifest and complete scientific integrity were
            # checked above. This is reuse, not a new nominal scientific review.
            continue
        if a.get("outcome") != "ACCEPTED" or not a.get("reasoning") or not a.get("evidence"):
            issues.append("substantive assessment missing: "+dim)
        for x in a.get("evidence",[]):
            if not validate_hashed_locator(q,x): issues.append("assessment evidence stale: "+dim)
    for finding in review.get("findings",[]):
        if finding.get("severity") in ("P0","P1") and finding.get("disposition") not in ("RESOLVED","JUSTIFIED_NOT_APPLICABLE"):
            issues.append("blocking research finding unresolved")
    if require_frozen:
        rm=q/"research_manifest.json"
        if not rm.is_file(): return issues+["research acceptance manifest missing"]
        d=load_json(rm)
        if d.get("status") != "RESEARCH_FROZEN" or d.get("scientific_manifest_sha256") != sha256(sm):
            issues.append("research acceptance snapshot stale")
        issues.extend(audit_manifest_bindings(rm,ACCEPTANCE_NAMES))
    return issues


def evidence_dependencies(q, include_visual=True):
    """Whitelist of scientific/result/visual dependencies; never a root rglob."""
    from core import load_json, load_csv, resolve
    found=set()
    def add(spec):
        if spec:
            p=resolve(q,spec.rsplit("@",1)[0].split("#",1)[0])
            if p.is_file(): found.add(p)
    registry=q/"result_registry.json"
    if registry.is_file():
        for r in load_json(registry).get("results",[]):
            add(r.get("source",{}).get("artifact")); add(r.get("computation_receipt"))
            add(r.get('source',{}).get('origin',{}).get('locator'))
            for v in r.get("verification",[]):
                add(v.get("artifact"))
                p=resolve(q,v.get("artifact",""))
                if p.is_file():
                    vd=load_json(p); add(vd.get("run_receipt")); add(vd.get("output_artifact"))
                    add(vd.get("argument")); add(vd.get("review_evidence"))
                    argument=vd.get('argument_check',{})
                    if isinstance(argument,dict):
                        add(argument.get('argument')); add(argument.get('review_evidence'))
    model=q/"model_contract.json"
    if model.is_file(): add(load_json(model).get("evaluator",{}).get("artifact"))
    for name in ("figure_candidates.csv","table_portfolio.csv") if include_visual else ():
        if (q/name).is_file():
            for r in load_csv(q/name):
                if r.get("status") in ("DELIVERED","EQUIVALENT"):
                    for key in ("data_source","output_path","plot_code","visual_review","generation_receipt"):
                        if not r.get(key,"").startswith("result:"): add(r.get(key))
    # Expand explicit receipt edges only, including raw inputs and actual code.
    frontier=list(found); visited=set()
    while frontier:
        p=frontier.pop()
        if p in visited or p.suffix != ".json": continue
        visited.add(p)
        try: d=load_json(p)
        except (ValueError,OSError): continue
        if isinstance(d,dict) and d.get("kind")=="EXECUTION_RECEIPT":
            for spec in d.get("code",[])+d.get("inputs",[])+d.get("outputs",[])+[d.get("log","")]:
                child=resolve(p.parent,spec.rsplit("@",1)[0])
                child=child.resolve()
                if child.is_file() and child not in found: found.add(child); frontier.append(child)
    return sorted(found)


def affected_by_change(q, changed):
    """No cache bypass: identify the minimal affected result→claim→figure set."""
    from core import load_json, load_csv, resolve
    changed={resolve(q,str(x)) for x in changed}; results=[]
    model_changed=bool(changed & {q.resolve()/"model_contract.json",q.resolve()/"question_contract.json",q.resolve()/"assumption_ledger.csv",q.resolve()/"domain_model_map.json"})
    model=q/"model_contract.json"
    if model.is_file():
        evaluator=resolve(q,load_json(model).get("evaluator",{}).get("artifact",""))
        model_changed=model_changed or evaluator in changed
    registry=q/"result_registry.json"
    for r in load_json(registry).get("results",[]) if registry.is_file() else []:
        dependencies={resolve(q,r.get("source",{}).get("artifact",""))}
        origin=r.get('source',{}).get('origin',{}).get('locator','')
        if origin: dependencies.add(resolve(q,origin.rsplit('@',1)[0].split('#',1)[0]))
        for binding in [r.get("computation_receipt","")]+[v.get("artifact","") for v in r.get("verification",[])]:
            if binding: dependencies.add(resolve(q,binding.rsplit("@",1)[0]))
        for p in list(dependencies):
            if not p.is_file() or p.suffix != ".json": continue
            try: d=load_json(p)
            except (ValueError,OSError): continue
            if isinstance(d,dict) and d.get("kind")=="EXECUTION_RECEIPT":
                dependencies.update(resolve(p.parent,x.rsplit("@",1)[0]) for x in d.get("code",[])+d.get("inputs",[])+d.get("outputs",[]))
            elif isinstance(d,dict) and d.get("run_receipt"):
                receipt=resolve(q,d["run_receipt"].rsplit("@",1)[0]); dependencies.add(receipt)
                if receipt.is_file():
                    run=load_json(receipt); dependencies.update(resolve(receipt.parent,x.rsplit("@",1)[0]) for x in run.get("code",[])+run.get("inputs",[])+run.get("outputs",[]))
            if isinstance(d,dict):
                argument=d.get('argument_check',d)
                if isinstance(argument,dict):
                    dependencies.update(resolve(q,argument[k].rsplit('@',1)[0].split('#',1)[0]) for k in ('argument','review_evidence') if argument.get(k))
        if model_changed or registry.resolve() in changed or dependencies & changed: results.append(r.get("result_id"))
    claim_path=q/"claim_evidence_map.csv"; figure_path=q/"figure_candidates.csv"
    claims=[r.get("claim_id") for r in load_csv(claim_path) if set(r.get("evidence_refs","").split(";")) & {"result:"+x for x in results}] if claim_path.is_file() else []
    figures=[r.get("figure_id") for r in load_csv(figure_path) if r.get("data_source") in {"result:"+x for x in results} or resolve(q,r.get("data_source","")) in changed] if figure_path.is_file() else []
    from core import claim_science_digest
    manifest=q/'scientific_manifest.json'
    claim_changed=(claim_path.resolve() in changed and manifest.is_file() and load_json(manifest).get('scientific_claim_digest')!=claim_science_digest(claim_path))
    if claim_changed:
        claims=[r.get('claim_id') for r in load_csv(claim_path)]
    if figure_path.is_file():
        for row in load_csv(figure_path):
            paths={resolve(q,row[k].rsplit('@',1)[0].split('#',1)[0]) for k in ('plot_code','output_path','visual_review','generation_receipt') if row.get(k)}
            if paths & changed and row.get('figure_id') not in figures: figures.append(row.get('figure_id'))
    scientific=bool(model_changed or results or claim_changed)
    return {"scientific_invalidated": scientific, "result_ids": results, "claim_ids": claims,
            "figure_ids": figures, "presentation_changed": bool(changed) and not scientific,
            "action": "REVALIDATE_AFFECTED_RESULTS" if model_changed or results else 'RECHECK_CHANGED_CLAIMS_AND_GATES' if claim_changed else "CHECK_EDITED_TEXT_OR_FIGURES_AND_FINAL_LAYOUT"}
