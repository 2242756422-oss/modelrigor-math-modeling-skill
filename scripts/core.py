#!/usr/bin/env python3
"""Fail-closed evidence and workflow checks for ModelRigor v5.1.2."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import re
import zipfile
from functools import lru_cache
from copy import deepcopy
from provenance import source_equal, display_matches, audit_verification, audit_run, audit_result_origin
from collections import defaultdict
from pathlib import Path
from typing import Any

_POLICY=json.loads((Path(__file__).resolve().parents[1]/"policy.json").read_text(encoding="utf-8"))
QUALITY = _POLICY["quality_dimensions"]
REVIEWERS = _POLICY["reviewer_roles"]
REVIEW_SCOPE = {
    "DOMAIN_EXPERT": {"DOMAIN_PROFESSIONALISM"},
    "MATHEMATICAL_MODELING_REVIEWER": {"SCIENTIFIC_CORRECTNESS", "MODELING_DEPTH"},
    "COMPETITION_JUDGE": {"CONTENT_DEPTH", "COMPETITIVE_QUALITY"},
    "SCIENTIFIC_FIGURE_EDITOR": {"VISUAL_QUALITY", "EVIDENCE_QUALITY"},
    "ADVERSARIAL_REVIEWER": {"SCIENTIFIC_CORRECTNESS", "EVIDENCE_QUALITY"},
}
ALLOWED_REVIEW = set(_POLICY["quality_statuses"])
FIGURE_ROLES = set(_POLICY["figure_roles"])
CHART_TYPES = {"line", "area", "scatter", "bubble", "hexbin", "bar", "dot", "lollipop", "histogram", "distribution", "density", "ecdf", "box", "violin", "raincloud", "heatmap", "cluster_heatmap", "correlation_matrix", "sensitivity_matrix", "schematic", "geometry_schematic", "workflow", "algorithm_architecture", "residual", "qq", "parity", "interval", "errorbar", "forest", "tornado", "roc", "pr", "calibration", "confusion_matrix", "radar", "polar", "network", "sankey", "chord", "map", "table_equivalent", "surface", "contour", "response_surface", "convergence", "objective_landscape", "parameter_profile", "multi_panel_composite", "pareto", "parallel_coordinates", "field_slice", "vector_field"}
SCIENTIFIC_NAMES = ["question_contract.json", "domain_model_map.json", "literature_to_model_map.csv", "model_contract.json", "assumption_ledger.csv", "uncertainty_budget.json", "result_registry.json", "conditional_gates.json"]
RESEARCH_NAMES = ["claim_evidence_map.csv", "content_units.csv", "evidence_promotion.csv", "figure_candidates.csv", "table_portfolio.csv", "competitive_development.json", "quality_assessment.json", "resource_consumption.csv", "visual_semantics.json"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def resolve(base: Path, relative: str) -> Path:
    p = Path(relative)
    return p if p.is_absolute() else (base / p).resolve()


def _nonempty(v: Any) -> bool:
    if isinstance(v, str):
        return bool(v.strip())
    return v is not None and v != [] and v != {}


def validate_text_locator(base: Path, spec: str, expected_hash: str | None = None) -> bool:
    if not spec or "#" not in spec:
        return False
    rel, fragment = spec.split("#", 1)
    p = resolve(base, rel)
    if not p.is_file() or not fragment:
        return False
    if expected_hash and sha256(p) != expected_hash:
        return False
    try:
        document=read_document(p)
        text=document_text(p,document)
        page=re.fullmatch(r"page=(\d+)::(.+)",fragment,re.S)
        if page:
            return any(x.get("page")==int(page[1]) and page[2] in x["text"] for x in document["segments"])
    except (ValueError,OSError): return False
    return fragment in text


def validate_hashed_locator(base: Path, spec: str) -> bool:
    if not spec or "@" not in spec:
        return False
    locator, digest = spec.rsplit("@", 1)
    return bool(re.fullmatch(r"[0-9a-f]{64}", digest)) and validate_text_locator(base, locator, digest)


def located_text(base:Path,spec:str)->str:
    """Inspect the selected text, never infer caption identity from a path."""
    if not validate_hashed_locator(base,spec): return ''
    locator=spec.rsplit('@',1)[0]; relative,fragment=locator.split('#',1)
    page=re.fullmatch(r'page=\d+::(.+)',fragment,re.S)
    if page: fragment=page[1]
    if fragment.startswith('['):
        return ' '.join(line.replace(fragment,'') for line in document_text(resolve(base,relative)).splitlines() if fragment in line)
    return fragment


def _read_document(path:Path)->dict:
    """One text/locator path; extraction is not proof of visual/math correctness.

    PDF page numbers are real source pages. Image-only/empty text pages block
    complete textual acceptance; OCR or reviewed transcription is a separate
    task, never silently substituted with bytes decoded as UTF-8.
    """
    from xml.etree import ElementTree as ET
    result={"kind":path.suffix.lower(),"status":"UNREADABLE","text":"","segments":[],"issues":[],"page_count":None,"page_sizes_pt":[]}
    if not path.is_file(): result["issues"]=["document missing"]; return result
    try:
        if path.suffix.lower()==".pdf":
            try: from pypdf import PdfReader
            except ImportError:
                result["issues"]=["PDF text extraction requires an available pypdf runtime; no automatic installation"]; return result
            reader=PdfReader(str(path)); result["page_count"]=len(reader.pages)
            missing=[]
            for i,page in enumerate(reader.pages,1):
                text=page.extract_text() or ""
                result["segments"].append({"page":i,"text":text})
                box=page.mediabox
                size=[float(box.width),float(box.height)]
                if int(page.get('/Rotate',0))%180: size.reverse()
                result["page_sizes_pt"].append(size)
                if not text.strip() or '\ufffd' in text: missing.append(i)
            result["text"]="\n\f\n".join(x["text"] for x in result["segments"])
            if missing or not reader.pages:
                result["status"]="TEXT_REVIEW_LIMITED"
                result["issues"]=[f"PDF text layer missing/unreliable on pages {missing}; inspect/OCR and verify before textual acceptance"]
            else: result["status"]="TEXT_READY"
        elif path.suffix.lower()==".docx":
            with zipfile.ZipFile(path) as z:
                if '[Content_Types].xml' not in z.namelist(): raise ValueError('invalid DOCX package')
                parts=['word/document.xml']+sorted(n for n in z.namelist() if re.fullmatch(r'word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml',n))
                for part in parts:
                    root=ET.fromstring(z.read(part))
                    for paragraph in root.iter():
                        if paragraph.tag.rsplit('}',1)[-1]!='p': continue
                        text=''.join(x.text or '' for x in paragraph.iter() if x.tag.rsplit('}',1)[-1]=='t')
                        result["segments"].append({"part":part,"text":text})
            result["text"]='\n'.join(x['text'] for x in result['segments']); result["status"]="TEXT_READY"
        elif path.suffix.lower() in ('.png','.jpg','.jpeg','.zip','.rar','.svg'):
            result["issues"]=["binary/visual artifact is not a text document"]
        else:
            text=path.read_text(encoding='utf-8-sig')
            result.update(text=text,segments=[{"text":x} for x in text.splitlines()],status="TEXT_READY")
    except (OSError,ValueError,KeyError,zipfile.BadZipFile,ET.ParseError) as e:
        result["issues"]=["cannot read document: "+str(e)]
    except Exception as e:
        # Optional PDF parser errors must fail closed, not return binary text.
        result["issues"]=["document parser failed: "+str(e)]
    return result


@lru_cache(maxsize=8)
def _cached_document(path:str,digest:str)->dict:
    return _read_document(Path(path))


def read_document(path:Path)->dict:
    # Content-keyed, bounded per-process extraction reuse: changing bytes
    # invalidates it even when timestamps/size are restored. Never share a
    # mutable status record with callers.
    path=Path(path).resolve()
    return deepcopy(_cached_document(str(path),sha256(path))) if path.is_file() else _read_document(path)


def document_text(path:Path,document:dict|None=None)->str:
    document=read_document(path) if document is None else document
    if document['status']!='TEXT_READY':
        raise ValueError('; '.join(document['issues']) or 'document text review unavailable')
    return document['text']


def validate_file_binding(base:Path,spec:str)->bool:
    if not spec or "@" not in spec:return False
    rel,digest=spec.rsplit("@",1);p=resolve(base,rel)
    return p.is_file() and bool(re.fullmatch(r"[0-9a-f]{64}",digest)) and sha256(p)==digest


def json_pointer(data: Any, pointer: str) -> Any:
    if pointer == "":
        return data
    if not pointer.startswith("/"):
        raise ValueError("JSON Pointer must start with /")
    cur = data
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        cur = cur[int(token)] if isinstance(cur, list) else cur[token]
    return cur


def equal_value(actual: Any, expected: Any, tol: float = 0.0) -> bool:
    if not isinstance(tol, (int, float)) or not math.isfinite(tol) or tol < 0:
        return False
    if isinstance(actual, bool) or isinstance(expected, bool):
        return source_equal(actual, expected)
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isfinite(float(actual)) and math.isfinite(float(expected)) and abs(float(actual)-float(expected)) <= tol
    return source_equal(actual, expected)


def _ids(items: list[Any]) -> list[str]:
    out = []
    for item in items:
        if isinstance(item, str): out.append(item.strip())
        elif isinstance(item, dict): out.append(str(item.get("id", item.get("name", item.get("output_id", "")))).strip())
    return [x for x in out if x]


def _quantifier_signature(items: list[Any]) -> list[tuple[str, str, str, str]]:
    sig = []
    for item in items:
        if not isinstance(item, dict): return []
        sig.append((str(item.get("variable", "")), str(item.get("domain", "")), str(item.get("quantifier", "")), str(item.get("aggregation", ""))))
    return sig


def _valid_quantifiers(items:list[Any])->bool:
    if not items:return False
    for x in items:
        if not isinstance(x,dict) or not all(_nonempty(x.get(k)) for k in ("variable","domain","quantifier","aggregation")):return False
        if x.get("quantifier") not in ("FOR_ALL","EXISTS"):return False
    return True


def audit_page_budget(path: Path) -> list[str]:
    d = load_json(path); issues: list[str] = []
    hard = d.get("hard_page_compliance", {}); status = hard.get("status")
    forbidden = ("reserved_global_pages", "available_question_pages", "question_page_targets")
    if any(k in d and d[k] not in (None, {}, "UNCONFIRMED") for k in forbidden): issues.append("mechanical or unsupported page targets present")
    if "total_page_limit" in d and d.get("total_page_limit") not in (None, "UNCONFIRMED"): issues.append("unsupported root total_page_limit present")
    def walk(obj,prefix=""):
        if isinstance(obj,dict):
            for k,v in obj.items():
                here=f"{prefix}.{k}" if prefix else k
                if k in ("target_pages","page_target","allocated_pages","question_page_targets","figures_required","figure_target","tables_required","table_target","formulas_required","formula_target","benchmark_required","ablation_required") and v not in (None,{},[],"UNCONFIRMED"): issues.append(f"legacy Depth/content allocation key present at {here}")
                walk(v,here)
        elif isinstance(obj,list):
            for i,v in enumerate(obj): walk(v,f"{prefix}[{i}]")
    walk(d)
    for q, item in (d.get("question_development") or {}).items():
        if any(k in item for k in ("target_pages", "page_target", "allocated_pages")): issues.append(f"{q}: concrete question page target present")
    if status == "UNSET":
        if hard.get("total_page_limit") is not None: issues.append("UNSET page policy has a concrete total limit")
    elif status == "VERIFIED":
        for k in ("official_rule_source", "competition_year", "source_sha256", "locator", "verbatim_excerpt", "total_page_limit", "counting_scope"):
            if not _nonempty(hard.get(k)): issues.append(f"verified page policy missing {k}")
        if not isinstance(hard.get("total_page_limit"), int) or hard.get("total_page_limit", 0) <= 0: issues.append("verified total page limit must be a positive integer")
        if not isinstance(d.get("target_competition_year"),int) or hard.get("competition_year")!=d.get("target_competition_year"): issues.append("official page rule year does not match declared target competition year")
        src = resolve(path.parent, hard.get("official_rule_source", ""))
        if not src.is_file() or hard.get("source_sha256") != (sha256(src) if src.is_file() else ""): issues.append("official rule source missing or hash mismatch")
        else:
            if not validate_text_locator(path.parent, f"{hard['official_rule_source']}#{hard.get('locator','')}", hard.get("source_sha256")): issues.append("official rule locator does not resolve")
            if not validate_text_locator(path.parent, f"{hard['official_rule_source']}#{hard.get('verbatim_excerpt','')}", hard.get("source_sha256")): issues.append("official rule excerpt does not occur in source")
        scope = hard.get("counting_scope", {})
        for part in ("cover", "abstract", "main_text", "references", "appendix", "ai_declaration"):
            if scope.get(part) not in ("INCLUDED", "EXCLUDED", "UNKNOWN"): issues.append(f"invalid counting scope: {part}")
    else: issues.append("hard_page_compliance.status must be UNSET or VERIFIED")
    if d.get("content_sufficiency") not in ("UNASSESSED", "UNDERDEVELOPED", "APPROPRIATE", "OVERDEVELOPED"): issues.append("invalid content_sufficiency")
    return issues


def audit_question_contract(path: Path) -> list[str]:
    d = load_json(path); issues = []
    for k in ("question_id", "task_text_locator", "required_outputs", "inputs", "decision_or_unknowns", "acceptance_evaluator"):
        if not _nonempty(d.get(k)): issues.append(f"question contract missing {k}")
    if d.get("task_text_locator") and not validate_hashed_locator(path.parent,d["task_text_locator"]): issues.append("task text locator unresolved or stale")
    seen = set()
    for out in d.get("required_outputs", []):
        if not isinstance(out, dict) or not all(_nonempty(out.get(k)) for k in ("output_id", "description", "evidence_type")) or "unit" not in out: issues.append("required_outputs must include output_id/description/evidence_type/unit"); continue
        if out["output_id"] in seen: issues.append("duplicate required output id")
        seen.add(out["output_id"])
    ev = d.get("acceptance_evaluator", {})
    for k in ("definition", "inputs", "outputs", "aggregation_quantifiers", "direction"):
        if not _nonempty(ev.get(k)): issues.append(f"acceptance evaluator missing {k}")
    if not _valid_quantifiers(ev.get("aggregation_quantifiers", [])): issues.append("acceptance evaluator quantifiers must be structured")
    if ev.get("direction") not in ("minimize","maximize","NOT_APPLICABLE"): issues.append("acceptance evaluator direction invalid")
    if d.get("allow_no_result") and not _nonempty(d.get("allow_no_result_reason")): issues.append("allow_no_result requires reason")
    if d.get("status")!="PASS": issues.append("question contract is not PASS")
    return issues


def audit_reviewer_report(path: Path, expected_role: str | None = None) -> list[str]:
    d=load_json(path); issues=[]; role=d.get("role")
    if expected_role and role!=expected_role: issues.append("reviewer role mismatch")
    if role not in REVIEWERS or not d.get("independent") or not _nonempty(d.get("run_id")): issues.append("reviewer identity/provenance invalid")
    if not all(_nonempty(d.get(k)) for k in ("agent_instance_id","attack_method","run_provenance")) or not validate_hashed_locator(path.parent,d.get("run_provenance","")): issues.append("reviewer runtime provenance invalid")
    artifacts=d.get("artifacts_read",[]); hashes=d.get("input_hashes",{})
    if not artifacts or set(artifacts)!=set(hashes): issues.append("artifacts_read and input_hashes must be identical nonempty sets")
    for rel in artifacts:
        p=resolve(path.parent,rel)
        if not p.is_file() or hashes.get(rel)!=(sha256(p) if p.is_file() else ""): issues.append(f"reviewer input stale/missing: {rel}")
    if not d.get("artifact_hashes_verified"): issues.append("reviewer did not verify hashes")
    findings=d.get("findings",[])
    if not findings: issues.append("reviewer findings cannot be empty")
    for f in findings:
        if not isinstance(f,dict) or not all(_nonempty(f.get(k)) for k in ("finding_id","severity","statement","evidence_locator","disposition")): issues.append("reviewer finding is not structured")
        elif not validate_hashed_locator(path.parent,f["evidence_locator"]): issues.append("reviewer finding evidence invalid")
    conclusions=d.get("quality_conclusions",{})
    if not REVIEW_SCOPE.get(role,set()).issubset(set(conclusions)): issues.append("reviewer quality scope incomplete")
    if any(conclusions.get(k)!="PASS" for k in REVIEW_SCOPE.get(role,set())): issues.append("reviewer scoped quality is not PASS")
    if set(d.get("review_scope",[]))!=REVIEW_SCOPE.get(role,set()): issues.append("review_scope inconsistent with role")
    if d.get("overall")!="PASS": issues.append("reviewer overall is not PASS")
    if not _nonempty(d.get("created_at")): issues.append("review timestamp missing")
    return issues


def audit_domain_map(path: Path) -> list[str]:
    d = load_json(path); issues = []
    if d.get("schema_version") == "5.1":
        from efficient import audit_adaptive_domain
        return audit_adaptive_domain(path)
    if not _nonempty(d.get("domain_family")): issues.append("domain_family missing")
    if not _nonempty(d.get("domain_objects")): issues.append("domain_objects missing")
    answers=d.get("answers",[])
    if {a.get("id") for a in answers}!=set(range(1,15)): issues.append("domain map must contain answers 1..14")
    for a in answers:
        if not _nonempty(a.get("answer")): issues.append(f"domain answer {a.get('id')} empty")
        if not a.get("evidence_locators"): issues.append(f"domain answer {a.get('id')} lacks evidence")
        for loc in a.get("evidence_locators",[]):
            if not validate_hashed_locator(path.parent,loc): issues.append(f"domain answer {a.get('id')} unresolved/stale locator")
    if not d.get("model_ladder") or not _nonempty(d.get("ladder_rationale")): issues.append("model ladder/rationale lacks problem-specific content")
    if any(x.get("status") not in ("RESOLVED","NOT_APPLICABLE") for x in d.get("p0_issues",[])): issues.append("unresolved domain P0 issue")
    review=d.get("domain_review",{}); rp=resolve(path.parent,review.get("report_artifact",""))
    if d.get("review_status")!="PASS": issues.append("independent domain review is not PASS")
    if review.get("role")!="DOMAIN_EXPERT" or not review.get("independent") or not review.get("run_id") or not rp.is_file() or review.get("report_sha256")!=(sha256(rp) if rp.is_file() else ""): issues.append("domain review provenance/report invalid")
    elif audit_reviewer_report(rp,"DOMAIN_EXPERT"): issues.append("domain reviewer report fails independent evidence checks")
    lg=d.get("literature_grounding",{})
    if lg.get("status") not in ("PASS","NOT_APPLICABLE"): issues.append("literature grounding unresolved")
    if lg.get("status")=="NOT_APPLICABLE" and not _nonempty(lg.get("reason")): issues.append("literature N/A lacks reason")
    return issues


def audit_literature_map(path: Path, domain_map_path: Path) -> list[str]:
    state=load_json(domain_map_path).get("literature_grounding",{}).get("status"); rows=load_csv(path)
    if state=="NOT_APPLICABLE": return []
    if not rows: return ["literature grounding PASS without mappings"]
    issues=[]
    for i,r in enumerate(rows,2):
        for k in ("source_id","source_type","source_locator","evidence_artifact","evidence_sha256","supported_role","model_object","adaptation","validity_range","decision_impact","status"):
            if not _nonempty(r.get(k)): issues.append(f"literature row {i} missing {k}")
        art=resolve(path.parent,r.get("evidence_artifact",""))
        if not art.is_file() or r.get("evidence_sha256")!=(sha256(art) if art.is_file() else ""): issues.append(f"literature row {i} evidence invalid")
        if r.get("status")!="PASS" or r.get("supported_role")=="background": issues.append(f"literature row {i} does not ground model")
    return issues


def audit_model_contract(path: Path) -> list[str]:
    """Structural consistency only. [] is NOT a well-posedness/math proof.

    Applicable existence, uniqueness, stability and identification arguments
    belong to the bound substantive domain review, not equation-count heuristics.
    """
    d=load_json(path); issues=[]
    for k in ("model_type","mathematical_objects","inputs","outputs","governing_relations","evaluator","failure_modes"):
        if not _nonempty(d.get(k)): issues.append(f"model contract missing {k}")
    ev=d.get("evaluator",{})
    for k in ("definition","artifact","artifact_sha256","version","scientific_version","inputs","outputs","aggregation_quantifiers","direction","numerical_interface"):
        if not _nonempty(ev.get(k)): issues.append(f"evaluator missing {k}")
    art=resolve(path.parent,ev.get("artifact",""))
    if not art.is_file() or ev.get("artifact_sha256")!=(sha256(art) if art.is_file() else ""): issues.append("evaluator artifact/hash invalid")
    if not _valid_quantifiers(ev.get("aggregation_quantifiers",[])): issues.append("evaluator quantifiers must be structured")
    if d.get("quantifiers") and not _valid_quantifiers(d.get("quantifiers",[])): issues.append("model quantifiers invalid")
    if ev.get("direction") not in ("minimize","maximize","NOT_APPLICABLE"): issues.append("evaluator direction invalid")
    if not isinstance(ev.get("scientific_version"),int) or ev.get("scientific_version",0)<1: issues.append("evaluator scientific_version must be positive")
    explanations=d.get("closure_explanations",{}); allowed_na={"NOT_APPLICABLE_ALGEBRAIC","NOT_APPLICABLE_EXACT_THEORY","NOT_APPLICABLE_NO_INDEX","NOT_APPLICABLE_NO_CONSTRAINT"}
    for k in ("index_domains","variables","parameters","quantifiers","initial_boundary_conditions","constraints"):
        if not _nonempty(d.get(k)) and explanations.get(k) not in allowed_na: issues.append(f"model contract does not close {k}")
    for k in ("variables","parameters"):
        for item in d.get(k,[]):
            if not isinstance(item,dict) or not _nonempty(item.get("name")) or not _nonempty(item.get("meaning")) or "unit" not in item: issues.append(f"{k} entries require name/meaning/unit")
    var_units={x.get("name"):x.get("unit") for x in d.get("variables",[]) if isinstance(x,dict)}
    out_units={x.get("id",x.get("name")):x.get("unit") for x in d.get("outputs",[]) if isinstance(x,dict)}
    for name in set(var_units)&set(out_units):
        if var_units[name]!=out_units[name]: issues.append(f"variable/output unit conflict for {name}")
    if d.get("model_type")=="optimization":
        if not isinstance(d.get("objective"),dict) or not all(_nonempty(d["objective"].get(k)) for k in ("sense","expression","decision_variables")): issues.append("optimization objective is not closed")
        if not d.get("constraints"): issues.append("optimization feasible domain missing")
        if not _nonempty(d.get("feasibility_evaluator")): issues.append("optimization feasibility evaluator missing")
    elif d.get("model_type") in ("physical","physics","engineering","physical_engineering"):
        if not d.get("initial_boundary_conditions"): issues.append("physical/engineering boundary conditions missing")
        if not _nonempty(d.get("observation_operator")): issues.append("physical/engineering observation operator missing")
    elif d.get("model_type") in ("machine_learning","data_ml"):
        for k in ("data_generating_process","observation_unit","split_protocol","leakage_controls","generalization_target"):
            if not _nonempty(d.get(k)): issues.append(f"data/ML contract missing {k}")
    elif d.get("model_type") in ("data","statistical","statistics"):
        for k in ("data_generating_process","observation_unit","identification_assumptions","dependence_structure","uncertainty_method"):
            if not _nonempty(d.get(k)): issues.append(f"statistical contract missing {k}")
    elif not d.get("objective") and explanations.get("objective") not in allowed_na: issues.append("absent objective lacks controlled N/A")
    if not _nonempty(d.get("identifiability")): issues.append("identifiability/uniqueness analysis missing")
    if d.get("status")!="PASS": issues.append("model contract is not PASS")
    return issues


def audit_contract_alignment(question_path: Path, model_path: Path) -> list[str]:
    q,m=load_json(question_path),load_json(model_path); issues=[]
    if set(_ids(q.get("inputs",[])))!=set(_ids(m.get("inputs",[]))): issues.append("question/model inputs disagree")
    def units(items): return {str(x.get("id",x.get("name"))):x.get("unit") for x in items if isinstance(x,dict)}
    if units(q.get("inputs",[]))!=units(m.get("inputs",[])): issues.append("question/model input units disagree")
    required={x.get("output_id") for x in q.get("required_outputs",[]) if isinstance(x,dict)}
    if not required.issubset(set(_ids(m.get("outputs",[])))): issues.append("model outputs do not cover required outputs")
    qout={x.get("output_id"):x.get("unit") for x in q.get("required_outputs",[]) if isinstance(x,dict)}
    mout=units(m.get("outputs",[]))
    if any(mout.get(k)!=v for k,v in qout.items()): issues.append("question/model output units disagree")
    unknowns=set(_ids(q.get("decision_or_unknowns",[]))); model_unknowns=set(_ids(m.get("variables",[])))|set(_ids(m.get("outputs",[])))
    if not unknowns.issubset(model_unknowns): issues.append("question unknowns/decisions are absent from model variables")
    qe,me=q.get("acceptance_evaluator",{}),m.get("evaluator",{})
    for k in ("inputs","outputs"):
        if set(_ids(qe.get(k,[])))!=set(_ids(me.get(k,[]))): issues.append(f"acceptance/model evaluator {k} disagree")
    if qe.get("direction")!=me.get("direction"): issues.append("acceptance/model evaluator direction disagrees")
    qsig=_quantifier_signature(qe.get("aggregation_quantifiers",[])); msig=_quantifier_signature(me.get("aggregation_quantifiers",[]))
    if qsig!=msig: issues.append("acceptance/model evaluator quantifiers disagree")
    if _quantifier_signature(m.get("quantifiers",[]))!=qsig: issues.append("model governing quantifiers disagree with acceptance contract")
    return issues


def audit_assumptions(path: Path, explicit_none_reason: str | None = None) -> list[str]:
    rows=load_csv(path)
    if not rows: return [] if _nonempty(explicit_none_reason) else ["empty assumption ledger without closure reason"]
    issues=[]
    for i,r in enumerate(rows,2):
        for k in ("assumption_id","category","statement","source_or_reason","affected_objects","impact_chain","testability","status"):
            if not _nonempty(r.get(k)): issues.append(f"assumption row {i} missing {k}")
        if r.get("status") not in ("ACCEPTED","TESTED","REJECTED","NOT_APPLICABLE"): issues.append(f"assumption row {i} invalid status")
    return issues


def read_result_value(result: dict[str, Any], registry_dir: Path) -> tuple[Any,list[str]]:
    src=result.get("source",{}); typ=src.get("type"); issues=[]; art=resolve(registry_dir,src.get("artifact",""))
    if not art.is_file(): return None,["source artifact missing"]
    if result.get("artifact_sha256")!=sha256(art): issues.append("source artifact hash mismatch")
    try:
        if typ in ("json_pointer","analytical"):
            if typ=="analytical" and not str(src.get("pointer","")).startswith("/"): return None,issues+["analytical result requires structured JSON pointer"]
            value=json_pointer(load_json(art),src.get("pointer",""))
        elif typ=="csv_cell":
            value=load_csv(art)[int(src["row"])][src["column"]]
            if isinstance(result.get("raw_value"),(int,float)): value=float(value)
            elif result.get("raw_value") is None:
                try: value=json.loads(value)
                except json.JSONDecodeError: pass
        else: return None,issues+["unsupported result source type"]
    except Exception as e: return None,issues+[f"cannot resolve source: {e}"]
    return value,issues


def audit_result_registry(path: Path, expected_version: int | None = None, allow_empty: bool = False) -> list[str]:
    d=load_json(path); issues=[]; seen=set()
    if not d.get("results") and not allow_empty: issues.append("result registry is empty")
    for r in d.get("results",[]):
        rid=r.get("result_id")
        if not rid or rid in seen: issues.append("missing or duplicate result_id")
        seen.add(rid)
        for k in ("meaning","unit","raw_value","display_value","source","artifact_sha256","scientific_version","required_output_ids"):
            optional_input_ids=(k=='required_output_ids' and r.get('source',{}).get('category') in ('GIVEN','OBSERVED'))
            if k not in r or (k!="unit" and not optional_input_ids and not _nonempty(r.get(k))): issues.append(f"{rid}: missing {k}")
        actual,local=read_result_value(r,path.parent); issues.extend(f"{rid}: {x}" for x in local)
        if r.get("source_tolerance", 0) not in (0, 0.0, None):
            issues.append(f"{rid}: source transcription must be exact; source_tolerance cannot mask changes")
        if not local and not source_equal(actual,r.get("raw_value")):
            issues.append(f"{rid}: raw value does not match source")
        if not display_matches(r.get("raw_value"),r.get("display_value")):
            issues.append(f"{rid}: display value inconsistent with source-derived rounding")
        if not r.get("approved"): issues.append(f"{rid}: result is not approved")
        if expected_version is not None and r.get("scientific_version")!=expected_version: issues.append(f"{rid}: scientific_version mismatch")
        issues.extend(f"{rid}: {x}" for x in audit_result_origin(path.parent,r))
        ver=r.get("verification",[])
        if not ver: issues.append(f"{rid}: no verification")
        for v in ver:
            vp=resolve(path.parent,v.get("artifact",""))
            if not vp.is_file() or v.get("sha256")!=(sha256(vp) if vp.is_file() else ""): issues.append(f"{rid}: verification artifact/hash invalid"); continue
            if v.get("status")!="PASS": issues.append(f"{rid}: verification binding status is not PASS")
            try: vd=load_json(vp)
            except Exception: issues.append(f"{rid}: verification must be structured JSON"); continue
            if vd.get("status")!="PASS" or not _nonempty(vd.get("method")):
                issues.append(f"{rid}: verification conclusion invalid")
            issues.extend(f"{rid}: {x}" for x in audit_verification(path.parent,vd,r))
            if vd.get("scientific_version")!=r.get("scientific_version"): issues.append(f"{rid}: result/verification scientific versions disagree")
            if expected_version is not None and vd.get("scientific_version")!=expected_version: issues.append(f"{rid}: verification scientific_version mismatch")
        if not isinstance(r.get("scientific_version"),int) or r.get("scientific_version",0)<1: issues.append(f"{rid}: scientific_version must be positive")
    return issues


def _claim_refs_ok(base: Path, refs: str, result_ids: set[str]) -> list[str]:
    issues=[]
    for ref in [x.strip() for x in refs.split(";") if x.strip()]:
        if ref.startswith("result:"):
            if ref[7:] not in result_ids: issues.append(f"dangling result {ref}")
        elif ref.startswith("file:"):
            if not validate_hashed_locator(base,ref[5:]): issues.append(f"dangling/stale file evidence {ref}")
        else: issues.append(f"unsupported evidence reference {ref}")
    return issues


def audit_claims(path: Path, result_registry: Path, require_paper: bool = True) -> list[str]:
    rows=load_csv(path); registry=load_json(result_registry).get("results",[]); results={r.get("result_id") for r in registry}; approved={r.get("result_id") for r in registry if r.get("approved")}; issues=[]
    if not rows: issues.append("claim map is empty")
    for i,r in enumerate(rows,2):
        if r.get("status") not in ("PASS","NOT_APPLICABLE"): issues.append(f"claim row {i} is not approved")
        if r.get("status")=="NOT_APPLICABLE":
            if not _nonempty(r.get("boundary")): issues.append(f"claim row {i} N/A lacks reason")
            continue
        for k in ("claim_id","claim_text","claim_type","evidence_refs","scope","boundary"):
            if not _nonempty(r.get(k)): issues.append(f"claim row {i} missing {k}")
        issues.extend(f"claim row {i} {x}" for x in _claim_refs_ok(path.parent,r.get("evidence_refs",""),results))
        for ref in [x.strip() for x in r.get("evidence_refs","").split(";") if x.startswith("result:")]:
            if ref[7:] not in approved: issues.append(f"claim row {i} cites unapproved result {ref}")
        if require_paper and not validate_text_locator(path.parent,r.get("paper_locator",""),r.get("paper_sha256","")): issues.append(f"claim row {i} paper locator/hash invalid")
    return issues


def audit_output_coverage(question_path: Path, result_path: Path, claims_path: Path) -> list[str]:
    q=load_json(question_path); required={x["output_id"] for x in q.get("required_outputs",[]) if isinstance(x,dict) and x.get("output_id")}; covered=set()
    for r in load_json(result_path).get("results",[]): covered.update(r.get("required_output_ids",[]))
    for c in load_csv(claims_path): covered.update(x.strip() for x in c.get("required_output_ids","").split(";") if x.strip())
    if not required and not q.get("allow_no_result"): return ["no required outputs and no explicit no-result contract"]
    issues=[]; missing=sorted(required-covered)
    output_types={x.get('output_id'):str(x.get('evidence_type','')).upper() for x in q.get('required_outputs',[]) if isinstance(x,dict)}
    for result in load_json(result_path).get('results',[]):
        if result.get('source',{}).get('category') in ('GIVEN','OBSERVED'):
            invalid=[x for x in result.get('required_output_ids',[]) if x in required and output_types[x] not in ('GIVEN','PARAMETER','OBSERVED','OBSERVATION','DATA')]
            if invalid: issues.append('given/observed input cannot substitute for a modeled output: '+','.join(invalid))
    if missing: issues.append("required outputs uncovered: "+",".join(missing))
    if required and not load_json(result_path).get("results",[]) and not load_csv(claims_path): issues.append("required outputs cannot close with empty result and claim sets")
    return issues


def audit_uncertainty(path: Path) -> list[str]:
    d=load_json(path); required={"domain_definition","model_form","data","measurement","material_or_business_parameter","numerical","optimization","implementation","operational"}; issues=[]
    by={r.get("category"):r for r in d.get("categories",[])}
    if d.get("schema_version")=="5.1":
        if not by or not set(by).issubset(required) or not d.get("risk_selection_basis"):
            issues.append("activated uncertainty risks/selection basis missing")
    elif set(by)!=required: issues.append("uncertainty categories incomplete")
    for name,r in by.items():
        if r.get("status") not in ("ASSESSED","NOT_APPLICABLE"): issues.append(f"uncertainty {name} not assessed")
        if r.get("status")=="ASSESSED" and not all(_nonempty(r.get(k)) for k in ("risk","impact","verification")): issues.append(f"uncertainty {name} lacks risk/impact/verification")
        if r.get("status")=="ASSESSED":
            for loc in r.get("verification",[]):
                if not validate_hashed_locator(path.parent,loc): issues.append(f"uncertainty {name} verification invalid")
        if r.get("status")=="NOT_APPLICABLE" and not _nonempty(r.get("risk")): issues.append(f"uncertainty {name} N/A lacks reason")
    dominant=d.get("dominant_risks",[])
    if not dominant: issues.append("dominant risks not identified")
    for x in dominant:
        name=x.get("category") if isinstance(x,dict) else x
        if name not in by or by.get(name,{}).get("status")!="ASSESSED" or not by.get(name,{}).get("verification"): issues.append(f"dominant risk {name} lacks assessed verification")
    return issues


def derived_content_requirements(question_dir: Path) -> dict[str,str]:
    q=load_json(question_dir/"question_contract.json"); r=load_json(question_dir/"result_registry.json")
    req={f"OUTPUT:{x['output_id']}":"required_output" for x in q.get("required_outputs",[]) if isinstance(x,dict) and x.get("output_id")}
    req.update({"DOMAIN:MODEL":"domain_model","MODEL:CLOSURE":"model_closure","MODEL:BOUNDARY":"boundary_or_constraints","VERIFY:DOMINANT_RISK":"verification"})
    for x in r.get("results",[]): req[f"RESULT:{x.get('result_id')}"]="result_interpretation"
    return req


def audit_content(path: Path, question_dir: Path | None = None) -> tuple[str,list[str]]:
    rows=load_csv(path); issues=[]; redundant=[]; covered=set(); results=set()
    if question_dir and (question_dir/"result_registry.json").exists(): results={r["result_id"] for r in load_json(question_dir/"result_registry.json").get("results",[])}
    for i,r in enumerate(rows,2):
        if r.get("status")=="REDUNDANT" or r.get("redundancy")=="YES": redundant.append(r.get("unit_id") or str(i)); continue
        if r.get("status")!="COVERED": continue
        for k in ("unit_id","source_kind","source_ids","requirement","importance","evidence_refs","paper_locator","paper_sha256","development"):
            if not _nonempty(r.get(k)): issues.append(f"content row {i} missing {k}")
        if not validate_text_locator(path.parent,r.get("paper_locator",""),r.get("paper_sha256","")): issues.append(f"content row {i} paper locator/hash invalid")
        issues.extend(f"content row {i} {x}" for x in _claim_refs_ok(path.parent,r.get("evidence_refs",""),results))
        covered.update(x.strip() for x in r.get("source_ids","").split(";") if x.strip())
    missing=[]
    if question_dir:
        missing=sorted(set(derived_content_requirements(question_dir))-covered)
        if missing: issues.append("authoritative content units missing: "+",".join(missing))
    if missing or issues:
        if redundant: issues.append("simultaneous low-value repetition: "+",".join(redundant))
        return "UNDERDEVELOPED",issues
    if redundant: return "OVERDEVELOPED",["low-value repetition: "+",".join(redundant)]
    if not rows: return "UNASSESSED",["no content units assessed"]
    return "APPROPRIATE",[]


def _real_image(path: Path) -> bool:
    if not path.is_file(): return False
    suffix=path.suffix.lower()
    try:
        if suffix in ('.png','.jpg','.jpeg'):
            from PIL import Image
            with Image.open(path) as im:
                if im.format not in ('PNG','JPEG'): return False
                im.verify()
            return True
        if suffix=='.svg':
            from xml.etree import ElementTree as ET
            return ET.parse(path).getroot().tag.rsplit('}',1)[-1]=='svg'
        if suffix=='.pdf':
            from pypdf import PdfReader
            return len(PdfReader(str(path)).pages)>0
    except Exception: return False
    return False


def image_dimensions(path:Path)->tuple[int,int]|None:
    if not _real_image(path): return None
    b=path.read_bytes()
    if path.suffix.lower()==".png" and len(b)>=24: return int.from_bytes(b[16:20],"big"),int.from_bytes(b[20:24],"big")
    try:
        from PIL import Image
        with Image.open(path) as im: return im.size
    except Exception: return None


def audit_image_readability(path:Path, review:dict)->list[str]:
    """File validity and raster sampling at final size, not scientific/aesthetic QA.

    Vector sources use their actual raster preview and substantive visual review;
    a source vector never inherits a PNG pixel threshold. Final page QA remains
    authoritative for actual placement, crop, fonts and text legibility.
    """
    if not _real_image(path): return ['invalid or undecodable figure file']
    if path.suffix.lower() in ('.svg','.pdf'): return []
    dimensions=image_dimensions(path)
    if not dimensions or min(dimensions)<=0: return ['raster dimensions unavailable']
    try:
        width=float(review['final_width_mm'])
        # Preserve aspect unless an explicit actual manuscript height is known.
        height=float(review.get('final_height_mm') or width*dimensions[1]/dimensions[0])
        if not all(math.isfinite(x) and x>0 for x in (width,height)): raise ValueError('size')
    except (KeyError,ValueError,TypeError):
        return ['raster readability not verified: actual final manuscript size missing']
    requirement=review.get('raster_requirement') or {}
    # Print reference for line/text plots, not a universal scientific-quality score.
    target=requirement.get('minimum_effective_dpi',300)
    try:
        target=float(target)
        if not math.isfinite(target) or target<=0: raise ValueError('DPI')
    except (TypeError,ValueError): return ['invalid figure-specific raster sampling requirement']
    if requirement and not requirement.get('basis'):
        return ['custom raster sampling requirement needs actual display/type rationale']
    effective=(dimensions[0]*25.4/width,dimensions[1]*25.4/height)
    # Raster exports quantize real physical dimensions to integer pixels.
    # Permit only that <1 pixel truncation, not an arbitrary percentage tolerance.
    needed=(max(1,math.floor(target*width/25.4+1e-9)),max(1,math.floor(target*height/25.4+1e-9)))
    if any(actual<minimum for actual,minimum in zip(dimensions,needed)):
        return [f'raster resolution too low at final size: {dimensions[0]}x{dimensions[1]}, effective DPI {effective[0]:.1f}/{effective[1]:.1f}, reference {target:g}; change display/export or substantiate figure-specific requirement']
    return []


def audit_figures(path: Path, domain_family: str = "", result_registry: Path | None = None, mechanism_required:bool|None=None) -> tuple[str,list[str]]:
    rows=load_csv(path); issues=[]; delivered=[]; mechanism=False; result_ids=set(); result_records={}; output_paths=set(); output_hashes=set()
    if result_registry and result_registry.exists():
        result_records={r["result_id"]:r for r in load_json(result_registry).get("results",[]) if r.get("approved")}
        result_ids=set(result_records)
    for i,r in enumerate(rows,2):
        role=r.get("role",""); status=r.get("status",""); rid=r.get("figure_id") or str(i)
        if role not in FIGURE_ROLES: issues.append(f"{rid}: invalid visual role")
        if status in ("NOT_APPLICABLE","DECLINED","MERGED"):
            if not rid or not r.get("research_question") or not r.get("status_reason"):
                issues.append(f"{rid}: discarded candidate needs its scientific question and disposition reason")
            if status=="MERGED" and not r.get("merged_into"):
                issues.append(f"{rid}: merged candidate target missing")
            continue
        if role=="MECHANISM" and status in ("DELIVERED","EQUIVALENT"): mechanism=True
        for k in ("figure_id","question_id","role","research_question","message","data_source","data_identity","demo_quarantine","preferred_chart_type","importance","status"):
            if not _nonempty(r.get(k)): issues.append(f"{rid}: missing {k}")
        if r.get("preferred_chart_type") not in CHART_TYPES: issues.append(f"{rid}: invalid preferred chart type")
        ds=r.get("data_source","")
        if ds.startswith("result:"):
            if ds[7:] not in result_ids: issues.append(f"{rid}: dangling result data source")
        else:
            p=resolve(path.parent,ds)
            if not p.is_file() or r.get("data_source_sha256")!=(sha256(p) if p.is_file() else ""): issues.append(f"{rid}: data source/hash invalid")
        identity=r.get("data_identity")
        if identity not in ("REAL_OBSERVATION","REAL_DERIVED","APPROVED_SYNTHETIC","ANALYTICAL","SIMULATED","SCHEMATIC"): issues.append(f"{rid}: invalid data identity")
        if r.get("demo_quarantine") not in ("REAL_DATA","SYNTHETIC_LABELED","NOT_APPLICABLE"): issues.append(f"{rid}: invalid demo quarantine")
        if identity=="APPROVED_SYNTHETIC" and r.get("demo_quarantine")!="SYNTHETIC_LABELED": issues.append(f"{rid}: synthetic evidence is not labeled")
        if status=="DELIVERED":
            out=resolve(path.parent,r.get("output_path",""))
            if not _real_image(out) or r.get("output_sha256")!=(sha256(out) if out.is_file() else ""): issues.append(f"{rid}: output is not a hash-bound image")
            if out.suffix.lower() in (".png",".jpg",".jpeg") and _real_image(out) and not _image_has_visible_content(out):
                issues.append(f"{rid}: blank or visibly empty raster figure cannot be accepted")
            if not validate_hashed_locator(path.parent,r.get("caption_locator","")): issues.append(f"{rid}: caption locator invalid")
            if not validate_text_locator(path.parent,r.get("paper_locator","")): issues.append(f"{rid}: paper locator invalid")
            if not validate_file_binding(path.parent,r.get("plot_code","")):
                issues.append(f"{rid}: generating code/vector source missing or stale")
            generation_issues,generation=audit_run(path.parent,r.get("generation_receipt",""),r.get("output_path"))
            issues.extend(f"{rid}: generation {x}" for x in generation_issues)
            if generation:
                dependencies=generation.get("code",[])+generation.get("inputs",[])
                code_digest=r.get("plot_code","").rsplit("@",1)[-1]
                if code_digest not in {x.rsplit("@",1)[-1] for x in dependencies}:
                    issues.append(f"{rid}: generating source not used by recorded plot/export")
                data_digest=r.get("data_source_sha256")
                if ds.startswith("result:") and ds[7:] in result_records:
                    result=result_records[ds[7:]]; actual,source_issues=read_result_value(result,result_registry.parent)
                    if source_issues or not source_equal(actual,result.get("raw_value")):
                        issues.append(f"{rid}: result data source invalid")
                    data_digest=result.get("artifact_sha256")
                if data_digest not in {x.rsplit("@",1)[-1] for x in generation.get("inputs",[])}:
                    issues.append(f"{rid}: plotted source not an input of the recorded generation")
            review_binding=r.get("visual_review","")
            if not validate_file_binding(path.parent,review_binding):
                issues.extend(f"{rid}: {x}" for x in audit_image_readability(out,{}))
                issues.append(f"{rid}: actual visual inspection required; image existence/hash is not visual quality")
            else:
                vr=load_json(resolve(path.parent,review_binding.rsplit("@",1)[0]))
                issues.extend(f"{rid}: {x}" for x in audit_image_readability(out,vr))
                if vr.get("image_sha256")!=r.get("output_sha256") or vr.get("outcome")!="ACCEPTED" or not vr.get("reviewer"):
                    issues.append(f"{rid}: visual inspection not bound to this final image")
                if vr.get("inspection_scope")!="DIRECT_IMAGE_AND_FINAL_SIZE" or not vr.get("final_width_mm") or not validate_file_binding(path.parent,vr.get("final_size_preview","")):
                    issues.append(f"{rid}: final manuscript-size inspection missing")
                else:
                    preview=resolve(path.parent,vr["final_size_preview"].rsplit("@",1)[0])
                    if preview.suffix.lower() not in (".png",".jpg",".jpeg") or not _image_has_visible_content(preview):
                        issues.append(f"{rid}: rendered final-size preview is blank or invalid")
                for item in ("scientific_encoding","source_fidelity","axes_units","legibility","legend_color","panel_caption","claim_support"):
                    finding=vr.get("checks",{}).get(item,{})
                    if finding.get("outcome") not in ("ACCEPTED","JUSTIFIED_NOT_APPLICABLE") or not finding.get("observation"):
                        issues.append(f"{rid}: observed visual check missing: {item}")
                if any(f.get("severity") in ("P0","P1") and f.get("disposition")!="RESOLVED" for f in vr.get("findings",[])):
                    issues.append(f"{rid}: unresolved visual defect")
            if r.get("output_path") in output_paths or r.get("output_sha256") in output_hashes: issues.append(f"{rid}: duplicate visual output masquerades as a separate figure")
            output_paths.add(r.get("output_path")); output_hashes.add(r.get("output_sha256"))
            try:
                count=int(r.get("panel_count") or 1)
                if count<1: raise ValueError("panel count")
                if count>1:
                    panels=json.loads(r.get("panels") or "[]")
                    if len(panels)!=count or any(not all(p.get(k) for k in ("label","role","evidence_claim")) or p.get("role") not in FIGURE_ROLES for p in panels):
                        issues.append(f"{rid}: panel evidence tasks not recorded consistently")
            except (ValueError,TypeError,AttributeError): issues.append(f"{rid}: invalid panel count/tasks")
            if identity=="APPROVED_SYNTHETIC":
                cap=located_text(path.parent,r.get("caption_locator","")).lower(); reason=r.get("status_reason","")
                if not any(x in cap for x in ("synthetic","合成")) or "VALIDATION_ONLY" not in reason: issues.append(f"{rid}: synthetic figure lacks caption identity or validation-only boundary")
            if identity in ("SIMULATED","SCHEMATIC"):
                labels=("simulation","simulated","仿真","模拟") if identity=="SIMULATED" else ("schematic","示意")
                if not any(x in located_text(path.parent,r.get("caption_locator","")).lower() for x in labels):
                    issues.append(f"{rid}: simulation/schematic identity must be explicit in the caption")
                if identity=="SIMULATED": issues.extend(f"{rid}: {x}" for x in audit_run(path.parent,r.get("computation_receipt",""))[0])
            delivered.append((r.get("preferred_chart_type"),role,r.get("research_question"),r.get("status_reason")))
        elif status=="EQUIVALENT":
            if not validate_hashed_locator(path.parent,r.get("equivalent_expression","")): issues.append(f"{rid}: equivalent expression invalid")
        else: issues.append(f"{rid}: unresolved figure status")
    physical=domain_family.lower() in ("physical","physics","engineering","physical_engineering")
    if (physical if mechanism_required is None else mechanism_required) and not mechanism: issues.append("physical/engineering model lacks delivered or equivalent mechanism evidence")
    from efficient import is_efficient
    if not is_efficient(path.parent) and len(delivered)>=3:
        charts={x[0] for x in delivered}; roles={x[1] for x in delivered}; questions={x[2] for x in delivered}
        reasons=[x[3] or "" for x in delivered]
        justified=all("TASK_MATCH:" in x and len(x)>=40 for x in reasons) and len(set(reasons))==len(reasons)
        if len(charts)==1 and (len(roles)>1 or len(questions)>1) and not justified: issues.append("VISUAL_MONOTONY: repeated encoding lacks distinct task-match rationale")
    return ("FAIL" if issues else "PASS"),issues


def audit_reviewers(directory: Path) -> list[str]:
    reports=[]
    for p in directory.glob("*.json"):
        try:
            d=load_json(p)
            if d.get("role") in REVIEWERS: reports.append((p,d))
        except Exception: pass
    issues=[]; by_role={d["role"]:(p,d) for p,d in reports}
    for role in REVIEWERS:
        if role not in by_role: issues.append(f"missing independent reviewer: {role}")
        else: issues.extend(f"{role}: {x}" for x in audit_reviewer_report(by_role[role][0],role))
    ids=[d.get("run_id") for _,d in reports]
    if len(ids)!=len(set(ids)): issues.append("reviewer run_ids are not independent")
    agents=[d.get("agent_instance_id") for _,d in reports]; methods=[d.get("attack_method") for _,d in reports]
    if len(agents)!=len(set(agents)) or len(methods)!=len(set(methods)): issues.append("reviewer instances/attack methods are not independent")
    evidence_sets=[{f.get("evidence_locator") for f in d.get("findings",[]) if isinstance(f,dict)} for _,d in reports]
    if len(reports)==len(REVIEWERS) and any(not (evidence_sets[i]-set().union(*(evidence_sets[:i]+evidence_sets[i+1:]))) for i in range(len(evidence_sets))): issues.append("each reviewer must contribute role-specific attack evidence")
    normalized=[]
    for _,d in reports:
        text=" ".join(f.get("statement","") for f in d.get("findings",[]) if isinstance(f,dict)).lower()
        for token in [str(d.get("role","")).lower(),str(d.get("run_id","")).lower(),str(d.get("agent_instance_id","")).lower()]: text=text.replace(token,"")
        normalized.append(re.sub(r"\s+"," ",text).strip())
    if len(normalized)!=len(set(normalized)): issues.append("reviewer narratives are cloned after identity normalization")
    return issues


def summarize_benchmark(protocol: dict[str,Any], runs: list[dict[str,Any]]) -> dict[str,Any]:
    if not protocol.get("triggered"): return {"status":"NOT_TRIGGERED","winner":None}
    fairness=protocol.get("fairness",{}); required=("data","evaluator","feasible_set","budget","termination","metric","direction","hardware","parallelism")
    bad=[k for k in required if fairness.get(k)!="SAME"]
    if bad: return {"status":"UNRESOLVED_UNFAIR","winner":None,"fairness_gaps":bad}
    direction=protocol.get("direction"); tol=protocol.get("tolerance")
    if direction not in ("minimize","maximize"): return {"status":"INVALID_PROTOCOL","winner":None,"reason":"direction"}
    try: tol=float(tol)
    except Exception: return {"status":"INVALID_PROTOCOL","winner":None,"reason":"tolerance"}
    if not math.isfinite(tol) or tol<0 or not _nonempty(protocol.get("tolerance_basis")): return {"status":"INVALID_PROTOCOL","winner":None,"reason":"tolerance"}
    metric=protocol.get("metric"); groups=defaultdict(list)
    failed=[]
    for r in runs:
        try: v=float(r[metric])
        except Exception: failed.append(r.get("method","UNKNOWN")); continue
        if r.get("feasible") is True and math.isfinite(v) and _nonempty(r.get("method")): groups[r["method"]].append(v)
        else: failed.append(r.get("method","UNKNOWN"))
    if failed:
        return {"status":"UNRESOLVED_FAILED_RUNS","winner":None,"failed_methods":failed,"reason":"Failure/feasibility rates require a fair protocol; cannot silently rank only surviving runs."}
    if len(groups)<2: return {"status":"INSUFFICIENT_COMPETITORS","winner":None}
    try: minimum=int(protocol.get("minimum_repetitions",1))
    except (TypeError,ValueError): return {"status":"INVALID_PROTOCOL","winner":None,"reason":"repetitions"}
    if minimum<1: return {"status":"INVALID_PROTOCOL","winner":None,"reason":"repetitions"}
    if protocol.get("stochastic") and any(len(v)<max(2,minimum) for v in groups.values()): return {"status":"INSUFFICIENT_REPETITIONS","winner":None}
    means={k:sum(v)/len(v) for k,v in groups.items()}; ordered=sorted(means.items(),key=lambda x:x[1],reverse=direction=="maximize"); gap=abs(ordered[0][1]-ordered[1][1])
    if gap<=tol: return {"status":"PRACTICAL_TIE","winner":None,"leaders":[ordered[0][0],ordered[1][0]],"method_means":means,"gap":gap,"tolerance":tol}
    return {"status":"CLEAR_WINNER","winner":ordered[0][0],"method_means":means,"gap":gap,"tolerance":tol}


def _gate_report(base:Path,gate:dict[str,Any],name:str,exact_required:bool=False)->list[str]:
    report=gate.get("report")
    if not isinstance(report,dict): return [f"triggered {name} lacks structured report binding"]
    p=resolve(base,report.get("artifact",""))
    if not p.is_file() or report.get("sha256")!=(sha256(p) if p.is_file() else ""): return [f"triggered {name} report/hash invalid"]
    try: d=load_json(p)
    except Exception: return [f"triggered {name} report is not JSON"]
    allowed={"benchmark":{"PRACTICAL_TIE","CLEAR_WINNER"},"bound_gap":{"PASS"},"alternative_formulation":{"PASS"},"ablation":{"PASS"}}[name]
    issues=[]
    if d.get("status") not in allowed: issues.append(f"triggered {name} report status invalid")
    if name=="benchmark":
        calc=summarize_benchmark(d.get("protocol",{}),d.get("runs",[]))
        for key in ("status","winner","method_means","gap","tolerance"):
            if not source_equal(calc.get(key),d.get(key)):
                issues.append(f"benchmark report does not reproduce {key}")
        if calc.get("status")=="PRACTICAL_TIE" and set(calc.get("leaders",[]))!=set(d.get("leaders",[])):
            issues.append("benchmark tie leaders do not reproduce")
        protocol=d.get("protocol",{})
        if d.get("direction",protocol.get("direction"))!=protocol.get("direction"):
            issues.append("benchmark direction contradicts protocol")
        model=base/"model_contract.json"
        if model.is_file() and load_json(model).get("evaluator",{}).get("direction") not in (None,"NOT_APPLICABLE",protocol.get("direction")):
            issues.append("benchmark direction contradicts model evaluator")
        for run in d.get("runs",[]):
            issues.extend(audit_run(base,run.get("run_receipt",""),run.get("output_artifact"))[0])
            output=resolve(base,run.get("output_artifact",""))
            try:
                value=json_pointer(load_json(output),run.get("metric_pointer",""))
                if not source_equal(value,run.get(protocol.get("metric"))):
                    issues.append("benchmark run metric differs from executed output")
            except (OSError,ValueError,KeyError,TypeError,IndexError):
                issues.append("benchmark run has no resolvable executed metric")
        if d.get("statistical_claim"):
            inference=d.get("inference",{})
            if not all(_nonempty(inference.get(k)) for k in ("design","effect","uncertainty","test_assumptions","review_reasoning")) or not validate_hashed_locator(base,inference.get("evidence","")):
                issues.append("statistical superiority needs a substantive statistical analysis, not a mean ranking")
    elif name=="bound_gap":
        if not all(k in d for k in ("direction","bound","achieved_value","gap","gap_tolerance","tolerance_basis","evaluator","result_ids")): issues.append("bound/gap report is incomplete")
        else:
            try:
                bound=float(d["bound"]); achieved=float(d["achieved_value"]); gap=float(d["gap"]); tol=float(d["gap_tolerance"])
                expected=achieved-bound if d.get("direction")=="minimize" else bound-achieved if d.get("direction")=="maximize" else math.nan
                if not all(math.isfinite(x) for x in (bound,achieved,gap,tol)) or expected<0 or gap<0 or tol<0 or abs(gap-expected)>1e-12: issues.append("bound/gap values or direction are invalid")
                if exact_required and gap != 0:
                    issues.append("task requires a certified exact optimum; a positive valid gap is not optimality")
            except Exception: issues.append("bound/gap values are not numeric")
            if not _nonempty(d.get("tolerance_basis")) or not _nonempty(d.get("result_ids")) or not validate_hashed_locator(base,d.get("evaluator","")): issues.append("bound/gap evidence binding is incomplete")
            certificate=d.get("bound_certificate",{})
            if certificate.get("kind")=="EXACT_ENUMERATION":
                cp=resolve(base,certificate.get("artifact",""))
                if not validate_file_binding(base,certificate.get("artifact","")+"@"+certificate.get("sha256","")):
                    issues.append("enumeration bound certificate missing/stale")
                else:
                    c=load_json(cp); domain=c.get("feasible_domain",[]); values=c.get("objective_values",[])
                    if not domain or len(domain)!=len(values) or len({json.dumps(x,sort_keys=True) for x in domain})!=len(domain):
                        issues.append("enumeration bound domain/value coverage invalid")
                    elif not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values) or not source_equal(d.get("bound"),min(values) if d.get("direction")=="minimize" else max(values)):
                        issues.append("enumeration bound not reproduced")
                    issues.extend(audit_run(base,certificate.get("run_receipt",""),certificate.get("artifact"))[0])
                    if not validate_hashed_locator(base,certificate.get("domain_completeness_argument","")):
                        issues.append("enumeration completeness needs an explicit reviewed argument")
            elif certificate.get("kind") in ("REVIEWED_PROOF","SOLVER_CERTIFICATE"):
                for key in ("derivation","feasible_set_relation","review_evidence"):
                    if not validate_hashed_locator(base,certificate.get(key,"")):
                        issues.append(f"bound validity missing {key}; arithmetic gap is not a legal bound")
                if not all(certificate.get(k) for k in ("reviewer","reasoning","scope","limitations")):
                    issues.append("bound certificate lacks substantive scientific review")
            else: issues.append("bound validity certificate required")
            registry=base/"result_registry.json"
            approved={r.get("result_id"):r for r in load_json(registry).get("results",[]) if r.get("approved")} if registry.is_file() else {}
            achieved_records=[approved.get(rid) for rid in d.get("result_ids",[])]
            achieved_values=[x.get("raw_value") for x in achieved_records if x]
            selector=d.get("achieved_source",{})
            if selector:
                try:
                    record=approved[selector["result_id"]]
                    if selector["result_id"] not in d.get("result_ids",[]): raise KeyError("unbound selected result")
                    achieved_values=[json_pointer(record["raw_value"],selector.get("pointer",""))]
                except (KeyError,ValueError,TypeError,IndexError): issues.append("bound achieved source selector invalid")
            if not achieved_records or any(x is None for x in achieved_records) or not any(source_equal(x,d.get("achieved_value")) for x in achieved_values):
                issues.append("bound achieved value does not match approved results")
    elif name=="alternative_formulation":
        if not all(_nonempty(d.get(k)) for k in ("primary_formulation","alternative_formulation","shared_evaluator","agreement_result_ids","boundary")): issues.append("alternative-formulation report is incomplete")
    elif name=="ablation":
        if not all(_nonempty(d.get(k)) for k in ("components","shared_evaluator","result_ids","conclusion","boundary")) or len(d.get("components",[]))<2: issues.append("ablation report is incomplete")
        design=d.get("controlled_design",{})
        if not all(design.get(k) for k in ("changed_components","held_fixed","comparison_units","confounding_limits")) or not validate_hashed_locator(base,design.get("evidence","")):
            issues.append("ablation requires a controlled comparison, not just a result table")
        if d.get("causal_claim") and (not design.get("identification_argument") or not validate_hashed_locator(base,design.get("causal_review",""))):
            issues.append("ablation does not establish causality without identification and review")
    return issues


def audit_conditional_gates(path:Path,claims_path:Path|None=None)->list[str]:
    d=load_json(path); issues=[]; text=""; types=set(); exact_required=False
    if claims_path and claims_path.exists():
        rows=load_csv(claims_path); text=" ".join(r.get("claim_text","") for r in rows if r.get("status")=="PASS").lower(); types={r.get("claim_type","").lower() for r in rows}
    derived={
        "benchmark": bool(types&{"comparative","superiority"} or re.search(r"\b(superior|outperform|best)\b|优于|最佳",text)),
        "bound_gap": bool(types&{"optimality","bound_gap"} or re.search(r"\boptimal\b|最优",text)),
        "ablation": bool(types&{"component_contribution","hybrid_contribution"} or re.search(r"component contribution|组件贡献|模块贡献",text)),
    }
    # Required-output semantics are authoritative even if the author avoids
    # an optimality keyword in the manuscript's claim row.
    question=path.parent/"question_contract.json"
    if question.is_file():
        contract=load_json(question)
        outputs=contract.get("required_outputs",[])
        if not isinstance(outputs,list) or any(not isinstance(x,dict) for x in outputs):
            issues.append("required output semantics must be structured before conditional gating")
        structured=[x for x in outputs if isinstance(x,dict)] if isinstance(outputs,list) else []
        descriptions=" ".join(str(x.get("description","")) for x in structured)
        task=contract.get("task_text_locator","")
        task_path=resolve(path.parent,task.split("#",1)[0]) if "#" in task else None
        task_text=document_text(task_path) if task_path and task_path.is_file() else ""
        exact_required=any(x.get("acceptance_kind")=="CERTIFIED_OPTIMUM" for x in structured)
        exact_required=exact_required or bool(re.search(r"global(?:ly)?\s+(?:minim|maximum|optimum|optimal|maximiz)|全局最优|精确最优",descriptions+" "+task_text,re.I))
        if exact_required: derived["bound_gap"]=True
    for name in ("benchmark","bound_gap","alternative_formulation","ablation"):
        gate=d.get(name,{})
        if derived.get(name,False) and not gate.get("triggered"): issues.append(f"claims require {name}")
        if gate.get("triggered"):
            if not _nonempty(gate.get("reason")) or not gate.get("evidence"): issues.append(f"triggered {name} lacks reason/evidence")
            for spec in gate.get("evidence",[]):
                if not validate_hashed_locator(path.parent,spec): issues.append(f"triggered {name} evidence invalid")
            issues.extend(_gate_report(path.parent,gate,name,exact_required if name=="bound_gap" else False))
        elif not _nonempty(gate.get("reason")): issues.append(f"skipped {name} lacks reason")
    if d.get("benchmark",{}).get("triggered") and len(set(d.get("candidate_methods",[])))<2: issues.append("benchmark requires two distinct candidate methods")
    return issues


def _image_has_visible_content(path:Path)->bool:
    try:
        from PIL import Image, ImageStat
        with Image.open(path) as im:
            gray=im.convert("L"); gray.thumbnail((320,320)); stat=ImageStat.Stat(gray)
            lo,hi=gray.getextrema(); mean=stat.mean[0]; std=stat.stddev[0]
            ink=sum(gray.histogram()[:245])/max(1,gray.width*gray.height)
            return lo<240 and hi>lo and std>1.0 and ink>0.0005 and mean<254.8
    except Exception:
        return False


def audit_page_qa(audit_path:Path)->list[str]:
    d=load_json(audit_path); qa=d.get("page_qa",{}); issues=[]; paper=resolve(audit_path.parent,d.get("paper_artifact",""))
    valid_docx=paper.is_file() and zipfile.is_zipfile(paper)
    if valid_docx:
        try:
            with zipfile.ZipFile(paper) as z: valid_docx="[Content_Types].xml" in z.namelist() and "word/document.xml" in z.namelist()
        except Exception: valid_docx=False
    pdf=read_document(paper) if paper.suffix.lower()=='.pdf' else None
    valid_pdf=pdf is not None and pdf.get('page_count',0) and pdf['status']=='TEXT_READY'
    if pdf is not None and pdf['status']!='TEXT_READY': issues.extend(pdf['issues'])
    if not (valid_docx or valid_pdf) or d.get("paper_sha256")!=(sha256(paper) if paper.is_file() else ""):
        issues.append("paper is not a valid hash-bound DOCX/PDF with reviewable text"); return issues
    if qa.get("status")!="PASS" or qa.get("document_sha256")!=sha256(paper): issues.append("page QA status/hash stale")
    renderer=resolve(audit_path.parent,qa.get("renderer_artifact",""))
    if qa.get("page_size")!="A4" or not _nonempty(qa.get("renderer")) or not renderer.is_file() or qa.get("renderer_sha256")!=(sha256(renderer) if renderer.is_file() else ""): issues.append("page QA lacks A4 renderer provenance")
    render_data={}
    try: render_data=load_json(renderer)
    except Exception: issues.append("renderer artifact must be a structured JSON manifest")
    if render_data:
        input_digest=render_data.get('input_document_sha256')
        if input_digest is None and paper.suffix.lower()=='.docx': input_digest=render_data.get('input_docx_sha256')
        if render_data.get("status")!="PASS" or render_data.get("exit_code")!=0 or input_digest!=sha256(paper) or render_data.get("page_size")!="A4" or not _nonempty(render_data.get("command")) or not _nonempty(render_data.get("tool_versions")): issues.append("renderer manifest does not bind a successful A4 render of this submitted document")
    review=resolve(audit_path.parent,qa.get("manual_review_artifact","")); review_data={}
    if not review.is_file() or qa.get("manual_review_sha256")!=(sha256(review) if review.is_file() else ""): issues.append("page QA lacks hash-bound page review artifact")
    else:
        try: review_data=load_json(review)
        except Exception: issues.append("page review artifact is not JSON")
    if review_data and (review_data.get("paper_sha256")!=sha256(paper) or review_data.get("page_count")!=qa.get("page_count")): issues.append("page review does not bind this paper/page count")
    pages=qa.get("pages",[])
    if qa.get("page_count")!=len(pages) or not pages or [x.get("page") for x in pages]!=list(range(1,len(pages)+1)): issues.append("page coverage is incomplete")
    if pdf is not None:
        if pdf['page_count']!=len(pages): issues.append('submitted PDF page count differs from rendered/reviewed pages')
        if any(abs(w-210*72/25.4)>0.5 or abs(h-297*72/25.4)>0.5 for w,h in pdf['page_sizes_pt']):
            issues.append('submitted PDF media boxes are not A4')
    required={"clipping","captions","equations","tables","readability","pagination"}; render_pages={int(x.get("page",-1)):x for x in render_data.get("page_outputs",[]) if isinstance(x,dict)}; review_pages={int(x.get("page",-1)):x for x in review_data.get("pages",[]) if isinstance(x,dict)}
    if set(render_pages)!=set(range(1,len(pages)+1)): issues.append('renderer output set differs from reviewed page set')
    for rec in pages:
        p=resolve(audit_path.parent,rec.get("image","")); w=rec.get("width_px",0); h=rec.get("height_px",0)
        dims=image_dimensions(p)
        if not dims or rec.get("sha256")!=(sha256(p) if p.is_file() else ""): issues.append(f"page {rec.get('page')} image/hash invalid")
        if not dims or dims!=(w,h) or w<1000 or h<1400 or abs(h/w-297/210)>0.06: issues.append(f"page {rec.get('page')} render is not credible A4")
        if dims and not _image_has_visible_content(p): issues.append(f"page {rec.get('page')} is blank or lacks credible visible content")
        rr=render_pages.get(rec.get("page"),{})
        if not rr or resolve(renderer.parent,rr.get("image",""))!=p or rr.get("sha256")!=(sha256(p) if p.is_file() else ""): issues.append(f"page {rec.get('page')} is not bound by renderer manifest")
        checks=rec.get("checks",{})
        rv=review_pages.get(rec.get("page"),{})
        if set(checks)!=required or any(v!="PASS" for v in checks.values()) or rec.get("manual_status")!="PASS": issues.append(f"page {rec.get('page')} visual QA incomplete")
        if rv.get("image_sha256")!=(sha256(p) if p.is_file() else "") or rv.get("checks")!=checks or rv.get("manual_status")!=rec.get("manual_status") or not _nonempty(rv.get("evidence_note")): issues.append(f"page {rec.get('page')} page-review record is missing or inconsistent")
    if review_data and (review_data.get("overall")!="PASS" or review_data.get("blocking_findings")): issues.append("manual page review has blocking findings")
    return issues


def scientific_artifacts(question_dir:Path)->list[Path]:
    from efficient import scientific_names
    return [question_dir/n for n in scientific_names(question_dir)]


def claim_science_digest(path:Path)->str:
    rows=[]
    for r in load_csv(path): rows.append({k:r.get(k,"") for k in ("claim_id","claim_text","claim_type","required_output_ids","evidence_refs","scope","boundary","status")})
    return hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def audit_manifest_bindings(manifest_path:Path,expected_names:list[str]|None=None)->list[str]:
    d=load_json(manifest_path); issues=[]; art=d.get("artifacts",{})
    if expected_names is not None and set(art)!=set(expected_names): issues.append("frozen artifact set is not exact")
    if not art: issues.append("frozen artifact set is empty")
    for rel,expected in art.items():
        p=resolve(manifest_path.parent,rel)
        if not p.is_file() or sha256(p)!=expected: issues.append(f"stale or missing frozen artifact: {rel}")
    for rel,expected in d.get("external_bindings",{}).items():
        p=resolve(manifest_path.parent,rel)
        if not p.is_file() or sha256(p)!=expected: issues.append(f"stale scientific dependency: {rel}")
    if d.get("status")=="SCIENTIFIC_FROZEN" and (manifest_path.parent/"claim_evidence_map.csv").exists():
        if d.get("scientific_claim_digest")!=claim_science_digest(manifest_path.parent/"claim_evidence_map.csv"): issues.append("scientific claim digest stale")
        try:
            results=load_json(manifest_path.parent/"result_registry.json").get("results",[])
            if d.get("result_ids")!=[r.get("result_id") for r in results]: issues.append("scientific manifest result_ids stale")
            vids=sorted({v.get("id",v.get("artifact","")) for r in results for v in r.get("verification",[])})
            if d.get("verification_ids")!=vids: issues.append("scientific manifest verification_ids stale")
            if d.get("question_id")!=load_json(manifest_path.parent/"question_contract.json").get("question_id"): issues.append("scientific manifest question_id mismatch")
        except Exception: issues.append("scientific manifest registry linkage unreadable")
    return issues


def audit_quality(path:Path,review_dir:Path|None=None)->list[str]:
    d=load_json(path); issues=[]; known={}
    if review_dir and review_dir.exists():
        for p in review_dir.glob("*.json"):
            try: known[load_json(p).get("run_id")]=p
            except Exception: pass
    for name in QUALITY:
        rec=d.get("dimensions",{}).get(name)
        if not isinstance(rec,dict): issues.append(f"missing quality dimension {name}"); continue
        if rec.get("status")!="PASS": issues.append(f"quality dimension {name} is not PASS")
        if not rec.get("evidence_locators") or not rec.get("reviewer_run_ids"): issues.append(f"quality dimension {name} lacks evidence/reviewer provenance")
        for loc in rec.get("evidence_locators",[]):
            if not validate_hashed_locator(path.parent,loc): issues.append(f"quality {name} evidence invalid")
        for run in rec.get("reviewer_run_ids",[]):
            if review_dir and (run not in known or audit_reviewer_report(known[run])): issues.append(f"quality {name} reviewer run invalid: {run}")
    return issues


def audit_development(path:Path)->list[str]:
    d=load_json(path); issues=[]
    for name in ("derivation_sufficiency","method_exposition","evidence_promotion","formula_architecture","table_architecture","result_interpretation","writing_quality"):
        rec=d.get(name,{}); status=rec.get("status")
        if status=="PASS":
            ev=rec.get("evidence_locators",rec.get("scanned_roots",[]))
            if not ev: issues.append(f"development item {name} lacks evidence")
            for loc in ev:
                if not validate_hashed_locator(path.parent,loc): issues.append(f"development item {name} evidence invalid")
        elif status=="NOT_APPLICABLE":
            if not _nonempty(rec.get("reason")): issues.append(f"development item {name} N/A lacks reason")
        else: issues.append(f"development item {name} unresolved")
    hero=d.get("hero_figure_attempt",{})
    if hero.get("status") not in ("ADOPTED","REJECTED_WITH_REASON","NOT_APPLICABLE") or not _nonempty(hero.get("reason")): issues.append("hero figure attempt unresolved")
    peer=d.get("peer_gap",{})
    if peer.get("status")=="PASS":
        if not peer.get("comparison_sources") or not peer.get("disposition"): issues.append("peer gap PASS lacks sources/disposition")
    elif peer.get("status")=="NOT_APPLICABLE":
        if not _nonempty(peer.get("reason")): issues.append("peer gap N/A lacks reason")
    else: issues.append("peer gap unresolved")
    return issues


def audit_resource_consumption(path:Path,result_registry:Path|None=None,require_nonempty:bool=False)->list[str]:
    rows=load_csv(path);issues=[]
    if require_nonempty and not rows:issues.append("delivered visual/table evidence lacks resource consumption")
    valid_results={r.get("result_id") for r in load_json(result_registry).get("results",[])} if result_registry and result_registry.exists() else set()
    for i,r in enumerate(rows,2):
        for k in ("capability_id","resource_kind","resource_path","source_sha256","reason","actual_interface","input_bindings","output_bindings","exit_code","excluded_legacy_policies","validation_evidence","semantic_review_status"):
            if not _nonempty(r.get(k)): issues.append(f"resource row {i} missing {k}")
        p=resolve(path.parent,r.get("resource_path",""))
        if not p.is_file() or r.get("source_sha256")!=(sha256(p) if p.is_file() else ""): issues.append(f"resource row {i} source/hash invalid")
        if r.get("resource_kind") not in ("LEGACY_SKILL","PROJECT_CODE","SYSTEM_TOOL") or r.get("actual_interface","").lower() in ("none","unknown","n/a"):issues.append(f"resource row {i} identity/interface invalid")
        for spec in [x.strip() for x in r.get("input_bindings","").split(";") if x.strip()]:
            if not validate_file_binding(path.parent,spec):issues.append(f"resource row {i} input binding invalid")
        for spec in [x.strip() for x in r.get("output_bindings","").split(";") if x.strip()]:
            if not validate_file_binding(path.parent,spec):issues.append(f"resource row {i} output binding invalid")
        ids=[x.strip() for x in r.get("result_ids","").split(";") if x.strip()]
        if ids and (result_registry is None or any(x not in valid_results for x in ids)):issues.append(f"resource row {i} result IDs invalid")
        if r.get("exit_code")!="0" or r.get("semantic_review_status")!="PASS": issues.append(f"resource row {i} execution/review failed")
        if not validate_hashed_locator(path.parent,r.get("validation_evidence","")): issues.append(f"resource row {i} validation evidence invalid")
    return issues


def audit_visual_semantics(path:Path,figure_path:Path|None=None)->list[str]:
    d=load_json(path); issues=[]
    if d.get("status")!="PASS": issues.append("visual semantics unresolved")
    if not d.get("semantics"): issues.append("visual semantics empty")
    for name,rec in d.get("semantics",{}).items():
        if not all(k in rec for k in ("color","line","marker")): issues.append(f"visual semantic {name} incomplete"); continue
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}",str(rec.get("color",""))) or rec.get("line") not in ("none","-","--","-.",":") or rec.get("marker") not in ("none","o","s","^","v","D","x","+"): issues.append(f"visual semantic {name} invalid")
    if d.get("accessibility",{}).get("grayscale_checked") is not True: issues.append("grayscale semantics not checked")
    if figure_path and figure_path.exists():
        roles={r.get("role") for r in load_csv(figure_path) if r.get("status")=="DELIVERED"}
        if "SCENARIO" in roles and not d.get("scenario_semantics"): issues.append("scenario figures lack scenario semantics")
        if roles & {"BENCHMARK","ABLATION","DATA_STRUCTURE"} and not d.get("group_semantics"): issues.append("group-comparison figures lack group semantics")
    return issues


def audit_tables(path:Path)->list[str]:
    issues=[]
    for i,r in enumerate(load_csv(path),2):
        if r.get("status")=="NOT_APPLICABLE":
            if not r.get("status_reason"): issues.append(f"table row {i} N/A lacks reason")
            continue
        for k in ("table_id","question_id","role","message","data_source","data_source_sha256","importance","status"):
            if not _nonempty(r.get(k)): issues.append(f"table row {i} missing {k}")
        src=resolve(path.parent,r.get("data_source",""))
        if not src.is_file() or r.get("data_source_sha256")!=(sha256(src) if src.is_file() else ""): issues.append(f"table row {i} source/hash invalid")
        if r.get("status")=="DELIVERED":
            if not validate_text_locator(path.parent,r.get("output_locator","")): issues.append(f"table row {i} output locator invalid")
        else: issues.append(f"table row {i} unresolved")
    return issues


EVIDENCE_SCAN_EXCLUDED={"scientific_manifest.json","research_manifest.json","competitive_development.json"}


def evidence_scan_candidates(root:Path,output:Path)->list[Path]:
    from efficient import is_efficient, evidence_dependencies
    if is_efficient(root):
        return [p for p in evidence_dependencies(root) if p.resolve()!=output.resolve()]
    out=output.resolve()
    return sorted(x for x in root.rglob("*") if x.is_file() and x.resolve()!=out and x.name not in EVIDENCE_SCAN_EXCLUDED and "__pycache__" not in x.parts and x.suffix.lower() in {".json",".csv",".png",".jpg",".jpeg",".svg",".pdf",".md",".py"})


def audit_evidence_promotion(path:Path,development_path:Path)->list[str]:
    status=load_json(development_path).get("evidence_promotion",{}).get("status"); rows=load_csv(path); issues=[]
    if status=="PASS" and not rows: return ["evidence promotion PASS without a saved-artifact scan"]
    if status=="NOT_APPLICABLE": return []
    if status!="PASS": return ["evidence promotion unresolved"]
    scanned=load_json(development_path).get("evidence_promotion",{}).get("scanned_roots",[])
    if "." not in scanned: issues.append("evidence promotion PASS lacks complete question-root scan declaration")
    expected={str(x.relative_to(path.parent)) for x in evidence_scan_candidates(path.parent,path)}
    actual={r.get("artifact","") for r in rows}
    if actual!=expected: issues.append("evidence promotion inventory is incomplete or contains undeclared artifacts")
    for i,r in enumerate(rows,2):
        art=resolve(path.parent,r.get("artifact",""))
        if not art.is_file() or r.get("locator")!=f"sha256:{sha256(art)}": issues.append(f"evidence promotion row {i} artifact/hash invalid")
        if r.get("decision") not in ("PROMOTE","KEEP_SUPPORTING","DROP_WITH_REASON") or not _nonempty(r.get("reason")): issues.append(f"evidence promotion row {i} unresolved")
    return issues


def audit_scientific(question_dir:Path,expected_version:int|None=None)->list[str]:
    issues=[]
    for p in scientific_artifacts(question_dir):
        if not p.exists(): issues.append(f"missing {p.name}")
    claims=question_dir/"claim_evidence_map.csv"
    if not claims.exists(): issues.append("missing claim_evidence_map.csv")
    if issues: return issues
    for label,fn,p in (("question",audit_question_contract,question_dir/"question_contract.json"),("domain",audit_domain_map,question_dir/"domain_model_map.json"),("model",audit_model_contract,question_dir/"model_contract.json"),("uncertainty",audit_uncertainty,question_dir/"uncertainty_budget.json")):
        issues.extend(f"{label}: {x}" for x in fn(p))
    issues.extend(f"alignment: {x}" for x in audit_contract_alignment(question_dir/"question_contract.json",question_dir/"model_contract.json"))
    if expected_version is not None and load_json(question_dir/"model_contract.json").get("evaluator",{}).get("scientific_version")!=expected_version: issues.append("model evaluator scientific_version mismatch")
    allow_empty=bool(load_json(question_dir/"question_contract.json").get("allow_no_result"))
    issues.extend(f"results: {x}" for x in audit_result_registry(question_dir/"result_registry.json",expected_version,allow_empty))
    if (question_dir/"literature_to_model_map.csv").is_file():
        issues.extend(f"literature: {x}" for x in audit_literature_map(question_dir/"literature_to_model_map.csv",question_dir/"domain_model_map.json"))
    issues.extend(f"conditional: {x}" for x in audit_conditional_gates(question_dir/"conditional_gates.json",claims))
    mc=load_json(question_dir/"model_contract.json")
    issues.extend(f"assumptions: {x}" for x in audit_assumptions(question_dir/"assumption_ledger.csv",mc.get("assumption_closure_reason")))
    issues.extend(f"claims: {x}" for x in audit_claims(claims,question_dir/"result_registry.json",False))
    issues.extend(f"coverage: {x}" for x in audit_output_coverage(question_dir/"question_contract.json",question_dir/"result_registry.json",claims))
    return issues


def audit_research_manifest(question_dir:Path)->list[str]:
    p=question_dir/"research_manifest.json"
    if not p.exists(): return ["research manifest missing"]
    d=load_json(p); issues=[]
    if d.get("status")!="RESEARCH_FROZEN": issues.append("research manifest is not current RESEARCH_FROZEN")
    sm=question_dir/"scientific_manifest.json"
    if not sm.is_file() or d.get("scientific_manifest_sha256")!=(sha256(sm) if sm.is_file() else ""): issues.append("research manifest scientific binding stale")
    expected=RESEARCH_NAMES+[str(x.relative_to(question_dir)) for x in sorted((question_dir/"reviews").glob("*.json"))]
    issues.extend(audit_manifest_bindings(p,expected))
    reports=[load_json(x) for x in sorted((question_dir/"reviews").glob("*.json"))]
    if d.get("review_run_ids")!=[x.get("run_id") for x in reports]: issues.append("research manifest reviewer run IDs stale")
    if d.get("content_sufficiency")!="APPROPRIATE": issues.append("research manifest content status invalid")
    if any(d.get("quality",{}).get(k)!="PASS" for k in QUALITY): issues.append("research manifest quality snapshot invalid")
    return issues


def audit_research(question_dir:Path,require_frozen:bool=False)->list[str]:
    from efficient import is_efficient, audit_acceptance
    if is_efficient(question_dir):
        return audit_acceptance(question_dir, require_frozen)
    sm=question_dir/"scientific_manifest.json"; issues=[]
    if not sm.exists() or load_json(sm).get("status")!="SCIENTIFIC_FROZEN": issues.append("valid Scientific Freeze required")
    else: issues.extend(audit_manifest_bindings(sm,SCIENTIFIC_NAMES))
    expected_version=load_json(sm).get("scientific_version") if sm.exists() else None
    issues.extend(audit_scientific(question_dir,expected_version))
    for n in RESEARCH_NAMES:
        if not (question_dir/n).exists(): issues.append(f"missing {n}")
    if any(x.startswith("missing") for x in issues): return issues
    issues.extend(f"claims presentation: {x}" for x in audit_claims(question_dir/"claim_evidence_map.csv",question_dir/"result_registry.json",True))
    status,local=audit_content(question_dir/"content_units.csv",question_dir)
    if status!="APPROPRIATE": issues.append(f"content is {status}")
    issues.extend(f"content: {x}" for x in local)
    family=load_json(question_dir/"domain_model_map.json").get("domain_family","")
    fs,local=audit_figures(question_dir/"figure_candidates.csv",family,question_dir/"result_registry.json")
    if fs!="PASS": issues.append("visual quality is FAIL")
    issues.extend(f"visual: {x}" for x in local)
    delivered_figures=any(r.get("status")=="DELIVERED" for r in load_csv(question_dir/"figure_candidates.csv")); delivered_tables=any(r.get("status")=="DELIVERED" for r in load_csv(question_dir/"table_portfolio.csv"))
    issues.extend(f"resource: {x}" for x in audit_resource_consumption(question_dir/"resource_consumption.csv",question_dir/"result_registry.json",delivered_figures or delivered_tables))
    issues.extend(f"visual semantics: {x}" for x in audit_visual_semantics(question_dir/"visual_semantics.json",question_dir/"figure_candidates.csv"))
    issues.extend(f"table: {x}" for x in audit_tables(question_dir/"table_portfolio.csv"))
    issues.extend(f"evidence promotion: {x}" for x in audit_evidence_promotion(question_dir/"evidence_promotion.csv",question_dir/"competitive_development.json"))
    review_dir=question_dir/"reviews"
    if not review_dir.exists(): issues.append("missing reviewer reports")
    else: issues.extend(f"review: {x}" for x in audit_reviewers(review_dir))
    issues.extend(f"development: {x}" for x in audit_development(question_dir/"competitive_development.json"))
    issues.extend(f"quality: {x}" for x in audit_quality(question_dir/"quality_assessment.json",review_dir))
    if require_frozen: issues.extend(f"research manifest: {x}" for x in audit_research_manifest(question_dir))
    return issues


def audit_paper_numeric_map(path:Path,paper:Path,question_dirs:list[Path])->list[str]:
    registries={}; duplicates=set()
    for qd in question_dirs:
        for r in load_json(qd/"result_registry.json").get("results",[]):
            if r["result_id"] in registries: duplicates.add(r["result_id"])
            registries[r["result_id"]]=r
    issues=[]; rows=load_csv(path)
    if duplicates: issues.append("duplicate Result Registry IDs across questions: "+",".join(sorted(duplicates)))
    if not rows and scientific_numeric_tokens(document_text(paper)):
        return ["paper scientific numeric map is empty"]
    mapped=[]; paper_resolved=paper.resolve(); text=document_text(paper)
    for i,r in enumerate(rows,2):
        loc=r.get("paper_locator",""); rel=loc.split("#",1)[0] if "#" in loc else ""
        if r.get("status")!="PASS" or not validate_text_locator(path.parent,loc,r.get("paper_sha256","")) or resolve(path.parent,rel)!=paper_resolved: issues.append(f"numeric row {i} paper binding invalid")
        if r.get("displayed_value") not in loc.split("#",1)[-1]: issues.append(f"numeric row {i} locator does not identify displayed value")
        kind=r.get("source_kind")
        if kind=="RESULT_REGISTRY":
            rec=registries.get(r.get("source_id"))
            if not rec or str(rec.get("display_value"))!=r.get("source_display_value") or r.get("displayed_value")!=r.get("source_display_value"): issues.append(f"numeric row {i} does not match Result Registry")
        elif kind=="APPROVED_SOURCE":
            if not validate_hashed_locator(path.parent,r.get("source_evidence","")) or r.get("displayed_value")!=r.get("source_display_value"): issues.append(f"numeric row {i} approved source binding invalid")
        else: issues.append(f"numeric row {i} source_kind invalid")
        mapped.append(r.get("displayed_value",""))
    tokens=scientific_numeric_tokens(text)
    if any(token not in mapped for token in tokens): issues.append("paper contains unmapped numeric tokens: "+",".join(sorted(set(t for t in tokens if t not in mapped))))
    return issues


def scientific_numeric_tokens(text:str)->list[str]:
    """Conservative scope filter, not an automatic claim-meaning classifier.

    Exclude only recognizable structural tokens; unknown prose numbers stay in
    scope. Years in result/parameter statements are not globally whitelisted.
    """
    values=[]
    key=re.compile(r"result|estimate|parameter|objective|accuracy|error|value|结果|估计|参数|目标值|误差|准确率|时长|功率",re.I)
    for line in text.splitlines():
        line=re.sub(r"^\s*(?:#{1,6}\s*)?\d+(?:\.\d+)*[、.\s]+(?=[A-Za-z\u4e00-\u9fff])","",line)
        line=re.sub(r"(?:图|表|式|章节|Figure|Table|Eq\.?|Section)\s*\(?\d+(?:\.\d+)*\)?","",line,flags=re.I)
        if not key.search(line):
            line=re.sub(r"\b(?:19|20)\d{2}(?:年|\s*(?:CUMCM|全国大学生数学建模竞赛))","",line,flags=re.I)
            line=re.sub(r"\[(?:\d+(?:\s*[-,]\s*\d+)*)\]","",line)
            # Named definition/formula constants are mathematical notation,
            # not numerical research claims. Equation outputs are still mapped
            # when the surrounding line explicitly calls them results.
            if re.search(r"^(?:\s*\$|\s*公式|\s*定义|\s*Eq\.?|\s*constant\b)",line,re.I): continue
        values.extend(re.findall(r"(?<![A-Za-z_])[-+]?(?:\d+\.\d+|\d+)(?:[eE][-+]?\d+)?%?",line))
    return values


def audit_whole_problem_map(path:Path,question_dirs:list[Path])->list[str]:
    d=load_json(path); issues=[]; qid_to_dir={load_json(q/"question_contract.json").get("question_id"):q.resolve() for q in question_dirs}; qids=set(qid_to_dir)
    declared={x.get("question_id") for x in d.get("questions",[]) if isinstance(x,dict)}
    if d.get("status")!="PASS": issues.append("whole_problem_map is not PASS")
    if declared!=qids: issues.append("whole_problem_map question set disagrees with audit scope")
    for rec in d.get("questions",[]):
        qid=rec.get("question_id"); p=resolve(path.parent,rec.get("path",""))
        if qid not in qid_to_dir or p!=qid_to_dir.get(qid): issues.append(f"whole_problem_map path mismatch for {qid}")
    for name in ("research_roles","evidence_priorities","writing_priorities"):
        values=d.get(name,{})
        if set(values)!=qids or any(not _nonempty(v) for v in values.values()): issues.append(f"whole_problem_map {name} incomplete")
    edges=[]
    for dep in d.get("dependencies",[]):
        u=dep.get("from",dep.get("upstream"));v=dep.get("to",dep.get("downstream"))
        if u not in qids or v not in qids: issues.append("dependency references unknown question")
        edges.append((u,v))
    graph=defaultdict(list)
    for u,v in edges: graph[u].append(v)
    visiting=set();done=set()
    def visit(x):
        if x in visiting:return False
        if x in done:return True
        visiting.add(x)
        for y in graph[x]:
            if not visit(y):return False
        visiting.remove(x);done.add(x);return True
    if any(not visit(x) for x in qids): issues.append("question dependency graph has a cycle")
    required={"models_evaluators","assumptions","symbols_units","claims_results"};checks={x.get("category"):x for x in d.get("consistency_checks",[]) if isinstance(x,dict)}
    if set(checks)!=required: issues.append("whole-problem consistency checks incomplete")
    for name,rec in checks.items():
        if rec.get("status")!="PASS" or not validate_hashed_locator(path.parent,rec.get("evidence_locator","")): issues.append(f"whole-problem consistency {name} invalid")
    locators=[x.get("evidence_locator") for x in checks.values()]
    from efficient import is_efficient
    if any(is_efficient(q) for q in question_dirs):
        if any(not rec.get("reasoning") for rec in checks.values()):
            issues.append("whole-problem consistency requires actual judgments, not duplicated PASS labels")
    elif len(locators)!=len(set(locators)): issues.append("whole-problem consistency categories lack distinct evidence")
    for group in ("shared_models","shared_evaluators"):
        for rec in d.get(group,[]):
            bindings=rec.get("question_hashes",{})
            if len(bindings)<2 or not set(bindings).issubset(qids): issues.append(f"{group} reusable object lacks multi-question bindings")
            if len(set(bindings.values()))>1 and not _nonempty(rec.get("relationship")): issues.append(f"{group} differing versions lack relationship explanation")
            for qid,digest in bindings.items():
                qd=qid_to_dir.get(qid)
                if not qd: continue
                if group=="shared_models": expected=sha256(qd/"model_contract.json") if (qd/"model_contract.json").is_file() else ""
                else:
                    model=load_json(qd/"model_contract.json") if (qd/"model_contract.json").is_file() else {}; ep=resolve(qd,model.get("evaluator",{}).get("artifact","")); expected=sha256(ep) if ep.is_file() else ""
                if digest!=expected: issues.append(f"{group} hash mismatch for {qid}")
    return issues


def audit_numbering_registry(path:Path)->list[str]:
    try:d=load_json(path)
    except Exception:return ["numbering_registry unreadable"]
    issues=[]; seen_ids=set(); seen_numbers=set(); maxima=defaultdict(int)
    for rec in d.get("allocations",[]):
        sid=rec.get("stable_id"); kind=rec.get("kind"); number=rec.get("number")
        if not _nonempty(sid) or kind not in ("equation","figure","table","algorithm") or not isinstance(number,int) or number<=0: issues.append("invalid numbering allocation"); continue
        if sid in seen_ids or (kind,number) in seen_numbers: issues.append("duplicate numbering allocation")
        seen_ids.add(sid); seen_numbers.add((kind,number)); maxima[kind]=max(maxima[kind],number)
    counters=d.get("counters",{})
    for kind in ("equation","figure","table","algorithm"):
        if not isinstance(counters.get(kind),int) or counters.get(kind)<maxima[kind]: issues.append(f"numbering counter invalid: {kind}")
    return issues


def audit_symbol_registry(path:Path)->list[str]:
    try:d=load_json(path)
    except Exception:return ["symbol_registry unreadable"]
    issues=[]; seen={}
    for rec in d.get("symbols",[]):
        symbol=rec.get("symbol"); meaning=rec.get("meaning"); unit=rec.get("unit")
        if not all(_nonempty(x) for x in (symbol,meaning,unit)): issues.append("symbol registry entry incomplete"); continue
        sig=(meaning,unit)
        if symbol in seen and seen[symbol]!=sig: issues.append(f"symbol conflict: {symbol}")
        seen[symbol]=sig
    return issues


def audit_figure_portfolio(path:Path,question_dirs:list[Path])->list[str]:
    rows=load_csv(path); issues=[]; expected={}; qmap={load_json(q/"question_contract.json").get("question_id"):q for q in question_dirs}
    for qid,qd in qmap.items():
        for rec in load_csv(qd/"figure_candidates.csv"):
            if rec.get("status") in ("DELIVERED","EQUIVALENT"): expected[(qid,rec.get("figure_id"))]=rec
    actual={(r.get("question_id"),r.get("figure_id")):r for r in rows}
    if set(actual)!=set(expected): issues.append("figure_portfolio does not exactly match question figure evidence")
    for key,row in actual.items():
        src=expected.get(key)
        if not src: continue
        if row.get("role")!=src.get("role") or row.get("status")!=src.get("status") or row.get("output_path")!=src.get("output_path") or row.get("paper_locator")!=src.get("paper_locator"): issues.append(f"figure_portfolio mismatch: {key}")
        qd=qmap[key[0]]; rm=qd/"research_manifest.json"
        if not validate_file_binding(path.parent,row.get("source_manifest","")) or resolve(path.parent,row.get("source_manifest","").rsplit("@",1)[0])!=rm.resolve(): issues.append(f"figure_portfolio manifest binding invalid: {key}")
    return issues


def audit_paper(audit_path:Path)->list[str]:
    d=load_json(audit_path); base=audit_path.parent; issues=[]
    paper=resolve(base,d.get("paper_artifact","")); qdirs=[resolve(base,x) for x in d.get("question_dirs",[])]
    if not qdirs: issues.append("whole-paper audit has no question directories")
    for qd in qdirs: issues.extend(f"{qd.name}: {x}" for x in audit_research(qd,True))
    whole=base/"whole_problem_map.json"
    if not whole.is_file(): issues.append("whole_problem_map missing")
    else: issues.extend(f"whole map: {x}" for x in audit_whole_problem_map(whole,qdirs))
    ps=resolve(base,d.get("project_state",""))
    if not ps.is_file(): issues.append("project_state missing")
    else:
        state=load_json(ps); scope={load_json(q/"question_contract.json").get("question_id"):q for q in qdirs}; records=state.get("questions",{})
        if set(records)!=set(scope): issues.append("project_state question set disagrees with audit scope")
        for qid,qd in scope.items():
            rec=records.get(qid,{}); sm=load_json(qd/"scientific_manifest.json") if (qd/"scientific_manifest.json").is_file() else {}; rm=load_json(qd/"research_manifest.json") if (qd/"research_manifest.json").is_file() else {}
            if rec.get("status")!="RESEARCH_FROZEN" or rec.get("scientific_version")!=sm.get("scientific_version") or rec.get("research_version")!=rm.get("research_version"): issues.append(f"project_state snapshot mismatch for {qid}")
        if whole.is_file():
            def edges(items): return {(x.get("from",x.get("upstream")),x.get("to",x.get("downstream"))) for x in items}
            if edges(state.get("dependencies",[]))!=edges(load_json(whole).get("dependencies",[])): issues.append("project_state dependencies disagree with whole_problem_map")
    for name,fn in (("numbering_registry.json",audit_numbering_registry),("symbol_registry.json",audit_symbol_registry)):
        gp=base/name
        if not gp.is_file(): issues.append(f"{name} missing")
        else: issues.extend(f"{name}: {x}" for x in fn(gp))
    fp=base/"figure_portfolio.csv"
    if not fp.is_file(): issues.append("figure_portfolio.csv missing")
    else: issues.extend(f"figure portfolio: {x}" for x in audit_figure_portfolio(fp,qdirs))
    units={}
    for qd in qdirs:
        model=load_json(qd/"model_contract.json")
        for group in ("inputs","outputs","variables","parameters"):
            for rec in model.get(group,[]):
                name=rec.get("id",rec.get("name")); unit=rec.get("unit")
                if name in units and units[name]!=unit: issues.append(f"cross-question unit conflict for {name}")
                units[name]=unit
    budget=base/"page_budget.json"
    if not budget.is_file(): issues.append("page_budget missing")
    else: issues.extend(f"page budget: {x}" for x in audit_page_budget(budget))
    num=resolve(base,d.get("paper_numeric_map",""))
    if not num.is_file(): issues.append("paper numeric map missing")
    elif paper.is_file(): issues.extend(audit_paper_numeric_map(num,paper,qdirs))
    issues.extend(audit_page_qa(audit_path))
    if d.get("content_sufficiency")!="APPROPRIATE": issues.append("whole-paper content is not APPROPRIATE")
    if d.get("scientific_consistency")!="PASS": issues.append("whole-paper scientific consistency is not PASS")
    for name in QUALITY:
        if d.get("quality",{}).get(name)!="PASS": issues.append(f"whole-paper quality {name} is not PASS")
    from efficient import is_efficient
    if any(is_efficient(q) for q in qdirs):
        from contest_rules import audit_delivery
        rule_profile=resolve(base,d.get("contest_rule_profile","contest_rule_profile.json"))
        if not rule_profile.is_file(): issues.append("annual contest_rule_profile missing")
        elif paper.is_file():
            issues.extend("delivery: "+x for x in audit_delivery(rule_profile,paper))
            if budget.is_file():
                page=load_json(budget); rules=load_json(rule_profile)
                if page.get("target_competition_year")!=rules.get("competition_year"):
                    issues.append("annual rule profile and page budget years disagree")
                hard=page.get("hard_page_compliance",{})
                if hard.get("status")!="VERIFIED" or hard.get("total_page_limit")!=rules.get("rules",{}).get("main_text_page_limit"):
                    issues.append("final official page policy unresolved or inconsistent")
        whole_review=resolve(base,d.get("whole_research_review",""))
        if not whole_review.is_file(): issues.append("actual integrated whole-paper review missing")
        else:
            wr=load_json(whole_review)
            if wr.get("paper_sha256")!=(sha256(paper) if paper.is_file() else "") or wr.get("outcome")!="ACCEPTED" or not wr.get("reviewer"):
                issues.append("whole-paper substantive review stale or unresolved")
            for key in ("mathematical_consistency","research_sufficiency","claim_strength","visual_portfolio","contest_competitiveness","official_compliance"):
                finding=wr.get("findings",{}).get(key,{})
                if not finding.get("reasoning") or finding.get("outcome")!="ACCEPTED" or not validate_hashed_locator(whole_review.parent,finding.get("evidence","")):
                    issues.append("whole-paper real assessment missing: "+key)
            report=wr.get("whole_visual_report","")
            if not validate_file_binding(whole_review.parent,report):
                issues.append("Whole-Paper Final Visual Audit report missing/stale")
            else:
                report_path=resolve(whole_review.parent,report.rsplit("@",1)[0])
                if "Status: REVIEWED" not in document_text(report_path):
                    issues.append("whole visual inventory is not an actual reviewed portfolio")
    return issues
