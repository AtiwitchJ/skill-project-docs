"""Build MD/HTML test evidence, charts, and observed failure workflows from JSON."""
import hashlib
import html
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import presentation_charts as charts
from test_results import BAD, OUTCOMES, STAGES, summarize


def escape(value):return html.escape(str(value),quote=True)


def datasets(result):
    cases=result['cases'];data={};specs=[];dimensions=[]
    limits='Observed test records only. Fixture/discovery records are identified separately. Timing is not a performance benchmark.'
    def add(key,title,typ,rows,unit='',**fields):
        data[key]=rows
        specs.append({"id":key,"title":title,"question":title,"type":typ,"source":{"path":"results.json","pointer":"/datasets/"+key},"unit":unit,"limitations":limits,**fields})
    def availability(name,available,reason):dimensions.append({"dimension":name,"available":bool(available),"reason":reason})
    if cases:
        add('outcomes','Test and fixture outcomes','bar',[{"outcome":k,"count":result['summary']['outcomes'][k]} for k in OUTCOMES],unit='records',x='outcome',y='count')
        grouped=defaultdict(Counter)
        for c in cases:grouped[c['suite']][c['outcome']]+=1
        suites=sorted(grouped,key=lambda k:sum(grouped[k].values()),reverse=True)
        selected=suites[:11];rows=[{"suite":s,**{k:grouped[s][k] for k in OUTCOMES}} for s in selected]
        if len(suites)>11:rows.append({"suite":f'Other suites ({len(suites)-11})',**{k:sum(grouped[s][k] for s in suites[11:]) for k in OUTCOMES}})
        # Combine uncommon outcomes explicitly to keep the chart within six series.
        for row in rows:row['other']=row.pop('expected_failure')+row.pop('unexpected_success')+row.pop('interrupted')
        add('suite-outcomes','Outcomes by suite (minor suites explicitly grouped)','stacked-bar',rows,unit='records',x='suite',series=[{"field":k} for k in ('passed','failed','error','skipped','other')])
    availability('Case outcomes',bool(cases),'Case-level records collected.' if cases else 'Command exit status alone provides no test-case inventory.')
    timed=[c for c in cases if c['kind']=='test' and c['outcome']!='skipped' and c.get('duration_s') is not None]
    if timed:
        slow=sorted(timed,key=lambda c:c['duration_s'],reverse=True)[:12]
        add('slowest','Slowest cases — top 12; full inventory below','bar',[{"test":str(i+1)+'. '+c['id'],"seconds":c['duration_s']} for i,c in enumerate(slow)],unit='s',x='test',y='seconds')
        add('duration-distribution','Distribution of observed case durations','histogram',[{"seconds":c['duration_s']} for c in timed],unit='s',value='seconds')
        add('duration-ecdf','Fraction of cases completed within each duration','ecdf',[{"seconds":c['duration_s']} for c in timed],unit='s',value='seconds')
        largest=Counter(c['suite'] for c in timed).most_common(15);names={name for name,_ in largest}
        add('suite-spread','Duration spread across cases within each suite','box',[{"suite":c['suite'] if c['suite'] in names else 'Other suites',"seconds":c['duration_s']} for c in timed],unit='s',x='suite',y='seconds')
    availability('Duration and distribution',bool(timed),f'{len(timed)} non-skipped cases have usable durations. Skipped cases are excluded; unknown durations are not replaced with zero.')
    events=[e for c in cases for e in c.get('events',[])]
    if events:
        totals=defaultdict(float)
        for event in events:totals[event['stage']]+=event['duration_s']
        add('stage-time','Observed time by lifecycle stage','bar',[{"stage":k,"seconds":v} for k,v in totals.items()],unit='s',x='stage',y='seconds')
    availability('Lifecycle timing',bool(events),'Native instrumentation observed lifecycle calls.' if events else 'Producer did not supply lifecycle timings; JUnit phase cannot be inferred.')
    failures=[(c,f) for c in cases if c['outcome'] in BAD for f in c.get('failures',[])]
    if failures:
        counts=Counter(f['stage'] for _,f in failures)
        add('failure-stages','Failure events by observed stage (including unknown)','bar',[{"stage":k,"events":v} for k,v in counts.items()],unit='failure events',x='stage',y='events',color='#b04e54')
        suites=Counter(c['suite'] for c,_ in failures);top={s for s,_ in suites.most_common(10)}
        matrix=Counter((c['suite'] if c['suite'] in top else 'Other suites',f['stage']) for c,f in failures)
        # Zero here is an observed count of events, not a missing measurement.
        rows=[{"suite":s,"stage":stage,"failures":matrix[(s,stage)]} for s in dict.fromkeys(k[0] for k in matrix) for stage in dict.fromkeys(k[1] for k in matrix)]
        add('failure-map','Failure events by suite and stage','heatmap',rows,unit='failure events',x='stage',y='suite',value='failures')
    availability('Failure locations',bool(failures),'Observed failure events; unknown stage remains explicit.' if failures else 'No failure event recorded; this does not establish code coverage.')
    history=result.get('history',[]);runs=history+[result]
    trend=[{"run":i+1,"pass_rate":r['summary']['pass_rate']} for i,r in enumerate(runs) if r['summary'].get('pass_rate') is not None]
    if len(trend)>1:add('pass-trend','Pass rate over comparable runs','line',trend,unit='%',x='run',y='pass_rate')
    duration_trend=[{"run":i+1,"seconds":r['duration_s']} for i,r in enumerate(runs) if r.get('duration_s') is not None]
    if len(duration_trend)>1:add('runtime-trend','Runner wall time over comparable runs','line',duration_trend,unit='s',x='run',y='seconds')
    availability('History trends',len(trend)>1 or len(duration_trend)>1,f'{len(runs)} comparable runs. Historical source paths and checksums are retained.')
    observed=defaultdict(list)
    for run in runs:
        per_run=defaultdict(list)
        for c in run['cases']:
            if c['kind']=='test' and c['outcome'] in {'passed','failed','error'}:per_run[c['id']].append(c['outcome'])
        for name,outcomes in per_run.items():
            if len(outcomes)==1:observed[name].append(outcomes[0])
    candidates=[]
    for name,outcomes in observed.items():
        if len(outcomes)>1 and 'passed' in outcomes and any(o!='passed' for o in outcomes):
            candidates.append({"test":name,"changes":sum(a!=b for a,b in zip(outcomes,outcomes[1:])),"observations":len(outcomes)})
    if candidates:add('outcome-changes','Outcome-change candidates, not proof of nondeterminism','bar',sorted(candidates,key=lambda r:r['changes'],reverse=True)[:12],unit='changes',x='test',y='changes')
    comparable=sum(len(values)>1 for values in observed.values())
    availability('Flaky candidates',comparable>0,f'{comparable} case IDs have repeated eligible observations. Outcome changes can reflect uncontrolled inputs; they do not prove a flaky test.' if comparable else 'No repeated eligible case ID in a matching context; one run cannot establish instability.')
    coverage=result.get('coverage')
    if coverage:
        rows=[{"file":r['file'],"covered":r['covered'],"missing":r['statements']-r['covered']} for r in coverage['files']]
        if not rows:rows=[{"file":"TOTAL","covered":coverage['totals']['covered'],"missing":coverage['totals']['statements']-coverage['totals']['covered']}]
        if rows:
            selected=sorted(rows,key=lambda r:r['missing'],reverse=True)[:12]
            add('coverage','Statement coverage — top 12 files by missing statements','stacked-bar',selected,unit='statements',x='file',series=[{"field":"covered"},{"field":"missing"}])
    availability('Statement coverage',bool(coverage),'Imported statement counts from coverage.py JSON.' if coverage else 'No coverage file supplied. Passing tests do not imply covered statements.')
    branches=coverage['totals'].get('branches') if coverage else None
    if branches is not None:
        total=coverage['totals'];add('branch-coverage','Measured branch coverage','stacked-bar',[{"scope":"TOTAL","covered":total['covered_branches'],"missing":branches-total['covered_branches']}],unit='branches',x='scope',series=[{"field":"covered"},{"field":"missing"}])
    availability('Branch coverage',branches is not None,'Measured branch counts were imported.' if branches is not None else 'Branch coverage was not supplied; statement coverage does not establish it.')
    return data,specs,dimensions


