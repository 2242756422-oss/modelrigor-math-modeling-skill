#!/usr/bin/env python3
from __future__ import annotations
import sys; sys.dont_write_bytecode=True
import csv, json, shutil, subprocess, tempfile, zipfile, struct, zlib
from pathlib import Path

from core import (QUALITY, REVIEWERS, REVIEW_SCOPE, SCIENTIFIC_NAMES, audit_claims,
                  audit_conditional_gates, audit_content, audit_domain_map,
                  audit_evidence_promotion, audit_figures, audit_manifest_bindings,
                  audit_model_contract, audit_page_budget, audit_page_qa,
                  audit_paper, audit_paper_numeric_map, audit_research,
                  audit_resource_consumption, audit_result_registry,
                  audit_reviewers, audit_scientific, audit_visual_semantics,
                  audit_whole_problem_map, derived_content_requirements, sha256,
                  summarize_benchmark)
from cqex import audit_whole, freeze_research, freeze_scientific, init_project, init_question, route_depth
from record_run import record_run

ROOT=Path(__file__).resolve().parents[1]; T=ROOT/"templates"; passed=[]
def jwrite(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def cwrite(p,headers,rows):
    with p.open("w",encoding="utf-8",newline="") as f: w=csv.DictWriter(f,fieldnames=headers); w.writeheader(); w.writerows(rows)
def headers(name):
    with (T/name).open(encoding="utf-8",newline="") as f:return next(csv.reader(f))
def check(name,cond):
    if not cond: raise AssertionError(name)
    passed.append(name)
def hashed(path,fragment): return f"{path.name}#{fragment}@{sha256(path)}"


def reviewer(base:Path,role:str,source:Path,run:str)->dict:
    rel="../"+source.name; loc=f"{rel}#[P]@{sha256(source)}"
    provenance=base/(run+"-provenance.md"); provenance.write_text(f"[RUN] Independent {role} attack using {run}.\n",encoding="utf-8")
    distinct={"DOMAIN_EXPERT":"mechanism, boundary and failure-mode closure checked","MATHEMATICAL_MODELING_REVIEWER":"quantifiers, evaluator and truth bindings reproduced","COMPETITION_JUDGE":"content sufficiency and peer-gap claims attacked","SCIENTIFIC_FIGURE_EDITOR":"visual necessity, semantics and evidence identity inspected","ADVERSARIAL_REVIEWER":"stale hashes, dangling references and false-PASS paths probed"}[role]
    return {"schema_version":"5.0","role":role,"run_id":run,"agent_instance_id":"agent-"+role.lower(),"attack_method":"attack-"+role.lower(),"run_provenance":hashed(provenance,"[RUN]"),"independent":True,"input_hashes":{rel:sha256(source),provenance.name:sha256(provenance)},"artifacts_read":[rel,provenance.name],"artifact_hashes_verified":True,"findings":[{"finding_id":run+"-F1","severity":"CLEAR","statement":distinct,"evidence_locator":hashed(provenance,"[RUN]"),"disposition":"RESOLVED"}],"quality_conclusions":{x:"PASS" for x in REVIEW_SCOPE[role]},"review_scope":sorted(REVIEW_SCOPE[role]),"created_at":"2026-01-01T00:00:00Z","overall":"PASS"}


def build_valid_question(base:Path)->Path:
    q=base/"q1"
    if q.exists(): shutil.rmtree(q)
    init_question(q,"q1")
    task=q/"task.md"; task.write_text("[TASK] Given a, compute x=a+1 for every supplied a.\n",encoding="utf-8")
    paper=q/"paper.md"; paper.write_text("[P] For every supplied a, x=a+1. The reported result is 2.\n[CAP] Exact relation shown algebraically.\n",encoding="utf-8")
    solver=q/"solver.py"; solver.write_text("def evaluate(a): return a+1\n",encoding="utf-8")
    proof=q/"proof.json"; jwrite(proof,{"theorems":{"THM1":{"value":2}}})
    verifier=q/"substitution_check.py"
    verifier.write_text('import json\na=1\nx=a+1\nwith open("verification_output.json","w") as f: json.dump({"observed_value":x,"checks":[{"purpose":"exact substitution for the supplied scalar","relation":"exact","actual":x,"expected":2}]},f)\n',encoding="utf-8")
    run_path=q/"verification_run.json"
    record_run(q,[sys.executable,str(verifier)],[verifier.name],[],["verification_output.json"],run_path)
    verify=q/"verify.json"; jwrite(verify,{"status":"PASS","kind":"EXECUTED_CHECK","method":"substitution recomputation (not independent proof)","observed_value":2,"scientific_version":1,"run_receipt":run_path.name+"@"+sha256(run_path),"output_artifact":"verification_output.json","observed_pointer":"/observed_value","independent":False})
    note=q/"domain_note.md"; note.write_text("[D1] For the supplied a=1, x=a+1 gives x=2 uniquely. The equality defines x, with finite dimensionless a; no approximation or optimizer is needed. This elementary derivation does not establish unrelated physical models.\n",encoding="utf-8")
    verified=json.loads(verify.read_text())
    verified['argument_check']={'kind':'REVIEWED_ARGUMENT','observed_value':2,'argument':hashed(note,'[D1]'),'review_evidence':hashed(note,'[D1]'),
        'substantive_review':{'outcome':'ACCEPTED','reviewer':'elementary gate-test derivation, not an independent theorem certification','reasoning':'Substitute a=1 into the explicit affine equality: 1+1=2, unique x.','scope':'defined scalar affine task','limitations':'No evidence for general physical/statistical modeling.'}}
    jwrite(verify,verified)
    dr=q/"domain_review.json"; jwrite(dr,{"schema_version":"5.0","role":"DOMAIN_EXPERT","run_id":"domain-pre-1","agent_instance_id":"agent-domain-pre","attack_method":"domain-ladder-and-omission-attack","run_provenance":hashed(note,"[D1]"),"independent":True,"input_hashes":{"domain_note.md":sha256(note)},"artifacts_read":["domain_note.md"],"artifact_hashes_verified":True,"findings":[{"finding_id":"D-F1","severity":"CLEAR","statement":"Domain closure is sufficient.","evidence_locator":hashed(note,"[D1]"),"disposition":"RESOLVED"}],"quality_conclusions":{"DOMAIN_PROFESSIONALISM":"PASS"},"review_scope":["DOMAIN_PROFESSIONALISM"],"created_at":"2026-01-01T00:00:00Z","overall":"PASS"})
    qc=json.loads((T/"question_contract.json").read_text()); qc.update({"question_id":"q1","task_text_locator":hashed(task,"[TASK]"),"required_outputs":[{"output_id":"x","description":"computed scalar","evidence_type":"result","unit":"1"}],"inputs":[{"id":"a","unit":"1"}],"decision_or_unknowns":["x"],"acceptance_evaluator":{"definition":"exact equality","inputs":["a"],"outputs":["x"],"aggregation_quantifiers":[{"variable":"a","domain":"supplied inputs","quantifier":"FOR_ALL","aggregation":"ALL_PASS"}],"direction":"NOT_APPLICABLE"},"status":"PASS"}); jwrite(q/"question_contract.json",qc)
    dm=json.loads((T/"domain_model_map.json").read_text()); dm.update({"question_id":"q1","domain_family":"theoretical","domain_objects":["real scalar"],"model_ladder":["exact scalar equality"],"ladder_rationale":"One exact layer closes the task without approximation.","literature_grounding":{"status":"NOT_APPLICABLE","reason":"self-contained elementary equality"},"review_status":"PASS","domain_review":{"role":"DOMAIN_EXPERT","run_id":"domain-pre-1","independent":True,"input_hashes":{"domain_note.md":sha256(note)},"artifacts_read":["domain_note.md"],"report_artifact":"domain_review.json","report_sha256":sha256(dr)}})
    for a in dm["answers"]: a["answer"]=f"case-specific answer {a['id']}"; a["evidence_locators"]=[hashed(note,"[D1]")]
    jwrite(q/"domain_model_map.json",dm)
    quant=[{"variable":"a","domain":"supplied inputs","quantifier":"FOR_ALL","aggregation":"ALL_PASS"}]
    mc=json.loads((T/"model_contract.json").read_text()); mc.update({"question_id":"q1","model_type":"direct_calculation","mathematical_objects":["x,a in R"],"index_domains":["supplied inputs"],"inputs":[{"id":"a","unit":"1"}],"outputs":[{"id":"x","unit":"1"}],"variables":[{"name":"x","meaning":"computed value","unit":"1"}],"parameters":[{"name":"a","meaning":"supplied value","unit":"1"}],"governing_relations":["x=a+1"],"quantifiers":quant,"constraints":["a is finite"],"evaluator":{"definition":"exact equality","artifact":"solver.py","artifact_sha256":sha256(solver),"version":"1","scientific_version":1,"inputs":["a"],"outputs":["x"],"aggregation_quantifiers":quant,"direction":"NOT_APPLICABLE","numerical_interface":"evaluate(a)"},"identifiability":"unique by equality","failure_modes":["non-finite a"],"closure_explanations":{"initial_boundary_conditions":"NOT_APPLICABLE_ALGEBRAIC","objective":"NOT_APPLICABLE_ALGEBRAIC"},"assumption_closure_reason":"All conditions are explicit in the exact equality.","status":"PASS"}); jwrite(q/"model_contract.json",mc)
    ub=json.loads((T/"uncertainty_budget.json").read_text())
    for rec in ub["categories"]: rec.update({"status":"NOT_APPLICABLE","risk":"Exact scalar case; category does not enter this task.","impact":"none","verification":[]})
    ub["categories"][1].update({"status":"ASSESSED","risk":"algebra transcription","impact":"wrong scalar","verification":[hashed(verify,'"status": "PASS"')]}); ub["dominant_risks"]=[{"category":"model_form"}]; jwrite(q/"uncertainty_budget.json",ub)
    rr={"schema_version":"5.0","results":[{"result_id":"R1","meaning":"computed scalar","unit":"1","raw_value":2,"display_value":"2","display_tolerance":0,"source_tolerance":0,"source":{"type":"analytical","artifact":"proof.json","pointer":"/theorems/THM1/value"},"artifact_sha256":sha256(proof),"scientific_version":1,"required_output_ids":["x"],"verification":[{"id":"V1","artifact":"verify.json","sha256":sha256(verify),"status":"PASS"}],"approved":True}]}; jwrite(q/"result_registry.json",rr)
    claim={"claim_id":"C1","claim_text":"x equals 2 for the supplied case","claim_type":"result","required_output_ids":"x","paper_locator":"paper.md#[P]","paper_sha256":sha256(paper),"evidence_refs":"result:R1","scope":"supplied case","boundary":"finite scalar input","status":"PASS"}; cwrite(q/"claim_evidence_map.csv",headers("claim_evidence_map.csv"),[claim])
    gates=json.loads((T/"conditional_gates.json").read_text())
    for name in ("benchmark","bound_gap","alternative_formulation","ablation"): gates[name]["reason"]="No trigger in exact single-method scalar question."
    jwrite(q/"conditional_gates.json",gates)
    semantics=json.loads((T/"visual_semantics.json").read_text()); semantics["status"]="PASS"; semantics["accessibility"]["grayscale_checked"]=True; jwrite(q/"visual_semantics.json",semantics)
    req=derived_content_requirements(q); row={"unit_id":"U1","question_id":"q1","source_kind":"DERIVED","source_ids":";".join(req),"requirement":"cover all contract, domain, model, verification, and result interpretation units","importance":"P0","evidence_refs":"result:R1","paper_locator":"paper.md#[P]","paper_sha256":sha256(paper),"development":"concise exact derivation and boundary","promotion_decision":"KEEP","redundancy":"NO","status":"COVERED"}; cwrite(q/"content_units.csv",headers("content_units.csv"),[row])
    dev=json.loads((T/"competitive_development.json").read_text())
    for name in ("derivation_sufficiency","method_exposition","evidence_promotion","formula_architecture","table_architecture","result_interpretation","writing_quality"): dev[name]={"status":"NOT_APPLICABLE","reason":"Exact one-line analytical task needs no separate expansion.","evidence_locators":[]}
    dev["hero_figure_attempt"]={"status":"NOT_APPLICABLE","reason":"No spatial or multivariate mechanism benefits from a hero figure.","candidate_id":None}; dev["peer_gap"]={"status":"NOT_APPLICABLE","reason":"Elementary exact equality has no meaningful peer-method gap.","comparison_sources":[],"gaps":[],"disposition":[]}; jwrite(q/"competitive_development.json",dev)
    for role in REVIEWERS: jwrite(q/"reviews"/(role+".json"),reviewer(q/"reviews",role,paper,"run-"+role.lower()))
    qa=json.loads((T/"quality_assessment.json").read_text())
    role_for={dim:next(role for role in REVIEWERS if dim in REVIEW_SCOPE[role]) for dim in QUALITY}
    for dim in QUALITY: qa["dimensions"][dim]={"status":"PASS","evidence_locators":[hashed(paper,"[P]")],"reviewer_run_ids":["run-"+role_for[dim].lower()]}
    jwrite(q/"quality_assessment.json",qa)
    return q


def write_docx(path:Path,text="2"):
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("[Content_Types].xml","<Types/>"); z.writestr("word/document.xml",f'<w:document xmlns:w="x"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>')
def write_png(path:Path,w=1240,h=1754,ink=True):
    def chunk(name,data):
        return struct.pack(">I",len(data))+name+data+struct.pack(">I",zlib.crc32(name+data)&0xffffffff)
    rows=[]
    for y in range(h):
        row=bytearray(b"\xff\xff\xff"*w)
        if ink and h//3 <= y < h//3+24:
            start=w//6; end=5*w//6
            row[3*start:3*end]=b"\x20\x20\x20"*(end-start)
        rows.append(b"\x00"+bytes(row))
    raw=b"".join(rows)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b""))


