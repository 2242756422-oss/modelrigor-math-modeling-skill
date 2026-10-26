#!/usr/bin/env python3
"""Bind the submitted DOCX/PDF, real render and attributed page inspection.

An AI visual inspection is not an independent human/team contest approval.
The reviewer record must identify the actual inspection source and its limits.
"""
from __future__ import annotations
import sys; sys.dont_write_bytecode=True
import argparse, json, shutil, tempfile
from pathlib import Path
from core import audit_page_qa, image_dimensions, load_json, sha256

p=argparse.ArgumentParser(); p.add_argument("--paper",type=Path,required=True,help='actual submitted DOCX or PDF'); p.add_argument("--render-dir",type=Path,required=True); p.add_argument("--renderer-artifact",type=Path,required=True,help="actual structured render manifest binding this submitted file"); p.add_argument("--page-review",type=Path,required=True); a=p.parse_args()
pages=sorted(a.render_dir.glob("page-*.png"),key=lambda x:int(x.stem.split("-")[-1]))
if not pages: raise SystemExit("REAL WORD QA REGRESSION FAIL: no rendered pages")
review=load_json(a.page_review)
if not review.get("reviewer") or not review.get("limits"):
    raise SystemExit("REAL WORD QA REGRESSION FAIL: attributed page inspection and its limits required; PASS is not human/team approval")
with tempfile.TemporaryDirectory() as td:
    root=Path(td); paper=root/("paper"+a.paper.suffix.lower()); shutil.copy2(a.paper,paper)
    outputs=[]; records=[]; review_by_page={x["page"]:x for x in review.get("pages",[])}
    for i,img in enumerate(pages,1):
        dims=image_dimensions(img); rr=review_by_page.get(i,{})
        if not dims: raise SystemExit(f"REAL WORD QA REGRESSION FAIL: invalid page image {img}")
        outputs.append({"page":i,"image":str(img.resolve()),"sha256":sha256(img)})
        records.append({"page":i,"image":str(img.resolve()),"sha256":sha256(img),"width_px":dims[0],"height_px":dims[1],"manual_status":rr.get("manual_status"),"checks":rr.get("checks",{})})
    # Never synthesize a successful renderer receipt from an arbitrary log.
    try: manifest=load_json(a.renderer_artifact)
    except (ValueError,OSError): raise SystemExit("REAL WORD QA REGRESSION FAIL: actual structured renderer manifest required, not an unverified log")
    input_digest=manifest.get('input_document_sha256')
    if input_digest is None and paper.suffix.lower()=='.docx': input_digest=manifest.get('input_docx_sha256')
    if input_digest!=sha256(paper) or manifest.get("exit_code")!=0 or manifest.get("status")!="PASS":
        raise SystemExit("REAL WORD QA REGRESSION FAIL: renderer receipt not bound to this submitted DOCX/PDF")
    expected={(x["page"],x["sha256"]) for x in outputs}
    if {(x.get("page"),x.get("sha256")) for x in manifest.get("page_outputs",[])}!=expected:
        raise SystemExit("REAL WORD QA REGRESSION FAIL: receipt output set differs from actual render")
    manifest["page_outputs"]=outputs
    renderer=root/"renderer_manifest.json"; renderer.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    audit={"paper_artifact":paper.name,"paper_sha256":sha256(paper),"page_qa":{"status":"PASS","renderer":"recorded actual renderer","renderer_artifact":"renderer_manifest.json","renderer_sha256":sha256(renderer),"manual_review_artifact":str(a.page_review.resolve()),"manual_review_sha256":sha256(a.page_review),"page_size":"A4","document_sha256":sha256(paper),"page_count":len(records),"pages":records}}
    ap=root/"audit.json"; ap.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    current=audit_page_qa(ap)
    paper.write_bytes(paper.read_bytes()+b"stale")
    stale=audit_page_qa(ap)
    if not stale: raise SystemExit("REAL WORD QA REGRESSION FAIL: paper mutation was not detected")
    known_fail=review.get("overall")=="FAIL"
    if known_fail and not current: raise SystemExit("REAL WORD QA REGRESSION FAIL: known page defect was missed")
    if not known_fail and current: raise SystemExit("REAL WORD QA REGRESSION FAIL: "+"; ".join(current))
print(f"REAL WORD QA REGRESSION PASS (submitted {paper.suffix}; {len(pages)} pages; {'known defect detected' if known_fail else 'page review passed'}; mutation rejected)")
