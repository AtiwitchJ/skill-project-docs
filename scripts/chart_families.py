"""Additional deterministic chart encodings. No plotting/runtime dependency."""
import math
from datetime import datetime, timezone

RATIONALE = {
    "grouped-bar": "Side-by-side bars compare named series within categories on a common zero baseline and unit.",
    "multi-line": "Separate lines compare series across the same ordered x values and unit; missing values are not interpolated.",
    "area": "A zero-baseline filled area shows the magnitude of a nonnegative measure over ordered observations.",
    "histogram": "Explicit bins show the distribution of raw observations; bin choice affects the apparent shape.",
    "box": "Boxes summarize raw sample distributions using linear-interpolated quartiles and Tukey 1.5-IQR whiskers; dots show outliers, not confidence intervals.",
    "ecdf": "The empirical cumulative distribution shows the observed fraction at or below each value without selecting histogram bins.",
    "range": "Supplied interval endpoints and optional estimates expose uncertainty or spread; their statistical meaning must be stated in the limits.",
    "dumbbell": "Linked points preserve the before/after pairing within each category without implying a time series.",
    "waterfall": "Signed contributions explain how a starting total changes; contributions must reconcile with any supplied final total.",
    "timeline": "Intervals show supplied start/end positions or dates, including overlap; task counts never determine duration.",
    "pareto": "Descending nonnegative contributions and an explicitly labelled cumulative-share line show concentration; the two scales are kept distinct.",
}
INTENTS = {"grouped-comparison":"grouped-bar", "series-trend":"multi-line", "volume":"area",
           "distribution":"histogram", "spread":"box", "cumulative-distribution":"ecdf",
           "uncertainty":"range", "paired-comparison":"dumbbell", "contribution":"waterfall",
           "schedule":"timeline", "concentration":"pareto"}


def quantile(values, p):
    values = sorted(values)
    if not values: raise ValueError("quantile needs observations")
    position = (len(values)-1)*p; low = int(position); high = math.ceil(position)
    return values[low]+(values[high]-values[low])*(position-low)


