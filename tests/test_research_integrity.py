#!/usr/bin/env python3
"""v5.1 adversarial/positive regressions. Fixtures test gates, not prize quality."""
from __future__ import annotations
import copy
import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from core import (audit_result_registry, audit_scientific, audit_research, audit_figures,
                  audit_domain_map, audit_model_contract, audit_paper_numeric_map, equal_value,
                  evidence_scan_candidates, load_json, sha256, _gate_report, summarize_benchmark,
                  scientific_numeric_tokens, QUALITY, claim_science_digest)
from core import audit_conditional_gates
from cqex import (init_question, prepare_stage, freeze_scientific, freeze_research, route_depth, activate_domain)
from efficient import PROFILE, domain_checks, affected_by_change, audit_acceptance, ACCEPTANCE_NAMES
from provenance import display_matches, source_equal
from record_run import record_run
from contest_rules import audit_delivery
from final_visual_inventory import build_inventory
from run_semantic_regressions import build_valid_question,jwrite,cwrite,headers,hashed,write_png


def make_efficient(base):
    q=build_valid_question(base)
    plan=load_json(q/"question_plan.json"); plan["workflow_profile"]=PROFILE; jwrite(q/"question_plan.json",plan)
    note=q/"domain_note.md"; anchor=hashed(note,"[D1]")
    d={"schema_version":"5.1","question_id":"q1","domain_family":"direct_calculation",
       "domain_families":["direct_calculation"],"domain_objects":["real scalar"],
       "checks":[{"id":k,"finding":"Exact relation x=a+1; finite scalar supplied; same units; substitution tested.","evidence":[anchor]} for k in sorted(domain_checks("direct_calculation"))],
       "model_ladder":["exact affine evaluation"],"ladder_rationale":"No approximation is needed for this defined algebraic task.",
       "literature_grounding":{"status":"NOT_APPLICABLE","reason":"self-contained elementary arithmetic"},"p0_issues":[],
       "core_review":{"outcome":"ACCEPTED","reviewer":"structural regression review, not independent science certification",
                      "reasoning":"Unique x follows by explicit equality; actual substitution run agrees for this supplied scalar.",
                      "limitations":"One supplied scalar is not evidence for arbitrary nonlinear/physical tasks.",
                      "risks_checked":["transcription"],"evidence":[anchor,hashed(q/"verification_output.json",'"observed_value"')]},"specialist_attacks":[]}
    jwrite(q/"domain_model_map.json",d)
    u=load_json(q/"uncertainty_budget.json"); u["schema_version"]="5.1"; u["risk_selection_basis"]="Only implementation/transcription enters exact scalar arithmetic."
    u["categories"]=[x for x in u["categories"] if x["status"]=="ASSESSED"]; jwrite(q/"uncertainty_budget.json",u)
    return q


def acceptance_review(q):
    sm=q/"scientific_manifest.json"; paper=q/"paper.md"
    anchor=hashed(paper,"[P]")
    review={"outcome":"ACCEPTED","reviewer":"regression fixture reviewer (not a contest-quality certification)",
            "scientific_manifest":sm.name+"@"+sha256(sm),"artifacts_inspected":[paper.name+"@"+sha256(paper)],
            "assessments":{k:{"outcome":"ACCEPTED","reasoning":"Scalar task is fully stated, derived and bounded in the inspected paragraph; this is only a gate fixture.","evidence":[anchor]} for k in QUALITY},"findings":[]}
    jwrite(q/"research_review.json",review)


