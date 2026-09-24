import json, sys, urllib.parse, urllib.request
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
m = json.loads(open('vehicle-images-manifest.json', encoding='utf-8').read())
missing = [(b, mod) for b, r in m['brands'].items()
           for mod, p in (r.get('models') or {}).items()
           if p.get('status') != 'downloaded' and p.get('reason') == 'No matching Commons photograph']

bc = Counter()
prefix_brands = Counter()
for b, mod in missing:
    bc[b] += 1
print('missing no-match:', len(missing), 'across', len(bc), 'brands')
print('--- top 25 brands by missing count ---')
for b, c in bc.most_common(25):
    print(f'  {b:35s} {c}')

# how many would succeed with a WIKIPEDIA SEARCH (opensearch) to resolve the correct article title?
def search(title, lang='en'):
    url = ('https://' + lang + '.wikipedia.org/w/api.php?action=opensearch&search='
           + urllib.parse.quote(title) + '&limit=3&namespace=0&format=json')
    req = urllib.request.Request(url, headers={'User-Agent': 'CarServiceAI/1.1 (vehicle photo probe) python-httpx/0.27', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            j = json.load(r)
        return j[1]
    except Exception:
        return []

print('--- sample opensearch titles for tricky ones ---')
import random
random.seed(3)
for b, mod in random.sample(missing, 12):
    opts = search(f'{b} {mod}')
    print(f'  {b} | {mod} -> {opts[:3]}')