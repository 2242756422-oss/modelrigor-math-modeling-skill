#!/usr/bin/env python3
"""Derive high-value visual questions from existing model/evidence needs without a figure quota."""
import sys; sys.dont_write_bytecode=True
import argparse, json, hashlib
from pathlib import Path
from core import load_json

p=argparse.ArgumentParser(); p.add_argument("question_dir",type=Path); p.add_argument("--out",type=Path); p.add_argument("--selection",type=Path,help="One compact optional selection/merge plan, not one report per candidate"); a=p.parse_args(); q=a.question_dir

def read(name, default):
    path=q/name
    return load_json(path) if path.exists() else default

def _norm(s):
    return " ".join(str(s).split()).strip().lower()

def _approved_results(rows):
    return [r for r in rows if isinstance(r,dict) and r.get("approved")]

def _list_len(v):
    return len(v) if isinstance(v,list) else 0

def _param_count(model):
    return _list_len(model.get("parameters"))

def _governing_count(model):
    return _list_len(model.get("governing_relations"))

domain=read("domain_model_map.json",{})
model=read("model_contract.json",{})
results=read("result_registry.json",{}).get("results",[])
unc=read("uncertainty_budget.json",{})
gates=read("conditional_gates.json",{})
family=str(domain.get("domain_family","" )).lower()
model_type=str(model.get("model_type","" )).lower()
physical=family in ("physical","physics","engineering","physical_engineering") or model_type in ("physical","physics","engineering","physical_engineering")
data_ml=model_type in ("data_ml","ml","data","statistical","statistics","machine_learning") or any(model.get(k) for k in ("data_generating_process","split_protocol","generalization_target"))
optimization=model_type in ("optimization","operations_research","or","scheduling","routing") or bool(model.get("objective"))

c=[]
seen=set()
approved=_approved_results(results)
verified=[r for r in approved if r.get("verification")]
dominant=unc.get("dominant_risks") or []
complex_task=bool(model.get("couplings") or model.get("multiple_agents") or model.get("regime_structure")
                  or (_governing_count(model)>1 and _param_count(model)>1))

def add(role, question, trigger, suggested_chart_families=None, importance="HIGH"):
    key=(role,_norm(question),_norm(trigger))
    if key in seen: return
    seen.add(key)
    cid="VO-"+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:10]
    c.append({"candidate_id":cid,"role":role,"research_question":question,"trigger":trigger,"suggested_chart_families":suggested_chart_families or [],"importance":importance,"selection":"UNDECIDED","obligation":"NONE_UNTIL_SELECTED","information_lost_if_omitted":"TO_BE_JUDGED_AT_SELECTION"})

# Strong, model-derived opportunities. These are candidates, not quotas.
if physical:
    add("MECHANISM","How do domain objects, boundaries and governing relations interact?","physical/engineering mechanism should be inspectable",["schematic","geometry_schematic","multi_panel_composite"])
    if model.get("governing_relations") or model.get("observation_operator"):
        add("MODEL_STRUCTURE","How are governing relations, states/parameters and the observation/evaluation layer connected?","physical model contains explicit governing or observation structure",["schematic","workflow","multi_panel_composite"])
    if _param_count(model) >= 2 or _governing_count(model) >= 2:
        add("DOMAIN_PROPERTY","Which regime boundary, material property or structural factor organizes the observed behavior?","physical task includes multiple parameters or governing relations that create interpretable domain structure",["contour","surface","schematic","multi_panel_composite"],"MEDIUM")
if data_ml:
    add("DATA_STRUCTURE","What structure in the observations, split or feature space materially affects the model?","data/ML generating, split or generalization structure is explicit",["distribution","correlation_matrix","heatmap","scatter","multi_panel_composite"])
    if model.get("split_protocol") or model.get("generalization_target"):
        add("DIAGNOSTIC","Which split behavior, imbalance or feature-response pattern most affects reliability?","data/ML task exposes split/generalization structure that merits inspection",["distribution","correlation_matrix","residual","calibration","multi_panel_composite"],"MEDIUM")
    if complex_task:
        add("DATA_STRUCTURE","What compact panel best shows heterogeneity across groups, time slices or feature blocks?","data/ML task is complex enough that one structural view may hide important heterogeneity",["heatmap","distribution","scatter","multi_panel_composite"],"MEDIUM")
