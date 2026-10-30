#!/usr/bin/env python3
"""Read-only result-section visual coverage and provenance checks.

Default candidates: project/results/*.md; add custom reports to the registry.
--require rejects missing coverage. A green general docs gate alone is not proof.
"""
import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit


def sections(text):
    result=[];current={'heading':'(document)','body':[]};fence=None
    for line in text.splitlines():
        mark=re.match(r'^\s*(`{3,}|~{3,})',line)
        if mark:
            if fence is None:fence=(mark[1][0],len(mark[1]))
            elif mark[1][0]==fence[0] and len(mark[1])>=fence[1]:fence=None
            continue
        if fence:continue
        heading=re.match(r'^#{1,6}\s+(.+?)\s*#*$',line)
        if heading:
            result.append(current);current={'heading':heading[1],'body':[]}
        else:current['body'].append(line)
    if fence is not None:raise ValueError('Unclosed code fence prevents reliable result-section inventory.')
    result.append(current)
    for item in result:
        item['body']='\n'.join(item['body'])
        numeric=[cell for line in item['body'].splitlines() if line.strip().startswith('|')
                 for cell in line.split('|')[1:-1] if re.search(r'\d',cell)]
        item['candidate']=len(numeric)>=2
    return result


class ImagesById(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self,text):
        super().__init__();self.frames=[];self.scopes={};self.images=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);own=None
        if tag=='img' and attrs.get('src'):self.images.append(attrs['src'])
        if attrs.get('id'):
            own={'images':[],'inline':[]};self.scopes.setdefault(attrs['id'],[]).append(own)
        active=[scope for _,scope in self.frames if scope is not None]+([own] if own else [])
        for scope in active:
            if tag=='img' and attrs.get('src'):scope['images'].append(attrs['src'])
            if tag=='svg':scope['inline'].append(attrs.get('data-asset-sha256'))
        if tag not in self.VOID:self.frames.append((tag,own))
    def handle_endtag(self,tag):
        for index in range(len(self.frames)-1,-1,-1):
            if self.frames[index][0]==tag:self.frames=self.frames[:index];break
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in self.VOID:self.handle_endtag(tag)


