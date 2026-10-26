"""Phase flow and chart outputs. Tasks own status; specs own grouping and encoding."""
from __future__ import annotations

import html
import json
import os
import re
import textwrap
from pathlib import Path

from presentation_charts import render as render_chart, svg_text, inside, html_visual

FLOW = ("<!-- AUTO:phase-flow -->", "<!-- /AUTO:phase-flow -->")
CHARTS = ("<!-- AUTO:charts -->", "<!-- /AUTO:charts -->")
STATES = {"x": ("done", "Done", "#17665c"), "/": ("doing", "In progress", "#345f9a"),
          "!": ("blocked", "Blocked", "#9b5416"), " ": ("todo", "Not started", "#63757b")}
THAI = {"Done": "เสร็จแล้ว", "In progress": "กำลังทำ", "Blocked": "ติดบล็อก", "Not started": "ยังไม่เริ่ม",
        "Phase route": "เส้นทางของ Phase", "Verified tasks": "Task ที่ตรวจแล้ว", "No tasks defined": "ยังไม่มี Task",
        "No measured results yet.": "ยังไม่มีผลที่วัดและตรวจแล้ว", "Step": "ขั้นตอน", "Status": "สถานะ"}


def word(text, language):
    return THAI.get(text, text) if language == "Thai" else text


def block(text, markers, value, append=False):
    begin, end = markers
    if text.count(begin) != text.count(end) or text.count(begin) > 1:
        raise ValueError("missing or duplicate AUTO marker: " + begin)
    content = begin+"\n"+value.strip()+"\n"+end
    if begin not in text:
        if append: return text.rstrip()+"\n\n"+content+"\n"
        raise ValueError("AUTO marker missing: " + begin)
    return re.sub(re.escape(begin)+r".*?"+re.escape(end), lambda _: content, text, flags=re.S)


def model(root, phase, items):
    root = Path(root)
    config = json.loads((root / ".project-docs/config.json").read_text(encoding="utf-8")) if (root / ".project-docs/config.json").exists() else {}
    path = root / ".project-docs/presentations" / f"phase-{phase}.json"
    spec = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if spec.get("version", 1) != 1:
        raise ValueError("unknown presentation spec version")
    steps = spec.get("flow", {}).get("steps")
    if steps is None:
        steps = [{"id": f"step-{n}", "label": t["title"], "tasks": [t.get("uid") or t["id"] or f"row-{n}"]} for n,t in enumerate(items,1)]
    lookup = {}
    for i, task in enumerate(items,1):
        for key in {task.get("uid"), task.get("id"), f"row-{i}"} - {None, ""}:
            if key in lookup and lookup[key] != i-1:
                raise ValueError("ambiguous task reference in phase: " + key)
            lookup[key] = i-1
    used, names, output = set(), set(), []
    for step in steps:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", step["id"]) or step["id"] in names:
            raise ValueError("step IDs must be unique slugs")
        names.add(step["id"])
        refs = step.get("tasks", [])
        if not refs: raise ValueError("a flow step must reference at least one task")
        group = []
        for ref in refs:
            if ref not in lookup: raise ValueError("flow references unknown task: " + str(ref))
            idx = lookup[ref]
            if idx in used: raise ValueError("each task must appear exactly once in the phase flow")
            used.add(idx); group.append(items[idx])
        marks = [t["mark"] for t in group]
        if any(m not in STATES for m in marks): raise ValueError("unknown task marker in phase flow")
        mark = "x" if all(m == "x" for m in marks) else "!" if "!" in marks else "/" if "/" in marks or "x" in marks else " "
        output.append({"id": step["id"], "label": step["label"], "mark": mark,
                       "done": marks.count("x"), "total": len(group), "refs": refs})
    if len(used) != len(items): raise ValueError("flow must cover every task in this phase")
    charts = [render_chart(root, entry) for entry in spec.get("charts", [])]
    test_run=None
    if spec.get('test_run'):
        import test_reporting
        path=inside(root,spec['test_run']);report=json.loads(path.read_text());test_reporting.validate(report)
        test_run={"path":path,"report":report}
        prefix='tests-'+__import__('hashlib').sha256(str(path.relative_to(root)).encode()).hexdigest()[:8]+'-'
        for entry in report['chart_specs']:
            value={**entry,"id":prefix+entry['id'],"source":{**entry['source'],"path":str(path.relative_to(root))}}
            charts.append(render_chart(root,value))
    if len({c["id"] for c in charts}) != len(charts): raise ValueError("duplicate chart id")
    return {"phase": phase, "steps": output, "done": sum(t["mark"] == "x" for t in items), "total": len(items),
            "language": config.get("language", "English"), "charts": charts,"test_run":test_run}


