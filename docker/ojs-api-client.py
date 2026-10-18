import json,re,urllib.request,urllib.parse,http.cookiejar
from pathlib import Path
root=Path(__file__).resolve().parents[1];base='http://localhost:8080/vestnik-test/en'
class LocalPolicy(http.cookiejar.DefaultCookiePolicy):
 def return_ok_domain(self,cookie,request):
  if cookie.domain in ('.localhost','localhost'): return True
  return super().return_ok_domain(cookie,request)
class Response:
 def __init__(self,r): self.status_code=r.code; self.content=r.read();self.text=self.content.decode('utf8','replace')
 def json(self):return json.loads(self.text)
class Client:
 def __init__(self):self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar(policy=LocalPolicy())));self.headers={}
 def request(self,method,url,data=None,json=None,headers=None):
  h=dict(self.headers);h.update(headers or {}); body=None
  if json is not None:body=__import__('json').dumps(json).encode();h['Content-Type']='application/json'
  elif isinstance(data,dict):body=urllib.parse.urlencode(data,doseq=True).encode()
  elif data is not None:body=data
  try:r=self.opener.open(urllib.request.Request(url,body,h,method=method),timeout=60)
  except urllib.error.HTTPError as e:r=e
  return Response(r)
 def get(self,u):return self.request('GET',u)
 def post(self,u,**kw):return self.request('POST',u,**kw)
 def put(self,u,**kw):return self.request('PUT',u,**kw)
def session(username):
 rows=json.loads((root/'.local-test-users.json').read_text())+json.loads((root/'.local-full-users.json').read_text());a=next((a for a in rows if a['username']==username),None)
 if username=='admin':a=json.loads((root/'.local-admin.json').read_text())
 s=Client();html=s.get(base+'/login').text;token=re.search(r'name="csrfToken"[^>]*value="([^"]+)',html)
 r=s.post(base+'/login/signIn',data={'username':username,'password':a['password'],'csrfToken':token.group(1) if token else ''})
 m=re.search(r'"csrfToken"\s*:\s*"([^"]+)"',r.text) or re.search(r'name="csrfToken"[^>]*value="([^"]+)',r.text)
 if m:s.headers['X-Csrf-Token']=m.group(1)
 s.headers['Accept']='application/json';return s
if __name__=='__main__':
 s=session('admin');r=s.get(base+'/api/v1/submissions'); print(r.status_code,r.text[:1500])
