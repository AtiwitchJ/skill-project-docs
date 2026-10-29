#!/usr/bin/env python3
"""Install seven discoverable skills into ONE selected agent root, with local copies.

Default is a read-only plan. --apply writes; --backup-existing explicitly permits
moving conflicting entries intact outside discovery before replacing them.
No network, package installs, account access or companion-skill replacement.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

VERBS=('setup','check','update','rework','close-phase','test')
ROOTS={'antigravity':'.gemini/config/skills','codex':'.agents/skills',
       'claude-code':'.claude/skills','gemini-cli':'.gemini/skills','copilot':'.copilot/skills'}
FOLDERS=('rules','scripts','templates','integrations','commands','assets','examples')
MANIFEST='.project-docs-bundle.json'


def validate_skill(raw,name):
    text=raw.decode('utf-8')
    if not text.startswith('---\n') or '\n---' not in text[4:]:raise ValueError('Missing frontmatter: '+name)
    head=text.split('---',2)[1]
    found=re.search(r'^name:\s*[\"\']?([a-z0-9-]+)[\"\']?\s*$',head,re.M)
    if not found or found[1]!=name or not re.search(r'^description:\s*\S',head,re.M):raise ValueError('Invalid skill metadata: '+name)


def bundle(source):
    source=Path(source).resolve();core={}
    for name in ('SKILL.md','README.md','AGENTS.md','LICENSE'):
        path=source/name
        if path.is_file():core[name]=path.read_bytes()
    if 'SKILL.md' not in core:raise ValueError('Source must contain the project-docs core.')
    validate_skill(core['SKILL.md'],'project-docs')
    for folder in FOLDERS:
        base=source/folder
        for path in sorted(base.rglob('*')):
            if any(p in ('__pycache__','.git','.DS_Store') for p in path.relative_to(base).parts) or path.suffix=='.pyc':continue
            if path.is_symlink():raise ValueError('Source resource symlinks must be reviewed/materialized first: '+str(path))
            if path.is_file():core[path.relative_to(source).as_posix()]=path.read_bytes()
    if 'rules/commands.md' not in core or 'rules/rework.md' not in core:raise ValueError('Source lacks the required command rules.')
    if 'README.md' in core:
        core['README.md']=core['README.md'].replace(b'[skill entry points](skills/)',b'[bundled entry-point sources](skill-adapters/)')
    result={'project-docs':core}
    for verb in VERBS:
        name='project-docs-'+verb
        candidate=source/'skills'/name/'SKILL.md'
        if not candidate.is_file():candidate=source/'skill-adapters'/(name+'.md')
        if not candidate.is_file():raise ValueError('Missing portable skill entry point: '+name)
        raw=candidate.read_bytes();validate_skill(raw,name)
        result[name]={'SKILL.md':raw}
        # Preserve reinstall sources without nested discoverable SKILL.md copies.
        core['skill-adapters/'+name+'.md']=raw
    return result


def same_tree(path,files):
    if path.is_symlink() or not path.is_dir():return False
    entries=[p for p in path.rglob('*') if not any(part in ('__pycache__','.DS_Store') for part in p.relative_to(path).parts) and p.suffix!='.pyc']
    if any(p.is_symlink() for p in entries):return False
    actual={p.relative_to(path).as_posix() for p in entries if p.is_file()}
    return actual==set(files) and all((path/name).read_bytes()==raw for name,raw in files.items())


def install(source,root,apply=False,backup_existing=False,backup_base=None):
    source=Path(source).resolve();requested=Path(root).expanduser().absolute();root=requested.resolve()
    if root==source or (source.is_relative_to(root/'project-docs') and source!=root/'project-docs'):raise ValueError('Destination would replace the source checkout.')
    if root.is_relative_to(source) and root.relative_to(source).parts[0] in (*FOLDERS,'skills','skill-adapters'):
        raise ValueError('Destination cannot be inside packaged source resources.')
    if root.exists() and not root.is_dir():raise ValueError('Skills root is not a directory.')
    backup_base=Path(backup_base).expanduser().resolve() if backup_base else Path.home()/'.local/share/skill-backups/project-docs-bundle'
    backup_base=backup_base.resolve()
    if backup_base==root or backup_base.is_relative_to(root):raise ValueError('Backups must be outside the skill discovery root.')
    packages=bundle(source);actions=[]
    for name,files in packages.items():
        target=root/name
        if same_tree(target,files):action='unchanged'
        elif target.exists() or target.is_symlink():action='backup-and-replace' if backup_existing else 'conflict'
        else:action='create'
        actions.append({'name':name,'action':action,'path':str(target)})
    digest=hashlib.sha256()
    for name,files in packages.items():
        for path,raw in sorted(files.items()):digest.update((name+'/'+path+'\0').encode());digest.update(hashlib.sha256(raw).digest())
    report={'status':'planned','requested_root':str(requested),'resolved_root':str(root),'source':str(source),
            'bundle_sha256':digest.hexdigest(),'skills':actions,'backup':None,
            'limits':'Filesystem packaging/discovery layout verified; restart/reload and verify the target agent UI separately. No application or account settings changed.'}
    if requested!=root:report['root_note']='Selected path resolves through symlinks; other agents sharing this root also see its updates.'
    if any(a['action']=='conflict' for a in actions):report['status']='blocked';return report
    manifest=root/MANIFEST
    if manifest.exists() or manifest.is_symlink():
        try:owned=not manifest.is_symlink() and json.loads(manifest.read_text()).get('schema')=='project-docs-bundle/v1'
        except (ValueError,AttributeError,OSError):owned=False
        if not owned:raise ValueError('Unrecognized existing bundle manifest; leave it intact and resolve manually.')
    if not apply:return report
    if all(a['action']=='unchanged' for a in actions):report['status']='unchanged';return report
    root.parent.mkdir(parents=True,exist_ok=True);root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.project-docs-stage-',dir=root.parent) as staging:
        stage=Path(staging)
        for name,files in packages.items():
            for relative,raw in files.items():
                output=stage/name/relative;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(raw)
        # Capture provenance only for an actual source checkout, not its parent project.
        def git(*args):
            try:
                r=subprocess.run(['git',*args],cwd=source,capture_output=True,text=True)
                return r.stdout.strip() if r.returncode==0 else None
            except OSError:return None
        checkout=git('rev-parse','--show-toplevel')
        provenance={'commit':git('rev-parse','HEAD'),'dirty':bool(git('status','--porcelain'))} if checkout and Path(checkout).resolve()==source else {'commit':None,'dirty':None}
        metadata={'schema':'project-docs-bundle/v1','bundle_sha256':report['bundle_sha256'],'source':str(source),'provenance':provenance,'skills':list(packages)}
        (stage/MANIFEST).write_text(json.dumps(metadata,indent=2)+'\n')
        backup=None;moved=[];created=[];manifest_moved=False;manifest_written=False
        try:
            need_backup=any(a['action']=='backup-and-replace' for a in actions) or manifest.exists()
            if need_backup:
                backup_base.mkdir(parents=True,exist_ok=True)
                backup=Path(tempfile.mkdtemp(prefix='activation-',dir=backup_base));report['backup']=str(backup)
            for a in actions:
                name=a['name'];target=root/name
                if a['action']=='unchanged':continue
                if a['action']=='backup-and-replace':os.replace(target,backup/name);moved.append(name)
                elif target.exists() or target.is_symlink():raise RuntimeError('Destination changed after preflight: '+str(target))
                os.replace(stage/name,target);created.append(name)
            if manifest.exists():os.replace(manifest,backup/MANIFEST);manifest_moved=True
            os.replace(stage/MANIFEST,manifest);manifest_written=True
        except Exception as error:
            try:
                if manifest_written:os.replace(manifest,stage/MANIFEST)
                if manifest_moved:os.replace(backup/MANIFEST,manifest)
                for name in reversed(created):
                    recovery=stage/('failed-'+name);os.replace(root/name,recovery)
                for name in reversed(moved):os.replace(backup/name,root/name)
            except Exception as restore_error:
                raise RuntimeError(f'Install failed; original entries retained at {backup}; restore needs attention: {restore_error}') from error
            raise RuntimeError('Install failed; previous entries restored: '+str(error)) from error
    report['status']='installed';return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    target=parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--agent',choices=ROOTS)
    target.add_argument('--skills-dir',type=Path,help='Explicit discovery root for another agent/workspace.')
    parser.add_argument('--source',type=Path,default=Path(__file__).resolve().parent.parent)
    mode=parser.add_mutually_exclusive_group();mode.add_argument('--apply',action='store_true');mode.add_argument('--dry-run',action='store_true')
    parser.add_argument('--backup-existing',action='store_true')
    parser.add_argument('--backup-dir',type=Path)
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    root=args.skills_dir or Path.home()/ROOTS[args.agent]
    try:report=install(args.source,root,args.apply,args.backup_existing,args.backup_dir)
    except (OSError,ValueError,RuntimeError) as e:
        print(json.dumps({'status':'error','error':str(e)}) if args.json else 'ERROR: '+str(e));return 1
    if args.agent=='codex':report['root_note']='Codex user skills use a shared .agents/skills root; other agents reading it also see changes.'
    if args.agent=='claude-code':report['legacy_note']='Existing .claude/commands files are untouched. Same-named native skills take precedence; review old adapters separately.'
    if args.json:print(json.dumps(report,indent=2))
    else:
        print(report['status']+': '+report['resolved_root'])
        for row in report['skills']:print(row['action']+': '+row['name'])
        for field in ('backup','root_note','legacy_note'):
            if report.get(field):print(field+': '+report[field])
        print(report['limits'])
    return 1 if report['status']=='blocked' else 0


if __name__=='__main__':raise SystemExit(main())
