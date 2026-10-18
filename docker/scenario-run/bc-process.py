from importlib.machinery import SourceFileLoader
h=SourceFileLoader('run','/private/tmp/run-full.py').load_module();globals().update({k:getattr(h,k) for k in ['session','req','upload','legacy','decision','invite']})
s=session('admin')
for sid in [3,4]:legacy(s,'grid/users/stage-participant/stage-participant-grid/save-participant',{'submissionId':sid,'stageId':1,'userGroupId':3,'userId':2,'canChangeMetadata':1,'recommendOnly':0,'message':''},f'{sid}-editor-assigned')
s=session('editor');decision(s,3,3,tag='B-send-review',message='Б направлена на рецензирование: PDF автора и архив LaTeX загружены.')
d=req(s,'GET','/submissions/3',tag='B-review-state');print('ROUND',d['reviewRounds'])
decision(s,4,17,tag='C-short-path',message='В принята по короткому тестовому пути, без рецензирования.');decision(s,4,7,tag='C-production',message='В передана в производство.')
d=legacy(s,'grid/article-galleys/article-galley-grid/update-galley',{'submissionId':4,'publicationId':4,'label':'PDF','locale':'ru','urlPath':'','urlRemote':''},'C-create-galley');gid=int(d['events'][0]['data'][0]);upload(s,4,'C-styled.pdf',10,{'assocType':521,'assocId':gid},'C-galley-upload')
req(s,'PUT','/submissions/4/publications/4',{'issueId':2,'pages':'4','datePublished':'2026-10-12'},'C-issue-assigned');req(s,'PUT','/submissions/4/publications/4/publish',{},'C-published');req(s,'GET','/issues/2',tag='issue-after-C')
