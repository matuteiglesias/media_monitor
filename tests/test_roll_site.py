import json, os, time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from roll_site import Result, roll

def snapshot(root, site='argentina-general', digest='20260721T18'):
 p=root/'apps/news_site/public/data/site_snapshot.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'site':{'site_id':site},'digest_at':digest,'snapshot_id':'a'*64,'metrics':{'item_count':11,'section_count':1}}));return p
class Fake:
 def __init__(self, root, deploy='noise\nhttps://roll-abc.vercel.app\n', health=None, fail=None):self.root=root;self.deploy=deploy;self.health=health or {'status':'ok','site_id':'argentina-general','snapshot_id':'a'*64,'digest_at':'20260721T18','item_count':11,'section_count':1};self.fail=fail;self.calls=[];self.health_calls=0
 def __call__(self, command, *, cwd, env=None):
  self.calls.append((command,env))
  if self.fail and self.fail==command[0:2]: return Result(command,1,'','bad')
  if command[:2]==['vercel','build']:
   out=self.root/'.vercel/output';out.mkdir(parents=True);(out/'config.json').write_text('{}'); os.utime(out,(time.time()+1,time.time()+1))
  if command[:2]==['vercel','deploy']:return Result(command,0,self.deploy,'progress')
  if command[:2]==['vercel','curl']:
   self.health_calls+=1
   value=self.health[self.health_calls-1] if isinstance(self.health,list) else self.health
   return Result(command,0,value if isinstance(value,str) else json.dumps(value),'')
  return Result(command,0,'','')
def latest(root):return json.loads(next((root/'storage/observability').glob('site_roll_latest_*.json')).read_text())
def test_successful_preview_roll(tmp_path):
 snapshot(tmp_path);f=Fake(tmp_path);r,c=roll('argentina-general','20260721T18','preview',tmp_path,f,lambda _:None);assert c==0 and r['status']=='ok';assert ['vercel','pull','--yes','--environment=preview'] in [x[0] for x in f.calls];assert latest(tmp_path)['snapshot_id']=='a'*64
def test_production_command_construction(tmp_path):
 snapshot(tmp_path);f=Fake(tmp_path);_,c=roll('argentina-general','20260721T18','production',tmp_path,f,lambda _:None);assert c==0;commands=[x[0] for x in f.calls];assert ['vercel','build','--prod'] in commands and ['vercel','deploy','--prebuilt','--prod'] in commands
def test_invalid_target_never_defaults_production(tmp_path):
 snapshot(tmp_path)
 try:roll('argentina-general','20260721T18','',tmp_path,Fake(tmp_path))
 except ValueError:pass
 else:assert False
def test_snapshot_mismatch_fails_before_vercel(tmp_path):
 snapshot(tmp_path,digest='wrong');f=Fake(tmp_path);r,c=roll('argentina-general','20260721T18','preview',tmp_path,f);assert c and r['failed_stage']=='identity' and not any(x[0][0]=='vercel' for x in f.calls)
def test_build_failure(tmp_path):
 snapshot(tmp_path);r,c=roll('argentina-general','20260721T18','preview',tmp_path,Fake(tmp_path,fail=['vercel','build']));assert c and r['failed_stage']=='build'
def test_missing_output(tmp_path):
 snapshot(tmp_path);f=Fake(tmp_path);f.__call__=lambda *a,**k: Result(a[0],0,'','')
 # class lookup prevents instance override; use a small runner without output
 def runner(command,**kw): return Result(command,0,'https://x.vercel.app' if command[:2]==['vercel','deploy'] else '','')
 r,c=roll('argentina-general','20260721T18','preview',tmp_path,runner);assert c and r['failed_stage']=='build'
def test_url_extraction_and_missing_host(tmp_path):
 snapshot(tmp_path);r,c=roll('argentina-general','20260721T18','preview',tmp_path,Fake(tmp_path,deploy='log https://x.vercel.app end'));assert c==0 and r['deployment_host']=='x.vercel.app';snapshot(tmp_path);r,c=roll('argentina-general','20260721T18','preview',tmp_path,Fake(tmp_path,deploy='no url'));assert c and r['failed_stage']=='deploy'
def test_malformed_health_and_identity_mismatches(tmp_path):
 for bad in ['not json',{'status':'ok','site_id':'argentina-general','snapshot_id':'bad','digest_at':'20260721T18','item_count':11,'section_count':1},{'status':'ok','site_id':'argentina-general','snapshot_id':'a'*64,'digest_at':'bad','item_count':11,'section_count':1},{'status':'ok','site_id':'argentina-general','snapshot_id':'a'*64,'digest_at':'20260721T18','item_count':1,'section_count':1}]:
  snapshot(tmp_path);r,c=roll('argentina-general','20260721T18','preview',tmp_path,Fake(tmp_path,health=bad),lambda _:None);assert c and r['failed_stage']=='health'
def test_health_retries_and_failure_record_is_safe(tmp_path):
 snapshot(tmp_path);ok={'status':'ok','site_id':'argentina-general','snapshot_id':'a'*64,'digest_at':'20260721T18','item_count':11,'section_count':1};f=Fake(tmp_path,health=['no',ok]);r,c=roll('argentina-general','20260721T18','preview',tmp_path,f,lambda _:None);assert c==0 and f.health_calls==2
 snapshot(tmp_path);r,c=roll('argentina-general','20260721T18','preview',tmp_path,Fake(tmp_path,deploy='token=secret'),lambda _:None);assert 'secret' not in json.dumps(latest(tmp_path))
def test_no_ingestion_or_editorial_commands(tmp_path):
 snapshot(tmp_path);f=Fake(tmp_path);roll('argentina-general','20260721T18','preview',tmp_path,f,lambda _:None);assert all(not any(word in ' '.join(c[0]) for word in ('s01','editorial','ingestion','export-pr3a')) for c in f.calls)
