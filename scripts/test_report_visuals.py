"""New numeric sections need current sourced visuals in MD, HTML and phase views."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from report_visuals import inspect

SCRIPTS=Path(__file__).resolve().parent


def checksum(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class ReportVisualTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'.project-docs').mkdir()
        self.md=self.root/'project/results/test-results.md';self.md.parent.mkdir(parents=True)
        self.md.write_text('## Comparison (Task 2.10)\n\n| Option | RAM |\n|---|---|\n| A | 12 |\n| B | 8 |\n\n![RAM](charts/ram.svg)\n')
        self.html=self.md.with_suffix('.html');self.html.write_text('<section id="comparison"><img src="charts/ram.svg"></section>')
        self.phase=self.root/'project/phases/phase-2/presentation.html';self.phase.parent.mkdir(parents=True);self.phase.write_text('<section id="result"><img src="../../results/charts/ram.svg"></section>')
        (self.phase.parent/'tasks.md').write_text('# PHASE 2: Fixture\n')
        self.asset=self.root/'project/results/charts/ram.svg';self.asset.parent.mkdir();self.asset.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"><title>RAM</title></svg>')
        self.generator=self.root/'scripts/plot.py';self.generator.parent.mkdir();self.generator.write_text('# Project-owned real generator fixture\n')
        self.sources=[]
        for name in ['local','remote']:
            path=self.root/(name+'.json');path.write_text('{"measurement":1}');self.sources.append({'path':path.name,'sha256':checksum(path)})
        self.section={'heading':'Comparison (Task 2.10)','html_id':'comparison','question':'Which uses less RAM?','limitations':'Fixture values; no performance claim.',
            'sources':self.sources,'visuals':[{'asset':'project/results/charts/ram.svg','sha256':checksum(self.asset),'generator':'scripts/plot.py','generator_sha256':checksum(self.generator)}],
            'presentations':[{'path':'project/phases/phase-2/presentation.html','html_id':'result'}]}
        self.data={'version':1,'reports':[{'markdown':'project/results/test-results.md','html':'project/results/test-results.html','sections':[self.section]}]}

    def save(self): (self.root/'.project-docs/report-visuals.json').write_text(json.dumps(self.data))
    def codes(self):return {f['code'] for f in inspect(self.root,True)['findings']}

    def test_missing_contract_is_not_a_visual_pass_for_new_numeric_results(self):
        self.assertEqual(inspect(self.root)['status'],'not-configured')
        self.assertIn('unregistered-result-section',self.codes())
        empty=self.root/'empty';empty.mkdir();self.assertEqual(inspect(empty,True)['status'],'not-applicable')

    def test_current_multi_source_visual_is_covered_without_any_writes(self):
        self.save();before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(inspect(self.root,True)['status'],'passed')
        self.assertEqual({str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()},before)

    def test_old_chart_in_another_section_does_not_cover_new_results(self):
        self.save();self.md.write_text(self.md.read_text().replace('![RAM](charts/ram.svg)','')+'\n## Historical comparison\n![Old](charts/ram.svg)\n')
        self.assertIn('missing-markdown-visual',self.codes())
        self.md.write_text(self.md.read_text()+'\n## New Option comparison\n| A | 5 |\n| B | 6 |\n')
        self.assertIn('unregistered-result-section',self.codes())

    def test_paired_html_and_phase_placements_must_embed_the_same_asset(self):
        self.save();self.html.write_text('<section id="comparison">table only</section>');self.phase.write_text('<section id="result">table only</section>')
        self.assertTrue({'missing-html-visual','missing-presentation-visual'}<=self.codes())
        self.section['presentations']=[];self.save();self.assertIn('untracked-presentation',self.codes())

    def test_overwritten_source_changed_generator_and_asset_are_detected(self):
        self.save();(self.root/'remote.json').write_text('{"measurement":9}');self.generator.write_text('# changed\n');self.asset.write_text('changed')
        r=inspect(self.root,True);self.assertEqual(r['status'],'failed')
        self.assertGreaterEqual(sum(f['code']=='stale-visual-input' for f in r['findings']),3)

    def test_missing_visual_or_scratch_generator_cannot_be_finished(self):
        self.section['visuals']=[];self.save();self.assertIn('missing-result-visual',self.codes())
        self.section['visuals']=[{'asset':'project/results/charts/ram.svg','sha256':checksum(self.asset),'generator':'../scratch.py','generator_sha256':'0'*64}]
        self.save();self.assertIn('stale-visual-input',self.codes())

    def test_explicit_table_only_requires_concrete_decision_and_paired_report(self):
        self.section.update(kind='table-only',reason='');self.save();self.assertIn('unjustified-table-only',self.codes())
        decision=self.root/'project/decision.md';decision.write_text('Reviewed policy: environment specification stays a table.\n')
        self.section.update(reason='Environment specification has mixed categorical units; exact values are better read as a table.',decision='project/decision.md');self.save()
        self.assertEqual(inspect(self.root,True)['status'],'passed')
        self.html.unlink();self.assertIn('missing-paired-html',self.codes())

    def test_inline_svg_checksum_and_fenced_examples(self):
        self.save();sha=checksum(self.asset)
        self.html.write_text('<section id="comparison"><svg data-asset-sha256="'+sha+'"></svg></section>')
        self.md.write_text(self.md.read_text()+'\n```markdown\n## Fake\n| X | 3 |\n| Y | 4 |\n```\n')
        self.assertEqual(inspect(self.root,True)['status'],'passed')

    def test_markdown_raw_html_images_are_real_embeds_too(self):
        self.save();self.md.write_text(self.md.read_text().replace('![RAM](charts/ram.svg)','<img src="charts/ram.svg" alt="RAM">'))
        self.assertEqual(inspect(self.root,True)['status'],'passed')

    def test_unclosed_fence_does_not_hide_uncovered_results_as_not_applicable(self):
        self.md.write_text('```markdown\n'+self.md.read_text())
        self.assertEqual(inspect(self.root,True)['status'],'failed')

    def test_gate_enforces_configured_contract_and_cli_preserves_failure(self):
        subprocess.run([sys.executable,str(SCRIPTS/'init_project.py'),'--path',str(self.root)],check=True,capture_output=True)
        self.save();self.section['visuals']=[];self.save()
        cli=subprocess.run([sys.executable,str(SCRIPTS/'report_visuals.py'),'--root',str(self.root),'--require','--json'],capture_output=True,text=True)
        self.assertEqual(cli.returncode,1);self.assertEqual(json.loads(cli.stdout)['status'],'failed')
        gate=subprocess.run([sys.executable,str(SCRIPTS/'check_docs.py')],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(gate.returncode,1);self.assertIn('Report visual coverage:',gate.stdout,gate.stderr)

    def test_duplicate_or_untrusted_registry_is_not_silently_accepted(self):
        self.data['reports'].append(self.data['reports'][0]);self.save();self.assertIn('invalid-visual-contract',self.codes())
        self.data['reports']=[];self.data['version']=True;self.save();self.assertIn('invalid-visual-contract',self.codes())


if __name__=='__main__':unittest.main()