def validate(result):
    if result.get('schema')!='project-docs-tests/v1':raise ValueError('unknown test results schema')
    for case in result['cases']:
        if case['outcome'] not in OUTCOMES or case['kind'] not in {'test','fixture','discovery'}:raise ValueError('invalid test record')
        if case.get('duration_s') is not None and (isinstance(case['duration_s'],bool) or not math.isfinite(case['duration_s']) or case['duration_s']<0):raise ValueError('invalid case duration')
        if any(f.get('stage') not in STAGES for f in case['failures']):raise ValueError('failure stage must be observed or explicitly unknown')
        for event in case.get('events',[]):
            if event.get('stage') not in STAGES or event.get('outcome') not in {'passed','failed','error','skipped'}:raise ValueError('invalid lifecycle event')
            if isinstance(event.get('duration_s'),bool) or not isinstance(event.get('duration_s'),(int,float)) or not math.isfinite(event['duration_s']) or event['duration_s']<0:raise ValueError('invalid lifecycle duration')
    if result['summary']!=summarize(result):raise ValueError('test summary disagrees with case records')
    expected,specs,dimensions=datasets(result)
    if result.get('datasets')!=expected:raise ValueError('chart datasets disagree with observed test results')
    if result.get('chart_specs')!=specs or result.get('dimensions')!=dimensions:raise ValueError('chart definitions or dimensions are stale')


