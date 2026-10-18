"""Poll the authenticated OJS REST API and log status/stage changes.
Run manually or from an external scheduler. Uses the existing local editor account.
This demo does not install a plugin or modify OJS core.
"""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import json,datetime
client=SourceFileLoader('ojs_client',str(Path(__file__).with_name('ojs-api-client.py'))).load_module()
root=Path(__file__).resolve().parents[1]; dest=root/'evidence/full-run'; dest.mkdir(parents=True,exist_ok=True)
statepath=dest/'status-monitor-state.json';old=json.loads(statepath.read_text()) if statepath.exists() else {}
s=client.session('editor');r=s.get('http://localhost:8080/vestnik-test/api/v1/submissions?count=100');assert r.status_code==200,r.text
new={str(x['id']):{'status':x['status'],'stageId':x['stageId']} for x in r.json()['items']}
changes=[{'time':datetime.datetime.now().astimezone().isoformat(),'submissionId':int(k),'before':old.get(k),'after':v} for k,v in new.items() if k in old and old[k]!=v]
with (dest/'status-changes.jsonl').open('a') as out:
 for item in changes:out.write(json.dumps(item,ensure_ascii=False)+'\n')
statepath.write_text(json.dumps(new,indent=2));print(json.dumps({'observed':len(new),'changes':changes},ensure_ascii=False))
