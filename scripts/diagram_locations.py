#!/usr/bin/env python3
"""Check or relocate project-owned Excalidraw files to project/diagrams/.

Default: read-only check. --plan previews; --apply moves original bytes and repairs
unambiguous text/spec references with intact backups outside the repository.
Does not execute generators or claim semantic/visual verification.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

SKIP={'.git','node_modules','.venv','venv','__pycache__','dist','build','.agents','.agent',
      '.claude','.codex','.gemini','.copilot','.cursor','.kilo','.hermes'}
TEXT={'.md','.html','.json','.py','.js','.ts','.sh','.yaml','.yml','.toml','.txt'}
HISTORY=('project/decisions/','project/backlog/migrations/','project/results/tests/',
         '.project-docs/rework/','.project-docs/runtime/')
CODE={'.py','.js','.ts','.sh'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def walk(root):
    for folder,dirs,names in os.walk(root,followlinks=False):
        base=Path(folder)
        dirs[:]=sorted(d for d in dirs if d not in SKIP and not (base/d).is_symlink()
                       and not (base/d).relative_to(root).as_posix().startswith('.project-docs/runtime'))
        for name in sorted(names):yield base/name


def inspect(root):
    root=Path(root).resolve();destination=root/'project/diagrams';findings=[];files=[]
    if not destination.resolve().is_relative_to(root):
        return {'status':'failed','files':[],'findings':[{'code':'unsafe-destination','where':'project/diagrams','message':'Canonical destination resolves outside this project.'}]}
    for path in walk(root):
        if path.suffix.lower()!='.excalidraw':continue
        relative=path.relative_to(root).as_posix();row={'path':relative}
        if path.is_symlink():
            row['status']='blocked-symlink';findings.append({'code':'diagram-symlink','where':relative,'message':'Resolve ownership/target without following an external symlink.'})
        else:
            row['sha256']=sha(path.read_bytes());row['status']='canonical' if path.is_relative_to(destination) else 'misplaced'
            if row['status']=='misplaced':findings.append({'code':'misplaced-excalidraw','where':relative,'message':'Editable project diagram must be moved to project/diagrams/; an old owner-map/rule entry is not an exemption.'})
        files.append(row)
    return {'status':'failed' if findings else 'passed','files':files,'findings':findings,
            'scope':'Repository files outside dependency/build caches, agent installations and runtime backups. Directory symlinks are not followed.'}


def plan(root):
    root=Path(root).resolve();report=inspect(root);moves=[];reserved={p.relative_to(root).as_posix() for p in walk(root)};errors=[]
    if any(f['code'] in ('diagram-symlink','unsafe-destination') for f in report['findings']):errors.extend(report['findings'])
    for row in report['files']:
        if row['status']!='misplaced':continue
        source=root/row['path'];raw=source.read_bytes()
        try:
            data=json.loads(raw)
            if not isinstance(data,dict) or data.get('type')!='excalidraw' or not isinstance(data.get('elements'),list):raise ValueError('Expected an Excalidraw scene with elements.')
        except (ValueError,UnicodeError) as error:
            errors.append({'code':'invalid-diagram','where':row['path'],'message':str(error)});continue
        stem=re.sub(r'[^a-z0-9-]+','-',source.stem.lower()).strip('-') or 'diagram'
        target='project/diagrams/'+stem+'.excalidraw'
        if target in reserved:
            target='project/diagrams/'+stem+'--'+sha(row['path'].encode())[:10]+'.excalidraw'
        if target in reserved:
            errors.append({'code':'destination-conflict','where':target,'message':'Distinct files must not overwrite one another.'});continue
        reserved.add(target);moves.append({'from':row['path'],'to':target,'sha256':row['sha256']})
    edits={};review=[]
    for path in walk(root):
        relative=path.relative_to(root).as_posix()
        if path.suffix.lower() not in TEXT or path.is_symlink() or relative.startswith(HISTORY):continue
        try:raw=path.read_bytes();text=raw.decode('utf-8')
        except (OSError,UnicodeError):continue
        changed=text
        mappings={}
        for move in moves:
            old=root/move['from'];new=root/move['to']
            old_relative=os.path.relpath(old,path.parent).replace(os.sep,'/')
            new_relative=os.path.relpath(new,path.parent).replace(os.sep,'/')
            for a,b in [(move['from'],move['to']),(old_relative,new_relative)]:
                for prefix in ('','./'):
                    mappings[prefix+a]=prefix+b
                    mappings[quote(prefix+a,safe='/')]=quote(prefix+b,safe='/')
        if mappings:
            # One pass: never rewrite text newly inserted by another move.
            pattern=re.compile(r'(?<![\w/.:?=&%+-])(?:'+'|'.join(re.escape(k) for k in sorted(mappings,key=len,reverse=True))+r')(?![\w.-])')
            changed=pattern.sub(lambda match:mappings[match[0]],changed)
        if changed!=text:edits[relative]=(raw,changed.encode('utf-8'))
        if path.suffix.lower() in CODE and any(Path(m['from']).name in text for m in moves):
            review.append({'path':relative,'reason':'Review generator/consumer output construction, including split/dynamic paths; verify by running its documented check/generator.'})
    return {'status':'blocked' if errors else 'planned','root':str(root),'moves':moves,
            'reference_files':sorted(edits),'manual_review':review,'findings':errors,
            'limits':'Only unambiguous local text references are patched. Historical records and remote URLs are retained. Generators, embedded diagram links, binary-document references and rendered diagrams need explicit follow-up verification.'},edits


def replace_bytes(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    handle=tempfile.NamedTemporaryFile(prefix='.diagram-edit-',dir=path.parent,delete=False)
    temporary=Path(handle.name)
    try:
        with handle:handle.write(raw)
        os.chmod(temporary,path.stat().st_mode)
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


def apply(root,backup_base=None):
    root=Path(root).resolve();report,edits=plan(root)
    if report['status']=='blocked':return report
    if not report['moves']:return dict(report,status='unchanged',location_check=inspect(root))
    base=(Path(backup_base).expanduser() if backup_base else Path.home()/'.local/share/skill-backups/project-docs-diagrams').resolve()
    if base==root or base.is_relative_to(root):raise ValueError('Original backups must be outside the project, not rediscovered as misplaced diagrams.')
    base.mkdir(parents=True,exist_ok=True);backup=Path(tempfile.mkdtemp(prefix='relocation-',dir=base))
    originals={m['from']:(root/m['from']).read_bytes() for m in report['moves']}
    originals.update({name:raw for name,(raw,_) in edits.items()})
    for relative,raw in originals.items():
        output=backup/'originals'/relative;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(raw)
    (backup/'plan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    moved=[];written=[]
    try:
        for move in report['moves']:
            old=root/move['from'];new=root/move['to']
            if sha(old.read_bytes())!=move['sha256']:raise RuntimeError('Source changed after planning: '+move['from'])
            if new.exists() or new.is_symlink():raise RuntimeError('Destination appeared after planning: '+move['to'])
            new.parent.mkdir(parents=True,exist_ok=True);os.replace(old,new);moved.append(move)
            if sha(new.read_bytes())!=move['sha256']:raise RuntimeError('Moved diagram bytes differ.')
        for relative,(old,new) in edits.items():
            path=root/relative
            if path.read_bytes()!=old:raise RuntimeError('Reference file changed after planning: '+relative)
            replace_bytes(path,new);written.append(relative)
    except Exception as error:
        try:
            for relative in reversed(written):replace_bytes(root/relative,originals[relative])
            for move in reversed(moved):os.replace(root/move['to'],root/move['from'])
        except Exception as restore_error:raise RuntimeError(f'Relocation failed; originals retained at {backup}; recovery needs attention: {restore_error}') from error
        raise RuntimeError('Relocation failed; original files/references restored. Backup: '+str(backup)) from error
    report.update(status='relocated',backup=str(backup),location_check=inspect(root))
    (backup/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    mode=parser.add_mutually_exclusive_group();mode.add_argument('--plan',action='store_true');mode.add_argument('--apply',action='store_true')
    parser.add_argument('--backup-dir',type=Path);parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    try:
        if not args.root.is_dir():raise ValueError('Project root does not exist.')
        report=apply(args.root,args.backup_dir) if args.apply else plan(args.root)[0] if args.plan else inspect(args.root)
    except (OSError,ValueError,RuntimeError) as error:
        print(json.dumps({'status':'error','error':str(error)}) if args.json else 'ERROR: '+str(error));return 1
    if args.json:print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print('Diagram locations: '+report['status'])
        for item in report.get('findings',[]):print(item['where']+': '+item['message'])
        for move in report.get('moves',[]):print(move['from']+' -> '+move['to'])
        if report.get('backup'):print('backup: '+report['backup'])
        if report.get('limits'):print(report['limits'])
    return 1 if report['status'] in ('failed','blocked') or report.get('location_check',{}).get('status')=='failed' else 0


if __name__=='__main__':raise SystemExit(main())
