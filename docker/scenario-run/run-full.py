from importlib.machinery import SourceFileLoader
m=SourceFileLoader('client','/private/tmp/ojs-client.py').load_module();globals().update({k:getattr(m,k) for k in ['root','base','session','json']});api='http://localhost:8080/vestnik-test/api/v1';evidence=root/'evidence/full-run'
def req(s,method,path,payload=None,tag=None):
 r=s.request(method,api+path,json=payload);d=r.json();print(method,path,r.status_code,str(d)[:200]);
 if tag:(evidence/(tag+'.json')).write_text(json.dumps({'http':r.status_code,'body':d},ensure_ascii=False,indent=2))
 if r.status_code>=400:raise RuntimeError(d)
 return d
def upload(s,sid,file,stage=2,extra=None,tag=None):
 import uuid,mimetypes
 file=root/'test-data/full-run'/file;b='vestnik'+uuid.uuid4().hex;fields={'fileStage':stage,'genreId':1};fields.update(extra or {});parts=[]
 for k,v in fields.items():parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
 parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{file.name}"\r\nContent-Type: {mimetypes.guess_type(file.name)[0] or "application/octet-stream"}\r\n\r\n'.encode()+file.read_bytes()+b'\r\n');parts.append(f'--{b}--\r\n'.encode());r=s.request('POST',api+f'/submissions/{sid}/files',data=b''.join(parts),headers={'Content-Type':'multipart/form-data; boundary='+b});d=r.json();print('UPLOAD',file.name,r.status_code,str(d)[:150]);
 if tag:(evidence/(tag+'.json')).write_text(json.dumps({'http':r.status_code,'body':d},ensure_ascii=False,indent=2))
 if r.status_code>=400:raise RuntimeError(d)
 return d
def contributor(s,sid,pid,username,given,family):return req(s,'POST',f'/submissions/{sid}/publications/{pid}/contributors',{'givenName':{'ru':given,'en':given},'familyName':{'ru':family,'en':family},'email':username+'@example.test','userGroupId':14,'includeInBrowse':True})
if __name__=='__main__':
 s=session('author');sid=pid=2
 p=req(s,'PUT',f'/submissions/{sid}/publications/{pid}',{'title':{'ru':'А Проверка поиска дубликатов в массивах','en':'A Testing duplicate detection in arrays'},'abstract':{'ru':'<p>Тестовая статья с формулой и рисунком. Сравниваются попарный поиск и множество.</p>','en':'<p>A test paper with a formula and figure comparing pairwise search and a set.</p>'},'keywords':{'ru':['алгоритмы','дубликаты'],'en':['algorithms','duplicates']}},'A-metadata')
 authors=[]
 for u,g,f in [('author','Тестовый','Автор'),('author2','Второй','Автор'),('author3','Третий','Автор')]:authors.append(contributor(s,sid,pid,u,g,f))
 req(s,'PUT',f'/submissions/{sid}/publications/{pid}',{'primaryContactId':authors[0]['id']},'A-primary-contact');upload(s,sid,'A-original.docx',tag='A-upload-original');req(s,'PUT',f'/submissions/{sid}/submit',{},'A-submitted')

def decision(s,sid,code,roundid=None,tag=None,message='Тестовое решение редакции'):
 p={'decision':code,'actions':[{'id':'notifyAuthors','subject':message,'body':message,'locale':'ru'}]}
 if roundid:p.update(reviewRoundId=roundid,round=1)
 return req(s,'POST',f'/submissions/{sid}/decisions',p,tag)
def legacy(s,path,data,tag):
 data['csrfToken']=s.headers.get('X-Csrf-Token','');r=s.post('http://localhost:8080/vestnik-test/$$$call$$$/'+path,data=data)
 try:d=r.json()
 except:raise RuntimeError((r.status_code,r.text[:150]))
 (evidence/(tag+'.json')).write_text(json.dumps({'http':r.status_code,'body':d},ensure_ascii=False,indent=2));print('LEGACY',tag,r.status_code,str(d)[:150]);return d

def invite(s,sid,rid,uid,files,tag):
 return legacy(s,'grid/users/reviewer/reviewer-grid/update-reviewer',{'submissionId':sid,'stageId':3,'reviewRoundId':rid,'selectionType':1,'reviewerId':uid,'responseDueDate':'2026-10-13','reviewDueDate':'2026-10-14','reviewMethod':2,'template':'REVIEW_REQUEST','personalMessage':'Please review {$submissionTitle}. Reply by {$responseDueDate}; review by {$reviewDueDate}. {$reviewAssignmentUrl}','selectedFiles[]':files[0],'reviewFormId':1},tag)
def reviewer_action(s,sid,op,data,tag):
 data['csrfToken']=s.headers.get('X-Csrf-Token','');r=s.post(base+f'/reviewer/{op}/{sid}',data=data)
 try:d=r.json()
 except:raise RuntimeError((r.status_code,r.text[:120]))
 (evidence/(tag+'.json')).write_text(json.dumps({'http':r.status_code,'body':d},ensure_ascii=False,indent=2));print('REVIEWER',tag,r.status_code,str(d)[:150]);return d
def discussion(s,sid,stage,title,body,users,tag,existing=None):
 import re,html
 if existing: url=f'http://localhost:8080/vestnik-test/$$$call$$$/grid/queries/queries-grid/update-query?queryId={existing}&wasNew=1&submissionId={sid}&stageId={stage}'
 else:
  r=s.get(f'http://localhost:8080/vestnik-test/$$$call$$$/grid/queries/queries-grid/add-query?submissionId={sid}&stageId={stage}');content=r.json()['content'];url=html.unescape(re.search(r'<form[^>]+action="([^"]+)"',content).group(1))
 r=s.post(url,data={'csrfToken':s.headers['X-Csrf-Token'],'subject':title,'comment':body,'users[]':users});d=r.json();(evidence/(tag+'.json')).write_text(json.dumps({'http':r.status_code,'body':d},ensure_ascii=False,indent=2));print('DISCUSSION',tag,r.status_code,str(d)[:200]);return d