def page_qa_record(root:Path,paper:Path,image:Path)->dict:
    checks={"clipping":"PASS","captions":"PASS","equations":"PASS","tables":"PASS","readability":"PASS","pagination":"PASS"}
    renderer=root/"renderer_manifest.json"
    jwrite(renderer,{"status":"PASS","input_docx_sha256":sha256(paper),"page_size":"A4","command":"test renderer exact invocation","tool_versions":{"renderer":"1.0"},"exit_code":0,"page_outputs":[{"page":1,"image":image.name,"sha256":sha256(image)}]})
    review=root/"page_review.json"
    jwrite(review,{"paper_sha256":sha256(paper),"page_count":1,"pages":[{"page":1,"image_sha256":sha256(image),"checks":checks,"manual_status":"PASS","evidence_note":"Page-specific inspection completed."}],"overall":"PASS","blocking_findings":[]})
    return {"status":"PASS","renderer":"test renderer","renderer_artifact":renderer.name,"renderer_sha256":sha256(renderer),"manual_review_artifact":review.name,"manual_review_sha256":sha256(review),"page_size":"A4","document_sha256":sha256(paper),"page_count":1,"pages":[{"page":1,"image":image.name,"sha256":sha256(image),"width_px":1240,"height_px":1754,"manual_status":"PASS","checks":checks}]}


