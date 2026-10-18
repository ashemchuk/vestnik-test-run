from importlib.machinery import SourceFileLoader
h=SourceFileLoader('run','/private/tmp/run-full.py').load_module();globals().update({k:getattr(h,k) for k in ['session','req','upload','discussion']})
s=session('editor');upload(s,2,'A-v2.pdf',10,{'assocType':521,'assocId':2},'A-galley-upload');req(s,'GET','/submissions/2/publications/2',tag='A-galley-state')
discussion(s,2,5,'А — согласование PDF','<p>Просьба проверить финальную PDF-гранку в разделе Publication → Galleys и подтвердить публикацию.</p>',[2,3],'A-proof-editor')
a=session('author');discussion(a,2,5,'А — PDF согласован','<p>Проверил финальный PDF: рисунок, формула и исправления v2 сохранены. Согласен на публикацию.</p>',[2,3],'A-proof-author')
