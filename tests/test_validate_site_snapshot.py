import subprocess,sys,json
from pathlib import Path
from test_build_site_snapshot import config,inputs,run,ROOT
def test_validate_snapshot(tmp_path):
 config(tmp_path);inputs(tmp_path);run(tmp_path); r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_site_snapshot.py'),'--site-id','test','--digest-at','20260721T18','--sites-dir',str(tmp_path/'sites'),'--input',str(tmp_path/'out.json'),'--now','2026-07-21T18:30:00Z'],capture_output=True,text=True);assert r.returncode==0,r.stdout
def test_validate_rejects_tamper(tmp_path):
 config(tmp_path);inputs(tmp_path);run(tmp_path);p=tmp_path/'out.json';x=json.loads(p.read_text());x['status']='bad';p.write_text(json.dumps(x));r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_site_snapshot.py'),'--site-id','test','--digest-at','20260721T18','--sites-dir',str(tmp_path/'sites'),'--input',str(p),'--now','2026-07-21T18:30:00Z'],capture_output=True,text=True);assert r.returncode==1