def workflow_states(case):
    if case['events']:
        stages=['setup','test','teardown','cleanup']
        states=[]
        for stage in stages:
            events=[e for e in case['events'] if e['stage']==stage]
            state='failed' if any(e['outcome'] in {'failed','error'} for e in events) else 'skipped' if any(e['outcome']=='skipped' for e in events) else 'passed' if events else 'not observed'
            states.append((stage,state,sum(e['duration_s'] for e in events) if events else None))
    else:
        stage=case['failures'][0]['stage'] if case['failures'] else 'unknown'
        states=[(stage,case['outcome'],None)]
    return states


def stage_label(case,stage):
    if stage=='test' and any(f['stage']=='test' and f['kind']=='assertion' for f in case['failures']):return 'Test body / assertion'
    return {'setup':'Setup','test':'Test body','teardown':'Teardown','cleanup':'Cleanup','fixture_setup':'Class/module setup','fixture_teardown':'Class/module teardown','discovery':'Discovery/import','unknown':'Unknown stage'}.get(stage,stage)


def workflow(case,uid):
    states=workflow_states(case)
    width=960;height=170;parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{uid}" font-family="system-ui,sans-serif"><title id="{uid}">{escape(case["id"])} — observed lifecycle</title><rect width="960" height="170" fill="#f2f6f7"/>']
    gap=930/len(states)
    for i,(stage,state,duration) in enumerate(states):
        px=15+i*gap;color='#b04e54' if state in BAD or state=='failed' else '#17665c' if state=='passed' else '#63757b'
        parts.append(f'<rect x="{px}" y="22" width="{gap-16}" height="112" rx="8" fill="white" stroke="{color}"/>')
        label=stage_label(case,stage)
        for y,value,size in ((48,label,17),(78,state,14),(110,f'{duration:.4g} s' if duration is not None else 'Timing unknown',12)):
            parts.append(f'<text x="{px+12}" y="{y}" fill="{color}" font-size="{size}">{escape(value)}</text>')
        if i<len(states)-1:parts.append(f'<text x="{px+gap-13}" y="84" font-size="16" fill="#63757b">→</text>')
    parts.append('<text x="20" y="156" font-size="12" fill="#536876">Observed stage or explicitly unknown. A failure location is not a root-cause diagnosis.</text></svg>')
    return ''.join(parts)


def workflow_html(case,uid):
    cards=[]
    for stage,state,duration in workflow_states(case):
        css='bad' if state in BAD else 'passed' if state=='passed' else ''
        timing=f'{duration:.4g} s' if duration is not None else 'Timing unknown'
        cards.append(f'<li class="{css}"><strong>{escape(stage_label(case,stage))}</strong><span>{escape(state.capitalize())}</span><small>{timing}</small></li>')
    return '<div class="workflow"><div class="workflow-visual">'+workflow(case,uid)+'</div><ol class="workflow-list" role="list">'+''.join(cards)+'</ol></div>'


