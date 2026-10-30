"""Local relocation fixtures: no external project or account access."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import diagram_locations as diagrams

SCENE=json.dumps({'type':'excalidraw','elements':[{'id':'keep-id','text':'Keep original'}]},ensure_ascii=False).encode()

class DiagramLocationsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.root=self.base/'repo';self.root.mkdir()

    def write(self,name,data):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(data if isinstance(data,bytes) else data.encode());return p

    def snapshot(self):return {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_readonly_inspect_and_plan_reject_old_owner_rule(self):
        self.write('docs/explanation/flow.excalidraw',SCENE)
        self.write('.project-docs/rules.md','Keep diagram in docs/explanation/flow.excalidraw')
        before=self.snapshot()
        self.assertEqual(diagrams.inspect(self.root)['status'],'failed')
        self.assertEqual(len(diagrams.plan(self.root)[0]['moves']),1)
        self.assertEqual(before,self.snapshot())

    def test_apply_preserves_bytes_repairs_local_links_specs_and_static_generator(self):
        self.write('docs/explanation/flow.excalidraw',SCENE)
        self.write('docs/explanation/readme.md','[scene](flow.excalidraw)\n[web](https://example.org/docs/explanation/flow.excalidraw)')
        self.write('.project-docs/diagrams/flow.json','{"file":"docs/explanation/flow.excalidraw"}')
        gen=self.write('scripts/build.py','output="docs/explanation/flow.excalidraw"');gen.chmod(0o755)
        report=diagrams.apply(self.root,self.base/'backups')
        self.assertEqual(report['location_check']['status'],'passed')
        self.assertFalse((self.root/'docs/explanation/flow.excalidraw').exists())
        self.assertEqual((self.root/'project/diagrams/flow.excalidraw').read_bytes(),SCENE)
        self.assertIn('../../project/diagrams/flow.excalidraw',(self.root/'docs/explanation/readme.md').read_text())
        self.assertIn('https://example.org/docs/explanation/flow.excalidraw',(self.root/'docs/explanation/readme.md').read_text())
        self.assertEqual(json.loads((self.root/'.project-docs/diagrams/flow.json').read_text())['file'],'project/diagrams/flow.excalidraw')
        self.assertIn('project/diagrams/flow.excalidraw',gen.read_text());self.assertTrue(gen.stat().st_mode & 0o111)
        self.assertEqual((Path(report['backup'])/'originals/docs/explanation/flow.excalidraw').read_bytes(),SCENE)
        self.assertEqual(diagrams.apply(self.root,self.base/'backups')['status'],'unchanged')

    def test_collision_retains_every_distinct_scene(self):
        self.write('project/diagrams/flow.excalidraw',SCENE)
        self.write('a/flow.excalidraw',SCENE+b'\n');self.write('b/flow.excalidraw',SCENE+b'  ')
        report=diagrams.apply(self.root,self.base/'backups')
        self.assertEqual(report['status'],'relocated')
        self.assertEqual({p.read_bytes() for p in (self.root/'project/diagrams').glob('*.excalidraw')},{SCENE,SCENE+b'\n',SCENE+b'  '})

    def test_generator_can_recreate_old_path_and_must_fail_location_check(self):
        self.write('flow.excalidraw',SCENE)
        self.write('scripts/build.py','output = Path("docs") / "explanation" / "flow.excalidraw"')
        report=diagrams.apply(self.root,self.base/'backups')
        self.assertEqual(report['manual_review'][0]['path'],'scripts/build.py')
        self.write('docs/explanation/flow.excalidraw',SCENE)
        self.assertEqual(diagrams.inspect(self.root)['status'],'failed')

    def test_invalid_scene_is_not_moved(self):
        self.write('bad.excalidraw','{"elements":[]}');before=self.snapshot()
        self.assertEqual(diagrams.apply(self.root,self.base/'backups')['status'],'blocked')
        self.assertEqual(before,self.snapshot())

    def test_symlinks_and_external_destination_block_without_touching_target(self):
        external=self.base/'outside.excalidraw';external.write_bytes(SCENE)
        (self.root/'link.excalidraw').symlink_to(external)
        self.assertEqual(diagrams.apply(self.root,self.base/'backups')['status'],'blocked')
        self.assertEqual(external.read_bytes(),SCENE)
        (self.root/'link.excalidraw').unlink();(self.root/'project').mkdir()
        (self.root/'project/diagrams').symlink_to(self.base,target_is_directory=True)
        self.assertEqual(diagrams.plan(self.root)[0]['status'],'blocked')

    def test_failed_reference_write_restores_originals(self):
        self.write('flow.excalidraw',SCENE);self.write('README.md','[flow](flow.excalidraw)')
        before=self.snapshot();real=diagrams.os.replace
        def fail_reference(source,target):
            if Path(target).name=='README.md':raise OSError('fixture failure')
            return real(source,target)
        with patch.object(diagrams.os,'replace',side_effect=fail_reference):
            with self.assertRaisesRegex(RuntimeError,'original files/references restored'):diagrams.apply(self.root,self.base/'backups')
        self.assertEqual(before,self.snapshot())

    def test_dependency_cache_ignored_history_preserved(self):
        self.write('node_modules/pkg/example.excalidraw',b'not a scene')
        self.write('flow.excalidraw',SCENE)
        history=self.write('project/decisions/old.md','Previously flow.excalidraw')
        diagrams.apply(self.root,self.base/'backups')
        self.assertEqual(history.read_text(),'Previously flow.excalidraw')
        self.assertEqual(diagrams.inspect(self.root)['status'],'passed')

    def test_cli_default_nonzero_is_readonly(self):
        self.write('flow.excalidraw',SCENE);before=self.snapshot()
        result=subprocess.run([sys.executable,str(Path(diagrams.__file__)),'--root',str(self.root),'--json'],capture_output=True,text=True)
        self.assertEqual(result.returncode,1);self.assertEqual(json.loads(result.stdout)['status'],'failed')
        self.assertEqual(before,self.snapshot())

    def test_document_gate_fails_without_registry_or_opt_in(self):
        source=Path(diagrams.__file__).resolve().parents[1]
        shutil.copytree(source/'examples/phase-presentation',self.root,dirs_exist_ok=True)
        self.write('docs/architecture.excalidraw',SCENE)
        result=subprocess.run([sys.executable,str(source/'scripts/check_docs.py'),'--phase','1'],cwd=self.root,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Diagram location:',result.stdout)
        self.assertEqual((self.root/'docs/architecture.excalidraw').read_bytes(),SCENE)

    def test_inside_repository_backup_is_rejected(self):
        self.write('flow.excalidraw',SCENE)
        with self.assertRaises(ValueError):diagrams.apply(self.root,self.root/'backup')

if __name__=='__main__':unittest.main()