def render(typ, rows, spec):
    from presentation_charts import number, fmt, svg_text as text, escape, PALETTE
    x, y = spec.get("x"), spec.get("y")
    series = spec.get("series", [])
    field = spec.get("value", y or x)
    if typ in {"histogram","ecdf"}: fields = [field]
    elif typ in {"grouped-bar","multi-line"}: fields = [x]+[s["field"] for s in series]
    elif typ == "range": fields = [x,spec.get("low","low"),spec.get("high","high")]+([spec["value"]] if spec.get("value") else [])
    elif typ == "dumbbell": fields = [x,spec.get("before","before"),spec.get("after","after")]
    elif typ == "timeline": fields = [x,spec.get("start_field","start"),spec.get("end_field","end")]
    else: fields = [x,y]
    if any(not f for f in fields) or any(f not in r for r in rows for f in fields):
        raise ValueError("chart fields are missing from source rows")
    limit=200000 if typ in {'histogram','box','ecdf'} else 5000
    if len(rows)>limit: raise ValueError(f"more than {limit} observations: aggregate explicitly or use a custom chart")
    if series and typ not in {"grouped-bar","multi-line"}: raise ValueError("series are not supported by this chart family")
    if typ in {"grouped-bar","multi-line"} and (not 1<=len(series)<=6 or len({s['field'] for s in series})!=len(series)):
        raise ValueError("use 1–6 distinct series with the same unit")
    color = spec.get("color",PALETTE[0]); unit=spec["unit"]
    left,right,top,bottom,height = 210,870,65,355,460
    parts=[]
    def line(x1,y1,x2,y2,stroke="#cbd7db",width=1):
        parts.append(f'<path d="M{x1:.3f} {y1:.3f}L{x2:.3f} {y2:.3f}" stroke="{stroke}" stroke-width="{width}" fill="none"/>')
    def rectangle(px,py,w,h,fill):
        parts.append(f'<rect x="{px:.3f}" y="{py:.3f}" width="{max(0,w):.3f}" height="{max(0,h):.3f}" fill="{fill}"/>')
    def dot(px,py,r=5,fill=None,title=""):
        parts.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="{r}" fill="{fill or color}"><title>{escape(title)}</title></circle>')
    def domain(values, zero=False):
        lo,hi=min(values),max(values)
        if zero:lo,hi=min(0,lo),max(0,hi)
        if lo==hi:lo,hi=lo-.5,hi+.5
        return lo,hi
    def scale(lo,hi,a,b):return lambda v:a+(v-lo)/(hi-lo)*(b-a)
    def xaxis(lo,hi,label,date=False):
        for i in range(5):
            v=lo+(hi-lo)*i/4;px=left+(right-left)*i/4
            line(px,top,px,bottom)
            tick=datetime.fromtimestamp(v,timezone.utc).strftime('%m-%d %H:%M') if date else fmt(v)
            parts.append(text(px,bottom+25,tick,12,"middle"))
        parts.append(text((left+right)/2,height-18,label,14,"middle"))
    def yaxis(lo,hi,label):
        for i in range(5):
            v=lo+(hi-lo)*i/4;py=bottom-(bottom-top)*i/4
            line(left,py,right,py);parts.append(text(left-12,py+4,fmt(v),12,"end"))
        parts.append(text(left,25,label,14))
    def categories():
        if len(rows)>16 or len({str(r[x]) for r in rows})!=len(rows): raise ValueError("use at most 16 unique categories, or aggregate explicitly")
    def temporal(values):
        date=all(isinstance(v,str) for v in values)
        if not date and any(isinstance(v,str) for v in values):raise ValueError("do not mix dates and numeric positions")
        out=[]
        for v in values:
            if date:
                dt=datetime.fromisoformat(v.replace('Z','+00:00'));out.append(dt.replace(tzinfo=dt.tzinfo or timezone.utc).timestamp())
            else:out.append(number(v))
        return out,date
    def ordered(values):
        if len(values)<2 or any(a>=b for a,b in zip(values,values[1:])):raise ValueError("x must be strictly increasing; do not invent category order")
    def legend():
        for i,s in enumerate(series):parts.append(text(75+i*145,27,s.get('label',s['field']),12,fill=PALETTE[i]))
    if typ=="grouped-bar":
        categories();legend();height=140+len(rows)*max(65,len(series)*17);bottom=height-75
        vals=[[number(r[s['field']]) for s in series] for r in rows];lo,hi=domain([v for g in vals for v in g],True);sx=scale(lo,hi,left,right)
        xaxis(lo,hi,spec.get('y_label','Value')+(f' ({unit})' if unit else ''))
        gap=(bottom-top)/len(rows)
        for i,(r,g) in enumerate(zip(rows,vals)):
            center=top+gap*(i+.5);parts.append(text(left-14,center+4,str(r[x])[:28],13,'end'))
            for n,v in enumerate(g):
                py=center+(n-(len(g)-1)/2)*15
                rectangle(min(sx(0),sx(v)),py-5,abs(sx(v)-sx(0)),10,PALETTE[n]);dot(sx(v),py,1,PALETTE[n],f'{r[x]} / {series[n].get("label",series[n]["field"])}: {fmt(v)}')
    elif typ in {"multi-line","area"}:
        left=80;xs,date=temporal([r[x] for r in rows]);ordered(xs)
        values=[[number(r[s['field']]) for r in rows] for s in series] if series else [[number(r[y]) for r in rows]]
        if typ=='area' and any(v<0 for v in values[0]):raise ValueError("area requires nonnegative values and a zero baseline")
        lo,hi=domain([v for group in values for v in group],typ=='area');sx=scale(min(xs),max(xs),left,right);sy=scale(lo,hi,bottom,top)
        yaxis(lo,hi,spec.get('y_label',y or 'Value')+(f' ({unit})' if unit else ''));xaxis(min(xs),max(xs),spec.get('x_label',x),date)
        if series:legend()
        for n,values_ in enumerate(values):
            points=' '.join(f'{sx(a):.3f},{sy(b):.3f}' for a,b in zip(xs,values_));stroke=PALETTE[n] if series else color
            if typ=='area':parts.append(f'<polygon points="{sx(xs[0])},{sy(0)} {points} {sx(xs[-1])},{sy(0)}" fill="{color}" fill-opacity="0.18"/>')
            parts.append(f'<polyline points="{points}" stroke="{stroke}" stroke-width="3" fill="none"/>')
            for a,b in zip(xs,values_):dot(sx(a),sy(b),3,stroke,fmt(b))
    elif typ in {"histogram","ecdf"}:
        left=85;values=sorted(number(r[field]) for r in rows);lo,hi=domain(values);sx=scale(lo,hi,left,right)
        if typ=='histogram':
            count=spec.get('bins',min(10,max(1,math.ceil(math.sqrt(len(values))))))
            if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=40:raise ValueError("bins must be an integer from 1 to 40")
            bins=[0]*count;span=(hi-lo)/count
            for v in values:bins[min(count-1,int((v-lo)/span))]+=1
            ymax=max(bins) or 1;sy=scale(0,ymax,bottom,top);yaxis(0,ymax,'Observations');xaxis(lo,hi,spec.get('x_label',field)+(f' ({unit})' if unit else ''))
            for i,n in enumerate(bins):
                rectangle(sx(lo+i*span)+1,sy(n),(right-left)/count-2,bottom-sy(n),color)
                parts.append(text(sx(lo+(i+.5)*span),sy(n)-6,n,12,'middle'))
        else:
            yaxis(0,1,'Observed cumulative fraction');xaxis(lo,hi,spec.get('x_label',field)+(f' ({unit})' if unit else ''))
            points=[(sx(values[0]),bottom)];old=0
            for i,v in enumerate(values,1):
                yy=bottom-(bottom-top)*i/len(values);points.extend([(sx(v),bottom-(bottom-top)*old),(sx(v),yy)]);old=i/len(values)
            parts.append('<polyline points="'+' '.join(f'{a:.3f},{b:.3f}' for a,b in points)+f'" stroke="{color}" stroke-width="3" fill="none"/>')
    elif typ=='box':
        groups={}
        for r in rows:groups.setdefault(str(r[x]),[]).append(number(r[y]))
        if len(groups)>16:raise ValueError("box chart supports at most 16 groups")
        height=140+len(groups)*50;bottom=height-75;lo,hi=domain([v for g in groups.values() for v in g]);sx=scale(lo,hi,left,right)
        xaxis(lo,hi,spec.get('y_label',y)+(f' ({unit})' if unit else ''))
        for i,(label,values) in enumerate(groups.items()):
            center=top+(bottom-top)*(i+.5)/len(groups);q1,median,q3=[quantile(values,p) for p in (.25,.5,.75)];iqr=q3-q1
            inner=[v for v in values if q1-1.5*iqr<=v<=q3+1.5*iqr];low,high=min(inner),max(inner)
            parts.append(text(left-15,center+4,f'{label[:23]} (n={len(values)})',12,'end'));line(sx(low),center,sx(high),center,color,2)
            rectangle(sx(q1),center-11,max(1,sx(q3)-sx(q1)),22,'#dcece7');line(sx(median),center-12,sx(median),center+12,color,3)
            for v in values:
                if v<low or v>high:dot(sx(v),center,3,title=fmt(v))
            dot(sx(median),center,2,title=f'Q1={fmt(q1)}, median={fmt(median)}, Q3={fmt(q3)}')
    elif typ in {"range","dumbbell","timeline"}:
        categories();height=145+len(rows)*50;bottom=height-80
        if typ=='range':a,b=spec.get('low','low'),spec.get('high','high')
        elif typ=='dumbbell':a,b=spec.get('before','before'),spec.get('after','after')
        else:a,b=spec.get('start_field','start'),spec.get('end_field','end')
        av,date=temporal([r[a] for r in rows]) if typ=='timeline' else ([number(r[a]) for r in rows],False)
        bv,date2=temporal([r[b] for r in rows]) if typ=='timeline' else ([number(r[b]) for r in rows],False)
        if date!=date2:raise ValueError("timeline endpoints must use the same date/numeric representation")
        if typ!='dumbbell' and any(aa>bb for aa,bb in zip(av,bv)):raise ValueError("lower/start endpoint exceeds upper/end endpoint")
        lo,hi=domain(av+bv);sx=scale(lo,hi,left,right);xaxis(lo,hi,spec.get('x_label','Position' if typ=='timeline' else 'Value')+(f' ({unit})' if unit else ''),date)
        if typ=='dumbbell':parts.append(text(left,25,spec.get('before_label',a)+' (gray) → '+spec.get('after_label',b)+' (green)',14))
        for i,(row,aa,bb) in enumerate(zip(rows,av,bv)):
            center=top+(bottom-top)*(i+.5)/len(rows);parts.append(text(left-15,center+4,str(row[x])[:28],13,'end'))
            line(sx(aa),center,sx(bb),center,'#b7c8cb',4 if typ!='timeline' else 18)
            if typ=='dumbbell':dot(sx(aa),center,6,'#63757b',fmt(aa));dot(sx(bb),center,6,color,fmt(bb))
            elif typ=='timeline':dot(sx(aa),center,3,title=str(row[a]));dot(sx(bb),center,3,title=str(row[b]))
            else:
                line(sx(aa),center-8,sx(aa),center+8,color,2);line(sx(bb),center-8,sx(bb),center+8,color,2)
                if spec.get('value'):
                    value=number(row[spec['value']])
                    if not aa<=value<=bb:raise ValueError("range estimate must lie inside its supplied interval")
                    dot(sx(value),center,5,title=fmt(value))
    elif typ=='waterfall':
        categories();left=80;start=number(spec.get('start',0));totals=[start]
        for row in rows:totals.append(totals[-1]+number(row[y]))
        if 'end' in spec and not math.isclose(totals[-1],number(spec['end']),rel_tol=1e-9,abs_tol=1e-9):raise ValueError("waterfall contributions do not reconcile with the supplied end")
        lo,hi=domain(totals,True);sy=scale(lo,hi,bottom,top);yaxis(lo,hi,spec.get('y_label',y)+(f' ({unit})' if unit else ''));gap=(right-left)/len(rows)
        for i,row in enumerate(rows):
            px=left+gap*(i+.2);a,b=totals[i:i+2];rectangle(px,min(sy(a),sy(b)),gap*.6,abs(sy(a)-sy(b)),color if b>=a else '#b04e54')
            parts.append(text(px+gap*.3,bottom+25,str(row[x])[:16],11,'middle'));parts.append(text(px+gap*.3,min(sy(a),sy(b))-8,fmt(row[y]),12,'middle'))
            if i<len(rows)-1:line(px+gap*.6,sy(b),px+gap,sy(b),'#9dadaf')
        parts.append(text(left,430,f'Start: {fmt(start)} · End: {fmt(totals[-1])} {unit}',14))
    else:  # Pareto: labels make both value and cumulative-share scales explicit.
        categories();left=80;ranked=sorted(rows,key=lambda r:number(r[y]),reverse=True);vals=[number(r[y]) for r in ranked]
        if any(v<0 for v in vals) or sum(vals)<=0:raise ValueError("Pareto requires nonnegative contributions and a positive total")
        sy=scale(0,max(vals),bottom,top);yaxis(0,max(vals),spec.get('y_label',y)+(f' ({unit})' if unit else ''));gap=(right-left)/len(rows);points=[];total=0
        for i,(row,v) in enumerate(zip(ranked,vals)):
            px=left+gap*(i+.5);rectangle(px-gap*.3,sy(v),gap*.6,bottom-sy(v),color);total+=v;share=total/sum(vals)
            points.append((px,bottom-share*(bottom-top)));parts.append(text(px,bottom+25,str(row[x])[:16],11,'middle'))
        parts.append('<polyline points="'+' '.join(f'{a:.3f},{b:.3f}' for a,b in points)+'" stroke="#b04e54" stroke-width="3" fill="none"/>')
        for i in range(5):parts.append(text(right+12,bottom-(bottom-top)*i/4+4,f'{i*25}%',12,fill='#b04e54'))
        parts.append(text(right,25,'Cumulative share (right)',12,'end',fill='#b04e54'))
    title_id='chart-'+spec['id']+'-title'
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height:g}" role="img" aria-labelledby="{title_id}" font-family="system-ui,sans-serif"><title id="{title_id}">{escape(spec["title"])}</title><desc>{escape(spec["question"])}</desc><rect width="960" height="{height:g}" fill="white"/>'+''.join(parts)+'</svg>'
    return svg,fields,[[r[f] for f in fields] for r in rows]