def flow_svg(data):
    language = data["language"]
    steps = data["steps"]
    rows = max(1, (len(steps)+2)//3)
    height = 100+rows*190
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 {height}" role="img" aria-labelledby="phase-flow-title" style="font-family:system-ui,sans-serif">',
             f'<title id="phase-flow-title">{word("Phase route",language)}: {data["done"]}/{data["total"]}</title>',
             '<desc>Ordered steps, derived task status. Multiple steps may be active at the same time.</desc>',
             f'<rect width="1100" height="{height}" rx="12" fill="#f5f8f8"/>',
             '<defs><marker id="flow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="none" stroke="#a4b5b6"/></marker></defs>',
             svg_text(24, 40, f'{word("Verified tasks",language)}: {data["done"]}/{data["total"]}', 20)]
    if not steps: parts.append(svg_text(24, 120, word("No tasks defined",language), 18))
    for i, step in enumerate(steps):
        col, row = i%3, i//3; x, y = 24+col*366, 75+row*190
        _, label, color = STATES[step["mark"]]
        parts.append(f'<rect x="{x}" y="{y}" width="320" height="132" rx="10" fill="#ffffff" stroke="#d7e1e1"/>')
        parts.append(f'<rect x="{x}" y="{y+12}" width="4" height="108" fill="{color}"/>')
        parts.append(svg_text(x+18,y+28,f'{i+1:02d} · {word(label,language)}',14,fill=color))
        title = str(step["label"])
        lines = textwrap.wrap(title, 29) or [""]
        if len(lines)>2: lines=lines[:1]+[lines[1][:26]+"…"]
        for j, line in enumerate(lines): parts.append(svg_text(x+18,y+58+j*22,line,18))
        parts.append(svg_text(x+18,y+113,f'{step["done"]}/{step["total"]} {word("Verified tasks",language)}',13))
        if i < len(steps)-1:
            if col < 2: path = f'M{x+326} {y+66}H{x+358}'
            else: path = f'M{x+326} {y+66}H1090V{y+160}H12V{y+256}H20'
            parts.append(f'<path d="{path}" fill="none" stroke="#a4b5b6" stroke-width="2" marker-end="url(#flow-arrow)"/>')
    return "".join(parts)+"</svg>"


def markdown_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("<", "&lt;")


