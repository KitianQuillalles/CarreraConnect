from pathlib import Path
p=Path(r'c:\Users\daniz\Desktop\carrera_connect\operatividad\templates\operatividad\gest_contenidos.html')
s=p.read_text(encoding='utf-8')
start = s.find('<script')
if start==-1:
    print('No <script> tag found')
    raise SystemExit(0)
start = s.find('>', start)+1
end = s.rfind('</script>')
if end==-1:
    print('No </script> tag found')
    raise SystemExit(0)
js = s[start:end]
open_count=js.count('{')
close_count=js.count('}')
print('braces { } count:', open_count, close_count)
import re
tries = len(re.findall(r"\btry\b", js))
catches = len(re.findall(r"\bcatch\b", js))
print('try count:', tries, 'catch count:', catches)
# show lines with lone 'catch' or 'try' for inspection
for i,l in enumerate(js.splitlines(), start=1):
    if 'catch' in l or 'try' in l:
        print(i, l.strip())
