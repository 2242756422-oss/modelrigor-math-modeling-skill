"""Behavior/math regressions; PDF/font fixtures are not human visual approval."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'examples'),str(ROOT/'tests')]
from core import (read_document,document_text,validate_hashed_locator,sha256,load_json,
                  audit_result_registry,audit_scientific,audit_page_qa,audit_research,located_text)
from run_semantic_regressions import build_valid_question,jwrite,cwrite,headers,hashed,write_png,page_qa_record
from test_research_integrity import make_efficient,acceptance_review
from cqex import freeze_scientific
from efficient import affected_by_change,SCIENTIFIC_REUSABLE
from sync_paper_numeric_map import derive
from conservative_exchange import generator,exact,solve,study
import numpy as np


def pdf_fixture(path,texts):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    writer=PdfWriter()
    for text in texts:
        page=writer.add_blank_page(width=210*72/25.4,height=297*72/25.4)
        if text is not None:
            font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
            stream=DecodedStreamObject(); stream.set_data(('BT /F1 12 Tf 72 720 Td ('+text.replace('(','\\(').replace(')','\\)')+') Tj ET').encode())
            page[NameObject('/Contents')]=writer._add_object(stream)
    writer.write(path)


class Targeted(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.base=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def registry(self):
        q=build_valid_question(self.base); d=load_json(q/'result_registry.json'); return q,d,d['results'][0]
    def save(self,q,d): jwrite(q/'result_registry.json',d); return audit_result_registry(q/'result_registry.json')

    def test_handwritten_computation_json_is_not_production_execution(self):
        q,d,r=self.registry(); r['source'].update(type='json_pointer',category='COMPUTED')
        self.assertTrue(any('production' in x for x in self.save(q,d)))

    def test_actual_computation_output_and_receipt_pass(self):
        q,d,r=self.registry(); v=load_json(q/'verify.json')
        r['source']={'type':'json_pointer','category':'COMPUTED','artifact':'verification_output.json','pointer':'/observed_value'}
        r['artifact_sha256']=sha256(q/'verification_output.json'); r['computation_receipt']=v['run_receipt']
        self.assertFalse(self.save(q,d))
        r['source']['artifact']='proof.json'; r['source']['pointer']='/theorems/THM1/value'; r['artifact_sha256']=sha256(q/'proof.json')
        self.assertTrue(any('not produced' in x for x in self.save(q,d)))

    def test_analytical_derivation_does_not_require_numerical_receipt(self):
        q,d,r=self.registry(); v=load_json(q/'verify.json'); argument=v['argument_check']
        argument.update(status='PASS',method='elementary exact affine derivation',scientific_version=1)
        jwrite(q/'verify.json',argument); r['verification'][0]['sha256']=sha256(q/'verify.json')
        r.pop('computation_receipt',None); self.assertFalse(self.save(q,d))

    def test_analytic_numeric_json_without_derivation_is_rejected(self):
        q,d,r=self.registry(); v=load_json(q/'verify.json'); v.pop('argument_check')
        jwrite(q/'verify.json',v); r['verification'][0]['sha256']=sha256(q/'verify.json')
        self.assertTrue(any('analytical result' in x for x in self.save(q,d)))

    def test_reviewed_analytic_conclusion_must_match_registered_value(self):
        q,d,r=self.registry(); v=load_json(q/'verify.json')['argument_check']
        v.update(status='PASS',method='exact elementary derivation',scientific_version=1)
        jwrite(q/'verify.json',v); r['verification'][0]['sha256']=sha256(q/'verify.json')
        proof=load_json(q/'proof.json'); proof['theorems']['THM1']['value']=900000; jwrite(q/'proof.json',proof)
        r.update(raw_value=900000,display_value='900000',artifact_sha256=sha256(q/'proof.json'))
        self.assertTrue(any('analytical result' in x for x in self.save(q,d)))

    def test_observation_and_given_categories_require_original_source(self):
        q,d,r=self.registry()
        for category in ('OBSERVED','GIVEN'):
            r['source']['category']=category; r['source'].pop('origin',None)
            self.assertTrue(any('original provenance' in x for x in self.save(q,d)))
            r['source']['origin']={'provider':'controlled provenance fixture, not actual observations','nature':'explicit test datum','locator':hashed(q/'domain_note.md','[D1]')}
            self.assertFalse(self.save(q,d))

    def test_demo_data_cannot_be_approved_science(self):
        q,d,r=self.registry(); r['source'].update(category='DEMO',demo_label='illustrative only')
        self.assertTrue(any('demo data cannot' in x for x in self.save(q,d)))

    def test_relabelling_computed_output_as_given_input_cannot_freeze(self):
        q,d,r=self.registry(); r['source'].update(category='GIVEN',origin={'provider':'test fixture','nature':'declared given','locator':hashed(q/'domain_note.md','[D1]')})
        self.assertFalse(self.save(q,d))
        self.assertTrue(any('cannot substitute' in x for x in audit_scientific(q)))
        r['required_output_ids']=[]; self.assertFalse(self.save(q,d))  # Legitimate input does not close the answer.

    def test_pdf_text_and_page_specific_source_locator(self):
        path=self.base/'paper.pdf'; pdf_fixture(path,['first value 2','second value 3'])
        self.assertEqual(read_document(path)['page_count'],2); self.assertIn('first value 2',document_text(path))
        self.assertTrue(validate_hashed_locator(self.base,'paper.pdf#page=2::second value 3@'+sha256(path)))
        self.assertFalse(validate_hashed_locator(self.base,'paper.pdf#page=1::second value 3@'+sha256(path)))

    def test_image_only_and_partial_pdf_cannot_claim_text_review(self):
        for texts in ([None],['first readable page',None]):
            path=self.base/'scan.pdf'; pdf_fixture(path,texts)
            self.assertEqual(read_document(path)['status'],'TEXT_REVIEW_LIMITED')
            with self.assertRaisesRegex(ValueError,'text layer'): document_text(path)
            self.assertFalse(validate_hashed_locator(self.base,'scan.pdf#first readable page@'+sha256(path)))

    def test_binary_pdf_fragment_is_not_a_source_locator(self):
        path=self.base/'fake.pdf'; path.write_bytes(b'%PDF-FAKE RAW_RESULT=2')
        self.assertFalse(validate_hashed_locator(self.base,'fake.pdf#RAW_RESULT=2@'+sha256(path)))

    def test_pdf_numeric_map_binds_actual_page_not_docx(self):
        q,d,r=self.registry(); path=self.base/'paper.pdf'; pdf_fixture(path,['The computed result is 2.'])
        rows,unresolved=derive(path,[q]); self.assertFalse(unresolved)
        self.assertEqual(len(rows),1); self.assertIn('#page=1::',rows[0]['paper_locator'])
        self.assertEqual(rows[0]['paper_sha256'],sha256(path))

    def test_document_cache_invalidates_content_and_cannot_be_mutated(self):
        path=self.base/'text.md'; path.write_text('value 2'); first=read_document(path); first['text']='tampered'
        self.assertEqual(document_text(path),'value 2'); path.write_text('value 3')
        self.assertEqual(document_text(path),'value 3')

    def test_caption_identity_cannot_come_from_file_or_marker_name(self):
        path=self.base/'simulated_plot_caption.md'; path.write_text('[SIMULATED] Response curve from data.\n')
        self.assertNotIn('simulated',located_text(self.base,path.name+'#[SIMULATED]@'+sha256(path)).lower())

    def test_pdf_page_gate_uses_submitted_pdf_and_actual_page_count(self):
        path=self.base/'paper.pdf'; pdf_fixture(path,['Scientific result 2'])
        image=self.base/'page-1.png'; write_png(image)
        qa=page_qa_record(self.base,path,image)
        manifest=load_json(self.base/'renderer_manifest.json'); manifest['input_document_sha256']=manifest.pop('input_docx_sha256')
        jwrite(self.base/'renderer_manifest.json',manifest); qa['renderer_sha256']=sha256(self.base/'renderer_manifest.json')
        audit=self.base/'audit.json'; jwrite(audit,{'paper_artifact':path.name,'paper_sha256':sha256(path),'page_qa':qa})
        self.assertFalse(audit_page_qa(audit))  # Metadata fixture, not real visual approval.
        pdf_fixture(path,['Scientific result 2','unreviewed second page'])
        data=load_json(audit); data['paper_sha256']=sha256(path); data['page_qa']['document_sha256']=sha256(path); jwrite(audit,data)
        self.assertTrue(any('page count' in x for x in audit_page_qa(audit)))

    def test_scientific_review_reuse_survives_wording_not_model_change(self):
        q=make_efficient(self.base); self.assertEqual(freeze_scientific(q),0); acceptance_review(q)
        before=sha256(q/'scientific_manifest.json'); review=load_json(q/'research_review.json')
        for dim in SCIENTIFIC_REUSABLE: review['assessments'][dim]={'outcome':'ACCEPTED','reuse':'CURRENT_SCIENTIFIC_FREEZE'}
        (q/'paper.md').write_text('[P] The same exact scalar result is 2, with clearer wording.\n')
        claims=__import__('core').load_csv(q/'claim_evidence_map.csv'); claims[0]['paper_sha256']=sha256(q/'paper.md'); cwrite(q/'claim_evidence_map.csv',headers('claim_evidence_map.csv'),claims)
        review['artifacts_inspected']=['paper.md@'+sha256(q/'paper.md')]
        for dim in set(review['assessments'])-SCIENTIFIC_REUSABLE: review['assessments'][dim]['evidence']=[hashed(q/'paper.md','[P]')]
        jwrite(q/'research_review.json',review)
        self.assertFalse(audit_research(q)); self.assertEqual(sha256(q/'scientific_manifest.json'),before)
        model=load_json(q/'model_contract.json'); model['governing_relations']=['x=a+2']; jwrite(q/'model_contract.json',model)
        self.assertTrue(audit_research(q))

    def test_visual_quality_cannot_reuse_scientific_pass(self):
        q=make_efficient(self.base); self.assertEqual(freeze_scientific(q),0); acceptance_review(q)
        review=load_json(q/'research_review.json'); review['assessments']['VISUAL_QUALITY']={'outcome':'ACCEPTED','reuse':'CURRENT_SCIENTIFIC_FREEZE'}
        jwrite(q/'research_review.json',review); self.assertTrue(audit_research(q))

    def test_changed_claim_is_scientific_not_presentation_only(self):
        q=make_efficient(self.base); self.assertEqual(freeze_scientific(q),0)
        claims=__import__('core').load_csv(q/'claim_evidence_map.csv'); claims[0]['claim_text']='This is a global optimum'; cwrite(q/'claim_evidence_map.csv',headers('claim_evidence_map.csv'),claims)
        impact=affected_by_change(q,['claim_evidence_map.csv'])
        self.assertTrue(impact['scientific_invalidated']); self.assertEqual(impact['result_ids'],[])
        self.assertEqual(impact['action'],'RECHECK_CHANGED_CLAIMS_AND_GATES')

    def test_optional_legacy_resource_absence_runs_real_native_plotting(self):
        out=self.base/'plots'
        command=[sys.executable,str(ROOT/'scripts/visual_resource_smoke.py'),'--resource-root',str(self.base/'missing'),'--out',str(out)]
        proc=subprocess.run(command,text=True,capture_output=True)
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
        self.assertIn('FALLBACK EXERCISED',proc.stdout); self.assertTrue((out/'resource_smoke.png').is_file())

    def test_model_derivation_matches_generator_and_mass_identity(self):
        for volumes in ((1.,1.),(1.,3.)):
            a=generator(volumes,.8); self.assertTrue(np.allclose(a@np.ones(2),0))
            self.assertTrue(np.allclose(np.array(volumes)@a,0))
            for h in (.125,2.,20.):
                inverse=np.linalg.inv(np.eye(2)-h*a)
                self.assertGreaterEqual(float(inverse.min()),0); self.assertTrue(np.allclose(inverse@np.ones(2),1))

    def test_structural_repair_is_physically_effective_not_universal_accuracy_claim(self):
        result=study(); self.assertLess(result['explicit']['minimum'],0); self.assertGreaterEqual(result['implicit']['minimum'],0)
        self.assertLessEqual(result['implicit']['mass_error'],result['implicit']['roundoff_mass_bound'])
        self.assertTrue(all(result['refinement'][i+1]['max_error']<result['refinement'][i]['max_error'] for i in range(5)))

    def test_actual_study_output_is_serializable_not_only_in_memory_fixture(self):
        self.assertIn('observed_value',json.loads(json.dumps(study())))

    def test_exact_simple_model_has_no_need_for_algorithm_stacking(self):
        times=np.linspace(0,6,121); values=exact(times)
        self.assertTrue(np.allclose(values[:,0]+values[:,1],1))
        self.assertTrue(np.allclose(values[:,0]-values[:,1],np.exp(-1.6*times)))
        # Closed form solves the specified linear mechanism without training,
        # optimization, random seeds or a competitor constructed for show.
        self.assertTrue(np.all((values>=0)&(values<=1)))

    def test_assumption_change_requires_weighted_mass_and_valid_domains(self):
        changed=solve(.125,'implicit',(1.,3.)); mass=np.asarray(changed['values'])@np.array([1.,3.])
        self.assertTrue(np.allclose(mass,1)); self.assertGreater(abs(np.asarray(changed['values'])[-1].sum()-1),.4)
        self.assertAlmostEqual(float(exact([100.],(1.,3.))[0,0]),.25)
        for volumes,flow in (((0.,1.),.8),((1.,1.),-.8)):
            with self.assertRaises(ValueError): generator(volumes,flow)


if __name__=='__main__': unittest.main(verbosity=2)
