from importlib.machinery import SourceFileLoader
h=SourceFileLoader('run','/private/tmp/run-full.py').load_module();globals().update({k:getattr(h,k) for k in ['session','req','upload','legacy','decision']})
for role,label,title,en,files in [('author2','B','Б Анализ времени ожидания в очереди','B Analysing waiting time in a queue',['B-latex.zip','B-author.pdf']),('author3','C','В Короткая заметка о стабильной сортировке','C A short note on stable sorting',['C-styled.docx'])]:
 s=session(role);d=req(s,'POST','/submissions',{'locale':'ru','sectionId':1},label+'-draft');sid=d['id'];pid=d['currentPublicationId'];print(label,sid,pid)
 req(s,'PUT',f'/submissions/{sid}/publications/{pid}',{'title':{'ru':title,'en':en},'abstract':{'ru':'<p>Тестовая работа для проверки редакционного процесса: '+title+'.</p>','en':'<p>A test manuscript for the editorial workflow: '+en+'.</p>'},'keywords':{'ru':['алгоритмы'],'en':['algorithms']}},label+'-metadata')
 for f in files:upload(s,sid,f,tag=label+'-'+f+'-upload')
 req(s,'PUT',f'/submissions/{sid}/submit',{},label+'-submitted')