def workflow_markdown(case):
    rows=['| Stage | Observed status | Duration |','|---|---|---|']
    for stage,state,duration in workflow_states(case):
        rows.append('| '+stage_label(case,stage)+' | '+state+' | '+(f'{duration:.4g} s' if duration is not None else 'Unknown')+' |')
    return '\n'.join(rows)


def chart_figure(chart,source='results.json'):
    head=''.join('<th>'+escape(f)+'</th>' for f in chart['fields'])
    rows=''.join('<tr>'+''.join('<td>'+escape(v)+'</td>' for v in row)+'</tr>' for row in chart['rows'][:100])
    preview=f'<p>Showing the first 100 of {len(chart["rows"])} rows. Full observations remain in the linked JSON source.</p>' if len(chart['rows'])>100 else ''
    return f'<figure class="evidence-chart"><h3>{escape(chart["title"])}</h3>{charts.html_visual(chart["svg"])}<figcaption><p><strong>Why:</strong> {escape(chart["why"])}</p><p><strong>Limits:</strong> {escape(chart["limits"])}</p><p class="source-note">Source: <a href="{escape(source)}">{escape(source)}</a> · {escape(chart["source"].get("pointer",""))} · SHA-256 {chart["sha256"]}</p></figcaption>{preview}<details><summary>Inspect source values</summary><div class="tbl"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div></details></figure>'


def page(title,body):
    css=(Path(__file__).resolve().parent.parent/'templates/presentation-visuals.css').read_text()
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(title)+'</title><style>'+css+'''
    *{box-sizing:border-box}html{scroll-padding-top:var(--report-offset,90px)}body{margin:0;background:#eaf0f4;color:#172d3f;font:16px/1.6 system-ui,sans-serif}main{max-width:1120px;margin:24px auto;padding:28px;background:white;border-radius:12px}h1{font-size:clamp(28px,4vw,46px);line-height:1.15}h2{margin-top:44px}h3,summary{overflow-wrap:anywhere}a{color:#17665c}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;text-align:left;border-bottom:1px solid #d0dde3;vertical-align:top}.tbl{overflow-x:auto}.badge{padding:4px 10px;border-radius:5px;background:#e5f1ed}.bad{background:#fbebeb;color:#963e44}.note{background:#f2f6f7;padding:16px;border-left:4px solid #63757b}.source-note{overflow-wrap:anywhere}.case-pager{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:14px 0}.case-pager button{font:inherit;padding:8px 12px;border:1px solid #a8b9c0;border-radius:6px;background:white;color:#17665c}.case-pager button:disabled{opacity:.5}.case{padding:16px;border:1px solid #d0dde3;margin:12px 0;border-radius:8px}input{font:inherit;padding:10px;width:100%;border:1px solid #a8b9c0;border-radius:6px}.workflow{overflow-x:auto}.workflow svg{display:block;width:100%;min-width:650px}button,summary{cursor:pointer}.report-nav{position:sticky;top:0;padding:12px 0;background:white;z-index:5;border-bottom:1px solid #d0dde3;display:flex;gap:14px;flex-wrap:wrap;font-size:13px}a:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #345f9a;outline-offset:3px}@media(max-width:600px){main{margin:0;padding:18px;border-radius:0}.dimension-table thead{display:none}.dimension-table tr{display:grid;gap:5px;padding:14px 0;border-bottom:1px solid #d0dde3}.dimension-table td{border:0;padding:3px 0}.dimension-table td:first-child{font-weight:600}.dimension-table td:nth-child(2){color:#17665c}}@media print{input,.report-nav,.case-pager{display:none}.case[hidden]{display:block!important}details{display:block}.case,figure{break-inside:avoid}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
    </style></head><body><main>'''+body+'''</main><script>let printDetails=[];addEventListener('beforeprint',()=>{printDetails=[...document.querySelectorAll('details')].map(el=>[el,el.open]);printDetails.forEach(([el])=>el.open=true)});addEventListener('afterprint',()=>{printDetails.forEach(([el,open])=>el.open=open);printDetails=[]});document.querySelectorAll('[data-filter]').forEach(input=>{const rows=[...document.querySelectorAll(input.dataset.filter)];const texts=rows.map(row=>row.textContent.toLowerCase());if(!rows.length){input.disabled=true;input.placeholder='No case-level records available';return}let page=0;const pager=document.createElement('div');pager.className='case-pager';const prev=document.createElement('button'),next=document.createElement('button'),status=document.createElement('span');prev.type=next.type='button';prev.textContent='Previous cases';next.textContent='Next cases';status.setAttribute('aria-live','polite');pager.append(prev,status,next);input.closest('label').after(pager);function render(){const q=input.value.toLowerCase();const matches=rows.filter((row,i)=>texts[i].includes(q));const pages=Math.max(1,Math.ceil(matches.length/50));page=Math.min(page,pages-1);const visible=new Set(matches.slice(page*50,(page+1)*50));rows.forEach(row=>{const hidden=!visible.has(row);if(row.hidden!==hidden)row.hidden=hidden});status.textContent=`${matches.length ? page*50+1 : 0}–${Math.min((page+1)*50,matches.length)} of ${matches.length} matches (${rows.length} records total)`;prev.disabled=page===0;next.disabled=page===pages-1}prev.onclick=()=>{page--;render()};next.onclick=()=>{page++;render()};input.addEventListener('input',()=>{page=0;render()});render()});const headings=[...document.querySelectorAll('h2')];if(headings.length>1){const nav=document.createElement('nav');nav.className='report-nav';nav.setAttribute('aria-label','Report sections');headings.forEach((heading,i)=>{heading.id='report-section-'+i;const a=document.createElement('a');a.href='#'+heading.id;a.textContent=heading.textContent;nav.append(a)});document.querySelector('h1').after(nav);const measure=()=>document.documentElement.style.setProperty('--report-offset',`${nav.offsetHeight+16}px`);measure();if('ResizeObserver' in window)new ResizeObserver(measure).observe(nav)}</script></body></html>'''


