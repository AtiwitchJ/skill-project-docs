"""Required hierarchy semantics and gate integration; temporary fixtures, no accounts."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from task_naming import inspect

SCRIPTS=Path(__file__).resolve().parent


class HierarchyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'.project-docs').mkdir()
        (self.root/'.project-docs/config.json').write_text('{}')
        self.path=self.root/'project/phases/phase-2/tasks.md';self.path.parent.mkdir(parents=True)
        (self.root/'project/source-plan.md').write_text('# Source plan\nExperiments: Agent with Azure MCP\n')
        self.data={'version':1,'phases':{'2':{'topics':[{'label':'Agent with Azure MCP','category':'Experiments','source':'project/source-plan.md','source_label':'Agent with Azure MCP','disposition':'in-scope'}]}}}
        self.task='''## Experiments

### [ ] 2.6 [Agent with Azure MCP] Prepare the approved experiment
**Task UID:** stable-azure
**Work category:** Experiments
**Plan topic:** Agent with Azure MCP
**Plan source:** project/source-plan.md — Experiments box
**Scope disposition:** in-scope
- [ ] Verify approved scope.
'''
        self.path.write_text(self.task)

    def registry(self):
        (self.root/'.project-docs/task-topics.json').write_text(json.dumps(self.data))

    def codes(self):return {f['code'] for f in inspect(self.root,required=True)['findings']}

    def test_unconfigured_is_not_a_pass_and_required_missing_contract_fails(self):
        self.assertEqual(inspect(self.root)['status'],'not-configured')
        self.assertIn('missing-topic-registry',self.codes())
        (self.root/'.project-docs/config.json').write_text('{"task_naming":{"required":true}}')
        self.assertEqual(inspect(self.root)['status'],'failed')

    def test_valid_structure_read_only_with_unchanged_identity_and_status(self):
        self.registry()
        def snapshot():return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        before=snapshot();r=inspect(self.root,required=True)
        self.assertEqual(r['status'],'passed');self.assertEqual(snapshot(),before)
        self.assertEqual((r['tasks'][0]['number'],r['tasks'][0]['uid'],r['tasks'][0]['mark']),('2.6','stable-azure',' '))

    def test_missing_prefix_is_failure_even_when_all_tasks_are_checked(self):
        self.registry();self.path.write_text(self.task.replace('[ ] 2.6 [Agent with Azure MCP]','[x] 2.6'))
        self.assertIn('missing-topic-title',self.codes());self.assertIn('unmapped-plan-topic',self.codes())

    def test_categories_sources_and_aliases_are_checked(self):
        self.registry();self.path.write_text(self.task.replace('## Experiments','## PoC').replace('**Plan topic:** Agent with Azure MCP','**Plan topic:** Shortened'))
        self.assertTrue({'category-mismatch','source-topic-mismatch'}<=self.codes())
        self.data['phases']['2']['topics'][0]['source_label']='Exact original Azure topic';self.registry()
        self.assertIn('unexplained-alias',self.codes())

    def test_missing_plan_coverage_and_excluded_work_not_counted_done(self):
        topic=self.data['phases']['2']['topics'][0];topic.update(disposition='out-of-scope',reason='Approved boundary',decision='project/source-plan.md')
        self.registry();self.path.write_text(self.task.replace('### [ ]','### [x]').replace('**Scope disposition:** in-scope','**Scope disposition:** out-of-scope'))
        self.assertIn('excluded-as-done',self.codes())
        topic['decision']='';self.registry();self.assertIn('missing-scope-decision',self.codes())
        self.path.write_text('## Experiments\n');self.assertIn('unmapped-plan-topic',self.codes())

    def test_duplicate_identity_and_compact_spacing_are_not_silently_repaired(self):
        self.registry();self.path.write_text(self.task+self.task.replace('2.6 [','2.6['))
        self.assertTrue({'duplicate-task-uid','duplicate-task-number','compact-title'}<=self.codes())

    def test_sources_cannot_escape_project_and_fenced_examples_are_not_tasks(self):
        self.registry();self.path.write_text(self.task+'\n```markdown\n### [x] 9.9 [Fake] Example\n```\n')
        self.assertEqual(inspect(self.root)['status'],'passed')
        self.data['phases']['2']['topics'][0]['source']='../external.md';self.registry()
        self.assertIn('missing-plan-source',self.codes())

    def test_cli_and_gate_reject_required_hierarchy_defects(self):
        subprocess.run([sys.executable,str(SCRIPTS/'init_project.py'),'--path',str(self.root)],check=True,capture_output=True)
        self.registry();self.path.write_text(self.task.replace('[Agent with Azure MCP] ',''))
        cli=subprocess.run([sys.executable,str(SCRIPTS/'task_naming.py'),'--root',str(self.root),'--require','--phase','2','--json'],capture_output=True,text=True)
        self.assertEqual(cli.returncode,1);self.assertEqual(json.loads(cli.stdout)['status'],'failed')
        gate=subprocess.run([sys.executable,str(SCRIPTS/'check_docs.py'),'--phase','2'],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(gate.returncode,1);self.assertIn('Task hierarchy:',gate.stdout)

    def test_malformed_registry_and_missing_phase_contract_are_findings(self):
        (self.root/'.project-docs/task-topics.json').write_text('[]')
        self.assertIn('invalid-topic-registry',self.codes())
        self.data['phases']={};self.registry();self.assertIn('missing-phase-topics',self.codes())


if __name__=='__main__':unittest.main()
