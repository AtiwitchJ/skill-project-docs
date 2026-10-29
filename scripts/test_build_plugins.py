"""All-host packaging uses identical skills; offline exports do not install hosts."""
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import build_plugins as plugins
import install_skills

SOURCE=Path(__file__).resolve().parent.parent


class PluginPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_every_target_has_correct_native_marker_and_same_seven_skills(self):
        packages=install_skills.bundle(SOURCE);version='1.2.3'
        markers={'claude-code':'.claude-plugin/plugin.json','codex':'.codex-plugin/plugin.json',
                 'antigravity':'plugin.json','copilot':'plugin.json','gemini-cli':'gemini-extension.json',
                 'cursor':'.cursor-plugin/plugin.json','agent-plugins':'plugin.json'}
        for target in plugins.TARGETS:
            with self.subTest(target=target):
                files=plugins.package_files(packages,target,version)
                self.assertEqual(len(plugins.validate_package(files,target,version)),7)
                if target!='portable-skills':self.assertIn(markers[target],files)
                for name,content in packages.items():
                    prefix='' if target=='portable-skills' else 'skills/'
                    self.assertEqual(files[prefix+name+'/SKILL.md'],content['SKILL.md'])
                self.assertFalse(any(p.startswith(('hooks/','mcp.json','.mcp.json')) for p in files))

    def test_native_manifest_shapes_do_not_copy_other_host_schema(self):
        self.assertEqual(plugins.manifests('gemini-cli','1.0.0')['gemini-extension.json']['name'],'project-docs')
        self.assertEqual(plugins.manifests('antigravity','1.0.0')['plugin.json']['$schema'],'https://antigravity.google/schemas/v1/plugin.json')
        self.assertEqual(plugins.manifests('copilot','1.0.0')['plugin.json']['$schema'],plugins.STANDARD)
        self.assertEqual(plugins.manifests('codex','1.0.0')['.codex-plugin/plugin.json']['skills'],'./skills/')
        self.assertIn('cursor',install_skills.ROOTS)
        self.assertEqual(install_skills.ROOTS['kilo'],'.kilo/skills')
        self.assertEqual(install_skills.ROOTS['opencode'],'.config/opencode/skills')
        self.assertEqual(install_skills.ROOTS['hermes'],'.hermes/skills')

    def test_all_export_verifies_archives_relative_catalogs_and_safe_portable_fallback(self):
        output=self.root/'release';r=plugins.export(SOURCE,output=output)
        self.assertEqual(len(r['artifacts']),8)
        self.assertEqual(plugins.check_export(output)['status'],'verified')
        for catalog,expected in [('.claude-plugin/marketplace.json','./claude-code/project-docs'),('.cursor-plugin/marketplace.json','./cursor/project-docs')]:
            value=json.loads((output/catalog).read_text());self.assertEqual(value['plugins'][0]['source'],expected);self.assertTrue((output/expected).is_dir())
        codex=json.loads((output/'.agents/plugins/marketplace.json').read_text())
        self.assertTrue((output/codex['plugins'][0]['source']['path']).is_dir())
        self.assertEqual(codex['plugins'][0]['policy']['installation'],'AVAILABLE')
        self.assertEqual(install_skills.install(output/'portable-skills/project-docs/project-docs',self.root/'isolated-skills',apply=True,backup_base=self.root/'backups')['status'],'installed')

    def test_repeat_is_deterministic_and_never_overwrites_modified_output(self):
        output=self.root/'release';first=plugins.export(SOURCE,['claude-code'],output=output)
        second=plugins.export(SOURCE,['claude-code'],output=output)
        self.assertEqual(second['status'],'unchanged');self.assertEqual(first['artifacts'],second['artifacts'])
        f=output/'claude-code/project-docs/README.md';f.write_text('local changes')
        with self.assertRaisesRegex(ValueError,'Nothing overwritten'):plugins.export(SOURCE,['claude-code'],output=output)
        self.assertEqual(f.read_text(),'local changes')

    def test_content_changes_change_snapshot_version_and_archive_digest(self):
        self.assertNotEqual(plugins.digest({'a':b'a'}),plugins.digest({'a':b'b'}))
        packages=install_skills.bundle(SOURCE);r1=plugins.export(SOURCE,['copilot'],output=self.root/'one')
        packages['project-docs']['notes.txt']=b'changed content'
        with mock.patch.object(plugins,'bundle',return_value=packages):r2=plugins.export(SOURCE,['copilot'],output=self.root/'two')
        self.assertNotEqual(r1['version'],r2['version']);self.assertNotEqual(r1['artifacts'][0]['sha256'],r2['artifacts'][0]['sha256'])

    def test_corruption_and_extra_files_are_detected_read_only(self):
        output=self.root/'release';plugins.export(SOURCE,['gemini-cli'],output=output)
        archive=next(output.glob('*.zip'));archive.write_bytes(b'bad archive')
        with self.assertRaisesRegex(ValueError,'Changed/missing'):plugins.check_export(output)
        self.assertEqual(archive.read_bytes(),b'bad archive')
        other=self.root/'other';plugins.export(SOURCE,['cursor'],output=other);(other/'unexpected').write_text('x')
        with self.assertRaisesRegex(ValueError,'Unexpected'):plugins.check_export(other)

    def test_unsafe_paths_and_incomplete_skill_sets_are_rejected(self):
        packages=install_skills.bundle(SOURCE);files=plugins.package_files(packages,'codex','1.0.0')
        files['../outside']=b'x'
        with self.assertRaisesRegex(ValueError,'Unsafe'):plugins.validate_package(files,'codex','1.0.0')
        files.pop('../outside');files.pop('skills/project-docs-check/SKILL.md')
        with self.assertRaisesRegex(ValueError,'seven'):plugins.validate_package(files,'codex','1.0.0')

    @unittest.skipUnless(shutil.which('claude') or shutil.which('agy'),'Native plugin validators not installed')
    def test_available_native_validators_accept_packages_and_catalog(self):
        output=self.root/'native';plugins.export(SOURCE,['claude-code','antigravity'],output=output)
        checks=[]
        if shutil.which('claude'):
            checks.extend([['claude','plugin','validate',str(output/'claude-code/project-docs'),'--strict','--json'],
                           ['claude','plugin','validate',str(output/'.claude-plugin/marketplace.json'),'--strict','--json']])
        if shutil.which('agy'):checks.append(['agy','plugin','validate',str(output/'antigravity/project-docs')])
        for command in checks:
            with self.subTest(validator=command[0],path=command[3]):
                r=subprocess.run(command,capture_output=True,text=True,timeout=60)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_invalid_versions_and_targets_fail_before_any_output_is_written(self):
        for value in ('../bad','1.0.0-01','1.0.0-.','1.0.0+','1.0','01.0.0'):
            with self.subTest(value=value),self.assertRaises(ValueError):plugins.export(SOURCE,['claude-code'],value,self.root/'output')
        with self.assertRaises(ValueError):plugins.export(SOURCE,['imaginary-plugin'],output=self.root/'output')
        self.assertFalse((self.root/'output').exists())

    def test_zip_has_fixed_safe_metadata_and_exact_bytes(self):
        files={'SKILL.md':b'hello','data/a.json':b'{}'}
        self.assertEqual(plugins.zip_bytes(files),plugins.zip_bytes(files))
        import io
        with zipfile.ZipFile(io.BytesIO(plugins.zip_bytes(files))) as z:
            self.assertEqual(z.read('project-docs/SKILL.md'),b'hello')
            self.assertTrue(all(x.date_time==(1980,1,1,0,0,0) and not x.filename.startswith('/') for x in z.infolist()))


if __name__=='__main__':unittest.main()
