#!/usr/bin/env python3
"""Export native plugin/extension packages plus portable skills from one bundle.

No host installation, configuration changes, network, hooks or MCP registration.
Default: all targets, immutable output under dist/plugins/<version>/all/.
"""
import argparse
import hashlib
import io
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path

from install_skills import bundle, same_tree, validate_skill

NAME='project-docs'
DESCRIPTION='Evidence-backed project documentation, phase handoffs, charts and Task hierarchy.'
STANDARD='https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
TARGETS=('claude-code','codex','antigravity','copilot','gemini-cli','cursor','agent-plugins','portable-skills')
VERSION=re.compile(r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$')


def json_bytes(value):return (json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()


def digest(files):
    h=hashlib.sha256()
    for path,raw in sorted(files.items()):h.update((path+'\0').encode());h.update(hashlib.sha256(raw).digest())
    return h.hexdigest()


def valid_version(value):
    if not isinstance(value,str) or not VERSION.fullmatch(value) or '..' in value:return False
    plain=value.split('+',1)[0]
    if '-' in plain:
        tokens=plain.split('-',1)[1].split('.')
        if any(not t or (t.isdigit() and len(t)>1 and t.startswith('0')) for t in tokens):return False
    if '+' in value and any(not t for t in value.split('+',1)[1].split('.')):return False
    return True


def manifests(target,version):
    basic={'name':NAME,'version':version,'description':DESCRIPTION}
    if target!='gemini-cli':basic['author']={'name':'project-docs maintainers'}
    if target=='claude-code':return {'.claude-plugin/plugin.json':basic}
    if target=='codex':return {'.codex-plugin/plugin.json':dict(basic,skills='./skills/')}
    if target=='cursor':return {'.cursor-plugin/plugin.json':basic}
    if target=='antigravity':return {'plugin.json':dict(basic,**{'$schema':'https://antigravity.google/schemas/v1/plugin.json'})}
    if target in ('copilot','agent-plugins'):return {'plugin.json':dict(basic,**{'$schema':STANDARD})}
    if target=='gemini-cli':return {'gemini-extension.json':basic}
    if target=='portable-skills':return {}
    raise ValueError('Unsupported package target: '+str(target))


def package_files(packages,target,version):
    prefix='' if target=='portable-skills' else 'skills/'
    result={prefix+name+'/'+path:raw for name,files in packages.items() for path,raw in files.items()}
    result.update({path:json_bytes(data) for path,data in manifests(target,version).items()})
    result['README.md']=(f'# project-docs — {target}\n\nVersion: {version}\n\n'
        'Contains the project-docs core and six workflow skills built from the same source. '
        'No automatic hooks, MCP servers, account credentials or agent-setting edits are included. '
        'See the release-level INSTALL.md and build-manifest.json for installation and verification. '
        'Use either the native plugin or standalone skills per agent to avoid duplicate entry points. '
        'Plugin namespacing/invocation depends on the host; inspect its picker after installation. '
        'Packaging validation alone does not establish live UI/workflow success.\n').encode()
    return result


def validate_package(files,target,version):
    expected=manifests(target,version)
    for path,data in expected.items():
        if json.loads(files[path])!=data:raise ValueError('Unexpected native manifest: '+path)
    prefix='' if target=='portable-skills' else 'skills/'
    names=[NAME]+[NAME+'-'+v for v in ('setup','check','update','rework','close-phase','test')]
    discovered=sorted(p for p in files if p.endswith('/SKILL.md'))
    if discovered!=sorted(prefix+n+'/SKILL.md' for n in names):raise ValueError('Expected exactly seven discoverable sibling skills.')
    for name in names:validate_skill(files[prefix+name+'/SKILL.md'],name)
    if prefix+NAME+'/rules/commands.md' not in files:raise ValueError('Adjacent shared core is missing.')
    for path in files:
        p=Path(path)
        if p.is_absolute() or '..' in p.parts or '\\' in path:raise ValueError('Unsafe package path: '+path)
    return names


def zip_bytes(files):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path,raw in sorted(files.items()):
            entry=zipfile.ZipInfo(NAME+'/'+path,date_time=(1980,1,1,0,0,0))
            entry.create_system=3;entry.external_attr=0o100644<<16;entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,raw)
    return out.getvalue()


def install_text(targets):
    lines=['# Local installation of exported packages','These commands are instructions, not commands executed by the builder. Review packages first. Keep this release directory in place while loading local plugins. Do not install both standalone and plugin copies into the same host.']
    if 'antigravity' in targets:lines+=['## Antigravity','From this release directory: `agy plugin install ./antigravity/project-docs`. App/IDE users can use their supported local-plugin picker.']
    if 'claude-code' in targets:lines+=['## Claude Code','Temporary local load: `claude --plugin-dir ./claude-code/project-docs`. Persistent install: `/plugin marketplace add /absolute/path/to/this-release`, then `/plugin install project-docs@project-docs-claude-local`.']
    if 'codex' in targets:lines+=['## Codex','Register this local marketplace: `codex plugin marketplace add /absolute/path/to/this-release`. Inspect `codex plugin marketplace list`, then on versions with CLI install use `codex plugin add project-docs@project-docs-codex-local`. Otherwise install from that source in the plugin picker. Adding a marketplace alone is not installation.']
    if 'copilot' in targets:lines+=['## Copilot / VS Code','Use Agent Customizations → Plugins → Install a plugin from source and select `copilot/project-docs`. Check enablement for the intended harness; this exporter does not edit VS Code settings.']
    if 'gemini-cli' in targets:lines+=['## Gemini CLI','From this release directory: `gemini extensions install ./gemini-cli/project-docs`. This is an extension, not an Antigravity plugin.']
    if 'cursor' in targets:lines+=['## Cursor','Add this local marketplace using the plugin UI/workflow supported by your installed Cursor version; its catalog is `.cursor-plugin/marketplace.json`. The native package is `cursor/project-docs`. If local plugin import is unavailable, use the portable-skill installer for Cursor. No unsupported CLI install command is invented here.']
    if 'agent-plugins' in targets:lines+=['## Agent Plugins 1.0 compatible clients','Load `agent-plugins/project-docs` using the client’s supported local-plugin import. This is standards-format packaging, not a claim that every client supports it.']
    if 'portable-skills' in targets:lines+=['## Portable fallback: Kilo, OpenCode, Hermes and other skill hosts','The seven siblings are under `portable-skills/project-docs/`. Run the bundled `project-docs/scripts/install_skills.py --agent kilo --dry-run`, then `--apply` (with reviewed `--backup-existing` when replacing conflicts). Other named targets include `opencode`, `hermes`, `cursor`, `antigravity`, `codex`, `claude-code`, `gemini-cli`, `copilot`; custom roots use `--skills-dir`.']
    lines+=['## Verify and update','Restart/reload the intended host, confirm the core plus six workflows are visible, and run a small read-only check in a documented test project. Record packaging/schema/native-validator checks separately from real invocation. Auto-generated snapshot versions include a content digest; explicit release versions must be bumped when content changes. Original hooks/auth/service access are not bypassed or configured.']
    return '\n\n'.join(lines)+'\n'


def export(source,targets=None,version=None,output=None):
    source=Path(source).resolve();targets=sorted(set(targets or TARGETS))
    if not targets or any(t not in TARGETS for t in targets):raise ValueError('Choose supported package targets.')
    packages=bundle(source)
    flat={name+'/'+p:raw for name,files in packages.items() for p,raw in files.items()}
    source_digest=digest(flat);version=version or '0.1.0-dev.g'+source_digest[:12]
    if not valid_version(version):raise ValueError('Use a semantic version without path separators.')
    selection='all' if set(targets)==set(TARGETS) else '-'.join(targets)
    output=Path(output).expanduser().resolve() if output else source/'dist/plugins'/version/selection
    if output==source or source.is_relative_to(output):raise ValueError('Output cannot replace the source checkout/its parent.')
    files={};artifacts=[]
    for target in targets:
        package=package_files(packages,target,version);names=validate_package(package,target,version)
        base=target+'/'+NAME
        files.update({base+'/'+p:raw for p,raw in package.items()})
        archive=NAME+'-'+target+'-'+version+'.zip';raw=zip_bytes(package);files[archive]=raw
        artifacts.append({'target':target,'directory':base,'archive':archive,'sha256':hashlib.sha256(raw).hexdigest(),
                          'tree_sha256':digest(package),'manifests':list(manifests(target,version)),'skills':names})
    if 'claude-code' in targets:
        files['.claude-plugin/marketplace.json']=json_bytes({'name':'project-docs-claude-local','metadata':{'description':DESCRIPTION},'owner':{'name':'project-docs maintainers'},'plugins':[{'name':NAME,'source':'./claude-code/'+NAME,'version':version}]})
    if 'codex' in targets:
        files['.agents/plugins/marketplace.json']=json_bytes({'name':'project-docs-codex-local','plugins':[{'name':NAME,'source':{'source':'local','path':'./codex/'+NAME},'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'},'category':'Productivity'}]})
    if 'cursor' in targets:
        files['.cursor-plugin/marketplace.json']=json_bytes({'name':'project-docs-cursor-local','owner':{'name':'project-docs maintainers'},'plugins':[{'name':NAME,'source':'./cursor/'+NAME}]})
    files['INSTALL.md']=install_text(targets).encode()
    metadata={'schema':'project-docs-plugin-export/v1','version':version,'source_bundle_sha256':source_digest,'targets':targets,'artifacts':artifacts,
              'verification':'Offline packaging only; no live installation, account access or UI success implied.',
              'files':{p:hashlib.sha256(raw).hexdigest() for p,raw in sorted(files.items())}}
    files['build-manifest.json']=json_bytes(metadata)
    if output.exists():
        if not same_tree(output,files):raise ValueError('Output already exists with different content; use a new output/version. Nothing overwritten.')
        return dict(metadata,status='unchanged',output=str(output))
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.plugin-export-',dir=output.parent) as staging:
        tree=Path(staging)/'release';tree.mkdir()
        for path,raw in files.items():
            p=tree/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        os.replace(tree,output)
    return dict(metadata,status='exported',output=str(output))


