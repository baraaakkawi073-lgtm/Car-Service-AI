import json, sys, urllib.parse, urllib.request, time
sys.stdout.reconfigure(encoding='utf-8')

def key(s): return ''.join(c for c in s.casefold() if c.isalnum())

def load():
    return json.loads(open('vehicle-images-manifest.json', encoding='utf-8').read())

m = load()
missing = []
for b, r in m['brands'].items():
    for mod, p in (r.get('models') or {}).items():
        if p.get('status') != 'downloaded' and p.get('reason') == 'No matching Commons photograph':
            missing.append((b, mod))

print('total no-match missing:', len(missing))

import random
random.seed(7)
sample = random.sample(missing, 60)

UA = {'User-Agent': 'CarServiceAI/1.1 (https://github.com/anomalyco/opencode; vehicle photo lookup for a car-maintenance assistant) python-httpx/0.27',
      'Accept': 'application/json'}

def query(title):
    url = 'https://en.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(title.replace(' ', '_'))
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.load(r)
    except Exception:
        return None
    return j

hits = 0
thumb_hits = 0
for b, mod in sample:
    candidates = [f'{b} {mod}']
    if b.upper() in mod.upper():
        candidates.insert(0, f'{b}')
    got = None
    for t in candidates:
        j = query(t)
        if j and (j.get('originalimage') or j.get('thumbnail')):
            got = t
            hits += 1
            if j.get('originalimage'):
                thumb_hits += 1
            break
    time.sleep(0.1)
    print(f'{"HIT " if got else "MISS"} {b} | {mod}' + (f'  <- [{got}]' if got else ''))

print('---')
print('hits:', hits, '/', len(sample), f'({100*hits/len(sample):.0f}%)')
print('with originalimage:', thumb_hits)