import httpx, json, sys
sys.stdout.reconfigure(encoding='utf-8')
H = {'User-Agent': 'CarServiceAI/1.2 (vehicle duplicate fix) python-httpx/0.27'}
c = httpx.Client(headers=H, timeout=40, follow_redirects=True)
url = 'https://commons.wikimedia.org/w/api.php'
queries = ['intitle:"BMW" intitle:"650i" filetype:bitmap',
           'Ford Transit filetype:bitmap',
           'Volkswagen Golf filetype:bitmap']
for q in queries:
    r = c.get(url, params={'action': 'query', 'format': 'json', 'generator': 'search',
                           'gsrsearch': q, 'gsrnamespace': '6', 'gsrlimit': '10',
                           'prop': 'imageinfo', 'iiprop': 'url|mime|size', 'iiurlwidth': '960'})
    print('QUERY:', q)
    print('STATUS', r.status_code)
    try:
        d = r.json()
    except Exception:
        print('  raw:', r.text[:300])
        continue
    print('  keys', list(d.keys()), 'error?', d.get('error'))
    pages = (d.get('query', {}).get('pages') or {})
    print('  npages', len(pages))
    for k, v in list(pages.items())[:3]:
        print('   ', v.get('title'), (v.get('imageinfo') or [{}])[0].get('mime'),
              (v.get('imageinfo') or [{}])[0].get('width'))