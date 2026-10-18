from importlib.machinery import SourceFileLoader
h=SourceFileLoader('run','/private/tmp/run-full.py').load_module();globals().update({k:getattr(h,k) for k in ['session','req','upload','root','api','json']});m=h.m
import hashlib,urllib.request
out={};a=session('author');r=a.get(api+'/submissions/3');out['authorA_B_submission']={'http':r.status_code,'body':r.json()};u=json.load(open(root/'evidence/full-run/B-review-PDF.json'))['body']['url'];r=a.get(u);out['authorA_B_file']={'http':r.status_code,'body':r.text[:150]}
s=session('reviewer3');r=s.get(api+'/submissions/3');out['unassignedReviewer_B']={'http':r.status_code,'body':r.json()}
an=m.Client();u=json.load(open(root/'evidence/full-run/A-galley-state.json'))['body']['galleys'][0]['file']['url'];r=an.get(u);out['anonymous_internal_galley']={'http':r.status_code,'body':r.text[:120]};r=an.get('http://localhost:8080/vestnik-test/ru/article/download/2/2/15');out['anonymous_public_PDF']={'http':r.status_code,'bytes':len(r.content),'matchesFixture':r.content==(root/'test-data/full-run/A-v2.pdf').read_bytes()}
u=json.load(open(root/'evidence/full-run/A-upload-original.json'))['body']['url'];r=an.get(u);out['anonymous_original_manuscript']={'http':r.status_code,'body':r.text[:120]}
r=an.get('http://localhost:8080/vestnik-test/ru/article/download/2/2/15');out['A_unchanged_after_C']=r.content==(root/'test-data/full-run/A-v2.pdf').read_bytes()
s=session('author2');d=req(s,'POST','/submissions',{'locale':'ru','sectionId':1},'security-probe-draft');sid=d['id'];out['probeSubmissionId']=sid
for filename in ['blocked-upload.php','blocked-upload.html']:
 try: d=upload(s,sid,filename,tag='security-'+filename);out[filename]={'accepted':True,'fileId':d['id'],'path':d['path'],'mimetype':d['mimetype']};req(s,'DELETE',f"/submissions/{sid}/files/{d['id']}",tag='security-remove-'+filename)
 except RuntimeError as ex:out[filename]={'accepted':False,'error':str(ex)}
(root/'evidence/full-run/security-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
mail=json.load(urllib.request.urlopen('http://localhost:8025/api/v1/messages'));selected=[]
for msg in mail['messages']:
 if any(t in msg['Subject'] for t in ['Б отклонена','Сможете ли','А — доработка']):
  d=json.load(urllib.request.urlopen('http://localhost:8025/api/v1/message/'+msg['ID']));(root/'evidence/full-run'/('mail-final-'+msg['ID']+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2));selected.append({'id':msg['ID'],'subject':msg['Subject'],'to':msg['To'],'text':d['Text']})
(root/'evidence/full-run/mail-final-selected.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2))