def main():
  with tempfile.TemporaryDirectory() as td:
    d=Path(td)
    page=d/"page.json"; shutil.copy2(T/"page_budget.json",page); check("page_budget_initial_UNSET",not audit_page_budget(page))
    bad=json.loads(page.read_text()); bad["hard_page_compliance"].update({"status":"VERIFIED","total_page_limit":30,"official_rule_source":"missing.txt","competition_year":2026,"source_sha256":"0"*64,"locator":"RULE","verbatim_excerpt":"30 pages"}); jwrite(page,bad); check("verified_page_rule_missing_source_fails",bool(audit_page_budget(page)))
    bad=json.loads((T/"page_budget.json").read_text()); bad["total_page_limit"]=19; jwrite(page,bad); check("root_page_limit_cannot_bypass_UNSET",bool(audit_page_budget(page)))
    plan=d/"plan.json"; jwrite(plan,{"keep":"evidence","page_target":3,"figure_target":4,"table_target":2,"formula_target":8,"benchmark_required":True,"ablation_required":True}); route_depth(plan,"L3"); routed=json.loads(plan.read_text()); check("L3_no_page_figure_benchmark_and_preserves_evidence",routed["keep"]=="evidence" and not any(k in routed for k in ("page_target","figure_target","table_target","formula_target","benchmark_required","ablation_required")))
    proj=d/"project"; init_project(proj,"P"); check("whole_problem_initialization_complete",all((proj/x).exists() for x in ("whole_problem_map.json","project_state.json","page_budget.json","numbering_registry.json","symbol_registry.json","visual_semantics.json","figure_portfolio.csv","result_registry.json")))
    q=build_valid_question(d)
    check("complete_domain_map_passes_structure",not audit_domain_map(q/"domain_model_map.json"))
    dm=json.loads((q/"domain_model_map.json").read_text()); dm["answers"][0]["evidence_locators"]=["missing.md#x@"+"0"*64]; jwrite(q/"domain_model_map.json",dm); check("domain_nonexistent_locator_fails",bool(audit_domain_map(q/"domain_model_map.json"))); q=build_valid_question(d)
    check("direct_calculation_without_objective_passes",not audit_model_contract(q/"model_contract.json"))
    mc=json.loads((q/"model_contract.json").read_text()); mc["model_type"]="physical_engineering"; mc["initial_boundary_conditions"]=[]; mc["observation_operator"]=None; jwrite(q/"model_contract.json",mc); check("physical_model_missing_boundary_and_observation_fails",bool(audit_model_contract(q/"model_contract.json"))); q=build_valid_question(d)
    mc=json.loads((q/"model_contract.json").read_text()); mc["model_type"]="optimization"; mc["objective"]={"sense":"minimize","expression":"x","decision_variables":["x"]}; mc["constraints"]=[]; mc["feasibility_evaluator"]=None; jwrite(q/"model_contract.json",mc); check("optimization_missing_feasible_domain_fails",bool(audit_model_contract(q/"model_contract.json"))); q=build_valid_question(d)
    mc=json.loads((q/"model_contract.json").read_text()); mc["model_type"]="data_ml"; mc.update({"data_generating_process":"iid observations","observation_unit":"sample","split_protocol":"group split","leakage_controls":[],"generalization_target":"new group"}); jwrite(q/"model_contract.json",mc); check("data_ML_missing_leakage_control_fails",bool(audit_model_contract(q/"model_contract.json"))); q=build_valid_question(d)
    mc=json.loads((q/"model_contract.json").read_text()); mc["quantifiers"]=[{"variable":"a","domain":"supplied inputs","quantifier":"EXISTS","aggregation":"ANY_PASS"}]; jwrite(q/"model_contract.json",mc); check("contradictory_quantifier_fails_scientific",bool(audit_scientific(q))); q=build_valid_question(d)
    check("analytical_result_without_experiment_id_passes",not audit_result_registry(q/"result_registry.json",1))
    rr=json.loads((q/"result_registry.json").read_text()); rr["results"][0]["raw_value"]=999; jwrite(q/"result_registry.json",rr); check("analytical_wrong_value_fails",bool(audit_result_registry(q/"result_registry.json",1))); q=build_valid_question(d)
    rr=json.loads((q/"result_registry.json").read_text()); rr["results"][0]["approved"]=False; jwrite(q/"result_registry.json",rr); check("unapproved_result_fails",bool(audit_result_registry(q/"result_registry.json",1))); q=build_valid_question(d)
    jwrite(q/"result_registry.json",{"schema_version":"5.0","results":[]}); cwrite(q/"claim_evidence_map.csv",headers("claim_evidence_map.csv"),[]); check("empty_results_claims_fail_required_output",bool(audit_scientific(q))); q=build_valid_question(d)
    cp=q/"claim_evidence_map.csv"; rows=list(csv.DictReader(cp.open())); rows[0]["evidence_refs"]="file:missing.md#x@"+"0"*64; cwrite(cp,headers("claim_evidence_map.csv"),rows); check("dangling_claim_evidence_fails",bool(audit_claims(cp,q/"result_registry.json"))); q=build_valid_question(d)
    proto={"triggered":True,"metric":"score","direction":"minimize","tolerance":0.01,"tolerance_basis":"measurement resolution","minimum_repetitions":2,"stochastic":True,"fairness":{k:"SAME" for k in ("data","evaluator","feasible_set","budget","termination","metric","direction","hardware","parallelism")}}
    runs=[{"method":"A","score":1.0,"feasible":True},{"method":"A","score":1.01,"feasible":True},{"method":"B","score":1.005,"feasible":True},{"method":"B","score":1.006,"feasible":True}]; check("benchmark_below_tolerance_is_PRACTICAL_TIE",summarize_benchmark(proto,runs)["status"]=="PRACTICAL_TIE")
    badp=dict(proto); badp["direction"]="sideways"; check("benchmark_invalid_direction_fails",summarize_benchmark(badp,runs)["status"]=="INVALID_PROTOCOL")
    badp=dict(proto); badp["tolerance"]=-1; check("benchmark_negative_tolerance_fails",summarize_benchmark(badp,runs)["status"]=="INVALID_PROTOCOL")
    check("benchmark_aggregates_distinct_methods",set(summarize_benchmark(proto,runs)["leaders"])=={"A","B"})
    claims=list(csv.DictReader((q/"claim_evidence_map.csv").open())); claims[0]["claim_type"]="superiority"; claims[0]["claim_text"]="Our method is superior to baseline"; cwrite(q/"claim_evidence_map.csv",headers("claim_evidence_map.csv"),claims); check("superiority_claim_derives_benchmark_gate",bool(audit_conditional_gates(q/"conditional_gates.json",q/"claim_evidence_map.csv"))); q=build_valid_question(d)
    claims=list(csv.DictReader((q/"claim_evidence_map.csv").open())); claims[0]["claim_type"]="hybrid_contribution"; claims[0]["claim_text"]="Component contribution improves the hybrid model"; cwrite(q/"claim_evidence_map.csv",headers("claim_evidence_map.csv"),claims); check("hybrid_contribution_derives_ablation_gate",bool(audit_conditional_gates(q/"conditional_gates.json",q/"claim_evidence_map.csv"))); q=build_valid_question(d)
    claims=list(csv.DictReader((q/"claim_evidence_map.csv").open())); claims[0]["claim_type"]="optimality"; claims[0]["claim_text"]="The solution is optimal"; cwrite(q/"claim_evidence_map.csv",headers("claim_evidence_map.csv"),claims); check("optimality_claim_derives_bound_gap_gate",bool(audit_conditional_gates(q/"conditional_gates.json",q/"claim_evidence_map.csv"))); q=build_valid_question(d)
    gates=json.loads((q/"conditional_gates.json").read_text()); gates["benchmark"]={"triggered":True,"reason":"compare methods","evidence":["missing.json#x@"+"0"*64],"report":{"artifact":"missing.json","sha256":"0"*64}}; gates["candidate_methods"]=["A","B"]; jwrite(q/"conditional_gates.json",gates); check("triggered_benchmark_missing_artifact_fails",bool(audit_conditional_gates(q/"conditional_gates.json",q/"claim_evidence_map.csv"))); q=build_valid_question(d)
    check("simple_theory_zero_figures_passes",audit_figures(q/"figure_candidates.csv","theoretical",q/"result_registry.json")[0]=="PASS")
    check("physical_case_without_mechanism_fails",audit_figures(q/"figure_candidates.csv","physical",q/"result_registry.json")[0]=="FAIL")
    fh=headers("figure_candidates.csv"); cwrite(q/"figure_candidates.csv",fh,[{"figure_id":"F1","question_id":"q1","role":"INVALID","research_question":"why","message":"m","data_source":"missing.csv","data_source_sha256":"0"*64,"data_identity":"real","demo_quarantine":"REAL_DATA","preferred_chart_type":"line","figure_cost":"L","page_cost":"L","importance":"HIGH","status":"NOT_APPLICABLE","status_reason":"x","equivalent_expression":"","output_path":"","output_sha256":"","caption_locator":"","paper_locator":"","page_qa_ref":""}]); check("invalid_visual_role_and_source_fail",audit_figures(q/"figure_candidates.csv","theoretical",q/"result_registry.json")[0]=="FAIL"); q=build_valid_question(d)
    # Expanded chart vocabulary is permissive only; it creates no figure quota.
    # This tests media/schema bindings only, not the quality of a real forest plot.
    fig=q/"forest.png"; write_png(fig,w=1920,h=1280)
    plotter=q/"plot_fixture.py"
    plotter.write_text('import sys,json\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(ROOT/"scripts"))+')\nfrom run_semantic_regressions import write_png\njson.loads(Path("proof.json").read_text())\nwrite_png(Path("forest.png"),w=1920,h=1280)\n',encoding="utf-8")
    generated=q/"plot_run.json"
    record_run(q,[sys.executable,plotter.name],[plotter.name],["proof.json"],[fig.name],generated)
    vr=q/"visual_review.json"; jwrite(vr,{"image_sha256":sha256(fig),"outcome":"ACCEPTED","reviewer":"STRUCTURAL_FIXTURE_NOT_SCIENTIFIC_REVIEW","inspection_scope":"DIRECT_IMAGE_AND_FINAL_SIZE","final_width_mm":160,"final_size_preview":fig.name+"@"+sha256(fig),"checks":{k:{"outcome":"ACCEPTED","observation":"fixture field coverage only; not real visual QA"} for k in ("scientific_encoding","source_fidelity","axes_units","legibility","legend_color","panel_caption","claim_support")}})
    forest={k:"" for k in fh}; forest.update({"figure_id":"F-FOREST","question_id":"q1","role":"COMPARISON","research_question":"How do effect estimates compare with uncertainty?","message":"effect estimates and intervals","data_source":"result:R1","data_source_sha256":"","data_identity":"REAL_DERIVED","demo_quarantine":"REAL_DATA","preferred_chart_type":"forest","figure_cost":"M","page_cost":"M","importance":"MEDIUM","status":"DELIVERED","status_reason":"TASK_MATCH: forest plot directly encodes estimate and interval for this comparison task.","output_path":fig.name,"output_sha256":sha256(fig),"caption_locator":hashed(q/"paper.md","[CAP]"),"paper_locator":"paper.md#[CAP]","plot_code":plotter.name+"@"+sha256(plotter),"generation_receipt":generated.name+"@"+sha256(generated),"visual_review":vr.name+"@"+sha256(vr)}); cwrite(q/"figure_candidates.csv",fh,[forest]); check("expanded_chart_type_forest_accepted",audit_figures(q/"figure_candidates.csv","theoretical",q/"result_registry.json")[0]=="PASS")
    # The miner should surface additional strong opportunities for a physical model, but remain restrained for simple theory.
    q=build_valid_question(d); mc=json.loads((q/"model_contract.json").read_text()); mc["model_type"]="physical_engineering"; mc["initial_boundary_conditions"]=["x(0)=0"]; mc["observation_operator"]="direct scalar observation"; jwrite(q/"model_contract.json",mc); dm=json.loads((q/"domain_model_map.json").read_text()); dm["domain_family"]="physical_engineering"; jwrite(q/"domain_model_map.json",dm)
    vm=d/"visual-miner.json"; subprocess.run([sys.executable,str(ROOT/"scripts/mine_visual_opportunities.py"),str(q),"--out",str(vm)],check=True); roles={x["role"] for x in json.loads(vm.read_text())["candidates"]}; check("visual_miner_derives_model_validation_interpretation",{"MECHANISM","MODEL_STRUCTURE","PRIMARY_RESULT","VALIDATION","PHYSICAL_INTERPRETATION"}.issubset(roles))
    q=build_valid_question(d); vm2=d/"visual-miner-theory.json"; subprocess.run([sys.executable,str(ROOT/"scripts/mine_visual_opportunities.py"),str(q),"--out",str(vm2)],check=True); roles2={x["role"] for x in json.loads(vm2.read_text())["candidates"]}; check("visual_miner_simple_theory_no_mechanical_expansion",roles2=={"PRIMARY_RESULT","UNCERTAINTY"})
    q=build_valid_question(d)
    proof=q/"proof.json"; proof_data=json.loads(proof.read_text()); proof_data["theorems"]["THM2"]={"value":3}; jwrite(proof,proof_data)
    verify2=q/"verify2.json"; jwrite(verify2,{"status":"PASS","method":"independent substitution","observed_value":3,"scientific_version":1})
    rr=json.loads((q/"result_registry.json").read_text()); rr["results"].append({"result_id":"R2","meaning":"secondary scalar","unit":"1","raw_value":3,"display_value":"3","display_tolerance":0,"source_tolerance":0,"source":{"type":"analytical","artifact":"proof.json","pointer":"/theorems/THM2/value"},"artifact_sha256":sha256(proof),"scientific_version":1,"required_output_ids":["x"],"verification":[{"id":"V2","artifact":"verify2.json","sha256":sha256(verify2),"status":"PASS"}],"approved":True}); jwrite(q/"result_registry.json",rr)
    vm3=d/"visual-miner-multi-result.json"; subprocess.run([sys.executable,str(ROOT/"scripts/mine_visual_opportunities.py"),str(q),"--out",str(vm3)],check=True)
    cand3=json.loads(vm3.read_text())["candidates"]; pr_count=sum(1 for x in cand3 if x["role"]=="PRIMARY_RESULT"); roles3={x["role"] for x in cand3}; check("visual_miner_allows_multiple_distinct_result_views",pr_count>=2 and "COMPARISON" in roles3)
    q=build_valid_question(d)
    mc=json.loads((q/"model_contract.json").read_text()); mc["model_type"]="physical_engineering"; mc["parameters"]=[{"name":"p1","meaning":"m1","unit":"1"},{"name":"p2","meaning":"m2","unit":"1"},{"name":"p3","meaning":"m3","unit":"1"}]; mc["governing_relations"]=["r1","r2"]; mc["initial_boundary_conditions"]=["bc1"]; mc["observation_operator"]="obs"; jwrite(q/"model_contract.json",mc)
    dm=json.loads((q/"domain_model_map.json").read_text()); dm["domain_family"]="physical_engineering"; jwrite(q/"domain_model_map.json",dm)
    proof=q/"proof.json"; proof_data=json.loads(proof.read_text()); proof_data["theorems"]["THM2"]={"value":3}; proof_data["theorems"]["THM3"]={"value":4}; jwrite(proof,proof_data)
    verify2=q/"verify2.json"; jwrite(verify2,{"status":"PASS","method":"independent substitution","observed_value":3,"scientific_version":1})
    verify3=q/"verify3.json"; jwrite(verify3,{"status":"PASS","method":"independent substitution","observed_value":4,"scientific_version":1})
    rr=json.loads((q/"result_registry.json").read_text()); rr["results"].append({"result_id":"R2","meaning":"secondary scalar","unit":"1","raw_value":3,"display_value":"3","display_tolerance":0,"source_tolerance":0,"source":{"type":"analytical","artifact":"proof.json","pointer":"/theorems/THM2/value"},"artifact_sha256":sha256(proof),"scientific_version":1,"required_output_ids":["x"],"verification":[{"id":"V2","artifact":"verify2.json","sha256":sha256(verify2),"status":"PASS"}],"approved":True}); rr["results"].append({"result_id":"R3","meaning":"tertiary scalar","unit":"1","raw_value":4,"display_value":"4","display_tolerance":0,"source_tolerance":0,"source":{"type":"analytical","artifact":"proof.json","pointer":"/theorems/THM3/value"},"artifact_sha256":sha256(proof),"scientific_version":1,"required_output_ids":["x"],"verification":[{"id":"V3","artifact":"verify3.json","sha256":sha256(verify3),"status":"PASS"}],"approved":True}); jwrite(q/"result_registry.json",rr)
    ub=json.loads((q/"uncertainty_budget.json").read_text()); ub["dominant_risks"]=[{"category":"model_form"},{"category":"parameter"}]; jwrite(q/"uncertainty_budget.json",ub)
    vm4=d/"visual-miner-complex.json"; subprocess.run([sys.executable,str(ROOT/"scripts/mine_visual_opportunities.py"),str(q),"--out",str(vm4)],check=True)
    cand4=json.loads(vm4.read_text())["candidates"]; roles4={x["role"] for x in cand4}; pr4=sum(1 for x in cand4 if x["role"]=="PRIMARY_RESULT"); check("visual_miner_complex_task_prefers_richer_nonredundant_portfolio", len(cand4)>=9 and pr4>=3 and {"MECHANISM","MODEL_STRUCTURE","DOMAIN_PROPERTY","COMPARISON","VALIDATION","PHYSICAL_INTERPRETATION","SENSITIVITY","UNCERTAINTY","ROBUSTNESS"}.issubset(roles4))
    q=build_valid_question(d)
    fig=q/"plot.png"; write_png(fig); monotony=[]
    for i,role in enumerate(("PRIMARY_RESULT","DIAGNOSTIC","UNCERTAINTY"),1): monotony.append({"figure_id":f"F{i}","question_id":"q1","role":role,"research_question":f"distinct task {i}","message":f"message {i}","data_source":"result:R1","data_source_sha256":"","data_identity":"REAL_DERIVED","demo_quarantine":"REAL_DATA","preferred_chart_type":"line","figure_cost":"M","page_cost":"M","importance":"HIGH","status":"DELIVERED","status_reason":"","equivalent_expression":"","output_path":"plot.png","output_sha256":sha256(fig),"caption_locator":hashed(q/"paper.md","[CAP]"),"paper_locator":"paper.md#[CAP]","page_qa_ref":""})
    cwrite(q/"figure_candidates.csv",fh,monotony); check("visual_monotony_detected",audit_figures(q/"figure_candidates.csv","theoretical",q/"result_registry.json")[0]=="FAIL"); q=build_valid_question(d)
    # Content cannot self-select a single low row.
    low={k:"" for k in headers("content_units.csv")}; low.update({"unit_id":"L","question_id":"q1","source_kind":"SELF","source_ids":"NONE","requirement":"minor","importance":"LOW","evidence_refs":"result:R1","paper_locator":"paper.md#[P]","paper_sha256":sha256(q/"paper.md"),"development":"minor","promotion_decision":"KEEP","redundancy":"NO","status":"COVERED"}); cwrite(q/"content_units.csv",headers("content_units.csv"),[low]); check("single_low_content_row_is_underdeveloped",audit_content(q/"content_units.csv",q)[0]=="UNDERDEVELOPED"); q=build_valid_question(d)
    check("content_appropriate_detected",audit_content(q/"content_units.csv",q)[0]=="APPROPRIATE")
    red={k:"" for k in headers("content_units.csv")}; red.update({"unit_id":"RED","question_id":"q1","source_kind":"EDITORIAL","source_ids":"RED","requirement":"generic repetition","importance":"LOW","development":"repeat","promotion_decision":"DROP","redundancy":"YES","status":"REDUNDANT"}); cwrite(q/"content_units.csv",headers("content_units.csv"),[red]); check("content_overdeveloped_detected",audit_content(q/"content_units.csv")[0]=="OVERDEVELOPED"); q=build_valid_question(d)
    rd=q/"reviews"; [p.unlink() for p in rd.glob("*.json")]
    for role in REVIEWERS:
        x=reviewer(rd,role,q/"paper.md","same"); x["findings"]=[]; jwrite(rd/(role+".json"),x)
    check("empty_or_copied_reviewer_reports_fail",bool(audit_reviewers(rd))); q=build_valid_question(d)
    # Resource use and evidence-promotion PASS states must resolve every artifact.
    resource=d/"ordinary.txt"; resource.write_text("ordinary\n",encoding="utf-8"); validation=d/"validation.md"; validation.write_text("[V] checked\n",encoding="utf-8")
    cwrite(q/"resource_consumption.csv",headers("resource_consumption.csv"),[{"capability_id":"fake","resource_kind":"PROJECT_CODE","resource_path":str(resource),"source_sha256":sha256(resource),"reason":"claim use","actual_interface":"none","input_bindings":"missing@"+"0"*64,"result_ids":"MISSING","output_bindings":"missing@"+"0"*64,"exit_code":"0","adaptations":"none","excluded_legacy_policies":"none","validation_evidence":f"{validation}#[V]@{sha256(validation)}","semantic_review_status":"PASS"}]); check("invented_resource_consumption_fails",bool(audit_resource_consumption(q/"resource_consumption.csv",q/"result_registry.json"))); q=build_valid_question(d)
    kept=q/"kept.json"; kept.write_text("{}\n",encoding="utf-8"); omitted=q/"omitted.csv"; omitted.write_text("x,y\n",encoding="utf-8")
    cwrite(q/"evidence_promotion.csv",headers("evidence_promotion.csv"),[{"evidence_id":"EV-1","artifact":"kept.json","locator":"sha256:"+sha256(kept),"claim_value":"minor","independence":"SELF","proposed_form":"text","page_cost":"low","decision":"KEEP_SUPPORTING","reason":"selected"}]); dev=json.loads((q/"competitive_development.json").read_text()); dev["evidence_promotion"]={"status":"PASS","reason":"scan","scanned_roots":["."],"decision_artifact":"evidence_promotion.csv"}; jwrite(q/"competitive_development.json",dev); check("incomplete_evidence_promotion_scan_fails",bool(audit_evidence_promotion(q/"evidence_promotion.csv",q/"competitive_development.json")))
    scan=d/"scan"; scan.mkdir(); (scan/"data.json").write_text("{}\n",encoding="utf-8"); inv=scan/"inventory.csv"; cmd=[sys.executable,str(ROOT/"scripts/scan_evidence.py"),str(scan),str(inv)]; subprocess.run(cmd,check=True,capture_output=True,text=True); subprocess.run(cmd,check=True,capture_output=True,text=True); scan_rows=list(csv.DictReader(inv.open())); check("evidence_scanner_excludes_its_output",all(r["artifact"]!="inventory.csv" for r in scan_rows))
    q=build_valid_question(d); sem=json.loads((q/"visual_semantics.json").read_text()); sem["semantics"]["observation"]["color"]="blue-ish"; jwrite(q/"visual_semantics.json",sem); check("garbage_visual_semantics_fail",bool(audit_visual_semantics(q/"visual_semantics.json"))); q=build_valid_question(d)
    check("scientific_freeze_valid_case_passes",freeze_scientific(q)==0)
    check("scientific_manifest_exact_set",not audit_manifest_bindings(q/"scientific_manifest.json",SCIENTIFIC_NAMES))
    v= json.loads((q/"scientific_manifest.json").read_text())["scientific_version"]; check("scientific_refreeze_unchanged_is_idempotent",freeze_scientific(q)==0 and json.loads((q/"scientific_manifest.json").read_text())["scientific_version"]==v)
    check("simple_theory_research_freeze_without_mechanical_expansion",freeze_research(q)==0 and not audit_research(q,True))
    # Tamper after freeze.
    with (q/"content_units.csv").open("a") as f:f.write("tamper")
    check("research_manifest_detects_postfreeze_change",bool(audit_research(q,True)))
    # Page QA rejects fake files and accepts a minimally valid hash-bound A4 record.
    fake=d/"fake.docx"; fake.write_bytes(b"fake"); img=d/"page.png"; write_png(img); qa=d/"qa.json"; jwrite(qa,{"paper_artifact":"fake.docx","paper_sha256":sha256(fake),"page_qa":page_qa_record(d,fake,img)}); check("fake_docx_page_QA_fails",bool(audit_page_qa(qa)))
    doc=d/"real.docx"; write_docx(doc); jwrite(qa,{"paper_artifact":"real.docx","paper_sha256":sha256(doc),"page_qa":page_qa_record(d,doc,img)}); check("hash_bound_A4_page_QA_passes",not audit_page_qa(qa)); doc.write_bytes(doc.read_bytes()+b"x"); check("word_page_QA_stales_after_document_change",bool(audit_page_qa(qa)))
    white=d/"white.png"; write_png(white,ink=False); doc2=d/"white.docx"; write_docx(doc2); jwrite(qa,{"paper_artifact":"white.docx","paper_sha256":sha256(doc2),"page_qa":page_qa_record(d,doc2,white)}); check("blank_page_image_fails_visual_QA",bool(audit_page_qa(qa)))
    # Whole-paper command binds all frozen questions, registries, page QA and can reopen development.
    wp=d/"whole"; init_project(wp,"WP"); wq=build_valid_question(wp); check("whole_scientific_freeze",freeze_scientific(wq)==0); check("whole_research_freeze",freeze_research(wq)==0)
    wdoc=wp/"paper.docx"; write_docx(wdoc,"The registered result is 2."); wimg=wp/"page-1.png"; write_png(wimg); wmanual=wp/"manual.md"; wmanual.write_text("[MODELS] Models checked.\n[ASSUMPTIONS] Assumptions checked.\n[SYMBOLS] Symbols checked.\n[CLAIMS] Claims checked.\n",encoding="utf-8")
    fragments={"models_evaluators":"[MODELS]","assumptions":"[ASSUMPTIONS]","symbols_units":"[SYMBOLS]","claims_results":"[CLAIMS]"}
    whole=json.loads((wp/"whole_problem_map.json").read_text()); whole.update({"questions":[{"question_id":"q1","path":"q1"}],"dependencies":[],"research_roles":{"q1":"theory core"},"evidence_priorities":{"q1":"exact result and independent verification"},"writing_priorities":{"q1":"concise derivation and boundary"},"consistency_checks":[{"category":name,"status":"PASS","evidence_locator":hashed(wmanual,fragments[name])} for name in fragments],"status":"PASS"}); jwrite(wp/"whole_problem_map.json",whole)
    cwrite(wp/"paper_numeric_map.csv",headers("paper_numeric_map.csv"),[{"paper_value_id":"PV1","paper_locator":"paper.docx#2","paper_sha256":sha256(wdoc),"displayed_value":"2","source_kind":"RESULT_REGISTRY","source_id":"R1","source_display_value":"2","source_evidence":"","status":"PASS"}])
    wa=json.loads((T/"whole_paper_audit.json").read_text()); wa.update({"paper_artifact":"paper.docx","paper_sha256":sha256(wdoc),"project_state":"project_state.json","question_dirs":["q1"],"paper_numeric_map":"paper_numeric_map.csv","scientific_consistency":"PASS","content_sufficiency":"APPROPRIATE","quality":{k:"PASS" for k in QUALITY},"status":"PENDING"}); wa["page_qa"]=page_qa_record(wp,wdoc,wimg); jwrite(wp/"whole_paper_audit.json",wa)
    check("whole_paper_audit_command_passes_valid_case",audit_whole(wp/"whole_paper_audit.json")==0)
    decoy=wp/"decoy.md"; decoy.write_text("[X] 2\n",encoding="utf-8"); cwrite(wp/"paper_numeric_map.csv",headers("paper_numeric_map.csv"),[{"paper_value_id":"PV1","paper_locator":"decoy.md#2","paper_sha256":sha256(decoy),"displayed_value":"2","source_kind":"RESULT_REGISTRY","source_id":"R1","source_display_value":"2","source_evidence":"","status":"PASS"}]); check("numeric_map_decoy_binding_fails",bool(audit_paper_numeric_map(wp/"paper_numeric_map.csv",wdoc,[wq])))
    write_docx(wdoc,"The result is 2 but 999 is unmapped."); cwrite(wp/"paper_numeric_map.csv",headers("paper_numeric_map.csv"),[{"paper_value_id":"PV1","paper_locator":"paper.docx#2","paper_sha256":sha256(wdoc),"displayed_value":"2","source_kind":"RESULT_REGISTRY","source_id":"R1","source_display_value":"2","source_evidence":"","status":"PASS"}]); check("unmapped_paper_number_fails",bool(audit_paper_numeric_map(wp/"paper_numeric_map.csv",wdoc,[wq])))
    write_docx(wdoc,"The registered result is 2."); cwrite(wp/"paper_numeric_map.csv",headers("paper_numeric_map.csv"),[{"paper_value_id":"PV1","paper_locator":"paper.docx#2","paper_sha256":sha256(wdoc),"displayed_value":"2","source_kind":"RESULT_REGISTRY","source_id":"R1","source_display_value":"2","source_evidence":"","status":"PASS"}]); wa=json.loads((wp/"whole_paper_audit.json").read_text()); wa["paper_sha256"]=sha256(wdoc); wa["page_qa"]=page_qa_record(wp,wdoc,wimg); jwrite(wp/"whole_paper_audit.json",wa)
    (wp/"numbering_registry.json").write_text("not json\n",encoding="utf-8"); check("whole_audit_rejects_malformed_global_registry",bool(audit_paper(wp/"whole_paper_audit.json"))); shutil.copy2(T/"numbering_registry.json",wp/"numbering_registry.json")
    whole=json.loads((wp/"whole_problem_map.json").read_text()); whole["questions"][0]["path"]="wrong"; jwrite(wp/"whole_problem_map.json",whole); check("whole_map_rejects_wrong_question_path",bool(audit_whole_problem_map(wp/"whole_problem_map.json",[wq]))); whole["questions"][0]["path"]="q1"; jwrite(wp/"whole_problem_map.json",whole)
    with (wq/"content_units.csv").open("a") as f: f.write("tamper")
    check("whole_paper_audit_detects_and_reopens_stale_research",audit_whole(wp/"whole_paper_audit.json",True)==1 and json.loads((wq/"research_manifest.json").read_text())["status"]=="REOPEN_FOR_DEVELOPMENT")
    stale=d/"stale"; init_project(stale,"S"); sq=build_valid_question(stale); state=json.loads((stale/"project_state.json").read_text()); state["questions"]={"q2":{"status":"RESEARCH_FROZEN"}}; state["dependencies"]=[{"from":"q1","to":"q2"}]; jwrite(stale/"project_state.json",state); check("scientific_version_change_propagates_downstream_STALE",freeze_scientific(sq)==0 and json.loads((stale/"project_state.json").read_text())["questions"]["q2"]["status"]=="STALE")
    hm=d/"handoff"; hm.mkdir(); draft={"schema_version":"5.0","question_id":"q1","status":"DRAFT","scientific_version":1,"created_at":None,"artifacts":{},"result_ids":[],"verification_ids":[],"upstream_scientific_versions":{}}; jwrite(hm/"scientific_manifest.json",draft); hand={"schema_version":"5.0","from_question":"q1","to_question":"q2","scientific_version":1,"scientific_manifest_sha256":sha256(hm/"scientific_manifest.json"),"objects":["x"],"symbols_units":{"x":"1"},"assumptions":[],"evaluator_contract":"e","status":"READY"}; jwrite(hm/"handoff.json",hand); proc=subprocess.run([sys.executable,str(ROOT/"scripts/check_handoff.py"),str(hm/"handoff.json")],capture_output=True,text=True); check("draft_manifest_handoff_fails",proc.returncode!=0)
    hp=d/"handoff_project"; init_project(hp,"H"); hq=build_valid_question(hp); check("handoff_source_scientific_freeze",freeze_scientific(hq)==0); sm=json.loads((hq/"scientific_manifest.json").read_text()); valid={"schema_version":"5.0","from_question":"q1","to_question":"q2","scientific_manifest":"scientific_manifest.json","scientific_version":sm["scientific_version"],"scientific_manifest_sha256":sha256(hq/"scientific_manifest.json"),"objects":["x"],"symbols_units":{"x":"1"},"assumptions":[],"evaluator_contract":hashed(hq/"solver.py","def evaluate"),"status":"READY"}; jwrite(hq/"handoff.json",valid); proc=subprocess.run([sys.executable,str(ROOT/"scripts/check_handoff.py"),str(hq/"handoff.json")],capture_output=True,text=True); check("semantic_handoff_valid_case_passes",proc.returncode==0); valid["objects"]=["ghost-object"]; jwrite(hq/"handoff.json",valid); proc=subprocess.run([sys.executable,str(ROOT/"scripts/check_handoff.py"),str(hq/"handoff.json")],capture_output=True,text=True); check("semantic_handoff_rejects_ghost_payload",proc.returncode!=0)
  print(f"SEMANTIC REGRESSIONS PASS ({len(passed)} cases)"); [print("-",x) for x in passed]


if __name__=="__main__": main()
