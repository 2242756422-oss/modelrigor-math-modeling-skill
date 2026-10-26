#!/usr/bin/env python3
"""Real subprocess/media regressions. They do not certify scientific quality."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'tests')]
from core import (sha256, audit_figures, audit_image_readability, _real_image,
                  audit_model_contract, audit_scientific)
from record_run import record_run
from provenance import audit_run, execution_entry, audit_verification
from run_semantic_regressions import build_valid_question, jwrite, cwrite, hashed
from test_research_integrity import make_efficient
from efficient import affected_by_change


class ExecutionHardening(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.base = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)
        self.script('A.py', "from pathlib import Path; Path('out.json').write_text('{\"v\":2}')\n")
        self.script('B.py', "from pathlib import Path; Path('out.json').write_text('{\"v\":99}')\n")

    def script(self, name, content):
        path = self.base/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content); return path

    def run_case(self, args=None, code=None, inputs=None, outputs=None, receipt='run.json'):
        return record_run(self.base, args or [sys.executable, 'A.py'], code or ['A.py'],
                          inputs or [], outputs or ['out.json'], self.base/receipt)

    def issues(self, name='run.json', output='out.json'):
        path=self.base/name
        return audit_run(self.base, str(path)+'@'+sha256(path), output)[0]

    def test_wrong_entry_rejected_before_execution(self):
        with self.assertRaises(ValueError): self.run_case([sys.executable, 'B.py'])
        self.assertFalse((self.base/'out.json').exists())

    def test_irrelevant_string_parameter_cannot_bind_entry(self):
        with self.assertRaises(ValueError): self.run_case([sys.executable, 'B.py', '--note', 'A.py'])
        self.assertFalse((self.base/'out.json').exists())

    def test_same_basename_in_different_directory_is_not_identity(self):
        self.script('other/A.py', (self.base/'B.py').read_text())
        with self.assertRaises(ValueError): self.run_case([sys.executable, 'other/A.py'])

    def test_relative_absolute_and_symlink_identity(self):
        (self.base/'alias.py').symlink_to(self.base/'A.py')
        for path in ('./A.py', str(self.base/'A.py'), 'alias.py'):
            data=self.run_case([sys.executable, path])
            self.assertEqual(data['process_exit_code'], 0); self.assertFalse(self.issues())

    def test_module_source_runs_and_binds(self):
        data=self.run_case([sys.executable, '-B', '-m', 'A'])
        self.assertEqual(data['execution_binding']['kind'], 'PYTHON_LOCAL_MODULE')
        self.assertEqual(json.loads((self.base/'out.json').read_text())['v'], 2)
        self.assertFalse(self.issues())

    def test_package_main_and_initialization_bound(self):
        self.script('pkg/__init__.py', 'OFFSET=1\n')
        main=self.script('pkg/__main__.py', "from pathlib import Path; from pkg import OFFSET; Path('out.json').write_text(str(OFFSET))\n")
        data=self.run_case([sys.executable, '-m', 'pkg'], code=[str(main)])
        self.assertEqual(len(data['code']), 2); self.assertFalse(self.issues())

    def test_python_interpreter_options_not_script_arguments(self):
        data=self.run_case([sys.executable, '-B', '-W', 'ignore', '-X', 'dev', 'A.py', 'B.py'])
        self.assertEqual(data['provenance_status'], 'PASS'); self.assertFalse(self.issues())

    def test_helper_import_and_legitimate_intermediate_outputs(self):
        self.script('helper.py', 'def calculate(x): return x+1\n')
        self.script('main.py', "import json; from pathlib import Path; from helper import calculate\nx=json.loads(Path('input.json').read_text())['v']; Path('middle.json').write_text(str(x)); Path('out.json').write_text(json.dumps({'v':calculate(x)}))\n")
        self.script('input.json', '{"v":1}')
        data=self.run_case([sys.executable, '-B', 'main.py'], code=['main.py','helper.py'], inputs=['input.json'], outputs=['middle.json','out.json'])
        self.assertEqual(data['provenance_status'], 'PASS'); self.assertFalse(self.issues())

    def test_multiple_script_arguments_only_first_is_entry(self):
        with self.assertRaises(ValueError): self.run_case([sys.executable, 'B.py', 'A.py'])
        data=self.run_case([sys.executable, 'A.py', 'B.py'], code=['A.py','B.py'])
        self.assertEqual(data['execution_binding']['entrypoint'], str(self.base/'A.py'))
        self.assertIn('not proof of imports', data['execution_binding']['scope'])

    def test_shell_wrapper_recorded_but_not_auto_certified(self):
        data=self.run_case(['/bin/sh', '-c', '"'+sys.executable+'" A.py'])
        self.assertEqual(data['process_exit_code'], 0)
        self.assertEqual(data['provenance_status'], 'LIMITED'); self.assertTrue(self.issues())

    def test_inline_python_is_limited_not_inferred_from_string(self):
        data=self.run_case([sys.executable,'-c', (self.base/'A.py').read_text(), 'A.py'])
        self.assertEqual(data['process_exit_code'], 0)
        self.assertEqual(data['provenance_status'], 'LIMITED'); self.assertTrue(self.issues())

    def reviewed_wrapper(self,command):
        note=self.script('invocation.md','[ENTRY] The literal shell command invokes the absolute interpreter and A.py in the recorded cwd; A.py writes the specified scalar. No other branches or input indirection in this controlled fixture.\n')
        return {'kind':'REVIEWED_ARGUMENT','command':command,'code':[str(self.base/'A.py')+'@'+sha256(self.base/'A.py')],
                'argument':hashed(note,'[ENTRY]'),'review_evidence':hashed(note,'[ENTRY]'),
                'substantive_review':{'reviewer':'controlled engineering review fixture','reasoning':'Inspected literal one-command shell and the actual source; not arbitrary-shell certification.',
                                      'scope':'literal fixture entry only','limitations':'not dynamic program/security proof','outcome':'ACCEPTED'}}

    def test_legitimate_wrapper_has_reviewed_not_auto_certified_route(self):
        command=['/bin/sh','-c','"'+sys.executable+'" A.py']
        data=record_run(self.base,command,['A.py'],[],['out.json'],self.base/'run.json',entry_review=self.reviewed_wrapper(command))
        self.assertEqual(data['process_exit_code'],0); self.assertEqual(data['provenance_status'],'LIMITED')
        issues,receipt=audit_run(self.base,str(self.base/'run.json')+'@'+sha256(self.base/'run.json'),'out.json')
        self.assertFalse(issues); self.assertEqual(receipt['entry_assurance'],'REVIEWED_ARGUMENT_NOT_AUTOMATIC_ENTRY_CERTIFICATION')

    def test_complex_pass_label_or_wrong_review_command_is_rejected(self):
        command=['/bin/sh','-c','"'+sys.executable+'" A.py']
        for review in ({'status':'PASS','method':'reviewed'},self.reviewed_wrapper(['/bin/sh','-c','false'])):
            with self.assertRaises(ValueError): record_run(self.base,command,['A.py'],[],['out.json'],self.base/'run.json',entry_review=review)
        self.assertFalse((self.base/'out.json').exists())

    def test_reviewed_argument_cannot_launder_identified_wrong_python_entry(self):
        command=[sys.executable,'B.py','A.py']
        with self.assertRaises(ValueError): record_run(self.base,command,['A.py'],[],['out.json'],self.base/'run.json',entry_review=self.reviewed_wrapper(command))

    def test_runtime_input_mutation_separates_actual_process_status(self):
        self.script('input.json','{"v":2}')
        self.script('A.py', "from pathlib import Path; Path('input.json').write_text('{\"v\":0}'); Path('out.json').write_text('0')\n")
        data=self.run_case(inputs=['input.json'])
        self.assertEqual(data['process_exit_code'], 0); self.assertEqual(data['exit_code'], 0)
        self.assertEqual(data['provenance_status'], 'FAIL'); self.assertTrue(data['integrity']['changed'])
        self.assertNotEqual(data['integrity']['before'], data['integrity']['after']); self.assertTrue(self.issues())

    def test_runtime_source_mutation_is_not_silently_post_bound(self):
        before=sha256(self.base/'A.py')
        self.script('A.py', "from pathlib import Path; Path(__file__).write_text('# changed'); Path('out.json').write_text('1')\n")
        before=sha256(self.base/'A.py'); data=self.run_case()
        self.assertEqual(data['exit_code'],0); self.assertEqual(data['provenance_status'],'FAIL')
        self.assertEqual(data['code'][0].rsplit('@',1)[1],before); self.assertTrue(self.issues())

    def test_deleted_input_is_integrity_failure_not_unhandled_error(self):
        self.script('input.json','{}')
        self.script('A.py', "from pathlib import Path; Path('input.json').unlink(); Path('out.json').write_text('1')\n")
        data=self.run_case(inputs=['input.json']); self.assertEqual(data['provenance_status'],'FAIL'); self.assertTrue(self.issues())

    def test_input_changed_before_run_binds_current_version(self):
        self.script('input.json','old'); old=sha256(self.base/'input.json')
        self.script('input.json','new'); data=self.run_case(inputs=['input.json'])
        self.assertNotEqual(old,data['inputs'][0].rsplit('@',1)[1]); self.assertFalse(self.issues())

    def test_input_output_alias_is_rejected_not_mutation_whitelisted(self):
        self.script('input.json','{}')
        with self.assertRaises(ValueError): self.run_case(inputs=['input.json'], outputs=['input.json'])

    def test_other_side_effect_does_not_pretend_to_be_full_workspace_audit(self):
        self.script('A.py', "from pathlib import Path; Path('side.txt').write_text('untracked'); Path('out.json').write_text('1')\n")
        data=self.run_case(); self.assertEqual(data['provenance_status'],'PASS')
        self.assertTrue((self.base/'side.txt').is_file()); self.assertIn('no full dynamic',data['validation_limitations'][1])

    def test_actual_nonzero_exit_is_preserved(self):
        self.script('A.py', "from pathlib import Path; import sys; Path('out.json').write_text('1'); sys.exit(7)\n")
        data=self.run_case(); self.assertEqual(data['process_exit_code'],7); self.assertEqual(data['exit_code'],7)
        self.assertTrue(self.issues())

    def test_stale_output_does_not_rewrite_successful_process_exit(self):
        self.script('out.json','1'); self.script('A.py', "print('no output')\n")
        data=self.run_case(); self.assertEqual(data['process_exit_code'],0)
        self.assertEqual(data['provenance_status'],'FAIL'); self.assertTrue(self.issues())

    def test_launch_failure_records_no_invented_child_exit(self):
        data=self.run_case(['/definitely/missing/python','A.py'])
        self.assertIsNone(data['process_exit_code']); self.assertTrue(data['process_error']); self.assertTrue(self.issues())

    def test_repeated_legitimate_runs_both_audit(self):
        for receipt in ('one.json','two.json'):
            self.run_case(receipt=receipt); self.assertFalse(self.issues(receipt))

    def test_symlink_retarget_during_run_is_detected(self):
        self.script('input.json','same'); self.script('other.json','same')
        (self.base/'link.json').symlink_to(self.base/'input.json')
        self.script('A.py', "from pathlib import Path; p=Path('link.json'); p.unlink(); p.symlink_to('other.json'); Path('out.json').write_text('1')\n")
        data=self.run_case(inputs=['link.json']); self.assertEqual(data['provenance_status'],'FAIL'); self.assertTrue(self.issues())

    def test_new_receipt_schema_actual_record_and_incomplete_rejected(self):
        import jsonschema
        data=self.run_case(); schema=json.loads((ROOT/'schemas/execution_receipt.schema.json').read_text())
        jsonschema.validate(data,schema)
        data['integrity'].pop('before'); jwrite(self.base/'run.json',data)
        self.assertTrue(self.issues())

    def test_old_valid_receipt_retains_limited_scope_not_fabricated_pre_hashes(self):
        data=self.run_case()
        for key in ('schema_version','cwd','process_exit_code','provenance_status','integrity','execution_binding','validation_limitations'):
            data.pop(key)
        jwrite(self.base/'old.json',data)
        issues, receipt=audit_run(self.base,str(self.base/'old.json')+'@'+sha256(self.base/'old.json'),'out.json')
        self.assertFalse(issues); self.assertIn('LEGACY_POST_RUN_ONLY',receipt['validation_limitations'][0])
        self.assertNotIn('integrity',receipt)

    def test_old_disconnected_receipt_is_not_grandfathered(self):
        data=self.run_case(); data.pop('schema_version'); data['command']=[sys.executable,'B.py','A.py']; jwrite(self.base/'run.json',data)
        self.assertTrue(self.issues())

    def test_unused_attached_helper_does_not_prove_independent_verification(self):
        self.script('A.py', "import json; json.dump({'observed_value':2,'checks':[{'purpose':'scalar equality','relation':'exact','actual':2,'expected':2}]},open('out.json','w'))\n")
        self.run_case(receipt='primary.json'); self.script('unused.py','NOT_IMPORTED=True\n')
        self.run_case(code=['A.py','unused.py'],receipt='verifier.json')
        verifier={'kind':'EXECUTED_CHECK','run_receipt':str(self.base/'verifier.json')+'@'+sha256(self.base/'verifier.json'),
                  'output_artifact':'out.json','independent':True,'independence_basis':'deliberate false helper claim'}
        result={'raw_value':2,'computation_receipt':str(self.base/'primary.json')+'@'+sha256(self.base/'primary.json')}
        self.assertIn('independent implementation not demonstrated',audit_verification(self.base,verifier,result))

    def test_module_safe_path_scope_and_ignore_environment_are_distinct(self):
        limited=execution_entry(self.base,[sys.executable,'-m','A'],['A.py'],{'PYTHONSAFEPATH':'1'})
        self.assertEqual(limited['status'],'UNVERIFIED')
        with patch.dict(os.environ,{'PYTHONSAFEPATH':'1'}):
            data=self.run_case([sys.executable,'-E','-m','A'])
        self.assertEqual(data['provenance_status'],'PASS'); self.assertFalse(self.issues())


class FigureAndWorkflowHardening(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.base=Path(self.temp.name).resolve(); self.addCleanup(self.temp.cleanup)

    def raster(self,name,size):
        from PIL import Image,ImageDraw
        path=self.base/name; im=Image.new('RGB',size,'white'); ImageDraw.Draw(im).line((0,0,size[0]-1,size[1]-1),fill='black',width=max(2,size[0]//40)); im.save(path); return path

    def test_tiny_nonblank_raster_rejected_at_manuscript_size(self):
        image=self.raster('tiny.png',(50,50))
        self.assertTrue(_real_image(image)); self.assertTrue(audit_image_readability(image,{'final_width_mm':160}))

    def test_high_resolution_raster_accepted(self):
        image=self.raster('large.png',(2400,1600))
        self.assertFalse(audit_image_readability(image,{'final_width_mm':160}))

    def test_nominal_300dpi_export_allows_only_integer_pixel_truncation(self):
        image=self.raster('nominal.png',(1889,850))
        self.assertFalse(audit_image_readability(image,{'final_width_mm':160,'final_height_mm':72}))
        smaller=self.raster('below.png',(1888,850))
        self.assertTrue(audit_image_readability(smaller,{'final_width_mm':160,'final_height_mm':72}))

    def test_identical_raster_different_display_size_changes_sampling(self):
        image=self.raster('medium.png',(600,400))
        self.assertFalse(audit_image_readability(image,{'final_width_mm':40}))
        self.assertTrue(audit_image_readability(image,{'final_width_mm':160}))

    def test_figure_specific_dpi_requires_reason_and_actual_height_checked(self):
        image=self.raster('medium.png',(600,400))
        self.assertTrue(audit_image_readability(image,{'final_width_mm':100,'raster_requirement':{'minimum_effective_dpi':150}}))
        self.assertFalse(audit_image_readability(image,{'final_width_mm':100,'raster_requirement':{'minimum_effective_dpi':150,'basis':'continuous-tone figure at reviewed electronic size'}}))
        self.assertTrue(audit_image_readability(image,{'final_width_mm':40,'final_height_mm':150}))

    def test_vector_svg_and_pdf_use_render_not_pixel_rule(self):
        svg=self.base/'plot.svg'; svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><path d="M0 0L10 10"/></svg>')
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        pdf=self.base/'plot.pdf'; fig,ax=plt.subplots(); ax.plot([0,1],[0,1]); fig.savefig(pdf); plt.close(fig)
        for path in (svg,pdf):
            self.assertTrue(_real_image(path)); self.assertFalse(audit_image_readability(path,{'final_width_mm':160}))

    def test_invalid_png_header_and_truncated_svg_pdf_rejected(self):
        for name,data in [('fake.png',b'\x89PNG\r\n\x1a\n'+b'\x00'*30),('fake.svg',b'<svg'),('fake.pdf',b'%PDF-1.4\n')]:
            path=self.base/name; path.write_bytes(data); self.assertFalse(_real_image(path))

    def test_actual_figure_gate_rejects_tiny_and_preserves_real_source_checks(self):
        q=build_valid_question(self.base)
        source=q/'data.json'; jwrite(source,{'value':2})
        plotter=q/'plot.py'; plotter.write_text("from PIL import Image,ImageDraw; import json\nx=json.load(open('data.json'))['value']; im=Image.new('RGB',(50,50),'white'); ImageDraw.Draw(im).line((0,0,49,49),fill='black',width=x); im.save('figure.png')\n")
        receipt=q/'plot_run.json'; record_run(q,[sys.executable,plotter.name],[plotter.name],[source.name],['figure.png'],receipt)
        image=q/'figure.png'; vr=q/'visual_review.json'
        jwrite(vr,{'image_sha256':sha256(image),'outcome':'ACCEPTED','reviewer':'TEST_FIXTURE_ONLY','inspection_scope':'DIRECT_IMAGE_AND_FINAL_SIZE','final_width_mm':160,'final_size_preview':image.name+'@'+sha256(image),'checks':{k:{'outcome':'ACCEPTED','observation':'structural fixture, not scientific review'} for k in ('scientific_encoding','source_fidelity','axes_units','legibility','legend_color','panel_caption','claim_support')}})
        fields=json.loads((ROOT/'schemas/csv_headers.json').read_text())['figure_candidates.csv']
        row={'figure_id':'F1','question_id':'q1','role':'PRIMARY_RESULT','research_question':'test sampling','message':'test fixture','data_source':source.name,'data_source_sha256':sha256(source),'data_identity':'REAL_DERIVED','demo_quarantine':'REAL_DATA','preferred_chart_type':'line','importance':'HIGH','status':'DELIVERED','output_path':image.name,'output_sha256':sha256(image),'caption_locator':hashed(q/'paper.md','[CAP]'),'paper_locator':'paper.md#[CAP]','plot_code':plotter.name+'@'+sha256(plotter),'generation_receipt':receipt.name+'@'+sha256(receipt),'visual_review':vr.name+'@'+sha256(vr)}
        cwrite(q/'figure_candidates.csv',fields,[row]); issues=audit_figures(q/'figure_candidates.csv','theoretical')[1]
        self.assertTrue(any('resolution too low' in x for x in issues))
        row['data_source_sha256']='0'*64; cwrite(q/'figure_candidates.csv',fields,[row])
        self.assertTrue(any('data source/hash invalid' in x for x in audit_figures(q/'figure_candidates.csv','theoretical')[1]))

    def test_visual_edit_has_no_unrelated_scientific_invalidation(self):
        q=make_efficient(self.base); plot=q/'plot.png'; self.raster('plot.png',(1200,800)).replace(plot)
        report=affected_by_change(q,[plot]); self.assertFalse(report['scientific_invalidated']); self.assertEqual(report['result_ids'],[])

    def test_structure_complete_does_not_prove_equal_count_system_is_well_posed(self):
        import numpy as np
        matrix=np.array([[1.,1.],[2.,2.]])
        self.assertEqual(matrix.shape[0],matrix.shape[1]); self.assertEqual(np.linalg.matrix_rank(matrix),1)
        self.assertFalse(np.allclose(matrix@np.linalg.lstsq(matrix,np.array([1.,3.]),rcond=None)[0],[1.,3.]))
        q=build_valid_question(self.base); self.assertFalse(audit_model_contract(q/'model_contract.json'))
        self.assertIn('NOT a well-posedness',audit_model_contract.__doc__)
        # Applicable adverse scientific evidence remains blocking in the live path.
        q=make_efficient(self.base); domain=json.loads((q/'domain_model_map.json').read_text())
        domain['p0_issues']=[{'status':'OPEN','reason':'rank-deficient inconsistent constraint system'}]; jwrite(q/'domain_model_map.json',domain)
        self.assertTrue(any('P0' in x for x in audit_scientific(q)))

    def test_default_cli_initialization_keeps_six_core_artifacts(self):
        path=self.base/'fresh'
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/cqex.py'),'init-question',str(path),'--id','q1'],capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr); self.assertEqual(len(list(path.iterdir())),6)


if __name__=='__main__': unittest.main(verbosity=2)
