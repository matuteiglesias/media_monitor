#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from build_site_snapshot import ROOT, read_json, validate_config, validate_schema, canonical_id, parse_time

def main():
 p=argparse.ArgumentParser(); p.add_argument('--site-id',required=True); p.add_argument('--digest-at',required=True); p.add_argument('--sites-dir',default='sites'); p.add_argument('--input',default='apps/news_site/public/data/site_snapshot.json'); p.add_argument('--now')
 a=p.parse_args()
 try:
  config=read_json(Path(a.sites_dir)/f'{a.site_id}.json'); validate_config(config); snap=read_json(Path(a.input)); validate_schema(snap)
  if snap['site']['site_id']!=a.site_id or snap['digest_at']!=a.digest_at: raise ValueError('snapshot site_id or digest_at does not match requested values')
  if snap['snapshot_id']!=canonical_id(snap): raise ValueError('snapshot_id is not deterministic canonical payload hash')
  if snap['metrics']['item_count'] != len(snap['latest']) and len(snap['latest']) != min(snap['metrics']['item_count'],config['presentation']['latest_count']): raise ValueError('item_count/latest mismatch')
  if snap['metrics']['item_count'] < config['selection']['minimum_items']: raise ValueError('snapshot below configured minimum_items')
  now=parse_time(a.now,'--now') if a.now else datetime.now(timezone.utc)
  if now-parse_time(snap['generated_at'],'generated_at') > timedelta(hours=config['selection']['max_age_hours']): raise ValueError('snapshot age exceeds configured max_age_hours')
  for item in [snap['hero'],*snap['latest']]:
   if parse_time(item['published_at'],item['index_id']) < now-timedelta(hours=config['selection']['max_age_hours']): raise ValueError('snapshot contains stale item')
  print(json.dumps({'status':'ok','snapshot_id':snap['snapshot_id'],'digest_at':snap['digest_at'],'item_count':snap['metrics']['item_count']})); return 0
 except Exception as e: print(f'[validate-site-snapshot] ERROR: {e}'); return 1
if __name__=='__main__': raise SystemExit(main())