if optimization:
    add("OPTIMIZATION_PROCESS","How do decisions, feasibility and objective value evolve or trade off?","objective/feasible-domain structure is explicit",["convergence","objective_landscape","sensitivity_matrix","multi_panel_composite"])
    if model.get("objective") and model.get("constraints"):
        add("OBJECTIVE_LANDSCAPE","Where are the dominant trade-offs, active constraints or feasible-region bottlenecks?","optimization task has explicit objective and constraint structure",["objective_landscape","contour","surface","multi_panel_composite"],"MEDIUM")
    if complex_task:
        add("OPTIMIZATION_PROCESS","Which convergence, search-region or scenario-comparison view most explains why the chosen solution is credible?","optimization task is complex enough that a single process view may under-explain solution credibility",["convergence","objective_landscape","interval","multi_panel_composite"],"MEDIUM")
    if len(gates.get("candidate_methods",[]))>=2:
        add("ALGORITHM_ARCHITECTURE","What distinct roles do the competing or hybrid method components play?","multiple candidate methods are registered",["algorithm_architecture","workflow","multi_panel_composite"],"MEDIUM")
if approved:
    add("PRIMARY_RESULT","Which registered results answer the contract most directly?","approved Result Registry entries exist",["line","bar","dot","interval","map","surface","multi_panel_composite"])
    if len(approved) >= 2:
        add("COMPARISON","How do the main approved results differ across outputs, scenarios or regimes?","multiple approved Result Registry entries exist",["dot","interval","heatmap","line","multi_panel_composite"],"MEDIUM")
        add("PRIMARY_RESULT","What secondary result view reveals the key trade-off, regime split or scenario pattern?","multiple approved results suggest more than one reader-facing result question",["line","dot","heatmap","surface","map","multi_panel_composite"],"MEDIUM")
    if complex_task and (_param_count(model) >= 2 or len(approved) >= 3):
        add("PRIMARY_RESULT","What compact result matrix, map or multi-panel summary best reveals the joint pattern across variables, scenarios or regimes?","complex task likely has more than one indispensable result lens",["heatmap","contour","surface","map","multi_panel_composite"],"MEDIUM")
    if verified and (physical or data_ml or optimization):
        add("VALIDATION","What independent evidence shows the reported result survives the main verification route?","registered results carry verification records and the task is nontrivial enough for visual validation",["parity","residual","interval","distribution","convergence","multi_panel_composite"])
        if len(verified) >= 2:
            add("VALIDATION","Do multiple outputs or regimes remain consistent under independent checks?","multiple approved results carry verification records",["parity","residual","interval","distribution","multi_panel_composite"],"MEDIUM")
        if complex_task and (len(verified) >= 1 and len(dominant) >= 1):
            add("VALIDATION","Which visual check best shows agreement after accounting for the dominant uncertainty or perturbation source?","complex task has both formal verification and identified uncertainty",["parity","interval","distribution","multi_panel_composite"],"MEDIUM")
    if physical:
        add("PHYSICAL_INTERPRETATION","What mechanism explains the magnitude, trend or regime of the primary result?","physical result exists and should be interpreted through the domain model",["line","contour","surface","schematic","multi_panel_composite"],"MEDIUM")
        if len(approved) >= 2 or model.get("governing_relations"):
            add("PHYSICAL_INTERPRETATION","Where do regime changes, hotspots or dominant mechanisms appear in the result space?","physical task has multiple outputs/regimes or rich governing structure",["contour","surface","heatmap","schematic","multi_panel_composite"],"MEDIUM")
        if complex_task and _param_count(model) >= 2:
            add("PHYSICAL_INTERPRETATION","How do parameter interactions manifest as interpretable physical regions, fronts or transition zones?","complex physical task has enough parametric structure to merit a second interpretation lens",["contour","surface","heatmap","multi_panel_composite"],"MEDIUM")