def check_export(root):
    root=Path(root).resolve();metadata=json.loads((root/'build-manifest.json').read_text())
    if metadata.get('schema')!='project-docs-plugin-export/v1' or not valid_version(metadata.get('version')):raise ValueError('Invalid build manifest.')
    hashes=metadata.get('files',{})
    if not isinstance(hashes,dict):raise ValueError('Invalid file inventory.')
    for path,expected in hashes.items():
        if Path(path).is_absolute() or '..' in Path(path).parts or '\\' in path:raise ValueError('Unsafe build path.')
        file=root/path
        if file.is_symlink() or not file.resolve().is_relative_to(root) or hashlib.sha256(file.read_bytes()).hexdigest()!=expected:raise ValueError('Changed/missing artifact: '+path)
    if {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}!=set(hashes)|{'build-manifest.json'}:raise ValueError('Unexpected export files.')
    for artifact in metadata['artifacts']:
        target=artifact['target'];base=root/artifact['directory']
        if target not in TARGETS or not base.resolve().is_relative_to(root):raise ValueError('Invalid target directory.')
        files={p.relative_to(base).as_posix():p.read_bytes() for p in base.rglob('*') if p.is_file()}
        validate_package(files,target,metadata['version'])
        if digest(files)!=artifact['tree_sha256']:raise ValueError('Package tree checksum differs.')
        archive_path=root/artifact['archive']
        if not archive_path.resolve().is_relative_to(root):raise ValueError('Archive outside release.')
        archive_raw=archive_path.read_bytes()
        if hashlib.sha256(archive_raw).hexdigest()!=artifact['sha256']:raise ValueError('Archive checksum differs.')
        with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
            names=[NAME+'/'+p for p in sorted(files)]
            if sorted(archive.namelist())!=names or len(archive.namelist())!=len(names):raise ValueError('Archive inventory differs.')
            if any(archive.read(NAME+'/'+p)!=raw for p,raw in files.items()):raise ValueError('Archive content differs.')
    return {'status':'verified','output':str(root),'version':metadata['version'],'targets':metadata['targets'],'verification':metadata['verification']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--target',choices=TARGETS,action='append')
    parser.add_argument('--all',action='store_true')
    parser.add_argument('--version')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--check',type=Path,help='Read-only checksums, layout and ZIP verification of an export.')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    if args.all and args.target:parser.error('Choose --all or --target, not both.')
    if args.check and (args.all or args.target or args.version or args.output):parser.error('--check cannot be combined with build options.')
    try:result=check_export(args.check) if args.check else export(args.source,args.target,args.version,args.output)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError,zipfile.BadZipFile) as error:
        print(json.dumps({'status':'error','error':str(error)}) if args.json else 'ERROR: '+str(error));return 1
    if args.json:print(json.dumps(result,indent=2))
    else:
        print(result['status']+': '+result['output']);print('version: '+result['version'])
        print('targets: '+', '.join(result['targets']))
        print(result.get('verification','Offline packaging; inspect INSTALL.md and verify native hosts separately.'))
    return 0


if __name__=='__main__':raise SystemExit(main())
