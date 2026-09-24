import json, sys, urllib.parse, urllib.request, random
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding='utf-8')
UA = {'User-Agent': 'CarServiceAI/1.1 (https://github.com/anomalyco/opencode; vehicle photo lookup for a car-maintenance assistant) python-httpx/0.27',
      'Accept': 'application/json'}

def rest(title, lang):
    url = f'https://{lang}.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(title.replace(' ', '_'))
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            j = json.load(r)
        return lang, j.get('title', ''), (j.get('originalimage') or {}).get('source') or (j.get('thumbnail') or {}).get('source')
    except Exception:
        return None

m = json.loads(open('vehicle-images-manifest.json', encoding='utf-8').read())
missing = [(b, mod) for b, r in m['brands'].items()
           for mod, p in (r.get('models') or {}).items()
           if p.get('status') != 'downloaded' and p.get('reason') == 'No matching Commons photograph']
print('missing no-match:', len(missing))

random.seed(42)
sample = random.sample(missing, 60)
LANGS = ('en', 'de', 'fr', 'it', 'es', 'pt', 'nl', 'ar', 'ru')

hits, misses = [], []
def try_entry(item):
    b, mod = item
    titles = [f'{b} {mod}', f'{b}_{mod}']
    for lang in LANGS:
        for t in titles:
            got = rest(t if '_' not in t else t.replace(' ', '_'), lang)
            if got and got[2]:
                return (b, mod, got)
    return (b, mod, None)

with ThreadPoolExecutor(max_workers=12) as ex:
    results = list(ex.map(try_entry, sample))

for b, mod, got in results:
    if got:
        hits.append((b, mod, got))
    else:
        misses.append((b, mod))

print('HITS:', len(hits), '/', len(sample), f'({100*len(hits)/len(sample):.0f}%)')
print('--- examples ---')
for b, mod, (lang, ttl, src) in hits[:15]:
    print(f'  {b} | {mod}  <- {lang}:{ttl}')
print('--- misses (first 20) ---')
for b, mod in misses[:20]:
    print(f'  {b} | {mod}')