from importlib.machinery import SourceFileLoader
h=SourceFileLoader('run','/private/tmp/run-full.py').load_module();s=h.session('author2');h.req(s,'DELETE','/submissions/5',tag='security-draft-remove')
