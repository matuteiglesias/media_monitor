import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SCRIPT=ROOT/'scripts/build_site_snapshot.py'
def write_json(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x))
def write_jsonl(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(''.join(json.dumps(r)+'\n' for r in x))
def config(tmp, **selection):
 c={'site_id':'test','name':'Test news','tagline':'Test tagline','locale':'es-AR','selection':{'topics':['All Topics'],'max_age_hours':3,'minimum_items':5,'max_items':40}|selection,'presentation':{'latest_count':12,'show_sources':True}}; write_json(tmp/'sites/test.json',c)
def inputs(tmp,digest='20260721T18',n=5, topic='All Topics'):
 now='2026-07-21T18:00:00Z'; refs=[{'digest_at':digest,'index_id':f'id{i}','title':f'Title {i}','topic':topic,'published_at':f'2026-07-21T{18-i%2:02}:00:00Z','link':f'https://e.test/{i}','source':'E'} for i in range(n)]; groups=[{'digest_at':digest,'topic':topic,'article_count':n,'top_titles':['Title 0'],'window_type':'A','group_number':1}]; write_jsonl(tmp/'indexes/news_recent_refs_latest.jsonl',refs); write_jsonl(tmp/'indexes/news_recent_groups_latest.jsonl',groups)
def run(tmp, expect=True):
 r=subprocess.run([sys.executable,str(SCRIPT),'--site-id','test','--digest-at','20260721T18','--sites-dir',str(tmp/'sites'),'--indexes-dir',str(tmp/'indexes'),'--output',str(tmp/'out.json'),'--now','2026-07-21T18:30:00Z'],capture_output=True,text=True); assert r.returncode==(0 if expect else 1),r.stdout+r.stderr; return r
def test_valid_snapshot_and_deterministic_id(tmp_path):
 config(tmp_path); inputs(tmp_path); run(tmp_path); one=json.loads((tmp_path/'out.json').read_text()); run(tmp_path); two=json.loads((tmp_path/'out.json').read_text()); assert one['snapshot_id']==two['snapshot_id']; assert one['metrics']=={'item_count':5,'section_count':1}
def test_mixed_digests_fail(tmp_path): config(tmp_path); inputs(tmp_path); p=tmp_path/'indexes/news_recent_refs_latest.jsonl'; rows=[json.loads(x) for x in p.read_text().splitlines()]; rows[-1]['digest_at']='20260721T17'; write_jsonl(p,rows); run(tmp_path,False)
def test_requested_digest_mismatch_fails(tmp_path): config(tmp_path); inputs(tmp_path,'20260721T17'); run(tmp_path,False)
def test_stale_input_fails(tmp_path): config(tmp_path); inputs(tmp_path); p=tmp_path/'indexes/news_recent_refs_latest.jsonl'; rows=[json.loads(x) for x in p.read_text().splitlines()]; [r.update(published_at='2026-07-21T10:00:00Z') for r in rows]; write_jsonl(p,rows); run(tmp_path,False)
def test_minimum_items_fails(tmp_path): config(tmp_path); inputs(tmp_path,n=4); run(tmp_path,False)
def test_topic_max_items_and_branding(tmp_path):
 config(tmp_path,topics=['Sports'],max_items=2,minimum_items=1); inputs(tmp_path,n=3,topic='Sports'); run(tmp_path); snap=json.loads((tmp_path/'out.json').read_text()); assert len(snap['latest'])==2 and snap['site']['name']=='Test news'
def test_second_configuration_changes_branding_without_renderer_change(tmp_path):
 config(tmp_path); inputs(tmp_path); run(tmp_path); first=json.loads((tmp_path/'out.json').read_text())
 second={'site_id':'second','name':'Otra portada','tagline':'Otra voz','locale':'es-AR','selection':{'topics':['All Topics'],'max_age_hours':3,'minimum_items':5,'max_items':40},'presentation':{'latest_count':12,'show_sources':False}}
 write_json(tmp_path/'sites/second.json',second)
 r=subprocess.run([sys.executable,str(SCRIPT),'--site-id','second','--digest-at','20260721T18','--sites-dir',str(tmp_path/'sites'),'--indexes-dir',str(tmp_path/'indexes'),'--output',str(tmp_path/'second.json'),'--now','2026-07-21T18:30:00Z'],capture_output=True,text=True); assert r.returncode==0,r.stdout
 assert json.loads((tmp_path/'second.json').read_text())['site']['name'] != first['site']['name']