def outputs(root, phase, items):
    root = Path(root)
    directory = root / "project/phases" / f"phase-{phase}"
    data = model(root, phase, items)
    language = data["language"]
    svg = flow_svg(data)
    assets = {directory / "phase-flow.svg": svg}
    md_flow = f'## {word("Phase route",language)}\n\n![{word("Phase route",language)}](phase-flow.svg)\n\n'
    md_flow += f'{word("Verified tasks",language)}: **{data["done"]}/{data["total"]}**. Counts describe verified tasks, not effort or elapsed time.\n\n'
    md_flow += '| '+word("Step",language)+' | '+word("Status",language)+' | '+word("Verified tasks",language)+' | Tasks |\n|---|---|---|---|\n'
    list_items = []
    for n, step in enumerate(data["steps"],1):
        state, label, _ = STATES[step["mark"]]; label = word(label,language)
        md_flow += f'| {n}. {markdown_cell(step["label"])} | {label} | {step["done"]}/{step["total"]} | {markdown_cell(", ".join(step["refs"]))} |\n'
        list_items.append(f'<li class="flow-step {state}"><span class="flow-state">{html.escape(label)}</span><strong>{n:02d} · {html.escape(step["label"])}</strong><span>{step["done"]}/{step["total"]} {word("Verified tasks",language)}</span></li>')
    active = [s["label"] for s in data["steps"] if s["mark"] in {"/", "!"}]
    summary = " · ".join(active) if active else ("All steps verified" if data["total"] and data["done"] == data["total"] else "No active step recorded")
    progress = f'<progress value="{data["done"]}" max="{data["total"]}" aria-label="Verified tasks"></progress>' if data["total"] else ""
    html_flow = f'<div class="phase-progress" data-tasks="{data["total"]}" data-done="{data["done"]}"><div class="flow-summary"><strong>{word("Verified tasks",language)}: {data["done"]}/{data["total"]}</strong><span>{html.escape(summary)}</span></div>{progress}<div class="flow-visual">{svg}</div><ol class="flow-list">{"".join(list_items)}</ol><p class="visual-note">Steps show planned order; activity may overlap. Task counts are not effort estimates.</p></div>'
    md_charts, html_charts = [], []
    test_md,test_html='',''
    if data['test_run']:
        import test_reporting
        run=data['test_run']['report'];path=data['test_run']['path'];link=os.path.relpath(path.with_name('report.html'),directory).replace(os.sep,'/')
        source=os.path.relpath(path,directory).replace(os.sep,'/');summary=run['summary'];status=run['status']
        note=f'Latest test run: {status}; exit code {run["exit_code"]}; {summary["test_cases"]} cases. Task status is unchanged.'
        test_md=f'## Latest test run\n\n{note}\n\n[Full report]({link}) · [Raw results]({source})\n\n'
        test_html=f'<aside class="test-run-summary"><h3>Latest test run</h3><p>{html.escape(note)}</p><p><a href="{html.escape(link,quote=True)}">Full report and all failure traces</a> · <a href="{html.escape(source,quote=True)}">Raw results</a></p>'
        failed=[c for c in run['cases'] if c['outcome'] in test_reporting.BAD]
        if failed:
            svg=test_reporting.workflow(failed[0],'phase-test-'+__import__('hashlib').sha256(str(path).encode()).hexdigest()[:8])
            asset=directory/'test-failure-flow.svg';assets[asset]=svg
            test_md+='First failed record (all failures are in the full report):\n\n![Observed test failure](test-failure-flow.svg)\n\n'+test_reporting.workflow_markdown(failed[0])+'\n\n'
            test_html+='<p>First failed record; the full report contains every failure.</p>'+test_reporting.workflow_html(failed[0],'phase-test-view')
        test_html+='</aside>'
    for chart in data["charts"]:
        relative = "charts/"+chart["id"]+".svg"
        assets[directory / relative] = chart["svg"]
        source = os.path.relpath(root / chart["source"]["path"], directory).replace(os.sep,"/")
        columns = " | ".join(markdown_cell(f) for f in chart["fields"])
        table = '| '+columns+' |\n| '+' | '.join('---' for _ in chart["fields"])+' |\n'
        table += "\n".join('| '+" | ".join(markdown_cell(v) for v in row)+' |' for row in chart["rows"][:100])
        preview = f"Showing the first 100 of {len(chart['rows'])} rows; full values remain in the JSON source." if len(chart["rows"])>100 else ""
        annotation = "\n".join('- '+note for note in chart["annotations"])
        md_charts.append(f'### Chart: {chart["title"]}\n\n{chart["question"]}\n\n![{chart["title"]}]({relative})\n\n**Why this chart:** {chart["why"]}\n\n{chart["takeaway"]}\n\n{annotation}\n\n**Source:** [{chart["source"]["path"]}]({source}) · JSON pointer `{chart["source"].get("pointer", "")}` · SHA-256 `{chart["sha256"]}`\n\n**Limits:** {chart["limits"]}\n\n{preview}\n\n<details>\n<summary>Source values</summary>\n\n{table}\n\n</details>')
        th = "".join('<th>'+html.escape(str(f))+'</th>' for f in chart["fields"])
        tr = "".join('<tr>'+"".join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in chart["rows"][:100])
        notes = "".join('<li>'+html.escape(note)+'</li>' for note in chart["annotations"])
        html_charts.append(f'<figure class="evidence-chart" data-chart="{chart["type"]}" data-source-sha256="{chart["sha256"]}"><header><h3>{html.escape(chart["title"])}</h3><p>{html.escape(chart["question"])}</p></header>{html_visual(chart["svg"])}<figcaption><p class="chart-takeaway">{html.escape(chart["takeaway"])}</p><p><strong>Why this chart:</strong> {html.escape(chart["why"])}</p><ul>{notes}</ul><p><strong>Limits:</strong> {html.escape(chart["limits"])}</p><p class="source-note"><strong>Source:</strong> <a href="{html.escape(source,quote=True)}">{html.escape(chart["source"]["path"])}</a> · {html.escape(chart["source"].get("pointer",""))} · SHA-256 <code>{chart["sha256"]}</code></p></figcaption><p>{preview}</p><details><summary>Inspect source values</summary><div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div></details></figure>')
    if not data["charts"]:
        empty = word("No measured results yet.",language)
        md_charts = ['## Evidence charts\n\n'+empty]
        html_charts = ['<p class="empty-results">'+empty+'</p>']
    else:
        md_charts.insert(0, "## Evidence charts")
    return {"model": data, "assets": assets, "md_flow": md_flow, "html_flow": html_flow,
            "md_charts": test_md+"\n\n".join(md_charts), "html_charts": test_html+"\n".join(html_charts)}


