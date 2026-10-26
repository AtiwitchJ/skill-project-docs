#!/usr/bin/env python3
"""Run tests and automatically create JSON + Markdown/HTML charts/failure flows.

unittest: native observed lifecycle. command: argv subprocess + optional JUnit.
junit: import existing XML, retaining unknown phase/timing rather than guessing.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime,timezone
from pathlib import Path

from integration_core import save
from test_results import coverage_data, import_junit, run_unittest, summarize
from test_reporting import datasets, write_report


def stamp():return datetime.now(timezone.utc).isoformat()


def context(root,selector,explicit=None):
    def git(*args):
        try:p=subprocess.run(['git',*args],cwd=root,capture_output=True)
        except OSError:return b''
        return p.stdout if p.returncode==0 else b''
    revision=git('rev-parse','HEAD').decode().strip() or None
    diff=hashlib.sha256(git('diff','HEAD')).hexdigest()
    source=Path(selector.get('start_dir',root))
    hashes=[]
    if selector.get('runner')=='unittest' and source.is_dir():
        hashes=[(str(p.relative_to(source)),hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(source.rglob('*.py'))]
    metadata={"python":platform.python_version(),"platform":platform.system(),"revision":revision,"tracked_diff_sha256":diff,"selector":selector,"test_source_sha256":hashlib.sha256(json.dumps(hashes).encode()).hexdigest()}
    signature=hashlib.sha256(json.dumps({"explicit":explicit} if explicit else metadata,sort_keys=True).encode()).hexdigest()
    return signature,metadata


def history(directory,current,signature):
    result=[]
    if not directory.exists():return result
    for path in directory.rglob('results.json'):
        if path.parent.resolve()==current.resolve():continue
        try:
            raw=path.read_bytes();run=json.loads(raw)
            if run.get('schema')!='project-docs-tests/v1' or run.get('context')!=signature:continue
            result.append({k:run[k] for k in ('started','summary','duration_s','cases')} | {"source":str(path.resolve()),"source_sha256":hashlib.sha256(raw).hexdigest()})
        except (ValueError,KeyError,OSError):continue
    result.sort(key=lambda r:r['started'])
    # Keep a bounded window and disclose it, rather than silently claim all history.
    return result[-30:]


def attach(root,phase,directory):
    spec_path=root/'.project-docs/presentations'/f'phase-{phase}.json'
    spec=json.loads(spec_path.read_text()) if spec_path.exists() else {"version":1}
    spec['test_run']=str((directory/'results.json').relative_to(root))
    save(spec_path,spec)
    command=[sys.executable,str(Path(__file__).with_name('sync_presentation.py')),str(phase)]
    result=subprocess.run(command,cwd=root,capture_output=True,text=True)
    if result.returncode:raise RuntimeError('Test report was saved, but phase sync failed: '+result.stdout+result.stderr)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--output',type=Path)
    parser.add_argument('--history',type=Path)
    parser.add_argument('--context',help='Explicit comparison context; caller is responsible for comparable inputs')
    parser.add_argument('--coverage',type=Path,help='Existing coverage.py JSON, never inferred from passed tests')
    parser.add_argument('--phase',type=int,help='Attach latest run and sync existing phase MD/HTML; never change Task marks')
    parser.add_argument('--label',default='',help='Describe fixtures/synthetic data or the test environment')
    sub=parser.add_subparsers(dest='mode',required=True)
    p=sub.add_parser('unittest');p.add_argument('--start-dir',default='.');p.add_argument('--pattern',default='test*.py');p.add_argument('--top-level-dir');p.add_argument('--failfast',action='store_true')
    p=sub.add_parser('junit');p.add_argument('file',type=Path)
    p=sub.add_parser('command');p.add_argument('--junit',type=Path);p.add_argument('--timeout',type=float);p.add_argument('argv',nargs=argparse.REMAINDER)
    args=parser.parse_args(argv);root=args.root.resolve();started=stamp()
    if not root.is_dir():parser.error('root must exist')
    output=args.output or Path('project/results/tests')/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    directory=(root/output).resolve()
    if directory.exists() and any(directory.iterdir()):parser.error('output must be empty: each run is immutable')
    if args.phase is not None:
        phase_dir=root/'project/phases'/f'phase-{args.phase}'
        if not directory.is_relative_to(root) or not all((phase_dir/p).is_file() for p in ('tasks.md','presentation.html')):parser.error('--phase requires an output inside the project and existing tasks.md/presentation.html')
    directory.mkdir(parents=True,exist_ok=True);selector={"runner":args.mode}
    result={"cases":[],"duration_s":None,"exit_code":2,"runner":args.mode,"stage_precision":"unknown","limitations":[]}
    previous=Path.cwd()
    try:
        os.chdir(root)
        if args.mode=='unittest':
            start=(root/args.start_dir).resolve();selector.update(start_dir=str(start),pattern=args.pattern,failfast=args.failfast)
            result=run_unittest(start,args.pattern,(root/args.top_level_dir).resolve() if args.top_level_dir else None,args.failfast)
            (directory/'runner.log').write_text(result.pop('log'),encoding='utf-8')
        elif args.mode=='junit':
            source=(root/args.file).resolve();shutil.copyfile(source,directory/'junit.xml');selector['input']=str(source)
            result=import_junit(directory/'junit.xml')
        else:
            command=args.argv[1:] if args.argv and args.argv[0]=='--' else args.argv
            if not command:raise ValueError('command mode needs argv after --')
            if args.timeout is not None and args.timeout<=0:raise ValueError('timeout must be positive')
            original_command=list(command)
            has_placeholder=any('{junit}' in arg for arg in command)
            junit=(root/args.junit).resolve() if args.junit else directory/'junit.xml' if has_placeholder else None
            command=[arg.replace('{junit}',str(junit)) for arg in command]
            if junit and junit.exists():raise ValueError('JUnit output already exists; use a new path to avoid stale evidence')
            selector['argv']=original_command;clock=time.perf_counter()
            with (directory/'stdout.log').open('wb') as stdout,(directory/'stderr.log').open('wb') as stderr:
                try:execution=subprocess.run(command,cwd=root,stdout=stdout,stderr=stderr,timeout=args.timeout,check=False);code=execution.returncode
                except subprocess.TimeoutExpired:code=124;result['runner_error']='Command timed out; partial results may be incomplete.'
            wall=time.perf_counter()-clock
            result['process_exit_code']=code
            if junit and junit.exists():
                if junit.resolve()!=(directory/'junit.xml').resolve():shutil.copyfile(junit,directory/'junit.xml')
                imported=import_junit(directory/'junit.xml');result.update(imported)
                code=code or imported['exit_code']
            elif junit:result['runner_error']='Command did not produce the requested fresh JUnit file.';code=code or 2
            result.update(duration_s=wall,exit_code=code,runner='command')
            result['limitations'].append('Subprocess exit status and wall time are observed; lifecycle stages remain unknown without native instrumentation.')
        if args.coverage:
            source=(root/args.coverage).resolve();shutil.copyfile(source,directory/'coverage-input.json')
            result['coverage']=coverage_data(directory/'coverage-input.json')
            result['coverage']['source_sha256']=hashlib.sha256((directory/'coverage-input.json').read_bytes()).hexdigest()
    except (Exception,KeyboardInterrupt) as exc:
        result['exit_code']=130 if isinstance(exc,KeyboardInterrupt) else result.get('process_exit_code') or 2
        result['runner_error']=traceback.format_exc();result['limitations'].append('Collection/import did not complete; no missing case result was fabricated.')
    finally:os.chdir(previous)
    signature,metadata=context(root,selector,args.context)
    result.update(schema='project-docs-tests/v1',started=started,finished=stamp(),selector=selector,context=signature,environment=metadata,disclaimer=args.label)
    result['logs']=[p.name for p in directory.glob('*.log')]
    result['inputs']=[{"path":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in directory.glob('*.xml')]
    result['summary']=summarize(result)
    result['status']='passed' if result['exit_code']==0 and result['summary']['outcomes']['passed'] else 'not_verified' if result['exit_code']==0 else 'failed'
    result['tests']=result['summary']['test_cases'];result['failures']=sum(result['summary']['outcomes'][s] for s in ('failed','unexpected_success','interrupted'));result['errors']=result['summary']['outcomes']['error']
    history_dir=(root/(args.history or 'project/results/tests')).resolve();result['history']=history(history_dir,directory,signature)
    result['limitations'].extend(['History uses at most 30 earlier matching recorded contexts; no one-run flakiness conclusion. Dependencies, input data and external state are not fully fingerprinted.','Coverage and branch coverage are unavailable unless measured by a supplied coverage file.','Report generation does not alter task status or diagnose root cause.'])
    result['datasets'],result['chart_specs'],result['dimensions']=datasets(result)
    save(directory/'results.json',result)
    rendered=write_report(directory)
    if rendered['errors']:
        print('Test records were saved, but some charts could not render. See the report rendering issues.',file=sys.stderr)
        return result['exit_code'] or 2
    if args.phase is not None:
        try:attach(root,args.phase,directory)
        except (ValueError,RuntimeError,OSError) as exc:print(str(exc),file=sys.stderr);return 2
    print(directory/'report.html');print(directory/'report.md')
    # Unix signals are preserved in JSON and mapped to a usable shell status here.
    return result['exit_code'] if 0<=result['exit_code']<=255 else 128+abs(result['exit_code'])


if __name__=='__main__':raise SystemExit(main())
