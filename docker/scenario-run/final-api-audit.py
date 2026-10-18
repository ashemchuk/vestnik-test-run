from importlib.machinery import SourceFileLoader
h=SourceFileLoader('run','/private/tmp/run-full.py').load_module();s=h.session('admin')
for path,tag in [('/users?count=100','api-users'),('/submissions/2/reviews','api-reviews'),('/submissions?count=100','final-submissions'),('/issues/2','final-issue'),('/contexts/1','final-journal')]:
 try:h.req(s,'GET',path,tag=tag)
 except Exception as e:print('NOT AVAILABLE',path,str(e)[:100])
