import json
import requests

H = {'User-Agent': 'CarServiceAI/1.2 (asset verification; local) python-requests/2.31'}
S = requests.Session()
S.headers.update(H)

for q in ['Kalmar Ottawa terminal tractor', 'Frontline armored vehicle', 'BYD T8 truck']:
    r = S.get('https://commons.wikimedia.org/w/api.php', params={
        'action': 'query', 'generator': 'search', 'gsrsearch': q,
        'gsrnamespace': 6, 'gsrlimit': 5, 'prop': 'imageinfo',
        'iiprop': 'url|size|extmetadata', 'iiurlwidth': 960, 'format': 'json'}, timeout=30)
    d = r.json()
    print('\nQUERY:', q)
    print('error:', d.get('error'))
    print('keys:', list(d.keys()))
    qq = d.get('query', {})
    print('query keys:', list(qq.keys()))
    if 'warnings' in d:
        print('warnings:', json.dumps(d['warnings'])[:300])
    pages = qq.get('pages', {})
    print('n pages:', len(pages))
    for p in list(pages.values())[:3]:
        print('  ', p.get('title'), p.get('index'))