def markdown(text, generated):
    # Put summaries before the first task heading, so generated text never becomes
    # a subtask or evidence item belonging to the final task in the file.
    for markers, content in ((FLOW, generated["md_flow"]), (CHARTS, generated["md_charts"])):
        if markers[0] not in text:
            idx = re.search(r"^###\s+\[", text, flags=re.M)
            position = idx.start() if idx else len(text)
            text = text[:position]+markers[0]+"\n"+markers[1]+"\n\n"+text[position:]
        text = block(text, markers, content)
    return text


def html_blocks(text, generated):
    for markers, content, index in ((FLOW, generated["html_flow"],1), (CHARTS, generated["html_charts"],3)):
        if markers[0] not in text:
            sections = list(re.finditer(r'<section\b[^>]*\bclass="[^"]*\bslide\b[^"]*"[^>]*>.*?</section>',text,flags=re.S))
            if not sections: raise ValueError("presentation has no slide for generated visual blocks")
            section = sections[min(index,len(sections)-1)]
            pos = section.end()-len('</section>')
            text = text[:pos]+markers[0]+"\n"+markers[1]+"\n"+text[pos:]
        text = block(text,markers,content)
    css_file = Path(__file__).resolve().parent.parent / "templates/presentation-visuals.css"
    css = css_file.read_text(encoding="utf-8")
    markers = ("<!-- AUTO:visual-styles -->", "<!-- /AUTO:visual-styles -->")
    if markers[0] not in text:
        text = text.replace("</head>",markers[0]+markers[1]+"\n</head>",1)
    return block(text,markers,'<style>\n'+css+'\n</style>')


def stale(root, phase, items, presentation):
    generated = outputs(root,phase,items)
    directory = Path(root) / "project/phases" / f"phase-{phase}"
    current = (directory / "tasks.md").read_text(encoding="utf-8")
    issues = []
    if markdown(current,generated) != current: issues.append("tasks.md flow/charts are stale")
    if html_blocks(presentation,generated) != presentation: issues.append("presentation flow/charts/styles are stale")
    for path, value in generated["assets"].items():
        if not path.exists() or path.read_text(encoding="utf-8") != value: issues.append(str(path.relative_to(root))+" is stale")
    return issues


def write(root, phase, items):
    generated = outputs(root,phase,items)
    directory = Path(root) / "project/phases" / f"phase-{phase}"
    path = directory / "tasks.md"
    current = path.read_text(encoding="utf-8")
    value = markdown(current,generated)
    if value != current: path.write_text(value,encoding="utf-8")
    for path,value in generated["assets"].items():
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists() or path.read_text(encoding="utf-8") != value: path.write_text(value,encoding="utf-8")
    return generated