if dominant:
    add("UNCERTAINTY","How does the dominant uncertainty change the claimed result?","dominant uncertainty recorded",["interval","errorbar","violin","tornado","sensitivity_matrix","multi_panel_composite"])
    if len(dominant) >= 2:
        add("ROBUSTNESS","Which conclusion remains stable across the main perturbation or scenario checks?","multiple dominant or tested uncertainty sources exist",["interval","tornado","sensitivity_matrix","multi_panel_composite"],"MEDIUM")
    if complex_task and len(dominant) >= 1:
        add("UNCERTAINTY","Which uncertainty summary best shows whether local variation and worst-case behavior tell the same story?","complex task benefits from separating average-risk and boundary-risk views",["interval","violin","tornado","multi_panel_composite"],"MEDIUM")
if _param_count(model) >= 2 and (physical or optimization or data_ml):
    add("SENSITIVITY","Which parameters most influence the result or decision?","multiple modeled parameters are present",["tornado","sensitivity_matrix","heatmap","contour","multi_panel_composite"],"MEDIUM")
    if complex_task and _param_count(model) >= 3:
        add("SENSITIVITY","What interaction view shows whether the leading parameters act independently or jointly?","complex task includes enough parameters that single-factor sensitivity may be incomplete",["sensitivity_matrix","contour","heatmap","multi_panel_composite"],"MEDIUM")

for gate,role,charts in (
    ("benchmark","BENCHMARK",["dot","forest","heatmap","multi_panel_composite"]),
    ("ablation","ABLATION",["bar","dot","heatmap","multi_panel_composite"]),
    ("bound_gap","BOUND_GAP",["interval","line","dot","multi_panel_composite"]),
    ("alternative_formulation","METHOD",["workflow","schematic","multi_panel_composite"]),
):
    if gates.get(gate,{}).get("triggered"):
        add(role,f"What evidence resolves the triggered {gate} claim?",f"{gate} gate triggered",charts)

if model.get("field_variables"):
    add("SPATIAL_TEMPORAL","Which computed field, slice or projection explains the governing mechanism?","field variables are explicitly modeled",["contour","surface","map","multi_panel_composite"])
if model.get("multi_objective"):
    add("DECISION_SUPPORT","Which nondominated trade-offs inform the actual decision?","multiple competing objectives are explicit",["scatter","parallel_coordinates","multi_panel_composite"])
if model.get("multiple_agents"):
    add("DECISION_SUPPORT","How do assignment, coordination and space/time interactions create the outcome?","multiple interacting decision makers",["network","interval","map","multi_panel_composite"])

if a.selection:
    decisions=load_json(a.selection).get("decisions",{})
    known={x["candidate_id"] for x in c}
    if set(decisions)-known: p.error("selection contains unknown candidate IDs")
    for candidate in c:
        choice=decisions.get(candidate["candidate_id"])
        if not choice: continue
        action=choice.get("action")
        if action not in ("SELECT","DECLINE","MERGE","DEFER") or not choice.get("reason"):
            p.error("selection requires a valid action and substantive reason")
        if action=="MERGE" and choice.get("into") not in known:
            p.error("merge target must be an existing candidate")
        candidate.update(selection=action,selection_reason=choice["reason"],merged_into=choice.get("into"),
                         information_lost_if_omitted=choice.get("information_lost_if_omitted", ""),
                         obligation="DATA_CODE_IMAGE_REVIEW" if action=="SELECT" else "NONE")

out={
    "schema_version":"5.0",
    "question_id":domain.get("question_id"),
    "quota":None,
    "selection_protocol":"One plan: select indispensable claims, merge shared evidence tasks, decline/defer the rest. Candidate counts and roles are not mandatory deliverable counts.",
    "candidates":c,
    "instruction":"These are high-value visual questions derived from existing artifacts, not a quota. Bias toward a richer portfolio when a complex task genuinely contains multiple distinct reader-facing questions, but reject decorative, repetitive or low-information figures. Multiple candidates may share one Figure Role only when they answer materially different research questions; otherwise merge tightly related evidence into one composite figure."
}
text=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
if a.out: a.out.write_text(text,encoding="utf-8")
else: print(text,end="")
