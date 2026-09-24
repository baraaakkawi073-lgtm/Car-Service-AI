"""Test intitle-based Commons search precision on tricky entries."""
import httpx, sys
sys.stdout.reconfigure(encoding='utf-8')
H = {'User-Agent': 'CarServiceAI/1.1 (https://github.com/anomalyco/opencode; vehicle photo lookup for a car-maintenance assistant) python-httpx/0.27'}
C = httpx.Client(headers=H, timeout=25)

def search(q, n=8):
    r = C.get('https://commons.wikimedia.org/w/api.php', params={
        'action': 'query', 'format': 'json', 'generator': 'search',
        'gsrsearch': q, 'gsrnamespace': '6', 'gsrlimit': str(n),
        'prop': 'imageinfo', 'iiprop': 'url|mime|size', 'iiurlwidth': '800'})
    if r.status_code != 200:
        return [('ERR', r.status_code)]
    out = []
    for p in sorted((r.json().get('query', {}).get('pages', {}) or {}).values(), key=lambda x: x.get('index', 99)):
        ii = (p.get('imageinfo') or [{}])[0]
        out.append((p.get('title', ''), ii.get('mime', ''), ii.get('width', 0)))
    return out

samples = [
    'intitle:"International" intitle:"4900" filetype:bitmap',
    'intitle:"Plymouth" intitle:"Prowler" filetype:bitmap',
    'intitle:"Suzuki" intitle:"Samurai" filetype:bitmap',
    'intitle:"Jeep" intitle:"CJ-7" filetype:bitmap',
    'intitle:"Fiat" intitle:"500e" filetype:bitmap',
    'intitle:"Kenworth" intitle:"K100" filetype:bitmap',
    'intitle:"Blue Bird" intitle:"All American" filetype:bitmap',
    'intitle:"Mack" intitle:"Granite" filetype:bitmap',
    'intitle:"Caterpillar" intitle:"CX" filetype:bitmap',
    'intitle:"American LaFrance" intitle:"Eagle" filetype:bitmap',
    'intitle:"Ferrari" intitle:"La Ferrari" filetype:bitmap',
    'intitle:"Tesla" intitle:"Cybertruck" filetype:bitmap',
]
for q in samples:
    print('Q:', q)
    for row in search(q):
        print('   ', row)
    print()
    sys.stdout.flush()