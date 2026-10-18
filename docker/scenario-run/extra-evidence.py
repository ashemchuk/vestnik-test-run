import urllib.request,json,pathlib,xml.etree.ElementTree as ET
r=pathlib.Path('/Users/shemchuk/Projects/vestnik/evidence/full-run')
for name,url in [('oai-identify','http://localhost:8080/vestnik-test/oai?verb=Identify'),('oai-records','http://localhost:8080/vestnik-test/oai?verb=ListRecords&metadataPrefix=oai_dc'),('release','https://api.github.com/repos/pkp/ojs/releases/tags/3_5_0-5')]:
 try:
  x=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'vestnik-local-test'}),timeout=30);v=x.read();(r/(name+('.json' if name=='release' else '.xml'))).write_bytes(v)
  if name=='release':d=json.loads(v);print({k:d.get(k) for k in ['tag_name','published_at','created_at','html_url']})
  else:print(name,x.status,len(v),'records',len(ET.fromstring(v).findall('.//{http://www.openarchives.org/OAI/2.0/}record')))
 except Exception as e:print(name,str(e))
