import urllib.request,hashlib,json,pathlib
r=pathlib.Path('/Users/shemchuk/Projects/vestnik');out={}
for port in [8080,8081]:
 d={};b=f'http://localhost:{port}/vestnik-test'
 for name,path in [('issue','/ru/issue/view/2'),('A','/ru/article/view/2'),('C','/ru/article/view/4'),('pdf','/ru/article/download/2/2/15')]:
  x=urllib.request.urlopen(b+path);v=x.read();d[name]={'http':x.status,'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()}
  if name=='issue':d[name]['bothArticles']=all(t.encode() in v for t in ['А Проверка поиска','В Короткая заметка'])
  if name=='pdf':d[name]['matchesFixture']=v==(r/'test-data/full-run/A-v2.pdf').read_bytes()
 out[str(port)]=d
(r/'evidence/full-run/restore-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
