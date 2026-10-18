from importlib.machinery import SourceFileLoader
h=SourceFileLoader('run','/private/tmp/run-full.py').load_module();globals().update({k:getattr(h,k) for k in ['session','req','legacy','upload','discussion','root']})
s=session('editor')
d=legacy(s,'grid/article-galleys/article-galley-grid/update-galley',{'submissionId':2,'publicationId':2,'label':'PDF','locale':'ru','urlPath':'','urlRemote':''},'A-create-galley')
print(d)
