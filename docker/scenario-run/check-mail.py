import urllib.request,json
from pathlib import Path
r=json.load(urllib.request.urlopen('http://localhost:8025/api/v1/messages'));Path('/Users/shemchuk/Projects/vestnik/evidence/full-run/mail-summary.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print('messages',r.get('total'));print([(m['ID'],m['Subject'],[x['Address'] for x in m['To']]) for m in r['messages'][:12]])
