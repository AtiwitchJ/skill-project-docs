#!/usr/bin/env python3
"""Create an explicitly synthetic presentation demo in an empty output directory."""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    if root.exists() and any(root.iterdir()): parser.error("output must be empty; existing project files are never overwritten")
    root.mkdir(parents=True,exist_ok=True)
    skill = Path(__file__).resolve().parent.parent
    def run(script,*arguments):
        subprocess.run([sys.executable,str(skill/"scripts"/script),*map(str,arguments)],cwd=root,check=True,stdout=subprocess.DEVNULL)
    run("init_project.py","--path",root,"--name","Phase presentation example","--language","English")
    phase = root/"project/phases/phase-1"; phase.mkdir(parents=True)
    (phase/"tasks.md").write_text('''# PHASE 1: Follow the route, inspect the evidence

> **Period:** Illustrative fixture — no real delivery dates
> All tasks, blockers and measurements in this example are synthetic. They demonstrate the presentation system, not delivery results.

### [x] 1.1 Define the owner files

**Task UID:** demo-owners
**Evidence:** Demonstration fixture; this is not an assertion about a live project.
- [x] Example owner map drafted.

### [x] 1.2 Choose the connection

**Task UID:** demo-connection
**Evidence:** Demonstration fixture only.
- [x] Example connection selected.

### [/] 1.3 Copy and reconcile

**Task UID:** demo-copy
- [x] Example inventory collected.
- [ ] Reconcile the remaining records.

### [!] 1.4 Verify representative cases (IMP-001)

**Task UID:** demo-verify
- [ ] Wait for the example validation owner (IMP-001).

### [ ] 1.5 Hand over the phase

**Task UID:** demo-handover
- [ ] Record the next decision and its evidence.
''',encoding="utf-8")
    measurements = {"disclaimer":"Synthetic fixture. Not benchmark or production evidence.",
                    "comparison":[{"method":"Baseline","latency_ms":140},{"method":"Candidate A","latency_ms":95},{"method":"Candidate B","latency_ms":110}],
                    "trend":[{"run":1,"latency_ms":140},{"run":2,"latency_ms":125},{"run":3,"latency_ms":110},{"run":4,"latency_ms":95}],
                    "paired":[{"scenario":"Small batch","before_ms":90,"after_ms":70},{"scenario":"Medium batch","before_ms":140,"after_ms":95},{"scenario":"Large batch","before_ms":210,"after_ms":160}]}
    results = root/"project/results/measurements.json"; results.write_text(json.dumps(measurements,indent=2)+"\n")
    shutil.copyfile(skill/"templates/paired-chart-example.py", root/"build_paired_chart.py")
    subprocess.run([sys.executable,str(root/"build_paired_chart.py"),str(results),str(root/"project/results/charts/paired.svg")],check=True)
    common = {"unit":"ms","limitations":"Synthetic values, one illustrative observation per row; no statistical or production conclusion."}
    spec = {"version":1,"flow":{"steps":[
        {"id":"prepare","label":"Prepare the source","tasks":["demo-owners","demo-connection"]},
        {"id":"copy","label":"Copy and reconcile","tasks":["demo-copy"]},
        {"id":"verify","label":"Verify and hand over","tasks":["demo-verify","demo-handover"]}]},"charts":[
        {**common,"id":"compare-methods","title":"Compare categories on a common baseline","question":"How do the example methods compare?","intent":"comparison","source":{"path":"project/results/measurements.json","pointer":"/comparison"},"x":"method","y":"latency_ms","y_label":"Latency","annotations":["The zero baseline keeps category differences proportionate."]},
        {**common,"id":"show-trend","title":"Use a line only when x has an order","question":"How does the example value change across ordered runs?","intent":"trend","source":{"path":"project/results/measurements.json","pointer":"/trend"},"x":"run","y":"latency_ms","x_label":"Run number","y_label":"Latency"},
        {**common,"id":"paired-latency","type":"custom","title":"Keep each before/after pair together","question":"How does the same scenario compare before and after?","source":{"path":"project/results/measurements.json","pointer":"/paired"},"fields":["scenario","before_ms","after_ms"],"asset":"project/results/charts/paired.svg","generator":"build_paired_chart.py","reason":"A paired-dot chart preserves the before/after relationship for each scenario without implying a time series."}]}
    specs = root/".project-docs/presentations"; specs.mkdir(parents=True,exist_ok=True)
    (specs/"phase-1.json").write_text(json.dumps(spec,indent=2)+"\n")
    (root/"project/roadmap.md").write_text('# Example roadmap\n\nSynthetic demonstration only.\n\n| Phase | Progress |\n|---|---|\n| [Phase 1](phases/phase-1/tasks.md) | 2/5 |\n')
    (root/"project/roadmap.html").write_text('<!doctype html><html lang="en"><title>Example roadmap</title><h1>Example roadmap</h1><p>Synthetic demonstration only.</p><p><a href="phases/phase-1/tasks.md">Phase 1: 2/5 verified tasks</a></p></html>')
    (root/"project/issues.md").write_text('# Example issue log\n\n## IMP-001: Example validation dependency\n\n**Status:** OPEN\n\nSynthetic blocker: a representative validation case is waiting for the example owner. This is not a real incident.\n')
    run("sync_presentation.py",1,"--new")
    path = phase/"presentation.html"; text = path.read_text()
    replacements = {
        "TODO: State the outcome this phase must demonstrate and the decision this audience needs to make.":"An illustrative route with source-backed charts. All statuses and measurements here are synthetic fixtures, not live project results.",
        "TODO: Explain the phase goal and prerequisites. Group tasks into meaningful steps when needed.":"Five example tasks form three steps. Work is active in the copy step, while verification is blocked; both remain visible.",
        "TODO: Explain the evidence and remaining condition for the tasks that need attention.":"The checklist is the status owner. An in-progress or blocked task does not count as a verified completion.",
        "TODO: State what the measurements establish, without claiming more than they show.":"These invented values demonstrate chart selection and source inspection. They establish no performance advantage in a real system.",
        "TODO: Real or synthetic data, sample size, run date and environment.":"Synthetic fixtures only. No real benchmark run, production environment or live migration is represented.",
        "TODO: Who checked the results; distinguish an AI judgment from a human review.":"The figures are rendered from the JSON fixture. No human review or statistical conclusion is implied.",
        "TODO: What was not tested and what could change the conclusion.":"A real decision would need representative cases, repeated measurements and an explicit acceptance rule.",
        "TODO: Issue ID or explicitly no blockers":"IMP-001: example validation dependency", "<td>TODO</td>":"<td>Example validation owner</td>",
        "TODO: Name the decision, its owner and the effect on the next step.":"The example validation owner must supply the representative case before the verification step can proceed.",
        "TODO: Describe the next action, owner and evidence needed.":"Reconcile the remaining example records, unblock the representative case, and verify before handing over."}
    for old,new in replacements.items(): text=text.replace(old,new)
    path.write_text(text,encoding="utf-8")
    run("sync_project_readme.py"); run("sync_memory_bank.py"); run("sync_presentation.py",1,"--check")
    print(path)


if __name__ == "__main__": main()