def write_report(directory):
    directory=Path(directory);source=directory/'results.json';result=json.loads(source.read_text());validate(result)
    rendered=[];render_errors=[]
    for spec in result['chart_specs']:
        try:rendered.append(charts.render(directory,spec))
        except (ValueError,KeyError,OSError) as exc:render_errors.append({'chart':spec['id'],'error':str(exc)})
    checksum=hashlib.sha256(source.read_bytes()).hexdigest();assets={};md=['# Test run report',result['started'],result.get('disclaimer','')]
    counts=result['summary'];status='PASSED' if result['exit_code']==0 and counts['outcomes']['passed'] else 'COMPLETED — NO VERIFIED PASS' if result['exit_code']==0 else 'FAILED / INCOMPLETE'
    md.extend([f'**Run outcome:** {status} · Exit code {result["exit_code"]}',f'**Inventory:** {counts["test_cases"]} test cases; {counts["fixture_records"]} fixture records; {counts["discovery_records"]} discovery records; {counts["subtests"]} subtest observations.',counts['pass_rate_definition'],f'**Source:** [results.json](results.json) · SHA-256 `{checksum}`'])
    body=f'<h1>Test run report</h1><p>{escape(result["started"])}</p><p>{escape(result.get("disclaimer",""))}</p><p><strong class="badge {"bad" if result["exit_code"] else ""}">{status}</strong> · Exit code {result["exit_code"]}</p><p>{counts["test_cases"]} test cases · {counts["fixture_records"]} fixtures · {counts["discovery_records"]} discovery records · {counts["subtests"]} subtests</p><p class="source-note">Source: <a href="results.json">results.json</a> · SHA-256 {checksum}</p>'
    if result.get('runner_error'):
        md.extend(['## Runner failure','```text',result['runner_error'],'```']);body+='<h2>Runner failure</h2><pre>'+escape(result['runner_error'])+'</pre>'
    md.append('## Available dimensions');dimension_rows=['| Dimension | Available | Meaning |','|---|---|---|']
    body+='<h2>Available dimensions</h2><div class="tbl"><table class="dimension-table"><thead><tr><th>Dimension</th><th>Available</th><th>Meaning</th></tr></thead><tbody>'
    for dim in result['dimensions']:
        available='Available' if dim['available'] else 'Not available'
        dimension_rows.append('| '+dim['dimension']+' | '+available+' | '+dim['reason'].replace('|','\\|')+' |')
        body+='<tr><td>'+escape(dim['dimension'])+'</td><td>'+available+'</td><td>'+escape(dim['reason'])+'</td></tr>'
    md.append('\n'.join(dimension_rows));body+='</tbody></table></div><h2>Charts</h2>'
    for error in render_errors:
        note='Chart unavailable: '+error['chart']+' — '+error['error']
        md.extend(['## Report rendering issue',note]);body+='<p class="note bad">'+escape(note)+'. Test records remain available below.</p>'
    for chart in rendered:
        asset='charts/'+chart['id']+'.svg';assets[asset]=chart['svg']
        md.extend(['## '+chart['title'],f'![{chart["title"]}]({asset})','**Why:** '+chart['why'],'**Limits:** '+chart['limits'],f'Source: [results.json](results.json) · `{chart["source"]["pointer"]}`'])
        if len(chart['rows'])>100:md.append(f'Source table preview: first 100 of {len(chart["rows"])} rows; full values remain in results.json.')
        table=['| '+' | '.join(chart['fields'])+' |','| '+' | '.join('---' for _ in chart['fields'])+' |']
        table.extend('| '+' | '.join(str(v).replace('|','\\|').replace('\n',' ') for v in row)+' |' for row in chart['rows'][:100]);md.append('\n'.join(table))
        body+=chart_figure(chart)
    failed=[c for c in result['cases'] if c['outcome'] in BAD]
    body+='<h2>Failure workflows</h2><p>First 20 failed-record workflows; the inventory below retains every record and traceback.</p>'
    md.extend(['## Failure workflows','First 20 failed-record workflows; all records and tracebacks remain below.'])
    for i,c in enumerate(failed[:20]):
        uid='failure-'+str(i)+'-'+hashlib.sha256(c['id'].encode()).hexdigest()[:8];svg=workflow(c,uid);asset='workflows/'+uid+'.svg';assets[asset]=svg
        md.extend(['### '+c['id'],f'![Observed failure lifecycle]({asset})',workflow_markdown(c)]);body+='<h3>'+escape(c['id'])+'</h3>'+workflow_html(c,uid)
    if not failed:md.append('No failed record was observed.');body+='<p>No failed record was observed.</p>'
    md.append('## Full inventory and tracebacks');body+='<h2>Full inventory and tracebacks</h2><label>Filter test names, outcomes or errors<input data-filter=".case" placeholder="Filter results"></label>'
    for c in result['cases']:
        md.extend(['### '+c['id'],f'Outcome: {c["outcome"]} · Kind: {c["kind"]} · Duration: {c["duration_s"] if c.get("duration_s") is not None else "unknown"} s'])
        body+='<details class="case"><summary>'+escape(c['outcome'].upper()+' · '+c['id'])+'</summary><p>Kind: '+escape(c['kind'])+' · Duration: '+escape(c.get('duration_s') if c.get('duration_s') is not None else 'unknown')+' s</p>'
        if c.get('skip_reason'):md.append('Skip: '+c['skip_reason']);body+='<p>Skip: '+escape(c['skip_reason'])+'</p>'
        for failure_ in c['failures']:
            md.extend(['Stage: '+failure_['stage']+' · '+failure_['message'],'<details><summary>Traceback</summary>','<pre>'+escape(failure_['traceback'])+'</pre>','</details>'])
            body+='<p><strong>Stage: '+escape(failure_['stage'])+'</strong> · '+escape(failure_['message'])+'</p><pre>'+escape(failure_['traceback'])+'</pre>'
        body+='</details>'
    md.extend(['## Limits',*result['limitations']]);body+='<h2>Limits</h2><ul>'+''.join('<li>'+escape(v)+'</li>' for v in result['limitations'])+'</ul>'
    for log in result.get('logs',[]):md.append(f'[Raw log]({log})');body+='<p><a href="'+escape(log)+'">Raw log: '+escape(log)+'</a></p>'
    for name,value in assets.items():p=directory/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value,encoding='utf-8')
    (directory/'report.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8');(directory/'report.html').write_text(page('Test run report',body),encoding='utf-8')
    return {'assets':assets,'errors':render_errors}
