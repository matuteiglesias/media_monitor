#!/usr/bin/env python3
"""Compile one digest-scoped source-news deployment snapshot."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator, FormatChecker

ROOT=Path(__file__).resolve().parents[1]
def read_json(path: Path): return json.loads(path.read_text(encoding='utf-8'))
def rows(path: Path):
    try: result=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    except json.JSONDecodeError as e: raise ValueError(f'{path}: invalid JSONL: {e}') from e
    if not result: raise ValueError(f'{path}: empty JSONL')
    if not all(isinstance(r,dict) for r in result): raise ValueError(f'{path}: JSONL rows must be objects')
    return result
def parse_time(value: Any, label: str):
    if not isinstance(value,str) or not value.strip(): raise ValueError(f'{label}: missing timestamp')
    try: return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
    except ValueError as e: raise ValueError(f'{label}: invalid timestamp {value!r}') from e
def digest_set(items, path):
    values={str(x.get('digest_at') or '').strip() for x in items}
    if '' in values or len(values)!=1: raise ValueError(f'{path}: expected exactly one non-empty digest_at, got {sorted(values)}')
    return values.pop()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def git_sha():
    try: return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    except Exception: return 'unknown'
def validate_config(config):
    for k in ('site_id','name','tagline','locale','selection','presentation'):
        if k not in config: raise ValueError(f'site config missing {k}')
    s=config['selection']; p=config['presentation']
    if not isinstance(s.get('topics'),list) or not s['topics']: raise ValueError('site config selection.topics must be non-empty')
    for k in ('max_age_hours','minimum_items','max_items'):
        if not isinstance(s.get(k),int) or s[k] < 0: raise ValueError(f'site config selection.{k} must be non-negative int')
    if not 0 < s['minimum_items'] <= s['max_items']: raise ValueError('site config minimum_items must be positive and <= max_items')
    if not isinstance(p.get('latest_count'),int) or p['latest_count'] < 1: raise ValueError('site config presentation.latest_count must be positive int')
def project_item(row, label):
    required=('index_id','title','topic','published_at','link')
    if any(not str(row.get(k) or '').strip() for k in required): raise ValueError(f'{label}: missing required item field')
    parse_time(row['published_at'],label)
    from urllib.parse import urlparse
    if urlparse(str(row['link'])).scheme not in {'http','https'}: raise ValueError(f'{label}: invalid URL')
    return {k:str(row.get(k) or '').strip() for k in ('index_id','title','topic','published_at','link')} | {'source':str(row.get('source') or '').strip() or 'unknown'}
def validate_schema(payload):
    schema=read_json(ROOT/'contracts/schemas/site_snapshot.v1.json')
    errors=sorted(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(payload),key=lambda e:list(e.path))
    if errors: raise ValueError('site snapshot schema validation failed: '+'; '.join(e.message for e in errors))
def canonical_id(payload):
    # generated_at is operational metadata, excluded so identical source input has a stable ID.
    canonical={k:v for k,v in payload.items() if k not in {'snapshot_id','generated_at'}}
    return hashlib.sha256(json.dumps(canonical,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def build(args):
    config_path=Path(args.sites_dir)/f'{args.site_id}.json'; config=read_json(config_path); validate_config(config)
    if config['site_id'] != args.site_id: raise ValueError('site config site_id does not match --site-id')
    refs_path=Path(args.indexes_dir)/'news_recent_refs_latest.jsonl'; groups_path=Path(args.indexes_dir)/'news_recent_groups_latest.jsonl'
    refs, groups=rows(refs_path), rows(groups_path)
    if digest_set(refs,refs_path)!=args.digest_at or digest_set(groups,groups_path)!=args.digest_at: raise ValueError('index digest_at does not match requested digest')
    now=parse_time(args.now,'--now') if args.now else datetime.now(timezone.utc)
    cutoff=now-timedelta(hours=config['selection']['max_age_hours'])
    selected=[]; seen=set()
    for i,row in enumerate(refs):
        item=project_item(row,f'{refs_path}:{i+1}')
        if item['topic'] not in config['selection']['topics'] or item['published_at'] and parse_time(item['published_at'],item['index_id']) < cutoff: continue
        if item['index_id'] in seen: continue
        seen.add(item['index_id']); selected.append(item)
    selected.sort(key=lambda x:(x['published_at'],x['index_id']),reverse=True); selected=selected[:config['selection']['max_items']]
    if len(selected)<config['selection']['minimum_items']: raise ValueError(f'selected {len(selected)} items; minimum_items={config["selection"]["minimum_items"]}')
    sections=[]
    for row in groups:
        topic=str(row.get('topic') or '').strip()
        if topic not in config['selection']['topics']: continue
        sections.append({'topic':topic,'article_count':int(row.get('article_count') or 0),'top_titles':[str(v) for v in (row.get('top_titles') or [])]})
    sections.sort(key=lambda x:x['topic'])
    if not sections: raise ValueError('no selected group sections')
    payload={'schema_name':'site_snapshot.v1','snapshot_id':'','site':{k:config[k] for k in ('site_id','name','tagline','locale')},'digest_at':args.digest_at,'generated_at':now.replace(microsecond=0).isoformat().replace('+00:00','Z'),'status':'ok','metrics':{'item_count':len(selected),'section_count':len(sections)},'hero':selected[0],'latest':selected[:config['presentation']['latest_count']],'sections':sections,'provenance':{'refs_path':str(refs_path),'refs_sha256':sha(refs_path),'groups_path':str(groups_path),'groups_sha256':sha(groups_path),'git_sha':git_sha()}}
    payload['snapshot_id']=canonical_id(payload); validate_schema(payload)
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=output.parent,delete=False) as f: json.dump(payload,f,ensure_ascii=False,indent=2); f.write('\n'); temp=Path(f.name)
    os.replace(temp,output); return payload
def main():
    p=argparse.ArgumentParser(); p.add_argument('--site-id',required=True); p.add_argument('--digest-at',required=True); p.add_argument('--sites-dir',default='sites'); p.add_argument('--indexes-dir',default='storage/indexes'); p.add_argument('--output',default='apps/news_site/public/data/site_snapshot.json'); p.add_argument('--now')
    try: print(json.dumps(build(p.parse_args()),ensure_ascii=False,indent=2))
    except Exception as e: print(f'[build-site-snapshot] ERROR: {e}'); return 1
    return 0
if __name__=='__main__': raise SystemExit(main())