class Integrity(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.base=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def question(self): return build_valid_question(self.base)

    def test_inflated_source_tolerance_cannot_promote_2_to_900000(self):
        q=self.question(); registry=load_json(q/"result_registry.json")
        registry["results"][0].update(raw_value=900000,display_value="900000",source_tolerance=1000000)
        jwrite(q/"result_registry.json",registry)
        self.assertTrue(audit_result_registry(q/"result_registry.json"))
        self.assertTrue(audit_scientific(q))
        self.assertNotEqual(freeze_scientific(q),0)

    def test_exact_source_recursive_nan_bool_and_invalid_tolerance(self):
        self.assertFalse(source_equal([math.nan],[math.nan]))
        self.assertFalse(source_equal(True,1)); self.assertFalse(equal_value(2,900000,math.inf))
        self.assertFalse(equal_value(2,2,-1)); self.assertTrue(source_equal({"x":[1,2.0]},{"x":[1.0,2]}))

    def test_display_rounding_not_user_tolerance(self):
        self.assertTrue(display_matches(1.23456,"1.235")); self.assertFalse(display_matches(2,"900000"))
        self.assertFalse(display_matches(math.nan,"nan"))

    def test_pass_only_is_not_independent_verification(self):
        q=self.question(); v=q/"verify.json"
        jwrite(v,{"status":"PASS","method":"independent verification","observed_value":2,"scientific_version":1})
        r=load_json(q/"result_registry.json"); r["results"][0]["verification"][0]["sha256"]=sha256(v); jwrite(q/"result_registry.json",r)
        self.assertTrue(audit_result_registry(q/"result_registry.json"))

    def test_word_qa_unattributed_pass_declaration_is_rejected(self):
        render=self.base/"render"; render.mkdir(); write_png(render/"page-1.png")
        review=self.base/"page_review.json"
        jwrite(review,{"overall":"PASS","pages":[],"blocking_findings":[]})
        command=[sys.executable,str(ROOT/"scripts/real_word_qa_regression.py"),
                 "--paper",str(self.base/"not_rendered.docx"),"--render-dir",str(render),
                 "--renderer-artifact",str(self.base/"missing_manifest.json"),"--page-review",str(review)]
        result=subprocess.run(command,text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn("attributed page inspection",result.stdout+result.stderr)

    def test_real_execution_assertions_are_rechecked(self):
        q=self.question(); self.assertFalse(audit_result_registry(q/"result_registry.json"))
        out=q/"verification_output.json"; d=load_json(out); d["checks"][0]["expected"]=99; jwrite(out,d)
        # Even if the source output hash is re-bound, arithmetic check must fail.
        receipt=q/"verification_run.json"; rec=load_json(receipt)
        rec["outputs"]=[str(out)+"@"+sha256(out)]; jwrite(receipt,rec)
        v=q/"verify.json"; vd=load_json(v); vd["run_receipt"]=receipt.name+"@"+sha256(receipt); jwrite(v,vd)
        r=load_json(q/"result_registry.json"); r["results"][0]["verification"][0]["sha256"]=sha256(v); jwrite(q/"result_registry.json",r)
        self.assertTrue(audit_result_registry(q/"result_registry.json"))

    def test_same_receipt_cannot_claim_independent_implementation(self):
        q=self.question(); v=q/"verify.json"; d=load_json(v)
        d.update(independent=True,independence_basis="same program is claimed independent")
        jwrite(v,d); r=load_json(q/"result_registry.json")
        r["results"][0]["computation_receipt"]=d["run_receipt"]
        r["results"][0]["verification"][0]["sha256"]=sha256(v); jwrite(q/"result_registry.json",r)
        self.assertTrue(audit_result_registry(q/"result_registry.json"))

    def benchmark(self):
        protocol={"triggered":True,"metric":"score","direction":"minimize","tolerance":0,"tolerance_basis":"Exact gate-test integers, not scientific inference.","fairness":{k:"SAME" for k in ("data","evaluator","feasible_set","budget","termination","metric","direction","hardware","parallelism")}}
        runs=[]
        for method,value in (("A",1),("B",100)):
            code=self.base/(method+".py"); output=self.base/(method+".json"); receipt=self.base/(method+"-run.json")
            code.write_text('import json\nwith open("'+output.name+'","w") as f: json.dump({"score":'+str(value)+'},f)\n')
            record_run(self.base,[sys.executable,code.name],[code.name],[],[output.name],receipt)
            runs.append({"method":method,"score":value,"feasible":True,"run_receipt":receipt.name+"@"+sha256(receipt),"output_artifact":output.name,"metric_pointer":"/score"})
        d={**summarize_benchmark(protocol,runs),"protocol":protocol,"runs":runs}
        report=self.base/"benchmark.json"; jwrite(report,d)
        return report,d

    def test_wrong_benchmark_winner_is_rejected(self):
        report,d=self.benchmark(); gate={"report":{"artifact":report.name,"sha256":sha256(report)}}
        self.assertFalse(_gate_report(self.base,gate,"benchmark"))
        d["winner"]="B"; jwrite(report,d); gate["report"]["sha256"]=sha256(report)
        self.assertTrue(_gate_report(self.base,gate,"benchmark"))

    def test_benchmark_objective_gap_mean_and_direction_reproduce(self):
        report,d=self.benchmark()
        for key,value in (("direction","maximize"),("gap",0),("method_means",{"A":100,"B":1})):
            wrong=copy.deepcopy(d); wrong[key]=value; jwrite(report,wrong)
            self.assertTrue(_gate_report(self.base,{"report":{"artifact":report.name,"sha256":sha256(report)}},"benchmark"))

    def test_untriggered_benchmark_creates_no_experiment_obligation(self):
        q=make_efficient(self.base); self.assertFalse(audit_scientific(q))
        self.assertEqual(summarize_benchmark({"triggered":False},[])["status"],"NOT_TRIGGERED")

    def test_arithmetic_gap_is_not_bound_validity(self):
        q=self.question(); p=q/"bound.json"
        jwrite(p,{"status":"PASS","direction":"minimize","bound":0,"achieved_value":2,"gap":2,"gap_tolerance":0,"tolerance_basis":"exact","evaluator":hashed(q/"solver.py","evaluate"),"result_ids":["R1"]})
        self.assertTrue(_gate_report(q,{"report":{"artifact":p.name,"sha256":sha256(p)}},"bound_gap"))

    def test_global_optimum_required_by_task_not_just_claim_keywords(self):
        q=self.question(); contract=load_json(q/"question_contract.json")
        contract["required_outputs"][0]["description"]="globally minimizing solution"
        jwrite(q/"question_contract.json",contract)
        self.assertIn("claims require bound_gap",audit_conditional_gates(q/"conditional_gates.json",q/"claim_evidence_map.csv"))

    def test_valid_bound_with_positive_gap_cannot_certify_exact_optimum(self):
        q=self.question(); p=q/"bound.json"; note=hashed(q/"domain_note.md","[D1]")
        d={"status":"PASS","direction":"minimize","bound":0,"achieved_value":2,"gap":2,"gap_tolerance":1000000,"tolerance_basis":"deliberate giant fake optimum tolerance","evaluator":hashed(q/"solver.py","evaluate"),"result_ids":["R1"],
           "bound_certificate":{"kind":"REVIEWED_PROOF","derivation":note,"feasible_set_relation":note,"review_evidence":note,"reviewer":"gate fixture","reasoning":"Only bound validity is tested, not optimality.","scope":"bound","limitations":"No optimum proof."}}
        jwrite(p,d); gate={"report":{"artifact":p.name,"sha256":sha256(p)}}
        self.assertTrue(any("positive valid gap" in x for x in _gate_report(q,gate,"bound_gap",True)))
        d.update(bound=2,gap=0,gap_tolerance=0); jwrite(p,d); gate["report"]["sha256"]=sha256(p)
        self.assertFalse(_gate_report(q,gate,"bound_gap",True))

    def test_required_visual_cannot_be_closed_by_descriptive_claim(self):
        q=make_efficient(self.base); contract=load_json(q/"question_contract.json")
        contract["required_outputs"][0]["evidence_type"]="VISUAL"
        jwrite(q/"question_contract.json",contract); self.assertEqual(freeze_scientific(q),0)
        acceptance_review(q)
        self.assertTrue(any("required scientific visual" in x for x in audit_research(q)))

    def test_blank_figure_and_blank_final_size_preview_rejected(self):
        q=self.question(); image=q/"blank.png"; write_png(image,ink=False)
        vr=q/"visual_review.json"; jwrite(vr,{"image_sha256":sha256(image),"outcome":"ACCEPTED","reviewer":"deliberately false fixture","inspection_scope":"DIRECT_IMAGE_AND_FINAL_SIZE","final_width_mm":160,"final_size_preview":image.name+"@"+sha256(image),"checks":{k:{"outcome":"ACCEPTED","observation":"Actually blank; assertion deliberately false"} for k in ("scientific_encoding","source_fidelity","axes_units","legibility","legend_color","panel_caption","claim_support")}})
        row={"figure_id":"F1","question_id":"q1","role":"PRIMARY_RESULT","research_question":"What value?","message":"scalar value","status":"DELIVERED","data_source":"result:R1","data_identity":"REAL_DERIVED","demo_quarantine":"REAL_DATA","preferred_chart_type":"line","importance":"HIGH","output_path":image.name,"output_sha256":sha256(image),"caption_locator":hashed(q/"paper.md","[CAP]"),"paper_locator":"paper.md#[CAP]","plot_code":"solver.py@"+sha256(q/"solver.py"),"visual_review":vr.name+"@"+sha256(vr)}
        cwrite(q/"figure_candidates.csv",headers("figure_candidates.csv"),[row])
        self.assertTrue(any("blank" in x for x in audit_figures(q/"figure_candidates.csv","theoretical",q/"result_registry.json")[1]))

    def test_ablation_table_without_controlled_design_is_rejected(self):
        q=self.question(); p=q/"ablation.json"
        jwrite(p,{"status":"PASS","components":["A","B"],"shared_evaluator":"evaluate","result_ids":["R1"],"conclusion":"causal improvement","boundary":"same task"})
        self.assertTrue(_gate_report(q,{"report":{"artifact":p.name,"sha256":sha256(p)}},"ablation"))

    def test_declined_visual_candidate_needs_no_data_or_generation(self):
        q=self.question()
        cwrite(q/"figure_candidates.csv",headers("figure_candidates.csv"),[{"figure_id":"F1","role":"SENSITIVITY","research_question":"Would a sensitivity plot add evidence for exact scalar?","status":"DECLINED","status_reason":"No uncertain parameter or interpretable response dimension in this exact task."}])
        self.assertEqual(audit_figures(q/"figure_candidates.csv","theoretical",q/"result_registry.json")[0],"PASS")

    def test_declining_indispensable_mechanism_does_not_close_visual_gate(self):
        q=self.question()
        cwrite(q/"figure_candidates.csv",headers("figure_candidates.csv"),[{"figure_id":"F1","role":"MECHANISM","research_question":"How does physical coupling work?","status":"DECLINED","status_reason":"Quota saving"}])
        self.assertEqual(audit_figures(q/"figure_candidates.csv","physical",q/"result_registry.json")[0],"FAIL")

    def test_result_centered_scan_excludes_management_files(self):
        q=make_efficient(self.base); files=evidence_scan_candidates(q,q/"scan.csv")
        files={x.resolve() for x in files}
        self.assertIn((q/"proof.json").resolve(),files); self.assertIn((q/"substitution_check.py").resolve(),files)
        self.assertNotIn((q/"content_units.csv").resolve(),files); self.assertNotIn((q/"question_plan.json").resolve(),files)
        self.assertNotIn((q/"quality_assessment.json").resolve(),files)

    def test_sections_years_formula_constants_not_research_results(self):
        text="2025年全国大学生数学建模竞赛\n1.2 模型建立\n图 3 给出机制\n公式 x = 2 y\n结果为 2"
        self.assertEqual(scientific_numeric_tokens(text),["2"])
        self.assertIn("2025",scientific_numeric_tokens("参数估计结果为2025"))

    def test_paper_wording_does_not_invalidate_scientific_results(self):
        q=make_efficient(self.base); self.assertEqual(freeze_scientific(q),0)
        original=sha256(q/"scientific_manifest.json")
        (q/"paper.md").write_text("[P] Wording polish only; the result remains 2.\n")
        impact=affected_by_change(q,["paper.md"])
        self.assertFalse(impact["scientific_invalidated"])
        self.assertFalse(audit_scientific(q,1)); self.assertEqual(freeze_scientific(q),0)
        self.assertEqual(sha256(q/"scientific_manifest.json"),original)

    def test_model_evaluator_and_raw_source_changes_mark_affected_results(self):
        q=make_efficient(self.base)
        for change in ("model_contract.json","solver.py","proof.json","substitution_check.py"):
            impact=affected_by_change(q,[change])
            self.assertTrue(impact["scientific_invalidated"],change)
            self.assertIn("R1",impact["result_ids"]); self.assertIn("C1",impact["claim_ids"])

    def test_adaptive_domain_and_missing_activated_checks(self):
        q=make_efficient(self.base); self.assertFalse(audit_domain_map(q/"domain_model_map.json"))
        d=load_json(q/"domain_model_map.json"); d["checks"].pop(); jwrite(q/"domain_model_map.json",d)
        self.assertTrue(audit_domain_map(q/"domain_model_map.json"))

    def test_statistical_inference_not_forced_through_ml_split(self):
        q=self.question(); d=load_json(q/"model_contract.json")
        d.update(model_type="statistical",data_generating_process="iid conditional observations",observation_unit="unit",identification_assumptions="known conditional mean",dependence_structure="iid under stated sampling",uncertainty_method="exact supplied-noise distribution")
        jwrite(q/"model_contract.json",d); self.assertFalse(audit_model_contract(q/"model_contract.json"))
        d.pop("identification_assumptions"); jwrite(q/"model_contract.json",d)
        self.assertTrue(audit_model_contract(q/"model_contract.json"))

    def test_new_init_creates_only_current_stage_artifacts(self):
        q=self.base/"new"; init_question(q,"q1",PROFILE)
        self.assertEqual(len(list(q.glob("*"))),6)
        self.assertFalse((q/"reviews").exists()); self.assertFalse((q/"research_manifest.json").exists())
        activate_domain(q,["statistical"])
        self.assertEqual(len(load_json(q/"domain_model_map.json")["checks"]),6)
        prepare_stage(q,"solve"); self.assertTrue((q/"result_registry.json").exists())

    def test_depth_routes_differ_without_quantities(self):
        plans=[]
        for depth in ("L1","L2","L3"):
            file=self.base/(depth+".json"); route_depth(file,depth); plans.append(load_json(file)["depth_effects"])
        self.assertEqual(len({json.dumps(x,sort_keys=True) for x in plans}),3)

    def test_lean_acceptance_cannot_bypass_science_or_actual_text(self):
        q=make_efficient(self.base); self.assertEqual(freeze_scientific(q),0)
        acceptance_review(q); self.assertFalse(audit_research(q))
        self.assertEqual(freeze_research(q),0)
        self.assertEqual(set(load_json(q/"research_manifest.json")["artifacts"]),set(ACCEPTANCE_NAMES))
        review=load_json(q/"research_review.json"); review["artifacts_inspected"]=[]; jwrite(q/"research_review.json",review)
        self.assertTrue(audit_research(q))
        registry=load_json(q/"result_registry.json"); registry["results"][0]["raw_value"]=999; jwrite(q/"result_registry.json",registry)
        self.assertNotEqual(freeze_research(q),0)

    def test_formal_figure_without_real_source_and_visual_inspection_fails(self):
        q=self.question(); row={"figure_id":"F1","question_id":"q1","role":"PRIMARY_RESULT","research_question":"What is the result?","message":"the computed value","status":"DELIVERED","data_source":"missing.csv","data_identity":"REAL_DERIVED","demo_quarantine":"REAL_DATA","preferred_chart_type":"line","importance":"HIGH"}
        cwrite(q/"figure_candidates.csv",headers("figure_candidates.csv"),[row]); _,issues=audit_figures(q/"figure_candidates.csv","theoretical",q/"result_registry.json")
        self.assertTrue(any("data source" in x for x in issues)); self.assertTrue(any("visual inspection" in x for x in issues))

    def test_whole_visual_inventory_waits_for_all_main_texts(self):
        jwrite(self.base/"whole_problem_map.json",{"questions":[{"question_id":"q1","path":"q1"}]})
        jwrite(self.base/"project_state.json",{"questions":{"q1":{"status":"SOLVING"}}})
        jwrite(self.base/"page_budget.json",{"status":"UNSET"}); (self.base/"q1").mkdir()
        self.assertFalse(build_inventory(self.base)["trigger_ready"])
        jwrite(self.base/"project_state.json",{"questions":{"q1":{"status":"DRAFTED"}}})
        self.assertTrue(build_inventory(self.base)["trigger_ready"])

    def test_annual_delivery_unverified_or_wrong_year_rejected(self):
        p=self.base/"rules.json"; jwrite(p,{"status":"UNSET"})
        self.assertTrue(audit_delivery(p,self.base/"paper.docx"))
        jwrite(p,{"status":"VERIFIED","competition_year":2025,"verified_for_year":2026,"checked_at":"2026-10-09","rules":{},"sources":[]})
        issues=audit_delivery(p,self.base/"paper.docx")
        self.assertTrue(any("year" in x for x in issues)); self.assertTrue(any("AI" in x for x in issues))

    def test_delivery_layout_page_limit_and_ai_support_checks(self):
        # These generated OOXML/rule records test deterministic checks only.
        # They are not official-source verification, rendering or human review.
        note=self.base/"review.txt"; note.write_text("[CHECK] Controlled rule/format fixture; not an actual contest approval.")
        anchor=hashed(note,"[CHECK]"); paper=self.base/"paper.docx"
        def doc(margin):
            with zipfile.ZipFile(paper,"w") as z:
                z.writestr("[Content_Types].xml","<Types/>")
                z.writestr("word/document.xml",'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Anonymous fixture</w:t></w:r></w:p><w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="'+str(margin)+'" w:bottom="'+str(margin)+'" w:left="'+str(margin)+'" w:right="'+str(margin)+'"/></w:sectPr></w:body></w:document>')
        doc(1418)
        d={"status":"VERIFIED","competition_year":2026,"verified_for_year":2026,"checked_at":"2026-10-09",
           "sources":[{"kind":kind,"year":2026,"url":"https://www.mcm.edu.cn/fixture-not-a-source","binding":anchor} for kind in ("FORMAT","PARTICIPATION","AI")],
           "rule_interpretation":{"reviewer":"STRUCTURAL_FIXTURE","reasoning":"Only machine format behavior is tested.","evidence":anchor},
           "rules":{"allowed_paper_suffixes":[".docx"],"max_paper_bytes":20000000,"layout":{"page_twips":[11906,16838],"minimum_margin_twips":1417},"main_text_page_limit":30,"allowed_support_suffixes":[".zip"],"max_support_bytes":20000000,"ai_detail_filename":"AI工具使用详情.pdf"},
           "actual_page_counts":{"main_text":1},"page_count_evidence":"review.txt@"+sha256(note),
           "anonymous_review":anchor,"reference_review":anchor,"electronic_structure_review":anchor,"support_inventory_review":anchor,"support_required":False,"ai_used":False,"ai_declaration_evidence":anchor}
        profile=self.base/"rules.json"; jwrite(profile,d)
        self.assertFalse(audit_delivery(profile,paper))
        doc(1000); self.assertTrue(any("margins" in x for x in audit_delivery(profile,paper)))
        doc(1418); d["actual_page_counts"]["main_text"]=31; jwrite(profile,d)
        self.assertTrue(any("page limit" in x for x in audit_delivery(profile,paper)))
        d["actual_page_counts"]["main_text"]=1; d["ai_used"]=True; d["support_required"]=True
        archive=self.base/"support.zip"
        with zipfile.ZipFile(archive,"w") as z: z.writestr("solve.py","print(1)")
        d["support_artifact"]=archive.name; jwrite(profile,d)
        issues=audit_delivery(profile,paper)
        self.assertTrue(any("AI-detail PDF missing" in x for x in issues)); self.assertTrue(any("human verification" in x for x in issues))

    def test_numeric_bindings_derive_only_unambiguous_result_values(self):
        from sync_paper_numeric_map import derive
        q=self.question(); paper=q/"paper.md"; paper.write_text("1.2 Results\n2025年全国大学生数学建模竞赛\nThe result is 2.")
        rows,unresolved=derive(paper,[q]); self.assertEqual(len(rows),1); self.assertFalse(unresolved)
        registry=load_json(q/"result_registry.json"); registry["results"].append({**registry["results"][0],"result_id":"R2"}); jwrite(q/"result_registry.json",registry)
        rows,unresolved=derive(paper,[q]); self.assertFalse(rows); self.assertTrue(unresolved)

    def test_register_result_reads_raw_and_display_automatically(self):
        q=self.question(); empty=q/"automatic_registry.json"; jwrite(empty,{"results":[]})
        proc=subprocess.run([sys.executable,str(ROOT/"scripts/register_result.py"),str(empty),"--id","AUTO","--meaning","scalar","--unit","1","--source-type","analytical","--artifact","proof.json","--pointer","/theorems/THM1/value","--required-output","x","--scientific-version","1","--verification-artifact",str(q/"verify.json")],capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
        self.assertEqual(load_json(empty)["results"][0]["raw_value"],2); self.assertFalse(audit_result_registry(empty))

    def test_failed_benchmark_runs_are_not_silently_discarded(self):
        _,report=self.benchmark(); runs=report["runs"]+[{"method":"B","score":10000,"feasible":False}]
        self.assertEqual(summarize_benchmark(report["protocol"],runs)["status"],"UNRESOLVED_FAILED_RUNS")

    def test_malformed_cli_returns_failure_not_traceback(self):
        p=self.base/"bad.json"; p.write_text("{bad")
        r=subprocess.run([sys.executable,str(ROOT/"scripts/cqex.py"),"audit-page-budget",str(p)],capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0); self.assertNotIn("Traceback",r.stdout+r.stderr)


if __name__=="__main__": unittest.main(verbosity=2)
