#!/usr/bin/env python3
"""Example custom chart: paired latency values, not independent categories.

python3 build_paired_chart.py project/results/measurements.json project/results/charts/paired.svg
Input: {"paired": [{"scenario": "Name", "before_ms": 100, "after_ms": 80}]}.
"""
import hashlib
import html
import json
import math
import sys
from pathlib import Path

source, output = map(Path, sys.argv[1:3])
rows = json.loads(source.read_text())["paired"]
values = [r[k] for r in rows for k in ("before_ms", "after_ms")]
if not rows or len(rows) > 8 or any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or v < 0 for v in values):
    raise SystemExit("use 1–8 scenarios with finite nonnegative millisecond values")
maximum = max(values) or 1
height = 155+len(rows)*65
parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" role="img" aria-labelledby="paired-title" font-family="system-ui,sans-serif">',
         '<title id="paired-title">Paired baseline and candidate latency by scenario</title>',
         '<desc>Linked points compare the same scenario before and after. Lower milliseconds are faster. This example uses synthetic fixture data.</desc>',
         f'<metadata id="project-docs-source-sha256">{hashlib.sha256(source.read_bytes()).hexdigest()}</metadata>',
         f'<metadata id="project-docs-generator-sha256">{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}</metadata>',
         f'<rect width="960" height="{height}" fill="white"/>',
         '<text x="220" y="28" font-size="15" fill="#63757b">Baseline</text><circle cx="205" cy="23" r="6" fill="#63757b"/>',
         '<text x="390" y="28" font-size="15" fill="#17665c">Candidate</text><circle cx="375" cy="23" r="6" fill="#17665c"/>']
for i,row in enumerate(rows):
    y = 75+i*65
    before, after = 220+row["before_ms"]/maximum*650, 220+row["after_ms"]/maximum*650
    parts += [f'<text x="24" y="{y+5}" font-size="16" fill="#273d45">{html.escape(row["scenario"])}</text>',
              f'<path d="M{before} {y}H{after}" stroke="#b7c6c9" stroke-width="4"/>']
    for x,value,color in ((before,row["before_ms"],"#63757b"),(after,row["after_ms"],"#17665c")):
        parts += [f'<circle cx="{x}" cy="{y}" r="7" fill="{color}"/>', f'<text x="{x}" y="{y-15}" text-anchor="middle" font-size="13" fill="{color}">{value:g}</text>']
for i in range(5):
    x,value = 220+i*650/4, maximum*i/4
    parts.append(f'<text x="{x}" y="{height-45}" text-anchor="middle" font-size="13" fill="#536876">{value:g}</text>')
parts.append(f'<text x="220" y="{height-15}" font-size="15" fill="#273d45">Latency (ms) · lower is faster</text></svg>')
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text("".join(parts),encoding="utf-8")
