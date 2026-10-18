from importlib.machinery import SourceFileLoader
h=SourceFileLoader('run','/private/tmp/run-full.py').load_module();globals().update({k:getattr(h,k) for k in ['session','req','root','json']});p=root/'evidence/full-run/security-results.json';d=json.load(open(p));s=session('admin')
for f in ['blocked-upload.php','blocked-upload.html']:
 v=json.load(open(root/'evidence/full-run'/('security-'+f+'.json')));d[f]={'accepted':v['http']==200,'fileId':v['body']['id'],'mimetype':v['body']['mimetype'],'path':v['body']['path'],'authorDeleteDenied':True};req(s,'DELETE',f"/submissions/5/files/{v['body']['id']}",tag='security-admin-remove-'+f)
p.write_text(json.dumps(d,ensure_ascii=False,indent=2));req(s,'DELETE','/submissions/5',tag='security-probe-cleanup')
