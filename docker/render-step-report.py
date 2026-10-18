"""Render the editable step report as a standalone HTML with embedded screenshots."""
from pathlib import Path
import base64
import re
import markdown
root = Path(__file__).resolve().parents[1]
source = root / 'OJS-FULL-RUN-REPORT.md'
destination = root / 'OJS-FREEFORM-REPORT.html'
body = markdown.markdown(source.read_text(), extensions=['fenced_code', 'tables'])
def embed(match):
    path = Path(match.group(1))
    if not path.is_absolute():
        path = root / 'screenshots' / path
    data = base64.b64encode(path.read_bytes()).decode()
    return 'src="data:image/jpeg;base64,' + data + '"'
body = re.sub(r'src="([^\"]+)"', embed, body)
css = '''*{box-sizing:border-box}body{margin:0;background:#eef2f5;color:#203647;font:17px/1.6 system-ui,sans-serif}main{max-width:1080px;margin:auto;background:white;padding:36px}h1{font-size:32px;line-height:1.2}h2{font-size:24px;border-top:1px solid #dce4ea;padding-top:24px;margin-top:40px}img{display:block;max-width:100%;max-height:1000px;height:auto;margin:24px auto}a{color:#006c98}pre{background:#f3f6f8;border:1px solid #d9e3e9;border-radius:5px;padding:16px;overflow-x:auto;font:13px/1.5 ui-monospace,monospace}code{font-size:14px}pre code{font-size:13px}table{border-collapse:collapse;width:100%;font-size:15px}td,th{border:1px solid #d5e0e7;padding:9px;text-align:left;vertical-align:top}th{background:#edf3f7}p:has(>em:only-child){font-size:14px;color:#557082;text-align:center}@media(max-width:650px){main{padding:18px}h1{font-size:27px}table{display:block;overflow-x:auto}}@media print{body{background:white}main{padding:0}img{max-height:800px}pre{white-space:pre-wrap;overflow-wrap:anywhere}}'''
destination.write_text('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OJS — работа по шагам</title><style>' + css + '</style><main>' + body + '</main></html>')
print(destination)