def inspect(root,required=False,reports=None):
    root=Path(root).resolve();findings=[];coverage=[]
    def add(code,where,message):findings.append({'code':code,'where':str(where),'message':message})
    def finish(status):return {'status':'failed' if findings else status,'findings':findings,'sections':coverage,
                               'limits':'Numeric-table detection is a candidate heuristic; registry completeness, plot correctness/comparability and visual readability still need human/agent review. No remote access or file writes.'}
    def local(value):
        if not isinstance(value,str) or not value or Path(value).is_absolute():raise ValueError('Use a nonempty project-relative path.')
        path=(root/value).resolve()
        if not path.is_relative_to(root):raise ValueError('Path escapes project.')
        return path
    registry=root/'.project-docs/report-visuals.json'
    try:
        config_path=root/'.project-docs/config.json';cfg=json.loads(config_path.read_text()) if config_path.exists() else {}
        policy=cfg.get('report_visuals',{})
        if not isinstance(policy,dict) or ('required' in policy and not isinstance(policy['required'],bool)):raise ValueError('Invalid report_visuals policy.')
        enabled=required or registry.exists() or policy.get('required') is True
        if not enabled:return finish('not-configured')
        data=json.loads(registry.read_text()) if registry.exists() else {'version':1,'reports':[]}
        if not isinstance(data,dict) or type(data.get('version')) is not int or data['version']!=1 or not isinstance(data.get('reports'),list):raise ValueError('Expected version 1 and reports list.')
        entries={}
        for entry in data['reports']:
            if not isinstance(entry,dict):raise ValueError('Report entry must be an object.')
            name=entry.get('markdown');local(name)
            if name in entries:raise ValueError('Duplicate report registry entry.')
            entries[name]=entry
        names=list(reports) if reports is not None else sorted({p.relative_to(root).as_posix() for p in (root/'project/results').glob('*.md')}|set(entries))
        for name in names:local(name)
    except (OSError,ValueError,TypeError,AttributeError) as error:
        add('invalid-visual-contract','.project-docs/report-visuals.json',str(error));return finish('failed')
    html_cache={}
    def embeds(path,element,asset,checksum):
        try:
            file=local(path)
            if file not in html_cache:html_cache[file]=ImagesById(file.read_text()).scopes
            scopes=html_cache[file].get(element,[])
            if len(scopes)!=1:return False
            for src in scopes[0]['images']:
                url=urlsplit(src)
                if not url.scheme and not url.netloc and (file.parent/unquote(url.path)).resolve()==asset:return True
            return checksum in scopes[0]['inline']
        except (OSError,ValueError,TypeError):return False
    def fingerprint(record,path_key,hash_key,where):
        try:
            path=local(record.get(path_key));checksum=record.get(hash_key)
            if not isinstance(checksum,str) or not re.fullmatch(r'[0-9a-f]{64}',checksum) or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum:raise ValueError('Missing/stale '+hash_key+' for '+str(record.get(path_key)))
            return path,checksum
        except (OSError,ValueError,TypeError) as error:add('stale-visual-input',where,str(error));return None,None
    for name in names:
        try:chunks=sections(local(name).read_text())
        except (OSError,ValueError) as error:add('missing-report',name,str(error));continue
        entry=entries.get(name)
        if entry is None:
            for chunk in chunks:
                if chunk['candidate']:add('unregistered-result-section',name+'#'+chunk['heading'],'Numeric result section has no declared visual/justified table-only coverage.');coverage.append({'report':name,'heading':chunk['heading'],'status':'unregistered'})
            continue
        try:
            if not local(entry.get('html')).is_file():raise ValueError('Paired HTML does not exist.')
        except (ValueError,TypeError) as error:add('missing-paired-html',name,str(error))
        records=entry.get('sections')
        if not isinstance(records,list):add('invalid-section-list',name,'sections must be a list.');continue
        grouped={}
        for chunk in chunks:grouped.setdefault(chunk['heading'],[]).append(chunk)
        seen=set()
        for record in records:
            if not isinstance(record,dict):add('invalid-section',name,'Section records must be objects.');continue
            heading=record.get('heading');where=name+'#'+str(heading)
            if not isinstance(heading,str) or heading in seen:add('duplicate-section',where,'Use one exact, unique Markdown heading per record.');continue
            seen.add(heading);matches=grouped.get(heading,[])
            if len(matches)!=1:add('missing-section',where,'Heading is missing/ambiguous.');continue
            body=matches[0]['body'];before=len(findings)
            sources=record.get('sources')
            if not isinstance(sources,list) or not sources:add('missing-visual-sources',where,'Declare every real raw source, including each environment/run.')
            else:
                for source in sources:
                    if isinstance(source,dict):fingerprint(source,'path','sha256',where)
                    else:add('invalid-source',where,'Source must be a path/checksum object.')
            for field in ('question','limitations'):
                if not isinstance(record.get(field),str) or not record[field].strip():add('missing-visual-context',where,'Missing '+field)
            if record.get('kind')=='table-only':
                reason=record.get('reason');decision=record.get('decision')
                try:
                    if not isinstance(reason,str) or len(reason.strip())<20 or not local(decision).is_file():raise ValueError('Table-only sections need a specific rationale and an actual reviewed decision/policy file.')
                except (ValueError,TypeError):add('unjustified-table-only',where,'Do not silently omit a useful comparison chart; supply a concrete table-only decision.')
                coverage.append({'report':name,'heading':heading,'status':'failed' if len(findings)>before else 'table-only; decision needs semantic review'})
                continue
            visuals=record.get('visuals')
            if not isinstance(visuals,list) or not visuals:add('missing-result-visual',where,'Create a sourced visual for this result, not merely regenerate an older unrelated chart.');visuals=[]
            placements=record.get('presentations',[])
            if not isinstance(placements,list):add('invalid-presentations',where,'presentations must be a list.');placements=[]
            phase=record.get('phase') or re.search(r'\bTask\s+\d+\.',heading,re.I)
            if not placements and (phase or not isinstance(record.get('no_presentation_reason'),str) or len(record['no_presentation_reason'].strip())<15):add('untracked-presentation',where,'Declare affected phase presentation placements, or justify a genuinely standalone report.')
            for visual in visuals:
                if not isinstance(visual,dict):add('invalid-visual',where,'Visual must be an object.');continue
                asset,checksum=fingerprint(visual,'asset','sha256',where)
                fingerprint(visual,'generator','generator_sha256',where)
                if asset is None:continue
                if asset.suffix.lower() not in ('.svg','.png','.jpg','.jpeg','.webp','.gif'):
                    add('unsupported-visual-asset',where,'Use a renderable image asset or a separately checksummed inline SVG.');continue
                images=re.findall(r'!\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))',body)
                images.extend((src,'') for src in ImagesById(body).images)
                md_paths=[]
                for a,b in images:
                    url=urlsplit(a or b)
                    if not url.scheme and not url.netloc:md_paths.append((local(name).parent/unquote(url.path)).resolve())
                inline=re.search(r'<svg\b[^>]*data-asset-sha256=[\"\']'+checksum,body)
                if asset not in md_paths and not inline:add('missing-markdown-visual',where,'Registered image is not embedded in this Markdown section.')
                if not embeds(entry.get('html'),record.get('html_id'),asset,checksum):add('missing-html-visual',where,'Registered image is absent from the paired HTML section/container.')
                for placement in placements:
                    if not isinstance(placement,dict) or not embeds(placement.get('path'),placement.get('html_id'),asset,checksum):add('missing-presentation-visual',where,'Registered image is absent from an affected presentation placement.')
            coverage.append({'report':name,'heading':heading,'status':'failed' if len(findings)>before else 'covered'})
        for chunk in chunks:
            if chunk['candidate'] and chunk['heading'] not in seen:add('unregistered-result-section',name+'#'+chunk['heading'],'New numeric section is not covered by the visual inventory.')
    return finish('passed' if coverage or findings else 'not-applicable')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--report',action='append',help='Project-relative Markdown owner; repeat for several reports.')
    parser.add_argument('--require',action='store_true')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args();result=inspect(args.root,args.require,args.report)
    if args.json:print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print('Report visuals: '+result['status'])
        for finding in result['findings']:print(finding['code']+': '+finding['where']+': '+finding['message'])
        print(result['limits'])
    return 1 if result['findings'] else 0


if __name__=='__main__':raise SystemExit(main())
