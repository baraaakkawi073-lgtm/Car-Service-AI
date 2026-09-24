import json, sys, urllib.parse, urllib.request, time, re
sys.stdout.reconfigure(encoding='utf-8')
UA = {'User-Agent': 'CarServiceAI/1.1 (https://github.com/anomalyco/opencode; vehicle photo lookup for a car-maintenance assistant) python-httpx/0.27',
      'Accept': 'application/json'}

def rest(title, lang='en'):
    url = f'https://{lang}.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(title.replace(' ', '_'))
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except Exception:
        return None

def commons_search(term, n=6):
    url = ('https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch='
           + urllib.parse.quote(term)
           + '&gsrnamespace=6&gsrlimit=' + str(n)
           + '&prop=imageinfo&iiprop=url|mime|size&iiurlwidth=1200&format=json')
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            j = json.load(r)
        return list((j.get('query') or {}).get('pages', {}).values())
    except Exception:
        return []

def is_photo(p):
    mime = p.get('mime', '')
    w = (p.get('width') or 0); h = (p.get('height') or 0)
    return (mime.startswith('image/jpeg') or mime.startswith('image/png') or mime.startswith('image/webp')) and w >= 500 and h >= 300

def key(s): return ''.join(c for c in s.casefold() if c.isalnum())

sample = [
    ('Mitsubishi', 'FM617'), ('HINO', 'XL7'), ('BYD', 'Fuel Cell Truck'),
    ('Isuzu', 'F7'), ('UD', 'UD2000'), ('WORKHORSE', 'W62'),
    ('AMERICAN MOTORS', 'Eagle 50'), ('SMIT', 'Tractor'),
    ('NAVISTAR', 'F2675'), ('INTERNATIONAL', 'HX61Z'),
    ('CATERPILLAR', 'NF1AD'), ('MACK', 'Pinnacle'),
    ('FREIGHTLINER', 'Cascadia'), ('KENWORTH', 'T680'),
    ('Ferrari', '812'), ('MCLAREN', 'Senna'), ('BUGATTI', 'Mistral'),
    ('TOYOTA', 'Land Cruiser'), ('HONDA', 'Accord'),
    ('TESLA', 'Model 3'), ('ISUZU', 'ELF'), ('AMERITECH', 'F1'),
]

strategies = {}
for b, mod in sample:
    got = []
    # S1: wikipedia multi-lang "Brand Model"
    for lang in ('en', 'de', 'fr', 'it', 'es', 'ar'):
        j = rest(f'{b} {mod}', lang)
        if j and (j.get('originalimage') or j.get('thumbnail')):
            ttl = j.get('title', '')
            img = (j.get('originalimage') or {}).get('source')
            got.append(('wiki', f'{lang}:{ttl}', bool(img))); break
    # S2: commons intitle model only (loose)
    sub = [] if got else None
    if got is None:
        for hit in commons_search(f'intitle:"{mod}"', 8):
            if is_photo(hit):
                sub = ('commons', hit.get('title'), True); break
    strategies[f'{b} | {mod}'] = got[0] if got else sub
    time.sleep(0.15)

hits = [v for v in strategies.values() if v]
print('hits:', len(hits), '/', len(sample), f'({100*len(hits)/len(sample):.0f}%)')
for k, v in strategies.items():
    print(f'{"HIT " if v else "MISS"} {k}' + (f'   <- {v[0]} [{v[1]}]' if v else ''))