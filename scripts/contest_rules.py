"""Annual official-rule bindings + deterministic DOCX/delivery checks.

Rules are supplied per competition year, not hard-coded from a past contest.
Anonymous identity leaks, references, substantive AI review and ambiguous clause
interpretations still require attributed human inspection.
"""
from __future__ import annotations
import re
import zipfile
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from pathlib import Path


def audit_delivery(profile_path: Path, paper: Path):
    from core import load_json, resolve, validate_hashed_locator, validate_file_binding, document_text, read_document
    d=load_json(profile_path); base=profile_path.parent; issues=[]
    if d.get("status")!="VERIFIED" or not isinstance(d.get("competition_year"),int):
        return ["annual official rule profile not verified"]
    if d.get("verified_for_year")!=d.get("competition_year") or not d.get("checked_at"):
        issues.append("rule verification year/date missing or mismatched")
    sources=d.get("sources",[])
    if not {x.get("kind") for x in sources}.issuperset({"FORMAT","PARTICIPATION","AI"}):
        issues.append("official format, participation and AI rule sources required")
    for source in sources:
        host=urlparse(source.get("url","")).hostname or ""
        if host not in ("www.mcm.edu.cn","mcm.edu.cn","en.mcm.edu.cn"):
            issues.append("rule source must be official CUMCM or explicitly resolve official provenance")
        if source.get("year")!=d.get("competition_year") or not validate_hashed_locator(base,source.get("binding","")):
            issues.append("official source year/content binding invalid")
    rules=d.get("rules",{}); layout=rules.get("layout",{})
    interpretation=d.get("rule_interpretation",{})
    if not interpretation.get("reviewer") or not interpretation.get("reasoning") or not validate_hashed_locator(base,interpretation.get("evidence","")):
        issues.append("actual official clauses require an attributed interpretation, not a VERIFIED label")
    if d.get("ai_used") not in (True,False):
        issues.append("AI usage state unresolved")
    if paper.suffix.lower() not in rules.get("allowed_paper_suffixes",[]):
        issues.append("paper file format violates verified annual rule")
    max_bytes=rules.get("max_paper_bytes")
    if not isinstance(max_bytes,int) or max_bytes<=0 or not paper.is_file() or paper.stat().st_size>max_bytes:
        issues.append("paper size/rule unresolved or exceeded")
    if paper.suffix.lower()==".docx" and zipfile.is_zipfile(paper):
        ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}; w="{"+ns["w"]+"}"
        with zipfile.ZipFile(paper) as z:
            root=ET.fromstring(z.read("word/document.xml")); sections=root.findall(".//w:sectPr",ns)
            if not sections: issues.append("DOCX section layout missing")
            for section in sections:
                size=section.find("w:pgSz",ns); margins=section.find("w:pgMar",ns)
                if size is None or margins is None: issues.append("DOCX page size/margins missing"); continue
                expected=layout.get("page_twips",[])
                actual=[int(size.get(w+"w","0")),int(size.get(w+"h","0"))]
                if len(expected)!=2 or any(abs(x-y)>2 for x,y in zip(expected,actual)):
                    issues.append("DOCX page dimensions differ from verified official layout")
                minimum=layout.get("minimum_margin_twips")
                if not isinstance(minimum,int) or any(int(margins.get(w+k,"0"))<minimum for k in ("top","bottom","left","right")):
                    issues.append("DOCX margins below verified official minimum")
    elif paper.suffix.lower()==".pdf":
        if not paper.is_file() or not paper.read_bytes().startswith(b"%PDF"):
            issues.append("paper PDF invalid")
        if not validate_file_binding(base,d.get("pdf_layout_review","")):
            issues.append("PDF requires actual render/layout inspection")
        pdf=read_document(paper)
        issues.extend(pdf['issues'])
        expected=layout.get('page_twips',[])
        if len(expected)!=2 or any(any(abs(size[i]-expected[i]/20)>0.5 for i in (0,1)) for size in pdf['page_sizes_pt']):
            issues.append('PDF media boxes differ from verified annual layout')
        if d.get('actual_page_counts',{}).get('total')!=pdf.get('page_count'):
            issues.append('submitted PDF total page count must match its actual pages')
    else: issues.append("valid Word/PDF document required")
    counts=d.get("actual_page_counts",{}); limit=rules.get("main_text_page_limit")
    if not isinstance(limit,int) or limit<=0 or not isinstance(counts.get("main_text"),int):
        issues.append("main-text page count and official limit must be established from final rendering")
    elif counts["main_text"]>limit: issues.append("official main-text page limit exceeded")
    if not validate_file_binding(base,d.get("page_count_evidence","")):
        issues.append("actual section page counts not bound to render/review evidence")
    try: text=document_text(paper)
    except (ValueError,OSError) as e:
        issues.append('submitted document text review incomplete: '+str(e)); text=''
    for token in d.get("identity_tokens",[]):
        if token and token in text: issues.append("possible anonymous identity leak: "+token)
    for key in ("anonymous_review","reference_review","electronic_structure_review","support_inventory_review"):
        if not validate_hashed_locator(base,d.get(key,"")):
            issues.append("substantive final compliance inspection missing: "+key)
    support=resolve(base,d.get("support_artifact",""))
    if d.get("support_required"):
        if not support.is_file() or support.suffix.lower() not in rules.get("allowed_support_suffixes",[]) or support.stat().st_size>rules.get("max_support_bytes",0):
            issues.append("support archive format/size invalid")
        elif support.suffix.lower()==".zip":
            if not zipfile.is_zipfile(support): issues.append("support ZIP invalid")
            else:
                with zipfile.ZipFile(support) as z:
                    names=z.namelist()
                    if not any(x.endswith(tuple(rules.get("source_code_suffixes",[".py",".m"]))) for x in names) and not d.get("no_program_reason"):
                        issues.append("runnable source code not present in support archive")
                    if d.get("ai_used") and rules.get("ai_detail_filename") not in {Path(x).name for x in names}:
                        issues.append("official AI-detail PDF missing from support archive")
                    for token in d.get("identity_tokens",[]):
                        if any(token in name for name in names): issues.append("support filename identity leak")
    ai=d.get("ai_usage",{})
    if d.get("ai_used"):
        for key in ("tools_and_models","purposes","prompt_process","adoption_and_human_verification"):
            if not ai.get(key): issues.append("official AI usage information missing: "+key)
        if not validate_hashed_locator(base,ai.get("human_review_evidence","")):
            issues.append("team-led, actual human verification must be recorded")
    if not validate_hashed_locator(base,d.get("ai_declaration_evidence","")):
        issues.append("annual AI declaration placement/content review missing")
    return issues
