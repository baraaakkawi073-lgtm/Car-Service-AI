import json, sys, urllib.parse, urllib.request, time, re
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding='utf-8')
UA = {'User-Agent': 'CarServiceAI/1.1 (https://github.com/anomalyco/opencode; vehicle photo lookup for a car-maintenance assistant) python-httpx/0.27',
      'Accept': 'application/json'}

def opensearch(q, lang):
    url = (f'https://{lang}.wikipedia.org/w/api.php?action=opensearch&search='
           + urllib.parse.quote(q, safe='') + '&limit=5&namespace=0&format=json')
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)[1]
    except Exception:
        return []

def summary(title, lang):
    url = f'https://{lang}.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(title.replace(' ', '_'))
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            j = json.load(r)
        src = (j.get('originalimage') or j.get('thumbnail') or {}).get('source')
        return j.get('title', ''), src
    except Exception:
        return None, None

m = json.loads(open('vehicle-images-manifest.json', encoding='utf-8').read())
import re as _re
cfg = open('src/config.py', encoding='utf-8').read()
m2 = _re.search(r'MANUFACTURERS\s*=\s*\{', cfg)
wiz = set()
if m2:
    for mm in _re.finditer(r'["\']([^"\']+)["\']\s*:\s*\[', cfg[m2.start():m2.start()+400000]):
        wiz.add(mm.group(1))

missing = [(b, mod) for b, r in m['brands'].items()
           for mod, p in (r.get('models') or {}).items()
           if p.get('status') != 'downloaded' and p.get('reason') == 'No matching Commons photograph'
           and b in wiz]
print('wizard-scope missing:', len(missing))

import random; random.seed(5)
sample = random.sample(missing, 40)

def try_entry(item):
    b, mod = item
    queries = [f'{b} {mod}', f'{mod} {b}', mod]
    for lang in ('en', 'de', 'fr', 'de'):
        for q in queries:
            for t in opensearch(q, lang)[:5]:
                if not any(w in t.lower() for w in re.split(r'\W+', b.lower())[:1] if w): 
                    pass
                ttl, src = summary(t, lang)
                if src:
                    return (b, mod, lang, ttl)
    return (b, mod, None, None)

with ThreadPoolExecutor(max_workers=10) as ex:
    results = list(ex.map(try_entry, sample))

hits = [(b, m, l, t) for b, m, l, t in results if t]
print('HITS:', len(hits), '/', len(sample), f'({100*len(hits)/len(sample):.0f}%)')
for b, m, l, t in hits:
    print(f'  {b} | {m}  <- {l}:{t}')
print('--- misses ---')
for b, m, l, t in ([r for r in results if not r[3]]):
    print(f'  {b} | {m}')