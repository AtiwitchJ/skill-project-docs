"""Test the runner against real failing fixtures, JUnit, history and all chart families."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from unittest import mock

import presentation_charts as charts
from test_results import import_junit
from test_results import summarize
from test_reporting import datasets,write_report

SCRIPTS=Path(__file__).resolve().parent


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def run_fixture(self,code,output='run',*extra):
        (self.root/'test_fixture.py').write_text(code)
        command=[sys.executable,str(SCRIPTS/'run_tests.py'),'--root',str(self.root),'--output',output,*extra,'unittest','--start-dir',str(self.root),'--pattern','test_fixture.py']
        p=subprocess.run(command,capture_output=True,text=True)
        path=self.root/output/'results.json';self.assertTrue(path.is_file(),p.stdout+p.stderr)
        return p,json.loads(path.read_text())

    def test_success_and_assertion_generate_reports_and_real_stage(self):
        p,result=self.run_fixture('import unittest\nclass Cases(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n def test_bad(self): self.assertEqual(1,2)\n')
        self.assertEqual(p.returncode,1)
        self.assertEqual(result['summary']['outcomes']['passed'],1)
        self.assertEqual(result['summary']['outcomes']['failed'],1)
        failed=next(c for c in result['cases'] if c['outcome']=='failed')
        self.assertEqual(failed['failures'][0]['stage'],'test')
        self.assertTrue(any(f['file'].endswith('test_fixture.py') for f in failed['failures'][0]['frames']))
        self.assertTrue((self.root/'run/report.html').is_file());self.assertTrue((self.root/'run/report.md').is_file())
        self.assertTrue(list((self.root/'run/workflows').glob('*.svg')))

    def test_setup_teardown_cleanup_and_body_exception_are_distinguished(self):
        for stage,method in (('setup','setUp'),('teardown','tearDown'),('test','test_body')):
            code=f'import unittest\nclass Cases(unittest.TestCase):\n def {method}(self): raise RuntimeError("{stage}")\n'
            if method!='test_body':code+=' def test_body(self): pass\n'
            with self.subTest(stage=stage):
                _,result=self.run_fixture(code,'run-'+stage)
                self.assertEqual(result['cases'][0]['failures'][0]['stage'],stage)
                observed=[e['stage'] for e in result['cases'][0]['events']]
                if stage=='setup':self.assertNotIn('test',observed);self.assertNotIn('teardown',observed)
        _,result=self.run_fixture('import unittest\nclass Cases(unittest.TestCase):\n def test_body(self): self.addCleanup(lambda: 1/0)\n','cleanup')
        self.assertEqual(result['cases'][0]['failures'][0]['stage'],'cleanup')

    def test_fixture_failure_is_not_a_fabricated_test_case(self):
        _,result=self.run_fixture('import unittest\nclass Cases(unittest.TestCase):\n @classmethod\n def setUpClass(cls): raise RuntimeError("fixture")\n def test_body(self): pass\n')
        self.assertEqual(result['summary']['test_cases'],0)
        self.assertEqual(result['summary']['fixture_records'],1)
        self.assertEqual(result['cases'][0]['failures'][0]['stage'],'fixture_setup')

    def test_discovery_import_error_is_retained(self):
        _,result=self.run_fixture('import module_that_does_not_exist_for_fixture\n')
        self.assertEqual(result['summary']['discovery_records'],1)
        self.assertEqual(result['cases'][0]['failures'][0]['stage'],'discovery')
        self.assertFalse(result['cases'][0]['events'])

    def test_subtests_expected_failure_unexpected_success_and_skip(self):
        code='''import unittest
class Cases(unittest.TestCase):
 def test_subtests(self):
  for i in [0,1,2]:
   with self.subTest(i=i):
    if i==2:self.skipTest('subtest skip')
    self.assertEqual(i,0)
 @unittest.expectedFailure
 def test_expected(self):self.fail('expected')
 @unittest.expectedFailure
 def test_unexpected(self):pass
 @unittest.skip('fixture skip')
 def test_skip(self):pass
'''
        p,result=self.run_fixture(code);self.assertNotEqual(p.returncode,0)
        self.assertEqual(result['summary']['test_cases'],4)
        self.assertEqual(result['summary']['subtests'],3)
        self.assertEqual(result['summary']['outcomes']['expected_failure'],1)
        self.assertEqual(result['summary']['outcomes']['unexpected_success'],1)
        self.assertFalse(any(c['id'].endswith('(i=2)') for c in result['cases']))

    def test_all_skipped_is_not_verified_passing_evidence(self):
        _,result=self.run_fixture('import unittest\n@unittest.skip("skip")\nclass Cases(unittest.TestCase):\n def test_body(self):pass\n')
        self.assertEqual(result['status'],'not_verified');self.assertIsNone(result['summary']['pass_rate'])

    def test_history_needs_repeated_matching_context(self):
        code='import unittest\nclass Cases(unittest.TestCase):\n def test_ok(self): pass\n'
        _,first=self.run_fixture(code,'history/one','--history','history')
        self.assertFalse(first['history'])
        _,second=self.run_fixture(code,'history/two','--history','history')
        self.assertEqual(len(second['history']),1)
        self.assertIn('pass-trend',second['datasets'])
        flaky=next(d for d in first['dimensions'] if d['dimension']=='Flaky candidates');self.assertFalse(flaky['available'])

    def test_outcome_changes_are_candidates_with_provenance_not_flaky_proof(self):
        code='import unittest\nclass Cases(unittest.TestCase):\n def test_outcome(self): self.assertTrue(False)\n'
        self.run_fixture(code,'history/one','--history','history','--context','explicit-fixture')
        _,second=self.run_fixture(code.replace('False','True'),'history/two','--history','history','--context','explicit-fixture')
        self.assertEqual(second['datasets']['outcome-changes'][0]['changes'],1)
        self.assertTrue(second['history'][0]['source_sha256'])
        self.assertIn('not proof',next(s for s in second['chart_specs'] if s['id']=='outcome-changes')['title'])

    def test_zero_tests_and_malformed_junit_do_not_report_verified_pass(self):
        p,result=self.run_fixture('# no discovered test cases\n','empty')
        self.assertNotEqual(p.returncode,0);self.assertNotEqual(result['status'],'passed')
        xml=self.root/'bad.xml';xml.write_text('<testsuite tests="1" failures="1"><testcase name="looks_ok"/></testsuite>')
        p=subprocess.run([sys.executable,str(SCRIPTS/'run_tests.py'),'--root',str(self.root),'--output','bad-junit','junit',str(xml)],capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        bad=json.loads((self.root/'bad-junit/results.json').read_text());self.assertEqual(bad['status'],'failed');self.assertTrue(bad['runner_error'])

    def test_coverage_is_imported_and_absence_is_not_zero(self):
        code='import unittest\nclass Cases(unittest.TestCase):\n def test_ok(self):pass\n'
        _,first=self.run_fixture(code,'one');self.assertNotIn('coverage',first)
        (self.root/'coverage.json').write_text(json.dumps({'totals':{'covered_lines':8,'num_statements':10,'covered_branches':2,'num_branches':4},'files':{'app.py':{'summary':{'covered_lines':8,'num_statements':10}}}}))
        _,second=self.run_fixture(code,'two','--coverage','coverage.json')
        self.assertEqual(second['coverage']['totals']['percent'],80)
        self.assertEqual(second['coverage']['totals']['branch_percent'],50)
        self.assertIn('branch-coverage',second['datasets'])

    def test_existing_run_is_not_overwritten(self):
        self.run_fixture('import unittest\nclass Cases(unittest.TestCase):\n def test_ok(self):pass\n')
        path=self.root/'run/results.json';before=path.read_bytes()
        p=subprocess.run([sys.executable,str(SCRIPTS/'run_tests.py'),'--root',str(self.root),'--output','run','unittest'],capture_output=True)
        self.assertEqual(p.returncode,2);self.assertEqual(path.read_bytes(),before)

    def test_command_exit_and_timeout_still_produce_reports_without_fake_cases(self):
        for name,args,expected in (('bad',['--',sys.executable,'-c','raise SystemExit(3)'],3),('timeout',['--timeout','.05','--',sys.executable,'-c','import time;time.sleep(2)'],124)):
            p=subprocess.run([sys.executable,str(SCRIPTS/'run_tests.py'),'--root',str(self.root),'--output',name,'command',*args],capture_output=True,text=True)
            self.assertEqual(p.returncode,expected,p.stderr)
            result=json.loads((self.root/name/'results.json').read_text());self.assertEqual(result['summary']['test_cases'],0)
            self.assertTrue((self.root/name/'report.html').exists());self.assertFalse(result['chart_specs'])

    def test_command_can_produce_fresh_junit_via_placeholder(self):
        child=self.root/'producer.py';child.write_text('import sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(\'<testsuite tests="1"><testcase name="ok" time="0.2"/></testsuite>\')\n')
        p=subprocess.run([sys.executable,str(SCRIPTS/'run_tests.py'),'--root',str(self.root),'--output','run','command','--',sys.executable,str(child),'{junit}'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        result=json.loads((self.root/'run/results.json').read_text());self.assertEqual(result['summary']['test_cases'],1)
        self.assertEqual(result['stage_precision'],'unknown')

    def test_keyboard_interrupt_keeps_partial_result_and_observed_stage(self):
        p,result=self.run_fixture('import unittest\nclass Cases(unittest.TestCase):\n def test_interrupt(self):raise KeyboardInterrupt()\n')
        self.assertEqual(p.returncode,130)
        self.assertEqual(result['cases'][0]['outcome'],'interrupted')
        self.assertEqual(result['cases'][0]['failures'][0]['stage'],'test')

    def test_junit_unknown_duration_and_stage_remain_unknown(self):
        path=self.root/'junit.xml';path.write_text('<testsuite tests="2" failures="1"><testcase name="ok"/><testcase name="bad"><failure message="failed">producer trace</failure></testcase></testsuite>')
        result=import_junit(path);self.assertIsNone(result['cases'][0]['duration_s']);self.assertEqual(result['cases'][1]['failures'][0]['stage'],'unknown')
        path.write_text('<testsuite tests="1" failures="1"><testcase name="looks_ok"/></testsuite>')
        with self.assertRaises(ValueError):import_junit(path)

    def test_phase_attachment_preserves_task_markers(self):
        phase=self.root/'project/phases/phase-1';phase.mkdir(parents=True)
        (self.root/'.project-docs').mkdir();(self.root/'.project-docs/config.json').write_text('{"language":"English"}')
        task='# PHASE 1: Fixture\n\n> **Period:** fixture\n\n### [ ] 1.1 Task\n- [ ] Pending\n'
        (phase/'tasks.md').write_text(task)
        subprocess.run([sys.executable,str(SCRIPTS/'sync_presentation.py'),'1','--new'],cwd=self.root,check=True,capture_output=True)
        _,result=self.run_fixture('import unittest\nclass Cases(unittest.TestCase):\n def test_bad(self):self.fail("bad")\n','run','--phase','1')
        self.assertIn('### [ ] 1.1 Task',(phase/'tasks.md').read_text())
        self.assertIn('Latest test run',(phase/'presentation.html').read_text())
        self.assertTrue((phase/'test-failure-flow.svg').is_file())


class ExtendedChartTests(unittest.TestCase):
    def test_large_inventory_keeps_all_records_with_bounded_table_previews(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            cases=[{'id':'suite.test_'+str(i),'suite':'suite','kind':'test','outcome':'passed','duration_s':(i%100)/1000,'events':[],'failures':[],'subtests':[],'skip_reason':None} for i in range(6000)]
            result={'schema':'project-docs-tests/v1','cases':cases,'started':'Synthetic stress fixture','duration_s':10,'exit_code':0,'history':[],'limitations':['Synthetic frontend stress fixture; not 6000 real executions.']}
            result['summary']=summarize(result);result['datasets'],result['chart_specs'],result['dimensions']=datasets(result)
            (root/'results.json').write_text(json.dumps(result))
            rendered=write_report(root);self.assertFalse(rendered['errors'])
            html=(root/'report.html').read_text();md=(root/'report.md').read_text()
            self.assertEqual(html.count('class="case"'),6000)
            self.assertIn('first 100 of 6000',html);self.assertIn('Math.ceil(matches.length/50)',html)
            self.assertIn('|---|---|---|\n| Case outcomes |',md)
            self.assertIn('suite.test_5999',html)

    def test_chart_render_error_is_visible_without_losing_test_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);case={'id':'a','suite':'s','kind':'test','outcome':'passed','duration_s':1,'events':[],'failures':[],'subtests':[],'skip_reason':None}
            result={'schema':'project-docs-tests/v1','cases':[case],'started':'Fixture','duration_s':1,'exit_code':0,'history':[],'limitations':['Fixture only.']}
            result['summary']=summarize(result);result['datasets'],result['chart_specs'],result['dimensions']=datasets(result)
            (root/'results.json').write_text(json.dumps(result));original=charts.render
            def render(directory,spec):
                if spec['id']=='outcomes':raise ValueError('Intentional rendering fixture')
                return original(directory,spec)
            with mock.patch.object(charts,'render',side_effect=render):rendered=write_report(root)
            self.assertEqual(len(rendered['errors']),1)
            self.assertIn('Chart unavailable: outcomes',(root/'report.html').read_text())
            self.assertIn('class="case"',(root/'report.html').read_text())

    def test_gallery_renders_all_sixteen_families_with_exact_source_values(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'gallery';p=subprocess.run([sys.executable,str(SCRIPTS/'build_chart_gallery.py'),'--output',str(root)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            specs=json.loads((root/'chart-specs.json').read_text());self.assertEqual(len(specs),16)
            for spec in specs:
                with self.subTest(chart=spec['type']):
                    rendered=charts.render(root,spec);ET.fromstring(rendered['svg']);self.assertTrue(rendered['rows'])
                    self.assertEqual(rendered['sha256'],hashlib.sha256((root/'gallery-data.json').read_bytes()).hexdigest())

    def test_extended_encodings_reject_invalid_semantics(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'data.json'
            cases=[('range',[{'label':'A','low':5,'high':1}],dict(x='label')),
                   ('waterfall',[{'label':'A','value':2}],dict(x='label',y='value',start=0,end=10)),
                   ('timeline',[{'label':'A','start':'2026-01-03','end':'2026-01-01'}],dict(x='label')),
                   ('pareto',[{'label':'A','value':-2}],dict(x='label',y='value')),
                   ('histogram',[{'value':True}],dict(value='value')),
                   ('area',[{'x':1,'y':-1},{'x':2,'y':2}],dict(x='x',y='y'))]
            for typ,rows,fields in cases:
                source.write_text(json.dumps(rows));spec={'id':'fixture','type':typ,'title':'Fixture','question':'What?','source':{'path':'data.json'},'unit':'s','limitations':'Synthetic.',**fields}
                with self.subTest(chart=typ),self.assertRaises(ValueError):charts.render(root,spec)


if __name__=='__main__':unittest.main()
