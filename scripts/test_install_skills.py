"""Portable discovery packages and safe local installer; no real agent dirs touched."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import install_skills as installer

SOURCE=Path(__file__).resolve().parent.parent


def snapshot(root):
    if not root.exists():return {}
    result={}
    for p in root.rglob('*'):
        if p.is_symlink():result[str(p.relative_to(root))]=('link',os.readlink(p))
        elif p.is_file():result[str(p.relative_to(root))]=('file',p.read_bytes())
    return result


class PortableInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.dest=self.base/'agent/skills';self.backup=self.base/'backups'

    def apply(self,**kwargs):return installer.install(SOURCE,self.dest,apply=True,backup_base=self.backup,**kwargs)

    def test_plan_does_not_create_any_directory(self):
        r=installer.install(SOURCE,self.dest)
        self.assertEqual(r['status'],'planned');self.assertFalse(self.dest.parent.exists());self.assertEqual(len(r['skills']),7)

    def test_seven_discoverable_siblings_with_complete_local_core_and_reinstall_sources(self):
        r=self.apply();self.assertEqual(r['status'],'installed')
        discovered=list(self.dest.rglob('SKILL.md'));self.assertEqual(len(discovered),7)
        self.assertTrue(all(p.parent.parent==self.dest for p in discovered))
        for verb in installer.VERBS:
            path=self.dest/('project-docs-'+verb)/'SKILL.md';raw=path.read_bytes();installer.validate_skill(raw,path.parent.name)
            self.assertNotIn(b'$ARGUMENTS',raw)
            self.assertTrue((path.parent/'../project-docs/rules/commands.md').is_file())
            self.assertEqual(raw,(self.dest/'project-docs/skill-adapters'/('project-docs-'+verb+'.md')).read_bytes())
        meta=json.loads((self.dest/installer.MANIFEST).read_text());self.assertEqual(meta['bundle_sha256'],r['bundle_sha256'])
        # No dependency on the original source or on a Claude installation.
        self.assertEqual(installer.install(self.dest/'project-docs',self.dest,apply=True,backup_base=self.backup)['status'],'unchanged')

    def test_repeat_install_and_runtime_caches_do_not_replace_packages(self):
        self.apply();cache=self.dest/'project-docs/scripts/__pycache__';cache.mkdir();(cache/'runtime.pyc').write_bytes(b'cache')
        before=snapshot(self.dest);r=self.apply();self.assertEqual(r['status'],'unchanged');self.assertEqual(snapshot(self.dest),before);self.assertFalse(self.backup.exists())

    def test_any_conflict_blocks_all_creations_before_writes(self):
        existing=self.dest/'project-docs-test';existing.mkdir(parents=True);(existing/'mine.txt').write_text('user content')
        before=snapshot(self.dest);r=self.apply();self.assertEqual(r['status'],'blocked');self.assertEqual(snapshot(self.dest),before);self.assertFalse(self.backup.exists())

    def test_backup_preserves_real_directory_and_symlink_target_and_unrelated_skill(self):
        external=self.base/'original';external.mkdir();(external/'keep').write_text('original target')
        self.dest.mkdir(parents=True);(self.dest/'project-docs').symlink_to(external,target_is_directory=True)
        old=self.dest/'project-docs-check';old.mkdir();(old/'mine').write_text('old skill')
        unrelated=self.dest/'project-docs-now';unrelated.mkdir();(unrelated/'SKILL.md').write_text('unknown companion')
        r=self.apply(backup_existing=True);backup=Path(r['backup'])
        self.assertTrue((backup/'project-docs').is_symlink());self.assertEqual((external/'keep').read_text(),'original target')
        self.assertEqual((backup/'project-docs-check/mine').read_text(),'old skill')
        self.assertEqual((unrelated/'SKILL.md').read_text(),'unknown companion')

    def test_failure_restores_previous_entries_and_leaves_no_partial_bundle(self):
        old=self.dest/'project-docs';old.mkdir(parents=True);(old/'mine').write_text('uncommitted original')
        before=snapshot(self.dest);real_replace=os.replace;failed=False
        def replace(src,dst):
            nonlocal failed
            if Path(dst).resolve()==(self.dest/'project-docs-update').resolve() and not failed:
                failed=True;raise OSError('injected installation failure')
            return real_replace(src,dst)
        with mock.patch.object(installer.os,'replace',side_effect=replace):
            with self.assertRaisesRegex(RuntimeError,'previous entries restored'):self.apply(backup_existing=True)
        self.assertEqual(snapshot(self.dest),before)

    def test_native_roots_are_explicit_and_only_selected_root_is_changed(self):
        self.assertEqual(installer.ROOTS['antigravity'],'.gemini/config/skills')
        self.assertEqual(installer.ROOTS['codex'],'.agents/skills')
        for agent in installer.ROOTS:
            with self.subTest(agent=agent):
                root=self.base/agent/'skills';installer.install(SOURCE,root,apply=True,backup_base=self.backup)
                self.assertEqual(len(list(root.glob('*/SKILL.md'))),7)
        self.assertFalse((self.base/'.claude').exists())

    def test_custom_root_symlink_is_reported_without_modifying_other_locations(self):
        actual=self.base/'shared';actual.mkdir();alias=self.base/'selected';alias.symlink_to(actual,target_is_directory=True)
        r=installer.install(SOURCE,alias)
        self.assertEqual(r['resolved_root'],str(actual.resolve()));self.assertIn('sharing',r['root_note']);self.assertEqual(list(actual.iterdir()),[])

    def test_unknown_manifest_and_backup_inside_discovery_are_rejected(self):
        self.dest.mkdir(parents=True);(self.dest/installer.MANIFEST).write_text('user file')
        with self.assertRaisesRegex(ValueError,'manifest'):self.apply()
        with self.assertRaisesRegex(ValueError,'Backups'):installer.install(SOURCE,self.dest,backup_base=self.dest/'backups')
        self.assertEqual((self.dest/installer.MANIFEST).read_text(),'user file')

    def test_missing_wrapper_dependency_is_reported_before_installation(self):
        source=self.base/'source';source.mkdir();shutil.copy(SOURCE/'SKILL.md',source/'SKILL.md')
        with self.assertRaisesRegex(ValueError,'required command rules'):installer.install(source,self.dest,apply=True,backup_base=self.backup)
        self.assertFalse(self.dest.exists())

    def test_installed_bundle_passes_existing_skill_discovery_check(self):
        project=self.base/'workspace';project.mkdir()
        subprocess.run([sys.executable,str(SOURCE/'scripts/init_project.py'),'--path',str(project)],check=True,capture_output=True)
        root=project/'.agents/skills';installer.install(SOURCE,root,apply=True,backup_base=self.backup)
        r=subprocess.run([sys.executable,str(root/'project-docs/scripts/check_skills.py'),'--no-user'],cwd=project,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_cli_json_plan_and_metadata_validate_without_network_or_agent(self):
        r=subprocess.run([sys.executable,str(SOURCE/'scripts/install_skills.py'),'--skills-dir',str(self.dest),'--dry-run','--json'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['status'],'planned');self.assertFalse(self.dest.exists())


if __name__=='__main__':unittest.main()
