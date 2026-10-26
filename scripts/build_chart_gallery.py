#!/usr/bin/env python3
"""Create a source-backed gallery of every native chart family; synthetic values only."""
import argparse
import json
from pathlib import Path

import presentation_charts as charts
from test_reporting import chart_figure,page


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    root=args.output.resolve()
    if root.exists() and any(root.iterdir()):parser.error('output must be empty')
    root.mkdir(parents=True,exist_ok=True)
    data={"disclaimer":"Synthetic chart fixtures. No benchmark, confidence claim or real project schedule.",
          "categories":[{"label":"A","value":12},{"label":"B","value":8},{"label":"C","value":5}],
          "ordered":[{"x":i,"y":v,"a":v,"b":v+3} for i,v in enumerate([8,12,9,15,18],1)],
          "parts":[{"group":"A","done":8,"left":2},{"group":"B","done":5,"left":5}],
          "matrix":[{"x":a,"y":b,"value":i+j} for i,a in enumerate(['A','B','C']) for j,b in enumerate(['Small','Large'])],
          "samples":[{"group":"A" if i<6 else "B","value":v} for i,v in enumerate([2,3,4,4,5,12,3,5,6,7,8,11])],
          "intervals":[{"label":"Small","before":12,"after":8,"low":6,"high":10,"estimate":8},{"label":"Large","before":20,"after":14,"low":11,"high":18,"estimate":14}],
          "contributions":[{"label":"Sales","value":20},{"label":"Returns","value":-7},{"label":"Other","value":5}],
          "schedule":[{"label":"Prepare","start":"2026-01-01T00:00:00Z","end":"2026-01-03T00:00:00Z"},{"label":"Validate","start":"2026-01-02T00:00:00Z","end":"2026-01-05T00:00:00Z"}]}
    (root/'gallery-data.json').write_text(json.dumps(data,indent=2)+'\n')
    definitions=[('bar','categories',dict(x='label',y='value')),('line','ordered',dict(x='x',y='y')),('scatter','ordered',dict(x='x',y='y')),
        ('stacked-bar','parts',dict(x='group',series=[{'field':'done'},{'field':'left'}])),('heatmap','matrix',dict(x='x',y='y',value='value')),
        ('grouped-bar','parts',dict(x='group',series=[{'field':'done'},{'field':'left'}])),('multi-line','ordered',dict(x='x',series=[{'field':'a'},{'field':'b'}])),
        ('area','ordered',dict(x='x',y='y')),('histogram','samples',dict(value='value',bins=5)),('box','samples',dict(x='group',y='value')),
        ('ecdf','samples',dict(value='value')),('range','intervals',dict(x='label',low='low',high='high',value='estimate')),
        ('dumbbell','intervals',dict(x='label',before='before',after='after')),('waterfall','contributions',dict(x='label',y='value',start=100,end=118)),
        ('timeline','schedule',dict(x='label',unit='UTC date')),('pareto','categories',dict(x='label',y='value'))]
    specs=[{"id":typ,"type":typ,"title":typ.replace('-',' ').title(),"question":charts.RATIONALE[typ],"source":{"path":"gallery-data.json","pointer":"/"+pointer},"unit":"example units","limitations":data['disclaimer'],**fields} for typ,pointer,fields in definitions]
    (root/'chart-specs.json').write_text(json.dumps(specs,indent=2)+'\n')
    body='<h1>16 native chart families</h1><p class="note">'+data['disclaimer']+'</p><p>Choose a chart by the question and available evidence. Every figure has an exact source-value table.</p><nav>'+ ' · '.join(f'<a href="#{s["id"]}">{s["title"]}</a>' for s in specs)+'</nav>'
    md=['# Native chart gallery',data['disclaimer']]
    for spec in specs:
        chart=charts.render(root,spec);destination=root/'charts'/(chart['id']+'.svg');destination.parent.mkdir(exist_ok=True);destination.write_text(chart['svg'])
        body+='<section id="'+chart['id']+'">'+chart_figure(chart,'gallery-data.json')+'</section>'
        md.extend(['## '+chart['title'],f'![{chart["title"]}](charts/{chart["id"]}.svg)',chart['why'],'Limits: '+chart['limits'],f'Source: [gallery-data.json](gallery-data.json) · `{chart["source"]["pointer"]}`'])
        table=['| '+' | '.join(chart['fields'])+' |','| '+' | '.join('---' for _ in chart['fields'])+' |']
        table.extend('| '+' | '.join(str(v).replace('|','\\|') for v in row)+' |' for row in chart['rows']);md.append('\n'.join(table))
    (root/'gallery.html').write_text(page('Native chart gallery',body));(root/'gallery.md').write_text('\n\n'.join(md)+'\n')
    print(root/'gallery.html')


if __name__=='__main__':main()
