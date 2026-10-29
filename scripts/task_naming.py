#!/usr/bin/env python3
"""Read-only Task category/topic/title/source checks; no provider access.

python3 task_naming.py --root . --require --phase 2 --json
A reviewed .project-docs/task-topics.json owns the plan-topic inventory.
Without a contract the result is 'not-configured', never a hierarchy pass.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

HEAD = re.compile(r'^###\s+\[(.)\]\s+(.*\S)\s*$')
TITLE = re.compile(r'^(\d+(?:\.\d+)*)(\s*)\[([^\[\]]+)\](\s+)(\S.*)$')
FIELD = re.compile(r'^\*\*([^*]+):\*\*\s*(.*?)\s*$')


def inventory(path):
    rows = []; current = None; category = ''; fence = None
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            char = marker[1][0]
            if fence is None: fence = (char, len(marker[1]))
            elif char == fence[0] and len(marker[1]) >= fence[1]: fence = None
            continue
        if fence: continue
        if line.startswith('## '): category = line[3:].strip(); current = None
        match = HEAD.match(line)
        if match:
            current = {'line':number,'mark':match[1],'raw_title':match[2],'category_heading':category,'fields':{}}
            rows.append(current)
        elif current:
            field = FIELD.match(line)
            if field: current['fields'].setdefault(field[1], []).append(field[2])
    return rows


def inspect(root, phases=None, required=False):
    root = Path(root).resolve(); findings = []; rows = []
    registry = root/'.project-docs/task-topics.json'
    def add(code, where, message): findings.append({'code':code,'where':str(where),'message':message})
    def result(enabled):
        return {'status':('failed' if findings else 'passed') if enabled else 'not-configured',
                'findings':findings,'tasks':rows,'limits':'Checks structure against the supplied topic registry; does not prove plan interpretation, task acceptance, Wh clarity or remote tracker updates.'}
    cfg_path = root/'.project-docs/config.json'
    try:
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        contract = cfg.get('task_naming', {})
        if not isinstance(contract, dict): raise ValueError('task_naming must be an object')
        if 'required' in contract and not isinstance(contract['required'],bool):raise ValueError('task_naming.required must be boolean')
        enabled = required or registry.exists() or contract.get('required') is True
    except (OSError, ValueError, TypeError, AttributeError) as e:
        add('invalid-config',cfg_path.relative_to(root),str(e));return result(True)
    if not enabled:return result(False)
    if not registry.is_file():
        add('missing-topic-registry','.project-docs/task-topics.json','Create a reviewed plan-topic inventory from real source material before claiming hierarchy compliance.')
        return result(True)
    try:
        data = json.loads(registry.read_text())
        if not isinstance(data,dict) or (type(data.get('version')) is not int or data.get('version')!=1) or not isinstance(data.get('phases'),dict):raise ValueError('expected version 1 and phases object')
        registered = data['phases']
        if any(not str(k).isdigit() or int(k)<1 or str(int(k))!=k for k in registered):raise ValueError('phase keys must be canonical positive integers')
    except (ValueError,OSError) as e:
        add('invalid-topic-registry','.project-docs/task-topics.json',str(e));return result(True)
    found = {int(p.parent.name[6:]) for p in (root/'project/phases').glob('phase-*/tasks.md') if p.parent.name[6:].isdigit()}
    if phases is not None and any(isinstance(n,bool) or not isinstance(n,int) or n<1 for n in phases):
        add('invalid-phase','phase','phase must be a positive integer');return result(True)
    selected = sorted(set(phases) if phases is not None else found | {int(k) for k in registered})
    all_uids = {}
    for phase in selected:
        path = root/f'project/phases/phase-{phase}/tasks.md'; where = path.relative_to(root).as_posix()
        if not path.is_file():add('missing-task-file',where,'Selected/registered phase has no tasks.md.');continue
        tasks = inventory(path); phase_data = registered.get(str(phase))
        if not isinstance(phase_data,dict) or not isinstance(phase_data.get('topics'),list):
            add('missing-phase-topics',where,'Register this phase and its actual plan topics.');continue
        topics = {}; observed = Counter(); ids = Counter()
        for index,topic in enumerate(phase_data['topics']):
            spot = f'.project-docs/task-topics.json:phase-{phase}/topics/{index}'
            if not isinstance(topic,dict) or any(not isinstance(topic.get(f),str) or not topic[f].strip() for f in ('label','category','source','source_label')):
                add('invalid-topic',spot,'Each topic needs nonempty label, category, source and exact source_label.');continue
            label = topic['label']
            if label in topics:add('duplicate-topic',spot,'Topic labels must be unique within a phase.');continue
            topics[label]=topic
            if label!=topic['source_label'] and not topic.get('alias_reason'):
                add('unexplained-alias',spot,'A shortened topic label needs an explicit alias_reason.')
            source = (root/topic['source']).resolve()
            if not source.is_relative_to(root) or not source.is_file():
                add('missing-plan-source',spot,'source must resolve to an existing file inside this project.')
            disposition = topic.get('disposition','in-scope')
            if disposition not in ('in-scope','out-of-scope','cancelled','deferred','pending'):
                add('invalid-disposition',spot,'Use in-scope/out-of-scope/cancelled/deferred/pending.')
            if disposition!='in-scope' and (not topic.get('reason') or not topic.get('decision')):
                add('missing-scope-decision',spot,'Non-active topics need a concrete reason and recorded decision/reference (pending decisions must be explicit).')
        for task in tasks:
            spot = f'{where}:{task["line"]}'; fields = task['fields']
            def field(name):return fields.get(name,[''])[0]
            row = {'phase':phase,'where':spot,'title':task['raw_title'],'mark':task['mark'],'category':field('Work category'),'uid':field('Task UID')}
            rows.append(row)
            for key,values in fields.items():
                if key in ('Task UID','Work category','Plan topic','Plan source','Scope disposition') and len(values)>1:add('duplicate-metadata',spot,'Repeated '+key+' metadata is ambiguous.')
            if task['mark'] not in (' ','x','/','!'):add('invalid-task-mark',spot,'Unsupported Task status marker.')
            uid = field('Task UID')
            if not uid or re.search(r'\s',uid):add('missing-task-uid',spot,'Preserve or explicitly establish one stable Task UID.')
            elif uid in all_uids:add('duplicate-task-uid',spot,'UID already used at '+all_uids[uid])
            else:all_uids[uid]=spot
            match = TITLE.match(task['raw_title'])
            if not match:
                add('missing-topic-title',spot,'Expected existing Task number [Plan topic] Action; do not renumber to repair it.')
                continue
            number,space,label,_,action = match.groups(); ids[number]+=1
            row.update({'number':number,'topic':label,'action':action})
            if not space:add('compact-title',spot,'Normalize spacing after the existing number without changing its identity.')
            topic = topics.get(label)
            if topic is None:add('unregistered-topic',spot,'Title topic is absent from the reviewed plan inventory.');continue
            observed[label]+=1
            if task['category_heading']!=topic['category'] or field('Work category')!=topic['category']:
                add('category-mismatch',spot,'Category heading and Work category must both match '+topic['category'])
            if field('Plan topic')!=topic['source_label']:add('source-topic-mismatch',spot,'Plan topic must retain the exact source_label.')
            if not field('Plan source') or topic['source'] not in field('Plan source'):
                add('missing-task-source',spot,'Plan source must cite the registered source path and its box/section.')
            disposition = field('Scope disposition').split(';',1)[0].strip()
            if disposition!=topic.get('disposition','in-scope'):add('scope-mismatch',spot,'Task scope disposition differs from the registered decision.')
            if disposition in ('out-of-scope','cancelled','deferred','pending') and task['mark']=='x':
                add('excluded-as-done',spot,'An exclusion/pending decision must not be counted as verified delivery.')
        for number,count in ids.items():
            if count>1:add('duplicate-task-number',where,'Duplicate existing Task number '+number+'; resolve identity, do not silently reassign it.')
        for label,topic in topics.items():
            if not observed[label]:add('unmapped-plan-topic',where,'Plan topic has no Task preserving its identity/decision: '+label)
    return result(True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--phase',type=int,action='append')
    parser.add_argument('--require',action='store_true',help='Missing hierarchy inventory is an error, never a silent skip.')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args();report=inspect(args.root,args.phase,args.require)
    if args.json:print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print('Task hierarchy: '+report['status'])
        for f in report['findings']:print(f'{f["code"]}: {f["where"]}: {f["message"]}')
        print(report['limits'])
    return 1 if report['findings'] else 0


if __name__=='__main__':raise SystemExit(main())
