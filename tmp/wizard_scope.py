import json, sys
sys.stdout.reconfigure(encoding='utf-8')
m = json.loads(open('vehicle-images-manifest.json', encoding='utf-8').read())
try:
    cfg = open('src/config.py', encoding='utf-8').read()
except Exception as e:
    print('no config', e); cfg = ''

# wizard brands: from config.py MANUFACTURERS keys
import re
m2 = re.search(r'MANUFACTURERS\s*=\s*\{', cfg)
wiz = set()
if m2:
    seg = cfg[m2.start():m2.start()+400000]
    for mm in re.finditer(r'["\']([^"\']+)["\']\s*:\s*\[', seg):
        wiz.add(mm.group(1))
print('wizard brands found in config:', len(wiz))

missing = [(b, mod) for b, r in m['brands'].items()
           for mod, p in (r.get('models') or {}).items()
           if p.get('status') != 'downloaded' and p.get('reason') == 'No matching Commons photograph']
from collections import Counter
in_wiz = [x for x in missing if x[0] in wiz]
out_wiz = [x for x in missing if x[0] not in wiz]
print('missing total:', len(missing))
print('  within wizard (87) brands:', len(in_wiz), f'({100*len(in_wiz)/len(missing):.0f}%)')
print('  outside wizard brands:', len(out_wiz))

print('--- wizard-brand missing, top 15 brands ---')
c = Counter(b for b, _ in in_wiz)
for b, n in c.most_common(15):
    print(f'  {b:20s} {n}')

print('--- sample of wizard-brand missing models ---')
import random; random.seed(1)
for b, mod in random.sample(in_wiz, 25):
    print(f'  {b} | {mod}')