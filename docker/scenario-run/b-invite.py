from importlib.machinery import SourceFileLoader
h=SourceFileLoader('run','/private/tmp/run-full.py').load_module();globals().update({k:getattr(h,k) for k in ['session','req','upload','invite']})
s=session('editor');f=upload(s,3,'B-author.pdf',4,{'assocType':523,'assocId':5},'B-review-PDF');invite(s,3,5,4,[f['id']],'B-invite-reviewer1');invite(s,3,5,9,[f['id']],'B-invite-reviewer5');d=req(s,'GET','/submissions/3',tag='B-reviewers');print(d['reviewAssignments'])
